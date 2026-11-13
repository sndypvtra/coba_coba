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
_SHOTS = {r["tag"]: r for r in json.loads((DATA / "ukur_results.json").read_text())["shots"]}
HP, GELAS = _SHOTS["20261110_131251_0"], _SHOTS["20261110_144509_0"]
PW, PH = 960, 1280            # the photo's size: the overlays are drawn in its pixels
TURBO = "linear-gradient(90deg,#7a0403,#d23105,#fb8022,#edd03a,#a4fc3c,#2ee5ae,#3e9bfe,#4454c4,#30123b)"


def overlay(r: dict, *, depth: bool, h: int) -> str:
    """SVG over the photo (or its depth map), in the photo's pixels: the segmentation outline, the courier's tap or box,
    the 3D box with the corners hidden from the camera dashed, and its sizes. Text is sized for a figure h px tall."""
    u = PH / h                                   # photo pixels per CSS pixel
    P = lambda q: (q[0] * PW, q[1] * PH)  # noqa: E731
    out = []
    poly = " ".join(f"{x * PW:.1f},{y * PH:.1f}" for x, y in r["outline"])
    if depth:
        out.append(f'<polygon points="{poly}" fill="none" stroke="#ffffff" stroke-width="{1.3 * u:.1f}" stroke-dasharray="{4 * u:.0f} {3 * u:.0f}" opacity=".9"/>')
    else:
        out.append(f'<polygon points="{poly}" fill="rgba(219,39,119,.30)" stroke="#f472b6" stroke-width="{1.6 * u:.1f}"/>')
    if not depth and r.get("tap"):
        x, y = r["tap"][0] * PW, r["tap"][1] * PH
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{8 * u:.1f}" fill="#fff"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{5 * u:.1f}" fill="#db2777"/>')
        out.append(f'<g transform="translate({x + 12 * u:.1f},{y - 10 * u:.1f})"><rect width="{74 * u:.0f}" height="{21 * u:.0f}" rx="{5 * u:.0f}" fill="#fde047"/>'
                   f'<text x="{37 * u:.0f}" y="{15 * u:.0f}" font-size="{12.5 * u:.1f}" font-weight="700" fill="#1f2937" text-anchor="middle">Tap objek</text></g>')
    if not depth and r.get("box"):
        x1, y1, x2, y2 = r["box"][0] * PW, r["box"][1] * PH, r["box"][2] * PW, r["box"][3] * PH
        out.append(f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{x2 - x1:.1f}" height="{y2 - y1:.1f}" fill="none" stroke="#fde047" '
                   f'stroke-width="{1.6 * u:.1f}" stroke-dasharray="{6 * u:.0f} {4 * u:.0f}"/>')
        out.append(f'<g transform="translate({x1:.1f},{y1 - 23 * u:.1f})"><rect width="{98 * u:.0f}" height="{21 * u:.0f}" rx="{5 * u:.0f}" fill="#fde047"/>'
                   f'<text x="{49 * u:.0f}" y="{15 * u:.0f}" font-size="{12.5 * u:.1f}" font-weight="700" fill="#1f2937" text-anchor="middle">Kotak marking</text></g>')
    c = r["corners"]; hid = set(r["hidden"])
    col = "#ffffff" if depth else "#22c55e"
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
        (xa, ya), (xb, yb) = P(c[a]), P(c[b])
        dash = f' stroke-dasharray="{4 * u:.0f} {3 * u:.0f}" opacity=".75"' if (a in hid or b in hid) else ""
        out.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{col}" stroke-width="{2 * u:.1f}" stroke-linecap="round"{dash}/>')
    cx = sum(q[0] for q in c) / 8 * PW; cy = sum(q[1] for q in c) / 8 * PH
    L, Wd, Hh = r["v046_cm"]
    if r.get("round"):                           # a round object: one diameter and the height
        tags = [("L", f"Diameter {cm(L)} cm"), ("H", f"Tinggi {cm(Hh)} cm")]
    else:
        tags = [("L", f"P {cm(L)} cm"), ("W", f"L {cm(Wd)} cm"), ("H", f"T {cm(Hh)} cm")]
    for k, t in tags:
        a, b = r["labels"][k]
        (xa, ya), (xb, yb) = P(c[a]), P(c[b])
        mx, my = (xa + xb) / 2, (ya + yb) / 2
        dx, dy = mx - cx, my - cy; n = max(1e-6, (dx * dx + dy * dy) ** .5)
        lx, ly = mx + dx / n * 26 * u, my + dy / n * 26 * u
        w = (14 + 7.6 * len(t)) * u; hh = 22 * u
        lx = min(max(lx, w / 2 + 6 * u), PW - w / 2 - 6 * u); ly = min(max(ly, 40 * u), PH - 20 * u)   # inside the picture
        out.append(f'<g transform="translate({lx - w / 2:.1f},{ly - hh / 2:.1f})"><rect width="{w:.0f}" height="{hh:.0f}" rx="{5 * u:.0f}" fill="#0b1220" '
                   f'stroke="{col}" stroke-width="{1.4 * u:.1f}"/><text x="{w / 2:.0f}" y="{15.5 * u:.0f}" font-size="{12.5 * u:.1f}" font-weight="700" fill="#fff" '
                   f'text-anchor="middle">{t}</text></g>')
    return f'<svg viewBox="0 0 {PW} {PH}" preserveAspectRatio="none" style="font-family:Inter">{"".join(out)}</svg>'


