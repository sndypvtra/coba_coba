# Brief: deck investor Outlytics

Kamu akan membuat deck presentasi untuk investor tentang **Outlytics**. Bahan
utamanya adalah 13 gambar mockup aplikasi yang saya lampirkan, dari
`00-peta-halaman.png` sampai `12-rapor-kafe.png`. Ini presentasi pertama
kami ke investor, jadi deck harus jelas, meyakinkan, dan jujur.

## Tentang Outlytics

Outlytics mengubah CCTV yang sudah terpasang di kafe dan toko menjadi angka bisnis
yang bisa langsung dipakai:

- berapa orang ada di outlet dan berapa kursi terisi, saat ini;
- jam ramai dalam seminggu, dan berapa staf yang dibutuhkan di jam itu;
- antrean dan kasir: kapan antrean panjang, kapan kasir kosong;
- perbandingan semua outlet dalam satu layar;
- notifikasi dan laporan otomatis lewat WhatsApp.

Tiga janji utama:

1. **Tanpa kamera baru.** Outlytics memakai CCTV yang sudah ada.
2. **Tanpa wajah, tanpa nama.** Sistem hanya menghitung orang, tidak mengenali siapa orangnya.
3. **Video tidak disimpan di cloud.** Rekaman tetap di outlet; yang dikirim ke cloud
   hanya angka. Klip bukti 30 detik untuk audit kasir hanya bisa diputar Owner,
   langsung dari perangkat outlet, dan terhapus otomatis setelah 30 hari.

Pembelinya adalah pemilik dan pengelola bisnis dengan banyak outlet: kafe,
restoran, toko roti, toko ritel, apotek, klinik, dan gym. Klien contoh di mockup
adalah Kedai Pagi, jaringan kafe dengan 12 outlet.

Kalimat satu napas: *Outlytics membantu pemilik bisnis dengan banyak outlet tahu
apa yang terjadi di setiap cabang, langsung dari CCTV yang sudah mereka punya.*

## Dua pembeda utama

Banyak produk sudah bisa menghitung orang dari CCTV. Yang membedakan Outlytics adalah
menggabungkan CCTV dengan **aplikasi kasir (POS)**, misalnya Moka, Majoo, ESB, atau
Pawoon. Aplikasi kasir mencatat setiap struk: jam, total, cara bayar, dan pembatalan.

1. **Audit Kasir** (`11-audit-kasir.png`).
   - Kalimatnya: *"Aplikasi kasir mencatat apa yang diketik. Outlytics melihat apa
     yang benar-benar terjadi, lalu menghitung selisihnya dalam rupiah."*
   - Cara kerjanya: setiap rombongan yang dilayani di kasir dicocokkan dengan struk.
     Kasus wajar dijelaskan otomatis, misalnya pengemudi ojol yang mengambil pesanan
     online atau orang yang hanya bertanya. Sisanya dikirim ke Owner sebagai temuan,
     lengkap dengan perkiraan rupiah dan klip bukti.
   - Pola dibandingkan per shift dengan kebiasaan outlet itu sendiri, bukan per kasir.
2. **Rapor Kafe** (`12-rapor-kafe.png`).
   - Kalimatnya: *"Bukan cuma angka Anda, tapi posisi Anda di antara kafe sejenis,
     dan alasannya."*
   - Omzet per kursi per jam dipecah menjadi pengunjung per kursi (dari CCTV) ×
     belanja per pengunjung (dari kasir). Karena itu rapor bisa menjelaskan *kenapa*
     angkanya rendah. Aplikasi kasir saja hanya bisa bilang *bahwa* angkanya rendah.
   - Anonim: angka kafe lain tidak pernah ditampilkan satu per satu, dan kelompok baru
     tampil kalau berisi minimal 5 brand.
   - Contoh model yang sama di industri lain adalah STR untuk hotel. Hotel menyetor
     datanya lalu menerima rapor pembanding. CoStar membeli STR seharga US$450 juta
     pada 2019 (sumber: costar.com, "CoStar to Buy STR for $450 Million").

