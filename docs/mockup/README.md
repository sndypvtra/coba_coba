# Mockup webapp — gambaran halaman untuk presentasi

Sebelas gambar 16:9 (3200×1800) tentang webapp yang membungkus pipeline dwell time
(project 05) menjadi produk: Live Ops, analytics, banding outlet, setup kamera,
alert WhatsApp, dan dua bidang akses — pelanggan dan platform. Nama kerja
**Denyut** hanyalah placeholder; ganti sebelum dipakai di depan orang.

Gambar-gambarnya statis. Ini bukan prototipe yang bisa diklik.

| File | Halaman | Untuk | Fungsinya |
|---|---|---|---|
| `00-peta-halaman` | Peta halaman | — | seluruh halaman, siapa yang melihatnya, dan tiga prinsip isolasi |
| `01-hari-ini` | Hari ini | Owner, Admin, Manager | lima angka kunci dan temuan yang perlu tindakan, tiap angka dengan lencana keandalannya |
| `02-live-ops` | Live Ops | Manager, Viewer (TV) | kondisi outlet detik ini: denah anonim, zona, kejadian, video on-site opsional |
| `03-analytics` | Analytics | Owner, Admin, Analyst | okupansi jam×hari, beban vs staf, okupansi meja, alur pelanggan |
| `04-banding-outlet` | Banding Outlet | Owner, Admin pusat | peringkat 12 outlet, anomali minggu ini, sebaran skor |
| `05-kamera-zona` | Kamera & Zona | Admin, Installer | pasang kamera, gambar zona di atas snapshot, validasi hitungan |
| `06-alert-laporan` | Alert & Laporan | Owner, Admin, Manager | aturan otomatis, laporan WhatsApp, jadwal ringkasan |
| `07-pengguna-role` | Pengguna & Role | Owner, Admin | undang pengguna, hak akses per role dan per outlet, keamanan akun |
| `08-privasi-audit` | Privasi & Audit | Owner | kontrol data, izin akses Support, log audit |
| `09-superadmin-tenant` | Tenant & Paket | Super Admin | seluruh pelanggan, paket dan hak fitur, permohonan akses |
| `10-superadmin-armada` | Armada Edge & Model | Super Admin | perangkat di lokasi, rilis engine bertahap dengan gerbang kualitas |

## Apa yang nyata, apa yang ilustrasi

**Nyata**, diambil dari project 05:

- Gambar kamera di `02-live-ops` adalah keluaran engine pada klip uji (frame terakhir
  `docs/scene5-dwell.jpg`, dipotong ke area video).
- `05-kamera-zona` memakai frame mentah dari klip yang sama, dengan dua zona yang
  digambar persis seperti di `config.py`: cermin dinding (dikecualikan) dan area
  pelayan (layanan). Zona antre yang sedang digambar hanya ilustrasi.
- Hitungan 8 orang (7 pelanggan dan 1 petugas) di `02` dan `05` adalah isi frame itu.

**Ilustrasi**: semua angka lain, nama tenant, pengguna, outlet, perangkat, dan domain.
Setiap gambar membawa tulisan "MOCKUP · data ilustrasi" di sudut kanan bawah. Jangan
menyajikan angka di gambar sebagai traksi atau hasil pengukuran.

**Dua hal untuk dijaga saat dipresentasikan**

- "Live" adalah target arsitektur. Engine hari ini memproses klip secara batch
  (±1,2 detik per frame di CPU, sekitar 6× lebih lambat dari real time pada 5 fps).
  Jangan menyebut angka latensi sebelum diukur di GPU.
- Frame berasal dari dataset CAFE (riset). Periksa lisensinya sebelum dipakai di
  materi komersial; ada orang di dalam frame.

## Membuat ulang

```bash
python tools/build_mockups.py                 # semua halaman -> docs/mockup/
python tools/build_mockups.py --only 01 03    # sebagian saja
python tools/build_mockups.py --scale 1       # pratinjau cepat 1600x900
```

Halaman ditulis sebagai HTML/CSS/SVG di `tools/mockup/pages.py` dan digambar dengan
Chromium headless. Font dan ikon diunduh sekali ke `tools/.mockup_cache` lalu
ditanam di halaman: Inter (SIL OFL), Lucide (ISC), dan Iconify untuk logo merek
(milik pemiliknya masing-masing). Palet dan aturan grafik mengikuti referensi dataviz:
satu hue untuk magnitudo, warna status hanya untuk status, tanpa sumbu ganda.
