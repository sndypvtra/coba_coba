# Prompt Claude Design: Fill Level Inspection

Deck produk **Fill Level Inspection**: satu web app, satu cerita, untuk pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol. Deck ini berdiri sendiri, dan bisa
digabung dengan deck produk lain (Warehouse Live Ops dan produk pabrik lainnya) karena gayanya sama.

**Level isi setiap botol terhadap target dan toleransi; underfill di-reject, overfill dihitung sebagai giveaway.**

## 1. Tentang gambar mockup

- Folder `pages/` berisi 6 gambar PNG **3840 × 2160 (4K, 16:9)**, satu gambar per layar web app.
- Templatenya sama dengan mockup warehouse: setiap layar adalah web app atau Dashboard TV milik Fill Level Inspection sendiri,
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
| 1 | Sampul | `03_dashboard_tv.png` | Fill Level Inspection · Level isi setiap botol terhadap target dan toleransi; underfill di-reject, overfill dihitung sebagai giveaway. |
| 2 | Masalah | – | 4 masalah di line hari ini |
| 3 | Solusi & cara kerja | – | alur kamera → edge AI box → web app → tindakan di line |
| 4 | Fitur 1/6 · Ringkasan | `01_ringkasan.png` | Setiap botol dicek; underfill di-reject, overfill dihitung sebagai produk terbuang |
| 5 | Fitur 2/6 · Live Monitoring | `02_live_monitoring.png` | Level isi terlihat langsung di layar, nozzle demi nozzle |
| 6 | Fitur 3/6 · Dashboard TV | `03_dashboard_tv.png` | Level isi diukur setiap frame, selama botol diisi |
| 7 | Fitur 4/6 · Reject & Giveaway | `04_reject_giveaway.png` | Setiap reject punya bukti; setiap mL lebih dihitung |
| 8 | Fitur 5/6 · Spesifikasi SKU | `05_spesifikasi_sku.png` | Target, toleransi, dan tindakan diatur per SKU |
| 9 | Fitur 6/6 · Kamera, Alert & Integrasi | `06_kamera_alert_integrasi.png` | Reject langsung ke PLC, alert langsung ke orang yang tepat |
| 10 | Ringkasan manfaat | – | 4 manfaat bisnis dan fitur yang mewujudkannya |
| 11 | Bukti PoC | – | hasil terukur dan batasannya |
| 12 | Pilot & langkah berikutnya | – | pilot 30 hari, yang disiapkan, keputusan |

## 4. Cara pakai

1. Buka Claude Design dan mulai proyek presentasi baru (atau buka deck yang akan digabung).
2. Lampirkan 6 gambar dari folder `pages/`: `01_ringkasan.png`, `02_live_monitoring.png`, `03_dashboard_tv.png`, `04_reject_giveaway.png`, `05_spesifikasi_sku.png`, `06_kamera_alert_integrasi.png`.
3. Tempel prompt di bagian 5. Isi dulu `[Nama tim]` dan `[Tanggal]`.
4. Setelah semua slide jadi, minta ekspor ke PPTX.

## 5. Prompt (tempel ke kolom chat Claude Design)

