"""Configuration for one dwell-time installation.

Unlike the conveyor cases there is no counting line and no belt direction: the
question is not "how many passed a point" but "who was here, and for how long".
That makes the tracker, not the detector, the component the answer depends on.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DwellConfig:
    filename: str
    prompts: list[str]
    label: str
    scene: str
    source: str
    conf: float = 0.25
    # A track must survive this many frames before it is counted as a real
    # presence. Without it a single-frame false positive on a chair back becomes
    # a "visitor" with a dwell time, and the unique-person total drifts upward
    # for the whole clip.
    #
    # Measured on the 30 s cafe clip: at 3 frames (0.6 s) the run reported 30
    # visitors against a mean occupancy of 12.2, because twelve tracks lived
    # under 5 s - duplicate boxes on people who already had an ID, not new
    # arrivals. At this camera nobody crosses the room in under a second, so a
    # sub-second track is noise by construction.
    min_track_age: int = 5
    # Boxes larger than this fraction of the frame are furniture or a camera
    # artefact, not a person at this camera height.
    max_box_area_frac: float = 0.35
    min_box_area_frac: float = 0.0008
    tracker_overrides: dict = field(default_factory=dict)
    notes: str = ""


CLIPS = [
    DwellConfig(
        filename="cafe_scene5_30s.mp4",
        prompts=["person"],
        label="person",
        scene="Cafe interior, elevated fixed camera - CAFE dataset scene 5",
        source="https://dk-kim.github.io/CAFE/",
        conf=0.25,
        min_track_age=5,
        notes=("assembled from 150 consecutive frames of CAFE scene 5 "
               "(every 6th frame of a 29.97 fps recording -> 4.995 fps, 30.0 s)"),
    ),
]
