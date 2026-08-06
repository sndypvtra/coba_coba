"""Drawing: the camera views, one floor, and the numbers underneath.

The layout follows the dataset's own banner - camera tiles down the left, camera
tiles down the right, the top-down view in the middle - because that arrangement
makes the one claim the case is about: *the same colour is the same person*. A
box in the top-left tile and a box in the bottom-right tile share a colour only
if the pipeline decided they are one identity, and the marker between them on
the floor is where it decided that person is standing.

The wireframes are not decoration. Each one is eight world points - a box of
measured height standing on the floor at the estimated position - projected back
through that camera's matrix. If the position or the height were wrong, the box
would visibly float, lean or sink, so the overlay is also the error display.
"""

from __future__ import annotations

import cv2
import numpy as np

from factory_vision.spatial.calibration import BOX_EDGES, Camera, box3d_corners
from factory_vision.spatial.bev import GroundMap

EAGLE = 810           # the top-down view is square and sets the mosaic height
MAX_ROWS = 6          # live-track rows the panel has room for
PANEL_H = 340


BG = (18, 18, 20)
INK = (238, 238, 238)
MUTED = (150, 150, 150)
DIM = (96, 96, 96)
RULE = (62, 62, 66)
WARN = (70, 120, 250)
ROBOT = (200, 170, 90)
CAMERA = (170, 200, 235)

# Distinct at small size and on a grey floor; index by global id.
PALETTE = [(120, 220, 90), (240, 160, 60), (90, 150, 255), (200, 120, 240),
           (80, 220, 230), (240, 110, 160), (150, 240, 160), (110, 190, 255),
           (230, 210, 100), (170, 130, 250), (100, 200, 180), (240, 130, 110)]



class Layout:
    """Tile and mosaic geometry, derived from how many cameras there are.

    The banner arrangement - a block of tiles, the floor plan, another block of
    tiles - is kept as rows and columns rather than as pixel constants, so four
    cameras and twelve produce the same design at different tile sizes. Tile
    height follows from the eagle view being square and as tall as the tile
    block, which is what keeps the plan legible when there are twelve tiles
    competing with it.
    """

    def __init__(self, cfg):
        self.rows_l, self.cols_l = cfg.grid("left")
        self.rows_r, self.cols_r = cfg.grid("right")
        rows = max(self.rows_l, self.rows_r, 1)
        self.tile_h = int(round(EAGLE / rows / 2) * 2)
        self.tile_w = int(round(self.tile_h * 16 / 9 / 2) * 2)
        self.band_h = self.tile_h * rows
        self.eagle = self.band_h
        self.width = self.tile_w * (self.cols_l + self.cols_r) + self.eagle
        self.height = self.band_h + PANEL_H

    def block(self, tiles: dict, side: str, rows: int, cols: int):
        blank = np.full((self.tile_h, self.tile_w, 3), BG, np.uint8)
        return np.vstack([
            np.hstack([tiles.get((side, r, c), blank) for c in range(cols)])
            for r in range(rows)
        ]) if rows and cols else np.zeros((self.band_h, 0, 3), np.uint8)

    def mosaic(self, tiles: dict, eagle, panel_img):
        band = np.hstack([self.block(tiles, "left", self.rows_l, self.cols_l),
                          eagle,
                          self.block(tiles, "right", self.rows_r, self.cols_r)])
        return np.vstack([band, panel_img])


def colour_for(gid: int, label: str) -> tuple[int, int, int]:
    if label != "person":
        return ROBOT
    return PALETTE[(gid - 1) % len(PALETTE)]


def text(img, s, org, scale, colour, weight=1):
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, colour, weight, cv2.LINE_AA)


def _fit(img, w, h):
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


# ------------------------------------------------------------ camera tiles


