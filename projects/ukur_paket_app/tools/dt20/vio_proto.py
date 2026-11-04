"""Prototype of the on-device engine (the Kotlin port follows it line by line), on a recording folder.

    python tools/dt20/vio_proto.py <recording_dir>

Unlike solve.py (COLMAP, PC only) this is meant for the phone's CPU:
  1. KLT point tracks over the saved frames (640 x 480 grey), forward-backward checked.
  2. Rotations from the motion sensors: game rotation vector (gravity-aligned, z up), else integrated gyroscope.
  3. ONE linear least-squares system, points eliminated (Schur complement):
       vision:  for each observation, the point seen in that frame lies on its viewing ray:
                (R_k[0] - x R_k[2]) . (X - c_k) = 0,  (R_k[1] - y R_k[2]) . (X - c_k) = 0
       inertia: c_b - c_a - v_a dt - g dt^2/2 + Ja b = alpha ;  v_b - v_a - g dt + Jb b = beta
     unknowns: camera centres c_k (c_0 = 0) in metres, velocities, accelerometer bias (gravity known from the rotation
     vector; unknown with the gyroscope). Rows reweighted to pixel errors (IRLS, Huber).
  4. The time offset and focal length that minimise the reprojection error (grid, then fine).
  5. Object tracks: the pick mask at its frame, then any track inside the object's hull in >= 80 % of frames shared.
     Support plane: RANSAC on background points round the object, normal near gravity. Box rule as method A.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

G = 9.81
R_DC = np.diag([1.0, -1.0, -1.0])            # upright camera -> device (portrait phone, back camera)


# ---------------------------------------------------------------- 1. tracks
def tracks(d: Path, rot: int, step=1, max_corners=900, min_dist=8):
    fr = [l.split(",") for l in (d / "frames.csv").read_text().splitlines()[1:] if l.strip()]
    idx = [int(r[0]) for r in fr][::step]
    obs = {}                                  # track id -> list of (frame index, u, v) in upright pixels
    prev = None; pts = None; ids = None; nid = 0
    for k, i in enumerate(idx):
        im = cv2.imread(str(d / "frames" / f"{i:05d}.jpg"), cv2.IMREAD_GRAYSCALE)
        if rot == 90: im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
        h, w = im.shape
        if im.shape[1] > 640: im = cv2.resize(im, (im.shape[1] // 2, im.shape[0] // 2), interpolation=cv2.INTER_AREA)
        if prev is not None and pts is not None and len(pts):
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, im, pts, None, winSize=(15, 15), maxLevel=3)
            back, st2, _ = cv2.calcOpticalFlowPyrLK(im, prev, nxt, None, winSize=(15, 15), maxLevel=3)
            ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm(back - pts, axis=2).ravel() < 0.7)
            ok &= (nxt[:, 0, 0] >= 0) & (nxt[:, 0, 1] >= 0) & (nxt[:, 0, 0] < im.shape[1]) & (nxt[:, 0, 1] < im.shape[0])
            pts = nxt[ok]; ids = ids[ok]
        # top up: new corners away from the live ones
        mask = np.full(im.shape, 255, np.uint8)
        if pts is not None:
            for p in pts[:, 0]: cv2.circle(mask, (int(p[0]), int(p[1])), min_dist + 2, 0, -1)
        want = max_corners - (0 if pts is None else len(pts))
        if want > 50:
            new = cv2.goodFeaturesToTrack(im, want, 0.005, min_dist, mask=mask, blockSize=5)
            if new is not None:
                pts = new.astype(np.float32) if pts is None else np.concatenate([pts, new.astype(np.float32)])
                ids = np.arange(nid, nid + len(new)) if ids is None else np.concatenate([ids, np.arange(nid, nid + len(new))])
                nid += len(new)
        for tid, p in zip(ids, pts[:, 0]): obs.setdefault(int(tid), []).append((k, float(p[0]), float(p[1])))
        prev = im
    scale = im.shape[1] / (h if rot in (90, 270) else w) if False else 1.0
    return idx, obs, im.shape[1], im.shape[0]


# ---------------------------------------------------------------- 2. rotations
def read_imu(d: Path):
    acc, gyr, rv = [], [], []
    for line in (d / "imu.csv").read_text().splitlines()[1:]:
        p = line.split(",")
        if p[0] == "accelerometer": acc.append([float(v) for v in p[1:5]])
        elif p[0] == "gyroscope": gyr.append([float(v) for v in p[1:5]])
        elif p[0] == "game_rotation_vector": rv.append([float(v) for v in p[1:6] if v != ""])
    return np.array(sorted(acc)), np.array(sorted(gyr)), np.array(sorted(rv))


def q2r(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


class Rotations:
    """world <- device at any time t (sensor clock, s)."""
    def __init__(self, gyr, rv):
        if len(rv) > 10:
            self.kind = "rv"; self.t = rv[:, 0] / 1e9
            q = rv[:, 1:5] if rv.shape[1] >= 5 else np.c_[rv[:, 1:4], np.sqrt(np.clip(1 - (rv[:, 1:4] ** 2).sum(1), 0, 1))]
            for i in range(1, len(q)):
                if q[i] @ q[i - 1] < 0: q[i] = -q[i]
            self.q = q
        else:
            self.kind = "gyro"; self.t = gyr[:, 0] / 1e9
            r = [np.eye(3)]
            for i in range(len(gyr) - 1):
                r.append(r[-1] @ cv2.Rodrigues(gyr[i, 1:] * (self.t[i + 1] - self.t[i]))[0])
            self.r = np.array(r)

    def at(self, t):
        i = int(np.clip(np.searchsorted(self.t, t) - 1, 0, len(self.t) - 2))
        a = np.clip((t - self.t[i]) / (self.t[i + 1] - self.t[i]), 0, 1)
        if self.kind == "rv":
            q = self.q[i] * (1 - a) + self.q[i + 1] * a; q /= np.linalg.norm(q)
            return q2r(q)
        dr = self.r[i].T @ self.r[i + 1]
        return self.r[i] @ cv2.Rodrigues(cv2.Rodrigues(dr)[0] * a)[0]


def preintegrate(times, rots, acc):
    out = []
    for a in range(len(times) - 1):
        ta, tb = times[a], times[a + 1]
        m = (acc[:, 0] / 1e9 >= ta) & (acc[:, 0] / 1e9 < tb)
        ts = acc[m, 0] / 1e9; am = acc[m, 1:]
        al = np.zeros(3); be = np.zeros(3); ja = np.zeros((3, 3)); jb = np.zeros((3, 3)); tp = ta
        for k in range(len(ts) + 1):
            tn = ts[k] if k < len(ts) else tb
            hh = tn - tp
            if len(ts) == 0: break
            r = rots.at(tp + hh / 2); f = am[min(k, len(ts) - 1)]
            al += be * hh + 0.5 * (r @ f) * hh * hh; be += (r @ f) * hh
            ja += jb * hh + 0.5 * r * hh * hh; jb += r * hh
            tp = tn
        out.append((tb - ta, al, be, ja, jb))
    return out


# ---------------------------------------------------------------- 3. two linear stages
SIG_PX, SIG_POS, SIG_VEL, SIG_BA = 1.0, 0.01, 0.01, 0.3


def vision(rwc, obs, f, cx, cy, iters=3):
    """Structure and camera centres from the rotations, up to scale: the vision rows are homogeneous (everything
    shrunk to nothing fits them too), so the scale is fixed to |c| = 1 and the answer is the smallest eigenvector of
    the reduced camera system (points eliminated by the Schur complement). Rows reweighted to pixel errors."""
    K = len(rwc); nc = 3 * (K - 1)
    ci = lambda k: None if k == 0 else 3 * (k - 1)
    pts = {p: [(k, (u - cx) / f, (v - cy) / f) for k, u, v in o] for p, o in obs.items() if len(o) >= 3}
    wts = {p: np.ones(len(o)) for p, o in pts.items()}
    dep = {p: np.ones(len(o)) for p, o in pts.items()}
    rows = {p: [(k, rwc[k].T[0] - x * rwc[k].T[2], rwc[k].T[1] - y * rwc[k].T[2]) for k, x, y in o] for p, o in pts.items()}
    cs = None
    for it in range(iters):
        S = np.zeros((nc, nc)); keep = {}
        for p, rr in rows.items():
            Ms = [(k, (wts[p][j] / dep[p][j]) ** 2 * (np.outer(a1, a1) + np.outer(a2, a2))) for j, (k, a1, a2) in enumerate(rr)]
            Hpp = sum(M for _, M in Ms); ev = np.linalg.eigvalsh(Hpp)
            if ev[0] < 1e-5 * ev[2]: continue
            Hi = np.linalg.inv(Hpp); keep[p] = (Ms, Hi)
            for k, Mk in Ms:
                if ci(k) is None: continue
                S[ci(k):ci(k) + 3, ci(k):ci(k) + 3] += Mk
                for l, Ml in Ms:
                    if ci(l) is not None: S[ci(k):ci(k) + 3, ci(l):ci(l) + 3] -= Mk @ Hi @ Ml
        w_, V_ = np.linalg.eigh(S)
        x = V_[:, 0]
        cs = [np.zeros(3)] + [x[3 * (k - 1):3 * k] for k in range(1, K)]
        X, errs = {}, {}
        flip = 0
        for p, (Ms, Hi) in keep.items():
            Xp = Hi @ sum(M @ cs[k] for k, M in Ms); X[p] = Xp
        # the eigenvector's sign is arbitrary: points must lie in front of the cameras
        zs = [ (rwc[k].T @ (X[p] - cs[k]))[2] for p in list(X)[:200] for k, _, _ in pts[p][:1]]
        if np.median(zs) < 0:
            cs = [-c for c in cs]; X = {p: -v for p, v in X.items()}
        for p in X:
            e = []
            for j, (k, xx, yy) in enumerate(pts[p]):
                xc = rwc[k].T @ (X[p] - cs[k]); z = xc[2]
                dep[p][j] = max(z, 1e-4)
                err = f * np.hypot(xc[0] / z - xx, xc[1] / z - yy) if z > 0 else 99
                e.append(err); wts[p][j] = 1.0 if err < 2.0 else 2.0 / err
            errs[p] = float(np.median(e))
    return cs, X, errs


def bundle_adjust(rwc, cs, X, obs, f, cx, cy, perr, sig_rot_deg=0.5, iters=2):
    """Refine rotations, centres and points together on the reprojection error (robust), the sensor rotations as a
    prior (sig_rot_deg), the first camera fixed; the scale is left to the inertial stage."""
    from scipy.optimize import least_squares
    from scipy.sparse import lil_matrix
    K = len(rwc)
    pid = [p for p in X if perr.get(p, 99) < 4.0]
    pts = {p: [(k, u, v) for k, u, v in obs[p]] for p in pid}
    nobs = sum(len(o) for o in pts.values())
    n_cam = 6 * K; n = n_cam + 3 * len(pid)
    x0 = np.zeros(n)
    for k in range(K): x0[6 * k + 3:6 * k + 6] = cs[k]
    for j, p in enumerate(pid): x0[n_cam + 3 * j:n_cam + 3 * j + 3] = X[p]
    oi = np.array([(k, j) for j, p in enumerate(pid) for k, _, _ in pts[p]]); uv = np.array([(u, v) for p in pid for _, u, v in pts[p]])
    srot = np.radians(sig_rot_deg)

    def rots(x):
        return np.array([rwc[k] @ cv2.Rodrigues(x[6 * k:6 * k + 3])[0] for k in range(K)])

    def res(x):
        R = rots(x); C = x[3:n_cam].reshape(K, 6)[:, 3:] if False else np.array([x[6 * k + 3:6 * k + 6] for k in range(K)])
        P = x[n_cam:].reshape(-1, 3)
        d = P[oi[:, 1]] - C[oi[:, 0]]
        xc = np.einsum("nji,nj->ni", R[oi[:, 0]], d)
        z = np.maximum(xc[:, 2], 1e-3)
        r = np.stack([f * xc[:, 0] / z + cx - uv[:, 0], f * xc[:, 1] / z + cy - uv[:, 1]], 1).ravel()
        prior = np.concatenate([x[6 * k:6 * k + 3] / srot for k in range(K)])
        fix0 = x[3:6] * 1e3
        return np.concatenate([r, prior, fix0])

    S = lil_matrix((2 * nobs + 3 * K + 3, n), dtype=int)
    for i, (k, j) in enumerate(oi):
        S[2 * i:2 * i + 2, 6 * k:6 * k + 6] = 1; S[2 * i:2 * i + 2, n_cam + 3 * j:n_cam + 3 * j + 3] = 1
    for k in range(K): S[2 * nobs + 3 * k:2 * nobs + 3 * k + 3, 6 * k:6 * k + 3] = 1
    S[2 * nobs + 3 * K:, 3:6] = 1
    sol = least_squares(res, x0, jac_sparsity=S, loss="huber", f_scale=1.5, method="trf", x_scale="jac", max_nfev=25)
    x = sol.x; R = rots(x)
    cs2 = [x[6 * k + 3:6 * k + 6] for k in range(K)]
    X2 = {p: x[n_cam + 3 * j:n_cam + 3 * j + 3] for j, p in enumerate(pid)}
    r = sol.fun[:2 * nobs].reshape(-1, 2); e = np.hypot(r[:, 0], r[:, 1])
    # per point: its worst reprojection error (a track that jumped once is wrong everywhere), and its parallax
    perr2 = {}; i = 0
    C = np.array(cs2)
    for p in pid:
        m = len(pts[p]); ks = [k for k, _, _ in pts[p]]
        a_ = C[ks[0]] - X2[p]; b_ = C[ks[-1]] - X2[p]
        par = np.degrees(np.arccos(np.clip(a_ @ b_ / (np.linalg.norm(a_) * np.linalg.norm(b_) + 1e-12), -1, 1)))
        perr2[p] = float(np.max(e[i:i + m])) if par >= 3.0 else 99.0
        i += m
    rot_change = [np.degrees(np.linalg.norm(x[6 * k:6 * k + 3])) for k in range(K)]
    return list(R), cs2, X2, perr2, float(np.median(rot_change))


def inertial(times, cs, pre, g_known):
    """Metric scale s, velocities, accelerometer bias (and gravity with the gyroscope) from the unit-scale path:
    s(c_b - c_a) - v_a dt - g dt^2/2 + Ja b = alpha ;  v_b - v_a - g dt + Jb b = beta."""
    K = len(cs); ng = 0 if g_known is not None else 3
    n = 1 + 3 * K + 3 + ng; vi = lambda k: 1 + 3 * k; bi = 1 + 3 * K; gi = bi + 3
    A, y = [], []
    for a, (dt, al, be, ja, jb) in enumerate(pre):
        b = a + 1
        for j in range(3):
            r = np.zeros(n); r[0] = cs[b][j] - cs[a][j]; r[vi(a) + j] = -dt; r[bi:bi + 3] = ja[j]
            rhs = al[j]
            if ng: r[gi + j] = -0.5 * dt * dt
            else: rhs += 0.5 * dt * dt * g_known[j]
            A.append(r / (dt * SIG_POS)); y.append(rhs / (dt * SIG_POS))
            r = np.zeros(n); r[vi(b) + j] = 1; r[vi(a) + j] = -1; r[bi:bi + 3] = jb[j]
            rhs = be[j]
            if ng: r[gi + j] = -dt
            else: rhs += dt * g_known[j]
            A.append(r / SIG_VEL); y.append(rhs / SIG_VEL)
    for j in range(3):
        r = np.zeros(n); r[bi + j] = 1 / SIG_BA; A.append(r); y.append(0.0)
    A = np.array(A); y = np.array(y)
    x, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = A @ x - y
    cov = np.linalg.pinv(A.T @ A) * (res @ res) / max(1, len(y) - n)
    g = g_known if g_known is not None else x[gi:gi + 3]
    return x[0], x[bi:bi + 3], g, float(np.sqrt(cov[0, 0])), float(np.sqrt((res ** 2).mean()))


# ---------------------------------------------------------------- 5. object, support plane, box
def remove_outliers(Q, k=6, z=2.5):
    """Statistical outlier removal: drop points whose mean distance to their k nearest neighbours is unusual."""
    if len(Q) <= k + 2: return Q
    d = np.linalg.norm(Q[:, None] - Q[None], axis=2); d.sort(1)
    m = d[:, 1:k + 1].mean(1); med = np.median(m); mad = np.median(np.abs(m - med)) + 1e-9
    return Q[m < med + z * 1.4826 * mad]


def box_of(pts, trim=3.0):
    xy = pts[:, :2]; best = None
    for ang in np.radians(np.arange(0, 90, 0.5)):
        c, s_ = np.cos(ang), np.sin(ang); u = xy @ np.array([[c, -s_], [s_, c]])
        lo = np.percentile(u, trim, axis=0); hi = np.percentile(u, 100 - trim, axis=0)
        a = np.prod(hi - lo)
        if best is None or a < best[0]: best = (a, hi - lo)
    return sorted(best[1] * 100, reverse=True) + [np.percentile(pts[:, 2], 100 - trim) * 100]


def hull_of(points):
    return cv2.convexHull(np.array(points, np.float32)) if len(points) >= 3 else None


def membership(obs, pick_k, mask, K):
    """Tracks inside the pick mask at its frame; then tracks inside the members' hull in >= 80 % of shared frames."""
    per_frame = {}
    for p, o in obs.items():
        for k, u, v in o: per_frame.setdefault(k, []).append((p, u, v))
    mh, mw = mask.shape
    member = set()
    for p, u, v in per_frame.get(pick_k, []):
        if 0 <= int(v) < mh and 0 <= int(u) < mw and mask[int(v), int(u)]: member.add(p)
    for _ in range(2):
        votes, seen = {}, {}
        for k, lst in per_frame.items():
            mem = [(u, v) for p, u, v in lst if p in member]
            if len(mem) < 6: continue
            hull = hull_of(mem)
            c = np.mean(mem, 0)
            hull_s = ((hull[:, 0] - c) * 0.92 + c).astype(np.float32)   # shrunk: the hull is a little larger than the object
            for p, u, v in lst:
                seen[p] = seen.get(p, 0) + 1
                votes[p] = votes.get(p, 0) + (cv2.pointPolygonTest(hull_s, (u, v), False) >= 0)
        member |= {p for p in seen if seen[p] >= 3 and votes[p] >= 0.8 * seen[p]}
    return member


