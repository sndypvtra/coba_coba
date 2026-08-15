"""On-frame drawing: colour palette and the live operations panel."""

from __future__ import annotations

import cv2
import supervision as sv

from factory_vision.counting.clips import ClipConfig


PALETTE = sv.ColorPalette.from_hex(
    ["#FF3B30", "#FF9500", "#FFD60A", "#34C759", "#00C7BE", "#0A84FF", "#BF5AF2", "#FF2D55"]
)

INK = (238, 238, 238)
DIM = (150, 150, 150)
GOOD = (120, 235, 150)
WARM = (120, 200, 255)


class Hud:
    """What a depot supervisor would want on the wall, and nothing else.

    The panel this replaced listed the model name, the prompt list, the tracker
    name, the active track count and the counting rule. All of that is true and
    none of it is a decision: nobody staffs a shift differently because the
    tracker is TrackTrack. It belongs in `summary.json`, where it is, and in the
    footer line here, once, small.

    What replaces it is the set of numbers a parcel operation actually runs on:
    rate, volume rate, headway, size mix, and what is on the belt right now.
    Rates are extrapolated from a short clip, so they are drawn as rates and
    labelled `/h`, with the observed counts they come from directly beneath -
    an extrapolation presented without its sample size is how a demo becomes a
    promise nobody can keep.
    """

    def __init__(self, cfg: ClipConfig, tracker_name: str, model_name: str, total_frames: int):
        self.cfg = cfg
        self.tracker_name = tracker_name
        self.model_name = model_name
        self.total_frames = total_frames

    def draw(self, frame, frame_idx, counted, ops, ms):
        """Two columns, and short enough to clear the lane.

        The panel sits over the exit end of the belt, which is also where the
        counting line is, so its height is a constraint rather than a taste: a
        dashboard that hides the moment being counted is worse than no
        dashboard. Seven KPIs in two columns end above the tallest parcel that
        passes underneath.
        """
        s = frame.shape[1] / 1920.0
        big = ops["largest"]
        mix = ops["mix"]
        grid = [
            ("THROUGHPUT", f"{ops['per_hour']:,.0f} /h", WARM,
             "SIZE MIX", f"S{mix.get('S', 0)}  M{mix.get('M', 0)}  L{mix.get('L', 0)}", INK),
            ("VOLUME RATE", f"{ops['m3_per_hour']:.1f} m3/h", WARM,
             "MEAN PARCEL", f"{ops['mean_volume_l']:.0f} L", INK),
            ("HEADWAY", f"{ops['headway_s']:.1f} s" if ops["headway_s"] else "-", WARM,
             "LARGEST",
             f"{big.length_m*100:.0f}x{big.width_m*100:.0f}x{big.height_m*100:.0f}"
             if big else "-", INK),
            ("ON BELT NOW", f"{ops['on_belt']}  ·  {ops['on_belt_l']:.0f} L", INK,
             "SIZES LOCKED", f"{ops['locked']}", INK),
        ]

        pad = int(22 * s)
        x0, y0 = int(24 * s), int(24 * s)
        box_w = int(760 * s)
        box_h = int(392 * s)

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
        put("PARCEL UNLOADING - LIVE", 0.58, DIM, 1.4, xa, y)
        y += int(14 * s)
        rule(y)

        y += int(64 * s)
        put(f"{counted}", 2.20, GOOD, 4, xa, y)
        put("PARCELS COUNTED", 0.62, INK, 2, xc - int(90 * s), y - int(24 * s))
        put(f"{ops['elapsed_s']:.1f} s  ·  {ops['volume_l']:.0f} L handled",
            0.52, DIM, 1.3, xc - int(90 * s), y)
        y += int(18 * s)
        rule(y)

        for la, va, ca, lb, vb, cb in grid:
            y += int(44 * s)
            put(la, 0.54, DIM, 1.3, xa, y)
            put(va, 0.68, ca, 2, xb, y)
            put(lb, 0.54, DIM, 1.3, xc, y)
            put(vb, 0.68, cb, 2, xd, y)

        y += int(24 * s)
        rule(y)
        y += int(24 * s)
        put(f"sizes frozen before the line  ·  rates extrapolated from "
            f"{ops['elapsed_s']:.0f} s", 0.45, DIM, 1.2, xa, y)
        y += int(22 * s)
        put(f"frame {frame_idx}/{self.total_frames}  ·  {ms:.0f} ms/f  ·  "
            f"{self.model_name} + DA3 metric depth", 0.45, DIM, 1.2, xa, y)
        return frame
