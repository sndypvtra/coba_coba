"""The mockup pages. Each function returns one complete HTML document.

One fictional tenant runs through every page, so the deck tells one story:
Kedai Pagi, a 12-outlet cafe chain, looked at on a Thursday afternoon in its
Senopati outlet (24 indoor seats). Every number is illustrative except where a
page says it comes from the dwell-time clip; the footer tag on every image says
so too.
"""

from __future__ import annotations

from pathlib import Path

from kit import (BLUE, GRID, INK, INK2, MUTED, ORANGE, ORDINAL, AXIS, SURF, RAMP, PULSE, basis, chip, columns, data_uri,
                 heatmap, ic, kpi, line_chart, page, scale_bar, smooth, spark, toggle, esc)

ROOT = Path(__file__).resolve().parents[2]
CLIP_STILL = ROOT / "projects/05_cafe_dwell_time/docs/scene5-dwell.jpg"
RAW_FRAME = Path(__file__).resolve().parents[1] / ".mockup_cache" / "scene5_f149.jpg"


# Table occupancy so far today (hours, 24-hour clock). One source for the Gantt on the
# analytics page and for the share quoted on the home page, so the two cannot disagree.
NOW = 15.2
TABLES = [("T1", 2), ("T2", 2), ("T3", 4), ("T4", 4), ("T5", 4), ("T6", 2), ("T7", 4), ("T8", 2)]
SEGS = {
    "T1": [(8.4, 9.2), (9.4, 10.3), (10.5, 13.2), (13.4, 14.2), (14.5, 15.2)],
    "T2": [(8.8, 9.5), (9.7, 10.6), (10.9, 11.8), (12.1, 13.0), (13.3, 14.0), (14.4, 15.2)],
    "T3": [(9.0, 10.1), (10.3, 12.8), (13.0, 14.1)],
    "T4": [(8.2, 12.1), (12.3, 13.0), (13.2, 14.0)],
    "T5": [(9.5, 10.2), (10.4, 11.2), (11.5, 14.8)],
    "T6": [(10.0, 10.8), (11.0, 11.9), (12.1, 13.0), (13.2, 13.9), (14.1, 15.2)],
    "T7": [(11.2, 12.4), (12.6, 13.7), (14.0, 14.7)],
    "T8": [(8.5, 9.1), (11.8, 13.4), (13.8, 15.2)],
}
LONG_H = 2.0  # a stay this long counts as long-stay


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


