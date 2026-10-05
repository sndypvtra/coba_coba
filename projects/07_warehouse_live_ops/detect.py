#!/usr/bin/env python3
"""Detection and per-camera tracking - the only expensive step, run once.

Every camera is read over the window it is needed for, every STRIDE-th frame,
through an open-vocabulary detector prompted with plain words ("person",
"forklift", ...), then a per-camera tracker. The result is a small table per
camera and window, cached under output/<scene>/detections/, so every later
step - lifting to the floor, fusion, analytics, rendering - can be rerun in
seconds without touching the model again.

    python detect.py --benchmark            # which model and input size, measured
    python detect.py --scene warehouse_000  # every window the videos need
    python detect.py --survey warehouse_027 # coarse pass to choose the real window
    python detect.py --scene warehouse_000 --detector site   # the fine-tuned model (train_detector.py)

Two detectors can fill the cache. "zero_shot" is YOLOE prompted with words and
example boxes - nothing trained on the site. "site" is YOLO11n fine-tuned on
this site's own labelled frames (#18), outside the scored windows; it exists
for the synthetic recording only, the one with labels to train on.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import STRIDE, WEIGHTS, output_dir  # noqa: E402
from scene import Labels, load_cameras, video_path  # noqa: E402

# What each class is called, or shown. People are found from the word alone.
# The site's vehicles are not: these are stand-up reach trucks and walkie
# stackers, and the word "forklift" finds 19% of them and "pallet jack" almost
# none (measured, detector_benchmark.json). So they are prompted *visually*,
# with a handful of example boxes - the way a site would be set up, with
# photos of its own equipment. The examples come from after the 200th second
# of the recording, outside every window that is scored or shown.
PROMPTS = {
    "warehouse_000": {"person": ("text", "person"),
                      "forklift": ("visual", "Forklift"),
                      "pallet_truck": ("visual", "PalletTruck")},
    "warehouse_027": {"person": ("text", "person"),
                      "robot": ("text", "small wheeled robot")},
}
EXAMPLES_FROM_FRAME = 6000
# Per-class floor on the score, from the precision/recall sweep in the README.
CONF = {"person": 0.20, "forklift": 0.40, "pallet_truck": 0.40, "robot": 0.30}
LABEL_KIND = {"person": "Person", "forklift": "Forklift", "pallet_truck": "PalletTruck"}

MODEL = "yoloe-11l-seg.pt"
IMGSZ = 1280

# The fine-tuned detector: its own input size and score floors, which a trained
# model's calibrated scores put higher than an open-vocabulary model's.
SITE_IMGSZ = 960
SITE_CONF = {"person": 0.25, "forklift": 0.20, "pallet_truck": 0.25}
DETECTORS = ("zero_shot", "site")
# What the videos use: each class from the detector that finds it best on frames
# neither saw in training (README, "Two detectors"). The zero-shot model finds
# more of the small, distant people; the fine-tuned one far more of the
# vehicles, and far fewer false ones.
HYBRID = {"person": "zero_shot", "forklift": "site", "pallet_truck": "site"}


# ------------------------------------------------------------------ the model
def _example_boxes(scene: str, kind: str, cams: list[str], n: int = 8) -> list[tuple]:
    """Clear, whole examples of one vehicle kind, one per camera, late in the recording."""
    labels = Labels(scene, list(load_cameras(scene)))
    out = []
    for cid in cams:
        b = labels.boxes_in(cid, kind=kind)
        b = b[(b[:, 0] >= EXAMPLES_FROM_FRAME) & ((b[:, 10] - b[:, 8]) >= 90)
              & (b[:, 7] > 5) & (b[:, 9] < 1915) & (b[:, 8] > 5) & (b[:, 10] < 1075)]
        if len(b):
            r = b[len(b) // 2]
            out.append((cid, int(r[0]), [float(v) for v in r[7:11]]))
        if len(out) == n:
            break
    return out


def visual_embedding(model, scene: str, examples: list[tuple]):
    """Average the visual-prompt embeddings of several example boxes."""
    import torch
    import torch.nn.functional as F
    from ultralytics.models.yolo.yoloe import YOLOEVPSegPredictor
    embs = []
    for cid, f, box in examples:
        cap = cv2.VideoCapture(str(video_path(scene, cid)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        cap.release()
        model.model.model[-1].nc = 1
        pred = YOLOEVPSegPredictor(overrides=dict(task="segment", mode="predict", imgsz=IMGSZ,
                                                  verbose=False, save=False, batch=1))
        pred.setup_model(model=model.model, verbose=False)
        pred.set_prompts({"bboxes": np.array([box]), "cls": np.array([0])})
        embs.append(F.normalize(pred.get_vpe(img).reshape(-1), dim=0))
    return F.normalize(torch.stack(embs).mean(0), dim=0)


def load_model(scene: str, name: str = MODEL):
    """YOLOE with this scene's vocabulary. Weights and the text encoder live in weights/.

    Note: YOLOE.set_classes() skips the update when the class *names* are
    unchanged, whatever the embeddings - so a visual prompt set under a name the
    model already had is silently ignored. The embeddings are therefore written
    straight into the model.
    """
    import torch
    import torch.nn.functional as F
    from ultralytics import YOLOE
    WEIGHTS.mkdir(exist_ok=True)
    here = os.getcwd()
    os.chdir(WEIGHTS)              # ultralytics downloads into the working directory
    try:
        model = YOLOE(name)
        classes = list(PROMPTS[scene])
        cache = output_dir(scene) / "prompt_embeddings.pt"
        if cache.exists():
            saved = torch.load(cache)
            emb, examples = saved["embeddings"], saved["examples"]
        else:
            rows, examples = [], {}
            cams = json.loads((output_dir(scene) / "geometry.json").read_text())["cameras"] \
                if (output_dir(scene) / "geometry.json").exists() else {}
            usable = sorted(c for c, v in cams.items() if v.get("passed", True))
            for c in classes:
                how, what = PROMPTS[scene][c]
                if how == "text":
                    rows.append(F.normalize(model.get_text_pe([what]).reshape(-1), dim=0))
                else:
                    examples[c] = _example_boxes(scene, what, usable)
                    rows.append(visual_embedding(model, scene, examples[c]))
            emb = torch.stack(rows)[None]
            torch.save({"embeddings": emb, "examples": examples, "classes": classes}, cache)
            (output_dir(scene) / "visual_prompt_examples.json").write_text(json.dumps(
                {c: [{"camera": cam, "frame": f, "box_xyxy": [round(v, 1) for v in b]}
                     for cam, f, b in ex] for c, ex in examples.items()}, indent=1))
        model.model.set_classes(classes, emb)
        model.predictor = None
    finally:
        os.chdir(here)
    return model


def predict(model, frame: np.ndarray, imgsz: int, conf_floor: float) -> np.ndarray:
    """Rows of x1, y1, x2, y2, score, class index."""
    r = model.predict(frame, imgsz=imgsz, conf=conf_floor, iou=0.5, verbose=False,
                      agnostic_nms=False, retina_masks=False)[0]
    b = r.boxes
    if b is None or not len(b):
        return np.zeros((0, 6), np.float32)
    return np.column_stack([b.xyxy.cpu().numpy(), b.conf.cpu().numpy(),
                            b.cls.cpu().numpy()]).astype(np.float32)


def keep_by_class(det: np.ndarray, classes: list[str], conf: dict | None = None) -> np.ndarray:
    if not len(det):
        return det
    conf = conf or CONF
    floor = np.array([conf[classes[int(c)]] for c in det[:, 5]])
    return det[det[:, 4] >= floor]


def drop_contained(det: np.ndarray, frac: float = 0.8) -> np.ndarray:
    """Remove a box mostly inside a stronger box of the same class.

    A raised camera often gives one box for a whole person and a second for
    their upper body. Overlap measured against the *smaller* box catches that
    pair, which ordinary IoU suppression does not, because the union is large.
    """
    if len(det) < 2:
        return det
    order = np.argsort(-det[:, 4])
    det = det[order]
    keep = np.ones(len(det), bool)
    area = (det[:, 2] - det[:, 0]) * (det[:, 3] - det[:, 1])
    for i in range(len(det)):
        if not keep[i]:
            continue
        j = np.arange(i + 1, len(det))
        j = j[keep[j] & (det[j, 5] == det[i, 5])]
        if not len(j):
            continue
        iw = np.clip(np.minimum(det[i, 2], det[j, 2]) - np.maximum(det[i, 0], det[j, 0]), 0, None)
        ih = np.clip(np.minimum(det[i, 3], det[j, 3]) - np.maximum(det[i, 1], det[j, 1]), 0, None)
        keep[j[(iw * ih) / np.maximum(np.minimum(area[i], area[j]), 1) > frac]] = False
    return det[keep]


# ---------------------------------------------------------------- the tracker
class _Boxes:
    """The minimal box container ultralytics' trackers read."""

    def __init__(self, det: np.ndarray):
        self.conf = det[:, 4]
        self.cls = det[:, 5]
        w, h = det[:, 2] - det[:, 0], det[:, 3] - det[:, 1]
        self.xywh = np.column_stack([det[:, 0] + w / 2, det[:, 1] + h / 2, w, h])
        self.xyxy = det[:, :4]

    def __len__(self):
        return len(self.conf)

    def __getitem__(self, i):
        out = _Boxes.__new__(_Boxes)
        out.conf, out.cls, out.xywh, out.xyxy = self.conf[i], self.cls[i], self.xywh[i], self.xyxy[i]
        return out


