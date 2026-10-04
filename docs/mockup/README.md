# Mockup webapp Outlytics — gambaran halaman untuk presentasi

Tiga belas gambar 16:9 tentang **Outlytics**, webapp yang membungkus pipeline
dwell time (project 05) menjadi produk: pantauan live per CCTV, analitik, perbandingan
outlet, pengaturan CCTV, notifikasi WhatsApp, dua sisi akses (aplikasi klien dan
panel internal), pembeda utamanya (**Audit Kasir**), dan **landing page** untuk
menjual ke pemilik outlet. Landing page juga tersedia sebagai satu halaman penuh.
Nama "Outlytics" berasal dari *outlet* + *analytics*. Per 1 Okt 2026 belum ditemukan
perusahaan atau aplikasi dengan nama itu, dan outlytics.ai, .io, serta .id belum
terdaftar (outlytics.com diparkir dan dijual). Merek di DJKI belum dicek; alamat
`app.outlytics.ai` di gambar hanya contoh sampai domainnya dibeli.

Setiap halaman tersedia dalam dua bentuk:

- **PNG 2400×1350** (`*.png`), untuk semua aplikasi, termasuk Claude Design dan
  Google Slides. Ukuran ini paling aman diunggah ke aplikasi slide. Kalau perlu lebih
  besar, jalankan `python tools/build_mockups.py --scale 3` untuk 4800×2700.
- **SVG** (`svg/*.svg`), yang tetap tajam di ukuran berapa pun. Teks di dalamnya sudah
  berupa garis (outline), jadi tidak butuh font. Hanya foto (di halaman 00, 02, dan 05)
  yang tetap berupa piksel. Foto-foto itu ditanam langsung di dalam file SVG, tanpa
  file terpisah. ID internal di tiap file diawali nomor dan inisial nama halamannya (`p02pl_…`), jadi
  beberapa SVG aman ditempel ke satu dokumen. Tanpa itu, halaman-halaman bisa saling
  meminjam bentuk potong (clip), lalu foto hilang: video jadi hitam dan thumbnail
  kosong. Bisa dimasukkan ke PowerPoint 2019, 2021, atau Microsoft
  365 lewat Insert → Pictures. Google Slides belum menerima SVG, jadi pakai PNG di sana.
  Kalau foto tetap tidak muncul di sebuah aplikasi, pakai PNG untuk halaman 00, 02,
  dan 05. Di versi SVG, bayangan lembut di sekeliling jendela diganti garis tepi tipis,
  karena efek bayangan sering tidak tergambar saat SVG diimpor ke aplikasi slide.

Untuk membuat deck di Claude Design, lampirkan ke-13 gambar 16:9 bersama
[`prompt-claude-design.md`](prompt-claude-design.md), lalu tempel salah satu prompt di
[`prompt-chat-claude-design.txt`](prompt-chat-claude-design.txt) ke kolom chat: prompt A
untuk merevisi deck yang sudah ada, prompt B untuk membuat deck baru. Brief-nya ditulis
dari kursi pembaca, yaitu pemilik outlet dan investor. Deck dibuka dengan landing page,
dan setiap slide memakai bahasa bisnis sehari-hari.

Gambar-gambarnya statis. Ini bukan prototipe yang bisa diklik.

