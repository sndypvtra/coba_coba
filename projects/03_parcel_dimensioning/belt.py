"""The surface the parcels ride on, and the test for whether they are on it.

Every height in this project is measured against this plane, so it has to be
fitted from the belt and nothing else. Two problems make that harder than it
sounds, and both were real failures on this clip:

*There is no clear frame.* No single frame of this clip has every patch of belt
uncovered, so a plane fitted from one frame is fitted partly to whatever parcel
was sitting on it - which tilts the plane and then subtracts that tilt from
every height measured afterwards. `bare_belt_depth` removes the traffic using
the one thing always true of a parcel: it sits *on* the belt, so it is always
nearer than the belt it hides.

*The background looks identical.* The static wall of cartons at the back of this
scene is the same colour, the same shape and the same size in pixels as the
parcels riding past it. No threshold on the image separates them; two geometric
tests do, and `on_belt` needs both.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from depth import masked_depth
from intrinsics import Intrinsics


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
        """How far the camera sits above the belt. The camera is the origin.

        The sign matters and was wrong once: writing this as ``-(-point) @ up``
        flipped it and made every parcel height come out near zero.
        """
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

    A parcel always sits *on* the belt, so it is always nearer than the belt it
    hides. Taking a high percentile of depth per pixel across frames therefore
    returns the belt wherever it was visible at least some of the time, and the
    traffic disappears.
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


def on_belt(size, corridor, base_band) -> bool:
    """Is this detection a parcel riding the belt, or is it the furniture?

    Two geometric tests, and both are needed because each one alone lets
    something through:

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
