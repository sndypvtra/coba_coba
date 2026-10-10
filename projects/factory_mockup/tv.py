"""Dashboard TV pages: the product's own TV screen, with the camera picture of the PoC in it.

As in the warehouse mockup, the page is the product: a dark TV layout with its own KPIs, charts,
event log and timeline, built here in HTML. From the PoC it takes only the camera picture with the
AI overlay drawn on it (img/<product>_cam_<frame>.jpg, see assets.py) and the measured figures
(the PoC summary and event files). Nothing of the PoC's own dashboard video is reused.
"""
from __future__ import annotations

import json
from pathlib import Path

from look import CSS, I, bd, card, hbars, kpi, legend, lines, num, tg, vbars

HERE = Path(__file__).resolve().parent
P = HERE.parent
META = json.loads((HERE / "img" / "meta.json").read_text())
WM_POC = "Mockup konsep · angka ilustrasi · gambar kamera dan angka bertanda PoC: hasil proof of concept"

# each product's TV rotates through its own views only; views not in the PoC are shown as tabs, never as screens
APPS = {"tomato": "grading", "lemon": "grading", "fill": "fill", "tray": "pack", "packing": "pack", "parcel": "parcel"}
TABS = {"grading": [("nutrition", "Tomat · USDA", "tomato"), ("nutrition", "Lemon · OECD", "lemon"), ("monitoring", "Tren lot", "-")],
        "fill": [("local_drink", "Line F1 · nozzle 1–8", "fill"), ("local_drink", "Line F2", "-"), ("water_drop", "Giveaway", "-")],
        "pack": [("inventory_2", "Tray kaleng · C1", "tray"), ("precision_manufacturing", "Robot packing · P1", "packing"),
                 ("grid_view", "Slot kosong", "-")],
        "parcel": [("package_2", "Belt OB1", "parcel"), ("package_2", "Belt OB2", "-"), ("local_shipping", "Muat truk", "-")]}
BRAND = {"grading": ("nutrition", "Produce Grading", "#16a34a"), "fill": ("local_drink", "Fill Level Inspection", "#2563eb"),
         "pack": ("inventory_2", "Pack Count QC", "#d97706"), "parcel": ("package_2", "Parcel Dimensioning", "#7c3aed")}
SEV_COL = {"high": "#ef4444", "medium": "#f59e0b", "low": "#3b82f6", "info": "#94a3b8"}
SEV_ID = {"high": ("red", "Tinggi", "error"), "medium": ("amber", "Sedang", "warning"), "low": ("blue", "Rendah", "info"),
          "info": ("slate", "Info", "info")}

EXTRA = """
.tvc{position:relative;border-radius:12px;overflow:hidden;background:#000;border:1px solid var(--border)}
.tvc img.cam{width:100%;height:100%;object-fit:cover;display:block}
.tvc .ch1,.tvc .ch2{position:absolute;top:12px;display:flex;gap:6px}
.tvc .ch1{left:12px}.tvc .ch2{right:12px}
.tvc .pl{height:28px;padding:0 11px;border-radius:7px;background:rgba(10,14,19,.82);color:#e9eef4;font-size:13px;font-weight:600;
  display:inline-flex;align-items:center;gap:7px;backdrop-filter:blur(2px)}
.tvc .pl .dot{width:8px;height:8px;border-radius:50%;background:currentColor}
.tvc .pl.live{color:#fca5a5}.tvc .pl.live b{color:#e9eef4}
.tvc .lgd{position:absolute;left:12px;bottom:12px;display:flex;gap:14px;padding:7px 12px;border-radius:8px;
  background:rgba(10,14,19,.82);color:#cbd5e1;font-size:12.5px}
.tvc .lgd i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.th{width:104px;height:58px;border-radius:7px;object-fit:cover;flex:none;background:#000}
.ev .tm{color:var(--text-3);font-size:12px;font-variant-numeric:tabular-nums;margin-left:auto;text-align:right;white-space:nowrap}
.tline{display:flex;align-items:center;gap:18px;padding:0 18px;height:56px;border-radius:12px;background:var(--surface);border:1px solid var(--border)}
.tline b{font-size:13.5px;white-space:nowrap}
.tline .bar{position:relative;flex:1;height:6px;border-radius:3px;background:#1d2733}
.tline .bar .done{position:absolute;left:0;top:0;bottom:0;border-radius:3px;background:#2563eb}
.tline .bar .dt{position:absolute;top:50%;width:12px;height:12px;border-radius:50%;transform:translate(-50%,-50%);box-shadow:0 0 0 2px var(--surface)}
.tline .bar .now{position:absolute;top:-9px;bottom:-9px;width:2px;background:#e9eef4}
.tline .tk{position:absolute;top:13px;font-size:11px;color:var(--text-3);transform:translateX(-50%)}
.tline .lg2{display:flex;gap:12px;font-size:12px;color:var(--text-2)}
.tline .lg2 i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}
.slot{height:58px;border-radius:9px;display:flex;align-items:flex-end;justify-content:space-between;padding:8px 10px;font-size:13px;font-weight:600}
.callout{margin-top:12px;padding:11px 14px;border-radius:10px;font-size:13.5px;line-height:1.45;display:flex;gap:9px;align-items:flex-start}
"""


def clock(t: float) -> str:
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def doc(body: str) -> str:
    return (f'<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Factory Vision · Dashboard TV</title>'
            f'<style>{CSS}{EXTRA}body{{background:var(--bg)}}</style></head><body class="dk">{body}</body></html>')


