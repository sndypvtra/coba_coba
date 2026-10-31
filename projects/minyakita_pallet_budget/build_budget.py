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
    ("sw_target", "Nilai jual jasa aplikasi AI computer vision dan web app (Opsi A dan B)", 125000000, RP,
     "Di atas tarif minimum INKINDO: sistem video analytics realtime 8 kamera dengan event trigger Telegram. Seluruhnya porsi developer."),
    ("split_dev", "Bagian developer dari margin perangkat/sewa", 0.50, PCT, "Tanpa kas CV: margin dibagi langsung ke 2 orang, sisanya untuk infrastruktur."),
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
header(J, 4, ["", "Peran", "Dikerjakan oleh", "", "", "", "Tarif per bulan (Rp)", "Tarif per hari (Rp)", "Acuan INKINDO 2026"])
DEV, INFRA = "Developer", "Infrastruktur"
ROLES = [
    ("pm", "Team Leader / Project Manager", INFRA, 37400000, "Tabel 3-26: Tenaga Ahli S1, pengalaman 8 tahun"),
    ("ai", "AI / Computer Vision Engineer", DEV, 32300000, "Tabel 3-26: Tenaga Ahli S1, pengalaman 5 tahun"),
    ("dev", "Pemrogram perangkat lunak (web app)", DEV, 17600000, "Tabel 4-26: Pemrogram Perangkat Lunak"),
    ("asst", "Asisten tenaga ahli (pelabelan data)", DEV, 17600000, "Tabel 4-26: Asisten Tenaga Ahli/Teknisi/Analis"),
    ("tech", "Teknisi jaringan TI", INFRA, 16900000, "Tabel 4-26: Teknisi Jaringan Teknologi Informasi"),
]
RATE, OWNER = {}, {}
r = 5
for key, lab, who, monthly, ref in ROLES:
    OWNER[key] = who
    put(J, f"B{r}", lab)
    put(J, f"C{r}", who, bold=True)
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
    ("Pembuatan AI Computer Vision", [
        ("Pengambilan data dan pelabelan sekitar 3.000 gambar karton dan palet dari CCTV dock (auto-labeling model pra-latih dan SAM, lalu dikoreksi)", 0, 2, 0, 8, 0, "Dataset kemasan Minyakita"),
        ("Training dan tuning model (karton, palet, lapisan)", 0, 10, 0, 0, 0, "Model deteksi khusus kemasan"),
        ("Logika hitung 60 karton per palet dan rekonsiliasi per DO", 0, 8, 0, 0, 0, "Status palet lengkap atau kurang, selisih per DO"),
        ("Optimasi pipeline realtime 8 kamera 20-30 fps (decode GPU, TensorRT)", 0, 6, 0, 0, 0, "Sistem realtime stabil"),
    ]),
    ("Pembuatan Web App", [
        ("Dashboard dock dan manajemen, input DO, laporan per DO/truk/palet, alert, user", 0, 0, 20, 0, 0, "Web app on-premise"),
        ("Live view 8 kamera di web app dengan overlay hasil deteksi dan hitungan", 0, 0, 4, 0, 0, "Pantau dock secara realtime"),
        ("Event trigger ke Telegram: aturan event (palet kurang, selisih DO, kamera mati), foto bukti, riwayat notifikasi", 0, 0, 5, 0, 0, "Notifikasi otomatis ke grup Telegram"),
        ("Integrasi data DO dari WMS/ERP (file CSV atau API)", 0, 0, 5, 0, 0, "DO otomatis di sistem"),
    ]),
    ("Setup dan Implementasi AI dan Web App", [
        ("Desain zona cek palet dan sudut pandang kamera untuk model (saat survey)", 0, 1, 0, 0, 0, "Zona cek per kamera"),
        ("Kalibrasi model dan zona cek di 8 kamera (ambang deteksi, hitung karton)", 0, 3, 0, 0, 0, "Model terkalibrasi per kamera"),
        ("Uji paralel 2 minggu: analisis akurasi, perbaikan model dan web app", 0, 5, 3, 0, 0, "Laporan akurasi"),
        ("Training penggunaan web app dan dashboard", 0, 0, 1, 0, 0, "Pengguna mahir memakai web app"),
    ]),
    ("Implementasi Infrastruktur", [
        ("Survey dock, desain posisi kamera, jalur kabel, dan ruang server", 1, 0, 0, 0, 1, "Gambar posisi kamera dan jalur kabel"),
        ("Instalasi rak, jaringan, server, dan setting 8 kamera", 0, 0, 0, 0, 4, "Infrastruktur siap"),
        ("Kalibrasi fisik 8 kamera (posisi, fokus, sudut)", 0, 0, 0, 0, 2, "Kamera terpasang sesuai desain"),
        ("Uji paralel 2 minggu: pendampingan lapangan dan sign-off", 2, 0, 0, 0, 4, "Berita acara uji paralel"),
        ("Training SOP checker dan supervisor, serah terima", 2, 0, 0, 0, 0, "SOP dan berita acara serah terima"),
    ]),
    ("Manajemen Proyek", [
        ("Koordinasi, rapat mingguan, laporan progres selama sekitar 16 minggu", 10, 0, 0, 0, 0, "Laporan progres"),
    ]),
]
GROUP_TOTAL = {}
n = 1
act0 = None
for gname, acts in GROUPS:
    section(J, r, gname, 9)
    r += 1
    g0 = r
    for act, pm, ai, dev, asst, tech, out in acts:
        act0 = act0 or r
        act1 = r
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
SOFTWARE = ("Pembuatan AI Computer Vision", "Pembuatan Web App", "Setup dan Implementasi AI dan Web App")
INFRA_GROUPS = ("Implementasi Infrastruktur", "Manajemen Proyek")
r += 1
section(J, r, "Nilai jual jasa aplikasi AI computer vision dan web app", 9)
r += 1
put(J, f"B{r}", "Nilai minimum INKINDO (hari kerja x tarif)")
put(J, f"H{r}", "=" + "+".join(GROUP_TOTAL[g].split("!")[1] for g in SOFTWARE), fmt=RP)
floor = r
r += 1
put(J, f"B{r}", "Nilai jual yang ditetapkan (Keputusan Bisnis)")
put(J, f"H{r}", f"={DK['sw_target']}", fmt=RP, color=GREEN)
target = r
r += 1
put(J, f"B{r}", "Faktor di atas tarif minimum")
put(J, f"H{r}", f"=H{target}/H{floor}", fmt="0.00")
factor = r
r += 1
sell = []
for i, g in enumerate(SOFTWARE):
    put(J, f"B{r}", f"Nilai jual {g}")
    if i < len(SOFTWARE) - 1:
        put(J, f"H{r}", f"=ROUND({GROUP_TOTAL[g].split('!')[1]}*H{factor},-3)", fmt=RP)
    else:
        put(J, f"H{r}", f"=H{target}-" + "-".join(f"H{x}" for x in sell), fmt=RP)
    sell.append(r)
    GROUP_TOTAL[g] = f"'Jasa INKINDO'!$H${r}"
    r += 1
