"""Investor deck mockup for the Minyakita pallet box counting project, 4 cameras.

Reads the 4-camera budget (build_budget.py 4 + recalc first), models the investor's cash flow for two revenue models
(one-off purchase like option A, yearly subscription like option B), and writes:

    deck.html          12 slides at 1600x900, charts and tables drawn as inline SVG/HTML
    data.json          every number the slides and the brief use
    detail_project.md  the project brief and a slide-by-slide script for Claude Design

    python build_investor_deck.py && node render.js   # -> slides/slide-01.png ... slide-12.png
"""
import html
import json
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "Budget_Minyakita_Pallet_Counting_4Kamera.xlsx"
DEV_FEE = 107_000_000          # the developer's agreed take for building the AI and the web app

# ---------------------------------------------------------------- numbers from the budget
wb = load_workbook(SRC, data_only=True)


def by_label(ws, label, col=2):
    for row in ws.iter_rows(values_only=True):
        if row[0] == label:
            return row[col - 1]
    raise KeyError(f"{ws.title}: {label}")


def jasa(label):
    for row in wb["Jasa INKINDO"].iter_rows(values_only=True):
        if row[1] == label:
            return row[7]
    raise KeyError(label)


sa, sb, rab = wb["Skenario A"], wb["Skenario B"], wb["RAB"]
cats = {}
for row in rab.iter_rows(min_row=5, max_col=7, values_only=True):
    if row[0] and row[1] and row[6] is not None and row[0] != "Jasa pasang":
        cats[row[0]] = cats.get(row[0], 0) + row[6]
devices = {
    "Server AI (PC GPU, HDD rekaman 8 TB, HDD backup 12 TB)": cats["Server AI on-prem"],
    "Kamera CCTV dan kabel (4 kamera 4MP)": cats["CCTV & kabel"],
    "Jaringan (router, switch PoE, rak)": cats["Jaringan"],
    "Layar status di loading dock (TV 55 inci)": cats["Layar loading dock"],
    "UPS server dan UPS rak": cats["Kelistrikan"],
    "Cadangan kenaikan harga perangkat (10%)": by_label(sa, "Kontinjensi perangkat"),
    "Jasa pasang kamera (vendor, 4 titik)": by_label(sa, "Jasa pasang kamera (vendor)"),
}
DEVICES = by_label(sa, "Total uang keluar")
assert sum(devices.values()) == DEVICES

sw = {
    "Pembuatan AI computer vision (model hitung karton)": jasa("Nilai jual Pembuatan AI Computer Vision"),
    "Pembuatan web app (dashboard, laporan, event, DO)": jasa("Nilai jual Pembuatan Web App"),
    "Setup dan implementasi AI dan web app di lokasi": jasa("Nilai jual Setup dan Implementasi AI dan Web App"),
    "Garansi software 3 bulan setelah go-live": by_label(sa, "Garansi software AI dan web app"),
}
sw["Insentif penyelesaian proyek"] = DEV_FEE - sum(sw.values())
infra = {
    "Implementasi infrastruktur (survey, instalasi, kalibrasi kamera)": jasa("Subtotal Implementasi Infrastruktur"),
    "Project management (koordinasi 16 minggu)": jasa("Subtotal Manajemen Proyek"),
    "Garansi infrastruktur 3 bulan setelah go-live": by_label(sa, "Garansi infrastruktur"),
}
INFRA_FEE = sum(infra.values())
INVEST = DEVICES + DEV_FEE + INFRA_FEE

PRICE_A = by_label(sa, "Total harga")
SETUP_B = by_label(sb, "Total jasa sekali bayar")
SUB_B = by_label(sb, "Langganan per tahun")
SUP_YEAR = by_label(sb, "Support software AI dan web app 12 bulan") + by_label(sb, "Support infrastruktur 12 bulan")
RESERVE = by_label(wb["Cadangan Penggantian"], "Total cadangan selama kontrak", 8)
TOTAL_B = by_label(sb, "Total selama kontrak minimum")
assert SETUP_B + 3 * SUB_B == TOTAL_B

# ---------------------------------------------------------------- investor cash flow per month (month 0 = PO)
GO_LIVE = 4
flows_a = {0: -INVEST + PRICE_A * 0.5, 1: PRICE_A * 0.3, GO_LIVE: PRICE_A * 0.2}
flows_b = {0: -INVEST + SETUP_B * 0.5 + SUB_B}
flows_b[GO_LIVE] = SETUP_B * 0.5
for m in range(GO_LIVE, GO_LIVE + 36):                 # support paid to the team + replacement reserve, monthly
    flows_b[m] = flows_b.get(m, 0) - SUP_YEAR / 12 - RESERVE / 36
for m in (GO_LIVE + 12, GO_LIVE + 24):                 # yearly subscription, paid in advance
    flows_b[m] += SUB_B


def cumulative(flows, last):
    run, out = 0, []
    for m in range(last + 1):
        run += flows.get(m, 0)
        out.append(round(run))
    return out


cum_a = cumulative(flows_a, GO_LIVE)
cum_b = cumulative(flows_b, GO_LIVE + 35)
cum_b_best = cumulative({m: v + (RESERVE / 36 if GO_LIVE <= m < GO_LIVE + 36 else 0) for m, v in flows_b.items()}, GO_LIVE + 35)
profit_a, profit_b, profit_b_best = cum_a[-1], cum_b[-1], cum_b_best[-1]
peak_a, peak_b = -min(cum_a), -min(cum_b)
payback_b = next(m for m, v in enumerate(cum_b) if v >= 0 and all(x >= 0 for x in cum_b[m:]))
first_cross_b = next(m for m, v in enumerate(cum_b) if v >= 0)

year_rows_b = []
for name, months in [("Saat PO (bulan 0)", [0]), ("Go-live (bulan 4)", []), ("Tahun ke-1 langganan (bulan 4-15)", range(4, 16)),
                     ("Tahun ke-2 langganan (bulan 16-27)", range(16, 28)), ("Tahun ke-3 langganan (bulan 28-39)", range(28, 40))]:
    if name.startswith("Saat PO"):
        cin, cout = SETUP_B * 0.5 + SUB_B, INVEST
    elif name.startswith("Go-live"):
        cin, cout = SETUP_B * 0.5, 0
    else:
        cin = SUB_B if months.start in (16, 28) else 0
        cout = (SUP_YEAR / 12 + RESERVE / 36) * len(months)
    year_rows_b.append([name, cin, cout])
run = 0
for row in year_rows_b:
    run += row[1] - row[2]
    row.append(run)
assert abs(run - profit_b) < 2

