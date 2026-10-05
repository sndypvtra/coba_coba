#!/usr/bin/env python3
"""APD: helmet and vest on every tracked person, from Ultralytics' Construction-PPE.

The detector. Ultralytics publishes Construction-PPE (1,132 training photos of
construction workers, labelled helmet, vest and nine more classes). YOLO11n is
fine-tuned on it here, on the CPU, and compiled to OpenVINO.

Where it looks. A helmet on a person 100 px tall in a 1920 x 1080 CCTV frame
is about twelve pixels - nothing a detector reading the whole frame can find.
So every person box the pipeline already tracks is cut out with a margin,
scaled up, and the PPE detector reads that crop instead, where a helmet is the
size it learned on. A helmet or vest box belongs to the person whose head or
torso it sits on, and only when no other person in the frame is nearer.

A vest needs a second opinion. Trained on construction photos, the detector
also takes a striped hoodie or a yellow T-shirt for a vest. CLIP (ViT-B/32) is
asked which of nine garments the person wears, in plain words; the two
safety-vest descriptions together must reach CLIP_VEST.

Too small to judge. Under MIN_PERSON_PX the detector found none of the helmets
in the by-eye check, so such a person is not judged at all (grey), and neither
is one cut by the frame's top edge.

Over time. One frame's answer is noisy (a head turned away, an arm across a
vest), so a person's status is the majority of their judged frames over the
last two seconds, and over the whole window for the summary - per tracked
identity, so a person keeps one status from camera to camera.

The check by eye. The recordings carry no PPE labels. Random crops are drawn
(--audit), a person labels them from a sheet that shows no AI verdict, and the
labels are stored beside the crops; only then is the AI scored against them.
The "calibration" sample set the rules above; the "check" sample, drawn and
labelled after the rules were fixed, is the measurement.

    python ppe.py --train                       # Construction-PPE, fine-tune YOLO11n (~40 min on 4 cores)
    python ppe.py --video 2 --video 3 --audit   # evidence per person crop, cached; the audit sheets and scores
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INPUT, OUTPUT, STRIDE, WEIGHTS, output_dir  # noqa: E402

DATA_DIR = INPUT / "construction-ppe"
DATA_URL = "https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip"
NAMES = ["helmet", "gloves", "vest", "boots", "goggles", "none", "Person", "no_helmet", "no_goggle",
         "no_gloves", "no_boots"]
HELMET, VEST = NAMES.index("helmet"), NAMES.index("vest")
SETTINGS = dict(epochs=12, imgsz=640, batch=16, freeze=10, close_mosaic=2, workers=3, cache="ram",
                device="cpu", plots=False, amp=False, seed=0, deterministic=True)
TARGET = WEIGHTS / "ppe_detector"
CROP_SIZE = 320          # crops are read at this size (the person fills most of it)
MARGIN = 0.12            # crop margin around the person box, as a share of its height
CONF = 0.30              # a helmet / vest box below this score is not evidence
# Calibration sample, video 2: of the people under 100 px wearing a helmet the
# detector found 0 of 8, of those over it 8 of 8 (and white vests: 1 of 8 under).
MIN_PERSON_PX = 100
CLIP_MODEL = "ViT-B/32"  # OpenAI CLIP via the ultralytics/CLIP package; ~340 MB, downloaded on first use
GARMENTS = ("a high-visibility safety vest", "a reflective safety vest", "a t-shirt", "a hoodie", "a jacket",
            "a sweater", "a shirt", "overalls", "a long-sleeve top")
VEST_WORDS = 2           # the first two garments are the vest
# Calibration sample: the six real-warehouse "vests" (striped hoodie, yellow
# T-shirt, red jacket) got 0.00-0.12 from CLIP, the simulation's vests 0.08-0.99.
CLIP_VEST = 0.20


# ------------------------------------------------------------------ training
def fetch() -> Path:
    """The dataset, downloaded and unpacked into input/construction-ppe (178 MB)."""
    if (DATA_DIR / "images" / "train").exists():
        return DATA_DIR
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    z = DATA_DIR / "construction-ppe.zip"
    urllib.request.urlretrieve(DATA_URL, z)
    with zipfile.ZipFile(z) as f:
        f.extractall(DATA_DIR)
    z.unlink()
    return DATA_DIR


def data_yaml() -> Path:
    root = fetch()
    y = root / "data_local.yaml"
    y.write_text(f"path: {root.resolve()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n"
                 + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)))
    return y


def _epochs_done(results_csv: Path) -> int:
    try:
        return max(0, len(results_csv.read_text().strip().splitlines()) - 1)
    except OSError:
        return 0


def train() -> dict:
    """Fine-tune, then score on the test split and compile for the CPU.

    A run that already finished all its epochs is not trained again (delete
    output/training_runs/ppe_detector to start over); only the test and the
    export are redone.
    """
    from ultralytics import YOLO
    from train_detector import base_weights, _train_minutes
    y = data_yaml()
    runs = OUTPUT / "training_runs"
    run = runs / "ppe_detector"
    t0 = time.time()
    if _epochs_done(run / "results.csv") < SETTINGS["epochs"] or not (run / "weights" / "best.pt").exists():
        YOLO(str(base_weights())).train(data=str(y), project=str(runs), name="ppe_detector", exist_ok=True,
                                        verbose=False, **SETTINGS)
    TARGET.mkdir(parents=True, exist_ok=True)
    shutil.copy(run / "weights" / "best.pt", TARGET / "ppe_detector.pt")
    model = YOLO(str(TARGET / "ppe_detector.pt"))
    # the held-out test split, never used in training or for choosing the epoch
    m = model.val(data=str(y), split="test", imgsz=SETTINGS["imgsz"], device="cpu", plots=False, verbose=False)
    per_class = {NAMES[int(c)]: {"precision": round(float(p), 3), "recall": round(float(r), 3),
                                 "mAP50": round(float(a50), 3)}
                 for c, p, r, a50 in zip(m.box.ap_class_index, m.box.p, m.box.r, m.box.ap50)}
    dst = TARGET / "ppe_detector_openvino_model"
    if dst.exists():
        shutil.rmtree(dst)
    # Ultralytics writes the export beside the weights, which is already where it belongs
    exported = Path(model.export(format="openvino", imgsz=CROP_SIZE, dynamic=False, verbose=False))
    if exported.resolve() != dst.resolve():
        shutil.move(str(exported), str(dst))
    info = {"dataset": "Ultralytics Construction-PPE (AGPL-3.0): 1,132 train / 143 val / 141 test photos",
            "base": "yolo11n.pt", "settings": {k: v for k, v in SETTINGS.items() if k not in ("workers", "cache")},
            "minutes_on_cpu": _train_minutes(runs / "ppe_detector" / "results.csv", t0),
            "test_split": {"mAP50_all": round(float(m.box.map50), 3), "per_class": per_class},
            "crop_inference_size": CROP_SIZE}
    (OUTPUT / "ppe_detector.json").write_text(json.dumps(info, indent=1, ensure_ascii=False))
    print(json.dumps(info, indent=1, ensure_ascii=False))
    return info


# ----------------------------------------------------------------- inference
def load_runtime():
    from ultralytics import YOLO
    target = TARGET / "ppe_detector_openvino_model"
    if not target.exists():
        raise SystemExit(f"{target} missing: run ppe.py --train first")
    return YOLO(str(target), task="detect")


def crop_box(box, w: int, h: int) -> tuple[int, int, int, int]:
    """The person box with a margin, made square-ish so the crop is not squashed."""
    x1, y1, x2, y2 = box
    bh = y2 - y1
    m = MARGIN * bh
    cx = (x1 + x2) / 2
    half_w = max((x2 - x1) / 2 + m, 0.3 * (bh + 2 * m))
    return (int(max(0, cx - half_w)), int(max(0, y1 - m)), int(min(w, cx + half_w)), int(min(h, y2 + m)))


def _owner(x: float, y: float, boxes: np.ndarray, torso: bool) -> int:
    """The person whose head (or torso) is nearest to the point, in body heights."""
    h = np.maximum(boxes[:, 3] - boxes[:, 1], 1)
    ax = (boxes[:, 0] + boxes[:, 2]) / 2
    ay = boxes[:, 1] + (0.40 if torso else 0.08) * h
    return int(np.argmin(np.hypot(x - ax, y - ay) / h))


def detector_evidence(model, frame: np.ndarray, boxes: np.ndarray, i: int) -> tuple[float, float]:
    """(helmet, vest) for person i of the frame's person boxes: the best box on their head / torso."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = boxes[i]
    cx1, cy1, cx2, cy2 = crop_box(boxes[i], w, h)
    crop = frame[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return 0.0, 0.0
    r = model.predict(crop, imgsz=CROP_SIZE, conf=0.10, iou=0.5, verbose=False)[0].boxes
    if r is None or not len(r):
        return 0.0, 0.0
    ph, pw = max(y2 - y1, 1), x2 - x1
    out = [0.0, 0.0]
    for (a, b, c, d), s, k in zip(r.xyxy.cpu().numpy(), r.conf.cpu().numpy(), r.cls.cpu().numpy().astype(int)):
        if k not in (HELMET, VEST):
            continue
        mx, my = cx1 + (a + c) / 2, cy1 + (b + d) / 2          # in the frame
        if not x1 - 0.15 * pw <= mx <= x2 + 0.15 * pw:
            continue
        rel = (my - y1) / ph
        torso = k == VEST
        if not (0.15 <= rel <= 0.75 if torso else -0.15 <= rel <= 0.33):
            continue
        if _owner(mx, my, boxes, torso) != i:                  # someone else's helmet / vest
            continue
        out[int(torso)] = max(out[int(torso)], float(s))
    return out[0], out[1]


class VestCheck:
    """CLIP's share for "a safety vest" among nine garments, per person."""

    def __init__(self):
        import clip
        import torch
        self.torch = torch
        self.model, self.pre = clip.load(CLIP_MODEL, device="cpu")
        with torch.no_grad():
            t = self.model.encode_text(clip.tokenize([f"a photo of a person wearing {g}" for g in GARMENTS]))
        self.text = t / t.norm(dim=-1, keepdim=True)

    def __call__(self, frame: np.ndarray, boxes: np.ndarray) -> np.ndarray:
        from PIL import Image
        ims = []
        for x1, y1, x2, y2 in boxes:
            m = int(0.05 * (y2 - y1))
            crop = frame[max(0, int(round(y1)) - m):int(round(y2)) + m, max(0, int(round(x1)) - m):int(round(x2)) + m]
            ims.append(self.pre(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))))
        with self.torch.no_grad():
            f = self.model.encode_image(self.torch.stack(ims))
            f = f / f.norm(dim=-1, keepdim=True)
            p = (100 * f @ self.text.T).softmax(-1).numpy()
        return p[:, :VEST_WORDS].sum(1)


