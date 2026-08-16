"""Case 6 - many fixed cameras, one warehouse floor, people located in 3D.

The chain, end to end:

  1. YOLOE detects from words alone - "person", "humanoid robot" - in each
     1920x1080 view. No training, no labels, no fine-tuning.
  2. Each view runs its own tracker, so a person keeps an identity within that
     camera.
  3. Every box is lifted onto the floor plane through the camera's homography,
     and its height is solved in closed form from the camera matrix. A rectangle
     becomes a position in metres and a stature in metres.
  4. Those positions are fused across cameras into one global identity per
     person - the step that turns a dozen headcounts into one.
  5. The result is drawn back into every view as a 3D box, plotted on the
     dataset's own top-down render of the building, and reduced to statistics.

What makes this measurable rather than merely presentable is that the dataset
ships the true 3D position of every object. The pipeline never reads it; the
summary reports the error against it.

Run:  python cases/case6_warehouse_spatial.py
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from collections import deque

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLOE

from factory_vision.tracking import resolve_tracker_cfg
from factory_vision.detect import DetView, build_tracker, suppress_contained
from factory_vision.paths import WEIGHTS_DIR, project_dirs

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)
import analytics as an
from bev import GroundMap
from calibration import load_cameras
from config import SCENES, SceneConfig
from fuse import Fuser
from lift import lift
import render as rd

warnings.filterwarnings("ignore")

TRAIL_S = 6.0


def scene_dir(cfg: SceneConfig):
    return VIDEO_DIR / cfg.asset_dir


def _open_clips(cfg: SceneConfig):
    caps, n = {}, None
    for v in cfg.views:
        path = VIDEO_DIR / v.filename
        if not path.exists():
            raise FileNotFoundError(
                f"{path} missing - run: python fetch_scene.py")
        cap = cv2.VideoCapture(str(path))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        n = count if n is None else min(n, count)
        caps[v.sensor_id] = cap
    return caps, n


def process(cfg: SceneConfig, args) -> dict:
    sdir = scene_dir(cfg)
    cams = load_cameras(sdir / "calibration.json")
    lay = rd.Layout(cfg)
    gmap = GroundMap.load(sdir / "map.png", sdir / "calibration.json",
                          cfg.floor_bounds_m, size=lay.eagle, flip=cfg.plan_flipped)
    gt_path = sdir / "ground_truth.json"
    gt = json.loads(gt_path.read_text()) if (gt_path.exists() and not args.no_gt) else None

    caps, n_avail = _open_clips(cfg)
    total = min(cfg.n_frames, n_avail)
    if args.max_frames:
        total = min(total, args.max_frames)
    fps = cfg.out_fps

    model = YOLOE(str(WEIGHTS_DIR / args.weights))
    model.set_classes(cfg.prompts, model.get_text_pe(cfg.prompts))
    tracker_cfg = resolve_tracker_cfg(args.tracker, cfg.tracker_overrides, "sp", OUTPUT_DIR)
    trackers, tracker_name = {}, ""
    for v in cfg.views:
        trackers[v.sensor_id], tracker_name = build_tracker(tracker_cfg, fps)

    class_conf = [cfg.spec(k).get("conf", cfg.conf) for k in cfg.kinds]
    floor_conf = min(class_conf)
    min_views = {k: cfg.spec(k).get("min_views", cfg.min_corroborating_views)
                 for k in cfg.kinds}

    fuser = Fuser(cfg.fuse_radius_m, cfg.max_age_frames)
    view_ids = [v.sensor_id for v in cfg.views]
    eagle_bg, gm = rd.eagle_base(gmap, cfg, cams, view_ids)

    out_path = OUTPUT_DIR / f"{cfg.name}__spatial.mp4"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    width, height = lay.width, lay.height
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (width, height))

    trails: dict[int, deque] = {}
    series: list[tuple[int, int]] = []      # (headcount, of them walking)
    heat = rd.HeatMap(gm)
    lane_open: set[int] = set()
    lane_entries = 0
    lane_by_person: dict[int, float] = {}
    near_open: set[tuple[int, int]] = set()
    near_events = 0
    near_frames = 0
    bay_frames: dict[int, dict[int, str]] = {}
    bay_load: dict[str, float] = {}
    per_frame_est: dict[int, list] = {}
    zone_seconds: dict[str, float] = {}
    lane_seconds: dict[str, float] = {}
    rejects: dict[str, int] = {}
    raw_dets = dup_dropped = 0
    times: list[float] = []
    trail_len = int(TRAIL_S * fps)

    for idx in range(total):
        t0 = time.time()
        frames, obs_all = {}, []
        for v in cfg.views:
            sid = v.sensor_id
            ok, frame = caps[sid].read()
            if not ok:
                frames[sid] = np.zeros((cams[sid].height, cams[sid].width, 3), np.uint8)
                continue
            frames[sid] = frame

            # One inference at the lowest threshold any class asks for, then
            # each class's own threshold re-applied. A pallet load scores
            # 0.15-0.20 where a person scores 0.9, so a single threshold either
            # loses the loads or floods the frame with person-shaped noise.
            # NMS runs per class, not across classes. A person standing in
            # front of a pallet load overlaps it heavily, and class-agnostic NMS
            # makes them compete: one of the two boxes is suppressed and which
            # one depends on a confidence race between a 0.9 person and a 0.2
            # load. That race is what fragmented the person identities when the
            # goods class was added.
            result = model.predict(frame, conf=floor_conf, iou=0.5, imgsz=args.imgsz,
                                   agnostic_nms=False, verbose=False)[0]
            det = sv.Detections.from_ultralytics(result)
            if len(det):
                keep = det.confidence >= np.array(
                    [class_conf[int(c)] for c in det.class_id])
                det = det[keep]
            raw_dets += len(det)
            before = len(det)
            det = suppress_contained(det, cfg.dedup_containment)
            dup_dropped += before - len(det)

            if len(det):
                out = trackers[sid].update(
                    DetView(det.xyxy.astype(np.float32),
                            det.confidence.astype(np.float32),
                            det.class_id.astype(np.float32)), frame)
            else:
                out = trackers[sid].update(
                    DetView(np.zeros((0, 4), np.float32), np.zeros(0, np.float32),
                            np.zeros(0, np.float32)), frame)

            kinds = cfg.kinds
            for r in np.asarray(out):
                box, tid, conf, cls = r[:4], int(r[4]), float(r[5]), int(r[6])
                kind = kinds[cls] if cls < len(kinds) else kinds[0]
                o = lift(cams[sid], box, conf, kind, tid,
                         cfg.valid_bounds_m, cfg.spec(kind)["height"],
                         cfg.spec(kind).get("height_reject", True))
                if o.ok:
                    obs_all.append(o)
                else:
                    rejects[o.reject] = rejects.get(o.reject, 0) + 1

        clusters = fuser.update(idx, obs_all)
        times.append((time.time() - t0) * 1000)

        # --------------------------------------------------------- bookkeeping
        confirmed = fuser.confirmed(cfg.min_track_age, min_views)
        drawable, est_rows = [], []
        for c in clusters:
            t = fuser.tracks[c.gid]
            if len(t.frames) < 2:
                continue
            # Only confirmed identities are drawn, so that every box in the
            # picture is also a row in the panel. Showing provisional ones would
            # be more informative and less honest: the reader's obvious check is
            # to count the boxes against the headline figure, and that check has
            # to come out right.
            if c.gid in confirmed:
                drawable.append((c.gid, t.label, c.x, c.y, t.height, t.yaw,
                                 (t.frames[-1] - t.frames[0] + 1) / fps,
                                 len(c.members), t.width))
            # Validation is offline and uses the whole of each identity's life,
            # including the frames before it reached the age gate.
            est_rows.append((c.gid, c.x, c.y, t.label))
            if c.gid in confirmed and cfg.spec(t.label).get("goods"):
                # Which painted bay this pallet is sitting in, if any. Bay
                # membership over time is what a transfer is made of.
                bay = next(iter(an.restricted_hits(c.x, c.y, cfg.zones)), None)
                if bay:
                    bay_frames.setdefault(idx, {})[c.gid] = bay
                    bay_load[bay] = bay_load.get(bay, 0.0) + 1.0 / fps
            if c.gid in confirmed and t.label == "person":
                z = an.area_zone(c.x, c.y, cfg.zones)
                zone_seconds[z] = zone_seconds.get(z, 0.0) + 1.0 / fps
                hits = an.restricted_hits(c.x, c.y, cfg.zones)
                for lane in hits:
                    lane_seconds[lane] = lane_seconds.get(lane, 0.0) + 1.0 / fps
                if hits:
                    lane_by_person[c.gid] = lane_by_person.get(c.gid, 0.0) + 1.0 / fps
                # An entry is a crossing of the boundary, not a frame spent
                # inside it: one person working in a lane for ten seconds is one
                # event, and ten people stepping through it is ten.
                if hits and c.gid not in lane_open:
                    lane_entries += 1
                if hits:
                    lane_open.add(c.gid)
                else:
                    lane_open.discard(c.gid)
                trails.setdefault(c.gid, deque(maxlen=trail_len)).append((c.x, c.y))
                heat.add(c.x, c.y)
        per_frame_est[idx] = est_rows

        people_now = sum(1 for g, lab, *_ in drawable if lab == "person" and g in confirmed)
        robots_now = sum(1 for g, lab, *_ in drawable if lab != "person" and g in confirmed)

        # near misses, live: a person inside the threshold of a machine
        ppl_xy = [(g, x, y) for g, lab, x, y, *_ in drawable if lab == "person"]
        bot_xy = [(g, x, y) for g, lab, x, y, *_ in drawable if lab != "person"]
        near_now = {(pg, bg) for pg, px, py in ppl_xy for bg, bx, by in bot_xy
                    if np.hypot(px - bx, py - by) < an.NEAR_MISS_M}
        near_events += len(near_now - near_open)
        near_frames += 1 if near_now else 0
        near_open = near_now
        gap_val = min((float(np.hypot(px - bx, py - by))
                       for _, px, py in ppl_xy for _, bx, by in bot_xy), default=None)

        # --------------------------------------------------------- rendering
        observed_by = {c.gid: set(c.cameras) for c in clusters}
        tiles = {}
        for v in cfg.views:
            cam = cams[v.sensor_id]
            here = []
            for gid, label, x, y, h, yaw, seen_s, ncam, wid in drawable:
                observed = v.sensor_id in observed_by.get(gid, ())
                # A view that detected the object always draws it. The frustum
                # test only decides whether to *add* a box to a view that did
                # not - otherwise a detection near the frame edge, whose head
                # projects off the top, would go undrawn in the very camera
                # that found it.
                if observed or (cam.looks_at(x, y, 0.0) and cam.looks_at(x, y, 1.6)):
                    here.append((gid, label, x, y, h, yaw, observed, wid))
            tiles[(v.side, v.row, v.col)] = rd.camera_tile(
                frames[v.sensor_id], cam, v.sensor_id, here, cfg, lay)

        eagle = rd.eagle_frame(eagle_bg, gm, cfg, drawable, trails, heat)

        motions = {g: an.motion(t, fps) for g, t in confirmed.items()}
        people_ids = [g for g, t in confirmed.items() if t.label == "person"]
        walked = sum(motions[g][0] for g in people_ids)
        moving_now = sum(1 for g, lab, *_ in drawable
                         if lab == "person" and g in confirmed
                         and an.current_speed(confirmed[g], fps) > an.MOVING_MS)
        series.append((people_now, moving_now))
        # Person-time, not clip-time: two people for ten seconds is twenty
        # person-seconds, and the travel rate a manager compares against a
        # benchmark is per person per hour.
        person_seconds = max(sum(len(confirmed[g].frames) for g in people_ids) / fps, 1e-6)
        moving_pct = 100.0 * float(np.mean([motions[g][3] for g in people_ids])) \
            if people_ids else 0.0
        zone_total = max(sum(zone_seconds.values()), 1e-6)
        stats = {
            "people_now": people_now,
            "people_peak": max(h for h, _ in series),
            "robots_now": robots_now,
            "moving_pct": moving_pct,
            "travel_rate": walked / person_seconds * 3600.0,
            "lane_entries": lane_entries,
            "lane_seconds": sum(lane_seconds.values()),
            "near_miss_events": near_events,
            "near_miss_m": an.NEAR_MISS_M,
            "gap": f"{gap_val:.1f} m" if gap_val is not None else "-",
            "zone_rows": [(k, 100.0 * v / zone_total)
                          for k, v in sorted(zone_seconds.items(), key=lambda kv: -kv[1])[:3]],
            "lane_rows": [(z.name, lane_seconds.get(z.name, 0.0))
                          for z in cfg.zones if z.kind == "restricted"],
            "n_views": len(cfg.views),
        }
        live_rows = []
        for gid, label, x, y, h, yaw, seen_s, ncam, wid in sorted(drawable):
            if gid not in confirmed:
                continue
            live_rows.append({
                "gid": gid, "label": label,
                "tag": f"{'P' if label == 'person' else 'R'}{gid}",
                "seen": f"{seen_s:.0f} s",
                "walked": f"{motions[gid][0]:.1f} m",
                "moving": f"{100 * motions[gid][3]:.0f}%",
                "lane": (f"{lane_by_person[gid]:.0f}s"
                         if lane_by_person.get(gid, 0.0) >= 0.5 else "-"),
                "in_lane": bool(an.restricted_hits(x, y, cfg.zones)),
                "zone": an.area_zone(x, y, cfg.zones),
            })
        panel_img = rd.panel(width, cfg, stats, series, live_rows,
                             idx / fps, total / fps, total, tracker_name)
        writer.write(lay.mosaic(tiles, eagle, panel_img))

        if args.progress and idx % 25 == 0:
            print(f"    frame {idx:3d}/{total}  people={people_now} "
                  f"robots={robots_now}  ids={len(confirmed)}", flush=True)

    writer.release()
    for c in caps.values():
        c.release()

    # ------------------------------------------------------------- summary
    confirmed = fuser.confirmed(cfg.min_track_age, min_views)
    single_view = [g for g, t in fuser.confirmed(cfg.min_track_age).items()
                   if g not in confirmed]
    reports = [an.describe(t, cfg) for t in confirmed.values()]
    people = [r for r in reports if r.label == "person"]
    goods = [r for r in reports if cfg.spec(r.label).get("goods")]
    robots = [r for r in reports if r.label != "person" and r not in goods]

    # Validation and the proximity figure are offline measurements, so they use
    # the set of identities that ended up confirmed rather than the set that had
    # already reached the age gate at each instant. The live occupancy series
    # uses the latter, because that is what the panel could honestly show at the
    # time - the two therefore differ during the first few frames of the clip.
    per_frame_conf = {i: [r for r in rows if r[0] in confirmed]
                      for i, rows in per_frame_est.items()}

    gt_by_frame = {}
    if gt is not None:
        for i in range(total):
            src = cfg.start_frame + i * cfg.stride
            gt_by_frame[i] = gt.get(str(src), [])

    summary = {
        "scene": cfg.name,
        "description": cfg.scene,
        "source": cfg.source,
        "licence": cfg.licence,
        "cameras": [{"sensor": v.sensor_id, "side": v.side,
                     "row": v.row, "col": v.col,
                     "banner_tile": v.provenance} for v in cfg.views],
        "clip": {
            "start_frame": cfg.start_frame,
            "window_frames": cfg.window_frames,
            "stride": cfg.stride,
            "frames_rendered": total,
            "fps_out": round(fps, 3),
            "duration_seconds": round(total / fps, 2),
        },
        "prompts": cfg.prompts,
        "conf": cfg.conf,
        "distinct_people": len(people),
        "distinct_robots": len(robots),
        "occupancy_mean": round(float(np.mean([h for h, _ in series])), 2) if series else 0.0,
        "occupancy_max": int(max(h for h, _ in series)) if series else 0,
        "floor_walked_m": round(sum(r.path_m for r in people), 1),
        "walking_speed_mean_ms": round(float(np.mean([r.speed_mean for r in people])), 2)
                                 if people else None,
        "person_height_median_m": round(float(np.median([r.height_m for r in people
                                                         if np.isfinite(r.height_m)])), 2)
                                  if people else None,
        # The block an operations manager reads. Everything below it is the
        # engineering evidence for these five lines.
        "operations": _operations(people, zone_seconds, lane_seconds,
                                  lane_entries, series, fps),
        "fusion": {
            "observations_merged": fuser.merges,
            "same_camera_duplicates_dropped": fuser.same_camera_dropped,
            "cross_camera_agreement_m": _agreement(reports),
            "mean_views_per_person": round(float(np.mean([r.cameras_mean for r in people])), 2)
                                     if people else None,
            "single_camera_share": round(float(np.mean([r.single_camera_share for r in people])), 3)
                                   if people else None,
            "associations_recovered_by_track_key": fuser.key_recoveries,
            "min_corroborating_views": cfg.min_corroborating_views,
            "identities_dropped_as_single_view": len(single_view),
        },
        "filtering": {
            "raw_detections": raw_dets,
            "duplicate_boxes_removed": dup_dropped,
            "lift_rejected": rejects,
        },
        "zone_seconds": {k: round(v, 1) for k, v in sorted(zone_seconds.items(),
                                                           key=lambda kv: -kv[1])},
        "restricted_lane_seconds": {k: round(v, 1) for k, v in lane_seconds.items()},
        "proximity": an.proximity(per_frame_conf, fps),
        "goods": {**an.transfers(bay_frames, fps),
                  "pallet_seconds_by_bay": {k: round(v, 1)
                                            for k, v in sorted(bay_load.items())},
                  "pallets_tracked": sum(1 for t in confirmed.values()
                                         if cfg.spec(t.label).get("goods"))},
        "people": [r.as_dict() for r in sorted(people, key=lambda r: r.gid)],
        "robots": [r.as_dict() for r in sorted(robots, key=lambda r: r.gid)],
        "pallets": [r.as_dict() for r in sorted(goods, key=lambda r: r.gid)],
        # Everything an interactive floor plan needs to replay this clip without
        # the video: the outlines, the camera positions and one row per identity
        # per sampled frame. Positions are rounded to the centimetre, which is
        # three times finer than the measured error and keeps the file small.
        "replay": {
            "fps": round(fps, 3),
            "frames": total,
            "floor_bounds_m": list(cfg.floor_bounds_m),
            "zones": [{"name": z.name, "kind": z.kind, "polygon_m": z.polygon_m}
                      for z in cfg.zones if z.polygon_m],
            "cameras": [{"id": v.sensor_id,
                         "x": round(float(cams[v.sensor_id].centre[0]), 2),
                         "y": round(float(cams[v.sensor_id].centre[1]), 2)}
                        for v in cfg.views],
            "tracks": [
                {"id": g, "kind": t.label,
                 "height_m": round(t.height, 2) if np.isfinite(t.height) else None,
                 "t0": t.frames[0],
                 "xy": [[round(x, 2), round(y, 2)] for x, y in zip(t.xs, t.ys)],
                 "f": t.frames}
                for g, t in sorted(confirmed.items())
            ],
        },
        "occupancy_series": [h for h, _ in series],
        "walking_series": [w for _, w in series],
        "avg_ms_per_frame": round(float(np.mean(times)), 1) if times else None,
        "output": out_path.name,
    }
    if gt_by_frame:
        summary["validation"] = an.validate(per_frame_conf, gt_by_frame, cfg)
        summary["validation"]["note"] = (
            "ground truth is read only here; detection, lifting and fusion never see it")

    (OUTPUT_DIR / f"{cfg.name}__spatial.json").write_text(json.dumps(summary, indent=2))
    return summary


def _operations(people, zone_seconds, lane_seconds, lane_entries, series, fps) -> dict:
    """The five lines a shift supervisor would actually be shown.

    Rates are per *person*-hour rather than per clip, because 30 seconds of
    footage is not a shift and the only honest way to state a travel figure is
    the rate it implies. Everything is derived from the same world tracks the
    validation block is measured against.
    """
    person_seconds = sum(r.frames for r in people) / fps
    walked = sum(r.path_m for r in people)
    total_zone = max(sum(zone_seconds.values()), 1e-6)
    return {
        "headcount_mean": round(float(np.mean([h for h, _ in series])), 2) if series else 0.0,
        "headcount_peak": int(max((h for h, _ in series), default=0)),
        "person_seconds_observed": round(person_seconds, 1),
        "walking_share_pct": round(100.0 * float(np.mean([r.moving_share for r in people])), 1)
                             if people else None,
        "travel_m_per_person_hour": round(walked / max(person_seconds, 1e-6) * 3600.0, 0),
        "travel_m_per_person": round(walked / max(len(people), 1), 1),
        "time_by_area_pct": {k: round(100.0 * v / total_zone, 1)
                             for k, v in sorted(zone_seconds.items(), key=lambda kv: -kv[1])},
        "pallet_lane_entries": lane_entries,
        "pallet_lane_seconds": round(sum(lane_seconds.values()), 1),
        "pallet_lane_share_pct": round(100.0 * sum(lane_seconds.values()) / total_zone, 1),
        "pallet_lane_entries_per_person_hour": round(
            lane_entries / max(person_seconds, 1e-6) * 3600.0, 0),
        # What the rate implies over a shift. This is the form the figure has to
        # take before anyone acts on it - "10 m walked" is not a finding, "8 km a
        # shift" is - but it is an extrapolation from 30 seconds and is labelled
        # as one rather than presented as an observation.
        "implied_per_8h_shift": {
            "walk_km_per_person": round(walked / max(person_seconds, 1e-6) * 3600.0 * 8 / 1000.0, 1),
            "pallet_lane_entries_per_person": round(
                lane_entries / max(person_seconds, 1e-6) * 3600.0 * 8, 0),
            "caveat": "linear extrapolation of a 30 s sample, not an observation",
        },
        "note": ("rates are per person-hour; walking means a straight-line world "
                 f"speed above {an.MOVING_MS} m/s over a 0.6 s window"),
    }


def _agreement(reports) -> float | None:
    vals = [r.agreement_m for r in reports if np.isfinite(r.agreement_m)]
    return round(float(np.median(vals)), 3) if vals else None


def _args(**overrides):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default=SCENES[0].name,
                    choices=[s.name for s in SCENES])
    ap.add_argument("--weights", default="yoloe-11l-seg.pt")
    ap.add_argument("--tracker", default="tracktrack")
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--no-gt", action="store_true",
                    help="skip the ground-truth validation block")
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args([]) if overrides else ap.parse_args()
    for k, v in overrides.items():
        setattr(args, k.replace("-", "_"), v)
    return args


def run_case(scene: str = "warehouse_014", **overrides) -> dict:
    cfg = next(s for s in SCENES if s.name == scene)
    return process(cfg, _args(**overrides))


def main():
    args = _args()
    cfg = next(s for s in SCENES if s.name == args.scene)
    summary = process(cfg, args)
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("people", "robots", "occupancy_series")}, indent=2))


if __name__ == "__main__":
    main()
