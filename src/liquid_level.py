"""LiquidLevel-Vision — fill-level segmentation and volume estimation.

Measures how much liquid a filling machine puts into a bottle, from video alone.

Per frame:
  1. The liquid is segmented by colour in HSV. On this footage saturation is the
     discriminator, not hue: the amber product sits at S~255 while the shiny
     conveyor and the empty glass sit at S~36-60.
  2. The mask is confined to the bottle's measurement ROI and reduced to the
     single base-anchored blob, so product splashed on the conveyor outside the
     bottle cannot inflate the reading.
  3. Volume is integrated as a stack of discs rather than read off as a height.
     The liquid fills the bottle's cross-section, so the mask's width at each
     row *is* the internal diameter at that row: V = sum over rows of
     pi*(w(y)/2)^2. That handles the bottle's shoulder and base taper, which a
     linear height reading gets wrong.
  4. Fill fraction is V_liquid / V_bottle, and millilitres are that fraction of
     the bottle's nominal capacity.

Why the ROI is anchored rather than detected per frame: YOLOE does find the
bottles (`transparent bottle`, conf ~0.78) but the boxes are unstable on clear
plastic — they wander 194-328 px and swap between neighbouring bottles, which
makes a fill time series meaningless. Template matching shows the bottle itself
moves only 7 px across the whole fill cycle. So the ROI is measured once and
micro-aligned per frame by template match. `--detect` overlays the live YOLOE
segmentation alongside, to show the detector is running and why it is not
trusted for the measurement.

READ THIS BEFORE BELIEVING THE MILLILITRES
------------------------------------------
`--capacity-ml` is an *assumption*, not a measurement. Nothing in the video
states the bottle's size. The fill *fraction* is measured; millilitres are that
fraction scaled by whatever capacity you pass in. Give it the real SKU capacity
and the number is meaningful; leave the default and it is illustrative only.
Disc integration also assumes the bottle is a solid of revolution, which is
true for these round bottles and false for a flask or a rectangular jerrycan.

Usage:
  python src/liquid_level.py
  python src/liquid_level.py --capacity-ml 350 --detect
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import cv2
import numpy as np
import supervision as sv

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "videos" / "07_bottle_filling_line.mp4"
OUT_DIR = ROOT / "output"

# Front bottle, measured off the 1920x1080 frame: mouth y=490, inner base
# y=1020, body spans x=615..865.
ROI = (618, 490, 900, 1030)  # right edge widened; left is kept tight because
#                              the bottle behind also holds product and the
#                              two masks would otherwise merge into one blob

# Template used to cancel the few px of camera shake, taken from the bottle's
# neck/shoulder which stays sharp and never fills with product.
TEMPLATE_FRAME = 140
TEMPLATE_BOX = (640, 520, 900, 640)

# Amber product. Calibrated from pixel statistics, not guessed:
#   liquid          H 15-20   S 105-255  V 162-207
#   conveyor        H 11-22   S   8-55   V 105-137
#   empty glass     H  6-20   S   8-60   V 111-175
# Mouth inner diameter in px, read off the frame; used to taper the neck.
MOUTH_WIDTH_PX = 185.0

LIQUID_LO = (13, 150, 120)
LIQUID_HI = (30, 255, 255)


def liquid_mask(frame: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Segment product inside the ROI, keeping only the base-anchored pool."""
    x1, y1, x2, y2 = roi
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, LIQUID_LO, LIQUID_HI)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

    inside = np.zeros_like(m)
    inside[y1:y2, x1:x2] = m[y1:y2, x1:x2]

    # Liquid rests on the base. Keep the largest blob reaching the lower
    # quarter; a splash clinging to the shoulder is not part of the fill.
    n, lab, stats, _ = cv2.connectedComponentsWithStats((inside > 0).astype(np.uint8), 8)
    if n <= 1:
        return inside
    base_y = y2 - (y2 - y1) // 4
    best, best_area = 0, 0
    for i in range(1, n):
        top = stats[i, cv2.CC_STAT_TOP]
        bottom = top + stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]
        if bottom >= base_y and area > best_area:
            best, best_area = i, area
    out = np.zeros_like(inside)
    if best:
        out[lab == best] = 255
    return out


