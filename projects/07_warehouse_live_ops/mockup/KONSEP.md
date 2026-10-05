# Warehouse Live Ops: konsep produk & mockup

Bahan presentasi investor: produk apa yang akan dibangun di atas PoC tiga video, siapa memakainya,
fitur apa saja, siapa boleh apa, dan bagaimana produk ini menghasilkan uang.

> **Ini mockup konsep.** Gambar kamera, peta lantai, snapshot insiden, hasil verifikasi kamera dan angka
> akurasi model adalah keluaran PoC pada rekaman NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0). Nama klien,
> nama pengguna, lokasi selain Gudang Simulasi A, dan semua angka bisnis (insiden hari ini, kepatuhan bulan
> ini, tenant, harga, pendapatan) adalah ilustrasi. Setiap halaman menulis hal ini di pojok kanan bawah.

## Satu kalimat

Warehouse Live Ops mengubah CCTV gudang menjadi **satu peta lantai yang hidup**: setiap orang dan forklift
punya posisi dalam meter dan ID yang sama di semua kamera; bahaya (nyaris tertabrak forklift, masuk jalur
forklift, APD tidak lengkap) langsung sampai ke orang yang tepat beserta foto bukti dan kameranya; semua
tercatat untuk laporan K3.

## Produk: 4 tampilan, 5 peran, 96 fitur

| Tampilan | Dipakai oleh | Isi | Jumlah fitur |
|---|---|---|---|
| **Web App** | Admin klien, Supervisor K3, Operator CCTV, Viewer | 12 modul | 48 |
| **Realtime Dashboard** (aplikasi terpisah) | layar ruang kontrol / TV, manajemen | 6 tampilan, berganti otomatis | 24 widget |
| **Konsol Super Admin** | tim kita (vendor) | 5 modul | 20 |
| **Aplikasi Supervisor** (iOS & Android) | supervisor K3 di lantai gudang | 4 fitur, ditambah notifikasi WhatsApp | 4 |

Label **PoC** di mockup = bagian yang sudah berjalan di proof of concept.

### Web App: 12 modul

| # | Modul | Fitur | PoC |
|---|---|---|---|
| 1 | Beranda | ringkasan KPI per shift · insiden yang perlu tindakan · cuplikan kamera langsung · tren & titik rawan | |
| 2 | Live Monitoring | video wall 1 / 4 / 9 / 1+5 · overlay AI (kotak, ID, zona) · **sorotan kamera otomatis** · peringatan langsung | ✓ |
| 3 | Peta Lantai Digital | posisi orang & forklift dalam meter · heatmap · zona & garis hitung · putar ulang 3D | ✓ |
| 4 | Pusat Insiden | triase & penugasan · status & SLA · tandai alarm palsu · aksi massal | |
| 5 | Detail Insiden & Bukti | klip sebelum–sesudah · posisi di peta · tindakan korektif (CAPA) · ekspor bukti PDF | |
| 6 | Pencarian Kejadian | tanya dengan bahasa sehari-hari · filter otomatis · lompat ke rekaman · simpan jadi aturan | ✓ |
| 7 | Laporan & Kepatuhan K3 | laporan shift / minggu / bulan · kepatuhan APD · format SMK3 & ISO 45001 · kirim terjadwal | |
| 8 | Zona & Aturan | gambar zona & garis di peta · aturan siap pakai · jadwal per shift · uji aturan pada rekaman | |
| 9 | Kamera & Kalibrasi | tambah kamera RTSP / ONVIF · **verifikasi posisi otomatis** · kesehatan kamera · kalibrasi 4 titik | ✓ |
| 10 | Notifikasi & Eskalasi | WhatsApp, email, push · matriks eskalasi · webhook / sirene · ringkasan shift | |
| 11 | Pengguna & Peran | undang & atur peran · akses per lokasi · SSO & 2FA · log audit | |
| 12 | Integrasi & Langganan | API & webhook · integrasi WMS / HRIS · langganan & tagihan · ekspor data | |

