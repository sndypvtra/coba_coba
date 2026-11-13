# Brief Claude Design: AI Vision untuk Operasional (8 use case)

Dokumen ini adalah instruksi lengkap untuk membuat satu deck presentasi dari 16 gambar mockup (PNG, 3840 × 2160).
Unggah dokumen ini bersama ke-16 gambar ke Claude Design, lalu buat **tepat 18 slide** sesuai bagian 5 dan 6.
Deck selesai di slide 18; jangan menambah slide lain.

## 1. Tujuan dan audiens

- **Audiens:** manajemen bisnis (operasional, logistik, QC, finance) dan tim teknis (IT, engineering) dalam satu
  ruangan. Setiap slide harus bisa dipahami kedua kelompok tanpa penjelasan tambahan.
- **Tujuan:** untuk setiap use case, deck menjawab dua pertanyaan secara berurutan:
  1. Masalah bisnis apa yang diselesaikan, dan bagaimana solusinya bekerja?
  2. Hasil apa yang didapat bisnis dari solusi itu?
- **Struktur:** sampul, lalu setiap use case tepat 2 slide, lalu satu slide penutup (ringkasan). Totalnya 18 slide.
  - **Slide A · Masalah & Solusi** memakai gambar `_1`.
  - **Slide B · Hasil** memakai gambar `_2`.
- **Slide yang tidak boleh dibuat.** Deck ini bukan proposal bisnis. Jangan membuat slide seperti tiga slide terakhir
  deck *Warehouse Live Ops*, dan jangan menyisipkan isinya ke slide lain, termasuk ke slide penutup:
  1. **Model bisnis:** pendapatan berulang, langganan per kamera, paket layanan, pendapatan pendukung (sewa perangkat,
     onboarding, add-on), go-to-market, target pasar, dan harga.
  2. **Bukti PoC:** rangkuman hasil uji dalam angka, seperti akurasi, error posisi, jumlah kamera yang lolos kalibrasi,
     hasil blind test, dan fokus pilot.
  3. **Langkah berikutnya:** pilot, kebutuhan dari klien (akses CCTV, perangkat, PIC), hal yang didapat klien,
     timeline per bulan, permintaan persetujuan, dan pendanaan.
  - Juga tidak ada slide anggaran atau RAB, harga, agenda, atau "terima kasih".
  - Pengecualian: angka "Hasil aktual" di UC5 dan UC7 adalah output aplikasi, bukan bukti PoC. Tampilkan angka itu di
    slide use case-nya sendiri, persis seperti tertulis di bagian 6.
- **Nada:** profesional, faktual, dan ringkas. Klaim hanya sebatas yang terlihat di gambar dan tertulis di dokumen ini.

## 2. Aturan desain

- Rasio 16:9. Semua gambar berukuran 3840 × 2160 (4K). Pakai file aslinya tanpa kompresi.
- **Satu gambar per slide use case**, tampil besar dan utuh: kolom kanan sekitar 70% lebar slide.
- Kolom kiri (sekitar 30% lebar slide) berisi teks:
  - label kecil di atas, misalnya `USE CASE 3 · PACK COUNT QC · MASALAH & SOLUSI` atau `… · HASIL`;
  - judul satu kalimat;
  - **Slide A:** blok **Masalah** lalu blok **Solusi**, dengan judul blok yang jelas;
  - **Slide B:** blok **Hasil**, ditambah baris **Hasil aktual** untuk UC5 dan UC7;
  - catatan kaki sumber di paling bawah.
- Pakai warna netral untuk blok Masalah dan warna aksen untuk blok Solusi dan Hasil. Warna aksen boleh berbeda per use
  case, tetapi tipografi, grid, dan posisi elemen sama di ke-16 slide use case.
- Gambar ditampilkan utuh. Jangan meng-crop bagian yang memotong label atau catatan kaki di dalam gambar, dan jangan
  menambah atau mengubah apa pun di dalam gambar.
- Mockup UC1–UC4 dan UC6 adalah layar yang **sudah pernah dipresentasikan**. Gambarnya dipakai tanpa perubahan.
- Speaker notes diisi dari bagian 6. Kalimatnya boleh dipersingkat, tetapi isinya tetap.

## 3. Aturan bahasa

- Bahasa Indonesia baku yang lazim di dunia kerja. Istilah teknis memakai istilah yang umum dipakai di engineering
  dan bisnis, termasuk istilah Inggris yang sudah lazim.
