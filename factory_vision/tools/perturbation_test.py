#!/usr/bin/env python3
"""Measure what a re-mounted camera costs the fill-volume inspection.

Case 4 is calibrated to one station: the ROI, the thread datum and the bottle
outline are all pixel coordinates in a fixed frame. This script quantifies how
badly that breaks when the framing moves, which is the difference between a
limitation that is stated and one that is assumed.

The clip is re-rendered with a modest zoom and translation - the sort of change
a camera knocked and re-mounted would produce, not a different production line -
and the same pipeline is run over it unchanged.

Run:  python src/perturbation_test.py
      python src/perturbation_test.py --zoom 1.15 --dx 100 --dy 0
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from factory_vision.paths import ROOT, VIDEO_DIR, WEIGHTS_DIR
if __name__ == "__main__" and str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from factory_vision import filling as L  # noqa: E402


def perturb_clip(src: Path, dst: Path, zoom: float, dx: int, dy: int) -> None:
    """Re-encode `src` zoomed about its centre and translated by (dx, dy)."""
    cap = cv2.VideoCapture(str(src))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Zoom about the frame centre, then translate. Composed into one affine so
    # the frame is resampled once.
    M = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), 0.0, zoom)
    M[0, 2] += dx
    M[1, 2] += dy

    writer = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REPLICATE))
        n += 1
    cap.release()
    writer.release()
    print(f"  wrote {dst.name}: {n} frames, zoom x{zoom:.2f}, shift ({dx:+d}, {dy:+d})")


"""A camera move small enough to be plausible, up to one nobody would miss."""
SWEEP = [
    (1.00, 40, 20),
    (1.08, 60, 30),
    (1.00, 120, 60),
    (1.20, 0, 0),
    (1.00, 220, 110),
]


def measure(zoom: float, dx: int, dy: int, capacity_ml: float) -> dict:
    tag = f"z{zoom:.2f}_dx{dx}_dy{dy}".replace(".", "")
    shifted = L.OUT_DIR / f"07_bottle_filling_line__{tag}.mp4"
    perturb_clip(Path(L.VIDEO), shifted, zoom, dx, dy)
    return L.run_case(video=str(shifted),
                      out_name=f"07_bottle_filling__liquid_{tag}.mp4",
                      summary_name=f"liquid_level_summary_{tag}.json",
                      capacity_ml=capacity_ml)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zoom", type=float, default=1.08)
    ap.add_argument("--dx", type=int, default=60)
    ap.add_argument("--dy", type=int, default=30)
    ap.add_argument("--capacity-ml", type=float, default=1500.0)
    ap.add_argument("--sweep", action="store_true",
                    help="run the whole sensitivity sweep instead of one setting")
    args = ap.parse_args()

    print("=" * 74)
    print("PERTURBATION TEST  |  does the case 4 calibration survive a camera move?")
    print("=" * 74)

    baseline_path = L.OUT_DIR / "liquid_level_summary.json"
    if not baseline_path.exists():
        raise SystemExit("run cases/case4_bottle_fill_volume.py first - "
                         f"{baseline_path} is the baseline this compares against")
    baseline = json.loads(baseline_path.read_text())
    b_ml, b_frac = baseline["final_estimated_ml"], baseline["final_fill_volume_frac"]

    settings = SWEEP if args.sweep else [(args.zoom, args.dx, args.dy)]
    rows = []
    for zoom, dx, dy in settings:
        print(f"\n>>> zoom x{zoom:.2f}, shift ({dx:+d}, {dy:+d})")
        got = measure(zoom, dx, dy, args.capacity_ml)
        rows.append((zoom, dx, dy, got["final_estimated_ml"],
                     got["final_fill_volume_frac"]))

    print("\n" + "-" * 74)
    print(f"  {'Framing':<32}{'Volume':>12}{'Fill':>10}{'Error':>10}")
    print(f"  {'calibrated':<32}{b_ml:>9,.0f} mL{b_frac*100:>9.1f}%{'-':>10}")
    for zoom, dx, dy, ml, frac in rows:
        desc = f"zoom x{zoom:.2f}, shift ({dx:+d}, {dy:+d})"
        err = (ml - b_ml) / b_ml * 100 if b_ml else 0.0
        print(f"  {desc:<32}{ml:>9,.0f} mL{frac*100:>9.1f}%{err:>9.1f}%")
    print("-" * 74)
    print("  Every row is reported through the same confident panel, with no error")
    print("  flag on any of them. That silence is the hazard, not the error itself.")


if __name__ == "__main__":
    main()
