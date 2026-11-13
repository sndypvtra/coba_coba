# Brief Claude Design: AI Vision untuk Operasional (Masalah & Solusi)

Dokumen ini adalah instruksi lengkap untuk membuat satu deck dari 16 gambar di folder `images/`.
Unggah dokumen ini bersama ke-16 gambar ke Claude Design, lalu buat **17 slide** sesuai bagian 5 dan 6.

## 1. Tujuan dan audiens

- **Audiens:** manajemen bisnis (operasional, logistik, QC, finance) dan tim teknis (IT, engineering) dalam satu
  ruangan. Setiap slide harus bisa dipahami kedua kelompok tanpa penjelasan tambahan.
- **Isi deck:** hanya **masalah bisnis dan solusinya**. Setiap use case punya tepat 2 slide, dan setiap slide berisi
  satu masalah beserta solusinya, dengan gambar layar yang menyelesaikan masalah tersebut.
- **Yang tidak dimasukkan:** slide bukti atau hasil uji (PoC), model bisnis, harga, pilot, timeline, langkah berikutnya,
  dan permintaan keputusan.
- **Nada:** profesional, faktual, dan ringkas. Klaim hanya sebatas yang terlihat di gambar dan tertulis di dokumen ini.

## 2. Aturan desain

- Rasio 16:9. Semua gambar berukuran 3840 × 2160 (4K). Pakai file aslinya tanpa kompresi.
- Layout sama untuk ke-16 slide use case:
  - label kecil di kiri atas, misalnya `USE CASE 3 · PACK COUNT QC`;
  - judul satu kalimat di bawah label;
  - kolom kiri (sekitar 30% lebar slide) berisi blok **Masalah** lalu blok **Solusi**;
  - kolom kanan (sekitar 70% lebar slide) berisi gambar, tampil utuh;
  - catatan kaki sumber di bawah.
- Blok Masalah dan Solusi dibedakan dengan judul blok yang jelas. Pakai satu warna netral untuk Masalah dan satu
  warna aksen untuk Solusi.
- Gambar ditampilkan utuh. Jangan meng-crop bagian yang memotong label atau catatan kaki di dalam gambar, dan jangan
  menambah atau mengubah apa pun di dalam gambar.
- Mockup UC1–UC4 dan UC6 adalah layar yang **sudah pernah dipresentasikan**. Gambarnya dipakai tanpa perubahan.
- Speaker notes diisi dari bagian 6. Kalimatnya boleh dipersingkat, tetapi isinya tetap.

## 3. Aturan bahasa

- Bahasa Indonesia baku yang lazim di dunia kerja. Istilah teknis memakai istilah yang umum dipakai di engineering
  dan bisnis, termasuk istilah Inggris yang sudah lazim.
- Judul menyebut hasil untuk bisnis, bukan nama fitur. Satu gagasan per poin.
- Hindari kata promosi seperti revolusioner, canggih, mutakhir, seamless, dan game changer.
- **Tanpa angka di teks slide dan speaker notes.** Jangan tulis jumlah, persentase, ukuran, waktu, atau perkiraan.
  - Gambar boleh berisi angka (tampilan layar), tetapi angka itu tidak dikutip di teks.
  - Angka di mockup UC1–UC4 dan UC6 adalah ilustrasi.
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

Video pendukung UC7 (`plate_vehicle_cctv.mp4`) tidak masuk deck. Putar terpisah atau tautkan di slide 14.

## 5. Susunan deck (17 slide)

