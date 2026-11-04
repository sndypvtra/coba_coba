"""DT20 engine, PC reference: one sweep recording (UkurPaket 0.2 format) -> L x W x H of the picked object, in cm.

    python tools/dt20/solve.py <recording_dir> [--work <dir>]

The stand-in for ARCore on a phone without it, done after the sweep instead of live:
  1. Structure from motion (COLMAP via pycolmap, BSD): camera poses and sparse 3D points, scale unknown.
  2. Clock and axes: the IMU-camera time offset (correlating gyro and visual turn rates) and the camera <- device
     rotation (Kabsch on the angular velocities), gyro bias.
  3. Visual-inertial alignment (the VINS-Mono initialisation, Qin & Shen 2017/2018, then refined): with the rotations
     from vision, the accelerometer integrated between frames must match the camera path: solves the metric scale,
     gravity, accelerometer bias and the velocities. Scale only exists if the phone accelerates: checked.
  4. Gravity-aligned metric scene; floor = plane of sparse points perpendicular to gravity (RANSAC); the angle between
     the two is a check.
  5. Object: the picked mask (tap or box -> MobileSAM in the app) gives seed points; MobileSAM (the app's own ONNX
     files) cuts the object out in 8 more keyframes, prompted by the seeds' box there, twice (the second round from
     what the first found). A 3D point is the object's when inside the mask in >= 80 % of the keyframes that see it;
     mask outlines are lifted to 3D at the depth of the object points next to them (sparse points stop short of the
     edges). Footprint: least-area rectangle (0,5 deg steps, 1,5 % trimmed); height: 97th percentile.
     The same box rule as method A on ARCore, without assuming the object is a box.
Phones whose gyroscope sends nothing (a Urovo DT50 did): the angular rate comes from the game rotation vector.
Cameras whose clock is not the sensors' (timestamp source UNKNOWN): frames are moved onto the sensor clock by their
arrival times (recorder 0.2.1+), and the rest is found by the time-offset search.
Writes <recording_dir>/result.json and result_overlay.jpg.
"""
import json
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pycolmap
from scipy.optimize import least_squares

G = 9.81
TRACK_MIN, ERR_MAX = 3, 1.5  # usable points: seen in at least 3 frames, reprojection error under 1,5 px
KEYFRAMES = 8                # frames that get their own MobileSAM mask
RIM_PX = 25                  # a mask outline pixel is lifted to 3D only with object points this close in the picture
VOTE = 0.8                   # a point is the object's when inside the mask in this share of the keyframes that see it
TRIM = 1.5                   # %: stray points trimmed off each side of the footprint
SAM_DIR = Path(__file__).resolve().parents[2] / "app" / "src" / "main" / "assets" / "sam"
MEAN = np.array([123.675, 116.28, 103.53], np.float32); STD = np.array([58.395, 57.12, 57.375], np.float32)


class Sam:
    """The app's own MobileSAM ONNX files (the phone runs the same model)."""
    def __init__(self):
        import onnxruntime as ort
        self.enc = ort.InferenceSession(str(SAM_DIR / "encoder.onnx")); self.dec = ort.InferenceSession(str(SAM_DIR / "decoder.onnx"))

    def box(self, bgr, b):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB); h, w = rgb.shape[:2]; s = 1024 / max(h, w)
        nh, nw = int(h * s + .5), int(w * s + .5)
        x = (cv2.resize(rgb, (nw, nh)).astype(np.float32) - MEAN) / STD
        pad = np.zeros((1024, 1024, 3), np.float32); pad[:nh, :nw] = x
        emb = self.enc.run(None, {"image": pad.transpose(2, 0, 1)[None]})[0]
        m, sc = self.dec.run(None, {"embeddings": emb, "coords": (np.array([[b[0], b[1]], [b[2], b[3]]], np.float32) * s)[None],
                                    "labels": np.array([[2, 3]], np.float32)})
        i = int(np.argmax(sc[0]))
        up = cv2.resize(m[0][i], (1024, 1024))[:nh, :nw]
        return cv2.resize(up, (w, h)) > 0, float(sc[0][i])


