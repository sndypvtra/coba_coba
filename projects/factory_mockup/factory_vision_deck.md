# Prompt Claude Design: Factory Vision, satu deck untuk empat produk pabrik

Satu presentasi berisi keempat produk: **Produce Grading, Fill Level Inspection, Pack Count QC, dan
Parcel Dimensioning**. Setiap produk tetap punya bagiannya sendiri dengan alur yang sama, jadi mudah dijelaskan
satu per satu, lalu ditutup dengan bukti PoC dan langkah pilot untuk semuanya. Total **34 slide**.

## 1. Gambar yang dipakai

- 26 gambar PNG 3840 × 2160 dari empat folder `apps/<app>/pages/`. Nama file sudah diberi awalan produk
  (**PG** Produce Grading, **FL** Fill Level, **PC** Pack Count QC, **PD** Parcel Dimensioning), jadi semuanya
  aman diunggah ke **satu proyek** tanpa bentrok nama. Jangan ganti nama filenya.
- Templatenya sama dengan mockup warehouse: setiap gambar adalah layar web app atau Dashboard TV produk itu sendiri.
  Dari PoC hanya diambil gambar kamera dengan overlay AI, plus angka hasil ukurnya. Angka lain ilustrasi, dan setiap
  gambar mencantumkannya di pojok kanan bawah. Tidak ada angka rupiah.

## 2. Susunan deck (34 slide)

| # | Slide | Gambar | Yang ditonjolkan |
|---|---|---|---|
| 1 | Sampul | `PG_03_dashboard_tv_tomat.png`, `FL_03_dashboard_tv.png`, `PC_03_dashboard_tv_tray.png`, `PD_03_dashboard_tv.png` | Factory Vision · empat produk |
| 2 | Masalah di pabrik | – | satu masalah per produk |
| 3 | Empat produk, satu cara kerja | – | kamera → edge AI box → web app & TV → tindakan di line |
| 4 | Bagian A · Produce Grading (pembuka) | `PG_03_dashboard_tv_tomat.png` kecil | untuk siapa, 3 masalah, alur kerja |
| 5 | Produce Grading · 1/6 · Ringkasan | `PG_01_ringkasan.png` | Setiap shift, mutu warna semua line terbaca di satu layar |
| 6 | Produce Grading · 2/6 · Live Monitoring | `PG_02_live_monitoring.png` | Supervisor melihat setiap buah yang keluar dari kelasnya, dan langsung bertindak |
| 7 | Produce Grading · 3/6 · Dashboard TV | `PG_03_dashboard_tv_tomat.png` + `PG_04_dashboard_tv_lemon.png` kecil | Layar di line menunjukkan mutu lot saat itu juga |
| 8 | Produce Grading · 4/6 · Laporan Lot | `PG_05_laporan_lot.png` | Setiap lot punya keputusan, bukti, dan riwayat yang bisa ditunjukkan ke pembeli |
| 9 | Produce Grading · 5/6 · Standar Grade | `PG_06_standar_grade.png` | Standar resmi dan spec pembeli, diatur sendiri oleh QC |
| 10 | Produce Grading · 6/6 · Kamera, Alert & Integrasi | `PG_07_kamera_alert_integrasi.png` | Orang yang tepat tahu dalam hitungan detik, line bertindak otomatis |
| 11 | Bagian B · Fill Level Inspection (pembuka) | `FL_03_dashboard_tv.png` kecil | untuk siapa, 3 masalah, alur kerja |
| 12 | Fill Level Inspection · 1/6 · Ringkasan | `FL_01_ringkasan.png` | Setiap botol dicek; underfill di-reject, overfill dihitung sebagai produk terbuang |
| 13 | Fill Level Inspection · 2/6 · Live Monitoring | `FL_02_live_monitoring.png` | Level isi terlihat langsung di layar, nozzle demi nozzle |
| 14 | Fill Level Inspection · 3/6 · Dashboard TV | `FL_03_dashboard_tv.png` | Level isi diukur setiap frame, selama botol diisi |
| 15 | Fill Level Inspection · 4/6 · Reject & Giveaway | `FL_04_reject_giveaway.png` | Setiap reject punya bukti; setiap mL lebih dihitung |
| 16 | Fill Level Inspection · 5/6 · Spesifikasi SKU | `FL_05_spesifikasi_sku.png` | Target, toleransi, dan tindakan diatur per SKU |
| 17 | Fill Level Inspection · 6/6 · Kamera, Alert & Integrasi | `FL_06_kamera_alert_integrasi.png` | Reject langsung ke PLC, alert langsung ke orang yang tepat |
| 18 | Bagian C · Pack Count QC (pembuka) | `PC_03_dashboard_tv_tray.png` kecil | untuk siapa, 3 masalah, alur kerja |
| 19 | Pack Count QC · 1/6 · Ringkasan | `PC_01_ringkasan.png` | Tray dan kardus kurang isi ditahan sebelum disegel |
| 20 | Pack Count QC · 2/6 · Live Monitoring | `PC_02_live_monitoring.png` | Setiap tray dan kardus terlihat dihitung, langsung di layar |
| 21 | Pack Count QC · 3/6 · Dashboard TV | `PC_03_dashboard_tv_tray.png` + `PC_04_dashboard_tv_packing.png` kecil | Setiap tray dihitung, setiap slot kosong ditandai |
| 22 | Pack Count QC · 4/6 · Detail Reject | `PC_05_detail_reject.png` | Setiap reject punya bukti, penyebab, dan tindakan perbaikan |
| 23 | Pack Count QC · 5/6 · Spesifikasi Kemasan | `PC_06_spesifikasi_kemasan.png` | Layout slot dan aturan isi diatur per SKU |
| 24 | Pack Count QC · 6/6 · Kamera, Alert & Integrasi | `PC_07_kamera_alert_integrasi.png` | Kemasan kurang isi dialihkan otomatis, orang yang tepat langsung tahu |
| 25 | Bagian D · Parcel Dimensioning (pembuka) | `PD_03_dashboard_tv.png` kecil | untuk siapa, 3 masalah, alur kerja |
| 26 | Parcel Dimensioning · 1/6 · Ringkasan | `PD_01_ringkasan.png` | Ukuran dan volume setiap paket, tanpa meteran |
| 27 | Parcel Dimensioning · 2/6 · Live Monitoring | `PD_02_live_monitoring.png` | Setiap paket terlihat diukur saat lewat |
| 28 | Parcel Dimensioning · 3/6 · Dashboard TV | `PD_03_dashboard_tv.png` | Satu kamera mengukur P × L × T paket di belt |
| 29 | Parcel Dimensioning · 4/6 · Muat & Tagihan | `PD_04_muat_tagihan.png` | Volume terukur dipakai untuk muat truk dan tagihan |
| 30 | Parcel Dimensioning · 5/6 · Kelas Ukuran & Tagihan | `PD_05_kelas_ukuran.png` | Kelas ukuran, rumus tagihan, dan kalibrasi diatur sendiri |
| 31 | Parcel Dimensioning · 6/6 · Kamera, Alert & Integrasi | `PD_06_kamera_alert_integrasi.png` | Data ukuran langsung masuk ke WMS, TMS, dan invoice |
| 32 | Ringkasan: empat produk, satu cara kerja | – | masalah → hasil per produk |
| 33 | Bukti PoC | – | hasil terukur per produk dan batasannya |
| 34 | Pilot & langkah berikutnya | – | mulai dari satu produk di satu line |

