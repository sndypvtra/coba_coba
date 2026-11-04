"""A synthetic DT20 sweep in the recorder's own file format, with a known object, for testing the solver.

    python tools/dt20/synth_sweep.py <out_dir> [box|cylinder|sack] [--rotate-only] [--dt50] [--seed N]

--dt50: what a Urovo DT50 reported: gyroscope listed but silent (only the fused game rotation vector, 200 Hz, with
10 ms lag), and a camera clock that is not the sensors' (timestamp source UNKNOWN, 3,2 s apart, frames arriving
35 +- 5 ms after their timestamp).

What is simulated, and how (so the test means something):
  - scene: textured floor (terrazzo-like) and one object with a printed / cardboard texture, lit from one side.
    box 40 x 30 x 20 cm turned 20 deg; cylinder r 13,5 cm h 40 cm (a gallon); sack = two merged ellipsoids (irregular).
  - camera: pinhole f = 420 px on 480 x 640 upright frames, stored sideways like the DT20 (sensor orientation 90),
    15 frames/s for 5 s, walking ~80 deg round the object at ~0,75 m, 0,55 m high, with small up/down/in/out motion.
  - motion sensors at 200 Hz from the same trajectory: accelerometer = specific force in the device frame, gyroscope =
    angular rate, each with white noise and a constant bias at the level of a cheap phone MEMS part
    (acc 0,03 m/s^2 noise, 0,08 m/s^2 bias; gyro 0,004 rad/s noise, 0,01 rad/s bias), and the IMU clock 12 ms ahead.
  - the pick: the object's true mask in the middle frame, with the tape size in pick.json (as a tester types it).
Not simulated: rolling shutter, motion blur, autofocus breathing, lens distortion, the lever arm camera <-> IMU.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

W, H, F = 480, 640, 420.0                      # upright frame
CX, CY = W / 2, H / 2
FPS, T, IMU_HZ = 15.0, 5.0, 200.0
TD = 0.012                                      # IMU clock ahead of the camera clock (s)
G = 9.81
R_CD = np.diag([1.0, -1.0, -1.0])               # device -> camera (portrait phone, back camera)


def look_at(p, target, roll):
    z = target - p; z /= np.linalg.norm(z)
    x = np.cross(z, [0, 0, 1.0]); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    r = np.stack([x, y, z], 1)                  # world <- camera
    c, s = np.cos(roll), np.sin(roll)
    return r @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def trajectory(t, rotate_only=False):
    """Camera centre and world <- camera rotation at times t (s)."""
    tt = np.clip(t, 0, T)
    phi = np.radians(-130 + 80 * (1 - np.cos(np.pi * tt / T)) / 2)
    if rotate_only:                             # standing still, only turning the phone: no metric scale
        p = np.stack([0.75 * np.cos(np.radians(-90)) + 0 * t, 0.75 * np.sin(np.radians(-90)) + 0 * t, 0.55 + 0 * t], 1)
        tgt = np.stack([0.15 * np.sin(2 * np.pi * t / 5), 0 * t, 0.1 + 0.03 * np.sin(2 * np.pi * t / 2)], 1)
        return p, np.array([look_at(p[i], tgt[i], 0.02 * np.sin(3 * t[i])) for i in range(len(t))])
    r = 0.75 + 0.06 * np.sin(2 * np.pi * t / 2.3)
    h = 0.55 + 0.05 * np.sin(2 * np.pi * t / 1.6)
    p = np.stack([r * np.cos(phi), r * np.sin(phi), h], 1)
    tgt = np.stack([0.02 * np.sin(t), 0.02 * np.cos(1.3 * t), 0.10 + 0 * t], 1)
    return p, np.array([look_at(p[i], tgt[i], 0.05 * np.sin(2.1 * t[i])) for i in range(len(t))])


# ---------------------------------------------------------------- scene
class Scene:
    def __init__(self, kind, rng):
        self.kind = kind
        self.floor = self.terrazzo(rng)
        self.tex = self.cardboard(rng) if kind == "box" else self.printed(rng, (200, 220, 235) if kind == "cylinder" else (70, 90, 60))
        if kind == "box":
            self.size = np.array([0.40, 0.30, 0.20]); self.yaw = np.radians(20); self.c = np.array([0.02, -0.01])
        elif kind == "cylinder":
            self.r, self.h = 0.135, 0.40
        else:
            self.ell = [(np.array([0.0, 0.0, 0.095]), np.array([0.22, 0.15, 0.095])),
                        (np.array([0.10, 0.06, 0.11]), np.array([0.13, 0.10, 0.08]))]

    @staticmethod
    def terrazzo(rng, n=2048):
        img = np.full((n, n, 3), (205, 200, 190), np.uint8)
        for _ in range(26000):
            x, y = rng.integers(0, n, 2); r = int(rng.integers(2, 9))
            col = tuple(int(v) for v in rng.choice([(60, 60, 65), (120, 110, 100), (160, 150, 140), (90, 80, 120), (230, 230, 225)]))
            cv2.circle(img, (int(x), int(y)), r, col, -1)
        return cv2.GaussianBlur(img, (3, 3), 0)

    @staticmethod
    def cardboard(rng, n=1024):
        base = np.array([95, 140, 180], np.float32)                     # BGR brown
        noise = cv2.GaussianBlur(rng.normal(0, 1, (n, n)).astype(np.float32), (0, 0), 2) * 18
        img = np.clip(base + noise[..., None], 0, 255).astype(np.uint8)
        for _ in range(60):                                             # print, tape, scribbles
            x, y = rng.integers(0, n - 120, 2); w, h = rng.integers(20, 120, 2)
            cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)), tuple(int(v) for v in rng.integers(20, 90, 3)), int(rng.integers(1, 4)))
        for _ in range(40):
            x, y = rng.integers(0, n - 200, 2)
            cv2.putText(img, "".join(rng.choice(list("ABCDEFGH0123456789"), 6)), (int(x), int(y) + 40), cv2.FONT_HERSHEY_SIMPLEX,
                        float(rng.uniform(0.6, 1.6)), (30, 30, 40), 2)
        cv2.rectangle(img, (380, 380), (640, 640), (245, 245, 245), -1)    # white label
        for i in range(12): cv2.line(img, (400, 400 + 18 * i), (620, 400 + 18 * i), (40, 40, 40), 2)
        return img

    @staticmethod
    def printed(rng, base, n=1024):
        img = np.full((n, n, 3), base, np.uint8)
        for _ in range(500):
            x, y = rng.integers(0, n, 2)
            cv2.circle(img, (int(x), int(y)), int(rng.integers(3, 18)), tuple(int(v) for v in rng.integers(0, 255, 3)), -1)
        for _ in range(30):
            x, y = rng.integers(0, n - 200, 2)
            cv2.putText(img, "".join(rng.choice(list("AQUA0123456789"), 5)), (int(x), int(y) + 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 2)
        return cv2.GaussianBlur(img, (3, 3), 0)

    def hit(self, o, d):
        """Nearest object hit: t, normal, (u, v) texture coords in metres; t = inf where missed."""
        n = d.shape[0]
        t = np.full(n, np.inf); nor = np.zeros((n, 3)); uv = np.zeros((n, 2))
        if self.kind == "box":
            c, s = np.cos(self.yaw), np.sin(self.yaw)
            rot = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])           # world -> box
            ob = rot @ (o - np.array([self.c[0], self.c[1], 0])); db = d @ rot.T
            lo = np.array([-self.size[0] / 2, -self.size[1] / 2, 0]); hi = np.array([self.size[0] / 2, self.size[1] / 2, self.size[2]])
            with np.errstate(divide="ignore", invalid="ignore"):
                t1 = (lo - ob) / db; t2 = (hi - ob) / db
            tn = np.minimum(t1, t2).max(1); tf = np.maximum(t1, t2).min(1)
            ok = (tn <= tf) & (tn > 0)
            t[ok] = tn[ok]
            ax = np.argmax(np.minimum(t1, t2), 1)
            p = ob + db * tn[:, None]
            nb = np.zeros((n, 3)); nb[np.arange(n), ax] = -np.sign(db[np.arange(n), ax])
            nor = nb @ rot
            uv = np.where((ax == 2)[:, None], p[:, :2], np.where((ax == 0)[:, None], p[:, 1:3], p[:, [0, 2]])) + np.array([0.5, 0.5])
        elif self.kind == "cylinder":
            a = d[:, 0] ** 2 + d[:, 1] ** 2; b = 2 * (o[0] * d[:, 0] + o[1] * d[:, 1]); cc = o[0] ** 2 + o[1] ** 2 - self.r ** 2
            disc = b * b - 4 * a * cc
            ts = (-b - np.sqrt(np.maximum(disc, 0))) / (2 * a)
            z = o[2] + ts * d[:, 2]
            side = (disc > 0) & (ts > 0) & (z >= 0) & (z <= self.h)
            tc = (self.h - o[2]) / d[:, 2]; pc = o + d * tc[:, None]
            cap = (tc > 0) & (pc[:, 0] ** 2 + pc[:, 1] ** 2 <= self.r ** 2)
            ps = o + d * ts[:, None]
            t = np.where(side, ts, np.inf); t = np.where(cap & (tc < t), tc, t)
            use_cap = cap & (tc <= t)
            nor = np.where(use_cap[:, None], [0, 0, 1.0], np.stack([ps[:, 0], ps[:, 1], 0 * ps[:, 0]], 1) / self.r)
            uv = np.where(use_cap[:, None], pc[:, :2] + 0.5, np.stack([np.arctan2(ps[:, 1], ps[:, 0]) * self.r + 1, ps[:, 2]], 1))
        else:
            for cen, rad in self.ell:
                oo = (o - cen) / rad; dd = d / rad
                a = (dd ** 2).sum(1); b = 2 * (oo * dd).sum(1); cc = (oo ** 2).sum() - 1
                disc = b * b - 4 * a * cc
                te = (-b - np.sqrt(np.maximum(disc, 0))) / (2 * a)
                ok = (disc > 0) & (te > 0) & (te < t)
                p = o + d * te[:, None]
                nn = (p - cen) / rad ** 2; nn /= np.linalg.norm(nn, axis=1, keepdims=True)
                t = np.where(ok, te, t); nor = np.where(ok[:, None], nn, nor)
                uv = np.where(ok[:, None], np.stack([np.arctan2(p[:, 1] - cen[1], p[:, 0] - cen[0]) * 0.2 + 1, p[:, 2] + p[:, 0]], 1), uv)
        return t, nor, uv

    def truth(self):
        """Smallest box round the object: L >= W, H (cm)."""
        if self.kind == "box": return sorted(self.size[:2] * 100, reverse=True) + [self.size[2] * 100]
        if self.kind == "cylinder": return [self.r * 200, self.r * 200, self.h * 100]
        pts = []
        for cen, rad in self.ell:
            u = np.random.default_rng(1).normal(size=(20000, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
            pts.append(cen + u * rad)
        p = np.concatenate(pts); p = p[p[:, 2] >= 0]
        (_, _), (a, b), _ = cv2.minAreaRect(p[:, :2].astype(np.float32))
        return [max(a, b) * 100, min(a, b) * 100, p[:, 2].max() * 100]

    def render(self, p, r_wc):
        u, v = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
        dc = np.stack([(u - CX) / F, (v - CY) / F, np.ones_like(u)], -1).reshape(-1, 3)
        d = dc @ r_wc.T; d /= np.linalg.norm(d, axis=1, keepdims=True)
        t_obj, nor, uv = self.hit(p, d)
        t_floor = np.where(d[:, 2] < 0, -p[2] / d[:, 2], np.inf)
        img = np.tile(np.array([175, 178, 180], np.float32), (H * W, 1))          # far wall: flat, no features
        fl = t_floor < t_obj
        pf = p + d * np.where(np.isfinite(t_floor), t_floor, 0)[:, None]
        fx = (np.mod(pf[:, 0] + 2, 4) / 4 * 2047).astype(int); fy = (np.mod(pf[:, 1] + 2, 4) / 4 * 2047).astype(int)
        far = np.clip((np.hypot(pf[:, 0], pf[:, 1]) - 1.8) / 0.8, 0, 1)[:, None]      # the floor fades out 1,8-2,6 m away
        img[fl] = (self.floor[fy, fx] * (1 - far) + np.array([175, 178, 180]) * far)[fl]
        ob = np.isfinite(t_obj) & ~fl
        tx = (np.mod(uv[:, 0], 1.0) * 1023).astype(int); ty = (np.mod(uv[:, 1], 1.0) * 1023).astype(int)
        light = np.array([0.35, -0.45, 0.82]); light /= np.linalg.norm(light)
        shade = 0.45 + 0.6 * np.clip(nor @ light, 0, 1)
        img[ob] = self.tex[ty[ob], tx[ob]] * shade[ob, None]
        img = img.reshape(H, W, 3) + np.random.default_rng(int(p[0] * 1e6) % 2**31).normal(0, 2.0, (H, W, 3))
        return np.clip(img, 0, 255).astype(np.uint8), ob.reshape(H, W)


# ---------------------------------------------------------------- motion sensors
def imu(rotate_only, rng):
    dt = 1e-3
    t = np.arange(-0.4, T + 0.4, dt)
    p, r_wc = trajectory(t, rotate_only)
    r_wd = r_wc @ R_CD                                      # R_CD is its own inverse
    acc_w = np.gradient(np.gradient(p, dt, axis=0), dt, axis=0)
    f_w = acc_w + np.array([0, 0, G])                       # specific force
    f_d = np.einsum("nji,nj->ni", r_wd, f_w)
    w_d = np.zeros_like(f_d)
    for i in range(len(t) - 1):
        dr = r_wd[i].T @ r_wd[i + 1]
        w_d[i] = cv2.Rodrigues(dr)[0].ravel() / dt
    w_d[-1] = w_d[-2]
    step = int(round(1 / IMU_HZ / dt))
    idx = np.arange(0, len(t), step)
    ba, bg = rng.normal(0, 0.08, 3), rng.normal(0, 0.01, 3)
    acc = f_d[idx] + ba + rng.normal(0, 0.03, (len(idx), 3))
    gyr = w_d[idx] + bg + rng.normal(0, 0.004, (len(idx), 3))
    return t[idx], acc, gyr, ba, bg


def quat(r):
    """Rotation matrix -> (x, y, z, w)."""
    w = np.sqrt(max(0.0, 1 + r[0, 0] + r[1, 1] + r[2, 2])) / 2
    if w > 1e-3:
        return np.array([(r[2, 1] - r[1, 2]) / (4 * w), (r[0, 2] - r[2, 0]) / (4 * w), (r[1, 0] - r[0, 1]) / (4 * w), w])
    x = np.sqrt(max(0.0, 1 + r[0, 0] - r[1, 1] - r[2, 2])) / 2
    return np.array([x, (r[0, 1] + r[1, 0]) / (4 * x), (r[0, 2] + r[2, 0]) / (4 * x), (r[2, 1] - r[1, 2]) / (4 * x)])


def main(out, kind="box", rotate_only=False, seed=0, dt50=False):
    rng = np.random.default_rng(seed)
    out = Path(out); (out / "frames").mkdir(parents=True, exist_ok=True)
    sc = Scene(kind, rng)
    tf = np.arange(0, T, 1 / FPS)
    p, r_wc = trajectory(tf, rotate_only)
    t0 = 10_000_000_000
    rows = ["index,t_ns,sharpness,width,height,bytes,arrival_ns"]
    cam_clock = -3_200_000_000 if dt50 else 0             # DT50: camera clock 3,2 s behind the sensors' clock
    mid = len(tf) // 2
    for i, (pi, ri) in enumerate(zip(p, r_wc)):
        img, ob = sc.render(pi, ri)
        side = np.ascontiguousarray(np.rot90(img, 1))       # stored as the sensor sees it (upright = rotate 90 clockwise)
        f = out / "frames" / f"{i:05d}.jpg"
        cv2.imwrite(str(f), side, [cv2.IMWRITE_JPEG_QUALITY, 92])
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        arrival = t0 + int(tf[i] * 1e9) + int((0.035 + rng.normal(0, 0.005)) * 1e9)
        rows.append(f"{i},{t0 + cam_clock + int(tf[i] * 1e9)},{cv2.Laplacian(g, cv2.CV_64F).var():.2f},{side.shape[1]},{side.shape[0]},{f.stat().st_size},{arrival}")
        if i == mid:
            mask = ob
            cv2.imwrite(str(out / "mask.png"), mask.astype(np.uint8) * 255)
    (out / "frames.csv").write_text("\n".join(rows) + "\n")
    ti, acc, gyr, ba, bg = imu(rotate_only, rng)
    lines = ["sensor,t_ns,v0,v1,v2,v3,v4,v5"]
    if dt50:                                            # fused orientation instead of the gyroscope, 10 ms late
        _, r_wc_i = trajectory(ti - 0.010, rotate_only)
        rvq = [quat(r @ R_CD) for r in r_wc_i]
    for k in range(len(ti)):
        ts = t0 + int((ti[k] + TD) * 1e9)
        lines.append(f"accelerometer,{ts},{acc[k, 0]:.5f},{acc[k, 1]:.5f},{acc[k, 2]:.5f}")
        if dt50:
            q = rvq[k] + rng.normal(0, 2e-4, 4); q /= np.linalg.norm(q)
            lines.append(f"game_rotation_vector,{ts + 500_000},{q[0]:.6f},{q[1]:.6f},{q[2]:.6f},{q[3]:.6f}")
        else:
            lines.append(f"gyroscope,{ts + 500_000},{gyr[k, 0]:.6f},{gyr[k, 1]:.6f},{gyr[k, 2]:.6f}")
    (out / "imu.csv").write_text("\n".join(lines) + "\n")
    (out / "session.json").write_text(json.dumps({"camera_id": "0", "size": [H, W], "sensor_orientation": 90,
                                                  "timestamp_source": "UNKNOWN" if dt50 else "REALTIME", "frames_saved": len(tf), "frames_dropped": 0}, indent=2))
    sensor_w = 3.5 * H / F                                  # focal 3,5 mm, sensor width so that f = 420 px on the 640 px side
    (out / "diagnosis.json").write_text(json.dumps({"cameras": [{"id": "0", "facing": "back", "focalLengthsMm": [3.5],
                                                                  "sensorSizeMm": [sensor_w, sensor_w * W / H], "pixelArray": [H, W]}]}, indent=2))
    ys, xs = np.nonzero(mask)
    truth = sc.truth()
    pick = {"frame": mid, "file": f"frames/{mid:05d}.jpg", "rotationDeg": 90, "width": W, "height": H, "mode": "box",
            "box": [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())], "maskFile": "mask.png", "maskScore": 1.0,
            "maskAreaPx": int(mask.sum()), "maskBox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "samEncodeMs": None, "samDecodeMs": 0, "name": f"sintetis {kind}", "tapeCm": [round(v, 1) for v in truth]}
    (out / "pick.json").write_text(json.dumps(pick, indent=2))
    (out / "truth.json").write_text(json.dumps({"kind": kind, "rotate_only": rotate_only, "size_cm": truth, "td_s": TD,
                                                "acc_bias": ba.tolist(), "gyro_bias": bg.tolist(), "f_px": F}, indent=2))
    print(out, kind, "truth", [round(v, 1) for v in truth])


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 0
    if "--seed" in sys.argv: a = [x for x in a if x != str(seed)]
    main(a[0], a[1] if len(a) > 1 else "box", "--rotate-only" in sys.argv, seed, "--dt50" in sys.argv)
