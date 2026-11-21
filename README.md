# Distributed Network Monitoring (Tema 13)

Aplikasi master–worker untuk memantau alamat IPv4 yang ditentukan operator. Master menemukan worker melalui UDP broadcast, memakai TCP sweep LAN sebagai fallback, membagi daftar target di antara node, lalu menggabungkan status, latency ICMP, dan packet loss. Setiap node menjalankan probe target secara paralel dengan `ProcessPoolExecutor`.

## Menjalankan

1. Pastikan semua komputer berada pada LAN yang sama dan Python 3 tersedia.
2. Izinkan TCP port `9998` dan UDP port `9999` pada firewall komputer worker.
3. Di setiap komputer worker, jalankan:

   ```sh
   python worker.py
   ```

4. Di komputer master, jalankan dengan target yang memang Anda berwenang pantau:

   ```sh
   python master.py 192.168.1.1 192.168.1.10 192.168.1.0/28
   ```

   Contoh pengaturan jumlah probe dan jumlah worker:

   ```sh
   python master.py 192.168.1.0/28 --count 5 --timeout 1 --workers 4
   ```

Tanpa `--workers`, master memakai semua worker yang ditemukan ditambah proses lokal pada master. CIDR dibatasi maksimal 4096 alamat; untuk memantau satu jaringan besar, pecah menjadi rentang yang lebih kecil. Target dan discovery worker adalah dua hal berbeda: worker ditemukan di LAN, sedangkan daftar IP yang dipantau diberikan eksplisit saat menjalankan master.

## Hasil

- `UP` jika sedikitnya satu probe ICMP mendapat balasan; `DOWN` jika semuanya timeout/gagal.
- Latency ditampilkan sebagai rata-rata/minimum/maksimum waktu round trip probe yang berhasil.
- Packet loss dihitung dari jumlah probe yang tidak mendapat balasan.
- Hasil `ERROR` menunjukkan masalah saat master berkomunikasi dengan worker.

ICMP ping mungkin perlu diizinkan oleh firewall target. Ping yang diblokir akan terlihat sebagai `DOWN`, sehingga interpretasikan hasil sesuai kebijakan jaringan. Worker membutuhkan executable `ping` sistem operasi (`ping` tersedia pada Windows, Linux, dan macOS).

## Catatan implementasi

- Discovery UDP memakai port `9999`; worker menerima task dan permintaan info melalui TCP port `9998`.
- TCP sweep otomatis hanya mencari worker yang membuka port `9998`; ia tidak menentukan target monitoring.
- Pembagian tugas saat ini dibagi merata menurut jumlah IP. Worker menjalankan target-targetnya secara multiprocessing.
- Bila jumlah target sedikit, sejumlah worker dapat menerima bagian kosong; node tetap terhitung sebagai worker aktif.