## 3. Cara mengerjakan di Claude Design (satu proyek, 4 tahap)

Gambar diunggah bertahap per produk supaya tidak kena batas lampiran dan Claude Design tetap fokus.
Kalau ternyata Claude Design bisa menerima 26 gambar sekaligus, lampirkan semuanya di tahap 1,
tempel prompt utama, lalu tulis "kerjakan semua slide 1–34".

**Tahap 1 · Bagian A · Produce Grading** — lampirkan 7 gambar dari `apps/produce_grading/pages/`: `PG_01_ringkasan.png`, `PG_02_live_monitoring.png`, `PG_03_dashboard_tv_tomat.png`, `PG_04_dashboard_tv_lemon.png`, `PG_05_laporan_lot.png`, `PG_06_standar_grade.png`, `PG_07_kamera_alert_integrasi.png`

Tempel **prompt utama** (bagian 5), lalu kirim.

**Tahap 2 · Bagian B · Fill Level Inspection** — lampirkan 6 gambar dari `apps/fill_level_inspection/pages/`: `FL_01_ringkasan.png`, `FL_02_live_monitoring.png`, `FL_03_dashboard_tv.png`, `FL_04_reject_giveaway.png`, `FL_05_spesifikasi_sku.png`, `FL_06_kamera_alert_integrasi.png`

Ketik pesan ini, lalu kirim:

```text
Ini gambar untuk Bagian B · Fill Level Inspection. Kerjakan slide 11–17 sesuai prompt utama.
```

**Tahap 3 · Bagian C · Pack Count QC** — lampirkan 7 gambar dari `apps/pack_count_qc/pages/`: `PC_01_ringkasan.png`, `PC_02_live_monitoring.png`, `PC_03_dashboard_tv_tray.png`, `PC_04_dashboard_tv_packing.png`, `PC_05_detail_reject.png`, `PC_06_spesifikasi_kemasan.png`, `PC_07_kamera_alert_integrasi.png`

Ketik pesan ini, lalu kirim:

```text
Ini gambar untuk Bagian C · Pack Count QC. Kerjakan slide 18–24 sesuai prompt utama.
```

**Tahap 4 · Bagian D · Parcel Dimensioning** — lampirkan 6 gambar dari `apps/parcel_dimensioning/pages/`: `PD_01_ringkasan.png`, `PD_02_live_monitoring.png`, `PD_03_dashboard_tv.png`, `PD_04_muat_tagihan.png`, `PD_05_kelas_ukuran.png`, `PD_06_kamera_alert_integrasi.png`

Ketik pesan ini, lalu kirim:

```text
Ini gambar untuk Bagian D · Parcel Dimensioning. Kerjakan slide 25–31 sesuai prompt utama. Lalu kerjakan slide penutup 32–34, dan perbarui sampul (slide 1): isi keempat bingkai dengan PG_03_dashboard_tv_tomat.png, FL_03_dashboard_tv.png, PC_03_dashboard_tv_tray.png, PD_03_dashboard_tv.png.
```

Setelah tahap 4 selesai, minta: "Periksa semua slide: judul di posisi yang sama, tidak ada teks terpotong, lalu ekspor ke PPTX."

## 4. Kalau Claude Design berhenti di tengah

Tulis: "Lanjutkan dari slide berikutnya sesuai prompt utama." Kalau slide terlalu padat: "Perbesar screenshot di slide
X sampai 65% lebar slide dan persingkat poinnya jadi satu baris."

Mau menambah **1 slide arsitektur sistem**? Lihat bagian 6. Itu bisa dikerjakan setelah deck 34 slide jadi,
atau sebelum ekspor.

## 5. Prompt utama (tempel di tahap 1)

