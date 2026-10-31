"""RAB: cafe video analytics for a small business (UMKM), 4 fixed cameras, on-premise.

Cashier at the till or not (and for how long), staff face recognition, people counting, staff vs customer:
the same analytics as projects/05_cafe_dwell_time. Two scenarios:
A = the cafe already has a PC that can be the AI server; B = we supply the PC server.
Layout follows the RAB slides of Factory_Vision_Presentation.pptx: Kategori, Komponen, Merek/Tipe, Spesifikasi,
Harga satuan, Link. Every price has a public source on the 'Sumber Harga' sheet.

    python build_rab.py   # -> RAB_Cafe_Vision_4_Kamera.xlsx (then recalc with LibreOffice)
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().parent / "RAB_Cafe_Vision_4_Kamera.xlsx"
ACCESSED = "31 Okt 2026"
F = "Arial"
BLUE, GREEN, BLACK, GREY = "0000FF", "008000", "000000", "404040"
YELLOW = PatternFill("solid", fgColor="FFFF00")
HEAD = PatternFill("solid", fgColor="1F3864")
SUB = PatternFill("solid", fgColor="D9E1F2")
TOTAL = PatternFill("solid", fgColor="F2F2F2")
RP = '#,##0;(#,##0);"-"'
PCT = '0.0%;(0.0%);"-"'
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


def note(ws, row, text, ncols, height=28):
    put(ws, f"A{row}", text, wrap=True, italic=True, color="595959")
    ws.merge_cells(f"A{row}:{get_column_letter(ncols)}{row}")
    ws.row_dimensions[row].height = height


# ------------------------------------------------------------------ Sumber Harga
SRC = [
    ("S1", "Factory_Vision_Presentation.pptx, slide RAB 3/3: Hikvision DS-2CD2143G2-IU Rp 1.687.000; APC Easy UPS BVX1200LI-MS Rp 1.975.000 (Tokopedia, dicek 12 Okt 2026)",
     "https://www.tokopedia.com/find/ds-2cd2143g2-iu"),
    ("S2", "Nale.co.id, Hikvision 4-ch 1U 4 PoE 4K NVR (DS-7604NI-K1/4P): Rp 2.459.451", "https://nale.co.id/?p=14506"),
    ("S3", "Viraindo (Vira Jaya Computer), daftar harga storage", "https://www.viraindo.com/storage.html"),
    ("S4", "Viraindo, daftar harga processor", "https://www.viraindo.com/proc.html"),
    ("S5", "Viraindo, daftar harga motherboard", "https://www.viraindo.com/motherboard.html"),
    ("S6", "Viraindo, daftar harga memory", "https://www.viraindo.com/memory.html"),
    ("S7", "Viraindo, daftar harga VGA", "https://www.viraindo.com/vga.html"),
    ("S8", "Viraindo, daftar harga power supply", "https://www.viraindo.com/psu.html"),
    ("S9", "Viraindo, daftar harga casing", "https://www.viraindo.com/casing.html"),
    ("S10", "Viraindo, daftar harga monitor", "https://www.viraindo.com/lcd.html"),
    ("S11", "Viraindo, daftar harga keyboard dan mouse", "https://www.viraindo.com/keymouse.html"),
    ("S12", "Viraindo, daftar harga networking", "https://www.viraindo.com/networking.html"),
    ("S13", "GSI Indonesia, Harga Pasang CCTV Per Titik 2026 (17 Apr 2026): IP camera jasa + material Rp 900.000 sampai Rp 1.500.000 per titik. Dipakai batas atas.",
     "https://gsi-indo.com/2026/04/17/harga-pasang-cctv-per-titik/"),
    ("S14", "Second Talent, Cost to Hire a Software Developer in Indonesia (25 Sep 2026): Machine Learning Engineer mid-level USD 33 sampai 86 per jam; 160 jam per bulan",
     "https://www.secondtalent.com/resources/cost-to-hire-a-software-developer-in-indonesia/"),
    ("S15", "Bank Indonesia, kurs JISDOR USD/IDR 30 Oktober 2026: Rp 18.138", "https://www.bi.go.id/id/statistik/informasi-kurs/jisdor/default.aspx"),
    ("S16", "servicecctv.id, Biaya Layanan CCTV 2026: kunjungan teknisi dan pengecekan Rp 150.000 (Jabodetabek)", "https://servicecctv.id/biaya-layanan-cctv/"),
    ("S17", "PMK No. 131 Tahun 2024: PPN efektif 11% (12% x DPP 11/12). Hanya ditagihkan bila CV sudah PKP.", "Peraturan Menteri Keuangan No. 131 Tahun 2024"),
]
SS = sheet("Sumber Harga", [7, 95, 70])
title(SS, "Sumber Harga", f"Harga dari sumber publik, diakses {ACCESSED} (kecuali disebut lain). Harga toko dapat berubah; minta penawaran tertulis sebelum membeli.")
header(SS, 4, ["Kode", "Sumber dan angka yang dipakai", "Tautan / dasar hukum"])
for i, (code, desc, url) in enumerate(SRC, 5):
    put(SS, f"A{i}", code, bold=True)
    put(SS, f"B{i}", desc, wrap=True)
    put(SS, f"C{i}", url, wrap=True, color="0563C1" if url.startswith("http") else GREY)
    if url.startswith("http"):
        SS[f"C{i}"].hyperlink = url

# ------------------------------------------------------------------ Keputusan Bisnis (fixed rows, referenced by address)
K = sheet("Keputusan Bisnis", [62, 14, 70])
title(K, "Keputusan Bisnis (bukan harga)", "Kebijakan CV. Ubah di sini, semua angka ikut berubah.")
header(K, 4, ["Parameter", "Nilai", "Keterangan"])
DEC = [
    ("cont", "Kontinjensi harga perangkat", 0.10, PCT, "Sama dengan RAB di pptx: cadangan fluktuasi harga RAM, GPU, storage (rupiah sedang melemah)."),
    ("mk_hw", "Markup perangkat", 0.15, PCT, "Selisih harga jual perangkat terhadap harga beli + kontinjensi."),
    ("mk_inst", "Markup instalasi", 0.20, PCT, "Selisih harga jual instalasi terhadap biaya vendor."),
    ("ratepos", "Posisi tarif jasa dalam rentang sumber (0 = bawah, 1 = atas)", 0, "0.00", "0 = batas bawah rentang tarif pasar."),
    ("comm", "Komisi tim pemasaran (3 orang), dari nilai kontrak sebelum PPN", 0.10, PCT, "Dibagi rata ke 3 orang. Dimasukkan ke harga jual."),
    ("warranty", "Garansi layanan termasuk harga (bulan)", 1, "0", "Support setelah serah terima, termasuk harga."),
    ("ppn", "PPN efektif (S17), isi 0 bila CV belum PKP", 0.11, PCT, "CV dengan omzet di bawah Rp 4,8 miliar per tahun boleh tidak PKP, sehingga tidak memungut PPN."),
]
DK = {}
for i, (key, lab, v, fmt, nt) in enumerate(DEC, 5):
    put(K, f"A{i}", lab)
    put(K, f"B{i}", v, color=BLUE, fmt=fmt, fill=YELLOW)
    put(K, f"C{i}", nt, wrap=True, color=GREY)
    DK[key] = f"'Keputusan Bisnis'!$B${i}"

# ------------------------------------------------------------------ RAB (format pptx)
RB = sheet("RAB", [16, 24, 40, 52, 7, 7, 15, 16, 16, 7])
title(RB, "RAB Infrastruktur On-Premise, Cafe 4 Kamera", "Format mengikuti slide RAB di Factory_Vision_Presentation.pptx. Qty A = PC server sudah ada. Qty B = PC server dari kita.")
header(RB, 4, ["Kategori", "Komponen", "Merek / Tipe", "Spesifikasi kunci", "Qty A", "Qty B", "Harga satuan (Rp)", "Total A (Rp)", "Total B (Rp)", "Sumber"])
ITEMS = [
    ("CCTV & rekaman", [
        ("Kamera IP CCTV", "Hikvision DS-2CD2143G2-IU (AcuSense)", "4MP dome, lensa 2,8 mm, H.264/H.265+, IR 30 m, WDR 120 dB, PoE, RTSP/ONVIF, mic", 4, 4, 1687000, "S1"),
        ("NVR 4 kanal PoE", "Hikvision DS-7604NI-K1/4P", "4 kanal, 4 port PoE (menyalakan kamera), rekaman 4K, 1 bay HDD, akses aplikasi HP", 1, 1, 2459451, "S2"),
        ("HDD rekaman", "Seagate 3.5\" Surveillance 4 TB Sata SkyHawk Series", "Kelas surveillance 24/7, sekitar 30 hari rekaman 4 kamera", 1, 1, 3500000, "S3"),
        ("Switch jaringan", "TP-Link TL-SG108", "8 port gigabit, menghubungkan NVR, PC server, router cafe", 1, 1, 310000, "S12"),
    ]),
    ("PC server AI (skenario B)", [
        ("Prosesor (CPU)", "AMD Ryzen 7600 [Box] 100-100001015BOX".replace("Ryzen 7600", "Ryzen 5 7600"), "6 core, 3,8 sampai 5,1 GHz, AM5, 65W, termasuk Wraith Stealth Cooler", 0, 1, 3300000, "S4"),
        ("Motherboard", "MSI PRO B650M-B", "AM5, chipset B650, DDR5, micro-ATX", 0, 1, 1785000, "S5"),
        ("Memori (RAM)", "Kingston FURY Beast DDR5 6000MHz 16GB (2x8GB) KF560C30BBAK2-16", "16 GB DDR5-6000, cukup untuk AI 4 kamera + web app + database", 0, 1, 1550000, "S6"),
        ("Kartu grafis (GPU)", "MSI GeForce RTX 3060 12 GB GDDR6 - Ventus 2X OC", "12 GB VRAM: deteksi orang, tracking, dan face recognition 4 kamera secara realtime", 0, 1, 5500000, "S7"),
        ("SSD NVMe (OS + database)", "Kingston SSD NV3 500GB M.2 NVMe PCIe Gen 4.0 x4", "500 GB, sistem, aplikasi, database, foto bukti", 0, 1, 1800000, "S3"),
        ("Power supply (PSU)", "Cooler Master MWE Bronze 550W V3 230V 80+ Bronze", "550 W, cukup untuk RTX 3060 (170 W) + CPU 65 W", 0, 1, 670000, "S8"),
        ("Casing", "Cooler Master MasterBox TD500 Mesh V2", "Mid tower, panel depan mesh untuk aliran udara 24 jam", 0, 1, 1240000, "S9"),
        ("Monitor", "Xiaomi A24i 23.8 FHD IPS 100Hz Monitor", "Layar dashboard di meja pemilik atau kasir", 0, 1, 1045000, "S10"),
        ("Keyboard & mouse", "Logitech Classic MK120 USB (K120 + B100)", "Kabel USB", 0, 1, 165000, "S11"),
        ("UPS server", "APC Easy UPS BVX1200LI-MS", "1200 VA / 650 W, AVR, untuk PC server dan NVR", 0, 1, 1975000, "S1"),
        ("Sistem operasi & software", "Ubuntu Server 24.04 LTS, driver NVIDIA, PostgreSQL, MediaMTX", "Open source, tanpa biaya lisensi", 0, 1, 0, "-"),
    ]),
    ("Opsi upgrade PC klien (skenario A, isi Qty A = 1 bila perlu)", [
        ("Kartu grafis (GPU)", "MSI GeForce RTX 3060 12 GB GDDR6 - Ventus 2X OC", "Wajib bila PC klien belum punya GPU NVIDIA minimal 8 GB VRAM", 0, 0, 5500000, "S7"),
        ("Power supply (PSU)", "Cooler Master MWE Bronze 550W V3 230V 80+ Bronze", "Bila PSU PC klien di bawah 550 W", 0, 0, 670000, "S8"),
        ("UPS", "APC Easy UPS BVX1200LI-MS", "Bila PC klien belum memakai UPS", 0, 0, 1975000, "S1"),
    ]),
]
r = 5
HW_ROWS = []
for cat, rows in ITEMS:
    section(RB, r, cat, 10)
    r += 1
    for comp, brand, spec, qa, qb, price, src in rows:
        put(RB, f"A{r}", cat.split(" (")[0], color=GREY)
        put(RB, f"B{r}", comp, wrap=True)
        put(RB, f"C{r}", brand, wrap=True)
        put(RB, f"D{r}", spec, wrap=True, color=GREY)
        put(RB, f"E{r}", qa, color=BLUE, fmt="0")
        put(RB, f"F{r}", qb, color=BLUE, fmt="0")
        put(RB, f"G{r}", price, color=BLUE, fmt=RP)
        put(RB, f"H{r}", f"=E{r}*G{r}", fmt=RP)
        put(RB, f"I{r}", f"=F{r}*G{r}", fmt=RP)
        put(RB, f"J{r}", src)
        HW_ROWS.append(r)
        r += 1
put(RB, f"B{r}", "Subtotal perangkat", bold=True, fill=TOTAL)
put(RB, f"H{r}", f"=SUM(H5:H{r - 1})", bold=True, fmt=RP, fill=TOTAL)
put(RB, f"I{r}", f"=SUM(I5:I{r - 1})", bold=True, fmt=RP, fill=TOTAL)
HW_A, HW_B = f"RAB!$H${r}", f"RAB!$I${r}"
r += 1
put(RB, f"B{r}", "Kontinjensi (fluktuasi harga perangkat)")
put(RB, f"H{r}", f"=H{r - 1}*{DK['cont']}", fmt=RP)
put(RB, f"I{r}", f"=I{r - 1}*{DK['cont']}", fmt=RP)
CONT_A, CONT_B = f"RAB!$H${r}", f"RAB!$I${r}"
r += 2
section(RB, r, "Instalasi", 10)
r += 1
put(RB, f"A{r}", "Instalasi", color=GREY)
put(RB, f"B{r}", "Jasa + material pasang IP camera", wrap=True)
put(RB, f"C{r}", "Per titik kamera")
put(RB, f"D{r}", "Termasuk kabel standar, konektor, bracket, pemasangan, setting sudut", wrap=True, color=GREY)
put(RB, f"E{r}", 4, color=BLUE, fmt="0")
put(RB, f"F{r}", 4, color=BLUE, fmt="0")
put(RB, f"G{r}", 1500000, color=BLUE, fmt=RP)
put(RB, f"H{r}", f"=E{r}*G{r}", fmt=RP)
put(RB, f"I{r}", f"=F{r}*G{r}", fmt=RP)
put(RB, f"J{r}", "S13")
INST_A, INST_B = f"RAB!$H${r}", f"RAB!$I${r}"
r += 2
note(RB, r, "Tidak termasuk: listrik, internet cafe, pekerjaan sipil. Harga toko umumnya sudah termasuk PPN masukan.", 10)

# ------------------------------------------------------------------ Jasa
J = sheet("Jasa Implementor", [5, 64, 10, 10, 18, 18, 30])
title(J, "Jasa Implementor Lapangan + Fullstack Computer Vision", "Dikerjakan satu orang (implementor). Tarif jual pasar: USD per jam x kurs JISDOR x 8 jam per hari.")
header(J, 4, ["", "Komponen tarif", "", "", "Nilai", "", "Sumber"])
put(J, "B5", "Tarif USD per jam, batas bawah (ML Engineer mid-level)")
put(J, "E5", 33, color=BLUE, fmt="0")
put(J, "G5", "S14")
put(J, "B6", "Tarif USD per jam, batas atas")
put(J, "E6", 86, color=BLUE, fmt="0")
put(J, "G6", "S14")
put(J, "B7", "Kurs USD/IDR (JISDOR 30 Okt 2026)")
put(J, "E7", 18138, color=BLUE, fmt=RP)
put(J, "G7", "S15")
put(J, "B8", "Jam kerja per hari")
put(J, "E8", 8, color=BLUE, fmt="0")
put(J, "G8", "S14: 160 jam per bulan")
put(J, "B9", "Tarif per hari (Rp)", bold=True, fill=TOTAL)
put(J, "E9", f"=(E5+(E6-E5)*{DK['ratepos']})*E8*E7", bold=True, fmt=RP, fill=TOTAL)
RATE = "'Jasa Implementor'!$E$9"
header(J, 11, ["No", "Pekerjaan", "Hari A", "Hari B", "Nilai A (Rp)", "Nilai B (Rp)", "Hasil"])
ACTS = [
    ("Survey lokasi, desain posisi 4 kamera (meja kasir, pintu masuk, area meja, bar)", 0.5, 0.5, "Denah posisi kamera"),
    ("Pengawasan instalasi kamera dan setting NVR", 1, 1, "Kamera dan rekaman jalan"),
    ("A: cek kelayakan dan setup PC klien (driver, Ubuntu). B: rakit dan setup PC server baru", 1, 1, "Server AI siap"),
    ("Deploy aplikasi AI + web app, sambung 4 kamera", 0.5, 0.5, "Sistem berjalan di lokasi"),
    ("Setting zona: meja kasir, area layanan, garis hitung di pintu masuk", 0.5, 0.5, "Zona dan garis hitung"),
    ("Pendaftaran wajah kasir dan pelayan (dengan persetujuan tertulis) + uji face recognition", 0.5, 0.5, "Data wajah staf"),
    ("Tuning model di kondisi cafe (cahaya, sudut, seragam staf)", 2, 2, "Akurasi sesuai kondisi cafe"),
    ("Kustomisasi web app: data staf, shift, laporan harian, notifikasi", 1.5, 1.5, "Dashboard dan laporan"),
    ("Uji coba 1 minggu dibanding pengecekan manual", 2, 2, "Laporan akurasi, persetujuan pemilik"),
    ("Training pemilik dan staf, serah terima", 0.5, 0.5, "Pemilik bisa memakai sendiri"),
]
r = 12
for i, (act, da, db, out) in enumerate(ACTS, 1):
    put(J, f"A{r}", i)
    put(J, f"B{r}", act, wrap=True)
    put(J, f"C{r}", da, color=BLUE, fmt="0.0")
    put(J, f"D{r}", db, color=BLUE, fmt="0.0")
    put(J, f"E{r}", f"=C{r}*{RATE}", fmt=RP)
    put(J, f"F{r}", f"=D{r}*{RATE}", fmt=RP)
    put(J, f"G{r}", out, wrap=True, color=GREY)
    r += 1
put(J, f"B{r}", "Total jasa implementor", bold=True, fill=TOTAL)
for col, fmt in (("C", "0.0"), ("D", "0.0"), ("E", RP), ("F", RP)):
    put(J, f"{col}{r}", f"=SUM({col}12:{col}{r - 1})", bold=True, fmt=fmt, fill=TOTAL)
JASA_A, JASA_B = f"'Jasa Implementor'!$E${r}", f"'Jasa Implementor'!$F${r}"
r += 2
section(J, r, "Layanan support per bulan (garansi dan maintenance)", 7)
r += 1
put(J, f"B{r}", "Pemantauan dan perbaikan jarak jauh (hari implementor)")
put(J, f"C{r}", 0.5, color=BLUE, fmt="0.0")
put(J, f"E{r}", f"=C{r}*{RATE}", fmt=RP)
r += 1
put(J, f"B{r}", "Kunjungan teknisi: cek kamera, bersihkan lensa (S16)")
put(J, f"C{r}", 1, color=BLUE, fmt="0")
put(J, f"E{r}", f"=C{r}*150000", fmt=RP)
put(J, f"G{r}", "Rp 150.000 per kunjungan, S16", color=GREY)
r += 1
put(J, f"B{r}", "Total layanan per bulan", bold=True, fill=TOTAL)
put(J, f"E{r}", f"=E{r - 2}+E{r - 1}", bold=True, fmt=RP, fill=TOTAL)
SUPPORT = f"'Jasa Implementor'!$E${r}"


def line(ws, row, label, formula, fmt=RP, bold=False, fill=None, nt=None, color=BLACK):
    put(ws, f"A{row}", label, bold=bold, fill=fill, wrap=True)
    put(ws, f"B{row}", formula, fmt=fmt, bold=bold, fill=fill, color=color)
    if nt:
        put(ws, f"C{row}", nt, wrap=True, color=GREY)


def scenario(name, ttl, sub, hw, cont, inst, jasa):
    ws = sheet(name, [62, 18, 60])
    title(ws, ttl, sub)
    section(ws, 4, "1. Uang keluar ke vendor", 3)
    line(ws, 5, "Perangkat", f"={hw}", color=GREEN)
    line(ws, 6, "Kontinjensi perangkat", f"={cont}", color=GREEN)
    line(ws, 7, "Instalasi", f"={inst}", color=GREEN)
    line(ws, 8, "Total uang keluar", "=SUM(B5:B7)", bold=True, fill=TOTAL)
    section(ws, 10, "2. Harga ke klien", 3)
    line(ws, 11, "Perangkat", f"=(B5+B6)*(1+{DK['mk_hw']})")
    line(ws, 12, "Instalasi 4 titik", f"=B7*(1+{DK['mk_inst']})")
    line(ws, 13, "Jasa implementasi, web app dan AI (lisensi 1 lokasi, 4 kamera)", f"={jasa}", color=GREEN)
    line(ws, 14, "Garansi layanan", f"={SUPPORT}*{DK['warranty']}", color=GREEN)
    line(ws, 15, "Subtotal sebelum komisi", "=SUM(B11:B14)")
    line(ws, 16, "Total harga (sebelum PPN), termasuk komisi pemasaran", f"=ROUNDUP(B15/(1-{DK['comm']}),-5)", bold=True, fill=TOTAL,
         nt="Dibulatkan ke atas ke Rp 100.000.")
    line(ws, 17, "PPN", f"=B16*{DK['ppn']}")
    line(ws, 18, "Total tagihan", "=B16+B17", bold=True)
    section(ws, 20, "3. Pembagian pendapatan tim", 3)
    line(ws, 21, "Komisi tim pemasaran (3 orang)", f"=B16*{DK['comm']}")
    line(ws, 22, "Per orang pemasaran", "=B21/3")
    line(ws, 23, "Jasa implementor (lapangan + fullstack CV)", "=B13+B14")
    line(ws, 24, "Kas CV (margin perangkat dan instalasi, pembulatan)", "=B16-B8-B21-B23")
    line(ws, 25, "Total pendapatan tim (komisi + jasa + kas CV)", "=B21+B23+B24", bold=True, fill=TOTAL, nt="Sebelum pajak penghasilan.")
    line(ws, 26, "Setara per bulan dalam 1 tahun", "=B25/12", bold=True)
    section(ws, 28, "4. Termin pembayaran yang diusulkan", 3)
    line(ws, 29, "DP 50% saat PO (membiayai pembelian perangkat)", "=B18*50%")
    line(ws, 30, "50% setelah uji coba dan serah terima", "=B18*50%")
    line(ws, 31, "Maintenance opsional per bulan setelah garansi", f"=ROUNDUP({SUPPORT},-5)", nt="Tidak termasuk dalam harga di atas.")
    return ws


scenario("Skenario A", "Skenario A: PC Server Sudah Ada di Cafe", "Kita pasang 4 kamera, NVR, instalasi, dan memasang aplikasi di PC milik cafe yang memenuhi syarat (sheet Syarat PC).",
         HW_A, CONT_A, INST_A, JASA_A)
scenario("Skenario B", "Skenario B: PC Server dari Kita", "Kita pasang 4 kamera, NVR, instalasi, dan PC server AI baru. Semua menjadi milik cafe.",
         HW_B, CONT_B, INST_B, JASA_B)

# ------------------------------------------------------------------ Syarat PC
P = sheet("Syarat PC", [30, 46, 60])
title(P, "Syarat Minimum PC Server Milik Cafe (Skenario A)", "Bila tidak terpenuhi, isi Qty A pada bagian 'Opsi upgrade PC klien' di sheet RAB.")
header(P, 4, ["Komponen", "Minimum", "Alasan"])
for i, (k, v, why) in enumerate([
    ("GPU", "NVIDIA, minimal 8 GB VRAM (contoh RTX 3060 12 GB, RTX 4060, RTX 5060)", "Deteksi orang, tracking, dan face recognition 4 kamera secara realtime. PC tanpa GPU NVIDIA tidak cukup."),
    ("CPU", "6 core generasi 2020 ke atas", "Decode 4 stream video dan web app."),
    ("RAM", "16 GB", "AI, database, dan web app berjalan bersamaan."),
    ("Penyimpanan", "SSD 500 GB kosong", "Sistem, database, foto bukti. Rekaman video tetap di NVR."),
    ("Power supply", "550 W", "Beban GPU 24 jam."),
    ("Pemakaian", "Khusus server, menyala 24 jam", "Jangan dipakai bersamaan untuk kasir/POS: bila PC hang, kasir ikut terganggu."),
    ("Jaringan", "Port LAN gigabit", "Tersambung ke switch yang sama dengan NVR."),
], 5):
    put(P, f"A{i}", k, bold=True)
    put(P, f"B{i}", v, wrap=True)
    put(P, f"C{i}", why, wrap=True, color=GREY)
    P.row_dimensions[i].height = 28

# ------------------------------------------------------------------ Ringkasan
R = sheet("Ringkasan", [52, 24, 24])
title(R, "Ringkasan RAB: Cafe Vision, 4 Kamera, On-Premise", "Kasir di meja kasir dan berapa lama, face recognition staf, hitung pengunjung, beda pelayan dan pelanggan.")
header(R, 4, ["", "A. PC server sudah ada", "B. PC server dari kita"])
SUM = [
    ("Uang keluar ke vendor", "='Skenario A'!B8", "='Skenario B'!B8", RP),
    ("Total harga ke klien (sebelum PPN)", "='Skenario A'!B16", "='Skenario B'!B16", RP),
    ("Total tagihan (dengan PPN bila CV PKP)", "='Skenario A'!B18", "='Skenario B'!B18", RP),
    ("Komisi pemasaran, total 3 orang", "='Skenario A'!B21", "='Skenario B'!B21", RP),
    ("Komisi per orang pemasaran", "='Skenario A'!B22", "='Skenario B'!B22", RP),
    ("Jasa implementor (lapangan + fullstack CV)", "='Skenario A'!B23", "='Skenario B'!B23", RP),
    ("Kas CV", "='Skenario A'!B24", "='Skenario B'!B24", RP),
    ("Total pendapatan tim", "='Skenario A'!B25", "='Skenario B'!B25", RP),
    ("Setara per bulan dalam 1 tahun", "='Skenario A'!B26", "='Skenario B'!B26", RP),
    ("Maintenance opsional per bulan setelah garansi", "='Skenario A'!B31", "='Skenario B'!B31", RP),
]
r = 5
for lab, fa, fb, fmt in SUM:
    put(R, f"A{r}", lab, bold=True)
    put(R, f"B{r}", fa, color=GREEN, fmt=fmt, right=True)
    put(R, f"C{r}", fb, color=GREEN, fmt=fmt, right=True)
    r += 1
r += 1
put(R, f"A{r}", "Catatan penting", bold=True)
for n in [
    "Face recognition hanya untuk staf yang sudah memberi persetujuan tertulis. Wajah pelanggan tidak didaftarkan dan tidak disimpan. Data wajah termasuk data pribadi spesifik menurut UU PDP. Pasang pemberitahuan CCTV di cafe.",
    "Model face recognition dipakai yang berlisensi bebas untuk komersial (misalnya YuNet dan SFace, Apache 2.0). Bila memakai Ultralytics YOLO (AGPL) untuk produk tertutup, perlu lisensi enterprise Ultralytics.",
    "Skenario A hanya berlaku bila PC cafe memenuhi sheet Syarat PC. Bila tidak, tambahkan GPU, PSU, atau UPS lewat Qty A di sheet RAB.",
    "Bila CV belum PKP, isi PPN = 0 di sheet Keputusan Bisnis.",
]:
    r += 1
    put(R, f"A{r}", "• " + n, wrap=True, color=GREY)
    R.merge_cells(f"A{r}:C{r}")
    R.row_dimensions[r].height = 42

order = ["Ringkasan", "RAB", "Jasa Implementor", "Skenario A", "Skenario B", "Syarat PC", "Keputusan Bisnis", "Sumber Harga"]
wb._sheets = [wb[n] for n in order]
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
