"""Design kit for the product mockups: tokens, icons, SVG charts, page shell.

Colour follows the dataviz reference palette (blue categorical slot 1, the
blue sequential ramp, the fixed status palette), and every chart obeys its mark
specs: thin marks, 2 px lines, 4 px rounded data ends, hairline solid grid, a
2 px surface gap between touching fills, no number on every point.

Orange is reserved here for the *platform* plane (the vendor's own console) so
the two planes of the product are told apart at a glance: blue is the
customer's app, orange is ours.
"""

from __future__ import annotations

import base64
import html
import math
import os
import re
import urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("MOCKUP_CACHE") or Path(__file__).resolve().parents[1] / ".mockup_cache")
UA = {"User-Agent": "Mozilla/5.0"}

# ---------------------------------------------------------------- palette ---
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURF, PAGE = "#e1e0d9", "#c3c2b7", "#fcfcfb", "#f6f6f3"
BLUE, ORANGE = "#2a78d6", "#eb6834"
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
        "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
ORDINAL = ["#86b6ef", "#3987e5", "#256abf", "#184f95"]  # validated --ordinal


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ------------------------------------------------------------------ assets ---
def _get(url: str, dest: Path) -> bytes:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers=UA)
        dest.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return dest.read_bytes()


def font_css() -> str:
    out = []
    for w in (400, 500, 600, 700):
        b = _get(f"https://cdn.jsdelivr.net/npm/@fontsource/inter/files/inter-latin-{w}-normal.woff2",
                 CACHE / "fonts" / f"inter-{w}.woff2")
        out.append("@font-face{font-family:'Inter';font-weight:%d;font-style:normal;"
                   "src:url(data:font/woff2;base64,%s) format('woff2')}" % (w, base64.b64encode(b).decode()))
    return "".join(out)


def _icon_svg(name: str, prefix: str) -> str:
    return _get(f"https://api.iconify.design/{prefix}/{name}.svg",
                CACHE / "icons" / f"{prefix}-{name}.svg").decode()


def ic(name: str, size: int = 16, sw: float = 1.9, cls: str = "", color: str | None = None,
       prefix: str = "lucide") -> str:
    """Inline icon. Lucide is stroke-based, so it follows `color` / currentColor."""
    s = _icon_svg(name, prefix)
    s = re.sub(r'\swidth="[^"]*"', f' width="{size}"', s, count=1)
    s = re.sub(r'\sheight="[^"]*"', f' height="{size}"', s, count=1)
    if prefix == "lucide":
        s = s.replace('stroke-width="2"', f'stroke-width="{sw}"')
    attrs = f' class="ic {cls}"' + (f' style="color:{color}"' if color else "")
    return s.replace("<svg", "<svg" + attrs, 1)


