"""Repository paths, resolved once.

Every module used to recompute the repository root from its own ``__file__``
depth, which meant moving a file silently changed where it looked for videos and
weights. Defining them here makes the depth a property of this one file.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = ROOT / "videos"
OUTPUT_DIR = ROOT / "output"
WEIGHTS_DIR = ROOT / "weights"
