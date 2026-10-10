# Prompt Claude Design: slide produk pabrik (Factory Vision)

File ini berisi prompt untuk membuat **slide produk pabrik**. Slide-slide ini nanti digabung dengan deck
**Warehouse Live Ops** yang sudah ada. Warehouse tidak dibahas lagi di sini, karena slide-nya sudah jadi.

Ada **4 produk pabrik**. Masing-masing dijual sendiri-sendiri, tetapi berjalan di satu platform yang sama
(web app, TV dashboard, alert, user & role, integrasi):

| Produk | Masalah yang diselesaikan | Kasus di PoC |
|---|---|---|
| **Produce Grading** | warna/kematangan buah dicek manual, lot dikirim campur | tomat (standar USDA) dan lemon (bagan warna OECD), digabung jadi satu produk |
| **Fill Level Inspection** | botol kurang isi lolos ke pasar, botol lebih isi = produk terbuang (giveaway) | mesin pengisi botol |
| **Pack Count QC** | tray/kardus kurang isi baru ketahuan setelah komplain | tray kaleng dan robot packing station (simulasi 3D) |
| **Parcel Dimensioning** | ukuran paket diukur manual, truk tidak terisi optimal, tagihan pakai berat saja | belt paket di truk |

Deck pabrik ini **tidak memuat angka uang**: tidak ada harga, ROI, atau penghematan dalam rupiah.
Harga disebut "per line, dihitung setelah line survey".

## 1. Sudut pandang: pemilik pabrik yang akan membeli

Saat menyusun slide, bayangkan Anda pemilik pabrik yang sedang memilih sistem video analytics.
Setiap slide harus menjawab salah satu pertanyaan ini:

1. **"Masalah saya yang mana yang diselesaikan?"** Reject, komplain pelanggan, giveaway, atau salah kirim.
2. **"Tunjukkan layarnya."** Layar yang dipakai QC dan supervisor setiap hari, cukup besar untuk dibaca.
3. **"Apa yang terjadi di line saat ada masalah?"** Siapa yang diberi tahu, apakah line berhenti, apakah produk ditahan.
4. **"Standarnya siapa?"** Standar resmi (USDA, OECD), spec pembeli, atau toleransi BDKT, dan siapa yang mengaturnya.
5. **"Apa buktinya kalau sistem ini benar?"** Hasil PoC, bukti foto per reject, dan audit trail.
6. **"Cocok dengan line dan sistem saya?"** Kamera, PLC, MES/ERP/WMS.
7. **"Bisa untuk semua pabrik saya?"**
8. **"Bagaimana mulainya, dan apa yang harus saya siapkan?"**

## 2. Struktur slide (21 slide)

