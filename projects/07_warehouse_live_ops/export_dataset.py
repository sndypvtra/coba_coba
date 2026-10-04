#!/usr/bin/env python3
"""#18 - A training set per camera angle, cut from the synthetic recording's labels.

The detector in this PoC is zero-shot: it was never trained on this building,
and it shows (README, "Accuracy"). The synthetic recording carries a labelled box
for every person, forklift and pallet truck in every camera, so it can be turned
into a fine-tuning set directly - no annotation work. This writes one set per
angle group (the groups `evaluate.angle_group` uses for #17), plus one with every
camera, in the YOLO format Ultralytics trains from:

    output/training_sets/<group>/images/{train,val}/<camera>_<frame>.jpg
    output/training_sets/<group>/labels/{train,val}/<camera>_<frame>.txt
    output/training_sets/<group>/data.yaml

Training needs a GPU (about an hour per set on one); this sandbox has none, so
the sets are built and checked here and trained elsewhere:

    yolo detect train data=output/training_sets/semua_cctv/data.yaml model=yolo11s.pt imgsz=1280 epochs=60

Leakage. Consecutive frames are near copies, so a frame-level split would put
the same moment in train and val. The split is by time instead: the last 60 s
are validation, and the two windows the videos are scored on (23-53 s and
116-146 s) are left out of both, so a model trained on these sets can still be
scored honestly on them.

    python export_dataset.py                 # one frame every 5 s per camera
    python export_dataset.py --every 1       # one per second: ~5,000 images, ~1.5 GB
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import draw as dr  # noqa: E402
from config import DOCS, OUTPUT, output_dir  # noqa: E402
from evaluate import angle_group  # noqa: E402
from scene import KINDS, Labels, load_cameras, video_path  # noqa: E402

SCENE = "warehouse_000"
CLASSES = {"Person": 0, "Forklift": 1, "PalletTruck": 2}
NAMES = ["person", "forklift", "pallet_truck"]
MIN_PX = 8                 # a box smaller than this on either side teaches nothing
VAL_FROM_S = 240.0         # the last minute of the 300 s recording is validation
FPS = 30


def held_out() -> list[tuple[int, int]]:
    """Frame ranges the videos are scored on: never in a training set."""
    sel = json.loads((output_dir(SCENE) / "selection.json").read_text())
    return [(sel["video1_live_ops"]["start_frame"], sel["video1_live_ops"]["end_frame"]),
            (sel["video2_one_camera"]["start_frame"], sel["video2_one_camera"]["end_frame"])]


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().replace("≥", "ge").replace("<", "lt"))
    return s.strip("_")


def yolo_lines(boxes: np.ndarray, w: int, h: int) -> list[str]:
    """Label boxes (kind, x1, y1, x2, y2) as YOLO text lines: class cx cy bw bh, normalised."""
    out = []
    for k, x1, y1, x2, y2 in boxes:
        x1, x2 = max(0.0, x1), min(float(w), x2)
        y1, y2 = max(0.0, y1), min(float(h), y2)
        if x2 - x1 < MIN_PX or y2 - y1 < MIN_PX:
            continue
        out.append(f"{CLASSES[KINDS[int(k)]]} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} "
                   f"{(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
    return out


def export(every_s: float, quality: int = 90) -> dict:
    cams = load_cameras(SCENE)
    labels = Labels(SCENE, list(cams))
    keep_out = held_out()
    root = OUTPUT / "training_sets"
    if root.exists():
        shutil.rmtree(root)
    step = max(1, int(round(every_s * FPS)))
    frames = [f for f in range(0, labels.n_frames, step)
              if not any(a <= f < b for a, b in keep_out)]
    groups = {c: angle_group(cams[c]) for c in sorted(cams)}
    stats = defaultdict(lambda: {"cameras": set(), "train": Counter(), "val": Counter(),
                                 "images": Counter()})
    preview = {}
    for cid in sorted(cams):
        cam = cams[cid]
        lab = labels.boxes_in(cid, frames=np.array(frames))
        lab = lab[np.isin(lab[:, 1], [KINDS.index(k) for k in CLASSES])]
        cap = cv2.VideoCapture(str(video_path(SCENE, cid)))
        for f in frames:
            rows = lab[lab[:, 0] == f]
            lines = yolo_lines(rows[:, [1, 7, 8, 9, 10]], cam.width, cam.height)
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, img = cap.read()
            if not ok:
                continue
            split = "val" if f >= VAL_FROM_S * FPS else "train"
            name = f"{cid}_{f:05d}"
            for g in (groups[cid], "semua CCTV"):
                d = root / slug(g)
                (d / "images" / split).mkdir(parents=True, exist_ok=True)
                (d / "labels" / split).mkdir(parents=True, exist_ok=True)
                if g == groups[cid]:
                    cv2.imwrite(str(d / "images" / split / f"{name}.jpg"), img,
                                [cv2.IMWRITE_JPEG_QUALITY, quality])
                else:
                    # the all-camera set links to the group's copy instead of a second JPEG
                    src = root / slug(groups[cid]) / "images" / split / f"{name}.jpg"
                    dst = d / "images" / split / f"{name}.jpg"
                    try:
                        dst.hardlink_to(src)
                    except OSError:
                        shutil.copyfile(src, dst)
                (d / "labels" / split / f"{name}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
                st = stats[g]
                st["cameras"].add(cid)
                st["images"][split] += 1
                for ln in lines:
                    st[split][NAMES[int(ln.split()[0])]] += 1
            if lines and len(lines) > len(preview.get(groups[cid], (None, None, []))[2]):
                preview[groups[cid]] = (cid, img, lines)
        cap.release()
        print(f"  {cid}: {groups[cid]}", flush=True)

    summary = {}
    for g, st in stats.items():
        d = root / slug(g)
        (d / "data.yaml").write_text(
            f"# {g}: {', '.join(sorted(st['cameras']))}\n"
            f"# train: frames before {VAL_FROM_S:.0f} s; val: from {VAL_FROM_S:.0f} s; "
            f"held out (the PoC's scoring windows): {keep_out}\n"
            f"path: {d.resolve()}\ntrain: images/train\nval: images/val\n"
            f"names:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)))
        summary[g] = {"folder": str(d.relative_to(OUTPUT.parent)), "cameras": sorted(st["cameras"]),
                      "images": dict(st["images"]), "boxes_train": dict(st["train"]),
                      "boxes_val": dict(st["val"])}
    out = {"every_s": every_s, "held_out_frames": keep_out, "val_from_s": VAL_FROM_S,
           "min_box_px": MIN_PX, "classes": NAMES, "sets": summary}
    (root / "summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    _preview(preview, out)
    return out


def _preview(preview: dict, out: dict) -> None:
    """One labelled example per angle group, for the README."""
    groups = [g for g in out["sets"] if g != "semua CCTV" and g in preview]
    tw, th = 640, 360
    img = np.full((70 + th * ((len(groups) + 1) // 2) + 10, 2 * tw + 30, 3), dr.BG, np.uint8)
    T = dr.Texts()
    T.add("#18 · DATASET LATIH PER SUDUT KAMERA (label dataset, format YOLO)", (12, 10), 20, dr.INK, True)
    T.add(f"1 frame tiap {out['every_s']:g} s per CCTV · validasi = 60 s terakhir · "
          "jendela uji video 1 dan 2 tidak dipakai", (12, 40), 14, dr.MUTED)
    colours = [dr.PERSON, dr.FORKLIFT, dr.PALLET]
    for i, g in enumerate(groups):
        cid, frame, lines = preview[g]
        h, w = frame.shape[:2]
        t = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
        for ln in lines:
            k, cx, cy, bw, bh = (float(v) for v in ln.split())
            x1, y1 = int((cx - bw / 2) * tw), int((cy - bh / 2) * th)
            x2, y2 = int((cx + bw / 2) * tw), int((cy + bh / 2) * th)
            cv2.rectangle(t, (x1, y1), (x2, y2), colours[int(k)], 1, cv2.LINE_AA)
        x, y = 10 + (i % 2) * (tw + 10), 70 + (i // 2) * th
        img[y:y + th - 6, x:x + tw] = t[:th - 6]
        s = out["sets"][g]
        n = sum(s["images"].values())
        T.add(f"{g} · {len(s['cameras'])} CCTV · {n} gambar", (x + 6, y + 6), 14, dr.INK, True, bg=dr.BG, pad=3)
    T.flush(img)
    DOCS.mkdir(exist_ok=True)
    cv2.imwrite(str(DOCS / "training_sets_preview.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 88])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--every", type=float, default=5.0, help="seconds between frames taken per camera")
    args = ap.parse_args()
    out = export(args.every)
    for g, s in out["sets"].items():
        print(f"{g:45s} {len(s['cameras']):2d} CCTV  {s['images']}  train {s['boxes_train']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
