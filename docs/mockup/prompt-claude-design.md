# Brief: deck Outlytics untuk pemilik outlet dan investor

Kamu akan membuat deck presentasi tentang **Outlytics**. Bahannya 13 gambar mockup yang
saya lampirkan, dimulai dari `00-landing-page.png`. Deck ini dibaca dua jenis orang:

- **Pemilik outlet**: pemilik kafe, resto, atau toko dengan beberapa cabang, yang mungkin
  membeli Outlytics.
- **Investor**: angel dan VC yang mungkin mendanai Outlytics.

Keduanya sibuk dan bukan orang teknis. Mereka membaca dengan satu pertanyaan di kepala:
*"Apa untungnya buat saya, dan apakah ini masuk akal?"*

## Duduklah di kursi pembaca

Sebelum menulis satu slide pun, posisikan dirimu sebagai pembacanya: pemilik outlet yang
tidak bisa menunggui semua cabangnya, atau investor yang baru pertama kali mendengar
Outlytics. Setiap slide menjawab satu pertanyaan mereka, dengan bahasa mereka:

| Pertanyaan pembaca | Slide |
|---|---|
| Ini apa, dan apa untungnya buat saya? | 1 |
| Masalah apa yang sedang saya alami tanpa sadar? | 2 |
| Berapa rupiah yang saya lewatkan? | 3 |
| Bagaimana Outlytics menemukannya? | 4–5 |
| Apa yang saya terima setiap hari? | 6–9 |
| Repot tidak memasangnya? | 10 |
| Adil untuk karyawan saya? Data saya aman? | 11 |
| Apakah ini bisa jadi bisnis besar, dan kenapa sulit ditiru? | 12–13 |
| Berapa harganya, dan apakah sepadan? | 14 |
| Apa yang sudah terbukti, dan apa langkah berikutnya? | 15–16 |

Sebelum menyerahkan deck, baca ulang setiap slide dari kursi pembaca dan uji dengan tiga
pertanyaan:

1. Apakah pemilik outlet menangkap pesannya dalam 5 detik?
2. Adakah kata yang membuat ia harus bertanya artinya? Kalau ada, ganti.
3. Apakah slide ini bicara uang, waktu, atau risiko? Kalau tidak, pertajam.

## Tentang Outlytics

Kalimat satu napas: *Outlytics menemukan omzet yang bocor di kasir, langsung dari CCTV.
Setiap pelanggan yang dilayani di kasir dicocokkan dengan struknya, dan selisihnya dikirim
ke WhatsApp setiap pagi dalam rupiah.*

Yang didapat pemilik outlet:

- **Selisih di kasir dalam rupiah.** Pelanggan yang dilayani tapi tidak punya struk
  langsung terlihat, lengkap dengan klip bukti 30 detik.
- **Laporan setiap pagi di WhatsApp.** Tanpa membuka aplikasi, Owner tahu kemarin ada apa.
- **Semua outlet dalam satu layar.** Tahu cabang mana yang perlu dicek minggu ini.
- **Jam ramai dan kebutuhan staf.** Tahu kapan antrean panjang, kapan kasir kosong, dan
  kapan perlu tambah orang.

**Pembeda utamanya: Audit Kasir.** Aplikasi kasir (misalnya Moka, Majoo, ESB, atau Pawoon)
hanya mencatat apa yang diketik. CCTV melihat siapa yang benar-benar dilayani. Outlytics
mencocokkan keduanya:

- kasus yang wajar disaring otomatis, misalnya pengemudi ojol yang mengambil pesanan
  online atau orang yang hanya bertanya;
- sisanya menjadi temuan yang perlu dicek, lengkap dengan perkiraan rupiah;
- polanya dibandingkan per shift dengan kebiasaan outlet itu sendiri, bukan per orang.

**Kenapa sulit ditiru:** idenya bisa disalin, tetapi data dan sambungannya tidak.

1. Ada rupiahnya, jadi pemilik outlet mau memasang Outlytics.
2. Setiap temuan yang ditinjau Owner membuat pencocokan makin akurat. Kumpulan temuan
   ini tidak dimiliki pesaing.
