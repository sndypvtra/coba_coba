"""Pass 2: where the liquid surface is, on every frame, after de-flickering.

Splash under the nozzle throws single-frame spikes: the raw series jumped to 69%
on f204 and 83% on f211 while the trend around them sat near 45%. A liquid
surface cannot rise a third of the bottle and fall back within 1/25 s, so what
comes off the per-frame detector is filtered before anything is reported.

Three filters, each fixing what the one before it cannot:

  median      kills isolated splash spikes without touching the trend
  isotonic    a filling level only rises, so the fitted curve may only rise
  smoothing   a filler dispenses at a roughly constant rate; monotonicity alone
              still allowed a sustained 27%-of-the-bottle step in 1/25 s

Rendering is deferred to a third pass precisely so this one can look ahead.
"""

from __future__ import annotations

import cv2
import numpy as np

from calibration import ROI, THREAD_DATUM_Y
from profile import (band_widths, isotonic_nonincreasing, pool_surface)
from segmentation import liquid_mask

MEDIAN_WINDOW = 7
SMOOTH_WINDOW = 11


def locate(cap, roi_for, band_profile, empty: int, max_frames: int = 0) -> list[int]:
    """The raw per-frame surface row; `empty` where no liquid was found."""
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    raw: list[int] = []
    while True:
        ok, frame = cap.read()
        if not ok or (max_frames and len(raw) >= max_frames):
            break
        roi = roi_for(frame)
        mask = liquid_mask(frame, roi)
        s = pool_surface(band_widths(mask, roi, roi[0] - ROI[0]), band_profile)
        raw.append(empty if s is None else int(s))
    return raw


def deflicker(raw: list[int], empty: int) -> list[int | None]:
    """Median, then monotonic fit, then smooth and re-impose monotonicity.

    Only the frames that actually hold liquid are fitted, so the empty run
    before the fill starts stays empty rather than being dragged into a trend.
    Rows count downward, so a rising level is a *non-increasing* row index.
    """
    arr = np.array(raw, dtype=float)
    pad = MEDIAN_WINDOW // 2
    padded = np.pad(arr, pad, mode="edge")
    smooth = np.array([np.median(padded[i:i + MEDIAN_WINDOW]) for i in range(len(arr))])

    wet = np.where(smooth < empty)[0]
    if len(wet):
        a, b = int(wet.min()), int(wet.max()) + 1
        seg = isotonic_nonincreasing(smooth[a:b])
        # Monotonicity alone still keeps a sustained step: the f215->f216 jump is
        # an increase, so the isotonic fit preserved it and the level still moved
        # 27% of the bottle in 1/25 s. Smooth the fitted curve, then re-impose
        # monotonicity on top of the smoothing.
        if len(seg) > SMOOTH_WINDOW:
            pad2 = SMOOTH_WINDOW // 2
            padded2 = np.pad(seg, pad2, mode="edge")
            seg = np.convolve(padded2, np.ones(SMOOTH_WINDOW) / SMOOTH_WINDOW,
                              mode="valid")[: len(seg)]
            seg = isotonic_nonincreasing(seg)
        smooth[a:b] = seg
    return [None if v >= empty else int(round(v)) for v in smooth]


def announce(n: int, ref_row: int, volume: float) -> None:
    print(f"pass 2: {n} surfaces located, median-filtered over {MEDIAN_WINDOW} frames; "
          f"capacity datum = thread line y={THREAD_DATUM_Y} (row {ref_row}), "
          f"reference volume {volume:.3e} px^3")
