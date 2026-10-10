"""Make the inspection clip: download, hold the camera still, cut the two chains out as 16:9.

    python prepare.py            # -> input/lime_chain.mp4 (1920 x 1080, 30 fps, 8.1 s)

Source: Pexels 32953325, "Lime sorting on conveyor belt in factory", filmed on a
phone held by hand (portrait, 1080 x 1920, 60 fps). Two steps make it usable as
a fixed inspection camera:

1. ffmpeg vidstab in tripod mode: every frame is aligned to the first, so the
   machine stays put and only the fruit moves.
2. A 1080 x 608 window over the two singulator chains, scaled to 1920 x 1080 and
   resampled to 30 fps.

The result is what a camera bolted above the chains would see, at a lower
sharpness than a real one (the window is upscaled 1.78 x).
"""
from __future__ import annotations

import subprocess
import urllib.request
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
URL = "https://videos.pexels.com/video-files/32953325/14044629_1080_1920_60fps.mp4"
PAGE = "https://www.pexels.com/video/lime-sorting-on-conveyor-belt-in-factory-32953325/"
CROP = "crop=1080:608:0:860"          # the two chains in the stabilised portrait frame


def main():
    inp = HERE / "input"
    inp.mkdir(exist_ok=True)
    src, trf, out = inp / "src_32953325.mp4", inp / "stab.trf", inp / "lime_chain.mp4"
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if not src.exists():
        print("downloading", PAGE)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        src.write_bytes(urllib.request.urlopen(req).read())
    subprocess.run([ff, "-v", "error", "-y", "-i", str(src), "-vf",
                    f"vidstabdetect=shakiness=8:accuracy=15:tripod=1:result={trf}", "-f", "null", "-"], check=True)
    subprocess.run([ff, "-v", "error", "-y", "-i", str(src), "-vf",
                    f"vidstabtransform=input={trf}:tripod=1:optzoom=0:zoom=6:interpol=bicubic:crop=black,"
                    f"{CROP},scale=1920:1080:flags=lanczos,fps=30,unsharp=5:5:0.6",
                    "-c:v", "libx264", "-crf", "16", "-an", str(out)], check=True)
    trf.unlink(missing_ok=True)
    print("->", out)


if __name__ == "__main__":
    main()
