# Prompt Claude Design: AI Vision Use Cases, 8 use case × 2 slide

Satu deck yang merangkum delapan use case AI vision. Setiap use case **hanya punya 2 slide**: slide A menjawab
**masalah bisnis → solusi**, slide B menunjukkan **hasil dan bukti** yang bisa dipakai klien untuk mengambil keputusan.
Ditambah sampul dan penutup, total **18 slide**.

## 1. Aturan umum

**Format**
- Rasio 16:9. Semua gambar ada di folder `images/`, berukuran 3840 × 2160 (4K). Pakai file aslinya, jangan dikompres.
- Gambar adalah isi utama slide: tampilkan besar (minimal ±70% luas slide), utuh, tanpa crop yang memotong angka,
  label, atau catatan kaki di dalam gambar. Jangan menambah, menghapus, atau mengubah angka di dalam gambar.
- Mockup UC1–UC4 dan UC6 adalah layar yang **sudah dipresentasikan**. Gambarnya dipakai apa adanya; tidak ada layar
  yang didesain ulang. (UC6 dirender ulang di resolusi 2× dari file HTML yang sama supaya tajam di 4K; isinya identik.)
- Setiap slide: label kecil di atas (mis. `USE CASE 3 · PACK COUNT QC · MASALAH & SOLUSI`), judul satu kalimat,
  gambar, 3–4 poin pendek, dan catatan kaki sumber. Speaker notes diisi dari bagian 4.
- Warna aksen per use case boleh berbeda, tetapi tipografi, grid, dan posisi elemen sama di 16 slide use case.

**Bahasa**
- Bahasa Indonesia profesional. Istilah teknis dan bisnis memakai istilah yang umum dipakai di industri, termasuk
  istilah Inggris yang sudah lazim: *dashboard, real-time, live monitoring, edge AI, bounding box, tracking,
  segmentasi, depth map, OCR, reject, underfill, overfill, giveaway, near miss, CAPA, PLC, WMS, TMS, ground truth,
  blind test*.
- Gunakan **"aktual"**, bukan "nyata" (rekaman aktual, berat aktual, tampilan aktual). Gunakan "PoC" untuk hasil
  uji, "pilot" untuk tahap berikutnya.
- Judul menyebut hasil untuk bisnis, bukan nama fitur. Kalimat pendek, satu gagasan per poin, tanpa kata promosi
  (revolusioner, canggih, mutakhir, seamless, game changer, dan sejenisnya).
- Angka hanya dari gambar atau dari dokumen ini. Angka hasil uji selalu diberi label **PoC**. Angka di layar mockup
  UC1–UC4 dan UC6 adalah ilustrasi kecuali bertanda PoC (sudah tertulis di gambar), jangan disebut sebagai hasil.
- Tidak ada harga, rupiah, atau perhitungan pajak di deck ini.

## 2. Gambar yang dipakai (16 file)

