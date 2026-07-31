"""factory-vision-poc — computer vision for production lines.

Two independent pipelines, kept apart because they share nothing but OpenCV:

``factory_vision.counting``
    Zero-shot object counting on conveyors (cases 1-3). YOLOE text prompts ->
    TrackTrack -> supervision line counting. No training, no fixed class list.

``factory_vision.filling``
    Fill-volume inspection on a bottling line (case 4). HSV segmentation and
    disc integration, calibrated to one station.

``factory_vision.tools``
    Calibration and measurement scripts that support the two above.
"""

from __future__ import annotations

from factory_vision.paths import OUTPUT_DIR, ROOT, VIDEO_DIR, WEIGHTS_DIR

__all__ = ["ROOT", "VIDEO_DIR", "OUTPUT_DIR", "WEIGHTS_DIR"]
