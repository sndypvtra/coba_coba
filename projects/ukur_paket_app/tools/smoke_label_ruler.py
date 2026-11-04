"""Smoke test: can the resi label (or its barcode) be the ruler on a phone without ARCore (Urovo DT20)?

    python tools/smoke_label_ruler.py            # needs opencv-python-headless, onnxruntime, zxing-cpp, python-barcode

Runs on the two photos already in the test resources, no new data:
  A. paket.jpg: a real parcel (black poly mailer). The courier's box (snipping-tool style) goes to the app's own
     MobileSAM ONNX files -> parcel mask. The label patch -> 4 corners -> homography to a label of known size ->
     the parcel outline in cm. The label in this photo is blurred for privacy, so its outline is only approximate,
     and the real parcel size is not known: this checks that the steps run and how far they can go, not accuracy.
  B. label/anteraja_barcode.png: the straightened barcode crop. Decoded, then the bars are fitted against the
     Code 128 module patterns of the same text to see whether a module width can be read (barcode as ruler).
Writes docs/smoke_label_ruler.jpg and prints the numbers.
"""
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import zxingcpp
from barcode.charsets import code128 as C128

HERE = Path(__file__).resolve().parents[1]
RES = HERE / "app" / "src" / "test" / "resources"
SAM = HERE / "app" / "src" / "main" / "assets" / "sam"
OUT = HERE / "docs" / "smoke_label_ruler.jpg"
MEAN = np.array([123.675, 116.28, 103.53], np.float32)
STD = np.array([58.395, 57.12, 57.375], np.float32)
COURIER_BOX = [185, 345, 815, 1560]          # the box a courier would drag around the parcel (x0, y0, x1, y1)
LABEL_SIZES_MM = {"10 x 10 cm": (100, 100), "10 x 15 cm": (100, 150)}


# ---------------------------------------------------------------- A. parcel photo
class Sam:
    def __init__(self, rgb):
        self.h, self.w = rgb.shape[:2]
        self.s = 1024 / max(self.h, self.w)
        self.nh, self.nw = int(self.h * self.s + .5), int(self.w * self.s + .5)
        x = (cv2.resize(rgb, (self.nw, self.nh)).astype(np.float32) - MEAN) / STD
        pad = np.zeros((1024, 1024, 3), np.float32)
        pad[:self.nh, :self.nw] = x
        enc = ort.InferenceSession(str(SAM / "encoder.onnx"))
        self.dec = ort.InferenceSession(str(SAM / "decoder.onnx"))
        self.emb = enc.run(None, {"image": pad.transpose(2, 0, 1)[None]})[0]

    def box(self, b):
        coords = np.array([[b[0], b[1]], [b[2], b[3]]], np.float32) * self.s
        m, sc = self.dec.run(None, {"embeddings": self.emb, "coords": coords[None], "labels": np.array([[2, 3]], np.float32)})
        i = int(np.argmax(sc[0]))                    # the app's rule: best of the three masks
        up = cv2.resize(m[0][i], (1024, 1024))[:self.nh, :self.nw]
        return cv2.resize(up, (self.w, self.h)) > 0, float(sc[0][i])


