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
from factory_vision.counting.sizing import depth_corridor, measure
from factory_vision.counting.tracking import resolve_tracker_cfg
from factory_vision.paths import OUTPUT_DIR, ROOT, VIDEO_DIR, WEIGHTS_DIR

warnings.filterwarnings("ignore")


def _consensus(sizes):
    """One parcel's size, as the median of every frame that measured it.

    A single frame reads short whenever the parcel behind it clips the mask or
    the one in front hides its base. Those failures are one-sided and sporadic,
    so a median over the pass is both steadier and closer to the truth than the
    best single frame - and it is available for free, because the parcel is
    measured on every depth frame it survives.
    """
    if not sizes:
        return None
    from factory_vision.counting.sizing import ParcelSize

    med = lambda key: float(np.median([getattr(s, key) for s in sizes]))
    length, width, height = med("length_m"), med("width_m"), med("height_m")
    return ParcelSize(
        distance_m=sizes[-1].distance_m,          # distance is live, not a median
        length_m=length, width_m=width, height_m=height,
        volume_l=length * width * height * 1000.0,
        points=int(np.median([s.points for s in sizes])),
        mask_kept=med("mask_kept"), base_offset_m=med("base_offset_m"),
        trusted=True, notes=[f"median of {len(sizes)} frames"],
    )


