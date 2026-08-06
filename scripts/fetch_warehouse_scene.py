#!/usr/bin/env python3
"""Fetch the warehouse scene used by case 6 and cut the clips it runs on.

Source: NVIDIA PhysicalAI-SmartSpaces on HuggingFace, CC BY 4.0, no gate and no
token needed.

    https://huggingface.co/datasets/nvidia/PhysicalAI-SmartSpaces

Four of Warehouse_014's twelve cameras are downloaded (about 520 MB in total),
each cut down to the 30-second window the case uses and subsampled to the
pipeline's frame rate. The full downloads are deleted afterwards unless --keep
is given, leaving four small clips in videos/ and the scene's calibration, map
and ground truth in videos/warehouse_014/.

    python scripts/fetch_warehouse_scene.py

Which four cameras, and why those: the dataset's banner image (demo.gif at the
repository root) is a 12-tile montage of this scene around its top-down view.
The four here are the tiles requested for this case - left block top-left and
bottom-left, right block top-left and bottom-right - identified by matching each
tile against the first frame of all twelve videos (best match 0.86-0.96,
next-best never above 0.44).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from factory_vision.paths import VIDEO_DIR  # noqa: E402
from factory_vision.spatial.config import SCENES  # noqa: E402

BASE = ("https://huggingface.co/datasets/nvidia/PhysicalAI-SmartSpaces"
        "/resolve/main/MTMC_Tracking_2025/train/Warehouse_014")
META = ["calibration.json", "map.png", "ground_truth.json"]


def download(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"  -> {dst.name}", flush=True)
    subprocess.run(["curl", "-fsSL", "-o", str(dst), url], check=True)


def cut(src: Path, dst: Path, start: int, window: int, stride: int, fps_out: float) -> int:
    """Write every `stride`-th frame of [start, start+window) to `dst`."""
    cap = cv2.VideoCapture(str(src))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    writer = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"mp4v"), fps_out, (w, h))
    written = 0
    for i in range(window):
        ok, frame = cap.read()
        if not ok:
            break
        if i % stride == 0:
            writer.write(frame)
            written += 1
    writer.release()
    cap.release()
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true",
                    help="keep the full-length source videos after cutting")
    ap.add_argument("--scene", default=SCENES[0].name)
    args = ap.parse_args()

    cfg = next(s for s in SCENES if s.name == args.scene)
    sdir = VIDEO_DIR / cfg.name
    raw = sdir / "raw"

    print(f"scene metadata -> {sdir}")
    for name in META:
        dst = sdir / name
        if not dst.exists():
            download(f"{BASE}/{name}", dst)

    print(f"videos ({len(cfg.views)} of 12 cameras)")
    for v in cfg.views:
        clip = VIDEO_DIR / v.filename
        if clip.exists():
            print(f"  == {clip.name} already cut")
            continue
        full = raw / f"{v.sensor_id}.mp4"
        if not full.exists():
            download(f"{BASE}/videos/{v.sensor_id}.mp4", full)
        n = cut(full, clip, cfg.start_frame, cfg.window_frames, cfg.stride, cfg.out_fps)
        print(f"  == {clip.name}: {n} frames at {cfg.out_fps:g} fps "
              f"({n / cfg.out_fps:.1f} s from source frame {cfg.start_frame})")

    if not args.keep and raw.exists():
        shutil.rmtree(raw)
        print("removed the full-length downloads (--keep to retain them)")


if __name__ == "__main__":
    main()
