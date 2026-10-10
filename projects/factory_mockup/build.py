#!/usr/bin/env python3
"""Mockup pages for the Factory Vision deck: four inspection products on one platform.

Each page is plain HTML and CSS (html/NN_name.html) rendered to a 1920x1080 picture (pages/NN_name.png)
by headless Chromium, in the same look as the warehouse mockup (look.py), so the two decks join up.

The camera pictures, the dashboard frames, the snapshots and every figure marked PoC come from the
proof-of-concept videos (assets.py). Plant names, people, daily totals and trends are illustrative,
and every page says so in its corner.

    python factory_mockup/assets.py        # once: pictures from the PoC videos
    python factory_mockup/build.py         # every page
    python factory_mockup/build.py 04 09   # some pages
    python factory_mockup/build.py --icons # refetch the icon subset after using a new icon (network)
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parent
sys.path.insert(0, str(HERE))

from look import (CSS, I, USED, avatar, bd, card, hbars, img, kpi, legend, lines, num, sev, spark,  # noqa: E402
                  status, tg, tile, up, vbars)

HTML, PAGES, IMGD, FONTS = HERE / "html", HERE / "pages", HERE / "img", HERE / "fonts"
META = json.loads((IMGD / "meta.json").read_text())

WM = "Concept mockup · illustrative figures"
WM_POC = "Concept mockup · illustrative figures · camera pictures and PoC figures: output of the proof of concept"
BRAND = "Factory Vision"

# ------------------------------------------------------------------ the four products
PRODUCTS = {
    "grading": ("nutrition", "Produce Grading", "#16a34a", "green",
                "Colour grade of every fruit on the line, against USDA and OECD standards"),
    "fill": ("local_drink", "Fill Level Inspection", "#2563eb", "blue",
             "Fill level of every bottle against target and tolerance"),
    "pack": ("inventory_2", "Pack Count QC", "#d97706", "amber",
             "Item count of every tray and box before it is sealed"),
    "parcel": ("package_2", "Parcel Dimensioning", "#7c3aed", "violet",
               "Size and volume of every parcel on the outbound belt"),
}

S = META["frames"]
TOMATOES = json.loads((P / "11_tomato_ripeness/output/tomato_ripeness_summary.json").read_text())["tomatoes"]


def im(kind: str, k: int = -1, cam: bool = True) -> str:
    f = S[kind][k]
    return f"../img/{kind}_{'cam' if cam else 'dash'}_{f}.jpg"


def history(rows: list[tuple]) -> str:
    """An audit trail: (time, what, who, colour)."""
    return "".join(f'<div class="row" style="gap:12px;padding:8px 0;border-bottom:1px solid var(--hair);font-size:13.5px">'
                   f'<span class="tn mut" style="width:54px;white-space:nowrap">{t}</span><span class="dot" style="color:{c}"></span>'
                   f'<b style="flex:1">{a}</b><span class="mut" style="font-size:12.5px">{b}</span></div>' for t, a, b, c in rows)


def hue_strip(hues: list[tuple], w: int = 1000, h: int = 120) -> str:
    """Each tomato's skin hue on the USDA class bands (hue falls from green on the right to red on the left)."""
    bands = [("Red", 45, 62.1, "#dc2626"), ("Light Red", 62.1, 71.5, "#f87171"), ("Pink", 71.5, 85.7, "#f472b6"),
             ("Turning", 85.7, 101.2, "#fb923c"), ("Breakers", 101.2, 111.2, "#facc15"), ("Green", 111.2, 125, "#22c55e")]
    X = lambda v: 10 + (w - 20) * (v - 45) / 80  # noqa: E731
    out = []
    for name, a, b, c in bands:
        out.append(f'<rect x="{X(a):.1f}" y="22" width="{X(b) - X(a) - 2:.1f}" height="{h - 52}" rx="4" style="fill:{c};opacity:.12"/>')
        out.append(f'<text x="{(X(a) + X(b)) / 2:.1f}" y="14" class="ax" text-anchor="middle">{name}</text>')
        if a > 45:
            out.append(f'<text x="{X(a):.1f}" y="{h - 12}" class="ax" text-anchor="middle">{a:.1f}°</text>')
    lane = {}
    for hue, c in sorted(hues):
        k = round(hue)
        n = lane.get(k, 0)
        lane[k] = n + 1
        out.append(f'<circle cx="{X(hue):.1f}" cy="{30 + (n % 6) * 11}" r="4.5" style="fill:{c};stroke:var(--surface)" stroke-width="1.5"/>')
    return f'<svg width="100%" viewBox="0 0 {w} {h}" style="display:block">{"".join(out)}</svg>'


def dev_bars(vals: list[float], labels: list[str], w: int, h: int, lo: float, hi: float, band: tuple, step: float,
             unit: str = " mL", flag: int | None = None) -> str:
    """Deviation from target per label: bars up (over) and down (under) from a zero line, the tolerance as a band."""
    L, R, T, B = 52, 10, 10, 26
    ph, pw = h - T - B, w - L - R
    Y = lambda v: T + ph * (hi - v) / (hi - lo)  # noqa: E731
    out = [f'<rect x="{L}" y="{Y(band[1]):.1f}" width="{pw}" height="{Y(band[0]) - Y(band[1]):.1f}" style="fill:#16a34a;opacity:.07"/>']
    v = lo
    while v <= hi + 1e-9:
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="{"bl" if abs(v) < 1e-9 else "gl"}"/>')
        out.append(f'<text x="{L - 8}" y="{Y(v) + 4:.1f}" class="ax" text-anchor="end">{v:+.0f}{unit}</text>')
        v += step
    for b, name in zip(band, ("lower limit", "upper limit")):
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{Y(b):.1f}" y2="{Y(b):.1f}" style="stroke:#16a34a" stroke-width="1.2" stroke-dasharray="5 4"/>')
        out.append(f'<text x="{w - R}" y="{Y(b) - 5:.1f}" class="ax" text-anchor="end" style="fill:#15803d">{name} {b:+.0f}{unit}</text>')
    slot = pw / len(vals)
    bw = min(44, slot * .5)
    for i, (x, lab) in enumerate(zip(vals, labels)):
        cx = L + slot * (i + .5)
        col = "#d97706" if flag == i else ("#dc2626" if x < band[0] else "#2563eb")
        y0, y1 = sorted((Y(0), Y(x)))
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{max(1.5, y1 - y0):.1f}" rx="3" style="fill:{col}"/>')
        out.append(f'<text x="{cx:.1f}" y="{(y0 - 6) if x >= 0 else (y1 + 14):.1f}" class="ax" text-anchor="middle" '
                   f'style="fill:var(--text-2);font-weight:600">{x:+.1f}</text>')
        out.append(f'<text x="{cx:.1f}" y="{h - 8}" class="ax" text-anchor="middle">{lab}</text>')
    return f'<svg width="{w}" height="{h}" style="display:block;max-width:100%">{"".join(out)}</svg>'


def poc() -> str:
    return '<span class="bd poc">PoC</span>'


# ------------------------------------------------------------------ shells
NAV = [
    ("Monitor", [("dashboard", "Overview", "overview"), ("videocam", "Live View", "live"),
                 ("live_tv", "TV Dashboard", "tv")]),
    ("Quality", [("report", "Rejects & Events", "events"), ("fact_check", "Lot & Batch Reports", "lots"),
                 ("description", "Shift Reports", "reports")]),
    ("Setup", [("tune", "Product Specs", "specs"), ("photo_camera", "Lines & Cameras", "cameras"),
               ("campaign", "Alerts & Integrations", "alerts")]),
    ("Admin", [("group", "Users & Roles", "users"), ("factory", "Plants", "plants"),
               ("receipt_long", "Subscription", "billing")]),
]


def sidebar(active: str, product: str, user: tuple) -> str:
    icon, name, colour, tone, _ = PRODUCTS[product]
    groups = []
    for title, items in NAV:
        rows = []
        for ic, label, key in items:
            extra = ""
            if key == "events":
                extra = '<span class="nb">5</span>'
            if key == "tv":
                extra = I("open_in_new", size=16).replace('class="i"', 'class="i ext"')
            rows.append(f'<div class="ni{" on" if key == active else ""}">{I(ic, key == active)}{label}{extra}</div>')
        groups.append(f'<div class="ng"><div class="t">{title}</div>{"".join(rows)}</div>')
    switch = "".join(
        f'<div class="row" style="gap:9px;padding:6px 8px;border-radius:7px;font-size:12.5px;'
        f'{"background:rgba(255,255,255,.07);color:#fff;font-weight:600" if k == product else "color:#8b99ad"}">'
        f'<span style="width:22px;height:22px;border-radius:6px;display:grid;place-items:center;background:{v[2]}">'
        f'{I(v[0], True, 15, "#fff")}</span>{v[1]}</div>' for k, v in PRODUCTS.items())
    uname, role, utone = user
    return (f'<aside class="side"><div class="brand"><span class="logo">{I("precision_manufacturing", True, 21)}</span>'
            f'<div><b>{BRAND}</b><small>Web App</small></div></div>'
            f'<div class="ng" style="margin-top:8px"><div class="t">Products</div>{switch}</div>'
            f'{"".join(groups)}<div class="sfoot">{avatar(uname, 34)}<div class="grow"><b>{uname}</b>{bd(role, utone)}</div>'
            f'{I("unfold_more", size=18, color="#5f6f86")}</div></aside>')


def topbar(product: str, site=("Plant A · Cikarang", "PT Contoh Industri"), shift="Shift 1 · 07–15 · 10:42") -> str:
    icon, name, colour, tone, _ = PRODUCTS[product]
    return (f'<header class="top"><div class="sel">{I("factory", size=20, color="var(--text-2)")}'
            f'<div><b>{site[0]}</b><small>{site[1]}</small></div>{I("expand_more", size=18, color="var(--text-3)")}</div>'
            f'<span class="chip" style="color:{colour};border-color:{colour}33;background:{colour}10">{I(icon, True, 16)}{name}</span>'
            f'<div class="search" style="width:440px">{I("search", size=19)}<span class="ell">Search lot, SKU, line, reject…</span>'
            f'<span class="kbd">Ctrl K</span></div>'
            f'<div class="right"><span class="chip ok"><span class="dot"></span>All lines online</span>'
            f'<span class="chip">{I("schedule", size=16)}{shift}</span><span class="iconbtn">{I("notifications")}<span class="nd"></span></span>'
            f'<span class="iconbtn">{I("help")}</span>{avatar("Dewi Lestari", 34)}</div></header>')


def doc(body: str, cls: str = "", extra_css: str = "") -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{BRAND} · mockup</title>'
            f'<style>{CSS}{extra_css}</style></head><body class="{cls}">{body}</body></html>')


def app(product: str, active: str, body: str, *, wm: str = WM_POC, user=("Dewi Lestari", "QC Manager", "green")) -> str:
    return doc(f'<div class="app">{sidebar(active, product, user)}<div class="main">{topbar(product)}'
               f'<main class="content">{body}</main></div></div><div class="wm">{wm}</div>')


def ph(title: str, sub: str, acts: str = "", crumb: str = "") -> str:
    c = f'<div class="crumb">{crumb}</div>' if crumb else ""
    return f'<div class="ph"><div>{c}<h1>{title}</h1><p>{sub}</p></div><div class="acts">{acts}</div></div>'


def btn(label: str, icon: str | None = None, kind: str = "") -> str:
    return f'<span class="btn {kind}">{I(icon) if icon else ""}{label}</span>'


def slide(eyebrow: str, title: str, lead: str, body: str, *, wm: str = WM) -> str:
    head = (f'<div class="shead"><div><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p class="lead">{lead}</p></div>'
            f'<div class="brandmini"><span class="logo" style="width:32px;height:32px">{I("precision_manufacturing", True, 19)}</span>'
            f'{BRAND}</div></div>')
    return doc(f'<div class="slide">{head}{body}</div><div class="wm">{wm}</div>')


def grid(cols: str, items: list[str], gap: int = 18, style: str = "") -> str:
    return f'<div style="display:grid;grid-template-columns:{cols};gap:{gap}px;{style}">{"".join(items)}</div>'


def annotated(product: str, src: str, title: str, sub: str, view: str, notes: list[tuple], foot: str) -> str:
    """A frame of the product's TV dashboard video, numbered, with what each part is for."""
    s = 1584 / 1920
    icon, name, colour, _, _ = PRODUCTS[product]
    marks = "".join(f'<span class="mk" style="left:{24 + x * s - 15:.0f}px;top:{96 + y * s - 15:.0f}px">{k}</span>'
                    for k, (x, y, _, _) in enumerate(notes, 1))
    items = "".join(f'<div style="display:flex;gap:12px"><span class="mk" style="position:static;flex:none">{k}</span><div>'
                    f'<b style="font-size:15px;color:#e9eef4">{a}</b>'
                    f'<div style="color:#9ba9b8;font-size:13px;margin-top:3px;line-height:1.45">{b}</div></div></div>'
                    for k, (_, _, a, b) in enumerate(notes, 1))
    css = (".mk{position:absolute;width:30px;height:30px;border-radius:50%;background:#3b82f6;color:#fff;font-weight:700;font-size:15px;"
           "display:grid;place-items:center;box-shadow:0 0 0 3px #05080c,0 4px 12px rgba(0,0,0,.5);z-index:3}")
    body = (f'<div style="position:absolute;left:24px;top:22px;right:24px;display:flex;align-items:center;gap:14px">'
            f'<span class="bd" style="background:{colour}33;color:#e9eef4;height:26px">{I(icon, True)}{name.upper()} · TV DASHBOARD</span>'
            f'<b style="font-size:22px;color:#e9eef4">{title}</b><span style="color:#9ba9b8;font-size:15px">{sub}</span>'
            f'<span style="margin-left:auto;color:#9ba9b8;font-size:13px">{view}</span></div>'
            f'<img src="{src}" style="position:absolute;left:24px;top:96px;width:1584px;height:891px;border-radius:10px;box-shadow:0 0 0 1px #232f3d">'
            f'{marks}<div style="position:absolute;left:1640px;top:96px;width:256px;display:flex;flex-direction:column;gap:18px">{items}</div>'
            f'<div style="position:absolute;left:24px;top:1003px;color:#9ba9b8;font-size:13px">{foot}</div>')
    return doc(body + f'<div class="wm" style="color:#657485">{WM_POC}</div>', cls="dk", extra_css=css + "body{background:#05080c}")


# ------------------------------------------------------------------ shared tables
ROLES = [
    ("shield_person", "Super Admin", "violet", "Vendor team", "All customers · platform"),
    ("admin_panel_settings", "Plant Admin", "blue", "Plant manager, IT", "All lines of the plant"),
    ("verified", "QC Manager", "green", "Quality assurance", "Assigned products & lines"),
    ("engineering", "Line Supervisor", "amber", "Production / shift lead", "Assigned lines"),
    ("visibility", "Viewer", "slate", "Management, auditor", "View only"),
]


# ================================================================== slides: platform
def p00_product_map() -> str:
    feats = {
        "grading": ["Colour class per fruit, per line", "USDA tomato classes · OECD lemon chart", "Lot check vs tolerance",
                    "Off-colour alerts & lot hold"],
        "fill": ["Fill level per bottle, per nozzle", "Target & tolerance per SKU", "Underfill reject signal",
                 "Giveaway (overfill) tracking"],
        "pack": ["Item count per tray / box", "Empty slot position", "Short pack hold & rework",
                 "Feeder gap / empty pick root cause"],
        "parcel": ["L × W × H & volume per parcel", "Size class S / M / L", "Volumetric weight",
                   "Manual check for near-boundary sizes"],
    }
    proof = {"grading": "41 tomatoes · 87 lemons graded; blind check 75/78 and 18/24 (±1 degree)",
             "fill": "fill level measured every frame, 67% at clip end; flow rate and time to target",
             "pack": "7/7 trays and 3/3 boxes judged right vs ground truth (3D simulation)",
             "parcel": "8/8 parcels counted; test carton read 340.5 mm vs 340 mm"}
    pics = {"grading": [("tomato", "Tomato · USDA"), ("lemon", "Lemon · OECD")], "fill": [("fill", "Bottle filler")],
            "pack": [("tray", "Can trays"), ("packing", "Robot packing station")], "parcel": [("parcel", "Outbound belt")]}
    cards = []
    for k, (icon, name, colour, tone, desc) in PRODUCTS.items():
        ps = pics[k]
        h = 300 if len(ps) == 1 else 146
        pic = "".join(tile(im(kind, 1), lab, colour, style=f"height:{h}px") for kind, lab in ps)
        cards.append(
            f'<section class="card" style="padding:20px 22px;gap:12px"><div class="row" style="gap:12px">'
            f'<span class="it {tone}" style="width:46px;height:46px">{I(icon, True, 25)}</span>'
            f'<div class="grow"><b style="font-size:18px;display:block">{name}</b><span class="mut" style="font-size:12.5px">{desc}</span></div></div>'
            + f'<div style="display:flex;flex-direction:column;gap:8px;margin:4px 0">{pic}</div>'
            + "".join(f'<div class="row" style="gap:9px;font-size:13.5px">{I("check_circle", True, 18, colour)}{f}</div>' for f in feats[k])
            + f'<div style="margin-top:auto;padding-top:12px;border-top:1px solid var(--hair);font-size:12.5px" class="sec">'
              f'{poc()} {proof[k]}</div></section>')
    shared = [("web", "Web App", "Overview · Live View · Rejects · Lot reports · Specs · Users"),
              ("live_tv", "TV Dashboard", "one screen per line, for the production floor"),
              ("smartphone", "Mobile alerts", "WhatsApp, push, email to the right person"),
              ("hub", "Integrations", "PLC reject signal · MES · ERP · WMS · API"),
              ("badge", "5 roles", "Super Admin · Plant Admin · QC Manager · Line Supervisor · Viewer")]
    sh = "".join(f'<div class="row" style="gap:12px;flex:1"><span class="it slate">{I(ic, True, 19)}</span><div>'
                 f'<b style="font-size:14px;display:block">{a}</b><span class="mut" style="font-size:12px">{b}</span></div></div>'
                 for ic, a, b in shared)
    flow = [("videocam", "Camera on the line", "existing CCTV or industrial camera"),
            ("memory", "Edge AI box", "detect, track, measure · < 1 s"),
            ("cloud", "Factory Vision cloud", "specs, lots, evidence, reports"),
            ("devices", "Web · TV · phone · PLC", "the right action, right away")]
    fl = "".join(f'<div class="row" style="gap:10px;flex:1"><span class="it blue">{I(ic, True, 19)}</span><div><b style="font-size:13.5px;display:block">{a}</b>'
                 f'<span class="mut" style="font-size:12px">{b}</span></div></div>'
                 + (I("arrow_forward", size=20, color="var(--text-3)") if k < 3 else "") for k, (ic, a, b) in enumerate(flow))
    body = (grid("repeat(4,1fr)", cards, 20, "flex:1;min-height:0")
            + f'<section class="card" style="padding:16px 22px;flex-direction:row;align-items:center;gap:18px">'
              f'<b style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);white-space:nowrap">Shared platform</b>{sh}</section>'
            + f'<section class="card" style="padding:14px 22px;flex-direction:row;align-items:center;gap:16px">'
              f'<b style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);white-space:nowrap">Data flow</b>{fl}</section>')
    return slide("Product map", "Four inspection products, one platform",
                 "Each product is sold on its own, per line. They share the web app, TV dashboard, alerts, users and integrations, "
                 f"so a plant can start with one and add the next. {poc()} = shown working in the proof of concept.", body)


def p01_roles() -> str:
    cards = "".join(
        f'<section class="card" style="padding:16px 18px;gap:8px"><div class="row"><span class="it {r[2]}">{I(r[0], True, 19)}</span>'
        f'<b style="font-size:16px">{r[1]}</b></div><div class="sec" style="font-size:13px">{r[3]}</div>'
        f'<div class="row mut" style="font-size:12.5px;gap:6px">{I("location_on", size=16)}{r[4]}</div></section>' for r in ROLES)
    F, E, V, N = "full", "edit", "view", "none"
    cap = [
        ("Live View & TV Dashboard", [V + "*", F, F, F, V]),
        ("Review rejects & events", [N, F, F, E, V]),
        ("Hold, release or re-sort a lot", [N, F, F, E, N]),
        ("Override a reject (with reason)", [N, F, F, N, N]),
        ("Export evidence & lot certificate", [N, F, F, N, V]),
        ("Shift & lot reports", [N, F, F, V, V]),
        ("Product specs, grade standards, tolerances", [N, F, E, N, N]),
        ("Lines, cameras & calibration", [E + "*", F, V, V, N]),
        ("Alerts & escalation", [N, F, E, N, N]),
        ("PLC / MES / ERP integration & API", [N, F, N, N, N]),
        ("Users, roles & SSO", [E, F, N, N, N]),
        ("Subscription & invoices", [F, V, N, N, N]),
        ("Customers, products enabled, edge & AI model releases", [F, N, N, N, N]),
        ("Audit log", [F, V, N, N, N]),
    ]
    mark = {F: (I("check_circle", True, 20, "#0f172a"), "Manage"), E: (I("edit_square", False, 19, "#0f172a"), "Limited"),
            V: (I("visibility", False, 19, "#64748b"), "View"), N: ('<span style="color:#cbd5e1;font-size:18px">—</span>', "")}
    head = "".join(f'<th style="text-align:center;width:170px">{bd(r[1], r[2], r[0])}</th>' for r in ROLES)
    rows = []
    for nm, cells in cap:
        tds = []
        for c in cells:
            m, label = mark[c.rstrip("*")]
            tds.append(f'<td style="text-align:center"><span class="row" style="justify-content:center;gap:6px">{m}'
                       f'<span class="mut" style="font-size:12px">{label}{"*" if c.endswith("*") else ""}</span></span></td>')
        rows.append(f'<tr><td style="font-weight:500">{nm}</td>{"".join(tds)}</tr>')
    table = (f'<section class="card" style="flex:1;min-height:0"><table class="tbl"><thead><tr><th>Capability</th>{head}</tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></section>')
    notes = (f'<div class="row" style="gap:28px;font-size:13px;color:var(--text-2)">'
             f'<span class="row" style="gap:6px">{mark[F][0]} Manage = create, change, delete</span>'
             f'<span class="row" style="gap:6px">{mark[E][0]} Limited = own lines only / needs approval</span>'
             f'<span class="row" style="gap:6px">{mark[V][0]} View only</span>'
             f'<span class="row" style="gap:6px">{I("lock", True, 18, "#6d28d9")}* Super Admin only with the Plant Admin’s permission, time-limited and in the audit log</span></div>')
    body = f'{grid("repeat(5,1fr)", [cards], 16)}{table}{notes}'
    body = f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px">{cards}</div>{table}{notes}'
    return slide("Roles & access", "The QC Manager owns the standard, the line acts on it",
                 "Role-based access per plant and per line. Each customer’s data is kept apart (multi-tenant); "
                 "the vendor cannot see a plant’s cameras without a permission that is logged.", body)