- Judul menyebut hasil untuk bisnis, bukan nama fitur. Satu gagasan per poin.
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
| IoU | ukuran kecocokan dua bentuk; makin mendekati satu, makin cocok |
| quality gate | pemeriksaan otomatis sebelum hasil dipakai |
| root cause, corrective action, CAPA | penyebab utama; tindakan perbaikan dan pencegahan |
| reject, underfill, overfill, giveaway | istilah QC di line produksi |
| near miss | kejadian yang hampir menjadi kecelakaan |
| PLC, WMS, TMS | sistem kontrol mesin, sistem gudang, sistem transportasi |

## 4. Gambar yang dipakai (16 file)

| Use case | File | Isi gambar | Sumber |
|---|---|---|---|
| UC1 Produce Grading | `UC1_produce_grading_1.png` | Dashboard TV di line: kelas warna setiap tomat, komposisi grade, off-colour lot terhadap limit, event log | mockup yang sudah dipresentasikan |
| | `UC1_produce_grading_2.png` | Laporan Lot: kelas warna USDA, keputusan lot, foto bukti, sebaran warna, riwayat lot, ekspor sertifikat | mockup yang sudah dipresentasikan |
| UC2 Fill Level Inspection | `UC2_fill_level_1.png` | Live Monitoring: outline botol, garis target, level isi, hasil per nozzle, tombol hentikan nozzle | mockup yang sudah dipresentasikan |
| | `UC2_fill_level_2.png` | Reject & Giveaway: daftar reject, giveaway per nozzle dengan saran tindakan, bukti reject | mockup yang sudah dipresentasikan |
| UC3 Pack Count QC | `UC3_pack_count_1.png` | Dashboard TV: isi tray dihitung per slot, tray kurang isi ditandai SHORT, posisi slot kosong | mockup yang sudah dipresentasikan |
| | `UC3_pack_count_2.png` | Detail Reject: peta slot kardus, root cause, foto dan klip bukti, timeline, corrective action | mockup yang sudah dipresentasikan |
| UC4 Parcel Dimensioning (conveyor) | `UC4_parcel_conveyor_1.png` | Dashboard TV: P × L × T dan volume setiap paket di belt, kelas ukuran, manual check | mockup yang sudah dipresentasikan |
| | `UC4_parcel_conveyor_2.png` | Rencana Muat & Tagihan: isi truk dari volume, berat volumetrik vs berat aktual per pelanggan, dasar tagihan | mockup yang sudah dipresentasikan |
| UC5 UkurPaket (APK Android) | `UC5_ukurpaket_1.png` | Layar aktual APK UkurPaket mode foto tanpa AR: ambil foto, marking, hasil benda kotak (HP), hasil benda bulat (gelas) | baru, dari foto uji di HP Urovo DT50 |
| | `UC5_ukurpaket_2.png` | Cara APK menghitung dimensi untuk dua objek: foto dengan segmentasi dan kotak 3D, depth map, kartu hasil, langkah perhitungan | baru, dari data yang sama |
| UC6 Warehouse Live Ops | `UC6_warehouse_1.png` | Live Monitoring: sorotan otomatis kamera saat near miss, peringatan langsung, peta lantai | mockup yang sudah dipresentasikan |
| | `UC6_warehouse_2.png` | Detail Insiden: klip kejadian, ringkasan, cuplikan bukti, posisi di peta, CAPA, linimasa | mockup yang sudah dipresentasikan |
| UC7 Plate & Vehicle (CCTV parkir) | `UC7_plate_vehicle_1.png` | Satu frame video hasil: CAM 1 gerbang menghitung motor, mobil, truk; CAM 2 area parkir membaca plat | baru, dari rekaman CCTV aktual |
| | `UC7_plate_vehicle_2.png` | Zoom kedua kamera, tabel hitungan per jenis, foto plat terbaca, cara kerja | baru, dari rekaman yang sama |
| UC8 Document OCR | `UC8_document_ocr_1.png` | Hasil ekstraksi satu tiket menjadi satu baris tabel, dengan bounding box per field | baru, dari repo GitHub ekstraksi tiket |
| | `UC8_document_ocr_2.png` | Hasil ekstraksi foto berisi beberapa tiket, satu baris tabel per tiket | baru, dari repo yang sama |

Video pendukung UC7 (`plate_vehicle_cctv.mp4`) tidak masuk deck. Putar terpisah atau tautkan di slide 14.

## 5. Susunan deck (18 slide)

