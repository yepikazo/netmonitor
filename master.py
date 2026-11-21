"""Master for distributed network monitoring (Tema 13)."""

import ipaddress
import json
import os
import re
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DISCOVERY_PORT = 9999
TCP_PORT = 9998
MAX_TARGETS = 4096
WORKER_SERVICE = "tema13-network-monitor-worker-v1"

try:
    import resource
except ImportError:  # resource is unavailable on Windows
    resource = None


def local_subnets():
    """Return IPv4 networks from every up interface, with portable fallbacks."""
    networks = {}
    # Linux/Android (including Termux): enumerate every interface instead of
    # asking the routing table which single interface would reach one address.
    try:
        output = subprocess.run(["ip", "-o", "-4", "addr", "show", "up"],
                               capture_output=True, text=True, timeout=3, check=False).stdout
        for line in output.splitlines():
            match = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+/\d+)", line)
            if not match:
                continue
            interface = line.split(":", 2)[1].strip() if ":" in line else ""
            try:
                iface = ipaddress.IPv4Interface(match.group(1))
                if not iface.ip.is_loopback and not iface.ip.is_link_local:
                    networks[str(iface.network)] = (str(iface.network), str(iface.ip), interface)
            except ipaddress.AddressValueError:
                continue
    except (OSError, subprocess.TimeoutExpired):
        pass

    if not networks:
        addresses = set()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("192.0.2.1", 80))
                addresses.add(probe.getsockname()[0])
        except OSError:
            pass
        try:
            addresses.update(socket.gethostbyname_ex(socket.gethostname())[2])
        except OSError:
            pass
        for address in addresses:
            try:
                ip = ipaddress.IPv4Address(address)
                if not ip.is_loopback and not ip.is_link_local:
                    net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                    networks.setdefault(str(net), (str(net), address, "detected"))
            except ipaddress.AddressValueError:
                continue
    return list(networks.values())


