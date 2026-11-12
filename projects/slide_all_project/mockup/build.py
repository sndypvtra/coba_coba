#!/usr/bin/env python3
"""Pictures for the use cases added to the all-projects deck that are laid out as HTML (UkurPaket, plate recognition),
in the type and colours of the Factory Vision mockups (factory_mockup/look.py), laid out at 1920 x 1080 and rendered at
2x (pages/*.png, 3840 x 2160) by headless Chromium. They are compositions of actual outputs, not web-app screens:

  UkurPaket  the APK's own screens (RealPhotoScreens: the app's Compose code fed one shot of the tester's ZIP) and that
             shot's record, drawn beside the phone's depth map. The tester's photos stay out of the repository
             (img/ukur is ignored); data/ukur_results.json holds only numbers and outlines.
  Plates     lpr/render2.py's frames, plate crops and log from two CCTV recordings (img/lpr/, data/lpr_log.json); the
             first picture of this use case is render2.py's own 4K still of the video.

The OCR pictures are drawn on the extractor's own result pages by tools/ocr_mockup.py.

    python mockup/build.py            # every page at 2x
    python mockup/build.py ukur       # some pages
    python mockup/build.py --icons    # fetch the icon subset after using a new icon (network)
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "factory_mockup"))
import look  # noqa: E402
from look import CSS, I, num  # noqa: E402
from build import shoot  # noqa: E402  (factory_mockup/build.py: headless Chromium at a device scale)

HTML, PAGES, IMG, DATA, FONTS = HERE / "html", HERE / "pages", HERE / "img", HERE / "data", HERE / "fonts"

EXTRA_CSS = """
body{background:#f3f5f8}
.cmp{position:absolute;inset:0;padding:44px 56px 40px;display:flex;flex-direction:column;gap:26px}
.foot{font-size:13px;color:var(--text-3);display:flex;align-items:center;gap:8px}
.phones{display:flex;justify-content:center;gap:76px;flex:1;min-height:0}
.pcol{display:flex;flex-direction:column;align-items:center;gap:20px;width:440px}
.phone{width:410px;height:820px;border-radius:46px;border:11px solid #0f172a;overflow:hidden;background:#000;
 box-shadow:0 24px 60px rgba(15,23,42,.22),0 2px 6px rgba(15,23,42,.12)}
.phone img{display:block;width:100%;height:100%;object-fit:cover}
.pcap{display:grid;grid-template-columns:40px 1fr;gap:14px;align-items:start;width:430px}
.pcap .n,.step .n{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:16px;color:#fff;background:#7c3aed}
.pcap b{font-size:20px;display:block;line-height:1.25}
.pcap p{font-size:15px;color:var(--text-2);margin-top:4px;line-height:1.45}
.fig{position:relative;border-radius:14px;overflow:hidden;background:#000;box-shadow:0 12px 30px rgba(15,23,42,.16)}
.fig img{display:block;width:100%;height:100%;object-fit:cover}
.fig svg{position:absolute;inset:0}
.cap{position:absolute;left:12px;top:12px;background:rgba(10,14,19,.84);color:#e9eef4;font-size:14px;font-weight:600;padding:5px 11px;border-radius:7px}
.panel{background:#fff;border:1px solid var(--border);border-radius:16px;padding:22px 24px}
.step{display:grid;grid-template-columns:40px 1fr;gap:14px;padding:12px 0;border-bottom:1px solid var(--hair)}
.step:last-child{border-bottom:none}
.step b{font-size:16.5px}.step p{color:var(--text-2);font-size:14px;margin-top:3px;line-height:1.45}
.kvs{display:grid;grid-template-columns:auto 1fr;column-gap:18px;row-gap:9px;font-size:15px}
.kvs span{color:var(--text-3)}.kvs b{font-weight:600}
.dimv{font-size:40px;font-weight:700;letter-spacing:-.02em;line-height:1.05}
.dimv small{font-size:18px;color:var(--text-3);font-weight:500}
.sect{font-size:12.5px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-3);margin-bottom:8px}
.lg2{display:flex;gap:22px;font-size:14px;color:var(--text-2);align-items:center;flex-wrap:wrap}
.lg2 span{display:inline-flex;align-items:center;gap:8px}
"""


def doc(body: str) -> str:
    return (f'<!doctype html><html lang="id"><head><meta charset="utf-8"><title>mockup</title>'
            f'<style>{CSS}{EXTRA_CSS}</style></head><body>{body}</body></html>')


def cm(v: float, dec: int = 1) -> str:
    return num(v, dec)


# ------------------------------------------------------------------ UkurPaket
UKUR = json.loads((DATA / "ukur_results.json").read_text())["shots"][0]
PW, PH = 960, 1280            # the photo's size: the overlays are drawn in its pixels
TURBO = "linear-gradient(90deg,#7a0403,#d23105,#fb8022,#edd03a,#a4fc3c,#2ee5ae,#3e9bfe,#4454c4,#30123b)"


def overlay(r: dict, *, depth: bool) -> str:
    """SVG over the photo (or its depth map): the segmentation outline, the courier's tap, the 3D box and its sides."""
    P = lambda q: (q[0] * PW, q[1] * PH)  # noqa: E731
    out = []
    poly = " ".join(f"{x * PW:.1f},{y * PH:.1f}" for x, y in r["outline"])
    if depth:
        out.append(f'<polygon points="{poly}" fill="none" stroke="#ffffff" stroke-width="3" stroke-dasharray="9 7" opacity=".9"/>')
    else:
        out.append(f'<polygon points="{poly}" fill="rgba(219,39,119,.30)" stroke="#f472b6" stroke-width="4"/>')
    if r.get("tap") and not depth:
        x, y = r["tap"][0] * PW, r["tap"][1] * PH
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="19" fill="#fff"/><circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#db2777"/>')
        out.append(f'<g transform="translate({x + 28:.1f},{y - 22:.1f})"><rect width="150" height="44" rx="9" fill="#fde047"/>'
                   f'<text x="75" y="30" font-size="23" font-weight="700" fill="#1f2937" text-anchor="middle">Tap objek</text></g>')
    c = r["corners"]; hid = set(r["hidden"])
    col = "#ffffff" if depth else "#22c55e"
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
        (xa, ya), (xb, yb) = P(c[a]), P(c[b])
        dash = ' stroke-dasharray="10 8" opacity=".7"' if (a in hid or b in hid) else ""
        out.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{col}" stroke-width="5" stroke-linecap="round"{dash}/>')
    cx = sum(p[0] for p in c) / 8 * PW; cy = sum(p[1] for p in c) / 8 * PH
    val = {"L": r["v046_cm"][0], "W": r["v046_cm"][1], "H": r["v046_cm"][2]}
    name = {"L": "P", "W": "L", "H": "T"}
    for k in ("L", "W", "H"):
        a, b = r["labels"][k]
        (xa, ya), (xb, yb) = P(c[a]), P(c[b])
        mx, my = (xa + xb) / 2, (ya + yb) / 2
        dx, dy = mx - cx, my - cy; n = max(1e-6, (dx * dx + dy * dy) ** .5)
        lx, ly = mx + dx / n * 62, my + dy / n * 62
        t = f"{name[k]} {cm(val[k])} cm"
        w = 30 + 16 * len(t)
        lx = min(max(lx, w / 2 + 10), PW - w / 2 - 10); ly = min(max(ly, 70), PH - 40)   # inside the picture
        out.append(f'<g transform="translate({lx - w / 2:.1f},{ly - 23:.1f})"><rect width="{w:.0f}" height="46" rx="10" fill="#0b1220" '
                   f'stroke="{col}" stroke-width="3"/><text x="{w / 2:.0f}" y="31" font-size="26" font-weight="700" fill="#fff" '
                   f'text-anchor="middle">{t}</text></g>')
    return f'<svg viewBox="0 0 {PW} {PH}" preserveAspectRatio="none" style="font-family:Inter">{"".join(out)}</svg>'


def fig(r: dict, depth: bool, h: int, caption: str) -> str:
    src = f'../img/ukur/{r["tag"]}_{"depth.png" if depth else "photo.jpg"}'
    return (f'<div class="fig" style="width:{h * 3 // 4}px;height:{h}px"><img src="{src}">{overlay(r, depth=depth)}'
            f'<span class="cap">{caption}</span></div>')


def ukur_flow() -> str:
    caps = [("Ambil foto", "Panduan sudut dan cek HP diam sebelum memotret. Tanpa ARCore, tanpa sensor depth."),
            ("Marking objek", "Tap objek atau tarik kotak. AI memotong outline objek (segmentasi MobileSAM)."),
            ("Hasil ukur", "Kotak 3D, P × L × T, berat volumetrik, dan skor kualitas langsung di HP.")]
    cols = "".join(f'<div class="pcol"><div class="phone"><img src="../img/ukur/app_{i}_{n}.png"></div>'
                   f'<div class="pcap"><span class="n">{i}</span><div><b>{t}</b><p>{d}</p></div></div></div>'
                   for i, (n, (t, d)) in enumerate(zip(("kamera", "marking", "hasil"), caps), 1))
    foot = (f'<div class="foot" style="justify-content:center">{I("smartphone", size=17)}Tampilan aktual APK UkurPaket 0.4.6 '
            f'(mode foto, tanpa AR) dengan data foto dari HP Urovo DT50 · sesi 20261110_131251 · objek: HP dengan clear case</div>')
    return doc(f'<div class="cmp" style="padding-top:38px"><div class="phones">{cols}</div>{foot}</div>')


def ukur_how() -> str:
    r = UKUR
    L, W, H = r["v046_cm"]; vol = L * W * H
    figs = (f'<div style="display:flex;gap:22px">{fig(r, False, 868, "Foto · marking · segmentasi · kotak 3D")}'
            f'{fig(r, True, 868, "Depth map · Depth Anything V2")}</div>')
    leg = (f'<div class="lg2"><span><i style="width:16px;height:16px;border-radius:50%;background:#db2777;border:3px solid #fff;'
           f'box-shadow:0 0 0 1px #cbd5e1;display:inline-block"></i>Tap objek</span>'
           f'<span><i style="width:16px;height:16px;border-radius:4px;background:rgba(219,39,119,.35);border:2px solid #f472b6;display:inline-block"></i>Segmentasi</span>'
           f'<span><i style="width:24px;border-top:3px solid #22c55e;display:inline-block"></i>Kotak 3D · putus-putus: rusuk tak terlihat</span>'
           f'<span style="margin-left:auto">dekat<i style="width:130px;height:10px;border-radius:5px;background:{TURBO};display:inline-block"></i>jauh</span></div>')
    left = f'<div style="display:flex;flex-direction:column;gap:16px">{figs}{leg}</div>'
    res = (f'<div class="panel"><div class="sect">Hasil APK · P × L × T</div><div class="dimv tn">{cm(L)} × {cm(W)} × {cm(H)} <small>cm</small></div>'
           f'<div class="kvs" style="margin-top:14px"><span>Berat volumetrik</span><b class="tn">{num(vol / 6000, 2)} kg (P × L × T ÷ 6000)</b>'
           f'<span>Jarak lensa ke objek</span><b class="tn">{num(r["focus_distance_m"] * 100, 0)} cm, dari autofocus</b>'
           f'<span>Kotak 3D vs outline</span><b class="tn">IoU {num(r["iou"], 2)}</b>'
           f'<span>Ketajaman outline</span><b class="tn">{num(r["sharpness"], 2)} (batas 0,6)</b>'
           f'<span>Status</span><b style="color:#067647">Akurat · skor {r["confidence"]}</b></div></div>')
    steps = [("Capture + IMU", f'Satu foto. Sensor gravitasi memberi arah vertikal dan sudut kamera ({int(r["down_deg"])}°, sama dengan layar APK).'),
             ("Marking → segmentasi", "Tap objek; MobileSAM memotong outline objek dari foto (mask)."),
             ("Depth & skala", f'Depth map membaca bidang meja. Dari dekat, jarak diambil dari autofocus lensa: '
                               f'kamera {num(r["camera_m"] * 100, 0)} cm di atas meja (AI depth {num(r["ai_m"] * 100, 0)} cm hanya pembanding).'),
             ("Fitting kotak 3D", f'Kotak 3D dicari sampai proyeksinya paling pas dengan outline (IoU {num(r["iou"], 2)}), '
                                  f'memakai intrinsik kamera dan arah gravitasi.'),
             ("Skala ke cm", "Ukuran kotak relatif × tinggi kamera = P × L × T. Quality gate: foto buram, objek terpotong, atau "
                             "bentuk tidak kotak masuk Perlu Dicek.")]
    st = "".join(f'<div class="step"><span class="n">{i}</span><div><b>{t}</b><p>{d}</p></div></div>' for i, (t, d) in enumerate(steps, 1))
    how = f'<div class="panel" style="padding-top:12px;padding-bottom:8px"><div class="sect" style="margin:8px 0 2px">Cara menghitung dimensi</div>{st}</div>'
    right = f'<div style="display:flex;flex-direction:column;gap:16px;width:520px">{res}{how}</div>'
    foot = (f'<div class="foot">{I("info", size=17)}Data: record hasil APK UkurPaket 0.4.6 (shot_0.json) dan depth map yang disimpan APK, '
            f'sesi 20261110_131251 · kotak 3D digambar dari koordinat yang dihitung APK</div>')
    return doc(f'<div class="cmp"><div style="display:flex;gap:30px;flex:1;min-height:0">{left}{right}</div>{foot}</div>')


# ------------------------------------------------------------------ plates and vehicles (two CCTV cameras)
LPR = DATA / "lpr_log.json"
# what the page shows of each camera: a frame of the joined video (lpr/render2.py's key_<cam>_<frame>.jpg, the same
# overlay as the video) and the part of it to zoom into, in the camera's pixels (x, y, w, h)
LPR_VIEW = {"CAM1": {"frame": 300, "crop": (1000, 290, 920, 484)}, "CAM2": {"frame": 300, "crop": (330, 530, 1100, 579)}}
CLS_ID = {"motorcycle": ("Motor", "#f59e0b"), "car": ("Mobil", "#3b82f6"), "truck": ("Truk / bus", "#8b5cf6")}


def zoom(cam: str, w: int, h: int, caption: str) -> str:
    v = LPR_VIEW[cam]; x, y, cw, ch = v["crop"]; s = w / cw
    W0, H0 = (1920, 1080) if cam == "CAM1" else (2560, 1440)
    return (f'<div class="fig" style="width:{w}px;height:{h}px"><img src="../img/lpr/key_{cam}_{v["frame"]:04d}.jpg" '
            f'style="position:absolute;width:{W0 * s:.1f}px;height:{H0 * s:.1f}px;left:{-x * s:.1f}px;top:{-y * s:.1f}px;object-fit:fill">'
            f'<span class="cap">{caption}</span></div>')


def lpr_proof() -> str:
    L = json.loads(LPR.read_text()); c1, c2 = L["CAM 1"], L["CAM 2"]
    figs = (f'<div style="display:flex;gap:22px">{zoom("CAM1", 893, 470, "CAM 1 · Gerbang 5 · motor bergerak dihitung")}'
            f'{zoom("CAM2", 893, 470, "CAM 2 · Area parkir · plat nomor terbaca")}</div>')
    rows = "".join(
        f'<tr><td><i style="background:{col}"></i>{name}</td><td class="tn"><b>{c1["moving"].get(k, 0)}</b></td>'
        f'<td class="tn">{c1["in_picture_last_frame"].get(k, 0)}</td></tr>' for k, (name, col) in CLS_ID.items())
    mv = sorted([r for r in c1["vehicles"] if r["moving"]], key=lambda r: r["moved_video_s"])
    moves = ('<div class="mvlog">' + "".join(
        f'<span><i style="background:{CLS_ID[r["cls"] if r["cls"] in CLS_ID else "truck"][1]}"></i>'
        f'{CLS_ID[r["cls"] if r["cls"] in CLS_ID else "truck"][0].split(" ")[0]} #{r["id"]} · detik {num(r["moved_video_s"], 1)}</span>'
        for r in mv) + '</div>')
    count = (f'<div class="panel" style="flex:1"><div class="sect">CAM 1 · kendaraan terhitung</div>'
             f'<table class="ct"><tr><th>Jenis</th><th>Bergerak</th><th>Di area (akhir video)</th></tr>{rows}</table>'
             f'<p class="note">Bergerak: berpindah lebih jauh dari lebar kotaknya sejak pertama terlihat, dihitung sekali per '
             f'ID tracking. Di area: terlihat di gambar pada akhir video, termasuk yang parkir.</p>{moves}</div>')
    cards = ""
    for r in [r for r in c2["vehicles"] if r["plate"]]:
        name = CLS_ID[r["cls"] if r["cls"] in CLS_ID else "truck"][0]
        cards += (f'<div class="plate"><img src="../img/lpr/CAM2_plate_{r["id"]}.png"><div><div class="pt">{r["plate_pretty"]}</div>'
                  f'<p>{name} #{r["id"]} · {r["votes"]} dari {r["reads"]} bacaan sama ({num(100 * r["votes"] / r["reads"], 0)}%)</p>'
                  f'<p class="ok">{I("check_circle", fill=True, size=16)}cek manual: sesuai plat di video</p></div></div>')
    plates = (f'<div class="panel" style="flex:1.15"><div class="sect">CAM 2 · plat nomor terbaca</div>{cards}'
              f'<p class="note" style="margin-top:14px">Plat di CAM 1 tidak dibaca: terlalu jauh dari kamera. Untuk membaca plat di '
              f'gerbang, kamera dipasang dekat jalur masuk, seperti CAM 2.</p></div>')
    steps = [("Deteksi kendaraan", "RF-DETR membaca motor, mobil, truk/bus di setiap frame."),
             ("Tracking ID", "Satu kendaraan satu ID; dihitung sekali, setelah terlihat 15 frame."),
             ("Deteksi plat", "YOLOv9 mencari plat di dalam kotak kendaraan."),
             ("OCR plat + voting", "fast-plate-ocr membaca setiap frame; plat ditetapkan setelah bacaan konsisten."),
             ("Log berfoto", "Plat, jenis, kamera, dan waktu tersimpan dengan foto plat.")]
    st = "".join(f'<div class="step sm"><span class="n">{i}</span><div><b>{t}</b><p>{d}</p></div></div>' for i, (t, d) in enumerate(steps, 1))
    how = f'<div class="panel" style="flex:1.1;padding-top:12px;padding-bottom:6px"><div class="sect" style="margin:8px 0 0">Cara kerja</div>{st}</div>'
    foot = (f'<div class="foot">{I("info", size=17)}Video: 2 kamera CCTV aktual (NVR) dari dataset publik Hugging Face '
            f'rithwikn/ai_cctv_videos, digabung dalam satu video · CAM 1 dari 2 potongan rekaman gerbang yang sama; '
            f'bagian rekaman yang beku dilewati · plat nomor Tanzania</div>')
    css = ('<style>.ct{width:100%;border-collapse:collapse;font-size:16px;margin-top:6px}.ct th{font-size:13px;font-weight:600;color:var(--text-3);'
           'text-align:left;padding:6px 0;border-bottom:1px solid var(--hair)}.ct td{padding:11px 0;border-bottom:1px solid var(--hair)}'
           '.ct td b{font-size:26px}.ct i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:10px}'
           '.note{font-size:13px;color:var(--text-3);line-height:1.45;margin-top:10px}'
           '.mvlog{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.mvlog span{display:inline-flex;align-items:center;gap:7px;'
           'font-size:13.5px;background:#f1f5f9;border:1px solid var(--hair);border-radius:7px;padding:5px 9px}'
           '.mvlog i{width:10px;height:10px;border-radius:3px;display:inline-block}'
           '.plate{display:flex;gap:16px;align-items:center;padding:12px 0;border-bottom:1px solid var(--hair)}.plate:last-child{border-bottom:none}'
           '.plate img{width:190px;height:76px;object-fit:contain;background:#0b1220;border-radius:8px;image-rendering:auto}'
           '.pt{font-size:28px;font-weight:700;letter-spacing:.02em}.plate p{font-size:14px;color:var(--text-2);margin-top:3px}'
           '.plate .ok{color:#067647;display:flex;align-items:center;gap:6px}.step.sm{padding:8px 0}.step.sm p{font-size:13.5px}</style>')
    return doc(f'{css}<div class="cmp"><div style="display:flex;flex-direction:column;gap:22px;flex:1;min-height:0">{figs}'
               f'<div style="display:flex;gap:22px;flex:1;min-height:0">{count}{plates}{how}</div></div>{foot}</div>')


# ------------------------------------------------------------------ pages
PAGES_ALL = {
    "UKUR_01_alur_apk": ukur_flow,
    "UKUR_02_cara_hitung": ukur_how,
    "LPR_02_hasil": lpr_proof,
}


def fetch_icons() -> None:
    for fill, name in ((False, "Line"), (True, "Fill")):
        names = ",".join(sorted(look.USED[fill])) or "info"
        url = ("https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,"
               f"{int(fill)},0&icon_names={names}&display=block")
        req = urllib.request.Request(url, headers={"User-Agent": "Wget/1.21"})
        css = urllib.request.urlopen(req, timeout=60).read().decode()
        font_url = css.split("url(")[1].split(")")[0]
        data = urllib.request.urlopen(urllib.request.Request(font_url, headers={"User-Agent": "Wget/1.21"}), timeout=60).read()
        (FONTS / f"MaterialSymbolsRounded-{name}.ttf").write_bytes(data)
        print(f"icons {name}: {len(look.USED[fill])} glyphs, {len(data) // 1024} KB")


def main(argv: list[str]) -> int:
    HTML.mkdir(exist_ok=True); PAGES.mkdir(exist_ok=True)
    want = [a for a in argv if not a.startswith("--")]
    built = []
    for name, fn in PAGES_ALL.items():
        if want and not any(w.lower() in name.lower() for w in want):
            continue
        path = HTML / f"{name}.html"; path.write_text(fn()); built.append((name, path))
    if "--icons" in argv:
        fetch_icons()
    if "--no-shot" not in argv:
        for name, path in built:
            shoot(path, PAGES / f"{name}.png", 1.0 if "--1x" in argv else 2.0)
            print("page", name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