### Realtime Dashboard: 6 tampilan

Aplikasi terpisah untuk layar besar: tanpa menu, gelap, berganti tampilan tiap 30 detik, dan memanggil
kamera yang relevan ke layar saat ada bahaya. Tiga tampilan pertama adalah video PoC.

| # | Tampilan | Isi | PoC |
|---|---|---|---|
| 1 | Command Center | KPI langsung · video wall + sorotan · peta lantai langsung · feed & lini masa | ✓ video 1 |
| 2 | Fokus Kamera / Zona | satu kamera besar · APD per orang · zona & garis hitung · posisi di denah | ✓ video 2 |
| 3 | Kepatuhan APD | helm & rompi per orang · satu orang lintas kamera · status sistem · feed pelanggaran | ✓ video 3 |
| 4 | Analitik Keselamatan | near miss per jam · titik rawan · pelanggaran per jenis · waktu tanggap | |
| 5 | Analitik Operasional | utilisasi forklift · arus garis hitung · kepadatan zona · orang di lantai | |
| 6 | Multi-lokasi (HQ) | skor per lokasi · peringkat & tren · insiden lintas lokasi · rotasi layar otomatis | |

### Konsol Super Admin: 5 modul

| # | Modul | Fitur |
|---|---|---|
| 1 | Tenant & Langganan | klien, paket & kuota kamera · status pilot · perpanjangan · kesehatan akun |
| 2 | Paket & Fitur | feature flag per tenant · add-on · batas pemakaian · uji beta terbatas |
| 3 | Edge & Model AI | status edge box · rilis model bertahap · rollback · akurasi per lokasi |
| 4 | Kesehatan & Penagihan | uptime & latensi · invoice & MRR · tunggakan · kuota penyimpanan |
| 5 | Dukungan & Audit | tiket dukungan · masuk sebagai tenant (dengan izin) · log audit platform · pengumuman |

### Aplikasi Supervisor: 4 fitur

Push alert dengan foto · tangani insiden di lantai (ambil alih, foto, catatan, selesaikan) · live kamera ·
ringkasan & serah terima shift. Supervisor yang belum memasang aplikasi menerima alert yang sama lewat WhatsApp.

## Peran & hak akses

Ada **Super Admin** dan **Admin**, dengan pembagian tegas: Super Admin mengelola *platform* (semua klien),
Admin mengelola *gudangnya sendiri*. Data tiap klien terpisah (multi-tenant).

| Peran | Siapa | Cakupan | Inti hak aksesnya |
|---|---|---|---|
| **Super Admin** | tim kita (vendor) | semua tenant | tenant, paket, feature flag, edge box, rilis model AI, penagihan, log audit platform. **Tidak** melihat kamera klien kecuali diberi izin oleh Admin tenant: berbatas waktu (maks. 60 menit) dan tercatat di log audit kedua pihak |
| **Admin** | pemilik / manajer gudang, IT | semua lokasi milik tenant | semua menu tenant: pengguna & peran, kamera & kalibrasi, zona & aturan, notifikasi, integrasi & API; melihat tagihan |
| **Supervisor K3** | HSE / kepala shift | lokasi yang ditugaskan | menangani & menutup insiden, CAPA, laporan K3, ekspor bukti; mengusulkan perubahan aturan |
| **Operator CCTV** | ruang kontrol | lokasi yang ditugaskan | live monitoring, konfirmasi / tandai alarm palsu, membuat insiden |
| **Viewer / Manajemen** | direksi, auditor | sesuai izin | dashboard dan laporan, hanya lihat |

Matriks lengkapnya (15 kemampuan × 5 peran) ada di halaman `01_peran_hak_akses.png`.

## Halaman mockup (23)

Semua 1920×1080, siap ditempel di slide 16:9, di `mockup/pages/`.