def draw_box3d(tile, cam: Camera, x, y, h, w, l, yaw, colour, sx, sy,
               label: str = "", observed: bool = True):
    """Project one upright box into a (already resized) camera tile.

    `observed` says whether *this* camera saw the object or whether the box is
    the fused estimate rendered into a view that missed it. Both are drawn,
    because a box standing correctly on a person a camera did not detect is the
    clearest evidence that the fusion is doing its job - but they are drawn
    differently, so the picture never implies a detection that did not happen.
    """
    corners = box3d_corners(x, y, h, w, l, yaw)
    uv = cam.project(corners)
    if not np.isfinite(uv).all():
        return None
    uv = np.stack([uv[:, 0] * sx, uv[:, 1] * sy], 1)
    pts = uv.astype(int)

    if observed:
        # The floor face is filled and the rest is wire, so contact with the
        # ground reads at a glance - that is the quantity being claimed.
        overlay = tile.copy()
        cv2.fillPoly(overlay, [pts[:4]], colour)
        cv2.addWeighted(overlay, 0.22, tile, 0.78, 0, tile)
        for a, b in BOX_EDGES:
            thick = 2 if (a < 4 and b < 4) else 1
            cv2.line(tile, tuple(pts[a]), tuple(pts[b]), colour, thick, cv2.LINE_AA)
    else:
        faint = tuple(int(0.45 * c + 0.55 * 30) for c in colour)
        for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
            cv2.line(tile, tuple(pts[a]), tuple(pts[b]), faint, 1, cv2.LINE_AA)
        for a, b in ((0, 4), (2, 6)):
            cv2.line(tile, tuple(pts[a]), tuple(pts[b]), faint, 1, cv2.LINE_AA)

    if label:
        scale = 0.40 if observed else 0.34
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        left = int(np.clip(pts[:, 0].min(), 2, tile.shape[1] - tw - 10))
        ly = int(np.clip(pts[4:, 1].min() - 4, th + 26, tile.shape[0] - 4))
        if observed:
            cv2.rectangle(tile, (left, ly - th - 4), (left + tw + 8, ly + 2), colour, -1)
            text(tile, label, (left + 4, ly - 2), scale, (16, 16, 16), 1)
        else:
            text(tile, label, (left + 4, ly - 2), scale, faint, 1)
    return pts


def camera_tile(frame, cam: Camera, view_label: str, tracks_here, cfg, lay: Layout):
    """One camera panel. `tracks_here` is (gid, label, x, y, h, yaw, observed)."""
    tile = _fit(frame, lay.tile_w, lay.tile_h)
    sx, sy = lay.tile_w / cam.width, lay.tile_h / cam.height
    fw, fl = cfg.footprint_m
    # Twelve tiles are each two-thirds the size of four, so the labels shed the
    # height reading and keep only the identity - a number nobody can read is
    # worse than no number.
    small = lay.tile_w < 560
    bar = 20 if small else 24

    seen = 0
    for gid, label, x, y, h, yaw, observed in sorted(tracks_here, key=lambda t: t[6]):
        colour = colour_for(gid, label)
        tag = f"{'P' if label == 'person' else 'R'}{gid}"
        if observed:
            seen += 1
            if np.isfinite(h) and not small:
                tag += f"  {h:.2f}m"
        draw_box3d(tile, cam, x, y, h if np.isfinite(h) else 1.75, fw, fl, yaw,
                   colour, sx, sy, tag, observed)

    cv2.rectangle(tile, (0, 0), (lay.tile_w - 1, lay.tile_h - 1), (55, 55, 58), 1)
    cv2.rectangle(tile, (0, 0), (lay.tile_w, bar), (0, 0, 0), -1)
    text(tile, view_label, (7, bar - 6), 0.40 if small else 0.46, INK, 1)
    inferred = len(tracks_here) - seen
    tag = f"{seen} det" if small else f"{seen} detected"
    if inferred:
        tag += f" +{inferred}" if small else f"  +{inferred} fused in"
    (tw, _), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
    text(tile, tag, (lay.tile_w - tw - 7, bar - 6), 0.36, MUTED, 1)
    return tile


# -------------------------------------------------------------- eagle view


