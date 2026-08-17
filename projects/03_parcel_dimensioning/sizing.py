"""How big is that parcel, in millimetres, from one camera.

A detector returns pixels. A pixel is not a size - the same box covers four
times the area at half the distance - so the conversion needs the distance and
the camera's focal length, and it needs them for the object rather than for the
frame::

    size = pixels * distance / focal

`depth.py` and `intrinsics.py` supply both. What is left is the part that makes
the number mean something: pixels of *what*, measured *along which direction*.

Measuring the silhouette's width and height would answer the wrong question. A
carton standing at an angle has a silhouette wider than any of its sides, and a
silhouette taller than the carton whenever the camera can see its lid. The
measurement has to happen in the world, against the surface the parcel is
resting on:

  1. fit the belt once - `belt.py`, and the camera never moves
  2. unproject the parcel's mask into 3D and drop what the mask leaked
  3. height is the extent along the belt's normal, from the belt up
  4. footprint is a minimum-area rectangle in the belt's plane, long side first

Step 3 is the reliable one: the base is pinned to a plane fitted from tens of
thousands of pixels, and the top edge is against open air.

Step 4 is only sometimes possible, and this module says which per parcel. A
parcel's extent *away* from the camera lives on its top face, and this camera
rides 488 mm above the belt - 125 mm above a 363 mm carton's lid. At 2.25 m that
carton's 500 mm top face spans **17 pixels**, and no algorithm recovers a depth
extent from 17 pixels. The same camera sees a 110 mm bag's top over 30 px and
measures it correctly.

That difference decides where the footprint correction may be applied. It was
measured on two cartons whose top faces spanned 10 and 14 px - both deep in the
under-resolved regime - so that regime is what it describes. Applied to
everything it inflated a flat bag the camera had measured correctly, from 444 mm
to 527, and pushed it out of M into L. Applied only where the camera could not
resolve the top face, it puts both 720 mm cartons in L and leaves the bag alone.

So the footprint is either measured or estimated, per parcel, and the size class
says which with a `*`. The real remedy for the tall cartons is geometric - raise
the camera or add a view across the lane - and no constant substitutes for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from belt import BeltPlane
from depth import masked_depth
from intrinsics import Intrinsics

# Longest side a single parcel can plausibly have on *this* belt - an
# installation constant, set from the lane, not a universal truth. The largest
# carton in this scene prints 720 mm on its side and the three real ones measure
# 721, 723 and 726, so 850 leaves 17 % of headroom above anything observed.
#
# What it rejects is the failure this gate exists for: one mask spanning two
# parcels standing shoulder to shoulder. That reads 991 mm long by 347 wide, a
# 2.9:1 sliver no single carton on this belt has, while a real 720 x 500 carton
# reads 1.4:1. The elongation is the tell, and the length bound catches it.
MAX_PARCEL_M = 0.85
# A mask reaching this close to a frame border belongs to an object that is only
# partly in view, so its extent is unmeasurable rather than merely uncertain.
EDGE_MARGIN = 4

# Longest side, in metres, separating S from M and M from L. The ordinary parcel
# boundaries; nothing about this installation moves them.
CLASS_BOUNDS = (0.30, 0.60)
# How wrong a footprint can be even when the camera did see enough of the top
# face to measure it. A class assigned closer than this to a boundary is a coin
# toss dressed up as a measurement.
FOOTPRINT_UNCERTAINTY = 0.10
# Pixels a parcel's top face must span in the depth direction before its
# footprint counts as measured rather than guessed. Below this the far side of
# the parcel is simply not in the image.
TOP_FACE_MIN_PX = 25.0


@dataclass
class ParcelSize:
    """One parcel, measured. Lengths in metres, distance along the camera axis."""

    distance_m: float
    length_m: float            # footprint, long side
    width_m: float             # footprint, short side
    height_m: float            # above the belt
    volume_l: float
    points: int
    mask_kept: float           # share of the mask that survived the depth gate
    base_offset_m: float       # how far the parcel's base sits off the belt
    top_face_px: float = 0.0   # pixels the parcel's top face spans in depth
    footprint_estimated: bool = False  # footprint came via the calibrated correction
    trusted: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def footprint_measurable(self) -> bool:
        """Did the camera see enough of the top face to measure the footprint?

        This is geometry, not a fitted constant. A parcel's extent *away* from
        the camera is only visible on its top face, and that face is
        foreshortened by ``(H - h) / z`` - the camera's height above the parcel
        over its distance. Here H is 488 mm and the cartons are 346-363 mm tall,
        so the camera rides 125 mm above their lids at 2.25 m and their 500 mm
        top faces span **17 to 22 pixels**. There is no algorithm that recovers a
        depth extent from 17 pixels; the information was never captured.

        The same camera sees a 110 mm bag's top face over 30 px and measures it
        fine. That is why one blanket correction could not serve both, and why
        this returns a per-parcel answer instead.
        """
        return self.top_face_px >= TOP_FACE_MIN_PX

    @property
    def longest_m(self) -> float:
        return max(self.length_m, self.width_m, self.height_m)

    @property
    def class_name(self) -> str:
        """The size bucket a parcel hub sorts into, by longest side.

        The boundaries are the ordinary 300 mm and 600 mm ones. They are only
        meaningful because `footprint_scale` has already corrected the
        single-camera footprint bias: without it a 720 mm carton measures 579 and
        lands in M, one side of a boundary that decides how it is handled.
        """
        if self.longest_m < CLASS_BOUNDS[0]:
            return "S"
        if self.longest_m < CLASS_BOUNDS[1]:
            return "M"
        return "L"

    @property
    def class_certain(self) -> bool:
        """Is the parcel far enough from a boundary for the class to mean it?

        A brown carton measured 595 mm against a 600 mm boundary and was
        reported flatly as M. The boundary is not in the wrong place - it is
        that a footprint good to +-10 % cannot resolve five millimetres, and an
        unqualified M claims it can.
        """
        u = FOOTPRINT_UNCERTAINTY * self.longest_m
        return all(abs(self.longest_m - b) > u for b in CLASS_BOUNDS)

    @property
    def class_mark(self) -> str:
        """How much to trust the class, in one character.

        ``?``  the longest side sits within the measurement's own uncertainty
               of a class boundary - the class could go either way.
        ``*``  the camera could not resolve this parcel's top face, so the
               footprint came from the calibrated correction rather than from
               direct measurement. Good to about +-10 %, not to the millimetre.
        """
        if not self.class_certain:
            return "?"
        return "*" if self.footprint_estimated else ""


def measure(mask: np.ndarray, depth: np.ndarray, K: Intrinsics, belt: BeltPlane,
            scale: float = 1.0, footprint_scale: tuple[float, float] = (1.0, 1.0),
            min_points: int = 400) -> ParcelSize | None:
    """Measure one parcel from its mask.

    ``scale`` is the single number that turns this from a relative measurement
    into an absolute one. Monocular metric depth carries a scene-wide scale
    error - 18 % on this clip, measured against a carton with its size printed
    on the side - which no amount of geometry removes, because the error is in
    the depth itself. One reference object fixes it for the whole install, which
    is what `config.py` records and how a real deployment is commissioned.
    """
    v, u, kept = masked_depth(depth, mask)
    if len(v) < min_points:
        return None

    # A parcel still crossing the frame border is only partly in the mask, and a
    # minimum-area rectangle fitted to half an object does not come out half the
    # size - it comes out wrong in a direction that is hard to predict. Such a
    # parcel is tracked and counted as normal; only the measurement is withheld
    # until the whole of it is in view.
    H, W = depth.shape
    clipped = bool(mask[:, :EDGE_MARGIN].any() or mask[:, W - EDGE_MARGIN:].any())

    P = K.unproject(u, v, depth[v, u])

    h = belt.height_of(P)
    base = float(np.percentile(h, 1.0))
    top = float(np.percentile(h, 99.5))
    height = max(top - max(base, 0.0), 0.0)

    plane_xy = belt.in_plane(P).astype(np.float32)
    (_, _), (a, b), _ = cv2.minAreaRect(plane_xy)
    # The parcel's own footprint, long side first - not its extent along the
    # belt axes. Those are different questions once a parcel sits at an angle,
    # and only this one has an answer a depot can use: a carton is 720 x 500
    # whichever way round it was set down, and that is what gets billed.
    #
    # Resolving it the other way needs the rect's rotation, and reading that
    # from OpenCV is a trap worth recording: `minAreaRect` returns the angle in
    # (-90, 0] with the `w` side along it, so a test on cos vs sin of that angle
    # silently swaps the two sides for every parcel rotated past 45 degrees.
    length, width = max(a, b), min(a, b)

    # `scale` is the depth model's global correction and applies to all three
    # axes. Whether `footprint_scale` applies is decided below, from geometry.
    length, width = float(length) * scale, float(width) * scale
    height = float(height) * scale

    # Plausibility, against the belt rather than against a guess. A parcel
    # cannot be wider than the lane it rides in, and something measuring a
    # couple of centimetres tall is the belt surface itself caught by a mask
    # that slid off its parcel - both are real failures seen in this clip, and
    # both produce a number that looks like a measurement unless it is checked.
    notes = []
    trusted = True
    if clipped:
        notes.append("clipped by the frame edge")
        trusted = False
    if kept < 0.55:
        notes.append("mask disagrees with depth")
        trusted = False
    if height <= 0.02:
        notes.append("no height above belt")
        trusted = False
    if max(length, width) > MAX_PARCEL_M:
        notes.append("wider than the lane")
        trusted = False
    distance = float(np.median(P[:, 2]))
    # How many pixels of top face the camera gets across the parcel's depth,
    # measured from what was observed - before any correction, because this is a
    # statement about the image rather than about the parcel.
    lift = max(belt.camera_height_m - height, 0.0)
    top_face_px = float(K.fx * lift / max(distance ** 2, 1e-6) * width)

    # The correction goes on only where it was measured. Both cartons it was
    # fitted to had top faces of 10 and 14 px - deep inside the under-determined
    # regime - so that is the regime it describes. Applying it to a parcel the
    # camera *did* resolve is extrapolation outside its calibration domain, and
    # it showed: a flat poly bag measured correctly at 444 mm was inflated to
    # 527 and pushed out of M into L.
    estimated = top_face_px < TOP_FACE_MIN_PX
    if estimated:
        length, width = length * footprint_scale[0], width * footprint_scale[1]
    # Re-sorted because the two factors differ: on a nearly square footprint the
    # larger correction can overtake the smaller side and print 47 x 49 in a
    # column headed long x short. It renames the pair and changes neither the
    # volume nor the size class, both of which are order-free.
    length, width = max(length, width), min(length, width)

    return ParcelSize(
        distance_m=distance,
        length_m=length, width_m=width, height_m=height,
        volume_l=length * width * height * 1000.0,
        points=int(len(v)), mask_kept=kept, base_offset_m=base,
        top_face_px=float(top_face_px), footprint_estimated=estimated,
        trusted=trusted, notes=notes,
    )


def consensus(sizes) -> ParcelSize | None:
    """One parcel's size, as the median of every frame that measured it.

    A single frame reads short whenever the parcel behind it clips the mask or
    the one in front hides its base. Those failures are one-sided and sporadic,
    so a median over the pass is both steadier and closer to the truth than the
    best single frame - and it is available for free, because the parcel is
    measured on every depth frame it survives.
    """
    if not sizes:
        return None
    med = lambda key: float(np.median([getattr(s, key) for s in sizes]))
    length, width, height = med("length_m"), med("width_m"), med("height_m")
    return ParcelSize(
        distance_m=sizes[-1].distance_m,          # distance is live, not a median
        length_m=length, width_m=width, height_m=height,
        volume_l=length * width * height * 1000.0,
        points=int(np.median([s.points for s in sizes])),
        mask_kept=med("mask_kept"), base_offset_m=med("base_offset_m"),
        top_face_px=med("top_face_px"),
        # `any`, deliberately, and not a median. A parcel whose top face was
        # resolved on only some frames is one the camera could not reliably
        # resolve, and the honest reading is the marked one - a `*` that turns
        # out to be unnecessary costs nothing, an unmarked guess costs the
        # reader their trust in the whole column.
        footprint_estimated=any(x.footprint_estimated for x in sizes),
        trusted=True, notes=[f"median of {len(sizes)} frames"],
    )