def support_plane(P, rng=np.random.default_rng(0)):
    best = (0, None)
    for _ in range(600):
        smp = P[rng.choice(len(P), 3, replace=False)]
        nrm = np.cross(smp[1] - smp[0], smp[2] - smp[0]); nn = np.linalg.norm(nrm)
        if nn < 1e-9: continue
        nrm /= nn
        if abs(nrm[2]) < np.cos(np.radians(12)): continue
        nrm = nrm * np.sign(nrm[2]); d = -nrm @ smp[0]
        inl = np.abs(P @ nrm + d) < 0.006
        if inl.sum() > best[0]: best = (inl.sum(), (nrm, d))
    return best[1]


def object_points(P, seed, member2d, fence=0.05, min_h=0.008):
    """3D, as method A: support plane under the seeds, points standing on it within `fence` of the seeds' footprint
    and voted in by the image outlines, then the cluster joined to the seeds."""
    sp = P[seed]
    c0 = np.median(sp[:, :2], 0)
    near = np.hypot(P[:, 0] - c0[0], P[:, 1] - c0[1]) < 0.6
    cand_plane = P[near & ~member2d]
    nrm, dd = support_plane(cand_plane if len(cand_plane) > 30 else P[~member2d])
    hgt = P @ nrm + dd
    v = np.cross(nrm, [0, 0, 1.0]); s_ = np.linalg.norm(v); c = nrm[2]
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    rp = np.eye(3) + vx + vx @ vx * ((1 - c) / s_ ** 2) if s_ > 1e-9 else np.eye(3)
    Q = P @ rp.T; Q[:, 2] = hgt
    seed_ok = seed & (hgt > min_h)
    hull = cv2.convexHull(Q[seed_ok, :2].astype(np.float32))
    dist = np.array([cv2.pointPolygonTest(hull, (float(x), float(y)), True) for x, y in Q[:, :2]])
    sel = (hgt > min_h) & (dist > -fence) & (member2d | seed)
    idx = np.nonzero(sel)[0]
    # connected (3 cm grid, 3D) to the seeds
    cells = {}
    for i in idx: cells.setdefault(tuple(np.floor(Q[i] / 0.03).astype(int)), []).append(i)
    start = {tuple(np.floor(Q[i] / 0.03).astype(int)) for i in np.nonzero(seed_ok)[0]}
    seen = set(k for k in start if k in cells); stack = list(seen); keep = []
    while stack:
        k = stack.pop(); keep += cells[k]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    nb = (k[0] + dx, k[1] + dy, k[2] + dz)
                    if nb in cells and nb not in seen: seen.add(nb); stack.append(nb)
    keep = np.array(sorted(keep))
    return Q[keep], nrm, keep


