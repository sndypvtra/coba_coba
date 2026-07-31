"""LiquidLevel-Vision — fill-level segmentation and volume estimation.

Measures how much liquid a filling machine puts into a bottle, from video alone.

Per frame:
  1. The liquid is segmented by colour in HSV. On this footage saturation is the
     discriminator, not hue: the amber product sits at S~255 while the shiny
     conveyor and the empty glass sit at S~36-60.
  2. The mask is confined to the bottle's measurement ROI and reduced to the
     single base-anchored blob, so product splashed on the conveyor outside the
     bottle cannot inflate the reading.
  3. The surface is the topmost row where the mask spans at least 45% of the
     bore, found by climbing from the base. This is the important bit: the
     falling jet is a thin column ~3% of the bore, so taking the topmost lit
     pixel measured the *nozzle stream* instead of the *level* and over-read the
     fill badly. The jet is drawn but excluded.
  4. Volume is integrated as a stack of discs over the bore below the surface:
     V = sum of pi*(bore(y)/2)^2. Using the bore rather than the per-frame mask
     width means glare or the machine's rod crossing the bottle cannot shrink
     the reading - only the surface position matters.
  5. Surfaces are median-filtered over 7 frames. Splash under the nozzle throws
     single-frame spikes that a real surface cannot produce.
  6. Capacity runs from the base up to the THREAD LINE, because that is what a
     stated fill volume means. It is deliberately not "the fullest level this
     clip reached" - that made the last frame read 100% by construction, when
     the liquid actually stops ~115 px below the threads and the bottle is only
     about three quarters full. Millilitres are that fraction of --capacity-ml.

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
# Right edge is 1010: the bottle body actually reaches x~1010 and the previous
# 900 clipped ~110 px of bore off it. Left stays tight at 618 because the bottle
# behind also holds product; nothing amber sits right of 1010, only background.
ROI = (618, 490, 1010, 1030)

# Bottom of the neck threads, read off the frame. This is the datum the stated
# capacity refers to - a filler's nominal volume is "up to the thread line", not
# "to the brim" and not "the fullest this clip happened to get". Using the
# fullest observed level made the last frame read 100% by construction, which is
# wrong: the liquid ends at y~700, some 115 px below the threads, so the bottle
# is visibly NOT full at the end of this clip.
THREAD_DATUM_Y = 585

# Template used to cancel the few px of camera shake, taken from the bottle's
# neck/shoulder which stays sharp and never fills with product.
TEMPLATE_FRAME = 140
TEMPLATE_BOX = (640, 520, 900, 640)

# Amber product. Calibrated from pixel statistics, not guessed:
#   liquid          H 15-20   S 105-255  V 162-207
#   conveyor        H 11-22   S   8-55   V 105-137
#   empty glass     H  6-20   S   8-60   V 111-175
# Absolute width that separates the falling jet from standing liquid. The jet
# runs 7-11 px; the shallowest pool is 80+. Used only to learn the bore, where a
# ratio test cannot be applied yet because the bore is what is being measured.
JET_MAX_WIDTH_PX = 40.0
# Rows whose learned bore falls below this fraction of the widest bore are
# treated as never observed. See bottle_profile for why.
BORE_MIN_FRACTION = 0.30

# Saturation is raised to 200 to reject product seen *through* glass. The front
# bottle's upper half is transparent and other filled bottles sit behind it, so
# their amber shows through and colour alone called it liquid inside this bottle.
# The extra glass layer desaturates it, and that is separable:
#   product, direct view          S 251-255
#   product seen through glass    S 104-199   <- was passing at S>=150
# At S>=150 the surface on the last frame read y=652; the real meniscus is y~690.
LIQUID_LO = (13, 200, 120)
LIQUID_HI = (30, 255, 255)

# Below the surface the region is liquid by definition, so a relaxed cut is used
# there purely to close the mask for display. The rods cast shadows that pull the
# product down to S 120-185, under the strict cut. This never moves the level:
# the surface is found with the strict cut, and volume integrates the bore.
LIQUID_LO_SHADOW = (13, 95, 90)

# Columns used to locate the surface: strictly inside the front bottle and right
# of where the neighbouring bottle's product is directly visible (it reaches
# x~690). Product in the bottle behind is just as saturated as product in this
# one, so colour cannot separate them - only position can.
SURFACE_BAND = (700, 890)

# Bottle silhouette, (y, x_left, x_right), read off the frame and interpolated
# between. The camera is fixed, so a hand-measured outline is exact and cheap.
# A rectangular ROI cannot express a bottle: it necessarily includes conveyor at
# the base corners, where product spilled on the belt was both shading the
# overlay outside the bottle and inflating the learned bore at the lowest rows.
BOTTLE_OUTLINE = [
    (585, 620, 1000),
    (650, 618, 1005),
    (700, 620, 1005),
    (800, 612, 1012),
    (900, 628, 1000),
    (960, 650, 975),
    (1010, 690, 935),
    (1029, 720, 900),
]


def bottle_silhouette(shape: tuple[int, int]) -> np.ndarray:
    """Boolean mask of the bottle interior, interpolated from BOTTLE_OUTLINE."""
    h, w = shape
    ys = np.array([p[0] for p in BOTTLE_OUTLINE], dtype=float)
    xl = np.array([p[1] for p in BOTTLE_OUTLINE], dtype=float)
    xr = np.array([p[2] for p in BOTTLE_OUTLINE], dtype=float)
    sil = np.zeros((h, w), dtype=bool)
    rows = np.arange(int(ys.min()), min(int(ys.max()) + 1, h))
    left = np.interp(rows, ys, xl).astype(int)
    right = np.interp(rows, ys, xr).astype(int)
    for y, a, b in zip(rows, left, right):
        sil[y, max(a, 0):min(b, w)] = True
    return sil


_SIL_CACHE: dict[tuple[int, int], np.ndarray] = {}


def silhouette_for(shape: tuple[int, int]) -> np.ndarray:
    if shape not in _SIL_CACHE:
        _SIL_CACHE[shape] = bottle_silhouette(shape)
    return _SIL_CACHE[shape]


def liquid_mask(frame: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Segment product inside the ROI, keeping only the base-anchored pool."""
    x1, y1, x2, y2 = roi
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, LIQUID_LO, LIQUID_HI)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

    inside = np.zeros_like(m)
    inside[y1:y2, x1:x2] = m[y1:y2, x1:x2]
    inside[~silhouette_for(m.shape)] = 0   # nothing outside the bottle counts

    # Liquid rests on the base, so keep EVERY component that reaches the lower
    # quarter - not just the largest. The machine's rods and probe cross the
    # bottle and cut the liquid's image into pieces: on the last frame the
    # bottom-left corner was its own 5040 px component and was being thrown away
    # purely for being smaller. A splash clinging high on the shoulder still gets
    # dropped, because it never reaches the base.
    n, lab, stats, _ = cv2.connectedComponentsWithStats((inside > 0).astype(np.uint8), 8)
    if n <= 1:
        return inside
    base_y = y2 - (y2 - y1) // 4
    out = np.zeros_like(inside)
    for i in range(1, n):
        bottom = stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT]
        if bottom >= base_y and stats[i, cv2.CC_STAT_AREA] >= 400:
            out[lab == i] = 255
    return out