REID = "yolo26n-reid.onnx"


REID_URL = f"https://github.com/ultralytics/assets/releases/download/v8.4.0/{REID}"


def reid_model() -> str:
    """The person re-identification network TrackTrack uses for appearance.

    Fetched straight from the release URL: ultralytics' own downloader first asks
    the GitHub API which assets exist, and where that API is unreachable it
    gives up silently and the tracker fails later on a missing file.
    """
    import urllib.request
    WEIGHTS.mkdir(exist_ok=True)
    path = WEIGHTS / REID
    if not path.exists():
        part = path.with_suffix(".part")
        urllib.request.urlretrieve(REID_URL, part)
        part.replace(path)
    return str(path)


# TrackTrack's score gates (high, low, new track) per detector. Its published
# defaults (0.6, 0.25, 0.7) assume a fully trained detector; open-vocabulary
# scores sit much lower, and a six-epoch fine-tune in between.
GATES = {"zero_shot": (0.35, 0.12, 0.40), "site": (0.30, 0.10, 0.35)}


def new_tracker(fps: float, detector: str = "zero_shot"):
    """TrackTrack (CVPR 2025): motion, appearance, confidence and corner angle.

    The cameras are fixed, so camera-motion compensation is off - it only adds
    jitter when nothing moves. A lost track may re-bind on a looser gate
    (lost_match_thr), which is what carries a person through a few frames
    behind a rack upright.
    """
    from ultralytics.trackers import TRACKTRACK
    high, low, new = GATES[detector]
    args = SimpleNamespace(
        tracker_type="tracktrack",
        track_high_thresh=high, track_low_thresh=low, new_track_thresh=new,
        track_buffer=int(round(fps * 3)), match_thresh=0.7, lost_match_thr=0.9,
        iou_weight=0.5, reid_weight=0.5, conf_weight=0.1, angle_weight=0.05,
        penalty_p=0.2, penalty_q=0.4, reduce_step=0.05,
        tai_thr=0.55, min_track_len=3,
        gmc_method="none", with_reid=True, model=reid_model(), device="cpu")
    return TRACKTRACK(args)


