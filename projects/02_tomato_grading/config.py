"""The tomato line.

Identical engine to the citrus project next door. The only things that differ
are the words given to the detector and the geometry of the belt - which is the
entire claim of a zero-shot pipeline, made checkable by putting the two side by
side.
"""

from __future__ import annotations

from factory_vision.counting import ClipConfig

CLIP = ClipConfig(
    filename="02_tomatoes_conveyor.mp4",
    prompts=["tomato"],
    label="tomato",
    # the clip that actually responds to tuning: 0.13 -> 0.059 with opened
    # gates cuts median entry lag 0.326 -> 0.203 and more than doubles the
    # share of objects acquired within 15% of the edge (21% -> 50%)
    conf=0.059,
    min_track_age=3,
    tracker_overrides={
        "track_high_thresh": 0.12,
        "track_low_thresh": 0.03,
        "new_track_thresh": 0.15,
        "min_track_len": 2,
    },
    line_center=(1000, 485),
    line_half_len=285,
    # the belt recedes up-and-left, so the line tilts ~9.5 deg off vertical
    # to sit square across the lane rather than parallel to the travel
    motion=(-14.79, -2.47),
    scene="Tomato grading line - roller conveyor close-up",
    source_url="https://www.pexels.com/video/tomatoes-on-a-moving-conveyor-belt-8675102/",
    # the nearest lane sits well outside the depth of field; those tomatoes
    # smear badly and break identity, so counting is restricted to the
    # in-focus lanes via the y-ROI below
    max_box_area_frac=0.06,
    roi_y=(0.0, 0.70),
    extra_notes="counts the in-focus lanes; blurred foreground lane excluded by ROI",
)