| # | Slide | Gambar | Judul |
|---|---|---|---|
| 1 | Sampul | 8 gambar `_1` sebagai thumbnail | AI Vision untuk operasional: delapan use case dari kamera dan foto |
| 2 | UC1 · A | `UC1_produce_grading_1.png` | Setiap buah di-grade di line; lot campur warna ketahuan sebelum dikirim |
| 3 | UC1 · B | `UC1_produce_grading_2.png` | Klaim pembeli dijawab dengan data per lot, bukan perkiraan |
| 4 | UC2 · A | `UC2_fill_level_1.png` | Level isi setiap botol terlihat langsung, nozzle demi nozzle |
| 5 | UC2 · B | `UC2_fill_level_2.png` | Setiap reject punya bukti, setiap kelebihan isi terukur per nozzle |
| 6 | UC3 · A | `UC3_pack_count_1.png` | Kemasan kurang isi tertahan sebelum disegel |
| 7 | UC3 · B | `UC3_pack_count_2.png` | Setiap reject punya bukti, penyebab, dan tindakan perbaikan |
| 8 | UC4 · A | `UC4_parcel_conveyor_1.png` | P × L × T setiap paket di belt terukur tanpa meteran |
| 9 | UC4 · B | `UC4_parcel_conveyor_2.png` | Volume terukur dipakai untuk muat truk dan tagihan |
| 10 | UC5 · A | `UC5_ukurpaket_1.png` | Kurir mengukur paket dengan satu foto dari HP, tanpa meteran |
| 11 | UC5 · B | `UC5_ukurpaket_2.png` | Dimensi dihitung dari satu foto, untuk benda kotak maupun bulat |
| 12 | UC6 · A | `UC6_warehouse_1.png` | Saat AI mendeteksi bahaya, kameranya langsung tampil di layar operator |
| 13 | UC6 · B | `UC6_warehouse_2.png` | Setiap insiden punya bukti lengkap dan tindakan perbaikan |
| 14 | UC7 · A | `UC7_plate_vehicle_1.png` | Kendaraan terhitung otomatis dan plat nomor terbaca dari CCTV yang sudah ada |
| 15 | UC7 · B | `UC7_plate_vehicle_2.png` | Setiap kendaraan dihitung sekali, setiap plat tercatat dengan foto |
| 16 | UC8 · A | `UC8_document_ocr_1.png` | Foto tiket langsung menjadi data tabel, tanpa ketik ulang |
| 17 | UC8 · B | `UC8_document_ocr_2.png` | Beberapa tiket dalam satu foto tetap terbaca satu per satu |
| 18 | Penutup | – | Delapan use case, satu pola: kamera atau foto, AI, lalu data dan tindakan |

## 6. Isi per slide

### Slide 1 · Sampul

- **Judul:** AI Vision untuk operasional: delapan use case dari kamera dan foto
- **Subjudul:** Pabrik, gudang, logistik, parkir, dan dokumen. Setiap use case: masalah bisnis, solusi, dan hasilnya.
- **Visual:** grid berisi delapan gambar `_1`, masing-masing dengan nama use case di bawahnya.
- **Baris bawah:** `[isi nama tim] · [isi tanggal]`
- **Speaker notes:** Deck ini merangkum delapan use case AI vision. Setiap use case dibahas dalam dua slide: masalah
  bisnis dan solusinya, lalu hasil yang didapat bisnis.

---

### UC1 · Produce Grading

**Untuk:** packing house buah dan sayur, eksportir, dan pemasok supermarket.

#### Slide 2 · UC1 · A · Masalah & Solusi
- **Label:** `USE CASE 1 · PRODUCE GRADING · MASALAH & SOLUSI`
- **Judul:** Setiap buah di-grade di line; lot campur warna ketahuan sebelum dikirim
- **Gambar:** `UC1_produce_grading_1.png`
- **Masalah:**
  - Warna dan kematangan dicek manual dengan sampel, sehingga lot campur warna lolos ke pembeli.
  - Standar berbeda per pembeli (USDA, OECD, spec supermarket) dan sulit diterapkan konsisten di setiap shift.
- **Solusi:**
  - Kamera di atas conveyor dan edge AI mengelompokkan setiap buah ke kelas warna standar USDA, lalu menghitungnya
    sekali di count gate.
  - Dashboard TV di line menampilkan komposisi grade dan off-colour lot terhadap limit secara real-time.
  - Saat off-colour melewati limit, operator langsung diarahkan untuk sortir ulang atau memberi label Mixed Color.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Ini Dashboard TV yang terpasang di line. Setiap buah diberi kotak sesuai kelas warnanya dan
  dihitung sekali. Begitu off-colour lot melewati limit, operator tahu saat itu juga dan bisa bertindak selagi buah
  masih di line, bukan setelah lot ditolak pembeli.

#### Slide 3 · UC1 · B · Hasil
- **Label:** `USE CASE 1 · PRODUCE GRADING · HASIL`
- **Judul:** Klaim pembeli dijawab dengan data per lot, bukan perkiraan
- **Gambar:** `UC1_produce_grading_2.png`
- **Hasil:**
  - Setiap lot punya keputusan sesuai standar warna USDA, lengkap dengan foto bukti dan sebaran warna setiap buah.
  - Riwayat lot mencatat setiap alert, hold, sortir ulang, dan siapa yang menangani.
  - Sertifikat lot dalam PDF bisa langsung dikirim ke QA pembeli.
