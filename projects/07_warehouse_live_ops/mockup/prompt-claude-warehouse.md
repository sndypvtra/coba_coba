# Prompt Claude Design: pitch deck Warehouse Live Ops

Deck investor **8 slide** yang fokus pada bisnis dan web app. **Deck ini tidak memuat angka uang**: tidak ada
harga, ROI, penghematan dalam rupiah, maupun proyeksi pendapatan. Manfaat diceritakan secara kualitatif.
Besarannya baru dihitung bersama klien dari data pilot 30 hari.

Prompt di bagian 2 bisa langsung dipakai: semua isi yang dibutuhkan sudah ada di dalamnya, jadi Claude
Design tidak perlu membaca repositori ini.

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
   | `20_superadmin_edge_ai.png` | 5 · konsol Super Admin |
   | `17_dashboard_analitik_operasional.png` | 6 · utilisasi forklift (opsional) |

   Jangan lampirkan `19_superadmin_tenant.png`, `22_model_bisnis.png` atau `KONSEP.md`: ketiganya memuat
   angka rupiah.
3. Tempel prompt di bagian 2 ke kolom chat. Isi dulu `[Nama tim]` dan `[Tanggal]`.
4. Revisi dengan perintah singkat (contoh di bagian 4).

Alur deck: masalah → solusi → web app → platform & peran → manfaat untuk klien → model bisnis → bukti & keputusan.

## 2. Prompt (tempel ke kolom chat)

