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

CLIP = Clip("03_packages_conveyor.mp4", 5370836)
DETECTOR = ("yoloe-11l-seg.pt", "yolo11n-cls.pt")

NEEDS = Requirements(
    clips=(CLIP,),
    weights=DETECTOR,
    hub_models=("depth-anything/DA3METRIC-LARGE", "depth-anything/DA3-LARGE"),
)

# `--count-only` runs the shared counter with no measurement at all, which is
# what projects 01 and 02 do. It must not fetch the depth checkpoints: 2.9 GB for
# models the run will never open.
NEEDS_COUNT_ONLY = Requirements(clips=(CLIP,), weights=DETECTOR,
                                notes=("--count-only: the depth checkpoints are "
                                       "not fetched and no size is reported",))

# The one dependency no `main.py` can install for you. Printed verbatim when it is
# missing, because a `ModuleNotFoundError` raised inside a model constructor -
# after a 2.9 GB download - is not an error message, it is a puzzle.
DA3_INSTALL = """\
  Depth Anything 3 is not installed, and it is the one thing this project cannot
  fetch for you. It has to go in WITHOUT its dependency list: upstream pins
  numpy<2 and pulls opencv-python, xformers and open3d, which between them would
  downgrade numpy and OpenCV out from under the rest of this repository.

      pip install --pre "omegaconf>=2.4.0.dev0"
      pip install --no-deps addict einops plyfile trimesh
      git clone --depth 1 https://github.com/ByteDance-Seed/depth-anything-3
      pip install --no-deps -e depth-anything-3

  Or run the counting half on its own, which needs none of it:

      python main.py --count-only
"""


def depth_installed() -> bool:
    """Is Depth Anything 3 importable? Checked before anything is downloaded."""
    from importlib.util import find_spec

    try:
        return find_spec("depth_anything_3") is not None
    except (ImportError, ValueError):
        return False


def fetch(video_dir: Path, weights_dir: Path, with_depth: bool = True) -> bool:
    """Download whatever is missing. False if the project cannot run."""
    return ensure(NEEDS if with_depth else NEEDS_COUNT_ONLY, video_dir, weights_dir)
