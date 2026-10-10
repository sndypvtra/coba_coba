#!/usr/bin/env python3
"""Pictures for the Factory Vision mockups, cut from the final dashboard videos of the PoC.

    python factory_mockup/assets.py      # -> factory_mockup/img/ (~20 s)

* <product>_dash_<frame>.jpg   a whole dashboard frame (1920 x 1080), for the TV dashboard pages
* <product>_cam_<frame>.jpg    the camera picture of that frame (1280 x 720), with the AI overlay
* snap_*.jpg                   evidence snapshots: the off-colour tomatoes, the short tray, the short box
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
P = HERE.parent
OUT = HERE / "img"
VX, VY, VW, VH = 16, 68, 1280, 720            # where the camera picture sits on every dashboard
K = VW / 1920

CLIPS = {
    "tomato": ("11_tomato_ripeness/output/tomato_ripeness.mp4", [40, 80, 125]),
    "lemon": ("12_lime_grading/output/lime_grading.mp4", [60, 150, 200, 240]),
    "fill": ("04_bottle_fill_volume/output/fill_inspection.mp4", [120, 180, 230]),
    "tray": ("08_pack_completeness/output/analytics/line_qc.mp4", [95, 230, 440]),
    "packing": ("08_pack_completeness/output/analytics/packing_qc.mp4", [290, 500, 850]),
    "parcel": ("03_parcel_dimensioning/output/parcel_dimensioning.mp4", [165, 300, 505]),
}


def frames(path, want):
    cap = cv2.VideoCapture(str(P / path))
    out = {}
    for f in sorted(set(want)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, im = cap.read()
        if ok:
            out[f] = im
    return out


def crop(im, cx, cy, w, h):
    H, W = im.shape[:2]
    x0, y0 = int(max(0, min(W - w, cx - w / 2))), int(max(0, min(H - h, cy - h / 2)))
    return im[y0:y0 + h, x0:x0 + w]


def main():
    OUT.mkdir(exist_ok=True)
    for k, (path, fs) in CLIPS.items():
        for f, im in frames(path, fs).items():
            cv2.imwrite(str(OUT / f"{k}_dash_{f}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 90])
            cv2.imwrite(str(OUT / f"{k}_cam_{f}.jpg"), im[VY:VY + VH, VX:VX + VW], [cv2.IMWRITE_JPEG_QUALITY, 90])

    # the off-colour (Light Red) tomatoes of the tomato lot, cut from the camera at the frame each was counted
    s = json.loads((P / "11_tomato_ripeness/output/tomato_ripeness_summary.json").read_text())
    tr = json.loads((P / "11_tomato_ripeness/output/tracks.json").read_text())
    off = [t for t in s["tomatoes"] if t["usda_class"] != "Red"]
    pics = frames("11_tomato_ripeness/input/tomato_lanes.mp4", [t["frame"] - 1 for t in off])
    snaps = []
    for n, t in enumerate(off):
        fr = tr["frames"][t["frame"] - 1]
        o = next((o for o in fr["objects"] if o["tid"] == t["tid"]), None)
        if o is None or t["frame"] - 1 not in pics:
            continue
        x0, y0, x1, y1 = o["box"]
        side = int(max(x1 - x0, y1 - y0) * 1.5)
        c = crop(pics[t["frame"] - 1], (x0 + x1) / 2, (y0 + y1) / 2, side, side)
        name = f"snap_tomato_{n}.jpg"
        cv2.imwrite(str(OUT / name), cv2.resize(c, (240, 240)), [cv2.IMWRITE_JPEG_QUALITY, 90])
        snaps.append({"img": name, "line": t["line"], "hue": t["hue"], "frame": t["frame"]})

    # the short tray and the short box, from the dashboard's own camera picture at the moment they were judged
    tray = frames(CLIPS["tray"][0], [89, 222, 413])
    for f, im in tray.items():
        cam = im[VY:VY + VH, VX:VX + VW]
        cv2.imwrite(str(OUT / f"snap_tray_{f}.jpg"), cv2.resize(crop(cam, 640, 360, 900, 506), (640, 360)),
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
    box = frames(CLIPS["packing"][0], [284, 412, 461])
    for f, im in box.items():
        cam = im[VY:VY + VH, VX:VX + VW]
        cv2.imwrite(str(OUT / f"snap_box_{f}.jpg"), cv2.resize(cam, (640, 360)), [cv2.IMWRITE_JPEG_QUALITY, 90])
    (OUT / "meta.json").write_text(json.dumps({"frames": {k: v[1] for k, v in CLIPS.items()}, "tomato_off": snaps}, indent=1))
    print(len(list(OUT.glob("*.jpg"))), "pictures ->", OUT)


if __name__ == "__main__":
    main()
