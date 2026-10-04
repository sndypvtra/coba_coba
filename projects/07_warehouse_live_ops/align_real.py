#!/usr/bin/env python3
"""Real recording: check every camera against the others, and correct what can be.

The real warehouse has no ground truth, so a camera cannot be checked against
where people really are - only against where the *other* cameras put them. A
person two cameras see at the same instant must land in one place. Measured on
the shipped calibration, they do not: some pairs agree to 0.2 m, others are a
metre apart, and the disagreement of a pair is mostly a constant shift.

So each camera gets one correction, a shift across the floor, solved for all
cameras at once from the people they see together (least squares on every
pair's median offset, one camera held fixed). A camera that still disagrees
with its partners after its shift - its error is a turn or a tilt, not a shift
- is not used, the same rule the synthetic recording's cameras are held to. A
camera that never sees a person another camera also sees cannot be checked,
and is not used either.

The shifts are fitted on the seconds the video does *not* show (one frame a
second), and the result is checked on the video's own 30 seconds: the numbers
in the README are out of sample.

    python align_real.py        # after detect.py --survey / --scene warehouse_027
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import world as wd  # noqa: E402
from config import STRIDE, output_dir  # noqa: E402
from evaluate import camera_agreement, _match  # noqa: E402
from scene import load_cameras, video_path  # noqa: E402

SCENE = "warehouse_027"
GATE_M = 3.0             # two placements this close at one instant may be one person
PLACE_SCALE = 0.25       # only floor both cameras place people on (world.CLASS["person"])
MIN_MATCHES = 30         # fewer shared sightings than this and a pair says nothing
AGREE_M = 0.35           # after its shift, a camera must agree with its partners this well


def fit_frames(n_frames: int, start: int, end: int, every: int = 30) -> list[int]:
    """One frame a second, outside the video's window."""
    return [f for f in range(0, n_frames, every) if not start <= f < end]


def detect_people(cams: list[str], frames: list[int]) -> dict[str, np.ndarray]:
    """Person boxes in the fitting frames: frame, x1, y1, x2, y2, score. Cached."""
    from detect import drop_contained, keep_by_class, load_runtime, predict, PROMPTS
    out, model = {}, None
    classes = list(PROMPTS[SCENE])
    for cid in cams:
        path = output_dir(SCENE) / "detections" / f"{cid}_align_1fps.npy"
        if path.exists():
            out[cid] = np.load(path)
            continue
        model = model or load_runtime(SCENE)
        cap = cv2.VideoCapture(str(video_path(SCENE, cid)))
        rows = []
        for f in frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, img = cap.read()
            if not ok:
                continue
            det = drop_contained(keep_by_class(predict(model, img, 1280, 0.15), classes))
            for d in det[det[:, 5] == classes.index("person")]:
                rows.append((f, *d[:5]))
        cap.release()
        out[cid] = np.array(rows, np.float32).reshape(-1, 6)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, out[cid])
        print(f"  {cid}: {len(out[cid])} people in {len(frames)} frames", flush=True)
    return out


def lifted(cams: dict, boxes: dict[str, np.ndarray]) -> dict[int, list[wd.Sighting]]:
    by_frame = defaultdict(list)
    for cid, rows in boxes.items():
        for r in rows:
            s = wd.lift(cams[cid], "person", int(r[0]), -1, float(r[5]), r[1:5])
            if not s.reject:
                by_frame[int(r[0])].append(s)
    return dict(by_frame)


def pair_offsets(cams: dict, sightings: dict[int, list[wd.Sighting]]) -> dict[tuple, np.ndarray]:
    """For every camera pair, (b - a) placement differences of the people both saw."""
    out = defaultdict(list)
    ids = sorted(cams)
    for f, ss in sightings.items():
        by = defaultdict(list)
        for s in ss:
            by[s.cam].append((s.x, s.y))
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if not by.get(a) or not by.get(b):
                    continue
                A, B = np.array(by[a]), np.array(by[b])
                A = A[cams[b].sees(A[:, 0], A[:, 1], PLACE_SCALE)]
                B = B[cams[a].sees(B[:, 0], B[:, 1], PLACE_SCALE)]
                for i2, j2, _ in _match(A, B, GATE_M):
                    out[(a, b)].append(B[j2] - A[i2])
    return {k: np.array(v) for k, v in out.items() if len(v) >= MIN_MATCHES}


def solve(offsets: dict[tuple, np.ndarray], cams: list[str], ref: str) -> dict[str, np.ndarray]:
    """Shifts t_c with (p_b + t_b) = (p_a + t_a) for every pair, t_ref = 0, weighted by evidence."""
    idx = {c: i for i, c in enumerate(cams)}
    A, B = [], []
    for (a, b), d in offsets.items():
        if a not in idx or b not in idx:
            continue
        w = np.sqrt(len(d))
        r = np.zeros(len(cams))
        r[idx[b]], r[idx[a]] = w, -w
        A.append(r)
        B.append(-np.median(d, 0) * w)
    r = np.zeros(len(cams))
    r[idx[ref]] = 1e3
    A.append(r)
    B.append(np.zeros(2))
    t, *_ = np.linalg.lstsq(np.array(A), np.array(B), rcond=None)
    return {c: t[i] for c, i in idx.items()}