def load_runtime(scene: str):
    """The scene's detector compiled to OpenVINO: 0.45 s a frame instead of 1.6.

    Export bakes the scene's prompts into the network, so there is one compiled
    model per scene. Outputs match the PyTorch model to within 0.02 in score.
    """
    import shutil
    from ultralytics import YOLO
    target = WEIGHTS / f"yoloe-11l_{scene}_openvino_model"
    if not target.exists():
        model = load_model(scene)
        here = os.getcwd()
        os.chdir(WEIGHTS)
        try:
            exported = Path(model.export(format="openvino", imgsz=IMGSZ, dynamic=False,
                                         verbose=False)).resolve()
        finally:
            os.chdir(here)
        shutil.move(str(exported), str(target))
    return YOLO(str(target), task="segment")


def load_site_runtime():
    """The fine-tuned detector from train_detector.py, compiled to OpenVINO."""
    from ultralytics import YOLO
    target = WEIGHTS / "site_detector_warehouse_000" / "site_detector_openvino_model"
    if not target.exists():
        raise SystemExit(f"{target} missing: run train_detector.py first")
    return YOLO(str(target), task="detect")


# ------------------------------------------------------------------ the runs
def cache_path(scene: str, cam: str, start: int, end: int, detector: str = "zero_shot") -> Path:
    d = output_dir(scene) / "detections"
    d.mkdir(exist_ok=True)
    tag = "" if detector == "zero_shot" else f"_{detector}"
    return d / f"{cam}_{start}-{end}_s{STRIDE}{tag}.npz"


