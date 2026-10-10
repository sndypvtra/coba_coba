# Prompt Claude Design: Parcel Dimensioning

Deck produk **Parcel Dimensioning**: satu web app, satu cerita, untuk gudang distribusi, 3PL, e-commerce fulfilment, ekspedisi. Deck ini berdiri sendiri, dan bisa
digabung dengan deck produk lain (Warehouse Live Ops dan produk pabrik lainnya) karena gayanya sama.

**Panjang × lebar × tinggi dan volume setiap paket di belt, untuk muat truk dan tagihan berat volumetrik.**

## 1. Tentang gambar mockup

- Folder `pages/` berisi 6 gambar PNG **3840 × 2160 (4K, 16:9)**, satu gambar per layar web app.
- Templatenya sama dengan mockup warehouse: setiap layar adalah web app atau Dashboard TV milik Parcel Dimensioning sendiri,
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
| 1 | Sampul | `03_dashboard_tv.png` | Parcel Dimensioning · Panjang × lebar × tinggi dan volume setiap paket di belt, untuk muat truk dan tagihan berat volumetrik. |
| 2 | Masalah | – | 4 masalah di line hari ini |
| 3 | Solusi & cara kerja | – | alur kamera → edge AI box → web app → tindakan di line |
| 4 | Fitur 1/6 · Ringkasan | `01_ringkasan.png` | Ukuran dan volume setiap paket, tanpa meteran |
| 5 | Fitur 2/6 · Live Monitoring | `02_live_monitoring.png` | Setiap paket terlihat diukur saat lewat |
| 6 | Fitur 3/6 · Dashboard TV | `03_dashboard_tv.png` | Satu kamera mengukur P × L × T paket di belt |
| 7 | Fitur 4/6 · Muat & Tagihan | `04_muat_tagihan.png` | Volume terukur dipakai untuk muat truk dan tagihan |
| 8 | Fitur 5/6 · Kelas Ukuran & Tagihan | `05_kelas_ukuran.png` | Kelas ukuran, rumus tagihan, dan kalibrasi diatur sendiri |
| 9 | Fitur 6/6 · Kamera, Alert & Integrasi | `06_kamera_alert_integrasi.png` | Data ukuran langsung masuk ke WMS, TMS, dan invoice |
| 10 | Ringkasan manfaat | – | 4 manfaat bisnis dan fitur yang mewujudkannya |
| 11 | Bukti PoC | – | hasil terukur dan batasannya |
| 12 | Pilot & langkah berikutnya | – | pilot 30 hari, yang disiapkan, keputusan |

## 4. Cara pakai

1. Buka Claude Design dan mulai proyek presentasi baru (atau buka deck yang akan digabung).
2. Lampirkan 6 gambar dari folder `pages/`: `01_ringkasan.png`, `02_live_monitoring.png`, `03_dashboard_tv.png`, `04_muat_tagihan.png`, `05_kelas_ukuran.png`, `06_kamera_alert_integrasi.png`.
3. Tempel prompt di bagian 5. Isi dulu `[Nama tim]` dan `[Tanggal]`.
4. Setelah semua slide jadi, minta ekspor ke PPTX.

## 5. Prompt (tempel ke kolom chat Claude Design)

