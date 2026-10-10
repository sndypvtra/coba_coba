# Prompt Claude Design: Pack Count QC

Deck produk **Pack Count QC**: satu web app, satu cerita, untuk pabrik makanan dan minuman kemasan, FMCG, co-packer. Deck ini berdiri sendiri, dan bisa
digabung dengan deck produk lain (Warehouse Live Ops dan produk pabrik lainnya) karena gayanya sama.

**Jumlah isi setiap tray dan kardus sebelum disegel, lengkap dengan slot yang kosong dan penyebabnya.**

## 1. Tentang gambar mockup

- Folder `pages/` berisi 7 gambar PNG **3840 × 2160 (4K, 16:9)**, satu gambar per layar web app.
- Templatenya sama dengan mockup warehouse: setiap layar adalah web app atau Dashboard TV milik Pack Count QC sendiri,
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
| 1 | Sampul | `03_dashboard_tv_tray.png` | Pack Count QC · Jumlah isi setiap tray dan kardus sebelum disegel, lengkap dengan slot yang kosong dan penyebabnya. |
| 2 | Masalah | – | 4 masalah di line hari ini |
| 3 | Solusi & cara kerja | – | alur kamera → edge AI box → web app → tindakan di line |
| 4 | Fitur 1/6 · Ringkasan | `01_ringkasan.png` | Tray dan kardus kurang isi ditahan sebelum disegel |
| 5 | Fitur 2/6 · Live Monitoring | `02_live_monitoring.png` | Setiap tray dan kardus terlihat dihitung, langsung di layar |
| 6 | Fitur 3/6 · Dashboard TV | `03_dashboard_tv_tray.png` + `04_dashboard_tv_packing.png` kecil | Setiap tray dihitung, setiap slot kosong ditandai |
| 7 | Fitur 4/6 · Detail Reject | `05_detail_reject.png` | Setiap reject punya bukti, penyebab, dan tindakan perbaikan |
| 8 | Fitur 5/6 · Spesifikasi Kemasan | `06_spesifikasi_kemasan.png` | Layout slot dan aturan isi diatur per SKU |
| 9 | Fitur 6/6 · Kamera, Alert & Integrasi | `07_kamera_alert_integrasi.png` | Kemasan kurang isi dialihkan otomatis, orang yang tepat langsung tahu |
| 10 | Ringkasan manfaat | – | 4 manfaat bisnis dan fitur yang mewujudkannya |
| 11 | Bukti PoC | – | hasil terukur dan batasannya |
| 12 | Pilot & langkah berikutnya | – | pilot 30 hari, yang disiapkan, keputusan |

## 4. Cara pakai

1. Buka Claude Design dan mulai proyek presentasi baru (atau buka deck yang akan digabung).
2. Lampirkan 7 gambar dari folder `pages/`: `01_ringkasan.png`, `02_live_monitoring.png`, `03_dashboard_tv_tray.png`, `04_dashboard_tv_packing.png`, `05_detail_reject.png`, `06_spesifikasi_kemasan.png`, `07_kamera_alert_integrasi.png`.
3. Tempel prompt di bagian 5. Isi dulu `[Nama tim]` dan `[Tanggal]`.
4. Setelah semua slide jadi, minta ekspor ke PPTX.

## 5. Prompt (tempel ke kolom chat Claude Design)

