"""How big is that parcel, in millimetres, from one camera.

A detector returns pixels. A pixel is not a size - the same box covers four
times the area at half the distance - so the conversion needs the distance and
the camera's focal length, and it needs them for the object rather than for the
frame::

    size = pixels * distance / focal

`depth.py` supplies both. What is left is the part that makes the number mean
something: pixels of *what*, measured *along which direction*.

Measuring the silhouette's width and height would answer the wrong question. A
carton standing at an angle has a silhouette wider than any of its sides, and a
silhouette taller than the carton whenever the camera can see its lid. The
measurement has to happen in the world, against the surface the parcel is
resting on:

  1. fit the belt once - the camera never moves, so neither does the belt
  2. unproject the parcel's mask into 3D and drop what the mask leaked
  3. height is the extent along the belt's normal, from the belt up
  4. footprint is a minimum-area rectangle in the belt's plane, reported long
     side first

Step 3 is the reliable one: the base is pinned to a plane fitted from tens of
thousands of pixels, and the top edge is against open air.

Step 4 is only sometimes possible, and the pipeline says which. A parcel's
extent *away* from the camera lives on its top face, and this camera rides
488 mm above the belt - 125 mm above a 363 mm carton's lid. At 2.25 m that
carton's 500 mm top face spans **17 pixels**, and no algorithm recovers a depth
extent from 17 pixels. The same camera sees a 110 mm bag's top over 30 px and
measures it correctly.

That difference is why one blanket correction cannot serve both. Scaling every
footprint up by the factor that fixes the cartons inflated a flat bag from a
true ~420 mm to 824 mm and moved it from M to L. So no correction is applied;
instead `ParcelSize.footprint_measurable` reports, per parcel, whether the
camera saw enough to answer, and the size class carries a `+` when it is a
lower bound. The remedy for the cartons is geometric - raise the camera or add
a view across the lane - not algorithmic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from factory_vision.counting.depth import Intrinsics, masked_depth

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
class BeltPlane:
    """The surface parcels ride on, in camera coordinates."""

    point: np.ndarray          # a point on the plane
    up: np.ndarray             # unit normal, pointing away from the belt
    along: np.ndarray          # unit vector, belt travel direction
    across: np.ndarray         # unit vector, completing the frame
    rms_m: float               # plane-fit residual
    samples: int

    def height_of(self, P: np.ndarray) -> np.ndarray:
        return (P - self.point) @ self.up

    def in_plane(self, P: np.ndarray) -> np.ndarray:
        d = P - self.point
        return np.stack([d @ self.along, d @ self.across], axis=-1)

    @property
    def camera_height_m(self) -> float:
        """How far the camera sits above the belt. The camera is the origin."""
        return float(-(self.point @ self.up))


def fit_plane(P: np.ndarray, iters: int = 6) -> tuple[np.ndarray, np.ndarray, float, np.ndarray]:
    """Least-squares plane, re-fitted with outliers trimmed each round."""
    keep = np.ones(len(P), bool)
    centre = P.mean(0)
    normal = np.array([0.0, -1.0, 0.0])
    for _ in range(iters):
        centre = P[keep].mean(0)
        _, _, Vt = np.linalg.svd(P[keep] - centre, full_matrices=False)
        normal = Vt[2]
        r = (P - centre) @ normal
        keep = np.abs(r) < max(2.5 * r[keep].std(), 0.003)
    return centre, normal, float(((P[keep] - centre) @ normal).std()), keep


def bare_belt_depth(depths: list[np.ndarray]) -> np.ndarray:
    """The belt with the traffic removed, from several frames of it.

    There is no frame in this clip where every patch of belt is clear, so a
    plane fitted from any single frame is fitted partly to whatever parcel
    happened to be sitting on it - which tilts the plane and then subtracts that
    tilt from every height measured afterwards. The fix uses the one thing that
    is always true of a parcel: it sits *on* the belt, so it is always nearer
    than the belt it hides. Taking a high percentile of depth per pixel across
    frames therefore returns the belt wherever it was visible at least some of
    the time, and the traffic disappears.
    """
    stack = np.stack(depths, axis=0)
    return np.percentile(stack, 85, axis=0).astype(np.float32)


def fit_belt(depth: np.ndarray, K: Intrinsics, patches, motion) -> BeltPlane:
    """Fit the belt from bare stretches of it, then orient the frame to travel.

    ``patches`` are windows of belt. They are spread across the view on purpose:
    a plane fitted from one corner of the image extrapolates badly to the other,
    and the parcels being measured are at both ends. Pass the output of
    `bare_belt_depth` rather than a single frame's map.
    """
    mask = np.zeros(depth.shape, np.uint8)
    for x0, x1, y0, y1 in patches:
        mask[y0:y1, x0:x1] = 1
    v, u, _ = masked_depth(depth, mask, band=1.5)
    P = K.unproject(u, v, depth[v, u])
    centre, normal, rms, keep = fit_plane(P)

    # Camera y grows downward, so the normal pointing away from the belt is the
    # one with a negative y. Getting this backwards puts every parcel below the
    # belt and every height at zero.
    up = normal if normal[1] < 0 else -normal

    # Travel direction, taken in the world rather than in the image: step along
    # the measured image motion from a point on the belt, land back on the
    # plane, and the difference is where the belt is going in metres.
    cx, cy = K.cx, K.cy
    step = np.array(motion, float)
    step = step / (np.linalg.norm(step) or 1.0) * 60.0
    p0 = _ray_to_plane(cx, cy + 120.0, K, centre, up)
    p1 = _ray_to_plane(cx + step[0], cy + 120.0 + step[1], K, centre, up)
    along = p1 - p0
    along -= (along @ up) * up
    along /= np.linalg.norm(along) or 1.0
    across = np.cross(up, along)
    across /= np.linalg.norm(across) or 1.0
    return BeltPlane(centre, up, along, across, rms, int(keep.sum()))


def _ray_to_plane(u, v, K: Intrinsics, point, normal):
    ray = np.array([(u - K.cx) / K.fx, (v - K.cy) / K.fy, 1.0])
    t = (normal @ point) / (normal @ ray)
    return ray * t


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

        ``+``  the footprint is a lower bound, so the class is too: this parcel
               is *at least* this class and may be larger. It is what an
               under-measured 720 mm carton should say instead of a flat "M".
        ``?``  the longest side sits within the measurement's own uncertainty of
               a class boundary.
        """
        if not self.footprint_measurable and self.longest_m > self.height_m:
            return "+"
        return "" if self.class_certain else "?"


