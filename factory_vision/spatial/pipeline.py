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

from factory_vision.counting.tracking import resolve_tracker_cfg
from factory_vision.detect import DetView, build_tracker, suppress_contained
from factory_vision.paths import OUTPUT_DIR, VIDEO_DIR, WEIGHTS_DIR
from factory_vision.spatial import analytics as an
from factory_vision.spatial.bev import GroundMap
from factory_vision.spatial.calibration import load_cameras
from factory_vision.spatial.config import SCENES, SceneConfig
from factory_vision.spatial.fuse import Fuser
from factory_vision.spatial.lift import lift
from factory_vision.spatial import render as rd

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
                f"{path} missing - run scripts/fetch_warehouse_scene.py first")
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
                          cfg.floor_bounds_m, size=lay.eagle)
    gt_path = sdir / "ground_truth.json"
    gt = json.loads(gt_path.read_text()) if (gt_path.exists() and not args.no_gt) else None

    caps, n_avail = _open_clips(cfg)
    total = min(cfg.n_frames, n_avail)
    if args.max_frames:
        total = min(total, args.max_frames)
    fps = cfg.out_fps

    model = YOLOE(str(WEIGHTS_DIR / args.weights))
    model.set_classes(cfg.prompts, model.get_text_pe(cfg.prompts))
    tracker_cfg = resolve_tracker_cfg(args.tracker, cfg.tracker_overrides, "sp")
    trackers, tracker_name = {}, ""
    for v in cfg.views:
        trackers[v.sensor_id], tracker_name = build_tracker(tracker_cfg, fps)

    fuser = Fuser(cfg.fuse_radius_m, cfg.max_age_frames)
    view_ids = [v.sensor_id for v in cfg.views]
    eagle_bg, gm = rd.eagle_base(gmap, cfg, cams, view_ids)

    out_path = OUTPUT_DIR / f"{cfg.name}__spatial.mp4"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    width, height = lay.width, lay.height
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (width, height))

    trails: dict[int, deque] = {}
    series: list[int] = []
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

            result = model.predict(frame, conf=cfg.conf, iou=0.5, imgsz=args.imgsz,
                                   agnostic_nms=True, verbose=False)[0]
            det = sv.Detections.from_ultralytics(result)
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

            for r in np.asarray(out):
                box, tid, conf, cls = r[:4], int(r[4]), float(r[5]), int(r[6])
                label = cfg.prompts[cls] if cls < len(cfg.prompts) else "person"
                label = "person" if label == cfg.person_prompt else "robot"
                o = lift(cams[sid], box, conf, label, tid,
                         cfg.valid_bounds_m, cfg.height_bounds_m)
                if o.ok:
                    obs_all.append(o)
                else:
                    rejects[o.reject] = rejects.get(o.reject, 0) + 1

        clusters = fuser.update(idx, obs_all)
        times.append((time.time() - t0) * 1000)

        # --------------------------------------------------------- bookkeeping
        confirmed = fuser.confirmed(cfg.min_track_age, cfg.min_corroborating_views)
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
                                 (t.frames[-1] - t.frames[0] + 1) / fps, len(c.members)))
            # Validation is offline and uses the whole of each identity's life,
            # including the frames before it reached the age gate.
            est_rows.append((c.gid, c.x, c.y, t.label))
            if c.gid in confirmed and t.label == "person":
                z = an.area_zone(c.x, c.y, cfg.zones)
                zone_seconds[z] = zone_seconds.get(z, 0.0) + 1.0 / fps
                for lane in an.restricted_hits(c.x, c.y, cfg.zones):
                    lane_seconds[lane] = lane_seconds.get(lane, 0.0) + 1.0 / fps
                trails.setdefault(c.gid, deque(maxlen=trail_len)).append((c.x, c.y))
        per_frame_est[idx] = est_rows

        people_now = sum(1 for g, lab, *_ in drawable if lab == "person" and g in confirmed)
        robots_now = sum(1 for g, lab, *_ in drawable if lab != "person" and g in confirmed)
        series.append(people_now)

        # --------------------------------------------------------- rendering
        observed_by = {c.gid: set(c.cameras) for c in clusters}
        tiles = {}
        for v in cfg.views:
            cam = cams[v.sensor_id]
            here = []
            for gid, label, x, y, h, yaw, seen_s, ncam in drawable:
                observed = v.sensor_id in observed_by.get(gid, ())
                # A view that detected the object always draws it. The frustum
                # test only decides whether to *add* a box to a view that did
                # not - otherwise a detection near the frame edge, whose head
                # projects off the top, would go undrawn in the very camera
                # that found it.
                if observed or (cam.looks_at(x, y, 0.0) and cam.looks_at(x, y, 1.6)):
                    here.append((gid, label, x, y, h, yaw, observed))
            label = v.sensor_id if lay.tile_w < 560 else f"{v.sensor_id}   {v.provenance}"
            tiles[(v.side, v.row, v.col)] = rd.camera_tile(
                frames[v.sensor_id], cam, label, here, cfg, lay)

        eagle = rd.eagle_frame(eagle_bg, gm, cfg, drawable, trails, idx, fps)

        motions = {g: an.motion(t, fps) for g, t in confirmed.items()}
        walked = sum(m[0] for g, m in motions.items()
                     if confirmed[g].label == "person")
        gap_txt, gap_warn = "-", False
        pp = [(x, y) for g, lab, x, y, *_ in drawable if lab == "person"]
        bb = [(x, y) for g, lab, x, y, *_ in drawable if lab != "person"]
        if pp and bb:
            gval = min(float(np.hypot(a[0] - b[0], a[1] - b[1])) for a in pp for b in bb)
            gap_txt, gap_warn = f"{gval:.1f} m", gval < 1.5
        zone_total = max(sum(zone_seconds.values()), 1e-6)
        stats = {
            "people_now": people_now,
            "robots_now": robots_now,
            "distinct_people": sum(1 for t in confirmed.values() if t.label == "person"),
            "distance_m": walked,
            "gap": gap_txt,
            "gap_warn": gap_warn,
            "zone_rows": sorted(zone_seconds.items(), key=lambda kv: -kv[1])[:3],
            "lane_rows": [(z.name, lane_seconds.get(z.name, 0.0))
                          for z in cfg.zones if z.kind == "restricted"],
            "zone_total": zone_total,
            "n_views": len(cfg.views),
        }
        live_rows = []
        for gid, label, x, y, h, yaw, seen_s, ncam in sorted(drawable):
            if gid not in confirmed:
                continue
            live_rows.append({
                "gid": gid, "label": label,
                "tag": f"{'P' if label == 'person' else 'R'}{gid}",
                "height": f"{h:.2f} m" if np.isfinite(h) else "-",
                "speed": f"{motions[gid][1]:.2f} m/s",
                "views": str(ncam),
                "seen": f"{seen_s:.1f} s",
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
    confirmed = fuser.confirmed(cfg.min_track_age, cfg.min_corroborating_views)
    single_view = [g for g, t in fuser.confirmed(cfg.min_track_age).items()
                   if g not in confirmed]
    reports = [an.describe(t, cfg) for t in confirmed.values()]
    people = [r for r in reports if r.label == "person"]
    robots = [r for r in reports if r.label != "person"]

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
        "occupancy_mean": round(float(np.mean(series)), 2) if series else 0.0,
        "occupancy_max": int(max(series)) if series else 0,
        "floor_walked_m": round(sum(r.path_m for r in people), 1),
        "walking_speed_mean_ms": round(float(np.mean([r.speed_mean for r in people])), 2)
                                 if people else None,
        "person_height_median_m": round(float(np.median([r.height_m for r in people
                                                         if np.isfinite(r.height_m)])), 2)
                                  if people else None,
        "fusion": {
            "observations_merged": fuser.merges,
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
        "people": [r.as_dict() for r in sorted(people, key=lambda r: r.gid)],
        "robots": [r.as_dict() for r in sorted(robots, key=lambda r: r.gid)],
        "occupancy_series": series,
        "avg_ms_per_frame": round(float(np.mean(times)), 1) if times else None,
        "output": out_path.name,
    }
    if gt_by_frame:
        summary["validation"] = an.validate(per_frame_conf, gt_by_frame, cfg)
        summary["validation"]["note"] = (
            "ground truth is read only here; detection, lifting and fusion never see it")

    (OUTPUT_DIR / f"{cfg.name}__spatial.json").write_text(json.dumps(summary, indent=2))
    return summary


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
