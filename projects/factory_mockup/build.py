#!/usr/bin/env python3
"""Mockup pages for the Factory Vision deck: four inspection products on one platform.

Each page is plain HTML and CSS (html/NN_name.html), laid out at 1920x1080 and rendered at 2x (pages/NN_name.png, 3840x2160)
by headless Chromium, in the same look as the warehouse mockup (look.py), so the two decks join up.

The camera pictures, the dashboard frames, the snapshots and every figure marked PoC come from the
proof-of-concept videos (assets.py). Plant names, people, daily totals and trends are illustrative,
and every page says so in its corner.

    python factory_mockup/assets.py        # once: pictures from the PoC videos
    python factory_mockup/build.py         # every page, at 2x: 3840 x 2160
    python factory_mockup/build.py 04 09   # some pages
    python factory_mockup/build.py --1x    # 1920 x 1080 instead
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

WM = "Mockup konsep · angka ilustrasi"
WM_POC = "Mockup konsep · angka ilustrasi · gambar kamera dan angka bertanda PoC: hasil proof of concept"
BRAND = "Factory Vision"

# ------------------------------------------------------------------ the four products
PRODUCTS = {
    "grading": ("nutrition", "Produce Grading", "#16a34a", "green",
                "Grade warna setiap buah di line, sesuai standar USDA dan OECD"),
    "fill": ("local_drink", "Fill Level Inspection", "#2563eb", "blue",
             "Level isi setiap botol terhadap target dan toleransi"),
    "pack": ("inventory_2", "Pack Count QC", "#d97706", "amber",
             "Jumlah isi setiap tray dan kardus sebelum disegel"),
    "parcel": ("package_2", "Parcel Dimensioning", "#7c3aed", "violet",
               "Ukuran dan volume setiap paket di belt"),
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
            out.append(f'<text x="{X(a):.1f}" y="{h - 12}" class="ax" text-anchor="middle">{num(a, 1)}°</text>')
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
    for b, name in zip(band, ("batas bawah", "batas atas")):
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
                   f'style="fill:var(--text-2);font-weight:600">{signed(x)}</text>')
        out.append(f'<text x="{cx:.1f}" y="{h - 8}" class="ax" text-anchor="middle">{lab}</text>')
    return f'<svg width="{w}" height="{h}" style="display:block;max-width:100%">{"".join(out)}</svg>'


def signed(x: float, dec: int = 1) -> str:
    """+3,0 / −3,0 in Indonesian figures."""
    return ("+" if x > 0 else "\u2212" if x < 0 else "") + num(abs(x), dec)


def poc() -> str:
    return '<span class="bd poc">PoC</span>'


# ------------------------------------------------------------------ shells
NAV = [
    ("Pantau", [("dashboard", "Ringkasan", "overview"), ("videocam", "Live View", "live"),
                ("live_tv", "Dashboard TV", "tv")]),
    ("Kualitas", [("report", "Reject & Kejadian", "events"), ("fact_check", "Laporan Lot & Batch", "lots"),
                  ("description", "Laporan Shift", "reports")]),
    ("Pengaturan", [("tune", "Spesifikasi Produk", "specs"), ("photo_camera", "Line & Kamera", "cameras"),
                    ("campaign", "Alert & Integrasi", "alerts")]),
    ("Admin", [("group", "Pengguna & Role", "users"), ("factory", "Pabrik", "plants"),
               ("receipt_long", "Langganan", "billing")]),
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
            f'<div class="ng" style="margin-top:8px"><div class="t">Produk</div>{switch}</div>'
            f'{"".join(groups)}<div class="sfoot">{avatar(uname, 34)}<div class="grow"><b>{uname}</b>{bd(role, utone)}</div>'
            f'{I("unfold_more", size=18, color="#5f6f86")}</div></aside>')


def topbar(product: str, site=("Pabrik A · Cikarang", "PT Contoh Industri"), shift="Shift 1 · 07–15 · 10:42") -> str:
    icon, name, colour, tone, _ = PRODUCTS[product]
    return (f'<header class="top"><div class="sel">{I("factory", size=20, color="var(--text-2)")}'
            f'<div><b>{site[0]}</b><small>{site[1]}</small></div>{I("expand_more", size=18, color="var(--text-3)")}</div>'
            f'<span class="chip" style="color:{colour};border-color:{colour}33;background:{colour}10">{I(icon, True, 16)}{name}</span>'
            f'<div class="search" style="width:440px">{I("search", size=19)}<span class="ell">Cari lot, SKU, line, reject…</span>'
            f'<span class="kbd">Ctrl K</span></div>'
            f'<div class="right"><span class="chip ok"><span class="dot"></span>Semua line online</span>'
            f'<span class="chip">{I("schedule", size=16)}{shift}</span><span class="iconbtn">{I("notifications")}<span class="nd"></span></span>'
            f'<span class="iconbtn">{I("help")}</span>{avatar("Dewi Lestari", 34)}</div></header>')


def doc(body: str, cls: str = "", extra_css: str = "") -> str:
    return (f'<!doctype html><html lang="id"><head><meta charset="utf-8"><title>{BRAND} · mockup</title>'
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
            f'<span class="bd" style="background:{colour}33;color:#e9eef4;height:26px">{I(icon, True)}{name.upper()} · DASHBOARD TV</span>'
            f'<b style="font-size:22px;color:#e9eef4">{title}</b><span style="color:#9ba9b8;font-size:15px">{sub}</span>'
            f'<span style="margin-left:auto;color:#9ba9b8;font-size:13px">{view}</span></div>'
            f'<img src="{src}" style="position:absolute;left:24px;top:96px;width:1584px;height:891px;border-radius:10px;box-shadow:0 0 0 1px #232f3d">'
            f'{marks}<div style="position:absolute;left:1640px;top:96px;width:256px;display:flex;flex-direction:column;gap:18px">{items}</div>'
            f'<div style="position:absolute;left:24px;top:1003px;color:#9ba9b8;font-size:13px">{foot}</div>')
    return doc(body + f'<div class="wm" style="color:#657485">{WM_POC}</div>', cls="dk", extra_css=css + "body{background:#05080c}")


# ------------------------------------------------------------------ shared tables
ROLES = [
    ("shield_person", "Super Admin", "violet", "Tim vendor", "Semua pelanggan · platform"),
    ("admin_panel_settings", "Plant Admin", "blue", "Plant manager, IT", "Semua line di pabrik"),
    ("verified", "QC Manager", "green", "Quality assurance (QA/QC)", "Produk & line yang ditugaskan"),
    ("engineering", "Line Supervisor", "amber", "Produksi / kepala shift", "Line yang ditugaskan"),
    ("visibility", "Viewer", "slate", "Manajemen, auditor", "Hanya melihat"),
]


# ================================================================== slides: platform
def p00_product_map() -> str:
    feats = {
        "grading": ["Kelas warna per buah, per line", "Kelas tomat USDA · bagan lemon OECD", "Cek lot terhadap toleransi",
                    "Alert off-colour & hold lot"],
        "fill": ["Level isi per botol, per nozzle", "Target & toleransi per SKU", "Sinyal reject untuk underfill",
                 "Pantau giveaway (overfill)"],
        "pack": ["Jumlah isi per tray / kardus", "Posisi slot yang kosong", "Hold & rework untuk short pack",
                 "Root cause: feeder gap / empty pick"],
        "parcel": ["P × L × T & volume per paket", "Kelas ukuran S / M / L", "Berat volumetrik",
                   "Manual check untuk ukuran dekat batas"],
    }
    proof = {"grading": "41 tomat · 87 lemon di-grade; cek blind 75/78 dan 18/24 (±1 derajat)",
             "fill": "level isi diukur tiap frame, 67% di akhir klip; flow rate dan waktu ke target",
             "pack": "7/7 tray dan 3/3 kardus benar vs data kebenaran (simulasi 3D)",
             "parcel": "8/8 paket terhitung; karton uji terbaca 340,5 mm vs 340 mm"}
    pics = {"grading": [("tomato", "Tomat · USDA"), ("lemon", "Lemon · OECD")], "fill": [("fill", "Mesin pengisi botol")],
            "pack": [("tray", "Tray kaleng"), ("packing", "Robot packing station")], "parcel": [("parcel", "Belt paket")]}
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
    shared = [("web", "Web App", "Ringkasan · Live View · Reject · Laporan lot · Spesifikasi · Pengguna"),
              ("live_tv", "Dashboard TV", "satu layar per line, untuk area produksi"),
              ("smartphone", "Alert ke HP", "WhatsApp, push, email ke orang yang tepat"),
              ("hub", "Integrasi", "Sinyal reject ke PLC · MES · ERP · WMS · API"),
              ("badge", "5 role", "Super Admin · Plant Admin · QC Manager · Line Supervisor · Viewer")]
    sh = "".join(f'<div class="row" style="gap:12px;flex:1"><span class="it slate">{I(ic, True, 19)}</span><div>'
                 f'<b style="font-size:14px;display:block">{a}</b><span class="mut" style="font-size:12px">{b}</span></div></div>'
                 for ic, a, b in shared)
    flow = [("videocam", "Kamera di line", "CCTV yang ada atau kamera industri"),
            ("memory", "Edge AI box", "deteksi, lacak, ukur · < 1 detik"),
            ("cloud", "Cloud Factory Vision", "spesifikasi, lot, bukti, laporan"),
            ("devices", "Web · TV · HP · PLC", "tindakan yang tepat, saat itu juga")]
    fl = "".join(f'<div class="row" style="gap:10px;flex:1"><span class="it blue">{I(ic, True, 19)}</span><div><b style="font-size:13.5px;display:block">{a}</b>'
                 f'<span class="mut" style="font-size:12px">{b}</span></div></div>'
                 + (I("arrow_forward", size=20, color="var(--text-3)") if k < 3 else "") for k, (ic, a, b) in enumerate(flow))
    body = (grid("repeat(4,1fr)", cards, 20, "flex:1;min-height:0")
            + f'<section class="card" style="padding:16px 22px;flex-direction:row;align-items:center;gap:18px">'
              f'<b style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);white-space:nowrap">Platform bersama</b>{sh}</section>'
            + f'<section class="card" style="padding:14px 22px;flex-direction:row;align-items:center;gap:16px">'
              f'<b style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);white-space:nowrap">Alur data</b>{fl}</section>')
    return slide("Peta produk", "Empat produk inspeksi, satu platform",
                 "Setiap produk dijual sendiri, per line. Semuanya memakai web app, dashboard TV, alert, pengguna dan integrasi yang sama, "
                 f"jadi pabrik bisa mulai dari satu produk lalu menambah yang lain. {poc()} = sudah terbukti di proof of concept.", body)


def p01_roles() -> str:
    cards = "".join(
        f'<section class="card" style="padding:16px 18px;gap:8px"><div class="row"><span class="it {r[2]}">{I(r[0], True, 19)}</span>'
        f'<b style="font-size:16px">{r[1]}</b></div><div class="sec" style="font-size:13px">{r[3]}</div>'
        f'<div class="row mut" style="font-size:12.5px;gap:6px">{I("location_on", size=16)}{r[4]}</div></section>' for r in ROLES)
    F, E, V, N = "full", "edit", "view", "none"
    cap = [
        ("Live View & Dashboard TV", [V + "*", F, F, F, V]),
        ("Tinjau reject & kejadian", [N, F, F, E, V]),
        ("Hold, release atau sortir ulang lot", [N, F, F, E, N]),
        ("Override reject (dengan alasan)", [N, F, F, N, N]),
        ("Ekspor bukti & sertifikat lot", [N, F, F, N, V]),
        ("Laporan shift & lot", [N, F, F, V, V]),
        ("Spesifikasi produk, standar grade, toleransi", [N, F, E, N, N]),
        ("Line, kamera & kalibrasi", [E + "*", F, V, V, N]),
        ("Alert & eskalasi", [N, F, E, N, N]),
        ("Integrasi PLC / MES / ERP & API", [N, F, N, N, N]),
        ("Pengguna, role & SSO", [E, F, N, N, N]),
        ("Langganan & invoice", [F, V, N, N, N]),
        ("Pelanggan, produk aktif, edge & update model AI", [F, N, N, N, N]),
        ("Audit log", [F, V, N, N, N]),
    ]
    mark = {F: (I("check_circle", True, 20, "#0f172a"), "Kelola"), E: (I("edit_square", False, 19, "#0f172a"), "Terbatas"),
            V: (I("visibility", False, 19, "#64748b"), "Lihat"), N: ('<span style="color:#cbd5e1;font-size:18px">—</span>', "")}
    head = "".join(f'<th style="text-align:center;width:170px">{bd(r[1], r[2], r[0])}</th>' for r in ROLES)
    rows = []
    for nm, cells in cap:
        tds = []
        for c in cells:
            m, label = mark[c.rstrip("*")]
            tds.append(f'<td style="text-align:center"><span class="row" style="justify-content:center;gap:6px">{m}'
                       f'<span class="mut" style="font-size:12px">{label}{"*" if c.endswith("*") else ""}</span></span></td>')
        rows.append(f'<tr><td style="font-weight:500">{nm}</td>{"".join(tds)}</tr>')
    table = (f'<section class="card" style="flex:1;min-height:0"><table class="tbl"><thead><tr><th>Fitur</th>{head}</tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></section>')
    notes = (f'<div class="row" style="gap:28px;font-size:13px;color:var(--text-2)">'
             f'<span class="row" style="gap:6px">{mark[F][0]} Kelola = buat, ubah, hapus</span>'
             f'<span class="row" style="gap:6px">{mark[E][0]} Terbatas = hanya line sendiri / perlu persetujuan</span>'
             f'<span class="row" style="gap:6px">{mark[V][0]} Hanya melihat</span>'
             f'<span class="row" style="gap:6px">{I("lock", True, 18, "#6d28d9")}* Super Admin hanya dengan izin Plant Admin, berbatas waktu, dan tercatat di audit log</span></div>')
    body = f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px">{cards}</div>{table}{notes}'
    return slide("Role & hak akses", "QC Manager memegang standar, line yang menjalankan",
                 "Hak akses per role, per pabrik dan per line. Data tiap pelanggan terpisah (multi-tenant); "
                 "vendor tidak bisa melihat kamera pabrik tanpa izin yang tercatat.", body)


# ================================================================== Produce Grading
def p02_grading_overview() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("nutrition", "green", "Buah di-grade hari ini", "41.860", f'{up("6% vs kemarin")}<span>tomat 4 line · lemon 2 line</span>'),
        kpi("verified", "green", "Di kelas warna utama", "86%", "lot langsung release saat cek pertama"),
        kpi("pause_circle", "amber", "Lot di-hold", "2", f'{bd("1 sortir ulang", "red")}{bd("1 Mixed Color", "violet")}'),
        kpi("block", "red", "Out of grade", "0,4%", "di-reject di line · lemon warna 10"),
    ])
    lines4 = ["Line T1", "Line T2", "Line T3", "Line T4"]
    tom = vbars([("Red", [88, 64, 85, 100], "#dc2626"), ("Light Red", [12, 36, 15, 0], "#f87171"),
                 ("Pink / lainnya", [0, 0, 0, 0], "#f472b6")], lines4, 520, 270, stacked=True, ymax=100,
                fmt=lambda v: f"{v:.0f}%", bw_max=56)
    lem = vbars([("Lot 1–3", [26, 23], "#facc15"), ("Lot 4–6", [74, 65], "#84cc16"), ("Lot 7–9", [0, 12], "#15803d")],
                ["Line L1", "Line L2"], 330, 270, stacked=True, ymax=100, fmt=lambda v: f"{v:.0f}%", bw_max=64)
    mix = card("Komposisi grade per line", grid("1fr 340px", [
        f'<div><div class="sect">Tomat · kelas warna USDA</div>{tom}'
        f'{legend([("Red", "#dc2626"), ("Light Red", "#f87171"), ("Pink / lainnya", "#f472b6")])}</div>',
        f'<div><div class="sect">Lemon · lot warna OECD</div>{lem}'
        f'{legend([("Lot 1–3", "#facc15"), ("Lot 4–6", "#84cc16"), ("Lot 7–9", "#15803d")])}</div>'], 28),
        icon="stacked_bar_chart", right="porsi buah yang di-grade shift ini")
    lots = [("T-1012-07", "Tomat", "T1–T4", "9.840", "Red", "17%", "Mixed Color", "Sortir ulang atau label"),
            ("T-1012-06", "Tomat", "T1–T4", "10.220", "Red", "6%", "Release", "—"),
            ("L-1012-04", "Lemon", "L1–L2", "11.310", "Lot 4–6", "31%", "Hold", "Pack terpisah"),
            ("L-1012-03", "Lemon", "L1–L2", "10.490", "Lot 4–6", "8%", "Release", "—")]
    rows = "".join(f'<tr><td><b>{a}</b></td><td>{b}</td><td class="mut">{c}</td><td class="tn">{d}</td><td>{e}</td>'
                   f'<td class="tn">{f}</td><td>{status(g)}</td><td class="sec">{h}</td></tr>' for a, b, c, d, e, f, g, h in lots)
    lot = card("Lot shift ini", f'<table class="tbl cp"><thead><tr><th>Lot</th><th>Produk</th><th>Line</th><th>Buah</th>'
               f'<th>Kelas utama</th><th>Off-colour</th><th>Status</th><th>Tindakan</th></tr></thead><tbody>{rows}</tbody></table>',
               icon="fact_check", right='<span class="lnk">Semua lot ' + I("chevron_right", size=16) + '</span>', cb_style="padding:10px 6px 6px")
    live = card("Line live", grid("1fr 1fr", [tile(im("tomato"), "T1–T4 · Tomat", "#dc2626", "41 terhitung"),
                                              tile(im("lemon"), "L1–L2 · Lemon", "#84cc16", "87 terhitung")], 10, "height:200px"),
                icon="videocam", right='<span class="lnk">Live View ' + I("chevron_right", size=16) + '</span>')
    trend = card("Off-colour per jam", lines([("Tomat", [4, 5, 6, 9, 12, 17, 8, 6], "#dc2626"),
                                                    ("Lemon", [7, 8, 6, 9, 31, 12, 9, 8], "#65a30d")],
                                                   ["07", "08", "09", "10", "11", "12", "13", "14"], 560, 262, hi=40,
                                                   ref=("limit lot 10%", 10), fmt=lambda v: f"{v:.0f}%")
                 + legend([("Tomat", "#dc2626"), ("Lemon", "#65a30d")]),
                 icon="monitoring", right="limit per lot")
    body = (ph("Ringkasan · Produce Grading", "Hari ini · Shift 1 · line tomat dan lemon",
               btn("Ekspor", "download") + btn("Buka Dashboard TV", "live_tv", "pri"))
            + k + grid("1fr 620px", [mix, trend]) + grid("1fr 620px", [lot, live]))
    return app("grading", "overview", body)


def p03_grading_live() -> str:
    big = tile(im("tomato", 1), "LIVE · T1–T4 · Line packing tomat · CAM 01", "#ef4444", style="aspect-ratio:16/9")
    idle = ('<div class="tile" style="aspect-ratio:16/9;background:#111821;display:grid;place-items:center">'
            '<span class="tl"><span class="dot" style="color:#94a3b8"></span>{}</span>'
            '<div style="text-align:center;color:#8b99ad;font-size:12.5px">{}<div style="margin-top:6px">{}</div></div></div>')
    small = [tile(im("lemon", 2), "LIVE · L1–L2 · Chain lemon · CAM 02", "#ef4444", style="aspect-ratio:16/9"),
             idle.format("T5–T8 · Line tomat 2 · CAM 03", I("sync", size=30, color="#8b99ad"), "Line berhenti · ganti SKU"),
             idle.format("L3–L4 · Line lemon 2 · CAM 04", I("schedule", size=30, color="#8b99ad"), "Line hanya jalan di shift 2")]
    wall = (f'<div style="display:flex;flex-direction:column;gap:10px">{big}'
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">{"".join(small)}</div></div>')
    snaps = "".join(f'<div style="text-align:center"><img class="thumb" src="../img/{s["img"]}" style="width:86px;height:86px">'
                    f'<div style="font-size:11.5px;margin-top:4px" class="sec">T{s["line"]} · {num(s["hue"], 0)}°</div></div>'
                    for s in META["tomato_off"][:6])
    cls = [("Red", 34, "#dc2626"), ("Light Red", 7, "#f87171"), ("Pink", 0, "#f472b6"), ("Turning", 0, "#fb923c"),
           ("Breakers", 0, "#facc15"), ("Green", 0, "#22c55e")]
    side = (card("Lot berjalan · T-1012-07", f'<div class="row" style="gap:8px;margin-bottom:10px">{status("Mixed Color")}'
                 f'{bd("off-colour 17% > 10%", "amber", "warning")}</div>'
                 + hbars([(a, b, c) for a, b, c in cls], vmax=41, label_w=90)
                 + f'<div class="mut" style="font-size:12px;margin-top:8px">{poc()} 41 tomat terhitung di count gate · USDA 7 CFR 51.1860</div>',
                 icon="fact_check", right=status("Berjalan"))
            + card("Buah off-colour · lot ini", f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">{snaps}</div>',
                   icon="photo_library", right="Light Red")
            + card("", f'<div class="col" style="gap:8px">{btn("Hold lot", "pause_circle", "pri")}{btn("Sortir ulang di line T2", "sync")}'
                       f'{btn("Release sebagai Mixed Color", "label")}</div>'))
    body = (ph("Live View", "Overlay AI di setiap kamera: kelas per buah, count gate, nomor line",
               '<span class="seg"><span>' + I("crop_square") + '1</span><span>' + I("grid_view") + '4</span><span class="on">'
               + I("view_quilt") + '1+3</span></span>' + btn("Layar penuh", "fullscreen"))
            + f'<div style="display:grid;grid-template-columns:1fr 420px;gap:18px;flex:1;min-height:0">'
              f'<div style="min-height:0">{wall}</div><div class="col" style="gap:14px">{side}</div></div>')
    return app("grading", "live", body, user=("Andi Wijaya", "Line Supervisor", "amber"))


def p04_tv_tomato() -> str:
    return annotated("grading", im("tomato", 2, cam=False), "Tomat · kelas warna USDA", "4 line, satu count gate",
                     "Tampilan 1 dari 2 · berganti tiap 30 detik", [
                         (640, 112, "Kamera live dengan AI", "Setiap tomat diberi kotak sesuai warna kelas USDA; buah yang terhitung diberi label line dan kelasnya."),
                         (40, 465, "Count gate", "Satu garis melintasi 4 line; tiap tomat dihitung sekali, line-nya terbaca saat melintas."),
                         (1330, 90, "KPI lot", "Jumlah terhitung, porsi kelas utama, off-colour vs limit 10%, hijau vs limit 5%."),
                         (1330, 290, "Grade Composition", "Enam kelas USDA dan cek label lot: release sebagai Red, sortir ulang, atau Mixed Color."),
                         (1330, 620, "Event Log", "Setiap tomat off-colour lengkap dengan foto, line, dan nilai warnanya."),
                         (40, 820, "Off-colour trend", "Porsi off-colour lot yang terus naik terhadap limit 10%."),
                         (680, 820, "Colour spread", "Warna tiap tomat terhadap batas kelas USDA.")],
                     "Frame dari video PoC (rekaman nyata Pexels, diputar ulang). Di produk: satu TV per line, data live dari edge box.")


def p05_tv_lemon() -> str:
    return annotated("grading", im("lemon", 2, cam=False), "Lemon · bagan warna OECD", "2 chain sortir",
                     "Tampilan 2 dari 2 · berganti tiap 30 detik", [
                         (640, 112, "Kamera live dengan AI", "Setiap lemon diberi kotak sesuai lot warnanya; buah yang terhitung diberi label line dan derajat warna."),
                         (40, 465, "Count gate", "Satu garis melintasi kedua chain."),
                         (1330, 90, "KPI standar", "Jumlah terhitung, sesuai standar warna (derajat 1–9), porsi lot utama, out of grade."),
                         (1330, 290, "Komposisi bagan OECD", "Jumlah lemon per derajat warna 1–10 dengan warna bagan aslinya, dikelompokkan per 3 derajat."),
                         (1330, 620, "Event Log", "Setiap lemon di luar lot utama, untuk di-pack terpisah; derajat 10 = reject."),
                         (40, 820, "Colour lot trend", "Porsi tiap lot dalam 2 detik terakhir: perubahan buah yang masuk langsung terlihat."),
                         (680, 820, "Degree spread", "Posisi tiap lemon di skala OECD 1–10.")],
                     "Frame dari video PoC (rekaman nyata Pexels, distabilkan). Bagan warna OECD dari panduan market-entry lemon CBI.")


def p06_grading_lot() -> str:
    cls = [("Red", 34, "#dc2626", "> 90% merah"), ("Light Red", 7, "#f87171", "> 60% merah muda–merah, ≤ 90% merah"),
           ("Pink", 0, "#f472b6", "30–60% pink atau merah"), ("Turning", 0, "#fb923c", "10–30% sudah berubah dari hijau"),
           ("Breakers", 0, "#facc15", "≤ 10% sudah berubah dari hijau"), ("Green", 0, "#22c55e", "hijau penuh")]
    rows = "".join(f'<tr><td><span class="row" style="gap:8px"><i class="sw" style="background:{c}"></i><b>{a}</b></span></td>'
                   f'<td class="sec">{d}</td><td class="tn" style="text-align:right"><b>{b}</b></td>'
                   f'<td class="tn mut" style="text-align:right">{100 * b / 41:.0f}%</td></tr>' for a, b, c, d in cls)
    comp = card("Kelas warna USDA", f'<table class="tbl cp"><thead><tr><th>Kelas</th><th>Permukaan (7 CFR 51.1860)</th>'
                f'<th style="text-align:right">Buah</th><th style="text-align:right">Porsi</th></tr></thead><tbody>{rows}</tbody></table>',
                icon="category", right=poc(), cb_style="padding:10px 6px 6px")
    check = card("Cek lot · USDA 7 CFR 51.1861", f'''
      <div class="kv"><span>Label lot yang diminta</span><b>Red</b>
      <span>Off-colour</span><span><b class="tn" style="color:#b42318">17%</b> <span class="mut">· limit 10%</span></span>
      <span>Hijau di lot</span><span><b class="tn">0%</b> <span class="mut">· limit 5%</span></span>
      <span>Keputusan</span><span>{status("Mixed Color")}</span></div>
      <div style="margin-top:14px;padding:12px 14px;border-radius:10px;background:#fffaeb;font-size:13.5px;line-height:1.5">
      {I("lightbulb", True, 18, "#b54708")} <b>Sortir ulang 7 tomat Light Red</b> (4 di line T2), maka lot bisa diberi label
      <b>Red</b>. Line T2 paling banyak membawa buah off-colour di lot ini.</div>
      <div class="row" style="gap:10px;margin-top:14px">{btn("Sortir ulang & cek ulang", "sync", "pri")}{btn("Release sebagai Mixed Color", "label")}</div>''',
                 icon="rule", right=status("Hold"))
    per = vbars([("Red", [7, 5, 11, 11], "#dc2626"), ("Light Red", [1, 4, 2, 0], "#f87171")],
                ["Line T1", "Line T2", "Line T3", "Line T4"], 560, 220, stacked=True, bw_max=60,
                tip=(1, 30, 20, "Line T2 · 9 tomat"))
    perc = card("Per line", per + legend([("Red", "#dc2626"), ("Light Red", "#f87171")]), icon="stacked_bar_chart", right=poc())
    snaps = "".join(f'<div><img class="thumb" src="../img/{s["img"]}" style="width:100%;height:118px">'
                    f'<div class="row" style="justify-content:space-between;margin-top:5px;font-size:12px"><b>Line T{s["line"]}</b>'
                    f'<span class="mut tn">hue {num(s["hue"], 1)}°</span></div></div>' for s in META["tomato_off"][:6])
    ev = card("Bukti foto · buah off-colour", f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px">{snaps}</div>',
              icon="photo_library", right="Light Red · terhitung di count gate")
    audit = card("Seberapa akurat", f'''<div class="col" style="gap:9px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}<span><b>75 dari 78</b> tomat sama dengan cek mata secara blind; sisanya beda 1 kelas</span></div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}<span>Batas kelas dari data colorimeter yang dipublikasikan, bukan disetel ke line ini</span></div>
      <div class="row" style="gap:8px">{I("info", True, 18, "#2563eb")}<span>Warna dicek dengan kartu referensi setiap awal shift</span></div></div>''',
                 icon="verified", right=poc())
    col = {"Red": "#dc2626", "Light Red": "#f87171"}
    spread = card("Warna kulit setiap tomat di lot ini", hue_strip([(t["hue"], col.get(t["usda_class"], "#f472b6")) for t in TOMATOES])
                  + '<div class="mut" style="font-size:12px;margin-top:4px">Satu titik = satu tomat yang terhitung di count gate · '
                    'sudut hue CIELAB kulit buah · batas kelas USDA</div>', icon="scatter_plot", right=poc())
    hist = card("Riwayat lot", history([
        ("10:21", "Lot dibuka", "sistem · palet T-1012-07", "#64748b"),
        ("10:38", "Off-colour di atas 10%", "sistem · alert ke QC Manager", "#f59e0b"),
        ("10:42", "Lot ditutup · hold", "sistem · 41 buah", "#f59e0b"),
        ("10:47", "Sortir ulang ditugaskan · line T2", "Dewi Lestari · QC Manager", "#2563eb"),
        ("—", "Cek ulang setelah sortir", "menunggu", "#cbd5e1")]), icon="history")
    body = (ph("Lot T-1012-07 · Tomat", "Line T1–T4 · Shift 1 · 10:21–10:42 · 41 tomat terhitung (klip PoC)",
               btn("Ekspor sertifikat lot (PDF)", "picture_as_pdf") + btn("Kirim ke QA pembeli", "send"),
               crumb=f'Laporan Lot & Batch {I("chevron_right", size=16)} T-1012-07')
            + grid("1fr 1fr 560px", [comp, check, perc]) + grid("1fr 520px", [ev, audit])
            + grid("1fr 520px", [spread, hist]))
    return app("grading", "lots", body)


def p07_grading_standards() -> str:
    lib = [("Kelas warna tomat USDA", "7 CFR 51.1860–51.1861", "Line T1–T4", "Aktif"),
           ("Bagan warna lemon OECD", "OECD Citrus Fruits · via CBI", "Line L1–L2", "Aktif"),
           ("Warna persik USDA (U.S. Fancy ≥ ⅓ merah)", "7 CFR 51.1210–51.1214", "—", "Draft"),
           ("Spec pembeli · Supermarket X", "spesifikasi pembeli", "—", "Draft")]
    rows = "".join(f'<tr class="{"on" if k == 0 else ""}"><td><b>{a}</b><div class="mut" style="font-size:12px">{b}</div></td>'
                   f'<td class="sec">{c}</td><td>{status(d)}</td></tr>' for k, (a, b, c, d) in enumerate(lib))
    left = card("Standar grade", f'<table class="tbl"><thead><tr><th>Standar</th><th>Dipakai di</th><th>Status</th></tr></thead>'
                f'<tbody>{rows}</tbody></table>', icon="menu_book", right=btn("Standar baru", "add", "sm"), cb_style="padding:10px 6px 6px")
    cls = [("Red", "< 62,1°", "#dc2626"), ("Light Red", "62,1–71,5°", "#f87171"), ("Pink", "71,5–85,7°", "#f472b6"),
           ("Turning", "85,7–101,2°", "#fb923c"), ("Breakers", "101,2–111,2°", "#facc15"), ("Green", "≥ 111,2°", "#22c55e")]
    crow = "".join(f'<div class="row" style="gap:10px;padding:7px 0;border-bottom:1px solid var(--hair)"><i class="sw" style="background:{c};width:14px;height:14px"></i>'
                   f'<b style="width:110px">{a}</b><span class="tn sec">{b}</span></div>' for a, b, c in cls)
    detail = card("Kelas warna tomat USDA", f'''
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
        <div><div class="sect">Kelas · sudut hue kulit (CIELAB)</div>{crow}
          <div class="mut" style="font-size:12px;margin-top:8px">Batas: titik tengah rata-rata colorimeter per kelas USDA yang dipublikasikan.</div></div>
        <div><div class="sect">Aturan lot</div>
          <div class="kv"><span>Limit off-colour</span><span><span class="inp" style="width:90px">10 %</span></span>
          <span>Limit hijau</span><span><span class="inp" style="width:90px">5 %</span></span>
          <span>Jika terlewati</span><span>{bd("Hold lot", "amber")} {bd("Alert QC Manager", "blue")}</span>
          <span>Ukuran lot</span><span><span class="inp" style="width:180px;white-space:nowrap">per palet / 20 menit</span></span></div>
          <div class="sect" style="margin-top:18px">Cek warna</div>
          <div class="kv"><span>Kartu referensi</span><span>{status("Pass")} <span class="mut">· hari ini 06:58 · ΔE 1,8</span></span>
          <span>Setiap</span><span>awal shift {tg(True)}</span></div></div></div>''',
                  icon="tune", right=f'{btn("Uji di rekaman", "play_circle", "sm")}{btn("Simpan", "check", "sm pri")}')
    test = card("Uji di rekaman sebelum go-live", grid("1fr 1fr 1fr 1fr", [
        kpi("nutrition", "green", "Buah di klip uji", "78", "semua tomat yang tampil"),
        kpi("verified", "green", "Sama dengan cek mata", "75 / 78", "cek blind · 3 beda 1 kelas"),
        kpi("rule", "amber", "Keputusan lot", "Mixed Color", "17% off-colour di lot PoC"),
        kpi("schedule", "blue", "Waktu uji", "4 menit", "untuk rekaman 7 hari")], 14), icon="science", right=poc())
    sw = [(235, 187, 43), (216, 190, 64), (205, 191, 59), (194, 183, 59), (184, 180, 63), (169, 174, 66),
          (148, 164, 59), (135, 146, 60), (109, 124, 58), (79, 101, 50)]
    lots = ["Lot 1–3"] * 3 + ["Lot 4–6"] * 3 + ["Lot 7–9"] * 3 + ["Out of grade"]
    chips = "".join(f'<div style="text-align:center"><div style="height:46px;border-radius:8px;background:rgb{c}"></div>'
                    f'<b style="display:block;font-size:14px;margin-top:6px">{k}</b><span class="mut" style="font-size:11.5px">{lots[k - 1]}</span></div>'
                    for k, c in enumerate(sw, 1))
    oecd = card("Bagan warna lemon OECD · line L1–L2", f'<div style="display:grid;grid-template-columns:repeat(10,1fr);gap:8px">{chips}</div>'
                f'<div class="kv" style="margin-top:14px"><span>Diizinkan</span><span>derajat 1–9 untuk Extra, Class I dan II</span>'
                f'<span>Per pengiriman</span><span>maksimal 3 derajat yang berdekatan</span>'
                f'<span>Derajat 10</span><span>{bd("Reject di line", "red")}</span></div>', icon="palette", right=status("Aktif"))
    changes = card("Riwayat perubahan", history([
        ("8 Okt", "Limit off-colour 10% dikonfirmasi", "Dewi Lestari · QC Manager", "#2563eb"),
        ("8 Okt", "Diuji di rekaman 7 hari", "Dewi Lestari · QC Manager", "#16a34a"),
        ("2 Okt", "Bagan lemon OECD ditambahkan", "Rina Hartono · Plant Admin", "#2563eb"),
        ("30 Sep", "Kartu referensi dicetak ulang", "Andi Wijaya · Line Supervisor", "#64748b"),
        ("28 Sep", "Kelas tomat USDA diimpor", "Rina Hartono · Plant Admin", "#2563eb")]), icon="history",
        right='<span class="lnk">Audit log ' + I("chevron_right", size=16) + '</span>')
    body = (ph("Spesifikasi Produk · Standar grade", "Pilih standar per line; QC Manager mengatur limit dan mengujinya dulu di rekaman",
               btn("Impor spec pembeli", "upload")) + grid("520px 1fr", [left, detail]) + test
            + grid("1fr 1fr", [oecd, changes]))
    return app("grading", "specs", body)


# ================================================================== Fill Level Inspection
def p08_fill_overview() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("local_drink", "blue", "Botol diinspeksi hari ini", "48.320", f'{up("3% vs kemarin")}<span>2 line · 16 nozzle</span>'),
        kpi("trending_down", "red", "Reject underfill", "37", "0,08% · sinyal reject dikirim ke PLC"),
        kpi("water_drop", "amber", "Rata-rata overfill", "+3,1 mL", "≈ 150 L produk terbuang (giveaway) hari ini"),
        kpi("check_circle", "green", "Dalam toleransi", "99,2%", "target 500 mL ± 2%"),
    ])
    noz = dev_bars([3.0, 2.0, 9.0, 1.0, -3.0, 3.5, 2.5, 1.5], [f"N{i}" for i in range(1, 9)], 900, 262, -12, 12,
                   (-10, 10), 4, flag=2)
    nz = card("Rata-rata isi vs target per nozzle · Line F1", noz + f'<div class="row" style="gap:12px;margin-top:6px">'
              f'{bd("Nozzle 3 selalu +9 mL di atas target: cek timing valve", "amber", "warning")}'
              f'<span class="mut" style="font-size:12px">target 500 mL · toleransi ±10 mL (±2%)</span></div>',
              icon="bar_chart", right="mL vs target · shift ini")
    tr = card("Reject underfill per jam", vbars([("Line F1", [2, 3, 1, 9, 4, 2, 3, 1], "#2563eb"), ("Line F2", [1, 2, 1, 2, 1, 3, 1, 1], "#93c5fd")],
                                                 ["07", "08", "09", "10", "11", "12", "13", "14"], 560, 262, bw_max=16)
              + legend([("Line F1", "#2563eb"), ("Line F2", "#93c5fd")]), icon="monitoring", right="lonjakan 10:00: level tangki rendah")
    sk = [("Air mineral 500 mL", "F1", "500 mL ± 2%", "24.180", "21", "+2,4 mL"),
          ("Jus 330 mL", "F2", "330 mL ± 2%", "16.900", "12", "+4,0 mL"),
          ("Sirup 620 mL", "F2", "620 mL ± 2%", "7.240", "4", "+3,3 mL")]
    rows = "".join(f'<tr><td><b>{a}</b></td><td>{b}</td><td class="sec tn" style="white-space:nowrap">{c}</td><td class="tn">{d}</td><td class="tn">{e}</td>'
                   f'<td class="tn">{f}</td></tr>' for a, b, c, d, e, f in sk)
    sku = card("SKU shift ini", f'<table class="tbl cp"><thead><tr><th>SKU</th><th>Line</th><th>Target</th><th>Diinspeksi</th>'
               f'<th>Underfill</th><th>Rata-rata overfill</th></tr></thead><tbody>{rows}</tbody></table>', icon="inventory", cb_style="padding:10px 6px 6px")
    rej = card("Reject underfill terbaru", history([
        ("10:41", "Line F1 · nozzle 5 · 486 mL", "di-reject · PLC", "#dc2626"),
        ("10:36", "Line F1 · nozzle 5 · 488 mL", "di-reject · PLC", "#dc2626"),
        ("10:12", "Line F2 · nozzle 2 · 323 mL", "di-reject · PLC", "#dc2626"),
        ("10:04", "Line F1 · 9 botol · tangki rendah", "alert · Line Supervisor", "#f59e0b")]), icon="report",
        right='<span class="lnk">Semua reject ' + I("chevron_right", size=16) + '</span>')
    live = card("Live · Line F1 · nozzle 1", tile(im("fill"), "F1 · Mesin pengisi · CAM 01", "#2563eb", "67%", style="height:205px")
                + f'<div class="mut" style="font-size:12px;margin-top:8px">{poc()} level isi diukur tiap frame dari bentuk botol</div>',
                icon="videocam")
    body = (ph("Ringkasan · Fill Level Inspection", "Hari ini · Shift 1 · line F1–F2",
               btn("Ekspor", "download") + btn("Buka Dashboard TV", "live_tv", "pri"))
            + k + grid("1fr 620px", [nz, tr]) + grid("1fr 1fr 480px", [sku, rej, live]))
    return app("fill", "overview", body)


def p09_tv_fill() -> str:
    return annotated("fill", im("fill", 2, cam=False), "Level isi · nozzle 1", "botol demi botol", "Line F1 · TV", [
        (640, 112, "Kamera live dengan AI", "Outline botol, garis target di leher botol, dan level terukur dalam % dan mL."),
        (1330, 90, "KPI pengisian", "Level isi, flow rate, waktu isi, dan sisa waktu ke target."),
        (1330, 290, "Fill curve", "Level dari waktu ke waktu terhadap band target 98–102%."),
        (1330, 620, "Event Log", "Botol masuk posisi, mulai mengalir, setengah target, keputusan."),
        (40, 820, "Aturan pass / reject", "Di bawah 98% = reject (underfill); di atas 102% = pass, dicatat sebagai giveaway."),
        (680, 820, "Tinggi bukan volume", "Volume dihitung dari bentuk botol, bukan dari tinggi cairan saja.")],
                     "Frame dari video PoC (rekaman nyata Pexels). Klip berakhir di 67% target, jadi PoC ini menunjukkan pengukuran, belum keputusan pass/reject.")


def p10_fill_spec() -> str:
    skus = [("Air mineral 500 mL", "PET 500 · bulat", "Aktif"), ("Jus 330 mL", "Kaca 330 · bulat", "Aktif"),
            ("Sirup 620 mL", "PET 620 · bahu", "Aktif"), ("Saus 340 g", "Kaca 340 · mulut lebar", "Draft")]
    rows = "".join(f'<tr class="{"on" if k == 0 else ""}"><td><b>{a}</b><div class="mut" style="font-size:12px">{b}</div></td><td>{status(c)}</td></tr>'
                   for k, (a, b, c) in enumerate(skus))
    left = card("SKU", f'<table class="tbl"><thead><tr><th>SKU · kemasan</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>',
                icon="inventory", right=btn("SKU baru", "add", "sm"), cb_style="padding:10px 6px 6px")
    rules = [("flag", "#079455", "Target", "500 mL · isi sampai garis leher botol"),
             ("tune", "#0e7490", "Toleransi", "98–102% (490–510 mL) saat nozzle berhenti"),
             ("trending_down", "#dc2626", "Di bawah 490 mL", "Reject · sinyal PLC ke rejector, dalam 0,5 detik"),
             ("water_drop", "#d97706", "Di atas 510 mL", "Pass · dicatat sebagai giveaway · alert jika 5 kali berturut-turut"),
             ("repeat", "#2563eb", "3 reject di satu nozzle", "Alert Line Supervisor · cek nozzle tersebut")]
    rr = "".join(f'<div class="row" style="gap:12px;padding:10px 0;border-bottom:1px solid var(--hair)">{I(ic, True, 20, c)}'
                 f'<b style="width:200px">{a}</b><span class="sec">{b}</span></div>' for ic, c, a, b in rules)
    spec = card("Air mineral 500 mL · aturan isi", f'''<div style="display:grid;grid-template-columns:1fr 420px;gap:28px">
      <div><div class="sect">Pass / reject</div>{rr}
        <div class="mut" style="font-size:12px;margin-top:10px">Atur toleransi sesuai ketentuan BDKT (metrologi legal) dan batas pelanggan untuk SKU ini.</div></div>
      <div><div class="sect">Profil kemasan</div>
        <div class="kv"><span>Kapasitas s/d garis leher</span><span><span class="inp" style="width:110px">500 mL</span></span>
        <span>Bentuk botol</span><span>diukur dari 3 botol kosong {status("Pass")}</span>
        <span>Tinggi → volume</span><span>dari outline botol {poc()}</span>
        <span>Nozzle</span><span><span class="inp" style="width:110px">8 per line</span></span>
        <span>Kamera</span><span>CAM 01 · tampak samping, backlight</span></div></div></div>''',
                icon="rule", right=f'{btn("Uji di rekaman", "play_circle", "sm")}{btn("Simpan", "check", "sm pri")}')
    gv = card("Giveaway minggu ini · Line F1", lines([("Rata-rata overfill", [3.6, 3.4, 3.9, 3.1, 2.8, 2.6, 2.4], "#d97706")],
                                                    ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"], 1000, 330, hi=5, ticks=5,
                                                    ref=("sasaran +2 mL", 2), fmt=lambda v: f"+{v:.0f} mL", area=True)
              + '<div class="mut" style="font-size:12px;margin-top:6px">Turun dari +3,6 ke +2,4 mL per botol setelah garis target dipindah hari Kamis: '
                '≈ 200 L produk terbuang lebih sedikit per minggu di line ini.</div>',
              icon="water_drop", right="mL per botol di atas target")
    pr = card("Sebelum go-live", f'''<div class="col" style="gap:10px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Garis target diatur dengan 3 botol referensi</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Sinyal reject diuji dengan PLC (Modbus TCP)</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Kamera terpasang tetap, backlight menyala, diuji di rekaman 7 hari</div>
      <div class="row" style="gap:8px">{I("radio_button_unchecked", False, 18, "#94a3b8")}Perbandingan dengan check weigher pada 50 botol</div>
      <div class="row" style="gap:8px">{I("radio_button_unchecked", False, 18, "#94a3b8")}Persetujuan QC Manager</div></div>''',
                icon="checklist", right="3 dari 5")
    chg = card("Riwayat perubahan", history([
        ("Kam", "Garis target diturunkan 2 mm", "Dewi Lestari · QC Manager", "#2563eb"),
        ("Sel", "Sinyal reject diuji", "Rina Hartono · Plant Admin", "#16a34a"),
        ("Sen", "Toleransi diatur ±2%", "Dewi Lestari · QC Manager", "#2563eb")]), icon="history")
    body = (ph("Spesifikasi Produk · Aturan isi", "Target, toleransi, dan tindakan per SKU; bentuk botol mengubah tinggi cairan menjadi volume",
               btn("Impor daftar SKU", "upload")) + grid("440px 1fr", [left, spec])
            + grid("1fr 560px", [gv, f'<div class="col" style="gap:18px">{pr}{chg}</div>']))
    return app("fill", "specs", body)


# ================================================================== Pack Count QC
def p11_pack_overview() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("fact_check", "amber", "Pack diinspeksi hari ini", "12.480", f'{up("2% vs kemarin")}<span>tray + kardus</span>'),
        kpi("production_quantity_limits", "red", "Short pack tertangkap", "23", "0,18% · di-hold sebelum disegel"),
        kpi("remove_circle", "amber", "Item kurang", "31", "semua dilengkapi sebelum dikirim"),
        kpi("conveyor_belt", "blue", "Feeder gap", "9", "penyebab 14 dari 31 item kurang"),
    ])
    tr = card("Short pack per jam", vbars([("Line kaleng C1 · tray", [1, 2, 4, 3, 2, 1, 1, 2], "#d97706"),
                                           ("Packing station P1 · kardus", [0, 1, 1, 2, 1, 1, 0, 1], "#fbbf24")],
                                           ["07", "08", "09", "10", "11", "12", "13", "14"], 780, 226, bw_max=16, ymax=4)
              + legend([("Line kaleng C1 · tray", "#d97706"), ("Packing station P1 · kardus", "#fbbf24")]),
              icon="monitoring", right="di-hold sebelum disegel")
    heat = card("Posisi item yang sering kosong · tray kaleng", f'''<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px">
      {"".join(f'<div style="height:64px;border-radius:8px;background:{c};display:flex;align-items:flex-end;justify-content:space-between;padding:8px 10px;font-size:13px"><b>{n}</b><span class="tn" style="font-size:16px;font-weight:600">{v}</span></div>'
               for n, v, c in [("A1", "0", "#f1f5f9"), ("A2", "6", "#d97706"), ("A3", "4", "#f59e0b"), ("A4", "0", "#f1f5f9"), ("A5", "1", "#fde7c2"),
                               ("B1", "0", "#f1f5f9"), ("B2", "0", "#f1f5f9"), ("B3", "1", "#fde7c2"), ("B4", "0", "#f1f5f9"), ("B5", "3", "#fbbf24")])}</div>
      <div class="row" style="justify-content:space-between;margin-top:6px;font-size:12px" class="mut"><span class="mut">lane filler 1 → 5</span><span class="mut">kaleng kurang per slot · 3.410 tray</span></div>
      <div style="margin-top:12px;padding:12px 14px;border-radius:10px;background:#eff6ff;font-size:13.5px;line-height:1.5">{I("insights", True, 18, "#2563eb")} <b>Slot A2 kosong 6× minggu ini</b>, A3 4×: lane filler 2 dan 3, bersebelahan. Cek guide kedua lane sebelum shift berikutnya.</div>''',
                icon="grid_view", right="minggu ini")
    ev = [("snap_box_461.jpg", "high", "Kardus #2 keluar kurang 2", "18/20 · slot B2, C5 kosong · di-hold", "P1", "10:41"),
          ("snap_tray_413.jpg", "high", "Tray #7 kurang 1 kaleng", "9/10 · slot B5 kosong · di-reject", "C1", "10:39"),
          ("snap_box_284.jpg", "medium", "Empty pick · slot B2", "robot bergerak tanpa produk · penyebab: feeder gap", "P1", "10:36"),
          ("snap_tray_222.jpg", "high", "Tray #4 kurang 1 kaleng", "9/10 · slot A3 kosong · di-reject", "C1", "10:34")]
    rows = "".join(f'<div class="ev"><img class="thumb" src="../img/{a}" style="width:112px;height:63px"><div class="grow">'
                   f'<div class="t1">{b}</div><div class="t2">{c}</div></div>{sev(s)}<span class="cam">{I("videocam", True)}{d}</span>'
                   f'<span class="mut tn" style="width:44px;text-align:right">{e}</span></div>' for a, s, b, c, d, e in ev)
    evc = card("Reject & kejadian terbaru", rows, icon="report", right=poc())
    live = card("Live", grid("1fr", [tile(im("tray"), "C1 · Line kaleng · CAM 03", "#d97706", "", style="height:150px"),
                                     tile(im("packing", 1), "P1 · Robot packing · CAM 04", "#d97706", "", style="height:150px")], 10),
                icon="videocam")
    body = (ph("Ringkasan · Pack Count QC", "Hari ini · Shift 1 · line kaleng C1 dan packing station P1",
               btn("Ekspor", "download") + btn("Buka Dashboard TV", "live_tv", "pri"))
            + k + grid("1fr 1fr", [tr, heat]) + grid("1fr 480px", [evc, live]))
    return app("pack", "overview", body)


def p12_tv_tray() -> str:
    return annotated("pack", im("tray", 2, cam=False), "Tray kaleng · 10 per tray", "ujung line pengisian", "Line C1 · TV", [
        (640, 112, "Kamera live dengan AI", "Setiap kaleng terdeteksi; slot kosong dilingkari merah dan tray ditandai SHORT."),
        (1330, 90, "KPI line", "Tray diinspeksi, tray kurang isi, kaleng kurang, kecepatan line."),
        (1330, 290, "Missing can positions", "Slot mana yang kosong dan apakah berulang: menunjuk ke satu lane filler."),
        (1330, 620, "Event Log", "Setiap tray kurang isi lengkap dengan foto, untuk di-reject."),
        (40, 820, "Last trays", "Jumlah isi dan pass / reject per tray."),
        (680, 820, "Trays inspected, cumulative", "Tray diinspeksi vs tray kurang, plus hasil uji vs data kebenaran.")],
                     "Frame dari video PoC (simulasi 3D dengan data kebenaran: 7/7 tray benar). Di produk: kamera di atas ujung line.")


def p13_tv_packing() -> str:
    return annotated("pack", im("packing", 1, cam=False), "Robot packing · 20 per kardus", "kardus diisi slot demi slot", "Station P1 · TV", [
        (640, 112, "Kamera live dengan AI", "Setiap slot kardus dipantau saat robot mengisi; empty pick diberi tanda silang merah."),
        (1330, 90, "KPI station", "Kardus di station, kardus selesai, empty pick, kecepatan robot."),
        (1330, 290, "Slot map", "Terisi, empty pick, slot berikutnya, sisa slot."),
        (1330, 620, "Event Log", "Feeder gap, empty pick, kardus kurang keluar: sebab dan akibat berurutan."),
        (40, 820, "Box history", "Setiap kardus yang keluar: jumlah isi, slot kosong, dan tindakan (seal & kirim atau hold & tambah)."),
        (680, 820, "Box count at station", "Jumlah isi dari waktu ke waktu terhadap standar 20.")],
                     "Frame dari video PoC (simulasi 3D dengan data kebenaran: 3/3 kardus dan 2/2 empty pick terdeteksi).")


def p14_pack_reject() -> str:
    tl = [("10:36:12", "conveyor_belt", "Feeder gap", "stopper kosong · slot B2 berisiko", "#2563eb"),
          ("10:36:14", "report", "Empty pick · slot B2", "robot bergerak tanpa produk", "#d97706"),
          ("10:38:57", "conveyor_belt", "Feeder gap", "stopper kosong · slot C5 berisiko", "#2563eb"),
          ("10:39:01", "report", "Empty pick · slot C5", "robot bergerak tanpa produk", "#d97706"),
          ("10:41:20", "production_quantity_limits", "Kardus #2 keluar kurang 2", "18/20 · di-hold di outfeed", "#dc2626"),
          ("10:41:31", "chat", "WhatsApp ke Line Supervisor", "Andi Wijaya · dibaca 10:41:40", "#079455"),
          ("10:44:02", "task_alt", "Rework & cek ulang", "20/20 · di-release oleh Andi Wijaya", "#079455")]
    steps = "".join(f'<div class="row" style="gap:12px;align-items:flex-start;padding:8px 0"><span class="mut tn" style="width:64px;font-size:12.5px;padding-top:2px">{a}</span>'
                    f'<span class="it" style="width:28px;height:28px;background:{c}1a;color:{c}">{I(ic, True, 17)}</span>'
                    f'<div><b style="font-size:13.5px">{t}</b><div class="mut" style="font-size:12.5px">{d}</div></div></div>' for a, ic, t, d, c in tl)
    ev = card("Bukti", f'<img class="thumb" src="../img/snap_box_461.jpg" style="width:100%;height:auto;aspect-ratio:16/9">'
              f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">'
              f'<img class="thumb" src="../img/snap_box_284.jpg" style="width:100%;height:auto;aspect-ratio:16/9">'
              f'<img class="thumb" src="../img/snap_box_412.jpg" style="width:100%;height:auto;aspect-ratio:16/9"></div>'
              f'<div class="row" style="gap:10px;margin-top:12px">{btn("Putar klip −10 / +10 detik", "play_circle")}{btn("Ekspor PDF", "picture_as_pdf")}</div>'
              f'<div class="kv" style="margin-top:16px"><span>Kamera</span><span>CAM 04 · tampak atas di outfeed</span>'
              f'<span>Pembacaan isi</span><span>tiap frame selama kardus terlihat · stabil di 18 sebelum keluar</span>'
              f'<span>Klip disimpan</span><span>30 hari (90 hari dengan add-on) · ekspor untuk arsip</span></div>',
              icon="photo_library", right=poc())
    slots = "".join(f'<div style="height:44px;border-radius:8px;display:flex;align-items:center;justify-content:space-between;padding:0 10px;'
                    f'font-size:12.5px;font-weight:600;{"background:#dc2626;color:#fff" if n in ("B2", "C5") else "background:#dcfce7;color:#166534"}">'
                    f'{n}{I("cancel" if n in ("B2", "C5") else "check_circle", True, 17)}</div>'
                    for n in [f"{r}{c}" for r in "ABCD" for c in range(1, 6)])
    det = card("Kardus #2 · Packing station P1", f'''
      <div class="row" style="gap:10px;margin-bottom:12px">{bd("Tinggi", "red", "error")}{status("Rework")}<span class="mut">SKU Snack Box 20 · Lot P-1012-11</span></div>
      <div class="kv"><span>Jumlah isi</span><b class="tn">18 / 20</b><span>Slot kosong</span><b>B2, C5</b>
      <span>Root cause</span><span>Feeder gap sebelum setiap empty pick {poc()}</span><span>PIC</span><span>{avatar("Andi Wijaya", 24)} Andi Wijaya</span></div>
      <div class="sect" style="margin-top:16px">Peta slot</div><div style="display:grid;grid-template-columns:repeat(5,1fr);gap:7px">{slots}</div>''',
               icon="inventory_2", right=status("Selesai"))
    capa = card("Corrective action", f'''<div class="col" style="gap:10px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Tambah 2 item, cek ulang 20/20, release</div>
      <div class="row" style="gap:8px">{I("pending", True, 18, "#d97706")}Naikkan level buffer feeder · Maintenance · tenggat Jumat</div>
      <div class="row" style="gap:8px">{I("pending", True, 18, "#d97706")}Alert jika 2 feeder gap dalam 5 menit</div></div>''', icon="build")
    body = (ph("Reject · Kardus #2 kurang 2", "Packing station P1 · 10:41 · di-hold di outfeed, di-rework lalu di-release",
               btn("Override (perlu QC Manager)", "gavel") + btn("Tutup", "check", "pri"),
               crumb=f'Reject & Kejadian {I("chevron_right", size=16)} P1-0412')
            + grid("1fr 560px 460px", [f'<div class="col" style="gap:18px">{det}{capa}</div>', ev, card("Timeline", steps + f'''
      <div class="sect" style="margin-top:14px">Penyebab sama minggu ini</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
        <div class="card" style="padding:12px 14px;gap:2px"><b style="font-size:22px">9</b><span class="mut" style="font-size:12px">feeder gap</span></div>
        <div class="card" style="padding:12px 14px;gap:2px"><b style="font-size:22px">14</b><span class="mut" style="font-size:12px">item kurang</span></div>
        <div class="card" style="padding:12px 14px;gap:2px"><b style="font-size:22px">6</b><span class="mut" style="font-size:12px">kardus di-hold</span></div></div>
      <div class="mut" style="font-size:12.5px;margin-top:10px">Ke-6 kardus tertangkap sebelum disegel · 0 komplain pelanggan minggu ini</div>''', icon="timeline")],
                   18, "flex:1;min-height:0"))
    return app("pack", "events", body, user=("Andi Wijaya", "Line Supervisor", "amber"))


# ================================================================== Parcel Dimensioning
PARCELS = [(18, 444, 427, 138, "M", ""), (15, 462, 362, 159, "M", ""), (20, 282, 234, 102, "S", "?"),
           (1, 689, 465, 366, "L", ""), (23, 391, 338, 108, "M", ""), (4, 383, 352, 140, "M", ""),
           (24, 376, 313, 268, "M", ""), (28, 754, 543, 341, "L", "")]


def p15_parcel_overview() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("package_2", "violet", "Paket terukur hari ini", "3.240", f'{up("8% vs kemarin")}<span>belt outbound OB1</span>'),
        kpi("view_in_ar", "violet", "Volume terkirim", "142 m³", "rata-rata 44 L per paket"),
        kpi("scale", "blue", "Berat volumetrik", "23,6 t", "P × L × T ÷ 6000 · vs 18,1 t di timbangan"),
        kpi("straighten", "amber", "Manual check", "41", "1,3% · ukuran dekat batas kelas"),
    ])
    col = {"S": "#22d3ee", "M": "#3b82f6", "L": "#7c3aed"}
    rows = "".join(
        f'<tr><td><b>#{t}</b></td><td class="tn">{l / 10:.0f} × {w / 10:.0f} × {h / 10:.0f} cm</td>'
        f'<td class="tn">{num(l * w * h / 1e6, 1)} L</td><td class="tn">{num(l * w * h / 6e6, 1)} kg</td>'
        f'<td><span class="bd" style="background:{col[c]}22;color:{col[c]}">{c}{m}</span></td>'
        f'<td>{status("Cek", "#d97706") if m else status("Pass")}</td></tr>' for t, l, w, h, c, m in PARCELS)
    log = card("Log paket", f'<table class="tbl cp"><thead><tr><th>Paket</th><th>P × L × T</th><th>Volume</th><th>Berat vol.</th>'
               f'<th>Kelas</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>', icon="list_alt",
               right=poc() + " 8 paket dari klip PoC", cb_style="padding:10px 6px 6px")
    mix = card("Komposisi ukuran hari ini", hbars([("S · sisi terpanjang < 30 cm", 812, "#22d3ee"), ("M · 30–60 cm", 1904, "#3b82f6"),
                                                  ("L · > 60 cm", 524, "#7c3aed")], label_w=200, fmt=lambda v: num(v)),
               icon="category", right="paket")
    tr = card("Paket per jam", vbars([("Paket", [310, 420, 465, 512, 448, 396, 380, 309], "#7c3aed")],
                                        ["07", "08", "09", "10", "11", "12", "13", "14"], 760, 180, bw_max=28, ymax=600), icon="monitoring",
              right="puncak 512 pada 10:00")
    vol = card("Volume per jam", lines([("Volume terukur", [13.8, 18.2, 20.1, 23.0, 19.6, 17.1, 16.8, 13.4], "#7c3aed")],
                                        ["07", "08", "09", "10", "11", "12", "13", "14"], 760, 180, hi=24, area=True,
                                        fmt=lambda v: f"{v:.0f} m³"), icon="view_in_ar", right="m³ per jam · rencanakan truk lebih awal")
    live = card("Live · belt OB1", tile(im("parcel"), "OB1 · Belt outbound · CAM 05", "#7c3aed", "8 terhitung", style="height:200px"),
                icon="videocam")
    body = (ph("Ringkasan · Parcel Dimensioning", "Hari ini · Shift 1 · belt outbound OB1",
               btn("Ekspor manifest (CSV)", "download") + btn("Buka Dashboard TV", "live_tv", "pri"))
            + k + grid("1fr 600px", [log, f'<div class="col" style="gap:18px">{mix}{live}</div>'])
            + grid("1fr 1fr", [tr, vol]))
    return app("parcel", "overview", body)


def p16_tv_parcel() -> str:
    return annotated("parcel", im("parcel", 2, cam=False), "Paket di belt · ukuran & volume", "belt teleskopik di truk", "Belt OB1 · TV", [
        (640, 112, "Kamera live dengan AI", "Setiap paket diberi kotak sesuai kelas ukurannya, lengkap dengan P × L × T dan volume."),
        (60, 230, "Count line", "Setiap paket dihitung sekali saat melintas."),
        (1330, 90, "KPI belt", "Paket terhitung, volume, laju per jam, manual check."),
        (1330, 290, "Parcels measured", "Ukuran akhir setiap paket sebelum count line."),
        (1330, 620, "Event Log", "Setiap paket; ukuran yang dekat batas kelas ditandai untuk manual check."),
        (40, 820, "Size mix", "S / M / L menurut jumlah dan volume."),
        (680, 820, "Volume handled", "Volume kumulatif dalam liter, plus uji terhadap hitungan manual.")],
                     "Frame dari video PoC (rekaman nyata Pexels): 8 dari 8 paket terhitung; karton uji terbaca 340,5 mm vs 340 mm.")


def p17_parcel_load() -> str:
    trucks = [("Truk 01 · Jakarta", "CDD box · 16 m³", 92, "Selesai muat", "#079455"), ("Truk 02 · Bandung", "CDD box · 16 m³", 78, "Sedang muat", "#2563eb"),
              ("Truk 03 · Surabaya", "Fuso box · 32 m³", 41, "Sedang muat", "#2563eb"), ("Truk 04 · Semarang", "CDD box · 16 m³", 0, "Terjadwal", "#94a3b8")]
    rows = "".join(f'<div style="padding:12px 0;border-bottom:1px solid var(--hair)"><div class="row"><b>{a}</b><span class="mut">{b}</span>'
                   f'<span style="margin-left:auto">{status(d, c)}</span></div><div class="row" style="gap:12px;margin-top:8px">'
                   f'<div class="prog grow" style="height:10px"><i style="width:{p}%;background:{c}"></i></div><b class="tn" style="width:44px;text-align:right">{p}%</b></div></div>'
                   for a, b, p, d, c in trucks)
    tk = card("Isi truk dari volume terukur", rows, icon="local_shipping", right="live dari belt OB1")
    bil = card("Berat volumetrik vs berat aktual · per pelanggan", vbars(
        [("Berat aktual", [4.2, 3.1, 2.6, 1.9, 1.4], "#94a3b8"), ("Berat volumetrik", [6.1, 3.3, 4.0, 1.8, 2.2], "#7c3aed")],
        ["Plg. A", "Plg. B", "Plg. C", "Plg. D", "Plg. E"], 900, 190, fmt=lambda v: f"{v:.0f} t", bw_max=30, ymax=8,
        tip=(0, 30, 20, "Pelanggan A · hari ini")) + legend([("Berat aktual", "#94a3b8"), ("Berat volumetrik", "#7c3aed")])
        + f'<div style="margin-top:10px;font-size:13.5px">{I("insights", True, 18, "#7c3aed")} Pelanggan A mengirim paket ringan tapi besar: '
          f'ditagih berdasarkan volume, bukan berat timbangan.</div>', icon="scale", right="ton hari ini")
    chk = card("Antrean manual check", "".join(
        f'<div class="ev"><span class="it amber">{I("straighten", True, 18)}</span><div class="grow"><div class="t1">{a}</div>'
        f'<div class="t2">{b}</div></div>{btn("Konfirmasi ukuran", None, "sm")}</div>'
        for a, b in [("Paket #20 · S? dekat 30 cm", "28 × 23 × 10 cm · 7 L · terbaca dekat batas S/M"),
                     ("Paket #3311 · M? dekat 60 cm", "58 × 41 × 30 cm · 71 L"),
                     ("Paket #3318 · L? dekat 60 cm", "61 × 40 × 22 cm · 54 L")]), icon="rule", right="3 terbuka")
    cus = [("Pelanggan A", "612", "36,6", "4,2", "6,1", "Volume"), ("Pelanggan B", "498", "19,8", "3,1", "3,3", "Volume"),
           ("Pelanggan C", "455", "24,0", "2,6", "4,0", "Volume"), ("Pelanggan D", "390", "10,8", "1,9", "1,8", "Berat"),
           ("Pelanggan E", "287", "13,2", "1,4", "2,2", "Volume")]
    br = "".join(f'<tr><td><b>{a}</b></td><td class="tn">{b}</td><td class="tn">{c} m³</td><td class="tn">{d} t</td>'
                 f'<td class="tn">{e} t</td><td>{bd(f, "violet" if f == "Volume" else "slate")}</td></tr>' for a, b, c, d, e, f in cus)
    bill = card("Dasar tagihan hari ini", f'<table class="tbl cp"><thead><tr><th>Pelanggan</th><th>Paket</th><th>Volume</th>'
                f'<th>Aktual</th><th>Volumetrik</th><th>Ditagih per</th></tr></thead><tbody>{br}</tbody></table>',
                icon="receipt_long", right="yang lebih besar dari keduanya", cb_style="padding:10px 6px 6px")
    dest = card("Volume per tujuan hari ini", hbars([("Jakarta", 58, "#7c3aed"), ("Bandung", 31, "#7c3aed"), ("Surabaya", 29, "#7c3aed"),
                                                     ("Semarang + lainnya", 24, "#7c3aed")], label_w=150,
                                                    fmt=lambda v: f"{num(v)} m³"), icon="map", right="dasar jumlah truk")
    gap7 = card("Selisih berat volumetrik vs aktual · 7 hari", lines(
        [("Berat volumetrik", [21.8, 22.4, 23.1, 22.0, 24.2, 19.5, 23.6], "#7c3aed"), ("Berat aktual", [16.9, 17.2, 17.8, 16.8, 18.6, 15.1, 18.1], "#94a3b8")],
        ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"], 900, 120, lo=10, hi=25, ticks=3, fmt=lambda v: f"{v:.0f} t")
        + legend([("Berat volumetrik", "#7c3aed"), ("Berat aktual", "#94a3b8")]), icon="monitoring",
        right="± 5 t per hari yang tidak tertagih jika memakai timbangan saja")
    body = (ph("Outbound · Rencana muat & tagihan", "Volume terukur per paket dipakai untuk muat truk dan tagihan berat volumetrik",
               btn("Ekspor ke TMS / WMS", "sync_alt") + btn("Kirim data invoice", "receipt_long", "pri"))
            + grid("620px 1fr", [tk, bil], 18) + grid("1fr 1fr", [chk, bill]) + grid("620px 1fr", [dest, gap7]))
    return app("parcel", "reports", body)


# ================================================================== shared pages
def p18_alerts() -> str:
    rules = [("nutrition", "#16a34a", "Produce Grading", "Off-colour lot di atas limit", "Hold lot · WhatsApp QC Manager", "High"),
             ("nutrition", "#16a34a", "Produce Grading", "Lemon warna derajat 10", "Reject di line · dicatat", "Medium"),
             ("local_drink", "#2563eb", "Fill Level", "Botol di bawah toleransi", "Sinyal reject ke PLC · dicatat", "High"),
             ("local_drink", "#2563eb", "Fill Level", "3 reject di satu nozzle dalam 10 menit", "WhatsApp Line Supervisor", "Medium"),
             ("inventory_2", "#d97706", "Pack Count QC", "Tray / kardus kurang isi", "Alihkan ke lane rework · alert", "High"),
             ("inventory_2", "#d97706", "Pack Count QC", "2 feeder gap dalam 5 menit", "Alert Maintenance", "Low"),
             ("package_2", "#7c3aed", "Parcel Dimensioning", "Ukuran dekat batas kelas", "Masuk antrean manual check", "Low")]
    sv = {"High": "high", "Medium": "medium", "Low": "low"}
    rows = "".join(f'<tr><td><span class="row" style="gap:8px">{I(ic, True, 18, c)}{p}</span></td><td><b>{a}</b></td>'
                   f'<td class="sec">{b}</td><td>{sev(sv[s])}</td><td>{tg(True)}</td></tr>' for ic, c, p, a, b, s in rules)
    rc = card("Aturan alert", f'<table class="tbl cp"><thead><tr><th>Produk</th><th>Kapan</th><th>Lalu</th><th>Tingkat</th><th>Aktif</th></tr></thead>'
              f'<tbody>{rows}</tbody></table>', icon="rule", right=btn("Aturan baru", "add", "sm"), cb_style="padding:10px 6px 6px")
    ints = [("settings_input_component", "PLC / SCADA", "OPC UA · Modbus TCP · output digital ke rejector", "Terhubung"),
            ("factory", "MES", "lot, SKU, dan hasil per shift", "Terhubung"),
            ("account_tree", "ERP", "SAP · Oracle · Odoo · catatan batch & kualitas", "Tersedia"),
            ("warehouse", "WMS / TMS", "dimensi paket, muat truk", "Tersedia"),
            ("chat", "WhatsApp Business", "alert berfoto ke orang yang tepat", "Terhubung"),
            ("webhook", "Webhook & REST API", "setiap kejadian dan pengukuran, real time", "Terhubung")]
    ir = "".join(f'<div class="ev"><span class="it slate">{I(ic, True, 19)}</span><div class="grow"><div class="t1">{a}</div>'
                 f'<div class="t2">{b}</div></div>{status("Online" if d == "Terhubung" else "Tersedia", "#079455" if d == "Terhubung" else "#94a3b8")}</div>'
                 for ic, a, b, d in ints)
    ic = card("Integrasi", ir, icon="hub")
    esc = card("Eskalasi", f'''<div class="col" style="gap:10px;font-size:13.5px">
      <div class="row" style="gap:10px">{bd("Tinggi", "red", "error")}<span>Line Supervisor langsung → QC Manager setelah 5 menit → Plant Admin setelah 15 menit</span></div>
      <div class="row" style="gap:10px">{bd("Sedang", "amber", "warning")}<span>Line Supervisor · ringkasan shift ke QC Manager</span></div>
      <div class="row" style="gap:10px">{bd("Rendah", "blue", "info")}<span>Hanya di laporan shift</span></div></div>''', icon="campaign")
    wa = card("Contoh pesan WhatsApp", f'''<div style="background:#e7f6e7;border-radius:12px;padding:12px;font-size:13px;line-height:1.45">
      <b>Factory Vision · Pabrik A</b><br>{I("error", True, 16, "#dc2626")} <b>Kardus #2 keluar kurang 2</b> · Packing station P1 · 10:41<br>
      18/20 · slot B2, C5 kosong · di-hold di outfeed<img class="thumb" src="../img/snap_box_461.jpg" style="width:100%;height:230px;object-fit:cover;margin-top:8px">
      <div class="mut" style="margin-top:6px">Balas 1 = saya tangani · 2 = alarm palsu</div></div>''', icon="chat")
    sent = card("Alert terkirim hari ini", history([
        ("10:41", "Kardus #2 keluar kurang 2 · P1", "WhatsApp · Andi Wijaya · dibaca dalam 9 detik", "#dc2626"),
        ("10:38", "Lot T-1012-07 off-colour 17%", "WhatsApp · Dewi Lestari · dibaca dalam 1 menit", "#dc2626"),
        ("10:04", "9 underfill · Line F1 · tangki rendah", "WhatsApp · Andi Wijaya · dibaca dalam 20 detik", "#f59e0b"),
        ("09:12", "Feeder gap · P1", "email · Maintenance", "#2563eb")]), icon="send", right="24 terkirim · 0 terlewat")
    body = (ph("Alert & Integrasi", "Satu set aturan untuk semua produk: siapa diberi tahu, apa yang dilakukan line, sistem mana yang menerima data")
            + grid("1fr 560px", [f'<div class="col" style="gap:18px">{rc}{esc}{sent}</div>', f'<div class="col" style="gap:18px">{ic}{wa}</div>'], 18, "flex:1;min-height:0"))
    return app("pack", "alerts", body, user=("Rina Hartono", "Plant Admin", "blue"))


def p19_cameras() -> str:
    cams = [("CAM 01", "T1–T4 · Packing tomat", "grading", "Online", "30 fps", "Pass", "06:58"),
            ("CAM 02", "L1–L2 · Chain lemon", "grading", "Online", "30 fps", "Pass", "06:59"),
            ("CAM 03", "C1 · Ujung line kaleng", "pack", "Online", "30 fps", "Pass", "07:01"),
            ("CAM 04", "P1 · Robot packing", "pack", "Online", "25 fps", "Pass", "07:01"),
            ("CAM 05", "OB1 · Belt outbound", "parcel", "Online", "30 fps", "Pass", "07:03"),
            ("CAM 06", "F1 · Filler nozzle 1–4", "fill", "Online", "25 fps", "Pass", "07:04"),
            ("CAM 07", "F1 · Filler nozzle 5–8", "fill", "Cek", "25 fps", "Silau di lensa", "07:04"),
            ("CAM 08", "F2 · Filler", "fill", "Jeda", "—", "Line berhenti", "—")]
    rows = "".join(f'<tr><td><span class="cam">{I("videocam", True)}{a}</span></td><td><b>{b}</b></td>'
                   f'<td><span class="row" style="gap:6px">{I(PRODUCTS[c][0], True, 17, PRODUCTS[c][2])}{PRODUCTS[c][1]}</span></td>'
                   f'<td>{status(d, {"Online": "#079455", "Cek": "#d97706", "Jeda": "#94a3b8"}[d])}</td><td class="tn">{e}</td>'
                   f'<td>{bd(f, "green" if f == "Pass" else "amber" if d == "Cek" else "slate")}</td><td class="mut tn">{g}</td></tr>'
                   for a, b, c, d, e, f, g in cams)
    cc = card("Kamera", f'<table class="tbl cp"><thead><tr><th>Kamera</th><th>Line</th><th>Produk</th><th>Status</th><th>Frame rate</th>'
              f'<th>Cek gambar</th><th>Cek terakhir</th></tr></thead><tbody>{rows}</tbody></table>', icon="photo_camera",
              right=btn("Tambah kamera (RTSP / ONVIF)", "add", "sm"), cb_style="padding:10px 6px 6px")
    edges = [("Edge box 01", "CAM 01–04", "41%", "18 ms"), ("Edge box 02", "CAM 05–08", "33%", "21 ms")]
    er = "".join(f'<div class="ev"><span class="it green">{I("memory", True, 19)}</span><div class="grow"><div class="t1">{a}</div>'
                 f'<div class="t2">{b} · GPU {c} · latency {d}</div></div>{status("Online")}</div>' for a, b, c, d in edges)
    ec = card("Edge AI box", er + f'<div class="mut" style="font-size:12px;margin-top:8px">Update model AI dipasang vendor line demi line, bisa di-rollback.</div>',
              icon="memory")
    setup = card("Kamera baru · cek CAM 07", f'''<div style="display:grid;grid-template-columns:1fr;gap:14px">
      <img class="thumb" src="{im("fill", 1)}" style="width:100%;height:200px;object-fit:cover">
      <div class="col" style="gap:8px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Produk fokus di titik inspeksi</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Frame rate ≥ 25 fps</div>
      <div class="row" style="gap:8px">{I("warning", True, 18, "#d97706")}Silau di sisi kanan lensa — pasang filter polarisasi atau geser 10 cm</div>
      <div class="row" style="gap:8px">{I("radio_button_unchecked", False, 18, "#94a3b8")}Cek warna dengan kartu referensi</div></div></div>''',
                  icon="center_focus_strong", right=status("Cek", "#d97706"))
    up7 = card("Uptime kamera · 7 hari, saat line jalan", hbars([(a, v, "#16a34a" if v >= 99 else "#d97706") for a, v in [
        ("CAM 01 · T1–T4", 99.8), ("CAM 02 · L1–L2", 99.6), ("CAM 03 · C1", 99.9), ("CAM 04 · P1", 99.7),
        ("CAM 05 · OB1", 99.5), ("CAM 06 · F1", 99.9), ("CAM 07 · F1", 97.2)]], vmax=100, label_w=150, fmt=lambda v: f"{num(v, 1)}%"),
        icon="monitor_heart")
    guide = card("Posisi kamera · yang perlu disiapkan pabrik", f'''<div class="col" style="gap:9px;font-size:13.5px">
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Dudukan tetap di atas atau samping line; tidak di-pan/zoom saat line jalan</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Cahaya merata di produk; backlight untuk botol</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Jaringan ke edge box (PoE) dan listrik untuk box</div>
      <div class="row" style="gap:8px">{I("check_circle", True, 18, "#079455")}Kamera IP yang ada bisa dipakai jika lolos cek gambar</div></div>''',
                  icon="checklist")
    body = (ph("Line & Kamera", "Setiap kamera dicek sebelum dipakai: fokus, frame rate, silau, warna",
               btn("Jalankan semua cek", "fact_check")) + cc + grid("1fr 1fr 1fr", [setup, f'<div class="col" style="gap:18px">{ec}{guide}</div>', up7]))
    return app("fill", "cameras", body, user=("Rina Hartono", "Plant Admin", "blue"))


def p20_multi_plant() -> str:
    plants = [("Pabrik A · Cikarang", ["grading", "fill", "pack", "parcel"], "99,2%", "0,14%", "1", "+2,5 mL"),
              ("Pabrik B · Surabaya", ["fill", "pack"], "98,7%", "0,22%", "0", "+3,8 mL"),
              ("Pabrik C · Medan", ["grading"], "96,4%", "—", "2", "—"),
              ("DC Jakarta", ["parcel"], "—", "—", "0", "—")]
    rows = "".join(f'<tr><td><b>{a}</b></td><td><span class="row" style="gap:4px">'
                   + "".join(f'<span class="it {PRODUCTS[p][3]}" style="width:26px;height:26px">{I(PRODUCTS[p][0], True, 15)}</span>' for p in ps)
                   + f'</span></td><td class="tn">{b}</td><td class="tn">{c}</td><td class="tn">{d}</td><td class="tn">{e}</td>'
                     f'<td>{spark(sp)}</td></tr>' for (a, ps, b, c, d, e), sp in zip(plants, [[6, 5, 5, 4, 4, 3, 3], [4, 5, 4, 4, 5, 4, 4],
                                                                                         [3, 4, 4, 5, 6, 6, 7], [2, 2, 3, 2, 2, 2, 2]]))
    tb = card("Semua pabrik · minggu ini", f'<table class="tbl"><thead><tr><th>Pabrik</th><th>Produk</th><th>First-pass quality</th>'
              f'<th>Short-pack rate</th><th>Lot di-hold</th><th>Rata-rata overfill</th><th>Reject · 7 hari</th></tr></thead><tbody>{rows}</tbody></table>',
              icon="factory", cb_style="padding:10px 6px 6px")
    comp = card("First-pass quality · 12 minggu", lines([("Pabrik A", [97.1, 97.5, 97.8, 98.0, 98.2, 98.4, 98.6, 98.7, 98.9, 99.0, 99.1, 99.2], "#2563eb"),
                                                        ("Pabrik B", [97.8, 97.9, 98.0, 98.0, 98.2, 98.3, 98.4, 98.4, 98.5, 98.6, 98.6, 98.7], "#d97706"),
                                                        ("Pabrik C", [95.0, 95.2, 95.1, 95.6, 95.8, 95.7, 96.0, 96.1, 96.2, 96.3, 96.3, 96.4], "#16a34a")],
                                                       [f"M{i}" for i in range(29, 41)], 900, 280, lo=94, hi=100, ticks=3,
                                                       fmt=lambda v: f"{v:.0f}%", end_labels=True, R=70), icon="monitoring")
    att = card("Perlu perhatian", "".join(
        f'<div class="ev"><span class="it {t}">{I(ic, True, 18)}</span><div class="grow"><div class="t1">{a}</div><div class="t2">{b}</div></div></div>'
        for ic, t, a, b in [("pause_circle", "amber", "Pabrik C · 2 lot lemon di-hold", "lot warna 7–9 naik sejak Selasa"),
                            ("water_drop", "amber", "Pabrik B · overfill +3,8 mL", "di atas sasaran +2 mL di line F2"),
                            ("warning", "amber", "Pabrik A · CAM 07 silau di lensa", "nozzle 5–8 dicek manual sejak 07:04")]), icon="priority_high")
    rep = card("Laporan mingguan ke kantor pusat", f'''<div class="kv"><span>Dikirim</span><span>setiap Senin 07:00 · PDF + Excel</span>
      <span>Kepada</span><span>Plant manager, QC, Operations Director</span>
      <span>Isi</span><span>ukuran yang sama untuk setiap pabrik dan produk</span></div>''', icon="mail", right=tg(True))
    body = (ph("Pabrik", "Satu tampilan untuk kantor pusat: semua pabrik, semua produk, ukuran yang sama",
               '<span class="seg"><span>Hari ini</span><span class="on">Minggu ini</span><span>Bulan ini</span></span>')
            + tb + grid("1fr 560px", [comp, f'<div class="col" style="gap:18px">{att}{rep}</div>']))
    return app("grading", "plants", body, user=("Budi Santoso", "Viewer", "slate"))


def p21_rollout() -> str:
    pilot = {"grading": "Keputusan lot dan kelas warna sama dengan QC pabrik pada sampel blind (PoC: 75/78 tomat)",
             "fill": "Setiap botol di bawah toleransi di-reject; level isi per nozzle dibandingkan dengan check weigher",
             "pack": "Setiap tray/kardus kurang isi di-hold sebelum disegel, dengan slot kosongnya (PoC: 7/7 tray, 3/3 kardus)",
             "parcel": "P × L × T dalam ±1 cm dari meteran pada 100 paket (karton uji PoC: 340,5 vs 340 mm)"}
    prods = []
    for k, (icon, name, colour, tone, desc) in PRODUCTS.items():
        unit = {"grading": "per line", "fill": "per line pengisian", "pack": "per line atau station", "parcel": "per belt"}[k]
        prods.append(f'<section class="card" style="padding:20px 22px;gap:10px"><div class="row" style="gap:12px">'
                     f'<span class="it {tone}" style="width:42px;height:42px">{I(icon, True, 23)}</span><b style="font-size:17px">{name}</b></div>'
                     f'<div class="sec" style="font-size:13px">{desc}</div>'
                     f'<div class="row" style="gap:8px;font-size:13.5px;margin-top:auto">{I("receipt_long", False, 18, "var(--text-3)")}'
                     f'<span>Langganan bulanan <b>{unit}</b></span></div>'
                     f'<div style="border-top:1px solid var(--hair);padding-top:10px;font-size:13px"><div class="sect" style="margin:0 0 6px">Target lolos pilot</div>'
                     f'{pilot[k]}</div></section>')
    inc = [("Termasuk di setiap produk", ["Web App & Dashboard TV", "Alert lewat WhatsApp, push, email", "Klip bukti disimpan 30 hari",
                                          "Laporan shift & lot, PDF / Excel", "Pengguna & role, audit log"]),
           ("Add-on", ["Integrasi sinyal reject ke PLC", "Konektor MES / ERP / WMS", "Tampilan multi-pabrik untuk kantor pusat",
                       "Klip bukti 90 hari", "Opsi on-premise"])]
    ic = "".join(f'<section class="card" style="padding:20px 22px;gap:9px"><b style="font-size:16px">{t}</b>'
                 + "".join(f'<div class="row" style="gap:9px;font-size:13.5px">{I("check_circle", True, 18, "#2563eb")}{f}</div>' for f in fs)
                 + '</section>' for t, fs in inc)
    steps = [("search", "1 · Line survey", "1 minggu", "posisi kamera, cahaya, kecepatan line, standar yang dipakai"),
             ("science", "2 · Pilot", "30 hari", "1 produk di 1 line · laporan akurasi vs QC manual"),
             ("rocket_launch", "3 · Go-live", "2 minggu", "koneksi PLC / MES, aturan alert, training"),
             ("add_business", "4 · Expand", "per kuartal", "line lain, produk berikutnya, pabrik lain")]
    st = "".join(f'<div class="row" style="gap:12px;flex:1;align-items:flex-start"><span class="it blue" style="width:40px;height:40px">{I(ic, True, 21)}</span>'
                 f'<div><b style="font-size:14.5px">{a}</b> <span class="mut">· {b}</span><div class="sec" style="font-size:12.5px;margin-top:3px">{c}</div></div></div>'
                 + (I("arrow_forward", size=20, color="var(--text-3)") if k < 3 else "") for k, (ic, a, b, c) in enumerate(steps))
    who = [("Disiapkan pabrik", "factory", ["Titik dudukan dan listrik di setiap titik inspeksi", "Jaringan dari line ke edge box",
                                              "Satu orang QC untuk cek blind selama pilot", "Standar atau spec pembeli yang dipakai"]),
           ("Disiapkan Factory Vision", "precision_manufacturing", ["Kamera, lampu, dan edge box, terpasang dan tersetel",
                                                                     "Setting standar, limit, dan aturan alert",
                                                                     "Laporan akurasi di akhir pilot", "Support dan update model AI"])]
    split = "".join(f'<section class="card" style="padding:18px 22px;gap:9px"><div class="row" style="gap:10px">{I(ic, True, 20, "#2563eb")}'
                    f'<b style="font-size:16px">{t}</b></div>'
                    + "".join(f'<div class="row" style="gap:9px;font-size:13.5px">{I("check_circle", True, 18, "#16a34a")}{f}</div>' for f in fs)
                    + '</section>' for t, ic, fs in who)
    body = (grid("repeat(4,1fr)", prods, 20)
            + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">{ic}</div>'
            + f'<section class="card" style="padding:18px 24px;flex-direction:row;align-items:center;gap:16px">{st}</section>'
            + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">{split}</div>'
            + f'<section class="card" style="padding:16px 24px;flex-direction:row;align-items:center;gap:14px;background:#0f172a;border-color:#0f172a;color:#e9eef4">'
              f'{I("handshake", True, 24, "#93c5fd")}<span style="font-size:15px"><b>Harga per line, dihitung setelah line survey.</b> '
              f'Biaya pilot dikreditkan ke kontrak bila pabrik melanjutkan.</span></section>')
    return slide("Paket & rollout", "Mulai dari satu produk di satu line, lalu kembangkan",
                 "Setiap produk adalah langganan bulanan per line, di platform yang sama. Mulai dengan pilot 30 hari di line "
                 "yang paling banyak menimbulkan reject, komplain, atau giveaway.", body)


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
            shoot(path, PAGES / f"{slug}.png", 1.0 if "--1x" in argv else 2.0)
            print("page", slug)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
