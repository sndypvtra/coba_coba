"""Turning a 2D box into a 3D object standing on the floor.

The detector returns a rectangle. What the analytics need is a position in the
building and a height in metres. The bridge is one assumption - *the bottom edge
of the box is where the object meets the floor* - plus the calibration, and
neither of those is a guess about appearance.

From there:

  floor position   back-project the bottom-centre of the box through the
                   ground-plane homography
  height           the closed-form solve in `Camera.height_at`, from the top
                   edge of the same box
  footprint        a constant, because a silhouette does not carry it
  precision        the world size of one image pixel at that floor point -
                   which is what makes a distant, grazing-angle observation
                   count for less than a near, steep-angle one when several
                   cameras disagree

The assumption fails in three ways, and each is handled on its own terms rather
than lumped together: a box clipped by the *bottom* of the frame has no visible
feet, so the floor point is wrong and the observation goes; a box clipped by a
*side* keeps its feet but has its horizontal centre pulled inwards, so it is
kept at reduced weight; a box clipped by the *top* has no visible head, so only
the height is discarded.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from factory_vision.spatial.calibration import Camera

EDGE_MARGIN = 3          # px; a box within this of a frame edge counts as clipped
# How much less a side-clipped observation is trusted. The bias is half the
# missing width, so it grows with how much of the person is off-frame; a flat
# factor is the conservative reading of an unknown amount.
SIDE_CLIP_PENALTY = 3.0


@dataclass
class Observation:
    """One camera's view of one object at one instant, lifted to the floor."""

    camera: str
    track_id: int
    label: str
    conf: float
    box2d: tuple[float, float, float, float]
    x: float = float("nan")
    y: float = float("nan")
    height: float = float("nan")
    precision_m: float = float("nan")   # world metres per image pixel here
    width_m: float = float("nan")     # footprint width read off the box
    height_clipped: bool = False
    side_clipped: bool = False
    reject: str = ""

    @property
    def ok(self) -> bool:
        return not self.reject

    @property
    def weight(self) -> float:
        """How much this observation should count when cameras are averaged.

        Inverse of the local ground-plane scale: a pixel of error near the
        camera is a couple of centimetres on the floor, and the same pixel near
        the horizon is most of a metre. Confidence is folded in as a mild factor
        - it says how sure the detector is that this is an object, not how sure
        it is about where it is.
        """
        if not np.isfinite(self.precision_m) or self.precision_m <= 0:
            return 0.0
        return float(self.conf ** 0.5 / self.precision_m)


def ground_precision(cam: Camera, u: float, v: float) -> float:
    """Metres on the floor spanned by one pixel at (u, v). Bigger is worse."""
    x0, y0 = cam.ground(u, v)
    x1, y1 = cam.ground(u, v + 1.0)
    x2, y2 = cam.ground(u + 1.0, v)
    if not all(np.isfinite([x0, y0, x1, y1, x2, y2])):
        return float("nan")
    return float(max(np.hypot(x1 - x0, y1 - y0), np.hypot(x2 - x0, y2 - y0)))


def lift(cam: Camera, box: np.ndarray, conf: float, label: str, track_id: int,
         valid_bounds: tuple[float, float, float, float],
         height_bounds: tuple[float, float],
         height_reject: bool = True) -> Observation:
    """`height_bounds` is the plausible stature of *this class*, not of people.

    A pallet transporter stands 0.20 m and a person 1.9 m. Sharing one range
    across both classes means every correct transporter detection is thrown away
    for being too short, and every phantom "robot" on a shelf is kept for being
    tall enough - which is exactly what happened before the classes were given
    their own dimensions.
    """
    x1, y1, x2, y2 = [float(v) for v in box]
    obs = Observation(cam.sensor_id, track_id, label, float(conf), (x1, y1, x2, y2))

    # Clipping at the bottom and clipping at the sides are not the same failure,
    # and treating them as one threw away every person standing at the edge of a
    # view - visibly, in tiles where a walking figure carried no box at all.
    # Only the bottom edge destroys the measurement: there the feet are outside
    # the frame and the lowest pixel is not the floor contact. A side clip keeps
    # the feet and only shifts the box's horizontal centre inwards, which is a
    # reason to trust the observation less rather than to discard it - and with
    # several cameras on the same person the unclipped views outvote it.
    if y2 >= cam.height - EDGE_MARGIN:
        obs.reject = "feet below frame"
        return obs
    obs.side_clipped = x1 <= EDGE_MARGIN or x2 >= cam.width - EDGE_MARGIN

    fx, fy = (x1 + x2) / 2.0, y2
    gx, gy = cam.ground(fx, fy)
    if not np.isfinite([gx, gy]).all():
        obs.reject = "ray parallel to floor"
        return obs

    bx0, by0, bx1, by1 = valid_bounds
    if not (bx0 <= gx <= bx1 and by0 <= gy <= by1):
        obs.reject = "off the floor"
        return obs

    obs.x, obs.y = gx, gy
    obs.precision_m = ground_precision(cam, fx, fy) * (
        SIDE_CLIP_PENALTY if obs.side_clipped else 1.0)

    # Footprint width, read rather than assumed. The box's pixel width at the
    # floor point maps to a world width through the same ground-plane scale that
    # gives the position, so the drawn box can hug the person instead of being a
    # constant-size cuboid that visibly misses them. A side-clipped box has lost
    # part of its width and does not get a say.
    if not obs.side_clipped and np.isfinite(obs.precision_m):
        wx0, _ = cam.ground(x1, y2)
        wx1, wy1 = cam.ground(x2, y2)
        if np.isfinite([wx0, wx1]).all():
            obs.width_m = float(np.hypot(wx1 - wx0, wy1 - cam.ground(x1, y2)[1]))

    h = cam.height_at(gx, gy, y1)
    lo, hi = height_bounds
    if y1 <= EDGE_MARGIN:
        # Head cut off by the top of the frame. The floor point is still good,
        # so the observation is kept and only the height is marked unusable.
        obs.height_clipped = True
    elif not np.isfinite(h) or not (lo <= h <= hi):
        # The top edge is visible, so this height is what the box actually says.
        # For a machine or a load that means the box is drawn around the wrong
        # object and the detection goes - it is what stops a "transport robot"
        # box spanning a whole shelving bay from becoming a machine.
        #
        # For a person it means nothing of the sort. A worker bent over a pallet
        # measures a metre and is still standing on their own feet, so the floor
        # point is as good as ever and only the height is unusable. Rejecting on
        # it dropped every crouching person near a camera - visibly, in tiles
        # where someone in plain view carried no box at all.
        if height_reject:
            obs.reject = "height implausible for class"
            return obs
        obs.height_clipped = True
    else:
        obs.height = h
    return obs
