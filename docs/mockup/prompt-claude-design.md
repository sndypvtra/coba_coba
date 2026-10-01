# Brief: deck investor Outlytics

Kamu akan membuat deck presentasi untuk investor tentang **Outlytics**. Bahan
utamanya adalah 11 gambar mockup aplikasi yang saya lampirkan, dari
`00-peta-halaman.png` sampai `10-superadmin-perangkat.png`. Ini presentasi pertama
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
3. **Video tetap di outlet.** Yang dikirim ke cloud hanya angka, bukan gambar atau video.

Pembelinya adalah pemilik dan pengelola bisnis dengan banyak outlet: kafe,
restoran, toko roti, toko ritel, apotek, klinik, dan gym. Klien contoh di mockup
adalah Kedai Pagi, jaringan kafe dengan 12 outlet.

Kalimat satu napas: *Outlytics membantu pemilik bisnis dengan banyak outlet tahu
apa yang terjadi di setiap cabang, langsung dari CCTV yang sudah mereka punya.*

## Penonton dan gaya bahasa

- Penontonnya investor (angel dan VC) yang belum tentu paham teknologi. Bayangkan
  juga ada pemilik kafe yang ikut duduk di ruangan.
- Pakai bahasa Indonesia yang sederhana dan manusiawi, seperti teks di mockup.
  Kalimatnya pendek, dan tiap slide hanya membawa satu pesan utama.
- Istilah Inggris yang umum boleh dipakai: Live, Owner, Admin, Manager, Dashboard,
  WhatsApp, Support, AI.
- Hindari istilah teknis seperti "inference", "tracking", "edge computing",
  "tenant", "RBAC", "model", atau "pipeline". Ganti dengan bahasa bisnis, misalnya
  "perangkat AI di outlet", "klien", "hak akses", dan "versi AI".
- Pakai istilah yang sama dengan mockup:
  - nama halaman: Pantauan Live, Ringkasan Hari Ini, Analitik, Perbandingan Outlet,
    CCTV & Area, Notifikasi & Laporan, Tim & Hak Akses, Privasi & Keamanan,
    Panel internal;
  - angka: "kursi terisi" (bukan "okupansi"), "pengunjung", "antrean",
    "kasir kosong", "lama berkunjung";
  - label keandalan angka: **Akurat** untuk angka yang dihitung langsung dari jumlah
    orang di gambar, dan **Estimasi** untuk angka yang dihitung dari pergerakan
    orang.
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
  `#fab219` untuk perlu perhatian, dan merah `#d03b3b` untuk kritis.
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
| `00-peta-halaman.png` | Semua halaman dalam satu gambar: aplikasi klien (biru), panel internal (oranye), dan tiga prinsip privasi |
| `01-ringkasan.png` | Ringkasan Hari Ini: lima angka kunci, grafik keramaian hari ini, dan hal yang perlu ditindaklanjuti |
| `02-pantauan-live.png` | Pantauan Live: denah ruangan dari CCTV 02, video CCTV, dan kejadian terbaru |
| `03-analitik.png` | Analitik: jam ramai seminggu, tamu vs staf, pemakaian meja, dan perjalanan tamu |
| `04-perbandingan-outlet.png` | Perbandingan Outlet: peringkat 12 outlet dan outlet yang perlu dicek |
| `05-cctv-area.png` | CCTV & Area: menyambungkan CCTV, menandai area di foto CCTV, dan cek akurasi |
| `06-notifikasi-laporan.png` | Notifikasi & Laporan: aturan otomatis dan contoh pesan WhatsApp |
| `07-tim-hak-akses.png` | Tim & Hak Akses: peran, akses per outlet, dan keamanan akun |
| `08-privasi-keamanan.png` | Privasi & Keamanan: data yang disimpan, izin akses tim support, dan riwayat aktivitas |
| `09-superadmin-klien.png` | Panel internal, Klien & Paket: semua klien, status teknis, serta paket dan harga |
| `10-superadmin-perangkat.png` | Panel internal, Perangkat AI & Update: kondisi perangkat dan update bertahap |

## Alur slide

Buat sekitar 16 slide dengan urutan di bawah. Judul di sini adalah arah pesannya;
boleh dipoles asal maknanya tetap sama.

1. **Cover.** "Outlytics", dengan tagline *"CCTV Anda, kini paham bisnis."*
   Visualnya potongan `02-pantauan-live.png` (denah dan video).
2. **Masalah.** "Pemilik outlet tidak bisa melihat apa yang terjadi di setiap
   cabang." Poinnya:
   - jam ramai yang sebenarnya tidak diketahui;
   - kasir kosong saat antrean panjang baru ketahuan dari komplain;
   - ada meja yang dipakai berjam-jam;
   - rekaman CCTV hanya dibuka kalau ada masalah.
3. **Solusi.** "Outlytics mengubah CCTV yang sudah ada menjadi angka bisnis,
   langsung." Tampilkan tiga janji utama.
