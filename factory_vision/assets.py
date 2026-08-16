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


class _Bar(tqdm):
    """A tqdm sized in bytes, updated from urlretrieve's block callback."""

    def hook(self):
        last = [0]

        def report(blocks, block_size, total):
            if total > 0:
                self.total = total
            self.update(blocks * block_size - last[0])
            last[0] = blocks * block_size

        return report


def _download(url: str, target: Path, label: str) -> bool:
    """Fetch one file, atomically. Returns False if the source refused."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with _Bar(unit="B", unit_scale=True, unit_divisor=1024, miniters=1,
                  desc=f"  {label:<34}", leave=True,
                  bar_format="{desc} {percentage:3.0f}%|{bar:24}| {n_fmt}/{total_fmt}") as bar:
            urllib.request.urlretrieve(url, tmp, reporthook=bar.hook())
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
    request = urllib.request.Request(direct, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30):
            return direct
    except Exception:
        pass
    try:
        with urllib.request.urlopen(f"{PEXELS_DOWNLOAD}/{clip.pexels_id}/",
                                    timeout=30) as response:
            print(f"  !! {clip.rendition} is gone for pexels {clip.pexels_id}; "
                  f"falling back to the default rendition.")
            print("     If that is not 1920x1080 this project's pixel constants "
                  "will not line up.")
            return response.geturl()
    except Exception as exc:
        print(f"  !! could not resolve pexels {clip.pexels_id}: {exc}")
        return None


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
                fetched.append(clip.name)
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
    if target.exists() or target.is_symlink():
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
