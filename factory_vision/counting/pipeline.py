"""The counting pipeline: detect from text, track, count line crossings.

Per frame:
  1. YOLOE (open-vocabulary) detects from *text prompts only* - no training, no
     fine-tuning, no fixed class list. Prompts are embedded once with
     ``get_text_pe`` and installed via ``set_classes``.
  2. Ultralytics runs the detection through a multi-object tracker (TrackTrack,
     CVPR 2025, by default) to get stable per-object IDs.
  3. Results become ``sv.Detections`` and are drawn with supervision: masks,
     boxes, ID labels, motion traces, the counting line, and a HUD.
  4. ``sv.LineZone`` turns crossings into counts, attributed per class.

Run all clips:      python -m factory_vision.counting.pipeline
Run one clip:       python -m factory_vision.counting.pipeline --only 02_tomatoes_conveyor.mp4
Smoke test (fast):  python -m factory_vision.counting.pipeline --max-frames 60 --stride 2
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLOE

from factory_vision.counting.clips import CLIPS, ClipConfig
from factory_vision.counting.geometry import (build_counting_line, draw_roi,
                                              filter_detections)
from factory_vision.counting.overlay import PALETTE, Hud
from factory_vision.counting.tracking import resolve_tracker_cfg
from factory_vision.paths import OUTPUT_DIR, ROOT, VIDEO_DIR, WEIGHTS_DIR

warnings.filterwarnings("ignore")


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

    model = YOLOE(str(WEIGHTS_DIR / args.weights))
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


def merge_summary(summary: dict, path: Path | None = None) -> None:
    """Fold one clip's summary into output/summary.json, keeping the others.

    Each case script runs a single clip, so it must not overwrite the shared
    file with a one-element list - the entry is replaced in place and the
    remaining clips are left as they were. Entries are held in CLIPS order so
    the file reads the same however the cases were run.
    """
    path = path or (OUTPUT_DIR / "summary.json")
    existing: list[dict] = []
    if path.exists():
        try:
            loaded = json.loads(path.read_text())
            if isinstance(loaded, list):
                existing = [e for e in loaded if isinstance(e, dict)]
        except json.JSONDecodeError:
            existing = []  # unreadable file is not worth losing this run over

    merged = [e for e in existing if e.get("video") != summary["video"]] + [summary]
    order = {c.filename: i for i, c in enumerate(CLIPS)}
    merged.sort(key=lambda e: order.get(e.get("video"), len(order)))
    path.write_text(json.dumps(merged, indent=2))


def run_case(filename: str, **overrides) -> dict:
    """Run one clip end to end and return its summary.

    The per-case scripts in `cases/` call this. They stay thin on purpose: the
    three counting cases differ only in their ClipConfig, so duplicating the
    pipeline into each script would mean three copies of the same tracker,
    counting and rendering code drifting apart on the next fix.
    """
    from types import SimpleNamespace

    args = SimpleNamespace(weights="yoloe-11l-seg.pt", tracker="tracktrack",
                           imgsz=1280, max_frames=0, stride=1)
    for key, value in overrides.items():
        setattr(args, key, value)
    try:
        cfg = next(c for c in CLIPS if c.filename == filename)
    except StopIteration:
        raise SystemExit(f"no clip named {filename}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = process(cfg, args)
    merge_summary(summary, Path(getattr(args, "summary", OUTPUT_DIR / "summary.json")))
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
