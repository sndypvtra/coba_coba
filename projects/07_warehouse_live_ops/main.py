#!/usr/bin/env python3
"""Warehouse live ops PoC: every step after detection, run from the cache.

The order, once, on a fresh copy (each step skips work already done):

    python fetch_data.py                       # both recordings, ~3.6 GB
    python geometry_check.py                   # which cameras may be used at all
    python choose_windows.py                   # the 30 s and the cameras each video shows
    python detect.py --scene warehouse_000     # zero-shot detector, ~35 min on 4 CPU cores
    python export_dataset.py                   # #18: training set from the labels
    python train_detector.py                   # #18: fine-tune on it, ~1 h on CPU
    python detect.py --scene warehouse_000 --detector site
    python detect.py --survey warehouse_027    # pick the real recording's busiest 30 s
    python detect.py --scene warehouse_027     # ~15 min
    python main.py                             # floor, analytics, accuracy, videos
    python report.py                           # the accuracy picture
    python replay_3d.py                        # #20

    python main.py --only 1                    # just video 1 (or 2, 3)
    python main.py --detector zero_shot        # videos from the untrained detector alone

The synthetic recording is scored with every detector whose cache exists; the
videos use the one given by --detector: by default "hybrid", people from the
zero-shot detector and vehicles from the fine-tuned one, once both have run.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analytics as an  # noqa: E402
import evaluate as ev  # noqa: E402
import videos as V  # noqa: E402
import world as wd  # noqa: E402
from config import STRIDE, output_dir  # noqa: E402
from detect import DETECTORS, HYBRID, cache_path, load_detections, static_scores  # noqa: E402
from scene import FloorPlan, Labels, dataset_plan, load_cameras, video_path  # noqa: E402

SOURCE = {"warehouse_000": "NVIDIA PhysicalAI-SmartSpaces 2026 · Warehouse_000 (simulasi)",
          "warehouse_027": "NVIDIA PhysicalAI-SmartSpaces 2026 · Warehouse_027 (gudang asli)"}
DETECTOR_NAME = {"zero_shot": "detektor zero-shot", "site": "detektor dilatih di lokasi",
                 "hybrid": "orang: detektor zero-shot · kendaraan: detektor dilatih di lokasi"}
CHOICES = DETECTORS + ("hybrid",)
CLASSES = ["person", "forklift", "pallet_truck", "robot"]
ALERTS = ["near_miss", "speeding", "lane", "wrong_way", "idle", "crowd"]


def _json(path: Path, obj) -> None:
    def fix(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, indent=1, default=fix, ensure_ascii=False))


def _available(scene: str, cams: list[str], start: int, end: int, detector: str) -> bool:
    parts = sorted(set(HYBRID.values())) if detector == "hybrid" else [detector]
    return all(cache_path(scene, c, start, end, d).exists() for c in cams for d in parts)


def _floor(scene: str, cams: dict, used: list[str], frames: list[int], detector: str) -> dict:
    """Detections lifted, fused, followed, stitched and analysed: one pass of the pipeline.

    The background-likeness check that removes racks read as reach trucks is a
    patch for the zero-shot detector's vehicles; the fine-tuned one does not
    make that mistake, and with the check on it would also drop forklifts
    parked all window, which are real.
    """
    start, end = frames[0], frames[-1] + STRIDE
    dets = {c: load_detections(scene, c, start, end, detector) for c in used}
    static = {c: static_scores(scene, c, start, end, detector) for c in used} if detector == "zero_shot" else None
    by_frame, rejects = wd.lift_all({c: cams[c] for c in used}, dets, static)
    res = wd.track(frames, by_frame, rejects)
    joins = wd.stitch(res, stride=STRIDE)
    afr, summary = an.analyse(scene, res, dets, STRIDE)
    return {"detections": dets, "by_frame": by_frame, "rejects": rejects, "result": res,
            "joins": joins, "frames": afr, "summary": summary}


def _scores(run: dict, labels: Labels, used: list[str], frames: list[int],
            truth_seen: dict, truth_all: dict) -> dict:
    res = run["result"]
    return {
        "people_on_plan": ev.plan_accuracy(res, labels, used, "person"),
        "forklifts_on_plan": ev.plan_accuracy(res, labels, used, "forklift"),
        "pallet_trucks_on_plan": ev.plan_accuracy(res, labels, used, "pallet_truck"),
        "boxes_in_the_pictures": ev.detector_quality(run["detections"], labels, frames),
        "analytics_vs_truth": ev.analytics_vs_truth(run["summary"], truth_seen, truth_all),
    }


def _frames_json(path: Path, afr: list, res: wd.Result, cams: list[str]) -> None:
    """Every analysed frame, compact, for the 3D replay (#20) and anyone else.

    Object rows: id, class, x, y, heading, speed m/s, walking, alerts (bit i =
    ALERTS[i]), speed reliable, cameras that placed it (bit i = cams[i]).
    """
    out = {"fps": wd.FPS, "classes": CLASSES, "alerts": ALERTS, "cams": cams, "frames": []}
    for fr in afr:
        seen = {b.gid: b.cams for b in res.blobs.get(fr.frame, [])}
        rows = []
        for o in fr.objects:
            rows.append([o.gid, CLASSES.index(o.cls), round(o.x, 2), round(o.y, 2), round(o.heading, 2),
                         round(o.speed, 2), int(o.walking), sum(1 << i for i, a in enumerate(ALERTS) if a in o.alerts),
                         int(o.reliable), sum(1 << i for i, c in enumerate(cams) if c in seen.get(o.gid, ()))])
        out["frames"].append({"f": fr.frame, "t": fr.t, "o": rows,
                              "near": [[p, v, round(d, 2)] for p, v, d in fr.near_pairs]})
    path.write_text(json.dumps(out, separators=(",", ":")))


# ----------------------------------------------------------------- video 1
def run_video1(report: dict, detector: str, do_render: bool = True) -> None:
    scene = "warehouse_000"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    v1 = sel["video1_live_ops"]
    used = sel["candidates"]
    allcams = load_cameras(scene)
    cams = {c: allcams[c] for c in used}
    frames = list(range(v1["start_frame"], v1["end_frame"], STRIDE))
    labels = Labels(scene, list(allcams))
    truth_seen, truth_all = (an.analyse(scene, ev.truth_result(labels, frames, cams=c), {}, STRIDE)[1]
                             for c in (used, None))
    t0 = time.time()
    runs = {d: _floor(scene, allcams, used, frames, d) for d in CHOICES
            if _available(scene, used, frames[0], frames[-1] + STRIDE, d)}
    if detector not in runs:
        raise SystemExit(f"no {detector} detections for video 1: run detect.py --detector {detector}")
    run = runs[detector]
    res = run["result"]
    acc = _scores(run, labels, used, frames, truth_seen, truth_all)
    acc.update({
        "detector": detector,
        "#1_people_per_camera_vs_labels": ev.camera_counts(run["detections"], labels, frames),
        "#17_detection_per_camera": ev.per_camera_detection(run["detections"], labels, frames, cams),
        "#15_floor_coverage": ev.coverage(cams, dataset_plan(scene)),
        "person_height": ev.label_heights(res),
        "lift_rejections": {f"{c}: {r}": n for (c, r), n in sorted(run["rejects"].items())},
        "identities_joined_by_stitching": run["joins"],
        "camera_agreement": ev.camera_agreement(res.sightings, cams),
        "other_detector": {d: _scores(r, labels, used, frames, truth_seen, truth_all)
                           for d, r in runs.items() if d != detector},
    })
    print(f"  video 1 floor + analytics + accuracy ({', '.join(runs)}) in {time.time() - t0:.0f} s", flush=True)
    t0 = time.time()
    acc["#16_fewest_cameras"] = ev.fewest_cameras(frames, run["by_frame"], labels, used)
    print(f"  #16 fewest cameras in {time.time() - t0:.0f} s", flush=True)
    report["video1"] = {"window": v1, "analytics": run["summary"], "accuracy": acc,
                        "truth": {"seen_by_cameras": truth_seen, "whole_floor": truth_all}}
    _json(output_dir(scene) / "video1_live_ops.json", report["video1"])
    _frames_json(output_dir(scene) / "video1_frames.json", run["frames"], res, used)
    if do_render:
        ctx = {"scene": scene, "cams": allcams, "plan": dataset_plan(scene), "shown": v1["shown"],
               "used": used, "result": res, "frames": run["frames"], "summary": run["summary"],
               "detections": run["detections"], "stride": STRIDE, "video_path": lambda c: video_path(scene, c),
               "source_note": SOURCE[scene], "detector_note": DETECTOR_NAME[detector]}
        V.video_live_ops(ctx, output_dir(scene) / "video1_live_ops.mp4")


# ----------------------------------------------------------------- video 2
def run_video2(report: dict, detector: str, do_render: bool = True) -> None:
    scene = "warehouse_000"
    geo = json.loads((output_dir(scene) / "geometry.json").read_text())
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    v2 = sel["video2_one_camera"]
    cid = v2["camera"]
    allcams = load_cameras(scene)
    frames = list(range(v2["start_frame"], v2["end_frame"], STRIDE))
    if not _available(scene, [cid], frames[0], frames[-1] + STRIDE, detector):
        raise SystemExit(f"no {detector} detections for video 2: run detect.py --detector {detector}")
    labels = Labels(scene, list(allcams))
    run = _floor(scene, allcams, [cid], frames, detector)
    res, dets = run["result"], run["detections"]
    rows, classes = dets[cid]
    k = classes.index("person")
    lab = labels.boxes_in(cid, frames=np.array(frames), kind="Person")
    lab = lab[(lab[:, 10] - lab[:, 8]) >= 40]
    series = []
    for f in frames:
        r = rows[(rows[:, 0] == f) & (rows[:, 7] == k) & (rows[:, 1] >= 0)]
        series.append((int(((r[:, 5] - r[:, 3]) >= 40).sum()), int((lab[:, 0] == f).sum())))
    truth_seen = an.analyse(scene, ev.truth_result(labels, frames, cams=[cid]), {}, STRIDE)[1]
    truth_all = an.analyse(scene, ev.truth_result(labels, frames), {}, STRIDE)[1]
    acc = {"detector": detector,
           "#1_count_vs_labels": ev.camera_counts(dets, labels, frames)[cid],
           "people_on_plan_from_this_camera": ev.plan_accuracy(res, labels, [cid], "person"),
           "boxes_in_the_picture": ev.detector_quality(dets, labels, frames),
           "analytics_vs_truth": ev.analytics_vs_truth(run["summary"], truth_seen, truth_all)}
    report["video2"] = {"window": v2, "analytics": run["summary"], "accuracy": acc}
    _json(output_dir(scene) / "video2_one_camera.json", report["video2"])
    if do_render:
        ctx = {"scene": scene, "cams": allcams, "plan": dataset_plan(scene), "camera": cid,
               "result": res, "frames": run["frames"], "summary": run["summary"], "detections": dets,
               "stride": STRIDE, "video_path": lambda c: video_path(scene, c), "source_note": SOURCE[scene],
               "count_series": series, "geometry": geo["cameras"][cid], "detector_note": DETECTOR_NAME[detector]}
        V.video_one_camera(ctx, output_dir(scene) / "video2_one_camera.mp4")


# ----------------------------------------------------------------- video 3
def run_video3(report: dict, do_render: bool = True) -> None:
    scene = "warehouse_027"
    sel = json.loads((output_dir(scene) / "selection.json").read_text())
    v3 = sel["video3_real"]
    cams = load_cameras(scene)                 # only the cameras align_real.py verified, shifted
    used = sorted(cams)
    total = len(load_cameras(scene, aligned=False))
    apath = output_dir(scene) / "camera_alignment.json"
    alignment = json.loads(apath.read_text()) if apath.exists() else None
    frames = list(range(v3["start_frame"], v3["end_frame"], STRIDE))
    run = _floor(scene, cams, used, frames, "zero_shot")
    res, afr, summary = run["result"], run["frames"], run["summary"]
    agree = ev.camera_agreement(res.sightings, cams)
    heights = ev.label_heights(res)
    busiest = sorted(used, key=lambda c: -summary["#1_people_per_camera"][c]["mean"])[:4]
    plan = FloorPlan(cv2.imread(str(output_dir(scene) / "floor_plan.png")),
                     np.load(output_dir(scene) / "floor_plan_affine.npy"), True)
    pts = np.array([[o.x, o.y] for fr in afr for o in fr.objects]).reshape(-1, 2)
    if len(pts):
        x0, y0 = np.percentile(pts, 1, axis=0) - 3
        x1, y1 = np.percentile(pts, 99, axis=0) + 3
    else:
        x0, y0, x1, y1 = -10, -10, 10, 10
    span = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bounds = (cx - span / 2, cy - span / 2, cx + span / 2, cy + span / 2)
    report["video3"] = {"window": v3, "shown": busiest, "used": used, "cameras_total": total,
                        "analytics": summary,
                        "checks": {"camera_agreement": agree, "person_height": heights,
                                   "camera_alignment": alignment,
                                   "lift_rejections": {f"{c}: {r}": n for (c, r), n in
                                                       sorted(run["rejects"].items())}}}
    _json(output_dir(scene) / "video3_real.json", report["video3"])
    if do_render:
        ctx = {"scene": scene, "cams": cams, "plan": plan, "plan_bounds": bounds, "shown": busiest,
               "used": used, "result": res, "frames": afr, "summary": summary, "detections": run["detections"],
               "stride": STRIDE, "video_path": lambda c: video_path(scene, c),
               "source_note": SOURCE[scene], "agreement": agree["all_pairs"]["median_m"],
               "agreement_within": agree["all_pairs"]["within_0_5_m_pct"], "alignment": alignment,
               "cameras_total": total}
        V.video_real(ctx, output_dir(scene) / "video3_real.mp4")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, choices=[1, 2, 3], action="append")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--detector", choices=CHOICES, help="for videos 1 and 2 (default: hybrid once the "
                                                         "fine-tuned detector has run)")
    args = ap.parse_args()
    report = {}
    sel = json.loads((output_dir("warehouse_000") / "selection.json").read_text())
    v1 = sel["video1_live_ops"]
    detector = args.detector or ("hybrid" if _available("warehouse_000", sel["candidates"], v1["start_frame"],
                                                         v1["end_frame"], "hybrid") else "zero_shot")
    todo = args.only or [1, 2, 3]
    for n in todo:
        t0 = time.time()
        print(f"== video {n}" + (f" ({detector})" if n < 3 else ""), flush=True)
        if n == 1:
            run_video1(report, detector, not args.no_render)
        elif n == 2:
            run_video2(report, detector, not args.no_render)
        else:
            run_video3(report, not args.no_render)
        print(f"   done in {time.time() - t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