| # | Halaman | Untuk | Yang ditunjukkan |
|---|---|---|---|
| 00 | Peta produk | investor | 4 tampilan, semua modul & jumlah fitur, 5 peran, alur data CCTV → edge box → cloud → web / TV / HP / WhatsApp |
| 01 | Peran & hak akses | investor | 5 peran, matriks 15 kemampuan, aturan akses Super Admin |
| 02 | Beranda | Admin | KPI shift, kamera teramai, insiden yang perlu tindakan dengan SLA, tren 7 hari, titik rawan, APD per area |
| 03 | Live Monitoring | Operator | video wall 1+5; near miss di CAM 0001 **disorot otomatis**; peta mini; konfirmasi / alarm palsu; lini masa |
| 04 | Peta Lantai Digital | Operator, Supervisor | semua orang & forklift di peta dari 15 kamera, lapisan, zona & garis hitung, replay 3D |
| 05 | Pusat Insiden | Supervisor | tab status, filter, bukti foto, tingkat, penanggung jawab, SLA tanggap, aksi massal |
| 06 | Detail Insiden & Bukti | Supervisor | klip 10 dtk sebelum–sesudah, cuplikan, posisi di peta, CAPA, linimasa AI → WhatsApp → ditangani |
| 07 | Pencarian Kejadian | semua | “orang tanpa rompi di area kerja timur pagi ini” → filter otomatis → hasil berfoto → jadikan aturan |
| 08 | Laporan & Kepatuhan K3 | Admin, Supervisor | KPI bulanan, APD harian vs target, pelanggaran per jenis, near miss per minggu, jam rawan, laporan SMK3 / ISO 45001 terjadwal |
| 09 | Zona & Aturan | Admin | editor zona di peta, aturan per zona dengan ambang & tingkat, tindakan saat terpicu, uji aturan pada rekaman 7 hari |
| 10 | Kamera & Kalibrasi | Admin | 19 kamera, verifikasi posisi **hasil PoC asli** (15 lolos, 4 gagal dengan alasannya), detail CAM 0004 dan langkah perbaikan |
| 11 | Notifikasi & Eskalasi | Admin | saluran, matriks eskalasi per tingkat, ringkasan & jam tenang, pratinjau WhatsApp, riwayat pengiriman |
| 12 | Pengguna & Peran | Admin | pengguna, peran, akses lokasi, 2FA, SSO, log audit (termasuk akses dukungan vendor) |
| 13 | Dashboard · Command Center | ruang kontrol | video 1 dengan penjelasan bernomor |
| 14 | Dashboard · Fokus Kamera | ruang kontrol | video 2 dengan penjelasan bernomor |
| 15 | Dashboard · Kepatuhan APD | ruang kontrol | video 3 dengan penjelasan bernomor |
| 16 | Dashboard · Analitik Keselamatan | manajemen | near miss per jam vs rata-rata, titik rawan, pelanggaran, APD per shift, insiden terbuka |
| 17 | Dashboard · Analitik Operasional | manajemen | orang di lantai hari ini vs kemarin, utilisasi tiap forklift, arus garis hitung, kepadatan zona |
| 18 | Dashboard · Multi-lokasi | HQ | 5 gudang, skor keselamatan, tren 12 minggu, peringkat, yang perlu perhatian |
| 19 | Super Admin · Tenant & Langganan | tim kita | MRR, tenant, kuota kamera, status pilot & tunggakan, detail tenant dengan feature flag |
| 20 | Super Admin · Edge & Model AI | tim kita | armada edge box, latensi alert, registri model dengan **akurasi PoC asli**, rilis bertahap & gerbang rilis |
| 21 | Aplikasi Supervisor | Supervisor | alert di layar kunci, menangani insiden di lantai, ringkasan & serah terima shift |
| 22 | Model bisnis | investor | 3 paket, contoh 1 gudang, biaya sekali & add-on, siapa pembelinya |

