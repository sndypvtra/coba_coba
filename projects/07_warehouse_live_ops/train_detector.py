#!/usr/bin/env python3
"""#18, closed: a detector fine-tuned on this site, trained here on the CPU.

The zero-shot detector finds 69-79% of the people a busy camera shows and
about one forklift in six (README, "Accuracy"), and every safety number built
on forklifts inherits that. A site that installs cameras would label a few
hundred of its own frames and fine-tune; the synthetic recording already carries
those labels, and `export_dataset.py` turns them into a training set.

This trains the smallest YOLO11 on that set (every camera, one frame every 5 s,
the last minute for validation, both scored windows left out entirely) and
compiles it to OpenVINO. On 4 CPU cores it takes about an hour, so it is kept
short: six epochs, backbone frozen, 960 px input. `detect.py --detector site`
then runs it in place of the zero-shot model, and main.py scores both on the
windows neither ever saw in training.

    python export_dataset.py        # once: the training set
    python train_detector.py        # ~1 h on CPU, minutes on a GPU
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import OUTPUT, WEIGHTS, output_dir  # noqa: E402

BASE = "yolo11n.pt"
BASE_URL = f"https://github.com/ultralytics/assets/releases/download/v8.4.0/{BASE}"
DATA = OUTPUT / "training_sets" / "semua_cctv" / "data.yaml"
SETTINGS = dict(epochs=6, imgsz=960, batch=8, freeze=10, close_mosaic=2, workers=3, cache="ram",
                device="cpu", val=False, plots=False, amp=False, seed=0, deterministic=True)
TARGET = WEIGHTS / "site_detector_warehouse_000"


def base_weights() -> Path:
    """The COCO-pretrained starting point, fetched from the release URL directly."""
    import urllib.request
    WEIGHTS.mkdir(exist_ok=True)
    path = WEIGHTS / BASE
    if not path.exists():
        part = path.with_suffix(".part")
        urllib.request.urlretrieve(BASE_URL, part)
        part.replace(path)
    return path


def _train_minutes(results_csv: Path, t0: float) -> float:
    """Training time over every session of the run, else this session's.

    results.csv keeps a running time per epoch, which starts again from zero
    when an interrupted run is resumed - so each session's last value is added.
    """
    try:
        import csv
        times = [float(r["time"]) for r in csv.DictReader(results_csv.open())]
        total = sum(a for a, b in zip(times, times[1:]) if b < a) + times[-1]
        return round(total / 60, 1)
    except (OSError, KeyError, ValueError, IndexError):
        return round((time.time() - t0) / 60, 1)


def train(resume: bool = False) -> dict:
    from ultralytics import YOLO
    if not DATA.exists():
        raise SystemExit(f"{DATA} missing: run export_dataset.py first")
    runs = OUTPUT / "training_runs"
    best = runs / "site_detector" / "weights" / "last.pt"
    t0 = time.time()
    if resume and best.exists():
        # carries on from the last finished epoch, with the settings it was started with
        YOLO(str(best)).train(resume=True)
    else:
        model = YOLO(str(base_weights()))
        model.train(data=str(DATA), project=str(runs), name="site_detector", exist_ok=True,
                    verbose=False, **SETTINGS)
    TARGET.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, TARGET / "site_detector.pt")
    exported = Path(YOLO(str(TARGET / "site_detector.pt")).export(
        format="openvino", imgsz=SETTINGS["imgsz"], dynamic=False, verbose=False))
    dst = TARGET / "site_detector_openvino_model"     # ultralytics knows the format by this suffix
    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(exported), str(dst))
    summary = json.loads((OUTPUT / "training_sets" / "summary.json").read_text())
    info = {"base": BASE, "settings": {k: v for k, v in SETTINGS.items() if k not in ("workers", "cache")},
            "training_set": summary["sets"]["semua CCTV"], "held_out_frames": summary["held_out_frames"],
            "minutes_on_cpu": _train_minutes(runs / "site_detector" / "results.csv", t0),
            "weights": str(dst.relative_to(WEIGHTS.parent))}
    (output_dir("warehouse_000") / "site_detector.json").write_text(json.dumps(info, indent=1, ensure_ascii=False))
    print(json.dumps(info, indent=1, ensure_ascii=False))
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run from its last epoch")
    train(ap.parse_args().resume)
    return 0


if __name__ == "__main__":
    sys.exit(main())
