# Brief Claude Design: AI Vision untuk Operasional (8 use case)

Dokumen ini adalah instruksi lengkap untuk membuat satu deck presentasi dari 16 gambar di folder `images/`.
Unggah dokumen ini bersama ke-16 gambar ke Claude Design, lalu buat **18 slide** sesuai bagian 5 dan 6.

## 1. Tujuan dan audiens

- **Audiens:** manajemen bisnis (operasional, logistik, QC, finance) dan tim teknis (IT, engineering) dalam satu
  ruangan. Setiap slide harus bisa dipahami kedua kelompok tanpa penjelasan tambahan.
- **Tujuan:** untuk setiap use case, deck menjawab tiga pertanyaan secara berurutan:
  1. Masalah bisnis apa yang diselesaikan?
  2. Bagaimana solusinya bekerja?
  3. Bukti apa yang sudah ada, dan apa yang dibuktikan di pilot?
- **Struktur:** setiap use case tepat 2 slide. Slide A berisi masalah dan solusi, slide B berisi hasil dan bukti.
  Ditambah sampul dan penutup, totalnya 18 slide.
- **Nada:** profesional, faktual, dan ringkas. Klaim hanya sebatas yang ditunjukkan gambar dan angka di dokumen ini.

## 2. Aturan desain

- Rasio 16:9. Semua gambar berukuran 3840 × 2160 (4K). Pakai file aslinya tanpa kompresi.
- Gambar adalah isi utama slide. Tampilkan besar (sekitar 70% luas slide) dan utuh. Jangan meng-crop bagian yang
  memotong angka, label, atau catatan kaki di dalam gambar, dan jangan mengubah atau menambah angka di dalam gambar.
- Mockup UC1–UC4 dan UC6 adalah layar yang **sudah pernah dipresentasikan**. Gambarnya dipakai tanpa perubahan.
  UC6 dirender ulang 2× dari file HTML yang sama supaya tajam di 4K; isinya identik.
- Setiap slide use case berisi:
  - label kecil di atas, misalnya `USE CASE 3 · PACK COUNT QC · MASALAH & SOLUSI`;
  - judul satu kalimat;
  - gambar;
  - 3–4 poin pendek;
  - catatan kaki sumber.
- Tipografi, grid, dan posisi elemen sama di ke-16 slide use case. Warna aksen boleh berbeda per use case.
- Speaker notes diisi persis dari bagian 6. Kalimatnya boleh dipersingkat, tetapi isi dan angkanya tetap.

## 3. Aturan bahasa

- Bahasa Indonesia baku yang lazim di dunia kerja. Istilah teknis memakai istilah yang umum dipakai di industri,
  termasuk istilah Inggris yang sudah lazim.
- Judul menyebut hasil untuk bisnis, bukan nama fitur. Satu gagasan per poin.
- Hindari kata promosi seperti revolusioner, canggih, mutakhir, seamless, dan game changer.
- Angka hanya dari gambar atau dari dokumen ini. Angka hasil uji selalu diberi label **PoC**.
- Angka di layar mockup UC1–UC4 dan UC6 adalah ilustrasi, kecuali yang bertanda PoC (sudah tertulis di gambar).
  Jangan sebut angka ilustrasi sebagai hasil.
- Tidak ada harga atau angka rupiah di deck ini.

**Istilah yang dipakai dan yang dihindari**

| Pakai | Jangan pakai |
|---|---|
| aktual (rekaman aktual, ukuran aktual, tampilan aktual) | nyata |
| garis kotak yang tertutup dari kamera | rusuk, sisi tersembunyi |
| hasil ekstraksi model | hasil apa adanya, mentah |
| PoC (hasil uji yang sudah ada), pilot (uji berikutnya bersama klien) | uji coba, trial |
| berat volumetrik (P × L × T ÷ 6000) | berat dimensi |
| status Akurat / Perlu Dicek (sesuai layar APK) | lulus / gagal |

**Istilah teknis yang boleh dipakai di slide tanpa diterjemahkan.** Artinya dicantumkan untuk speaker notes:

