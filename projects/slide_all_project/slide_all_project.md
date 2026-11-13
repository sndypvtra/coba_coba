# Brief Claude Design: AI Vision untuk Operasional (Masalah & Solusi)

Dokumen ini adalah instruksi lengkap untuk membuat satu deck dari 16 gambar mockup (PNG, 3840 × 2160).
Unggah dokumen ini bersama ke-16 gambar ke Claude Design, lalu buat **tepat 17 slide** sesuai bagian 5 dan 6.
Deck selesai di slide 17; jangan menambah slide lain.

## 1. Tujuan dan audiens

- **Audiens:** manajemen bisnis (operasional, logistik, QC, finance) dan tim teknis (IT, engineering) dalam satu
  ruangan. Setiap slide harus bisa dipahami kedua kelompok tanpa penjelasan tambahan.
- **Isi deck:** delapan project (use case). Setiap project punya tepat 2 slide berurutan:
  1. **Slide Masalah:** masalah bisnis yang dihadapi klien saat ini.
  2. **Slide Solusi:** cara produk menyelesaikan masalah tersebut, dengan dua mockup layar project itu.
- **Slide yang tidak boleh dibuat.** Deck ini bukan proposal bisnis. Jangan membuat slide seperti tiga slide terakhir
  deck *Warehouse Live Ops*, dan jangan menyisipkan isinya ke slide lain:
  1. **Model bisnis:** pendapatan berulang, langganan per kamera, paket layanan, pendapatan pendukung (sewa perangkat,
     onboarding, add-on), go-to-market, target pasar, dan harga.
  2. **Bukti PoC:** rangkuman hasil uji dalam angka, seperti akurasi, error posisi, jumlah kamera yang lolos kalibrasi,
     hasil blind test, dan fokus pilot.
  3. **Langkah berikutnya:** pilot, kebutuhan dari klien (akses CCTV, perangkat, PIC), hal yang didapat klien,
     timeline per bulan, permintaan persetujuan, dan pendanaan.
  - Juga tidak ada slide ringkasan manfaat, anggaran atau RAB, harga, agenda, penutup, atau "terima kasih".
  - Pengecualian: angka "Hasil aktual" di UC5 dan UC7 adalah output aplikasi, bukan slide bukti. Tampilkan angka itu
    di slide Solusi project tersebut, persis seperti tertulis di bagian 6.
- **Nada:** profesional, faktual, dan ringkas. Klaim hanya sebatas yang terlihat di gambar dan tertulis di dokumen ini.

## 2. Aturan desain

- Rasio 16:9. Semua gambar berukuran 3840 × 2160 (4K). Pakai file aslinya tanpa kompresi.
- **Slide Masalah** (layout sama untuk ke-8 project):
  - label kecil di kiri atas, misalnya `USE CASE 3 · PACK COUNT QC · MASALAH`;
  - judul satu kalimat, lalu satu baris "Untuk: …" (siapa pemakainya);
  - tiga kartu masalah berjajar, masing-masing berisi ikon garis sederhana, judul pendek, dan satu kalimat;
  - satu baris **Dampak bisnis** di bagian bawah;
  - tanpa mockup; warna netral dengan aksen peringatan yang lembut.
- **Slide Solusi** (layout sama untuk ke-8 project):
  - label kecil di kiri atas, misalnya `USE CASE 3 · PACK COUNT QC · SOLUSI`;
  - judul satu kalimat;
  - dua mockup berdampingan (gambar `_1` di kiri, gambar `_2` di kanan), masing-masing hampir setengah lebar slide,
    tampil utuh dalam rasio 16:9;
  - di bawah setiap mockup: nama layar (tebal) dan satu sampai dua kalimat tentang masalah yang diselesaikan layar itu;
  - untuk UC5 dan UC7, satu baris **Hasil aktual** di atas catatan kaki;
  - catatan kaki sumber di paling bawah;
  - warna aksen per project boleh berbeda, tetapi posisi elemen sama di ke-8 slide Solusi.
- Gambar ditampilkan utuh. Jangan meng-crop bagian yang memotong label atau catatan kaki di dalam gambar, dan jangan
  menambah atau mengubah apa pun di dalam gambar.
- Mockup UC1–UC4 dan UC6 adalah layar yang **sudah pernah dipresentasikan**. Gambarnya dipakai tanpa perubahan.
- Speaker notes diisi dari bagian 6. Kalimatnya boleh dipersingkat, tetapi isinya tetap.

## 3. Aturan bahasa

