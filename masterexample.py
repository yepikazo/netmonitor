# C:\mpi\master.py
import socket
import json
import time
import os
import math
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

DISCOVERY_PORT = 9999
TCP_PORT = 9998

def count_primes_chunk_local(args):
    """Fungsi komputasi berat lokal: Menghitung bilangan prima dan mengambil sampel"""
    start, end = args
    count = 0
    samples_first = []
    samples_last = []
    for n in range(max(2, start), end):
        is_p = True
        limit = int(math.isqrt(n)) + 1
        for i in range(2, limit):
            if n % i == 0:
                is_p = False
                break
        if is_p:
            count += 1
            if len(samples_first) < 5:
                samples_first.append(n)
            else:
                if len(samples_last) >= 5:
                    samples_last.pop(0)
                samples_last.append(n)
    return count, samples_first, samples_last

def run_local_task(start_num, end_num):
    """Mengeksekusi komputasi di PC Master lokal menggunakan seluruh core CPU"""
    cores = os.cpu_count() or 2
    total_items = end_num - start_num
    step = total_items // cores
    ranges = []
    for i in range(cores):
        s = start_num + i * step
        e = start_num + (i + 1) * step if i < cores - 1 else end_num
        ranges.append((s, e))

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=cores) as executor:
        results = list(executor.map(count_primes_chunk_local, ranges))
    durasi = time.time() - t0

    total_primes = sum(r[0] for r in results)
    all_first = []
    for r in results:
        all_first.extend(r[1])
        if len(all_first) >= 5:
            break
    sample_first = all_first[:5]

    all_last = []
    for r in reversed(results):
        all_last = r[2] + all_last
        if len(all_last) >= 5:
            break
    sample_last = all_last[-5:] if all_last else sample_first

    return {
        "host": socket.gethostname() + " (PC Master Anda)",
        "cores_used": cores,
        "primes_found": total_primes,
        "sample_first": sample_first,
        "sample_last": sample_last,
        "duration": durasi
    }, durasi

