#!/usr/bin/env python3
"""#20 - The 30 seconds of video 1 as a 3D scene you can walk around in.

Builds one self-contained web page from what main.py stored: every analysed
frame (output/warehouse_000/video1_frames.json), the events, the cameras'
calibration and the floor plan. The page plays the floor back in 3D - people as
upright figures, forklifts and pallet trucks as boxes turned the way they move,
near misses as red lines - with every CCTV hanging where its calibration puts
it. "Dari CCTV ..." puts the 3D eye exactly at a camera, looking where it
looks with its field of view: the figures should stand where the people stand
in that camera's video, which is the plan-to-camera check made visible.

    python replay_3d.py                  # output/warehouse_000/replay_3d.html

The page loads three.js from a CDN, so it needs internet the first time it is
opened; everything else (data, floor image) is inside the file.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C  # noqa: E402
import draw as dr  # noqa: E402
from config import output_dir  # noqa: E402
from render import PLACE_SCALE  # noqa: E402
from scene import Camera, building_mask, dataset_plan, load_cameras  # noqa: E402

HERE = Path(__file__).resolve().parent
SCENE = "warehouse_000"
ZONE_COLOUR = {"vehicle_lane": "#f97316", "one_way": "#f472b6", "area": "#94a3b8"}
NAME = {"near_miss": "nyaris tertabrak", "speeding": "ngebut", "idle": "diam lama", "lane": "jalur forklift",
        "wrong_way": "salah arah", "crowd": "kerumunan", "crossing": "melintas"}


def _hex(bgr) -> str:
    b, g, r = bgr
    return f"#{r:02x}{g:02x}{b:02x}"


def corner_rays(cam: Camera, reach_m: float = 22.0) -> list[list[float]]:
    """Where the rays through the picture's four corners end: on the floor, or `reach_m` out."""
    out = []
    Kinv = np.linalg.inv(cam.K)
    for u, v in ((0, 0), (cam.width, 0), (cam.width, cam.height), (0, cam.height)):
        d = cam.R.T @ (Kinv @ np.array([u, v, 1.0]))
        d /= np.linalg.norm(d)
        s = reach_m
        if d[2] < -1e-6:
            s = min(s, -cam.centre[2] / d[2])
        p = cam.centre + s * d
        out.append([round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2)])
    return out


def placement_area(cam: Camera, plan, inside: np.ndarray) -> list[list[list[float]]]:
    """The floor this camera places people on (as in the videos), cut to the building, in metres."""
    fp = cam.footprint(PLACE_SCALE, radius_m=80.0, step_m=0.25)
    if len(fp) < 3:
        return []
    m = np.zeros(inside.shape, np.uint8)
    u, v = plan.to_px(fp[:, 0], fp[:, 1])
    cv2.fillPoly(m, [np.stack([u, v], 1).round().astype(np.int32)], 1)
    m &= inside.astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for c in cs:
        if cv2.contourArea(c) < 30:
            continue
        c = cv2.approxPolyDP(c, 1.5, True)[:, 0, :].astype(float)
        x, y = plan.to_world(c[:, 0], c[:, 1])
        polys.append([[round(float(a), 2), round(float(b), 2)] for a, b in zip(x, y)])
    return polys


def events(summary: dict) -> list[dict]:
    ev = []
    for e in summary["#11_near_miss"]["events"]:
        ev.append({"type": "near_miss", "t": e.get("t", e["start_t"]), "who": f"P{e['person']} · F{e['forklift']}",
                   "text": f"{e['min_m']:.1f} m dari forklift".replace(".", ",")})
    for e in summary["#10_speeding"]["events"]:
        ev.append({"type": "speeding", "t": e["start_t"], "who": f"F{e['gid']}",
                   "text": f"{e['max_kmh']:.1f} km/j".replace(".", ",")})
    for e in summary["#8_idle"]["events"]:
        ev.append({"type": "idle", "t": e["start_t"] + C.IDLE_S, "who": f"P{e['gid']}",
                   "text": f"diam {C.IDLE_S:.0f} s di satu titik"})
    for e in summary["#13_wrong_way"]["events"]:
        ev.append({"type": "wrong_way", "t": e["t"], "who": f"P{e['gid']}", "text": "di lorong satu arah"})
    for e in summary["#12_vehicle_lane"].get("events", []):
        ev.append({"type": "lane", "t": e["t"], "who": f"P{e['gid']}", "text": "masuk jalur forklift"})
    for e in summary["#7_congestion"].get("events", []):
        ev.append({"type": "crowd", "t": e["start_t"], "who": f"{e['people_max']} orang",
                   "text": f"dalam radius {C.CROWD_RADIUS_M:g} m".replace(".", ",")})
    for e in summary["#3_crossings"]:
        ev.append({"type": "crossing", "t": e["t"], "who": f"P{e['gid']}",
                   "text": f"{e['line'].split(' ·')[0]} {'masuk' if e['dir'] == 'in' else 'keluar'}"})
    return sorted(ev, key=lambda e: e["t"])