def page(active: str, crumb: str, body: str, footer: str) -> str:
    prod = APPS[active]
    ic0, name0, col0 = BRAND[prod]
    tabs = "".join(f'<span class="{"on" if key == active else ""}">{I(ic, key == active)}{name}</span>' for ic, name, key in TABS[prod])
    top = (f'<header class="dtop"><span class="dlogo" style="background:{col0}">{I(ic0, True, 20, "#fff")}</span>'
           f'<b class="dname">{name0}</b><span class="dcr">/ Pabrik A · Cikarang</span><span class="dcr on">/ {crumb}</span>'
           f'<div class="right"><span class="dchip live"><span class="dot"></span>LIVE</span>'
           f'<span class="dchip">{I("schedule", size=16)}Shift 1 · 07–15</span><span class="dchip clock tn">10:42:07</span></div></header>')
    nav = (f'<nav class="dtabs">{tabs}<span class="rot">{I("autorenew", size=17)}Berganti otomatis tiap 30 detik {tg(True)}</span></nav>')
    return doc(f'{top}{nav}<main class="dbody">{body}</main>'
               f'<div class="wm" style="left:20px;right:auto">{footer}</div><div class="wm">{WM_POC}</div>')


def camera(src: str, left: str, right: list[str], legend_items: list[tuple] | None = None, h: int = 596) -> str:
    r = "".join(f'<span class="pl">{x}</span>' for x in right)
    lg = ""
    if legend_items:
        lg = '<div class="lgd">' + "".join(f'<span><i style="background:{c}"></i>{n}</span>' for n, c in legend_items) + "</div>"
    return (f'<div class="tvc" style="height:{h}px"><img class="cam" src="../img/{src}">'
            f'<div class="ch1"><span class="pl live"><span class="dot"></span><b>LIVE</b></span><span class="pl">{left}</span></div>'
            f'<div class="ch2">{r}</div>{lg}</div>')


def feed(title: str, rows: list[tuple], right: str) -> str:
    """rows: (thumbnail, severity, title, detail, time)."""
    out = "".join(f'<div class="ev"><img class="th" src="../img/{a}" style="{pos}"><div style="min-width:0">'
                  f'<div class="t1">{t}</div><div class="t2">{d}</div></div>'
                  f'<div class="tm">{tm}<div style="margin-top:6px"><span class="bd {SEV_ID[s][0]}">{I(SEV_ID[s][2], True)}{SEV_ID[s][1]}</span></div></div></div>'
                  for a, pos, s, t, d, tm in rows)
    return card(title, out, icon="notifications", right=right, style="flex:1;min-height:0;overflow:hidden", cb_style="padding-top:2px")


def timeline(title: str, events: list[tuple], total: float, now: float | None = None) -> str:
    """events: (time s, severity)."""
    now = total if now is None else now
    dots = "".join(f'<span class="dt" style="left:{100 * t / total:.2f}%;background:{SEV_COL[s]}"></span>' for t, s in events)
    ticks = "".join(f'<span class="tk" style="left:{100 * t / total:.2f}%">{clock(t)}</span>' for t in range(0, int(total) + 1, 5))
    lg = "".join(f'<span><i style="background:{SEV_COL[k]}"></i>{SEV_ID[k][1]}</span>' for k in ("high", "medium", "low", "info"))
    return (f'<div class="tline"><b>{title}</b><div class="bar"><span class="done" style="width:{100 * now / total:.1f}%"></span>'
            f'{dots}<span class="now" style="left:{100 * now / total:.1f}%"></span>{ticks}</div><div class="lg2">{lg}</div></div>')


