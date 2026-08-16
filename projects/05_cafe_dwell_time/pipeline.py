"""Person detection, per-frame occupancy, and per-person dwell time.

Three numbers come out of this:

  occupancy   how many people are in the room right now - customers *and* staff,
              because a server standing at the counter is a person present
  visitors    how many distinct customers have been seen so far - staff excluded,
              because a shift is not a visit
  dwell       for each customer, how long they have been in view; staff time is
              reported separately as service

The first is a detection problem and is the easy one. The other two are tracking
problems, and they are only as good as the identity assignment: if a seated
customer is occluded by someone walking past and comes back with a new track ID,
one 8-minute visit is reported as two 4-minute visits and the visitor count goes
up by one. So this module reports the fragmentation signals alongside the answer
rather than presenting the dwell times as clean facts - see `quality` in the
returned summary.

Where a room needs it, two things are excluded because neither is a customer
visit: a wall mirror shows people already counted in the room, and staff work
behind the counter. Both are handled by frame regions rather than by appearance
- nothing in a person's pixels says "reflection" or "employee"; what says it is
where they are in a fixed camera's frame. That makes the zones per-installation,
and a room without a mirror or a counter in view correctly has none.

Run:  python cases/case5_cafe_dwell_time.py
      python cases/case5_cafe_dwell_time.py --all
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from collections import defaultdict

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLOE

from factory_vision.tracking import resolve_tracker_cfg
from factory_vision.detect import DetView, build_tracker, suppress_contained
from config import CLIPS, DwellConfig, ExclusionZone
from factory_vision.paths import WEIGHTS_DIR, project_dirs

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)

warnings.filterwarnings("ignore")

PALETTE = sv.ColorPalette.from_hex(
    ["#4CC9F0", "#4361EE", "#7209B7", "#F72585", "#FF9E00", "#38B000",
     "#00C2A8", "#FFD60A", "#E5383B", "#9D4EDD", "#06D6A0", "#EF476F"]
)

INK = (240, 240, 240)
MUTED = (158, 158, 158)
DIM = (110, 110, 110)
ACCENT = (120, 240, 170)
RULE = (72, 72, 72)
ZONE = (96, 96, 250)


def _text(img, s, org, scale, colour, weight=1):
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, colour, weight, cv2.LINE_AA)


def _clock(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


# ---------------------------------------------------------------- detections


def zone_masks(zones: list[ExclusionZone], w: int, h: int) -> list[np.ndarray]:
    out = []
    for z in zones:
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [np.array(z.polygon, np.int32)], 1)
        out.append(m)
    return out


def zone_hits(det: sv.Detections, zones, masks, w: int, h: int) -> np.ndarray:
    """Index of the first zone each detection falls inside, or -1."""
    hit = np.full(len(det), -1, dtype=int)
    for i, box in enumerate(det.xyxy):
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = max(x1, 0), max(y1, 0)
        x2, y2 = min(x2, w), min(y2, h)
        if x2 <= x1 or y2 <= y1:
            continue
        area = float((x2 - x1) * (y2 - y1))
        for zi, (z, m) in enumerate(zip(zones, masks)):
            if float(m[y1:y2, x1:x2].sum()) / area >= z.min_overlap:
                hit[i] = zi
                break
    return hit


def drop_excluded(det: sv.Detections, zones, masks, w: int, h: int):
    """Remove detections inside an "exclude" zone; keep everything else.

    Service regions deliberately do not filter here. Deciding staff-or-customer
    from a single frame's geometry is what let a server slip into the visitor
    count the moment her box reached past the counter edge, so that decision is
    deferred to `classify_roles` once each person has a full track behind them.
    Only mirrors and the like are dropped now, because a reflection must never
    reach the tracker at all.

    Returns the surviving detections plus a per-zone occupancy count for the
    readout panel.
    """
    counted: dict[str, int] = {}
    if not len(det) or not zones:
        return det, counted
    hit = zone_hits(det, zones, masks, w, h)
    for zi, z in enumerate(zones):
        n = int((hit == zi).sum())
        if n:
            counted[z.name] = n
    drop = np.zeros(len(det), dtype=bool)
    for zi, z in enumerate(zones):
        if z.mode != "staff":
            drop |= hit == zi
    return det[~drop], counted


def classify_roles(merged, cfg, min_fraction=0.6):
    """Decide staff or customer once per person, from where the track lived.

    A role is a property of a person, not of a frame. The test is the share of a
    track's frames whose centre sat inside a service polygon: a server working a
    station spends nearly all of theirs there, while a customer who steps up to
    order spends only the ordering part of a longer track. Pairing the share with
    a minimum duration keeps a brief visit to the counter from reading as staff.
    """
    staff, customers = set(), set()
    for root, t in merged.items():
        if t["frames"] < cfg.min_track_age:
            continue
        share = t["in_zone"] / max(t["frames"], 1)
        if share >= min_fraction and t["frames"] >= cfg.min_staff_frames:
            staff.add(root)
        else:
            customers.add(root)
    return customers, staff


# -------------------------------------------------------------------- render


def _tag(vis, text, x1, y1, colour, scale):
    """Filled label above a box, clamped so it never runs off the top."""
    fs = 0.5 * max(scale, 0.75)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, 2)
    pad = int(7 * scale)
    y = max(y1, th + 2 * pad)
    x = min(x1, vis.shape[1] - tw - 2 * pad)
    cv2.rectangle(vis, (x, y - th - 2 * pad), (x + tw + 2 * pad, y), colour, -1)
    _text(vis, text, (x + pad, y - pad), fs, (14, 14, 14), 2)



PANEL_W = 470
SERVER_COLOUR = (60, 190, 255)      # amber - deliberately outside the track palette
ZONE_SERVER = (60, 190, 255)


def track_appearance(frame, box) -> np.ndarray:
    """Hue/saturation histogram of a box interior, used to re-link broken tracks."""
    x1, y1, x2, y2 = [int(v) for v in box]
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, frame.shape[1]), min(y2, frame.shape[0])
    if x2 - x1 < 4 or y2 - y1 < 4:
        return np.zeros((16, 16), np.float32)
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
    return cv2.normalize(hist, hist).astype(np.float32)


def merge_broken_tracks(tracks, fps, diag, max_gap_s=3.0,
                        max_move_frac=0.12, min_similarity=0.45):
    """Re-link a track that died to the one that replaced it.

    At 4.995 fps - the CAFE frames are every 6th of a 29.97 fps recording - a
    walking person crosses far more pixels between frames than a tracker's motion
    model expects, so a customer who is briefly occluded comes back as a new ID.
    Measured on scene 17 before this ran: seven tracks were born after frame 10,
    and the pattern was unmistakable (#2 died f116 / #27 born f122, #6 died f126 /
    #28 born f128).

    Two tracks are joined when the later one starts within `max_gap_s` of the
    earlier one ending, begins near where the earlier one stopped, and carries a
    similar colour histogram. All three must hold: time alone would merge
    strangers who swapped seats, and appearance alone would merge two customers
    in the same colour shirt.
    """
    ids = sorted(tracks)
    parent = {i: i for i in ids}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    max_gap = max_gap_s * fps
    merges = []
    for a in ids:
        for b in ids:
            if a == b:
                continue
            ta, tb = tracks[a], tracks[b]
            gap = tb["first"] - ta["last"]
            if not (0 < gap <= max_gap):
                continue
            ca = ta["last_centre"]
            cb = tb["first_centre"]
            move = float(np.hypot(ca[0] - cb[0], ca[1] - cb[1])) / diag
            if move > max_move_frac:
                continue
            sim = float(cv2.compareHist(ta["hist"], tb["hist"], cv2.HISTCMP_CORREL))
            if sim < min_similarity:
                continue
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
                merges.append((b, a, round(gap / fps, 2), round(move, 3), round(sim, 3)))
    return {i: find(i) for i in ids}, merges


def draw_zones(vis, zones, scale):
    """Draw each zone with supervision, in the colour of what it means.

    Excluded regions are dimmed - they are context. The service point is not
    dimmed: the person inside it is still being measured, just under a different
    heading, and hiding them would contradict the label.
    """
    for z in zones:
        pts = np.array(z.polygon, np.int32)
        staff = z.mode == "staff"
        colour = sv.Color.from_bgr_tuple(ZONE_SERVER if staff else ZONE)
        if not staff:
            overlay = vis.copy()
            cv2.fillPoly(overlay, [pts], (26, 26, 26))
            cv2.addWeighted(overlay, 0.55, vis, 0.45, 0, vis)
        zone = sv.PolygonZone(polygon=pts)
        ann = sv.PolygonZoneAnnotator(
            zone=zone, color=colour, thickness=max(2, int(2.2 * scale)),
            text_color=sv.Color.from_bgr_tuple((14, 14, 14)),
            text_scale=0.5 * scale, text_thickness=max(1, int(1.4 * scale)),
            text_padding=int(8 * scale), display_in_zone_count=False)
        vis = ann.annotate(scene=vis,
                           label=(z.name.upper() if staff else f"EXCLUDED - {z.name}"))
    return vis


def compose(vis, occupancy, visitors, idx, total, fps, dwell, live_ids,
            staff_dwell, staff_live, zone_counts, series, zones, tracker_name,
            merged_n):
    """Video on the right, readout on its own strip on the left."""
    h, w = vis.shape[:2]
    canvas = np.full((h, w + PANEL_W, 3), 16, np.uint8)
    canvas[:, PANEL_W:] = vis
    cv2.line(canvas, (PANEL_W - 1, 0), (PANEL_W - 1, h), (44, 44, 44), 1)

    m = 30
    _text(canvas, "CUSTOMER OCCUPANCY", (m, 52), 0.72, INK, 2)
    _text(canvas, "& DWELL TIME", (m, 82), 0.72, INK, 2)
    _text(canvas, "Cafe interior - fixed camera", (m, 108), 0.44, MUTED)
    cv2.line(canvas, (m, 128), (PANEL_W - m, 128), RULE, 1)
    _text(canvas, f"ELAPSED  {_clock(idx / fps)}", (m, 158), 0.48, MUTED)
    _text(canvas, f"FRAME  {idx}/{total}", (m, 182), 0.48, MUTED)

    _text(canvas, f"{occupancy}", (m, 268), 2.6, ACCENT, 4)
    _text(canvas, "IN ROOM NOW", (m + 2, 296), 0.44, MUTED)
    _text(canvas, "customers + staff", (m + 2, 314), 0.34, DIM)
    _text(canvas, f"{visitors}", (m + 240, 268), 2.6, INK, 4)
    _text(canvas, "VISITORS TOTAL", (m + 242, 296), 0.44, MUTED)
    _text(canvas, "customers only", (m + 242, 314), 0.34, DIM)

    gx, gy, gw, gh = m, 344, PANEL_W - 2 * m, 74
    cv2.rectangle(canvas, (gx, gy), (gx + gw, gy + gh), (30, 30, 30), -1)
    _text(canvas, "OCCUPANCY OVER TIME", (gx, gy - 10), 0.40, DIM)
    if len(series) > 1:
        top = max(max(series), 1)
        pts = [(gx + int(i / max(total - 1, 1) * gw),
                gy + gh - int(v / top * (gh - 6)) - 3) for i, v in enumerate(series)]
        cv2.polylines(canvas, [np.array(pts, np.int32)], False, ACCENT, 2)
        cv2.circle(canvas, pts[-1], 4, ACCENT, -1)
    _text(canvas, f"max {max(series) if series else 0}", (gx + gw - 58, gy + 16), 0.40, DIM)

    y = 448
    _text(canvas, "LONGEST IN VIEW", (m, y), 0.44, MUTED)
    cv2.line(canvas, (m, y + 12), (PANEL_W - m, y + 12), RULE, 1)
    live = sorted(((dwell[i], i) for i in live_ids), reverse=True)[:7]
    for row, (frames, tid) in enumerate(live):
        yy = y + 44 + row * 32
        colour = PALETTE.by_idx(int(tid)).as_bgr()
        cv2.rectangle(canvas, (m, yy - 13), (m + 13, yy), colour, -1)
        _text(canvas, f"#{tid}", (m + 26, yy), 0.50, INK)
        _text(canvas, f"{frames / fps:5.1f}s", (m + 92, yy), 0.50, INK)
        bar = int(min(frames / max(total, 1), 1.0) * (PANEL_W - 2 * m - 176))
        cv2.rectangle(canvas, (m + 176, yy - 11), (m + 176 + bar, yy - 3), colour, -1)

    # server block - only drawn for rooms that have a service point
    if any(z.mode == "staff" for z in zones):
        y = h - 320
        cv2.line(canvas, (m, y), (PANEL_W - m, y), RULE, 1)
        _text(canvas, "PELAYAN / SERVICE ROI", (m, y + 26), 0.44, MUTED)
        known = sorted(set(staff_dwell))
        _text(canvas, f"{len(known)}", (m, y + 76), 1.5, SERVER_COLOUR, 3)
        _text(canvas, "PELAYAN", (m + 2, y + 96), 0.38, MUTED)
        _text(canvas, f"{len(staff_live)} in roi now", (m + 120, y + 76), 0.46, INK)
        for row, tid in enumerate(known[:3]):
            yy = y + 128 + row * 30
            on = tid in staff_live
            cv2.rectangle(canvas, (m, yy - 13), (m + 13, yy),
                          SERVER_COLOUR if on else (70, 90, 110), -1)
            _text(canvas, f"PELAYAN #{tid}", (m + 26, yy), 0.46,
                  SERVER_COLOUR if on else DIM)
            _text(canvas, f"{staff_dwell[tid] / fps:5.1f}s", (m + 200, yy), 0.46, INK)
            bar = int(min(staff_dwell[tid] / max(total, 1), 1.0) * (PANEL_W - 2 * m - 290))
            cv2.rectangle(canvas, (m + 290, yy - 11), (m + 290 + bar, yy - 3),
                          SERVER_COLOUR, -1)
        _text(canvas, "time inside the service ROI",
              (m, y + 128 + max(len(known[:3]), 1) * 30 + 6), 0.38, DIM)
        if not known:
            _text(canvas, "unattended", (m, y + 130), 0.46, DIM)

    y = h - 132
    cv2.line(canvas, (m, y), (PANEL_W - m, y), RULE, 1)
    _text(canvas, "ZONES", (m, y + 22), 0.42, MUTED)
    for i, z in enumerate(zones):
        yy = y + 46 + i * 22
        col = SERVER_COLOUR if z.mode == "staff" else ZONE
        cv2.rectangle(canvas, (m, yy - 11), (m + 13, yy), col, -1)
        _text(canvas, f"{z.name}", (m + 26, yy), 0.42, INK)
        _text(canvas, f"{zone_counts.get(z.name, 0)} now", (m + 250, yy), 0.42, DIM)
    _text(canvas, f"YOLOE-11L-seg zero-shot  |  {tracker_name}  |  {merged_n} tracks re-linked",
          (m, h - 40), 0.38, DIM)
    _text(canvas, "occupancy measured; visitor total depends on tracking",
          (m, h - 20), 0.36, DIM)
    return canvas


# ------------------------------------------------------------------ pipeline


def process(cfg: DwellConfig, args) -> dict:
    src = VIDEO_DIR / cfg.filename
    if not src.exists():
        raise SystemExit(f"missing {src} - see docs for how the clip is built")
    info = sv.VideoInfo.from_video_path(str(src))
    w, h, fps = info.width, info.height, info.fps
    scale = w / 1920.0
    diag = float(np.hypot(w, h))

    tracker_cfg = resolve_tracker_cfg(args.tracker, cfg.tracker_overrides, "dw", OUTPUT_DIR)
    model = YOLOE(str(WEIGHTS_DIR / args.weights))
    model.set_classes(cfg.prompts, model.get_text_pe(cfg.prompts))
    # One tracker for everyone in the room. Splitting customers and staff into
    # separate trackers looked tidy but decided the role per *frame*, from how
    # much of a box fell inside the service polygon - so a server who leaned
    # forward, or whose box reached past the counter edge, was handed to the
    # customer tracker on that frame and acquired a visitor identity. Measured on
    # scene 1: she registered as staff in only 71 of 150 frames and her leftovers
    # surfaced as customer tracks #49 and #52. Role is a property of a person,
    # not of a frame, so it is decided once per track after tracking.
    tracker, tracker_name = build_tracker(tracker_cfg, fps)
    masks = zone_masks(cfg.exclusion_zones, w, h)
    zone_conf = [z.conf for z in cfg.exclusion_zones]
    floor_conf = min([cfg.conf] + [c for c in zone_conf if c is not None])

    frames_data: list[dict] = []
    tracks: dict[int, dict] = {}
    zone_counts_series: list[dict] = []
    raw_dets = dup_dropped = 0
    times: list[float] = []

    print(f"\n>>> {cfg.filename}  {w}x{h} @ {fps:.3f}fps  {info.total_frames} frames "
          f"({info.total_frames / fps:.1f}s)")
    print(f"    prompts={cfg.prompts} conf={cfg.conf} tracker={args.tracker} "
          f"min_track_age={cfg.min_track_age} dedup={cfg.dedup_containment}")
    for z in cfg.exclusion_zones:
        print(f"    zone '{z.name}' [{z.mode}]: {z.reason}")

    # ---- pass 1: detect, filter, track, describe ---------------------------
    cap = cv2.VideoCapture(str(src))
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok or (args.max_frames and idx >= args.max_frames):
            break
        idx += 1
        t0 = time.time()
        # One inference at the lowest threshold any region asks for, then the room
        # threshold is re-applied everywhere except inside a zone that sets its
        # own. A second pass over the ROI would cost another forward pass per
        # frame for the same result.
        result = model.predict(frame, conf=floor_conf, iou=0.5, imgsz=args.imgsz,
                               agnostic_nms=True, verbose=False)[0]
        det = sv.Detections.from_ultralytics(result)
        if len(det):
            area = ((det.xyxy[:, 2] - det.xyxy[:, 0])
                    * (det.xyxy[:, 3] - det.xyxy[:, 1])) / float(w * h)
            det = det[(area <= cfg.max_box_area_frac) & (area >= cfg.min_box_area_frac)]
        if len(det) and floor_conf < cfg.conf:
            hits = zone_hits(det, cfg.exclusion_zones, masks, w, h)
            thr = np.array([cfg.conf if hi < 0 or zone_conf[hi] is None
                            else zone_conf[hi] for hi in hits])
            det = det[det.confidence >= thr]
        raw_dets += len(det)
        before = len(det)
        det = suppress_contained(det, cfg.dedup_containment)
        dup_dropped += before - len(det)

        # Excluded regions still drop out before tracking - a mirror reflection
        # must never reach the tracker. Service regions do not: those detections
        # stay in, and are only labelled later.
        det, counts = drop_excluded(det, cfg.exclusion_zones, masks, w, h)
        zone_counts_series.append(counts)
        times.append((time.time() - t0) * 1000)

        row = {"people": []}
        if len(det):
            out = tracker.update(DetView(det.xyxy.astype(np.float32),
                                          det.confidence.astype(np.float32),
                                          det.class_id.astype(np.float32)), frame)
        else:
            out = tracker.update(DetView(np.zeros((0, 4), np.float32),
                                          np.zeros(0, np.float32),
                                          np.zeros(0, np.float32)), frame)
        for r in np.asarray(out):
            box, tid = r[:4], int(r[4])
            row["people"].append((tid, box.tolist()))
            t = tracks.setdefault(tid, {"first": idx, "frames": 0, "in_zone": 0,
                                        "hist": np.zeros((16, 16), np.float32),
                                        "n_hist": 0})
            t["last"] = idx
            t["frames"] += 1
            # Membership for the role vote uses the box centre rather than its
            # area. A person working behind a counter keeps their centre inside
            # the service polygon even when the box spills past the counter edge;
            # an area test loses them exactly when they lean in to serve.
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            if 0 <= cx < w and 0 <= cy < h:
                for zi, z in enumerate(cfg.exclusion_zones):
                    if z.mode == "staff" and masks[zi][cy, cx]:
                        t["in_zone"] += 1
                        break
            t["last_centre"] = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            if "first_centre" not in t:
                t["first_centre"] = t["last_centre"]
            if t["n_hist"] < 12:
                t["hist"] += track_appearance(frame, box)
                t["n_hist"] += 1
        frames_data.append(row)
    cap.release()
    for t in tracks.values():
        if t["n_hist"]:
            t["hist"] /= t["n_hist"]

    # ---- re-link tracks broken by occlusion --------------------------------
    alias, merges = merge_broken_tracks(tracks, fps, diag)
    if merges:
        print(f"    re-linked {len(merges)} broken tracks:")
        for b, a, gap, move, sim in merges:
            print(f"      #{b} -> #{a}   gap {gap}s  moved {move * 100:.1f}% of frame  "
                  f"appearance {sim:.2f}")

    merged: dict[int, dict] = {}
    for tid, t in tracks.items():
        root = alias[tid]
        m = merged.setdefault(root, {"first": t["first"], "last": t["last"],
                                     "frames": 0, "in_zone": 0})
        m["first"] = min(m["first"], t["first"])
        m["last"] = max(m["last"], t["last"])
        m["frames"] += t["frames"]
        m["in_zone"] += t["in_zone"]

    # ---- decide staff or customer, once per person -------------------------
    inzone = [(t["in_zone"] / max(t["frames"], 1), r, t) for r, t in merged.items()
              if t["in_zone"]]
    if inzone:
        print("    time inside a service zone, by track:")
        for share, r, t in sorted(inzone, reverse=True):
            print(f"      #{r:<3d} {t['in_zone']:3d}/{t['frames']:3d} frames  {share:5.0%}")
    locked, staff_locked = classify_roles(merged, cfg)
    if staff_locked:
        for r in sorted(staff_locked):
            t = merged[r]
            print(f"    #{r} classified as service: {t['in_zone']}/{t['frames']} "
                  f"frames inside the service zone "
                  f"({t['in_zone'] / max(t['frames'], 1):.0%})")

    # ---- hold staff across short detection gaps ----------------------------
    hold = max([z.hold_frames for z in cfg.exclusion_zones] or [0])
    held_total = 0
    if hold and staff_locked:
        seen_at = defaultdict(dict)
        for i, row in enumerate(frames_data):
            for tid, box in row["people"]:
                seen_at[alias[tid]][i] = box
        for tid in staff_locked:
            fr = sorted(seen_at[tid])
            for a, b in zip(fr, fr[1:]):
                gap = b - a - 1
                if 0 < gap <= hold:
                    for k in range(a + 1, b):
                        frames_data[k]["people"].append((tid, seen_at[tid][a]))
                        frames_data[k].setdefault("held", set()).add(tid)
                        held_total += 1
        if held_total:
            print(f"    held service tracks across {held_total} frames of missed "
                  f"detection (max gap {hold} frames)")

    # ---- pass 2: render from the recorded tracks ---------------------------
    out_path = OUTPUT_DIR / cfg.filename.replace(".mp4", "__dwell.mp4")
    out_info = sv.VideoInfo(width=w + PANEL_W, height=h, fps=info.fps,
                            total_frames=info.total_frames)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    box_ann = sv.RoundBoxAnnotator(color=PALETTE, thickness=max(2, int(3 * scale)),
                                   color_lookup=sv.ColorLookup.TRACK)
    dwell = defaultdict(int)
    staff_dwell = defaultdict(int)
    series: list[int] = []
    cap = cv2.VideoCapture(str(src))
    with sv.VideoSink(str(out_path), out_info, codec="mp4v") as sink:
        for i, row in enumerate(frames_data):
            ok, frame = cap.read()
            if not ok:
                break
            # One track list, split by the role each identity was assigned.
            seen_c, seen_s = set(), set()
            live, stf = [], []
            for t, b in row["people"]:
                root = alias.get(t, t)
                if root in staff_locked:
                    if root in seen_s:               # a merge can leave two boxes
                        continue                     # on one identity in a frame
                    seen_s.add(root)
                    stf.append((root, b))
                    staff_dwell[root] += 1
                elif root in locked:
                    if root in seen_c:
                        continue
                    seen_c.add(root)
                    live.append((root, b))
                    dwell[root] += 1
            # Occupancy is how many people are in the room, so it counts staff
            # too - a server standing at the counter is a person present. The
            # visitor total is a different question and stays customers-only:
            # staff are not visits.
            series.append(len(live) + len(stf))

            vis = draw_zones(frame.copy(), cfg.exclusion_zones, max(scale, 0.8))
            if live:
                d = sv.Detections(xyxy=np.array([b for _, b in live], np.float32),
                                  tracker_id=np.array([t for t, _ in live], int),
                                  class_id=np.zeros(len(live), int))
                vis = box_ann.annotate(vis, d)
            for tid, b in live:
                x1, y1 = int(b[0]), int(b[1])
                _tag(vis, f"#{tid}   {dwell[tid] / fps:.1f}s",
                     x1, y1, PALETTE.by_idx(tid).as_bgr(), scale)
            for tid, b in stf:
                x1, y1, x2, y2 = [int(v) for v in b]
                cv2.rectangle(vis, (x1, y1), (x2, y2), SERVER_COLOUR,
                              max(2, int(3 * scale)))
                _tag(vis, f"PELAYAN #{tid}   {staff_dwell[tid] / fps:.1f}s",
                     x1, y1, SERVER_COLOUR, scale)

            visitors_so_far = sum(1 for a in locked if merged[a]["first"] <= i + 1)
            sink.write_frame(compose(
                vis, len(live) + len(stf), visitors_so_far,
                i + 1, info.total_frames, fps, dwell, {t for t, _ in live},
                staff_dwell, {t for t, _ in stf},
                zone_counts_series[i] if i < len(zone_counts_series) else {},
                series, cfg.exclusion_zones, tracker_name, len(merges)))
    cap.release()

    people = [{"track_id": r, "first_frame": merged[r]["first"],
               "last_frame": merged[r]["last"], "frames_seen": dwell[r],
               "dwell_seconds": round(dwell[r] / fps, 2),
               "span_seconds": round((merged[r]["last"] - merged[r]["first"] + 1) / fps, 2),
               "continuity": round(dwell[r] / max(merged[r]["last"] - merged[r]["first"] + 1, 1), 3)}
              for r in sorted(locked)]
    held_per_track = defaultdict(int)
    for row in frames_data:
        for tid in row.get("held", ()):
            held_per_track[tid] += 1
    staff = [{"track_id": t,
              "service_seconds": round(staff_dwell[t] / fps, 2),
              "frames_total": staff_dwell[t],
              "frames_detected": staff_dwell[t] - held_per_track[t],
              "frames_held": held_per_track[t],
              "zone_share": round(merged[t]["in_zone"] / max(merged[t]["frames"], 1), 3)}
             for t in sorted(staff_locked)]
    fragmented = [p for p in people if p["continuity"] < 0.8]
    dwells = [p["dwell_seconds"] for p in people]

    summary = {
        "video": cfg.filename, "scene": cfg.scene, "source": cfg.source,
        "output": out_path.name, "resolution": f"{w}x{h}", "fps": round(fps, 3),
        "frames": len(frames_data), "duration_seconds": round(len(frames_data) / fps, 1),
        "model": args.weights.replace(".pt", ""), "prompts": cfg.prompts,
        "conf": cfg.conf, "tracker": "TrackTrack (CVPR 2025) + ReID + GMC",
        "visitors_total": len(locked),
        "occupancy_includes_staff": True,
        "occupancy_mean": round(float(np.mean(series)), 2) if series else 0,
        "occupancy_max": int(np.max(series)) if series else 0,
        "dwell_mean_seconds": round(float(np.mean(dwells)), 2) if dwells else 0,
        "dwell_max_seconds": round(float(np.max(dwells)), 2) if dwells else 0,
        "staff": staff,
        "staff_service_seconds": round(sum(s["service_seconds"] for s in staff), 2),
        "filtering": {
            "detections_before_filters": raw_dets,
            "duplicate_boxes_removed": dup_dropped,
            "zones": [{"name": z.name, "mode": z.mode, "reason": z.reason,
                       "min_overlap": z.min_overlap} for z in cfg.exclusion_zones],
            "tracks_relinked": len(merges),
            "relink_detail": [{"from": b, "into": a, "gap_seconds": g,
                               "moved_frac": mv, "appearance": s}
                              for b, a, g, mv, s in merges],
        },
        "quality": {
            "tracks_with_gaps": len(fragmented),
            "worst_continuity": round(min((p["continuity"] for p in people), default=1.0), 3),
            "note": ("continuity = frames actually seen / first-to-last span. "
                     "Below 1.0 the track was lost and re-acquired; re-linking "
                     "joins the obvious cases but cannot join every one."),
        },
        "avg_ms_per_frame": round(float(np.mean(times)), 1) if times else 0,
        "occupancy_series": series, "people": people, "notes": cfg.notes,
    }
    summary_name = cfg.filename.replace(".mp4", "__dwell.json")
    (OUTPUT_DIR / summary_name).write_text(json.dumps(summary, indent=2))
    print(f"    filtered: {dup_dropped} duplicate boxes; re-linked {len(merges)} tracks")
    print(f"    DONE {out_path.name}  visitors={len(locked)} "
          f"occupancy mean={summary['occupancy_mean']} max={summary['occupancy_max']} "
          f"dwell mean={summary['dwell_mean_seconds']}s max={summary['dwell_max_seconds']}s "
          f"staff={summary['staff_service_seconds']}s  {np.mean(times):.0f}ms/f")
    return summary


def run_case(filename: str = "cafe_scene5_30s.mp4", **overrides) -> dict:
    from types import SimpleNamespace

    args = SimpleNamespace(weights="yoloe-11l-seg.pt", tracker="tracktrack",
                           imgsz=1280, max_frames=0)
    for k, v in overrides.items():
        setattr(args, k, v)
    try:
        cfg = next(c for c in CLIPS if c.filename == filename)
    except StopIteration:
        raise SystemExit(f"no clip named {filename}")
    return process(cfg, args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="yoloe-11l-seg.pt")
    ap.add_argument("--tracker", default="tracktrack", choices=["tracktrack", "botsort"])
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()
    return process(CLIPS[0], args)


if __name__ == "__main__":
    main()
