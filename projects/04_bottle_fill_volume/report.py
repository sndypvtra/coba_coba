"""The console read-out.

The closing note carries the one thing a reader must not miss: the percentage is
measured, the millilitres are not. They are that percentage against a capacity
someone typed in, and printing the two in the same table without saying so would
pass off a configuration value as an observation.
"""

from __future__ import annotations

import calibration as L

SOURCE = ("https://www.pexels.com/video/"
          "empty-bottles-in-a-filling-machine-8720278/")


def banner() -> None:
    print("=" * 74)
    print("CASE 4  |  Fill-volume inspection")
    print("  scene : Bottling line - inline filler, clear bottles, amber product")
    print(f"  source: {SOURCE}")
    print("=" * 74)


def settings(capacity_ml: float) -> None:
    print(f"\n  method  : HSV segmentation (S>={L.LIQUID_LO[1]}) + disc integration")
    print(f"  datum   : bottle base to thread line (y={L.THREAD_DATUM_Y})")
    print(f"  capacity: {capacity_ml:,.0f} mL (configured, not measured)\n")


def results(summary: dict, capacity_ml: float) -> None:
    series = summary["series"]
    print("-" * 74)
    for label, value in (
        ("Dispensed volume", f"{summary['final_estimated_ml']:,.0f} mL"),
        ("Fill by volume", f"{summary['final_fill_volume_frac']*100:.1f} %"),
        ("Fill by height", f"{series[-1]['fill_height_frac']*100:.1f} %"),
        ("Nominal capacity", f"{capacity_ml:,.0f} mL"),
        ("Frames", summary["frames"]),
    ):
        print(f"  {label:<28} {value}")
    print(f"  {'video':<28} output/{summary['output']}")
    print("-" * 74)
    print("  Fill fraction is measured; the millilitre figure is that fraction")
    print("  against the configured capacity. Calibrated to this camera, bottle")
    print("  and product - README.md lists what shifts break it.")
