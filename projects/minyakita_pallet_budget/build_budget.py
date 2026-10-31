"""Budget workbook: Minyakita pallet box counting at the loading dock, 8 cameras at 20-30 fps, on-premise, no cloud.

Layout follows the RAB slides of Factory_Vision_Presentation.pptx (Kategori, Komponen, Merek/Tipe, Spesifikasi kunci,
Harga satuan, Link) with the deck's 10% price contingency. The AI server is an Agres Komputer build. Services are
priced with INKINDO's 2026 minimum billing rates (Pedoman Standar Minimal 2026), converted to a day rate the way the
guideline prescribes (SBOH = SBOB / 22 x 1.1). Two scenarios: A one-off purchase; B a one-off setup fee plus a yearly
subscription (device rental, support, replacement reserve) with a 36-month minimum contract and early-termination fee.

    python build_budget.py   # -> Budget_Minyakita_Pallet_Counting.xlsx (then recalc with LibreOffice)
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().parent / "Budget_Minyakita_Pallet_Counting.xlsx"
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


def line(ws, row, label, formula, fmt=RP, bold=False, fill=None, nt=None, color=BLACK):
    put(ws, f"A{row}", label, bold=bold, fill=fill, wrap=True)
    put(ws, f"B{row}", formula, fmt=fmt, bold=bold, fill=fill, color=color)
    if nt:
        put(ws, f"C{row}", nt, wrap=True, color=GREY)


# ------------------------------------------------------------------ Keputusan Bisnis (fixed addresses)
K = sheet("Keputusan Bisnis", [62, 14, 72])
title(K, "Keputusan Bisnis (bukan harga)", "Kebijakan perusahaan. Ubah di sini, semua angka ikut berubah.")
header(K, 4, ["Parameter", "Nilai", "Keterangan"])
DEC = [
    ("cont", "Kontinjensi harga perangkat", 0.10, PCT, "Sama dengan RAB di Factory_Vision_Presentation.pptx: fluktuasi harga RAM, GPU, storage; rupiah sedang melemah."),
    ("mk_hw", "Markup perangkat", 0.15, PCT, "Atas harga beli + kontinjensi."),
    ("mk_inst", "Markup jasa pasang kamera", 0.20, PCT, "Atas tarif vendor pemasang."),
    ("warranty", "Garansi layanan termasuk harga Opsi A (bulan)", 3, "0", "Support setelah serah terima."),
    ("term", "Kontrak minimum Opsi B (bulan)", 36, "0", "Modal perangkat ditutup selama kontrak minimum; tagihan tetap per 12 bulan di muka."),
    ("m_rent", "Margin sewa perangkat selama kontrak minimum (Opsi B)", 0.40, PCT, "Total sewa selama kontrak = uang keluar perangkat / (1 - margin)."),
    ("spare", "Cadangan pengganti per jenis perangkat yang garansinya habis sebelum kontrak selesai (unit)", 1, "0", "Dipakai di sheet Cadangan Penggantian."),
    ("late", "Batas telat bayar sebelum layanan dihentikan sementara (hari)", 30, "0", "Pengaman pembayaran Opsi B; ditulis di penawaran."),
    ("ppn", "PPN efektif (isi 0 bila belum PKP)", 0.11, PCT, "PMK 131/2024: 12% x DPP 11/12."),
]
DK = {}
for i, (key, lab, v, fmt, nt) in enumerate(DEC, 5):
    put(K, f"A{i}", lab)
    put(K, f"B{i}", v, color=BLUE, fmt=fmt, fill=YELLOW)
    put(K, f"C{i}", nt, wrap=True, color=GREY)
    DK[key] = f"'Keputusan Bisnis'!$B${i}"

# ------------------------------------------------------------------ RAB (format pptx)
RB = sheet("RAB", [15, 22, 36, 50, 6, 15, 15, 15, 16, 36])
title(RB, "RAB Infrastruktur On-Premise, Loading Dock 8 Kamera (20-30 fps realtime)",
      "Format mengikuti slide RAB Factory_Vision_Presentation.pptx. Harga satuan = harga beli; harga jual = harga beli x (1 + kontinjensi) x (1 + markup).")
header(RB, 4, ["Kategori", "Komponen", "Merek / Tipe", "Spesifikasi kunci", "Qty", "Harga satuan (Rp)", "Total (Rp)", "Harga jual satuan (Rp)", "Total jual (Rp)", "Link / sumber"])
TOKO = "https://www.tokopedia.com/find/"
AGRES = "https://www.tokopedia.com/agreskomputerofficial/agres-cryo-pc-ultra-5-245kf-rtx-5070-ti-16g-32gb-1tb-rakitan-pc-gaming-1731083491745892256"
ITEMS = [
    ("Server AI on-prem", [
        ("PC server AI (rakitan Agres)", "AGRES CRYO PC ULTRA 5 245KF RTX 5070 TI 16G / 32GB 1TB",
         "Intel Core Ultra 5 245KF 14 core, NVIDIA GeForce RTX 5070 Ti 16 GB GDDR7 (decode video di GPU + inferensi TensorRT), RAM 32 GB DDR5, SSD NVMe 1 TB. Untuk 8 kamera 4MP pada 20-30 fps.",
         1, 35000000, AGRES),
        ("HDD rekaman video", "WD Purple Pro 8TB", "3,5\" SATA, 7.200 rpm, kelas surveillance/AI 24/7, sekitar 2 minggu rekaman 8 kamera 25 fps", 1, 8006000, TOKO + "wd-purple-pro-8tb"),
        ("HDD backup eksternal", "Seagate Expansion Desktop 12TB (STKP12000400)", "USB 3.0, backup database dan klip bukti", 1, 9980000, TOKO + "seagate-expansion-12tb"),
        ("Sistem operasi & software", "Ubuntu Server 24.04 LTS, driver NVIDIA, TensorRT, MediaMTX, PostgreSQL", "Open source / gratis", 1, 0, "https://docs.nvidia.com/metropolis/deepstream/8.0/text/DS_Installation.html"),
    ]),
    ("Layar loading dock", [
        ("TV status loading dock", "Samsung Business TV BE55FX-H (LH55BEFHVGKXXD)", "55\" 4K, Tizen dengan web browser bawaan (buka dashboard web app langsung via LAN, tanpa PC tambahan), rating 16 jam/hari x 7 hari, garansi 3 tahun", 1, 8899000, TOKO + "samsung-business-tv-55"),
        ("Bracket TV", "Krisbow bracket fixed 32-55\"", "Wall mount", 1, 129000, TOKO + "bracket-tv-55-inch-fixed"),
    ]),
    ("Jaringan", [
        ("Router", "MikroTik RB5009UG+S+IN", "7x GbE, 1x 2.5GbE, 1x SFP+, VLAN kamera terpisah", 1, 4175000, TOKO + "rb5009ug-s-in"),
        ("Switch PoE CCTV", "TP-Link Omada TL-SG2218P", "16x Gigabit PoE+ (budget 150W) + 2x SFP, managed", 1, 4944000, TOKO + "tl-sg2218p"),
        ("Rak jaringan", "Indorack WR5012S", "Wall mount 12U, kedalaman 500mm, pintu kaca", 1, 2280000, TOKO + "indorack-wallmount-12u"),
        ("PDU rak", "Indorack PDU6G", "6 outlet, rack mount 19\"", 1, 395000, TOKO + "pdu-indorack"),
        ("Patch panel", "CommScope/AMP 24-port Cat6 (1933796-2)", "24 port, Cat6, 1U", 1, 1565000, TOKO + "patch-panel-24-port-cat6-commscope"),
        ("Patch cord", "CommScope Cat6 1m (NPC06UVDB)", "Cat6 UTP 1 m", 12, 66000, TOKO + "patch-cord-cat6-commscope-1m"),
    ]),
    ("CCTV & kabel", [
        ("Kamera IP CCTV", "Hikvision DS-2CD2143G2-IU (AcuSense)", "4MP dome, 2,8 mm, H.265+, IR 30 m, WDR 120dB, PoE, RTSP/ONVIF, sampai 25-30 fps", 8, 1687000, TOKO + "ds-2cd2143g2-iu"),
        ("Junction box kamera", "Hikvision DS-1280ZJ-XS", "Back box seri dome 2xx3G2", 8, 910000, TOKO + "junction-box-hikvision"),
        ("Kabel LAN (box 305 m)", "Belden Cat6 UTP 7814A", "Cat6 UTP 23AWG solid; 2 box untuk 8 titik (perkiraan, final setelah survey)", 2, 3365000, TOKO + "belden-cat-6-roll"),
        ("Konektor RJ45", "CommScope/AMP RJ45 Cat6", "Isi 100 pcs", 1, 1210000, TOKO + "connector-rj45-cat6-commscope"),
        ("Boot RJ45", "Belden AP700022 boot Cat6", "1 pack", 1, 190000, TOKO + "boot-rj45-cat6"),
        ("Pipa conduit", "Clipsal pipa PVC 20mm", "2,9 m per batang; sekitar 400 m jalur kabel (perkiraan)", 140, 15534, TOKO + "pipa-conduit-clipsal-20mm"),
        ("Klem pipa", "Clamp/saddle conduit 20mm", "Per pcs, jarak 1 m", 400, 2000, TOKO + "pipa-conduit-clipsal-20mm"),
    ]),
    ("Kelistrikan", [
        ("UPS server", "APC Easy UPS Online SRV2KI-E", "2000VA / 1800W, online double-conversion", 1, 9065000, TOKO + "apc-srv2ki"),
        ("UPS rak jaringan", "APC Easy UPS BVX1200LI-MS", "1200VA / 650W, AVR", 1, 1975000, TOKO + "apc-bvx1200li-ms"),
    ]),
]
r = 5
first = r
RAB_ROW = {}
for cat, rows in ITEMS:
    section(RB, r, cat, 10)
    r += 1
    for comp, brand, spec, q, price, link in rows:
        RAB_ROW[comp] = r
        put(RB, f"A{r}", cat, color=GREY)
        put(RB, f"B{r}", comp, wrap=True)
        put(RB, f"C{r}", brand, wrap=True)
        put(RB, f"D{r}", spec, wrap=True, color=GREY)
        put(RB, f"E{r}", q, color=BLUE, fmt="0")
        put(RB, f"F{r}", price, color=BLUE, fmt=RP)
        put(RB, f"G{r}", f"=E{r}*F{r}", fmt=RP)
        put(RB, f"H{r}", f"=ROUNDUP(F{r}*(1+{DK['cont']})*(1+{DK['mk_hw']}),-3)", fmt=RP)
        put(RB, f"I{r}", f"=E{r}*H{r}", fmt=RP)
        put(RB, f"J{r}", link, wrap=True, color="0563C1")
        RB[f"J{r}"].hyperlink = link
        r += 1
last_hw = r - 1
put(RB, f"B{r}", "Subtotal perangkat", bold=True, fill=TOTAL)
put(RB, f"G{r}", f"=SUM(G{first}:G{last_hw})", bold=True, fmt=RP, fill=TOTAL)
put(RB, f"I{r}", f"=SUM(I{first}:I{last_hw})", bold=True, fmt=RP, fill=TOTAL)
HW_COST, HW_SELL = f"RAB!$G${r}", f"RAB!$I${r}"
r += 1
put(RB, f"B{r}", "Kontinjensi (fluktuasi harga perangkat)")
put(RB, f"G{r}", f"=G{r - 1}*{DK['cont']}", fmt=RP)
HW_CONT = f"RAB!$G${r}"
r += 1
put(RB, f"B{r}", "Total perangkat + kontinjensi", bold=True, fill=TOTAL)
put(RB, f"G{r}", f"=G{r - 2}+G{r - 1}", bold=True, fmt=RP, fill=TOTAL)
r += 2
section(RB, r, "Jasa pasang", 10)
r += 1
put(RB, f"A{r}", "Jasa pasang", color=GREY)
put(RB, f"B{r}", "Jasa pasang IP camera (jasa saja)", wrap=True)
put(RB, f"C{r}", "Per titik kamera")
put(RB, f"D{r}", "Tarik kabel dan pasang conduit, pasang kamera, setting sudut; material sudah dihitung di atas", wrap=True, color=GREY)
put(RB, f"E{r}", 8, color=BLUE, fmt="0")
put(RB, f"F{r}", 350000, color=BLUE, fmt=RP)
put(RB, f"G{r}", f"=E{r}*F{r}", fmt=RP)
put(RB, f"H{r}", f"=ROUNDUP(F{r}*(1+{DK['mk_inst']}),-3)", fmt=RP)
put(RB, f"I{r}", f"=E{r}*H{r}", fmt=RP)
link = "https://gsi-indo.com/2026/04/17/harga-pasang-cctv-per-titik/"
put(RB, f"J{r}", link, wrap=True, color="0563C1")
RB[f"J{r}"].hyperlink = link
INST_COST, INST_SELL = f"RAB!$G${r}", f"RAB!$I${r}"
r += 2
note(RB, r, "Harga Tokopedia dari RAB Factory_Vision_Presentation.pptx (dicek 12 Okt 2026, umumnya sudah termasuk PPN). PC server: Agres Komputer Official, dicek 31 Okt 2026. "
     "Panjang kabel dan conduit adalah perkiraan; angka final setelah survey dock.", 10, 30)

# ------------------------------------------------------------------ Jasa (INKINDO 2026)
J = sheet("Jasa INKINDO", [5, 58, 9, 9, 9, 9, 9, 17, 34])
title(J, "Jasa Pembuatan AI, Web App, dan Implementasi (tarif INKINDO 2026)",
      "Pedoman Standar Minimal INKINDO 2026, DKI Jakarta (indeks 1,000). Tarif sudah termasuk gaji, beban sosial, overhead, dan keuntungan.")
header(J, 4, ["", "Peran", "", "", "", "", "Tarif per bulan (Rp)", "Tarif per hari (Rp)", "Acuan INKINDO 2026"])
ROLES = [
    ("pm", "Team Leader / Project Manager", 37400000, "Tabel 3-26: Tenaga Ahli S1, pengalaman 8 tahun"),
    ("ai", "AI / Computer Vision Engineer", 32300000, "Tabel 3-26: Tenaga Ahli S1, pengalaman 5 tahun"),
    ("dev", "Pemrogram perangkat lunak (web app)", 17600000, "Tabel 4-26: Pemrogram Perangkat Lunak"),
    ("asst", "Asisten tenaga ahli (pelabelan data)", 17600000, "Tabel 4-26: Asisten Tenaga Ahli/Teknisi/Analis"),
    ("tech", "Teknisi jaringan TI", 16900000, "Tabel 4-26: Teknisi Jaringan Teknologi Informasi"),
]
RATE = {}
r = 5
for key, lab, monthly, ref in ROLES:
    put(J, f"B{r}", lab)
    put(J, f"G{r}", monthly, color=BLUE, fmt=RP)
    put(J, f"H{r}", f"=G{r}/22*1.1", fmt=RP, bold=True)
    put(J, f"I{r}", ref, wrap=True, color=GREY)
    RATE[key] = f"'Jasa INKINDO'!$H${r}"
    r += 1
put(J, f"B{r}", "Konversi harian sesuai pedoman: tarif per hari = tarif per bulan / 22 x 1,1 (Perlem LKPP 12/2021 bagian 2.2.2).", italic=True, color="595959")
r += 2
header(J, r, ["No", "Pekerjaan", "PM", "AI/CV", "Pemrogram", "Asisten", "Teknisi", "Nilai jasa (Rp)", "Hasil"])
r += 1
GROUPS = [
    ("Pembuatan AI", [
        ("Pengambilan data dan pelabelan sekitar 3.000 gambar karton dan palet dari CCTV dock", 0, 2, 0, 8, 0, "Dataset kemasan Minyakita"),
        ("Training dan tuning model (karton, palet, lapisan)", 0, 10, 0, 0, 0, "Model deteksi khusus kemasan"),
        ("Logika hitung 60 karton per palet dan rekonsiliasi per DO", 0, 8, 0, 0, 0, "Status palet lengkap atau kurang, selisih per DO"),
        ("Optimasi pipeline realtime 8 kamera 20-30 fps (decode GPU, TensorRT)", 0, 6, 0, 0, 0, "Sistem realtime stabil"),
    ]),
    ("Pembuatan Web App", [
        ("Dashboard dock dan manajemen, input DO, laporan per DO/truk/palet, alert, user", 0, 0, 20, 0, 0, "Web app on-premise"),
        ("Integrasi data DO dari WMS/ERP (file CSV atau API)", 0, 0, 5, 0, 0, "DO otomatis di sistem"),
    ]),
    ("Implementasi Lapangan", [
        ("Survey dock dan desain posisi kamera serta zona cek palet", 1, 1, 0, 0, 1, "Gambar posisi kamera"),
        ("Instalasi rak, jaringan, server, dan setting 8 kamera", 0, 0, 0, 0, 4, "Infrastruktur siap"),
        ("Kalibrasi 8 kamera dan zona cek palet", 0, 3, 0, 0, 2, "Kamera terkalibrasi"),
        ("Uji paralel 2 minggu dibanding hitung manual", 2, 5, 3, 0, 4, "Laporan akurasi, sign-off"),
        ("Training pengguna, SOP, serah terima", 2, 0, 1, 0, 0, "SOP checker dan supervisor"),
    ]),
    ("Manajemen Proyek", [
        ("Koordinasi, rapat mingguan, laporan progres selama 8-10 minggu", 10, 0, 0, 0, 0, "Laporan progres"),
    ]),
]
GROUP_TOTAL = {}
n = 1
for gname, acts in GROUPS:
    section(J, r, gname, 9)
    r += 1
    g0 = r
    for act, pm, ai, dev, asst, tech, out in acts:
        put(J, f"A{r}", n)
        put(J, f"B{r}", act, wrap=True)
        for col, v in zip("CDEFG", (pm, ai, dev, asst, tech)):
            put(J, f"{col}{r}", v, color=BLUE, fmt="0")
        put(J, f"H{r}", f"=C{r}*{RATE['pm']}+D{r}*{RATE['ai']}+E{r}*{RATE['dev']}+F{r}*{RATE['asst']}+G{r}*{RATE['tech']}", fmt=RP)
        put(J, f"I{r}", out, wrap=True, color=GREY)
        r += 1
        n += 1
    put(J, f"B{r}", f"Subtotal {gname}", bold=True, fill=TOTAL)
    put(J, f"H{r}", f"=SUM(H{g0}:H{r - 1})", bold=True, fmt=RP, fill=TOTAL)
    GROUP_TOTAL[gname] = f"'Jasa INKINDO'!$H${r}"
    r += 1
put(J, f"B{r}", "Total jasa", bold=True, fill=TOTAL)
put(J, f"H{r}", "=" + "+".join(v.split("!")[1] for v in GROUP_TOTAL.values()), bold=True, fmt=RP, fill=TOTAL)
JASA = f"'Jasa INKINDO'!$H${r}"
r += 2
section(J, r, "Layanan support per bulan (garansi dan langganan)", 9)
r += 1
s0 = r
for act, pm, ai, dev, asst, tech in [
    ("Kunjungan rutin: cek kamera, bersihkan lensa, cek server dan rekaman", 0, 0, 0, 0, 1),
    ("Pemantauan akurasi dan retraining model", 0, 1, 0, 0, 0),
    ("Perbaikan dan update web app", 0, 0, 1, 0, 0),
]:
    put(J, f"B{r}", act, wrap=True)
    for col, v in zip("CDEFG", (pm, ai, dev, asst, tech)):
        put(J, f"{col}{r}", v, color=BLUE, fmt="0")
    put(J, f"H{r}", f"=C{r}*{RATE['pm']}+D{r}*{RATE['ai']}+E{r}*{RATE['dev']}+F{r}*{RATE['asst']}+G{r}*{RATE['tech']}", fmt=RP)
    r += 1
put(J, f"B{r}", "Total layanan per bulan", bold=True, fill=TOTAL)
put(J, f"H{r}", f"=SUM(H{s0}:H{r - 1})", bold=True, fmt=RP, fill=TOTAL)
SUPPORT = f"'Jasa INKINDO'!$H${r}"

# ------------------------------------------------------------------ Skenario A
SA = sheet("Skenario A", [64, 18, 58])
title(SA, "Skenario A: Beli Putus", "Semua perangkat, jasa pasang, web app dan AI menjadi milik perusahaan. Sekali bayar.")
section(SA, 4, "1. Uang keluar ke vendor", 3)
line(SA, 5, "Perangkat", f"={HW_COST}", color=GREEN)
line(SA, 6, "Kontinjensi perangkat", f"={HW_CONT}", color=GREEN)
line(SA, 7, "Jasa pasang kamera (vendor)", f"={INST_COST}", color=GREEN)
line(SA, 8, "Total uang keluar", "=SUM(B5:B7)", bold=True, fill=TOTAL)
section(SA, 10, "2. Harga ke klien", 3)
line(SA, 11, "Perangkat (harga jual)", f"={HW_SELL}", color=GREEN)
line(SA, 12, "Jasa pasang kamera", f"={INST_SELL}", color=GREEN)
line(SA, 13, "Pembuatan AI", f"={GROUP_TOTAL['Pembuatan AI']}", color=GREEN)
line(SA, 14, "Pembuatan Web App", f"={GROUP_TOTAL['Pembuatan Web App']}", color=GREEN)
line(SA, 15, "Implementasi Lapangan", f"={GROUP_TOTAL['Implementasi Lapangan']}", color=GREEN)
line(SA, 16, "Manajemen Proyek", f"={GROUP_TOTAL['Manajemen Proyek']}", color=GREEN)
line(SA, 17, "Garansi layanan", f"={SUPPORT}*{DK['warranty']}")
line(SA, 18, "Total harga (sebelum PPN)", "=SUM(B11:B17)", bold=True, fill=TOTAL)
line(SA, 19, "PPN", f"=B18*{DK['ppn']}")
line(SA, 20, "Total tagihan", "=B18+B19", bold=True)
section(SA, 22, "3. Pendapatan", 3)
line(SA, 23, "Jasa tim (AI, web app, implementasi, manajemen, garansi)", "=SUM(B13:B17)")
line(SA, 24, "Margin perangkat dan jasa pasang", "=B11+B12-B8")
line(SA, 25, "Pendapatan bersih (sebelum pajak penghasilan)", "=B18-B8", bold=True, fill=TOTAL)
line(SA, 26, "Setara per bulan dalam 1 tahun", "=B25/12", bold=True)
section(SA, 28, "4. Termin dan opsi", 3)
line(SA, 29, "DP 50% saat PO", "=B20*50%")
line(SA, 30, "30% setelah instalasi selesai", "=B20*30%")
line(SA, 31, "20% setelah uji paralel dan serah terima", "=B20*20%")
line(SA, 32, "Maintenance opsional per tahun setelah garansi", f"=ROUNDUP({SUPPORT}*12,-5)")

# ------------------------------------------------------------------ Cadangan penggantian (Opsi B)
CP = sheet("Cadangan Penggantian", [30, 34, 15, 11, 50, 12, 9, 16])
title(CP, "Cadangan Penggantian Perangkat (Opsi B)",
      "Perangkat aktif yang garansi pabriknya habis sebelum kontrak minimum selesai dicadangkan 1 unit pengganti (harga beli + kontinjensi).")
header(CP, 4, ["Perangkat", "Merek / Tipe", "Harga beli satuan (Rp)", "Garansi pabrik (bulan)", "Sumber garansi",
               "Habis sebelum kontrak selesai?", "Qty cadangan", "Nilai cadangan (Rp)"])
TP = "https://www.tokopedia.com/"
RESERVE = [   # (device, brand, price formula or input, warranty months, source text, link)
    ("Kamera IP CCTV", "Hikvision DS-2CD2143G2-IU", f"=RAB!F{RAB_ROW['Kamera IP CCTV']}", 24,
     "Listing toko: garansi resmi Hikvision 2 tahun", TP + "zacharycctv/hikvision-ds-2cd2143g2-i-4mp-dome-ip-camera"),
    ("PC server: prosesor", "Intel Core Ultra 5 (harga 245K dipakai sebagai batas atas)", 3960000, 12,
     "Rincian garansi PC rakitan Agres: CPU 1 tahun", TP + "jayapc/processor-intel-core-ultra-5-245k-box-arrow-lake-socket-lga-1851"),
    ("PC server: VGA, motherboard, SSD", "Bagian dari AGRES CRYO PC", 0, 36,
     "Rincian garansi PC rakitan Agres: VGA, motherboard, SSD 3 tahun; PSU 5 tahun; RAM seumur hidup", AGRES),
    ("HDD rekaman video", "WD Purple Pro 8TB", f"=RAB!F{RAB_ROW['HDD rekaman video']}", 60,
     "WD: limited warranty 5 tahun", "https://www.ic.plus/products/purple-pro-8tb.html"),
    ("HDD backup eksternal", "Seagate Expansion Desktop 12TB", f"=RAB!F{RAB_ROW['HDD backup eksternal']}", 12,
     "Halaman Seagate berbeda per negara (1 sampai 3 tahun); dipakai yang terpendek", "https://www.seagate.com/support/external-hard-drives/desktop-hard-drives/expansion-desktop/"),
    ("TV status loading dock", "Samsung Business TV BE55FX-H", f"=RAB!F{RAB_ROW['TV status loading dock']}", 36,
     "Garansi 3 tahun (RAB pptx)", TOKO + "samsung-business-tv-55"),
    ("Router", "MikroTik RB5009UG+S+IN", f"=RAB!F{RAB_ROW['Router']}", 12,
     "Listing toko: garansi 12 bulan; sumber Indonesia belum ada", "https://www.getic.com/product/mikrotik-rb5009ug-s-in"),
    ("Switch PoE CCTV", "TP-Link Omada TL-SG2218P", f"=RAB!F{RAB_ROW['Switch PoE CCTV']}", 24,
     "Listing toko berbeda (2 sampai 5 tahun); dipakai yang terpendek", "https://ict.com.mm/products/tp-link-tl-sg2218p-jetstream-18-port-gigabit-smart-switch-with-16-port-poe"),
    ("UPS server", "APC Easy UPS Online SRV2KI-E", f"=RAB!F{RAB_ROW['UPS server']}", 24,
     "Listing toko: garansi 2 tahun, termasuk baterai", "https://www.comms-express.com/products/apc-srv2ki-e-easy-ups-on-line-2000va-1800w-tower-230v/"),
    ("UPS rak jaringan", "APC Easy UPS BVX1200LI-MS", f"=RAB!F{RAB_ROW['UPS rak jaringan']}", 24,
     "Manual: garansi produk 2 tahun", "https://manuals.plus/asin/B08G8WT2L9"),
]
r = 5
for dev, brand, price, wmon, src, link in RESERVE:
    put(CP, f"A{r}", dev, wrap=True)
    put(CP, f"B{r}", brand, wrap=True, color=GREY)
    put(CP, f"C{r}", price, fmt=RP, color=GREEN if isinstance(price, str) else BLUE)
    put(CP, f"D{r}", wmon, fmt="0", color=BLUE)
    put(CP, f"E{r}", src, wrap=True, color="0563C1")
    CP[f"E{r}"].hyperlink = link
    put(CP, f"F{r}", f'=IF(D{r}<{DK["term"]},"Ya","Tidak")')
    put(CP, f"G{r}", f'=IF(D{r}<{DK["term"]},{DK["spare"]},0)', fmt="0")
    put(CP, f"H{r}", f"=ROUNDUP(G{r}*C{r}*(1+{DK['cont']}),-3)", fmt=RP)
    CP.row_dimensions[r].height = 28
    r += 1
put(CP, f"A{r}", "Total cadangan selama kontrak", bold=True, fill=TOTAL)
put(CP, f"H{r}", f"=SUM(H5:H{r - 1})", bold=True, fmt=RP, fill=TOTAL)
RESERVE_TOTAL = f"'Cadangan Penggantian'!$H${r}"
note(CP, r + 2, "Tidak dicadangkan: perangkat pasif (rak, PDU, patch panel, kabel, conduit, bracket, junction box), dan casing serta cooler PC "
     "(model belum diketahui, konfirmasi ke Agres). Kerusakan karena kelalaian, benturan forklift, bencana, petir, atau listrik tidak stabil "
     "ditanggung klien sesuai kontrak, bukan dari cadangan ini.", 8, 42)

# ------------------------------------------------------------------ Skenario B
SB = sheet("Skenario B", [64, 18, 58])
title(SB, "Skenario B: Sewa + Langganan, Kontrak Minimum",
      "Perangkat milik kita. Klien bayar biaya setup sekali, lalu langganan per 12 bulan di muka selama kontrak minimum.")
section(SB, 4, "1. Uang keluar ke vendor (di awal)", 3)
line(SB, 5, "Perangkat", f"={HW_COST}", color=GREEN)
line(SB, 6, "Kontinjensi perangkat", f"={HW_CONT}", color=GREEN)
line(SB, 7, "Jasa pasang kamera (vendor)", f"={INST_COST}", color=GREEN)
line(SB, 8, "Total uang keluar", "=SUM(B5:B7)", bold=True, fill=TOTAL)
section(SB, 10, "2. Biaya setup (satu kali, kerja custom untuk klien)", 3)
line(SB, 11, "Pembuatan AI", f"={GROUP_TOTAL['Pembuatan AI']}", color=GREEN)
line(SB, 12, "Pembuatan Web App", f"={GROUP_TOTAL['Pembuatan Web App']}", color=GREEN)
line(SB, 13, "Implementasi Lapangan", f"={GROUP_TOTAL['Implementasi Lapangan']}", color=GREEN)
line(SB, 14, "Manajemen Proyek", f"={GROUP_TOTAL['Manajemen Proyek']}", color=GREEN)
line(SB, 15, "Total biaya setup", "=SUM(B11:B14)", bold=True, fill=TOTAL)
section(SB, 17, "3. Langganan per tahun (selama kontrak minimum)", 3)
line(SB, 18, "Sewa perangkat dan pemasangan", f"=ROUNDUP(B8/(1-{DK['m_rent']})/({DK['term']}/12),-5)",
     nt="Uang keluar perangkat + margin sewa, dibagi rata selama kontrak minimum.")
line(SB, 19, "Layanan support dan maintenance 12 bulan", f"=ROUNDUP({SUPPORT}*12,-5)",
     nt="Kunjungan rutin, retraining model, update web app (sheet Jasa INKINDO).")
line(SB, 20, "Jaminan penggantian perangkat", f"=ROUNDUP({RESERVE_TOTAL}/({DK['term']}/12),-5)",
     nt="Cadangan penggantian dibagi rata per tahun (sheet Cadangan Penggantian).")
line(SB, 21, "Langganan per tahun (sebelum PPN)", "=SUM(B18:B20)", bold=True, fill=TOTAL)
section(SB, 23, "4. Tagihan ke klien (sebelum PPN)", 3)
line(SB, 24, "Tahun pertama (setup + langganan)", "=B15+B21", bold=True)
line(SB, 25, "Per tahun berikutnya", "=B21")
line(SB, 26, "Total selama kontrak minimum", f"=B15+B21*{DK['term']}/12", bold=True, fill=TOTAL)
line(SB, 27, "PPN tahun pertama", f"=B24*{DK['ppn']}")
line(SB, 28, "Tagihan tahun pertama termasuk PPN", "=B24+B27", bold=True)
section(SB, 30, "5. Pendapatan selama kontrak minimum", 3)
line(SB, 31, "Total pendapatan (sebelum PPN)", "=B26")
line(SB, 32, "Uang keluar perangkat", "=-B8")
line(SB, 33, "Cadangan penggantian bila terpakai semua", f"=-{RESERVE_TOTAL}", color=GREEN)
line(SB, 34, "Pendapatan bersih (cadangan terpakai semua)", "=SUM(B31:B33)", bold=True, fill=TOTAL)
line(SB, 35, "Pendapatan bersih (cadangan tidak terpakai)", "=B31+B32", bold=True)
line(SB, 36, "Setara per bulan (cadangan terpakai semua)", f"=B34/{DK['term']}")
line(SB, 37, "Modal perangkat kembali dari sewa pada bulan ke-", "=B8/(B18/12)", fmt="0.0")
section(SB, 39, "6. Pengamanan", 3)
line(SB, 40, "Pembayaran saat PO: 50% setup + langganan tahun pertama", "=B15*50%+B21",
     nt="Lebih besar dari uang keluar perangkat, jadi kita tidak menalangi modal.")
line(SB, 41, "Kas saat PO dikurangi uang keluar perangkat", "=B40-B8")
line(SB, 42, "Biaya pemutusan bila berhenti setelah tahun ke-1", f"=B18*({DK['term']}/12-1)",
     nt="Sisa sewa perangkat sampai akhir kontrak minimum.")
line(SB, 43, "Biaya pemutusan bila berhenti setelah tahun ke-2", f"=B18*MAX({DK['term']}/12-2,0)")
line(SB, 44, "Pendapatan bersih bila berhenti setelah tahun ke-1 (bayar biaya pemutusan)", "=B24+B42-B8")

# ------------------------------------------------------------------ Sumber
SS = sheet("Sumber Harga", [7, 95, 70])
title(SS, "Sumber Harga", "Harga toko dapat berubah; minta penawaran tertulis sebelum membeli.")
header(SS, 4, ["Kode", "Sumber", "Tautan"])
for i, (c, d, u) in enumerate([
    ("S1", "RAB Factory_Vision_Presentation.pptx (slide RAB 1/3 sampai 3/3): harga Tokopedia dicek 12 Okt 2026, umumnya sudah termasuk PPN. Tautan per item ada di sheet RAB.", "Factory_Vision_Presentation.pptx"),
    ("S2", "Agres Komputer Official (Tokopedia): AGRES CRYO PC ULTRA 5 245KF RTX 5070 TI 16G / 32GB 1TB, Rp 35.000.000 (dicek 31 Okt 2026 lewat hasil pencarian). Konfirmasi varian, PSU, dan casing ke penjual.", AGRES),
    ("S3", "Pembanding: e-katalog INAPROC/LKPP, AGRES CRYO PC ULTRA 5 245KF RTX 5070 12G 32GB/1TB + Win 11 Pro: Rp 34.234.234 + PPN Rp 3.765.766. Situs Agres (agres.id, agreskomputer.com) saat ini tidak menampilkan stok PC Ready/workstation.",
     "https://katalog.inaproc.id/pt-bangun-jaya-pedia/agres-cryo-pc-ultra-5-245kf-rtx-5070-12g-32gb-1tb-win-11-pro-rakitan-pc-gaming"),
    ("S4", "INKINDO, Pedoman Standar Minimal Tahun 2026 Remunerasi (Billing Rate): Tabel 3-26 (Tenaga Ahli tanpa SKK) dan Tabel 4-26 (Teknisi/Analis); SBOH = SBOB / 22 x 1,1.", "https://www.inkindo.org/documents/ikdweb-billing-rate-2026.pdf"),
    ("S5", "GSI Indonesia, Harga Pasang CCTV Per Titik 2026: IP camera jasa saja Rp 200.000 sampai Rp 350.000 per titik. Dipakai batas atas.", "https://gsi-indo.com/2026/04/17/harga-pasang-cctv-per-titik/"),
    ("S6", "PMK No. 131 Tahun 2024: PPN 12% x DPP 11/12, efektif 11%.", "Peraturan Menteri Keuangan No. 131 Tahun 2024"),
    ("S7", "Samsung BE55FX-H: spesifikasi toko mencantumkan Tizen dan web browser bawaan, jadi TV dock membuka dashboard tanpa mini PC. "
           "Stasiun operator (mini PC, monitor, keyboard) dihapus karena klien memantau dari laptop sendiri lewat VPN perusahaan. "
           "Cek browser di SKU LH55BEFHVGKXXD saat pembelian.", "https://www.dateks.lv/ru/cenas/televizori/1417992-samsung-be55fx-h-lh55befhlguxen-55-"),
    ("S8", "Garansi pabrik per perangkat untuk cadangan penggantian Opsi B: tautan sumber ada di tiap baris sheet Cadangan Penggantian. "
           "Bila sumber berbeda, dipakai masa garansi terpendek. Konfirmasi masa garansi resmi Indonesia saat pembelian.", "Sheet Cadangan Penggantian"),
], 5):
    put(SS, f"A{i}", c, bold=True)
    put(SS, f"B{i}", d, wrap=True)
    put(SS, f"C{i}", u, wrap=True, color="0563C1" if u.startswith("http") else GREY)
    if u.startswith("http"):
        SS[f"C{i}"].hyperlink = u

# ------------------------------------------------------------------ Ringkasan
R = sheet("Ringkasan", [52, 20, 20, 20, 20])
title(R, "Ringkasan: Hitung Karton per Palet di Loading Dock, 8 Kamera 20-30 fps, On-Premise",
      "Format RAB mengikuti pptx; PC server dari Agres; jasa dengan tarif INKINDO 2026. Hitungan per tahun (12 bulan).")
header(R, 4, ["", "A. Beli putus", "B. Tahun pertama", "B. Per tahun berikutnya", "B. Total kontrak minimum"])
SUM = [
    ("Uang keluar ke vendor", "='Skenario A'!B8", "='Skenario B'!B8", "=0", "='Skenario B'!B8"),
    ("Harga ke klien (sebelum PPN)", "='Skenario A'!B18", "='Skenario B'!B24", "='Skenario B'!B25", "='Skenario B'!B26"),
    ("Tagihan termasuk PPN", "='Skenario A'!B20", "='Skenario B'!B28", f"='Skenario B'!B25*(1+{DK['ppn']})", f"='Skenario B'!B26*(1+{DK['ppn']})"),
    ("Pendapatan bersih (B: cadangan terpakai semua)", "='Skenario A'!B25", None, None, "='Skenario B'!B34"),
    ("Pendapatan bersih (B: cadangan tidak terpakai)", None, None, None, "='Skenario B'!B35"),
    ("Modal perangkat kembali (bulan ke-)", None, None, None, "='Skenario B'!B37"),
]
r = 5
for lab, *fs in SUM:
    put(R, f"A{r}", lab, bold=True)
    for col, f in zip("BCDE", fs):
        if f:
            put(R, f"{col}{r}", f, color=GREEN, fmt="0.0" if "bulan ke" in lab else RP, right=True)
    r += 1
r += 1
put(R, f"A{r}", "Rincian jasa (sama di kedua opsi)", bold=True)
r += 1
for g, ref in GROUP_TOTAL.items():
    put(R, f"A{r}", g)
    put(R, f"B{r}", f"={ref}", color=GREEN, fmt=RP, right=True)
    r += 1
r += 1
for t in [
    "PC server: GPU RTX 5070 Ti 16 GB mendekode 8 stream 4MP di GPU dan menjalankan model TensorRT; target 20-30 fps per kamera. Kapasitas final dibuktikan dengan benchmark saat uji paralel.",
    "Tarif jasa INKINDO adalah standar minimal nasional untuk badan usaha jasa konsultansi dan sudah termasuk overhead dan keuntungan.",
    "Opsi B: pembayaran saat PO (50% setup + langganan tahun pertama) sudah menutup uang keluar perangkat; berhenti sebelum kontrak minimum selesai dikenai sisa sewa perangkat.",
]:
    put(R, f"A{r}", "• " + t, wrap=True, color=GREY)
    R.merge_cells(f"A{r}:E{r}")
    R.row_dimensions[r].height = 30
    r += 1

order = ["Ringkasan", "RAB", "Jasa INKINDO", "Skenario A", "Skenario B", "Cadangan Penggantian", "Keputusan Bisnis", "Sumber Harga"]
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
