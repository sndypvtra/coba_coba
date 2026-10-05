"""From boxes in pixels to objects on the floor, one identity per object.

Three steps, each one a place where a camera's picture becomes a claim about
the building:

  lift     A box's bottom-centre is where the object meets the floor. Through
           the camera's floor homography that pixel becomes a position in
           metres, and the box's top edge then gives the object's height in
           closed form. A height no person or vehicle could have means the box
           does not stand on the floor where it seems to - usually legs hidden
           behind a pallet - and the sighting is dropped rather than placed
           somewhere wrong.
  fuse     Sightings of one instant from different cameras that land in the
           same place are one object. Never two from the same camera: its own
           tracker has already said they are different.
  follow   Fused objects are linked over time into global identities, by where
           they should be now and by which camera tracks they were built from.

Nothing here reads the dataset's labels. `evaluate` compares against them
afterwards.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from scene import Camera

FPS = 10.0                      # analysed frames per second (30 fps / stride 3)

# Per class, all measured on this recording (README, "How the floor is built"):
#   height     plausible height in metres; outside it the box is not standing on
#              the floor where it seems to (legs hidden behind a pallet, a rack
#              read as a vehicle) and the sighting is dropped
#   max_scale  coarsest floor resolution, m/px, at which a sighting is placed.
#              People: median error 0.15-0.24 m up to 0.25 m/px, 0.64 m beyond.
#              Forklifts are big, and a fifth of the moving ones are only ever
#              seen far away: they are placed out to 0.8 m/px, shown on the plan,
#              and kept out of every speed and distance alert (analytics.py
#              trusts a vehicle's position only at 0.15 m/px or finer).
#              Pallet trucks are only placed reliably close to a camera.
#   fuse_m     how far apart two cameras' sightings of one object can land
#   noise_m    position noise allowed when following an identity frame to frame
#   vmax       fastest believable speed, m/s - sets how far an identity may move
#   depth_m    how far behind the box's bottom edge the object's centre lies
#   min_frames analysed frames before an identity is reported
#   static     drop a sighting whose box looks exactly like the empty-floor
#              background: a rack read as a reach truck is static scenery
CLASS = {
    "person":       {"height": (0.9, 2.3), "max_scale": 0.25, "fuse_m": 0.9, "noise_m": 0.6,
                     "vmax": 2.5, "depth_m": 0.0, "min_frames": 5, "static": False, "confirm_score": 0.5},
    "forklift":     {"height": (1.2, 3.8), "max_scale": 0.80, "fuse_m": 2.0, "noise_m": 1.0,
                     "vmax": 4.0, "depth_m": 0.8, "min_frames": 8, "static": True, "confirm_score": 0.5},
    "pallet_truck": {"height": (0.6, 3.0), "max_scale": 0.10, "fuse_m": 1.6, "noise_m": 0.8,
                     "vmax": 2.5, "depth_m": 0.5, "min_frames": 8, "static": False, "confirm_score": 0.4},
    "robot":        {"height": (0.2, 1.6), "max_scale": 0.20, "fuse_m": 1.0, "noise_m": 0.6,
                     "vmax": 2.0, "depth_m": 0.3, "min_frames": 5, "static": False, "confirm_score": 0.4},
}
STATIC_NCC = 0.90               # this similar to the long-run background = scenery
EDGE = 3                        # px: a box this close to the frame edge is cut by it


@dataclass
class Sighting:
    cam: str
    frame: int
    track: int
    cls: str
    score: float
    box: tuple[float, float, float, float]
    x: float = math.nan
    y: float = math.nan
    height: float = math.nan
    scale: float = math.nan         # metres of floor per pixel at the foot point
    side_cut: bool = False
    reject: str = ""

    @property
    def weight(self) -> float:
        """How much this sighting counts when cameras disagree: finer floor wins."""
        w = 1.0 / max(self.scale, 1e-3) ** 2
        return w * (0.25 if self.side_cut else 1.0) * self.score


def lift(cam: Camera, cls: str, frame: int, track: int, score: float,
         box: np.ndarray, static_ncc: float = math.nan) -> Sighting:
    x1, y1, x2, y2 = (float(v) for v in box)
    s = Sighting(cam.id, frame, int(track), cls, float(score), (x1, y1, x2, y2))
    if CLASS[cls]["static"] and static_ncc > STATIC_NCC:
        s.reject = "static scenery"
        return s
    if y2 >= cam.height - EDGE:
        s.reject = "feet below the frame"
        return s
    s.side_cut = x1 <= EDGE or x2 >= cam.width - EDGE
    u, v = (x1 + x2) / 2.0, y2
    fx, fy = cam.to_floor(np.array([u]), np.array([v]))
    if not np.isfinite(fx[0]):
        s.reject = "above the horizon"
        return s
    spec = CLASS[cls]
    sc = float(cam.floor_scale(np.array([u]), np.array([v]))[0])
    if not np.isfinite(sc) or sc > spec["max_scale"]:
        s.reject = "too far to place"
        return s
    px, py = float(fx[0]), float(fy[0])
    if y1 > EDGE:
        h = cam.height_at(px, py, y1)
        lo, hi = spec["height"]
        if not (lo <= h <= hi):
            s.reject = "height implausible"
            return s
        s.height = h
    # a vehicle's box bottom is its near edge; its centre is further along the ray
    if spec["depth_m"]:
        dx, dy = px - cam.centre[0], py - cam.centre[1]
        d = math.hypot(dx, dy)
        if d > 1e-6:
            px += dx / d * spec["depth_m"]
            py += dy / d * spec["depth_m"]
    s.x, s.y, s.scale = px, py, sc
    return s


# ------------------------------------------------------------------- fusion
@dataclass
class Blob:
    """The sightings of one object at one instant, and where they agree it is."""

    cls: str
    members: list[Sighting]
    x: float = 0.0
    y: float = 0.0
    height: float = math.nan
    gid: int = -1

    def settle(self) -> None:
        w = np.array([m.weight for m in self.members])
        w = w if w.sum() > 0 else np.ones(len(w))
        self.x = float(np.dot(w, [m.x for m in self.members]) / w.sum())
        self.y = float(np.dot(w, [m.y for m in self.members]) / w.sum())
        hs = [m.height for m in self.members if np.isfinite(m.height)]
        self.height = float(np.median(hs)) if hs else math.nan

    @property
    def cams(self) -> set[str]:
        return {m.cam for m in self.members}

    @property
    def keys(self) -> set[tuple[str, int]]:
        return {(m.cam, m.track) for m in self.members if m.track >= 0}

    @property
    def spread_m(self) -> float:
        if len(self.members) < 2:
            return 0.0
        p = np.array([[m.x, m.y] for m in self.members])
        return float(np.linalg.norm(p - p.mean(0), axis=1).max())


def fuse(sightings: list[Sighting]) -> list[Blob]:
    """Group one instant's sightings into objects, finest-placed first."""
    blobs: list[Blob] = []
    for s in sorted(sightings, key=lambda s: -s.weight):
        best, best_d = None, CLASS[s.cls]["fuse_m"]
        for b in blobs:
            if b.cls != s.cls or s.cam in b.cams:
                continue
            d = math.hypot(s.x - b.x, s.y - b.y)
            if d < best_d:
                best, best_d = b, d
        if best is None:
            b = Blob(s.cls, [s])
            b.settle()
            blobs.append(b)
        else:
            best.members.append(s)
            best.settle()
    return blobs