Kenapa dua ini sulit ditiru: idenya bisa disalin, tetapi datanya tidak.

- Audit Kasir membuat Owner mau memasang Outlytics, karena ada rupiahnya.
- Setiap temuan yang ditinjau Owner membuat pencocokan makin akurat.
- Makin banyak outlet yang ikut, makin tajam Rapor Kafe.
- Owner enggan pindah, karena riwayat dan pembandingnya hilang kalau pindah.

## Penonton dan gaya bahasa

- Penontonnya investor (angel dan VC) yang belum tentu paham teknologi. Bayangkan
  juga ada pemilik kafe yang ikut duduk di ruangan.
- Pakai bahasa Indonesia yang sederhana dan manusiawi, seperti teks di mockup.
  Kalimatnya pendek, dan tiap slide hanya membawa satu pesan utama.
- Istilah Inggris yang umum boleh dipakai: Live, Owner, Admin, Manager, Dashboard,
  WhatsApp, Support, AI.
- Hindari istilah teknis seperti "inference", "tracking", "edge computing",
  "tenant", "RBAC", "model", atau "pipeline". Ganti dengan bahasa bisnis, misalnya
  "perangkat AI di outlet", "klien", "hak akses", dan "versi AI". Kalau menyebut
  "POS", jelaskan sekali sebagai "aplikasi kasir".
- Pakai istilah yang sama dengan mockup:
  - nama halaman: Pantauan Live, Ringkasan Hari Ini, Analitik, Audit Kasir,
    Perbandingan Outlet, Rapor Kafe, CCTV & Area, Notifikasi & Laporan,
    Tim & Hak Akses, Privasi & Keamanan, Panel internal;
  - angka: "kursi terisi" (bukan "okupansi"), "pengunjung", "antrean",
    "kasir kosong", "lama berkunjung";
  - audit: "rombongan", "struk", "cocok dengan struk", "wajar", "perlu dicek",
    "temuan", "omzet per kursi per jam";
  - label keandalan angka: **Akurat** untuk angka yang dihitung langsung dari jumlah
    orang di gambar, **Estimasi** untuk angka yang dihitung dari pergerakan orang,
    dan **Data kasir** untuk angka yang diambil dari struk.
- Sebut temuan audit sebagai "selisih yang perlu dicek", bukan "pencurian" atau
  "kecurangan". Sistem menunjukkan pola, bukan menuduh orang.
- Sapa penonton dengan "Anda".

## Gaya visual

Ikuti gaya mockup supaya deck dan gambarnya terasa satu kesatuan.

- Format 16:9.
- Font Inter, atau sans-serif lain yang mirip.
- Warna:
  - biru `#2a78d6` untuk aplikasi klien dan aksen utama;
  - oranye `#eb6834` khusus untuk panel internal;
  - teks utama `#0b0b0b`, teks kedua `#52514e`, teks samar `#898781`;
  - latar `#f6f6f3` dengan kartu putih bersudut membulat (sekitar 12px) dan garis tipis.
- Warna status hanya dipakai untuk status: hijau `#0ca30c` untuk baik, kuning
  `#fab219` untuk perlu perhatian, dan merah `#d03b3b` untuk kritis atau perlu dicek.
- Beri banyak ruang kosong.
- Judul slide berupa satu kalimat yang menyampaikan pesannya, bukan sekadar topik.
- Teks isi maksimal sekitar 30 kata per slide.
- Tampilkan gambar mockup besar dan utuh, dan jangan gambar ulang atau ubah isinya.
  Kamu boleh memotong atau memperbesar bagian tertentu, lalu memberi label penunjuk
  yang singkat.
- Logonya kotak biru membulat dengan ikon mata pemindai, plus tulisan "Outlytics",
  seperti di sudut kiri atas mockup.

## File yang dilampirkan

