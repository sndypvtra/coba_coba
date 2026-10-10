"""The look of the three videos: one dark theme, one type family, one set of parts.

Text is Inter and icons are Material Symbols Rounded, both bundled in
assets/fonts (SIL OFL 1.1 and Apache 2.0; the icons are a subset with only the
symbols used here). A helmet and a vest have no symbol there, so they are
drawn below. Pillow draws everything on a frame converted once per frame;
the card backgrounds never change, so they are drawn once per video at twice
the size and scaled down, which gives them smooth corners.

Colours are RGB here (Pillow); `bgr()` converts for OpenCV.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parent / "assets" / "fonts"
W, H = 1920, 1080
M, G = 16, 12                     # outer margin, gap between cards
TOP = 56                          # top bar height

BG, SURFACE, SURFACE_2, BORDER = (10, 14, 19), (17, 24, 32), (24, 33, 44), (35, 47, 61)
TEXT, TEXT_2, TEXT_3 = (233, 238, 244), (155, 169, 184), (101, 116, 133)
BLUE, CYAN, GREEN, AMBER, RED = (59, 130, 246), (34, 211, 238), (34, 197, 94), (245, 158, 11), (239, 68, 68)
ORANGE, VIOLET, PINK, YELLOW, SLATE = (251, 146, 60), (167, 139, 250), (244, 114, 182), (250, 204, 21), (148, 163, 184)

SEVERITY = {"high": RED, "medium": AMBER, "low": BLUE, "info": SLATE}
SEVERITY_NAME = {"high": "Tinggi", "medium": "Sedang", "low": "Rendah", "info": "Info"}
CAMERA = [BLUE, ORANGE, GREEN, VIOLET]           # one colour per camera on screen
STATE = {True: GREEN, False: RED, None: (82, 94, 108)}   # PPE: worn, not worn, not judged

_WEIGHT = {"regular": "Inter-Regular.ttf", "medium": "Inter-Medium.ttf", "semibold": "Inter-SemiBold.ttf",
           "bold": "Inter-Bold.ttf"}


def bgr(rgb) -> tuple[int, int, int]:
    return int(rgb[2]), int(rgb[1]), int(rgb[0])


def alpha(rgb, a: float) -> tuple[int, int, int, int]:
    return int(rgb[0]), int(rgb[1]), int(rgb[2]), int(round(255 * a))


try:                                       # icons are ligatures and digits use tabular figures: both need
    from PIL import features                # Pillow's raqm text layout; without it icons become dots
    RAQM = bool(features.check("raqm"))
except Exception:                           # pragma: no cover
    RAQM = False
_LAYOUT = ImageFont.Layout.RAQM if RAQM else ImageFont.Layout.BASIC


@lru_cache(maxsize=128)
def font(size: int, weight: str = "regular"):
    return ImageFont.truetype(str(FONTS / _WEIGHT[weight]), size, layout_engine=_LAYOUT)


@lru_cache(maxsize=32)
def icon_font(size: int):
    return ImageFont.truetype(str(FONTS / "MaterialSymbolsRounded.ttf"), size, layout_engine=_LAYOUT)


def num(x: float, digits: int = 1) -> str:
    """A decimal the Indonesian way: 4,6 not 4.6."""
    return f"{x:.{digits}f}".replace(".", ",")


def clock(t: float) -> str:
    return f"{int(t) // 60:02d}:{int(t) % 60:02d}"


# ------------------------------------------------------------ pictograms
@lru_cache(maxsize=64)
def pictogram(name: str, size: int, rgb: tuple = (255, 255, 255)) -> Image.Image:
    """Helmet or vest as a small RGBA image, drawn at 8x and scaled down for smooth edges."""
    k = 8
    s = size * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (*rgb, 255)
    u = s / 64.0
    if name == "helmet":
        d.pieslice((10 * u, 14 * u, 54 * u, 62 * u), 180, 360, fill=c)          # the shell
        d.rounded_rectangle((3 * u, 37 * u, 61 * u, 45 * u), radius=4 * u, fill=c)  # the brim
        d.rounded_rectangle((29 * u, 12 * u, 35 * u, 30 * u), radius=3 * u, fill=(0, 0, 0, 0))  # the ridge
    elif name == "vest":
        d.polygon([(17 * u, 6 * u), (26 * u, 6 * u), (32 * u, 30 * u), (38 * u, 6 * u), (47 * u, 6 * u),
                   (47 * u, 14 * u), (56 * u, 24 * u), (56 * u, 58 * u), (8 * u, 58 * u), (8 * u, 24 * u),
                   (17 * u, 14 * u)], fill=c)
        d.rectangle((8 * u, 40 * u, 56 * u, 46 * u), fill=(0, 0, 0, 0))           # the reflective band
    return im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------ the canvas
class Canvas:
    """One frame being drawn: Pillow image with an RGBA pen, from and back to OpenCV once."""

    def __init__(self, frame_bgr: np.ndarray):
        self.im = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def bgr(self) -> np.ndarray:
        return cv2.cvtColor(np.asarray(self.im), cv2.COLOR_RGB2BGR)

    # text -------------------------------------------------------------
    def text(self, xy, s: str, size: int = 14, weight: str = "regular", fill=TEXT, anchor: str = "la",
             tnum: bool = False):
        f = font(size, weight)
        feats = ["tnum"] if tnum and RAQM else None
        self.d.text((int(xy[0]), int(xy[1])), str(s), font=f, fill=fill, anchor=anchor, features=feats)
        return self.d.textbbox((int(xy[0]), int(xy[1])), str(s), font=f, anchor=anchor, features=feats)

    @staticmethod
    def width(s: str, size: int = 14, weight: str = "regular", tnum: bool = False) -> int:
        return int(font(size, weight).getlength(str(s), features=["tnum"] if tnum and RAQM else None))

    def fit(self, s: str, size: int, weight: str, room: int) -> str:
        """Shorten with an ellipsis until it fits in `room` pixels."""
        if self.width(s, size, weight) <= room:
            return s
        while len(s) > 2 and self.width(s + "…", size, weight) > room:
            s = s[:-1]
        return s.rstrip() + "…"

    def icon(self, name: str, xy, size: int = 20, fill=TEXT, anchor: str = "mm") -> None:
        if not RAQM:
            self.dot(xy, size / 5, fill)
            return
        self.d.text((int(xy[0]), int(xy[1])), name, font=icon_font(size), fill=fill, anchor=anchor)

    def pictogram(self, name: str, centre, size: int, rgb=(255, 255, 255)) -> None:
        p = pictogram(name, size, tuple(rgb))
        self.im.paste(p, (int(centre[0] - size / 2), int(centre[1] - size / 2)), p)

    # shapes -----------------------------------------------------------
    def rrect(self, box, r: int = 8, fill=None, outline=None, width: int = 1) -> None:
        x0, y0, x1, y1 = (int(v) for v in box)
        if x1 <= x0 or y1 <= y0:
            return
        self.d.rounded_rectangle((x0, y0, x1, y1), radius=min(r, (x1 - x0) // 2, (y1 - y0) // 2), fill=fill,
                                 outline=outline, width=width)

    def dot(self, centre, r: float, fill) -> None:
        x, y = centre
        self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)

    def pill(self, xy, label: str, size: int = 12, fg=TEXT, bg=SURFACE_2, weight: str = "semibold",
             icon: str | None = None, dot=None, pad: tuple[int, int] = (8, 4), anchor: str = "la",
             tnum: bool = False) -> tuple[int, int, int, int]:
        """A rounded label; anchor la / ra / lb / rb / mm on its outer box. Returns the box."""
        isz = size + 4
        w = self.width(label, size, weight, tnum) + 2 * pad[0] + (isz + 4 if icon else 0) + (12 if dot else 0)
        h = size + 2 * pad[1] + 4
        x, y = xy
        if anchor[0] == "r":
            x -= w
        elif anchor[0] == "m":
            x -= w // 2
        if anchor[1] == "b":
            y -= h
        elif anchor[1] == "m":
            y -= h // 2
        self.rrect((x, y, x + w, y + h), r=h // 2, fill=bg)
        cx = x + pad[0]
        if dot:
            self.dot((cx + 3, y + h / 2), 3.5, dot)
            cx += 12
        if icon:
            self.icon(icon, (cx + isz / 2, y + h / 2), isz, fg)
            cx += isz + 4
        self.text((cx, y + h / 2), label, size, weight, fg, anchor="lm", tnum=tnum)
        return x, y, x + w, y + h

    # parts ------------------------------------------------------------
    def card_title(self, box, title: str, icon: str | None = None, right: str | None = None) -> int:
        """A card's heading line; returns the y where its content starts."""
        x0, y0, x1, _ = box
        x = x0 + 16
        if icon:
            self.icon(icon, (x + 9, y0 + 20), 18, TEXT_2)
            x += 26
        self.text((x, y0 + 20), title, 14, "semibold", TEXT, anchor="lm")
        if right:
            self.text((x1 - 16, y0 + 20), right, 12, "regular", TEXT_3, anchor="rm")
        return y0 + 40

    def kpi(self, box, icon: str, label: str, value: str, sub: str = "", accent=BLUE, value_fill=TEXT,
            sub_fill=TEXT_3) -> None:
        """A KPI card's content: icon tile, label, big value, one line under it."""
        x0, y0, x1, y1 = box
        self.rrect((x0 + 14, y0 + 14, x0 + 48, y0 + 48), r=9, fill=alpha(accent, 0.16))
        self.icon(icon, (x0 + 31, y0 + 31), 21, accent)
        self.text((x0 + 60, y0 + 15), label, 13, "medium", TEXT_2)
        self.text((x0 + 60, y0 + 33), value, 28, "bold", value_fill, tnum=True)
        if sub:
            self.text((x0 + 14, y1 - 14), self.fit(sub, 12, "regular", x1 - x0 - 28), 12, "regular", sub_fill,
                      anchor="ls")

    def event_row(self, box, ev, thumb: np.ndarray | None, now: bool = False) -> None:
        """One alert in a feed: severity bar, snapshot, what and when, then who, where and which camera."""
        x0, y0, x1, y1 = box
        sev = SEVERITY[ev.severity]
        self.rrect(box, r=8, fill=alpha(sev, 0.10) if now else SURFACE_2)
        self.rrect((x0, y0 + 6, x0 + 3, y1 - 6), r=1, fill=sev)
        tx = x0 + 14
        th = y1 - y0 - 12
        tw = int(th * 16 / 9)
        if thumb is not None:
            t = cv2.resize(thumb, (tw, th), interpolation=cv2.INTER_AREA)
            timg = Image.fromarray(cv2.cvtColor(t, cv2.COLOR_BGR2RGB))
            self.im.paste(timg, (tx, y0 + 6), rounded_mask(tw, th, 6))
        else:                       # nobody involved is in a camera picture at that moment
            self.rrect((tx, y0 + 6, tx + tw, y0 + 6 + th), r=6, fill=BORDER)
            self.icon("videocam_off", (tx + tw / 2, y0 + 6 + th / 2), 20, TEXT_3)
        tx += tw + 12
        ty = y0 + (y1 - y0) / 2 - 10
        self.icon(ev.icon, (tx + 9, ty), 17, sev)
        right = clock(ev.t)
        room = x1 - tx - 30 - self.width(right, 12, "medium", True) - 14
        self.text((tx + 24, ty), self.fit(ev.title, 14, "semibold", room), 14, "semibold", TEXT, anchor="lm")
        self.text((x1 - 12, ty), right, 12, "medium", TEXT_2, anchor="rm", tnum=True)
        # which camera saw it, always: right-aligned on the second line, the detail fills the rest
        cx = x1 - 10
        for c in reversed(ev.cams[:2]):
            b = self.pill((cx, ty + 21), c, 10, TEXT, BORDER, "semibold", icon="videocam", pad=(6, 2), anchor="rm")
            cx = b[0] - 4
        more = len(ev.cams) - 2
        if more > 0:
            b = self.text((cx - 2, ty + 21), f"+{more}", 10, "medium", TEXT_2, anchor="rm")
            cx = b[0] - 4
        self.text((tx, ty + 21), self.fit(ev.detail, 12, "regular", cx - tx - 8), 12, "regular", TEXT_2,
                  anchor="lm")

    def topbar(self, view: str, site: str, status: str, t: float, total: float, chips: list[str]) -> None:
        self.d.rectangle((0, 0, W, TOP), fill=SURFACE)
        self.d.line((0, TOP - 1, W, TOP - 1), fill=BORDER)
        self.rrect((M, 12, M + 32, 44), r=8, fill=BLUE)
        self.icon("precision_manufacturing", (M + 16, 28), 22, (255, 255, 255))
        x = M + 44
        b = self.text((x, 28), "Factory Vision", 17, "semibold", TEXT, anchor="lm")
        x = b[2] + 14
        for part, fill, weight in ((site, TEXT_2, "medium"), (view, TEXT, "semibold")):
            self.text((x, 28), "/", 16, "regular", TEXT_3, anchor="lm")
            x += 16
            b = self.text((x, 28), part, 15, weight, fill, anchor="lm")
            x = b[2] + 14
        # right side: chips, then the replay clock
        rx = W - M
        b = self.pill((rx, 28), f"{clock(t)} / {clock(total)}", 14, TEXT, SURFACE_2, "semibold", icon="play_arrow",
                      pad=(10, 6), anchor="rm", tnum=True)
        rx = b[0] - 8
        b = self.pill((rx, 28), status, 12, TEXT, alpha(BLUE, 0.20), "semibold", icon="history", pad=(10, 6),
                      anchor="rm")
        rx = b[0] - 8
        for c in chips:
            b = self.pill((rx, 28), c, 12, TEXT_2, SURFACE_2, "medium", pad=(10, 6), anchor="rm")
            rx = b[0] - 8

    def legend(self, xy, items: list[tuple], size: int = 12) -> int:
        """Inline legend: (kind, colour, label) with kind dot / bar / ring / icon:<name>. Returns end x."""
        x, y = xy
        for kind, col, label in items:
            if kind == "dot":
                self.dot((x + 5, y), 4.5, col)
                x += 14
            elif kind == "ring":
                self.d.ellipse((x, y - 5, x + 10, y + 5), outline=col, width=2)
                x += 15
            elif kind == "bar":
                self.rrect((x, y - 4, x + 14, y + 4), r=2, fill=col)
                x += 19
            elif kind.startswith("icon:"):
                self.icon(kind[5:], (x + 7, y), 15, col)
                x += 18
            b = self.text((x, y), label, size, "regular", TEXT_2, anchor="lm")
            x = b[2] + 16
        return x

    def timeline(self, box, t: float, total: float, events: list, title: str = "Lini masa kejadian") -> None:
        """The window as a track: elapsed part, one mark per reported event, the playhead."""
        x0, y0, x1, y1 = box
        self.rrect(box, r=10, fill=SURFACE)
        self.text((x0 + 16, (y0 + y1) / 2), title, 13, "semibold", TEXT, anchor="lm")
        lx = x1 - 16
        for sev in ("info", "low", "medium", "high"):
            b = self.text((lx, (y0 + y1) / 2), SEVERITY_NAME[sev], 12, "regular", TEXT_2, anchor="rm")
            self.dot((b[0] - 9, (y0 + y1) / 2), 4.5, SEVERITY[sev])
            lx = b[0] - 24
        tx0, tx1 = x0 + 190, lx - 24
        ty = (y0 + y1) / 2 - 4
        self.rrect((tx0, ty - 3, tx1, ty + 3), r=3, fill=SURFACE_2)
        px = tx0 + (tx1 - tx0) * min(1.0, t / total)
        self.rrect((tx0, ty - 3, px, ty + 3), r=3, fill=alpha(BLUE, 0.55))
        for k in range(0, int(total) + 1, 5):
            gx = tx0 + (tx1 - tx0) * k / total
            if k % 10 == 0:
                self.text((gx, ty + 15), clock(k), 10, "regular", TEXT_3, anchor="mm", tnum=True)
        for ev in events:
            if ev.t <= t:
                ex = tx0 + (tx1 - tx0) * ev.t / total
                self.dot((ex, ty), 5, SEVERITY[ev.severity])
                self.d.ellipse((ex - 5, ty - 5, ex + 5, ty + 5), outline=SURFACE, width=1)
        self.d.line((px, ty - 11, px, ty + 11), fill=TEXT, width=2)