# ---------------------------------------------------------------- reading
def read_recording(d: Path):
    ses = json.loads((d / "session.json").read_text())
    rows = [l.split(",") for l in (d / "frames.csv").read_text().splitlines()[1:] if l.strip()]
    frames = {int(r[0]): int(r[1]) for r in rows}
    # a camera clock that is not the sensors' (timestamp_source UNKNOWN): moved onto it by the arrival times; the
    # delivery delay left over is found by the time-offset search below
    if ses.get("timestamp_source") != "REALTIME" and rows and len(rows[0]) > 6:
        off = int(np.median([int(r[6]) - int(r[1]) for r in rows]))
        frames = {k: v + off for k, v in frames.items()}
    acc, gyr, rv = [], [], {"game_rotation_vector": [], "rotation_vector": []}
    for line in (d / "imu.csv").read_text().splitlines()[1:]:
        p = line.split(",")
        if p[0] == "accelerometer": acc.append([float(p[1])] + [float(v) for v in p[2:5]])
        elif p[0] == "gyroscope": gyr.append([float(p[1])] + [float(v) for v in p[2:5]])
        elif p[0] in rv: rv[p[0]].append([float(p[1])] + [float(v) for v in p[2:6] if v != ""])
    acc = np.array(sorted(acc)); gyr = np.array(sorted(gyr))
    if len(gyr) < 10:                                   # gyroscope listed but silent (seen on a Urovo DT50)
        src = rv["game_rotation_vector"] or rv["rotation_vector"]
        gyr = gyro_from_rotation_vector(np.array(sorted(src))) if len(src) > 10 else gyr
    pick = json.loads((d / "pick.json").read_text()) if (d / "pick.json").exists() else None
    diag = json.loads((d / "diagnosis.json").read_text()) if (d / "diagnosis.json").exists() else None
    return ses, frames, acc, gyr, pick, diag


def gyro_from_rotation_vector(rv):
    """Angular rate in the device frame from the fused orientation: 2 vec(conj(q_a) q_b) / dt."""
    t = rv[:, 0]; x, y, z = rv[:, 1], rv[:, 2], rv[:, 3]
    w = rv[:, 4] if rv.shape[1] > 4 else np.sqrt(np.clip(1 - x * x - y * y - z * z, 0, 1))
    q = np.stack([w, x, y, z], 1)
    a, b = q[:-1], q[1:]
    dt = (t[1:] - t[:-1]) / 1e9
    dot = (a * b).sum(1); sg = np.where(dot < 0, -1.0, 1.0)
    vx = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0] - a[:, 2] * b[:, 3] + a[:, 3] * b[:, 2]
    vy = a[:, 0] * b[:, 2] + a[:, 1] * b[:, 3] - a[:, 2] * b[:, 0] - a[:, 3] * b[:, 1]
    vz = a[:, 0] * b[:, 3] - a[:, 1] * b[:, 2] + a[:, 2] * b[:, 1] - a[:, 3] * b[:, 0]
    ok = (dt > 0) & (dt < 0.1)
    out = np.stack([(t[:-1] + t[1:]) / 2, 2 * sg * vx / dt, 2 * sg * vy / dt, 2 * sg * vz / dt], 1)
    return out[ok]


def focal_prior(diag, w_side):
    """Focal length in pixels from the Camera2 facts: focal (mm) / sensor width (mm) x image width (sensor side)."""
    try:
        c = next(c for c in diag["cameras"] if c.get("facing") == "back")
        return c["focalLengthsMm"][0] / c["sensorSizeMm"][0] * w_side
    except Exception:
        return None


ROT = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


