"""What this project needs before it can run.

Declared rather than fetched inline, so the answer to "what does this case
depend on" is one short file instead of a read of the entry point. The
downloader itself is shared - see `factory_vision/assets.py` - because all six
projects pull from the same three places.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.assets import Clip, Requirements, ensure

NEEDS = Requirements(
    clips=(Clip("01_oranges_production_line.mp4", 10576687),),
    # The detector; the classifier is the tracker's re-identification backbone.
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the MobileCLIP text encoder (~572 MB) is fetched by ultralytics on "
           "the first get_text_pe() call",),
)


def fetch(video_dir: Path, weights_dir: Path) -> bool:
    """Download whatever is missing. False if the project cannot run."""
    return ensure(NEEDS, video_dir, weights_dir)
