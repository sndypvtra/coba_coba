# Prompt Claude Design: pitch deck Warehouse Live Ops (dengan tur produk)

Deck **18 slide**: 3 pembuka, **11 slide tur produk** (satu fitur per slide, screenshot besar), dan 4 penutup.
Durasinya sekitar 25 menit. **Deck ini tidak memuat angka uang**: tidak ada harga, ROI, penghematan dalam
rupiah, maupun proyeksi pendapatan. Manfaat diceritakan secara kualitatif dan besarannya dihitung bersama
klien dari data pilot 30 hari.

## 1. Kenapa deck 8 slide terasa kurang

- **Hanya 6 dari 23 layar mockup yang tampil.** Beranda, Live Monitoring, Detail Insiden, aplikasi HP,
  dashboard TV dan Super Admin muncul. Peta Lantai, Pusat Insiden, Pencarian, Laporan K3, Zona & Aturan,
  Kamera, Notifikasi, Pengguna & Peran dan Multi-lokasi tidak muncul sama sekali.
- **Layarnya kecil.** Di slide 4, tiga screenshot masing-masing hanya ±28% lebar slide; di slide 5, dua
  screenshot ±24%. Isi layarnya tidak terbaca, sehingga fitur hanya diceritakan, tidak diperlihatkan.
- **Slide 6–8 tanpa layar produk.** Manfaat, model bisnis dan bukti ditulis tanpa memperlihatkan fitur
  yang mewujudkannya.

## 2. Yang diharapkan pemilik bisnis dari deck ini

Dari sudut pandang calon pembeli, deck harus menjawab delapan pertanyaan ini:

1. **"Tunjukkan layarnya."** Saya ingin melihat aplikasi yang akan dipakai tim saya, cukup besar untuk dibaca.
2. **"Ceritakan dalam alur kerja saya."** Pagi hari, ada kejadian, ditangani, dibuktikan, dilaporkan, lalu dievaluasi.
3. **"Apa untungnya di setiap layar?"** Satu kalimat manfaat bisnis per fitur.
4. **"Siapa di tim saya yang memakainya?"** Admin, supervisor K3, operator CCTV, atau manajemen.
5. **"Bisakah tim saya mengaturnya sendiri, dan apakah cocok dengan CCTV saya?"**
6. **"Apakah data saya aman dan terkendali?"** Siapa bisa melihat apa, dan apa yang bisa dilihat vendor.
7. **"Bisa untuk semua lokasi saya?"**
8. **"Apa buktinya, dan apa yang harus saya siapkan untuk mulai?"**

## 3. Struktur 18 slide

Tur produk mengikuti satu hari kerja di gudang: memantau, menindak, membuktikan, melapor, mengevaluasi, mengatur.

