"""How right the floor is: the pipeline scored against the dataset's labels.

Only the synthetic recording has labels, so only it is scored. The pipeline
never reads them; this module compares afterwards.

  people on the plan   each analysed frame, the plan's people are matched to
                       the labelled people within 1 m. Recall is reported two
                       ways - against everyone on the floor, and against those
                       a camera in use could actually see (a labelled box at
                       least 40 px tall in one of them) - because nobody can be
                       placed who is not in any picture.
  identity             how many plan identities each labelled person got, and
                       how many labelled people each plan identity covered.
  vehicles             the same for forklifts and pallet trucks, within 2 m.
  #1 per camera        people counted in a camera's own picture against the
                       labelled boxes there, both at least 40 px tall.
  #17 per angle        detection recall and precision per camera, grouped by
                       mounting height and tilt.
  #16 fewest cameras   cameras removed one at a time, least useful first, with
                       the plan's recall after each removal.
  #15 coverage         how much of the building's floor each number of cameras
                       images finely enough to place someone (0.25 m/px).
  agreement            how far apart two cameras place the same person; the
                       only accuracy measure the unlabelled real recording has.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment

from scene import KINDS, Camera, FloorPlan, Labels, building_mask
from world import Blob, Result, Track, stitch, track

GATE = {"person": 1.0, "forklift": 2.0, "pallet_truck": 2.0}
LABEL = {"person": "Person", "forklift": "Forklift", "pallet_truck": "PalletTruck"}


def _match(a: np.ndarray, b: np.ndarray, gate: float):
    """Optimal pairs between two point sets within a gate: (i, j, distance)."""
    if not len(a) or not len(b):
        return []
    d = np.linalg.norm(a[:, None] - b[None], axis=2)
    c = np.where(d <= gate, d, 1e6)
    r, k = linear_sum_assignment(c)
    return [(i, j, float(d[i, j])) for i, j in zip(r, k) if c[i, j] < 1e6]


def seeable(labels: Labels, frame: int, cams: list[str], kind: str, min_px: float = 40.0) -> set[int]:
    """Labelled object ids that at least one of these cameras pictures usefully."""
    rows = labels.boxes[(labels.objs[labels.boxes[:, 0].astype(int), 0] == frame)]
    ok = set()
    ci = {labels.cam_ids.index(c) for c in cams if c in labels.cam_ids}
    k = KINDS.index(kind)
    for r in rows:
        o = labels.objs[int(r[0])]
        if int(o[1]) == k and int(r[1]) in ci and (r[5] - r[3]) >= min_px:
            ok.add(int(o[2]))
    return ok


def plan_accuracy(res: Result, labels: Labels, cams: list[str], cls: str = "person") -> dict:
    kind = LABEL[cls]
    tp = n_ai = n_gt = n_see = tp_see = 0
    errors, count_err = [], []
    gid_of = defaultdict(list)          # label id -> plan ids it was matched to, in order
    lab_of = defaultdict(set)           # plan id -> label ids
    for f in res.frames:
        ai = [(g, x, y) for g, c, x, y in res.positions(f) if c == cls]
        gt = labels.at(f, kind)
        see = seeable(labels, f, cams, kind)
        A = np.array([[x, y] for _, x, y in ai]).reshape(-1, 2)
        G = gt[:, 3:5]
        pairs = _match(A, G, GATE[cls])
        n_ai += len(ai)
        n_gt += len(gt)
        n_see += len(see)
        tp += len(pairs)
        for i, j, d in pairs:
            lid = int(gt[j, 2])
            errors.append(d)
            gid_of[lid].append(ai[i][0])
            lab_of[ai[i][0]].add(lid)
            tp_see += lid in see
        count_err.append(len(ai) - len(see))
    frag = [len(set(v)) for v in gid_of.values()]
    switches = sum(sum(1 for a, b in zip(v, v[1:]) if a != b) for v in gid_of.values())
    return {
        "frames": len(res.frames),
        "precision": round(tp / max(n_ai, 1), 3),
        "recall_all_on_floor": round(tp / max(n_gt, 1), 3),
        "recall_seeable": round(tp_see / max(n_see, 1), 3),
        "position_error_m_median": round(float(np.median(errors)), 3) if errors else None,
        "position_error_m_p90": round(float(np.percentile(errors, 90)), 3) if errors else None,
        "count_vs_seeable_mean": round(float(np.mean(count_err)), 2) if count_err else None,
        "count_vs_seeable_abs_mean": round(float(np.mean(np.abs(count_err))), 2) if count_err else None,
        "plan_ids_per_label_mean": round(float(np.mean(frag)), 2) if frag else None,
        "id_switches": switches,
        "labels_per_plan_id_mean": round(float(np.mean([len(v) for v in lab_of.values()])), 2)
        if lab_of else None,
        "label_people_matched": len(gid_of),
    }


def forklift_motion(afr: list, labels: Labels, gate_m: float = 3.0) -> dict:
    """Is each forklift on the plan moving, as the dashboard says, against the labels?

    Every forklift on the plan counts (the "forklifts moving" card and the
    utilisation use them all). A plan forklift is matched to the nearest
    labelled forklift within `gate_m`; the label's speed is its displacement
    over one second centred on the frame.
    """
    import config as C
    kind = LABEL["forklift"]
    tp = fp = fn = tn = 0
    for fr in afr:
        now, a, b = labels.at(fr.frame, kind), labels.at(fr.frame - 15, kind), labels.at(fr.frame + 15, kind)
        for o in fr.objects:
            if o.cls != "forklift" or not len(now):
                continue
            d = np.hypot(now[:, 3] - o.x, now[:, 4] - o.y)
            if d.min() > gate_m:
                continue
            i = now[int(np.argmin(d)), 2]
            ra, rb = a[a[:, 2] == i], b[b[:, 2] == i]
            if not len(ra) or not len(rb):
                continue
            truth = np.hypot(rb[0, 3] - ra[0, 3], rb[0, 4] - ra[0, 4]) > C.VEHICLE_MOVING_MS
            said = o.speed > C.VEHICLE_MOVING_MS
            tp += said and truth
            fp += said and not truth
            fn += truth and not said
            tn += not said and not truth
    n = int(tp + fp + fn + tn)
    return {"sightings": n, "moving_right": round(float(tp + tn) / max(n, 1), 3),
            "utilisation_ai": round(float(tp + fp) / max(n, 1), 3),
            "utilisation_truth": round(float(tp + fn) / max(n, 1), 3)}


def camera_counts(detections: dict, labels: Labels, frames: list[int], min_px: float = 40.0) -> dict:
    """#1 - people in a camera's own picture: AI count against labelled boxes."""
    out = {}
    for cid, (rows, classes) in detections.items():
        k = classes.index("person")
        lab = labels.boxes_in(cid, frames=np.array(frames), kind="Person")
        lab = lab[(lab[:, 10] - lab[:, 8]) >= min_px]
        err = []
        for f in frames:
            r = rows[(rows[:, 0] == f) & (rows[:, 7] == k) & (rows[:, 1] >= 0)]
            ai = int(((r[:, 5] - r[:, 3]) >= min_px).sum())
            gt = int((lab[:, 0] == f).sum())
            err.append((ai, gt))
        e = np.array(err)
        diff = e[:, 0] - e[:, 1]
        out[cid] = {"ai_mean": round(float(e[:, 0].mean()), 2), "label_mean": round(float(e[:, 1].mean()), 2),
                    "abs_error_mean": round(float(np.abs(diff).mean()), 2),
                    "bias": round(float(diff.mean()), 2),
                    "within_1_pct": round(100.0 * float(np.mean(np.abs(diff) <= 1)), 1)}
    return out