- Bahasa Indonesia baku yang lazim di dunia kerja. Istilah teknis memakai istilah yang umum dipakai di engineering
  dan bisnis, termasuk istilah Inggris yang sudah lazim.
- Judul menyebut masalah atau hasil untuk bisnis, bukan nama fitur. Satu gagasan per poin.
- Hindari kata promosi seperti revolusioner, canggih, mutakhir, seamless, dan game changer.
- **Tanpa angka asumsi.** Jangan tulis angka ilustrasi, perkiraan, atau hasil uji (PoC) di teks slide dan speaker notes.
  - Angka di mockup UC1–UC4 dan UC6 adalah ilustrasi. Angka itu tetap ada di gambar, tetapi tidak dikutip di teks.
- **Angka aktual hasil aplikasi wajib dipertahankan persis seperti di dokumen ini dan di gambar**, tanpa dibulatkan
  atau diubah. Angka ini hanya ada di UC5 (hasil ukur APK UkurPaket) dan UC7 (hasil video CCTV), dan ditandai
  "Hasil aktual" di bagian 6.
- Nama produk atau model yang mengandung angka (misalnya YOLOv9) dan istilah seperti 3D atau P × L × T bukan angka
  dalam aturan ini.

**Istilah yang dipakai dan yang dihindari**

| Pakai | Jangan pakai |
|---|---|
| aktual (rekaman aktual, ukuran aktual, tampilan aktual) | nyata |
| garis kotak yang tertutup dari kamera | rusuk, sisi tersembunyi |
| hasil ekstraksi model | hasil apa adanya, mentah |
| berat volumetrik (P × L × T dibagi faktor volumetrik) | berat dimensi |
| status Akurat / Perlu Dicek (sesuai layar APK) | lulus / gagal |
| alarm palsu (false alarm) | salah alarm |

**Istilah teknis yang boleh dipakai di slide tanpa diterjemahkan.** Artinya dicantumkan untuk speaker notes:

| Istilah | Arti singkat |
|---|---|
| edge AI | AI yang berjalan di perangkat di lokasi, bukan di cloud |
| live monitoring, dashboard, real-time | tampilan langsung saat kejadian berlangsung |
| bounding box | kotak penanda posisi objek di gambar |
| segmentasi | memisahkan objek dari latar belakang |
| depth map | peta jarak setiap titik gambar dari kamera |
| ID tracking | nomor unik per objek supaya setiap objek dihitung sekali |
| count line, count gate | garis hitung di gambar kamera |
| OCR | membaca teks dari gambar |
| vision-language model (VLM) | model AI yang membaca gambar lalu menjawab dalam teks |
| quality gate | pemeriksaan otomatis sebelum hasil dipakai |
| root cause, corrective action, CAPA | penyebab utama; tindakan perbaikan dan pencegahan |
| reject, underfill, overfill, giveaway | istilah QC di line produksi |
| near miss | kejadian yang hampir menjadi kecelakaan |
| PLC, WMS, TMS | sistem kontrol mesin, sistem gudang, sistem transportasi |

## 4. Gambar yang dipakai (16 file)

Semua gambar dipakai di slide Solusi. Slide Masalah tidak memakai mockup.

