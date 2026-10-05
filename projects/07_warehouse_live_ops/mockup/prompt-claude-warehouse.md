# Prompt Claude Design: pitch deck Warehouse Live Ops

Deck investor **8 slide**, fokus pada bisnis dan web app. Prompt di bagian 2 berdiri sendiri: semua angka
yang dibutuhkan sudah ada di dalamnya, jadi Claude Design tidak perlu membaca repositori ini.

## 1. Cara pakai

1. Buka Claude Design dan mulai proyek baru (presentasi / slide).
2. Lampirkan 7 gambar dari `mockup/pages/`:

   | File | Dipakai di slide |
   |---|---|
   | `02_beranda.png` | 1 · sampul |
   | `03_live_monitoring.png` | 4 · deteksi & sorot |
   | `21_aplikasi_supervisor.png` | 4 · tindak dari HP |
   | `06_detail_insiden.png` | 4 · bukti |
   | `16_dashboard_analitik_keselamatan.png` | 5 · dashboard TV |
   | `19_superadmin_tenant.png` | 5 · konsol Super Admin |
   | `17_dashboard_analitik_operasional.png` | 6 · utilisasi forklift (opsional) |

3. Tempel prompt di bagian 2 ke kolom chat. Isi dulu `[Nama tim]`, `[Tanggal]` dan `[isi nilai]`, atau biarkan sebagai placeholder.
4. Revisi dengan perintah singkat (contoh di bagian 4).

Alur deck: masalah → solusi → web app → platform & peran → biaya–manfaat klien → model bisnis → bukti & keputusan.

## 2. Prompt (tempel ke kolom chat)