def disc_volume(mask: np.ndarray, roi: tuple[int, int, int, int]) -> tuple[float, np.ndarray]:
    """Integrate a mask as a stack of discs. Returns (volume_px3, width_per_row)."""
    x1, y1, x2, y2 = roi
    band = mask[y1:y2, x1:x2] > 0
    widths = band.sum(axis=1).astype(float)  # pixels of liquid per row
    vol = float(np.sum(np.pi * (widths / 2.0) ** 2))
    return vol, widths


def bottle_profile(observed: np.ndarray) -> np.ndarray:
    """Internal width per row for the whole bottle, built once from a full pass.

    Rows the liquid ever reached are measured directly — the product fills the
    cross-section, so its width there *is* the internal diameter. Rows above the
    highest level were never wetted, so they are tapered linearly from the
    topmost measured width to the mouth diameter (~185 px, read off the frame).
    That taper matters: assuming the neck is as wide as the body would inflate
    capacity and silently under-report fill %.
    """
    prof = observed.copy()
    known = prof > 0
    if not known.any():
        return prof
    top_known = int(np.argmax(known))
    if top_known > 0:
        prof[:top_known] = np.linspace(MOUTH_WIDTH_PX, prof[top_known], top_known)
    k = 15
    return np.convolve(prof, np.ones(k) / k, mode="same")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capacity-ml", type=float, default=500.0,
                    help="ASSUMED bottle capacity; scales the mL readout")
    ap.add_argument("--detect", action="store_true",
                    help="also run YOLOE and overlay its bottle segmentation")
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    info = sv.VideoInfo.from_video_path(str(VIDEO))
    w, h = info.width, info.height

    model = None
    if args.detect:
        from ultralytics import YOLOE

        model = YOLOE(str(ROOT / "weights" / "yoloe-11l-seg.pt"))
        model.set_classes(["transparent bottle"], model.get_text_pe(["transparent bottle"]))

    cap = cv2.VideoCapture(str(VIDEO))
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
    n_seen = 0
    while True:
        ok, frame = cap.read()
        if not ok or (args.max_frames and n_seen >= args.max_frames):
            break
        n_seen += 1
        roi = roi_for(frame)
        _, widths = disc_volume(liquid_mask(frame, roi), roi)
        k = min(len(widths), len(max_profile))
        max_profile[:k] = np.maximum(max_profile[:k], widths[:k])
    prof = bottle_profile(max_profile)
    v_bottle = float(np.sum(np.pi * (prof / 2.0) ** 2)) or 1.0
    print(f"pass 1: profile learned over {n_seen} frames, "
          f"bottle volume {v_bottle:.3e} px^3")

    # ---- pass 2: measure and render against the fixed capacity -------------
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    series: list[dict] = []
    out_path = OUT_DIR / "07_bottle_filling__liquid.mp4"
    sink = sv.VideoSink(str(out_path), sv.VideoInfo(width=w, height=h, fps=info.fps,
                                                    total_frames=info.total_frames),
                        codec="mp4v")
    idx = 0
    with sink:
        while True:
            ok, frame = cap.read()
            if not ok or (args.max_frames and idx >= args.max_frames):
                break
            idx += 1
            roi = roi_for(frame)
            mask = liquid_mask(frame, roi)
            v_liq, widths = disc_volume(mask, roi)

            frac = min(v_liq / v_bottle, 1.0)
            ml = frac * args.capacity_ml
            rows = np.where(widths > 0)[0]
            level_h = (len(widths) - rows.min()) / len(widths) if len(rows) else 0.0

            series.append({"frame": idx, "fill_volume_frac": round(frac, 4),
                           "fill_height_frac": round(float(level_h), 4),
                           "estimated_ml": round(ml, 1)})

            vis = render(frame, roi, mask, frac, level_h, ml, args.capacity_ml, idx,
                         info.total_frames, model)
            sink.write_frame(vis)
    cap.release()

    summary = {
        "project": "LiquidLevel-Vision",
        "video": VIDEO.name,
        "output": out_path.name,
        "frames": idx,
        "assumed_capacity_ml": args.capacity_ml,
        "final_fill_volume_frac": series[-1]["fill_volume_frac"] if series else 0,
        "final_estimated_ml": series[-1]["estimated_ml"] if series else 0,
        "caveat": ("fill fraction is measured; mL is that fraction times the ASSUMED "
                   "capacity, which is not observable from the video"),
        "series": series,
    }
    (OUT_DIR / "liquid_level_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"DONE {out_path.name}  frames={idx} "
          f"final_fill={summary['final_fill_volume_frac']*100:.1f}% "
          f"~{summary['final_estimated_ml']:.0f} mL (assumed {args.capacity_ml:.0f} mL bottle)")


