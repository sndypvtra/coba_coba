"""Wiring the six models into one answer the counting pipeline can use.

This is the only file that knows the whole chain, and it exists so that no other
file has to:

    DA3-LARGE          -> intrinsics.py   the camera, predicted
    DA3METRIC-LARGE    -> depth.py        canonical depth x focal / 300 = metres
    depth_cache.py                        so the second run is nearly free
    belt.py                               the plane every height is measured from
    sizing.py                             mask + depth + plane -> millimetres

It implements `factory_vision.counting.measuring.Measurement`, which is the
contract the shared counter calls through. Projects 01 and 02 pass no backend
and none of this loads - no torch, no DA3, no 2.9 GB of checkpoints.

Everything here is per-installation. The constants live in `config.py` next to
the measurement that set each one; this file holds only the order of operations.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

import belt as belt_mod
import sizing
from depth import MetricDepth


class ParcelMeasurement:
    """The measurement backend for one parcel belt."""

    def __init__(self, cfg, clip):
        # Two configs, because two things are being described. `cfg` is metric
        # and belongs to this camera; `clip` is the clip itself, and the two
        # fields taken from it - the file name for the cache key, and the belt's
        # measured travel to orient the plane - are properties of the footage
        # rather than of the measurement.
        self.cfg = cfg
        self.clip = clip
        self.refresh_every = cfg.depth_every
        self.model: MetricDepth | None = None
        self.belt: belt_mod.BeltPlane | None = None
        self.K = None
        self.depth_map: np.ndarray | None = None
        self.rejected = 0          # detections that failed the on-belt test

    # ---------------------------------------------------------------- setup

    def prepare(self, src, width: int, height: int, output_dir) -> None:
        """Solve the camera and fit the belt from probes spread over the clip.

        The probes are spread rather than consecutive because both fits want
        variety: the intrinsics average over several views of a static scene,
        and the belt fit needs frames whose traffic sits in different places, so
        that between them every patch of belt is bare at least once.
        """
        probes = self._probe_frames(src)
        cache = Path(output_dir) / ".depth_cache" / Path(self.clip.filename).stem
        self.model = MetricDepth(process_res=self.cfg.depth_process_res,
                                 cache_dir=cache)

        K_proc = self.model.solve_intrinsics(probes[:4])
        self.K = K_proc.scaled_to(width, height)
        print(f"    depth   : DA3 {self.cfg.depth_process_res}px  "
              f"fx={self.K.fx:.0f} fy={self.K.fy:.0f} hFOV={self.K.hfov_deg:.1f}deg  "
              f"spread={self.model.intrinsics_spread*100:.1f}%  "
              f"square-pixel error={K_proc.square_pixel_error*100:.1f}%")

        maps = [self.model.depth(f, f"probe{i}") for i, f in enumerate(probes)]
        self.belt = belt_mod.fit_belt(belt_mod.bare_belt_depth(maps), self.K,
                                      self.cfg.belt_patches, self.clip.motion)
        print(f"    belt    : plane rms {self.belt.rms_m*1000:.1f} mm from "
              f"{self.belt.samples} px, camera "
              f"{self.belt.camera_height_m*1000:.0f} mm above it")

        # Seed the rolling map with the clip's own first frame. The loop
        # refreshes it on frame 1 anyway, so this only matters if depth_every is
        # ever changed such that it does not - and then the right stale map to
        # hold is the near one.
        self.depth_map = maps[0]

    @staticmethod
    def _probe_frames(src, count: int = 6) -> list[np.ndarray]:
        cap = cv2.VideoCapture(str(src))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 500
        frames = []
        for idx in np.linspace(0, max(total - 2, 0), count).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ok, frame = cap.read()
            if ok:
                frames.append(frame)
        cap.release()
        return frames

    # ------------------------------------------------------------- per frame

    def refresh(self, frame, key: str) -> None:
        self.depth_map = self.model.depth(frame, key)

    def measure_frame(self, det):
        """Measure every detection, keep the ones riding the belt.

        The depth map may be up to `refresh_every` frames old. At 4.7 px/frame a
        parcel drifts 23 px between runs, which a median over the whole mask
        absorbs - and the thing this gate exists to reject, the static stack at
        the back, does not move at all.
        """
        if self.belt is None or self.depth_map is None or not len(det):
            return det, []
        masks = det.mask if det.mask is not None else [None] * len(det)
        sizes, keep = [], np.zeros(len(det), bool)
        for i, mk in enumerate(masks):
            size = (sizing.measure(mk.astype(np.uint8), self.depth_map, self.K,
                                   self.belt, self.cfg.size_scale,
                                   self.cfg.footprint_scale)
                    if mk is not None else None)
            keep[i] = belt_mod.on_belt(size, self.cfg.depth_corridor,
                                       self.cfg.belt_base_band)
            sizes.append(size)
        self.rejected += int((~keep).sum())
        return det[keep], [s for s, k in zip(sizes, keep) if k]

    def lock_ready(self, centre_x: float, samples: int) -> bool:
        """Freeze the size once the parcel passes the lock line.

        Two samples minimum, so a single frame's reading is never what gets
        frozen. The lock sits where the parcel is nearest the camera, fully in
        view and best resolved - before the trolley starts occluding it.
        """
        if self.cfg.size_lock_x is None:
            return False
        return centre_x <= self.cfg.size_lock_x and samples >= 2

    def consensus(self, sizes):
        return sizing.consensus(sizes)

    def panel_stats(self, stats: dict, counted_sizes: list, live: list,
                    locked: dict) -> dict:
        """The measured half of the live dashboard - see `panel.py`.

        Computed here rather than in the shared pipeline because only a project
        that measures can produce any of it. Everything comes off the same
        locked measurements the summary uses, so the panel and the report can
        never disagree.

        ``stats`` is the counting half, already computed. The volume *rate*
        needs both halves - litres from here, elapsed time from there - so it is
        derived here rather than leaving the panel to do arithmetic.
        """
        volume_l = sum(s.volume_l for s in counted_sizes)
        hours = stats["elapsed_s"] / 3600.0
        mix = {"S": 0, "M": 0, "L": 0}
        borderline = 0
        for s in counted_sizes:
            mix[s.class_name] = mix.get(s.class_name, 0) + 1
            borderline += bool(s.class_mark)
        return {
            "volume_l": volume_l,
            "m3_per_hour": (volume_l / 1000.0) / hours if hours > 0 else 0.0,
            "mean_volume_l": volume_l / len(counted_sizes) if counted_sizes else 0.0,
            "mix": mix,
            "borderline": borderline,
            "on_belt": len(live),
            "on_belt_l": sum(s.volume_l for s in live),
            "largest": max(counted_sizes, key=lambda s: s.volume_l, default=None),
            "locked": len(locked),
        }

    # ---------------------------------------------------------------- report

    def summary(self, track_sizes: dict, track_age: dict, min_track_age: int,
                depth_ms: list) -> dict:
        """Distance, size, and how good each of them is.

        Only tracks the tracker held long enough to be countable are listed. A
        two-frame flicker has a size too, and reporting it would pad the table
        with rows nobody can act on.
        """
        parcels = [self._row(tid, sizes) for tid, sizes in sorted(track_sizes.items())
                   if track_age.get(tid, 0) >= min_track_age and len(sizes) >= 2]
        volumes = [p["volume_l"] for p in parcels]
        classes: dict[str, int] = {}
        for p in parcels:
            classes[p["size_class"]] = classes.get(p["size_class"], 0) + 1

        return {
            "method": "Depth Anything 3 (DA3-LARGE intrinsics + DA3METRIC-LARGE depth)",
            "process_res": self.cfg.depth_process_res,
            "depth_every_n_frames": self.cfg.depth_every,
            "depth_frames": self.model.frames_run,
            "depth_frames_from_cache": self.model.frames_cached,
            "avg_depth_ms": round(float(np.mean(depth_ms)), 1) if depth_ms else None,
            "intrinsics": {
                "fx": round(self.K.fx, 1), "fy": round(self.K.fy, 1),
                "cx": round(self.K.cx, 1), "cy": round(self.K.cy, 1),
                "hfov_deg": round(self.K.hfov_deg, 1),
                "frame_to_frame_spread_pct": round(self.model.intrinsics_spread * 100, 2),
                "square_pixel_error_pct": round(self.K.square_pixel_error * 100, 2),
                "note": "predicted, not calibrated; distance scales with it, size does not",
            },
            "belt_plane": {
                "fit_rms_mm": round(self.belt.rms_m * 1000, 1),
                "pixels": self.belt.samples,
                "camera_height_above_belt_mm": round(self.belt.camera_height_m * 1000),
            },
            "size_scale": round(self.cfg.size_scale, 4),
            "size_scale_note": self.cfg.size_scale_note,
            "footprint_scale": list(self.cfg.footprint_scale),
            "footprint_scale_note": self.cfg.footprint_scale_note,
            "depth_corridor_m": (list(self.cfg.depth_corridor)
                                 if self.cfg.depth_corridor else None),
            "detections_outside_corridor": self.rejected,
            "parcels_measured": len(parcels),
            "size_classes": classes,
            "total_volume_l": round(float(np.sum(volumes)), 1) if volumes else 0.0,
            "median_volume_l": round(float(np.median(volumes)), 1) if volumes else 0.0,
            "parcels": parcels,
        }

    def _row(self, tid: int, sizes: list) -> dict:
        s = sizing.consensus(sizes)
        dims = sorted([s.length_m, s.width_m, s.height_m], reverse=True)
        return {
            "track": tid,
            "frames_measured": len(sizes),
            "distance_m": round(float(np.median([x.distance_m for x in sizes])), 3),
            "distance_range_m": [round(float(min(x.distance_m for x in sizes)), 2),
                                 round(float(max(x.distance_m for x in sizes)), 2)],
            "length_mm": round(s.length_m * 1000),
            "width_mm": round(s.width_m * 1000),
            "height_mm": round(s.height_m * 1000),
            "longest_side_mm": round(dims[0] * 1000),
            "volume_l": round(s.volume_l, 1),
            "size_class": s.class_name,
            "size_class_mark": s.class_mark,
            "top_face_px": round(s.top_face_px, 1),
            "footprint_measurable": bool(s.footprint_measurable),
            "footprint_estimated": bool(s.footprint_estimated),
            "mask_kept": round(s.mask_kept, 2),
            # spread of the height across the pass: the honest error bar on a
            # measurement nobody can check against a tape measure
            "height_iqr_mm": round(float(np.subtract(*np.percentile(
                [x.height_m for x in sizes], [75, 25])) * 1000)),
        }