3. Outlytics netral terhadap merek aplikasi kasir. Sebuah aplikasi kasir hanya melayani
   pelanggannya sendiri, sedangkan grup kafe sering memakai aplikasi kasir yang berbeda
   di tiap cabang.
4. Riwayat temuan dan pola per shift membuat Owner enggan pindah.

Klien contoh di mockup adalah **Kedai Pagi**, jaringan kafe dengan 12 outlet, dan
pemiliknya bernama **Lucky**.

## Bahasa

- Bahasa Indonesia sehari-hari yang sopan. Kalimat pendek. Sapa pembaca dengan "Anda".
- Pakai kata-kata pemilik outlet: omzet, rupiah, kasir, struk, pelanggan, rombongan
  (orang yang datang bersama), staf, shift, cabang, outlet.
- Ganti istilah teknis:
  - "POS" menjadi "aplikasi kasir" (jelaskan sekali di slide 4);
  - "API" atau "integrasi" menjadi "sambungan resmi";
  - jangan memakai "inference", "tracking", "model", "pipeline", "edge", "server", atau
    "GPU";
  - "AI", "CCTV", "WhatsApp", "Owner", "Admin", "Manager", dan "dashboard" boleh dipakai.
- Angka selalu dengan satuan yang langsung dipahami: "±Rp 334 rb", "5 temuan",
  "141 dari 152 rombongan".
- Judul slide berupa satu kalimat kesimpulan, bukan topik. Contoh: bukan "Fitur Audit
  Kasir", tapi "Setiap pelanggan di kasir dicocokkan dengan struknya."
- Teks isi maksimal sekitar 30 kata per slide. Satu slide, satu pesan.
- Pakai nama dan istilah yang sama dengan mockup:
  - nama halaman: Ringkasan Hari Ini, Pantauan Live, Analitik, Audit Kasir,
    Perbandingan Outlet, CCTV & Area, Notifikasi & Laporan, Tim & Hak Akses,
    Privasi & Keamanan, Panel internal;
  - angka: "kursi terisi" (bukan "okupansi"), "pengunjung", "antrean", "kasir kosong",
    "lama berkunjung", "cocok dengan struk", "wajar", "perlu dicek", "temuan";
  - label keandalan angka: **Akurat** (dihitung langsung dari jumlah orang di gambar),
    **Estimasi** (dihitung dari pergerakan orang), dan **Data kasir** (diambil dari struk).
- Sebut temuan audit sebagai "selisih yang perlu dicek", bukan "pencurian" atau
  "kecurangan". Sistem menunjukkan pola, bukan menuduh orang.

## Gaya visual

Ikuti gaya mockup supaya deck dan gambarnya terasa satu kesatuan.

- Format 16:9, font Inter atau sans-serif lain yang mirip.
- Warna:
  - biru `#2a78d6` untuk aksen utama dan aplikasi klien;
  - oranye `#eb6834` khusus untuk panel internal;
  - teks utama `#0b0b0b`, teks kedua `#52514e`, teks samar `#898781`;
  - latar `#f6f6f3` dengan kartu putih bersudut membulat (sekitar 12px) dan garis tipis.
- Warna status hanya untuk status: hijau `#0ca30c` untuk baik, kuning `#fab219` untuk
  perlu perhatian, dan merah `#d03b3b` untuk kritis atau perlu dicek.
- Beri banyak ruang kosong.
- Tampilkan gambar mockup besar dan utuh. Jangan gambar ulang atau mengubah isinya.
  Boleh memotong atau memperbesar bagian tertentu, lalu memberi label penunjuk yang
  singkat.
- Grafik sederhana (misalnya dua batang "biaya" dan "potensi" di slide 3) boleh dibuat
  sendiri dengan warna di atas.
- Logonya kotak biru membulat dengan ikon mata pemindai, plus tulisan "Outlytics", seperti
  di sudut kiri atas mockup.

## File yang dilampirkan

