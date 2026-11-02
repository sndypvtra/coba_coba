# Detail Project: Sistem Hitung Karton per Palet di Loading Dock (4 Kamera)

Proposal investasi untuk pembangunan sistem AI computer vision yang menghitung karton pada setiap palet di loading dock Gudang Minyakita, sebelum barang naik ke truk ekspedisi. Dokumen ini adalah brief untuk membuat deck PPTX di Claude Design: isi tiap slide, angka, grafik, dan tabelnya sudah final dan konsisten dengan file budget.

- **Tanggal:** November 2026
- **Lokasi:** Gudang Minyakita, area loading dock
- **Skala:** 4 kamera CCTV 4MP
- **Modal awal investor:** Rp 246.472.418 (Rp 246,5 juta)
- **Fee developer AI computer vision dan web app:** Rp 107.000.000
- **Waktu pengerjaan:** 16 minggu dari PO sampai go-live
- **Semua angka dalam Rupiah.**

## 1. Apa yang dikerjakan

Yang dibangun adalah **sistem penghitungan box (karton) pada palet di loading dock**:

1. Palet berhenti sebentar di zona cek depan dock.
2. 4 kamera CCTV merekam palet; PC server AI di gudang menghitung jumlah karton secara realtime (20-30 fps per kamera).
3. Hasil hitung dibandingkan dengan standar 60 karton per palet dan dengan data DO (delivery order).
4. Status palet (lengkap atau kurang) tampil di TV loading dock dan di web app; palet kurang langsung memicu peringatan.
5. Setiap event tersimpan bersama foto dan klip bukti di PC server sebagai audit trail. Owner bisa live monitoring dari luar gudang lewat Tailscale.

**Komponen utama:** model AI computer vision (deteksi dan hitung karton), web app on-premise (dashboard, laporan per DO, truk, dan palet, event trigger, riwayat event), PC server AI dengan GPU NVIDIA RTX 5060 Ti 16 GB, 4 kamera Hikvision 4MP, jaringan, UPS, dan TV status di dock. Tidak memakai cloud; data tetap di gudang.

## 2. Timeline 16 minggu

- **M1-M2:** Survey dock, desain posisi kamera, pengadaan perangkat
- **M3-M4:** Instalasi kamera, jaringan, server; mulai rekam data
- **M5-M10:** Pelabelan data, training model AI, logika hitung 60 karton
- **M5-M10:** Pembuatan web app (paralel)
- **M11-M13:** Optimasi realtime 4 kamera, integrasi data DO, kalibrasi
- **M14-M15:** Uji paralel 2 minggu vs hitung manual
- **M16:** Training pengguna, SOP, serah terima (go-live)

## 3. Total investasi awal: Rp 246.472.418

Dibayar investor saat PO. Harga perangkat dari toko resmi di Tokopedia (dicek Oktober 2026) ditambah cadangan kenaikan harga 10%. Fee tim dihitung dari tarif INKINDO 2026.

| Rincian | Nilai |
| --- | ---: |
| Server AI (PC GPU, HDD rekaman 8 TB, HDD backup 12 TB) | Rp 47.135.000 |
| Kamera CCTV dan kabel (4 kamera 4MP) | Rp 16.640.380 |
| Jaringan (router, switch PoE, rak) | Rp 10.793.000 |
| Layar status di loading dock (TV 55 inci) | Rp 9.028.000 |
| UPS server dan UPS rak | Rp 7.974.000 |
| Cadangan kenaikan harga perangkat (10%) | Rp 9.157.038 |
| Jasa pasang kamera (vendor, 4 titik) | Rp 1.400.000 |
| **Subtotal perangkat** | **Rp 102.127.418** |
| Fee developer AI computer vision dan web app | Rp 107.000.000 |
| Fee infrastruktur dan project management | Rp 37.345.000 |
| **Total investasi awal** | **Rp 246.472.418** |

### Fee developer (tetap): Rp 107.000.000