- **Catatan kaki:** sama dengan slide 2
- **Speaker notes:** Laporan Lot menyimpan keputusan, bukti, dan riwayat setiap lot. Saat ada klaim warna dari
  pembeli, tim sales menjawab dengan data lot tersebut, bukan dengan perkiraan.

---

### UC2 · Fill Level Inspection

**Untuk:** pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol.

#### Slide 4 · UC2 · A · Masalah & Solusi
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION · MASALAH & SOLUSI`
- **Judul:** Level isi setiap botol terlihat langsung, nozzle demi nozzle
- **Gambar:** `UC2_fill_level_1.png`
- **Masalah:**
  - Botol underfill lolos ke pasar dan berisiko memicu komplain serta pelanggaran ketentuan BDKT.
  - Overfill tidak terukur, padahal itu produk yang terbuang (giveaway) setiap hari. Cek manual hanya sampel berkala.
- **Solusi:**
  - Kamera di mesin pengisi dan edge AI mengukur level isi setiap botol, lalu mengubah tinggi cairan menjadi volume
    berdasarkan profil botol.
  - Status setiap nozzle tampil langsung: pass, underfill, atau overfill.
  - Supervisor bisa menghentikan nozzle yang bermasalah dari layar yang sama.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Di kamera terlihat outline botol, garis target di leher botol, dan level isi yang bergerak naik.
  Di sebelah kanan, nozzle yang underfill ditandai merah dan bisa langsung dihentikan untuk dicek, tanpa menunggu sampel
  berikutnya.

#### Slide 5 · UC2 · B · Hasil
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION · HASIL`
- **Judul:** Setiap reject punya bukti, setiap kelebihan isi terukur per nozzle
- **Gambar:** `UC2_fill_level_2.png`
- **Hasil:**
  - Botol di bawah toleransi di-reject lewat sinyal ke PLC, lalu dikonfirmasi QC atau ditandai alarm palsu.
  - Bukti setiap reject tersimpan: gambar kamera, level isi saat nozzle berhenti, dan sinyal ke PLC.
  - Giveaway per nozzle dibandingkan dengan target dan toleransi, disertai saran tindakan untuk Maintenance.
- **Catatan kaki:** sama dengan slide 4
- **Speaker notes:** Halaman ini dipakai QC dan Maintenance. Setiap reject punya bukti, dan grafik giveaway per nozzle
  menunjukkan nozzle mana yang perlu disetel, berdasarkan data, bukan perasaan.

---

### UC3 · Pack Count QC

**Untuk:** pabrik makanan dan minuman kemasan, FMCG, dan co-packer.

#### Slide 6 · UC3 · A · Masalah & Solusi
- **Label:** `USE CASE 3 · PACK COUNT QC · MASALAH & SOLUSI`
- **Judul:** Kemasan kurang isi tertahan sebelum disegel
- **Gambar:** `UC3_pack_count_1.png`
- **Masalah:**
  - Tray atau kardus kurang isi baru ketahuan setelah ada komplain dari distributor atau konsumen.
  - Cek manual hanya sampel. Penyebab kekurangan (feeder, lane filler, robot) tidak tercatat, jadi masalahnya berulang.
- **Solusi:**
  - Kamera di ujung line dan edge AI menghitung isi setiap tray per slot.
  - Slot kosong ditandai, lalu tray kurang isi diberi status SHORT dan di-reject sebelum disegel.
  - Peta posisi slot kosong menunjukkan apakah masalah berulang di lane filler yang sama.
- **Catatan kaki:** Video: simulasi 3D buatan tim · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Ini Dashboard TV di ujung line kaleng. Tray yang kurang isi ditandai SHORT dan slot kosongnya
  dilingkari. Kalau slot yang sama berulang kali kosong, itu menunjuk ke lane filler tertentu, sehingga yang
  diperbaiki adalah penyebabnya, bukan hanya kemasannya.

#### Slide 7 · UC3 · B · Hasil
- **Label:** `USE CASE 3 · PACK COUNT QC · HASIL`
- **Judul:** Setiap reject punya bukti, penyebab, dan tindakan perbaikan
- **Gambar:** `UC3_pack_count_2.png`
- **Hasil:**
  - Peta slot kardus menunjukkan slot yang kosong beserta root cause-nya.
  - Foto dan klip bukti sebelum dan sesudah kejadian, bisa diekspor ke PDF.
  - Timeline mencatat kejadian dari feeder gap sampai rework, termasuk notifikasi WhatsApp ke Line Supervisor, dan
    corrective action ditugaskan ke tim terkait.
