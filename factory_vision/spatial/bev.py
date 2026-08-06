"""The eagle view: one picture of the floor that every camera agrees on.

The dataset ships a top-down render of the building, `map.png`, together with
the two numbers that tie it to world coordinates - a scale in pixels per metre
and a translation in metres. So the eagle view is not a synthetic plan drawing:
it is the actual floor, and a person plotted on it is standing where the
picture says they are standing.

That is the whole argument for doing this in world coordinates. Four cameras
produce four different, incomparable pixel grids; the floor is the one frame in
which "the same person" and "1.4 metres apart" mean anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class GroundMap:
    image: np.ndarray          # the cropped top-down render
    scale: float               # pixels per metre in the *source* map
    tx: float
    ty: float
    crop: tuple[int, int]      # source pixel of the crop's top-left corner
    zoom: float = 1.0          # applied on top of the crop
    pad: tuple[int, int] = (0, 0)   # centring offset when squared off
    # The dataset presents this floor rotated half a turn in its own banner, and
    # that is the picture anyone comparing against the published material has in
    # their head. Matching it costs nothing - the world coordinates are
    # untouched, only which way up the plan is drawn - and reading a plan upside
    # down is exactly the kind of confusion that gets a correct position
    # reported as a bug.
    flip: bool = False

    @classmethod
    def load(cls, map_path: Path, calibration_path: Path,
             bounds_m: tuple[float, float, float, float],
             margin_m: float = 0.7, size: int | None = None,
             flip: bool = False) -> "GroundMap":
        cal = json.loads(Path(calibration_path).read_text())
        sensor = cal["sensors"][0]
        scale = float(sensor["scaleFactor"])
        tx = float(sensor["translationToGlobalCoordinates"]["x"])
        ty = float(sensor["translationToGlobalCoordinates"]["y"])

        img = cv2.imread(str(map_path))
        if img is None:
            raise FileNotFoundError(map_path)
        x0, y0, x1, y1 = bounds_m
        px0 = int(round((x0 - margin_m + tx) * scale))
        py0 = int(round((y0 - margin_m + ty) * scale))
        px1 = int(round((x1 + margin_m + tx) * scale))
        py1 = int(round((y1 + margin_m + ty) * scale))
        px0, py0 = max(px0, 0), max(py0, 0)
        px1, py1 = min(px1, img.shape[1]), min(py1, img.shape[0])
        crop = img[py0:py1, px0:px1].copy()

        zoom, pad = 1.0, (0, 0)
        if size:
            # One scale factor for both axes, then centre the result in a square
            # canvas. Stretching the crop to fill the square instead would make
            # the eagle view anisotropic, and a scale bar on an anisotropic plan
            # is a lie in one of the two directions.
            zoom = size / max(crop.shape[0], crop.shape[1])
            crop = cv2.resize(crop, None, fx=zoom, fy=zoom,
                              interpolation=cv2.INTER_AREA)
            ch, cw = crop.shape[:2]
            canvas = np.zeros((size, size, 3), crop.dtype)
            pad = ((size - cw) // 2, (size - ch) // 2)
            canvas[pad[1]:pad[1] + ch, pad[0]:pad[0] + cw] = crop
            crop = canvas
        if flip:
            crop = cv2.rotate(crop, cv2.ROTATE_180)
        return cls(crop, scale, tx, ty, (px0, py0), zoom, pad, flip)

    # ---------------------------------------------------------------- maps

    def to_px(self, x, y):
        """World metres -> pixel in `image`. Accepts scalars or arrays."""
        u = ((np.asarray(x, float) + self.tx) * self.scale - self.crop[0]) * self.zoom + self.pad[0]
        v = ((np.asarray(y, float) + self.ty) * self.scale - self.crop[1]) * self.zoom + self.pad[1]
        if self.flip:
            h, w = self.image.shape[:2]
            u, v = (w - 1) - u, (h - 1) - v
        return u, v

    def pt(self, x, y) -> tuple[int, int]:
        u, v = self.to_px(x, y)
        return int(round(float(u))), int(round(float(v)))

    def poly(self, polygon_m) -> np.ndarray:
        return np.array([self.pt(x, y) for x, y in polygon_m], np.int32)

    @property
    def px_per_m(self) -> float:
        return self.scale * self.zoom

    @property
    def size(self) -> tuple[int, int]:
        return self.image.shape[1], self.image.shape[0]
