# Mockup webapp Outlytics — gambaran halaman untuk presentasi

Sebelas gambar 16:9 (3200×1800) tentang **Outlytics**, webapp yang membungkus pipeline
dwell time (project 05) menjadi produk: pantauan live per CCTV, analitik, perbandingan
outlet, pengaturan CCTV, notifikasi WhatsApp, dan dua sisi akses — aplikasi klien dan
panel internal. Nama "Outlytics" berasal dari *outlet* + *analytics*. Per 1 Okt 2026
belum ditemukan perusahaan atau aplikasi dengan nama itu, dan outlytics.ai, .io, serta
.id belum terdaftar (outlytics.com diparkir dan dijual). Merek di DJKI belum dicek;
alamat `app.outlytics.ai` di gambar hanya contoh sampai domainnya dibeli.

Untuk membuat deck investor dari gambar-gambar ini di Claude Design, lampirkan ke-11
gambar bersama [`prompt-claude-design.md`](prompt-claude-design.md).

Gambar-gambarnya statis. Ini bukan prototipe yang bisa diklik.

| File | Halaman | Untuk | Fungsinya |
|---|---|---|---|
| `00-peta-halaman` | Peta halaman | — | seluruh halaman, siapa yang melihatnya, dan tiga prinsip privasi |
| `01-ringkasan` | Ringkasan Hari Ini | Owner, Admin, Manager | lima angka kunci hari ini dan hal yang perlu ditindaklanjuti; tiap angka berlabel Akurat atau Estimasi |
| `02-pantauan-live` | Pantauan Live | Manager, Layar TV | kondisi outlet saat ini per CCTV: denah ruangan, antrean, kasir, kejadian, video |
| `03-analitik` | Analitik | Owner, Admin, Analis | jam ramai seminggu, tamu vs staf, pemakaian meja, perjalanan tamu |
| `04-perbandingan-outlet` | Perbandingan Outlet | Owner, Admin pusat | peringkat 12 outlet, outlet yang perlu dicek, skor semua outlet |
| `05-cctv-area` | CCTV & Area | Admin, Teknisi | sambungkan CCTV, tandai area di foto CCTV, cek akurasi hitungan |
| `06-notifikasi-laporan` | Notifikasi & Laporan | Owner, Admin, Manager | aturan otomatis, pesan WhatsApp, jadwal laporan |
| `07-tim-hak-akses` | Tim & Hak Akses | Owner, Admin | undang anggota, hak akses per peran dan per outlet, keamanan akun |
| `08-privasi-keamanan` | Privasi & Keamanan | Owner | pengaturan data, izin akses tim support, riwayat aktivitas |
| `09-superadmin-klien` | Klien & Paket | Super Admin, Support | semua klien, status teknis, paket dan harga, permintaan akses |
| `10-superadmin-perangkat` | Perangkat AI & Update | Super Admin | perangkat AI di tiap outlet, update bertahap dengan syarat lanjut |

## Apa yang nyata, apa yang ilustrasi

**Nyata**, diambil dari project 05:

- Video di `02-pantauan-live` adalah keluaran engine pada klip uji
  (`projects/05_cafe_dwell_time/docs/scene5-dwell.jpg`, dipotong ke area video).
- Denah "Ruang Utama Lt. 1" di halaman yang sama digambar dari frame itu. Titik hilang
  tepi bangku, tepi counter, dan kaki kursi dipakai untuk memproyeksikan meja dan orang
  ke lantai. Hasilnya, dinding bangku dan counter bertemu sekitar 128°, tidak siku. Karena
  itu di kamera counter tampak menyambung lurus dari ujung bangku, dan denah
  mempertahankan sudut itu. Bangku panjang 6 kursi dengan meja 1–3, empat orang di meja 2,
  satu staf di belakang counter, dan total 8 orang (7 tamu, 1 staf) sesuai frame. Posisi
  dirapikan ke ukuran meja yang wajar, jadi bisa bergeser beberapa puluh sentimeter.
- `05-cctv-area` memakai frame mentah dari klip yang sama, dengan dua area yang digambar
  persis seperti di `config.py`: cermin dinding (tidak dihitung) dan area kasir. Area
  antre yang sedang digambar adalah ilustrasi. Letaknya sama dengan di denah: di depan
  kasir dan etalase, overlap dengan area kasir.

**Ilustrasi**: semua angka lain, nama klien, pengguna, outlet, perangkat, harga paket,
dan domain. Setiap gambar membawa tulisan "MOCKUP · contoh data, bukan data asli" di
sudut kanan bawah. Jangan menyajikan angka di gambar sebagai traksi atau hasil pengukuran.

Angka antarhalaman sengaja dibuat saling cocok, jadi tidak ada yang bertentangan saat
dibandingkan:

- Ruang Utama punya 24 kursi; 6 terisi (25%), antrean 0, dan kasir ada staf.
- Ada 12 outlet. KPI jaringan di `04` dihitung dari tabelnya.
- Ada 12 klien dengan 43 outlet dan 43 perangkat AI; 11 perangkat sudah memakai versi 2.4.

Harga paket (Rp 500 rb dan Rp 1,5 jt per outlet per bulan, Enterprise sesuai kontrak)
adalah hipotesis dari konsep bisnis dan belum divalidasi.

**Dua hal untuk dijaga saat dipresentasikan**

- "Live" adalah target arsitektur. Engine hari ini memproses klip secara batch
  (±1,2 detik per frame di CPU, sekitar 6× lebih lambat dari real time pada 5 fps).
  Jangan menyebut angka latensi sebelum diukur di GPU.
- Frame berasal dari dataset CAFE (riset). Periksa lisensinya sebelum dipakai di
  materi komersial, karena ada orang di dalam frame.

## Membuat ulang

```bash
python tools/build_mockups.py                 # semua halaman -> docs/mockup/
python tools/build_mockups.py --only 01 03    # sebagian saja
python tools/build_mockups.py --scale 1       # pratinjau cepat 1600x900
```

Halaman ditulis sebagai HTML/CSS/SVG di `tools/mockup/pages.py` dan digambar dengan
Chromium headless. Font dan ikon diunduh sekali ke `tools/.mockup_cache` lalu ditanam di
halaman: Inter (SIL OFL), Lucide (ISC), dan Iconify untuk logo merek (milik pemiliknya
masing-masing). Palet dan aturan grafik mengikuti referensi dataviz: satu hue untuk
besaran angka, warna status hanya untuk status, dan tanpa sumbu ganda.