## Model bisnis (harga ilustrasi, divalidasi saat pilot)

Langganan per kamera per bulan + sewa edge box + onboarding sekali bayar.

| Paket | Harga | Isi |
|---|---|---|
| Operasional | Rp 250 rb / kamera / bulan | peta lantai & heatmap, hitung orang & garis, utilisasi forklift, kepadatan zona, laporan harian & mingguan, bukti 30 hari, hingga 10 pengguna |
| **Keselamatan** (direkomendasikan) | Rp 450 rb / kamera / bulan | semua di Operasional + near miss orang–forklift, jalur & zona terlarang, kecepatan forklift, APD, sorotan otomatis, WhatsApp & eskalasi, pencarian, laporan SMK3 & ISO 45001, aplikasi supervisor, pengguna tanpa batas |
| Enterprise | per kontrak | semua di Keselamatan + dashboard HQ multi-lokasi, SSO & audit lanjutan, integrasi WMS / HRIS & API, opsi on-premise, SLA 99,9%, model AI khusus lokasi |

| Biaya lain | Harga |
|---|---|
| Edge AI box | Rp 1,5 jt / bulan per 16 kamera (atau beli putus) |
| Onboarding & kalibrasi | Rp 15 jt / lokasi: audit kamera, verifikasi posisi, gambar zona, pelatihan |
| Pilot 30 hari | Rp 25 jt untuk 1 lokasi, ≤ 8 kamera; dikreditkan ke kontrak bila lanjut |
| Add-on | replay 3D, retensi bukti 90 hari, SMS cadangan |

Contoh satu gudang 40 kamera di paket Keselamatan: 40 × Rp 450 rb = Rp 18 jt, ditambah 3 edge box
Rp 4,5 jt, jadi **Rp 22,5 jt per bulan (Rp 270 jt per tahun)**, ditambah onboarding Rp 15 jt.

**Pembeli:** 3PL & distribusi, pabrik dan gudang bahan baku, cold storage, e-commerce fulfilment & DC ritel.
**Pemicu beli:** kewajiban SMK3 (PP 50/2012), audit ISO 45001, klaim kecelakaan & asuransi, forklift yang menganggur.
**Jalan masuk:** pilot 1 lokasi → kontrak lokasi itu → lokasi lain di grup yang sama (land & expand).

## Kenapa bisa laku

1. **Masalah yang sudah ada anggarannya.** Kecelakaan forklift, klaim, dan audit K3 punya pemilik
   (HSE, operasional) dan biaya nyata.
2. **Mulai dari CCTV yang terpasang.** Setiap kamera diuji dulu secara otomatis; yang belum layak diberi
   alasan dan langkah perbaikannya (di PoC: 15 dari 19 lolos), jadi klien tahu sejak awal kamera mana yang bisa dipakai.
3. **Terasa di hari pertama.** Kamera yang melihat bahaya dipanggil ke layar saat alert berbunyi, dan
   supervisor menerima WhatsApp berfoto dalam hitungan detik.
4. **Bukti, bukan sekadar alarm.** Setiap insiden punya klip, posisi di peta, penanggung jawab, SLA dan
   CAPA, siap untuk audit SMK3 / ISO 45001.
5. **Satu peta, bukan 19 layar.** Satu ID per orang di semua kamera membuka analitik operasional
   (utilisasi forklift, arus orang, kepadatan) yang tidak dimiliki VMS biasa: jalan naik kelas dari paket
   Keselamatan ke Operasional dan sebaliknya.
6. **Bahasa Indonesia & WhatsApp.** Antarmuka, pencarian dan notifikasi dalam bahasa sehari-hari di
   lantai gudang.
7. **Akurasi yang terbuka.** Akurasi diukur dan dilaporkan per lokasi; aturan baru diuji pada rekaman
   sebelum diaktifkan sehingga alarm palsu terlihat sebelum mengganggu.