def main(d):
    d = Path(d)
    ses = json.loads((d / "session.json").read_text()); rot = int(ses.get("sensor_orientation", 90))
    pick = json.loads((d / "pick.json").read_text())
    idx, obs, w, h = tracks(d, rot)
    fr = {int(r.split(",")[0]): r.split(",") for r in (d / "frames.csv").read_text().splitlines()[1:] if r.strip()}
    t_cam = np.array([int(fr[i][1]) for i in idx]) / 1e9
    if ses.get("timestamp_source") != "REALTIME":
        off = np.median([int(fr[i][6]) - int(fr[i][1]) for i in idx]) / 1e9; t_cam = t_cam + off
    acc, gyr, rv = read_imu(d)
    rots = Rotations(gyr, rv)
    diag = json.loads((d / "diagnosis.json").read_text())
    cam = next(c for c in diag["cameras"] if c.get("facing") == "back")
    side = max(ses["size"])
    f0 = cam["focalLengthsMm"][0] / cam["sensorSizeMm"][0] * side * (w / min(ses["size"]))   # at the tracking width
    g_known = np.array([0, 0, -G]) if rots.kind == "rv" else None
    cx, cy = w / 2, h / 2

    def run(td, f):
        times = t_cam + td
        rwc = [rots.at(t) @ R_DC for t in times]
        cs, X, perr = vision(rwc, obs, f, cx, cy)
        err = float(np.median(list(perr.values()))) if perr else 99.0
        return times, rwc, cs, X, perr, err
    best = None
    for td in np.arange(-0.08, 0.041, 0.01):
        r_ = run(td, f0)
        if best is None or r_[-1] < best[0]: best = (r_[-1], td)
    td = best[1]
    for td_ in np.arange(td - 0.008, td + 0.0081, 0.002):
        r_ = run(td_, f0)
        if r_[-1] < best[0]: best = (r_[-1], td_)
    td = best[1]; fbest = (best[0], f0)
    for fs in (0.9, 0.95, 1.05, 1.1):
        r_ = run(td, f0 * fs)
        if r_[-1] < fbest[0]: fbest = (r_[-1], f0 * fs)
    f = fbest[1]
    times, rwc, cs, X, perr, err = run(td, f)
    pre = preintegrate(times, rots, acc)
    s_, ba, g, s_sd, ires = inertial(times, cs, pre, g_known)
    cs = [c * s_ for c in cs]; X = {p: v * s_ for p, v in X.items()}
    # gravity-aligned: with the rotation vector the world already has z up; else rotate g to -z
    if g_known is None:
        gz = -g / np.linalg.norm(g); v = np.cross(gz, [0, 0, 1.0]); s = np.linalg.norm(v); c = gz[2]
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        ra = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2) if s > 1e-9 else np.eye(3)
    else: ra = np.eye(3)
    pid = [p for p in X if perr[p] < 3.0]
    P = np.array([ra @ X[p] for p in pid])
    pk = idx.index(pick["frame"]) if pick["frame"] in idx else 0
    mask = cv2.imread(str(d / pick["maskFile"]), cv2.IMREAD_GRAYSCALE) > 127
    if mask.shape[1] != w: mask = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    member = membership(obs, pk, mask, len(idx))
    seed_ids = set()
    for p, o in obs.items():
        for k, u, v in o:
            if k == pk and 0 <= int(v) < mask.shape[0] and 0 <= int(u) < mask.shape[1] and mask[int(v), int(u)]: seed_ids.add(p)
    is_m = np.array([p in member for p in pid]); is_s = np.array([p in seed_ids for p in pid])
    o2, nrm, _ = object_points(P, is_s, is_m)
    o2 = remove_outliers(o2)
    size = box_of(o2)
    res = {"engine": "on-device prototype", "frames": len(idx), "tracks": len(obs), "points": len(pid), "object_points": int(len(o2)),
           "rotation_source": rots.kind, "time_offset_ms": round(td * 1000, 1), "focal_px": round(f, 1), "focal_prior_px": round(f0, 1),
           "reproj_px": round(err, 2), "acc_bias": np.round(ba, 3).tolist(), "scale_sd_pct": round(100 * s_sd / s_, 2), "size_cm": [round(v, 1) for v in size],
           "tape_cm": pick.get("tapeCm")}
    if res["tape_cm"] and all(res["tape_cm"]): res["error_cm"] = [round(a - b, 1) for a, b in zip(size, res["tape_cm"])]
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1])
