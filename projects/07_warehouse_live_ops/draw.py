"""Drawing helpers shared by the check images and the videos.

Text goes through Pillow so it can use a real font; everything else is OpenCV.
Text is queued and drawn in one pass per picture, because converting a 1080p
frame between OpenCV and Pillow for every label would cost more than the label.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIRS = [Path("/usr/share/fonts/truetype/dejavu"),
             Path("/usr/share/fonts/dejavu"), Path("/Library/Fonts"),
             Path("C:/Windows/Fonts")]


def _find(name: str) -> str | None:
    for d in FONT_DIRS:
        p = d / name
        if p.exists():
            return str(p)
    return None


REGULAR = _find("DejaVuSans.ttf") or _find("Arial.ttf") or _find("arial.ttf")
BOLD = _find("DejaVuSans-Bold.ttf") or _find("Arial Bold.ttf") or _find("arialbd.ttf")


@lru_cache(maxsize=64)
def font(size: int, bold: bool = False):
    path = BOLD if bold else REGULAR
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def bgr(hex_colour: str) -> tuple[int, int, int]:
    h = hex_colour.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return b, g, r


# One colour per camera on screen, used for its tile border, its field of view
# on the plan and the ring around everything it sees - the link a viewer follows
# between a tile and the plan.
CAMERA_COLOURS = [bgr(c) for c in ("#2a78d6", "#eb6834", "#16a34a", "#a855f7",
                                   "#0ea5b7", "#e11d74", "#eab308")]

INK = bgr("#f2f2f0")
MUTED = bgr("#9a9a96")
FAINT = bgr("#5c5c58")
BG = bgr("#111214")
PANEL = bgr("#18191c")
GOOD = bgr("#22c55e")
WARN = bgr("#fab219")
BAD = bgr("#ef4444")
PERSON = bgr("#38bdf8")
PERSON_IDLE = bgr("#f8fafc")
FORKLIFT = bgr("#f97316")
PALLET = bgr("#facc15")
ROBOT = bgr("#c084fc")


class Texts:
    """Queue text for one picture, then draw it all at once."""

    def __init__(self):
        self.items = []

    def add(self, s: str, xy, size: int = 16, colour=INK, bold: bool = False,
            anchor: str = "la", bg=None, pad: int = 3):
        self.items.append((str(s), (int(xy[0]), int(xy[1])), size, colour, bold, anchor, bg, pad))

    def width(self, s: str, size: int, bold: bool = False) -> int:
        return int(font(size, bold).getlength(str(s)))

    def flush(self, img: np.ndarray) -> np.ndarray:
        if not self.items:
            return img
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(pil)
        for s, xy, size, colour, bold, anchor, bg, pad in self.items:
            f = font(size, bold)
            if bg is not None:
                x0, y0, x1, y1 = d.textbbox(xy, s, font=f, anchor=anchor)
                d.rectangle((x0 - pad, y0 - pad, x1 + pad, y1 + pad), fill=bg[::-1])
            d.text(xy, s, font=f, fill=colour[::-1], anchor=anchor)
        self.items = []
        img[:] = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
        return img


def _best_spot(candidates, tw: int, th: int, taken: list, w: int, h: int):
    """The first candidate corner whose label box stays in the picture and clear of `taken`,
    else the one that overlaps least (leaving the picture costs most)."""
    best, best_cost = None, None
    for x0, y0 in candidates:
        box = (x0, y0, x0 + tw, y0 + th)
        off = max(0, -box[0]) + max(0, box[2] - w) + max(0, -box[1]) + max(0, box[3] - h)
        hit = sum(max(0, min(box[2], b[2]) - max(box[0], b[0])) * max(0, min(box[3], b[3]) - max(box[1], b[1]))
                  for b in taken)
        cost = off * 1000 + hit
        if best_cost is None or cost < best_cost:
            best, best_cost = box, cost
        if cost == 0:
            break
    return best


def place_label(T: Texts, text: str, at: tuple[int, int], size: int, colour, taken: list,
                w: int, h: int, gap: int = 8, bg=BG, bold: bool = True) -> None:
    """Put a label beside a point where it fits on the picture and covers no other label.

    Tries right-above, left-above, right-below and left-below of the point; the
    first that stays inside the picture and clear of everything in `taken`
    (rectangles x0, y0, x1, y1) wins, otherwise the one that overlaps least.
    The chosen rectangle is added to `taken`.
    """
    tw, th = T.width(text, size, bold) + 2, size + 4
    u, v = int(at[0]), int(at[1])
    best = _best_spot(((u + gap, v - gap - th), (u - gap - tw, v - gap - th),
                       (u + gap, v + gap - 2), (u - gap - tw, v + gap - 2)), tw, th, taken, w, h)
    taken.append(best)
    T.add(text, (best[0] + 1, best[1] + 1), size, colour, bold, bg=bg, pad=1)


def box_label(T: Texts, text: str, box, size: int, colour, taken: list, w: int, h: int, bg=BG) -> None:
    """Label a box: above its left corner, else above its right one, below it, or just inside its top.

    Always inside the picture, and clear of the labels already in `taken`.
    """
    x1, y1, x2, y2 = (int(v) for v in box)
    tw, th = T.width(text, size, True) + 2, size + 4
    cands = [(x1, y1 - th - 1), (x2 - tw, y1 - th - 1), (x1, y2 + 1), (x1 + 1, y1 + 1)]
    cands = [(min(max(0, x), w - tw), min(max(0, y), h - th)) for x, y in cands]
    best = _best_spot(cands, tw, th, taken, w, h)
    taken.append(best)
    T.add(text, (best[0] + 1, best[1] + 1), size, colour, True, bg=bg, pad=1)


def blend(img: np.ndarray, overlay: np.ndarray, mask: np.ndarray, alpha: float) -> None:
    """Mix `overlay` into `img` where `mask` is set, in place."""
    m = mask.astype(bool)
    img[m] = (img[m].astype(np.float32) * (1 - alpha) + overlay[m].astype(np.float32) * alpha
              ).astype(np.uint8)


def fill_alpha(img: np.ndarray, pts: np.ndarray, colour, alpha: float) -> None:
    if len(pts) < 3:
        return
    layer = img.copy()
    cv2.fillPoly(layer, [np.asarray(pts, np.int32)], colour, cv2.LINE_AA)
    cv2.addWeighted(layer, alpha, img, 1 - alpha, 0, img)


def fit(img: np.ndarray, w: int, h: int) -> np.ndarray:
    """Scale to fit inside w x h, keeping the aspect ratio, on a dark canvas."""
    s = min(w / img.shape[1], h / img.shape[0])
    r = cv2.resize(img, (max(1, int(img.shape[1] * s)), max(1, int(img.shape[0] * s))),
                   interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    out = np.full((h, w, 3), BG, np.uint8)
    y0, x0 = (h - r.shape[0]) // 2, (w - r.shape[1]) // 2
    out[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] = r
    return out