def measure(mask: np.ndarray, depth: np.ndarray, K: Intrinsics, belt: BeltPlane,
            scale: float = 1.0, footprint_scale: tuple[float, float] = (1.0, 1.0),
            min_points: int = 400) -> ParcelSize | None:
    """Measure one parcel from its mask.

    ``scale`` is the single number that turns this from a relative measurement
    into an absolute one. Monocular metric depth carries a scene-wide scale
    error - 18 % on this clip, measured against a carton with its size printed
    on the side - which no amount of geometry removes, because the error is in
    the depth itself. One reference object fixes it for the whole install, which
    is what `clips.py` records and how a real deployment is commissioned.
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

    # `scale` fixes the depth model's global error and applies to all three axes.
    # `footprint_scale` fixes something different and applies only to the two
    # horizontal ones: a single camera sees the front of a parcel and not its
    # back, so the footprint is short by an amount that has nothing to do with
    # depth accuracy. Leaving it uncorrected is not the neutral choice it looks
    # like - it puts a carton that prints 720 mm on its side into the wrong size
    # class, which is a business output, not a rounding error.
    length, width = sorted((float(length) * scale * footprint_scale[0],
                            float(width) * scale * footprint_scale[1]),
                           reverse=True)
    height = float(height) * scale
    # Re-sorted because the two factors differ: on a nearly square footprint the
    # larger correction can overtake the smaller side and print 47 x 49 in a
    # column headed long x short. It renames the pair and changes neither the
    # volume nor the size class, both of which are order-free.

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
    # How many pixels of top face the camera gets across the parcel's depth.
    # See ParcelSize.footprint_measurable for why this decides everything.
    lift = max(belt.camera_height_m - height, 0.0)
    top_face_px = K.fx * lift / max(distance ** 2, 1e-6) * width
    return ParcelSize(
        distance_m=distance,
        length_m=length, width_m=width, height_m=height,
        volume_l=length * width * height * 1000.0,
        points=int(len(v)), mask_kept=kept, base_offset_m=base,
        top_face_px=float(top_face_px), trusted=trusted, notes=notes,
    )


def on_belt(size: "ParcelSize | None", corridor, base_band) -> bool:
    """Is this detection a parcel riding the belt, or is it the furniture?

    The static wall of cartons at the back of this scene is the same colour, the
    same shape and the same size in pixels as the parcels riding past it, so no
    threshold on the image can separate them. Two geometric tests do, and both
    are needed because each one alone lets something through:

    *Depth corridor.* Belt traffic runs 1.9-2.9 m from the camera at the belt
    surface, and a parcel's body reads up to 0.3 m further back than the patch of
    belt beneath it, so the far bound has to sit at 3.2 m rather than at the
    belt's own 2.9 - a 2.95 m bound rejected three real parcels at the far end of
    the lane, measured at 2.99, 3.00 and 3.11 m. The nearest background is the
    stack at 3.26 m, which leaves the bound only 0.06 m of room.

    *Base on the belt plane.* That thin margin is why this second test exists. A
    parcel rests on the belt, so its base sits within a few centimetres of the
    fitted plane; the stack behind stands on the truck floor and reads 0.12 to
    0.84 m off it. The two tests fail on different objects - the corridor catches
    stack cartons whose base happens to land near the plane extended backwards,
    the base test catches whatever the corridor's tight far bound lets through -
    so a detection has to pass both.

    Together they are what makes a 0.05 confidence floor safe: the background is
    rejected on geometry before the tracker ever sees it.
    """
    if size is None:
        return False
    near, far = corridor
    lo, hi = base_band
    return (near <= size.distance_m <= far) and (lo <= size.base_offset_m <= hi)