| # | Slide | Gambar | Judul |
|---|---|---|---|
| 1 | Sampul | 8 gambar `_1` sebagai thumbnail | AI Vision untuk operasional: masalah bisnis dan solusinya |
| 2 | UC1 · 1 | `UC1_produce_grading_1.png` | Mutu warna setiap buah terpantau langsung di line |
| 3 | UC1 · 2 | `UC1_produce_grading_2.png` | Setiap lot punya keputusan dan bukti untuk pembeli |
| 4 | UC2 · 1 | `UC2_fill_level_1.png` | Level isi setiap botol terpantau langsung, per nozzle |
| 5 | UC2 · 2 | `UC2_fill_level_2.png` | Underfill di-reject otomatis, giveaway terukur per nozzle |
| 6 | UC3 · 1 | `UC3_pack_count_1.png` | Kemasan kurang isi tertahan sebelum disegel |
| 7 | UC3 · 2 | `UC3_pack_count_2.png` | Setiap reject punya bukti, penyebab, dan tindakan perbaikan |
| 8 | UC4 · 1 | `UC4_parcel_conveyor_1.png` | Ukuran setiap paket di belt terukur tanpa meteran |
| 9 | UC4 · 2 | `UC4_parcel_conveyor_2.png` | Volume terukur dipakai untuk muat truk dan tagihan |
| 10 | UC5 · 1 | `UC5_ukurpaket_1.png` | Kurir mengukur paket dengan satu foto dari HP |
| 11 | UC5 · 2 | `UC5_ukurpaket_2.png` | Ukuran dihitung dari satu foto, dengan pemeriksaan kualitas otomatis |
| 12 | UC6 · 1 | `UC6_warehouse_1.png` | Saat AI mendeteksi bahaya, kameranya langsung tampil di layar operator |
| 13 | UC6 · 2 | `UC6_warehouse_2.png` | Setiap insiden punya bukti lengkap dan tindakan perbaikan |
| 14 | UC7 · 1 | `UC7_plate_vehicle_1.png` | Kendaraan terhitung otomatis dari CCTV yang sudah ada |
| 15 | UC7 · 2 | `UC7_plate_vehicle_2.png` | Plat nomor terbaca dan tercatat dengan foto |
| 16 | UC8 · 1 | `UC8_document_ocr_1.png` | Foto tiket langsung menjadi data tabel, tanpa ketik ulang |
| 17 | UC8 · 2 | `UC8_document_ocr_2.png` | Beberapa tiket dalam satu foto tetap terbaca satu per satu |

## 6. Isi per slide

### Slide 1 · Sampul

- **Judul:** AI Vision untuk operasional: masalah bisnis dan solusinya
- **Subjudul:** Pabrik, gudang, logistik, parkir, dan dokumen, dari kamera dan foto yang sudah ada.
- **Visual:** grid berisi delapan gambar `_1`, masing-masing dengan nama use case di bawahnya.
- **Baris bawah:** `[isi nama tim] · [isi tanggal]`
- **Speaker notes:** Deck ini merangkum delapan use case AI vision. Setiap use case dibahas dalam dua slide, dan
  setiap slide menjawab satu masalah bisnis beserta solusinya.

---

### UC1 · Produce Grading

**Untuk:** packing house buah dan sayur, eksportir, dan pemasok supermarket.

#### Slide 2 · UC1 · 1
- **Label:** `USE CASE 1 · PRODUCE GRADING`
- **Judul:** Mutu warna setiap buah terpantau langsung di line
- **Gambar:** `UC1_produce_grading_1.png`
- **Masalah:** Warna dan kematangan buah dicek manual dengan sampel, sehingga lot campur warna baru ketahuan setelah
  sampai di pembeli.
- **Solusi:**
  - Kamera di atas conveyor dan edge AI mengelompokkan setiap buah ke kelas warna sesuai standar USDA, dan setiap buah
    dihitung sekali di count gate.
  - Dashboard TV di line menampilkan komposisi grade dan off-colour lot terhadap limit secara real-time.
  - Saat off-colour melewati limit, operator langsung mendapat arahan: sortir ulang atau beri label Mixed Color.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Ini Dashboard TV yang terpasang di line. Setiap buah diberi kotak sesuai kelas warnanya dan
  dihitung sekali. Begitu off-colour lot melewati limit, operator tahu saat itu juga dan bisa bertindak selagi buah
  masih di line, bukan setelah lot ditolak pembeli.