| Use case | File | Isi gambar | Sumber |
|---|---|---|---|
| UC1 Produce Grading | `UC1_produce_grading_1.png` | Dashboard TV di line: kelas warna setiap tomat, off-colour lot vs limit | mockup existing `PG_03_dashboard_tv_tomat` |
| | `UC1_produce_grading_2.png` | Laporan Lot: keputusan lot, foto bukti, riwayat, ekspor sertifikat | mockup existing `PG_05_laporan_lot` |
| UC2 Fill Level Inspection | `UC2_fill_level_1.png` | Live Monitoring: level isi per botol, status per nozzle | mockup existing `FL_02_live_monitoring` |
| | `UC2_fill_level_2.png` | Reject & Giveaway: reject per nozzle, giveaway per nozzle, bukti reject | mockup existing `FL_04_reject_giveaway` |
| UC3 Pack Count QC | `UC3_pack_count_1.png` | Dashboard TV: tray dihitung, slot kosong ditandai SHORT | mockup existing `PC_03_dashboard_tv_tray` |
| | `UC3_pack_count_2.png` | Detail Reject: peta slot, klip bukti, timeline sampai rework | mockup existing `PC_05_detail_reject` |
| UC4 Parcel Dimensioning (conveyor) | `UC4_parcel_conveyor_1.png` | Dashboard TV: P × L × T setiap paket di belt | mockup existing `PD_03_dashboard_tv` |
| | `UC4_parcel_conveyor_2.png` | Muat & Tagihan: isi truk dari volume, berat volumetrik per pelanggan | mockup existing `PD_04_muat_tagihan` |
| UC5 UkurPaket (APK Android) | `UC5_ukurpaket_1.png` | 3 layar aktual APK UkurPaket 0.4.6, mode foto tanpa AR: ambil foto → marking → hasil | baru, dari data ZIP sesi `20261110_131251` |
| | `UC5_ukurpaket_2.png` | Foto + segmentasi + kotak 3D berdampingan dengan depth map, plus 5 langkah cara hitung | baru, dari data ZIP yang sama |
| UC6 Warehouse Live Ops | `UC6_warehouse_1.png` | Live Monitoring: auto-popup kamera saat near miss, alert, mini map | mockup existing `03_live_monitoring` |
| | `UC6_warehouse_2.png` | Detail Insiden & Bukti: klip 10 detik, timeline, CAPA, ekspor PDF | mockup existing `06_detail_insiden` |
| UC7 Plate & Vehicle (CCTV parkir) | `UC7_plate_vehicle_1.png` | <<UC7_IMG1>> | baru, dari video hasil `plate_vehicle_cctv.mp4` |
| | `UC7_plate_vehicle_2.png` | <<UC7_IMG2>> | baru, dari video hasil yang sama |
| UC8 Document OCR | `UC8_document_ocr_1.png` | Hasil repo apa adanya, 1 tiket → 1 baris tabel, dengan bounding box per field | baru, dari `results/single0.jpeg` |
| | `UC8_document_ocr_2.png` | Hasil repo apa adanya, 2 tiket dan 3 tiket dalam satu foto → 1 baris per tiket | baru, dari `results/multiple0.jpeg` dan `multiple1.jpeg` |

Video pendukung (tidak masuk deck, diputar terpisah atau ditautkan di slide UC7): `plate_vehicle_cctv.mp4`.

## 3. Susunan deck (18 slide)

| # | Slide | Gambar | Judul |
|---|---|---|---|
| 1 | Sampul | 8 gambar `_1` sebagai thumbnail kecil | AI Vision untuk operasional: 8 use case dari kamera dan foto |
| 2 | UC1 · A | `UC1_produce_grading_1.png` | Setiap buah di-grade di line; lot campur warna ketahuan sebelum dikirim |
| 3 | UC1 · B | `UC1_produce_grading_2.png` | Klaim pembeli dijawab dengan data per lot, bukan perkiraan |
| 4 | UC2 · A | `UC2_fill_level_1.png` | Level isi setiap botol terlihat langsung, nozzle demi nozzle |
| 5 | UC2 · B | `UC2_fill_level_2.png` | Setiap reject punya bukti, setiap mL lebih terhitung per nozzle |
| 6 | UC3 · A | `UC3_pack_count_1.png` | Kemasan kurang isi tertahan sebelum disegel |
| 7 | UC3 · B | `UC3_pack_count_2.png` | Setiap reject punya bukti, penyebab, dan tindakan perbaikan |
| 8 | UC4 · A | `UC4_parcel_conveyor_1.png` | P × L × T setiap paket di belt terukur tanpa meteran |
| 9 | UC4 · B | `UC4_parcel_conveyor_2.png` | Volume terukur dipakai untuk muat truk dan tagihan |
| 10 | UC5 · A | `UC5_ukurpaket_1.png` | Kurir mengukur paket dengan satu foto dari HP, tanpa meteran |
| 11 | UC5 · B | `UC5_ukurpaket_2.png` | Dimensi dihitung dari satu foto: segmentasi, depth map, dan kotak 3D |
| 12 | UC6 · A | `UC6_warehouse_1.png` | Saat AI mendeteksi bahaya, kameranya langsung tampil di layar operator |
| 13 | UC6 · B | `UC6_warehouse_2.png` | Setiap insiden punya bukti lengkap dan tindakan perbaikan |
| 14 | UC7 · A | `UC7_plate_vehicle_1.png` | <<UC7_TITLE_A>> |
| 15 | UC7 · B | `UC7_plate_vehicle_2.png` | <<UC7_TITLE_B>> |
| 16 | UC8 · A | `UC8_document_ocr_1.png` | Foto tiket langsung menjadi data tabel, tanpa ketik ulang |
| 17 | UC8 · B | `UC8_document_ocr_2.png` | Beberapa tiket dalam satu foto tetap terbaca satu per satu |
| 18 | Penutup | – | Ringkasan 8 use case: masalah → hasil, lalu langkah pilot |