# ---------------------------------------------------------------- 1. structure from motion
def sfm(d: Path, work: Path, frames, rot, f_prior):
    img_dir = work / "images"; img_dir.mkdir(parents=True, exist_ok=True)
    for i in frames:
        im = cv2.imread(str(d / "frames" / f"{i:05d}.jpg"))
        if im is None: continue
        if ROT[rot] is not None: im = cv2.rotate(im, ROT[rot])
        cv2.imwrite(str(img_dir / f"{i:05d}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 95])
    h, w = im.shape[:2]
    db = work / "db.db"
    if db.exists(): db.unlink()
    ro = pycolmap.ImageReaderOptions()
    ro.camera_model = "SIMPLE_RADIAL"
    if f_prior: ro.camera_params = f"{f_prior},{w / 2},{h / 2},0"
    eo = pycolmap.FeatureExtractionOptions(); eo.sift.max_num_features = 6000
    pycolmap.extract_features(db, img_dir, camera_mode=pycolmap.CameraMode.SINGLE, reader_options=ro, extraction_options=eo,
                              device=pycolmap.Device.cpu)
    po = pycolmap.SequentialPairingOptions(); po.overlap = 20; po.quadratic_overlap = True
    pycolmap.match_sequential(db, pairing_options=po, device=pycolmap.Device.cpu)
    opts = pycolmap.IncrementalPipelineOptions(); opts.multiple_models = False
    out = work / "sparse"; out.mkdir(exist_ok=True)
    recs = pycolmap.incremental_mapping(db, img_dir, out, options=opts)
    if not recs:
        raise SystemExit("SfM: tidak ada rekonstruksi. HP harus digeser mengitari objek, bukan hanya diputar di tempat.")
    rec = max(recs.values(), key=lambda r: r.num_reg_images())
    return rec, (w, h)


def poses(rec):
    """frame index -> (R_wc, c) in SfM units."""
    out = {}
    for im in rec.images.values():
        if not im.has_pose: continue
        cw = im.cam_from_world()
        r = cw.rotation.matrix(); t = cw.translation
        out[int(Path(im.name).stem)] = (r.T, -r.T @ t)
    return dict(sorted(out.items()))


# ---------------------------------------------------------------- 2. clock and axes
def so3_log(r):
    return cv2.Rodrigues(r)[0].ravel()


def gyro_mean(gyr, t0, t1):
    m = (gyr[:, 0] >= t0) & (gyr[:, 0] < t1)
    return gyr[m, 1:].mean(0) if m.sum() >= 2 else None


def clock_and_axes(ps, frames, gyr):
    ids = list(ps)
    vis, mids = [], []
    for a, b in zip(ids, ids[1:]):
        dt = (frames[b] - frames[a]) / 1e9
        if dt <= 0 or dt > 0.25: continue
        vis.append(so3_log(ps[a][0].T @ ps[b][0]) / dt); mids.append((frames[a], frames[b]))
    vis = np.array(vis)
    best = (-2, 0.0)
    for td in np.arange(-0.20, 0.1001, 0.001):          # IMU clock = camera clock + td (arrival mapping leaves up to ~-150 ms)
        g = [gyro_mean(gyr, a + td * 1e9, b + td * 1e9) for a, b in mids]
        ok = [i for i, v in enumerate(g) if v is not None]
        if len(ok) < 10: continue
        c = np.corrcoef(np.linalg.norm(vis[ok], axis=1), [np.linalg.norm(g[i]) for i in ok])[0, 1]
        if c > best[0]: best = (c, td)
    corr, td = best
    g = np.array([gyro_mean(gyr, a + td * 1e9, b + td * 1e9) for a, b in mids])
    bg = np.zeros(3)
    for _ in range(3):                                   # camera <- device rotation, then the gyro bias, twice
        u, _, vt = np.linalg.svd((vis).T @ (g - bg))
        r_cd = u @ np.diag([1, 1, np.linalg.det(u @ vt)]) @ vt
        bg = (g - vis @ r_cd).mean(0)
    resid = np.linalg.norm(vis - (g - bg) @ r_cd.T, axis=1)
    return td, corr, r_cd, bg, float(np.sqrt((resid ** 2).mean()))


# ---------------------------------------------------------------- 3. visual-inertial alignment
def preintegrate(ps, frames, acc, gyr, td, r_cd, bg):
    """Per frame pair, in the SfM world frame (rotations from vision, gyro in between):
    alpha, beta for the raw accelerometer, and their exact derivatives by the accelerometer bias
    (alpha(b) = alpha - Ja b, beta(b) = beta - Jb b), since the rotations do not depend on it."""
    ids = list(ps); out = []
    for a, b in zip(ids, ids[1:]):
        ta, tb = frames[a] / 1e9 + td, frames[b] / 1e9 + td
        if tb - ta > 0.25: continue
        m = (acc[:, 0] / 1e9 >= ta) & (acc[:, 0] / 1e9 < tb)
        if m.sum() < 3: continue
        r = ps[a][0] @ r_cd                               # world <- device at frame a
        alpha = np.zeros(3); beta = np.zeros(3); ja = np.zeros((3, 3)); jb = np.zeros((3, 3)); t_prev = ta
        ts = acc[m, 0] / 1e9; aa = acc[m, 1:]
        for k in range(len(ts) + 1):
            t_next = ts[k] if k < len(ts) else tb
            hh = t_next - t_prev
            am = aa[min(k, len(ts) - 1)]
            alpha += beta * hh + 0.5 * (r @ am) * hh * hh; beta += (r @ am) * hh
            ja += jb * hh + 0.5 * r * hh * hh; jb += r * hh
            w = gyro_mean(gyr, t_prev * 1e9, (t_next + 1e-4) * 1e9)
            if w is not None and hh > 0: r = r @ cv2.Rodrigues((w - bg) * hh)[0]
            t_prev = t_next
        out.append((a, b, tb - ta, alpha, beta, ja, jb))
    return out


# each row is divided by its expected noise, so the bias prior weighs what it should
SIG_POS = 0.015              # m/s: position rows (SfM jitter of ~1 mm over one frame step)
SIG_VEL = 0.010              # m/s: velocity rows (accelerometer noise integrated over one step)
BA_PRIOR = 0.3               # m/s^2: a phone accelerometer bias is well below this


def align(ps, pre):
    """Linear in [s, g, b_a, v_k]:  s(c_b - c_a) - v_a dt - g dt^2/2 + Ja b_a = alpha ;  v_b - v_a - g dt + Jb b_a = beta."""
    ids = list(ps); ix = {k: i for i, k in enumerate(ids)}
    n = 7 + 3 * len(ids)
    rows, rhs = [], []
    for a, b, dt, al, be, ja, jb in pre:
        ca, cb = ps[a][1], ps[b][1]
        for j in range(3):
            r = np.zeros(n); r[0] = cb[j] - ca[j]; r[1 + j] = -0.5 * dt * dt; r[4:7] = ja[j]; r[7 + 3 * ix[a] + j] = -dt
            rows.append(r / dt / SIG_POS); rhs.append(al[j] / dt / SIG_POS)
            r = np.zeros(n); r[1 + j] = -dt; r[4:7] = jb[j]; r[7 + 3 * ix[a] + j] = -1; r[7 + 3 * ix[b] + j] = 1
            rows.append(r / SIG_VEL); rhs.append(be[j] / SIG_VEL)
    for j in range(3):
        r = np.zeros(n); r[4 + j] = 1 / BA_PRIOR; rows.append(r); rhs.append(0.0)
    return np.array(rows), np.array(rhs), ix


def refine(a_mat, b_vec):
    """The same equations with |g| = 9,81 (gravity as two angles), non-linear least squares from the linear answer."""
    x0, *_ = np.linalg.lstsq(a_mat, b_vec, rcond=None)
    g0 = x0[1:4] / np.linalg.norm(x0[1:4])
    th0 = np.arccos(np.clip(-g0[2], -1, 1)); ph0 = np.arctan2(-g0[1], -g0[0])

    def full(p):
        th, ph = p[1], p[2]
        g = -G * np.array([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])
        return np.concatenate([[p[0]], g, p[3:]])

    r = least_squares(lambda p: a_mat @ full(p) - b_vec, np.concatenate([[x0[0], th0, ph0], x0[4:]]), method="lm")
    x = full(r.x)
    dof = max(1, len(b_vec) - len(r.x))
    cov = np.linalg.pinv(r.jac.T @ r.jac) * (r.fun @ r.fun) / dof
    return x[0], x[1:4], x[4:7], float(np.sqrt(cov[0, 0])), float(np.sqrt((r.fun ** 2).mean())), float(np.linalg.norm(x0[1:4]))


# ---------------------------------------------------------------- 4-5. floor, object, box
def floor_plane(pts, rng=np.random.default_rng(0)):
    best = (0, None)
    for _ in range(600):
        s = pts[rng.choice(len(pts), 3, replace=False)]
        n = np.cross(s[1] - s[0], s[2] - s[0]); nn = np.linalg.norm(n)
        if nn < 1e-9: continue
        n /= nn
        if abs(n[2]) < np.cos(np.radians(15)): continue
        d = -n @ s[0]
        inl = np.abs(pts @ n + d) < 0.008
        if inl.sum() > best[0]: best = (inl.sum(), (n, d, inl))
    n, d, inl = best[1]
    q = pts[inl]; c = q.mean(0); _, _, vt = np.linalg.svd(q - c); n = vt[2] * np.sign(vt[2][2])
    return n, -n @ c


def box_of(pts, trim=1.0):
    """Smallest rectangle round the footprint, robust to stray points: the angle (0,5 deg steps) whose trimmed
    (trim .. 100 - trim percentile) extents have the least area. Height: 97th percentile."""
    xy = pts[:, :2]
    best = None
    for ang in np.radians(np.arange(0, 90, 0.5)):
        c, s_ = np.cos(ang), np.sin(ang)
        u = xy @ np.array([[c, -s_], [s_, c]])
        lo = np.percentile(u, trim, axis=0); hi = np.percentile(u, 100 - trim, axis=0)
        area = np.prod(hi - lo)
        if best is None or area < best[0]: best = (area, ang, lo, hi)
    _, ang, lo, hi = best
    c, s_ = np.cos(ang), np.sin(ang); rot = np.array([[c, -s_], [s_, c]])
    hgt = np.percentile(pts[:, 2], 97)
    corners = np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]]) @ rot.T
    return sorted((hi - lo) * 100, reverse=True) + [hgt * 100], corners, hgt