def worn(e) -> tuple[bool, bool]:
    """(helmet, vest) from one sighting's evidence row (helmet score, vest score, CLIP vest share)."""
    return bool(e[0] >= CONF), bool(e[1] >= CONF and e[2] >= CLIP_VEST)


def _window(video: int) -> tuple[str, dict, list[str]]:
    from scene import load_cameras
    scene = "warehouse_000" if video == 2 else "warehouse_027"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    win = sel["video2_one_camera"] if video == 2 else sel["video3_real"]
    cams = [win["camera"]] if video == 2 else sorted(load_cameras(scene))
    return scene, win, cams


def judged_rows(rows: np.ndarray, classes: list[str]) -> np.ndarray:
    """Person rows big enough to judge and not cut by the frame's top edge."""
    return (rows[:, 7] == classes.index("person")) & ((rows[:, 5] - rows[:, 3]) >= MIN_PERSON_PX) & (rows[:, 3] > 3)


def run_video(video: int) -> list[Path]:
    """Evidence for every person row of the cached detections the video uses, cached per camera.

    Rows: helmet score, vest score, CLIP vest share; NaN = not judged.
    """
    from detect import load_detections
    from scene import video_path
    scene, win, cams = _window(video)
    model, vest_check, paths = None, None, []
    for cid in cams:
        path = ppe_path(scene, cid, win["start_frame"], win["end_frame"])
        paths.append(path)
        if path.exists():
            continue
        model = model or load_runtime()
        vest_check = vest_check or VestCheck()
        rows, classes = load_detections(scene, cid, win["start_frame"], win["end_frame"])
        person = rows[:, 7] == classes.index("person")
        judge = judged_rows(rows, classes)
        out = np.full((len(rows), 3), np.nan, np.float32)
        by_frame: dict[int, list[int]] = {}
        for i in np.nonzero(person)[0]:
            by_frame.setdefault(int(rows[i, 0]), []).append(int(i))
        cap = cv2.VideoCapture(str(video_path(scene, cid)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, win["start_frame"])
        t0, n = time.time(), 0
        for f in range(win["start_frame"], win["end_frame"]):
            ok, img = cap.read()
            if not ok:
                break
            idx = by_frame.get(f, [])
            mine = [i for i in idx if judge[i]]
            if not mine:
                continue
            boxes = rows[idx, 2:6]
            for i in mine:
                out[i, :2] = detector_evidence(model, img, boxes, idx.index(i))
            out[mine, 2] = vest_check(img, rows[mine, 2:6])
            n += len(mine)
        cap.release()
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, out)
        print(f"  {cid}: {n} person crops judged in {time.time() - t0:.0f} s", flush=True)
    return paths


