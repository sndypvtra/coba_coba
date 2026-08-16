#!/usr/bin/env python3
"""Case 3 - Parcel belt: count, range and dimension mixed packages.

    python main.py

The heaviest of the six to set up, and all of it automatic: two Depth Anything 3
checkpoints (~2.9 GB) arrive alongside the detector on first run. They are the
reason this project can answer *how big was it* from a single fixed camera, and
they are cached afterwards - both by Hugging Face, and per-frame by the pipeline
itself in `output/.depth_cache`, so a second run costs a fraction of the first.

Where the work happens:

    config.py    the line, the belt patches, the depth corridor, both
                 calibration scales - every constant the millimetres rest on
    assets.py    the clip, the detector, and the two depth checkpoints
    report.py    the read-out, including the error budget beside each number
    ../../factory_vision/counting/depth.py    canonical depth -> metres
    ../../factory_vision/counting/sizing.py   pixels + range -> millimetres
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

# Counted by hand from a slit-scan of the counting line's own pixel column - one
# column per frame, stacked - rather than from any run of this pipeline. That is
# what makes it a check and not a restatement.
SLIT_SCAN_TRUTH = 8


def main() -> int:
    report.banner(CLIP)

    if not assets.fetch(VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    report.settings(CLIP)
    summary = run_case(CLIP, VIDEO_DIR, OUTPUT_DIR)
    report.headline(summary, CLIP, SLIT_SCAN_TRUTH)

    dim = summary.get("dimensioning", {})
    if dim:
        report.measurement_chain(dim)
        report.parcel_table(dim)
        report.legend()
    adopt_mobileclip(WEIGHTS_DIR, Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