| File | Isi |
|---|---|
| `00-peta-halaman.png` | Semua halaman dalam satu gambar: aplikasi klien (biru), pembeda utama (biru tua), panel internal (oranye), dan tiga prinsip privasi |
| `01-ringkasan.png` | Ringkasan Hari Ini: lima angka kunci, grafik keramaian hari ini, hal yang perlu ditindaklanjuti, dan kartu "Kasir vs struk hari ini" |
| `02-pantauan-live.png` | Pantauan Live: denah ruangan dari CCTV 02, video CCTV, dan kejadian terbaru |
| `03-analitik.png` | Analitik: jam ramai seminggu, tamu vs staf, pemakaian meja, dan perjalanan tamu |
| `04-perbandingan-outlet.png` | Perbandingan Outlet: peringkat 12 outlet, kolom "tanpa struk", dan outlet yang perlu dicek |
| `05-cctv-area.png` | CCTV & Area: menyambungkan CCTV, menandai area (termasuk titik pesan), menyambungkan aplikasi kasir, dan cek akurasi |
| `06-notifikasi-laporan.png` | Notifikasi & Laporan: aturan otomatis dan pesan WhatsApp yang memuat ringkasan audit kasir |
| `07-tim-hak-akses.png` | Tim & Hak Akses: peran, akses per outlet, siapa boleh membuka audit dan klip, dan keamanan akun |
| `08-privasi-keamanan.png` | Privasi & Keamanan: data yang disimpan, klip bukti, ikut Rapor Kafe, izin akses tim support, dan riwayat aktivitas |
| `09-superadmin-klien.png` | Panel internal, Klien & Paket: semua klien, status teknis, serta paket dan harga |
| `10-superadmin-perangkat.png` | Panel internal, Perangkat AI & Update: kondisi perangkat dan update bertahap |
| `11-audit-kasir.png` | Audit Kasir: rombongan vs struk, temuan yang perlu dicek, pola per shift, garis waktu satu temuan, dan sumber data kasir |
| `12-rapor-kafe.png` | Rapor Kafe: posisi outlet dibanding kafe sejenis, alasan di balik angkanya, dan saran tindakan |

Setiap gambar juga ada versi SVG-nya, dengan nama yang sama di folder `svg/`. Kalau
kamu bisa memakai SVG, gunakan versi itu supaya gambar tetap tajam saat diperbesar
atau dipotong.

## Alur slide

Buat sekitar 19 slide dengan urutan di bawah. Judul di sini adalah arah pesannya;
boleh dipoles asal maknanya tetap sama.

1. **Cover.** "Outlytics", dengan tagline *"CCTV Anda, kini paham bisnis."*
   Visualnya potongan `02-pantauan-live.png` (denah dan video).
2. **Masalah.** "Pemilik outlet tidak bisa melihat apa yang terjadi di setiap
   cabang." Poinnya:
   - jam ramai yang sebenarnya tidak diketahui;
   - kasir kosong saat antrean panjang baru ketahuan dari komplain;
   - aplikasi kasir hanya tahu apa yang diketik, bukan siapa yang benar-benar dilayani;
   - rekaman CCTV hanya dibuka kalau ada masalah.
3. **Solusi.** "Outlytics mengubah CCTV yang sudah ada menjadi angka bisnis,
   langsung." Tampilkan tiga janji utama.
4. **Cara kerja.** Diagram empat langkah sederhana:
   1. CCTV di outlet.
   2. Perangkat AI di outlet menghitung orang.
   3. Hanya angka yang dikirim ke cloud, lalu dicocokkan dengan struk dari aplikasi
      kasir.
   4. Hasilnya tampil di dashboard dan WhatsApp.

   Tekankan bahwa video tidak disimpan di cloud.
5. **Satu aplikasi, dua sisi.** Pakai `00-peta-halaman.png`. Aplikasi klien
   untuk Owner, Admin, dan Manager; panel internal untuk tim Outlytics. Tunjuk
   kelompok "Pembeda utama".