| # | Slide | Screenshot | Fitur yang ditonjolkan |
|---|---|---|---|
| 1 | Sampul | `video1_spotlight.jpg` | dashboard ruang kontrol dari PoC |
| 2 | Masalah | – | 4 masalah gudang hari ini |
| 3 | Solusi & cara kerja | – | alur CCTV → kotak AI → cloud → web/TV/HP; 4 tampilan untuk 5 peran |
| 4 | Tur 1 · Beranda | `02_beranda.png` | ringkasan shift, insiden perlu tindakan + SLA, titik rawan |
| 5 | Tur 2 · Live Monitoring | `03_live_monitoring.png` | sorotan kamera otomatis, AI di setiap kamera, konfirmasi / alarm palsu |
| 6 | Tur 3 · Peta Lantai Digital | `04_peta_lantai.png` | semua orang & forklift di satu peta, lapisan zona, replay 3D |
| 7 | Tur 4 · Notifikasi & Aplikasi Supervisor | `21_aplikasi_supervisor.png` + `11_notifikasi_eskalasi.png` | alert berfoto di HP, tangani di lantai, eskalasi, serah terima shift |
| 8 | Tur 5 · Pusat Insiden | `05_pusat_insiden.png` | semua kejadian ditugaskan, status & SLA, aksi massal |
| 9 | Tur 6 · Detail Insiden & Bukti | `06_detail_insiden.png` | klip sebelum–sesudah, linimasa, CAPA, ekspor PDF |
| 10 | Tur 7 · Pencarian Kejadian | `07_pencarian.png` | cari dengan bahasa sehari-hari, jadikan aturan |
| 11 | Tur 8 · Laporan & Kepatuhan K3 | `08_laporan_k3.png` | KPI bulanan, tren APD, laporan SMK3 / ISO 45001 terjadwal |
| 12 | Tur 9 · Analitik & Multi-lokasi | `17_dashboard_analitik_operasional.png` + `18_dashboard_multi_lokasi.png` | pemakaian tiap forklift, arus & kepadatan, semua lokasi |
| 13 | Tur 10 · Zona, Aturan & Kamera | `09_zona_aturan.png` + `10_kamera_kalibrasi.png` | editor zona, aturan siap pakai, uji di rekaman, uji kamera |
| 14 | Tur 11 · Pengguna, Peran & Keamanan | `12_pengguna_peran.png` + `20_superadmin_edge_ai.png` | peran & akses per lokasi, SSO / 2FA, log audit, akses vendor |
| 15 | Ringkasan manfaat | – | 4 manfaat bisnis dan fitur yang mewujudkannya |
| 16 | Model bisnis | – | langganan per kamera, 3 paket, jalur masuk (tanpa harga) |
| 17 | Bukti PoC | – | 6 hasil terukur + fokus pilot |
| 18 | Pilot & keputusan | – | kebutuhan & hasil pilot, timeline 12 bulan, keputusan |

## 4. Cara pakai

1. Buka Claude Design dan mulai proyek presentasi baru.
2. Lampirkan 16 gambar ini (semuanya tanpa angka rupiah):
   - dari `docs/`: `video1_spotlight.jpg`
   - dari `mockup/pages/`: `02_beranda`, `03_live_monitoring`, `04_peta_lantai`, `05_pusat_insiden`,
     `06_detail_insiden`, `07_pencarian`, `08_laporan_k3`, `09_zona_aturan`, `10_kamera_kalibrasi`,
     `11_notifikasi_eskalasi`, `12_pengguna_peran`, `17_dashboard_analitik_operasional`,
     `18_dashboard_multi_lokasi`, `20_superadmin_edge_ai`, `21_aplikasi_supervisor` (semua `.png`)

   Jangan lampirkan `19_superadmin_tenant.png`, `22_model_bisnis.png` atau `KONSEP.md`: ketiganya memuat angka rupiah.
3. Tempel prompt di bagian 5. Isi dulu `[Nama tim]` dan `[Tanggal]`.
4. Jika Claude Design membatasi jumlah lampiran, kerjakan bertahap: slide 1–9 dulu, lalu "lanjutkan slide 10–18" dengan sisa gambar.

## 5. Prompt (tempel ke kolom chat)

