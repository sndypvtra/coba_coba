"""Run the project's counting engine once and keep everything the dashboard needs.

Same detector, prompts, confidence floor, ROI, tracker and counting line as
`main.py` (all from config.py); the only difference is what is kept. For every
frame: each tracker-confirmed object with its id, box and colour, and the
crossings. Colour is read inside the segmentation mask, in CIELAB, as a hue
angle h = atan2(b*, a*): red fruit sits low, orange higher, green-yellow higher
still. That is the standard way tomato colour is graded, and it is what
grade.py turns into ripeness classes.

    python dashboard/tracks.py        # -> output/tracks.json (slow: ~1.5 s a frame on CPU)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import supervision as sv  # noqa: E402
from ultralytics import YOLOE  # noqa: E402

from config import CLIP as cfg  # noqa: E402
from factory_vision.counting.geometry import build_counting_line, filter_detections  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR  # noqa: E402
from factory_vision.tracking import resolve_tracker_cfg  # noqa: E402

IMGSZ = 1280
OUT = ROOT / "output"


def colour(frame_lab, frame_bgr, mask, box):
    """Median hue angle, chroma and lightness inside the mask, plus a sharpness reading."""
    x0, y0, x1, y1 = (int(v) for v in box)
    m = mask[y0:y1, x0:x1] if mask is not None else None
    lab = frame_lab[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
    if m is not None and m.size:
        sel = m.reshape(-1)
        if sel.sum() > 30:
            lab = lab[sel]
    L = lab[:, 0] * 100 / 255
    a = lab[:, 1] - 128
    b = lab[:, 2] - 128
    keep = (L > 15) & (L < 95)                     # leave out specular highlights and deep shadow
    if keep.sum() > 20:
        L, a, b = L[keep], a[keep], b[keep]
    hue = float(np.degrees(np.arctan2(np.median(b), np.median(a))))
    chroma = float(np.hypot(np.median(a), np.median(b)))
    g = cv2.cvtColor(frame_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(g, cv2.CV_32F).var()) if g.size else 0.0
    return round(hue, 1), round(chroma, 1), round(float(np.median(L)), 1), round(sharp, 1)


def main():
    src = ROOT / "input" / cfg.filename
    info = sv.VideoInfo.from_video_path(str(src))
    w, h = info.width, info.height
    tracker_cfg = resolve_tracker_cfg("tracktrack", cfg.tracker_overrides, cfg.filename[:2], OUT)
    model = YOLOE(str(WEIGHTS_DIR / "yoloe-11l-seg.pt"))
    model.set_classes(cfg.prompts, model.get_text_pe(cfg.prompts))
    a, b = build_counting_line(cfg)
    line = sv.LineZone(start=a, end=b, triggering_anchors=(sv.Position.CENTER,), minimum_crossing_threshold=2)
    age: dict[int, int] = {}
    frames, crossings = [], []
    cap = cv2.VideoCapture(str(src))
    idx = 0
    t_start = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        r = model.track(frame, persist=True, tracker=str(tracker_cfg), conf=cfg.conf, iou=0.5, imgsz=IMGSZ,
                        agnostic_nms=True, verbose=False)[0]
        det = filter_detections(sv.Detections.from_ultralytics(r), cfg, w, h)
        if len(det) and det.tracker_id is not None:
            tracked = det[np.array([t is not None for t in det.tracker_id])]
        else:
            tracked = det[np.zeros(len(det), dtype=bool)]
        for t in (tracked.tracker_id if len(tracked) else []):
            age[int(t)] = age.get(int(t), 0) + 1
        locked = tracked[np.array([age[int(t)] >= cfg.min_track_age for t in tracked.tracker_id])] \
            if len(tracked) else tracked
        crossed, _ = line.trigger(locked)
        for j, flag in enumerate(crossed):
            if flag:
                crossings.append({"frame": idx, "tid": int(locked.tracker_id[j])})
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        objs = []
        for k in range(len(tracked)):
            box = tracked.xyxy[k]
            mask = tracked.mask[k] if tracked.mask is not None else None
            hue, chroma, light, sharp = colour(lab, frame, mask, box)
            objs.append({"tid": int(tracked.tracker_id[k]), "box": [round(float(v), 1) for v in box],
                         "conf": round(float(tracked.confidence[k]), 3), "age": age[int(tracked.tracker_id[k])],
                         "hue": hue, "chroma": chroma, "light": light, "sharp": sharp})
        frames.append({"frame": idx, "objects": objs})
        if idx % 25 == 0:
            print(f"frame {idx}/{info.total_frames}  counted {line.in_count}  "
                  f"{(time.time() - t_start) / idx:.2f} s/frame", flush=True)
    out = {"video": cfg.filename, "fps": info.fps, "size": [w, h], "prompts": cfg.prompts, "conf": cfg.conf,
           "line": [[a.x, a.y], [b.x, b.y]], "roi_y": list(cfg.roi_y), "counted": line.in_count,
           "crossings": crossings, "frames": frames}
    OUT.mkdir(exist_ok=True)
    (OUT / "tracks.json").write_text(json.dumps(out))
    print("counted", line.in_count, "->", OUT / "tracks.json")


if __name__ == "__main__":
    main()
