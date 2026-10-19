"""Check the exported ONNX MobileSAM against the PyTorch one on the conveyor frame (mask IoU per tap/box),
and write the ONNX masks as references for the app's own Segmenter (SegmenterTest compares against them).

    python tools/check_sam_onnx.py <mobile_sam.pt>
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from ultralytics import SAM

HERE = Path(__file__).resolve().parents[1]
RES = HERE / "app" / "src" / "test" / "resources" / "conveyor"
SAMDIR = HERE / "app" / "src" / "main" / "assets" / "sam"
MEAN = np.array([123.675, 116.28, 103.53], np.float32); STD = np.array([58.395, 57.12, 57.375], np.float32)


def prep(rgb):
    h, w = rgb.shape[:2]; s = 1024 / max(h, w)
    nh, nw = int(h * s + 0.5), int(w * s + 0.5)
    x = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    x = (x - MEAN) / STD
    pad = np.zeros((1024, 1024, 3), np.float32); pad[:nh, :nw] = x
    return pad.transpose(2, 0, 1)[None], s, (nh, nw)


def decode(dec, emb, coords, labels, s, nhw, hw, pick):
    m, sc = dec.run(None, {"embeddings": emb, "coords": (np.array(coords, np.float32) * s)[None], "labels": np.array(labels, np.float32)[None]})
    m, sc = m[0], sc[0]
    i = pick(m, sc)
    up = cv2.resize(m[i], (1024, 1024), interpolation=cv2.INTER_LINEAR)[:nhw[0], :nhw[1]]
    return cv2.resize(up, (hw[1], hw[0]), interpolation=cv2.INTER_LINEAR) > 0, sc


def main(weights):
    scene = json.loads((RES / "scene.json").read_text())
    bgr = cv2.imread(str(RES / "frame.jpg")); rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    enc = ort.InferenceSession(str(SAMDIR / "encoder.onnx")); dec = ort.InferenceSession(str(SAMDIR / "decoder.onnx"))
    x, s, nhw = prep(rgb)
    emb = enc.run(None, {"image": x})[0]
    ref = SAM(weights)
    best = lambda m, sc: int(np.argmax(sc))          # the app's rule, for a tap and for a box alike
    for t in scene["taps"]:
        r_box = ref(bgr, bboxes=[t["box_px"]], verbose=False)[0].masks.data[0].cpu().numpy() > 0
        x0, y0, x1, y1 = t["box_px"]
        mb, _ = decode(dec, emb, [[x0, y0], [x1, y1]], [2, 3], s, nhw, rgb.shape[:2], best)
        mp, scp = decode(dec, emb, [t["tap_px"], [0, 0]], [1, -1], s, nhw, rgb.shape[:2], best)
        for kind, m in (("tap", mp), ("box", mb)):
            cv2.imwrite(str(RES / f"sam_{kind}_{t['tid']}.png"), m.astype(np.uint8) * 255)
        iou = lambda a, b: (a & b).sum() / max(1, (a | b).sum())
        print(f"#{t['tid']:<3} box IoU vs PyTorch {iou(mb, r_box):.3f}   tap vs box {iou(mp, mb):.3f}   scores {np.round(scp, 3)}")


if __name__ == "__main__":
    main(sys.argv[1])