# ------------------------------------------------------------- per person
WINDOW_S = 2.0           # live status: majority of the judged frames in the last two seconds
MIN_JUDGED = 3           # fewer judged frames than this: not known yet
VIOLATION_S = 2.0        # without a helmet / vest for this long, continuously, is an event


def per_frame(res, detections: dict, evidence: dict, track_offset: int = 0) -> dict[int, dict[int, tuple]]:
    """frame -> global identity -> (helmet worn, vest worn) from its sightings in that frame.

    Each sighting is the person row (camera, frame, track id) of the cached
    detections; several cameras seeing one person combine by "any camera saw it".
    A sighting without a judgement (too small, cut at the top) contributes nothing.
    track_offset: what the run's detector added to these track ids (detect.track_offset).
    """
    index = {}
    for cid, (rows, classes) in detections.items():
        ev = evidence.get(cid)
        if ev is None:
            continue
        k = classes.index("person")
        for i in np.nonzero((rows[:, 7] == k) & (rows[:, 1] >= 0) & np.isfinite(ev[:, 0]))[0]:
            index[(cid, int(rows[i, 0]), int(rows[i, 1]) + track_offset)] = worn(ev[i])
    out: dict[int, dict[int, tuple]] = {}
    for f, blobs in res.blobs.items():
        for b in blobs:
            if b.cls != "person":
                continue
            ws = [index[(m.cam, f, m.track)] for m in b.members if (m.cam, f, m.track) in index]
            if ws:
                out.setdefault(f, {})[b.gid] = (any(h for h, _ in ws), any(v for _, v in ws))
    return out


