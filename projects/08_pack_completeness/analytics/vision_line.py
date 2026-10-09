"""Can line: follow every tray, check its ten slots in the inspection zone, judge it once.

Only pixels go in. A tray is found by its cardboard colour. In the inspection
zone, a band around the middle of the picture where the camera looks straight
at the tray, each of the ten slots is checked for a can lid: a lid is a bright,
grey-white disc, an empty slot shows the brown tray floor. Where the slots are
inside the tray box is measured from this same clip in `calibrate()`, from
trays whose ten lids are all found (Hough circles), so nothing is read from the
render. A tray's verdict is the most common reading over the frames it spent in
the zone, given when it leaves the zone.

Slot names for people: columns 1-5 from the leading edge (the right, where the
tray is heading), row A is the far row, row B the near one.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import cv2
import numpy as np

EXPECTED = 10
COLS, ROWS = 5, 2
ZONE_X = 640                     # centre of the inspection zone, image x
ZONE_HALF = 130                  # the zone is ZONE_X +- this, for the tray centre
BELT_Y = (220, 442)
LID_R = (26, 44)


def tray_boxes(frame_bgr):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (5, 90, 35), (25, 255, 230))
    m[:BELT_Y[0]] = 0
    m[BELT_Y[1]:] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (41, 41)))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    return sorted([[int(x), int(y), int(x + w), int(y + h)] for x, y, w, h, a in st[1:] if a > 4000 and h > 60])


def in_zone(box):
    return abs((box[0] + box[2]) / 2 - ZONE_X) <= ZONE_HALF


def hough_lids(frame_bgr, box):
    g = cv2.medianBlur(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY), 5)
    c = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, 1.2, 50, param1=80, param2=30,
                         minRadius=LID_R[0], maxRadius=LID_R[1])
    if c is None:
        return []
    x0, y0, x1, y1 = box
    return [(float(x), float(y)) for x, y, r in c[0] if x0 - 6 <= x <= x1 + 6 and y0 - 40 <= y <= y1 + 6]


def calibrate(frames):
    """Slot centres relative to the tray box, from in-zone trays with ten lids found."""
    rel = []
    for fr in frames:
        for b in tray_boxes(fr):
            if not in_zone(b):
                continue
            ls = hough_lids(fr, b)
            if len(ls) != EXPECTED:
                continue
            pts = sorted(ls, key=lambda p: p[1])
            far, near = sorted(pts[:5], key=lambda p: -p[0]), sorted(pts[5:], key=lambda p: -p[0])
            one = []
            for c in range(COLS):
                for row in (far, near):
                    x, y = row[c]
                    one.append(((x - b[0]) / (b[2] - b[0]), (y - b[1]) / (b[3] - b[1])))
            rel.append(one)
    return np.median(np.array(rel), axis=0).tolist(), len(rel)


def slot_points(template, box):
    x0, y0, x1, y1 = box
    return [(x0 + u * (x1 - x0), y0 + v * (y1 - y0)) for u, v in template]


def read_slots(hsv, template, box, r=16):
    """True where a lid is seen: most of a small disc at the slot is bright and colourless."""
    out = []
    for x, y in slot_points(template, box):
        xi, yi = int(round(x)), int(round(y))
        patch = hsv[max(0, yi - r):yi + r + 1, max(0, xi - r):xi + r + 1]
        yy, xx = np.mgrid[:patch.shape[0], :patch.shape[1]]
        disc = (yy - (yi - max(0, yi - r))) ** 2 + (xx - (xi - max(0, xi - r))) ** 2 <= r * r
        px = patch[disc]
        lid = np.mean((px[:, 1] < 60) & (px[:, 2] > 120)) if len(px) else 0.0
        out.append(bool(lid > 0.5))
    return out


@dataclass
class Tray:
    key: int
    box: list
    first: int
    readings: list = field(default_factory=list)      # (frame, [10 x bool]) in the zone
    tid: int | None = None                           # tray number, in the order trays reach the zone
    verdict: dict | None = None

    @property
    def live(self):
        """The latest reading while in the zone."""
        return self.readings[-1][1] if self.readings else None


class LineInspector:
    def __init__(self, template):
        self.template = template
        self.trays: list[Tray] = []
        self.done: list[Tray] = []
        self.next_key = 1
        self.next_id = 1
        self.events: list[dict] = []

    def step(self, f, frame_bgr):
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        live = []
        for b in tray_boxes(frame_bgr):
            best, bo = None, 0
            for t in self.trays:
                ov = min(b[2], t.box[2] + 30) - max(b[0], t.box[0])
                if ov > bo and t not in live:
                    best, bo = t, ov
            if best is None:
                best = Tray(self.next_key, b, f)
                self.next_key += 1
            best.box = b
            live.append(best)
        for t in live:
            if in_zone(t.box) and t.verdict is None:
                if t.tid is None:
                    t.tid = self.next_id
                    self.next_id += 1
                t.readings.append((f, read_slots(hsv, self.template, t.box)))
            elif t.readings and t.verdict is None:
                self.judge(t, f)
        for t in self.trays:                     # left the picture before leaving the zone
            if t not in live and t.readings and t.verdict is None:
                self.judge(t, f)
        self.trays = live
        return live

    def judge(self, t, f):
        counts = [sum(r) for _, r in t.readings]
        n = Counter(counts).most_common(1)[0][0]
        votes = np.mean([r for _, r in t.readings], axis=0)
        empty = [k for k in range(EXPECTED) if votes[k] < 0.5]
        t.verdict = {"frame": f, "count": n, "ok": n >= EXPECTED, "empty": empty, "box": list(t.box),
                     "frames_read": len(counts),
                     "agreement": round(counts.count(n) / len(counts), 3)}
        self.done.append(t)
        self.events.append({"frame": f, "tray": t.tid, "kind": "judged", **t.verdict})


def anchored(box, judged_box, width=1280):
    """The tray box at full size: when the frame edge cuts the tray, keep the width it had when judged."""
    w = judged_box[2] - judged_box[0]
    if box[0] > 4 and box[2] < width - 4:
        return box
    if box[0] > 4:
        return [box[0], box[1], box[0] + w, box[3]]
    return [box[2] - w, box[1], box[2], box[3]]


def slot_label(k):
    col, row = divmod(k, ROWS)
    return f"{'AB'[row]}{col + 1}"


def truth_slot(k):
    """This module's slot index to the scene's (near row is the scene's row 0)."""
    col, row = divmod(k, ROWS)
    return col * ROWS + (1 - row)
