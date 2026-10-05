#!/usr/bin/env python3
"""APD: helmet and vest on every tracked person, from Ultralytics' Construction-PPE.

The detector. Ultralytics publishes Construction-PPE (1,132 training photos of
construction workers, labelled helmet, vest, no_helmet and eight more classes).
YOLO11n is fine-tuned on it here, on the CPU, and compiled to OpenVINO.

Where it looks. A helmet on a person 60 px tall in a 1920 x 1080 CCTV frame is
about eight pixels - nothing a detector reading the whole frame can find. So
every person box the pipeline already tracks is cut out with a margin, scaled
up, and the PPE detector reads that crop instead: there the helmet is ~40 px,
the size it learned on. A helmet counts when its box sits on the head (top
third of the crop), a vest when it sits on the torso. A person under 60 px
tall, or cut by the frame's top edge, is not judged at all.

Over time. One frame's answer is noisy (a head turned away, an arm across a
vest), so a person's status is the majority of their judged frames over the
last two seconds, and over the whole window for the summary - per tracked
identity, so a person keeps one status from camera to camera.

    python ppe.py --train          # download Construction-PPE, fine-tune YOLO11n (~1 h on 4 cores)
    python ppe.py --video 2        # helmet/vest evidence for video 2's camera, cached
    python ppe.py --video 3        # and for the real warehouse's verified cameras
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
HELMET, VEST, NO_HELMET = NAMES.index("helmet"), NAMES.index("vest"), NAMES.index("no_helmet")
SETTINGS = dict(epochs=12, imgsz=640, batch=16, freeze=10, close_mosaic=2, workers=3, cache="ram",
                device="cpu", plots=False, amp=False, seed=0, deterministic=True)
TARGET = WEIGHTS / "ppe_detector"
CROP_SIZE = 320          # crops are read at this size (the person fills most of it)
MIN_PERSON_PX = 60       # shorter than this in the CCTV frame: too small to judge
MARGIN = 0.12            # crop margin around the person box, as a share of its height
CONF = 0.30              # a helmet / vest / no-helmet box below this score is not evidence


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


def train() -> dict:
    from ultralytics import YOLO
    from train_detector import base_weights, _train_minutes
    y = data_yaml()
    runs = OUTPUT / "training_runs"
    t0 = time.time()
    YOLO(str(base_weights())).train(data=str(y), project=str(runs), name="ppe_detector", exist_ok=True,
                                    verbose=False, **SETTINGS)
    best = runs / "ppe_detector" / "weights" / "best.pt"
    TARGET.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, TARGET / "ppe_detector.pt")
    model = YOLO(str(TARGET / "ppe_detector.pt"))
    # the held-out test split, never used in training or for choosing the epoch
    m = model.val(data=str(y), split="test", imgsz=SETTINGS["imgsz"], device="cpu", plots=False, verbose=False)
    per_class = {NAMES[int(c)]: {"precision": round(float(p), 3), "recall": round(float(r), 3),
                                 "mAP50": round(float(a50), 3)}
                 for c, p, r, a50 in zip(m.box.ap_class_index, m.box.p, m.box.r, m.box.ap50)}
    exported = Path(model.export(format="openvino", imgsz=CROP_SIZE, dynamic=False, verbose=False))
    dst = TARGET / "ppe_detector_openvino_model"
    if dst.exists():
        shutil.rmtree(dst)
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


def evidence(model, frame: np.ndarray, box) -> tuple[float, float, float]:
    """(helmet, vest, no_helmet) scores for one person: the best box of each on its head or torso."""
    h, w = frame.shape[:2]
    cx1, cy1, cx2, cy2 = crop_box(box, w, h)
    crop = frame[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return 0.0, 0.0, 0.0
    r = model.predict(crop, imgsz=CROP_SIZE, conf=0.10, iou=0.5, verbose=False)[0].boxes
    if r is None or not len(r):
        return 0.0, 0.0, 0.0
    xyxy, conf, cls = r.xyxy.cpu().numpy(), r.conf.cpu().numpy(), r.cls.cpu().numpy().astype(int)
    # where the person is inside the crop
    px1, py1, px2, py2 = box[0] - cx1, box[1] - cy1, box[2] - cx1, box[3] - cy1
    ph, pw = py2 - py1, px2 - px1
    out = {HELMET: 0.0, VEST: 0.0, NO_HELMET: 0.0}
    for (x1, y1, x2, y2), c, k in zip(xyxy, conf, cls):
        if k not in out:
            continue
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if not px1 - 0.15 * pw <= mx <= px2 + 0.15 * pw:
            continue
        rel = (my - py1) / max(ph, 1)
        on_head = -0.15 <= rel <= 0.33
        on_torso = 0.15 <= rel <= 0.75
        if (k in (HELMET, NO_HELMET) and on_head) or (k == VEST and on_torso):
            out[k] = max(out[k], float(c))
    return out[HELMET], out[VEST], out[NO_HELMET]


def run_video(video: int) -> list[Path]:
    """Evidence for every person row of the cached detections the video uses, cached per camera."""
    from detect import load_detections
    from scene import load_cameras, video_path
    scene = "warehouse_000" if video == 2 else "warehouse_027"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    win = sel["video2_one_camera"] if video == 2 else sel["video3_real"]
    cams = [win["camera"]] if video == 2 else sorted(load_cameras(scene))
    model, paths = None, []
    for cid in cams:
        path = ppe_path(scene, cid, win["start_frame"], win["end_frame"])
        paths.append(path)
        if path.exists():
            continue
        model = model or load_runtime()
        rows, classes = load_detections(scene, cid, win["start_frame"], win["end_frame"])
        k = classes.index("person")
        out = np.full((len(rows), 3), np.nan, np.float32)        # helmet, vest, no_helmet; NaN = not judged
        want = np.nonzero((rows[:, 7] == k) & ((rows[:, 5] - rows[:, 3]) >= MIN_PERSON_PX) & (rows[:, 3] > 3))[0]
        by_frame: dict[int, list[int]] = {}
        for i in want:
            by_frame.setdefault(int(rows[i, 0]), []).append(int(i))
        cap = cv2.VideoCapture(str(video_path(scene, cid)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, win["start_frame"])
        t0, n = time.time(), 0
        for f in range(win["start_frame"], win["end_frame"]):
            ok, img = cap.read()
            if not ok:
                break
            for i in by_frame.get(f, []):
                out[i] = evidence(model, img, rows[i, 2:6])
                n += 1
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
            index[(cid, int(rows[i, 0]), int(rows[i, 1]) + track_offset)] = ev[i]
    out: dict[int, dict[int, tuple]] = {}
    for f, blobs in res.blobs.items():
        for b in blobs:
            if b.cls != "person":
                continue
            evs = [index[(m.cam, f, m.track)] for m in b.members if (m.cam, f, m.track) in index]
            if evs:
                e = np.max(np.array(evs), axis=0)
                out.setdefault(f, {})[b.gid] = (bool(e[0] >= CONF), bool(e[1] >= CONF))
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
            "rule": f"helmet / vest box on the head / torso of the person crop at score >= {CONF}; a person's "
                    f"status is the majority of their judged frames (live: the last {WINDOW_S:g} s); a violation "
                    f"is {VIOLATION_S:g} s or more without",
            "violations": events}


def ppe_path(scene: str, cam: str, start: int, end: int) -> Path:
    return output_dir(scene) / "ppe" / f"{cam}_{start}-{end}_s{STRIDE}.npy"


def load_evidence(scene: str, cam: str, start: int, end: int) -> np.ndarray | None:
    p = ppe_path(scene, cam, start, end)
    return np.load(p) if p.exists() else None


AUDIT_N = {2: 48, 3: 24}


def audit_sample(video: int, seed: int = 0) -> list[dict]:
    """Random person crops of the video's window for the by-eye check, fixed once drawn.

    At most two per tracked person, at least MIN_PERSON_PX tall and not cut by
    the frame's top: the crops the detector is asked to judge. Stored in
    output/<scene>/ppe_audit.json; the labels a person gives them by eye go
    beside them in the same file.
    """
    from detect import load_detections
    from scene import load_cameras
    scene = "warehouse_000" if video == 2 else "warehouse_027"
    path = output_dir(scene) / "ppe_audit.json"
    if path.exists():
        return json.loads(path.read_text())["crops"]
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    win = sel["video2_one_camera"] if video == 2 else sel["video3_real"]
    cams = [win["camera"]] if video == 2 else sorted(load_cameras(scene))
    pool = []
    for cid in cams:
        rows, classes = load_detections(scene, cid, win["start_frame"], win["end_frame"])
        k = classes.index("person")
        ok = (rows[:, 7] == k) & (rows[:, 1] >= 0) & ((rows[:, 5] - rows[:, 3]) >= MIN_PERSON_PX) & (rows[:, 3] > 3)
        for i in np.nonzero(ok)[0]:
            pool.append({"camera": cid, "frame": int(rows[i, 0]), "track": int(rows[i, 1]),
                         "box": [round(float(v), 1) for v in rows[i, 2:6]], "row": int(i)})
    rng = np.random.default_rng(seed)
    rng.shuffle(pool)
    picks, per_track = [], {}
    for p in pool:
        key = (p["camera"], p["track"])
        if per_track.get(key, 0) < 2:
            per_track[key] = per_track.get(key, 0) + 1
            picks.append(p)
        if len(picks) == AUDIT_N[video]:
            break
    path.write_text(json.dumps({"video": video, "crops": picks, "labels": None}, indent=1))
    return picks


def _audit(video: int) -> tuple[str, dict, list[dict]]:
    scene = "warehouse_000" if video == 2 else "warehouse_027"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    win = sel["video2_one_camera"] if video == 2 else sel["video3_real"]
    data = json.loads((output_dir(scene) / "ppe_audit.json").read_text())
    return scene, win, data


def _track_majority(rows: np.ndarray, ev: np.ndarray, i: int, video_fps: float) -> tuple[bool, bool] | None:
    """The live status of row i's track: majority of its judged frames in the WINDOW_S before it."""
    f, tid = rows[i, 0], rows[i, 1]
    near = np.nonzero((rows[:, 1] == tid) & (rows[:, 0] <= f) & (rows[:, 0] > f - WINDOW_S * video_fps)
                      & np.isfinite(ev[:, 0]))[0]
    if len(near) < MIN_JUDGED:
        return None
    return bool(np.mean(ev[near, 0] >= CONF) >= 0.5), bool(np.mean(ev[near, 1] >= CONF) >= 0.5)


