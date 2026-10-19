"""Prepare the package photo for the courier app mockup.

    python assets.py <photo.jpg>

Writes img/paket.jpg (the shipping label blurred, it carries a name, an address
and an order number) and img/geom.json: the parcel outline, its bounding box on
the floor, the 3D box drawn on the result screen, sample points for the depth
dots, and the two neighbouring cartons. Coordinates are pixels of the photo.

The outline is found with plain OpenCV (black plastic + red sticker on a light
floor), which is enough for a mockup; the app itself would use a segmentation
model prompted by the courier's tap.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "img"

# Label corners, read off the photo by eye and padded a little.
LABEL = [(264, 446), (694, 358), (782, 808), (350, 864)]
# The two cartons at the top of the photo: other parcels, not the one measured.
OTHERS = [(30, 0, 330, 172), (468, 0, 899, 326)]
# Size shown on the result screen. Footprint from the box below, scaled by the
# label (~10 cm, about 44 px/cm on the top of the parcel); height is a guess.
SIZE_CM = (27, 15, 6)
CAMERA = (450, 800)     # principal point, roughly the photo centre
SHRINK = 0.89           # floor face vs top face: camera ~0.55 m above, parcel 6 cm tall


def main(src: str) -> None:
    im = cv2.imread(src)
    H, W = im.shape[:2]
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = ((v < 70) | (((h < 10) | (h > 165)) & (s > 120) & (v > 80))).astype(np.uint8)
    m[:330] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    m = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    fill = np.zeros_like(m)
    cv2.drawContours(fill, cs, -1, 1, -1)
    fill = cv2.morphologyEx(fill, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    cs, _ = cv2.findContours(fill, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    outline = cv2.approxPolyDP(c, 4, True)[:, 0].tolist()

    # 3D box: the top face is the rectangle around the outline, the floor face is
    # the same rectangle pulled toward the camera centre (it is further away).
    top = cv2.boxPoints(cv2.minAreaRect(c))
    top = top[np.argsort(np.arctan2(top[:, 1] - top[:, 1].mean(), top[:, 0] - top[:, 0].mean()))]
    cx = np.array(CAMERA, float)
    base = cx + SHRINK * (top - cx)

    # depth dots on the parcel, and floor-grid dots around it
    yy, xx = np.mgrid[12:H:24, 12:W:24]
    on = fill[yy, xx] > 0
    dots = np.stack([xx[on], yy[on]], 1)
    rng = np.random.default_rng(7)
    dots = dots + rng.normal(0, 3, dots.shape)
    near = cv2.dilate(fill, np.ones((41, 41), np.uint8))
    gy, gx = np.mgrid[20:H:44, 20:W:44]
    free = near[gy, gx] == 0
    for x0, y0, x1, y1 in OTHERS:
        free &= ~((gx >= x0 - 20) & (gx <= x1 + 20) & (gy >= y0) & (gy <= y1 + 20))
    grid = np.stack([gx[free], gy[free]], 1)

    # blur the label: name, address, order number
    poly = np.int32(LABEL)
    mask = np.zeros((H, W), np.uint8)
    cv2.fillPoly(mask, [poly], 255)
    mask = cv2.GaussianBlur(mask, (9, 9), 0)[..., None] / 255.0
    soft = cv2.GaussianBlur(im, (0, 0), 9)
    soft = cv2.addWeighted(soft, 0.85, np.full_like(soft, 235), 0.15, 0)
    out = (im * (1 - mask) + soft * mask).astype(np.uint8)
    OUT.mkdir(exist_ok=True)
    cv2.imwrite(str(OUT / "paket.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, 92])

    r = lambda a: [[round(float(x), 1), round(float(y), 1)] for x, y in a]
    geom = {"W": W, "H": H, "outline": outline, "top": r(top), "base": r(base),
            "dots": r(dots), "grid": r(grid), "others": OTHERS, "size_cm": SIZE_CM,
            "camera": CAMERA}
    (OUT / "geom.json").write_text(json.dumps(geom))
    print(f"outline {len(outline)} pts, {len(dots)} depth dots, {len(grid)} grid dots")


if __name__ == "__main__":
    main(sys.argv[1])
