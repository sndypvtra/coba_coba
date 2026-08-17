#!/usr/bin/env python3
"""Case 4 - Bottling line: measure how much product is dispensed into a bottle.

    python main.py
    python main.py --capacity-ml 1000        # a different SKU
    python main.py --video other_fill.mp4    # new footage from the SAME station

Not counting, and not zero-shot. Product inside the bottle is segmented on
saturation, the liquid surface is located, and the volume below it is integrated
over the bottle's bore as a stack of discs.

What is *measured* is the fill fraction. Millilitres are that fraction against
the nominal capacity configured for the SKU - no video can observe how big a
bottle is.

Where the work happens:

    calibration.py   the ROI, the surface band, the thread-line datum
    assets.py        the clip, pinned to the 1080p rendition
    roi.py           keeping the window on the bottle against camera shake
    segmentation.py  product vs glass vs background, on saturation
    profile.py       widths, pool tops, isotonic fit, disc integration
    bore.py          pass 1: the fixed bore, and the capacity it implies
    level.py         pass 2: the surface per frame, de-flickered
    pipeline.py      the sequence, and pass 3's render
    panel.py         the readout overlay
    report.py        this file's console output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets  # noqa: E402
import report  # noqa: E402
from pipeline import run_case  # noqa: E402

from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capacity-ml", type=float, default=1500.0,
                    help="nominal fill volume for this SKU, base to thread line")
    ap.add_argument("--detect", action="store_true",
                    help="overlay live YOLOE bottle segmentation")
    # Every pixel constant in calibration.py belongs to one camera position, so
    # --video is only meaningful for another clip from the same bolted-down
    # station. It lives here rather than in pipeline.py because a project with
    # two command lines has one too many.
    ap.add_argument("--video", default=None,
                    help="source clip; the calibration is per-installation, so "
                         "this means another clip from the same station")
    ap.add_argument("--max-frames", type=int, default=0,
                    help="stop after N frames (0 = the whole clip)")
    args = ap.parse_args()

    report.banner()

    if not assets.fetch(VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1

    report.settings(args.capacity_ml)
    overrides = {"capacity_ml": args.capacity_ml, "detect": args.detect,
                 "max_frames": args.max_frames}
    if args.video:
        overrides["video"] = args.video
    summary = run_case(**overrides)
    report.results(summary, args.capacity_ml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
