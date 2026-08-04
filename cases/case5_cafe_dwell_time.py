#!/usr/bin/env python3
"""Case 5 - Cafe: count people per frame and measure how long each one stays.

Zero-shot detection again - the detector is given the word "person" and nothing
else - but the question is different from the conveyor cases. There is no line
and no travel direction. What is reported is occupancy (how many are in frame
now), visitors (how many distinct people have appeared), and dwell time per
person.

Two things are excluded, and both are per-installation: a wall mirror shows
people already counted in the room, and staff behind the counter are not
customers. Neither is decidable from a person's appearance - only from where
they are in a fixed camera's frame - so each cafe carries its own zones in
factory_vision/dwell/config.py.

Dwell time is a *tracking* result. If a seated customer is occluded and comes
back with a new ID, one long visit is reported as two short ones. The summary
carries a continuity figure per person so that failure is visible rather than
hidden - see `quality` in output/dwell_summary.json.

Run:  python cases/case5_cafe_dwell_time.py
      python cases/case5_cafe_dwell_time.py --clip cafe_scene17_30s.mp4
      python cases/case5_cafe_dwell_time.py --all
"""

import argparse

from _common import ROOT, banner, report  # noqa: F401  (sets sys.path)

from factory_vision.dwell import CLIPS, run_case


def run_one(cfg, number: int) -> None:
    banner(number, f"Cafe occupancy and dwell time - {cfg.filename}",
           cfg.scene, cfg.source)
    print(f"  prompts: {cfg.prompts}")
    print(f"  conf={cfg.conf}  min_track_age={cfg.min_track_age}  "
          f"dedup={cfg.dedup_containment}")
    for z in cfg.exclusion_zones:
        print(f"  zone '{z.name}': {z.reason}")
    print()

    summary = run_case(cfg.filename)
    q, f = summary["quality"], summary["filtering"]

    report(summary, [
        ("Distinct visitors", summary["visitors_total"]),
        ("Occupancy, mean", summary["occupancy_mean"]),
        ("Occupancy, max", summary["occupancy_max"]),
        ("Dwell, mean", f"{summary['dwell_mean_seconds']} s"),
        ("Dwell, max", f"{summary['dwell_max_seconds']} s"),
        ("Clip duration", f"{summary['duration_seconds']} s"),
        ("Duplicate boxes removed", f["duplicate_boxes_removed"]),
        ("Excluded by zone", f["excluded_by_zone"] or "none"),
        ("Tracks with gaps", f"{q['tracks_with_gaps']} of {summary['visitors_total']}"),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame"),
    ])
    print("  Occupancy is a detection result and is the reliable number here.")
    print("  Dwell time and the visitor total depend on identity holding across")
    print("  occlusions; 'tracks with gaps' is how often it did not.\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default=CLIPS[0].filename,
                    choices=[c.filename for c in CLIPS])
    ap.add_argument("--all", action="store_true", help="run every configured cafe")
    args = ap.parse_args()

    todo = CLIPS if args.all else [next(c for c in CLIPS if c.filename == args.clip)]
    for i, cfg in enumerate(todo, start=1):
        run_one(cfg, 5 if len(todo) == 1 else i)


if __name__ == "__main__":
    main()
