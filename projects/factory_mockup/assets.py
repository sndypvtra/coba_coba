#!/usr/bin/env python3
"""Pictures for the Factory Vision mockups, from the proof of concept.

    python factory_mockup/assets.py      # -> factory_mockup/img/

The mockup pages are their own web app and TV dashboard: they do not reuse the PoC dashboard videos.
What they take from the PoC is the camera picture with the AI overlay drawn on it (boxes, labels,
count gate) and nothing else, exported clean by each dashboard script:

    python dashboard/dashboard.py --cam 40 80 125 133          # 11_tomato_ripeness
    python dashboard/dashboard.py --cam 60 150 200 240 245     # 12_lime_grading
    python dashboard/dashboard.py --cam 120 180 230 232        # 04_bottle_fill_volume
    python dashboard/dashboard.py --cam 165 300 505 511        # 03_parcel_dimensioning
    python analytics/dashboard.py line --cam 89 95 222 230 413 440   # 08_pack_completeness
    python analytics/dashboard.py pack --cam 284 290 412 461 500 850

* <product>_cam_<frame>.jpg   the camera picture (1280 x 720) with the AI overlay only
* snap_*.jpg                   evidence snapshots: off-colour tomatoes, lemons outside the main lot,
                               parcels, the short trays and the short box
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
P = HERE.parent
OUT = HERE / "img"
K = 1280 / 1920                                # source frame -> camera picture
PACK = "08_pack_completeness/output/analytics/cam"

CAMS = {   # product: (folder, file pattern, frames)
    "tomato": ("11_tomato_ripeness/output/cam", "cam_{:04d}.jpg", [40, 80, 125, 133]),
    "lemon": ("12_lime_grading/output/cam", "cam_{:04d}.jpg", [60, 150, 200, 240, 245]),
    "fill": ("04_bottle_fill_volume/output/cam", "cam_{:04d}.jpg", [120, 180, 230, 232]),
    "tray": (PACK, "line_qc_cam_{:04d}.jpg", [95, 230, 440]),
    "packing": (PACK, "packing_qc_cam_{:04d}.jpg", [290, 500, 850]),
    "parcel": ("03_parcel_dimensioning/output/cam", "cam_{:04d}.jpg", [165, 300, 505, 511]),
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


def fruit_snaps(video, tracks, items, prefix, size=480):
    """A square crop of each item at the frame it was counted, from the source footage (no overlay)."""
    tr = json.loads((P / tracks).read_text())
    pics = frames(video, [t["frame"] - 1 for t in items])
    out = []
    for n, t in enumerate(items):
        fr = tr["frames"][t["frame"] - 1]
        o = next((o for o in fr["objects"] if o["tid"] == t["tid"]), None)
        if o is None or t["frame"] - 1 not in pics:
            continue
        x0, y0, x1, y1 = o["box"]
        side = int(max(x1 - x0, y1 - y0) * 1.5)
        c = crop(pics[t["frame"] - 1], (x0 + x1) / 2, (y0 + y1) / 2, side, side)
        name = f"{prefix}_{n}.jpg"
        cv2.imwrite(str(OUT / name), cv2.resize(c, (size, size), interpolation=cv2.INTER_CUBIC), [cv2.IMWRITE_JPEG_QUALITY, 95])
        out.append({"img": name, **{k: t[k] for k in t if k != "tid"}})
    return out


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for k, (folder, pat, fs) in CAMS.items():
        for f in fs:
            src = P / folder / pat.format(f)
            if not src.exists():
                raise SystemExit(f"missing {src}: export it with the dashboard's --cam option (see the top of this file)")
            shutil.copy(src, OUT / f"{k}_cam_{f}.jpg")

    s = json.loads((P / "11_tomato_ripeness/output/tomato_ripeness_summary.json").read_text())
    tom = fruit_snaps("11_tomato_ripeness/input/tomato_lanes.mp4", "11_tomato_ripeness/output/tracks.json",
                      [t for t in s["tomatoes"] if t["usda_class"] != "Red"], "snap_tomato")
    ls = json.loads((P / "12_lime_grading/output/lime_grading_summary.json").read_text())
    main_lot = ls["main_lot"]
    lem = fruit_snaps("12_lime_grading/input/lime_chain.mp4", "12_lime_grading/output/tracks.json",
                      [t for t in ls["lemons"] if t["lot"] != main_lot][-6:], "snap_lemon")

    # parcels: a crop of each counted parcel, 16:9, from the source footage
    ps = json.loads((P / "03_parcel_dimensioning/output/parcel_dimensioning_summary.json").read_text())["parcels"]
    rec = json.loads((P / "03_parcel_dimensioning/output/record.json").read_text())
    pics = frames("03_parcel_dimensioning/input/03_packages_conveyor.mp4", [p["frame"] - 1 for p in ps])
    par = []
    for p in ps:
        o = next((o for o in rec["frames"][p["frame"] - 1]["objects"] if o["tid"] == p["tid"]), None)
        if o is None or p["frame"] - 1 not in pics:
            continue
        x0, y0, x1, y1 = o["box"]
        w = int(max(x1 - x0, (y1 - y0) * 16 / 9) * 1.4)
        c = crop(pics[p["frame"] - 1], (x0 + x1) / 2, (y0 + y1) / 2, w, int(w * 9 / 16))
        name = f"snap_parcel_{p['tid']}.jpg"
        cv2.imwrite(str(OUT / name), cv2.resize(c, (640, 360), interpolation=cv2.INTER_CUBIC), [cv2.IMWRITE_JPEG_QUALITY, 95])
        par.append(name)

    # the short trays and the short box: the clean camera picture at the moment they were judged
    for f in (89, 222, 413):
        cam = cv2.imread(str(P / PACK / f"line_qc_cam_{f:04d}.jpg"))
        cv2.imwrite(str(OUT / f"snap_tray_{f}.jpg"), crop(cam, 640, 360, 900, 506), [cv2.IMWRITE_JPEG_QUALITY, 95])
    for f in (284, 412, 461):
        shutil.copy(P / PACK / f"packing_qc_cam_{f:04d}.jpg", OUT / f"snap_box_{f}.jpg")

    (OUT / "meta.json").write_text(json.dumps({"frames": {k: v[2] for k, v in CAMS.items()}, "tomato_off": tom,
                                               "lemon_off": lem, "parcels": par}, indent=1, ensure_ascii=False))
    print(len(list(OUT.glob("*.jpg"))), "pictures ->", OUT)


if __name__ == "__main__":
    main()
