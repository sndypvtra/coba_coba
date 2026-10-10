"""Read how much of each peach's skin is red, frame by frame, in the grading zone.

    python dashboard/colour.py           # after segment.py -> output/colour.json (~1 min)

Peaches roll on the sizer's rollers, so over the frames a peach shows most of
its skin; its red share is the median of what each frame shows. A skin pixel is
red when its CIELAB hue angle h = atan2(b*, a*) is below RED_HUE: the blush of
these peaches sits at 0-30 deg, the yellow-orange ground colour at 30-60 deg.
Highlights, deep shadow and grey pixels (the rollers between fruit) are left out.
Only the grading zone right of ZONE_X is read: there the peaches run one by one,
in focus and in full view.
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

ZONE_X = 1250          # px: the grading zone starts here
RED_HUE = 36.0         # deg: below this hue angle a skin pixel is red (lit red skin reaches 30-37, yellow ground colour 44-60)
MIN_PX = 300           # skin pixels needed for a read


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


def main():
    tr = json.loads((OUT / "tracks.json").read_text())
    cap = cv2.VideoCapture(str(VIDEO))
    reads = {}
    for fr in tr["frames"]:
        ok, im = cap.read()
        if not ok:
            break
        lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
        for o in fr["objects"]:
            if o["cx"] < ZONE_X or len(o["poly"]) < 3:
                continue
            s = red_share(lab, o["poly"], im.shape[:2])
            if s is not None:
                reads.setdefault(str(o["tid"]), []).append([fr["frame"], round(s, 3)])
    (OUT / "colour.json").write_text(json.dumps({"zone_x": ZONE_X, "red_hue": RED_HUE, "reads": reads}))
    print(len(reads), "peaches read ->", OUT / "colour.json")


if __name__ == "__main__":
    main()