| File | Isi |
|---|---|
| `00-landing-page.png` | Landing page `outlytics.ai`: judul "Temukan omzet yang bocor di kasir, langsung dari CCTV", bukti di sampingnya (halaman Audit Kasir dan laporan WhatsApp), ajakan coba gratis 30 hari, dan tiga manfaat utama |
| `00-peta-halaman.png` | Semua halaman aplikasi dalam satu gambar: aplikasi klien (biru), pembeda utama (biru tua), panel internal (oranye), dan tiga prinsip |
| `01-ringkasan.png` | Ringkasan Hari Ini: lima angka kunci, grafik keramaian, hal yang perlu ditindaklanjuti, dan kartu "Kasir vs struk hari ini" |
| `02-pantauan-live.png` | Pantauan Live: denah ruangan dari CCTV 02, video CCTV, dan kejadian terbaru |
| `03-analitik.png` | Analitik: jam ramai seminggu, tamu vs staf, pemakaian meja, dan perjalanan tamu |
| `04-perbandingan-outlet.png` | Perbandingan Outlet: peringkat 12 outlet, kolom "tanpa struk", dan outlet yang perlu dicek |
| `05-cctv-area.png` | CCTV & Area: menyambungkan CCTV, menandai area (termasuk titik pesan), menyambungkan aplikasi kasir, dan cek akurasi |
| `06-notifikasi-laporan.png` | Notifikasi & Laporan: aturan otomatis dan laporan WhatsApp pagi yang memuat hasil audit kasir |
| `07-tim-hak-akses.png` | Tim & Hak Akses: peran, akses per outlet, siapa yang boleh membuka audit dan klip |
| `08-privasi-keamanan.png` | Privasi & Keamanan: klip bukti hanya untuk Owner, laporan per shift, data yang disimpan, dan riwayat aktivitas |
| `09-superadmin-klien.png` | Panel internal, Klien & Paket: semua klien, status teknis, serta paket dan harga |
| `10-superadmin-perangkat.png` | Panel internal, Perangkat AI & Update: kondisi perangkat dan update bertahap |
| `11-audit-kasir.png` | Audit Kasir: rombongan vs struk, temuan yang perlu dicek, pola per shift, garis waktu satu temuan, dan sumber data kasir |

Setiap gambar juga ada versi SVG-nya dengan nama yang sama. Kalau bisa, pakai SVG supaya
gambar tetap tajam saat diperbesar atau dipotong. File `00-landing-page-penuh.png` (kalau
ikut terlampir) adalah landing page utuh dari atas sampai bawah. Pakai hanya sebagai bahan
teks untuk slide 3 dan 14; jangan ditampilkan utuh.

## Alur slide

Buat 16 slide dengan urutan di bawah. Judul di sini adalah arah pesannya; boleh dipoles
asal maknanya tetap sama.

1. **Cover: landing page.** Pakai `00-landing-page.png` besar. Judul: "Outlytics". Kalimat
   di bawahnya: *"Temukan omzet yang bocor di kasir, langsung dari CCTV."* Ini kesan
   pertama, jadi biarkan gambarnya yang bicara.
2. **Masalah.** "Yang tidak tercatat, tidak bisa Anda perbaiki." Tiga poin:
   - transaksi yang tidak diketik: pelanggan sudah membayar, tapi struknya tidak pernah
     ada;
   - pembeli yang pergi karena antre: masuk, melihat antrean, lalu keluar;
   - cabang yang tidak bisa ditunggui: laporan dari cabang belum tentu menceritakan
     semuanya.
3. **Nilainya dalam rupiah.** "Kebocoran kecil, nilainya besar." Contoh satu outlet
   dengan omzet Rp 150 jt per bulan dan rata-rata struk Rp 60 rb:
   - kalau 1% transaksi tidak tercatat, ±Rp 1,5 jt per bulan;
   - kalau 3% pembeli pergi karena antre, ±Rp 4,5 jt per bulan;
   - total yang bisa terlihat ±Rp 6 jt per bulan, dibanding biaya paket Growth
     Rp 1,5 jt.

   Tulis jelas bahwa ini contoh dengan persentase andaian, bukan janji.
4. **Solusinya.** "Setiap pelanggan di kasir dicocokkan dengan struknya." Diagram tiga
   langkah sederhana:
   1. CCTV melihat siapa yang dilayani di kasir.
   2. Hasilnya dicocokkan dengan struk di aplikasi kasir (sistem kasir yang sudah dipakai
      outlet, misalnya Moka atau Majoo).
   3. Selisihnya dikirim ke WhatsApp setiap pagi, dalam rupiah.
