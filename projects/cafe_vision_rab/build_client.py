"""Client quotation for the cafe project, built from the internal RAB (run build_rab.py + recalc first).

Shows only selling prices, totals, terms and scope. Nothing internal: no purchase prices, markup, contingency,
commission, day rates, team split or purchase sources. Line prices add up exactly to the internal totals.

    python build_client.py   # -> Penawaran_Cafe_Vision_4_Kamera.xlsx (then recalc with LibreOffice)
"""
import math
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
SRC = HERE / "RAB_Cafe_Vision_4_Kamera.xlsx"
OUT = HERE / "Penawaran_Cafe_Vision_4_Kamera.xlsx"
F = "Arial"
HEAD = PatternFill("solid", fgColor="1F3864")
SUB = PatternFill("solid", fgColor="D9E1F2")
TOTAL = PatternFill("solid", fgColor="F2F2F2")
RP = '#,##0;(#,##0);"-"'
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

# ---------------------------------------------------------------- internal values (never written to the client file)
src = load_workbook(SRC, data_only=True)
dec = {src["Keputusan Bisnis"][f"A{r}"].value: src["Keputusan Bisnis"][f"B{r}"].value for r in range(5, 12)}
cont = dec["Kontinjensi harga perangkat"]
mk_hw = dec["Markup perangkat"]
mk_inst = dec["Markup instalasi"]
comm = dec["Komisi tim pemasaran (3 orang), dari nilai kontrak sebelum PPN"]
ppn = dec["PPN efektif (S17), isi 0 bila CV belum PKP"]
warranty = dec["Garansi layanan termasuk harga (bulan)"]
k_hw = (1 + cont) * (1 + mk_hw) / (1 - comm)
k_inst = (1 + mk_inst) / (1 - comm)


def sell(cost, k):
    return int(math.ceil(cost * k / 1000.0) * 1000)


rab = src["RAB"]
items = []          # (group, component, brand, spec, qty_a, qty_b, unit_sell)
group = None
for r in range(5, rab.max_row + 1):
    a, b = rab[f"A{r}"].value, rab[f"B{r}"].value
    if a and not b and rab[f"G{r}"].value is None:
        group = a
        continue
    if b and rab[f"G{r}"].value is not None and rab[f"E{r}"].value is not None:
        k = k_inst if a == "Instalasi" else k_hw
        items.append((group, b, rab[f"C{r}"].value, rab[f"D{r}"].value, rab[f"E{r}"].value, rab[f"F{r}"].value, sell(rab[f"G{r}"].value, k)))
total = {"A": src["Skenario A"]["B16"].value, "B": src["Skenario B"]["B16"].value}
goods = {o: sum((qa if o == "A" else qb) * unit for grp, _, _, _, qa, qb, unit in items if not (grp and grp.startswith("Opsi upgrade")))
         for o in "AB"}
# the same service in both options carries the same price: the smaller remainder, rounded down to Rp 100.000
SERVICE = min(total[o] - goods[o] for o in "AB") // 100000 * 100000
maint = src["Skenario A"]["B31"].value

# ---------------------------------------------------------------- client workbook
wb = Workbook()
wb.remove(wb.active)
wb.properties.creator = "Tim Cafe Vision"
wb.properties.title = "Penawaran Cafe Vision 4 Kamera"


def sheet(name, widths):
    ws = wb.create_sheet(name)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_view.showGridLines = False
    return ws


def put(ws, ref, value, bold=False, fmt=None, fill=None, wrap=False, size=10, italic=False, color="000000", right=False):
    c = ws[ref]
    c.value = value
    c.font = Font(name=F, size=size, bold=bold, italic=italic, color=color)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    c.alignment = Alignment(vertical="top", wrap_text=wrap, horizontal="right" if right else None)
    return c


def header(ws, row, labels):
    for i, lab in enumerate(labels, 1):
        put(ws, f"{get_column_letter(i)}{row}", lab, bold=True, fill=HEAD, wrap=True, color="FFFFFF").border = BOX


def band(ws, row, text, ncols):
    for i in range(1, ncols + 1):
        ws[f"{get_column_letter(i)}{row}"].fill = SUB
    put(ws, f"A{row}", text, bold=True, fill=SUB)


def bullets(ws, row, lines, ncols, height=30):
    for t in lines:
        put(ws, f"A{row}", "• " + t, wrap=True, color="404040")
        ws.merge_cells(f"A{row}:{get_column_letter(ncols)}{row}")
        ws.row_dimensions[row].height = height
        row += 1
    return row


SERVICE_SCOPE = ("Aplikasi analitik video AI + web app (lisensi 1 lokasi, 4 kamera), survey, setting zona meja kasir dan garis hitung, "
                 "pendaftaran wajah staf, kalibrasi di kondisi cafe, uji coba 1 minggu, training, serah terima, "
                 f"dan garansi layanan {warranty} bulan.")