def statuses(frames: list[int], judged: dict, fps: float) -> tuple[dict, dict, list]:
    """Live status per frame, the window's status per person, and violation events.

    live[frame][gid] = (helmet, vest), each True / False / None (not known yet).
    """
    hist: dict[int, list] = {}
    live, out_events, open_ = {}, [], {}
    n = int(round(WINDOW_S * fps))
    t0 = frames[0]
    step = frames[1] - frames[0] if len(frames) > 1 else 1
    for f in frames:
        for gid, hv in judged.get(f, {}).items():
            hist.setdefault(gid, []).append((f, hv))
        cur = {}
        for gid, h in hist.items():
            recent = [hv for g, hv in h if f - g < n * step]
            if len(recent) < MIN_JUDGED:
                continue
            cur[gid] = tuple(bool(np.mean([hv[k] for hv in recent]) >= 0.5) for k in (0, 1))
        live[f] = cur
        t = round((f - t0) / (fps * step), 1)
        for gid, (helm, vest) in cur.items():
            for what, ok in (("helm", helm), ("rompi", vest)):
                key = (gid, what)
                if not ok:
                    ev = open_.setdefault(key, {"gid": gid, "what": what, "start_t": t})
                    ev["end_t"] = t
                elif key in open_:
                    ev = open_.pop(key)
                    if ev["end_t"] - ev["start_t"] >= VIOLATION_S:
                        out_events.append(ev)
    out_events += [ev for ev in open_.values() if ev["end_t"] - ev["start_t"] >= VIOLATION_S]
    final = {}
    for gid, h in hist.items():
        if len(h) >= MIN_JUDGED:
            final[gid] = {"helmet": bool(np.mean([hv[0] for _, hv in h]) >= 0.5),
                          "vest": bool(np.mean([hv[1] for _, hv in h]) >= 0.5), "judged_frames": len(h)}
    return live, final, sorted(out_events, key=lambda e: e["start_t"])