| Rincian | Nilai |
| --- | ---: |
| Pembuatan AI computer vision (model hitung karton) | Rp 45.597.000 |
| Pembuatan web app (dashboard, laporan, event, DO) | Rp 28.911.000 |
| Setup dan implementasi AI dan web app di lokasi | Rp 17.244.000 |
| Garansi software 3 bulan setelah go-live | Rp 7.485.000 |
| Insentif penyelesaian proyek | Rp 7.763.000 |
| **Total** | **Rp 107.000.000** |

### Fee infrastruktur dan project management: Rp 37.345.000

| Rincian | Nilai |
| --- | ---: |
| Implementasi infrastruktur (survey, instalasi, kalibrasi kamera) | Rp 16.110.000 |
| Project management (koordinasi 16 minggu) | Rp 18.700.000 |
| Garansi infrastruktur 3 bulan setelah go-live | Rp 2.535.000 |
| **Total** | **Rp 37.345.000** |

Tim (developer dan orang infrastruktur) tidak menaruh modal. Profit proyek setelah fee tim dan biaya operasional menjadi hak investor.

## 4. Dua model pendapatan

| | Beli putus (seperti Opsi A) | Subscription (seperti Opsi B) |
| --- | --- | --- |
| Yang dibayar klien | Rp 254.236.000 sekali (termin 50/30/20) | Rp 126.562.000 sekali + Rp 106.340.000 per tahun |
| Total pendapatan proyek | Rp 254.236.000 | Rp 445.582.000 (36 bulan) |
| Pemilik perangkat | Klien | Penyedia (jaminan investor) |
| Durasi dana investor | 4 bulan | 40 bulan (PO sampai akhir kontrak) |
| Profit investor | **Rp 7.763.582** | **Rp 50.756.582** (s.d. Rp 82.289.582) |
| ROI atas modal awal | 3,1% | 20,6% (s.d. 33,4%) |
| Dana investor tertahan paling besar | Rp 119.354.418 | Rp 76.851.418 |

**Asumsi model:** seluruh fee tim dan pembelian perangkat dibayar investor saat PO. Pembayaran klien masuk ke investor. Pada subscription, support bulanan untuk tim (Rp 38.940.000 per tahun) dan cadangan penggantian perangkat (Rp 31.533.000 selama kontrak, dihitung rata per bulan) dibayar dari pendapatan langganan. Angka "s.d." berlaku bila cadangan penggantian tidak terpakai.

## 5. Proyeksi beli putus: profit Rp 7.763.582 (3,1%) dalam 4 bulan

| Waktu | Uang masuk | Uang keluar | Saldo kumulatif investor |
| --- | ---: | ---: | ---: |
| Saat PO (bulan 0) | Rp 127.118.000 | Rp 246.472.418 | Rp -119.354.418 |
| Setelah instalasi (bulan 1) | Rp 76.270.800 | - | Rp -43.083.618 |
| Serah terima / go-live (bulan 4) | Rp 50.847.200 | - | Rp 7.763.582 |

Dana investor tertahan paling besar Rp 119.354.418 (setelah DP klien saat PO). Grafik: waterfall dari modal -Rp 246,5 juta sampai profit +Rp 7,8 juta.

## 6. Proyeksi subscription: profit Rp 50.756.582 (20,6%), s.d. Rp 82.289.582 (33,4%)

| Periode | Uang masuk | Uang keluar (modal awal, support, cadangan) | Saldo kumulatif investor |
| --- | ---: | ---: | ---: |
| Saat PO (bulan 0) | Rp 169.621.000 | Rp 246.472.418 | Rp -76.851.418 |
| Go-live (bulan 4) | Rp 63.281.000 | - | Rp -13.570.418 |
| Tahun ke-1 langganan (bulan 4-15) | - | Rp 49.451.000 | Rp -63.021.418 |
| Tahun ke-2 langganan (bulan 16-27) | Rp 106.340.000 | Rp 49.451.000 | Rp -6.132.418 |
| Tahun ke-3 langganan (bulan 28-39) | Rp 106.340.000 | Rp 49.451.000 | Rp 50.756.582 |