def detail(name, ttl, opt):
    ws = sheet(name, [5, 30, 40, 50, 7, 16, 17])
    put(ws, "A1", ttl, bold=True, size=14)
    put(ws, "A2", "Harga dalam Rupiah, belum termasuk PPN.", italic=True, color="595959")
    header(ws, 4, ["No", "Item", "Merek / Tipe", "Spesifikasi", "Qty", "Harga satuan (Rp)", "Jumlah (Rp)"])
    r, n = 5, 1
    first_line = r
    cur = None
    for grp, comp, brand, spec, qa, qb, unit in items:
        qty = qa if opt == "A" else qb
        if grp and grp.startswith("Opsi upgrade") or not qty:
            continue
        g = grp.split(" (")[0] if grp else "Instalasi"
        if g != cur:
            band(ws, r, g, 7)
            r += 1
            cur = g
        put(ws, f"A{r}", n)
        put(ws, f"B{r}", comp, wrap=True)
        put(ws, f"C{r}", brand, wrap=True)
        put(ws, f"D{r}", spec, wrap=True, color="404040")
        put(ws, f"E{r}", qty, fmt="0")
        put(ws, f"F{r}", unit, fmt=RP)
        put(ws, f"G{r}", f"=E{r}*F{r}", fmt=RP)
        r += 1
        n += 1
    goods_last = r - 1
    band(ws, r, "Implementasi dan aplikasi", 7)
    r += 1
    put(ws, f"A{r}", n)
    put(ws, f"B{r}", "Implementasi, aplikasi AI dan web app", wrap=True)
    put(ws, f"C{r}", "Paket", wrap=True)
    put(ws, f"D{r}", SERVICE_SCOPE, wrap=True, color="404040")
    ws.row_dimensions[r].height = 64
    put(ws, f"E{r}", 1, fmt="0")
    put(ws, f"F{r}", SERVICE, fmt=RP)
    put(ws, f"G{r}", f"=E{r}*F{r}", fmt=RP)
    r += 2
    put(ws, f"D{r}", "Total (sebelum PPN)", bold=True, fill=TOTAL)
    put(ws, f"G{r}", f"=SUM(G{first_line}:G{r - 2})", bold=True, fmt=RP, fill=TOTAL)
    tot = r
    r += 1
    put(ws, f"D{r}", "PPN")
    put(ws, f"E{r}", ppn, fmt="0%")
    put(ws, f"G{r}", f"=G{tot}*E{r}", fmt=RP)
    r += 1
    put(ws, f"D{r}", "Total tagihan", bold=True, fill=TOTAL)
    put(ws, f"G{r}", f"=G{tot}+G{r - 1}", bold=True, fmt=RP, fill=TOTAL)
    return ws, tot, r


ws_a, tot_a, grand_a = detail("Rincian Opsi A", "Rincian Opsi A: memakai PC server milik cafe", "A")
ws_b, tot_b, grand_b = detail("Rincian Opsi B", "Rincian Opsi B: termasuk PC server AI baru", "B")

# ---------------------------------------------------------------- Ringkasan Penawaran
R = sheet("Ringkasan Penawaran", [46, 26, 26])
put(R, "A1", "Penawaran: Cafe Vision, Analitik Video AI 4 Kamera", bold=True, size=14)
put(R, "A2", "Kepada: [Nama Cafe]  ·  Tanggal: [isi tanggal]  ·  Berlaku 14 hari sejak tanggal penawaran", italic=True, color="595959")
header(R, 4, ["", "Opsi A: PC server milik cafe", "Opsi B: termasuk PC server baru"])
rows = [
    ("Total (sebelum PPN)", f"='Rincian Opsi A'!G{tot_a}", f"='Rincian Opsi B'!G{tot_b}"),
    ("PPN", f"='Rincian Opsi A'!G{tot_a + 1}", f"='Rincian Opsi B'!G{tot_b + 1}"),
    ("Total tagihan", f"='Rincian Opsi A'!G{grand_a}", f"='Rincian Opsi B'!G{grand_b}"),
    ("DP 50% saat PO", f"='Rincian Opsi A'!G{grand_a}*50%", f"='Rincian Opsi B'!G{grand_b}*50%"),
    ("Pelunasan 50% setelah uji coba dan serah terima", f"='Rincian Opsi A'!G{grand_a}*50%", f"='Rincian Opsi B'!G{grand_b}*50%"),
]
r = 5
for lab, fa, fb in rows:
    bold = lab == "Total tagihan"
    put(R, f"A{r}", lab, bold=True)
    put(R, f"B{r}", fa, fmt=RP, right=True, bold=bold, fill=TOTAL if bold else None)
    put(R, f"C{r}", fb, fmt=RP, right=True, bold=bold, fill=TOTAL if bold else None)
    r += 1
