"""From mask to measurement: bore profile, liquid surface, volume.

The surface is found by width, not by height. The falling jet is a thin column
~3% of the bore while standing liquid spans it, so the topmost lit pixel tracks
the nozzle rather than the level. Volume integrates the learned bore below the
surface as a stack of discs, so glare or a rod crossing the bottle cannot shrink
the reading - only the surface position matters.
"""

from __future__ import annotations

import numpy as np

from calibration import (BORE_MIN_FRACTION, JET_MAX_WIDTH_PX,
                                                POOL_GAP_TOLERANCE, POOL_MIN_RATIO,
                                                SURFACE_BAND)


def row_widths(mask: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Width of the liquid mask on each row of the ROI, top row first."""
    x1, y1, x2, y2 = roi
    return (mask[y1:y2, x1:x2] > 0).sum(axis=1).astype(float)


def band_widths(mask: np.ndarray, roi: tuple[int, int, int, int],
                dx: int = 0) -> np.ndarray:
    """Row widths within SURFACE_BAND only, used to locate the surface."""
    _, y1, _, y2 = roi
    a, b = SURFACE_BAND[0] + dx, SURFACE_BAND[1] + dx
    return (mask[y1:y2, a:b] > 0).sum(axis=1).astype(float)



def pool_top_absolute(widths: np.ndarray, gap_tol: int = 6) -> int | None:
    """Top of the contiguous pool, using an absolute width cut.

    Used to learn the bore, where no bore is known yet so no ratio test is
    possible. Contiguity is what excludes splash: a turbulent sheet under the
    nozzle can be as wide as the pool, but it is separated from it by a narrow
    band, so a run that must reach the base cannot include it.

    Without this the bore was learned from splash. At the topmost row it
    accepted, the recorded bore was 41 px against a real bore of 282 px - and
    because the ratio test then compared later splashes against that tiny value,
    the surface climbed into the splash region near the end of the fill. Exactly
    the "level jumps to the top and joins the base pool" symptom.
    """
    wide = widths >= JET_MAX_WIDTH_PX
    if not wide.any():
        return None
    y = int(np.where(wide)[0].max())  # lowest wide row = the base
    top, gap = y, 0
    while y >= 0:
        if wide[y]:
            top, gap = y, 0
        else:
            gap += 1
            if gap > gap_tol:
                break
        y -= 1
    return top


def pool_surface(widths: np.ndarray, profile: np.ndarray) -> int | None:
    """Row index of the liquid surface, walking up from the base.

    This is the fix for measuring the *jet* instead of the *level*. Liquid at
    rest spans the full cross-section of the vessel; a stream still falling from
    the nozzle is a thin column. Taking the topmost lit row therefore tracked
    the nozzle, not the surface — on frame 229 that put the line at y=597 (mask
    9 px wide, 3% of the bore) when the real surface was at y=660 (146 px).

    So instead: start at the lowest lit row and climb while each row is at least
    POOL_MIN_RATIO of the bore, tolerating short gaps where a highlight or the
    machine's rod hides the edge. Returns None if no standing liquid is found.
    """
    lit = np.where(widths > 0)[0]
    if len(lit) == 0:
        return None
    # A row with no measured bore cannot qualify. Guarding this matters: the
    # ratio test used max(bore, 1.0), so above the known bore it compared
    # against 1 px and passed on anything, letting the surface climb into rows
    # the liquid had never reached and reporting a datum with bore = 0.
    known = profile > 0
    ref = np.maximum(profile, 1.0)
    y = int(lit.max())  # lowest lit row = the base
    surface, gap = None, 0
    while y >= 0:
        if known[y] and widths[y] >= POOL_MIN_RATIO * ref[y]:
            surface, gap = y, 0
        else:
            gap += 1
            if gap > POOL_GAP_TOLERANCE:
                break
        y -= 1
    return surface


def isotonic_nonincreasing(y: np.ndarray) -> np.ndarray:
    """Best least-squares fit to `y` that never increases (pool-adjacent violators).

    Applied to the surface row over time. A threshold on a single frame cannot
    place the surface stably here: seen at an angle the liquid surface projects
    as an ellipse ~50 rows tall, and inside that band the colour mask is noisy,
    so any cutoff lands on a different row from frame to frame. Sweeping the
    cutoff and the reference did not help - every variant still jumped 50-70
    rows somewhere in the clip.

    The fix comes from physics instead of thresholds: during a fill the level
    only rises, so the row index only decreases. Fitting the closest
    non-increasing curve removes the jumps and the dips at once.

    NOTE this assumes a single monotonic fill of one bottle. It will flatten a
    genuine fall in level - a drained or swapped bottle - so it is wrong for
    footage that is not one fill cycle.
    """
    vals: list[float] = []
    sizes: list[int] = []
    for v in y.astype(float):
        vals.append(v)
        sizes.append(1)
        while len(vals) > 1 and vals[-2] < vals[-1]:
            n1, n2 = sizes[-2], sizes[-1]
            merged = (vals[-2] * n1 + vals[-1] * n2) / (n1 + n2)
            vals.pop(); sizes.pop()
            vals[-1] = merged; sizes[-1] = n1 + n2
    out = np.empty(len(y))
    i = 0
    for v, n in zip(vals, sizes):
        out[i:i + n] = v
        i += n
    return out


def liquid_volume(surface: int | None, profile: np.ndarray) -> float:
    """Volume of liquid below `surface`, integrated as a stack of discs.

    Integration uses the *bore* profile rather than the per-frame mask width.
    Below the surface the bottle is full, so the true cross-section is the bore;
    a mask narrower than that is occlusion or glare, not less liquid. This makes
    the reading depend only on locating the surface, not on a pixel-perfect mask.
    """
    if surface is None:
        return 0.0
    return float(np.sum(np.pi * (profile[surface:] / 2.0) ** 2))


def bottle_profile(observed: np.ndarray) -> np.ndarray:
    """Bore width per row, from what the liquid actually revealed.

    Returns one array - the bore per ROI row, zero where no liquid ever reached.
    Holes inside the wetted body are interpolated, the whole thing is smoothed
    over 15 rows, and rows whose bore is implausibly narrow are trimmed off the
    top (see BORE_MIN_FRACTION).

    Nothing is extrapolated *here*, and that is the point of the split: an
    earlier version reached the unwetted neck up to a hand-read mouth diameter,
    taken from the bottle's outer rim (185 px) while the mask measures the inner
    bore (max 159 px). The neck came out wider than the body - an inverted
    funnel - and the guess covered 60 % of the profile.

    Extending the bore to the capacity datum is a separate decision and lives in
    `bore.capacity`, which carries the neck up from a robust estimate of the
    upper body and says so on the console when it does. Keeping the two apart is
    what stops a measurement and an assumption sharing one array with no way to
    tell which is which.
    """
    prof = observed.copy()
    known = np.where(prof > 0)[0]
    if len(known) == 0:
        return prof
    top = int(known.min())
    idx = np.arange(len(prof))
    body = slice(top, len(prof))
    seg = prof[body]
    holes = seg <= 0
    if holes.any() and (~holes).any():
        seg[holes] = np.interp(idx[body][holes], idx[body][~holes], seg[~holes])
        prof[body] = seg
    k = 15
    sm = np.convolve(prof, np.ones(k) / k, mode="same")
    sm[:top] = 0.0

    # Trim the top of the learned bore where it is implausibly narrow. Even with
    # contiguity, a wave crest can connect to the pool by a thin neck and get
    # recorded as bore - the datum ended up on a row whose "bore" was 41 px
    # against a real bore of 282 px, a tall thin column that both inflated the
    # reference and gave the surface somewhere to climb. A real bottle's bore
    # does not drop below ~30% of its widest point inside the fillable body.
    floor = BORE_MIN_FRACTION * float(sm.max())
    ok = sm >= floor
    if ok.any():
        y = int(np.where(ok)[0].max())
        while y >= 0 and ok[y]:
            y -= 1
        sm[: y + 1] = 0.0
    return sm

