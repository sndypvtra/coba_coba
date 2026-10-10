"""Find every lemon in the inspection zone, follow it from frame to frame, read its colour.

    python dashboard/segment.py      # -> output/tracks.json (~15 min on 4 CPU cores)

FastSAM ("segment anything", fast) cuts the frame into objects without being told
what they are. A segment is a lemon if it is fruit-coloured (hue and saturation),
big enough, and its centre lies in the inspection zone: the front rows of the
washer, which are in focus. A zero-shot detector was tried first and found these
wet, packed fruit poorly (best box 0.64, boxes spanning two fruits); FastSAM
separates them cleanly.

Each lemon is followed by mask overlap with the frames before it. Its colour is
read inside the mask in CIELAB as a hue angle h = atan2(b*, a*): green fruit sits
high (about 110 deg and up), yellow fruit lower (about 90 deg). Specular
highlights from the water and very dark pixels are left out.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import FastSAM

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VIDEO = ROOT / "input" / "lemon_wash.mp4"
OUT = ROOT / "output"

IMGSZ = 1024
ZONE_Y = 0.40          # a lemon's centre must be below this share of the frame height (the sharp front rows)
MIN_AREA = 18000       # px at 1920 x 1080; smaller segments are the blurred rows behind or fragments
MAX_AREA = 0.30        # share of the frame; bigger is the brush or a merge
FRUIT_SHARE = 0.60     # share of a segment's pixels that must be fruit-coloured
IOU_MATCH = 0.30
MAX_GAP = 4            # frames a lemon may go unseen and keep its number
SCALE = 4              # masks are compared at 1/4 size


def fruit_share(hsv, m):
    px = hsv[m]
    return float(np.mean((px[:, 0] >= 15) & (px[:, 0] <= 50) & (px[:, 1] > 80))) if len(px) else 0.0


def hue(lab, m):
    px = lab[m].astype(np.float32)
    L = px[:, 0] * 100 / 255
    keep = (L > 20) & (L < 92)
    if keep.sum() > 50:
        px = px[keep]
    a = np.median(px[:, 1] - 128)
    b = np.median(px[:, 2] - 128)
    return float(np.degrees(np.arctan2(b, a))), float(np.hypot(a, b))


def outline(m):
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return []
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 3.0, True)
    return c.reshape(-1, 2).tolist()


def main():
    model = FastSAM(str(ROOT / "weights" / "FastSAM-x.pt"))
    cap = cv2.VideoCapture(str(VIDEO))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    tracks = {}        # tid -> {"small": mask, "last": frame}
    next_id = 1
    frames = []
    t0 = time.time()
    f = 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        f += 1
        H, W = im.shape[:2]
        hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
        r = model(im, device="cpu", retina_masks=True, imgsz=IMGSZ, conf=0.4, iou=0.9, verbose=False)[0]
        found = []
        if r.masks is not None:
            for mk in r.masks.data.cpu().numpy():
                m = mk > 0.5
                a = int(m.sum())
                if a < MIN_AREA or a > MAX_AREA * m.size:
                    continue
                ys, xs = np.nonzero(m)
                if ys.mean() < ZONE_Y * H or fruit_share(hsv, m) < FRUIT_SHARE:
                    continue
                found.append((m, a, xs, ys))
        # one fruit, one segment: drop a segment mostly inside a bigger one
        found.sort(key=lambda t: -t[1])
        kept = []
        for m, a, xs, ys in found:
            if any((m & k[0]).sum() > 0.6 * a for k in kept):
                continue
            kept.append((m, a, xs, ys))
        # follow: greedy by mask overlap with recent tracks
        smalls = [cv2.resize(k[0].astype(np.uint8), (W // SCALE, H // SCALE), interpolation=cv2.INTER_NEAREST) > 0
                  for k in kept]
        pairs = []
        for i, s in enumerate(smalls):
            for tid, tr in tracks.items():
                if f - tr["last"] > MAX_GAP:
                    continue
                inter = (s & tr["small"]).sum()
                if inter:
                    pairs.append((inter / (s | tr["small"]).sum(), i, tid))
        pairs.sort(reverse=True)
        assigned, used = {}, set()
        for iou, i, tid in pairs:
            if iou < IOU_MATCH or i in assigned or tid in used:
                continue
            assigned[i] = tid
            used.add(tid)
        objs = []
        for i, (m, a, xs, ys) in enumerate(kept):
            tid = assigned.get(i)
            if tid is None:
                tid = next_id
                next_id += 1
            tracks[tid] = {"small": smalls[i], "last": f}
            h, chroma = hue(lab, m)
            g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            sharp = float(cv2.Laplacian(g[ys.min():ys.max() + 1, xs.min():xs.max() + 1], cv2.CV_32F).var())
            objs.append({"tid": tid, "box": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                         "area": a, "hue": round(h, 1), "chroma": round(chroma, 1), "sharp": round(sharp, 1),
                         "poly": outline(m)})
        frames.append({"frame": f, "objects": objs})
        if f % 25 == 0:
            print(f"frame {f}/{n}  lemons {len(objs)}  ids {next_id - 1}  {(time.time() - t0) / f:.2f} s/frame",
                  flush=True)
    OUT.mkdir(exist_ok=True)
    out = {"video": VIDEO.name, "fps": fps, "size": [W, H], "zone_y": ZONE_Y, "frames": frames}
    (OUT / "tracks.json").write_text(json.dumps(out))
    print("done:", next_id - 1, "lemons seen ->", OUT / "tracks.json")


if __name__ == "__main__":
    main()
