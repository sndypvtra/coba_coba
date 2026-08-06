"""One identity per person, not one per camera.

Each camera runs its own tracker, so four cameras watching one warehouse produce
four independent sets of track IDs. Person 3 is `Camera_01#7` and `Camera_02#2`
and `Camera#4`, and a headcount that adds those up says twelve people are in a
room containing three.

Fusion happens on the floor, where the four views are comparable:

  1. per frame, group observations that land in the same place - never two from
     the same camera, which the per-camera tracker has already separated
  2. carry those groups forward in time as global identities

Step 2 does not rely on distance alone. A group that contains `Camera_01#7`
today and a group that contained `Camera_01#7` a moment ago are the same object
almost regardless of where they are, because the single-camera tracker is the
one component that has appearance to work with. Distance is the fallback, not
the primary evidence - which is what keeps identities alive through the moment
when two people pass each other in an aisle.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from factory_vision.spatial.lift import Observation


@dataclass
class Cluster:
    """The observations of one object at one instant, and their consensus."""

    x: float
    y: float
    height: float
    label: str
    conf: float
    members: list[Observation] = field(default_factory=list)
    gid: int = -1

    @property
    def cameras(self) -> list[str]:
        return [o.camera for o in self.members]

    @property
    def keys(self) -> set[tuple[str, int]]:
        return {(o.camera, o.track_id) for o in self.members}

    @property
    def spread_m(self) -> float:
        """How far apart the cameras placed this object. 0 for a single view."""
        if len(self.members) < 2:
            return 0.0
        p = np.array([[o.x, o.y] for o in self.members])
        return float(np.max(np.linalg.norm(p - p.mean(0), axis=1)))


@dataclass
class GlobalTrack:
    gid: int
    label_votes: Counter = field(default_factory=Counter)
    key_votes: Counter = field(default_factory=Counter)
    frames: list[int] = field(default_factory=list)
    xs: list[float] = field(default_factory=list)
    ys: list[float] = field(default_factory=list)
    heights: list[float] = field(default_factory=list)
    cameras: list[int] = field(default_factory=list)   # how many saw it, per frame
    spreads: list[float] = field(default_factory=list)
    yaw: float = 0.0
    last_seen: int = -1

    @property
    def label(self) -> str:
        return self.label_votes.most_common(1)[0][0] if self.label_votes else "person"

    @property
    def height(self) -> float:
        return float(np.median(self.heights)) if self.heights else float("nan")

    @property
    def position(self) -> tuple[float, float]:
        return self.xs[-1], self.ys[-1]

    def predict(self, frame: int) -> tuple[float, float]:
        """Where the object should be now, from its last observed velocity."""
        if len(self.xs) < 2:
            return self.xs[-1], self.ys[-1]
        dt = max(self.frames[-1] - self.frames[-2], 1)
        vx = (self.xs[-1] - self.xs[-2]) / dt
        vy = (self.ys[-1] - self.ys[-2]) / dt
        gap = frame - self.frames[-1]
        return self.xs[-1] + vx * gap, self.ys[-1] + vy * gap

    def path_length_m(self) -> float:
        if len(self.xs) < 2:
            return 0.0
        p = np.stack([self.xs, self.ys], 1)
        return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


def cluster_frame(obs: list[Observation], radius: float) -> list[Cluster]:
    """Group same-instant observations that describe the same object.

    Greedy and seeded by precision: the observation the geometry trusts most
    starts each group, and the rest join the group whose running centroid they
    are inside. Two constraints keep the grouping honest.

    *Never two from one camera.* The per-camera tracker has already ruled they
    are different objects, and overruling it here from position alone would
    merge two people standing in line with the lens.

    *Never two different classes.* In this warehouse the three people never come
    within 8.07 m of one another, so position alone would be plenty to tell them
    apart - but a person and a humanoid robot pass within 0.69 m, which is
    *inside* the fusion radius. Without the class constraint that pass merges a
    person into a robot and the headcount drops. A view that disagrees about the
    class therefore starts its own group and is re-attached later by track
    identity, which is stronger evidence than proximity anyway.
    """
    live = [o for o in obs if o.ok]
    live.sort(key=lambda o: -o.weight)
    clusters: list[Cluster] = []
    for o in live:
        best, best_d = None, radius
        for c in clusters:
            if o.camera in c.cameras or c.label != o.label:
                continue
            d = float(np.hypot(o.x - c.x, o.y - c.y))
            if d < best_d:
                best, best_d = c, d
        if best is None:
            clusters.append(Cluster(o.x, o.y, o.height, o.label, o.conf, [o]))
        else:
            best.members.append(o)
            _recompute(best)
    for c in clusters:
        _recompute(c)
    return clusters


def _recompute(c: Cluster) -> None:
    w = np.array([o.weight for o in c.members], float)
    if w.sum() <= 0:
        w = np.ones(len(c.members))
    xs = np.array([o.x for o in c.members])
    ys = np.array([o.y for o in c.members])
    c.x = float((xs * w).sum() / w.sum())
    c.y = float((ys * w).sum() / w.sum())
    hs = [o.height for o in c.members if np.isfinite(o.height)]
    c.height = float(np.median(hs)) if hs else float("nan")
    c.conf = float(max(o.conf for o in c.members))
    c.label = Counter(o.label for o in c.members).most_common(1)[0][0]


class Fuser:
    """Assigns and maintains global identities across frames."""

    def __init__(self, fuse_radius: float, max_age: int, assoc_radius: float | None = None):
        self.fuse_radius = fuse_radius
        self.assoc_radius = assoc_radius or fuse_radius * 2.0
        self.max_age = max_age
        self.tracks: dict[int, GlobalTrack] = {}
        self._next = 1
        self.merges = 0          # observations absorbed into a multi-camera cluster
        self.key_recoveries = 0  # associations that distance alone would have missed

    def update(self, frame: int, obs: list[Observation]) -> list[Cluster]:
        clusters = cluster_frame(obs, self.fuse_radius)
        self.merges += sum(len(c.members) - 1 for c in clusters)

        alive = [t for t in self.tracks.values() if frame - t.last_seen <= self.max_age]
        if clusters and alive:
            cost = np.full((len(clusters), len(alive)), 1e6)
            for i, c in enumerate(clusters):
                for j, t in enumerate(alive):
                    px, py = t.predict(frame)
                    d = float(np.hypot(c.x - px, c.y - py))
                    shared = sum(t.key_votes.get(k, 0) for k in c.keys)
                    if shared:
                        # A single-camera tracker's own identity claim is the
                        # strongest evidence available; distance only breaks ties
                        # between tracks that both claim the same key.
                        cost[i, j] = d / (1.0 + shared)
                    elif d <= self.assoc_radius:
                        cost[i, j] = d
            rows, cols = linear_sum_assignment(cost)
            for i, j in zip(rows, cols):
                if cost[i, j] >= 1e6:
                    continue
                t = alive[j]
                c = clusters[i]
                if np.hypot(c.x - t.predict(frame)[0], c.y - t.predict(frame)[1]) > self.assoc_radius:
                    self.key_recoveries += 1
                self._append(t, frame, c)
                c.gid = t.gid

        for c in clusters:
            if c.gid < 0:
                t = GlobalTrack(self._next)
                self._next += 1
                self.tracks[t.gid] = t
                self._append(t, frame, c)
                c.gid = t.gid
        return clusters

    def _append(self, t: GlobalTrack, frame: int, c: Cluster) -> None:
        if t.xs:
            dx, dy = c.x - t.xs[-1], c.y - t.ys[-1]
            if np.hypot(dx, dy) > 0.12:       # ignore jitter when standing still
                t.yaw = float(np.arctan2(dy, dx))
        t.frames.append(frame)
        t.xs.append(c.x)
        t.ys.append(c.y)
        t.cameras.append(len(c.members))
        t.spreads.append(c.spread_m)
        if np.isfinite(c.height):
            t.heights.append(c.height)
        t.label_votes[c.label] += 1
        for k in c.keys:
            t.key_votes[k] += 1
        t.last_seen = frame

    def confirmed(self, min_age: int, min_views: int = 1) -> dict[int, GlobalTrack]:
        """Identities old enough, and corroborated by enough cameras, to report.

        The second gate is what a multi-camera install buys over four separate
        ones. A real object standing in the overlap is eventually seen by more
        than one view; a phantom - a "humanoid robot" box that a single camera
        puts on a pallet truck - is not, because the other cameras look at that
        same truck from a different angle and do not produce it. Requiring a
        second view at *some point* in an identity's life, rather than in every
        frame, keeps people who walk briefly into a single-camera corner.
        """
        return {g: t for g, t in self.tracks.items()
                if len(t.frames) >= min_age
                and (max(t.cameras) if t.cameras else 0) >= min_views}
