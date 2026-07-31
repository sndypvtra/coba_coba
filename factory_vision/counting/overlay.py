"""On-frame drawing: colour palette and the live counting HUD."""

from __future__ import annotations

import cv2
import supervision as sv

from factory_vision.counting.clips import ClipConfig


PALETTE = sv.ColorPalette.from_hex(
    ["#FF3B30", "#FF9500", "#FFD60A", "#34C759", "#00C7BE", "#0A84FF", "#BF5AF2", "#FF2D55"]
)


class Hud:
    """Translucent stats panel drawn on top of the supervision annotations."""

    def __init__(self, cfg: ClipConfig, tracker_name: str, model_name: str, total_frames: int):
        self.cfg = cfg
        self.tracker_name = tracker_name
        self.model_name = model_name
        self.total_frames = total_frames

    def draw(self, frame, frame_idx, counts, per_class, active, unique_ids, ms, locked=0):
        h, w = frame.shape[:2]
        s = w / 1920.0  # scale everything off a 1080p reference
        pad = int(22 * s)
        line_h = int(34 * s)

        rows = [
            (f"{self.cfg.label.upper()} COUNTED (IN): {counts}", 1.05, (90, 255, 140)),
            (f"scene   : {self.cfg.scene}", 0.62, (235, 235, 235)),
            (f"model   : {self.model_name}  (zero-shot, text prompt)", 0.62, (235, 235, 235)),
            (f"prompts : {', '.join(self.cfg.prompts)}", 0.62, (150, 220, 255)),
            (f"tracker : {self.tracker_name}", 0.62, (235, 235, 235)),
            (
                f"per-class: " + ", ".join(f"{k}={v}" for k, v in per_class.items())
                if per_class
                else "per-class: -",
                0.62,
                (235, 235, 235),
            ),
            (
                f"active tracks: {active}   locked [L]: {locked}"
                f"   unique IDs seen: {unique_ids}",
                0.62,
                (235, 235, 235),
            ),
            (
                f"counting rule: locked >= {self.cfg.min_track_age} frames, then crosses line",
                0.62,
                (150, 220, 255),
            ),
            (
                f"frame {frame_idx}/{self.total_frames}   {ms:.0f} ms/frame",
                0.62,
                (185, 185, 185),
            ),
        ]

        box_w = int(900 * s)
        box_h = pad * 2 + line_h * len(rows)
        overlay = frame.copy()
        cv2.rectangle(overlay, (pad, pad), (pad + box_w, pad + box_h), (18, 18, 18), -1)
        cv2.addWeighted(overlay, 0.62, frame, 0.38, 0, frame)
        cv2.rectangle(frame, (pad, pad), (pad + box_w, pad + box_h), (90, 255, 140), max(1, int(2 * s)))

        y = pad + int(line_h * 0.95)
        for text, scale, color in rows:
            cv2.putText(
                frame,
                text,
                (pad + int(18 * s), y),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale * s * 1.25,
                color,
                max(1, int(2.4 * s)) if scale > 1 else max(1, int(1.6 * s)),
                cv2.LINE_AA,
            )
            y += line_h
        return frame

