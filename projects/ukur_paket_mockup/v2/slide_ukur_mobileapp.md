# Prompt Claude Design: UkurPaket, ukur paket saat pickup dengan HP kurir

Deck presentasi untuk **management**: masalah, solusi, alur kurir, manfaat bisnis, status saat ini, dan rencana pilot.
Total **12 slide**, format 16:9. Bahasa Indonesia, dengan istilah bisnis dan teknis yang umum dipakai
(pickup, on-device AI, offline, KPI, pilot, dispute). Tidak ada angka rupiah.

## 1. Gambar yang dipakai

Unggah semua file PNG dari folder ini ke **satu proyek** Claude Design. Jangan ganti nama filenya.

| File | Isi | Ukuran |
|---|---|---|
| `alur_kurir.png` | Board 8 langkah alur kurir, dari scan resi sampai data tersimpan | 3840 × 2160 |
| `fitur_lapangan.png` | Board 8 fitur untuk kondisi lapangan | 3840 × 2160 |
| `screens/01_pickup.png` … `screens/16_riwayat.png` | Setiap layar app di dalam bingkai HP, latar transparan | 1348 × ±2860 |

Daftar layar di folder `screens/`:

| File | Layar |
|---|---|
| `01_pickup.png` | Pickup hari ini: daftar resi, tombol Scan resi |
| `02_persiapan.png` | Persiapan: 4 aturan foto |
| `03_scan_lantai.png` | Scan Lantai: titik putih di lantai |
| `04_pilih_paket.png` | Pilih Paket: paket dipilih (garis magenta), paket lain diabaikan |
| `05_scan_paket.png` | Scan Paket: progres 64%, titik data 3D |
| `06_hasil_ukur.png` | Hasil Ukur: kotak 3D dan ukuran 27 × 15 × 6 cm, status Akurat |
| `07_berat.png` | Berat: berat timbangan, berat volumetrik, Berat Tagih |
| `08_tersimpan.png` | Tersimpan: foto, ukuran, waktu, lokasi GPS, progres pickup |
| `09_pilih_area.png` | Pilih Area: kurir menandai area paket dengan jari |
| `10_paket_berikutnya.png` | Paket berikutnya: paket yang sudah diukur diberi tanda ✓ |
| `11_peringatan.png` | Arahan langsung: "Mundur sedikit · paket terpotong layar" |
| `12_perlu_dicek.png` | Perlu Dicek: skor rendah, Simpan dikunci 2 detik |
| `13_ukur_di_hub.png` | Ukur di Hub: pilih alasan setelah 2× gagal |
| `14_detail_ukur_di_hub.png` | Data Ukur di Hub: foto, waktu, lokasi, dan alasan |
| `15_cek_hp.png` | Cek HP: HP kurir siap mengukur |
| `16_riwayat.png` | Riwayat: semua hasil ukur di HP |

Semua gambar adalah **tampilan asli dari aplikasi uji coba** (APK v0.1), bukan desain konsep. Foto paketnya asli
dengan label resi disamarkan. Ukuran 27 × 15 × 6 cm di layar adalah contoh untuk menunjukkan alur, bukan hasil
ukur sungguhan. Jangan ubah isi gambar, dan jangan memotong layar HP.

## 2. Gaya visual

- Warna utama **magenta #ED0677**, aksen **kuning #FFCB08**, teks gelap **#0F172A**, abu-abu **#475569**,
  latar terang **#F6F7FA**. Hijau / oranye / merah hanya untuk status (Akurat / Perlu Dicek / gagal).
- Font **Inter** (atau sans-serif sejenis), judul tebal, isi ringkas: maksimal 3–4 poin per slide.
- Layar HP ditampilkan utuh dengan bayangan lembut. Board 3840 × 2160 dipakai satu slide penuh.
- Jangan menambahkan logo perusahaan; tim akan menambahkannya sendiri bila perlu. Nama produk: **UkurPaket**.

## 3. Susunan deck (12 slide)