#### Slide 3 · UC1 · 2
- **Label:** `USE CASE 1 · PRODUCE GRADING`
- **Judul:** Setiap lot punya keputusan dan bukti untuk pembeli
- **Gambar:** `UC1_produce_grading_2.png`
- **Masalah:** Klaim warna dari pembeli atau importir sulit dijawab karena tidak ada data per lot, sementara standar
  setiap pembeli berbeda.
- **Solusi:**
  - Laporan Lot berisi keputusan lot sesuai standar warna USDA, foto bukti buah off-colour, dan sebaran warna setiap
    buah.
  - Riwayat lot mencatat setiap alert, hold, sortir ulang, dan siapa yang menangani.
  - Sertifikat lot dalam PDF bisa langsung dikirim ke QA pembeli.
- **Catatan kaki:** sama dengan slide 2
- **Speaker notes:** Laporan Lot menyimpan keputusan, bukti, dan riwayat setiap lot. Saat ada klaim warna, tim sales
  menjawab dengan data lot tersebut, bukan dengan perkiraan.

---

### UC2 · Fill Level Inspection

**Untuk:** pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol.

#### Slide 4 · UC2 · 1
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION`
- **Judul:** Level isi setiap botol terpantau langsung, per nozzle
- **Gambar:** `UC2_fill_level_1.png`
- **Masalah:** Isi botol hanya dicek lewat sampel berkala, sehingga botol underfill lolos ke pasar dan nozzle yang
  bermasalah terlambat ketahuan.
- **Solusi:**
  - Kamera di mesin pengisi dan edge AI mengukur level isi setiap botol, lalu mengubah tinggi cairan menjadi volume
    berdasarkan profil botol.
  - Status setiap nozzle tampil langsung: pass, underfill, atau overfill.
  - Supervisor bisa menghentikan nozzle yang bermasalah dari layar yang sama.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Di kamera terlihat outline botol, garis target di leher botol, dan level isi yang bergerak naik.
  Di sebelah kanan, nozzle yang underfill ditandai merah, dan supervisor bisa langsung menghentikannya untuk dicek tanpa
  menunggu sampel berikutnya.

#### Slide 5 · UC2 · 2
- **Label:** `USE CASE 2 · FILL LEVEL INSPECTION`
- **Judul:** Underfill di-reject otomatis, giveaway terukur per nozzle
- **Gambar:** `UC2_fill_level_2.png`
- **Masalah:** Botol overfill adalah produk yang terbuang setiap hari tetapi tidak pernah terukur, dan reject tanpa
  bukti sulit ditindaklanjuti tim teknik.
- **Solusi:**
  - Botol di bawah toleransi di-reject lewat sinyal ke PLC.
  - Setiap reject tersimpan dengan bukti (gambar kamera, level isi, dan sinyal ke PLC), lalu dikonfirmasi QC atau
    ditandai alarm palsu.
  - Giveaway per nozzle dibandingkan dengan target dan toleransi, lengkap dengan saran tindakan untuk Maintenance.
- **Catatan kaki:** sama dengan slide 4
- **Speaker notes:** Halaman ini dipakai QC dan Maintenance. Setiap reject punya bukti, dan grafik giveaway per nozzle
  menunjukkan nozzle mana yang perlu disetel, berdasarkan data, bukan perasaan.

---

### UC3 · Pack Count QC

**Untuk:** pabrik makanan dan minuman kemasan, FMCG, dan co-packer.

#### Slide 6 · UC3 · 1
- **Label:** `USE CASE 3 · PACK COUNT QC`
- **Judul:** Kemasan kurang isi tertahan sebelum disegel
- **Gambar:** `UC3_pack_count_1.png`
- **Masalah:** Tray dan kardus kurang isi baru ketahuan setelah ada komplain distributor atau konsumen, karena cek
  manual hanya sampel.
- **Solusi:**
  - Kamera di ujung line dan edge AI menghitung isi setiap tray per slot.
  - Slot kosong ditandai, lalu tray kurang isi diberi status SHORT dan di-reject sebelum disegel.
  - Peta posisi slot kosong menunjukkan apakah masalah berulang di lane filler yang sama.
- **Catatan kaki:** Video: simulasi 3D buatan tim · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Ini Dashboard TV di ujung line kaleng. Tray yang kurang isi ditandai SHORT dan slot kosongnya
  dilingkari. Kalau slot yang sama berulang kali kosong, itu menunjuk ke lane filler tertentu, sehingga yang
  diperbaiki adalah penyebabnya.

#### Slide 7 · UC3 · 2
- **Label:** `USE CASE 3 · PACK COUNT QC`
- **Judul:** Setiap reject punya bukti, penyebab, dan tindakan perbaikan
- **Gambar:** `UC3_pack_count_2.png`
- **Masalah:** Penyebab kekurangan isi (feeder, lane filler, atau robot) tidak tercatat, sehingga masalah yang sama
  terus berulang.
- **Solusi:**
  - Detail reject menampilkan peta slot, root cause, serta foto dan klip bukti.
  - Timeline mencatat kejadian dari feeder gap sampai rework, termasuk notifikasi WhatsApp ke Line Supervisor.
  - Corrective action ditugaskan ke tim terkait dan bisa diekspor ke PDF.
- **Catatan kaki:** sama dengan slide 6
- **Speaker notes:** Ini detail satu reject. Investigasi selesai lebih cepat karena slot yang kosong, penyebabnya,
  penanggung jawabnya, dan buktinya ada di satu halaman yang siap ditunjukkan ke pelanggan atau auditor.

---

### UC4 · Parcel Dimensioning (conveyor)

**Untuk:** gudang distribusi, 3PL, e-commerce fulfilment, dan ekspedisi.

#### Slide 8 · UC4 · 1
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING`
- **Judul:** Ukuran setiap paket di belt terukur tanpa meteran
- **Gambar:** `UC4_parcel_conveyor_1.png`
- **Masalah:** Ukuran paket diukur manual dengan meteran atau tidak diukur sama sekali, sehingga data volume tidak
  tersedia.
