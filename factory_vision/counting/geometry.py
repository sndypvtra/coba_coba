"""Frame geometry: the counting line, the region of interest, size gating."""

from __future__ import annotations

import cv2
import numpy as np
import supervision as sv

from factory_vision.counting.clips import ClipConfig


def build_counting_line(cfg: ClipConfig) -> tuple[sv.Point, sv.Point]:
    """Build a line square across the belt, oriented so travel counts as IN.

    Two steps:

    1. *Perpendicular.* The line runs at 90 deg to ``motion``. A line parallel
       to the travel direction would barely be crossed at all, so orientation
       follows the belt rather than the frame axes.
    2. *Inbound.* supervision counts IN when an object ends up on the side where
       ``Vector.cross_product < 0`` (see ``LineZone._compute_anchor_sides``:
       ``triggers = cross_product(...) < 0`` feeds ``tracker_state``, and
       ``tracker_state`` True increments ``in_count``). Probing one step along
       ``motion`` tells us which endpoint order lands on that side, so every
       clip reports crossings as IN and never OUT.
    """
    cx, cy = cfg.line_center
    mx, my = cfg.motion
    norm = float(np.hypot(mx, my)) or 1.0
    # unit normal to the direction of travel
    px, py = -my / norm, mx / norm
    a = (cx + px * cfg.line_half_len, cy + py * cfg.line_half_len)
    b = (cx - px * cfg.line_half_len, cy - py * cfg.line_half_len)

    # probe a point just past the line, in the direction the belt is heading
    probe = (cx + mx / norm * 40.0, cy + my / norm * 40.0)

    def cross(start, end, pt):
        return (end[0] - start[0]) * (pt[1] - start[1]) - (end[1] - start[1]) * (
            pt[0] - start[0]
        )

    if cross(a, b, probe) >= 0:  # would land on the OUT side -> flip
        a, b = b, a
    return sv.Point(int(a[0]), int(a[1])), sv.Point(int(b[0]), int(b[1]))

def draw_roi(frame, cfg: ClipConfig, w: int, h: int):
    """Outline the counted region when it is narrower than the full frame."""
    if cfg.roi_x == (0.0, 1.0) and cfg.roi_y == (0.0, 1.0):
        return frame
    x1, x2 = int(cfg.roi_x[0] * w), int(cfg.roi_x[1] * w) - 1
    y1, y2 = int(cfg.roi_y[0] * h), int(cfg.roi_y[1] * h) - 1
    color = (255, 190, 90)
    step, gap = int(28 * w / 1920), int(16 * w / 1920)
    t = max(1, int(2 * w / 1920))
    for x in range(x1, x2, step + gap):  # dashed horizontals
        cv2.line(frame, (x, y1), (min(x + step, x2), y1), color, t, cv2.LINE_AA)
        cv2.line(frame, (x, y2), (min(x + step, x2), y2), color, t, cv2.LINE_AA)
    for y in range(y1, y2, step + gap):  # dashed verticals
        cv2.line(frame, (x1, y), (x1, min(y + step, y2)), color, t, cv2.LINE_AA)
        cv2.line(frame, (x2, y), (x2, min(y + step, y2)), color, t, cv2.LINE_AA)
    cv2.putText(
        frame,
        "COUNTING ROI",
        (x1 + int(12 * w / 1920), y1 + int(34 * w / 1920)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7 * w / 1920,
        color,
        max(1, int(2 * w / 1920)),
        cv2.LINE_AA,
    )
    return frame


def filter_detections(det: sv.Detections, cfg: ClipConfig, w: int, h: int) -> sv.Detections:
    """Drop out-of-ROI and implausibly sized boxes before counting."""
    if len(det) == 0:
        return det
    x1, y1, x2, y2 = det.xyxy.T
    area = ((x2 - x1) * (y2 - y1)) / float(w * h)
    cx, cy = (x1 + x2) / 2.0 / w, (y1 + y2) / 2.0 / h
    keep = (
        (area <= cfg.max_box_area_frac)
        & (area >= cfg.min_box_area_frac)
        & (cx >= cfg.roi_x[0])
        & (cx <= cfg.roi_x[1])
        & (cy >= cfg.roi_y[0])
        & (cy <= cfg.roi_y[1])
    )
    return det[keep]

