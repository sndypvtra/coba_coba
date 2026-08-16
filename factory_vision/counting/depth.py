"""Metric depth from Depth Anything 3, for a camera nobody calibrated.

The belt footage is stock video. There is no checkerboard, no intrinsics file
and no second camera, so the usual route to metres - calibrate, then triangulate
- is closed. Depth Anything 3 (ByteDance, Nov 2025) opens a different one: it
reads depth straight out of a single image, and it reads it in metres.

It takes two of DA3's models to do that, because they are split by design:

  ``DA3METRIC-LARGE``  a depth head only. Its output is *canonical* metric
                       depth, which is metres divided by the focal length - a
                       scale-free quantity, because a monocular network cannot
                       know whether it is looking at a big thing far away or a
                       small thing near by.
  ``DA3-LARGE``        the geometry model, which carries a camera decoder and
                       predicts the intrinsics the metric head is missing.

Multiplying one by the other is DA3's own recipe, lifted from the nested model's
forward pass (``DepthAnything3Net._apply_metric_scaling``)::

    metres = canonical * (fx + fy) / 2 / 300

Two consequences shape everything downstream, and they pull in opposite
directions:

*Distance inherits the focal's error.* The predicted focal is the weak link -
it moves by 3 % between processing resolutions - and it multiplies the depth
directly, so a reported distance is only ever as good as that estimate.

*Size does not.* A length measured off the image is ``pixels * Z / f``, and
``Z`` already carries a factor of ``f``, so the focal cancels:

    size = pixels_proc * canonical / 300

which is why the sizes in `sizing.py` survive an intrinsics estimate that is
merely approximate, and why they are calibrated against a parcel with its
dimensions printed on the side rather than against the camera.

The camera does not move in this footage, so the intrinsics are solved once on
the first frame and reused.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# DA3's export package imports a Gaussian-splat video writer, a COLMAP binding
# and a mesh library at module scope. None of them are on the inference path
# this pipeline uses, and two of them will not build against a current
# setuptools, so they are stubbed rather than installed.
for _name in ("moviepy", "moviepy.editor", "pycolmap"):
    if _name not in sys.modules:
        _stub = types.ModuleType(_name)
        _stub.__getattr__ = lambda _attr: None
        sys.modules[_name] = _stub
sys.modules["moviepy"].editor = sys.modules["moviepy.editor"]

GEOMETRY_MODEL = "depth-anything/DA3-LARGE"
METRIC_MODEL = "depth-anything/DA3METRIC-LARGE"

# DA3's own constant in `apply_metric_scaling`. It is the canonical focal the
# metric head was trained against, not a tuning knob.
CANONICAL_FOCAL = 300.0


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
        clip that check rejects 392 and 700 px and keeps 518 and 896.
        """
        expect = self.fx / self.width * (self.width / self.height)
        return float(abs(self.fy / self.height - expect) / expect)

    def unproject(self, u, v, z):
        u = np.asarray(u, float)
        v = np.asarray(v, float)
        z = np.asarray(z, float)
        return np.stack([(u - self.cx) * z / self.fx,
                         (v - self.cy) * z / self.fy, z], axis=-1)


class MetricDepth:
    """Depth Anything 3, wired for a fixed camera and returning metres."""

    def __init__(self, process_res: int = 896, threads: int = 4,
                 cache_dir=None):
        import torch

        torch.set_num_threads(threads)
        from depth_anything_3.api import DepthAnything3

        self.process_res = process_res
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.frames_cached = 0
        self._geometry = DepthAnything3.from_pretrained(GEOMETRY_MODEL).eval()
        self._metric = DepthAnything3.from_pretrained(METRIC_MODEL).eval()
        self.intrinsics: Intrinsics | None = None
        self.frames_run = 0

    def solve_intrinsics(self, frames_bgr: list[np.ndarray]) -> Intrinsics:
        """Average the camera decoder over several frames of a static camera.

        One frame is enough in principle. Several are cheap, and the spread
        across them is the only estimate available of how much to trust the
        number - there is no calibration target to check it against.
        """
        mats, sizes = [], None
        for bgr in frames_bgr:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            pred = self._geometry.inference([rgb], process_res=self.process_res,
                                            export_dir=None)
            mats.append(np.asarray(pred.intrinsics)[0])
            sizes = pred.depth[0].shape
        K = np.mean(mats, axis=0)
        spread = float(np.std([m[0, 0] for m in mats]) / K[0, 0]) if len(mats) > 1 else 0.0
        self.intrinsics = Intrinsics.from_matrix(K, sizes[1], sizes[0])
        self.intrinsics_spread = spread
        return self.intrinsics

    def depth(self, bgr: np.ndarray, cache_key: str | None = None) -> np.ndarray:
        """Metric depth in metres, at the frame's own resolution.

        A ``cache_key`` makes the map reusable. On this machine one forward pass
        costs 7 s when the host is quiet and 60 s when it is not, so a 511-frame
        render is anywhere between 25 minutes and two hours - and a container
        restart part-way through threw all of it away once. The maps depend only
        on the frame and the processing resolution, both of which are fixed, so
        caching them makes a re-render for a label or panel change nearly free
        and makes an interrupted run resumable.

        Stored at the processing resolution in float16: 0.9 MB a frame instead
        of 8, and a quantisation step of about 1 mm at these distances, which is
        far below the model's own error.
        """
        if self.intrinsics is None:
            self.solve_intrinsics([bgr])
        h, w = bgr.shape[:2]
        path = self._cache_path(cache_key)
        if path is not None and path.exists():
            self.frames_cached += 1
            return cv2.resize(np.load(path).astype(np.float32), (w, h),
                              interpolation=cv2.INTER_LINEAR)

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pred = self._metric.inference([rgb], process_res=self.process_res,
                                      export_dir=None)
        metres = pred.depth[0] * self.intrinsics.focal / CANONICAL_FOCAL
        self.frames_run += 1
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp.npy")
            np.save(tmp, metres.astype(np.float16))
            tmp.replace(path)        # atomic, so a kill mid-write leaves no stub
        return cv2.resize(metres, (w, h), interpolation=cv2.INTER_LINEAR)

    def _cache_path(self, key: str | None):
        if key is None or self.cache_dir is None:
            return None
        return self.cache_dir / f"{key}_{self.process_res}.npy"


def masked_depth(depth: np.ndarray, mask: np.ndarray,
                 band: float = 0.12) -> tuple[np.ndarray, np.ndarray, float]:
    """Depth samples belonging to one object, with background bled out.

    A detector mask is never exactly the object. It leaks a few pixels of
    whatever is behind, and behind a parcel on this belt is a wall a metre and a
    half further back - so a plain mean over the mask is pulled a long way by a
    small minority of pixels. An object occupies one depth band, so anything
    outside a robust band around the median is not part of it.

    Returns the kept (v, u) coordinates and the fraction of the mask retained;
    a low fraction means the mask and the object disagree, which is worth
    reporting rather than hiding.
    """
    v, u = np.nonzero(mask)
    if len(v) == 0:
        return np.empty(0, int), np.empty(0, int), 0.0
    z = depth[v, u]
    median = float(np.median(z))
    mad = float(np.median(np.abs(z - median))) * 1.4826
    keep = np.abs(z - median) <= max(3.0 * mad, band)
    return v[keep], u[keep], float(keep.mean())