| Use case | File | Isi gambar | Sumber |
|---|---|---|---|
| UC1 Produce Grading | `UC1_produce_grading_1.png` | Dashboard TV di line: kelas warna setiap tomat, komposisi grade, off-colour lot terhadap limit | mockup yang sudah dipresentasikan |
| | `UC1_produce_grading_2.png` | Laporan Lot: keputusan lot, foto bukti, sebaran warna, riwayat lot, ekspor sertifikat | mockup yang sudah dipresentasikan |
| UC2 Fill Level Inspection | `UC2_fill_level_1.png` | Live Monitoring: level isi botol di kamera, status per nozzle, tombol hentikan nozzle | mockup yang sudah dipresentasikan |
| | `UC2_fill_level_2.png` | Reject & Giveaway: daftar reject, giveaway per nozzle, bukti reject | mockup yang sudah dipresentasikan |
| UC3 Pack Count QC | `UC3_pack_count_1.png` | Dashboard TV: isi tray dihitung per slot, tray kurang isi ditandai SHORT, peta slot kosong | mockup yang sudah dipresentasikan |
| | `UC3_pack_count_2.png` | Detail Reject: peta slot kardus, root cause, foto dan klip bukti, timeline, corrective action | mockup yang sudah dipresentasikan |
| UC4 Parcel Dimensioning (conveyor) | `UC4_parcel_conveyor_1.png` | Dashboard TV: P × L × T dan volume setiap paket di belt, kelas ukuran, manual check | mockup yang sudah dipresentasikan |
| | `UC4_parcel_conveyor_2.png` | Rencana Muat & Tagihan: isi truk dari volume, berat volumetrik vs berat aktual per pelanggan | mockup yang sudah dipresentasikan |
| UC5 UkurPaket (APK Android) | `UC5_ukurpaket_1.png` | Layar aktual APK UkurPaket mode foto tanpa AR: ambil foto, marking, hasil benda kotak, hasil benda bulat | baru, dari foto uji di HP Urovo DT50 |
| | `UC5_ukurpaket_2.png` | Cara APK menghitung dimensi: foto dengan segmentasi dan kotak 3D, depth map, kartu hasil, langkah perhitungan | baru, dari data yang sama |
| UC6 Warehouse Live Ops | `UC6_warehouse_1.png` | Live Monitoring: kamera otomatis tampil saat near miss, peringatan langsung, peta lantai | mockup yang sudah dipresentasikan |
| | `UC6_warehouse_2.png` | Detail Insiden: klip kejadian, cuplikan bukti, posisi di peta, CAPA, linimasa | mockup yang sudah dipresentasikan |
| UC7 Plate & Vehicle (CCTV parkir) | `UC7_plate_vehicle_1.png` | Video hasil: CAM 1 gerbang menghitung motor, mobil, truk; CAM 2 area parkir membaca plat | baru, dari rekaman CCTV aktual |
| | `UC7_plate_vehicle_2.png` | Zoom kedua kamera, tabel hitungan per jenis, foto plat terbaca, cara kerja | baru, dari rekaman yang sama |
| UC8 Document OCR | `UC8_document_ocr_1.png` | Hasil ekstraksi satu tiket menjadi satu baris tabel, dengan bounding box per field | baru, dari repo GitHub ekstraksi tiket |
| | `UC8_document_ocr_2.png` | Hasil ekstraksi foto berisi beberapa tiket, satu baris tabel per tiket | baru, dari repo yang sama |

Video pendukung UC7 (`plate_vehicle_cctv.mp4`) tidak masuk deck. Putar terpisah atau tautkan di slide Solusi UC7.

## 5. Susunan deck (17 slide)

| # | Slide | Gambar | Judul |
|---|---|---|---|
| 1 | Sampul | 8 gambar `_1` sebagai thumbnail | AI Vision untuk operasional: masalah bisnis dan solusinya |
| 2 | UC1 · Masalah | – | Mutu warna buah hanya dicek dengan sampel, sehingga lot campur warna lolos ke pembeli |
| 3 | UC1 · Solusi | `UC1_produce_grading_1.png`, `UC1_produce_grading_2.png` | Setiap buah di-grade di line, setiap lot punya keputusan dan bukti |
| 4 | UC2 · Masalah | – | Isi botol hanya dicek dengan sampel, sehingga underfill lolos dan overfill terbuang |
| 5 | UC2 · Solusi | `UC2_fill_level_1.png`, `UC2_fill_level_2.png` | Level isi setiap botol terukur langsung, per nozzle |
| 6 | UC3 · Masalah | – | Kemasan kurang isi baru ketahuan setelah ada komplain |
| 7 | UC3 · Solusi | `UC3_pack_count_1.png`, `UC3_pack_count_2.png` | Setiap kemasan dihitung per slot dan ditahan sebelum disegel |
| 8 | UC4 · Masalah | – | Ukuran paket tidak terukur, sehingga muat truk dan tagihan berdasarkan perkiraan |
| 9 | UC4 · Solusi | `UC4_parcel_conveyor_1.png`, `UC4_parcel_conveyor_2.png` | Ukuran setiap paket terukur di belt dan langsung dipakai untuk muat truk dan tagihan |
| 10 | UC5 · Masalah | – | Ukuran paket saat pickup dan di counter masih diukur dengan meteran atau ditebak |
| 11 | UC5 · Solusi | `UC5_ukurpaket_1.png`, `UC5_ukurpaket_2.png` | Kurir mengukur paket dengan satu foto dari HP |
| 12 | UC6 · Masalah | – | CCTV gudang merekam semuanya, tetapi belum mencegah insiden |
| 13 | UC6 · Solusi | `UC6_warehouse_1.png`, `UC6_warehouse_2.png` | Bahaya terdeteksi saat terjadi, setiap insiden tercatat dengan bukti |
| 14 | UC7 · Masalah | – | Kendaraan dan plat nomor masih dicatat manual |
| 15 | UC7 · Solusi | `UC7_plate_vehicle_1.png`, `UC7_plate_vehicle_2.png` | Kendaraan terhitung otomatis dan plat nomor terbaca dari CCTV yang sudah ada |
| 16 | UC8 · Masalah | – | Tiket dan dokumen hasil scan masih diketik ulang secara manual |
| 17 | UC8 · Solusi | `UC8_document_ocr_1.png`, `UC8_document_ocr_2.png` | Foto tiket langsung menjadi data tabel, satu baris per tiket |