Saldo pertama kali positif di bulan ke-16, lalu sempat turun lagi sebelum pembayaran langganan tahun ke-3; balik modal permanen di bulan ke-28. Dana tertahan paling besar Rp 76.851.418 (setelah pembayaran klien saat PO).

## 7. Ringkasan return investor

| | Beli putus | Subscription 36 bulan |
| --- | --- | --- |
| Modal awal investor | Rp 246.472.418 | Rp 246.472.418 |
| Total uang kembali ke investor | Rp 254.236.000 | Rp 297.229.000 (s.d. Rp 328.762.000) |
| Profit investor | **Rp 7.763.582** | **Rp 50.756.582** (s.d. Rp 82.289.582) |
| ROI atas modal awal | 3,1% | 20,6% (s.d. 33,4%) |
| ROI atas dana tertahan paling besar | 6,5% | 66,0% (s.d. 107,1%) |
| Waktu sampai profit diterima penuh | 4 bulan | 40 bulan |
| Fee developer (tetap) | Rp 107.000.000 | Rp 107.000.000 |

## 8. Risiko dan mitigasi

| Risiko | Mitigasi |
| --- | --- |
| Klien berhenti di tengah kontrak (subscription) | Biaya pemutusan = sisa sewa perangkat sampai bulan ke-36; perangkat tetap milik penyedia |
| Klien telat bayar | Lebih dari 30 hari, layanan support dihentikan sementara; pembayaran di muka per tahun |
| Perangkat rusak | Cadangan penggantian Rp 31,5 juta sudah dihitung; kerusakan karena kelalaian ditanggung klien |
| Akurasi atau kecepatan tidak tercapai | Uji paralel 2 minggu sebelum go-live dan sebelum termin terakhir |
| Harga perangkat naik | Sudah ada cadangan kenaikan harga 10% |
| Lisensi software AI | Model memakai lisensi komersial bebas (Apache-2.0), tanpa biaya lisensi tahunan |

## 9. Naskah slide untuk Claude Design (16:9)

Gaya: bersih, latar putih, satu warna aksen biru untuk angka utama, abu-abu untuk data pendukung, hijau = uang masuk, merah = uang keluar. Font sans-serif (Inter). Judul slide berupa kalimat temuan, bukan topik. Gambar mockup referensi ada di folder `slides/`.

1. **Cover.** Judul: "Sistem Hitung Karton per Palet di Loading Dock". Isi: Kartu angka: Gudang Minyakita · 4 kamera CCTV · modal awal Rp 246,5 juta · 16 minggu.
2. **Masalah dan solusi.** Judul: "Hitung manual di loading dock rawan selisih; sistem ini menghitung setiap palet otomatis". Isi: Dua kolom: masalah hari ini vs solusi. Baris kartu: 60 karton/palet, 20-30 fps, 4 kamera, on-premise.
3. **Cara kerja.** Judul: "Cara kerja: kamera, PC server AI, lalu hasilnya tampil di web app dan TV dock". Isi: Diagram alur: 4 kamera -> PC server AI -> hitung karton dan cocokkan DO -> web app + TV dock dan owner via Tailscale. Mockup tampilan web app (ilustrasi): daftar palet hijau/merah.
4. **Timeline.** Judul: "Pengerjaan 16 minggu dari PO sampai go-live". Isi: Gantt 7 baris per minggu (M1-M16), lihat bagian 2.
5. **Investasi awal.** Judul: "Total investasi awal Rp 246,5 juta, dibayar investor saat PO". Isi: Bar bertumpuk 3 bagian (perangkat, fee developer, fee infrastruktur) + tabel rincian bagian 3.
6. **Fee tim.** Judul: "Fee tim tetap: developer Rp 107 juta, infrastruktur Rp 37,3 juta". Isi: Dua tabel rincian fee (bagian 3).
7. **Model pendapatan.** Judul: "Dua model pendapatan: beli putus untung cepat tapi kecil, subscription lebih besar tapi lebih lama". Isi: Tabel perbandingan bagian 4.
8. **Proyeksi beli putus.** Judul: "Beli putus: investor untung Rp 7,8 juta (3,1%) dalam 4 bulan". Isi: Waterfall + 3 kartu KPI + tabel arus kas bagian 5.
9. **Proyeksi subscription.** Judul: "Subscription: investor untung Rp 50,8 juta (20,6%), balik modal permanen di bulan ke-28". Isi: Grafik garis saldo kumulatif per bulan (bulan 0-39), garis putus-putus abu untuk skenario cadangan utuh, penanda go-live dan pembayaran tahunan + tabel bagian 6.
10. **Return investor.** Judul: "Ringkasan return investor per model". Isi: Tabel bagian 7.
11. **Risiko.** Judul: "Risiko utama dan mitigasinya". Isi: Tabel bagian 8.
12. **Langkah berikutnya.** Judul: "Langkah berikutnya". Isi: Yang diminta dari investor (komitmen Rp 246,5 juta, pilih model, perjanjian tertulis) + urutan eksekusi 4 langkah.