# ================================================================== Produce Grading
def p02_grading_overview() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("nutrition", "green", "Fruit graded today", "41,860", f'{up("6% vs yesterday")}<span>tomato 4 lines · lemon 2 lines</span>'),
        kpi("verified", "green", "In main colour class", "86%", "lots released at first check"),
        kpi("pause_circle", "amber", "Lots on hold", "2", f'{bd("1 re-sort", "red")}{bd("1 Mixed Color", "violet")}'),
        kpi("block", "red", "Out of grade", "0.4%", "rejected at the line · lemon colour 10"),
    ])
    lines4 = ["Line T1", "Line T2", "Line T3", "Line T4"]
    tom = vbars([("Red", [88, 64, 85, 100], "#dc2626"), ("Light Red", [12, 36, 15, 0], "#f87171"),
                 ("Pink / other", [0, 0, 0, 0], "#f472b6")], lines4, 520, 270, stacked=True, ymax=100,
                fmt=lambda v: f"{v:.0f}%", bw_max=56)
    lem = vbars([("Lot 1–3", [26, 23], "#facc15"), ("Lot 4–6", [74, 65], "#84cc16"), ("Lot 7–9", [0, 12], "#15803d")],
                ["Line L1", "Line L2"], 330, 270, stacked=True, ymax=100, fmt=lambda v: f"{v:.0f}%", bw_max=64)
    mix = card("Grade mix by line", grid("1fr 340px", [
        f'<div><div class="sect">Tomato · USDA colour class</div>{tom}'
        f'{legend([("Red", "#dc2626"), ("Light Red", "#f87171"), ("Pink / other", "#f472b6")])}</div>',
        f'<div><div class="sect">Lemon · OECD colour lot</div>{lem}'
        f'{legend([("Lot 1–3", "#facc15"), ("Lot 4–6", "#84cc16"), ("Lot 7–9", "#15803d")])}</div>'], 28),
        icon="stacked_bar_chart", right="share of fruit graded this shift")
    lots = [("T-1012-07", "Tomato", "T1–T4", "9,840", "Red", "17%", "Mixed Color", "Re-sort or label"),
            ("T-1012-06", "Tomato", "T1–T4", "10,220", "Red", "6%", "Released", "—"),
            ("L-1012-04", "Lemon", "L1–L2", "11,310", "Lot 4–6", "31%", "On hold", "Pack apart"),
            ("L-1012-03", "Lemon", "L1–L2", "10,490", "Lot 4–6", "8%", "Released", "—")]
    rows = "".join(f'<tr><td><b>{a}</b></td><td>{b}</td><td class="mut">{c}</td><td class="tn">{d}</td><td>{e}</td>'
                   f'<td class="tn">{f}</td><td>{status(g)}</td><td class="sec">{h}</td></tr>' for a, b, c, d, e, f, g, h in lots)
    lot = card("Lots this shift", f'<table class="tbl cp"><thead><tr><th>Lot</th><th>Product</th><th>Lines</th><th>Fruit</th>'
               f'<th>Main class</th><th>Off-colour</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table>',
               icon="fact_check", right='<span class="lnk">All lots ' + I("chevron_right", size=16) + '</span>', cb_style="padding:10px 6px 6px")
    live = card("Live lines", grid("1fr 1fr", [tile(im("tomato"), "T1–T4 · Tomato", "#dc2626", "41 counted"),
                                               tile(im("lemon"), "L1–L2 · Lemon", "#84cc16", "87 counted")], 10, "height:200px"),
                icon="videocam", right='<span class="lnk">Live View ' + I("chevron_right", size=16) + '</span>')
    trend = card("Off-colour share by hour", lines([("Tomato", [4, 5, 6, 9, 12, 17, 8, 6], "#dc2626"),
                                                    ("Lemon", [7, 8, 6, 9, 31, 12, 9, 8], "#65a30d")],
                                                   ["07", "08", "09", "10", "11", "12", "13", "14"], 560, 262, hi=40,
                                                   ref=("lot limit 10%", 10), fmt=lambda v: f"{v:.0f}%")
                 + legend([("Tomato", "#dc2626"), ("Lemon", "#65a30d")]),
                 icon="monitoring", right="limit per lot")
    body = (ph("Overview · Produce Grading", "Today · Shift 1 · tomato and lemon lines",
               btn("Export", "download") + btn("Open TV Dashboard", "live_tv", "pri"))
            + k + grid("1fr 620px", [mix, trend]) + grid("1fr 620px", [lot, live]))
    return app("grading", "overview", body)


