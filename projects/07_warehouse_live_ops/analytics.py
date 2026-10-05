"""The analytics, computed from the floor - never from pixels.

Everything here reads `world.Result`: confirmed identities with positions in
metres, ten times a second. Working in metres is what makes the numbers mean
the same thing in every camera: a counting line, a zone or a 1.5 m safety
distance is drawn once on the floor plan and holds for every view of it.

Per frame (`Frame`), for the live panel and the overlays:
    who is on the floor, walking or still; who is in which zone; lines crossed
    so far; people near a moving forklift; forklifts over the speed limit;
    people in the forklift lane or against a one-way aisle; crowds; people still
    for too long.
Over the window (`summary`), for the report:
    the same, as counts, durations, rates and places.

The numbering (#1-#15) follows the list the project was asked to cover.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

import config as C
from world import FPS, Result

VEHICLE_BODY = {"forklift": (2.6, 1.2), "pallet_truck": (1.8, 0.9), "robot": (0.8, 0.6)}
RELIABLE_SCALE = {"person": 0.25, "forklift": 0.15, "pallet_truck": 0.10, "robot": 0.15}


# ------------------------------------------------------------------ geometry
def inside(x, y, poly) -> np.ndarray:
    """Points inside a polygon (ray casting), vectorised over x, y."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    res = np.zeros(x.shape, bool)
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        cond = (y1 > y) != (y2 > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xin = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        res ^= cond & (x < xin)
    return res


def side(line: C.Line, x: float, y: float) -> float:
    (ax, ay), (bx, by) = line.a, line.b
    return (bx - ax) * (y - ay) - (by - ay) * (x - ax)


def crosses(line: C.Line, p0, p1) -> int:
    """+1 left-to-right, -1 right-to-left, 0 if the step does not cross the segment."""
    s0, s1 = side(line, *p0), side(line, *p1)
    if s0 == 0 or s1 == 0 or (s0 > 0) == (s1 > 0):
        return 0
    (ax, ay), (bx, by) = line.a, line.b
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    den = (bx - ax) * dy - (by - ay) * dx
    if abs(den) < 1e-12:
        return 0
    t = ((p0[0] - ax) * dy - (p0[1] - ay) * dx) / den
    return (1 if s0 > 0 else -1) if 0.0 <= t <= 1.0 else 0


def edge_distance(x: float, y: float, poly) -> float:
    """Distance from a point to the nearest edge of a polygon."""
    best = math.inf
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / max(dx * dx + dy * dy, 1e-12)))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def body_distance(px, py, vx, vy, heading, length, width) -> np.ndarray:
    """Distance from points to a vehicle's body, an oriented rectangle."""
    c, s = math.cos(-heading), math.sin(-heading)
    lx = c * (np.asarray(px) - vx) - s * (np.asarray(py) - vy)
    ly = s * (np.asarray(px) - vx) + c * (np.asarray(py) - vy)
    return np.hypot(np.maximum(np.abs(lx) - length / 2, 0), np.maximum(np.abs(ly) - width / 2, 0))


# ------------------------------------------------------------------- motion
@dataclass
class Motion:
    gid: int
    cls: str
    frames: np.ndarray            # analysed source-frame numbers, ascending
    x: np.ndarray                 # smoothed metres
    y: np.ndarray
    speed: np.ndarray             # m/s over a one-second window
    heading: np.ndarray           # radians, held while stationary
    ncams: np.ndarray
    reliable: np.ndarray          # speed measured from fine enough positions, over enough time

    def at(self, frame: int) -> int | None:
        i = int(np.searchsorted(self.frames, frame))
        return i if i < len(self.frames) and self.frames[i] == frame else None


