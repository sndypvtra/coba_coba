#!/usr/bin/env python3
"""Pictures from the PoC for the web-app mockups: camera views, floor plans, snapshots.

Everything here is a real output of the pipeline on the NVIDIA recordings
(CC BY 4.0): the same detections, identities and alerts as the three videos.
The mockup pages (build.py) place them inside the product's screens.

    python mockup/assets.py        # ~3 min: video 1, 2 and 3 pipelines, then the pictures
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import config as C  # noqa: E402
import main as Mn  # noqa: E402
import ops  # noqa: E402
import render as R  # noqa: E402
import ui  # noqa: E402
from config import STRIDE, output_dir  # noqa: E402
from scene import Labels, building_mask, dataset_plan, load_cameras, read_frame, video_path  # noqa: E402

IMG = HERE / "img"
WALL0 = 10 * 3600 + 41 * 60 + 56     # the mockups' story: video 1's second 0 is 10:41:56 on Monday morning


def wall(t: float) -> str:
    s = int(WALL0 + t)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


# ------------------------------------------------------------ the three windows
def video1() -> dict:
    scene = "warehouse_000"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    v1 = sel["video1_live_ops"]
    cams = load_cameras(scene)
    frames = list(range(v1["start_frame"], v1["end_frame"], STRIDE))
    run = Mn._floor(scene, cams, sel["candidates"], frames, "hybrid")
    return {"scene": scene, "cams": cams, "used": sel["candidates"], "shown": v1["shown"], "plan": dataset_plan(scene),
            "frames": run["frames"], "result": run["result"], "detections": run["detections"],
            "summary": run["summary"], "video_path": lambda c: video_path(scene, c)}


def video2() -> dict:
    scene = "warehouse_000"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    v2 = sel["video2_one_camera"]
    cams = load_cameras(scene)
    frames = list(range(v2["start_frame"], v2["end_frame"], STRIDE))
    run = Mn._floor(scene, cams, [v2["camera"]], frames, "hybrid")
    apd = Mn._ppe(scene, run["result"], [v2["camera"]], frames, "hybrid")
    Mn._locate(apd["events"], run["frames"], run["result"])
    return {"scene": scene, "cams": cams, "camera": v2["camera"], "frames": run["frames"], "result": run["result"],
            "detections": run["detections"], "summary": run["summary"], "ppe": apd,
            "video_path": lambda c: video_path(scene, c)}


def video3() -> dict:
    scene = "warehouse_027"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    v3 = sel["video3_real"]
    cams = load_cameras(scene)
    used = sorted(cams)
    frames = list(range(v3["start_frame"], v3["end_frame"], STRIDE))
    run = Mn._floor(scene, cams, used, frames, "zero_shot")
    apd = Mn._ppe(scene, run["result"], used, frames, "zero_shot")
    Mn._locate(apd["events"], run["frames"], run["result"])
    return {"scene": scene, "cams": cams, "used": used, "frames": run["frames"], "result": run["result"],
            "detections": run["detections"], "summary": run["summary"], "ppe": apd,
            "video_path": lambda c: video_path(scene, c)}


# ------------------------------------------------------------ pictures
def frame_at(ctx: dict, t: float):
    return min(ctx["frames"], key=lambda f: abs(f.t - t))


def camera_pic(ctx: dict, cid: str, t: float, size=(640, 360), big=False, ppe: dict | None = None) -> np.ndarray:
    """One camera at second t, with the pipeline's boxes, names and floor overlays (no header)."""
    fr = frame_at(ctx, t)
    res = ctx["result"]
    confirmed = res.confirmed_ids()
    k2g, _ = R.key_index(res.blobs.get(fr.frame, []), confirmed)
    site = C.SITE.get(ctx["scene"], {"zones": [], "lines": []})
    ov = R.CameraOverlay(ctx["cams"][cid], size, site["zones"], site["lines"])
    rows, classes = ctx["detections"][cid]
    img = read_frame(ctx["video_path"](cid), fr.frame)
    pic, mk = R.camera_view(img, ov, rows, classes, fr.frame, fr, k2g, confirmed, big=big, ppe=ppe)
    cv = ui.Canvas(pic)
    mk.draw(cv, 0, 0)
    return cv.bgr()


