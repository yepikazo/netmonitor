# Distributed Network Monitoring — Tema 13

Aplikasi master–worker untuk memantau konektivitas alamat IPv4. Master menemukan worker di LAN menggunakan UDP broadcast dan TCP sweep fallback seperti pola `masterexample.py`; worker menerima tugas melalui TCP, lalu membagi target ke beberapa proses CPU. Daftar worker adalah node pemroses, sedangkan alamat IP/CIDR yang dimonitor dimasukkan operator secara eksplisit.

## Menjalankan

1. Hubungkan komputer ke LAN yang sama dan pasang Python 3. Izinkan TCP `9998` serta UDP `9999` pada firewall worker.
2. Di setiap worker jalankan `python worker.py`.
3. Di master jalankan `python master.py`, pilih skenario pengujian, jumlah probe dan timeout, lalu masukkan alamat IP/CIDR yang diizinkan.
4. Pilih worker dari daftar yang ditemukan. Tekan Enter untuk memakai seluruh node atau masukkan indeks/rentang seperti `0-3`.

Contoh target: `192.168.1.1, 192.168.1.10` atau `192.168.1.0/28`. Target CIDR dibatasi maksimal 4096 alamat. Worker yang ditemukan tidak otomatis dijadikan target monitoring.

## Skenario dan butir evaluasi

Menu master menyediakan sequential baseline, local multiprocessing, distributed processing, perbandingan pembagian statis/dinamis, simulasi worker gagal dengan retry lokal, dan scalability untuk 1/2/4/6/9 worker. Pada scalability, master lokal ikut sebagai node pemroses; skenario worker yang jumlahnya belum tersedia dilewati. Untuk memenuhi pengujian fisik sesuai PDF diperlukan 1 master dan 9 worker.

Hasil menampilkan waktu eksekusi, throughput, speedup dan efficiency bila ada baseline, jumlah node, status UP/DOWN, latency rata-rata/minimum/maksimum, packet loss, serta informasi CPU dan peak memory master yang tersedia pada platform. Worker mencetak progres target. Simulasi fault tolerance melaporkan waktu retry/recovery lokal. Catat juga penggunaan CPU/memori tiap node dari OS saat percobaan untuk analisis cluster; metrik lokal master saja bukan pengukuran agregat seluruh node.

## Interpretasi dan batasan

- `UP` berarti satu atau lebih probe ICMP menerima balasan; `DOWN` berarti semua probe gagal/timeout. Ping yang diblokir firewall juga dapat tampak `DOWN`.
- Worker discovery memakai UDP `9999`; informasi dan tugas dikirim melalui TCP `9998`. TCP sweep memindai subnet lokal yang terdeteksi untuk mencari worker.
- Setiap worker memakai `ProcessPoolExecutor` untuk memproses target secara paralel. Static membagi daftar target merata; dynamic memberikan batch berikutnya ke node yang lebih dulu selesai.
- Jika worker gagal, task-nya dimasukkan kembali dengan retry pada master lokal. Untuk laporan, dokumentasikan topologi, konfigurasi node/jaringan, hasil percobaan terkontrol, dan analisis tiap metrik. Video demonstrasi harus menunjukkan minimal 10 node fisik sesuai PDF.