data = dict(
    devices=devices, devices_total=DEVICES, sw=sw, dev_fee=DEV_FEE, infra=infra, infra_fee=INFRA_FEE, invest=INVEST,
    price_a=PRICE_A, setup_b=SETUP_B, sub_b=SUB_B, total_b=TOTAL_B, support_year=SUP_YEAR, reserve=RESERVE,
    profit_a=profit_a, profit_b=profit_b, profit_b_best=profit_b_best, peak_a=peak_a, peak_b=peak_b,
    payback_b=payback_b, first_cross_b=first_cross_b, cum_a=cum_a, cum_b=cum_b, cum_b_best=cum_b_best,
    year_rows_b=year_rows_b,
)
(HERE / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- formatting
def rp(v):
    return "Rp " + f"{round(v):,}".replace(",", ".")


def jt(v, d=1):
    s = f"{abs(v) / 1e6:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if v < 0 else "") + f"Rp {s} juta"


def pct(v, d=1):
    return f"{v * 100:.{d}f}%".replace(".", ",")


e = html.escape
INK, MUTED, GRID, AXIS, ACCENT = "#1A1F2B", "#5B6474", "#E3E6EB", "#9AA3B0", "#2563EB"
GOOD, BAD, GREY, SOFT = "#2E9E5B", "#C8473F", "#B8C0CC", "#EEF3FD"


def table(head, rows, widths=None, total=False, num_cols=()):
    cols = "".join(f"<col style='width:{w}'>" for w in widths) if widths else ""
    th = "".join(f"<th class='{'num' if i in num_cols else ''}'>{e(h)}</th>" for i, h in enumerate(head))
    body = ""
    for ri, r in enumerate(rows):
        cls = " class='total'" if total and ri == len(rows) - 1 else ""
        body += f"<tr{cls}>" + "".join(f"<td class='{'num' if i in num_cols else ''}'>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    return f"<table><colgroup>{cols}</colgroup><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def kpi(label, value, note="", accent=False):
    return (f"<div class='kpi{' accent' if accent else ''}'><div class='kpi-label'>{e(label)}</div>"
            f"<div class='kpi-value'>{e(value)}</div><div class='kpi-note'>{e(note)}</div></div>")


# ---------------------------------------------------------------- charts (inline SVG)
def investment_bar():
    parts = [("Perangkat dan pemasangan", DEVICES, GREY), ("Fee developer AI dan web app", DEV_FEE, ACCENT),
             ("Fee infrastruktur dan PM", INFRA_FEE, "#7C8796")]
    W, x0, y0, h = 1440, 0, 40, 64
    out, x = [], x0
    for i, (name, v, c) in enumerate(parts):
        w = v / INVEST * W
        last = i == len(parts) - 1
        tx, anchor = (x + w - 4, "end") if last else (x + 4, "start")
        out.append(f"<rect x='{x:.1f}' y='{y0}' width='{max(w - 3, 1):.1f}' height='{h}' rx='4' fill='{c}'/>"
                   f"<text x='{tx:.1f}' y='{y0 - 12}' text-anchor='{anchor}' font-size='20' font-weight='600' fill='{INK}'>{e(name)}</text>"
                   f"<text x='{tx:.1f}' y='{y0 + h + 30}' text-anchor='{anchor}' font-size='20' fill='{MUTED}'>{jt(v)} · {pct(v / INVEST, 0)}</text>")
        x += w
    return f"<svg viewBox='0 0 {W} 150' width='{W}' height='150'>{''.join(out)}</svg>"


def waterfall_a():
    steps = [("Modal investor saat PO", -INVEST), ("DP 50% klien saat PO", PRICE_A * 0.5),
             ("Termin 30% setelah instalasi", PRICE_A * 0.3), ("Termin 20% saat serah terima", PRICE_A * 0.2)]
    W, H, left, y_top, y_bot = 860, 540, 80, 40, 450
    lo, hi = -INVEST * 1.04, max(profit_a, 0) + 40e6
    Y = lambda v: y_top + (hi - v) / (hi - lo) * (y_bot - y_top)
    bw, gap = 112, 40
    out = []
    for t in range(-250, 51, 50):
        v = t * 1e6
        if lo <= v <= hi:
            out.append(f"<line x1='{left}' x2='{W - 10}' y1='{Y(v):.1f}' y2='{Y(v):.1f}' stroke='{AXIS if t == 0 else GRID}' stroke-width='{1.5 if t == 0 else 1}'/>"
                       f"<text x='{left - 12}' y='{Y(v) + 6:.1f}' text-anchor='end' font-size='17' fill='{MUTED}'>{t}</text>")
    level, x = 0, left + 20
    for i, (name, v) in enumerate(steps):
        a, b = level, level + v
        c = BAD if v < 0 else GOOD
        out.append(f"<rect x='{x}' y='{Y(max(a, b)):.1f}' width='{bw}' height='{abs(Y(a) - Y(b)):.1f}' fill='{c}' fill-opacity='0.85' rx='3'/>")
        lab_y = Y(max(a, b)) + 30 if v < 0 else Y(max(a, b)) - 10
        out.append(f"<text x='{x + bw / 2}' y='{lab_y:.1f}' text-anchor='middle' font-size='19' font-weight='600' fill='{'#FFFFFF' if v < 0 else INK}'>{'+' if v > 0 else ''}{jt(v).replace('Rp ', '').replace(' juta', '')}</text>")
        words = name.split(" ")
        mid = len(words) // 2 + (1 if len(words) % 2 else 0)
        for k, line in enumerate([" ".join(words[:mid]), " ".join(words[mid:])]):
            out.append(f"<text x='{x + bw / 2}' y='{y_bot + 30 + k * 22}' text-anchor='middle' font-size='16' fill='{MUTED}'>{e(line)}</text>")
        if i < len(steps) - 1:
            out.append(f"<line x1='{x + bw}' x2='{x + bw + gap}' y1='{Y(b):.1f}' y2='{Y(b):.1f}' stroke='{AXIS}' stroke-dasharray='4 4'/>")
        level, x = b, x + bw + gap
    out.append(f"<rect x='{x}' y='{Y(max(0, level)):.1f}' width='{bw}' height='{max(abs(Y(0) - Y(level)), 2):.1f}' fill='{GREY}' rx='3'/>"
               f"<text x='{x + bw / 2}' y='{Y(max(0, level)) - 10:.1f}' text-anchor='middle' font-size='19' font-weight='600' fill='{INK}'>+{jt(level).replace('Rp ', '').replace(' juta', '')}</text>"
               f"<text x='{x + bw / 2}' y='{y_bot + 30}' text-anchor='middle' font-size='16' fill='{MUTED}'>Profit</text>"
               f"<text x='{x + bw / 2}' y='{y_bot + 52}' text-anchor='middle' font-size='16' fill='{MUTED}'>investor</text>")
    out.append(f"<text x='{left - 12}' y='{y_top - 14}' text-anchor='end' font-size='16' fill='{MUTED}'>juta Rp</text>"
               f"<text x='{W - 10}' y='{y_top - 14}' text-anchor='end' font-size='16' fill='{MUTED}'>hijau = masuk · merah = keluar · abu = hasil</text>")
    return f"<svg viewBox='0 0 {W} {H}' width='{W}' height='{H}'>{''.join(out)}</svg>"


def jcurve_b():
    W, H, left, right, y_top, y_bot = 900, 400, 70, 880, 34, 330
    n = len(cum_b) - 1
    lo, hi = min(cum_b) * 1.3, max(cum_b_best) * 1.12
    X = lambda m: left + m / n * (right - left)
    Y = lambda v: y_top + (hi - v) / (hi - lo) * (y_bot - y_top)
    out = []
    for t in range(-100, 151, 25):
        v = t * 1e6
        if lo <= v <= hi:
            out.append(f"<line x1='{left}' x2='{right}' y1='{Y(v):.1f}' y2='{Y(v):.1f}' stroke='{AXIS if t == 0 else GRID}' stroke-width='{1.5 if t == 0 else 1}'/>"
                       f"<text x='{left - 12}' y='{Y(v) + 6:.1f}' text-anchor='end' font-size='17' fill='{MUTED}'>{t}</text>")
    for m in range(0, n + 1, 4):
        out.append(f"<text x='{X(m):.1f}' y='{y_bot + 30}' text-anchor='middle' font-size='17' fill='{MUTED}'>{m}</text>")
    out.append(f"<text x='{right}' y='{y_bot + 54}' text-anchor='end' font-size='16' fill='{MUTED}'>Bulan sejak PO</text>"
               f"<text x='{left - 12}' y='{y_top - 14}' text-anchor='end' font-size='16' fill='{MUTED}'>juta Rp</text>")
    for m, lab in [(GO_LIVE, "Go-live"), (GO_LIVE + 12, "Bayar langganan th-2"), (GO_LIVE + 24, "Bayar langganan th-3")]:
        out.append(f"<line x1='{X(m):.1f}' x2='{X(m):.1f}' y1='{y_top}' y2='{y_bot}' stroke='{AXIS}' stroke-dasharray='4 5'/>"
                   f"<text x='{X(m) + 6:.1f}' y='{y_top + 14}' font-size='15' fill='{MUTED}'>{lab}</text>")
    best = "".join(f"{'L' if m else 'M'}{X(m):.1f} {Y(v):.1f}" for m, v in enumerate(cum_b_best))
    base = "".join(f"{'L' if m else 'M'}{X(m):.1f} {Y(v):.1f}" for m, v in enumerate(cum_b))
    out.append(f"<path d='{best}' fill='none' stroke='{GREY}' stroke-width='2.5' stroke-dasharray='7 6'/>"
               f"<path d='{base}' fill='none' stroke='{ACCENT}' stroke-width='3.5'/>")
    out.append(f"<circle cx='{X(0):.1f}' cy='{Y(cum_b[0]):.1f}' r='6' fill='{ACCENT}'/>"
               f"<text x='{X(0) + 12:.1f}' y='{Y(cum_b[0]) + 26:.1f}' font-size='18' font-weight='600' fill='{INK}'>Dana tertahan {jt(cum_b[0])}</text>"
               f"<circle cx='{X(n):.1f}' cy='{Y(cum_b[-1]):.1f}' r='6' fill='{ACCENT}'/>"
               f"<text x='{X(n) - 10:.1f}' y='{Y(cum_b[-1]) + 28:.1f}' text-anchor='end' font-size='17' font-weight='600' fill='{INK}'>Profit +{jt(profit_b)}</text>"
               f"<circle cx='{X(n):.1f}' cy='{Y(cum_b_best[-1]):.1f}' r='5' fill='{GREY}'/>"
               f"<line x1='{right - 292}' x2='{right - 264}' y1='{y_top - 19}' y2='{y_top - 19}' stroke='{GREY}' stroke-width='2.5' stroke-dasharray='7 6'/>"
               f"<text x='{right}' y='{y_top - 14}' text-anchor='end' font-size='16' fill='{MUTED}'>bila cadangan utuh: +{jt(profit_b_best)}</text>"
               f"<circle cx='{X(payback_b):.1f}' cy='{Y(cum_b[payback_b]):.1f}' r='6' fill='{ACCENT}'/>"
               f"<text x='{X(payback_b) - 12:.1f}' y='{Y(cum_b[payback_b]) + 6:.1f}' text-anchor='end' font-size='17' font-weight='600' fill='{INK}'>Balik modal permanen, bulan ke-{payback_b}</text>")
    return f"<svg viewBox='0 0 {W} {H}' width='{W}' height='{H}'>{''.join(out)}</svg>"


def timeline():
    phases = [("Survey dock, desain posisi kamera, pengadaan perangkat", 1, 2), ("Instalasi kamera, jaringan, server; mulai rekam data", 3, 4),
              ("Pelabelan data, training model AI, logika hitung 60 karton", 5, 10), ("Pembuatan web app (berjalan paralel)", 5, 10),
              ("Optimasi realtime 4 kamera, integrasi data DO, kalibrasi", 11, 13), ("Uji paralel 2 minggu vs hitung manual", 14, 15),
              ("Training pengguna, SOP, serah terima (go-live)", 16, 16)]
    W, left, right, y0, row = 1440, 560, 1420, 50, 62
    X = lambda w: left + (w - 1) / 16 * (right - left)
    out = []
    for w in range(1, 17):
        out.append(f"<line x1='{X(w):.1f}' x2='{X(w):.1f}' y1='{y0 - 10}' y2='{y0 + row * len(phases)}' stroke='{GRID}'/>"
                   f"<text x='{X(w) + (right - left) / 32:.1f}' y='{y0 - 18}' text-anchor='middle' font-size='16' fill='{MUTED}'>M{w}</text>")
    for i, (name, a, b) in enumerate(phases):
        y = y0 + i * row + 14
        c = ACCENT if "go-live" in name else ("#7C8796" if "Uji" in name else GREY)
        out.append(f"<text x='0' y='{y + 22}' font-size='20' fill='{INK}'>{e(name)}</text>"
                   f"<rect x='{X(a) + 3:.1f}' y='{y}' width='{X(b + 1) - X(a) - 6:.1f}' height='32' rx='6' fill='{c}'/>")
    return f"<svg viewBox='0 0 {W} {y0 + row * len(phases) + 10}' width='{W}' height='{y0 + row * len(phases) + 10}'>{''.join(out)}</svg>"


def flow_diagram():
    box = lambda x, y, w, h, t1, t2, acc=False: (
        f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='14' fill='{SOFT if acc else '#FFFFFF'}' stroke='{ACCENT if acc else AXIS}' stroke-width='{2.5 if acc else 1.5}'/>"
        f"<text x='{x + w / 2}' y='{y + h / 2 - 6}' text-anchor='middle' font-size='22' font-weight='600' fill='{INK}'>{e(t1)}</text>"
        f"<text x='{x + w / 2}' y='{y + h / 2 + 22}' text-anchor='middle' font-size='17' fill='{MUTED}'>{e(t2)}</text>")
    arrow = lambda x1, y1, x2, y2: f"<path d='M{x1} {y1}L{x2} {y2}' stroke='{AXIS}' stroke-width='2' marker-end='url(#a)'/>"
    out = [f"<defs><marker id='a' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto'><path d='M0 0L10 5L0 10z' fill='{AXIS}'/></marker></defs>",
           box(0, 70, 230, 110, "4 kamera CCTV", "di zona cek dock"), arrow(230, 125, 290, 125),
           box(290, 50, 300, 150, "PC server AI", "on-premise, RTX 5060 Ti", True), arrow(590, 125, 650, 125),
           box(650, 50, 330, 150, "Hitung karton", "per palet, cocokkan DO", True), arrow(980, 100, 1040, 70), arrow(980, 150, 1040, 190),
           box(1040, 10, 340, 110, "Web app + TV dock", "status palet, alert, laporan"),
           box(1040, 140, 340, 110, "Owner via Tailscale", "live monitoring dari luar")]
    return f"<svg viewBox='0 0 1400 260' width='1400' height='260'>{''.join(out)}</svg>"


def dashboard_mock():
    rows = [("Palet 0418", "DO-2611-07", "60 / 60", True), ("Palet 0419", "DO-2611-07", "60 / 60", True),
            ("Palet 0420", "DO-2611-08", "57 / 60", False)]
    out = [f"<rect x='0' y='0' width='620' height='262' rx='14' fill='#FFFFFF' stroke='{AXIS}'/>",
           f"<rect x='0' y='0' width='620' height='48' rx='14' fill='{SOFT}'/><rect x='0' y='30' width='620' height='18' fill='{SOFT}'/>",
           f"<text x='20' y='31' font-size='18' font-weight='600' fill='{INK}'>Loading Dock 1 · Truk B 9123 KX</text>",
           f"<text x='600' y='31' text-anchor='end' font-size='16' fill='{MUTED}'>Ilustrasi</text>"]
    for i, (p, do, n, ok) in enumerate(rows):
        y = 70 + i * 62
        c = GOOD if ok else BAD
        out.append(f"<rect x='16' y='{y}' width='588' height='50' rx='8' fill='{'#FFFFFF' if ok else '#FBECEA'}' stroke='{GRID}'/>"
                   f"<circle cx='42' cy='{y + 25}' r='9' fill='{c}'/>"
                   f"<text x='64' y='{y + 31}' font-size='18' font-weight='600' fill='{INK}'>{p}</text>"
                   f"<text x='220' y='{y + 31}' font-size='17' fill='{MUTED}'>{do}</text>"
                   f"<text x='588' y='{y + 31}' text-anchor='end' font-size='19' font-weight='600' fill='{c}'>{n} karton</text>")
    return f"<svg viewBox='0 0 620 262' width='620' height='262'>{''.join(out)}</svg>"


# ---------------------------------------------------------------- slides
roi_a, roi_b, roi_b_best = profit_a / INVEST, profit_b / INVEST, profit_b_best / INVEST
slides = []


def slide(title, sub, body, n):
    slides.append(f"<section class='slide' id='s{n:02d}'><div class='head'><div class='kicker'>Proposal investasi · Hitung karton per palet · 4 kamera</div>"
                  f"<h1>{e(title)}</h1><p class='sub'>{e(sub)}</p></div><div class='body'>{body}</div>"
                  f"<div class='foot'><span>Gudang Minyakita · Loading dock</span><span>{n:02d}</span></div></section>")


slides.append(f"""<section class='slide cover' id='s01'><div class='cover-inner'>
<div class='kicker'>Proposal investasi · November 2026</div>
<h1 class='big'>Sistem Hitung Karton per Palet di Loading Dock</h1>
<p class='lead'>AI computer vision menghitung karton di setiap palet sebelum naik ke truk, dan mencocokkannya dengan DO secara realtime.</p>
<div class='cover-kpis'>{kpi('Lokasi', 'Gudang Minyakita')}{kpi('Skala', '4 kamera CCTV')}{kpi('Modal awal investor', jt(INVEST), rp(INVEST), True)}{kpi('Waktu pengerjaan', '16 minggu', 'PO sampai go-live')}</div>
</div></section>""")

slide("Hitung manual di loading dock rawan selisih; sistem ini menghitung setiap palet otomatis",
      "Standar 1 palet = 60 karton. Selisih ketahuan setelah truk berangkat, ketika sudah sulit ditelusuri.",
      f"""<div class='two'><div class='card'><h3>Masalah hari ini</h3><ul>
<li>Checker menghitung karton per palet secara manual saat jam sibuk</li><li>Palet kurang 1-3 karton sering lolos ke truk</li>
<li>Selisih baru ketahuan di tujuan; bukti sulit dicari</li><li>Tidak ada data realtime per DO, per truk, dan per palet</li></ul></div>
<div class='card accent'><h3>Solusi yang dibangun</h3><ul>
<li>Kamera di zona cek dock menghitung karton setiap palet secara otomatis</li><li>Peringatan langsung di TV dock bila palet kurang dari 60</li>
<li>Rekonsiliasi otomatis per DO, per truk, dan per palet</li><li>Rekaman dan foto bukti tersimpan sebagai audit trail</li></ul></div></div>
<div class='kpi-row'>{kpi('Isi standar', '60 karton / palet')}{kpi('Kecepatan analisa', '20-30 fps', 'realtime per kamera')}{kpi('Jumlah kamera', '4 kamera 4MP')}{kpi('Deployment', 'On-premise', 'tanpa cloud')}</div>""", 2)

slide("Kamera, PC server AI, lalu hasilnya tampil di web app dan TV dock",
      "Semua proses berjalan di PC server di gudang; owner tetap bisa memantau dari luar lewat Tailscale.",
      f"<div class='center'>{flow_diagram()}</div><div class='two narrow'><div>{dashboard_mock()}</div><div class='card'><h3>Yang dilihat pengguna</h3><ul>"
      "<li>Status setiap palet: lengkap (hijau) atau kurang (merah)</li><li>Jumlah karton per palet, per DO, dan per truk</li>"
      "<li>Riwayat event dengan foto dan klip bukti</li><li>Live view 4 kamera untuk owner dan supervisor</li>"
      "<li>Rekaman dan data tersimpan di PC server gudang, tanpa cloud</li></ul></div></div>", 3)

slide("Pengerjaan 16 minggu dari PO sampai go-live",
      "Uji paralel 2 minggu memastikan akurasi dan kecepatan 20-30 fps sebelum sistem dipakai penuh.",
      f"<div class='center'>{timeline()}</div>", 4)

dev_rows = [[e(k), rp(v)] for k, v in sw.items()] + [["<b>Total fee developer</b>", f"<b>{rp(DEV_FEE)}</b>"]]
dev_table = table(["Fee developer (AI computer vision dan web app)", "Nilai"], dev_rows, ["70%", "30%"], True, (1,))
inv_rows = ([[e(k), rp(v)] for k, v in devices.items()] + [["<b>Subtotal perangkat</b>", f"<b>{rp(DEVICES)}</b>"]]
            + [["Fee developer AI computer vision dan web app", rp(DEV_FEE)], ["Fee infrastruktur dan project management", rp(INFRA_FEE)],
               ["<b>Total investasi awal</b>", f"<b>{rp(INVEST)}</b>"]])
slide(f"Total investasi awal {jt(INVEST)}, dibayar investor saat PO",
      "Perangkat dari toko resmi (harga Oktober 2026) + cadangan kenaikan harga 10%; fee tim mengikuti tarif INKINDO 2026.",
      f"<div class='center'>{investment_bar()}</div><div class='center tbl-wide'>{table(['Rincian investasi awal', 'Nilai'], inv_rows, ['72%', '28%'], True, (1,))}</div>", 5)

infra_rows = [[e(k), rp(v)] for k, v in infra.items()] + [["<b>Total fee infrastruktur</b>", f"<b>{rp(INFRA_FEE)}</b>"]]
slide("Fee tim tetap: developer Rp 107 juta, infrastruktur Rp 37,3 juta",
      "Fee dibayar dari dana investor. Setelah go-live, support bulanan dibayar dari pendapatan langganan (model subscription).",
      f"<div class='two'><div>{dev_table}</div><div>{table(['Fee infrastruktur dan project management', 'Nilai'], infra_rows, ['70%', '30%'], True, (1,))}"
      f"<p class='note'>Tim tidak menaruh modal. Profit proyek setelah fee tim menjadi hak investor.</p></div></div>", 6)

cmp_rows = [
    ["Yang dibayar klien", f"{rp(PRICE_A)} sekali (termin 50/30/20)", f"{rp(SETUP_B)} sekali + {rp(SUB_B)} per tahun"],
    ["Total pendapatan proyek", rp(PRICE_A), f"{rp(TOTAL_B)} (36 bulan)"],
    ["Pemilik perangkat", "Klien", "Penyedia (jaminan investor)"],
    ["Durasi dana investor", "4 bulan", "40 bulan (PO sampai akhir kontrak)"],
    ["Profit investor", f"<b>{rp(profit_a)}</b>", f"<b>{rp(profit_b)}</b> (s.d. {rp(profit_b_best)})"],
    ["ROI atas modal awal", pct(roi_a), f"{pct(roi_b)} (s.d. {pct(roi_b_best)})"],
    ["Dana investor tertahan paling besar", rp(peak_a), rp(peak_b)],
]
slide("Dua model pendapatan: beli putus untung cepat tapi kecil, subscription lebih besar tapi lebih lama",
      "Modal awal sama di kedua model; yang beda adalah cara dan waktu klien membayar.",
      f"<div class='center tbl-wide'>{table(['', 'Beli putus (seperti Opsi A)', 'Subscription (seperti Opsi B)'], cmp_rows, ['30%', '32%', '38%'], False, ())}</div>", 7)

a_rows = [["Saat PO (bulan 0)", rp(PRICE_A * 0.5), rp(INVEST), rp(cum_a[0])], ["Setelah instalasi (bulan 1)", rp(PRICE_A * 0.3), "-", rp(cum_a[1])],
          ["Serah terima / go-live (bulan 4)", rp(PRICE_A * 0.2), "-", rp(cum_a[GO_LIVE])]]
slide(f"Beli putus: investor untung {jt(profit_a)} ({pct(roi_a)}) dalam 4 bulan",
      "Klien membayar termin 50% saat PO, 30% setelah instalasi, 20% saat serah terima. Cocok sebagai pendanaan jangka pendek.",
      f"<div class='two wide-left'><div>{waterfall_a()}</div><div><div class='kpi-col'>{kpi('Profit investor', jt(profit_a), rp(profit_a), True)}"
      f"{kpi('ROI atas modal awal', pct(roi_a), 'dalam 4 bulan')}{kpi('Dana tertahan paling besar', jt(peak_a), 'setelah DP klien saat PO')}"
      f"{kpi('Modal kembali penuh', 'Bulan ke-4', 'saat serah terima')}</div></div></div>", 8)

b_rows = [[e(r[0]), rp(r[1]) if r[1] else "-", rp(r[2]) if r[2] else "-", rp(r[3])] for r in year_rows_b]
slide(f"Subscription: investor untung {jt(profit_b)} ({pct(roi_b)}) dalam 40 bulan",
      f"Langganan dibayar di muka tiap tahun; profit naik ke {jt(profit_b_best)} bila cadangan penggantian perangkat utuh.",
      f"<div class='two wide-left'><div>{jcurve_b()}</div><div><div class='kpi-col'>{kpi('Profit investor', jt(profit_b), f's.d. {jt(profit_b_best)} bila cadangan utuh', True)}"
      f"{kpi('ROI atas modal awal', pct(roi_b), f's.d. {pct(roi_b_best)}, dalam 40 bulan')}{kpi('Dana tertahan paling besar', jt(peak_b), 'setelah pembayaran klien saat PO')}"
      f"{kpi('Balik modal permanen', f'Bulan ke-{payback_b}', f'saldo pertama positif di bulan ke-{first_cross_b}')}</div></div></div>"
      f"<div class='center tbl-wide small'>{table(['Periode', 'Uang masuk', 'Uang keluar', 'Saldo kumulatif'], b_rows, ['34%', '20%', '26%', '20%'], False, (1, 2, 3))}</div>", 9)

ret_rows = [["Modal awal investor", rp(INVEST), rp(INVEST)], ["Total uang kembali ke investor", rp(INVEST + profit_a), f"{rp(INVEST + profit_b)} (s.d. {rp(INVEST + profit_b_best)})"],
            ["Profit investor", f"<b>{rp(profit_a)}</b>", f"<b>{rp(profit_b)}</b> (s.d. {rp(profit_b_best)})"],
            ["ROI atas modal awal", pct(roi_a), f"{pct(roi_b)} (s.d. {pct(roi_b_best)})"],
            ["ROI atas dana tertahan paling besar", pct(profit_a / peak_a), f"{pct(profit_b / peak_b)} (s.d. {pct(profit_b_best / peak_b)})"],
            ["Waktu sampai profit diterima penuh", "4 bulan", "40 bulan"], ["Fee developer (tetap)", rp(DEV_FEE), rp(DEV_FEE)]]
slide("Ringkasan return investor per model",
      "Developer menerima fee tetap Rp 107 juta di kedua model; seluruh profit proyek setelah biaya menjadi hak investor.",
      f"<div class='center tbl-wide'>{table(['', 'Beli putus', 'Subscription 36 bulan'], ret_rows, ['36%', '28%', '36%'], False, ())}</div>"
      f"<p class='note center-note'>ROI atas dana tertahan dihitung dari saldo minus terbesar setelah pembayaran klien masuk.</p>", 10)

risk_rows = [["Klien berhenti di tengah kontrak (subscription)", "Biaya pemutusan = sisa sewa perangkat sampai bulan ke-36; perangkat tetap milik penyedia"],
             ["Klien telat bayar", "Lebih dari 30 hari, layanan support dihentikan sementara; pembayaran di muka per tahun"],
             ["Perangkat rusak", "Cadangan penggantian Rp 31,5 juta sudah dihitung; kerusakan karena kelalaian ditanggung klien"],
             ["Akurasi atau kecepatan tidak tercapai", "Uji paralel 2 minggu sebelum go-live dan sebelum termin terakhir"],
             ["Harga perangkat naik", "Sudah ada cadangan kenaikan harga 10%"],
             ["Lisensi software AI", "Model memakai lisensi komersial bebas (Apache-2.0), tanpa biaya lisensi tahunan"]]
slide("Risiko utama dan mitigasinya", "Struktur kontrak dibuat supaya dana investor tetap aman bila klien berhenti atau telat bayar.",
      f"<div class='center tbl-wide'>{table(['Risiko', 'Mitigasi'], [[e(a), e(b)] for a, b in risk_rows], ['36%', '64%'])}</div>", 11)

slide("Langkah berikutnya", "Keputusan yang dibutuhkan dari investor dan urutan eksekusinya.",
      f"""<div class='two'><div class='card'><h3>Yang diminta dari investor</h3><ul>
<li>Komitmen modal awal {jt(INVEST)} ({rp(INVEST)}) saat PO</li><li>Pilih model: beli putus atau subscription 36 bulan</li>
<li>Perjanjian investasi tertulis: profit, jadwal pembayaran, jaminan perangkat</li></ul></div>
<div class='card accent'><h3>Urutan eksekusi</h3><ol>
<li>Penawaran final dan PO dari klien</li><li>Dana investor masuk; pengadaan perangkat minggu 1-2</li>
<li>Pengerjaan 16 minggu, laporan progres mingguan ke investor</li><li>Go-live; pembayaran klien sesuai model yang dipilih</li></ol></div></div>""", 12)

CSS = f"""
@page {{ size: 1600px 900px; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #F4F6F9; font-family: Inter, 'Helvetica Neue', Arial, sans-serif; color: {INK}; }}
.slide {{ width: 1600px; height: 900px; background: #FFFFFF; position: relative; padding: 56px 80px 64px; margin: 0 auto 24px; overflow: hidden; }}
.kicker {{ font-size: 18px; letter-spacing: .04em; text-transform: uppercase; color: {ACCENT}; font-weight: 600; }}
h1 {{ font-size: 40px; line-height: 1.18; margin: 10px 0 8px; font-weight: 700; max-width: 1380px; }}
.sub {{ font-size: 22px; color: {MUTED}; margin: 0 0 22px; max-width: 1380px; }}
.foot {{ position: absolute; left: 80px; right: 80px; bottom: 24px; display: flex; justify-content: space-between; font-size: 16px; color: {MUTED}; border-top: 1px solid {GRID}; padding-top: 10px; }}
.body {{ position: relative; }}
.center {{ display: flex; justify-content: center; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }}
.two.narrow {{ grid-template-columns: 640px 1fr; margin-top: 18px; align-items: start; }}
.two.wide-left {{ grid-template-columns: auto 1fr; gap: 36px; align-items: start; }}
.kpi-col .kpi {{ padding: 10px 18px; }}
.kpi-col .kpi-value {{ font-size: 26px; }}
.card {{ border: 1.5px solid {GRID}; border-radius: 16px; padding: 24px 28px; }}
.card.accent {{ border-color: {ACCENT}; background: {SOFT}; }}
.card h3 {{ margin: 0 0 10px; font-size: 26px; }}
.card ul, .card ol {{ margin: 0; padding-left: 26px; font-size: 22px; line-height: 1.55; }}
.kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 28px; }}
.kpi-col {{ display: grid; gap: 14px; margin-bottom: 18px; }}
.kpi {{ border: 1.5px solid {GRID}; border-radius: 14px; padding: 14px 20px; }}
.kpi.accent {{ border-color: {ACCENT}; background: {SOFT}; }}
.kpi-label {{ font-size: 17px; color: {MUTED}; }}
.kpi-value {{ font-size: 30px; font-weight: 700; margin-top: 2px; }}
.kpi-note {{ font-size: 16px; color: {MUTED}; min-height: 4px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 19px; }}
.tbl-wide table {{ width: 1360px; }}
.small table {{ font-size: 16px; }}
.small td, .small th {{ padding: 5px 12px; }}
.small {{ margin-top: 8px; }}
th {{ text-align: left; font-weight: 600; color: {MUTED}; border-bottom: 2px solid {INK}; padding: 8px 12px; font-size: 17px; }}
td {{ border-bottom: 1px solid {GRID}; padding: 8px 12px; vertical-align: top; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
tr.total td {{ border-top: 2px solid {INK}; border-bottom: none; }}
.note {{ font-size: 19px; color: {MUTED}; margin-top: 16px; }}
.center-note {{ text-align: center; }}
.cover {{ background: linear-gradient(135deg, #FFFFFF 55%, {SOFT}); }}
.cover-inner {{ position: absolute; left: 96px; right: 96px; top: 150px; }}
h1.big {{ font-size: 64px; max-width: 1200px; margin: 18px 0 20px; }}
.lead {{ font-size: 28px; color: {MUTED}; max-width: 1150px; line-height: 1.4; }}
.cover-kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 70px; }}
"""
(HERE / "deck.html").write_text(f"<!doctype html><html lang='id'><head><meta charset='utf-8'><title>Proposal Investasi Hitung Karton</title>"
                                f"<style>{CSS}</style></head><body>{''.join(slides)}</body></html>")

# ---------------------------------------------------------------- detail_project.md
L = []
w = L.append
w("# Detail Project: Sistem Hitung Karton per Palet di Loading Dock (4 Kamera)\n")
w("Proposal investasi untuk pembangunan sistem AI computer vision yang menghitung karton pada setiap palet di loading dock "
  "Gudang Minyakita, sebelum barang naik ke truk ekspedisi. Dokumen ini adalah brief untuk membuat deck PPTX di Claude Design: "
  "isi tiap slide, angka, grafik, dan tabelnya sudah final dan konsisten dengan file budget.\n")
w(f"- **Tanggal:** November 2026\n- **Lokasi:** Gudang Minyakita, area loading dock\n- **Skala:** 4 kamera CCTV 4MP\n"
  f"- **Modal awal investor:** {rp(INVEST)} ({jt(INVEST)})\n- **Fee developer AI computer vision dan web app:** {rp(DEV_FEE)}\n"
  f"- **Waktu pengerjaan:** 16 minggu dari PO sampai go-live\n- **Semua angka dalam Rupiah.**\n")
w("## 1. Apa yang dikerjakan\n")
w("Yang dibangun adalah **sistem penghitungan box (karton) pada palet di loading dock**:\n")
w("1. Palet berhenti sebentar di zona cek depan dock.\n2. 4 kamera CCTV merekam palet; PC server AI di gudang menghitung jumlah karton secara realtime (20-30 fps per kamera).\n"
  "3. Hasil hitung dibandingkan dengan standar 60 karton per palet dan dengan data DO (delivery order).\n"
  "4. Status palet (lengkap atau kurang) tampil di TV loading dock dan di web app; palet kurang langsung memicu peringatan.\n"
  "5. Setiap event tersimpan bersama foto dan klip bukti di PC server sebagai audit trail. Owner bisa live monitoring dari luar gudang lewat Tailscale.\n")
w("**Komponen utama:** model AI computer vision (deteksi dan hitung karton), web app on-premise (dashboard, laporan per DO, truk, dan palet, "
  "event trigger, riwayat event), PC server AI dengan GPU NVIDIA RTX 5060 Ti 16 GB, 4 kamera Hikvision 4MP, jaringan, UPS, dan TV status di dock. "
  "Tidak memakai cloud; data tetap di gudang.\n")
w("## 2. Timeline 16 minggu\n")
for name, wk in [("Survey dock, desain posisi kamera, pengadaan perangkat", "M1-M2"), ("Instalasi kamera, jaringan, server; mulai rekam data", "M3-M4"),
                 ("Pelabelan data, training model AI, logika hitung 60 karton", "M5-M10"), ("Pembuatan web app (paralel)", "M5-M10"),
                 ("Optimasi realtime 4 kamera, integrasi data DO, kalibrasi", "M11-M13"), ("Uji paralel 2 minggu vs hitung manual", "M14-M15"),
                 ("Training pengguna, SOP, serah terima (go-live)", "M16")]:
    w(f"- **{wk}:** {name}")
w("")
w(f"## 3. Total investasi awal: {rp(INVEST)}\n")
w("Dibayar investor saat PO. Harga perangkat dari toko resmi di Tokopedia (dicek Oktober 2026) ditambah cadangan kenaikan harga 10%. "
  "Fee tim dihitung dari tarif INKINDO 2026.\n")
w("| Rincian | Nilai |\n| --- | ---: |")
for k, v in devices.items():
    w(f"| {k} | {rp(v)} |")
w(f"| **Subtotal perangkat** | **{rp(DEVICES)}** |\n| Fee developer AI computer vision dan web app | {rp(DEV_FEE)} |\n"
  f"| Fee infrastruktur dan project management | {rp(INFRA_FEE)} |\n| **Total investasi awal** | **{rp(INVEST)}** |\n")
w("### Fee developer (tetap): Rp 107.000.000\n\n| Rincian | Nilai |\n| --- | ---: |")
for k, v in sw.items():
    w(f"| {k} | {rp(v)} |")
w(f"| **Total** | **{rp(DEV_FEE)}** |\n")
w(f"### Fee infrastruktur dan project management: {rp(INFRA_FEE)}\n\n| Rincian | Nilai |\n| --- | ---: |")
for k, v in infra.items():
    w(f"| {k} | {rp(v)} |")
w(f"| **Total** | **{rp(INFRA_FEE)}** |\n")
w("Tim (developer dan orang infrastruktur) tidak menaruh modal. Profit proyek setelah fee tim dan biaya operasional menjadi hak investor.\n")
w("## 4. Dua model pendapatan\n")
w("| | Beli putus (seperti Opsi A) | Subscription (seperti Opsi B) |\n| --- | --- | --- |")
for r in cmp_rows:
    w("| " + " | ".join(c.replace("<b>", "**").replace("</b>", "**") for c in r) + " |")
w("")
w(f"**Asumsi model:** seluruh fee tim dan pembelian perangkat dibayar investor saat PO. Pembayaran klien masuk ke investor. "
  f"Pada subscription, support bulanan untuk tim ({rp(SUP_YEAR)} per tahun) dan cadangan penggantian perangkat ({rp(RESERVE)} selama kontrak, "
  f"dihitung rata per bulan) dibayar dari pendapatan langganan. Angka \"s.d.\" berlaku bila cadangan penggantian tidak terpakai.\n")
w(f"## 5. Proyeksi beli putus: profit {rp(profit_a)} ({pct(roi_a)}) dalam 4 bulan\n")
w("| Waktu | Uang masuk | Uang keluar | Saldo kumulatif investor |\n| --- | ---: | ---: | ---: |")
for r in a_rows:
    w("| " + " | ".join(r) + " |")
w(f"\nDana investor tertahan paling besar {rp(peak_a)} (setelah DP klien saat PO). Grafik: waterfall dari modal -{jt(INVEST)} sampai profit +{jt(profit_a)}.\n")
w(f"## 6. Proyeksi subscription: profit {rp(profit_b)} ({pct(roi_b)}), s.d. {rp(profit_b_best)} ({pct(roi_b_best)})\n")
w("| Periode | Uang masuk | Uang keluar (modal awal, support, cadangan) | Saldo kumulatif investor |\n| --- | ---: | ---: | ---: |")
for r in b_rows:
    w("| " + " | ".join(r) + " |")
w(f"\nSaldo pertama kali positif di bulan ke-{first_cross_b}, lalu sempat turun lagi sebelum pembayaran langganan tahun ke-3; balik modal permanen di bulan ke-{payback_b}. "
  f"Dana tertahan paling besar {rp(peak_b)} (setelah pembayaran klien saat PO).\n")
w("## 7. Ringkasan return investor\n")
w("| | Beli putus | Subscription 36 bulan |\n| --- | --- | --- |")
for r in ret_rows:
    w("| " + " | ".join(c.replace("<b>", "**").replace("</b>", "**") for c in r) + " |")
w("")
w("## 8. Risiko dan mitigasi\n\n| Risiko | Mitigasi |\n| --- | --- |")
for a, b in risk_rows:
    w(f"| {a} | {b} |")
w("")
w("## 9. Naskah slide untuk Claude Design (16:9)\n")
w("Gaya: bersih, latar putih, satu warna aksen biru untuk angka utama, abu-abu untuk data pendukung, hijau = uang masuk, merah = uang keluar. "
  "Font sans-serif (Inter). Judul slide berupa kalimat temuan, bukan topik. Gambar mockup referensi ada di folder `slides/`.\n")
script = [
    ("Cover", "Sistem Hitung Karton per Palet di Loading Dock", f"Kartu angka: Gudang Minyakita · 4 kamera CCTV · modal awal {jt(INVEST)} · 16 minggu."),
    ("Masalah dan solusi", "Hitung manual di loading dock rawan selisih; sistem ini menghitung setiap palet otomatis",
     "Dua kolom: masalah hari ini vs solusi. Baris kartu: 60 karton/palet, 20-30 fps, 4 kamera, on-premise."),
    ("Cara kerja", "Cara kerja: kamera, PC server AI, lalu hasilnya tampil di web app dan TV dock",
     "Diagram alur: 4 kamera -> PC server AI -> hitung karton dan cocokkan DO -> web app + TV dock dan owner via Tailscale. Mockup tampilan web app (ilustrasi): daftar palet hijau/merah."),
    ("Timeline", "Pengerjaan 16 minggu dari PO sampai go-live", "Gantt 7 baris per minggu (M1-M16), lihat bagian 2."),
    ("Investasi awal", f"Total investasi awal {jt(INVEST)}, dibayar investor saat PO", "Bar bertumpuk 3 bagian (perangkat, fee developer, fee infrastruktur) + tabel rincian bagian 3."),
    ("Fee tim", "Fee tim tetap: developer Rp 107 juta, infrastruktur Rp 37,3 juta", "Dua tabel rincian fee (bagian 3)."),
    ("Model pendapatan", "Dua model pendapatan: beli putus untung cepat tapi kecil, subscription lebih besar tapi lebih lama", "Tabel perbandingan bagian 4."),
    ("Proyeksi beli putus", f"Beli putus: investor untung {jt(profit_a)} ({pct(roi_a)}) dalam 4 bulan", "Waterfall + 3 kartu KPI + tabel arus kas bagian 5."),
    ("Proyeksi subscription", f"Subscription: investor untung {jt(profit_b)} ({pct(roi_b)}), balik modal permanen di bulan ke-{payback_b}",
     "Grafik garis saldo kumulatif per bulan (bulan 0-39), garis putus-putus abu untuk skenario cadangan utuh, penanda go-live dan pembayaran tahunan + tabel bagian 6."),
    ("Return investor", "Ringkasan return investor per model", "Tabel bagian 7."),
    ("Risiko", "Risiko utama dan mitigasinya", "Tabel bagian 8."),
    ("Langkah berikutnya", "Langkah berikutnya", f"Yang diminta dari investor (komitmen {jt(INVEST)}, pilih model, perjanjian tertulis) + urutan eksekusi 4 langkah."),
]
for i, (name, title, content) in enumerate(script, 1):
    w(f"{i}. **{name}.** Judul: \"{title}\". Isi: {content}")
w("")
w("## 10. Data grafik\n")
w("**Saldo kumulatif investor, beli putus (juta Rp, bulan 0-4):** " + ", ".join(f"{m}: {v / 1e6:.1f}" for m, v in enumerate(cum_a)) + "\n")
w("**Saldo kumulatif investor, subscription (juta Rp, bulan 0-39):** " + ", ".join(f"{m}: {v / 1e6:.1f}" for m, v in enumerate(cum_b)) + "\n")
w("**Sama, bila cadangan penggantian tidak terpakai:** " + ", ".join(f"{m}: {v / 1e6:.1f}" for m, v in enumerate(cum_b_best)) + "\n")
w("**File gambar siap pakai (folder `grafik/`, PNG resolusi 3x + SVG vektor):**\n\n"
  "| File | Dipakai di slide |\n| --- | --- |\n"
  "| grafik-01-alur-sistem | 3. Cara kerja |\n| grafik-02-contoh-dashboard | 3. Cara kerja |\n"
  "| grafik-03-timeline-16-minggu | 4. Timeline |\n| grafik-04-komposisi-investasi | 5. Investasi awal |\n"
  "| grafik-05-waterfall-beli-putus | 8. Proyeksi beli putus |\n| grafik-06-saldo-subscription | 9. Proyeksi subscription |\n\n"
  "Mockup slide lengkap ada di folder `slides/` (3200x1800 px) sebagai acuan layout.\n")
w("## 11. Sumber\n")
w("- Budget internal: `Budget_Minyakita_Pallet_Counting_4Kamera.xlsx` (sheet RAB, Jasa INKINDO, Skenario A, Skenario B, Cadangan Penggantian).\n"
  "- Tarif jasa: Pedoman Standar Minimal Billing Rate INKINDO 2026 (https://www.inkindo.org/documents/ikdweb-billing-rate-2026.pdf).\n"
  "- Harga perangkat: toko resmi di Tokopedia, dicek Oktober 2026 (tautan per barang di sheet RAB).\n"
  "- Ini proyeksi berdasarkan penawaran ke klien; realisasi tergantung PO, jadwal pembayaran klien, dan biaya aktual.")
(HERE / "detail_project.md").write_text("\n".join(L) + "\n")
print(json.dumps({k: data[k] for k in ("invest", "profit_a", "profit_b", "profit_b_best", "peak_a", "peak_b", "payback_b", "first_cross_b")}))
