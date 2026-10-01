#!/usr/bin/env python3
"""Render the product mockup pages to 16:9 PNGs for the investor deck.

    python tools/build_mockups.py                 # all pages -> docs/mockup/
    python tools/build_mockups.py --only 01 03    # just these (by prefix)
    python tools/build_mockups.py --scale 1       # quick, low-resolution preview

Each page is a hand-built HTML/CSS/SVG document (tools/mockup/pages.py) drawn in
headless Chromium - the same engine the architecture diagram was checked with.
Fonts and icons are fetched once into tools/.mockup_cache and embedded, so a
page renders with no network after that. The one real image on these pages is
the dwell-time clip: the annotated still from project 05 and a raw frame of the
same clip for the zone editor.

Needs: a Chromium headless shell (CHROME env var, or the Playwright build), OpenCV + Pillow only
for the overview slide's thumbnails.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "mockup"))
import pages  # noqa: E402

# The headless *shell* gives an exact 1600x900 viewport; full Chromium in headless
# mode loses ~88 px to an emulated window frame and the page comes out cropped.
_SHELL = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell"
CHROME = os.environ.get("CHROME") or (_SHELL if Path(_SHELL).exists()
                                      else "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def render(html_path: Path, png_path: Path, scale: int) -> None:
    cmd = [CHROME] + ([] if "headless_shell" in CHROME else ["--headless"]) + [
           "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
           f"--force-device-scale-factor={scale}", "--window-size=1600,900",
           f"--screenshot={png_path}", "--virtual-time-budget=6000", f"file://{html_path}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not png_path.exists():
        sys.exit(f"render failed for {html_path.name}:\n{r.stderr[-800:]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "docs" / "mockup"))
    ap.add_argument("--work", default=os.environ.get("MOCKUP_WORK", str(HERE / ".mockup_cache" / "html")))
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--only", nargs="*", default=None, help="page-name prefixes, e.g. 01 03")
    a = ap.parse_args()

    out, work = Path(a.out), Path(a.work)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    for name, fn in pages.PAGES:
        if a.only and not any(name.startswith(p) for p in a.only):
            continue
        h = work / f"{name}.html"
        h.write_text(fn(), encoding="utf-8")
        render(h.resolve(), (out / f"{name}.png").resolve(), a.scale)
        print(f"  {name}.png")

    if not a.only or any("00".startswith(p) or p.startswith("00") for p in a.only):
        import base64
        import cv2
        thumbs = {}
        for name, _ in pages.PAGES:
            src = out / f"{name}.png"
            if not src.exists():
                sys.exit(f"overview needs {src.name}; render the pages first")
            im = cv2.resize(cv2.imread(str(src)), (480, 270), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 88])
            thumbs[name] = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
        h = work / "00-peta-halaman.html"
        h.write_text(pages.overview(thumbs), encoding="utf-8")
        render(h.resolve(), (out / "00-peta-halaman.png").resolve(), a.scale)
        print("  00-peta-halaman.png")


if __name__ == "__main__":
    main()