# ------------------------------------------------------------ background
@lru_cache(maxsize=64)
def rounded_mask(w: int, h: int, r: int) -> Image.Image:
    """An anti-aliased rounded-rectangle mask, for pasting pictures with soft corners."""
    k = 4
    m = Image.new("L", (w * k, h * k), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * k - 1, h * k - 1), radius=r * k, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def board(cards: list[tuple], radius: int = 12) -> np.ndarray:
    """The page background with its card shapes, drawn at 2x and scaled down; BGR."""
    k = 2
    im = Image.new("RGB", (W * k, H * k), BG)
    d = ImageDraw.Draw(im)
    for box in cards:
        x0, y0, x1, y1 = (int(v * k) for v in box)
        d.rounded_rectangle((x0, y0, x1, y1), radius=radius * k, fill=SURFACE, outline=BORDER, width=k)
    im = im.resize((W, H), Image.LANCZOS)
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def paste_rounded(canvas_bgr: np.ndarray, img_bgr: np.ndarray, xy, r: int = 10) -> None:
    """Put a picture on the page with soft rounded corners."""
    x, y = xy
    h, w = img_bgr.shape[:2]
    a = (np.asarray(rounded_mask(w, h, r), np.float32) / 255.0)[..., None]
    dst = canvas_bgr[y:y + h, x:x + w].astype(np.float32)
    canvas_bgr[y:y + h, x:x + w] = (img_bgr.astype(np.float32) * a + dst * (1 - a)).astype(np.uint8)


