"""Pictures for the videos: camera views and the floor plan, in the look of ui.py.

The promise a viewer has to be able to check with their own eyes is that a dot
on the plan is the person in the camera picture. Three things carry it:

  name       a person is P12 in the picture and P12 on the plan; a forklift F3.
  colour     each camera on screen has one colour: the dot before its name,
             its field of view on the plan, its marker there, and a thin ring
             around every dot it currently sees.
  honesty    a box that did not make it onto the plan - feet out of frame, too
             far to place, not yet confirmed - is still drawn, faint and unlabelled.

Shapes are drawn with OpenCV (anti-aliased) on each picture; every label is
collected as a mark and drawn later, once per frame, on the page's Canvas.
Frames are written straight into ffmpeg as H.264, so the files play anywhere.
"""

from __future__ import annotations

import math
import subprocess
from collections import deque
from pathlib import Path

import cv2
import numpy as np

import config as C
import ops
import ui
from analytics import VEHICLE_BODY, Frame
from scene import Camera, FloorPlan

W, H = ui.W, ui.H
TAG = {"person": "P", "forklift": "F", "pallet_truck": "T", "robot": "R"}
CLASS_RGB = {"person": ui.CYAN, "forklift": ui.ORANGE, "pallet_truck": ui.YELLOW, "robot": ui.VIOLET}
CLASS_ICON = {"forklift": "forklift", "pallet_truck": "pallet", "robot": "smart_toy"}
# an object's colour when it is part of an alert, most serious first
ALERT_RGB = [("near_miss", ui.RED), ("speeding", ui.RED), ("lane", ui.ORANGE), ("wrong_way", ui.PINK)]
UNPLACED = (110, 122, 136)
DARK = (10, 14, 19)