def data_uri(path: Path, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


# --------------------------------------------------------------------- css ---
CSS = r"""
:root{
  --page:#f6f6f3;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
  --grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);
  --blue:#2a78d6;--blue-d:#184f95;--blue-t:#e6effb;--orange:#eb6834;--orange-d:#9a3a14;--orange-t:#fdeae1;
  --good:#0ca30c;--good-t:#e5f4e5;--good-x:#006300;
  --warn:#fab219;--warn-t:#fdf1d3;--warn-x:#7a5200;
  --crit:#d03b3b;--crit-t:#fbe5e5;--crit-x:#a42626;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1600px;height:900px;overflow:hidden;background:#e5e4de}
body{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;color:var(--ink);
  -webkit-font-smoothing:antialiased;font-size:13px;line-height:1.35}
svg text{font-family:inherit}
.ic{display:inline-block;vertical-align:middle;flex:none}

.stage{position:relative;width:1600px;height:900px;background:linear-gradient(135deg,#ecebe6,#dedcd5)}
.win{position:absolute;left:26px;top:20px;width:1548px;height:852px;background:var(--page);border-radius:14px;
  box-shadow:0 26px 60px rgba(11,11,11,.22),0 0 0 1px rgba(11,11,11,.09);overflow:hidden;display:flex;flex-direction:column}
.chrome{height:38px;flex:none;background:#efeee9;border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 14px}
.dots{display:flex;gap:7px;width:90px}.dots i{width:11px;height:11px;border-radius:50%;background:#d4d3cc;display:block}
.url{margin:0 auto;width:470px;height:24px;border-radius:7px;background:var(--surface);border:1px solid var(--border);
  display:flex;align-items:center;gap:7px;padding:0 10px;font-size:12px;color:var(--ink2)}
.chrome .sp{width:90px}
.app{flex:1;display:flex;min-height:0}
.mocktag{position:absolute;right:30px;bottom:3px;font-size:10.5px;color:#8b8a83;letter-spacing:.02em}

/* sidebar */
.side{width:216px;flex:none;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:15px 12px 12px}
.brand{display:flex;align-items:center;gap:9px;padding:0 6px 13px;font-weight:700;font-size:17px;letter-spacing:-.015em}
.logo{width:28px;height:28px;border-radius:8px;background:var(--blue);display:grid;place-items:center;flex:none}
.outlet{border:1px solid var(--border);border-radius:10px;padding:8px 10px;display:flex;align-items:center;gap:9px;background:#fff;margin-bottom:8px}
.outlet .t{font-weight:600;font-size:13px;line-height:1.2}.outlet .s{font-size:11.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nav-g{font-size:10.5px;font-weight:600;letter-spacing:.09em;color:var(--muted);padding:12px 9px 5px;text-transform:uppercase}
.nav a{display:flex;align-items:center;gap:10px;padding:7px 9px;border-radius:8px;font-size:13.5px;color:var(--ink2);font-weight:500;margin-bottom:1px}
.nav a.on{background:var(--blue-t);color:var(--blue-d);font-weight:600}
.nav a .live{width:7px;height:7px;border-radius:50%;background:var(--crit);margin-left:auto}
.nav a .tag{margin-left:auto;font-size:10px;font-weight:600;color:var(--muted);border:1px solid var(--grid);border-radius:5px;padding:0 5px}
.me{margin-top:auto;border-top:1px solid var(--grid);padding:11px 6px 0;display:flex;align-items:center;gap:9px}
.av{width:30px;height:30px;border-radius:50%;background:#dfe9f8;color:var(--blue-d);display:grid;place-items:center;font-weight:600;font-size:11.5px;flex:none}
.me .n{font-weight:600;font-size:12.5px;line-height:1.2}.me .r{font-size:11.5px;color:var(--muted)}
.side.dark{background:#1a1a19;border-right:0;color:#c3c2b7}
.side.dark .brand{color:#fff}.side.dark .logo{background:var(--orange)}
.side.dark .nav a{color:#c3c2b7}.side.dark .nav a.on{background:rgba(255,255,255,.10);color:#fff}
.side.dark .nav-g{color:#898781}.side.dark .me{border-color:#2c2c2a}.side.dark .me .n{color:#fff}
.side.dark .av{background:#3a2a22;color:#ffb28f}
.side.dark .outlet{background:#232321;border-color:#2c2c2a;color:#fff}.side.dark .outlet .s{color:#898781}
.envtag{font-size:10px;font-weight:700;letter-spacing:.08em;color:#ffb28f;background:rgba(235,104,52,.16);border-radius:5px;padding:2px 6px}

/* main */
.main{flex:1;min-width:0;padding:16px 22px 22px;display:flex;flex-direction:column;gap:13px;overflow:hidden}
.head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex:none}
h1{font-size:22px;font-weight:700;letter-spacing:-.018em;line-height:1.15}
.sub{font-size:13px;color:var(--ink2);margin-top:3px}
.banner{flex:none;display:flex;align-items:center;gap:9px;background:var(--orange-t);color:var(--orange-d);border-radius:9px;
  padding:7px 12px;font-size:12.5px;font-weight:500}

.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px;min-width:0;display:flex;flex-direction:column}
.card-h{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px;flex:none}
.card-h h3{font-size:14px;font-weight:600;letter-spacing:-.005em}
.card-h .hint{font-size:12px;color:var(--muted);margin-top:1px}

.row{display:flex;align-items:center}.col{display:flex;flex-direction:column}
.g4{gap:4px}.g6{gap:6px}.g8{gap:8px}.g10{gap:10px}.g12{gap:12px}.g14{gap:14px}.g18{gap:18px}
.grow{flex:1;min-width:0}.nogrow{flex:none}.sp{justify-content:space-between}.wrap{flex-wrap:wrap}
.muted{color:var(--muted)}.ink2{color:var(--ink2)}.b{font-weight:600}.sm{font-size:12px}.xs{font-size:11px}
.tnum{font-variant-numeric:tabular-nums}.right{text-align:right}.center{text-align:center}
.grid{display:grid}

.chip{display:inline-flex;align-items:center;gap:5px;height:22px;padding:0 9px;border-radius:999px;font-size:11.5px;font-weight:500;white-space:nowrap}
.chip.good{background:var(--good-t);color:var(--good-x)}.chip.warn{background:var(--warn-t);color:var(--warn-x)}
.chip.crit{background:var(--crit-t);color:var(--crit-x)}.chip.info{background:var(--blue-t);color:var(--blue-d)}
.chip.neutral{background:#efeee9;color:var(--ink2)}.chip.orange{background:var(--orange-t);color:var(--orange-d)}
.chip.sq{border-radius:6px}
.btn{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 12px;border-radius:8px;font-size:12.5px;font-weight:500;
  border:1px solid var(--border);background:#fff;color:var(--ink);white-space:nowrap}
.btn.pri{background:var(--blue);border-color:var(--blue);color:#fff}
.btn.org{background:var(--orange);border-color:var(--orange);color:#fff}
.btn.sm{height:26px;padding:0 10px;font-size:12px;border-radius:7px}
.sel{display:inline-flex;align-items:center;gap:8px;height:30px;padding:0 10px;border-radius:8px;border:1px solid var(--border);background:#fff;font-size:12.5px;font-weight:500}
.sel .k{color:var(--muted);font-weight:400}
.search{display:flex;align-items:center;gap:7px;height:30px;padding:0 10px;border-radius:8px;border:1px solid var(--border);background:#fff;font-size:12.5px;color:var(--muted);width:210px}
.sw{width:30px;height:18px;border-radius:999px;background:#c3c2b7;position:relative;flex:none}
.sw::after{content:"";position:absolute;left:2px;top:2px;width:14px;height:14px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.sw.on{background:var(--blue)}.sw.on::after{left:14px}
.sw.lock{background:#9bb9e3}.sw.lock::after{left:14px}

/* kpi */
.kpi{padding:13px 15px 12px;gap:0}
.kpi .l{font-size:12px;color:var(--ink2);font-weight:500;display:flex;align-items:center;justify-content:space-between}
.kpi .v{white-space:nowrap;font-size:31px;font-weight:600;letter-spacing:-.022em;line-height:1.1}
.kpi .v small{font-size:13px;font-weight:500;color:var(--ink2);margin-left:5px;letter-spacing:0}
.kpi .d{font-size:12px;color:var(--ink2);display:flex;align-items:center;gap:6px}
.delta{font-weight:600}.delta.g{color:var(--good-x)}.delta.r{color:var(--crit-x)}
.basis{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:500;height:20px;padding:0 7px;border-radius:6px}
.basis.good{background:var(--good-t);color:var(--good-x)}.basis.warn{background:var(--warn-t);color:var(--warn-x)}

/* tables */
table{border-collapse:collapse;width:100%;font-size:13px}
th{font-size:10.5px;font-weight:600;color:var(--muted);text-align:left;letter-spacing:.06em;text-transform:uppercase;padding:0 10px 8px;border-bottom:1px solid var(--grid);white-space:nowrap}
td{padding:8px 10px;border-bottom:1px solid #eceae4;font-variant-numeric:tabular-nums;white-space:nowrap;vertical-align:middle}
tr:last-child td{border-bottom:0}
td.n,th.n{text-align:right}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}
.meter{height:8px;border-radius:99px;background:#dbe8f9;position:relative;overflow:hidden}
.meter>i{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:var(--blue)}
.meter.org{background:#fbe0d3}.meter.org>i{background:var(--orange)}
.sep{height:1px;background:var(--grid);margin:0}
.item{display:flex;gap:11px;padding:11px 0;border-bottom:1px solid #eceae4}
.item:last-child{border-bottom:0}
.ibox{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;flex:none}
.ibox.warn{background:var(--warn-t);color:var(--warn-x)}.ibox.crit{background:var(--crit-t);color:var(--crit-x)}
.ibox.info{background:var(--blue-t);color:var(--blue-d)}.ibox.good{background:var(--good-t);color:var(--good-x)}
.ibox.orange{background:var(--orange-t);color:var(--orange-d)}.ibox.neutral{background:#efeee9;color:var(--ink2)}
.livepill{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 10px;border-radius:999px;background:var(--crit-t);color:var(--crit-x);font-size:11.5px;font-weight:700;letter-spacing:.05em}
.livepill i{width:7px;height:7px;border-radius:50%;background:var(--crit)}
.tick{color:var(--blue)}.cross{color:#b9b8b0}
.lg{display:flex;align-items:center;gap:14px;font-size:12px;color:var(--ink2)}
.lg i{display:inline-block;width:12px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
.lg i.sq{height:10px;width:10px;border-radius:3px}
.stp{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:11.5px;font-weight:600;border:1.5px solid var(--axis);color:var(--muted);background:#fff;flex:none}
.stp.on{border-color:var(--blue);color:var(--blue-d);background:var(--blue-t)}.stp.done{background:var(--blue);border-color:var(--blue);color:#fff}
.roomy td,.rm td{padding-top:11px;padding-bottom:11px}.lgt td{padding-top:9px;padding-bottom:9px}
.cmp td{padding-top:6px;padding-bottom:6px}
.tool{width:30px;height:30px;border-radius:8px;display:grid;place-items:center;color:var(--ink2);border:1px solid transparent}
.tool.on{background:var(--blue-t);color:var(--blue-d);border-color:#bcd3f3}
.field{display:flex;align-items:center;justify-content:space-between;gap:8px;height:32px;padding:0 10px;border-radius:8px;border:1px solid var(--border);background:#fff;font-size:13px}
"""


# ------------------------------------------------------------------ shell ---
def _nav(groups, active: str) -> str:
    out = []
    for g, items in groups:
        out.append(f'<div class="nav-g">{g}</div>')
        for key, icon, label, extra in items:
            cls = "on" if key == active else ""
            out.append(f'<a class="{cls}">{ic(icon, 17)}<span>{label}</span>{extra}</a>')
    return '<div class="nav">' + "".join(out) + "</div>"


BRAND = "Tilik"


def logo(size: int = 18) -> str:
    return ic("scan-eye", size, 2.1, color="#fff")


def sidebar_tenant(active: str) -> str:
    groups = [
        ("Operasional", [("home", "layout-dashboard", "Ringkasan Hari Ini", ""),
                         ("live", "radio", "Pantauan Live", '<span class="live"></span>')]),
        ("Laporan", [("analytics", "chart-column", "Analitik", ""),
                     ("hq", "building-2", "Perbandingan Outlet", "")]),
        ("Otomatis", [("alert", "bell-ring", "Notifikasi &amp; Laporan", "")]),
        ("Pengaturan", [("setup", "video", "CCTV &amp; Area", ""),
                        ("users", "users", "Tim &amp; Hak Akses", ""),
                        ("privacy", "shield-check", "Privasi &amp; Keamanan", "")]),
    ]
    return f"""<aside class="side">
  <div class="brand"><span class="logo">{logo()}</span>{BRAND}</div>
  <div class="outlet"><span class="ibox info" style="width:28px;height:28px">{ic('store', 15)}</span>
    <div class="grow"><div class="t">Senopati</div><div class="s">Kedai Pagi · Jakarta</div></div>{ic('chevrons-up-down', 15, color=MUTED)}</div>
  {_nav(groups, active)}
  <div class="me"><div class="av">RA</div><div class="grow"><div class="n">Rina Adiningsih</div><div class="r">Owner</div></div>{ic('chevron-down', 15, color=MUTED)}</div>
</aside>"""


def sidebar_platform(active: str) -> str:
    groups = [
        ("Panel internal", [("tenant", "building", "Klien &amp; Paket", ""),
                            ("fleet", "server", "Perangkat AI", ""),
                            ("billing", "credit-card", "Tagihan", "")]),
        ("Operasional", [("support", "life-buoy", "Support", '<span class="tag">izin</span>'),
                         ("flags", "flag", "Fitur Khusus", ""),
                         ("audit", "scroll-text", "Riwayat Internal", "")]),
    ]
    return f"""<aside class="side dark">
  <div class="brand"><span class="logo">{logo()}</span>{BRAND}</div>
  <div class="outlet"><span class="envtag">INTERNAL</span><div class="grow"><div class="s" style="color:#c3c2b7">Khusus tim {BRAND}</div></div></div>
  {_nav(groups, active)}
  <div class="me"><div class="av">BS</div><div class="grow"><div class="n">Bima Saputra</div><div class="r">Super Admin</div></div>{ic('chevron-down', 15, color='#898781')}</div>
</aside>"""


def page(*, plane: str, active: str, url: str, title: str, sub: str, actions: str, body: str,
         banner: str = "") -> str:
    side = sidebar_tenant(active) if plane == "tenant" else sidebar_platform(active)
    ban = f'<div class="banner">{banner}</div>' if banner else ""  # banner = icon html + <span>text</span>
    return f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><style>{font_css()}{CSS}</style></head>
<body><div class="stage"><div class="win">
 <div class="chrome"><div class="dots"><i></i><i></i><i></i></div>
   <div class="url">{ic('lock', 12, color=MUTED)}<span>{esc(url)}</span></div><div class="sp"></div></div>
 <div class="app">{side}<main class="main">
   <div class="head"><div><h1>{title}</h1><div class="sub">{sub}</div></div><div class="row g8">{actions}</div></div>
   {ban}{body}
 </main></div></div>
 <div class="mocktag">MOCKUP · contoh data, bukan data asli</div></div></body></html>"""


# ------------------------------------------------------------ components ---
def chip(text: str, kind: str = "neutral", icon: str | None = None, sq: bool = False) -> str:
    i = ic(icon, 12, 2.2) if icon else ""
    return f'<span class="chip {kind}{" sq" if sq else ""}">{i}{text}</span>'


def basis(kind: str) -> str:
    """The reliability badge - the product's signature element."""
    if kind in ("det", "line"):
        return f'<span class="basis good">{ic("circle-check", 12, 2.2)}Akurat</span>'
    return f'<span class="basis warn">{ic("circle-alert", 12, 2.2)}Estimasi</span>'


def kpi(label: str, value: str, unit: str, delta: str, dkind: str, dtxt: str, bas: str,
        icon: str, series: list[float]) -> str:
    dcls = {"g": "delta g", "r": "delta r", "n": "delta"}[dkind]
    arrow = ""
    if delta and dkind != "n":
        arrow = ic("trending-up" if delta.startswith("+") else "trending-down", 13, 2.2)
    return f"""<div class="card kpi"><div class="l"><span>{label}</span>{ic(icon, 15, color=MUTED)}</div>
 <div class="row sp" style="margin:7px 0 4px"><div class="v">{value}<small>{unit}</small></div>{spark(series)}</div>
 <div class="d"><span class="{dcls} row g4">{arrow}{delta}</span><span class="muted">{dtxt}</span></div>
 <div style="margin-top:9px">{basis(bas)}</div></div>"""


def toggle(on: bool = True, lock: bool = False) -> str:
    return f'<span class="sw {"lock" if lock else ("on" if on else "")}"></span>'


# ------------------------------------------------------------------ charts ---
def smooth(pts: list[tuple[float, float]]) -> str:
    """Monotone cubic path (Fritsch-Carlson): never overshoots the data."""
    n = len(pts)
    if n < 3:
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    dx = [xs[i + 1] - xs[i] for i in range(n - 1)]
    m = [(ys[i + 1] - ys[i]) / dx[i] for i in range(n - 1)]
    t = [m[0]] + [0 if m[i - 1] * m[i] <= 0 else (m[i - 1] + m[i]) / 2 for i in range(1, n - 1)] + [m[-1]]
    for i in range(n - 1):
        if m[i] == 0:
            t[i] = t[i + 1] = 0
        else:
            a, b = t[i] / m[i], t[i + 1] / m[i]
            s = a * a + b * b
            if s > 9:
                k = 3 / math.sqrt(s)
                t[i], t[i + 1] = k * a * m[i], k * b * m[i]
    d = f"M{xs[0]:.1f},{ys[0]:.1f}"
    for i in range(n - 1):
        h = dx[i] / 3
        d += f" C{xs[i] + h:.1f},{ys[i] + t[i] * h:.1f} {xs[i + 1] - h:.1f},{ys[i + 1] - t[i + 1] * h:.1f} {xs[i + 1]:.1f},{ys[i + 1]:.1f}"
    return d


def spark(vals: list[float], w: int = 80, h: int = 32, color: str = BLUE, tail: int = 4) -> str:
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = [(3 + i * (w - 10) / (len(vals) - 1), 5 + (h - 12) * (1 - (v - lo) / rng)) for i, v in enumerate(vals)]
    ex, ey = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="flex:none">'
            f'<path d="{smooth(pts)}" fill="none" stroke="{AXIS}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{smooth(pts[-tail:])}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="{color}" stroke="{SURF}" stroke-width="2"/></svg>')


