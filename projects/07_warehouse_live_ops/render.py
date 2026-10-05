"""The three videos. Every CCTV tile is tied to the plan, by colour and by name.

The promise a viewer has to be able to check with their own eyes is that a dot
on the plan is the person in the tile. Four things carry it:

  colour     each camera on screen has one colour: its tile border, its field
             of view drawn on the plan, its marker on the plan, and a ring
             around every dot it currently sees.
  name       a person is P12 in the tile and P12 on the plan; a forklift F3.
  echoes     a person placed by *other* cameras is drawn into a tile as a small
             hollow circle at the floor point those cameras computed. If the
             calibration were wrong, the circles would float off the people.
  honesty    a box that did not make it onto the plan - feet out of frame, too
             far to place, not yet confirmed - is still drawn, in grey.

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
import draw as dr
from analytics import VEHICLE_BODY, Frame
from scene import Camera, FloorPlan

W, H = 1920, 1080
HEADER = 48
TAG = {"person": "P", "forklift": "F", "pallet_truck": "T", "robot": "R"}
CLASS_COLOUR = {"person": dr.PERSON, "forklift": dr.FORKLIFT, "pallet_truck": dr.PALLET, "robot": dr.ROBOT}
ALERT_COLOUR = {"near_miss": dr.BAD, "speeding": dr.BAD, "lane": dr.bgr("#fb923c"),
                "wrong_way": dr.bgr("#f472b6"), "idle": dr.WARN, "crowd": dr.bgr("#f87171")}
ALERT_NAME = {"near_miss": "nyaris tertabrak", "speeding": "ngebut", "lane": "di jalur forklift",
              "wrong_way": "salah arah", "idle": "diam lama", "crowd": "kerumunan"}


# ------------------------------------------------------------------ output
class VideoOut:
    """Raw BGR frames piped into ffmpeg, H.264 + yuv420p for universal playback."""

    def __init__(self, path: Path, fps: float):
        import imageio_ffmpeg
        self.path = path
        self.p = subprocess.Popen(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo",
             "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
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


# --------------------------------------------------------------- the plan
class PlanView:
    """The floor plan, cropped to a world rectangle and fitted into w x h."""

    def __init__(self, plan: FloorPlan, bounds: tuple, w: int, h: int, dim: float = 0.62):
        x0, y0, x1, y1 = bounds
        crop = plan.crop(x0, y0, x1, y1)
        s = min(w / crop.image.shape[1], h / crop.image.shape[0])
        crop = crop.resized(s)
        self.w, self.h = w, h
        self.img = np.full((h, w, 3), dr.BG, np.uint8)
        oy, ox = (h - crop.image.shape[0]) // 2, (w - crop.image.shape[1]) // 2
        self.img[oy:oy + crop.image.shape[0], ox:ox + crop.image.shape[1]] = (crop.image * dim).astype(np.uint8)
        self.A = np.array([[1, 0, ox], [0, 1, oy], [0, 0, 1.0]]) @ crop.A
        self.px_per_m = abs(self.A[0, 0])
        self.base = self.img.copy()

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


def draw_static(view: PlanView, cams: dict[str, Camera], shown: list[str], other: list[str],
                zones, lines, inside: np.ndarray | None = None) -> np.ndarray:
    """Zones, lines, fields of view and camera markers - drawn once.

    `inside`, in the view's pixels, is the building's floor: a field of view
    stops at the wall even though the geometry would carry it on outside.
    """
    img = view.base.copy()
    T = dr.Texts()
    marks = [view.pt(cams[c].centre[0], cams[c].centre[1]) for c in list(other) + list(shown)]
    taken = [(u - 6, v - 6, u + 6, v + 6) for u, v in marks]
    for z in zones:
        p = view.poly(z.polygon)
        if z.kind == "vehicle_lane":
            dr.fill_alpha(img, p, dr.FORKLIFT, 0.20)
            cv2.polylines(img, [p], True, dr.FORKLIFT, 1, cv2.LINE_AA)
        elif z.kind == "one_way":
            dr.fill_alpha(img, p, dr.bgr("#f472b6"), 0.16)
            cv2.polylines(img, [p], True, dr.bgr("#f472b6"), 1, cv2.LINE_AA)
            cx, cy = np.mean([q[0] for q in z.polygon]), np.mean([q[1] for q in z.polygon])
            a = view.pt(cx - z.direction[0] * 3, cy - z.direction[1] * 3)
            b = view.pt(cx + z.direction[0] * 3, cy + z.direction[1] * 3)
            cv2.arrowedLine(img, a, b, dr.bgr("#f472b6"), 2, cv2.LINE_AA, tipLength=0.35)
        else:
            dr.fill_alpha(img, p, dr.bgr("#94a3b8"), 0.10)
            cv2.polylines(img, [p], True, dr.bgr("#cbd5e1"), 1, cv2.LINE_AA)
    for ln in lines:
        a, b = view.pt(*ln.a), view.pt(*ln.b)
        cv2.line(img, a, b, dr.INK, 2, cv2.LINE_AA)
        dr.place_label(T, ln.name.split(" ·")[0].replace("Garis ", ""), b, 13, dr.INK, taken, view.w, view.h, 4)
    for cid in other:
        cs, _ = cv2.findContours(fov_mask(view, cams[cid], inside), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, cs, -1, dr.FAINT, 1, cv2.LINE_AA)
    for k, cid in enumerate(shown):
        col = dr.CAMERA_COLOURS[k]
        m = fov_mask(view, cams[cid], inside)
        dr.blend(img, np.full_like(img, col), m.astype(bool), 0.13)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, cs, -1, col, 2, cv2.LINE_AA)
    for cid in list(other) + list(shown):
        cam = cams[cid]
        col = dr.CAMERA_COLOURS[shown.index(cid)] if cid in shown else dr.FAINT
        u, v = view.pt(cam.centre[0], cam.centre[1])
        hx, hy = view.pt(cam.centre[0] + 2.5 * math.cos(cam.heading), cam.centre[1] + 2.5 * math.sin(cam.heading))
        cv2.arrowedLine(img, (u, v), (hx, hy), col, 2, cv2.LINE_AA, tipLength=0.4)
        cv2.circle(img, (u, v), 5 if cid in shown else 3, col, -1, cv2.LINE_AA)
        # the heading arrow is part of the marker: a label must not cover it
        taken.append((min(u, hx) - 3, min(v, hy) - 3, max(u, hx) + 3, max(v, hy) + 3))
    for cid in shown:
        u, v = view.pt(cams[cid].centre[0], cams[cid].centre[1])
        dr.place_label(T, cid.replace("Camera_", "CCTV "), (u, v), 13, dr.CAMERA_COLOURS[shown.index(cid)],
                    taken, view.w, view.h)
    T.flush(img)
    view.taken = taken            # moving labels are kept off these, every frame
    return img


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
        a = (np.clip((h - 0.06) / 0.7, 0, 1) * 0.55)[..., None]
        img[:] = (img * (1 - a) + col * a).astype(np.uint8)


def draw_objects(img: np.ndarray, view: PlanView, fr: Frame, seen_by: dict[int, set],
                 shown: list[str], trails: dict, T: dr.Texts, label_all: bool = False) -> None:
    taken = list(getattr(view, "taken", []))
    for o in fr.objects:
        tr = trails.setdefault(o.gid, deque(maxlen=30))
        tr.append((o.x, o.y))
    for gid, tr in trails.items():
        if len(tr) > 1:
            pts = np.array([view.pt(x, y) for x, y in tr], np.int32)
            cv2.polylines(img, [pts], False, dr.FAINT, 1, cv2.LINE_AA)
    for p, v, d in fr.near_pairs:
        po = next((o for o in fr.objects if o.gid == p), None)
        vo = next((o for o in fr.objects if o.gid == v), None)
        if po and vo:
            cv2.line(img, view.pt(po.x, po.y), view.pt(vo.x, vo.y), dr.BAD, 2, cv2.LINE_AA)
    for x, y, n in fr.crowd_spots:
        u, v = view.pt(x, y)
        cv2.circle(img, (u, v), int(C.CROWD_RADIUS_M * view.px_per_m), ALERT_COLOUR["crowd"], 1, cv2.LINE_AA)
    for o in sorted(fr.objects, key=lambda o: o.cls != "person"):
        u, v = view.pt(o.x, o.y)
        rings = [dr.CAMERA_COLOURS[shown.index(c)] for c in sorted(seen_by.get(o.gid, ())) if c in shown]
        if o.cls in VEHICLE_BODY:
            L, Wd = VEHICLE_BODY[o.cls]
            c, s = math.cos(o.heading), math.sin(o.heading)
            corners = [(o.x + c * a - s * b, o.y + s * a + c * b)
                       for a, b in ((-L / 2, -Wd / 2), (L / 2, -Wd / 2), (L / 2, Wd / 2), (-L / 2, Wd / 2))]
            p = view.poly(corners)
            col = ALERT_COLOUR["near_miss"] if "near_miss" in o.alerts or "speeding" in o.alerts \
                else CLASS_COLOUR[o.cls]
            cv2.fillPoly(img, [p], col, cv2.LINE_AA)
            for k, rc in enumerate(rings):
                cv2.polylines(img, [p], True, rc, 2 + 2 * k, cv2.LINE_AA)
            lab = f"{TAG[o.cls]}{o.gid}" + (f" {kmh(o.speed)}" if o.cls == "forklift" and o.reliable else "")
            dr.place_label(T, lab, (u, v), 12, col, taken, view.w, view.h, 6)
            continue
        col = dr.PERSON if o.walking else dr.PERSON_IDLE
        for a in ("near_miss", "wrong_way", "lane", "idle", "crowd"):
            if a in o.alerts:
                col = ALERT_COLOUR[a]
                break
        for k, rc in enumerate(rings):
            cv2.circle(img, (u, v), 6 + 3 * k, rc, 2, cv2.LINE_AA)
        cv2.circle(img, (u, v), 4, col, -1, cv2.LINE_AA)
        if rings or o.alerts or label_all:
            dr.place_label(T, f"P{o.gid}", (u, v), 11, col if o.alerts else dr.INK, taken, view.w, view.h, 5,
                           bold=bool(o.alerts))


# --------------------------------------------------------------- the tiles
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


def tile(img: np.ndarray, cam: Camera, rows: np.ndarray, classes: list[str], frame: int, fr: Frame,
         key_to_gid: dict, placed: set, colour, size: tuple[int, int], zones, lines,
         title: str, big: bool = False) -> np.ndarray:
    """One camera, scaled to `size`, with everything tying it to the plan."""
    tw, th = size
    s = tw / cam.width
    out = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
    T = dr.Texts()
    fs = 15 if big else 11
    taken = [(0, 0, 14 + T.width(title, 16 if big else 13, True), 32 if big else 26)]   # the title
    # the floor overlays, projected from metres; zones faint, lines solid
    layer = out.copy()
    for z in zones:
        col = dr.FORKLIFT if z.kind == "vehicle_lane" else dr.bgr("#f472b6") if z.kind == "one_way" \
            else dr.bgr("#cbd5e1")
        for seg in project_poly(cam, list(z.polygon)):
            cv2.polylines(layer, [(seg * s).astype(np.int32)], False, col, 2 if big else 1, cv2.LINE_AA)
    cv2.addWeighted(layer, 0.55, out, 0.45, 0, out)
    for ln in lines:
        for seg in project_poly(cam, [ln.a, ln.b]):
            q = (seg * s).astype(np.int32)
            cv2.polylines(out, [q], False, dr.INK, 2, cv2.LINE_AA)
            if np.hypot(*(q[-1] - q[0])) >= (90 if big else 45):
                mid = q[len(q) // 2]
                dr.place_label(T, ln.name.split(" ·")[0], (int(mid[0]), int(mid[1])), fs, dr.INK, taken, tw, th, 4)
    objs = {o.gid: o for o in fr.objects}
    here = set()
    labels = []
    r = rows[rows[:, 0] == frame]
    for d in r:
        x1, y1, x2, y2 = (d[2:6] * s).astype(int)
        cls = classes[int(d[7])]
        gid = key_to_gid.get((cam.id, int(d[1]))) if d[1] >= 0 else None
        if gid is not None and gid in objs and gid in placed:
            o = objs[gid]
            here.add(gid)
            col = CLASS_COLOUR[cls]
            for a in ("near_miss", "speeding", "wrong_way", "lane", "idle", "crowd"):
                if a in o.alerts:
                    col = ALERT_COLOUR[a]
                    break
            cv2.rectangle(out, (x1, y1), (x2, y2), col, 2 if big else 1, cv2.LINE_AA)
            lab = f"{TAG[cls]}{gid}"
            if cls == "forklift" and o.reliable:
                lab += f" {kmh(o.speed)}"
            labels.append((lab, (x1, y1, x2, y2), col))
        else:
            # seen, but not on the plan (feet out of frame, too far, not yet confirmed)
            cv2.rectangle(out, (x1, y1), (x2, y2), dr.MUTED, 1, cv2.LINE_AA)
    # nearest first: the label of the biggest box is the one that keeps its place
    for lab, box, col in sorted(labels, key=lambda t: -(t[1][3] - t[1][1])):
        dr.box_label(T, lab, box, fs, col, taken, tw, th)
    # echoes: objects other cameras placed, drawn at their floor point in this view
    for o in fr.objects:
        if o.gid in here:
            continue
        uv = cam.to_image(np.array([[o.x, o.y, 0.0]]))[0]
        if not np.isfinite(uv).all() or not (0 <= uv[0] < cam.width and 0 <= uv[1] < cam.height):
            continue
        if cam.floor_scale(np.array([uv[0]]), np.array([uv[1]]))[0] > 0.15:
            continue
        u, v = int(uv[0] * s), int(uv[1] * s)
        cv2.circle(out, (u, v), 6 if big else 4, CLASS_COLOUR[o.cls], 1, cv2.LINE_AA)
        if big:
            dr.place_label(T, f"{TAG[o.cls]}{o.gid}", (u, v), 11, dr.MUTED, taken, tw, th, 5, bold=False)
    cv2.rectangle(out, (0, 0), (tw - 1, th - 1), colour, 4 if big else 3)
    T.add(title, (8, 6), 16 if big else 13, dr.INK, True, bg=colour, pad=4)
    return T.flush(out)


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


# --------------------------------------------------------------- panels
def header(img: np.ndarray, title: str, sub: str, clock: str) -> None:
    img[:HEADER] = dr.PANEL
    T = dr.Texts()
    T.add(title, (16, 11), 21, dr.INK, True)
    x = 16 + T.width(title, 21, True) + 18
    room = W - 16 - T.width(clock, 20, True) - 24 - x
    size = 15
    while size > 11 and T.width(sub, size) > room:      # shrink to fit before the clock
        size -= 1
    while T.width(sub, size) > room and len(sub) > 4:   # and only then cut
        sub = sub[:-2].rstrip() + "…"
    T.add(sub, (x, 15 + (15 - size) // 2), size, dr.MUTED)
    T.add(clock, (W - 16, 12), 20, dr.INK, True, anchor="ra")
    T.flush(img)


def kpi(T: dr.Texts, x: int, y: int, label: str, value: str, note: str = "", colour=dr.INK,
        size: int = 34) -> None:
    T.add(label.upper(), (x, y), 12, dr.MUTED, True)
    T.add(value, (x, y + 16), size, colour, True)
    if note:
        T.add(note, (x + T.width(value, size, True) + 8, y + 16 + size - 20), 13, dr.MUTED)


def ticker(T: dr.Texts, x: int, y: int, w: int, events: list[str], rows: int = 5) -> None:
    T.add("KEJADIAN TERBARU", (x, y), 12, dr.MUTED, True)
    for i, e in enumerate(events[-rows:][::-1]):
        T.add(e, (x, y + 20 + i * 21), 14, dr.INK if i == 0 else dr.MUTED)


def sparkline(img: np.ndarray, x: int, y: int, w: int, h: int, series: list[list[float]],
              colours: list, ymax: float | None = None) -> None:
    cv2.rectangle(img, (x, y), (x + w, y + h), dr.FAINT, 1)
    top = ymax or max(1.0, max(max(s) for s in series if s))
    for s, col in zip(series, colours):
        if len(s) < 2:
            continue
        n = len(s)
        pts = np.array([(x + int(i * w / max(n - 1, 1)) if n > 1 else x, y + h - int(v / top * (h - 4)) - 2)
                        for i, v in enumerate(s)], np.int32)
        cv2.polylines(img, [pts], False, col, 2, cv2.LINE_AA)


def num(x: float, digits: int = 1) -> str:
    """A decimal the Indonesian way: 4,6 not 4.6."""
    return f"{x:.{digits}f}".replace(".", ",")


def kmh(speed_ms: float) -> str:
    return f"{speed_ms * 3.6:.0f} km/j"


def fmt_t(t: float) -> str:
    return f"{int(t) // 60:02d}:{int(t) % 60:02d}"