```text
Buatkan pitch deck 16:9 berbahasa Indonesia untuk "Warehouse Live Ops", maksimal 8 slide. Fokus pada nilai bisnis dan web app-nya; jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC): AI membaca CCTV gudang, menaruh setiap orang dan forklift di satu peta lantai digital (dalam meter), lalu memberi peringatan bahaya beserta buktinya. Deck ini untuk investor dan pemilik perusahaan gudang yang akan mendanai pembangunan aplikasinya secara end-to-end. Penontonnya non-teknis: bicaralah soal risiko, biaya, waktu, dan uang.

GAYA VISUAL
- Bersih dan profesional seperti produk SaaS enterprise. Latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, aksen biru #2563EB; slide 1 dan 8 berlatar navy #0B1220. Huruf Inter (atau sans-serif serupa).
- Judul setiap slide berupa kalimat kesimpulan. Satu pesan per slide, maksimal sekitar 6 baris teks; angka kunci dibuat besar.
- Screenshot terlampir ditaruh utuh dalam bingkai browser atau ponsel (sudut membulat, bayangan halus); jangan dipotong sampai teks di layarnya hilang.
- Grafik sederhana: satu sumbu, biru dan abu-abu, nilai ditulis langsung di batang, tanpa efek 3D.
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.
- Slide yang memuat gambar kamera diberi catatan kaki kecil: "Cuplikan kamera: NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0)".
- Harga dan hitungan biaya–manfaat diberi catatan kaki kecil: "Ilustrasi; divalidasi saat pilot 30 hari."

GAMBAR TERLAMPIR (mockup web app)
02_beranda.png · 03_live_monitoring.png · 06_detail_insiden.png · 21_aplikasi_supervisor.png · 16_dashboard_analitik_keselamatan.png · 19_superadmin_tenant.png · 17_dashboard_analitik_operasional.png
Jika ada yang tidak terlampir, pakai bingkai placeholder berlabel nama filenya.

ISI SLIDE

1. Sampul
- Judul: Warehouse Live Ops
- Subjudul: Satu peta lantai yang hidup dari CCTV gudang: lebih aman, lebih efisien, siap audit.
- Teks kecil: Konsep produk & rencana bisnis · [Nama tim] · [Tanggal]
- Visual: 02_beranda.png dalam bingkai browser.

2. Masalah: "CCTV gudang merekam semuanya, tetapi jarang mencegah apa pun"
- Bahaya orang–forklift baru diketahui setelah terjadi; tidak ada yang sanggup menonton belasan layar sepanjang shift.
- Mencari bukti satu kejadian berarti memutar rekaman berjam-jam.
- Laporan K3 dan bukti audit (SMK3 PP 50/2012, ISO 45001) masih disusun manual.
- Utilisasi forklift tidak terukur, sehingga armada bisa berlebih tanpa ketahuan.

3. Solusi: "Warehouse Live Ops mengubah CCTV menjadi peta lantai yang hidup"
- Diagram 4 langkah: CCTV terpasang (diuji otomatis) → kotak AI di gudang (menaruh orang & forklift di peta, dalam meter) → platform cloud (aturan, insiden, bukti, laporan) → web app, layar TV, aplikasi HP & WhatsApp.
- Tiga hasil bisnis: Lebih aman (near miss, jalur forklift, APD, kecepatan) · Lebih efisien (utilisasi forklift, arus & kepadatan orang) · Siap audit (bukti & laporan otomatis).

4. Web app: "Dari bahaya ke tindakan dalam hitungan detik"
Tiga langkah berurutan, masing-masing dengan screenshot:
- Deteksi & sorot: AI menandai near miss, dan kamera yang melihatnya langsung tampil di layar (03_live_monitoring.png).
- Tindak: supervisor menerima WhatsApp/push berfoto dan menanganinya dari HP (21_aplikasi_supervisor.png).
- Buktikan: klip sebelum–sesudah, posisi di peta, penanggung jawab, tindakan korektif, ekspor PDF (06_detail_insiden.png).
- Baris kecil: 12 modul: Beranda, Live Monitoring, Peta Lantai, Pusat Insiden, Bukti, Pencarian, Laporan K3, Zona & Aturan, Kamera & Kalibrasi, Notifikasi, Pengguna & Peran, Integrasi & Langganan.

5. Platform & peran: "Admin mengelola gudangnya, Super Admin mengelola platform"
- Sisi klien: Admin (pengguna, kamera, zona & aturan, notifikasi, laporan, tagihan) · Supervisor K3 (menangani insiden, laporan) · Operator CCTV (memantau, konfirmasi) · Viewer/Manajemen (hanya lihat). Akses dibatasi per lokasi.
- Sisi vendor: Super Admin (klien & langganan, paket & fitur, kotak AI & model, penagihan, dukungan). Kamera klien hanya bisa dilihat dengan izin Admin, maksimal 60 menit, dan tercatat di log audit.
- Strip 4 tampilan: Web App (12 modul) · Dashboard TV realtime (6 tampilan) · Konsol Super Admin (5 modul) · Aplikasi Supervisor (iOS/Android).
- Visual kecil: 16_dashboard_analitik_keselamatan.png dan 19_superadmin_tenant.png.

6. Biaya–manfaat klien: "Untuk gudang 40 kamera, penghematan operasional menutup biaya; keselamatan menjadi nilai tambah"
Contoh: DC 40 kamera, 20 forklift sewaan, 3 shift, paket Keselamatan.
- Biaya: Rp 22,5 jt/bulan (langganan Rp 18 jt + 3 kotak AI Rp 4,5 jt) = Rp 270 jt/tahun, ditambah onboarding Rp 15 jt sekali bayar.
- Manfaat terukur per tahun:
  · Armada forklift: 2 dari 20 unit sewaan dilepas berkat data utilisasi per unit (Rp 11 jt/unit/bulan) → Rp 264 jt
  · Investigasi kejadian: ±37 jam kerja/bulan tidak lagi habis untuk memutar rekaman → Rp 33 jt
  · Laporan K3 & bukti audit: ±3 hari kerja/bulan → Rp 22 jt
  · Kerusakan barang & rak akibat benturan turun 25% → Rp 24 jt
  · Total Rp 343 jt/tahun ≈ 1,3× biaya
- Hasil: tahun pertama hampir impas (3 bulan awal dipakai mengukur baseline), balik modal di bulan ke-14; mulai tahun kedua bersih ±Rp 73 jt/tahun.
- Belum dihitung: setiap kecelakaan serius yang dicegah (contoh Rp 150 jt, setara ±7 bulan langganan), premi asuransi, dan syarat KPI K3 dari klien 3PL.
- Tampilkan sebagai grafik batang horizontal biaya vs manfaat, plus kotak "Belum dihitung". Visual kecil opsional: 17_dashboard_analitik_operasional.png.

7. Model bisnis: "Pendapatan berulang per kamera, tumbuh mengikuti jumlah lokasi"
- Paket per kamera per bulan: Operasional Rp 250 rb (peta, hitung orang, utilisasi forklift, laporan) · Keselamatan Rp 450 rb (+ near miss, jalur & zona, APD, sorotan otomatis, WhatsApp, laporan K3) · Enterprise per kontrak (multi-lokasi, SSO, integrasi WMS, on-premise).
- Tambahan: kotak AI Rp 1,5 jt/bulan per 16 kamera · onboarding Rp 15 jt/lokasi · pilot 30 hari Rp 25 jt (dikreditkan ke kontrak).
- Ekonomi unit: 1 lokasi 40 kamera = Rp 270 jt/tahun pendapatan berulang, margin kotor perkiraan ±64%.
- Skala: 10 lokasi ≈ Rp 2,7 M/tahun · 50 lokasi ≈ Rp 13,5 M/tahun.
- Jalur masuk: pilot 1 gudang → kontrak lokasi itu → lokasi lain dalam grup yang sama. Sasaran: 3PL & distribusi, manufaktur, cold storage, e-commerce fulfilment.

8. Bukti & langkah berikutnya: "Teknologi intinya sudah terbukti; pilot 30 hari membuktikannya di gudang Anda"
- Hasil PoC (rekaman gudang simulasi berlabel lengkap + 1 gudang nyata): 15 dari 19 kamera lolos uji otomatis · posisi orang di peta meleset median 0,19 m · 6 lintasan garis hitung, semuanya benar · utilisasi forklift terukur 62% (sebenarnya 55%) · APD: helm 24 dari 26 dan rompi 22 dari 28 benar pada uji buta · 0 alarm palsu untuk ngebut dan kerumunan.
- Fokus pilot: menangkap near miss saat orang tertutup forklift (di PoC baru 1 dari 13) dan pemrosesan real-time di kotak AI ber-GPU.
- Timeline 12 bulan: Pilot (bulan 1–2) → MVP web app (bulan 2–5) → Laporan K3, aplikasi HP, Super Admin (bulan 5–8) → Multi-lokasi & integrasi (bulan 8–12).
- Keputusan yang diminta: persetujuan pilot di 1 gudang dan anggaran pembangunan [isi nilai].

ATURAN
- Jangan menambah statistik pasar, kutipan, nama/logo klien, atau angka apa pun di luar prompt ini.
- Format angka Indonesia: Rp 22,5 jt; Rp 2,7 M; 0,19 m.
- Tambahkan catatan pembicara 2–3 kalimat untuk setiap slide.
```