def p03_grading_live() -> str:
    big = tile(im("tomato", 1), "LIVE · T1–T4 · Tomato packing line · CAM 01", "#ef4444", style="aspect-ratio:16/9")
    idle = ('<div class="tile" style="aspect-ratio:16/9;background:#111821;display:grid;place-items:center">'
            '<span class="tl"><span class="dot" style="color:#94a3b8"></span>{}</span>'
            '<div style="text-align:center;color:#8b99ad;font-size:12.5px">{}<div style="margin-top:6px">{}</div></div></div>')
    small = [tile(im("lemon", 2), "LIVE · L1–L2 · Lemon chains · CAM 02", "#ef4444", style="aspect-ratio:16/9"),
             idle.format("T5–T8 · Tomato line 2 · CAM 03", I("sync", size=30, color="#8b99ad"), "Line stopped · SKU changeover"),
             idle.format("L3–L4 · Lemon line 2 · CAM 04", I("schedule", size=30, color="#8b99ad"), "Line runs on shift 2 only")]
    wall = (f'<div style="display:flex;flex-direction:column;gap:10px">{big}'
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">{"".join(small)}</div></div>')
    snaps = "".join(f'<div style="text-align:center"><img class="thumb" src="../img/{s["img"]}" style="width:86px;height:86px">'
                    f'<div style="font-size:11.5px;margin-top:4px" class="sec">T{s["line"]} · {s["hue"]:.0f}°</div></div>'
                    for s in META["tomato_off"][:6])
    cls = [("Red", 34, "#dc2626"), ("Light Red", 7, "#f87171"), ("Pink", 0, "#f472b6"), ("Turning", 0, "#fb923c"),
           ("Breakers", 0, "#facc15"), ("Green", 0, "#22c55e")]
    side = (card("Current lot · T-1012-07", f'<div class="row" style="gap:8px;margin-bottom:10px">{status("Mixed Color")}'
                 f'{bd("off-colour 17% > 10%", "amber", "warning")}</div>'
                 + hbars([(a, b, c) for a, b, c in cls], vmax=41, label_w=90)
                 + f'<div class="mut" style="font-size:12px;margin-top:8px">{poc()} 41 tomatoes counted at the gate · USDA 7 CFR 51.1860</div>',
                 icon="fact_check", right=status("Running"))
            + card("Off-colour fruit · this lot", f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">{snaps}</div>',
                   icon="photo_library", right="Light Red")
            + card("", f'<div class="col" style="gap:8px">{btn("Hold lot", "pause_circle", "pri")}{btn("Re-sort on line T2", "sync")}'
                       f'{btn("Release as Mixed Color", "label")}</div>'))
    body = (ph("Live View", "AI overlay on every camera: class per fruit, count gate, line number",
               '<span class="seg"><span>' + I("crop_square") + '1</span><span>' + I("grid_view") + '4</span><span class="on">'
               + I("view_quilt") + '1+3</span></span>' + btn("Full screen", "fullscreen"))
            + f'<div style="display:grid;grid-template-columns:1fr 420px;gap:18px;flex:1;min-height:0">'
              f'<div style="min-height:0">{wall}</div><div class="col" style="gap:14px">{side}</div></div>')
    return app("grading", "live", body, user=("Andi Wijaya", "Line Supervisor", "amber"))


def p04_tv_tomato() -> str:
    return annotated("grading", im("tomato", 2, cam=False), "Tomato · USDA colour classes", "4 lines, one count gate",
                     "View 1 of 2 · rotates every 30 s", [
                         (640, 112, "Live camera with AI", "Every tomato boxed in its USDA class colour; counted fruit labelled with line and class."),
                         (40, 465, "Count gate", "One line across all 4 lines; each tomato counted once, its line read where it crosses."),
                         (1330, 90, "Lot KPIs", "Counted, main class share, off-colour vs the 10% limit, green vs the 5% limit."),
                         (1330, 290, "Grade Composition", "Six USDA classes and the lot label check: release as Red, re-sort, or Mixed Color."),
                         (1330, 620, "Event Log", "Every off-colour tomato with a snapshot, line and hue."),
                         (40, 820, "Off-colour trend", "The lot’s off-colour share building up against the 10% limit."),
                         (680, 820, "Colour spread", "Each tomato’s hue against the USDA class bounds.")],
                     "Frame from the PoC video (real Pexels footage, replayed). In the product: one TV per line, live data from the edge box.")


def p05_tv_lemon() -> str:
    return annotated("grading", im("lemon", 2, cam=False), "Lemon · OECD colour chart", "2 sorting chains",
                     "View 2 of 2 · rotates every 30 s", [
                         (640, 112, "Live camera with AI", "Every lemon boxed in its colour lot; counted fruit labelled with line and colour degree."),
                         (40, 465, "Count gate", "One line across both chains."),
                         (1330, 90, "Standard KPIs", "Counted, within colour standard (degree 1–9), main lot share, out of grade."),
                         (1330, 290, "OECD chart composition", "Lemons per colour degree 1–10 in the chart’s own colours, lots of 3 degrees."),
                         (1330, 620, "Event Log", "Every lemon outside the main lot, to pack apart; degree 10 = reject."),
                         (40, 820, "Colour lot trend", "Lot share over the last 2 s: a change in incoming fruit shows at once."),
                         (680, 820, "Degree spread", "Each lemon on the OECD 1–10 scale.")],
                     "Frame from the PoC video (real Pexels footage, stabilised). OECD colour chart via CBI market-entry guide for lemons.")


def p06_grading_lot() -> str:
    cls = [("Red", 34, "#dc2626", "> 90% red"), ("Light Red", 7, "#f87171", "> 60% pinkish-red, ≤ 90% red"),
           ("Pink", 0, "#f472b6", "30–60% pink or red"), ("Turning", 0, "#fb923c", "10–30% changed from green"),
           ("Breakers", 0, "#facc15", "≤ 10% changed from green"), ("Green", 0, "#22c55e", "fully green")]
    rows = "".join(f'<tr><td><span class="row" style="gap:8px"><i class="sw" style="background:{c}"></i><b>{a}</b></span></td>'
                   f'<td class="sec">{d}</td><td class="tn" style="text-align:right"><b>{b}</b></td>'
                   f'<td class="tn mut" style="text-align:right">{100 * b / 41:.0f}%</td></tr>' for a, b, c, d in cls)
    comp = card("USDA colour class", f'<table class="tbl cp"><thead><tr><th>Class</th><th>Surface (7 CFR 51.1860)</th>'
                f'<th style="text-align:right">Fruit</th><th style="text-align:right">Share</th></tr></thead><tbody>{rows}</tbody></table>',
                icon="category", right=poc(), cb_style="padding:10px 6px 6px")
    check = card("Lot check · USDA 7 CFR 51.1861", f'''
      <div class="kv"><span>Lot label asked</span><b>Red</b>
      <span>Off-colour</span><span><b class="tn" style="color:#b42318">17%</b> <span class="mut">· limit 10%</span></span>
      <span>Green in lot</span><span><b class="tn">0%</b> <span class="mut">· limit 5%</span></span>
      <span>Verdict</span><span>{status("Mixed Color")}</span></div>
      <div style="margin-top:14px;padding:12px 14px;border-radius:10px;background:#fffaeb;font-size:13.5px;line-height:1.5">
      {I("lightbulb", True, 18, "#b54708")} <b>Re-sort 7 Light Red tomatoes</b> (4 on line T2) and the lot can be labelled
      <b>Red</b>. Line T2 carried the most off-colour fruit this lot.</div>
      <div class="row" style="gap:10px;margin-top:14px">{btn("Re-sort & re-check", "sync", "pri")}{btn("Release as Mixed Color", "label")}</div>''',
                 icon="rule", right=status("On hold"))
    per = vbars([("Red", [7, 5, 11, 11], "#dc2626"), ("Light Red", [1, 4, 2, 0], "#f87171")],
                ["Line T1", "Line T2", "Line T3", "Line T4"], 560, 220, stacked=True, bw_max=60,
                tip=(1, 30, 20, "Line T2 · 9 tomatoes"))
    perc = card("By line", per + legend([("Red", "#dc2626"), ("Light Red", "#f87171")]), icon="stacked_bar_chart", right=poc())
    snaps = "".join(f'<div><img class="thumb" src="../img/{s["img"]}" style="width:100%;height:118px">'
                    f'<div class="row" style="justify-content:space-between;margin-top:5px;font-size:12px"><b>Line T{s["line"]}</b>'
                    f'<span class="mut tn">hue {s["hue"]:.1f}°</span></div></div>' for s in META["tomato_off"][:6])
    ev = card("Evidence · off-colour fruit", f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px">{snaps}</div>',
              icon="photo_library", right="Light Red · counted at the gate")
    audit = card("How far to trust it", f'''<div class="col" style="gap:9px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}<span><b>75 of 78</b> tomatoes match a blind check by eye; the rest one class apart</span></div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}<span>Class bounds from published colorimeter data, not tuned to this line</span></div>
      <div class="row" style="gap:8px">{I("info", True, 18, "#2563eb")}<span>Colour checked with a reference card at each shift start</span></div></div>''',
                 icon="verified", right=poc())
    col = {"Red": "#dc2626", "Light Red": "#f87171"}
    spread = card("Skin hue of every tomato in the lot", hue_strip([(t["hue"], col.get(t["usda_class"], "#f472b6")) for t in TOMATOES])
                  + '<div class="mut" style="font-size:12px;margin-top:4px">One dot per tomato counted at the gate · '
                    'CIELAB hue angle of the skin · USDA class bounds</div>', icon="scatter_plot", right=poc())
    hist = card("Lot history", history([
        ("10:21", "Lot opened", "system · pallet T-1012-07", "#64748b"),
        ("10:38", "Off-colour above 10%", "system · alert to QC Manager", "#f59e0b"),
        ("10:42", "Lot closed · on hold", "system · 41 fruit", "#f59e0b"),
        ("10:47", "Re-sort assigned · line T2", "Dewi Lestari · QC Manager", "#2563eb"),
        ("—", "Re-check after re-sort", "waiting", "#cbd5e1")]), icon="history")
    body = (ph("Lot T-1012-07 · Tomato", "Lines T1–T4 · Shift 1 · 10:21–10:42 · 41 tomatoes counted (PoC clip)",
               btn("Export lot certificate (PDF)", "picture_as_pdf") + btn("Send to customer QA", "send"),
               crumb=f'Lot & Batch Reports {I("chevron_right", size=16)} T-1012-07')
            + grid("1fr 1fr 560px", [comp, check, perc]) + grid("1fr 520px", [ev, audit])
            + grid("1fr 520px", [spread, hist]))
    return app("grading", "lots", body)


def p07_grading_standards() -> str:
    lib = [("USDA tomato colour classes", "7 CFR 51.1860–51.1861", "Lines T1–T4", "Active"),
           ("OECD lemon colour chart", "OECD Citrus Fruits · via CBI", "Lines L1–L2", "Active"),
           ("USDA peach colour (U.S. Fancy ≥ ⅓ red)", "7 CFR 51.1210–51.1214", "—", "Draft"),
           ("Customer spec · Supermarket X", "buyer specification", "—", "Draft")]
    rows = "".join(f'<tr class="{"on" if k == 0 else ""}"><td><b>{a}</b><div class="mut" style="font-size:12px">{b}</div></td>'
                   f'<td class="sec">{c}</td><td>{status(d)}</td></tr>' for k, (a, b, c, d) in enumerate(lib))
    left = card("Grade standards", f'<table class="tbl"><thead><tr><th>Standard</th><th>Used on</th><th>Status</th></tr></thead>'
                f'<tbody>{rows}</tbody></table>', icon="menu_book", right=btn("New standard", "add", "sm"), cb_style="padding:10px 6px 6px")
    cls = [("Red", "< 62.1°", "#dc2626"), ("Light Red", "62.1–71.5°", "#f87171"), ("Pink", "71.5–85.7°", "#f472b6"),
           ("Turning", "85.7–101.2°", "#fb923c"), ("Breakers", "101.2–111.2°", "#facc15"), ("Green", "≥ 111.2°", "#22c55e")]
    crow = "".join(f'<div class="row" style="gap:10px;padding:7px 0;border-bottom:1px solid var(--hair)"><i class="sw" style="background:{c};width:14px;height:14px"></i>'
                   f'<b style="width:110px">{a}</b><span class="tn sec">{b}</span></div>' for a, b, c in cls)
    detail = card("USDA tomato colour classes", f'''
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
        <div><div class="sect">Classes · skin hue angle (CIELAB)</div>{crow}
          <div class="mut" style="font-size:12px;margin-top:8px">Bounds: midpoints of published colorimeter means per USDA class.</div></div>
        <div><div class="sect">Lot rules</div>
          <div class="kv"><span>Off-colour limit</span><span><span class="inp" style="width:90px">10 %</span></span>
          <span>Green limit</span><span><span class="inp" style="width:90px">5 %</span></span>
          <span>On breach</span><span>{bd("Hold lot", "amber")} {bd("Alert QC Manager", "blue")}</span>
          <span>Lot size</span><span><span class="inp" style="width:140px">per pallet / 20 min</span></span></div>
          <div class="sect" style="margin-top:18px">Colour check</div>
          <div class="kv"><span>Reference card</span><span>{status("Pass")} <span class="mut">· today 06:58 · ΔE 1.8</span></span>
          <span>Every</span><span>shift start {tg(True)}</span></div></div></div>''',
                  icon="tune", right=f'{btn("Test on recorded footage", "play_circle", "sm")}{btn("Save", "check", "sm pri")}')
    test = card("Test on recorded footage before going live", grid("1fr 1fr 1fr 1fr", [
        kpi("nutrition", "green", "Fruit in test clip", "78", "every tomato on screen"),
        kpi("verified", "green", "Match by eye", "75 / 78", "blind check · 3 one class apart"),
        kpi("rule", "amber", "Lot verdict", "Mixed Color", "17% off-colour on the PoC lot"),
        kpi("schedule", "blue", "Test time", "4 min", "on 7 days of footage")], 14), icon="science", right=poc())
    sw = [(235, 187, 43), (216, 190, 64), (205, 191, 59), (194, 183, 59), (184, 180, 63), (169, 174, 66),
          (148, 164, 59), (135, 146, 60), (109, 124, 58), (79, 101, 50)]
    lots = ["Lot 1–3"] * 3 + ["Lot 4–6"] * 3 + ["Lot 7–9"] * 3 + ["Out of grade"]
    chips = "".join(f'<div style="text-align:center"><div style="height:46px;border-radius:8px;background:rgb{c}"></div>'
                    f'<b style="display:block;font-size:14px;margin-top:6px">{k}</b><span class="mut" style="font-size:11.5px">{lots[k - 1]}</span></div>'
                    for k, c in enumerate(sw, 1))
    oecd = card("OECD lemon colour chart · lines L1–L2", f'<div style="display:grid;grid-template-columns:repeat(10,1fr);gap:8px">{chips}</div>'
                f'<div class="kv" style="margin-top:14px"><span>Allowed</span><span>degrees 1–9 in Extra, Class I and II</span>'
                f'<span>Per consignment</span><span>at most 3 adjacent degrees</span>'
                f'<span>Degree 10</span><span>{bd("Reject at the line", "red")}</span></div>', icon="palette", right=status("Active"))
    changes = card("Change history", history([
        ("Oct 08", "Off-colour limit 10% confirmed", "Dewi Lestari · QC Manager", "#2563eb"),
        ("Oct 08", "Tested on 7 days of footage", "Dewi Lestari · QC Manager", "#16a34a"),
        ("Oct 02", "OECD lemon chart added", "Rina Hartono · Plant Admin", "#2563eb"),
        ("Sep 30", "Reference card re-printed", "Andi Wijaya · Line Supervisor", "#64748b"),
        ("Sep 28", "USDA tomato classes imported", "Rina Hartono · Plant Admin", "#2563eb")]), icon="history",
        right='<span class="lnk">Audit log ' + I("chevron_right", size=16) + '</span>')
    body = (ph("Product Specs · Grade standards", "Pick a standard per line; the QC Manager sets limits and tests them on recorded footage first",
               btn("Import buyer spec", "upload")) + grid("520px 1fr", [left, detail]) + test
            + grid("1fr 1fr", [oecd, changes]))
    return app("grading", "specs", body)


# ================================================================== Fill Level Inspection
def p08_fill_overview() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("local_drink", "blue", "Bottles inspected today", "48,320", f'{up("3% vs yesterday")}<span>2 lines · 16 nozzles</span>'),
        kpi("trending_down", "red", "Underfill rejects", "37", "0.08% · reject signal sent to PLC"),
        kpi("water_drop", "amber", "Average overfill", "+3.1 mL", "≈ 150 L of product given away today"),
        kpi("check_circle", "green", "Within tolerance", "99.2%", "target 500 mL ± 2%"),
    ])
    noz = dev_bars([3.0, 2.0, 9.0, 1.0, -3.0, 3.5, 2.5, 1.5], [f"N{i}" for i in range(1, 9)], 900, 262, -12, 12,
                   (-10, 10), 4, flag=2)
    nz = card("Mean fill vs target by nozzle · Line F1", noz + f'<div class="row" style="gap:12px;margin-top:6px">'
              f'{bd("Nozzle 3 runs +9 mL over target: check valve timing", "amber", "warning")}'
              f'<span class="mut" style="font-size:12px">target 500 mL · tolerance ±10 mL (±2%)</span></div>',
              icon="bar_chart", right="mL vs target · this shift")
    tr = card("Underfill rejects by hour", vbars([("Line F1", [2, 3, 1, 9, 4, 2, 3, 1], "#2563eb"), ("Line F2", [1, 2, 1, 2, 1, 3, 1, 1], "#93c5fd")],
                                                 ["07", "08", "09", "10", "11", "12", "13", "14"], 560, 262, bw_max=16)
              + legend([("Line F1", "#2563eb"), ("Line F2", "#93c5fd")]), icon="monitoring", right="10:00 spike: low tank level")
    sk = [("Water 500 mL", "F1", "500 mL ± 2%", "24,180", "21", "+2.4 mL"),
          ("Juice 330 mL", "F2", "330 mL ± 2%", "16,900", "12", "+4.0 mL"),
          ("Syrup 620 mL", "F2", "620 mL ± 2%", "7,240", "4", "+3.3 mL")]
    rows = "".join(f'<tr><td><b>{a}</b></td><td>{b}</td><td class="sec tn" style="white-space:nowrap">{c}</td><td class="tn">{d}</td><td class="tn">{e}</td>'
                   f'<td class="tn">{f}</td></tr>' for a, b, c, d, e, f in sk)
    sku = card("SKUs this shift", f'<table class="tbl cp"><thead><tr><th>SKU</th><th>Line</th><th>Target</th><th>Inspected</th>'
               f'<th>Underfill</th><th>Avg overfill</th></tr></thead><tbody>{rows}</tbody></table>', icon="inventory", cb_style="padding:10px 6px 6px")
    rej = card("Latest underfill rejects", history([
        ("10:41", "Line F1 · nozzle 5 · 486 mL", "rejected · PLC", "#dc2626"),
        ("10:36", "Line F1 · nozzle 5 · 488 mL", "rejected · PLC", "#dc2626"),
        ("10:12", "Line F2 · nozzle 2 · 323 mL", "rejected · PLC", "#dc2626"),
        ("10:04", "Line F1 · 9 bottles · low tank", "alert · Line Supervisor", "#f59e0b")]), icon="report",
        right='<span class="lnk">All rejects ' + I("chevron_right", size=16) + '</span>')
    live = card("Live · Line F1 · nozzle 1", tile(im("fill"), "F1 · Filler · CAM 01", "#2563eb", "67%", style="height:205px")
                + f'<div class="mut" style="font-size:12px;margin-top:8px">{poc()} level measured every frame from the bottle shape</div>',
                icon="videocam")
    body = (ph("Overview · Fill Level Inspection", "Today · Shift 1 · lines F1–F2",
               btn("Export", "download") + btn("Open TV Dashboard", "live_tv", "pri"))
            + k + grid("1fr 620px", [nz, tr]) + grid("1fr 1fr 480px", [sku, rej, live]))
    return app("fill", "overview", body)


