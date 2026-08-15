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
thousands of pixels, and the top edge is against open air. Step 4 is honest but
weaker - a single camera sees the front of a parcel and not its back, so the
footprint's short side is a lower bound whenever no side face is in view. Both
are reported; only the height is used for calibration, because it is the only
one a single view measures whole.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from factory_vision.counting.depth import Intrinsics, masked_depth

# Longest side a single parcel on an unloading belt can plausibly have. Anything
# past this is a mask that has swallowed its neighbour or a stretch of belt.
MAX_PARCEL_M = 1.00


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
    trusted: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def class_name(self) -> str:
        """The size bucket a parcel hub would sort into, by longest side."""
        longest = max(self.length_m, self.width_m, self.height_m)
        if longest < 0.30:
            return "S"
        if longest < 0.60:
            return "M"
        return "L"


def measure(mask: np.ndarray, depth: np.ndarray, K: Intrinsics, belt: BeltPlane,
            scale: float = 1.0, min_points: int = 400) -> ParcelSize | None:
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

    length, width, height = (float(length) * scale, float(width) * scale,
                             float(height) * scale)

    # Plausibility, against the belt rather than against a guess. A parcel
    # cannot be wider than the lane it rides in, and something measuring a
    # couple of centimetres tall is the belt surface itself caught by a mask
    # that slid off its parcel - both are real failures seen in this clip, and
    # both produce a number that looks like a measurement unless it is checked.
    notes = []
    trusted = True
    if kept < 0.55:
        notes.append("mask disagrees with depth")
        trusted = False
    if abs(base) > 0.06:
        notes.append("base off the belt")
    if height <= 0.02:
        notes.append("no height above belt")
        trusted = False
    if max(length, width) > MAX_PARCEL_M:
        notes.append("wider than the lane")
        trusted = False
    return ParcelSize(
        distance_m=float(np.median(P[:, 2])),
        length_m=length, width_m=width, height_m=height,
        volume_l=length * width * height * 1000.0,
        points=int(len(v)), mask_kept=kept, base_offset_m=base,
        trusted=trusted, notes=notes,
    )


def depth_corridor(depth: np.ndarray, boxes: np.ndarray, near: float, far: float,
                   masks=None) -> np.ndarray:
    """Keep only detections standing inside the belt's depth corridor.

    The static wall of cartons at the back of this scene is the same colour, the
    same shape and the same size in pixels as the parcels riding past it, so no
    threshold on the image can separate them - which is why the old configuration
    had to fence them off with a hand-drawn x-band that also clipped real traffic
    at the same x. In depth they are a metre and a half apart and the separation
    is trivial. This is the filter that lets the confidence floor come down far
    enough to catch the faint parcels without the background flooding in.
    """
    if len(boxes) == 0:
        return np.zeros(0, bool)
    keep = np.zeros(len(boxes), bool)
    H, W = depth.shape
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        if masks is not None and masks[i] is not None and masks[i].sum() > 40:
            v, u, _ = masked_depth(depth, masks[i].astype(np.uint8))
            z = depth[v, u] if len(v) else np.array([np.inf])
        else:
            x1i, y1i = max(int(x1), 0), max(int(y1), 0)
            x2i, y2i = min(int(x2), W - 1), min(int(y2), H - 1)
            patch = depth[y1i:y2i + 1, x1i:x2i + 1]
            z = patch.ravel() if patch.size else np.array([np.inf])
        keep[i] = near <= float(np.median(z)) <= far
    return keep
