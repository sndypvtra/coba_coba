#!/usr/bin/env python3
"""Case 5 - Cafe: how many people, and how long each of them stayed.

    python main.py              # scene 5, the default room
    python main.py --scene 1    # the other room
    python main.py --all        # both, one after another

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

# Everything this project needs is in this folder, including its copy of
# `factory_vision/`. Nothing above it is on the path, which is what lets the
# folder be lifted into a repository of its own and still run.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets  # noqa: E402
import baseline  # noqa: E402
import report  # noqa: E402
from config import CLIPS  # noqa: E402
from pipeline import run_case  # noqa: E402

from factory_vision.assets import adopt_mobileclip, place_mobileclip  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)


def main() -> int:
    rooms = [c.scene_id for c in CLIPS]
    ap = argparse.ArgumentParser(
        description="Occupancy and dwell time for one room of the cafe.")
    # A room number, not a file name. `--clip cafe_scene1_30s.mp4` made the
    # command line depend on how the footage happens to be named; a room is what
    # the person running this actually has in mind.
    ap.add_argument("--scene", type=int, default=rooms[0], choices=rooms,
                    metavar="N", help=f"which room to measure {tuple(rooms)}")
    ap.add_argument("--all", action="store_true",
                    help="measure every room, one after another")
    args = ap.parse_args()

    if not assets.fetch(VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    todo = CLIPS if args.all else [c for c in CLIPS if c.scene_id == args.scene]
    missing = assets.missing_clips(VIDEO_DIR, todo)
    if missing:
        report.clips_not_found(missing)
        return 1

    # The rooms are independent measurements, not views of one scene, so they
    # are reported one after another and never combined. Saying which others
    # exist keeps a default run from hiding them.
    report.rooms(todo, [c for c in CLIPS if c not in todo])
    for cfg in todo:
        report.banner(cfg)
        summary = run_case(cfg.filename)
        report.results(summary)
        report.regression(baseline.check(cfg.scene_id, summary))
    adopt_mobileclip(WEIGHTS_DIR, Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
