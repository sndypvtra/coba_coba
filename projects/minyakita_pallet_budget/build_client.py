"""Client quotation for the Minyakita loading-dock project, built from the internal budget (build_budget.py + recalc first).

Shows only selling prices, totals, terms and scope. Nothing internal: no purchase prices or price ranges, markup,
margin, day rates, exchange rate, CV income or purchase sources. Totals equal the internal ones.

    python build_client.py   # -> Penawaran_Minyakita_Loading_Dock.xlsx (then recalc with LibreOffice)
"""
import math
import re
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
mk_hw, mk_inst, warranty, ppn = kb["B6"].value, kb["B7"].value, kb["B8"].value, kb["B11"].value
sa, sb = src["Skenario A"], src["Skenario B"]
total_a = sa["B14"].value
maint_a = sa["B28"].value
year1, renew = sb["B13"].value, sb["B28"].value


def up1000(x):
    return int(math.ceil(x / 1000.0) * 1000)


def clean(name):
    return re.sub(r"\s*\([^)]*Rp[^)]*\)", "", name).strip()


goods = []          # (group, item, brand, qty, unit_sell)
hw = src["Hardware"]
group = None
for r in range(5, hw.max_row + 1):
    a, b, e = hw[f"A{r}"].value, hw[f"B{r}"].value, hw[f"E{r}"].value
    if a and not b:
        group = a
    elif b and e is not None and hw[f"D{r}"].value is not None:
        goods.append((group, b, clean(hw[f"C{r}"].value), hw[f"D{r}"].value, up1000(e * (1 + mk_hw))))
ins = src["Instalasi"]
for r in range(5, ins.max_row + 1):
    b, e = ins[f"B{r}"].value, ins[f"E{r}"].value
    if b and e is not None and ins[f"D{r}"].value is not None:
        goods.append(("Instalasi", b, clean(ins[f"C{r}"].value), ins[f"D{r}"].value, up1000(e * (1 + mk_inst))))
goods_total = sum(q * u for _, _, _, q, u in goods)
package_a = total_a - goods_total
# subscription lines, rounded to Rp 100.000, adding up exactly to the internal totals
support_year = round(sb["B12"].value, -5)
rent_year1 = round(sb["B10"].value, -5)
impl_year1 = year1 - rent_year1 - support_year
rent_renew = renew - support_year

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


def totals(ws, r, first, last):
    put(ws, f"C{r}", "Total (sebelum PPN)", bold=True, fill=TOTAL)
    put(ws, f"F{r}", f"=SUM(F{first}:F{last})", bold=True, fmt=RP, fill=TOTAL)
    put(ws, f"C{r + 1}", "PPN")
    put(ws, f"D{r + 1}", ppn, fmt="0%")
    put(ws, f"F{r + 1}", f"=F{r}*D{r + 1}", fmt=RP)
    put(ws, f"C{r + 2}", "Total tagihan", bold=True, fill=TOTAL)
    put(ws, f"F{r + 2}", f"=F{r}+F{r + 1}", bold=True, fmt=RP, fill=TOTAL)
    return r, r + 2


IMPL_SCOPE = ("Aplikasi AI hitung karton per palet + web app on-premise (lisensi 1 lokasi, 8 kamera), survey dock, "
              "pelabelan dan training model khusus kemasan Minyakita, rekonsiliasi per DO, kalibrasi 8 kamera, "
              "uji paralel 2 minggu dibanding hitung manual, training pengguna dan SOP, serah terima")

# ---------------------------------------------------------------- Rincian Opsi A
A = sheet("Rincian Opsi A", [5, 36, 62, 7, 17, 18])
put(A, "A1", "Rincian Opsi A: Beli Putus", bold=True, size=14)
put(A, "A2", "Semua perangkat, instalasi, dan aplikasi menjadi milik perusahaan. Harga dalam Rupiah, belum termasuk PPN.", italic=True, color="595959")
header(A, 4, ["No", "Item", "Merek / Tipe", "Qty", "Harga satuan (Rp)", "Jumlah (Rp)"])
r, n, cur, first = 5, 1, None, 5
for grp, item, brand, q, u in goods:
    g = grp.replace(" (rakit)", "")
    if g != cur:
        band(A, r, g, 6)
        r += 1
        cur = g
    put(A, f"A{r}", n)
    put(A, f"B{r}", item, wrap=True)
    put(A, f"C{r}", brand, wrap=True, color="404040")
    put(A, f"D{r}", q, fmt="0")
    put(A, f"E{r}", u, fmt=RP)
    put(A, f"F{r}", f"=D{r}*E{r}", fmt=RP)
    r += 1
    n += 1