| Istilah | Arti singkat |
|---|---|
| edge AI | AI yang berjalan di perangkat di lokasi, bukan di cloud |
| live monitoring, dashboard, real-time | tampilan langsung saat kejadian berlangsung |
| bounding box | kotak penanda posisi objek di gambar |
| segmentasi | memisahkan objek dari latar belakang |
| depth map | peta jarak setiap titik gambar dari kamera |
| ID tracking | nomor unik per objek supaya dihitung sekali |
| OCR | membaca teks dari gambar |
| vision-language model (VLM) | model AI yang membaca gambar lalu menjawab dalam teks |
| IoU | ukuran kecocokan dua bentuk, 0 sampai 1 (1 = sama persis) |
| quality gate | pemeriksaan otomatis sebelum hasil dipakai |
| ground truth, blind test | data acuan yang benar; uji tanpa tahu jawaban sistem |
| reject, underfill, overfill, giveaway | istilah QC di line produksi |
| near miss, CAPA | hampir celaka; tindakan perbaikan dan pencegahan |
| PLC, WMS, TMS | sistem kontrol mesin, sistem gudang, sistem transportasi |

## 4. Gambar yang dipakai (16 file)

| Use case | File | Isi gambar | Sumber |
|---|---|---|---|
| UC1 Produce Grading | `UC1_produce_grading_1.png` | Dashboard TV di line: kelas warna setiap tomat, off-colour lot dibanding limit | mockup yang sudah dipresentasikan (`PG_03_dashboard_tv_tomat`) |
| | `UC1_produce_grading_2.png` | Laporan Lot: keputusan lot, foto bukti, riwayat, ekspor sertifikat | mockup yang sudah dipresentasikan (`PG_05_laporan_lot`) |
| UC2 Fill Level Inspection | `UC2_fill_level_1.png` | Live Monitoring: level isi setiap botol, status per nozzle | mockup yang sudah dipresentasikan (`FL_02_live_monitoring`) |
| | `UC2_fill_level_2.png` | Reject & Giveaway: reject per nozzle, giveaway per nozzle, bukti reject | mockup yang sudah dipresentasikan (`FL_04_reject_giveaway`) |
| UC3 Pack Count QC | `UC3_pack_count_1.png` | Dashboard TV: setiap tray dihitung, slot kosong ditandai SHORT | mockup yang sudah dipresentasikan (`PC_03_dashboard_tv_tray`) |
| | `UC3_pack_count_2.png` | Detail Reject: peta slot, klip bukti, timeline sampai rework | mockup yang sudah dipresentasikan (`PC_05_detail_reject`) |
| UC4 Parcel Dimensioning (conveyor) | `UC4_parcel_conveyor_1.png` | Dashboard TV: P × L × T setiap paket di belt | mockup yang sudah dipresentasikan (`PD_03_dashboard_tv`) |
| | `UC4_parcel_conveyor_2.png` | Muat & Tagihan: isi truk dari volume, berat volumetrik per pelanggan | mockup yang sudah dipresentasikan (`PD_04_muat_tagihan`) |
| UC5 UkurPaket (APK Android) | `UC5_ukurpaket_1.png` | 4 layar aktual APK UkurPaket 0.4.6, mode foto tanpa AR: ambil foto, marking, hasil benda kotak (HP), hasil benda bulat (gelas) | baru, dari data foto uji di HP Urovo DT50 |
| | `UC5_ukurpaket_2.png` | Dua objek: foto dengan segmentasi dan kotak 3D di samping depth map, kartu hasil, dan 5 langkah cara hitung | baru, dari data yang sama |
| UC6 Warehouse Live Ops | `UC6_warehouse_1.png` | Live Monitoring: kamera otomatis tampil saat near miss, daftar alert, mini map | mockup yang sudah dipresentasikan (`03_live_monitoring`) |
| | `UC6_warehouse_2.png` | Detail Insiden & Bukti: klip 10 detik, timeline, CAPA, ekspor PDF | mockup yang sudah dipresentasikan (`06_detail_insiden`) |
| UC7 Plate & Vehicle (CCTV parkir) | `UC7_plate_vehicle_1.png` | Satu frame video hasil: CAM 1 gerbang (motor, mobil, truk dihitung) dan CAM 2 area parkir (plat terbaca), dengan panel hitungan dan daftar plat | baru, dari video hasil `plate_vehicle_cctv.mp4` |
| | `UC7_plate_vehicle_2.png` | Bukti: zoom kedua kamera, tabel hitungan per jenis, foto plat dan jumlah bacaan yang sama, cara kerja 5 langkah | baru, dari video hasil yang sama |
| UC8 Document OCR | `UC8_document_ocr_1.png` | Hasil ekstraksi 1 tiket menjadi 1 baris tabel, dengan bounding box per field | baru, dari `results/single0.jpeg` |
| | `UC8_document_ocr_2.png` | Hasil ekstraksi 2 tiket dan 3 tiket dalam satu foto, 1 baris tabel per tiket | baru, dari `results/multiple0.jpeg` dan `results/multiple1.jpeg` |

