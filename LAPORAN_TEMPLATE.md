# Laporan Proyek Tema 13: Distributed Network Monitoring

> Template ini belum berisi hasil eksperimen. Ganti seluruh bagian `[isi ...]` dengan data dan analisis dari pengujian kelompok; jangan mengisi angka perkiraan seolah hasil pengukuran.

## Identitas Kelompok

- Mata kuliah: Komputasi Paralel dan Sistem Terdistribusi
- Anggota (3 mahasiswa): [isi nama/NIM]
- Kelas/kelompok: [isi]
- Dosen: [isi]
- Tanggal pengujian: [isi]

## BAB I. Pendahuluan

### 1.1 Latar Belakang

[Jelaskan kebutuhan memantau konektivitas banyak alamat IP dan alasan pemrosesan paralel/terdistribusi berguna untuk kasus ini.]

### 1.2 Tujuan

[Tuliskan tujuan mengukur status koneksi, latency, packet loss, serta mengevaluasi sequential, local parallel, distributed, load balancing, fault tolerance, dan scalability.]

## BAB II. Studi Pustaka

### 2.1 Landasan Teori

[Jelaskan ICMP echo/ping, latency RTT, packet loss, multiprocessing, arsitektur master–worker, dynamic load balancing, fault tolerance, speedup, efficiency, throughput, CPU utilization, dan memory utilization.]

### 2.2 Sumber

[Cantumkan sumber resmi/primer untuk protokol, pustaka, rumus, dan aset yang digunakan. Sertakan judul, organisasi/penulis, URL, dan tanggal akses.]

## BAB III. Metodologi

### 3.1 Rancangan Percobaan

- Kasus: pemantauan konektivitas IP worker pada jaringan Wi-Fi/hotspot.
- Jumlah probe per IP: [isi]
- Timeout probe: [isi]
- Pengulangan setiap skenario: [isi]
- Kondisi jaringan dan waktu pengujian: [isi]
- Target monitoring: [daftar/rentang IP yang dipantau]

### 3.2 Arsitektur dan Topologi

[Sertakan diagram topologi dan jelaskan master, worker, UDP discovery port 9999, TCP task port 9998, serta alur pembagian dan pengumpulan hasil.]

### 3.3 Mekanisme Kerja

[Jelaskan task decomposition per IP, multiprocessing pada node, pembagian statis/dinamis, penanganan kegagalan dan retry, serta cara menghitung metrik.]

Rumus yang digunakan:

- Speedup = waktu sequential / waktu paralel
- Efficiency = speedup / jumlah node pemroses × 100%
- Throughput = jumlah target selesai / waktu eksekusi
- Packet loss = probe hilang / probe terkirim × 100%
- Recovery time = waktu dari deteksi kegagalan sampai task retry selesai

### 3.4 Konfigurasi Node dan Jaringan

| Peran | Hostname | OS/perangkat | CPU/core | RAM | IP | Keterangan |
|---|---|---|---:|---:|---|---|
| Master | [isi] | [isi] | [isi] | [isi] | [isi] | |
| Worker 1–9 | [isi per node] | [isi] | [isi] | [isi] | [isi] | |

## BAB IV. Hasil dan Pembahasan

### 4.1 Implementasi

[Jelaskan implementasi master, worker, protokol komunikasi, multiprocessing, load balancing, dan fault tolerance.]

### 4.2 Hasil Pengukuran

Catat hasil aktual dari setiap skenario. Jalankan beberapa pengulangan dan laporkan nilai yang digunakan (misalnya rata-rata), variasinya, dan kondisi pengujian.

| Skenario | Worker | Waktu (s) | Speedup | Efficiency (%) | Throughput (IP/s) | CPU (%) | RAM (%) | Recovery (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sequential | 0 | [isi] | 1.00 | — | [isi] | [isi] | [isi] | — |
| Local parallel | 0 | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | — |
| Distributed | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | — |
| Static balancing | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | — |
| Dynamic balancing | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | — |
| Fault tolerance | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] |

| Worker untuk scalability | Waktu (s) | Speedup | Efficiency (%) | Throughput (IP/s) | CPU (%) | RAM (%) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] |
| 2 | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] |
| 4 | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] |
| 6 | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] |
| 9 | [isi] | [isi] | [isi] | [isi] | [isi] | [isi] |

Ringkasan konektivitas:

| Target IP | Status | RTT avg/min/max (ms) | Probe terkirim/diterima | Packet loss (%) |
|---|---|---|---:|---:|
| [isi] | [UP/DOWN] | [isi] | [isi] | [isi] |

### 4.3 Analisis Data

[Bahas hasil setiap skenario: perbedaan waktu, speedup/efficiency, throughput, penggunaan CPU/RAM, distribusi beban statis vs dinamis, recovery time, dan tren scalability. Jelaskan hasil yang tidak sesuai harapan beserta faktor jaringan/perangkat.]

## BAB V. Kesimpulan

[Jawab tujuan proyek berdasarkan hasil terukur. Cantumkan keterbatasan, misalnya ICMP diblokir, variasi hotspot, atau jumlah node.]

## Lampiran

- Source code: arsip `Tema13_NetworkMonitoring_source.zip`.
- Bukti konfigurasi jaringan dan node: [isi nama lampiran].
- Video demonstrasi maksimal 5 menit, MP4, menampilkan 1 master dan 9 worker fisik: [isi nama file/lokasi].
- Log atau screenshot hasil pengujian: [isi].
