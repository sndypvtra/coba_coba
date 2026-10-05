#!/usr/bin/env python3
"""Does every camera put things where the floor plan says they are?

What this project promises is that a dot on the plan is where the object
really stands, as seen by the camera whose tile is on screen beside it. That
rests entirely on the calibration, so every camera is tested before any is
chosen, and a camera that fails is neither shown nor used to place anything.

Synthetic scene (labels and a floor plan ship with it):

  1. Labels into pixels. The dataset knows where every person stands. That
     floor point, projected through the camera, must land on the bottom-centre
     of the person's labelled box; the box, projected back, must land on the
     floor point. A camera passes when the systematic part of that error (the
     median offset) is at most 6 px, the scatter around it at most 5 px, and
     the median floor error at most 0.30 m.
  2. Labels onto the plan. Every labelled position must fall inside the
     building on map.png - a mirrored or shifted plan transform would put
     people in the car park.
  3. Camera onto plan, by eye. Each camera's floor is warped onto the plan;
     floor markings and rack bases must fall on the plan's own.

Real scene (no labels, no plan): a one-metre grid is drawn on each camera's
floor. Whether two cameras put the same person in the same place can only be
measured once people are detected: `align_real.py` does that, shifts each
camera to agree with the others, and keeps only the cameras that then agree.

    python geometry_check.py                   # both scenes
    python geometry_check.py --scene warehouse_027
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import draw as dr  # noqa: E402
from config import DOCS, output_dir  # noqa: E402
from scene import (Camera, FloorPlan, Labels, building_mask, dataset_plan,  # noqa: E402
                   input_dir, load_cameras, video_path)

MAX_SCALE = 0.10      # m per pixel: beyond this, one pixel is over 10 cm of floor
SHOW_FRAME = {"warehouse_000": 1800, "warehouse_027": 900}
PASS = {"bias_px": 6.0, "spread_px": 5.0, "floor_m": 0.30}


# ------------------------------------------------------------------ pictures
def background(scene: str, cam: str, n: int = 15) -> np.ndarray:
    """Median of n frames spread over the clip: the floor with nobody on it."""
    cap = cv2.VideoCapture(str(video_path(scene, cam)))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for i in np.linspace(0, total - 1, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, f = cap.read()
        if ok:
            frames.append(f)
    cap.release()
    return np.median(np.stack(frames), axis=0).astype(np.uint8)


def frame_at(scene: str, cam: str, index: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(video_path(scene, cam)))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, f = cap.read()
    cap.release()
    return f


def warp_to_plan(cam: Camera, plan: FloorPlan, img: np.ndarray,
                 max_scale: float = MAX_SCALE) -> tuple[np.ndarray, np.ndarray]:
    """The camera image laid onto the plan through the floor homography."""
    H, W = plan.image.shape[:2]
    uu, vv = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    xs, ys = plan.to_world(uu, vv)
    uv = cam.to_image(np.stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)], 1))
    mapx = np.nan_to_num(uv[:, 0].reshape(H, W), nan=-1).astype(np.float32)
    mapy = np.nan_to_num(uv[:, 1].reshape(H, W), nan=-1).astype(np.float32)
    warped = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR, borderValue=0)
    return warped, cam.sees(xs, ys, max_scale)


def clipped_footprint(cam: Camera, plan: FloorPlan, inside: np.ndarray | None) -> np.ndarray:
    """The camera's useful floor, cut to the building, as plan pixels."""
    fp = cam.footprint(MAX_SCALE)
    if not len(fp):
        return np.zeros((0, 2), np.int32)
    poly = np.stack(plan.to_px(fp[:, 0], fp[:, 1]), 1).astype(np.int32)
    if inside is None:
        return poly
    m = np.zeros(inside.shape, np.uint8)
    cv2.fillPoly(m, [poly], 1)
    m &= inside.astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return max(cs, key=cv2.contourArea)[:, 0, :] if cs else np.zeros((0, 2), np.int32)