def line_chart(w: int, h: int, today: list[tuple[float, float]], avg: list[tuple[float, float]],
               now: float, ymax: int = 100, xmin: int = 8, xmax: int = 22,
               peak: tuple[float, float, str] | None = None, now_label: str = "") -> str:
    """Emphasis form: today (accent, with a 10 % wash) against a gray reference."""
    L, R, T, B = 38, 16, 14, 26
    pw, ph = w - L - R, h - T - B
    X = lambda x: L + (x - xmin) / (xmax - xmin) * pw
    Y = lambda y: T + ph * (1 - y / ymax)
    g = []
    for v in range(0, ymax + 1, 25):
        g.append(f'<line x1="{L}" x2="{w - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID if v else AXIS}" stroke-width="1"/>')
        g.append(f'<text x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}" style="font-variant-numeric:tabular-nums">{v}%</text>')
    for x in range(xmin, xmax + 1, 2):
        g.append(f'<text x="{X(x):.1f}" y="{h - 7}" text-anchor="middle" font-size="11" fill="{MUTED}" style="font-variant-numeric:tabular-nums">{x:02d}.00</text>')
    avg_pts = [(X(x), Y(y)) for x, y in avg]
    t_pts = [(X(x), Y(y)) for x, y in today]
    area = smooth(t_pts) + f" L{t_pts[-1][0]:.1f},{Y(0):.1f} L{t_pts[0][0]:.1f},{Y(0):.1f} Z"
    ex, ey = t_pts[-1]
    out = "".join(g)
    out += f'<line x1="{X(now):.1f}" x2="{X(now):.1f}" y1="{T}" y2="{Y(0):.1f}" stroke="{AXIS}" stroke-width="1"/>'
    out += f'<path d="{smooth(avg_pts)}" fill="none" stroke="{MUTED}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    out += f'<path d="{area}" fill="{BLUE}" fill-opacity=".10"/>'
    out += f'<path d="{smooth(t_pts)}" fill="none" stroke="{BLUE}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    if peak:
        px, py, txt = peak
        out += f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="4" fill="{BLUE}" stroke="{SURF}" stroke-width="2"/>'
        out += f'<text x="{X(px) - 10:.1f}" y="{Y(py) - 8:.1f}" text-anchor="end" font-size="12" font-weight="600" fill="{INK}">{txt}</text>'
    out += f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4.5" fill="{BLUE}" stroke="{SURF}" stroke-width="2"/>'
    if now_label:
        out += f'<text x="{ex + 10:.1f}" y="{ey - 8:.1f}" font-size="12" font-weight="600" fill="{INK}">{now_label}</text>'
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{out}</svg>'


