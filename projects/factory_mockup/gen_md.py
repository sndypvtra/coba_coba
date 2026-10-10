#!/usr/bin/env python3
"""Write apps/<app>/<app>.md: the Claude Design prompt for each product's own deck.

    python factory_mockup/gen_md.py
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent

COMMON_STYLE = """GAYA VISUAL
- Sama dengan deck "Warehouse Live Ops": latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, huruf Inter. Warna aksen produk ini: {colour} (untuk label kecil, ikon, dan garis penanda). Slide 1 dan slide terakhir berlatar navy #0B1220.
- Judul setiap slide berupa kalimat kesimpulan dari sudut pandang pembeli.
- Slide tur produk: screenshot adalah bintangnya. Screenshot utama mengisi minimal 60% lebar slide, utuh dalam bingkai browser (sudut membulat, bayangan halus), jangan dipotong. Teks pendamping di kolom samping (maksimal 35% lebar). Selang-seling posisi screenshot kiri dan kanan.
- Screenshot Dashboard TV (latar gelap) ditaruh dalam bingkai layar TV (bezel tipis, sudut membulat).
- Pada setiap screenshot, pasang 3 penanda bernomor (lingkaran kecil warna aksen) di bagian layar yang dijelaskan, sesuai petunjuk letak dalam kurung di setiap poin.
- Jika ada screenshot kedua, tampilkan lebih kecil (±30% lebar), bertumpuk di pojok screenshot utama dengan bayangan.
- Kolom teks tiap slide tur: label kecil "FITUR n/{n_tour} · NAMA LAYAR", judul, 3 poin bernomor, satu baris tebal "Manfaat untuk bisnis", dan baris kecil "Dipakai oleh".
- Catatan kaki kecil di slide yang memuat gambar kamera: "{footnote}"
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata."""

COMMON_RULES = """ATURAN
- Tidak ada angka uang: jangan tampilkan rupiah, harga, ROI, persentase penghematan, atau proyeksi pendapatan.
- Jangan menambah statistik pasar, kutipan, nama/logo klien, atau klaim lain di luar prompt ini.
- Angka di layar mockup adalah ilustrasi, kecuali yang bertanda PoC. Jangan mengutip angka ilustrasi sebagai hasil.
- Format angka Indonesia (340,5 mm; 41.860).
- Bahasa Indonesia sehari-hari; istilah teknis dan bisnis boleh dalam bahasa Inggris selama umum dipakai di pabrik. Hindari kata yang jarang dipakai pemilik bisnis.
- Tambahkan catatan pembicara 2–3 kalimat untuk setiap slide; di slide tur, isinya cara mendemokan layar itu dalam satu menit."""

APPS = {
    "produce_grading": dict(
        name="Produce Grading", colour="#16A34A", buyer="packing house buah dan sayur, eksportir, pemasok supermarket",
        tagline="Grade warna setiap buah di line, sesuai standar USDA dan OECD, lengkap dengan bukti per lot.",
        footnote="Video: Pexels (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC",
        problem=["Warna dan kematangan buah dicek manual dengan sampel kecil; lot campur warna lolos ke pembeli.",
                 "Klaim dari pembeli atau importir sulit dijawab karena tidak ada data per lot.",
                 "Standar berbeda per pembeli (USDA, OECD, spec supermarket) dan sulit diterapkan konsisten tiap shift.",
                 "Sortir ulang baru dilakukan di gudang, setelah buah sudah dikemas."],
        flow="kamera di atas conveyor → edge AI box membaca kelas warna setiap buah dan menghitungnya per line → web app menggabungkan per lot dan mencocokkan dengan standar → hold lot, sortir ulang, atau release, dengan bukti foto",
        users="QC Manager, Line Supervisor, operator line, tim sales/ekspor",
        pages=[
            ("01_ringkasan.png", None, "Ringkasan", "Setiap shift, mutu warna semua line terbaca di satu layar", [
                "Buah di-grade hari ini, persentase di kelas warna utama, lot di-hold, dan out of grade (baris kartu atas).",
                "Komposisi grade per line untuk tomat (kelas USDA) dan lemon (lot warna OECD), plus off-colour per jam terhadap limit lot 10% (grafik tengah).",
                "Daftar lot shift ini dengan statusnya (Release, Hold, Mixed Color) dan cuplikan line yang sedang berjalan (baris bawah)."],
             "lot bermasalah ketahuan sebelum naik truk, bukan setelah ditolak pembeli.", "QC Manager, Plant Manager"),
            ("02_live_monitoring.png", None, "Live Monitoring", "Supervisor melihat setiap buah yang keluar dari kelasnya, dan langsung bertindak", [
                "Kamera dengan overlay AI: kelas warna per buah, nomor line, count gate (kamera besar kiri).",
                "Lot berjalan: jumlah per kelas USDA dan off-colour 17% di atas limit 10%, plus foto buah off-colour per line (kolom kanan).",
                "Tombol Hold lot, Sortir ulang di line T2, atau Release sebagai Mixed Color (kanan bawah)."],
             "sortir ulang dilakukan saat buah masih di line, bukan di gudang.", "Line Supervisor"),
            ("03_dashboard_tv_tomat.png", "04_dashboard_tv_lemon.png", "Dashboard TV", "Layar di line menunjukkan mutu lot saat itu juga", [
                "Kamera live dengan AI: setiap tomat diberi kotak sesuai kelas warna USDA dan dihitung sekali di count gate (gambar kamera kiri atas).",
                "KPI lot dan Grade Composition: 41 tomat, 83% Red, off-colour 17% di atas limit 10% → label Mixed Color atau sortir ulang 7 buah (kanan atas dan tengah).",
                "Event Log berfoto, grafik per line, off-colour yang terus naik, dan lini masa (kanan bawah dan baris bawah). Screenshot kecil: tampilan lemon dengan bagan warna OECD derajat 1–10, berganti otomatis di TV yang sama."],
             "operator tidak perlu menebak; satu layar memberi tahu kapan harus sortir ulang.", "operator line, Line Supervisor"),
            ("05_laporan_lot.png", None, "Laporan Lot", "Setiap lot punya keputusan, bukti, dan riwayat yang bisa ditunjukkan ke pembeli", [
                "Cek lot sesuai USDA 7 CFR 51.1861: off-colour 17% > limit 10% → Mixed Color, atau sortir ulang 7 buah agar bisa diberi label Red (kartu tengah atas).",
                "Foto bukti buah off-colour dan sebaran warna setiap buah terhadap batas kelas USDA (baris tengah dan kiri bawah).",
                "Riwayat lot (dibuka, alert, hold, sortir ulang, oleh siapa) dan ekspor sertifikat lot PDF untuk QA pembeli (kanan bawah dan tombol atas)."],
             "klaim pembeli bisa dijawab dengan data per lot, bukan perkiraan.", "QC Manager, tim sales/ekspor"),
            ("06_standar_grade.png", None, "Standar Grade", "Standar resmi dan spec pembeli, diatur sendiri oleh QC", [
                "Daftar standar: kelas warna tomat USDA, bagan warna lemon OECD, dan spec pembeli (tabel kiri atas).",
                "Batas tiap kelas, limit off-colour, tindakan otomatis jika limit terlewati, dan cek warna dengan kartu referensi tiap awal shift (panel kanan atas).",
                "Standar diuji dulu di rekaman sebelum go-live; di PoC 75 dari 78 tomat sama dengan cek mata (kartu tengah dan bagan OECD di bawah)."],
             "ganti pembeli atau pasar ekspor cukup ganti standar, bukan ganti sistem.", "QC Manager"),
            ("07_kamera_alert_integrasi.png", None, "Kamera, Alert & Integrasi", "Orang yang tepat tahu dalam hitungan detik, line bertindak otomatis", [
                "Kamera per line dengan status dan hasil cek gambar (tabel kiri atas).",
                "Aturan alert khusus grading (off-colour lot, hijau di lot, lemon derajat 10, kartu warna gagal) dan eskalasi (kiri tengah dan bawah).",
                "Integrasi ke PLC sortir, ERP/sistem lot, WhatsApp, dan API, plus contoh pesan WhatsApp berfoto (kolom kanan)."],
             "masalah tidak menunggu laporan akhir shift.", "Plant Admin, IT"),
        ],
        proof=["41 tomat di 4 line, kelas warna USDA (7 CFR 51.1860): 75 dari 78 sama dengan cek mata secara blind, sisanya beda 1 kelas.",
               "87 lemon di 2 chain, bagan warna OECD derajat 1–10: 18 dari 24 dalam ±1 derajat dari cek mata secara blind.",
               "Batas kelas tomat diambil dari data colorimeter yang dipublikasikan, bukan disetel ke klip ini.",
               "Yang dibuktikan saat pilot: lot dengan kamera dan pencahayaan pabrik sendiri, dicek blind oleh QC pabrik."],
        qa=[("Apa bedanya dengan mesin sortir optik?", "Mesin sortir memutuskan per buah. Produce Grading membaca setiap buah, menggabungkannya per lot, dan mencocokkannya dengan standar pembeli, lengkap dengan foto bukti. Keduanya bisa jalan bersama."),
            ("Standarnya dari mana?", "Tomat: kelas warna USDA (7 CFR 51.1860) dan toleransi lot (51.1861). Lemon: bagan warna OECD untuk citrus, derajat 1–10. Spec pembeli bisa ditambahkan QC Manager."),
            ("Bagaimana kalau lampu berubah?", "Warna dicek dengan kartu referensi setiap awal shift; jika gagal, Line Supervisor mendapat alert.")],
        pilot="kecocokan kelas warna dan status lot dengan cek blind oleh QC pabrik; jumlah lot yang ditahan sebelum dikirim",
    ),
    "fill_level_inspection": dict(
        name="Fill Level Inspection", colour="#2563EB", buyer="pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol",
        tagline="Level isi setiap botol terhadap target dan toleransi; underfill di-reject, overfill dihitung sebagai giveaway.",
        footnote="Video: Pexels 8720278 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC",
        problem=["Botol kurang isi lolos ke pasar: risiko komplain dan masalah BDKT.",
                 "Botol lebih isi tidak terukur, padahal itu produk yang diberikan gratis (giveaway) setiap hari.",
                 "Cek manual hanya sampel per jam; nozzle yang bermasalah baru ketahuan belakangan.",
                 "Tinggi cairan tidak sama dengan volume, karena bentuk botol menyempit di dasar dan bahu."],
        flow="kamera samping dengan backlight di mesin pengisi → edge AI box mengukur level isi setiap frame dan mengubahnya jadi volume dari bentuk botol → web app menilai pass/reject per SKU → sinyal reject ke PLC dan laporan giveaway per nozzle",
        users="QC Manager, Production Manager, operator filler",
        pages=[
            ("01_ringkasan.png", None, "Ringkasan", "Setiap botol dicek; underfill di-reject, overfill dihitung sebagai produk terbuang", [
                "Botol diinspeksi, reject underfill, rata-rata overfill dalam mL, dan persentase dalam toleransi (baris kartu atas).",
                "Rata-rata isi per nozzle terhadap target dan batas toleransi: nozzle 3 selalu kelebihan isi (grafik kiri).",
                "Reject per jam dengan penyebabnya, reject terbaru, dan kamera live (kanan dan baris bawah)."],
             "aman dari komplain isi kurang, dan giveaway per nozzle terukur sehingga bisa dikurangi.", "QC Manager, Production Manager"),
            ("02_live_monitoring.png", None, "Live Monitoring", "Level isi terlihat langsung di layar, nozzle demi nozzle", [
                "Kamera dengan overlay AI: outline botol, garis target di leher botol, level isi dalam % dan mL (kamera besar kiri).",
                "Siklus berjalan dan hasil terakhir per nozzle 1–8, dengan nozzle yang bermasalah ditandai (kolom kanan).",
                "Tombol hentikan nozzle untuk dicek atau tandai reject manual (kanan bawah)."],
             "supervisor tahu nozzle mana yang bermasalah tanpa menunggu sampel per jam.", "Line Supervisor"),
            ("03_dashboard_tv.png", None, "Dashboard TV", "Level isi diukur setiap frame, selama botol diisi", [
                "Kamera live dengan AI: garis target dan level isi saat ini dalam % dan mL (gambar kamera kiri atas).",
                "KPI dan fill curve: level isi, flow rate, waktu isi, sisa waktu ke target (kanan atas).",
                "Aturan pass/reject per SKU dan \"tinggi bukan volume\": tinggi 74% = volume 67% (baris bawah). Catatan jujur: klip PoC berakhir di 67%, jadi belum ada keputusan pass/reject; angka mL memakai contoh SKU 500 mL."],
             "keputusan isi berdasarkan volume, bukan perkiraan dari tinggi cairan.", "operator filler, QC"),
            ("04_reject_giveaway.png", None, "Reject & Giveaway", "Setiap reject punya bukti; setiap mL lebih dihitung", [
                "Reject underfill terbaru per nozzle, dengan status dikonfirmasi QC atau alarm palsu (tabel kiri atas).",
                "Giveaway per nozzle terhadap target dan batas toleransi, dengan saran tindakan (grafik kanan atas).",
                "Bukti reject (gambar kamera, level saat nozzle berhenti, sinyal ke PLC) dan reject per jam (baris bawah)."],
             "tim teknik tahu nozzle mana yang perlu disetel, berdasarkan data, bukan perasaan.", "QC Manager, Maintenance"),
            ("05_spesifikasi_sku.png", None, "Spesifikasi SKU", "Target, toleransi, dan tindakan diatur per SKU", [
                "Daftar SKU dan aturan isi: target, toleransi 98–102%, reject di bawah 490 mL lewat sinyal PLC dalam 0,5 detik (kiri dan tengah atas).",
                "Profil botol dari 3 botol kosong agar tinggi cairan bisa diubah jadi volume; toleransi disesuaikan dengan BDKT dan spec pelanggan (kanan atas).",
                "Giveaway per minggu turun setelah garis target dipindah, checklist sebelum go-live, dan riwayat perubahan (baris bawah)."],
             "aturan mutu dan bukti perubahannya tersimpan rapi, siap untuk audit.", "QC Manager"),
            ("06_kamera_alert_integrasi.png", None, "Kamera, Alert & Integrasi", "Reject langsung ke PLC, alert langsung ke orang yang tepat", [
                "Kamera per mesin pengisi dengan status dan hasil cek gambar, termasuk kamera yang perlu dicek (tabel kiri atas).",
                "Aturan alert khusus pengisian (underfill, reject berulang di satu nozzle, overfill beruntun, kamera silau) dan eskalasi (kiri tengah dan bawah).",
                "Integrasi PLC/rejector, check weigher, MES, WhatsApp, plus contoh pesan WhatsApp berfoto (kolom kanan)."],
             "line bertindak otomatis, dan masalah nozzle tidak menunggu akhir shift.", "Plant Admin, IT"),
        ],
        proof=["Level isi diukur setiap frame pada rekaman nyata mesin pengisi, dan bentuk botol diukur sehingga tinggi diubah menjadi volume.",
               "Klip PoC berakhir di 67% saat botol masih diisi, jadi belum ada keputusan pass/reject; angka mL memakai contoh SKU 500 mL.",
               "Yang dibuktikan saat pilot: keputusan pass/reject setiap botol dan perbandingan level isi dengan check weigher."],
        qa=[("Apakah perlu kamera khusus?", "Kamera industri atau IP biasa cukup, dipasang tetap di samping mesin pengisi; untuk botol bening biasanya perlu backlight."),
            ("Bagaimana dengan botol berwarna gelap?", "Diuji saat line survey; jika level tidak terlihat dari samping, posisi kamera atau lampu disesuaikan."),
            ("Apa bedanya dengan check weigher?", "Check weigher menimbang di ujung line. Fill Level membaca per nozzle saat pengisian, jadi penyebabnya langsung terlihat. Keduanya bisa dibandingkan.")],
        pilot="setiap underfill ter-reject; level isi per nozzle dibandingkan dengan check weigher; giveaway per nozzle",
    ),
    "pack_count_qc": dict(
        name="Pack Count QC", colour="#D97706", buyer="pabrik makanan dan minuman kemasan, FMCG, co-packer",
        tagline="Jumlah isi setiap tray dan kardus sebelum disegel, lengkap dengan slot yang kosong dan penyebabnya.",
        footnote="Video: simulasi 3D buatan tim dengan data kebenaran · layar mockup, angka ilustrasi kecuali yang bertanda PoC",
        problem=["Tray atau kardus kurang isi baru ketahuan setelah ada komplain dari distributor atau konsumen.",
                 "Cek manual hanya sampel; kemasan yang sudah disegel sulit dibuka ulang.",
                 "Penyebab kekurangan (feeder kosong, lane filler, robot) tidak tercatat, jadi masalah berulang.",
                 "Bukti untuk menjawab klaim pelanggan tidak ada."],
        flow="kamera di atas ujung line atau packing station → edge AI box menghitung isi setiap tray/kardus per slot → web app menilai lengkap atau kurang sebelum disegel → hold/divert ke rework, alert, dan penyebabnya dicatat",
        users="QC Manager, Line Supervisor, Maintenance",
        pages=[
            ("01_ringkasan.png", None, "Ringkasan", "Tray dan kardus kurang isi ditahan sebelum disegel", [
                "Pack diinspeksi, short pack tertangkap, item kurang, dan feeder gap sebagai penyebab (baris kartu atas).",
                "Short pack per jam dan slot yang paling sering kosong minggu ini (grafik kiri dan heatmap kanan).",
                "Reject & kejadian terbaru berfoto dan dua kamera live (baris bawah)."],
             "komplain \"isi kurang\" dicegah, dan penyebabnya ketahuan.", "QC Manager, Line Supervisor"),
            ("02_live_monitoring.png", None, "Live Monitoring", "Setiap tray dan kardus terlihat dihitung, langsung di layar", [
                "Kamera dengan overlay AI: jumlah isi, slot kosong dilingkari merah, tray ditandai SHORT (kamera besar kiri).",
                "Tray terakhir dan alert terbaru dengan tombol Konfirmasi & reject atau Alarm palsu (kolom kanan).",
                "Kardus di packing station, kecepatan robot, dan status feeder (kanan bawah)."],
             "supervisor bertindak sebelum kemasan disegel, bukan setelah komplain.", "Line Supervisor"),
            ("03_dashboard_tv_tray.png", "04_dashboard_tv_packing.png", "Dashboard TV", "Setiap tray dihitung, setiap slot kosong ditandai", [
                "Kamera live dengan AI: slot kosong dilingkari merah dan tray ditandai SHORT (gambar kamera kiri atas).",
                "Posisi kaleng yang kosong dan apakah berulang, menunjuk ke lane filler (kanan tengah).",
                "Tray terakhir dengan pass/reject, tray diinspeksi kumulatif, dan Event Log berfoto (baris bawah). Screenshot kecil: robot packing station dengan peta slot kardus dan root cause feeder gap → empty pick → kardus kurang isi."],
             "bukan hanya \"kurang\", tetapi juga \"kurang di slot mana dan kenapa\".", "operator line, Line Supervisor"),
            ("05_detail_reject.png", None, "Detail Reject", "Setiap reject punya bukti, penyebab, dan tindakan perbaikan", [
                "Peta slot kardus: B2 dan C5 kosong, 18/20, dengan root cause feeder gap (kiri atas).",
                "Foto bukti dan klip 10 detik sebelum–sesudah, bisa diekspor ke PDF (tengah).",
                "Timeline dari feeder gap → empty pick → kardus di-hold → WhatsApp → rework 20/20, plus corrective action (kanan dan kiri bawah)."],
             "investigasi selesai dalam hitungan menit; bukti siap untuk pelanggan atau audit.", "Line Supervisor, QC Manager, Maintenance"),
            ("06_spesifikasi_kemasan.png", None, "Spesifikasi Kemasan", "Layout slot dan aturan isi diatur per SKU", [
                "Daftar kemasan dengan layout slot (tray 10, kardus 20, dan lain-lain) (tabel kiri).",
                "Layout slot dan tindakan jika isi kurang, feeder gap, atau empty pick (panel kanan).",
                "Uji di rekaman sebelum go-live (PoC: 3/3 kardus, 7/7 tray, 2/2 empty pick) dan hasil per kemasan minggu ini (baris bawah)."],
             "ganti SKU atau kemasan cukup ganti layout, bukan ganti sistem.", "QC Manager"),
            ("07_kamera_alert_integrasi.png", None, "Kamera, Alert & Integrasi", "Kemasan kurang isi dialihkan otomatis, orang yang tepat langsung tahu", [
                "Kamera per line dan station dengan status dan hasil cek gambar (tabel kiri atas).",
                "Aturan alert khusus kemasan (kurang isi, feeder gap berulang, slot yang sama kosong, empty pick) dan eskalasi (kiri tengah dan bawah).",
                "Integrasi PLC/diverter, MES, robot controller, WhatsApp, plus contoh pesan WhatsApp berfoto (kolom kanan)."],
             "line bertindak otomatis, dan Maintenance tahu penyebabnya lebih awal.", "Plant Admin, IT"),
        ],
        proof=["Tray 10 kaleng (simulasi 3D dengan data kebenaran): 7 dari 7 tray benar, 181 dari 181 pembacaan benar.",
               "Kardus 20 item di robot packing station: 3 dari 3 kardus benar, 2 dari 2 empty pick ditemukan, feeder gap terdeteksi lebih dulu.",
               "Yang dibuktikan saat pilot: uji di line nyata dengan kemasan dan pencahayaan pabrik sendiri."],
        qa=[("Kenapa PoC-nya simulasi?", "Supaya setiap slot punya data kebenaran yang pasti untuk mengukur akurasi. Pilot dilakukan di line nyata Anda."),
            ("Bagaimana kalau produknya bertumpuk?", "Dinilai saat line survey; kamera dipasang di titik sebelum kemasan ditutup, saat isinya masih terlihat."),
            ("Apakah line harus diperlambat?", "Tidak. Kamera membaca kemasan yang lewat; kemasan kurang isi dialihkan lewat sinyal ke PLC atau diverter.")],
        pilot="setiap short pack tertahan sebelum disegel, lengkap dengan slot yang kosong; penyebab yang berulang (feeder, lane)",
    ),
    "parcel_dimensioning": dict(
        name="Parcel Dimensioning", colour="#7C3AED", buyer="gudang distribusi, 3PL, e-commerce fulfilment, ekspedisi",
        tagline="Panjang × lebar × tinggi dan volume setiap paket di belt, untuk muat truk dan tagihan berat volumetrik.",
        footnote="Video: Pexels 5370836 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC",
        problem=["Ukuran paket diukur manual dengan meteran, atau tidak diukur sama sekali.",
                 "Tagihan hanya berdasarkan berat timbangan, padahal paket ringan tapi besar memakan ruang truk.",
                 "Rencana muat truk berdasarkan perkiraan, sehingga truk berangkat setengah kosong atau kurang.",
                 "Selisih tagihan dengan pelanggan sulit dibuktikan."],
        flow="kamera di atas belt bongkar/muat → edge AI box mengukur P × L × T setiap paket dan menghitungnya di count line → web app mengelompokkan kelas ukuran dan menghitung berat volumetrik → data ke WMS/TMS dan sistem invoice",
        users="Logistics/Warehouse Manager, supervisor dock, Finance",
        pages=[
            ("01_ringkasan.png", None, "Ringkasan", "Ukuran dan volume setiap paket, tanpa meteran", [
                "Paket terukur hari ini, volume, berat volumetrik, dan paket yang perlu manual check (baris kartu atas).",
                "Log paket: P × L × T, volume, berat volumetrik (P × L × T ÷ 6000), kelas S/M/L (tabel kiri).",
                "Komposisi ukuran, kamera live, dan volume per jam untuk merencanakan truk lebih awal (kanan dan baris bawah)."],
             "data ukuran setiap paket tanpa menambah orang atau memperlambat belt.", "Warehouse/Logistics Manager"),
            ("02_live_monitoring.png", None, "Live Monitoring", "Setiap paket terlihat diukur saat lewat", [
                "Kamera dengan overlay AI: kotak paket, P × L × T, kelas ukuran, dan count line (kamera besar kiri).",
                "Paket terakhir dengan foto dan ukurannya (kanan atas).",
                "Paket yang dekat batas kelas masuk manual check, dengan tombol Konfirmasi atau Ubah kelas (kanan bawah)."],
             "ukuran yang meragukan tidak ditebak, tetapi dikonfirmasi orang.", "supervisor dock, operator belt"),
            ("03_dashboard_tv.png", None, "Dashboard TV", "Satu kamera mengukur P × L × T paket di belt", [
                "Kamera live dengan AI: setiap paket diberi kotak sesuai kelas ukuran dan dihitung di count line (gambar kamera kiri atas).",
                "Tabel paket terukur: P × L × T, volume, berat volumetrik, kelas; paket dekat batas kelas masuk manual check (kanan tengah).",
                "Komposisi ukuran S/M/L dan volume kumulatif, dengan uji vs hitungan manual (baris bawah)."],
             "ukuran yang konsisten, bisa dicek ulang dari fotonya.", "operator belt, supervisor logistik"),
            ("04_muat_tagihan.png", None, "Muat & Tagihan", "Volume terukur dipakai untuk muat truk dan tagihan", [
                "Isi tiap truk dari volume terukur: selesai muat, sedang muat, terjadwal (kiri atas).",
                "Berat volumetrik vs berat aktual per pelanggan; pelanggan dengan paket ringan tapi besar ditagih berdasarkan volume (kanan atas).",
                "Antrean manual check, dasar tagihan per pelanggan, volume per tujuan, dan selisih berat 7 hari, siap dikirim ke TMS/WMS (baris tengah dan bawah)."],
             "truk terisi lebih penuh dan tagihan sesuai ruang yang benar-benar dipakai.", "Logistics Manager, Finance"),
            ("05_kelas_ukuran.png", None, "Kelas Ukuran & Tagihan", "Kelas ukuran, rumus tagihan, dan kalibrasi diatur sendiri", [
                "Batas kelas S/M/L dan kapan paket masuk manual check (kiri atas).",
                "Rumus berat volumetrik (P × L × T ÷ 6000) yang bisa diubah per pelanggan, dan ke mana datanya dikirim (kanan atas).",
                "Kalibrasi kamera dengan karton referensi (PoC: 340,5 mm vs 340 mm) dan uji di rekaman sebelum go-live (baris bawah)."],
             "aturan tagihan transparan dan bisa ditunjukkan ke pelanggan.", "Logistics Manager, Finance"),
            ("06_kamera_alert_integrasi.png", None, "Kamera, Alert & Integrasi", "Data ukuran langsung masuk ke WMS, TMS, dan invoice", [
                "Kamera per belt dan dock dengan status dan hasil cek gambar (tabel kiri atas).",
                "Aturan alert khusus paket (ukuran dekat batas kelas, paket tidak terukur, truk hampir penuh, belt berhenti) dan eskalasi (kiri tengah dan bawah).",
                "Integrasi WMS, TMS, sistem invoice, API, plus contoh pesan WhatsApp berfoto (kolom kanan)."],
             "tidak ada input ulang data ukuran; semua sistem memakai angka yang sama.", "Plant Admin, IT"),
        ],
        proof=["8 paket di belt bongkar truk (rekaman nyata): 8 dari 8 terhitung, sama dengan hitungan manual.",
               "Karton uji yang tidak dipakai untuk kalibrasi terbaca 340,5 mm, aslinya 340 mm.",
               "Laju per jam di layar adalah perkiraan dari klip 17 detik, bukan data satu shift.",
               "Yang dibuktikan saat pilot: akurasi ±1 cm pada 100 paket dibandingkan meteran; isi truk sebelum vs sesudah."],
        qa=[("Perlu kamera 3D atau laser?", "PoC memakai satu kamera biasa yang dikalibrasi dengan karton referensi. Untuk akurasi lebih tinggi, kamera depth bisa ditambahkan saat pilot."),
            ("Bagaimana dengan paket yang tumpang tindih?", "Paket yang tidak terukur jelas ditandai dan masuk antrean manual check, tidak ditebak."),
            ("Bisa tersambung ke sistem kami?", "WMS, TMS, sistem invoice, webhook, dan REST API; data dikirim per paket.")],
        pilot="P × L × T dalam ±1 cm dari meteran pada 100 paket; isi truk sebelum vs sesudah",
    ),
}


def md(slug: str, a: dict) -> str:
    n_tour = len(a["pages"])
    total = 3 + n_tour + 3
    imgs = []
    for p in a["pages"]:
        imgs.append(p[0])
        if p[1]:
            imgs.append(p[1])
    rows = [f"| 1 | Sampul | `{a['pages'][2][0]}` | {a['name']} · {a['tagline']} |",
            "| 2 | Masalah | – | 4 masalah di line hari ini |",
            "| 3 | Solusi & cara kerja | – | alur kamera → edge AI box → web app → tindakan di line |"]
    for k, p in enumerate(a["pages"], 1):
        g = f"`{p[0]}`" + (f" + `{p[1]}` kecil" if p[1] else "")
        rows.append(f"| {3 + k} | Fitur {k}/{n_tour} · {p[2]} | {g} | {p[3]} |")
    rows += [f"| {total - 2} | Ringkasan manfaat | – | 4 manfaat bisnis dan fitur yang mewujudkannya |",
             f"| {total - 1} | Bukti PoC | – | hasil terukur dan batasannya |",
             f"| {total} | Pilot & langkah berikutnya | – | pilot 30 hari, yang disiapkan, keputusan |"]
    tour = []
    for k, p in enumerate(a["pages"], 1):
        g = p[0] + (f" utama, {p[1]} kecil" if p[1] else "")
        pts = "\n".join(f"{i}) {t}" for i, t in enumerate(p[4], 1))
        tour.append(f"{3 + k}. FITUR {k}/{n_tour} · {p[2].upper()}: \"{p[3]}\" ({g})\n{pts}\n"
                    f"Manfaat untuk bisnis: {p[5]}\nDipakai oleh: {p[6]}.")
    problem = "\n".join(f"- {t}" for t in a["problem"])
    proof = "\n".join(f"- {t}" for t in a["proof"])
    qa = "\n".join(f"| {q} | {r} |" for q, r in a["qa"])
    style = COMMON_STYLE.format(colour=a["colour"], n_tour=n_tour, footnote=a["footnote"])
    return f"""# Prompt Claude Design: {a['name']}

