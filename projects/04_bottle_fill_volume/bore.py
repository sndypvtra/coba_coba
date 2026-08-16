"""Pass 1: the bottle's internal bore, and the capacity it implies.

The denominator has to be fixed before any fraction is computed. Growing it
frame by frame makes the fill series non-monotonic and meaningless - the level
appears to fall whenever the bore below it widens - so the whole clip is walked
once to find the widest liquid ever seen at each row, and only then is anything
divided by anything.

Two profiles come out, because two different questions are being asked:

  prof       the full ROI width per row - the bore, used for volume
  band_prof  the same over a narrow column under the nozzle - used only to
             locate the surface, where a full-width search would lock onto
             splash against the bottle wall
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from calibration import ROI, SURFACE_BAND, THREAD_DATUM_Y
from profile import band_widths, bottle_profile, pool_top_absolute, row_widths
from segmentation import liquid_mask

# How far below the topmost measured row the neck bore is sampled from. Right at
# the surface the mask is only partial, so the topmost row is not representative.
NECK_SAMPLE = (30, 150)


@dataclass
class Bore:
    """The fixed reference every fraction in this project is taken against."""

    profile: np.ndarray         # bore per row, full ROI width
    band_profile: np.ndarray    # bore per row, surface-band width
    frames: int


def learn(cap, roi_for, max_frames: int = 0) -> Bore:
    """Walk the clip and keep the widest contiguous pool seen at each row.

    The cut is absolute and only the run that reaches the base is kept: an
    absolute cut avoids a ratio against a bore that is not known yet, and the
    contiguity requirement keeps splash out of the bore.
    """
    rows = ROI[3] - ROI[1]
    max_profile = np.zeros(rows)
    band_max = np.zeros(rows)
    seen = 0
    while True:
        ok, frame = cap.read()
        if not ok or (max_frames and seen >= max_frames):
            break
        seen += 1
        roi = roi_for(frame)
        mask = liquid_mask(frame, roi)
        _accumulate(max_profile, row_widths(mask, roi))
        _accumulate(band_max, band_widths(mask, roi, roi[0] - ROI[0]))
    print(f"pass 1: bore measured over {seen} frames from contiguous pool rows only; "
          f"surface band x={SURFACE_BAND[0]}-{SURFACE_BAND[1]}")
    return Bore(bottle_profile(max_profile), bottle_profile(band_max), seen)


def _accumulate(running: np.ndarray, widths: np.ndarray) -> None:
    """Keep the widest contiguous pool this row has ever shown."""
    top = pool_top_absolute(widths)
    if top is None:
        return
    keep = np.zeros_like(widths)
    keep[top:] = widths[top:]
    k = min(len(keep), len(running))
    running[:k] = np.maximum(running[:k], keep[:k])


def capacity(bore: Bore) -> tuple[np.ndarray, float, int]:
    """The bore extended to the thread line, and the volume it encloses.

    Capacity runs from the base up to the thread line, not up to the fullest
    level ever seen - otherwise a bottle filled to 70% would report 100%. No
    liquid ever reveals the bore above the highest wetted row, so that stretch
    is carried up as a constant. This bottle is a wide-mouth jar whose neck is
    nearly as wide as its body, which makes that a small approximation here; it
    would not be on a bottle with a real taper.
    """
    ref_row = max(THREAD_DATUM_Y - ROI[1], 0)
    cap_prof = bore.profile.copy()
    measured = np.where(cap_prof > 0)[0]
    if len(measured):
        top_measured = int(measured.min())
        # Sampled from the upper body, not from the topmost measured row. At the
        # surface the mask is partial - the topmost bore here is 89 px against an
        # upper-body bore of ~280 - and because volume goes as bore squared,
        # extrapolating with 89 shrank the unfilled neck tenfold and pushed the
        # final reading to 94% of capacity on a bottle that is visibly ~3/4 full.
        lo = min(top_measured + NECK_SAMPLE[0], len(cap_prof) - 1)
        hi = min(top_measured + NECK_SAMPLE[1], len(cap_prof))
        window = cap_prof[lo:hi]
        neck = float(np.median(window[window > 0])) if (window > 0).any() else 0.0
        if top_measured > ref_row and neck > 0:
            print(f"        neck bore extrapolated as {neck:.0f} px "
                  f"(topmost measured was {cap_prof[top_measured]:.0f} px)")
            cap_prof[ref_row:top_measured] = neck
    volume = float(np.sum(np.pi * (cap_prof[ref_row:] / 2.0) ** 2)) or 1.0
    return cap_prof, volume, ref_row