- **Catatan kaki:** sama dengan slide 6
- **Speaker notes:** Ini detail satu reject. Investigasi selesai lebih cepat karena slot yang kosong, penyebabnya,
  penanggung jawabnya, dan buktinya ada di satu halaman yang siap ditunjukkan ke pelanggan atau auditor.

---

### UC4 · Parcel Dimensioning (conveyor)

**Untuk:** gudang distribusi, 3PL, e-commerce fulfilment, dan ekspedisi.

#### Slide 8 · UC4 · A · Masalah & Solusi
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING · MASALAH & SOLUSI`
- **Judul:** P × L × T setiap paket di belt terukur tanpa meteran
- **Gambar:** `UC4_parcel_conveyor_1.png`
- **Masalah:**
  - Ukuran paket diukur manual dengan meteran, atau tidak diukur sama sekali.
  - Tagihan hanya berdasarkan berat timbangan, padahal paket ringan tetapi besar memakan ruang truk.
- **Solusi:**
  - Kamera di atas belt bongkar muat dan edge AI mengukur P × L × T serta volume setiap paket.
  - Setiap paket dihitung sekali di count line dan dikelompokkan per kelas ukuran.
  - Paket yang ukurannya dekat batas kelas masuk manual check, bukan ditebak.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Ini Dashboard TV di belt bongkar truk. Setiap paket diberi kotak sesuai kelas ukurannya, lalu
  masuk tabel bersama P × L × T, volume, dan berat volumetriknya. Paket yang meragukan dikonfirmasi oleh petugas.

#### Slide 9 · UC4 · B · Hasil
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING · HASIL`
- **Judul:** Volume terukur dipakai untuk muat truk dan tagihan
- **Gambar:** `UC4_parcel_conveyor_2.png`
- **Hasil:**
  - Isi setiap truk dihitung dari volume terukur, dengan status selesai muat, sedang muat, atau terjadwal.
  - Berat volumetrik dibandingkan dengan berat aktual per pelanggan, dan tagihan memakai yang lebih besar.
  - Data dikirim ke TMS/WMS dan sistem invoice tanpa input ulang.
- **Catatan kaki:** sama dengan slide 8
- **Speaker notes:** Data ukuran langsung dipakai dua tim: logistik untuk rencana muat truk, dan finance untuk dasar
  tagihan. Pelanggan yang mengirim paket ringan tetapi besar ditagih sesuai ruang yang benar-benar dipakai.

---

### UC5 · UkurPaket (APK Android, mode foto)

**Untuk:** kurir pickup, counter ekspedisi, dan agen. Perangkat: HP Android atau handheld kurir, diuji di Urovo DT50.

#### Slide 10 · UC5 · A · Masalah & Solusi
- **Label:** `USE CASE 5 · UKURPAKET · MASALAH & SOLUSI`
- **Judul:** Kurir mengukur paket dengan satu foto dari HP, tanpa meteran
- **Gambar:** `UC5_ukurpaket_1.png`
- **Masalah:**
  - Saat pickup dan di counter, ukuran paket diukur dengan meteran atau hanya ditebak, sehingga berat volumetrik dan
    berat tagih sering tidak sesuai.
  - Handheld kurir umumnya tidak punya ARCore atau sensor depth, sehingga aplikasi ukur berbasis AR tidak bisa dipakai.
- **Solusi (layar di gambar):**
  - **Ambil foto:** APK memandu sudut foto dan memastikan HP diam sebelum memotret.
  - **Marking objek:** kurir tap objek atau tarik kotak, lalu AI memisahkan objek dari latar belakang.
  - **Hasil ukur:** P × L × T, berat volumetrik, dan status kualitas langsung tampil di HP, untuk benda kotak maupun
    benda bulat (diameter × diameter × tinggi).
- **Catatan kaki:** Tampilan aktual APK UkurPaket (mode foto, tanpa AR) dengan foto dari HP Urovo DT50
- **Speaker notes:** Layar-layar ini adalah tampilan aktual APK, diisi foto dari HP uji. Kurir cukup memotret dan
  menandai objek, lalu hasilnya langsung keluar di layar yang sama tanpa ARCore atau sensor tambahan. Benda kotak
  mendapat status Akurat, sedangkan benda bulat tetap diukur tetapi ditandai Perlu Dicek karena bentuknya bukan kotak.
  Berat volumetrik bukan berat aktual: berat aktual tetap dari timbangan, dan berat tagih adalah yang lebih besar dari
  keduanya.