def run_camera(model, classes: list[str], scene: str, cam: str, start: int, end: int,
               detector: str = "zero_shot") -> Path:
    """Detect and track one camera over [start, end), every STRIDE-th frame.

    Saved columns: frame, track id (-1 if the tracker did not confirm the box),
    x1, y1, x2, y2, score, class index.
    """
    out = cache_path(scene, cam, start, end, detector)
    if out.exists():
        return out
    imgsz, conf = (IMGSZ, CONF) if detector == "zero_shot" else (SITE_IMGSZ, SITE_CONF)
    cap = cv2.VideoCapture(str(video_path(scene, cam)))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    tracker = new_tracker(30.0 / STRIDE, detector)
    rows, times = [], []
    floor = min(conf[c] for c in classes)
    for f in range(start, end):
        ok, frame = cap.read()
        if not ok:
            break
        if (f - start) % STRIDE:
            continue
        t0 = time.time()
        det = drop_contained(keep_by_class(predict(model, frame, imgsz, floor), classes, conf))
        tracks = tracker.update(_Boxes(det), img=frame)
        times.append(time.time() - t0)
        # Keep every detection, with the track id where TrackTrack kept it. Its
        # rows are x1, y1, x2, y2, id, score, class, index-into-detections.
        tid = np.full(len(det), -1, np.int32)
        for t in np.asarray(tracks).reshape(-1, 8):
            i = int(t[7])
            if 0 <= i < len(det):
                tid[i] = int(t[4])
        for d, i in zip(det, tid):
            rows.append((f, i, *d[:4], d[4], d[5]))
    cap.release()
    arr = np.array(rows, np.float32).reshape(-1, 8)
    np.savez_compressed(out, rows=arr, classes=np.array(classes),
                        sec_per_frame=np.array(np.mean(times) if times else 0.0))
    print(f"    {cam} {start}-{end}: {len(arr)} boxes, {np.mean(times):.2f} s/frame", flush=True)
    return out


