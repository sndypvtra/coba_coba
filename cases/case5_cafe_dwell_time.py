#!/usr/bin/env python3
"""Case 5 - Cafe: count people per frame and measure how long each one stays.

Zero-shot detection again - the detector is given the word "person" and nothing
else - but the question is different from the conveyor cases. There is no line
and no travel direction. What is reported is occupancy (how many are in frame
now), visitors (how many distinct people have appeared), and dwell time per
person.

Dwell time is a *tracking* result. If a seated customer is occluded and comes
back with a new ID, one long visit is reported as two short ones. The summary
carries a continuity figure per person so that failure is visible rather than
hidden - see `quality` in output/dwell_summary.json.

Run:  python cases/case5_cafe_dwell_time.py
"""

from _common import ROOT, banner, report  # noqa: F401  (sets sys.path)

from factory_vision.dwell import CLIPS, run_case

CLIP = "cafe_scene5_30s.mp4"


def main() -> None:
    cfg = next(c for c in CLIPS if c.filename == CLIP)
    banner(5, "Cafe occupancy and dwell time (zero-shot)", cfg.scene, cfg.source)
    print(f"  prompts: {cfg.prompts}")
    print(f"  conf={cfg.conf}  min_track_age={cfg.min_track_age}\n")

    summary = run_case(CLIP)
    q = summary["quality"]

    report(summary, [
        ("Distinct visitors", summary["visitors_total"]),
        ("Occupancy, mean", summary["occupancy_mean"]),
        ("Occupancy, max", summary["occupancy_max"]),
        ("Dwell, mean", f"{summary['dwell_mean_seconds']} s"),
        ("Dwell, max", f"{summary['dwell_max_seconds']} s"),
        ("Clip duration", f"{summary['duration_seconds']} s"),
        ("Tracks with gaps", f"{q['tracks_with_gaps']} of {summary['visitors_total']}"),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame"),
    ])
    print("  Occupancy is a detection result and is the reliable number here.")
    print("  Dwell time and the visitor total depend on identity holding across")
    print("  occlusions; 'tracks with gaps' is how often it did not.")


if __name__ == "__main__":
    main()
