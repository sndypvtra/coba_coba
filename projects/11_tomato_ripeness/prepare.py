"""Make the inspection clip: download and hold the camera still.

    python prepare.py            # -> input/tomato_lanes.mp4 (1920 x 1080, 29.97 fps, 4.4 s)

Source: Pexels 8675103, "Tomatoes on a moving conveyor belt", 1920 x 1080. The
camera drifts slowly (about 30 px over the clip), so ffmpeg vidstab in tripod
mode aligns every frame to the first and a 3 % zoom hides the moving edges.
"""
from __future__ import annotations

import subprocess
import urllib.request
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
URL = "https://videos.pexels.com/video-files/8675103/8675103-hd_1920_1080_30fps.mp4"
PAGE = "https://www.pexels.com/video/tomatoes-on-a-moving-conveyor-belt-8675103/"


def main():
    inp = HERE / "input"
    inp.mkdir(exist_ok=True)
    src, trf, out = inp / "src_8675103.mp4", inp / "stab.trf", inp / "tomato_lanes.mp4"
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if not src.exists():
        print("downloading", PAGE)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        src.write_bytes(urllib.request.urlopen(req).read())
    subprocess.run([ff, "-v", "error", "-y", "-i", str(src), "-vf",
                    f"vidstabdetect=shakiness=4:accuracy=15:tripod=1:result={trf}", "-f", "null", "-"], check=True)
    subprocess.run([ff, "-v", "error", "-y", "-i", str(src), "-vf",
                    f"vidstabtransform=input={trf}:tripod=1:optzoom=0:zoom=3:interpol=bicubic:crop=black",
                    "-c:v", "libx264", "-crf", "16", "-an", str(out)], check=True)
    trf.unlink(missing_ok=True)
    print("->", out)


if __name__ == "__main__":
    main()
