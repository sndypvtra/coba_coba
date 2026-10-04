"""The building in metres: its cameras, its floor plan, and the dataset's labels.

Three coordinate systems meet here and everything else in the project goes
through this file to move between them:

  image       pixels of one camera, origin top-left, 1920 x 1080
  world       metres, z up, the floor is z = 0 (the dataset's own frame)
  plan        pixels of the top-down floor plan the operator looks at

A camera ships two matrices. `cameraMatrix` P (3 x 4) takes any world point to
the image. `homography` H (3 x 3) is P with its z column removed, so it takes a
point *on the floor* to the image - and its inverse takes an image pixel back to
the floor. That inverse is the whole trick: a box's bottom edge is where the
object stands, so one pixel becomes one position in metres.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from config import OUTPUT, SOURCES, input_dir


# --------------------------------------------------------------------- cameras
@dataclass
class Camera:
    id: str
    K: np.ndarray            # 3 x 3 intrinsics
    R: np.ndarray            # 3 x 3 world -> camera rotation
    t: np.ndarray            # 3     world -> camera translation
    P: np.ndarray            # 3 x 4 world -> image
    H: np.ndarray            # 3 x 3 floor (x, y, 1) -> image
    width: int
    height: int

    def __post_init__(self):
        self.H_inv = np.linalg.inv(self.H)
        self.centre = -self.R.T @ self.t
        self.axis = self.R[2]                      # optical axis, world frame

    @classmethod
    def from_sensor(cls, s: dict) -> "Camera":
        """The floor homography is always rebuilt from P, never read from the file.

        In the synthetic recordings the published `homography` is exactly P with
        its z column removed. In the real ones it is not - it differs from that
        by three orders of magnitude and puts the floor behind some cameras - so
        trusting it there would place every person somewhere they are not. P
        itself is consistent in both (K [R|t], cameras 2.5-3 m up, tilted down),
        so the floor plane is taken from it everywhere.
        """
        attrs = {a["name"]: a["value"] for a in s.get("attributes", [])}
        E = np.asarray(s["extrinsicMatrix"], float)
        P = np.asarray(s["cameraMatrix"], float)
        return cls(id=s["id"], K=np.asarray(s["intrinsicMatrix"], float),
                   R=E[:, :3], t=E[:, 3], P=P, H=P[:, [0, 1, 3]].copy(),
                   width=int(float(attrs.get("frameWidth", 1920))),
                   height=int(float(attrs.get("frameHeight", 1080))))

    # -- where it is and where it looks
    @property
    def mount_height_m(self) -> float:
        return float(self.centre[2])

    @property
    def tilt_deg(self) -> float:
        """Degrees below the horizon the optical axis points."""
        return math.degrees(math.asin(float(np.clip(-self.axis[2], -1, 1))))

    @property
    def heading(self) -> float:
        """Direction the camera faces on the floor, radians in the world frame."""
        return math.atan2(float(self.axis[1]), float(self.axis[0]))

    @property
    def hfov_deg(self) -> float:
        return math.degrees(2 * math.atan(self.width / (2 * self.K[0, 0])))

    # -- image <-> world
    def to_floor(self, u, v):
        """Image pixel(s) -> floor point(s) in metres. NaN where the ray misses."""
        u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
        p = self.H_inv @ np.stack([u.ravel(), v.ravel(), np.ones(u.size)])
        with np.errstate(divide="ignore", invalid="ignore"):
            x, y = p[0] / p[2], p[1] / p[2]
        # A pixel above the horizon back-projects to a point *behind* the camera;
        # the homography cannot tell, so check it by projecting forward again.
        bad = ~self.in_front(np.stack([x, y, np.zeros_like(x)], 1))
        x[bad] = np.nan
        y[bad] = np.nan
        return x.reshape(u.shape), y.reshape(u.shape)

    def depth(self, pts: np.ndarray) -> np.ndarray:
        pts = np.atleast_2d(np.asarray(pts, float))
        return (self.R @ pts.T + self.t[:, None])[2]

    def in_front(self, pts: np.ndarray) -> np.ndarray:
        with np.errstate(invalid="ignore"):
            return self.depth(pts) > 0.05

    def to_image(self, pts: np.ndarray) -> np.ndarray:
        """World point(s) (N, 3) -> pixels (N, 2); NaN behind the camera."""
        pts = np.atleast_2d(np.asarray(pts, float))
        h = self.P @ np.hstack([pts, np.ones((len(pts), 1))]).T
        uv = (h[:2] / h[2]).T
        uv[~self.in_front(pts)] = np.nan
        return uv

    def floor_scale(self, u, v):
        """Metres of floor covered by one pixel at (u, v). Bigger is coarser."""
        x0, y0 = self.to_floor(u, v)
        x1, y1 = self.to_floor(np.asarray(u) + 1.0, v)
        x2, y2 = self.to_floor(u, np.asarray(v) + 1.0)
        return np.fmax(np.hypot(x1 - x0, y1 - y0), np.hypot(x2 - x0, y2 - y0))

    def sees(self, xs: np.ndarray, ys: np.ndarray, max_scale: float = 0.10,
             margin: int = 0) -> np.ndarray:
        """Which floor points this camera images at no coarser than `max_scale`.

        Geometry only: a rack standing between the lens and the point is not
        modelled here. Occlusion is measured separately, from who is actually
        detected (or labelled) in each view.
        """
        pts = np.stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)], 1)
        uv = self.to_image(pts)
        ok = np.isfinite(uv).all(1)
        ok &= (uv[:, 0] >= margin) & (uv[:, 0] < self.width - margin)
        ok &= (uv[:, 1] >= margin) & (uv[:, 1] < self.height - margin)
        sc = np.full(len(pts), np.inf)
        sc[ok] = self.floor_scale(uv[ok, 0], uv[ok, 1])
        return (ok & (sc <= max_scale)).reshape(xs.shape)

    def footprint(self, max_scale: float = 0.10, radius_m: float = 60.0,
                  step_m: float = 0.2) -> np.ndarray:
        """Outline of the floor this camera images usefully, in world metres.

        Rasterises `sees` on a grid around the camera and traces the largest
        region. Returns an (N, 2) polygon, empty if the camera sees no floor.
        """
        g = np.arange(-radius_m, radius_m + step_m, step_m)
        xs, ys = np.meshgrid(g + self.centre[0], g + self.centre[1])
        mask = self.sees(xs, ys, max_scale).astype(np.uint8)
        cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cs:
            return np.zeros((0, 2))
        c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
        return np.stack([g[0] + self.centre[0] + c[:, 0] * step_m,
                         g[0] + self.centre[1] + c[:, 1] * step_m], 1)

    def shifted(self, dx: float, dy: float) -> "Camera":
        """The same camera moved (dx, dy) metres across the floor.

        A point seen at floor position p is then placed at p + (dx, dy). In
        matrices: P' = P [I | -s], so the camera centre moves by s = (dx, dy, 0)
        and nothing about where it looks changes.
        """
        s = np.array([dx, dy, 0.0])
        T = np.eye(4)
        T[:3, 3] = -s
        P = self.P @ T
        return Camera(id=self.id, K=self.K, R=self.R, t=self.t - self.R @ s, P=P,
                      H=P[:, [0, 1, 3]].copy(), width=self.width, height=self.height)

    def height_at(self, x: float, y: float, v_top: float) -> float:
        """Height of an upright object standing at (x, y) whose top is at row v_top.

        The object is the vertical segment (x, y, 0)-(x, y, h). Its top projects
        to row v(h) = (P1.X + h P1z) / (P3.X + h P3z), where X = (x, y, 0, 1) and
        P1z, P3z are the z column. Cross-multiplied this is linear in h, so the
        height comes out in closed form from one box edge and the calibration.
        """
        X = np.array([x, y, 0.0, 1.0])
        a1, a3 = self.P[1] @ X, self.P[2] @ X
        b1, b3 = self.P[1, 2], self.P[2, 2]
        den = v_top * b3 - b1
        return float((a1 - v_top * a3) / den) if abs(den) > 1e-9 else float("nan")


def load_cameras(scene: str, aligned: bool = True) -> dict[str, Camera]:
    """The scene's cameras from its calibration file.

    For the real recording, `align_real.py` measures how far each camera's
    floor is shifted against the others (from people two cameras see at once)
    and stores it; with `aligned`, those shifts are applied here, and only the
    cameras it could verify are returned.
    """
    data = json.loads((input_dir(scene) / "calibration.json").read_text())
    cams = {s["id"]: Camera.from_sensor(s) for s in data["sensors"] if s.get("type", "camera") == "camera"}
    path = OUTPUT / scene / "camera_alignment.json"
    if aligned and path.exists():
        a = json.loads(path.read_text())
        cams = {c: cams[c].shifted(*a["cameras"][c]["shift_m"]) for c in a["verified"]}
    return cams


# ------------------------------------------------------------------ floor plan
@dataclass
class FloorPlan:
    """A top-down picture of the floor and the transform that ties it to metres.

    `A` is the 3 x 3 affine map world (x, y, 1) -> plan pixel (u, v, 1). For the
    dataset's map.png it comes from the published scale and translation; for a
    scene without one, it is whatever frame the plan was built in.
    """

    image: np.ndarray
    A: np.ndarray
    built_from_cameras: bool = False

    def __post_init__(self):
        self.A_inv = np.linalg.inv(self.A)

    @property
    def px_per_m(self) -> float:
        return float(abs(self.A[0, 0]))

    def to_px(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        return self.A[0, 0] * x + self.A[0, 1] * y + self.A[0, 2], \
            self.A[1, 0] * x + self.A[1, 1] * y + self.A[1, 2]

    def to_world(self, u, v):
        u, v = np.asarray(u, float), np.asarray(v, float)
        return self.A_inv[0, 0] * u + self.A_inv[0, 1] * v + self.A_inv[0, 2], \
            self.A_inv[1, 0] * u + self.A_inv[1, 1] * v + self.A_inv[1, 2]

    def crop(self, x0: float, y0: float, x1: float, y1: float) -> "FloorPlan":
        """The part of the plan covering a world rectangle, transform adjusted."""
        us, vs = self.to_px([x0, x1], [y0, y1])
        c0, c1 = int(max(0, np.floor(min(us)))), int(min(self.image.shape[1], np.ceil(max(us))))
        r0, r1 = int(max(0, np.floor(min(vs)))), int(min(self.image.shape[0], np.ceil(max(vs))))
        T = np.array([[1, 0, -c0], [0, 1, -r0], [0, 0, 1.0]])
        return FloorPlan(self.image[r0:r1, c0:c1].copy(), T @ self.A, self.built_from_cameras)

    def resized(self, scale: float) -> "FloorPlan":
        img = cv2.resize(self.image, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        S = np.diag([scale, scale, 1.0])
        return FloorPlan(img, S @ self.A, self.built_from_cameras)


def dataset_plan(scene: str) -> FloorPlan:
    """The dataset's own map.png, placed in world metres.

    The calibration publishes, per sensor, `scaleFactor` (plan pixels per metre)
    and `translationToGlobalCoordinates` (tx, ty), with u = (x + tx) * s. The
    plan's rows run against the world y axis: row 0 is the largest y, so
    v = (rows - 1) - (y + ty) * s. Getting that sign wrong still puts every
    point inside the building, mirrored, so `geometry_check.py` verifies it
    against the floor itself rather than trusting it.
    """
    root = input_dir(scene)
    img = cv2.imread(str(root / "map.png"))
    if img is None:
        raise FileNotFoundError(root / "map.png")
    s0 = json.loads((root / "calibration.json").read_text())["sensors"][0]
    s = float(s0["scaleFactor"])
    tx = float(s0["translationToGlobalCoordinates"]["x"])
    ty = float(s0["translationToGlobalCoordinates"]["y"])
    rows = img.shape[0]
    A = np.array([[s, 0, s * tx], [0, -s, rows - 1 - s * ty], [0, 0, 1.0]])
    return FloorPlan(img, A)


def building_mask(plan: FloorPlan) -> np.ndarray:
    """Plan pixels inside the building: the largest dark region of map.png."""
    m = (plan.image.max(axis=2) < 150).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return np.ones(m.shape, bool)
    return lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))


def floor_mosaic(cams: dict[str, Camera], frames: dict[str, np.ndarray],
                 px_per_m: float = 40.0, max_scale: float = 0.06,
                 margin_m: float = 1.0, agree_tol: float = 38.0,
                 trust_scale: float = 0.022) -> tuple[FloorPlan, np.ndarray]:
    """A floor plan for a site that has none, painted from its own cameras.

    Every plan pixel is a floor point. Laying a camera image onto the floor is
    only right for things that *are* on the floor: a rack or a wall gets smeared
    away from the lens, differently in every camera. So a pixel is kept only
    where that cannot have happened - where two cameras that both see it agree on
    its colour, or where one camera sees it from so close (finer than
    `trust_scale` m/px) that it is almost certainly floor. The rest stays dark.
    The finest camera paints each kept pixel. Returns the plan and the index of
    the camera that painted each pixel (-1 where none did).
    """
    ids = list(cams)
    # bounds: where any camera images the floor finely enough
    pts = []
    for c in cams.values():
        g = np.linspace(-60, 60, 241)
        xs, ys = np.meshgrid(g + c.centre[0], g + c.centre[1])
        m = c.sees(xs, ys, max_scale)
        pts.append(np.stack([xs[m], ys[m]], 1))
    pts = np.concatenate(pts)
    x0, y0 = pts.min(0) - margin_m
    x1, y1 = pts.max(0) + margin_m
    W = int(np.ceil((x1 - x0) * px_per_m))
    Hh = int(np.ceil((y1 - y0) * px_per_m))
    A = np.array([[px_per_m, 0, -x0 * px_per_m], [0, -px_per_m, y1 * px_per_m], [0, 0, 1.0]])
    plan = FloorPlan(np.zeros((Hh, W, 3), np.uint8), A, built_from_cameras=True)

    uu, vv = np.meshgrid(np.arange(W) + 0.5, np.arange(Hh) + 0.5)
    xs, ys = plan.to_world(uu, vv)
    layers, scales = [], []
    for cid in ids:
        c = cams[cid]
        uv = c.to_image(np.stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)], 1))
        ok = np.isfinite(uv).all(1) & (uv[:, 0] >= 0) & (uv[:, 0] < c.width - 1) \
            & (uv[:, 1] >= 0) & (uv[:, 1] < c.height - 1)
        sc = np.full(xs.size, np.inf)
        sc[ok] = c.floor_scale(uv[ok, 0], uv[ok, 1])
        mapx = np.nan_to_num(uv[:, 0].reshape(Hh, W), nan=-1).astype(np.float32)
        mapy = np.nan_to_num(uv[:, 1].reshape(Hh, W), nan=-1).astype(np.float32)
        layers.append(cv2.remap(frames[cid], mapx, mapy, cv2.INTER_LINEAR).astype(np.float32))
        scales.append(sc.reshape(Hh, W))
    scales = np.stack(scales)                       # (cams, H, W)
    seen = scales <= max_scale
    agreed = np.zeros((Hh, W), bool)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            both = seen[a] & seen[b]
            if both.any():
                diff = np.abs(layers[a] - layers[b]).mean(axis=2)
                agreed |= both & (diff < agree_tol)
    keep = agreed | (scales <= trust_scale).any(axis=0)
    best = np.where(seen, scales, np.inf).argmin(axis=0)
    owner = np.where(keep & seen.any(axis=0), best, -1)
    for k in range(len(ids)):
        m = owner == k
        plan.image[m] = layers[k][m].astype(np.uint8)
    return plan, owner


# ---------------------------------------------------------------------- labels
KINDS = ["Person", "Forklift", "PalletTruck", "Transporter", "NovaCarter",
         "FourierGR1T2", "AgilityDigit"]


class Labels:
    """The dataset's ground truth, packed into arrays and cached.

    ground_truth.json is 270 MB of nested dicts; parsing it takes most of a
    minute and a few GB. It is read once and stored as two flat tables:

      objs    one row per object per frame: frame, kind, id, x, y, z, sx, sy, sz, yaw
      boxes   one row per object per frame per camera that sees it:
              obj row, camera, x1, y1, x2, y2

    The labels are used to choose windows, to verify geometry and to score the
    pipeline. The pipeline itself never reads them.
    """

    def __init__(self, scene: str, cams: list[str]):
        self.scene = scene
        cache = input_dir(scene) / "labels_cache.npz"
        self.cam_ids = sorted(cams)
        if cache.exists():
            z = np.load(cache, allow_pickle=False)
            self.objs, self.boxes = z["objs"], z["boxes"]
            self.cam_ids = list(z["cams"])
        else:
            self.objs, self.boxes = self._parse()
            np.savez_compressed(cache, objs=self.objs, boxes=self.boxes,
                                cams=np.array(self.cam_ids))
        self.frame = self.objs[:, 0].astype(int)
        self.kind = self.objs[:, 1].astype(int)
        self.oid = self.objs[:, 2].astype(int)
        self._starts = np.searchsorted(self.frame, np.arange(self.frame.max() + 2))
        self.n_frames = int(self.frame.max()) + 1

    def _parse(self):
        gt = json.loads((input_dir(self.scene) / "ground_truth.json").read_text())
        cam_index = {c: i for i, c in enumerate(self.cam_ids)}
        objs, boxes = [], []
        for f in sorted(gt, key=int):
            for o in gt[f]:
                k = KINDS.index(o["object type"]) if o["object type"] in KINDS else -1
                x, y, z = o["3d location"]
                sx, sy, sz = o["3d bounding box scale"]
                yaw = o["3d bounding box rotation"][2]
                row = len(objs)
                objs.append((int(f), k, o["object id"], x, y, z, sx, sy, sz, yaw))
                for cam, b in o.get("2d bounding box visible", {}).items():
                    if cam in cam_index:
                        boxes.append((row, cam_index[cam], *b))
        return np.array(objs, float), np.array(boxes, float)

    def rows(self, frame: int) -> slice:
        return slice(self._starts[frame], self._starts[frame + 1])

    def at(self, frame: int, kind: str | None = None) -> np.ndarray:
        r = self.objs[self.rows(frame)]
        return r if kind is None else r[r[:, 1] == KINDS.index(kind)]

    def boxes_in(self, cam: str, frames: np.ndarray | None = None,
                 kind: str | None = None) -> np.ndarray:
        """2D label boxes in one camera, joined to the object they belong to.

        Columns: 0 frame, 1 kind, 2 id, 3 x, 4 y, 5 z, 6 height, 7 x1, 8 y1,
        9 x2, 10 y2 - world metres for the object, pixels for the box.
        """
        ci = self.cam_ids.index(cam)
        b = self.boxes[self.boxes[:, 1] == ci]
        o = self.objs[b[:, 0].astype(int)]
        out = np.column_stack([o[:, 0], o[:, 1], o[:, 2], o[:, 3], o[:, 4], o[:, 5],
                               o[:, 8], b[:, 2:6]])
        if kind is not None:
            out = out[out[:, 1] == KINDS.index(kind)]
        if frames is not None:
            out = out[np.isin(out[:, 0], frames)]
        return out


def read_frame(path: Path, index: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise IOError(f"{path}: frame {index} unreadable")
    return frame


def video_path(scene: str, cam: str) -> Path:
    return input_dir(scene) / "videos" / f"{cam}.mp4"


def is_real(scene: str) -> bool:
    return SOURCES[scene].real
