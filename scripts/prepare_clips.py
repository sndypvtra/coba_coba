"""Prepare the two source clips that cannot be used as downloaded.

- 04 cans: the Pexels asset is 2732x1440; downscale to 1920x1012 so encoding and
  the output file stay reasonable. Content is unchanged.
- 06 chocolate: the asset is a 30 s montage of five shots. Only frames 445-595
  are a continuous take of pralines on the cooling belt, which is the part that
  can be counted with one fixed line; the rest cuts between liquid chocolate,
  an enrober and a packed tray.

Idempotent - skips whatever is already built.
"""

from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
VIDEOS = ROOT / "videos"


def downscale(src: Path, dst: Path, size: tuple[int, int]) -> None:
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        out.write(cv2.resize(frame, size))
        n += 1
    cap.release()
    out.release()
    print(f"  {dst.name}: {n} frames at {size[0]}x{size[1]}")


def trim(src: Path, dst: Path, start: int, count: int) -> None:
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    n = 0
    for _ in range(count):
        ok, frame = cap.read()
        if not ok:
            break
        out.write(frame)
        n += 1
    cap.release()
    out.release()
    print(f"  {dst.name}: {n} frames from offset {start}")


def main() -> None:
    jobs = [
        ("04_cans_canning_line_RAW.mp4", "04_cans_canning_line.mp4", downscale, (1920, 1012)),
        ("06_chocolate_praline_line_RAW.mp4", "06_chocolate_praline_line.mp4", trim, (445, 150)),
    ]
    for raw_name, out_name, fn, arg in jobs:
        raw, out = VIDEOS / raw_name, VIDEOS / out_name
        if out.exists():
            print(f"  have {out_name}")
            continue
        if not raw.exists():
            print(f"  !! missing {raw_name}, run fetch_assets.sh first")
            continue
        if fn is downscale:
            downscale(raw, out, arg)
        else:
            trim(raw, out, *arg)


if __name__ == "__main__":
    main()
