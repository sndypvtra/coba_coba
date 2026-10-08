"""Homographies between the three still segments of the clip (ref 85 -> 17 / 145)."""
import cv2
import numpy as np


def fit(src, dst, prior, step=90, size=120, win=110):
    s = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    d = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
    H, W = s.shape
    P, Q = [], []
    for y in range(60, H - size - 60, step):
        for x in range(60, W - size - 60, step):
            px, py = x + prior[0], y + prior[1]
            if px - win < 0 or py - win < 0 or px + size + win > W or py + size + win > H:
                continue
            t = s[y:y + size, x:x + size]
            if t.std() < 12:
                continue
            a = d[py - win:py + size + win, px - win:px + size + win]
            r = cv2.matchTemplate(a, t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(r)
            if mx < 0.6:
                continue
            P.append((x + size / 2, y + size / 2))
            Q.append((px - win + loc[0] + size / 2, py - win + loc[1] + size / 2))
    P, Q = np.float32(P), np.float32(Q)
    Hm, inl = cv2.findHomography(P, Q, cv2.RANSAC, 6.0)
    return Hm, int(inl.sum()), len(P)


def apply(Hm, x, y):
    v = Hm @ np.array([x, y, 1.0])
    return v[0] / v[2], v[1] / v[2]