| # | Slide | Mockup (dari `factory_mockup/pages/`) | Yang ditonjolkan |
|---|---|---|---|
| F1 | Peta produk | `00_product_map.png` | 4 produk, 1 platform; foto kamera tiap produk |
| F2 | Role & akses | `01_roles_access.png` | 5 role; QC Manager pegang standar, line yang bertindak |
| F3 | Produce Grading · Overview | `02_grading_overview.png` | grade mix per line, off-colour per jam, lot on hold |
| F4 | Produce Grading · Live View | `03_grading_live_view.png` | AI di kamera, lot berjalan, foto buah off-colour, tombol Hold / Re-sort |
| F5 | Produce Grading · TV Dashboard | `04_grading_tv_tomato.png` (+ `05_grading_tv_lemon.png` kecil) | layar TV di line, dari video PoC |
| F6 | Produce Grading · Lot Report | `06_grading_lot_report.png` | cek lot USDA, bukti foto, lot history, ekspor sertifikat lot |
| F7 | Produce Grading · Grade Standards | `07_grading_standards.png` | kelas USDA, bagan OECD, limit lot, uji di rekaman |
| F8 | Fill Level · Overview | `08_fill_overview.png` | rata-rata isi per nozzle vs toleransi, underfill reject, giveaway |
| F9 | Fill Level · TV Dashboard | `09_fill_tv.png` | level isi tiap frame, fill curve, tinggi ≠ volume |
| F10 | Fill Level · Fill Rules | `10_fill_spec.png` | target & toleransi per SKU, sinyal reject ke PLC, giveaway per minggu |
| F11 | Pack Count QC · Overview | `11_pack_overview.png` | short pack per jam, slot yang sering kosong, reject terbaru |
| F12 | Pack Count QC · TV Dashboard | `12_pack_tv_trays.png` (+ `13_pack_tv_packing.png` kecil) | hitung kaleng per tray dan isi kardus per slot |
| F13 | Pack Count QC · Reject Detail | `14_pack_reject_detail.png` | peta slot, bukti, timeline, root cause, corrective action |
| F14 | Parcel Dimensioning · Overview | `15_parcel_overview.png` | P × L × T dan volume per paket, size mix, volume per jam |
| F15 | Parcel Dimensioning · TV Dashboard | `16_parcel_tv.png` | ukuran 3D dari 1 kamera, count line, manual check |
| F16 | Parcel Dimensioning · Load & Billing | `17_parcel_load_billing.png` | isi truk dari volume terukur, berat volumetrik vs berat aktual |
| F17 | Alerts & Integrations | `18_alerts_integrations.png` | alert rule, eskalasi, WhatsApp berfoto, PLC/MES/ERP/WMS |
| F18 | Lines & Cameras | `19_lines_cameras.png` | cek kamera sebelum dipakai, edge AI box, uptime |
| F19 | Plants | `20_plants.png` | semua pabrik, ukuran yang sama, laporan mingguan |
| F20 | Bukti PoC | – (tabel angka) | hasil terukur per produk + batasannya |
| F21 | Paket & rollout | `21_plans_rollout.png` | langganan per line, pilot pass mark, langkah mulai |

**Untuk digabung dengan deck warehouse:** taruh F1–F21 setelah slide tur produk warehouse dan sebelum
slide penutup (model bisnis, bukti, pilot). Slide F2 (role) dan F17–F19 (alert, kamera, multi-plant)
bisa disatukan dengan slide warehouse yang setara jika deck terlalu panjang. Lihat bagian 6.

## 3. Cara pakai

1. Buka Claude Design, lalu buka proyek deck warehouse yang sudah ada, atau mulai proyek baru.
2. Lampirkan 22 gambar dari `factory_mockup/pages/` (semua `.png`, tanpa angka rupiah):
   `00_product_map`, `01_roles_access`, `02_grading_overview`, `03_grading_live_view`,
   `04_grading_tv_tomato`, `05_grading_tv_lemon`, `06_grading_lot_report`, `07_grading_standards`,
   `08_fill_overview`, `09_fill_tv`, `10_fill_spec`, `11_pack_overview`, `12_pack_tv_trays`,
   `13_pack_tv_packing`, `14_pack_reject_detail`, `15_parcel_overview`, `16_parcel_tv`,
   `17_parcel_load_billing`, `18_alerts_integrations`, `19_lines_cameras`, `20_plants`, `21_plans_rollout`.
3. Tempel prompt di bagian 4. Isi dulu `[Nama tim]` dan `[Tanggal]`.
4. Kalau jumlah lampiran dibatasi, kerjakan bertahap: F1–F10 dulu, lalu "lanjutkan F11–F21" dengan sisa gambar.
5. Video demo untuk diputar saat presentasi (bukan untuk dilampirkan ke Claude Design):
   `11_tomato_ripeness/output/tomato_ripeness.mp4`, `12_lime_grading/output/lime_grading.mp4`,
   `04_bottle_fill_volume/output/fill_inspection.mp4`, `08_pack_completeness/output/analytics/line_qc.mp4`,
   `08_pack_completeness/output/analytics/packing_qc.mp4`, `03_parcel_dimensioning/output/parcel_dimensioning.mp4`.

## 4. Prompt (tempel ke kolom chat)