def build(out_path: Path, fragment: bool = False) -> Path:
    frames = json.loads((output_dir(SCENE) / "video1_frames.json").read_text())
    v1 = json.loads((output_dir(SCENE) / "video1_live_ops.json").read_text())
    sel = json.loads((output_dir(SCENE) / "selection.json").read_text())
    shown = sel["video1_live_ops"]["shown"]
    cams = load_cameras(SCENE)
    plan = dataset_plan(SCENE)
    inside = building_mask(plan)

    # the floor image: the building, cropped, at most 2048 px across
    ys, xs = np.nonzero(inside)
    pad = 6
    r0, r1 = max(0, ys.min() - pad), min(inside.shape[0], ys.max() + pad)
    c0, c1 = max(0, xs.min() - pad), min(inside.shape[1], xs.max() + pad)
    img = plan.image[r0:r1, c0:c1]
    s = min(1.0, 2048 / max(img.shape[:2]))
    if s < 1:
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 84])
    xa, ya = plan.to_world(c0 - 0.5, r0 - 0.5)
    xb, yb = plan.to_world(c1 - 0.5, r1 - 0.5)

    cam_rows = []
    for cid in frames["cams"]:
        c = cams[cid]
        k = shown.index(cid) if cid in shown else -1
        cam_rows.append({
            "id": cid, "name": cid.replace("Camera_", "CCTV "),
            "colour": _hex(dr.CAMERA_COLOURS[k]) if k >= 0 else None,
            "centre": [round(float(v), 3) for v in c.centre], "axis": [round(float(v), 4) for v in c.axis],
            "down": [round(float(v), 4) for v in c.R[1]],
            "vfov": round(math.degrees(2 * math.atan(c.height / (2 * c.K[1, 1]))), 2),
            "aspect": round(c.width / c.height, 4),
            "tilt": round(c.tilt_deg, 1), "corners": corner_rays(c), "floor": placement_area(c, plan, inside)})
    # shown cameras last, so their colours draw over the grey ones
    cam_rows.sort(key=lambda r: r["colour"] is not None)
    site = C.SITE[SCENE]
    data = {
        "source": f"NVIDIA PhysicalAI-SmartSpaces 2026 · Warehouse_000 (simulasi) · detik "
                  f"{v1['window']['start_s']:.0f}–{v1['window']['end_s']:.0f} · {len(frames['cams'])} CCTV",
        "note": "Posisi di sini adalah hasil pipeline AI dari video CCTV, bukan label dataset. Orang digambar sebagai "
                "sosok setinggi 1,7 m, forklift dan pallet truck sebagai kotak berukuran tipikal yang menghadap arah "
                "geraknya. Rak tidak dimodelkan dalam 3D: lantainya adalah denah dataset. Bidang berwarna = lantai "
                "tempat CCTV itu menaruh orang (≤ 0,25 m per piksel), sama seperti di video.",
        "fps": frames["fps"], "classes": frames["classes"], "alerts": frames["alerts"],
        "floor": {"bounds": [round(float(xa), 3), round(float(yb), 3), round(float(xb), 3), round(float(ya), 3)],
                  "image": "data:image/jpeg;base64," + base64.b64encode(jpg.tobytes()).decode()},
        "cameras": cam_rows,
        "zones": [{"name": z.name, "kind": z.kind, "colour": ZONE_COLOUR.get(z.kind, "#94a3b8"),
                   "polygon": [list(p) for p in z.polygon]} for z in site["zones"]],
        "lines": [{"name": ln.name.split(" ·")[0], "a": list(ln.a), "b": list(ln.b)} for ln in site["lines"]],
        "frames": frames["frames"],
        "events": events(v1["analytics"]),
    }
    page = (HERE / "replay_template.html").read_text()
    page = page.replace("__DATA__", json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
    if not fragment:
        page = ('<!doctype html>\n<html lang="id">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
                + page + "\n</body>\n</html>\n")
    out_path.write_text(page)
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=output_dir(SCENE) / "replay_3d.html")
    ap.add_argument("--fragment", action="store_true", help="page body only, for hosts that add their own <head>")
    args = ap.parse_args()
    p = build(args.out, args.fragment)
    print(f"{p}  ({p.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