## 3. Dasar angka (untuk sesi tanya jawab)

Semua harga dan asumsi klien adalah ilustrasi yang diukur ulang saat pilot 30 hari; angka PoC berasal
dari pengukuran terhadap data kebenaran (lihat README proyek).

### Biaya klien: DC 40 kamera, paket Keselamatan

| Komponen | Hitungan | Per bulan | Per tahun |
|---|---|---|---|
| Langganan | 40 kamera × Rp 450 rb | Rp 18,0 jt | Rp 216 jt |
| Kotak AI (edge box) | 3 × Rp 1,5 jt (1 kotak per 16 kamera) | Rp 4,5 jt | Rp 54 jt |
| **Biaya berulang** | | **Rp 22,5 jt** | **Rp 270 jt** |
| Onboarding & kalibrasi | sekali bayar | | Rp 15 jt (tahun 1) |

### Manfaat terukur: skenario dasar

| Manfaat | Asumsi (ganti dengan data klien) | Per bulan | Per tahun |
|---|---|---|---|
| Armada forklift | 2 dari 20 unit sewaan dilepas atau ditunda; sewa Rp 11 jt/unit/bulan tanpa operator | Rp 22,0 jt | Rp 264 jt |
| Investigasi kejadian | 20 kejadian/bulan; dari ±2 jam memutar rekaman jadi ±10 menit; staf Rp 75 rb/jam (Rp 12 jt/bulan) | Rp 2,75 jt | Rp 33 jt |
| Laporan K3 & audit | dari 4 jadi 1 hari kerja/bulan; Rp 600 rb/hari | Rp 1,8 jt | Rp 22 jt |
| Kerusakan barang & rak | Rp 8 jt/bulan, turun 25% karena jalur dan kecepatan diawasi | Rp 2,0 jt | Rp 24 jt |
| **Total** | | **Rp 28,6 jt** | **Rp 343 jt (1,27× biaya)** |