5. **Audit Kasir.** Pakai `11-audit-kasir.png`. Judul: "Aplikasi kasir mencatat yang
   diketik. Outlytics melihat yang benar-benar terjadi." Sorot:
   - 152 rombongan dilayani di kasir, 141 cocok dengan struk;
   - 7 dijelaskan otomatis (pengemudi ojol, orang yang hanya bertanya);
   - 5 temuan perlu dicek, perkiraan ±Rp 334 rb;
   - shift malam 3,5× dari biasanya;
   - garis waktu yang menunjukkan tidak ada struk untuk rombongan pukul 19.42.
6. **Laporan pagi di WhatsApp.** Pakai `06-notifikasi-laporan.png`. Judul: "Tanpa membuka
   aplikasi, Anda tahu kemarin ada apa." Sorot pesan harian pukul 08.00: 141 dari 152
   cocok, 5 temuan perlu dicek, dan 9 rombongan pergi karena antre.
7. **Ringkasan hari ini.** Pakai `01-ringkasan.png`. Judul: "Satu layar untuk hari ini."
   Sorot hal-hal berikut:
   - saran tambah 1 staf di kasir pukul 12.30–14.00;
   - kartu "Kasir vs struk hari ini": 94 dari 98 cocok, 2 perlu dicek;
   - label Akurat dan Estimasi di setiap angka.
8. **Semua cabang.** Pakai `04-perbandingan-outlet.png`. Judul: "Tahu cabang mana yang perlu
   dicek minggu ini." Sorot Bekasi: 8,7% rombongan tanpa struk, 5× cabang lain. Untuk
   pemilik waralaba, ini audit omzet.
9. **Ramai dan staf.** Pakai `03-analitik.png`, dengan potongan `02-pantauan-live.png`.
   Judul: "Tahu kapan ramai, dan kapan perlu tambah orang." Sorot hal-hal berikut:
   - jam paling ramai dalam seminggu;
   - 11 orang keluar dari antrean sebelum dilayani;
   - saran tambah 1 staf di 5 jam sibuk.
10. **Pemasangan.** Pakai `05-cctv-area.png`. Judul: "Dipasang tim kami. Laporan pertama
    datang keesokan paginya." Lima langkahnya:
    1. Sambungkan CCTV.
    2. Tandai area, termasuk titik pesan di depan kasir.
    3. Sambungkan aplikasi kasir.
    4. Cek akurasi.
    5. Aktifkan.

    CCTV berikutnya bisa ditambah sendiri dalam beberapa menit.
11. **Adil dan aman.** Pakai `07-tim-hak-akses.png` dan `08-privasi-keamanan.png`. Judul:
    "Adil untuk karyawan, aman untuk data Anda." Poinnya:
    - laporan dibuat per shift, bukan per orang;
    - klip bukti hanya bisa diputar Owner, terhapus otomatis setelah 30 hari, dan setiap
      pemutaran tercatat;
    - setiap orang hanya melihat yang perlu, sesuai perannya;
    - tim internal Outlytics hanya bisa melihat data dengan izin Owner.
12. **Satu aplikasi, siap untuk banyak klien.** Pakai `00-peta-halaman.png`, dengan
    `09-superadmin-klien.png` dan `10-superadmin-perangkat.png` sebagai pendukung.
    Judul: "Satu aplikasi untuk klien, satu panel untuk tim kami." Semua klien dikelola
    dari satu panel, dan update dikirim bertahap serta berhenti otomatis kalau ada
    masalah.
13. **Kenapa sulit ditiru.** Slide teks dengan roda gila dari empat alasan di bagian
    "Tentang Outlytics": ada rupiahnya, temuan yang ditinjau membuat makin akurat, netral
    terhadap merek aplikasi kasir, dan riwayat membuat Owner enggan pindah. Jangan menulis
    jumlah outlet atau klien kami.
14. **Harga.** "Mulai dari satu outlet." Harga per outlet per bulan:
    - Starter Rp 500 rb;
    - Growth Rp 1,5 jt, termasuk Audit Kasir;
    - Enterprise sesuai kebutuhan.

    Semua paket gratis 30 hari, tanpa kontrak. Sumbernya tabel "Paket & fitur" di
    `09-superadmin-klien.png`. Tulis bahwa harga ini masih hipotesis yang akan divalidasi
    lewat pilot.
