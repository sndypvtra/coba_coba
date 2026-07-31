#!/usr/bin/env python3
"""Case 2 - Tomato grading line: count tomatoes crossing a line.

Zero-shot from the single word "tomato". This is the clip where threshold tuning
actually paid off: lowering conf and opening the tracker gates cut median entry
lag 0.326 -> 0.203 and more than doubled the share of tomatoes acquired within
15% of the frame edge (21% -> 50%).

Run:  python cases/case2_tomatoes_counting.py
"""

from _common import ROOT, banner, report  # noqa: F401

from factory_vision.counting import CLIPS, run_case

CLIP = "02_tomatoes_conveyor.mp4"


def main() -> None:
    cfg = next(c for c in CLIPS if c.filename == CLIP)
    banner(2, "Tomato counting (zero-shot)", cfg.scene, cfg.source_url)
    print(f"  prompts: {cfg.prompts}")
    print(f"  conf={cfg.conf}  min_track_age={cfg.min_track_age}  "
          f"belt motion={cfg.motion} px/frame")
    print(f"  note   : {cfg.extra_notes}\n")

    summary = run_case(CLIP)

    report(summary, [
        ("Counted (line crossings)", summary["count_total"]),
        ("Unique track IDs", summary["unique_track_ids"]),
        ("Reverse crossings", summary["count_reverse_crossings"]),
        ("Detections / frame", summary["avg_detections_per_frame"]),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame"),
    ])


if __name__ == "__main__":
    main()
