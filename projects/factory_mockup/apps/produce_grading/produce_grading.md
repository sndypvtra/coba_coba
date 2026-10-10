# Prompt Claude Design: Produce Grading

Deck produk **Produce Grading**: satu web app, satu cerita, untuk packing house buah dan sayur, eksportir, pemasok supermarket. Deck ini berdiri sendiri, dan bisa
digabung dengan deck produk lain (Warehouse Live Ops dan produk pabrik lainnya) karena gayanya sama.

**Grade warna setiap buah di line, sesuai standar USDA dan OECD, lengkap dengan bukti per lot.**

## 1. Tentang gambar mockup

- Folder `pages/` berisi 7 gambar PNG **3840 × 2160 (4K, 16:9)**, satu gambar per layar web app.
- Templatenya sama dengan mockup warehouse: setiap layar adalah web app atau Dashboard TV milik Produce Grading sendiri,
  dengan menu, KPI, grafik, Event Log, dan lini masa sendiri. Dari PoC hanya diambil **gambar kamera dengan overlay AI**
  yang ditempel di dalam layar, plus angka hasil ukurnya.
- Bahasa di layar: bahasa Indonesia dengan istilah teknis Inggris yang umum di pabrik. Format angka Indonesia.
- Label kecil yang tergambar di dalam gambar kamera (misalnya "Count gate") adalah overlay AI dari PoC dan tetap seperti di videonya.
- Setiap gambar mencantumkan "Mockup konsep · angka ilustrasi" di pojok kanan bawah. Hanya angka bertanda **PoC**
  dan gambar kamera yang hasil uji sungguhan. Tidak ada angka rupiah.

## 2. Sudut pandang pembeli

Bayangkan Anda pemilik pabrik yang sedang memilih sistem video analytics. Setiap slide harus menjawab salah satu dari:
masalah saya yang mana yang selesai; layar apa yang dipakai tim saya; apa yang terjadi di line saat ada masalah;
standarnya siapa dan siapa yang mengatur; apa buktinya; apakah cocok dengan kamera dan sistem saya; bagaimana mulainya.

## 3. Daftar slide (12 slide)

| # | Slide | Gambar (folder `pages/`) | Yang ditonjolkan |
|---|---|---|---|
| 1 | Sampul | `03_dashboard_tv_tomat.png` | Produce Grading · Grade warna setiap buah di line, sesuai standar USDA dan OECD, lengkap dengan bukti per lot. |
| 2 | Masalah | – | 4 masalah di line hari ini |
| 3 | Solusi & cara kerja | – | alur kamera → edge AI box → web app → tindakan di line |
| 4 | Fitur 1/6 · Ringkasan | `01_ringkasan.png` | Setiap shift, mutu warna semua line terbaca di satu layar |
| 5 | Fitur 2/6 · Live Monitoring | `02_live_monitoring.png` | Supervisor melihat setiap buah yang keluar dari kelasnya, dan langsung bertindak |
| 6 | Fitur 3/6 · Dashboard TV | `03_dashboard_tv_tomat.png` + `04_dashboard_tv_lemon.png` kecil | Layar di line menunjukkan mutu lot saat itu juga |
| 7 | Fitur 4/6 · Laporan Lot | `05_laporan_lot.png` | Setiap lot punya keputusan, bukti, dan riwayat yang bisa ditunjukkan ke pembeli |
| 8 | Fitur 5/6 · Standar Grade | `06_standar_grade.png` | Standar resmi dan spec pembeli, diatur sendiri oleh QC |
| 9 | Fitur 6/6 · Kamera, Alert & Integrasi | `07_kamera_alert_integrasi.png` | Orang yang tepat tahu dalam hitungan detik, line bertindak otomatis |
| 10 | Ringkasan manfaat | – | 4 manfaat bisnis dan fitur yang mewujudkannya |
| 11 | Bukti PoC | – | hasil terukur dan batasannya |
| 12 | Pilot & langkah berikutnya | – | pilot 30 hari, yang disiapkan, keputusan |

## 4. Cara pakai

1. Buka Claude Design dan mulai proyek presentasi baru (atau buka deck yang akan digabung).
2. Lampirkan 7 gambar dari folder `pages/`: `01_ringkasan.png`, `02_live_monitoring.png`, `03_dashboard_tv_tomat.png`, `04_dashboard_tv_lemon.png`, `05_laporan_lot.png`, `06_standar_grade.png`, `07_kamera_alert_integrasi.png`.
3. Tempel prompt di bagian 5. Isi dulu `[Nama tim]` dan `[Tanggal]`.
4. Setelah semua slide jadi, minta ekspor ke PPTX.