def worker_info(ip):
    try:
        with socket.create_connection((ip, TCP_PORT), timeout=0.8) as conn:
            conn.settimeout(1)
            conn.sendall(json.dumps({"action": "info"}).encode() + b"\n")
            data = conn.makefile("rb").readline(4096)
            info = json.loads(data.decode())
            if info.get("service") != WORKER_SERVICE:
                return None
            info["ip"] = ip
            return info
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def discover_workers(wait=1.0):
    workers = {}
    networks = local_subnets()
    if networks:
        print("[*] Jaringan yang dipindai:")
        for network, own_ip, interface in networks:
            print(f"    - {interface}: {own_ip} pada {network} (Wi-Fi/hotspot maupun LAN)")
    else:
        print("[!] Tidak ada subnet IPv4 aktif yang terdeteksi oleh sistem.")
    if networks:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.2)
            for network, _, _ in networks:
                try:
                    sock.sendto(b"DISCOVER_WORKERS", (str(ipaddress.ip_network(network).broadcast_address), DISCOVERY_PORT))
                except OSError:
                    continue
            deadline = time.monotonic() + wait
            while time.monotonic() < deadline:
                try:
                    raw, addr = sock.recvfrom(2048)
                    info = json.loads(raw.decode())
                    if info.get("service") != WORKER_SERVICE:
                        continue
                    info["ip"] = addr[0]
                    workers[addr[0]] = info
                except socket.timeout:
                    continue
                except (OSError, ValueError, json.JSONDecodeError):
                    continue

        # TCP fallback for LANs where broadcast discovery is blocked.
        candidates = []
        for network, own_ip, _ in networks:
            subnet = ipaddress.ip_network(network)
            first_host = int(subnet.network_address) + 1
            last_host = int(subnet.broadcast_address) - 1
            own_number = int(ipaddress.IPv4Address(own_ip))
            # Scan near the master's address. Starting at the network's first
            # address misses nearby nodes when a Wi-Fi subnet is larger than /20.
            low = max(first_host, own_number - MAX_TARGETS // 2)
            high = min(last_host, low + MAX_TARGETS - 1)
            low = max(first_host, high - MAX_TARGETS + 1)
            candidates.extend(str(ipaddress.IPv4Address(number))
                              for number in range(low, high + 1)
                              if number != own_number)
        candidates = list(dict.fromkeys(candidates))
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


def ask_integer(prompt, default, minimum, maximum):
    value = input(f"{prompt} [{default}]: ").strip()
    if not value:
        return default
    try:
        number = int(value)
        if minimum <= number <= maximum:
            return number
    except ValueError:
        pass
    print(f"Input tidak valid; memakai nilai {default}.")
    return default


def print_results(rows, duration, errors=0, baseline=None, node_count=1):
    rows.sort(key=lambda row: ipaddress.IPv4Address(row["ip"]))
    print("\nIP              STATUS       LATENCY avg/min/max         PACKET LOSS")
    print("-" * 78)
    for row in rows:
        if row.get("error"):
            print(f"{row['ip']:<15} ERROR        -                          -")
            continue
        avg = "-" if row["avg_ms"] is None else f"{row['avg_ms']:.2f}/{row['min_ms']:.2f}/{row['max_ms']:.2f} ms"
        print(f"{row['ip']:<15} {row['status']:<12} {avg:<26} {row['packet_loss_pct']:.1f}% ({row['lost']}/{row['sent']})")
    failed = sum(bool(row.get("error")) for row in rows)
    up = sum(row.get("status") == "UP" for row in rows)
    print(f"\nSelesai {duration:.2f}s — UP: {up}, DOWN: {len(rows)-up-failed}, error: {errors+failed}")
    print(f"Throughput: {len(rows) / duration:.2f} IP/detik" if duration else "Throughput: -")
    cpu_seconds = max(0.0, time.process_time())
    peak_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else "tidak tersedia"
    print(f"CPU master (kumulatif proses): {cpu_seconds:.2f}s | Peak memory master: {peak_memory} (platform unit)")
    if baseline and duration:
        speedup = baseline / duration
        print(f"Speedup: {speedup:.2f}x | Efisiensi ({node_count} node): {speedup / node_count * 100:.1f}%")


def monitor_sequential(targets, count, timeout):
    from worker import monitor_one
    rows = []
    print(f"[jalan] Sequential: mulai memantau {len(targets)} target.", flush=True)
    for index, ip in enumerate(targets, 1):
        row = monitor_one((ip, count, timeout))
        rows.append(row)
        print(f"[progres] Sequential {index}/{len(targets)} — {ip} {row['status']}", flush=True)
    return rows


def choose_workers(workers):
    print("\nNode pemroses tersedia:")
    for index, worker in enumerate(workers):
        label = "Master lokal" if worker.get("local") else "Worker LAN"
        print(f"  [{index}] {worker['host']} ({worker['ip']}) — {worker['cores']} core, {label}")
    print("Pilih indeks/rentang (contoh 0-3), all/ENTER, atau tambahkan worker: add <IP>.")
    while True:
        value = input("Node yang digunakan [all]: ").strip().lower()
        if not value or value in {"all", "*"}:
            return workers
        if value.startswith("add "):
            try:
                address = str(ipaddress.IPv4Address(value.split()[1]))
                existing = next((node for node in workers if node["ip"] == address), None)
                if existing:
                    print(f"Worker {address} sudah ada pada daftar.")
                    continue
                print(f"[*] Menghubungi worker {address} pada TCP {TCP_PORT}...")
                node = worker_info(address)
                if node:
                    workers.append(node)
                    print(f"[+] Ditambahkan: [{len(workers)-1}] {node['host']} ({address}), {node['cores']} core")
                else:
                    print("[-] Tidak ada respons worker. Pastikan worker.py berjalan dan TCP 9998 dapat dijangkau.")
            except (ValueError, IndexError):
                print("Format: add 192.168.43.123")
            continue
        indices = []
        try:
            for part in value.replace(" ", ",").split(","):
                if not part:
                    continue
                if "-" in part:
                    first, last = map(int, part.split("-", 1))
                    indices.extend(range(first, last + 1))
                else:
                    indices.append(int(part))
            if indices and all(0 <= index < len(workers) for index in indices):
                return [workers[index] for index in dict.fromkeys(indices)]
        except ValueError:
            pass
        print("Pilihan node tidak valid.")


def select_workers(all_workers, count=0):
    if count <= 0 or count >= len(all_workers):
        return all_workers
    return all_workers[:count]


def monitor_distributed(targets, workers, count, timeout, weighted=False, simulate_failure=False, dynamic=False):
    if not workers:
        return [], 0.0, 0
    if dynamic:
        return monitor_dynamic(targets, workers, count, timeout)
    if weighted:
        total_cores = sum(max(1, worker["cores"]) for worker in workers)
        chunks, start = [], 0
        for i, worker in enumerate(workers):
            size = len(targets) - start if i == len(workers) - 1 else round(len(targets) * worker["cores"] / total_cores)
            chunks.append(targets[start:start + size])
            start += size
    else:
        chunks = [targets[i::len(workers)] for i in range(len(workers))]

    start_time = time.monotonic()
    rows, failed_nodes = [], 0
    assignments = []
    injected_failure = next((i for i, node in enumerate(workers) if not node.get("local")), 0)
    for i, (worker, chunk) in enumerate(zip(workers, chunks)):
        if not chunk:
            continue
        if simulate_failure and i == injected_failure:
            print(f"[simulasi] {worker['host']} gagal; {len(chunk)} target dimasukkan kembali ke antrean.")
            failed_nodes += 1
            assignments.append((None, chunk))
        else:
            assignments.append((worker, chunk))

    with ThreadPoolExecutor(max_workers=max(1, len(assignments))) as pool:
        future_map = {}
        for worker, chunk in assignments:
            node_name = worker["host"] if worker else "retry di master lokal"
            print(f"[jalan] {node_name}: mulai {len(chunk)} target.", flush=True)
            if worker is None:
                future = pool.submit(monitor_local, chunk, count, timeout)
            elif worker.get("local"):
                future = pool.submit(monitor_local, chunk, count, timeout)
            else:
                future = pool.submit(run_job, worker, chunk, count, timeout)
            future_map[future] = (worker, chunk)
        for future in as_completed(future_map):
            worker, chunk = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"error": str(exc), "results": []}
            if result.get("error"):
                failed_nodes += 1
                print(f"[!] Worker {worker['host'] if worker else 'simulasi'} gagal ({result['error']}); retry lokal {len(chunk)} target.")
                recovery_started = time.monotonic()
                try:
                    result = monitor_local(chunk, count, timeout)
                except Exception as exc:
                    result = {"results": [{"ip": ip, "error": str(exc)} for ip in chunk]}
                print(f"[pemulihan] Retry lokal selesai dalam {time.monotonic() - recovery_started:.2f}s.")
            print(f"[progres] {worker['host'] if worker else 'master retry'} selesai {len(result.get('results', []))}/{len(chunk)} target.", flush=True)
            rows.extend(result.get("results", []))
    return rows, time.monotonic() - start_time, failed_nodes


