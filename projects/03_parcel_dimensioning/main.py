#!/usr/bin/env python3
"""Case 3 - Parcel belt: count, range and dimension mixed packages.

    python main.py

The heaviest of the six to set up, and all of it automatic: two Depth Anything 3
checkpoints (~2.9 GB) arrive alongside the detector on first run. They are the
reason this project can answer *how big was it* from a single fixed camera, and
they are cached afterwards - both by Hugging Face, and per-frame by the pipeline
itself in `output/.depth_cache`, so a second run costs a fraction of the first.

Six models are in play here, and each one has a module that owns it:

    intrinsics.py    DA3-LARGE's camera decoder -> fx, fy, and the square-pixel
                     test that rejected two processing resolutions
    depth.py         DA3METRIC-LARGE -> canonical depth x focal / 300 = metres
    depth_cache.py   float16 maps on disk, so the second run is nearly free
    belt.py          the plane every height is measured against, plus the
                     two-part test for whether a detection is on it at all
    sizing.py        mask + depth + plane -> millimetres, and how much to
                     trust each one
    measurement.py   the order of operations, and the contract the shared
                     counting pipeline calls through

    panel.py         the live dashboard - the only project of the three that is
                     entitled to print a size, because it is the one measuring
    config.py        CLIP (counting) and SIZING (metric), kept apart because
                     only one of them survives the camera being moved
    assets.py        the clip, the detector, and the two depth checkpoints
    report.py        the read-out, including the error budget beside each number

The detector, tracker and counting rule stay in `factory_vision/counting/`,
shared with projects 01 and 02. Nothing metric does.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets  # noqa: E402
import panel  # noqa: E402
import report  # noqa: E402
from config import CLIP, SIZING  # noqa: E402
from measurement import ParcelMeasurement  # noqa: E402

from factory_vision.assets import adopt_mobileclip, place_mobileclip  # noqa: E402
from factory_vision.counting import run_case  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)

# Counted by hand from a slit-scan of the counting line's own pixel column - one
# column per frame, stacked - rather than from any run of this pipeline. That is
# what makes it a check and not a restatement.
SLIT_SCAN_TRUTH = 8


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count-only", action="store_true",
                    help="run without Depth Anything 3: no depth models and no "
                         "sizes. NOTE the count is then wrong - 10 against a "
                         "verified 8 - because the depth corridor is what fences "
                         "off the static stack. For seeing it run, not quoting.")
    args = ap.parse_args()

    report.banner(CLIP)

    # Checked before a single byte is downloaded. Without this the run fetched
    # 2.9 GB of depth checkpoints and only then raised ModuleNotFoundError from
    # inside a model constructor, several minutes into what looked like progress.
    if not args.count_only and not assets.depth_installed():
        print(f"\n{assets.DA3_INSTALL}")
        return 1

    if not assets.fetch(VIDEO_DIR, WEIGHTS_DIR, with_depth=not args.count_only):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    report.settings(CLIP, SIZING, measuring=not args.count_only)
    # The backend is what makes this project measure rather than merely count.
    # Projects 01 and 02 make the same run_case call without one - and so does
    # --count-only, which also drops this project's panel: a dashboard with a
    # SIZE MIX row and nothing to put in it is the defect panel.py exists to
    # prevent, so the shared counting panel is used instead.
    if args.count_only:
        summary = run_case(CLIP, VIDEO_DIR, OUTPUT_DIR)
    else:
        summary = run_case(CLIP, VIDEO_DIR, OUTPUT_DIR,
                           backend=ParcelMeasurement(SIZING, CLIP),
                           panel=panel.build)
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
