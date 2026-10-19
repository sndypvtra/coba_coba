"""Turn one frame of the parcel-belt PoC (projects/03_parcel_dimensioning) into a test scene for the
app's measuring core: 3D points, the belt plane, and one "tap" per parcel.

    python tools/conveyor_scene.py [frame]      # default 471 (1-based, has a cached depth map)

Writes app/src/test/resources/conveyor/: points.f32 (x,y,z float32, metres, camera frame: x right,
y down, z forward), scene.json (plane, taps, the PoC's sizes for the same parcels), frame.jpg.
Depth: the PoC's cached Depth Anything 3 metric map, times the PoC's calibration (one printed carton).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parents[1]
POC = HERE.parent / "03_parcel_dimensioning"
OUT = HERE / "app" / "src" / "test" / "resources" / "conveyor"


def main(frame: int = 471):
    summ = json.loads((POC / "output" / "summary.json").read_text())["dimensioning"]
    rec = json.loads((POC / "output" / "record.json").read_text())["frames"]
    row = next(f for f in rec if f["frame"] == frame)
    depth = np.load(POC / "output" / ".depth_cache" / "03_packages_conveyor" / f"f{frame:05d}_896.npy").astype(np.float32)
    depth *= summ["size_scale"]
    H, W = depth.shape
    K = summ["intrinsics"]
    sx, sy = W / 1920, H / 1080
    fx, fy, cx, cy = K["fx"] * sx, K["fy"] * sy, K["cx"] * sx, K["cy"] * sy

    v, u = np.mgrid[0:H, 0:W]
    pts = np.stack([(u - cx) / fx * depth, (v - cy) / fy * depth, depth], -1)

    # belt plane from the PoC's bare-belt patches (full-res pixel windows)
    patches = [(150, 380, 705, 745), (880, 1120, 690, 725), (1180, 1450, 678, 715), (1500, 1850, 660, 695)]
    P = np.concatenate([pts[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)].reshape(-1, 3) for x0, x1, y0, y1 in patches])
    for _ in range(4):
        c = P.mean(0)
        n = np.linalg.svd(P - c)[2][2]
        d = np.abs((P - c) @ n)
        P = P[d < max(np.percentile(d, 90), 0.004)]
    up = n if n[1] < 0 else -n
    rms = float(np.sqrt((((P - c) @ up) ** 2).mean()))

    # keep what an ARCore phone would roughly see: 1 point every 2 px, within 3,5 m
    sel = pts[::2, ::2].reshape(-1, 3)
    sel = sel[(sel[:, 2] > 0.3) & (sel[:, 2] < 3.5)]
    OUT.mkdir(parents=True, exist_ok=True)
    sel.astype("<f4").tofile(OUT / "points.f32")

    taps = []
    for o in row["objects"]:
        x0, y0, x1, y1 = o["box"]
        tu, tv = (x0 + x1) / 2, y0 + (y1 - y0) * 0.35          # a tap on the upper middle of the parcel
        dz = float(depth[int(tv * sy), int(tu * sx)])
        seed = [(tu * sx - cx) / fx * dz, (tv * sy - cy) / fy * dz, dz]
        poc = row["sizes"].get(str(o["tid"]))
        taps.append({"tid": o["tid"], "tap_px": [round(tu, 1), round(tv, 1)], "box_px": o["box"], "seed": seed,
                     "poc_mm": [poc["l_mm"], poc["w_mm"], poc["h_mm"]] if poc else None})

    cap = cv2.VideoCapture(str(POC / "input" / "03_packages_conveyor.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame - 1)
    ok, img = cap.read()
    cv2.imwrite(str(OUT / "frame.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    scene = {"frame": frame, "plane_origin": c.tolist(), "plane_up": up.tolist(), "plane_rms_mm": round(rms * 1000, 1),
             "K_full": [K["fx"], K["fy"], K["cx"], K["cy"]], "points": int(len(sel)), "taps": taps,
             "reference": "parcel #28 is the printed 720 x 500 x 340 mm carton the PoC calibrated on"}
    (OUT / "scene.json").write_text(json.dumps(scene, indent=1))
    print(f"{len(sel)} points, plane rms {rms * 1000:.1f} mm, {len(taps)} taps, camera {abs(c @ up) * 1000:.0f} mm above the belt")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 471)
