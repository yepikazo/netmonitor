# worker.py (Jalankan di PC Client / priz)
import socket
import json
import threading
import os
import time
import math
from concurrent.futures import ProcessPoolExecutor

DISCOVERY_PORT = 9999
TCP_PORT = 9998

def count_primes_chunk(args):
    """Fungsi komputasi berat: Menghitung bilangan prima dalam rentang start..end"""
    start, end = args
    count = 0
    for n in range(max(2, start), end):
        is_p = True
        limit = int(math.isqrt(n)) + 1
        for i in range(2, limit):
            if n % i == 0:
                is_p = False
                break
        if is_p:
            count += 1
    return count

def udp_discovery_responder():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", DISCOVERY_PORT))
        while True:
            try:
                data, addr = s.recvfrom(1024)
                if data == b"DISCOVER_WORKERS":
                    info = {
                        "host": socket.gethostname(),
                        "cores": os.cpu_count() or 2,
                        "port": TCP_PORT
                    }
                    s.sendto(json.dumps(info).encode("utf-8"), addr)
            except Exception:
                pass

def handle_task(conn, addr):
    with conn:
        try:
            raw_data = conn.recv(65536).decode("utf-8")
            if not raw_data:
                return
            req = json.loads(raw_data)
            start_num = req.get("start", 2)
            end_num = req.get("end", 1000)
            cores = os.cpu_count() or 2

            total_items = end_num - start_num
            print("\n" + "=" * 60)
            print(f"[+] DITERIMA TUGAS DARI MASTER ({addr[0]})")
            print("=" * 60)
            print(f"[*] Rentang Angka : {start_num:,} s.d. {end_num:,} ({total_items:,} angka)")
            print(f"[*] Multi-Core    : Mengaktifkan SELURUH {cores} Core CPU...")
            print("[*] (Buka Task Manager / Ctrl+Shift+Esc untuk cek CPU 100%)")
            print("-" * 60)

            # Memecah rentang tugas merata ke seluruh core CPU lokal
            step = total_items // cores
            ranges = []
            for i in range(cores):
                s = start_num + i * step
                e = start_num + (i + 1) * step if i < cores - 1 else end_num
                ranges.append((s, e))

            t0 = time.time()
            with ProcessPoolExecutor(max_workers=cores) as executor:
                results = list(executor.map(count_primes_chunk, ranges))
            durasi = time.time() - t0

            total_primes = sum(results)
            print(f"[✓] KOMPUTASI SELESAI DALAM {durasi:.2f} DETIK!")
            print(f"[✓] Ditemukan {total_primes:,} bilangan prima.")
            print("=" * 60 + "\n")

            response = {
                "host": socket.gethostname(),
                "cores_used": cores,
                "primes_found": total_primes,
                "duration": durasi
            }
            conn.sendall(json.dumps(response).encode("utf-8"))
        except Exception as e:
            print(f"[-] Error proses tugas: {e}")

def main():
    threading.Thread(target=udp_discovery_responder, daemon=True).start()
    hostname = socket.gethostname()
    cores = os.cpu_count() or 2

    print("=" * 60)
    print("      HEAVY PARALLEL WORKER NODE (MULTI-CORE READY)")
    print("=" * 60)
    print(f"[*] Hostname : {hostname}")
    print(f"[*] Kapasitas: {cores} Core CPU (Siap 100% Load)")
    print(f"[*] Status   : Menunggu instruksi dari Master di port {TCP_PORT}...")
    print("=" * 60)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_srv:
        tcp_srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_srv.bind(("", TCP_PORT))
        tcp_srv.listen(5)
        while True:
            conn, addr = tcp_srv.accept()
            threading.Thread(target=handle_task, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()