put(J, f"B{r}", "Tarif INKINDO adalah standar minimal; nilai jual di atasnya mencerminkan keahlian video analytics realtime dan "
    "integrasi event trigger. Selisihnya masuk ke porsi developer.", italic=True, color="595959")
r += 2
put(J, f"B{r}", "Total jasa (nilai jual)", bold=True, fill=TOTAL)
put(J, f"H{r}", "=" + "+".join(v.split("!")[1] for v in GROUP_TOTAL.values()), bold=True, fmt=RP, fill=TOTAL)
JASA = f"'Jasa INKINDO'!$H${r}"
r += 1
put(J, f"B{r}", "Total hari kerja per peran (pembuatan + implementasi)", bold=True)
for col in "CDEFG":
    put(J, f"{col}{r}", f"=SUM({col}{act0}:{col}{act1})", fmt="0", bold=True)
DAYS = {k: f"'Jasa INKINDO'!${c}${r}" for k, c in zip(("pm", "ai", "dev", "asst", "tech"), "CDEFG")}
r += 1
put(J, f"B{r}", "Pelabelan memakai auto-labeling lalu dikoreksi, jadi waktu kerja nyata lebih pendek; nilai jasa tetap karena yang dijual "
    "hasilnya (dataset siap latih), bukan jam kerja.", italic=True, color="595959")
