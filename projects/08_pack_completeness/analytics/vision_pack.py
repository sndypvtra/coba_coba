"""Packing station: find the boxes, see which of the 20 slots hold a product, catch empty picks.

Only pixels go in. Boxes are the cardboard-coloured regions on the main belt;
products are the blue top panels. Everything that depends on where the camera
is gets measured from the clip itself in `calibrate()`: where a box stands while
it is filled, the 5 x 4 slot grid inside it (from a box seen full), and the
feeder stop. A real line would run this once on installation.

Products only ever go into a box at the station, never come out, and the robot
arm hides part of the box on every trip. So a slot counts as filled once a
product has been seen in it on LATCH frames running, and stays filled until the
box leaves. The robot fills the slots in order; a slot still empty after the
next one has been filled for a while is an empty pick.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

EXPECTED = 20
COLS, ROWS = 5, 4
LATCH = 3                    # frames in a row a product must be seen before it counts
MISS_AFTER = 20              # frames the next slot must be filled before the gap counts as a miss
FEED_WARN = 14               # frames with nothing at the feeder stop while a box still needs products
                             # (a normal cycle leaves it empty for about 9)
BELT_Y = (300, 610)          # main belt band in the image
FEED_Y = (195, 250)          # feeder band


def tan_mask(hsv):
    return cv2.inRange(hsv, (8, 30, 80), (25, 200, 255))


def boxes(hsv):
    m = tan_mask(hsv)
    m[:BELT_Y[0]] = 0
    m[BELT_Y[1]:] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31)))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    return sorted([[int(x), int(y), int(x + w), int(y + h)] for x, y, w, h, a in st[1:]
                   if a > 15000 and w > 120])


def products(hsv, y0=BELT_Y[0], y1=BELT_Y[1]):
    """Centres of blue top panels (front-face bands are thin and left out)."""
    m = cv2.inRange(hsv, (95, 60, 60), (130, 255, 255))
    m[:y0] = 0
    m[y1:] = 0
    n, _, st, c = cv2.connectedComponentsWithStats(m)
    out = []
    for (x, y, w, h, a), (cx, cy) in zip(st[1:], c[1:]):
        if a > 250 and h > 14 and w / h < 2.2 and h / w < 2.2:
            out.append((float(cx), float(cy)))
    return out


@dataclass
class Calibration:
    station_cx: float                 # box centre x while it is filled
    template: list                    # 20 slot centres relative to the box, (u, v) in [0, 1]
    pitch_px: float
    feeder_stop: list                 # x0, y0, x1, y1 of the feeder stop in the image

    def slots(self, box):
        x0, y0, x1, y1 = box
        return [(x0 + u * (x1 - x0), y0 + v * (y1 - y0)) for u, v in self.template]


def calibrate(frames_hsv):
    """Station position, slot grid and feeder stop, from the clip's own pixels."""
    # the station: where fully visible boxes stand still the longest
    centres = []
    for hsv in frames_hsv[::5]:
        for b in boxes(hsv):
            if b[0] > 4 and b[2] < hsv.shape[1] - 4:
                centres.append(round((b[0] + b[2]) / 2 / 4) * 4)
    vals, cnt = np.unique(centres, return_counts=True)
    station = float(vals[np.argmax(cnt)])
    # the grid: boxes at the station with exactly 20 products in them
    rel = []
    for hsv in frames_hsv:
        for b in boxes(hsv):
            if abs((b[0] + b[2]) / 2 - station) > 6:
                continue
            ps = [p for p in products(hsv) if b[0] < p[0] < b[2] and b[1] < p[1] < b[3]]
            if len(ps) != EXPECTED:
                continue
            ps = sorted(ps, key=lambda p: p[1])
            rows = [sorted(ps[r * COLS:(r + 1) * COLS]) for r in range(ROWS)]
            rel.append([((x - b[0]) / (b[2] - b[0]), (y - b[1]) / (b[3] - b[1])) for row in rows for x, y in row])
    tpl = np.median(np.array(rel), axis=0)
    w = np.median([b[2] - b[0] for hsv in frames_hsv[:50] for b in boxes(hsv)
                   if abs((b[0] + b[2]) / 2 - station) < 6])
    pitch = float(np.median(np.diff(tpl[:COLS, 0])) * w)
    # the feeder stop: where products on the feeder band come to rest (largest x they reach)
    xs = [p[0] for hsv in frames_hsv[::3] for p in products(hsv, *FEED_Y)]
    stop_x = float(np.percentile(xs, 99.5))
    return Calibration(station, tpl.tolist(), pitch, [stop_x - 30, FEED_Y[0], stop_x + 25, FEED_Y[1]]), len(rel)