# ------------------------------------------------------------------ output
class VideoOut:
    """Raw BGR frames piped into ffmpeg, H.264 + yuv420p for universal playback."""

    def __init__(self, path: Path, fps: float):
        import imageio_ffmpeg
        self.path = path
        self.p = subprocess.Popen(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo",
             "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)

    def write(self, img: np.ndarray) -> None:
        self.p.stdin.write(np.ascontiguousarray(img).tobytes())

    def close(self) -> None:
        self.p.stdin.close()
        self.p.wait()


class Reader:
    """Sequential reader returning every stride-th frame of a window."""

    def __init__(self, path: Path, start: int, stride: int):
        self.cap = cv2.VideoCapture(str(path))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        self.pos, self.stride = start, stride

    def get(self, frame: int) -> np.ndarray:
        img = None
        while self.pos <= frame:
            ok, img = self.cap.read()
            self.pos += 1
            if not ok:
                return np.zeros((1080, 1920, 3), np.uint8)
        return img


# ------------------------------------------------------------------ labels
def _ink_on(rgb) -> tuple:
    """Dark text on a light chip, white on a dark one."""
    return DARK if (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) > 140 else (255, 255, 255)


class Marks:
    """Labels for one picture, placed clear of each other, drawn later on the page at an offset."""

    def __init__(self, w: int, h: int, taken: list | None = None, memory: dict | None = None):
        self.w, self.h = w, h
        self.taken = list(taken or [])
        self.ops: list[tuple] = []
        # where each object's tag sat last frame: it stays there while that spot is as good as any,
        # so a tag does not hop from side to side as its neighbours move
        self.memory = memory if memory is not None else {}

    def _spot(self, cands, tw: int, th: int, key=None):
        boxes, costs = [], []
        for x0, y0 in cands:
            x0 = min(max(2, x0), self.w - tw - 2)
            y0 = min(max(2, y0), self.h - th - 2)
            box = (x0, y0, x0 + tw, y0 + th)
            boxes.append(box)
            costs.append(sum(max(0, min(box[2], b[2]) - max(box[0], b[0])) *
                             max(0, min(box[3], b[3]) - max(box[1], b[1])) for b in self.taken))
        k = int(np.argmin(costs))
        last = self.memory.get(key) if key is not None else None
        if last is not None and last < len(costs) and costs[last] <= costs[k]:
            k = last
        if key is not None:
            self.memory[key] = k
        self.taken.append(boxes[k])
        return boxes[k]

    @staticmethod
    def tag_size(text: str, size: int, icon: str | None, badges: int) -> tuple[int, int]:
        h = size + 9
        w = ui.Canvas.width(text, size, "semibold") + 12 + (size + 6 if icon else 0) + badges * (h - 2)
        return w, h

    def tag(self, box, text: str, rgb, size: int = 12, icon: str | None = None, badges: list | None = None,
            point: bool = False, key=None) -> None:
        """A coloured tag for an object, PPE badges at its end.

        On a picture the tag always touches its box - on its top edge, inside
        it, or on its bottom edge - so it is never read as someone else's; on
        the plan it sits beside the dot.
        """
        tw, th = self.tag_size(text, size, icon, len(badges or []))
        if point:
            u, v = box
            cands = [(u + 8, v - th - 4), (u - tw - 8, v - th - 4), (u + 8, v + 4), (u - tw - 8, v + 4)]
        else:
            x1, y1, x2, y2 = box
            cands = [(x1, y1 - th), (x2 - tw, y1 - th), (x1 + 1, y1 + 1), (x1, y2), (x2 - tw, y2)]
        self.ops.append(("tag", self._spot(cands, tw, th, key), text, rgb, size, icon, badges or []))

    def chip(self, xy, text: str, size: int = 11, rgb=ui.TEXT, bg=(10, 14, 19, 200), icon: str | None = None,
             dot=None, anchor: str = "la", place: bool = True) -> None:
        """A neutral dark chip (zone names, line counts, camera names)."""
        w = ui.Canvas.width(text, size, "semibold") + 16 + (size + 8 if icon else 0) + (12 if dot else 0)
        h = size + 10
        x, y = xy
        x -= w if anchor[0] == "r" else (w // 2 if anchor[0] == "m" else 0)
        y -= h if anchor[1] == "b" else (h // 2 if anchor[1] == "m" else 0)
        if place:
            box = self._spot([(x, y), (x, y - h - 4), (x, y + h + 4), (x - w // 2, y)], w, h)
        else:
            box = (x, y, x + w, y + h)
        self.ops.append(("chip", box, text, size, rgb, bg, icon, dot))

    def draw(self, cv: ui.Canvas, dx: int = 0, dy: int = 0) -> None:
        for op in self.ops:
            if op[0] == "tag":
                _, (x0, y0, x1, y1), text, rgb, size, icon, badges = op
                x0, y0, x1, y1 = x0 + dx, y0 + dy, x1 + dx, y1 + dy
                cv.rrect((x0, y0, x1, y1), r=6, fill=(*rgb, 235))
                ink = _ink_on(rgb)
                x = x0 + 6
                if icon:
                    cv.icon(icon, (x + (size + 2) / 2, (y0 + y1) / 2), size + 3, ink)
                    x += size + 6
                b = cv.text((x, (y0 + y1) / 2), text, size, "semibold", ink, anchor="lm")
                x = b[2] + 5
                d = y1 - y0 - 4
                for name, state in badges:
                    cx, cy = x + d / 2, (y0 + y1) / 2
                    cv.dot((cx, cy), d / 2, ui.STATE[state])
                    cv.d.ellipse((cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2), outline=(*DARK, 120), width=1)
                    cv.pictogram(name, (cx, cy), int(d * 0.72), (255, 255, 255))
                    x += d + 2
            else:
                _, (x0, y0, x1, y1), text, size, rgb, bg, icon, dot = op
                x0, y0, x1, y1 = x0 + dx, y0 + dy, x1 + dx, y1 + dy
                cv.rrect((x0, y0, x1, y1), r=(y1 - y0) // 2, fill=bg)
                x = x0 + 8
                if dot:
                    cv.dot((x + 3, (y0 + y1) / 2), 3.5, dot)
                    x += 12
                if icon:
                    cv.icon(icon, (x + (size + 4) / 2, (y0 + y1) / 2), size + 4, rgb)
                    x += size + 8
                cv.text((x, (y0 + y1) / 2), text, size, "semibold", rgb, anchor="lm", tnum=True)


# --------------------------------------------------------------- the plan
class PlanView:
    """The floor plan, cropped to a world rectangle, fitted into w x h and toned down to a dark map."""

    def __init__(self, plan: FloorPlan, bounds: tuple, w: int, h: int, inside: np.ndarray | None = None):
        x0, y0, x1, y1 = bounds
        crop = plan.crop(x0, y0, x1, y1)
        s = min(w / crop.image.shape[1], h / crop.image.shape[0])
        crop = crop.resized(s)
        self.w, self.h = w, h
        g = cv2.cvtColor(crop.image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        tone = (g[..., None] * np.array([0.34, 0.31, 0.28], np.float32) + np.array([16, 12, 9], np.float32))
        self.img = np.full((h, w, 3), ui.bgr(ui.SURFACE), np.uint8)
        oy, ox = (h - crop.image.shape[0]) // 2, (w - crop.image.shape[1]) // 2
        self.img[oy:oy + crop.image.shape[0], ox:ox + crop.image.shape[1]] = np.clip(tone, 0, 255).astype(np.uint8)
        self.A = np.array([[1, 0, ox], [0, 1, oy], [0, 0, 1.0]]) @ crop.A
        self.px_per_m = abs(self.A[0, 0])
        self.base = self.img.copy()
        self.taken: list = []

    def pt(self, x, y) -> tuple[int, int]:
        u = self.A[0, 0] * x + self.A[0, 1] * y + self.A[0, 2]
        v = self.A[1, 0] * x + self.A[1, 1] * y + self.A[1, 2]
        return int(round(u)), int(round(v))

    def poly(self, pts) -> np.ndarray:
        return np.array([self.pt(x, y) for x, y in pts], np.int32)


PLACE_SCALE = 0.25      # m/px: as far as a camera places people (world.CLASS["person"])


def fov_mask(view: PlanView, cam: Camera, inside: np.ndarray | None) -> np.ndarray:
    """Plan pixels this camera can place a person on, cut to the building."""
    fp = cam.footprint(PLACE_SCALE, radius_m=80.0, step_m=0.25)
    m = np.zeros((view.h, view.w), np.uint8)
    if len(fp) > 2:
        cv2.fillPoly(m, [view.poly(fp)], 1)
    if inside is not None:
        m &= inside.astype(np.uint8)
    return m


ZONE_RGB = {"area": ui.SLATE, "vehicle_lane": ui.AMBER, "one_way": ui.PINK}


def zone_share(cam: Camera, zone) -> float:
    """The share of a zone's floor this camera can place a person on."""
    from analytics import inside
    fp = cam.footprint(PLACE_SCALE, radius_m=80.0, step_m=0.25)
    if len(fp) < 3:
        return 0.0
    xs, ys = [p[0] for p in zone.polygon], [p[1] for p in zone.polygon]
    gx, gy = np.meshgrid(np.linspace(min(xs), max(xs), 40), np.linspace(min(ys), max(ys), 40))
    gx, gy = gx.ravel(), gy.ravel()
    inz = inside(gx, gy, zone.polygon)
    return float(np.mean(inside(gx[inz], gy[inz], fp))) if inz.any() else 0.0


def _blend_poly(img, pts, rgb, a: float) -> None:
    layer = img.copy()
    cv2.fillPoly(layer, [pts], ui.bgr(rgb), cv2.LINE_AA)
    cv2.addWeighted(layer, a, img, 1 - a, 0, img)


def plan_static(view: PlanView, cams: dict[str, Camera], shown: list[str], other: list[str],
                zones, lines, inside: np.ndarray | None = None) -> np.ndarray:
    """Zones, lines, fields of view and camera markers - drawn once."""
    img = view.base.copy()
    for z in zones:
        p = view.poly(z.polygon)
        rgb = ZONE_RGB.get(z.kind, ui.SLATE)
        _blend_poly(img, p, rgb, 0.16 if z.kind != "area" else 0.08)
        if z.kind == "area":
            ui.dashed(img, np.vstack([p, p[:1]]), rgb, 1, 6, 5)
        else:
            cv2.polylines(img, [p], True, ui.bgr(rgb), 1, cv2.LINE_AA)
        if z.kind == "one_way":
            cx, cy = np.mean([q[0] for q in z.polygon]), np.mean([q[1] for q in z.polygon])
            a = view.pt(cx - z.direction[0] * 3, cy - z.direction[1] * 3)
            b = view.pt(cx + z.direction[0] * 3, cy + z.direction[1] * 3)
            cv2.arrowedLine(img, a, b, ui.bgr(ui.PINK), 2, cv2.LINE_AA, tipLength=0.35)
    for ln in lines:
        a, b = view.pt(*ln.a), view.pt(*ln.b)
        cv2.line(img, a, b, ui.bgr(ui.TEXT), 2, cv2.LINE_AA)
        for p in (a, b):
            cv2.circle(img, p, 3, ui.bgr(ui.TEXT), -1, cv2.LINE_AA)
    for k, cid in enumerate(shown):
        rgb = ui.CAMERA[k]
        m = fov_mask(view, cams[cid], inside)
        layer = img.copy()
        layer[m.astype(bool)] = ui.bgr(rgb)
        cv2.addWeighted(layer, 0.07, img, 0.93, 0, img)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:
            ui.dashed(img, np.vstack([c[:, 0], c[:1, 0]]), rgb, 1, 7, 5)
    for cid in list(other) + list(shown):
        cam = cams[cid]
        rgb = ui.CAMERA[shown.index(cid)] if cid in shown else ui.TEXT_3
        u, v = view.pt(cam.centre[0], cam.centre[1])
        hx, hy = view.pt(cam.centre[0] + 2.2 * math.cos(cam.heading), cam.centre[1] + 2.2 * math.sin(cam.heading))
        cv2.line(img, (u, v), (hx, hy), ui.bgr(rgb), 2, cv2.LINE_AA)
        cv2.circle(img, (u, v), 5 if cid in shown else 3, ui.bgr(rgb), -1, cv2.LINE_AA)
        if cid in shown:
            cv2.circle(img, (u, v), 8, ui.bgr(rgb), 1, cv2.LINE_AA)
        view.taken.append((min(u, hx) - 6, min(v, hy) - 6, max(u, hx) + 6, max(v, hy) + 6))
    return img


def plan_labels(view: PlanView, cams, shown: list[str], zones, lines, fr: Frame, scene: str,
                memory: dict | None = None, colours: list | None = None) -> Marks:
    """The plan's names: shown cameras, numbered zones, lines with their counts."""
    colours = colours or ui.CAMERA
    mk = Marks(view.w, view.h, view.taken, memory)
    for k, cid in enumerate(shown):
        u, v = view.pt(cams[cid].centre[0], cams[cid].centre[1])
        mk.chip((u + 10, v - 10), ops.cam_label(cid), 10, colours[k], (10, 14, 19, 215), anchor="lb")
    for k, z in enumerate(zones):          # numbered; the names and counts are listed under the plan
        xs, ys = [p[0] for p in z.polygon], [p[1] for p in z.polygon]
        u, v = view.pt(min(xs), max(ys))
        mk.chip((u + 2, v + 2), f"{k + 1}", 10, ZONE_RGB.get(z.kind, ui.SLATE) if z.kind != "area" else ui.TEXT,
                (10, 14, 19, 215))
    for ln in lines:
        a, b = view.pt(*ln.a), view.pt(*ln.b)
        i, o = fr.line_totals.get(ln.name, (0, 0))
        letter = ln.name.split(" ·")[0].replace("Garis ", "")
        mk.chip(((a[0] + b[0]) // 2 + 6, (a[1] + b[1]) // 2), f"{letter}  ↑{i} ↓{o}", 10, ui.TEXT,
                (10, 14, 19, 215), anchor="lm")
    return mk


class Heat:
    """Where people have been, accumulated over the window."""

    def __init__(self, view: PlanView, radius_m: float = 1.2):
        self.acc = np.zeros((view.h, view.w), np.float32)
        self.view = view
        self.sigma = max(1.0, radius_m * view.px_per_m / 2)

    def add(self, x: float, y: float) -> None:
        u, v = self.view.pt(x, y)
        if 0 <= u < self.view.w and 0 <= v < self.view.h:
            self.acc[v, u] += 1.0

    def blend(self, img: np.ndarray) -> None:
        if self.acc.max() <= 0:
            return
        h = cv2.GaussianBlur(self.acc, (0, 0), self.sigma)
        h /= max(float(np.percentile(h[h > 0], 99.5)), 1e-6)
        h = np.clip(h, 0, 1)
        col = cv2.applyColorMap((h * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
        a = (np.clip((h - 0.08) / 0.7, 0, 1) * 0.42)[..., None]
        img[:] = (img * (1 - a) + col * a).astype(np.uint8)


def person_rgb(o, ppe_state=None) -> tuple:
    """A person's colour: an alert first, then their PPE (green complete, amber not), else cyan."""
    for a, rgb in ALERT_RGB:
        if a in o.alerts:
            return rgb
    if ppe_state is not None and ppe_state != (None, None):
        return ui.GREEN if all(ppe_state) else ui.AMBER
    return ui.CYAN


def plan_objects(img: np.ndarray, view: PlanView, fr: Frame, seen_by: dict[int, set], shown: list[str],
                 trails: dict, mk: Marks, ppe: dict | None = None, label_all: bool = False,
                 colours: list | None = None) -> None:
    """People, vehicles, their last three seconds, and the near-miss link, on the plan.

    `colours[i]` is the ring colour of `shown[i]` (default: the camera colours).
    """
    colours = colours or ui.CAMERA
    for o in fr.objects:
        trails.setdefault(o.gid, deque(maxlen=30)).append((o.x, o.y))
    layer = img.copy()
    for gid, tr in trails.items():
        if len(tr) > 1:
            pts = np.array([view.pt(x, y) for x, y in tr], np.int32)
            cv2.polylines(layer, [pts], False, ui.bgr(ui.CYAN), 1, cv2.LINE_AA)
    cv2.addWeighted(layer, 0.35, img, 0.65, 0, img)
    for p, v, d in fr.near_pairs:
        po = next((o for o in fr.objects if o.gid == p), None)
        vo = next((o for o in fr.objects if o.gid == v), None)
        if po and vo:
            cv2.line(img, view.pt(po.x, po.y), view.pt(vo.x, vo.y), ui.bgr(ui.RED), 2, cv2.LINE_AA)
    for x, y, n in fr.crowd_spots:
        cv2.circle(img, view.pt(x, y), int(C.CROWD_RADIUS_M * view.px_per_m), ui.bgr(ui.BLUE), 1, cv2.LINE_AA)
    for o in sorted(fr.objects, key=lambda o: o.cls == "person"):
        u, v = view.pt(o.x, o.y)
        rings = [colours[shown.index(c)] for c in sorted(seen_by.get(o.gid, ())) if c in shown]
        if o.cls in VEHICLE_BODY:
            L, Wd = VEHICLE_BODY[o.cls]
            c, s = math.cos(o.heading), math.sin(o.heading)
            corners = [(o.x + c * a - s * b, o.y + s * a + c * b)
                       for a, b in ((-L / 2, -Wd / 2), (L / 2, -Wd / 2), (L / 2, Wd / 2), (-L / 2, Wd / 2))]
            p = view.poly(corners)
            rgb = ui.RED if ("near_miss" in o.alerts or "speeding" in o.alerts) else CLASS_RGB[o.cls]
            cv2.fillPoly(img, [p], ui.bgr(rgb), cv2.LINE_AA)
            cv2.polylines(img, [p], True, ui.bgr(DARK), 1, cv2.LINE_AA)
            if o.cls == "forklift" and o.reliable and o.speed > C.VEHICLE_MOVING_MS:
                tip = view.pt(o.x + c * (L / 2 + 0.9), o.y + s * (L / 2 + 0.9))
                cv2.arrowedLine(img, (u, v), tip, ui.bgr(ui.TEXT), 1, cv2.LINE_AA, tipLength=0.5)
            for k, rc in enumerate(rings):
                cv2.polylines(img, [p], True, ui.bgr(rc), 1 + k, cv2.LINE_AA)
            lab = f"{TAG[o.cls]}{o.gid}" + (f" · {speed_text(o)}" if o.cls == "forklift" and o.reliable else "")
            mk.tag((u, v), lab, rgb, 10, point=True, key=o.gid)
            continue
        rgb = person_rgb(o, (ppe or {}).get(o.gid))
        for k, rc in enumerate(rings):
            cv2.circle(img, (u, v), 7 + 3 * k, ui.bgr(rc), 1, cv2.LINE_AA)
        cv2.circle(img, (u, v), 5, ui.bgr(DARK), -1, cv2.LINE_AA)
        cv2.circle(img, (u, v), 4, ui.bgr(rgb if o.walking or rgb != ui.CYAN else (186, 230, 253)), -1, cv2.LINE_AA)
        if rings or o.alerts or label_all:
            mk.tag((u, v), f"P{o.gid}", rgb, 10, point=True, key=o.gid)


# --------------------------------------------------------------- the cameras
def project_poly(cam: Camera, pts, step_m: float = 0.1) -> list[np.ndarray]:
    """A floor outline as image segments, kept only where the camera places things.

    Drawn all the way to the horizon, a line's far end crowds into the
    vanishing point and its label lands on top of every other label.
    """
    dense = []
    n = len(pts)
    closed = len(pts) > 2
    for i in range(n if closed else n - 1):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        k = max(2, int(math.hypot(x1 - x0, y1 - y0) / step_m))
        for t in np.linspace(0, 1, k, endpoint=False):
            dense.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    if not closed:
        dense.append(pts[-1])
    d = np.array(dense)
    ok = cam.sees(d[:, 0], d[:, 1], PLACE_SCALE)
    uv = cam.to_image(np.column_stack([d, np.zeros(len(d))]))
    segs, cur = [], []
    for good, p in zip(ok, uv):
        if good:
            cur.append(p)
        elif cur:
            if len(cur) > 1:
                segs.append(np.array(cur))
            cur = []
    if len(cur) > 1:
        segs.append(np.array(cur))
    return segs


class CameraOverlay:
    """What is fixed in one camera's picture at one size: its zones and lines, projected once."""

    def __init__(self, cam: Camera, size: tuple[int, int], zones, lines):
        self.cam, self.size = cam, size
        s = size[0] / cam.width
        self.zones = [(z, [(seg * s).astype(np.int32) for seg in project_poly(cam, list(z.polygon))]) for z in zones]
        self.lines = [(ln, [(seg * s).astype(np.int32) for seg in project_poly(cam, [ln.a, ln.b])]) for ln in lines]


def camera_view(img: np.ndarray, ov: CameraOverlay, rows: np.ndarray, classes: list[str], frame: int, fr: Frame,
                key_to_gid: dict, placed: set, big: bool = False, ppe: dict | None = None,
                header: tuple | None = None, memory: dict | None = None) -> tuple[np.ndarray, Marks]:
    """One camera picture scaled to its tile, with the floor's zones and lines and every detection.

    Returns the picture and its labels (drawn later on the page). `ppe`, when
    given, is each person's live helmet / vest status, shown as two badges.
    `header` = (camera colour, camera label, place name, people count);
    `memory` keeps each tag's side from one frame to the next (one per camera).
    """
    tw, th = ov.size
    cam = ov.cam
    s = tw / cam.width
    out = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
    mk = Marks(tw, th, memory=memory)
    fs = 12 if big else 10
    if header:
        mk.taken += [(0, 0, tw, 40 if big else 32)]
    # the floor: zones as outlines, lines solid
    layer = out.copy()
    for z, segs in ov.zones:
        rgb = ZONE_RGB.get(z.kind, ui.SLATE)
        for seg in segs:
            if z.kind == "area":
                ui.dashed(layer, seg, (226, 232, 240), 2 if big else 1, 10, 7)
            else:
                cv2.polylines(layer, [seg], False, ui.bgr(rgb), 3 if big else 2, cv2.LINE_AA)
    cv2.addWeighted(layer, 0.6, out, 0.4, 0, out)
    if big:
        for z, segs in ov.zones:
            if not segs or z.kind == "area":
                continue
            seg = max(segs, key=len)
            if np.hypot(*(seg[-1] - seg[0])) >= 120:
                mid = seg[len(seg) // 2]
                mk.chip((int(mid[0]), int(mid[1]) + 6), ops.zone_label(z.name), 11, ZONE_RGB[z.kind],
                        (10, 14, 19, 190))
    for ln, segs in ov.lines:
        for q in segs:
            cv2.polylines(out, [q], False, ui.bgr(ui.TEXT), 2, cv2.LINE_AA)
            if np.hypot(*(q[-1] - q[0])) >= (110 if big else 60):
                mid = q[len(q) // 2]
                i, o = fr.line_totals.get(ln.name, (0, 0))
                text = f"{ops.line_label(ln.name)}  ↑{i} ↓{o}" if big else ln.name.split(" ·")[0].replace("Garis ", "")
                mk.chip((int(mid[0]), int(mid[1]) + 4), text, fs, ui.TEXT, (10, 14, 19, 205))
    objs = {o.gid: o for o in fr.objects}
    labels = []
    on_plan = 0
    for d in rows[rows[:, 0] == frame]:
        box = (d[2:6] * s).astype(int)
        cls = classes[int(d[7])]
        gid = key_to_gid.get((cam.id, int(d[1]))) if d[1] >= 0 else None
        if gid is not None and gid in objs and gid in placed:
            o = objs[gid]
            state = (ppe or {}).get(gid) if cls == "person" else None
            if cls == "person":
                rgb = person_rgb(o, state if ppe is not None else None)
            else:
                rgb = ui.RED if ("near_miss" in o.alerts or "speeding" in o.alerts) else CLASS_RGB[cls]
            alert = any(a in o.alerts for a, _ in ALERT_RGB)
            ui.lock_box(out, box, rgb, 2, fill=0.12 if alert else 0.0)
            labels.append((o, cls, box, rgb, state))
            on_plan += cls == "person" and d[5] - d[3] >= 40
        else:
            # seen and followed by the camera, but not on the plan (feet out of frame, too far
            # to place precisely, not yet confirmed): boxed in grey, without a name
            ui.lock_box(out, box, UNPLACED, 1, outline=0.8)
    # nearest first: the label of the biggest box is the one that keeps its place
    for o, cls, box, rgb, state in sorted(labels, key=lambda t: -(t[2][3] - t[2][1])):
        text = f"{TAG[cls]}{o.gid}"
        if cls == "forklift" and o.reliable:
            text += f" · {speed_text(o)}"
        badges = None
        if cls == "person" and ppe is not None:
            h, v = state if state else (None, None)
            badges = [("helmet", h), ("vest", v)]
        mk.tag(tuple(box), text, rgb, fs, icon=CLASS_ICON.get(cls), badges=badges, key=o.gid)
    if header:
        rgb, label, place, n = header
        size = 12 if big else 10
        mk.chip((10, 10), f"{label} · {place}", size, ui.TEXT, (10, 14, 19, 205), dot=rgb, place=False)
        # the people this camera shows, and how many of them are named on the plan (the others: grey boxes)
        mk.chip((tw - 10, 10), f"{n} orang · {min(on_plan, n)} di peta", size, ui.TEXT, (10, 14, 19, 205),
                icon="groups", anchor="ra", place=False)
    return out, mk


def key_index(fr_blobs, confirmed: set) -> tuple[dict, dict]:
    """(camera, tracker id) -> global id, and global id -> cameras seeing it, at one frame."""
    k2g, seen = {}, {}
    for b in fr_blobs:
        if b.gid not in confirmed:
            continue
        for m in b.members:
            if m.track >= 0:
                k2g[(m.cam, m.track)] = b.gid
        seen[b.gid] = {m.cam for m in b.members}
    return k2g, seen


def speed_text(o) -> str:
    """The speed written beside a forklift.

    Above the limit only once it has lasted the full second the speeding alert
    needs; shorter, it reads "<= limit". On this site every such short reading
    was a position jump between cameras, not a forklift going faster (F12 shown
    at 11 km/h against 2.9 true, F13 at 9 against 3.6).
    """
    kmh = o.speed * 3.6
    if kmh > C.SPEED_LIMIT_KMH and "speeding" not in o.alerts:
        return f"≤{C.SPEED_LIMIT_KMH:.0f} km/j"
    return f"{kmh:.0f} km/j"