- **Solusi:**
  - Kamera di atas belt bongkar muat dan edge AI mengukur P × L × T serta volume setiap paket.
  - Setiap paket dihitung sekali di count line dan dikelompokkan per kelas ukuran.
  - Paket yang ukurannya dekat batas kelas masuk manual check, bukan ditebak.
- **Catatan kaki:** Video: Pexels (lisensi Pexels) · layar mockup, angka di layar adalah ilustrasi
- **Speaker notes:** Ini Dashboard TV di belt bongkar truk. Setiap paket diberi kotak sesuai kelas ukurannya, lalu
  masuk tabel bersama P × L × T, volume, dan berat volumetriknya. Paket yang meragukan dikonfirmasi oleh petugas.

#### Slide 9 · UC4 · 2
- **Label:** `USE CASE 4 · PARCEL DIMENSIONING`
- **Judul:** Volume terukur dipakai untuk muat truk dan tagihan
- **Gambar:** `UC4_parcel_conveyor_2.png`
- **Masalah:** Tagihan hanya berdasarkan berat timbangan, padahal paket ringan tetapi besar memakan ruang truk, dan
  rencana muat masih berdasarkan perkiraan.
- **Solusi:**
  - Isi setiap truk dihitung dari volume paket yang terukur.
  - Berat volumetrik dibandingkan dengan berat aktual per pelanggan, dan tagihan memakai yang lebih besar.
  - Data langsung dikirim ke TMS/WMS dan sistem invoice tanpa input ulang.
- **Catatan kaki:** sama dengan slide 8
- **Speaker notes:** Data ukuran langsung dipakai dua tim: logistik untuk rencana muat truk, dan finance untuk dasar
  tagihan. Pelanggan yang mengirim paket ringan tetapi besar ditagih sesuai ruang yang benar-benar dipakai.

---

### UC5 · UkurPaket (APK Android, mode foto)

