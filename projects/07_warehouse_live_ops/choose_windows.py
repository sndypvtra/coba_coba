#!/usr/bin/env python3
"""Pick the 30 seconds and the cameras each video shows, from the data.

Only cameras that passed `geometry_check.py` are candidates: a camera whose
calibration puts people a metre away from where they stand would make the plan
lie, and it is not shown or used.

Synthetic scene - chosen from the labels, before any model runs:

  video 1   the whole floor. The window with the most going on: people walking,
            forklifts moving, and people close to moving forklifts. Then the four
            cameras that see most of that window's people and forklifts, kept
            apart so their fields of view are distinct on the plan.
  video 2   one camera. The passing camera that sees the most people, over its
            own busiest 30 seconds.

The real scene has no labels; its window is chosen by `detect.py --survey`.

    python choose_windows.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import WINDOW_S, STRIDE, output_dir  # noqa: E402
from scene import KINDS, Labels, load_cameras  # noqa: E402

SCENE = "warehouse_000"
FPS = 30
MIN_BOX_PX = 40          # a person this tall or more counts as visible in a camera
NEAR_M = 1.5             # a person this close to a moving forklift's body
MOVING_MS = 0.3


def speeds(labels: Labels, kind: str) -> dict[int, np.ndarray]:
    """Per object: speed in m/s at every frame, from +-0.3 s of travel."""
    rows = labels.objs[labels.kind == KINDS.index(kind)]
    out = {}
    for oid in np.unique(rows[:, 2]).astype(int):
        r = rows[rows[:, 2] == oid]
        xy = np.full((labels.n_frames, 2), np.nan)
        xy[r[:, 0].astype(int)] = r[:, 3:5]
        s = np.full(labels.n_frames, np.nan)
        s[9:-9] = np.linalg.norm(xy[18:] - xy[:-18], axis=1) / 0.6
        out[oid] = s
    return out


def near_misses(labels: Labels, moving: dict[int, np.ndarray]) -> np.ndarray:
    """Frames (sampled every 6) in which a person is within NEAR_M of a moving forklift."""
    hits = np.zeros(labels.n_frames, int)
    for f in range(0, labels.n_frames, 6):
        rows = labels.at(f)
        people = rows[rows[:, 1] == KINDS.index("Person")]
        lifts = rows[rows[:, 1] == KINDS.index("Forklift")]
        for L in lifts:
            s = moving.get(int(L[2]))
            if s is None or not s[f] > MOVING_MS:
                continue
            c, si = math.cos(-L[9]), math.sin(-L[9])
            lx = c * (people[:, 3] - L[3]) - si * (people[:, 4] - L[4])
            ly = si * (people[:, 3] - L[3]) + c * (people[:, 4] - L[4])
            d = np.hypot(np.maximum(np.abs(lx) - L[6] / 2, 0), np.maximum(np.abs(ly) - L[7] / 2, 0))
            hits[f] += int((d < NEAR_M).sum())
    return hits


def main() -> int:
    geo = json.loads((output_dir(SCENE) / "geometry.json").read_text())
    passing = sorted(c for c, v in geo["cameras"].items() if v["passed"])
    cams = load_cameras(SCENE)
    labels = Labels(SCENE, list(cams))
    n, win = labels.n_frames, int(WINDOW_S * FPS)

    # who each camera sees, frame by frame
    vis_people, vis_lifts = {}, {}
    for cid in passing:
        b = labels.boxes_in(cid)
        tall = (b[:, 10] - b[:, 8]) >= MIN_BOX_PX
        for kind, store in (("Person", vis_people), ("Forklift", vis_lifts)):
            sel = b[tall & (b[:, 1] == KINDS.index(kind))]
            store[cid] = np.bincount(sel[:, 0].astype(int), minlength=n)[:n]

    lift_speed = speeds(labels, "Forklift")
    people_speed = speeds(labels, "Person")
    lifts_moving = np.nansum([s > MOVING_MS for s in lift_speed.values()], axis=0)
    people_walking = np.nansum([s > MOVING_MS for s in people_speed.values()], axis=0)
    close = near_misses(labels, lift_speed)

    def window_sum(a):
        c = np.concatenate([[0], np.cumsum(a)])
        return c[win:] - c[:-win]

    starts = np.arange(0, n - win + 1, FPS)
    seen_all = sum(vis_people.values())
    score = (window_sum(close)[starts] / max(window_sum(close).max(), 1)
             + window_sum(lifts_moving)[starts] / max(window_sum(lifts_moving).max(), 1)
             + window_sum(people_walking)[starts] / max(window_sum(people_walking).max(), 1)
             + window_sum(seen_all)[starts] / max(window_sum(seen_all).max(), 1))
    s1 = int(starts[int(np.argmax(score))])
    sl = slice(s1, s1 + win)

    # four cameras for video 1: most people and forklifts in this window, kept apart
    rank = sorted(passing, key=lambda c: -(vis_people[c][sl].mean() + 4 * vis_lifts[c][sl].mean()))
    chosen = []
    for c in rank:
        cc = cams[c]
        apart = all(np.hypot(*(cc.centre[:2] - cams[o].centre[:2])) > 10
                    or abs(math.degrees((cc.heading - cams[o].heading + math.pi) % (2 * math.pi) - math.pi)) > 45
                    for o in chosen)
        if apart:
            chosen.append(c)
        if len(chosen) == 4:
            break

    # video 2: the camera that sees the most people, over its own busiest window
    best = max(passing, key=lambda c: vis_people[c].mean())
    s2 = int(starts[int(np.argmax(window_sum(vis_people[best])[starts]))])

    def describe(start, cams_on):
        s = slice(start, start + win)
        return {
            "start_frame": start, "end_frame": start + win, "stride": STRIDE,
            "start_s": round(start / FPS, 1), "end_s": round((start + win) / FPS, 1),
            "people_on_floor": [int(x) for x in (np.bincount(labels.frame[labels.kind == 0], minlength=n)[s].min(),
                                                np.bincount(labels.frame[labels.kind == 0], minlength=n)[s].max())],
            "people_walking_mean": round(float(people_walking[s].mean()), 1),
            "forklifts_moving_mean": round(float(lifts_moving[s].mean()), 2),
            "people_near_moving_forklift_samples": int(close[s].sum()),
            "cameras": {c: {"people_visible_mean": round(float(vis_people[c][s].mean()), 1),
                            "people_visible_max": int(vis_people[c][s].max()),
                            "forklifts_visible_mean": round(float(vis_lifts[c][s].mean()), 2)}
                        for c in cams_on},
        }

    sel = {
        "candidates": passing,
        "rejected_by_geometry": sorted(c for c, v in geo["cameras"].items() if not v["passed"]),
        "video1_live_ops": {**describe(s1, chosen), "shown": chosen,
                            "why": "busiest 30 s by walking, moving forklifts, people near "
                                   "moving forklifts and people in view; four cameras that "
                                   "see most of it, at least 10 m or 45 degrees apart"},
        "video2_one_camera": {**describe(s2, [best]), "camera": best,
                              "why": "the passing camera with the most people in view, "
                                     "over its own busiest 30 s"},
        "window_s": WINDOW_S,
        "busiest_cameras_whole_recording": sorted(
            ({"camera": c, "people_visible_mean": round(float(vis_people[c].mean()), 1),
              "forklifts_visible_mean": round(float(vis_lifts[c].mean()), 2)} for c in passing),
            key=lambda r: -r["people_visible_mean"]),
    }
    (output_dir(SCENE) / "selection.json").write_text(json.dumps(sel, indent=1))
    print(json.dumps({k: v for k, v in sel.items() if k != "busiest_cameras_whole_recording"}, indent=1))
    print("busiest:", [(r["camera"], r["people_visible_mean"], r["forklifts_visible_mean"])
                       for r in sel["busiest_cameras_whole_recording"][:8]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