```text
Buatkan pitch deck 16:9 berbahasa Indonesia untuk "Warehouse Live Ops" sebanyak 18 slide: 3 slide pembuka, 11 slide tur produk, dan 4 slide penutup. Tujuan utamanya: calon pembeli dan investor MELIHAT web app-nya bekerja, fitur demi fitur, dan memahami manfaat bisnis tiap fitur. Jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC): AI membaca CCTV gudang, menaruh setiap orang dan forklift di satu peta lantai digital (dalam meter), lalu memberi peringatan bahaya beserta buktinya. Deck ini untuk investor dan pemilik perusahaan gudang yang akan mendanai pembangunan aplikasinya secara end-to-end. Bayangkan penontonnya pemilik bisnis yang bertanya: "Layar apa yang akan dipakai tim saya setiap hari, dan apa untungnya untuk bisnis saya?"

GAYA VISUAL
- Bersih dan profesional seperti produk SaaS enterprise. Latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, aksen biru #2563EB; slide 1, 3, 15 dan 18 berlatar navy #0B1220. Huruf Inter (atau sans-serif serupa).
- Judul setiap slide berupa kalimat kesimpulan dari sudut pandang pembeli.
- Slide tur produk: screenshot adalah bintangnya. Screenshot utama mengisi minimal 60% lebar slide dan cukup besar sehingga judul dan angka di layarnya terbaca. Teks pendamping ada di kolom samping (maksimal 35% lebar). Selang-seling posisi screenshot kiri dan kanan antar-slide.
- Pada screenshot utama, pasang 3 penanda bernomor (lingkaran biru kecil) di bagian layar yang dijelaskan, dengan nomor yang sama dengan urutan poin di kolom teks. Petunjuk letaknya ada dalam kurung di setiap poin.
- Jika ada screenshot kedua, tampilkan lebih kecil (±30% lebar) bertumpuk di pojok screenshot utama dengan bayangan; jangan dijajarkan kecil-kecil.
- Kolom teks tiap slide tur berisi: label kecil "TUR PRODUK · n/11", judul, 3 poin bernomor, satu baris tebal "Manfaat untuk bisnis", dan baris kecil "Dipakai oleh".
- Screenshot ditaruh utuh dalam bingkai browser (sudut membulat, bayangan halus); jangan dipotong sampai teks di layarnya hilang.
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.
- Slide yang memuat gambar kamera diberi catatan kaki kecil: "Cuplikan kamera: NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0) · layar mockup, angka ilustrasi".

GAMBAR TERLAMPIR
video1_spotlight.jpg · 02_beranda.png · 03_live_monitoring.png · 04_peta_lantai.png · 21_aplikasi_supervisor.png · 11_notifikasi_eskalasi.png · 05_pusat_insiden.png · 06_detail_insiden.png · 07_pencarian.png · 08_laporan_k3.png · 17_dashboard_analitik_operasional.png · 18_dashboard_multi_lokasi.png · 09_zona_aturan.png · 10_kamera_kalibrasi.png · 12_pengguna_peran.png · 20_superadmin_edge_ai.png
Jika ada yang tidak terlampir, pakai bingkai placeholder berlabel nama filenya.

PEMBUKA

1. Sampul
- Judul: Warehouse Live Ops
- Subjudul: Satu peta lantai yang hidup dari CCTV gudang: lebih aman, lebih efisien, siap audit.
- Teks kecil: Konsep produk & rencana bisnis · [Nama tim] · [Tanggal]
- Visual: video1_spotlight.jpg (dashboard ruang kontrol dari PoC) besar dalam bingkai layar, sedikit terpotong di sisi kanan.

2. Masalah: "CCTV gudang merekam semuanya, tetapi jarang mencegah apa pun"
Empat kartu dengan ikon:
- Bahaya orang–forklift baru diketahui setelah terjadi; tidak ada yang sanggup menonton belasan layar sepanjang shift.
- Mencari bukti satu kejadian berarti memutar rekaman berjam-jam.
- Laporan K3 dan bukti audit (SMK3 PP 50/2012, ISO 45001) masih disusun manual.
- Pemakaian forklift tidak terukur, sehingga armada bisa berlebih tanpa ketahuan.

3. Solusi: "Satu platform, dari CCTV yang terpasang sampai ke tangan orang yang tepat"
- Diagram alur 4 langkah: CCTV terpasang (diuji otomatis) → kotak AI di gudang (menaruh orang & forklift di peta, dalam meter) → platform cloud (aturan, insiden, bukti, laporan) → web app, layar TV, aplikasi HP & WhatsApp.
- Strip "4 tampilan untuk 5 peran": Web App (12 modul) · Dashboard TV ruang kontrol (6 tampilan) · Aplikasi Supervisor (iOS/Android) · Konsol Super Admin (vendor). Peran: Admin, Supervisor K3, Operator CCTV, Viewer/Manajemen, Super Admin.
- Teks kecil: "Berikut tur 11 layar utama, mengikuti satu hari kerja di gudang."

TUR PRODUK (satu fitur per slide)

4. TUR 1/11 · Beranda: "Setiap pagi, kondisi gudang terbaca dalam satu layar" (02_beranda.png)
1) Ringkasan shift: insiden terbuka, near miss, kepatuhan APD, pemakaian forklift, kamera siap pakai (baris kartu di atas).
2) Insiden yang perlu tindakan, diurutkan menurut tingkat dan sisa waktu SLA (kartu di kanan).
3) Kamera teramai, tren 7 hari, titik rawan, dan kepatuhan APD per area (tengah kiri dan baris bawah).
Manfaat untuk bisnis: prioritas hari ini jelas tanpa rapat panjang atau rekap manual.
Dipakai oleh: Admin, manajer gudang.

5. TUR 2/11 · Live Monitoring: "Kamera yang melihat bahaya muncul sendiri di layar" (03_live_monitoring.png)
1) Sorotan otomatis: saat terjadi near miss, kamera yang melihatnya langsung dipanggil ke layar besar berbingkai merah (kiri atas).
2) AI menandai orang, forklift, APD, dan zona di setiap kamera (kotak di semua tayangan).
3) Daftar peringatan dengan tombol Konfirmasi / Alarm palsu, peta mini, dan lini masa kejadian (kolom kanan dan bawah).
Manfaat untuk bisnis: satu operator bisa mengawasi banyak kamera karena AI yang menyaring.
Dipakai oleh: Operator CCTV.

6. TUR 3/11 · Peta Lantai Digital: "Seluruh gudang dalam satu peta, bukan belasan layar" (04_peta_lantai.png)
1) Posisi setiap orang dan forklift dari 15 kamera, dalam meter, dengan ID yang sama di semua kamera (peta besar di kiri).
2) Zona, jalur forklift, garis hitung, dan jangkauan kamera bisa dinyalakan atau dimatikan (tombol di kiri atas peta, tabel di kanan).
3) Putar ulang 3D untuk investigasi dan pelatihan (kanan bawah).
Manfaat untuk bisnis: arus kerja dan titik rawan yang tidak terlihat dari satu kamera menjadi jelas.
Dipakai oleh: Operator CCTV, Supervisor K3.

7. TUR 4/11 · Notifikasi & Aplikasi Supervisor: "Orang yang tepat tahu dalam hitungan detik, di mana pun ia berada" (21_aplikasi_supervisor.png utama, 11_notifikasi_eskalasi.png kecil)
1) Push dan WhatsApp berfoto: apa yang terjadi, di mana, kamera mana (ponsel kiri).
2) Supervisor mengambil alih, menambah foto atau catatan, dan menyelesaikan insiden dari HP (ponsel tengah).
3) Eskalasi otomatis ke manajer bila belum ditanggapi, plus ringkasan dan serah terima shift (ponsel kanan dan screenshot kecil).
Manfaat untuk bisnis: tanggapan cepat tanpa harus duduk di ruang kontrol.
Dipakai oleh: Supervisor K3, kepala shift.

8. TUR 5/11 · Pusat Insiden: "Tidak ada kejadian yang terlewat: semua ditugaskan dan diawasi" (05_pusat_insiden.png)
1) Setiap peringatan menjadi insiden dengan foto bukti, tingkat, lokasi, dan kamera (bagian kiri tabel).
2) Penanggung jawab, status, dan sisa waktu SLA dalam satu daftar (bagian kanan tabel).
3) Filter, tandai alarm palsu, dan aksi massal (baris filter dan bilah gelap di bawah).
Manfaat untuk bisnis: tindak lanjut yang disiplin dan bisa diaudit, tidak bergantung pada ingatan.
Dipakai oleh: Supervisor K3, Admin.

9. TUR 6/11 · Detail Insiden & Bukti: "Setiap kejadian punya bukti lengkap dan tindakan perbaikan" (06_detail_insiden.png)
1) Klip 10 detik sebelum–sesudah, cuplikan, dan posisi di peta (kiri).
2) Linimasa: terdeteksi → notifikasi terkirim → ditangani → catatan (kanan bawah).
3) Tindakan korektif (CAPA) dengan penanggung jawab dan tenggat, plus ekspor bukti PDF (kanan tengah dan tombol di atas).
Manfaat untuk bisnis: investigasi selesai dalam hitungan menit; bukti siap untuk audit, asuransi, atau klien.
Dipakai oleh: Supervisor K3, tim HSE.

10. TUR 7/11 · Pencarian Kejadian: "Cari kejadian seperti bertanya ke rekan kerja" (07_pencarian.png)
1) Ketik dengan bahasa sehari-hari, misalnya "orang tanpa rompi di area kerja timur pagi ini" (kotak cari di atas).
2) Sistem menerjemahkannya menjadi filter jenis, zona, waktu, dan kamera, lalu menampilkan hasil berfoto (label biru dan grid hasil).
3) Pencarian bisa disimpan dan dijadikan aturan peringatan (kolom kanan).
Manfaat untuk bisnis: jam kerja tidak lagi habis untuk memutar rekaman.
Dipakai oleh: semua peran.

11. TUR 8/11 · Laporan & Kepatuhan K3: "Laporan K3 dan bukti audit tersusun sendiri" (08_laporan_k3.png)
1) KPI bulanan: skor keselamatan, near miss, kepatuhan APD, insiden selesai sesuai SLA (baris atas).
2) Tren kepatuhan APD terhadap target, pelanggaran per jenis, dan jam rawan (grafik tengah dan bawah).
3) Laporan terjadwal: akhir shift, mingguan, bulanan SMK3, dan paket bukti audit ISO 45001 (kanan bawah).
Manfaat untuk bisnis: siap audit kapan saja; tim K3 fokus memperbaiki, bukan merekap.
Dipakai oleh: Supervisor K3, manajemen.

12. TUR 9/11 · Analitik & Multi-lokasi: "Manajemen melihat operasional setiap gudang, dan seluruh grup, secara langsung" (17_dashboard_analitik_operasional.png utama, 18_dashboard_multi_lokasi.png kecil)
1) Pemakaian tiap forklift, sehingga unit yang jarang dipakai langsung terlihat (kanan atas).
2) Orang di lantai sepanjang hari, arus di garis hitung, dan kepadatan per zona (kiri dan baris bawah).
3) Semua lokasi dalam satu layar: skor keselamatan, peringkat, dan yang perlu perhatian (screenshot kecil).
Teks kecil: "Tampil juga di layar TV ruang kontrol dan berganti otomatis."
Manfaat untuk bisnis: keputusan armada, tata letak, dan jadwal shift berdasarkan data, bukan perkiraan.
Dipakai oleh: manajemen, kantor pusat.

13. TUR 10/11 · Zona, Aturan & Kamera: "Tim Anda sendiri yang mengatur aturan, tanpa menunggu vendor" (09_zona_aturan.png utama, 10_kamera_kalibrasi.png kecil)
1) Gambar zona dan garis langsung di peta (editor di tengah).
2) Pilih aturan siap pakai (near miss, jalur forklift, kecepatan, APD), tentukan ambang, jadwal shift, dan siapa yang diberi tahu (panel kanan).
3) Uji aturan pada rekaman 7 hari sebelum diaktifkan; setiap kamera diuji otomatis dan yang meleset diberi langkah perbaikan (kanan bawah dan screenshot kecil).
Manfaat untuk bisnis: sistem cepat mengikuti perubahan tata letak gudang, dan alarm palsu ketahuan sebelum mengganggu.
Dipakai oleh: Admin.

14. TUR 11/11 · Pengguna, Peran & Keamanan: "Kendali penuh: siapa melihat apa, dan semuanya tercatat" (12_pengguna_peran.png utama, 20_superadmin_edge_ai.png kecil)
1) Peran Admin, Supervisor K3, Operator CCTV, dan Viewer, dengan akses per lokasi (tabel kiri).
2) SSO, 2FA, keluar otomatis, dan log audit setiap perubahan (kolom kanan).
3) Tim vendor (Super Admin) mengelola kotak AI dan pembaruan model; kamera klien hanya bisa dilihat dengan izin Admin, berbatas waktu, dan tercatat (screenshot kecil).
Manfaat untuk bisnis: data gudang tetap di bawah kendali perusahaan Anda.
Dipakai oleh: Admin, tim IT.

PENUTUP

15. Ringkasan manfaat: "Satu sistem, empat manfaat bisnis"
Grid 2×2; tiap kartu berisi manfaat dan fitur yang mewujudkannya:
- Lebih aman: sorotan otomatis, notifikasi & eskalasi, aturan zona dan kecepatan, kepatuhan APD.
- Lebih efisien: peta lantai, pemakaian tiap forklift, arus dan kepadatan orang, analitik multi-lokasi.
- Siap audit: pusat insiden, bukti & CAPA, laporan K3 terjadwal, log audit.
- Terkendali: zona dan aturan diatur sendiri, uji kamera otomatis, peran & akses per lokasi.
Catatan kaki: "Besaran manfaat dihitung bersama klien dari data pilot 30 hari."

16. Model bisnis: "Pendapatan berulang yang tumbuh mengikuti jumlah kamera dan lokasi"
- Langganan bulanan per kamera dalam tiga paket: Operasional (peta lantai, hitung orang, pemakaian forklift, laporan) · Keselamatan (ditambah near miss, jalur & zona, APD, sorotan otomatis, WhatsApp, laporan K3) · Enterprise (multi-lokasi, SSO, integrasi WMS, opsi on-premise).
- Pendapatan pendukung: sewa kotak AI per lokasi, onboarding & kalibrasi, pilot 30 hari berbayar yang dikreditkan ke kontrak, serta add-on.
- Jalur masuk: pilot 1 gudang → kontrak lokasi itu → lokasi lain dalam grup yang sama. Sasaran awal: 3PL & distribusi, manufaktur, cold storage, e-commerce fulfilment.
Catatan kaki: "Harga disusun setelah pilot."

17. Bukti: "Teknologi intinya sudah terbukti di rekaman gudang"
Enam angka besar dari PoC (rekaman gudang simulasi berlabel lengkap + 1 gudang nyata):
- 15 dari 19 kamera lolos uji otomatis
- posisi orang di peta meleset median 0,19 m
- 6 lintasan garis hitung, semuanya benar
- pemakaian forklift terukur 62% (sebenarnya 55%)
- APD: helm 24 dari 26 dan rompi 22 dari 28 benar pada uji buta
- 0 alarm palsu untuk ngebut dan kerumunan
Kotak "Fokus pilot": menangkap near miss saat orang tertutup forklift (di PoC baru 1 dari 13) dan pemrosesan real-time di kotak AI ber-GPU.

18. Langkah berikutnya: "Mulai dengan pilot 30 hari di satu gudang"
- Yang kami butuhkan dari Anda: akses CCTV (RTSP/ONVIF), tempat dan jaringan untuk kotak AI, satu PIC dari tim K3 atau operasional.
- Yang Anda dapatkan: baseline keselamatan dan pemakaian forklift, laporan akurasi, rekomendasi kamera, rencana implementasi.
- Timeline 12 bulan: Pilot (bulan 1–2) → MVP web app (bulan 2–5) → Laporan K3, aplikasi HP, Super Admin (bulan 5–8) → Multi-lokasi & integrasi (bulan 8–12).
- Keputusan yang diminta: menyetujui pilot di 1 gudang dan mendanai pembangunan end-to-end sesuai timeline.

ATURAN
- Tidak ada angka uang di deck ini: jangan tampilkan rupiah, harga, ROI, persentase penghematan, atau proyeksi pendapatan. Ceritakan manfaat secara kualitatif.
- Jangan menambah statistik pasar, kutipan, nama/logo klien, atau angka dan klaim lain di luar prompt ini.
- Format angka Indonesia: 0,19 m.
- Tambahkan catatan pembicara 2–3 kalimat untuk setiap slide; di slide tur, catatannya berisi cara mendemokan layar itu dalam satu menit.
```

