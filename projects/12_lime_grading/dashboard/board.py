"""The page every Factory Vision dashboard shares: where the cards go, and the parts
that are the same in each (detection chips, the event feed, charts, the encoder).

1920 x 1080. The camera picture sits top left at 1280 x 720; four KPI cards, a
middle card and the event feed run down the right; two cards sit under the
picture; the event timeline runs along the bottom.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

import cv2
import numpy as np

import ui
from ui import BG, BLUE, BORDER, TEXT, TEXT_3, G, M, TOP, W, alpha

VX, VY, VW, VH = M, TOP + 12, 1280, 720
RX = VX + VW + G
RX1 = W - M
KW = (RX1 - RX - G) // 2
KPI_BOXES = [(RX, 68, RX + KW, 156), (RX + KW + G, 68, RX1, 156),
             (RX, 168, RX + KW, 256), (RX + KW + G, 168, RX1, 256)]
MID = (RX, 268, RX1, 588)
FEED = (RX, 600, RX1, 1012)
BL = (VX, 800, 650, 1012)
BR = (662, 800, VX + VW, 1012)
TL = (VX, 1024, RX1, 1064)
CARDS = KPI_BOXES + [MID, FEED, BL, BR]


@dataclass
class Event:
    frame: int
    t: float
    severity: str              # high / medium / low / info
    icon: str
    title: str
    detail: str
    kind: str
    feed: bool = True
    cams: list = field(default_factory=lambda: ["CAM 01"])
    focus: list | None = None  # image box (picture coordinates) to cut the snapshot from


def read_video(path, size=(VW, VH)):
    """All frames, at the picture size, and the frame rate."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return out, fps
        out.append(cv2.resize(f, size, interpolation=cv2.INTER_AREA) if f.shape[1::-1] != size else f)


def crop_16x9(img, box, min_w=300):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w = max(min_w, (x1 - x0) * 1.35)
    h = w * 9 / 16
    if h < (y1 - y0) * 1.25:
        h = (y1 - y0) * 1.25
        w = h * 16 / 9
    H_, W_ = img.shape[:2]
    w, h = min(w, W_), min(h, H_)
    ax = int(np.clip(cx - w / 2, 0, W_ - w))
    ay = int(np.clip(cy - h / 2, 0, H_ - h))
    return img[ay:ay + int(h), ax:ax + int(w)].copy()


def chip(c, xy, label, colour, icon=None, anchor="lb", size=12):
    """A label tied to a detection: solid colour, white text."""
    return c.pill(xy, label, size, (255, 255, 255), alpha(colour, 0.92), "semibold", icon=icon,
                  pad=(7, 3), anchor=anchor, tnum=True)


def corner_chips(c, left, right):
    c.pill((10, 10), left, 12, TEXT, alpha(BG, 0.78), "semibold", dot=BLUE, pad=(9, 4))
    x = VW - 10
    for label in right:
        b = c.pill((x, 10), label, 12, TEXT, alpha(BG, 0.78), "semibold", pad=(9, 4), anchor="ra")
        x = b[0] - 6


def feed(c, events, t, thumbs, title="Event Log", rows=4, unit="events", empty="No events yet"):
    shown = [e for e in events if e.feed and e.t <= t]
    x0, y0, x1, y1 = FEED
    y = c.card_title(FEED, title, "notifications", f"{len(shown)} {unit[:-1] if len(shown) == 1 and unit.endswith('s') else unit}")
    if not shown:
        c.text(((x0 + x1) / 2, (y + y1) / 2), empty, 13, "regular", TEXT_3, anchor="mm")
        return
    rh = (y1 - y - 12 - (rows - 1) * 8) // rows
    for k, ev in enumerate(reversed(shown[-rows:])):
        ry = y + 4 + k * (rh + 8)
        c.event_row((x0 + 12, ry, x1 - 12, ry + rh), ev, thumbs.get(id(ev)), now=t - ev.t < 2.0)


def chart_axes(c, box, ymax, ticks, total, xstep=5, fmt=str, xfmt=None):
    x0, y0, x1, y1 = box
    for v in ticks:
        y = y1 - (y1 - y0) * v / ymax
        c.d.line((x0, y, x1, y), fill=alpha(BORDER, 0.9), width=1)
        c.text((x0 - 8, y), fmt(v), 11, "regular", TEXT_3, anchor="rm", tnum=True)
    xfmt = xfmt or ui.clock
    s = 0
    while s <= total + 1e-6:
        x = x0 + (x1 - x0) * s / total
        c.text((x, y1 + 12), xfmt(s), 10, "regular", TEXT_3, anchor="mm", tnum=True)
        s += xstep


def series_chart(img, box, series, total_n, ymax):
    """Thin lines over the box, growing left to right; series is [(values, rgb, fill)]."""
    x0, y0, x1, y1 = box
    for vals, rgb, fill in series:
        if len(vals) < 2:
            continue
        pts = np.array([(x0 + (x1 - x0) * i / max(total_n - 1, 1), y1 - (y1 - y0) * min(v, ymax) / ymax)
                        for i, v in enumerate(vals)], np.float32)
        if fill:
            poly = np.vstack([pts, [[pts[-1, 0], y1], [pts[0, 0], y1]]]).astype(np.int32)
            layer = img.copy()
            cv2.fillPoly(layer, [poly], ui.bgr(rgb), cv2.LINE_AA)
            cv2.addWeighted(layer, 0.12, img, 0.88, 0, img)
        cv2.polylines(img, [pts.astype(np.int32)], False, ui.bgr(rgb), 2, cv2.LINE_AA)


def stills(draw, n, want, path_for):
    """Draw every frame up to the last one wanted (so state builds up), write the wanted ones."""
    for i in range(n):
        img = draw(i)
        if i + 1 in want:
            cv2.imwrite(str(path_for(i + 1)), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if i + 1 >= max(want):
            return


def encode(frames_iter, path, fps):
    import imageio_ffmpeg
    path.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-s", f"{W}x{ui.H}", "-r", str(fps), "-i", "-",
                          "-c:v", "libx264", "-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p",
                          "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)
    for f in frames_iter:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()