15. **Yang sudah terbukti dan langkah berikutnya.**
    - Yang sudah terbukti: mesin AI-nya sudah berjalan di rekaman uji sebuah kafe
      sungguhan. Ia menghitung orang, memisahkan staf dari tamu, dan mengabaikan pantulan
      di cermin.
    - Langkah berikutnya: pilot di 10 outlet pertama di Jabodetabek untuk mengukur dua
      hal, yaitu berapa rupiah yang ditemukan Audit Kasir dan berapa persen temuannya
      memang perlu dicek.
    - Target pilot: [isi target pilot].
16. **Penutup.** "Mulai dari satu outlet." Dua ajakan:
    - untuk pemilik outlet: coba gratis 30 hari atau ikut pilot;
    - untuk investor: [isi kebutuhan pendanaan atau kemitraan].

    Lalu kontak: [isi kontak].

## Aturan kejujuran (wajib)

- **Semua angka di mockup adalah contoh data.** Ini termasuk Kedai Pagi, 187 pengunjung,
  12 outlet, 12 klien, ±Rp 334 rb, dan Rp 10,8 jt. Jangan sajikan sebagai traksi,
  pendapatan, jumlah pelanggan nyata, atau besar kebocoran yang sudah terbukti.
- **Beri catatan kecil "Mockup · contoh data"** di pojok setiap slide yang memakai mockup.
- **"Live" adalah target produk.** Saat ini mesin AI memproses rekaman uji, belum real
  time. Jangan menulis angka kecepatan atau jeda waktu.
- **Audit Kasir adalah rencana produk.** Mesin AI hari ini sudah bisa menghitung orang dan
  memisahkan staf dari tamu. Pencocokan dengan struk dan sambungan ke aplikasi kasir belum
  dibangun.
- **Harga paket masih hipotesis.**
- **Janji di landing page adalah rencana**, bukan hasil: program pilot 10 outlet, gratis
  30 hari, pemasangan dalam satu kunjungan, dan laporan keesokan paginya.
- **Hitungan ±Rp 6 jt di slide 3 adalah contoh** dengan persentase andaian. Jangan
  sajikan sebagai hasil rata-rata pelanggan.
- **Jangan menambahkan testimoni, logo pelanggan, atau logo aplikasi kasir** ke slide
  mana pun. Belum ada pelanggan maupun kerja sama. Moka, Majoo, ESB, dan Pawoon hanya
  contoh aplikasi kasir yang punya sambungan resmi.
- **Jangan menulis "tanpa kamera baru", "tanpa wajah", atau "video tidak disimpan di
  cloud".** Ketiganya belum tentu benar: titik pesan mungkin butuh kamera tambahan, klip
  bukti memperlihatkan orang apa adanya, dan pemrosesan video bisa berjalan di cloud.
- **Jangan menulis bahwa produk sudah sesuai UU PDP.** Kalau perlu, tulis "dirancang
  mengikuti prinsip UU PDP; akan ditinjau konsultan hukum".
- **Jangan mengarang data pasar, pesaing, pendanaan, atau tim.** Kalau sebuah slide
  butuh data itu, beri tempat kosong yang jelas, misalnya [isi ukuran pasar], supaya saya
  yang mengisinya.
- **Foto dan video kafe di mockup berasal dari dataset riset CAFE.** Di slide yang
  menampilkannya (`02`, `05`, dan potongan foto di `00-peta-halaman`), beri catatan kecil
  "Rekaman uji dari dataset riset".

## Yang saya minta darimu

- Deck 16:9 yang lengkap, sesuai alur di atas.
- Catatan pembicara untuk setiap slide, 2–4 kalimat, dengan bahasa lisan yang santai tapi
  sopan, seolah sedang bicara langsung dengan pemilik outlet.
- Di akhir, tulis dua hal:
  - daftar kata teknis yang kamu ganti, dan penggantinya;
  - usulan kalau menurutmu ada urutan atau sudut cerita yang lebih kuat. Jangan langsung
    mengubah deck.
