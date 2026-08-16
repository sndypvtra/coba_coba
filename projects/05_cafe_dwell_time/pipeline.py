"""Occupancy and dwell time, end to end.

Three numbers come out of this:

  occupancy   how many people are in the room right now - customers *and* staff,
              because a server standing at the counter is a person present
  visitors    how many distinct customers have been seen so far - staff excluded,
              because a shift is not a visit
  dwell       for each customer, how long they have been in view; staff time is
              reported separately as service

The first is a detection problem and is the easy one. The other two are tracking
problems, and they are only as good as the identity assignment - which is why
the chain below spends four of its six steps on identity rather than on pixels:

  1. detection.observe   detect, filter by zone, track, describe        (pass 1)
  2. identity.merge      re-link tracks the tracker broke on occlusion
  3. roles.classify      staff or customer, decided once per person
  4. roles.hold          carry confirmed staff over gaps in detection
  5. render.render       replay the clip against the settled identities (pass 2)
  6. summary.build       the result, with the quality signals attached

This module is the sequence and nothing else. Every step above lives in its own
file, so a change to how staff are recognised cannot accidentally change how
they are drawn.

Run:  python main.py
      python main.py --all
"""

from __future__ import annotations

import argparse
import warnings

import numpy as np
import supervision as sv

import detection
import identity
import roles
import summary as summarise
import zones
from config import CLIPS, DwellConfig
from render import render
from factory_vision.paths import project_dirs

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)

warnings.filterwarnings("ignore")


def process(cfg: DwellConfig, args) -> dict:
    src = VIDEO_DIR / cfg.filename
    if not src.exists():
        raise SystemExit(f"missing {src} - see README.md for how the clip is built")
    info = sv.VideoInfo.from_video_path(str(src))
    w, h, fps = info.width, info.height, info.fps
    diag = float(np.hypot(w, h))
    masks = zones.masks_for(cfg.exclusion_zones, w, h)

    _announce(cfg, args, info)

    # ---- pass 1: detect, filter, track, describe ---------------------------
    obs = detection.observe(cfg, args, src, masks, w, h, fps, OUTPUT_DIR)

    # ---- re-link tracks broken by occlusion --------------------------------
    alias, merges = identity.merge_broken_tracks(obs.tracks, fps, diag)
    _report_merges(merges)
    merged = identity.collapse(obs.tracks, alias)

    # ---- decide staff or customer, once per person -------------------------
    _report_zone_shares(merged)
    customers, staff_locked = roles.classify(merged, cfg)
    _report_staff(merged, staff_locked)

    # ---- hold staff across short detection gaps ----------------------------
    hold = max([z.hold_frames for z in cfg.exclusion_zones] or [0])
    held = roles.hold_across_gaps(obs.frames, alias, staff_locked, hold)
    if held:
        print(f"    held service tracks across {held} frames of missed "
              f"detection (max gap {hold} frames)")

    # ---- pass 2: render from the recorded tracks ---------------------------
    out_path = OUTPUT_DIR / cfg.filename.replace(".mp4", "__dwell.mp4")
    timeline = render(src, out_path, obs, alias, merged, customers, staff_locked,
                      cfg, info, len(merges))

    result = summarise.build(cfg, args, obs, merged, customers, staff_locked,
                             timeline, merges, out_path, info)
    summarise.write(result, OUTPUT_DIR, cfg.filename)
    _report_done(result, obs, out_path, merges)
    return result


def _announce(cfg, args, info) -> None:
    print(f"\n>>> {cfg.filename}  {info.width}x{info.height} @ {info.fps:.3f}fps  "
          f"{info.total_frames} frames ({info.total_frames / info.fps:.1f}s)")
    print(f"    prompts={cfg.prompts} conf={cfg.conf} tracker={args.tracker} "
          f"min_track_age={cfg.min_track_age} dedup={cfg.dedup_containment}")
    for z in cfg.exclusion_zones:
        print(f"    zone '{z.name}' [{z.mode}]: {z.reason}")


def _report_merges(merges) -> None:
    if not merges:
        return
    print(f"    re-linked {len(merges)} broken tracks:")
    for b, a, gap, move, sim in merges:
        print(f"      #{b} -> #{a}   gap {gap}s  moved {move * 100:.1f}% of frame  "
              f"appearance {sim:.2f}")


def _report_zone_shares(merged) -> None:
    shares = roles.zone_shares(merged)
    if not shares:
        return
    print("    time inside a service zone, by track:")
    for share, r, t in shares:
        print(f"      #{r:<3d} {t['in_zone']:3d}/{t['frames']:3d} frames  {share:5.0%}")


def _report_staff(merged, staff_locked) -> None:
    for r in sorted(staff_locked):
        t = merged[r]
        print(f"    #{r} classified as service: {t['in_zone']}/{t['frames']} "
              f"frames inside the service zone "
              f"({t['in_zone'] / max(t['frames'], 1):.0%})")


def _report_done(result, obs, out_path, merges) -> None:
    print(f"    filtered: {obs.duplicates_dropped} duplicate boxes; "
          f"re-linked {len(merges)} tracks")
    print(f"    DONE {out_path.name}  visitors={result['visitors_total']} "
          f"occupancy mean={result['occupancy_mean']} max={result['occupancy_max']} "
          f"dwell mean={result['dwell_mean_seconds']}s "
          f"max={result['dwell_max_seconds']}s "
          f"staff={result['staff_service_seconds']}s  {obs.avg_ms:.0f}ms/f")


def run_case(filename: str = "cafe_scene5_30s.mp4", **overrides) -> dict:
    from types import SimpleNamespace

    args = SimpleNamespace(weights="yoloe-11l-seg.pt", tracker="tracktrack",
                           imgsz=1280, max_frames=0)
    for k, v in overrides.items():
        setattr(args, k, v)
    try:
        cfg = next(c for c in CLIPS if c.filename == filename)
    except StopIteration:
        raise SystemExit(f"no clip named {filename}")
    return process(cfg, args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="yoloe-11l-seg.pt")
    ap.add_argument("--tracker", default="tracktrack", choices=["tracktrack", "botsort"])
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()
    return process(CLIPS[0], args)


if __name__ == "__main__":
    main()