def render(frame, roi, mask, frac, level_h, ml, cap_ml, idx, total, model):
    vis = frame.copy()
    x1, y1, x2, y2 = roi

    if model is not None:
        r = model.predict(frame, conf=0.15, imgsz=1280, agnostic_nms=True, verbose=False)[0]
        d = sv.Detections.from_ultralytics(r)
        if d.mask is not None:
            for m in d.mask:
                b = m.astype(bool)
                vis[b] = (0.82 * vis[b] + 0.18 * np.array([255, 255, 0])).astype(np.uint8)

    # liquid segmentation
    b = mask > 0
    vis[b] = (0.45 * vis[b] + 0.55 * np.array([255, 0, 220])).astype(np.uint8)

    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
    rows = np.where(mask[y1:y2, x1:x2].any(axis=1))[0]
    if len(rows):
        ytop = y1 + int(rows.min())
        cv2.line(vis, (x1 - 25, ytop), (x2 + 25, ytop), (0, 255, 255), 4)
        cv2.putText(vis, "LEVEL", (x2 + 32, ytop + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 255, 255), 2, cv2.LINE_AA)

    # vertical gauge
    gx = x2 + 120
    cv2.rectangle(vis, (gx, y1), (gx + 46, y2), (230, 230, 230), 2)
    fh = int((y2 - y1) * frac)
    cv2.rectangle(vis, (gx + 3, y2 - fh), (gx + 43, y2 - 3), (0, 200, 255), -1)

    panel = [
        (f"FILL {frac*100:5.1f}%  ~{ml:.0f} mL", 1.15, (90, 255, 140)),
        (f"volume fraction (disc integration)  {frac*100:.1f}%", 0.62, (235, 235, 235)),
        (f"height fraction                     {level_h*100:.1f}%", 0.62, (235, 235, 235)),
        (f"assumed capacity                    {cap_ml:.0f} mL  <- NOT measured", 0.62, (150, 220, 255)),
        ("liquid: HSV S>=150 (conveyor S~40)", 0.62, (235, 235, 235)),
        ("ROI anchored: bottle moves only 7 px", 0.62, (235, 235, 235)),
        (f"frame {idx}/{total}", 0.62, (185, 185, 185)),
    ]
    pad, lh = 22, 34
    bw, bh = 780, pad * 2 + lh * len(panel)
    ov = vis.copy()
    cv2.rectangle(ov, (pad, pad), (pad + bw, pad + bh), (18, 18, 18), -1)
    cv2.addWeighted(ov, 0.62, vis, 0.38, 0, vis)
    cv2.rectangle(vis, (pad, pad), (pad + bw, pad + bh), (90, 255, 140), 2)
    yy = pad + int(lh * 0.95)
    for t, s, c in panel:
        cv2.putText(vis, t, (pad + 18, yy), cv2.FONT_HERSHEY_SIMPLEX, s, c,
                    3 if s > 1 else 2, cv2.LINE_AA)
        yy += lh
    return vis


if __name__ == "__main__":
    main()
