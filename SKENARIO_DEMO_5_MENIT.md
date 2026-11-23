# Skenario Video Demonstrasi Tema 13 (Maksimal 5 Menit)

PDF mensyaratkan video MP4 berdurasi maksimal 5 menit sebagai bukti sistem berjalan pada minimal 10 node fisik: 1 master dan 9 worker. Gunakan alur di bawah sebagai rundown. Rekam perangkat dan hasil yang benar-benar dijalankan; jangan menambahkan node atau hasil simulasi seolah-olah fisik.

## Persiapan sebelum merekam

- Siapkan **1 komputer master + 9 perangkat worker fisik**; catat hostname dan IP masing-masing.
- Hubungkan semuanya ke Wi-Fi/hotspot yang sama dan pastikan tidak ada client/AP isolation.
- Pasang source code terbaru serta `psutil` di semua node. Pastikan firewall worker mengizinkan TCP `9998` dan UDP `9999`, dan ICMP ping dapat dijawab.
- Jalankan `worker.py` di sembilan worker dan biarkan prosesnya aktif. Atur terminal supaya hostname/protokol worker terlihat.
- Siapkan master dengan terminal dan direktori proyek; tutup jendela lain yang tidak diperlukan.
- Pilih target/probe yang membuat proses selesai dalam waktu demonstrasi. Pengaturan awal yang disarankan: 1 probe per IP dan timeout 1 detik.
- Pastikan hasil sebelumnya tidak membingungkan. Program membuat file hasil baru di `hasil/` setiap kali dijalankan.

## Rundown video

| Waktu | Gambar yang direkam | Narasi/tindakan |
|---|---|---|
| 0:00–0:25 | Judul proyek dan tampilan topologi/perangkat | “Ini Distributed Network Monitoring Tema 13 dengan arsitektur satu master dan sembilan worker.” Sebutkan bahwa semua perangkat terhubung pada jaringan yang sama. |
| 0:25–1:05 | Tampilkan worker berjalan; pan kamera atau tampilkan konsol worker secara singkat | Tunjukkan sembilan perangkat fisik. Sorot beberapa banner worker yang menampilkan hostname dan protokol `tema13-network-monitor-worker-v1`. Katakan bahwa seluruh worker sudah aktif. |
| 1:05–1:35 | Terminal master | Jalankan `python master.py --evaluasi`, pilih mode `1`, lalu tekan Enter untuk semua node. Masukkan `1` untuk jumlah probe dan `1` untuk timeout jika diminta. Tunjukkan master menemukan worker dan menjadikan seluruh IP worker terdeteksi sebagai target. |
| 1:35–3:45 | Hasil proses master dan aktivitas worker | Biarkan baseline sequential, local parallel, dan distributed dinamis selesai. Tunjukkan status UP/DOWN, RTT, packet loss, waktu, speedup/efficiency, throughput, serta CPU/RAM. Pada layar worker, sorot notifikasi saat menerima dan menyelesaikan task. |
| 3:45–4:25 | File hasil | Buka file yang dilaporkan master, biasanya `hasil/hasil_monitoring.txt`. Tunjukkan hasil per IP, ringkasan metrik, analisis, dan konfigurasi run tersimpan. |
| 4:25–4:55 | Penutup/topologi kembali | Ringkas bahwa task dibagi ke node, diproses paralel/terdistribusi, dan hasil dikumpulkan kembali. Akhiri sebelum 5 menit. |

Jika proses melebihi waktu, potong jeda saat menunggu dan tampilkan bagian hasil yang relevan dari rekaman run yang sama. Jangan mempercepat atau mengubah angka hasil tanpa memberi keterangan.

## Command singkat

Pada setiap worker Linux/Termux:

```sh
source .venv/bin/activate
python worker.py
```

Pada setiap worker Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python worker.py
```

Untuk demo singkat, gunakan mode evaluasi `1` agar hanya satu run monitoring yang dijalankan. Perintah normal `python master.py` menjalankan 10 pengulangan benchmark dan dapat melebihi batas video 5 menit.

Di master Linux:

```sh
source .venv/bin/activate
python master.py --evaluasi
```

Pilih `1` pada menu.

Di master Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python master.py --evaluasi
```

Pilih `1` pada menu.

Alur normal menjalankan benchmark 10 kali dan dapat melebihi batas video 5 menit. Untuk video, gunakan mode evaluasi `1` agar satu run selesai dalam durasi demonstrasi. Pengujian statis-vs-dinamis, fault tolerance, serta variasi scalability 1/2/4/6/9 worker dapat direkam atau dilaporkan terpisah melalui `python master.py --evaluasi`.

## Checklist sebelum mengumpulkan

- [ ] Durasi video MP4 tidak lebih dari 5 menit.
- [ ] Terlihat 1 master dan 9 worker fisik.
- [ ] Worker aktif dan master menemukan worker pada run yang direkam.
- [ ] Ada hasil monitoring dari run tersebut: status, RTT, dan packet loss.
- [ ] Metrik performa dan file hasil ditunjukkan.
- [ ] Narasi sesuai dengan proses dan hasil nyata.