Deck produk **{a['name']}**: satu web app, satu cerita, untuk {a['buyer']}. Deck ini berdiri sendiri, dan bisa
digabung dengan deck produk lain (Warehouse Live Ops dan produk pabrik lainnya) karena gayanya sama.

**{a['tagline']}**

## 1. Tentang gambar mockup

- Folder `pages/` berisi {len(imgs)} gambar PNG **3840 × 2160 (4K, 16:9)**, satu gambar per layar web app.
- Templatenya sama dengan mockup warehouse: setiap layar adalah web app atau Dashboard TV milik {a['name']} sendiri,
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

## 3. Daftar slide ({total} slide)

| # | Slide | Gambar (folder `pages/`) | Yang ditonjolkan |
|---|---|---|---|
""" + "\n".join(rows) + f"""

## 4. Cara pakai

1. Buka Claude Design dan mulai proyek presentasi baru (atau buka deck yang akan digabung).
2. Lampirkan {len(imgs)} gambar dari folder `pages/`: {", ".join(f"`{x}`" for x in imgs)}.
3. Tempel prompt di bagian 5. Isi dulu `[Nama tim]` dan `[Tanggal]`.
4. Setelah semua slide jadi, minta ekspor ke PPTX.

## 5. Prompt (tempel ke kolom chat Claude Design)

