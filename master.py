"""Master for distributed network monitoring (Tema 13)."""

import argparse
import ipaddress
import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DISCOVERY_PORT = 9999
TCP_PORT = 9998
MAX_TARGETS = 4096


def local_subnets():
    """Find IPv4 /24 networks on local interfaces using the standard library."""
    addresses = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 80))  # TEST-NET address; no packet is sent.
            addresses.add(probe.getsockname()[0])
    except OSError:
        pass
    try:
        addresses.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    networks = {}
    for address in addresses:
        try:
            ip = ipaddress.IPv4Address(address)
            if not ip.is_loopback and not ip.is_link_local:
                net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                networks[str(net)] = (str(net), address)
        except ipaddress.AddressValueError:
            continue
    return list(networks.values())


def worker_info(ip):
    try:
        with socket.create_connection((ip, TCP_PORT), timeout=0.35) as conn:
            conn.settimeout(1)
            conn.sendall(json.dumps({"action": "info"}).encode() + b"\n")
            data = conn.makefile("rb").readline(4096)
            info = json.loads(data.decode())
            info["ip"] = ip
            return info
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def discover_workers(wait=1.0):
    workers = {}
    networks = local_subnets()
    if networks:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.2)
            for network, _ in networks:
                sock.sendto(b"DISCOVER_WORKERS", (str(ipaddress.ip_network(network).broadcast_address), DISCOVERY_PORT))
            deadline = time.monotonic() + wait
            while time.monotonic() < deadline:
                try:
                    raw, addr = sock.recvfrom(2048)
                    info = json.loads(raw.decode())
                    info["ip"] = addr[0]
                    workers[addr[0]] = info
                except socket.timeout:
                    continue
                except (OSError, ValueError, json.JSONDecodeError):
                    continue

        # TCP fallback for LANs where broadcast discovery is blocked.
        candidates = []
        for network, own_ip in networks:
            candidates.extend(str(ip) for ip in ipaddress.ip_network(network).hosts() if str(ip) != own_ip)
        with ThreadPoolExecutor(max_workers=96) as pool:
            futures = [pool.submit(worker_info, ip) for ip in candidates if ip not in workers]
            for future in as_completed(futures):
                info = future.result()
                if info:
                    workers[info["ip"]] = info
    return list(workers.values())


def parse_targets(items):
    """Expand explicit IPv4 addresses/CIDRs while bounding accidental huge scans."""
    targets = set()
    for item in items:
        try:
            if "/" in item:
                network = ipaddress.ip_network(item, strict=False)
                if network.version != 4:
                    raise ValueError("hanya IPv4 yang didukung")
                if network.num_addresses > MAX_TARGETS:
                    raise ValueError(f"maksimal {MAX_TARGETS} alamat per rentang")
                targets.update(str(ip) for ip in network.hosts())
            else:
                targets.add(str(ipaddress.IPv4Address(item)))
        except (ValueError, ipaddress.AddressValueError) as exc:
            raise ValueError(f"Target tidak valid '{item}': {exc}") from exc
        if len(targets) > MAX_TARGETS:
            raise ValueError(f"Jumlah target melebihi batas {MAX_TARGETS}")
    return sorted(targets, key=ipaddress.IPv4Address)


def request_json(ip, payload, timeout):
    with socket.create_connection((ip, TCP_PORT), timeout=timeout) as conn:
        conn.settimeout(timeout)
        conn.sendall(json.dumps(payload).encode() + b"\n")
        file = conn.makefile("rb")
        response = file.readline(4 * 1024 * 1024)
        if not response:
            raise ConnectionError("worker menutup koneksi tanpa hasil")
        return json.loads(response.decode())


def run_job(worker, targets, count, timeout):
    try:
        return request_json(worker["ip"], {"action": "monitor", "targets": targets,
                            "count": count, "timeout": timeout}, max(30, count * timeout + 10))
    except (OSError, ValueError, ConnectionError) as exc:
        return {"error": str(exc), "results": []}


