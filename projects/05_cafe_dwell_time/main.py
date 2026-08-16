#!/usr/bin/env python3
"""Case 5 - Cafe: how many people, and how long each of them stayed.

    python main.py
    python main.py --clip cafe_scene1_30s.mp4
    python main.py --all

Two rooms of the same cafe, counted and timed from words alone. Occupancy is a
detection result and is the number to trust; dwell time additionally needs an
identity to survive people walking behind each other, which is reported rather
than assumed.

Where the work happens:

    config.py       the two rooms - prompts, thresholds, mirror and counter
    assets.py       what has to be present before a run
    zones.py        frame regions that are not ordinary customers
    detection.py    pass 1: detect, filter, track, describe
    identity.py     re-linking tracks the tracker broke on occlusion
    roles.py        staff or customer, decided once per person
    render.py       pass 2: the annotated video
    overlay.py      the readout strip and the box tags
    summary.py      the result record and its quality signals
    pipeline.py     the sequence, and nothing else
    report.py       this file's console output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets  # noqa: E402
import report  # noqa: E402
from config import CLIPS  # noqa: E402
from pipeline import run_case  # noqa: E402

from factory_vision.assets import adopt_mobileclip, place_mobileclip  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default=CLIPS[0].filename,
                    choices=[c.filename for c in CLIPS])
    ap.add_argument("--all", action="store_true", help="run every configured room")
    args = ap.parse_args()

    if not assets.fetch(VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    todo = CLIPS if args.all else [next(c for c in CLIPS if c.filename == args.clip)]
    missing = assets.missing_clips(VIDEO_DIR, todo)
    if missing:
        report.clips_not_found(missing)
        return 1

    for cfg in todo:
        report.banner(cfg)
        report.results(run_case(cfg.filename))
    adopt_mobileclip(WEIGHTS_DIR, Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
