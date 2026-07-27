"""Measure detection latency at frame entry, and sweep thresholds against it.

The question this answers: when an object enters the frame, how far does it
travel before the pipeline actually locks onto it?

For each clip the entry edge is derived from the measured motion vector (these
belts run left, so objects enter from the right). For every track we record the
position where it was first seen and express it as *entry lag*: the fraction of
the frame the object had already crossed before being picked up. 0.00 means it
was caught right at the edge, 0.30 means it was already 30% into the frame.

Reported per setting:
  det/f      mean detections per frame
  tracks     distinct track IDs
  lag_med    median entry lag (lower is better)
  lag_p90    90th percentile entry lag - the stragglers
  early%     share of tracks picked up within 15% of the entry edge

Usage:
  python src/tune_thresholds.py --clips 01,02,03
  python src/tune_thresholds.py --clips 02 --confs 0.05,0.08,0.11
"""

from __future__ import annotations

import argparse
import collections
import warnings
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLOE

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
import sys

sys.path.insert(0, str(ROOT))
from src.conveyor_count import CLIPS, filter_detections  # noqa: E402

import supervision as sv  # noqa: E402


def entry_axis(motion: tuple[float, float]) -> tuple[int, bool]:
    """Return (axis, from_high_edge) for where objects enter the frame.

    axis 0 = x, 1 = y. from_high_edge means they come in at the right/bottom.
    """
    mx, my = motion
    if abs(mx) >= abs(my):
        return 0, mx < 0  # moving left -> entering from the right edge
    return 1, my < 0


def run(cfg, conf, tracker_path, imgsz, min_age, max_frames):
    model = YOLOE(str(ROOT / "weights" / "yoloe-11l-seg.pt"))
    model.set_classes(cfg.prompts, model.get_text_pe(cfg.prompts))

    cap = cv2.VideoCapture(str(ROOT / "videos" / cfg.filename))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    axis, from_high = entry_axis(cfg.motion)
    extent = w if axis == 0 else h

    first_pos: dict[int, float] = {}
    age = collections.Counter()
    n_det, n_frames = 0, 0

    while True:
        ok, frame = cap.read()
        if not ok or (max_frames and n_frames >= max_frames):
            break
        n_frames += 1
        r = model.track(
            frame,
            persist=True,
            tracker=str(tracker_path),
            conf=conf,
            iou=0.5,
            imgsz=imgsz,
            agnostic_nms=True,
            verbose=False,
        )[0]
        det = sv.Detections.from_ultralytics(r)
        det = filter_detections(det, cfg, w, h)
        n_det += len(det)
        if len(det) == 0 or det.tracker_id is None:
            continue
        for box, tid in zip(det.xyxy, det.tracker_id):
            if tid is None:
                continue
            tid = int(tid)
            age[tid] += 1
            # only bank the position once the track is old enough to be real
            if age[tid] == min_age and tid not in first_pos:
                c = (box[0] + box[2]) / 2 if axis == 0 else (box[1] + box[3]) / 2
                first_pos[tid] = 1.0 - c / extent if from_high else c / extent
    cap.release()

    lags = np.array(list(first_pos.values())) if first_pos else np.array([1.0])
    return {
        "det_f": n_det / max(n_frames, 1),
        "tracks": len(first_pos),
        "lag_med": float(np.median(lags)),
        "lag_p90": float(np.percentile(lags, 90)),
        "early": float((lags <= 0.15).mean()),
    }


def make_tracker(base: Path, out: Path, **over) -> Path:
    cfg = yaml.safe_load(base.read_text())
    reid = cfg.get("model")
    if reid and reid != "auto" and not Path(reid).is_absolute():
        cfg["model"] = str((ROOT / reid).resolve())
    cfg.update(over)
    out.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", default="01,02,03")
    ap.add_argument("--confs", default="")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--max-frames", type=int, default=110)
    ap.add_argument("--scratch", default="/tmp")
    args = ap.parse_args()

    base = ROOT / "src" / "trackers" / "tracktrack_zeroshot.yaml"
    scratch = Path(args.scratch)
    wanted = args.clips.split(",")

    for cfg in CLIPS:
        if cfg.filename[:2] not in wanted:
            continue
        print(f"\n=== {cfg.filename}  (current conf={cfg.conf}, min_age={cfg.min_track_age})")
        print(f"{'setting':46s} {'det/f':>6s} {'tracks':>7s} {'lag_med':>8s} {'lag_p90':>8s} {'early%':>7s}")

        confs = (
            [float(x) for x in args.confs.split(",")]
            if args.confs
            else sorted({round(cfg.conf * m, 3) for m in (1.0, 0.7, 0.5, 0.35)})
        )
        # A: detection threshold sweep, tracker gates left at their tuned values
        for c in confs:
            tp = make_tracker(base, scratch / "tt_base.yaml")
            r = run(cfg, c, tp, args.imgsz, cfg.min_track_age, args.max_frames)
            tag = f"conf={c}" + ("  <- current" if abs(c - cfg.conf) < 1e-6 else "")
            print(
                f"  {tag:44s} {r['det_f']:6.1f} {r['tracks']:7d} "
                f"{r['lag_med']:8.3f} {r['lag_p90']:8.3f} {r['early']*100:6.0f}%"
            )
        # B: best-case early acquisition - lowest conf plus opened tracker gates
        lo = min(confs)
        tp = make_tracker(
            base,
            scratch / "tt_open.yaml",
            track_high_thresh=0.12,
            track_low_thresh=0.03,
            new_track_thresh=0.15,
            min_track_len=2,
        )
        r = run(cfg, lo, tp, args.imgsz, cfg.min_track_age, args.max_frames)
        print(
            f"  {f'conf={lo} + open tracker gates':44s} {r['det_f']:6.1f} {r['tracks']:7d} "
            f"{r['lag_med']:8.3f} {r['lag_p90']:8.3f} {r['early']*100:6.0f}%"
        )
        # C: same, but also drop the maturity gate to 3 frames
        r = run(cfg, lo, tp, args.imgsz, 3, args.max_frames)
        print(
            f"  {f'conf={lo} + open gates + min_age=3':44s} {r['det_f']:6.1f} {r['tracks']:7d} "
            f"{r['lag_med']:8.3f} {r['lag_p90']:8.3f} {r['early']*100:6.0f}%"
        )


if __name__ == "__main__":
    main()
