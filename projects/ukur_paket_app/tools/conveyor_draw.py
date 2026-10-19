"""Draw the conveyor replay: each tapped parcel's box from the app's core, geometry-only vs mask.

    python tools/conveyor_draw.py     # after ./gradlew :app:testDebugUnitTest --tests '*ConveyorReplayTest'
"""
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parents[1]
RES = HERE / "app" / "src" / "test" / "resources" / "conveyor"
B = HERE / "app" / "build" / "conveyor"
COLORS = [(245, 135, 66), (94, 197, 34), (11, 158, 245), (153, 72, 236), (246, 92, 139), (166, 184, 20), (68, 68, 239)]


def draw(results, title):
    scene = json.loads((RES / "scene.json").read_text())
    fx, fy, cx, cy = scene["K_full"]
    img = cv2.imread(str(RES / "frame.jpg"))
    order = {t["tid"]: i for i, t in enumerate(scene["taps"])}
    for r in results:
        if "floor" not in r:
            continue
        c = COLORS[order[r["tid"]] % len(COLORS)]
        P = np.array(r["floor"] + r["top"])
        uv = np.stack([fx * P[:, 0] / P[:, 2] + cx, fy * P[:, 1] / P[:, 2] + cy], 1).astype(int)
        for i in range(4):
            j = (i + 1) % 4
            cv2.line(img, tuple(uv[i]), tuple(uv[j]), c, 2, cv2.LINE_AA)
            cv2.line(img, tuple(uv[i + 4]), tuple(uv[j + 4]), c, 3, cv2.LINE_AA)
            cv2.line(img, tuple(uv[i]), tuple(uv[i + 4]), c, 2, cv2.LINE_AA)
        t = next(x for x in scene["taps"] if x["tid"] == r["tid"])
        cv2.circle(img, tuple(int(v) for v in t["tap_px"]), 8, (255, 255, 255), -1)
        cv2.circle(img, tuple(int(v) for v in t["tap_px"]), 8, c, 3)
        label = f"#{r['tid']} {r['l']:.0f}x{r['w']:.0f}x{r['h']:.0f}"
        x, y = int(uv[4:, 0].min()), int(uv[4:, 1].min()) - 10
        x, y = max(4, min(x, 1920 - 230)), max(30, y)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
        cv2.rectangle(img, (x - 4, y - th - 6), (x + tw + 4, y + 6), c, -1)
        cv2.putText(img, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (1920, 60), (15, 23, 42), -1)
    cv2.putText(img, title, (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    return img


geo = json.loads((B / "result.json").read_text())
mask = [r for r in json.loads((B / "result_mask.json").read_text()) if r["kind"] == "box"]
a = draw(geo, "A. Geometri saja: ketuk paket -> paket yang menempel ikut tergabung (cm)")
b = draw(mask, "B. Ketuk/kotak -> MobileSAM -> depth di dalam masker: tiap paket terpisah (cm)")
out = np.vstack([a[330:900], np.full((12, 1920, 3), 255, np.uint8), b[330:900]])
cv2.imwrite(str(HERE / "docs" / "conveyor_test.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("wrote", HERE / "docs" / "conveyor_test.jpg")