**Untuk:** kurir pickup, counter ekspedisi, dan agen. Perangkat: HP Android atau handheld kurir, diuji di Urovo DT50.

#### Slide 10 · UC5 · 1
- **Label:** `USE CASE 5 · UKURPAKET`
- **Judul:** Kurir mengukur paket dengan satu foto dari HP
- **Gambar:** `UC5_ukurpaket_1.png`
- **Masalah:** Saat pickup dan di counter, ukuran paket diukur dengan meteran atau hanya ditebak, sementara handheld
  kurir umumnya tidak punya ARCore atau sensor depth untuk aplikasi ukur berbasis AR.
- **Solusi:**
  - APK memandu sudut foto dan memastikan HP diam sebelum memotret.
  - Kurir tap objek atau tarik kotak, lalu AI memisahkan objek dari latar belakang.
  - P × L × T dan berat volumetrik langsung tampil di HP, untuk benda kotak maupun benda bulat (diameter × diameter ×
    tinggi).
- **Catatan kaki:** Tampilan aktual APK UkurPaket versi terbaru (mode foto, tanpa AR) dengan foto dari HP Urovo DT50
- **Speaker notes:** Layar-layar ini adalah tampilan aktual APK yang diisi foto dari HP uji. Kurir cukup memotret dan
  menandai objek, lalu hasilnya keluar di layar yang sama tanpa ARCore atau sensor tambahan. Berat volumetrik bukan
  berat aktual: berat aktual tetap dari timbangan, dan berat tagih adalah yang lebih besar dari keduanya.

#### Slide 11 · UC5 · 2
- **Label:** `USE CASE 5 · UKURPAKET`
- **Judul:** Ukuran dihitung dari satu foto, dengan pemeriksaan kualitas otomatis
- **Gambar:** `UC5_ukurpaket_2.png`
- **Masalah:** Ukuran yang salah langsung berdampak ke tagihan, sehingga hasil ukur harus bisa dipercaya dan bisa
  dicek ulang.
- **Solusi:**
  - APK menggabungkan segmentasi, depth map, sensor gravitasi, dan jarak fokus lensa untuk membentuk kotak 3D di
    sekitar objek, lalu menghitung ukurannya dalam cm.
  - Quality gate memberi status Akurat atau Perlu Dicek, misalnya untuk foto buram, objek terpotong, atau bentuk yang
    bukan kotak.
  - Status dan foto bukti tersimpan bersama ukuran, sehingga admin atau hub bisa mengecek ulang.
- **Catatan kaki:** Data: hasil ukur dan depth map yang disimpan APK UkurPaket · kotak 3D digambar dari koordinat yang
  dihitung APK
- **Speaker notes:** Di setiap baris, kiri adalah foto dengan hasil segmentasi dan kotak 3D, dan tengah adalah depth
  map: merah berarti dekat, biru berarti jauh. Garis putus-putus adalah garis kotak yang tertutup dari kamera. Benda
  kotak mendapat status Akurat, sedangkan benda bulat tetap diukur tetapi diberi status Perlu Dicek. Hasil berstatus
  Perlu Dicek tetap bisa dipakai kurir, dan ukurannya tersimpan bersama foto bukti untuk dicek ulang.

---

### UC6 · Warehouse Live Ops

**Untuk:** 3PL dan distribusi, manufaktur, cold storage, dan e-commerce fulfilment.

