"""What this project needs before it can run, and which half arrives by itself.

Compare with `01_citrus_counting/assets.py`: same weights, same encoder, a
different clip id. That is the whole difference between the two cases at every
level except `config.py` and `panel.py`.

  model weights   fetched automatically - one copy of a checkpoint is the same
                  as any other.
  the source clip fetched by *you*, from the link printed on a first run. It is
                  the thing being measured, and this project's counting line and
                  y-ROI were set on one specific rendition of it.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.assets import Clip, Requirements, ensure, require_clip

CLIP = Clip("02_tomatoes_conveyor.mp4", 8675102, "hd_1920_1080_30fps")
SOURCE_PAGE = "https://www.pexels.com/video/tomatoes-on-a-moving-conveyor-belt-8675102/"

NEEDS = Requirements(
    # The detector; the classifier is the tracker's re-identification backbone.
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the MobileCLIP text encoder (~572 MB) is fetched by ultralytics on "
           "the first get_text_pe() call",),
)


def fetch(video_dir: Path, weights_dir: Path) -> bool:
    """Download the weights, check the clip. False if the project cannot run."""
    weights_ok = ensure(NEEDS, video_dir, weights_dir)
    print("\n  source clip (manual)")
    clip_ok = require_clip(CLIP, video_dir, SOURCE_PAGE)
    return weights_ok and clip_ok
