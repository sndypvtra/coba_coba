"""Where things live, resolved once.

Each project keeps its own `input/` and `output/` so a case can be read, run and
understood without reference to the others. The two heavy shared caches do not
follow that rule and should not: model weights are hundreds of megabytes and
identical across projects, so they sit at the repository root and every project
points at them.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS_DIR = ROOT / "weights"          # shared: the same 70 MB checkpoint, six times over
PROJECTS_DIR = ROOT / "projects"


def project_dirs(project_file: str) -> tuple[Path, Path]:
    """The `input/` and `output/` belonging to the project a module lives in.

    Takes ``__file__`` so a project never has to write its own name down, and
    moving or renaming a project folder cannot leave a stale path behind.
    """
    here = Path(project_file).resolve().parent
    video_dir = here / "input"
    output_dir = here / "output"
    video_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return video_dir, output_dir