## 4. Isi per slide

### Slide 1 · Sampul

- **Judul:** AI Vision untuk operasional: 8 use case dari kamera dan foto
- **Subjudul:** Factory, warehouse, logistik, parkir, dan dokumen. Setiap use case: masalah bisnis, solusi, dan bukti.
- **Visual:** grid 4 × 2 thumbnail dari delapan gambar `_1`, masing-masing diberi nama use case di bawahnya.
- **Baris bawah:** `[isi nama tim] · [isi tanggal]`
- **Speaker notes:** Deck ini merangkum delapan use case AI vision. Setiap use case dibahas dalam dua slide: masalah
  bisnis dan solusinya, lalu hasil dan bukti yang sudah ada. Angka hasil uji selalu ditandai PoC.

---

### UC1 · Produce Grading

**Untuk:** packing house buah dan sayur, eksportir, pemasok supermarket.

#### Slide 2 · UC1 · A · Masalah & Solusi
- **Label:** `USE CASE 1 · PRODUCE GRADING · MASALAH & SOLUSI`
- **Judul:** Setiap buah di-grade di line; lot campur warna ketahuan sebelum dikirim
- **Gambar:** `UC1_produce_grading_1.png`
- **Masalah:**
  - Warna dan kematangan dicek manual dengan sampel kecil; lot campur warna lolos ke pembeli.
  - Standar berbeda per pembeli (USDA, OECD, spec supermarket) dan sulit diterapkan konsisten tiap shift.
- **Solusi:**
  - Kamera di atas conveyor dan edge AI membaca kelas warna setiap buah, dihitung sekali di count gate.
  - Off-colour lot dibandingkan dengan limit secara real-time; di layar: 17% vs limit 10% → label Mixed Color atau
    sortir ulang 7 buah.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC
- **Speaker notes:** Ini Dashboard TV di line. Setiap tomat diberi kotak sesuai kelas warna USDA dan dihitung sekali.
  Banner kuning menunjukkan off-colour lot 17%, di atas limit 10%, jadi lot diberi label Mixed Color atau 7 buah
  disortir ulang. Keputusan ini diambil saat buah masih di line, bukan setelah lot ditolak pembeli.

#### Slide 3 · UC1 · B · Hasil & Bukti
- **Label:** `USE CASE 1 · PRODUCE GRADING · HASIL & BUKTI`
- **Judul:** Klaim pembeli dijawab dengan data per lot, bukan perkiraan
- **Gambar:** `UC1_produce_grading_2.png`
- **Poin:**
  - Setiap lot punya keputusan sesuai standar warna USDA, lengkap dengan foto bukti dan sebaran warna setiap buah.
  - Riwayat lot (alert, hold, sortir ulang, oleh siapa) dan sertifikat lot PDF untuk QA pembeli.
  - **PoC:** 75 dari 78 tomat sama dengan cek mata secara blind test, sisanya beda 1 kelas. Lemon: 18 dari 24 dalam
    ±1 derajat bagan warna OECD.
- **Catatan kaki:** sama dengan slide 2
- **Speaker notes:** Laporan Lot menyimpan keputusan, bukti, dan riwayat setiap lot. Kalau ada klaim warna dari
  pembeli, tim sales menjawab dengan data lot tersebut. Hasil PoC: 75 dari 78 tomat sama dengan cek mata secara
  blind test. Di pilot, kecocokan ini diuji ulang oleh QC pabrik.