## 6. Isi per slide

### Slide 1 · Sampul

- **Judul:** AI Vision untuk operasional: masalah bisnis dan solusinya
- **Subjudul:** Pabrik, gudang, logistik, parkir, dan dokumen, dari kamera dan foto yang sudah ada.
- **Visual:** grid berisi delapan gambar `_1`, masing-masing dengan nama project di bawahnya.
- **Baris bawah:** `[isi nama tim] · [isi tanggal]`
- **Speaker notes:** Deck ini merangkum delapan project AI vision. Untuk setiap project, kita lihat dulu masalah
  bisnisnya, lalu solusinya.

---

### UC1 · Produce Grading

#### Slide 2 · UC1 · Masalah
- **Label:** `USE CASE 1 · PRODUCE GRADING · MASALAH`
- **Judul:** Mutu warna buah hanya dicek dengan sampel, sehingga lot campur warna lolos ke pembeli
- **Untuk:** packing house buah dan sayur, eksportir, dan pemasok supermarket
- **Kartu masalah:**
  1. **Cek manual hanya sampel:** warna dan kematangan dicek dengan mata pada sebagian kecil buah, sisanya lewat tanpa
     dicek.
  2. **Standar berbeda per pembeli:** USDA, OECD, dan spec supermarket sulit diterapkan konsisten di setiap shift.
  3. **Klaim sulit dijawab:** tidak ada data dan bukti per lot saat pembeli atau importir mengajukan klaim warna.
- **Dampak bisnis:** lot ditolak atau diklaim setelah dikirim, dan kepercayaan pembeli turun.
- **Speaker notes:** Hari ini mutu warna dicek manual dengan sampel. Akibatnya lot campur warna baru ketahuan di
  tangan pembeli, dan saat ada klaim, tidak ada data per lot untuk menjawabnya.

#### Slide 3 · UC1 · Solusi
- **Label:** `USE CASE 1 · PRODUCE GRADING · SOLUSI`
- **Judul:** Setiap buah di-grade di line, setiap lot punya keputusan dan bukti
- **Mockup kiri:** `UC1_produce_grading_1.png`
  - **Dashboard TV di line:** kamera dan edge AI mengelompokkan setiap buah ke kelas warna standar USDA dan
    menghitungnya sekali di count gate. Saat off-colour lot melewati limit, operator langsung diarahkan untuk sortir
    ulang atau memberi label Mixed Color.
- **Mockup kanan:** `UC1_produce_grading_2.png`
  - **Laporan Lot:** setiap lot punya keputusan sesuai standar, foto bukti, dan riwayat penanganan. Sertifikat lot
    dalam PDF siap dikirim ke QA pembeli.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Di kiri, Dashboard TV di line: setiap buah diberi kotak sesuai kelas warnanya, dan operator tahu
  saat lot mulai keluar dari standar. Di kanan, Laporan Lot menyimpan keputusan, bukti, dan riwayat, sehingga klaim
  pembeli dijawab dengan data.

---

### UC2 · Fill Level Inspection

#### Slide 4 · UC2 · Masalah
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION · MASALAH`
- **Judul:** Isi botol hanya dicek dengan sampel, sehingga underfill lolos dan overfill terbuang
- **Untuk:** pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol
- **Kartu masalah:**
  1. **Underfill lolos ke pasar:** botol kurang isi berisiko memicu komplain konsumen dan pelanggaran ketentuan BDKT.
  2. **Overfill tidak terukur:** kelebihan isi adalah produk yang terbuang (giveaway) setiap hari.
  3. **Nozzle bermasalah terlambat ketahuan:** sampel berkala tidak menunjukkan nozzle mana yang salah setel.
- **Dampak bisnis:** risiko komplain dan regulasi, serta kerugian produk yang terus berjalan tanpa terlihat.
- **Speaker notes:** Cek isi botol hari ini mengandalkan sampel berkala. Botol kurang isi bisa lolos ke pasar,
  kelebihan isi terbuang tanpa terukur, dan nozzle yang salah setel baru ketahuan belakangan.

#### Slide 5 · UC2 · Solusi
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION · SOLUSI`
- **Judul:** Level isi setiap botol terukur langsung, per nozzle
- **Mockup kiri:** `UC2_fill_level_1.png`
  - **Live Monitoring:** kamera di mesin pengisi dan edge AI mengukur level isi setiap botol, lalu mengubahnya menjadi
    volume berdasarkan profil botol. Status setiap nozzle tampil langsung, dan nozzle bermasalah bisa dihentikan dari
    layar yang sama.