put(R, f"A{r}", "Maintenance setelah masa garansi (opsional, per bulan)", bold=True)
put(R, f"B{r}", maint, fmt=RP, right=True)
put(R, f"C{r}", maint, fmt=RP, right=True)
r += 2
band(R, r, "Yang Anda dapatkan", 3)
r = bullets(R, r + 1, [
    "Status kasir: kasir ada di meja kasir atau tidak, dan berapa lama (durasi per shift).",
    "Face recognition staf: kasir dan pelayan dikenali dari wajah yang sudah didaftarkan.",
    "Hitung pengunjung: jumlah orang masuk dan jumlah orang di dalam cafe per jam.",
    "Pelayan dan pelanggan dibedakan, sehingga hitungan pengunjung tidak tercampur staf.",
    "Dashboard web di cafe dan di HP pemilik, laporan harian, dan notifikasi bila kasir meninggalkan meja terlalu lama.",
    "Rekaman 4 kamera sekitar 30 hari di NVR, bisa dilihat dari aplikasi HP.",
], 3, 22)
r += 1
band(R, r, "Jadwal", 3)
r = bullets(R, r + 1, [
    "Sekitar 3 minggu sejak DP: survey dan pemasangan (minggu 1), setting dan kalibrasi (minggu 2), uji coba 1 minggu dan serah terima (minggu 3).",
], 3, 30)
r += 1
band(R, r, "Garansi", 3)
r = bullets(R, r + 1, [
    "Perangkat: garansi resmi pabrikan sesuai masing-masing produk.",
    f"Layanan: {warranty} bulan setelah serah terima (perbaikan jarak jauh dan 1 kunjungan pengecekan).",
], 3, 22)
r += 1
band(R, r, "Yang disiapkan cafe", 3)
r = bullets(R, r + 1, [
    "Listrik di titik kamera dan di lokasi server, internet cafe untuk akses dashboard dari HP.",
    "Persetujuan tertulis dari staf yang wajahnya didaftarkan, dan papan pemberitahuan CCTV di cafe.",
    "Opsi A: PC yang memenuhi syarat di sheet Syarat PC (Opsi A).",
], 3, 22)
r += 1
band(R, r, "Tidak termasuk", 3)
bullets(R, r + 1, [
    "Pekerjaan sipil dan kelistrikan baru, biaya internet, kunjungan di luar Jabodetabek.",
], 3, 22)

# ---------------------------------------------------------------- Syarat PC (Opsi A)
P = sheet("Syarat PC (Opsi A)", [26, 50, 56])
put(P, "A1", "Syarat Minimum PC Server Milik Cafe (Opsi A)", bold=True, size=14)
put(P, "A2", "Kami cek PC saat survey. Bila belum memenuhi, tersedia paket upgrade di bawah.", italic=True, color="595959")
header(P, 4, ["Komponen", "Minimum", "Alasan"])
reqs = [
    ("GPU", "NVIDIA, minimal 8 GB VRAM (contoh RTX 3060 12 GB, RTX 4060, RTX 5060)", "AI 4 kamera dan face recognition berjalan realtime."),
    ("CPU", "6 core generasi 2020 ke atas", "Memproses 4 video sekaligus."),
    ("RAM", "16 GB", "AI, database, dan web app berjalan bersamaan."),
    ("Penyimpanan", "SSD 500 GB kosong", "Sistem dan data laporan. Rekaman tetap di NVR."),
    ("Power supply", "550 W", "Menyala 24 jam dengan GPU."),
    ("Pemakaian", "Khusus server, menyala 24 jam", "Tidak dipakai bersamaan untuk kasir/POS."),
]
r = 5
for k, v, why in reqs:
    put(P, f"A{r}", k, bold=True)
    put(P, f"B{r}", v, wrap=True)
    put(P, f"C{r}", why, wrap=True, color="404040")
    P.row_dimensions[r].height = 28
    r += 1
r += 1
header(P, r, ["Paket upgrade (bila perlu)", "Merek / Tipe", "Harga (Rp, sebelum PPN)"])
r += 1
for grp, comp, brand, spec, qa, qb, unit in items:
    if grp and grp.startswith("Opsi upgrade"):
        put(P, f"A{r}", comp)
        put(P, f"B{r}", brand, wrap=True)
        put(P, f"C{r}", unit, fmt=RP)
        r += 1

wb._sheets = [wb[n] for n in ["Ringkasan Penawaran", "Rincian Opsi A", "Rincian Opsi B", "Syarat PC (Opsi A)"]]
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