| # | Slide | Gambar | Pesan utama |
|---|---|---|---|
| 1 | Sampul | `06_hasil_ukur.png` + `04_pilih_paket.png` | UkurPaket: ukur P × L × T paket saat pickup, cukup dengan HP kurir |
| 2 | Masalah | – | Ukuran dan berat paket sering hanya berdasarkan deklarasi penjual |
| 3 | Solusi dalam 3 langkah | `01_pickup.png`, `05_scan_paket.png`, `08_tersimpan.png` | Scan resi → ukur dengan kamera → data tersimpan sebagai bukti |
| 4 | Alur kurir | `alur_kurir.png` (satu slide penuh) | 8 langkah dari scan resi sampai data tersimpan |
| 5 | Banyak paket di satu lokasi | `04_pilih_paket.png`, `09_pilih_area.png`, `10_paket_berikutnya.png` | Kurir memilih paket yang diukur; paket lain tidak ikut terukur |
| 6 | Berat Tagih yang benar | `06_hasil_ukur.png`, `07_berat.png` | Ongkir dihitung dari berat yang lebih besar: timbangan atau volumetrik |
| 7 | Siap untuk kondisi lapangan | `fitur_lapangan.png` (satu slide penuh) | Paket menempel, tempat gelap, hasil meragukan: ada jalan keluarnya |
| 8 | Kontrol mutu data | `12_perlu_dicek.png`, `13_ukur_di_hub.png`, `14_detail_ukur_di_hub.png` | Hasil meragukan tidak lolos begitu saja; tidak ada paket yang tertinggal |
| 9 | Manfaat bisnis | – | Revenue assurance, tagihan akurat, bukti untuk dispute, data untuk operasional |
| 10 | Cara kerja (ringkas) | `15_cek_hp.png` | On-device AI + AR di HP Android, berjalan offline, data terikat ke resi |
| 11 | Status saat ini | `16_riwayat.png` | Prototipe APK siap diuji; sudah lolos uji otomatis, belum uji lapangan |
| 12 | Rencana pilot & keputusan | – | 3 fase, KPI yang diukur, dukungan yang dibutuhkan dari management |

## 4. Isi setiap slide

**Slide 1 · Sampul**
- Judul: **UkurPaket**
- Subjudul: Ukur panjang × lebar × tinggi paket saat pickup, cukup dengan kamera HP kurir.
- Tampilkan dua layar HP berdampingan: `04_pilih_paket.png` dan `06_hasil_ukur.png`.

**Slide 2 · Masalah**
- Judul: Ukuran paket masih bergantung pada deklarasi penjual
- Poin:
  - Berat dan ukuran yang dideklarasikan sering lebih kecil dari aslinya, sehingga ongkir yang ditagih kurang (revenue leakage).
  - Pengukuran ulang di hub menambah antrean dan waktu proses.
  - Saat ada dispute ongkir, bukti ukuran fisik paket tidak selalu tersedia.
  - Input ukuran manual rawan salah ketik dan sulit diaudit.

**Slide 3 · Solusi dalam 3 langkah**
- Judul: Diukur di titik pertama: saat pickup
- Tiga kolom, masing-masing dengan satu layar HP:
  1. **Scan resi** (`01_pickup.png`): hasil ukur langsung terikat ke nomor resi.
  2. **Ukur dengan kamera** (`05_scan_paket.png`): kurir menggerakkan HP mengitari paket beberapa detik.
  3. **Tersimpan sebagai bukti** (`08_tersimpan.png`): foto dengan kotak 3D, ukuran, waktu, dan lokasi.

**Slide 4 · Alur kurir**
- Judul: Alur kurir, 8 langkah
- Tampilkan `alur_kurir.png` satu slide penuh, tanpa teks tambahan selain judul.

**Slide 5 · Banyak paket di satu lokasi**
- Judul: Kurir menentukan paket yang diukur
- Poin:
  - Ketuk paketnya; paket di sebelahnya otomatis diabaikan (ditandai "Paket lain").
  - Kalau ketukan kurang pas, kurir menandai area paket dengan jari (Pilih Area).
  - Paket berikutnya di lokasi yang sama: tanpa scan lantai ulang, paket yang selesai diberi tanda ✓.
- Gambar: `04_pilih_paket.png`, `09_pilih_area.png`, `10_paket_berikutnya.png`.

**Slide 6 · Berat Tagih yang benar**
- Judul: Ongkir dari ukuran fisik, bukan hanya deklarasi
- Poin:
  - Berat volumetrik = P × L × T (cm) ÷ 6.000 (faktor bisa diatur: 4.000 / 5.000 / 6.000).
  - **Berat Tagih** = yang lebih besar antara berat timbangan dan berat volumetrik.
  - Angka hasil ukur tidak bisa diedit kurir; setiap hasil punya skor keyakinan.
- Gambar: `06_hasil_ukur.png`, `07_berat.png`.

**Slide 7 · Siap untuk kondisi lapangan**
- Judul: Dibuat untuk kondisi nyata kurir
- Tampilkan `fitur_lapangan.png` satu slide penuh.