```text
Buatkan presentasi 16:9 berbahasa Indonesia berjudul "Factory Vision" sebanyak 34 slide, siap diekspor ke PowerPoint. Isinya empat produk video analytics untuk pabrik, masing-masing di bagiannya sendiri. Gambar dilampirkan bertahap per produk: sekarang terlampir gambar Bagian A (Produce Grading). Kerjakan sekarang slide 1–3 dan slide 4–10; bagian lain menunggu gambarnya di pesan berikutnya. Untuk gambar yang belum terlampir, pakai bingkai placeholder berlabel nama filenya. Di sampul (slide 1), isi dulu bingkai Produce Grading dengan PG_03_dashboard_tv_tomat.png; tiga bingkai lain diisi nanti.

Tujuan utamanya: calon pembeli MELIHAT web app tiap produk bekerja, layar demi layar, dan memahami manfaat bisnis tiap layar. Jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC) empat produk inspeksi berbasis kamera. Setiap produk dijual sendiri, per line, dengan web app, Dashboard TV, alert, dan integrasinya sendiri:
- Produce Grading: Grade warna setiap buah di line, sesuai standar USDA dan OECD, lengkap dengan bukti per lot. Untuk packing house buah dan sayur, eksportir, pemasok supermarket.
- Fill Level Inspection: Level isi setiap botol terhadap target dan toleransi; underfill di-reject, overfill dihitung sebagai giveaway. Untuk pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol.
- Pack Count QC: Jumlah isi setiap tray dan kardus sebelum disegel, lengkap dengan slot yang kosong dan penyebabnya. Untuk pabrik makanan dan minuman kemasan, FMCG, co-packer.
- Parcel Dimensioning: Panjang × lebar × tinggi dan volume setiap paket di belt, untuk muat truk dan tagihan berat volumetrik. Untuk gudang distribusi, 3PL, e-commerce fulfilment, ekspedisi.
Penontonnya pemilik dan direktur pabrik yang sedang memilih sistem video analytics. Mereka bertanya: "Masalah saya yang mana yang selesai, layar apa yang dipakai tim saya, apa yang terjadi di line saat ada masalah, dan apa buktinya?"

GAYA VISUAL
- Sama dengan deck "Warehouse Live Ops": latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, huruf Inter. Setiap produk punya warna aksen sendiri: Produce Grading hijau #16A34A, Fill Level Inspection biru #2563EB, Pack Count QC oranye #D97706, Parcel Dimensioning ungu #7C3AED. Slide pembuka dan penutup memakai aksen biru #2563EB (untuk label kecil, ikon, dan garis penanda). Slide 1 dan slide terakhir berlatar navy #0B1220.
- Judul setiap slide berupa kalimat kesimpulan dari sudut pandang pembeli.
- Slide tur produk: screenshot adalah bintangnya. Screenshot utama mengisi minimal 60% lebar slide, utuh dalam bingkai browser (sudut membulat, bayangan halus), jangan dipotong. Teks pendamping di kolom samping (maksimal 35% lebar). Selang-seling posisi screenshot kiri dan kanan.
- Screenshot Dashboard TV (latar gelap) ditaruh dalam bingkai layar TV (bezel tipis, sudut membulat).
- Pada setiap screenshot, pasang 3 penanda bernomor (lingkaran kecil warna aksen) di bagian layar yang dijelaskan, sesuai petunjuk letak dalam kurung di setiap poin.
- Jika ada screenshot kedua, tampilkan lebih kecil (±30% lebar), bertumpuk di pojok screenshot utama dengan bayangan.
- Kolom teks tiap slide tur: label kecil "NAMA PRODUK · FITUR n/6 · NAMA LAYAR", judul, 3 poin bernomor, satu baris tebal "Manfaat untuk bisnis", dan baris kecil "Dipakai oleh".
- Catatan kaki kecil di slide yang memuat gambar kamera, sesuai produknya:
  Produce Grading: "Video: Pexels (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
  Fill Level Inspection: "Video: Pexels 8720278 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
  Pack Count QC: "Video: simulasi 3D buatan tim dengan data kebenaran · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
  Parcel Dimensioning: "Video: Pexels 5370836 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.
- Setiap bagian produk dibuka dengan slide pembuka bagian, lalu slide tur layar. Slide tur memakai warna aksen produk itu.

GAMBAR (diunggah bertahap)
PG_01_ringkasan.png · PG_02_live_monitoring.png · PG_03_dashboard_tv_tomat.png · PG_04_dashboard_tv_lemon.png · PG_05_laporan_lot.png · PG_06_standar_grade.png · PG_07_kamera_alert_integrasi.png · FL_01_ringkasan.png · FL_02_live_monitoring.png · FL_03_dashboard_tv.png · FL_04_reject_giveaway.png · FL_05_spesifikasi_sku.png · FL_06_kamera_alert_integrasi.png · PC_01_ringkasan.png · PC_02_live_monitoring.png · PC_03_dashboard_tv_tray.png · PC_04_dashboard_tv_packing.png · PC_05_detail_reject.png · PC_06_spesifikasi_kemasan.png · PC_07_kamera_alert_integrasi.png · PD_01_ringkasan.png · PD_02_live_monitoring.png · PD_03_dashboard_tv.png · PD_04_muat_tagihan.png · PD_05_kelas_ukuran.png · PD_06_kamera_alert_integrasi.png

PEMBUKA

1. Sampul (latar navy)
- Judul: Factory Vision
- Subjudul: Video analytics untuk line produksi: grade buah, level isi botol, isi kemasan, dan ukuran paket, dari kamera di line.
- Teks kecil: Konsep produk · [Nama tim] · [Tanggal]
- Visual: empat bingkai layar TV kecil berjajar 2×2 di sisi kanan, satu per produk, masing-masing dengan nama produknya: PG_03_dashboard_tv_tomat.png (Produce Grading), FL_03_dashboard_tv.png (Fill Level Inspection), PC_03_dashboard_tv_tray.png (Pack Count QC), PD_03_dashboard_tv.png (Parcel Dimensioning).

2. Masalah: "Masalah mutu di line baru ketahuan setelah produk keluar pabrik"
Empat kartu, satu per produk, dengan ikon dan warna aksen produknya:
- Produce Grading · lot campur warna terkirim ke pembeli; cek manual hanya sampel
- Fill Level Inspection · botol kurang isi lolos ke pasar; botol lebih isi = produk terbuang (giveaway)
- Pack Count QC · tray dan kardus kurang isi baru ketahuan setelah komplain
- Parcel Dimensioning · ukuran paket tidak diketahui; truk dan tagihan tidak optimal

3. Solusi: "Empat produk, satu cara kerja"
- Diagram alur 4 langkah: kamera di line (CCTV yang ada atau kamera industri) → edge AI box di pabrik (deteksi, hitung, ukur) → web app dan Dashboard TV (standar, laporan, bukti) → tindakan di line (sinyal reject ke PLC, hold, WhatsApp).
- Strip empat produk di bawahnya, masing-masing dengan warna aksen dan satu baris "untuk siapa".
- Teks kecil: "Berikut tur layar setiap produk. Setiap produk bisa dibeli sendiri, per line."

BAGIAN A · PRODUCE GRADING (slide 4–10)

4. PEMBUKA BAGIAN A · PRODUCE GRADING: "Grade warna setiap buah di line, sesuai standar USDA dan OECD, lengkap dengan bukti per lot." (PG_03_dashboard_tv_tomat.png kecil, dalam bingkai layar TV, di sisi kanan)
- Label kecil: "PRODUK 1/4". Latar warna aksen produk (#16A34A) dengan teks putih, atau latar terang dengan ikon warna aksen.
- Untuk: packing house buah dan sayur, eksportir, pemasok supermarket.
- Masalah: Warna dan kematangan buah dicek manual dengan sampel kecil; lot campur warna lolos ke pembeli.
- Masalah: Klaim dari pembeli atau importir sulit dijawab karena tidak ada data per lot.
- Masalah: Standar berbeda per pembeli (USDA, OECD, spec supermarket) dan sulit diterapkan konsisten tiap shift.
- Alur kerja (diagram 4 langkah kecil): kamera di atas conveyor → edge AI box membaca kelas warna setiap buah dan menghitungnya per line → web app menggabungkan per lot dan mencocokkan dengan standar → hold lot, sortir ulang, atau release, dengan bukti foto.

5. PRODUCE GRADING · FITUR 1/6 · RINGKASAN: "Setiap shift, mutu warna semua line terbaca di satu layar" (PG_01_ringkasan.png)
1) Buah di-grade hari ini, persentase di kelas warna utama, lot di-hold, dan out of grade (baris kartu atas).
2) Komposisi grade per line untuk tomat (kelas USDA) dan lemon (lot warna OECD), plus off-colour per jam terhadap limit lot 10% (grafik tengah).
3) Daftar lot shift ini dengan statusnya (Release, Hold, Mixed Color) dan cuplikan line yang sedang berjalan (baris bawah).
Manfaat untuk bisnis: lot bermasalah ketahuan sebelum naik truk, bukan setelah ditolak pembeli.
Dipakai oleh: QC Manager, Plant Manager.

6. PRODUCE GRADING · FITUR 2/6 · LIVE MONITORING: "Supervisor melihat setiap buah yang keluar dari kelasnya, dan langsung bertindak" (PG_02_live_monitoring.png)
1) Kamera dengan overlay AI: kelas warna per buah, nomor line, count gate (kamera besar kiri).
2) Lot berjalan: jumlah per kelas USDA dan off-colour 17% di atas limit 10%, plus foto buah off-colour per line (kolom kanan).
3) Tombol Hold lot, Sortir ulang di line T2, atau Release sebagai Mixed Color (kanan bawah).
Manfaat untuk bisnis: sortir ulang dilakukan saat buah masih di line, bukan di gudang.
Dipakai oleh: Line Supervisor.

7. PRODUCE GRADING · FITUR 3/6 · DASHBOARD TV: "Layar di line menunjukkan mutu lot saat itu juga" (PG_03_dashboard_tv_tomat.png utama, PG_04_dashboard_tv_lemon.png kecil)
1) Kamera live dengan AI: setiap tomat diberi kotak sesuai kelas warna USDA dan dihitung sekali di count gate (gambar kamera kiri atas).
2) KPI lot dan Grade Composition: 41 tomat, 83% Red, off-colour 17% di atas limit 10% → label Mixed Color atau sortir ulang 7 buah (kanan atas dan tengah).
3) Event Log berfoto, grafik per line, off-colour yang terus naik, dan lini masa (kanan bawah dan baris bawah). Screenshot kecil: tampilan lemon dengan bagan warna OECD derajat 1–10, berganti otomatis di TV yang sama.
Manfaat untuk bisnis: operator tidak perlu menebak; satu layar memberi tahu kapan harus sortir ulang.
Dipakai oleh: operator line, Line Supervisor.

8. PRODUCE GRADING · FITUR 4/6 · LAPORAN LOT: "Setiap lot punya keputusan, bukti, dan riwayat yang bisa ditunjukkan ke pembeli" (PG_05_laporan_lot.png)
1) Cek lot sesuai USDA 7 CFR 51.1861: off-colour 17% > limit 10% → Mixed Color, atau sortir ulang 7 buah agar bisa diberi label Red (kartu tengah atas).
2) Foto bukti buah off-colour dan sebaran warna setiap buah terhadap batas kelas USDA (baris tengah dan kiri bawah).
3) Riwayat lot (dibuka, alert, hold, sortir ulang, oleh siapa) dan ekspor sertifikat lot PDF untuk QA pembeli (kanan bawah dan tombol atas).
Manfaat untuk bisnis: klaim pembeli bisa dijawab dengan data per lot, bukan perkiraan.
Dipakai oleh: QC Manager, tim sales/ekspor.

9. PRODUCE GRADING · FITUR 5/6 · STANDAR GRADE: "Standar resmi dan spec pembeli, diatur sendiri oleh QC" (PG_06_standar_grade.png)
1) Daftar standar: kelas warna tomat USDA, bagan warna lemon OECD, dan spec pembeli (tabel kiri atas).
2) Batas tiap kelas, limit off-colour, tindakan otomatis jika limit terlewati, dan cek warna dengan kartu referensi tiap awal shift (panel kanan atas).
3) Standar diuji dulu di rekaman sebelum go-live; di PoC 75 dari 78 tomat sama dengan cek mata (kartu tengah dan bagan OECD di bawah).
Manfaat untuk bisnis: ganti pembeli atau pasar ekspor cukup ganti standar, bukan ganti sistem.
Dipakai oleh: QC Manager.

10. PRODUCE GRADING · FITUR 6/6 · KAMERA, ALERT & INTEGRASI: "Orang yang tepat tahu dalam hitungan detik, line bertindak otomatis" (PG_07_kamera_alert_integrasi.png)
1) Kamera per line dengan status dan hasil cek gambar (tabel kiri atas).
2) Aturan alert khusus grading (off-colour lot, hijau di lot, lemon derajat 10, kartu warna gagal) dan eskalasi (kiri tengah dan bawah).
3) Integrasi ke PLC sortir, ERP/sistem lot, WhatsApp, dan API, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: masalah tidak menunggu laporan akhir shift.
Dipakai oleh: Plant Admin, IT.

BAGIAN B · FILL LEVEL INSPECTION (slide 11–17)

11. PEMBUKA BAGIAN B · FILL LEVEL INSPECTION: "Level isi setiap botol terhadap target dan toleransi; underfill di-reject, overfill dihitung sebagai giveaway." (FL_03_dashboard_tv.png kecil, dalam bingkai layar TV, di sisi kanan)
- Label kecil: "PRODUK 2/4". Latar warna aksen produk (#2563EB) dengan teks putih, atau latar terang dengan ikon warna aksen.
- Untuk: pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol.
- Masalah: Botol kurang isi lolos ke pasar: risiko komplain dan masalah BDKT.
- Masalah: Botol lebih isi tidak terukur, padahal itu produk yang diberikan gratis (giveaway) setiap hari.
- Masalah: Cek manual hanya sampel per jam; nozzle yang bermasalah baru ketahuan belakangan.
- Alur kerja (diagram 4 langkah kecil): kamera samping dengan backlight di mesin pengisi → edge AI box mengukur level isi setiap frame dan mengubahnya jadi volume dari bentuk botol → web app menilai pass/reject per SKU → sinyal reject ke PLC dan laporan giveaway per nozzle.

12. FILL LEVEL INSPECTION · FITUR 1/6 · RINGKASAN: "Setiap botol dicek; underfill di-reject, overfill dihitung sebagai produk terbuang" (FL_01_ringkasan.png)
1) Botol diinspeksi, reject underfill, rata-rata overfill dalam mL, dan persentase dalam toleransi (baris kartu atas).
2) Rata-rata isi per nozzle terhadap target dan batas toleransi: nozzle 3 selalu kelebihan isi (grafik kiri).
3) Reject per jam dengan penyebabnya, reject terbaru, dan kamera live (kanan dan baris bawah).
Manfaat untuk bisnis: aman dari komplain isi kurang, dan giveaway per nozzle terukur sehingga bisa dikurangi.
Dipakai oleh: QC Manager, Production Manager.

13. FILL LEVEL INSPECTION · FITUR 2/6 · LIVE MONITORING: "Level isi terlihat langsung di layar, nozzle demi nozzle" (FL_02_live_monitoring.png)
1) Kamera dengan overlay AI: outline botol, garis target di leher botol, level isi dalam % dan mL (kamera besar kiri).
2) Siklus berjalan dan hasil terakhir per nozzle 1–8, dengan nozzle yang bermasalah ditandai (kolom kanan).
3) Tombol hentikan nozzle untuk dicek atau tandai reject manual (kanan bawah).
Manfaat untuk bisnis: supervisor tahu nozzle mana yang bermasalah tanpa menunggu sampel per jam.
Dipakai oleh: Line Supervisor.

14. FILL LEVEL INSPECTION · FITUR 3/6 · DASHBOARD TV: "Level isi diukur setiap frame, selama botol diisi" (FL_03_dashboard_tv.png)
1) Kamera live dengan AI: garis target dan level isi saat ini dalam % dan mL (gambar kamera kiri atas).
2) KPI dan fill curve: level isi, flow rate, waktu isi, sisa waktu ke target (kanan atas).
3) Aturan pass/reject per SKU dan "tinggi bukan volume": tinggi 74% = volume 67% (baris bawah). Catatan jujur: klip PoC berakhir di 67%, jadi belum ada keputusan pass/reject; angka mL memakai contoh SKU 500 mL.
Manfaat untuk bisnis: keputusan isi berdasarkan volume, bukan perkiraan dari tinggi cairan.
Dipakai oleh: operator filler, QC.

15. FILL LEVEL INSPECTION · FITUR 4/6 · REJECT & GIVEAWAY: "Setiap reject punya bukti; setiap mL lebih dihitung" (FL_04_reject_giveaway.png)
1) Reject underfill terbaru per nozzle, dengan status dikonfirmasi QC atau alarm palsu (tabel kiri atas).
2) Giveaway per nozzle terhadap target dan batas toleransi, dengan saran tindakan (grafik kanan atas).
3) Bukti reject (gambar kamera, level saat nozzle berhenti, sinyal ke PLC) dan reject per jam (baris bawah).
Manfaat untuk bisnis: tim teknik tahu nozzle mana yang perlu disetel, berdasarkan data, bukan perasaan.
Dipakai oleh: QC Manager, Maintenance.

16. FILL LEVEL INSPECTION · FITUR 5/6 · SPESIFIKASI SKU: "Target, toleransi, dan tindakan diatur per SKU" (FL_05_spesifikasi_sku.png)
1) Daftar SKU dan aturan isi: target, toleransi 98–102%, reject di bawah 490 mL lewat sinyal PLC dalam 0,5 detik (kiri dan tengah atas).
2) Profil botol dari 3 botol kosong agar tinggi cairan bisa diubah jadi volume; toleransi disesuaikan dengan BDKT dan spec pelanggan (kanan atas).
3) Giveaway per minggu turun setelah garis target dipindah, checklist sebelum go-live, dan riwayat perubahan (baris bawah).
Manfaat untuk bisnis: aturan mutu dan bukti perubahannya tersimpan rapi, siap untuk audit.
Dipakai oleh: QC Manager.

17. FILL LEVEL INSPECTION · FITUR 6/6 · KAMERA, ALERT & INTEGRASI: "Reject langsung ke PLC, alert langsung ke orang yang tepat" (FL_06_kamera_alert_integrasi.png)
1) Kamera per mesin pengisi dengan status dan hasil cek gambar, termasuk kamera yang perlu dicek (tabel kiri atas).
2) Aturan alert khusus pengisian (underfill, reject berulang di satu nozzle, overfill beruntun, kamera silau) dan eskalasi (kiri tengah dan bawah).
3) Integrasi PLC/rejector, check weigher, MES, WhatsApp, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: line bertindak otomatis, dan masalah nozzle tidak menunggu akhir shift.
Dipakai oleh: Plant Admin, IT.

BAGIAN C · PACK COUNT QC (slide 18–24)

18. PEMBUKA BAGIAN C · PACK COUNT QC: "Jumlah isi setiap tray dan kardus sebelum disegel, lengkap dengan slot yang kosong dan penyebabnya." (PC_03_dashboard_tv_tray.png kecil, dalam bingkai layar TV, di sisi kanan)
- Label kecil: "PRODUK 3/4". Latar warna aksen produk (#D97706) dengan teks putih, atau latar terang dengan ikon warna aksen.
- Untuk: pabrik makanan dan minuman kemasan, FMCG, co-packer.
- Masalah: Tray atau kardus kurang isi baru ketahuan setelah ada komplain dari distributor atau konsumen.
- Masalah: Cek manual hanya sampel; kemasan yang sudah disegel sulit dibuka ulang.
- Masalah: Penyebab kekurangan (feeder kosong, lane filler, robot) tidak tercatat, jadi masalah berulang.
- Alur kerja (diagram 4 langkah kecil): kamera di atas ujung line atau packing station → edge AI box menghitung isi setiap tray/kardus per slot → web app menilai lengkap atau kurang sebelum disegel → hold/divert ke rework, alert, dan penyebabnya dicatat.

19. PACK COUNT QC · FITUR 1/6 · RINGKASAN: "Tray dan kardus kurang isi ditahan sebelum disegel" (PC_01_ringkasan.png)
1) Pack diinspeksi, short pack tertangkap, item kurang, dan feeder gap sebagai penyebab (baris kartu atas).
2) Short pack per jam dan slot yang paling sering kosong minggu ini (grafik kiri dan heatmap kanan).
3) Reject & kejadian terbaru berfoto dan dua kamera live (baris bawah).
Manfaat untuk bisnis: komplain "isi kurang" dicegah, dan penyebabnya ketahuan.
Dipakai oleh: QC Manager, Line Supervisor.

20. PACK COUNT QC · FITUR 2/6 · LIVE MONITORING: "Setiap tray dan kardus terlihat dihitung, langsung di layar" (PC_02_live_monitoring.png)
1) Kamera dengan overlay AI: jumlah isi, slot kosong dilingkari merah, tray ditandai SHORT (kamera besar kiri).
2) Tray terakhir dan alert terbaru dengan tombol Konfirmasi & reject atau Alarm palsu (kolom kanan).
3) Kardus di packing station, kecepatan robot, dan status feeder (kanan bawah).
Manfaat untuk bisnis: supervisor bertindak sebelum kemasan disegel, bukan setelah komplain.
Dipakai oleh: Line Supervisor.

21. PACK COUNT QC · FITUR 3/6 · DASHBOARD TV: "Setiap tray dihitung, setiap slot kosong ditandai" (PC_03_dashboard_tv_tray.png utama, PC_04_dashboard_tv_packing.png kecil)
1) Kamera live dengan AI: slot kosong dilingkari merah dan tray ditandai SHORT (gambar kamera kiri atas).
2) Posisi kaleng yang kosong dan apakah berulang, menunjuk ke lane filler (kanan tengah).
3) Tray terakhir dengan pass/reject, tray diinspeksi kumulatif, dan Event Log berfoto (baris bawah). Screenshot kecil: robot packing station dengan peta slot kardus dan root cause feeder gap → empty pick → kardus kurang isi.
Manfaat untuk bisnis: bukan hanya "kurang", tetapi juga "kurang di slot mana dan kenapa".
Dipakai oleh: operator line, Line Supervisor.

22. PACK COUNT QC · FITUR 4/6 · DETAIL REJECT: "Setiap reject punya bukti, penyebab, dan tindakan perbaikan" (PC_05_detail_reject.png)
1) Peta slot kardus: B2 dan C5 kosong, 18/20, dengan root cause feeder gap (kiri atas).
2) Foto bukti dan klip 10 detik sebelum–sesudah, bisa diekspor ke PDF (tengah).
3) Timeline dari feeder gap → empty pick → kardus di-hold → WhatsApp → rework 20/20, plus corrective action (kanan dan kiri bawah).
Manfaat untuk bisnis: investigasi selesai dalam hitungan menit; bukti siap untuk pelanggan atau audit.
Dipakai oleh: Line Supervisor, QC Manager, Maintenance.

23. PACK COUNT QC · FITUR 5/6 · SPESIFIKASI KEMASAN: "Layout slot dan aturan isi diatur per SKU" (PC_06_spesifikasi_kemasan.png)
1) Daftar kemasan dengan layout slot (tray 10, kardus 20, dan lain-lain) (tabel kiri).
2) Layout slot dan tindakan jika isi kurang, feeder gap, atau empty pick (panel kanan).
3) Uji di rekaman sebelum go-live (PoC: 3/3 kardus, 7/7 tray, 2/2 empty pick) dan hasil per kemasan minggu ini (baris bawah).
Manfaat untuk bisnis: ganti SKU atau kemasan cukup ganti layout, bukan ganti sistem.
Dipakai oleh: QC Manager.

24. PACK COUNT QC · FITUR 6/6 · KAMERA, ALERT & INTEGRASI: "Kemasan kurang isi dialihkan otomatis, orang yang tepat langsung tahu" (PC_07_kamera_alert_integrasi.png)
1) Kamera per line dan station dengan status dan hasil cek gambar (tabel kiri atas).
2) Aturan alert khusus kemasan (kurang isi, feeder gap berulang, slot yang sama kosong, empty pick) dan eskalasi (kiri tengah dan bawah).
3) Integrasi PLC/diverter, MES, robot controller, WhatsApp, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: line bertindak otomatis, dan Maintenance tahu penyebabnya lebih awal.
Dipakai oleh: Plant Admin, IT.

BAGIAN D · PARCEL DIMENSIONING (slide 25–31)

25. PEMBUKA BAGIAN D · PARCEL DIMENSIONING: "Panjang × lebar × tinggi dan volume setiap paket di belt, untuk muat truk dan tagihan berat volumetrik." (PD_03_dashboard_tv.png kecil, dalam bingkai layar TV, di sisi kanan)
- Label kecil: "PRODUK 4/4". Latar warna aksen produk (#7C3AED) dengan teks putih, atau latar terang dengan ikon warna aksen.
- Untuk: gudang distribusi, 3PL, e-commerce fulfilment, ekspedisi.
- Masalah: Ukuran paket diukur manual dengan meteran, atau tidak diukur sama sekali.
- Masalah: Tagihan hanya berdasarkan berat timbangan, padahal paket ringan tapi besar memakan ruang truk.
- Masalah: Rencana muat truk berdasarkan perkiraan, sehingga truk berangkat setengah kosong atau kurang.
- Alur kerja (diagram 4 langkah kecil): kamera di atas belt bongkar/muat → edge AI box mengukur P × L × T setiap paket dan menghitungnya di count line → web app mengelompokkan kelas ukuran dan menghitung berat volumetrik → data ke WMS/TMS dan sistem invoice.

26. PARCEL DIMENSIONING · FITUR 1/6 · RINGKASAN: "Ukuran dan volume setiap paket, tanpa meteran" (PD_01_ringkasan.png)
1) Paket terukur hari ini, volume, berat volumetrik, dan paket yang perlu manual check (baris kartu atas).
2) Log paket: P × L × T, volume, berat volumetrik (P × L × T ÷ 6000), kelas S/M/L (tabel kiri).
3) Komposisi ukuran, kamera live, dan volume per jam untuk merencanakan truk lebih awal (kanan dan baris bawah).
Manfaat untuk bisnis: data ukuran setiap paket tanpa menambah orang atau memperlambat belt.
Dipakai oleh: Warehouse/Logistics Manager.

27. PARCEL DIMENSIONING · FITUR 2/6 · LIVE MONITORING: "Setiap paket terlihat diukur saat lewat" (PD_02_live_monitoring.png)
1) Kamera dengan overlay AI: kotak paket, P × L × T, kelas ukuran, dan count line (kamera besar kiri).
2) Paket terakhir dengan foto dan ukurannya (kanan atas).
3) Paket yang dekat batas kelas masuk manual check, dengan tombol Konfirmasi atau Ubah kelas (kanan bawah).
Manfaat untuk bisnis: ukuran yang meragukan tidak ditebak, tetapi dikonfirmasi orang.
Dipakai oleh: supervisor dock, operator belt.

28. PARCEL DIMENSIONING · FITUR 3/6 · DASHBOARD TV: "Satu kamera mengukur P × L × T paket di belt" (PD_03_dashboard_tv.png)
1) Kamera live dengan AI: setiap paket diberi kotak sesuai kelas ukuran dan dihitung di count line (gambar kamera kiri atas).
2) Tabel paket terukur: P × L × T, volume, berat volumetrik, kelas; paket dekat batas kelas masuk manual check (kanan tengah).
3) Komposisi ukuran S/M/L dan volume kumulatif, dengan uji vs hitungan manual (baris bawah).
Manfaat untuk bisnis: ukuran yang konsisten, bisa dicek ulang dari fotonya.
Dipakai oleh: operator belt, supervisor logistik.

29. PARCEL DIMENSIONING · FITUR 4/6 · MUAT & TAGIHAN: "Volume terukur dipakai untuk muat truk dan tagihan" (PD_04_muat_tagihan.png)
1) Isi tiap truk dari volume terukur: selesai muat, sedang muat, terjadwal (kiri atas).
2) Berat volumetrik vs berat aktual per pelanggan; pelanggan dengan paket ringan tapi besar ditagih berdasarkan volume (kanan atas).
3) Antrean manual check, dasar tagihan per pelanggan, volume per tujuan, dan selisih berat 7 hari, siap dikirim ke TMS/WMS (baris tengah dan bawah).
Manfaat untuk bisnis: truk terisi lebih penuh dan tagihan sesuai ruang yang benar-benar dipakai.
Dipakai oleh: Logistics Manager, Finance.

30. PARCEL DIMENSIONING · FITUR 5/6 · KELAS UKURAN & TAGIHAN: "Kelas ukuran, rumus tagihan, dan kalibrasi diatur sendiri" (PD_05_kelas_ukuran.png)
1) Batas kelas S/M/L dan kapan paket masuk manual check (kiri atas).
2) Rumus berat volumetrik (P × L × T ÷ 6000) yang bisa diubah per pelanggan, dan ke mana datanya dikirim (kanan atas).
3) Kalibrasi kamera dengan karton referensi (PoC: 340,5 mm vs 340 mm) dan uji di rekaman sebelum go-live (baris bawah).
Manfaat untuk bisnis: aturan tagihan transparan dan bisa ditunjukkan ke pelanggan.
Dipakai oleh: Logistics Manager, Finance.

31. PARCEL DIMENSIONING · FITUR 6/6 · KAMERA, ALERT & INTEGRASI: "Data ukuran langsung masuk ke WMS, TMS, dan invoice" (PD_06_kamera_alert_integrasi.png)
1) Kamera per belt dan dock dengan status dan hasil cek gambar (tabel kiri atas).
2) Aturan alert khusus paket (ukuran dekat batas kelas, paket tidak terukur, truk hampir penuh, belt berhenti) dan eskalasi (kiri tengah dan bawah).
3) Integrasi WMS, TMS, sistem invoice, API, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: tidak ada input ulang data ukuran; semua sistem memakai angka yang sama.
Dipakai oleh: Plant Admin, IT.

PENUTUP

32. Ringkasan: "Empat produk, satu tujuan: masalah mutu ketahuan di line, bukan di tangan pelanggan" (latar terang)
Tabel atau 4 kartu, satu per produk, kolom Masalah → Hasil:
- Produce Grading: lot campur warna terkirim ke pembeli; cek manual hanya sampel → lot bermasalah ditahan sebelum dikirim, dengan bukti per lot untuk pembeli.
- Fill Level Inspection: botol kurang isi lolos ke pasar; botol lebih isi = produk terbuang (giveaway) → setiap underfill di-reject otomatis; giveaway per nozzle terukur dan bisa dikurangi.
- Pack Count QC: tray dan kardus kurang isi baru ketahuan setelah komplain → kemasan kurang isi ditahan sebelum disegel, lengkap dengan slot dan penyebabnya.
- Parcel Dimensioning: ukuran paket tidak diketahui; truk dan tagihan tidak optimal → ukuran setiap paket tanpa meteran; truk lebih penuh dan tagihan sesuai volume.
Catatan kaki: "Besaran manfaat dihitung bersama klien dari data pilot 30 hari."

33. Bukti PoC: "Inti teknologi keempat produk sudah diuji"
Tabel 4 baris (satu per produk) dengan kolom Yang diuji · Hasil:
- Produce Grading: 41 tomat di 4 line, kelas warna USDA (7 CFR 51.1860): 75 dari 78 sama dengan cek mata secara blind, sisanya beda 1 kelas. 87 lemon di 2 chain, bagan warna OECD derajat 1–10: 18 dari 24 dalam ±1 derajat dari cek mata secara blind. Batas kelas tomat diambil dari data colorimeter yang dipublikasikan, bukan disetel ke klip ini.
- Fill Level Inspection: Level isi diukur setiap frame pada rekaman nyata mesin pengisi, dan bentuk botol diukur sehingga tinggi diubah menjadi volume. Klip PoC berakhir di 67% saat botol masih diisi, jadi belum ada keputusan pass/reject; angka mL memakai contoh SKU 500 mL.
- Pack Count QC: Tray 10 kaleng (simulasi 3D dengan data kebenaran): 7 dari 7 tray benar, 181 dari 181 pembacaan benar. Kardus 20 item di robot packing station: 3 dari 3 kardus benar, 2 dari 2 empty pick ditemukan, feeder gap terdeteksi lebih dulu.
- Parcel Dimensioning: 8 paket di belt bongkar truk (rekaman nyata): 8 dari 8 terhitung, sama dengan hitungan manual. Karton uji yang tidak dipakai untuk kalibrasi terbaca 340,5 mm, aslinya 340 mm. Laju per jam di layar adalah perkiraan dari klip 17 detik, bukan data satu shift.
Kotak "Yang dibuktikan saat pilot":
- Produce Grading: kecocokan kelas warna dan status lot dengan cek blind oleh QC pabrik; jumlah lot yang ditahan sebelum dikirim.
- Fill Level Inspection: setiap underfill ter-reject; level isi per nozzle dibandingkan dengan check weigher; giveaway per nozzle.
- Pack Count QC: setiap short pack tertahan sebelum disegel, lengkap dengan slot yang kosong; penyebab yang berulang (feeder, lane).
- Parcel Dimensioning: P × L × T dalam ±1 cm dari meteran pada 100 paket; isi truk sebelum vs sesudah.
Catatan kaki: "Laju per menit/jam di video adalah perkiraan dari klip beberapa detik, bukan data satu shift."

34. Langkah berikutnya: "Mulai dari satu produk di satu line" (latar navy)
- Langkah: line survey 1 minggu → pilot 30 hari → go-live 2 minggu → line atau produk berikutnya.
- Yang disiapkan pabrik: titik dudukan dan listrik di titik inspeksi, jaringan ke edge AI box, satu orang QC untuk cek blind, standar atau spec yang dipakai.
- Yang kami siapkan: kamera, lampu, dan edge AI box terpasang dan tersetel; setting standar, limit, dan aturan alert; laporan akurasi di akhir pilot.
- Kalimat penutup tebal: "Harga per line, dihitung setelah line survey."

ATURAN
- Tidak ada angka uang: jangan tampilkan rupiah, harga, ROI, persentase penghematan, atau proyeksi pendapatan.
- Jangan menambah statistik pasar, kutipan, nama/logo klien, atau klaim lain di luar prompt ini.
- Angka di layar mockup adalah ilustrasi, kecuali yang bertanda PoC. Jangan mengutip angka ilustrasi sebagai hasil.
- Format angka Indonesia (340,5 mm; 41.860).
- Bahasa Indonesia sehari-hari; istilah teknis dan bisnis boleh dalam bahasa Inggris selama umum dipakai di pabrik. Hindari kata yang jarang dipakai pemilik bisnis.
- Tambahkan catatan pembicara 2–3 kalimat untuk setiap slide; di slide tur, isinya cara mendemokan layar itu dalam satu menit.
```