def summary(final: dict, events: list) -> dict:
    n = len(final)
    return {"people_judged": n,
            "with_helmet": sum(v["helmet"] for v in final.values()),
            "with_vest": sum(v["vest"] for v in final.values()),
            "rule": f"people >= {MIN_PERSON_PX} px tall; helmet / vest box on the head / torso of the person "
                    f"crop at score >= {CONF}, and for a vest CLIP's safety-vest share >= {CLIP_VEST}; a person's "
                    f"status is the majority of their judged frames (live: the last {WINDOW_S:g} s); a violation "
                    f"is {VIOLATION_S:g} s or more without",
            "violations": events}


def ppe_path(scene: str, cam: str, start: int, end: int) -> Path:
    return output_dir(scene) / "ppe" / f"{cam}_{start}-{end}_s{STRIDE}.npy"


def load_evidence(scene: str, cam: str, start: int, end: int) -> np.ndarray | None:
    p = ppe_path(scene, cam, start, end)
    return np.load(p) if p.exists() else None


# ------------------------------------------------------------- the check by eye
SAMPLES = {"calibration": {2: 48, 3: 24}, "check": {2: 48, 3: 24}}
SEEDS = {"calibration": 0, "check": 1}


def audit_path(video: int, sample: str) -> Path:
    scene = "warehouse_000" if video == 2 else "warehouse_027"
    return output_dir(scene) / f"ppe_audit_{sample}.json"


def audit_sample(video: int, sample: str) -> list[dict]:
    """Random person crops of the video's window for the check by eye, fixed once drawn.

    At most two per tracked person. The calibration sample (drawn first, at
    the then 60 px floor) set the rules; the check sample is drawn from the
    crops the final rules judge, away from every calibration crop (not the
    same track within a second), and is the one that measures them.
    """
    from detect import load_detections
    path = audit_path(video, sample)
    if path.exists():
        return json.loads(path.read_text())["crops"]
    scene, win, cams = _window(video)
    avoid = []
    if sample == "check":
        cal = audit_path(video, "calibration")
        avoid = json.loads(cal.read_text())["crops"] if cal.exists() else []
    pool = []
    for cid in cams:
        rows, classes = load_detections(scene, cid, win["start_frame"], win["end_frame"])
        for i in np.nonzero(judged_rows(rows, classes) & (rows[:, 1] >= 0))[0]:
            f, tid = int(rows[i, 0]), int(rows[i, 1])
            if any(a["camera"] == cid and a["track"] == tid and abs(a["frame"] - f) <= 30 for a in avoid):
                continue
            pool.append({"camera": cid, "frame": f, "track": tid,
                         "box": [round(float(v), 1) for v in rows[i, 2:6]], "row": int(i)})
    rng = np.random.default_rng(SEEDS[sample])
    rng.shuffle(pool)
    picks, per_track = [], {}
    for p in pool:
        key = (p["camera"], p["track"])
        if per_track.get(key, 0) < 2:
            per_track[key] = per_track.get(key, 0) + 1
            picks.append(p)
        if len(picks) == SAMPLES[sample][video]:
            break
    path.write_text(json.dumps({"video": video, "sample": sample, "crops": picks, "labels": None}, indent=1))
    return picks


def _track_majority(rows: np.ndarray, ev: np.ndarray, i: int, video_fps: float) -> tuple[bool, bool] | None:
    """The live status of row i's track: majority of its judged frames in the WINDOW_S before it."""
    f, tid = rows[i, 0], rows[i, 1]
    near = np.nonzero((rows[:, 1] == tid) & (rows[:, 0] <= f) & (rows[:, 0] > f - WINDOW_S * video_fps)
                      & np.isfinite(ev[:, 0]))[0]
    if len(near) < MIN_JUDGED:
        return None
    w = np.array([worn(ev[j]) for j in near])
    return bool(w[:, 0].mean() >= 0.5), bool(w[:, 1].mean() >= 0.5)