def label_quad(bgr, parcel):
    """The label is the large bright patch on the parcel: Otsu split inside the parcel, largest blob, 4-corner fit."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    t, _ = cv2.threshold(g[parcel].reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)   # dark plastic vs label
    bright = ((g > t) & parcel).astype(np.uint8)
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, np.ones((25, 25), np.uint8))
    c = max(cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)
    q = cv2.approxPolyN(cv2.convexHull(c), 4).reshape(-1, 2).astype(np.float64)
    s, d = q.sum(1), q[:, 0] - q[:, 1]
    return np.array([q[np.argmin(s)], q[np.argmax(d)], q[np.argmax(s)], q[np.argmin(d)]])     # tl, tr, br, bl


def rect_aspect(quad, wh, f):
    """Width/height of the real rectangle behind an image quad (Zhang & He 2004), principal point at the centre."""
    c0 = np.array([wh[0] / 2, wh[1] / 2])
    h = lambda p: np.array([p[0] - c0[0], p[1] - c0[1], 1.0])
    tl, tr, br, bl = quad
    m1, m2, m3, m4 = h(tl), h(tr), h(bl), h(br)
    k2 = np.dot(np.cross(m1, m4), m3) / np.dot(np.cross(m2, m4), m3)
    k3 = np.dot(np.cross(m1, m4), m2) / np.dot(np.cross(m3, m4), m2)
    n2, n3 = k2 * m2 - m1, k3 * m3 - m1
    ai = np.diag([1 / f, 1 / f, 1.0])
    return float(np.sqrt((ai @ n2) @ (ai @ n2) / ((ai @ n3) @ (ai @ n3))))


def parcel_photo():
    bgr = cv2.imread(str(RES / "paket.jpg"))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = bgr.shape[:2]
    parcel, score = Sam(rgb).box(COURIER_BOX)
    quad = label_quad(bgr, parcel)
    aspects = {f: rect_aspect(quad, (w, h), f) for f in (900, 1200, 1500)}
    contour = max(cv2.findContours(parcel.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)
    sizes = {}
    for name, (lw, lh) in LABEL_SIZES_MM.items():
        # the label's longer image side gets the longer real side
        top, left = np.linalg.norm(quad[1] - quad[0]), np.linalg.norm(quad[3] - quad[0])
        rw, rh = (lh, lw) if top > left and lh > lw else (lw, lh)
        hm = cv2.getPerspectiveTransform(quad.astype(np.float32), np.float32([[0, 0], [rw, 0], [rw, rh], [0, rh]]))
        mm = cv2.perspectiveTransform(contour.astype(np.float32), hm)
        (_, _), (a, b), _ = cv2.minAreaRect(mm)
        sizes[name] = (max(a, b) / 10, min(a, b) / 10, hm)
    return bgr, parcel, score, quad, aspects, sizes


# ---------------------------------------------------------------- B. barcode crop
def barcode_crop():
    img = cv2.imread(str(RES / "label" / "anteraja_barcode.png"), cv2.IMREAD_GRAYSCALE)
    found = zxingcpp.read_barcodes(img, formats=zxingcpp.BarcodeFormat.Code128)
    text = found[0].text
    prof = img[10:-10].astype(np.float32).mean(0)
    p = (prof - prof.mean()) / prof.std()
    thr = (np.percentile(prof, 3) + np.percentile(prof, 97)) / 2
    xs = np.where(prof < thr)[0]
    x0, x1 = xs[0], xs[-1] + 1
    b = lambda s: [ord(ch) - 32 for ch in s]
    cands = {
        "Code B saja": [104] + b(text),
        "B 'TSA-8' + C": [104] + b(text[:5]) + [99] + [int(text[i:i + 2]) for i in range(5, 15, 2)],
        "B 'TSA-' + C + B": [104] + b(text[:4]) + [99] + [int(text[i:i + 2]) for i in range(4, 14, 2)] + [100] + b(text[14:]),
    }
    g = np.arange(-12, 13)
    k = np.exp(-g ** 2 / (2 * 2.5 ** 2)); k /= k.sum()
    X = np.arange(prof.size)
    fits = []
    for name, v in cands.items():
        chk = (v[0] + sum(a * i for i, a in enumerate(v[1:], 1))) % 103
        mods = np.array([c == "1" for c in "".join(C128.CODES[a] for a in v + [chk]) + C128.STOP + "11"])
        n, best = mods.size, (-1.0, 0.0)
        for a in np.linspace(-0.4, 0.4, 33):              # 1D projective map: allows perspective along the bars
            for e0 in np.arange(x0 - 3, x0 + 3.1):
                for e1 in np.arange(x1 - 3, x1 + 3.1):
                    t = (X - e0) / (e1 - e0)
                    u = t * (1 + a) / (1 + a * t)
                    sig = np.where((t >= 0) & (t < 1), np.where(mods[np.clip((u * n).astype(int), 0, n - 1)], -1., 1.), 1.)
                    sig = np.convolve(sig, k, "same"); sig = (sig - sig.mean()) / sig.std()
                    c = float((p * sig).mean())
                    if c > best[0]: best = (c, a)
        fits.append((name, n, best[0], (x1 - x0) / n))
    return text, str(found[0].format), x1 - x0, fits


# ---------------------------------------------------------------- report
def draw(bgr, parcel, quad, sizes):
    vis = bgr.copy()
    vis[parcel] = (0.55 * vis[parcel] + 0.45 * np.array([80, 200, 80])).astype(np.uint8)
    x0, y0, x1, y1 = COURIER_BOX
    cv2.rectangle(vis, (x0, y0), (x1, y1), (255, 255, 255), 3)
    cv2.polylines(vis, [quad.astype(np.int32)], True, (0, 140, 255), 5)
    for p in quad: cv2.circle(vis, tuple(int(v) for v in p), 9, (0, 140, 255), -1)
    # top view in cm, label 10 x 10 cm, 1 px = 1 mm, with a 5 cm grid
    l, w, hm = sizes["10 x 10 cm"]
    h, wd = bgr.shape[:2]
    shift = np.array([[1, 0, 120], [0, 1, 120], [0, 0, 1]], np.float64)
    top = cv2.warpPerspective(bgr, shift @ hm, (480, 520))
    m = cv2.warpPerspective(parcel.astype(np.uint8) * 255, shift @ hm, (480, 520)) > 0
    top[m] = (0.65 * top[m] + 0.35 * np.array([80, 200, 80])).astype(np.uint8)
    for gx in range(0, 480, 50): cv2.line(top, (gx, 0), (gx, 519), (255, 255, 255), 1)
    for gy in range(0, 520, 50): cv2.line(top, (0, gy), (479, gy), (255, 255, 255), 1)
    c = max(cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)
    box = cv2.boxPoints(cv2.minAreaRect(c)).astype(np.int32)
    cv2.polylines(top, [box], True, (40, 40, 230), 3)
    cv2.putText(top, f"{l:.1f} x {w:.1f} cm (label 10x10)", (10, 505), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 230), 2)
    cv2.putText(top, "grid 5 cm", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    top = cv2.resize(top, (int(480 * h / 520), h))
    return np.hstack([vis, top])


def main():
    bgr, parcel, score, quad, aspects, sizes = parcel_photo()
    print("A. paket.jpg")
    print(f"   parcel mask from the courier's box: SAM score {score:.3f}, {int(parcel.sum())} px")
    print("   label corners (tl, tr, br, bl):", np.round(quad).astype(int).tolist())
    print("   label width/height recovered from perspective:", {f"f={f}px": round(a, 3) for f, a in aspects.items()})
    for name, (l, w, _) in sizes.items():
        print(f"   if the label is {name}: parcel outline {l:.1f} x {w:.1f} cm (on the label's plane)")
    print("   height: not measurable from one top-down photo without gravity / a second view")
    text, fmt, span, fits = barcode_crop()
    print(f"B. anteraja_barcode.png: decoded {text} ({fmt}), bars span {span} px")
    for name, n, c, wpx in fits:
        print(f"   {name:18s} {n:3d} modules: fit {c:.3f}, {wpx:.2f} px/module on average")
    OUT.parent.mkdir(exist_ok=True)
    cv2.imwrite(str(OUT), draw(bgr, parcel, quad, sizes), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print("wrote", OUT.relative_to(HERE))


if __name__ == "__main__":
    main()