def main():
    parser = argparse.ArgumentParser(description="Pemantauan konektivitas IP terdistribusi (Tema 13).")
    parser.add_argument("targets", nargs="+", help="Alamat IPv4 atau CIDR yang Anda berwenang pantau, mis. 192.168.1.10 192.168.1.0/28")
    parser.add_argument("--workers", type=int, default=0, help="Jumlah worker jaringan yang digunakan (0=semua yang ditemukan)")
    parser.add_argument("--count", type=int, default=4, help="Probe per IP untuk menghitung packet loss (default: 4)")
    parser.add_argument("--timeout", type=float, default=1.0, help="Timeout tiap probe dalam detik (default: 1)")
    args = parser.parse_args()
    if args.count < 1 or args.count > 20 or not 0 < args.timeout <= 10:
        parser.error("--count harus 1..20 dan --timeout harus 0..10 detik")
    try:
        targets = parse_targets(args.targets)
    except ValueError as exc:
        parser.error(str(exc))
    if not targets:
        parser.error("Tidak ada alamat host dalam daftar target")

    print("[+] Mencari worker melalui UDP discovery dan TCP sweep...")
    workers = discover_workers()
    local = {"host": socket.gethostname(), "ip": "127.0.0.1", "cores": os.cpu_count() or 1, "local": True}
    workers.insert(0, local)
    if args.workers:
        if args.workers < 1:
            parser.error("--workers harus lebih besar dari 0")
        workers = workers[:args.workers]

    print(f"[+] {len(workers)} node aktif; {len(targets)} alamat target; {args.count} probe/IP")
    for i, worker in enumerate(workers, 1):
        print(f"    {i}. {worker['host']} ({worker['ip']}) — {worker['cores']} core")

    # Static equal chunks keep assignment simple; workers parallelize probes locally.
    chunks = [targets[i::len(workers)] for i in range(len(workers))]
    started = time.monotonic()
    outputs = []
    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        futures = {pool.submit(monitor_local, chunk, args.count, args.timeout) if worker.get("local")
                   else pool.submit(run_job, worker, chunk, args.count, args.timeout): worker
                   for worker, chunk in zip(workers, chunks)}
        for future in as_completed(futures):
            worker = futures[future]
            try:
                outputs.append((worker, future.result()))
            except Exception as exc:
                outputs.append((worker, {"error": str(exc), "results": []}))
    duration = time.monotonic() - started
    rows = [row for _, output in outputs for row in output.get("results", [])]
    failed_nodes = [(worker, output["error"]) for worker, output in outputs if output.get("error")]
    rows.sort(key=lambda row: ipaddress.IPv4Address(row["ip"]))
    print("\nIP              STATUS       LATENCY (avg/min/max)       PACKET LOSS")
    print("-" * 76)
    for row in rows:
        if row.get("error"):
            print(f"{row['ip']:<15} ERROR        -                         - ({row['error']})")
            continue
        avg = "-" if row["avg_ms"] is None else f"{row['avg_ms']:.2f}/{row['min_ms']:.2f}/{row['max_ms']:.2f} ms"
        print(f"{row['ip']:<15} {row['status']:<12} {avg:<25} {row['packet_loss_pct']:.1f}% ({row['lost']}/{row['sent']})")
    for worker, error in failed_nodes:
        print(f"Worker gagal {worker['host']} ({worker['ip']}): {error}")
    errors = sum(bool(row.get("error")) for row in rows)
    up = sum(row.get("status") == "UP" for row in rows)
    print(f"\nSelesai {duration:.2f}s — UP: {up}, DOWN: {len(rows)-up-errors}, error: {errors + len(failed_nodes)}")


def monitor_local(targets, count, timeout):
    from worker import monitor_targets
    return {"results": monitor_targets(targets, count, timeout)}


if __name__ == "__main__":
    main()