#### Slide 11 · UC5 · B · Hasil
- **Label:** `USE CASE 5 · UKURPAKET · HASIL`
- **Judul:** Dimensi dihitung dari satu foto, untuk benda kotak maupun bulat
- **Gambar:** `UC5_ukurpaket_2.png`
- **Hasil:**
  - APK menggabungkan segmentasi, depth map, sensor gravitasi, dan jarak fokus lensa untuk membentuk kotak 3D di
    sekitar objek, lalu menghitung ukurannya dalam cm.
  - Quality gate memberi status Akurat atau Perlu Dicek, misalnya untuk foto buram, objek terpotong, atau bentuk yang
    bukan kotak.
  - Hasil berstatus Perlu Dicek tetap bisa dipakai kurir, dan ukurannya tersimpan bersama status serta foto bukti
    untuk dicek ulang oleh admin atau hub.
- **Hasil aktual APK (tampilkan persis):**
  - HP dengan clear case: **15,5 × 6,4 × 1,8 cm** (P × L × T), berat volumetrik **0,03 kg**, jarak lensa ke objek
    **12 cm** (autofocus), tinggi kamera di atas meja **9 cm**, kecocokan kotak 3D (IoU) **0,97**, status
    **Akurat · skor 100**.
  - Gelas dengan sedotan: **7,1 × 7,1 × 23,7 cm** (diameter × diameter × tinggi), berat volumetrik **0,20 kg**, jarak
    lensa ke objek **24 cm** (autofocus), tinggi kamera di atas meja **30 cm**, kecocokan kotak 3D (IoU) **0,85**,
    status **Perlu Dicek · skor 75**.
- **Catatan kaki:** Data: hasil ukur dan depth map yang disimpan APK UkurPaket · kotak 3D digambar dari koordinat yang
  dihitung APK
- **Speaker notes:** Di setiap baris, kiri adalah foto dengan hasil segmentasi dan kotak 3D, dan tengah adalah depth
  map: merah berarti dekat, biru berarti jauh. Garis putus-putus adalah garis kotak yang tertutup dari kamera. HP
  terukur 15,5 × 6,4 × 1,8 cm dengan status Akurat. Gelas terukur 7,1 × 7,1 × 23,7 cm, dibaca diameter × diameter ×
  tinggi dengan tinggi termasuk sedotan, dan diberi status Perlu Dicek karena bentuknya bukan kotak.

---

### UC6 · Warehouse Live Ops

**Untuk:** 3PL dan distribusi, manufaktur, cold storage, dan e-commerce fulfilment.

#### Slide 12 · UC6 · A · Masalah & Solusi
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS · MASALAH & SOLUSI`
- **Judul:** Saat AI mendeteksi bahaya, kameranya langsung tampil di layar operator
- **Gambar:** `UC6_warehouse_1.png`
- **Masalah:**
  - Risiko tabrakan orang dan forklift baru ketahuan setelah terjadi, karena operator tidak mungkin memantau belasan
    layar CCTV sepanjang shift.
  - Mencari bukti satu insiden berarti memutar ulang rekaman berjam-jam.
- **Solusi:**
  - CCTV yang sudah ada dan edge AI mendeteksi orang, forklift, APD, dan zona di setiap kamera.
  - Saat near miss terdeteksi, kamera terkait otomatis tampil di layar utama.
  - Peringatan masuk ke daftar dan bisa dikonfirmasi atau ditandai alarm palsu, lengkap dengan posisinya di peta lantai.
- **Catatan kaki:** Cuplikan kamera: NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0) · layar mockup, angka di layar adalah
  ilustrasi
- **Speaker notes:** Satu operator bisa mengawasi banyak kamera karena AI yang menyaring kejadian. Begitu near miss
  terdeteksi, kameranya tampil sendiri di layar besar dan peringatannya masuk ke daftar di sebelah kanan.

#### Slide 13 · UC6 · B · Hasil
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS · HASIL`
- **Judul:** Setiap insiden punya bukti lengkap dan tindakan perbaikan
- **Gambar:** `UC6_warehouse_2.png`
- **Hasil:**
  - Klip sebelum dan sesudah kejadian, cuplikan bukti, dan posisi di peta tersimpan otomatis per insiden.
  - Linimasa mencatat deteksi, notifikasi WhatsApp, sampai insiden ditangani.
  - CAPA dengan penanggung jawab dan tenggat, serta ekspor bukti PDF untuk audit K3.
- **Catatan kaki:** sama dengan slide 12
- **Speaker notes:** Investigasi selesai lebih cepat karena klip, posisi, dan linimasa sudah tersimpan per insiden.
  Tindakan perbaikan juga tercatat sampai selesai, sehingga siap untuk audit.

---

### UC7 · Plate Recognition & Vehicle Counting (CCTV parkir)

**Untuk:** pengelola parkir, depot dan gudang distribusi, kawasan industri, dan gedung perkantoran.

