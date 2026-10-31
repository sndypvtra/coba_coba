"""Client quotation for the Minyakita loading-dock project, built from the internal budget (build_budget.py + recalc first).

Shows only selling prices, totals, terms and scope. Nothing internal: no purchase prices, markup, contingency,
margin, day rates, exchange rate, CV income or purchase sources. Totals equal the internal ones.

    python build_client.py   # -> Penawaran_Minyakita_Loading_Dock.xlsx (then recalc with LibreOffice)
"""
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
SRC = HERE / "Budget_Minyakita_Pallet_Counting.xlsx"
OUT = HERE / "Penawaran_Minyakita_Loading_Dock.xlsx"
F = "Arial"
HEAD = PatternFill("solid", fgColor="1F3864")
SUB = PatternFill("solid", fgColor="D9E1F2")
TOTAL = PatternFill("solid", fgColor="F2F2F2")
RP = '#,##0;(#,##0);"-"'
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

# ---------------------------------------------------------------- internal values (never written to the client file)
src = load_workbook(SRC, data_only=True)
kb = src["Keputusan Bisnis"]


def by_label(ws, label, col="B"):
    """Value next to a label in column A (the scenario sheets are label/value lists)."""
    for r in range(1, ws.max_row + 1):
        if ws[f"A{r}"].value == label:
            return ws[f"{col}{r}"].value
    raise KeyError(f"{ws.title}: {label}")


warranty = by_label(kb, "Garansi layanan termasuk harga Opsi A (bulan)")
ppn = by_label(kb, "PPN efektif (isi 0 bila belum PKP)")
sa, sb = src["Skenario A"], src["Skenario B"]
total_a = by_label(sa, "Total harga (sebelum PPN)")
garansi_a = by_label(sa, "Garansi layanan")
maint_a = by_label(sa, "Maintenance opsional per tahun setelah garansi")
free_b = by_label(kb, "Layanan termasuk di tahun pertama Opsi B (bulan)")
support_b1 = by_label(sb, "Layanan support tahun pertama")
year1 = by_label(sb, "Total tahun pertama (sebelum PPN)")
renew = by_label(sb, "Langganan per tahun (sebelum PPN)")

CLIENT_NAME = {   # internal item names -> client wording
    "PC server AI (rakitan Agres)": "PC server AI (workstation GPU)",
    "Jasa pasang IP camera (jasa saja)": "Jasa pasang kamera per titik",
}
goods = []          # (category, item, brand, spec, qty, unit_sell)
rab = src["RAB"]
for r in range(5, rab.max_row + 1):
    a, b, e, h = (rab[f"{c}{r}"].value for c in "ABEH")
    if a and b and e is not None and h is not None:
        spec = rab[f"D{r}"].value
        if b == "Jasa pasang IP camera (jasa saja)":
            spec = "Tarik kabel dan pasang conduit, pasang kamera, setting sudut pandang"
        goods.append((a, CLIENT_NAME.get(b, b), rab[f"C{r}"].value, spec, e, h))
goods_total = sum(q * u for *_, q, u in goods)

# service groups from the jasa sheet: name -> (value, task list without days or rates)
js = src["Jasa INKINDO"]
services, grp = {}, None
for r in range(1, js.max_row + 1):
    a, b, h = js[f"A{r}"].value, js[f"B{r}"].value, js[f"H{r}"].value
    if a in ("Pembuatan AI", "Pembuatan Web App", "Implementasi Lapangan", "Manajemen Proyek"):
        grp = a
        services[grp] = [0, []]
    elif grp and isinstance(a, int):
        services[grp][1].append(b)
    elif grp and b == f"Subtotal {grp}":
        services[grp][0] = h
        grp = None
assert goods_total + sum(v for v, _ in services.values()) + garansi_a == total_a, "Opsi A tidak sama dengan budget"
assert goods_total + sum(v for v, _ in services.values()) + support_b1 == year1, "Opsi B tidak sama dengan budget"

# ---------------------------------------------------------------- client workbook
wb = Workbook()
wb.remove(wb.active)
wb.properties.creator = "Tim Implementasi"
wb.properties.title = "Penawaran Sistem Hitung Karton per Palet, Loading Dock"


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


