"""Frame regions that mean something other than "an ordinary customer".

Two things have to be kept out of a visitor count, and neither is decidable from
a person's pixels: a wall mirror shows people who are already counted in the
room, and staff work behind a counter. What says "reflection" or "employee" is
*where in a fixed camera's frame* the box sits - so both are declared as
polygons in config.py and resolved here.

That makes the zones per-installation, and a room with neither a mirror nor a
counter in view correctly has none.

Geometry only. How a zone is drawn lives in overlay.py, because the colour a
region is painted is a presentation decision and the region itself is not.
"""

from __future__ import annotations

import cv2
import numpy as np
import supervision as sv

from config import ExclusionZone


def masks_for(zones: list[ExclusionZone], w: int, h: int) -> list[np.ndarray]:
    """One filled binary mask per zone, in frame coordinates."""
    out = []
    for z in zones:
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [np.array(z.polygon, np.int32)], 1)
        out.append(m)
    return out


def hits(det: sv.Detections, zones, masks, w: int, h: int) -> np.ndarray:
    """Index of the first zone each detection falls inside, or -1.

    A detection matches when at least `min_overlap` of its box *area* lies in
    the polygon. Area rather than a single anchor point because both failure
    directions matter: a reflected person sits wholly inside the mirror, while a
    real customer may have only their head poking into it, and any one anchor
    point gets one of those two wrong.
    """
    hit = np.full(len(det), -1, dtype=int)
    for i, box in enumerate(det.xyxy):
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = max(x1, 0), max(y1, 0)
        x2, y2 = min(x2, w), min(y2, h)
        if x2 <= x1 or y2 <= y1:
            continue
        area = float((x2 - x1) * (y2 - y1))
        for zi, (z, m) in enumerate(zip(zones, masks)):
            if float(m[y1:y2, x1:x2].sum()) / area >= z.min_overlap:
                hit[i] = zi
                break
    return hit


def drop_excluded(det: sv.Detections, zones, masks, w: int, h: int):
    """Remove detections inside an "exclude" zone; keep everything else.

    Service regions deliberately do not filter here. Deciding staff-or-customer
    from a single frame's geometry is what let a server slip into the visitor
    count the moment her box reached past the counter edge, so that decision is
    deferred to `roles.classify` once each person has a full track behind them.
    Only mirrors and the like are dropped now, because a reflection must never
    reach the tracker at all.

    Returns the surviving detections plus a per-zone occupancy count for the
    readout panel.
    """
    counted: dict[str, int] = {}
    if not len(det) or not zones:
        return det, counted
    hit = hits(det, zones, masks, w, h)
    for zi, z in enumerate(zones):
        n = int((hit == zi).sum())
        if n:
            counted[z.name] = n
    drop = np.zeros(len(det), dtype=bool)
    for zi, z in enumerate(zones):
        if z.mode != "staff":
            drop |= hit == zi
    return det[~drop], counted


def per_detection_conf(det: sv.Detections, zones, masks, w: int, h: int,
                       room_conf: float) -> np.ndarray:
    """The confidence threshold that applies to each detection.

    A service point in a dark corner can sit far below the threshold that is
    right for the rest of the room, and dropping the room threshold to reach it
    buys those frames at the cost of false positives everywhere else. So one
    inference runs at the lowest threshold any region asks for and the room
    threshold is re-applied here, except inside a zone that sets its own.
    """
    zone_conf = [z.conf for z in zones]
    where = hits(det, zones, masks, w, h)
    return np.array([room_conf if hi < 0 or zone_conf[hi] is None else zone_conf[hi]
                     for hi in where])


def floor_conf(zones: list[ExclusionZone], room_conf: float) -> float:
    """The single threshold to run inference at, given every zone's exception."""
    return min([room_conf] + [z.conf for z in zones if z.conf is not None])


def staff_zone_at(x: int, y: int, zones, masks, w: int, h: int) -> bool:
    """Is this point inside a service polygon?

    Membership for the role vote uses the box *centre* rather than its area. A
    person working behind a counter keeps their centre inside the service
    polygon even when the box spills past the counter edge; an area test loses
    them exactly when they lean in to serve.
    """
    if not (0 <= x < w and 0 <= y < h):
        return False
    for zi, z in enumerate(zones):
        if z.mode == "staff" and masks[zi][y, x]:
            return True
    return False