- **Arus kas tahun 1.** Bulan 1–3 dipakai mengukur baseline, sehingga penghematan forklift belum ada
  (manfaat Rp 6,6 jt/bulan). Mulai bulan 4 manfaat penuh Rp 28,6 jt/bulan.
  - Total tahun 1: manfaat Rp 277 jt, biaya Rp 285 jt, selisih −Rp 8 jt (hampir impas).
  - Balik modal kumulatif terjadi di bulan ke-14.
  - Tahun 2: manfaat Rp 343 jt, biaya Rp 270 jt, bersih +Rp 73 jt.
- **Sensitivitas.**
  - Hanya 1 forklift dilepas: manfaat Rp 211 jt, atau 0,78× biaya. Selisihnya tertutup bila satu kecelakaan serius dicegah.
  - 3 forklift dilepas dan kerusakan turun 40%: manfaat Rp 489 jt, atau 1,8× biaya.
  - Paket Operasional: biaya Rp 174 jt/tahun, manfaat Rp 319 jt dari forklift, investigasi dan laporan, atau 1,8× biaya.
- **Belum dihitung.**
  - Kecelakaan serius yang dicegah. Asumsi contoh Rp 150 jt per kejadian, mencakup henti operasi area, investigasi, pekerja pengganti, kerusakan dan administrasi. Angka ini setara 6,7 bulan langganan.
  - Premi asuransi.
  - Kontrak 3PL yang mensyaratkan KPI K3.
- **Kenapa forklift menjadi pengungkit terbesar.** PoC membuktikan utilisasi bisa diukur per unit: terukur 62% terhadap 55% sebenarnya. Berapa unit yang benar-benar bisa dilepas ditentukan dari data utilisasi 30 hari saat pilot. Untuk armada milik sendiri, manfaatnya berupa penundaan pembelian unit baru.

### Ekonomi unit vendor: 1 lokasi 40 kamera per tahun (perkiraan awal)

| | Per tahun |
|---|---|
| Pendapatan berulang | Rp 270 jt |
| Kotak AI: 3 unit × Rp 30 jt, disusutkan 3 tahun | Rp 30 jt |
| Cloud & penyimpanan bukti | Rp 24 jt |
| Notifikasi (WhatsApp, push, email) | Rp 6 jt |
| Dukungan & customer success | Rp 36 jt |
| **Margin kotor** | **Rp 174 jt (±64%)** |

Onboarding Rp 15 jt per lokasi menutup biaya instalasi dan kalibrasi awal. Skala pendapatan berulang:
10 lokasi ≈ Rp 2,7 M/tahun, 50 lokasi ≈ Rp 13,5 M/tahun.

### Angka PoC yang dikutip di slide 8

| Klaim | Hasil pengukuran |
|---|---|
| Kamera lolos uji otomatis | 15 dari 19; 4 ditolak beserta alasannya |
| Posisi orang di peta | meleset median 0,19 m; 79% titik adalah orang sungguhan |
| Garis hitung | 6 lintasan, semuanya benar |
| Utilisasi forklift | terukur 62%, sebenarnya 55% |
| APD (uji buta, gudang simulasi) | helm benar 24 dari 26, rompi benar 22 dari 28 |
| Alarm palsu | ngebut 0, kerumunan 0 |
| Batasan (fokus pilot) | near miss tertangkap 1 dari 13 karena orang tertutup forklift di gambar; belum real-time di CPU (0,45 detik per gambar) |

## 4. Perintah revisi cepat di Claude Design

- "Ringkas jadi 6 slide: gabungkan slide 2 dengan 3, dan slide 7 dengan 8."
- "Perbesar screenshot di slide 4 dan kurangi teksnya menjadi satu kalimat per langkah."
- "Ubah slide 6 menjadi satu grafik air terjun: biaya, lalu tiap manfaat, lalu selisih bersih."
- "Buat versi tema gelap untuk presentasi di layar besar."
- "Ekspor ke PPTX atau PDF."