def layout(cam: str, kpis: list[str], right: str, feed_html: str, bottom: list[str], tl: str) -> str:
    return (f'<div style="display:grid;grid-template-columns:1100px 1fr;gap:12px;flex:1;min-height:0">'
            f'<div style="display:flex;flex-direction:column;gap:12px;min-height:0">{cam}'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;flex:1;min-height:0">{"".join(bottom)}</div></div>'
            f'<div style="display:flex;flex-direction:column;gap:12px;min-height:0">'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">{"".join(kpis)}</div>{right}{feed_html}</div></div>{tl}')


def jload(path: str):
    return json.loads((P / path).read_text())


# ================================================================== Produce Grading · tomato
USDA = [("Red", "#dc2626"), ("Light Red", "#f87171"), ("Pink", "#f472b6"), ("Turning", "#fb923c"), ("Breakers", "#facc15"),
        ("Green", "#22c55e")]


def tv_tomato() -> str:
    s = jload("11_tomato_ripeness/output/tomato_ripeness_summary.json")
    fps, total = 29.97, s["seconds"]
    tom = s["tomatoes"]
    n = len(tom)
    cnt = {c: sum(1 for t in tom if t["usda_class"] == c) for c, _ in USDA}
    off = n - cnt["Red"]
    kp = [kpi("nutrition", "red", "Tomat terhitung", f"{n}", f"4 line · ≈ {num(s['per_minute'])}/menit (perkiraan dari klip {num(total, 1)} detik)"),
          kpi("verified", "green", "Kelas utama · Red", f"{100 * cnt['Red'] / n:.0f}%", f"{cnt['Red']} dari {n} tomat"),
          kpi("rule", "amber", "Off-colour", f"{100 * off / n:.0f}%", f"{bd('di atas limit 10%', 'red')} sortir ulang atau label Mixed Color"),
          kpi("eco", "green", "Hijau di lot", "0%", "limit 5% (USDA)")]
    comp = card("Grade Composition · kelas warna USDA",
                hbars([(c, cnt[c], col) for c, col in USDA], vmax=n, label_w=90, fmt=lambda v: f"{v} buah")
                + f'<div class="callout" style="background:rgba(245,158,11,.12);color:#fcd34d">{I("warning", True, 18, "#fbbf24")}'
                  f'<span><b>Label lot: Mixed Color</b> · off-colour {100 * off / n:.0f}% &gt; 10%. Sortir ulang {off} tomat '
                  f'Light Red agar lot bisa diberi label Red.</span></div>', icon="stacked_bar_chart",
                right='<span class="mut">USDA 7 CFR 51.1860–51.1861</span>', cb_style="padding-top:10px")
    per = [[sum(1 for t in tom if t["line"] == ln and t["usda_class"] == c) for ln in range(1, 5)] for c in ("Red", "Light Red")]
    byline = card("Per line · Red vs Light Red", vbars([("Red", per[0], "#dc2626"), ("Light Red", per[1], "#f87171")],
                                                        [f"Line {k}" for k in range(1, 5)], 520, 128, stacked=True, bw_max=46, ticks=3)
                  + legend([("Red", "#dc2626"), ("Light Red", "#f87171")]), icon="bar_chart", right="Line 2 paling banyak off-colour")
    # off-colour share as the lot builds up, tomato by tomato
    run, k, share = [], 0, []
    for t in sorted(tom, key=lambda t: t["frame"]):
        k += t["usda_class"] != "Red"
        run.append(t)
        share.append(100 * k / len(run))
    step = max(1, len(share) // 12)
    pts = share[4::step]
    trend = card("Off-colour lot · bertambah per tomat", lines([("Off-colour", pts, "#f59e0b"), ("Limit USDA 10%", [10] * len(pts), "#ef4444", True)],
                                                             [str(5 + i * step) for i in range(len(pts))], 520, 128, hi=30, ticks=3,
                                                             fmt=lambda v: f"{v:.0f}%", every=2)
                 + legend([("Off-colour", "#f59e0b"), ("Limit 10%", "#ef4444")]), icon="monitoring", right="sumbu x: tomat ke-")
    offs = [t for t in tom if t["usda_class"] != "Red"]
    snaps = META["tomato_off"]
    rows = [(x["img"], "", "medium", f"Light Red · Line {x['line']}", f"hue {num(x['hue'], 1)}° · off-colour untuk lot Red",
             clock(x["frame"] / fps)) for x in sorted(snaps, key=lambda x: -x["frame"])[:3]]
    ev = feed("Event Log", rows, f"{len(offs)} kejadian")
    breach = next((t["frame"] / fps for i, t in enumerate(run) if i >= 4 and share[i] > 10), None)
    tl = timeline("Lini masa off-colour", [(t["frame"] / fps, "medium") for t in offs] + ([(breach, "high")] if breach else []), total)
    cam = camera("tomato_cam_133.jpg", "CAM 01 · Line packing tomat · 4 line",
                 [f"{n} terhitung", "Count gate: semua line"], [(c, col) for c, col in USDA])
    return page("tomato", "Line tomat T1–T4",
                layout(cam, kp, comp, ev, [byline, trend], tl),
                "Gambar kamera dan angka: hasil PoC pada rekaman Pexels 8675103 (diputar ulang)")


# ================================================================== Produce Grading · lemon
SWATCH = [(235, 187, 43), (216, 190, 64), (205, 191, 59), (194, 183, 59), (184, 180, 63), (169, 174, 66),
          (148, 164, 59), (135, 146, 60), (109, 124, 58), (79, 101, 50)]
LOT_COL = {"Colour lot 1–3": "#facc15", "Colour lot 4–6": "#84cc16", "Colour lot 7–9": "#15803d", "Out of Grade": "#ef4444"}
LOT_ID = {"Colour lot 1–3": "Lot warna 1–3", "Colour lot 4–6": "Lot warna 4–6", "Colour lot 7–9": "Lot warna 7–9", "Out of Grade": "Out of grade"}


def degree_bars(deg: dict, h: int = 170) -> str:
    top = max(deg.values()) or 1
    cols = []
    for d in range(1, 11):
        v = deg[str(d)]
        r, g, b = SWATCH[d - 1]
        cols.append(f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;justify-content:flex-end">'
                    f'<span class="tn" style="font-size:12.5px;font-weight:600">{v}</span>'
                    f'<div style="width:70%;height:{max(3, h * v / top):.0f}px;border-radius:5px 5px 2px 2px;background:rgb({r},{g},{b})"></div>'
                    f'<span class="mut" style="font-size:12px">{d}</span></div>')
    lots = (f'<div style="display:grid;grid-template-columns:3fr 3fr 3fr 1fr;gap:6px;margin-top:8px;font-size:11.5px;text-align:center">'
            + "".join(f'<div style="border-top:3px solid {c};padding-top:4px" class="mut">{n}</div>'
                      for n, c in [("Lot 1–3", "#facc15"), ("Lot 4–6", "#84cc16"), ("Lot 7–9", "#15803d"), ("10", "#ef4444")]) + "</div>")
    return f'<div style="display:flex;gap:4px;height:{h + 46}px;align-items:flex-end">{"".join(cols)}</div>{lots}'


def tv_lemon() -> str:
    s = jload("12_lime_grading/output/lime_grading_summary.json")
    fps, total = 30.0, s["seconds"]
    lem = s["lemons"]
    n = len(lem)
    lots = {x["name"]: x["count"] for x in s["lots"]}
    main = s["main_lot"]
    kp = [kpi("nutrition", "green", "Lemon terhitung", f"{n}", f"2 chain · ≈ {num(s['per_minute'])}/menit (perkiraan dari klip {num(total, 1)} detik)"),
          kpi("verified", "green", "Sesuai standar warna", "100%", "derajat 1–9 · Extra, Class I, Class II"),
          kpi("inventory_2", "blue", "Lot utama · warna 4–6", f"{100 * lots[main] / n:.0f}%", f"{lots[main]} lemon · maks. 3 derajat per pack"),
          kpi("block", "red", "Out of grade", f"{lots['Out of Grade']}", "tidak ada derajat 10")]
    comp = card("Grade Composition · bagan warna OECD", degree_bars(s["degrees"])
                + '<div class="mut" style="font-size:12px;margin-top:10px">Derajat 1 kuning … 10 hijau tua. Derajat 1–9 boleh untuk Extra, Class I dan II; '
                  'satu pack maksimal 3 derajat berdekatan.</div>', icon="palette", right='<span class="mut">OECD Citrus Fruits · via CBI</span>',
                cb_style="padding-top:10px")
    per = [[sum(1 for t in lem if t["line"] == ln and t["lot"] == lot) for ln in (1, 2)] for lot in list(LOT_COL)[:3]]
    byline = card("Per chain · lot warna", vbars([(LOT_ID[lot], per[k], LOT_COL[lot]) for k, lot in enumerate(list(LOT_COL)[:3])],
                                                  ["Line 1", "Line 2"], 520, 128, stacked=True, bw_max=70, ticks=3)
                  + legend([(LOT_ID[lot], LOT_COL[lot]) for lot in list(LOT_COL)[:3]]), icon="bar_chart",
                  right=f"line 1: {s['per_line'][0]} · line 2: {s['per_line'][1]}")
    # lot share in the last 2 s, sampled every second
    pts, labels = [], []
    for sec in range(2, int(total) + 1):
        win = [t for t in lem if sec - 2 < t["frame"] / fps <= sec]
        if win:
            pts.append([100 * sum(1 for t in win if t["lot"] == lot) / len(win) for lot in list(LOT_COL)[:3]])
            labels.append(f"{sec} dtk")
    trend = card("Colour lot trend · 2 detik terakhir", lines([(LOT_ID[lot], [p[k] for p in pts], LOT_COL[lot]) for k, lot in enumerate(list(LOT_COL)[:3])],
                                                            labels, 520, 128, hi=100, ticks=2, fmt=lambda v: f"{v:.0f}%")
                 + legend([(LOT_ID[lot], LOT_COL[lot]) for lot in list(LOT_COL)[:3]]), icon="monitoring", right="perubahan buah masuk")
    rows = [(x["img"], "", "low", f"{LOT_ID[x['lot']]} · Line {x['line']}", f"derajat {x['degree']} (OECD) · pack terpisah dari lot 4–6",
             clock(x["frame"] / fps)) for x in sorted(META["lemon_off"], key=lambda x: -x["frame"])[:2]]
    outs = [t for t in lem if t["lot"] != main]
    ev = feed("Event Log", rows, f"{len(outs)} di luar lot utama")
    tl = timeline("Di luar lot utama", [(t["frame"] / fps, "low") for t in outs], total)
    cam = camera("lemon_cam_245.jpg", "CAM 02 · Chain sortir lemon · 2 line", [f"{n} terhitung", "Count gate: kedua chain"],
                 [("Lot 1–3", "#facc15"), ("Lot 4–6", "#84cc16"), ("Lot 7–9", "#15803d"), ("10 · out of grade", "#ef4444")])
    return page("lemon", "Chain lemon L1–L2", layout(cam, kp, comp, ev, [byline, trend], tl),
                "Gambar kamera dan angka: hasil PoC pada rekaman Pexels 32953325 (distabilkan)")


# ================================================================== Fill Level
def tv_fill() -> str:
    s = jload("04_bottle_fill_volume/output/fill_inspection_summary.json")
    ser = jload("04_bottle_fill_volume/output/liquid_level_summary.json")["series"]
    fps, total = s["fps"], s["frames"] / s["fps"]
    ml = s["sku_ml_example"]
    rate = s["mean_rate_frac_per_s"] * ml
    end = s["fill_at_clip_end"]
    kp = [kpi("local_drink", "blue", "Level isi · nozzle 1", f"{100 * end:.0f}%", f"≈ {num(end * ml)} mL dari target {num(ml)} mL (contoh SKU)"),
          kpi("water_drop", "cyan", "Flow rate", f'{num(rate)}<small>mL/detik</small>', "rata-rata sejak mulai mengalir"),
          kpi("timer", "amber", "Waktu isi", f'{num(total - s["flow_start_s"], 1)}<small>detik</small>', f"mulai {clock(s['flow_start_s'])}"),
          kpi("hourglass_bottom", "green", "Sisa ke target", f'{num(s["target_expected_at_s"] - total, 1)}<small>detik</small>', "dari flow rate rata-rata")]
    step = 6
    vol = [100 * r["fill_volume_frac"] for r in ser][::step]
    hgt = [100 * r["fill_height_frac"] for r in ser][::step]
    lab = [f"{(i * step) / fps:.0f} dtk" for i in range(len(vol))]
    curve = card("Fill curve · nozzle 1", lines([("Volume terisi", vol, "#3b82f6"), ("Target 100%", [100] * len(vol), "#22c55e", True)],
                                               lab, 740, 210, hi=110, ticks=2, fmt=lambda v: f"{v:.0f}%", every=6, area=True)
                 + legend([("Volume terisi", "#3b82f6"), ("Target 100% · toleransi 98–102%", "#22c55e")]),
                 icon="monitoring", right=f"sekarang {100 * end:.0f}%", cb_style="padding-top:8px")
    rules = [("flag", "#22c55e", "Target", "100% · isi sampai garis leher botol"),
             ("tune", "#22d3ee", "Toleransi", "98–102% saat nozzle berhenti"),
             ("trending_down", "#ef4444", "Di bawah 98%", "reject · underfill · sinyal ke PLC"),
             ("water_drop", "#f59e0b", "Di atas 102%", "pass · dicatat sebagai giveaway")]
    rr = "".join(f'<div class="row" style="gap:10px;padding:7px 0;border-bottom:1px solid var(--hair);font-size:13.5px">{I(ic, True, 18, c)}'
                 f'<b style="width:110px">{a}</b><span class="sec">{b}</span></div>' for ic, c, a, b in rules)
    rule = card("Aturan pass / reject", rr + '<div class="row" style="gap:10px;margin-top:10px;font-size:13px">'
                f'<span class="mut">Siklus ini</span>{bd(f"mengisi · {100 * end:.0f}%", "blue")}'
                '<span class="mut" style="margin-left:auto">keputusan saat nozzle berhenti</span></div>', icon="rule",
                right='<span class="mut">contoh SKU 500 mL</span>')
    hv = card("Tinggi cairan bukan volume", lines([("Tinggi cairan", hgt, "#94a3b8"), ("Volume", vol, "#f59e0b")], lab, 520, 128,
                                                 hi=100, ticks=2, fmt=lambda v: f"{v:.0f}%", every=8)
              + legend([("Tinggi cairan", "#94a3b8"), ("Volume dari bentuk botol", "#f59e0b")])
              + f'<div class="mut" style="font-size:12px;margin-top:4px">Tinggi {100 * s["height_at_clip_end"]:.0f}% = volume {100 * end:.0f}%: '
                'botol menyempit di dasar dan bahu.</div>', icon="straighten")
    tx = {"Bottle in position": ("Botol masuk posisi", "4 botol di bawah nozzle · botol depan diukur", "info", "fill_cam_120.jpg"),
          "Filling started · nozzle 1": ("Mulai mengisi · nozzle 1", "1,4 detik setelah botol masuk posisi", "info", "fill_cam_180.jpg"),
          "Half of target reached": ("Setengah target tercapai", "3,1 detik sejak mulai · 76 mL/detik", "info", "fill_cam_230.jpg"),
          "Clip ends before the cycle does": ("Klip PoC berakhir sebelum siklus selesai", "67% · target diperkirakan 1,9 detik lagi",
                                              "low", "fill_cam_232.jpg")}
    rows = [(tx[e["title"]][3], "object-position:30% 60%", tx[e["title"]][2], tx[e["title"]][0], tx[e["title"]][1], clock(e["t"]))
            for e in reversed(s["events"])][:3]
    ev = feed("Event Log", rows, f"{len(rows)} kejadian")
    tl = timeline("Lini masa siklus", [(e["t"], tx[e["title"]][2]) for e in s["events"]], total)
    cam = camera("fill_cam_232.jpg", "CAM 06 · Filler F1 · nozzle 1", ["Fase: mengisi", f"{100 * end:.0f}% · {num(end * ml)} mL"])
    right = curve
    return page("fill", "Line F1 · nozzle 1", layout(cam, kp, right, ev, [rule, hv], tl),
                "Gambar kamera dan angka: hasil PoC pada rekaman Pexels 8720278 · klip berakhir di 67%, belum ada keputusan pass/reject")


# ================================================================== Pack Count QC · trays
def slot_grid(counts: dict, rows: str, cols: int, colour: str = "#d97706") -> str:
    top = max(counts.values()) if counts else 1
    cells = []
    for r in rows:
        for c in range(1, cols + 1):
            k = f"{r}{c}"
            v = counts.get(k, 0)
            bg = f"rgba(217,119,6,{0.25 + 0.6 * v / top:.2f})" if v else "#1d2733"
            cells.append(f'<div class="slot" style="background:{bg};color:{"#fff" if v else "#64748b"}"><span>{k}</span>'
                         f'<span class="tn" style="font-size:16px">{f"{v}×" if v else "–"}</span></div>')
    return f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:8px">{"".join(cells)}</div>'


def tv_tray() -> str:
    evs = jload("08_pack_completeness/output/analytics/line_qc_events.json")
    sc = jload("08_pack_completeness/output/analytics/line_qc_score.json")
    total = 450 / 30
    short = [e for e in evs if e["kind"] == "tray_short"]
    n = sc["trays_judged"]
    slots = {}
    for e in short:
        k = e["detail"].split("slot ")[1].split(" ")[0]
        slots[k] = slots.get(k, 0) + 1
    kp = [kpi("fact_check", "blue", "Tray diinspeksi", f"{n}", f"{n - len(short)} pass · {len(short)} kurang isi"),
          kpi("production_quantity_limits", "red", "Tray kurang isi", f"{len(short)}", f"{100 * len(short) / n:.0f}% · ditandai reject"),
          kpi("remove_circle", "amber", "Kaleng kurang", f"{len(short)}", f"dari {10 * n} kaleng seharusnya"),
          kpi("speed", "cyan", "Kecepatan line", f'27,5<small>tray/menit</small>', "≈ 275 kaleng/menit, dari jarak antar tray")]
    heat = card("Posisi kaleng yang kosong", f'<div class="row mut" style="justify-content:space-between;font-size:12px;margin-bottom:8px">'
                f'<span>Baris A · belakang</span><span>arah belt →</span></div>'
                + slot_grid(slots, "AB", 5)
                + f'<div class="mut" style="font-size:12px;margin-top:8px">Baris B · depan (dekat kamera)</div>'
                + f'<div class="callout" style="background:rgba(59,130,246,.12);color:#bfdbfe">{I("insights", True, 18, "#60a5fa")}'
                  f'<span><b>{len(short)} kejadian di {len(slots)} posisi berbeda.</b> Belum ada pola satu lane filler; terus dipantau.</span></div>',
                icon="grid_view", right=f"{len(short)} kejadian", cb_style="padding-top:10px")
    cards = []
    for v in list(reversed(sc["verdicts"]))[:6]:
        ok = v["count"] == 10
        dots = "".join(f'<i style="display:inline-block;width:9px;height:9px;border-radius:50%;margin:1px;'
                       f'background:{"#ef4444" if k in v["empty_slots"] else "#22c55e"}"></i>' for k in range(10))
        cards.append(f'<div style="flex:1;border-radius:9px;padding:10px 6px;text-align:center;background:{"#1d2733" if ok else "rgba(239,68,68,.12)"};'
                     f'border-top:3px solid {"#22c55e" if ok else "#ef4444"}"><b style="font-size:13px">#{v["tray"]}</b>'
                     f'<div style="width:62px;margin:8px auto">{dots}</div><b class="tn" style="font-size:16px">{v["count"]}/10</b>'
                     f'<div style="margin-top:6px">{bd("pass", "green") if ok else bd("reject", "red")}</div></div>')
    last = card("Tray terakhir", f'<div style="display:flex;gap:8px">{"".join(cards)}</div>', icon="history", right="6 terbaru · terbaru di kiri")
    secs = list(range(0, int(total) + 1))
    insp = [sum(1 for e in evs if e["t"] <= t) for t in secs]
    sh = [sum(1 for e in short if e["t"] <= t) for t in secs]
    cum = card("Tray diinspeksi, kumulatif", lines([("Diinspeksi", insp, "#3b82f6"), ("Kurang isi", sh, "#ef4444")],
                                                  [f"{t} dtk" for t in secs], 520, 128, hi=8, ticks=2, every=5)
               + legend([("Diinspeksi", "#3b82f6"), ("Kurang isi", "#ef4444")])
               + f'<div class="mut" style="font-size:12px;margin-top:4px">Uji vs data kebenaran: {sc["trays_correct"]}/{n} tray benar · '
                 f'{sc["readings_in_zone"] - sc["readings_wrong"]}/{sc["readings_in_zone"]} pembacaan benar</div>', icon="monitoring")
    snap = {89: "snap_tray_89.jpg", 222: "snap_tray_222.jpg", 413: "snap_tray_413.jpg"}
    rows = [(snap[e["frame"]], "", "high", f"Tray #{e['ref']} kurang 1 kaleng",
             f"9/10 · slot {e['detail'].split('slot ')[1].split(' ')[0]} kosong · ditandai reject", clock(e["t"])) for e in reversed(short)][:3]
    ev = feed("Event Log", rows, f"{len(short)} kejadian")
    tl = timeline("Lini masa", [(e["t"], "high" if e["kind"] == "tray_short" else "info") for e in evs], total)
    cam = camera("tray_cam_440.jpg", "CAM 03 · Ujung line pengisian kaleng", ["Simulasi 3D", f"{n} tray · {len(short)} kurang"],
                 [("lengkap", "#22c55e"), ("kurang isi", "#ef4444"), ("sedang dicek", "#22d3ee")])
    return page("tray", "Line kaleng C1", layout(cam, kp, heat, ev, [last, cum], tl),
                "Gambar kamera dan angka: hasil PoC pada simulasi 3D dengan data kebenaran (7/7 tray benar)")


# ================================================================== Pack Count QC · robot packing station
def tv_packing() -> str:
    evs = jload("08_pack_completeness/output/analytics/packing_qc_events.json")
    sc = jload("08_pack_completeness/output/analytics/packing_qc_score.json")
    total = 857 / 25
    boxes = sc["verdicts"]
    short = [b for b in boxes if b["count"] < 20]
    kp = [kpi("inventory_2", "blue", "Kardus selesai", f"{len(boxes)}", f"{len(boxes) - len(short)} lengkap · {len(short)} kurang isi"),
          kpi("report", "amber", "Empty pick", f"{sc['empty_picks_found']}", "2× feeder gap terdeteksi lebih dulu"),
          kpi("speed", "cyan", "Kecepatan robot", f'94<small>pick/menit</small>', "waktu siklus 0,64 detik (median)"),
          kpi("verified", "green", "Uji vs data kebenaran", f"{sc['boxes_correct']}/{sc['boxes_judged']}", "kardus benar · 2/2 empty pick ditemukan")]
    lab = "ABCD"
    cells = []
    for r in lab:
        for c in range(1, 6):
            k = f"{r}{c}"
            miss = k in ("B2", "C5")
            cells.append(f'<div class="slot" style="height:46px;align-items:center;background:{"rgba(239,68,68,.85)" if miss else "rgba(34,197,94,.16)"};'
                         f'color:{"#fff" if miss else "#86efac"}"><span>{k}</span>{I("cancel" if miss else "check_circle", True, 18)}</div>')
    smap = card("Peta slot · kardus #2", f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:7px">{"".join(cells)}</div>'
                f'<div class="callout" style="background:rgba(239,68,68,.12);color:#fecaca">{I("error", True, 18, "#f87171")}'
                f'<span><b>18/20 · slot B2 dan C5 kosong.</b> Kardus di-hold di outfeed, ditambah 2 item lalu dicek ulang.</span></div>',
                icon="grid_view", right=bd("kurang 2", "red"), cb_style="padding-top:10px")
    rel = {e["ref"]: e for e in evs if e["kind"] in ("box_ok", "box_short")}
    trs = "".join(f'<tr><td><b>#{b["box"]}</b></td><td class="tn">{clock(rel[b["box"]]["t"])}</td><td class="tn">{b["count"]}/20</td>'
                  f'<td>{bd("lengkap", "green") if b["count"] == 20 else bd("kurang", "red")}</td>'
                  f'<td class="sec">{", ".join("B2" if k == 6 else "C5" if k == 14 else str(k) for k in b["empty"]) or "–"}</td>'
                  f'<td class="sec">{"Seal & kirim" if b["count"] == 20 else "Hold, tambah 2 item"}</td></tr>' for b in boxes)
    hist = card("Riwayat kardus", f'<table class="tbl cp"><thead><tr><th>Kardus</th><th>Keluar</th><th>Isi</th><th>Status</th>'
                f'<th>Slot kosong</th><th>Tindakan</th></tr></thead><tbody>{trs}</tbody></table>', icon="list_alt", cb_style="padding:6px 4px 4px")
    chain = [("conveyor_belt", "#3b82f6", "Feeder gap", "stopper kosong", "2×"), ("report", "#f59e0b", "Empty pick", "robot bergerak tanpa produk", "2×"),
             ("production_quantity_limits", "#ef4444", "Kardus kurang isi", "ditahan sebelum disegel", "1×")]
    ch = "".join(f'<div class="row" style="gap:10px;padding:8px 0;border-bottom:1px solid var(--hair)"><span class="it" style="width:30px;height:30px;'
                 f'background:{c}26;color:{c}">{I(ic, True, 17)}</span><div style="flex:1"><b style="font-size:13.5px">{a}</b>'
                 f'<div class="mut" style="font-size:12px">{b}</div></div><b class="tn">{n}</b></div>'
                 + (f'<div style="padding-left:14px;color:var(--text-3)">{I("arrow_downward", size=16)}</div>' if k < 2 else "")
                 for k, (ic, c, a, b, n) in enumerate(chain))
    cause = card("Root cause · sebab dan akibat", ch, icon="account_tree")
    tx = {"box_ok": ("Kardus #{r} lengkap", "20/20 · lanjut ke seal", "info"),
          "feeder_gap": ("Feeder gap", "stopper kosong · slot {s} kardus #{r} berisiko", "low"),
          "missed": ("Empty pick · slot {s}", "robot bergerak tanpa produk · penyebab: feeder gap", "medium"),
          "box_short": ("Kardus #{r} keluar kurang 2", "18/20 · slot B2, C5 kosong · hold & lengkapi", "high")}
    thumb = {101: "packing_cam_290.jpg", 232: "snap_box_284.jpg", 284: "snap_box_284.jpg", 360: "snap_box_412.jpg",
             412: "snap_box_412.jpg", 461: "snap_box_461.jpg", 821: "packing_cam_850.jpg"}

    def slot_of(e):
        d = e["detail"] + " " + e["title"]
        return "B2" if "B2" in d and "C5" not in d else "C5" if "C5" in d and "B2" not in d else ""
    rows = [(thumb[e["frame"]], "", tx[e["kind"]][2], tx[e["kind"]][0].format(r=e["ref"], s=slot_of(e)),
             tx[e["kind"]][1].format(r=e["ref"], s=slot_of(e)), clock(e["t"])) for e in reversed(evs) if e["frame"] <= 461][:2]
    ev = feed("Event Log", rows, f"{len(evs)} kejadian")
    tl = timeline("Lini masa", [(e["t"], e["severity"]) for e in evs], total)
    cam = camera("packing_cam_500.jpg", "CAM 04 · Robot packing station P1", ["Simulasi 3D", "Siklus 0,64 dtk"],
                 [("sedang diisi", "#22d3ee"), ("lengkap", "#22c55e"), ("kurang isi", "#ef4444")])
    return page("packing", "Packing station P1", layout(cam, kp, smap, ev, [hist, cause], tl),
                "Gambar kamera dan angka: hasil PoC pada simulasi 3D dengan data kebenaran (3/3 kardus benar)")


# ================================================================== Parcel Dimensioning
CLS_COL = {"S": "#22d3ee", "M": "#3b82f6", "L": "#a78bfa"}
CLS_ID = {"S": "kecil", "M": "sedang", "L": "besar"}


def tv_parcel() -> str:
    s = jload("03_parcel_dimensioning/output/parcel_dimensioning_summary.json")
    ps = s["parcels"]
    fps, total = 29.97, 511 / 29.97
    vol = sum(p["volume_l"] for p in ps)
    chk = [p for p in ps if p["mark"] == "?"]
    kp = [kpi("package_2", "violet", "Paket terhitung", f"{len(ps)}", f"sama dengan hitungan manual ({s['slit_scan_truth']})"),
          kpi("view_in_ar", "blue", "Volume", f'{num(vol)}<small>L</small>', f"rata-rata {num(vol / len(ps))} L per paket"),
          kpi("speed", "cyan", "Laju bongkar", f'{num(len(ps) / total * 3600, -2 if False else 0)}<small>/jam</small>',
              f"perkiraan dari klip {num(total)} detik"),
          kpi("straighten", "amber", "Manual check", f"{len(chk)}", "ukuran dekat batas kelas")]
    trs = "".join(f'<tr><td><b>#{p["tid"]}</b></td><td class="tn">{p["l_mm"] / 10:.0f} × {p["w_mm"] / 10:.0f} × {p["h_mm"] / 10:.0f} cm</td>'
                  f'<td class="tn">{num(p["volume_l"], 1)} L</td><td class="tn">{num(p["volume_l"] / 6, 1)} kg</td>'
                  f'<td><span class="bd" style="background:{CLS_COL[p["cls"]]}26;color:{CLS_COL[p["cls"]]}">{p["cls"]}{"?" if p["mark"] == "?" else ""}</span></td>'
                  f'<td>{bd("cek manual", "amber") if p["mark"] == "?" else bd("terhitung", "green")}</td></tr>' for p in reversed(ps))
    tbl = card("Paket terukur", f'<table class="tbl cp"><thead><tr><th>Paket</th><th>P × L × T</th><th>Volume</th><th>Berat vol.</th>'
               f'<th>Kelas</th><th>Status</th></tr></thead><tbody>{trs}</tbody></table>', icon="list_alt",
               right='<span class="mut">ukuran akhir sebelum count line</span>', cb_style="padding:6px 4px 4px")
    mix = card("Komposisi ukuran", hbars([(f"{k} · {CLS_ID[k]}", sum(1 for p in ps if p["cls"] == k), CLS_COL[k]) for k in "SML"],
                                         label_w=100, fmt=lambda v: f"{v} paket")
               + "".join(f'<div class="row mut" style="font-size:12px;justify-content:space-between;margin-top:4px"><span>{k} · volume</span>'
                         f'<span class="tn">{num(sum(p["volume_l"] for p in ps if p["cls"] == k))} L</span></div>' for k in "SML")
               + '<div class="mut" style="font-size:12px;margin-top:6px">Batas kelas: sisi terpanjang 30 cm dan 60 cm</div>', icon="category")
    secs = list(range(0, int(total) + 1))
    cum = [sum(p["volume_l"] for p in ps if p["frame"] / fps <= t) for t in secs]
    cv = card("Volume, kumulatif", lines([("Volume", cum, "#a78bfa")], [f"{t} dtk" for t in secs], 520, 128, hi=400, ticks=2,
                                         fmt=lambda v: f"{v:.0f} L", every=5, area=True)
              + '<div class="mut" style="font-size:12px;margin-top:4px">Uji: 8 = hitungan manual 8 · karton uji terbaca 340,5 mm, aslinya 340 mm</div>',
              icon="monitoring", right=f"{num(vol)} L")
    rows = []
    for p in sorted(ps, key=lambda p: -p["frame"])[:2]:
        q = p["mark"] == "?"
        rows.append((f"snap_parcel_{p['tid']}.jpg", "", "medium" if q else "info",
                     f"Paket #{p['tid']} · " + ("cek ukuran manual" if q else f"{CLS_ID[p['cls']]} ({p['cls']})"),
                     f"{p['l_mm'] / 10:.0f}×{p['w_mm'] / 10:.0f}×{p['h_mm'] / 10:.0f} cm · {num(p['volume_l'])} L"
                     + (" · dekat batas S/M" if q else ""), clock(p["frame"] / fps)))
    ev = feed("Event Log", rows, f"{len(ps)} kejadian")
    tl = timeline("Lini masa", [(p["frame"] / fps, "medium" if p["mark"] == "?" else "info") for p in ps], total)
    cam = camera("parcel_cam_511.jpg", "CAM 05 · Belt bongkar truk", [f"{len(ps)} terhitung", "Count line"],
                 [("S · kecil", CLS_COL["S"]), ("M · sedang", CLS_COL["M"]), ("L · besar", CLS_COL["L"]), ("sedang diukur", "#94a3b8")])
    return page("parcel", "Belt outbound OB1", layout(cam, kp, tbl, ev, [mix, cv], tl),
                "Gambar kamera dan angka: hasil PoC pada rekaman Pexels 5370836")


PAGES = [("04_grading_tv_tomato", tv_tomato), ("05_grading_tv_lemon", tv_lemon), ("09_fill_tv", tv_fill),
         ("12_pack_tv_trays", tv_tray), ("13_pack_tv_packing", tv_packing), ("16_parcel_tv", tv_parcel)]
