"""What this project needs before it can run.

The only one of the six whose default Pexels rendition is 3840x2160, so the
rendition is pinned by name rather than left to the /download/ endpoint - every
pixel constant in calibration.py is set on the 1080p one, and silently getting
4K would move all of them.

Weights are optional here. The measurement is colour and geometry and needs no
network at all; the detector is only fetched because `--detect` overlays it.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.assets import Clip, Requirements, ensure

NEEDS = Requirements(
    # 25 fps, unlike the 30 fps conveyor clips.
    clips=(Clip("07_bottle_filling_line.mp4", 8720278, "hd_1920_1080_25fps"),),
    weights=("yoloe-11l-seg.pt",),
    notes=("weights are only needed for --detect; the measurement itself is "
           "colour and geometry, no network",),
)


def fetch(video_dir: Path, weights_dir: Path) -> bool:
    """Download whatever is missing. False if the project cannot run."""
    return ensure(NEEDS, video_dir, weights_dir)