def bullets(ws, row, lines, ncols, height=22):
    for t in lines:
        put(ws, f"A{row}", "• " + t, wrap=True, color="404040")
        ws.merge_cells(f"A{row}:{get_column_letter(ncols)}{row}")
        ws.row_dimensions[row].height = height
        row += 1
    return row


def line(ws, r, n, item, brand, spec, qty, unit, height=None):
    put(ws, f"A{r}", n)
    put(ws, f"B{r}", item, wrap=True)
    put(ws, f"C{r}", brand, wrap=True, color="404040")
    put(ws, f"D{r}", spec, wrap=True, color="404040")
    put(ws, f"E{r}", qty, fmt="0")
    put(ws, f"F{r}", unit, fmt=RP if unit != "termasuk" else None, right=True)
    put(ws, f"G{r}", f"=E{r}*F{r}" if unit != "termasuk" else 0, fmt=RP)
    longest = max(len(str(item or "")) / 30, len(str(brand or "")) / 28, len(str(spec or "")) / 52)
    ws.row_dimensions[r].height = height or max(15, 13 * (int(longest) + 1))


def subtotal(ws, r, name, first, last):
    for col in "BCDEFG":
        ws[f"{col}{r}"].fill = TOTAL
    put(ws, f"B{r}", f"Subtotal {name}", bold=True, fill=TOTAL)
    put(ws, f"G{r}", f"=SUM(G{first}:G{last})", bold=True, fmt=RP, fill=TOTAL)
    return f"G{r}"


def totals(ws, r, cells, label="Total (sebelum PPN)"):
    put(ws, f"D{r}", label, bold=True, fill=TOTAL)
    put(ws, f"G{r}", "=" + "+".join(cells), bold=True, fmt=RP, fill=TOTAL)
    put(ws, f"D{r + 1}", "PPN")
    put(ws, f"F{r + 1}", ppn, fmt="0%")
    put(ws, f"G{r + 1}", f"=G{r}*F{r + 1}", fmt=RP)
    put(ws, f"D{r + 2}", "Total tagihan", bold=True, fill=TOTAL)
    put(ws, f"G{r + 2}", f"=G{r}+G{r + 1}", bold=True, fmt=RP, fill=TOTAL)
    return r, r + 2


SERVICE_TEXT = {
    "Pembuatan AI": "Model AI khusus kemasan Minyakita, berjalan realtime 8 kamera pada 20-30 fps",
    "Pembuatan Web App": "Web app on-premise untuk dock dan manajemen",
    "Implementasi Lapangan": "Pemasangan, kalibrasi, uji paralel, dan serah terima di lokasi",
    "Manajemen Proyek": "Pengelolaan proyek selama 8-10 minggu",
}
SUPPORT_TEXT = ("Kunjungan rutin bulanan (cek kamera, lensa, server, rekaman), pemantauan akurasi dan retraining model, "
                "perbaikan dan update web app")
WIDTHS = [5, 30, 28, 52, 6, 17, 18]
COLS = ["No", "Item", "Merek / Tipe", "Spesifikasi / lingkup", "Qty", "Harga satuan (Rp)", "Jumlah (Rp)"]


def service_lines(ws, r, n):
    for name, (value, tasks) in services.items():
        line(ws, r, n, f"Jasa {name}", SERVICE_TEXT[name], "; ".join(tasks), 1, value)
        r, n = r + 1, n + 1
    return r, n


SERVICES_BAND = "Aplikasi AI, web app, dan implementasi"


def full_breakdown(ws, r, support_label, support_brand, support_value):
    """Every device, installation and service line with a subtotal per category; returns (next row, subtotal cells)."""
    n, subs = 1, []
    for cat in dict.fromkeys(g[0] for g in goods):
        band(ws, r, cat, 7)
        first = r = r + 1
        for _, item, brand, spec, q, u in (g for g in goods if g[0] == cat):
            line(ws, r, n, item, brand, spec, q, u if u else "termasuk")
            r, n = r + 1, n + 1
        subs.append(subtotal(ws, r, cat, first, r - 1))
        r += 1
    band(ws, r, SERVICES_BAND, 7)
    first = r + 1
    r, n = service_lines(ws, first, n)
    line(ws, r, n, support_label, support_brand, SUPPORT_TEXT, 1, support_value)
    subs.append(subtotal(ws, r + 1, SERVICES_BAND, first, r))
    return r + 3, subs


