"""The mockup pages. Each function returns one complete HTML document.

One fictional client runs through every page so the deck tells one story:
Kedai Pagi, a 12-outlet cafe chain, seen on a Thursday afternoon in its Senopati
outlet. The outlet has four CCTVs; CCTV 02 watches the main room, and that room
is the dwell-time clip from project 05 - the floor plan on the live page is
drawn from that clip's frame. Every other number is illustrative, and the
footer tag on every image says so.

Copy is written for the people who buy this - cafe owners and investors - so it
avoids engineering words: "kursi terisi", not "okupansi"; "akurat / estimasi",
not "deteksi / tracking".
"""

from __future__ import annotations

import math
from pathlib import Path

from kit import (AXIS, BLUE, BRAND, INK, INK2, MUTED, ORANGE, ORDINAL, SURF, basis, chip, columns, data_uri,
                 heatmap, ic, kpi, line_chart, logo, page, scale_bar, spark, toggle)

ROOT = Path(__file__).resolve().parents[2]
CLIP_STILL = ROOT / "projects/05_cafe_dwell_time/docs/scene5-dwell.jpg"
RAW_FRAME = Path(__file__).resolve().parents[1] / ".mockup_cache" / "scene5_f149.jpg"
APP = "app.outlytics.ai"      # placeholders: outlytics.ai was still unregistered on 1 Oct 2026
PANEL = "panel.outlytics.ai"

LIVE_CAM, LIVE_ROOM = "CCTV 02", "Ruang Utama Lt. 1"

# ------------------------------------------------------------------ tables ---
# The main room as CCTV 02 sees it: three tables along the long bench under the
# mirror (two bench seats each); meja 4, three tables pushed into one row in front
# of the counter with three chairs a side; and two small tables with two chairs
# each. 21 seats, and the floor plan draws every one of them. At 15.12 meja 2
# holds the four people at the bench, meja 4 the man at its end by the till, and
# meja 6 the woman in the foreground - the people in the frame the plan is traced
# from. Meja 5 is the empty table with a drink left on it.
NOW = 15.2
TABLES = [("Meja 1", 4), ("Meja 2", 4), ("Meja 3", 3), ("Meja 4", 6), ("Meja 5", 2), ("Meja 6", 2)]
SEGS = {
    "Meja 1": [(8.4, 9.3), (9.9, 12.4), (12.7, 13.6), (13.9, 14.8)],
    "Meja 2": [(8.8, 9.7), (10.0, 10.9), (11.2, 12.0), (12.2, 13.1), (13.4, 15.2)],
    "Meja 3": [(9.0, 10.2), (10.6, 13.9), (14.2, 14.9)],
    "Meja 4": [(8.2, 12.1), (12.4, 13.2), (13.5, 14.4), (14.6, 15.2)],
    "Meja 5": [(10.1, 11.0), (11.4, 13.6), (14.0, 14.9)],
    "Meja 6": [(8.6, 9.2), (11.3, 12.5), (12.8, 13.9), (14.3, 15.2)],
}
SEATS = sum(n for _, n in TABLES)                          # 21
BENCH_SEATS = sum(n for t, n in TABLES if t in ("Meja 1", "Meja 2", "Meja 3"))
WOOD_SEATS = SEATS - BENCH_SEATS
SEATED_BENCH, SEATED_WOOD = 4, 2                           # who is sitting where at 15.12
SEATED = SEATED_BENCH + SEATED_WOOD
OCC = round(100 * SEATED / SEATS)                          # % of seats taken now
LONG_H = 2.0  # a stay this long counts as a long stay


def _seat_hours(w0: float, w1: float) -> tuple[float, float]:
    """(long-stay seat-hours, all seat-hours) inside the window [w0, w1]."""
    seats = dict(TABLES)
    long_h = all_h = 0.0
    for t, segs in SEGS.items():
        for a, b in segs:
            ov = max(0.0, min(b, w1) - max(a, w0))
            all_h += ov * seats[t]
            if b - a >= LONG_H:
                long_h += ov * seats[t]
    return long_h, all_h


LONG_TABLES = sum(1 for segs in SEGS.values() if any(b - a >= LONG_H for a, b in segs))
_l, _a = _seat_hours(11.0, 15.0)
LONG_SHARE = round(100 * _l / _a)


