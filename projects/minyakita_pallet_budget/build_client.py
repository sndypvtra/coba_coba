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
sa, sb = src["Skenario A"], src["Skenario B"]
total_a = by_label(sa, "Total harga")
gar_sw_a = by_label(sa, "Garansi software AI dan web app")
gar_inf_a = by_label(sa, "Garansi infrastruktur")
maint_a = by_label(sa, "Maintenance opsional per tahun setelah garansi")
cr_sw = by_label(kb, "Tarif change request software (AI computer vision dan web app) per hari kerja")
cr_inf = by_label(kb, "Tarif change request infrastruktur per hari kerja")
term = by_label(kb, "Kontrak minimum Opsi B (bulan)")
late = by_label(kb, "Batas telat bayar sebelum layanan dihentikan sementara (hari)")
setup_b = by_label(sb, "Total jasa sekali bayar")
rent_b = by_label(sb, "Sewa perangkat dan pemasangan")
sup_sw_b = by_label(sb, "Support software AI dan web app 12 bulan")
sup_inf_b = by_label(sb, "Support infrastruktur 12 bulan")
reserve_b = by_label(sb, "Jaminan penggantian perangkat")
sub_b = by_label(sb, "Langganan per tahun")
year1 = by_label(sb, "Tahun pertama (jasa sekali bayar + langganan)")
total_b = by_label(sb, "Total selama kontrak minimum")
YEARS = int(term // 12)

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
SOFTWARE = ("Pembuatan AI Computer Vision", "Pembuatan Web App", "Setup dan Implementasi AI dan Web App")
INFRA = ("Implementasi Infrastruktur", "Manajemen Proyek")
js = src["Jasa INKINDO"]
services, grp = {}, None
for r in range(1, js.max_row + 1):
    a, b, h = js[f"A{r}"].value, js[f"B{r}"].value, js[f"H{r}"].value
    if a in SOFTWARE + INFRA:
        grp = a
        services[grp] = [0, []]
    elif grp and isinstance(a, int):
        services[grp][1].append(b)
    elif grp and b == f"Subtotal {grp}":
        services[grp][0] = by_label(sa, grp)
        grp = None
assert len(services) == 5
assert goods_total + sum(v for v, _ in services.values()) + gar_sw_a + gar_inf_a == total_a, "Opsi A tidak sama dengan budget"
assert sum(v for v, _ in services.values()) == setup_b and rent_b + sup_sw_b + sup_inf_b + reserve_b == sub_b, "Opsi B tidak sama dengan budget"
assert setup_b + sub_b == year1 and setup_b + sub_b * YEARS == total_b

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


def totals(ws, r, cells, label="Total harga"):
    for col in "DEFG":
        ws[f"{col}{r}"].fill = TOTAL
    put(ws, f"D{r}", label, bold=True, fill=TOTAL)
    put(ws, f"G{r}", "=" + "+".join(cells), bold=True, fmt=RP, fill=TOTAL)
    return r, r


SERVICE_TEXT = {
    "Pembuatan AI Computer Vision": "Model AI khusus kemasan Minyakita, berjalan realtime 8 kamera pada 20-30 fps",
    "Pembuatan Web App": "Web app video analytics on-premise: live view, dashboard, laporan, event trigger dan riwayat event",
    "Setup dan Implementasi AI dan Web App": "Setup dan kalibrasi model, uji akurasi, training web app, akses jarak jauh owner",
    "Implementasi Infrastruktur": "Survey, instalasi perangkat, uji paralel lapangan, dan serah terima",
    "Manajemen Proyek": "Pengelolaan proyek selama sekitar 16 minggu",
}
SUPPORT_SW_TEXT = "Pemantauan akurasi dan retraining model, perbaikan dan update web app"
SUPPORT_SW_B_TEXT = ("Pemantauan sistem jarak jauh, review akurasi bulanan, retraining model per kuartal, perbaikan bug, "
                     "update web app dan keamanan, penyesuaian konfigurasi (zona, ambang, akun, format laporan); "
                     "respons gangguan kritis maksimal 1x24 jam")
SUPPORT_INF_TEXT = "Kunjungan rutin bulanan: cek kamera, bersihkan lensa, cek server, jaringan, dan rekaman"
WIDTHS = [5, 30, 28, 52, 6, 17, 18]
COLS = ["No", "Item", "Merek / Tipe", "Spesifikasi / lingkup", "Qty", "Harga satuan (Rp)", "Jumlah (Rp)"]


def service_lines(ws, r, n, names):
    for name in names:
        value, tasks = services[name]
        line(ws, r, n, f"Jasa {name}", SERVICE_TEXT[name], "; ".join(tasks), 1, value)
        r, n = r + 1, n + 1
    return r, n


SOFTWARE_BAND = "Aplikasi AI computer vision dan web app"
INFRA_BAND = "Jasa infrastruktur dan manajemen proyek"


def full_breakdown(ws, r):
    """Every device, installation and service line with a subtotal per category; returns (next row, subtotal cells)."""
    n, subs = 1, []
    for cat in dict.fromkeys(g[0] for g in goods if g[0] != "Jasa pasang"):
        band(ws, r, cat, 7)
        first = r = r + 1
        for _, item, brand, spec, q, u in (g for g in goods if g[0] == cat):
            line(ws, r, n, item, brand, spec, q, u if u else "termasuk")
            r, n = r + 1, n + 1
        subs.append(subtotal(ws, r, cat, first, r - 1))
        r += 1
    band(ws, r, INFRA_BAND, 7)
    first = r = r + 1
    for _, item, brand, spec, q, u in (g for g in goods if g[0] == "Jasa pasang"):
        line(ws, r, n, item, brand, spec, q, u)
        r, n = r + 1, n + 1
    r, n = service_lines(ws, r, n, INFRA)
    subs.append(subtotal(ws, r, INFRA_BAND, first, r - 1))
    r += 1
    band(ws, r, SOFTWARE_BAND, 7)
    first = r + 1
    r, n = service_lines(ws, first, n, SOFTWARE)
    subs.append(subtotal(ws, r, SOFTWARE_BAND, first, r - 1))
    r += 1
    band(ws, r, f"Garansi {warranty} bulan setelah serah terima", 7)
    first = r + 1
    line(ws, r + 1, n, "Garansi software AI dan web app", f"{warranty} bulan", SUPPORT_SW_TEXT, 1, gar_sw_a)
    line(ws, r + 2, n + 1, "Garansi infrastruktur", f"{warranty} bulan", SUPPORT_INF_TEXT, 1, gar_inf_a)
    subs.append(subtotal(ws, r + 3, "garansi", first, r + 2))
    return r + 5, subs


# ---------------------------------------------------------------- Rincian Opsi A
A = sheet("Rincian Opsi A", WIDTHS)
put(A, "A1", "Rincian Opsi A: Beli Putus", bold=True, size=14)
put(A, "A2", "Semua perangkat, instalasi, aplikasi AI, dan web app menjadi milik perusahaan. Harga dalam Rupiah, tidak dikenakan PPN.",
    italic=True, color="595959")
header(A, 4, COLS)
r, subs = full_breakdown(A, 5)
tot_a, grand_a = totals(A, r, subs)

# ---------------------------------------------------------------- Rincian Opsi B
B = sheet("Rincian Opsi B", WIDTHS)
put(B, "A1", f"Rincian Opsi B: Sewa dan Langganan, Kontrak Minimum {term} Bulan", bold=True, size=14)
put(B, "A2", "Perangkat disediakan, dipasang, dan dirawat penyedia. Jasa aplikasi dan jasa infrastruktur dibayar sekali; "
    "langganan dibayar di muka per 12 bulan. "
    "Harga dalam Rupiah, tidak dikenakan PPN.", italic=True, color="595959")
header(B, 4, COLS)
band(B, 5, SOFTWARE_BAND + " (dibayar sekali)", 7)
r, n = service_lines(B, 6, 1, SOFTWARE)
sw_cell = subtotal(B, r, SOFTWARE_BAND, 6, r - 1)
band(B, r + 1, INFRA_BAND + " (dibayar sekali)", 7)
first = r + 2
r, n = service_lines(B, first, n, INFRA)
inf_cell = subtotal(B, r, INFRA_BAND, first, r - 1)
setup_cell = f"{sw_cell}+{inf_cell}"
r += 2
band(B, r, "LANGGANAN PER TAHUN (dibayar di muka per 12 bulan)", 7)
first = r + 1
line(B, r + 1, 1, "Sewa perangkat dan pemasangan", "Seluruh perangkat di daftar bawah",
     "8 kamera, PC server AI, penyimpanan rekaman dan backup, UPS, rak dan jaringan, TV status loading dock; terpasang di 8 titik", 1, rent_b)
line(B, r + 2, 2, "Support software AI dan web app", "12 bulan, menggantikan garansi", SUPPORT_SW_B_TEXT, 1, sup_sw_b)
line(B, r + 3, 3, "Support infrastruktur", "12 bulan, menggantikan garansi", SUPPORT_INF_TEXT, 1, sup_inf_b)
line(B, r + 4, 4, "Jaminan penggantian perangkat", "Kerusakan karena pemakaian normal",
     "Perangkat rusak diganti unit setara oleh penyedia, termasuk setelah garansi pabrik habis", 1, reserve_b)
sub_cell = subtotal(B, r + 5, "langganan per tahun", first, r + 4)
r += 7
band(B, r, f"TAGIHAN SELAMA KONTRAK MINIMUM ({term} bulan)", 7)
r += 1
year_rows = []
for y in range(1, YEARS + 1):
    put(B, f"B{r}", f"Tahun ke-{y}" + (" (jasa sekali bayar + langganan)" if y == 1 else " (langganan)"), wrap=True)
    put(B, f"G{r}", f"={setup_cell}+{sub_cell}" if y == 1 else f"={sub_cell}", fmt=RP)
    year_rows.append(f"G{r}")
    r += 1
tot_bk, grand_bk = totals(B, r + 1, year_rows, f"Total kontrak {term} bulan")
r = grand_bk + 2
band(B, r, "BIAYA PEMUTUSAN bila kontrak dihentikan sebelum masa minimum", 7)
r += 1
for y in range(1, YEARS):
    put(B, f"B{r}", f"Berhenti setelah tahun ke-{y}")
    put(B, f"D{r}", f"Sisa sewa perangkat sampai bulan ke-{term} ({YEARS - y} tahun)", color="404040")
    put(B, f"G{r}", f"=F{first}*{YEARS - y}", fmt=RP)
    r += 1
put(B, f"B{r}", "Jasa sekali bayar dan langganan yang sudah dibayar tidak dikembalikan. Sebagai ganti biaya pemutusan, perusahaan dapat "
    "membeli perangkat dengan nilai yang sama.", wrap=True, color="404040", italic=True)
B.merge_cells(f"B{r}:G{r}")
B.row_dimensions[r].height = 28
r += 2
band(B, r, "Perangkat yang disediakan (tanpa harga, tetap milik penyedia)", 7)
r += 1
for cat, item, brand, spec, q, u in goods:
    if cat == "Jasa pasang":
        continue
    put(B, f"B{r}", item, wrap=True)
    put(B, f"C{r}", brand, wrap=True, color="404040")
    put(B, f"D{r}", spec, wrap=True, color="404040")
    put(B, f"E{r}", q, fmt="0")
    B.row_dimensions[r].height = max(15, 13 * (int(max(len(str(brand)) / 28, len(str(spec)) / 52)) + 1))
    r += 1

# ---------------------------------------------------------------- Ringkasan Penawaran
R = sheet("Ringkasan Penawaran", [52, 26, 26, 26])
put(R, "A1", "Penawaran: Sistem Hitung Karton per Palet di Loading Dock (8 Kamera)", bold=True, size=14)
put(R, "A2", "Kepada: PT [nama perusahaan], Gudang Minyakita  ·  Tanggal: [isi tanggal]  ·  Berlaku 14 hari sejak tanggal penawaran",
    italic=True, color="595959")
header(R, 4, ["", "Opsi A: Beli putus", "Opsi B: Tahun ke-1", f"Opsi B: Tahun ke-2 s.d. {YEARS} (per tahun)"])
put(R, "A5", "Total harga (tanpa PPN)", bold=True, fill=TOTAL)
for col, f in zip("BCD", (f"='Rincian Opsi A'!G{tot_a}", f"='Rincian Opsi B'!{year_rows[0]}", f"='Rincian Opsi B'!{year_rows[1]}")):
    put(R, f"{col}5", f, fmt=RP, right=True, bold=True, fill=TOTAL)
r = 6
put(R, f"A{r}", "Pemilik perangkat", bold=True)
put(R, f"B{r}", "Perusahaan", right=True)
put(R, f"C{r}", "Penyedia", right=True)
put(R, f"D{r}", "Penyedia", right=True)
r += 1
put(R, f"A{r}", "Layanan support dan maintenance", bold=True)
put(R, f"B{r}", f"{warranty} bulan termasuk", right=True)
put(R, f"C{r}", "12 bulan termasuk", right=True)
put(R, f"D{r}", "12 bulan termasuk", right=True)
r += 1
put(R, f"A{r}", "Penggantian perangkat rusak (pemakaian normal)", bold=True)
put(R, f"B{r}", "Garansi pabrik", right=True)
put(R, f"C{r}", "Ditanggung penyedia", right=True)
put(R, f"D{r}", "Ditanggung penyedia", right=True)
r += 1
put(R, f"A{r}", "Maintenance setelah masa garansi (Opsi A, opsional, per tahun)", bold=True)
put(R, f"B{r}", maint_a, fmt=RP, right=True)
put(R, f"C{r}", "termasuk", right=True)
put(R, f"D{r}", "termasuk", right=True)
r += 1
put(R, f"A{r}", f"Total selama {YEARS} tahun", bold=True)
put(R, f"B{r}", f"=B5+B{r - 1}*{YEARS - 1}", fmt=RP, right=True)
put(R, f"C{r}", f"='Rincian Opsi B'!G{tot_bk}", fmt=RP, right=True)
R.merge_cells(f"C{r}:D{r}")
r += 1
put(R, f"A{r}", "(Opsi A dihitung dengan maintenance opsional mulai tahun ke-2)", italic=True, color="595959")
r += 2
band(R, r, "Termin pembayaran", 4)
r = bullets(R, r + 1, [
    "Opsi A: DP 50% saat PO, 30% setelah instalasi selesai, 20% setelah uji paralel dan serah terima.",
    "Opsi B: saat PO dibayar 50% jasa sekali bayar (aplikasi dan infrastruktur) serta langganan tahun ke-1; sisa 50% jasa saat sistem mulai dipakai (go-live). "
    "Periode langganan dihitung sejak go-live; tahun berikutnya dibayar di muka di awal tiap periode 12 bulan.",
], 4)
r += 1
band(R, r, "Yang didapatkan", 4)
r = bullets(R, r + 1, [
    "Hitung karton setiap palet (standar 60 karton) di zona cek depan dock, dan peringatan langsung bila palet kurang.",
    "Video analytics realtime 8 kamera pada 20-30 fps, diproses di PC server AI dengan GPU NVIDIA RTX 5070 Ti 16 GB di lokasi.",
    "Rekonsiliasi jumlah karton per DO, per truk, dan per palet sebelum barang naik ke armada ekspedisi.",
    "Web app on-premise, dibuka dari laptop tim gudang lewat jaringan/VPN perusahaan (tanpa install aplikasi), plus TV status di loading dock; laporan per DO, truk, dan palet.",
    "Event trigger otomatis (palet kurang, selisih DO, kamera mati) tercatat di web app beserta foto dan klip bukti yang disimpan di PC server.",
    "Owner dapat live monitoring 8 kamera serta melihat riwayat event dan laporan dari luar gudang melalui Tailscale (koneksi terenkripsi langsung ke server).",
    "Rekaman 8 kamera sebagai bukti audit dan penyelesaian selisih.",
    "Seluruh sistem berjalan di lokasi (on-premise): rekaman video, event, dan data tersimpan di PC server gudang, tanpa penyimpanan cloud.",
], 4)
r += 1
band(R, r, "Jadwal", 4)
r = bullets(R, r + 1, [
    "Total sekitar 16 minggu (4 bulan) sejak PO.",
    "Minggu 1-2: survey dock, desain posisi kamera dan zona cek palet, pengadaan perangkat.",
    "Minggu 3-4: instalasi kamera, jaringan, dan server; pengambilan data dari CCTV dock dimulai.",
    "Minggu 5-10: pelabelan data, training dan tuning model, logika hitung karton dan rekonsiliasi DO; pembuatan web app berjalan paralel.",
    "Minggu 11-13: optimasi realtime 8 kamera, integrasi data DO, kalibrasi zona cek.",
    "Minggu 14-15: uji paralel 2 minggu dibanding hitung manual, termasuk uji performa 8 kamera 20-30 fps.",
    "Minggu 16: training pengguna, SOP, dan serah terima (go-live).",
], 4)
r += 1
band(R, r, "Garansi dan layanan", 4)
r = bullets(R, r + 1, [
    "Opsi A: perangkat bergaransi resmi pabrikan; layanan " + str(warranty) + " bulan setelah serah terima.",
    "Opsi B: selama kontrak, layanan support, maintenance, dan penggantian perangkat rusak karena pemakaian normal ditanggung penyedia.",
], 4)
r += 1
band(R, r, "Yang disiapkan perusahaan", 4)
r = bullets(R, r + 1, [
    "Listrik di titik kamera dan ruang server, alat kerja ketinggian (forklift dengan man basket atau sejenisnya) saat pemasangan.",
    "Laptop untuk memantau dashboard, serta 1 alamat IP dan port LAN di jaringan perusahaan untuk server dan TV dock (akses dari luar gudang lewat VPN perusahaan yang sudah ada).",
    "Koneksi internet di server untuk akses jarak jauh owner, serta akun Tailscale atas nama owner (biaya langganan Tailscale, bila ada, ditanggung perusahaan).",
    "Data DO (ekspor file atau akses API WMS/ERP) dan satu PIC gudang untuk koordinasi dan uji paralel.",
    "SOP: palet berhenti sejenak di zona cek, plastik wrap bening agar karton terlihat kamera.",
], 4)
r += 1
band(R, r, "Ketentuan dan pengamanan", 4)
r = bullets(R, r + 1, [
    f"Opsi B: kontrak minimum {term} bulan. Bila dihentikan lebih awal, perusahaan membayar biaya pemutusan sebesar sisa sewa perangkat "
    "sampai akhir kontrak minimum (rincian di sheet Rincian Opsi B), atau membeli perangkat dengan nilai yang sama.",
    "Opsi B: jasa sekali bayar dan langganan yang sudah dibayar tidak dapat dikembalikan.",
    f"Opsi B: perangkat, aplikasi AI, dan web app tetap milik penyedia; perusahaan mendapat hak pakai selama langganan aktif. "
    "Data operasional milik perusahaan dan dapat diekspor kapan saja.",
    f"Opsi B: keterlambatan pembayaran lebih dari {late} hari, layanan support dan pembaruan dihentikan sementara sampai pembayaran diterima.",
    "Opsi B: perangkat tidak boleh dipindahkan, dibongkar, atau diubah tanpa persetujuan tertulis penyedia. Setelah kontrak minimum, "
    "langganan dapat diperpanjang dengan harga yang disepakati ulang, atau perangkat ditarik oleh penyedia.",
    "Opsi A: hak milik perangkat dan hak pakai aplikasi AI serta web app (1 lokasi, 8 kamera) berpindah ke perusahaan setelah pembayaran lunas. "
    "Kode sumber aplikasi tidak termasuk.",
    "Kedua opsi: kerusakan karena kelalaian, salah pakai, benturan forklift atau alat angkut, bencana alam, banjir, kebakaran, petir, "
    "tegangan listrik tidak stabil, atau perubahan instalasi oleh pihak lain ditanggung perusahaan sesuai harga perangkat dan jasa saat itu.",
    "Kedua opsi: perusahaan memberikan akses lokasi untuk pemasangan dan kunjungan maintenance terjadwal.",
], 4, 30)
r += 1
band(R, r, "Penambahan atau perubahan fitur (change request)", 4)
r = bullets(R, r + 1, [
    "Garansi dan langganan support mencakup perbaikan bug dan penyesuaian konfigurasi pada fitur yang tercantum di penawaran ini. "
    "Fitur baru atau perubahan alur di luar lingkup tersebut diperlakukan sebagai change request dan ditagih terpisah.",
    "Prosedur: perusahaan mengajukan permintaan tertulis; dalam 5 hari kerja penyedia menyampaikan lingkup, estimasi hari kerja, biaya, "
    "dan dampak jadwal; pekerjaan dimulai setelah persetujuan tertulis (PO atau adendum).",
    f"Tarif: software (AI computer vision dan web app) Rp {cr_sw:,.0f} per hari kerja; infrastruktur Rp {cr_inf:,.0f} per hari kerja; "
    "minimal 1 hari kerja per permintaan. Perangkat atau material tambahan ditagih sesuai harga saat itu.".replace(",", "."),
    "Pembayaran change request: 50% saat persetujuan, 50% setelah fitur diserahkan dan diuji bersama. Tarif berlaku selama masa kontrak "
    "atau 12 bulan sejak serah terima (Opsi A); setelahnya dapat disesuaikan.",
    "Opsi B: fitur hasil change request menjadi bagian sistem yang dirawat dalam langganan tanpa tambahan biaya support.",
], 4, 30)
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
