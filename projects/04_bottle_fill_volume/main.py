#!/usr/bin/env python3
"""Case 4 - Bottling line: measure how much product is dispensed into a bottle.

    python main.py
    python main.py --capacity-ml 1000        # a different SKU

Not counting, and not zero-shot. Product inside the bottle is segmented on
saturation, the liquid surface is located, and the volume below it is integrated
over the bottle's bore as a stack of discs.

What is *measured* is the fill fraction. Millilitres are that fraction against
the nominal capacity configured for the SKU - no video can observe how big a
bottle is.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration as L  # noqa: E402
from pipeline import run_case  # noqa: E402

from factory_vision.assets import Clip, Requirements, ensure  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)

NEEDS = Requirements(
    # 25 fps, and the only clip of the six whose default Pexels rendition is
    # 3840x2160 - every pixel constant in calibration.py is set on the 1080p one.
    clips=(Clip("07_bottle_filling_line.mp4", 8720278, "hd_1920_1080_25fps"),),
    weights=("yoloe-11l-seg.pt",),
    notes=("weights are only needed for --detect; the measurement itself is "
           "colour and geometry, no network",),
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capacity-ml", type=float, default=1500.0,
                    help="nominal fill volume for this SKU, base to thread line")
    ap.add_argument("--detect", action="store_true",
                    help="overlay live YOLOE bottle segmentation")
    args = ap.parse_args()

    print("=" * 74)
    print("CASE 4  |  Fill-volume inspection")
    print("  scene : Bottling line - inline filler, clear bottles, amber product")
    print("  source: https://www.pexels.com/video/"
          "empty-bottles-in-a-filling-machine-8720278/")
    print("=" * 74)

    if not ensure(NEEDS, VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1

    print(f"\n  method  : HSV segmentation (S>={L.LIQUID_LO[1]}) + disc integration")
    print(f"  datum   : bottle base to thread line (y={L.THREAD_DATUM_Y})")
    print(f"  capacity: {args.capacity_ml:,.0f} mL (configured, not measured)\n")

    summary = run_case(capacity_ml=args.capacity_ml, detect=args.detect)
    series = summary["series"]

    print("-" * 74)
    for label, value in (
        ("Dispensed volume", f"{summary['final_estimated_ml']:,.0f} mL"),
        ("Fill by volume", f"{summary['final_fill_volume_frac']*100:.1f} %"),
        ("Fill by height", f"{series[-1]['fill_height_frac']*100:.1f} %"),
        ("Nominal capacity", f"{args.capacity_ml:,.0f} mL"),
        ("Frames", summary["frames"]),
    ):
        print(f"  {label:<28} {value}")
    print(f"  {'video':<28} output/{summary['output']}")
    print("-" * 74)
    print("  Fill fraction is measured; the millilitre figure is that fraction")
    print("  against the configured capacity. Calibrated to this camera, bottle")
    print("  and product - README.md lists what shifts break it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
