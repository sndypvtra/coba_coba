# Mockup webapp Outlytics — gambaran halaman untuk presentasi

Sebelas gambar 16:9 tentang **Outlytics**, webapp yang membungkus pipeline
dwell time (project 05) menjadi produk: pantauan live per CCTV, analitik, perbandingan
outlet, pengaturan CCTV, notifikasi WhatsApp, dan dua sisi akses — aplikasi klien dan
panel internal. Nama "Outlytics" berasal dari *outlet* + *analytics*. Per 1 Okt 2026
belum ditemukan perusahaan atau aplikasi dengan nama itu, dan outlytics.ai, .io, serta
.id belum terdaftar (outlytics.com diparkir dan dijual). Merek di DJKI belum dicek;
alamat `app.outlytics.ai` di gambar hanya contoh sampai domainnya dibeli.

Setiap halaman tersedia dalam dua bentuk:

- **PNG 4800×2700** (`*.png`), untuk semua aplikasi. Resolusinya cukup besar untuk
  dipotong atau diperbesar di slide.
- **SVG** (`svg/*.svg`), yang tetap tajam di ukuran berapa pun. Teks di dalamnya sudah
  berupa garis (outline), jadi tidak butuh font. Hanya dua foto CCTV yang tetap berupa
  piksel, dalam ukuran aslinya. Bisa dimasukkan ke PowerPoint 2019, 2021, atau Microsoft
  365 lewat Insert → Pictures. Google Slides belum menerima SVG, jadi pakai PNG di sana.
  Di versi SVG, bayangan lembut di sekeliling jendela diganti garis tepi tipis, karena
  efek bayangan sering tidak tergambar saat SVG diimpor ke aplikasi slide.

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
- Denah "Ruang Utama Lt. 1" di halaman yang sama digambar dari frame itu, dan dilihat
  dari arah yang sama dengan CCTV 02: counter melintang hampir datar di belakang, dinding
  bangku turun ke kiri, kamera di bawah. Ruangannya digambar siku seperti denah biasa.
  Isinya sesuai frame:
  - bangku panjang 6 kursi dengan meja 1–3; di meja 2 ada empat orang, dua di bangku dan
    dua di kursi, duduk saling berhadapan;
  - meja 4 berupa tiga meja dalam satu baris di depan counter, dengan enam kursi saling
    berhadapan; ujung kanannya, tempat seorang pria duduk, bersinggungan dengan area antre;
  - meja 5 (kosong, ada gelas tertinggal) dan meja 6 (perempuan di latar depan, duduk
    di sisi yang menghadap kamera), masing-masing dua kursi yang saling berhadapan;
  - satu orang sedang berjalan, satu staf di belakang counter, total 8 orang (7 tamu,
    1 staf).

  Posisinya dirapikan ke ukuran meja yang wajar, jadi bisa bergeser beberapa puluh
  sentimeter dari aslinya.
- `05-cctv-area` memakai frame mentah dari klip yang sama, dengan dua area yang digambar
  persis seperti di `config.py`: cermin dinding (tidak dihitung) dan area kasir. Area
  antre yang sedang digambar adalah ilustrasi. Letaknya sama dengan di denah: di depan
  kasir dan etalase, overlap dengan area kasir, dan menyentuh ujung meja 4.

**Ilustrasi**: semua angka lain, nama klien, pengguna, outlet, perangkat, harga paket,
dan domain. Setiap gambar membawa tulisan "MOCKUP · contoh data, bukan data asli" di
sudut kanan bawah. Jangan menyajikan angka di gambar sebagai traksi atau hasil pengukuran.

Angka antarhalaman sengaja dibuat saling cocok, jadi tidak ada yang bertentangan saat
dibandingkan:

- Ruang Utama punya 21 kursi; 6 terisi (29%), antrean 0, dan kasir ada staf.
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
pip install pymupdf                           # sekali saja, untuk SVG
python tools/build_mockups.py                 # semua halaman -> docs/mockup/ dan docs/mockup/svg/
python tools/build_mockups.py --only 01 03    # sebagian saja
python tools/build_mockups.py --scale 1 --no-svg   # pratinjau cepat 1600x900
```

Halaman ditulis sebagai HTML/CSS/SVG di `tools/mockup/pages.py` dan digambar dengan
Chromium headless. Untuk SVG, Chromium mencetak tiap halaman ke PDF satu halaman, lalu
PyMuPDF mengubahnya ke SVG. Font dan ikon diunduh sekali ke `tools/.mockup_cache` lalu ditanam di
halaman: Inter (SIL OFL), Lucide (ISC), dan Iconify untuk logo merek (milik pemiliknya
masing-masing). Palet dan aturan grafik mengikuti referensi dataviz: satu hue untuk
besaran angka, warna status hanya untuk status, dan tanpa sumbu ganda.