# ------------------------------------------------------------------ identity
@dataclass
class Track:
    gid: int
    cls: str
    frames: list[int] = field(default_factory=list)
    xs: list[float] = field(default_factory=list)
    ys: list[float] = field(default_factory=list)
    heights: list[float] = field(default_factory=list)
    ncams: list[int] = field(default_factory=list)
    keys: Counter = field(default_factory=Counter)
    seen_by: Counter = field(default_factory=Counter)
    scores: list[float] = field(default_factory=list)
    scales: list[float] = field(default_factory=list)    # finest m/px among the sightings

    def predict(self, frame: int) -> tuple[float, float]:
        if len(self.xs) < 3:
            return self.xs[-1], self.ys[-1]
        k = min(5, len(self.xs) - 1)
        dt = max(self.frames[-1] - self.frames[-1 - k], 1)
        vx = (self.xs[-1] - self.xs[-1 - k]) / dt
        vy = (self.ys[-1] - self.ys[-1 - k]) / dt
        gap = frame - self.frames[-1]
        return self.xs[-1] + vx * gap, self.ys[-1] + vy * gap

    @property
    def confirmed(self) -> bool:
        """Old enough, and either seen by two cameras or confidently by one."""
        if len(self.frames) < CLASS[self.cls]["min_frames"]:
            return False
        return max(self.ncams) >= 2 or float(np.median(self.scores)) >= CLASS[self.cls]["confirm_score"]

    @property
    def height(self) -> float:
        return float(np.median(self.heights)) if self.heights else math.nan


