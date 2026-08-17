"""Calibration and measurement scripts supporting the two pipelines.

``probe_prompts``       sweep prompt wording and confidence against a clip
``tune_thresholds``     measure how late an object is first detected on entry
``perturbation_test``   measure what a moved camera costs the fill inspection

None of these are needed to run a case; they are how the constants the cases
depend on were arrived at. Run them as modules from the repository root::

    python -m factory_vision.tools.tune_thresholds --clips 01,02
    python -m factory_vision.tools.perturbation_test --sweep

Each one reaches *into* a project - for its config, its clip, or its pipeline -
which is the opposite direction to everything else in this package, where
projects import the shared engine and never the reverse. That is why the loader
below lives here and not in `paths.py`: it is a tool-only convenience, and
nothing on a project's own run path may depend on it.
"""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType

from factory_vision.paths import project_path


def project_module(prefix: str, module: str) -> ModuleType:
    """Import `module` out of the project folder starting with `prefix`.

    ``project_module("04", "pipeline")`` gives project 04's pipeline. The folder
    is put on ``sys.path`` first because a project's modules import each other by
    bare name (``import bore``, ``from panel import render``) - they are written
    to be read as a self-contained folder, and that is worth more than being
    importable as a package.
    """
    folder = project_path(prefix)
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location(f"_p{prefix}_{module}",
                                                  folder / f"{module}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {module}.py from {folder}")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def project_clip(prefix: str):
    """The `CLIP` config a counting project declares - the single source of it."""
    return project_module(prefix, "config").CLIP