# ---------------------------------------------------------------- Rincian Opsi A
A = sheet("Rincian Opsi A", WIDTHS)
put(A, "A1", "Rincian Opsi A: Beli Putus", bold=True, size=14)
put(A, "A2", "Semua perangkat, instalasi, aplikasi AI, dan web app menjadi milik perusahaan. Harga dalam Rupiah, belum termasuk PPN.",
    italic=True, color="595959")
header(A, 4, COLS)
r, subs = full_breakdown(A, 5, f"Garansi layanan {warranty} bulan", "Setelah serah terima", garansi_a)
tot_a, grand_a = totals(A, r, subs)

# ---------------------------------------------------------------- Rincian Opsi B
B = sheet("Rincian Opsi B", WIDTHS)
put(B, "A1", "Rincian Opsi B: Langganan Layanan Tahunan", bold=True, size=14)
put(B, "A2", f"Tahun pertama harganya sama dengan beli putus, dengan layanan {free_b} bulan (Opsi A: {warranty} bulan). "
    "Mulai tahun kedua dibayar langganan layanan per tahun. Harga dalam Rupiah, belum termasuk PPN.", italic=True, color="595959")
header(B, 4, COLS)
band(B, 5, "TAHUN PERTAMA", 7)
r, subs = full_breakdown(B, 6, f"Layanan support dan maintenance {free_b} bulan",
                         f"Setelah serah terima, harga sama dengan garansi {warranty} bulan Opsi A", support_b1)
tot_b1, grand_b1 = totals(B, r, subs, "Total tahun pertama (sebelum PPN)")
r = grand_b1 + 2
band(B, r, "LANGGANAN TAHUN BERIKUTNYA (per tahun)", 7)
line(B, r + 1, 1, "Layanan support dan maintenance, 12 bulan", "Dibayar di awal tiap periode", SUPPORT_TEXT, 1, renew)
tot_bn, grand_bn = totals(B, r + 3, [f"G{r + 1}"], "Langganan per tahun (sebelum PPN)")

# ---------------------------------------------------------------- Ringkasan Penawaran
R = sheet("Ringkasan Penawaran", [52, 26, 26, 26])
put(R, "A1", "Penawaran: Sistem Hitung Karton per Palet di Loading Dock (8 Kamera)", bold=True, size=14)
put(R, "A2", "Kepada: PT [nama perusahaan], Gudang Minyakita  ·  Tanggal: [isi tanggal]  ·  Berlaku 14 hari sejak tanggal penawaran",
    italic=True, color="595959")
header(R, 4, ["", "Opsi A: Beli putus", "Opsi B: Tahun pertama", "Opsi B: Langganan per tahun berikutnya"])
rows = [
    ("Total (sebelum PPN)", f"='Rincian Opsi A'!G{tot_a}", f"='Rincian Opsi B'!G{tot_b1}", f"='Rincian Opsi B'!G{tot_bn}"),
    ("PPN", f"='Rincian Opsi A'!G{tot_a + 1}", f"='Rincian Opsi B'!G{tot_b1 + 1}", f"='Rincian Opsi B'!G{tot_bn + 1}"),
    ("Total tagihan", f"='Rincian Opsi A'!G{grand_a}", f"='Rincian Opsi B'!G{grand_b1}", f"='Rincian Opsi B'!G{grand_bn}"),
]
r = 5
for lab, fa, fb, fc in rows:
    bold = lab == "Total tagihan"
    put(R, f"A{r}", lab, bold=True)
    for col, f in zip("BCD", (fa, fb, fc)):
        put(R, f"{col}{r}", f, fmt=RP, right=True, bold=bold, fill=TOTAL if bold else None)
    r += 1
