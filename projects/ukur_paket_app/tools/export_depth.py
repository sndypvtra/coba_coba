"""Exports the depth model of the photo mode (UkurPaket 0.4.0): Ultralytics YOLO26n-depth (AGPL-3.0) to ONNX.

    pip install "ultralytics>=8.4.104" onnx
    python tools/export_depth.py app/src/main/assets/depth

Input 'images' [1, 3, 640, 480] (an upright 3:4 picture, RGB / 255, stretched to that size as Ultralytics does);
output 'output0' [1, 1, 640, 480], metres along the optical axis (the released global scale calibration is inside).
640 x 480 keeps the phone picture's shape (no stretching) at about the cost of a 512 x 512 input: ~0,05 s on a 4-core
PC, roughly 1,2-1,5 s on a Urovo DT50 (Snapdragon 660 class, CPU only). The photo mode only takes one number from it,
the camera's height above the floor, so the small model is enough.
"""
import os
import shutil
import sys
from pathlib import Path

from ultralytics import YOLO


def main(out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    m = YOLO("yolo26n-depth.pt")
    p = Path(m.export(format="onnx", imgsz=[640, 480], opset=18, simplify=False))
    dst = out / "yolo26n-depth-640x480.onnx"
    shutil.move(str(p), dst)
    print(dst, os.path.getsize(dst) // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "app/src/main/assets/depth")