def coverage_mask(cam: Camera, gm: GroundMap) -> np.ndarray:
    """Which floor pixels of the eagle view this camera can actually see.

    Computed forwards, by projecting every floor point into the camera and
    asking whether it lands in the image, rather than backwards by
    back-projecting the image corners. Backwards is the tempting direction and
    it does not work: the upper corners of a camera looking across a room lie
    above the horizon, where the ground plane has no answer, and hulling
    whatever those rays return draws a coverage area across the whole building.
    """
    h, w = gm.image.shape[:2]
    vs, us = np.mgrid[0:h, 0:w]
    X = (us - gm.pad[0]) / gm.zoom
    Y = (vs - gm.pad[1]) / gm.zoom
    X = (X + gm.crop[0]) / gm.scale - gm.tx
    Y = (Y + gm.crop[1]) / gm.scale - gm.ty
    pts = np.stack([X.ravel(), Y.ravel(), np.zeros(X.size), np.ones(X.size)], 1)
    hom = pts @ cam.P.T
    wq = hom[:, 2]
    ok = wq > 1e-6
    u = np.full(X.size, -1e9)
    v = np.full(X.size, -1e9)
    u[ok] = hom[ok, 0] / wq[ok]
    v[ok] = hom[ok, 1] / wq[ok]
    inside = ok & (u >= 0) & (u < cam.width) & (v >= 0) & (v < cam.height)
    return inside.reshape(h, w)


def eagle_base(gmap: GroundMap, cfg, cams: dict[str, Camera], view_ids: list[str]):
    """Static part of the top-down view: floor, zones, camera coverage."""
    gm = gmap
    base = gm.image.copy()

    # Shade the floor by how many cameras cover it, normalised so the darkest
    # and lightest ends mean the same thing whether there are four views or
    # twelve. Overlap is what makes fusion possible, so where it is thin is
    # worth seeing. Per-camera outlines are drawn only while they still read as
    # separate shapes - twelve of them is a scribble, not information.
    masks = [coverage_mask(cams[sid], gm) for sid in view_ids]
    count = np.sum(masks, axis=0).astype(np.float32)
    tint = np.zeros_like(base, np.float32)
    tint[..., 1] = np.clip(count / max(len(masks), 1), 0, 1) * 22.0
    base = np.clip(base.astype(np.float32) + tint, 0, 255).astype(np.uint8)
    if len(masks) <= 6:
        lines = base.copy()
        for i, m in enumerate(masks):
            cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(lines, cnts, -1, PALETTE[i % len(PALETTE)], 1, cv2.LINE_AA)
        cv2.addWeighted(lines, 0.40, base, 0.60, 0, base)

    for z in cfg.zones:
        if not z.polygon_m:
            continue
        poly = gm.poly(z.polygon_m)
        if z.kind == "restricted":
            cv2.polylines(base, [poly], True, WARN, 1, cv2.LINE_AA)
        else:
            cv2.polylines(base, [poly], True, (150, 235, 150), 2, cv2.LINE_AA)
            org = tuple(poly.min(0) + [5, 17])
            text(base, z.name.upper(), org, 0.40, (10, 20, 10), 3)
            text(base, z.name.upper(), org, 0.40, (170, 250, 170), 1)

    # Camera markers get one neutral colour rather than one each: the palette is
    # already spoken for by identities, and a camera wearing a person's colour
    # invites exactly the wrong reading.
    for sid in view_ids:
        p = gm.pt(cams[sid].centre[0], cams[sid].centre[1])
        cv2.drawMarker(base, p, CAMERA, cv2.MARKER_TRIANGLE_UP, 11, 2)
        short = sid.replace("Camera_", "C") if "_" in sid else "C00"
        text(base, short, (p[0] + 8, p[1] + 4), 0.34, (10, 10, 10), 3)
        text(base, short, (p[0] + 8, p[1] + 4), 0.34, CAMERA, 1)
    return base, gm