- **Mockup kanan:** `UC2_fill_level_2.png`
  - **Reject & Giveaway:** botol underfill di-reject lewat sinyal ke PLC, lengkap dengan bukti. Giveaway per nozzle
    dibandingkan dengan target, disertai saran tindakan untuk Maintenance.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Di kiri, supervisor melihat level isi setiap botol dan status setiap nozzle secara langsung. Di
  kanan, setiap reject punya bukti, dan giveaway per nozzle menunjukkan nozzle mana yang perlu disetel.

---

### UC3 · Pack Count QC

#### Slide 6 · UC3 · Masalah
- **Label:** `USE CASE 3 · PACK COUNT QC · MASALAH`
- **Judul:** Kemasan kurang isi baru ketahuan setelah ada komplain
- **Untuk:** pabrik makanan dan minuman kemasan, FMCG, dan co-packer
- **Kartu masalah:**
  1. **Cek manual hanya sampel:** tray dan kardus yang sudah disegel sulit dibuka ulang untuk dicek.
  2. **Penyebab tidak tercatat:** feeder kosong, lane filler, atau robot yang gagal mengambil produk tidak terlacak.
  3. **Masalah berulang:** tanpa data per slot, perbaikan dilakukan berdasarkan dugaan.
- **Dampak bisnis:** komplain distributor dan konsumen, biaya rework, dan risiko reputasi merek.
- **Speaker notes:** Kemasan kurang isi biasanya baru ketahuan setelah sampai di distributor atau konsumen. Karena
  penyebabnya tidak tercatat, masalah yang sama terus berulang.

#### Slide 7 · UC3 · Solusi
- **Label:** `USE CASE 3 · PACK COUNT QC · SOLUSI`
- **Judul:** Setiap kemasan dihitung per slot dan ditahan sebelum disegel
- **Mockup kiri:** `UC3_pack_count_1.png`
  - **Dashboard TV:** kamera di ujung line dan edge AI menghitung isi setiap tray per slot. Tray kurang isi ditandai
    SHORT dan di-reject sebelum disegel, dan peta slot kosong menunjukkan lane filler yang bermasalah.
- **Mockup kanan:** `UC3_pack_count_2.png`
  - **Detail Reject:** setiap reject punya peta slot, root cause, serta foto dan klip bukti. Timeline dan corrective
    action tercatat sampai rework selesai.
- **Catatan kaki:** Video: simulasi 3D buatan tim · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Di kiri, tray yang kurang isi ditandai dan ditahan sebelum disegel. Di kanan, setiap reject
  lengkap dengan penyebab dan buktinya, sehingga yang diperbaiki adalah sumber masalahnya.

---

### UC4 · Parcel Dimensioning (conveyor)

#### Slide 8 · UC4 · Masalah
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING · MASALAH`
- **Judul:** Ukuran paket tidak terukur, sehingga muat truk dan tagihan berdasarkan perkiraan
- **Untuk:** gudang distribusi, 3PL, e-commerce fulfilment, dan ekspedisi
- **Kartu masalah:**
  1. **Ukur manual atau tidak diukur:** meteran memperlambat proses, sehingga sebagian besar paket tidak diukur.
  2. **Tagihan hanya dari timbangan:** paket ringan tetapi besar memakan ruang truk, tetapi ditagih berdasarkan berat.
  3. **Muat truk berdasarkan perkiraan:** truk berangkat tidak penuh atau kekurangan ruang.
- **Dampak bisnis:** pendapatan dari berat volumetrik hilang dan kapasitas truk tidak terpakai optimal.
- **Speaker notes:** Tanpa data ukuran, tagihan hanya mengikuti berat timbangan dan rencana muat truk hanya perkiraan.
  Paket ringan tetapi besar menjadi kerugian yang tidak terlihat.

#### Slide 9 · UC4 · Solusi
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING · SOLUSI`
- **Judul:** Ukuran setiap paket terukur di belt dan langsung dipakai untuk muat truk dan tagihan
- **Mockup kiri:** `UC4_parcel_conveyor_1.png`
  - **Dashboard TV:** kamera di atas belt dan edge AI mengukur P × L × T serta volume setiap paket, menghitungnya di
    count line, dan mengelompokkannya per kelas ukuran. Paket yang ukurannya dekat batas kelas masuk manual check.
