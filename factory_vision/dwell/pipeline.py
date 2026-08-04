"""Person detection, per-frame occupancy, and per-person dwell time.

Three numbers come out of this:

  occupancy   how many people are in the frame right now
  visitors    how many distinct people have been seen so far
  dwell       for each person, how long they have been in view

The first is a detection problem and is the easy one. The other two are tracking
problems, and they are only as good as the identity assignment: if a seated
customer is occluded by someone walking past and comes back with a new track ID,
one 8-minute visit is reported as two 4-minute visits and the visitor count goes
up by one. So this module reports the fragmentation signals alongside the
answer rather than presenting the dwell times as clean facts - see
`quality` in the returned summary.

Run:  python cases/case5_cafe_dwell_time.py
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLOE

from factory_vision.counting.tracking import resolve_tracker_cfg
from factory_vision.dwell.config import CLIPS, DwellConfig
from factory_vision.paths import OUTPUT_DIR, VIDEO_DIR, WEIGHTS_DIR

warnings.filterwarnings("ignore")

PALETTE = sv.ColorPalette.from_hex(
    ["#4CC9F0", "#4361EE", "#7209B7", "#F72585", "#FF9E00", "#38B000",
     "#00C2A8", "#FFD60A", "#E5383B", "#9D4EDD"]
)

INK = (238, 238, 238)
MUTED = (165, 165, 165)
ACCENT = (120, 240, 170)
WARN = (90, 190, 255)
RULE = (78, 78, 78)


def _text(img, s, org, scale, colour, weight=1):
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, colour, weight, cv2.LINE_AA)


def _mmss(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def filter_detections(det: sv.Detections, cfg: DwellConfig, w: int, h: int) -> sv.Detections:
    """Drop boxes that cannot be a person at this camera height."""
    if not len(det):
        return det
    area = (det.xyxy[:, 2] - det.xyxy[:, 0]) * (det.xyxy[:, 3] - det.xyxy[:, 1])
    frac = area / float(w * h)
    return det[(frac <= cfg.max_box_area_frac) & (frac >= cfg.min_box_area_frac)]


def draw_panel(vis, occupancy, visitors, idx, total, fps, dwell, locked, w, h):
    """Live readout: occupancy now, visitors so far, and the longest dwellers."""
    scale = w / 1920.0
    pw, ph = int(430 * scale), int(330 * scale)
    x0, y0 = int(28 * scale), int(28 * scale)
    panel = vis[y0:y0 + ph, x0:x0 + pw].copy()
    vis[y0:y0 + ph, x0:x0 + pw] = cv2.addWeighted(
        panel, 0.22, np.full_like(panel, (18, 18, 18)), 0.78, 0)
    cv2.rectangle(vis, (x0, y0), (x0 + 4, y0 + ph), ACCENT, -1)

    s = scale
    _text(vis, "Cafe occupancy & dwell time", (x0 + int(20 * s), y0 + int(34 * s)), 0.66 * s, INK, 2)
    _text(vis, f"t = {idx / fps:6.1f}s   frame {idx}/{total}",
          (x0 + int(20 * s), y0 + int(60 * s)), 0.46 * s, MUTED)
    cv2.line(vis, (x0 + int(20 * s), y0 + int(74 * s)),
             (x0 + pw - int(20 * s), y0 + int(74 * s)), RULE, 1)

    _text(vis, f"{occupancy}", (x0 + int(20 * s), y0 + int(132 * s)), 1.7 * s, ACCENT, 3)
    _text(vis, "IN FRAME NOW", (x0 + int(22 * s), y0 + int(154 * s)), 0.40 * s, MUTED)
    _text(vis, f"{visitors}", (x0 + int(230 * s), y0 + int(132 * s)), 1.7 * s, INK, 3)
    _text(vis, "VISITORS SO FAR", (x0 + int(232 * s), y0 + int(154 * s)), 0.40 * s, MUTED)
    cv2.line(vis, (x0 + int(20 * s), y0 + int(170 * s)),
             (x0 + pw - int(20 * s), y0 + int(170 * s)), RULE, 1)

    _text(vis, "LONGEST IN VIEW", (x0 + int(20 * s), y0 + int(194 * s)), 0.40 * s, MUTED)
    live = sorted(((v, k) for k, v in dwell.items() if k in locked), reverse=True)[:4]
    for row, (frames, tid) in enumerate(live):
        y = y0 + int((222 + row * 26) * s)
        colour = PALETTE.by_idx(int(tid)).as_bgr()
        cv2.rectangle(vis, (x0 + int(20 * s), y - int(11 * s)),
                      (x0 + int(32 * s), y + int(1 * s)), colour, -1)
        _text(vis, f"#{tid}", (x0 + int(42 * s), y), 0.46 * s, INK)
        _text(vis, _mmss(frames / fps), (x0 + int(120 * s), y), 0.46 * s, INK)
        bar = int(min(frames / max(total, 1), 1.0) * 220 * s)
        cv2.rectangle(vis, (x0 + int(190 * s), y - int(9 * s)),
                      (x0 + int(190 * s) + bar, y - int(1 * s)), colour, -1)
    return vis


def process(cfg: DwellConfig, args) -> dict:
    src = VIDEO_DIR / cfg.filename
    if not src.exists():
        raise SystemExit(f"missing {src} - build it first (see docs/dwell-time.md)")
    info = sv.VideoInfo.from_video_path(str(src))
    w, h, fps = info.width, info.height, info.fps
    scale = w / 1920.0

    tracker_cfg = resolve_tracker_cfg(args.tracker, cfg.tracker_overrides, "dw")
    model = YOLOE(str(WEIGHTS_DIR / args.weights))
    model.set_classes(cfg.prompts, model.get_text_pe(cfg.prompts))

    # Colour by TRACK, not by class. Everything here is one class ("person"), so
    # the default class lookup paints every box the same colour and the identity
    # the whole measurement rests on becomes invisible in the output.
    box_ann = sv.RoundBoxAnnotator(color=PALETTE, thickness=max(2, int(3 * scale)),
                                   color_lookup=sv.ColorLookup.TRACK)
    trace_ann = sv.TraceAnnotator(color=PALETTE, thickness=max(2, int(2 * scale)),
                                  trace_length=15, position=sv.Position.BOTTOM_CENTER,
                                  color_lookup=sv.ColorLookup.TRACK)

    dwell: dict[int, int] = defaultdict(int)      # frames each id was actually seen
    first_seen: dict[int, int] = {}
    last_seen: dict[int, int] = {}
    locked: set[int] = set()
    occupancy_series: list[int] = []
    times: list[float] = []

    out_path = OUTPUT_DIR / cfg.filename.replace(".mp4", "__dwell.mp4")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    print(f"\n>>> {cfg.filename}  {w}x{h} @ {fps:.3f}fps  {info.total_frames} frames "
          f"({info.total_frames / fps:.1f}s)")
    print(f"    prompts={cfg.prompts} conf={cfg.conf} tracker={args.tracker} "
          f"min_track_age={cfg.min_track_age}")

    with sv.VideoSink(str(out_path), info, codec="mp4v") as sink:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok or (args.max_frames and idx >= args.max_frames):
                break
            idx += 1

            t0 = time.time()
            result = model.track(frame, persist=True, tracker=str(tracker_cfg),
                                 conf=cfg.conf, iou=0.5, imgsz=args.imgsz,
                                 agnostic_nms=True, verbose=False)[0]
            times.append((time.time() - t0) * 1000)

            det = sv.Detections.from_ultralytics(result)
            det = filter_detections(det, cfg, w, h)
            if len(det) and det.tracker_id is not None:
                for tid in det.tracker_id:
                    tid = int(tid)
                    dwell[tid] += 1
                    first_seen.setdefault(tid, idx)
                    last_seen[tid] = idx
                    if dwell[tid] >= cfg.min_track_age:
                        locked.add(tid)
                det = det[np.array([int(t) in locked for t in det.tracker_id])]

            occupancy = len(det)
            occupancy_series.append(occupancy)

            vis = frame.copy()
            vis = trace_ann.annotate(vis, det)
            vis = box_ann.annotate(vis, det)
            if len(det) and det.tracker_id is not None:
                for box, tid in zip(det.xyxy, det.tracker_id):
                    tid = int(tid)
                    x1, y1, x2, _ = box.astype(int)
                    tag = f"#{tid}  {dwell[tid] / fps:4.1f}s"
                    (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX,
                                                  0.52 * max(scale, 0.7), 2)
                    colour = PALETTE.by_idx(tid).as_bgr()
                    cv2.rectangle(vis, (x1, y1 - th - int(10 * scale)),
                                  (x1 + tw + int(12 * scale), y1), colour, -1)
                    _text(vis, tag, (x1 + int(6 * scale), y1 - int(5 * scale)),
                          0.52 * max(scale, 0.7), (12, 12, 12), 2)

            vis = draw_panel(vis, occupancy, len(locked), idx, info.total_frames,
                             fps, dwell, locked, w, h)
            sink.write_frame(vis)

    cap.release()

    # A track that is seen far fewer frames than its own first-to-last span was
    # dropped and re-acquired; that is the signature of an identity split, and it
    # is the thing that quietly inflates the visitor count.
    people = []
    for tid in sorted(locked):
        span = last_seen[tid] - first_seen[tid] + 1
        people.append({
            "track_id": tid,
            "first_frame": first_seen[tid],
            "last_frame": last_seen[tid],
            "frames_seen": dwell[tid],
            "dwell_seconds": round(dwell[tid] / fps, 2),
            "span_seconds": round(span / fps, 2),
            "continuity": round(dwell[tid] / span, 3),
        })
    fragmented = [p for p in people if p["continuity"] < 0.8]
    dwells = [p["dwell_seconds"] for p in people]

    summary = {
        "video": cfg.filename,
        "scene": cfg.scene,
        "source": cfg.source,
        "output": out_path.name,
        "resolution": f"{w}x{h}",
        "fps": round(fps, 3),
        "frames": idx,
        "duration_seconds": round(idx / fps, 1),
        "model": args.weights.replace(".pt", ""),
        "prompts": cfg.prompts,
        "conf": cfg.conf,
        "tracker": "TrackTrack (CVPR 2025) + ReID + GMC",
        "visitors_total": len(locked),
        "occupancy_mean": round(float(np.mean(occupancy_series)), 2) if occupancy_series else 0,
        "occupancy_max": int(np.max(occupancy_series)) if occupancy_series else 0,
        "dwell_mean_seconds": round(float(np.mean(dwells)), 2) if dwells else 0,
        "dwell_max_seconds": round(float(np.max(dwells)), 2) if dwells else 0,
        "quality": {
            "tracks_with_gaps": len(fragmented),
            "worst_continuity": round(min((p["continuity"] for p in people), default=1.0), 3),
            "note": ("continuity = frames actually seen / first-to-last span. "
                     "Below 1.0 the track was lost and re-acquired; every such gap "
                     "is a dwell time that may belong to a person already counted."),
        },
        "avg_ms_per_frame": round(float(np.mean(times)), 1) if times else 0,
        "occupancy_series": occupancy_series,
        "people": people,
        "notes": cfg.notes,
    }
    (OUTPUT_DIR / "dwell_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"    DONE {out_path.name}  visitors={len(locked)} "
          f"occupancy mean={summary['occupancy_mean']} max={summary['occupancy_max']} "
          f"dwell mean={summary['dwell_mean_seconds']}s max={summary['dwell_max_seconds']}s "
          f"{np.mean(times):.0f}ms/f")
    return summary


def run_case(filename: str = "cafe_scene5_30s.mp4", **overrides) -> dict:
    from types import SimpleNamespace

    args = SimpleNamespace(weights="yoloe-11l-seg.pt", tracker="tracktrack",
                           imgsz=1280, max_frames=0)
    for k, v in overrides.items():
        setattr(args, k, v)
    try:
        cfg = next(c for c in CLIPS if c.filename == filename)
    except StopIteration:
        raise SystemExit(f"no clip named {filename}")
    return process(cfg, args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="yoloe-11l-seg.pt")
    ap.add_argument("--tracker", default="tracktrack", choices=["tracktrack", "botsort"])
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()
    return process(CLIPS[0], args)


if __name__ == "__main__":
    main()