```text
Buatkan 12 slide presentasi 16:9 berbahasa Indonesia untuk produk "Fill Level Inspection", siap diekspor ke PowerPoint. Tujuan utamanya: calon pembeli MELIHAT web app-nya bekerja, layar demi layar, dan memahami manfaat bisnis setiap layar. Jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC) Fill Level Inspection: Level isi setiap botol terhadap target dan toleransi; underfill di-reject, overfill dihitung sebagai giveaway. Penontonnya pabrik minuman, sirup, saus, minyak, dan produk cair dalam botol yang sedang memilih sistem video analytics. Mereka bertanya: "Masalah saya yang mana yang selesai, layar apa yang dipakai tim saya, apa yang terjadi di line saat ada masalah, dan apa buktinya?"

GAYA VISUAL
- Sama dengan deck "Warehouse Live Ops": latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, huruf Inter. Warna aksen produk ini: #2563EB (untuk label kecil, ikon, dan garis penanda). Slide 1 dan slide terakhir berlatar navy #0B1220.
- Judul setiap slide berupa kalimat kesimpulan dari sudut pandang pembeli.
- Slide tur produk: screenshot adalah bintangnya. Screenshot utama mengisi minimal 60% lebar slide, utuh dalam bingkai browser (sudut membulat, bayangan halus), jangan dipotong. Teks pendamping di kolom samping (maksimal 35% lebar). Selang-seling posisi screenshot kiri dan kanan.
- Screenshot Dashboard TV (latar gelap) ditaruh dalam bingkai layar TV (bezel tipis, sudut membulat).
- Pada setiap screenshot, pasang 3 penanda bernomor (lingkaran kecil warna aksen) di bagian layar yang dijelaskan, sesuai petunjuk letak dalam kurung di setiap poin.
- Jika ada screenshot kedua, tampilkan lebih kecil (±30% lebar), bertumpuk di pojok screenshot utama dengan bayangan.
- Kolom teks tiap slide tur: label kecil "FITUR n/6 · NAMA LAYAR", judul, 3 poin bernomor, satu baris tebal "Manfaat untuk bisnis", dan baris kecil "Dipakai oleh".
- Catatan kaki kecil di slide yang memuat gambar kamera: "Video: Pexels 8720278 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.

GAMBAR TERLAMPIR
01_ringkasan.png · 02_live_monitoring.png · 03_dashboard_tv.png · 04_reject_giveaway.png · 05_spesifikasi_sku.png · 06_kamera_alert_integrasi.png
Jika ada yang tidak terlampir, pakai bingkai placeholder berlabel nama filenya.

PEMBUKA

1. Sampul
- Judul: Fill Level Inspection
- Subjudul: Level isi setiap botol terhadap target dan toleransi; underfill di-reject, overfill dihitung sebagai giveaway.
- Teks kecil: Konsep produk · [Nama tim] · [Tanggal]
- Visual: 03_dashboard_tv.png besar dalam bingkai layar TV, sedikit terpotong di sisi kanan.

2. Masalah: "Masalah yang terjadi di line setiap hari"
Empat kartu dengan ikon:
- Botol kurang isi lolos ke pasar: risiko komplain dan masalah BDKT.
- Botol lebih isi tidak terukur, padahal itu produk yang diberikan gratis (giveaway) setiap hari.
- Cek manual hanya sampel per jam; nozzle yang bermasalah baru ketahuan belakangan.
- Tinggi cairan tidak sama dengan volume, karena bentuk botol menyempit di dasar dan bahu.

3. Solusi & cara kerja: "Dari kamera di line sampai tindakan di line"
- Diagram alur 4 langkah: kamera samping dengan backlight di mesin pengisi → edge AI box mengukur level isi setiap frame dan mengubahnya jadi volume dari bentuk botol → web app menilai pass/reject per SKU → sinyal reject ke PLC dan laporan giveaway per nozzle.
- Strip "Dipakai oleh": QC Manager, Production Manager, operator filler.
- Teks kecil: "Berikut tur 6 layar utama Fill Level Inspection."

TUR PRODUK (satu layar per slide)

4. FITUR 1/6 · RINGKASAN: "Setiap botol dicek; underfill di-reject, overfill dihitung sebagai produk terbuang" (01_ringkasan.png)
1) Botol diinspeksi, reject underfill, rata-rata overfill dalam mL, dan persentase dalam toleransi (baris kartu atas).
2) Rata-rata isi per nozzle terhadap target dan batas toleransi: nozzle 3 selalu kelebihan isi (grafik kiri).
3) Reject per jam dengan penyebabnya, reject terbaru, dan kamera live (kanan dan baris bawah).
Manfaat untuk bisnis: aman dari komplain isi kurang, dan giveaway per nozzle terukur sehingga bisa dikurangi.
Dipakai oleh: QC Manager, Production Manager.

5. FITUR 2/6 · LIVE MONITORING: "Level isi terlihat langsung di layar, nozzle demi nozzle" (02_live_monitoring.png)
1) Kamera dengan overlay AI: outline botol, garis target di leher botol, level isi dalam % dan mL (kamera besar kiri).
2) Siklus berjalan dan hasil terakhir per nozzle 1–8, dengan nozzle yang bermasalah ditandai (kolom kanan).
3) Tombol hentikan nozzle untuk dicek atau tandai reject manual (kanan bawah).
Manfaat untuk bisnis: supervisor tahu nozzle mana yang bermasalah tanpa menunggu sampel per jam.
Dipakai oleh: Line Supervisor.

6. FITUR 3/6 · DASHBOARD TV: "Level isi diukur setiap frame, selama botol diisi" (03_dashboard_tv.png)
1) Kamera live dengan AI: garis target dan level isi saat ini dalam % dan mL (gambar kamera kiri atas).
2) KPI dan fill curve: level isi, flow rate, waktu isi, sisa waktu ke target (kanan atas).
3) Aturan pass/reject per SKU dan "tinggi bukan volume": tinggi 74% = volume 67% (baris bawah). Catatan jujur: klip PoC berakhir di 67%, jadi belum ada keputusan pass/reject; angka mL memakai contoh SKU 500 mL.
Manfaat untuk bisnis: keputusan isi berdasarkan volume, bukan perkiraan dari tinggi cairan.
Dipakai oleh: operator filler, QC.

7. FITUR 4/6 · REJECT & GIVEAWAY: "Setiap reject punya bukti; setiap mL lebih dihitung" (04_reject_giveaway.png)
1) Reject underfill terbaru per nozzle, dengan status dikonfirmasi QC atau alarm palsu (tabel kiri atas).
2) Giveaway per nozzle terhadap target dan batas toleransi, dengan saran tindakan (grafik kanan atas).
3) Bukti reject (gambar kamera, level saat nozzle berhenti, sinyal ke PLC) dan reject per jam (baris bawah).
Manfaat untuk bisnis: tim teknik tahu nozzle mana yang perlu disetel, berdasarkan data, bukan perasaan.
Dipakai oleh: QC Manager, Maintenance.

8. FITUR 5/6 · SPESIFIKASI SKU: "Target, toleransi, dan tindakan diatur per SKU" (05_spesifikasi_sku.png)
1) Daftar SKU dan aturan isi: target, toleransi 98–102%, reject di bawah 490 mL lewat sinyal PLC dalam 0,5 detik (kiri dan tengah atas).
2) Profil botol dari 3 botol kosong agar tinggi cairan bisa diubah jadi volume; toleransi disesuaikan dengan BDKT dan spec pelanggan (kanan atas).
3) Giveaway per minggu turun setelah garis target dipindah, checklist sebelum go-live, dan riwayat perubahan (baris bawah).
Manfaat untuk bisnis: aturan mutu dan bukti perubahannya tersimpan rapi, siap untuk audit.
Dipakai oleh: QC Manager.

9. FITUR 6/6 · KAMERA, ALERT & INTEGRASI: "Reject langsung ke PLC, alert langsung ke orang yang tepat" (06_kamera_alert_integrasi.png)
1) Kamera per mesin pengisi dengan status dan hasil cek gambar, termasuk kamera yang perlu dicek (tabel kiri atas).
2) Aturan alert khusus pengisian (underfill, reject berulang di satu nozzle, overfill beruntun, kamera silau) dan eskalasi (kiri tengah dan bawah).
3) Integrasi PLC/rejector, check weigher, MES, WhatsApp, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: line bertindak otomatis, dan masalah nozzle tidak menunggu akhir shift.
Dipakai oleh: Plant Admin, IT.

PENUTUP

10. Ringkasan manfaat: "Satu sistem, empat manfaat bisnis"
Grid 2×2, tiap kartu berisi manfaat dan layar yang mewujudkannya: lebih sedikit komplain dan reject (Ringkasan, Live Monitoring); bukti untuk setiap keputusan (laporan, detail, foto bukti); standar diatur sendiri (Spesifikasi SKU); tersambung ke line dan sistem yang ada (Kamera, Alert & Integrasi).
Catatan kaki: "Besaran manfaat dihitung bersama klien dari data pilot 30 hari."

11. Bukti PoC: "Inti teknologinya sudah diuji"
- Level isi diukur setiap frame pada rekaman nyata mesin pengisi, dan bentuk botol diukur sehingga tinggi diubah menjadi volume.
- Klip PoC berakhir di 67% saat botol masih diisi, jadi belum ada keputusan pass/reject; angka mL memakai contoh SKU 500 mL.
- Yang dibuktikan saat pilot: keputusan pass/reject setiap botol dan perbandingan level isi dengan check weigher.

12. Langkah berikutnya: "Mulai dengan pilot 30 hari di satu line"
- Yang disiapkan pabrik: titik dudukan dan listrik di titik inspeksi, jaringan ke edge AI box, satu orang QC untuk cek blind, standar atau spec yang dipakai.
- Yang kami siapkan: kamera, lampu, dan edge AI box terpasang dan tersetel; setting standar, limit, dan aturan alert; laporan akurasi di akhir pilot.
- Yang diukur saat pilot: setiap underfill ter-reject; level isi per nozzle dibandingkan dengan check weigher; giveaway per nozzle.
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
| Apakah perlu kamera khusus? | Kamera industri atau IP biasa cukup, dipasang tetap di samping mesin pengisi; untuk botol bening biasanya perlu backlight. |
| Bagaimana dengan botol berwarna gelap? | Diuji saat line survey; jika level tidak terlihat dari samping, posisi kamera atau lampu disesuaikan. |
| Apa bedanya dengan check weigher? | Check weigher menimbang di ujung line. Fill Level membaca per nozzle saat pengisian, jadi penyebabnya langsung terlihat. Keduanya bisa dibandingkan. |
| Apakah kamera harus diganti? | Tidak selalu. Kamera IP yang ada bisa dipakai jika lolos cek gambar (fokus, frame rate, silau, warna). |
| Berapa harganya? | Langganan bulanan per line. Angkanya dihitung setelah line survey. |
| Berapa lama sampai jalan? | Line survey 1 minggu, pilot 30 hari, go-live 2 minggu. |