**Slide 8 · Kontrol mutu data**
- Judul: Data yang masuk bisa dipercaya
- Poin:
  - **Perlu Dicek**: hasil dengan skor rendah ditandai, tombol Simpan dikunci 2 detik agar kurir memeriksa ulang.
  - **Ukur di Hub**: setelah 2× gagal, paket tetap diambil dan diukur di hub, lengkap dengan foto, lokasi, dan alasan.
  - **Bukti per resi**: nomor resi diambil dari scan barcode garis di label (QR tidak dibaca), lalu setiap hasil ukur menyimpan foto dengan kotak 3D, waktu, dan lokasi.
- Gambar: `12_perlu_dicek.png`, `13_ukur_di_hub.png`, `14_detail_ukur_di_hub.png`.

**Slide 9 · Manfaat bisnis**
- Judul: Manfaat bagi bisnis
- Tabel 2 kolom (manfaat · penjelasan):
  - **Revenue assurance**: selisih antara ukuran deklarasi dan ukuran asli terlihat sejak pickup.
  - **Tagihan akurat**: Berat Tagih dihitung dari ukuran fisik paket.
  - **Bukti untuk dispute**: foto dengan kotak 3D, waktu, dan lokasi untuk setiap resi.
  - **Beban hub berkurang**: paket yang sudah terukur di pickup tidak perlu antre ukur ulang di hub.
  - **Data operasional**: volume setiap paket tersedia untuk perencanaan muat armada.

**Slide 10 · Cara kerja (ringkas)**
- Judul: Teknologi yang dipakai
- Poin:
  - **Augmented Reality (AR)** dari Google mengenali lantai dan jarak dari kamera HP.
  - **On-device AI** memisahkan paket yang dipilih dari paket di sekitarnya.
  - **Berjalan offline**: semua proses di HP; setelah integrasi, data dikirim ke sistem saat ada sinyal.
  - **HP Android yang mendukung AR**, contoh Samsung Galaxy A35 / A55. App memeriksa HP saat pertama dibuka.
- Gambar: `15_cek_hp.png`.

**Slide 11 · Status saat ini**
- Judul: Prototipe siap diuji
- Poin:
  - **Sudah ada**: aplikasi Android uji coba (APK v0.1) dengan alur lengkap, dari scan resi sampai riwayat.
  - **Sudah diuji otomatis**: 17 tes, termasuk alur kurir, perhitungan ukuran pada data simulasi, pemilihan paket
    di antara banyak paket, dan pembacaan barcode dari label resi AnterAja asli.
  - **Belum**: uji lapangan di HP Android, dan integrasi dengan sistem order/resi.
- Gambar: `16_riwayat.png`.

**Slide 12 · Rencana pilot & keputusan**
- Judul: Langkah berikutnya
- Tiga fase:
  1. **Uji lapangan**: 50–100 paket diukur dengan app dan dengan meteran, di HP yang mendukung AR.
  2. **Integrasi sistem**: ambil data deklarasi berdasarkan nomor resi, kirim hasil ukur ke sistem.
  3. **Pilot**: sekelompok kurir di satu area atau hub.
- KPI yang diukur: selisih ukuran vs meteran (cm), durasi per paket (detik), % hasil Perlu Dicek,
  % paket Ukur di Hub, dan selisih Berat Tagih vs deklarasi.
- Yang dibutuhkan dari management: persetujuan uji lapangan, 2–3 HP uji, dan akses ke data resi untuk integrasi.

## 5. Prompt untuk ditempel di Claude Design

```
Buat presentasi 12 slide (16:9) untuk management berjudul "UkurPaket". Ikuti susunan dan isi slide di
slide_ukur_mobileapp.md (bagian 3 dan 4) persis, dalam bahasa Indonesia dengan istilah bisnis yang umum.

Gambar terlampir: alur_kurir.png dan fitur_lapangan.png (board 3840×2160, pakai satu slide penuh, jangan dipotong),
dan screens/01_pickup.png sampai screens/16_riwayat.png (layar HP berbingkai, latar transparan). Pakai gambar
sesuai tabel; jangan ubah isi gambar dan jangan memotong layar HP.

Gaya: warna utama magenta #ED0677, aksen kuning #FFCB08, teks #0F172A, abu-abu #475569, latar #F6F7FA.
Hijau/oranye/merah hanya untuk status. Font Inter. Ringkas: maksimal 3–4 poin per slide, judul berupa pesan.
Jangan menambahkan logo, angka rupiah, atau klaim akurasi yang tidak ada di dokumen.
Di slide yang memakai layar app, tambahkan catatan kecil: "Tampilan aplikasi uji coba; ukuran di layar adalah contoh."
```
