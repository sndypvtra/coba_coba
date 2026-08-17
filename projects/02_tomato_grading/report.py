"""The console read-out.

Identical to `01_citrus_counting/report.py`, deliberately. The two cases run the
same engine over different words - they differ in `config.py` and `panel.py` and
nothing else - and reporting them in the same format is what lets the two outputs
be compared line by line. It stays a copy in each project rather than a shared
import because a project folder that cannot be read on its own is not a worked
example.
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


def regression(checks) -> None:
    """Did this run reproduce the last verified one?

    Printed rather than asserted: a moved number is information, not a crash,
    and the person running it should see what moved and by how much.
    """
    print("  AGAINST THE LAST VERIFIED RUN  (baseline.py)")
    for c in checks:
        print(f"    {c}")
    if all(c.ok for c in checks):
        print("    every recorded figure reproduced.")
    else:
        print("    something moved - see baseline.py for what the figure means")
        print("    and update it in the same commit if the change is intended.")
    print("-" * 74)
