#!/usr/bin/env python3
"""Pass 2 for two CCTV cameras in one video: CAM 1 (a gate) counts motorcycles, cars and trucks; CAM 2 (a parking area)
reads plates. A plate is shown once it is settled (votes over the frames so far, never the future), a vehicle is
counted once tracked MIN_FRAMES frames, and it counts as passing when its box moved more than MOVE of the picture's
width during its track (else parked).

    python lpr/render2.py <cam1.mp4> <det_cam1.json> <cam2.mp4> <det_cam2.json> <out dir>
Writes <out>/plate_vehicle_cctv.mp4 (1920x1080, H.264), <out>/log.json, <out>/crops/, and <out>/still_<k>.png: the same
dashboard drawn at 3840x2160 for the slides.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "mockup" / "assets" / "fonts"
PLATE_RE = re.compile(r"^([A-Z]{1,3})([0-9]{1,4})([A-Z]{0,3})$")
CLS = {"car": ("Mobil", (59, 130, 246)), "motorcycle": ("Motor", (245, 158, 11)),
       "truck": ("Truk", (139, 92, 246)), "bus": ("Bus", (139, 92, 246))}
MIN_FRAMES, MOVE = 15, 0.06
BG, CARD, LINE, TXT, MUT, DIM = (11, 18, 32), (17, 24, 32), (35, 47, 61), (233, 238, 244), (155, 169, 184), (101, 116, 133)


def font(w: str, s: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Inter-{w}.ttf"), max(8, round(s)))


def pretty(p: str) -> str:
    m = PLATE_RE.match(p or "")
    return " ".join(x for x in m.groups() if x) if m else (p or "")


def settle(reads):
    votes = defaultdict(float); n = defaultdict(int)
    for t, p in reads:
        if PLATE_RE.match(t) and sum(c.isdigit() for c in t) >= 2:
            votes[t] += p; n[t] += 1
    if not votes:
        return None, 0.0, 0
    best = max(votes, key=votes.get); share = votes[best] / sum(votes.values())
    ok = (n[best] >= 3 or (n[best] >= 2 and votes[best] / n[best] >= 0.90)) and share >= 0.6
    return (best if ok else None), share, n[best]


class Cam:
    def __init__(self, video: str, det: str, name: str, role: str):
        self.video, self.name, self.role = video, name, role
        D = json.loads(Path(det).read_text()); self.frames = D["frames"]; self.fps = D["fps"]; self.W, self.H = D["w"], D["h"]
        self.life = defaultdict(list); self.reads = defaultdict(list); votes = defaultdict(lambda: defaultdict(float))
        self.box = defaultdict(dict)
        for k, fr in enumerate(self.frames):
            for v in fr:
                i = v["id"]; self.life[i].append(k); votes[i][v["cls"]] += v["conf"]; self.box[i][k] = v["box"]
                p = v.get("plate")
                if p and p["text"]:
                    self.reads[i].append((k, p["text"], float(np.mean(p["probs"])) if p["probs"] else 0.5, p["box"]))
        self.cls = {i: max(c, key=c.get) for i, c in votes.items()}
        self.settled_at, self.final = {}, {}
        for i, rs in self.reads.items():
            acc = []
            for k, t, p, _ in rs:
                acc.append((t, p))
                if settle(acc)[0] and i not in self.settled_at:
                    self.settled_at[i] = k
            self.final[i] = settle([(t, p) for _, t, p, _ in rs])
        self.moving = {}
        for i, ks in self.life.items():
            cs = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in (self.box[i][k] for k in ks)]
            d = max(np.hypot(c[0] - cs[0][0], c[1] - cs[0][1]) for c in cs) / self.W
            self.moving[i] = d > MOVE
        self.counted = {i for i, ks in self.life.items() if len(ks) >= MIN_FRAMES}

    def counts_upto(self, k):
        """(passing, parked) per class among vehicles tracked MIN_FRAMES frames by frame k."""
        mv, pk = defaultdict(int), defaultdict(int)
        for i in self.counted:
            ks = self.life[i]
            if len(ks) >= MIN_FRAMES and ks[MIN_FRAMES - 1] <= k:
                c = "truck" if self.cls[i] in ("truck", "bus") else self.cls[i]
                (mv if self.moving[i] else pk)[c] += 1
        return mv, pk


def overlay(img: Image.Image, cam: Cam, k: int, sc: float, fs: float, show_plates: bool) -> None:
    d = ImageDraw.Draw(img); fl = font("SemiBold", 13 * fs); fp = font("Bold", 15 * fs); lw = max(2, round(2 * fs))
    for v in cam.frames[k] if k < len(cam.frames) else []:
        if v["id"] not in cam.counted:
            continue
        x1, y1, x2, y2 = [a * sc for a in v["box"]]
        name, col = CLS[cam.cls.get(v["id"], v["cls"])]
        d.rounded_rectangle([x1, y1, x2, y2], round(5 * fs), outline=col, width=lw)
        lab = f"{name} #{v['id']}" + ("" if cam.moving[v["id"]] else " · parkir")
        tw = d.textlength(lab, font=fl); th = 19 * fs
        d.rounded_rectangle([x1, y1 - th - 2, x1 + tw + 12 * fs, y1 - 2], round(4 * fs), fill=col)
        d.text((x1 + 6 * fs, y1 - th / 2 - 2), lab, font=fl, fill="white", anchor="lm")
        if not show_plates:
            continue
        p = v.get("plate"); settled = v["id"] in cam.settled_at and cam.settled_at[v["id"]] <= k
        if p:
            px1, py1, px2, py2 = [a * sc for a in p["box"]]
            d.rectangle([px1, py1, px2, py2], outline=(16, 185, 129) if settled else (226, 232, 240), width=max(1, lw - 1))
        if settled:
            text = pretty(cam.final[v["id"]][0]); tw = d.textlength(text, font=fp); th = 23 * fs
            cx = (x1 + x2) / 2; ty = y2 + 4 * fs
            if ty + th > img.size[1] - 2:
                ty = y2 - th - 4 * fs
            d.rounded_rectangle([cx - tw / 2 - 8 * fs, ty, cx + tw / 2 + 8 * fs, ty + th], round(4 * fs), fill=(255, 255, 255),
                                outline=(16, 185, 129), width=max(1, lw - 1))
            d.text((cx, ty + th / 2), text, font=fp, fill=(15, 23, 42), anchor="mm")


def dashboard(fr1, fr2, c1: Cam, c2: Cam, k: int, crops: dict, s: float) -> Image.Image:
    W, H = round(1920 * s), round(1080 * s)
    cv = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(cv)
    tw_, th_ = round(936 * s), round(526 * s); y0 = round(68 * s)
    for x, fr, cam, plates in ((16, fr1, c1, False), (968, fr2, c2, True)):
        tile = Image.fromarray(cv2.cvtColor(cv2.resize(fr, (tw_, th_), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
        overlay(tile, cam, k, tw_ / cam.W, s, plates)
        cv.paste(tile, (round(x * s), y0))
        dd = ImageDraw.Draw(cv)
        lab = f"{cam.name} · {cam.role}"
        f = font("SemiBold", 14 * s); w = dd.textlength(lab, font=f)
        dd.rounded_rectangle([round((x + 10) * s), y0 + round(10 * s), round((x + 10) * s) + w + round(20 * s), y0 + round(38 * s)], round(6 * s), fill=(10, 14, 19))
        dd.text((round((x + 20) * s), y0 + round(24 * s)), lab, font=f, fill=TXT, anchor="lm")
    # header
    d.rounded_rectangle([16 * s, 16 * s, 104 * s, 48 * s], 8 * s, fill=(37, 99, 235)); d.text((60 * s, 32 * s), "2 CCTV", font=font("Bold", 16 * s), fill="white", anchor="mm")
    d.text((120 * s, 32 * s), "Parking CCTV Analytics  ·  hitung motor & mobil  ·  baca plat nomor", font=font("SemiBold", 21 * s), fill=TXT, anchor="lm")
    secs = k / c1.fps
    d.text((1904 * s, 32 * s), f"00:{int(secs):02d}.{int((secs % 1) * 10)}", font=font("SemiBold", 21 * s), fill=MUT, anchor="rm")
    # panel 1: counts at the gate
    py = round(610 * s); ph = round(410 * s)
    d.rounded_rectangle([16 * s, py, 952 * s, py + ph], 14 * s, fill=CARD, outline=LINE)
    d.text((36 * s, py + 30 * s), f"{c1.name} · kendaraan terhitung", font=font("SemiBold", 18 * s), fill=TXT, anchor="lm")
    mv, pk = c1.counts_upto(k)
    for j, (key, (name, col)) in enumerate([("motorcycle", CLS["motorcycle"]), ("car", CLS["car"]), ("truck", ("Truk / bus", CLS["truck"][1]))]):
        bx = (36 + j * 302) * s; by = py + 62 * s
        d.rounded_rectangle([bx, by, bx + 286 * s, by + 168 * s], 12 * s, fill=(22, 31, 42), outline=LINE)
        d.rounded_rectangle([bx + 16 * s, by + 18 * s, bx + 28 * s, by + 30 * s], 3 * s, fill=col)
        d.text((bx + 38 * s, by + 24 * s), name, font=font("Medium", 16 * s), fill=MUT, anchor="lm")
        d.text((bx + 16 * s, by + 80 * s), str(mv[key]), font=font("Bold", 50 * s), fill=TXT, anchor="lm")
        d.text((bx + 16 * s, by + 128 * s), "lewat", font=font("Medium", 14 * s), fill=MUT, anchor="lm")
        d.text((bx + 16 * s, by + 150 * s), f"{pk[key]} parkir di area", font=font("Medium", 14 * s), fill=DIM, anchor="lm")
    d.text((36 * s, py + 262 * s), "Lewat = kotak kendaraan berpindah > 6% lebar gambar selama dilacak; parkir = diam di area.",
           font=font("Medium", 14 * s), fill=DIM, anchor="lm")
    d.text((36 * s, py + 286 * s), "Satu kendaraan dihitung sekali (ID tracking), setelah terlihat minimal 15 frame.",
           font=font("Medium", 14 * s), fill=DIM, anchor="lm")
    mv2, pk2 = c2.counts_upto(k)
    d.text((36 * s, py + 330 * s), f"{c2.name}: {mv2['car'] + pk2['car']} mobil · {mv2['truck'] + pk2['truck']} truk/bus · "
                                  f"{mv2['motorcycle'] + pk2['motorcycle']} motor terdeteksi",
           font=font("SemiBold", 16 * s), fill=TXT, anchor="lm")
    # panel 2: plates read in the parking area
    x0 = 968 * s
    d.rounded_rectangle([x0, py, 1904 * s, py + ph], 14 * s, fill=CARD, outline=LINE)
    d.text((x0 + 20 * s, py + 30 * s), f"Plat nomor terbaca", font=font("SemiBold", 18 * s), fill=TXT, anchor="lm")
    rows = sorted([(t, i, c) for c in (c2, c1) for i, t in c.settled_at.items() if t <= k], key=lambda r: r[0], reverse=True)[:4]
    y = py + 58 * s
    if not rows:
        d.text((x0 + 20 * s, y + 30 * s), "membaca plat…", font=font("Medium", 16 * s), fill=MUT, anchor="lm")
    for t, i, c in rows:
        d.rounded_rectangle([x0 + 16 * s, y, 1888 * s, y + 80 * s], 10 * s, fill=(22, 31, 42), outline=LINE)
        crop = crops.get((c.name, i))
        if crop is not None:
            im = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            f_ = min(150 * s / im.size[0], 60 * s / im.size[1])          # fit the box, small plates scaled up
            im = im.resize((max(1, round(im.size[0] * f_)), max(1, round(im.size[1] * f_))), Image.LANCZOS)
            cv.paste(im, (round(x0 + 28 * s), round(y + 40 * s - im.size[1] / 2)))
        name, col = CLS[c.cls[i]]
        d.text((x0 + 200 * s, y + 28 * s), pretty(c.final[i][0]), font=font("Bold", 22 * s), fill=TXT, anchor="lm")
        d.rounded_rectangle([x0 + 200 * s, y + 50 * s, x0 + 210 * s, y + 60 * s], 3 * s, fill=col)
        d.text((x0 + 218 * s, y + 55 * s), f"{name} #{i} · {c.name} · detik {t / c.fps:.0f} · {c.final[i][2]} bacaan sama",
               font=font("Medium", 14 * s), fill=MUT, anchor="lm")
        y += 88 * s
    d.text((16 * s, 1046 * s), "Video: 2 rekaman CCTV aktual (NVR) dari dataset publik Hugging Face rithwikn/ai_cctv_videos, digabung dalam satu "
                               "video; plat nomor Tanzania. Model: RF-DETR (kendaraan), YOLOv9 (plat), fast-plate-ocr (OCR plat), di CPU.",
           font=font("Medium", 13 * s), fill=DIM, anchor="lm")
    return cv


def main(v1, d1, v2, d2, out_dir, stills=None):
    out = Path(out_dir); (out / "crops").mkdir(parents=True, exist_ok=True)
    c1 = Cam(v1, d1, "CAM 1", "Gerbang 5"); c2 = Cam(v2, d2, "CAM 2", "Area parkir")
    # the sharpest crop of each settled plate (widest read of the settled text)
    want = defaultdict(list)
    for c in (c1, c2):
        for i, rs in c.reads.items():
            s = c.final[i][0]
            if s:
                k, t, p, box = max([r for r in rs if r[1] == s], key=lambda r: (r[3][2] - r[3][0], r[2]))
                want[(c.name, k)].append((i, box))
    crops = {}
    cap1, cap2 = cv2.VideoCapture(v1), cv2.VideoCapture(v2)
    n = min(len(c1.frames), len(c2.frames))
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(c1.fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                           str(out / "plate_vehicle_cctv.mp4")], stdin=subprocess.PIPE)
    stills = set(stills) if stills else {round(n * f) for f in (0.35, 0.6, 0.9)}
    for k in range(n):
        ok1, f1 = cap1.read(); ok2, f2 = cap2.read()
        if not (ok1 and ok2):
            break
        for c, fr in ((c1, f1), (c2, f2)):
            for i, box in want.get((c.name, k), []):
                x1, y1, x2, y2 = [int(round(a)) for a in box]; pad = int(0.12 * (x2 - x1))
                crops[(c.name, i)] = fr[max(0, y1 - pad):min(c.H, y2 + pad), max(0, x1 - pad):min(c.W, x2 + pad)].copy()
                cv2.imwrite(str(out / "crops" / f"{c.name.replace(' ', '')}_plate_{i}.png"), crops[(c.name, i)])
        ff.stdin.write(np.asarray(dashboard(f1, f2, c1, c2, k, crops, 1.0)).tobytes())
        if k in stills:
            dashboard(f1, f2, c1, c2, k, crops, 2.0).save(out / f"still_{k:04d}.png")
            # each camera at its own resolution with the same overlay, labels sized as on the dashboard tile
            for c, fr, plates in ((c1, f1, False), (c2, f2, True)):
                im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
                overlay(im, c, k, 1.0, c.W / 936, plates)
                im.save(out / f"key_{c.name.replace(' ', '')}_{k:04d}.jpg", quality=92)
    ff.stdin.close(); ff.wait()
    log = {}
    for c in (c1, c2):
        rows = []
        for i in sorted(c.counted):
            s, share, nv = c.final.get(i, (None, 0, 0))
            rows.append({"id": i, "cls": c.cls[i], "moving": bool(c.moving[i]), "first_s": round(c.life[i][0] / c.fps, 2),
                         "last_s": round(c.life[i][-1] / c.fps, 2), "frames": len(c.life[i]), "plate": s, "plate_pretty": pretty(s) if s else None,
                         "votes": nv, "share": round(share, 2), "reads": len(c.reads.get(i, [])),
                         "settled_s": round(c.settled_at[i] / c.fps, 2) if i in c.settled_at else None})
        mv, pk = c.counts_upto(n - 1)
        log[c.name] = {"role": c.role, "video": Path(c.video).name, "frames": n, "fps": c.fps, "passing": dict(mv), "parked": dict(pk), "vehicles": rows}
    (out / "log.json").write_text(json.dumps(log, indent=1))
    print({k: (v["passing"], v["parked"], sum(1 for r in v["vehicles"] if r["plate"])) for k, v in log.items()})


if __name__ == "__main__":
    # optional 6th argument: the frames to save as stills, e.g. 400,700,950
    main(*sys.argv[1:6], stills=[int(x) for x in sys.argv[6].split(",")] if len(sys.argv) > 6 else None)
