"""What the viewer sees: the readout strip, the zone outlines, the box tags.

Drawing only. Nothing here decides anything - every number it prints has already
been decided by the time it arrives, which is what keeps a presentation change
from moving a measurement.

The layout is a strip on the left rather than a panel floating over the video,
because a cafe frame has people in every corner and there is no dead space to
put a panel in without hiding one of them.
"""

from __future__ import annotations

import cv2
import numpy as np
import supervision as sv

PANEL_W = 470

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
# Amber, deliberately outside the track palette: staff must never be mistakable
# for a customer identity at a glance.
SERVER_COLOUR = (60, 190, 255)


def _text(img, s, org, scale, colour, weight=1):
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, colour, weight, cv2.LINE_AA)


def clock(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def tag(vis, text, x1, y1, colour, scale):
    """Filled label above a box, clamped so it never runs off the top."""
    fs = 0.5 * max(scale, 0.75)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, 2)
    pad = int(7 * scale)
    y = max(y1, th + 2 * pad)
    x = min(x1, vis.shape[1] - tw - 2 * pad)
    cv2.rectangle(vis, (x, y - th - 2 * pad), (x + tw + 2 * pad, y), colour, -1)
    _text(vis, text, (x + pad, y - pad), fs, (14, 14, 14), 2)


def draw_zones(vis, zone_list, scale):
    """Draw each zone in the colour of what it means.

    Excluded regions are dimmed - they are context. The service point is not
    dimmed: the person inside it is still being measured, just under a different
    heading, and hiding them would contradict the label.
    """
    for z in zone_list:
        pts = np.array(z.polygon, np.int32)
        staff = z.mode == "staff"
        colour = sv.Color.from_bgr_tuple(SERVER_COLOUR if staff else ZONE)
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


def draw_people(vis, live, staff, dwell, staff_dwell, fps, scale, box_ann):
    """Customer boxes in their identity colour, staff boxes in service amber."""
    if live:
        d = sv.Detections(xyxy=np.array([b for _, b in live], np.float32),
                          tracker_id=np.array([t for t, _ in live], int),
                          class_id=np.zeros(len(live), int))
        vis = box_ann.annotate(vis, d)
    for tid, b in live:
        tag(vis, f"#{tid}   {dwell[tid] / fps:.1f}s",
            int(b[0]), int(b[1]), PALETTE.by_idx(tid).as_bgr(), scale)
    for tid, b in staff:
        x1, y1, x2, y2 = [int(v) for v in b]
        cv2.rectangle(vis, (x1, y1), (x2, y2), SERVER_COLOUR, max(2, int(3 * scale)))
        tag(vis, f"PELAYAN #{tid}   {staff_dwell[tid] / fps:.1f}s",
            x1, y1, SERVER_COLOUR, scale)
    return vis


def box_annotator(scale: float) -> sv.RoundBoxAnnotator:
    return sv.RoundBoxAnnotator(color=PALETTE, thickness=max(2, int(3 * scale)),
                                color_lookup=sv.ColorLookup.TRACK)


def compose(vis, occupancy, visitors, idx, total, fps, dwell, live_ids,
            staff_dwell, staff_live, zone_counts, series, zone_list, tracker_name,
            merged_n):
    """Video on the right, readout on its own strip on the left."""
    h, w = vis.shape[:2]
    canvas = np.full((h, w + PANEL_W, 3), 16, np.uint8)
    canvas[:, PANEL_W:] = vis
    cv2.line(canvas, (PANEL_W - 1, 0), (PANEL_W - 1, h), (44, 44, 44), 1)

    m = 30
    _header(canvas, m, idx, total, fps)
    _headline(canvas, m, occupancy, visitors)
    _sparkline(canvas, m, series, total)
    _longest_in_view(canvas, m, dwell, live_ids, fps, total)
    if any(z.mode == "staff" for z in zone_list):
        _service_block(canvas, m, h, staff_dwell, staff_live, fps, total)
    _zone_legend(canvas, m, h, zone_list, zone_counts, tracker_name, merged_n)
    return canvas


def _header(canvas, m, idx, total, fps):
    _text(canvas, "CUSTOMER OCCUPANCY", (m, 52), 0.72, INK, 2)
    _text(canvas, "& DWELL TIME", (m, 82), 0.72, INK, 2)
    _text(canvas, "Cafe interior - fixed camera", (m, 108), 0.44, MUTED)
    cv2.line(canvas, (m, 128), (PANEL_W - m, 128), RULE, 1)
    _text(canvas, f"ELAPSED  {clock(idx / fps)}", (m, 158), 0.48, MUTED)
    _text(canvas, f"FRAME  {idx}/{total}", (m, 182), 0.48, MUTED)


def _headline(canvas, m, occupancy, visitors):
    """The two numbers, and the fact that they count different populations."""
    _text(canvas, f"{occupancy}", (m, 268), 2.6, ACCENT, 4)
    _text(canvas, "IN ROOM NOW", (m + 2, 296), 0.44, MUTED)
    _text(canvas, "customers + staff", (m + 2, 314), 0.34, DIM)
    _text(canvas, f"{visitors}", (m + 240, 268), 2.6, INK, 4)
    _text(canvas, "VISITORS TOTAL", (m + 242, 296), 0.44, MUTED)
    _text(canvas, "customers only", (m + 242, 314), 0.34, DIM)


def _sparkline(canvas, m, series, total):
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


def _longest_in_view(canvas, m, dwell, live_ids, fps, total):
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


def _service_block(canvas, m, h, staff_dwell, staff_live, fps, total):
    """Only drawn for a room that has a service point."""
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


def _zone_legend(canvas, m, h, zone_list, zone_counts, tracker_name, merged_n):
    y = h - 132
    cv2.line(canvas, (m, y), (PANEL_W - m, y), RULE, 1)
    _text(canvas, "ZONES", (m, y + 22), 0.42, MUTED)
    for i, z in enumerate(zone_list):
        yy = y + 46 + i * 22
        col = SERVER_COLOUR if z.mode == "staff" else ZONE
        cv2.rectangle(canvas, (m, yy - 11), (m + 13, yy), col, -1)
        _text(canvas, f"{z.name}", (m + 26, yy), 0.42, INK)
        _text(canvas, f"{zone_counts.get(z.name, 0)} now", (m + 250, yy), 0.42, DIM)
    _text(canvas, f"YOLOE-11L-seg zero-shot  |  {tracker_name}  |  "
                  f"{merged_n} tracks re-linked", (m, h - 40), 0.38, DIM)
    _text(canvas, "occupancy measured; visitor total depends on tracking",
          (m, h - 20), 0.36, DIM)
