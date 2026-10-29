# SmartDesk — Pemantau Fokus Belajar

Proyek IoT untuk memantau kondisi lingkungan dan aktivitas saat belajar menggunakan dua HP Android sebagai *edge device*, MQTT cloud broker, dan dashboard web. SmartDesk dirancang dengan dua alternatif implementasi, yaitu menggunakan Python dan Termux:API atau menggunakan browser web secara langsung. Kedua alternatif menerapkan pemrosesan data sensor di perangkat (*edge computing*) dan menggunakan MQTT untuk mengirim telemetri ke dashboard.

## 1. Tujuan dan Konsep Proyek

SmartDesk bertujuan menyediakan indikator pendukung suasana belajar melalui dua parameter:

- **Kondisi cahaya:** memantau intensitas cahaya di sekitar tempat belajar.
- **Aktivitas gerakan:** mengukur perubahan percepatan untuk memperkirakan tingkat aktivitas perangkat.

Dashboard menggabungkan data dari kedua sensor untuk menampilkan status pemantauan. Sistem ini tidak dapat memastikan seseorang benar-benar sedang belajar hanya berdasarkan sensor, sehingga hasilnya digunakan sebagai indikator, bukan kesimpulan pasti.

## 2. Dua Alternatif Implementasi

### Ide 1 — SmartDesk dengan Python dan Termux:API

Pada alternatif pertama, HP Android menjalankan program Python melalui Termux. Sensor dibaca menggunakan Termux:API, data diproses di perangkat, kemudian hasilnya dikirim ke broker MQTT. Dashboard web pada laptop menerima data dan mengirim perintah ARM/DISARM.

**Arsitektur:**

```text
HP A — Sensor Cahaya
Termux:API → edge_light.py
                    │
                    ▼
               MQTT Broker
                    ▲
                    │
HP B — Sensor Gerak │
Termux:API → edge_motion.py
                    │
                    ▼
             Dashboard Web
                  Laptop
```

**Karakteristik:**
- HP A membaca sensor cahaya fisik dan menghitung moving average Lux.
- HP B membaca accelerometer dan menghitung RMS percepatan dinamis.
- Python dan Termux:API digunakan untuk membaca serta memproses data sensor.
- Dashboard berlangganan (*subscribe*) pada topik telemetri dan mengirim perintah kontrol melalui MQTT.
- Program pada HP dapat menerima perintah ARM/DISARM dari dashboard.

### Ide 2 — SmartDesk berbasis Web dan Browser Sensor

Pada alternatif kedua, HP tidak perlu menjalankan Python atau Termux. Halaman web bertindak sebagai aplikasi sensor: browser membaca sensor yang tersedia dan mengirim data secara langsung ke broker MQTT menggunakan MQTT.js melalui secure WebSocket.

**Arsitektur:**

```text
HP A — Sensor Cahaya
Browser → Pemrosesan Cahaya ─────┐
                                 │
                                 ▼
                            MQTT Broker
                                 ▲
                                 │
HP B — Sensor Gerak               │
Browser → Pemrosesan Gerak ───────┘
                                 │
                                 ▼
                         Dashboard Monitor
                              Laptop
```

**Karakteristik:**
- HP A menggunakan Ambient Light Sensor jika tersedia. Jika tidak, implementasi dapat menggunakan estimasi kecerahan dari kamera.
- HP B membaca data gerakan melalui DeviceMotionEvent jika didukung browser dan perangkat.
- Pemrosesan data dilakukan menggunakan JavaScript di browser.
- MQTT.js mengirim telemetri langsung ke broker melalui secure WebSocket.
- Laptop menjalankan dashboard monitor yang menerima data dari kedua HP.
- Sensor browser umumnya membutuhkan akses melalui HTTPS dan izin sensor yang sesuai.

**Batasan:** estimasi kecerahan kamera menggunakan skala 0–255 dan bukan pengukuran Lux fisik. Dukungan sensor pada browser juga bergantung pada perangkat, browser, izin, dan kondisi sistem operasi.

## 3. Perbandingan Kedua Ide

| Aspek | Ide 1: Python | Ide 2: Web |
|---|---|---|
| Pembacaan sensor | Termux:API | API sensor browser |
| Bahasa utama | Python | JavaScript |
| Aplikasi HP | Termux dan Termux:API | Browser |
| Pemrosesan data | Program Python di HP | JavaScript di browser |
| Pengiriman MQTT | Paho-MQTT melalui TLS | MQTT.js melalui secure WebSocket |
| Dashboard | Web pada laptop | Web pada laptop atau perangkat lain |
| Ketergantungan | Python, Termux, dan izin sensor | Browser yang mendukung sensor dan HTTPS |
| Sensor cahaya | Sensor fisik yang terdeteksi Termux:API | Ambient Light Sensor atau estimasi kamera |
| Keterbatasan utama | Pengaturan lingkungan Python dan akses sensor | Dukungan API browser dan aktivitas latar belakang |

Kedua alternatif menggunakan prinsip yang sama, yaitu membaca data sensor, memproses data di perangkat, dan mengirim hasil melalui MQTT. Perbedaan utamanya terletak pada cara perangkat mengakses sensor dan menjalankan pemrosesan.

