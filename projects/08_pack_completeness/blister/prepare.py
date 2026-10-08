"""Stage 0: reference frames of the three still segments and the maps between them.

usage: python3 prepare.py <work_dir> <mixkit_4750.mp4>

The sheet indexes twice in this clip (frames 35-43 and 127-134) and is still
otherwise, so one frame per still segment stands for the whole segment.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import segmap  # noqa: E402

WORK, SRC = sys.argv[1], sys.argv[2]
REFS = (17, 85, 145)
# rough sheet travel per index (pixels), from the clip's median optical flow; the
# fit below searches around it, since the blister pattern repeats every pocket
PRIOR = {17: (-590, 300), 145: (560, -270)}


def main():
    os.makedirs(WORK, exist_ok=True)
    cap = cv2.VideoCapture(SRC)
    i, got = 0, {}
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i in REFS:
            got[i] = f
            cv2.imwrite(f"{WORK}/ref_{i}.png", f)
        i += 1
    for k, prior in PRIOR.items():
        H, inl, n = segmap.fit(got[85], got[k], prior)
        np.save(f"{WORK}/H_85_{k}.npy", H)
        print(f"frame 85 -> {k}: {inl}/{n} patches agree")


if __name__ == "__main__":
    main()
