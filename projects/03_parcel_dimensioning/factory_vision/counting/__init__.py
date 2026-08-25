"""Zero-shot conveyor counting (cases 1-3).

The detector is given words, never labels and never training data. Objects are
named in plain English, embedded with ``get_text_pe()``, tracked with TrackTrack,
and counted as they cross a line laid perpendicular to the belt's travel.

    from factory_vision.counting import run_case
    summary = run_case(cfg, video_dir, output_dir)
"""

from __future__ import annotations

from factory_vision.counting.clips import ClipConfig
from factory_vision.counting.measuring import Measurement
from factory_vision.counting.pipeline import process, run_case

__all__ = ["ClipConfig", "Measurement", "run_case", "process"]