def audit_score(video: int) -> dict:
    """The AI against the by-eye labels of the audit crops, per item (helmet, vest).

    Two readings: the single frame the crop is from, and the live status the
    video shows (majority of the person's judged frames in the last WINDOW_S).
    Crops a person could not label (null) are left out and counted.
    """
    from detect import load_detections
    from world import FPS
    scene, win, data = _audit(video)
    labels = data.get("labels")
    if not labels:
        raise SystemExit(f"{scene}/ppe_audit.json has no labels yet")
    cache, out = {}, {"crops": len(labels)}
    rows_of = {}
    for c in data["crops"]:
        if c["camera"] not in cache:
            cache[c["camera"]] = (load_detections(scene, c["camera"], win["start_frame"], win["end_frame"])[0],
                                  load_evidence(scene, c["camera"], win["start_frame"], win["end_frame"]))
        rows_of[id(c)] = cache[c["camera"]]
    for k, item in enumerate(("helmet", "vest")):
        for reading in ("frame", "live"):
            tp = tn = fp = fn = unknown = 0
            for c, lab in zip(data["crops"], labels):
                truth = lab[item]
                if truth is None:
                    continue
                rows, ev = rows_of[id(c)]
                if reading == "frame":
                    said = bool(ev[c["row"], k] >= CONF)
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
            out[f"{item}_{reading}"] = {"labelled": n, "correct": tp + tn, "accuracy": round((tp + tn) / n, 3) if n else None,
                                        "worn_found": f"{tp}/{tp + fn}", "not_worn_found": f"{tn}/{tn + fp}",
                                        "false_alarm": fp, "missed": fn, "not_known_yet": unknown}
        out[f"{item}_unlabelled"] = sum(lab[item] is None for lab in labels)
    return out