# -------------------------------------------------------- synthetic scene checks
def person_errors(cam: Camera, labels: Labels, step: int = 10) -> dict:
    """Label floor point vs label box, in both directions, for one camera.

    Only boxes that hold the whole person count: a box cut by the frame edge, or
    shortened because a rack hides the legs, has no feet at its bottom edge and
    would measure the occlusion rather than the calibration. How often that
    happens is itself worth knowing, so it is reported as `hidden_pct`.
    """
    b = labels.boxes_in(cam.id, kind="Person")
    b = b[b[:, 0] % step == 0]
    x1, y1, x2, y2 = b[:, 7], b[:, 8], b[:, 9], b[:, 10]
    inside = ((y2 - y1) >= 40) & (y1 > 3) & (y2 < cam.height - 3) & (x1 > 3) & (x2 < cam.width - 3)
    b = b[inside]
    if not len(b):
        return {"samples": 0}
    feet = cam.to_image(np.column_stack([b[:, 3], b[:, 4], np.zeros(len(b))]))
    head = cam.to_image(np.column_stack([b[:, 3], b[:, 4], b[:, 6]]))
    whole = (b[:, 10] - b[:, 8]) >= 0.85 * (feet[:, 1] - head[:, 1])
    w, f = b[whole], feet[whole]
    du = f[:, 0] - (w[:, 7] + w[:, 9]) / 2
    dv = f[:, 1] - w[:, 10]
    bu, bv = float(np.median(du)), float(np.median(dv))
    fx, fy = cam.to_floor((w[:, 7] + w[:, 9]) / 2, w[:, 10])
    m = np.hypot(fx - w[:, 3], fy - w[:, 4])
    m = m[np.isfinite(m)]
    return {
        "samples": int(len(b)),
        "whole_person_boxes": int(whole.sum()),
        "hidden_pct": round(100.0 * (1 - whole.mean()), 1),
        "bias_px": round(float(np.hypot(bu, bv)), 1),
        "bias_direction_px": [round(bu, 1), round(bv, 1)],
        "spread_px": round(float(np.median(np.hypot(du - bu, dv - bv))), 1),
        "floor_m_median": round(float(np.median(m)), 3),
        "floor_m_p90": round(float(np.percentile(m, 90)), 3),
    }


def verdict(e: dict) -> tuple[bool, str]:
    if not e.get("samples"):
        return False, "tidak ada orang berlabel yang terlihat utuh"
    fails = []
    if e["bias_px"] > PASS["bias_px"]:
        fails.append(f"bias {e['bias_px']} px")
    if e["spread_px"] > PASS["spread_px"]:
        fails.append(f"sebaran {e['spread_px']} px")
    if e["floor_m_median"] > PASS["floor_m"]:
        fails.append(f"meleset {e['floor_m_median']} m")
    return (not fails), ("lolos" if not fails else "gagal: " + ", ".join(fails))