r += 2
section(J, r, "Layanan support per bulan (garansi dan langganan)", 9)
r += 1
sup0 = r
SUP_PART = {}
for part, rows in [
    ("software", [("Pemantauan akurasi dan retraining model", 0, 1, 0, 0, 0),
                  ("Perbaikan dan update web app", 0, 0, 1, 0, 0)]),
    ("infra", [("Kunjungan rutin: cek kamera, bersihkan lensa, cek server, jaringan, dan rekaman", 0, 0, 0, 0, 1)]),
]:
    p0 = r
    for act, pm, ai, dev, asst, tech in rows:
        put(J, f"B{r}", act, wrap=True)
        for col, v in zip("CDEFG", (pm, ai, dev, asst, tech)):
            put(J, f"{col}{r}", v, color=BLUE, fmt="0")
        put(J, f"H{r}", f"=C{r}*{RATE['pm']}+D{r}*{RATE['ai']}+E{r}*{RATE['dev']}+F{r}*{RATE['asst']}+G{r}*{RATE['tech']}", fmt=RP)
        r += 1
    put(J, f"B{r}", "Subtotal support software AI dan web app" if part == "software" else "Subtotal support infrastruktur", bold=True, fill=TOTAL)
    put(J, f"H{r}", f"=SUM(H{p0}:H{r - 1})", bold=True, fmt=RP, fill=TOTAL)
    SUP_PART[part] = f"'Jasa INKINDO'!$H${r}"
    r += 1
put(J, f"B{r}", "Total layanan per bulan", bold=True, fill=TOTAL)
put(J, f"H{r}", f"={SUP_PART['software'].split('!')[1]}+{SUP_PART['infra'].split('!')[1]}", bold=True, fmt=RP, fill=TOTAL)
SUPPORT, SUPPORT_SW, SUPPORT_INF = f"'Jasa INKINDO'!$H${r}", SUP_PART["software"], SUP_PART["infra"]
SUP_DAYS = {k: f"SUM('Jasa INKINDO'!${c}${sup0}:${c}${r - 1})" for k, c in zip(("pm", "ai", "dev", "asst", "tech"), "CDEFG")}

# ------------------------------------------------------------------ Skenario A
SA = sheet("Skenario A", [64, 18, 58])
title(SA, "Skenario A: Beli Putus", "Semua perangkat, jasa pasang, web app dan AI menjadi milik perusahaan. Sekali bayar.")
A_REF = {}


def ref(refs, key, ws, row):
    refs[key] = f"'{ws.title}'!$B${row}"


section(SA, 4, "1. Uang keluar ke vendor", 3)
line(SA, 5, "Perangkat", f"={HW_COST}", color=GREEN)
line(SA, 6, "Kontinjensi perangkat", f"={HW_CONT}", color=GREEN)
line(SA, 7, "Jasa pasang kamera (vendor)", f"={INST_COST}", color=GREEN)
line(SA, 8, "Total uang keluar", "=SUM(B5:B7)", bold=True, fill=TOTAL)
ref(A_REF, "out", SA, 8)
section(SA, 10, "2. Harga ke klien", 3)
line(SA, 11, "Perangkat (harga jual)", f"={HW_SELL}", color=GREEN)
line(SA, 12, "Jasa pasang kamera", f"={INST_SELL}", color=GREEN)
r = 13
for g, cell in GROUP_TOTAL.items():
    line(SA, r, g, f"={cell}", color=GREEN)
    r += 1
line(SA, r, "Garansi software AI dan web app", f"={SUPPORT_SW}*{DK['warranty']}", nt="Retraining model dan update web app selama masa garansi.")
line(SA, r + 1, "Garansi infrastruktur", f"={SUPPORT_INF}*{DK['warranty']}", nt="Kunjungan rutin perangkat selama masa garansi.")
line(SA, r + 2, "Total harga (sebelum PPN)", f"=SUM(B11:B{r + 1})", bold=True, fill=TOTAL)
line(SA, r + 3, "PPN", f"=B{r + 2}*{DK['ppn']}")
line(SA, r + 4, "Total tagihan", f"=B{r + 2}+B{r + 3}", bold=True)
ref(A_REF, "total", SA, r + 2)
ref(A_REF, "bill", SA, r + 4)
jasa_end, total_row, bill_row = r + 1, r + 2, r + 4
r += 6
section(SA, r, "3. Pendapatan", 3)
line(SA, r + 1, "Jasa tim (AI, web app, implementasi, manajemen, garansi)", f"=SUM(B13:B{jasa_end})")
line(SA, r + 2, "Margin perangkat dan jasa pasang", "=B11+B12-B8")
line(SA, r + 3, "Pendapatan bersih (sebelum pajak penghasilan)", f"=B{total_row}-B8", bold=True, fill=TOTAL)
line(SA, r + 4, "Setara per bulan dalam 1 tahun", f"=B{r + 3}/12", bold=True)
ref(A_REF, "net", SA, r + 3)
r += 6
section(SA, r, "4. Termin dan opsi", 3)
line(SA, r + 1, "DP 50% saat PO", f"=B{bill_row}*50%")
line(SA, r + 2, "30% setelah instalasi selesai", f"=B{bill_row}*30%")
line(SA, r + 3, "20% setelah uji paralel dan serah terima", f"=B{bill_row}*20%")
line(SA, r + 4, "Maintenance opsional per tahun setelah garansi", f"={SUPPORT}*12", nt="Software AI dan web app ditambah infrastruktur, 12 bulan.")

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
      "Perangkat milik kita. Klien bayar jasa aplikasi dan jasa infrastruktur sekali, lalu langganan per 12 bulan di muka selama kontrak minimum.")
