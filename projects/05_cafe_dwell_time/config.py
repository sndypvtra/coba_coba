"""Configuration for one dwell-time installation.

Unlike the conveyor cases there is no counting line and no belt direction: the
question is not "how many passed a point" but "who was here, and for how long".
That makes the tracker, not the detector, the component the answer depends on.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExclusionZone:
    """A region of the frame whose detections are not ordinary customers.

    A detection is matched when at least `min_overlap` of its box area falls
    inside the polygon. Overlap is used rather than a single anchor point
    because both failure directions matter: a reflected person sits wholly
    inside the zone, while a real customer may have only their head poking into
    it, and an anchor test gets one of those two wrong whichever point it picks.

    `mode` decides what happens to a match:

      "exclude"  drop it - a mirror reflection is a person counted twice, and a
                 person behind a counter is not a visit
      "staff"    keep it, tracked and timed, but reported as service rather than
                 as a customer. Dropping a server loses the one measurement a
                 manager actually wants from them: how long they spent serving.
    """

    name: str
    reason: str
    polygon: list[tuple[int, int]]
    min_overlap: float = 0.70
    mode: str = "exclude"
    # Optional detection threshold for this region alone. A service point in a
    # dark corner can sit far below the threshold that is right for the rest of
    # the room, and a global drop would buy those frames at the cost of false
    # positives everywhere else. Narrow region, narrow exception.
    conf: float | None = None
    # A staff track may be held across this many frames of missed detection.
    # Used only where the person has been confirmed present through the gap and
    # does not move; held frames are counted separately from detected ones in
    # the summary so the interpolation is never passed off as observation.
    hold_frames: int = 0


@dataclass
class DwellConfig:
    filename: str
    # The room, by the number CAFE gives it. A room number is what a person
    # asks for - `--scene 1` - and deriving it by parsing the file name would
    # make renaming a clip silently change the command line.
    scene_id: int
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
    # A staff track must last this long to count as service. Measured on scene 5:
    # the real server holds 107 frames, while two customers who happened to stand
    # at the counter early in the clip produced 9- and 5-frame tracks and were
    # reported as staff. A server attends a station; a customer passes one.
    min_staff_frames: int = 15
    exclusion_zones: list[ExclusionZone] = field(default_factory=list)
    tracker_overrides: dict = field(default_factory=dict)
    notes: str = ""


CLIPS = [
    DwellConfig(
        filename="cafe_scene5_30s.mp4",
        scene_id=5,
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
                name="area pelayan",
                reason="behind the counter - timed as service, not as a visit",
                mode="staff",
                hold_frames=6,
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
    # Scene 1 has no mirror, so it carries no exclude zone - only a service one.
    # It does also produce a low-confidence detection (0.37-0.43) on a backlit
    # merchandise shelf at x~540, y~155. That is a false positive on goods rather
    # than a person, and it is left to the track-age gate rather than papered over
    # with another zone.
    DwellConfig(
        filename="cafe_scene1_30s.mp4",
        scene_id=1,
        prompts=["person"],
        label="person",
        scene="Cafe interior, elevated fixed camera - CAFE dataset scene 1",
        source="https://dk-kim.github.io/CAFE/",
        conf=0.25,
        min_track_age=5,
        exclusion_zones=[
            ExclusionZone(
                name="area pelayan",
                reason="counter under the menu boards - timed as service, not a visit",
                mode="staff",
                # The server works the far end of the counter, deep in the room
                # under the illuminated menu boards. Scanning every detection in
                # the left half of the frame down to conf 0.05 puts her at
                # x 742-870, y 225-345; the polygon is that footprint with a
                # margin. The nearest customer detection starts below y=440, so
                # the zone cannot swallow one.
                #
                # Not the person at the top left of the frame, who leans on a
                # wall-facing bar ledge - she is a customer and is counted as one.
                # Traced from the counter itself rather than boxed off: the top
                # edge follows the underside of the illuminated shelf, the bottom
                # edge follows the counter top, which falls away to the right
                # from y=336 at x=700 to y=356 at x=916.
                polygon=[(700, 200), (860, 203), (912, 212), (916, 356),
                         (858, 350), (762, 343), (700, 336)],
                # Detection here is far worse than in the rest of the room: the
                # counter is deep in the scene, backlit by the menu boards, and
                # equipment on the counter top keeps cutting her in half. She
                # appears in roughly half the sampled frames at the room
                # threshold, at confidences spanning 0.05-0.71. Both numbers
                # below come from that measurement rather than from taste.
                conf=0.10,
                hold_frames=12,
            ),
        ],
        notes=("assembled from 150 consecutive frames of CAFE scene 1; "
               "one server station under the menu boards, no mirror"),
    ),
]
