"""Per-clip configuration: what to look for, where the line goes, how it moves.

Everything that differs between cases 1-3 lives here. The pipeline itself is
identical for all three, so a new belt is a new ClipConfig, not new code.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClipConfig:
    """Per-clip settings. Line geometry is in source-video pixels.

    The counting line is not written down as two endpoints. It is built
    perpendicular to ``motion`` - the belt's measured travel direction - and
    then oriented so that travelling along ``motion`` always counts as IN.
    That is the "look at where the conveyor is heading" rule, applied
    automatically instead of hand-placed per clip.
    """

    filename: str
    prompts: list[str]
    label: str  # single display/count label all prompts collapse into
    conf: float
    line_center: tuple[int, int]
    line_half_len: int
    motion: tuple[float, float]  # median px/frame of tracked objects
    scene: str
    source_url: str
    # an object must be held by the tracker this many frames before it is
    # allowed to count - it has to be locked on well before it reaches the line
    min_track_age: int = 6
    # drop boxes whose area exceeds this fraction of the frame (out-of-focus
    # foreground blobs that drift across the lens rather than ride the belt)
    max_box_area_frac: float = 0.12
    min_box_area_frac: float = 0.00035
    extra_notes: str = ""
    roi_x: tuple[float, float] = (0.0, 1.0)  # keep detections inside this x band
    roi_y: tuple[float, float] = (0.0, 1.0)
    # per-clip tracker gate overrides, measured with src/tune_thresholds.py.
    # Opening these lets a track spawn from the weak, partly-cropped detection
    # an object gives off as it enters frame, instead of waiting until it is
    # fully inside. How much they help is clip-specific - see README.
    tracker_overrides: dict = field(default_factory=dict)


# `motion` is the median per-frame displacement of *tracked objects* (not raw
# optical flow, which on these clips locks onto the rotating rollers rather than
# the produce riding on them). Measured over 45-frame samples; see README.
CLIPS: list[ClipConfig] = [
    ClipConfig(
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
    ),
    ClipConfig(
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
    ),
    ClipConfig(
        filename="03_packages_conveyor.mp4",
        # "sports bag" is here because the black holdall on the belt was being
        # missed entirely: against the first three prompts its best overlap with
        # any box was IoU 0.01. It is fabric, so "plastic bag" never matched it.
        # Adding this prompt finds it at conf 0.55 for +0.7 det/frame; a bare
        # "bag" scores marginally higher but adds 2.4 det/frame of loose boxes.
        prompts=["cardboard box", "parcel", "plastic bag", "sports bag"],
        label="package",
        # 0.22 -> 0.15 raises detections 8.4 -> 10.0/frame. Entry lag barely
        # responds here (0.559 -> 0.546) because the metric is dominated by the
        # stationary pallet stack, which is present from frame 1 and never
        # "enters" - belt items are already picked up close to the right edge.
        conf=0.15,
        min_track_age=4,
        tracker_overrides={
            "track_high_thresh": 0.16,
            "track_low_thresh": 0.04,
            "new_track_thresh": 0.20,
            "min_track_len": 2,
        },
        line_center=(1180, 640),
        line_half_len=260,
        # tracked median here is polluted by the stationary stack, so this uses
        # the optical-flow direction for the belt itself: straight left
        motion=(-1.52, 0.08),
        scene="Parcel unloading belt - mixed boxes, bags and parcels",
        source_url="https://www.pexels.com/video/unloading-packages-on-a-conveyor-belt-5370836/",
        max_box_area_frac=0.10,
        # the stationary cage of boxes on the left is not belt traffic
        roi_x=(0.34, 1.0),
        extra_notes="static pallet stack on the left is excluded by ROI",
    ),
]