## 4. Arsitektur MQTT

Kedua alternatif menggunakan HiveMQ Public Broker. Karena broker ini bersifat publik, setiap kelompok harus menggunakan Project ID yang unik dan tidak mengirimkan data pribadi.

Broker menggunakan koneksi TLS untuk program Python dan secure WebSocket untuk browser.

### Topik MQTT

Gunakan format topik berikut:

- Telemetri cahaya: `smartdesk/<PROJECT_ID>/edge/light/telemetry`
- Telemetri gerakan: `smartdesk/<PROJECT_ID>/edge/motion/telemetry`
- Kontrol: `smartdesk/<PROJECT_ID>/control`

Pada alternatif Python, HP A dan HP B melakukan *publish* telemetri, sedangkan dashboard melakukan *subscribe* dan mengirim perintah kontrol. Pada alternatif web, halaman sensor melakukan *publish* langsung dari browser dan dashboard monitor melakukan *subscribe* pada topik telemetri.

`PROJECT_ID` harus sama pada semua perangkat dalam satu kelompok. `DEVICE_ID` digunakan untuk membedakan perangkat, misalnya `hpA` dan `hpB`.

### Contoh payload

Telemetri cahaya:

```json
{
  "device_id": "hpA",
  "lux": 245.2,
  "lux_avg": 278.4,
  "window": 5,
  "sent_at_ms": 1790000000000
}
```

Telemetri gerakan:

```json
{
  "device_id": "hpB",
  "motion_rms": 0.91,
  "window": 5,
  "sent_at_ms": 1790000000000
}
```

Perintah kontrol:

```json
{
  "command": "ARM",
  "sent_at_ms": 1790000000000
}
```

Struktur payload dapat disesuaikan dengan implementasi yang digunakan. Nama field dan satuan harus konsisten antara pengirim dan dashboard.

## 5. Algoritma Pemrosesan Data

### Moving Average Cahaya

Pada implementasi Python, sistem menyimpan hingga N pembacaan Lux terakhir. Rata-rata bergerak dihitung dengan rumus:

```text
lux_avg = sum(window_lux) / len(window_lux)
```

Status cahaya ditandai **BURUK** jika `lux_avg < LUX_THRESHOLD`. Nilai awal ambang adalah 300 Lux dan dapat disesuaikan berdasarkan pengujian.

Pada implementasi web, algoritma moving average digunakan untuk nilai Lux jika Ambient Light Sensor tersedia. Jika menggunakan kamera, sistem menghitung estimasi kecerahan berbasis gambar dan bukan Lux fisik.

### RMS Percepatan Dinamis

Data accelerometer berupa komponen percepatan pada sumbu x, y, dan z. Pada implementasi Python, percepatan dinamis dihitung dengan:

```text
dynamic = sqrt(x*x + y*y + z*z) - 9.81
```

Nilai RMS pada satu window dihitung dengan:

```text
motion_rms = sqrt(mean(dynamic**2))
```

Status aktivitas ditandai **TINGGI** jika RMS melebihi `MOTION_RMS_THRESHOLD`. Nilai awal ambang adalah 0,7 m/s², bukan standar universal.

Implementasi web menggunakan DeviceMotionEvent dan memproses data gerakan dengan pendekatan RMS pada window sampel. Detail perhitungan perlu disesuaikan dengan bentuk data percepatan yang disediakan browser.

### Rule-Based Fusion pada Dashboard

Dashboard menggabungkan data sensor dengan aturan berikut:

1. **DISARMED:** pemantauan dinonaktifkan.
2. **AKTIVITAS TINGGI:** sistem dalam keadaan ARM dan RMS gerakan melampaui ambang.
3. **CAHAYA BURUK:** sistem dalam keadaan ARM dan nilai cahaya berada di bawah ambang.
4. **TERPANTAU:** sistem dalam keadaan ARM, aktivitas tidak tinggi, dan kondisi cahaya memadai.
5. **MENUNGGU DATA:** telemetri dari salah satu perangkat belum diterima.

Urutan prioritas aturan harus konsisten dalam implementasi dashboard agar status tidak saling bertentangan.

## 6. Kebutuhan Sistem

### Untuk Ide 1 — Python dan Termux:API

- Dua HP Android dengan sensor cahaya dan accelerometer yang sesuai.
- Termux dan Termux:API.
- Python 3.10 atau lebih baru.
- Library `paho-mqtt` dan `python-dotenv`.
- Laptop dengan browser modern.
- Koneksi internet untuk mengakses broker MQTT.

Instalasi pada Termux:

```bash
pkg update
pkg install python termux-api
pip install paho-mqtt python-dotenv
```

Buat file `.env` berdasarkan `.env.example`, kemudian isi `PROJECT_ID` yang sama pada kedua HP dan `DEVICE_ID` yang berbeda.

Periksa sensor yang tersedia:

```bash
termux-sensor -l
termux-sensor -s LIGHT -n 1
termux-sensor -s ACCELEROMETER -n 1
```