def fig(r: dict, depth: bool, h: int, caption: str) -> str:
    src = f'../img/ukur/{r["tag"]}_{"depth.png" if depth else "photo.jpg"}'
    return (f'<div class="fig" style="width:{h * 3 // 4}px;height:{h}px;flex:none"><img src="{src}">{overlay(r, depth=depth, h=h)}'
            f'<span class="cap">{caption}</span></div>')


def ukur_flow() -> str:
    caps = [("app_1_kamera", "Ambil foto", "Panduan sudut 30–60° dan cek HP diam sebelum memotret. Tanpa ARCore dan tanpa sensor depth."),
            ("app_2_marking", "Marking objek", "Kurir tap objek atau tarik kotak. AI memisahkan objek dari latar belakang (segmentasi)."),
            ("app_3_hasil", "Hasil · benda kotak", f'HP dengan clear case: {cm(HP["v046_cm"][0])} × {cm(HP["v046_cm"][1])} × '
                                                    f'{cm(HP["v046_cm"][2])} cm. Status Akurat, skor {HP["confidence"]}.'),
            ("app_4_gelas_hasil", "Hasil · benda bulat", f'Gelas: {cm(GELAS["v046_cm"][0])} × {cm(GELAS["v046_cm"][1])} × {cm(GELAS["v046_cm"][2])} cm '
                                                         f'(diameter × diameter × tinggi). Status Perlu Dicek karena bentuknya bukan kotak.')]
    cols = "".join(f'<div class="pcol"><div class="phone"><img src="../img/ukur/{f}.png"></div>'
                   f'<div class="pcap"><span class="n">{i}</span><div><b>{t}</b><p>{d}</p></div></div></div>'
                   for i, (f, t, d) in enumerate(caps, 1))
    foot = (f'<div class="foot" style="justify-content:center">{I("smartphone", size=17)}Tampilan aktual APK UkurPaket 0.4.6 (mode foto, '
            f'tanpa AR) dengan foto dari HP Urovo DT50 · layar 1–3: HP dengan clear case (sesi 20261110_131251) · layar 4: gelas '
            f'hurricane dengan sedotan (sesi 20261110_144509)</div>')
    return doc(f'<div class="cmp" style="padding-top:38px"><div class="phones" style="gap:16px">{cols}</div>{foot}</div>')


def card(r: dict, name: str, extra: str = "") -> str:
    L, Wd, Hh = r["v046_cm"]; vol = L * Wd * Hh
    chip = ('<b style="color:#067647">Akurat · skor %d</b>' % r["confidence"] if r["ok"]
            else '<b style="color:#b54708">Perlu Dicek · skor %d</b>' % r["confidence"])
    unit = "diameter × diameter × tinggi" if r.get("round") else "P × L × T"
    return (f'<div class="panel" style="flex:none;width:430px;padding:18px 20px"><div class="sect">{name}</div>'
            f'<div class="dimv tn" style="font-size:32px">{cm(L)} × {cm(Wd)} × {cm(Hh)} <small>cm</small></div>'
            f'<div style="font-size:13px;color:var(--text-3);margin-top:4px">{unit}</div>'
            f'<div class="kvs" style="margin-top:12px;font-size:14px;row-gap:7px">'
            f'<span>Berat volumetrik</span><b class="tn">{num(vol / 6000, 2)} kg</b>'
            f'<span>Jarak lensa ke objek</span><b class="tn">{num(r["focus_distance_m"] * 100, 0)} cm (autofocus)</b>'
            f'<span>Tinggi kamera di atas meja</span><b class="tn">{num(r["camera_m"] * 100, 0)} cm</b>'
            f'<span>Kecocokan kotak 3D (IoU)</span><b class="tn">{num(r["iou"], 2)}</b>'
            f'<span>Status APK</span>{chip}</div>{extra}</div>')


