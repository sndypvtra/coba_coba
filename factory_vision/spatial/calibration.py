"""Camera geometry: pixels to the floor, and metres back to pixels.

Everything the 3D case does rests on two operations, and both are exact rather
than learned:

  ground(u, v)   a pixel, assumed to be where an object touches the floor,
                 becomes a point on the floor plane Z=0
  project(X,Y,Z) a point in the building becomes a pixel

The dataset ships the matrices for both. `homography` is the 3x4 camera matrix
with its Z column removed, which is exactly the floor-plane-to-image map, and
inverting it gives the first operation. The second is the camera matrix itself.

Nothing here estimates depth from appearance. A monocular detector cannot tell
how far away something is, but it does not have to: a person standing on a known
floor has one unknown left, and the calibration supplies it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Camera:
    sensor_id: str
    width: int
    height: int
    K: np.ndarray        # 3x3 intrinsics
    R: np.ndarray        # 3x3 world -> camera rotation
    t: np.ndarray        # 3   world -> camera translation
    P: np.ndarray        # 3x4 camera matrix, K [R|t]
    H: np.ndarray        # 3x3 floor plane (Z=0) -> image
    H_inv: np.ndarray
    centre: np.ndarray   # 3   camera position in world metres

    @classmethod
    def from_sensor(cls, s: dict) -> "Camera":
        attrs = {a["name"]: a["value"] for a in s["attributes"]}
        K = np.asarray(s["intrinsicMatrix"], float)
        E = np.asarray(s["extrinsicMatrix"], float)
        P = np.asarray(s["cameraMatrix"], float)
        H = np.asarray(s["homography"], float)
        R, t = E[:, :3], E[:, 3]
        return cls(
            sensor_id=s["id"],
            width=int(float(attrs["frameWidth"])),
            height=int(float(attrs["frameHeight"])),
            K=K, R=R, t=t, P=P, H=H, H_inv=np.linalg.inv(H),
            centre=-R.T @ t,
        )

    # ------------------------------------------------------------------ maps

    def ground(self, u: float, v: float) -> tuple[float, float]:
        """Back-project one image point onto the floor plane."""
        p = self.H_inv @ np.array([u, v, 1.0])
        if abs(p[2]) < 1e-9:          # the ray is parallel to the floor
            return float("nan"), float("nan")
        return float(p[0] / p[2]), float(p[1] / p[2])

    def project(self, pts: np.ndarray) -> np.ndarray:
        """Project world points (N,3) to pixels (N,2). Behind-camera -> NaN."""
        pts = np.atleast_2d(np.asarray(pts, float))
        hom = np.hstack([pts, np.ones((len(pts), 1))]) @ self.P.T
        w = hom[:, 2]
        out = np.full((len(pts), 2), np.nan)
        ok = w > 1e-6
        out[ok] = hom[ok, :2] / w[ok, None]
        return out

    def height_at(self, x: float, y: float, v_top: float) -> float:
        """Height of the vertical line at (x, y) whose top projects to row v_top.

        A person is a vertical segment: feet at (x, y, 0), head at (x, y, h).
        Projecting that segment gives

            v(h) = (a1 + h b1) / (a2 + h b2),   a = P[:, :2] (x, y) + P[:, 3]
                                                b = P[:, 2]

        which is linear in h on both sides once cross-multiplied, so h follows in
        closed form. No search, no assumed stature - the height comes out of the
        box, and a value outside human range is then a useful signal that the box
        was not a whole standing person.
        """
        a = self.P[:, 0] * x + self.P[:, 1] * y + self.P[:, 3]
        b = self.P[:, 2]
        denom = v_top * b[2] - b[1]
        if abs(denom) < 1e-9:
            return float("nan")
        return float((a[1] - v_top * a[2]) / denom)

    def looks_at(self, x: float, y: float, z: float = 0.0) -> bool:
        """Is this world point in front of the camera and inside the frame?"""
        uv = self.project(np.array([[x, y, z]]))[0]
        if not np.isfinite(uv).all():
            return False
        return -50 <= uv[0] <= self.width + 50 and -50 <= uv[1] <= self.height + 50


def box3d_corners(x: float, y: float, h: float, w: float, l: float,
                  yaw: float) -> np.ndarray:
    """Eight corners of an upright box standing on the floor at (x, y).

    Order: 0-3 bottom face anticlockwise, 4-7 the same corners at height h.
    """
    dx, dy = w / 2.0, l / 2.0
    base = np.array([[-dx, -dy], [dx, -dy], [dx, dy], [-dx, dy]])
    c, s = np.cos(yaw), np.sin(yaw)
    rot = base @ np.array([[c, s], [-s, c]])
    ground = np.hstack([rot + [x, y], np.zeros((4, 1))])
    top = ground.copy()
    top[:, 2] = h
    return np.vstack([ground, top])


BOX_EDGES = ((0, 1), (1, 2), (2, 3), (3, 0),
             (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7))


def load_cameras(path: Path) -> dict[str, Camera]:
    data = json.loads(Path(path).read_text())
    return {s["id"]: Camera.from_sensor(s)
            for s in data["sensors"] if s.get("type") == "camera"}
