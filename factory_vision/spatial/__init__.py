"""Multi-camera spatial analytics: 3D localisation and an eagle view (case 6).

Four fixed warehouse cameras, one floor. People are detected zero-shot, lifted
from image rectangles to positions and heights in metres through each camera's
calibration, fused into one identity per person across the four views, and drawn
back as 3D boxes plus a top-down plot of the building.

    from factory_vision.spatial import run_case
    summary = run_case()

The dataset ships true 3D positions. They are used to *measure* the result and
never as an input - see `validation` in the returned summary.
"""

from __future__ import annotations

from factory_vision.spatial.config import SCENES, SceneConfig
from factory_vision.spatial.pipeline import process, run_case

__all__ = ["SCENES", "SceneConfig", "run_case", "process"]
