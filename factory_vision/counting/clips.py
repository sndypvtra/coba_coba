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
    # Keep only detections whose median depth falls in this corridor, in metres,
    # AND whose base sits this far from the fitted belt plane. Both are needed;
    # see sizing.on_belt for what each one catches that the other misses.
    depth_corridor: tuple[float, float] | None = None
    belt_base_band: tuple[float, float] = (-0.10, 0.15)
    # Freeze a parcel's measured size once its centre passes this x, so the
    # number it is counted with is the one taken where it was best seen.
    size_lock_x: int | None = None
    # One number, from one reference object of known size, that turns relative
    # metric depth into absolute. See sizing.measure.
    size_scale: float = 1.0
    size_scale_note: str = ""
    # Corrects the footprint's two horizontal axes only, as (long, short). A
    # separate constant from size_scale because it fixes a different thing: not
    # the depth model's accuracy, but the fact that one camera cannot see the
    # back of a parcel.
    footprint_scale: tuple[float, float] = (1.0, 1.0)
    footprint_scale_note: str = ""
