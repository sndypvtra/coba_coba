"""Capsule stadium from its green cap blob (fixed capsule axis for this clip)."""
import cv2
import numpy as np

D = np.array([0.996, 0.086])
N = np.array([-D[1], D[0]])


def cap_blob(img, x, y, r=40):
    h = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((h[..., 0] > 70) & (h[..., 0] < 100) & (h[..., 1] > 110) & (h[..., 2] > 60)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    cands = [(np.hypot(cen[i][0] - x, cen[i][1] - y), i) for i in range(1, n) if st[i, 4] > 500]
    d, i = min(cands)
    if d > r:
        raise ValueError((x, y, d))
    ys, xs = np.nonzero(lab == i)
    return xs.astype(float), ys.astype(float)


def stadium_params(xs, ys, body=0.75, tail=0.08, rscale=0.76):
    c = np.array([xs.mean(), ys.mean()])
    t = (xs - c[0]) * D[0] + (ys - c[1]) * D[1]
    s = (xs - c[0]) * N[0] + (ys - c[1]) * N[1]
    L = t.max() - t.min()
    r = rscale * (s.max() - s.min())
    left, right = t.min() - body * L, t.max() + tail * L
    p0 = c + D * (left + r)
    p1 = c + D * (right - r)
    return p0, p1, r


def stadium_mask(p0, p1, r, shape):
    m = np.zeros(shape[:2], np.uint8)
    a, b = tuple(int(round(v)) for v in p0), tuple(int(round(v)) for v in p1)
    cv2.line(m, a, b, 255, int(round(2 * r)))
    cv2.circle(m, a, int(round(r)), 255, -1)
    cv2.circle(m, b, int(round(r)), 255, -1)
    return m
