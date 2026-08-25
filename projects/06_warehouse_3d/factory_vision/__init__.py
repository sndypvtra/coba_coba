"""The shared half of this project, vendored so the folder stands on its own.

This package came from a monorepo of six computer-vision cases, where it sat at
the repository root. A copy of exactly what this one case needs lives here
instead, so the folder can be lifted into a repository of its own and still run.

``factory_vision.assets``
    Fetches the model weights on first run, with a progress bar.

``factory_vision.detect``
    YOLOE's detections in the shape the tracker wants, plus the
    contained-box suppression this footage needs.

``factory_vision.tracking``
    The tracker gates, retuned for the score range open-vocabulary detection
    actually produces.

``factory_vision.paths``
    Where the weights, the input and the output live, resolved against this
    folder.
"""

from __future__ import annotations

from factory_vision.paths import ROOT, WEIGHTS_DIR, project_dirs

__all__ = ["ROOT", "WEIGHTS_DIR", "project_dirs"]