```text
Buatkan {total} slide presentasi 16:9 berbahasa Indonesia untuk produk "{a['name']}", siap diekspor ke PowerPoint. Tujuan utamanya: calon pembeli MELIHAT web app-nya bekerja, layar demi layar, dan memahami manfaat bisnis setiap layar. Jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC) {a['name']}: {a['tagline']} Penontonnya {a['buyer']} yang sedang memilih sistem video analytics. Mereka bertanya: "Masalah saya yang mana yang selesai, layar apa yang dipakai tim saya, apa yang terjadi di line saat ada masalah, dan apa buktinya?"

{style}

GAMBAR TERLAMPIR
{" · ".join(imgs)}
Jika ada yang tidak terlampir, pakai bingkai placeholder berlabel nama filenya.

PEMBUKA

1. Sampul
- Judul: {a['name']}
- Subjudul: {a['tagline']}
- Teks kecil: Konsep produk · [Nama tim] · [Tanggal]
- Visual: {a['pages'][2][0]} besar dalam bingkai layar TV, sedikit terpotong di sisi kanan.

2. Masalah: "Masalah yang terjadi di line setiap hari"
Empat kartu dengan ikon:
{problem}

3. Solusi & cara kerja: "Dari kamera di line sampai tindakan di line"
- Diagram alur 4 langkah: {a['flow']}.
- Strip "Dipakai oleh": {a['users']}.
- Teks kecil: "Berikut tur {n_tour} layar utama {a['name']}."

TUR PRODUK (satu layar per slide)

""" + "\n\n".join(tour) + f"""

PENUTUP

{total - 2}. Ringkasan manfaat: "Satu sistem, empat manfaat bisnis"
Grid 2×2, tiap kartu berisi manfaat dan layar yang mewujudkannya: lebih sedikit komplain dan reject (Ringkasan, Live Monitoring); bukti untuk setiap keputusan (laporan, detail, foto bukti); standar diatur sendiri ({a['pages'][-2][2]}); tersambung ke line dan sistem yang ada (Kamera, Alert & Integrasi).
Catatan kaki: "Besaran manfaat dihitung bersama klien dari data pilot 30 hari."

{total - 1}. Bukti PoC: "Inti teknologinya sudah diuji"
{proof}

{total}. Langkah berikutnya: "Mulai dengan pilot 30 hari di satu line"
- Yang disiapkan pabrik: titik dudukan dan listrik di titik inspeksi, jaringan ke edge AI box, satu orang QC untuk cek blind, standar atau spec yang dipakai.
- Yang kami siapkan: kamera, lampu, dan edge AI box terpasang dan tersetel; setting standar, limit, dan aturan alert; laporan akurasi di akhir pilot.
- Yang diukur saat pilot: {a['pilot']}.
- Langkah: line survey 1 minggu → pilot 30 hari → go-live 2 minggu → line berikutnya.
- Kalimat penutup tebal: "Harga per line, dihitung setelah line survey."

{COMMON_RULES}
```

## 6. Pegangan tanya jawab

| Pertanyaan | Jawaban singkat |
|---|---|
{qa}
| Apakah kamera harus diganti? | Tidak selalu. Kamera IP yang ada bisa dipakai jika lolos cek gambar (fokus, frame rate, silau, warna). |
| Berapa harganya? | Langganan bulanan per line. Angkanya dihitung setelah line survey. |
| Berapa lama sampai jalan? | Line survey 1 minggu, pilot 30 hari, go-live 2 minggu. |
"""


def main():
    for slug, a in APPS.items():
        out = HERE / "apps" / slug / f"{slug}.md"
        out.write_text(md(slug, a))
        print(out)


if __name__ == "__main__":
    main()
