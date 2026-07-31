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

ROOT = Path(__file__).resolve().parent.parent
if __name__ == "__main__" and str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from src import liquid_level as L  # noqa: E402


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zoom", type=float, default=1.08)
    ap.add_argument("--dx", type=int, default=60)
    ap.add_argument("--dy", type=int, default=30)
    ap.add_argument("--capacity-ml", type=float, default=1500.0)
    args = ap.parse_args()

    print("=" * 74)
    print("PERTURBATION TEST  |  does the case 4 calibration survive a camera move?")
    print("=" * 74)

    baseline_path = L.OUT_DIR / "liquid_level_summary.json"
    if not baseline_path.exists():
        raise SystemExit("run cases/case4_bottle_fill_volume.py first - "
                         f"{baseline_path} is the baseline this compares against")
    baseline = json.loads(baseline_path.read_text())

    shifted = L.OUT_DIR / "07_bottle_filling_line__shifted.mp4"
    print("\nperturbing the source clip")
    perturb_clip(Path(L.VIDEO), shifted, args.zoom, args.dx, args.dy)

    print("\nrunning the unchanged pipeline over it")
    got = L.run_case(video=str(shifted),
                     out_name="07_bottle_filling__liquid_shifted.mp4",
                     summary_name="liquid_level_summary_shifted.json",
                     capacity_ml=args.capacity_ml)

    b_ml, b_frac = baseline["final_estimated_ml"], baseline["final_fill_volume_frac"]
    g_ml, g_frac = got["final_estimated_ml"], got["final_fill_volume_frac"]

    print("\n" + "-" * 74)
    print(f"  {'':<34}{'Volume':>12}{'Fill':>10}")
    print(f"  {'Calibrated clip':<34}{b_ml:>9,.0f} mL{b_frac*100:>9.1f}%")
    print(f"  {'Same scene, framing shifted':<34}{g_ml:>9,.0f} mL{g_frac*100:>9.1f}%")
    print("-" * 74)
    ratio = b_ml / g_ml if g_ml else float("inf")
    print(f"  off by {ratio:.1f}x, reported through the same panel with no error flag.")
    print("  Nothing in the output signals that the calibration no longer holds -")
    print("  that silence is the hazard, not the error itself.")


if __name__ == "__main__":
    main()
