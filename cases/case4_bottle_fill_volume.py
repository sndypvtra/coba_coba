#!/usr/bin/env python3
"""Case 4 - Bottling line: measure how much product is dispensed into a bottle.

Not a counting problem and not zero-shot. Product inside the bottle is segmented
on saturation, the liquid surface is located, and the volume below it is
integrated over the bottle's bore as a stack of discs.

What is measured is the fill *fraction*. Millilitres are that fraction against
the nominal capacity you configure for the SKU - a video cannot observe how big
a bottle is.

Run:  python cases/case4_bottle_fill_volume.py
      python cases/case4_bottle_fill_volume.py --capacity-ml 1000
"""

import argparse

from _common import ROOT, banner, report  # noqa: F401

import factory_vision.filling as L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capacity-ml", type=float, default=1500.0,
                    help="nominal fill volume for this SKU, base to thread line")
    ap.add_argument("--detect", action="store_true",
                    help="overlay live YOLOE bottle segmentation")
    args = ap.parse_args()

    banner(4, "Fill-volume inspection",
           "Bottling line - inline filler, clear bottles, amber product",
           "https://www.pexels.com/video/empty-bottles-in-a-filling-machine-8720278/")
    print(f"  method  : HSV segmentation (S>={L.LIQUID_LO[1]}) + disc integration")
    print(f"  datum   : bottle base to thread line (y={L.THREAD_DATUM_Y})")
    print(f"  capacity: {args.capacity_ml:,.0f} mL (configured, not measured)\n")

    summary = L.run_case(capacity_ml=args.capacity_ml, detect=args.detect)

    series = summary["series"]
    report(summary, [
        ("Dispensed volume", f"{summary['final_estimated_ml']:,.0f} mL"),
        ("Fill by volume", f"{summary['final_fill_volume_frac']*100:.1f} %"),
        ("Fill by height", f"{series[-1]['fill_height_frac']*100:.1f} %"),
        ("Nominal capacity", f"{args.capacity_ml:,.0f} mL"),
        ("Frames", summary["frames"]),
    ])
    print("  Fill fraction is measured; the millilitre figure is that fraction")
    print("  against the configured capacity. Calibrated to this camera, bottle")
    print("  and product - see docs/liquid-level.md for what shifts break it.")


if __name__ == "__main__":
    main()
