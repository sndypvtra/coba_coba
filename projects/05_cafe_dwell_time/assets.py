"""What this project needs before it can run.

The only case of the six whose clips cannot be fetched by id: both are cut from
a long CAFE dataset recording rather than downloaded whole, so they ship in
`input/` and the README records where they came from. Everything else - the
detector and the tracker's re-identification backbone - arrives on first run.
"""

from __future__ import annotations

from pathlib import Path

from config import CLIPS

from factory_vision.assets import Requirements, ensure

NEEDS = Requirements(
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the two cafe clips are pre-cut and live in input/; see README.md",),
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
