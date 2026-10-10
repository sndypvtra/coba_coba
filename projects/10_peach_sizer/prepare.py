"""Download the inspection clip.

    python prepare.py            # -> input/peach_sizer.mp4 (1920 x 1080, 29.97 fps, 8.1 s)

Source: Pexels 32642676, "Efficient peach sorting in food processing plant",
filmed from a fixed point over the infeed of a five-lane roller sizer. The
camera does not move, so the clip is used as it is.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "https://videos.pexels.com/video-files/32642676/13918786_1920_1080_30fps.mp4"
PAGE = "https://www.pexels.com/video/efficient-peach-sorting-in-food-processing-plant-32642676/"


def main():
    inp = HERE / "input"
    inp.mkdir(exist_ok=True)
    out = inp / "peach_sizer.mp4"
    if out.exists():
        print("already there:", out)
        return
    print("downloading", PAGE)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    out.write_bytes(urllib.request.urlopen(req).read())
    print("->", out)


if __name__ == "__main__":
    main()
