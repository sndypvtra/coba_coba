#!/usr/bin/env python3
"""Case 2 - Tomato grading line: the same engine, different words.

    python main.py

The only difference from project 01 is `config.py`. Same weights, same tracker,
same counting rule, the same four files in the same shape - one word changed and
a line moved. That is the whole claim of a zero-shot pipeline, and putting the
two projects side by side is what makes it checkable rather than asserted.

Where the work happens:

    config.py    the line, the prompts, the thresholds - the whole calibration
    assets.py    what has to be downloaded before a run
    report.py    the console read-out
    ../../factory_vision/counting/   the detector, tracker and counting rule
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
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
