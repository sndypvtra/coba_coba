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

    # --- measuring, if this installation does any -----------------------------
    # Deliberately NOT a set of size fields. Everything metric - the depth
    # model's resolution, the belt patches, the corridor, both calibration
    # scales - belongs to the project that measures, and lives there:
    # `projects/03_parcel_dimensioning/config.py`.
    #
    # Those eleven fields used to sit here, and two of this class's three users
    # never read one of them. A config that describes a belt plane to a project
    # counting oranges is not a shared config, it is one project's config with
    # the others tolerated in it. The measurement now arrives as a backend
    # object instead - see `measuring.Measurement` - so the presence of a
    # measurement is a structural fact rather than a flag defaulting to False.
