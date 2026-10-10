"""The measurement, per frame, for the dashboard: the same three passes as main.py.

Nothing new is measured here. bore.learn fixes the bottle's bore, level.locate
and level.deflicker give the surface on every frame, and the volume below it is
integrated over the bore. On top of that this file adds what a line needs to
act on: when the bottle is in position, when product starts to flow, the flow
rate, and where the fill is heading.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bore as bore_mod  # noqa: E402
import level  # noqa: E402
from calibration import THREAD_DATUM_Y  # noqa: E402
from profile import liquid_volume  # noqa: E402
from roi import RoiTracker  # noqa: E402
from segmentation import liquid_mask  # noqa: E402

FLOW_START = 0.005          # volume fraction at which the fill counts as started
RATE_WINDOW_S = 1.0         # flow rate over the last second


def measure(video):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    roi_for = RoiTracker(cap)
    bore = bore_mod.learn(cap, roi_for, 0)
    cap_prof, v_bottle, ref_row = bore_mod.capacity(bore)
    empty = len(bore.profile)
    raw = level.locate(cap, roi_for, bore.band_profile, empty, 0)
    surfaces = level.deflicker(raw, empty)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    rows = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        roi = roi_for(frame)
        res = cv2.matchTemplate(frame, roi_for.template, cv2.TM_CCOEFF_NORMED)
        score = float(cv2.minMaxLoc(res)[1])
        s = surfaces[i] if i < len(surfaces) else None
        frac = min(liquid_volume(s, cap_prof) / v_bottle, 1.0) if s is not None else 0.0
        span = max(len(bore.profile) - ref_row, 1)
        hfrac = min((empty - s) / span, 1.0) if s is not None else 0.0
        rows.append({"frame": i + 1, "t": i / fps, "roi": list(roi), "surface_row": s,
                     "surface_y": (roi[1] + s) if s is not None else None,
                     "frac": float(frac), "height_frac": float(hfrac), "match": score})
        i += 1
    cap.release()
    # the bottle is in position once the neck template is found where it belongs
    in_pos = next((r["frame"] for r in rows if r["match"] >= 0.8), None)
    start = next((r["frame"] for r in rows if r["frac"] >= FLOW_START), None)
    n = int(round(RATE_WINDOW_S * fps))
    for k, r in enumerate(rows):
        a = rows[max(0, k - n)]
        dt = r["t"] - a["t"]
        r["rate_frac_s"] = (r["frac"] - a["frac"]) / dt if dt > 0 else 0.0
    # how volume grows with height in this bottle: the reason a level is not a volume
    span = max(empty - ref_row, 1)
    curve = [(min((empty - s) / span, 1.0), min(liquid_volume(s, cap_prof) / v_bottle, 1.0))
             for s in range(empty, ref_row - 1, -4)]
    datum = {"thread_y": THREAD_DATUM_Y, "bore_rows": empty, "ref_row": ref_row,
             "height_volume_curve": [(round(h, 4), round(v, 4)) for h, v in curve]}
    return {"fps": fps, "rows": rows, "in_position": in_pos, "flow_start": start, "datum": datum}


if __name__ == "__main__":
    m = measure(HERE.parent / "input" / "07_bottle_filling_line.mp4")
    rs = m["rows"]
    print("fps", m["fps"], "frames", len(rs), "in position", m["in_position"], "flow start", m["flow_start"])
    for k in (0, 60, 120, 140, 150, 160, 180, 200, 220, 231):
        r = rs[k]
        print(r["frame"], round(r["t"], 2), "match", round(r["match"], 2), "frac", round(r["frac"], 3),
              "h", round(r["height_frac"], 3), "rate %/s", round(100 * r["rate_frac_s"], 1), "y", r["surface_y"])
