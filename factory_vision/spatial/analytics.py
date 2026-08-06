"""What the floor plan is for: numbers a warehouse manager can act on.

Everything here is computed in metres and seconds from the fused world tracks,
so none of it is tied to a camera. Headcount, where people spent their time,
how far they walked, how fast, how close they came to a moving robot.

Two measurement notes that the numbers depend on, stated here rather than
buried:

*Speed and distance need smoothing, and the reason is arithmetic.* A floor
position carries roughly 0.3 m of error. Differencing consecutive samples 0.1 s
apart turns that into 3 m/s of pure noise - larger than walking pace - and
summing those differences inflates path length without limit. Both are therefore
computed on a track smoothed over `SMOOTH_S` seconds, and that window is
reported alongside the result.

*The ground truth is used as a ruler, never as an input.* The dataset ships the
true 3D position of every object, so the error of this pipeline can be measured
instead of asserted. Nothing in the detection, lifting or fusion path reads it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from factory_vision.spatial.config import SceneConfig, Zone
from factory_vision.spatial.fuse import GlobalTrack

SMOOTH_S = 0.5


# ------------------------------------------------------------------- zones


def in_polygon(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    """Even-odd ray cast. Polygons here have a handful of vertices."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xh = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xh:
                inside = not inside
    return inside


def area_zone(x: float, y: float, zones: list[Zone]) -> str:
    """Which named area a floor point falls in.

    Areas are checked in order and the first hit wins, so the outlined blocks
    take precedence and the zone declared with an empty outline is the
    catch-all - "the rest of the marked floor" is a real answer, and giving it a
    name beats reporting a blank.
    """
    fallback = "unassigned"
    for z in zones:
        if z.kind != "area":
            continue
        if not z.polygon_m:
            fallback = z.name
        elif in_polygon(x, y, z.polygon_m):
            return z.name
    return fallback


def restricted_hits(x: float, y: float, zones: list[Zone]) -> list[str]:
    return [z.name for z in zones
            if z.kind == "restricted" and in_polygon(x, y, z.polygon_m)]


# ------------------------------------------------------------- trajectories


