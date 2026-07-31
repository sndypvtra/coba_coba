#!/usr/bin/env python3
"""Case 3 - Parcel unloading belt: count mixed packages crossing a line.

The case that shows the main failure mode of prompt-driven detection: a black
holdall sat on the belt undetected for several passes because nobody had named
it. Against "cardboard box", "parcel" and "plastic bag" its best overlap with any
predicted box was IoU 0.01 - it is fabric, so "plastic bag" never matched. Adding
"sports bag" finds it at conf 0.55.

An object type nobody names is not missed, it is invisible, and nothing in the
output flags it.

Run:  python cases/case3_packages_counting.py
"""

from _common import ROOT, banner, report  # noqa: F401

from src.conveyor_count import CLIPS, run_case

CLIP = "03_packages_conveyor.mp4"


def main() -> None:
    cfg = next(c for c in CLIPS if c.filename == CLIP)
    banner(3, "Package counting (zero-shot)", cfg.scene, cfg.source_url)
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