def load_detections(scene: str, cam: str, start: int, end: int,
                    detector: str = "zero_shot") -> tuple[np.ndarray, list[str]]:
    """Cached rows (frame, track id, x1, y1, x2, y2, score, class) and class names.

    "hybrid" is not a run of its own: it takes each class from the detector
    HYBRID names, with the second detector's track ids moved out of the
    first's range so the two never collide.
    """
    if detector == "hybrid":
        parts, classes = [], None
        for k, d in enumerate(sorted(set(HYBRID.values()))):
            rows, cls = load_detections(scene, cam, start, end, d)
            classes = classes or cls
            if cls != classes:
                raise ValueError(f"{d} classes {cls} != {classes}")
            want = [classes.index(c) for c, src in HYBRID.items() if src == d and c in classes]
            r = rows[np.isin(rows[:, 7], want)].copy()
            r[r[:, 1] >= 0, 1] += 100_000 * k
            parts.append(r)
        rows = np.concatenate(parts)
        return rows[np.argsort(rows[:, 0], kind="stable")], classes
    z = np.load(cache_path(scene, cam, start, end, detector))
    return z["rows"], list(z["classes"])


VEHICLES = ("forklift", "pallet_truck", "robot")


def long_run_background(scene: str, cam: str, n: int = 25) -> np.ndarray:
    """Median of n frames spread over the whole recording: the floor with nobody on it.

    A vehicle that moves at any point in the recording is absent from most of
    those frames and so absent from the median. A rack is in all of them.
    """
    path = output_dir(scene) / "detections" / f"{cam}_background.png"
    if path.exists():
        return cv2.imread(str(path))
    cap = cv2.VideoCapture(str(video_path(scene, cam)))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for i in np.linspace(0, total - 1, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, f = cap.read()
        if ok:
            frames.append(f)
    cap.release()
    bg = np.median(np.stack(frames), axis=0).astype(np.uint8)
    cv2.imwrite(str(path), bg)
    return bg


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float32).ravel()
    b = b.astype(np.float32).ravel()
    a -= a.mean()
    b -= b.mean()
    return float((a @ b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-6))