def smooth_track(xs, ys, window: int):
    """Centred moving average, shrinking at the ends rather than padding."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    if window <= 1 or len(xs) < 2:
        return xs, ys
    out_x, out_y = np.empty_like(xs), np.empty_like(ys)
    half = window // 2
    for i in range(len(xs)):
        a, b = max(0, i - half), min(len(xs), i + half + 1)
        out_x[i], out_y[i] = xs[a:b].mean(), ys[a:b].mean()
    return out_x, out_y


@dataclass
class PersonReport:
    gid: int
    label: str
    frames: int
    first_s: float
    last_s: float
    dwell_s: float
    height_m: float
    path_m: float
    speed_mean: float
    speed_max: float
    cameras_mean: float
    cameras_max: int
    single_camera_share: float
    agreement_m: float
    zone_seconds: dict
    restricted_seconds: dict

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = round(v, 3)
        d["zone_seconds"] = {k: round(v, 1) for k, v in self.zone_seconds.items()}
        d["restricted_seconds"] = {k: round(v, 1) for k, v in self.restricted_seconds.items()}
        return d


def motion(track: GlobalTrack, fps: float) -> tuple[float, float, float]:
    """Path length, mean speed and 95th-percentile speed, all smoothed.

    Kept separate from `describe` because the live panel needs it on every
    identity on every frame, while the zone breakdown is only needed once at the
    end. Folding the two together made the render loop re-run a point-in-polygon
    test over every sample of every track's history, every frame.
    """
    window = max(1, int(round(SMOOTH_S * fps)))
    sx, sy = smooth_track(track.xs, track.ys, window)
    if len(sx) < 2:
        return 0.0, 0.0, 0.0
    step = np.linalg.norm(np.diff(np.stack([sx, sy], 1), axis=0), axis=1)
    dt = np.diff(np.asarray(track.frames, float)) / fps
    speeds = step / np.maximum(dt, 1e-6)
    # A 95th percentile rather than the maximum: one bad frame should not become
    # the headline "top speed".
    return (float(step.sum()), float(speeds.mean()),
            float(np.percentile(speeds, 95)))


def describe(track: GlobalTrack, cfg: SceneConfig) -> PersonReport:
    fps = cfg.out_fps
    path, smean, smax = motion(track, fps)

    per_sample = 1.0 / fps
    zone_s: dict[str, float] = {}
    restr_s: dict[str, float] = {}
    for x, y in zip(track.xs, track.ys):
        area = area_zone(x, y, cfg.zones)
        zone_s[area] = zone_s.get(area, 0.0) + per_sample
        for name in restricted_hits(x, y, cfg.zones):
            restr_s[name] = restr_s.get(name, 0.0) + per_sample

    cams = np.asarray(track.cameras, float)
    multi = [s for s, c in zip(track.spreads, track.cameras) if c > 1]
    return PersonReport(
        gid=track.gid,
        label=track.label,
        frames=len(track.frames),
        first_s=track.frames[0] / fps,
        last_s=track.frames[-1] / fps,
        dwell_s=(track.frames[-1] - track.frames[0] + 1) / fps,
        height_m=track.height,
        path_m=path,
        speed_mean=smean,
        speed_max=smax,
        cameras_mean=float(cams.mean()),
        cameras_max=int(cams.max()),
        single_camera_share=float((cams == 1).mean()),
        agreement_m=float(np.median(multi)) if multi else float("nan"),
        zone_seconds=zone_s,
        restricted_seconds=restr_s,
    )


# --------------------------------------------------------------- validation


def validate(per_frame: dict[int, list[tuple[int, float, float, str]]],
             gt_by_frame: dict[int, list[dict]],
             cfg: SceneConfig, gate_m: float = 1.0) -> dict:
    """Measure this pipeline against the dataset's own 3D positions.

    Estimates and ground-truth objects are matched per frame by world distance
    with the Hungarian algorithm and a hard gate, which is the same rule the
    tracking benchmarks use. The gate is one metre - about a person's own width,
    so a match means the same person rather than merely the same corner of the
    building. Reported: how far off the positions are, how often a person is
    found at all, how often one is invented, and how many separate global
    identities each real person collected - the last being the number that
    decides whether the dwell times can be believed.
    """
    errs, matched, gt_total, est_total, fp = [], 0, 0, 0, 0
    id_map: dict[int, set] = {}
    count_err = []
    for frame, ests in sorted(per_frame.items()):
        gt = [o for o in gt_by_frame.get(frame, []) if o["object type"] == "Person"]
        people = [e for e in ests if e[3] == "person"]
        gt_total += len(gt)
        est_total += len(people)
        count_err.append(len(people) - len(gt))
        if not gt or not people:
            fp += len(people)
            continue
        cost = np.array([[float(np.hypot(e[1] - g["3d location"][0],
                                         e[2] - g["3d location"][1]))
                          for g in gt] for e in people])
        rows, cols = linear_sum_assignment(cost)
        used = set()
        for i, j in zip(rows, cols):
            if cost[i, j] <= gate_m:
                errs.append(cost[i, j])
                matched += 1
                used.add(i)
                id_map.setdefault(gt[j]["object id"], set()).add(people[i][0])
        fp += len(people) - len(used)

    errs = np.asarray(errs)
    frag = [len(v) for v in id_map.values()]
    return {
        "gt_person_boxes": gt_total,
        "estimated_person_boxes": est_total,
        "matched": matched,
        "recall": round(matched / gt_total, 4) if gt_total else None,
        "precision": round(matched / est_total, 4) if est_total else None,
        "false_positives": fp,
        "localisation_error_m": {
            "median": round(float(np.median(errs)), 3) if len(errs) else None,
            "mean": round(float(errs.mean()), 3) if len(errs) else None,
            "p95": round(float(np.percentile(errs, 95)), 3) if len(errs) else None,
        },
        "count_error_per_frame": {
            "mean": round(float(np.mean(count_err)), 3),
            "abs_mean": round(float(np.mean(np.abs(count_err))), 3),
            "frames_exact": int(np.sum(np.asarray(count_err) == 0)),
            "frames": len(count_err),
        },
        "gt_objects_seen": len(id_map),
        "global_ids_per_gt_object": frag,
        "id_fragmentation": round(float(np.mean(frag)), 2) if frag else None,
        "gate_m": gate_m,
    }


def proximity(per_frame: dict[int, list[tuple[int, float, float, str]]],
              fps: float) -> dict:
    """Closest a person came to a humanoid robot, frame by frame.

    A warehouse's own reason to want this: the robots move, the people move, and
    the interesting number is not where either was but how close they got.
    """
    mins, breaches = [], 0
    for frame, ests in sorted(per_frame.items()):
        ppl = [(e[1], e[2]) for e in ests if e[3] == "person"]
        bots = [(e[1], e[2]) for e in ests if e[3] != "person"]
        if not ppl or not bots:
            continue
        d = min(float(np.hypot(p[0] - b[0], p[1] - b[1])) for p in ppl for b in bots)
        mins.append(d)
        if d < 1.5:
            breaches += 1
    if not mins:
        return {"frames_with_both": 0}
    return {
        "frames_with_both": len(mins),
        "nearest_approach_m": round(float(np.min(mins)), 2),
        "median_separation_m": round(float(np.median(mins)), 2),
        "seconds_within_1m5": round(breaches / fps, 1),
    }