def p09_tv_fill() -> str:
    return annotated("fill", im("fill", 2, cam=False), "Fill level · nozzle 1", "bottle by bottle", "Line F1 · TV", [
        (640, 112, "Live camera with AI", "Bottle outline, thread-line target and the measured level in % and mL."),
        (1330, 90, "Fill KPIs", "Fill level, flow rate, fill time and time to target."),
        (1330, 290, "Fill curve", "Level over time against the target band 98–102%."),
        (1330, 620, "Event Log", "Bottle in position, flow start, half target, verdict."),
        (40, 820, "Pass / reject rule", "Below 98% = reject (underfill); above 102% = pass, logged as giveaway."),
        (680, 820, "Height is not volume", "Volume from the bottle shape, not from the level height.")],
                     "Frame from the PoC video (real Pexels footage). The clip ends at 67% of target, so this PoC shows the measurement, not a verdict.")


def p10_fill_spec() -> str:
    skus = [("Mineral water 500 mL", "PET 500 · round", "Active"), ("Juice 330 mL", "Glass 330 · round", "Active"),
            ("Syrup 620 mL", "PET 620 · shoulder", "Active"), ("Sauce 340 g", "Glass 340 · wide neck", "Draft")]
    rows = "".join(f'<tr class="{"on" if k == 0 else ""}"><td><b>{a}</b><div class="mut" style="font-size:12px">{b}</div></td><td>{status(c)}</td></tr>'
                   for k, (a, b, c) in enumerate(skus))
    left = card("SKUs", f'<table class="tbl"><thead><tr><th>SKU · container</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>',
                icon="inventory", right=btn("New SKU", "add", "sm"), cb_style="padding:10px 6px 6px")
    rules = [("flag", "#079455", "Target", "500 mL · fill up to the thread line"),
             ("tune", "#0e7490", "Tolerance", "98–102% (490–510 mL) when the nozzle stops"),
             ("trending_down", "#dc2626", "Below 490 mL", "Reject · PLC signal to the rejector, within 0.5 s"),
             ("water_drop", "#d97706", "Above 510 mL", "Pass · logged as giveaway · alert if 5 in a row"),
             ("repeat", "#2563eb", "3 rejects on one nozzle", "Alert Line Supervisor · check that nozzle")]
    rr = "".join(f'<div class="row" style="gap:12px;padding:10px 0;border-bottom:1px solid var(--hair)">{I(ic, True, 20, c)}'
                 f'<b style="width:200px">{a}</b><span class="sec">{b}</span></div>' for ic, c, a, b in rules)
    spec = card("Mineral water 500 mL · fill rule", f'''<div style="display:grid;grid-template-columns:1fr 420px;gap:28px">
      <div><div class="sect">Pass / reject</div>{rr}
        <div class="mut" style="font-size:12px;margin-top:10px">Set the tolerance to the legal metrology (BDKT) and customer limits that apply to this SKU.</div></div>
      <div><div class="sect">Container profile</div>
        <div class="kv"><span>Capacity to thread line</span><span><span class="inp" style="width:110px">500 mL</span></span>
        <span>Shape</span><span>measured from 3 empty bottles {status("Pass")}</span>
        <span>Height → volume</span><span>from the bottle outline {poc()}</span>
        <span>Nozzles</span><span><span class="inp" style="width:110px">8 per line</span></span>
        <span>Camera</span><span>CAM 01 · side view, backlit</span></div></div></div>''',
                icon="rule", right=f'{btn("Test on recorded footage", "play_circle", "sm")}{btn("Save", "check", "sm pri")}')
    gv = card("Giveaway this week · Line F1", lines([("Avg overfill", [3.6, 3.4, 3.9, 3.1, 2.8, 2.6, 2.4], "#d97706")],
                                                   ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], 1000, 330, hi=5,
                                                   ref=("goal +2 mL", 2), fmt=lambda v: f"+{v:.0f} mL", area=True)
              + '<div class="mut" style="font-size:12px;margin-top:6px">From +3.6 to +2.4 mL a bottle after the target line was moved on Thursday '
                '≈ 200 L less product given away a week on this line.</div>',
              icon="water_drop", right="mL per bottle above target")
    pr = card("Before go-live", f'''<div class="col" style="gap:10px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Target line set on 3 reference bottles</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Reject signal tested with the PLC (Modbus TCP)</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Camera fixed, backlight on, 7 days of footage tested</div>
      <div class="row" style="gap:8px">{I("radio_button_unchecked", False, 18, "#94a3b8")}Check weigher comparison on 50 bottles</div>
      <div class="row" style="gap:8px">{I("radio_button_unchecked", False, 18, "#94a3b8")}QC Manager sign-off</div></div>''',
                icon="checklist", right="3 of 5")
    chg = card("Change history", history([
        ("Thu", "Target line moved 2 mm down", "Dewi Lestari · QC Manager", "#2563eb"),
        ("Tue", "Reject signal tested", "Rina Hartono · Plant Admin", "#16a34a"),
        ("Mon", "Tolerance set to ±2%", "Dewi Lestari · QC Manager", "#2563eb")]), icon="history")
    body = (ph("Product Specs · Fill rules", "Target, tolerance and actions per SKU; container shape turns level height into volume",
               btn("Import SKU list", "upload")) + grid("440px 1fr", [left, spec])
            + grid("1fr 560px", [gv, f'<div class="col" style="gap:18px">{pr}{chg}</div>']))
    return app("fill", "specs", body)


# ================================================================== Pack Count QC
def p11_pack_overview() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("fact_check", "amber", "Packs inspected today", "12,480", f'{up("2% vs yesterday")}<span>trays + boxes</span>'),
        kpi("production_quantity_limits", "red", "Short packs caught", "23", "0.18% · held before sealing"),
        kpi("remove_circle", "amber", "Missing items", "31", "all put back before shipping"),
        kpi("conveyor_belt", "blue", "Feeder gaps", "9", "root cause of 14 of 31 missing items"),
    ])
    tr = card("Short packs by hour", vbars([("Can line C1 · trays", [1, 2, 4, 3, 2, 1, 1, 2], "#d97706"),
                                            ("Packing station P1 · boxes", [0, 1, 1, 2, 1, 1, 0, 1], "#fbbf24")],
                                           ["07", "08", "09", "10", "11", "12", "13", "14"], 780, 226, bw_max=16, ymax=4)
              + legend([("Can line C1 · trays", "#d97706"), ("Packing station P1 · boxes", "#fbbf24")]),
              icon="monitoring", right="held before sealing")
    heat = card("Where items go missing · can trays", f'''<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px">
      {"".join(f'<div style="height:64px;border-radius:8px;background:{c};display:flex;align-items:flex-end;justify-content:space-between;padding:8px 10px;font-size:13px"><b>{n}</b><span class="tn" style="font-size:16px;font-weight:600">{v}</span></div>'
               for n, v, c in [("A1", "0", "#f1f5f9"), ("A2", "6", "#d97706"), ("A3", "4", "#f59e0b"), ("A4", "0", "#f1f5f9"), ("A5", "1", "#fde7c2"),
                               ("B1", "0", "#f1f5f9"), ("B2", "0", "#f1f5f9"), ("B3", "1", "#fde7c2"), ("B4", "0", "#f1f5f9"), ("B5", "3", "#fbbf24")])}</div>
      <div class="row" style="justify-content:space-between;margin-top:6px;font-size:12px" class="mut"><span class="mut">filler lane 1 → 5</span><span class="mut">missing cans per slot · 3,410 trays</span></div>
      <div style="margin-top:12px;padding:12px 14px;border-radius:10px;background:#eff6ff;font-size:13.5px;line-height:1.5">{I("insights", True, 18, "#2563eb")} <b>Slot A2 empty 6× this week</b>, A3 4×: filler lanes 2 and 3, side by side. Check both lane guides before the next shift.</div>''',
                icon="grid_view", right="this week")
    ev = [("snap_box_461.jpg", "high", "Box #2 released short 2", "18/20 · slots B2, C5 empty · held", "P1", "10:41"),
          ("snap_tray_413.jpg", "high", "Tray #7 short 1 can", "9/10 · slot B5 empty · rejected", "C1", "10:39"),
          ("snap_box_284.jpg", "medium", "Empty pick · slot B2", "robot moved without product · cause: feeder gap", "P1", "10:36"),
          ("snap_tray_222.jpg", "high", "Tray #4 short 1 can", "9/10 · slot A3 empty · rejected", "C1", "10:34")]
    rows = "".join(f'<div class="ev"><img class="thumb" src="../img/{a}" style="width:112px;height:63px"><div class="grow">'
                   f'<div class="t1">{b}</div><div class="t2">{c}</div></div>{sev(s)}<span class="cam">{I("videocam", True)}{d}</span>'
                   f'<span class="mut tn" style="width:44px;text-align:right">{e}</span></div>' for a, s, b, c, d, e in ev)
    evc = card("Latest rejects & events", rows, icon="report", right=poc())
    live = card("Live", grid("1fr", [tile(im("tray"), "C1 · Can line · CAM 03", "#d97706", "", style="height:150px"),
                                     tile(im("packing", 1), "P1 · Robot packing · CAM 04", "#d97706", "", style="height:150px")], 10),
                icon="videocam")
    body = (ph("Overview · Pack Count QC", "Today · Shift 1 · can line C1 and packing station P1",
               btn("Export", "download") + btn("Open TV Dashboard", "live_tv", "pri"))
            + k + grid("1fr 1fr", [tr, heat]) + grid("1fr 480px", [evc, live]))
    return app("pack", "overview", body)


def p12_tv_tray() -> str:
    return annotated("pack", im("tray", 2, cam=False), "Can trays · 10 per tray", "end of the filling line", "Line C1 · TV", [
        (640, 112, "Live camera with AI", "Every can found; an empty slot ringed in red and the tray flagged SHORT."),
        (1330, 90, "Line KPIs", "Trays inspected, short trays, missing cans, line speed."),
        (1330, 290, "Missing can positions", "Which slot goes empty, and whether it repeats: points to one filler lane."),
        (1330, 620, "Event Log", "Every short tray with a snapshot, to reject."),
        (40, 820, "Last trays", "Count and pass / reject per tray."),
        (680, 820, "Trays inspected, cumulative", "Inspected against short, with the test against ground truth.")],
                     "Frame from the PoC video (3D simulation with known truth: 7/7 trays judged right). In the product: a camera above the end of the line.")


def p13_tv_packing() -> str:
    return annotated("pack", im("packing", 1, cam=False), "Robot packing · 20 per box", "box filled slot by slot", "Station P1 · TV", [
        (640, 112, "Live camera with AI", "Each slot of the box tracked as the robot fills it; empty picks crossed in red."),
        (1330, 90, "Station KPIs", "Box at station, boxes done, empty picks, robot speed."),
        (1330, 290, "Slot map", "Filled, empty pick, next slot, to go."),
        (1330, 620, "Event Log", "Feeder gap, empty pick, short box released: cause and effect in order."),
        (40, 820, "Box history", "Each box released, its count, empty slots and the action: seal & ship or hold & add."),
        (680, 820, "Box count at station", "Count over time against the standard of 20.")],
                     "Frame from the PoC video (3D simulation with known truth: 3/3 boxes and 2/2 empty picks found).")


