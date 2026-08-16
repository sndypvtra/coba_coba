"""The readout panel and the per-frame overlay."""

from __future__ import annotations

import cv2
import numpy as np
import supervision as sv

from segmentation import display_mask


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