| File | Halaman | Untuk | Fungsinya |
|---|---|---|---|
| `00-landing-page` | Landing page | Calon pembeli | layar pertama situs `outlytics.ai`: janji utama, bukti di sampingnya (halaman audit dan laporan WhatsApp), dan satu ajakan; jadi cover deck |
| `00-landing-page-penuh` | Landing page, utuh | Calon pembeli | seluruh situs dari atas sampai bawah, 2400 × 9729 piksel; untuk desain web, bukan untuk slide |
| `00-peta-halaman` | Peta halaman | — | seluruh halaman dalam tiga kelompok (aplikasi klien, pembeda utama, panel internal) dan tiga prinsip privasi |
| `01-ringkasan` | Ringkasan Hari Ini | Owner, Admin, Manager | lima angka kunci hari ini, hal yang perlu ditindaklanjuti, dan kartu "Kasir vs struk hari ini"; tiap angka berlabel Akurat atau Estimasi |
| `02-pantauan-live` | Pantauan Live | Manager, Layar TV | kondisi outlet saat ini per CCTV: denah ruangan, antrean, kasir, kejadian, video |
| `03-analitik` | Analitik | Owner, Admin, Analis | jam ramai seminggu, tamu vs staf, pemakaian meja, perjalanan tamu |
| `04-perbandingan-outlet` | Perbandingan Outlet | Owner, Admin pusat | peringkat 12 outlet, kolom "tanpa struk", outlet yang perlu dicek, skor semua outlet |
| `05-cctv-area` | CCTV & Area | Admin, Teknisi | sambungkan CCTV, tandai area di foto CCTV (termasuk titik pesan untuk audit kasir), sambungkan aplikasi kasir, cek akurasi |
| `06-notifikasi-laporan` | Notifikasi & Laporan | Owner, Admin, Manager | aturan otomatis (termasuk struk dibatalkan tanpa pelanggan), pesan WhatsApp dengan ringkasan audit, jadwal laporan |
| `07-tim-hak-akses` | Tim & Hak Akses | Owner, Admin | undang anggota, hak akses per peran dan per outlet (termasuk siapa boleh membuka audit dan klip), keamanan akun |
| `08-privasi-keamanan` | Privasi & Keamanan | Owner | pengaturan data (klip bukti, laporan per shift), izin akses tim support, riwayat aktivitas |
| `09-superadmin-klien` | Klien & Paket | Super Admin, Support | semua klien, status teknis, paket dan harga, permintaan akses |
| `10-superadmin-perangkat` | Perangkat AI & Update | Super Admin | perangkat AI di tiap outlet, update bertahap dengan syarat lanjut |
| `11-audit-kasir` | Audit Kasir | Owner | setiap rombongan yang dilayani di kasir dicocokkan dengan struk dari aplikasi kasir; selisihnya dalam rupiah, pola per shift, temuan yang perlu dicek, dan klip bukti |

Landing page bernomor 00 supaya membuka set gambar dan deck. Audit Kasir (11) ditambahkan
di belakang supaya nama file lama tidak berubah.

## Pembeda utama: Audit Kasir

**POS** (*point of sale*) adalah aplikasi kasir, misalnya Moka, Majoo, ESB, atau Pawoon.
POS mencatat setiap struk: jam, total, cara bayar, kanal (di kasir atau pesanan
online), dan pembatalan. CCTV melihat siapa yang benar-benar datang dan dilayani.
**Audit Kasir (`11`)** menggabungkan keduanya. Rombongan yang dilayani di titik pesan
dicocokkan dengan struk. Halaman ini menampilkan:

- kasus yang wajar (pengemudi ojol mengambil pesanan online, orang yang hanya
  bertanya) dijelaskan otomatis;
- sisanya menjadi temuan yang perlu dicek, dengan perkiraan rupiah;
- pola dibandingkan per shift dengan kebiasaan outlet itu sendiri, bukan per kasir;
- garis waktu yang menunjukkan kenapa sebuah temuan muncul;
- klip bukti 30 detik.

Supaya fitur ini masuk akal di seluruh aplikasi, halaman lain ikut diubah:

- **Menu samping**: tambah Audit Kasir (dengan jumlah temuan terbuka) dan Aplikasi Kasir.
- **`01`**: kartu "Laporan WhatsApp" diganti "Kasir vs struk hari ini", dan status
  aplikasi kasir masuk ke Status sistem.
- **`04`**: kolom tren diganti kolom "tanpa struk". Bekasi menggantikan Seminyak di
  daftar perlu dicek, sebagai contoh audit antar-outlet; untuk waralaba, ini audit omzet.
- **`05`**:
  - zona baru **Titik pesan**;
  - langkah baru **Sambungkan kasir** di antara "Tandai area" dan "Cek akurasi".
- **`06`**:
  - laporan WhatsApp harian memuat kasir vs struk, temuan, dan antre-lalu-pergi;
  - aturan baru: struk dibatalkan saat tidak ada pelanggan di depan kasir;
  - aturan "antrean 6 orang" dilepas supaya halaman tetap muat.
