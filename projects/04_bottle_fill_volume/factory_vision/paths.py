"""Where things live, resolved once, relative to this project.

`ROOT` is the project folder itself: this package sits inside it, so a project
lifted into a repository of its own keeps its weights and its input beside it
rather than reaching for a shared cache that is no longer there.

The monorepo this came from had a `projects/` directory and helpers to look
across it. Those are gone from this copy on purpose - a standalone project has
no siblings to find.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS_DIR = ROOT / "weights"          # model checkpoints, downloaded on first run


def project_dirs(project_file: str) -> tuple[Path, Path]:
    """The `input/` and `output/` belonging to the project a module lives in.

    Takes ``__file__`` so a project never has to write its own name down, and
    moving or renaming the folder cannot leave a stale path behind.
    """
    here = Path(project_file).resolve().parent
    video_dir = here / "input"
    output_dir = here / "output"
    video_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return video_dir, output_dir