Nama sensor yang digunakan harus sesuai dengan hasil pemeriksaan perangkat.

### Untuk Ide 2 — Browser Sensor

- Dua HP Android dengan browser modern.
- Dukungan sensor yang diperlukan pada browser dan perangkat.
- Laptop atau perangkat untuk dashboard monitor.
- Hosting HTTPS, misalnya GitHub Pages.
- Koneksi internet.
- Izin sensor atau kamera sesuai kebutuhan.

Tidak diperlukan instalasi Python, Termux, atau Termux:API pada HP. Seluruh halaman web menggunakan Project ID yang sama, sedangkan Device ID membedakan perangkat.

## 7. Cara Menjalankan

### Ide 1 — Python dan Termux:API

1. Salin proyek ke kedua HP dan buat file `.env`.
2. Jalankan `python edge_light.py` pada HP A.
3. Jalankan `python edge_motion.py` pada HP B.
4. Pada laptop, buka direktori proyek dan jalankan:

   ```bash
   python -m http.server 8000 --bind 0.0.0.0
   ```

5. Buka dashboard melalui `http://localhost:8000/dashboard/` pada laptop.
6. Masukkan Project ID yang sama, lalu klik Connect.
7. Uji telemetri sensor serta perintah ARM/DISARM.

Jika dashboard perlu dibuka dari perangkat lain melalui jaringan lokal, gunakan IP lokal laptop, misalnya `http://192.168.1.10:8000/dashboard/`. Akses sensor browser pada koneksi HTTP dari perangkat lain mungkin dibatasi; hal ini terutama relevan jika dashboard juga menggunakan sensor browser.

### Ide 2 — Browser Sensor

1. Publikasikan halaman dashboard melalui hosting HTTPS.
2. Buka halaman yang sama pada HP A, HP B, dan laptop.
3. Pada HP A, pilih **HP A — Sensor cahaya**, gunakan Device ID `hpA`, lalu klik Connect MQTT dan Mulai baca sensor.
4. Pada HP B, pilih **HP B — Sensor gerak**, gunakan Device ID `hpB`, lalu klik Connect MQTT dan Mulai baca sensor.
5. Pada laptop, pilih **Dashboard monitor**, gunakan Project ID yang sama, lalu klik Connect MQTT.
6. Berikan izin sensor atau kamera jika diminta.
7. Pastikan dashboard menerima telemetri dari kedua perangkat.

Nama opsi dan tombol mengikuti implementasi halaman web yang digunakan.

## 8. Pengujian dan Evaluasi

Lakukan pengujian berikut pada alternatif yang dipilih:

1. **Sensor cahaya:** ubah kondisi pencahayaan dan amati perubahan nilai yang dikirim. Bedakan Lux fisik dari estimasi kamera.
2. **Sensor gerakan:** bandingkan data ketika perangkat diam dan bergerak.
3. **Threshold:** uji kondisi di bawah dan di atas ambang yang ditetapkan, lalu catat nilai sensor serta status dashboard.
4. **MQTT:** pastikan telemetri kedua perangkat diterima oleh dashboard.
5. **Kontrol:** uji ARM/DISARM dan periksa apakah status pemantauan berubah sesuai implementasi.
6. **Kestabilan:** amati apakah koneksi dan pengiriman data tetap berjalan ketika browser atau aplikasi berada di latar belakang.

Catat hasil pengujian untuk mengevaluasi ketepatan indikator, respons sistem, dan keterbatasan setiap alternatif.

## 9. Keamanan dan Batasan

- HiveMQ Public Broker merupakan broker bersama. Gunakan Project ID yang unik dan jangan mengirim data sensitif.
- Penggunaan Project ID dan Device ID bukan mekanisme autentikasi.
- Pada broker publik, pihak lain yang mengetahui topik dapat berpotensi membaca atau mengirim pesan pada topik tersebut.
- Sensor browser bergantung pada dukungan perangkat, browser, izin, dan secure context.
- Sistem operasi dapat menghentikan pembacaan sensor ketika aplikasi atau browser berada di latar belakang.
- Accelerometer hanya memberikan indikator gerakan perangkat; data tersebut tidak membuktikan seseorang sedang belajar atau meninggalkan kursi.
- Ambang sensor merupakan nilai awal yang perlu dievaluasi melalui pengujian nyata.

## 10. Struktur Proyek

Struktur repository yang menggabungkan kedua alternatif dapat disusun sebagai berikut:

```text
smartdesk-iot/
├── README.md
├── .env.example
├── mqtt_common.py
├── edge_light.py
├── edge_motion.py
├── dashboard/
│   └── index.html
└── docs/
    └── index.html
```

Keterangan:

- Folder `dashboard/` pada root merupakan dashboard dari implementasi Python.
- Folder `docs/` digunakan untuk GitHub Pages jika Pages dikonfigurasi agar menerbitkan isi folder tersebut.

Kedua alternatif dapat dikembangkan dan diuji secara terpisah. Untuk demonstrasi, pilih salah satu implementasi dan pastikan pengirim serta dashboard menggunakan format payload dan topik MQTT yang sesuai.