## 5. Prompt (tempel ke kolom chat Claude Design)

```text
Buatkan 12 slide presentasi 16:9 berbahasa Indonesia untuk produk "Produce Grading", siap diekspor ke PowerPoint. Tujuan utamanya: calon pembeli MELIHAT web app-nya bekerja, layar demi layar, dan memahami manfaat bisnis setiap layar. Jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC) Produce Grading: Grade warna setiap buah di line, sesuai standar USDA dan OECD, lengkap dengan bukti per lot. Penontonnya packing house buah dan sayur, eksportir, pemasok supermarket yang sedang memilih sistem video analytics. Mereka bertanya: "Masalah saya yang mana yang selesai, layar apa yang dipakai tim saya, apa yang terjadi di line saat ada masalah, dan apa buktinya?"

GAYA VISUAL
- Sama dengan deck "Warehouse Live Ops": latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, huruf Inter. Warna aksen produk ini: #16A34A (untuk label kecil, ikon, dan garis penanda). Slide 1 dan slide terakhir berlatar navy #0B1220.
- Judul setiap slide berupa kalimat kesimpulan dari sudut pandang pembeli.
- Slide tur produk: screenshot adalah bintangnya. Screenshot utama mengisi minimal 60% lebar slide, utuh dalam bingkai browser (sudut membulat, bayangan halus), jangan dipotong. Teks pendamping di kolom samping (maksimal 35% lebar). Selang-seling posisi screenshot kiri dan kanan.
- Screenshot Dashboard TV (latar gelap) ditaruh dalam bingkai layar TV (bezel tipis, sudut membulat).
- Pada setiap screenshot, pasang 3 penanda bernomor (lingkaran kecil warna aksen) di bagian layar yang dijelaskan, sesuai petunjuk letak dalam kurung di setiap poin.
- Jika ada screenshot kedua, tampilkan lebih kecil (±30% lebar), bertumpuk di pojok screenshot utama dengan bayangan.
- Kolom teks tiap slide tur: label kecil "FITUR n/6 · NAMA LAYAR", judul, 3 poin bernomor, satu baris tebal "Manfaat untuk bisnis", dan baris kecil "Dipakai oleh".
- Catatan kaki kecil di slide yang memuat gambar kamera: "Video: Pexels (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.

GAMBAR TERLAMPIR
01_ringkasan.png · 02_live_monitoring.png · 03_dashboard_tv_tomat.png · 04_dashboard_tv_lemon.png · 05_laporan_lot.png · 06_standar_grade.png · 07_kamera_alert_integrasi.png
Jika ada yang tidak terlampir, pakai bingkai placeholder berlabel nama filenya.

PEMBUKA

1. Sampul
- Judul: Produce Grading
- Subjudul: Grade warna setiap buah di line, sesuai standar USDA dan OECD, lengkap dengan bukti per lot.
- Teks kecil: Konsep produk · [Nama tim] · [Tanggal]
- Visual: 03_dashboard_tv_tomat.png besar dalam bingkai layar TV, sedikit terpotong di sisi kanan.

2. Masalah: "Masalah yang terjadi di line setiap hari"
Empat kartu dengan ikon:
- Warna dan kematangan buah dicek manual dengan sampel kecil; lot campur warna lolos ke pembeli.
- Klaim dari pembeli atau importir sulit dijawab karena tidak ada data per lot.
- Standar berbeda per pembeli (USDA, OECD, spec supermarket) dan sulit diterapkan konsisten tiap shift.
- Sortir ulang baru dilakukan di gudang, setelah buah sudah dikemas.

3. Solusi & cara kerja: "Dari kamera di line sampai tindakan di line"
- Diagram alur 4 langkah: kamera di atas conveyor → edge AI box membaca kelas warna setiap buah dan menghitungnya per line → web app menggabungkan per lot dan mencocokkan dengan standar → hold lot, sortir ulang, atau release, dengan bukti foto.
- Strip "Dipakai oleh": QC Manager, Line Supervisor, operator line, tim sales/ekspor.
- Teks kecil: "Berikut tur 6 layar utama Produce Grading."

TUR PRODUK (satu layar per slide)

4. FITUR 1/6 · RINGKASAN: "Setiap shift, mutu warna semua line terbaca di satu layar" (01_ringkasan.png)
1) Buah di-grade hari ini, persentase di kelas warna utama, lot di-hold, dan out of grade (baris kartu atas).
2) Komposisi grade per line untuk tomat (kelas USDA) dan lemon (lot warna OECD), plus off-colour per jam terhadap limit lot 10% (grafik tengah).
3) Daftar lot shift ini dengan statusnya (Release, Hold, Mixed Color) dan cuplikan line yang sedang berjalan (baris bawah).
Manfaat untuk bisnis: lot bermasalah ketahuan sebelum naik truk, bukan setelah ditolak pembeli.
Dipakai oleh: QC Manager, Plant Manager.

5. FITUR 2/6 · LIVE MONITORING: "Supervisor melihat setiap buah yang keluar dari kelasnya, dan langsung bertindak" (02_live_monitoring.png)
1) Kamera dengan overlay AI: kelas warna per buah, nomor line, count gate (kamera besar kiri).
2) Lot berjalan: jumlah per kelas USDA dan off-colour 17% di atas limit 10%, plus foto buah off-colour per line (kolom kanan).
3) Tombol Hold lot, Sortir ulang di line T2, atau Release sebagai Mixed Color (kanan bawah).
Manfaat untuk bisnis: sortir ulang dilakukan saat buah masih di line, bukan di gudang.
Dipakai oleh: Line Supervisor.

6. FITUR 3/6 · DASHBOARD TV: "Layar di line menunjukkan mutu lot saat itu juga" (03_dashboard_tv_tomat.png utama, 04_dashboard_tv_lemon.png kecil)
1) Kamera live dengan AI: setiap tomat diberi kotak sesuai kelas warna USDA dan dihitung sekali di count gate (gambar kamera kiri atas).
2) KPI lot dan Grade Composition: 41 tomat, 83% Red, off-colour 17% di atas limit 10% → label Mixed Color atau sortir ulang 7 buah (kanan atas dan tengah).
3) Event Log berfoto, grafik per line, off-colour yang terus naik, dan lini masa (kanan bawah dan baris bawah). Screenshot kecil: tampilan lemon dengan bagan warna OECD derajat 1–10, berganti otomatis di TV yang sama.
Manfaat untuk bisnis: operator tidak perlu menebak; satu layar memberi tahu kapan harus sortir ulang.
Dipakai oleh: operator line, Line Supervisor.

7. FITUR 4/6 · LAPORAN LOT: "Setiap lot punya keputusan, bukti, dan riwayat yang bisa ditunjukkan ke pembeli" (05_laporan_lot.png)
1) Cek lot sesuai USDA 7 CFR 51.1861: off-colour 17% > limit 10% → Mixed Color, atau sortir ulang 7 buah agar bisa diberi label Red (kartu tengah atas).
2) Foto bukti buah off-colour dan sebaran warna setiap buah terhadap batas kelas USDA (baris tengah dan kiri bawah).
3) Riwayat lot (dibuka, alert, hold, sortir ulang, oleh siapa) dan ekspor sertifikat lot PDF untuk QA pembeli (kanan bawah dan tombol atas).
Manfaat untuk bisnis: klaim pembeli bisa dijawab dengan data per lot, bukan perkiraan.
Dipakai oleh: QC Manager, tim sales/ekspor.

8. FITUR 5/6 · STANDAR GRADE: "Standar resmi dan spec pembeli, diatur sendiri oleh QC" (06_standar_grade.png)
1) Daftar standar: kelas warna tomat USDA, bagan warna lemon OECD, dan spec pembeli (tabel kiri atas).
2) Batas tiap kelas, limit off-colour, tindakan otomatis jika limit terlewati, dan cek warna dengan kartu referensi tiap awal shift (panel kanan atas).
3) Standar diuji dulu di rekaman sebelum go-live; di PoC 75 dari 78 tomat sama dengan cek mata (kartu tengah dan bagan OECD di bawah).
Manfaat untuk bisnis: ganti pembeli atau pasar ekspor cukup ganti standar, bukan ganti sistem.
Dipakai oleh: QC Manager.

9. FITUR 6/6 · KAMERA, ALERT & INTEGRASI: "Orang yang tepat tahu dalam hitungan detik, line bertindak otomatis" (07_kamera_alert_integrasi.png)
1) Kamera per line dengan status dan hasil cek gambar (tabel kiri atas).
2) Aturan alert khusus grading (off-colour lot, hijau di lot, lemon derajat 10, kartu warna gagal) dan eskalasi (kiri tengah dan bawah).
3) Integrasi ke PLC sortir, ERP/sistem lot, WhatsApp, dan API, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: masalah tidak menunggu laporan akhir shift.
Dipakai oleh: Plant Admin, IT.

PENUTUP

10. Ringkasan manfaat: "Satu sistem, empat manfaat bisnis"
Grid 2×2, tiap kartu berisi manfaat dan layar yang mewujudkannya: lebih sedikit komplain dan reject (Ringkasan, Live Monitoring); bukti untuk setiap keputusan (laporan, detail, foto bukti); standar diatur sendiri (Standar Grade); tersambung ke line dan sistem yang ada (Kamera, Alert & Integrasi).
Catatan kaki: "Besaran manfaat dihitung bersama klien dari data pilot 30 hari."

11. Bukti PoC: "Inti teknologinya sudah diuji"
- 41 tomat di 4 line, kelas warna USDA (7 CFR 51.1860): 75 dari 78 sama dengan cek mata secara blind, sisanya beda 1 kelas.
- 87 lemon di 2 chain, bagan warna OECD derajat 1–10: 18 dari 24 dalam ±1 derajat dari cek mata secara blind.
- Batas kelas tomat diambil dari data colorimeter yang dipublikasikan, bukan disetel ke klip ini.
- Yang dibuktikan saat pilot: lot dengan kamera dan pencahayaan pabrik sendiri, dicek blind oleh QC pabrik.

12. Langkah berikutnya: "Mulai dengan pilot 30 hari di satu line"
- Yang disiapkan pabrik: titik dudukan dan listrik di titik inspeksi, jaringan ke edge AI box, satu orang QC untuk cek blind, standar atau spec yang dipakai.
- Yang kami siapkan: kamera, lampu, dan edge AI box terpasang dan tersetel; setting standar, limit, dan aturan alert; laporan akurasi di akhir pilot.
- Yang diukur saat pilot: kecocokan kelas warna dan status lot dengan cek blind oleh QC pabrik; jumlah lot yang ditahan sebelum dikirim.
- Langkah: line survey 1 minggu → pilot 30 hari → go-live 2 minggu → line berikutnya.
- Kalimat penutup tebal: "Harga per line, dihitung setelah line survey."

ATURAN
- Tidak ada angka uang: jangan tampilkan rupiah, harga, ROI, persentase penghematan, atau proyeksi pendapatan.
- Jangan menambah statistik pasar, kutipan, nama/logo klien, atau klaim lain di luar prompt ini.
- Angka di layar mockup adalah ilustrasi, kecuali yang bertanda PoC. Jangan mengutip angka ilustrasi sebagai hasil.
- Format angka Indonesia (340,5 mm; 41.860).
- Bahasa Indonesia sehari-hari; istilah teknis dan bisnis boleh dalam bahasa Inggris selama umum dipakai di pabrik. Hindari kata yang jarang dipakai pemilik bisnis.
- Tambahkan catatan pembicara 2–3 kalimat untuk setiap slide; di slide tur, isinya cara mendemokan layar itu dalam satu menit.
```

## 6. Pegangan tanya jawab

| Pertanyaan | Jawaban singkat |
|---|---|
| Apa bedanya dengan mesin sortir optik? | Mesin sortir memutuskan per buah. Produce Grading membaca setiap buah, menggabungkannya per lot, dan mencocokkannya dengan standar pembeli, lengkap dengan foto bukti. Keduanya bisa jalan bersama. |
| Standarnya dari mana? | Tomat: kelas warna USDA (7 CFR 51.1860) dan toleransi lot (51.1861). Lemon: bagan warna OECD untuk citrus, derajat 1–10. Spec pembeli bisa ditambahkan QC Manager. |
| Bagaimana kalau lampu berubah? | Warna dicek dengan kartu referensi setiap awal shift; jika gagal, Line Supervisor mendapat alert. |
| Apakah kamera harus diganti? | Tidak selalu. Kamera IP yang ada bisa dipakai jika lolos cek gambar (fokus, frame rate, silau, warna). |
| Berapa harganya? | Langganan bulanan per line. Angkanya dihitung setelah line survey. |
| Berapa lama sampai jalan? | Line survey 1 minggu, pilot 30 hari, go-live 2 minggu. |