class World:
    """Global identities, updated one analysed frame at a time."""

    def __init__(self, max_gap_s: float = 2.0):
        self.tracks: dict[int, Track] = {}
        self.max_gap = int(max_gap_s * FPS)
        self._next = 1

    def step(self, frame: int, blobs: list[Blob], stride: int = 3) -> list[Blob]:
        live = [t for t in self.tracks.values() if frame - t.frames[-1] <= self.max_gap * stride]
        if blobs and live:
            cost = np.full((len(blobs), len(live)), 1e6)
            for i, b in enumerate(blobs):
                for j, t in enumerate(live):
                    if t.cls != b.cls:
                        continue
                    px, py = t.predict(frame)
                    d = math.hypot(b.x - px, b.y - py)
                    # how far it could have gone since it was last placed, plus noise
                    gap_s = (frame - t.frames[-1]) / (FPS * stride)
                    spec = CLASS[b.cls]
                    gate = spec["noise_m"] + spec["vmax"] * gap_s
                    shared = sum(t.keys.get(k, 0) for k in b.keys)
                    if shared and d <= 2.0 * gate:
                        # a camera tracker vouching for the link is the strongest
                        # evidence - but not strong enough to excuse a teleport
                        cost[i, j] = d / (1.0 + shared)
                    elif d <= gate:
                        cost[i, j] = d
            rows, cols = linear_sum_assignment(cost)
            for i, j in zip(rows, cols):
                if cost[i, j] < 1e6:
                    self._extend(live[j], frame, blobs[i])
        for b in blobs:
            if b.gid < 0:
                t = Track(self._next, b.cls)
                self._next += 1
                self.tracks[t.gid] = t
                self._extend(t, frame, b)
        return blobs

    def _extend(self, t: Track, frame: int, b: Blob) -> None:
        t.frames.append(frame)
        t.xs.append(b.x)
        t.ys.append(b.y)
        t.ncams.append(len(b.cams))
        t.scores.append(max(m.score for m in b.members))
        t.scales.append(min(m.scale for m in b.members))
        if np.isfinite(b.height):
            t.heights.append(b.height)
        for k in b.keys:
            t.keys[k] += 1
        for c in b.cams:
            t.seen_by[c] += 1
        b.gid = t.gid


# --------------------------------------------------------------- running it
@dataclass
class Result:
    """Everything later steps need, per analysed frame."""

    frames: list[int]
    blobs: dict[int, list[Blob]]              # frame -> fused objects (with gid)
    tracks: dict[int, Track]
    rejects: Counter
    sightings: dict[int, list[Sighting]]      # frame -> every lifted sighting

    def confirmed_ids(self) -> set[int]:
        return {g for g, t in self.tracks.items() if t.confirmed}

    def positions(self, frame: int, smooth: int = 3) -> list[tuple[int, str, float, float]]:
        """Confirmed objects at a frame: gid, class, x, y (lightly smoothed)."""
        ok = self.confirmed_ids()
        out = []
        for b in self.blobs.get(frame, []):
            if b.gid not in ok:
                continue
            t = self.tracks[b.gid]
            i = t.frames.index(frame)
            lo = max(0, i - smooth + 1)
            out.append((b.gid, b.cls, float(np.mean(t.xs[lo:i + 1])), float(np.mean(t.ys[lo:i + 1]))))
        return out


