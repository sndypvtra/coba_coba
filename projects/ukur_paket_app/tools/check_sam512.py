"""MobileSAM 512 against the 1024 model the app shipped: mask IoU on the same box prompts, and encoder time.

    python tools/check_sam512.py <dir with encoder512.onnx/decoder512.onnx> <frames dir (jpg)> [box x0,y0,x1,y1 on frame 1]

The 1024 model's mask on each frame gives the next frame's box (it follows the object), and is the reference.
Also runs the 7 parcels (taps and boxes) of the conveyor test frame against the committed references.
"""
import glob
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

HERE = Path(__file__).resolve().parents[1]
MEAN = np.array([123.675, 116.28, 103.53], np.float32); STD = np.array([58.395, 57.12, 57.375], np.float32)


class Sam:
    def __init__(self, enc, dec, size, threads=4):
        o = ort.SessionOptions(); o.intra_op_num_threads = threads
        self.enc = ort.InferenceSession(str(enc), o); self.dec = ort.InferenceSession(str(dec), o); self.size = size

    def embed(self, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB); h, w = rgb.shape[:2]; s = self.size / max(h, w)
        nh, nw = int(h * s + .5), int(w * s + .5)
        x = (cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA).astype(np.float32) - MEAN) / STD
        pad = np.zeros((self.size, self.size, 3), np.float32); pad[:nh, :nw] = x
        t = time.time(); e = self.enc.run(None, {"image": pad.transpose(2, 0, 1)[None]})[0]
        return e, s, (nh, nw), (h, w), time.time() - t

    def masks(self, emb, coords, labels):
        """All three candidate masks (whole, part, sub-part) with their scores."""
        e, s, nhw, hw, _ = emb
        m, sc = self.dec.run(None, {"embeddings": e, "coords": (np.array(coords, np.float32) * s)[None], "labels": np.array(labels, np.float32)[None]})
        out = []
        for i in range(m.shape[1]):
            up = cv2.resize(m[0][i], (self.size, self.size))[:nhw[0], :nhw[1]]
            out.append(cv2.resize(up, (hw[1], hw[0])) > 0)
        return out, sc[0]

    def mask(self, emb, coords, labels):
        e, s, nhw, hw, _ = emb
        m, sc = self.dec.run(None, {"embeddings": e, "coords": (np.array(coords, np.float32) * s)[None], "labels": np.array(labels, np.float32)[None]})
        i = int(np.argmax(sc[0])); low = m.shape[-1]
        up = cv2.resize(m[0][i], (self.size, self.size))[:nhw[0], :nhw[1]]
        return cv2.resize(up, (hw[1], hw[0])) > 0


def iou(a, b): return float((a & b).sum() / max(1, (a | b).sum()))


def main(d512, frames, box):
    big = Sam(HERE / "app/src/main/assets/sam/encoder.onnx", HERE / "app/src/main/assets/sam/decoder.onnx", 1024)
    small = Sam(Path(d512) / "encoder512.onnx", Path(d512) / "decoder512.onnx", 512)
    fs = sorted(glob.glob(frames + "/*.jpg"))[:73:6]
    b = box; out = []; tb = []; ts = []
    for f in fs:
        img = cv2.imread(f)
        eb = big.embed(img); es = small.embed(img); tb.append(eb[-1]); ts.append(es[-1])
        mb = big.mask(eb, [[b[0], b[1]], [b[2], b[3]]], [2, 3]); ms = small.mask(es, [[b[0], b[1]], [b[2], b[3]]], [2, 3])
        out.append(round(iou(mb, ms), 3))
        ys, xs = np.nonzero(mb); mx, my = 0.1 * np.ptp(xs), 0.1 * np.ptp(ys)
        b = [xs.min() - mx, ys.min() - my, xs.max() + mx, ys.max() + my]
    # conveyor frame: 7 parcels, tap and box each
    scene = json.loads((HERE / "app/src/test/resources/conveyor/scene.json").read_text())
    img = cv2.imread(str(HERE / "app/src/test/resources/conveyor/frame.jpg")); es = small.embed(img); conv = []
    for t in scene["taps"]:
        x0, y0, x1, y1 = t["box_px"]
        for kind, (c, l) in (("box", ([[x0, y0], [x1, y1]], [2, 3])), ("tap", ([t["tap_px"], [0, 0]], [1, -1]))):
            ref = cv2.imread(str(HERE / f"app/src/test/resources/conveyor/sam_{kind}_{t['tid']}.png"), cv2.IMREAD_GRAYSCALE) > 127
            conv.append((t["tid"], kind, round(iou(small.mask(es, c, l), ref), 3)))
    print(json.dumps({"video_iou_512_vs_1024": out, "video_iou_median": float(np.median(out)), "video_iou_min": min(out),
                      "conveyor_iou_512_vs_1024": conv, "encoder_s_1024": round(float(np.median(tb)), 3),
                      "encoder_s_512": round(float(np.median(ts)), 3)}, indent=1))


if __name__ == "__main__":
    bx = [float(v) for v in sys.argv[3].split(",")] if len(sys.argv) > 3 else [185, 255, 360, 685]
    main(sys.argv[1], sys.argv[2], bx)
