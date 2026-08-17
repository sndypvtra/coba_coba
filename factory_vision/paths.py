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


def project_path(prefix: str) -> Path:
    """The project folder whose name starts with `prefix` - "01", "04", ...

    For the tools in `factory_vision/tools/`, which work *across* cases and so
    cannot use `project_dirs(__file__)` the way a project's own modules do.
    """
    for p in sorted(PROJECTS_DIR.iterdir()):
        if p.is_dir() and p.name.startswith(f"{prefix}_"):
            return p
    raise FileNotFoundError(f"no project folder under {PROJECTS_DIR} starts with {prefix!r}")


def clip_path(filename: str) -> Path:
    """Locate a source clip in whichever project's `input/` holds it.

    Clips used to live in one shared `videos/` directory, and a `VIDEO_DIR`
    constant here pointed at it. Each project now keeps its own `input/`, so a
    tool spanning several cases has to look the file up rather than assume one
    place. Returns the path even when it does not exist, so callers can report a
    missing clip themselves - they know whether it is fatal.
    """
    for project in sorted(PROJECTS_DIR.iterdir()):
        candidate = project / "input" / filename
        if candidate.exists():
            return candidate
    return PROJECTS_DIR / "??" / "input" / filename