## 6. Tambahan: 1 slide arsitektur sistem (slide 34, deck menjadi 35 slide)

Untuk deck yang sudah jadi di Claude Design, di proyek yang sama. Lampirkan `arsitektur/ARC_arsitektur_sistem.png`.
Gambarnya diambil dari diagram draw.io `architecture_multi_pabrik.drawio` (di root repo), tanpa baris judulnya,
karena judul ditulis di slide. Tempel prompt di bawah (juga ada di
`claude_design_prompts/tahap_6_tambah_arsitektur.txt`), lalu kirim.

```text
Tambahkan 1 slide arsitektur ke deck Factory Vision yang sudah ada. Sisipkan setelah slide 33 (Bukti PoC) dan sebelum slide "Langkah berikutnya", jadi slide arsitektur menjadi slide 34 dan slide "Langkah berikutnya" pindah ke nomor 35. Total deck menjadi 35 slide. Jangan ubah isi slide lain.

Terlampir 1 gambar: ARC_arsitektur_sistem.png. Gambar ini sudah berisi seluruh penjelasan, jadi slide ini hanya berisi judul dan gambar, tanpa poin atau kartu tambahan.

34. ARSITEKTUR: "Setiap pabrik mandiri, dipantau dari mana saja" (ARC_arsitektur_sistem.png)
- Label kecil di atas judul: "ARSITEKTUR SISTEM", warna aksen biru #2563EB.
- Judul: Setiap pabrik mandiri, dipantau dari mana saja
- Subjudul satu baris di bawah judul: AI, rekaman, dan data diproses di server tiap pabrik. Dashboard bisa dibuka dari kantor, rumah, atau HP lewat jaringan privat yang aman.
- Gambar sebesar mungkin di bawah subjudul, di tengah, memenuhi sisa tinggi slide. Jangan crop, jangan ubah isi gambar, dan jaga rasio aslinya. Beri bingkai tipis abu (#E2E8F0) dengan sudut membulat, sama seperti screenshot di slide lain.
- Gaya sama dengan slide penutup: latar terang #F3F5F8, teks #0F172A dan #475569, huruf Inter. Posisi judul sama dengan slide lain.
- Catatan kaki kecil: "Diagram lengkap (file draw.io) tersedia untuk tim IT."

Setelah itu ubah nomor slide "Langkah berikutnya" menjadi 35. Periksa judul, nomor slide, dan tidak ada teks terpotong, lalu ekspor ulang ke PPTX.
```