B_REF = {}
section(SB, 4, "1. Uang keluar ke vendor (di awal)", 3)
line(SB, 5, "Perangkat", f"={HW_COST}", color=GREEN)
line(SB, 6, "Kontinjensi perangkat", f"={HW_CONT}", color=GREEN)
line(SB, 7, "Jasa pasang kamera (vendor)", f"={INST_COST}", color=GREEN)
line(SB, 8, "Total uang keluar", "=SUM(B5:B7)", bold=True, fill=TOTAL)
ref(B_REF, "out", SB, 8)
section(SB, 10, "2. Jasa sekali bayar: aplikasi AI dan web app, infrastruktur, manajemen proyek", 3)
r = 11
for g, cell in GROUP_TOTAL.items():
    line(SB, r, g, f"={cell}", color=GREEN)
    r += 1
line(SB, r, "Total jasa sekali bayar", f"=SUM(B11:B{r - 1})", bold=True, fill=TOTAL)
setup = r
r += 2
section(SB, r, "3. Langganan per tahun (selama kontrak minimum)", 3)
sub0 = r + 1
line(SB, r + 1, "Sewa perangkat dan pemasangan", f"=ROUNDUP(B8/(1-{DK['m_rent']})/({DK['term']}/12),-5)",
     nt="Uang keluar perangkat + margin sewa, dibagi rata selama kontrak minimum.")
line(SB, r + 2, "Support software AI dan web app 12 bulan", f"={SUPPORT_SW}*12", nt="Retraining model, update web app (sheet Jasa INKINDO).")
line(SB, r + 3, "Support infrastruktur 12 bulan", f"={SUPPORT_INF}*12", nt="Kunjungan rutin perangkat (sheet Jasa INKINDO).")
line(SB, r + 4, "Jaminan penggantian perangkat", f"=ROUNDUP({RESERVE_TOTAL}/({DK['term']}/12),-5)",
     nt="Cadangan penggantian dibagi rata per tahun (sheet Cadangan Penggantian).")
line(SB, r + 5, "Langganan per tahun (sebelum PPN)", f"=SUM(B{r + 1}:B{r + 4})", bold=True, fill=TOTAL)
rent, sub = r + 1, r + 5
r += 7
section(SB, r, "4. Tagihan ke klien (sebelum PPN)", 3)
line(SB, r + 1, "Tahun pertama (jasa sekali bayar + langganan)", f"=B{setup}+B{sub}", bold=True)
line(SB, r + 2, "Per tahun berikutnya", f"=B{sub}")
line(SB, r + 3, "Total selama kontrak minimum", f"=B{setup}+B{sub}*{DK['term']}/12", bold=True, fill=TOTAL)
line(SB, r + 4, "PPN tahun pertama", f"=B{r + 1}*{DK['ppn']}")
line(SB, r + 5, "Tagihan tahun pertama termasuk PPN", f"=B{r + 1}+B{r + 4}", bold=True)
for k, off in (("year1", 1), ("next", 2), ("total", 3), ("bill1", 5)):
    ref(B_REF, k, SB, r + off)