@dataclass
class Box:
    key: int                                         # internal, from the first sighting
    box: list
    first: int
    filled: dict = field(default_factory=dict)       # slot -> frame it was latched
    seen_run: dict = field(default_factory=dict)     # slot -> frames in a row seen
    missed: dict = field(default_factory=dict)       # slot -> frame the miss was called
    arrived: int | None = None                       # first frame at the station
    left: int | None = None                          # frame it started to leave
    start_count: int | None = None                   # products already in when first seen at the station
    verdict: dict | None = None
    bid: int | None = None                           # box number, in the order boxes reach the station

    @property
    def count(self):
        return len(self.filled)


class PackInspector:
    def __init__(self, cal: Calibration):
        self.cal = cal
        self.boxes: list[Box] = []
        self.done: list[Box] = []
        self.next_key = 1
        self.next_id = 1
        self.events: list[dict] = []
        self.feeder: list[bool] = []                 # product at the feeder stop, per frame
        self.feeder_run = 0                          # frames since a product was last at the stop

    def at_station(self, b):
        return abs((b[0] + b[2]) / 2 - self.cal.station_cx) < 6

    def step(self, f, frame_bgr):
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        found = boxes(hsv)
        ps = products(hsv)
        fx0, fy0, fx1, fy1 = (int(v) for v in self.cal.feeder_stop)
        here = any(fx0 <= x <= fx1 for x, _ in products(hsv, fy0, fy1))
        self.feeder.append(here)
        self.feeder_run = 0 if here else self.feeder_run + 1
        live = []
        for b in found:
            best, bo = None, 0
            for t in self.boxes:
                ov = min(b[2], t.box[2] + 40) - max(b[0], t.box[0])
                if ov > bo and t not in live:
                    best, bo = t, ov
            if best is None:
                best = Box(self.next_key, b, f)
                self.next_key += 1
            best.box = b
            live.append(best)
        for t in live:
            if self.at_station(t.box) and t.left is None:
                self.fill(t, f, ps)
            elif t.arrived is not None and t.left is None:
                t.left = f
                self.judge(t, f)
        self.boxes = live
        filling = [t for t in live if t.arrived is not None and t.left is None]
        if (self.feeder_run == FEED_WARN and filling
                and filling[0].count + len(filling[0].missed) < EXPECTED):
            self.events.append({"frame": f, "box": filling[0].bid, "kind": "feeder_gap",
                                "slot": filling[0].count + len(filling[0].missed)})
        return live

    def fill(self, t, f, ps):
        if t.arrived is None:
            t.arrived = f
            t.bid = self.next_id
            self.next_id += 1
        slots = self.cal.slots(t.box)
        r = 0.35 * self.cal.pitch_px
        for k, (sx, sy) in enumerate(slots):
            hit = any(abs(sx - x) < r and abs(sy - y) < r for x, y in ps)
            t.seen_run[k] = t.seen_run.get(k, 0) + 1 if hit else 0
            if k not in t.filled and t.seen_run[k] >= LATCH:
                t.filled[k] = f
                if f > t.arrived + LATCH:
                    self.events.append({"frame": f, "box": t.bid, "slot": k, "kind": "placed"})
        if t.start_count is None and f >= t.arrived + LATCH:
            t.start_count = t.count
        # an empty pick: slot k still empty while a later slot has been filled for MISS_AFTER frames
        if t.filled:
            for k in range(max(t.filled)):
                if k in t.filled or k in t.missed:
                    continue
                later = [fr for s, fr in t.filled.items() if s > k]
                if later and f - min(later) >= MISS_AFTER:
                    t.missed[k] = f
                    self.events.append({"frame": f, "box": t.bid, "slot": k, "kind": "missed",
                                        "feeder_gap": self.feeder_gap(f)})

    def feeder_gap(self, f, look=90):
        """Longest run without a product at the feeder stop in the last `look` frames."""
        run = best = 0
        for v in self.feeder[max(0, f - look):f]:
            run = 0 if v else run + 1
            best = max(best, run)
        return best

    def judge(self, t, f):
        empty = [k for k in range(EXPECTED) if k not in t.filled]
        t.verdict = {"frame": f, "count": t.count, "ok": t.count >= EXPECTED, "empty": empty, "box": list(t.box)}
        self.done.append(t)
        self.events.append({"frame": f, "box": t.bid, "kind": "released", "count": t.count, "empty": empty})


def slot_label(k):
    """Slots as people on the line name them: row A at the back, columns 1-5 from the left."""
    r, c = divmod(k, COLS)
    return f"{'ABCD'[r]}{c + 1}"