def area_chart(img_bgr: np.ndarray, box, series: list[tuple[list[float], tuple]], ymax: float | None = None,
               fill_first: bool = True, n_total: int | None = None) -> None:
    """Thin anti-aliased lines over the box; the first series also gets a soft fill under it.

    `n_total` fixes the x axis to the whole window so the chart grows from left to right.
    """
    x0, y0, x1, y1 = box
    top = ymax or max(1.0, max((max(s) for s, _ in series if s), default=1.0))
    for k, (s, rgb) in enumerate(series):
        if len(s) < 2:
            continue
        n = n_total or len(s)
        pts = np.array([(x0 + (x1 - x0) * i / max(n - 1, 1), y1 - (y1 - y0) * min(v, top) / top)
                        for i, v in enumerate(s)], np.float32)
        if k == 0 and fill_first:
            poly = np.vstack([pts, [[pts[-1, 0], y1], [pts[0, 0], y1]]]).astype(np.int32)
            layer = img_bgr.copy()
            cv2.fillPoly(layer, [poly], bgr(rgb), cv2.LINE_AA)
            cv2.addWeighted(layer, 0.16, img_bgr, 0.84, 0, img_bgr)
        cv2.polylines(img_bgr, [pts.astype(np.int32)], False, bgr(rgb), 2, cv2.LINE_AA)


