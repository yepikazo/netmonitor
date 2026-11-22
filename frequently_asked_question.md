# Frequently Asked Questions (FAQ)

## Menjalankan program

### Node mana yang menjalankan master dan worker?

Jalankan `worker.py` pada setiap worker dan biarkan prosesnya aktif. Jalankan `master.py` pada satu node master. Pengujian lengkap sesuai PDF memerlukan 1 master dan 9 worker fisik.

### Bagaimana menjalankan semua skenario pengujian?

Jalankan `python master.py --evaluasi` pada master, lalu pilih skenario dari menu. Perintah biasa `python master.py` menjalankan baseline sequential, local parallel pada master, dan distributed dengan load balancing dinamis.

### Apakah master meminta alamat target?

Tidak. Semua IP worker Tema 13 yang berhasil ditemukan otomatis menjadi target monitoring. Pilihan node pemroses menentukan komputer yang mengerjakan task dan terpisah dari daftar target.

### Bisakah program memantau IP selain worker?

Alur saat ini memantau IP worker yang ditemukan. Pemantauan IP lain memerlukan daftar target terpisah, yang belum disediakan pada alur normal.

## Discovery dan koneksi

### Port apa yang harus diizinkan?

Pada setiap worker, izinkan TCP `9998` untuk permintaan info/task dan UDP `9999` untuk discovery. Ikuti command pada [PANDUAN_SETUP.md](PANDUAN_SETUP.md). Master dan worker harus berada pada Wi-Fi/hotspot yang sama; pastikan AP/client isolation tidak menghalangi koneksi.

### Master tidak menemukan worker. Apa yang perlu diperiksa?

Pastikan worker berjalan dengan source terbaru dan banner menampilkan `tema13-network-monitor-worker-v1`. Periksa IP/subnet, rule firewall worker, dan pengaturan isolation hotspot. Jika broadcast discovery gagal, masukkan `add <IP-WORKER>` pada prompt pilihan node; master tetap memvalidasi protokolnya.

### `nc -vz <IP-WORKER> 9998` berhasil, tetapi worker tidak muncul. Kenapa?

`nc` hanya memastikan port TCP terbuka. Master juga memerlukan jawaban protokol worker Tema 13. Pastikan file `worker.py` pada perangkat tersebut versi terbaru. Jika master menampilkan prompt pemilihan node, coba `add <IP-WORKER>`.

### Apa arti `Connection refused`?

Host dapat dijangkau, tetapi tidak ada proses yang menerima koneksi pada TCP `9998`. Pastikan worker masih berjalan, IP yang diuji benar, dan tidak ada error saat worker membuka port.

## Hasil dan metrik

### Apa arti UP dan DOWN?

`UP` berarti setidaknya satu probe ICMP mendapat balasan. `DOWN` berarti semua probe gagal/timeout; firewall target yang memblokir ping juga dapat membuat status terlihat DOWN.

### Bagaimana latency dihitung?

Program membaca RTT dari output sistem `ping`, bukan durasi proses ping. Jika sistem hanya melaporkan `time<1ms`, program mencatat estimasi `0.5ms`.

### Mengapa CPU/RAM tidak tersedia?

Pasang `psutil` pada master dan setiap worker dengan `python -m pip install -r requirements.txt`, lalu jalankan ulang. Utilization diukur dari proses dan child process yang mengerjakan task.

### Di mana hasil disimpan?

Master membuat direktori `hasil/` di folder proyek dan menyimpan `hasil_monitoring.txt`. Jika nama itu sudah terpakai, nama berikutnya memakai awalan nomor, misalnya `1_hasil_monitoring.txt`, kemudian `2_hasil_monitoring.txt`.

### Mengapa target yang sama diuji beberapa kali?

Mode normal menjalankan sequential baseline, local parallel, dan distributed dinamis untuk dibandingkan. Mode `--evaluasi` juga menyediakan pembagian statis/dinamis, fault tolerance, dan scalability.

### Mengapa sebagian variasi scalability dilewati?

Program hanya menjalankan variasi 1, 2, 4, 6, atau 9 worker jika jumlah worker tersebut benar-benar tersedia/terpilih. Skenario yang dilewati bukan hasil pengukuran. Pengujian lengkap memerlukan 9 worker jaringan dan 1 master.

## Pengumpulan tugas

### Apakah menjalankan program saja sudah menyelesaikan tugas?

Belum. Isi [LAPORAN_TEMPLATE.md](LAPORAN_TEMPLATE.md) dengan data dan analisis eksperimen aktual. PDF juga meminta source code terkompresi dan video MP4 maksimal 5 menit yang menunjukkan 1 master serta 9 worker fisik. Gunakan [ALUR_PENGUJIAN.md](ALUR_PENGUJIAN.md) dan [SKENARIO_DEMO_5_MENIT.md](SKENARIO_DEMO_5_MENIT.md) sebagai panduan.
