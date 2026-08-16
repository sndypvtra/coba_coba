#!/usr/bin/env python3
"""Case 6 - Warehouse: four cameras, one floor plan, people located in 3D.

    python main.py
    python main.py --max-frames 60      # a quick look

The only project whose source is a research dataset rather than stock footage:
NVIDIA's PhysicalAI-SmartSpaces, which ships calibration and 3D ground truth
with the video. That is what makes this the one case whose accuracy can be
stated against a truth rather than argued for - median error 0.181 m.

First run downloads the scene (~520 MB) and cuts the four 30-second clips.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import SCENES  # noqa: E402
from pipeline import run_case  # noqa: E402

from factory_vision.assets import (Requirements, adopt_mobileclip, ensure,  # noqa: E402
                                   place_mobileclip)
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)

NEEDS = Requirements(
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the warehouse scene is fetched by fetch_scene.py in this folder; "
           "run it once before main.py",),
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default=SCENES[0].name,
                    choices=[s.name for s in SCENES])
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args()

    cfg = next(s for s in SCENES if s.name == args.scene)
    print("=" * 74)
    print("CASE 6  |  Warehouse 3D localisation and eagle view")
    print(f"  scene : {cfg.scene}")
    print(f"  source: {cfg.source}")
    print("=" * 74)

    if not ensure(NEEDS, VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    if not (VIDEO_DIR / cfg.assets).exists():
        print(f"\n  input/{cfg.assets}/ is missing - the calibration, floor plan and")
        print("  ground truth live there. Run:  python fetch_scene.py")
        return 1

    print(f"\n  prompts: {cfg.prompts}   conf={cfg.conf}")
    print(f"  {len(cfg.views)} camera views")
    for v in cfg.views:
        print(f"  view {v.side:>5} r{v.row + 1}c{v.col + 1}   {v.sensor_id}")
    print(f"  fuse radius {cfg.fuse_radius_m} m")
    for kind, spec in cfg.classes.items():
        print(f"  class {kind:9s} prompt '{spec['prompt']}'  height {spec['height']} m"
              f"  footprint {spec['footprint']} m")
    print()

    summary = run_case(cfg.name, max_frames=args.max_frames, progress=args.progress)
    print(f"\n  video   output/{summary['output']}")
    adopt_mobileclip(WEIGHTS_DIR, Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