#### Slide 12 · UC6 · 1
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS`
- **Judul:** Saat AI mendeteksi bahaya, kameranya langsung tampil di layar operator
- **Gambar:** `UC6_warehouse_1.png`
- **Masalah:** Risiko tabrakan orang dan forklift baru ketahuan setelah terjadi, karena operator tidak mungkin memantau
  belasan layar CCTV sepanjang shift.
- **Solusi:**
  - CCTV yang sudah ada dan edge AI mendeteksi orang, forklift, APD, dan zona di setiap kamera.
  - Saat near miss terdeteksi, kamera terkait otomatis tampil di layar utama.
  - Peringatan masuk ke daftar dan bisa dikonfirmasi atau ditandai alarm palsu, lengkap dengan posisinya di peta lantai.
- **Catatan kaki:** Cuplikan kamera: NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0) · layar mockup, angka di layar adalah
  ilustrasi
- **Speaker notes:** Satu operator bisa mengawasi banyak kamera karena AI yang menyaring kejadian. Begitu near miss
  terdeteksi, kameranya tampil sendiri di layar besar dan peringatannya masuk ke daftar di sebelah kanan.

#### Slide 13 · UC6 · 2
- **Label:** `USE CASE 6 · WAREHOUSE LIVE OPS`
- **Judul:** Setiap insiden punya bukti lengkap dan tindakan perbaikan
- **Gambar:** `UC6_warehouse_2.png`
- **Masalah:** Mencari bukti satu insiden berarti memutar ulang rekaman berjam-jam, dan laporan K3 masih disusun manual.
- **Solusi:**
  - Klip sebelum dan sesudah kejadian, cuplikan bukti, dan posisi di peta tersimpan otomatis per insiden.
  - Linimasa mencatat deteksi, notifikasi WhatsApp, sampai insiden ditangani.
  - CAPA dengan penanggung jawab dan tenggat, serta ekspor bukti PDF untuk audit K3.
- **Catatan kaki:** sama dengan slide 12
- **Speaker notes:** Investigasi selesai lebih cepat karena klip, posisi, dan linimasa sudah tersimpan per insiden.
  Tindakan perbaikan juga tercatat sampai selesai, sehingga siap untuk audit.

---

### UC7 · Plate Recognition & Vehicle Counting (CCTV parkir)

**Untuk:** pengelola parkir, depot dan gudang distribusi, kawasan industri, dan gedung perkantoran.

#### Slide 14 · UC7 · 1
- **Label:** `USE CASE 7 · PLATE & VEHICLE`
- **Judul:** Kendaraan terhitung otomatis dari CCTV yang sudah ada
- **Gambar:** `UC7_plate_vehicle_1.png`
- **Masalah:** Kendaraan masuk dan keluar dicatat manual oleh petugas, sehingga tidak ada data jumlah motor, mobil,
  dan truk.
- **Solusi:**
  - CCTV di gerbang dan edge AI mendeteksi serta melacak setiap kendaraan, lalu menghitungnya sekali per ID tracking.
  - Hitungan dipisah per jenis kendaraan (motor, mobil, truk/bus) dan membedakan kendaraan yang bergerak dari yang parkir.
  - Beberapa kamera dipantau sekaligus di satu layar.
- **Catatan kaki:** Video: rekaman CCTV aktual dari dataset publik Hugging Face `rithwikn/ai_cctv_videos`, dua kamera
  digabung dalam satu video
- **Speaker notes:** Video ini menggabungkan dua kamera CCTV aktual. Kamera gerbang menghitung kendaraan, dan setiap
  kendaraan diberi ID tracking sehingga dihitung sekali. Kendaraan yang bergerak dan yang parkir dihitung terpisah.

#### Slide 15 · UC7 · 2
- **Label:** `USE CASE 7 · PLATE & VEHICLE`
- **Judul:** Plat nomor terbaca dan tercatat dengan foto
- **Gambar:** `UC7_plate_vehicle_2.png`
- **Masalah:** Plat nomor ditulis tangan sehingga rawan salah dan terlewat, dan mencari kapan kendaraan tertentu datang
  berarti memutar ulang rekaman CCTV.
- **Solusi:**
  - Plat dideteksi di dalam kotak kendaraan, lalu dibaca dengan OCR.
  - Plat ditetapkan setelah beberapa bacaan sama, bukan dari satu frame saja.
  - Setiap plat tercatat bersama foto plat, jenis kendaraan, kamera, dan waktu.
  - Kamera untuk baca plat dipasang dekat jalur masuk, supaya plat terlihat cukup besar.
- **Catatan kaki:** sama dengan slide 14
- **Speaker notes:** Di area parkir, plat dibaca dari banyak frame dan baru ditetapkan setelah bacaannya konsisten,
  sehingga hasilnya stabil. Plat di kamera gerbang tidak dibaca karena terlalu jauh. Karena itu, kamera baca plat
  dipasang dekat jalur masuk.

---

### UC8 · Document OCR (tiket dari foto atau hasil scan)

**Untuk:** tim finance dan admin yang merekap tiket, kuitansi, atau dokumen hasil scan, misalnya untuk reimbursement
perjalanan dinas dan rekap biaya.

#### Slide 16 · UC8 · 1
- **Label:** `USE CASE 8 · DOCUMENT OCR`
- **Judul:** Foto tiket langsung menjadi data tabel, tanpa ketik ulang
- **Gambar:** `UC8_document_ocr_1.png`
- **Masalah:** Tiket, kuitansi, dan dokumen hasil scan diketik ulang manual untuk rekap dan reimbursement. Prosesnya
  lambat, rawan salah ketik, dan sulit diaudit.
- **Solusi:**
  - Vision-language model membaca foto dan langsung mengisi field: tanggal, stasiun asal, stasiun tujuan, jam
    berangkat, jam tiba, dan harga.
  - Hasilnya langsung berbentuk tabel yang siap direkap.
  - Kotak berwarna di gambar menghubungkan setiap field di tiket dengan kolom yang sama di tabel.
- **Catatan kaki:** Hasil ekstraksi dari repo GitHub `sndypvtra/VL-Model-for-Taiwan-Railways-tickets-Extractor` ·
  bounding box ditambahkan untuk presentasi
- **Speaker notes:** Ini hasil ekstraksi model pada satu foto tiket. Warna kotak membantu membaca hasilnya: biru untuk
  tanggal, hijau untuk stasiun, oranye untuk jam, dan ungu untuk harga, dengan warna yang sama di tiket dan di tabel.

#### Slide 17 · UC8 · 2
- **Label:** `USE CASE 8 · DOCUMENT OCR`
- **Judul:** Beberapa tiket dalam satu foto tetap terbaca satu per satu
- **Gambar:** `UC8_document_ocr_2.png`
- **Masalah:** Dokumen sering difoto bersamaan dalam satu gambar dengan format yang beragam (dua bahasa, cetakan kecil,
  foto miring), sehingga sulit ditangani template OCR biasa.
- **Solusi:**
  - Model memisahkan setiap tiket dalam satu foto dan mengisi satu baris tabel per tiket.
  - Nomor tiket di foto sama dengan nomor baris di tabel, sehingga mudah dicocokkan.
  - Field yang kosong atau tidak sesuai format bisa diarahkan ke pengecekan manual sebelum data dipakai.
- **Catatan kaki:** sama dengan slide 16
- **Speaker notes:** Foto yang berisi beberapa tiket tetap dipecah per tiket, dan setiap tiket menjadi satu baris
  tabel. Untuk dokumen yang sulit dibaca, field yang kosong diarahkan ke pengecekan manual, sehingga data yang masuk
  ke rekap tetap bersih.

## 7. Checklist sebelum selesai

- [ ] Total 17 slide: sampul, lalu 2 slide per use case, dan setiap slide berisi satu masalah dan solusinya.
- [ ] Tidak ada slide bukti atau hasil uji, model bisnis, harga, pilot, timeline, atau langkah berikutnya.
- [ ] Tidak ada angka di teks slide dan speaker notes (lihat bagian 3).
- [ ] Ke-16 gambar dari `images/` dipakai dengan nama file persis seperti di bagian 4, utuh dan tidak diedit.
- [ ] Tidak ada kata "nyata", "rusuk", atau "apa adanya". Istilah mengikuti tabel di bagian 3.
- [ ] Setiap slide use case punya catatan kaki sumber.
- [ ] Speaker notes terisi di semua slide.
