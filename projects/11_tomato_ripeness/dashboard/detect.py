"""Detect and follow every tomato, and read its colour from inside its box.

    python dashboard/detect.py        # -> output/tracks.json (~1.5 s a frame on CPU)

Detection only: YOLOE, prompted with words, gives a box and a score per fruit;
no mask is used anywhere. TrackTrack keeps one identity per tomato from frame to
frame. The colour is read inside an ellipse at the centre of the box (half its
width and height), which stays on the fruit and off the belt and the
neighbours; in CIELAB, as the hue angle h = atan2(b*, a*) of the median a* and
b*, with highlights and deep shadow left out. Red fruit sits lowest, orange
higher, yellow and green higher still.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLOE

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VIDEO = ROOT / "input" / "tomato_lanes.mp4"
WEIGHTS = ROOT / "weights"
OUT = ROOT / "output"

PROMPTS = ["tomato", "orange fruit"]   # "orange fruit" picks up the paler, orange tomatoes "tomato" alone scores low
CONF = 0.06                            # zero-shot scores run low; the tracker's own gates do the rest
IMGSZ = 1280
MIN_AREA, MAX_AREA = 0.0008, 0.06      # box area as a share of the frame: drops specks and boxes over several fruit
TRACKER = {"track_high_thresh": 0.12, "track_low_thresh": 0.03, "new_track_thresh": 0.15, "min_track_len": 2}
ELLIPSE = 0.25                         # semi-axes of the colour ellipse, as a share of the box width and height


def tracker_cfg():
    """The tracker YAML with this clip's gates and an absolute path to the ReID backbone."""
    cfg = yaml.safe_load((HERE / "tracktrack.yaml").read_text())
    cfg["model"] = str(WEIGHTS / "yolo11n-cls.pt")
    cfg.update(TRACKER)
    dst = WEIGHTS / ".tracktrack_resolved.yaml"
    dst.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return dst


def colour(lab, gray, box):
    """Hue angle, chroma and lightness inside the centre ellipse of the box, and how sharp the box is."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    h, w = lab.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 - x0 < 6 or y1 - y0 < 6:
        return None
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.ellipse(m, ((x1 - x0) // 2, (y1 - y0) // 2),
                (max(2, int((x1 - x0) * ELLIPSE)), max(2, int((y1 - y0) * ELLIPSE))), 0, 0, 360, 1, -1)
    px = lab[y0:y1, x0:x1][m > 0].astype(np.float32)
    L = px[:, 0] * 100 / 255
    a, b = px[:, 1] - 128, px[:, 2] - 128
    keep = (L > 15) & (L < 92)
    if keep.sum() > 20:
        L, a, b = L[keep], a[keep], b[keep]
    ma, mb = float(np.median(a)), float(np.median(b))
    sharp = float(cv2.Laplacian(gray[y0:y1, x0:x1], cv2.CV_32F).var())
    return {"hue": round(float(np.degrees(np.arctan2(mb, ma))), 1), "chroma": round(float(np.hypot(ma, mb)), 1),
            "light": round(float(np.median(L)), 1), "sharp": round(sharp, 1)}


def main():
    model = YOLOE(str(WEIGHTS / "yoloe-11l-seg.pt"))
    model.set_classes(PROMPTS, model.get_text_pe(PROMPTS))
    trk = tracker_cfg()
    cap = cv2.VideoCapture(str(VIDEO))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames, t0, f = [], time.time(), 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        f += 1
        H, W = im.shape[:2]
        r = model.track(im, persist=True, tracker=str(trk), conf=CONF, iou=0.5, imgsz=IMGSZ, agnostic_nms=True,
                        verbose=False)[0]
        lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        objs = []
        if r.boxes is not None and r.boxes.id is not None:
            for box, tid, conf in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.id.cpu().numpy(),
                                      r.boxes.conf.cpu().numpy()):
                area = (box[2] - box[0]) * (box[3] - box[1]) / (W * H)
                if not MIN_AREA <= area <= MAX_AREA:
                    continue
                c = colour(lab, gray, box)
                if c is None:
                    continue
                objs.append({"tid": int(tid), "box": [round(float(v), 1) for v in box], "conf": round(float(conf), 3),
                             **c})
        frames.append({"frame": f, "objects": objs})
        if f % 20 == 0:
            print(f"frame {f}/{n}  tomatoes {len(objs)}  {(time.time() - t0) / f:.2f} s/frame", flush=True)
    OUT.mkdir(exist_ok=True)
    (OUT / "tracks.json").write_text(json.dumps({"video": VIDEO.name, "fps": fps, "size": [W, H],
                                                 "prompts": PROMPTS, "conf": CONF, "frames": frames}))
    print("done:", f, "frames ->", OUT / "tracks.json")


if __name__ == "__main__":
    main()