def static_scores(scene: str, cam: str, start: int, end: int, detector: str = "zero_shot") -> np.ndarray:
    """For every cached vehicle box, how much it looks like the empty-floor background.

    Normalised cross-correlation of the box against the same region of the
    long-run background, in grey. Measured on this recording: boxes the
    detector called "forklift" that were really racks score 0.99; forklifts
    that move score far lower. People are not scored (NaN) - they move.
    """
    path = cache_path(scene, cam, start, end, detector).with_suffix(".static.npy")
    if path.exists():
        return np.load(path)
    rows, classes = load_detections(scene, cam, start, end, detector)
    out = np.full(len(rows), np.nan, np.float32)
    want = [classes.index(c) for c in VEHICLES if c in classes]
    idx = np.nonzero(np.isin(rows[:, 7], want))[0]
    if len(idx):
        bg = cv2.cvtColor(long_run_background(scene, cam), cv2.COLOR_BGR2GRAY)
        cap = cv2.VideoCapture(str(video_path(scene, cam)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        frames_needed = set(rows[idx, 0].astype(int))
        by_frame: dict[int, list[int]] = {}
        for i in idx:
            by_frame.setdefault(int(rows[i, 0]), []).append(int(i))
        for f in range(start, end):
            ok, img = cap.read()
            if not ok:
                break
            if f not in frames_needed:
                continue
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            for i in by_frame[f]:
                x1, y1, x2, y2 = [int(round(v)) for v in rows[i, 2:6]]
                x1, y1 = max(x1, 0), max(y1, 0)
                x2, y2 = min(x2, g.shape[1]), min(y2, g.shape[0])
                if x2 - x1 < 6 or y2 - y1 < 6:
                    continue
                out[i] = _ncc(cv2.resize(g[y1:y2, x1:x2], (24, 48)), cv2.resize(bg[y1:y2, x1:x2], (24, 48)))
        cap.release()
    np.save(path, out)
    return out


# ------------------------------------------------------------- benchmark
def match(det: np.ndarray, gt: np.ndarray, thr: float = 0.5) -> tuple[int, int, int]:
    """Greedy IoU matching; returns true positives, detections, labels."""
    if not len(det) or not len(gt):
        return 0, len(det), len(gt)
    x1 = np.maximum(det[:, None, 0], gt[None, :, 0])
    y1 = np.maximum(det[:, None, 1], gt[None, :, 1])
    x2 = np.minimum(det[:, None, 2], gt[None, :, 2])
    y2 = np.minimum(det[:, None, 3], gt[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    a = (det[:, 2] - det[:, 0]) * (det[:, 3] - det[:, 1])
    b = (gt[:, 2] - gt[:, 0]) * (gt[:, 3] - gt[:, 1])
    iou = inter / (a[:, None] + b[None, :] - inter + 1e-9)
    tp, used = 0, set()
    for i in np.argsort(-det[:, 4]):
        j = int(np.argmax(np.where([k not in used for k in range(len(gt))], iou[i], -1)))
        if iou[i, j] >= thr and j not in used:
            used.add(j)
            tp += 1
    return tp, len(det), len(gt)


def benchmark(frames_per_cam: int = 6) -> dict:
    """Score the detector against the labels on the frames video 1 shows.

    Six frames from each of the four on-screen cameras, spread over the window.
    A detection counts when it overlaps a labelled box of its class at IoU 0.4
    or more; labelled boxes under 20 px tall are left out. "Clearly visible"
    keeps only labels at least 60 px tall and not cut by the frame edge, which
    separates "the model missed it" from "nobody could see it".
    """
    scene = "warehouse_000"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    v1 = sel["video1_live_ops"]
    labels = Labels(scene, list(load_cameras(scene)))
    picks = np.linspace(v1["start_frame"], v1["end_frame"] - 1, frames_per_cam).astype(int)
    frames = {}
    for cid in v1["shown"]:
        cap = cv2.VideoCapture(str(video_path(scene, cid)))
        for f in picks:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
            ok, img = cap.read()
            if ok:
                frames[(cid, int(f))] = img
        cap.release()
    classes = list(PROMPTS[scene])
    model = load_runtime(scene)
    t, stats = [], {c: [0, 0, 0, 0, 0] for c in classes}
    for (cid, f), img in frames.items():
        t0 = time.time()
        det = drop_contained(keep_by_class(predict(model, img, IMGSZ, 0.10), classes))
        t.append(time.time() - t0)
        for k, c in enumerate(classes):
            gt = labels.boxes_in(cid, frames=np.array([f]), kind=LABEL_KIND[c])
            gt = gt[(gt[:, 10] - gt[:, 8]) >= 20]
            clear = gt[((gt[:, 10] - gt[:, 8]) >= 60) & (gt[:, 7] > 3) & (gt[:, 9] < 1917)]
            tp, nd, ng = match(det[det[:, 5] == k], gt[:, 7:11], 0.4)
            tpc, _, ngc = match(det[det[:, 5] == k], clear[:, 7:11], 0.4)
            for i, v in enumerate((tp, nd, ng, tpc, ngc)):
                stats[c][i] += v
    res = {"model": MODEL, "imgsz": IMGSZ, "frames": len(frames),
           "sec_per_frame": round(float(np.median(t[1:])), 2),
           "classes": {c: {"recall": round(s[0] / max(s[2], 1), 3),
                           "precision": round(s[0] / max(s[1], 1), 3),
                           "recall_clearly_visible": round(s[3] / max(s[4], 1), 3),
                           "labels": s[2], "conf": CONF[c],
                           "prompt": PROMPTS[scene][c][0]} for c, s in stats.items()},
           # measured while choosing the set-up, on the same 24 frames
           "alternatives_measured": {
               "yoloe-11l @ 960, text prompts": {"sec_per_frame": 0.84, "person_recall": 0.519,
                                                 "forklift_recall": 0.176, "pallet_truck_recall": 0.091},
               "yoloe-11l @ 1280, text prompts": {"sec_per_frame": 1.54, "person_recall": 0.636,
                                                  "forklift_recall": 0.189, "pallet_truck_recall": 0.045},
               "yoloe-11m @ 1280, text prompts": {"sec_per_frame": 1.29, "person_recall": 0.563,
                                                  "forklift_recall": 0.014, "pallet_truck_recall": 0.076},
               "several words per vehicle": {"forklift_recall": 0.23, "forklift_precision": 0.586,
                                             "pallet_truck_recall": 0.0},
           }}
    (output_dir(scene) / "detector_benchmark.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return res


# -------------------------------------------------------------- what to run
def jobs(scene: str) -> list[tuple[str, int, int]]:
    """(camera, start, end) for every window a video needs."""
    if scene == "warehouse_000":
        sel = json.loads((output_dir(scene) / "selection.json").read_text())
        v1, v2 = sel["video1_live_ops"], sel["video2_one_camera"]
        todo = [(c, v1["start_frame"], v1["end_frame"]) for c in sel["candidates"]]
        todo.append((v2["camera"], v2["start_frame"], v2["end_frame"]))
        return todo
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    v3 = sel["video3_real"]
    # every camera, verified or not: align_real.py checks them against each other from these
    return [(c, v3["start_frame"], v3["end_frame"]) for c in sorted(load_cameras(scene, aligned=False))]


def survey(scene: str, every_s: float = 1.0) -> dict:
    """Count people once a second in every camera, to choose the real window."""
    classes = list(PROMPTS[scene])
    model = load_runtime(scene)
    cams = sorted(load_cameras(scene, aligned=False))
    counts = {}
    for cid in cams:
        cap = cv2.VideoCapture(str(video_path(scene, cid)))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        row = []
        for f in range(0, n, int(30 * every_s)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, img = cap.read()
            if not ok:
                break
            det = drop_contained(keep_by_class(predict(model, img, IMGSZ, 0.15), classes))
            row.append(int((det[:, 5] == 0).sum()))
        cap.release()
        counts[cid] = row
        print(f"  {cid}: {row}", flush=True)
    n = min(len(r) for r in counts.values())
    total = np.sum([r[:n] for r in counts.values()], axis=0)
    win = 30
    sums = np.convolve(total, np.ones(win), "valid")
    s = int(np.argmax(sums))
    start = s * 30
    sel = {"survey_people_per_second": counts,
           "video3_real": {"start_frame": start, "end_frame": start + 900, "stride": STRIDE,
                           "start_s": s, "end_s": s + win,
                           "people_counted_per_second_mean": round(float(sums[s] / win), 1),
                           "why": "the 30 s with the most people summed over all seven cameras, "
                                  "counted once a second"}}
    path = output_dir(scene) / "selection.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(sel)
    path.write_text(json.dumps(old, indent=1))
    return sel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--survey", choices=list(PROMPTS))
    ap.add_argument("--scene", choices=list(PROMPTS))
    ap.add_argument("--camera", action="append", help="only these cameras")
    ap.add_argument("--detector", choices=DETECTORS, default="zero_shot")
    args = ap.parse_args()
    if args.benchmark:
        benchmark()
        return 0
    if args.survey:
        survey(args.survey)
        return 0
    if args.scene:
        if args.detector == "site" and args.scene != "warehouse_000":
            raise SystemExit("the site detector is trained on warehouse_000's labels only")
        classes = list(PROMPTS[args.scene])
        model = load_runtime(args.scene) if args.detector == "zero_shot" else load_site_runtime()
        if args.detector == "site":
            names = [model.names[i] for i in sorted(model.names)]
            if names != classes:
                raise SystemExit(f"site detector classes {names} != {classes}")
        todo = jobs(args.scene)
        if args.camera:
            todo = [j for j in todo if j[0] in args.camera]
        print(f"{args.scene}: {len(todo)} camera windows ({args.detector})", flush=True)
        for cam, s, e in todo:
            run_camera(model, classes, args.scene, cam, s, e, args.detector)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
