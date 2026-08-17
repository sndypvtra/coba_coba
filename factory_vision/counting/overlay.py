"""On-frame drawing: colour palette and the live operations panel.

The panel is *data-driven*, and that is a correction rather than a preference.

It used to be written for the parcel belt - the title said PARCEL UNLOADING, the
grid held SIZE MIX and VOLUME RATE and SIZES LOCKED, and the footer named DA3
metric depth. Projects 01 and 02 share this file, so the citrus line rendered a
286-frame video captioned "PARCEL UNLOADING - LIVE", counting "PARCELS", with
five KPIs reading structurally zero and a footer crediting a depth model that
project never loads. A panel that hides the thing being counted is bad; a panel
that *claims a model ran when it did not* is worse, because nothing in the frame
says it is wrong.

So this module now knows how to draw a panel and nothing about what belongs on
one. Each project builds its own `Panel` - see each project's `panel.py` - and
what a project cannot measure, it cannot print.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import supervision as sv

PALETTE = sv.ColorPalette.from_hex(
    ["#FF3B30", "#FF9500", "#FFD60A", "#34C759", "#00C7BE", "#0A84FF", "#BF5AF2", "#FF2D55"]
)

INK = (238, 238, 238)
DIM = (150, 150, 150)
GOOD = (120, 235, 150)
WARM = (120, 200, 255)


@dataclass
class Panel:
    """One frame's worth of dashboard, decided by the project that owns it."""

    title: str                      # "CITRUS SORTING - LIVE"
    headline: str                   # "ORANGES COUNTED"
    subtitle: str = ""              # the small line under the big number
    #: (label, value, colour) - laid out two per row, in order
    rows: list[tuple[str, str, tuple]] = field(default_factory=list)
    #: the small print. Name only what actually ran.
    footer: str = ""

    @property
    def height(self) -> int:
        """Tall enough for the rows it has, and no taller.

        The panel sits over the exit end of the belt, which is also where the
        counting line is, so its height is a constraint rather than a taste: a
        dashboard that hides the moment being counted is worse than no
        dashboard.
        """
        return 224 + 44 * ((len(self.rows) + 1) // 2)


class Hud:
    """Draws a `Panel`. Holds no opinion about what is on it."""

    def __init__(self, cfg, tracker_name: str, model_name: str, total_frames: int):
        self.cfg = cfg
        self.tracker_name = tracker_name
        self.model_name = model_name
        self.total_frames = total_frames

    def draw(self, frame, frame_idx: int, counted: int, panel: Panel, ms: float):
        s = frame.shape[1] / 1920.0
        pad = int(22 * s)
        x0, y0 = int(24 * s), int(24 * s)
        box_w = int(760 * s)
        box_h = int(panel.height * s)

        over = frame.copy()
        cv2.rectangle(over, (x0, y0), (x0 + box_w, y0 + box_h), (14, 15, 18), -1)
        cv2.addWeighted(over, 0.82, frame, 0.18, 0, frame)
        cv2.rectangle(frame, (x0, y0), (x0 + box_w, y0 + box_h), (70, 74, 82),
                      max(1, int(2 * s)))

        def put(text, scale, colour, thick, at, yy):
            cv2.putText(frame, text, (at, yy), cv2.FONT_HERSHEY_SIMPLEX,
                        scale * s, colour, max(1, int(thick * s)), cv2.LINE_AA)

        def rule(yy):
            cv2.line(frame, (x0 + pad, yy), (x0 + box_w - pad, yy),
                     (58, 62, 70), max(1, int(1 * s)))

        xa = x0 + pad
        xb = xa + int(160 * s)          # left column value
        xc = xa + int(390 * s)          # right column label
        xd = xc + int(170 * s)          # right column value

        y = y0 + pad + int(20 * s)
        put(panel.title, 0.58, DIM, 1.4, xa, y)
        y += int(14 * s)
        rule(y)

        y += int(64 * s)
        put(f"{counted}", 2.20, GOOD, 4, xa, y)
        put(panel.headline, 0.62, INK, 2, xc - int(90 * s), y - int(24 * s))
        if panel.subtitle:
            put(panel.subtitle, 0.52, DIM, 1.3, xc - int(90 * s), y)
        y += int(18 * s)
        rule(y)

        # Two per row, left column then right. An odd number of rows leaves the
        # right-hand slot empty rather than stretching the last value across.
        for i in range(0, len(panel.rows), 2):
            y += int(44 * s)
            la, va, ca = panel.rows[i]
            put(la, 0.54, DIM, 1.3, xa, y)
            put(va, 0.68, ca, 2, xb, y)
            if i + 1 < len(panel.rows):
                lb, vb, cb = panel.rows[i + 1]
                put(lb, 0.54, DIM, 1.3, xc, y)
                put(vb, 0.68, cb, 2, xd, y)

        y += int(24 * s)
        rule(y)
        y += int(24 * s)
        if panel.footer:
            put(panel.footer, 0.45, DIM, 1.2, xa, y)
            y += int(22 * s)
        put(f"frame {frame_idx}/{self.total_frames}  ·  {ms:.0f} ms/f  ·  "
            f"{self.model_name} + {self.tracker_name}", 0.45, DIM, 1.2, xa, y)
        return frame
