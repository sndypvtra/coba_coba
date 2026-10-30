"""Budget workbook: Minyakita pallet box counting at the loading dock, 8 cameras, 3 commercial scenarios.

    python build_budget.py   # -> Budget_Minyakita_Pallet_Counting.xlsx (then recalc with LibreOffice)
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().parent / "Budget_Minyakita_Pallet_Counting.xlsx"
F = "Arial"
BLUE, GREEN, BLACK = "0000FF", "008000", "000000"
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


def sheet(name, widths):
    ws = wb.create_sheet(name)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_view.showGridLines = False
    return ws


def put(ws, ref, value, color=BLACK, bold=False, fmt=None, fill=None, wrap=False, size=10, italic=False):
    c = ws[ref]
    c.value = value
    c.font = Font(name=F, size=size, bold=bold, color=color, italic=italic)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    c.alignment = Alignment(vertical="top", wrap_text=wrap)
    return c


def title(ws, text, sub):
    put(ws, "A1", text, bold=True, size=14)
    put(ws, "A2", sub, italic=True, color="595959")


def header(ws, row, labels):
    for i, lab in enumerate(labels, 1):
        c = put(ws, f"{get_column_letter(i)}{row}", lab, color="FFFFFF", bold=True, fill=HEAD, wrap=True)
        c.border = BOX


def section(ws, row, text, ncols):
    for i in range(1, ncols + 1):
        ws[f"{get_column_letter(i)}{row}"].fill = SUB
    put(ws, f"A{row}", text, bold=True, fill=SUB)


wb.remove(wb.active)

# ------------------------------------------------------------------ Asumsi
A = sheet("Asumsi", [52, 16, 70])
title(A, "Asumsi & Parameter", "Sel biru berlatar kuning = input yang boleh diubah. Semua angka dalam Rupiah, belum termasuk PPN, kecuali disebut lain.")
header(A, 4, ["Parameter", "Nilai", "Keterangan / sumber"])
ASM = {}
rows = [
    ("Umum", None, None, None),
    ("kurs", "Kurs USD ke IDR", 16500, RP, "Asumsi kurs untuk biaya AWS. Ganti sesuai kurs saat penawaran."),
    ("n", "Masa kontrak B dan C (bulan)", 36, '0', "Masa amortisasi perangkat dan implementasi. Kontrak minimum yang diusulkan."),
    ("rate", "Biaya modal per tahun", 0.12, PCT, "Biaya dana/bunga untuk perangkat yang kita danai di skenario B dan C."),
    ("cont", "Kontinjensi biaya proyek", 0.10, PCT, "Cadangan untuk selisih harga, kabel tambahan, kunjungan ulang."),
    ("Skenario A (klien membeli)", None, None, None),
    ("mk_hw", "Markup hardware", 0.15, PCT, "Margin reseller perangkat; praktik system integrator 10 sampai 20 persen."),
    ("mk_inst", "Markup material dan instalasi", 0.25, PCT, "Margin jasa instalasi dan material."),
    ("m_sw", "Target margin lisensi software dan implementasi", 0.45, PCT, "Harga = biaya / (1 - margin)."),
    ("m_amc", "Target margin kontrak maintenance (AMC)", 0.30, PCT, "Harga AMC per tahun = biaya support A x 12 / (1 - margin)."),
    ("Skenario B (bayar per box) dan C (langganan tahunan)", None, None, None),
    ("m_b", "Target margin skenario B (per box)", 0.45, PCT, "Lebih tinggi dari C karena kita menanggung risiko volume."),
    ("m_c", "Target margin skenario C (langganan)", 0.40, PCT, "Pendapatan tetap dan dibayar di muka per tahun, risiko lebih rendah."),
    ("setup", "Porsi biaya implementasi yang ditagih di depan (setup fee)", 0.50, PCT, "0% = semua diamortisasi ke tagihan bulanan; 100% = semua ditagih di depan."),
    ("mk_setup", "Markup setup fee", 0.20, PCT, "Margin atas porsi implementasi yang ditagih di depan."),
    ("vol", "Volume box terhitung per bulan (skenario B)", 250000, RP, "ASUMSI: 4 dock, 16 truk per hari, 600 karton per truk, 26 hari kerja. Wajib dikonfirmasi data klien."),
    ("ppp", "Box per palet", 60, '0', "Dari klien: 1 palet = 60 kardus."),
    ("floor", "Minimum komitmen B (% dari tagihan normal)", 0.70, PCT, "Lantai tagihan bulanan supaya biaya kita tetap tertutup saat volume turun."),
    ("Pajak (informasi)", None, None, None),
    ("ppn", "PPN efektif", 0.11, PCT, "PPN 12% dengan DPP nilai lain 11/12, efektif 11%. Konfirmasi ke konsultan pajak."),
    ("pph23", "PPh 23 dipotong klien atas jasa dan sewa", 0.02, PCT, "Mengurangi kas yang diterima; bisa dikreditkan di SPT tahunan."),
    ("Tarif internal per hari kerja (biaya kita, termasuk BPJS dan overhead gaji)", None, None, None),
    ("r_pm", "Project Manager", 1000000, RP, "Setara gaji sekitar Rp 21 juta per bulan, 21 hari kerja."),
    ("r_cv", "AI / Computer Vision Engineer", 1200000, RP, "Setara sekitar Rp 25 juta per bulan."),
    ("r_fs", "Fullstack Engineer (web app dan integrasi)", 900000, RP, "Setara sekitar Rp 19 juta per bulan."),
    ("r_fe", "Field Engineer / Teknisi", 600000, RP, "Setara sekitar Rp 12,6 juta per bulan."),
    ("Operasional", None, None, None),
    ("cloud_usd", "Cloud AWS per bulan (USD), skenario B dan C", 45, RP, "1 VM kecil region Jakarta + disk + backup + snapshot S3: dashboard, laporan, data tagihan, monitoring jarak jauh."),
    ("inet", "Internet khusus sistem per bulan, skenario B dan C", 400000, RP, "Paket 4G/broadband untuk akses jarak jauh dan sinkron data. Nol jika memakai internet klien."),
    ("hw_res", "Cadangan penggantian hardware per tahun (% nilai hardware)", 0.10, PCT, "Kamera, HDD, PSU, kipas rusak di lingkungan gudang berdebu. Hanya B dan C."),
    ("ins", "Asuransi perangkat per tahun (% nilai hardware)", 0.005, PCT, "Asuransi all risk perangkat milik kita di lokasi klien. Hanya B dan C."),
    ("trans", "Transport per kunjungan maintenance", 300000, RP, "Wilayah Jabodetabek."),
]
r = 5
for item in rows:
    if item[1] is None:
        section(A, r, item[0], 3)
    else:
        key, lab, val, fmt, note = item
        put(A, f"A{r}", lab)
        put(A, f"B{r}", val, color=BLUE, fmt=fmt, fill=YELLOW)
        put(A, f"C{r}", note, wrap=True, color="404040")
        ASM[key] = f"Asumsi!$B${r}"
    r += 1


def a(key):
    return ASM[key]


# ------------------------------------------------------------------ Hardware
H = sheet("Hardware", [5, 34, 58, 7, 16, 16, 46])
title(H, "Bill of Materials Hardware (8 kamera, 1 lokasi)", "Harga beli kita, estimasi pasar Jabodetabek. Wajib diganti dengan penawaran vendor sebelum penawaran final.")
header(H, 4, ["No", "Item", "Spesifikasi", "Qty", "Harga satuan (Rp)", "Total (Rp)", "Catatan"])
hw = [
    ("IP Camera 8MP (4K) fixed lens", "Hikvision/Dahua kelas pro, H.265, WDR 120dB, IR 40 m, IP67", 8, 1800000, "Resolusi tinggi untuk menghitung karton dan lapisan palet."),
    ("Bracket, pole mount, junction box", "Bracket dinding/plafon, junction box tahan air", 8, 250000, "Kamera top-down dipasang di ketinggian 5 sampai 7 m."),
    ("NVR 8 kanal PoE 4K", "8 port PoE, dukung H.265, 2 bay HDD", 1, 4500000, "Rekaman bukti untuk audit dan sengketa."),
    ("HDD surveillance 8 TB", "WD Purple / Seagate SkyHawk", 1, 3800000, "Sekitar 14 hari rekaman 8 kamera pada 2 sampai 3 Mbps."),
    ("PoE switch gigabit 8 port (managed)", "Untuk cluster kamera di area dock", 1, 2000000, "Jika jarak kamera ke NVR lebih dari 90 m."),
    ("Edge AI server (workstation)", "CPU 8 core, RAM 32 GB, NVMe 1 TB + SSD 2 TB, GPU NVIDIA RTX 16 GB, PSU 750W Gold", 1, 28000000, "Menjalankan deteksi, tracking, hitung karton 8 kamera secara realtime di lokasi."),
    ("UPS online 2 kVA", "Untuk server, NVR, switch, router", 1, 7500000, "Melindungi dari listrik padam dan naik-turun."),
    ("Rack wallmount 12U + PDU", "Dengan kipas dan kunci", 1, 3000000, "Tempat server dan perangkat jaringan."),
    ("Router VPN (MikroTik)", "RouterOS v7, WireGuard", 1, 1500000, "Akses jarak jauh aman untuk support dan sinkron cloud."),
    ("Layar dashboard di dock", "TV 43 inch + bracket", 1, 4500000, "Status palet dan selisih per DO di area muat."),
    ("Tablet checker", "Android 10 inch", 2, 3500000, "Checker memilih/scan DO sebelum muat."),
]
r = 5
for i, (it, spec, q, p, note) in enumerate(hw, 1):
    put(H, f"A{r}", i)
    put(H, f"B{r}", it)
    put(H, f"C{r}", spec, wrap=True)
    put(H, f"D{r}", q, color=BLUE, fmt="0")
    put(H, f"E{r}", p, color=BLUE, fmt=RP)
    put(H, f"F{r}", f"=D{r}*E{r}", fmt=RP)
    put(H, f"G{r}", note, wrap=True, color="404040")
    r += 1
HW_FIRST, HW_LAST = 5, r - 1
put(H, f"B{r}", "Total hardware", bold=True, fill=TOTAL)
put(H, f"F{r}", f"=SUM(F{HW_FIRST}:F{HW_LAST})", bold=True, fmt=RP, fill=TOTAL)
HW_TOTAL = f"Hardware!$F${r}"

# ------------------------------------------------------------------ Instalasi
I = sheet("Instalasi", [5, 40, 46, 9, 16, 16, 46])
title(I, "Material dan Instalasi", "Biaya kita. Tenaga teknisi internal memakai tarif di sheet Asumsi.")
header(I, 4, ["No", "Item", "Keterangan", "Qty", "Harga satuan (Rp)", "Total (Rp)", "Catatan"])
inst = [
    ("Kabel UTP Cat6 outdoor 305 m", "Sekitar 60 sampai 70 m per kamera", 2, 2300000, None, "roll"),
    ("Pipa conduit, klem, cable tray, konektor", "Lumpsum", 1, 3000000, None, ""),
    ("Kelistrikan rack server", "Stop kontak, MCB, grounding", 1, 1500000, None, ""),
    ("Jasa pasang kamera dan tarik kabel", "Per titik kamera, pekerjaan di ketinggian", 8, 600000, None, ""),
    ("Sewa scissor lift", "Per hari", 2, 1500000, None, ""),
    ("Setting rack, server, jaringan, NVR", "Hari kerja field engineer", 2, None, "r_fe", ""),
    ("Transport dan konsumsi tim instalasi", "Lumpsum", 1, 2000000, None, ""),
]
r = 5
for i, (it, ket, q, p, rate_key, _u) in enumerate(inst, 1):
    put(I, f"A{r}", i)
    put(I, f"B{r}", it)
    put(I, f"C{r}", ket, wrap=True)
    put(I, f"D{r}", q, color=BLUE, fmt="0")
    if rate_key:
        put(I, f"E{r}", f"={a(rate_key)}", color=GREEN, fmt=RP)
    else:
        put(I, f"E{r}", p, color=BLUE, fmt=RP)
    put(I, f"F{r}", f"=D{r}*E{r}", fmt=RP)
    r += 1
put(I, f"B{r}", "Total material dan instalasi", bold=True, fill=TOTAL)
put(I, f"F{r}", f"=SUM(F5:F{r - 1})", bold=True, fmt=RP, fill=TOTAL)
INST_TOTAL = f"Instalasi!$F${r}"

# ------------------------------------------------------------------ Implementasi
M = sheet("Implementasi", [5, 52, 9, 9, 9, 9, 16, 44])
title(M, "Implementasi Software (khusus lokasi ini)", "Hari kerja (man-day) per peran x tarif internal. Platform inti diambil dari project warehouse sebelumnya.")
header(M, 4, ["No", "Aktivitas", "PM", "AI/CV", "Fullstack", "Field Eng", "Biaya (Rp)", "Keluaran"])
acts = [
    ("Site survey, layout dock, desain posisi kamera", 1, 1, 0, 1, "Gambar posisi kamera, zona cek palet per dock"),
    ("Pengambilan data dan pelabelan gambar karton dan palet", 0, 4, 0, 1, "Dataset sekitar 3.000 gambar dari CCTV lokasi"),
    ("Training dan tuning model (karton, palet, lapisan, orang, forklift)", 0, 10, 0, 0, "Model deteksi khusus kemasan Minyakita"),
    ("Logika hitung palet (lapisan x pola) dan rekonsiliasi per DO", 0, 8, 3, 0, "Status palet lengkap / kurang, selisih per DO"),
    ("Kustomisasi web app: dashboard, laporan per DO/truk/palet, alert", 0, 0, 10, 0, "Dashboard dock dan manajemen"),
    ("Integrasi data DO dari WMS/ERP (API atau file CSV)", 0, 0, 6, 0, "DO otomatis tersedia di tablet checker"),
    ("Deploy edge server dan kalibrasi 8 kamera", 0, 3, 0, 3, "Sistem berjalan di lokasi"),
    ("UAT: uji paralel 2 minggu vs hitung manual", 2, 5, 0, 5, "Laporan akurasi, sign-off klien"),
    ("Training user, SOP, serah terima", 2, 0, 0, 1, "SOP checker dan supervisor"),
    ("Manajemen proyek", 6, 0, 0, 0, "Rapat mingguan, laporan progres"),
]
r = 5
for i, (act, pm, cv, fs, fe, outp) in enumerate(acts, 1):
    put(M, f"A{r}", i)
    put(M, f"B{r}", act, wrap=True)
    for col, v in zip("CDEF", (pm, cv, fs, fe)):
        put(M, f"{col}{r}", v, color=BLUE, fmt="0")
    put(M, f"G{r}", f"=C{r}*{a('r_pm')}+D{r}*{a('r_cv')}+E{r}*{a('r_fs')}+F{r}*{a('r_fe')}", fmt=RP)
    put(M, f"H{r}", outp, wrap=True, color="404040")
    r += 1
last_act = r - 1
put(M, f"B{r}", "Subtotal hari kerja", bold=True, fill=TOTAL)
for col in "CDEFG":
    put(M, f"{col}{r}", f"=SUM({col}5:{col}{last_act})", bold=True, fmt=RP if col == "G" else "0", fill=TOTAL)
sub_row = r
r += 1
extras = [
    ("Outsourcing pelabelan gambar (3.000 gambar x Rp 1.500)", 4500000, "Bisa dikerjakan internal jika ada tenaga."),
    ("Perjalanan dan akomodasi tim selama implementasi", 3000000, "Lumpsum."),
    ("Alokasi biaya pengembangan platform (dibagi ke beberapa klien)", 30000000,
     "Platform video analytics dan web app dari project warehouse sebelumnya, perlu dibuat versi produksi (streaming). Asumsi biaya platform Rp 180 juta dibagi 6 klien."),
]
for lab, val, note in extras:
    put(M, f"B{r}", lab, wrap=True)
    put(M, f"G{r}", val, color=BLUE, fmt=RP)
    put(M, f"H{r}", note, wrap=True, color="404040")
    r += 1
put(M, f"B{r}", "Total implementasi", bold=True, fill=TOTAL)
put(M, f"G{r}", f"=SUM(G{sub_row}:G{r - 1})", bold=True, fmt=RP, fill=TOTAL)
IMPL_TOTAL = f"Implementasi!$G${r}"
r += 2
put(M, f"B{r}", "Durasi implementasi yang diusulkan: 8 sampai 10 minggu (survey, data, model, instalasi, UAT 2 minggu).", italic=True, color="595959")

# ------------------------------------------------------------------ Biaya Bulanan
O = sheet("Biaya Bulanan", [5, 46, 40, 15, 9, 9, 15, 15])
title(O, "Biaya Operasional Bulanan (biaya kita)", "Skenario A = kontrak maintenance (klien punya perangkat). Skenario B dan C = layanan penuh (kita punya perangkat dan bertanggung jawab atas uptime).")
header(O, 4, ["No", "Item", "Dasar perhitungan", "Biaya satuan (Rp)", "Qty A", "Qty B/C", "Biaya A per bulan", "Biaya B/C per bulan"])
opex = [
    ("Cloud AWS (dashboard, laporan, data tagihan)", "USD per bulan x kurs", f"={a('cloud_usd')}*{a('kurs')}", 0, 1),
    ("Internet khusus sistem", "Paket bulanan", f"={a('inet')}", 0, 1),
    ("Monitoring jarak jauh dan support AI", "Hari kerja AI/CV engineer per bulan", f"={a('r_cv')}", 0.5, 1),
    ("Support lapangan dan helpdesk", "Hari kerja field engineer per bulan", f"={a('r_fe')}", 0.5, 1),
    ("Update dan retraining model", "Hari kerja AI/CV engineer per bulan (rata-rata)", f"={a('r_cv')}", 0.33, 1),
    ("Preventive maintenance per kuartal (bersih lensa, cek perangkat)", "(1 hari field engineer + transport) / 3", f"=({a('r_fe')}+{a('trans')})/3", 1, 1),
    ("Account management, laporan bulanan, rekonsiliasi tagihan", "Hari kerja PM per bulan", f"={a('r_pm')}", 0.25, 0.5),
    ("Cadangan penggantian hardware", "Nilai hardware x persen per tahun / 12", f"={HW_TOTAL}*{a('hw_res')}/12", 0, 1),
    ("Asuransi perangkat", "Nilai hardware x persen per tahun / 12", f"={HW_TOTAL}*{a('ins')}/12", 0, 1),
    ("Listrik server dan kamera (sekitar 250 kWh per bulan)", "Ditanggung klien di semua skenario", 0, 0, 0),
]
r = 5
for i, (lab, basis, unit, qa, qb) in enumerate(opex, 1):
    put(O, f"A{r}", i)
    put(O, f"B{r}", lab, wrap=True)
    put(O, f"C{r}", basis, wrap=True, color="404040")
    put(O, f"D{r}", unit, color=GREEN if isinstance(unit, str) else BLUE, fmt=RP)
    put(O, f"E{r}", qa, color=BLUE, fmt="0.00")
    put(O, f"F{r}", qb, color=BLUE, fmt="0.00")
    put(O, f"G{r}", f"=D{r}*E{r}", fmt=RP)
    put(O, f"H{r}", f"=D{r}*F{r}", fmt=RP)
    r += 1
put(O, f"B{r}", "Total biaya operasional per bulan", bold=True, fill=TOTAL)
put(O, f"G{r}", f"=SUM(G5:G{r - 1})", bold=True, fmt=RP, fill=TOTAL)
put(O, f"H{r}", f"=SUM(H5:H{r - 1})", bold=True, fmt=RP, fill=TOTAL)
OPEX_A = f"'Biaya Bulanan'!$G${r}"
OPEX_BC = f"'Biaya Bulanan'!$H${r}"


# ------------------------------------------------------------------ helpers for scenario sheets
def line(ws, row, label, formula, fmt=RP, bold=False, fill=None, note=None, color=BLACK):
    put(ws, f"A{row}", label, bold=bold, fill=fill, wrap=True)
    put(ws, f"B{row}", formula, fmt=fmt, bold=bold, fill=fill, color=color)
    if note:
        put(ws, f"C{row}", note, wrap=True, color="404040")


# ------------------------------------------------------------------ Skenario A
SA = sheet("Skenario A", [58, 18, 70])
title(SA, "Skenario A: Klien membeli server dan perangkat (proyek + kontrak maintenance)", "Perangkat menjadi milik klien. Kita mendapat laba di depan dari proyek, lalu laba bulanan dari kontrak maintenance (AMC).")
section(SA, 4, "1. Biaya kita (sekali di depan)", 3)
line(SA, 5, "Hardware", f"={HW_TOTAL}", color=GREEN)
line(SA, 6, "Material dan instalasi", f"={INST_TOTAL}", color=GREEN)
line(SA, 7, "Implementasi software", f"={IMPL_TOTAL}", color=GREEN)
line(SA, 8, "Kontinjensi", f"=SUM(B5:B7)*{a('cont')}")
line(SA, 9, "Total biaya kita", "=SUM(B5:B8)", bold=True, fill=TOTAL)
section(SA, 11, "2. Harga ke klien (sekali di depan)", 3)
line(SA, 12, "Hardware (termasuk garansi vendor)", f"=B5*(1+{a('mk_hw')})")
line(SA, 13, "Material dan instalasi", f"=B6*(1+{a('mk_inst')})")
line(SA, 14, "Lisensi software perpetual (8 kanal) dan implementasi", f"=ROUNDUP(B7*(1+{a('cont')})/(1-{a('m_sw')}),-6)",
     note="Termasuk web app, model AI khusus kemasan, integrasi DO, UAT, training, garansi software 3 bulan.")
line(SA, 15, "Total harga proyek (sebelum PPN)", "=SUM(B12:B14)", bold=True, fill=TOTAL)
line(SA, 16, "PPN", f"=B15*{a('ppn')}")
line(SA, 17, "Total tagihan proyek (termasuk PPN)", "=B15+B16", bold=True)
section(SA, 19, "3. Laba proyek (sekali)", 3)
line(SA, 20, "Laba kotor proyek", "=B15-B9", bold=True)
line(SA, 21, "Margin proyek", "=IF(B15=0,0,B20/B15)", fmt=PCT)
section(SA, 23, "4. Kontrak maintenance tahunan (AMC), mulai bulan ke-4", 3)
line(SA, 24, "Biaya support kita per bulan", f"={OPEX_A}", color=GREEN, note="Monitoring jarak jauh, support, update model, preventive maintenance per kuartal.")
line(SA, 25, "Harga AMC per tahun", f"=ROUNDUP(B24*12/(1-{a('m_amc')}),-6)", bold=True)
line(SA, 26, "Setara per bulan", "=B25/12")
line(SA, 27, "AMC sebagai persen dari harga software", "=IF(B14=0,0,B25/B14)", fmt=PCT, note="Praktik umum 15 sampai 22 persen per tahun.")
line(SA, 28, "Laba AMC per bulan", "=B26-B24", bold=True)
section(SA, 30, "5. Gambaran laba per bulan", 3)
line(SA, 31, "Laba proyek dibagi masa 36 bulan", f"=B20/{a('n')}")
line(SA, 32, "Laba per bulan setara (proyek dibagi 36 bulan + AMC)", "=B31+B28", bold=True, fill=TOTAL)
line(SA, 33, "Total laba 36 bulan (proyek + AMC 33 bulan)", f"=B20+B28*({a('n')}-3)", bold=True)
line(SA, 34, "Total yang dibayar klien 36 bulan (sebelum PPN)", f"=B15+B26*({a('n')}-3)")

# ------------------------------------------------------------------ shared B/C investment block
def invest_block(ws, start):
    r = start
    section(ws, r, "1. Investasi kita (perangkat milik kita, dipasang di lokasi klien)", 3)
    line(ws, r + 1, "Hardware + material dan instalasi (termasuk kontinjensi)", f"=({HW_TOTAL}+{INST_TOTAL})*(1+{a('cont')})", color=GREEN)
    line(ws, r + 2, "Implementasi software (termasuk kontinjensi)", f"={IMPL_TOTAL}*(1+{a('cont')})", color=GREEN)
    line(ws, r + 3, "Total investasi di depan", f"=B{r + 1}+B{r + 2}", bold=True, fill=TOTAL)
    line(ws, r + 4, "Setup fee ditagih ke klien di depan", f"=ROUNDUP(B{r + 2}*{a('setup')}*(1+{a('mk_setup')}),-6)",
         note="Porsi implementasi yang ditagih di depan, diatur di sheet Asumsi.")
    line(ws, r + 5, "Laba dari setup fee", f"=B{r + 4}-B{r + 2}*{a('setup')}")
    line(ws, r + 6, "Nilai yang dipulihkan lewat tagihan bulanan", f"=B{r + 1}+B{r + 2}*(1-{a('setup')})")
    line(ws, r + 7, "Pengembalian modal + bunga per bulan (cicilan)", f"=PMT({a('rate')}/12,{a('n')},-B{r + 6})",
         note="Anuitas selama masa kontrak dengan biaya modal di sheet Asumsi.")
    line(ws, r + 8, "Biaya operasional per bulan", f"={OPEX_BC}", color=GREEN)
    line(ws, r + 9, "Total biaya per bulan (titik impas)", f"=B{r + 7}+B{r + 8}", bold=True, fill=TOTAL)
    return {"inv": f"B{r + 3}", "setup": f"B{r + 4}", "setup_profit": f"B{r + 5}", "pmt": f"B{r + 7}",
            "opex": f"B{r + 8}", "cost": f"B{r + 9}", "next": r + 11}


# ------------------------------------------------------------------ Skenario B
SB = sheet("Skenario B", [58, 18, 70])
title(SB, "Skenario B: Infrastruktur dari kita, klien bayar per box yang terhitung", "Server, CCTV, dan instalasi milik kita. Tagihan bulanan = jumlah box terhitung x harga per box, dengan minimum komitmen bulanan.")
b = invest_block(SB, 4)
r = b["next"]
section(SB, r, "2. Harga", 3)
line(SB, r + 1, "Target pendapatan per bulan", f"={b['cost']}/(1-{a('m_b')})")
line(SB, r + 2, "Volume box per bulan (asumsi)", f"={a('vol')}", fmt=RP, color=GREEN)
line(SB, r + 3, "Harga per box", f"=ROUNDUP(B{r + 1}/B{r + 2},0)", bold=True, fill=TOTAL, note="Dibulatkan ke atas ke rupiah terdekat.")
line(SB, r + 4, "Setara harga per palet", f"=B{r + 3}*{a('ppp')}", note="Alternatif penagihan per palet terverifikasi, lebih mudah diaudit.")
line(SB, r + 5, "Minimum komitmen per bulan", f"=ROUNDUP(MAX({b['cost']},B{r + 3}*B{r + 2}*{a('floor')}),-5)", bold=True,
     note="Tagihan tidak pernah di bawah angka ini, sehingga biaya kita selalu tertutup.")
section(SB, r + 7, "3. Laba per bulan pada volume asumsi", 3)
line(SB, r + 8, "Tagihan per bulan", f"=MAX(B{r + 3}*B{r + 2},B{r + 5})", bold=True)
line(SB, r + 9, "Biaya per bulan", f"={b['cost']}")
line(SB, r + 10, "Laba per bulan", f"=B{r + 8}-B{r + 9}", bold=True, fill=TOTAL)
line(SB, r + 11, "Margin", f"=IF(B{r + 8}=0,0,B{r + 10}/B{r + 8})", fmt=PCT)
line(SB, r + 12, "Volume impas (box per bulan)", f"=ROUNDUP({b['cost']}/B{r + 3},0)", fmt=RP)
line(SB, r + 13, "Payback investasi bersih (bulan)", f"=IF(B{r + 8}-{b['opex']}<=0,0,({b['inv']}-{b['setup']})/(B{r + 8}-{b['opex']}))", fmt=NUM,
     note="(Investasi - setup fee) / (tagihan - biaya operasional).")
line(SB, r + 14, "Total laba 36 bulan (setup + bulanan)", f"={b['setup_profit']}+B{r + 10}*{a('n')}", bold=True)
line(SB, r + 15, "Total yang dibayar klien 36 bulan (sebelum PPN)", f"={b['setup']}+B{r + 8}*{a('n')}")
line(SB, r + 16, "Laba per bulan jika kontrak diperpanjang (tahun ke-4)", f"=B{r + 8}-{b['opex']}",
     note="Perangkat sudah lunas, biaya tinggal operasional.")
B_ROWS = {"price": f"B{r + 3}", "pallet": f"B{r + 4}", "min": f"B{r + 5}", "bill": f"B{r + 8}", "profit": f"B{r + 10}",
          "payback": f"B{r + 13}", "tot": f"B{r + 14}", "client": f"B{r + 15}", "y4": f"B{r + 16}", "be": f"B{r + 12}"}
r += 18
section(SB, r, "4. Sensitivitas volume (harga per box tetap)", 3)
r += 1
for i, lab in enumerate(["Volume box per bulan", "Tagihan per bulan", "Laba per bulan"]):
    put(SB, f"{'ABC'[i]}{r}", lab, bold=True, color="FFFFFF", fill=HEAD)
r += 1
for v in (100000, 150000, 200000, 250000, 300000, 400000):
    put(SB, f"A{r}", v, color=BLUE, fmt=RP)
    put(SB, f"B{r}", f"=MAX(A{r}*{B_ROWS['price']},{B_ROWS['min']})", fmt=RP)
    put(SB, f"C{r}", f"=B{r}-{b['cost']}", fmt=RP)
    r += 1
put(SB, f"A{r}", "Di bawah volume impas, tagihan ditahan oleh minimum komitmen.", italic=True, color="595959")

# ------------------------------------------------------------------ Skenario C
SC = sheet("Skenario C", [58, 18, 70])
title(SC, "Skenario C: Infrastruktur dari kita, klien berlangganan per tahun", "Server, CCTV, dan instalasi milik kita. Klien membayar langganan tahunan di muka, kontrak 3 tahun.")
c = invest_block(SC, 4)
r = c["next"]
section(SC, r, "2. Harga", 3)
line(SC, r + 1, "Target pendapatan per bulan", f"={c['cost']}/(1-{a('m_c')})")
line(SC, r + 2, "Langganan per tahun (dibayar di muka)", f"=ROUNDUP(B{r + 1}*12,-6)", bold=True, fill=TOTAL)
line(SC, r + 3, "Setara per bulan", f"=B{r + 2}/12")
section(SC, r + 5, "3. Laba", 3)
line(SC, r + 6, "Biaya per bulan", f"={c['cost']}")
line(SC, r + 7, "Laba per bulan", f"=B{r + 3}-B{r + 6}", bold=True, fill=TOTAL)
line(SC, r + 8, "Margin", f"=IF(B{r + 3}=0,0,B{r + 7}/B{r + 3})", fmt=PCT)
line(SC, r + 9, "Payback investasi bersih (bulan)", f"=IF(B{r + 3}-{c['opex']}<=0,0,({c['inv']}-{c['setup']})/(B{r + 3}-{c['opex']}))", fmt=NUM,
     note="Karena langganan dibayar di muka per tahun, kas tahun pertama sudah masuk di bulan pertama.")
line(SC, r + 10, "Total laba 36 bulan (setup + bulanan)", f"={c['setup_profit']}+B{r + 7}*{a('n')}", bold=True)
line(SC, r + 11, "Total yang dibayar klien 36 bulan (sebelum PPN)", f"={c['setup']}+B{r + 2}*{a('n')}/12")
line(SC, r + 12, "Laba per bulan jika kontrak diperpanjang (tahun ke-4)", f"=B{r + 3}-{c['opex']}",
     note="Perangkat sudah lunas, biaya tinggal operasional.")
C_ROWS = {"year": f"B{r + 2}", "month": f"B{r + 3}", "profit": f"B{r + 7}", "payback": f"B{r + 9}", "tot": f"B{r + 10}",
          "client": f"B{r + 11}", "y4": f"B{r + 12}"}

# ------------------------------------------------------------------ Ringkasan
R = sheet("Ringkasan", [50, 22, 22, 22])
title(R, "Ringkasan 3 Skenario: Penghitungan Box per Palet di Loading Dock (8 kamera)", "Semua angka sebelum PPN. Ubah input di sheet Asumsi, Hardware, Instalasi, Implementasi, Biaya Bulanan.")
header(R, 4, ["", "A. Klien beli perangkat", "B. Bayar per box", "C. Langganan tahunan"])
summary = [
    ("Pemilik perangkat", '="Klien"', '="Kita"', '="Kita"', None),
    ("Investasi kita di depan", "='Skenario A'!B9", f"='Skenario B'!{b['inv']}", f"='Skenario C'!{c['inv']}", RP),
    ("Tagihan di depan ke klien", "='Skenario A'!B15", f"='Skenario B'!{b['setup']}", f"='Skenario C'!{c['setup']}", RP),
    ("Tagihan berulang ke klien", "='Skenario A'!B25", f"='Skenario B'!{B_ROWS['bill']}", f"='Skenario C'!{C_ROWS['year']}", RP),
    ("Satuan tagihan berulang", '="per tahun (AMC)"', '="per bulan"', '="per tahun di muka"', None),
    ("Harga per box / per palet", '="-"', f"=TEXT('Skenario B'!{B_ROWS['price']},\"#,##0\")&\" / \"&TEXT('Skenario B'!{B_ROWS['pallet']},\"#,##0\")", '="-"', None),
    ("Minimum komitmen per bulan", '="-"', f"='Skenario B'!{B_ROWS['min']}", '="-"', RP),
    ("Laba di depan (proyek / setup fee)", "='Skenario A'!B20", f"='Skenario B'!{b['setup_profit']}", f"='Skenario C'!{c['setup_profit']}", RP),
    ("Laba berulang per bulan", "='Skenario A'!B28", f"='Skenario B'!{B_ROWS['profit']}", f"='Skenario C'!{C_ROWS['profit']}", RP),
    ("Laba per bulan setara (36 bulan)", "='Skenario A'!B32", f"='Skenario B'!{B_ROWS['tot']}/{a('n')}", f"='Skenario C'!{C_ROWS['tot']}/{a('n')}", RP),
    ("Total laba 36 bulan", "='Skenario A'!B33", f"='Skenario B'!{B_ROWS['tot']}", f"='Skenario C'!{C_ROWS['tot']}", RP),
    ("Payback investasi (bulan)", '="langsung"', f"='Skenario B'!{B_ROWS['payback']}", f"='Skenario C'!{C_ROWS['payback']}", NUM),
    ("Laba per bulan tahun ke-4 (perpanjangan)", "='Skenario A'!B28", f"='Skenario B'!{B_ROWS['y4']}", f"='Skenario C'!{C_ROWS['y4']}", RP),
    ("Total dibayar klien 36 bulan", "='Skenario A'!B34", f"='Skenario B'!{B_ROWS['client']}", f"='Skenario C'!{C_ROWS['client']}", RP),
    ("Risiko utama untuk kita", '="Rendah, tapi laba sekali"', '="Volume turun, sengketa hitungan"', '="Perangkat rusak/hilang"', None),
]
r = 5
for lab, fa, fb, fc, fmt in summary:
    put(R, f"A{r}", lab, bold=True)
    for col, f in zip("BCD", (fa, fb, fc)):
        cc = put(R, f"{col}{r}", f, color=GREEN, fmt=fmt, wrap=True)
        cc.alignment = Alignment(horizontal="right", vertical="top", wrap_text=True)
    r += 1
r += 1
put(R, f"A{r}", "Catatan", bold=True)
notes = [
    "Harga perangkat adalah estimasi pasar; ganti dengan penawaran vendor (minimal 2 vendor) sebelum penawaran final.",
    "Volume skenario B adalah asumsi; minta data jumlah DO, truk, dan karton per bulan dari klien.",
    "Server AI tetap berada di lokasi klien di semua skenario (edge). Mengirim 8 stream ke GPU cloud jauh lebih mahal.",
    "Listrik, ruang rack, titik jaringan, dan data DO disediakan klien di semua skenario.",
    "PPN ditambahkan di invoice. Untuk jasa dan sewa, klien memotong PPh 23 sebesar 2 persen.",
    "Jika model AI memakai Ultralytics YOLO (lisensi AGPL), produk komersial tertutup wajib membeli lisensi enterprise. Alternatif tanpa biaya: model berlisensi Apache 2.0 seperti RT-DETR, D-FINE, atau YOLOX.",
]
for n in notes:
    r += 1
    put(R, f"A{r}", "• " + n, wrap=True, color="404040")
    R.merge_cells(f"A{r}:D{r}")
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