#### Slide 14 · UC7 · A · Masalah & Solusi
- **Label:** `USE CASE 7 · PLATE & VEHICLE · MASALAH & SOLUSI`
- **Judul:** Kendaraan terhitung otomatis dan plat nomor terbaca dari CCTV yang sudah ada
- **Gambar:** `UC7_plate_vehicle_1.png` (satu frame dari video hasil)
- **Masalah:**
  - Kendaraan masuk, keluar, dan parkir dicatat manual oleh petugas. Plat ditulis tangan, sehingga rawan salah dan
    terlewat saat ramai.
  - Tidak ada data jumlah motor, mobil, dan truk. Mencari kapan kendaraan tertentu datang berarti memutar ulang
    rekaman CCTV.
- **Solusi:**
  - CCTV yang sudah ada dan edge AI mendeteksi serta melacak setiap kendaraan. Motor, mobil, dan truk/bus dihitung
    sekali per ID tracking, terpisah antara yang bergerak dan yang parkir.
  - Plat nomor dibaca dari kamera yang dekat dengan jalur kendaraan (deteksi plat dan OCR), lalu dicatat bersama foto
    plat, jenis kendaraan, kamera, dan waktu.
- **Hasil aktual pada video (tampilkan persis):** kendaraan yang bergerak di gerbang terhitung **3 motor** dan
  **1 truk**, masing-masing sekali.
- **Catatan kaki:** Video: rekaman CCTV aktual dari dataset publik Hugging Face `rithwikn/ai_cctv_videos`, dua kamera
  digabung dalam satu video · plat nomor Tanzania
- **Speaker notes:** Video ini menggabungkan dua kamera CCTV aktual. Kamera gerbang menghitung kendaraan, dan kamera
  area parkir membaca plat. Setiap kendaraan diberi ID tracking sehingga dihitung sekali. Kendaraan yang bergerak
  diberi label "bergerak", sedangkan yang parkir tetap masuk hitungan "di area".

#### Slide 15 · UC7 · B · Hasil
- **Label:** `USE CASE 7 · PLATE & VEHICLE · HASIL`
- **Judul:** Setiap kendaraan dihitung sekali, setiap plat tercatat dengan foto
- **Gambar:** `UC7_plate_vehicle_2.png`
- **Hasil:**
  - Hitungan kendaraan dipisah per jenis, dan setiap kendaraan dihitung sekali per ID tracking.
  - Plat ditetapkan setelah beberapa bacaan sama, bukan dari satu frame, lalu tercatat bersama foto plat, jenis
    kendaraan, kamera, dan waktu.
  - Pejalan kaki yang mirip motor, kabin truk yang masuk lebih dulu, dan rekaman CCTV yang sempat beku ditangani
    sehingga kendaraan tidak terhitung dua kali.
  - Kamera baca plat dipasang dekat jalur masuk; kamera yang jauh dari jalur dipakai untuk menghitung kendaraan.
- **Hasil aktual pada video (tampilkan persis):** plat terbaca **T 649 EHP** dan **T 119 ELM**, keduanya sesuai dengan
  plat di video.
- **Catatan kaki:** sama dengan slide 14
- **Speaker notes:** Di area parkir, plat dibaca dari banyak frame dan baru ditetapkan setelah bacaannya konsisten,
  sehingga hasilnya stabil. Plat di kamera gerbang tidak dibaca karena terlalu jauh, jadi kamera baca plat dipasang
  dekat jalur masuk.

---

### UC8 · Document OCR (tiket dari foto atau hasil scan)

**Untuk:** tim finance dan admin yang merekap tiket, kuitansi, atau dokumen hasil scan, misalnya untuk reimbursement
perjalanan dinas dan rekap biaya.

#### Slide 16 · UC8 · A · Masalah & Solusi
- **Label:** `USE CASE 8 · DOCUMENT OCR · MASALAH & SOLUSI`
- **Judul:** Foto tiket langsung menjadi data tabel, tanpa ketik ulang
- **Gambar:** `UC8_document_ocr_1.png`
- **Masalah:**
  - Tiket, kuitansi, dan dokumen hasil scan diketik ulang secara manual. Prosesnya lambat, rawan salah ketik, dan
    sulit diaudit.
  - Format dokumen beragam (dua bahasa, cetakan kecil, foto miring), sehingga sulit ditangani template OCR biasa.
- **Solusi:**
  - Vision-language model membaca foto dan langsung mengisi field: tanggal, stasiun asal, stasiun tujuan, jam
    berangkat, jam tiba, dan harga.
  - Kotak berwarna menghubungkan setiap field di tiket dengan kolom yang sama di tabel hasil.
- **Catatan kaki:** Hasil ekstraksi dari repo GitHub `sndypvtra/VL-Model-for-Taiwan-Railways-tickets-Extractor` ·
  bounding box ditambahkan untuk presentasi
