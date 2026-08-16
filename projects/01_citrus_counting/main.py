#!/usr/bin/env python3
"""Case 1 - Citrus sorting line: count oranges past a line, from words alone.

    python main.py

Everything missing is fetched first, with a progress bar. Nothing to install
by hand, no order to remember: the clip lands in `input/`, the weights in the
shared `weights/` at the repository root, and the result in `output/`.

Where the work happens:

    config.py    the line, the prompts, the thresholds - the whole calibration
    assets.py    what has to be downloaded before a run
    report.py    the console read-out
    ../../factory_vision/counting/   the detector, tracker and counting rule,
                 shared with project 02 because nothing in it is fruit-specific
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets  # noqa: E402
import report  # noqa: E402
from config import CLIP  # noqa: E402

from factory_vision.assets import adopt_mobileclip, place_mobileclip  # noqa: E402
from factory_vision.counting import run_case  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)


def main() -> int:
    report.banner(CLIP, "1", "Citrus sorting line - zero-shot counting")

    if not assets.fetch(VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    report.settings(CLIP)
    report.results(run_case(CLIP, VIDEO_DIR, OUTPUT_DIR))
    adopt_mobileclip(WEIGHTS_DIR, Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