```text
Buatkan 21 slide 16:9 berbahasa Indonesia untuk bagian "produk pabrik" dari deck kami. Slide ini akan digabung dengan deck "Warehouse Live Ops" yang sudah ada, jadi pakai gaya visual yang sama persis. Istilah teknis dan bisnis boleh dalam bahasa Inggris selama umum dipakai di pabrik (line, reject, lot, SKU, QC, PLC, dashboard, alert, giveaway). Jangan memakai kata yang jarang dipakai pemilik bisnis. Jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC) empat produk inspeksi berbasis kamera untuk pabrik. Keempatnya dijual terpisah, per line, tetapi berjalan di satu platform bernama "Factory Vision" (web app, TV dashboard di line, alert ke HP/WhatsApp, user & role, integrasi PLC/MES/ERP/WMS):
- Produce Grading: kelas warna setiap buah di conveyor sesuai standar resmi (tomat: kelas warna USDA; lemon: bagan warna OECD), lalu cek lot terhadap toleransi.
- Fill Level Inspection: level isi setiap botol terhadap target dan toleransi per SKU; underfill di-reject lewat PLC, overfill dicatat sebagai giveaway.
- Pack Count QC: jumlah isi setiap tray dan kardus sebelum disegel, termasuk posisi slot yang kosong dan penyebabnya.
- Parcel Dimensioning: panjang × lebar × tinggi dan volume setiap paket di belt, untuk isi truk dan tagihan berat volumetrik.
Penontonnya pemilik dan direktur pabrik yang sedang memilih sistem video analytics. Mereka bertanya: "Masalah saya yang mana yang selesai, layar apa yang dipakai tim saya, apa yang terjadi di line saat ada masalah, dan apa buktinya?"

GAYA VISUAL
- Sama dengan deck warehouse: latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, aksen biru #2563EB; slide F1 dan F21 berlatar navy #0B1220. Huruf Inter.
- Setiap produk punya warna sendiri, dipakai hanya untuk label kecil dan ikon: Produce Grading hijau #16A34A, Fill Level biru #2563EB, Pack Count QC oranye #D97706, Parcel Dimensioning ungu #7C3AED.
- Judul setiap slide berupa kalimat kesimpulan dari sudut pandang pembeli.
- Slide tur: screenshot adalah bintangnya. Screenshot utama mengisi minimal 60% lebar slide, utuh dalam bingkai browser (sudut membulat, bayangan halus), cukup besar sehingga angka di layar terbaca. Teks pendamping di kolom samping (maksimal 35% lebar). Selang-seling posisi screenshot kiri dan kanan.
- Pada screenshot utama, pasang 3 penanda bernomor (lingkaran biru kecil) di bagian layar yang dijelaskan, sesuai petunjuk letak dalam kurung di setiap poin.
- Screenshot TV dashboard (F5, F9, F12, F15) sudah memuat penanda bernomor dan penjelasan di sisi kanan: tampilkan apa adanya, selebar mungkin, tanpa penanda tambahan.
- Jika ada screenshot kedua, tampilkan lebih kecil (±30% lebar), bertumpuk di pojok screenshot utama dengan bayangan.
- Kolom teks tiap slide tur: label kecil "NAMA PRODUK · n/4" (atau "PLATFORM" untuk F2 dan F17–F19), judul, 3 poin bernomor, satu baris tebal "Manfaat untuk bisnis", dan baris kecil "Dipakai oleh".
- Slide dengan gambar kamera diberi catatan kaki kecil sesuai produknya:
  Produce Grading, Fill Level, Parcel: "Video: Pexels (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
  Pack Count QC: "Video: simulasi 3D buatan tim dengan data kebenaran · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.

GAMBAR TERLAMPIR
00_product_map.png · 01_roles_access.png · 02_grading_overview.png · 03_grading_live_view.png · 04_grading_tv_tomato.png · 05_grading_tv_lemon.png · 06_grading_lot_report.png · 07_grading_standards.png · 08_fill_overview.png · 09_fill_tv.png · 10_fill_spec.png · 11_pack_overview.png · 12_pack_tv_trays.png · 13_pack_tv_packing.png · 14_pack_reject_detail.png · 15_parcel_overview.png · 16_parcel_tv.png · 17_parcel_load_billing.png · 18_alerts_integrations.png · 19_lines_cameras.png · 20_plants.png · 21_plans_rollout.png
Jika ada yang tidak terlampir, pakai bingkai placeholder berlabel nama filenya.

PEMBUKA

F1. Peta produk: "Empat produk inspeksi untuk pabrik, satu platform" (00_product_map.png)
- Tampilkan screenshot hampir penuh. Di atasnya satu kalimat: "Mulai dari satu produk di satu line, tambah produk berikutnya tanpa ganti sistem."
- Empat kartu kecil di bawah judul, satu per produk, masing-masing dengan masalah yang diselesaikan:
  Produce Grading · lot campur warna terkirim ke pembeli
  Fill Level Inspection · botol kurang isi lolos, botol lebih isi = produk terbuang
  Pack Count QC · tray/kardus kurang isi baru ketahuan setelah komplain
  Parcel Dimensioning · ukuran paket tidak diketahui, truk dan tagihan tidak optimal
- Teks kecil: Konsep produk · [Nama tim] · [Tanggal]

F2. PLATFORM · Role & akses: "QC Manager pegang standar, line yang bertindak" (01_roles_access.png)
1) Lima role: Super Admin (vendor), Plant Admin, QC Manager, Line Supervisor, Viewer (kartu di atas).
2) Hak akses per fitur: siapa boleh hold/release lot, override reject, mengubah standar dan toleransi (tabel tengah).
3) Vendor hanya bisa melihat kamera dengan izin Plant Admin, berbatas waktu, tercatat di audit log (catatan di bawah tabel).
Manfaat untuk bisnis: keputusan mutu tetap di tangan QC; setiap override punya nama dan alasan.
Dipakai oleh: Plant Admin, IT.

PRODUCE GRADING (tomat dan lemon dalam satu produk)

F3. PRODUCE GRADING · 1/4 · Overview: "Setiap shift, mutu warna semua line terbaca dalam satu layar" (02_grading_overview.png)
1) Buah ter-grade hari ini, persentase di kelas utama, lot on hold, dan out of grade (baris kartu di atas).
2) Grade mix per line untuk tomat (kelas USDA) dan lemon (lot warna OECD) dalam satu grafik (tengah kiri).
3) Off-colour per jam terhadap limit lot 10%, plus daftar lot dan statusnya: Released, On hold, Mixed Color (kanan tengah dan tabel bawah).
Manfaat untuk bisnis: lot yang bermasalah ketahuan sebelum masuk truk, bukan setelah ditolak pembeli.
Dipakai oleh: QC Manager, Plant Manager.

F4. PRODUCE GRADING · 2/4 · Live View: "Supervisor melihat setiap buah yang keluar dari kelasnya, dan bisa langsung bertindak" (03_grading_live_view.png)
1) Kamera dengan overlay AI: kelas warna per buah, nomor line, count gate (screenshot kamera besar).
2) Lot yang sedang berjalan: jumlah per kelas USDA dan status off-colour 17% di atas limit 10% (kartu kanan atas).
3) Foto buah off-colour beserta line-nya, dan tombol Hold lot / Re-sort / Release as Mixed Color (kanan tengah dan bawah).
Manfaat untuk bisnis: re-sort dilakukan saat buah masih di line, bukan di gudang.
Dipakai oleh: Line Supervisor.

F5. PRODUCE GRADING · 3/4 · TV Dashboard: "Layar di line menunjukkan mutu lot saat itu juga" (04_grading_tv_tomato.png utama, 05_grading_tv_lemon.png kecil)
- Ini frame dari video PoC (rekaman Pexels): tomat di 4 line dengan kelas warna USDA, dan lemon di 2 chain dengan bagan warna OECD derajat 1–10. TV berganti tampilan otomatis.
- Poin di kolom teks: (1) setiap buah dihitung sekali di count gate, dengan line dan kelasnya; (2) KPI lot dan Grade Composition langsung memberi status label lot; (3) Event Log berfoto untuk setiap buah di luar kelas utama.
Manfaat untuk bisnis: operator tidak perlu menebak; satu layar memberi tahu kapan harus sortir ulang.
Dipakai oleh: operator line, Line Supervisor.

F6. PRODUCE GRADING · 4/4 · Lot Report: "Setiap lot punya keputusan, bukti, dan riwayat yang bisa ditunjukkan ke pembeli" (06_grading_lot_report.png)
1) Cek lot sesuai USDA 7 CFR 51.1861: off-colour 17% > limit 10% → label Mixed Color, atau re-sort 7 buah agar bisa dilabel Red (kartu tengah atas).
2) Bukti foto buah off-colour dan sebaran warna setiap buah terhadap batas kelas USDA (baris tengah dan bawah kiri).
3) Lot history (kapan dibuka, alert, hold, re-sort, siapa) dan ekspor lot certificate PDF untuk QA pembeli (kanan bawah dan tombol atas).
Manfaat untuk bisnis: klaim dari pembeli bisa dijawab dengan data per lot, bukan perkiraan.
Dipakai oleh: QC Manager, tim sales/ekspor.

F7. PRODUCE GRADING · Grade Standards: "Standar resmi dan spec pembeli, diatur sendiri oleh QC" (07_grading_standards.png)
1) Library standar: kelas warna tomat USDA, bagan warna lemon OECD, dan spec pembeli (tabel kiri).
2) Batas tiap kelas, limit off-colour, aksi otomatis saat limit terlewati, dan cek warna dengan kartu referensi tiap awal shift (panel kanan).
3) Uji standar di rekaman sebelum dipakai; di PoC, 75 dari 78 tomat sama dengan cek mata (kartu bawah dan bagan OECD).
Manfaat untuk bisnis: ganti pembeli atau pasar ekspor cukup ganti standar, bukan ganti sistem.
Dipakai oleh: QC Manager.

FILL LEVEL INSPECTION

F8. FILL LEVEL · 1/3 · Overview: "Setiap botol dicek; underfill di-reject, overfill dihitung sebagai produk terbuang" (08_fill_overview.png)
1) Botol diinspeksi, underfill reject, rata-rata overfill dalam mL, dan persentase dalam toleransi (baris kartu atas).
2) Rata-rata isi per nozzle terhadap target dan batas toleransi: nozzle 3 terlihat selalu lebih isi (grafik kiri).
3) Underfill per jam dengan penyebabnya (tangki rendah jam 10:00), reject terbaru, dan kamera live (kanan dan baris bawah).
Manfaat untuk bisnis: aman dari komplain isi kurang, dan giveaway per nozzle terukur sehingga bisa dikurangi.
Dipakai oleh: QC Manager, Production Manager.

F9. FILL LEVEL · 2/3 · TV Dashboard: "Level isi diukur setiap frame, selama botol diisi" (09_fill_tv.png)
- Frame dari video PoC (rekaman Pexels): level isi, flow rate, waktu menuju target, dan fill curve per nozzle.
- Poin: (1) garis target di botol dan level saat ini; (2) "tinggi bukan volume": bentuk botol diukur sehingga tinggi 44% = volume 31%; (3) aturan pass/reject per SKU tampil di layar.
- Catatan jujur di slide: klip PoC selesai di 67% saat botol masih diisi, jadi belum ada keputusan pass/reject; angka mL memakai contoh SKU 500 mL.
Manfaat untuk bisnis: keputusan isi berdasarkan volume, bukan perkiraan dari tinggi cairan.
Dipakai oleh: operator filler, QC.

F10. FILL LEVEL · 3/3 · Fill Rules: "Target, toleransi, dan aksi diatur per SKU" (10_fill_spec.png)
1) Daftar SKU dan aturan isi: target, toleransi 98–102%, reject di bawah 490 mL lewat sinyal PLC dalam 0,5 detik (tabel kiri dan tengah).
2) Profil botol dari 3 botol kosong agar tinggi bisa diubah jadi volume, dan toleransi disesuaikan dengan BDKT dan spec pelanggan (kolom kanan atas).
3) Giveaway per minggu turun setelah garis target dipindah, checklist sebelum go-live, dan riwayat perubahan (baris bawah).
Manfaat untuk bisnis: aturan mutu dan bukti perubahan tersimpan rapi, siap untuk audit.
Dipakai oleh: QC Manager.

PACK COUNT QC

F11. PACK COUNT QC · 1/3 · Overview: "Tray dan kardus kurang isi ditahan sebelum disegel" (11_pack_overview.png)
1) Pack diinspeksi, short pack yang tertangkap, item hilang, dan feeder gap sebagai penyebab (baris kartu atas).
2) Slot mana yang paling sering kosong minggu ini: A2 dan A3, menunjuk ke filler lane 2 dan 3 (heatmap kanan).
3) Reject terbaru berfoto dengan severity, kamera, dan jam (kiri bawah).
Manfaat untuk bisnis: komplain "isi kurang" dari pelanggan dicegah, dan penyebabnya ketahuan.
Dipakai oleh: QC Manager, Line Supervisor.

F12. PACK COUNT QC · 2/3 · TV Dashboard: "Setiap tray dihitung, setiap slot kosong ditandai" (12_pack_tv_trays.png utama, 13_pack_tv_packing.png kecil)
- Frame dari video PoC (simulasi 3D dengan data kebenaran): tray 10 kaleng di ujung line, dan robot packing station 20 item per kardus.
- Poin: (1) slot kosong dilingkari merah dan tray ditandai SHORT; (2) posisi slot yang hilang dan pola berulangnya; (3) di packing station, empty pick robot dan feeder supply gap tercatat sebagai penyebab.
Manfaat untuk bisnis: bukan hanya "kurang", tapi juga "kurang di slot mana dan kenapa".
Dipakai oleh: operator line, Line Supervisor.

F13. PACK COUNT QC · 3/3 · Reject Detail: "Setiap reject punya bukti, penyebab, dan tindakan perbaikan" (14_pack_reject_detail.png)
1) Peta slot kardus: B2 dan C5 kosong, 18/20, dengan root cause feeder supply gap (kiri atas).
2) Bukti foto dan klip 10 detik sebelum–sesudah, siap diekspor PDF (tengah).
3) Timeline dari feeder gap → empty pick → kardus ditahan → WhatsApp ke supervisor → rework 20/20, plus corrective action (kanan dan kiri bawah).
Manfaat untuk bisnis: investigasi selesai dalam menit; bukti siap untuk pelanggan atau audit.
Dipakai oleh: Line Supervisor, QC Manager, Maintenance.

PARCEL DIMENSIONING

F14. PARCEL DIMENSIONING · 1/3 · Overview: "Ukuran dan volume setiap paket, tanpa meteran" (15_parcel_overview.png)
1) Paket terukur hari ini, volume, berat volumetrik, dan paket yang perlu manual check (baris kartu atas).
2) Parcel log: P × L × T, volume, berat volumetrik (P×L×T/6000), kelas S/M/L (tabel kiri).
3) Size mix dan volume per jam untuk merencanakan truk lebih awal (kanan dan baris bawah).
Manfaat untuk bisnis: data ukuran untuk setiap paket tanpa menambah orang atau memperlambat belt.
Dipakai oleh: Warehouse/Logistics Manager.

F15. PARCEL DIMENSIONING · 2/3 · TV Dashboard: "Satu kamera mengukur P × L × T paket di belt" (16_parcel_tv.png)
- Frame dari video PoC (rekaman Pexels): setiap paket diukur saat lewat, dihitung di count line, dan masuk tabel.
- Poin: (1) kotak 3D dan ukuran per paket; (2) paket yang ukurannya dekat batas kelas masuk manual check, bukan ditebak; (3) volume kumulatif dan laju bongkar.
Manfaat untuk bisnis: ukuran yang konsisten, bisa dicek ulang dari fotonya.
Dipakai oleh: operator belt, supervisor logistik.

F16. PARCEL DIMENSIONING · 3/3 · Load & Billing: "Volume terukur dipakai untuk isi truk dan tagihan" (17_parcel_load_billing.png)
1) Isi tiap truk dari volume terukur: loaded, loading, planned (kiri atas).
2) Berat volumetrik vs berat aktual per pelanggan; pelanggan dengan paket ringan tapi besar ditagih berdasarkan volume (kanan atas).
3) Antrean manual check dan dasar tagihan per pelanggan, siap dikirim ke TMS/WMS (baris bawah).
Manfaat untuk bisnis: truk terisi lebih penuh dan tagihan sesuai ruang yang benar-benar dipakai.
Dipakai oleh: Logistics Manager, Finance.

PLATFORM (dipakai semua produk)

F17. PLATFORM · Alerts & Integrations: "Orang yang tepat tahu dalam detik, line bertindak otomatis" (18_alerts_integrations.png)
1) Alert rule per produk: kapan, lalu apa (hold lot, sinyal reject ke PLC, divert ke rework, WhatsApp), dengan severity (tabel kiri atas).
2) Eskalasi: Line Supervisor → QC Manager setelah 5 menit → Plant Admin setelah 15 menit, dan daftar alert terkirim hari ini (kiri bawah).
3) Integrasi PLC/SCADA, MES, ERP, WMS/TMS, WhatsApp Business, webhook & API, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: tidak ada masalah yang menunggu laporan akhir shift.
Dipakai oleh: Plant Admin, IT.

F18. PLATFORM · Lines & Cameras: "Setiap kamera dicek sebelum dipakai, dan dipantau setelahnya" (19_lines_cameras.png)
1) Semua kamera per line dan produk, status, frame rate, dan hasil image check (tabel atas).
2) Cek kamera baru: fokus, frame rate, silau, warna dengan kartu referensi, beserta saran perbaikannya (kiri bawah).
3) Edge AI box per line, uptime kamera 7 hari, dan apa yang perlu disiapkan pabrik (tengah dan kanan bawah).
Manfaat untuk bisnis: hasil inspeksi bisa dipercaya karena kualitas gambar dijaga setiap hari.
Dipakai oleh: Plant Admin, Maintenance.

F19. PLATFORM · Plants: "Kantor pusat melihat semua pabrik dengan ukuran yang sama" (20_plants.png)
1) Semua pabrik dan produk yang aktif: first-pass quality, short-pack rate, lot on hold, rata-rata overfill (tabel atas).
2) Tren first-pass quality 12 minggu per pabrik (grafik kiri bawah).
3) Yang perlu perhatian, dan laporan mingguan otomatis ke kantor pusat (kanan bawah).
Manfaat untuk bisnis: pabrik bisa dibandingkan secara adil, dan praktik terbaik bisa ditiru.
Dipakai oleh: Direksi, Operations Director.

PENUTUP

F20. Bukti PoC: "Inti teknologinya sudah diuji pada video nyata dan simulasi dengan data kebenaran"
Tabel 4 baris, satu per produk, kolom: Produk · Yang diuji · Hasil · Yang masih harus dibuktikan di pilot.
- Produce Grading · tomat: 41 tomat di 4 line, kelas warna USDA · 75 dari 78 sama dengan cek mata secara blind, sisanya selisih 1 kelas · lot dengan pencahayaan dan kamera pabrik sendiri
- Produce Grading · lemon: 87 lemon di 2 chain, bagan warna OECD 1–10 · 18 dari 24 dalam ±1 derajat dari cek mata secara blind · kalibrasi kartu warna di line pabrik
- Fill Level: level isi setiap frame, bentuk botol diubah jadi volume · klip PoC selesai di 67% saat botol masih diisi; belum ada keputusan pass/reject · keputusan pass/reject dan perbandingan dengan check weigher
- Pack Count QC: tray 10 kaleng dan kardus 20 item (simulasi 3D) · 7 dari 7 tray dan 3 dari 3 kardus benar; 2 dari 2 empty pick tertangkap · uji di line nyata
- Parcel Dimensioning: 8 paket di belt · 8 dari 8 terhitung; karton uji terbaca 340,5 mm vs 340 mm sebenarnya · ±1 cm pada 100 paket
Catatan kaki: "Laju per menit/jam di video adalah perkiraan dari klip beberapa detik, bukan data satu shift."

F21. Paket & langkah mulai: "Beli satu produk untuk satu line, lalu kembangkan" (21_plans_rollout.png)
1) Langganan bulanan per line untuk tiap produk; fitur yang termasuk dan add-on (kartu atas dan tengah).
2) Pilot pass mark per produk: angka yang harus tercapai sebelum lanjut (bagian bawah kartu produk).
3) Langkah: line survey 1 minggu → pilot 30 hari → go-live 2 minggu → expand; pembagian tugas pabrik vs vendor (baris bawah).
Kalimat penutup tebal: "Harga per line, dihitung setelah line survey. Biaya pilot dikreditkan ke kontrak bila berlanjut."

ATURAN
- Tidak ada angka uang: jangan tampilkan rupiah, harga, ROI, persentase penghematan, atau proyeksi pendapatan.
- Jangan menambah statistik pasar, kutipan, nama/logo klien, atau klaim lain di luar prompt ini.
- Angka di layar mockup adalah ilustrasi, kecuali yang bertanda PoC. Jangan mengutip angka ilustrasi sebagai hasil.
- Format angka Indonesia di teks slide (340,5 mm), angka di screenshot biarkan apa adanya.
- Tambahkan catatan pembicara 2–3 kalimat untuk setiap slide; di slide tur, catatannya berisi cara mendemokan layar itu dalam satu menit, dan untuk F5, F9, F12, F15 sebutkan video demo yang diputar.
```

