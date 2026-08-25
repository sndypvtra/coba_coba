"""What this project needs before it can run, and which parts arrive by itself.

The heaviest of the set. Three kinds of dependency, treated three ways:

  model weights   fetched automatically - the detector, plus two Depth Anything 3
                  checkpoints (~2.9 GB) from the Hugging Face hub. Metric depth
                  here is split across two models rather than one:

                      DA3METRIC-LARGE   canonical depth - metres divided by the
                                        focal length, which no single image pins
                      DA3-LARGE         that focal length, from its camera decoder

                  Multiply the two and the result is metres.
  the source clip fetched by *you*, from the link printed on a first run. Every
                  metric constant in `config.py` - the belt patches, the depth
                  corridor, the lock line - was measured on one rendition of it.
  Depth Anything 3 itself, the Python package, which no `main.py` can install.
                  Checked before anything downloads; see DA3_INSTALL below.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.assets import Clip, Requirements, ensure, require_clip

CLIP = Clip("03_packages_conveyor.mp4", 5370836, "hd_1920_1080_30fps")
SOURCE_PAGE = ("https://www.pexels.com/video/"
               "unloading-packages-on-a-conveyor-belt-5370836/")
DETECTOR = ("yoloe-11l-seg.pt", "yolo11n-cls.pt")

NEEDS = Requirements(
    weights=DETECTOR,
    hub_models=("depth-anything/DA3METRIC-LARGE", "depth-anything/DA3-LARGE"),
)

# `--count-only` runs the shared counter with no measurement at all. It must not
# fetch the depth checkpoints: 2.9 GB for models the run will never open.
NEEDS_COUNT_ONLY = Requirements(weights=DETECTOR,
                                notes=("--count-only: the depth checkpoints are "
                                       "not fetched and no size is reported",))

# The one dependency no `main.py` can install for you. Printed verbatim when it is
# missing, because a `ModuleNotFoundError` raised inside a model constructor -
# after a 2.9 GB download - is not an error message, it is a puzzle.
DA3_INSTALL = """\
  Depth Anything 3 is not installed, and it is the one thing this project cannot
  fetch for you. It has to go in WITHOUT its dependency list: upstream pins
  numpy<2 and pulls opencv-python, xformers and open3d, which between them would
  downgrade numpy and OpenCV out from under the rest of this project.

      pip install --pre "omegaconf>=2.4.0.dev0"
      pip install --no-deps addict einops plyfile trimesh
      git clone --depth 1 https://github.com/ByteDance-Seed/depth-anything-3
      pip install --no-deps -e depth-anything-3

  Or watch the counter run without it - but read what that costs first:

      python main.py --count-only

  On this clip that counts 10 against a verified 8, because the depth corridor
  is also what fences off the static stack of cartons at the back, and the
  confidence floor was set assuming it is there.
"""


def depth_installed() -> bool:
    """Is Depth Anything 3 importable? Checked before anything is downloaded."""
    from importlib.util import find_spec

    try:
        return find_spec("depth_anything_3") is not None
    except (ImportError, ValueError):
        return False


def fetch(video_dir: Path, weights_dir: Path, with_depth: bool = True) -> bool:
    """Download the weights, check the clip. False if the project cannot run."""
    weights_ok = ensure(NEEDS if with_depth else NEEDS_COUNT_ONLY,
                        video_dir, weights_dir)
    print("\n  source clip (manual)")
    clip_ok = require_clip(CLIP, video_dir, SOURCE_PAGE)
    return weights_ok and clip_ok
