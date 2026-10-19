"""UkurPaket: mockup of the courier app that measures a parcel (L x W x H) with the phone camera.

    python assets.py <photo.jpg>   # once: blur the label, find the parcel outline -> img/
    python build.py                # screens/*.png (1236 x 2676), screens/alur_kurir.png (3840 x 2160),
                                   # prototype/index.html (clickable, one self-contained file)
    python build.py --no-shot      # HTML only

Every screen is written once (the functions s1 ... s8 below) and used three ways: one PNG per
screen, the overview board, and the clickable prototype. The camera screens are the courier's
real photo with the overlays the app would draw: the floor grid, the parcel outline, the depth
dots and the 3D box. The size shown (27 x 15 x 6 cm) is an illustration for testing the flow,
estimated from the label, not a measurement.
"""

import base64
import glob
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
IMG, HTML, OUT, PROTO = HERE / "img", HERE / "html", HERE / "screens", HERE / "prototype"
INTER = HERE.parent / "factory_mockup" / "assets" / "fonts"
G = json.loads((IMG / "geom.json").read_text())
PW, PH = G["W"], G["H"]
SW, SH = 412, 892                      # screen size in CSS px (Android 412 x 892)
K = SW / PW                            # photo -> screen scale
L, Wd, Ht = G["size_cm"]
VOL = L * Wd * Ht / 1000               # litres
VOLW = L * Wd * Ht / 6000              # kg, divisor 6000
RESI = "UKP-260419-0007"