def p14_pack_reject() -> str:
    tl = [("10:36:12", "conveyor_belt", "Feeder supply gap", "stopper empty · slot B2 at risk", "#2563eb"),
          ("10:36:14", "report", "Empty pick · slot B2", "robot moved without product", "#d97706"),
          ("10:38:57", "conveyor_belt", "Feeder supply gap", "stopper empty · slot C5 at risk", "#2563eb"),
          ("10:39:01", "report", "Empty pick · slot C5", "robot moved without product", "#d97706"),
          ("10:41:20", "production_quantity_limits", "Box #2 released short 2", "18/20 · held at the outfeed", "#dc2626"),
          ("10:41:31", "chat", "WhatsApp to Line Supervisor", "Andi Wijaya · seen 10:41:40", "#079455"),
          ("10:44:02", "task_alt", "Reworked & re-checked", "20/20 · released by Andi Wijaya", "#079455")]
    steps = "".join(f'<div class="row" style="gap:12px;align-items:flex-start;padding:8px 0"><span class="mut tn" style="width:64px;font-size:12.5px;padding-top:2px">{a}</span>'
                    f'<span class="it" style="width:28px;height:28px;background:{c}1a;color:{c}">{I(ic, True, 17)}</span>'
                    f'<div><b style="font-size:13.5px">{t}</b><div class="mut" style="font-size:12.5px">{d}</div></div></div>' for a, ic, t, d, c in tl)
    ev = card("Evidence", f'<img class="thumb" src="../img/snap_box_461.jpg" style="width:100%;height:auto;aspect-ratio:16/9">'
              f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">'
              f'<img class="thumb" src="../img/snap_box_284.jpg" style="width:100%;height:auto;aspect-ratio:16/9">'
              f'<img class="thumb" src="../img/snap_box_412.jpg" style="width:100%;height:auto;aspect-ratio:16/9"></div>'
              f'<div class="row" style="gap:10px;margin-top:12px">{btn("Play clip −10 s / +10 s", "play_circle")}{btn("Export PDF", "picture_as_pdf")}</div>'
              f'<div class="kv" style="margin-top:16px"><span>Camera</span><span>CAM 04 · top view over the outfeed</span>'
              f'<span>Count read</span><span>every frame while the box is in view · stable at 18 before release</span>'
              f'<span>Clip kept</span><span>30 days (90 with add-on) · export to keep</span></div>',
              icon="photo_library", right=poc())
    slots = "".join(f'<div style="height:44px;border-radius:8px;display:flex;align-items:center;justify-content:space-between;padding:0 10px;'
                    f'font-size:12.5px;font-weight:600;{"background:#dc2626;color:#fff" if n in ("B2", "C5") else "background:#dcfce7;color:#166534"}">'
                    f'{n}{I("cancel" if n in ("B2", "C5") else "check_circle", True, 17)}</div>'
                    for n in [f"{r}{c}" for r in "ABCD" for c in range(1, 6)])
    det = card("Box #2 · Packing station P1", f'''
      <div class="row" style="gap:10px;margin-bottom:12px">{bd("High", "red", "error")}{status("Rework")}<span class="mut">SKU Snack Box 20 · Lot P-1012-11</span></div>
      <div class="kv"><span>Count</span><b class="tn">18 / 20</b><span>Empty slots</span><b>B2, C5</b>
      <span>Root cause</span><span>Feeder supply gap before each empty pick {poc()}</span><span>Owner</span><span>{avatar("Andi Wijaya", 24)} Andi Wijaya</span></div>
      <div class="sect" style="margin-top:16px">Slot map</div><div style="display:grid;grid-template-columns:repeat(5,1fr);gap:7px">{slots}</div>''',
               icon="inventory_2", right=status("Closed"))
    capa = card("Corrective action", f'''<div class="col" style="gap:10px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Add 2 items, re-check 20/20, release</div>
      <div class="row" style="gap:8px">{I("pending", True, 18, "#d97706")}Raise feeder buffer level · Maintenance · due Fri</div>
      <div class="row" style="gap:8px">{I("pending", True, 18, "#d97706")}Alert when 2 feeder gaps in 5 min</div></div>''', icon="build")
    body = (ph("Reject · Box #2 short 2", "Packing station P1 · 10:41 · held at the outfeed, reworked and released",
               btn("Override (needs QC Manager)", "gavel") + btn("Close", "check", "pri"),
               crumb=f'Rejects & Events {I("chevron_right", size=16)} P1-0412')
            + grid("1fr 560px 460px", [f'<div class="col" style="gap:18px">{det}{capa}</div>', ev, card("Timeline", steps + f'''
      <div class="sect" style="margin-top:14px">Same cause this week</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
        <div class="card" style="padding:12px 14px;gap:2px"><b style="font-size:22px">9</b><span class="mut" style="font-size:12px">feeder gaps</span></div>
        <div class="card" style="padding:12px 14px;gap:2px"><b style="font-size:22px">14</b><span class="mut" style="font-size:12px">missing items</span></div>
        <div class="card" style="padding:12px 14px;gap:2px"><b style="font-size:22px">6</b><span class="mut" style="font-size:12px">boxes held</span></div></div>
      <div class="mut" style="font-size:12.5px;margin-top:10px">All 6 boxes caught before sealing · 0 complaints from customers this week</div>''', icon="timeline")],
                   18, "flex:1;min-height:0"))
    return app("pack", "events", body, user=("Andi Wijaya", "Line Supervisor", "amber"))


# ================================================================== Parcel Dimensioning
PARCELS = [(18, 444, 427, 138, "M", ""), (15, 462, 362, 159, "M", ""), (20, 282, 234, 102, "S", "?"),
           (1, 689, 465, 366, "L", ""), (23, 391, 338, 108, "M", ""), (4, 383, 352, 140, "M", ""),
           (24, 376, 313, 268, "M", ""), (28, 754, 543, 341, "L", "")]


def p15_parcel_overview() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("package_2", "violet", "Parcels measured today", "3,240", f'{up("8% vs yesterday")}<span>outbound belt OB1</span>'),
        kpi("view_in_ar", "violet", "Volume shipped", "142 m³", "avg 44 L per parcel"),
        kpi("scale", "blue", "Volumetric weight", "23.6 t", "L × W × H ÷ 6000 · vs 18.1 t on the scale"),
        kpi("straighten", "amber", "Manual check", "41", "1.3% · size near a class boundary"),
    ])
    col = {"S": "#22d3ee", "M": "#3b82f6", "L": "#7c3aed"}
    rows = "".join(
        f'<tr><td><b>#{t}</b></td><td class="tn">{l / 10:.0f} × {w / 10:.0f} × {h / 10:.0f} cm</td>'
        f'<td class="tn">{l * w * h / 1e6:.1f} L</td><td class="tn">{l * w * h / 6e6:.1f} kg</td>'
        f'<td><span class="bd" style="background:{col[c]}22;color:{col[c]}">{c}{m}</span></td>'
        f'<td>{status("Check", "#d97706") if m else status("Pass")}</td></tr>' for t, l, w, h, c, m in PARCELS)
    log = card("Parcel log", f'<table class="tbl cp"><thead><tr><th>Parcel</th><th>L × W × H</th><th>Volume</th><th>Vol. weight</th>'
               f'<th>Class</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>', icon="list_alt",
               right=poc() + " 8 parcels from the PoC clip", cb_style="padding:10px 6px 6px")
    mix = card("Size mix today", hbars([("S · longest side < 30 cm", 812, "#22d3ee"), ("M · 30–60 cm", 1904, "#3b82f6"),
                                        ("L · > 60 cm", 524, "#7c3aed")], label_w=190, fmt=lambda v: f"{v:,.0f}"),
               icon="category", right="parcels")
    tr = card("Parcels per hour", vbars([("Parcels", [310, 420, 465, 512, 448, 396, 380, 309], "#7c3aed")],
                                        ["07", "08", "09", "10", "11", "12", "13", "14"], 760, 196, bw_max=28, ymax=600), icon="monitoring",
              right="peak 512 at 10:00")
    vol = card("Volume per hour", lines([("Measured volume", [13.8, 18.2, 20.1, 23.0, 19.6, 17.1, 16.8, 13.4], "#7c3aed")],
                                        ["07", "08", "09", "10", "11", "12", "13", "14"], 760, 196, hi=24, area=True,
                                        fmt=lambda v: f"{v:.0f} m³"), icon="view_in_ar", right="m³ per hour · plan trucks ahead")
    live = card("Live · belt OB1", tile(im("parcel"), "OB1 · Outbound belt · CAM 05", "#7c3aed", "8 counted", style="height:200px"),
                icon="videocam")
    body = (ph("Overview · Parcel Dimensioning", "Today · Shift 1 · outbound belt OB1",
               btn("Export manifest (CSV)", "download") + btn("Open TV Dashboard", "live_tv", "pri"))
            + k + grid("1fr 600px", [log, f'<div class="col" style="gap:18px">{mix}{live}</div>'])
            + grid("1fr 1fr", [tr, vol]))
    return app("parcel", "overview", body)


def p16_tv_parcel() -> str:
    return annotated("parcel", im("parcel", 2, cam=False), "Parcels on the belt · size & volume", "telescopic belt at the truck", "Belt OB1 · TV", [
        (640, 112, "Live camera with AI", "Each parcel boxed in its size class with L × W × H and volume."),
        (60, 230, "Count line", "Each parcel counted once as it crosses."),
        (1330, 90, "Belt KPIs", "Parcels counted, volume handled, rate, manual checks."),
        (1330, 290, "Parcels measured", "Final size of each parcel before the count line."),
        (1330, 620, "Event Log", "Each parcel; a near-boundary size flagged for a manual check."),
        (40, 820, "Size mix", "S / M / L by count and volume."),
        (680, 820, "Volume handled", "Cumulative litres, with the test against a hand count.")],
                     "Frame from the PoC video (real Pexels footage): 8 of 8 parcels counted; a test carton read 340.5 mm against 340 mm.")


def p17_parcel_load() -> str:
    trucks = [("Truck 01 · Jakarta", "CDD box · 16 m³", 92, "Loaded", "#079455"), ("Truck 02 · Bandung", "CDD box · 16 m³", 78, "Loading", "#2563eb"),
              ("Truck 03 · Surabaya", "Fuso box · 32 m³", 41, "Loading", "#2563eb"), ("Truck 04 · Semarang", "CDD box · 16 m³", 0, "Planned", "#94a3b8")]
    rows = "".join(f'<div style="padding:12px 0;border-bottom:1px solid var(--hair)"><div class="row"><b>{a}</b><span class="mut">{b}</span>'
                   f'<span style="margin-left:auto">{status(d, c)}</span></div><div class="row" style="gap:12px;margin-top:8px">'
                   f'<div class="prog grow" style="height:10px"><i style="width:{p}%;background:{c}"></i></div><b class="tn" style="width:44px;text-align:right">{p}%</b></div></div>'
                   for a, b, p, d, c in trucks)
    tk = card("Truck fill by measured volume", rows, icon="local_shipping", right="live from belt OB1")
    bil = card("Volumetric vs actual weight · by customer", vbars(
        [("Actual weight", [4.2, 3.1, 2.6, 1.9, 1.4], "#94a3b8"), ("Volumetric weight", [6.1, 3.3, 4.0, 1.8, 2.2], "#7c3aed")],
        ["Cust. A", "Cust. B", "Cust. C", "Cust. D", "Cust. E"], 900, 260, fmt=lambda v: f"{v:.0f} t", bw_max=30, ymax=8,
        tip=(0, 30, 20, "Customer A · today")) + legend([("Actual weight", "#94a3b8"), ("Volumetric weight", "#7c3aed")])
        + f'<div style="margin-top:10px;font-size:13.5px">{I("insights", True, 18, "#7c3aed")} Customer A ships light, bulky parcels: '
          f'billed by volume, not by scale weight.</div>', icon="scale", right="tonnes today")
    chk = card("Manual check queue", "".join(
        f'<div class="ev"><span class="it amber">{I("straighten", True, 18)}</span><div class="grow"><div class="t1">{a}</div>'
        f'<div class="t2">{b}</div></div>{btn("Confirm size", None, "sm")}</div>'
        for a, b in [("Parcel #20 · S? near 30 cm", "28 × 23 × 10 cm · 7 L · read near the S/M bound"),
                     ("Parcel #3311 · M? near 60 cm", "58 × 41 × 30 cm · 71 L"),
                     ("Parcel #3318 · L? near 60 cm", "61 × 40 × 22 cm · 54 L")]), icon="rule", right="3 open")
    cus = [("Customer A", "612", "36.6", "4.2", "6.1", "Volume"), ("Customer B", "498", "19.8", "3.1", "3.3", "Volume"),
           ("Customer C", "455", "24.0", "2.6", "4.0", "Volume"), ("Customer D", "390", "10.8", "1.9", "1.8", "Weight"),
           ("Customer E", "287", "13.2", "1.4", "2.2", "Volume")]
    br = "".join(f'<tr><td><b>{a}</b></td><td class="tn">{b}</td><td class="tn">{c} m³</td><td class="tn">{d} t</td>'
                 f'<td class="tn">{e} t</td><td>{bd(f, "violet" if f == "Volume" else "slate")}</td></tr>' for a, b, c, d, e, f in cus)
    bill = card("Billing basis today", f'<table class="tbl cp"><thead><tr><th>Customer</th><th>Parcels</th><th>Volume</th>'
                f'<th>Actual</th><th>Volumetric</th><th>Billed by</th></tr></thead><tbody>{br}</tbody></table>',
                icon="receipt_long", right="the higher of the two", cb_style="padding:10px 6px 6px")
    body = (ph("Outbound · Load planning & billing", "Measured volume per parcel feeds truck loading and volumetric billing",
               btn("Export to TMS / WMS", "sync_alt") + btn("Send invoice data", "receipt_long", "pri"))
            + grid("620px 1fr", [tk, bil], 18) + grid("1fr 1fr", [chk, bill]))
    return app("parcel", "reports", body)