Video pendukung UC7 (tidak masuk deck; diputar terpisah atau ditautkan di slide 14):
`plate_vehicle_cctv.mp4`, 1920 × 1080, 39,9 detik.

## 5. Susunan deck (18 slide)

| # | Slide | Gambar | Judul |
|---|---|---|---|
| 1 | Sampul | 8 gambar `_1` sebagai thumbnail | AI Vision untuk operasional: 8 use case dari kamera dan foto |
| 2 | UC1 · A | `UC1_produce_grading_1.png` | Setiap buah di-grade di line; lot campur warna ketahuan sebelum dikirim |
| 3 | UC1 · B | `UC1_produce_grading_2.png` | Klaim pembeli dijawab dengan data per lot, bukan perkiraan |
| 4 | UC2 · A | `UC2_fill_level_1.png` | Level isi setiap botol terlihat langsung, nozzle demi nozzle |
| 5 | UC2 · B | `UC2_fill_level_2.png` | Setiap reject punya bukti, setiap mL lebih terhitung per nozzle |
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

- **Judul:** AI Vision untuk operasional: 8 use case dari kamera dan foto
- **Subjudul:** Pabrik, gudang, logistik, parkir, dan dokumen. Setiap use case: masalah bisnis, solusi, dan bukti.
- **Visual:** grid 4 × 2 berisi delapan gambar `_1`, masing-masing dengan nama use case di bawahnya.
- **Baris bawah:** `[isi nama tim] · [isi tanggal]`
- **Speaker notes:** Deck ini merangkum delapan use case AI vision. Setiap use case dibahas dalam dua slide:
  masalah bisnis dan solusinya, lalu hasil dan bukti yang sudah ada. Semua angka hasil uji ditandai PoC.

---

### UC1 · Produce Grading

**Untuk:** packing house buah dan sayur, eksportir, dan pemasok supermarket.

#### Slide 2 · UC1 · A · Masalah & Solusi
- **Label:** `USE CASE 1 · PRODUCE GRADING · MASALAH & SOLUSI`
- **Judul:** Setiap buah di-grade di line; lot campur warna ketahuan sebelum dikirim
- **Gambar:** `UC1_produce_grading_1.png`
- **Masalah:**
  - Warna dan kematangan dicek manual dengan sampel kecil, sehingga lot campur warna lolos ke pembeli.
  - Standar berbeda per pembeli (USDA, OECD, spec supermarket) dan sulit diterapkan konsisten di setiap shift.
- **Solusi:**
  - Kamera di atas conveyor dan edge AI membaca kelas warna setiap buah, lalu menghitungnya sekali di count gate.
  - Off-colour lot dibandingkan dengan limit secara real-time. Contoh di layar: 17% terhadap limit 10%, sehingga
    lot diberi label Mixed Color atau 7 buah disortir ulang.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC
- **Speaker notes:** Ini Dashboard TV di line. Setiap tomat diberi kotak sesuai kelas warna USDA dan dihitung
  sekali. Banner kuning menunjukkan off-colour lot 17%, di atas limit 10%, sehingga lot diberi label Mixed Color atau
  7 buah disortir ulang. Keputusan ini diambil saat buah masih di line, bukan setelah lot ditolak pembeli.

#### Slide 3 · UC1 · B · Hasil & Bukti
- **Label:** `USE CASE 1 · PRODUCE GRADING · HASIL & BUKTI`
- **Judul:** Klaim pembeli dijawab dengan data per lot, bukan perkiraan
- **Gambar:** `UC1_produce_grading_2.png`
- **Poin:**
  - Setiap lot punya keputusan sesuai standar warna USDA, lengkap dengan foto bukti dan sebaran warna setiap buah.
  - Riwayat lot (alert, hold, sortir ulang, dan siapa yang menangani) serta sertifikat lot dalam PDF untuk QA pembeli.
  - **PoC:** 75 dari 78 tomat sama dengan cek mata dalam blind test, sisanya hanya beda 1 kelas. Lemon: 18 dari 24
    berada dalam ±1 derajat bagan warna OECD.
- **Catatan kaki:** sama dengan slide 2
- **Speaker notes:** Laporan Lot menyimpan keputusan, bukti, dan riwayat setiap lot. Saat ada klaim warna dari
  pembeli, tim sales menjawab dengan data lot tersebut. Pada PoC, 75 dari 78 tomat sama dengan cek mata dalam blind
  test. Di pilot, kecocokan ini diuji ulang oleh QC pabrik.

---

### UC2 · Fill Level Inspection

