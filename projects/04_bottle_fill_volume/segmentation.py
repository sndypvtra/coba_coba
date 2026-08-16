"""Segmenting product from everything else, and masking to the bottle.

Saturation is the discriminator here, not hue: product in direct view sits at
S 251-255 while the same product seen through the bottle glass sits at S 104-199
with almost the same hue. A hue cut cannot separate them; a saturation cut can.
"""

from __future__ import annotations

import cv2
import numpy as np

from calibration import (BOTTLE_OUTLINE, LIQUID_HI,
                                                LIQUID_LO, LIQUID_LO_SHADOW)


def bottle_silhouette(shape: tuple[int, int]) -> np.ndarray:
    """Boolean mask of the bottle interior, interpolated from BOTTLE_OUTLINE."""
    h, w = shape
    ys = np.array([p[0] for p in BOTTLE_OUTLINE], dtype=float)
    xl = np.array([p[1] for p in BOTTLE_OUTLINE], dtype=float)
    xr = np.array([p[2] for p in BOTTLE_OUTLINE], dtype=float)
    sil = np.zeros((h, w), dtype=bool)
    rows = np.arange(int(ys.min()), min(int(ys.max()) + 1, h))
    left = np.interp(rows, ys, xl).astype(int)
    right = np.interp(rows, ys, xr).astype(int)
    for y, a, b in zip(rows, left, right):
        sil[y, max(a, 0):min(b, w)] = True
    return sil


_SIL_CACHE: dict[tuple[int, int], np.ndarray] = {}


def silhouette_for(shape: tuple[int, int]) -> np.ndarray:
    if shape not in _SIL_CACHE:
        _SIL_CACHE[shape] = bottle_silhouette(shape)
    return _SIL_CACHE[shape]


def liquid_mask(frame: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Segment product inside the ROI, keeping only the base-anchored pool."""
    x1, y1, x2, y2 = roi
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, LIQUID_LO, LIQUID_HI)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

    inside = np.zeros_like(m)
    inside[y1:y2, x1:x2] = m[y1:y2, x1:x2]
    inside[~silhouette_for(m.shape)] = 0   # nothing outside the bottle counts

    # Liquid rests on the base, so keep EVERY component that reaches the lower
    # quarter - not just the largest. The machine's rods and probe cross the
    # bottle and cut the liquid's image into pieces: on the last frame the
    # bottom-left corner was its own 5040 px component and was being thrown away
    # purely for being smaller. A splash clinging high on the shoulder still gets
    # dropped, because it never reaches the base.
    n, lab, stats, _ = cv2.connectedComponentsWithStats((inside > 0).astype(np.uint8), 8)
    if n <= 1:
        return inside
    base_y = y2 - (y2 - y1) // 4
    out = np.zeros_like(inside)
    for i in range(1, n):
        bottom = stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT]
        if bottom >= base_y and stats[i, cv2.CC_STAT_AREA] >= 400:
            out[lab == i] = 255
    return out


def display_mask(frame: np.ndarray, roi: tuple[int, int, int, int],
                 surface: int | None, strict: np.ndarray) -> np.ndarray:
    """Mask for DISPLAY only - closes rod shadows below the measured surface.

    Purely cosmetic, and deliberately fenced in so it cannot influence anything:
    it is confined to rows below the already-measured surface, and only keeps
    relaxed-threshold blobs that touch the strict mask, so product spilled on the
    conveyor is not painted into the bottle. The level and the volume are still
    computed from the strict mask and the bore, untouched by this.

    Needed because the rods and probe crossing the bottle cast shadows that pull
    the product to S 120-185, under the strict S>=200 cut, leaving slivers of
    real liquid unshaded in the demo.
    """
    if surface is None:
        return strict
    x1, y1, x2, y2 = roi
    ysurf = y1 + surface
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, LIQUID_LO_SHADOW, LIQUID_HI)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    band = np.zeros_like(m)
    band[ysurf:y2, x1:x2] = m[ysurf:y2, x1:x2]
    band[~silhouette_for(m.shape)] = 0

    n, lab, _, _ = cv2.connectedComponentsWithStats((band > 0).astype(np.uint8), 8)
    out = strict.copy()
    for i in range(1, n):
        blob = lab == i
        if (blob & (strict > 0)).any():      # must touch measured product
            out[blob] = 255
    return out

