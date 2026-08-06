"""Configuration for one multi-camera space.

The other cases are configured per *clip*. This one is configured per *scene*,
because the whole point is that several cameras look at one floor: their
detections are only comparable once they have been put into the same world
coordinate frame, and that frame belongs to the scene rather than to any one
camera.

Everything metric here - zone outlines, floor bounds, the person footprint - is
in the dataset's world coordinates, in metres. Nothing is in pixels, which is
what makes a zone definition survive a change of camera.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass
class CameraView:
    """One camera of the scene, and where its panel goes in the mosaic.

    `side`, `row` and `col` are the tile's position in the dataset's own banner
    - two blocks of camera tiles with the top-down view between them. Keeping
    the mosaic in those terms rather than in pixels means the same renderer
    handles four cameras and twelve.
    """

    sensor_id: str          # key into calibration.json / ground_truth.json
    filename: str           # clip in videos/, cut by scripts/fetch_warehouse_scene.py
    side: str               # "left" | "right"
    row: int
    col: int

    @property
    def provenance(self) -> str:
        return f"banner tile: {self.side} block, row {self.row + 1} col {self.col + 1}"


@dataclass
class Zone:
    """A named region of the floor, outlined in world metres.

    `kind` decides how it is reported:

      "area"        an ordinary part of the building - the occupancy breakdown
                    is "where did people spend their time"
      "restricted"  a marked lane that people are not supposed to stand in, so
                    time inside it is reported as an exposure rather than as
                    occupancy
    """

    name: str
    kind: str
    polygon_m: list[tuple[float, float]]
    note: str = ""


@dataclass
class SceneConfig:
    name: str
    scene: str
    source: str
    licence: str

    views: list[CameraView]

    # Source clip window. The dataset videos are 9,000 frames at 30 fps; the
    # pipeline reads a window of that and subsamples it, so `stride` is what
    # separates "30 seconds of video" from "300 inferences per camera".
    src_fps: float = 30.0
    start_frame: int = 1950
    window_frames: int = 900
    stride: int = 3

    # Zero-shot prompt list, one prompt per class. Naming the machines is what
    # keeps them out of the headcount: an object with nowhere to put it does not
    # go undetected, it gets detected as the nearest class that *is* on the list.
    classes: dict = field(default_factory=lambda: dict(CLASSES))
    conf: float = 0.15

    dedup_containment: float = 0.80

    @property
    def prompts(self) -> list[str]:
        return [c["prompt"] for c in self.classes.values()]

    @property
    def kinds(self) -> list[str]:
        return list(self.classes)

    def spec(self, kind: str) -> dict:
        return self.classes[kind]

    # Two cameras seeing the same person put them within this distance of each
    # other. There is a lot of room here: over this window the three people
    # never come within 8.07 m of one another, so no plausible gate confuses
    # two of them. What the gate *does* have to survive is a person passing a
    # humanoid robot at 0.69 m - closer than the gate - which is why fusion is
    # constrained by class as well as by distance (see `fuse.cluster_frame`).
    fuse_radius_m: float = 0.90
    # A global identity survives this many sampled frames with no observation
    # before it is retired. At 10 fps that is 1.5 s of full occlusion.
    max_age_frames: int = 15
    # ... and must be seen this many times before it is reported at all. One
    # second. Measured: at 4 frames a second identity appeared alongside a real
    # person for 6 frames at a mean 2.2 m/s - a duplicate box that survived
    # containment suppression in three views at once, which the per-camera rule
    # in `fuse.cluster_frame` cannot merge by design. It is not a person and it
    # does not move like one, and a persistence gate is the cheap way to say so.
    min_track_age: int = 10
    # An identity must also be corroborated by this many cameras at some point.
    # Cheap insurance that only a multi-camera install can buy: a single view's
    # phantom is not reproduced by the other views looking at the same spot. Set
    # to 1 to disable, at the cost of reporting single-view artefacts.
    min_corroborating_views: int = 2

    # Floor extent, from the yellow boundary painted on the dataset's map.png.
    floor_bounds_m: tuple[float, float, float, float] = (-9.63, -19.65, 9.63, -0.37)
    # Detections that land outside this (slightly larger) rectangle are dropped:
    # the ground-plane back-projection is unstable near the horizon and sends
    # the odd box to the far side of the building.
    valid_bounds_m: tuple[float, float, float, float] = (-10.6, -20.6, 10.6, 0.6)

    # Draw the floor plan the way the dataset's own banner draws it.
    plan_flipped: bool = True

    zones: list[Zone] = field(default_factory=list)
    tracker_overrides: dict = field(default_factory=dict)
    notes: str = ""
    # Scene assets (calibration, map, ground truth) live in videos/<assets>/.
    # Separate from `name` so that two view selections of one building share one
    # download instead of fetching 1.5 GB twice.
    assets: str = ""

    @property
    def asset_dir(self) -> str:
        return self.assets or self.name

    def grid(self, side: str) -> tuple[int, int]:
        """Rows and columns of the tile block on one side of the eagle view."""
        v = [x for x in self.views if x.side == side]
        if not v:
            return 0, 0
        return max(x.row for x in v) + 1, max(x.col for x in v) + 1

    @property
    def out_fps(self) -> float:
        return self.src_fps / self.stride

    @property
    def n_frames(self) -> int:
        return self.window_frames // self.stride


# One entry per class: what to call it, how tall it can plausibly be, and what
# footprint to draw. The height range is a real filter, not decoration - a
# pallet transporter stands 0.20 m and a person 1.9 m, so a detection lifted to
# the wrong range is a detection on the wrong thing and is dropped. Footprints
# and height ranges are the dataset's own object dimensions, widened a little.
# `height_reject` says whether a stature outside the range disqualifies the
# detection or merely leaves the height unknown. For a person it must not:
# whatever their posture the box bottom is still their feet, so the *position*
# stands even when a bent-over worker measures 1.0 m. Rejecting on it dropped
# every crouching person near the camera. For a machine or a load an impossible
# stature means the box is drawn round the wrong thing, and it is a rejection.
#
# `conf` and `min_views` are per class because the classes are not equally easy.
# A pallet load sits low, is half-occluded by whatever is stacked on it, and
# scores 0.15-0.20 where a person scores 0.9; it is also seen by fewer cameras,
# so demanding two views loses the very loads that move.
CLASSES = {
    # The 1.20 m floor is a measured trade, not an oversight. A worker bent over
    # a pallet close to a camera measures about a metre and is thrown away by it
    # - visibly, in tiles where someone in plain view carries no box. Both ways
    # of admitting them cost more than they return, over the same 60 frames:
    #
    #   floor 1.20 m, reject   4 people   1.00 global IDs per real person
    #   floor 0.95 m, reject   5 people   1.33
    #   no height rejection    6 people   2.33
    #
    # A box that measures a metre is usually not a crouching worker; it is a
    # person-shaped box drawn round stacked goods, and letting those in breaks
    # the identity of everyone else. The crouching worker stays a known miss.
    "person":   {"prompt": "person",          "height": (1.20, 2.30),
                 "footprint": (0.60, 0.46), "machine": False, "goods": False,
                 "height_reject": True, "conf": 0.15, "min_views": 2},
    "humanoid": {"prompt": "humanoid robot",  "height": (1.20, 2.30),
                 "footprint": (0.60, 0.46), "machine": True,  "goods": False,
                 "height_reject": True,  "conf": 0.15, "min_views": 2},
    "vehicle":  {"prompt": "transport robot", "height": (0.10, 0.80),
                 "footprint": (1.43, 0.65), "machine": True,  "goods": False,
                 "height_reject": True,  "conf": 0.15, "min_views": 2},
    "pallet":   {"prompt": "cardboard box",   "height": (0.15, 1.90),
                 "footprint": (1.20, 0.80), "machine": False, "goods": True,
                 "height_reject": True,  "conf": 0.10, "min_views": 1},
}


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _clip(sensor_id: str) -> str:
    n = sensor_id.split("_")[1] if "_" in sensor_id else "00"
    return f"w014_camera_{n}_30s.mp4"


def _view(sensor_id: str, side: str, row: int, col: int) -> CameraView:
    return CameraView(sensor_id, _clip(sensor_id), side, row, col)


# Every tile of the dataset banner, in its banner position. The mapping from
# tile to camera was measured, not guessed: each of the twelve tiles was
# template-matched against the first frame of all twelve videos and resolved at
# 0.87-0.96 against a next-best of at most 0.44.
BANNER_TILES = [
    _view("Camera_02", "left", 0, 0),   _view("Camera_03", "left", 0, 1),
    _view("Camera_08", "left", 1, 0),   _view("Camera_09", "left", 1, 1),
    _view("Camera", "left", 2, 0),      _view("Camera_07", "left", 2, 1),
    _view("Camera_06", "right", 0, 0),  _view("Camera_11", "right", 0, 1),
    _view("Camera_04", "right", 1, 0),  _view("Camera_05", "right", 1, 1),
    _view("Camera_10", "right", 2, 0),  _view("Camera_01", "right", 2, 1),
]

# Zone outlines were read off the dataset's own map.png with a one-metre grid
# drawn over it, so they follow the paint on the floor rather than a guess: the
# black-bordered block, the three blue pallet lanes inside it, and the racking
# at the north end.
WAREHOUSE_014_FULL = SceneConfig(
    name="warehouse_014_full",
    assets="warehouse_014",
    scene="Warehouse_014 - all 12 fixed cameras over one 19.3 x 19.3 m floor",
    source=("https://huggingface.co/datasets/nvidia/PhysicalAI-SmartSpaces"
            " - MTMC_Tracking_2025/train/Warehouse_014"),
    licence="CC BY 4.0",
    views=list(BANNER_TILES),
    zones=[
        # Re-measured from the floor itself, not from the map. The bay outlines
        # and the painted bay numbers were located in Camera_02 and
        # back-projected through its calibration, then checked by projecting
        # them into the other three views. The earlier outlines came from
        # reading map.png under a y-mirrored transform and sat half a warehouse
        # away from the paint.
        Zone("Staging area", "area", _rect(-5.19, -17.98, 8.02, -9.73),
             "the black-bordered block holding bays 1-3"),
        # People work *around* the bays as much as inside them, so the ring of
        # floor immediately outside the block gets its own name. Without it every
        # metre of that ring is filed under "racking", which reads as people
        # spending three quarters of the shift at the shelves when they are
        # actually standing at the bays.
        Zone("Staging aisle", "area", _rect(-7.70, -20.50, 10.50, -7.20),
             "the working ring immediately around the staging block"),
        Zone("Racking and shelving", "area", [], "the rest of the marked floor"),
        # The three painted bays. Numbering runs 1 at high x to 3 at low x, which
        # is the order the floor markings themselves use.
        Zone("Bay 1", "restricted", _rect(4.54, -16.80, 6.41, -11.19),
             "painted bay 1, marker at (5.50, -10.68)"),
        Zone("Bay 2", "restricted", _rect(0.21, -17.13, 2.42, -10.91),
             "painted bay 2, marker at (1.45, -10.34)"),
        Zone("Bay 3", "restricted", _rect(-4.01, -17.07, -1.83, -10.87),
             "painted bay 3, marker at (-2.83, -10.25)"),
    ],
    notes=("30 s from frame 1950 (t=65 s), the busiest window of the 300 s "
           "recording by person travel distance; every banner tile"),
)

# The four tiles asked for first: the left block's top-left and bottom-left, and
# the right block's top-left and bottom-right. Same building, same window, same
# assets - a subset of views rather than a second scene.
_QUAD = {("left", 0, 0), ("left", 2, 0), ("right", 0, 0), ("right", 2, 1)}
WAREHOUSE_014 = replace(
    WAREHOUSE_014_FULL,
    name="warehouse_014",
    scene="Warehouse_014 - four fixed cameras over one 19.3 x 19.3 m floor",
    views=[replace(v, row=0 if (v.side, v.row, v.col) in
                   {("left", 0, 0), ("right", 0, 0)} else 1, col=0)
           for v in BANNER_TILES if (v.side, v.row, v.col) in _QUAD],
    notes=("30 s from frame 1950 (t=65 s), the busiest window of the 300 s "
           "recording by person travel distance; four of the twelve tiles"),
)

SCENES = [WAREHOUSE_014_FULL, WAREHOUSE_014]
