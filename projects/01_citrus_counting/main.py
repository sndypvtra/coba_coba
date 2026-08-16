#!/usr/bin/env python3
"""Case 1 - Citrus sorting line: count oranges past a line, from words alone.

    python main.py

Everything missing is fetched first, with a progress bar. Nothing to install
by hand, no order to remember: the clip lands in `input/`, the weights in the
shared `weights/` at the repository root, and the result in `output/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import CLIP  # noqa: E402

from factory_vision.assets import Clip, Requirements, ensure, place_mobileclip  # noqa: E402
from factory_vision.counting import run_case  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)

NEEDS = Requirements(
    clips=(Clip("01_oranges_production_line.mp4", 10576687),),
    # The detector; the classifier is the tracker's re-identification backbone.
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the MobileCLIP text encoder (~572 MB) is fetched by ultralytics on "
           "the first get_text_pe() call",),
)


def main() -> int:
    print("=" * 74)
    print("CASE 1  |  Citrus sorting line - zero-shot counting")
    print(f"  scene : {CLIP.scene}")
    print(f"  source: {CLIP.source_url}")
    print("=" * 74)

    if not ensure(NEEDS, VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    print(f"\n  prompts: {CLIP.prompts}")
    print(f"  conf={CLIP.conf}  min_track_age={CLIP.min_track_age}  "
          f"belt motion={CLIP.motion} px/frame\n")

    summary = run_case(CLIP, VIDEO_DIR, OUTPUT_DIR)

    print("-" * 74)
    for label, value in (
        ("Counted (line crossings)", summary["count_total"]),
        ("Unique track IDs", summary["unique_track_ids"]),
        ("Reverse crossings", summary["count_reverse_crossings"]),
        ("Detections / frame", summary["avg_detections_per_frame"]),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame"),
    ):
        print(f"  {label:<28} {value}")
    print(f"  {'video':<28} output/{summary['output']}")
    print(f"  {'summary':<28} output/summary.json")
    print("-" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
