"""Calibrate YOLOE zero-shot text prompts against sample frames of each clip.

Runs several candidate prompt sets on a handful of frames per video and reports
how many boxes each set yields plus the confidence spread, so the production
pipeline can be configured with prompts that actually fire on this footage.
"""

import argparse
import warnings
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLOE

warnings.filterwarnings("ignore")

from factory_vision.paths import ROOT, VIDEO_DIR, WEIGHTS_DIR

CANDIDATES = {
    "01_oranges_production_line.mp4": [
        ["orange"],
        ["orange fruit"],
        ["orange", "fruit"],
        ["round orange fruit on conveyor roller"],
    ],
    "02_tomatoes_conveyor.mp4": [
        ["tomato"],
        ["red tomato"],
        ["tomato", "fruit"],
        ["ripe tomato on conveyor belt"],
    ],
    "03_packages_conveyor.mp4": [
        ["cardboard box"],
        ["box", "package"],
        ["cardboard box", "parcel", "plastic bag"],
        ["package"],
    ],
}


def probe(model: YOLOE, video: Path, prompt_sets, conf: float, imgsz: int, n_frames: int):
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idxs = [int(total * p) for p in np.linspace(0.15, 0.85, n_frames)]
    frames = []
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if ok:
            frames.append((i, fr))
    cap.release()

    print(f"\n=== {video.name} ({len(frames)} sample frames) ===")
    for names in prompt_sets:
        model.set_classes(names, model.get_text_pe(names))
        counts, confs = [], []
        for _, fr in frames:
            r = model.predict(fr, conf=conf, imgsz=imgsz, verbose=False)[0]
            counts.append(len(r.boxes))
            if len(r.boxes):
                confs.extend(r.boxes.conf.tolist())
        c = np.array(confs) if confs else np.array([0.0])
        print(
            f"  {str(names):58s} n/frame={np.mean(counts):5.1f} "
            f"(min {min(counts)}, max {max(counts)})  "
            f"conf mean={c.mean():.2f} p10={np.percentile(c,10):.2f} max={c.max():.2f}"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(WEIGHTS_DIR / "yoloe-11m-seg.pt"))
    ap.add_argument("--conf", type=float, default=0.05)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--frames", type=int, default=4)
    args = ap.parse_args()

    model = YOLOE(args.weights)
    for name, prompt_sets in CANDIDATES.items():
        video = VIDEO_DIR / name
        if video.exists():
            probe(model, video, prompt_sets, args.conf, args.imgsz, args.frames)
        else:
            print(f"skip missing {video}")


if __name__ == "__main__":
    main()
