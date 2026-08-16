"""Keeping the measurement window on the bottle.

The ROI is anchored rather than detected per frame, and that is a measured
decision rather than a shortcut. YOLOE does find the bottles (`transparent
bottle`, conf ~0.78) but the boxes are unstable on clear plastic - they wander
194-328 px and swap between neighbouring bottles, which makes a fill time series
meaningless. Template matching shows the bottle itself moves only 7 px across
the whole fill cycle.

So the window is measured once, in calibration.py, and only micro-aligned here
against camera shake.
"""

from __future__ import annotations

import cv2

from calibration import ROI, TEMPLATE_BOX, TEMPLATE_FRAME

# True motion is 7 px, so a match further away than this is a bad one rather
# than a big shake, and is ignored. The early frames hold empty bottles that
# look nothing like the template and would otherwise drag the window off.
MAX_SHAKE_PX = 40
MIN_MATCH_SCORE = 0.5


class RoiTracker:
    """The measurement window for a frame, shake-corrected."""

    def __init__(self, cap: cv2.VideoCapture):
        cap.set(cv2.CAP_PROP_POS_FRAMES, TEMPLATE_FRAME)
        ok, ref = cap.read()
        if not ok:
            raise SystemExit(f"could not read template frame {TEMPLATE_FRAME}")
        x1, y1, x2, y2 = TEMPLATE_BOX
        self.template = ref[y1:y2, x1:x2].copy()
        self.origin = (x1, y1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def __call__(self, frame) -> tuple[int, int, int, int]:
        res = cv2.matchTemplate(frame, self.template, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(res)
        ox, oy = loc[0] - self.origin[0], loc[1] - self.origin[1]
        if score < MIN_MATCH_SCORE or abs(ox) > MAX_SHAKE_PX or abs(oy) > MAX_SHAKE_PX:
            ox = oy = 0
        return (ROI[0] + ox, ROI[1] + oy, ROI[2] + ox, ROI[3] + oy)