---

### UC2 · Fill Level Inspection

**Untuk:** pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol.

#### Slide 4 · UC2 · A · Masalah & Solusi
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION · MASALAH & SOLUSI`
- **Judul:** Level isi setiap botol terlihat langsung, nozzle demi nozzle
- **Gambar:** `UC2_fill_level_1.png`
- **Masalah:**
  - Botol underfill lolos ke pasar: risiko komplain dan ketentuan BDKT.
  - Overfill tidak terukur, padahal itu produk yang terbuang (giveaway) setiap hari; cek manual hanya sampel per jam.
- **Solusi:**
  - Kamera samping dengan backlight di mesin pengisi; edge AI mengukur level isi setiap frame.
  - Tinggi cairan diubah menjadi volume dari profil botol; underfill di-reject lewat sinyal PLC.
- **Catatan kaki:** Video: Pexels 8720278 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC
- **Speaker notes:** Di kamera terlihat outline botol, garis target di leher botol, dan level isi dalam persen dan
  mL. Di kanan, status nozzle 1–8; nozzle yang underfill ditandai merah dan bisa langsung dihentikan untuk dicek,
  tanpa menunggu sampel per jam.

#### Slide 5 · UC2 · B · Hasil & Bukti
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION · HASIL & BUKTI`
- **Judul:** Setiap reject punya bukti, setiap mL lebih terhitung per nozzle
- **Gambar:** `UC2_fill_level_2.png`
- **Poin:**
  - Reject underfill per nozzle, masing-masing dikonfirmasi QC atau ditandai alarm palsu.
  - Giveaway per nozzle terhadap target dan toleransi, dengan saran tindakan untuk tim teknik.
  - Bukti reject: gambar kamera, level saat nozzle berhenti, dan sinyal ke PLC.
  - **PoC:** level isi terukur setiap frame pada rekaman aktual mesin pengisi. Klip berakhir di 67% saat botol masih
    diisi, jadi belum ada keputusan pass/reject; angka mL memakai contoh SKU 500 mL.
- **Catatan kaki:** sama dengan slide 4
- **Speaker notes:** Halaman ini dipakai QC dan Maintenance. Setiap reject punya bukti, dan giveaway per nozzle
  menunjukkan nozzle mana yang perlu disetel. Sampaikan terus terang batas PoC: klip berakhir di 67%. Di pilot,
  level per nozzle dibandingkan dengan check weigher.

---

### UC3 · Pack Count QC

**Untuk:** pabrik makanan dan minuman kemasan, FMCG, co-packer.

#### Slide 6 · UC3 · A · Masalah & Solusi
- **Label:** `USE CASE 3 · PACK COUNT QC · MASALAH & SOLUSI`
- **Judul:** Kemasan kurang isi tertahan sebelum disegel
- **Gambar:** `UC3_pack_count_1.png`
- **Masalah:**
  - Tray atau kardus kurang isi baru ketahuan setelah komplain distributor atau konsumen.
  - Cek manual hanya sampel; penyebab kekurangan (feeder, lane filler, robot) tidak tercatat, jadi masalah berulang.
- **Solusi:**
  - Kamera di atas ujung line atau packing station; edge AI menghitung isi setiap tray dan kardus per slot.
  - Slot kosong dilingkari merah, tray ditandai SHORT dan dialihkan sebelum disegel.
- **Catatan kaki:** Video: simulasi 3D buatan tim dengan data kebenaran (ground truth) · layar mockup, angka
  ilustrasi kecuali yang bertanda PoC
- **Speaker notes:** Dashboard TV di ujung line kaleng. Tray yang kurang isi ditandai SHORT dan slot kosongnya
  dilingkari. Kalau slot yang sama berulang kosong, itu menunjuk ke lane filler tertentu, jadi yang diperbaiki
  adalah penyebabnya, bukan hanya kemasannya.