# ================================================================== shared pages
def p18_alerts() -> str:
    rules = [("nutrition", "#16a34a", "Produce Grading", "Lot off-colour above limit", "Hold lot · WhatsApp QC Manager", "High"),
             ("nutrition", "#16a34a", "Produce Grading", "Lemon colour degree 10", "Reject at line · log", "Medium"),
             ("local_drink", "#2563eb", "Fill Level", "Bottle below tolerance", "PLC reject signal · log", "High"),
             ("local_drink", "#2563eb", "Fill Level", "3 rejects on one nozzle in 10 min", "WhatsApp Line Supervisor", "Medium"),
             ("inventory_2", "#d97706", "Pack Count QC", "Short tray / box", "Divert to rework lane · alert", "High"),
             ("inventory_2", "#d97706", "Pack Count QC", "2 feeder gaps in 5 min", "Alert Maintenance", "Low"),
             ("package_2", "#7c3aed", "Parcel Dimensioning", "Size near a class boundary", "Manual check queue", "Low")]
    sv = {"High": "high", "Medium": "medium", "Low": "low"}
    rows = "".join(f'<tr><td><span class="row" style="gap:8px">{I(ic, True, 18, c)}{p}</span></td><td><b>{a}</b></td>'
                   f'<td class="sec">{b}</td><td>{sev(sv[s])}</td><td>{tg(True)}</td></tr>' for ic, c, p, a, b, s in rules)
    rc = card("Alert rules", f'<table class="tbl cp"><thead><tr><th>Product</th><th>When</th><th>Then</th><th>Severity</th><th>On</th></tr></thead>'
              f'<tbody>{rows}</tbody></table>', icon="rule", right=btn("New rule", "add", "sm"), cb_style="padding:10px 6px 6px")
    ints = [("settings_input_component", "PLC / SCADA", "OPC UA · Modbus TCP · digital output to rejector", "Connected"),
            ("factory", "MES", "lots, SKUs and shift results", "Connected"),
            ("account_tree", "ERP", "SAP · Oracle · Odoo · batch & quality records", "Available"),
            ("warehouse", "WMS / TMS", "parcel dimensions, truck loading", "Available"),
            ("chat", "WhatsApp Business", "alerts with photo to the right person", "Connected"),
            ("webhook", "Webhook & REST API", "every event and measurement, in real time", "Connected")]
    ir = "".join(f'<div class="ev"><span class="it slate">{I(ic, True, 19)}</span><div class="grow"><div class="t1">{a}</div>'
                 f'<div class="t2">{b}</div></div>{status("Online" if d == "Connected" else "Draft", "#079455" if d == "Connected" else "#94a3b8")}'
                 f'<span class="mut" style="width:78px;font-size:12px">{d}</span></div>' for ic, a, b, d in ints)
    ic = card("Integrations", ir, icon="hub")
    esc = card("Escalation", f'''<div class="col" style="gap:10px;font-size:13.5px">
      <div class="row" style="gap:10px">{bd("High", "red", "error")}<span>Line Supervisor at once → QC Manager after 5 min → Plant Admin after 15 min</span></div>
      <div class="row" style="gap:10px">{bd("Medium", "amber", "warning")}<span>Line Supervisor · shift summary to QC Manager</span></div>
      <div class="row" style="gap:10px">{bd("Low", "blue", "info")}<span>In the shift report only</span></div></div>''', icon="campaign")
    wa = card("WhatsApp preview", f'''<div style="background:#e7f6e7;border-radius:12px;padding:12px;font-size:13px;line-height:1.45">
      <b>Factory Vision · Plant A</b><br>{I("error", True, 16, "#dc2626")} <b>Box #2 released short 2</b> · Packing station P1 · 10:41<br>
      18/20 · slots B2, C5 empty · held at outfeed<img class="thumb" src="../img/snap_box_461.jpg" style="width:100%;height:230px;object-fit:cover;margin-top:8px">
      <div class="mut" style="margin-top:6px">Reply 1 = taking it · 2 = false alarm</div></div>''', icon="chat")
    sent = card("Alerts sent today", history([
        ("10:41", "Box #2 released short 2 · P1", "WhatsApp · Andi Wijaya · seen in 9 s", "#dc2626"),
        ("10:38", "Lot T-1012-07 off-colour 17%", "WhatsApp · Dewi Lestari · seen in 1 min", "#dc2626"),
        ("10:04", "9 underfills · Line F1 · low tank", "WhatsApp · Andi Wijaya · seen in 20 s", "#f59e0b"),
        ("09:12", "Feeder gaps · P1", "email · Maintenance", "#2563eb")]), icon="send", right="24 sent · 0 missed")
    body = (ph("Alerts & Integrations", "One rule set for every product: who is told, what the line does, which systems get the data")
            + grid("1fr 560px", [f'<div class="col" style="gap:18px">{rc}{esc}{sent}</div>', f'<div class="col" style="gap:18px">{ic}{wa}</div>'], 18, "flex:1;min-height:0"))
    return app("pack", "alerts", body, user=("Rina Hartono", "Plant Admin", "blue"))


def p19_cameras() -> str:
    cams = [("CAM 01", "T1–T4 · Tomato packing", "grading", "Online", "30 fps", "Pass", "06:58"),
            ("CAM 02", "L1–L2 · Lemon chains", "grading", "Online", "30 fps", "Pass", "06:59"),
            ("CAM 03", "C1 · Can line end", "pack", "Online", "30 fps", "Pass", "07:01"),
            ("CAM 04", "P1 · Robot packing", "pack", "Online", "25 fps", "Pass", "07:01"),
            ("CAM 05", "OB1 · Outbound belt", "parcel", "Online", "30 fps", "Pass", "07:03"),
            ("CAM 06", "F1 · Filler nozzle 1–4", "fill", "Online", "25 fps", "Pass", "07:04"),
            ("CAM 07", "F1 · Filler nozzle 5–8", "fill", "Check", "25 fps", "Glare on lens", "07:04"),
            ("CAM 08", "F2 · Filler", "fill", "Paused", "—", "Line stopped", "—")]
    rows = "".join(f'<tr><td><span class="cam">{I("videocam", True)}{a}</span></td><td><b>{b}</b></td>'
                   f'<td><span class="row" style="gap:6px">{I(PRODUCTS[c][0], True, 17, PRODUCTS[c][2])}{PRODUCTS[c][1]}</span></td>'
                   f'<td>{status(d, {"Online": "#079455", "Check": "#d97706", "Paused": "#94a3b8"}[d])}</td><td class="tn">{e}</td>'
                   f'<td>{bd(f, "green" if f == "Pass" else "amber" if d == "Check" else "slate")}</td><td class="mut tn">{g}</td></tr>'
                   for a, b, c, d, e, f, g in cams)
    cc = card("Cameras", f'<table class="tbl cp"><thead><tr><th>Camera</th><th>Line</th><th>Product</th><th>Status</th><th>Frame rate</th>'
              f'<th>Image check</th><th>Last check</th></tr></thead><tbody>{rows}</tbody></table>', icon="photo_camera",
              right=btn("Add camera (RTSP / ONVIF)", "add", "sm"), cb_style="padding:10px 6px 6px")
    edges = [("Edge box 01", "CAM 01–04", "41%", "18 ms"), ("Edge box 02", "CAM 05–08", "33%", "21 ms")]
    er = "".join(f'<div class="ev"><span class="it green">{I("memory", True, 19)}</span><div class="grow"><div class="t1">{a}</div>'
                 f'<div class="t2">{b} · GPU {c} · latency {d}</div></div>{status("Online")}</div>' for a, b, c, d in edges)
    ec = card("Edge AI boxes", er + f'<div class="mut" style="font-size:12px;margin-top:8px">AI model updates rolled out by the vendor, line by line, with rollback.</div>',
              icon="memory")
    setup = card("New camera · CAM 07 check", f'''<div style="display:grid;grid-template-columns:1fr;gap:14px">
      <img class="thumb" src="{im("fill", 1)}" style="width:100%;height:200px;object-fit:cover">
      <div class="col" style="gap:8px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Product in focus at the inspection point</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Frame rate ≥ 25 fps</div>
      <div class="row" style="gap:8px">{I("warning", True, 18, "#d97706")}Glare on the right of the lens — add a polariser or move 10 cm</div>
      <div class="row" style="gap:8px">{I("radio_button_unchecked", False, 18, "#94a3b8")}Reference card colour check</div></div></div>''',
                  icon="center_focus_strong", right=status("Check", "#d97706"))
    up7 = card("Camera uptime · 7 days, line running", hbars([(a, v, "#16a34a" if v >= 99 else "#d97706") for a, v in [
        ("CAM 01 · T1–T4", 99.8), ("CAM 02 · L1–L2", 99.6), ("CAM 03 · C1", 99.9), ("CAM 04 · P1", 99.7),
        ("CAM 05 · OB1", 99.5), ("CAM 06 · F1", 99.9), ("CAM 07 · F1", 97.2)]], vmax=100, label_w=150, fmt=lambda v: f"{v:.1f}%"),
        icon="monitor_heart")
    guide = card("Camera placement · what we need from the plant", f'''<div class="col" style="gap:9px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}A fixed mount over or beside the line; no pan or zoom while running</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Even light on the product; a backlight for bottles</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Network to the edge box (PoE), power for the box</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Existing IP cameras can be used if they pass the image check</div></div>''',
                  icon="checklist")
    body = (ph("Lines & Cameras", "Each camera is checked before it is used: focus, frame rate, glare, colour",
               btn("Run all checks", "fact_check")) + cc + grid("1fr 1fr 1fr", [setup, f'<div class="col" style="gap:18px">{ec}{guide}</div>', up7]))
    return app("fill", "cameras", body, user=("Rina Hartono", "Plant Admin", "blue"))


