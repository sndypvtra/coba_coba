"""Zero-shot conveyor counting: YOLOE text prompts -> TrackTrack -> supervision.

Pipeline per frame:
  1. YOLOE (open-vocabulary) detects from *text prompts only* - no training, no
     fine-tuning, no fixed class list. Prompts are embedded once with
     ``get_text_pe`` and installed via ``set_classes``.
  2. Ultralytics runs the detection through a multi-object tracker (TrackTrack,
     CVPR 2025, by default) to get stable per-object IDs.
  3. Results are converted to ``sv.Detections`` and drawn with supervision:
     masks, boxes, ID labels, motion traces, a counting line, and a HUD.
  4. ``sv.LineZone`` turns line crossings into counts, attributed per class.

Run all clips:      python src/conveyor_count.py
Run one clip:       python src/conveyor_count.py --only 02_tomatoes_conveyor.mp4
Smoke test (fast):  python src/conveyor_count.py --max-frames 60 --stride 2
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLOE

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = ROOT / "videos"
OUTPUT_DIR = ROOT / "output"
TRACKER_DIR = Path(__file__).resolve().parent / "trackers"


@dataclass
class ClipConfig:
    """Per-clip settings. Line geometry is in source-video pixels.

    The counting line is not written down as two endpoints. It is built
    perpendicular to ``motion`` - the belt's measured travel direction - and
    then oriented so that travelling along ``motion`` always counts as IN.
    That is the "look at where the conveyor is heading" rule, applied
    automatically instead of hand-placed per clip.
    """

    filename: str
    prompts: list[str]
    label: str  # single display/count label all prompts collapse into
    conf: float
    line_center: tuple[int, int]
    line_half_len: int
    motion: tuple[float, float]  # median px/frame of tracked objects
    scene: str
    source_url: str
    # an object must be held by the tracker this many frames before it is
    # allowed to count - it has to be locked on well before it reaches the line
    min_track_age: int = 6
    # drop boxes whose area exceeds this fraction of the frame (out-of-focus
    # foreground blobs that drift across the lens rather than ride the belt)
    max_box_area_frac: float = 0.12
    min_box_area_frac: float = 0.00035
    extra_notes: str = ""
    roi_x: tuple[float, float] = (0.0, 1.0)  # keep detections inside this x band
    roi_y: tuple[float, float] = (0.0, 1.0)
    # per-clip tracker gate overrides, measured with src/tune_thresholds.py.
    # Opening these lets a track spawn from the weak, partly-cropped detection
    # an object gives off as it enters frame, instead of waiting until it is
    # fully inside. How much they help is clip-specific - see README.
    tracker_overrides: dict = field(default_factory=dict)


# `motion` is the median per-frame displacement of *tracked objects* (not raw
# optical flow, which on these clips locks onto the rotating rollers rather than
# the produce riding on them). Measured over 45-frame samples; see README.
CLIPS: list[ClipConfig] = [
    ClipConfig(
        filename="01_oranges_production_line.mp4",
        prompts=["orange", "round orange fruit"],
        label="orange",
        # 0.14 -> 0.095: lifts detections 5.9 -> 7.0/frame and pulls median
        # entry lag 0.303 -> 0.276. Going lower (0.063) barely moved lag again
        # but nearly doubled track count, i.e. fragments not earlier pickups.
        conf=0.095,
        min_track_age=4,
        tracker_overrides={
            "track_high_thresh": 0.16,
            "track_low_thresh": 0.04,
            "new_track_thresh": 0.20,
            "min_track_len": 2,
        },
        line_center=(900, 645),
        line_half_len=385,
        motion=(-3.21, 0.94),  # left, drifting slightly down
        scene="Citrus sorting line - oranges on roller conveyor",
        source_url="https://www.pexels.com/video/fruit-on-production-line-10576687/",
        max_box_area_frac=0.05,
    ),
    ClipConfig(
        filename="02_tomatoes_conveyor.mp4",
        prompts=["tomato"],
        label="tomato",
        # the clip that actually responds to tuning: 0.13 -> 0.059 with opened
        # gates cuts median entry lag 0.326 -> 0.203 and more than doubles the
        # share of objects acquired within 15% of the edge (21% -> 50%)
        conf=0.059,
        min_track_age=3,
        tracker_overrides={
            "track_high_thresh": 0.12,
            "track_low_thresh": 0.03,
            "new_track_thresh": 0.15,
            "min_track_len": 2,
        },
        line_center=(1000, 485),
        line_half_len=285,
        # the belt recedes up-and-left, so the line tilts ~9.5 deg off vertical
        # to sit square across the lane rather than parallel to the travel
        motion=(-14.79, -2.47),
        scene="Tomato grading line - roller conveyor close-up",
        source_url="https://www.pexels.com/video/tomatoes-on-a-moving-conveyor-belt-8675102/",
        # the nearest lane sits well outside the depth of field; those tomatoes
        # smear badly and break identity, so counting is restricted to the
        # in-focus lanes via the y-ROI below
        max_box_area_frac=0.06,
        roi_y=(0.0, 0.70),
        extra_notes="counts the in-focus lanes; blurred foreground lane excluded by ROI",
    ),
    ClipConfig(
        filename="03_packages_conveyor.mp4",
        prompts=["cardboard box", "parcel", "plastic bag"],
        label="package",
        # 0.22 -> 0.15 raises detections 8.4 -> 10.0/frame. Entry lag barely
        # responds here (0.559 -> 0.546) because the metric is dominated by the
        # stationary pallet stack, which is present from frame 1 and never
        # "enters" - belt items are already picked up close to the right edge.
        conf=0.15,
        min_track_age=4,
        tracker_overrides={
            "track_high_thresh": 0.16,
            "track_low_thresh": 0.04,
            "new_track_thresh": 0.20,
            "min_track_len": 2,
        },
        line_center=(1180, 640),
        line_half_len=260,
        # tracked median here is polluted by the stationary stack, so this uses
        # the optical-flow direction for the belt itself: straight left
        motion=(-1.52, 0.08),
        scene="Parcel unloading belt - mixed boxes, bags and parcels",
        source_url="https://www.pexels.com/video/unloading-packages-on-a-conveyor-belt-5370836/",
        max_box_area_frac=0.10,
        # the stationary cage of boxes on the left is not belt traffic
        roi_x=(0.34, 1.0),
        extra_notes="static pallet stack on the left is excluded by ROI",
    ),
    # --- manufacturing / factory lines -----------------------------------
    # Prompt choice here is counter-intuitive and worth reading the README on:
    # naming the product ("beer can", "chocolate") returns literally nothing,
    # while describing what it looks like works well. See "Prompting" below.
    ClipConfig(
        filename="04_cans_canning_line.mp4",
        prompts=["shiny metal cylinder"],  # "beer can"/"soda can"/"tin can" -> 0 detections
        label="can",
        conf=0.15,
        line_center=(971, 500),
        line_half_len=250,
        motion=(7.09, 1.13),  # travels right, up the rail
        scene="Brewery canning line - aluminium cans on transfer rail",
        source_url="https://www.pexels.com/video/a-series-of-beer-cans-in-production-line-5532772/",
        # the model sometimes boxes the whole rail of cans as one blob
        max_box_area_frac=0.12,
    ),
    ClipConfig(
        filename="05_dough_bakery_line.mp4",
        prompts=["dough", "bread"],
        label="dough bar",
        conf=0.15,
        line_center=(862, 470),
        line_half_len=450,
        motion=(-1.88, 0.99),
        scene="Industrial bakery - raw dough bars on moulding belt",
        source_url="https://www.pexels.com/video/raw-dough-on-a-conveyor-belt-6560778/",
        # each bar fills ~19% of the frame in this close-up
        max_box_area_frac=0.35,
        min_box_area_frac=0.010,
    ),
    ClipConfig(
        filename="06_chocolate_praline_line.mp4",
        prompts=["brown cube"],  # "chocolate"/"praline"/"chocolate bar" -> 0 detections
        label="praline",
        # 0.18 left whole frames empty in this very shallow depth of field;
        # 0.10 detects 4.2/frame with no empty frames across the clip
        conf=0.10,
        line_center=(630, 740),
        line_half_len=400,
        motion=(4.52, 0.82),
        scene="Confectionery line - enrobed pralines on cooling belt",
        source_url="https://www.pexels.com/video/factory-making-chocolate-7012967/",
        max_box_area_frac=0.28,
        min_box_area_frac=0.008,
        extra_notes="trimmed to the continuous cooling-belt shot (frames 445-595)",
    ),
]


def build_counting_line(cfg: ClipConfig) -> tuple[sv.Point, sv.Point]:
    """Build a line square across the belt, oriented so travel counts as IN.

    Two steps:

    1. *Perpendicular.* The line runs at 90 deg to ``motion``. A line parallel
       to the travel direction would barely be crossed at all, so orientation
       follows the belt rather than the frame axes.
    2. *Inbound.* supervision counts IN when an object ends up on the side where
       ``Vector.cross_product < 0`` (see ``LineZone._compute_anchor_sides``:
       ``triggers = cross_product(...) < 0`` feeds ``tracker_state``, and
       ``tracker_state`` True increments ``in_count``). Probing one step along
       ``motion`` tells us which endpoint order lands on that side, so every
       clip reports crossings as IN and never OUT.
    """
    cx, cy = cfg.line_center
    mx, my = cfg.motion
    norm = float(np.hypot(mx, my)) or 1.0
    # unit normal to the direction of travel
    px, py = -my / norm, mx / norm
    a = (cx + px * cfg.line_half_len, cy + py * cfg.line_half_len)
    b = (cx - px * cfg.line_half_len, cy - py * cfg.line_half_len)

    # probe a point just past the line, in the direction the belt is heading
    probe = (cx + mx / norm * 40.0, cy + my / norm * 40.0)

    def cross(start, end, pt):
        return (end[0] - start[0]) * (pt[1] - start[1]) - (end[1] - start[1]) * (
            pt[0] - start[0]
        )

    if cross(a, b, probe) >= 0:  # would land on the OUT side -> flip
        a, b = b, a
    return sv.Point(int(a[0]), int(a[1])), sv.Point(int(b[0]), int(b[1]))

PALETTE = sv.ColorPalette.from_hex(
    ["#FF3B30", "#FF9500", "#FFD60A", "#34C759", "#00C7BE", "#0A84FF", "#BF5AF2", "#FF2D55"]
)


class Hud:
    """Translucent stats panel drawn on top of the supervision annotations."""

    def __init__(self, cfg: ClipConfig, tracker_name: str, model_name: str, total_frames: int):
        self.cfg = cfg
        self.tracker_name = tracker_name
        self.model_name = model_name
        self.total_frames = total_frames

    def draw(self, frame, frame_idx, counts, per_class, active, unique_ids, ms, locked=0):
        h, w = frame.shape[:2]
        s = w / 1920.0  # scale everything off a 1080p reference
        pad = int(22 * s)
        line_h = int(34 * s)

        rows = [
            (f"{self.cfg.label.upper()} COUNTED (IN): {counts}", 1.05, (90, 255, 140)),
            (f"scene   : {self.cfg.scene}", 0.62, (235, 235, 235)),
            (f"model   : {self.model_name}  (zero-shot, text prompt)", 0.62, (235, 235, 235)),
            (f"prompts : {', '.join(self.cfg.prompts)}", 0.62, (150, 220, 255)),
            (f"tracker : {self.tracker_name}", 0.62, (235, 235, 235)),
            (
                f"per-class: " + ", ".join(f"{k}={v}" for k, v in per_class.items())
                if per_class
                else "per-class: -",
                0.62,
                (235, 235, 235),
            ),
            (
                f"active tracks: {active}   locked [L]: {locked}"
                f"   unique IDs seen: {unique_ids}",
                0.62,
                (235, 235, 235),
            ),
            (
                f"counting rule: locked >= {self.cfg.min_track_age} frames, then crosses line",
                0.62,
                (150, 220, 255),
            ),
            (
                f"frame {frame_idx}/{self.total_frames}   {ms:.0f} ms/frame",
                0.62,
                (185, 185, 185),
            ),
        ]

        box_w = int(900 * s)
        box_h = pad * 2 + line_h * len(rows)
        overlay = frame.copy()
        cv2.rectangle(overlay, (pad, pad), (pad + box_w, pad + box_h), (18, 18, 18), -1)
        cv2.addWeighted(overlay, 0.62, frame, 0.38, 0, frame)
        cv2.rectangle(frame, (pad, pad), (pad + box_w, pad + box_h), (90, 255, 140), max(1, int(2 * s)))

        y = pad + int(line_h * 0.95)
        for text, scale, color in rows:
            cv2.putText(
                frame,
                text,
                (pad + int(18 * s), y),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale * s * 1.25,
                color,
                max(1, int(2.4 * s)) if scale > 1 else max(1, int(1.6 * s)),
                cv2.LINE_AA,
            )
            y += line_h
        return frame


def draw_roi(frame, cfg: ClipConfig, w: int, h: int):
    """Outline the counted region when it is narrower than the full frame."""
    if cfg.roi_x == (0.0, 1.0) and cfg.roi_y == (0.0, 1.0):
        return frame
    x1, x2 = int(cfg.roi_x[0] * w), int(cfg.roi_x[1] * w) - 1
    y1, y2 = int(cfg.roi_y[0] * h), int(cfg.roi_y[1] * h) - 1
    color = (255, 190, 90)
    step, gap = int(28 * w / 1920), int(16 * w / 1920)
    t = max(1, int(2 * w / 1920))
    for x in range(x1, x2, step + gap):  # dashed horizontals
        cv2.line(frame, (x, y1), (min(x + step, x2), y1), color, t, cv2.LINE_AA)
        cv2.line(frame, (x, y2), (min(x + step, x2), y2), color, t, cv2.LINE_AA)
    for y in range(y1, y2, step + gap):  # dashed verticals
        cv2.line(frame, (x1, y), (x1, min(y + step, y2)), color, t, cv2.LINE_AA)
        cv2.line(frame, (x2, y), (x2, min(y + step, y2)), color, t, cv2.LINE_AA)
    cv2.putText(
        frame,
        "COUNTING ROI",
        (x1 + int(12 * w / 1920), y1 + int(34 * w / 1920)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7 * w / 1920,
        color,
        max(1, int(2 * w / 1920)),
        cv2.LINE_AA,
    )
    return frame


def filter_detections(det: sv.Detections, cfg: ClipConfig, w: int, h: int) -> sv.Detections:
    """Drop out-of-ROI and implausibly sized boxes before counting."""
    if len(det) == 0:
        return det
    x1, y1, x2, y2 = det.xyxy.T
    area = ((x2 - x1) * (y2 - y1)) / float(w * h)
    cx, cy = (x1 + x2) / 2.0 / w, (y1 + y2) / 2.0 / h
    keep = (
        (area <= cfg.max_box_area_frac)
        & (area >= cfg.min_box_area_frac)
        & (cx >= cfg.roi_x[0])
        & (cx <= cfg.roi_x[1])
        & (cy >= cfg.roi_y[0])
        & (cy <= cfg.roi_y[1])
    )
    return det[keep]


def resolve_tracker_cfg(name: str, overrides: dict | None = None, tag: str = "") -> Path:
    """Rewrite the tracker YAML with an absolute ReID path and clip overrides.

    Ultralytics resolves a relative ``model:`` against the working directory, so
    the checked-in relative path only works when run from the project root.
    ``overrides`` carries the per-clip gate tuning from ClipConfig.
    """
    import yaml

    src = TRACKER_DIR / f"{name}_zeroshot.yaml"
    cfg = yaml.safe_load(src.read_text())
    reid = cfg.get("model")
    if reid and reid != "auto" and not Path(reid).is_absolute():
        cfg["model"] = str((ROOT / reid).resolve())
    if overrides:
        cfg.update(overrides)
    dst = OUTPUT_DIR / f".{name}{('_' + tag) if tag else ''}_resolved.yaml"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return dst


def process(cfg: ClipConfig, args) -> dict:
    src = VIDEO_DIR / cfg.filename
    info = sv.VideoInfo.from_video_path(str(src))
    w, h = info.width, info.height
    scale = w / 1920.0

    tracker_cfg = resolve_tracker_cfg(args.tracker, cfg.tracker_overrides, cfg.filename[:2])
    tracker_label = {
        "tracktrack": "TrackTrack (CVPR 2025) + ReID + GMC",
        "botsort": "BoT-SORT + ReID + GMC",
    }[args.tracker]

    model = YOLOE(str(ROOT / "weights" / args.weights))
    model.set_classes(cfg.prompts, model.get_text_pe(cfg.prompts))
    model_label = args.weights.replace(".pt", "")

    line_a, line_b = build_counting_line(cfg)
    line = sv.LineZone(
        start=line_a,
        end=line_b,
        triggering_anchors=(sv.Position.CENTER,),
        minimum_crossing_threshold=2,
    )

    mask_ann = sv.MaskAnnotator(color=PALETTE, opacity=0.30)
    box_ann = sv.RoundBoxAnnotator(color=PALETTE, thickness=max(2, int(3 * scale)))
    label_ann = sv.LabelAnnotator(
        color=PALETTE,
        text_scale=0.5 * max(scale, 0.6),
        text_thickness=max(1, int(1.6 * scale)),
        text_position=sv.Position.TOP_LEFT,
    )
    trace_ann = sv.TraceAnnotator(
        color=PALETTE, thickness=max(2, int(3 * scale)), trace_length=40, position=sv.Position.CENTER
    )
    # every clip is oriented so travel across the line is IN, so OUT is always
    # zero and is hidden rather than shown as a permanent "OUT: 0"
    line_ann = sv.LineZoneAnnotator(
        thickness=max(2, int(4 * scale)),
        color=sv.Color.from_hex("#FFD60A"),
        text_scale=0.9 * max(scale, 0.6),
        text_thickness=max(1, int(2 * scale)),
        custom_in_text="IN",
        display_out_count=False,
    )

    hud = Hud(cfg, tracker_label, model_label, info.total_frames)

    out_path = OUTPUT_DIR / f"{Path(cfg.filename).stem}__counted.mp4"
    out_info = sv.VideoInfo(width=w, height=h, fps=info.fps, total_frames=info.total_frames)

    per_class: dict[str, int] = {}
    unique_ids: set[int] = set()
    track_age: dict[int, int] = {}  # frames each ID has been held by the tracker
    times: list[float] = []
    frames_written = 0
    total_dets = 0

    cap = cv2.VideoCapture(str(src))
    print(f"\n>>> {cfg.filename}  {w}x{h} @ {info.fps:.2f}fps  {info.total_frames} frames")
    print(f"    prompts={cfg.prompts} conf={cfg.conf} imgsz={args.imgsz} tracker={args.tracker}")

    with sv.VideoSink(target_path=str(out_path), video_info=out_info, codec="mp4v") as sink:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            idx += 1
            if args.stride > 1 and (idx - 1) % args.stride:
                continue
            if args.max_frames and frames_written >= args.max_frames:
                break

            t0 = time.time()
            result = model.track(
                frame,
                persist=True,
                tracker=str(tracker_cfg),
                conf=cfg.conf,
                iou=0.5,
                imgsz=args.imgsz,
                agnostic_nms=True,  # collapses duplicate boxes across prompt aliases
                verbose=False,
            )[0]
            times.append((time.time() - t0) * 1000)

            det = sv.Detections.from_ultralytics(result)
            det = filter_detections(det, cfg, w, h)
            total_dets += len(det)

            # every prompt alias is the same physical object type -> one label
            if len(det):
                det.data["class_name"] = np.array([cfg.label] * len(det))
                det.class_id = np.zeros(len(det), dtype=int)

            # only tracker-confirmed objects are drawn and counted
            if len(det) and det.tracker_id is not None:
                tracked = det[np.array([t is not None for t in det.tracker_id])]
            else:
                tracked = det[np.zeros(len(det), dtype=bool)]
            if len(tracked):
                unique_ids.update(int(t) for t in tracked.tracker_id)
                for t in tracked.tracker_id:
                    track_age[int(t)] = track_age.get(int(t), 0) + 1

            # Maturity gate: an object is only eligible to be counted once the
            # tracker has held the same ID for min_track_age frames. It must be
            # picked up and locked on well before it reaches the line, so a
            # flickering box that pops into existence on top of the line cannot
            # register a crossing.
            if len(tracked):
                locked_mask = np.array(
                    [track_age[int(t)] >= cfg.min_track_age for t in tracked.tracker_id]
                )
            else:
                locked_mask = np.zeros(0, dtype=bool)
            locked = tracked[locked_mask]

            crossed_in, _ = line.trigger(locked)
            for flag_in, name in zip(crossed_in, locked.data.get("class_name", [])):
                if flag_in:
                    per_class[name] = per_class.get(name, 0) + 1

            annotated = draw_roi(frame.copy(), cfg, w, h)
            if len(tracked):
                if tracked.mask is not None:
                    annotated = mask_ann.annotate(annotated, tracked)
                annotated = trace_ann.annotate(annotated, tracked)
                annotated = box_ann.annotate(annotated, tracked)
                # a locked track carries [L] - it is armed and will count on cross
                labels = [
                    f"#{int(tid)}{'[L]' if lock else ''} {name} {conf:.2f}"
                    for tid, name, conf, lock in zip(
                        tracked.tracker_id,
                        tracked.data["class_name"],
                        tracked.confidence,
                        locked_mask,
                    )
                ]
                annotated = label_ann.annotate(annotated, tracked, labels)

            annotated = line_ann.annotate(annotated, line)
            annotated = hud.draw(
                annotated,
                idx,
                line.in_count,
                per_class,
                len(tracked),
                len(unique_ids),
                float(np.mean(times[-30:])),
                len(locked),
            )
            sink.write_frame(annotated)
            frames_written += 1

            if frames_written % 50 == 0:
                print(
                    f"    frame {idx}/{info.total_frames} IN={line.in_count} "
                    f"active={len(tracked)} locked={len(locked)} ids={len(unique_ids)} "
                    f"{np.mean(times[-50:]):.0f}ms/f",
                    flush=True,
                )

    cap.release()
    # The line is oriented to the belt, so forward travel is IN and that alone
    # is the count. OUT therefore holds *reverse* crossings, which on a one-way
    # conveyor should be rare - a handful means box jitter or an ID switch
    # briefly threw a centroid back over the line. It is reported as a quality
    # signal and is deliberately excluded from the total.
    total = line.in_count
    summary = {
        "video": cfg.filename,
        "scene": cfg.scene,
        "source_url": cfg.source_url,
        "output": out_path.name,
        "resolution": f"{w}x{h}",
        "fps": round(float(info.fps), 2),
        "frames_written": frames_written,
        "model": model_label,
        "prompts": cfg.prompts,
        "conf": cfg.conf,
        "imgsz": args.imgsz,
        "tracker": tracker_label,
        "count_total": int(total),
        "count_in": int(line.in_count),
        "count_reverse_crossings": int(line.out_count),  # excluded from total
        "line": [[line_a.x, line_a.y], [line_b.x, line_b.y]],
        "motion_px_per_frame": list(cfg.motion),
        "min_track_age": cfg.min_track_age,
        "per_class": per_class,
        "unique_track_ids": len(unique_ids),
        "avg_detections_per_frame": round(total_dets / max(frames_written, 1), 2),
        "avg_ms_per_frame": round(float(np.mean(times)), 1),
        "notes": cfg.extra_notes,
    }
    print(
        f"    DONE {out_path.name}  IN={line.in_count} (reverse={line.out_count}) "
        f"ids={len(unique_ids)} {np.mean(times):.0f}ms/f  "
        f"{out_path.stat().st_size/1e6:.1f}MB"
    )
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="yoloe-11l-seg.pt")
    ap.add_argument("--tracker", default="tracktrack", choices=["tracktrack", "botsort"])
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--only", default=None, help="process a single filename")
    ap.add_argument("--max-frames", type=int, default=0, help="0 = whole clip")
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--summary", default=str(OUTPUT_DIR / "summary.json"))
    args = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clips = [c for c in CLIPS if args.only in (None, c.filename)]
    if not clips:
        raise SystemExit(f"no clip matches --only {args.only}")

    summaries = [process(cfg, args) for cfg in clips]

    Path(args.summary).write_text(json.dumps(summaries, indent=2))
    print("\n==================== SUMMARY ====================")
    for s in summaries:
        print(
            f"{s['output']:46s} count={s['count_total']:4d} "
            f"ids={s['unique_track_ids']:4d} {s['avg_ms_per_frame']:.0f}ms/f"
        )
    print(f"\nwrote {args.summary}")


if __name__ == "__main__":
    main()
