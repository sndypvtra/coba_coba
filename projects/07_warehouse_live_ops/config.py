"""Scenes, windows and every threshold the analytics use.

Everything metric is in the dataset's world frame, in metres, with z up and the
floor at z = 0. Pixel constants live only where a picture is drawn.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / "input"
OUTPUT = HERE / "output"
DOCS = HERE / "docs"
WEIGHTS = HERE / "weights"


@dataclass(frozen=True)
class Source:
    """Where a recording lives in the dataset, and what ships with it."""

    hf_path: str
    real: bool          # filmed in a real warehouse rather than rendered
    labelled: bool      # ships ground_truth.json (3D boxes and 2D boxes per camera)
    floor_plan: bool    # ships map.png, a top-down render tied to world metres


SOURCES = {
    "warehouse_000": Source("MTMC_Tracking_2026/train/Warehouse_000",
                            real=False, labelled=True, floor_plan=True),
    "warehouse_027": Source("MTMC_Tracking_2026/test/Warehouse_027",
                            real=True, labelled=False, floor_plan=False),
}


WINDOW_S = 30.0       # every video covers this much of the recording
STRIDE = 3            # every 3rd frame of 30 fps: 10 analysed frames a second


@dataclass(frozen=True)
class Zone:
    """A named part of the floor, in world metres.

    kind "area" is ordinary floor (occupancy and dwell time); "vehicle_lane" is
    where forklifts drive, so a person inside it is an exposure, not occupancy;
    "one_way" carries a permitted direction of travel.
    """

    name: str
    kind: str
    polygon: tuple
    direction: tuple = ()          # unit vector of the permitted way, for one_way


@dataclass(frozen=True)
class Line:
    """A counting line: crossings from its left side to its right are 'in'."""

    name: str
    a: tuple
    b: tuple


def _rect(x0, y0, x1, y1):
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


# Warehouse_000. Every outline below sits inside the field of view of a camera
# that is on screen, and follows the floor rather than a guess: the staging
# rectangle is the one painted on map.png, the vehicle lane is the corridor the
# forklifts actually drive along over the five minutes (a site survey, done
# once, of the kind any installation starts with), and the counting lines were
# placed where people cross most.
SITE = {
    "warehouse_000": {
        "zones": [
            Zone("Staging A", "area", _rect(-37.3, -51.7, -15.9, -48.1)),
            Zone("Area kerja timur", "area", _rect(-30.0, -70.0, -10.0, -53.0)),
            Zone("Area utara", "area", _rect(-62.0, -32.0, -45.0, -12.0)),
            Zone("Area selatan", "area", _rect(-37.0, -100.0, -20.0, -80.0)),
            Zone("Jalur forklift tengah", "vehicle_lane", _rect(-60.0, -63.5, -17.0, -60.5)),
            # A demonstration rule: this simulated site has no one-way aisles, so
            # one is declared here to show what the check does.
            Zone("Lorong satu arah (contoh)", "one_way", _rect(-37.5, -66.0, -33.5, -52.0),
                 direction=(0.0, -1.0)),
        ],
        "lines": [
            Line("Garis A", (-15.0, -46.0), (-15.0, -66.0)),
            Line("Garis B", (-27.0, -55.0), (-12.0, -55.0)),
            Line("Garis C · seberang jalur forklift", (-45.0, -62.0), (-20.0, -62.0)),
        ],
    },
}

# Thresholds, in the units a supervisor would use.
WALKING_MS = 0.4          # faster than this over one second is walking
IDLE_S = 15.0             # still for this long is reported (a PoC-length stand-in for minutes)
IDLE_RADIUS_M = 0.8       # "still" = never further than this from where they stopped
CROWD_RADIUS_M = 2.0      # people within this of a person count towards a crowd
CROWD_MIN = 4             # this many within the radius is congestion
CROWD_S = 1.0             # ... lasting at least this long
LANE_MARGIN_M = 0.3       # in the forklift lane = this far inside its edge (out = outside it)
LANE_CLEAR_S = 2.0        # out of the forklift lane this long before stepping in again is a new entry
NEAR_MISS_M = 1.5         # a person this close to a moving forklift's body
SPEED_LIMIT_KMH = 5.0     # forklift speed limit used for the speeding alert
VEHICLE_MOVING_MS = 0.3
WRONG_WAY_MS = 0.4        # moving against a one-way aisle faster than this, for 1 s


def input_dir(scene: str) -> Path:
    return INPUT / scene


def output_dir(scene: str) -> Path:
    d = OUTPUT / scene
    d.mkdir(parents=True, exist_ok=True)
    return d
