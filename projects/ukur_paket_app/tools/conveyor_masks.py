"""Tap- and box-prompted segmentation on the conveyor test scene (after conveyor_scene.py).

    python tools/conveyor_masks.py <mobile_sam.pt>

For every tapped parcel, MobileSAM (Apache 2.0, the on-device candidate) is prompted twice: with the
tap point (the courier touches the parcel) and with a box (the courier drags a box, snipping-tool
style; here the PoC's detection box stands in for it). The depth points inside each mask go to
app/src/test/resources/conveyor/mask_{point,box}_<tid>.f32 for the app's measuring core, and a
preview with all masks is written to build/conveyor/masks.jpg.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import SAM

HERE = Path(__file__).resolve().parents[1]
RES = HERE / "app" / "src" / "test" / "resources" / "conveyor"
POC = HERE.parent / "03_parcel_dimensioning"
COLORS = [(66, 135, 245), (34, 197, 94), (245, 158, 11), (236, 72, 153), (139, 92, 246), (20, 184, 166), (239, 68, 68)]


def main(weights: str):
    scene = json.loads((RES / "scene.json").read_text())
    summ = json.loads((POC / "output" / "summary.json").read_text())["dimensioning"]
    depth = np.load(POC / "output" / ".depth_cache" / "03_packages_conveyor" / f"f{scene['frame']:05d}_896.npy").astype(np.float32)
    depth *= summ["size_scale"]
    H, W = depth.shape
    fx, fy, cx, cy = scene["K_full"]
    sx, sy = W / 1920, H / 1080
    fx, fy, cx, cy = fx * sx, fy * sy, cx * sx, cy * sy
    img = cv2.imread(str(RES / "frame.jpg"))
    sam = SAM(weights)
    prev = {"point": img.copy(), "box": img.copy()}
    stats = []
    for k, t in enumerate(scene["taps"]):
        for kind in ("point", "box"):
            r = sam(img, points=[t["tap_px"]], labels=[1], verbose=False) if kind == "point" else \
                sam(img, bboxes=[t["box_px"]], verbose=False)
            m = r[0].masks.data[0].cpu().numpy().astype(np.uint8)
            m = cv2.resize(m, (1920, 1080), interpolation=cv2.INTER_NEAREST) if m.shape != (1080, 1920) else m
            # depth maps smear across object edges: keep the mask's inside only
            core = cv2.erode(m, np.ones((9, 9), np.uint8))
            md = cv2.resize(core, (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
            v, u = np.nonzero(md)
            z = depth[v, u]
            pts = np.stack([(u - cx) / fx * z, (v - cy) / fy * z, z], -1)
            pts.astype("<f4").tofile(RES / f"mask_{kind}_{t['tid']}.f32")
            c = COLORS[k % len(COLORS)]
            layer = prev[kind]
            layer[m > 0] = (0.55 * layer[m > 0] + 0.45 * np.array(c)).astype(np.uint8)
            cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(layer, cs, -1, c, 3)
            if kind == "point":
                cv2.circle(layer, tuple(int(x) for x in t["tap_px"]), 9, (255, 255, 255), -1)
                cv2.circle(layer, tuple(int(x) for x in t["tap_px"]), 9, c, 3)
            else:
                x0, y0, x1, y1 = (int(x) for x in t["box_px"])
                cv2.rectangle(layer, (x0, y0), (x1, y1), (255, 255, 255), 2)
            stats.append((t["tid"], kind, int(m.sum()), len(pts)))
    out = HERE / "app" / "build" / "conveyor"
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / "masks_point.jpg"), prev["point"], [cv2.IMWRITE_JPEG_QUALITY, 90])
    cv2.imwrite(str(out / "masks_box.jpg"), prev["box"], [cv2.IMWRITE_JPEG_QUALITY, 90])
    for s in stats:
        print("#%-3d %-5s mask %7d px  %5d depth points" % s)


if __name__ == "__main__":
    main(sys.argv[1])
