# Panduan Setup Tema 13

Panduan ini menyiapkan master dan worker pada Windows atau Linux. Worker harus menjalankan versi `worker.py` yang sama dengan `master.py`; semua file Python proyek, termasuk `process_metrics.py`, harus tersedia di setiap node. Program memakai satu subnet Wi-Fi/hotspot untuk menemukan worker. IP worker yang ditemukan otomatis menjadi target monitoring.

## Persiapan jaringan

1. Hubungkan semua node ke Wi-Fi/hotspot yang sama.
2. Pastikan router/hotspot tidak mengaktifkan AP/client isolation.
3. Pada setiap worker, izinkan koneksi masuk TCP `9998` dan UDP `9999`.
4. Pastikan target mengizinkan ICMP echo request agar status dan RTT ping dapat diukur.

TCP `9998` membawa permintaan info dan task. UDP `9999` dipakai master untuk discovery worker. Master membuka koneksi keluar; aturan inbound tersebut terutama dipasang pada worker.

## Windows

Jalankan PowerShell sebagai Administrator untuk aturan firewall. Jalankan bagian Python di terminal biasa dari folder proyek.

### 1. Pasang Python dan dependensi

Pasang Python 3 dari python.org dengan launcher `py`, lalu buka PowerShell di folder proyek yang berisi `master.py`, `worker.py`, `process_metrics.py`, dan `requirements.txt`.

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Jika aktivasi virtual environment ditolak oleh execution policy, izinkan hanya pada sesi PowerShell saat ini, lalu aktifkan kembali:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Ulangi setup dependensi pada setiap node Windows. Buka terminal baru dan aktifkan `.venv` kembali sebelum menjalankan program.

### 2. Buka firewall worker

Pada setiap komputer Windows yang menjalankan `worker.py`, jalankan PowerShell sebagai Administrator:

```powershell
New-NetFirewallRule -DisplayName "Tema13 Worker TCP 9998" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9998 -Profile Private,Domain
New-NetFirewallRule -DisplayName "Tema13 Worker UDP 9999" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 9999 -Profile Private,Domain
New-NetFirewallRule -DisplayName "Tema13 Worker ICMPv4 Echo" -Direction Inbound -Action Allow -Protocol ICMPv4 -IcmpType 8 -Profile Private,Domain
Get-NetFirewallRule -DisplayName "Tema13 Worker *"
```

Rule TCP/UDP mengizinkan master menemukan dan mengirim task ke worker. Rule ICMP mengizinkan probe ping. Periksa profil jaringan:

```powershell
Get-NetConnectionProfile
```

Rule di atas berlaku untuk profil `Private` dan `Domain`. Tandai Wi-Fi sebagai `Private` hanya jika itu jaringan tepercaya; jika kebijakan lab mengharuskan profil `Public`, sesuaikan profil rule firewall dengan kebijakan tersebut.

### 3. Jalankan worker dan master

Di setiap worker, dari folder proyek dan setelah virtual environment diaktifkan:

```powershell
python worker.py
```

Banner worker harus menunjukkan protokol `tema13-network-monitor-worker-v1`. Biarkan terminal worker tetap berjalan.

Di master, buka PowerShell lain di folder proyek, aktifkan `.venv`, lalu:

```powershell
python master.py
```

Untuk membuka port worker dengan `netsh` sebagai alternatif, gunakan Administrator:

```powershell
netsh advfirewall firewall add rule name="Tema13 Worker TCP 9998" dir=in action=allow protocol=TCP localport=9998
netsh advfirewall firewall add rule name="Tema13 Worker UDP 9999" dir=in action=allow protocol=UDP localport=9999
```

## Linux

Contoh berikut mencakup Arch Linux (termasuk setup yang cocok untuk master Arch) dan Ubuntu/Debian. Gunakan folder proyek yang sama pada semua node.

### Arch Linux

Pasang Python, pip, dan UFW bila belum tersedia:

```sh
sudo pacman -S python python-pip ufw
```

Siapkan dependensi pada setiap node:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Pada setiap worker Arch, tambahkan rule firewall lalu aktifkan UFW:

```sh
sudo ufw allow 9998/tcp
sudo ufw allow 9999/udp
sudo ufw status verbose
sudo systemctl enable --now ufw.service
```

Jika UFW sudah aktif, rule langsung berlaku. Pastikan tidak ada pengelola firewall lain yang mengganti rule secara bersamaan.

### Ubuntu/Debian

Pasang Python, venv, pip, dan UFW bila belum tersedia:

```sh
sudo apt update
sudo apt install python3 python3-venv python3-pip ufw
```

Siapkan dependensi pada setiap node:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Pada setiap worker, buka port:

```sh
sudo ufw allow 9998/tcp
sudo ufw allow 9999/udp
sudo ufw status verbose
sudo ufw enable
```

### Fedora/RHEL dengan firewalld

Pada setiap worker:

```sh
sudo firewall-cmd --permanent --add-port=9998/tcp
sudo firewall-cmd --permanent --add-port=9999/udp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

Pasang Python dan buat virtual environment menggunakan package manager distro jika belum ada. Setelah dependensi tersedia:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Jalankan worker/master di Linux

Di setiap worker, aktifkan environment lalu jalankan:

```sh
source .venv/bin/activate
python worker.py
```

Di master, terminal lain:

```sh
source .venv/bin/activate
python master.py
```

## Android Termux sebagai worker

Termux tidak memakai UFW. Pasang Python dan siapkan dependensi:

```sh
pkg install python
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Jalankan worker:

```sh
python worker.py
```

Hubungkan master ke hotspot Android yang sama. Android biasa tidak menyediakan command firewall untuk membuka port; komunikasi bisa tetap dibatasi oleh pengaturan hotspot/AP isolation atau kebijakan perangkat. Pastikan banner worker menampilkan protokol versi terbaru.

## Pemeriksaan koneksi

Di Linux, uji TCP dari master ke IP worker:

```sh
nc -vz <IP-WORKER> 9998
```

Di PowerShell:

```powershell
Test-NetConnection <IP-WORKER> -Port 9998
```

Jika TCP berhasil tetapi worker tidak muncul, periksa banner protokol, pastikan master dan worker memakai source terbaru, dan gunakan `add <IP-WORKER>` pada prompt pemilihan node. Untuk skenario tugas penuh siapkan 1 master dan 9 worker fisik.