**Untuk:** pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol.

#### Slide 4 · UC2 · A · Masalah & Solusi
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION · MASALAH & SOLUSI`
- **Judul:** Level isi setiap botol terlihat langsung, nozzle demi nozzle
- **Gambar:** `UC2_fill_level_1.png`
- **Masalah:**
  - Botol underfill lolos ke pasar dan berisiko memicu komplain serta pelanggaran ketentuan BDKT.
  - Overfill tidak terukur, padahal itu produk yang terbuang (giveaway) setiap hari. Cek manual hanya sampel per jam.
- **Solusi:**
  - Kamera samping dengan backlight di mesin pengisi; edge AI mengukur level isi di setiap frame.
  - Tinggi cairan diubah menjadi volume berdasarkan profil botol. Botol underfill di-reject lewat sinyal ke PLC.
- **Catatan kaki:** Video: Pexels 8720278 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC
- **Speaker notes:** Di kamera terlihat outline botol, garis target di leher botol, serta level isi dalam persen dan
  mL. Di sebelah kanan ada status nozzle 1 sampai 8. Nozzle yang underfill ditandai merah dan bisa langsung dihentikan
  untuk dicek, tanpa menunggu sampel per jam.

#### Slide 5 · UC2 · B · Hasil & Bukti
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION · HASIL & BUKTI`
- **Judul:** Setiap reject punya bukti, setiap mL lebih terhitung per nozzle
- **Gambar:** `UC2_fill_level_2.png`
- **Poin:**
  - Setiap reject underfill tercatat per nozzle, lalu dikonfirmasi QC atau ditandai alarm palsu.
  - Giveaway per nozzle dibandingkan dengan target dan toleransi, disertai saran tindakan untuk tim teknik.
  - Bukti reject berisi gambar kamera, level isi saat nozzle berhenti, dan sinyal ke PLC.
  - **PoC:** level isi terukur di setiap frame pada rekaman aktual mesin pengisi. Klip berakhir di 67% saat botol
    masih diisi, sehingga belum ada keputusan pass/reject. Angka mL memakai contoh SKU 500 mL.
- **Catatan kaki:** sama dengan slide 4
- **Speaker notes:** Halaman ini dipakai QC dan Maintenance. Setiap reject punya bukti, dan giveaway per nozzle
  menunjukkan nozzle mana yang perlu disetel. Sampaikan batas PoC dengan terbuka: klip berakhir di 67%. Di pilot,
  level isi per nozzle dibandingkan dengan check weigher.

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
  - Kamera di atas ujung line atau packing station; edge AI menghitung isi setiap tray dan kardus per slot.
  - Slot kosong dilingkari merah, dan tray ditandai SHORT lalu dialihkan sebelum disegel.
- **Catatan kaki:** Video: simulasi 3D buatan tim dengan ground truth · layar mockup, angka ilustrasi kecuali yang
  bertanda PoC
- **Speaker notes:** Ini Dashboard TV di ujung line kaleng. Tray yang kurang isi ditandai SHORT dan slot kosongnya
  dilingkari. Kalau slot yang sama berulang kali kosong, itu menunjuk ke lane filler tertentu. Yang diperbaiki adalah
  penyebabnya, bukan hanya kemasannya.

#### Slide 7 · UC3 · B · Hasil & Bukti
- **Label:** `USE CASE 3 · PACK COUNT QC · HASIL & BUKTI`
- **Judul:** Setiap reject punya bukti, penyebab, dan tindakan perbaikan
- **Gambar:** `UC3_pack_count_2.png`
- **Poin:**
  - Peta slot kardus menunjukkan B2 dan C5 kosong (18/20) dengan penyebab feeder gap.
  - Foto bukti dan klip 10 detik sebelum dan sesudah kejadian, bisa diekspor ke PDF.
  - Timeline lengkap: feeder gap, empty pick, kardus di-hold, notifikasi WhatsApp, rework menjadi 20/20, dan
    corrective action.
  - **PoC (simulasi 3D dengan ground truth):** tray 7 dari 7 benar (181 dari 181 pembacaan), kardus 3 dari 3 benar,
    dan 2 dari 2 empty pick ditemukan.
- **Catatan kaki:** sama dengan slide 6
- **Speaker notes:** Ini detail satu reject. Investigasi selesai dalam hitungan menit: slot mana yang kosong, apa
  penyebabnya, siapa yang menangani, dan bukti yang siap untuk pelanggan atau audit.

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
  - Kamera di atas belt bongkar muat; edge AI mengukur P × L × T dan menghitung setiap paket di count line.
  - Paket yang ukurannya dekat batas kelas masuk manual check, bukan ditebak.