def disagreement(offsets: dict, shifts: dict, c: str) -> float | None:
    """Median, over a camera's partners, of the pair's median distance after the shifts."""
    meds = []
    for (a, b), d in offsets.items():
        if c in (a, b) and a in shifts and b in shifts:
            meds.append(float(np.median(np.linalg.norm(d + shifts[b] - shifts[a], axis=1))))
    return float(np.median(meds)) if meds else None


def align() -> dict:
    raw = load_cameras(SCENE, aligned=False)
    sel = json.loads((output_dir(SCENE) / "selection.json").read_text())["video3_real"]
    n = int(cv2.VideoCapture(str(video_path(SCENE, sorted(raw)[0]))).get(cv2.CAP_PROP_FRAME_COUNT))
    frames = fit_frames(n, sel["start_frame"], sel["end_frame"])
    t0 = time.time()
    boxes = detect_people(sorted(raw), frames)
    offsets = pair_offsets(raw, lifted(raw, boxes))
    seen_with_others = {c for k in offsets for c in k}
    keep = sorted(seen_with_others)
    rejected = {c: "in the seconds used for fitting it never sees a person another camera also sees: "
                   "cannot be checked" for c in sorted(raw) if c not in seen_with_others}
    rejected_at: dict[str, float] = {}
    while True:
        ref = max(keep, key=lambda c: sum(len(d) for k, d in offsets.items() if c in k))
        shifts = solve({k: d for k, d in offsets.items() if k[0] in keep and k[1] in keep}, keep, ref)
        dis = {c: disagreement({k: d for k, d in offsets.items() if k[0] in keep and k[1] in keep}, shifts, c)
               for c in keep}
        worst = max(keep, key=lambda c: dis[c] if dis[c] is not None else 1e9)
        if dis[worst] is not None and dis[worst] <= AGREE_M or len(keep) <= 2:
            break
        rejected[worst] = (f"still {dis[worst]:.2f} m from its partners after its best shift: "
                           f"the error is a turn or tilt, not a shift")
        rejected_at[worst] = dis[worst]
        keep.remove(worst)
    # the cameras rejected along the way get the shift that fits them best, for the record
    for c in rejected:
        ds = [(d if b == c else -d) + (shifts[a] if b == c else shifts[b]) for (a, b), d in offsets.items()
              if c in (a, b) and (a if b == c else b) in shifts]
        shifts.setdefault(c, np.median(np.concatenate(ds), 0) if ds else np.zeros(2))

    # out of sample: the video's own 30 s, from the tracked detections, before and after
    from detect import load_detections
    vids = {c: load_detections(SCENE, c, sel["start_frame"], sel["end_frame"]) for c in sorted(raw)}
    vframes = list(range(sel["start_frame"], sel["end_frame"], STRIDE))

    def check(cams: dict) -> dict:
        by_frame, _ = wd.lift_all(cams, {c: vids[c] for c in cams})
        return camera_agreement({f: by_frame.get(f, []) for f in vframes}, cams)

    before = check({c: raw[c] for c in raw})
    after = check({c: raw[c].shifted(*shifts[c]) for c in keep})
    out = {
        "rule": f"shift per camera from people two cameras see at once (pairs within {GATE_M} m, both placing "
                f"people at <= {PLACE_SCALE} m/px); a camera is used if, after its shift, it agrees with its "
                f"partners to {AGREE_M} m (median)",
        "fit_frames": {"count": len(frames), "outside_window": [sel["start_frame"], sel["end_frame"]],
                       "every_s": 1.0},
        "reference": ref,
        "cameras": {c: {"shift_m": [round(float(v), 3) for v in shifts[c]],
                        "matches_with_others": int(sum(len(d) for k, d in offsets.items() if c in k)),
                        "disagreement_after_shift_m":
                            round(disagreement({k: d for k, d in offsets.items() if k[0] in keep and k[1] in keep},
                                               shifts, c), 3) if c in keep else
                            round(rejected_at[c], 3) if c in rejected_at else None,
                        "used": c in keep}
                    for c in sorted(raw)},
        "verified": keep,
        "rejected": rejected,
        "check_on_video_window": {"all_cameras_as_shipped": before["all_pairs"],
                                  "verified_cameras_shifted": after["all_pairs"],
                                  "pairs_as_shipped": before["pairs"], "pairs_shifted": after["pairs"]},
        "seconds": round(time.time() - t0, 1),
    }
    (output_dir(SCENE) / "camera_alignment.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({k: out[k] for k in ("cameras", "verified", "rejected")}, indent=1, ensure_ascii=False))
    print("video window, as shipped:", before["all_pairs"])
    print("video window, verified + shifted:", after["all_pairs"])
    return out


if __name__ == "__main__":
    align()
