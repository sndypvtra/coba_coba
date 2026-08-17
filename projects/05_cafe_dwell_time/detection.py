"""Pass 1: detect people, filter them, track them, describe them.

The detector walks the clip once and produces the thing everything else is built
on: a per-frame list of boxes with track ids.

`describe_tracks` then makes a second, cheap pass to aggregate those into
per-track records - lifetime, service-zone share, colour signature. It is
separate, and public, because `identity.split_switched_tracks` rewrites who is
who: after a split every aggregate has to be recomputed from the corrected
assignment rather than patched, and building them inside the detection loop made
that impossible.

Rendering is a third pass, because the identity repairs have to see the whole
clip before the first frame can be drawn.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLOE

import identity
import zones
from config import DwellConfig
from factory_vision.detect import DetView, build_tracker, suppress_contained
from factory_vision.paths import WEIGHTS_DIR
from factory_vision.tracking import resolve_tracker_cfg


@dataclass
class Observations:
    """What one pass over the clip saw. Pixels in, no interpretation yet."""

    frames: list[dict] = field(default_factory=list)
    tracks: dict[int, dict] = field(default_factory=dict)
    zone_counts: list[dict] = field(default_factory=list)
    raw_detections: int = 0
    duplicates_dropped: int = 0
    times: list[float] = field(default_factory=list)
    tracker_name: str = ""

    @property
    def avg_ms(self) -> float:
        return round(float(np.mean(self.times)), 1) if self.times else 0.0


def build_model(weights: str, prompts: list[str]) -> YOLOE:
    model = YOLOE(str(WEIGHTS_DIR / weights))
    model.set_classes(prompts, model.get_text_pe(prompts))
    return model


def observe(cfg: DwellConfig, args, src, masks, w: int, h: int,
            fps: float, output_dir) -> Observations:
    """Detect, filter, track and describe every frame of the clip.

    One tracker for everyone in the room. Splitting customers and staff into
    separate trackers looked tidy but decided the role per *frame*, from how much
    of a box fell inside the service polygon - so a server who leaned forward, or
    whose box reached past the counter edge, was handed to the customer tracker on
    that frame and acquired a visitor identity. Role is a property of a person,
    not of a frame, so it is decided once per track in `roles.py`.
    """
    tracker_cfg = resolve_tracker_cfg(args.tracker, cfg.tracker_overrides, "dw", output_dir)
    model = build_model(args.weights, cfg.prompts)
    tracker, tracker_name = build_tracker(tracker_cfg, fps)
    floor = zones.floor_conf(cfg.exclusion_zones, cfg.conf)

    obs = Observations(tracker_name=tracker_name)
    cap = cv2.VideoCapture(str(src))
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok or (args.max_frames and idx >= args.max_frames):
            break
        idx += 1
        t0 = time.time()
        # One inference at the lowest threshold any region asks for; the room
        # threshold is re-applied below. A second pass over the ROI would cost
        # another forward pass per frame for the same result.
        result = model.predict(frame, conf=floor, iou=0.5, imgsz=args.imgsz,
                               agnostic_nms=True, verbose=False)[0]
        det = sv.Detections.from_ultralytics(result)
        if len(det):
            area = ((det.xyxy[:, 2] - det.xyxy[:, 0])
                    * (det.xyxy[:, 3] - det.xyxy[:, 1])) / float(w * h)
            det = det[(area <= cfg.max_box_area_frac) & (area >= cfg.min_box_area_frac)]
        if len(det) and floor < cfg.conf:
            thr = zones.per_detection_conf(det, cfg.exclusion_zones, masks, w, h, cfg.conf)
            det = det[det.confidence >= thr]
        obs.raw_detections += len(det)
        before = len(det)
        det = suppress_contained(det, cfg.dedup_containment)
        obs.duplicates_dropped += before - len(det)

        # Excluded regions drop out before tracking - a mirror reflection must
        # never reach the tracker. Service regions do not: those detections stay
        # in, and are only labelled later.
        det, counts = zones.drop_excluded(det, cfg.exclusion_zones, masks, w, h)
        obs.zone_counts.append(counts)
        obs.times.append((time.time() - t0) * 1000)

        out = tracker.update(_view(det), frame)
        row = {"people": []}
        for r in np.asarray(out):
            box, tid = r[:4], int(r[4])
            row["people"].append((tid, box.tolist()))
        obs.frames.append(row)
    cap.release()

    obs.tracks = describe_tracks(obs.frames, src, cfg, masks, w, h)
    return obs


def describe_tracks(frames, src, cfg, masks, w: int, h: int) -> dict:
    """Per-track records, derived from the per-frame assignments.

    Derived, and deliberately so: `identity.split_switched_tracks` rewrites who
    is who, and every aggregate - lifetime, zone share, colour signature - has
    to be recomputed from the corrected assignment rather than patched. Building
    these inside the detection loop made that impossible, which is why it costs
    a second pass over the video now.
    """
    tracks: dict[int, dict] = {}
    cap = cv2.VideoCapture(str(src))
    for idx, row in enumerate(frames, start=1):
        ok, frame = cap.read()
        if not ok:
            break
        for tid, box in row["people"]:
            _describe(tracks, tid, idx, box, frame, cfg, masks, w, h)
    cap.release()
    for t in tracks.values():
        if t["n_hist"]:
            t["hist"] /= t["n_hist"]
    return tracks


def _view(det: sv.Detections) -> DetView:
    """The tracker's input, including for a frame that detected nothing."""
    if not len(det):
        return DetView(np.zeros((0, 4), np.float32), np.zeros(0, np.float32),
                       np.zeros(0, np.float32))
    return DetView(det.xyxy.astype(np.float32),
                   det.confidence.astype(np.float32),
                   det.class_id.astype(np.float32))


def _describe(tracks, tid: int, idx: int, box, frame, cfg, masks, w, h) -> None:
    """Fold one frame's observation of one track into that track's record."""
    t = tracks.setdefault(tid, {"first": idx, "frames": 0, "in_zone": 0,
                                "hist": np.zeros(identity.HIST_BINS, np.float32),
                                "n_hist": 0})
    t["last"] = idx
    t["frames"] += 1
    cx = int((box[0] + box[2]) / 2)
    cy = int((box[1] + box[3]) / 2)
    if zones.staff_zone_at(cx, cy, cfg.exclusion_zones, masks, w, h):
        t["in_zone"] += 1
    t["last_centre"] = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    if "first_centre" not in t:
        t["first_centre"] = t["last_centre"]
    if t["n_hist"] < identity.HIST_FRAMES:
        t["hist"] += identity.appearance(frame, box)
        t["n_hist"] += 1