```text
Buatkan pitch deck 16:9 berbahasa Indonesia untuk "Warehouse Live Ops", maksimal 8 slide. Fokus pada nilai bisnis dan web app-nya; jangan bahas detail teknis AI (model, algoritma, kode).

KONTEKS
Tim kami sudah membuat proof of concept (PoC): AI membaca CCTV gudang, menaruh setiap orang dan forklift di satu peta lantai digital (dalam meter), lalu memberi peringatan bahaya beserta buktinya. Deck ini untuk investor dan pemilik perusahaan gudang yang akan mendanai pembangunan aplikasinya secara end-to-end. Penontonnya non-teknis: ceritakan risiko yang berkurang, waktu yang dihemat, dan keputusan yang menjadi lebih mudah.

GAYA VISUAL
- Bersih dan profesional seperti produk SaaS enterprise. Latar putih atau abu sangat muda (#F3F5F8), teks #0F172A dan #475569, aksen biru #2563EB; slide 1 dan 8 berlatar navy #0B1220. Huruf Inter (atau sans-serif serupa).
- Judul setiap slide berupa kalimat kesimpulan. Satu pesan per slide, maksimal sekitar 6 baris teks.
- Screenshot terlampir ditaruh utuh dalam bingkai browser atau ponsel (sudut membulat, bayangan halus); jangan dipotong sampai teks di layarnya hilang.
- Ikon garis sederhana. Jangan memakai logo perusahaan nyata.
- Slide yang memuat gambar kamera diberi catatan kaki kecil: "Cuplikan kamera: NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0)".
- Slide 6 dan 7 diberi catatan kaki kecil: "Besaran manfaat dan harga dihitung bersama klien dari data pilot 30 hari."

GAMBAR TERLAMPIR (mockup web app)
02_beranda.png · 03_live_monitoring.png · 06_detail_insiden.png · 21_aplikasi_supervisor.png · 16_dashboard_analitik_keselamatan.png · 20_superadmin_edge_ai.png · 17_dashboard_analitik_operasional.png
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
- Pemakaian forklift tidak terukur, sehingga armada bisa berlebih tanpa ketahuan.

3. Solusi: "Warehouse Live Ops mengubah CCTV menjadi peta lantai yang hidup"
- Diagram 4 langkah: CCTV terpasang (diuji otomatis) → kotak AI di gudang (menaruh orang & forklift di peta, dalam meter) → platform cloud (aturan, insiden, bukti, laporan) → web app, layar TV, aplikasi HP & WhatsApp.
- Tiga hasil bisnis: Lebih aman (near miss, jalur forklift, APD, kecepatan) · Lebih efisien (pemakaian forklift, arus & kepadatan orang) · Siap audit (bukti & laporan otomatis).

4. Web app: "Dari bahaya ke tindakan dalam hitungan detik"
Tiga langkah berurutan, masing-masing dengan screenshot:
- Deteksi & sorot: AI menandai near miss, dan kamera yang melihatnya langsung tampil di layar (03_live_monitoring.png).
- Tindak: supervisor menerima WhatsApp/push berfoto dan menanganinya dari HP (21_aplikasi_supervisor.png).
- Buktikan: klip sebelum–sesudah, posisi di peta, penanggung jawab, tindakan korektif, ekspor PDF (06_detail_insiden.png).
- Baris kecil: 12 modul: Beranda, Live Monitoring, Peta Lantai, Pusat Insiden, Bukti, Pencarian, Laporan K3, Zona & Aturan, Kamera & Kalibrasi, Notifikasi, Pengguna & Peran, Integrasi & Langganan.

5. Platform & peran: "Admin mengelola gudangnya, Super Admin mengelola platform"
- Sisi klien: Admin (pengguna, kamera, zona & aturan, notifikasi, laporan, tagihan) · Supervisor K3 (menangani insiden, laporan) · Operator CCTV (memantau, konfirmasi) · Viewer/Manajemen (hanya lihat). Akses dibatasi per lokasi.
- Sisi vendor: Super Admin (klien & langganan, paket & fitur, kotak AI & model, penagihan, dukungan). Kamera klien hanya bisa dilihat dengan izin Admin, berbatas waktu, dan tercatat di log audit.
- Strip 4 tampilan: Web App (12 modul) · Dashboard TV realtime (6 tampilan) · Konsol Super Admin (5 modul) · Aplikasi Supervisor (iOS/Android).
- Visual kecil: 16_dashboard_analitik_keselamatan.png (dashboard TV) dan 20_superadmin_edge_ai.png (konsol Super Admin).

6. Manfaat untuk klien: "Manfaatnya terasa di keselamatan, operasional, dan kepatuhan"
Tampilkan sebagai tabel dua kolom, "Sebelum" → "Dengan Warehouse Live Ops":
- Bahaya orang–forklift diketahui setelah terjadi → peringatan dan kamera yang melihatnya muncul saat kejadian; supervisor langsung tahu lokasinya.
- Bukti dicari dengan memutar rekaman berjam-jam → klip, foto, dan posisi di peta tersedia dalam beberapa klik.
- Laporan K3 dan bukti audit disusun manual → laporan harian sampai bulanan dan paket bukti audit tersusun otomatis.
- Pemakaian forklift berdasarkan perkiraan → pemakaian tiap unit terukur, sehingga armada bisa disesuaikan dengan kebutuhan nyata.
- Belasan layar CCTV ditonton bergantian → AI menyaring kejadian; operator fokus pada yang perlu tindakan.
Di bawah tabel, empat hasil bisnis dengan ikon: Risiko kecelakaan & henti operasi berkurang · Biaya armada dan administrasi lebih efisien · Siap audit SMK3 / ISO 45001 · Data lantai gudang untuk keputusan manajemen.
Visual kecil opsional: 17_dashboard_analitik_operasional.png (pemakaian per forklift).

7. Model bisnis: "Pendapatan berulang yang tumbuh mengikuti jumlah kamera dan lokasi"
- Langganan bulanan per kamera dalam tiga paket: Operasional (peta lantai, hitung orang, pemakaian forklift, laporan) · Keselamatan (ditambah near miss, jalur & zona, APD, sorotan otomatis, WhatsApp, laporan K3) · Enterprise (multi-lokasi, SSO, integrasi WMS, opsi on-premise).
- Pendapatan pendukung: sewa kotak AI per lokasi, onboarding & kalibrasi, pilot 30 hari berbayar yang dikreditkan ke kontrak, serta add-on.
- Jalur masuk: pilot 1 gudang → kontrak lokasi itu → lokasi lain dalam grup yang sama.
- Sasaran awal: 3PL & distribusi, manufaktur, cold storage, e-commerce fulfilment.
- Skalabel: satu tim melayani banyak klien lewat Konsol Super Admin; fitur dibuka per paket tanpa pemasangan ulang.

8. Bukti & langkah berikutnya: "Teknologi intinya sudah terbukti; pilot 30 hari membuktikannya di gudang Anda"
- Hasil PoC (rekaman gudang simulasi berlabel lengkap + 1 gudang nyata): 15 dari 19 kamera lolos uji otomatis · posisi orang di peta meleset median 0,19 m · 6 lintasan garis hitung, semuanya benar · pemakaian forklift terukur 62% (sebenarnya 55%) · APD: helm 24 dari 26 dan rompi 22 dari 28 benar pada uji buta · 0 alarm palsu untuk ngebut dan kerumunan.
- Fokus pilot: menangkap near miss saat orang tertutup forklift (di PoC baru 1 dari 13) dan pemrosesan real-time di kotak AI ber-GPU.
- Timeline 12 bulan: Pilot (bulan 1–2) → MVP web app (bulan 2–5) → Laporan K3, aplikasi HP, Super Admin (bulan 5–8) → Multi-lokasi & integrasi (bulan 8–12).
- Keputusan yang diminta: menyetujui pilot di 1 gudang dan mendanai pembangunan end-to-end sesuai timeline.

ATURAN
- Tidak ada angka uang di deck ini: jangan tampilkan rupiah, harga, ROI, persentase penghematan, atau proyeksi pendapatan. Ceritakan manfaat secara kualitatif.
- Jangan menambah statistik pasar, kutipan, nama/logo klien, atau angka dan klaim lain di luar prompt ini.
- Format angka Indonesia: 0,19 m.
- Tambahkan catatan pembicara 2–3 kalimat untuk setiap slide.
```

## 3. Pegangan tanya jawab

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
| Berapa lama membangunnya? | 12 bulan dalam 4 tahap. Nilai pertama sudah terasa saat pilot di bulan 1–2. |

### Angka PoC yang dikutip di slide 8

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

## 4. Perintah revisi cepat di Claude Design

- "Ringkas jadi 6 slide: gabungkan slide 2 dengan 3, dan slide 7 dengan 8."
- "Perbesar screenshot di slide 4 dan kurangi teksnya menjadi satu kalimat per langkah."
- "Buat slide 6 lebih visual: empat kartu manfaat dengan ikon, dan tabel sebelum–sesudah dipersingkat."
- "Buat versi tema gelap untuk presentasi di layar besar."
- "Ekspor ke PPTX atau PDF."