6. **Pantauan Live.** Pakai `02-pantauan-live.png`. Sorot hal-hal berikut:
   - denah ruangan digambar dari CCTV, dilihat dari arah kamera yang sama;
   - ada 8 orang di ruangan: 7 tamu dan 1 staf;
   - antrean 0 dan kasir ada staf;
   - setiap angka diberi label Akurat atau Estimasi.
7. **Ringkasan untuk Owner.** Pakai `01-ringkasan.png`. Sorot lima angka kunci,
   saran tambah 1 staf di kasir pukul 12.30–14.00, dan kartu "Kasir vs struk hari
   ini".
8. **Pembeda 1: Audit Kasir.** Pakai `11-audit-kasir.png`. Judul: "Aplikasi kasir
   mencatat apa yang diketik. Outlytics melihat apa yang benar-benar terjadi." Sorot
   hal-hal berikut:
   - 152 rombongan dilayani, 141 cocok dengan struk;
   - 7 dijelaskan otomatis;
   - 5 temuan perlu dicek, ±Rp 334 rb;
   - shift malam 3,5× dari biasanya;
   - garis waktu yang menunjukkan tidak ada struk di jendela waktu rombongan itu.
9. **Audit dari laporan WhatsApp sampai antar-outlet.** Pakai
   `06-notifikasi-laporan.png` dan `04-perbandingan-outlet.png`. Sorot dua hal:
   - laporan harian di WhatsApp memuat kasir vs struk;
   - di perbandingan outlet, Bekasi punya 8,7% rombongan tanpa struk, 5× outlet lain.

   Untuk waralaba, ini audit omzet.
10. **Pembeda 2: Rapor Kafe.** Pakai `12-rapor-kafe.png`. Judul: "Bukan cuma angka
    Anda, tapi posisi Anda di antara kafe sejenis, dan alasannya." Sorot hal-hal
    berikut:
    - omzet per kursi per jam 15% di bawah kafe sejenis;
    - penyebabnya jumlah pengunjung, bukan belanja;
    - dua saran yang bisa langsung dijalankan.
11. **Kenapa sulit ditiru.** Slide teks dengan roda gila:
    1. Audit Kasir membawa outlet masuk.
    2. Temuan yang ditinjau Owner membuat pencocokan makin akurat.
    3. Makin banyak outlet lintas brand membuat Rapor Kafe makin tajam.
    4. Riwayat dan pembanding membuat Owner enggan pindah.

    Sebut STR sebagai contoh model yang sama di hotel. Jangan menulis jumlah outlet
    kami.
12. **Analitik yang bisa langsung ditindaklanjuti.** Pakai `03-analitik.png`.
    Sorot hal-hal berikut:
    - jam paling ramai dalam seminggu;
    - saran tambah 1 staf di 5 jam sibuk;
    - 11 orang keluar dari antrean sebelum dilayani.
13. **Untuk jaringan outlet.** Pakai `04-perbandingan-outlet.png`. "Lihat 12 outlet
    dalam satu layar, dan tahu mana yang perlu dicek minggu ini."
14. **Pasang cepat.** Pakai `05-cctv-area.png`. "Tambah CCTV baru dalam beberapa
    menit, tanpa teknisi khusus." Langkahnya:
    1. Sambungkan CCTV.
    2. Tandai area, termasuk titik pesan.
    3. Sambungkan aplikasi kasir.
    4. Cek akurasi.
    5. Aktifkan.
15. **Privasi dan kepercayaan.** Pakai `07-tim-hak-akses.png` dan
    `08-privasi-keamanan.png`. Poinnya:
    - hak akses diatur per peran dan per outlet;
    - klip bukti hanya untuk Owner, diputar dari perangkat outlet, dan setiap
      pemutaran tercatat;
    - laporan dibuat per shift, bukan per orang;
    - ikut Rapor Kafe adalah pilihan Owner;
    - tim internal hanya bisa membuka data dengan izin Owner.
