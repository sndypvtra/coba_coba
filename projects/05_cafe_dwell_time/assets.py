"""What this project needs before it can run.

The only case of the six whose clips are committed rather than fetched. CAFE is
distributed as a single ~150 GB Google Drive archive with no API, so there is no
honest way for a first run to pull it; the two 30-second cuts are in `input/`
instead, and `.gitignore` carries an explicit exception for them.

That means this file has only the weights to fetch. `missing_clips` still exists
because a clip can go missing - someone prunes the repo, or copies the project
folder without its inputs - and the failure should say so plainly instead of
surfacing as a stack trace deep in the video reader.
"""

from __future__ import annotations

from pathlib import Path

from config import CLIPS

from factory_vision.assets import Requirements, ensure

NEEDS = Requirements(
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the two cafe clips are committed in input/ - CAFE has no fetchable "
           "API; see README.md",),
)


def fetch(video_dir: Path, weights_dir: Path) -> bool:
    return ensure(NEEDS, video_dir, weights_dir)


def missing_clips(video_dir: Path, wanted=None) -> list[str]:
    """Which of the configured clips are not in `input/`.

    Checked separately from `fetch` because these two cannot be downloaded, so
    the remedy is a README instruction rather than a retry.
    """
    todo = wanted if wanted is not None else CLIPS
    return [c.filename for c in todo if not (video_dir / c.filename).exists()]