def _prepare_depth(cfg: ClipConfig, src, w: int, h: int):
    """Solve the camera and fit the belt once, before the clip starts.

    Both are properties of the installation, not of any frame: the camera does
    not move and neither does the belt. Doing this per frame would cost the run
    a second model pass and would let the belt plane wander with the noise in
    each depth map, which is exactly the thing every height is measured against.
    """
    from factory_vision.counting.depth import MetricDepth
    from factory_vision.counting.sizing import bare_belt_depth, fit_belt

    cap = cv2.VideoCapture(str(src))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 500
    probes = []
    for idx in np.linspace(0, max(total - 2, 0), 6).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            probes.append(frame)
    cap.release()

    model = MetricDepth(process_res=cfg.depth_process_res)
    K_proc = model.solve_intrinsics(probes[:4])
    K = K_proc.scaled_to(w, h)
    print(f"    depth   : DA3 {cfg.depth_process_res}px  fx={K.fx:.0f} fy={K.fy:.0f} "
          f"hFOV={K.hfov_deg:.1f}deg  spread={model.intrinsics_spread*100:.1f}%  "
          f"square-pixel error={K_proc.square_pixel_error*100:.1f}%")

    maps = [model.depth(f) for f in probes]
    belt = fit_belt(bare_belt_depth(maps), K, cfg.belt_patches, cfg.motion)
    print(f"    belt    : plane rms {belt.rms_m*1000:.1f} mm from {belt.samples} px, "
          f"camera {belt.camera_height_m*1000:.0f} mm above it")
    model.frame_K = K
    # Seed the rolling map with the clip's own first frame. The loop refreshes it
    # on frame 1 anyway, so this only matters if depth_every is ever changed such
    # that it does not - and then the right stale map to hold is the near one.
    return model, belt, maps[0]


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

    depth_model = belt = None
    last_depth = None
    depth_ms: list[float] = []
    corridor_dropped = 0
    # every measurement each track ever produced, so the reported size is a
    # median over a parcel's whole pass rather than one lucky frame
    track_sizes: dict[int, list] = {}
    if cfg.measure_size:
        depth_model, belt, last_depth = _prepare_depth(cfg, src, w, h)

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

            # Depth runs on every Nth frame; the corridor test uses the most
            # recent map. At 4.7 px/frame a parcel drifts 23 px between runs,
            # which a median over the whole mask absorbs - and the thing the
            # corridor has to separate, the static stack at the back, does not
            # move at all.
            if depth_model is not None and (idx - 1) % cfg.depth_every == 0:
                td = time.time()
                last_depth = depth_model.depth(frame)
                depth_ms.append((time.time() - td) * 1000)

            if cfg.depth_corridor and last_depth is not None and len(det):
                near, far = cfg.depth_corridor
                masks = list(det.mask) if det.mask is not None else None
                inside = depth_corridor(last_depth, det.xyxy, near, far, masks)
                corridor_dropped += int((~inside).sum())
                det = det[inside]
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

            # Measure on the frames that have a fresh depth map. A parcel is
            # measured many times over its pass and reported as the median,
            # because a single frame can catch it half-occluded by the one in
            # front and read short.
            if (belt is not None and last_depth is not None and len(tracked)
                    and (idx - 1) % cfg.depth_every == 0 and tracked.mask is not None):
                for tid, mk in zip(tracked.tracker_id, tracked.mask):
                    size = measure(mk.astype(np.uint8), last_depth,
                                   depth_model.frame_K, belt, cfg.size_scale)
                    if size is not None and size.trusted:
                        track_sizes.setdefault(int(tid), []).append(size)

            annotated = draw_roi(frame.copy(), cfg, w, h)
            if len(tracked):
                if tracked.mask is not None:
                    annotated = mask_ann.annotate(annotated, tracked)
                annotated = trace_ann.annotate(annotated, tracked)
                annotated = box_ann.annotate(annotated, tracked)
                # a locked track carries [L] - it is armed and will count on cross
                labels = []
                for tid, name, conf, lock in zip(
                    tracked.tracker_id, tracked.data["class_name"],
                    tracked.confidence, locked_mask,
                ):
                    head = f"#{int(tid)}{'[L]' if lock else ''} {name} {conf:.2f}"
                    size = _consensus(track_sizes.get(int(tid)))
                    if size is not None:
                        head += (f"  {size.distance_m:.2f}m  "
                                 f"{size.length_m*100:.0f}x{size.width_m*100:.0f}"
                                 f"x{size.height_m*100:.0f}cm [{size.class_name}]")
                    labels.append(head)
                annotated = label_ann.annotate(annotated, tracked, labels)

            annotated = line_ann.annotate(annotated, line)
            hud_sizing = None
            if belt is not None and len(tracked):
                live = [_consensus(track_sizes.get(int(t))) for t in tracked.tracker_id]
                live = [s for s in live if s is not None]
                if live:
                    hud_sizing = {
                        "model": f"Depth Anything 3 metric @ {cfg.depth_process_res}px, "
                                 f"every {cfg.depth_every}th frame",
                        "measured": len(live),
                        "volume_l": sum(s.volume_l for s in live),
                        "nearest_m": min(s.distance_m for s in live),
                    }
            annotated = hud.draw(
                annotated,
                idx,
                line.in_count,
                per_class,
                len(tracked),
                len(unique_ids),
                float(np.mean(times[-30:])),
                len(locked),
                hud_sizing,
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
    if cfg.measure_size:
        summary["dimensioning"] = _dimension_summary(
            cfg, depth_model, belt, track_sizes, track_age, corridor_dropped, depth_ms)
    print(
        f"    DONE {out_path.name}  IN={line.in_count} (reverse={line.out_count}) "
        f"ids={len(unique_ids)} {np.mean(times):.0f}ms/f  "
        f"{out_path.stat().st_size/1e6:.1f}MB"
    )
    return summary


def _dimension_summary(cfg, depth_model, belt, track_sizes, track_age,
                       corridor_dropped, depth_ms) -> dict:
    """The measurement half of the report: distance, size and how good they are.

    Only tracks the tracker held long enough to be countable are listed. A
    two-frame flicker has a size too, and reporting it would pad the table with
    rows nobody can act on.
    """
    K = depth_model.frame_K
    parcels = []
    for tid, sizes in sorted(track_sizes.items()):
        if track_age.get(tid, 0) < cfg.min_track_age or len(sizes) < 2:
            continue
        s = _consensus(sizes)
        dims = sorted([s.length_m, s.width_m, s.height_m], reverse=True)
        parcels.append({
            "track": tid,
            "frames_measured": len(sizes),
            "distance_m": round(float(np.median([x.distance_m for x in sizes])), 3),
            "distance_range_m": [round(float(min(x.distance_m for x in sizes)), 2),
                                 round(float(max(x.distance_m for x in sizes)), 2)],
            "length_mm": round(s.length_m * 1000),
            "width_mm": round(s.width_m * 1000),
            "height_mm": round(s.height_m * 1000),
            "longest_side_mm": round(dims[0] * 1000),
            "volume_l": round(s.volume_l, 1),
            "size_class": s.class_name,
            "mask_kept": round(s.mask_kept, 2),
            # spread of the height across the pass: the honest error bar on a
            # measurement nobody can check against a tape measure
            "height_iqr_mm": round(float(np.subtract(*np.percentile(
                [x.height_m for x in sizes], [75, 25])) * 1000)),
        })
    volumes = [p["volume_l"] for p in parcels]
    classes = {}
    for p in parcels:
        classes[p["size_class"]] = classes.get(p["size_class"], 0) + 1
    return {
        "method": "Depth Anything 3 (DA3-LARGE intrinsics + DA3METRIC-LARGE depth)",
        "process_res": cfg.depth_process_res,
        "depth_every_n_frames": cfg.depth_every,
        "depth_frames": depth_model.frames_run,
        "avg_depth_ms": round(float(np.mean(depth_ms)), 1) if depth_ms else None,
        "intrinsics": {
            "fx": round(K.fx, 1), "fy": round(K.fy, 1),
            "cx": round(K.cx, 1), "cy": round(K.cy, 1),
            "hfov_deg": round(K.hfov_deg, 1),
            "frame_to_frame_spread_pct": round(depth_model.intrinsics_spread * 100, 2),
            "square_pixel_error_pct": round(K.square_pixel_error * 100, 2),
            "note": "predicted, not calibrated; distance scales with it, size does not",
        },
        "belt_plane": {
            "fit_rms_mm": round(belt.rms_m * 1000, 1),
            "pixels": belt.samples,
            "camera_height_above_belt_mm": round(belt.camera_height_m * 1000),
        },
        "size_scale": round(cfg.size_scale, 4),
        "size_scale_note": cfg.size_scale_note,
        "depth_corridor_m": list(cfg.depth_corridor) if cfg.depth_corridor else None,
        "detections_outside_corridor": corridor_dropped,
        "parcels_measured": len(parcels),
        "size_classes": classes,
        "total_volume_l": round(float(np.sum(volumes)), 1) if volumes else 0.0,
        "median_volume_l": round(float(np.median(volumes)), 1) if volumes else 0.0,
        "parcels": parcels,
    }


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