16. **Siap untuk banyak klien.** Pakai `09-superadmin-klien.png` dan
    `10-superadmin-perangkat.png`. Semua klien dikelola dari satu panel, dan
    update AI dikirim bertahap serta otomatis berhenti kalau ada masalah.
17. **Model bisnis.** Harga per outlet per bulan:
    - Starter Rp 500 rb;
    - Growth Rp 1,5 jt, termasuk Audit Kasir;
    - Enterprise sesuai kontrak.

    Rapor Kafe tersedia untuk semua paket yang ikut berbagi data tanpa nama. Lihat
    tabel "Paket & fitur" di `09-superadmin-klien.png`. Tulis dengan jelas bahwa harga
    ini masih hipotesis yang akan divalidasi lewat pilot.
18. **Yang sudah terbukti dan langkah berikutnya.** Mesin AI-nya sudah berjalan
    di rekaman uji sebuah kafe sungguhan. Ia menghitung orang, memisahkan staf dari
    tamu, dan mengabaikan pantulan di cermin. Langkah berikutnya adalah pilot di
    outlet nyata untuk mengukur dua hal: berapa rupiah yang ditemukan Audit Kasir, dan
    berapa persen temuannya memang perlu dicek. Target pilot: [isi target pilot].
19. **Penutup.** Tulis ajakannya: [isi kebutuhan pendanaan atau kemitraan], lalu
    kontak: [isi kontak].

## Aturan kejujuran (wajib)

- Semua angka di mockup adalah contoh data, termasuk Kedai Pagi, 187 pengunjung,
  12 outlet, 12 klien, ±Rp 334 rb, Rp 10,8 jt, dan "41 kafe dari 13 brand". Jangan
  sajikan angka-angka itu sebagai traksi, pendapatan, jumlah pelanggan nyata, atau
  besar kebocoran yang sudah terbukti.
- Di setiap slide yang memakai mockup, beri catatan kecil di pojok:
  "Mockup · contoh data".
- "Live" adalah target produk. Saat ini mesin AI memproses rekaman uji, belum
  real time. Jangan menulis angka kecepatan atau jeda waktu.
- Audit Kasir dan Rapor Kafe adalah rencana produk. Mesin AI hari ini sudah bisa
  menghitung orang dan memisahkan staf dari tamu, tetapi pencocokan dengan struk,
  sambungan ke aplikasi kasir, dan rapor pembanding belum dibangun.
- Rapor Kafe butuh data dari banyak outlet lintas brand. Tulis bahwa ini kondisi
  target yang tumbuh bersama jumlah klien.
- Moka, Majoo, ESB, dan Pawoon hanya contoh aplikasi kasir yang menyediakan Open API.
  Belum ada integrasi atau kerja sama dengan mereka, jadi jangan sebut mereka mitra.
- Jangan menulis bahwa produk sudah sesuai UU PDP. Tulis "dirancang mengikuti
  prinsip UU PDP; akan ditinjau konsultan hukum".
- Harga paket masih hipotesis.
- Jangan mengarang data pasar, pesaing, pendanaan, atau tim. Kalau sebuah slide
  butuh data itu, beri tempat kosong yang jelas, misalnya [isi ukuran pasar], supaya
  saya yang mengisinya. Satu-satunya angka luar yang boleh dipakai adalah akuisisi
  STR oleh CoStar di atas, beserta sumbernya.
- Video kafe di mockup berasal dari dataset riset CAFE. Di slide yang
  menampilkannya, beri catatan kecil "Rekaman uji dari dataset riset".

## Yang saya minta darimu

- Deck 16:9 yang lengkap, sesuai alur di atas.
- Catatan pembicara untuk setiap slide, sebanyak 2–4 kalimat, dengan bahasa lisan
  yang santai tapi sopan.
- Kalau menurutmu ada urutan atau sudut cerita yang lebih kuat, tulis usulannya di
  akhir. Jangan langsung mengubah deck.