#### Slide 7 · UC3 · B · Hasil & Bukti
- **Label:** `USE CASE 3 · PACK COUNT QC · HASIL & BUKTI`
- **Judul:** Setiap reject punya bukti, penyebab, dan tindakan perbaikan
- **Gambar:** `UC3_pack_count_2.png`
- **Poin:**
  - Peta slot kardus: B2 dan C5 kosong (18/20), penyebab feeder gap.
  - Foto bukti dan klip 10 detik sebelum–sesudah, bisa diekspor ke PDF.
  - Timeline: feeder gap → empty pick → kardus di-hold → WhatsApp → rework 20/20, plus corrective action.
  - **PoC (simulasi 3D dengan ground truth):** tray 7 dari 7 benar (181 dari 181 pembacaan), kardus 3 dari 3 benar,
    2 dari 2 empty pick ditemukan.
- **Catatan kaki:** sama dengan slide 6
- **Speaker notes:** Ini detail satu reject. Investigasi yang biasanya memakan waktu selesai dalam hitungan menit:
  slot mana yang kosong, kenapa, siapa yang menangani, dan bukti yang siap untuk pelanggan atau audit.

---

### UC4 · Parcel Dimensioning (conveyor)

**Untuk:** gudang distribusi, 3PL, e-commerce fulfilment, ekspedisi.

#### Slide 8 · UC4 · A · Masalah & Solusi
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING · MASALAH & SOLUSI`
- **Judul:** P × L × T setiap paket di belt terukur tanpa meteran
- **Gambar:** `UC4_parcel_conveyor_1.png`
- **Masalah:**
  - Ukuran paket diukur manual dengan meteran, atau tidak diukur sama sekali.
  - Tagihan hanya berdasarkan berat timbangan, padahal paket ringan tapi besar memakan ruang truk.
- **Solusi:**
  - Kamera di atas belt bongkar/muat; edge AI mengukur P × L × T dan menghitung setiap paket di count line.
  - Paket yang ukurannya dekat batas kelas masuk manual check, tidak ditebak.
- **Catatan kaki:** Video: Pexels 5370836 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC
- **Speaker notes:** Dashboard TV di belt bongkar truk. Setiap paket diberi kotak sesuai kelas ukuran, lalu masuk
  tabel dengan P × L × T, volume, dan berat volumetrik. Paket yang meragukan dikonfirmasi orang.

#### Slide 9 · UC4 · B · Hasil & Bukti
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING · HASIL & BUKTI`
- **Judul:** Volume terukur dipakai untuk muat truk dan tagihan
- **Gambar:** `UC4_parcel_conveyor_2.png`
- **Poin:**
  - Isi tiap truk dihitung dari volume terukur: selesai muat, sedang muat, terjadwal.
  - Berat volumetrik (P × L × T ÷ 6000) vs berat aktual per pelanggan; paket ringan tapi besar ditagih dari volume.
  - Data dikirim ke TMS/WMS tanpa input ulang.
  - **PoC (rekaman aktual):** 8 dari 8 paket terhitung, sama dengan hitungan manual. Karton uji terbaca 340,5 mm,
    ukuran aktualnya 340 mm.
- **Catatan kaki:** Layar mockup, angka ilustrasi kecuali yang bertanda PoC · laju per jam di layar adalah perkiraan
  dari klip 17 detik
- **Speaker notes:** Data ukuran langsung dipakai dua tim: logistik untuk rencana muat truk, finance untuk dasar
  tagihan. Di pilot, P × L × T dibandingkan dengan meteran pada 100 paket, target ±1 cm.

---

### UC5 · UkurPaket (APK Android, mode foto)

**Untuk:** kurir pickup, counter ekspedisi, agen. Perangkat: HP Android atau handheld kurir (diuji di Urovo DT50).