def ukur_how() -> str:
    h = 452
    row = lambda r, nm, ex: (f'<div style="display:flex;gap:14px;min-height:0">{fig(r, False, h, "Foto · segmentasi · kotak 3D")}'  # noqa: E731
                             f'{fig(r, True, h, "Depth map")}{card(r, nm, ex)}</div>')
    ex_g = ('<p class="note" style="font-size:12.5px;color:var(--text-3);line-height:1.45;margin-top:10px">Benda bulat dibaca '
            'diameter × diameter × tinggi; tinggi termasuk sedotan. Status Perlu Dicek karena bentuknya bukan kotak.</p>')
    ex_h = (f'<p class="note" style="font-size:12.5px;color:var(--text-3);line-height:1.45;margin-top:10px">Outline tajam '
            f'(skor ketajaman {num(HP["sharpness"], 2)}, batas 0,6) dan kotak 3D pas dengan outline.</p>')
    left = (f'<div style="display:flex;flex-direction:column;gap:16px">{row(HP, "Objek 1 · HP dengan clear case", ex_h)}'
            f'{row(GELAS, "Objek 2 · gelas dengan sedotan", ex_g)}</div>')
    steps = [("Foto + sensor gravitasi", "Satu foto. Sensor gravitasi (IMU) memberi arah tegak dan sudut kamera, sama dengan yang tampil di layar APK."),
             ("Marking dan segmentasi", "Kurir tap objek atau tarik kotak. Model segmentasi (MobileSAM) memisahkan objek dari latar belakang."),
             ("Depth map dan skala", "Model depth (Depth Anything V2) membaca permukaan meja atau lantai. Skala diambil dari jarak fokus "
                                     "lensa (autofocus); depth dari AI hanya sebagai pembanding."),
             ("Fitting kotak 3D", "Ukuran dan posisi kotak 3D disesuaikan sampai bentuknya di foto paling cocok dengan outline objek (IoU), "
                                  "memakai parameter lensa dan arah gravitasi."),
             ("Ukuran dalam cm + quality gate", "Ukuran kotak dikalikan skala menjadi P × L × T; benda bulat dibaca diameter × diameter × "
                                                "tinggi. Foto buram, objek terpotong, atau bentuk bukan kotak diberi status Perlu Dicek.")]
    st = "".join(f'<div class="step" style="padding:10px 0"><span class="n">{i}</span><div><b>{t}</b><p>{d}</p></div></div>'
                 for i, (t, d) in enumerate(steps, 1))
    leg = (f'<div class="lg2" style="font-size:13px;gap:10px 18px;margin-top:6px">'
           f'<span><i style="width:14px;height:14px;border-radius:50%;background:#db2777;border:3px solid #fff;box-shadow:0 0 0 1px #cbd5e1;display:inline-block"></i>Tap objek</span>'
           f'<span><i style="width:16px;height:12px;border:2px dashed #eab308;display:inline-block"></i>Kotak marking</span>'
           f'<span><i style="width:14px;height:14px;border-radius:4px;background:rgba(219,39,119,.35);border:2px solid #f472b6;display:inline-block"></i>Segmentasi</span>'
           f'<span><i style="width:22px;border-top:3px solid #22c55e;display:inline-block"></i>Kotak 3D</span>'
           f'<span><i style="width:22px;border-top:3px dashed #22c55e;display:inline-block"></i>Garis kotak yang tertutup dari kamera</span>'
           f'<span>Depth map: dekat<i style="width:90px;height:9px;border-radius:5px;background:{TURBO};display:inline-block"></i>jauh</span></div>')
    how = (f'<div class="panel" style="flex:1;padding-top:12px;padding-bottom:12px;display:flex;flex-direction:column">'
           f'<div class="sect" style="margin:8px 0 2px">Cara APK menghitung dimensi</div>{st}'
           f'<div style="margin-top:auto;background:#fffaeb;border:1px solid #fedf89;border-radius:12px;padding:12px 14px;font-size:14px;'
           f'line-height:1.5;color:#7a2e0e"><b>Status Perlu Dicek</b> tetap bisa dipakai kurir lewat tombol "Pakai ukuran ini". '
           f'Ukurannya tersimpan dengan status tersebut beserta foto bukti, sehingga bisa dicek ulang oleh admin atau hub.</div>'
           f'<div style="border-top:1px solid var(--hair);padding-top:12px;margin-top:14px">{leg}</div></div>')
    foot = (f'<div class="foot">{I("info", size=17)}Data: record hasil APK UkurPaket 0.4.6 dan depth map yang disimpan APK '
            f'(sesi 20261110_131251 dan 20261110_144509) · kotak 3D digambar dari koordinat yang dihitung APK; angka tidak diubah</div>')
    return doc(f'<div class="cmp"><div style="display:flex;gap:22px;flex:1;min-height:0">{left}'
               f'<div style="display:flex;flex-direction:column;flex:1;min-width:0">{how}</div></div>{foot}</div>')


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
    steps = [("Deteksi kendaraan", "RF-DETR mendeteksi motor, mobil, dan truk/bus di setiap frame."),
             ("ID tracking", "Setiap kendaraan mendapat satu ID dan dihitung sekali, setelah terlihat 15 frame."),
             ("Deteksi plat", "YOLOv9 mencari plat di dalam kotak kendaraan."),
             ("OCR plat", "fast-plate-ocr membaca plat di setiap frame; plat ditetapkan setelah beberapa bacaan sama."),
             ("Log berfoto", "Plat, jenis kendaraan, kamera, dan waktu tersimpan bersama foto plat.")]
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
