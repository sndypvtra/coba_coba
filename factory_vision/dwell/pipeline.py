"""Person detection, per-frame occupancy, and per-person dwell time.

Three numbers come out of this:

  occupancy   how many customers are in the frame right now
  visitors    how many distinct customers have been seen so far
  dwell       for each customer, how long they have been in view

The first is a detection problem and is the easy one. The other two are tracking
problems, and they are only as good as the identity assignment: if a seated
customer is occluded by someone walking past and comes back with a new track ID,
one 8-minute visit is reported as two 4-minute visits and the visitor count goes
up by one. So this module reports the fragmentation signals alongside the answer
rather than presenting the dwell times as clean facts - see `quality` in the
returned summary.

Two things are deliberately not counted, because neither is a customer visit:

  reflections   a wall mirror shows people who are already counted in the room
  staff         anyone working behind the counter

Both are handled by frame regions rather than by appearance. Nothing in a
person's pixels says "reflection" or "employee"; what says it is where they are
in a fixed camera's frame, and that is knowable once per installation.

Run:  python cases/case5_cafe_dwell_time.py
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from collections import defaultdict

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLOE

from factory_vision.counting.tracking import resolve_tracker_cfg
from factory_vision.dwell.config import CLIPS, DwellConfig, ExclusionZone
from factory_vision.paths import OUTPUT_DIR, VIDEO_DIR, WEIGHTS_DIR

warnings.filterwarnings("ignore")

PALETTE = sv.ColorPalette.from_hex(
    ["#4CC9F0", "#4361EE", "#7209B7", "#F72585", "#FF9E00", "#38B000",
     "#00C2A8", "#FFD60A", "#E5383B", "#9D4EDD", "#06D6A0", "#EF476F"]
)

INK = (240, 240, 240)
MUTED = (158, 158, 158)
DIM = (110, 110, 110)
ACCENT = (120, 240, 170)
RULE = (72, 72, 72)
ZONE = (96, 96, 250)


def _text(img, s, org, scale, colour, weight=1):
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, colour, weight, cv2.LINE_AA)


def _clock(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


# ---------------------------------------------------------------- detections


def suppress_contained(det: sv.Detections, threshold: float) -> sv.Detections:
    """Drop a box that is largely swallowed by a more confident one.

    NMS scores overlap as intersection over *union*, which is small when one box
    is much bigger than the other - exactly the head-and-shoulders vs whole-body
    pair this camera produces on seated customers. Scoring by intersection over
    the *smaller* box instead measures containment, which is what that pair
    actually is.

    Measured over the first 20 frames of the cafe clip: 14 pairs exceed 0.75
    containment and every one of them sits below IoU 0.5, so NMS keeps them all.
    Tightening NMS instead is not an option - those duplicates span IoU
    0.076-0.485 while genuinely adjacent customers span 0.000-0.425, and a
    threshold low enough to catch the duplicates would wrongly merge 101 pairs of
    different people. The two populations are separable by containment and not by
    IoU, which is the whole reason this function exists.
    """
    if len(det) < 2:
        return det
    order = np.argsort(-det.confidence)
    boxes = det.xyxy[order]
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep = np.ones(len(boxes), dtype=bool)
    for i in range(len(boxes)):
        if not keep[i]:
            continue
        xx1 = np.maximum(boxes[i, 0], boxes[i + 1:, 0])
        yy1 = np.maximum(boxes[i, 1], boxes[i + 1:, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[i + 1:, 2])
        yy2 = np.minimum(boxes[i, 3], boxes[i + 1:, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        smaller = np.minimum(areas[i], areas[i + 1:])
        contained = inter / np.maximum(smaller, 1.0)
        keep[i + 1:][contained > threshold] = False
    return det[order[keep]]


class _DetView:
    """Minimal Results-like view the ultralytics trackers accept.

    `model.track()` runs detection and tracking in one call, which leaves no
    seam to filter between them - and filtering *after* the tracker is useless,
    because by then a duplicate box has already been promoted to its own track
    ID and counted as a visitor. Detection and tracking are therefore driven
    separately here so the filters run in the only place they can work.
    """

    def __init__(self, xyxy: np.ndarray, conf: np.ndarray, cls: np.ndarray):
        self.conf = conf
        self.cls = cls
        cx = (xyxy[:, 0] + xyxy[:, 2]) / 2.0
        cy = (xyxy[:, 1] + xyxy[:, 3]) / 2.0
        self.xywh = np.stack([cx, cy, xyxy[:, 2] - xyxy[:, 0],
                              xyxy[:, 3] - xyxy[:, 1]], axis=1)

    def __len__(self):
        return len(self.conf)


def build_tracker(tracker_cfg_path, fps: float):
    """Instantiate the tracker named in the resolved YAML."""
    import yaml
    from types import SimpleNamespace

    import ultralytics.trackers as trackers

    cfg = yaml.safe_load(open(tracker_cfg_path))
    cfg.setdefault("frame_rate", int(round(fps)))
    name = str(cfg.get("tracker_type", "tracktrack")).lower()
    cls = {"tracktrack": trackers.TRACKTRACK, "botsort": trackers.BOTSORT,
           "bytetrack": trackers.BYTETracker}[name]
    return cls(SimpleNamespace(**cfg)), name


def zone_masks(zones: list[ExclusionZone], w: int, h: int) -> list[np.ndarray]:
    out = []
    for z in zones:
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [np.array(z.polygon, np.int32)], 1)
        out.append(m)
    return out


def apply_exclusions(det: sv.Detections, zones, masks, w: int, h: int):
    """Remove detections that lie mostly inside an exclusion zone."""
    if not len(det) or not zones:
        return det, {}
    dropped: dict[str, int] = {}
    keep = np.ones(len(det), dtype=bool)
    for zi, (z, m) in enumerate(zip(zones, masks)):
        for i, box in enumerate(det.xyxy):
            if not keep[i]:
                continue
            x1, y1, x2, y2 = [int(v) for v in box]
            x1, y1 = max(x1, 0), max(y1, 0)
            x2, y2 = min(x2, w), min(y2, h)
            if x2 <= x1 or y2 <= y1:
                continue
            inside = float(m[y1:y2, x1:x2].sum()) / float((x2 - x1) * (y2 - y1))
            if inside >= z.min_overlap:
                keep[i] = False
                dropped[z.name] = dropped.get(z.name, 0) + 1
    return det[keep], dropped


# -------------------------------------------------------------------- render


def draw_zones(vis, zones, scale):
    """Mark the excluded regions, so the viewer can see what was left out.

    Kept deliberately quiet: a dim wash and a thin outline. These regions are
    context, not the subject, and at full strength they pulled the eye away from
    the tracked customers - which are what the frame is about.
    """
    for z in zones:
        pts = np.array(z.polygon, np.int32)
        overlay = vis.copy()
        cv2.fillPoly(overlay, [pts], (26, 26, 26))
        cv2.addWeighted(overlay, 0.55, vis, 0.45, 0, vis)
        cv2.polylines(vis, [pts], True, ZONE, max(1, int(1.4 * scale)))
        x = int(pts[:, 0].min()) + int(14 * scale)
        y = int(pts[:, 1].max()) - int(12 * scale)
        _text(vis, f"EXCLUDED - {z.name.upper()}", (x, y), 0.46 * scale, ZONE, 1)
    return vis


PANEL_W = 460


def compose(vis, occupancy, visitors, idx, total, fps, dwell, live_ids,
            excluded_now, series, zones, tracker_name):
    """Video on the right, readout on its own strip on the left.

    The panel used to sit on top of the frame, where it covered the mirror - one
    of the two regions the viewer most needs to see, since the whole point is
    that nothing is being counted there. Giving the readout its own strip means
    no part of the scene is ever hidden by the thing describing it.
    """
    h, w = vis.shape[:2]
    canvas = np.full((h, w + PANEL_W, 3), 16, np.uint8)
    canvas[:, PANEL_W:] = vis
    cv2.line(canvas, (PANEL_W - 1, 0), (PANEL_W - 1, h), (44, 44, 44), 1)

    m = 30                      # left margin
    _text(canvas, "CUSTOMER OCCUPANCY", (m, 52), 0.72, INK, 2)
    _text(canvas, "& DWELL TIME", (m, 82), 0.72, INK, 2)
    _text(canvas, "Cafe interior - fixed camera", (m, 108), 0.44, MUTED)
    cv2.line(canvas, (m, 128), (PANEL_W - m, 128), RULE, 1)

    _text(canvas, f"ELAPSED  {_clock(idx / fps)}", (m, 158), 0.48, MUTED)
    _text(canvas, f"FRAME  {idx}/{total}", (m, 182), 0.48, MUTED)

    _text(canvas, f"{occupancy}", (m, 268), 2.6, ACCENT, 4)
    _text(canvas, "IN ROOM NOW", (m + 2, 296), 0.44, MUTED)
    _text(canvas, f"{visitors}", (m + 240, 268), 2.6, INK, 4)
    _text(canvas, "VISITORS TOTAL", (m + 242, 296), 0.44, MUTED)

    gx, gy, gw, gh = m, 330, PANEL_W - 2 * m, 86
    cv2.rectangle(canvas, (gx, gy), (gx + gw, gy + gh), (30, 30, 30), -1)
    _text(canvas, "OCCUPANCY OVER TIME", (gx, gy - 10), 0.40, DIM)
    if len(series) > 1:
        top = max(max(series), 1)
        pts = [(gx + int(i / max(total - 1, 1) * gw),
                gy + gh - int(v / top * (gh - 6)) - 3) for i, v in enumerate(series)]
        cv2.polylines(canvas, [np.array(pts, np.int32)], False, ACCENT, 2)
        cv2.circle(canvas, pts[-1], 4, ACCENT, -1)
    _text(canvas, f"max {max(series) if series else 0}", (gx + gw - 58, gy + 16), 0.40, DIM)

    _text(canvas, "LONGEST IN VIEW", (m, 456), 0.44, MUTED)
    cv2.line(canvas, (m, 468), (PANEL_W - m, 468), RULE, 1)
    live = sorted(((dwell[i], i) for i in live_ids), reverse=True)[:9]
    for row, (frames, tid) in enumerate(live):
        y = 500 + row * 34
        colour = PALETTE.by_idx(int(tid)).as_bgr()
        cv2.rectangle(canvas, (m, y - 13), (m + 13, y), colour, -1)
        _text(canvas, f"#{tid}", (m + 26, y), 0.50, INK)
        _text(canvas, f"{frames / fps:5.1f}s", (m + 92, y), 0.50, INK)
        bar = int(min(frames / max(total, 1), 1.0) * (PANEL_W - 2 * m - 176))
        cv2.rectangle(canvas, (m + 176, y - 11), (m + 176 + bar, y - 3), colour, -1)

    y = h - 168
    cv2.line(canvas, (m, y), (PANEL_W - m, y), RULE, 1)
    _text(canvas, "NOT COUNTED", (m, y + 26), 0.44, MUTED)
    for i, z in enumerate(zones):
        yy = y + 52 + i * 26
        cv2.rectangle(canvas, (m, yy - 11), (m + 13, yy), ZONE, -1)
        n = excluded_now.get(z.name, 0)
        _text(canvas, f"{z.name}", (m + 26, yy), 0.44, INK)
        _text(canvas, f"{n} this frame", (m + 210, yy), 0.44, DIM)
    _text(canvas, f"YOLOE-11L-seg zero-shot  |  {tracker_name}",
          (m, h - 44), 0.40, DIM)
    _text(canvas, "occupancy measured; visitor total depends on tracking",
          (m, h - 22), 0.38, DIM)
    return canvas


# ------------------------------------------------------------------ pipeline


def process(cfg: DwellConfig, args) -> dict:
    src = VIDEO_DIR / cfg.filename
    if not src.exists():
        raise SystemExit(f"missing {src} - see docs/dwell-time.md for how it is built")
    info = sv.VideoInfo.from_video_path(str(src))
    w, h, fps = info.width, info.height, info.fps
    scale = w / 1920.0

    tracker_cfg = resolve_tracker_cfg(args.tracker, cfg.tracker_overrides, "dw")
    model = YOLOE(str(WEIGHTS_DIR / args.weights))
    model.set_classes(cfg.prompts, model.get_text_pe(cfg.prompts))
    tracker, tracker_name = build_tracker(tracker_cfg, fps)
    masks = zone_masks(cfg.exclusion_zones, w, h)

    # Colour by TRACK, not by class. Everything here is one class ("person"), so
    # the default class lookup paints every box the same colour and the identity
    # the whole measurement rests on becomes invisible in the output.
    box_ann = sv.RoundBoxAnnotator(color=PALETTE, thickness=max(2, int(3 * scale)),
                                   color_lookup=sv.ColorLookup.TRACK)
    trace_ann = sv.TraceAnnotator(color=PALETTE, thickness=max(2, int(2 * scale)),
                                  trace_length=15, position=sv.Position.BOTTOM_CENTER,
                                  color_lookup=sv.ColorLookup.TRACK)

    dwell: dict[int, int] = defaultdict(int)
    first_seen: dict[int, int] = {}
    last_seen: dict[int, int] = {}
    locked: set[int] = set()
    series: list[int] = []
    excluded_total: dict[str, int] = {}
    raw_dets = 0
    dup_dropped = 0
    times: list[float] = []

    out_path = OUTPUT_DIR / cfg.filename.replace(".mp4", "__dwell.mp4")
    out_info = sv.VideoInfo(width=w + PANEL_W, height=h, fps=info.fps,
                            total_frames=info.total_frames)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    print(f"\n>>> {cfg.filename}  {w}x{h} @ {fps:.3f}fps  {info.total_frames} frames "
          f"({info.total_frames / fps:.1f}s)")
    print(f"    prompts={cfg.prompts} conf={cfg.conf} tracker={args.tracker} "
          f"min_track_age={cfg.min_track_age} dedup={cfg.dedup_containment}")
    for z in cfg.exclusion_zones:
        print(f"    zone '{z.name}': {z.reason} (>= {z.min_overlap:.0%} of box)")

    with sv.VideoSink(str(out_path), out_info, codec="mp4v") as sink:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok or (args.max_frames and idx >= args.max_frames):
                break
            idx += 1

            t0 = time.time()
            result = model.predict(frame, conf=cfg.conf, iou=0.5, imgsz=args.imgsz,
                                   agnostic_nms=True, verbose=False)[0]

            det = sv.Detections.from_ultralytics(result)
            if len(det):
                area = ((det.xyxy[:, 2] - det.xyxy[:, 0])
                        * (det.xyxy[:, 3] - det.xyxy[:, 1])) / float(w * h)
                det = det[(area <= cfg.max_box_area_frac) & (area >= cfg.min_box_area_frac)]
            raw_dets += len(det)

            # Both filters run before the tracker sees anything. A duplicate box
            # that reaches the tracker becomes its own ID and its own "visitor";
            # a mirror reflection that reaches it consumes an ID too.
            before = len(det)
            det = suppress_contained(det, cfg.dedup_containment)
            dup_dropped += before - len(det)

            det, dropped_now = apply_exclusions(det, cfg.exclusion_zones, masks, w, h)
            for k, v in dropped_now.items():
                excluded_total[k] = excluded_total.get(k, 0) + v

            tracks = tracker.update(
                _DetView(det.xyxy.astype(np.float32),
                         det.confidence.astype(np.float32),
                         det.class_id.astype(np.float32)), frame)
            times.append((time.time() - t0) * 1000)

            if len(tracks):
                tracks = np.asarray(tracks)
                det = sv.Detections(
                    xyxy=tracks[:, :4].astype(np.float32),
                    confidence=tracks[:, 5].astype(np.float32),
                    class_id=tracks[:, 6].astype(int),
                    tracker_id=tracks[:, 4].astype(int),
                )
            else:
                det = sv.Detections.empty()

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
            series.append(occupancy)

            vis = draw_zones(frame.copy(), cfg.exclusion_zones, max(scale, 0.8))
            vis = trace_ann.annotate(vis, det)
            vis = box_ann.annotate(vis, det)
            if len(det) and det.tracker_id is not None:
                for box, tid in zip(det.xyxy, det.tracker_id):
                    tid = int(tid)
                    x1, y1 = int(box[0]), int(box[1])
                    tag = f"#{tid}   {dwell[tid] / fps:.1f}s"
                    fs = 0.5 * max(scale, 0.75)
                    (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, fs, 2)
                    pad = int(7 * scale)
                    y_tag = max(y1, th + 2 * pad)
                    colour = PALETTE.by_idx(tid).as_bgr()
                    cv2.rectangle(vis, (x1, y_tag - th - 2 * pad),
                                  (x1 + tw + 2 * pad, y_tag), colour, -1)
                    _text(vis, tag, (x1 + pad, y_tag - pad), fs, (14, 14, 14), 2)

            live_ids = (set(int(t) for t in det.tracker_id)
                        if (len(det) and det.tracker_id is not None) else set())
            sink.write_frame(compose(vis, occupancy, len(locked), idx,
                                     info.total_frames, fps, dwell, live_ids,
                                     dropped_now, series, cfg.exclusion_zones,
                                     tracker_name))

    cap.release()

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
        "occupancy_mean": round(float(np.mean(series)), 2) if series else 0,
        "occupancy_max": int(np.max(series)) if series else 0,
        "dwell_mean_seconds": round(float(np.mean(dwells)), 2) if dwells else 0,
        "dwell_max_seconds": round(float(np.max(dwells)), 2) if dwells else 0,
        "filtering": {
            "detections_before_filters": raw_dets,
            "duplicate_boxes_removed": dup_dropped,
            "excluded_by_zone": excluded_total,
            "zones": [{"name": z.name, "reason": z.reason,
                       "min_overlap": z.min_overlap} for z in cfg.exclusion_zones],
        },
        "quality": {
            "tracks_with_gaps": len(fragmented),
            "worst_continuity": round(min((p["continuity"] for p in people), default=1.0), 3),
            "note": ("continuity = frames actually seen / first-to-last span. "
                     "Below 1.0 the track was lost and re-acquired; every such gap "
                     "is a dwell time that may belong to a person already counted."),
        },
        "avg_ms_per_frame": round(float(np.mean(times)), 1) if times else 0,
        "occupancy_series": series,
        "people": people,
        "notes": cfg.notes,
    }
    (OUTPUT_DIR / "dwell_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"    filtered: {dup_dropped} duplicate boxes, "
          f"{sum(excluded_total.values())} zone hits {excluded_total}")
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