- **Catatan kaki:** Video: Pexels 5370836 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC
- **Speaker notes:** Ini Dashboard TV di belt bongkar truk. Setiap paket diberi kotak sesuai kelas ukurannya, lalu
  masuk tabel lengkap dengan P × L × T, volume, dan berat volumetrik. Paket yang meragukan dikonfirmasi oleh petugas.

#### Slide 9 · UC4 · B · Hasil & Bukti
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING · HASIL & BUKTI`
- **Judul:** Volume terukur dipakai untuk muat truk dan tagihan
- **Gambar:** `UC4_parcel_conveyor_2.png`
- **Poin:**
  - Isi setiap truk dihitung dari volume terukur, dengan status selesai muat, sedang muat, atau terjadwal.
  - Berat volumetrik (P × L × T ÷ 6000) dibandingkan dengan berat aktual per pelanggan. Paket ringan tetapi besar
    ditagih berdasarkan volume.
  - Data langsung dikirim ke TMS/WMS tanpa input ulang.
  - **PoC (rekaman aktual):** 8 dari 8 paket terhitung, sama dengan hitungan manual. Karton uji terbaca 340,5 mm;
    ukuran aktualnya 340 mm.
- **Catatan kaki:** Layar mockup, angka ilustrasi kecuali yang bertanda PoC · laju per jam di layar adalah perkiraan
  dari klip 17 detik
- **Speaker notes:** Data ukuran langsung dipakai dua tim: logistik untuk rencana muat truk, dan finance untuk dasar
  tagihan. Di pilot, hasil P × L × T dibandingkan dengan meteran pada 100 paket dengan target selisih ±1 cm.

---

### UC5 · UkurPaket (APK Android, mode foto)

**Untuk:** kurir pickup, counter ekspedisi, dan agen. Perangkat: HP Android atau handheld kurir; diuji di Urovo DT50.

#### Slide 10 · UC5 · A · Masalah & Solusi
- **Label:** `USE CASE 5 · UKURPAKET · MASALAH & SOLUSI`
- **Judul:** Kurir mengukur paket dengan satu foto dari HP, tanpa meteran
- **Gambar:** `UC5_ukurpaket_1.png`
- **Masalah:**
  - Saat pickup dan di counter, ukuran paket diukur dengan meteran atau hanya ditebak, sehingga berat volumetrik
    dan berat tagih sering tidak sesuai.
  - Handheld kurir umumnya tidak punya ARCore atau sensor depth, sehingga aplikasi ukur berbasis AR tidak bisa dipakai.
- **Solusi (4 layar di gambar):**
  - **Ambil foto:** APK memandu sudut 30–60° dan memastikan HP diam sebelum memotret.
  - **Marking objek:** kurir tap objek atau tarik kotak, lalu AI memisahkan objek dari latar belakang.
  - **Hasil:** P × L × T, berat volumetrik, dan status kualitas langsung tampil di HP. Benda kotak (HP) berstatus
    Akurat; benda bulat (gelas) dibaca diameter × diameter × tinggi dan berstatus Perlu Dicek.
- **Catatan kaki:** Tampilan aktual APK UkurPaket 0.4.6 (mode foto, tanpa AR) · foto dari HP Urovo DT50, sesi
  20261110_131251 (HP) dan 20261110_144509 (gelas)
- **Speaker notes:** Empat layar ini adalah tampilan aktual APK, diisi foto dari HP uji. Kurir cukup memotret,
  menandai objek, dan hasilnya langsung keluar di layar yang sama, tanpa ARCore atau sensor tambahan. Layar ketiga
  menunjukkan benda kotak dengan status Akurat. Layar keempat menunjukkan benda bulat: APK tetap memberi ukuran,
  tetapi menandainya Perlu Dicek karena bentuknya bukan kotak. Berat volumetrik bukan berat aktual. Berat aktual
  tetap dari timbangan, dan berat tagih adalah yang lebih besar dari keduanya.

#### Slide 11 · UC5 · B · Hasil & Bukti
- **Label:** `USE CASE 5 · UKURPAKET · CARA HITUNG & HASIL`
- **Judul:** Dimensi dihitung dari satu foto, untuk benda kotak maupun bulat
- **Gambar:** `UC5_ukurpaket_2.png`
- **Poin:**
  - **HP dengan clear case:** 15,5 × 6,4 × 1,8 cm, berat volumetrik 0,03 kg, status Akurat · skor 100. Kotak 3D
    pas dengan outline objek (IoU 0,97).
  - **Gelas dengan sedotan:** 7,1 × 7,1 × 23,7 cm (diameter × diameter × tinggi, tinggi termasuk sedotan), berat
    volumetrik 0,20 kg, status Perlu Dicek · skor 75 karena bentuknya bukan kotak.
  - Skala pada foto gelas dicek dengan benda lain di foto yang sama: kaki gelas 8,1 cm, piring 30 cm, dan garpu
    21 cm. Semuanya ukuran yang wajar.
  - Cara hitung 5 langkah: foto dan sensor gravitasi, segmentasi, depth map dan skala dari autofocus, fitting kotak
    3D, lalu ukuran dalam cm dengan quality gate.
- **Catatan kaki:** Data: record hasil APK UkurPaket 0.4.6 dan depth map yang disimpan APK · kotak 3D digambar
  dari koordinat yang dihitung APK; angka tidak diubah
- **Speaker notes:** Di setiap baris, kiri adalah foto dengan hasil segmentasi dan kotak 3D. Tengah adalah depth map
  dari model AI di HP; merah berarti dekat, biru berarti jauh. Garis putus-putus adalah garis kotak yang tertutup dari
  kamera. Skala diambil dari jarak fokus lensa, sedangkan depth dari AI hanya pembanding. Status Perlu Dicek tetap
  bisa dipakai kurir, tetapi ukurannya tersimpan dengan status tersebut beserta foto bukti untuk dicek ulang. Ukuran
  meteran kedua objek tidak tercatat di data uji. Karena itu, di pilot hasil APK dibandingkan dengan meteran pada
  paket aktual.

---

### UC6 · Warehouse Live Ops

**Untuk:** 3PL dan distribusi, manufaktur, cold storage, dan e-commerce fulfilment.

#### Slide 12 · UC6 · A · Masalah & Solusi
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS · MASALAH & SOLUSI`
- **Judul:** Saat AI mendeteksi bahaya, kameranya langsung tampil di layar operator
- **Gambar:** `UC6_warehouse_1.png`
- **Masalah:**
  - Risiko tabrakan orang dan forklift baru ketahuan setelah terjadi. Operator tidak mungkin memantau belasan layar
    sepanjang shift.
  - Mencari bukti satu insiden berarti memutar ulang rekaman berjam-jam.