def corner_box(img_bgr: np.ndarray, box, rgb, thickness: int = 2, frac: float = 0.25, fill: float = 0.0) -> None:
    """A detection drawn as four corner brackets, optionally with a faint fill."""
    x1, y1, x2, y2 = (int(v) for v in box)
    if x2 - x1 < 3 or y2 - y1 < 3:
        return
    c = bgr(rgb)
    if fill > 0:
        roi = img_bgr[max(0, y1):y2, max(0, x1):x2]
        if roi.size:
            roi[:] = (roi.astype(np.float32) * (1 - fill) + np.array(c, np.float32) * fill).astype(np.uint8)
    lx, ly = max(4, int((x2 - x1) * frac)), max(4, int((y2 - y1) * frac * 0.6))
    for (ax, ay), (dx, dy) in (((x1, y1), (1, 1)), ((x2, y1), (-1, 1)), ((x1, y2), (1, -1)), ((x2, y2), (-1, -1))):
        cv2.line(img_bgr, (ax, ay), (ax + dx * lx, ay), c, thickness, cv2.LINE_AA)
        cv2.line(img_bgr, (ax, ay), (ax, ay + dy * ly), c, thickness, cv2.LINE_AA)


def lock_box(img_bgr: np.ndarray, box, rgb, thickness: int = 2, fill: float = 0.0, outline: float = 0.65) -> None:
    """A detection: a thin full outline (so the box visibly encloses its object) with strong corners."""
    x1, y1, x2, y2 = (int(round(v)) for v in box)
    h_, w_ = img_bgr.shape[:2]
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w_ - 1, x2), min(h_ - 1, y2)
    if x2 - x1 < 3 or y2 - y1 < 3:
        return
    c = bgr(rgb)
    roi = img_bgr[y1:y2 + 1, x1:x2 + 1]
    if fill > 0:
        roi[:] = (roi.astype(np.float32) * (1 - fill) + np.array(c, np.float32) * fill).astype(np.uint8)
    layer = roi.copy()
    cv2.rectangle(layer, (0, 0), (x2 - x1, y2 - y1), c, 1, cv2.LINE_AA)
    cv2.addWeighted(layer, outline, roi, 1 - outline, 0, roi)
    lx = max(5, int(0.30 * (x2 - x1)))
    ly = max(6, int(0.18 * (y2 - y1)))
    for (ax, ay), (dx, dy) in (((x1, y1), (1, 1)), ((x2, y1), (-1, 1)), ((x1, y2), (1, -1)), ((x2, y2), (-1, -1))):
        cv2.line(img_bgr, (ax, ay), (ax + dx * lx, ay), c, thickness, cv2.LINE_AA)
        cv2.line(img_bgr, (ax, ay), (ax, ay + dy * ly), c, thickness, cv2.LINE_AA)


def dashed(img_bgr: np.ndarray, pts: np.ndarray, rgb, thickness: int = 1, dash: int = 8, gap: int = 6) -> None:
    """A dashed anti-aliased polyline."""
    c = bgr(rgb)
    carry = 0.0
    on = True
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
        seg = float(np.hypot(*(b - a)))
        pos = 0.0
        while pos < seg:
            step = (dash if on else gap) - carry
            end = min(seg, pos + step)
            if on:
                p, q = a + (b - a) * pos / max(seg, 1e-6), a + (b - a) * end / max(seg, 1e-6)
                cv2.line(img_bgr, tuple(int(v) for v in p), tuple(int(v) for v in q), c, thickness, cv2.LINE_AA)
            if end - pos < step:
                carry += end - pos
                break
            pos, carry, on = end, 0.0, not on
