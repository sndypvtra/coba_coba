"""What this project needs before it can run.

Compare with `01_citrus_counting/assets.py`: same weights, same encoder, a
different clip id. That is the whole difference between the two cases at every
level except `config.py`.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.assets import Clip, Requirements, ensure

NEEDS = Requirements(
    clips=(Clip("02_tomatoes_conveyor.mp4", 8675102),),
    # The detector; the classifier is the tracker's re-identification backbone.
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the MobileCLIP text encoder (~572 MB) is fetched by ultralytics on "
           "the first get_text_pe() call",),
)


def fetch(video_dir: Path, weights_dir: Path) -> bool:
    """Download whatever is missing. False if the project cannot run."""
    return ensure(NEEDS, video_dir, weights_dir)
