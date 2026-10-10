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
sys.modules.setdefault("build", sys.modules[__name__])

import tv  # noqa: E402
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


def im(kind: str, k: int = -1) -> str:
    """The PoC camera picture, AI overlay only (assets.py)."""
    return f"../img/{kind}_cam_{S[kind][k]}.jpg"


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
def _nav(quality: list, spec: tuple) -> list:
    return [("Pantau", [("dashboard", "Ringkasan", "overview"), ("videocam", "Live Monitoring", "live"),
                        ("live_tv", "Dashboard TV", "tv")]),
            ("Kualitas", quality),
            ("Pengaturan", [spec, ("settings_input_component", "Kamera, Alert & Integrasi", "settings")]),
            ("Admin", [("group", "Pengguna & Role", "users"), ("factory", "Pabrik", "plants")])]


# each product is its own web app, with its own menu in the words of that line
NAVS = {
    "grading": _nav([("fact_check", "Laporan Lot", "lots"), ("report", "Riwayat Off-colour", "events"),
                     ("description", "Laporan Shift", "reports")], ("tune", "Standar Grade", "specs")),
    "fill": _nav([("report", "Reject & Giveaway", "events"), ("description", "Laporan Shift", "reports")],
                 ("tune", "Spesifikasi SKU", "specs")),
    "pack": _nav([("report", "Reject & Rework", "events"), ("description", "Laporan Shift", "reports")],
                 ("tune", "Spesifikasi Kemasan", "specs")),
    "parcel": _nav([("list_alt", "Log Paket", "events"), ("local_shipping", "Muat & Tagihan", "lots"),
                    ("description", "Laporan Shift", "reports")], ("tune", "Kelas Ukuran", "specs")),
}
SEARCH = {"grading": "Cari lot, line, kelas warna…", "fill": "Cari SKU, nozzle, reject…",
          "pack": "Cari tray, kardus, slot, reject…", "parcel": "Cari paket, truk, pelanggan…"}
BADGE = {"grading": 3, "fill": 4, "pack": 5, "parcel": 1}


def sidebar(active: str, product: str, user: tuple) -> str:
    icon, name, colour, tone, _ = PRODUCTS[product]
    groups = []
    for title, items in NAVS[product]:
        rows = []
        for ic, label, key in items:
            extra = ""
            if key == "events":
                extra = f'<span class="nb">{BADGE[product]}</span>'
            if key == "tv":
                extra = I("open_in_new", size=16).replace('class="i"', 'class="i ext"')
            rows.append(f'<div class="ni{" on" if key == active else ""}">{I(ic, key == active)}{label}{extra}</div>')
        groups.append(f'<div class="ng"><div class="t">{title}</div>{"".join(rows)}</div>')
    uname, role, utone = user
    return (f'<aside class="side"><div class="brand"><span class="logo" style="background:{colour}">{I(icon, True, 21)}</span>'
            f'<div><b>{name}</b><small>by {BRAND}</small></div></div>'
            f'{"".join(groups)}<div class="sfoot">{avatar(uname, 34)}<div class="grow"><b>{uname}</b>{bd(role, utone)}</div>'
            f'{I("unfold_more", size=18, color="#5f6f86")}</div></aside>')