def audit_sheet(video: int) -> Path:
    """The audit crops with the AI's verdict and the by-eye label, misses outlined in red."""
    import draw as dr
    from config import DOCS
    from scene import video_path
    scene, win, data = _audit(video)
    labels = data.get("labels") or [{"helmet": None, "vest": None}] * len(data["crops"])
    evs = {}
    cw, ch, cols = 196, 300, 8
    n = len(data["crops"])
    sheet = np.full((64 + ch * ((n + cols - 1) // cols), cw * cols, 3), dr.BG, np.uint8)
    T = dr.Texts()
    T.add(f"Audit APD video {video}: {n} potongan orang acak. Atas: putusan AI pada frame itu. "
          f"Bawah: label mata (dibuat sebelum melihat AI).", (10, 10), 16, dr.INK, True)
    T.add("H = helm, R = rompi. Hijau = dipakai, merah = tidak, abu = tak bisa dinilai. Bingkai merah = AI salah.",
          (10, 34), 14, dr.MUTED)
    caps = {}
    mark = lambda v: {True: "ya", False: "tidak", None: "?"}[v]
    for k, (c, lab) in enumerate(zip(data["crops"], labels)):
        if c["camera"] not in evs:
            evs[c["camera"]] = load_evidence(scene, c["camera"], win["start_frame"], win["end_frame"])
        e = evs[c["camera"]][c["row"]]
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
        cv2.rectangle(crop, (bx[0], bx[1]), (bx[2], bx[3]), dr.FAINT, 1)
        gx, gy = (k % cols) * cw, 64 + (k // cols) * ch
        ox = gx + (cw - crop.shape[1]) // 2
        sheet[gy + 28:gy + 28 + crop.shape[0], ox:ox + crop.shape[1]] = crop
        said = (bool(e[0] >= CONF), bool(e[1] >= CONF))
        wrong = any(lab[it] is not None and lab[it] != said[j] for j, it in enumerate(("helmet", "vest")))
        if wrong:
            cv2.rectangle(sheet, (gx + 2, gy + 2), (gx + cw - 3, gy + ch - 3), dr.BAD, 2)
        T.add(f"#{k + 1}", (gx + 8, gy + 7), 13, dr.MUTED, True)
        T.add("AI", (gx + 52, gy + 7), 12, dr.MUTED, True)
        T.add("H", (gx + 76, gy + 6), 13, dr.INK, True, bg=dr.CHIP[said[0]], pad=2)
        T.add("R", (gx + 100, gy + 6), 13, dr.INK, True, bg=dr.CHIP[said[1]], pad=2)
        yb = gy + ch - 30
        T.add("mata", (gx + 8, yb + 2), 12, dr.MUTED, True)
        T.add("H", (gx + 52, yb), 13, dr.INK, True, bg=dr.CHIP[lab["helmet"]], pad=2)
        T.add("R", (gx + 76, yb), 13, dr.INK, True, bg=dr.CHIP[lab["vest"]], pad=2)
        T.add(f"{mark(lab['helmet'])}/{mark(lab['vest'])}", (gx + 100, yb + 2), 12, dr.MUTED)
    for cap in caps.values():
        cap.release()
    T.flush(sheet)
    out = DOCS / f"ppe_audit_video{video}.jpg"
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--video", type=int, choices=[2, 3], action="append")
    ap.add_argument("--audit", action="store_true",
                    help="score the AI against the by-eye labels of the audit crops, and draw the audit sheet")
    args = ap.parse_args()
    if args.train:
        train()
    for v in args.video or []:
        run_video(v)
        if args.audit:
            audit_sample(v)
            print(audit_sheet(v))
            score = audit_score(v)
            scene = "warehouse_000" if v == 2 else "warehouse_027"
            (output_dir(scene) / "ppe_audit_score.json").write_text(json.dumps(score, indent=1))
            print(json.dumps(score, indent=1))
    if not args.train and not args.video:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