def eagle_frame(base, gm: GroundMap, cfg, live, trails, frame_idx, fps):
    view = base.copy()
    fw, fl = cfg.footprint_m

    for gid, pts in trails.items():
        if len(pts) < 2:
            continue
        colour = colour_for(gid, "person")
        poly = np.array([gm.pt(x, y) for x, y in pts], np.int32)
        cv2.polylines(view, [poly], False, colour, 1, cv2.LINE_AA)

    for gid, label, x, y, h, yaw, seen_s, n_cam in live:
        colour = colour_for(gid, label)
        c, s = np.cos(yaw), np.sin(yaw)
        base_pts = np.array([[-fw / 2, -fl / 2], [fw / 2, -fl / 2],
                             [fw / 2, fl / 2], [-fw / 2, fl / 2]])
        rot = base_pts @ np.array([[c, s], [-s, c]]) + [x, y]
        poly = np.array([gm.pt(px, py) for px, py in rot], np.int32)
        cv2.fillPoly(view, [poly], colour)
        cv2.polylines(view, [poly], True, (20, 20, 20), 1, cv2.LINE_AA)
        tip = gm.pt(x + 0.75 * c, y + 0.75 * s)
        cv2.arrowedLine(view, gm.pt(x, y), tip, colour, 2, cv2.LINE_AA, tipLength=0.4)
        tag = f"{'P' if label == 'person' else 'R'}{gid}"
        px, py = gm.pt(x, y)
        text(view, tag, (px + 10, py - 9), 0.46, (8, 8, 8), 3)
        text(view, tag, (px + 10, py - 9), 0.46, colour, 1)
        # A ring for every extra camera that agrees this object is here.
        for k in range(1, n_cam):
            cv2.circle(view, (px, py), 9 + 4 * k, colour, 1, cv2.LINE_AA)

    side = view.shape[0]
    cv2.rectangle(view, (0, 0), (side, 26), (0, 0, 0), -1)
    text(view, "EAGLE VIEW  -  world coordinates, metres", (8, 18), 0.48, INK, 1)
    # Scale bar: two metres, measured on the map rather than assumed.
    two_m = int(round(2.0 * gm.px_per_m))
    y0 = side - 18
    cv2.line(view, (14, y0), (14 + two_m, y0), INK, 2)
    cv2.line(view, (14, y0 - 4), (14, y0 + 4), INK, 2)
    cv2.line(view, (14 + two_m, y0 - 4), (14 + two_m, y0 + 4), INK, 2)
    text(view, "2 m", (14 + two_m + 6, y0 + 4), 0.40, INK, 1)
    cv2.rectangle(view, (0, 0), (side - 1, side - 1), (55, 55, 58), 1)
    return view


# ------------------------------------------------------------------- panel


def _bars(canvas, x, y, w, rows, total, colour=(120, 200, 120)):
    for i, (name, value) in enumerate(rows):
        yy = y + i * 20
        text(canvas, name, (x, yy), 0.40, MUTED, 1)
        frac = value / total if total else 0.0
        cv2.rectangle(canvas, (x + 168, yy - 9), (x + 168 + w, yy - 1), (44, 44, 48), -1)
        cv2.rectangle(canvas, (x + 168, yy - 9),
                      (x + 168 + int(w * min(frac, 1.0)), yy - 1), colour, -1)
        text(canvas, f"{value:.0f}s", (x + 176 + w, yy), 0.40, INK, 1)