```text
Buatkan 12 slide presentasi 16:9 berbahasa Indonesia untuk produk "Parcel Dimensioning", siap diekspor ke PowerPoint. Tujuan utamanya: calon pembeli MELIHAT web app-nya bekerja, layar demi layar, dan memahami manfaat bisnis setiap layar. Jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC) Parcel Dimensioning: Panjang × lebar × tinggi dan volume setiap paket di belt, untuk muat truk dan tagihan berat volumetrik. Penontonnya gudang distribusi, 3PL, e-commerce fulfilment, ekspedisi yang sedang memilih sistem video analytics. Mereka bertanya: "Masalah saya yang mana yang selesai, layar apa yang dipakai tim saya, apa yang terjadi di line saat ada masalah, dan apa buktinya?"

GAYA VISUAL
- Sama dengan deck "Warehouse Live Ops": latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, huruf Inter. Warna aksen produk ini: #7C3AED (untuk label kecil, ikon, dan garis penanda). Slide 1 dan slide terakhir berlatar navy #0B1220.
- Judul setiap slide berupa kalimat kesimpulan dari sudut pandang pembeli.
- Slide tur produk: screenshot adalah bintangnya. Screenshot utama mengisi minimal 60% lebar slide, utuh dalam bingkai browser (sudut membulat, bayangan halus), jangan dipotong. Teks pendamping di kolom samping (maksimal 35% lebar). Selang-seling posisi screenshot kiri dan kanan.
- Screenshot Dashboard TV (latar gelap) ditaruh dalam bingkai layar TV (bezel tipis, sudut membulat).
- Pada setiap screenshot, pasang 3 penanda bernomor (lingkaran kecil warna aksen) di bagian layar yang dijelaskan, sesuai petunjuk letak dalam kurung di setiap poin.
- Jika ada screenshot kedua, tampilkan lebih kecil (±30% lebar), bertumpuk di pojok screenshot utama dengan bayangan.
- Kolom teks tiap slide tur: label kecil "FITUR n/6 · NAMA LAYAR", judul, 3 poin bernomor, satu baris tebal "Manfaat untuk bisnis", dan baris kecil "Dipakai oleh".
- Catatan kaki kecil di slide yang memuat gambar kamera: "Video: Pexels 5370836 (lisensi Pexels) · layar mockup, angka ilustrasi kecuali yang bertanda PoC"
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.

GAMBAR TERLAMPIR
01_ringkasan.png · 02_live_monitoring.png · 03_dashboard_tv.png · 04_muat_tagihan.png · 05_kelas_ukuran.png · 06_kamera_alert_integrasi.png
Jika ada yang tidak terlampir, pakai bingkai placeholder berlabel nama filenya.

PEMBUKA

1. Sampul
- Judul: Parcel Dimensioning
- Subjudul: Panjang × lebar × tinggi dan volume setiap paket di belt, untuk muat truk dan tagihan berat volumetrik.
- Teks kecil: Konsep produk · [Nama tim] · [Tanggal]
- Visual: 03_dashboard_tv.png besar dalam bingkai layar TV, sedikit terpotong di sisi kanan.

2. Masalah: "Masalah yang terjadi di line setiap hari"
Empat kartu dengan ikon:
- Ukuran paket diukur manual dengan meteran, atau tidak diukur sama sekali.
- Tagihan hanya berdasarkan berat timbangan, padahal paket ringan tapi besar memakan ruang truk.
- Rencana muat truk berdasarkan perkiraan, sehingga truk berangkat setengah kosong atau kurang.
- Selisih tagihan dengan pelanggan sulit dibuktikan.

3. Solusi & cara kerja: "Dari kamera di line sampai tindakan di line"
- Diagram alur 4 langkah: kamera di atas belt bongkar/muat → edge AI box mengukur P × L × T setiap paket dan menghitungnya di count line → web app mengelompokkan kelas ukuran dan menghitung berat volumetrik → data ke WMS/TMS dan sistem invoice.
- Strip "Dipakai oleh": Logistics/Warehouse Manager, supervisor dock, Finance.
- Teks kecil: "Berikut tur 6 layar utama Parcel Dimensioning."

TUR PRODUK (satu layar per slide)

4. FITUR 1/6 · RINGKASAN: "Ukuran dan volume setiap paket, tanpa meteran" (01_ringkasan.png)
1) Paket terukur hari ini, volume, berat volumetrik, dan paket yang perlu manual check (baris kartu atas).
2) Log paket: P × L × T, volume, berat volumetrik (P × L × T ÷ 6000), kelas S/M/L (tabel kiri).
3) Komposisi ukuran, kamera live, dan volume per jam untuk merencanakan truk lebih awal (kanan dan baris bawah).
Manfaat untuk bisnis: data ukuran setiap paket tanpa menambah orang atau memperlambat belt.
Dipakai oleh: Warehouse/Logistics Manager.

5. FITUR 2/6 · LIVE MONITORING: "Setiap paket terlihat diukur saat lewat" (02_live_monitoring.png)
1) Kamera dengan overlay AI: kotak paket, P × L × T, kelas ukuran, dan count line (kamera besar kiri).
2) Paket terakhir dengan foto dan ukurannya (kanan atas).
3) Paket yang dekat batas kelas masuk manual check, dengan tombol Konfirmasi atau Ubah kelas (kanan bawah).
Manfaat untuk bisnis: ukuran yang meragukan tidak ditebak, tetapi dikonfirmasi orang.
Dipakai oleh: supervisor dock, operator belt.

6. FITUR 3/6 · DASHBOARD TV: "Satu kamera mengukur P × L × T paket di belt" (03_dashboard_tv.png)
1) Kamera live dengan AI: setiap paket diberi kotak sesuai kelas ukuran dan dihitung di count line (gambar kamera kiri atas).
2) Tabel paket terukur: P × L × T, volume, berat volumetrik, kelas; paket dekat batas kelas masuk manual check (kanan tengah).
3) Komposisi ukuran S/M/L dan volume kumulatif, dengan uji vs hitungan manual (baris bawah).
Manfaat untuk bisnis: ukuran yang konsisten, bisa dicek ulang dari fotonya.
Dipakai oleh: operator belt, supervisor logistik.

7. FITUR 4/6 · MUAT & TAGIHAN: "Volume terukur dipakai untuk muat truk dan tagihan" (04_muat_tagihan.png)
1) Isi tiap truk dari volume terukur: selesai muat, sedang muat, terjadwal (kiri atas).
2) Berat volumetrik vs berat aktual per pelanggan; pelanggan dengan paket ringan tapi besar ditagih berdasarkan volume (kanan atas).
3) Antrean manual check, dasar tagihan per pelanggan, volume per tujuan, dan selisih berat 7 hari, siap dikirim ke TMS/WMS (baris tengah dan bawah).
Manfaat untuk bisnis: truk terisi lebih penuh dan tagihan sesuai ruang yang benar-benar dipakai.
Dipakai oleh: Logistics Manager, Finance.

8. FITUR 5/6 · KELAS UKURAN & TAGIHAN: "Kelas ukuran, rumus tagihan, dan kalibrasi diatur sendiri" (05_kelas_ukuran.png)
1) Batas kelas S/M/L dan kapan paket masuk manual check (kiri atas).
2) Rumus berat volumetrik (P × L × T ÷ 6000) yang bisa diubah per pelanggan, dan ke mana datanya dikirim (kanan atas).
3) Kalibrasi kamera dengan karton referensi (PoC: 340,5 mm vs 340 mm) dan uji di rekaman sebelum go-live (baris bawah).
Manfaat untuk bisnis: aturan tagihan transparan dan bisa ditunjukkan ke pelanggan.
Dipakai oleh: Logistics Manager, Finance.

9. FITUR 6/6 · KAMERA, ALERT & INTEGRASI: "Data ukuran langsung masuk ke WMS, TMS, dan invoice" (06_kamera_alert_integrasi.png)
1) Kamera per belt dan dock dengan status dan hasil cek gambar (tabel kiri atas).
2) Aturan alert khusus paket (ukuran dekat batas kelas, paket tidak terukur, truk hampir penuh, belt berhenti) dan eskalasi (kiri tengah dan bawah).
3) Integrasi WMS, TMS, sistem invoice, API, plus contoh pesan WhatsApp berfoto (kolom kanan).
Manfaat untuk bisnis: tidak ada input ulang data ukuran; semua sistem memakai angka yang sama.
Dipakai oleh: Plant Admin, IT.

PENUTUP

10. Ringkasan manfaat: "Satu sistem, empat manfaat bisnis"
Grid 2×2, tiap kartu berisi manfaat dan layar yang mewujudkannya: lebih sedikit komplain dan reject (Ringkasan, Live Monitoring); bukti untuk setiap keputusan (laporan, detail, foto bukti); standar diatur sendiri (Kelas Ukuran & Tagihan); tersambung ke line dan sistem yang ada (Kamera, Alert & Integrasi).
Catatan kaki: "Besaran manfaat dihitung bersama klien dari data pilot 30 hari."

11. Bukti PoC: "Inti teknologinya sudah diuji"
- 8 paket di belt bongkar truk (rekaman nyata): 8 dari 8 terhitung, sama dengan hitungan manual.
- Karton uji yang tidak dipakai untuk kalibrasi terbaca 340,5 mm, aslinya 340 mm.
- Laju per jam di layar adalah perkiraan dari klip 17 detik, bukan data satu shift.
- Yang dibuktikan saat pilot: akurasi ±1 cm pada 100 paket dibandingkan meteran; isi truk sebelum vs sesudah.

12. Langkah berikutnya: "Mulai dengan pilot 30 hari di satu line"
- Yang disiapkan pabrik: titik dudukan dan listrik di titik inspeksi, jaringan ke edge AI box, satu orang QC untuk cek blind, standar atau spec yang dipakai.
- Yang kami siapkan: kamera, lampu, dan edge AI box terpasang dan tersetel; setting standar, limit, dan aturan alert; laporan akurasi di akhir pilot.
- Yang diukur saat pilot: P × L × T dalam ±1 cm dari meteran pada 100 paket; isi truk sebelum vs sesudah.
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
| Perlu kamera 3D atau laser? | PoC memakai satu kamera biasa yang dikalibrasi dengan karton referensi. Untuk akurasi lebih tinggi, kamera depth bisa ditambahkan saat pilot. |
| Bagaimana dengan paket yang tumpang tindih? | Paket yang tidak terukur jelas ditandai dan masuk antrean manual check, tidak ditebak. |
| Bisa tersambung ke sistem kami? | WMS, TMS, sistem invoice, webhook, dan REST API; data dikirim per paket. |
| Apakah kamera harus diganti? | Tidak selalu. Kamera IP yang ada bisa dipakai jika lolos cek gambar (fokus, frame rate, silau, warna). |
| Berapa harganya? | Langganan bulanan per line. Angkanya dihitung setelah line survey. |
| Berapa lama sampai jalan? | Line survey 1 minggu, pilot 30 hari, go-live 2 minggu. |