def _iou_match(det: np.ndarray, gt: np.ndarray, thr: float = 0.4) -> int:
    if not len(det) or not len(gt):
        return 0
    x1 = np.maximum(det[:, None, 0], gt[None, :, 0])
    y1 = np.maximum(det[:, None, 1], gt[None, :, 1])
    x2 = np.minimum(det[:, None, 2], gt[None, :, 2])
    y2 = np.minimum(det[:, None, 3], gt[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    a = (det[:, 2] - det[:, 0]) * (det[:, 3] - det[:, 1])
    b = (gt[:, 2] - gt[:, 0]) * (gt[:, 3] - gt[:, 1])
    iou = inter / (a[:, None] + b[None, :] - inter + 1e-9)
    c = np.where(iou >= thr, 1 - iou, 1e6)
    r, k = linear_sum_assignment(c)
    return int(sum(c[i, j] < 1e6 for i, j in zip(r, k)))


def per_camera_detection(detections: dict, labels: Labels, frames: list[int], cams: dict[str, Camera]) -> dict:
    """#17 - detection recall and precision in each camera's own picture, people only."""
    out = {}
    for cid, (rows, classes) in detections.items():
        k = classes.index("person")
        tp = nd = ng = 0
        lab = labels.boxes_in(cid, frames=np.array(frames), kind="Person")
        lab = lab[(lab[:, 10] - lab[:, 8]) >= 20]
        for f in frames[::3]:
            d = rows[(rows[:, 0] == f) & (rows[:, 7] == k)][:, 2:6]
            g = lab[lab[:, 0] == f][:, 7:11]
            tp += _iou_match(d, g)
            nd += len(d)
            ng += len(g)
        c = cams[cid]
        out[cid] = {"recall": round(tp / max(ng, 1), 3), "precision": round(tp / max(nd, 1), 3),
                    "labels": ng, "mount_height_m": round(c.mount_height_m, 1),
                    "tilt_deg": round(c.tilt_deg, 1), "group": angle_group(c)}
    groups = defaultdict(list)
    for v in out.values():
        groups[v["group"]].append(v)
    summary = {g: {"cameras": len(v),
                   "recall_mean": round(float(np.mean([x["recall"] for x in v])), 3),
                   "precision_mean": round(float(np.mean([x["precision"] for x in v])), 3)}
               for g, v in sorted(groups.items())}
    return {"cameras": out, "groups": summary}


def angle_group(c: Camera) -> str:
    h, t = c.mount_height_m, c.tilt_deg
    if h < 2.5:
        return "setinggi mata (<2,5 m)"
    if h < 5.0:
        return "plafon rendah, mendatar (2,5-5 m, <15°)" if t < 15 else "plafon rendah, menunduk (2,5-5 m, ≥15°)"
    return "plafon tinggi, landai (≥5 m, <35°)" if t < 35 else "plafon tinggi, curam (≥5 m, ≥35°)"


def fewest_cameras(frames: list[int], by_frame, labels: Labels, cams: list[str], step: int = 2) -> list[dict]:
    """#16 - greedy removal: at each step drop the camera whose loss costs least recall."""
    sub = frames[::step]

    def recall(keep: set[str]) -> float:
        r = track(sub, by_frame, only=keep)
        stitch(r, stride=sub[1] - sub[0])
        tp = n = 0
        for f in sub:
            ai = np.array([[x, y] for g, c, x, y in r.positions(f) if c == "person"]).reshape(-1, 2)
            gt = labels.at(f, "Person")[:, 3:5]
            tp += len(_match(ai, gt, GATE["person"]))
            n += len(gt)
        return tp / max(n, 1)

    keep = set(cams)
    curve = [{"cameras": len(keep), "recall_all_on_floor": round(recall(keep), 3), "removed": None}]
    while len(keep) > 1:
        best = max(keep, key=lambda c: recall(keep - {c}))
        keep = keep - {best}
        curve.append({"cameras": len(keep), "recall_all_on_floor": round(recall(keep), 3), "removed": best})
    return curve


def coverage(cams: dict[str, Camera], plan: FloorPlan, max_scale: float = 0.25, step_m: float = 0.5) -> dict:
    """#15 - share of the building's floor where 0, 1, 2+ of these cameras can place a person.

    `max_scale` is the same 0.25 m per pixel the pipeline places people out to,
    so this is the floor the plan can show at all.
    """
    inside = building_mask(plan)
    ys, xs = np.nonzero(inside)
    wx, wy = plan.to_world(xs[::int(max(1, step_m * plan.px_per_m))], ys[::int(max(1, step_m * plan.px_per_m))])
    n = np.zeros(len(wx), int)
    for c in cams.values():
        n += c.sees(np.asarray(wx), np.asarray(wy), max_scale).astype(int)
    return {"floor_points": int(len(n)),
            "seen_by_0_pct": round(100.0 * float(np.mean(n == 0)), 1),
            "seen_by_1_pct": round(100.0 * float(np.mean(n == 1)), 1),
            "seen_by_2plus_pct": round(100.0 * float(np.mean(n >= 2)), 1),
            "rule": f"floor imaged at {max_scale} m per pixel or finer; racks hiding the floor are not modelled"}


def label_heights(res: Result) -> dict:
    """Median measured height of people - a check that the scene is in metres."""
    h = [t.height for g, t in res.tracks.items() if t.cls == "person" and t.confirmed and math.isfinite(t.height)]
    return {"people": len(h), "median_m": round(float(np.median(h)), 2) if h else None}


def camera_agreement(sightings: dict, cams: dict[str, Camera], gate_m: float = 3.0,
                     place_scale: float = 0.25) -> dict:
    """How far apart two cameras independently place the same person - no labels needed.

    `sightings`: frame -> every lifted sighting (world.Result.sightings). For
    every pair of cameras and every analysed frame, the people each camera
    placed on floor that *both* can place people on are paired up (optimal
    matching, within `gate_m`), and the distance between the two placements is
    recorded. The gate is three times the fusion distance on purpose: measured
    on the fused objects instead, the answer could never exceed the 0.9 m the
    fusion itself allows. A camera whose calibration is off disagrees with every
    partner; a good pair agrees to a few decimetres. On the synthetic recording,
    where the truth is known, the same measure shows what "a few" is.
    """
    pairs = defaultdict(list)
    ids = sorted(cams)
    for f, sights in sightings.items():
        by_cam = defaultdict(list)
        for s in sights:
            if s.cls == "person":
                by_cam[s.cam].append((s.x, s.y))
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if not by_cam.get(a) or not by_cam.get(b):
                    continue
                A, B = np.array(by_cam[a]), np.array(by_cam[b])
                A = A[cams[b].sees(A[:, 0], A[:, 1], place_scale)]
                B = B[cams[a].sees(B[:, 0], B[:, 1], place_scale)]
                for _, _, d in _match(A, B, gate_m):
                    pairs[(a, b)].append(d)
    per_pair = {f"{a} + {b}": {"samples": len(v), "median_m": round(float(np.median(v)), 3),
                               "within_0_5_m_pct": round(100.0 * float(np.mean(np.array(v) <= 0.5)), 1)}
                for (a, b), v in sorted(pairs.items()) if len(v) >= 20}
    per_cam = defaultdict(list)
    for (a, b), v in pairs.items():
        if len(v) >= 20:
            per_cam[a].append(float(np.median(v)))
            per_cam[b].append(float(np.median(v)))
    every = [d for v in pairs.values() if len(v) >= 20 for d in v]
    return {"rule": f"same instant, floor both cameras place people on (≤ {place_scale} m/px), "
                    f"optimal pairs within {gate_m} m",
            "all_pairs": {"samples": len(every),
                          "median_m": round(float(np.median(every)), 3) if every else None,
                          "within_0_5_m_pct": round(100.0 * float(np.mean(np.array(every) <= 0.5)), 1)
                          if every else None},
            "pairs": per_pair,
            "cameras": {c: {"partners": len(v), "median_disagreement_m": round(float(np.median(v)), 3)}
                        for c, v in sorted(per_cam.items())}}


# ------------------------------------------------------- analytics vs truth
CLS_OF_KIND = {"Person": "person", "Forklift": "forklift", "PalletTruck": "pallet_truck"}


def truth_result(labels: Labels, frames: list[int], cams: list[str] | None = None,
                 min_px: float = 40.0) -> Result:
    """The labels dressed as a pipeline result, so the same analytics code runs on them.

    With `cams`, an object is kept only in the frames where one of those cameras
    shows it at least `min_px` tall: what a perfect detector and tracker could
    deliver from these cameras. Without, everyone on the floor: what happened.
    """
    tracks: dict[int, Track] = {}
    blobs: dict[int, list[Blob]] = {}
    ci = {labels.cam_ids.index(c) for c in cams} if cams else None
    for f in frames:
        rows = labels.at(f)
        keep = np.ones(len(rows), bool)
        if ci is not None:
            r0 = labels.rows(f).start
            lo, hi = np.searchsorted(labels.boxes[:, 0], [r0, r0 + len(rows)])
            b = labels.boxes[lo:hi]
            b = b[np.isin(b[:, 1].astype(int), list(ci)) & ((b[:, 5] - b[:, 3]) >= min_px)]
            keep = np.isin(np.arange(r0, r0 + len(rows)), b[:, 0].astype(int))
        blobs[f] = []
        for r in rows[keep]:
            cls = CLS_OF_KIND.get(KINDS[int(r[1])] if r[1] >= 0 else "")
            if cls is None:
                continue
            gid = int(r[2])
            t = tracks.setdefault(gid, Track(gid, cls))
            t.frames.append(f)
            t.xs.append(float(r[3]))
            t.ys.append(float(r[4]))
            t.ncams.append(2)
            t.scores.append(1.0)
            t.scales.append(0.01)
            blob = Blob(cls, [], float(r[3]), float(r[4]))
            blob.gid = gid
            blobs[f].append(blob)
    return Result(list(frames), blobs, tracks, Counter(), {f: [] for f in frames})


def _match_events(ai: list[dict], truth: list[dict], t_tol: float = 1.0, d_tol: float = 3.0) -> dict:
    """Events agree when they overlap in time (within t_tol s) and lie within d_tol m."""
    def span(e):
        a = e.get("start_t", e.get("t", 0.0))
        return a - t_tol, max(e.get("end_t", a), e.get("t", a)) + t_tol
    used, hit = set(), 0
    for e in ai:
        a0, a1 = span(e)
        for j, g in enumerate(truth):
            if j in used:
                continue
            b0, b1 = span(g)
            if a0 <= b1 and b0 <= a1 and math.hypot(e["x"] - g["x"], e["y"] - g["y"]) <= d_tol:
                used.add(j)
                hit += 1
                break
    return {"ai": len(ai), "truth": len(truth), "matched": hit,
            "precision": round(hit / len(ai), 2) if ai else None,
            "recall": round(hit / len(truth), 2) if truth else None}


def _match_crossings(ai: list[dict], truth: list[dict], t_tol: float = 0.5) -> dict:
    """A crossing agrees with a true one on the same line, in the same direction, within t_tol s."""
    used, hit = set(), 0
    for e in ai:
        for j, g in enumerate(truth):
            if j not in used and e["line"] == g["line"] and e["dir"] == g["dir"] and abs(e["t"] - g["t"]) <= t_tol:
                used.add(j)
                hit += 1
                break
    return {"ai": len(ai), "truth": len(truth), "matched": hit,
            "precision": round(hit / len(ai), 2) if ai else None,
            "recall": round(hit / len(truth), 2) if truth else None}


def analytics_vs_truth(ai: dict, seen: dict, everyone: dict) -> dict:
    """The video's numbers next to the same numbers computed from the labels.

    `seen`: labels restricted to what the cameras in use show (a perfect
    pipeline's ceiling); `everyone`: every labelled object on the floor.
    """
    def row(name, f):
        return {"analytic": name, "ai": f(ai), "truth_seen_by_cameras": f(seen), "truth_whole_floor": f(everyone)}

    out = [row("#2 orang di lantai, rata-rata", lambda s: s["#2_headcount"]["mean"]),
           row("#2 orang di lantai, maks", lambda s: s["#2_headcount"]["max"])]
    for i, ln in enumerate(ai["#3_lines"]):
        out.append(row(f"#3 {ln['line'].split(' ·')[0]}: masuk + keluar",
                       lambda s, i=i: s["#3_lines"][i]["in"] + s["#3_lines"][i]["out"]))
    for i, z in enumerate(ai["#4_zones"]):
        out.append(row(f"#4 {z['zone']}: okupansi rata-rata",
                       lambda s, i=i: s["#4_zones"][i]["occupancy_mean"]))
    out += [row("#6 waktu berjalan (%)", lambda s: s["#6_walking"]["walking_share_pct"]),
            row("#7 frame dengan kerumunan (%)", lambda s: s["#7_congestion"]["frames_with_a_crowd_pct"]),
            row("#8 kejadian diam lama", lambda s: len(s["#8_idle"]["events"])),
            row("#10 kejadian forklift ngebut", lambda s: len(s["#10_speeding"]["events"])),
            row("#11 kejadian nyaris tertabrak", lambda s: len(s["#11_near_miss"]["events"])),
            row("#12 orang masuk jalur forklift", lambda s: s["#12_vehicle_lane"]["entries"])]
    events = {}
    for key, name in (("#11_near_miss", "near_miss"), ("#10_speeding", "speeding"), ("#8_idle", "idle")):
        events[name] = {"vs_truth_seen": _match_events(ai[key]["events"], seen[key]["events"]),
                        "vs_truth_whole_floor": _match_events(ai[key]["events"], everyone[key]["events"])}
    events["lane"] = {"vs_truth_seen": _match_events(ai["#12_vehicle_lane"]["events"],
                                                     seen["#12_vehicle_lane"]["events"], 1.0, 2.0)}
    events["crossing"] = {"vs_truth_seen": _match_crossings(ai["#3_crossings"], seen["#3_crossings"])}
    return {"rows": out, "events": events,
            "note": "truth_seen_by_cameras = the labels kept only while a camera in use shows the object "
                    "at least 40 px tall; truth_whole_floor = every labelled object. Both run through the "
                    "same analytics code as the AI."}


def detector_quality(detections: dict, labels: Labels, frames: list[int], min_px: float = 20.0,
                     every: int = 3) -> dict:
    """Box recall and precision per class, all cameras pooled, IoU 0.4, labels >= min_px tall."""
    out = {}
    for cls, kind in (("person", "Person"), ("forklift", "Forklift"), ("pallet_truck", "PalletTruck")):
        tp = nd = ng = 0
        for cid, (rows, classes) in detections.items():
            if cls not in classes:
                continue
            k = classes.index(cls)
            lab = labels.boxes_in(cid, frames=np.array(frames[::every]), kind=kind)
            lab = lab[(lab[:, 10] - lab[:, 8]) >= min_px]
            for f in frames[::every]:
                d = rows[(rows[:, 0] == f) & (rows[:, 7] == k)][:, 2:6]
                g = lab[lab[:, 0] == f][:, 7:11]
                tp += _iou_match(d, g)
                nd += len(d)
                ng += len(g)
        out[cls] = {"recall": round(tp / max(ng, 1), 3), "precision": round(tp / max(nd, 1), 3), "labels": ng}
    return out
