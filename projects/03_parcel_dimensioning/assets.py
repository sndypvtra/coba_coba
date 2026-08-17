"""What this project needs before it can run.

The heaviest of the six to set up, and all of it automatic. Two Depth Anything 3
checkpoints (~2.9 GB) arrive alongside the detector on first run, because metric
depth here is split across two models rather than one:

    DA3METRIC-LARGE   returns *canonical* depth - metres divided by the focal
                      length, which no single image can pin down
    DA3-LARGE         supplies the focal length, from its camera decoder

Multiply the two and the result is metres. They are cached afterwards - by
Hugging Face for the weights, and per-frame by the pipeline in
`output/.depth_cache` - so a second run costs a fraction of the first.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.assets import Clip, Requirements, ensure

NEEDS = Requirements(
    clips=(Clip("03_packages_conveyor.mp4", 5370836),),
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    hub_models=("depth-anything/DA3METRIC-LARGE", "depth-anything/DA3-LARGE"),
    notes=("Depth Anything 3 must be installed separately - see this project's "
           "README; without it, drop the backend= argument in main.py and the "
           "project still counts, exactly as projects 01 and 02 do",),
)


def fetch(video_dir: Path, weights_dir: Path) -> bool:
    """Download whatever is missing. False if the project cannot run."""
    return ensure(NEEDS, video_dir, weights_dir)
