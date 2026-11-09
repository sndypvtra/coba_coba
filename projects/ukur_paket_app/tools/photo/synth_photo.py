"""Synthetic hand-held photos of one object on a floor, for testing the photo mode (UkurPaket 0.4.0).

    python tools/photo/synth_photo.py <out_dir> [box|sack|cylinder] [--seed N] [--n 3]

Each photo is what the photo mode receives on the phone: an upright 480 x 640 picture, the camera's intrinsics, and the
'up' direction in camera axes (from the accelerometer while the phone is still), plus what only a test knows: the true
depth map (metres along the optical axis), the object's true mask and its true size.

The camera is held like a courier holds it: standing or bending a little (lens 0,75-1,15 m above the floor), looking
down 38-62 deg at the object from near a corner, a few degrees of roll, at 0,7-1,4 m. The object is the sweep test's
(tools/dt20/synth_sweep.py): a 40 x 30 x 20 cm carton, a sack, or a gallon. Floor: terrazzo out to 5 m; a textured wall
4 m away so the top of the picture is not empty.
Not simulated: lens distortion, blur, noise beyond 2 grey levels, shadows on the floor.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dt20"))
import synth_sweep as ss  # noqa: E402

W, H, F = 480, 640, 420.0
CX, CY = W / 2, H / 2


def look_at(p, target, roll):
    z = target - p; z /= np.linalg.norm(z)
    x = np.cross(z, [0, 0, 1.0]); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    r = np.stack([x, y, z], 1)                       # world <- camera
    c, s = np.cos(roll), np.sin(roll)
    return r @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def wall_texture(rng, n=1024):
    img = np.full((n, n, 3), (180, 190, 200), np.uint8)
    for _ in range(400):
        x, y = rng.integers(0, n, 2); w, h = rng.integers(10, 120, 2)
        cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)), tuple(int(v) for v in rng.integers(90, 230, 3)), -1)
    return cv2.GaussianBlur(img, (5, 5), 0)


def render(sc, wall, p, r_wc, rng):
    u, v = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    dc = np.stack([(u - CX) / F, (v - CY) / F, np.ones_like(u)], -1).reshape(-1, 3)
    d = dc @ r_wc.T                                  # world directions, not unit: t is then depth along the axis
    t_obj, nor, uv = sc.hit(p, d)
    t_floor = np.where(d[:, 2] < 0, -p[2] / d[:, 2], np.inf)
    # a wall 4 m from the object, facing it
    cam_dir = np.array([np.cos(np.radians(-110)), np.sin(np.radians(-110)), 0.0])   # where the photos are taken from
    wn = cam_dir                                     # the wall faces the camera, 4 m behind the object
    w0 = -cam_dir * 4.0
    den = d @ wn
    t_wall = np.where(den < -1e-6, ((w0 - p) @ wn) / np.where(den < -1e-6, den, -1), np.inf)
    t = np.minimum(np.minimum(t_obj, t_floor), t_wall)
    img = np.zeros((H * W, 3), np.float32)
    fl = (t_floor <= t) & np.isfinite(t_floor)
    pf = p + d * np.where(fl, t_floor, 0)[:, None]
    fx = (np.mod(pf[:, 0] + 8, 4) / 4 * 2047).astype(int); fy = (np.mod(pf[:, 1] + 8, 4) / 4 * 2047).astype(int)
    img[fl] = sc.floor[fy[fl], fx[fl]]
    wl = (t_wall <= t) & np.isfinite(t_wall) & ~fl
    pw = p + d * np.where(wl, t_wall, 0)[:, None]
    ax = np.cross(wn, [0, 0, 1.0])
    wu = (np.mod(pw @ ax, 3) / 3 * 1023).astype(int); wv = (np.mod(pw[:, 2], 3) / 3 * 1023).astype(int)
    img[wl] = wall[wv[wl], wu[wl]]
    ob = np.isfinite(t_obj) & (t_obj <= t)
    tx = (np.mod(uv[:, 0], 1.0) * 1023).astype(int); ty = (np.mod(uv[:, 1], 1.0) * 1023).astype(int)
    light = np.array([0.35, -0.45, 0.82]); light /= np.linalg.norm(light)
    shade = 0.45 + 0.6 * np.clip(nor @ light, 0, 1)
    img[ob] = sc.tex[ty[ob], tx[ob]] * shade[ob, None]
    img = img.reshape(H, W, 3) + rng.normal(0, 2.0, (H, W, 3))
    depth = np.where(np.isfinite(t), t, 0).reshape(H, W).astype(np.float32)   # d has z = 1 in camera axes
    return np.clip(img, 0, 255).astype(np.uint8), ob.reshape(H, W), depth


def main(out, kind="box", seed=0, n=3):
    rng = np.random.default_rng(seed)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    sc = ss.Scene(kind, rng)
    wall = wall_texture(rng)
    truth = sc.truth()
    centre = np.array([0.02, -0.01, 0.08])
    shots = []
    for i in range(n):
        az = np.radians(-130 + 80 * i / max(1, n - 1) + rng.normal(0, 6))   # round the object, near its corners
        cam_h = rng.uniform(0.75, 1.15)
        down = np.radians(rng.uniform(38, 62))
        dist = (cam_h - centre[2]) / np.tan(down)
        p = np.array([dist * np.cos(az), dist * np.sin(az), cam_h])
        r_wc = look_at(p, centre + rng.normal(0, 0.03, 3), np.radians(rng.normal(0, 4)))
        img, ob, depth = render(sc, wall, p, r_wc, rng)
        name = f"{i:02d}"
        cv2.imwrite(str(out / f"photo_{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(str(out / f"mask_{name}.png"), ob.astype(np.uint8) * 255)
        cv2.imwrite(str(out / f"depth_{name}.png"), np.clip(depth * 1000, 0, 65535).astype(np.uint16))   # mm
        up_cam = r_wc.T @ np.array([0, 0, 1.0])                              # world up in camera axes
        ys, xs = np.nonzero(ob)
        shots.append({"photo": f"photo_{name}.jpg", "mask": f"mask_{name}.png", "depth_mm": f"depth_{name}.png",
                      "up": up_cam.tolist(), "camera_height_m": float(cam_h), "down_deg": float(np.degrees(down)),
                      "box": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]})
    meta = {"kind": kind, "size_cm": [round(v, 2) for v in truth], "width": W, "height": H,
            "fx": F, "fy": F, "cx": CX, "cy": CY, "photos": shots}
    (out / "truth.json").write_text(json.dumps(meta, indent=2))
    print(out, kind, "truth", [round(v, 1) for v in truth])


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 0
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 3
    a = [x for x in a if x not in (str(seed), str(n))]
    main(a[0], a[1] if len(a) > 1 else "box", seed, n)