def display_mask(frame: np.ndarray, roi: tuple[int, int, int, int],
                 surface: int | None, strict: np.ndarray) -> np.ndarray:
    """Mask for DISPLAY only - closes rod shadows below the measured surface.

    Purely cosmetic, and deliberately fenced in so it cannot influence anything:
    it is confined to rows below the already-measured surface, and only keeps
    relaxed-threshold blobs that touch the strict mask, so product spilled on the
    conveyor is not painted into the bottle. The level and the volume are still
    computed from the strict mask and the bore, untouched by this.

    Needed because the rods and probe crossing the bottle cast shadows that pull
    the product to S 120-185, under the strict S>=200 cut, leaving slivers of
    real liquid unshaded in the demo.
    """
    if surface is None:
        return strict
    x1, y1, x2, y2 = roi
    ysurf = y1 + surface
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, LIQUID_LO_SHADOW, LIQUID_HI)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    band = np.zeros_like(m)
    band[ysurf:y2, x1:x2] = m[ysurf:y2, x1:x2]
    band[~silhouette_for(m.shape)] = 0

    n, lab, _, _ = cv2.connectedComponentsWithStats((band > 0).astype(np.uint8), 8)
    out = strict.copy()
    for i in range(1, n):
        blob = lab == i
        if (blob & (strict > 0)).any():      # must touch measured product
            out[blob] = 255
    return out