put(R, f"A{r}", "Pemilik perangkat", bold=True)
put(R, f"B{r}", "Perusahaan", right=True)
put(R, f"C{r}", "Perusahaan", right=True)
put(R, f"D{r}", "Perusahaan", right=True)
r += 1
put(R, f"A{r}", "Layanan support dan maintenance", bold=True)
put(R, f"B{r}", f"{warranty} bulan termasuk", right=True)
put(R, f"C{r}", f"{free_b} bulan termasuk", right=True)
put(R, f"D{r}", "12 bulan termasuk", right=True)
r += 1
put(R, f"A{r}", "Maintenance setelah masa garansi (Opsi A, opsional, per tahun)", bold=True)
put(R, f"B{r}", maint_a, fmt=RP, right=True)
put(R, f"C{r}", "-", right=True)
put(R, f"D{r}", "-", right=True)
r += 2
band(R, r, "Termin pembayaran", 4)
r = bullets(R, r + 1, [
    "Opsi A: DP 50% saat PO, 30% setelah instalasi selesai, 20% setelah uji paralel dan serah terima.",
    "Opsi B tahun pertama: sama dengan Opsi A (50% / 30% / 20%). Langganan tahun berikutnya dibayar di awal tiap periode 12 bulan.",
    "Opsi B: komitmen langganan minimal 1 tahun setelah tahun pertama.",
], 4)
r += 1
band(R, r, "Yang didapatkan", 4)
r = bullets(R, r + 1, [
    "Hitung karton setiap palet (standar 60 karton) di zona cek depan dock, dan peringatan langsung bila palet kurang.",
    "Video analytics realtime 8 kamera pada 20-30 fps, diproses di PC server AI dengan GPU NVIDIA RTX 5070 Ti 16 GB di lokasi.",
    "Rekonsiliasi jumlah karton per DO, per truk, dan per palet sebelum barang naik ke armada ekspedisi.",
    "Web app on-premise, dibuka dari laptop tim gudang lewat jaringan/VPN perusahaan (tanpa install aplikasi), plus TV status di loading dock; laporan per DO, truk, dan palet.",
    "Rekaman 8 kamera sebagai bukti audit dan penyelesaian selisih.",
    "Seluruh sistem berjalan di lokasi (on-premise), tanpa cloud; data tetap di gudang.",
], 4)
r += 1
band(R, r, "Jadwal", 4)
r = bullets(R, r + 1, [
    "Sekitar 8 sampai 10 minggu sejak PO: survey dan desain, pengambilan data dan training model, pembuatan web app, "
    "instalasi dan kalibrasi, uji paralel 2 minggu (termasuk uji performa 8 kamera), serah terima.",
], 4, 30)
r += 1
band(R, r, "Garansi dan layanan", 4)
r = bullets(R, r + 1, [
    "Opsi A: perangkat bergaransi resmi pabrikan; layanan " + str(warranty) + " bulan setelah serah terima.",
    f"Opsi B: perangkat bergaransi resmi pabrikan; layanan {free_b} bulan di tahun pertama, lalu berlanjut selama langganan aktif.",
], 4)
r += 1
band(R, r, "Yang disiapkan perusahaan", 4)
r = bullets(R, r + 1, [
    "Listrik di titik kamera dan ruang server, alat kerja ketinggian (forklift dengan man basket atau sejenisnya) saat pemasangan.",
    "Laptop untuk memantau dashboard, serta 1 alamat IP dan port LAN di jaringan perusahaan untuk server dan TV dock (akses dari luar gudang lewat VPN perusahaan yang sudah ada).",
    "Data DO (ekspor file atau akses API WMS/ERP) dan satu PIC gudang untuk koordinasi dan uji paralel.",
    "SOP: palet berhenti sejenak di zona cek, plastik wrap bening agar karton terlihat kamera.",
], 4)
r += 1
band(R, r, "Catatan", 4)
bullets(R, r + 1, [
    "Jumlah kabel dan conduit berdasarkan perkiraan; disesuaikan setelah survey lokasi.",
    "Tidak termasuk pekerjaan sipil, instalasi listrik baru, dan perjalanan di luar Jabodetabek (ditagihkan sesuai biaya aktual bila ada).",
], 4)

wb._sheets = [wb[n] for n in ["Ringkasan Penawaran", "Rincian Opsi A", "Rincian Opsi B"]]
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