- **`07`**: baris "Audit kasir & klip". Owner melihat semua; Admin hanya ringkasan.
- **`08`**:
  - pengaturan "Klip bukti audit kasir";
  - laporan per shift, bukan per orang;
  - struk dari kasir masuk daftar data yang disimpan;
  - riwayat yang mencatat setiap klip yang diputar.
- **`09`**: Audit kasir masuk paket Growth (sebelumnya "sambung ke mesin kasir" hanya
  untuk Enterprise).
- **`00`**: kelompok baru "Pembeda utama", dengan cara kerjanya dalam tiga langkah.

**Rapor Kafe ditunda.** Pembanding antar-kafe sempat dirancang sebagai halaman tersendiri,
lalu ditunda karena belum dibutuhkan. Fitur ini baru berguna kalau sudah ada banyak
outlet lintas brand. Desain dan kodenya tersimpan di riwayat git (commit `2214dcf`).

## Landing page

Landing page ditulis untuk orang yang membayar, yaitu pemilik outlet, bukan untuk
orang teknis. Bahasanya bahasa bisnis sehari-hari, dan istilah "POS" diganti
"aplikasi kasir". Urutannya mengikuti pertanyaan calon pembeli:

1. **Apa untungnya?** Judul: *"Temukan omzet yang bocor di kasir, langsung dari
   CCTV."* Di sampingnya ada buktinya: halaman Audit Kasir dan laporan WhatsApp pagi.
   Ajakannya satu: **Coba gratis 30 hari**, dengan WhatsApp sebagai pilihan kedua.
2. **Masalah apa?** Transaksi yang tidak diketik, pembeli yang pergi karena antre, dan
   cabang yang tidak bisa ditunggui.
3. **Repot tidak?** Tiga langkah sampai laporan pertama: sambungkan CCTV, sambungkan
   aplikasi kasir (atau upload Excel), lalu terima laporan di WhatsApp.
4. **Seperti apa hasilnya?** Contoh audit satu hari dengan angka yang sama dengan
   halaman `11`.
5. **Sepadan tidak?** Hitungan contoh: omzet Rp 150 jt dan struk Rp 60 rb. Kalau 1%
   transaksi tidak tercatat dan 3% pembeli pergi karena antre, potensinya ±Rp 6 jt
   per bulan, 4× biaya paket Growth.
6. **Aman tidak?** Tiga janji: klip bukti hanya untuk Owner, laporan per shift (bukan
   per orang), dan tim internal hanya bisa melihat data dengan izin Owner.
7. **Berapa harganya, dan apa yang sering ditanyakan?** Tiga paket (sama dengan `09`)
   dan enam tanya jawab. Penutupnya formulir singkat: nama, nomor WhatsApp, dan
   jumlah outlet.

Landing page ini sengaja **tidak** memuat testimoni, logo pelanggan, atau logo
aplikasi kasir. Semuanya belum ada, dan kalau dikarang justru menjadi hal pertama yang
dicek investor. Tambahkan setelah pilot.

Sebelum landing page ini dipakai sungguhan, putuskan dan sanggupi dulu janji-janji
bisnis di dalamnya:

- program pilot untuk 10 outlet pertama di Jabodetabek;
- gratis 30 hari, tanpa kartu kredit dan tanpa kontrak;
- pemasangan dalam satu kunjungan;
- laporan pertama datang keesokan paginya;
- harga paket.

Gambar ini adalah desain, belum situs yang responsif untuk HP.

**Klaim yang dihapus.** "Tanpa kamera baru", "tanpa wajah", dan "video tidak disimpan di
cloud" tidak lagi ditulis di halaman mana pun, karena belum tentu benar:

- titik pesan mungkin butuh kamera tambahan atau posisi baru;
- klip bukti memperlihatkan orang apa adanya;
- pemrosesan video bisa berjalan di cloud.

Prinsip ketiga di `00` diganti "Klip bukti hanya untuk Owner".

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
- Pemisahan staf dan tamu per orang (`roles.py`) adalah dasar Audit Kasir: tamu di titik
  pesan dihitung saat ada staf di area kasir.