def check_tcp_node(ip):
    """Mengecek port 9998 jika UDP broadcast diblokir router/firewall"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex((ip, TCP_PORT)) == 0:
                try:
                    s.sendall(json.dumps({"action": "info"}).encode("utf-8"))
                    s.settimeout(0.5)
                    raw = s.recv(1024).decode("utf-8")
                    info = json.loads(raw)
                    info["ip"] = ip
                    return info
                except Exception:
                    try:
                        name = socket.gethostbyaddr(ip)[0]
                    except Exception:
                        name = "Worker-Node"
                    return {"host": name, "cores": 4, "port": TCP_PORT, "ip": ip}
    except Exception:
        pass
    return None

def get_local_subnets():
    """Mendeteksi seluruh subnet aktif di PC ini (bisa bekerja offline tanpa internet)"""
    subnets = []
    ips = []
    # 1. Coba probe gateway (jika ada koneksi internet)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
    except Exception:
        pass

    # 2. Coba baca semua IP dari hostname lokal (sangat ampuh saat offline di lab)
    try:
        host = socket.gethostname()
        for ip in socket.gethostbyname_ex(host)[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass

    for ip in ips:
        parts = ip.split(".")
        if len(parts) == 4 and not parts[0].startswith("127"):
            prefix = ".".join(parts[:3])
            if prefix not in [s[0] for s in subnets]:
                subnets.append((prefix, f"{prefix}.255", ip))

    if not subnets:
        subnets.append(("192.168.0", "192.168.0.255", "127.0.0.1"))
    return subnets

def discover_workers(timeout=1.0):
    """Dual-Discovery: UDP Broadcast + Fast Parallel TCP Sweep (Offline & Multi-Adapter Ready)"""
    workers = {}
    local_subnets = get_local_subnets()

    # Cetak info subnet agar user tahu IP Master apa yang aktif
    detected_ips = [s[2] for s in local_subnets]
    print(f"[*] IP Master Terdeteksi: {', '.join(detected_ips)}")

    # 1. Jalankan UDP Broadcast ke seluruh subnet lokal
    broadcast_list = ["255.255.255.255", "<broadcast>"] + [s[1] for s in local_subnets]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.2)

        for b_ip in broadcast_list:
            try:
                s.sendto(b"DISCOVER_WORKERS", (b_ip, DISCOVERY_PORT))
            except Exception:
                pass

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = s.recvfrom(1024)
                ip = addr[0]
                info = json.loads(data.decode("utf-8"))
                info["ip"] = ip
                workers[ip] = info
            except socket.timeout:
                continue
            except Exception:
                pass

    # 2. Fast TCP Sweep Fallback (Menembus router AP Isolation / memblokir broadcast)
    targets = []
    for prefix, _, my_ip in local_subnets:
        for i in range(1, 255):
            t_ip = f"{prefix}.{i}"
            if t_ip not in workers and t_ip != my_ip:
                targets.append(t_ip)

    if targets:
        with ThreadPoolExecutor(max_workers=80) as ex:
            tcp_nodes = list(filter(None, ex.map(check_tcp_node, targets)))
            for node in tcp_nodes:
                workers[node["ip"]] = node

    return list(workers.values())

def send_task(worker, start_num, end_num):
    """Mengirim tugas rentang angka ke worker (remote atau local)"""
    if worker.get("is_local"):
        res, durasi = run_local_task(start_num, end_num)
        return worker, start_num, end_num, res, durasi

    ip = worker["ip"]
    port = worker.get("port", TCP_PORT)
    t0 = time.time()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(180)  # Timeout 3 menit untuk komputasi berat
            s.connect((ip, port))
            payload = json.dumps({"start": start_num, "end": end_num}).encode("utf-8")
            s.sendall(payload)

            raw_res = s.recv(65536).decode("utf-8")
            res = json.loads(raw_res)
            durasi = time.time() - t0
            return worker, start_num, end_num, res, durasi
    except Exception as e:
        durasi = time.time() - t0
        err_msg = str(e)
        if "10060" in err_msg or "timed out" in err_msg.lower():
            err_msg = "Firewall Windows memblokir Port 9998 (Inbound Connection Blocked)"
        elif "10061" in err_msg or "refused" in err_msg.lower():
            err_msg = "Script worker.py belum berjalan di PC Client ini"
        return worker, start_num, end_num, {"error": err_msg}, durasi

def parse_node_selection(input_str, total_nodes):
    """Mendukung format: all, *, enter, koma (0,1,2), rentang (0-3), dan spasi (0 1 2)"""
    input_str = input_str.strip().lower()
    if not input_str or input_str in ["all", "*"]:
        return list(range(total_nodes))

    indices = []
    # Normalisasi spasi dan koma
    parts = input_str.replace(" ", ",").split(",")
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if "-" in p:
            try:
                start, end = p.split("-")
                indices.extend(range(int(start), int(end) + 1))
            except ValueError:
                pass
        elif p.isdigit():
            indices.append(int(p))

    # Validasi index dan hapus duplikasi sambil menjaga urutan
    valid = []
    for i in indices:
        if 0 <= i < total_nodes and i not in valid:
            valid.append(i)
    return valid

def main():
    print("=" * 68)
    print("      DISTRIBUTED PARALLEL COMPUTING (MASTER NODE)")
    print("=" * 68)
    print("[*] Memindai Worker di seluruh jaringan LAN (Auto-Discovery)...")

    remote_workers = discover_workers(timeout=1.5)

    # Otomatis mendaftarkan PC Master Lokal sebagai Worker #0
    local_worker = {
        "host": socket.gethostname(),
        "ip": "127.0.0.1",
        "cores": os.cpu_count() or 4,
        "is_local": True
    }
    
    # Gabungkan Master lokal + Client jaringan
    all_workers = [local_worker] + [w for w in remote_workers if w["host"] != socket.gethostname()]

    print(f"\n[+] Siap Digunakan {len(all_workers)} Node Komputasi:")
    print("-" * 68)
    for idx, w in enumerate(all_workers):
        label = "(PC Master Anda / Lokal)" if w.get("is_local") else "(Client Jaringan LAN)"
        print(f"  [{idx}] Host: {w['host']:<16} | Core: {w['cores']:>2} Cores | {label}")
    print("-" * 68)

    # 1. Pilih Worker Secara Fleksibel
    print("\nFormat Pemilihan Perangkat:")
    print("  * Tekan [ENTER] atau ketik 'all' -> Pilih SEMUA perangkat sekaligus")
    print("  * Pilih spesifik dengan koma     -> Contoh: 0,1 atau 0,2,3")
    print("  * Rentang dengan tanda hubung    -> Contoh: 0-2 (memilih node 0, 1, dan 2)")
    print("  * Tambah IP manual jika perlu    -> Contoh: add 192.168.0.50")

    selected_workers = []
    while not selected_workers:
        default_all = f"0-{len(all_workers)-1}" if len(all_workers) > 1 else "0"
        pilihan = input(f"\nMasukkan pilihan node [Default: {default_all} (Semua)]: ").strip()

        if pilihan.lower().startswith("add "):
            target_ip = pilihan.split()[1].strip()
            print(f"[*] Menghubungi IP manual: {target_ip}...")
            manual_node = check_tcp_node(target_ip)
            if not manual_node:
                manual_node = {"host": f"Node-{target_ip}", "cores": 4, "port": TCP_PORT, "ip": target_ip}
            all_workers.append(manual_node)
            print(f"[✓] Berhasil menambahkan manual: [{len(all_workers)-1}] {manual_node['host']} ({target_ip})")
            continue

        selected_idx = parse_node_selection(pilihan, len(all_workers))
        if selected_idx:
            selected_workers = [all_workers[i] for i in selected_idx]
        else:
            print("[-] Pilihan tidak valid atau di luar rentang. Silakan coba lagi.")

    print(f"\n[✓] Terpilih {len(selected_workers)} Node Komputasi untuk Cluster:")
    total_selected_cores = sum(w["cores"] for w in selected_workers)
    for idx, w in enumerate(selected_workers):
        tipe = "Master (Lokal)" if w.get("is_local") else "Client (LAN)"
        print(f"    {idx+1}. {w['host']:<16} ({w['ip']}) - {w['cores']} Cores [{tipe}]")
    print(f"    --> Total Tenaga Komputasi: {total_selected_cores} Core CPU!")

    # 2. Input beban komputasi berat
    print("\n" + "-" * 68)
    print("Studi Kasus: Pencarian Bilangan Prima Skala Besar (Heavy Compute)")
    print("Rekomendasi beban waktu (~30 s.d. 45 detik untuk 2 PC): 30.000.000 angka")
    input_total = input("Masukkan total angka yang diuji [Default: 30000000]: ").strip()
    total_target = int(input_total) if input_total.isdigit() and int(input_total) > 0 else 30_000_000

    # 3. SCATTER: Memecah rentang angka proporsional dengan kekuatan Core tiap PC (Load Balancing)
    n = len(selected_workers)
    total_cores = sum(w["cores"] for w in selected_workers)
    ranges = []
    current_start = 2
    for i, w in enumerate(selected_workers):
        if i == n - 1:
            current_end = total_target
        else:
            share = int((w["cores"] / total_cores) * (total_target - 2))
            current_end = current_start + share - 1
        ranges.append((current_start, current_end))
        current_start = current_end + 1

    print("\n" + "=" * 68)
    print("   [FASE 1: SCATTER] PEMBAGIAN BEBAN RENTANG ANGKA KE TIAP PC")
    print("=" * 68)
    for i in range(n):
        w = selected_workers[i]
        s_val, e_val = ranges[i]
        items_count = e_val - s_val + 1
        porsi_persen = (w['cores'] / total_cores) * 100
        tipe = "PC Master Lokal" if w.get("is_local") else "PC Client Jaringan"
        print(f"  >> PC #{i+1} [{w['host']} - {tipe}]")
        print(f"     Kapasitas    : {w['cores']} Core CPU ({porsi_persen:.1f}% Tenaga Cluster)")
        print(f"     Beban Hitung : Rentang {s_val:,} s.d. {e_val:,} ({items_count:,} angka)\n")

    print("=" * 68)
    print("   [FASE 2: PARALLEL COMPUTE] PROSES SERENTAK DI SEMUA PC (100% CPU)")
    print("=" * 68)
    print("[*] Seluruh PC sedang memproses komputasi secara simultan...")
    print("[*] (Buka Task Manager / Ctrl+Shift+Esc di tiap PC untuk pantau grafik CPU)\n")
    t_start = time.time()

    # 4. Kirim tugas simultan ke semua PC terpilih
    hasil_cluster = []
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [
            pool.submit(send_task, selected_workers[i], ranges[i][0], ranges[i][1])
            for i in range(n)
        ]
        for f in futures:
            w, s_val, e_val, res, durasi = f.result()
            tipe = "PC Master" if w.get("is_local") else "PC Client"

            if "error" in res:
                print(f"  [✗] GAGAL: PC #{len(hasil_cluster)+1} [{w['host']} ({tipe})]")
                print(f"      Kendala        : {res['error']}")
                print(f"      Rentang Macet  : {s_val:,} s.d. {e_val:,}\n")
                continue

            hasil_cluster.append((w, s_val, e_val, res, durasi))
            primes = res.get("primes_found", 0)
            cores_used = res.get("cores_used", w["cores"])
            s_first = res.get("sample_first", [])
            s_last = res.get("sample_last", [])

            print(f"  [✓] HASIL DARI PC #{len(hasil_cluster)} [{w['host']} ({tipe})]")
            print(f"      Core Digunakan : {cores_used} Core CPU (100% Load)")
            print(f"      Bagian Tugas   : Rentang {s_val:,} s.d. {e_val:,}")
            print(f"      Prima Ditemui  : {primes:,} bilangan prima")
            print(f"      Bukti Angka    : {s_first} ... {s_last}")
            print(f"      Waktu Proses   : {durasi:.2f} detik\n")

    t_end = time.time()

    # 5. GATHER: Penggabungan dan Rekapitulasi Akhir
    total_primes_all = sum(res.get("primes_found", 0) for _, _, _, res, _ in hasil_cluster)
    total_active_cores = sum(res.get("cores_used", w["cores"]) for w, _, _, res, _ in hasil_cluster)
    waktu_cluster = t_end - t_start

    print("=" * 68)
    print("   [FASE 3: GATHER & REKAPITULASI] HASIL AKHIR CLUSTER")
    print("=" * 68)
    print("  Rincian Distribusi Pengerjaan:")
    for w, s_val, e_val, res, durasi in hasil_cluster:
        primes = res.get("primes_found", 0)
        items_count = e_val - s_val + 1
        tipe = "Master" if w.get("is_local") else "Client"
        print(f"   * PC {w['host']:<15} [{tipe:<6}] : {items_count:,} angka -> {primes:,} prima ({durasi:.2f}s)")

    print("-" * 68)
    print(f"  Total Seluruh Angka Diuji    : {total_target:,} angka")
    print(f"  Total Core CPU Dilibatkan    : {total_active_cores} Core (Cluster Multi-Node)")
    print(f"  Total Bilangan Prima Ditemui : {total_primes_all:,} bilangan prima")
    print(f"  Total Waktu Komputasi Cluster: {waktu_cluster:.2f} detik (~{waktu_cluster/60:.1f} menit)")

    if len(hasil_cluster) > 1:
        single_estimate = sum(d for _, _, _, _, d in hasil_cluster)
        speedup = single_estimate / waktu_cluster if waktu_cluster > 0 else 1
        print(f"  Efisiensi / Speedup          : ~{speedup:.1f}x LEBIH CEPAT dibanding 1 PC!")
    print("=" * 68 + "\n")

if __name__ == "__main__":
    main()