def audit_score(video: int, sample: str) -> dict:
    """The AI against the by-eye labels of a sample's crops, per item (helmet, vest).

    Two readings: the single frame the crop is from, and the live status the
    video shows (majority of the person's judged frames in the last WINDOW_S).
    Crops a person could not label (null), and crops the rules do not judge
    (too small), are left out and counted.
    """
    from detect import load_detections
    from world import FPS
    scene, win, _ = _window(video)
    data = json.loads(audit_path(video, sample).read_text())
    labels = data.get("labels")
    if not labels:
        raise SystemExit(f"{audit_path(video, sample).name} has no labels yet: label its sheet by eye first")
    cache = {}
    for c in data["crops"]:
        if c["camera"] not in cache:
            cache[c["camera"]] = (load_detections(scene, c["camera"], win["start_frame"], win["end_frame"])[0],
                                  load_evidence(scene, c["camera"], win["start_frame"], win["end_frame"]))
    out = {"crops": len(labels)}
    for k, item in enumerate(("helmet", "vest")):
        for reading in ("frame", "live"):
            tp = tn = fp = fn = unknown = small = 0
            for c, lab in zip(data["crops"], labels):
                truth = lab[item]
                if truth is None:
                    continue
                rows, ev = cache[c["camera"]]
                if not np.isfinite(ev[c["row"], 0]):
                    small += 1
                    continue
                if reading == "frame":
                    said = worn(ev[c["row"]])[k]
                else:
                    st = _track_majority(rows, ev, c["row"], FPS * STRIDE)
                    if st is None:
                        unknown += 1
                        continue
                    said = st[k]
                tp += truth and said
                tn += (not truth) and (not said)
                fp += (not truth) and said
                fn += truth and (not said)
            n = tp + tn + fp + fn
            out[f"{item}_{reading}"] = {"labelled": n, "correct": tp + tn,
                                        "accuracy": round((tp + tn) / n, 3) if n else None,
                                        "worn_found": f"{tp}/{tp + fn}", "not_worn_found": f"{tn}/{tn + fp}",
                                        "false_alarm": fp, "missed": fn, "not_known_yet": unknown,
                                        "not_judged_too_small": small}
        out[f"{item}_unlabelled"] = sum(lab[item] is None for lab in labels)
    return out


def worn_shares(video: int) -> dict:
    """Share of all judged crops the AI calls helmet / vest, and the detector alone without CLIP's check.

    In the real recording nobody wears either (every audit crop says so), so
    there every one of these is a false alarm.
    """
    scene, win, cams = _window(video)
    ev = []
    for cid in cams:
        e = load_evidence(scene, cid, win["start_frame"], win["end_frame"])
        ev.append(e[np.isfinite(e[:, 0])])
    ev = np.concatenate(ev)
    w = np.array([worn(e) for e in ev])
    return {"judged_crops": int(len(ev)), "helmet": round(float(w[:, 0].mean()), 4),
            "vest": round(float(w[:, 1].mean()), 4), "vest_detector_alone": round(float((ev[:, 1] >= CONF).mean()), 4)}


