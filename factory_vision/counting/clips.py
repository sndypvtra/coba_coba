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

    # --- counting line -------------------------------------------------------
    # Snap the line upright instead of taking the normal of the image motion.
    # Correct when the camera has no roll; see build_counting_line.
    line_plumb: bool = False
    # Endpoints in y, source pixels. Overrides line_half_len when set.
    line_span: tuple[int, int] | None = None

    # --- metric depth and sizing --------------------------------------------
    # Off by default: the two other counting clips have no belt plane to fit and
    # nothing to measure against, so they should not pay for a depth model.
    measure_size: bool = False
    # Run the depth model every Nth frame and carry each track's measurement
    # between runs. Parcels move 4.7 px/frame here, so a value of 5 costs 23 px
    # of travel between measurements - well inside the mask.
    depth_every: int = 5
    depth_process_res: int = 896
    # Bare stretches of belt used to fit the plane, as (x0, x1, y0, y1). Spread
    # across the view so the fit does not extrapolate.
    belt_patches: tuple = ()
    # Keep only detections whose median depth falls in this corridor, in metres.
    # This is what replaces the hand-drawn x-band; see sizing.depth_corridor.
    depth_corridor: tuple[float, float] | None = None
    # One number, from one reference object of known size, that turns relative
    # metric depth into absolute. See sizing.measure.
    size_scale: float = 1.0
    size_scale_note: str = ""


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
        # "styrofoam box" is the second instance of the same lesson the holdall
        # taught, found by asking why the last container on the belt carried no
        # box at all. It is not missed by the detector: it scores 0.098 as
        # "parcel", which clears the confidence floor and the depth corridor but
        # never reaches the tracker's new_track_thresh of 0.20, so no track is
        # ever created and the object exists in no output. Naming the material
        # takes the same box from 0.098 to 0.580, clear of every gate.
        #
        #   base prompts                0.098   +0.00 det/frame
        #   + "styrofoam box"           0.580   +0.67   <- adopted
        #   + "cool box"                0.759   +3.44   scores best, too noisy
        #   + "plastic crate"           0.098   +0.00   no effect at all
        prompts=["cardboard box", "parcel", "plastic bag", "sports bag",
                 "styrofoam box"],
        label="package",
        # 0.15 -> 0.08. The old floor was set to keep the static stack of
        # cartons at the back of the shot out of the count, and it paid for that
        # with real traffic: the last cream container scored 0.098 as "parcel",
        # the dark parcel behind it 0.12, the far-right carton 0.10 - all
        # invisible at 0.15. The stack is fenced off in depth now, 1.4 m further
        # back, so the floor can drop without the background flooding in.
        #
        # This does not change the count, and it was never going to: the objects
        # it recovers are at the tail of the clip and none of them completes a
        # crossing before the belt stops. What it changes is whether the belt is
        # fully seen, which is a different question and the one a depot cares
        # about - every parcel now carries a box, an identity and a size.
        conf=0.08,
        min_track_age=4,
        tracker_overrides={
            "track_high_thresh": 0.16,
            "track_low_thresh": 0.04,
            "new_track_thresh": 0.20,
            "min_track_len": 2,
        },
        line_center=(1180, 640),
        line_half_len=260,
        # The belt, measured by optical flow restricted to the belt surface and
        # to features that actually move: the previous (-1.52, 0.08) was taken
        # over the whole frame and was dragged towards zero by the stationary
        # stack, under-reading the speed by a factor of three. A parcel takes
        # 154 frames to cross this view, not 470.
        motion=(-4.69, 0.27),
        line_plumb=True,
        # the full working height of the lane: below the belt surface to well
        # above the tallest parcel that rides it
        line_span=(330, 940),
        scene="Parcel unloading belt - mixed boxes, bags and parcels",
        source_url="https://www.pexels.com/video/unloading-packages-on-a-conveyor-belt-5370836/",
        max_box_area_frac=0.10,
        measure_size=True,
        depth_every=5,
        belt_patches=((150, 380, 705, 745), (880, 1120, 690, 725),
                      (1180, 1450, 678, 715), (1500, 1850, 660, 695)),
        # Measured off the bare-belt depth map, not guessed. The lane runs from
        # 1.87 m where parcels leave frame to 2.90 m where they enter it, and
        # parcels sit on the belt so they are always nearer than that. The
        # nearest background the corridor has to reject is the static stack of
        # cartons at 3.26 m. 2.95 sits in the 0.36 m gap between the two.
        depth_corridor=(1.45, 2.95),
        # Monocular metric depth is scale-accurate to about 20 % and no amount
        # of geometry fixes that, because the error is in the depth itself. One
        # reference object fixes it for the whole install - which is exactly how
        # a dimensioning station is commissioned on site, with a test carton.
        #
        # This clip supplies its own: two cartons print "Ebat/Dimensions
        # 720x500x340 mm" on the side, legible in frame. Both ride flat on the
        # 720x500 face, so their height above the belt is 340 mm - and height is
        # the one dimension a single camera sees whole, base on the fitted plane
        # and top against open air.
        #
        #   calibrate  white carton, 19 frames, height 277.4 mm -> x1.226
        #   validate   brown carton, a different object at a different place and
        #              time, never used to fit the scale: 277.8 mm measured,
        #              which the scale turns into 340.5 mm against a true 340
        #
        # That agreement says the scale *transfers* between objects; it does not
        # say the depth is unbiased, because both cartons are the same model at
        # similar range and any systematic error hits them equally. The spread
        # within a single pass is the honest per-frame error bar: the height
        # wobbles by an IQR of 31 mm (11 %) frame to frame, which is why sizes
        # are reported as a median over the pass and not from one frame.
        size_scale=340.0 / 277.4,
        size_scale_note=("one printed 720x500x340 mm carton (height 277.4 mm measured); "
                         "a second, unseen carton then reads 340.5 mm against 340"),
        extra_notes="static stack excluded in depth, not by an x-band",
    ),
]

