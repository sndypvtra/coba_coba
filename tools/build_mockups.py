#!/usr/bin/env python3
"""Render the product mockup pages for the investor deck, as PNG and as SVG.

    python tools/build_mockups.py                 # all pages -> docs/mockup/ (+ docs/mockup/svg/)
    python tools/build_mockups.py --only 01 03    # just these (by prefix)
    python tools/build_mockups.py --scale 1       # quick, low-resolution preview
    python tools/build_mockups.py --no-svg        # PNG only

Each page is a hand-built HTML/CSS/SVG document (tools/mockup/pages.py) drawn in
headless Chromium - the same engine the architecture diagram was checked with.
Fonts and icons are fetched once into tools/.mockup_cache and embedded, so a
page renders with no network after that. The one real image on these pages is
the dwell-time clip: the annotated still from project 05 and a raw frame of the
same clip for the zone editor.

The PNGs are drawn at 3x (4800x2700) so a slide can crop or stretch them. The SVGs
never blur at any size: Chromium prints each page to a one-page PDF, and PyMuPDF
turns that into SVG with the text as outlines, so a slide tool needs no fonts to
show it. Only the two video frames stay pixels inside them, at their own size.

Needs: a Chromium headless shell (CHROME env var, or the Playwright build), OpenCV
for the overview slide's thumbnails, and PyMuPDF (pip install pymupdf) for the SVGs.
"""

from __future__ import annotations

import argparse
import os
import re
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


def _chrome(*args: str) -> subprocess.CompletedProcess:
    cmd = [CHROME] + ([] if "headless_shell" in CHROME else ["--headless"]) + [
           "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--window-size=1600,900",
           "--virtual-time-budget=6000", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def render(html_path: Path, png_path: Path, scale: int) -> None:
    r = _chrome(f"--force-device-scale-factor={scale}", f"--screenshot={png_path}", f"file://{html_path}")
    if not png_path.exists():
        sys.exit(f"render failed for {html_path.name}:\n{r.stderr[-800:]}")


def render_svg(html_path: Path, svg_path: Path) -> None:
    """Print the page to a one-page PDF (the page CSS sets a 1600x900 sheet), then
    convert that page to SVG with the text drawn as outlines."""
    import pymupdf
    pdf_path = html_path.with_suffix(".pdf")
    pdf_path.unlink(missing_ok=True)
    r = _chrome("--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", f"file://{html_path}")
    if not pdf_path.exists():
        sys.exit(f"pdf failed for {html_path.name}:\n{r.stderr[-800:]}")
    with pymupdf.open(pdf_path) as doc:
        if len(doc) != 1:
            sys.exit(f"{html_path.name} printed to {len(doc)} pages, expected 1")
        svg = doc[0].get_svg_image(text_as_path=True)
    # Chromium rounds the 1600x900 px sheet to 1200 x 675.12 pt; trim the stray 0.12 pt
    # so the SVG is exactly 16:9 and fills a slide with no sliver.
    w, h = 1200, 675

    def sized(m: re.Match) -> str:
        tag = re.sub(r'\bheight="[\d.]+"', f'height="{h}"', m.group(0))
        return re.sub(r'\bviewBox="[^"]+"', f'viewBox="0 0 {w} {h}"', tag)

    svg_path.write_text(re.sub(r"<svg\b[^>]*>", sized, svg, count=1), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "docs" / "mockup"))
    ap.add_argument("--work", default=os.environ.get("MOCKUP_WORK", str(HERE / ".mockup_cache" / "html")))
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--only", nargs="*", default=None, help="page-name prefixes, e.g. 01 03")
    ap.add_argument("--no-svg", action="store_true", help="skip the SVG copies")
    a = ap.parse_args()

    out, work = Path(a.out), Path(a.work)
    svg_dir = out / "svg"
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    want_svg = not a.no_svg
    if want_svg:
        try:
            import pymupdf  # noqa: F401
        except ImportError:
            sys.exit("SVG output needs PyMuPDF: pip install pymupdf (or pass --no-svg)")
        svg_dir.mkdir(parents=True, exist_ok=True)

    def emit(name: str, html: str) -> None:
        h = work / f"{name}.html"
        h.write_text(html, encoding="utf-8")
        render(h.resolve(), (out / f"{name}.png").resolve(), a.scale)
        if want_svg:
            render_svg(h.resolve(), (svg_dir / f"{name}.svg").resolve())
        print(f"  {name}")

    for name, fn in pages.PAGES:
        if a.only and not any(name.startswith(p) for p in a.only):
            continue
        emit(name, fn())

    if not a.only or any("00".startswith(p) or p.startswith("00") for p in a.only):
        import base64
        import cv2
        thumbs = {}
        for name, _ in pages.PAGES:
            src = out / f"{name}.png"
            if not src.exists():
                sys.exit(f"overview needs {src.name}; render the pages first")
            # 960 px wide: sharp in the 3x PNG and when the SVG is enlarged on a slide
            im = cv2.resize(cv2.imread(str(src)), (960, 540), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 90])
            thumbs[name] = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
        emit("00-peta-halaman", pages.overview(thumbs))


if __name__ == "__main__":
    main()
