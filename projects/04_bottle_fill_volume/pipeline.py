"""Fill-volume inspection, in three passes over the clip.

  1. bore.learn      the bottle's internal bore, over every frame. The
                     denominator has to be fixed before any fraction is
                     computed - growing it frame by frame makes the series
                     non-monotonic and meaningless.
  2. level.locate    the surface on every frame, then de-flickered: a median
                     kills splash spikes, an isotonic fit enforces that a
                     filling level only rises, and a smoothing pass makes the
                     rate physically plausible.
  3. this file       render against the now-fixed reference.

Not counting, and not zero-shot. Product inside the bottle is segmented on
saturation, the liquid surface is located, and the volume below it is integrated
over the bottle's bore as a stack of discs.

WHAT THE MILLILITRES MEAN
-------------------------
The fill *fraction* is measured. Millilitres are that fraction against the
nominal capacity passed as `--capacity-ml`, which nothing in the video can
observe. Give it the real SKU capacity and the number is meaningful; leave the
default and it is illustrative. Disc integration also assumes a solid of
revolution - true for these round bottles, false for a flask or a jerrycan.

Usage:
  python main.py
  python main.py --capacity-ml 350 --detect
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import cv2
import supervision as sv

import bore as bore_mod
import level
from panel import render
from profile import liquid_volume, row_widths
from roi import RoiTracker
from segmentation import liquid_mask

from factory_vision.paths import WEIGHTS_DIR, project_dirs

VIDEO_DIR, OUT_DIR = project_dirs(__file__)

warnings.filterwarnings("ignore")

VIDEO = VIDEO_DIR / "07_bottle_filling_line.mp4"


def _detector(enabled: bool):
    """YOLOE, only when asked for.

    `--detect` overlays the live segmentation alongside the measurement, to show
    the detector is running and why it is not trusted for the measurement.
    """
    if not enabled:
        return None
    from ultralytics import YOLOE

    model = YOLOE(str(WEIGHTS_DIR / "yoloe-11l-seg.pt"))
    model.set_classes(["transparent bottle"], model.get_text_pe(["transparent bottle"]))
    return model


def run(args) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src_video = Path(args.video)
    info = sv.VideoInfo.from_video_path(str(src_video))
    model = _detector(args.detect)

    cap = cv2.VideoCapture(str(src_video))
    roi_for = RoiTracker(cap)

    # ---- pass 1: the fixed reference ---------------------------------------
    bore = bore_mod.learn(cap, roi_for, args.max_frames)
    cap_prof, v_bottle, ref_row = bore_mod.capacity(bore)

    # ---- pass 2: the surface on every frame, de-flickered -------------------
    empty = len(bore.profile)
    raw = level.locate(cap, roi_for, bore.band_profile, empty, args.max_frames)
    surfaces = level.deflicker(raw, empty)
    level.announce(len(raw), ref_row, v_bottle)

    # ---- pass 3: render against the now-fixed reference ---------------------
    series = _render(cap, args, info, roi_for, surfaces, bore, cap_prof,
                     v_bottle, ref_row, model)
    cap.release()
    return _summary(args, src_video, series, info)


def _render(cap, args, info, roi_for, surfaces, bore, cap_prof, v_bottle,
            ref_row, model) -> list[dict]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    out_path = OUT_DIR / args.out_name
    sink = sv.VideoSink(str(out_path), sv.VideoInfo(width=info.width, height=info.height,
                                                    fps=info.fps,
                                                    total_frames=info.total_frames),
                        codec="mp4v")
    series: list[dict] = []
    idx = 0
    with sink:
        while True:
            ok, frame = cap.read()
            if not ok or (args.max_frames and idx >= args.max_frames):
                break
            roi = roi_for(frame)
            mask = liquid_mask(frame, roi)
            widths = row_widths(mask, roi)
            surface = surfaces[idx] if idx < len(surfaces) else None
            idx += 1

            frac = min(liquid_volume(surface, cap_prof) / v_bottle, 1.0)
            ml = frac * args.capacity_ml
            span = max(len(bore.profile) - ref_row, 1)
            level_h = (min((len(widths) - surface) / span, 1.0)
                       if surface is not None else 0.0)

            series.append({"frame": idx, "fill_volume_frac": round(frac, 4),
                           "fill_height_frac": round(float(level_h), 4),
                           "estimated_ml": round(ml, 1)})
            sink.write_frame(render(frame, roi, mask, surface, frac, level_h, ml,
                                    args.capacity_ml, idx, info.total_frames, model))
    return series


def _summary(args, src_video, series, info) -> dict:
    out_path = OUT_DIR / args.out_name
    summary = {
        "project": "LiquidLevel-Vision",
        "video": src_video.name,
        "output": out_path.name,
        "frames": len(series),
        "nominal_capacity_ml": args.capacity_ml,
        "final_fill_volume_frac": series[-1]["fill_volume_frac"] if series else 0,
        "final_estimated_ml": series[-1]["estimated_ml"] if series else 0,
        "note": ("fill fraction is measured from the video; millilitres are that "
                 "fraction against the nominal capacity configured for the SKU, "
                 "which no camera can observe"),
        "series": series,
    }
    summary_name = getattr(args, "summary_name", "liquid_level_summary.json")
    (OUT_DIR / summary_name).write_text(json.dumps(summary, indent=2))
    print(f"DONE {out_path.name}  frames={len(series)} "
          f"final_fill={summary['final_fill_volume_frac']*100:.1f}% "
          f"~{summary['final_estimated_ml']:.0f} mL of {args.capacity_ml:.0f} mL nominal")
    return summary


def run_case(**overrides) -> dict:
    """Run the fill-volume inspection and return its summary."""
    from types import SimpleNamespace

    args = SimpleNamespace(video=str(VIDEO), out_name="07_bottle_filling__liquid.mp4",
                           summary_name="liquid_level_summary.json",
                           capacity_ml=1500.0, detect=False, max_frames=0)
    for key, value in overrides.items():
        setattr(args, key, value)
    return run(args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(VIDEO),
                    help="source clip; note the calibration is per-installation")
    ap.add_argument("--out-name", default="07_bottle_filling__liquid.mp4")
    ap.add_argument("--capacity-ml", type=float, default=1500.0,
                    help="nominal SKU capacity, base to thread line; scales the mL readout")
    ap.add_argument("--detect", action="store_true",
                    help="also run YOLOE and overlay its bottle segmentation")
    ap.add_argument("--max-frames", type=int, default=0)
    return run(ap.parse_args())