```text
Buatkan 12 slide presentasi 16:9 berbahasa Indonesia untuk produk "Pack Count QC", siap diekspor ke PowerPoint. Tujuan utamanya: calon pembeli MELIHAT web app-nya bekerja, layar demi layar, dan memahami manfaat bisnis setiap layar. Jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC) Pack Count QC: Jumlah isi setiap tray dan kardus sebelum disegel, lengkap dengan slot yang kosong dan penyebabnya. Penontonnya pabrik makanan dan minuman kemasan, FMCG, co-packer yang sedang memilih sistem video analytics. Mereka bertanya: "Masalah saya yang mana yang selesai, layar apa yang dipakai tim saya, apa yang terjadi di line saat ada masalah, dan apa buktinya?"

GAYA VISUAL
- Sama dengan deck "Warehouse Live Ops": latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, huruf Inter. Warna aksen produk ini: #D97706 (untuk label kecil, ikon, dan garis penanda). Slide 1 dan slide terakhir berlatar navy #0B1220.
- Judul setiap slide berupa kalimat kesimpulan dari sudut pandang pembeli.
- Slide tur produk: screenshot adalah bintangnya. Screenshot utama mengisi minimal 60% lebar slide, utuh dalam bingkai browser (sudut membulat, bayangan halus), jangan dipotong. Teks pendamping di kolom samping (maksimal 35% lebar). Selang-seling posisi screenshot kiri dan kanan.
- Screenshot Dashboard TV (latar gelap) ditaruh dalam bingkai layar TV (bezel tipis, sudut membulat).
- Pada setiap screenshot, pasang 3 penanda bernomor (lingkaran kecil warna aksen) di bagian layar yang dijelaskan, sesuai petunjuk letak dalam kurung di setiap poin.
- Jika ada screenshot kedua, tampilkan lebih kecil (±30% lebar), bertumpuk di pojok screenshot utama dengan bayangan.
- Kolom teks tiap slide tur: label kecil "FITUR n/6 · NAMA LAYAR", judul, 3 poin bernomor, satu baris tebal "Manfaat untuk bisnis", dan baris kecil "Dipakai oleh".
- Catatan kaki kecil di slide yang memuat gambar kamera: "Video: simulasi 3D buatan tim dengan data kebenaran · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.

GAMBAR TERLAMPIR
01_ringkasan.png · 02_live_monitoring.png · 03_dashboard_tv_tray.png · 04_dashboard_tv_packing.png · 05_detail_reject.png · 06_spesifikasi_kemasan.png · 07_kamera_alert_integrasi.png
Jika ada yang tidak terlampir, pakai bingkai placeholder berlabel nama filenya.

PEMBUKA

1. Sampul
- Judul: Pack Count QC
- Subjudul: Jumlah isi setiap tray dan kardus sebelum disegel, lengkap dengan slot yang kosong dan penyebabnya.
- Teks kecil: Konsep produk · [Nama tim] · [Tanggal]
- Visual: 03_dashboard_tv_tray.png besar dalam bingkai layar TV, sedikit terpotong di sisi kanan.

2. Masalah: "Masalah yang terjadi di line setiap hari"
Empat kartu dengan ikon:
- Tray atau kardus kurang isi baru ketahuan setelah ada komplain dari distributor atau konsumen.
- Cek manual hanya sampel; kemasan yang sudah disegel sulit dibuka ulang.
- Penyebab kekurangan (feeder kosong, lane filler, robot) tidak tercatat, jadi masalah berulang.
- Bukti untuk menjawab klaim pelanggan tidak ada.

3. Solusi & cara kerja: "Dari kamera di line sampai tindakan di line"
- Diagram alur 4 langkah: kamera di atas ujung line atau packing station → edge AI box menghitung isi setiap tray/kardus per slot → web app menilai lengkap atau kurang sebelum disegel → hold/divert ke rework, alert, dan penyebabnya dicatat.
- Strip "Dipakai oleh": QC Manager, Line Supervisor, Maintenance.
- Teks kecil: "Berikut tur 6 layar utama Pack Count QC."

TUR PRODUK (satu layar per slide)

4. FITUR 1/6 · RINGKASAN: "Tray dan kardus kurang isi ditahan sebelum disegel" (01_ringkasan.png)
1) Pack diinspeksi, short pack tertangkap, item kurang, dan feeder gap sebagai penyebab (baris kartu atas).
2) Short pack per jam dan slot yang paling sering kosong minggu ini (grafik kiri dan heatmap kanan).
3) Reject & kejadian terbaru berfoto dan dua kamera live (baris bawah).
Manfaat untuk bisnis: komplain "isi kurang" dicegah, dan penyebabnya ketahuan.
Dipakai oleh: QC Manager, Line Supervisor.

5. FITUR 2/6 · LIVE MONITORING: "Setiap tray dan kardus terlihat dihitung, langsung di layar" (02_live_monitoring.png)
1) Kamera dengan overlay AI: jumlah isi, slot kosong dilingkari merah, tray ditandai SHORT (kamera besar kiri).
2) Tray terakhir dan alert terbaru dengan tombol Konfirmasi & reject atau Alarm palsu (kolom kanan).
3) Kardus di packing station, kecepatan robot, dan status feeder (kanan bawah).
Manfaat untuk bisnis: supervisor bertindak sebelum kemasan disegel, bukan setelah komplain.
Dipakai oleh: Line Supervisor.

6. FITUR 3/6 · DASHBOARD TV: "Setiap tray dihitung, setiap slot kosong ditandai" (03_dashboard_tv_tray.png utama, 04_dashboard_tv_packing.png kecil)
1) Kamera live dengan AI: slot kosong dilingkari merah dan tray ditandai SHORT (gambar kamera kiri atas).
2) Posisi kaleng yang kosong dan apakah berulang, menunjuk ke lane filler (kanan tengah).
3) Tray terakhir dengan pass/reject, tray diinspeksi kumulatif, dan Event Log berfoto (baris bawah). Screenshot kecil: robot packing station dengan peta slot kardus dan root cause feeder gap → empty pick → kardus kurang isi.
Manfaat untuk bisnis: bukan hanya "kurang", tetapi juga "kurang di slot mana dan kenapa".
Dipakai oleh: operator line, Line Supervisor.

7. FITUR 4/6 · DETAIL REJECT: "Setiap reject punya bukti, penyebab, dan tindakan perbaikan" (05_detail_reject.png)
1) Peta slot kardus: B2 dan C5 kosong, 18/20, dengan root cause feeder gap (kiri atas).
2) Foto bukti dan klip 10 detik sebelum–sesudah, bisa diekspor ke PDF (tengah).
3) Timeline dari feeder gap → empty pick → kardus di-hold → WhatsApp → rework 20/20, plus corrective action (kanan dan kiri bawah).
Manfaat untuk bisnis: investigasi selesai dalam hitungan menit; bukti siap untuk pelanggan atau audit.
Dipakai oleh: Line Supervisor, QC Manager, Maintenance.

8. FITUR 5/6 · SPESIFIKASI KEMASAN: "Layout slot dan aturan isi diatur per SKU" (06_spesifikasi_kemasan.png)
1) Daftar kemasan dengan layout slot (tray 10, kardus 20, dan lain-lain) (tabel kiri).
2) Layout slot dan tindakan jika isi kurang, feeder gap, atau empty pick (panel kanan).
3) Uji di rekaman sebelum go-live (PoC: 3/3 kardus, 7/7 tray, 2/2 empty pick) dan hasil per kemasan minggu ini (baris bawah).
Manfaat untuk bisnis: ganti SKU atau kemasan cukup ganti layout, bukan ganti sistem.
Dipakai oleh: QC Manager.

9. FITUR 6/6 · KAMERA, ALERT & INTEGRASI: "Kemasan kurang isi dialihkan otomatis, orang yang tepat langsung tahu" (07_kamera_alert_integrasi.png)
1) Kamera per line dan station dengan status dan hasil cek gambar (tabel kiri atas).
2) Aturan alert khusus kemasan (kurang isi, feeder gap berulang, slot yang sama kosong, empty pick) dan eskalasi (kiri tengah dan bawah).
3) Integrasi PLC/diverter, MES, robot controller, WhatsApp, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: line bertindak otomatis, dan Maintenance tahu penyebabnya lebih awal.
Dipakai oleh: Plant Admin, IT.

PENUTUP

10. Ringkasan manfaat: "Satu sistem, empat manfaat bisnis"
Grid 2×2, tiap kartu berisi manfaat dan layar yang mewujudkannya: lebih sedikit komplain dan reject (Ringkasan, Live Monitoring); bukti untuk setiap keputusan (laporan, detail, foto bukti); standar diatur sendiri (Spesifikasi Kemasan); tersambung ke line dan sistem yang ada (Kamera, Alert & Integrasi).
Catatan kaki: "Besaran manfaat dihitung bersama klien dari data pilot 30 hari."

11. Bukti PoC: "Inti teknologinya sudah diuji"
- Tray 10 kaleng (simulasi 3D dengan data kebenaran): 7 dari 7 tray benar, 181 dari 181 pembacaan benar.
- Kardus 20 item di robot packing station: 3 dari 3 kardus benar, 2 dari 2 empty pick ditemukan, feeder gap terdeteksi lebih dulu.
- Yang dibuktikan saat pilot: uji di line nyata dengan kemasan dan pencahayaan pabrik sendiri.

12. Langkah berikutnya: "Mulai dengan pilot 30 hari di satu line"
- Yang disiapkan pabrik: titik dudukan dan listrik di titik inspeksi, jaringan ke edge AI box, satu orang QC untuk cek blind, standar atau spec yang dipakai.
- Yang kami siapkan: kamera, lampu, dan edge AI box terpasang dan tersetel; setting standar, limit, dan aturan alert; laporan akurasi di akhir pilot.
- Yang diukur saat pilot: setiap short pack tertahan sebelum disegel, lengkap dengan slot yang kosong; penyebab yang berulang (feeder, lane).
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
| Kenapa PoC-nya simulasi? | Supaya setiap slot punya data kebenaran yang pasti untuk mengukur akurasi. Pilot dilakukan di line nyata Anda. |
| Bagaimana kalau produknya bertumpuk? | Dinilai saat line survey; kamera dipasang di titik sebelum kemasan ditutup, saat isinya masih terlihat. |
| Apakah line harus diperlambat? | Tidak. Kamera membaca kemasan yang lewat; kemasan kurang isi dialihkan lewat sinyal ke PLC atau diverter. |
| Apakah kamera harus diganti? | Tidak selalu. Kamera IP yang ada bisa dipakai jika lolos cek gambar (fokus, frame rate, silau, warna). |
| Berapa harganya? | Langganan bulanan per line. Angkanya dihitung setelah line survey. |
| Berapa lama sampai jalan? | Line survey 1 minggu, pilot 30 hari, go-live 2 minggu. |