8. **Bisnis berulang yang tumbuh.** Pendapatan bertambah mengikuti jumlah kamera dan lokasi; satu tim
   melayani banyak klien lewat konsol Super Admin.

## Posisi PoC hari ini, apa adanya

| Sudah terbukti (rekaman simulasi berlabel + 1 gudang nyata) | Belum, dan harus dibangun / dibuktikan |
|---|---|
| 15 dari 19 kamera lolos uji posisi otomatis; 4 ditolak dengan alasannya | Orang yang ditemukan baru 46% dari yang tampak ≥ 40 px: detektor yang jadi batas, bukan geometri |
| Posisi orang di peta: 79% titik adalah orang sungguhan, selisih median 0,19 m | 12 dari 13 near miss sungguhan terlewat: orangnya tertutup badan forklift di gambar. Perlu detektor yang dilatih per lokasi dan kamera dari sudut lain |
| Garis hitung: 6 lintasan, semuanya benar; berjalan vs diam 67,4% (kebenaran 67,5%) | Belum real-time di CPU (0,45 dtk per gambar per kamera untuk orang): edge box ber-GPU wajib |
| Forklift: deteksi 16% → 46%, presisi 55% → 77% setelah dilatih di lokasi; utilisasi 62% (sebenarnya 55%) | Web app, dashboard analitik, aplikasi supervisor, notifikasi, super admin: semua masih mockup ini |
| APD (uji buta): helm benar 24 dari 26, rompi 22 dari 28 | Data dari satu gudang simulasi dan satu gudang nyata; pilot di lokasi klien yang menentukan |
| Alarm palsu ngebut 0 dan kerumunan 0; sorotan kamera otomatis, pencarian bahasa Indonesia, replay 3D sudah jalan | Harga dan angka bisnis di mockup masih ilustrasi |

## Rencana membangun end-to-end (usulan)

| Fase | Waktu | Hasil |
|---|---|---|
| 1 · Pilot | bulan 1–2 | 1 lokasi, ≤ 8 kamera, edge box ber-GPU, Realtime Dashboard + WhatsApp, laporan akurasi & baseline keselamatan |
| 2 · MVP | bulan 2–5 | Web App inti: Beranda, Live Monitoring, Peta Lantai, Pusat Insiden, Detail & Bukti, Zona & Aturan, Kamera & Kalibrasi, Notifikasi; peran Admin, Supervisor, Operator |
| 3 · Produk berbayar | bulan 5–8 | Laporan K3, Pencarian, Aplikasi Supervisor, Konsol Super Admin (tenant, paket, edge, penagihan) |
| 4 · Skala | bulan 8–12 | Multi-lokasi / HQ, SSO, API & integrasi WMS, rilis model bertahap, opsi on-premise |

Usulan teknologi: React / Next.js + TypeScript di web, WebSocket untuk data langsung dan WebRTC / HLS untuk
video; backend Python (FastAPI) dengan PostgreSQL + TimescaleDB, Redis, dan object storage untuk klip bukti;
multi-tenant dengan row-level security; edge box ber-GPU yang menjalankan pipeline PoC (deteksi, peta,
aturan) lewat TensorRT / ONNX; WhatsApp Business Platform, FCM / APNs dan email untuk notifikasi; React
Native atau Flutter untuk aplikasi supervisor.

## Membuat ulang gambar

```bash
python mockup/assets.py   # gambar dari PoC (±3 menit; butuh rekaman dari fetch_data.py)
python mockup/build.py    # 23 halaman: html/*.html → pages/*.png (headless Chromium)
```

`build.py --icons` mengambil ulang subset ikon Material Symbols bila ada ikon baru dipakai.
Huruf: Inter (SIL OFL 1.1, `assets/fonts`); ikon: Material Symbols Rounded (Apache 2.0, `mockup/fonts`).