def monitor_dynamic(targets, workers, count, timeout):
    """Dispatch small batches to the next free node, so faster nodes get more work."""
    start_time = time.monotonic()
    batch_size = max(1, (len(targets) + len(workers) * 4 - 1) // (len(workers) * 4))
    batches = iter([targets[i:i + batch_size] for i in range(0, len(targets), batch_size)])
    rows, failed_nodes = [], 0

    def submit(pool, worker):
        try:
            chunk = next(batches)
        except StopIteration:
            return None
        print(f"[jalan] {worker['host']}: batch baru {len(chunk)} target.", flush=True)
        if worker.get("local"):
            future = pool.submit(monitor_local, chunk, count, timeout)
        else:
            future = pool.submit(run_job, worker, chunk, count, timeout)
        return future, worker, chunk

    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        pending = {}
        for worker in workers:
            task = submit(pool, worker)
            if task:
                future, assigned_worker, chunk = task
                pending[future] = (assigned_worker, chunk)
        while pending:
            completed = next(as_completed(tuple(pending)))
            worker, chunk = pending.pop(completed)
            try:
                result = completed.result()
            except Exception as exc:
                result = {"error": str(exc), "results": []}
            if result.get("error"):
                failed_nodes += 1
                print(f"[!] Worker {worker['host']} gagal; retry lokal {len(chunk)} target.")
                recovery_started = time.monotonic()
                try:
                    result = monitor_local(chunk, count, timeout)
                except Exception as exc:
                    result = {"results": [{"ip": ip, "error": str(exc)} for ip in chunk]}
                print(f"[pemulihan] Retry lokal selesai dalam {time.monotonic() - recovery_started:.2f}s.")
            done = len(result.get("results", []))
            print(f"[progres] {worker['host']}: batch selesai {done}/{len(chunk)} target.", flush=True)
            rows.extend(result.get("results", []))
            next_task = submit(pool, worker)
            if next_task:
                future, assigned_worker, next_chunk = next_task
                pending[future] = (assigned_worker, next_chunk)
    return rows, time.monotonic() - start_time, failed_nodes


def evaluation_main():
    print("=" * 72)
    print("DISTRIBUTED NETWORK MONITORING — TEMA 13")
    print("=" * 72)
    print("1. Pemantauan jaringan (semua worker)")
    print("2. Pengujian sequential (baseline satu proses)")
    print("3. Pengujian local parallel (multiprocessing pada master)")
    print("4. Pengujian distributed (jumlah worker dipilih)")
    print("5. Perbandingan load balancing (statis vs dinamis)")
    print("6. Fault tolerance (simulasi worker gagal dan retry lokal)")
    print("7. Scalability (variasi 1, 2, 4, 6, 9 worker + master)")
    mode = input("Pilih pengujian [1]: ").strip() or "1"
    if mode not in {str(i) for i in range(1, 8)}:
        print("Pilihan tidak valid.")
        return
    count = ask_integer("Jumlah probe per IP", 4, 1, 20)
    try:
        timeout = float(input("Timeout per probe dalam detik [1]: ").strip() or "1")
        if not 0 < timeout <= 10:
            raise ValueError
    except ValueError:
        print("Timeout tidak valid; memakai 1 detik.")
        timeout = 1.0
    print("[+] Mencari worker aktif pada semua interface jaringan...")
    local_ips = {address for _, address, _ in local_subnets()}
    remote_workers = [w for w in discover_workers()
                      if w["ip"] not in local_ips and w["ip"] != "127.0.0.1"]
    if not remote_workers:
        print("[-] Tidak menemukan worker jaringan; hanya pengujian sequential/local yang dapat dijalankan.")
    targets = sorted({worker["ip"] for worker in remote_workers}, key=ipaddress.IPv4Address)
    print(f"[+] Target monitoring otomatis: semua {len(targets)} worker yang terdeteksi.")
    print("[+] Worker ditemukan:")
    for worker in remote_workers:
        print(f"    - {worker['host']} ({worker['ip']}) — {worker['cores']} core")
    print(f"[+] Target monitoring: {len(targets)} alamat IPv4 eksplisit")

    workers = [{"host": socket.gethostname(), "ip": "127.0.0.1", "cores": os.cpu_count() or 1, "local": True}]
    workers.extend(remote_workers)
    print(f"[+] Node pemroses tersedia: {len(workers)} (master lokal + worker jaringan)")

    if mode in {"1", "4", "5", "6", "7"}:
        workers = choose_workers(workers)
    if mode == "7":
        remote_count = sum(not worker.get("local") for worker in workers)
        if remote_count < 9:
            print(f"[!] PDF meminta 9 worker untuk skenario penuh; saat ini hanya {remote_count} worker jaringan terpilih.")

    if mode == "2":
        started = time.monotonic()
        rows = monitor_sequential(targets, count, timeout)
        print_results(rows, time.monotonic() - started)
    elif mode == "3":
        baseline_start = time.monotonic()
        monitor_sequential(targets, count, timeout)
        baseline = time.monotonic() - baseline_start
        print(f"Baseline sequential: {baseline:.2f}s")
        started = time.monotonic()
        result = monitor_local(targets, count, timeout)
        elapsed = time.monotonic() - started
        print_results(result["results"], elapsed, baseline=baseline, node_count=1)
    elif mode == "5":
        static_baseline = None
        for dynamic in (False, True):
            label = "dinamis, batch dikirim ke node yang selesai lebih dulu" if dynamic else "statis, pembagian rata di awal"
            print(f"\n[+] Distribusi {label}")
            rows, elapsed, failed = monitor_distributed(targets, workers, count, timeout, dynamic=dynamic)
            print_results(rows, elapsed, failed, baseline=static_baseline, node_count=len(workers))
            if not dynamic:
                static_baseline = elapsed
    elif mode == "6":
        rows, elapsed, failed = monitor_distributed(targets, workers, count, timeout, simulate_failure=True)
        print_results(rows, elapsed, failed)
        print(f"Recovery selesai; node gagal/simulasi yang dicatat: {failed}")
    elif mode == "7":
        baseline = None
        for remote_count in (1, 2, 4, 6, 9):
            selected = [workers[0]] + [node for node in workers[1:] if not node.get("local")][:remote_count]
            if len(selected) == 1:
                print(f"[!] Lewati skenario {remote_count} worker: worker jaringan tidak tersedia.")
                continue
            print(f"\n[+] Skalabilitas: {len(selected)-1} worker + master (target {remote_count} worker)")
            rows, elapsed, failed = monitor_distributed(targets, selected, count, timeout)
            print_results(rows, elapsed, failed, baseline=baseline, node_count=len(selected))
            if baseline is None:
                baseline = elapsed
    else:
        requested = 0
        baseline = None
        if mode == "4":
            requested = ask_integer(f"Jumlah node yang dipakai (1-{len(workers)})", len(workers), 1, len(workers))
            workers = select_workers(workers, requested)
            baseline_start = time.monotonic()
            monitor_sequential(targets, count, timeout)
            baseline = time.monotonic() - baseline_start
            print(f"Baseline sequential: {baseline:.2f}s")
        rows, elapsed, failed = monitor_distributed(targets, workers, count, timeout)
        print_results(rows, elapsed, failed, baseline=baseline, node_count=len(workers))


def main():
    print("=" * 68)
    print("DISTRIBUTED NETWORK MONITORING — TEMA 13")
    print("=" * 68)
    print("[*] Mencari worker.py yang aktif di Wi-Fi/hotspot atau LAN...")
    local_ips = {address for _, address, _ in local_subnets()}
    remote_workers = [worker for worker in discover_workers()
                      if worker["ip"] not in local_ips and worker["ip"] != "127.0.0.1"]
    if not remote_workers:
        print("[-] Discovery otomatis belum menemukan worker.")
        print("    Pastikan Termux menjalankan versi worker.py Tema 13 terbaru (dengan protokol worker-v1).")
        print("    Anda masih bisa memasukkan IP Termux dengan format: add 192.168.x.x")

    workers = [{"host": socket.gethostname(), "ip": "127.0.0.1",
                "cores": os.cpu_count() or 1, "local": True}] + remote_workers
    print("\n[+] Worker.py yang terdeteksi:")
    for index, worker in enumerate(remote_workers, 1):
        print(f"    [{index}] {worker['host']} ({worker['ip']}) — {worker['cores']} core")
    print(f"[+] Master lokal juga tersedia sebagai node komputasi ({workers[0]['cores']} core).")

    selected = choose_workers(workers)
    targets = sorted({worker["ip"] for worker in workers if not worker.get("local")},
                     key=ipaddress.IPv4Address)
    print(f"[+] Target monitoring otomatis: semua {len(targets)} worker yang terdeteksi.")
    if not targets:
        print("[-] Tidak ada worker untuk dipantau. Jalankan worker.py atau tambahkan IP worker yang valid.")
        return
    count = ask_integer("Jumlah probe per IP", 4, 1, 20)
    try:
        timeout = float(input("Timeout per probe dalam detik [1]: ").strip() or "1")
        if not 0 < timeout <= 10:
            raise ValueError
    except ValueError:
        print("Timeout tidak valid; memakai 1 detik.")
        timeout = 1.0

    print(f"\n[+] {len(targets)} target, {len(selected)} node pemroses.")
    print("[+] Menjalankan baseline sequential...")
    started = time.monotonic()
    monitor_sequential(targets, count, timeout)
    baseline = time.monotonic() - started
    print(f"[hasil] Sequential: {baseline:.2f}s")

    print("\n[+] Menjalankan local parallel pada master...")
    started = time.monotonic()
    local_result = monitor_local(targets, count, timeout)
    local_duration = time.monotonic() - started
    print_results(local_result["results"], local_duration, baseline=baseline, node_count=1)

    print("\n[+] Menjalankan pemantauan distributed dengan pembagian dinamis...")
    rows, duration, failed = monitor_distributed(targets, selected, count, timeout, dynamic=True)
    print_results(rows, duration, failed, baseline=baseline, node_count=len(selected))


def monitor_local(targets, count, timeout):
    from worker import monitor_targets
    return {"results": monitor_targets(targets, count, timeout)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "--evaluasi":
        evaluation_main()
    else:
        main()