# ------------------------------------------------------------------ assets ---
def ensure_assets() -> tuple[Path, Path]:
    """The annotated frame cropped to the video, and the raw frame it was taken from."""
    import cv2
    cache = RAW_FRAME.parent
    still = cache / "scene5_annotated_video.jpg"
    if not still.exists():
        im = cv2.imread(str(CLIP_STILL))
        cv2.imwrite(str(still), im[:, 236:], [cv2.IMWRITE_JPEG_QUALITY, 92])  # drop the engine's own side panel
    if not RAW_FRAME.exists():
        cap = cv2.VideoCapture(str(ROOT / "projects/05_cafe_dwell_time/input/cafe_scene5_30s.mp4"))
        cap.set(cv2.CAP_PROP_POS_FRAMES, 149)
        ok, fr = cap.read()
        cv2.imwrite(str(RAW_FRAME), fr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return still, RAW_FRAME


def snapshots() -> list[str]:
    """Five frames of the same clip used as the accuracy-check photos."""
    import cv2
    cache = RAW_FRAME.parent
    cap = cv2.VideoCapture(str(ROOT / "projects/05_cafe_dwell_time/input/cafe_scene5_30s.mp4"))
    out = []
    for i in (149, 0, 37, 75, 112):
        f = cache / f"snap_{i:03d}.jpg"
        if not f.exists():
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, fr = cap.read()
            cv2.imwrite(str(f), cv2.resize(fr, (480, 270), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
        out.append(data_uri(f))
    return out


# ----------------------------------------------------------------- helpers ---
def btn(text: str, icon: str | None = None, kind: str = "") -> str:
    return f'<span class="btn {kind}">{ic(icon, 15) if icon else ""}{text}</span>'


def sel(k: str, v: str) -> str:
    key = f'<span class="k">{k}</span>' if k else ""
    return f'<span class="sel">{key}{v}{ic("chevron-down", 14, color=MUTED)}</span>'


def cardh(title: str, hint: str = "", right: str = "") -> str:
    h = f'<div class="hint">{hint}</div>' if hint else ""
    return f'<div class="card-h"><div><h3>{title}</h3>{h}</div>{right}</div>'


def steps(labels: list[str], active: int) -> str:
    out = []
    for i, lab in enumerate(labels, 1):
        if i < active:
            circ, cls = f'<span class="stp done">{ic("check", 13, 2.8)}</span>', "ink2"
        elif i == active:
            circ, cls = f'<span class="stp on">{i}</span>', "b"
        else:
            circ, cls = f'<span class="stp">{i}</span>', "muted"
        out.append(f'<div class="row g8">{circ}<span class="{cls}" style="font-size:13px">{lab}</span></div>')
        if i < len(labels):
            out.append('<div style="width:40px;height:1px;background:var(--axis)"></div>')
    return '<div class="row g10 nogrow" style="flex:none">' + "".join(out) + "</div>"


def mini(label: str, value: str, sub: str, icon_: str) -> str:
    return (f'<div class="card" style="padding:12px 15px;gap:5px"><div class="row sp"><span class="sm ink2 b">{label}</span>{ic(icon_, 15, color=MUTED)}</div>'
            f'<div class="row g8" style="align-items:baseline"><span style="font-size:27px;font-weight:600;letter-spacing:-.02em;line-height:1.1">{value}</span><span class="sm ink2">{sub}</span></div></div>')


def item(kind: str, icon_: str, title: str, body: str, foot: str = "") -> str:
    f = f'<div class="row sp" style="margin-top:8px">{foot}</div>' if foot else ""
    return (f'<div class="item"><div class="ibox {kind}">{ic(icon_, 16)}</div><div class="grow">'
            f'<div class="b" style="font-size:13.5px">{title}</div><div class="ink2" style="margin-top:2px">{body}</div>{f}</div></div>')


# =============================================================== 01 ringkasan
def home() -> str:
    kpis = "".join([
        kpi("Pengunjung hari ini", "187", "orang", "+9%", "g", "vs Kamis lalu", "line", "door-open",
            [4, 9, 15, 24, 33, 52, 71, 96, 118, 142, 166, 187]),
        kpi("Kursi terisi sekarang", f"{OCC}%", f"{SEATED}/{SEATS} kursi", "puncak 92%", "n", "pukul 13.05", "det", "armchair",
            [4, 8, 17, 33, 50, 79, 92, 83, 67, 46, 34, OCC]),
        kpi("Rata-rata lama berkunjung", "38", "menit", "−7%", "n", "vs Kamis lalu", "trk", "timer",
            [41, 40, 44, 39, 37, 36, 35, 39, 41, 40, 37, 38]),
        kpi("Antrean sekarang", "0", "orang", "terpanjang 6", "n", "pukul 12.58", "det", "users",
            [0, 1, 1, 2, 3, 6, 4, 3, 2, 1, 0, 0]),
        kpi("Kasir kosong hari ini", "7", "menit", "+4 menit", "r", "vs rata-rata", "det", "triangle-alert",
            [0, 0, 0, 1, 0, 2, 4, 0, 0, 0, 0, 0]),
    ])
    today = [(8, 4), (8.5, 8), (9, 17), (9.5, 25), (10, 33), (10.5, 38), (11, 50), (11.5, 63), (12, 79),
             (12.5, 88), (13.08, 92), (13.5, 83), (14, 67), (14.5, 46), (15, 34), (15.2, OCC)]
    avg = [(8, 6), (9, 15), (10, 29), (11, 46), (12, 71), (13, 80), (14, 63), (15, 41), (16, 38), (17, 48),
           (18, 62), (19, 70), (20, 57), (21, 34), (22, 14)]
    chart = line_chart(758, 322, today, avg, now=15.2, peak=(13.08, 92, "Puncak 92% · 13.05"), now_label=f"{OCC}%")

    def att(kind, icon_, title, body, action, bas):
        return item(kind, icon_, title, body, f'<span class="btn sm">{action}{ic("arrow-right", 13)}</span>{bas}')

    attention = (att("warn", "siren", "Kasir kosong 3× saat ada antrean",
                     "Pukul 12.50–13.35, antrean 4–6 orang, total 7 menit tanpa staf di kasir.<br>"
                     "<b style='color:var(--ink)'>Saran:</b> tambah 1 staf di kasir pukul 12.30–14.00.",
                     "Lihat kejadian", basis("det"))
                 + att("info", "armchair", f"{LONG_TABLES} meja dipakai lebih dari 2 jam",
                       f"Menahan {LONG_SHARE}% kapasitas kursi saat jam makan siang (11.00–15.00).",
                       "Lihat pemakaian meja", basis("det"))
                 + att("crit", "wifi-off", "CCTV 03 · Teras offline sejak 09.42",
                       "Angka &ldquo;sekarang&rdquo; di halaman ini belum termasuk area teras.",
                       "Cek CCTV", chip("Perlu dicek", "crit")))

    def zone(n, v, vmax, txt=""):
        return (f'<div class="row g10"><span class="sm ink2" style="width:110px">{n}</span>'
                f'<div class="meter grow"><i style="width:{100 * v / vmax:.0f}%"></i></div>'
                f'<span class="sm b tnum" style="width:54px;text-align:right">{txt or f"{v}/{vmax}"}</span></div>')

    bottom = f"""<div class="grid" style="grid-template-columns:1.1fr 1fr 1fr;gap:12px;height:122px;flex:none">
 <div class="card" style="padding:12px 16px"><div class="card-h" style="margin-bottom:8px"><h3>Area saat ini</h3>{basis('det')}</div>
   <div class="col g8">{zone('Bangku panjang', SEATED_BENCH, BENCH_SEATS)}{zone('Meja kayu', SEATED_WOOD, WOOD_SEATS)}{zone('Antrean', 0, 6, '0 orang')}</div></div>
 <div class="card" style="padding:12px 16px"><div class="card-h" style="margin-bottom:6px"><h3>Laporan WhatsApp 08.00</h3>{chip('Terkirim', 'good', 'check')}</div>
   <div class="ink2 sm" style="margin-bottom:8px">Ringkasan kemarin untuk 3 orang</div>
   <div class="row g6 wrap">{chip('Lucky · Owner', 'neutral')}{chip('Bagas · Admin', 'neutral')}{chip('Sari · Manager', 'neutral')}</div></div>
 <div class="card" style="padding:12px 16px"><div class="card-h" style="margin-bottom:8px"><h3>Status sistem</h3>{chip('1 perlu dicek', 'warn', 'circle-alert')}</div>
   <div class="col g6 sm"><div class="row sp"><span class="ink2">CCTV online</span><span class="b">3 dari 4</span></div>
   <div class="row sp"><span class="ink2">Data terakhir masuk</span><span class="b">3 detik lalu</span></div>
   <div class="row sp"><span class="ink2">Versi AI</span><span class="b">2.4 (terbaru)</span></div></div></div></div>"""

    body = f"""<div class="grid" style="grid-template-columns:repeat(5,1fr);gap:12px;flex:none">{kpis}</div>
<div class="row g12" style="flex:1;min-height:0;align-items:stretch">
 <div class="card" style="flex:0 0 61.5%">
   {cardh("Keramaian hari ini vs rata-rata 4 Kamis terakhir", f"% kursi terisi di Ruang Utama ({SEATS} kursi)", basis("det"))}
   <div class="lg" style="margin-bottom:4px"><span><i style="background:{BLUE}"></i>Hari ini</span><span><i style="background:{MUTED}"></i>Rata-rata 4 Kamis</span></div>
   {chart}</div>
 <div class="card grow" style="padding-bottom:6px">{cardh("Perlu perhatian", "", chip("3 hal", "neutral"))}{attention}</div>
</div>{bottom}"""
    return page(plane="tenant", active="home", url=f"{APP}/senopati/ringkasan",
                title="Selamat sore, Lucky",
                sub="Kamis, 1 Okt 2026 · Outlet Senopati, Jakarta Selatan · buka 08.00–22.00 · update 15.12",
                actions=sel("", "Hari ini") + btn("Download PDF", "download"), body=body)


# ============================================================ 02 pantauan live
# The plan is traced from CCTV 02's frame (frame 149 of the project 05 clip) and
# drawn the way that camera looks at the room: the counter runs almost level
# across the back, the bench wall falls away to the left, and the camera sits at
# the bottom. The room itself is drawn square, as a floor plan should be. In the
# frame the bench wall and the counter actually meet at about 128 degrees, which
# is why on camera the counter reads as the bench row carrying straight on; the
# projection below keeps that look.
#
# Units are metres: x along the back wall (the counter), y along the bench wall
# toward the camera, both from the far corner.
ISO_K, ISO_X0, ISO_Y0 = 55.0, 322.0, 112.0
_AX, _AY = 1.16, 0.16    # one metre along the counter: nearly level, as on camera
_BX, _BY = -0.80, 0.62   # one metre along the bench wall: down and to the left


def P(x: float, y: float, z: float = 0.0) -> tuple[float, float]:
    """Room metres -> screen, seen from CCTV 02's side of the room."""
    return ISO_X0 + (x * _AX + y * _BX) * ISO_K, ISO_Y0 + (x * _AY + y * _BY) * ISO_K - z


def _pts(seq) -> str:
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in seq)


def shape(corners, fill, stroke="none", sw=1.0, extra="", z=0.0) -> str:
    return (f'<polygon points="{_pts(P(x, y, z) for x, y in corners)}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linejoin="round" {extra}/>')


def box(x0, y0, x1, y1) -> list[tuple[float, float]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _mid(corners) -> tuple[float, float]:
    return sum(c[0] for c in corners) / len(corners), sum(c[1] for c in corners) / len(corners)


def _line(a, b, color, sw=1.0) -> str:
    (x1, y1), (x2, y2) = P(*a), P(*b)
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{sw}"/>'


def _guest(x, y) -> str:
    sx, sy = P(x, y)
    return (f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="13" fill="{BLUE}" fill-opacity=".14"/>'
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="7.5" fill="{BLUE}" stroke="{SURF}" stroke-width="2.5"/>')


def _staff(x, y) -> str:
    sx, sy = P(x, y)
    return (f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="14" fill="{ORANGE}" fill-opacity=".16"/>'
            f'<rect x="{sx - 7.5:.1f}" y="{sy - 7.5:.1f}" width="15" height="15" rx="4.5" fill="{ORANGE}" stroke="{SURF}" stroke-width="2.5"/>')


def _num(x, y, n, occ) -> str:
    sx, sy = P(x, y)
    return f'<text x="{sx:.1f}" y="{sy + 3.5:.1f}" text-anchor="middle" font-size="10.5" font-weight="700" fill="{"#184f95" if occ else MUTED}">{n}</text>'


def _callout(x, y, title, sub, px, py, color, up=False) -> str:
    ly = y - 14 if up else y + 19  # leave from above the title when the target is above it
    return (f'<line x1="{x + 4}" y1="{ly}" x2="{px:.1f}" y2="{py:.1f}" stroke="{color}" stroke-width="1" stroke-opacity=".75"/>'
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{color}"/>'
            f'<text x="{x}" y="{y}" font-size="11.5" font-weight="700" fill="{color}">{title}</text>'
            f'<text x="{x}" y="{y + 14}" font-size="10.5" fill="{MUTED}">{sub}</text>')


def floorplan(w: int = 706, h: int = 418) -> str:
    """Ruang Utama Lt. 1 as CCTV 02 sees it. The long bench under the mirror runs down the
    left wall, the counter along the back wall, and meja 4 - three tables in one row - in
    front of the counter. No entrance: it is not in this camera's view."""
    W, H, wall = 5.6, 6.6, 34
    t = []
    t.append(shape(box(0, 0, W, H), "#f1f0ea", AXIS, 1.4))
    t.append(f'<polygon points="{_pts([P(0, 0), P(0, H), P(0, H, wall), P(0, 0, wall)])}" fill="#e6e4dd" stroke="{AXIS}" stroke-width="1.2" stroke-linejoin="round"/>')
    t.append(f'<polygon points="{_pts([P(0, 0), P(W, 0), P(W, 0, wall), P(0, 0, wall)])}" fill="#ecebe5" stroke="{AXIS}" stroke-width="1.2" stroke-linejoin="round"/>')
    # the mirror on the bench wall: what it shows are people already counted, so it is excluded
    # (hatched with clipped lines, not an SVG pattern: a pattern prints as a masked bitmap)
    mirror = [P(0, 1.4, 9), P(0, 3.6, 9), P(0, 3.6, 28), P(0, 1.4, 28)]
    mx0, mx1 = min(p[0] for p in mirror), max(p[0] for p in mirror)
    my0, my1 = min(p[1] for p in mirror), max(p[1] for p in mirror)
    span, hatch, x = my1 - my0, [], mx0 - (my1 - my0)
    while x < mx1:
        hatch.append(f'<line x1="{x:.1f}" y1="{my1:.1f}" x2="{x + span:.1f}" y2="{my0:.1f}"/>')
        x += 8.5
    t.append(f'<clipPath id="mirror"><polygon points="{_pts(mirror)}"/></clipPath>'
             f'<g clip-path="url(#mirror)" stroke="#d03b3b" stroke-opacity=".55" stroke-width="2">{"".join(hatch)}</g>'
             f'<polygon points="{_pts(mirror)}" fill="none" stroke="#d03b3b" stroke-opacity=".6" stroke-width="1"/>')
    # the long metal bench, six seats
    t.append(shape(box(0, 0.5, 0.45, 4.4), "#d9d7cf", AXIS, 1))
    for yy in (1.15, 1.8, 2.45, 3.1, 3.75):
        t.append(_line((0, yy), (0.45, yy), "#b9b8b0"))
    # the counter along the back wall: coffee bar, till, display case
    t.append(shape(box(1.75, 0.7, 3.6, 1.25), "#d3d1c8", AXIS, 1))
    t.append(shape(box(1.95, 0.75, 2.5, 1.0), "#b9b7ae"))
    t.append(shape(box(3.25, 0.8, 3.55, 1.15), "#6b6a64"))
    t.append(shape(box(3.6, 0.55, 5.4, 1.35), "#e2e0d8", AXIS, 1))
    # chairs: meja 1 and 2 have two each facing the bench; meja 5 and 6 have two each,
    # facing each other across the table, none on the right; meja 4 has three a side,
    # facing each other across the row
    chairs = [(1.25, 0.95), (1.25, 2.12), (1.25, 2.48), (1.25, 3.35), (1.25, 3.8),    # meja 3, 2, 1
              (2.15, 3.85), (2.15, 4.85),                                            # meja 5
              (3.25, 4.05), (3.25, 5.05)]                                            # meja 6
    chairs += [(x0 + 0.175, yy) for x0 in (2.0, 2.65, 3.3) for yy in (1.8, 2.95)]     # meja 4
    for x, y in chairs:
        t.append(shape(box(x, y, x + 0.3, y + 0.3), "#e6e4dd", AXIS, 0.8))
    occ = {"1": False, "2": True, "3": False, "4": True, "5": False, "6": True}
    tables = {"1": box(0.55, 3.2, 1.15, 4.2), "2": box(0.55, 2.05, 1.15, 2.85), "3": box(0.55, 0.8, 1.15, 1.4),
              "5": box(2.0, 4.2, 2.6, 4.8), "6": box(3.1, 4.4, 3.7, 5.0)}
    for n, c in tables.items():
        on = occ[n]
        t.append(shape(c, "#cde2fb" if on else SURF, "#86b6ef" if on else AXIS, 1.2))
    t.append(shape(box(2.0, 2.2, 3.95, 2.85), "#cde2fb", "#86b6ef", 1.2))   # meja 4: one row of three tables
    for xs in (2.65, 3.3):
        t.append(_line((xs, 2.2), (xs, 2.85), "#86b6ef"))
    # zones. The queue zone sits in front of the till: it overlaps the cashier zone at the
    # counter, and reaches over the end of meja 4, where the man at that table is sitting.
    t.append(shape(box(1.65, 0.0, 5.5, 1.6), ORANGE, ORANGE, 1.2, 'fill-opacity=".12" stroke-opacity=".6"'))
    t.append(shape(box(3.1, 1.15, 4.65, 2.55), BLUE, BLUE, 1.2, 'fill-opacity=".08" stroke-opacity=".5"'))
    for n, c in tables.items():
        t.append(_num(*_mid(c), n, occ[n]))
    t.append(_num(2.975, 2.525, "4", True))
    # the people in the frame: four at meja 2 (two on the bench and two on chairs, facing
    # each other), the man at the end of meja 4, the woman on the camera side of meja 6,
    # one person walking, and the one member of staff behind the counter
    guests = [(0.24, 2.27), (0.24, 2.63), (1.4, 2.27), (1.4, 2.63), (3.625, 3.1), (3.4, 5.2), (4.25, 3.95)]
    for x, y in guests:
        t.append(_guest(x, y))
    wx, wy = P(*guests[-1])
    t.append(f'<text x="{wx + 13:.1f}" y="{wy + 4:.1f}" font-size="10.5" fill="{MUTED}">sedang berjalan</text>')
    t.append(_staff(2.9, 0.4))
    # labels
    t.append(_callout(132, 26, "Cermin dinding", "pantulan tidak dihitung", *P(0, 2.5, 19), "#a42626"))
    t.append(_callout(16, 150, "Bangku panjang", "6 kursi · meja 1–3", *P(0.22, 3.9), "#184f95"))
    t.append(_callout(448, 26, "Area kasir", "1 staf bertugas", *P(2.4, 0.35), "#9a3a14"))
    t.append(_callout(596, 26, "Etalase", "kue &amp; minuman", *P(4.7, 0.95), INK2))
    t.append(_callout(560, 268, "Area antre", "kosong · 0 orang", *P(4.3, 1.9), "#184f95", up=True))
    # the camera this plan is drawn from, on the near wall
    cx, cy = P(4.4, H)
    t.append(f'<g transform="translate({cx - 9:.1f},{cy - 13:.1f})" style="color:{INK}">{ic("cctv", 18, 2)}</g>'
             f'<text x="{cx + 14:.1f}" y="{cy + 1:.1f}" font-size="11" font-weight="700" fill="{INK}">CCTV 02</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(t)}</svg>'


def live() -> str:
    still, _ = ensure_assets()

    def tile(label, body, bas):
        return (f'<div class="card" style="padding:11px 15px;gap:7px"><div class="row sp"><span class="sm ink2 b">{label}</span>{bas}</div>'
                f'{body}</div>')

    big = 'style="font-size:28px;font-weight:600;letter-spacing:-.02em;line-height:1"'
    strip = "".join([
        tile("Di ruangan", f'<div class="row g8" style="align-items:baseline"><span {big}>8</span><span class="sm ink2">7 tamu · 1 staf</span></div>', basis("det")),
        tile("Kursi terisi", f'<div class="row g10"><span {big}>{OCC}%</span><div class="grow"><div class="meter"><i style="width:{OCC}%"></i></div><div class="xs muted" style="margin-top:4px">{SEATED} dari {SEATS} kursi</div></div></div>', basis("det")),
        tile("Antrean", f'<div class="row g8" style="align-items:baseline"><span {big}>0</span><span class="sm ink2">tidak ada yang menunggu</span></div>', basis("det")),
        tile("Kasir", f'<div class="row g10">{chip("Ada staf", "good", "circle-check")}<span class="sm ink2">1 staf di area kasir</span></div>', basis("det")),
    ])

    def ztile(name, sub, val, pct):
        return (f'<div style="border:1px solid var(--border);border-radius:10px;padding:8px 11px;background:#fff"><div class="row sp"><span class="sm b">{name}</span>'
                f'<span class="b tnum sm">{val}</span></div><div class="xs muted" style="margin:1px 0 6px">{sub}</div><div class="meter"><i style="width:{pct}%"></i></div></div>')

    zones = (ztile("Bangku panjang", "meja 1–3", f"{SEATED_BENCH} / {BENCH_SEATS}", round(100 * SEATED_BENCH / BENCH_SEATS))
             + ztile("Meja kayu", "meja 4–6", f"{SEATED_WOOD} / {WOOD_SEATS}", round(100 * SEATED_WOOD / WOOD_SEATS))
             + ztile("Area antre", "tidak ada antrean", "0", 0)
             + '<div style="border:1px solid var(--border);border-radius:10px;padding:8px 11px;background:#fff"><div class="row sp"><span class="sm b">Area kasir</span>'
               f'{chip("Ada staf", "good")}</div><div class="xs muted" style="margin-top:7px">1 staf · terakhir kosong 13.34</div></div>')

    legend = (f'<div class="lg" style="margin:6px 0 10px;gap:13px"><span><i class="sq" style="background:{BLUE};border-radius:50%"></i>Tamu</span>'
              f'<span><i class="sq" style="background:{ORANGE}"></i>Staf</span>'
              '<span><i class="sq" style="background:#cde2fb"></i>Meja terisi</span>'
              '<span><i class="sq" style="background:#fbe3d8;border:1px solid #f0b495"></i>Area kasir</span>'
              '<span><i class="sq" style="background:#e3edfa;border:1px solid #a8c6ee"></i>Area antre</span>'
              '<span><svg width="10" height="10" viewBox="0 0 10 10" style="margin-right:6px;vertical-align:middle">'
              '<clipPath id="lgh"><rect width="10" height="10" rx="3"/></clipPath><g clip-path="url(#lgh)"><rect width="10" height="10" fill="#fcfcfb"/>'
              '<path d="M-5 5L5-5M-2 10L10-2M3 13L13 3" stroke="#e9aaaa" stroke-width="2"/></g></svg>Tidak dihitung</span>'
              '<span class="muted" style="margin-left:auto">angka = nomor meja</span></div>')

    left = f"""<div class="card" style="flex:0 0 58%">{cardh(LIVE_ROOM, f"{LIVE_CAM} · setiap titik = 1 orang, tanpa wajah dan tanpa video", chip("Diperbarui 2 detik lalu", "neutral", "refresh-cw"))}
 {floorplan()}{legend}<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:10px">{zones}</div></div>"""

    video = f"""<div class="card" style="flex:none;height:372px">{cardh(f"Video {LIVE_CAM}", "", chip("Hanya di jaringan outlet", "neutral", "lock"))}
 <div style="position:relative;height:270px;border-radius:9px;overflow:hidden;background:#111">
  <img src="{data_uri(still)}" style="width:100%;height:100%;object-fit:cover;object-position:50% 40%">
  <span class="chip" style="position:absolute;left:10px;top:10px;background:rgba(11,11,11,.72);color:#fff">{ic("video", 12, 2.2)}{LIVE_CAM} · {LIVE_ROOM}</span>
  <span class="chip" style="position:absolute;right:10px;top:10px;background:rgba(11,11,11,.72);color:#fff"><i class="dot" style="background:#ff6b6b;width:7px;height:7px"></i>LIVE</span></div>
 <div class="xs muted" style="margin-top:8px">Contoh hasil AI pada rekaman uji. Video hanya bisa dibuka dari jaringan outlet dan tidak dikirim ke internet.</div></div>"""

    def al(kind, icon_, title, sub, time):
        return (f'<div class="row g10" style="padding:5px 0;border-bottom:1px solid #eceae4"><div class="ibox {kind}" style="width:26px;height:26px;border-radius:8px">{ic(icon_, 14)}</div>'
                f'<div class="grow"><div class="b" style="font-size:12.5px">{title}</div><div class="xs muted">{sub}</div></div><span class="xs muted tnum">{time}</span></div>')

    events = f"""<div class="card grow" style="padding-bottom:4px"><div class="card-h" style="margin-bottom:4px"><h3>Kejadian terbaru</h3>{chip("Hari ini", "neutral")}</div>
 {al("info", "gauge", f"Kursi terisi turun ke {OCC}%", "jam makan siang sudah lewat", "15.09")}
 {al("good", "circle-check", "Antrean kembali kosong", "setelah 25 menit ada antrean", "14.58")}
 {al("warn", "siren", "Kasir kosong 4 menit saat 5 orang antre", "WhatsApp terkirim ke Manager", "13.31")}
 {al("crit", "wifi-off", "CCTV 03 · Teras offline", "tim support otomatis diberi tahu", "09.42")}</div>"""

    cam = (f'<span class="sel">{ic("video", 14, color=MUTED)}<span class="b">{LIVE_CAM}</span>'
           f'<span class="ink2" style="font-weight:400">· {LIVE_ROOM}</span>{ic("chevron-down", 14, color=MUTED)}</span>')
    body = f"""<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:none">{strip}</div>
<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}<div class="col g12 grow">{video}{events}</div></div>"""
    return page(plane="tenant", active="live", url=f"{APP}/senopati/live/cctv-02",
                title="Pantauan Live", sub="Outlet Senopati · 4 CCTV terpasang · data diperbarui setiap beberapa detik",
                actions='<span class="livepill"><i></i>LIVE</span>' + btn("Mode TV", "tv-minimal") + cam, body=body)


# ================================================================ 03 analitik
DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def _heat_data():
    base = [8, 14, 26, 42, 68, 80, 60, 40, 36, 46, 60, 66, 54, 32, 12]
    mult = (1.0, 0.96, 1.0, 1.05, 1.12, 1.22, 1.16)
    data = []
    for d in range(7):
        row = []
        for i, b in enumerate(base):
            v = b * mult[d]
            if d >= 5:  # weekends run later and longer
                v = (b * 0.55 + base[min(14, i + 1)] * 0.45) * mult[d] + (6 if 4 <= i <= 9 else 0)
            row.append(max(2, min(98, v + 3 * math.sin(d * 1.7 + i * 0.9))))
        data.append(row)
    return base, data


def gantt(w: int, h: int) -> str:
    x0, xr = 100, w - 34
    hr = (xr - x0) / 8  # px per hour, 08.00 - 16.00
    X = lambda t: x0 + (t - 8) * hr
    rh, top = 34, 20
    out = []
    for k in range(9):
        out.append(f'<line x1="{X(8 + k):.1f}" x2="{X(8 + k):.1f}" y1="{top - 4}" y2="{top + rh * len(TABLES)}" stroke="#e1e0d9" stroke-width="1"/>')
        out.append(f'<text x="{X(8 + k):.1f}" y="11" text-anchor="middle" font-size="10.5" fill="{MUTED}" style="font-variant-numeric:tabular-nums">{8 + k:02d}.00</text>')
    for i, (name, seats) in enumerate(TABLES):
        y = top + i * rh
        out.append(f'<text x="0" y="{y + 19}" font-size="12" font-weight="600" fill="{INK}">{name}</text>'
                   f'<text x="50" y="{y + 19}" font-size="11" fill="{MUTED}">{seats} kursi</text>')
        for a, b in SEGS[name]:
            long_ = (b - a) >= LONG_H
            bx, bw = X(a), X(b) - X(a)
            out.append(f'<rect x="{bx:.1f}" y="{y + 7}" width="{bw:.1f}" height="16" rx="4" fill="{ORANGE if long_ else BLUE}"/>')
            if long_:
                d = b - a
                lab = f"{int(d)} jam {round((d - int(d)) * 60):02d} mnt"
                out.append(f'<text x="{bx + bw / 2:.1f}" y="{y + 19}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#fff">{lab}</text>')
    out.append(f'<line x1="{X(NOW):.1f}" x2="{X(NOW):.1f}" y1="{top - 4}" y2="{top + rh * len(TABLES)}" stroke="{INK}" stroke-width="1.5"/>')
    out.append(f'<text x="{X(NOW) - 6:.1f}" y="{top + rh * len(TABLES) + 14}" text-anchor="end" font-size="10.5" font-weight="600" fill="{INK}">sekarang 15.12</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def analytics() -> str:
    base, data = _heat_data()
    rows = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
    cols = [f"{h:02d}" for h in range(8, 23)]
    pi = max(range(7), key=lambda i: max(data[i]))
    pj = max(range(15), key=lambda j: data[pi][j])
    heat = heatmap(752, 232, data, rows, cols, mark=(pi, pj))
    peak_txt = f"Paling ramai: {DAYS[pi]} {8 + pj:02d}.00 · {round(data[pi][pj])}% kursi terisi"

    cust = [round(b * 0.24) for b in base]
    rec = [3 if c >= 14 else 2 for c in cust]
    hi = {i for i, c in enumerate(rec) if c == 3}
    cw = 457
    cols_svg = columns(cw, 150, cust, [f"{h:02d}" for h in range(8, 23)], 21, hi, {max(range(15), key=lambda i: cust[i]): str(max(cust))})
    slot = (cw - 16) / 15

    def rowcells(vals, mark):
        cells = "".join(f'<div class="center tnum" style="width:{slot:.2f}px;font-size:12px;{"font-weight:700;color:var(--blue-d);background:var(--blue-t);border-radius:5px" if mark(i) else "color:var(--ink2)"}">{v}</div>'
                        for i, v in enumerate(vals))
        return f'<div class="row" style="margin-left:8px;height:22px">{cells}</div>'

    staff = f"""<div class="card grow">{cardh("Jumlah tamu vs jumlah staf", "Hari kerja · rata-rata tamu per jam", basis("det"))}
 {cols_svg}<div class="row xs muted" style="margin:2px 0 3px">Staf terjadwal</div>{rowcells([2] * 15, lambda i: False)}
 <div class="row xs muted" style="margin:6px 0 3px"><span>Saran staf</span><span class="chip info" style="margin-left:8px;height:18px">+1 staf di {len(hi)} jam sibuk</span></div>{rowcells(rec, lambda i: i in hi)}</div>"""

    heatcard = f"""<div class="card" style="flex:0 0 61.5%">{cardh("Jam ramai dalam seminggu", "% kursi terisi, rata-rata per jam", basis("det"))}
 {heat}<div class="row sp" style="margin-top:8px"><div class="row g8 xs muted"><span>Sepi</span>{scale_bar(140)}<span>Penuh</span></div><span class="xs b">{peak_txt}</span></div></div>"""

    gcard = f"""<div class="card" style="flex:0 0 61.5%">{cardh("Pemakaian meja hari ini", "Berapa lama tiap meja dipakai, dari buka sampai sekarang", basis("det"))}
 {gantt(752, 252)}<div class="row sp" style="margin-top:6px"><div class="lg"><span><i class="sq" style="background:{BLUE}"></i>Kurang dari 2 jam</span><span><i class="sq" style="background:{ORANGE}"></i>2 jam atau lebih</span></div>
 <span class="xs b">{LONG_TABLES} meja dipakai 2 jam+ · menahan {LONG_SHARE}% kursi saat makan siang</span></div></div>"""

    stages = [("Masuk outlet", 187, ""), ("Ikut antre", 151, "menunggu ±2 menit"), ("Bayar di kasir", 140, ""), ("Duduk di meja", 96, "44 bawa pulang")]
    frows = ""
    for (n, v, note), col in zip(stages, ORDINAL):
        bw = 186 * v / 187
        frows += (f'<div class="row g10" style="height:44px"><div style="width:138px;flex:none"><div class="b" style="font-size:12.5px">{n}</div><div class="xs muted">{note or "&nbsp;"}</div></div>'
                  f'<svg width="186" height="24" viewBox="0 0 186 24" style="flex:none"><rect x="0" y="4" width="{bw:.1f}" height="16" rx="4" fill="{col}"/></svg>'
                  f'<div class="b tnum" style="width:92px;flex:none;white-space:nowrap">{v} <span class="muted" style="font-weight:500">· {round(100 * v / 187)}%</span></div></div>')
    funnel = f"""<div class="card grow">{cardh("Perjalanan tamu hari ini", "Dari pintu masuk sampai duduk", basis("trk"))}
 <div style="margin-top:2px">{frows}</div>
 <div class="row sp" style="margin-top:6px;padding:9px 12px;border-radius:10px;background:var(--warn-t)"><span class="sm" style="color:var(--warn-x)"><b>11 orang (7%)</b> keluar dari antrean sebelum dilayani</span>{chip("Lihat", "warn", "arrow-right")}</div>
 <div class="row g8" style="margin-top:auto;padding-top:8px;align-items:flex-start">{ic("info", 14, color=MUTED)}<span class="xs muted"><b>Estimasi</b> dihitung dari pergerakan orang, bisa meleset saat orang saling menutupi. <b>Akurat</b> dihitung langsung dari jumlah orang di gambar.</span></div></div>"""

    body = f'<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{heatcard}{staff}</div><div class="row g12" style="flex:1;min-height:0;align-items:stretch">{gcard}{funnel}</div>'
    return page(plane="tenant", active="analytics", url=f"{APP}/senopati/analitik",
                title="Analitik", sub="Outlet Senopati · 24–30 Sep 2026 · dibandingkan dengan minggu sebelumnya",
                actions=sel("Periode", "7 hari terakhir") + sel("Bandingkan", "Minggu lalu") + sel("Area", "Semua area") + btn("Download", "download"), body=body)


# ======================================================= 04 perbandingan outlet
OUTLETS = [  # outlet, kota, pengunjung/hari, perubahan, kursi terisi saat ramai, waktu tunggu, kasir kosong mnt/hari, skor
    ("Seminyak", "Bali", 289, "+14%", 98, "1:20", 3, 91),
    ("PIK", "Jakarta Utara", 301, "+11%", 94, "1:35", 4, 88),
    ("Ubud", "Bali", 198, "+7%", 88, "1:42", 5, 86),
    ("Dago", "Bandung", 242, "+8%", 89, "1:48", 5, 84),
    ("Kemang", "Jakarta Selatan", 268, "+3%", 91, "1:52", 6, 82),
    ("Senopati", "Jakarta Selatan", 262, "+6%", 92, "2:05", 7, 79),
    ("Tunjungan", "Surabaya", 223, "+2%", 84, "2:10", 8, 77),
    ("Malioboro", "Yogyakarta", 205, "+1%", 81, "2:18", 9, 74),
    ("Depok", "Depok", 171, "−2%", 73, "2:36", 10, 71),
    ("BSD City", "Tangerang Selatan", 187, "−4%", 76, "2:30", 22, 69),
    ("Bekasi", "Bekasi", 164, "−6%", 74, "2:48", 14, 66),
    ("Braga", "Bandung", 156, "−9%", 71, "3:25", 12, 58),
]


def _network_kpis() -> tuple[str, str, str]:
    """The tiles above the table, computed from its rows so the two always agree."""
    visitors = f"{sum(o[2] for o in OUTLETS) * 30:,}".replace(",", ".")
    peak = round(sum(o[4] for o in OUTLETS) / len(OUTLETS))
    secs = [int(m) * 60 + int(s) for m, s in (o[5].split(":") for o in OUTLETS)]
    mean = sum(secs) / len(secs)
    return visitors, f"{peak}%", f"{int(mean // 60)}:{round(mean % 60):02d}"


def hq() -> str:
    def status(sc):
        if sc >= 80:
            return chip("Sangat baik", "good", "circle-check")
        return chip("Cukup", "warn", "circle-alert") if sc >= 65 else chip("Kritis", "crit", "siren")

    trs = ""
    for i, (n, k, m, d, op, tw, ck, sc) in enumerate(OUTLETS, 1):
        series = [60 + 30 * math.sin(i * 1.3 + j * 0.8) + (sc - 70) * 0.8 + j * (1.5 if d.startswith("+") else -1.5) for j in range(12)]
        dcol = "var(--good-x)" if d.startswith("+") else "var(--crit-x)"
        trs += (f'<tr><td class="muted">{i}</td><td style="line-height:1.2"><div class="b">{n}</div><div class="xs muted">{k}</div></td>'
                f'<td class="n"><span class="b">{m}</span> <span class="xs b" style="color:{dcol}">{d}</span></td>'
                f'<td class="n">{op}%</td><td class="n">{tw}</td><td class="n">{ck} mnt</td>'
                f'<td><div class="row g8"><div class="meter" style="width:64px"><i style="width:{sc}%"></i></div><span class="b tnum">{sc}</span></div></td>'
                f'<td>{spark(series, 58, 22)}</td><td>{status(sc)}</td></tr>')

    cols = "".join(f'<col style="width:{w}px">' for w in (28, 132, 98, 94, 67, 112, 104, 64)) + "<col>"
    table = f"""<div class="card" style="flex:0 0 68%">{cardh("Peringkat outlet · 30 hari", "Skor 0–100 dari keramaian, waktu tunggu, dan kasir yang selalu ada staf", basis("trk"))}
 <table class="cmp" style="table-layout:fixed"><colgroup>{cols}</colgroup>
 <thead><tr><th></th><th>Outlet</th><th class="n">Pengunjung</th><th class="n">Saat ramai</th><th class="n">Tunggu</th><th class="n">Kasir kosong</th><th>Skor</th><th>Tren</th><th>Status</th></tr></thead>
 <tbody>{trs}</tbody></table>
 <div class="row sp" style="margin-top:auto;padding-top:8px"><span class="xs muted">Pengunjung per hari · Saat ramai = kursi terisi saat paling ramai · Tunggu = menit:detik · Kasir kosong per hari</span>
 <span class="btn sm">Detail outlet{ic("arrow-right", 13)}</span></div></div>"""

    scores = [o[7] for o in OUTLETS]
    side = f"""<div class="card grow">{cardh("Perlu dicek minggu ini", "", chip("3 outlet", "neutral"))}
 {item("crit", "trending-up", "Braga · waktu tunggu naik 38%", "Rata-rata 3:25, minggu lalu 2:29. Terjadi 4 dari 7 hari. Kasir kosong 12 menit per hari.")}
 {item("warn", "siren", "BSD City · kasir kosong 22 menit/hari", "Hampir 3× rata-rata outlet lain. Paling sering pukul 12.00–14.00.")}
 {item("info", "armchair", "Seminyak · hampir selalu penuh", "98% kursi terisi saat ramai, penuh 41 menit di akhir pekan. Pertimbangkan tambah kursi atau staf.")}
 <div style="margin-top:auto"><div class="row sp" style="margin-top:6px"><span class="sm b">Skor semua outlet</span><span class="xs muted">terang = sangat baik (80 ke atas)</span></div>
 {columns(364, 250, scores, [str(i) for i in range(1, len(scores) + 1)], 100, {i for i, v in enumerate(scores) if v < 80}, {len(scores) - 1: str(scores[-1])})}</div>
 <div class="row g8" style="padding-top:2px;align-items:flex-start">{ic("info", 14, color=MUTED)}<span class="xs muted">Angka sudah disesuaikan dengan jumlah kursi dan jam buka, jadi outlet besar dan kecil bisa dibandingkan adil.</span></div></div>"""

    visitors, peak, wait = _network_kpis()
    kpis = (mini("Pengunjung 30 hari", visitors, "+5%", "door-open") + mini("Kursi terisi saat ramai", peak, "rata-rata 12 outlet", "gauge")
            + mini("Rata-rata waktu tunggu", wait, "menit", "timer") + mini("Outlet perlu dicek", "3", "dari 12", "triangle-alert"))
    body = f'<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:none">{kpis}</div><div class="row g12" style="flex:1;min-height:0;align-items:stretch">{table}{side}</div>'
    return page(plane="tenant", active="hq", url=f"{APP}/kedai-pagi/perbandingan",
                title="Perbandingan Outlet", sub="Kedai Pagi · 12 outlet · 1–30 Sep 2026 · khusus Owner dan Admin pusat",
                actions=sel("Periode", "30 hari") + sel("Kota", "Semua kota") + btn("Download", "download"), body=body)


# ================================================================ 05 cctv & area
def setup() -> str:
    _, raw = ensure_assets()
    mirror = [(50, 0), (745, 0), (735, 185), (620, 225), (420, 252), (250, 246), (165, 196), (50, 110)]
    cashier = [(1050, 0), (1920, 0), (1920, 120), (1650, 200), (1500, 195), (1080, 150)]
    # The queue zone being drawn: in front of the till and the display case, as on the
    # floor plan. It overlaps the cashier zone at the counter's edge, which is where a
    # queue meets the till, and reaches over the far end of meja 4. It stops short of the
    # man standing in the aisle, and above the middle of the man seated at meja 4, so
    # neither is counted as queuing.
    queue = [(1525, 186), (1650, 190), (1920, 110), (1920, 420), (1640, 405), (1528, 330)]

    def poly(pts, col, dashed=False):
        d = " ".join(f"{x},{y}" for x, y in pts)
        dash = ' stroke-dasharray="18 12"' if dashed else ""
        alpha = ".18" if dashed else ".24"
        o = (f'<polygon points="{d}" fill="{col}" fill-opacity="{alpha}" stroke="{col}" stroke-width="5" '
             f'stroke-linejoin="round"{dash}/>')
        return o + "".join(f'<rect x="{x - 11}" y="{y - 11}" width="22" height="22" rx="5" fill="#fff" stroke="{col}" stroke-width="4"/>' for x, y in pts)

    overlay = (f'<svg viewBox="0 0 1920 1080" preserveAspectRatio="none" style="position:absolute;inset:0;width:100%;height:100%">'
               f'{poly(mirror, "#d03b3b")}{poly(cashier, "#eb6834")}{poly(queue, "#2a78d6", dashed=True)}</svg>')

    def lab(left, top, text, fg, border):
        return (f'<span class="chip" style="position:absolute;left:{left}%;top:{top}%;background:#fff;color:{fg};border:1px solid {border};'
                f'box-shadow:0 2px 6px rgba(0,0,0,.18)">{text}</span>')

    labels = (lab(4.5, 7, "Cermin · tidak dihitung", "#a42626", "#e9b3b3")
              + lab(56, 3.2, "Area kasir · staf", "#9a3a14", "#f3c5ad")
              + lab(80.6, 19.6, "Area antre · draft", "#184f95", "#bcd3f3")
              + f'<span style="position:absolute;left:79.1%;top:17.6%;color:#0b0b0b;filter:drop-shadow(0 1px 2px rgba(255,255,255,.9))">{ic("mouse-pointer-2", 22, 1.8)}</span>'
              + '<span class="chip" style="position:absolute;left:53.5%;top:10.5%;background:rgba(11,11,11,.78);color:#fff">Klik titik pertama untuk menyelesaikan</span>')

    snaps = snapshots()
    times = [("09.12", True), ("11.40", False), ("13.05", False), ("15.20", False), ("18.10", False)]
    strip = "".join(
        f'<div style="position:relative;flex:1;height:64px;border-radius:8px;overflow:hidden;border:2px solid {"#2a78d6" if on else "transparent"}">'
        f'<img src="{u}" style="width:100%;height:100%;object-fit:cover;object-position:50% 40%;display:block{";opacity:.55" if not on else ""}">'
        f'<span class="chip" style="position:absolute;left:5px;bottom:5px;height:18px;font-size:10.5px;background:rgba(11,11,11,.72);color:#fff">{t}{" ✓" if on else ""}</span></div>'
        for u, (t, on) in zip(snaps, times))
    tools = (f'<span class="tool">{ic("mouse-pointer-2", 17)}</span><span class="tool on">{ic("pentagon", 17)}</span>'
             f'<span class="tool">{ic("minus", 17)}</span><span class="tool">{ic("trash-2", 17)}</span>')
    editor = f"""<div class="card grow" style="padding:12px 14px">
 <div class="row sp" style="margin-bottom:10px"><div class="row g4">{tools}<span style="width:1px;height:20px;background:var(--grid);margin:0 8px"></span>
   <span class="sm ink2">Gambar area: klik untuk menambah titik</span></div>
   <div class="row g8">{chip("Foto CCTV 09.12", "neutral", "image")}<span class="btn sm">{ic("refresh-cw", 13)}Ambil ulang</span></div></div>
 <div style="position:relative;border-radius:9px;overflow:hidden;background:#111;aspect-ratio:16/9;width:100%">
  <img src="{data_uri(raw)}" style="width:100%;height:100%;display:block">{overlay}{labels}</div>
 <div class="row sp" style="margin:9px 0 6px"><span class="xs muted">Foto untuk cek akurasi · diambil dari rekaman uji</span><span class="xs muted">Full HD · 5 gambar per detik</span></div>
 <div class="row g8">{strip}</div></div>"""

    def zrow(col, name, kind, sub, dashed=False):
        sw = f'<span style="width:14px;height:14px;border-radius:4px;background:{col}33;border:2px {"dashed" if dashed else "solid"} {col};flex:none;margin-top:2px"></span>'
        return (f'<div class="item" style="padding:9px 0">{sw}<div class="grow"><div class="row sp"><span class="b" style="font-size:13px">{name}</span>{kind}</div>'
                f'<div class="xs muted" style="margin-top:2px">{sub}</div></div></div>')

    cam = f"""<div class="card" style="flex:none">{cardh(f"{LIVE_CAM} · {LIVE_ROOM}", "", chip("Terhubung", "good", "circle-check"))}
 <div class="col g6 sm"><div class="row sp"><span class="ink2">Alamat IP</span><span class="b tnum">192.168.1.21</span></div>
 <div class="row sp"><span class="ink2">Kualitas gambar</span><span class="b">Full HD</span></div>
 <div class="row sp"><span class="ink2">Diproses</span><span class="b">5 gambar per detik</span></div></div></div>"""
    zones = f"""<div class="card grow" style="padding-bottom:6px">{cardh("Area di CCTV ini", "", chip("4", "neutral"))}
 {zrow("#eb6834", "Area kasir", chip("Area staf", "orange"), "untuk menghitung waktu layanan, bukan tamu")}
 {zrow("#2a78d6", "Area antre", chip("Draft", "info"), "menempel ke area kasir · untuk menghitung waktu tunggu", True)}
 {zrow("#d03b3b", "Cermin dinding", chip("Tidak dihitung", "crit"), "pantulan orang di cermin tidak ikut dihitung")}
 {zrow("#898781", "Ruang utama", chip("Dihitung", "neutral"), "seluruh gambar · semua orang dihitung")}</div>"""
    valid = f"""<div class="card" style="flex:none">{cardh("Cek akurasi cepat", "Bandingkan hitungan AI dengan hitungan Anda")}
 <div class="row g10"><div class="grow"><div class="xs muted" style="margin-bottom:4px">Hitungan Anda</div><div class="field"><span class="b">8</span><span class="xs muted">orang</span></div></div>
 <div class="grow"><div class="xs muted" style="margin-bottom:4px">Hitungan AI</div><div class="field" style="background:var(--blue-t);border-color:#bcd3f3"><span class="b">8</span><span class="xs" style="color:var(--blue-d)">7 tamu + 1 staf</span></div></div></div>
 <div class="row sp" style="margin:10px 0 8px">{chip("Sesuai", "good", "circle-check")}<span class="xs muted">Foto 1 dari 5</span></div>
 <div class="meter"><i style="width:20%"></i></div>
 <div class="xs muted" style="margin-top:8px">Hasil dari 5 foto masuk ke laporan akurasi CCTV ini.</div></div>"""

    body = f"""{steps(["Sambungkan CCTV", "Tandai area", "Cek akurasi", "Aktifkan"], 2)}
<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{editor}<div class="col g12" style="flex:0 0 346px">{cam}{zones}{valid}</div></div>"""
    return page(plane="tenant", active="setup", url=f"{APP}/senopati/cctv/02/area",
                title="CCTV &amp; Area", sub="Outlet Senopati · tambah CCTV baru dalam beberapa menit, tanpa teknisi khusus",
                actions=btn("Simpan draft") + btn("Lanjut: cek akurasi", "arrow-right", "pri"), body=body)


# ======================================================== 06 notifikasi & laporan
def alerts() -> str:
    wa = ic("whatsapp", 14, prefix="simple-icons", color="#25d366")  # flat: the gradient logo prints as a bitmap

    def ch(kind):
        m = {"wa": f'<span class="chip neutral">{wa}WhatsApp</span>', "push": f'<span class="chip neutral">{ic("bell", 12, 2)}Notifikasi app</span>',
             "mail": f'<span class="chip neutral">{ic("mail", 12, 2)}Email</span>', "rep": f'<span class="chip neutral">{ic("file-text", 12, 2)}Laporan harian</span>'}
        return m[kind]

    def rule(title, sub, chans, last):
        return (f'<div class="row g12" style="padding:10px 0;border-bottom:1px solid #eceae4">{toggle(True)}'
                f'<div class="grow"><div style="font-size:13.5px">{title}</div><div class="xs muted" style="margin-top:2px">{sub}</div></div>'
                f'<div class="row g6" style="flex:none">{"".join(ch(c) for c in chans)}</div>'
                f'<div class="xs muted tnum" style="width:96px;text-align:right;flex:none">{last}</div></div>')

    rules = f"""<div class="card" style="flex:none;padding-bottom:4px">{cardh("Aturan aktif", "Berlaku selama jam buka", chip("5 aturan", "neutral"))}
 {rule("<b>Kasir kosong</b> 3 menit atau lebih <b>saat</b> 3 orang atau lebih antre", "Dikirim ke: Manager Senopati", ["wa"], "terakhir 13.31")}
 {rule("<b>Kursi terisi</b> 90% atau lebih selama 15 menit", "Dikirim ke: Manager Senopati", ["wa", "push"], "terakhir 13.05")}
 {rule("<b>Antrean</b> 6 orang atau lebih", "Dikirim ke: Supervisor", ["push"], "terakhir 12.58")}
 {rule("<b>CCTV offline</b> 5 menit atau lebih", "Dikirim ke: Admin · tim support otomatis diberi tahu", ["mail"], "terakhir 09.42")}
 {rule("<b>Meja dipakai</b> 3 jam atau lebih", "Tanpa notifikasi, cukup masuk laporan harian", ["rep"], "&mdash;")}</div>"""

    def inl(t):
        return f'<span class="sel" style="height:28px">{t}</span>'

    builder = f"""<div class="card" style="flex:none">{cardh("Buat aturan baru", "Cukup susun kalimat, tanpa coding", chip("Akurat", "good", "circle-check"))}
 <div class="row g8 wrap" style="row-gap:8px"><span class="b xs muted" style="letter-spacing:.06em">JIKA</span>{inl("Kasir")}{inl("kosong")}<span class="sm ink2">selama</span>{inl("3 menit")}
 <span class="b xs muted" style="letter-spacing:.06em">DAN</span>{inl("Antrean")}{inl("lebih dari 2 orang")}
 <span style="width:100%;height:0"></span><span class="b xs muted" style="letter-spacing:.06em">MAKA KIRIM KE</span>{inl("Manager")}<span class="sm ink2">lewat</span>{inl(wa + " WhatsApp")}
 <span class="grow"></span><span class="btn pri">Simpan aturan</span></div></div>"""

    def sch(name, when):
        return f'<div class="row g10" style="padding:7px 0;border-bottom:1px solid #eceae4">{toggle(True)}<div class="grow"><div class="b sm">{name}</div></div><span class="sm ink2">{when}</span></div>'

    schedule = f"""<div class="card grow" style="padding-bottom:4px">{cardh("Laporan otomatis", "Dikirim ke: Lucky (Owner), Bagas (Admin), Sari (Manager)")}
 {sch("Harian", "setiap hari 08.00")}{sch("Mingguan", "setiap Senin 07.00")}{sch("Bulanan", "tanggal 1, 07.00")}</div>"""

    msg1 = ("<b>Laporan harian · Kedai Pagi Senopati</b><br>Rabu, 30 Sep 2026<br><br>"
            "• Pengunjung: <b>241 orang</b> (+3% dari Rabu lalu)<br>• Paling ramai: <b>88%</b> kursi terisi, pukul 12.40<br>"
            "• Kasir kosong: <b>5 menit</b><br>• Rata-rata lama berkunjung: <b>41 menit</b> <i>(estimasi)</i><br><br>"
            f"Catatan: 2 meja dipakai lebih dari 3 jam.<br><span style='color:#2a78d6'>{APP}/senopati</span>")
    msg2 = ("<b>Kasir kosong</b> 4 menit, 5 orang sedang antre.<br>Saran: minta 1 staf ke kasir.<br>"
            f"<span style='color:#2a78d6'>{APP}/senopati/live</span>")
    phone = f"""<div style="flex:0 0 330px;display:flex;justify-content:center">
 <div style="width:318px;height:100%;max-height:696px;border-radius:40px;background:#161615;padding:9px;box-shadow:0 18px 40px rgba(11,11,11,.28)">
  <div style="width:100%;height:100%;border-radius:32px;background:#ece5dd;overflow:hidden;display:flex;flex-direction:column">
   <div style="height:26px;display:flex;align-items:center;justify-content:space-between;padding:0 18px;font-size:11px;font-weight:600;background:#0f5a4c;color:#fff"><span>15.12</span><span>5G ▮▮▮</span></div>
   <div class="row g8" style="padding:9px 12px;background:#0f5a4c;color:#fff">{ic("chevron-left", 18, 2.2)}<span class="logo" style="width:30px;height:30px;border-radius:50%">{logo(17)}</span>
    <div><div style="font-size:13px;font-weight:600;line-height:1.2">{BRAND} · Senopati</div><div style="font-size:10.5px;opacity:.8">akun bisnis</div></div></div>
   <div style="flex:1;padding:12px 10px;display:flex;flex-direction:column;gap:8px;overflow:hidden">
    <div class="center" style="align-self:center;font-size:10.5px;background:#e1f2fb;color:#52514e;border-radius:6px;padding:3px 9px">HARI INI</div>
    <div style="align-self:flex-start;max-width:92%;background:#fff;border-radius:2px 10px 10px 10px;padding:8px 10px 6px;font-size:12px;line-height:1.45;box-shadow:0 1px 1px rgba(0,0,0,.12)">{msg1}<div class="right" style="font-size:10px;color:#898781;margin-top:3px">08.00</div></div>
    <div style="align-self:flex-start;max-width:92%;background:#fff;border-radius:2px 10px 10px 10px;padding:8px 10px 6px;font-size:12px;line-height:1.45;box-shadow:0 1px 1px rgba(0,0,0,.12)">{msg2}<div class="right" style="font-size:10px;color:#898781;margin-top:3px">13.31</div></div>
   </div>
   <div class="row g8" style="padding:8px 10px;background:#f4f0ea"><div style="flex:1;height:30px;border-radius:15px;background:#fff;font-size:11.5px;color:#898781;display:flex;align-items:center;padding:0 12px">Pesan otomatis dari {BRAND}</div></div>
  </div></div></div>"""

    body = f'<div class="row g14" style="flex:1;min-height:0;align-items:stretch"><div class="col g12 grow">{rules}{builder}{schedule}</div>{phone}</div>'
    return page(plane="tenant", active="alert", url=f"{APP}/senopati/notifikasi",
                title="Notifikasi &amp; Laporan", sub="Outlet Senopati · info penting langsung ke WhatsApp, tanpa harus membuka dashboard",
                actions=btn("Riwayat", "history") + btn("Buat aturan", "plus", "pri"), body=body)


# ================================================================ 07 tim & hak akses
def users() -> str:
    def u(init, name, mail, role, scope, tfa, last, kind="info"):
        t = (f'<span class="row g4" style="color:var(--good-x)">{ic("shield-check", 15, 2)}<span class="xs b">aktif</span></span>' if tfa
             else f'<span class="row g4" style="color:var(--warn-x)">{ic("triangle-alert", 15, 2)}<span class="xs b">belum</span></span>')
        return (f'<tr><td><div class="row g10"><div class="av" style="width:28px;height:28px;font-size:10.5px">{init}</div><div><div class="b">{name}</div><div class="xs muted">{mail}</div></div></div></td>'
                f'<td>{chip(role, kind)}</td><td class="ink2">{scope}</td><td>{t}</td><td class="muted">{last}</td></tr>')

    rows = (u("L", "Lucky", "lucky@kedaipagi.id", "Owner", "Semua outlet", True, "2 menit lalu", "orange")
            + u("BP", "Bagas Pratama", "bagas@kedaipagi.id", "Admin", "Semua outlet", True, "1 jam lalu")
            + u("SW", "Sari Wulandari", "sari@kedaipagi.id", "Manager", "Senopati", True, "12 menit lalu")
            + u("DH", "Dimas Hartono", "dimas@kedaipagi.id", "Manager", "Kemang", False, "kemarin")
            + u("PL", "Putri Lestari", "putri@kedaipagi.id", "Analis", "Semua outlet · lihat saja", True, "3 hari lalu")
            + u("TV", "TV ruang staf", "perangkat · Mode TV", "Layar TV", "Senopati", True, "online", "neutral")
            + u("TC", "Teknisi CCTV (mitra)", "mitra@cctvjaya.id", "Teknisi", "Senopati · s.d. 3 Okt", True, "2 hari lalu", "neutral"))
    ucols = "".join(f'<col style="width:{w}px">' for w in (206, 98, 172, 96)) + "<col>"
    left = f"""<div class="card" style="flex:0 0 55.5%">{cardh("Anggota tim", "Peran menentukan apa yang bisa dilihat dan diubah · Verifikasi = login 2 langkah", chip("7 orang", "neutral"))}
 <table class="roomy" style="table-layout:fixed"><colgroup>{ucols}</colgroup><thead><tr><th>Nama</th><th>Peran</th><th>Akses outlet</th><th>Verifikasi</th><th>Terakhir aktif</th></tr></thead><tbody>{rows}</tbody></table>
 <div style="margin:12px 0 4px"><div class="row sp" style="margin-bottom:2px"><span class="sm b">Undangan belum diterima</span>{chip("2", "neutral")}</div>
  <div class="row g10" style="padding:8px 0;border-bottom:1px solid #eceae4">{ic("mail", 16, color=MUTED)}<span class="grow sm"><b>anton@kedaipagi.id</b> <span class="muted">· Manager · Braga · dikirim 2 hari lalu</span></span><span class="btn sm">Kirim ulang</span></div>
  <div class="row g10" style="padding:8px 0">{ic("mail", 16, color=MUTED)}<span class="grow sm"><b>laras@kedaipagi.id</b> <span class="muted">· Analis · semua outlet · dikirim kemarin</span></span><span class="btn sm">Kirim ulang</span></div></div>
 <div class="row g10" style="margin-top:auto;padding:11px 13px;border-radius:10px;background:var(--blue-t)">{ic("sparkles", 17, color="#184f95")}
  <div class="grow"><div class="b sm" style="color:var(--blue-d)">Peran khusus <span class="chip info" style="height:18px;margin-left:6px">Enterprise</span></div>
  <div class="xs" style="color:#2d4f80;margin-top:2px">Buat peran sendiri, misalnya &ldquo;Area Manager Bandung&rdquo; yang hanya bisa melihat outlet Dago dan Braga.</div></div></div></div>"""

    tk, no = ic("check", 17, 2.6, "tick"), '<span class="cross">&ndash;</span>'

    def c(x):
        if x is True:
            return tk
        if x is False:
            return no
        return f'<span class="chip neutral" style="height:18px;padding:0 5px;font-size:10px">{x}</span>'

    caps = [("Pantauan live", [True, True, "outletnya", False, "outletnya", False]),
            ("Analitik & perbandingan", [True, True, "outletnya", True, False, False]),
            ("Download data", [True, True, "outletnya", True, False, False]),
            ("Notifikasi & laporan", [True, True, "outletnya", False, False, False]),
            ("CCTV & area", [True, True, False, False, False, "sementara"]),
            ("Tim & hak akses", [True, "terbatas", False, False, False, False]),
            ("Privasi & data", [True, False, False, False, False, False]),
            ("Tagihan & paket", [True, False, False, False, False, False]),
            ("Riwayat aktivitas", [True, "lihat", False, False, False, False])]
    heads = "".join(f'<th class="center" style="padding:0 2px 8px;font-size:10px">{h}</th>' for h in ["Owner", "Admin", "Manager", "Analis", "Layar TV", "Teknisi"])
    mrows = "".join(f'<tr><td style="padding:9px 6px;font-size:12.5px">{n.replace("&", "&amp;")}</td>' + "".join(f'<td class="center" style="padding:9px 2px">{c(x)}</td>' for x in v) + "</tr>" for n, v in caps)
    right = f"""<div class="card grow">{cardh("Siapa bisa apa", f"Hak akses tiap peran. Super Admin tidak ada di sini karena itu tim internal {BRAND}.")}
 <table class="rm" style="table-layout:fixed"><colgroup><col style="width:136px"><col><col><col><col><col><col></colgroup><thead><tr><th style="padding-left:6px">Fitur</th>{heads}</tr></thead><tbody>{mrows}</tbody></table>
 <div class="row g10" style="margin-top:14px;padding:11px 13px;border-radius:10px;background:var(--orange-t)">{ic("lock", 17, color="#9a3a14")}
  <div class="sm" style="color:#7a2f0f"><b>Tim internal {BRAND}</b> tidak bisa melihat data Anda tanpa izin Owner. Izinnya sementara dan tercatat di riwayat aktivitas.</div></div>
 <div style="margin-top:14px"><div class="sm b" style="margin-bottom:2px">Keamanan akun</div>
  <div class="row g12" style="padding:9px 0;border-bottom:1px solid #eceae4">{toggle(True)}<div class="grow sm">Wajib verifikasi 2 langkah untuk Owner dan Admin</div></div>
  <div class="row g12" style="padding:9px 0;border-bottom:1px solid #eceae4">{toggle(False)}<div class="grow sm">Login dengan akun Google / Microsoft</div>{chip("Enterprise", "info")}</div>
  <div class="row g12" style="padding:9px 0">{toggle(True)}<div class="grow sm">Otomatis logout setelah 12 jam tidak aktif</div></div></div>
 <div class="row g14 xs muted wrap" style="margin-top:auto;padding-top:8px;row-gap:3px"><span><b>outletnya</b> = hanya outlet yang ditugaskan</span><span><b>sementara</b> = ada batas waktunya</span><span><b>terbatas</b> = tidak bisa mengubah Owner</span></div></div>"""
    body = f'<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}{right}</div>'
    return page(plane="tenant", active="users", url=f"{APP}/kedai-pagi/tim",
                title="Tim &amp; Hak Akses", sub="Kedai Pagi · 7 orang · 12 outlet · hanya Owner dan Admin",
                actions='<span class="search">' + ic("search", 14) + "Cari nama</span>" + sel("Peran", "Semua peran") + btn("Undang anggota", "user-plus", "pri"), body=body)


# ============================================================ 08 privasi & keamanan
def privacy() -> str:
    def pr(title, sub, ctl):
        return (f'<div class="item" style="align-items:center;padding:10px 0"><div class="grow"><div class="b" style="font-size:13px">{title}</div>'
                f'<div class="xs muted" style="margin-top:2px;line-height:1.4">{sub}</div></div>{ctl}</div>')

    left = f"""<div class="card" style="flex:0 0 45%;padding-bottom:6px">{cardh("Pengaturan privasi", "Hanya menyimpan data yang benar-benar perlu")}
 {pr("Video tidak keluar dari outlet", "Yang dikirim ke cloud hanya angka dan titik tanpa identitas, bukan gambar.", toggle(lock=True))}
 {pr("Tanpa wajah, tanpa nama", "Sistem tidak mengenali wajah dan tidak tahu siapa orangnya.", toggle(lock=True))}
 {pr("Buka video CCTV dari aplikasi", "Hanya Owner dan Admin, dan hanya dari jaringan outlet.", toggle(True))}
 {pr("Laporan per staf", "Mati. Waktu layanan hanya dilaporkan per area kasir. Menyalakan butuh persetujuan Owner dan pemberitahuan ke tim.", toggle(False))}
 {pr("Lama penyimpanan data detail", "Setelah itu hanya ringkasan harian yang disimpan.", '<span class="sel" style="height:28px">13 bulan' + ic("chevron-down", 14, color=MUTED) + "</span>")}
 {pr("Download tanpa data per orang", "File yang di-download hanya berisi ringkasan.", toggle(True))}
 {pr("Area yang tidak dihitung", "1 aktif: cermin dinding (Senopati, CCTV 02).", '<span class="btn sm">Kelola</span>')}
 {pr("Permintaan data dari pelanggan", "Tanggapi permintaan lihat atau hapus data; semuanya tercatat.", '<span class="btn sm">Buka</span>')}
 <div style="margin-top:auto;padding-top:12px"><div class="sm b" style="margin-bottom:8px">Data apa yang disimpan</div>
 <div class="grid" style="grid-template-columns:1fr 1fr;gap:10px">
  <div style="border:1px solid var(--border);border-radius:10px;padding:10px 12px;background:#fff"><div class="row g6 b sm" style="color:var(--good-x)">{ic("circle-check", 15, 2.2)}Disimpan</div>
   <div class="xs ink2" style="margin-top:6px;line-height:1.65">Jumlah orang per menit<br>Lama berada di tiap area (tanpa identitas)<br>Kejadian: antrean, kasir, notifikasi</div></div>
  <div style="border:1px solid var(--border);border-radius:10px;padding:10px 12px;background:#fff"><div class="row g6 b sm" style="color:var(--crit-x)">{ic("ban", 15, 2.2)}Tidak pernah disimpan</div>
   <div class="xs ink2" style="margin-top:6px;line-height:1.65">Video dan foto<br>Wajah atau ciri tubuh<br>Nama atau identitas tamu</div></div></div></div></div>"""

    req = f"""<div class="card" style="flex:none;border-color:#f3c5ad;background:#fffaf7">{cardh("Permintaan akses dari tim support", "", chip("menunggu persetujuan", "orange", "clock"))}
 <div class="row g12" style="align-items:flex-start"><div class="av" style="background:#fdeae1;color:#9a3a14">DS</div>
 <div class="grow"><div style="font-size:13.5px"><b>Dewi S.</b> (Support {BRAND}) minta izin <b>melihat</b> data <b>Senopati</b> selama <b>60 menit</b>.</div>
 <div class="ink2 sm" style="margin-top:3px">Alasan: &ldquo;CCTV 03 · Teras offline sejak 09.42, perlu cek perangkat.&rdquo;</div>
 <div class="row g8" style="margin-top:10px"><span class="btn pri sm">Izinkan 60 menit</span><span class="btn sm">Tolak</span><span class="xs muted" style="margin-left:6px">berakhir dalam 14:32</span></div></div></div></div>"""

    def lg(t, who, act, obj):
        return f'<tr><td class="muted">{t}</td><td class="b">{who}</td><td>{act}</td><td class="ink2" style="white-space:normal">{obj}</td></tr>'

    log = f"""<div class="card grow" style="padding-bottom:6px">{cardh("Riwayat aktivitas", "Semua aksi penting tercatat dan tidak bisa diubah", chip("hari ini", "neutral"))}
 <table class="lgt"><thead><tr><th>Waktu</th><th>Siapa</th><th>Melakukan</th><th>Detail</th></tr></thead><tbody>
 {lg("15.04", "Sari W. · Manager", "Download data", "Analitik · 7 hari")}
 {lg("14.31", "Bagas P. · Admin", "Mengubah area", "Senopati · CCTV 02 · area kasir")}
 {lg("13.31", "Sistem", "Kirim notifikasi", "Kasir kosong &rarr; WhatsApp")}
 {lg("11.02", "Lucky · Owner", "Mengubah aturan", "Kasir kosong · 3 menit")}
 {lg("09.42", "Sistem", "CCTV offline", "Senopati · CCTV 03 Teras")}
 {lg("08.00", "Sistem", "Kirim laporan", "Harian · 3 orang")}
 {lg("07.55", "Dimas H. · Manager", "Gagal login", "verifikasi 2 langkah belum aktif")}
 {lg("kemarin", "Teknisi CCTV", "Menambah CCTV", "Senopati · CCTV 03 Teras")}
 {lg("kemarin", "Putri L. · Analis", "Membuka analitik", "Perbandingan outlet · 30 hari")}
 {lg("kemarin", "Sistem", "Update AI", "Perangkat Senopati · versi 2.3 &rarr; 2.4")}
 {lg("kemarin", "Bagas P. · Admin", "Mengundang anggota", "laras@kedaipagi.id · Analis")}
 {lg("2 hari lalu", "Bagas P. · Admin", "Mengundang anggota", "anton@kedaipagi.id · Manager Braga")}</tbody></table></div>"""
    body = f'<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}<div class="col g12 grow">{req}{log}</div></div>'
    return page(plane="tenant", active="privacy", url=f"{APP}/kedai-pagi/privasi",
                title="Privasi &amp; Keamanan", sub="Kedai Pagi · atur data yang disimpan dan lihat siapa melakukan apa · khusus Owner",
                actions=btn("Download riwayat", "download"), body=body)


# ================================================================ panel internal
PLATFORM_NOTE = (f'{ic("lock", 15)}<span>Anda hanya melihat <b>data teknis</b> (status perangkat dan CCTV). Data bisnis klien hanya bisa dibuka '
                 'dengan izin Owner: sementara dan tercatat.</span>')


def plan_chip(name: str) -> str:
    if name == "Enterprise":
        return '<span class="chip" style="background:#1a1a19;color:#fff">Enterprise</span>'
    return chip(name, "info" if name == "Growth" else "neutral")


# ========================================================= 09 super admin: klien
# Twelve clients, 43 outlets, one AI device per outlet. The page lists eight; the
# other four run seven outlets and 18 CCTVs, all online. The tiles above both
# tables are computed from these, so the panel never contradicts itself.
CLIENTS = [  # nama, jenis, paket, outlet, cctv online, cctv total, status, login terakhir, aksi
    ("Kedai Pagi", "Kafe", "Enterprise", 12, 46, 48, "warn", "2 menit lalu", "wait"),
    ("Roti Hangat", "Toko roti", "Growth", 7, 21, 21, "ok", "1 jam lalu", ""),
    ("Fit Studio Kota", "Gym", "Growth", 3, 8, 8, "ok", "kemarin", ""),
    ("Optik Jernih", "Toko ritel", "Growth", 5, 14, 15, "warn", "3 jam lalu", ""),
    ("Toko Buku Pelangi", "Toko ritel", "Growth", 4, 11, 12, "ok", "kemarin", ""),
    ("Klinik Sehat Bersama", "Klinik", "Starter", 2, 4, 4, "ok", "2 hari lalu", ""),
    ("Apotek Sentosa", "Apotek", "Starter", 2, 4, 4, "ok", "kemarin", ""),
    ("Kopi Tetangga", "Kafe", "Starter", 1, 0, 2, "bad", "5 jam lalu", "ask"),
]
OTHER_CLIENTS = (4, 7, 18, 18)  # klien, outlet, cctv online, cctv total - not listed on the page
DEVICES = sum(c[3] for c in CLIENTS) + OTHER_CLIENTS[1]  # 43
DEVICES_ON = DEVICES - 1                                   # Kopi Tetangga's is offline
ON_NEW = 11                                                # on version 2.4 after stage 2


def sa_tenants() -> str:
    def health(kind):
        return {"ok": chip("Normal", "good", "circle-check"), "warn": chip("Perlu dicek", "warn", "circle-alert"),
                "bad": chip("Ada masalah", "crit", "siren")}[kind]

    def action(kind):
        if kind == "ask":
            return f'<span class="btn sm">{ic("lock", 12)}Minta akses</span>'
        if kind == "wait":
            return chip("Menunggu izin", "orange", "clock")
        return '<span class="btn sm">Detail</span>'

    rows = "".join(f'<tr><td><div class="b">{n}</div><div class="xs muted">{k}</div></td><td>{plan_chip(pl)}</td><td class="n">{o}</td>'
                   f'<td class="n">{on} / {tot}</td><td>{health(h)}</td><td class="muted">{last}</td><td>{action(a)}</td></tr>'
                   for n, k, pl, o, on, tot, h, last, a in CLIENTS)
    n_clients = len(CLIENTS) + OTHER_CLIENTS[0]
    left = f"""<div class="card" style="flex:0 0 63.5%">{cardh("Klien", "Status teknis tiap klien, tanpa data bisnis mereka", chip(f"{len(CLIENTS)} dari {n_clients}", "neutral"))}
 <table class="roomy"><thead><tr><th>Klien</th><th>Paket</th><th class="n">Outlet</th><th class="n">CCTV online</th><th>Status</th><th>Login terakhir</th><th></th></tr></thead><tbody>{rows}</tbody></table>
 <div class="row g8" style="margin-top:auto;padding-top:10px">{ic("lock", 14, color=MUTED)}<span class="xs muted">&ldquo;Minta akses&rdquo; mengirim permintaan ke Owner klien. Tanpa persetujuan, data tidak terbuka.</span></div></div>"""

    tk, no = ic("check", 17, 2.6, "tick"), '<span class="cross">&ndash;</span>'

    def v(x):
        if x is True:
            return tk
        if x is False:
            return no
        return f'<span class="xs b">{x}</span>'

    feats = [("Harga per outlet / bulan", ["Rp 500 rb", "Rp 1,5 jt", "sesuai kontrak"]),
             ("CCTV per outlet", ["maks. 2", "maks. 4", "bebas"]),
             ("Pantauan live", [True, True, True]), ("Riwayat analitik", ["30 hari", "13 bulan", "bebas"]),
             ("Antrean &amp; kasir", [False, True, True]), ("Notifikasi WhatsApp", ["email saja", True, True]),
             ("Perbandingan outlet", [False, False, True]), ("Sambung ke mesin kasir", [False, False, True]),
             ("Login Google &amp; peran khusus", [False, False, True]), ("Garansi layanan (SLA)", [False, False, True])]
    frows = "".join(f'<tr><td style="padding:9px 6px;font-size:12.5px">{n}</td>' + "".join(f'<td class="center" style="padding:9px 2px">{v(x)}</td>' for x in xs) + "</tr>" for n, xs in feats)
    right = f"""<div class="card grow">{cardh("Paket &amp; fitur", "Atur fitur yang didapat tiap paket", '<span class="btn sm org">Ubah paket</span>')}
 <table style="table-layout:fixed"><colgroup><col style="width:170px"><col><col><col></colgroup><thead><tr><th style="padding-left:6px">Fitur</th><th class="center">Starter</th><th class="center">Growth</th><th class="center">Enterprise</th></tr></thead><tbody>{frows}</tbody></table>
 <div class="row g10" style="margin-top:auto;padding:10px 12px;border-radius:10px;background:var(--orange-t)">{ic("flag", 16, color="#9a3a14")}
  <div class="sm" style="color:#7a2f0f"><b>2 klien</b> punya fitur khusus di luar paketnya.</div></div></div>"""
    cam_on = sum(c[4] for c in CLIENTS) + OTHER_CLIENTS[2]
    cam_all = sum(c[5] for c in CLIENTS) + OTHER_CLIENTS[3]
    pct = f"{100 * cam_on / cam_all:.1f}".replace(".", ",") + "%"
    problems = sum(1 for c in CLIENTS if c[6] != "ok")
    kpis = (mini("CCTV online", pct, f"{cam_on} dari {cam_all}", "video") + mini("Perangkat AI online", f"{DEVICES_ON} / {DEVICES}", "", "server")
            + mini("Sudah pakai versi 2.4", f"{ON_NEW} / {DEVICES}", "tahap 2 dari 3", "rocket")
            + mini("Klien perlu dicek", str(problems), "1 mendesak", "siren"))
    body = f'<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:none">{kpis}</div><div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}{right}</div>'
    return page(plane="platform", active="tenant", url=f"{PANEL}/klien", title="Klien &amp; Paket",
                sub=f"Panel internal · khusus tim {BRAND} · semua aksi tercatat",
                actions='<span class="search">' + ic("search", 14) + "Cari klien</span>" + btn("Tambah klien", "plus", "org"),
                body=body, banner=PLATFORM_NOTE)


# ===================================================== 10 super admin: perangkat
def sa_fleet() -> str:
    def st(kind):
        return {"on": chip("Online", "good", "circle-check"), "off": chip("Offline", "crit", "wifi-off"),
                "hot": chip("Terlalu panas", "warn", "thermometer")}[kind]

    devices = [("AI-0112", "Kedai Pagi · Senopati", "on", "2.4", "3 / 4", "61°C", "3 detik"),
               ("AI-0113", "Kedai Pagi · Kemang", "on", "2.4", "4 / 4", "64°C", "2 detik"),
               ("AI-0131", "Kedai Pagi · Dago", "on", "2.4", "4 / 4", "60°C", "2 detik"),
               ("AI-0130", "Kedai Pagi · Braga", "hot", "2.4", "4 / 4", "83°C", "3 detik"),
               ("AI-0087", "Roti Hangat · Pusat", "on", "2.3", "3 / 3", "58°C", "4 detik"),
               ("AI-0121", "Optik Jernih · Mall A", "on", "2.4", "2 / 3", "66°C", "3 detik"),
               ("AI-0102", "Toko Buku Pelangi · Cab. 2", "on", "2.3", "4 / 4", "57°C", "4 detik"),
               ("AI-0076", "Fit Studio Kota · Kuningan", "on", "2.3", "3 / 3", "56°C", "5 detik"),
               ("AI-0045", "Klinik Sehat · Lobi", "on", "2.3", "2 / 2", "55°C", "5 detik"),
               ("AI-0099", "Kopi Tetangga · Utama", "off", "2.3", "0 / 2", "&mdash;", "5 jam lalu")]
    rows = "".join(f'<tr><td class="b">{dev}</td><td class="ink2">{cl}</td><td>{st(k)}</td><td>{ver}</td><td class="n">{cams}</td>'
                   f'<td class="n">{temp}</td><td class="muted">{seen}</td></tr>' for dev, cl, k, ver, cams, temp, seen in devices)
    fcols = "".join(f'<col style="width:{w}px">' for w in (92, 200, 136, 84, 62, 66)) + "<col>"
    left = f"""<div class="card" style="flex:0 0 62.5%">{cardh("Perangkat AI di outlet", "Satu perangkat per outlet: membaca CCTV, menghitung orang, lalu mengirim angkanya saja", chip(f"{len(devices)} dari {DEVICES}", "neutral"))}
 <table class="roomy" style="table-layout:fixed"><colgroup>{fcols}</colgroup><thead><tr><th>Perangkat</th><th>Klien · outlet</th><th>Status</th><th>Versi AI</th><th class="n">CCTV</th><th class="n">Suhu</th><th>Terakhir aktif</th></tr></thead><tbody>{rows}</tbody></table>
 <div class="row g8" style="margin-top:auto;padding-top:10px">{ic("info", 14, color=MUTED)}<span class="xs muted">Setiap versi AI diuji dulu di sebagian kecil perangkat sebelum dikirim ke semua.</span></div></div>"""

    def gate(kind, text):
        icn, col = ("circle-check", "var(--good-x)") if kind == "ok" else ("circle-alert", "var(--warn-x)")
        return f'<div class="row g8" style="padding:4px 0"><span style="color:{col}">{ic(icn, 16, 2.2)}</span><span class="sm">{text}</span></div>'

    def stage(i, state, title, meta, extra=""):
        circ = (f'<span class="stp done">{ic("check", 13, 2.8)}</span>' if state == "done" else f'<span class="stp on">{i}</span>' if state == "on" else f'<span class="stp">{i}</span>')
        return (f'<div class="row g10" style="align-items:flex-start;padding:7px 0">{circ}<div class="grow"><div class="row sp"><span class="b" style="font-size:13px">{title}</span>'
                f'<span class="xs muted">{meta}</span></div>{extra}</div></div>')

    rollout = f"""<div class="card" style="flex:none">{cardh("Update AI versi 2.4", "Dikirim bertahap, otomatis berhenti kalau ada masalah", chip("sedang berjalan", "info", "rocket"))}
 {stage(1, "done", "Uji coba · 5%", "2 perangkat · 48 jam", '<div class="xs muted" style="margin-top:2px">Lolos semua syarat</div>')}
 {stage(2, "on", "Tahap 2 · 25%", f"{ON_NEW} perangkat · 17 dari 48 jam", '<div class="meter org" style="margin-top:7px"><i style="width:35%"></i></div>')}
 {stage(3, "", "Semua perangkat · 100%", f"{DEVICES} perangkat", '<div class="xs muted" style="margin-top:2px">Menunggu tahap 2 selesai</div>')}
 <div class="sep" style="margin:8px 0 6px"></div><div class="xs b muted" style="letter-spacing:.06em;margin-bottom:2px">SYARAT LANJUT</div>
 {gate("ok", "Hitungan tetap sesuai dengan hitungan manual")}{gate("ok", "Tidak lebih sering keliru membedakan orang")}
 {gate("ok", "Semua perangkat tahap 2 tetap lancar")}{gate("warn", "Suhu perangkat di bawah 80°C: 1 perangkat di atas (Braga)")}
 <div class="row g8" style="margin-top:10px"><span class="btn sm">Jeda</span><span class="btn sm">Kembali ke versi 2.3</span><span class="grow"></span><span class="btn org sm" style="opacity:.55">Kirim ke semua</span></div></div>"""

    old = DEVICES - ON_NEW
    p_new = round(100 * ON_NEW / DEVICES)
    dist = f"""<div class="card grow"><div class="card-h" style="margin-bottom:8px"><h3>Versi AI di semua perangkat</h3></div>
 <div class="row" style="gap:2px"><div style="flex:{ON_NEW};height:16px;background:{BLUE};border-radius:5px 0 0 5px"></div><div style="flex:{old};height:16px;background:{ORANGE};border-radius:0 5px 5px 0"></div></div>
 <div class="row sp" style="margin-top:9px"><div class="lg"><span><i class="sq" style="background:{BLUE}"></i>Versi 2.4 · {p_new}%</span><span><i class="sq" style="background:{ORANGE}"></i>Versi 2.3 · {100 - p_new}%</span></div>
 <span class="xs muted">{ON_NEW} dan {old} perangkat</span></div>
 <div class="row g8" style="margin-top:auto;padding-top:10px;align-items:flex-start">{ic("moon", 14, color=MUTED)}<span class="xs muted">Update dipasang saat outlet sudah tutup, jadi pantauan di jam buka tidak pernah terputus.</span></div></div>"""
    kpis = (mini("Perangkat online", f"{DEVICES_ON} / {DEVICES}", "", "server") + mini("Sudah pakai versi 2.4", f"{ON_NEW} / {DEVICES}", "tahap 2 dari 3", "rocket")
            + mini("Suhu rata-rata", "62°C", "tertinggi 83°C", "thermometer") + mini("Data sampai ke cloud", "±3 detik", "dari outlet", "timer"))
    body = f'<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:none">{kpis}</div><div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}<div class="col g12 grow">{rollout}{dist}</div></div>'
    return page(plane="platform", active="fleet", url=f"{PANEL}/perangkat", title="Perangkat AI &amp; Update",
                sub="Panel internal · perangkat AI di setiap outlet dan update yang dikirim bertahap",
                actions=btn("Siapkan versi baru", "cpu") + btn("Kirim update", "rocket", "org"), body=body, banner=PLATFORM_NOTE)


# ================================================================ 00 peta halaman
def overview(thumbs: dict[str, str]) -> str:
    from kit import CSS, font_css

    def card(name, num, title, desc, who, accent):
        chips = "".join(f'<span class="chip neutral" style="height:21px;font-size:11.5px;padding:0 8px">{w}</span>' for w in who)
        return (f'<div style="background:#fff;border:1px solid var(--border);border-radius:12px;padding:9px;display:flex;flex-direction:column;gap:6px;min-width:0">'
                f'<div style="position:relative;border-radius:8px;overflow:hidden;outline:1px solid rgba(11,11,11,.10)"><img src="{thumbs[name]}" style="width:100%;display:block">'
                f'<span style="position:absolute;left:7px;top:7px;width:22px;height:22px;border-radius:50%;background:{accent};color:#fff;font-size:11.5px;font-weight:700;display:grid;place-items:center">{num}</span></div>'
                f'<div class="b" style="font-size:15px;margin-top:3px">{title}</div><div class="ink2" style="font-size:12.5px;line-height:1.45;min-height:37px">{desc}</div>'
                f'<div class="row g4 wrap">{chips}</div></div>')

    cust = [("01-ringkasan", 1, "Ringkasan Hari Ini", "Angka penting hari ini dan hal yang perlu ditindaklanjuti.", ["Owner", "Admin", "Manager"]),
            ("02-pantauan-live", 2, "Pantauan Live", "Kondisi outlet saat ini per CCTV: denah, antrean, kasir, video.", ["Manager", "Layar TV"]),
            ("03-analitik", 3, "Analitik", "Jam ramai, pemakaian meja, perjalanan tamu, kebutuhan staf.", ["Owner", "Admin", "Analis"]),
            ("04-perbandingan-outlet", 4, "Perbandingan Outlet", "Peringkat 12 outlet dan outlet yang perlu dicek.", ["Owner", "Admin pusat"]),
            ("05-cctv-area", 5, "CCTV &amp; Area", "Sambungkan CCTV, tandai area kasir dan antre, cek akurasi.", ["Admin", "Teknisi"]),
            ("06-notifikasi-laporan", 6, "Notifikasi &amp; Laporan", "Aturan otomatis dan laporan rutin lewat WhatsApp.", ["Owner", "Admin", "Manager"]),
            ("07-tim-hak-akses", 7, "Tim &amp; Hak Akses", "Undang anggota tim dan atur siapa bisa apa.", ["Owner", "Admin"]),
            ("08-privasi-keamanan", 8, "Privasi &amp; Keamanan", "Data yang disimpan, izin support, riwayat aktivitas.", ["Owner"])]
    plat = [("09-superadmin-klien", 9, "Klien &amp; Paket", "Semua klien, paket, fitur, dan permintaan akses.", ["Super Admin", "Support"]),
            ("10-superadmin-perangkat", 10, "Perangkat AI &amp; Update", "Perangkat AI di outlet dan update bertahap.", ["Super Admin"])]
    later = ["Tagihan &amp; pembayaran", "Support (izin sementara)", "Fitur khusus per klien", "Riwayat internal"]

    def principle(icon_, title, text):
        return (f'<div class="row g12" style="flex:1;background:#fff;border:1px solid var(--border);border-radius:12px;padding:16px 18px">'
                f'<span class="ibox info" style="width:36px;height:36px;border-radius:11px">{ic(icon_, 19)}</span><div><div class="b" style="font-size:15px">{title}</div>'
                f'<div class="ink2" style="font-size:12.5px;margin-top:3px;line-height:1.45">{text}</div></div></div>')

    return f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><style>{font_css()}{CSS}</style></head>
<body><div class="stage" style="background:var(--page);padding:34px 36px 44px;display:flex;flex-direction:column;justify-content:space-between">
 <div class="row sp" style="flex:none"><div><div class="row g10"><span class="logo">{logo()}</span><h1 style="font-size:26px">{BRAND} · Peta Halaman</h1></div>
  <div class="sub" style="margin-top:4px">Satu aplikasi, dua sisi: untuk klien dan untuk tim internal · 10 halaman utama</div></div>
  <div class="row g8 sm ink2"><span class="chip info">Aplikasi klien</span><span class="chip orange">Panel internal</span></div></div>
 <div class="row g14" style="align-items:flex-start;flex:none">
  <div style="flex:0 0 1010px;background:#eef3fb;border:1px solid #cfdcf1;border-radius:16px;padding:14px 16px 16px">
   <div class="row sp" style="margin-bottom:11px"><div class="b" style="font-size:13px;letter-spacing:.09em;color:var(--blue-d)">APLIKASI KLIEN</div>
    <div class="xs ink2">Owner · Admin · Manager · Analis · Layar TV · Teknisi</div></div>
   <div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px">{"".join(card(n, i, t, d, w, "#2a78d6") for n, i, t, d, w in cust)}</div></div>
  <div style="flex:1;background:#fdf1ea;border:1px solid #f3cfba;border-radius:16px;padding:14px 16px 16px">
   <div class="row sp" style="margin-bottom:11px"><div class="b" style="font-size:13px;letter-spacing:.09em;color:var(--orange-d)">PANEL INTERNAL</div><div class="xs ink2">khusus tim {BRAND}</div></div>
   <div class="grid" style="grid-template-columns:1fr 1fr;gap:12px">{"".join(card(n, i, t, d, w, "#eb6834") for n, i, t, d, w in plat)}</div>
   <div class="xs b muted" style="letter-spacing:.06em;margin:14px 0 8px">BERIKUTNYA</div>
   <div class="grid" style="grid-template-columns:1fr 1fr;gap:8px">{"".join(f'<div style="border:1.5px dashed #e2b9a1;border-radius:10px;padding:11px 12px;font-size:12.5px;color:#7a2f0f">{t}</div>' for t in later)}</div></div></div>
 <div class="row g12" style="flex:none">{principle("database", "Data tiap klien terpisah", "Data setiap klien disimpan terpisah dan tidak bisa saling melihat.")}
  {principle("key-round", "Akses hanya dengan izin", "Tim internal hanya bisa membuka data klien setelah disetujui Owner, dan hanya untuk waktu terbatas.")}
  {principle("video", "Video tetap di outlet", "Yang dikirim ke cloud hanya angka, bukan gambar atau video.")}</div>
 <div class="mocktag">MOCKUP · contoh data, bukan data asli</div></div></body></html>"""


PAGES = [("01-ringkasan", home), ("02-pantauan-live", live), ("03-analitik", analytics),
         ("04-perbandingan-outlet", hq), ("05-cctv-area", setup), ("06-notifikasi-laporan", alerts),
         ("07-tim-hak-akses", users), ("08-privasi-keamanan", privacy),
         ("09-superadmin-klien", sa_tenants), ("10-superadmin-perangkat", sa_fleet)]
