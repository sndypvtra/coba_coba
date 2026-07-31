"""Zero-shot conveyor counting (cases 1-3).

The detector is given words, never labels and never training data. Objects are
named in plain English, embedded with ``get_text_pe()``, tracked with TrackTrack,
and counted as they cross a line laid perpendicular to the belt's travel.

    from factory_vision.counting import run_case
    summary = run_case("02_tomatoes_conveyor.mp4")
"""

from __future__ import annotations

from factory_vision.counting.clips import CLIPS, ClipConfig
from factory_vision.counting.pipeline import merge_summary, process, run_case

__all__ = ["CLIPS", "ClipConfig", "run_case", "process", "merge_summary"]