year1_row, total_row = r + 1, r + 3
r += 7
section(SB, r, "5. Pendapatan selama kontrak minimum", 3)
line(SB, r + 1, "Total pendapatan (sebelum PPN)", f"=B{total_row}")
line(SB, r + 2, "Uang keluar perangkat", "=-B8")
line(SB, r + 3, "Cadangan penggantian bila terpakai semua", f"=-{RESERVE_TOTAL}", color=GREEN)
line(SB, r + 4, "Pendapatan bersih (cadangan terpakai semua)", f"=SUM(B{r + 1}:B{r + 3})", bold=True, fill=TOTAL)
line(SB, r + 5, "Pendapatan bersih (cadangan tidak terpakai)", f"=B{r + 1}+B{r + 2}", bold=True)
line(SB, r + 6, "Setara per bulan (cadangan terpakai semua)", f"=B{r + 4}/{DK['term']}")
line(SB, r + 7, "Modal perangkat kembali dari sewa pada bulan ke-", f"=B8/(B{rent}/12)", fmt="0.0")
for k, off in (("net", 4), ("net_unused", 5), ("payback", 7)):
    ref(B_REF, k, SB, r + off)
r += 9
section(SB, r, "6. Pengamanan", 3)
line(SB, r + 1, "Pembayaran saat PO: 50% jasa sekali bayar + langganan tahun pertama", f"=B{setup}*50%+B{sub}",
     nt="Lebih besar dari uang keluar perangkat, jadi kita tidak menalangi modal.")
line(SB, r + 2, "Kas saat PO dikurangi uang keluar perangkat", f"=B{r + 1}-B8")
line(SB, r + 3, "Biaya pemutusan bila berhenti setelah tahun ke-1", f"=B{rent}*({DK['term']}/12-1)",
     nt="Sisa sewa perangkat sampai akhir kontrak minimum.")
line(SB, r + 4, "Biaya pemutusan bila berhenti setelah tahun ke-2", f"=B{rent}*MAX({DK['term']}/12-2,0)")
line(SB, r + 5, "Pendapatan bersih bila berhenti setelah tahun ke-1 (bayar biaya pemutusan)", f"=B{year1_row}+B{r + 3}-B8")

# ------------------------------------------------------------------ Porsi tim (internal)
def value(who, days):
    return "+".join(f"{days[k]}*{RATE[k]}" for k in RATE if OWNER[k] == who)


PT = sheet("Porsi Tim", [64, 18, 18, 52])
title(PT, "Porsi Tim: Developer dan Infrastruktur (tanpa kas CV)",
      "Seluruh pendapatan bersih dibagi langsung ke 2 orang: nilai jasa masing-masing (hari kerja x tarif INKINDO) ditambah bagian margin.")
header(PT, 4, ["", "Opsi A", "Opsi B (kontrak minimum)", "Keterangan"])


def both(row, label, fa, fb, bold=False, fill=None, color=BLACK, fmt=RP, nt=None):
    line(PT, row, label, fa, bold=bold, fill=fill, color=color, fmt=fmt)
    put(PT, f"C{row}", fb, bold=bold, fill=fill, color=color, fmt=fmt)
    if nt:
        put(PT, f"D{row}", nt, wrap=True, color=GREY)
        PT.row_dimensions[row].height = 28


dev_work, dev_sup = "=" + "+".join(GROUP_TOTAL[g] for g in SOFTWARE), value(DEV, SUP_DAYS)
inf_work, inf_sup = "=" + "+".join(GROUP_TOTAL[g] for g in INFRA_GROUPS), value(INFRA, SUP_DAYS)
section(PT, 5, "1. Margin yang dibagi berdua", 4)
both(6, "Pendapatan bersih", f"={A_REF['net']}", f"={B_REF['net']}", color=GREEN,
     nt="Opsi B dengan asumsi cadangan penggantian terpakai semua.")
both(7, "Dikurangi nilai jasa kedua orang", "=-(B12+B13+B18+B19)", "=-(C12+C13+C18+C19)")
both(8, "Margin perangkat / sewa untuk dibagi", "=B6+B7", "=C6+C7", bold=True, fill=TOTAL,
     nt="Opsi A: margin perangkat dan jasa pasang. Opsi B: margin sewa perangkat.")
section(PT, 10, "2. Developer: AI/CV, web app, pelabelan", 4)
put(PT, "A11", "Bagian margin", color=GREY)
put(PT, "B11", f"={DK['split_dev']}", fmt=PCT, color=GREEN)
both(12, "Pembuatan AI Computer Vision, Pembuatan Web App, Setup dan Implementasi AI dan Web App", dev_work, "=B12",
     nt="Sama di kedua opsi, dibayar di depan.")
