"""Read how much of each peach's skin is red, frame by frame, on the lines.

    python dashboard/colour.py           # after segment.py -> output/colour.json (~1 min)

Peaches roll on the sizer's rollers, so over the frames a peach shows most of
its skin; its red share is the median of what each frame shows. A skin pixel is
red when its CIELAB hue angle h = atan2(b*, a*) is below RED_HUE: the blush of
these peaches sits at 0-30 deg, red skin under the lamps at 30-37 deg, the
yellow-orange ground colour at 44-60 deg.
Highlights, deep shadow and grey pixels (the rollers between fruit) are left out.
FastSAM now and then outlines a group of small far-away peaches as one segment;
a segment much wider than the usual peach at its height (OVERSIZE) is not read.
Every peach on the lines is read, from ZONE_Y (just below the feed belt, where
the fruit drops into the lines) down to the bottom of the picture.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VIDEO = ROOT / "input" / "peach_sizer.mp4"
OUT = ROOT / "output"

ZONE_Y = 300           # px: the grading zone starts here, below the feed belt
RED_HUE = 38.0         # deg: below this a skin pixel is red (lit red skin reaches 30-37, yellow ground colour 44-60)
MIN_PX = 300           # skin pixels needed for a read
OVERSIZE = 1.6         # a segment this many times wider than a usual peach at its height is a group of peaches


def red_share(lab, poly, shape):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.array(poly, np.int32)], 1)
    m = cv2.erode(m, np.ones((5, 5), np.uint8)) > 0        # keep off the edge, where the roller shows through
    px = lab[m].astype(np.float32)
    L = px[:, 0] * 100 / 255
    a, b = px[:, 1] - 128, px[:, 2] - 128
    keep = (L > 15) & (L < 90) & (np.hypot(a, b) > 15)
    if keep.sum() < MIN_PX:
        return None
    h = np.degrees(np.arctan2(b[keep], a[keep]))
    return float(np.mean(h < RED_HUE))


def on_line1(x, y):
    return x < 0.9 * y - 100


def usual_width(tr):
    """Median peach width (sqrt of area) per 100 px band of height, on line 1 and on lines 2-6."""
    a = np.array([(o["cx"], o["cy"], np.sqrt(o["area"])) for fr in tr["frames"] for o in fr["objects"]
                  if o["cy"] >= ZONE_Y])
    med = {}
    for side in (True, False):
        for y0 in range(ZONE_Y, 1080, 100):
            m = (on_line1(a[:, 0], a[:, 1]) == side) & (a[:, 1] >= y0) & (a[:, 1] < y0 + 100)
            if m.sum() >= 10:
                med[(side, y0)] = float(np.median(a[m, 2]))
    return med


def oversize(o, med):
    m = med.get((bool(on_line1(o["cx"], o["cy"])), int((o["cy"] - ZONE_Y) // 100) * 100 + ZONE_Y))
    return m is not None and np.sqrt(o["area"]) > OVERSIZE * m


def main():
    tr = json.loads((OUT / "tracks.json").read_text())
    med = usual_width(tr)
    skipped = []
    cap = cv2.VideoCapture(str(VIDEO))
    reads = {}
    for fr in tr["frames"]:
        ok, im = cap.read()
        if not ok:
            break
        lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
        for o in fr["objects"]:
            if o["cy"] < ZONE_Y or len(o["poly"]) < 3:
                continue
            if oversize(o, med):
                skipped.append([o["tid"], fr["frame"]])
                continue
            s = red_share(lab, o["poly"], im.shape[:2])
            if s is not None:
                reads.setdefault(str(o["tid"]), []).append([fr["frame"], round(s, 3)])
    (OUT / "colour.json").write_text(json.dumps({"zone_y": ZONE_Y, "red_hue": RED_HUE, "reads": reads,
                                                "oversize": skipped}))
    print(len(reads), "pieces of track read,", len(skipped), "oversize segments skipped ->", OUT / "colour.json")


if __name__ == "__main__":
    main()