## 5. Pegangan tanya jawab (dari sudut pandang pembeli)

| Pertanyaan | Jawaban singkat |
|---|---|
| Apa bedanya dengan sortir mesin optik yang sudah ada? | Mesin sortir memutuskan per buah. Produce Grading membaca setiap buah, menggabungkannya per lot, dan mencocokkan dengan standar yang dipakai pembeli (USDA, OECD, atau spec pembeli), lengkap dengan bukti foto. Keduanya bisa jalan bersama. |
| Standarnya dari mana? | Tomat: kelas warna USDA (7 CFR 51.1860) dan toleransi lot (51.1861). Lemon: bagan warna OECD untuk citrus, derajat 1–10. Spec pembeli bisa ditambahkan oleh QC Manager. |
| Apakah kamera harus diganti? | Tidak selalu. Kamera IP yang ada bisa dipakai jika lolos image check (fokus, frame rate, silau, warna). Untuk botol biasanya perlu backlight. |
| Bagaimana kalau sistem salah? | Setiap keputusan punya foto. Reject bisa di-override oleh QC Manager dengan alasan, dan tercatat di audit log. Akurasi diukur di pilot dengan cek blind oleh QC pabrik. |
| Apakah line jadi lebih lambat? | Tidak. Kamera membaca produk yang lewat; aksi ke line (reject, divert) lewat sinyal PLC yang sudah ada. |
| Bisa tersambung ke sistem kami? | PLC/SCADA (OPC UA, Modbus TCP), MES, ERP, WMS/TMS, WhatsApp Business, webhook dan REST API. |
| Berapa harganya? | Langganan bulanan per line. Angkanya dihitung setelah line survey, sesuai jumlah line dan produk. |
| Berapa lama sampai jalan? | Line survey 1 minggu, pilot 30 hari, go-live 2 minggu. |