def panel(width, cfg, stats, series, live_rows, elapsed, total_s, total_frames,
          tracker_name):
    c = np.full((PANEL_H, width, 3), BG, np.uint8)
    cv2.line(c, (0, 0), (width, 0), RULE, 1)

    # ---- masthead, its own column so nothing has to be squeezed past it
    text(c, "MULTI-CAMERA", (18, 34), 0.66, INK, 2)
    text(c, "SPATIAL ANALYTICS", (18, 60), 0.66, INK, 2)
    text(c, cfg.scene.split(" - ")[0], (18, 84), 0.42, MUTED, 1)
    text(c, f"{elapsed:5.1f} s / {total_s:.0f} s", (18, 106), 0.46, INK, 1)
    cv2.line(c, (300, 16), (300, PANEL_H - 34), RULE, 1)

    # ---- headline figures, spread across whatever width the mosaic has
    figs = [("PEOPLE NOW", f"{stats['people_now']}",
             f"fused across {stats['n_views']} views"),
            ("HUMANOID ROBOTS", f"{stats['robots_now']}", "named, not counted as people"),
            ("DISTINCT PEOPLE", f"{stats['distinct_people']}", "global identities so far"),
            ("FLOOR WALKED", f"{stats['distance_m']:.0f} m", "smoothed world tracks"),
            ("NEAREST PERSON-ROBOT", stats["gap"], "closest approach this frame")]
    x0, x1 = 328, width - 18
    step = min(300, (x1 - x0) // len(figs))
    for i, (title, value, note) in enumerate(figs):
        x = x0 + i * step
        text(c, title, (x, 34), 0.38, MUTED, 1)
        col = WARN if title.startswith("NEAREST") and stats["gap_warn"] else INK
        text(c, value, (x, 76), 0.92, col, 2)
        text(c, note, (x, 98), 0.34, DIM, 1)

    cv2.line(c, (300, 122), (x1, 122), RULE, 1)

    # ---- lower row: three blocks sharing the content width
    content = x1 - x0
    gx, gy, gh = 344, 152, 108
    gw = max(360, int(content * 0.34))
    zx = gx + gw + 84
    tx = min(zx + max(420, int(content * 0.26)), x1 - 470)
    cv2.rectangle(c, (gx, gy), (gx + gw, gy + gh), (30, 30, 34), -1)
    text(c, "PEOPLE ON THE FLOOR", (gx, gy - 8), 0.38, MUTED, 1)
    if series:
        top = max(4, max(series) + 1)
        for lvl in range(0, top + 1, max(1, top // 4)):
            yy = gy + gh - int(gh * lvl / top)
            cv2.line(c, (gx, yy), (gx + gw, yy), (44, 44, 48), 1)
            text(c, str(lvl), (gx - 16, yy + 4), 0.34, DIM, 1)
        # The x axis is the whole clip, not the part seen so far, so the trace
        # grows across the panel instead of being rescaled to fill it every frame.
        span = max(total_frames - 1, 1)
        pts = [(gx + int(gw * i / span), gy + gh - int(gh * v / top))
               for i, v in enumerate(series)]
        cv2.polylines(c, [np.array(pts, np.int32)], False, (120, 220, 90), 2, cv2.LINE_AA)
        cv2.circle(c, pts[-1], 3, (120, 220, 90), -1)
    text(c, f"0 s", (gx, gy + gh + 14), 0.34, DIM, 1)
    text(c, f"{total_s:.0f} s", (gx + gw - 24, gy + gh + 14), 0.34, DIM, 1)

    # ---- zone dwell
    text(c, "PERSON-SECONDS BY AREA", (zx, 144), 0.38, MUTED, 1)
    _bars(c, zx, 166, 150, stats["zone_rows"], stats["zone_total"])
    text(c, "PERSON-SECONDS IN MARKED PALLET LANES", (zx, 236), 0.38, MUTED, 1)
    _bars(c, zx, 258, 150, stats["lane_rows"], stats["zone_total"], WARN)

    # ---- live table
    cv2.line(c, (tx - 40, 136), (tx - 40, PANEL_H - 34), RULE, 1)
    text(c, "LIVE TRACKS", (tx, 144), 0.38, MUTED, 1)
    cols = [0, 60, 150, 250, 330, 420]
    for i, hname in enumerate(["ID", "HEIGHT", "SPEED", "VIEWS", "IN VIEW", "AREA"]):
        text(c, hname, (tx + cols[i], 166), 0.34, DIM, 1)
    cv2.line(c, (tx, 172), (width - 18, 172), RULE, 1)
    for r, row in enumerate(live_rows[:MAX_ROWS]):
        yy = 190 + r * 21
        colour = colour_for(row["gid"], row["label"])
        text(c, row["tag"], (tx + cols[0], yy), 0.42, colour, 1)
        text(c, row["height"], (tx + cols[1], yy), 0.40, INK, 1)
        text(c, row["speed"], (tx + cols[2], yy), 0.40, INK, 1)
        text(c, row["views"], (tx + cols[3], yy), 0.40, INK, 1)
        text(c, row["seen"], (tx + cols[4], yy), 0.40, INK, 1)
        text(c, row["zone"], (tx + cols[5], yy), 0.38, MUTED, 1)
    if len(live_rows) > MAX_ROWS:
        text(c, f"+{len(live_rows) - MAX_ROWS} more",
             (tx + cols[0], 190 + MAX_ROWS * 21), 0.36, DIM, 1)

    foot = (f"YOLOE-11L-seg zero-shot  |  {tracker_name} per camera  |  "
            f"ground-plane homography + camera matrix  |  identities fused in world metres")
    text(c, foot, (18, PANEL_H - 12), 0.40, DIM, 1)
    src = cfg.source.split(" - ")[0]
    (sw, _), _ = cv2.getTextSize(src, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
    text(c, src, (width - sw - 18, PANEL_H - 12), 0.36, DIM, 1)
    return c
