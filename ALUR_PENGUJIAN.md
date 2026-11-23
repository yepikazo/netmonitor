# Alur Pengetesan Tema 13

Dokumen ini menjelaskan pengujian sesuai butir UAS. Untuk menjalankan menu semua skenario gunakan `python master.py --evaluasi`. Target monitoring dibuat otomatis dari IP worker Tema 13 yang ditemukan; daftar IP worker itulah yang diping. Discovery hanya memindai satu subnet Wi-Fi/hotspot.

## A. Persiapan eksperimen

### 1. Siapkan node

- Sediakan 1 master dan 9 worker fisik untuk pengujian lengkap.
- Hubungkan semua perangkat ke Wi-Fi/hotspot yang sama dan pastikan client/AP isolation tidak menghalangi komunikasi antarperangkat.
- Ikuti [PANDUAN_SETUP.md](PANDUAN_SETUP.md) untuk memasang `psutil`, membuka TCP `9998` dan UDP `9999` pada worker, serta mengizinkan ICMP echo bila firewall memblokir ping.
- Gunakan source code versi yang sama pada seluruh node, termasuk `worker.py` dan `process_metrics.py`.

### 2. Jalankan worker

Di setiap worker, aktifkan virtual environment dan jalankan:

```sh
source .venv/bin/activate
python worker.py
```

Pada Windows PowerShell, aktifkan dengan:

```powershell
.\.venv\Scripts\Activate.ps1
python worker.py
```

Biarkan seluruh worker tetap berjalan. Catat hostname, alamat IPv4, OS, jumlah core, dan RAM setiap node untuk tabel konfigurasi laporan.

### 3. Mulai menu pengujian di master

Di master jalankan:

```sh
source .venv/bin/activate
python master.py --evaluasi
```

Pada Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python master.py --evaluasi
```

Masukkan jumlah probe dan timeout yang sama pada semua pengulangan. Contoh awal yang dapat dipakai: 5 probe/IP dan timeout 1 detik. Setelah worker ditemukan, pilih semua node dengan Enter atau `all`. Target otomatis adalah seluruh IP worker yang terdeteksi.

Sebelum mengukur, pastikan jumlah worker yang ditampilkan sesuai node yang aktif. Jika worker tidak ditemukan, selesaikan masalah jaringan terlebih dahulu; hasil uji distributed dengan node hilang bukan pengukuran cluster lengkap.

## B. Pengujian wajib

`python master.py` menjalankan sequential baseline, local parallel, dan distributed dinamis masing-masing satu kali. Untuk mengulang ketiga pengujian itu 10 kali tanpa memilih mode, jalankan `python master.py --10`; konfigurasi dimasukkan sekali lalu digunakan pada semua pengulangan. Untuk skenario khusus di `--evaluasi`, satu pemanggilan menjalankan pilihan tersebut satu kali; ulangi command dan pilih mode/konfigurasi sama sebanyak 10 kali jika ingin 10 sampel. Setiap invocation menyimpan hasilnya ke file baru di `hasil/`. Gunakan jumlah probe, timeout, target, dan kondisi jaringan yang sama agar perbandingan adil.

Untuk mengukur distributed processing sebanyak 10 kali, pilih mode `4` pada setiap pengulangan. Untuk mengukur dan membandingkan static vs dynamic sebanyak 10 kali, pilih mode `5`; satu pemanggilan mode tersebut menjalankan kedua strategi masing-masing satu kali. Jangan mencampur hasil dari mode atau konfigurasi yang berbeda saat menghitung rata-rata.

### 1. Sequential processing (baseline)

Pilih `2`. Master memproses target satu per satu dalam satu proses. Catat:

- execution time total;
- throughput IP/detik;
- status, RTT, dan packet loss per target;
- CPU/RAM proses master yang dicetak.

Gunakan waktu ini sebagai baseline sequential untuk menghitung speedup skenario berikutnya.

### 2. Local parallel processing

Pilih `3`. Program menjalankan sequential baseline, kemudian multiprocessing pada master. Catat waktu dan metrik kedua tahap serta hitung:

```text
Speedup local = waktu sequential / waktu local parallel
Efficiency local = speedup local / jumlah core/node yang dipakai × 100%
```

Untuk konsistensi, jelaskan di laporan apakah efficiency dihitung per node atau per core. Jangan mencampur definisi antar tabel.

### 3. Distributed processing

Pilih `4`, pilih node pemroses, lalu masukkan jumlah node yang akan digunakan. Perhitungan `Jumlah node` mencakup master lokal jika master dipilih. Program menjalankan sequential baseline lalu distribusi statis. Catat waktu, throughput, speedup, efficiency, status worker, serta CPU/RAM per node.

### 4. Dynamic load balancing

Pilih `5` dan gunakan semua node. Program mengukur pembagian statis terlebih dahulu, kemudian batch dinamis. Pada mode dinamis, worker yang selesai lebih dulu menerima batch berikutnya. Bandingkan:

- waktu total dan throughput;
- jumlah/beban task yang selesai per worker;
- CPU/RAM rata-rata dan puncak setiap worker;
- apakah pembagian dinamis mengurangi waktu dibanding statis.

Speedup yang ditampilkan pada tahap dinamis memakai waktu statis sebagai pembanding. Jelaskan bahwa hasil dipengaruhi jumlah target, RTT jaringan, dan jumlah batch.

### 5. Fault tolerance

Pilih `6`. Program mensimulasikan kegagalan worker pertama yang dipilih; task worker tersebut dialihkan dan diproses ulang pada master lokal. Catat node yang disimulasikan gagal, jumlah task yang di-requeue, recovery time, hasil akhir target, dan apakah ada target yang hilang.

Mode ini menguji jalur pemulihan terkontrol. Untuk laporan yang lebih kuat, lakukan juga satu percobaan tambahan dengan menghentikan worker sungguhan ketika task berjalan, lalu catat perilakunya secara terpisah.

### 6. Scalability

Pilih `7` dan pilih semua worker. Program menguji 1, 2, 4, 6, lalu 9 worker jaringan; master lokal juga ikut menjadi node pemroses. Sediakan 9 worker fisik agar semua variasi benar-benar dijalankan. Jika jumlah worker tersedia kurang dari konfigurasi tertentu, program melewati konfigurasi itu; jangan mencatat skenario yang dilewati sebagai hasil pengukuran.

Untuk tiap konfigurasi catat execution time, speedup, efficiency, throughput, CPU, dan RAM. Gunakan baseline yang konsisten dan jelaskan jumlah total node pemroses (worker jaringan + master).

## C. Pengulangan dan analisis

- Jalankan setiap skenario minimal 3 kali; 5 kali lebih baik jika waktu memungkinkan.
- Pertahankan daftar worker, jumlah probe, timeout, dan kondisi jaringan yang sama.
- Laporkan rata-rata dan variasi hasil (misalnya minimum–maksimum atau simpangan baku); jangan hanya memilih run tercepat.
- Bandingkan execution time, speedup, efficiency, throughput, CPU/RAM, serta recovery time.
- Jelaskan bahwa RTT berasal dari angka yang dicetak executable `ping`; output `time<1ms` dicatat sebagai estimasi setengah batas tersebut.
- Bila target berstatus DOWN, cek apakah ICMP diblokir sebelum menyimpulkan perangkat mati.
- Ringkasan otomatis program membantu membaca hasil, tetapi BAB IV tetap harus membahas penyebab perbedaan dan keterbatasan eksperimen.

Isi tabel hasil pada [LAPORAN_TEMPLATE.md](LAPORAN_TEMPLATE.md) dengan data aktual. Sertakan tangkapan layar/log yang menunjukkan node dan hasil pengujian.

Master juga menulis konfigurasi run, hasil per target, metrik CPU/RAM, analisis, dan recovery time ke `hasil/hasil_monitoring.txt`. Jika sudah ada, nama berikutnya diberi nomor di depan, misalnya `hasil/1_hasil_monitoring.txt`. Salin hasil dari file tersebut ke tabel BAB IV.

## D. Alur demonstrasi video (maksimal 5 menit)

1. Tampilkan topologi: satu master dan sembilan worker fisik yang terhubung.
2. Tampilkan worker aktif dan hostname/IP masing-masing secara singkat.
3. Jalankan satu pengujian distributed dari master dan tunjukkan hasil status, RTT, packet loss, waktu, throughput, CPU/RAM.
4. Tunjukkan satu bukti load balancing atau fault tolerance.
5. Akhiri dengan ringkasan hasil; pastikan durasi tidak melebihi 5 menit.

Video dan pengujian 10 node harus direkam langsung saat perangkat tersedia; hasilnya tidak dapat digantikan oleh simulasi pada satu komputer.