both(13, "Support AI dan web app (retraining, update)", f"=({dev_sup})*{DK['warranty']}", f"=({dev_sup})*{DK['term']}",
     nt="Opsi A: garansi 3 bulan. Opsi B: selama kontrak minimum (1 hari AI + 1 hari web app per bulan).")
both(14, "Bagian margin", "=B8*$B$11", "=C8*$B$11")
both(15, "Total developer", "=SUM(B12:B14)", "=SUM(C12:C14)", bold=True, fill=TOTAL)
section(PT, 17, "3. Infrastruktur: team leader/PM dan teknisi", 4)
both(18, "Implementasi Infrastruktur, Manajemen Proyek", inf_work, "=B18",
     nt="Jasa pasang kamera dari vendor luar; bila dipasang sendiri, biaya vendor ikut masuk ke porsi ini.")
both(19, "Kunjungan rutin", f"=({inf_sup})*{DK['warranty']}", f"=({inf_sup})*{DK['term']}")
both(20, "Bagian margin", "=B8*(1-$B$11)", "=C8*(1-$B$11)")
both(21, "Total infrastruktur", "=SUM(B18:B20)", "=SUM(C18:C20)", bold=True, fill=TOTAL)
section(PT, 23, "4. Kontrol", 4)
both(24, "Total dibayarkan ke 2 orang", "=B15+B21", "=C15+C21", bold=True)
both(25, "Selisih dengan pendapatan bersih (harus 0)", "=ROUND(B24-B6,0)", "=ROUND(C24-C6,0)")
section(PT, 27, "5. Cadangan penggantian (Opsi B)", 4)
both(28, "Dipegang untuk membeli perangkat pengganti", "=0", f"={RESERVE_TOTAL}",
     nt="Sisa yang tidak terpakai di akhir kontrak dibagi dengan persentase yang sama.")
both(29, "Tambahan developer bila tidak terpakai", "=0", "=C28*$B$11")
both(30, "Tambahan infrastruktur bila tidak terpakai", "=0", "=C28*(1-$B$11)")
section(PT, 32, "6. Beban kerja dan jadwal", 4)
line(PT, 33, "Hari kerja developer (ditagih)", "=" + "+".join(DAYS[k] for k in RATE if OWNER[k] == DEV), fmt="0")
line(PT, 34, "Hari kerja infrastruktur (ditagih)", "=" + "+".join(DAYS[k] for k in RATE if OWNER[k] == INFRA), fmt="0")
put(PT, "D33", "Sekitar 16 minggu (80 hari kerja); pelabelan dipercepat dengan auto-labeling.", wrap=True, color=GREY)
put(PT, "D34", "Berjalan paralel dengan pekerjaan developer.", wrap=True, color=GREY)

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
    ("Uang keluar ke vendor", f"={A_REF['out']}", f"={B_REF['out']}", "=0", f"={B_REF['out']}"),
    ("Harga ke klien (sebelum PPN)", f"={A_REF['total']}", f"={B_REF['year1']}", f"={B_REF['next']}", f"={B_REF['total']}"),
    ("Tagihan termasuk PPN", f"={A_REF['bill']}", f"={B_REF['bill1']}", f"={B_REF['next']}*(1+{DK['ppn']})", f"={B_REF['total']}*(1+{DK['ppn']})"),
    ("Pendapatan bersih (B: cadangan terpakai semua)", f"={A_REF['net']}", None, None, f"={B_REF['net']}"),
    ("Pendapatan bersih (B: cadangan tidak terpakai)", None, None, None, f"={B_REF['net_unused']}"),
    ("Modal perangkat kembali (bulan ke-)", None, None, None, f"={B_REF['payback']}"),
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
    "Tim 2 orang tanpa kas CV: developer (AI, web app, pelabelan) dan infrastruktur (team leader/PM dan teknisi). Seluruh pendapatan bersih dibagi langsung ke 2 orang (sheet Porsi Tim). Jadwal sekitar 16 minggu.",
]:
    put(R, f"A{r}", "• " + t, wrap=True, color=GREY)
    R.merge_cells(f"A{r}:E{r}")
    R.row_dimensions[r].height = 30
    r += 1

order = ["Ringkasan", "RAB", "Jasa INKINDO", "Skenario A", "Skenario B", "Cadangan Penggantian", "Porsi Tim", "Keputusan Bisnis", "Sumber Harga"]
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
