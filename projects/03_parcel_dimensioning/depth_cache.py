"""Depth maps kept on disk, because they are expensive and never change.

One DA3 forward pass costs 7 s on this machine when the host is quiet and 60 s
when it is not, so a 511-frame run is anywhere between 25 minutes and two hours -
and a container restart part-way through threw all of it away once.

The maps depend only on the frame and the processing resolution, and both are
fixed for a given clip. So they are worth storing: a re-render for a label or a
panel change becomes nearly free, and an interrupted run resumes instead of
starting over.

Two details make the cache safe rather than merely fast:

*float16 at the processing resolution.* 0.9 MB a frame instead of 8, with a
quantisation step around 1 mm at these distances - far below the model's own
error, so the cache costs nothing in accuracy.

It does cost *reproducibility*, and in two different ways that are worth keeping
apart.

The fixable one: storing float16 while returning float32 meant the run that
computed a map measured different numbers from every run that later read it.
`MetricDepth.depth` now quantises its return value the same way, so a computed
map and its read-back are bitwise equal.

The one that remains: DA3 is bit-identical within a process but not across
processes, drifting by ~1e-6 canonical units - orders of magnitude below anything
physical, and below this cache's own resolution. Rounding to float16 turns those
wobbles into +/-1 quantisation step, 2-8 mm at these ranges, on a minority of
pixels. Comparing two independent runs of the same clip: median difference
exactly 0, p99 3.9 mm, and that is enough to move a parcel's measured side by up
to 5 mm. Storing float32 would shrink this to ~1e-6 m at the cost of doubling the
cache to 190 MB; the tolerance is documented in the README instead, because a
figure quoted without one is the actual hazard.

*Atomic replace.* The map is written to a temporary name and moved into place,
so a process killed mid-write leaves no truncated file that the next run would
happily load as real depth.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


class DepthCache:
    """Stored depth maps for one clip at one processing resolution."""

    def __init__(self, directory, process_res: int):
        self.dir = Path(directory) if directory else None
        self.process_res = process_res
        self.hits = 0

    def path_for(self, key: str | None) -> Path | None:
        if key is None or self.dir is None:
            return None
        return self.dir / f"{key}_{self.process_res}.npy"

    def load(self, key: str | None) -> np.ndarray | None:
        """The stored map at processing resolution, or None if not cached."""
        path = self.path_for(key)
        if path is None or not path.exists():
            return None
        self.hits += 1
        return np.load(path).astype(np.float32)

    def store(self, key: str | None, metres: np.ndarray) -> None:
        path = self.path_for(key)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp.npy")
        np.save(tmp, metres.astype(np.float16))
        tmp.replace(path)      # atomic, so a kill mid-write leaves no stub