def audit_sheet(video: int, sample: str, blind: bool = False) -> Path:
    """The sample's crops; with the AI's verdict and the by-eye label unless blind (for labelling)."""
    import draw as dr
    from config import DOCS
    from scene import video_path
    scene, win, _ = _window(video)
    data = json.loads(audit_path(video, sample).read_text())
    labels = data.get("labels") or [{"helmet": None, "vest": None}] * len(data["crops"])
    evs = {}
    cw, ch, cols = 196, 300, 8
    n = len(data["crops"])
    sheet = np.full((64 + ch * ((n + cols - 1) // cols), cw * cols, 3), dr.BG, np.uint8)
    T = dr.Texts()
    name = {"calibration": "sampel kalibrasi (aturan ditetapkan di sini)",
            "check": "sampel uji (diambil dan dilabel setelah aturan tetap)"}[sample]
    if blind:
        T.add(f"Video {video}, {name}: {n} potongan orang acak, untuk dilabel mata (tanpa putusan AI).",
              (10, 10), 16, dr.INK, True)
    else:
        T.add(f"Audit APD video {video}, {name}: {n} potongan orang acak. Atas: putusan AI pada frame itu. "
              f"Bawah: label mata.", (10, 10), 16, dr.INK, True)
        T.add("H = helm, R = rompi. Hijau = dipakai, merah = tidak, abu = tak dinilai (terlalu kecil) / tak bisa "
              "dipastikan mata. Bingkai merah = AI salah.", (10, 34), 14, dr.MUTED)
    caps = {}
    mark = {True: "ya", False: "tidak", None: "?"}
    for k, (c, lab) in enumerate(zip(data["crops"], labels)):
        cap = caps.setdefault(c["camera"], cv2.VideoCapture(str(video_path(scene, c["camera"]))))
        cap.set(cv2.CAP_PROP_POS_FRAMES, c["frame"])
        ok, img = cap.read()
        if not ok:
            continue
        x1, y1, x2, y2 = crop_box(c["box"], img.shape[1], img.shape[0])
        crop = img[y1:y2, x1:x2]
        s = min((cw - 12) / crop.shape[1], (ch - 66) / crop.shape[0])
        crop = cv2.resize(crop, (max(1, int(crop.shape[1] * s)), max(1, int(crop.shape[0] * s))),
                          interpolation=cv2.INTER_CUBIC)
        bx = [int((c["box"][0] - x1) * s), int((c["box"][1] - y1) * s), int((c["box"][2] - x1) * s),
              int((c["box"][3] - y1) * s)]
        cv2.rectangle(crop, (bx[0], bx[1]), (bx[2], bx[3]), dr.WARN if blind else dr.FAINT, 1)
        gx, gy = (k % cols) * cw, 64 + (k // cols) * ch
        ox = gx + (cw - crop.shape[1]) // 2
        sheet[gy + 28:gy + 28 + crop.shape[0], ox:ox + crop.shape[1]] = crop
        T.add(f"#{k + 1}", (gx + 8, gy + 7), 13, dr.MUTED, True)
        if blind:
            T.add(f"{c['camera'].replace('Camera_', 'CCTV ')} · {int(c['box'][3] - c['box'][1])} px",
                  (gx + 48, gy + 8), 11, dr.MUTED)
            continue
        if c["camera"] not in evs:
            evs[c["camera"]] = load_evidence(scene, c["camera"], win["start_frame"], win["end_frame"])
        e = evs[c["camera"]][c["row"]]
        said = worn(e) if np.isfinite(e[0]) else (None, None)
        wrong = any(lab[it] is not None and said[j] is not None and lab[it] != said[j]
                    for j, it in enumerate(("helmet", "vest")))
        if wrong:
            cv2.rectangle(sheet, (gx + 2, gy + 2), (gx + cw - 3, gy + ch - 3), dr.BAD, 2)
        T.add("AI", (gx + 52, gy + 7), 12, dr.MUTED, True)
        T.add("H", (gx + 76, gy + 6), 13, dr.INK, True, bg=dr.CHIP[said[0]], pad=2)
        T.add("R", (gx + 100, gy + 6), 13, dr.INK, True, bg=dr.CHIP[said[1]], pad=2)
        yb = gy + ch - 30
        T.add("mata", (gx + 8, yb + 2), 12, dr.MUTED, True)
        T.add("H", (gx + 52, yb), 13, dr.INK, True, bg=dr.CHIP[lab["helmet"]], pad=2)
        T.add("R", (gx + 76, yb), 13, dr.INK, True, bg=dr.CHIP[lab["vest"]], pad=2)
        T.add(f"{mark[lab['helmet']]}/{mark[lab['vest']]}", (gx + 100, yb + 2), 12, dr.MUTED)
    for cap in caps.values():
        cap.release()
    T.flush(sheet)
    # the labelling sheet is working material, kept beside the labels it produced
    out = output_dir(scene) / f"ppe_audit_{sample}_blind.jpg" if blind else DOCS / f"ppe_audit_video{video}_{sample}.jpg"
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--video", type=int, choices=[2, 3], action="append")
    ap.add_argument("--audit", action="store_true",
                    help="draw the audit samples, and score the AI against their by-eye labels once they exist")
    args = ap.parse_args()
    if args.train:
        train()
    for v in args.video or []:
        run_video(v)
        if not args.audit:
            continue
        scores = {}
        for sample in SAMPLES:
            audit_sample(v, sample)
            if not json.loads(audit_path(v, sample).read_text()).get("labels"):
                print(f"{audit_path(v, sample).name}: label the crops on {audit_sheet(v, sample, blind=True)} "
                      f"by eye and store them under \"labels\" first")
                continue
            print(audit_sheet(v, sample))
            scores[sample] = audit_score(v, sample)
        scores["all_crops_called_worn"] = worn_shares(v)
        scene = "warehouse_000" if v == 2 else "warehouse_027"
        (output_dir(scene) / "ppe_audit_score.json").write_text(json.dumps(scores, indent=1))
        print(json.dumps(scores, indent=1))
    if not args.train and not args.video:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