def heatmap(w: int, h: int, data: list[list[float]], rows: list[str], cols: list[str],
            mark: tuple[int, int] | None = None) -> str:
    """One-hue sequential grid, 2 px surface gaps, no borders around cells."""
    L, T = 34, 18
    gw, gh = w - L, h - T
    nr, nc = len(data), len(data[0])
    cw, ch = gw / nc, gh / nr
    lo = min(min(r) for r in data)
    hi = max(max(r) for r in data)
    out = []
    for j, c in enumerate(cols):
        if j % 2 == 0:
            out.append(f'<text x="{L + j * cw + cw / 2:.1f}" y="11" text-anchor="middle" font-size="10.5" fill="{MUTED}" style="font-variant-numeric:tabular-nums">{c}</text>')
    for i, r in enumerate(rows):
        out.append(f'<text x="{L - 8}" y="{T + i * ch + ch / 2 + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{r}</text>')
        for j in range(nc):
            v = (data[i][j] - lo) / ((hi - lo) or 1)
            col = RAMP[min(12, max(0, round(v * 12)))]
            out.append(f'<rect x="{L + j * cw + 1:.1f}" y="{T + i * ch + 1:.1f}" width="{cw - 2:.1f}" height="{ch - 2:.1f}" rx="3" fill="{col}"/>')
    if mark:
        i, j = mark
        cx, cy = L + j * cw + cw / 2, T + i * ch + ch / 2
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#fff" stroke="{INK}" stroke-width="2"/>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def scale_bar(w: int = 150) -> str:
    stops = "".join(f'<stop offset="{i / 12 * 100:.0f}%" stop-color="{c}"/>' for i, c in enumerate(RAMP))
    return (f'<svg width="{w}" height="10" viewBox="0 0 {w} 10"><defs><linearGradient id="sb">{stops}</linearGradient></defs>'
            f'<rect width="{w}" height="10" rx="5" fill="url(#sb)"/></svg>')