band(A, r, "Implementasi dan aplikasi", 6)
r += 1
put(A, f"A{r}", n)
put(A, f"B{r}", "Implementasi, aplikasi AI dan web app (paket)", wrap=True)
put(A, f"C{r}", IMPL_SCOPE + f", garansi layanan {warranty} bulan.", wrap=True, color="404040")
A.row_dimensions[r].height = 64
put(A, f"D{r}", 1, fmt="0")
put(A, f"E{r}", package_a, fmt=RP)
put(A, f"F{r}", f"=D{r}*E{r}", fmt=RP)
tot_a, grand_a = totals(A, r + 2, first, r)

# ---------------------------------------------------------------- Rincian Opsi B
B = sheet("Rincian Opsi B", [5, 40, 62, 7, 17, 18])
put(B, "A1", "Rincian Opsi B: Langganan per Tahun", bold=True, size=14)
put(B, "A2", "Perangkat disediakan dan tetap milik penyedia, ditagih per tahun. Harga dalam Rupiah, belum termasuk PPN.", italic=True, color="595959")
header(B, 4, ["No", "Komponen langganan", "Keterangan", "Qty", "Harga (Rp)", "Jumlah (Rp)"])
band(B, 5, "Tahun pertama", 6)
lines1 = [
    ("Sewa perangkat dan instalasi, 12 bulan", "8 kamera, NVR + HDD 8 TB, PC server AI, UPS online, rack, switch, monitor, layar dock (daftar di bawah), terpasang di 8 titik", rent_year1),
    ("Implementasi, aplikasi AI dan web app (paket)", IMPL_SCOPE + ".", impl_year1),
    ("Layanan support dan maintenance, 12 bulan", "Kunjungan rutin bulanan, pemantauan akurasi dan retraining model, perbaikan dan update web app, laporan bulanan, penggantian perangkat rusak", support_year),
]
r = 6
for i, (lab, ket, v) in enumerate(lines1, 1):
    put(B, f"A{r}", i)
    put(B, f"B{r}", lab, wrap=True)
    put(B, f"C{r}", ket, wrap=True, color="404040")
    B.row_dimensions[r].height = 42
    put(B, f"D{r}", 1, fmt="0")
    put(B, f"E{r}", v, fmt=RP)
    put(B, f"F{r}", f"=D{r}*E{r}", fmt=RP)
    r += 1
tot_b1, grand_b1 = totals(B, r + 1, 6, r - 1)
r = grand_b1 + 2
band(B, r, "Perpanjangan tahun berikutnya", 6)
r += 1
first_renew = r
for i, (lab, ket, v) in enumerate([
    ("Sewa perangkat, 12 bulan", "Perangkat yang sama, tetap terpasang", rent_renew),
    ("Layanan support dan maintenance, 12 bulan", "Sama seperti tahun pertama", support_year),
], 1):
    put(B, f"A{r}", i)
    put(B, f"B{r}", lab, wrap=True)
    put(B, f"C{r}", ket, wrap=True, color="404040")
    put(B, f"D{r}", 1, fmt="0")
    put(B, f"E{r}", v, fmt=RP)
    put(B, f"F{r}", f"=D{r}*E{r}", fmt=RP)
    r += 1
tot_bn, grand_bn = totals(B, r + 1, first_renew, r - 1)
r = grand_bn + 2
band(B, r, "Perangkat yang disediakan (tanpa harga, tetap milik penyedia)", 6)
r += 1
for grp, item, brand, q, u in goods:
    if grp == "Instalasi":
        continue
    put(B, f"B{r}", item, wrap=True)
    put(B, f"C{r}", brand, wrap=True, color="404040")
    put(B, f"D{r}", q, fmt="0")
    r += 1

