"""What an owner sees: alerts with a severity, in plain words, with a snapshot that proves them.

The analytics (analytics.py, ppe.py) measure; this module only decides how a
measurement is told on screen:

  which events are alerts, and how serious - a near miss outranks a missing
      vest, which outranks a crowd; a person standing still is information;
  what things are called - a camera by the part of the floor it watches, a
      counting line by what it counts, never "Garis C";
  one alert per person for PPE - a person without helmet and vest is one
      alert, not two, and not a new one every time a frame flickers;
  the evidence - a crop of the camera that saw it, at the moment it is reported.

Counting lines and crossings are flows, not alerts: they are counted, not listed.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

import config as C
import ui
from analytics import inside

CAMERA_NAME = {
    # named after the zone each camera's floor covers most (measured on its footprint)
    "warehouse_000": {"Camera_0003": "Area kerja timur", "Camera_0005": "Jalur forklift tengah",
                      "Camera_0011": "Area utara", "Camera_0007": "Area selatan",
                      "Camera_0001": "Area konveyor barat", "Camera_0000": "Sudut barat daya",
                      "Camera_0010": "Lorong tengah", "Camera_0015": "Area kerja timur, sisi dok",
                      "Camera_0008": "Area tengah utara"},
    "warehouse_027": {"Camera_0000": "Lantai utama", "Camera_0005": "Lorong rak",
                      "Camera_0006": "Lantai utama, sisi dinding"},
}
LINE_NAME = {"Garis A": "Lintasan timur", "Garis B": "Lintasan area kerja",
             "Garis C · seberang jalur forklift": "Penyeberangan jalur forklift"}
ZONE_NAME = {"Lorong satu arah (contoh)": "Lorong satu arah"}

# kind: severity, icon, title
KIND = {
    "near_miss": ("high", "warning", "Nyaris tertabrak forklift"),
    "speeding": ("high", "speed", "Forklift melebihi batas kecepatan"),
    "lane": ("medium", "do_not_step", "Pejalan kaki di jalur forklift"),
    "wrong_way": ("medium", "route", "Melawan arah di lorong satu arah"),
    "ppe": ("medium", "engineering", "APD tidak lengkap"),
    "crowd": ("low", "groups", "Kerumunan"),
    "idle": ("info", "hourglass_bottom", "Diam lama di satu titik"),
}


def cam_label(cid: str) -> str:
    return cid.replace("Camera_", "CAM ")


def camera_name(scene: str, cid: str) -> str:
    return CAMERA_NAME.get(scene, {}).get(cid, cam_label(cid))


def line_label(name: str) -> str:
    """'A · Lintasan timur' - the letter stays, so the video, the JSON and the README still agree."""
    return f"{name.split(' ·')[0].replace('Garis ', '')} · {LINE_NAME.get(name, name)}"


def zone_label(name: str) -> str:
    return ZONE_NAME.get(name, name)


def where(scene: str, x, y) -> str:
    """The smallest named zone containing the point, or '' (zones overlap)."""
    if x is None:
        return ""
    zones = [z for z in C.SITE.get(scene, {"zones": []})["zones"] if bool(inside(x, y, z.polygon))]
    if not zones:
        return ""
    area = lambda z: abs(np.cross(np.subtract(z.polygon[1], z.polygon[0]), np.subtract(z.polygon[2], z.polygon[1])))
    return zone_label(min(zones, key=area).name)


@dataclass
class Event:
    t: float                  # seconds into the window, when it is reported
    kind: str
    severity: str
    icon: str
    title: str
    detail: str
    gids: tuple               # who: the person first, then the vehicle
    cam_ids: tuple
    x: float | None = None
    y: float | None = None
    end: float | None = None  # when it was over, where that is known
    moment: float | None = None  # the instant that shows it best (a near miss: the closest approach)

    @property
    def cams(self) -> list[str]:
        return [cam_label(c) for c in self.cam_ids]


def _ev(kind: str, t: float, detail: str, gids, cams, x=None, y=None, title: str | None = None,
        end: float | None = None, moment: float | None = None) -> Event:
    sev, icon, name = KIND[kind]
    return Event(round(float(t), 1), kind, sev, icon, title or name, detail, tuple(gids), tuple(cams or ()), x, y,
                 round(float(end), 1) if end is not None else None,
                 round(float(moment), 1) if moment is not None else None)


def _distance(m: float) -> str:
    # a person "inside" the forklift's outline is a person in its path: say so, not "0,0 m"
    return "di lintasan forklift" if m < 0.5 else f"jarak {ui.num(m)} m"


def ppe_alerts(violations: list[dict], gap_s: float = 5.0) -> list[dict]:
    """One alert per person and episode.

    Helmet and vest missing together are one alert; a person who was already
    reported is reported again only after `gap_s` with nothing missing.
    """
    from ppe import VIOLATION_S
    out, last_end = [], {}
    by_start = sorted(violations, key=lambda e: e["start_t"])
    used = set()
    for i, e in enumerate(by_start):
        if i in used:
            continue
        group = [e]
        for j in range(i + 1, len(by_start)):
            o = by_start[j]
            if j not in used and o["gid"] == e["gid"] and abs(o["start_t"] - e["start_t"]) <= 0.5:
                group.append(o)
                used.add(j)
        g = e["gid"]
        start = min(o["start_t"] for o in group)
        end = max(o["end_t"] for o in group)
        if g in last_end and start - last_end[g] < gap_s:
            last_end[g] = max(last_end[g], end)
            continue
        last_end[g] = end
        out.append({"gid": g, "what": sorted({o["what"] for o in group}), "t": start + VIOLATION_S,
                    "x": e.get("x"), "y": e.get("y"), "cams": e.get("cams", []), "seconds": end - start})
    return out


def events(scene: str, summary: dict, ppe_violations: list[dict] | None = None) -> list[Event]:
    """Every alert and notice of a window, as the owner reads them, in time order."""
    out = []
    a = summary
    for e in a["#11_near_miss"]["events"]:
        # raised the moment the person comes within reach, as an alarm would be; the row
        # reports the closest approach of the whole episode, where it happened
        z = where(scene, e["x"], e["y"])
        out.append(_ev("near_miss", e["start_t"],
                       f"P{e['person']} & forklift F{e['forklift']} · {_distance(e['min_m'])}" + (f" · {z}" if z else ""),
                       (e["person"], e["forklift"]), e.get("cams"), e["x"], e["y"], end=e.get("end_t"),
                       moment=e.get("t")))
    for e in a["#10_speeding"]["events"]:
        out.append(_ev("speeding", e["start_t"], f"F{e['gid']} · puncak {ui.num(e['max_kmh'])} km/j, batas "
                                                 f"{C.SPEED_LIMIT_KMH:.0f}", (e["gid"],), e.get("cams"),
                       e.get("x"), e.get("y"), end=e.get("end_t")))
    for e in a["#12_vehicle_lane"].get("events", []):
        z = where(scene, e["x"], e["y"]) or "Jalur forklift"
        out.append(_ev("lane", e["t"], f"P{e['gid']} · {z}", (e["gid"],), e.get("cams"), e["x"], e["y"]))
    for e in a["#13_wrong_way"]["events"]:
        out.append(_ev("wrong_way", e["t"], f"P{e['gid']} · {zone_label(e['zone'])}", (e["gid"],), e.get("cams"),
                       e["x"], e["y"]))
    for e in a["#7_congestion"].get("events", []):
        out.append(_ev("crowd", e["start_t"], f"{e['people_max']} orang dalam radius {C.CROWD_RADIUS_M:g} m"
                       + (f" · {where(scene, e['x'], e['y'])}" if where(scene, e["x"], e["y"]) else ""),
                       tuple(e["people"]), e.get("cams"), e["x"], e["y"]))
    for e in a["#8_idle"]["events"]:
        z = where(scene, e["x"], e["y"])
        out.append(_ev("idle", e["start_t"] + C.IDLE_S, f"P{e['gid']} · {e['seconds']:.0f} s" + (f" · {z}" if z else ""),
                       (e["gid"],), e.get("cams"), e["x"], e["y"]))
    for e in ppe_alerts(ppe_violations or []):
        what = " & ".join(e["what"])
        out.append(_ev("ppe", e["t"], f"P{e['gid']} · tanpa {what}", (e["gid"],), e["cams"], e["x"], e["y"],
                       title="Tanpa helm & rompi" if len(e["what"]) == 2 else f"Tanpa {what}"))
    return sorted(out, key=lambda e: (e.t, e.kind))


def spotlights(evs: list[Event], shown: list[str], linger_s: float = 4.0) -> list[tuple]:
    """When a camera that is not on screen sees an alert, it is called up: (from, to, camera, event).

    Serious alerts only (high and medium). The switch happens the moment the
    alert is raised - never before, as it could not in a live system - and the
    tile switches back `linger_s` after the alert is over; a later call-up ends
    an earlier one.
    """
    out = []
    for e in evs:
        if e.severity not in ("high", "medium") or not e.cam_ids or set(e.cam_ids) & set(shown):
            continue
        t0, t1 = e.t, max(e.end or e.t, e.t) + linger_s
        if out and t0 < out[-1][1]:
            out[-1] = (out[-1][0], t0, out[-1][2], out[-1][3])
        out.append((t0, t1, e.cam_ids[0], e))
    return [s for s in out if s[1] > s[0]]


# ------------------------------------------------------------ the evidence
def snapshot(ev: Event, res, detections: dict, frames: list, video_path, prefer: list[str] = ()) -> np.ndarray | None:
    """A 16:9 crop of the camera that saw the event, at the moment it is reported.

    The camera is the one, among those that placed the people involved, whose
    picture shows them largest (a camera on screen wins a tie). None when the
    people involved are not in any camera's picture then (seen by others only).
    """
    when = ev.moment if ev.moment is not None else ev.t
    near = sorted(frames, key=lambda f: abs(f.t - when))[:12]
    for fr in near:
        per_cam: dict[str, list] = {}
        for b in res.blobs.get(fr.frame, []):
            if b.gid not in ev.gids:
                continue
            for m in b.members:
                rows = detections.get(m.cam, (None,))[0]
                if rows is None or m.track < 0:
                    continue
                r = rows[(rows[:, 0] == fr.frame) & (rows[:, 1] == m.track)]
                if len(r):
                    per_cam.setdefault(m.cam, []).append(r[0, 2:6])
        if not per_cam:
            continue
        # the camera that shows the most of the people involved, then one on screen, then the largest
        cam = max(per_cam, key=lambda c: (len(per_cam[c]), c in prefer, max(bx[3] - bx[1] for bx in per_cam[c])))
        boxes = per_cam[cam]
        cap = cv2.VideoCapture(str(video_path(cam)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, fr.frame)
        ok, img = cap.read()
        cap.release()
        if not ok:
            continue
        b = np.array(boxes)
        x0, y0, x1, y1 = b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()
        h = max(y1 - y0, 80.0)
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        hh = h * 0.85
        hw = max(hh * 16 / 9, (x1 - x0) / 2 * 1.3)
        hh = hw * 9 / 16
        X0, X1 = int(max(0, cx - hw)), int(min(img.shape[1], cx + hw))
        Y0, Y1 = int(max(0, cy - hh)), int(min(img.shape[0], cy + hh))
        crop = img[Y0:Y1, X0:X1].copy()
        for bx in boxes:            # mark who it is about, in the alert's colour
            ui.corner_box(crop, (bx[0] - X0, bx[1] - Y0, bx[2] - X0, bx[3] - Y0), ui.SEVERITY[ev.severity],
                          thickness=max(2, int(crop.shape[0] / 120)))
        return crop
    return None


# ------------------------------------------------------------ running figures
class Tally:
    """Figures that accumulate over the window, frame by frame."""

    def __init__(self):
        self.lift_moving = 0
        self.lift_seen = 0
        self.heads: list[int] = []
        self.walking: list[int] = []

    def add(self, fr) -> None:
        # every forklift on the plan counts, not only those close enough for a speed reading: against
        # the labels, "moving" is right 81 % of the time this way, and the share moving comes out at
        # 62 % against 57 % true; the close ones alone cover a quarter of the forklift-time
        lifts = [o for o in fr.objects if o.cls == "forklift"]
        self.lift_seen += len(lifts)
        self.lift_moving += sum(o.speed > C.VEHICLE_MOVING_MS for o in lifts)
        people = [o for o in fr.objects if o.cls == "person"]
        self.heads.append(len(people))
        self.walking.append(sum(o.walking for o in people))

    @property
    def utilisation(self) -> float | None:
        """Share of the forklift-time on the plan so far that was spent moving."""
        return self.lift_moving / self.lift_seen if self.lift_seen else None


def ppe_now(live: dict, gids) -> tuple[int, int, int, int]:
    """(people judged, with helmet, with vest, with both) among `gids`."""
    known = [live[g] for g in gids if g in live]
    return (len(known), sum(1 for h, _ in known if h), sum(1 for _, v in known if v),
            sum(1 for h, v in known if h and v))
