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

# 25 fps, unlike the 30 fps conveyor clips.
CLIP = Clip("07_bottle_filling_line.mp4", 8720278, "hd_1920_1080_25fps")

NEEDS = Requirements(
    clips=(CLIP,),
    notes=("the measurement is colour and geometry - no network is downloaded "
           "or run unless --detect asks for the overlay",),
)

# Only `--detect` needs a detector, so only `--detect` fetches one. It used to be
# unconditional, which meant a clean clone pulled 71 MB of weights to run a
# pipeline that never opens them - and contradicted this project's one real
# selling point, that it needs no network at all.
NEEDS_DETECT = Requirements(
    clips=(CLIP,),
    weights=("yoloe-11l-seg.pt",),
    notes=("--detect overlays YOLOE, so the detector is fetched; the "
           "measurement itself still does not use it",),
)


def fetch(video_dir: Path, weights_dir: Path, detect: bool = False) -> bool:
    """Download whatever is missing. False if the project cannot run."""
    return ensure(NEEDS_DETECT if detect else NEEDS, video_dir, weights_dir)