# ---------------------------------------------------------------- Ringkasan Penawaran
R = sheet("Ringkasan Penawaran", [52, 26, 26, 26])
put(R, "A1", "Penawaran: Sistem Hitung Karton per Palet di Loading Dock (8 Kamera)", bold=True, size=14)
put(R, "A2", "Kepada: PT [nama perusahaan], Gudang Minyakita  ·  Tanggal: [isi tanggal]  ·  Berlaku 14 hari sejak tanggal penawaran",
    italic=True, color="595959")
header(R, 4, ["", "Opsi A: Beli putus", "Opsi B: Langganan, tahun pertama", "Opsi B: Langganan, tahun berikutnya"])
rows = [
    ("Total (sebelum PPN)", f"='Rincian Opsi A'!F{tot_a}", f"='Rincian Opsi B'!F{tot_b1}", f"='Rincian Opsi B'!F{tot_bn}"),
    ("PPN", f"='Rincian Opsi A'!F{tot_a + 1}", f"='Rincian Opsi B'!F{tot_b1 + 1}", f"='Rincian Opsi B'!F{tot_bn + 1}"),
    ("Total tagihan", f"='Rincian Opsi A'!F{grand_a}", f"='Rincian Opsi B'!F{grand_b1}", f"='Rincian Opsi B'!F{grand_bn}"),
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
put(R, f"C{r}", "Penyedia", right=True)
put(R, f"D{r}", "Penyedia", right=True)
r += 1
put(R, f"A{r}", "Maintenance setelah masa garansi (Opsi A, opsional, per tahun)", bold=True)
put(R, f"B{r}", maint_a, fmt=RP, right=True)
put(R, f"C{r}", "termasuk", right=True)
put(R, f"D{r}", "termasuk", right=True)
r += 2
band(R, r, "Termin pembayaran", 4)
r = bullets(R, r + 1, [
    "Opsi A: DP 50% saat PO, 30% setelah instalasi selesai, 20% setelah uji paralel dan serah terima.",
    "Opsi B tahun pertama: 50% saat PO, 50% saat sistem mulai dipakai (go-live). Tahun berikutnya: dibayar di awal periode langganan.",
    "Opsi B: masa langganan minimal 12 bulan.",
], 4)
r += 1
band(R, r, "Yang didapatkan", 4)
r = bullets(R, r + 1, [
    "Hitung karton setiap palet (standar 60 karton) di zona cek depan dock, dan peringatan langsung bila palet kurang.",
    "Rekonsiliasi jumlah karton per DO, per truk, dan per palet sebelum barang naik ke armada ekspedisi.",
    "Dashboard web on-premise di kantor gudang dan layar status di loading dock; laporan per DO, truk, dan palet.",
    "Rekaman 8 kamera di NVR sebagai bukti audit dan penyelesaian selisih.",
    "Seluruh sistem berjalan di lokasi (on-premise), tanpa cloud; data tetap di gudang.",
], 4)
r += 1
band(R, r, "Jadwal", 4)
r = bullets(R, r + 1, [
    "Sekitar 8 sampai 10 minggu sejak PO: survey dan desain, pengambilan data dan training model, instalasi dan kalibrasi, uji paralel 2 minggu, serah terima.",
], 4, 30)
r += 1
band(R, r, "Garansi dan layanan", 4)
r = bullets(R, r + 1, [
    "Opsi A: perangkat bergaransi resmi pabrikan; layanan " + str(warranty) + " bulan setelah serah terima.",
    "Opsi B: selama masa langganan, layanan support, maintenance, dan penggantian perangkat rusak ditanggung penyedia.",
], 4)
r += 1
band(R, r, "Yang disiapkan perusahaan", 4)
r = bullets(R, r + 1, [
    "Listrik di titik kamera dan ruang server, alat kerja ketinggian (forklift dengan man basket atau sejenisnya) saat pemasangan.",
    "Data DO (ekspor file atau akses API WMS/ERP) dan satu PIC gudang untuk koordinasi dan uji paralel.",
    "SOP: palet berhenti sejenak di zona cek, plastik wrap bening agar karton terlihat kamera.",
], 4)
r += 1
band(R, r, "Tidak termasuk", 4)
bullets(R, r + 1, [
    "Pekerjaan sipil, instalasi listrik baru, dan perjalanan di luar Jabodetabek (ditagihkan sesuai biaya aktual bila ada).",
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
