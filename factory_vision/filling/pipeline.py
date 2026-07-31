"""Fill-volume inspection, in three passes over the clip.

  1. Learn the bottle's internal bore over every frame. The denominator has to
     be fixed before any fraction is computed - growing it frame by frame makes
     the series non-monotonic and meaningless.
  2. Locate the surface on every frame, then de-flicker: a 7-frame median kills
     splash spikes, an isotonic fit enforces that a filling level only rises,
     and a smoothing pass makes the rate physically plausible.
  3. Render against the now-fixed reference.

Why the ROI is anchored rather than detected per frame: YOLOE does find the
bottles (`transparent bottle`, conf ~0.78) but the boxes are unstable on clear
plastic - they wander 194-328 px and swap between neighbouring bottles, which
makes a fill time series meaningless. Template matching shows the bottle itself
moves only 7 px across the whole fill cycle. So the ROI is measured once and
micro-aligned per frame by template match. `--detect` overlays the live YOLOE
segmentation alongside, to show the detector is running and why it is not
trusted for the measurement.

WHAT THE MILLILITRES MEAN
-------------------------
The fill *fraction* is measured. Millilitres are that fraction against the
nominal capacity passed as `--capacity-ml`, which nothing in the video can
observe. Give it the real SKU capacity and the number is meaningful; leave the
default and it is illustrative. Disc integration also assumes a solid of
revolution - true for these round bottles, false for a flask or a jerrycan.

Usage:
  python -m factory_vision.filling.pipeline
  python -m factory_vision.filling.pipeline --capacity-ml 350 --detect
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import cv2
import numpy as np
import supervision as sv

from factory_vision.filling.calibration import (ROI, SURFACE_BAND, TEMPLATE_BOX,
                                                TEMPLATE_FRAME, THREAD_DATUM_Y)
from factory_vision.filling.panel import render
from factory_vision.filling.profile import (band_widths, bottle_profile,
                                            isotonic_nonincreasing, liquid_volume,
                                            pool_surface, pool_top_absolute,
                                            row_widths)
from factory_vision.filling.segmentation import liquid_mask
from factory_vision.paths import OUTPUT_DIR as OUT_DIR
from factory_vision.paths import ROOT, VIDEO_DIR, WEIGHTS_DIR

warnings.filterwarnings("ignore")

VIDEO = VIDEO_DIR / "07_bottle_filling_line.mp4"


def run(args) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src_video = Path(args.video)
    info = sv.VideoInfo.from_video_path(str(src_video))
    w, h = info.width, info.height

    model = None
    if args.detect:
        from ultralytics import YOLOE

        model = YOLOE(str(WEIGHTS_DIR / "yoloe-11l-seg.pt"))
        model.set_classes(["transparent bottle"], model.get_text_pe(["transparent bottle"]))

    cap = cv2.VideoCapture(str(src_video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, TEMPLATE_FRAME)
    ok, ref = cap.read()
    tx1, ty1, tx2, ty2 = TEMPLATE_BOX
    template = ref[ty1:ty2, tx1:tx2].copy()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def roi_for(frame):
        """ROI for this frame, shake-corrected. Clamped hard: measured true
        motion is 7 px, so a larger match is a bad one (early frames hold empty
        bottles that look nothing like the template) and is ignored."""
        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(res)
        ox, oy = loc[0] - tx1, loc[1] - ty1
        if score < 0.5 or abs(ox) > 40 or abs(oy) > 40:
            ox = oy = 0
        return (ROI[0] + ox, ROI[1] + oy, ROI[2] + ox, ROI[3] + oy)

    # ---- pass 1: learn the bottle's internal profile over the whole clip ----
    # The denominator must be fixed before any fraction is computed. Growing it
    # frame by frame makes the fill series non-monotonic and meaningless.
    max_profile = np.zeros(ROI[3] - ROI[1])
    band_max = np.zeros(ROI[3] - ROI[1])
    n_seen = 0
    while True:
        ok, frame = cap.read()
        if not ok or (args.max_frames and n_seen >= args.max_frames):
            break
        n_seen += 1
        roi = roi_for(frame)
        widths = row_widths(liquid_mask(frame, roi), roi)
        # Absolute cut, and only the run that reaches the base. The absolute cut
        # avoids a ratio against a bore that is not known yet; the contiguity
        # keeps splash out of the bore.
        top = pool_top_absolute(widths)
        if top is not None:
            keep = np.zeros_like(widths)
            keep[top:] = widths[top:]
            k = min(len(keep), len(max_profile))
            max_profile[:k] = np.maximum(max_profile[:k], keep[:k])
        bw = band_widths(liquid_mask(frame, roi), roi, roi[0] - ROI[0])
        btop = pool_top_absolute(bw, gap_tol=6)
        if btop is not None:
            bk = np.zeros_like(bw)
            bk[btop:] = bw[btop:]
            k2 = min(len(bk), len(band_max))
            band_max[:k2] = np.maximum(band_max[:k2], bk[:k2])
    prof = bottle_profile(max_profile)
    band_prof = bottle_profile(band_max)
    print(f"pass 1: bore measured over {n_seen} frames from contiguous pool rows only; "
          f"surface band x={SURFACE_BAND[0]}-{SURFACE_BAND[1]}")

    # ---- pass 2: locate the surface on every frame, then de-flicker ---------
    # Splash under the nozzle throws single-frame spikes: the raw series jumped
    # to 69% on f204 and 83% on f211 while the trend around them sat near 45%.
    # A liquid surface cannot rise a third of the bottle and fall back within
    # 1/25 s, so a short temporal median removes those without touching the
    # trend. Rendering is deferred to pass 3 so the filter can see ahead.
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    EMPTY = len(prof)
    raw: list[int] = []
    while True:
        ok, frame = cap.read()
        if not ok or (args.max_frames and len(raw) >= args.max_frames):
            break
        roi = roi_for(frame)
        m = liquid_mask(frame, roi)
        s = pool_surface(band_widths(m, roi, roi[0] - ROI[0]), band_prof)
        raw.append(EMPTY if s is None else int(s))
    win = 7
    pad = win // 2
    arr = np.array(raw, dtype=float)
    padded = np.pad(arr, pad, mode="edge")
    smooth = np.array([np.median(padded[i:i + win]) for i in range(len(arr))])

    # Median kills single-frame spikes; the monotonic fit fixes the sustained
    # jumps a per-frame threshold cannot avoid. Only frames that actually hold
    # liquid are fitted, so the empty run before the fill stays empty.
    wet = np.where(smooth < EMPTY)[0]
    if len(wet):
        a, b = int(wet.min()), int(wet.max()) + 1
        seg = isotonic_nonincreasing(smooth[a:b])
        # Monotonicity alone still keeps a sustained step: the f215->f216 jump is
        # an increase, so the isotonic fit preserved it and the level still moved
        # 27% of the bottle in 1/25 s. A filler dispenses at a roughly constant
        # rate, so smooth the fitted curve and re-impose monotonicity on top.
        k = 11
        if len(seg) > k:
            pad2 = k // 2
            padded2 = np.pad(seg, pad2, mode="edge")
            seg = np.convolve(padded2, np.ones(k) / k, mode="valid")[: len(seg)]
            seg = isotonic_nonincreasing(seg)
        smooth[a:b] = seg
    surfaces = [None if v >= EMPTY else int(round(v)) for v in smooth]
    # 100% is the highest *de-flickered* surface, so a single splash frame cannot
    # define the datum. Clamp every surface to it so nothing exceeds 100%.
    # Capacity runs from the base up to the thread line, not up to the fullest
    # level seen. This bottle is a wide-mouth jar - its neck is nearly as wide as
    # its body - so the bore above the highest wetted row is carried up as a
    # constant rather than tapered. That is a real approximation, but a small one
    # here, and it is the only stretch of bore no liquid ever revealed.
    ref_row = max(THREAD_DATUM_Y - ROI[1], 0)
    cap_prof = prof.copy()
    measured = np.where(cap_prof > 0)[0]
    if len(measured):
        top_measured = int(measured.min())
        # The neck bore is carried up from a robust estimate of the UPPER BODY,
        # not from the topmost measured row. Right at the surface the mask is
        # only partial - the topmost measured bore here is 89 px against an
        # upper-body bore of ~280 - and because volume goes as bore squared,
        # extrapolating with 89 shrank the unfilled neck tenfold and pushed the
        # final reading to 94% of capacity when the bottle is visibly ~3/4 full.
        lo = min(top_measured + 30, len(cap_prof) - 1)
        hi = min(top_measured + 150, len(cap_prof))
        window = cap_prof[lo:hi]
        neck = float(np.median(window[window > 0])) if (window > 0).any() else 0.0
        if top_measured > ref_row and neck > 0:
            cap_prof[ref_row:top_measured] = neck
            print(f"        neck bore extrapolated as {neck:.0f} px "
                  f"(topmost measured was {cap_prof[top_measured]:.0f} px)")
    v_bottle = float(np.sum(np.pi * (cap_prof[ref_row:] / 2.0) ** 2)) or 1.0
    print(f"pass 2: {len(raw)} surfaces located, median-filtered over {win} frames; "
          f"capacity datum = thread line y={THREAD_DATUM_Y} (row {ref_row}), "
          f"reference volume {v_bottle:.3e} px^3")

    # ---- pass 3: render against the fixed reference -------------------------
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    series: list[dict] = []
    out_path = OUT_DIR / args.out_name
    sink = sv.VideoSink(str(out_path), sv.VideoInfo(width=w, height=h, fps=info.fps,
                                                    total_frames=info.total_frames),
                        codec="mp4v")
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
            v_liq = liquid_volume(surface, cap_prof)

            frac = min(v_liq / v_bottle, 1.0)
            ml = frac * args.capacity_ml
            span = max(len(prof) - ref_row, 1)
            level_h = min((len(widths) - surface) / span, 1.0) if surface is not None else 0.0

            series.append({"frame": idx, "fill_volume_frac": round(frac, 4),
                           "fill_height_frac": round(float(level_h), 4),
                           "estimated_ml": round(ml, 1)})

            vis = render(frame, roi, mask, surface, frac, level_h, ml,
                         args.capacity_ml, idx, info.total_frames, model)
            sink.write_frame(vis)
    cap.release()

    summary = {
        "project": "LiquidLevel-Vision",
        "video": src_video.name,
        "output": out_path.name,
        "frames": idx,
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
    print(f"DONE {out_path.name}  frames={idx} "
          f"final_fill={summary['final_fill_volume_frac']*100:.1f}% "
          f"~{summary['final_estimated_ml']:.0f} mL of {args.capacity_ml:.0f} mL nominal")
    return summary


def run_case(**overrides) -> dict:
    """Run the fill-volume inspection and return its summary.

    Entry point for `cases/case4_bottle_fill_volume.py`.
    """
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