### Yang diukur saat pilot 30 hari

- **Produce Grading:** kecocokan kelas warna dan status lot dengan cek blind oleh QC pabrik; jumlah lot yang ditahan sebelum kirim.
- **Fill Level:** setiap underfill ter-reject; level isi per nozzle dibandingkan dengan check weigher; giveaway per nozzle.
- **Pack Count QC:** setiap short pack tertahan sebelum disegel, dengan slot yang kosong; penyebab berulang (feeder, lane).
- **Parcel Dimensioning:** P × L × T dalam ±1 cm dari meteran pada 100 paket; isi truk sebelum vs sesudah.

## 6. Kalau digabung dengan deck warehouse terlalu panjang

- "Ringkas bagian pabrik jadi 12 slide: F1, lalu satu slide Overview + satu slide TV Dashboard untuk setiap produk (F3+F5, F8+F9, F11+F12, F14+F15), F17, F20, dan F21. Screenshot utama tetap besar."
- "Gabungkan F2 dengan slide role warehouse, dan F17–F19 dengan slide platform warehouse, sebagai satu platform untuk gudang dan pabrik."
- "Tambahkan slide pemisah sebelum F1 berjudul 'Untuk pabrik' dengan latar navy."
- "Ekspor ke PPTX atau PDF."

## 7. Sumber gambar

- `factory_mockup/pages/*.png` dibuat oleh `factory_mockup/build.py` (HTML → PNG 1920 × 1080). Gambar kamera
  dan angka bertanda PoC diambil dari video PoC oleh `factory_mockup/assets.py`. Nama pabrik, orang,
  angka harian, dan tren adalah ilustrasi, dan setiap halaman menuliskannya di pojok kanan bawah.
- Video: Pexels 8675103 (tomat), Pexels 32953325 (lemon), Pexels 8720278 (botol), Pexels 5370836 (paket),
  semuanya lisensi Pexels; Pack Count QC dari simulasi 3D buatan tim (Blender).
