#!/usr/bin/env python3
"""Render the product mockup pages for the investor deck, as PNG and as SVG.

    python tools/build_mockups.py                 # all pages -> docs/mockup/ (+ docs/mockup/svg/)
    python tools/build_mockups.py --only 01 03    # just these (by prefix)
    python tools/build_mockups.py --scale 1       # quick, low-resolution preview
    python tools/build_mockups.py --no-svg        # PNG only

Most pages are one 16:9 screen. The few in pages.LONG_PAGES (the full landing page)
are 1600 px wide and as tall as their content: such a page writes its own height into
data-h on <body>, and the build reads it back before sizing the screenshot and the
PDF sheet. The landing page is numbered 00 so it opens the set.

Each page is a hand-built HTML/CSS/SVG document (tools/mockup/pages.py) drawn in
headless Chromium - the same engine the architecture diagram was checked with.
Fonts and icons are fetched once into tools/.mockup_cache and embedded, so a
page renders with no network after that. The one real image on these pages is
the dwell-time clip: the annotated still from project 05 and a raw frame of the
same clip for the zone editor.

The PNGs are drawn at 2400x1350, a size every slide tool takes without trouble
(pass --scale 3 for 4800x2700). The SVGs never blur at any size: Chromium prints
each page to a one-page PDF, and PyMuPDF turns that into SVG with the text as
outlines, so a slide tool needs no fonts to show it. Only the photos stay pixels
inside them, embedded at their own size.

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


def _chrome(*args: str, size: tuple[int, int] = (1600, 900)) -> subprocess.CompletedProcess:
    cmd = [CHROME] + ([] if "headless_shell" in CHROME else ["--headless"]) + [
           "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={size[0]},{size[1]}",
           "--virtual-time-budget=6000", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def render(html_path: Path, png_path: Path, scale: float, size: tuple[int, int] = (1600, 900)) -> None:
    png_path.unlink(missing_ok=True)
    r = _chrome(f"--force-device-scale-factor={scale}", f"--screenshot={png_path}", f"file://{html_path}", size=size)
    if not png_path.exists():
        sys.exit(f"render failed for {html_path.name}:\n{r.stderr[-800:]}")


def page_height(html_path: Path) -> int:
    """The height a long page reports for itself once its fonts are in."""
    r = _chrome("--dump-dom", f"file://{html_path}", size=(1600, 2000))
    m = re.search(r'<body[^>]*\bdata-h="(\d+)"', r.stdout)
    if not m:
        sys.exit(f"{html_path.name} did not report its height:\n{r.stderr[-800:]}")
    return int(m.group(1))


def render_svg(html_path: Path, svg_path: Path, size: tuple[int, int] = (1600, 900)) -> None:
    """Print the page to a one-page PDF (the page CSS sets the sheet to the page's own
    size), then convert that page to SVG with the text drawn as outlines."""
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
    w, h = round(size[0] * 0.75), round(size[1] * 0.75)

    def sized(m: re.Match) -> str:
        tag = re.sub(r'\bheight="[\d.]+"', f'height="{h}"', m.group(0))
        return re.sub(r'\bviewBox="[^"]+"', f'viewBox="0 0 {w} {h}"', tag)

    svg = re.sub(r"<svg\b[^>]*>", sized, svg, count=1)
    # The photos are embedded as data URIs. PyMuPDF wraps their base64 every 64
    # characters, and XML turns those line breaks into spaces inside the attribute;
    # Chromium decodes that anyway but stricter viewers drop the image. Write each one
    # on one line, and give it the SVG 2 `href` as well as the older `xlink:href`.
    svg = re.sub(r'(data:[\w/+.-]+;base64,)([^"]*)"', lambda m: m.group(1) + re.sub(r"\s+", "", m.group(2)) + '"', svg)
    svg = re.sub(r'<image\b([^>]*?)\sxlink:href="([^"]*)"', r'<image\1 href="\2" xlink:href="\2"', svg)
    # Two more changes that a browser cannot see, for the importers that get them
    # wrong - with either, the photos are what disappears, because every photo sits
    # inside a rounded clip. Bake each clip outline's transform into its points, since
    # some importers ignore a transform inside <clipPath>. And give every id the page
    # number: a deck tool that pastes several pages into one document would otherwise
    # let a page pick up another page's clip_451 or glyph font_6_363.
    svg = re.sub(r"<clipPath\b[^>]*>.*?</clipPath>", _bake_clip, svg, flags=re.S)
    # The number alone is not unique - 00 is the landing page, its full-length copy and
    # the overview - so the words' initials follow it: 00-landing-page -> p00lp_.
    num, *words = svg_path.stem.split("-")
    pfx = f"p{num}{''.join(w[0] for w in words)}_"
    svg = re.sub(r'(\sid="|url\(#|href="#)', lambda m: m.group(1) + pfx, svg)
    svg_path.write_text(svg, encoding="utf-8")


_NUM = r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def _bake_clip(m: re.Match) -> str:
    """Apply a clip outline's matrix(a,0,0,d,e,f) to its absolute M/L/C/H/V points."""
    def bake(pm: re.Match) -> str:
        a, b, c, d, e, f = (float(v) for v in pm.group(1).split(","))
        data = pm.group(2)
        if b or c or not set(re.findall(r"[A-Za-z]", re.sub(_NUM, " ", data))) <= set("MLCHVZ"):
            return pm.group(0)
        out, cmd, i = [], "", 0
        for tok in re.findall(rf"[A-Za-z]|{_NUM}", data):
            if tok.isalpha():
                cmd, i = tok, 0
                out.append(tok)
                continue
            is_y = cmd == "V" or (cmd != "H" and i % 2 == 1)
            v = float(tok) * d + f if is_y else float(tok) * a + e
            out.append(f"{v:.3f}".rstrip("0").rstrip("."))
            i += 1
        return f'<path d="{" ".join(out)}"'
    return re.sub(r'<path transform="matrix\(([^)]*)\)" d="([^"]*)"', bake, m.group(0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "docs" / "mockup"))
    ap.add_argument("--work", default=os.environ.get("MOCKUP_WORK", str(HERE / ".mockup_cache" / "html")))
    ap.add_argument("--scale", type=float, default=1.5, help="1.5 gives 2400x1350")
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

    for name, fn in pages.LONG_PAGES:
        if a.only and not any(name.startswith(p) for p in a.only):
            continue
        html = fn()
        h = work / f"{name}.html"
        h.write_text(html, encoding="utf-8")
        size = (1600, page_height(h.resolve()))
        h.write_text(html.replace("</head>", f"<style>@page{{size:{size[0]}px {size[1]}px;margin:0}}</style></head>", 1),
                     encoding="utf-8")
        render(h.resolve(), (out / f"{name}.png").resolve(), a.scale, size)
        if want_svg:
            render_svg(h.resolve(), (svg_dir / f"{name}.svg").resolve(), size)
        print(f"  {name} ({size[0]}x{size[1]})")

    if not a.only or any("00".startswith(p) or p.startswith("00") for p in a.only):
        import base64
        import cv2
        thumbs = {}
        for name, _ in pages.PAGES:
            src = out / f"{name}.png"
            if not src.exists():
                sys.exit(f"overview needs {src.name}; render the pages first")
            # 960 px wide: sharp in the PNG and when the SVG is enlarged on a slide
            im = cv2.resize(cv2.imread(str(src)), (960, 540), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 90])
            thumbs[name] = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
        emit("00-peta-halaman", pages.overview(thumbs))


if __name__ == "__main__":
    main()
