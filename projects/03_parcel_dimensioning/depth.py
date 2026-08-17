"""Metric depth from Depth Anything 3 - the second of the two models.

Depth Anything 3 (ByteDance, Nov 2025) reads depth out of a single image, and it
reads it in metres. It takes two of DA3's models to do that, because they are
split by design:

  ``DA3METRIC-LARGE``  a depth head only. Its output is *canonical* metric
                       depth, which is metres divided by the focal length - a
                       scale-free quantity, because a monocular network cannot
                       know whether it is looking at a big thing far away or a
                       small thing near by.
  ``DA3-LARGE``        the geometry model, which carries the camera decoder and
                       predicts the focal the metric head is missing. See
                       `intrinsics.py`.

Multiplying one by the other is DA3's own recipe, lifted from the nested model's
forward pass (``DepthAnything3Net._apply_metric_scaling``)::

    metres = canonical * (fx + fy) / 2 / 300

``CANONICAL_FOCAL`` below is that 300. It is the focal the metric head was
trained against, not a tuning knob.

The camera does not move in this footage, so the intrinsics are solved once and
reused for the whole clip.
"""

from __future__ import annotations

import sys
import types

import cv2
import numpy as np

from depth_cache import DepthCache
from intrinsics import Intrinsics

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

# DA3's own constant in `apply_metric_scaling`.
CANONICAL_FOCAL = 300.0


class MetricDepth:
    """Depth Anything 3, wired for a fixed camera and returning metres."""

    def __init__(self, process_res: int = 896, threads: int = 4, cache_dir=None):
        import torch

        torch.set_num_threads(threads)
        from depth_anything_3.api import DepthAnything3

        self.process_res = process_res
        self.cache = DepthCache(cache_dir, process_res)
        self._geometry = DepthAnything3.from_pretrained(GEOMETRY_MODEL).eval()
        self._metric = DepthAnything3.from_pretrained(METRIC_MODEL).eval()
        self.intrinsics: Intrinsics | None = None
        self.intrinsics_spread = 0.0
        self.frames_run = 0

    @property
    def frames_cached(self) -> int:
        return self.cache.hits

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
        """Metric depth in metres, at the frame's own resolution."""
        if self.intrinsics is None:
            self.solve_intrinsics([bgr])
        h, w = bgr.shape[:2]

        stored = self.cache.load(cache_key)
        if stored is not None:
            return cv2.resize(stored, (w, h), interpolation=cv2.INTER_LINEAR)

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pred = self._metric.inference([rgb], process_res=self.process_res,
                                      export_dir=None)
        metres = pred.depth[0] * self.intrinsics.focal / CANONICAL_FOCAL
        self.frames_run += 1
        self.cache.store(cache_key, metres)
        # Quantised the same way the cache stores it, so the run that *computes*
        # a map measures the same numbers as every run that later *reads* it.
        # Returning float32 here while storing float16 made a first run disagree
        # with all of its own successors, which is a difference this pipeline can
        # remove and should.
        #
        # It does NOT make two independent runs agree, and it would be wrong to
        # read it that way. DA3 is bit-identical within one process but not
        # across processes: its output moves by ~1e-6 canonical units, far below
        # anything physical - and float16 then rounds those wobbles to +/-1 step,
        # which is 2-8 mm at these ranges. Two cold runs of this clip agreed on
        # every map to a median of exactly zero and a p99 of 3.9 mm, and that was
        # enough to move parcel dimensions by up to 5 mm. See the README's
        # note on run-to-run tolerance.
        metres = metres.astype(np.float16).astype(np.float32)
        return cv2.resize(metres, (w, h), interpolation=cv2.INTER_LINEAR)


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
