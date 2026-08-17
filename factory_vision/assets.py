"""Everything a project needs to run, fetched on first launch.

The point of this file is that `python main.py` works on a clean clone. No
setup script to remember, no README step that says "first download the
weights" - a project declares what it needs, and anything missing arrives with
a progress bar before the pipeline starts.

Three kinds of asset, three very different sources:

  source clips   Pexels, by video id. The pixel constants in every project -
                 counting lines, ROIs, bottle geometry - are calibrated against
                 a *specific rendition*, so the rendition is named rather than
                 left to the /download/ endpoint, which hands back whatever is
                 largest. That is 3840x2160 for one of these clips and would
                 silently move every constant.
  model weights  Ultralytics release assets, by filename.
  hub models     Hugging Face repos, via `snapshot_download`, which brings its
                 own progress bars and its own cache.

Anything already present is left alone, so a second run costs nothing and an
interrupted download resumes rather than restarting from zero.
"""

from __future__ import annotations

import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from tqdm import tqdm

ULTRALYTICS_RELEASE = "https://github.com/ultralytics/assets/releases/download/v8.3.0"
PEXELS_CDN = "https://videos.pexels.com/video-files"
PEXELS_DOWNLOAD = "https://www.pexels.com/download/video"

# Pexels' CDN refuses the default `Python-urllib/3.x` User-Agent with a bare 403,
# on HEAD and GET alike, so every clip fetch failed on a clean clone while the
# same URL returned 200 to curl. Any other User-Agent is accepted; this one says
# who is calling rather than pretending to be a browser.
USER_AGENT = ("factory-vision-poc/1.0 "
              "(+https://github.com/sndypvtra/coba_coba)")

# Ultralytics fetches this itself the first time `get_text_pe()` runs, into the
# *working directory* rather than anywhere sensible. Naming it here lets a
# project pre-place it so the download happens with the others, in view, instead
# of as a surprise 572 MB pause in the middle of the first frame.
MOBILECLIP = "mobileclip_blt.ts"


@dataclass(frozen=True)
class Clip:
    """One source video, pinned to the rendition the constants were set on."""

    name: str
    pexels_id: int
    rendition: str = "hd_1920_1080_30fps"
    note: str = ""


@dataclass(frozen=True)
class Requirements:
    """What one project needs before it can run."""

    clips: tuple[Clip, ...] = ()
    weights: tuple[str, ...] = ()
    hub_models: tuple[str, ...] = ()
    extras: tuple = ()          # callables run last, for anything bespoke
    notes: tuple[str, ...] = field(default_factory=tuple)