def largest_cluster(p, cell=0.02):
    keys = np.floor(p[:, :2] / cell).astype(int)
    cells = {}
    for i, k in enumerate(map(tuple, keys)): cells.setdefault(k, []).append(i)
    seen, best = set(), []
    for k in cells:
        if k in seen: continue
        stack, comp = [k], []
        seen.add(k)
        while stack:
            c = stack.pop(); comp += cells[c]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nb = (c[0] + dx, c[1] + dy)
                    if nb in cells and nb not in seen: seen.add(nb); stack.append(nb)
        if len(comp) > len(best): best = comp
    return np.array(sorted(best))


def solve(d: Path, work: Path):
    t_start = time.time()
    ses, frames, acc, gyr, pick, diag = read_recording(d)
    rot = int(ses.get("sensor_orientation", 90))
    side_w = max(ses.get("size", [0, 0]))
    f_prior = focal_prior(diag, side_w) if diag else None
    rec, (w, h) = sfm(d, work, frames, rot, f_prior)
    ps = poses(rec)
    cam = rec.cameras[next(iter(rec.cameras))]
    td, corr, r_cd, bg, gres = clock_and_axes(ps, frames, gyr)
    pre = preintegrate(ps, frames, acc, gyr, td, r_cd, bg)
    a_mat, b_vec, _ = align(ps, pre)
    s, g, ba, s_sd, vres, g_lin = refine(a_mat, b_vec)

    # metric, gravity-aligned world (z up)
    gz = -g / np.linalg.norm(g)
    v = np.cross(gz, [0, 0, 1.0]); sv = np.linalg.norm(v); cv_ = gz @ [0, 0, 1.0]
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    r_al = np.eye(3) + vx + vx @ vx * ((1 - cv_) / (sv * sv)) if sv > 1e-9 else np.eye(3)
    ids3 = list(rec.points3D.keys())
    xyz = np.array([rec.points3D[i].xyz for i in ids3]) * s @ r_al.T
    err = np.array([rec.points3D[i].error for i in ids3]); trk = np.array([rec.points3D[i].track.length() for i in ids3])
    n, dd = floor_plane(xyz[(trk >= 3) & (err < 2.0)])
    floor_tilt = float(np.degrees(np.arccos(abs(n[2]))))
    # put the floor at z = 0 along its own normal (the floor, not gravity, defines "standing on")
    v = np.cross(n, [0, 0, 1.0]); sv = np.linalg.norm(v); cv_ = n[2]
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    r_fl = np.eye(3) + vx + vx @ vx * ((1 - cv_) / (sv * sv)) if sv > 1e-9 else np.eye(3)
    xyz_f = xyz @ r_fl.T; xyz_f[:, 2] += dd

    res = {"frames": len(frames), "registered": len(ps), "points": len(ids3), "time_offset_ms": round(td * 1000, 1),
           "gyro_vision_corr": round(corr, 3), "gyro_fit_rad_s": round(gres, 4), "gyro_bias": np.round(bg, 4).tolist(),
           "camera_from_device": np.round(r_cd, 3).tolist(), "scale_m_per_unit": s, "scale_sd_pct": round(100 * s_sd / s, 2),
           "acc_bias": np.round(ba, 3).tolist(), "imu_fit_rms": round(vres, 4), "gravity_linear_m_s2": round(g_lin, 3), "floor_vs_gravity_deg": round(floor_tilt, 2),
           "focal_px": float(cam.params[0]), "focal_prior_px": f_prior}
    if pick:
        pf = pick["frame"]
        if pf not in ps: raise SystemExit(f"picked frame {pf} not registered by SfM")
        mask = cv2.imread(str(d / pick["maskFile"]), cv2.IMREAD_GRAYSCALE) > 127
        mask = cv2.dilate(mask.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        r_wc, c = ps[pf]
        xc = (np.array([rec.points3D[i].xyz for i in ids3]) - c) @ r_wc          # SfM units, picked camera frame
        uv = np.array([cam.img_from_cam(p) if p[2] > 0 else [-1, -1] for p in xc])
        inside = (xc[:, 2] > 0) & (uv[:, 0] >= 0) & (uv[:, 1] >= 0) & (uv[:, 0] < w) & (uv[:, 1] < h)
        inside[inside] = mask[uv[inside, 1].astype(int), uv[inside, 0].astype(int)]
        # repeated prints match wrongly between faces: only points seen 4+ times that reproject within 1 px
        good = (trk >= TRACK_MIN) & (err < ERR_MAX) & (xyz_f[:, 2] > 0.01)
        # seeds: seen in the picked frame inside the mask, one connected cluster
        seen = np.zeros(len(ids3), bool)
        pick_img = next(im for im in rec.images.values() if int(Path(im.name).stem) == pf)
        pos = {pid: k for k, pid in enumerate(ids3)}
        for p2 in pick_img.points2D:
            if p2.has_point3D() and p2.point3D_id in pos: seen[pos[p2.point3D_id]] = True
        seeds = np.nonzero(inside & seen & good)[0]
        if len(seeds) < 15: raise SystemExit(f"only {len(seeds)} object points seen in the picked frame")
        span = np.ptp(xyz_f[seeds, :2], axis=0).prod()
        cell = float(np.clip(2.5 * np.sqrt(span / len(seeds)), 0.02, 0.08))
        seeds = seeds[largest_cluster(xyz_f[seeds], cell)]
        # masks in more frames: MobileSAM prompted with the box round the seeds as seen from there
        sam = Sam()
        ids_sorted = list(ps)
        keys = sorted(set([pf] + [ids_sorted[int(round(k))] for k in np.linspace(0, len(ids_sorted) - 1, KEYFRAMES)]))
        sfm_xyz = np.array([rec.points3D[i].xyz for i in ids3])
        def project(k, pts):
            r_wc_k, c_k = ps[k]; pc = (pts - c_k) @ r_wc_k
            uv = np.array([cam.img_from_cam(p) if p[2] > 0 else [-1e9, -1e9] for p in pc]); return uv, pc[:, 2] > 0
        cand = np.nonzero(good)[0]

        def cut_masks(src, margin):
            out, scores = {pf: mask}, {}
            for k in keys:
                if k == pf: continue
                uv, front = project(k, sfm_xyz[src]); uv = uv[front]
                if len(uv) < 10: continue
                x0, y0 = np.percentile(uv, 1, axis=0); x1, y1 = np.percentile(uv, 99, axis=0)
                mx_, my_ = margin * (x1 - x0), margin * (y1 - y0)
                bb = [max(0, x0 - mx_), max(0, y0 - my_), min(w - 1, x1 + mx_), min(h - 1, y1 + my_)]
                img_k = cv2.imread(str(work / "images" / f"{k:05d}.jpg"))
                mk, sc = sam.box(img_k, bb)
                out[k] = cv2.dilate(mk.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0; scores[k] = round(sc, 3)
                view = img_k.copy(); view[mk] = (0.5 * view[mk] + [0, 0, 120]).astype(np.uint8)
                cv2.rectangle(view, (int(bb[0]), int(bb[1])), (int(bb[2]), int(bb[3])), (255, 255, 255), 2)
                cv2.imwrite(str(work / f"mask_{k:05d}.jpg"), view)
            return out, scores

        def vote(pts_idx, ms):
            votes = np.zeros(len(pts_idx)); seen_n = np.zeros(len(pts_idx))
            for k, mk in ms.items():
                uv, front = project(k, sfm_xyz[pts_idx])
                inimg = front & (uv[:, 0] >= 0) & (uv[:, 1] >= 0) & (uv[:, 0] < w) & (uv[:, 1] < h)
                idx = np.nonzero(inimg)[0]
                seen_n[idx] += 1
                votes[idx] += ms_get(mk, uv[idx])
            m = pts_idx[(seen_n >= 3) & (votes >= VOTE * seen_n)]
            return m[largest_cluster(xyz_f[m], cell)] if len(m) else m

        ms_get = lambda mk, uv: mk[uv[:, 1].astype(int), uv[:, 0].astype(int)]
        # two rounds: the seeds only cover what the picked frame sees; the first vote finds the rest of the object
        masks, mask_scores = cut_masks(seeds, 0.15)
        member = vote(cand, masks)
        masks, mask_scores = cut_masks(member, 0.08)
        member = vote(cand, masks)
        obj = xyz_f[member]
        # silhouette rims: sparse points stop short of the object's edges (no corners right at a silhouette), so each
        # mask outline is lifted to 3D at the depth of the object points next to it, and voted on like the points
        to_floor = lambda q: (q * s @ r_al.T @ r_fl.T) + np.array([0, 0, dd])
        rims = []
        for k, mk in masks.items():
            uv_o, front = project(k, sfm_xyz[member])
            r_wc_k, c_k = ps[k]
            z_o = ((sfm_xyz[member] - c_k) @ r_wc_k)[:, 2]
            ok = front & (uv_o[:, 0] >= 0) & (uv_o[:, 0] < w) & (uv_o[:, 1] >= 0) & (uv_o[:, 1] < h)
            if ok.sum() < 10: continue
            tree_uv, tree_z = uv_o[ok], z_o[ok]
            cs, _ = cv2.findContours(mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if not cs: continue
            ct = max(cs, key=cv2.contourArea).reshape(-1, 2)[::4].astype(float)
            for u, v in ct:
                d2 = (tree_uv[:, 0] - u) ** 2 + (tree_uv[:, 1] - v) ** 2
                near = np.argsort(d2)[:5]
                if d2[near[0]] > RIM_PX ** 2 or np.ptp(tree_z[near]) * s > 0.02: continue   # neighbours on one surface only
                z = float(np.median(tree_z[near]))
                ray = np.array([*cam.cam_from_img(np.array([u, v])), 1.0])
                rims.append(c_k + r_wc_k @ (ray * z))
        rim_n = 0
        if rims:
            rims = np.array(rims)
            votes = np.zeros(len(rims)); seen_r = np.zeros(len(rims))
            for k, mk in masks.items():
                uv, front = project(k, rims)
                inimg = front & (uv[:, 0] >= 0) & (uv[:, 1] >= 0) & (uv[:, 0] < w) & (uv[:, 1] < h)
                idx = np.nonzero(inimg)[0]; seen_r[idx] += 1
                votes[idx] += mk[uv[idx, 1].astype(int), uv[idx, 0].astype(int)]
            rim_f = to_floor(rims[(seen_r >= 3) & (votes >= VOTE * seen_r)])
            rim_f = rim_f[rim_f[:, 2] > 0.01]
            rim_n = len(rim_f)
            if rim_n: obj = np.concatenate([obj, rim_f])
        res["rim_points"] = int(rim_n)
        res["masks"] = len(masks); res["mask_scores"] = mask_scores; res["object_points_seen_in_pick"] = int(len(seeds))
        np.save(work / "object_points.npy", obj)
        cams = np.array([ps[k][1] for k in ps]) * s @ r_al.T @ r_fl.T; cams[:, 2] += dd
        np.save(work / "camera_centres.npy", np.concatenate([np.array(list(ps))[:, None], cams], 1))
        size, corners, hgt = box_of(obj, TRIM)
        res.update({"object_points": int(len(obj)), "size_cm": [round(v, 1) for v in size]})
        tape = [v for v in (pick.get("tapeCm") or []) if v]
        if len(tape) == 3:
            res["tape_cm"] = tape
            res["error_cm"] = [round(a - b, 1) for a, b in zip(size, tape)]
        # overlay: the box drawn into the picked frame
        img = cv2.imread(str(work / "images" / f"{pf:05d}.jpg"))
        inv = np.linalg.inv(r_fl @ r_al)
        def to_px(p):
            q = p.copy(); q[2] -= dd; q = (q @ inv.T) / s
            pc = (q - c) @ r_wc
            return cam.img_from_cam(pc)
        base = [np.array([x, y, 0.0]) for x, y in corners]; top = [b + [0, 0, hgt] for b in base]
        for a, b in [(0, 1), (1, 2), (2, 3), (3, 0)]:
            for ring in (base, top):
                cv2.line(img, tuple(int(v) for v in to_px(ring[a])), tuple(int(v) for v in to_px(ring[b])), (60, 220, 60), 2, cv2.LINE_AA)
            cv2.line(img, tuple(int(v) for v in to_px(base[a])), tuple(int(v) for v in to_px(top[a])), (60, 220, 60), 2, cv2.LINE_AA)
        for p in obj[::max(1, len(obj) // 600)]:
            cv2.circle(img, tuple(int(v) for v in to_px(p)), 2, (40, 40, 230), -1)
        cv2.putText(img, " x ".join(f"{v:.1f}" for v in size) + " cm", (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(img, " x ".join(f"{v:.1f}" for v in size) + " cm", (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (40, 40, 40), 2, cv2.LINE_AA)
        cv2.imwrite(str(d / "result_overlay.jpg"), img)
    res["seconds_pc"] = round(time.time() - t_start, 1)
    (d / "result.json").write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    d = Path(sys.argv[1])
    work = Path(sys.argv[sys.argv.index("--work") + 1]) if "--work" in sys.argv else d / "_work"
    if work.exists(): shutil.rmtree(work)
    print(json.dumps(solve(d, work), indent=2))