#### Slide 10 · UC5 · A · Masalah & Solusi
- **Label:** `USE CASE 5 · UKURPAKET · MASALAH & SOLUSI`
- **Judul:** Kurir mengukur paket dengan satu foto dari HP, tanpa meteran
- **Gambar:** `UC5_ukurpaket_1.png`
- **Masalah:**
  - Di pickup dan counter, ukuran paket diukur pakai meteran atau ditebak, jadi berat volumetrik dan berat tagih
    sering tidak sesuai.
  - Handheld kurir umumnya tidak punya ARCore atau sensor depth, jadi aplikasi ukur berbasis AR tidak bisa dipakai.
- **Solusi (3 langkah di APK, terlihat di gambar):**
  - **Ambil foto:** panduan sudut 30–60° dan cek HP diam sebelum memotret.
  - **Marking objek:** kurir tap paket atau tarik kotak; AI memotong outline paket (segmentasi).
  - **Hasil ukur:** P × L × T, berat volumetrik, dan skor kualitas langsung di HP, lalu "Pakai ukuran ini".
- **Catatan kaki:** Tampilan aktual APK UkurPaket 0.4.6 (mode foto, tanpa AR) · data foto dari sesi 20261110_131251
- **Speaker notes:** Tiga layar ini adalah tampilan aktual APK, diisi dengan foto dari HP uji. Kurir cukup memotret
  dari pojok paket, tap paketnya, dan hasil ukur keluar di layar yang sama. Tidak perlu ARCore atau sensor
  tambahan. Berat volumetrik bukan berat aktual: berat aktual tetap dari timbangan, dan berat tagih adalah yang
  lebih besar dari keduanya.

#### Slide 11 · UC5 · B · Hasil & Bukti
- **Label:** `USE CASE 5 · UKURPAKET · CARA HITUNG & HASIL`
- **Judul:** Dimensi dihitung dari satu foto: segmentasi, depth map, dan kotak 3D
- **Gambar:** `UC5_ukurpaket_2.png`
- **Poin:**
  - Hasil APK untuk sesi ini: **15,5 × 6,4 × 1,8 cm**, berat volumetrik 0,03 kg, status Akurat · skor 100.
  - Kotak 3D di foto dan di depth map digambar dari koordinat yang dihitung APK; kotak 3D cocok dengan outline objek
    (IoU 0,97).
  - Cara hitung (5 langkah di panel kanan gambar): foto + sensor gravitasi → segmentasi → depth map dan skala dari
    jarak autofocus → fitting kotak 3D → skala ke cm dan quality gate.
  - Quality gate: foto buram, objek terpotong, atau bentuk bukan kotak masuk "Perlu Dicek", tidak dipakai otomatis.
- **Catatan kaki:** Data: record hasil APK UkurPaket 0.4.6 dan depth map yang disimpan APK, sesi 20261110_131251
- **Speaker notes:** Kiri: foto dengan titik tap, hasil segmentasi, dan kotak 3D. Tengah: depth map dari model AI di
  HP; merah berarti dekat, biru berarti jauh. Skala diambil dari jarak autofocus lensa; depth AI hanya pembanding.
  Status Akurat adalah penilaian quality gate APK (ketajaman, kecocokan kotak dengan outline, sudut kamera), bukan
  perbandingan dengan meteran, karena ukuran meteran objek ini tidak tercatat di data sesi. Di pilot, hasil APK
  dibandingkan dengan meteran pada paket aktual.

---

### UC6 · Warehouse Live Ops

**Untuk:** 3PL dan distribusi, manufaktur, cold storage, e-commerce fulfilment.

