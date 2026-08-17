"""The camera nobody calibrated, as predicted by DA3-LARGE's camera decoder.

This is one of the two models the metric chain needs, and it is the weak one.
The belt footage is stock video: no checkerboard, no intrinsics file, no second
camera. DA3-LARGE carries a camera decoder that predicts fx, fy, cx, cy straight
from the image, and that prediction is all there is.

Its error propagates asymmetrically, which is the single most important fact
about this project:

*Distance inherits it.* Metres come out as ``canonical x focal / 300``, so the
focal multiplies the depth directly. A distance is only ever as good as this
estimate, and the estimate moves by about 3 % between processing resolutions.

*Size does not.* A length measured off the image is ``pixels x Z / f``, and Z
already carries a factor of f, so the focal cancels::

    size = pixels_proc * canonical / 300

That is why `sizing.py` survives an intrinsics estimate that is merely
approximate, and why the sizes are calibrated against a carton with its
dimensions printed on the side rather than against the camera.

`square_pixel_error` is the only check available on a number with no ground
truth, and it is a real one: it rejected two processing resolutions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Intrinsics:
    """A pinhole camera, in the pixel units of a given image size."""

    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int

    @classmethod
    def from_matrix(cls, K, width: int, height: int) -> "Intrinsics":
        return cls(float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2]),
                   width, height)

    def scaled_to(self, width: int, height: int) -> "Intrinsics":
        """The same camera expressed at another image size.

        Needed because DA3 works at its processing resolution while the masks
        and the video are at the clip's. Every pixel quantity has to be in one
        of those two frames, never a mix.
        """
        sx, sy = width / self.width, height / self.height
        return Intrinsics(self.fx * sx, self.fy * sy, self.cx * sx, self.cy * sy,
                          width, height)

    @property
    def focal(self) -> float:
        return (self.fx + self.fy) / 2.0

    @property
    def hfov_deg(self) -> float:
        return float(2 * np.degrees(np.arctan(self.width / 2.0 / self.fx)))

    @property
    def square_pixel_error(self) -> float:
        """How far the predicted intrinsics are from square pixels.

        ``fx/W`` and ``fy/H`` must agree once the aspect ratio is divided out.
        When they do not, the camera decoder has produced something no real
        sensor could, and the processing resolution is a poor choice. On this
        clip that check rejects 392 and 700 px - 8 % error - and keeps 518 and
        896, which land at 0.2 and 0.4 %.
        """
        expect = self.fx / self.width * (self.width / self.height)
        return float(abs(self.fy / self.height - expect) / expect)

    def unproject(self, u, v, z):
        """Pixels plus depth into camera-frame 3D points, in metres."""
        u = np.asarray(u, float)
        v = np.asarray(v, float)
        z = np.asarray(z, float)
        return np.stack([(u - self.cx) * z / self.fx,
                         (v - self.cy) * z / self.fy, z], axis=-1)