def topbar(product: str, site=("Pabrik A · Cikarang", "PT Contoh Industri"), shift="Shift 1 · 07–15 · 10:42") -> str:
    return (f'<header class="top"><div class="sel">{I("factory", size=20, color="var(--text-2)")}'
            f'<div><b>{site[0]}</b><small>{site[1]}</small></div>{I("expand_more", size=18, color="var(--text-3)")}</div>'
            f'<div class="search" style="width:520px">{I("search", size=19)}<span class="ell">{SEARCH[product]}</span>'
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




# ------------------------------------------------------------------ shared tables
ROLES = [
    ("shield_person", "Super Admin", "violet", "Tim vendor", "Semua pelanggan · platform"),
    ("admin_panel_settings", "Plant Admin", "blue", "Plant manager, IT", "Semua line di pabrik"),
    ("verified", "QC Manager", "green", "Quality assurance (QA/QC)", "Produk & line yang ditugaskan"),
    ("engineering", "Line Supervisor", "amber", "Produksi / kepala shift", "Line yang ditugaskan"),
    ("visibility", "Viewer", "slate", "Manajemen, auditor", "Hanya melihat"),
]


# ================================================================== slides: platform




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
    body = (ph("Live Monitoring", "Overlay AI di setiap kamera: kelas per buah, count gate, nomor line",
               '<span class="seg"><span>' + I("crop_square") + '1</span><span>' + I("grid_view") + '4</span><span class="on">'
               + I("view_quilt") + '1+3</span></span>' + btn("Layar penuh", "fullscreen"))
            + f'<div style="display:grid;grid-template-columns:1fr 420px;gap:18px;flex:1;min-height:0">'
              f'<div style="min-height:0">{wall}</div><div class="col" style="gap:14px">{side}</div></div>')
    return app("grading", "live", body, user=("Andi Wijaya", "Line Supervisor", "amber"))






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
               crumb=f'Laporan Lot {I("chevron_right", size=16)} T-1012-07')
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
    body = (ph("Standar Grade", "Pilih standar per line; QC Manager mengatur limit dan mengujinya dulu di rekaman",
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
    live = card("Live · Line F1 · nozzle 1", tile(im("fill"), "F1 · Mesin pengisi · CAM 06", "#2563eb", "67%", style="height:205px")
                + f'<div class="mut" style="font-size:12px;margin-top:8px">{poc()} level isi diukur tiap frame dari bentuk botol</div>',
                icon="videocam")
    body = (ph("Ringkasan · Fill Level Inspection", "Hari ini · Shift 1 · line F1–F2",
               btn("Ekspor", "download") + btn("Buka Dashboard TV", "live_tv", "pri"))
            + k + grid("1fr 620px", [nz, tr]) + grid("1fr 1fr 480px", [sku, rej, live]))
    return app("fill", "overview", body)




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
        <span>Kamera</span><span>CAM 06 · tampak samping, backlight</span></div></div></div>''',
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
    body = (ph("Spesifikasi SKU · Aturan isi", "Target, toleransi, dan tindakan per SKU; bentuk botol mengubah tinggi cairan menjadi volume",
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
               crumb=f'Reject & Rework {I("chevron_right", size=16)} P1-0412')
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
    return app("parcel", "lots", body)


# ================================================================== shared pages








APP_DIR = HERE / "apps"


def apps() -> dict:
    """Each product is its own web app: its pages, in the order they are told, and where they are written."""
    import extra as X   # imports build, so it is loaded here and not at the top
    T = dict(tv.PAGES)
    return {
        "produce_grading": [
            ("01_ringkasan", p02_grading_overview), ("02_live_monitoring", p03_grading_live),
            ("03_dashboard_tv_tomat", T["04_grading_tv_tomato"]), ("04_dashboard_tv_lemon", T["05_grading_tv_lemon"]),
            ("05_laporan_lot", p06_grading_lot), ("06_standar_grade", p07_grading_standards),
            ("07_kamera_alert_integrasi", lambda: X.settings("grading"))],
        "fill_level_inspection": [
            ("01_ringkasan", p08_fill_overview), ("02_live_monitoring", X.live_fill), ("03_dashboard_tv", T["09_fill_tv"]),
            ("04_reject_giveaway", X.fill_events), ("05_spesifikasi_sku", p10_fill_spec),
            ("06_kamera_alert_integrasi", lambda: X.settings("fill"))],
        "pack_count_qc": [
            ("01_ringkasan", p11_pack_overview), ("02_live_monitoring", X.live_pack),
            ("03_dashboard_tv_tray", T["12_pack_tv_trays"]), ("04_dashboard_tv_packing", T["13_pack_tv_packing"]),
            ("05_detail_reject", p14_pack_reject), ("06_spesifikasi_kemasan", X.pack_spec),
            ("07_kamera_alert_integrasi", lambda: X.settings("pack"))],
        "parcel_dimensioning": [
            ("01_ringkasan", p15_parcel_overview), ("02_live_monitoring", X.live_parcel), ("03_dashboard_tv", T["16_parcel_tv"]),
            ("04_muat_tagihan", p17_parcel_load), ("05_kelas_ukuran", X.parcel_spec),
            ("06_kamera_alert_integrasi", lambda: X.settings("parcel"))],
    }


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
    """python build.py [app ...] [--icons] [--1x] [--no-shot]; an app is named by any part of its folder name."""
    HTML.mkdir(exist_ok=True)
    want = [a for a in argv if not a.startswith("--")]
    built = []
    for slug, pages in apps().items():
        if want and not any(w in slug for w in want):
            continue
        out = APP_DIR / slug / "pages"
        out.mkdir(parents=True, exist_ok=True)
        for name, fn in pages:
            path = HTML / f"{slug}__{name}.html"
            path.write_text(fn())
            built.append((slug, name, path, out / f"{name}.png"))
    if "--icons" in argv:
        fetch_icons()
    if "--no-shot" not in argv:
        for slug, name, path, png in built:
            shoot(path, png, 1.0 if "--1x" in argv else 2.0)
            print("page", slug, name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