- **Mockup kanan:** `UC4_parcel_conveyor_2.png`
  - **Muat & Tagihan:** isi setiap truk dihitung dari volume terukur. Berat volumetrik dibandingkan dengan berat
    aktual per pelanggan, dan datanya dikirim ke TMS/WMS serta sistem invoice.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Di kiri, setiap paket terukur saat lewat di belt tanpa meteran. Di kanan, data ukuran itu langsung
  dipakai logistik untuk rencana muat truk dan finance untuk dasar tagihan.

---

### UC5 · UkurPaket (APK Android, mode foto)

#### Slide 10 · UC5 · Masalah
- **Label:** `USE CASE 5 · UKURPAKET · MASALAH`
- **Judul:** Ukuran paket saat pickup dan di counter masih diukur dengan meteran atau ditebak
- **Untuk:** kurir pickup, counter ekspedisi, dan agen
- **Kartu masalah:**
  1. **Ukur manual lambat:** kurir mengukur dengan meteran, atau menebak saat antrean panjang.
  2. **Berat tagih tidak sesuai:** ukuran yang salah membuat berat volumetrik dan tagihan keliru.
  3. **Perangkat terbatas:** handheld kurir umumnya tidak punya ARCore atau sensor depth untuk aplikasi ukur berbasis
     AR.
- **Dampak bisnis:** selisih tagihan dan proses pickup yang lambat.
- **Speaker notes:** Di lapangan, ukuran paket diukur dengan meteran atau sekadar ditebak. Aplikasi ukur berbasis AR
  juga tidak bisa dipakai karena handheld kurir umumnya tidak mendukungnya.

#### Slide 11 · UC5 · Solusi
- **Label:** `USE CASE 5 · UKURPAKET · SOLUSI`
- **Judul:** Kurir mengukur paket dengan satu foto dari HP
- **Mockup kiri:** `UC5_ukurpaket_1.png`
  - **Alur di APK:** APK memandu sudut foto, kurir tap objek atau tarik kotak, lalu P × L × T, berat volumetrik, dan
    status kualitas langsung tampil. Benda kotak dan benda bulat sama-sama terbaca.
- **Mockup kanan:** `UC5_ukurpaket_2.png`
  - **Cara APK menghitung:** segmentasi, depth map, sensor gravitasi, dan jarak fokus lensa membentuk kotak 3D di
    sekitar objek. Quality gate memberi status Akurat atau Perlu Dicek, dan statusnya tersimpan bersama foto bukti.
- **Hasil aktual APK (tampilkan persis):**
  - HP dengan clear case: **15,5 × 6,4 × 1,8 cm** (P × L × T), berat volumetrik **0,03 kg**, status
    **Akurat · skor 100**.
  - Gelas dengan sedotan: **7,1 × 7,1 × 23,7 cm** (diameter × diameter × tinggi), berat volumetrik **0,20 kg**, jarak
    lensa ke objek **24 cm** (autofocus), tinggi kamera di atas meja **30 cm**, kecocokan kotak 3D (IoU) **0,85**,
    status **Perlu Dicek · skor 75**.
- **Catatan kaki:** Tampilan aktual APK UkurPaket (mode foto, tanpa AR) dengan foto dari HP Urovo DT50 · kotak 3D
  digambar dari koordinat yang dihitung APK
- **Speaker notes:** Di kiri, kurir cukup memotret dan menandai objek, lalu hasilnya keluar di layar yang sama tanpa
  ARCore atau sensor tambahan. Di kanan, cara APK menghitung ukuran dari satu foto. HP terukur 15,5 × 6,4 × 1,8 cm
  dengan status Akurat. Gelas terukur 7,1 × 7,1 × 23,7 cm dengan tinggi termasuk sedotan, dan diberi status Perlu
  Dicek karena bentuknya bukan kotak. Berat volumetrik bukan berat aktual: berat aktual tetap dari timbangan, dan berat
  tagih adalah yang lebih besar dari keduanya.

