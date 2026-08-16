#!/usr/bin/env python3
"""Case 5 - Cafe: how many people, and how long each of them stayed.

    python main.py
    python main.py --clip cafe_scene1_30s.mp4
    python main.py --all

Two rooms of the same cafe, counted and timed from words alone. Occupancy is a
detection result and is the number to trust; dwell time additionally needs an
identity to survive people walking behind each other, which is reported rather
than assumed.

The two clips are cut from a long stock video, so unlike the other projects
they cannot be fetched by id - `input/` already holds them, and the README says
where they came from.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CLIPS  # noqa: E402
from pipeline import run_case  # noqa: E402

from factory_vision.assets import Requirements, ensure, place_mobileclip  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)

NEEDS = Requirements(
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the two cafe clips are pre-cut and live in input/; see README.md",),
)


def run_one(cfg) -> None:
    print("=" * 74)
    print(f"CASE 5  |  Cafe occupancy and dwell time - {cfg.filename}")
    print(f"  scene : {cfg.scene}")
    print(f"  source: {cfg.source}")
    print("=" * 74)
    print(f"  prompts: {cfg.prompts}")
    print(f"  conf={cfg.conf}  min_track_age={cfg.min_track_age}  "
          f"dedup={cfg.dedup_containment}")
    for z in cfg.exclusion_zones:
        print(f"  zone '{z.name}': {z.reason}")
    print()

    summary = run_case(cfg.filename)
    q, f = summary["quality"], summary["filtering"]

    print("-" * 74)
    for label, value in (
        ("Distinct visitors", summary["visitors_total"]),
        ("Occupancy, mean", summary["occupancy_mean"]),
        ("Occupancy, max", summary["occupancy_max"]),
        ("Dwell, mean", f"{summary['dwell_mean_seconds']} s"),
        ("Dwell, max", f"{summary['dwell_max_seconds']} s"),
        ("Clip duration", f"{summary['duration_seconds']} s"),
        ("Duplicate boxes removed", f["duplicate_boxes_removed"]),
        ("Broken tracks re-linked", f["tracks_relinked"]),
        ("Staff service time", f"{summary['staff_service_seconds']} s"
                               if summary["staff"] else "no service point"),
        ("Tracks with gaps", f"{q['tracks_with_gaps']} of {summary['visitors_total']}"),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame"),
    ):
        print(f"  {label:<28} {value}")
    print(f"  {'video':<28} output/{summary['output']}")
    print("-" * 74)
    print("  Occupancy is a detection result and is the reliable number here.")
    print("  Dwell time and the visitor total depend on identity holding across")
    print("  occlusions; 'tracks with gaps' is how often it did not.\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default=CLIPS[0].filename,
                    choices=[c.filename for c in CLIPS])
    ap.add_argument("--all", action="store_true", help="run every configured room")
    args = ap.parse_args()

    if not ensure(NEEDS, VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    todo = CLIPS if args.all else [next(c for c in CLIPS if c.filename == args.clip)]
    missing = [c.filename for c in todo if not (VIDEO_DIR / c.filename).exists()]
    if missing:
        print(f"\n  input/ is missing {missing}. See README.md for how these two "
              f"clips are cut from the source video.")
        return 1
    for cfg in todo:
        run_one(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
