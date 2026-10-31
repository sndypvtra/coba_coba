"""Budget workbook: Minyakita pallet box counting at the loading dock, 8 cameras, on-premise standalone (no cloud).

Two scenarios: A = one-off purchase (hardware, installation, web app and AI become the client's inventory);
B = annual subscription (all infrastructure stays ours, the client rents it with the software and service).
Every price comes from a public web source listed on the 'Sumber Harga' sheet.

    python build_budget.py   # -> Budget_Minyakita_Pallet_Counting.xlsx (then recalc with LibreOffice)
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().parent / "Budget_Minyakita_Pallet_Counting.xlsx"
ACCESSED = "31 Okt 2026"
F = "Arial"
BLUE, GREEN, BLACK, GREY = "0000FF", "008000", "000000", "404040"
YELLOW = PatternFill("solid", fgColor="FFFF00")
HEAD = PatternFill("solid", fgColor="1F3864")
SUB = PatternFill("solid", fgColor="D9E1F2")
TOTAL = PatternFill("solid", fgColor="F2F2F2")
RP = '#,##0;(#,##0);"-"'
PCT = '0.0%;(0.0%);"-"'
NUM = '#,##0.0;(#,##0.0);"-"'
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

wb = Workbook()
wb.remove(wb.active)


def sheet(name, widths):
    ws = wb.create_sheet(name)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_view.showGridLines = False
    return ws


def put(ws, ref, value, color=BLACK, bold=False, fmt=None, fill=None, wrap=False, size=10, italic=False, right=False):
    c = ws[ref]
    c.value = value
    c.font = Font(name=F, size=size, bold=bold, color=color, italic=italic)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    c.alignment = Alignment(vertical="top", wrap_text=wrap, horizontal="right" if right else None)
    return c


def title(ws, text, sub):
    put(ws, "A1", text, bold=True, size=14)
    put(ws, "A2", sub, italic=True, color="595959")


def header(ws, row, labels):
    for i, lab in enumerate(labels, 1):
        put(ws, f"{get_column_letter(i)}{row}", lab, color="FFFFFF", bold=True, fill=HEAD, wrap=True).border = BOX


def section(ws, row, text, ncols):
    for i in range(1, ncols + 1):
        ws[f"{get_column_letter(i)}{row}"].fill = SUB
    put(ws, f"A{row}", text, bold=True, fill=SUB)


# ------------------------------------------------------------------ Sumber Harga
SRC = [
    ("S1", "Viraindo (Vira Jaya Computer), daftar harga VGA", "https://www.viraindo.com/vga.html"),
    ("S2", "Viraindo, daftar harga processor", "https://www.viraindo.com/proc.html"),
    ("S3", "Viraindo, daftar harga motherboard", "https://www.viraindo.com/motherboard.html"),
    ("S4", "Viraindo, daftar harga memory", "https://www.viraindo.com/memory.html"),
    ("S5", "Viraindo, daftar harga storage (SSD, HDD)", "https://www.viraindo.com/storage.html"),
    ("S6", "Viraindo, daftar harga power supply", "https://www.viraindo.com/psu.html"),
    ("S7", "Viraindo, daftar harga casing", "https://www.viraindo.com/casing.html"),
    ("S8", "Viraindo, daftar harga UPS dan stabilizer", "https://www.viraindo.com/ups-stabilizer.html"),
    ("S9", "Viraindo, daftar harga networking", "https://www.viraindo.com/networking.html"),
    ("S10", "Viraindo, daftar harga rack server", "https://www.viraindo.com/rackserver.html"),
    ("S11", "Viraindo, daftar harga monitor dan TV", "https://www.viraindo.com/lcd.html"),
    ("S12", "Viraindo, daftar harga keyboard dan mouse", "https://www.viraindo.com/keymouse.html"),
    ("S13", "Hikvision Indonesia, Daftar Harga CCTV Hikvision Terbaru 2026 (terbit 14 Mar 2026). Dipakai batas atas kisaran.",
     "https://hikvision-indonesia.com/daftar-harga-cctv-hikvision-terbaru-2026-seri-2mp-hingga-5mp/"),
    ("S14", "GSI Indonesia, Harga Pasang CCTV Per Titik 2026 (terbit 17 Apr 2026): IP camera jasa + material Rp 900.000 sampai Rp 1.500.000 per titik. Dipakai batas atas.",
     "https://gsi-indo.com/2026/04/17/harga-pasang-cctv-per-titik/"),
    ("S15", "Acuan tarif tim. Okezone Economy, Berapa Gaji Engineering AI (28 Mei 2026): level menengah Rp 16 juta sampai Rp 25 juta per bulan. Dipakai nilai tengah.",
     "https://economy.okezone.com/read/2026/05/28/320/3221176/berapa-gaji-engineering-ai-segini-kisarannya?page=all"),
    ("S16", "Acuan tarif tim. Indeed Indonesia, gaji Full Stack Developer di Jakarta: rata-rata Rp 10.203.433 per bulan (49 laporan, diperbarui 15 Agu 2026)",
     "https://id.indeed.com/career/full-stack-developer/salaries/Jakarta"),
    ("S17", "Acuan tarif tim. LokerID, gaji Manajemen dan Strategi IT di DKI Jakarta: rata-rata Rp 13,3 juta per bulan",
     "https://www.loker.id/gaji/information-technology/manajemen-it/jakarta"),
    ("S18", "Acuan tarif tim. Indeed Indonesia, gaji Staf Teknisi di Jakarta: Rp 4.912.597 per bulan (107 laporan)",
     "https://id.indeed.com/salaries/staf-teknisi-Salaries"),
    ("S19", "PMK No. 131 Tahun 2024: PPN 12% dengan DPP 11/12, tarif efektif 11% untuk barang dan jasa non mewah", "Peraturan Menteri Keuangan No. 131 Tahun 2024"),
]
SS = sheet("Sumber Harga", [7, 90, 70])
title(SS, "Sumber Harga", f"Semua harga diambil dari sumber publik di bawah, diakses {ACCESSED}. Harga toko dapat berubah; minta penawaran tertulis sebelum pembelian.")
header(SS, 4, ["Kode", "Sumber dan angka yang dipakai", "Tautan / dasar hukum"])
for i, (code, desc, url) in enumerate(SRC, 5):
    put(SS, f"A{i}", code, bold=True)
    put(SS, f"B{i}", desc, wrap=True)
    put(SS, f"C{i}", url, wrap=True, color="0563C1" if url.startswith("http") else GREY)
    if url.startswith("http"):
        SS[f"C{i}"].hyperlink = url

# ------------------------------------------------------------------ Hardware
H = sheet("Hardware", [5, 32, 62, 6, 15, 16, 8])
title(H, "Hardware (8 kamera, 1 lokasi, on-premise)", "Harga beli kita dari sumber publik. Kode sumber merujuk ke sheet Sumber Harga.")
header(H, 4, ["No", "Item", "Produk persis seperti tercantum di sumber", "Qty", "Harga satuan (Rp)", "Total (Rp)", "Sumber"])
HW = [
    ("Kamera", None),
    ("IP Camera 4MP bullet", "Hikvision DS-2CD1043G0-I (kisaran Rp 950.000 sampai Rp 1.150.000)", 8, 1150000, "S13"),
    ("NVR 8 kanal PoE", "Hikvision DS-7608NI-K1/8P, NVR 8 Channel (kisaran Rp 2.200.000 sampai Rp 2.800.000)", 1, 2800000, "S13"),
    ("HDD rekaman 8 TB", "Seagate 3.5\" Surveillance 8 TB Sata SkyHawk Series", 1, 5900000, "S5"),
    ("PC server AI (rakit)", None),
    ("Processor", "AMD Ryzen 7 7700 3.8Ghz Up To 5.3Ghz Cache 32MB 65W AM5 [Box] - 8 Core - with AMD Wraith Prism Cooler", 1, 5200000, "S2"),
    ("Motherboard", "MSI PRO B650M-P", 1, 1890000, "S3"),
    ("Memory 32 GB", "G.Skill Ripjaws S5 White DDR5 PC48000 6000MHz 32GB (2x16GB) - F5-6000J3648D16GX2-RS5W", 1, 4150000, "S4"),
    ("SSD 1 TB (sistem, aplikasi, database)", "Kingston SSD NV3 1TB M.2 NVMe PCIe Gen 4.0 x4", 1, 3100000, "S5"),
    ("GPU 16 GB (AI 8 kamera)", "Gigabyte GeForce RTX 5060 Ti 16 GB - WindForce - GV-N506TWF2-16GD", 1, 9700000, "S1"),
    ("Power supply 750W Gold", "Seasonic G12 GM-750 750W - Semi Modular - 80+ Gold - 5 Years Warranty Replacement", 1, 1430000, "S6"),
    ("Casing", "Cooler Master MasterBox TD500 Mesh V2", 1, 1240000, "S7"),
    ("Pendukung", None),
    ("UPS online 2 kVA", "APC Easy UPS On-Line, 2000VA/1800W 230V - SRV2KI-E", 1, 9100000, "S8"),
    ("Switch gigabit 8 port", "TP-Link Switch 8 Port Gigabit 10/100/1000 - TL-SG108", 1, 310000, "S9"),
    ("Rack wallmount 8U (NVR, switch)", "Indorack Wallmount Rack Single Door 19 inch WIR5508S 8U Width:600mm Depth: 550mm", 1, 2050000, "S10"),
    ("Monitor dashboard 27 inch", "LG 27 27MS500-B FHD IPS 100Hz Monitor", 1, 1420000, "S11"),
    ("Layar status di loading dock 43 inch", "Xiaomi TV A 43 FHD - 2025", 1, 2870000, "S11"),
    ("Keyboard dan mouse", "Logitech Classic MK120 USB (K120 + B100)", 1, 165000, "S12"),
]
r = 5
first = r
for item in HW:
    if item[1] is None:
        section(H, r, item[0], 7)
    else:
        it, prod, q, p, src = item
        put(H, f"B{r}", it)
        put(H, f"C{r}", prod, wrap=True, color=GREY)
        put(H, f"D{r}", q, color=BLUE, fmt="0")
        put(H, f"E{r}", p, color=BLUE, fmt=RP)
        put(H, f"F{r}", f"=D{r}*E{r}", fmt=RP)
        put(H, f"G{r}", src)
    r += 1
put(H, f"B{r}", "Total hardware", bold=True, fill=TOTAL)
put(H, f"F{r}", f"=SUM(F{first}:F{r - 1})", bold=True, fmt=RP, fill=TOTAL)
HW_TOTAL = f"Hardware!$F${r}"
r += 2
put(H, f"B{r}", "Kecocokan untuk 8 kamera: GPU 16 GB menjalankan deteksi dan hitung karton 8 stream secara bersamaan; CPU 8 core untuk decode dan web app; NVR merekam semua kamera sebagai bukti.", wrap=True, italic=True, color="595959")
H.merge_cells(f"B{r}:G{r}")
H.row_dimensions[r].height = 28
r += 1
put(H, f"B{r}", "Sistem operasi Ubuntu Server dan seluruh software pendukung memakai lisensi open source, tanpa biaya lisensi.", italic=True, color="595959")
H.merge_cells(f"B{r}:G{r}")

# ------------------------------------------------------------------ Instalasi
I = sheet("Instalasi", [5, 40, 62, 6, 15, 16, 8])
title(I, "Instalasi", "Jasa pasang per titik sudah termasuk material standar (kabel, konektor, bracket) menurut sumber.")
header(I, 4, ["No", "Item", "Keterangan", "Qty", "Harga satuan (Rp)", "Total (Rp)", "Sumber"])
INST = [
    ("Jasa + material pasang IP camera per titik", "Termasuk kabel standar, konektor, pemasangan, setting sudut", 8, 1500000, "S14"),
    ("Kabel UTP Cat6 tambahan 305 m", "Belden Cable UTP Cat.6 305 Meters (7814A), untuk jarak kamera ke NVR di atas panjang standar", 1, 2900000, "S9"),
    ("Konektor RJ45 Cat6", "Belden Connector Cat6 (50 Pieces) BL AP700008", 1, 340000, "S9"),
]
r = 5
for i, (it, ket, q, p, src) in enumerate(INST, 1):
    put(I, f"A{r}", i)
    put(I, f"B{r}", it, wrap=True)
    put(I, f"C{r}", ket, wrap=True, color=GREY)
    put(I, f"D{r}", q, color=BLUE, fmt="0")
    put(I, f"E{r}", p, color=BLUE, fmt=RP)
    put(I, f"F{r}", f"=D{r}*E{r}", fmt=RP)
    put(I, f"G{r}", src)
    r += 1
put(I, f"B{r}", "Total instalasi", bold=True, fill=TOTAL)
put(I, f"F{r}", f"=SUM(F5:F{r - 1})", bold=True, fmt=RP, fill=TOTAL)
INST_TOTAL = f"Instalasi!$F${r}"
r += 2
put(I, f"B{r}", "Tidak termasuk: alat kerja ketinggian (umumnya memakai forklift atau man basket milik gudang), listrik, dan pekerjaan sipil. Panjang kabel final mengikuti hasil survey.", wrap=True, italic=True, color="595959")
I.merge_cells(f"B{r}:G{r}")
I.row_dimensions[r].height = 28

# ------------------------------------------------------------------ Implementasi
M = sheet("Implementasi", [5, 56, 8, 8, 9, 9, 16, 42])
title(M, "Pembangunan Web App dan AI + Implementasi oleh Tim CV", "Biaya jasa tim CV = hari kerja x tarif harian. Tarif harian mengacu gaji pasar Jakarta per peran dibagi hari kerja.")
section(M, 4, "1. Tarif jasa tim CV per hari kerja", 8)
header(M, 5, ["", "Peran", "", "", "", "Acuan per bulan (Rp)", "Tarif per hari (Rp)", "Sumber acuan"])
put(M, "B6", "Hari kerja per bulan")
put(M, "G6", 21, color=BLUE, fmt="0")
put(M, "H6", "5 hari kerja x 52 minggu / 12 bulan, dibulatkan", color=GREY)
DAYS = "Implementasi!$G$6"
RATE = {}
r = 7
for key, lab, sal, src in [
    ("pm", "Project Manager IT", 13300000, "S17"),
    ("ai", "AI / Computer Vision Engineer (level menengah)", 20500000, "S15"),
    ("fs", "Fullstack Developer (web app)", 10203433, "S16"),
    ("fe", "Teknisi lapangan", 4912597, "S18"),
]:
    put(M, f"B{r}", lab)
    put(M, f"F{r}", sal, color=BLUE, fmt=RP)
    put(M, f"G{r}", f"=F{r}/{DAYS}", fmt=RP, bold=True)
    put(M, f"H{r}", src)
    RATE[key] = f"Implementasi!$G${r}"
    r += 1
section(M, r + 1, "2. Pekerjaan dan biaya jasa tim", 8)
ACT0 = r + 3
header(M, ACT0 - 1, ["No", "Pekerjaan", "PM", "AI/CV", "Fullstack", "Teknisi", "Biaya jasa tim (Rp)", "Hasil"])
ACTS = [
    ("Survey lokasi, layout dock, desain posisi kamera dan zona cek palet", 1, 1, 0, 1, "Gambar posisi kamera per dock"),
    ("Pengambilan dan pelabelan gambar karton dan palet dari CCTV lokasi", 0, 2, 0, 4, "Dataset karton dan palet Minyakita"),
    ("Training dan tuning model AI (karton, palet, lapisan)", 0, 10, 0, 0, "Model deteksi khusus kemasan Minyakita"),
    ("Logika hitung karton per palet (60 karton) dan rekonsiliasi per DO", 0, 8, 3, 0, "Status palet lengkap atau kurang, selisih per DO"),
    ("Web app on-premise: dashboard, input DO, laporan per DO, truk, palet, alert, user", 0, 0, 20, 0, "Web app berjalan di server lokal"),
    ("Pipeline video 8 kamera dan deploy di PC server", 0, 5, 3, 0, "Sistem realtime di lokasi"),
    ("Rakit dan setting PC server, kalibrasi 8 kamera", 0, 3, 0, 3, "Server dan kamera siap"),
    ("UAT: uji paralel 2 minggu dibanding hitung manual", 2, 5, 0, 5, "Laporan akurasi, sign-off klien"),
    ("Training pengguna, SOP, serah terima", 2, 0, 0, 1, "SOP checker dan supervisor"),
    ("Manajemen proyek", 8, 0, 0, 0, "Rapat mingguan, laporan progres"),
]
r = ACT0
for i, (act, pm, ai, fs, fe, out) in enumerate(ACTS, 1):
    put(M, f"A{r}", i)
    put(M, f"B{r}", act, wrap=True)
    for col, v in zip("CDEF", (pm, ai, fs, fe)):
        put(M, f"{col}{r}", v, color=BLUE, fmt="0")
    put(M, f"G{r}", f"=C{r}*{RATE['pm']}+D{r}*{RATE['ai']}+E{r}*{RATE['fs']}+F{r}*{RATE['fe']}", fmt=RP)
    put(M, f"H{r}", out, wrap=True, color=GREY)
    r += 1
put(M, f"B{r}", "Total biaya jasa tim CV", bold=True, fill=TOTAL)
for col in "CDEFG":
    put(M, f"{col}{r}", f"=SUM({col}{ACT0}:{col}{r - 1})", bold=True, fmt=RP if col == "G" else "0", fill=TOTAL)
IMPL_TOTAL = f"Implementasi!$G${r}"
r += 2
put(M, f"B{r}", "Durasi proyek dari survey sampai serah terima (bulan), sekitar 8 sampai 10 minggu", italic=True, color="595959")
put(M, f"G{r}", 2.5, color=BLUE, fmt="0.0")
DURATION = f"Implementasi!$G${r}"

# ------------------------------------------------------------------ Layanan (support)
L = sheet("Layanan", [52, 9, 9, 9, 9, 16, 40])
title(L, "Layanan Support oleh Tim CV (on-site, tanpa cloud)", "Hari kerja per bulan x tarif harian di sheet Implementasi. Skenario A: garansi software 3 bulan. Skenario B: selama masa langganan.")
header(L, 4, ["Kegiatan per bulan", "PM", "AI/CV", "Fullstack", "Teknisi", "Biaya per bulan (Rp)", "Keterangan"])
SUPPORT = [
    ("Kunjungan rutin: cek kamera, bersihkan lensa, cek server dan rekaman", 0, 0.5, 0, 1, "1 kali per bulan"),
    ("Pemantauan akurasi dan retraining model", 0, 1, 0, 0, "Rata-rata per bulan"),
    ("Perbaikan dan update web app", 0, 0, 0.5, 0, "Rata-rata per bulan"),
    ("Laporan bulanan dan koordinasi dengan klien", 0.25, 0, 0, 0, ""),
]
r = 5
for act, pm, ai, fs, fe, note in SUPPORT:
    put(L, f"A{r}", act, wrap=True)
    for col, v in zip("BCDE", (pm, ai, fs, fe)):
        put(L, f"{col}{r}", v, color=BLUE, fmt="0.00")
    put(L, f"F{r}", f"=B{r}*{RATE['pm']}+C{r}*{RATE['ai']}+D{r}*{RATE['fs']}+E{r}*{RATE['fe']}", fmt=RP)
    put(L, f"G{r}", note, color=GREY)
    r += 1
put(L, f"A{r}", "Total biaya layanan per bulan", bold=True, fill=TOTAL)
put(L, f"F{r}", f"=SUM(F5:F{r - 1})", bold=True, fmt=RP, fill=TOTAL)
SUPPORT_M = f"Layanan!$F${r}"
r += 2
put(L, f"A{r}", "Penggantian perangkat rusak ditanggung garansi pabrikan selama masa garansi masing-masing (lihat spesifikasi produk). Transport kunjungan di luar Jabodetabek ditagihkan sesuai biaya aktual.", wrap=True, italic=True, color="595959")
L.merge_cells(f"A{r}:G{r}")
L.row_dimensions[r].height = 28

# ------------------------------------------------------------------ Keputusan bisnis
K = sheet("Keputusan Bisnis", [58, 14, 70])
title(K, "Keputusan Bisnis (bukan harga)", "Margin, markup, dan masa kontrak adalah kebijakan perusahaan. Ubah di sini, semua angka ikut berubah.")
header(K, 4, ["Parameter", "Nilai", "Keterangan"])
DEC = [
    ("mk_hw", "Markup hardware (skenario A)", 0.15, PCT, "Selisih harga jual perangkat terhadap harga beli."),
    ("mk_inst", "Markup instalasi (skenario A)", 0.20, PCT, "Selisih harga jual instalasi terhadap biaya vendor."),
    ("m_sw", "Margin web app dan AI (skenario A)", 0.40, PCT, "Harga jual = biaya pembangunan / (1 - margin)."),
    ("warranty", "Garansi software termasuk harga (bulan, skenario A)", 3, "0", "Layanan support selama masa garansi, biayanya masuk ke harga."),
    ("n", "Masa kontrak minimum skenario B (bulan)", 36, "0", "Investasi perangkat dan pembangunan dipulihkan merata selama masa ini."),
    ("m_b", "Margin langganan (skenario B)", 0.40, PCT, "Harga langganan = biaya per bulan / (1 - margin)."),
]
DK = {}
r = 5
for key, lab, v, fmt, note in DEC:
    put(K, f"A{r}", lab)
    put(K, f"B{r}", v, color=BLUE, fmt=fmt, fill=YELLOW)
    put(K, f"C{r}", note, wrap=True, color=GREY)
    DK[key] = f"'Keputusan Bisnis'!$B${r}"
    r += 1
put(K, f"A{r + 1}", "PPN efektif (S19)")
put(K, f"B{r + 1}", 0.11, color=BLUE, fmt=PCT)
put(K, f"C{r + 1}", "Ditambahkan di invoice. Untuk jasa dan sewa (skenario B), klien memotong PPh 23 sebesar 2%.", wrap=True, color=GREY)
DK["ppn"] = f"'Keputusan Bisnis'!$B${r + 1}"


def line(ws, row, label, formula, fmt=RP, bold=False, fill=None, note=None, color=BLACK):
    put(ws, f"A{row}", label, bold=bold, fill=fill, wrap=True)
    put(ws, f"B{row}", formula, fmt=fmt, bold=bold, fill=fill, color=color)
    if note:
        put(ws, f"C{row}", note, wrap=True, color=GREY)


# ------------------------------------------------------------------ Skenario A
SA = sheet("Skenario A", [60, 18, 62])
title(SA, "Skenario A: Beli Putus", "Klien membeli semua: kamera, NVR, PC server, instalasi, web app dan AI. Semua menjadi inventaris Minyakita. Sekali bayar.")
section(SA, 4, "1. Biaya kita", 3)
line(SA, 5, "Hardware", f"={HW_TOTAL}", color=GREEN)
line(SA, 6, "Instalasi", f"={INST_TOTAL}", color=GREEN)
line(SA, 7, "Jasa tim CV: pembangunan web app, AI, dan implementasi", f"={IMPL_TOTAL}", color=GREEN)
line(SA, 8, "Jasa tim CV: support selama garansi software", f"={SUPPORT_M}*{DK['warranty']}", color=GREEN)
line(SA, 9, "Total biaya kita", "=SUM(B5:B8)", bold=True, fill=TOTAL)
section(SA, 11, "2. Harga ke klien", 3)
line(SA, 12, "Hardware", f"=B5*(1+{DK['mk_hw']})")
line(SA, 13, "Instalasi", f"=B6*(1+{DK['mk_inst']})")
line(SA, 14, "Lisensi web app dan AI (selamanya, 1 lokasi, 8 kamera) + implementasi + garansi", f"=ROUNDUP((B7+B8)/(1-{DK['m_sw']}),-6)")
line(SA, 15, "Total harga (sebelum PPN)", "=SUM(B12:B14)", bold=True, fill=TOTAL)
line(SA, 16, "PPN", f"=B15*{DK['ppn']}")
line(SA, 17, "Total tagihan (termasuk PPN)", "=B15+B16", bold=True)
section(SA, 19, "3. Keuntungan", 3)
line(SA, 20, "Laba kotor proyek", "=B15-B9", bold=True, fill=TOTAL)
line(SA, 21, "Margin", "=IF(B15=0,0,B20/B15)", fmt=PCT)
line(SA, 22, "Laba per bulan selama pengerjaan proyek", f"=B20/{DURATION}", note="Laba proyek dibagi durasi pengerjaan di sheet Implementasi.")
section(SA, 24, "4. Termin pembayaran yang diusulkan", 3)
line(SA, 25, "DP 50% saat PO (membiayai pembelian hardware)", "=B17*50%")
line(SA, 26, "30% saat instalasi selesai", "=B17*30%")
line(SA, 27, "20% setelah UAT dan serah terima", "=B17*20%")
line(SA, 28, "Setelah masa garansi: kontrak maintenance opsional", f"=ROUNDUP({SUPPORT_M}*12/(1-{DK['m_sw']}),-6)",
     note="Per tahun, jika klien ingin support berlanjut. Tidak termasuk dalam harga beli putus.")

# ------------------------------------------------------------------ Skenario B
SB = sheet("Skenario B", [60, 18, 62])
title(SB, "Skenario B: Langganan per Tahun", "Semua infrastruktur milik kita (kamera, NVR, PC server). Klien menyewa beserta web app, AI, dan layanan support. Ditagih per tahun di muka.")
section(SB, 4, "1. Investasi kita di depan", 3)
line(SB, 5, "Hardware", f"={HW_TOTAL}", color=GREEN)
line(SB, 6, "Instalasi", f"={INST_TOTAL}", color=GREEN)
line(SB, 7, "Jasa tim CV: pembangunan web app, AI, dan implementasi", f"={IMPL_TOTAL}", color=GREEN)
line(SB, 8, "Total investasi", "=SUM(B5:B7)", bold=True, fill=TOTAL)
section(SB, 10, "2. Biaya per bulan", 3)
line(SB, 11, "Pemulihan investasi per bulan", f"=B8/{DK['n']}", note="Dibagi rata selama masa kontrak minimum.")
line(SB, 12, "Jasa tim CV: layanan support", f"={SUPPORT_M}", color=GREEN)
line(SB, 13, "Total biaya per bulan", "=B11+B12", bold=True, fill=TOTAL)
section(SB, 15, "3. Harga ke klien", 3)
line(SB, 16, "Langganan per tahun (sebelum PPN)", f"=ROUNDUP(B13*12/(1-{DK['m_b']}),-6)", bold=True, fill=TOTAL)
line(SB, 17, "Setara per bulan", "=B16/12")
line(SB, 18, "PPN", f"=B16*{DK['ppn']}")
line(SB, 19, "Tagihan per tahun (termasuk PPN)", "=B16+B18", bold=True)
section(SB, 21, "4. Keuntungan", 3)
line(SB, 22, "Laba per bulan", "=B17-B13", bold=True, fill=TOTAL)
line(SB, 23, "Margin", "=IF(B17=0,0,B22/B17)", fmt=PCT)
line(SB, 24, "Laba per tahun", "=B22*12")
line(SB, 25, "Total laba selama masa kontrak", f"=B22*{DK['n']}")
line(SB, 26, "Balik modal (bulan)", "=IF(B17-B12<=0,0,B8/(B17-B12))", fmt=NUM, note="Investasi / (langganan per bulan - biaya layanan).")
line(SB, 27, "Laba per bulan jika diperpanjang setelah kontrak (perangkat sudah lunas)", "=B17-B12")
section(SB, 29, "5. Arus kas per tahun (langganan dibayar di muka)", 3)
put(SB, "A30", "Tahun", bold=True, color="FFFFFF", fill=HEAD)
put(SB, "B30", "Kas bersih tahun itu (Rp)", bold=True, color="FFFFFF", fill=HEAD)
put(SB, "C30", "Kas kumulatif (Rp)", bold=True, color="FFFFFF", fill=HEAD)
for i in range(3):
    rr = 31 + i
    put(SB, f"A{rr}", f"Tahun {i + 1}")
    first_year = "-B8" if i == 0 else "0"
    put(SB, f"B{rr}", f"={first_year}+B16-B12*12", fmt=RP)
    put(SB, f"C{rr}", f"=B{rr}" if i == 0 else f"=C{rr - 1}+B{rr}", fmt=RP)

# ------------------------------------------------------------------ Ringkasan
R = sheet("Ringkasan", [50, 26, 26])
title(R, "Ringkasan: Hitung Karton per Palet di Loading Dock, 8 Kamera, On-Premise", "Semua harga dari sumber publik (sheet Sumber Harga). Tidak ada cloud; seluruh sistem berjalan di lokasi.")
header(R, 4, ["", "A. Beli putus", "B. Langganan per tahun"])
SUM = [
    ("Pemilik perangkat", '="Minyakita (inventaris klien)"', '="Kita (disewakan)"', None),
    ("Investasi / biaya kita", "='Skenario A'!B9", "='Skenario B'!B8", RP),
    ("Harga ke klien (sebelum PPN)", "='Skenario A'!B15", "='Skenario B'!B16", RP),
    ("Satuan harga", '="sekali bayar"', '="per tahun, di muka"', None),
    ("Tagihan termasuk PPN", "='Skenario A'!B17", "='Skenario B'!B19", RP),
    ("Laba", "='Skenario A'!B20", "='Skenario B'!B24", RP),
    ("Satuan laba", '="sekali, per proyek"', '="per tahun"', None),
    ("Laba per bulan (A: selama pengerjaan; B: selama kontrak)", "='Skenario A'!B22", "='Skenario B'!B22", RP),
    ("Margin", "='Skenario A'!B21", "='Skenario B'!B23", PCT),
    ("Balik modal (bulan)", '="langsung (DP 50%)"', "='Skenario B'!B26", NUM),
    ("Total dibayar klien selama 36 bulan (sebelum PPN)", "='Skenario A'!B15", f"='Skenario B'!B16*{DK['n']}/12", RP),
    ("Total laba kita selama 36 bulan", "='Skenario A'!B20", "='Skenario B'!B25", RP),
    ("Jasa tim CV di dalam biaya, 36 bulan", "='Skenario A'!B7+'Skenario A'!B8", f"='Skenario B'!B7+'Skenario B'!B12*{DK['n']}", RP),
    ("Total diterima tim CV selama 36 bulan (jasa tim + laba)", "='Skenario A'!B7+'Skenario A'!B8+'Skenario A'!B20", f"='Skenario B'!B7+'Skenario B'!B12*{DK['n']}+'Skenario B'!B25", RP),
    ("Laba per bulan setelah kontrak diperpanjang", '="-"', "='Skenario B'!B27", RP),
]
r = 5
for lab, fa, fb, fmt in SUM:
    put(R, f"A{r}", lab, bold=True)
    for col, f in zip("BC", (fa, fb)):
        put(R, f"{col}{r}", f, color=GREEN, fmt=fmt, right=True)
    r += 1
r += 1
put(R, f"A{r}", "Isi paket di kedua skenario", bold=True)
for n in [
    "8 IP camera 4MP, NVR 8 kanal + HDD 8 TB (rekaman bukti), PC server AI dengan GPU 16 GB, UPS online 2 kVA, rack, switch, monitor dashboard, layar status di dock.",
    "Web app on-premise: dashboard per dock, input DO, hitung karton per palet (60 karton), alert palet kurang, laporan per DO, truk, dan palet.",
    "Instalasi 8 titik, kalibrasi, UAT paralel 2 minggu, training pengguna dan SOP.",
    "Tidak termasuk: listrik, alat kerja ketinggian, pekerjaan sipil, transport di luar Jabodetabek.",
]:
    r += 1
    put(R, f"A{r}", "• " + n, wrap=True, color=GREY)
    R.merge_cells(f"A{r}:C{r}")
    R.row_dimensions[r].height = 28

wb.move_sheet("Ringkasan", offset=-(len(wb.sheetnames) - 1))
wb.active = 0
for ws in wb.worksheets:
    ws.freeze_panes = "A5"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
wb.save(OUT)
print(OUT)
