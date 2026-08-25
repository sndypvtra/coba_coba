"""What this project needs before it can run, and which half arrives by itself.

The lightest of the set: by default it runs **no neural network at all**, so by
default it downloads nothing either.

  model weights   only for `--detect`, which overlays YOLOE alongside the
                  measurement to show the detector running. Fetched then and not
                  before - it used to be unconditional, 71 MB of weights for a
                  pipeline that never opens them.
  the source clip fetched by *you*, from the link printed on a first run.

The rendition matters more here than anywhere else in the set. This clip's
default Pexels rendition is 3840x2160, and every one of the eleven constants in
`calibration.py` - the ROI, the thread datum, the bottle outline - is an absolute
pixel coordinate measured on the **1080p 25 fps** one. Getting 4K by accident
would move all of them at once, so the file is checked when it arrives.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.assets import Clip, Requirements, ensure, require_clip

# 25 fps, unlike the 30 fps conveyor clips.
CLIP = Clip("07_bottle_filling_line.mp4", 8720278, "hd_1920_1080_25fps")
SOURCE_PAGE = ("https://www.pexels.com/video/"
               "empty-bottles-in-a-filling-machine-8720278/")

NEEDS = Requirements(
    notes=("the measurement is colour and geometry - no network is downloaded "
           "or run unless --detect asks for the overlay",),
)

NEEDS_DETECT = Requirements(
    weights=("yoloe-11l-seg.pt",),
    notes=("--detect overlays YOLOE, so the detector is fetched; the "
           "measurement itself still does not use it",),
)


def fetch(video_dir: Path, weights_dir: Path, detect: bool = False) -> bool:
    """Download the weights if asked for, check the clip. False if it cannot run."""
    weights_ok = ensure(NEEDS_DETECT if detect else NEEDS, video_dir, weights_dir)
    print("\n  source clip (manual)")
    clip_ok = require_clip(CLIP, video_dir, SOURCE_PAGE)
    return weights_ok and clip_ok