#### Slide 12 · UC6 · A · Masalah & Solusi
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS · MASALAH & SOLUSI`
- **Judul:** Saat AI mendeteksi bahaya, kameranya langsung tampil di layar operator
- **Gambar:** `UC6_warehouse_1.png`
- **Masalah:**
  - Risiko tabrakan orang dan forklift baru ketahuan setelah terjadi; operator tidak mungkin memantau belasan layar
    sepanjang shift.
  - Mencari bukti satu insiden berarti playback rekaman berjam-jam.
- **Solusi:**
  - CCTV existing dan edge AI mendeteksi orang, forklift, APD, dan zona di setiap kamera.
  - Saat near miss, kamera terkait otomatis naik ke layar utama dengan bingkai merah; alert bisa dikonfirmasi atau
    ditandai false alarm.
- **Catatan kaki:** Cuplikan kamera: NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0) · layar mockup, angka ilustrasi
- **Speaker notes:** Satu operator bisa mengawasi banyak kamera karena AI yang memfilter kejadian. Begitu near miss
  terdeteksi, kameranya tampil sendiri di layar besar dan alert masuk ke daftar di kanan.

#### Slide 13 · UC6 · B · Hasil & Bukti
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS · HASIL & BUKTI`
- **Judul:** Setiap insiden punya bukti lengkap dan tindakan perbaikan
- **Gambar:** `UC6_warehouse_2.png`
- **Poin:**
  - Klip 10 detik sebelum–sesudah, snapshot, dan posisi kejadian di floor map.
  - Timeline dari deteksi sampai ditangani, CAPA dengan PIC dan due date, ekspor bukti PDF untuk audit SMK3/ISO 45001.
  - **PoC:** error posisi orang di floor map 0,19 m (median); 6 dari 6 line crossing benar; deteksi APD helm 24 dari
    26 dan rompi 22 dari 28 benar (blind test).
  - **Fokus pilot:** near miss saat orang terhalang forklift (di PoC baru 1 dari 13 terdeteksi).
- **Catatan kaki:** sama dengan slide 12 · hasil PoC dari rekaman gudang simulasi berlabel lengkap dan 1 gudang aktual
- **Speaker notes:** Investigasi selesai dalam hitungan menit karena klip, posisi, dan timeline sudah tersimpan per
  insiden. Sampaikan juga batas PoC: near miss saat orang terhalang forklift masih menjadi fokus pilot.

---

### UC7 · Plate Recognition & Vehicle Counting (CCTV parkir)

<<UC7_SECTION>>

---

### UC8 · Document OCR (tiket kereta hasil foto/scan)

**Untuk:** tim finance dan admin yang merekap tiket, kuitansi, atau dokumen hasil scan (reimbursement perjalanan
dinas, rekap biaya).

#### Slide 16 · UC8 · A · Masalah & Solusi
- **Label:** `USE CASE 8 · DOCUMENT OCR · MASALAH & SOLUSI`
- **Judul:** Foto tiket langsung menjadi data tabel, tanpa ketik ulang
- **Gambar:** `UC8_document_ocr_1.png`
- **Masalah:**
  - Tiket, kuitansi, dan dokumen hasil scan diketik ulang manual: lambat, rawan salah ketik, dan sulit diaudit.
  - Format dokumen beragam (dua bahasa, cetakan kecil, foto miring), sulit ditangani template OCR biasa.
- **Solusi:**
  - Vision-language model (Qwen2.5-VL-3B) membaca foto dan langsung mengisi field: tanggal, stasiun asal, stasiun
    tujuan, jam berangkat, jam tiba, harga.
  - Bounding box berwarna menghubungkan setiap field di tiket dengan kolom yang sama di tabel hasil.
- **Catatan kaki:** Hasil apa adanya dari repo github.com/sndypvtra/VL-Model-for-Taiwan-Railways-tickets-Extractor
  (`results/single0.jpeg`) · bounding box ditambahkan untuk presentasi (posisi dari text detector RapidOCR; model
  VLM hanya mengembalikan teks)
- **Speaker notes:** Ini output aplikasi apa adanya. Kotak berwarna hanya membantu membaca: biru tanggal, hijau
  stasiun, oranye jam, ungu harga, warna yang sama di tiket dan di tabel. Kolom Mileage tidak dibaca dari tiket,
  tetapi dihitung dari tabel jarak stasiun, jadi tidak termasuk penilaian.