## 6. Pegangan tanya jawab

### Yang diukur saat pilot 30 hari (sebelum vs sesudah)

Besaran manfaat dan harga disepakati bersama klien dari data ini.

- Jumlah near miss dan pejalan kaki yang masuk jalur forklift per shift, beserta titik rawannya.
- Waktu dari kejadian sampai ditanggapi supervisor.
- Pemakaian tiap forklift, termasuk unit yang jarang dipakai.
- Waktu yang dibutuhkan untuk menemukan bukti satu kejadian.
- Kepatuhan APD per area dan per shift.
- Waktu penyusunan laporan K3 dan bukti audit.

### Pertanyaan yang mungkin muncul

| Pertanyaan | Jawaban singkat |
|---|---|
| Berapa penghematannya? | Kami tidak mau menebak. Pilot 30 hari mengukur kondisi sebelum dan sesudah di gudang Anda; dari situ penghematan dihitung bersama. |
| Berapa harganya? | Langganan bulanan per kamera dalam tiga paket. Angkanya disusun setelah pilot, sesuai jumlah kamera dan paket yang dipilih. |
| Apakah CCTV harus diganti? | Kami mulai dari CCTV yang terpasang. Setiap kamera diuji otomatis, dan yang belum layak diberi rekomendasi posisi atau kalibrasi. Di PoC, 15 dari 19 kamera langsung lolos. |
| Seberapa akurat? | Posisi orang di peta meleset median 0,19 m, garis hitung 6 dari 6 benar, dan APD terbaca benar pada uji buta. Yang masih dikejar adalah near miss saat orang tertutup forklift (PoC: 1 dari 13), sehingga ini menjadi fokus pilot. |
| Bagaimana keamanan datanya? | Akses diatur per peran dan per lokasi, dengan SSO / 2FA dan log audit. Tim kami hanya bisa melihat kamera klien dengan izin Admin, berbatas waktu, dan tercatat. |
| Bisakah tim kami mengatur sendiri? | Bisa. Zona, garis dan aturan digambar langsung di peta oleh Admin, lalu diuji pada rekaman 7 hari sebelum diaktifkan. |
| Berapa lama membangunnya? | 12 bulan dalam 4 tahap. Nilai pertama sudah terasa saat pilot di bulan 1–2. |