- **Speaker notes:** Ini hasil ekstraksi model pada satu foto tiket. Warna kotak membantu membaca hasilnya: biru untuk
  tanggal, hijau untuk stasiun, oranye untuk jam, dan ungu untuk harga, dengan warna yang sama di tiket dan di tabel.

#### Slide 17 · UC8 · B · Hasil
- **Label:** `USE CASE 8 · DOCUMENT OCR · HASIL`
- **Judul:** Beberapa tiket dalam satu foto tetap terbaca satu per satu
- **Gambar:** `UC8_document_ocr_2.png`
- **Hasil:**
  - Foto berisi beberapa tiket dipisahkan per tiket, dan setiap tiket menjadi satu baris tabel.
  - Nomor tiket di foto sama dengan nomor baris di tabel, sehingga mudah dicocokkan.
  - Field yang kosong atau tidak sesuai format bisa diarahkan ke pengecekan manual sebelum data dipakai.
- **Catatan kaki:** sama dengan slide 16
- **Speaker notes:** Foto yang berisi beberapa tiket tetap dipecah per tiket, sehingga rekap tidak perlu diketik ulang.
  Untuk dokumen yang sulit dibaca, field yang kosong diarahkan ke pengecekan manual, sehingga data yang masuk ke rekap
  tetap bersih.

---

### Slide 18 · Penutup

- **Label:** `RINGKASAN`
- **Judul:** Delapan use case, satu pola: kamera atau foto, AI, lalu data dan tindakan
- **Isi:** tabel delapan baris dengan kolom **Use case · Masalah · Solusi · Hasil untuk bisnis**, tanpa angka:

| Use case | Masalah | Solusi | Hasil untuk bisnis |
|---|---|---|---|
| Produce Grading | lot campur warna lolos; cek manual hanya sampel | setiap buah di-grade di line | lot bermasalah ditahan sebelum dikirim, dengan bukti per lot |
| Fill Level Inspection | underfill lolos; giveaway tidak terukur | level isi setiap botol terukur per nozzle | underfill di-reject; giveaway terukur dan bisa dikurangi |
| Pack Count QC | kemasan kurang isi baru ketahuan setelah komplain | isi setiap kemasan dihitung per slot | kemasan kurang isi ditahan sebelum disegel; penyebab tercatat |
| Parcel Dimensioning | ukuran paket tidak terukur | P × L × T setiap paket di belt | muat truk dan tagihan berdasarkan volume terukur |
| UkurPaket | ukur manual saat pickup dan di counter | ukur dari satu foto di HP kurir | ukuran dan status kualitas langsung di HP, dengan foto bukti |
| Warehouse Live Ops | bahaya baru ketahuan setelah terjadi | AI di CCTV yang sudah ada | peringatan saat kejadian; bukti dan CAPA per insiden |
| Plate & Vehicle | kendaraan dan plat dicatat manual | hitung kendaraan dan baca plat dari CCTV | data kendaraan per jenis; plat tercatat dengan foto |
| Document OCR | tiket dan dokumen diketik ulang | vision-language model membaca foto | field langsung menjadi tabel, siap direkap |

- **Speaker notes:** Delapan use case ini memakai pola yang sama: kamera atau foto yang sudah ada, AI yang membaca
  gambarnya, lalu data dan tindakan yang langsung dipakai tim operasional.
- Slide ini **hanya** ringkasan masalah, solusi, dan hasil. Jangan tambahkan langkah berikutnya, pilot, timeline,
  harga, model bisnis, angka bukti, atau ucapan terima kasih.

## 7. Checklist sebelum selesai

- [ ] Total 18 slide: sampul, 8 use case × 2 slide (A: masalah & solusi, B: hasil), dan satu slide penutup.
- [ ] Setiap slide use case memakai satu gambar besar sesuai bagian 5, utuh dan tidak diedit.
- [ ] Tidak ada slide model bisnis, bukti PoC, atau langkah berikutnya (pilot, timeline, permintaan keputusan),
      dan isinya tidak disisipkan ke slide lain, termasuk slide penutup.
- [ ] Tidak ada slide anggaran, harga, agenda, atau "terima kasih"; slide terakhir adalah slide 18.
- [ ] Tidak ada angka asumsi, ilustrasi, perkiraan, atau hasil uji di teks slide dan speaker notes (lihat bagian 3).
- [ ] Angka "Hasil aktual" di UC5 dan UC7 tampil persis seperti di dokumen ini.
- [ ] Tidak ada kata "nyata", "rusuk", atau "apa adanya". Istilah mengikuti tabel di bagian 3.
- [ ] Setiap slide use case punya catatan kaki sumber.
- [ ] Speaker notes terisi di semua slide.