---

### UC6 · Warehouse Live Ops

#### Slide 12 · UC6 · Masalah
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS · MASALAH`
- **Judul:** CCTV gudang merekam semuanya, tetapi belum mencegah insiden
- **Untuk:** 3PL dan distribusi, manufaktur, cold storage, dan e-commerce fulfilment
- **Kartu masalah:**
  1. **Bahaya baru ketahuan setelah terjadi:** risiko tabrakan orang dan forklift tidak terpantau saat itu juga.
  2. **Terlalu banyak layar:** operator tidak mungkin memantau belasan kamera sepanjang shift.
  3. **Bukti sulit dicari:** mencari satu insiden berarti memutar ulang rekaman berjam-jam, dan laporan K3 disusun
     manual.
- **Dampak bisnis:** risiko kecelakaan kerja, investigasi yang lambat, dan kesiapan audit K3 yang rendah.
- **Speaker notes:** Hampir setiap gudang sudah punya CCTV, tetapi rekamannya baru dibuka setelah ada kejadian. Bahaya
  tidak dicegah, dan bukti sulit dicari.

#### Slide 13 · UC6 · Solusi
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS · SOLUSI`
- **Judul:** Bahaya terdeteksi saat terjadi, setiap insiden tercatat dengan bukti
- **Mockup kiri:** `UC6_warehouse_1.png`
  - **Live Monitoring:** CCTV yang sudah ada dan edge AI mendeteksi orang, forklift, APD, dan zona. Saat near miss,
    kamera terkait otomatis tampil di layar utama dan peringatan masuk ke daftar.
- **Mockup kanan:** `UC6_warehouse_2.png`
  - **Detail Insiden:** klip kejadian, cuplikan bukti, posisi di peta, dan linimasa tersimpan otomatis. CAPA dengan
    penanggung jawab dan tenggat siap diekspor untuk audit K3.
- **Catatan kaki:** Cuplikan kamera: NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0) · layar mockup, angka di layar adalah
  ilustrasi
- **Speaker notes:** Di kiri, satu operator bisa mengawasi banyak kamera karena AI yang menyaring kejadian. Di kanan,
  setiap insiden tercatat lengkap dengan bukti dan tindakan perbaikannya, sehingga siap untuk audit.

---

### UC7 · Plate Recognition & Vehicle Counting (CCTV parkir)

#### Slide 14 · UC7 · Masalah
- **Label:** `USE CASE 7 · PLATE & VEHICLE · MASALAH`
- **Judul:** Kendaraan dan plat nomor masih dicatat manual
- **Untuk:** pengelola parkir, depot dan gudang distribusi, kawasan industri, dan gedung perkantoran
- **Kartu masalah:**
  1. **Pencatatan manual:** petugas menulis plat dan jenis kendaraan, sehingga rawan salah dan terlewat saat ramai.
  2. **Tidak ada data kendaraan:** jumlah motor, mobil, dan truk yang masuk dan keluar tidak tercatat.
  3. **Pencarian lambat:** mencari kapan kendaraan tertentu datang berarti memutar ulang rekaman CCTV.
- **Dampak bisnis:** kontrol akses dan keamanan lemah, serta keputusan operasional tanpa data.
- **Speaker notes:** Di banyak lokasi, kendaraan dan plat nomor masih dicatat petugas secara manual. Data jumlah
  kendaraan tidak ada, dan mencari kendaraan tertentu harus lewat rekaman.

#### Slide 15 · UC7 · Solusi
- **Label:** `USE CASE 7 · PLATE & VEHICLE · SOLUSI`
- **Judul:** Kendaraan terhitung otomatis dan plat nomor terbaca dari CCTV yang sudah ada
- **Mockup kiri:** `UC7_plate_vehicle_1.png`
  - **Dua kamera dalam satu layar:** kamera gerbang menghitung motor, mobil, dan truk/bus sekali per ID tracking,
    terpisah antara yang bergerak dan yang parkir. Kamera area parkir membaca plat nomor.
- **Mockup kanan:** `UC7_plate_vehicle_2.png`
  - **Hitungan dan plat tercatat:** plat ditetapkan setelah beberapa bacaan sama, lalu dicatat bersama foto plat,
    jenis kendaraan, kamera, dan waktu. Kamera baca plat dipasang dekat jalur masuk.
- **Hasil aktual pada video (tampilkan persis):** kendaraan bergerak di gerbang terhitung **3 motor** dan **1 truk**,
  masing-masing sekali; plat terbaca **T 649 EHP** dan **T 119 ELM**, keduanya sesuai dengan plat di video.
