"""Occupancy and dwell-time measurement from a fixed indoor camera (case 5).

People are detected zero-shot, tracked, and two things are reported per frame:
how many are present now, and how long each has been in view.

    from factory_vision.dwell import run_case
    summary = run_case()

Dwell time is a tracking result, not a detection result. The summary carries the
track-continuity figures that say how much to trust it.
"""

from __future__ import annotations

from factory_vision.dwell.config import CLIPS, DwellConfig
from factory_vision.dwell.pipeline import process, run_case

__all__ = ["CLIPS", "DwellConfig", "run_case", "process"]
