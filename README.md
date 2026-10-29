# SmartDesk — Pemantau Fokus Belajar

Proyek IoT berbasis dua HP Android sebagai edge device, MQTT cloud broker, dan dashboard web lokal.

## Arsitektur
- **HP A:** light sensor → moving average Lux → MQTT `smartdesk/<PROJECT_ID>/edge/light/telemetry`
- **HP B:** accelerometer → RMS percepatan dinamis → MQTT `smartdesk/<PROJECT_ID>/edge/motion/telemetry`
- **MQTT broker:** HiveMQ public broker, TLS port 8883 untuk Python dan secure WebSocket port 8884 untuk browser.
- **Dashboard:** `dashboard/index.html`, disajikan dari laptop pada Wi-Fi/hotspot yang sama. Dashboard menerima telemetri dan mengirim ARM/DISARM melalui MQTT.

> Broker publik dipakai bersama. Ganti `PROJECT_ID` dengan ID unik kelompok dan jangan mengirim data pribadi. Broker publik tidak cocok untuk data rahasia.

## Kebutuhan
- Dua HP Android yang memiliki light sensor (HP A) dan accelerometer (HP B).
- Install Termux dan aplikasi Termux:API dari sumber yang kompatibel; install keduanya pada HP yang digunakan.
- Laptop dengan Python 3.10+ dan browser modern.
- Semua perangkat berada pada Wi-Fi/hotspot yang sama; internet diperlukan untuk broker cloud.

## 1. Siapkan kedua HP
Di Termux, jalankan:
```bash
pkg update
pkg install python termux-api
pip install paho-mqtt python-dotenv
```
Salin folder proyek ke kedua HP, lalu buat `.env` berdasarkan contoh:
```bash
cp .env.example .env
```
Edit `.env`, isi `PROJECT_ID` yang sama pada kedua HP, serta `DEVICE_ID` berbeda (`hpA` dan `hpB`).

Pastikan izin sensor Termux:API diberikan. Untuk memeriksa sensor yang tersedia:
```bash
termux-sensor -l
termux-sensor -s LIGHT -n 1
termux-sensor -s ACCELEROMETER -n 1
```
Nama sensor dapat berbeda antarperangkat. Gunakan nama yang ditampilkan oleh `termux-sensor -l`, lalu atur `LIGHT_SENSOR_NAME` atau `ACCEL_SENSOR_NAME` pada `.env`.

## 2. Jalankan edge devices
Di HP A:
```bash
python edge_light.py
```
Di HP B:
```bash
python edge_motion.py
```
Kedua program membaca sensor melalui Termux:API, memproses sampel di perangkat, lalu mengirim hasil olahan ke broker MQTT. Edge menerima kontrol ARM/DISARM dari dashboard.

## 3. Jalankan dashboard di laptop
Dari direktori proyek:
```bash
python -m http.server 8000 --bind 0.0.0.0
```
Cari alamat IP lokal laptop, misalnya `192.168.1.10`, lalu buka di browser laptop atau HP yang satu jaringan:
`http://192.168.1.10:8000/dashboard/`

Isi Project ID yang sama dengan `.env`, lalu klik **Connect**. Jika tidak bisa diakses, periksa firewall laptop dan pastikan klien berada di jaringan yang sama. Dashboard browser juga perlu akses internet untuk koneksi WebSocket TLS ke broker.

## 4. Algoritma
### Moving average cahaya
Simpan hingga N pembacaan Lux terakhir. Nilai rata-rata bergerak:
`lux_avg = sum(window_lux) / len(window_lux)`
Status cahaya **BURUK** jika `lux_avg < LUX_THRESHOLD` (default 300 lux; ubah sesuai lingkungan dan kebutuhan tugas).

### RMS percepatan dinamis
Untuk setiap sampel accelerometer (x, y, z), hitung magnitude dan kurangi gravitasi:
`dynamic = sqrt(x*x + y*y + z*z) - 9.81`
Dalam satu window:
`motion_rms = sqrt(mean(dynamic**2))`
Status aktivitas **TINGGI** jika RMS melampaui `MOTION_RMS_THRESHOLD` (default 0.7 m/s²). Ambang ini adalah nilai awal untuk pengujian, bukan standar universal.

### Rule-based fusion pada dashboard
- DISARMED → pemantauan dinonaktifkan.
- ARM dan RMS tinggi → `AKTIVITAS TINGGI`.
- ARM dan moving average Lux rendah → `CAHAYA BURUK`.
- ARM, aktivitas tidak tinggi, cahaya memadai → `TERPANTAU`.
- Data salah satu perangkat belum masuk → tampilkan `MENUNGGU DATA`.

Sistem tidak bisa memastikan seseorang benar-benar belajar atau meninggalkan kursi hanya dari accelerometer di saku. Gunakan label aktivitas sebagai indikator, lalu evaluasi threshold melalui pengujian nyata.

## Topic MQTT
- `smartdesk/<PROJECT_ID>/edge/light/telemetry`
- `smartdesk/<PROJECT_ID>/edge/motion/telemetry`
- `smartdesk/<PROJECT_ID>/control` (dashboard publish, edge subscribe)

## Payload contoh
```json
{"device_id":"hpA","lux":245.2,"lux_avg":278.4,"window":5,"sent_at_ms":1790000000000}
```
```json
{"device_id":"hpB","motion_rms":0.91,"window":5,"sent_at_ms":1790000000000}
```
```json
{"command":"ARM","sent_at_ms":1790000000000}
```

## Catatan pengujian
1. Pastikan telemetri HP A berubah saat sensor cahaya ditutup/dihadapkan ke sumber cahaya.
2. Pastikan RMS HP B meningkat saat HP di saku bergerak dan relatif rendah saat diam.
3. Uji cahaya di bawah dan di atas threshold; catat Lux dan status.
4. Uji ARM/DISARM dari dashboard dan pastikan status berubah.
5. Catat hasil dan batasan pada laporan/PPT.

## Struktur
```text
smartdesk-iot/
├── README.md
├── mqtt_common.py
├── edge_light.py
├── edge_motion.py
├── dashboard/                 
│   └── index.html
│
├── smartdesk-web-iot/           
│   ├── README.md
│   └── dashboard/
│       └── index.html
│
└── docs/                        
    └── index.html
```