**Ilustrasi**: semua angka lain, nama klien, pengguna, outlet, perangkat, harga paket,
dan domain. Setiap gambar membawa tulisan "MOCKUP · contoh data, bukan data asli" di
sudut kanan bawah. Jangan menyajikan angka di gambar sebagai traksi atau hasil pengukuran.

Hal lain yang juga ilustrasi:

- **Pencocokan dengan struk belum dibangun.** Engine hari ini menghitung orang dan
  memisahkan staf dari tamu. Pencocokan dan konektor aplikasi kasir adalah rencana
  produk.
- **Besar kebocoran belum diukur.** Angka rupiah di `11` adalah contoh. Berapa yang
  benar-benar ditemukan, dan seberapa sering temuan itu benar, baru diketahui lewat
  pilot.
- **Nama aplikasi kasir hanya contoh.** Moka, Majoo, ESB, dan Pawoon disebut karena
  masing-masing menyediakan Open API. Belum ada integrasi atau kerja sama dengan
  mereka.
- **Gambar di panel temuan `11` digambar, bukan dipotong dari video.** Tidak ada orang
  sungguhan yang ditampilkan sebagai temuan.
- **Hitungan di landing page adalah contoh.** Persentase 1% dan 3% bukan hasil ukur, dan
  ditulis sebagai "kalau", bukan sebagai janji.

Angka antarhalaman sengaja dibuat saling cocok, jadi tidak ada yang bertentangan saat
dibandingkan:

- **Ruang Utama**: 21 kursi; 6 terisi (29%), antrean 0, dan kasir ada staf.
- **Jaringan**: ada 12 outlet. KPI jaringan di `04` dihitung dari tabelnya.
- **Klien**: ada 12 klien dengan 43 outlet dan 43 perangkat AI; 11 perangkat sudah memakai
  versi 2.4.
- **Audit kemarin (Rabu 30 Sep, Senopati)**, dipakai di `11` dan di laporan WhatsApp `06`:
  - 168 rombongan masuk;
  - 152 dilayani di kasir: 141 cocok dengan struk, 7 wajar (4 ojol, 3 hanya bertanya),
    dan 4 tanpa struk;
  - ditambah 1 struk dibatalkan, jadi 5 temuan senilai ±Rp 334 rb;
  - 9 rombongan antre lalu pergi (±Rp 522 rb);
  - 184 struk dengan omzet Rp 10,8 jt.
- **Audit hari ini (s.d. 15.00)**, di `01`:
  - 98 rombongan dilayani, 94 cocok, 2 wajar, 2 perlu dicek;
  - angka 98 sesuai dengan 140 orang yang membayar di kasir di corong `03`;
  - lencana "7" di menu Audit Kasir adalah 5 temuan kemarin + 2 hari ini yang belum
    ditinjau.

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
python tools/build_mockups.py --only 11 00    # Audit Kasir lalu landing page (landing page memakai gambar halaman 11)
python tools/build_mockups.py --scale 1 --no-svg   # pratinjau cepat 1600x900
```

Halaman ditulis sebagai HTML/CSS/SVG di `tools/mockup/pages.py` dan digambar dengan
Chromium headless. Untuk SVG, Chromium mencetak tiap halaman ke PDF satu halaman, lalu
PyMuPDF mengubahnya ke SVG. Landing page versi utuh lebih tinggi dari satu layar: halaman
itu melaporkan tingginya sendiri, lalu screenshot dan lembar PDF-nya disesuaikan. Karena
nomor 00 dipakai tiga file, ID di setiap SVG diawali nomor plus inisial namanya
(`p00lp_`, `p00lpp_`, `p00ph_`), jadi tidak ada yang bentrok. Font dan ikon diunduh sekali ke `tools/.mockup_cache` lalu ditanam di
halaman: Inter (SIL OFL), Lucide (ISC), dan Iconify untuk logo merek (milik pemiliknya
masing-masing). Palet dan aturan grafik mengikuti referensi dataviz: satu hue untuk
besaran angka, warna status hanya untuk status, dan tanpa sumbu ganda.