def columns(w: int, h: int, vals: list[float], labels: list[str], ymax: float, hi_idx: set[int] = frozenset(),
            label_idx: dict[int, str] | None = None) -> str:
    """<=24 px columns, 4 px rounded caps, square at the baseline; one label, on the peak."""
    L, R, T, B = 8, 8, 20, 22
    pw, ph = w - L - R, h - T - B
    n = len(vals)
    slot = pw / n
    bw = min(22, slot - 6)
    base = T + ph
    out = [f'<line x1="{L}" x2="{w - R}" y1="{base}" y2="{base}" stroke="{AXIS}" stroke-width="1"/>']
    for i, v in enumerate(vals):
        bh = ph * v / ymax
        x = L + i * slot + (slot - bw) / 2
        y = base - bh
        col = BLUE if i in hi_idx else "#9ec5f4"
        r = 4
        out.append(f'<path d="M{x:.1f},{base} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} H{x + bw - r:.1f} Q{x + bw:.1f},{y:.1f} {x + bw:.1f},{y + r:.1f} V{base} Z" fill="{col}"/>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{h - 6}" text-anchor="middle" font-size="10.5" fill="{MUTED}" style="font-variant-numeric:tabular-nums">{labels[i]}</text>')
        if label_idx and i in label_idx:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="11.5" font-weight="600" fill="{INK}">{label_idx[i]}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def hbar(label: str, value: float, vmax: float, color: str, w: int, text: str, sub: str = "") -> str:
    """One labelled horizontal bar: the value sits outside the bar end."""
    bw = max(4, (w - 70) * value / vmax)
    return (f'<div class="row g10" style="height:30px"><div style="width:150px;flex:none"><div class="b" style="font-size:12.5px">{label}</div>'
            f'<div class="xs muted">{sub}</div></div>'
            f'<svg width="{w - 70}" height="24" viewBox="0 0 {w - 70} 24"><rect x="0" y="5" width="{bw:.1f}" height="14" rx="4" fill="{color}"/></svg>'
            f'<div class="b tnum" style="width:60px;flex:none">{text}</div></div>')