def lift_all(cams: dict[str, Camera], detections: dict[str, tuple[np.ndarray, list[str]]],
             static: dict[str, np.ndarray] | None = None, on_floor=None
             ) -> tuple[dict[int, list[Sighting]], Counter]:
    """Every cached detection lifted to the floor, grouped by frame.

    `detections[cam]` is the table from detect.py: frame, track id, x1, y1,
    x2, y2, score, class index - and the class names. `static[cam]`, aligned
    with those rows, is each box's similarity to the empty-floor background.
    `on_floor(x, y)`, where the building's outline is known, says whether a
    point is inside it: a sighting placed beyond the walls was placed wrong
    (a far, coarse view), and is dropped rather than drawn in the car park.
    """
    by_frame: dict[int, list[Sighting]] = defaultdict(list)
    rejects: Counter = Counter()
    for cid, (rows, classes) in detections.items():
        cam = cams[cid]
        ncc = static.get(cid) if static else None
        for i, r in enumerate(rows):
            s = lift(cam, classes[int(r[7])], int(r[0]), int(r[1]), float(r[6]), r[2:6],
                     float(ncc[i]) if ncc is not None else math.nan)
            if not s.reject and on_floor is not None and not on_floor(s.x, s.y):
                s.reject = "outside the building"
            if s.reject:
                rejects[(s.cls, s.reject)] += 1
            else:
                by_frame[int(r[0])].append(s)
    return dict(by_frame), rejects


def track(frames: list[int], by_frame: dict[int, list[Sighting]], rejects: Counter | None = None,
          only: set[str] | None = None) -> Result:
    """Fuse and follow every analysed frame, optionally from a subset of cameras."""
    world = World()
    stride = (frames[1] - frames[0]) if len(frames) > 1 else 1
    blobs = {}
    kept = {}
    for f in frames:
        s = by_frame.get(f, [])
        if only is not None:
            s = [x for x in s if x.cam in only]
        kept[f] = s
        blobs[f] = world.step(f, fuse(s), stride)
    return Result(frames, blobs, world.tracks, rejects or Counter(), kept)


def stitch(res: Result, max_gap_s: float = 2.5, stride: int = 3) -> int:
    """Join identities that broke: one ends, another of its class starts nearby soon after.

    A person who walks behind a rack upright, or out of one camera's view and
    into another's a few metres on, comes back as a new identity. If an
    identity ends and another begins within `max_gap_s`, close enough that the
    first could have walked there at a believable speed, they are one. Pairs
    are joined cheapest first, and an identity is joined at most once at each
    end. Returns the number of joins.
    """
    joined = 0
    while True:
        tracks = sorted(res.tracks.values(), key=lambda t: t.frames[0])
        cands = []
        for a in tracks:
            for b in tracks:
                if a is b or a.cls != b.cls or b.frames[0] <= a.frames[-1]:
                    continue
                gap_s = (b.frames[0] - a.frames[-1]) / (FPS * stride)
                if gap_s > max_gap_s:
                    continue
                spec = CLASS[a.cls]
                px, py = a.predict(b.frames[0]) if gap_s < 1.0 else (a.xs[-1], a.ys[-1])
                d = math.hypot(b.xs[0] - px, b.ys[0] - py)
                # a walking pace, not the fastest believable one: a join is a guess
                if d <= spec["noise_m"] + 0.6 * spec["vmax"] * gap_s:
                    cands.append((d + 0.5 * gap_s, a.gid, b.gid))
        if not cands:
            return joined
        cands.sort()
        used_end, used_start, merges = set(), set(), []
        for _, ga, gb in cands:
            if ga in used_end or gb in used_start or ga in used_start or gb in used_end:
                continue
            used_end.add(ga)
            used_start.add(gb)
            merges.append((ga, gb))
        if not merges:
            return joined
        for ga, gb in merges:
            a, b = res.tracks[ga], res.tracks.pop(gb)
            for name in ("frames", "xs", "ys", "heights", "ncams", "scores", "scales"):
                getattr(a, name).extend(getattr(b, name))
            a.keys.update(b.keys)
            a.seen_by.update(b.seen_by)
            for f in b.frames:
                for blob in res.blobs.get(f, []):
                    if blob.gid == gb:
                        blob.gid = ga
            joined += 1


def run(cams: dict[str, Camera], detections: dict[str, tuple[np.ndarray, list[str]]],
        frames: list[int], static: dict[str, np.ndarray] | None = None) -> Result:
    """Lift, fuse, follow and stitch every analysed frame."""
    by_frame, rejects = lift_all(cams, detections, static)
    res = track(frames, by_frame, rejects)
    stitch(res, stride=(frames[1] - frames[0]) if len(frames) > 1 else 1)
    return res
