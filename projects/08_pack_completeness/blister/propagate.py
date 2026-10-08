"""Stage 2: carry the emptied pockets through every frame of the clip.

usage: python3 -I propagate.py <work_dir> <src.mp4> <out.mp4>

Still segments get the reference delta added frame by frame, so the clip's own
grain and flicker stay on top of the edit. During the two indexing moves the
delta is warped along the sheet's path and smeared with the same motion blur.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

WORK, SRC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SEG = {17: (0, 34), 85: (44, 126), 145: (135, 153)}          # still frames per reference
MOVES = [(34, 44, 17, 85), (126, 135, 85, 145)]               # last still, first still, refs
SHUTTER = 0.5


def frames():
    cap = cv2.VideoCapture(SRC)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return out
        out.append(f)


def flow_x(fr):
    """Cumulative median horizontal flow, used only to time the moves."""
    cum = [0.0]
    prev = cv2.cvtColor(fr[0], cv2.COLOR_BGR2GRAY)
    for f in fr[1:]:
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        p = cv2.goodFeaturesToTrack(prev, 1500, 0.01, 8)
        q, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p, None, winSize=(31, 31), maxLevel=4)
        d = (q - p)[st[:, 0] == 1].reshape(-1, 2)
        cum.append(cum[-1] + float(np.median(d[:, 0])))
        prev = g
    return np.array(cum)


def norm(H):
    return H / H[2, 2]


def motion_kernel(v, shutter=SHUTTER):
    L = max(1, int(round(np.hypot(*v) * shutter)))
    k = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
    c = L
    ang = np.arctan2(v[1], v[0])
    for t in np.linspace(-L / 2, L / 2, 4 * L + 1):
        x, y = int(round(c + t * np.cos(ang))), int(round(c + t * np.sin(ang)))
        k[y, x] = 1
    return k / k.sum()


def refine(pred, frame, win=48):
    """Residual shift between the predicted (warped, blurred) reference and the real frame."""
    g1 = cv2.cvtColor(pred, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    H, W = g1.shape
    y0, y1, x0, x1 = 250, H - 250, 450, W - 450
    t = g1[y0:y1, x0:x1]
    a = g2[y0 - win:y1 + win, x0 - win:x1 + win]
    r = cv2.matchTemplate(a, t, cv2.TM_CCOEFF_NORMED)
    _, _, _, loc = cv2.minMaxLoc(r)
    return float(loc[0] - win), float(loc[1] - win)


def moved_boxes(tg, Hr, dx, dy, W, H):
    boxes = {}
    for name, v in tg.items():
        x0, y0, x1, y1 = v["box"]
        pts = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])[None]
        q = cv2.perspectiveTransform(pts, Hr)[0] + np.float32([dx, dy])
        bx = [int(max(0, q[:, 0].min())), int(max(0, q[:, 1].min())),
              int(min(W - 1, q[:, 0].max())), int(min(H - 1, q[:, 1].max()))]
        if bx[2] > bx[0] and bx[3] > bx[1]:
            boxes[name] = bx
    return boxes


def main():
    fr = frames()
    n = len(fr)
    H, W = fr[0].shape[:2]
    delta = {k: np.load(f"{WORK}/delta_{k}.npy") for k in SEG}
    H17 = np.load(f"{WORK}/H_85_17.npy")
    H145 = np.load(f"{WORK}/H_85_145.npy")
    # ref-to-ref maps: A=17 -> B=85 and B=85 -> C=145
    to_next = {17: norm(np.linalg.inv(H17)), 85: norm(H145)}
    cum = flow_x(fr)
    refs = {k: fr[k] for k in SEG}
    edited = {k: cv2.imread(f"{WORK}/edited_{k}.png").astype(np.float32) for k in SEG}
    alpha = {k: np.load(f"{WORK}/alpha_{k}.npy") for k in SEG}
    log = []

    targets = json.load(open(f"{WORK}/targets.json"))
    truth = {}
    out = [None] * n
    for k, (a, b) in SEG.items():
        for i in range(a, b + 1):
            truth[i] = {name: v["box"] for name, v in targets[str(k)].items()}
            out[i] = np.clip(fr[i].astype(np.float32) + delta[k], 0, 255).astype(np.uint8)

    centre = np.array([W / 2, H / 2, 1.0])
    for last, first, ra, rb in MOVES:
        Hab = to_next[ra]
        span = cum[first] - cum[last]
        prev_pt = None
        for i in range(last + 1, first):
            f = float(np.clip((cum[i] - cum[last]) / span, 0, 1))
            Hi = norm((1 - f) * np.eye(3) + f * Hab)               # ref A coords -> frame i
            pt = Hi @ centre
            pt = pt[:2] / pt[2]
            v = pt - prev_pt if prev_pt is not None else (pt - centre[:2])
            prev_pt = pt
            src = ra if f < 0.5 else rb
            Hr = Hi if f < 0.5 else norm(Hi @ np.linalg.inv(Hab))
            k = motion_kernel(v)
            pred = cv2.filter2D(cv2.warpPerspective(refs[src], Hr, (W, H)), -1, k)
            dx, dy = refine(pred, fr[i])
            T = np.float32([[1, 0, dx], [0, 1, dy]])
            ed = cv2.filter2D(cv2.warpPerspective(edited[src], Hr, (W, H), borderMode=cv2.BORDER_REPLICATE), -1, k)
            ed = cv2.warpAffine(ed, T, (W, H), borderMode=cv2.BORDER_REPLICATE)
            al = cv2.filter2D(cv2.warpPerspective(alpha[src], Hr, (W, H)), -1, k)
            al = cv2.warpAffine(al, T, (W, H))
            # match the frame's brightness around the patch, then composite
            ring = (al > 0.02) & (al < 0.3)
            if ring.sum() > 100:
                gain = (fr[i][ring].astype(np.float32).mean(0) + 1) / (ed[ring].astype(np.float32).mean(0) + 1)
                ed = ed.astype(np.float32) * gain
            out[i] = np.clip(fr[i].astype(np.float32) * (1 - al[..., None]) + ed * al[..., None], 0, 255).astype(np.uint8)
            log.append({"frame": i, "f": round(f, 3), "refine": [round(dx, 1), round(dy, 1)]})
            truth[i] = moved_boxes(targets[str(src)], Hr, dx, dy, W, H)

    tmp = OUT + ".frames"
    os.makedirs(tmp, exist_ok=True)
    for i, f in enumerate(out):
        cv2.imwrite(f"{tmp}/{i:04d}.png", f)
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-framerate", "25",
                    "-i", f"{tmp}/%04d.png", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                    "-pix_fmt", "yuv420p", OUT], check=True)
    json.dump({"cum_flow_x": cum.tolist(), "moves": log}, open(f"{WORK}/timing.json", "w"), indent=1)
    json.dump({"fps": 25, "size": [W, H], "capsules_per_strip": 10,
               "note": "each box is a blister pocket emptied digitally; one per strip, so that strip holds 9 of 10",
               "frames": [{"frame": i, "empty_pockets": truth.get(i, {})} for i in range(n)]},
              open(f"{WORK}/blister_truth.json", "w"), indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