## 10. Data grafik

**Saldo kumulatif investor, beli putus (juta Rp, bulan 0-4):** 0: -119.4, 1: -43.1, 2: -43.1, 3: -43.1, 4: 7.8

**Saldo kumulatif investor, subscription (juta Rp, bulan 0-39):** 0: -76.9, 1: -76.9, 2: -76.9, 3: -76.9, 4: -17.7, 5: -21.8, 6: -25.9, 7: -30.1, 8: -34.2, 9: -38.3, 10: -42.4, 11: -46.5, 12: -50.7, 13: -54.8, 14: -58.9, 15: -63.0, 16: 39.2, 17: 35.1, 18: 31.0, 19: 26.8, 20: 22.7, 21: 18.6, 22: 14.5, 23: 10.4, 24: 6.2, 25: 2.1, 26: -2.0, 27: -6.1, 28: 96.1, 29: 92.0, 30: 87.8, 31: 83.7, 32: 79.6, 33: 75.5, 34: 71.4, 35: 67.2, 36: 63.1, 37: 59.0, 38: 54.9, 39: 50.8

**Sama, bila cadangan penggantian tidak terpakai:** 0: -76.9, 1: -76.9, 2: -76.9, 3: -76.9, 4: -16.8, 5: -20.1, 6: -23.3, 7: -26.6, 8: -29.8, 9: -33.0, 10: -36.3, 11: -39.5, 12: -42.8, 13: -46.0, 14: -49.3, 15: -52.5, 16: 50.6, 17: 47.3, 18: 44.1, 19: 40.8, 20: 37.6, 21: 34.4, 22: 31.1, 23: 27.9, 24: 24.6, 25: 21.4, 26: 18.1, 27: 14.9, 28: 118.0, 29: 114.7, 30: 111.5, 31: 108.2, 32: 105.0, 33: 101.8, 34: 98.5, 35: 95.3, 36: 92.0, 37: 88.8, 38: 85.5, 39: 82.3

## 11. Sumber

- Budget internal: `Budget_Minyakita_Pallet_Counting_4Kamera.xlsx` (sheet RAB, Jasa INKINDO, Skenario A, Skenario B, Cadangan Penggantian).
- Tarif jasa: Pedoman Standar Minimal Billing Rate INKINDO 2026 (https://www.inkindo.org/documents/ikdweb-billing-rate-2026.pdf).
- Harga perangkat: toko resmi di Tokopedia, dicek Oktober 2026 (tautan per barang di sheet RAB).
- Ini proyeksi berdasarkan penawaran ke klien; realisasi tergantung PO, jadwal pembayaran klien, dan biaya aktual.
