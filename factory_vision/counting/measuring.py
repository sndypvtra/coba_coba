"""The seam between counting and measuring.

Counting a thing past a line and measuring how big it is are different problems
with different equipment. Three projects share the counter; exactly one measures,
and it needs two extra neural networks, a fitted ground plane and a per-frame
depth cache to do it.

For a while all of that lived in this package anyway, under `depth.py` and
`sizing.py`. It ran, but it made the shared half a liar: 619 lines that projects
01 and 02 never execute, sitting in a package labelled as the part they have in
common. Worse, it left `ClipConfig` carrying eleven fields that are dead for two
of its three users, so reading either of those projects meant stepping over
belt patches and footprint scales that have nothing to do with oranges.

So the measurement lives with the project that owns it, and reaches the counter
through this protocol. The pipeline calls these methods when a backend is given
and skips the whole measurement path when it is not - which is what makes
"project 01 does not measure" a structural fact rather than a flag that happens
to be False.

Nothing here imports torch, DA3 or the sizing code. That is the point: this file
describes the shape of the collaboration, and the shared pipeline needs to know
the shape without carrying the weight.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Measurement(Protocol):
    """What the counting pipeline needs from a measurement backend.

    Implemented by `projects/03_parcel_dimensioning/measurement.py`. Sizes are
    duck-typed: the pipeline and the HUD read `volume_l`, `class_name`,
    `class_mark`, `length_m`, `width_m`, `height_m` and `distance_m` off
    whatever objects come back, and never construct one.
    """

    #: Run the depth model every Nth frame. Depth is the expensive part, and a
    #: parcel drifts only a few pixels between runs, so it does not need to be
    #: refreshed as often as the detector.
    refresh_every: int

    def prepare(self, src, width: int, height: int, output_dir) -> None:
        """Solve the camera and fit the ground plane, once, before frame 1.

        Both are properties of the installation rather than of any frame. Doing
        it per frame would cost a second model pass and would let the plane
        wander with the noise in each depth map - which is the very thing every
        height is measured against.
        """

    def refresh(self, frame, key: str) -> None:
        """Recompute the depth map that the next measurements will use."""

    def measure_frame(self, det) -> tuple[Any, list]:
        """Measure every detection, and drop the ones that are not on the belt.

        Returns the surviving detections and their sizes, positionally aligned.
        Measuring first and gating on the result is what lets the detector's
        confidence floor sit as low as 0.05: background is rejected on geometry,
        before the tracker is ever asked to hold an identity for it.
        """

    def lock_ready(self, centre_x: float, samples: int) -> bool:
        """Should this track's size be frozen now?

        A parcel measured all the way to the frame edge keeps revising its size
        while it is being clipped and occluded - the reading would move at
        exactly the moment it is counted. So the value is frozen while the
        parcel is still fully in view.
        """

    def consensus(self, sizes: list):
        """One size from every frame that measured the same object."""

    def summary(self, track_sizes: dict, track_age: dict, min_track_age: int,
                depth_ms: list) -> dict:
        """The measurement half of the report, for `summary.json`."""
