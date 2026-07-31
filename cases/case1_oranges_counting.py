#!/usr/bin/env python3
"""Case 1 - Citrus sorting line: count oranges crossing a line.

Zero-shot: the detector is given the words "orange" and "round orange fruit" and
nothing else. No training, no labelled data, no fixed class list.

Run:  python cases/case1_oranges_counting.py
"""

from _common import ROOT, banner, report  # noqa: F401  (sets sys.path)

from factory_vision.counting import CLIPS, run_case

CLIP = "01_oranges_production_line.mp4"


def main() -> None:
    cfg = next(c for c in CLIPS if c.filename == CLIP)
    banner(1, "Orange counting (zero-shot)", cfg.scene, cfg.source_url)
    print(f"  prompts: {cfg.prompts}")
    print(f"  conf={cfg.conf}  min_track_age={cfg.min_track_age}  "
          f"belt motion={cfg.motion} px/frame\n")

    summary = run_case(CLIP)

    report(summary, [
        ("Counted (line crossings)", summary["count_total"]),
        ("Unique track IDs", summary["unique_track_ids"]),
        ("Reverse crossings", summary["count_reverse_crossings"]),
        ("Detections / frame", summary["avg_detections_per_frame"]),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame"),
    ])
    print("  Note: this belt runs ~3 px/frame, so over 9.5 s most detected")
    print("  oranges never reach the line. Crossings measure throughput past a")
    print("  point; unique IDs count everything that appeared on screen.")


if __name__ == "__main__":
    main()
