"""What this project needs before it can run, and which half arrives by itself.

The two halves are treated differently on purpose:

  model weights   fetched automatically. One copy of `yoloe-11l-seg.pt` is the
                  same file as any other, so there is nothing to get wrong and
                  no reason to make anyone do it by hand.
  the source clip fetched by *you*, from the link printed on a first run. It is
                  the thing being measured, and every pixel constant here - the
                  counting line, the box-area limit - was set on one specific
                  rendition of it. Handing that step over means the rendition is
                  chosen deliberately, and it is checked when it arrives.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.assets import Clip, Requirements, ensure, require_clip

CLIP = Clip("01_oranges_production_line.mp4", 10576687, "hd_1920_1080_30fps")
SOURCE_PAGE = "https://www.pexels.com/video/fruit-on-production-line-10576687/"

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