### Angka PoC yang dikutip di slide 17

| Klaim | Hasil pengukuran |
|---|---|
| Kamera lolos uji otomatis | 15 dari 19; 4 ditolak beserta alasannya |
| Posisi orang di peta | meleset median 0,19 m; 79% titik adalah orang sungguhan |
| Garis hitung | 6 lintasan, semuanya benar |
| Pemakaian (utilisasi) forklift | terukur 62%, sebenarnya 55% |
| APD (uji buta, gudang simulasi) | helm benar 24 dari 26, rompi benar 22 dari 28 |
| Alarm palsu | ngebut 0, kerumunan 0 |
| Batasan (fokus pilot) | near miss tertangkap 1 dari 13 karena orang tertutup forklift di gambar; belum real-time di CPU (0,45 detik per gambar) |

Sumber: pengukuran terhadap data kebenaran, dijelaskan di README proyek.

## 7. Perintah revisi cepat di Claude Design

- Versi lebih pendek (12 slide): "Ringkas jadi 12 slide: gabungkan slide 2+3, 5+6, 8+9, 13+14, 15+16, dan 17+18. Tetap satu pesan per slide dan screenshot utama tetap besar."
- "Perbesar screenshot di slide 4–14 sampai 65% lebar slide; persingkat poin menjadi satu baris."
- "Tambahkan penanda bernomor yang belum ada di screenshot slide tur, sesuai petunjuk letaknya."
- "Buat versi tema gelap untuk presentasi di layar besar."
- "Ekspor ke PPTX atau PDF."
