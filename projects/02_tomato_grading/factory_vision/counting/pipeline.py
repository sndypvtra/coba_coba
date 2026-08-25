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

This module is the engine, not an entry point. Projects 01, 02 and 03 each own
a `config.py` and a `main.py` and call `run_case` with their own directories -
which is the whole demonstration for the first two: same engine, same weights,
different words.

    from factory_vision.counting import run_case
    summary = run_case(cfg, video_dir=..., output_dir=...)
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLOE

from factory_vision.counting.clips import ClipConfig
from factory_vision.counting.geometry import (build_counting_line, draw_roi,
                                              filter_detections)
from factory_vision.counting.overlay import INK, PALETTE, WARM, Hud, Panel
from factory_vision.tracking import resolve_tracker_cfg
from factory_vision.paths import WEIGHTS_DIR

warnings.filterwarnings("ignore")


def _counting_stats(frame_idx: int, fps: float, counted: int, crossing_frames,
                    active: int, tracks_seen: int) -> dict:
    """What every counting line knows about itself, and nothing more.

    A count on its own answers nothing an operator can act on: what a line is
    scheduled against is rate - how many an hour, how far apart they arrive.
    Both are derived from the crossings already recorded, so nothing here needs
    a second pass over anything.

    Rates are extrapolations from a clip of a few seconds. The panel labels them
    as rates and prints the observed count beside them, because an extrapolation
    shown without its sample size is how a demo becomes a promise nobody can
    keep.

    Anything beyond this - volumes, size mixes - is a *measurement*, and a
    project that does not measure must not be able to print one. Those keys are
    merged in by the measurement backend, if there is one.
    """
    elapsed_s = max(frame_idx / max(fps, 1e-6), 1e-6)
    hours = elapsed_s / 3600.0
    gaps = [(b - a) / fps for a, b in zip(crossing_frames, crossing_frames[1:])]
    return {
        "counted": counted,
        "elapsed_s": elapsed_s,
        "per_hour": counted / hours if hours > 0 else 0.0,
        "headway_s": float(np.mean(gaps)) if gaps else None,
        "active": active,
        "tracks_seen": tracks_seen,
    }


def _size_of(tid: int, locked: dict, running: dict, backend):
    """A track's size: the frozen one if it has been locked, else the running one."""
    if tid in locked:
        return locked[tid]
    return backend.consensus(running.get(tid) or [])


def _generic_panel(cfg: ClipConfig, stats: dict) -> Panel:
    """The panel a project gets if it does not build its own.

    Deliberately dull, and deliberately honest: it names the thing being counted
    from `cfg.label` and shows only what a counting line can actually know.
    """
    noun = cfg.label.upper()
    return Panel(
        title=f"{noun} COUNTING - LIVE",
        headline=f"{noun} COUNTED",
        subtitle=f"{stats['elapsed_s']:.1f} s elapsed",
        rows=[("THROUGHPUT", f"{stats['per_hour']:,.0f} /h", WARM),
              ("IN VIEW NOW", f"{stats['active']}", INK),
              ("HEADWAY", f"{stats['headway_s']:.1f} s" if stats["headway_s"] else "-", WARM),
              ("TRACKS SEEN", f"{stats['tracks_seen']}", INK)],
    )


