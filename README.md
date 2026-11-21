# Distributed Network Monitoring — Tema 13

Aplikasi master–worker untuk memantau konektivitas alamat IPv4. **Jaringan Wi-Fi/hotspot adalah cara koneksi yang disarankan/default untuk percobaan ini**: hubungkan master dan semua worker ke Wi-Fi/hotspot yang sama. Master menemukan worker menggunakan UDP broadcast dan TCP sweep fallback seperti pola `masterexample.py`; worker menerima tugas melalui TCP, lalu membagi target ke beberapa proses CPU. Daftar worker adalah node pemroses, sedangkan alamat IP/CIDR yang dimonitor dimasukkan operator secara eksplisit.

## Menjalankan

1. Hubungkan master dan semua worker ke **Wi-Fi/hotspot yang sama** dan pasang Python 3. Pada setiap komputer worker, izinkan TCP `9998` serta UDP `9999` (perintah di bawah).
2. Di setiap worker jalankan `python worker.py`.
3. Di master jalankan `python master.py`, pilih skenario pengujian, jumlah probe dan timeout, lalu masukkan alamat IP/CIDR yang diizinkan.
4. Pilih worker dari daftar yang ditemukan. Tekan Enter untuk memakai seluruh node atau masukkan indeks/rentang seperti `0-3`. Jika worker Termux tidak terdeteksi, masukkan `add <IP-Termux>` pada prompt pilihan node, misalnya `add 192.168.43.123`.

Contoh target: `192.168.1.1, 192.168.1.10` atau `192.168.1.0/28`. Target CIDR dibatasi maksimal 4096 alamat. Worker yang ditemukan tidak otomatis dijadikan target monitoring.

## Membuka port firewall pada worker

Jalankan perintah pada komputer **worker**. TCP `9998` dipakai master untuk meminta info dan mengirim tugas; UDP `9999` dipakai untuk discovery. Perintah firewall biasanya perlu dijalankan dengan hak administrator/root. Jika firewall tidak memakai UFW/firewalld di Linux, sesuaikan dengan pengelola firewall yang aktif.

### Linux (UFW, misalnya Ubuntu/Debian)

Pasang UFW jika belum tersedia:

```sh
sudo apt update
sudo apt install ufw
```

Lalu izinkan port worker:

```sh
sudo ufw allow 9998/tcp
sudo ufw allow 9999/udp
sudo ufw status
```

Untuk distro berbasis Fedora/RHEL, gunakan `firewalld` (umumnya sudah terpasang) pada bagian berikutnya, atau pasang dengan `sudo dnf install ufw` jika repositori distro menyediakan paket UFW.

### Arch Linux (UFW)

Arch Linux dapat memasang UFW melalui pacman. Jalankan pada worker Arch jika UFW belum tersedia:

```sh
sudo pacman -S ufw
sudo systemctl enable --now ufw.service
```

Tambahkan rule port worker dan periksa statusnya:

```sh
sudo ufw allow 9998/tcp
sudo ufw allow 9999/udp
sudo ufw status verbose
```

Jika UFW baru saja diaktifkan, pastikan rule dibuat sesuai jaringan yang dipercaya dan jangan mengaktifkan pengelola firewall lain bersamaan tanpa memahami konflik aturannya. Rujukan instalasi/service: [ArchWiki UFW](https://wiki.archlinux.org/title/Uncomplicated_Firewall).

### Linux (firewalld, misalnya Fedora/RHEL)

```sh
sudo firewall-cmd --permanent --add-port=9998/tcp
sudo firewall-cmd --permanent --add-port=9999/udp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

### Termux (Android)

Termux tidak menyediakan perintah firewall yang setara dengan UFW; Android umumnya tidak mengizinkan aplikasi biasa mengubah aturan firewall. Tidak ada command `ufw` yang perlu dijalankan. Jika Android menjadi hotspot, jalankan worker di Android dan hubungkan Arch Linux sebagai klien Wi-Fi ke hotspot tersebut. Pastikan hotspot/router tidak mengaktifkan client/AP isolation. Root diperlukan untuk mengubah aturan firewall tingkat sistem secara manual.

Periksa alamat interface dan rute di Termux:

```sh
ip -4 addr
ip route
```

Periksa alamat dan rute di Arch:

```sh
ip -4 addr
ip route
```

Pastikan alamat kedua perangkat berada pada subnet yang sama. Gunakan alamat IPv4 Android yang ditampilkan di Termux pada perintah `add <IP>` jika broadcast discovery/TCP sweep tetap tidak menemukan worker.

### Windows (PowerShell sebagai Administrator)

```powershell
New-NetFirewallRule -DisplayName "Tema13 Worker TCP 9998" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9998 -Profile Private,Domain
New-NetFirewallRule -DisplayName "Tema13 Worker UDP 9999" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 9999 -Profile Private,Domain
Get-NetFirewallRule -DisplayName "Tema13 Worker *"
```

Gunakan profil `Private` untuk jaringan lab/rumah yang dipercaya. Jika jaringan yang digunakan berprofil Public, ubah `-Profile Private,Domain` menjadi `-Profile Any` hanya bila memang diperlukan dan diizinkan oleh kebijakan jaringan. Di master tidak perlu membuka port inbound untuk komunikasi task; master membuat koneksi keluar ke worker.

## Skenario dan butir evaluasi

Menu master menyediakan sequential baseline, local multiprocessing, distributed processing, perbandingan pembagian statis/dinamis, simulasi worker gagal dengan retry lokal, dan scalability untuk 1/2/4/6/9 worker. Pada scalability, master lokal ikut sebagai node pemroses; skenario worker yang jumlahnya belum tersedia dilewati. Untuk memenuhi pengujian fisik sesuai PDF diperlukan 1 master dan 9 worker.

Hasil menampilkan waktu eksekusi, throughput, speedup dan efficiency bila ada baseline, jumlah node, status UP/DOWN, latency rata-rata/minimum/maksimum, packet loss, serta informasi CPU dan peak memory master yang tersedia pada platform. Worker mencetak progres target. Simulasi fault tolerance melaporkan waktu retry/recovery lokal. Catat juga penggunaan CPU/memori tiap node dari OS saat percobaan untuk analisis cluster; metrik lokal master saja bukan pengukuran agregat seluruh node.

## Interpretasi dan batasan

- `UP` berarti satu atau lebih probe ICMP menerima balasan; `DOWN` berarti semua probe gagal/timeout. Ping yang diblokir firewall juga dapat tampak `DOWN`.
- Worker discovery memakai UDP `9999`; informasi dan tugas dikirim melalui TCP `9998`. TCP sweep memindai subnet lokal yang terdeteksi untuk mencari worker.
- Setiap worker memakai `ProcessPoolExecutor` untuk memproses target secara paralel. Static membagi daftar target merata; dynamic memberikan batch berikutnya ke node yang lebih dulu selesai.
- Jika worker gagal, task-nya dimasukkan kembali dengan retry pada master lokal. Untuk laporan, dokumentasikan topologi, konfigurasi node/jaringan, hasil percobaan terkontrol, dan analisis tiap metrik. Video demonstrasi harus menunjukkan minimal 10 node fisik sesuai PDF.