4. **Cara kerja.** Diagram empat langkah sederhana:
   1. CCTV di outlet.
   2. Perangkat AI di outlet menghitung orang.
   3. Hanya angka yang dikirim ke cloud.
   4. Hasilnya tampil di dashboard dan WhatsApp.

   Tekankan bahwa video tidak pernah keluar dari outlet.
5. **Satu aplikasi, dua sisi.** Pakai `00-peta-halaman.png`. Aplikasi klien
   untuk Owner, Admin, dan Manager; panel internal untuk tim Outlytics.
6. **Pantauan Live.** Pakai `02-pantauan-live.png`. Sorot hal-hal berikut:
   - denah ruangan digambar dari CCTV;
   - ada 8 orang di ruangan: 7 tamu dan 1 staf;
   - antrean 0 dan kasir ada staf;
   - setiap angka diberi label Akurat atau Estimasi.
7. **Ringkasan untuk Owner.** Pakai `01-ringkasan.png`. Sorot lima angka kunci
   dan bagian "Perlu perhatian" yang langsung memberi saran, misalnya tambah
   1 staf di kasir pukul 12.30–14.00.
8. **Notifikasi WhatsApp.** Pakai `06-notifikasi-laporan.png`. "Info penting
   langsung ke WhatsApp, tanpa harus membuka dashboard." Sorot pesan "Kasir kosong
   4 menit, 5 orang sedang antre."
9. **Analitik yang bisa langsung ditindaklanjuti.** Pakai `03-analitik.png`.
   Sorot hal-hal berikut:
   - jam paling ramai dalam seminggu;
   - saran tambah 1 staf di 5 jam sibuk;
   - 11 orang keluar dari antrean sebelum dilayani.
10. **Untuk jaringan outlet.** Pakai `04-perbandingan-outlet.png`. "Lihat 12 outlet
    dalam satu layar, dan tahu mana yang perlu dicek minggu ini."
11. **Pasang cepat.** Pakai `05-cctv-area.png`. "Tambah CCTV baru dalam beberapa
    menit, tanpa teknisi khusus." Langkahnya: sambungkan CCTV, tandai area, cek
    akurasi, lalu aktifkan.
12. **Privasi dan kepercayaan.** Pakai `07-tim-hak-akses.png` dan
    `08-privasi-keamanan.png`. Poinnya:
    - hak akses diatur per peran dan per outlet;
    - tim internal hanya bisa membuka data dengan izin Owner, untuk waktu terbatas
      dan tercatat;
    - yang disimpan hanya angka.
13. **Siap untuk banyak klien.** Pakai `09-superadmin-klien.png` dan
    `10-superadmin-perangkat.png`. Semua klien dikelola dari satu panel, dan
    update AI dikirim bertahap serta otomatis berhenti kalau ada masalah.
14. **Model bisnis.** Harga per outlet per bulan:
    - Starter Rp 500 rb;
    - Growth Rp 1,5 jt;
    - Enterprise sesuai kontrak.

    Lihat tabel "Paket & fitur" di `09-superadmin-klien.png`. Tulis dengan jelas
    bahwa harga ini masih hipotesis yang akan divalidasi lewat pilot.
15. **Yang sudah terbukti dan langkah berikutnya.** Mesin AI-nya sudah berjalan
    di rekaman uji sebuah kafe sungguhan. Ia menghitung orang, memisahkan staf dari
    tamu, dan mengabaikan pantulan di cermin. Langkah berikutnya adalah pilot di
    outlet nyata: [isi target pilot].
16. **Penutup.** Tulis ajakannya: [isi kebutuhan pendanaan atau kemitraan], lalu
    kontak: [isi kontak].

## Aturan kejujuran (wajib)

- Semua angka di mockup adalah contoh data, termasuk Kedai Pagi, 187 pengunjung,
  12 outlet, dan 12 klien. Jangan sajikan angka-angka itu sebagai traksi,
  pendapatan, atau jumlah pelanggan nyata.
- Di setiap slide yang memakai mockup, beri catatan kecil di pojok:
  "Mockup · contoh data".
- "Live" adalah target produk. Saat ini mesin AI memproses rekaman uji, belum
  real time. Jangan menulis angka kecepatan atau jeda waktu.
- Harga paket masih hipotesis.
- Jangan mengarang data pasar, pesaing, pendanaan, atau tim. Kalau sebuah slide
  butuh data itu, beri tempat kosong yang jelas, misalnya [isi ukuran pasar], supaya
  saya yang mengisinya.
- Video kafe di mockup berasal dari dataset riset CAFE. Di slide yang
  menampilkannya, beri catatan kecil "Rekaman uji dari dataset riset".

## Yang saya minta darimu

- Deck 16:9 yang lengkap, sesuai alur di atas.
- Catatan pembicara untuk setiap slide, sebanyak 2–4 kalimat, dengan bahasa lisan
  yang santai tapi sopan.
- Kalau menurutmu ada urutan atau sudut cerita yang lebih kuat, tulis usulannya di
  akhir. Jangan langsung mengubah deck.