def _open(url: str, method: str = "GET", timeout: int = 30):
    """Open a URL with a User-Agent that CDNs accept - see USER_AGENT."""
    request = urllib.request.Request(url, method=method,
                                     headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def _download(url: str, target: Path, label: str) -> bool:
    """Fetch one file, atomically. Returns False if the source refused.

    Streamed by hand rather than through `urlretrieve`, which cannot carry a
    User-Agent header. That is not a style preference: without one Pexels answers
    403 and no clip can be fetched at all.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with _open(url) as response:
            total = int(response.headers.get("Content-Length") or 0)
            with tqdm(total=total or None, unit="B", unit_scale=True,
                      unit_divisor=1024, miniters=1, desc=f"  {label:<34}",
                      leave=True,
                      bar_format="{desc} {percentage:3.0f}%|{bar:24}| "
                                 "{n_fmt}/{total_fmt}") as bar, tmp.open("wb") as out:
                while True:
                    chunk = response.read(1 << 16)
                    if not chunk:
                        break
                    out.write(chunk)
                    bar.update(len(chunk))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        tmp.unlink(missing_ok=True)
        print(f"  {label:<34} FAILED: {exc}")
        return False
    # Only now does the real name appear, so an interrupted run never leaves a
    # half-file that looks complete to the `exists()` check on the next launch.
    tmp.replace(target)
    return True


def _resolve_clip(clip: Clip) -> str | None:
    """The named rendition if it still exists, else whatever Pexels redirects to."""
    direct = f"{PEXELS_CDN}/{clip.pexels_id}/{clip.pexels_id}-{clip.rendition}.mp4"
    try:
        with _open(direct, method="HEAD"):
            return direct
    except Exception:
        pass
    try:
        with _open(f"{PEXELS_DOWNLOAD}/{clip.pexels_id}/") as response:
            print(f"  !! {clip.rendition} is gone for pexels {clip.pexels_id}; "
                  f"falling back to the default rendition.")
            print("     Every pixel constant in this project was measured on "
                  f"{clip.rendition}, so the download is checked against it and")
            print("     refused if it does not match - see _verify_rendition.")
            return response.geturl()
    except Exception as exc:
        print(f"  !! could not resolve pexels {clip.pexels_id}: {exc}")
        return None


def _expected_size(rendition: str) -> tuple[int, int] | None:
    """The frame size a rendition name promises: hd_1920_1080_30fps -> 1920x1080."""
    parts = rendition.split("_")
    for i in range(len(parts) - 1):
        if parts[i].isdigit() and parts[i + 1].isdigit():
            return int(parts[i]), int(parts[i + 1])
    return None


def _verify_rendition(path: Path, clip: Clip) -> bool:
    """Refuse a clip whose frame size is not the one the constants were set on.

    The fallback above exists because a rendition can be withdrawn, but what
    Pexels hands back instead is *the largest* one - 3840x2160 for the bottling
    clip. Downloading that and carrying on would leave every ROI, counting line
    and bottle outline pointing at the wrong pixels, and nothing in the output
    would say so: the run would simply report a confident wrong number. So the
    file is measured before it is accepted.
    """
    want = _expected_size(clip.rendition)
    if want is None:
        return True
    import cv2  # local: this module is imported before the pipeline needs cv2

    cap = cv2.VideoCapture(str(path))
    got = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    cap.release()
    if got == want:
        return True
    print(f"  {clip.name:<34} WRONG RENDITION: {got[0]}x{got[1]}, "
          f"expected {want[0]}x{want[1]}")
    print("     This project's pixel constants were measured on "
          f"{clip.rendition}; a different frame size would move all of them.")
    return False


def ensure(req: Requirements, video_dir: Path, weights_dir: Path,
           quiet: bool = False) -> bool:
    """Fetch whatever is missing. Returns True if the project can run.

    Reports what it already has as well as what it fetches, because "nothing
    happened" and "nothing needed to happen" look identical otherwise, and the
    difference matters when a run then fails for want of a file.
    """
    ok = True
    have, fetched = [], []

    if req.weights:
        _say(quiet, "\n[1/3] model weights")
        for name in req.weights:
            target = weights_dir / name
            if target.exists():
                have.append(name)
                _say(quiet, f"  {name:<34} present")
                continue
            if _download(f"{ULTRALYTICS_RELEASE}/{name}", target, name):
                fetched.append(name)
            else:
                ok = False

    if req.hub_models:
        _say(quiet, "\n[2/3] Hugging Face models")
        for repo in req.hub_models:
            try:
                from huggingface_hub import snapshot_download
                _say(quiet, f"  {repo}")
                snapshot_download(repo)
                fetched.append(repo)
            except Exception as exc:
                print(f"  {repo:<34} FAILED: {exc}")
                ok = False

    if req.clips:
        _say(quiet, "\n[3/3] source clips (Pexels, free for commercial use)")
        for clip in req.clips:
            target = video_dir / clip.name
            if target.exists():
                have.append(clip.name)
                _say(quiet, f"  {clip.name:<34} present")
                continue
            url = _resolve_clip(clip)
            if url and _download(url, target, clip.name):
                if _verify_rendition(target, clip):
                    fetched.append(clip.name)
                else:
                    # Renamed rather than deleted: it is a perfectly good video,
                    # just not the one this project is calibrated for, and a
                    # silent delete would look like the download failed. The
                    # rename is what matters, though - left under its expected
                    # name, the next run's `exists()` check would call it present
                    # and measure the wrong pixels without a word.
                    kept = target.with_suffix(".wrong-rendition.mp4")
                    target.replace(kept)
                    print(f"     kept as {kept.name}, not accepted as the input")
                    ok = False
            else:
                ok = False

    for extra in req.extras:
        try:
            extra(video_dir=video_dir, weights_dir=weights_dir)
        except Exception as exc:
            print(f"  extra step FAILED: {exc}")
            ok = False

    if not quiet:
        print(f"\n  {len(have)} already present, {len(fetched)} fetched")
        for note in req.notes:
            print(f"  note: {note}")
    return ok


def _say(quiet: bool, text: str) -> None:
    if not quiet:
        print(text)
        sys.stdout.flush()


def place_mobileclip(weights_dir: Path, run_dir: Path) -> None:
    """Put the MobileCLIP text encoder where ultralytics will look for it.

    Ultralytics resolves this file against the *current working directory*, and
    every project now runs from its own folder. Without this, each one
    re-downloads the same 572 MB into its own directory - which is exactly what
    happened the first time the projects were split, four times over, before the
    link below was pointed at the right source.

    The encoder lives in the shared `weights/` with the detector checkpoints,
    for the same reason they do: it is identical for every project and far too
    large to hold six copies of.
    """
    source = weights_dir / MOBILECLIP
    target = run_dir / MOBILECLIP
    if target.is_symlink() and not target.exists():
        # A link left by an earlier run whose target has since moved - the repo
        # was relocated, or weights/ was pruned. `is_symlink()` is true for a
        # broken link, so returning early here would leave ultralytics to open a
        # dangling path and fail somewhere far less obvious.
        target.unlink()
    if target.exists():
        return
    if not source.exists():
        # Nothing to link yet. Ultralytics will fetch it into the project folder
        # on the first `get_text_pe()`; move it into weights/ afterwards and
        # every other project picks it up from there.
        return
    try:
        target.symlink_to(source)
    except OSError:
        shutil.copy2(source, target)


def adopt_mobileclip(weights_dir: Path, run_dir: Path) -> None:
    """Move a freshly downloaded encoder into the shared cache and link it back.

    Called after the model has run, so the 572 MB ultralytics just fetched into
    a project folder is available to the other five instead of being downloaded
    again by each of them.
    """
    here = run_dir / MOBILECLIP
    shared = weights_dir / MOBILECLIP
    if not here.is_file() or here.is_symlink() or shared.exists():
        return
    weights_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(here), str(shared))
    try:
        here.symlink_to(shared)
    except OSError:
        pass