def process(cfg: ClipConfig, args, video_dir: Path, output_dir: Path,
            backend=None, panel=None) -> dict:
    src = video_dir / cfg.filename
    info = sv.VideoInfo.from_video_path(str(src))
    w, h = info.width, info.height
    scale = w / 1920.0

    tracker_cfg = resolve_tracker_cfg(args.tracker, cfg.tracker_overrides, cfg.filename[:2],
                                     output_dir)
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
    # A project draws its own dashboard. What it cannot measure, it cannot
    # print - which is the whole reason this is injected rather than shared.
    build_panel = panel or (lambda stats: _generic_panel(cfg, stats))

    out_path = output_dir / f"{Path(cfg.filename).stem}__counted.mp4"
    out_info = sv.VideoInfo(width=w, height=h, fps=info.fps, total_frames=info.total_frames)

    per_class: dict[str, int] = {}
    unique_ids: set[int] = set()
    track_age: dict[int, int] = {}  # frames each ID has been held by the tracker
    times: list[float] = []
    frames_written = 0
    total_dets = 0

    depth_ms: list[float] = []
    # every measurement each track ever produced, so the reported size is a
    # median over a parcel's whole pass rather than one lucky frame
    track_sizes: dict[int, list] = {}
    locked_sizes: dict[int, object] = {}   # frozen once the parcel nears the line
    crossing_frames: list[int] = []        # when each count happened, for headway
    counted_sizes: list = []               # the size each counted parcel carried
    # A backend is the whole of "does this installation measure". Without one,
    # no depth model is loaded and the measurement path below is never entered -
    # see `measuring.Measurement`.
    if backend is not None:
        backend.prepare(src, w, h, output_dir)

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

            # Depth is refreshed every Nth frame; the gate uses the most recent
            # map. Which N, and why it is safe, is the backend's business.
            if backend is not None and (idx - 1) % backend.refresh_every == 0:
                td = time.time()
                backend.refresh(frame, f"f{idx:05d}")
                depth_ms.append((time.time() - td) * 1000)

            # One measurement per detection serves two purposes: it decides
            # whether the thing is on the belt at all, and if it is, it is the
            # size. Measuring first and gating on the result is what lets the
            # confidence floor sit at 0.05 - the background is rejected on
            # geometry, before the tracker is asked to hold an identity for it.
            frame_sizes: list = []
            if backend is not None:
                det, frame_sizes = backend.measure_frame(det)
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
            for j, flag_in in enumerate(crossed_in):
                if not flag_in:
                    continue
                name = locked.data.get("class_name", [cfg.label] * len(locked))[j]
                per_class[name] = per_class.get(name, 0) + 1
                crossing_frames.append(idx)
                if locked.tracker_id is not None and backend is not None:
                    size = _size_of(int(locked.tracker_id[j]), locked_sizes,
                                    track_sizes, backend)
                    if size is not None:
                        counted_sizes.append(size)

            # Attach each measurement to the track that carries it, and stop
            # once the backend says the reading should be frozen. A parcel
            # measured all the way to the edge of frame would keep revising its
            # size while it is being clipped by the frame border and occluded by
            # the trolley - the reading would move at exactly the moment it is
            # counted.
            if backend is not None and len(det) and det.tracker_id is not None and frame_sizes:
                for tid, size, box in zip(det.tracker_id, frame_sizes, det.xyxy):
                    if tid is None or size is None or not size.trusted:
                        continue
                    tid = int(tid)
                    if tid in locked_sizes:
                        continue
                    track_sizes.setdefault(tid, []).append(size)
                    centre_x = float(box[0] + box[2]) / 2.0
                    if backend.lock_ready(centre_x, len(track_sizes[tid])):
                        locked_sizes[tid] = backend.consensus(track_sizes[tid])

            annotated = draw_roi(frame.copy(), cfg, w, h)
            if len(tracked):
                if tracked.mask is not None:
                    annotated = mask_ann.annotate(annotated, tracked)
                annotated = trace_ann.annotate(annotated, tracked)
                annotated = box_ann.annotate(annotated, tracked)
                # The label says what stage the parcel is at, because that is
                # what an operator watching this needs: still being measured,
                # size frozen, or counted.
                labels = []
                for tid, conf in zip(tracked.tracker_id, tracked.confidence):
                    tid = int(tid)
                    size = (_size_of(tid, locked_sizes, track_sizes, backend)
                            if backend is not None else None)
                    if size is None:
                        labels.append(f"#{tid}  {conf:.2f}")
                        continue
                    dims = (f"{size.length_m*100:.0f}x{size.width_m*100:.0f}"
                            f"x{size.height_m*100:.0f}cm")
                    cls = size.class_name + size.class_mark
                    if tid in locked_sizes:
                        labels.append(f"#{tid} LOCKED {dims} {size.volume_l:.0f}L "
                                      f"[{cls}] {size.distance_m:.2f}m")
                    else:
                        labels.append(f"#{tid} {dims} [{cls}] "
                                      f"{size.distance_m:.2f}m")
                annotated = label_ann.annotate(annotated, tracked, labels)

            annotated = line_ann.annotate(annotated, line)
            stats = _counting_stats(idx, info.fps, line.in_count, crossing_frames,
                                    len(tracked), len(unique_ids))
            if backend is not None:
                live = [s for s in (_size_of(int(t), locked_sizes, track_sizes, backend)
                                    for t in tracked.tracker_id) if s is not None] \
                    if len(tracked) else []
                stats.update(backend.panel_stats(stats, counted_sizes, live,
                                                 locked_sizes))
            annotated = hud.draw(annotated, idx, line.in_count,
                                 build_panel(stats),
                                 float(np.mean(times[-30:])))
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
    if backend is not None:
        summary["dimensioning"] = backend.summary(track_sizes, track_age,
                                                  cfg.min_track_age, depth_ms)
    print(
        f"    DONE {out_path.name}  IN={line.in_count} (reverse={line.out_count}) "
        f"ids={len(unique_ids)} {np.mean(times):.0f}ms/f  "
        f"{out_path.stat().st_size/1e6:.1f}MB"
    )
    return summary


def run_case(cfg: ClipConfig, video_dir: Path, output_dir: Path, backend=None,
             panel=None, **overrides) -> dict:
    """Run one clip end to end, write its summary, and return it.

    Each project owns its own `config.py` and its own `output/`, so a summary is
    one clip's and nothing else's. The previous version merged every clip into a
    single shared file and had to re-sort it on every run to stop one case
    clobbering another's entry - a problem that only existed because the output
    was shared.

    ``backend`` is an optional `measuring.Measurement`. Give one and the clip is
    measured as well as counted; leave it out - as projects 01 and 02 do - and
    nothing metric is loaded at all.

    ``panel`` is an optional callable that turns one frame's stats into an
    `overlay.Panel`. Each project supplies its own, so a project cannot print a
    KPI it has no way of measuring - which is exactly what went wrong when the
    parcel dashboard was hardcoded here and the citrus line inherited it.
    """
    from types import SimpleNamespace

    args = SimpleNamespace(weights="yoloe-11l-seg.pt", tracker="tracktrack",
                           imgsz=1280, max_frames=0, stride=1)
    for key, value in overrides.items():
        setattr(args, key, value)

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = process(cfg, args, video_dir, output_dir, backend=backend,
                      panel=panel)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary
