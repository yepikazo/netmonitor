"""Worker node for distributed network monitoring (Tema 13)."""


import concurrent.futures
import ipaddress
import json
import os
import platform
import socket
import subprocess
import threading

DISCOVERY_PORT = 9999
TCP_PORT = 9998
MAX_TARGETS = 4096


def ping_once(ip, timeout):
    """Run one platform-native ICMP echo and return elapsed milliseconds or None."""
    system = platform.system().lower()
    if system == "windows":
        command = ["ping", "-n", "1", "-w", str(max(1, int(timeout * 1000))), ip]
    else:
        # Linux and macOS use different timeout flags; both accept -c 1.
        command = (["ping", "-n", "-c", "1", "-W", str(max(1, int(timeout)) if system == "linux" else max(1, int(timeout * 1000))), ip]
                   if system == "linux" else ["ping", "-n", "-c", "1", "-W", str(max(1, int(timeout))), ip])
    started = time.perf_counter()
    try:
        proc = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=timeout + 1, check=False)
        return (time.perf_counter() - started) * 1000 if proc.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def monitor_one(args):
    ip, count, timeout = args
    samples = [ping_once(ip, timeout) for _ in range(count)]
    received = [sample for sample in samples if sample is not None]
    sent = len(samples)
    lost = sent - len(received)
    return {
        "ip": ip,
        "status": "UP" if received else "DOWN",
        "sent": sent,
        "received": len(received),
        "lost": lost,
        "packet_loss_pct": lost * 100 / sent,
        "avg_ms": sum(received) / len(received) if received else None,
        "min_ms": min(received) if received else None,
        "max_ms": max(received) if received else None,
    }


def monitor_targets(targets, count, timeout):
    if not isinstance(targets, list) or len(targets) > MAX_TARGETS:
        raise ValueError(f"targets harus berupa daftar maksimal {MAX_TARGETS} IP")
    if (not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 20
            or not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 10):
        raise ValueError("parameter count/timeout di luar batas")
    try:
        targets = [str(ipaddress.IPv4Address(ip)) for ip in targets]
    except (ipaddress.AddressValueError, TypeError) as exc:
        raise ValueError("semua target harus berupa alamat IPv4 valid") from exc
    cores = os.cpu_count() or 1
    # Each process works on independent IPs; avoid spawning more processes than targets.
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(cores, max(1, len(targets)))) as pool:
        return list(pool.map(monitor_one, [(ip, count, timeout) for ip in targets]))


def send_line(conn, value):
    conn.sendall(json.dumps(value).encode() + b"\n")


def handle_client(conn, addr):
    with conn:
        try:
            conn.settimeout(10)
            raw = conn.makefile("rb").readline(1024 * 1024)
            if not raw:
                return
            request = json.loads(raw.decode())
            if request.get("action") == "info":
                send_line(conn, {"host": socket.gethostname(), "cores": os.cpu_count() or 1, "port": TCP_PORT})
                return
            if request.get("action") != "monitor":
                send_line(conn, {"error": "aksi tidak dikenal"})
                return
            targets = request.get("targets")
            count = request.get("count", 4)
            timeout = request.get("timeout", 1.0)
            conn.settimeout(None)
            print(f"[+] {addr[0]} meminta monitoring {len(targets) if isinstance(targets, list) else '?'} target")
            results = monitor_targets(targets, count, timeout)
            send_line(conn, {"host": socket.gethostname(), "results": results})
            print(f"[✓] Selesai memantau {len(results)} target untuk {addr[0]}")
        except (ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
            try:
                send_line(conn, {"error": str(exc)})
            except OSError:
                pass
            print(f"[-] Permintaan dari {addr[0]} gagal: {exc}")


def udp_discovery_responder():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", DISCOVERY_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                if data == b"DISCOVER_WORKERS":
                    info = {"host": socket.gethostname(), "cores": os.cpu_count() or 1, "port": TCP_PORT}
                    sock.sendto(json.dumps(info).encode(), addr)
            except OSError:
                continue


def main():
    threading.Thread(target=udp_discovery_responder, daemon=True).start()
    print(f"Network Monitor Worker — {socket.gethostname()} ({os.cpu_count() or 1} core)")
    print(f"Menunggu master pada TCP {TCP_PORT}, discovery UDP {DISCOVERY_PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("", TCP_PORT))
        server.listen(32)
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
