"""Detection and tracking pieces shared by more than one use case.

Everything here was written for the cafe dwell-time case and is reused
unchanged by the warehouse spatial case. It lives at package root rather than
inside either one because a use-case package importing a sibling use-case
package is the wrong dependency direction - `factory_vision.spatial` should not
have to know that `factory_vision.dwell` exists.
"""

from __future__ import annotations

import numpy as np
import supervision as sv


def suppress_contained(det: sv.Detections, threshold: float) -> sv.Detections:
    """Drop a box that is largely swallowed by a more confident one.

    NMS scores overlap as intersection over *union*, which is small when one box
    is much bigger than the other - exactly the head-and-shoulders vs whole-body
    pair a raised indoor camera produces on seated people. Scoring by
    intersection over the *smaller* box instead measures containment, which is
    what that pair actually is.

    Measured over the first 20 frames of the cafe clip: 14 pairs exceed 0.75
    containment and every one of them sits below IoU 0.5, so NMS keeps them all.
    Tightening NMS instead is not an option - those duplicates span IoU
    0.076-0.485 while genuinely adjacent customers span 0.000-0.425, and a
    threshold low enough to catch the duplicates would wrongly merge 101 pairs of
    different people. The two populations are separable by containment and not by
    IoU, which is the whole reason this function exists.
    """
    if len(det) < 2:
        return det
    order = np.argsort(-det.confidence)
    boxes = det.xyxy[order]
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep = np.ones(len(boxes), dtype=bool)
    for i in range(len(boxes)):
        if not keep[i]:
            continue
        xx1 = np.maximum(boxes[i, 0], boxes[i + 1:, 0])
        yy1 = np.maximum(boxes[i, 1], boxes[i + 1:, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[i + 1:, 2])
        yy2 = np.minimum(boxes[i, 3], boxes[i + 1:, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        smaller = np.minimum(areas[i], areas[i + 1:])
        contained = inter / np.maximum(smaller, 1.0)
        keep[i + 1:][contained > threshold] = False
    return det[order[keep]]


class DetView:
    """Minimal Results-like view the ultralytics trackers accept.

    `model.track()` runs detection and tracking in one call, which leaves no
    seam to filter between them - and filtering *after* the tracker is useless,
    because by then a duplicate box has already been promoted to its own track
    ID and counted as a visitor. Detection and tracking are therefore driven
    separately here so the filters run in the only place they can work.
    """

    def __init__(self, xyxy: np.ndarray, conf: np.ndarray, cls: np.ndarray):
        self.conf = conf
        self.cls = cls
        cx = (xyxy[:, 0] + xyxy[:, 2]) / 2.0
        cy = (xyxy[:, 1] + xyxy[:, 3]) / 2.0
        self.xywh = np.stack([cx, cy, xyxy[:, 2] - xyxy[:, 0],
                              xyxy[:, 3] - xyxy[:, 1]], axis=1)

    def __len__(self):
        return len(self.conf)


def build_tracker(tracker_cfg_path, fps: float):
    """Instantiate the tracker named in the resolved YAML."""
    import yaml
    from types import SimpleNamespace

    import ultralytics.trackers as trackers

    cfg = yaml.safe_load(open(tracker_cfg_path))
    cfg.setdefault("frame_rate", int(round(fps)))
    name = str(cfg.get("tracker_type", "tracktrack")).lower()
    cls = {"tracktrack": trackers.TRACKTRACK, "botsort": trackers.BOTSORT,
           "bytetrack": trackers.BYTETracker}[name]
    return cls(SimpleNamespace(**cfg)), name