def ensure_assets() -> tuple[Path, Path]:
    """The two stills: the annotated frame cropped to the video, and a raw frame of the same clip."""
    import cv2
    cache = RAW_FRAME.parent
    still = cache / "scene5_annotated_video.jpg"
    if not still.exists():
        im = cv2.imread(str(CLIP_STILL))
        cv2.imwrite(str(still), im[:, 236:], [cv2.IMWRITE_JPEG_QUALITY, 92])  # drop the engine's own side panel
    if not RAW_FRAME.exists():
        cap = cv2.VideoCapture(str(ROOT / "projects/05_cafe_dwell_time/input/cafe_scene5_30s.mp4"))
        cap.set(cv2.CAP_PROP_POS_FRAMES, 149)  # the frame the annotated still was taken from
        ok, fr = cap.read()
        cv2.imwrite(str(RAW_FRAME), fr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return still, RAW_FRAME


def btn(text: str, icon: str | None = None, kind: str = "") -> str:
    return f'<span class="btn {kind}">{ic(icon, 15) if icon else ""}{text}</span>'


def sel(k: str, v: str) -> str:
    return f'<span class="sel"><span class="k">{k}</span>{v}{ic("chevron-down", 14, color=MUTED)}</span>'


# =============================================================== 01 hari ini
def home() -> str:
    kpis = "".join([
        kpi("Masuk hari ini", "187", "orang", "+9%", "g", "vs Kamis lalu", "line", "door-open",
            [4, 9, 15, 24, 33, 52, 71, 96, 118, 142, 166, 187]),
        kpi("Okupansi sekarang", "29%", "7/24 kursi", "−63 poin", "n", "dari puncak 13.05", "det", "armchair",
            [4, 8, 17, 33, 50, 79, 92, 83, 67, 46, 33, 29]),
        kpi("Waktu tinggal median", "38", "mnt", "−7%", "n", "vs Kamis lalu", "trk", "timer",
            [41, 40, 44, 39, 37, 36, 35, 39, 41, 40, 37, 38]),
        kpi("Antrean sekarang", "1", "orang", "puncak 6", "n", "pukul 12.58", "det", "users",
            [0, 1, 1, 2, 3, 6, 4, 3, 2, 1, 1, 1]),
        kpi("Counter tak terjaga", "7", "mnt", "+4 mnt", "r", "vs rata-rata harian", "det", "triangle-alert",
            [0, 0, 0, 1, 0, 2, 4, 0, 0, 0, 0, 0]),
    ])

    today = [(8, 4), (8.5, 8), (9, 17), (9.5, 25), (10, 33), (10.5, 38), (11, 50), (11.5, 63), (12, 79),
             (12.5, 88), (13.08, 92), (13.5, 83), (14, 67), (14.5, 46), (15, 33), (15.2, 29)]
    avg = [(8, 6), (9, 15), (10, 29), (11, 46), (12, 71), (13, 80), (14, 63), (15, 41), (16, 38), (17, 48),
           (18, 62), (19, 70), (20, 57), (21, 34), (22, 14)]
    chart = line_chart(758, 322, today, avg, now=15.2, peak=(13.08, 92, "Puncak 92% · 13.05"), now_label="29%")

    def att(kind, icon, title, body, action, bas):
        return f"""<div class="item"><div class="ibox {kind}">{ic(icon, 16)}</div><div class="grow">
 <div class="b" style="font-size:13.5px">{title}</div><div class="ink2" style="margin:2px 0 8px">{body}</div>
 <div class="row sp"><span class="btn sm">{action}{ic('arrow-right', 13)}</span>{bas}</div></div></div>"""

    attention = (att("warn", "siren", "Counter kosong 3× saat ada antrean",
                     "12.50–13.35 · antrean 4–6 orang, total 7 mnt tanpa petugas di zona layanan.<br>"
                     "<b style='color:var(--ink)'>Usulan:</b> tambah 1 orang di counter 12.30–14.00.",
                     "Lihat kejadian", basis("det"))
                 + att("info", "armchair", f"{LONG_TABLES} meja dipakai lebih dari 2 jam",
                       f"Menahan {LONG_SHARE}% kursi-jam yang terpakai pada 11.00–15.00.",
                       "Lihat okupansi meja", basis("det"))
                 + att("crit", "wifi-off", "Kamera Teras offline sejak 09.42",
                       "Angka &ldquo;sekarang&rdquo; hanya mencakup ruang dalam; okupansi teras tidak terhitung.",
                       "Periksa kamera", chip("Perlu tindakan", "crit")))

    def zone(n, v, vmax, kind=""):
        pct = 100 * v / vmax
        return (f'<div class="row g10"><span class="sm ink2" style="width:104px">{n}</span>'
                f'<div class="meter grow {kind}"><i style="width:{pct:.0f}%"></i></div>'
                f'<span class="sm b tnum" style="width:46px;text-align:right">{v}/{vmax}</span></div>')

    bottom = f"""<div class="grid" style="grid-template-columns:1.1fr 1fr 1fr;gap:12px;height:122px;flex:none">
 <div class="card" style="padding:12px 16px"><div class="card-h" style="margin-bottom:8px"><h3>Zona sekarang</h3>{basis('det')}</div>
   <div class="col g8">{zone('Area duduk A', 4, 12)}{zone('Area duduk B', 2, 12)}{zone('Antre', 1, 6)}</div></div>
 <div class="card" style="padding:12px 16px"><div class="card-h" style="margin-bottom:6px"><h3>Laporan WhatsApp 08.00</h3>{chip('Terkirim', 'good', 'check')}</div>
   <div class="ink2 sm" style="margin-bottom:8px">Ringkasan harian untuk 3 penerima</div>
   <div class="row g6 wrap">{chip('Rina · Owner', 'neutral')}{chip('Bagas · Admin', 'neutral')}{chip('Sari · Manager', 'neutral')}</div></div>
 <div class="card" style="padding:12px 16px"><div class="card-h" style="margin-bottom:8px"><h3>Kesehatan sistem</h3>{chip('1 perlu tindakan', 'warn', 'circle-alert')}</div>
   <div class="col g6 sm"><div class="row sp"><span class="ink2">Kamera online</span><span class="b">3 dari 4</span></div>
   <div class="row sp"><span class="ink2">Edge · jeda data</span><span class="b">3 dtk</span></div>
   <div class="row sp"><span class="ink2">Engine</span><span class="b">v2.4.0 · TensorRT FP16</span></div></div></div></div>"""

    body = f"""<div class="grid" style="grid-template-columns:repeat(5,1fr);gap:12px;flex:none">{kpis}</div>
<div class="row g12" style="flex:1;min-height:0;align-items:stretch">
 <div class="card" style="flex:0 0 61.5%">
   <div class="card-h"><div><h3>Okupansi hari ini vs rata-rata 4 Kamis terakhir</h3><div class="hint">Pelanggan di ruang dalam, % dari 24 kursi</div></div>{basis('det')}</div>
   <div class="lg" style="margin-bottom:4px"><span><i style="background:{BLUE}"></i>Hari ini</span><span><i style="background:{MUTED}"></i>Rata-rata 4 Kamis</span></div>
   {chart}</div>
 <div class="card grow" style="padding-bottom:6px"><div class="card-h"><h3>Perlu perhatian</h3>{chip('3 temuan', 'neutral')}</div>{attention}</div>
</div>{bottom}"""
    return page(plane="tenant", active="home", url="app.denyut.id/senopati/hari-ini",
                title="Selamat sore, Rina",
                sub="Kamis, 1 Okt 2026 · Senopati, Jakarta Selatan · buka 08.00–22.00 · data s.d. 15.12",
                actions=sel("", "Hari ini") + btn("Unduh PDF", "download"), body=body)


# ================================================================ 02 live ops
def _cust(x, y):
    return (f'<circle cx="{x}" cy="{y}" r="15" fill="{BLUE}" fill-opacity=".12"/>'
            f'<circle cx="{x}" cy="{y}" r="8" fill="{BLUE}" stroke="{SURF}" stroke-width="2.5"/>')


def _staff(x, y):
    return (f'<circle cx="{x}" cy="{y}" r="15" fill="{ORANGE}" fill-opacity=".14"/>'
            f'<rect x="{x - 7.5}" y="{y - 7.5}" width="15" height="15" rx="4.5" fill="{ORANGE}" stroke="{SURF}" stroke-width="2.5"/>')


def _table(x, y, w, h, occ):
    fill, stroke = ("#cde2fb", "#9ec5f4") if occ else (SURF, AXIS)
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


def floorplan(w: int = 706, h: int = 418) -> str:
    """Top-down schematic of the dining room: anonymous dots, no pixels. The people are the eight
    in the clip's last frame (seven customers, one server), placed to echo where they sit."""
    t = []
    t.append('<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             '<line x1="0" y1="0" x2="0" y2="7" stroke="#d03b3b" stroke-opacity=".5" stroke-width="2"/></pattern></defs>')
    t.append(f'<rect x="4" y="4" width="{w - 8}" height="{h - 8}" rx="14" fill="#f1f0ea" stroke="{AXIS}" stroke-width="1.5"/>')
    # entrance: a gap in the bottom wall
    t.append(f'<rect x="38" y="{h - 8}" width="76" height="8" fill="#fff"/>')
    t.append(f'<path d="M76 {h - 22} v-18 m-6 7 l6 -8 l6 8" fill="none" stroke="{MUTED}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    t.append(f'<text x="124" y="{h - 26}" font-size="11" font-weight="600" fill="{INK2}">Pintu masuk</text>')
    # mirror: excluded zone, as in the clip's config
    t.append('<path d="M40 5 H300 L296 22 L250 28 L120 26 L62 17 Z" fill="url(#hatch)"/>')
    t.append(f'<text x="46" y="46" font-size="10.5" font-weight="600" fill="#a42626">Cermin dinding · dikecualikan</text>')
    # service zone + counter + queue zone
    t.append('<rect x="414" y="8" width="282" height="62" rx="10" fill="#eb6834" fill-opacity=".10" stroke="#eb6834" stroke-opacity=".5" stroke-width="1.2"/>')
    t.append('<text x="424" y="25" font-size="10.5" font-weight="600" fill="#9a3a14">Zona layanan</text>')
    t.append('<rect x="424" y="42" width="262" height="20" rx="6" fill="#d7d5cc"/>')
    t.append('<text x="555" y="56" text-anchor="middle" font-size="9.5" font-weight="600" letter-spacing="1.5" fill="#6b6a64">COUNTER</text>')
    t.append('<rect x="424" y="78" width="262" height="72" rx="8" fill="#2a78d6" fill-opacity=".07" stroke="#2a78d6" stroke-opacity=".4" stroke-width="1.2"/>')
    t.append('<text x="434" y="95" font-size="10.5" font-weight="600" fill="#184f95">Zona antre</text>')
    # tables - the same T1..T8 as the occupancy timeline
    t.append('<text x="70" y="80" font-size="10.5" font-weight="600" fill="#184f95">Area duduk A</text>')
    spec = [("T1", 70, 96, 86, 46, True), ("T2", 176, 96, 86, 46, True), ("T3", 70, 176, 86, 46, False),
            ("T4", 176, 176, 86, 46, False), ("T5", 296, 150, 64, 64, False), ("T6", 296, 258, 64, 64, True),
            ("T7", 190, 306, 64, 64, False), ("T8", 560, 190, 86, 46, True)]
    for name, x, y, tw, th, occ in spec:
        t.append(_table(x, y, tw, th, occ))
        t.append(f'<text x="{x + tw - 8}" y="{y + th - 8}" text-anchor="end" font-size="10" font-weight="600" fill="{"#184f95" if occ else MUTED}">{name}</text>')
    t.append('<text x="296" y="244" font-size="10.5" font-weight="600" fill="#184f95">Area duduk B</text>')
    # people
    for x, y in [(94, 112), (132, 112), (200, 112), (238, 112), (328, 342), (528, 118), (662, 213)]:
        t.append(_cust(x, y))
    t.append(_staff(555, 26))
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(t)}</svg>'


def live() -> str:
    still, _ = ensure_assets()

    def tile(label, body, bas):
        return (f'<div class="card" style="padding:11px 15px;gap:7px"><div class="row sp"><span class="sm ink2 b">{label}</span>{bas}</div>'
                f'{body}</div>')

    big = 'style="font-size:28px;font-weight:600;letter-spacing:-.02em;line-height:1"'
    strip = "".join([
        tile("Di ruangan", f'<div class="row g8" style="align-items:baseline"><span {big}>8</span><span class="sm ink2">7 pelanggan · 1 petugas</span></div>', basis("det")),
        tile("Kapasitas terpakai", f'<div class="row g10"><span {big}>29%</span><div class="grow"><div class="meter"><i style="width:29%"></i></div><div class="xs muted" style="margin-top:4px">7 dari 24 kursi</div></div></div>', basis("det")),
        tile("Antrean", f'<div class="row g8" style="align-items:baseline"><span {big}>1</span><span class="sm ink2">orang · tunggu ±1 mnt</span></div>', basis("det")),
        tile("Counter", f'<div class="row g10"><span {big}>{chip("Terjaga", "good", "circle-check")}</span><span class="sm ink2">1 petugas di zona layanan</span></div>', basis("det")),
    ])

    def ztile(name, val, pct, extra=""):
        return (f'<div style="border:1px solid var(--border);border-radius:10px;padding:8px 11px;background:#fff"><div class="row sp"><span class="sm b">{name}</span>'
                f'<span class="b tnum sm">{val}</span></div><div class="meter" style="margin-top:7px"><i style="width:{pct}%"></i></div>{extra}</div>')

    zones = (ztile("Area duduk A", "4 / 12", 33) + ztile("Area duduk B", "2 / 12", 17) + ztile("Antre", "1 · ±1 mnt", 17)
             + '<div style="border:1px solid var(--border);border-radius:10px;padding:8px 11px;background:#fff"><div class="row sp"><span class="sm b">Zona layanan</span>'
               f'{chip("Terjaga", "good")}</div><div class="xs muted" style="margin-top:9px">1 petugas · terakhir kosong 13.34</div></div>')

    legend = (f'<div class="lg" style="margin:8px 0 10px"><span><i class="sq" style="background:{BLUE};border-radius:50%"></i>Pelanggan</span>'
              f'<span><i class="sq" style="background:{ORANGE}"></i>Petugas</span>'
              '<span><i class="sq" style="background:#cde2fb"></i>Meja terisi</span>'
              '<span><i class="sq" style="background:repeating-linear-gradient(45deg,#e9aaaa 0 2px,#fcfcfb 2px 5px)"></i>Zona dikecualikan</span></div>')

    left = f"""<div class="card" style="flex:0 0 58%"><div class="card-h"><div><h3>Denah ruang dalam — langsung</h3>
 <div class="hint">Titik anonim dari hasil deteksi · tanpa video, tanpa wajah</div></div>{chip("Diperbarui 2 dtk lalu", "neutral", "refresh-cw")}</div>
 {floorplan()}{legend}<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:10px">{zones}</div></div>"""

    video = f"""<div class="card" style="flex:none;height:372px"><div class="card-h"><div><h3>Video on-site <span class="muted" style="font-weight:400">· opsional</span></h3></div>
 {chip("LAN / VPN · tidak lewat cloud", "neutral", "lock")}</div>
 <div style="position:relative;height:270px;border-radius:9px;overflow:hidden;background:#111">
  <img src="{data_uri(still)}" style="width:100%;height:100%;object-fit:cover;object-position:50% 40%">
  <span class="chip" style="position:absolute;left:10px;top:10px;background:rgba(11,11,11,.72);color:#fff">{ic("video", 12, 2.2)}Kamera 1 · Ruang dalam</span>
  <span class="chip" style="position:absolute;right:10px;top:10px;background:rgba(11,11,11,.72);color:#fff"><i class="dot" style="background:#ff6b6b;width:7px;height:7px"></i>LIVE</span></div>
 <div class="xs muted" style="margin-top:8px">Keluaran nyata engine pada klip uji. Video dibuka langsung dari perangkat di lokasi, tidak pernah melewati cloud.</div></div>"""

    def al(kind, icon, title, sub, time):
        return (f'<div class="row g10" style="padding:5px 0;border-bottom:1px solid #eceae4"><div class="ibox {kind}" style="width:26px;height:26px;border-radius:8px">{ic(icon, 14)}</div>'
                f'<div class="grow"><div class="b" style="font-size:12.5px">{title}</div><div class="xs muted">{sub}</div></div><span class="xs muted tnum">{time}</span></div>')

    alerts = f"""<div class="card grow" style="padding-bottom:4px"><div class="card-h" style="margin-bottom:4px"><h3>Kejadian terbaru</h3>{chip("Hari ini", "neutral")}</div>
 {al("info", "gauge", "Okupansi turun ke 29%", "di bawah ambang jam sibuk", "15.09")}
 {al("good", "circle-check", "Antrean kembali 2 orang atau kurang", "setelah 25 mnt di atas 3 orang", "14.58")}
 {al("warn", "siren", "Counter tak terjaga 4 mnt · antrean 5 orang", "WhatsApp terkirim ke Manager", "13.31")}
 {al("crit", "wifi-off", "Kamera Teras offline", "tiket support dibuat otomatis", "09.42")}</div>"""

    body = f"""<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:none">{strip}</div>
<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}<div class="col g12 grow">{video}{alerts}</div></div>"""
    return page(plane="tenant", active="live", url="app.denyut.id/senopati/live",
                title="Live Ops", sub="Senopati · ruang dalam · Kamera 1–2 · untuk supervisor lantai",
                actions='<span class="livepill"><i></i>LIVE</span>' + btn("Mode TV", "tv-minimal") + sel("Kamera", "Semua"), body=body)


# ============================================================== 03 analytics
def _heat_data():
    import math
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
    x0, xr = 78, w - 34
    hr = (xr - x0) / 8  # px per hour, 08.00 - 16.00
    X = lambda t: x0 + (t - 8) * hr
    rh, top = 27, 20
    out = []
    for k in range(9):
        out.append(f'<line x1="{X(8 + k):.1f}" x2="{X(8 + k):.1f}" y1="{top - 4}" y2="{top + rh * len(TABLES)}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{X(8 + k):.1f}" y="11" text-anchor="middle" font-size="10.5" fill="{MUTED}" style="font-variant-numeric:tabular-nums">{8 + k:02d}.00</text>')
    for i, (name, seats) in enumerate(TABLES):
        y = top + i * rh
        out.append(f'<text x="0" y="{y + 18}" font-size="12" font-weight="600" fill="{INK}">{name}</text>'
                   f'<text x="26" y="{y + 18}" font-size="11" fill="{MUTED}">{seats} kursi</text>')
        for a, b in SEGS[name]:
            long_ = (b - a) >= LONG_H
            bx, bw = X(a), X(b) - X(a)
            out.append(f'<rect x="{bx:.1f}" y="{y + 6}" width="{bw:.1f}" height="15" rx="4" fill="{ORANGE if long_ else BLUE}"/>')
            if long_:
                d = b - a
                lab = f"{int(d)}j {round((d - int(d)) * 60):02d}m"
                out.append(f'<text x="{bx + bw / 2:.1f}" y="{y + 17.5}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#fff">{lab}</text>')
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
    peak_txt = f"Puncak: {rows[pi]} {8 + pj:02d}.00 · {round(data[pi][pj])}%"

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

    staff = f"""<div class="card grow"><div class="card-h"><div><h3>Beban vs staf — hari kerja rata-rata</h3><div class="hint">Pelanggan rata-rata per jam</div></div>{basis("det")}</div>
 {cols_svg}<div class="row xs muted" style="margin:2px 0 3px"><span style="width:76px">Terjadwal</span></div>{rowcells([2] * 15, lambda i: False)}
 <div class="row xs muted" style="margin:6px 0 3px"><span>Disarankan</span><span class="chip info" style="margin-left:8px;height:18px">+1 pada {len(hi)} jam</span></div>{rowcells(rec, lambda i: i in hi)}</div>"""

    heatcard = f"""<div class="card" style="flex:0 0 61.5%"><div class="card-h"><div><h3>Okupansi per jam, 7 hari terakhir</h3><div class="hint">% dari 24 kursi · rata-rata per jam</div></div>{basis("det")}</div>
 {heat}<div class="row sp" style="margin-top:8px"><div class="row g8 xs muted"><span>Sepi</span>{scale_bar(140)}<span>Penuh</span></div><span class="xs b">{peak_txt}</span></div></div>"""

    gcard = f"""<div class="card" style="flex:0 0 61.5%"><div class="card-h"><div><h3>Okupansi meja — hari ini</h3><div class="hint">Berapa lama tiap meja terpakai tanpa jeda</div></div>{basis("det")}</div>
 {gantt(752, 252)}<div class="row sp" style="margin-top:6px"><div class="lg"><span><i class="sq" style="background:{BLUE}"></i>Singkat (di bawah 2 jam)</span><span><i class="sq" style="background:{ORANGE}"></i>Long-stay (2 jam atau lebih)</span></div>
 <span class="xs b">{LONG_TABLES} meja long-stay menahan {LONG_SHARE}% kursi-jam pada 11.00–15.00</span></div></div>"""

    stages = [("Masuk lewat pintu", 187, ""), ("Ke area antre", 151, "median tunggu 2 mnt"), ("Dilayani di counter", 140, ""), ("Duduk di meja", 96, "44 bawa pulang")]
    frows = ""
    for (n, v, note), col in zip(stages, ORDINAL):
        bw = 186 * v / 187
        frows += (f'<div class="row g10" style="height:44px"><div style="width:138px;flex:none"><div class="b" style="font-size:12.5px">{n}</div><div class="xs muted">{note or "&nbsp;"}</div></div>'
                  f'<svg width="186" height="24" viewBox="0 0 186 24" style="flex:none"><rect x="0" y="4" width="{bw:.1f}" height="16" rx="4" fill="{col}"/></svg>'
                  f'<div class="b tnum" style="width:92px;flex:none;white-space:nowrap">{v} <span class="muted" style="font-weight:500">· {round(100 * v / 187)}%</span></div></div>')
    funnel = f"""<div class="card grow"><div class="card-h"><div><h3>Alur pelanggan</h3><div class="hint">Perpindahan antar zona hari ini</div></div>{basis("trk")}</div>
 <div style="margin-top:2px">{frows}</div>
 <div class="row sp" style="margin-top:6px;padding:9px 12px;border-radius:10px;background:var(--warn-t)"><span class="sm" style="color:var(--warn-x)"><b>11 orang (7%)</b> meninggalkan antrean tanpa dilayani</span>{chip("Tinjau", "warn", "arrow-right")}</div>
 <div class="row g8" style="margin-top:auto;padding-top:8px">{ic("info", 14, color=MUTED)}<span class="xs muted">Berbasis tracking: tiap angka tampil bersama lencana keandalannya.</span></div></div>"""

    body = f'<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{heatcard}{staff}</div><div class="row g12" style="flex:1;min-height:0;align-items:stretch">{gcard}{funnel}</div>'
    return page(plane="tenant", active="analytics", url="app.denyut.id/senopati/analytics",
                title="Analytics", sub="Senopati · 24–30 Sep 2026 (7 hari) · dibandingkan dengan 7 hari sebelumnya",
                actions=sel("Periode", "7 hari terakhir") + sel("Bandingkan", "7 hari sebelumnya") + sel("Zona", "Semua") + btn("Ekspor", "download"), body=body)


# =============================================================== 04 banding
def hq() -> str:
    import math
    rows = [  # outlet, kota, masuk/hari, delta, okupansi puncak, tunggu median, counter kosong mnt/hari, skor
        ("Seminyak", "Bali", 289, "+14%", 98, "1:20", 3, 91),
        ("PIK", "Jakarta Utara", 301, "+11%", 94, "1:35", 4, 88),
        ("Dago", "Bandung", 242, "+8%", 89, "1:48", 5, 84),
        ("Kemang", "Jakarta Selatan", 268, "+3%", 91, "1:52", 6, 82),
        ("Senopati", "Jakarta Selatan", 214, "+6%", 92, "2:05", 7, 79),
        ("Tunjungan", "Surabaya", 223, "+2%", 84, "2:10", 8, 77),
        ("Malioboro", "Yogyakarta", 205, "+1%", 81, "2:18", 9, 74),
        ("Depok", "Depok", 171, "−2%", 73, "2:36", 10, 71),
        ("BSD City", "Tangerang Selatan", 187, "−4%", 76, "2:30", 22, 69),
        ("Braga", "Bandung", 156, "−9%", 71, "3:25", 12, 58),
    ]

    def status(sc):
        return chip("Prima", "good", "circle-check") if sc >= 80 else (chip("Perhatikan", "warn", "circle-alert") if sc >= 65 else chip("Kritis", "crit", "siren"))

    trs = ""
    for i, (n, k, m, d, op, tw, ck, sc) in enumerate(rows, 1):
        series = [60 + 30 * math.sin(i * 1.3 + j * 0.8) + (sc - 70) * 0.8 + j * (1.5 if d.startswith("+") else -1.5) for j in range(12)]
        dcol = "var(--good-x)" if d.startswith("+") else "var(--crit-x)"
        trs += (f'<tr><td class="muted">{i}</td><td><div class="b">{n}</div><div class="xs muted">{k}</div></td>'
                f'<td class="n"><span class="b">{m}</span> <span class="xs b" style="color:{dcol}">{d}</span></td>'
                f'<td class="n">{op}%</td><td class="n">{tw}</td><td class="n">{ck} mnt</td>'
                f'<td><div class="row g8"><div class="meter" style="width:70px"><i style="width:{sc}%"></i></div><span class="b tnum">{sc}</span></div></td>'
                f'<td>{spark(series, 66, 24)}</td><td>{status(sc)}</td></tr>')

    table = f"""<div class="card" style="flex:0 0 68%"><div class="card-h"><div><h3>Peringkat outlet — 30 hari</h3>
 <div class="hint">Skor 0–100 dari okupansi, waktu tunggu dan counter terjaga, dinormalisasi per kursi dan jam buka</div></div>{basis("trk")}</div>
 <table style="table-layout:fixed"><colgroup><col style="width:30px"><col style="width:150px"><col style="width:108px"><col style="width:76px"><col style="width:72px"><col style="width:88px"><col style="width:128px"><col style="width:86px"><col></colgroup>
 <thead><tr><th></th><th>Outlet</th><th class="n">Masuk/hari</th><th class="n">Puncak</th><th class="n">Tunggu</th><th class="n">Kosong/hari</th><th>Skor</th><th>Tren</th><th>Status</th></tr></thead>
 <tbody>{trs}</tbody></table>
 <div class="row sp" style="margin-top:auto;padding-top:8px"><span class="xs muted">10 dari 12 outlet · Puncak = okupansi puncak · Tunggu = median menit:detik · Kosong = menit counter tak terjaga</span><span class="btn sm">Lihat semua outlet{ic("arrow-right", 13)}</span></div></div>"""

    def an(kind, icon, title, body_):
        return (f'<div class="item"><div class="ibox {kind}">{ic(icon, 16)}</div><div class="grow"><div class="b" style="font-size:13.5px">{title}</div>'
                f'<div class="ink2" style="margin-top:2px">{body_}</div></div></div>')

    anomalies = f"""<div class="card grow"><div class="card-h"><h3>Anomali minggu ini</h3>{chip("3 outlet", "neutral")}</div>
 {an("crit", "trending-up", "Braga — waktu tunggu naik 38%", "Median 3:25 vs 2:29 minggu lalu, di 4 dari 7 hari. Counter kosong 12 mnt/hari.")}
 {an("warn", "siren", "BSD City — counter kosong 22 mnt/hari", "Tiga kali rata-rata jaringan (7 mnt). Terpusat di 12.00–14.00.")}
 {an("info", "armchair", "Seminyak — okupansi puncak 98%", "Penuh 41 mnt di akhir pekan. Pertimbangkan menambah kursi atau jam staf.")}
 <div style="margin-top:auto"><div class="row sp" style="margin-top:6px"><span class="sm b">Sebaran skor, 12 outlet</span><span class="xs muted">terang = prima (80 ke atas)</span></div>
 {columns(364, 104, [91, 88, 86, 84, 82, 79, 77, 74, 71, 69, 66, 58], [str(i) for i in range(1, 13)], 100, set(range(5, 12)), {11: "58"})}</div>
 <div class="row g8" style="padding-top:2px">{ic("info", 14, color=MUTED)}<span class="xs muted">Dinormalisasi agar outlet kecil dan besar bisa dibandingkan adil.</span></div></div>"""

    def kp(label, value, sub, ic_):
        return (f'<div class="card" style="padding:12px 15px;gap:5px"><div class="row sp"><span class="sm ink2 b">{label}</span>{ic(ic_, 15, color=MUTED)}</div>'
                f'<div class="row g8" style="align-items:baseline"><span style="font-size:27px;font-weight:600;letter-spacing:-.02em;line-height:1.1">{value}</span><span class="sm ink2">{sub}</span></div></div>')

    kpis = (kp("Masuk 30 hari", "79.680", "+5%", "door-open") + kp("Okupansi puncak rata-rata", "85%", "jaringan", "gauge")
            + kp("Tunggu median", "2:08", "menit:detik", "timer") + kp("Outlet dengan anomali", "3", "dari 12", "triangle-alert"))
    body = f'<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:none">{kpis}</div><div class="row g12" style="flex:1;min-height:0;align-items:stretch">{table}{anomalies}</div>'
    return page(plane="tenant", active="hq", url="app.denyut.id/jaringan/banding-outlet",
                title="Banding Outlet", sub="Kedai Pagi · 12 outlet · 1–30 Sep 2026 · hanya untuk Owner dan Admin pusat",
                actions=sel("Periode", "30 hari") + sel("Kota", "Semua") + btn("Ekspor", "download"), body=body)


def snapshots() -> list[str]:
    """Five frames of the same clip as the validation snapshots (the first is the one being edited)."""
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


# ================================================================ 05 kamera & zona
def setup() -> str:
    _, raw = ensure_assets()
    mirror = [(50, 0), (745, 0), (735, 185), (620, 225), (420, 252), (250, 246), (165, 196), (50, 110)]
    staff = [(1050, 0), (1920, 0), (1920, 120), (1650, 200), (1500, 195), (1080, 150)]
    draft = [(1010, 340), (1700, 340), (1800, 650), (930, 650)]   # a queue zone being drawn

    def poly(pts, col, dashed=False, handles=True):
        d = " ".join(f"{x},{y}" for x, y in pts)
        dash = ' stroke-dasharray="18 12"' if dashed else ""
        alpha = ".14" if dashed else ".24"
        o = (f'<polygon points="{d}" fill="{col}" fill-opacity="{alpha}" stroke="{col}" stroke-width="5" '
             f'stroke-linejoin="round"{dash}/>')
        if handles:
            o += "".join(f'<rect x="{x - 11}" y="{y - 11}" width="22" height="22" rx="5" fill="#fff" stroke="{col}" stroke-width="4"/>' for x, y in pts)
        return o

    overlay = (f'<svg viewBox="0 0 1920 1080" preserveAspectRatio="none" style="position:absolute;inset:0;width:100%;height:100%">'
               f'{poly(mirror, "#d03b3b")}{poly(staff, "#eb6834")}{poly(draft, "#2a78d6", dashed=True)}</svg>')

    def lab(left, top, text, fg, border):
        return (f'<span class="chip" style="position:absolute;left:{left}%;top:{top}%;background:#fff;color:{fg};border:1px solid {border};'
                f'box-shadow:0 2px 6px rgba(0,0,0,.18)">{text}</span>')

    labels = (lab(4.5, 7, "Cermin dinding · Dikecualikan", "#a42626", "#e9b3b3")
              + lab(55, 3.2, "Area pelayan · Layanan", "#9a3a14", "#f3c5ad")
              + lab(54, 36, "Zona antre · sedang digambar", "#184f95", "#bcd3f3")
              + f'<span style="position:absolute;left:47.6%;top:58.5%;color:#0b0b0b;filter:drop-shadow(0 1px 2px rgba(255,255,255,.9))">{ic("mouse-pointer-2", 22, 1.8)}</span>'
              + '<span class="chip" style="position:absolute;left:51%;top:62%;background:rgba(11,11,11,.78);color:#fff">Klik titik pertama untuk menutup zona</span>')

    tools = (f'<span class="tool">{ic("mouse-pointer-2", 17)}</span><span class="tool on">{ic("pentagon", 17)}</span>'
             f'<span class="tool">{ic("minus", 17)}</span><span class="tool">{ic("trash-2", 17)}</span>')
    snaps = snapshots()
    labs = [("09.12", True), ("11.40", False), ("13.05", False), ("15.20", False), ("18.10", False)]
    strip = "".join(
        f'<div style="position:relative;flex:1;height:64px;border-radius:8px;overflow:hidden;border:2px solid {"#2a78d6" if on else "transparent"}">'
        f'<img src="{u}" style="width:100%;height:100%;object-fit:cover;object-position:50% 40%;display:block{";opacity:.55" if not on else ""}">'
        f'<span class="chip" style="position:absolute;left:5px;bottom:5px;height:18px;font-size:10.5px;background:rgba(11,11,11,.72);color:#fff">{t}{" ✓" if on else ""}</span></div>'
        for u, (t, on) in zip(snaps, labs))
    editor = f"""<div class="card grow" style="padding:12px 14px">
 <div class="row sp" style="margin-bottom:10px"><div class="row g4">{tools}<span style="width:1px;height:20px;background:var(--grid);margin:0 8px"></span>
   <span class="sm ink2">Poligon: klik untuk menambah titik</span></div>
   <div class="row g8">{chip("Snapshot 09.12", "neutral", "image")}<span class="btn sm">{ic("refresh-cw", 13)}Segarkan</span></div></div>
 <div style="position:relative;border-radius:9px;overflow:hidden;background:#111;aspect-ratio:16/9;width:100%">
  <img src="{data_uri(raw)}" style="width:100%;height:100%;display:block">{overlay}{labels}</div>
 <div class="row sp" style="margin:9px 0 6px"><span class="xs muted">Snapshot untuk validasi · frame ini dari klip uji dwell time</span>
   <span class="xs muted">1920×1080 · 5 fps</span></div><div class="row g8">{strip}</div></div>"""

    def zrow(col, name, kind, sub, dashed=False):
        sw = f'<span style="width:14px;height:14px;border-radius:4px;background:{col}33;border:2px {"dashed" if dashed else "solid"} {col};flex:none;margin-top:2px"></span>'
        return (f'<div class="item" style="padding:9px 0">{sw}<div class="grow"><div class="row sp"><span class="b" style="font-size:13px">{name}</span>{kind}</div>'
                f'<div class="xs muted" style="margin-top:2px">{sub}</div></div></div>')

    cam = f"""<div class="card" style="flex:none">{cardh("Kamera 1 · Ruang dalam", "", chip("Terhubung", "good", "circle-check"))}
 <div class="col g6 sm"><div class="row sp"><span class="ink2">Alamat</span><span class="b tnum">rtsp://•••@192.168.1.21</span></div>
 <div class="row sp"><span class="ink2">Video</span><span class="b">H.264 · 1920×1080</span></div>
 <div class="row sp"><span class="ink2">Sampling</span><span class="b">5 fps</span></div></div></div>"""
    zones = f"""<div class="card grow" style="padding-bottom:6px">{cardh("Zona", "", chip("3", "neutral"))}
 {zrow("#eb6834", "Area pelayan", chip("Layanan", "orange"), "6 titik · dihitung sebagai layanan, bukan kunjungan")}
 {zrow("#d03b3b", "Cermin dinding", chip("Dikecualikan", "crit"), "8 titik · pantulan akan terhitung dua kali")}
 {zrow("#2a78d6", "Zona antre", chip("Draf", "info"), "menggambar… · waktu tunggu dihitung dari sini", True)}
 {zrow("#898781", "Ruang utama", chip("Hitung", "neutral"), "seluruh frame · semua orang dihitung kecuali zona di atas")}</div>"""
    valid = f"""<div class="card" style="flex:none">{cardh("Validasi cepat", "Cocokkan hitungan sistem dengan mata Anda")}
 <div class="row g10"><div class="grow"><div class="xs muted" style="margin-bottom:4px">Hitung manual</div><div class="field"><span class="b">8</span><span class="xs muted">orang</span></div></div>
 <div class="grow"><div class="xs muted" style="margin-bottom:4px">Hasil sistem</div><div class="field" style="background:var(--blue-t);border-color:#bcd3f3"><span class="b">8</span><span class="xs" style="color:var(--blue-d)">7 + 1 petugas</span></div></div></div>
 <div class="row sp" style="margin:10px 0 8px">{chip("Cocok", "good", "circle-check")}<span class="xs muted">Snapshot 1 dari 5</span></div>
 <div class="meter"><i style="width:20%"></i></div>
 <div class="xs muted" style="margin-top:8px">Selisih rata-rata dari 5 snapshot tampil di laporan keandalan kamera.</div></div>"""

    body = f"""{steps(["Hubungkan kamera", "Gambar zona", "Validasi hitungan", "Aktifkan"], 2)}
<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{editor}<div class="col g12" style="flex:0 0 346px">{cam}{zones}{valid}</div></div>"""
    return page(plane="tenant", active="setup", url="app.denyut.id/senopati/kamera/1/zona",
                title="Kamera &amp; Zona", sub="Senopati · pasang kamera baru dalam beberapa menit, tanpa teknisi khusus",
                actions=btn("Simpan draf") + btn("Lanjut ke validasi", "arrow-right", "pri"), body=body)


# ================================================================ 06 alert & laporan
def alerts() -> str:
    wa = ic("whatsapp-icon", 14, prefix="logos")

    def ch(kind):
        m = {"wa": f'<span class="chip neutral">{wa}WhatsApp</span>', "push": f'<span class="chip neutral">{ic("bell", 12, 2)}Push</span>',
             "mail": f'<span class="chip neutral">{ic("mail", 12, 2)}Email</span>', "rep": f'<span class="chip neutral">{ic("file-text", 12, 2)}Ringkasan harian</span>'}
        return m[kind]

    def rule(title, sub, chans, last):
        return (f'<div class="row g12" style="padding:10px 0;border-bottom:1px solid #eceae4">{toggle(True)}'
                f'<div class="grow"><div style="font-size:13.5px">{title}</div><div class="xs muted" style="margin-top:2px">{sub}</div></div>'
                f'<div class="row g6" style="flex:none">{"".join(ch(c) for c in chans)}</div>'
                f'<div class="xs muted tnum" style="width:96px;text-align:right;flex:none">{last}</div></div>')

    rules = f"""<div class="card" style="flex:none;padding-bottom:4px">{cardh("Aturan aktif", "Berlaku di jam buka · semua berbasis deteksi, jadi andal", f'{chip("5 aturan", "neutral")}')}
 {rule("<b>Counter tak terjaga</b> 3 mnt atau lebih <b>dan</b> antrean 3 orang atau lebih", "Ke: Manager Senopati", ["wa"], "terakhir 13.31")}
 {rule("<b>Okupansi</b> 90% atau lebih selama 15 mnt", "Ke: Manager Senopati", ["wa", "push"], "terakhir 13.05")}
 {rule("<b>Antrean</b> 6 orang atau lebih", "Ke: Supervisor lantai", ["push"], "terakhir 12.58")}
 {rule("<b>Kamera offline</b> 5 mnt atau lebih", "Ke: Admin · tiket dukungan dibuat otomatis", ["mail"], "terakhir 09.42")}
 {rule("<b>Meja dipakai</b> 3 jam atau lebih", "Tanpa notifikasi langsung, masuk ringkasan harian", ["rep"], "&mdash;")}</div>"""

    def inl(t, strong=False):
        return f'<span class="sel" style="height:28px;{"background:var(--blue-t);border-color:#bcd3f3;color:var(--blue-d);font-weight:600" if strong else ""}">{t}</span>'

    builder = f"""<div class="card" style="flex:none">{cardh("Aturan baru", "Susun dengan kalimat, tanpa kode", chip("Deteksi · Andal", "good", "circle-check"))}
 <div class="row g8 wrap" style="row-gap:8px"><span class="b xs muted" style="letter-spacing:.06em">JIKA</span>{inl("Zona layanan")}{inl("kosong")}<span class="sm ink2">selama</span>{inl("3 mnt")}
 <span class="b xs muted" style="letter-spacing:.06em">DAN</span>{inl("Antrean")}{inl("lebih dari 2 orang")}
 <span style="width:100%;height:0"></span><span class="b xs muted" style="letter-spacing:.06em">MAKA KIRIM KE</span>{inl("Manager")}<span class="sm ink2">lewat</span>{inl(wa + " WhatsApp")}
 <span class="grow"></span><span class="btn pri">Simpan aturan</span></div></div>"""

    def sch(name, when, on=True):
        return f'<div class="row g10" style="padding:7px 0;border-bottom:1px solid #eceae4">{toggle(on)}<div class="grow"><div class="b sm">{name}</div></div><span class="sm ink2">{when}</span></div>'

    schedule = f"""<div class="card grow" style="padding-bottom:4px">{cardh("Laporan terjadwal", "Penerima: Rina (Owner), Bagas (Admin), Sari (Manager)")}
 {sch("Harian", "setiap hari 08.00")}{sch("Mingguan", "Senin 07.00")}{sch("Bulanan", "tanggal 1, 07.00")}</div>"""

    msg1 = ("<b>Laporan harian · Kedai Pagi Senopati</b><br>Rabu, 30 Sep 2026<br><br>"
            "• Masuk: <b>241 orang</b> (+3% vs Rabu lalu)<br>• Puncak okupansi: <b>88%</b> pukul 12.40<br>"
            "• Counter tak terjaga: <b>5 mnt</b><br>• Waktu tinggal median: <b>41 mnt</b> <i>(tracking · sedang)</i><br><br>"
            "Catatan: 2 meja dipakai lebih dari 3 jam.<br><span style='color:#2a78d6'>app.denyut.id/senopati</span>")
    msg2 = ("<b>Counter tak terjaga</b> 4 mnt, antrean 5 orang.<br>Usulan: panggil 1 orang ke counter.<br>"
            "<span style='color:#2a78d6'>app.denyut.id/senopati/live</span>")
    phone = f"""<div style="flex:0 0 330px;display:flex;justify-content:center">
 <div style="width:318px;height:100%;max-height:696px;border-radius:40px;background:#161615;padding:9px;box-shadow:0 18px 40px rgba(11,11,11,.28)">
  <div style="width:100%;height:100%;border-radius:32px;background:#ece5dd;overflow:hidden;display:flex;flex-direction:column">
   <div style="height:26px;display:flex;align-items:center;justify-content:space-between;padding:0 18px;font-size:11px;font-weight:600;background:#0f5a4c;color:#fff"><span>15.12</span><span>5G ▮▮▮</span></div>
   <div class="row g8" style="padding:9px 12px;background:#0f5a4c;color:#fff">{ic("chevron-left", 18, 2.2)}<span class="logo" style="width:30px;height:30px;border-radius:50%">{PULSE}</span>
    <div><div style="font-size:13px;font-weight:600;line-height:1.2">Denyut · Senopati</div><div style="font-size:10.5px;opacity:.8">akun bisnis</div></div></div>
   <div style="flex:1;padding:12px 10px;display:flex;flex-direction:column;gap:8px;overflow:hidden">
    <div class="center" style="align-self:center;font-size:10.5px;background:#e1f2fb;color:#52514e;border-radius:6px;padding:3px 9px">HARI INI</div>
    <div style="align-self:flex-start;max-width:92%;background:#fff;border-radius:2px 10px 10px 10px;padding:8px 10px 6px;font-size:12px;line-height:1.45;box-shadow:0 1px 1px rgba(0,0,0,.12)">{msg1}<div class="right" style="font-size:10px;color:#898781;margin-top:3px">08.00</div></div>
    <div style="align-self:flex-start;max-width:92%;background:#fff;border-radius:2px 10px 10px 10px;padding:8px 10px 6px;font-size:12px;line-height:1.45;box-shadow:0 1px 1px rgba(0,0,0,.12)">{msg2}<div class="right" style="font-size:10px;color:#898781;margin-top:3px">13.31</div></div>
   </div>
   <div class="row g8" style="padding:8px 10px;background:#f4f0ea"><div style="flex:1;height:30px;border-radius:15px;background:#fff;font-size:11.5px;color:#898781;display:flex;align-items:center;padding:0 12px">Pesan ini hanya untuk dibaca</div></div>
  </div></div></div>"""

    body = f'<div class="row g14" style="flex:1;min-height:0;align-items:stretch"><div class="col g12 grow">{rules}{builder}{schedule}</div>{phone}</div>'
    return page(plane="tenant", active="alert", url="app.denyut.id/senopati/alert",
                title="Alert &amp; Laporan", sub="Senopati · pemilik membaca WhatsApp, bukan dashboard. Kabar sampai ke sana.",
                actions=btn("Riwayat kejadian", "history") + btn("Aturan baru", "plus", "pri"), body=body)


# ================================================================ 07 pengguna & role
def users() -> str:
    def u(init, name, mail, role, scope, tfa, last, kind="info"):
        t = (f'<span class="row g4" style="color:var(--good-x)">{ic("shield-check", 15, 2)}<span class="xs b">aktif</span></span>' if tfa
             else f'<span class="row g4" style="color:var(--warn-x)">{ic("triangle-alert", 15, 2)}<span class="xs b">belum</span></span>')
        return (f'<tr><td><div class="row g10"><div class="av" style="width:28px;height:28px;font-size:10.5px">{init}</div><div><div class="b">{name}</div><div class="xs muted">{mail}</div></div></div></td>'
                f'<td>{chip(role, kind)}</td><td class="ink2">{scope}</td><td>{t}</td><td class="muted">{last}</td></tr>')

    rows = (u("RA", "Rina Adiningsih", "rina@kedaipagi.id", "Owner", "Semua outlet", True, "2 mnt lalu", "orange")
            + u("BP", "Bagas Pratama", "bagas@kedaipagi.id", "Admin", "Semua outlet", True, "1 jam lalu")
            + u("SW", "Sari Wulandari", "sari@kedaipagi.id", "Manager", "Senopati", True, "12 mnt lalu")
            + u("DH", "Dimas Hartono", "dimas@kedaipagi.id", "Manager", "Kemang", False, "kemarin")
            + u("PL", "Putri Lestari", "putri@kedaipagi.id", "Analyst", "Semua outlet · baca", True, "3 hari lalu")
            + u("TV", "TV ruang staf", "perangkat · mode TV", "Viewer", "Senopati", True, "online", "neutral")
            + u("TC", "Teknisi CCTV (mitra)", "mitra@cctvjaya.id", "Installer", "Senopati · s.d. 3 Okt", True, "2 hari lalu", "neutral"))
    left = f"""<div class="card" style="flex:0 0 55.5%">{cardh("Pengguna", "Role menentukan apa yang bisa dilihat dan diubah; cakupan membatasi outlet", chip("7 pengguna", "neutral"))}
 <table class="roomy"><thead><tr><th>Pengguna</th><th>Role</th><th>Cakupan</th><th>2FA</th><th>Aktif</th></tr></thead><tbody>{rows}</tbody></table>
 <div style="margin:12px 0 4px"><div class="row sp" style="margin-bottom:2px"><span class="sm b">Undangan tertunda</span>{chip("2", "neutral")}</div>
  <div class="row g10" style="padding:8px 0;border-bottom:1px solid #eceae4">{ic("mail", 16, color=MUTED)}<span class="grow sm"><b>anton@kedaipagi.id</b> <span class="muted">· Manager · Braga · dikirim 2 hari lalu</span></span><span class="btn sm">Kirim ulang</span></div>
  <div class="row g10" style="padding:8px 0">{ic("mail", 16, color=MUTED)}<span class="grow sm"><b>laras@kedaipagi.id</b> <span class="muted">· Analyst · semua outlet · dikirim kemarin</span></span><span class="btn sm">Kirim ulang</span></div></div>
 <div class="row g10" style="margin-top:auto;padding:11px 13px;border-radius:10px;background:var(--blue-t)">{ic("sparkles", 17, color="#184f95")}
  <div class="grow"><div class="b sm" style="color:var(--blue-d)">Role kustom <span class="chip info" style="height:18px;margin-left:6px">Enterprise</span></div>
  <div class="xs" style="color:#2d4f80;margin-top:2px">Buat role sendiri, mis. &ldquo;Area Manager Bandung&rdquo;: Dago dan Braga saja, dengan ekspor.</div></div></div></div>"""

    tk, no = ic("check", 17, 2.6, "tick"), '<span class="cross">&ndash;</span>'

    def c(x):
        if x is True:
            return tk
        if x is False:
            return no
        return f'<span class="chip neutral" style="height:19px;padding:0 6px;font-size:10.5px">{x}</span>'

    caps = [("Live Ops", [True, True, "outlet", False, "outlet", False]),
            ("Analytics dan banding", [True, True, "outlet", True, False, False]),
            ("Ekspor dan API key", [True, True, "outlet", True, False, False]),
            ("Alert dan laporan", [True, True, "outlet", False, False, False]),
            ("Zona dan kamera", [True, True, False, False, False, "sementara"]),
            ("Pengguna dan role", [True, "bukan Owner", False, False, False, False]),
            ("Privasi dan retensi", [True, False, False, False, False, False]),
            ("Tagihan dan paket", [True, False, False, False, False, False]),
            ("Log audit", [True, "lihat", False, False, False, False])]
    heads = "".join(f'<th class="center" style="padding:0 2px 8px;font-size:10px">{h}</th>' for h in ["Owner", "Admin", "Manager", "Analyst", "Viewer", "Installer"])
    mrows = "".join(f'<tr><td style="padding:9px 6px;font-size:12.5px">{n}</td>' + "".join(f'<td class="center" style="padding:9px 2px">{c(x)}</td>' for x in v) + "</tr>" for n, v in caps)
    right = f"""<div class="card grow">{cardh("Hak akses per role", "Sama untuk semua tenant. Super Admin tidak termasuk: itu bidang lain.")}
 <table class="rm" style="table-layout:fixed"><colgroup><col style="width:136px"><col><col><col><col><col><col></colgroup><thead><tr><th style="padding-left:6px">Kemampuan</th>{heads}</tr></thead><tbody>{mrows}</tbody></table>
 <div class="row g10" style="margin-top:14px;padding:11px 13px;border-radius:10px;background:var(--orange-t)">{ic("lock", 17, color="#9a3a14")}
  <div class="sm" style="color:#7a2f0f"><b>Super Admin</b> (tim platform) tidak ada di daftar ini. Akses ke data tenant hanya lewat izin Owner: berbatas waktu dan tercatat di Log audit.</div></div>
 <div style="margin-top:14px"><div class="sm b" style="margin-bottom:2px">Keamanan akun</div>
  <div class="row g12" style="padding:9px 0;border-bottom:1px solid #eceae4">{toggle(True)}<div class="grow sm">2FA wajib untuk Owner dan Admin</div></div>
  <div class="row g12" style="padding:9px 0;border-bottom:1px solid #eceae4">{toggle(False)}<div class="grow sm">Masuk lewat SSO (Google / Microsoft)</div>{chip("Enterprise", "info")}</div>
  <div class="row g12" style="padding:9px 0">{toggle(True)}<div class="grow sm">Sesi berakhir otomatis setelah 12 jam tidak aktif</div></div></div>
 <div class="row g14 xs muted" style="margin-top:auto;padding-top:8px"><span><b>outlet</b> = hanya outlet yang ditugaskan</span><span><b>sementara</b> = berbatas waktu</span></div></div>"""
    body = f'<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}{right}</div>'
    return page(plane="tenant", active="users", url="app.denyut.id/jaringan/pengguna",
                title="Pengguna &amp; Role", sub="Kedai Pagi · 7 pengguna · 12 outlet · hanya Owner dan Admin",
                actions='<span class="search">' + ic("search", 14) + "Cari pengguna</span>" + sel("Role", "Semua") + btn("Undang pengguna", "user-plus", "pri"), body=body)


# ================================================================ 08 privasi & audit
def privacy() -> str:
    def pr(title, sub, ctl):
        return (f'<div class="item" style="align-items:center;padding:10px 0"><div class="grow"><div class="b" style="font-size:13px">{title}</div>'
                f'<div class="xs muted" style="margin-top:2px;line-height:1.4">{sub}</div></div>{ctl}</div>')

    lock = f'<span class="row g6 xs muted">{ic("lock", 13)}selalu aktif</span>'
    left = f"""<div class="card" style="flex:0 0 45%;padding-bottom:6px">{cardh("Kontrol privasi", "Dirancang dengan prinsip minimisasi data")}
 {pr("Video tidak meninggalkan lokasi", "Yang dikirim ke cloud hanya angka dan titik anonim, tidak pernah gambar.", toggle(lock=True))}
 {pr("Tanpa wajah, tanpa identifikasi lintas sesi", "ID pelacak anonim dan hanya berlaku dalam satu sesi kamera.", toggle(lock=True))}
 {pr("Akses video on-site (LAN / VPN)", "Owner dan Admin, lewat jaringan lokasi. Tidak melewati cloud.", toggle(True))}
 {pr("Metrik per-orang untuk petugas", "Mati secara default. Waktu layanan hanya dilaporkan per zona. Menyalakan butuh persetujuan Owner dan pemberitahuan ke tim.", toggle(False))}
 {pr("Retensi data per-menit", "Setelah itu hanya agregat harian yang disimpan.", '<span class="sel" style="height:28px">13 bulan' + ic("chevron-down", 14, color=MUTED) + "</span>")}
 {pr("Ekspor tanpa ID pelacak", "Berkas ekspor hanya berisi agregat, bukan jejak per-orang.", toggle(True))}
 {pr("Zona dikecualikan", "1 aktif: cermin dinding (Senopati).", '<span class="btn sm">Kelola</span>')}
 {pr("Permintaan data (akses / hapus)", "Tanggapi permintaan dari subjek data dengan jejak yang tercatat.", '<span class="btn sm">Buka formulir</span>')}
 <div style="margin-top:auto;padding-top:12px"><div class="sm b" style="margin-bottom:8px">Peta data</div>
 <div class="grid" style="grid-template-columns:1fr 1fr;gap:10px">
  <div style="border:1px solid var(--border);border-radius:10px;padding:10px 12px;background:#fff"><div class="row g6 b sm" style="color:var(--good-x)">{ic("circle-check", 15, 2.2)}Disimpan</div>
   <div class="xs ink2" style="margin-top:6px;line-height:1.65">Jumlah orang per menit<br>Lama berada di zona (anonim)<br>Kejadian: antre, layanan, alert</div></div>
  <div style="border:1px solid var(--border);border-radius:10px;padding:10px 12px;background:#fff"><div class="row g6 b sm" style="color:var(--crit-x)">{ic("ban", 15, 2.2)}Tidak pernah disimpan</div>
   <div class="xs ink2" style="margin-top:6px;line-height:1.65">Video dan gambar<br>Wajah atau ciri biometrik<br>Nama atau identitas pelanggan</div></div></div></div></div>"""

    req = f"""<div class="card" style="flex:none;border-color:#f3c5ad;background:#fffaf7">{cardh("Permintaan akses Support", "", chip("menunggu persetujuan", "orange", "clock"))}
 <div class="row g12" style="align-items:flex-start"><div class="av" style="background:#fdeae1;color:#9a3a14">DS</div>
 <div class="grow"><div style="font-size:13.5px"><b>Dewi S.</b> (Support Denyut) meminta akses <b>baca</b> ke <b>Senopati</b> selama <b>60 menit</b>.</div>
 <div class="ink2 sm" style="margin-top:3px">Alasan: &ldquo;Kamera Teras offline sejak 09.42, perlu memeriksa log perangkat.&rdquo;</div>
 <div class="row g8" style="margin-top:10px"><span class="btn pri sm">Setujui 60 mnt</span><span class="btn sm">Tolak</span><span class="xs muted" style="margin-left:6px">kedaluwarsa dalam 14:32</span></div></div></div></div>"""

    def lg(t, who, act, obj, kind="neutral"):
        return f'<tr><td class="muted">{t}</td><td class="b">{who}</td><td>{act}</td><td class="ink2" style="white-space:normal">{obj}</td></tr>'

    log = f"""<div class="card grow" style="padding-bottom:6px">{cardh("Log audit", "Setiap aksi sensitif tercatat dan tidak bisa diubah", chip("hari ini", "neutral"))}
 <table class="lgt"><thead><tr><th>Waktu</th><th>Pelaku</th><th>Aksi</th><th>Objek</th></tr></thead><tbody>
 {lg("15.04", "Sari W. · Manager", "Mengekspor CSV", "Analytics · 7 hari")}
 {lg("14.31", "Bagas P. · Admin", "Mengubah zona", "Senopati · Area pelayan")}
 {lg("13.31", "Sistem", "Mengirim alert", "Counter tak terjaga &rarr; WhatsApp")}
 {lg("11.02", "Rina A. · Owner", "Menyetujui akses Support", "Dewi S. · 60 mnt · Senopati")}
 {lg("09.42", "Sistem", "Kamera offline", "Senopati · Teras")}
 {lg("08.00", "Sistem", "Mengirim laporan", "Harian · 3 penerima")}
 {lg("07.55", "Dimas H. · Manager", "Login gagal", "2FA belum aktif · Kemang")}
 {lg("kemarin", "Teknisi · Installer", "Menambah kamera", "Senopati · Teras")}
 {lg("kemarin", "Putri L. · Analyst", "Melihat analytics", "Banding outlet · 30 hari")}
 {lg("kemarin", "Sistem", "Memperbarui engine", "edge-0112 · v2.3.2 &rarr; v2.4.0")}</tbody></table></div>"""
    body = f'<div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}<div class="col g12 grow">{req}{log}</div></div>'
    return page(plane="tenant", active="privacy", url="app.denyut.id/jaringan/privasi",
                title="Privasi &amp; Audit", sub="Kedai Pagi · kontrol data dan jejak siapa melakukan apa · hanya Owner",
                actions=btn("Ekspor log", "download"), body=body)


# ================================================================ platform plane
PLATFORM_NOTE = (f'{ic("lock", 15)}<span>Anda melihat <b>metadata operasional</b>. Data analitik pelanggan hanya terbuka lewat izin Owner: '
                 'berbatas waktu dan tercatat di audit log.</span>')


def mini(label: str, value: str, sub: str, icon_: str) -> str:
    return (f'<div class="card" style="padding:12px 15px;gap:5px"><div class="row sp"><span class="sm ink2 b">{label}</span>{ic(icon_, 15, color=MUTED)}</div>'
            f'<div class="row g8" style="align-items:baseline"><span style="font-size:27px;font-weight:600;letter-spacing:-.02em;line-height:1.1">{value}</span><span class="sm ink2">{sub}</span></div></div>')


def plan_chip(name: str) -> str:
    if name == "Enterprise":
        return '<span class="chip" style="background:#1a1a19;color:#fff">Enterprise</span>'
    return chip(name, "info" if name == "Growth" else "neutral")


# ================================================================ 09 super admin: tenant & paket
def sa_tenants() -> str:
    def health(kind):
        return {"ok": chip("Sehat", "good", "circle-check"), "warn": chip("Perlu perhatian", "warn", "circle-alert"),
                "bad": chip("Insiden", "crit", "siren")}[kind]

    def t(name, ind, plan, outlets, cams, kind, last, ask=False):
        act = f'<span class="btn sm">{ic("lock", 12)}Minta akses</span>' if ask else '<span class="btn sm">Detail</span>'
        return (f'<tr><td><div class="b">{name}</div><div class="xs muted">{ind}</div></td><td>{plan_chip(plan)}</td><td class="n">{outlets}</td>'
                f'<td class="n">{cams}</td><td>{health(kind)}</td><td class="muted">{last}</td><td>{act}</td></tr>')

    rows = (t("Kedai Pagi", "F&amp;B", "Enterprise", 12, "46 / 48", "ok", "2 mnt lalu")
            + t("Roti Hangat", "Bakery", "Growth", 7, "21 / 21", "ok", "1 jam lalu")
            + t("Fit Studio Kota", "Gym", "Growth", 3, "8 / 8", "ok", "kemarin")
            + t("Optik Jernih", "Retail", "Growth", 5, "14 / 15", "warn", "3 jam lalu")
            + t("Toko Buku Pelangi", "Retail", "Growth", 4, "11 / 12", "ok", "kemarin")
            + t("Klinik Sehat Bersama", "Klinik", "Starter", 2, "4 / 4", "ok", "2 hari lalu")
            + t("Kopi Tetangga", "F&amp;B", "Starter", 1, "0 / 2", "bad", "5 jam lalu", True))
    left = f"""<div class="card" style="flex:0 0 63.5%">{cardh("Tenant", "Kesehatan operasional per pelanggan · tanpa data analitik mereka", chip("7 dari 38", "neutral"))}
 <table class="roomy"><thead><tr><th>Tenant</th><th>Paket</th><th class="n">Outlet</th><th class="n">Kamera online</th><th>Kesehatan</th><th>Login</th><th></th></tr></thead><tbody>{rows}</tbody></table>
 <div class="row g8" style="margin-top:auto;padding-top:10px">{ic("lock", 14, color=MUTED)}<span class="xs muted">&ldquo;Minta akses&rdquo; mengirim permohonan ke Owner tenant. Tanpa persetujuan, tombolnya tidak membuka apa pun.</span></div></div>"""

    tk, no = ic("check", 17, 2.6, "tick"), '<span class="cross">&ndash;</span>'

    def v(x):
        if x is True:
            return tk
        if x is False:
            return no
        return f'<span class="xs b">{x}</span>'

    feats = [("Live Ops", [True, True, True]), ("Riwayat analytics", ["30 hari", "13 bulan", "kustom"]),
             ("Antrean dan layanan", [False, True, True]), ("Alert dan WhatsApp", ["email", True, True]),
             ("Banding outlet (HQ)", [False, False, True]), ("API dan webhook", [False, "baca", True]),
             ("SSO dan role kustom", [False, False, True]), ("Retensi kustom dan SLA", [False, False, True])]
    frows = "".join(f'<tr><td style="padding:10px 6px;font-size:12.5px">{n}</td>' + "".join(f'<td class="center" style="padding:10px 2px">{v(x)}</td>' for x in xs) + "</tr>" for n, xs in feats)
    right = f"""<div class="card grow">{cardh("Paket dan hak fitur", "Satu tempat mengatur apa yang termasuk di tiap paket", '<span class="btn sm org">Edit paket</span>')}
 <table style="table-layout:fixed"><colgroup><col style="width:158px"><col><col><col></colgroup><thead><tr><th style="padding-left:6px">Fitur</th><th class="center">Starter</th><th class="center">Growth</th><th class="center">Enterprise</th></tr></thead><tbody>{frows}</tbody></table>
 <div class="row g10" style="margin-top:auto;padding:10px 12px;border-radius:10px;background:var(--orange-t)">{ic("flag", 16, color="#9a3a14")}
  <div class="sm" style="color:#7a2f0f"><b>2 tenant</b> memakai feature flag khusus (pengecualian dari paketnya).</div></div></div>"""
    kpis = (mini("Kamera online", "96,8%", "semua tenant", "video") + mini("Perangkat edge sehat", "41 / 43", "", "server")
            + mini("Memakai engine terbaru", "74%", "", "rocket") + mini("Insiden terbuka", "2", "1 kritis", "siren"))
    body = f'<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:none">{kpis}</div><div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}{right}</div>'
    return page(plane="platform", active="tenant", url="console.denyut.id/tenant", title="Tenant &amp; Paket",
                sub="Konsol platform · hanya tim internal · setiap aksi tercatat",
                actions='<span class="search">' + ic("search", 14) + "Cari tenant</span>" + btn("Tenant baru", "plus", "org"),
                body=body, banner=PLATFORM_NOTE)


# ================================================================ 10 super admin: armada edge & model
def sa_fleet() -> str:
    def st(kind):
        return {"on": chip("Online", "good", "circle-check"), "off": chip("Offline", "crit", "wifi-off"),
                "hot": chip("Suhu tinggi", "warn", "thermometer"), "upd": chip("Memperbarui", "info", "refresh-cw")}[kind]

    def d(dev, tenant, kind, eng, cams, fps, temp, seen):
        return (f'<tr><td class="b">{dev}</td><td class="ink2">{tenant}</td><td>{st(kind)}</td><td>{eng}</td><td class="n">{cams}</td>'
                f'<td class="n">{fps}</td><td class="n">{temp}</td><td class="muted">{seen}</td></tr>')

    rows = (d("edge-0112", "Kedai Pagi · Senopati", "on", "v2.4.0", "3 / 4", "5,0", "61°", "3 dtk")
            + d("edge-0113", "Kedai Pagi · Kemang", "on", "v2.4.0", "4 / 4", "5,0", "64°", "2 dtk")
            + d("edge-0130", "Kedai Pagi · Braga", "hot", "v2.4.0", "4 / 4", "4,6", "83°", "3 dtk")
            + d("edge-0087", "Roti Hangat · Pusat", "on", "v2.3.2", "3 / 3", "5,0", "58°", "4 dtk")
            + d("edge-0121", "Optik Jernih · Mall A", "on", "v2.4.0", "2 / 3", "5,0", "66°", "3 dtk")
            + d("edge-0102", "Toko Buku Pelangi · Cab 2", "upd", "v2.3.2 &rarr; v2.4.0", "4 / 4", "&mdash;", "&mdash;", "baru saja")
            + d("edge-0045", "Klinik Sehat · Lobi", "on", "v2.3.2", "2 / 2", "5,0", "55°", "5 dtk")
            + d("edge-0099", "Kopi Tetangga · Utama", "off", "v2.3.2", "0 / 2", "&mdash;", "&mdash;", "5 jam lalu"))
    left = f"""<div class="card" style="flex:0 0 62.5%">{cardh("Armada perangkat edge", "Satu perangkat di tiap lokasi: decode, deteksi (TensorRT), tracking, lalu kirim angka", chip("8 dari 43", "neutral"))}
 <table class="roomy"><thead><tr><th>Perangkat</th><th>Tenant · outlet</th><th>Status</th><th>Engine</th><th class="n">Kamera</th><th class="n">FPS</th><th class="n">GPU</th><th>Terlihat</th></tr></thead><tbody>{rows}</tbody></table>
 <div class="row g8" style="margin-top:auto;padding-top:10px">{ic("info", 14, color=MUTED)}<span class="xs muted">FPS = sampling yang diproses (target 5). Engine TensorRT dibangun per GPU dan presisi, jadi GPU berbeda mendapat build berbeda.</span></div></div>"""

    def gate(kind, text):
        icn, col = ("circle-check", "var(--good-x)") if kind == "ok" else ("circle-alert", "var(--warn-x)")
        return f'<div class="row g8" style="padding:4px 0"><span style="color:{col}">{ic(icn, 16, 2.2)}</span><span class="sm">{text}</span></div>'

    def stage(i, state, title, meta, extra=""):
        circ = (f'<span class="stp done">{ic("check", 13, 2.8)}</span>' if state == "done" else f'<span class="stp on">{i}</span>' if state == "on" else f'<span class="stp">{i}</span>')
        return (f'<div class="row g10" style="align-items:flex-start;padding:7px 0">{circ}<div class="grow"><div class="row sp"><span class="b" style="font-size:13px">{title}</span>'
                f'<span class="xs muted">{meta}</span></div>{extra}</div></div>')

    rollout = f"""<div class="card" style="flex:none">{cardh("Rilis engine v2.4.0", "Bertahap: berhenti otomatis kalau gerbang gagal", chip("berjalan", "info", "rocket"))}
 {stage(1, "done", "Canary · 5%", "2 perangkat · 48 jam", '<div class="xs muted" style="margin-top:2px">Lolos semua gerbang</div>')}
 {stage(2, "on", "Ring 1 · 25%", "11 perangkat · 19 dari 48 jam", '<div class="meter org" style="margin-top:7px"><i style="width:40%"></i></div>')}
 {stage(3, "", "Semua perangkat · 100%", "43 perangkat", '<div class="xs muted" style="margin-top:2px">Menunggu Ring 1 selesai</div>')}
 <div class="sep" style="margin:8px 0 6px"></div><div class="xs b muted" style="letter-spacing:.06em;margin-bottom:2px">GERBANG KUALITAS</div>
 {gate("ok", "Selisih okupansi vs hitung manual tidak memburuk")}{gate("ok", "Track berlubang tidak naik dibanding engine lama")}
 {gate("ok", "Sampling stabil 5 fps di semua perangkat Ring 1")}{gate("warn", "Suhu GPU di bawah 80°: 1 perangkat di atas (edge-0130)")}
 <div class="row g8" style="margin-top:10px"><span class="btn sm">Jeda</span><span class="btn sm">Rollback ke v2.3.2</span><span class="grow"></span><span class="btn org sm" style="opacity:.55">Lanjut ke Semua</span></div></div>"""

    dist = f"""<div class="card grow"><div class="card-h" style="margin-bottom:8px"><h3>Sebaran versi engine</h3></div>
 <div class="row" style="gap:2px"><div style="flex:74;height:16px;background:{BLUE};border-radius:5px 0 0 5px"></div><div style="flex:26;height:16px;background:{ORANGE};border-radius:0 5px 5px 0"></div></div>
 <div class="row sp" style="margin-top:9px"><div class="lg"><span><i class="sq" style="background:{BLUE}"></i>v2.4.0 · 74%</span><span><i class="sq" style="background:{ORANGE}"></i>v2.3.2 · 26%</span></div>
 <span class="xs muted">32 dan 11 perangkat</span></div></div>"""
    kpis = (mini("Perangkat online", "41 / 43", "", "server") + mini("Memakai engine terbaru", "74%", "", "rocket")
            + mini("Suhu GPU rata-rata", "62°", "maks 83°", "thermometer") + mini("Jeda data median", "3 dtk", "edge ke cloud", "timer"))
    body = f'<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:none">{kpis}</div><div class="row g12" style="flex:1;min-height:0;align-items:stretch">{left}<div class="col g12 grow">{rollout}{dist}</div></div>'
    return page(plane="platform", active="fleet", url="console.denyut.id/armada", title="Armada Edge &amp; Model",
                sub="Konsol platform · perangkat di lokasi pelanggan dan rilis engine bertahap",
                actions=btn("Bangun engine", "cpu") + btn("Rilis baru", "rocket", "org"), body=body, banner=PLATFORM_NOTE)


# ================================================================ 00 peta halaman
def overview(thumbs: dict[str, str]) -> str:
    from kit import CSS, font_css

    def card(name, num, title, desc, who, accent):
        chips = "".join(f'<span class="chip neutral" style="height:21px;font-size:11.5px;padding:0 8px">{w}</span>' for w in who)
        return (f'<div style="background:#fff;border:1px solid var(--border);border-radius:12px;padding:9px;display:flex;flex-direction:column;gap:6px;min-width:0">'
                f'<div style="position:relative;border-radius:8px;overflow:hidden;box-shadow:0 0 0 1px rgba(11,11,11,.10)"><img src="{thumbs[name]}" style="width:100%;display:block">'
                f'<span style="position:absolute;left:7px;top:7px;width:22px;height:22px;border-radius:50%;background:{accent};color:#fff;font-size:11.5px;font-weight:700;display:grid;place-items:center">{num}</span></div>'
                f'<div class="b" style="font-size:15px;margin-top:3px">{title}</div><div class="ink2" style="font-size:12.5px;line-height:1.45;min-height:37px">{desc}</div>'
                f'<div class="row g4 wrap">{chips}</div></div>')

    cust = [("01-hari-ini", 1, "Hari ini", "Lima angka kunci dan temuan yang perlu tindakan.", ["Owner", "Admin", "Manager"]),
            ("02-live-ops", 2, "Live Ops", "Kondisi outlet detik ini: denah anonim, zona, video on-site opsional.", ["Manager", "Viewer (TV)"]),
            ("03-analytics", 3, "Analytics", "Pola jam×hari, okupansi meja, alur pelanggan, beban vs staf.", ["Owner", "Admin", "Analyst"]),
            ("04-banding-outlet", 4, "Banding Outlet", "Peringkat 12 outlet, anomali, sebaran skor.", ["Owner", "Admin pusat"]),
            ("05-kamera-zona", 5, "Kamera &amp; Zona", "Pasang kamera, gambar zona di snapshot, validasi hitungan.", ["Admin", "Installer"]),
            ("06-alert-laporan", 6, "Alert &amp; Laporan", "Aturan otomatis, WhatsApp, ringkasan harian dan mingguan.", ["Owner", "Admin", "Manager"]),
            ("07-pengguna-role", 7, "Pengguna &amp; Role", "Undang pengguna, hak akses per role dan per outlet.", ["Owner", "Admin"]),
            ("08-privasi-audit", 8, "Privasi &amp; Audit", "Kontrol data, izin Support, log audit.", ["Owner"])]
    plat = [("09-superadmin-tenant", 9, "Tenant &amp; Paket", "Seluruh pelanggan, paket, hak fitur, permohonan akses.", ["Super Admin", "Support"]),
            ("10-superadmin-armada", 10, "Armada Edge &amp; Model", "Perangkat di lokasi dan rilis engine bertahap.", ["Super Admin"])]
    later = ["Tagihan &amp; pemakaian", "Dukungan (izin sementara)", "Feature flags", "Audit platform"]

    def principle(icon_, title, text):
        return (f'<div class="row g12" style="flex:1;background:#fff;border:1px solid var(--border);border-radius:12px;padding:16px 18px">'
                f'<span class="ibox info" style="width:36px;height:36px;border-radius:11px">{ic(icon_, 19)}</span><div><div class="b" style="font-size:15px">{title}</div><div class="ink2" style="font-size:12.5px;margin-top:3px;line-height:1.45">{text}</div></div></div>')

    return f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><style>{font_css()}{CSS}</style></head>
<body><div class="stage" style="background:var(--page);padding:34px 36px 44px;display:flex;flex-direction:column;justify-content:space-between">
 <div class="row sp" style="flex:none"><div><div class="row g10"><span class="logo">{PULSE}</span><h1 style="font-size:26px">Peta halaman</h1></div>
  <div class="sub" style="margin-top:4px">Satu produk, dua bidang akses · 10 halaman utama</div></div>
  <div class="row g8 sm ink2"><span class="chip info">Aplikasi pelanggan</span><span class="chip orange">Konsol platform</span></div></div>
 <div class="row g14" style="align-items:flex-start;flex:none">
  <div style="flex:0 0 1010px;background:#eef3fb;border:1px solid #cfdcf1;border-radius:16px;padding:14px 16px 16px">
   <div class="row sp" style="margin-bottom:11px"><div class="b" style="font-size:13px;letter-spacing:.09em;color:var(--blue-d)">APLIKASI PELANGGAN</div>
    <div class="xs ink2">Owner · Admin · Manager · Analyst · Viewer · Installer</div></div>
   <div class="grid" style="grid-template-columns:repeat(4,1fr);gap:12px">{"".join(card(n, i, t, d, w, "#2a78d6") for n, i, t, d, w in cust)}</div></div>
  <div style="flex:1;background:#fdf1ea;border:1px solid #f3cfba;border-radius:16px;padding:14px 16px 16px">
   <div class="row sp" style="margin-bottom:11px"><div class="b" style="font-size:13px;letter-spacing:.09em;color:var(--orange-d)">KONSOL PLATFORM</div><div class="xs ink2">tim internal saja</div></div>
   <div class="grid" style="grid-template-columns:1fr 1fr;gap:12px">{"".join(card(n, i, t, d, w, "#eb6834") for n, i, t, d, w in plat)}</div>
   <div class="xs b muted" style="letter-spacing:.06em;margin:14px 0 8px">BERIKUTNYA</div>
   <div class="grid" style="grid-template-columns:1fr 1fr;gap:8px">{"".join(f'<div style="border:1.5px dashed #e2b9a1;border-radius:10px;padding:11px 12px;font-size:12.5px;color:#7a2f0f">{t}</div>' for t in later)}</div></div></div>
 <div class="row g12" style="flex:none">{principle("database", "Isolasi tenant", "Setiap pelanggan terpisah di database lewat Row-Level Security PostgreSQL.")}
  {principle("key-round", "Izin sementara", "Super Admin masuk ke data pelanggan hanya dengan persetujuan Owner, berbatas waktu, tercatat.")}
  {principle("video", "Video tetap di lokasi", "Yang menyeberang ke cloud hanya angka dan titik anonim, tidak pernah gambar.")}</div>
 <div class="mocktag">MOCKUP · data ilustrasi · bukan data pelanggan</div></div></body></html>"""


# <<<APPEND>>>


PAGES = [("01-hari-ini", home), ("02-live-ops", live), ("03-analytics", analytics), ("04-banding-outlet", hq),
         ("05-kamera-zona", setup), ("06-alert-laporan", alerts), ("07-pengguna-role", users), ("08-privasi-audit", privacy),
         ("09-superadmin-tenant", sa_tenants), ("10-superadmin-armada", sa_fleet)]
