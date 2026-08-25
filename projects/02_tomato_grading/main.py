#!/usr/bin/env python3
"""Case 2 - Tomato grading line: the same engine, different words.

    python main.py

Same weights, same tracker, same counting rule, the same six modules in the same
shape. Two of them differ from project 01: `config.py` (one prompt instead of
two, a line 9.4 degrees off vertical, a y-ROI) and `panel.py` (the words on the
dashboard). Nothing else. That is the whole claim of a zero-shot pipeline, and
putting the two projects side by side is what makes it checkable rather than
asserted.

Where the work happens:

    config.py     one prompt, a tilted line, and the y-ROI that excludes the
                  blurred foreground lane
    assets.py     what has to be downloaded before a run
    panel.py      the dashboard; says "in-focus lanes only" on the frame, so the
                  count cannot be read as every tomato on the machine
    report.py     the console read-out
    baseline.py   the last verified count, checked and printed on every run

The detector, tracker and counting rule live in `factory_vision/counting/`.
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
import panel  # noqa: E402
import report  # noqa: E402
from config import CLIP  # noqa: E402

from factory_vision.assets import adopt_mobileclip, place_mobileclip  # noqa: E402
from factory_vision.counting import run_case  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # No options on purpose - the whole calibration is `config.py`, and a flag
    # that moved a counting line would put the answer somewhere the repository
    # cannot see. It is here so that `--help` prints help and a mistyped flag is
    # refused, rather than silently ignored while a seven-minute render starts.
    ap.parse_args()

    report.banner(CLIP, "2", "Tomato grading line - zero-shot counting")

    if not assets.fetch(VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    report.settings(CLIP)
    # This project draws its own dashboard. It counts and does not
    # measure, so `panel.build` has no size or volume row to print -
    # which is the point, and used to be the bug.
    summary = run_case(CLIP, VIDEO_DIR, OUTPUT_DIR, panel=panel.build)
    report.results(summary)
    report.regression(baseline.check(summary))
    adopt_mobileclip(WEIGHTS_DIR, Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