def row_widths(mask: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Width of the liquid mask on each row of the ROI, top row first."""
    x1, y1, x2, y2 = roi
    return (mask[y1:y2, x1:x2] > 0).sum(axis=1).astype(float)


def band_widths(mask: np.ndarray, roi: tuple[int, int, int, int],
                dx: int = 0) -> np.ndarray:
    """Row widths within SURFACE_BAND only, used to locate the surface."""
    _, y1, _, y2 = roi
    a, b = SURFACE_BAND[0] + dx, SURFACE_BAND[1] + dx
    return (mask[y1:y2, a:b] > 0).sum(axis=1).astype(float)


# A row only counts as standing liquid if the mask spans this much of the
# bottle's internal width there. The falling jet is ~3% wide; the pool is 50%+.
POOL_MIN_RATIO = 0.45
# Rows the mask may lose to specular highlights. Deliberately small: while the
# machine is filling there is a turbulent splash sheet 30-40 rows above the
# settled pool, separated from it by a narrow band. A tolerance large enough to
# bridge that band made the reading bistable, flipping between ~30% and ~50% on
# alternate frames (f161 30%, f162 49%). The settled pool is the fill level; the
# splash crest sits above it and overestimates. The static rod that crosses the
# bottle needs no bridging - it occludes every frame, so the learned bore
# profile already accounts for it and the ratio test self-calibrates.
POOL_GAP_TOLERANCE = 10


def pool_top_absolute(widths: np.ndarray, gap_tol: int = 6) -> int | None:
    """Top of the contiguous pool, using an absolute width cut.

    Used to learn the bore, where no bore is known yet so no ratio test is
    possible. Contiguity is what excludes splash: a turbulent sheet under the
    nozzle can be as wide as the pool, but it is separated from it by a narrow
    band, so a run that must reach the base cannot include it.

    Without this the bore was learned from splash. At the topmost row it
    accepted, the recorded bore was 41 px against a real bore of 282 px - and
    because the ratio test then compared later splashes against that tiny value,
    the surface climbed into the splash region near the end of the fill. Exactly
    the "level jumps to the top and joins the base pool" symptom.
    """
    wide = widths >= JET_MAX_WIDTH_PX
    if not wide.any():
        return None
    y = int(np.where(wide)[0].max())  # lowest wide row = the base
    top, gap = y, 0
    while y >= 0:
        if wide[y]:
            top, gap = y, 0
        else:
            gap += 1
            if gap > gap_tol:
                break
        y -= 1
    return top


def pool_surface(widths: np.ndarray, profile: np.ndarray) -> int | None:
    """Row index of the liquid surface, walking up from the base.

    This is the fix for measuring the *jet* instead of the *level*. Liquid at
    rest spans the full cross-section of the vessel; a stream still falling from
    the nozzle is a thin column. Taking the topmost lit row therefore tracked
    the nozzle, not the surface — on frame 229 that put the line at y=597 (mask
    9 px wide, 3% of the bore) when the real surface was at y=660 (146 px).

    So instead: start at the lowest lit row and climb while each row is at least
    POOL_MIN_RATIO of the bore, tolerating short gaps where a highlight or the
    machine's rod hides the edge. Returns None if no standing liquid is found.
    """
    lit = np.where(widths > 0)[0]
    if len(lit) == 0:
        return None
    # A row with no measured bore cannot qualify. Guarding this matters: the
    # ratio test used max(bore, 1.0), so above the known bore it compared
    # against 1 px and passed on anything, letting the surface climb into rows
    # the liquid had never reached and reporting a datum with bore = 0.
    known = profile > 0
    ref = np.maximum(profile, 1.0)
    y = int(lit.max())  # lowest lit row = the base
    surface, gap = None, 0
    while y >= 0:
        if known[y] and widths[y] >= POOL_MIN_RATIO * ref[y]:
            surface, gap = y, 0
        else:
            gap += 1
            if gap > POOL_GAP_TOLERANCE:
                break
        y -= 1
    return surface


def isotonic_nonincreasing(y: np.ndarray) -> np.ndarray:
    """Best least-squares fit to `y` that never increases (pool-adjacent violators).

    Applied to the surface row over time. A threshold on a single frame cannot
    place the surface stably here: seen at an angle the liquid surface projects
    as an ellipse ~50 rows tall, and inside that band the colour mask is noisy,
    so any cutoff lands on a different row from frame to frame. Sweeping the
    cutoff and the reference did not help - every variant still jumped 50-70
    rows somewhere in the clip.

    The fix comes from physics instead of thresholds: during a fill the level
    only rises, so the row index only decreases. Fitting the closest
    non-increasing curve removes the jumps and the dips at once.

    NOTE this assumes a single monotonic fill of one bottle. It will flatten a
    genuine fall in level - a drained or swapped bottle - so it is wrong for
    footage that is not one fill cycle.
    """
    vals: list[float] = []
    sizes: list[int] = []
    for v in y.astype(float):
        vals.append(v)
        sizes.append(1)
        while len(vals) > 1 and vals[-2] < vals[-1]:
            n1, n2 = sizes[-2], sizes[-1]
            merged = (vals[-2] * n1 + vals[-1] * n2) / (n1 + n2)
            vals.pop(); sizes.pop()
            vals[-1] = merged; sizes[-1] = n1 + n2
    out = np.empty(len(y))
    i = 0
    for v, n in zip(vals, sizes):
        out[i:i + n] = v
        i += n
    return out


def liquid_volume(surface: int | None, profile: np.ndarray) -> float:
    """Volume of liquid below `surface`, integrated as a stack of discs.

    Integration uses the *bore* profile rather than the per-frame mask width.
    Below the surface the bottle is full, so the true cross-section is the bore;
    a mask narrower than that is occlusion or glare, not less liquid. This makes
    the reading depend only on locating the surface, not on a pixel-perfect mask.
    """
    if surface is None:
        return 0.0
    return float(np.sum(np.pi * (profile[surface:] / 2.0) ** 2))


def bottle_profile(observed: np.ndarray) -> np.ndarray:
    """Bore width per row, measured only. Returns (profile, reference_row).

    Earlier versions extrapolated the unwetted neck up to a hand-read mouth
    diameter. That was wrong twice over: the figure was taken from the bottle's
    outer rim (185 px) while the mask measures the inner bore (max 159 px), so
    the neck came out *wider* than the body — an inverted funnel — and the
    extrapolation covered 60% of the profile, meaning most of the "capacity" was
    a guess rather than a measurement.

    Now nothing is extrapolated. The bore is known only for rows the liquid
    actually reached, and `reference_row` is the highest of those: the fullest
    level the machine reached in this clip. Fill is reported against that, which
    is also the industrially meaningful datum, since a filler targets a nominal
    level at the shoulder rather than the brim.
    """
    prof = observed.copy()
    known = np.where(prof > 0)[0]
    if len(known) == 0:
        return prof
    top = int(known.min())
    idx = np.arange(len(prof))
    body = slice(top, len(prof))
    seg = prof[body]
    holes = seg <= 0
    if holes.any() and (~holes).any():
        seg[holes] = np.interp(idx[body][holes], idx[body][~holes], seg[~holes])
        prof[body] = seg
    k = 15
    sm = np.convolve(prof, np.ones(k) / k, mode="same")
    sm[:top] = 0.0

    # Trim the top of the learned bore where it is implausibly narrow. Even with
    # contiguity, a wave crest can connect to the pool by a thin neck and get
    # recorded as bore - the datum ended up on a row whose "bore" was 41 px
    # against a real bore of 282 px, a tall thin column that both inflated the
    # reference and gave the surface somewhere to climb. A real bottle's bore
    # does not drop below ~30% of its widest point inside the fillable body.
    floor = BORE_MIN_FRACTION * float(sm.max())
    ok = sm >= floor
    if ok.any():
        y = int(np.where(ok)[0].max())
        while y >= 0 and ok[y]:
            y -= 1
        sm[: y + 1] = 0.0
    return sm


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


def run(args) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src_video = Path(args.video)
    info = sv.VideoInfo.from_video_path(str(src_video))
    w, h = info.width, info.height

    model = None
    if args.detect:
        from ultralytics import YOLOE

        model = YOLOE(str(ROOT / "weights" / "yoloe-11l-seg.pt"))
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


def _text(img, s, org, scale, colour, weight=1, font=cv2.FONT_HERSHEY_SIMPLEX):
    cv2.putText(img, s, org, font, scale, colour, weight, cv2.LINE_AA)


def _text_right(img, s, right_x, y, scale, colour, weight=1,
                font=cv2.FONT_HERSHEY_SIMPLEX):
    (w, _), _ = cv2.getTextSize(s, font, scale, weight)
    cv2.putText(img, s, (right_x - w, y), font, scale, colour, weight, cv2.LINE_AA)


# panel palette
INK = (238, 238, 238)      # primary text
MUTED = (162, 162, 162)    # labels
ACCENT = (120, 240, 170)   # headline figure
RULE = (78, 78, 78)        # dividers
PRODUCT = (215, 0, 190)    # product overlay
STREAM = (255, 205, 60)    # dispensing stream overlay


def draw_panel(vis, frac, level_h, ml, cap_ml, idx, total):
    """Readout panel. Deliberately plain: a headline figure, then a spec table."""
    pad = 26
    w, h = 470, 384
    ov = vis.copy()
    cv2.rectangle(ov, (pad, pad), (pad + w, pad + h), (16, 18, 20), -1)
    cv2.addWeighted(ov, 0.78, vis, 0.22, 0, vis)
    cv2.rectangle(vis, (pad, pad), (pad + w, pad + h), (58, 62, 66), 1)
    cv2.line(vis, (pad, pad), (pad, pad + h), ACCENT, 3)

    left, right = pad + 22, pad + w - 22
    y = pad + 42
    _text(vis, "LiquidLevel-Vision", (left, y), 0.72, INK, 1, cv2.FONT_HERSHEY_DUPLEX)
    y += 26
    _text(vis, "Automated fill-volume inspection", (left, y), 0.5, MUTED)
    y += 22
    cv2.line(vis, (left, y), (right, y), RULE, 1)

    # headline figures
    y += 62
    _text(vis, f"{ml:,.0f}", (left, y), 1.55, ACCENT, 2, cv2.FONT_HERSHEY_DUPLEX)
    (nw, _), _ = cv2.getTextSize(f"{ml:,.0f}", cv2.FONT_HERSHEY_DUPLEX, 1.55, 2)
    _text(vis, "mL", (left + nw + 10, y), 0.66, MUTED, 1)
    _text_right(vis, f"{frac*100:.1f}%", right, y, 1.1, INK, 2, cv2.FONT_HERSHEY_DUPLEX)
    y += 24
    _text(vis, "DISPENSED", (left, y), 0.44, MUTED)
    _text_right(vis, "OF CAPACITY", right, y, 0.44, MUTED)

    y += 20
    cv2.line(vis, (left, y), (right, y), RULE, 1)

    rows = [
        ("Nominal capacity", f"{cap_ml:,.0f} mL"),
        ("Level height", f"{level_h*100:.1f} %"),
        ("Reference datum", "base to thread line"),
        ("Frame", f"{idx} / {total}"),
    ]
    y += 30
    for label, value in rows:
        _text(vis, label, (left, y), 0.5, MUTED)
        _text_right(vis, value, right, y, 0.52, INK)
        y += 27

    # legend
    y += 6
    cv2.line(vis, (left, y), (right, y), RULE, 1)
    y += 24
    cv2.rectangle(vis, (left, y - 10), (left + 14, y + 2), PRODUCT, -1)
    _text(vis, "product", (left + 22, y), 0.46, MUTED)
    cv2.rectangle(vis, (left + 130, y - 10), (left + 144, y + 2), STREAM, -1)
    _text(vis, "dispensing stream", (left + 152, y), 0.46, MUTED)
    return vis


def render(frame, roi, mask, surface, frac, level_h, ml, cap_ml, idx, total, model):
    vis = frame.copy()
    x1, y1, x2, y2 = roi

    if model is not None:
        r = model.predict(frame, conf=0.15, imgsz=1280, agnostic_nms=True, verbose=False)[0]
        d = sv.Detections.from_ultralytics(r)
        if d.mask is not None:
            for m in d.mask:
                b = m.astype(bool)
                vis[b] = (0.86 * vis[b] + 0.14 * np.array([255, 255, 0])).astype(np.uint8)

    mask = display_mask(frame, roi, surface, mask)

    # Product below the surface is what is measured; the stream above it is not.
    b = mask > 0
    ysurf = y1 + surface if surface is not None else y2
    pool = np.zeros_like(b)
    pool[ysurf:, :] = b[ysurf:, :]
    stream = b & ~pool
    vis[stream] = (0.68 * vis[stream] + 0.32 * np.array(STREAM)).astype(np.uint8)
    vis[pool] = (0.5 * vis[pool] + 0.5 * np.array(PRODUCT)).astype(np.uint8)

    if surface is not None:
        cv2.line(vis, (x1 - 18, ysurf), (x2 + 18, ysurf), (90, 240, 255), 2, cv2.LINE_AA)
        _text(vis, f"{level_h*100:.0f}%", (x2 + 26, ysurf + 6), 0.62, (90, 240, 255), 1)

    # fill gauge
    gx, gw = x2 + 96, 34
    cv2.rectangle(vis, (gx, y1), (gx + gw, y2), (70, 74, 78), 1)
    fh = int((y2 - y1 - 4) * frac)
    cv2.rectangle(vis, (gx + 2, y2 - 2 - fh), (gx + gw - 2, y2 - 2), ACCENT, -1)
    for q in (0.25, 0.5, 0.75):
        ty = int(y2 - (y2 - y1) * q)
        cv2.line(vis, (gx + gw + 4, ty), (gx + gw + 12, ty), RULE, 1)

    return draw_panel(vis, frac, level_h, ml, cap_ml, idx, total)


if __name__ == "__main__":
    main()