def plan_view(ctx: dict, size=(900, 880)):
    scene, plan, cams = ctx["scene"], ctx["plan"], ctx["cams"]
    inside = building_mask(plan)
    ys, xs = np.nonzero(inside)
    x0, y1 = plan.to_world(xs.min(), ys.min())
    x1, y0 = plan.to_world(xs.max(), ys.max())
    view = R.PlanView(plan, (x0 - 1, y0 - 1, x1 + 1, y1 + 1), *size)
    from videos import _view_mask
    return view, _view_mask(view, plan, inside)


def plan_live(ctx: dict, t: float, size=(900, 880), spotlight: str | None = None) -> np.ndarray:
    """The whole floor at second t: zones, lines, the cameras on screen, everyone, the near miss so far."""
    scene, cams = ctx["scene"], ctx["cams"]
    site = C.SITE[scene]
    view, floor = plan_view(ctx, size)
    shown = list(ctx["shown"])
    others = [c for c in ctx["used"] if c not in shown]
    static = R.plan_static(view, cams, shown, others, site["zones"], site["lines"], floor)
    m = static.copy()
    heat = R.Heat(view)
    trails: dict = {}
    res = ctx["result"]
    confirmed = res.confirmed_ids()
    evs = ops.events(scene, ctx["summary"])
    colours = list(ui.CAMERA[:4])
    for fr in ctx["frames"]:
        if fr.t > t:
            break
        for o in fr.objects:
            if o.cls == "person":
                heat.add(o.x, o.y)
            trails.setdefault(o.gid, __import__("collections").deque(maxlen=30)).append((o.x, o.y))
    heat.blend(m)
    fr = frame_at(ctx, t)
    _, seen = R.key_index(res.blobs.get(fr.frame, []), confirmed)
    if spotlight:
        cnts = cv2.findContours(R.fov_mask(view, cams[spotlight], floor), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        for cnt in cnts:
            ui.dashed(m, np.vstack([cnt[:, 0], cnt[:1, 0]]), ui.RED, 2, 7, 5)
        u, v = view.pt(cams[spotlight].centre[0], cams[spotlight].centre[1])
        cv2.circle(m, (u, v), 6, ui.bgr(ui.RED), -1, cv2.LINE_AA)
        shown = shown[:3] + [spotlight]
        colours = colours[:3] + [ui.RED]
    mk = R.plan_labels(view, cams, shown, site["zones"], site["lines"], fr, scene, None, colours)
    for e in evs:
        if e.kind == "near_miss" and e.t <= t:
            u, v = view.pt(e.x, e.y)
            cv2.circle(m, (u, v), 11, ui.bgr(ui.RED), 2, cv2.LINE_AA)
            mk.chip((u + 14, v), f"{wall(e.t)} · {e.cams[0]}", 10, ui.RED, (10, 14, 19, 220), icon="warning",
                    anchor="lm")
    trails = {g: tr for g, tr in trails.items()}
    R.plan_objects(m, view, fr, seen, shown, {}, mk, colours=colours)
    cv = ui.Canvas(m)
    mk.draw(cv, 0, 0)
    return cv.bgr()


def plan_heat(ctx: dict, size=(900, 880)) -> np.ndarray:
    """Where people were over the whole window, and every near miss: the hot-spot map."""
    scene, cams = ctx["scene"], ctx["cams"]
    site = C.SITE[scene]
    view, floor = plan_view(ctx, size)
    m = R.plan_static(view, cams, [], list(ctx["used"]), site["zones"], site["lines"], floor)
    heat = R.Heat(view, radius_m=1.6)
    for fr in ctx["frames"]:
        for o in fr.objects:
            if o.cls == "person":
                heat.add(o.x, o.y)
    heat.blend(m)
    mk = R.Marks(view.w, view.h, view.taken)
    for k, z in enumerate(site["zones"]):
        xs, ys = [p[0] for p in z.polygon], [p[1] for p in z.polygon]
        u, v = view.pt(min(xs), max(ys))
        mk.chip((u + 2, v + 2), ops.zone_label(z.name), 10, ui.TEXT, (10, 14, 19, 215))
    for e in ops.events(scene, ctx["summary"]):
        if e.kind in ("near_miss", "lane"):
            u, v = view.pt(e.x, e.y)
            col = ui.RED if e.kind == "near_miss" else ui.ORANGE
            cv2.circle(m, (u, v), 9 if e.kind == "near_miss" else 6, ui.bgr(col), 2, cv2.LINE_AA)
    cv = ui.Canvas(m)
    mk.draw(cv, 0, 0)
    return cv.bgr()


def plan_heat_light(ctx: dict, size=(900, 880)) -> np.ndarray:
    """The hot-spot map for the light web app: where people were (one warm hue), near misses ringed."""
    scene = ctx["scene"]
    view, _ = plan_view(ctx, size)
    m = plan_light(ctx, view, size)
    heat = R.Heat(view, radius_m=1.6)
    for fr in ctx["frames"]:
        for o in fr.objects:
            if o.cls == "person":
                heat.add(o.x, o.y)
    h = cv2.GaussianBlur(heat.acc, (0, 0), heat.sigma)
    h = np.clip(h / max(float(np.percentile(h[h > 0], 99.5)), 1e-6), 0, 1)[..., None]
    lo, hi = np.array([143, 180, 246], np.float32), np.array([12, 65, 194], np.float32)   # BGR: light to deep orange
    col = lo + (hi - lo) * h
    a = np.clip((h - 0.05) / 0.6, 0, 1) * 0.8
    m[:] = (m * (1 - a) + col * a).astype(np.uint8)
    site = C.SITE[scene]
    for z in site["zones"]:
        cv2.polylines(m, [view.poly(z.polygon)], True, (139, 116, 100), 1, cv2.LINE_AA)
    for e in ops.events(scene, ctx["summary"]):
        if e.kind in ("near_miss", "lane"):
            u, v = view.pt(e.x, e.y)
            col = (59, 59, 208) if e.kind == "near_miss" else (0, 140, 230)
            cv2.circle(m, (u, v), 10 if e.kind == "near_miss" else 7, col, 2, cv2.LINE_AA)
    return m


def plan_raw(ctx: dict, size=(1000, 980)) -> tuple[np.ndarray, dict]:
    """The floor plan as rendered by the dataset, and where each zone and line falls on it (pixels)."""
    view, _ = plan_view(ctx, size)
    site = C.SITE[ctx["scene"]]
    geo = {"zones": [{"name": ops.zone_label(z.name), "kind": z.kind,
                      "points": [list(view.pt(x, y)) for x, y in z.polygon]} for z in site["zones"]],
           "lines": [{"name": ops.line_label(ln.name), "a": list(view.pt(*ln.a)), "b": list(view.pt(*ln.b))}
                     for ln in site["lines"]],
           "cameras": {c: list(view.pt(ctx["cams"][c].centre[0], ctx["cams"][c].centre[1])) for c in ctx["used"]}}
    return plan_light(ctx, view, size), geo


def plan_light(ctx: dict, view, size) -> np.ndarray:
    """The same crop as the dark map, washed light for the web app: the racks and boxes still read."""
    plan = ctx["plan"]
    inside = building_mask(plan)
    ys, xs = np.nonzero(inside)
    x0, y1 = plan.to_world(xs.min(), ys.min())
    x1, y0 = plan.to_world(xs.max(), ys.max())
    crop = plan.crop(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    crop = crop.resized(min(size[0] / crop.image.shape[1], size[1] / crop.image.shape[0]))
    tone = crop.image.astype(np.float32) * 0.42 + 255 * 0.58
    out = np.full((size[1], size[0], 3), (246, 243, 240), np.uint8)
    oy, ox = (size[1] - tone.shape[0]) // 2, (size[0] - tone.shape[1]) // 2
    out[oy:oy + tone.shape[0], ox:ox + tone.shape[1]] = np.clip(tone, 0, 255).astype(np.uint8)
    from videos import _view_mask
    floor = _view_mask(view, plan, inside)
    out[~floor] = (246, 243, 240)
    edge = cv2.morphologyEx(floor.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    out[edge] = (184, 170, 156)
    return out


def snapshots(ctx: dict, evs: list, size=(480, 270)) -> list:
    out = []
    for e in evs:
        s = ops.snapshot(e, ctx["result"], ctx["detections"], ctx["frames"], ctx["video_path"],
                         list(ctx.get("shown", [])))
        out.append(cv2.resize(s, size, interpolation=cv2.INTER_AREA) if s is not None else None)
    return out


def busiest_labelled(cid: str, labels: Labels, height: int) -> int:
    """The frame where this camera sees the most whole, near people in the labels."""
    b = labels.boxes_in(cid, kind="Person")
    ok = (b[:, 10] < height - 3) & (b[:, 10] - b[:, 8] >= 90) & (b[:, 0] % 30 == 0)
    frames, n = np.unique(b[ok, 0].astype(int), return_counts=True)
    return int(frames[np.argmax(n)]) if len(n) else 900


def calibration_pic(cid: str, frame: int | None, labels: Labels, size=(960, 540)) -> tuple[np.ndarray, float]:
    """Where the calibration puts each labelled person's feet (ring) against their box (cross), joined."""
    cams = load_cameras("warehouse_000")
    cam = cams[cid]
    frame = busiest_labelled(cid, labels, cam.height) if frame is None else frame
    img = read_frame(video_path("warehouse_000", cid), frame)
    b = labels.boxes_in(cid, frames=np.array([frame]), kind="Person")
    s = size[0] / cam.width
    out = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    errs = []
    for r in b:
        x1, y1, x2, y2 = r[7:11]
        if y2 >= cam.height - 3 or (y2 - y1) < 50:
            continue
        foot = cam.to_image(np.array([[r[3], r[4], 0.0]]))[0]
        if not np.isfinite(foot).all():
            continue
        bx, by = (x1 + x2) / 2, y2
        e = float(np.hypot(foot[0] - bx, foot[1] - by))
        errs.append(e)
        col = ui.GREEN if e <= 12 else ui.RED
        p, q = (int(bx * s), int(by * s)), (int(foot[0] * s), int(foot[1] * s))
        cv2.line(out, p, q, ui.bgr(col), 2, cv2.LINE_AA)
        cv2.drawMarker(out, p, ui.bgr(ui.TEXT), cv2.MARKER_CROSS, 12, 2, cv2.LINE_AA)
        cv2.circle(out, q, 7, ui.bgr(col), 2, cv2.LINE_AA)
    return out, float(np.median(errs)) if errs else float("nan")


def thumbs(frame: int = 900, size=(192, 108)) -> None:
    """Every camera of the simulated warehouse as it is, for the camera list."""
    for cid in sorted(load_cameras("warehouse_000")):
        img = read_frame(video_path("warehouse_000", cid), frame)
        cv2.imwrite(str(IMG / f"thumb_{cid[-4:]}.jpg"), cv2.resize(img, size, interpolation=cv2.INTER_AREA),
                    [cv2.IMWRITE_JPEG_QUALITY, 88])


def main() -> int:
    IMG.mkdir(parents=True, exist_ok=True)
    meta: dict = {}
    thumbs()
    c1 = video1()
    # the video wall at second 3: the near miss in CAM 0001 under way
    wall = ["Camera_0001", "Camera_0003", "Camera_0005", "Camera_0011", "Camera_0007", "Camera_0010", "Camera_0015",
            "Camera_0008", "Camera_0000"]
    for cid in wall:
        cv2.imwrite(str(IMG / f"cam_{cid[-4:]}.jpg"), camera_pic(c1, cid, 3.0), [cv2.IMWRITE_JPEG_QUALITY, 90])
    cv2.imwrite(str(IMG / "evidence_0001.jpg"), camera_pic(c1, "Camera_0001", 3.8, (1280, 720), big=True),
                [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(str(IMG / "evidence_0001_before.jpg"), camera_pic(c1, "Camera_0001", 2.0, (1280, 720), big=True),
                [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(str(IMG / "plan_live.png"), plan_live(c1, 3.0, (900, 880), spotlight="Camera_0001"))
    cv2.imwrite(str(IMG / "plan_live_24.png"), plan_live(c1, 24.0, (900, 880)))
    cv2.imwrite(str(IMG / "plan_heat.png"), plan_heat(c1, (900, 880)))
    cv2.imwrite(str(IMG / "plan_heat_light.png"), plan_heat_light(c1, (900, 880)))
    raw, geo = plan_raw(c1, (1000, 980))
    cv2.imwrite(str(IMG / "plan_raw.jpg"), raw, [cv2.IMWRITE_JPEG_QUALITY, 92])
    meta["plan_raw"] = geo
    evs1 = ops.events(c1["scene"], c1["summary"])
    meta["events_v1"] = []
    for k, (e, s) in enumerate(zip(evs1, snapshots(c1, evs1))):
        name = f"snap_v1_{k}.jpg"
        if s is not None:
            cv2.imwrite(str(IMG / name), s, [cv2.IMWRITE_JPEG_QUALITY, 90])
        meta["events_v1"].append({"t": e.t, "kind": e.kind, "severity": e.severity, "title": e.title,
                                  "detail": e.detail, "cams": e.cams, "img": name if s is not None else None})
    del c1
    c2 = video2()
    evs2 = ops.events(c2["scene"], c2["summary"], c2["ppe"]["events"])
    meta["events_v2"] = []
    for k, (e, s) in enumerate(zip(evs2, snapshots(c2, evs2))):
        name = f"snap_v2_{k}.jpg"
        if s is not None:
            cv2.imwrite(str(IMG / name), s, [cv2.IMWRITE_JPEG_QUALITY, 90])
        meta["events_v2"].append({"t": e.t, "kind": e.kind, "severity": e.severity, "title": e.title,
                                  "detail": e.detail, "cams": e.cams, "img": name if s is not None else None})
    live = c2["ppe"]["live"]
    fr = frame_at(c2, 20.0)
    cv2.imwrite(str(IMG / "cam_0003_ppe.jpg"),
                camera_pic(c2, "Camera_0003", 20.0, (1280, 720), big=True, ppe=live.get(fr.frame, {})),
                [cv2.IMWRITE_JPEG_QUALITY, 92])
    del c2
    c3 = video3()
    evs3 = ops.events(c3["scene"], c3["summary"], c3["ppe"]["events"])
    meta["events_v3"] = []
    for k, (e, s) in enumerate(zip(evs3, snapshots(c3, evs3))):
        name = f"snap_v3_{k}.jpg"
        if s is not None:
            cv2.imwrite(str(IMG / name), s, [cv2.IMWRITE_JPEG_QUALITY, 90])
        meta["events_v3"].append({"t": e.t, "kind": e.kind, "severity": e.severity, "title": e.title,
                                  "detail": e.detail, "cams": e.cams, "img": name if s is not None else None})
    live3 = c3["ppe"]["live"]
    for cid in c3["used"]:
        fr = frame_at(c3, 20.0)
        cv2.imwrite(str(IMG / f"real_{cid[-4:]}.jpg"),
                    camera_pic(c3, cid, 20.0, (960, 540), big=True, ppe=live3.get(fr.frame, {})),
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
    del c3
    labels = Labels("warehouse_000", list(load_cameras("warehouse_000")))
    for cid in ("Camera_0003", "Camera_0004"):
        pic, med = calibration_pic(cid, None, labels)
        cv2.imwrite(str(IMG / f"calib_{cid[-4:]}.jpg"), pic, [cv2.IMWRITE_JPEG_QUALITY, 90])
        meta[f"calib_{cid[-4:]}"] = round(med, 1)
    r3d = cv2.imread(str(HERE.parent / "docs" / "replay_3d.jpg"))
    cv2.imwrite(str(IMG / "replay_3d.jpg"), r3d[52:840, 0:1118], [cv2.IMWRITE_JPEG_QUALITY, 90])
    (IMG / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print("assets in", IMG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
