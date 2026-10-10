"""Find every peach on the sizer and follow it.

    python dashboard/segment.py      # -> output/tracks.json (~30 min on 4 CPU cores)

FastSAM cuts each frame into objects without being told what they are; a segment
is a peach if most of its pixels are peach-coloured (red to orange-yellow,
saturated), it is a plausible size, and it lies on the machine (below the feed
belt and the people at the back). FastSAM was chosen over the zero-shot detector
because it gives each peach its own outline even where peaches touch, so the
colour read stays on one fruit; the detector, prompted "peach", found nothing,
and prompted "apple" it boxed queued fruit in pairs. Which segments touch is
kept in the output as well ("touch").

Peaches roll fast along the lanes, so following them by mask overlap alone
breaks; each track predicts where its peach will be from its last two
positions, and detections are matched to predictions by distance (Hungarian),
within a radius that scales with the peach's size.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment
from ultralytics import FastSAM

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VIDEO = ROOT / "input" / "peach_sizer.mp4"
OUT = ROOT / "output"

IMGSZ = 1280
TOP_Y = 270            # px: above this is the feed belt and the people behind the machine
MIN_AREA, MAX_AREA = 1200, 90000
FRUIT_SHARE = 0.50
MATCH_R = 0.9          # match radius, in peach diameters
MAX_GAP = 3
TOUCH_PX = 6           # two peaches whose masks come within this many px touch


def peach_share(hsv, m):
    px = hsv[m]
    if not len(px):
        return 0.0
    h, s, v = px[:, 0], px[:, 1], px[:, 2]
    return float(np.mean(((h <= 25) | (h >= 165)) & (s > 90) & (v > 45)))


def outline(m):
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return []
    c = cv2.approxPolyDP(max(cs, key=cv2.contourArea), 2.0, True)
    return c.reshape(-1, 2).tolist()


def main():
    model = FastSAM(str(ROOT / "weights" / "FastSAM-x.pt"))
    cap = cv2.VideoCapture(str(VIDEO))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    tracks = {}            # tid -> {"pos": [(f, x, y)], "d": diameter}
    next_id = 1
    frames = []
    kernel = np.ones((TOUCH_PX * 2 + 1, TOUCH_PX * 2 + 1), np.uint8)
    t0 = time.time()
    f = 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        f += 1
        hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        r = model(im, device="cpu", retina_masks=True, imgsz=IMGSZ, conf=0.3, iou=0.9, verbose=False)[0]
        cand = []
        if r.masks is not None:
            for mk in r.masks.data.cpu().numpy():
                m = mk > 0.5
                a = int(m.sum())
                if a < MIN_AREA or a > MAX_AREA:
                    continue
                ys, xs = np.nonzero(m)
                cy, cx = float(ys.mean()), float(xs.mean())
                if cy < TOP_Y or peach_share(hsv, m) < FRUIT_SHARE:
                    continue
                cand.append({"m": m, "a": a, "cx": cx, "cy": cy, "box": [int(xs.min()), int(ys.min()),
                                                                           int(xs.max()), int(ys.max())]})
        # one peach, one segment: drop a segment mostly inside a bigger one
        cand.sort(key=lambda c: -c["a"])
        kept = []
        for c in cand:
            if any((c["m"] & k["m"]).sum() > 0.5 * c["a"] for k in kept):
                continue
            kept.append(c)
        # which peaches touch another
        grown = [cv2.dilate(k["m"].astype(np.uint8), kernel) > 0 for k in kept]
        for i, k in enumerate(kept):
            k["touch"] = [j for j in range(len(kept)) if j != i and (grown[i] & kept[j]["m"]).any()]
        # follow: predicted position vs detection, Hungarian on distance
        live = [t for t, tr in tracks.items() if f - tr["pos"][-1][0] <= MAX_GAP]
        pred = []
        for t in live:
            p = tracks[t]["pos"]
            if len(p) >= 2:
                (f1, x1, y1), (f2, x2, y2) = p[-2], p[-1]
                k_ = (f - f2) / max(f2 - f1, 1)
                pred.append((x2 + (x2 - x1) * k_, y2 + (y2 - y1) * k_))
            else:
                pred.append(p[-1][1:])
        assign = {}
        if live and kept:
            cost = np.full((len(kept), len(live)), 1e6)
            for i, k in enumerate(kept):
                d = np.sqrt(k["a"] / np.pi) * 2
                for j, t in enumerate(live):
                    dist = np.hypot(k["cx"] - pred[j][0], k["cy"] - pred[j][1])
                    if dist <= MATCH_R * max(d, tracks[t]["d"]):
                        cost[i, j] = dist
            rows, cols = linear_sum_assignment(cost)
            for i, j in zip(rows, cols):
                if cost[i, j] < 1e6:
                    assign[i] = live[j]
        objs = []
        for i, k in enumerate(kept):
            tid = assign.get(i)
            if tid is None:
                tid = next_id
                next_id += 1
                tracks[tid] = {"pos": [], "d": 0.0}
            d = float(np.sqrt(k["a"] / np.pi) * 2)
            tracks[tid]["pos"].append((f, k["cx"], k["cy"]))
            tracks[tid]["d"] = d
            k["tid"] = tid
        for k in kept:
            objs.append({"tid": k["tid"], "box": k["box"], "cx": round(k["cx"], 1), "cy": round(k["cy"], 1),
                         "area": k["a"], "touch": [kept[j]["tid"] for j in k["touch"]], "poly": outline(k["m"])})
        frames.append({"frame": f, "objects": objs})
        if f % 20 == 0:
            print(f"frame {f}/{n}  peaches {len(objs)}  ids {next_id - 1}  {(time.time() - t0) / f:.2f} s/frame",
                  flush=True)
    OUT.mkdir(exist_ok=True)
    (OUT / "tracks.json").write_text(json.dumps({"video": VIDEO.name, "fps": fps, "size": [1920, 1080],
                                                 "top_y": TOP_Y, "frames": frames}))
    print("done:", next_id - 1, "ids ->", OUT / "tracks.json")


if __name__ == "__main__":
    main()
