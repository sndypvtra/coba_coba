"""The console read-out.

Identical to `01_citrus_counting/report.py`, deliberately. The two cases run the
same engine over different words, and reporting them in the same format is what
lets the two outputs be compared line by line. It stays a copy in each project
rather than a shared import because a project folder that cannot be read on its
own is not a worked example.
"""

from __future__ import annotations


def banner(cfg, case: str, title: str) -> None:
    print("=" * 74)
    print(f"CASE {case}  |  {title}")
    print(f"  scene : {cfg.scene}")
    print(f"  source: {cfg.source_url}")
    print("=" * 74)


def settings(cfg) -> None:
    print(f"\n  prompts: {cfg.prompts}")
    print(f"  conf={cfg.conf}  min_track_age={cfg.min_track_age}  "
          f"belt motion={cfg.motion} px/frame\n")


def results(summary: dict) -> None:
    print("-" * 74)
    for label, value in (
        ("Counted (line crossings)", summary["count_total"]),
        ("Unique track IDs", summary["unique_track_ids"]),
        ("Reverse crossings", summary["count_reverse_crossings"]),
        ("Detections / frame", summary["avg_detections_per_frame"]),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame"),
    ):
        print(f"  {label:<28} {value}")
    print(f"  {'video':<28} output/{summary['output']}")
    print(f"  {'summary':<28} output/summary.json")
    print("-" * 74)
