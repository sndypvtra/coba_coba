"""The parcel belt, configured twice over - once to count it, once to measure it.

The longest config in the repository, and every constant in it was measured
rather than chosen. The comments carry the measurement, so a number can be
re-derived instead of trusted.

Two objects, because they answer to two different pieces of machinery:

  ``CLIP``    a `ClipConfig`, the same type projects 01 and 02 fill in. Prompts,
              thresholds, the counting line. Nothing in it is metric.
  ``SIZING``  a `SizingConfig`, which exists only here. The depth model's
              resolution, the belt patches, the corridor, both calibration
              scales - everything that stops being meaningful the moment the
              camera moves.

They used to be one object, with the eleven metric fields living in the shared
`ClipConfig` where projects 01 and 02 inherited them and never read one. Keeping
them apart is what lets the shared counter stay honest about being shared.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory_vision.counting import ClipConfig

CLIP = ClipConfig(
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
    conf=0.05,
    min_track_age=4,
    # These are the numbers the geometric gates buy. A detection has to be
    # standing on the belt plane, inside the belt's depth corridor, before
    # the tracker ever sees it - so the tracker's own thresholds no longer
    # have to double as a background filter and can be set for what they are
    # actually for, which is holding an identity.
    #
    # It matters because the old spawn gate was the binding constraint and
    # nothing else was: at the tail of the clip a container detected at 0.65
    # confidence, sitting squarely on the belt, carried no box at all,
    # because 0.20 is the threshold for *starting* a track and three of its
    # neighbours scored 0.05-0.10. Lowering the confidence floor without
    # lowering this one buys nothing.
    tracker_overrides={
        "track_high_thresh": 0.06,
        "track_low_thresh": 0.02,
        "new_track_thresh": 0.07,
        "min_track_len": 2,
    },
    # At the left-hand end of the lane, where the belt is nearest the camera
    # (2.20 m against 2.90 m at the far end) and one image pixel is 1.6 mm on
    # the belt against 2.1 mm. Measuring a parcel where it is best resolved
    # and counting it there is the same decision. Any further left and the
    # trolley handle at x 230-330 starts cutting into the mask.
    line_center=(350, 640),
    line_half_len=260,
    # The belt, measured by optical flow restricted to the belt surface and
    # to features that actually move: the previous (-1.52, 0.08) was taken
    # over the whole frame and was dragged towards zero by the stationary
    # stack, under-reading the speed by a factor of three. A parcel takes
    # 154 frames to cross this view, not 470.
    #
    # Shared by both configs below: it orients the counting line, and it is
    # also how the belt plane learns which way "along" points.
    motion=(-4.69, 0.27),
    line_plumb=True,
    # the full working height of the lane at x=350: below the belt's front
    # edge (y 785) to well above the tallest parcel that rides it
    line_span=(400, 1010),
    scene="Parcel unloading belt - mixed boxes, bags and parcels",
    source_url="https://www.pexels.com/video/unloading-packages-on-a-conveyor-belt-5370836/",
    max_box_area_frac=0.10,
    extra_notes="static stack excluded in depth, not by an x-band",
)


@dataclass
class SizingConfig:
    """Everything metric about this one installation.

    Re-measure all of it if the camera moves, the lens changes or the belt is
    re-sited. None of it transfers to another station, which is exactly why it
    does not live in the shared `ClipConfig`.
    """

    # Run the depth model every Nth frame and carry each track's measurement
    # between runs. Parcels move 4.7 px/frame here, so a value of 5 costs 23 px
    # of travel between measurements - well inside the mask.
    depth_every: int = 5
    # Chosen by the square-pixel test in `intrinsics.py`, not by taste: 392 and
    # 700 px make the camera decoder emit non-square pixels (8 % error), while
    # 518 and 896 land at 0.2-0.4 %.
    depth_process_res: int = 896
    # Bare stretches of belt used to fit the plane, as (x0, x1, y0, y1). Spread
    # across the view on purpose - a plane fitted from one corner extrapolates
    # badly to the other, and parcels are measured at both ends.
    belt_patches: tuple = ()
    # The lane runs 1.87 m where parcels leave frame to 2.90 m where they
    # enter it, but a parcel's *body* reads up to 0.3 m further back than the
    # belt beneath it, so the far bound is the belt's 2.90 plus that - not
    # the belt's own depth. A 2.95 bound rejected three real parcels at the
    # far end, measured at 2.99, 3.00 and 3.11 m. The nearest background is
    # the stack at 3.26 m, which leaves only 0.06 m of room, which is why
    # belt_base_band exists as a second, independent test.
    depth_corridor: tuple[float, float] | None = None
    belt_base_band: tuple[float, float] = (-0.10, 0.15)
    # Freeze a parcel's measured size once its centre passes this x, so the
    # number it is counted with is the one taken where it was best seen.
    size_lock_x: int | None = None
    size_scale: float = 1.0
    size_scale_note: str = ""
    footprint_scale: tuple[float, float] = (1.0, 1.0)
    footprint_scale_note: str = ""


SIZING = SizingConfig(
    depth_every=5,
    depth_process_res=896,
    belt_patches=((150, 380, 705, 745), (880, 1120, 690, 725),
                  (1180, 1450, 678, 715), (1500, 1850, 660, 695)),
    depth_corridor=(1.45, 3.20),
    belt_base_band=(-0.10, 0.15),
    # Freeze each parcel's size 170 px before the line - about 36 frames of
    # travel - so what gets counted is a settled measurement rather than
    # whatever the last frame happened to say.
    size_lock_x=520,
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
    # The footprint's own correction, and the domain it is allowed in.
    #
    # Measured on the same two cartons after size_scale:
    #
    #                       long        short     top face
    #   brown carton     579 -> x1.244  288       10 px
    #   white carton     637 -> x1.130  338       14 px
    #   applied          x1.187         x1.608
    #
    # Both were deep in the regime where this camera cannot resolve a top
    # face at all, so that regime is what the correction describes. Applied
    # to everything it inflated a flat poly bag the camera *had* measured
    # correctly - 444 mm became 527 and the bag jumped from M to L. Applied
    # only where the top face is under-resolved, it puts both 720 mm cartons
    # in L and leaves the bag where it was.
    #
    # Where it does apply it transfers between the two cartons to about
    # +-10 % on the long side and +-16 % on the short, so a parcel measured
    # this way carries a `*` and is not claimed to the millimetre.
    footprint_scale=(1.187, 1.608),
    footprint_scale_note=("applied only where the top face is under-resolved; "
                          "both reference cartons were in that regime, at 10 and 14 px"),
)