#### Slide 17 · UC8 · B · Hasil & Bukti
- **Label:** `USE CASE 8 · DOCUMENT OCR · HASIL & BUKTI`
- **Judul:** Beberapa tiket dalam satu foto tetap terbaca satu per satu
- **Gambar:** `UC8_document_ocr_2.png`
- **Poin:**
  - 2 tiket dan 3 tiket dalam satu foto menjadi satu baris per tiket; nomor tiket di foto sama dengan nomor baris.
  - **Uji hasil repo (PoC):** 23 tiket dari 20 foto di folder `results/`, setiap field dicek manual dengan tiketnya:
    **134 dari 138 field benar (97,1%)**, 19 dari 23 tiket benar di semua field.
  - 4 field salah: 2 harga tidak terbaca (cetakan kecil, tertutup jari), 1 harga 870 terbaca 780, 1 tanggal tidak
    terbaca karena angka tahun terpotong di tepi foto.
  - Usulan pilot: field kosong atau tidak sesuai format masuk antrean cek manual sebelum data dipakai.
- **Catatan kaki:** Hasil apa adanya dari repo yang sama (`results/multiple0.jpeg`, `results/multiple1.jpeg`) ·
  bounding box ditambahkan untuk presentasi
- **Speaker notes:** Foto berisi beberapa tiket tetap dipecah per tiket. Dari 138 field yang dicek, 134 benar. Kesalahan
  terjadi pada harga yang tercetak kecil atau tertutup jari dan tanggal yang terpotong, jadi aturan cek manual untuk
  field kosong menutup sebagian besar risikonya.

---

### Slide 18 · Penutup

- **Label:** `RINGKASAN`
- **Judul:** Delapan use case, satu pola: kamera atau foto → AI → data dan tindakan
- **Isi:** tabel 8 baris, kolom **Use case · Masalah · Hasil · Bukti (PoC)**:

| Use case | Masalah | Hasil | Bukti (PoC) |
|---|---|---|---|
| Produce Grading | lot campur warna terkirim; cek manual hanya sampel | lot bermasalah ditahan sebelum dikirim, bukti per lot | 75/78 tomat sama dengan cek mata |
| Fill Level Inspection | underfill lolos; giveaway tidak terukur | underfill di-reject; giveaway terukur per nozzle | level isi terukur setiap frame (rekaman aktual) |
| Pack Count QC | kemasan kurang isi ketahuan setelah komplain | ditahan sebelum disegel, slot dan penyebab tercatat | tray 7/7, kardus 3/3 (simulasi 3D) |
| Parcel Dimensioning | ukuran paket tidak diketahui | P × L × T setiap paket; truk dan tagihan dari volume | 8/8 terhitung; 340,5 vs 340 mm |
| UkurPaket | ukur manual di pickup/counter | P × L × T dari satu foto di HP kurir | tampilan aktual APK, skor 100 pada sesi uji |
| Warehouse Live Ops | bahaya ketahuan setelah terjadi | alert real-time, bukti dan CAPA per insiden | error posisi 0,19 m; line crossing 6/6 |
| Plate & Vehicle | <<UC7_SUM_PROBLEM>> | <<UC7_SUM_RESULT>> | <<UC7_SUM_POC>> |
| Document OCR | tiket dan dokumen diketik ulang | field langsung jadi tabel | 134/138 field benar |

- **Baris bawah:** Langkah berikutnya: pilot 30 hari per use case, dengan blind test oleh tim klien. Besaran manfaat
  dihitung bersama klien dari data pilot.
- **Speaker notes:** Setiap use case bisa dimulai sendiri. Kami usulkan mulai dari masalah yang paling mendesak, satu
  lokasi atau satu line, dengan pilot 30 hari dan blind test oleh tim klien.

## 5. Checklist sebelum selesai

- [ ] 18 slide; setiap use case tepat 2 slide (A: masalah & solusi, B: hasil & bukti).
- [ ] 16 gambar dipakai dari `images/` dengan nama file persis seperti tabel bagian 2, utuh dan tidak diedit.
- [ ] Tidak ada kata "nyata"; dipakai "aktual".
- [ ] Setiap angka hasil uji diberi label PoC; angka ilustrasi tidak disebut sebagai hasil.
- [ ] Catatan kaki sumber ada di setiap slide use case.
- [ ] Tidak ada harga, rupiah, atau perhitungan pajak.
- [ ] Speaker notes terisi di semua slide.