def num(x, d=1):
    """Indonesian number format: 2,4 and 6.000."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def i(name, fill=False, cls=""):
    return f'<i class="i{" f" if fill else ""} {cls}">{name}</i>'


# --------------------------------------------------------------- styles ----
CSS = """
:root{--ink:#0F172A;--t2:#475569;--t3:#94A3B8;--line:#E2E8F0;--bg:#F3F5F8;--card:#FFFFFF;--blue:#2563EB;--blue-l:#EFF4FF;
--green:#16A34A;--green-l:#ECFDF3;--amber:#D97706;--amber-l:#FFF7E6;--red:#DC2626;--live:#22C55E;--glass:rgba(15,23,42,.66)}
.screen{width:412px;height:892px;position:relative;overflow:hidden;background:var(--bg);font-family:Inter,system-ui,sans-serif;
color:var(--ink);font-size:14px;line-height:1.4;-webkit-font-smoothing:antialiased}
.screen *{box-sizing:border-box}
.i{font-family:MSR;font-weight:400;font-style:normal;font-size:20px;line-height:1;display:inline-block;white-space:nowrap;
font-feature-settings:'liga';-webkit-font-smoothing:antialiased;font-variation-settings:'FILL' 0,'wght' 400,'opsz' 24;flex:none}
.i.f{font-variation-settings:'FILL' 1,'wght' 400,'opsz' 24}
.tn{font-variant-numeric:tabular-nums}
.sb{position:absolute;top:0;left:0;right:0;height:30px;padding:0 20px;display:flex;align-items:center;justify-content:space-between;
font-size:13px;font-weight:600;z-index:20;color:var(--ink)}
.sb .i{font-size:16px;margin-left:3px}.sb.dk{color:#fff}
.gb{position:absolute;bottom:7px;left:50%;width:108px;height:4px;margin-left:-54px;border-radius:2px;background:#0F172A;opacity:.55;z-index:30}
.gb.dk{background:#fff;opacity:.8}
.ah{position:absolute;top:30px;left:0;right:0;height:60px;padding:0 18px;display:flex;align-items:center;justify-content:space-between}
.brand{display:flex;align-items:center;gap:10px}.brand b{display:block;font-size:16px;line-height:1.15}
.brand small{color:var(--t2);font-size:12px}
.logo{width:36px;height:36px;border-radius:10px;background:var(--blue);display:grid;place-items:center;color:#fff}
.logo .i{font-size:22px}
.chip{display:inline-flex;align-items:center;gap:5px;height:26px;padding:0 10px;border-radius:13px;font-size:12px;font-weight:600;
white-space:nowrap}
.chip .i{font-size:16px}
.chip.ok{background:var(--green-l);color:var(--green)}.chip.warn{background:var(--amber-l);color:var(--amber)}
.chip.blue{background:var(--blue-l);color:var(--blue)}.chip.grey{background:#EEF1F5;color:var(--t2)}
.body{position:absolute;left:0;right:0;padding:0 16px;display:flex;flex-direction:column;gap:12px}
.h1{font-size:24px;font-weight:700;letter-spacing:-.01em}.sub{color:var(--t2);font-size:13px;margin-top:-8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px}
.card.act{border:1.5px solid var(--blue);box-shadow:0 6px 18px rgba(37,99,235,.10)}
.row{display:flex;align-items:center;gap:12px}.row>div{flex:1;min-width:0}.row b{display:block;font-size:15px}
.row small{display:block;color:var(--t2);font-size:12.5px}
.ico{width:40px;height:40px;border-radius:12px;background:#EEF1F5;display:grid;place-items:center;color:var(--t2);flex:none}
.ico.b{background:var(--blue-l);color:var(--blue)}.ico.g{background:var(--green-l);color:var(--green)}
.rl{margin-top:12px;border-top:1px solid var(--line);display:flex;flex-direction:column}
.rr{display:flex;align-items:center;gap:10px;height:44px;border-bottom:1px solid var(--line);font-size:13.5px}
.rr:last-child{border-bottom:0}.rr .m{font-family:ui-monospace,Menlo,monospace;font-size:13px;font-weight:600;flex:1}
.rr .s{color:var(--t2);font-size:12.5px}.rr .i{color:var(--t3)}
.rr.on{background:var(--blue-l);margin:0 -14px;padding:0 14px;border-bottom-color:transparent}
.rr.on .s{color:var(--blue);font-weight:600}.rr.on .i{color:var(--blue)}
.pb{height:6px;border-radius:3px;background:#E5E9F0;overflow:hidden}.pb>span{display:block;height:100%;background:var(--blue);border-radius:3px}
.cta{position:absolute;left:0;right:0;padding:12px 16px;display:flex;gap:10px;background:linear-gradient(rgba(243,245,248,0),var(--bg) 30%)}
.btn{height:52px;border-radius:14px;border:0;font:600 16px Inter,system-ui,sans-serif;display:flex;align-items:center;justify-content:center;
gap:8px;flex:1;cursor:pointer;-webkit-tap-highlight-color:transparent}
.btn .i{font-size:22px}
.cta[style*="column"] .btn{flex:none}
.btn.pri{background:var(--blue);color:#fff;box-shadow:0 6px 16px rgba(37,99,235,.28)}
.btn.sec{background:#fff;color:var(--ink);border:1.5px solid var(--line)}
.btn.ok{background:var(--green);color:#fff;box-shadow:0 6px 16px rgba(22,163,74,.28)}
.btn.dis{background:#CBD5E1;color:#fff;box-shadow:none}
.btn:focus-visible,.gbtn:focus-visible,.ib:focus-visible{outline:3px solid #93C5FD;outline-offset:2px}
.bn{position:absolute;bottom:0;left:0;right:0;height:72px;padding-bottom:16px;background:#fff;border-top:1px solid var(--line);
display:flex;justify-content:space-around;align-items:center}
.bn span{display:flex;flex-direction:column;align-items:center;gap:2px;font-size:11.5px;color:var(--t3);font-weight:500}
.bn span.on{color:var(--blue)}.bn .i{font-size:24px}
.tb{position:absolute;top:30px;left:0;right:0;height:60px;padding:0 12px;display:flex;align-items:center;gap:8px;background:var(--bg)}
.tb b{display:block;font-size:17px}.tb small{display:block;color:var(--t2);font-size:12.5px}
.ib{width:40px;height:40px;border-radius:20px;border:0;background:transparent;display:grid;place-items:center;color:var(--ink);cursor:pointer}
.ib .i{font-size:24px}
.h2{font-size:19px;font-weight:700}
.ck{display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}.ck:last-child{border-bottom:0}
.ck b{display:block;font-size:14.5px}.ck small{display:block;color:var(--t2);font-size:12.5px}
.tip{display:flex;gap:10px;align-items:center;background:var(--blue-l);border-radius:14px;padding:11px 12px;font-size:13px;color:#1E3A8A}
.tip .i{color:var(--blue)}.tip u{text-decoration:none;font-weight:600;color:var(--blue);white-space:nowrap}
.box{width:20px;height:20px;border-radius:6px;border:2px solid #CBD5E1;flex:none}
/* camera screens */
.cam{position:absolute;left:0;top:0;width:412px;height:892px;background-color:#0B1220;background-repeat:no-repeat;
background-size:412px auto}
.ov{position:absolute;left:0;width:412px;height:732.8px;overflow:visible;pointer-events:none}
.ov2{position:absolute;left:0;top:0;width:412px;height:892px;pointer-events:none;overflow:visible}
.shade{position:absolute;left:0;right:0;top:0;height:120px;background:linear-gradient(rgba(2,6,23,.55),rgba(2,6,23,0))}
.ctop{position:absolute;top:36px;left:12px;right:12px;display:flex;align-items:center;gap:8px;z-index:10}
.gbtn{width:42px;height:42px;border-radius:21px;border:0;background:var(--glass);backdrop-filter:blur(10px);color:#fff;
display:grid;place-items:center;cursor:pointer;flex:none}
.gbtn .i{font-size:22px}
.gpill{flex:1;height:42px;border-radius:21px;background:var(--glass);backdrop-filter:blur(10px);color:#fff;display:flex;
align-items:center;justify-content:space-between;padding:0 16px;font-size:13.5px;font-weight:600}
.seg{display:flex;gap:4px}.seg span{width:18px;height:5px;border-radius:3px;background:rgba(255,255,255,.3)}
.seg span.on{background:#fff}.seg span.done{background:var(--live)}
.sheet{position:absolute;left:0;right:0;bottom:0;background:#fff;border-radius:22px 22px 0 0;padding:10px 18px 30px;
box-shadow:0 -8px 30px rgba(2,6,23,.25);display:flex;flex-direction:column;gap:10px;z-index:15}
.sheet:before{content:"";display:block;width:40px;height:4px;border-radius:2px;background:#E2E8F0;margin:0 auto 2px}
.sheet h3{margin:0;font-size:18px;font-weight:700;line-height:1.25}.sheet p{margin:0;color:var(--t2);font-size:13.5px}
.btns{display:flex;gap:10px}
.tag{position:absolute;z-index:6;height:24px;padding:0 9px;border-radius:12px;font-size:12px;font-weight:600;display:flex;align-items:center;
gap:4px;white-space:nowrap}
.tag .i{font-size:15px}
.tag.blue{background:#2563EB;color:#fff}.tag.grey{background:rgba(15,23,42,.62);color:#fff}
.tag.dim{background:#fff;color:#15803D;font-size:14px;font-weight:700;height:28px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.3)}
.tag.dim.am{color:#B45309}
.ret{position:absolute;width:56px;height:56px;margin:-28px 0 0 -28px;z-index:7}
.hint{position:absolute;left:50%;width:84px;height:84px;margin-left:-42px;border-radius:42px;background:var(--glass);
backdrop-filter:blur(8px);display:grid;place-items:center;color:#fff;z-index:6}
.hint .i{font-size:44px;animation:sway 1.6s ease-in-out infinite}
@keyframes sway{0%,100%{transform:translateX(-14px)}50%{transform:translateX(14px)}}
.banner{position:absolute;top:88px;left:12px;right:12px;z-index:10;background:#F59E0B;color:#1F1300;border-radius:14px;padding:10px 14px;
display:flex;gap:10px;align-items:center;font-size:13px}
.banner b{display:block;font-size:15px}.banner .i{font-size:26px}
.ring,.row>.ring{width:58px;height:58px;flex:none;position:relative}.ring b{position:absolute;inset:0;display:grid;place-items:center;font-size:14px}
.chk{display:flex;gap:12px;font-size:12.5px;color:var(--t2);flex-wrap:wrap}.chk span{display:flex;align-items:center;gap:4px}
.chk .i{font-size:16px}.chk .y{color:var(--green)}.chk .w{color:var(--blue)}
.big{font-size:32px;font-weight:700;letter-spacing:-.02em;line-height:1.1}.big small{font-size:18px;color:var(--t2);font-weight:600}
.st3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.st3>div{background:var(--bg);border-radius:12px;padding:8px 10px}.st3 small{display:block;color:var(--t2);font-size:11.5px}
.st3 b{font-size:16px}
.field{background:#fff;border:2px solid var(--blue);border-radius:14px;height:64px;display:flex;align-items:center;padding:0 16px;gap:6px}
.field b{font-size:28px;flex:1}.field span{color:var(--t2);font-size:16px;font-weight:600}
.field b:after{content:"";display:inline-block;width:2px;height:28px;background:var(--blue);margin-left:2px;vertical-align:-4px;
animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.lab{font-size:13px;font-weight:600;color:var(--t2)}
.cmp{display:flex;flex-direction:column;gap:9px}
.cmp .r{display:flex;align-items:center;justify-content:space-between;font-size:14px}
.cmp .r small{display:block;color:var(--t3);font-size:12px}
.cmp .use{background:var(--green-l);border-radius:12px;padding:10px 12px;margin:2px -4px 0}
.cmp .use b{font-size:20px;color:var(--green)}
.done{display:flex;flex-direction:column;align-items:center;gap:6px;text-align:center}
.done .c{width:64px;height:64px;border-radius:32px;background:var(--green);display:grid;place-items:center;color:#fff;
box-shadow:0 0 0 10px var(--green-l)}
.done .c .i{font-size:40px}.done b{font-size:21px;margin-top:10px}.done small{color:var(--t2);font-size:13px}
.kv{display:flex;flex-direction:column;gap:7px;font-size:13px}.kv div{display:flex;flex-direction:column}
.kv small{color:var(--t3);font-size:11.5px}.kv b{font-size:14px}
.thumb{width:122px;height:206px;border-radius:12px;background-size:cover;background-position:center;flex:none}
.ex{height:150px;border-radius:14px;background-size:cover;background-position:center 58%;position:relative;overflow:hidden}
.ex .chip{position:absolute;left:10px;bottom:10px}
"""


def fontcss(proto: bool) -> str:
    if proto:
        ms = base64.b64encode((HERE / "fonts" / "MaterialSymbolsRounded.ttf").read_bytes()).decode()
        return f"@font-face{{font-family:MSR;src:url(data:font/ttf;base64,{ms}) format('truetype');font-display:block}}\n"
    f = "\n".join(f"@font-face{{font-family:Inter;src:url({(INTER / f'Inter-{n}.ttf').as_uri()});font-weight:{w}}}"
                  for n, w in (("Regular", 400), ("Medium", 500), ("SemiBold", 600), ("Bold", 700)))
    return f + f"\n@font-face{{font-family:MSR;src:url({(HERE / 'fonts' / 'MaterialSymbolsRounded.ttf').as_uri()})}}\n"


# ------------------------------------------------------------- geometry ----
def P(pts):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def at(x, y, oy):
    """Photo pixel -> screen CSS px for a camera view shifted by oy."""
    return x * K, y * K + oy


rng = random.Random(3)
CX, CY = np.mean(np.array(G["outline"], float), 0)
DOTS = sorted(G["dots"], key=lambda p: np.hypot(p[0] - CX, p[1] - CY) + rng.uniform(0, 160))
GRID = sorted(G["grid"], key=lambda p: abs(p[0] - 450) * .6 + abs(p[1] - 1599) + rng.uniform(0, 140))


def svg(oy, inner):
    return (f'<svg class="ov" style="top:{oy:.1f}px" viewBox="0 0 {PW} {PH}" preserveAspectRatio="none" '
            f'xmlns="http://www.w3.org/2000/svg">{inner}</svg>')


def grid_dots(frac=1.0):
    n = len(GRID)
    return "".join(f'<circle class="gd" data-r="{k / n:.3f}" cx="{x}" cy="{y}" r="5" fill="#fff" '
                   f'opacity="{.9 if k < frac * n else 0}"/>' for k, (x, y) in enumerate(GRID))


def depth_dots(frac):
    n = len(DOTS)
    return "".join(f'<circle class="dd" data-r="{k / n:.3f}" cx="{x}" cy="{y}" r="4.5" fill="#22D3EE" '
                   f'opacity="{.95 if k < frac * n else 0}"/>' for k, (x, y) in enumerate(DOTS))


def outline(color, fill, w=7, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polygon points="{P(G["outline"])}" fill="{fill}" stroke="{color}" stroke-width="{w}" '
            f'stroke-linejoin="round"{d}/>')


def others():
    return "".join(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="12" fill="rgba(255,255,255,.06)" '
                   f'stroke="#fff" stroke-width="5" stroke-dasharray="18 12" opacity=".85"/>'
                   for x0, y0, x1, y1 in G["others"])


def wire(color):
    t, b = G["top"], G["base"]
    s = f'<polygon points="{P(b)}" fill="none" stroke="{color}" stroke-width="5" stroke-dasharray="16 10" opacity=".9"/>'
    s += "".join(f'<line x1="{t[k][0]}" y1="{t[k][1]}" x2="{b[k][0]}" y2="{b[k][1]}" stroke="{color}" stroke-width="5"/>'
                 for k in range(4))
    s += f'<polygon points="{P(t)}" fill="{color}" fill-opacity=".10" stroke="{color}" stroke-width="8" stroke-linejoin="round"/>'
    s += "".join(f'<circle cx="{x}" cy="{y}" r="11" fill="#fff" stroke="{color}" stroke-width="5"/>' for x, y in t)
    return s


def dim_tags(oy, amber=False):
    t, b = G["top"], G["base"]
    cls = "tag dim am" if amber else "tag dim"
    mid = lambda p, q: ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    x, y = at(*mid(t[0], t[1]), oy)
    s = f'<span class="{cls}" style="left:{x - 34:.0f}px;top:{y + 10:.0f}px">{Wd} cm</span>'
    x, y = at(*mid(t[0], t[3]), oy)
    s += f'<span class="{cls}" style="left:{x + 12:.0f}px;top:{y - 14:.0f}px">{L} cm</span>'
    x, y = at(*mid(t[1], b[1]), oy)
    s += f'<span class="{cls}" style="left:{x - 76:.0f}px;top:{y + 4:.0f}px">{Ht} cm</span>'
    return s


# --------------------------------------------------------------- pieces ----
def sb(dark=False):
    return (f'<div class="sb{" dk" if dark else ""}"><span class="tn">09:41</span>'
            f'<span>{i("signal_cellular_alt", True)}{i("wifi", True)}{i("battery_full", True)}</span></div>')


def gb(dark=False):
    return f'<div class="gb{" dk" if dark else ""}"></div>'


def ctop(step, title, right="", back="1"):
    seg = "".join(f'<span class="{"done" if k < step else "on" if k == step else ""}"></span>' for k in (1, 2, 3))
    label = f"{step}/3 · {title}" if step else title
    seg_html = f'<span class="seg">{seg}</span>' if step else ""
    return (f'<div class="shade"></div><div class="ctop"><button class="gbtn" data-go="{back}" aria-label="Kembali">'
            f'{i("arrow_back")}</button><div class="gpill"><span>{label}</span>{seg_html}</div>{right}</div>')


def cam(oy):
    return f'<div class="cam" style="background-position:0 {oy:.1f}px"></div>'


def ring(pct, color="#2563EB"):
    c = 2 * np.pi * 24
    return (f'<div class="ring"><svg width="58" height="58" viewBox="0 0 58 58"><circle cx="29" cy="29" r="24" fill="none" '
            f'stroke="#E2E8F0" stroke-width="6"/><circle class="rg" cx="29" cy="29" r="24" fill="none" stroke="{color}" '
            f'stroke-width="6" stroke-linecap="round" stroke-dasharray="{c:.1f}" stroke-dashoffset="{c * (1 - pct):.1f}" '
            f'transform="rotate(-90 29 29)"/></svg><b class="tn rp">{int(pct * 100)}%</b></div>')


def reticle(x, y):
    return (f'<svg class="ret" style="left:{x}px;top:{y}px" viewBox="0 0 56 56"><circle cx="28" cy="28" r="20" fill="none" '
            f'stroke="#fff" stroke-width="3"/><circle cx="28" cy="28" r="4" fill="#fff"/><path d="M28 2v8M28 46v8M2 28h8M46 28h8" '
            f'stroke="#fff" stroke-width="3" stroke-linecap="round"/></svg>')


# -------------------------------------------------------------- screens ----
def s1():
    rows = [("UKP-260419-0007", "Belum diukur", True), ("UKP-260419-0008", "Belum diukur", False),
            ("UKP-260419-0009", "Belum diukur", False)]
    rl = "".join(f'<div class="rr{" on" if on else ""}" data-go="2">{i("qr_code_2")}<span class="m tn">{r}</span>'
                 f'<span class="s">{s}</span>{i("chevron_right")}</div>' for r, s, on in rows)
    return f"""{sb()}
<div class="ah"><div class="brand"><span class="logo">{i("deployed_code", True)}</span><div><b>UkurPaket</b>
<small>Andi · Kurir pickup</small></div></div><span class="chip ok">{i("cloud_done", True)}Tersinkron</span></div>
<div class="body" style="top:100px">
<div class="h1">Pickup hari ini</div><div class="sub">Senin, 19 Okt · 3 lokasi · 7 paket</div>
<div><div class="row" style="justify-content:space-between;font-size:12.5px;color:var(--t2);margin-bottom:6px">
<span>Paket sudah diukur</span><b class="tn" style="flex:none;font-size:12.5px;color:var(--ink)">1 dari 7</b></div>
<div class="pb"><span style="width:14%"></span></div></div>
<div class="card act"><div class="row"><span class="ico b">{i("storefront", True)}</span><div><b>Toko Sinar Jaya</b>
<small>Jl. Contoh Raya No. 12 · 1,2 km</small></div><span class="chip blue">Berikutnya</span></div>
<div class="rl">{rl}</div></div>
<div class="card"><div class="row"><span class="ico g">{i("home", True)}</span><div><b>Rumah · Ibu Rina</b>
<small>1 paket · 30 × 20 × 12 cm</small></div><span class="chip ok">{i("check_circle", True)}Selesai</span></div></div>
<div class="card"><div class="row"><span class="ico">{i("inventory_2", True)}</span><div><b>Gudang Mitra Cikarang</b>
<small>3 paket · jadwal 13:00</small></div><span class="chip grey">Nanti</span></div></div>
</div>
<div class="cta" style="bottom:72px"><button class="btn pri" data-go="2">{i("barcode_scanner")}Scan resi untuk ukur</button></div>
<nav class="bn"><span class="on">{i("local_shipping", True)}Pickup</span><span>{i("history")}Riwayat</span><span>{i("person")}Akun</span></nav>
{gb()}"""


def s2():
    checks = [("inventory_2", "Taruh paket di lantai atau meja", "Bidang datar, jangan di atas paket lain"),
              ("crop_free", "Satu paket, tidak menempel", "Geser sedikit kalau berdempetan"),
              ("directions_walk", "Mundur sekitar 1 langkah", "Seluruh paket terlihat di layar"),
              ("light_mode", "Tempat cukup terang", "Nyalakan senter kalau gelap")]
    ck = "".join(f'<div class="ck"><span class="ico b">{i(n, True)}</span><div><b>{t}</b><small>{s}</small></div></div>'
                 for n, t, s in checks)
    return f"""{sb()}
<div class="tb"><button class="ib" data-go="1" aria-label="Kembali">{i("arrow_back")}</button><div><b>Ukur paket</b>
<small class="tn">{RESI} · Toko Sinar Jaya</small></div></div>
<div class="body" style="top:96px">
<div class="ex" style="background-image:var(--ex)"><span class="chip ok">{i("check_circle", True)}Contoh posisi yang benar</span></div>
<div class="h2">Sebelum mulai</div>
<div class="card" style="padding:4px 14px">{ck}</div>
<div class="tip">{i("front_hand", True)}<span>Paket kecil bisa diukur sambil dipegang.</span><u data-toast="Mode pegang: pegang paket dengan satu sudut menghadap kamera. Label resi dipakai sebagai penggaris.">Ukur cara lain</u></div>
<div class="row" style="gap:10px;font-size:13px;color:var(--t2)"><span class="box"></span>
<span style="flex:1">Jangan tampilkan lagi <span style="color:var(--t3)">(muncul 3 kali pertama)</span></span></div>
</div>
<div class="cta" style="bottom:16px"><button class="btn pri" data-go="3">{i("photo_camera", True)}Mulai ukur</button></div>
{gb()}"""


def s3(proto=False):
    oy = 0
    found = not proto
    chip = (f'<span class="chip ok s3c">{i("check_circle", True)}Alas terdeteksi</span>' if found else
            f'<span class="chip warn s3c">{i("sync")}Mencari alas…</span>')
    return f"""{cam(oy)}{svg(oy, grid_dots(1.0 if found else 0))}
{sb(True)}{ctop(1, "Cari alas", f'<button class="gbtn" data-toast="Senter menyala">{i("flashlight_on", True)}</button>', "2")}
<div class="hint" style="top:300px">{i("swipe")}</div>
<div class="sheet">
<div>{chip}</div>
<h3>Gerakkan HP pelan ke kiri dan kanan</h3>
<p>Titik putih muncul di lantai berarti alas sudah dikenali.</p>
<div class="btns"><button class="btn {"pri" if found else "dis"} s3b" data-go="4">{i("arrow_forward")}Lanjut pilih paket</button></div>
</div>{gb(True)}"""


def s4():
    oy = 0
    tags = "".join(f'<span class="tag grey" data-toast="Paket lain tidak ikut diukur. Ketuk paket ini untuk memilihnya." '
                   f'style="left:{at(x0, 0, oy)[0] + 10:.0f}px;top:{max(at(0, y1, oy)[1] - 34, 96):.0f}px;pointer-events:auto">'
                   f'{i("inventory_2")}Paket lain</span>' for x0, y0, x1, y1 in G["others"])
    xs, ys = zip(*G["outline"])
    tx, ty = at(min(xs), min(ys), oy)
    return f"""{cam(oy)}{svg(oy, others() + outline("#3B82F6", "rgba(59,130,246,.16)"))}
{sb(True)}{ctop(2, "Pilih paket", f'<button class="gbtn" data-toast="Gambar kotak: seret jari di sekeliling paket, seperti snipping tool.">{i("crop")}</button>', "3")}
{tags}<span class="tag blue" style="left:{tx + 12:.0f}px;top:{ty + 12:.0f}px">{i("check_circle", True)}Paket terpilih</span>
{reticle(206, 420)}
<div class="sheet">
<h3>Arahkan titik ke paket</h3>
<p>Garis biru = paket yang akan diukur. Bukan paket ini? Ketuk paket yang benar.</p>
<div class="btns"><button class="btn sec" style="flex:.8" data-toast="Gambar kotak: seret jari di sekeliling paket, seperti snipping tool.">{i("crop")}Gambar kotak</button>
<button class="btn pri" data-go="5">{i("lock", True)}Kunci paket</button></div>
</div>{gb(True)}"""


def arc():
    return ('<svg class="ov2" viewBox="0 0 412 892"><path class="arc" d="M236 628 C 330 640, 392 590, 392 500" fill="none" '
            'stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-dasharray="10 9"/>'
            '<path d="M380 512 L392 492 L404 512" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" '
            'stroke-linejoin="round"/></svg>')


def s5(pct=.64, proto=False):
    oy = -59
    frac = 0 if proto else pct
    return f"""{cam(oy)}{svg(oy, outline("#22C55E", "rgba(34,197,94,.10)", 6) + depth_dots(frac))}{arc()}
{sb(True)}{ctop(3, "Pindai", "", "4")}
<span class="tag grey s5slow" style="left:150px;top:96px;{"display:none" if proto else "display:none"}">{i("timer")}Pelan-pelan</span>
<div class="sheet">
<div class="row" style="gap:14px">{ring(frac)}<div><h3>Geser HP pelan memutar ke sudut paket</h3></div></div>
<div class="chk"><span class="y">{i("check_circle", True)}Alas</span><span class="y">{i("check_circle", True)}Paket terkunci</span>
<span class="w">{i("deployed_code", True)}Kedalaman <b class="tn rp2">{int(frac * 100)}%</b></span></div>
<div class="btns"><button class="btn sec s5r" data-go="5">{i("refresh")}Ulangi pindai</button></div>
</div>{gb(True)}"""


def s5b():
    oy = 30
    return f"""{cam(oy)}{svg(oy, outline("#F59E0B", "rgba(245,158,11,.10)", 6) + depth_dots(.38))}
{sb(True)}{ctop(3, "Pindai", "", "4")}
<div class="banner">{i("warning", True)}<div><b>Mundur sedikit</b>Bagian bawah paket terpotong layar.</div></div>
<div class="sheet">
<div class="row" style="gap:14px">{ring(.38, "#94A3B8")}<div><h3>Pindai dijeda</h3>
<p>Lanjut otomatis setelah seluruh paket terlihat.</p></div></div>
<div class="chk"><span class="y">{i("check_circle", True)}Alas</span><span class="y">{i("check_circle", True)}Paket terkunci</span>
<span style="color:var(--amber)">{i("warning", True)}Paket terpotong</span></div>
<div class="btns"><button class="btn sec" data-go="5">{i("refresh")}Ulangi pindai</button></div>
</div>{gb(True)}"""


def s6(check=False):
    oy = -59
    col = "#F59E0B" if check else "#22C55E"
    status = (f'<span class="chip warn">{i("warning", True)}Cek ulang · tepi kurang jelas</span>' if check else
              f'<span class="chip ok">{i("check_circle", True)}Akurat · keyakinan 92%</span>')
    note = ('<p>Plastik hitam mengkilap. Pastikan kotak pas membungkus paket, atau ulangi dari sudut lain.</p>'
            if check else "")
    save = (f'<button class="btn dis" data-go="7">{i("check")}Simpan (2)</button>' if check else
            f'<button class="btn ok" data-go="7">{i("check")}Simpan</button>')
    return f"""{cam(oy)}{svg(oy, wire(col))}{dim_tags(oy, check)}
{sb(True)}{ctop(0, "Hasil ukur", f'<button class="gbtn" data-toast="Ukur cara lain: mode pegang, kertas A4 sebagai penggaris, atau isi manual (masuk audit).">{i("more_vert")}</button>', "5")}
<div class="sheet">
<div class="row" style="justify-content:space-between">{status}<span class="tn" style="flex:none;color:var(--t3);font-size:12px">…0007</span></div>
<div class="big tn">{L} × {Wd} × {Ht} <small>cm</small></div>{note}
<div class="st3"><div><small>Volume</small><b class="tn">{num(VOL)} L</b></div><div><small>Berat volumetrik</small>
<b class="tn">{num(VOLW, 2)} kg</b></div><div><small>Waktu ukur</small><b class="tn">8 dtk</b></div></div>
<div class="btns"><button class="btn sec" style="flex:.7" data-go="5">{i("refresh")}Ulangi</button>{save}</div>
</div>{gb(True)}"""


def s7():
    return f"""{sb()}
<div class="tb"><button class="ib" data-go="6" aria-label="Kembali">{i("arrow_back")}</button><div><b>Berat paket</b>
<small class="tn">{RESI}</small></div></div>
<div class="body" style="top:96px">
<div class="card row"><span class="thumb" style="width:58px;height:84px;border-radius:10px;background-image:var(--th)"></span>
<div><b class="tn" style="font-size:18px">{L} × {Wd} × {Ht} cm</b><small>Volume {num(VOL)} L · diukur AR di lantai</small></div>
<span class="chip ok">{i("check_circle", True)}Akurat</span></div>
<div style="display:flex;flex-direction:column;gap:8px"><span class="lab">Berat timbangan</span>
<div class="field"><b class="tn">0,10</b><span>kg</span></div>
<div class="row" style="gap:8px;font-size:12.5px;color:var(--t2)"><span style="flex:1">Ketik dari timbangan, atau hubungkan timbangan Bluetooth.</span>
<span class="chip blue" data-toast="Mencari timbangan Bluetooth di sekitar…">{i("bluetooth")}Hubungkan</span></div></div>
<div class="card cmp">
<div class="r"><span>Berat timbangan</span><b class="tn">0,10 kg</b></div>
<div class="r"><span>Berat volumetrik<small class="tn">{L} × {Wd} × {Ht} ÷ 6.000</small></span><b class="tn">{num(VOLW, 2)} kg</b></div>
<div class="r use"><span><b style="font-size:14px;color:var(--ink)">Berat dipakai</b><small>volumetrik lebih besar</small></span>
<b class="tn">{num(VOLW, 2)} kg</b></div>
</div>
<div style="font-size:12px;color:var(--t3)">{i("info", False, "")} Pembagi 6.000 untuk layanan Reguler, diatur oleh admin.</div>
</div>
<div class="cta" style="bottom:16px"><button class="btn pri" data-go="8">Lanjut{i("arrow_forward")}</button></div>
{gb()}"""


def s8():
    return f"""{sb()}
<div class="body" style="top:58px">
<div class="done"><span class="c">{i("check", True)}</span><b>Paket tersimpan</b><small>Paket 1 dari 3 · Toko Sinar Jaya</small></div>
<div class="card row" style="align-items:stretch;gap:14px"><span class="thumb" style="background-image:var(--th)"></span>
<div class="kv"><div><small>Resi</small><b class="tn">{RESI}</b></div><div><small>Ukuran</small><b class="tn">{L} × {Wd} × {Ht} cm</b></div>
<div><small>Berat dipakai</small><b class="tn">{num(VOLW, 2)} kg · volumetrik</b></div><div><small>Cara ukur</small><b>AR di lantai · 92%</b></div>
<div><small>Waktu & lokasi</small><b class="tn">09:42 · GPS tercatat</b></div></div></div>
<div class="row" style="gap:8px;flex-wrap:wrap"><span class="chip warn">{i("cloud_upload", True)}Menunggu sinyal · terkirim otomatis</span></div>
<div style="font-size:12.5px;color:var(--t2)">Foto, kotak 3D, ukuran, waktu, dan GPS disimpan sebagai bukti. Angka ukur tidak bisa diedit.</div>
<div><div class="row" style="justify-content:space-between;font-size:12.5px;color:var(--t2);margin-bottom:6px"><span>Toko Sinar Jaya</span>
<b class="tn" style="flex:none;font-size:12.5px;color:var(--ink)">1 dari 3 paket</b></div><div class="pb"><span style="width:33%"></span></div></div>
</div>
<div class="cta" style="bottom:16px;flex-direction:column;gap:8px"><button class="btn pri" data-go="4" data-toast="Alas sudah dikenali · paket 2 dari 3">{i("arrow_forward")}Paket berikutnya</button>
<button class="btn sec" data-go="1">Selesai pickup</button></div>
{gb()}"""


SCREENS = [  # id, file name, title, one-line caption, function
    ("1", "01_pilih_order", "Pilih order", "Scan resi, ukuran langsung terikat ke resi", s1),
    ("2", "02_persiapan", "Persiapan", "4 aturan bergambar, muncul 3 kali pertama", s2),
    ("3", "03_cari_alas", "Cari alas", "Gerakkan HP sampai titik muncul di lantai", s3),
    ("4", "04_pilih_paket", "Pilih paket", "Titik bidik + ketuk; paket lain diabaikan", s4),
    ("5", "05_pindai", "Pindai", "Geser HP memutar ke sudut, 2–3 detik", s5),
    ("6", "06_hasil", "Hasil", "Kotak 3D menempel di paket + P × L × T", s6),
    ("7", "07_berat", "Berat", "Berat timbangan vs volumetrik, dipakai yang lebih besar", s7),
    ("8", "08_tersimpan", "Tersimpan", "Bukti tersimpan, terkirim saat ada sinyal", s8),
    ("5b", "05b_peringatan", "Peringatan saat pindai", "Contoh: paket terpotong layar", s5b),
    ("6b", "06b_cek_ulang", "Hasil perlu dicek", "Contoh: plastik hitam, tepi kurang jelas", lambda: s6(True)),
]
CAM = {"3", "4", "5", "6", "5b", "6b"}


# ---------------------------------------------------------------- pages ----
def images():
    """Small pictures used on the light screens: the example on screen 2, the 3D-box thumbnail."""
    im = cv2.imread(str(IMG / "paket.jpg"))
    ex = cv2.resize(im[560:1240, 0:899], (720, 544), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(IMG / "contoh.jpg"), ex, [cv2.IMWRITE_JPEG_QUALITY, 85])
    th = im.copy()
    t, b = np.int32(G["top"]), np.int32(G["base"])
    cv2.polylines(th, [b], True, (94, 197, 34), 5, cv2.LINE_AA)
    for k in range(4):
        cv2.line(th, tuple(t[k]), tuple(b[k]), (94, 197, 34), 5, cv2.LINE_AA)
    cv2.polylines(th, [t], True, (94, 197, 34), 9, cv2.LINE_AA)
    th = cv2.resize(th[250:1599, 90:860], (366, 642), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(IMG / "thumb.jpg"), th, [cv2.IMWRITE_JPEG_QUALITY, 85])


def uri(p):
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()


def picvars(proto):
    if proto:
        return (f".cam{{background-image:url({uri(IMG / 'paket.jpg')})}}\n"
                f":root{{--ex:url({uri(IMG / 'contoh.jpg')});--th:url({uri(IMG / 'thumb.jpg')})}}\n")
    return (f".cam{{background-image:url({(IMG / 'paket.jpg').as_uri()})}}\n"
            f":root{{--ex:url({(IMG / 'contoh.jpg').as_uri()});--th:url({(IMG / 'thumb.jpg').as_uri()})}}\n")


def screen_page(fn):
    return (f"<!doctype html><html lang='id'><head><meta charset='utf-8'><style>{fontcss(False)}{CSS}{picvars(False)}"
            f"html,body{{margin:0;background:#000}}</style></head><body><div class='screen'>{fn()}</div></body></html>")


def board():
    phones = "".join(
        f'<div class="ph"><div class="num">{n}</div><div class="frame"><div class="scr"><div class="screen">{fn()}</div></div></div>'
        f'<div class="cap"><b>{t}</b><small>{c}</small></div></div>' for n, f_, t, c, fn in SCREENS[:8])
    return f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><style>{fontcss(False)}{CSS}{picvars(False)}
html,body{{margin:0}}body{{width:1920px;height:1080px;background:#F3F5F8;font-family:Inter,sans-serif;color:#0F172A;position:relative;overflow:hidden}}
.hd{{position:absolute;left:56px;top:44px;right:56px}}
.ey{{font-size:13px;font-weight:700;letter-spacing:.12em;color:#2563EB}}
.hd h1{{margin:8px 0 6px;font-size:38px;letter-spacing:-.02em}}.hd p{{margin:0;font-size:17px;color:#475569}}
.rowp{{position:absolute;left:56px;right:56px;top:196px;display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:16px}}
.ph{{display:flex;flex-direction:column;align-items:center;min-width:0}}
.num{{width:34px;height:34px;border-radius:17px;background:#2563EB;color:#fff;font-weight:700;display:grid;place-items:center;
font-size:16px;margin-bottom:12px}}
.frame{{width:204px;height:426px;border-radius:30px;background:#0F172A;padding:7px;box-shadow:0 14px 30px rgba(15,23,42,.18)}}
.scr{{width:190px;height:412px;border-radius:24px;overflow:hidden;position:relative}}
.scr .screen{{transform:scale(.46117);transform-origin:0 0;position:absolute;left:0;top:-.5px}}
.cap{{text-align:center;margin-top:14px;max-width:212px}}.cap b{{display:block;font-size:17px}}.cap small{{display:block;margin-top:4px;font-size:13.5px;color:#475569;line-height:1.35}}
.ft{{position:absolute;left:56px;right:56px;bottom:34px;font-size:13px;color:#94A3B8;display:flex;justify-content:space-between}}
.flow{{position:absolute;left:56px;right:56px;top:836px;display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.flow div{{background:#fff;border:1px solid #E2E8F0;border-radius:16px;padding:16px 18px;font-size:14.5px;color:#475569}}
.flow b{{display:block;color:#0F172A;font-size:16px;margin-bottom:4px}}
</style></head><body>
<div class="hd"><div class="ey">UKURPAKET · ALUR KURIR</div><h1>Mengukur P × L × T paket dengan kamera HP</h1>
<p>Mode utama AR di lantai: sekitar 10 detik untuk paket pertama, sekitar 5 detik untuk paket berikutnya di lokasi yang sama. Tetap jalan tanpa sinyal.</p></div>
<div class="rowp">{phones}</div>
<div class="flow"><div><b>Kalau hasil meragukan</b>Status kuning, tombol Simpan dikunci 2 detik, kurir diminta cek kotak 3D atau ulangi dari sudut lain.</div>
<div><b>Kalau alas tidak terdeteksi</b>Pindah ke mode pegang (label resi sebagai penggaris), kertas A4, atau isi manual yang masuk audit.</div>
<div><b>Banyak paket di satu lokasi</b>Setelah Simpan, langsung ke langkah 4. Alas sudah dikenali, paket yang sudah diukur diberi tanda.</div></div>
<div class="ft"><span>Foto paket asli, label resi disamarkan. Ukuran di layar adalah ilustrasi untuk uji alur, bukan hasil ukur.</span>
<span>Mockup konsep · UkurPaket</span></div>
</body></html>"""


def prototype():
    list_items = "".join(f'<button class="li" data-go="{n}"><span class="n">{n}</span><span><b>{t}</b><small>{c}</small></span></button>'
                         for n, f_, t, c, fn in SCREENS)
    screens = "".join(f'<div class="screen" id="s{n}" data-id="{n}"{" hidden" if n != "1" else ""}>'
                      f'{fn(proto=True) if fn in (s3, s5) else fn()}</div>' for n, f_, t, c, fn in SCREENS)
    return f"""<title>UkurPaket Prototipe</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<style>
/* Layout: a dark stage with the phone in the middle; on a desktop a side panel lists every screen. */
:root{{--stage:#0E1525;--panel:#151F33;--ptext:#E6ECF5;--pmuted:#94A3B8;--paccent:#60A5FA;--pline:#24324D;color-scheme:dark}}
[hidden]{{display:none!important}}
html,body{{height:100%}}
body{{background:var(--stage);color:var(--ptext);font-family:Inter,system-ui,sans-serif;margin:0;overflow:hidden}}
{fontcss(True)}{CSS}{picvars(True)}
.wrap{{height:100%;display:flex;gap:40px;align-items:center;justify-content:center;padding-block:16px;
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));box-sizing:border-box}}
.side{{width:330px;max-height:100%;overflow:auto;display:flex;flex-direction:column;gap:14px}}
.side h1{{margin:0;font-size:24px;letter-spacing:-.01em}}.side p{{margin:0;color:var(--pmuted);font-size:13.5px;line-height:1.5}}
.ey{{font-size:11.5px;font-weight:700;letter-spacing:.12em;color:var(--paccent)}}
.how{{background:var(--panel);border:1px solid var(--pline);border-radius:14px;padding:12px 14px;font-size:13px;color:var(--pmuted);line-height:1.5}}
.how b{{color:var(--ptext)}}
.list{{display:flex;flex-direction:column;gap:4px}}
.li{{display:flex;gap:10px;align-items:flex-start;text-align:left;background:transparent;border:1px solid transparent;border-radius:12px;
padding:8px 10px;color:var(--ptext);cursor:pointer;font:inherit}}
.li:hover{{background:var(--panel)}}.li.on{{background:var(--panel);border-color:var(--pline)}}
.li:focus-visible{{outline:2px solid var(--paccent)}}
.li .n{{width:26px;height:26px;border-radius:13px;background:#24324D;display:grid;place-items:center;font-size:12px;font-weight:700;flex:none}}
.li.on .n{{background:#2563EB}}
.li b{{display:block;font-size:13.5px}}.li small{{display:block;color:var(--pmuted);font-size:12px}}
.devbox{{position:relative;flex:none}}
.device{{position:absolute;left:0;top:0;width:412px;height:892px;transform-origin:0 0;border-radius:34px;overflow:hidden;
box-shadow:0 0 0 10px #05080F,0 30px 60px rgba(0,0,0,.5)}}
.toast{{position:absolute;left:50%;top:100px;transform:translateX(-50%);z-index:50;width:360px;max-width:88%;background:#0F172A;color:#fff;
border-radius:14px;padding:11px 14px;font-size:13.5px;line-height:1.4;box-shadow:0 10px 30px rgba(0,0,0,.4);opacity:0;transition:opacity .2s;
pointer-events:none}}
.toast.on{{opacity:1}}
.menu{{position:absolute;top:5px;left:50%;transform:translateX(-50%);z-index:60;height:22px;padding:0 10px;border-radius:11px;border:0;
background:rgba(37,99,235,.92);color:#fff;font:600 11px Inter,system-ui,sans-serif;cursor:pointer;display:none}}
.drawer{{position:fixed;inset:0;background:rgba(2,6,23,.6);z-index:100;display:flex;align-items:flex-end}}
.drawer .in{{background:var(--panel);width:100%;max-height:75%;overflow:auto;border-radius:18px 18px 0 0;padding:14px;
padding-bottom:calc(14px + env(safe-area-inset-bottom,0px));padding-left:max(14px,env(safe-area-inset-left,0px));
padding-right:max(14px,env(safe-area-inset-right,0px))}}
[data-go],[data-toast]{{cursor:pointer}}
@media (max-width:760px){{.side{{display:none}}.wrap{{padding:0}}.device{{border-radius:0;box-shadow:none}}.menu{{display:block}}}}
@media (prefers-reduced-motion:reduce){{.hint .i,.field b:after{{animation:none}}}}
</style>
<div class="wrap">
<aside class="side"><div class="ey">PROTOTIPE · UNTUK UJI KURIR</div><h1>UkurPaket</h1>
<p>Alur mengukur P × L × T paket dengan kamera HP. Tombol di layar bisa diketuk seperti aplikasi asli; langkah 3 dan 5 berjalan otomatis.</p>
<div class="how"><b>Cara uji:</b> beri HP ke kurir, minta ukur paket dari layar 1 tanpa dibantu. Catat di langkah mana kurir ragu, salah ketuk, atau bertanya. Buka dari HP untuk tampilan layar penuh.</div>
<div class="list">{list_items}</div>
<p style="font-size:12px">Foto paket asli, label resi disamarkan. Ukuran di layar adalah ilustrasi, bukan hasil ukur.</p></aside>
<div class="devbox" id="devbox"><div class="device" id="device">{screens}
<button class="menu" id="menu">Prototipe · daftar layar</button><div class="toast" id="toast"></div></div></div>
</div>
<div class="drawer" id="drawer" hidden><div class="in"><div class="list">{list_items}</div></div></div>
<script>
(function(){{
const dev=document.getElementById('device'),box=document.getElementById('devbox'),toastEl=document.getElementById('toast');
const reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
let timers=[];function later(f,ms){{timers.push(setTimeout(f,ms))}}
function fit(){{const narrow=innerWidth<=760;const aw=narrow?innerWidth:innerWidth-420,ah=innerHeight-(narrow?0:40);
const k=Math.min(aw/412,ah/892,narrow?4:1.05);dev.style.transform='scale('+k+')';box.style.width=412*k+'px';box.style.height=892*k+'px'}}
addEventListener('resize',fit);fit();
let tt;function toast(m){{toastEl.textContent=m;toastEl.classList.add('on');clearTimeout(tt);tt=setTimeout(()=>toastEl.classList.remove('on'),2600)}}
function setDots(sel,frac){{dev.querySelectorAll(sel).forEach(c=>{{c.setAttribute('opacity',(+c.dataset.r<frac)?(sel=='.gd'?.9:.95):0)}})}}
function anim(ms,step,done){{if(reduce){{step(1);done&&done();return}}const t0=performance.now();
(function f(t){{const p=Math.min(1,(t-t0)/ms);step(p);if(p<1)timers.push(requestAnimationFrame(f));else done&&done()}})(t0)}}
const hooks={{
 '3':s=>{{const chip=s.querySelector('.s3c'),btn=s.querySelector('.s3b');setDots('#s3 .gd',0);
   chip.className='chip warn s3c';chip.innerHTML='<i class="i">sync</i>Mencari alas…';btn.className='btn dis s3b';
   later(()=>anim(1600,p=>setDots('#s3 .gd',p),()=>{{chip.className='chip ok s3c';chip.innerHTML='<i class="i f">check_circle</i>Alas terdeteksi';
     btn.className='btn pri s3b';later(()=>{{if(cur=='3')go('4')}},1400)}}),600)}},
 '5':s=>{{const ring=s.querySelector('.rg'),rp=s.querySelector('.rp'),rp2=s.querySelector('.rp2'),slow=s.querySelector('.s5slow');
   const C=2*Math.PI*24;setDots('#s5 .dd',0);slow.style.display='none';
   anim(3600,p=>{{ring.setAttribute('stroke-dashoffset',C*(1-p));rp.textContent=Math.round(p*100)+'%';rp2.textContent=Math.round(p*100)+'%';
     setDots('#s5 .dd',p);slow.style.display=(p>.3&&p<.45)?'flex':'none'}},()=>later(()=>{{if(cur=='5')go('6')}},500))}}
}};
let cur='1';
function go(id){{timers.forEach(t=>{{clearTimeout(t);cancelAnimationFrame(t)}});timers=[];
 dev.querySelectorAll('.screen').forEach(s=>s.hidden=s.dataset.id!==id);cur=id;
 document.querySelectorAll('.li').forEach(b=>b.classList.toggle('on',b.dataset.go===id));
 document.getElementById('drawer').hidden=true;const s=document.getElementById('s'+id);hooks[id]&&hooks[id](s)}}
document.addEventListener('click',e=>{{
 if(e.target.closest('#menu')){{document.getElementById('drawer').hidden=false;return}}
 if(e.target.id==='drawer'){{e.target.hidden=true;return}}
 const g=e.target.closest('[data-go]'),t=e.target.closest('[data-toast]');
 if(g&&g.classList.contains('dis')){{toast(g.classList.contains('s3b')?'Tunggu sampai alas terdeteksi.':'Cek dulu kotak hijau di paket.');return}}
 if(g){{go(g.dataset.go)}}if(t){{toast(t.dataset.toast)}}}});
go('1');
}})();
</script>"""


# ----------------------------------------------------------------- shoot ----
def chrome():
    for c in [os.environ.get("CHROME", "")] + sorted(glob.glob("/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell")):
        if c and Path(c).exists():
            return c
    sys.exit("headless Chromium not found: set CHROME=/path/to/headless_shell")


def shoot(html, png, w, h, scale):
    subprocess.run([chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    f"--force-device-scale-factor={scale}", f"--window-size={w},{h}", "--virtual-time-budget=3000",
                    f"--screenshot={png}", html.as_uri()], check=True, capture_output=True, timeout=120)


def main(argv):
    for d in (HTML, OUT, PROTO):
        d.mkdir(exist_ok=True)
    images()
    pages = []
    for n, f, t, c, fn in SCREENS:
        p = HTML / f"{f}.html"
        p.write_text(screen_page(fn))
        pages.append((p, OUT / f"{f}.png"))
    b = HTML / "alur_kurir.html"
    b.write_text(board())
    (PROTO / "index.html").write_text(prototype())
    if "--no-shot" in argv:
        return
    for p, png in pages:
        shoot(p, png, SW, SH, 3)
        print("screen", png.name)
    shoot(b, OUT / "alur_kurir.png", 1920, 1080, 2)
    print("board alur_kurir.png")


if __name__ == "__main__":
    main(sys.argv[1:])
