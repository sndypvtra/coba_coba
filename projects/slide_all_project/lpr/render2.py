#!/usr/bin/env python3
"""Pass 2 for two CCTV cameras in one video: CAM 1 (a gate) counts motorcycles, cars and trucks; CAM 2 (a parking area)
reads plates. Everything shown at a frame uses only the frames up to it, never the future:
  - a vehicle appears once tracked MIN_FRAMES frames;
  - it counts as moving from the frame its box is further from where its track began than the box is wide (and at
    least MOVE of the picture's width): the vehicles crossing the yard; "di area" is how many of each class are in
    the picture now;
  - a plate is shown once its reads settle (settle()).
Before that, the detector's output is cleaned: of two boxes on one vehicle (IoU > DUP) only the surer is kept, and a
track whose box jumps faster than JUMP of the width per frame, or more than twice its own width, is split there: its ID went to another vehicle, as
happens when the recording stalls and resumes (CAM 1 freezes for about 7 s, then skips 9 s). Frozen stretches of a
recording (FROZEN frames or more, picture unchanged) are left out of the video, for both cameras.

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
MIN_FRAMES, MOVE, DUP, JUMP, FROZEN = 15, 0.06, 0.8, 0.03, 10
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


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u > 0 else 0.0


def centre(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


class Cam:
    def __init__(self, video: str, det: str, name: str, role: str, stalls: set[int] = frozenset()):
        self.video, self.name, self.role = video, name, role
        D = json.loads(Path(det).read_text()); self.fps = D["fps"]; self.W, self.H = D["w"], D["h"]
        self.cuts = D.get("cuts", []); self.pieces = D.get("pieces")
        # one box per vehicle, and a new ID where a track jumps to another vehicle
        last, seg, self.frames = {}, defaultdict(int), []
        for k, fr in enumerate(D["frames"]):
            keep = []
            for v in sorted(fr, key=lambda v: -v["conf"]):
                if all(iou(v["box"], u["box"]) <= DUP for u in keep):
                    keep.append(v)
            out = []
            for v in keep:
                i = v["id"]; c = centre(v["box"])
                if i in last:
                    k0, c0, w0 = last[i]; dist = np.hypot(c[0] - c0[0], c[1] - c0[1])
                    # faster than a vehicle moves, or across the picture after a gap: the ID went to another vehicle
                    if dist / max(1, k - k0) > JUMP * self.W or dist > 2 * w0:
                        seg[i] += 1
                last[i] = (k, c, v["box"][2] - v["box"][0])
                out.append(dict(v, id=i + 1000 * seg[i]) if seg[i] else v)
            self.frames.append(out)
        self._bridge(stalls)
        self.dropped = self._people(D.get("persons"))
        self.merged = self._parts()
        # IDs as shown: 1, 2, 3 ... in the order the vehicles first appear (the splits above leave gaps and large numbers)
        seen = defaultdict(int)
        for fr in self.frames:
            for v in fr:
                seen[v["id"]] += 1
        order = {}
        for fr in self.frames:
            for v in fr:
                if seen[v["id"]] >= MIN_FRAMES:
                    order.setdefault(v["id"], len(order) + 1)
        for i in seen:                                   # never shown: out of the way
            order.setdefault(i, 100000 + i)
        self.frames = [[dict(v, id=order[v["id"]]) for v in fr] for fr in self.frames]
        self.life = defaultdict(list); self.reads = defaultdict(list); votes = defaultdict(lambda: defaultdict(float))
        self.box = defaultdict(dict)
        for k, fr in enumerate(self.frames):
            for v in fr:
                i = v["id"]; self.life[i].append(k); votes[i][v["cls"]] += v["conf"]; self.box[i][k] = v["box"]
                p = v.get("plate")
                if p and p["text"]:
                    self.reads[i].append((k, p["text"], float(np.mean(p["probs"])) if p["probs"] else 0.5, p["box"]))
        self.cls = {i: max(c, key=c.get) for i, c in votes.items()}
        # the plate as known at each read (reads so far only), and the reading over the whole track for the log
        self.plate_track, self.final = {}, {}
        for i, rs in self.reads.items():
            acc, track = [], []
            for k, t, p, _ in rs:
                acc.append((t, p)); now = settle(acc)[0]
                if not track or track[-1][1] != now:
                    track.append((k, now))
            self.plate_track[i] = track
            self.final[i] = settle([(t, p) for _, t, p, _ in rs])
        self.shown_at = {i: ks[MIN_FRAMES - 1] for i, ks in self.life.items() if len(ks) >= MIN_FRAMES}
        # moving: away from where it was first seen by more than its own width (and at least MOVE of the picture);
        # a parked vehicle's box drifts by less when another passes in front of it or it sits at the picture's edge
        self.moved_at = {}
        for i, ks in self.life.items():
            c0 = centre(self.box[i][ks[0]]); ws = []
            for k in ks:
                b = self.box[i][k]; c = centre(b); ws.append(b[2] - b[0])
                if np.hypot(c[0] - c0[0], c[1] - c0[1]) > max(MOVE * self.W, float(np.median(ws))):
                    self.moved_at[i] = k
                    break

    def _people(self, persons) -> list[int]:
        """Drop motorcycle tracks that are people (lpr/persons.py): in at least half the frames checked, a person box
        covers 60% or more of the motorcycle box and the detector is surer of the person. A parked motorcycle never
        meets this; a pedestrian carrying goods, read as a motorcycle, does."""
        if not persons:
            return []
        hits, checked = defaultdict(int), defaultdict(int)
        for k, fr in enumerate(self.frames):
            if persons[k] is None:
                continue
            for v in fr:
                if v["cls"] != "motorcycle":
                    continue
                m = v["box"]; area = (m[2] - m[0]) * (m[3] - m[1]); checked[v["id"]] += 1
                for q in persons[k]:
                    ix = max(0.0, min(m[2], q[2]) - max(m[0], q[0])); iy = max(0.0, min(m[3], q[3]) - max(m[1], q[1]))
                    if area > 0 and ix * iy / area >= 0.6 and q[4] > v["conf"]:
                        hits[v["id"]] += 1
                        break
        drop = {i for i in checked if hits[i] * 2 >= checked[i] and hits[i] > 0}
        if drop:
            self.frames = [[v for v in fr if v["id"] not in drop] for fr in self.frames]
        return sorted(drop)

    def _parts(self) -> dict:
        """A moving vehicle first seen in part (a truck's cab entering the picture, read as a car) gets a track of its
        own: when two moving tracks share 10 frames or more, in most of them one box lies 60% or more inside the
        other, and over those frames both move the same way by about as much, the smaller is part of the larger and
        takes its ID (its own box dropped where both are seen). Two vehicles may overlap for a moment, but not move
        as one for 10 frames."""
        box = defaultdict(dict)
        for k, fr in enumerate(self.frames):
            for v in fr:
                box[v["id"]][k] = v["box"]

        def moved(i):
            ks = sorted(box[i]); c0 = centre(box[i][ks[0]])
            w = float(np.median([box[i][k][2] - box[i][k][0] for k in ks]))
            return max(np.hypot(*(np.subtract(centre(box[i][k]), c0))) for k in ks) > max(MOVE * self.W, w)

        def inside(a, b):
            ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            return ix * iy / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))

        mv = [i for i in box if len(box[i]) >= MIN_FRAMES and moved(i)]
        into = {}
        for a in mv:
            for b in mv:
                if a == b or a in into:
                    continue
                both = [k for k in box[a] if k in box[b]]
                if len(both) < 10 or sum(inside(box[a][k], box[b][k]) >= 0.6 for k in both) < 0.8 * len(both):
                    continue
                da = np.subtract(centre(box[a][both[-1]]), centre(box[a][both[0]]))
                db = np.subtract(centre(box[b][both[-1]]), centre(box[b][both[0]]))
                if np.hypot(*(da - db)) < 0.5 * max(np.hypot(*db), 1e-6):
                    into[a] = b
        if into:
            frames = []
            for k, fr in enumerate(self.frames):
                out = []
                for v in fr:
                    j = into.get(v["id"])
                    if j is None:
                        out.append(v)
                    elif k not in box[j]:            # the part alone: it is the larger vehicle, seen in part
                        out.append(dict(v, id=j))
                frames.append(out)
            self.frames = frames
        return into

    def _bridge(self, stalls: set[int]) -> None:
        """Across a stall of the recording, a vehicle that was moving when the picture froze and one moving the same way
        when it resumes are the same vehicle, when there is exactly one of each per class: the later track takes the
        earlier ID. (Nothing is seen during the stall, so the tracker alone gives the vehicle a new ID.)"""
        first, last, cls = {}, {}, defaultdict(lambda: defaultdict(float))
        for k, fr in enumerate(self.frames):
            for v in fr:
                first.setdefault(v["id"], (k, centre(v["box"]))); last[v["id"]] = (k, centre(v["box"]))
                cls[v["id"]]["truck" if v["cls"] in ("truck", "bus") else v["cls"]] += v["conf"]
        grp = {i: max(c, key=c.get) for i, c in cls.items()}
        runs = []
        for k in sorted(stalls):
            if runs and k == runs[-1][1] + 1:
                runs[-1][1] = k
            else:
                runs.append([k, k])
        rename = {}
        for a, b in runs:
            if any(b < c <= b + 3 for c in self.cuts):     # the next frames are another piece of recording
                continue

            def dx(i):  # its sideways travel, and whether it is far enough to call it moving
                (_, c0), (_, c1) = first[i], last[i]
                return c1[0] - c0[0]
            ended = [i for i in last if b - 2 <= last[i][0] <= b and abs(dx(i)) > MOVE * self.W]
            begun = [i for i in first if b + 1 <= first[i][0] <= b + 3 and abs(dx(i)) > MOVE * self.W]
            for g in {grp[i] for i in ended}:
                e = [i for i in ended if grp[i] == g]; s = [j for j in begun if grp[j] == g]
                if len(e) == 1 and len(s) == 1 and np.sign(dx(e[0])) == np.sign(dx(s[0])):
                    rename[s[0]] = e[0]
        if rename:
            self.frames = [[dict(v, id=rename[v["id"]]) if v["id"] in rename else v for v in fr] for fr in self.frames]
        self.bridged = rename

    def plate_at(self, i, k):
        """(plate text, frame it became that) as known at frame k, or (None, None)."""
        cur = (None, None)
        for k0, t in self.plate_track.get(i, []):
            if k0 > k:
                break
            cur = (t, k0) if t else (None, None)
        return cur

    def group(self, i):
        return "truck" if self.cls[i] in ("truck", "bus") else self.cls[i]

    def shown(self, i, k) -> bool:
        return i in self.shown_at and self.shown_at[i] <= k

    def moving(self, i, k) -> bool:
        return i in self.moved_at and self.moved_at[i] <= k

    def counts_upto(self, k):
        """(moving so far, in the picture now) per class: moving counts each vehicle once, from the frame it moved."""
        mv, now = defaultdict(int), defaultdict(int)
        for i in self.shown_at:
            if self.shown(i, k) and self.moving(i, k):
                mv[self.group(i)] += 1
        for v in self.frames[min(k, len(self.frames) - 1)]:
            if self.shown(v["id"], k):
                now[self.group(v["id"])] += 1
        return mv, now


def overlay(img: Image.Image, cam: Cam, k: int, sc: float, fs: float, show_plates: bool) -> None:
    """Boxes first, then labels: each label goes to the first of a few places by its box that no other label takes
    (above the box, inside its top, inside its bottom), moving vehicles first so theirs stay where expected."""
    d = ImageDraw.Draw(img); fl = font("SemiBold", 13 * fs); fp = font("Bold", 15 * fs); lw = max(2, round(2 * fs))
    W, H = img.size
    vs = [v for v in (cam.frames[k] if k < len(cam.frames) else []) if cam.shown(v["id"], k)]
    vs.sort(key=lambda v: (not cam.moving(v["id"], k), -(v["box"][2] - v["box"][0]) * (v["box"][3] - v["box"][1])))
    for v in vs:
        x1, y1, x2, y2 = [a * sc for a in v["box"]]
        d.rounded_rectangle([x1, y1, x2, y2], round(5 * fs), outline=CLS[cam.cls.get(v["id"], v["cls"])][1], width=lw)
    taken = []

    def free(r):
        return all(r[2] <= q[0] or r[0] >= q[2] or r[3] <= q[1] or r[1] >= q[3] for q in taken)

    for v in vs:
        x1, y1, x2, y2 = [a * sc for a in v["box"]]
        name, col = CLS[cam.cls.get(v["id"], v["cls"])]
        lab = f"{name} #{v['id']}" + (" · bergerak" if cam.moving(v["id"], k) else "")
        tw = d.textlength(lab, font=fl) + 12 * fs; th = 19 * fs
        spots = [(x1, y1 - th - 2), (x1 + lw, y1 + lw), (x1 + lw, y2 - th - lw), (x2 - tw - lw, y1 + lw)]
        spots = [(min(max(0, x), W - tw), min(max(0, y), H - th)) for x, y in spots]
        x, y = next((q for q in spots if free((q[0], q[1], q[0] + tw, q[1] + th))), spots[0])
        taken.append((x, y, x + tw, y + th))
        d.rounded_rectangle([x, y, x + tw, y + th], round(4 * fs), fill=col)
        d.text((x + 6 * fs, y + th / 2), lab, font=fl, fill="white", anchor="lm")
        if not show_plates:
            continue
        p = v.get("plate"); text = cam.plate_at(v["id"], k)[0]; settled = text is not None
        if p:
            px1, py1, px2, py2 = [a * sc for a in p["box"]]
            d.rectangle([px1, py1, px2, py2], outline=(16, 185, 129) if settled else (226, 232, 240), width=max(1, lw - 1))
        if settled:
            text = pretty(text); tw = d.textlength(text, font=fp); th = 23 * fs
            cx = (x1 + x2) / 2; ty = y2 + 4 * fs
            if ty + th > H - 2:
                ty = y2 - th - 4 * fs
            d.rounded_rectangle([cx - tw / 2 - 8 * fs, ty, cx + tw / 2 + 8 * fs, ty + th], round(4 * fs), fill=(255, 255, 255),
                                outline=(16, 185, 129), width=max(1, lw - 1))
            d.text((cx, ty + th / 2), text, font=fp, fill=(15, 23, 42), anchor="mm")
            taken.append((cx - tw / 2 - 8 * fs, ty, cx + tw / 2 + 8 * fs, ty + th))


def dashboard(fr1, fr2, c1: Cam, c2: Cam, k1: int, k2: int, t: float, crops: dict, s: float) -> Image.Image:
    """One video frame: CAM 1 at its frame k1, CAM 2 at its frame k2, t seconds into the joined video."""
    W, H = round(1920 * s), round(1080 * s)
    cv = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(cv)
    tw_, th_ = round(936 * s), round(526 * s); y0 = round(68 * s)
    for x, fr, cam, k, plates in ((16, fr1, c1, k1, False), (968, fr2, c2, k2, True)):
        tile = Image.fromarray(cv2.cvtColor(cv2.resize(fr, (tw_, th_), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
        overlay(tile, cam, k, tw_ / cam.W, s, plates)
        cv.paste(tile, (round(x * s), y0))
        dd = ImageDraw.Draw(cv)
        lab = f"{cam.name} · {cam.role}" + (f" · potongan {1 + sum(c <= k for c in cam.cuts)}/{len(cam.cuts) + 1}" if cam.cuts else "")
        f = font("SemiBold", 14 * s); w = dd.textlength(lab, font=f)
        dd.rounded_rectangle([round((x + 10) * s), y0 + round(10 * s), round((x + 10) * s) + w + round(20 * s), y0 + round(38 * s)], round(6 * s), fill=(10, 14, 19))
        dd.text((round((x + 20) * s), y0 + round(24 * s)), lab, font=f, fill=TXT, anchor="lm")
    # header
    d.rounded_rectangle([16 * s, 16 * s, 104 * s, 48 * s], 8 * s, fill=(37, 99, 235)); d.text((60 * s, 32 * s), "2 CCTV", font=font("Bold", 16 * s), fill="white", anchor="mm")
    d.text((120 * s, 32 * s), "Parking CCTV Analytics  ·  hitung motor & mobil  ·  baca plat nomor", font=font("SemiBold", 21 * s), fill=TXT, anchor="lm")
    secs = t
    d.text((1904 * s, 32 * s), f"00:{int(secs):02d}.{int((secs % 1) * 10)}", font=font("SemiBold", 21 * s), fill=MUT, anchor="rm")
    # panel 1: counts at the gate
    py = round(610 * s); ph = round(410 * s)
    d.rounded_rectangle([16 * s, py, 952 * s, py + ph], 14 * s, fill=CARD, outline=LINE)
    d.text((36 * s, py + 30 * s), f"{c1.name} · kendaraan terhitung", font=font("SemiBold", 18 * s), fill=TXT, anchor="lm")
    mv, pk = c1.counts_upto(k1)
    for j, (key, (name, col)) in enumerate([("motorcycle", CLS["motorcycle"]), ("car", CLS["car"]), ("truck", ("Truk / bus", CLS["truck"][1]))]):
        bx = (36 + j * 302) * s; by = py + 62 * s
        d.rounded_rectangle([bx, by, bx + 286 * s, by + 168 * s], 12 * s, fill=(22, 31, 42), outline=LINE)
        d.rounded_rectangle([bx + 16 * s, by + 18 * s, bx + 28 * s, by + 30 * s], 3 * s, fill=col)
        d.text((bx + 38 * s, by + 24 * s), name, font=font("Medium", 16 * s), fill=MUT, anchor="lm")
        d.text((bx + 16 * s, by + 80 * s), str(mv[key]), font=font("Bold", 50 * s), fill=TXT, anchor="lm")
        d.text((bx + 16 * s, by + 128 * s), "bergerak", font=font("Medium", 14 * s), fill=MUT, anchor="lm")
        d.text((bx + 16 * s, by + 150 * s), f"{pk[key]} di area sekarang", font=font("Medium", 14 * s), fill=DIM, anchor="lm")
    d.text((36 * s, py + 262 * s), "Bergerak = berpindah lebih jauh dari lebar kotaknya sejak pertama terlihat; dihitung sekali per ID tracking.",
           font=font("Medium", 14 * s), fill=DIM, anchor="lm")
    d.text((36 * s, py + 286 * s), "Di area = kendaraan yang terlihat di gambar saat ini, termasuk yang parkir.",
           font=font("Medium", 14 * s), fill=DIM, anchor="lm")
    mv2, pk2 = c2.counts_upto(k2)
    d.text((36 * s, py + 330 * s), f"{c2.name} · {c2.role}: {pk2['car']} mobil · {pk2['truck']} truk/bus · {pk2['motorcycle']} motor di area sekarang",
           font=font("SemiBold", 16 * s), fill=TXT, anchor="lm")
    # panel 2: plates read in the parking area
    x0 = 968 * s
    d.rounded_rectangle([x0, py, 1904 * s, py + ph], 14 * s, fill=CARD, outline=LINE)
    d.text((x0 + 20 * s, py + 30 * s), f"Plat nomor terbaca", font=font("SemiBold", 18 * s), fill=TXT, anchor="lm")
    # plates are read on CAM 2 only: on the gate camera they are too far away to read
    rows = sorted([(c2.plate_at(i, k2)[1], i, c2) for i in c2.plate_track if c2.plate_at(i, k2)[0]], key=lambda r: r[0], reverse=True)[:4]
    y = py + 58 * s
    if not rows:
        d.text((x0 + 20 * s, y + 30 * s), "membaca plat…", font=font("Medium", 16 * s), fill=MUT, anchor="lm")
    for k0, i, c in rows:
        d.rounded_rectangle([x0 + 16 * s, y, 1888 * s, y + 80 * s], 10 * s, fill=(22, 31, 42), outline=LINE)
        crop = crops.get((c.name, i))
        if crop is not None:
            im = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            f_ = min(150 * s / im.size[0], 60 * s / im.size[1])          # fit the box, small plates scaled up
            im = im.resize((max(1, round(im.size[0] * f_)), max(1, round(im.size[1] * f_))), Image.LANCZOS)
            cv.paste(im, (round(x0 + 28 * s), round(y + 40 * s - im.size[1] / 2)))
        name, col = CLS[c.cls[i]]
        d.text((x0 + 200 * s, y + 28 * s), pretty(c.plate_at(i, k2)[0]), font=font("Bold", 22 * s), fill=TXT, anchor="lm")
        d.rounded_rectangle([x0 + 200 * s, y + 50 * s, x0 + 210 * s, y + 60 * s], 3 * s, fill=col)
        d.text((x0 + 218 * s, y + 55 * s), f"{name} #{i} · {c.name} · terbaca di detik {k0 / c.fps:.0f}",
               font=font("Medium", 14 * s), fill=MUT, anchor="lm")
        y += 88 * s
    d.text((16 * s, 1046 * s), "Video: 2 rekaman CCTV aktual (NVR) dari dataset publik Hugging Face rithwikn/ai_cctv_videos, digabung dalam satu "
                               "video; plat nomor Tanzania. Model: RF-DETR (kendaraan), YOLOv9 (plat), fast-plate-ocr (OCR plat), di CPU.",
           font=font("Medium", 13 * s), fill=DIM, anchor="lm")
    return cv


def frozen(video: str) -> set[int]:
    """Frames where the recording stalled: the recorder's on-screen clock (top right) stands still for more than 1.5 s
    and the picture repeats the frame before. A still scene alone is not a stall: its clock keeps ticking."""
    cap = cv2.VideoCapture(video); fps = cap.get(cv2.CAP_PROP_FPS) or 25
    same_pic, same_clock, prev, k = set(), [], None, 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        H, W = f.shape[:2]
        g = cv2.cvtColor(cv2.resize(f, (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.int16)
        clock = cv2.cvtColor(f[int(.02 * H):int(.09 * H), int(.72 * W):int(.99 * W)], cv2.COLOR_BGR2GRAY).astype(np.int16)
        if prev is not None:
            if np.abs(g - prev[0]).mean() < 0.3:
                same_pic.add(k)
            if np.abs(clock - prev[1]).mean() < 1.0:
                same_clock.append(k)
        prev, k = (g, clock), k + 1
    runs = []
    for k in same_clock:
        if runs and k == runs[-1][1] + 1:
            runs[-1][1] = k
        else:
            runs.append([k, k])
    out = set()
    for a, b in runs:
        if b - a + 1 >= 1.5 * fps:
            out |= {k for k in range(a, b + 1) if k in same_pic}
    # a single glitched frame inside a stall belongs to it
    out |= {k for k in range(1, max(out, default=0)) if k - 1 in out and k + 1 in out}
    return out


def main(v1, d1, v2, d2, out_dir, stills=None):
    out = Path(out_dir); (out / "crops").mkdir(parents=True, exist_ok=True)
    st1, st2 = frozen(v1), frozen(v2)
    c1 = Cam(v1, d1, "CAM 1", "Gerbang 5", st1); c2 = Cam(v2, d2, "CAM 2", "Area parkir", st2)
    # the sharpest crop of each settled plate (widest read of the settled text)
    want = defaultdict(list)
    for c in (c2,):
        for i, rs in c.reads.items():
            s = c.final[i][0]
            if s:
                # a crop when the plate is first shown, replaced by the widest read of it when the video gets there
                k0 = next((k for k, t in c.plate_track[i] if t), None)
                first = next((r for r in rs if r[0] >= k0), None) if k0 is not None else None
                if first is not None:
                    want[(c.name, first[0])].append((i, first[3]))
                k, t, p, box = max([r for r in rs if r[1] == s], key=lambda r: (r[3][2] - r[3][0], r[2]))
                want[(c.name, k)].append((i, box))
    crops = {}

    def keep_crops(c, k, fr):
        for i, box in want.get((c.name, k), []):
            x1, y1, x2, y2 = [int(round(a)) for a in box]; pad = int(0.12 * (x2 - x1))
            crops[(c.name, i)] = fr[max(0, y1 - pad):min(c.H, y2 + pad), max(0, x1 - pad):min(c.W, x2 + pad)].copy()
            cv2.imwrite(str(out / "crops" / f"{c.name.replace(' ', '')}_plate_{i}.png"), crops[(c.name, i)])

    class Reader:  # a camera's frames in order, every frame seen once (for the crops), the asked one returned
        def __init__(self, video, cam):
            self.cap, self.cam, self.pos, self.fr = cv2.VideoCapture(video), cam, 0, None

        def get(self, k):
            while self.pos <= k:
                ok, self.fr = self.cap.read()
                assert ok, f"{self.cam.name}: no frame {self.pos}"
                keep_crops(self.cam, self.pos, self.fr); self.pos += 1
            return self.fr

    # the joined video: each camera's frames without its stalls, side by side, until either camera ends
    pairs = list(zip([k for k in range(len(c1.frames)) if k not in st1], [k for k in range(len(c2.frames)) if k not in st2]))
    r1, r2 = Reader(v1, c1), Reader(v2, c2)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(c1.fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                           str(out / "plate_vehicle_cctv.mp4")], stdin=subprocess.PIPE)
    stills = set(stills) if stills else {round(len(pairs) * f) for f in (0.35, 0.6, 0.9)}
    for j, (k1, k2) in enumerate(pairs):
        f1, f2 = r1.get(k1), r2.get(k2)
        ff.stdin.write(np.asarray(dashboard(f1, f2, c1, c2, k1, k2, j / c1.fps, crops, 1.0)).tobytes())
        if j in stills:
            dashboard(f1, f2, c1, c2, k1, k2, j / c1.fps, crops, 2.0).save(out / f"still_{j:04d}.png")
            # each camera at its own resolution with the same overlay, labels sized as on the dashboard tile
            for c, fr, k, plates in ((c1, f1, k1, False), (c2, f2, k2, True)):
                im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
                overlay(im, c, k, 1.0, c.W / 936, plates)
                im.save(out / f"key_{c.name.replace(' ', '')}_{j:04d}.jpg", quality=92)
    ff.stdin.close(); ff.wait()
    at = [{k1: j for j, (k1, _) in enumerate(pairs)}, {k2: j for j, (_, k2) in enumerate(pairs)}]
    log = {}
    for c in (c1, c2):
        rows = []; to_j = at[0 if c is c1 else 1]
        for i in sorted(c.shown_at):
            s, share, nv = c.final.get(i, (None, 0, 0))
            mj = next((to_j[k] for k in range(c.moved_at[i], len(c.frames)) if k in to_j), None) if i in c.moved_at else None
            rows.append({"id": i, "cls": c.cls[i], "moving": i in c.moved_at, "moved_s": round(c.moved_at[i] / c.fps, 2) if i in c.moved_at else None,
                         "moved_video_s": round(mj / c.fps, 1) if mj is not None else None, "first_s": round(c.life[i][0] / c.fps, 2),
                         "last_s": round(c.life[i][-1] / c.fps, 2), "frames": len(c.life[i]), "plate": s, "plate_pretty": pretty(s) if s else None,
                         "votes": nv, "share": round(share, 2), "reads": len(c.reads.get(i, [])),
                         "plate_track": [[round(k0 / c.fps, 2), t] for k0, t in c.plate_track.get(i, [])]})
        last = pairs[-1][0 if c is c1 else 1]; st = sorted(st1 if c is c1 else st2)
        mv, pk = c.counts_upto(last)
        log[c.name] = {"role": c.role, "video": Path(c.video).name, "pieces": c.pieces, "cuts": c.cuts, "frames_used": last + 1,
                       "stalled_frames_left_out": len(st), "fps": c.fps, "dropped_as_people": c.dropped, "bridged": c.bridged,
                       "moving": dict(mv), "in_picture_last_frame": dict(pk), "vehicles": rows}
    (out / "log.json").write_text(json.dumps(log, indent=1))
    print(len(pairs), "frames,", round(len(pairs) / c1.fps, 1), "s", {k: (v["moving"], v["in_picture_last_frame"], [r["plate_pretty"] for r in v["vehicles"] if r["plate"]]) for k, v in log.items()})


if __name__ == "__main__":
    # optional 6th argument: the frames of the joined video to save as stills, e.g. 400,700,950
    main(*sys.argv[1:6], stills=[int(x) for x in sys.argv[6].split(",")] if len(sys.argv) > 6 else None)