def camera_panel(cam: Camera, plan: FloorPlan, inside: np.ndarray, frame: np.ndarray,
                 labels: Labels, index: int, colour, metrics: dict) -> np.ndarray:
    """Left: the camera, with each person's labelled floor point projected into it.
    Right: the same moment on the plan, with the camera's floor laid over it."""
    T = dr.Texts()
    left = frame.copy()
    gu, gv = np.meshgrid(np.arange(0, cam.width, 8), np.arange(0, cam.height, 8))
    sc = cam.floor_scale(gu.astype(float), gv.astype(float))
    good = (np.isfinite(sc) & (sc <= MAX_SCALE)).astype(np.uint8)
    good = cv2.resize(good, (cam.width, cam.height), interpolation=cv2.INTER_NEAREST)
    cs, _ = cv2.findContours(good, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(left, cs, -1, colour, 3, cv2.LINE_AA)
    for r in labels.boxes_in(cam.id, frames=np.array([index]), kind="Person"):
        x1, y1, x2, y2 = r[7:11]
        cv2.rectangle(left, (int(x1), int(y1)), (int(x2), int(y2)), dr.MUTED, 1)
        u, v = cam.to_image(np.array([[r[3], r[4], 0.0]]))[0]
        if np.isfinite(u):
            cv2.circle(left, (int(u), int(v)), 9, dr.GOOD, -1, cv2.LINE_AA)
        cv2.drawMarker(left, (int((x1 + x2) / 2), int(y2)), dr.bgr("#ff3bd4"),
                       cv2.MARKER_CROSS, 22, 3)
    left = cv2.resize(left, (640, 360), interpolation=cv2.INTER_AREA)

    fp = cam.footprint(MAX_SCALE)
    x0, y0 = np.minimum(fp.min(0), cam.centre[:2]) - 3
    x1, y1 = np.maximum(fp.max(0), cam.centre[:2]) + 3
    crop = plan.crop(x0, y0, x1, y1)
    k = 360 / crop.image.shape[0]
    crop = crop.resized(k)
    ins = cv2.resize(_crop_mask(plan, inside, x0, y0, x1, y1), (crop.image.shape[1], crop.image.shape[0]),
                     interpolation=cv2.INTER_NEAREST).astype(bool)
    warped, mask = warp_to_plan(cam, crop, frame)
    right = crop.image.copy()
    dr.blend(right, warped, mask & ins, 0.62)
    poly = clipped_footprint(cam, crop, ins)
    if len(poly) > 2:
        cv2.polylines(right, [poly], True, colour, 2, cv2.LINE_AA)
    for r in labels.at(index, "Person"):
        u, v = crop.to_px(r[3], r[4])
        if 0 <= u < right.shape[1] and 0 <= v < right.shape[0]:
            cv2.circle(right, (int(u), int(v)), 4, dr.GOOD, -1, cv2.LINE_AA)
    cu, cv_ = crop.to_px(cam.centre[0], cam.centre[1])
    hx, hy = crop.to_px(cam.centre[0] + 3 * np.cos(cam.heading), cam.centre[1] + 3 * np.sin(cam.heading))
    cv2.arrowedLine(right, (int(cu), int(cv_)), (int(hx), int(hy)), colour, 3, cv2.LINE_AA, tipLength=0.3)
    cv2.circle(right, (int(cu), int(cv_)), 7, colour, -1, cv2.LINE_AA)
    right = right[:, :min(right.shape[1], 700)]

    ok = metrics["passed"]
    head = np.full((34, 640 + right.shape[1] + 10, 3), dr.PANEL, np.uint8)
    e = metrics["labels"]
    T.add(("LOLOS " if ok else "GAGAL ") + cam.id, (10, 7), 18, dr.GOOD if ok else dr.BAD, True)
    T.add(f"tinggi {cam.mount_height_m:.1f} m · menunduk {cam.tilt_deg:.0f}° · bias {e.get('bias_px')} px · "
          f"meleset {e.get('floor_m_median')} m · {e.get('hidden_pct')}% orang tertutup sebagian",
          (215, 9), 16, dr.INK)
    T.flush(head)
    body = np.full((360, head.shape[1], 3), dr.BG, np.uint8)
    body[:, :640] = left
    body[:right.shape[0], 650:650 + right.shape[1]] = right
    return np.vstack([head, body])


def _crop_mask(plan: FloorPlan, mask: np.ndarray, x0, y0, x1, y1) -> np.ndarray:
    us, vs = plan.to_px([x0, x1], [y0, y1])
    c0, c1 = int(max(0, np.floor(min(us)))), int(min(mask.shape[1], np.ceil(max(us))))
    r0, r1 = int(max(0, np.floor(min(vs)))), int(min(mask.shape[0], np.ceil(max(vs))))
    return mask[r0:r1, c0:c1].astype(np.uint8)


def check_synthetic(scene: str) -> dict:
    cams = load_cameras(scene)
    plan = dataset_plan(scene)
    inside = building_mask(plan)
    labels = Labels(scene, list(cams))
    idx = SHOW_FRAME[scene]
    out = output_dir(scene) / "geometry"
    out.mkdir(exist_ok=True)

    # every labelled person, every second, must stand inside the building
    p = labels.objs[(labels.kind == 0) & (labels.frame % 30 == 0)]
    u, v = plan.to_px(p[:, 3], p[:, 4])
    ui, vi = np.clip(u.astype(int), 0, inside.shape[1] - 1), np.clip(v.astype(int), 0, inside.shape[0] - 1)
    on_plan = float(inside[vi, ui].mean() * 100)

    results, panels = {}, []
    overview = plan.image.copy()
    for k, cid in enumerate(sorted(cams)):
        cam = cams[cid]
        colour = dr.CAMERA_COLOURS[k % len(dr.CAMERA_COLOURS)]
        e = person_errors(cam, labels)
        ok, why = verdict(e)
        fp = cam.footprint(MAX_SCALE)
        results[cid] = {
            "passed": ok, "verdict": why,
            "mount_height_m": round(cam.mount_height_m, 2),
            "tilt_deg": round(cam.tilt_deg, 1),
            "hfov_deg": round(cam.hfov_deg, 1),
            "useful_floor_m2": round(float(cv2.contourArea(fp.astype(np.float32))), 1)
            if len(fp) > 2 else 0.0,
            "labels": e,
        }
        if ok:
            warped, mask = warp_to_plan(cam, plan, background(scene, cid))
            dr.blend(overview, warped, mask & inside, 0.55)
        panel = camera_panel(cam, plan, inside, frame_at(scene, cid, idx), labels, idx,
                             colour, results[cid])
        cv2.imwrite(str(out / f"{cid}.jpg"), panel, [cv2.IMWRITE_JPEG_QUALITY, 88])
        panels.append(panel)
        print(f"  {cid}: {why} (bias {e.get('bias_px')} px, {e.get('floor_m_median')} m)", flush=True)

    T = dr.Texts()
    marks = {c: tuple(int(v) for v in plan.to_px(cams[c].centre[0], cams[c].centre[1])) for c in cams}
    taken = [(u - 6, v - 6, u + 6, v + 6) for u, v in marks.values()]
    ys, xs = np.nonzero(inside)
    r0, c0 = max(0, ys.min() - 20), max(0, xs.min() - 20)
    r1, c1 = ys.max() + 20, xs.max() + 20
    for k, cid in enumerate(sorted(cams)):
        cam = cams[cid]
        ok = results[cid]["passed"]
        colour = dr.CAMERA_COLOURS[k % len(dr.CAMERA_COLOURS)] if ok else dr.BAD
        poly = clipped_footprint(cam, plan, inside)
        if len(poly) > 2:
            cv2.polylines(overview, [poly], True, colour, 2 if ok else 1, cv2.LINE_AA)
        cv2.circle(overview, marks[cid], 5, colour, -1, cv2.LINE_AA)
    for k, cid in enumerate(sorted(cams)):
        ok = results[cid]["passed"]
        colour = dr.CAMERA_COLOURS[k % len(dr.CAMERA_COLOURS)] if ok else dr.BAD
        # placed inside the part of the plan that is kept, clear of the other labels
        u, v = marks[cid]
        local = [(a - c0, b - r0, cc - c0, d - r0) for a, b, cc, d in taken]
        dr.place_label(T, cid.replace("Camera_", "") + ("" if ok else " gagal"), (u - c0, v - r0), 13, colour,
                       local, c1 - c0, r1 - r0, 7)
        x0, y0, x1, y1 = local[-1]
        taken.append((x0 + c0, y0 + r0, x1 + c0, y1 + r0))
    overview = overview[r0:r1, c0:c1].copy()
    T.flush(overview)
    cv2.imwrite(str(DOCS / f"geometry_{scene}_plan.jpg"), overview, [cv2.IMWRITE_JPEG_QUALITY, 88])

    sheet_w = max(p.shape[1] for p in panels)
    pad = [cv2.copyMakeBorder(p, 0, 0, 0, sheet_w - p.shape[1], cv2.BORDER_CONSTANT, value=dr.BG)
           for p in panels]
    if len(pad) % 2:
        pad.append(np.full_like(pad[0], dr.BG))
    sheet = np.vstack([np.hstack(pad[i:i + 2]) for i in range(0, len(pad), 2)])
    sheet = cv2.resize(sheet, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(DOCS / f"geometry_{scene}_cameras.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return {"labels_inside_building_pct": round(on_plan, 2), "criteria": PASS, "cameras": results}


# ------------------------------------------------------------- real scene check
def floor_grid(cam: Camera, img: np.ndarray, colour, step_m: float = 1.0) -> np.ndarray:
    """A one-metre grid on the floor, as this camera would see it."""
    out = img.copy()
    fp = cam.footprint(MAX_SCALE)
    if not len(fp):
        return out
    (x0, y0), (x1, y1) = fp.min(0), fp.max(0)
    for horizontal in (False, True):
        a0, a1 = (y0, y1) if horizontal else (x0, x1)
        b0, b1 = (x0, x1) if horizontal else (y0, y1)
        for a in np.arange(np.floor(a0), np.ceil(a1) + step_m, step_m):
            bs = np.arange(b0, b1, 0.05)
            xs, ys = (bs, np.full_like(bs, a)) if horizontal else (np.full_like(bs, a), bs)
            ok = cam.sees(xs, ys, MAX_SCALE)
            uv = cam.to_image(np.stack([xs, ys, np.zeros_like(xs)], 1))
            seg = []
            for good, q in zip(ok, uv):
                if good:
                    seg.append(q)
                    continue
                if len(seg) > 1:
                    cv2.polylines(out, [np.array(seg, np.int32)], False, colour, 2, cv2.LINE_AA)
                seg = []
            if len(seg) > 1:
                cv2.polylines(out, [np.array(seg, np.int32)], False, colour, 2, cv2.LINE_AA)
    return out


def check_real(scene: str) -> dict:
    """The real recording has no labels and no floor plan: a one-metre grid on each camera's floor.

    Whether two cameras put the same person in the same place is measured once
    people are detected (align_real.py); cameras it could not verify are drawn
    in red here. No plan is painted: three cameras looking along the floor from
    under three metres cannot tell floor from rack, and a plan that cannot be
    trusted is worse than none (README).
    """
    raw = load_cameras(scene, aligned=False)
    cams = load_cameras(scene)                 # verified and shifted, once align_real.py has run
    ids = sorted(cams)
    T = dr.Texts()
    tiles = []
    for cid in sorted(raw):
        used = cid in cams
        colour = dr.CAMERA_COLOURS[ids.index(cid) % len(dr.CAMERA_COLOURS)] if used else dr.BAD
        g = floor_grid(cams[cid] if used else raw[cid], frame_at(scene, cid, SHOW_FRAME[scene]), colour)
        g = cv2.resize(g, (640, 360), interpolation=cv2.INTER_AREA)
        T.add(f"{cid} · grid 1 m di lantai" + ("" if used else " · tidak dipakai"), (10, 8), 17,
              dr.INK if used else dr.BAD, True, bg=dr.BG)
        tiles.append(T.flush(g))
    if len(tiles) % 2:
        tiles.append(np.full_like(tiles[0], dr.BG))
    sheet = np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)])
    cv2.imwrite(str(DOCS / f"geometry_{scene}_cameras.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
    err_file = input_dir(scene) / "vggt_reprojection_error.txt"
    return {"cameras": {c: {"mount_height_m": round(raw[c].mount_height_m, 2),
                            "tilt_deg": round(raw[c].tilt_deg, 1),
                            "hfov_deg": round(raw[c].hfov_deg, 1),
                            "used": c in cams} for c in sorted(raw)},
            "vggt_report": err_file.read_text() if err_file.exists() else ""}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", action="append", choices=["warehouse_000", "warehouse_027"])
    args = ap.parse_args()
    DOCS.mkdir(exist_ok=True)
    for scene in args.scene or ["warehouse_000", "warehouse_027"]:
        print(f"== {scene}")
        res = check_synthetic(scene) if scene == "warehouse_000" else check_real(scene)
        path = output_dir(scene) / "geometry.json"
        old = json.loads(path.read_text()) if path.exists() else {}
        old.update(res)
        path.write_text(json.dumps(old, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
