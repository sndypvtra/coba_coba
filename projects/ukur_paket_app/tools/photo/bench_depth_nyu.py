"""How well each depth model gives the camera height above the floor (the photo mode's one AI number), on NYUv2 test:
real indoor photos, Kinect depth as truth, the floor labelled. Pictures turned to portrait (as the phone's)."""
import io, sys, json, time
import numpy as np, cv2, pyarrow.parquet as pq
import onnxruntime as ort

def load(path):
    for r in pq.read_table(path).to_pylist():
        rgb = cv2.imdecode(np.frombuffer(r["rgb"]["bytes"], np.uint8), cv2.IMREAD_COLOR)
        dep = cv2.imdecode(np.frombuffer(r["depth"]["bytes"], np.uint8), cv2.IMREAD_UNCHANGED).astype(np.float32) / 1000
        sem = np.round(cv2.imdecode(np.frombuffer(r["semantic"]["bytes"], np.uint8), cv2.IMREAD_UNCHANGED) / (65535 / 40)).astype(np.int32)
        yield r["id"], rgb, dep, sem

def rot(a): return np.ascontiguousarray(a[:, 140:500])        # upright portrait: centre crop 360 x 480

def yolo(sess):
    h, w = sess.get_inputs()[0].shape[2:]
    def f(bgr):
        x = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
        return sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0][0, 0]
    return f

def land(f):
    """The portrait picture turned back to landscape for the model, its depth turned to portrait again."""
    return lambda bgr: np.ascontiguousarray(np.rot90(f(np.ascontiguousarray(np.rot90(bgr, 1))), -1))

def dav2(sess, h, w):
    mean = np.array([0.485, 0.456, 0.406], np.float32); std = np.array([0.229, 0.224, 0.225], np.float32)
    def f(bgr):
        x = (cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255 - mean) / std
        return sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    return f

def moge(name, fov_x):
    import torch
    from moge.model.v2 import MoGeModel
    m = MoGeModel.from_pretrained(name).eval()
    def f(bgr):
        x = torch.tensor(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=torch.float32).permute(2, 0, 1) / 255
        with torch.no_grad():
            out = m.infer(x, fov_x=fov_x, resolution_level=5, use_fp16=False)
        d = out["depth"].numpy()
        return np.nan_to_num(d, nan=0.0, posinf=0.0)
    return f

def main(parquet, models):
    K0 = json.load(open(parquet.rsplit("/", 2)[0] + "/camera_params.json"))["intrinsics"]
    # turned 90 deg clockwise: x' = (480 - 1 - y), y' = x
    fx, fy, cx, cy = K0["fx"], K0["fy"], K0["cx"] - 140, K0["cy"]
    W, H = 360, 480
    v, u = np.mgrid[0:H, 0:W]
    R = np.stack([(u + 0.5 - cx) / fx, (v + 0.5 - cy) / fy, np.ones((H, W))], -1)
    res = {k: [] for k in models}; times = {k: [] for k in models}
    n = 0
    for id_, rgb, dep, sem in load(parquet):
        rgb, dep, sem = rot(rgb), rot(dep), rot(sem)
        floor = (sem == 2) & (dep > 0.2) & (dep < 8)
        if floor.sum() < 4000: continue
        P = R[floor] * dep[floor][:, None]
        # true floor plane (least squares, two trims)
        keep = np.ones(len(P), bool)
        for _ in range(3):
            c = P[keep].mean(0); _, _, vt = np.linalg.svd(P[keep] - c, full_matrices=False); nrm = vt[2]
            d = (P - c) @ nrm; keep = np.abs(d) < 0.03
        if nrm @ c > 0: nrm = -nrm                 # up: from the floor towards the camera
        h_true = float(-(nrm @ c))
        if not (0.4 < h_true < 2.5): continue
        down = np.degrees(np.arcsin(np.clip(-nrm[2], -1, 1)))
        n += 1
        for k, f in models.items():
            t0 = time.time(); z = f(rgb); times[k].append(time.time() - t0)
            z = cv2.resize(z.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
            hp = np.median(-(R[floor] @ nrm) * z[floor])
            res[k].append((h_true, hp, down))
    print(f"{n} test photos with enough floor; camera {np.median([r[0] for r in res[list(models)[0]]]):.2f} m above it (median)")
    print(f"{'model':28s} {'bias':>6s} {'after calibration: median err':>30s} {'p75':>6s} {'p90':>6s} {'max':>6s} {'ms/photo PC':>12s}")
    for k in models:
        a = np.array(res[k]); r = a[:, 1] / a[:, 0]
        b = np.median(r); e = np.abs(r / b - 1) * 100
        print(f"{k:28s} {b:6.2f} {np.median(e):29.1f}% {np.percentile(e, 75):5.1f}% {np.percentile(e, 90):5.1f}% {e.max():5.1f}% {1000 * np.median(times[k]):11.0f}")

if __name__ == "__main__":
    pq_path, ydir, ddir = sys.argv[1], sys.argv[2], sys.argv[3]
    o = ort.SessionOptions(); o.intra_op_num_threads = 4
    S = lambda p: ort.InferenceSession(p, o, providers=["CPUExecutionProvider"])
    models = {
        "YOLO26n portrait 640x480": yolo(S(f"{ydir}/yolo26n-depth_640x480.onnx")),
        "YOLO26l portrait 640x480": yolo(S(f"{ydir}/yolo26l-depth_640x480.onnx")),
        "DAv2-S fp32 portrait 280x378": dav2(S(f"{ddir}/dav2s_metric_indoor.onnx"), 378, 280),
        "DAv2-S int8 portrait 280x378": dav2(S(f"{ddir}/dav2s_metric_indoor_int8.onnx"), 378, 280),
        "DAv2-S fp32 portrait 364x490": dav2(S(f"{ddir}/dav2s_metric_indoor.onnx"), 490, 364),
    }
    if len(sys.argv) > 4:
        import math
        fov = math.degrees(2 * math.atan(240 / 519.47))            # portrait width 480, fx' = fy
        models["MoGe-2 ViT-S (known FOV)"] = moge("Ruicheng/moge-2-vits-normal", fov)
        if "big" in sys.argv[4:]: models["MoGe-2 ViT-L (known FOV)"] = moge("Ruicheng/moge-2-vitl-normal", fov)
    main(pq_path, models)
