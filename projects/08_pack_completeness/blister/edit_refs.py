"""Stage 1: empty the target pockets on each still segment's reference frame.

usage: python3 -I edit_refs.py <work_dir> <lama.pt>
Writes edited_<k>.png, delta_<k>.npy (float32, BGR) and targets.json.
"""
import json
import sys

import cv2
import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))

import geom
import lama
import segmap

WORK, MODEL = sys.argv[1], sys.argv[2]
REFS = (17, 85, 145)
# targets picked on frame 85, one per blister strip (upper, middle, lower)
TARGETS = {"strip_upper": (894, 155), "strip_middle": (809, 612), "strip_lower": (1110, 706)}


def capsule_context(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    green = (hsv[..., 0] > 60) & (hsv[..., 0] < 110) & (hsv[..., 1] > 80)
    white = (hsv[..., 2] > 238) & (hsv[..., 1] < 30)
    m = (green | white).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return cv2.dilate(m, np.ones((11, 11), np.uint8))


def neutralise(out, mask, strength=0.8):
    """Pull leftover green tint inside the pocket towards the ring's chroma."""
    lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB).astype(np.float32)
    ring = cv2.dilate(mask, np.ones((31, 31), np.uint8)) & ~cv2.dilate(mask, np.ones((9, 9), np.uint8))
    ctx = capsule_context(out) == 0
    sel = (ring > 0) & ctx
    if sel.sum() < 50:
        return out
    a0, b0 = np.median(lab[..., 1][sel]), np.median(lab[..., 2][sel])
    w = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), 3) * strength
    lab[..., 1] = lab[..., 1] * (1 - w) + a0 * w
    lab[..., 2] = lab[..., 2] * (1 - w) + b0 * w
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


SHARP = 22.0   # mean |Laplacian| around an in-focus pocket (frame 85, middle strip)


def feather(img, mask):
    """Edge softness that follows the local depth-of-field blur."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lap = np.abs(cv2.Laplacian(g, cv2.CV_32F))
    ring = cv2.dilate(mask, np.ones((41, 41), np.uint8)) & ~mask
    s = float(lap[ring > 0].mean())
    return float(np.clip(2.5 * SHARP / max(s, 1e-3), 2.5, 10.0))


def main():
    refs = {k: cv2.imread(f"{WORK}/ref_{k}.png") for k in REFS}
    Hs = {85: np.eye(3), 17: np.load(f"{WORK}/H_85_17.npy"), 145: np.load(f"{WORK}/H_85_145.npy")}
    info = {}
    for k in REFS:
        img = refs[k]
        Hh, Ww = img.shape[:2]
        edited = img.copy()
        alpha = np.zeros((Hh, Ww), np.float32)
        ctx = capsule_context(img)
        info[k] = {}
        for name, (x, y) in TARGETS.items():
            px, py = segmap.apply(Hs[k], x, y)
            if not (-20 <= px < Ww + 20 and -20 <= py < Hh + 20):
                continue
            try:
                xs, ys = geom.cap_blob(img, px, py, r=40)
            except ValueError:
                continue
            p0, p1, r = geom.stadium_params(xs, ys, body=1.0, tail=0.1, rscale=0.82)
            tm = geom.stadium_mask(p0, p1, r, img.shape)
            cx, cy = int((p0[0] + p1[0]) / 2), int((p0[1] + p1[1]) / 2)
            x0 = int(np.clip(cx - 256, 0, Ww - 512))
            y0 = int(np.clip(cy - 256, 0, Hh - 512))
            mk = np.maximum(ctx, tm)[y0:y0 + 512, x0:x0 + 512]
            out = lama.inpaint(MODEL, edited[y0:y0 + 512, x0:x0 + 512], mk)
            full = edited.copy()
            full[y0:y0 + 512, x0:x0 + 512] = out
            full = neutralise(full, tm, strength=0.6)
            sigma = feather(img, tm)
            a = cv2.GaussianBlur(cv2.dilate(tm, np.ones((5, 5), np.uint8)).astype(np.float32) / 255.0, (0, 0), sigma)
            edited = (full * a[..., None] + edited * (1 - a[..., None])).astype(np.uint8)
            alpha = np.maximum(alpha, a)
            ys2, xs2 = np.nonzero(tm)
            info[k][name] = {"p0": [float(v) for v in p0], "p1": [float(v) for v in p1], "r": float(r),
                             "box": [int(xs2.min()), int(ys2.min()), int(xs2.max()), int(ys2.max())]}
            info[k][name]["feather"] = sigma
            print(k, name, info[k][name]["box"], round(sigma, 1), flush=True)
        cv2.imwrite(f"{WORK}/edited_{k}.png", edited)
        np.save(f"{WORK}/delta_{k}.npy", edited.astype(np.float32) - img.astype(np.float32))
        np.save(f"{WORK}/alpha_{k}.npy", alpha)
    json.dump(info, open(f"{WORK}/targets.json", "w"), indent=1)


if __name__ == "__main__":
    main()