def motions(res: Result, stride: int) -> dict[int, Motion]:
    """Smooth each confirmed identity and give it a speed and heading.

    Fused positions jitter by a decimetre or two from frame to frame; speed is
    therefore measured over one second (ten analysed frames), and positions are
    averaged over half a second before anything is drawn or measured.
    """
    out = {}
    for gid in res.confirmed_ids():
        t = res.tracks[gid]
        # people: a one-second fit; vehicles, placed less precisely: two seconds
        half = int(FPS // 2) if t.cls == "person" else int(FPS)
        f = np.asarray(t.frames)
        x, y = np.asarray(t.xs, float), np.asarray(t.ys, float)
        k = np.ones(5) / 5
        if len(x) >= 5:
            xs = np.convolve(np.pad(x, 2, mode="edge"), k, "valid")
            ys = np.convolve(np.pad(y, 2, mode="edge"), k, "valid")
        else:
            xs, ys = x.copy(), y.copy()
        # Speed is the slope of a straight-line fit through one second of raw
        # positions, not the distance between two noisy end points: one bad
        # placement cannot turn a walking pace into a speeding forklift.
        ts = f / (FPS * stride)
        sp = np.zeros(len(f))
        hd = np.zeros(len(f))
        last = 0.0
        for i in range(len(f)):
            a, b = max(0, i - half), min(len(f), i + half + 1)
            if b - a >= 4 and ts[b - 1] - ts[a] > 0.3:
                tt = ts[a:b] - ts[a:b].mean()
                den = float((tt ** 2).sum())
                vx = float((tt * (x[a:b] - x[a:b].mean())).sum() / den)
                vy = float((tt * (y[a:b] - y[a:b].mean())).sum() / den)
                sp[i] = math.hypot(vx, vy)
                if sp[i] > 0.2:
                    last = math.atan2(vy, vx)
            hd[i] = last
        # A speed is only trusted where the positions behind it are fine: the
        # object seen closely enough (finest sighting under RELIABLE_SCALE m/px)
        # for most of the second, two seconds into its track, and not faster
        # than anything of its kind can move. Elsewhere it is shown but never
        # raises an alert.
        sc = np.asarray(t.scales, float)
        rel = np.zeros(len(f), bool)
        from world import CLASS
        vmax = CLASS[t.cls]["vmax"]
        for i in range(len(f)):
            a, b = max(0, i - half), min(len(f), i + half + 1)
            rel[i] = ((ts[i] - ts[0]) >= 2.0 and np.median(sc[a:b]) <= RELIABLE_SCALE.get(t.cls, 0.15)
                      and sp[i] <= vmax)
        out[gid] = Motion(gid, t.cls, f, xs, ys, sp, hd, np.asarray(t.ncams), rel)
    return out


# ------------------------------------------------------------------- frames
@dataclass
class Obj:
    gid: int
    cls: str
    x: float
    y: float
    speed: float
    heading: float
    ncams: int
    reliable: bool = True
    walking: bool = False
    zones: tuple = ()
    alerts: tuple = ()            # "near_miss", "idle", "lane", "wrong_way", "crowd", "speeding"


@dataclass
class Frame:
    frame: int
    t: float                                   # seconds into the window
    objects: list[Obj]
    camera_people: dict[str, int]              # #1: people the camera itself sees now
    zone_people: dict[str, int]                # #4
    line_totals: dict[str, tuple[int, int]]    # #3: in, out so far
    near_pairs: list[tuple[int, int, float]]   # #11: person, forklift, metres
    events_so_far: dict[str, int]
    crowd_spots: list[tuple[float, float, int]]  # #7: x, y, people


def camera_counts(detections: dict, classes_of: dict, frame: int,
                  min_height_px: float = 40.0) -> dict[str, int]:
    """#1 - people one camera sees in its own picture, tracked and at least 40 px tall."""
    out = {}
    for cid, (rows, classes) in detections.items():
        r = rows[rows[:, 0] == frame]
        k = classes.index("person")
        tall = (r[:, 5] - r[:, 3]) >= min_height_px
        out[cid] = int(((r[:, 7] == k) & (r[:, 1] >= 0) & tall).sum())
    return out


def analyse(scene: str, res: Result, detections: dict, stride: int) -> tuple[list[Frame], dict]:
    site = C.SITE.get(scene, {"zones": [], "lines": []})
    zones, lines = site["zones"], site["lines"]
    mot = motions(res, stride)
    frames = res.frames
    t0 = frames[0]

    line_in = {ln.name: 0 for ln in lines}
    line_out = {ln.name: 0 for ln in lines}
    seen_crossings = []
    prev_pos: dict[int, tuple[float, float]] = {}
    zone_time = defaultdict(float)            # (zone, gid) -> seconds
    lane_entries, lane_seconds = 0, 0.0
    lane_events = []
    lane_last: dict[int, int] = {}            # gid -> last frame seen in the lane
    lane_outside: set[int] = set()            # gids seen outside the lane at least once
    in_lane_prev: set[int] = set()
    crowd_open: list[dict] = []
    crowd_events = []
    wrong_open: dict[int, int] = {}           # gid -> frames moving the wrong way in a row
    wrong_events = []
    near_open: dict[tuple[int, int], dict] = {}
    near_events = []
    speed_open: dict[int, dict] = {}
    speed_events = []
    over_limit: dict[int, int] = {}            # gid -> analysed frames in a row over the limit
    still_since: dict[int, tuple[int, float, float]] = {}
    idle_events: dict[int, dict] = {}
    crowd_frames, crowd_spots_all = 0, []
    walk_frames = defaultdict(int)
    obs_frames = defaultdict(int)
    heat = []
    out_frames = []
    dt = 1.0 / FPS

    for f in frames:
        # which cameras placed each identity now: every event records who saw it
        cams_of = {b.gid: sorted(b.cams) for b in res.blobs.get(f, [])}
        objs = []
        for gid, m in mot.items():
            i = m.at(f)
            if i is None:
                continue
            o = Obj(gid, m.cls, float(m.x[i]), float(m.y[i]), float(m.speed[i]),
                    float(m.heading[i]), int(m.ncams[i]), bool(m.reliable[i]))
            o.walking = m.cls == "person" and o.speed > C.WALKING_MS
            o.zones = tuple(z.name for z in zones if inside(o.x, o.y, z.polygon))
            objs.append(o)
        people = [o for o in objs if o.cls == "person"]
        vehicles = [o for o in objs if o.cls in VEHICLE_BODY]
        alerts = defaultdict(set)

        # #3 lines
        for o in people:
            if o.gid in prev_pos:
                for ln in lines:
                    c = crosses(ln, prev_pos[o.gid], (o.x, o.y))
                    if c > 0:
                        line_in[ln.name] += 1
                    elif c < 0:
                        line_out[ln.name] += 1
                    if c:
                        seen_crossings.append({"line": ln.name, "gid": o.gid, "t": round((f - t0) / (FPS * stride), 1),
                                               "dir": "in" if c > 0 else "out", "x": round(o.x, 2),
                                               "y": round(o.y, 2), "cams": cams_of.get(o.gid, [])})
            prev_pos[o.gid] = (o.x, o.y)

        # #4 zones, #12 vehicle lane, #13 one-way
        zone_people = {z.name: 0 for z in zones}
        in_lane_now = set()
        for o in people:
            for z in zones:
                if z.kind == "vehicle_lane":
                    # in the lane once LANE_MARGIN_M (config) inside it, out once
                    # outside it: someone walking along its edge is not stepping in
                    # and out of it with every decimetre of position noise
                    if z.name in o.zones and (o.gid in in_lane_prev or
                                              edge_distance(o.x, o.y, z.polygon) >= C.LANE_MARGIN_M):
                        in_lane_now.add(o.gid)
                # the lane's occupancy follows the lane rule above, so "in the lane" means one thing everywhere
                if z.name in o.zones and (z.kind != "vehicle_lane" or o.gid in in_lane_now):
                    zone_people[z.name] += 1
                    zone_time[(z.name, o.gid)] += dt
                    if z.kind == "one_way" and o.speed > C.WRONG_WAY_MS:
                        vx, vy = math.cos(o.heading), math.sin(o.heading)
                        if vx * z.direction[0] + vy * z.direction[1] < -0.5:
                            wrong_open[o.gid] = wrong_open.get(o.gid, 0) + 1
                            if wrong_open[o.gid] == int(FPS):      # one second the wrong way
                                wrong_events.append({"gid": o.gid, "zone": z.name,
                                                     "t": round((f - t0) / (FPS * stride), 1),
                                                     "x": round(o.x, 2), "y": round(o.y, 2),
                                                     "cams": cams_of.get(o.gid, [])})
                            if wrong_open[o.gid] >= int(FPS):
                                alerts[o.gid].add("wrong_way")
                        else:
                            wrong_open.pop(o.gid, None)
        lane_seconds += len(in_lane_now) * dt
        for o in people:
            # an entry is someone seen outside the lane stepping into it, at least
            # LANE_CLEAR_S (config) after they were last in it: a position wobbling
            # on the edge is one entry, not five, and an identity that first
            # appears inside the lane (someone already there, picked up again) is
            # not an entry at all
            if o.gid in in_lane_now - in_lane_prev and o.gid in lane_outside and \
                    f - lane_last.get(o.gid, -10 ** 9) > C.LANE_CLEAR_S * FPS * stride:
                lane_entries += 1
                lane_events.append({"gid": o.gid, "t": round((f - t0) / (FPS * stride), 1),
                                    "x": round(o.x, 2), "y": round(o.y, 2), "cams": cams_of.get(o.gid, [])})
        for g in in_lane_now:
            alerts[g].add("lane")
            lane_last[g] = f
        lane_outside |= {o.gid for o in people if o.gid not in in_lane_now}
        in_lane_prev = in_lane_now

        # #6 walking, #5 heat
        for o in people:
            obs_frames[o.gid] += 1
            walk_frames[o.gid] += int(o.walking)
            heat.append((o.x, o.y))

        # #8 still for too long
        for o in people:
            s = still_since.get(o.gid)
            if s is None or math.hypot(o.x - s[1], o.y - s[2]) > C.IDLE_RADIUS_M:
                still_since[o.gid] = (f, o.x, o.y)
                continue
            dur = (f - s[0]) / (FPS * stride)
            if dur >= C.IDLE_S:
                alerts[o.gid].add("idle")
                ev = idle_events.setdefault(o.gid, {"gid": o.gid, "start_t": round((s[0] - t0) / (FPS * stride), 1),
                                                    "x": round(s[1], 2), "y": round(s[2], 2),
                                                    "cams": cams_of.get(o.gid, [])})
                ev["seconds"] = round(dur, 1)

        # #7 crowds: CROWD_MIN people within CROWD_RADIUS_M of one person, lasting
        # CROWD_S (config). A single frame is not a crowd: one person placed twice
        # by two cameras, for an instant, would otherwise make one.
        spots = []
        if len(people) >= C.CROWD_MIN:
            P = np.array([[o.x, o.y] for o in people])
            d = np.linalg.norm(P[:, None] - P[None], axis=2)
            n_near = (d <= C.CROWD_RADIUS_M).sum(1)
            for i in np.argsort(-n_near):
                if n_near[i] < C.CROWD_MIN:
                    break
                if all(math.hypot(P[i, 0] - sx, P[i, 1] - sy) > 2 * C.CROWD_RADIUS_M for sx, sy, _, _ in spots):
                    members = [people[j] for j in np.nonzero(d[i] <= C.CROWD_RADIUS_M)[0]]
                    spots.append((float(P[i, 0]), float(P[i, 1]), int(n_near[i]), members))
        tnow = round((f - t0) / (FPS * stride), 1)
        live = []
        for sx, sy, n, members in spots:
            ep = next((e for e in crowd_open if math.hypot(sx - e["x"], sy - e["y"]) <= 2 * C.CROWD_RADIUS_M), None)
            if ep is None:
                ep = {"start_t": tnow, "x": round(sx, 2), "y": round(sy, 2), "people_max": n, "people": [],
                      "cams": []}
                crowd_open.append(ep)
            ep["end_t"] = tnow
            ep["people_max"] = max(ep["people_max"], n)
            ep["people"] = sorted(set(ep["people"]) | {o.gid for o in members})
            ep["cams"] = sorted(set(ep["cams"]) | {c for o in members for c in cams_of.get(o.gid, [])})
            if ep["end_t"] - ep["start_t"] >= C.CROWD_S:
                live.append((sx, sy, n))
                for o in members:
                    alerts[o.gid].add("crowd")
        for ep in list(crowd_open):
            if tnow - ep["end_t"] > 1.0:
                crowd_open.remove(ep)
                if ep["end_t"] - ep["start_t"] >= C.CROWD_S:
                    crowd_events.append(ep)
        spots = live
        if spots:
            crowd_frames += 1
            crowd_spots_all.extend(spots)

        # #10 speeding, #11 near misses
        for v in vehicles:
            kmh = v.speed * 3.6
            over = v.cls == "forklift" and v.reliable and kmh > C.SPEED_LIMIT_KMH
            over_limit[v.gid] = over_limit.get(v.gid, 0) + 1 if over else 0
            if over and over_limit[v.gid] >= int(FPS):      # a full second over the limit
                alerts[v.gid].add("speeding")
                ev = speed_open.setdefault(v.gid, {"gid": v.gid, "start_t": tnow, "max_kmh": 0.0,
                                                   "x": round(v.x, 2), "y": round(v.y, 2),
                                                   "cams": cams_of.get(v.gid, [])})
                ev["max_kmh"] = round(max(ev["max_kmh"], kmh), 1)
                ev["end_t"] = tnow
            elif v.gid in speed_open:
                speed_events.append(speed_open.pop(v.gid))
        near_now = []
        for v in vehicles:
            if v.cls != "forklift" or not v.reliable or v.speed < C.VEHICLE_MOVING_MS:
                continue
            L, W = VEHICLE_BODY[v.cls]
            for o in people:
                d = float(body_distance(o.x, o.y, v.x, v.y, v.heading, L, W))
                if d < C.NEAR_MISS_M:
                    near_now.append((o.gid, v.gid, d))
                    alerts[o.gid].add("near_miss")
                    alerts[v.gid].add("near_miss")
                    key = (o.gid, v.gid)
                    ev = near_open.setdefault(key, {"person": o.gid, "forklift": v.gid, "start_t": tnow,
                                                    "min_m": d, "x": o.x, "y": o.y})
                    if d <= ev["min_m"]:
                        ev.update(min_m=d, x=o.x, y=o.y, t=tnow,
                                  cams=sorted(set(cams_of.get(o.gid, [])) | set(cams_of.get(v.gid, []))),
                                  forklift_kmh=round(v.speed * 3.6, 1))
                    ev["last_f"] = f
                    ev["end_t"] = tnow
        for key in list(near_open):
            if f - near_open[key]["last_f"] > FPS * stride * 0.5:      # half a second clear ends it
                near_events.append(near_open.pop(key))

        for o in objs:
            o.alerts = tuple(sorted(alerts.get(o.gid, ())))
        out_frames.append(Frame(
            frame=f, t=round((f - t0) / (FPS * stride), 2), objects=objs,
            camera_people=camera_counts(detections, None, f),
            zone_people=zone_people,
            line_totals={ln.name: (line_in[ln.name], line_out[ln.name]) for ln in lines},
            near_pairs=near_now,
            events_so_far={"near_miss": len(near_events) + len(near_open),
                           "speeding": len(speed_events) + len(speed_open),
                           "lane_entries": lane_entries,
                           "wrong_way": len(wrong_events),
                           "idle": len(idle_events),
                           "crowd_frames": crowd_frames},
            crowd_spots=spots))

    near_events += list(near_open.values())
    speed_events += list(speed_open.values())
    crowd_events += [ep for ep in crowd_open if ep["end_t"] - ep["start_t"] >= C.CROWD_S]
    for ev in near_events:
        ev.pop("last_f", None)
        ev["min_m"] = round(ev["min_m"], 2)
        ev["x"], ev["y"] = round(ev["x"], 2), round(ev["y"], 2)
    summary = summarise(scene, res, mot, out_frames, zones, lines, line_in, line_out, seen_crossings,
                        zone_time, lane_entries, lane_seconds, lane_events, wrong_events, near_events,
                        speed_events, idle_events, crowd_frames, crowd_spots_all, crowd_events,
                        walk_frames, obs_frames, stride)
    summary["heat_points"] = len(heat)
    return out_frames, summary


def summarise(scene, res, mot, frames, zones, lines, line_in, line_out, crossings, zone_time,
              lane_entries, lane_seconds, lane_events, wrong_events, near_events, speed_events, idle_events,
              crowd_frames, crowd_spots, crowd_events, walk_frames, obs_frames, stride) -> dict:
    window_s = len(frames) / FPS
    people = [m for m in mot.values() if m.cls == "person"]
    heads = [sum(1 for o in fr.objects if o.cls == "person") for fr in frames]
    dist = {}
    for m in people:
        step = int(FPS // 2)
        px, py = m.x[::step], m.y[::step]
        seg = np.hypot(np.diff(px), np.diff(py))
        dist[m.gid] = float(seg[seg > 0.1].sum()) if len(seg) else 0.0
    person_s = sum(obs_frames.values()) / FPS
    cams = sorted(frames[0].camera_people) if frames else []
    cam_counts = {c: [fr.camera_people[c] for fr in frames] for c in cams}

    def zone_rows():
        rows = []
        for z in zones:
            occ = [fr.zone_people[z.name] for fr in frames]
            per = [v for (zn, g), v in zone_time.items() if zn == z.name]
            rows.append({"zone": z.name, "kind": z.kind,
                         "occupancy_mean": round(float(np.mean(occ)), 2), "occupancy_max": int(max(occ)),
                         "people_entered": len(per), "dwell_s_mean": round(float(np.mean(per)), 1) if per else 0.0,
                         "dwell_s_max": round(float(max(per)), 1) if per else 0.0,
                         "person_seconds": round(float(sum(per)), 1)})
        return rows

    vehicles = defaultdict(list)
    for m in mot.values():
        if m.cls in VEHICLE_BODY:
            vehicles[m.cls].append({
                "gid": m.gid, "seconds_seen": round(len(m.frames) / FPS, 1),
                "reliable_speed_s": round(float(m.reliable.sum()) / FPS, 1),
                "moving_pct": round(100.0 * float(np.mean(m.speed[m.reliable] > C.VEHICLE_MOVING_MS)), 1)
                if m.reliable.any() else None,
                # the 90th percentile, not the maximum: one bad placement makes a
                # maximum, and the speeding alert already needs a full second
                "top_kmh_p90": round(float(np.percentile(m.speed[m.reliable], 90)) * 3.6, 1)
                if m.reliable.any() else None})
    ncams = np.concatenate([m.ncams for m in people]) if people else np.zeros(0)
    return {
        "window_s": round(window_s, 1),
        "#1_people_per_camera": {c: {"mean": round(float(np.mean(v)), 1), "max": int(max(v))}
                                 for c, v in cam_counts.items()},
        "#2_headcount": {"mean": round(float(np.mean(heads)), 1), "min": int(min(heads)),
                         "max": int(max(heads)), "unique_identities": len(people)},
        "#3_lines": [{"line": ln.name, "in": line_in[ln.name], "out": line_out[ln.name]} for ln in lines],
        "#3_crossings": crossings,
        "#4_zones": zone_rows(),
        "#6_walking": {"walking_share_pct": round(100.0 * sum(walk_frames.values()) / max(sum(obs_frames.values()), 1), 1),
                       "distance_m_per_person_mean": round(float(np.mean(list(dist.values()))), 1) if dist else 0.0,
                       "travel_m_per_person_hour": round(sum(dist.values()) / max(person_s, 1e-6) * 3600.0),
                       "note": f"walking = faster than {C.WALKING_MS} m/s over one second"},
        "#7_congestion": {"frames_with_a_crowd_pct": round(100.0 * crowd_frames / max(len(frames), 1), 1),
                          "rule": f"{C.CROWD_MIN}+ people within {C.CROWD_RADIUS_M} m",
                          "hotspots": _hotspots(crowd_spots), "events": crowd_events},
        "#8_idle": {"rule": f"within {C.IDLE_RADIUS_M} m of one spot for {C.IDLE_S:.0f} s or more",
                    "events": list(idle_events.values())},
        "#9_forklift_use": vehicles.get("forklift", []),
        "#10_speeding": {"limit_kmh": C.SPEED_LIMIT_KMH, "events": speed_events},
        "#11_near_miss": {"rule": f"person within {C.NEAR_MISS_M} m of a moving forklift's body",
                          "events": near_events},
        "#12_vehicle_lane": {"entries": lane_entries, "person_seconds": round(lane_seconds, 1),
                             "events": lane_events},
        "#13_wrong_way": {"events": wrong_events},
        "#14_other_vehicles": {k: v for k, v in vehicles.items() if k != "forklift"},
        "#15_seen_by_cameras": {"person_frames_seen_by_2plus_pct": round(100.0 * float(np.mean(ncams >= 2)), 1)
                                if len(ncams) else None,
                                "person_frames_seen_by_1_pct": round(100.0 * float(np.mean(ncams == 1)), 1)
                                if len(ncams) else None},
    }


def _hotspots(spots, cell_m: float = 4.0, top: int = 3):
    if not spots:
        return []
    cells = defaultdict(int)
    for x, y, n in spots:
        cells[(round(x / cell_m), round(y / cell_m))] += 1
    best = sorted(cells.items(), key=lambda kv: -kv[1])[:top]
    return [{"x": k[0] * cell_m, "y": k[1] * cell_m, "frames": v} for k, v in best]