- **Solusi:**
  - CCTV yang sudah ada dan edge AI mendeteksi orang, forklift, APD, dan zona di setiap kamera.
  - Saat near miss terjadi, kamera terkait otomatis tampil di layar utama dengan bingkai merah. Setiap alert bisa
    dikonfirmasi atau ditandai false alarm.
- **Catatan kaki:** Cuplikan kamera: NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0) · layar mockup, angka ilustrasi
- **Speaker notes:** Satu operator bisa mengawasi banyak kamera karena AI yang menyaring kejadian. Begitu near miss
  terdeteksi, kameranya tampil sendiri di layar besar dan alert masuk ke daftar di kanan.

#### Slide 13 · UC6 · B · Hasil & Bukti
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS · HASIL & BUKTI`
- **Judul:** Setiap insiden punya bukti lengkap dan tindakan perbaikan
- **Gambar:** `UC6_warehouse_2.png`
- **Poin:**
  - Klip 10 detik sebelum dan sesudah kejadian, snapshot, dan posisi kejadian di floor map.
  - Timeline dari deteksi sampai ditangani, CAPA dengan PIC dan tenggat, serta ekspor bukti PDF untuk audit SMK3 dan
    ISO 45001.
  - **PoC:** error posisi orang di floor map 0,19 m (median); 6 dari 6 line crossing benar; deteksi APD dalam blind
    test benar 24 dari 26 untuk helm dan 22 dari 28 untuk rompi.
  - **Fokus pilot:** near miss saat orang terhalang forklift (di PoC baru 1 dari 13 yang terdeteksi).
- **Catatan kaki:** sama dengan slide 12 · hasil PoC dari rekaman gudang simulasi berlabel lengkap dan 1 gudang aktual
- **Speaker notes:** Investigasi selesai dalam hitungan menit karena klip, posisi, dan timeline sudah tersimpan per
  insiden. Sampaikan juga batas PoC: near miss saat orang terhalang forklift masih menjadi fokus pilot.

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
  - Tidak ada data jumlah motor, mobil, dan truk per jam. Mencari kapan kendaraan tertentu datang berarti memutar
    ulang rekaman CCTV.
- **Solusi:**
  - CCTV yang sudah ada dan edge AI mendeteksi serta melacak setiap kendaraan. Motor, mobil, dan truk/bus dihitung
    sekali per ID tracking.
  - Plat nomor dibaca dari kamera yang cukup dekat (deteksi plat dan OCR), lalu dicatat bersama foto plat, jenis
    kendaraan, kamera, dan waktu.
- **Catatan kaki:** Video: 2 kamera CCTV aktual (NVR) dari dataset publik Hugging Face `rithwikn/ai_cctv_videos`,
  digabung dalam satu video · plat nomor Tanzania
- **Speaker notes:** Video ini menggabungkan dua kamera CCTV aktual. CAM 1 di gerbang menghitung kendaraan, dan CAM 2
  di area parkir membaca plat. Setiap kendaraan diberi ID tracking sehingga dihitung sekali. Kendaraan yang bergerak
  diberi label "bergerak", sedangkan yang parkir tetap masuk hitungan "di area". Plat baru tampil setelah beberapa
  bacaan konsisten, bukan dari satu frame saja.

#### Slide 15 · UC7 · B · Hasil & Bukti
- **Label:** `USE CASE 7 · PLATE & VEHICLE · HASIL & BUKTI`
- **Judul:** Setiap kendaraan dihitung sekali, setiap plat tercatat dengan foto
- **Gambar:** `UC7_plate_vehicle_2.png`
- **Poin:**
  - **PoC CAM 1 (gerbang, 2 potongan rekaman):** 3 motor dan 1 truk bergerak, masing-masing terhitung sekali. 5 mobil
    terdeteksi parkir di area, dan tidak ada mobil yang bergerak. Hasil ini sudah dicek manual terhadap video.
  - **PoC CAM 2 (area parkir):** 2 plat terbaca. **T 649 EHP** terbaca sama di 970 dari 998 frame (97%), dan
    **T 119 ELM** di 874 dari 998 frame (88%). Keduanya sudah dicek manual dan sesuai dengan plat di video.
  - Kondisi lapangan yang ditangani: pejalan kaki pembawa barang yang sempat terbaca sebagai motor dibuang, kabin
    truk yang masuk lebih dulu digabung ke truknya, dan bagian rekaman NVR yang beku dilewati tanpa menghitung truk
    dua kali.
  - Batas PoC: plat di CAM 1 tidak terbaca karena terlalu jauh dari kamera. Di pilot, kamera baca plat dipasang dekat
    jalur masuk, dan hitungan per jam dibandingkan dengan hitungan manual.
- **Catatan kaki:** sama dengan slide 14 · CAM 1 berasal dari 2 potongan rekaman gerbang yang sama; bagian rekaman
  yang beku (gangguan NVR) dilewati
- **Speaker notes:** Di gerbang, tiga motor dan satu truk yang lewat terhitung masing-masing sekali. Semua mobil di
  area ini parkir, jadi hitungan mobil bergerak nol. Di area parkir, dua plat terbaca konsisten di hampir semua frame
  dan sudah dicek manual. Sampaikan juga batasnya: plat di gerbang tidak terbaca karena kamera terlalu jauh, sehingga
  di pilot kamera baca plat dipasang dekat jalur masuk.

---

### UC8 · Document OCR (tiket kereta dari foto atau hasil scan)

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
  - Vision-language model (Qwen2.5-VL-3B) membaca foto dan langsung mengisi field: tanggal, stasiun asal, stasiun
    tujuan, jam berangkat, jam tiba, dan harga.
  - Bounding box berwarna menghubungkan setiap field di tiket dengan kolom yang sama di tabel hasil.
- **Catatan kaki:** Hasil ekstraksi dari repo GitHub `sndypvtra/VL-Model-for-Taiwan-Railways-tickets-Extractor`
  (`results/single0.jpeg`) · bounding box ditambahkan untuk presentasi; posisinya dari text detector RapidOCR karena
  model hanya mengembalikan teks
- **Speaker notes:** Ini hasil ekstraksi model pada satu foto tiket. Kotak berwarna membantu membaca hasilnya: biru
  untuk tanggal, hijau untuk stasiun, oranye untuk jam, dan ungu untuk harga, dengan warna yang sama di tiket dan di
  tabel. Kolom Mileage tidak dibaca dari tiket, tetapi dihitung dari tabel jarak stasiun, sehingga tidak termasuk
  penilaian.

#### Slide 17 · UC8 · B · Hasil & Bukti
- **Label:** `USE CASE 8 · DOCUMENT OCR · HASIL & BUKTI`
- **Judul:** Beberapa tiket dalam satu foto tetap terbaca satu per satu
- **Gambar:** `UC8_document_ocr_2.png`
- **Poin:**
  - Foto berisi 2 tiket dan 3 tiket menjadi satu baris per tiket. Nomor tiket di foto sama dengan nomor baris di tabel.
  - **PoC:** 23 tiket dari 20 foto di folder `results` repo, dan setiap field dicek manual dengan tiketnya.
    Hasilnya **134 dari 138 field benar (97,1%)**, dan 19 dari 23 tiket benar di semua field.
  - Empat field yang salah: 2 harga tidak terbaca (cetakan kecil dan tertutup jari), 1 harga 870 terbaca 780, dan 1
    tanggal tidak terbaca karena angka tahunnya terpotong di tepi foto.
  - Usulan untuk pilot: field yang kosong atau tidak sesuai format masuk antrean cek manual sebelum data dipakai.
- **Catatan kaki:** Hasil ekstraksi dari repo yang sama (`results/multiple0.jpeg` dan `results/multiple1.jpeg`) ·
  bounding box ditambahkan untuk presentasi
- **Speaker notes:** Foto yang berisi beberapa tiket tetap dipecah per tiket. Dari 138 field yang dicek, 134 benar.
  Kesalahan terjadi pada harga yang tercetak kecil atau tertutup jari dan pada tanggal yang terpotong. Aturan cek
  manual untuk field kosong menutup sebagian besar risiko tersebut.

---

### Slide 18 · Penutup

- **Label:** `RINGKASAN`
- **Judul:** Delapan use case, satu pola: kamera atau foto, AI, lalu data dan tindakan
- **Isi:** tabel 8 baris dengan kolom **Use case · Masalah · Hasil · Bukti (PoC)**:

| Use case | Masalah | Hasil | Bukti (PoC) |
|---|---|---|---|
| Produce Grading | lot campur warna terkirim; cek manual hanya sampel | lot bermasalah ditahan sebelum dikirim, dengan bukti per lot | 75 dari 78 tomat sama dengan cek mata |
| Fill Level Inspection | underfill lolos; giveaway tidak terukur | underfill di-reject; giveaway terukur per nozzle | level isi terukur di setiap frame (rekaman aktual) |
| Pack Count QC | kemasan kurang isi baru ketahuan setelah komplain | ditahan sebelum disegel; slot dan penyebab tercatat | tray 7/7, kardus 3/3 (simulasi 3D) |
| Parcel Dimensioning | ukuran paket tidak diketahui | P × L × T setiap paket; muat truk dan tagihan dari volume | 8/8 paket terhitung; 340,5 vs 340 mm |
| UkurPaket | ukur manual saat pickup dan di counter | P × L × T dari satu foto di HP kurir, untuk benda kotak dan bulat | HP: Akurat, skor 100; gelas: skala sesuai benda acuan |
| Warehouse Live Ops | bahaya baru ketahuan setelah terjadi | alert real-time, bukti, dan CAPA per insiden | error posisi 0,19 m; line crossing 6/6 |
| Plate & Vehicle | kendaraan dan plat dicatat manual | kendaraan dihitung per jenis; plat tercatat dengan foto | 3 motor + 1 truk terhitung benar; 2/2 plat benar |
| Document OCR | tiket dan dokumen diketik ulang | field langsung menjadi tabel | 134 dari 138 field benar |

- **Baris bawah:** Langkah berikutnya: pilot 30 hari per use case dengan blind test oleh tim klien. Besaran manfaat
  dihitung bersama klien dari data pilot.
- **Speaker notes:** Setiap use case bisa dimulai sendiri. Kami mengusulkan mulai dari masalah yang paling mendesak,
  di satu lokasi atau satu line, dengan pilot 30 hari dan blind test oleh tim klien.

## 7. Checklist sebelum selesai

- [ ] Total 18 slide, dan setiap use case tepat 2 slide (A: masalah & solusi, B: hasil & bukti).
- [ ] Ke-16 gambar dari `images/` dipakai dengan nama file persis seperti di bagian 4, utuh dan tidak diedit.
- [ ] Tidak ada kata "nyata", "rusuk", atau "apa adanya". Istilah mengikuti tabel di bagian 3.
- [ ] Setiap angka hasil uji diberi label PoC, dan angka ilustrasi tidak disebut sebagai hasil.
- [ ] Setiap slide use case punya catatan kaki sumber.
- [ ] Tidak ada harga atau angka rupiah.
- [ ] Speaker notes terisi di semua slide.
