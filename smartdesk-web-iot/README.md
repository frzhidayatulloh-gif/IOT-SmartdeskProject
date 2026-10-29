# SmartDesk Web IoT — browser-only sensor publishing

Versi ini menggunakan **halaman web dashboard sebagai aplikasi sensor**. HP tidak perlu menjalankan `edge_light.py`, `edge_motion.py`, Termux, atau Python. Browser HP membaca sensor yang diizinkan lalu **publish langsung ke HiveMQ melalui MQTT over secure WebSocket**. Dashboard monitor melakukan **subscribe** pada topic yang sama.

## Arsitektur

```text
HP A (buka dashboard web, pilih "HP A — Sensor cahaya")
  Browser sensor cahaya / fallback kamera
  └── PUBLISH smartdesk/<PROJECT_ID>/edge/light/telemetry ─┐
                                                           │
HP B (buka dashboard web, pilih "HP B — Sensor gerak")     ├── HiveMQ MQTT broker
  Browser DeviceMotionEvent                                │
  └── PUBLISH smartdesk/<PROJECT_ID>/edge/motion/telemetry ┘
                                                           │
Laptop (buka dashboard web, pilih "Dashboard monitor")     │
  └── SUBSCRIBE smartdesk/<PROJECT_ID>/edge/+/telemetry ◄──┘
```

## Topic publish/subscribe

- HP A publish: `smartdesk/<PROJECT_ID>/edge/light/telemetry`
- HP B publish: `smartdesk/<PROJECT_ID>/edge/motion/telemetry`
- Semua dashboard subscribe: `smartdesk/<PROJECT_ID>/edge/+/telemetry`

MQTT.js dipakai di `dashboard/index.html`. Cari `client.publish(...)` untuk publish, `client.subscribe(...)` untuk subscribe, dan `client.on("message", ...)` untuk menerima pesan.

## Menjalankan

### Cara mudah: GitHub Pages (disarankan untuk sensor browser)

Sensor web umumnya memerlukan secure context HTTPS. Unggah folder `dashboard` ke repository GitHub lalu aktifkan **Settings → Pages** (deploy dari branch `main`, folder `/root` atau atur struktur repository agar `index.html` berada di root yang dipublikasikan). Jika menggunakan struktur proyek ini, paling mudah salin isi `dashboard/` ke root repository khusus GitHub Pages.

Buka URL HTTPS yang sama pada kedua HP dan laptop.

### Uji lokal

Dari folder proyek:
```bash
python -m http.server 8000
```
`http://localhost:8000/dashboard/` dapat digunakan pada perangkat yang menjalankan server itu sendiri. Untuk membuka dari HP lain melalui IP LAN, browser mungkin menolak sensor/kamera karena halaman HTTP bukan secure context. Untuk uji sensor lintas perangkat, gunakan HTTPS hosting.

## Pengaturan di dashboard

1. Isi Project ID yang unik untuk kelompok, misalnya `smartdesk-kelompok7`. Gunakan ID sama di semua perangkat.
2. HP A: pilih `HP A — Sensor cahaya`, ubah Device ID menjadi `hpA`, klik **Connect MQTT**, lalu **Mulai baca sensor**.
3. HP B: pilih `HP B — Sensor gerak`, ubah Device ID menjadi `hpB`, klik **Connect MQTT**, lalu **Mulai baca sensor**.
4. Laptop: pilih `Dashboard monitor`, gunakan Project ID sama, klik **Connect MQTT**.
5. Beri izin sensor/kamera jika browser memintanya.

## Sensor cahaya: batasan penting

Browser tidak selalu menyediakan Ambient Light Sensor fisik. Jika didukung dan diizinkan, halaman mengirim `lux` dan `lux_avg`. Jika tidak, halaman menggunakan kamera belakang untuk menghitung kecerahan rata-rata gambar dalam skala 0–255. **Estimasi kamera bukan nilai Lux** dan dapat dipengaruhi arah kamera, exposure, serta objek yang dilihat. Untuk laporan, sebut ini sebagai estimasi kecerahan berbasis kamera, bukan pengukuran lux fisik.

Sensor gerak memakai `DeviceMotionEvent`. Dukungan dan izin berbeda antar browser/perangkat. Jika data tidak muncul, coba browser modern pada HP yang mendukung sensor dan akses dashboard melalui HTTPS.

## Algoritma

- Moving average: rata-rata hingga 5 sampel terakhir.
- Motion RMS: akar dari rata-rata kuadrat nilai percepatan dinamis dalam window hingga 10 sampel.
- Ambang awal yang ditampilkan di dashboard: 300 lux dan RMS 0.7 m/s². Estimasi kamera memakai batas 80/255, yang hanya indikator kasar. Sesuaikan setelah pengujian.

## Keamanan dan pengujian

- `broker.hivemq.com` adalah broker publik. Gunakan Project ID yang unik dan jangan kirim data sensitif.
- Ini prototype untuk demonstrasi, bukan sistem autentikasi. Siapa pun yang mengetahui topic pada broker publik berpotensi mengirim pesan ke topic tersebut.
- Browser harus tetap terbuka dan sensor aktif agar pengiriman berjalan; sistem operasi dapat menghentikan aktivitas latar belakang.
- Uji masing-masing HP, pastikan log menunjukkan publish dan dashboard monitor menerima nilai.
