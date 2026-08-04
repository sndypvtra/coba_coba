"""Configuration for one dwell-time installation.

Unlike the conveyor cases there is no counting line and no belt direction: the
question is not "how many passed a point" but "who was here, and for how long".
That makes the tracker, not the detector, the component the answer depends on.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExclusionZone:
    """A region of the frame whose detections are not customers.

    A detection is dropped when at least `min_overlap` of its box area falls
    inside the polygon. Overlap is used rather than a single anchor point
    because both failure directions matter: a reflected person sits wholly
    inside the zone, while a real customer may have only their head poking into
    it, and an anchor test gets one of those two wrong whichever point it picks.
    """

    name: str
    reason: str
    polygon: list[tuple[int, int]]
    min_overlap: float = 0.70


@dataclass
class DwellConfig:
    filename: str
    prompts: list[str]
    label: str
    scene: str
    source: str
    conf: float = 0.25
    # A track must survive this many frames before it counts as a real presence.
    # Note this gate is weak against duplicate boxes: it counts cumulative frames
    # seen, and a spurious second box on an already-tracked person easily reaches
    # five. Raising it from 3 to 5 moved the visitor total 30 -> 29 and no
    # further, which is why duplicates are now suppressed at the detection stage
    # instead (see `dedup_containment`).
    min_track_age: int = 5
    # Two boxes covering the same person are common at this camera angle: one on
    # the head-and-shoulders of a seated customer, one on the whole body. Their
    # IoU stays near 0.4 so NMS keeps both, but the smaller is ~90% contained by
    # the larger. Containment catches what IoU misses.
    dedup_containment: float = 0.75
    max_box_area_frac: float = 0.35
    min_box_area_frac: float = 0.0008
    exclusion_zones: list[ExclusionZone] = field(default_factory=list)
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
        exclusion_zones=[
            ExclusionZone(
                name="mirror",
                reason="wall mirror - reflections are people already counted elsewhere",
                # Traced from the mirror's metal frame. The lower edge is held a
                # little high on purpose: the nearest real customer's head starts
                # around y=285 at x=500, and clipping a real person to catch a
                # reflection would be the worse error of the two.
                polygon=[(50, 0), (745, 0), (735, 185), (620, 225),
                         (420, 252), (250, 246), (165, 196), (50, 110)],
            ),
            ExclusionZone(
                name="service area",
                reason="behind the counter - staff, not customers",
                # The lower edge follows the counter's top edge, measured at
                # (1080,150) - (1500,195) - (1650,200). Staff stand beyond it and
                # fall wholly inside; a customer at the till has only their head
                # and shoulders above the counter, so their box stays well under
                # the overlap threshold and is kept.
                polygon=[(1050, 0), (1920, 0), (1920, 120),
                         (1650, 200), (1500, 195), (1080, 150)],
            ),
        ],
        notes=("assembled from 150 consecutive frames of CAFE scene 5 "
               "(every 6th frame of a 29.97 fps recording -> 4.995 fps, 30.0 s)"),
    ),
]
