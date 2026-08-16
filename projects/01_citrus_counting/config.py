"""The citrus line: what to look for, and where the counting line goes.

`motion` is the median per-frame displacement of *tracked objects*, not raw
optical flow - flow on this clip locks onto the rotating rollers rather than the
fruit riding on them.
"""

from __future__ import annotations

from factory_vision.counting import ClipConfig

CLIP = ClipConfig(
    filename="01_oranges_production_line.mp4",
    prompts=["orange", "round orange fruit"],
    label="orange",
    # 0.14 -> 0.095: lifts detections 5.9 -> 7.0/frame and pulls median
    # entry lag 0.303 -> 0.276. Going lower (0.063) barely moved lag again
    # but nearly doubled track count, i.e. fragments not earlier pickups.
    conf=0.095,
    min_track_age=4,
    tracker_overrides={
        "track_high_thresh": 0.16,
        "track_low_thresh": 0.04,
        "new_track_thresh": 0.20,
        "min_track_len": 2,
    },
    line_center=(900, 645),
    line_half_len=385,
    motion=(-3.21, 0.94),  # left, drifting slightly down
    scene="Citrus sorting line - oranges on roller conveyor",
    source_url="https://www.pexels.com/video/fruit-on-production-line-10576687/",
    max_box_area_frac=0.05,
)
