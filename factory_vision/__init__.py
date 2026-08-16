"""factory-vision-poc — the shared half of six computer-vision projects.

Each case lives in its own folder under `projects/`, with its own `main.py`,
its own `input/` and `output/`, and its own configuration. What sits here is
only what more than one of them genuinely needs:

``factory_vision.assets``
    Fetches a project's clips, weights and Hub models on first run, with a
    progress bar, so `python main.py` works on a clean clone.

``factory_vision.counting``
    The zero-shot counting engine behind projects 01, 02 and 03. Shared on
    purpose: those three differ only in their `config.py`, and copying the
    pipeline into each would be three versions of one tracker drifting apart.

``factory_vision.detect`` and ``factory_vision.tracking``
    Detection filtering and the retuned tracker gates, used by the counting
    engine and by projects 05 and 06 which drive the tracker directly.

``factory_vision.tools``
    Calibration and measurement scripts that support the projects.
"""

from __future__ import annotations

from factory_vision.paths import PROJECTS_DIR, ROOT, WEIGHTS_DIR, project_dirs

__all__ = ["ROOT", "WEIGHTS_DIR", "PROJECTS_DIR", "project_dirs"]