def p20_multi_plant() -> str:
    plants = [("Plant A · Cikarang", ["grading", "fill", "pack", "parcel"], "99.2%", "0.14%", "1", "+2.5 mL"),
              ("Plant B · Surabaya", ["fill", "pack"], "98.7%", "0.22%", "0", "+3.8 mL"),
              ("Plant C · Medan", ["grading"], "96.4%", "—", "2", "—"),
              ("DC Jakarta", ["parcel"], "—", "—", "0", "—")]
    rows = "".join(f'<tr><td><b>{a}</b></td><td><span class="row" style="gap:4px">'
                   + "".join(f'<span class="it {PRODUCTS[p][3]}" style="width:26px;height:26px">{I(PRODUCTS[p][0], True, 15)}</span>' for p in ps)
                   + f'</span></td><td class="tn">{b}</td><td class="tn">{c}</td><td class="tn">{d}</td><td class="tn">{e}</td>'
                     f'<td>{spark(sp)}</td></tr>' for (a, ps, b, c, d, e), sp in zip(plants, [[6, 5, 5, 4, 4, 3, 3], [4, 5, 4, 4, 5, 4, 4],
                                                                                         [3, 4, 4, 5, 6, 6, 7], [2, 2, 3, 2, 2, 2, 2]]))
    tb = card("All plants · this week", f'<table class="tbl"><thead><tr><th>Plant</th><th>Products</th><th>First-pass quality</th>'
              f'<th>Short-pack rate</th><th>Lots on hold</th><th>Avg overfill</th><th>Rejects · 7 days</th></tr></thead><tbody>{rows}</tbody></table>',
              icon="factory", cb_style="padding:10px 6px 6px")
    comp = card("First-pass quality · 12 weeks", lines([("Plant A", [97.1, 97.5, 97.8, 98.0, 98.2, 98.4, 98.6, 98.7, 98.9, 99.0, 99.1, 99.2], "#2563eb"),
                                                        ("Plant B", [97.8, 97.9, 98.0, 98.0, 98.2, 98.3, 98.4, 98.4, 98.5, 98.6, 98.6, 98.7], "#d97706"),
                                                        ("Plant C", [95.0, 95.2, 95.1, 95.6, 95.8, 95.7, 96.0, 96.1, 96.2, 96.3, 96.3, 96.4], "#16a34a")],
                                                       [f"W{i}" for i in range(29, 41)], 900, 280, lo=94, hi=100, ticks=3,
                                                       fmt=lambda v: f"{v:.0f}%", end_labels=True, R=70), icon="monitoring")
    att = card("Needs attention", "".join(
        f'<div class="ev"><span class="it {t}">{I(ic, True, 18)}</span><div class="grow"><div class="t1">{a}</div><div class="t2">{b}</div></div></div>'
        for ic, t, a, b in [("pause_circle", "amber", "Plant C · 2 lemon lots on hold", "colour lot 7–9 rising since Tuesday"),
                            ("water_drop", "amber", "Plant B · overfill +3.8 mL", "above the +2 mL goal on line F2"),
                            ("warning", "amber", "Plant A · CAM 07 glare on lens", "nozzles 5–8 checked by hand since 07:04")]), icon="priority_high")
    rep = card("Weekly report to head office", f'''<div class="kv"><span>Sent</span><span>every Monday 07:00 · PDF + Excel</span>
      <span>To</span><span>Plant managers, QC, Operations Director</span>
      <span>Holds</span><span>the same measures for every plant and product</span></div>''', icon="mail", right=tg(True))
    body = (ph("Plants", "One view for head office: every plant, every product, the same measures",
               '<span class="seg"><span>Today</span><span class="on">This week</span><span>This month</span></span>')
            + tb + grid("1fr 560px", [comp, f'<div class="col" style="gap:18px">{att}{rep}</div>']))
    return app("grading", "plants", body, user=("Budi Santoso", "Viewer", "slate"))


def p21_rollout() -> str:
    pilot = {"grading": "Lot verdict and colour class agree with the plant’s QC on a blind sample (PoC: 75/78 tomatoes)",
             "fill": "Every bottle below tolerance rejected; fill level per nozzle checked against the check weigher",
             "pack": "Every short tray or box held before sealing, with the empty slot named (PoC: 7/7 trays, 3/3 boxes)",
             "parcel": "L × W × H within ±1 cm of a tape measure on 100 parcels (PoC test carton: 340.5 vs 340 mm)"}
    prods = []
    for k, (icon, name, colour, tone, desc) in PRODUCTS.items():
        unit = {"grading": "per line", "fill": "per filling line", "pack": "per line or station", "parcel": "per belt"}[k]
        prods.append(f'<section class="card" style="padding:20px 22px;gap:10px"><div class="row" style="gap:12px">'
                     f'<span class="it {tone}" style="width:42px;height:42px">{I(icon, True, 23)}</span><b style="font-size:17px">{name}</b></div>'
                     f'<div class="sec" style="font-size:13px">{desc}</div>'
                     f'<div class="row" style="gap:8px;font-size:13.5px;margin-top:auto">{I("receipt_long", False, 18, "var(--text-3)")}'
                     f'<span>Subscription <b>{unit}</b>, monthly</span></div>'
                     f'<div style="border-top:1px solid var(--hair);padding-top:10px;font-size:13px"><div class="sect" style="margin:0 0 6px">Pilot pass mark</div>'
                     f'{pilot[k]}</div></section>')
    inc = [("Included in every product", ["Web App & TV Dashboard", "Alerts by WhatsApp, push, email", "Evidence clips 30 days",
                                          "Shift & lot reports, PDF / Excel", "Users & roles, audit log"]),
           ("Add-ons", ["PLC reject signal integration", "MES / ERP / WMS connector", "Multi-plant view for head office",
                        "Evidence 90 days", "On-premise option"])]
    ic = "".join(f'<section class="card" style="padding:20px 22px;gap:9px"><b style="font-size:16px">{t}</b>'
                 + "".join(f'<div class="row" style="gap:9px;font-size:13.5px">{I("check_circle", True, 18, "#2563eb")}{f}</div>' for f in fs)
                 + '</section>' for t, fs in inc)
    steps = [("search", "1 · Line survey", "1 week", "camera position, light, line speed, standard to use"),
             ("science", "2 · Pilot", "30 days", "1 product on 1 line · accuracy report vs manual QC"),
             ("rocket_launch", "3 · Go-live", "2 weeks", "PLC / MES link, alert rules, training"),
             ("add_business", "4 · Expand", "per quarter", "more lines, next product, other plants")]
    st = "".join(f'<div class="row" style="gap:12px;flex:1;align-items:flex-start"><span class="it blue" style="width:40px;height:40px">{I(ic, True, 21)}</span>'
                 f'<div><b style="font-size:14.5px">{a}</b> <span class="mut">· {b}</span><div class="sec" style="font-size:12.5px;margin-top:3px">{c}</div></div></div>'
                 + (I("arrow_forward", size=20, color="var(--text-3)") if k < 3 else "") for k, (ic, a, b, c) in enumerate(steps))
    who = [("The plant provides", "factory", ["Mounting point and power at each inspection point", "Network from the line to the edge box",
                                                "A QC person for the blind check during the pilot", "The standard or buyer spec to apply"]),
           ("Factory Vision provides", "precision_manufacturing", ["Camera, light and edge box, installed and tuned",
                                                                    "Set-up of the standard, limits and alert rules",
                                                                    "Accuracy report at the end of the pilot", "Support and AI model updates"])]
    split = "".join(f'<section class="card" style="padding:18px 22px;gap:9px"><div class="row" style="gap:10px">{I(ic, True, 20, "#2563eb")}'
                    f'<b style="font-size:16px">{t}</b></div>'
                    + "".join(f'<div class="row" style="gap:9px;font-size:13.5px">{I("check_circle", True, 18, "#16a34a")}{f}</div>' for f in fs)
                    + '</section>' for t, ic, fs in who)
    body = (grid("repeat(4,1fr)", prods, 20)
            + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">{ic}</div>'
            + f'<section class="card" style="padding:18px 24px;flex-direction:row;align-items:center;gap:16px">{st}</section>'
            + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">{split}</div>'
            + f'<section class="card" style="padding:16px 24px;flex-direction:row;align-items:center;gap:14px;background:#0f172a;border-color:#0f172a;color:#e9eef4">'
              f'{I("handshake", True, 24, "#93c5fd")}<span style="font-size:15px"><b>Price per line, quoted after the line survey.</b> '
              f'The pilot fee is credited to the contract when the plant continues.</span></section>')
    return slide("Plans & rollout", "Buy one product for one line, then grow",
                 "Each product is a monthly subscription per line, on the shared platform. Start with a 30-day pilot on the line "
                 "that costs the most in rejects, complaints or giveaway.", body)


PAGE_FUNCS = [
    ("00_product_map", p00_product_map), ("01_roles_access", p01_roles),
    ("02_grading_overview", p02_grading_overview), ("03_grading_live_view", p03_grading_live),
    ("04_grading_tv_tomato", p04_tv_tomato), ("05_grading_tv_lemon", p05_tv_lemon),
    ("06_grading_lot_report", p06_grading_lot), ("07_grading_standards", p07_grading_standards),
    ("08_fill_overview", p08_fill_overview), ("09_fill_tv", p09_tv_fill), ("10_fill_spec", p10_fill_spec),
    ("11_pack_overview", p11_pack_overview), ("12_pack_tv_trays", p12_tv_tray), ("13_pack_tv_packing", p13_tv_packing),
    ("14_pack_reject_detail", p14_pack_reject),
    ("15_parcel_overview", p15_parcel_overview), ("16_parcel_tv", p16_tv_parcel), ("17_parcel_load_billing", p17_parcel_load),
    ("18_alerts_integrations", p18_alerts), ("19_lines_cameras", p19_cameras), ("20_plants", p20_multi_plant),
    ("21_plans_rollout", p21_rollout),
]


# ------------------------------------------------------------------ rendering
def fetch_icons() -> None:
    """Material Symbols Rounded, only the glyphs the pages use (Apache 2.0), from Google Fonts."""
    for fill, name in ((False, "Line"), (True, "Fill")):
        names = ",".join(sorted(USED[fill]))
        url = ("https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,"
               f"{int(fill)},0&icon_names={names}&display=block")
        req = urllib.request.Request(url, headers={"User-Agent": "Wget/1.21"})
        css = urllib.request.urlopen(req, timeout=60).read().decode()
        font_url = css.split("url(")[1].split(")")[0]
        data = urllib.request.urlopen(urllib.request.Request(font_url, headers={"User-Agent": "Wget/1.21"}), timeout=60).read()
        (FONTS / f"MaterialSymbolsRounded-{name}.ttf").write_bytes(data)
        print(f"icons {name}: {len(USED[fill])} glyphs, {len(data) // 1024} KB")


def chrome() -> tuple[str, bool]:
    """(binary, is_headless_shell). The headless shell's page is exactly the window; full Chrome's
    new headless mode keeps 87 px of the window for a browser frame it does not draw."""
    shells = sorted(glob.glob("/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell"))
    for c in [os.environ.get("CHROME", "")] + shells + sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")) + \
             [shutil.which(n) or "" for n in ("chromium", "chromium-browser", "google-chrome")]:
        if c and Path(c).exists():
            return c, c.endswith("headless_shell")
    sys.exit("headless Chromium not found: set CHROME=/path/to/chrome")


def shoot(html: Path, png: Path, scale: float = 1.0) -> None:
    exe, shell = chrome()
    frame = 0 if shell else 87
    subprocess.run([exe] + ([] if shell else ["--headless=new"]) +
                   ["--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
                    f"--force-device-scale-factor={scale}", f"--window-size=1920,{1080 + frame}",
                    "--allow-file-access-from-files", "--virtual-time-budget=4000", f"--screenshot={png}", html.as_uri()],
                   check=True, capture_output=True, timeout=120)
    if frame:
        import cv2
        pic = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
        cv2.imwrite(str(png), pic[:int(1080 * scale)])


def main(argv: list[str]) -> int:
    HTML.mkdir(exist_ok=True)
    PAGES.mkdir(exist_ok=True)
    want = [a for a in argv if not a.startswith("--")]
    built = []
    for slug, fn in PAGE_FUNCS:
        page = fn()
        if want and not any(slug.startswith(w) for w in want):
            continue
        path = HTML / f"{slug}.html"
        path.write_text(page)
        built.append((slug, path))
    if "--icons" in argv:
        fetch_icons()
    if "--no-shot" not in argv:
        for slug, path in built:
            shoot(path, PAGES / f"{slug}.png")
            print("page", slug)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