- **Catatan kaki:** Video: rekaman CCTV aktual dari dataset publik Hugging Face `rithwikn/ai_cctv_videos`, dua kamera
  digabung dalam satu video
- **Speaker notes:** Di kiri, video dari dua kamera CCTV aktual: kamera gerbang menghitung kendaraan dan kamera area
  parkir membaca plat. Di kanan, hitungan per jenis dan plat yang terbaca, masing-masing dengan foto. Plat di kamera
  gerbang tidak dibaca karena terlalu jauh, jadi kamera baca plat dipasang dekat jalur masuk.

---

### UC8 · Document OCR (tiket dari foto atau hasil scan)

#### Slide 16 · UC8 · Masalah
- **Label:** `USE CASE 8 · DOCUMENT OCR · MASALAH`
- **Judul:** Tiket dan dokumen hasil scan masih diketik ulang secara manual
- **Untuk:** tim finance dan admin yang merekap tiket, kuitansi, atau dokumen hasil scan
- **Kartu masalah:**
  1. **Ketik ulang lambat:** setiap tiket atau kuitansi diinput satu per satu untuk rekap dan reimbursement.
  2. **Rawan salah ketik:** salah tanggal atau harga baru ketahuan saat pengecekan atau audit.
  3. **Format beragam:** dua bahasa, cetakan kecil, foto miring, dan beberapa dokumen dalam satu foto sulit ditangani
     template OCR biasa.
- **Dampak bisnis:** jam kerja admin terbuang dan data rekap kurang bisa dipercaya.
- **Speaker notes:** Rekap tiket dan kuitansi masih diketik ulang satu per satu. Prosesnya lambat, rawan salah, dan
  sulit diaudit, apalagi saat formatnya berbeda-beda.

#### Slide 17 · UC8 · Solusi
- **Label:** `USE CASE 8 · DOCUMENT OCR · SOLUSI`
- **Judul:** Foto tiket langsung menjadi data tabel, satu baris per tiket
- **Mockup kiri:** `UC8_document_ocr_1.png`
  - **Satu tiket:** vision-language model membaca foto dan mengisi field tanggal, stasiun asal, stasiun tujuan, jam
    berangkat, jam tiba, dan harga. Kotak berwarna menghubungkan setiap field di tiket dengan kolom di tabel.
- **Mockup kanan:** `UC8_document_ocr_2.png`
  - **Beberapa tiket dalam satu foto:** setiap tiket dipisahkan menjadi satu baris tabel. Field yang kosong atau
    tidak sesuai format bisa diarahkan ke pengecekan manual sebelum data dipakai.
- **Catatan kaki:** Hasil ekstraksi dari repo GitHub `sndypvtra/VL-Model-for-Taiwan-Railways-tickets-Extractor` ·
  bounding box ditambahkan untuk presentasi
- **Speaker notes:** Di kiri, satu foto tiket langsung menjadi satu baris tabel, dengan warna kotak yang sama di tiket
  dan di tabel. Di kanan, foto berisi beberapa tiket tetap dipecah per tiket, sehingga rekap tidak perlu diketik ulang.

## 7. Checklist sebelum selesai

- [ ] Total 17 slide: sampul, lalu untuk setiap project satu slide Masalah diikuti satu slide Solusi.
- [ ] Slide Masalah tanpa mockup; slide Solusi berisi dua mockup project itu, utuh dan berdampingan.
- [ ] Tidak ada slide model bisnis, bukti PoC, atau langkah berikutnya (pilot, timeline, permintaan keputusan),
      dan isinya tidak disisipkan ke slide lain.
- [ ] Tidak ada slide ringkasan, anggaran, harga, agenda, penutup, atau "terima kasih"; slide terakhir adalah slide 17.
- [ ] Tidak ada angka asumsi, ilustrasi, perkiraan, atau hasil uji di teks slide dan speaker notes (lihat bagian 3).
- [ ] Angka "Hasil aktual" di UC5 dan UC7 tampil persis seperti di dokumen ini.
- [ ] Ke-16 gambar mockup dipakai dengan nama file persis seperti di bagian 4, utuh dan tidak diedit.
- [ ] Tidak ada kata "nyata", "rusuk", atau "apa adanya". Istilah mengikuti tabel di bagian 3.
- [ ] Setiap slide Solusi punya catatan kaki sumber.
- [ ] Speaker notes terisi di semua slide.
