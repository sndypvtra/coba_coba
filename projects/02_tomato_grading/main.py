#!/usr/bin/env python3
"""Case 2 - Tomato grading line: the same engine, different words.

    python main.py

The only difference from project 01 is `config.py`. Same weights, same tracker,
same counting rule - one word changed and a line moved. That is the whole claim
of a zero-shot pipeline, and putting the two projects side by side is what makes
it checkable rather than asserted.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import CLIP  # noqa: E402

from factory_vision.assets import (Clip, Requirements, adopt_mobileclip, ensure,  # noqa: E402
                                   place_mobileclip)
from factory_vision.counting import run_case  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(__file__)

NEEDS = Requirements(
    clips=(Clip("02_tomatoes_conveyor.mp4", 8675102),),
    # The detector; the classifier is the tracker's re-identification backbone.
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    notes=("the MobileCLIP text encoder (~572 MB) is fetched by ultralytics on "
           "the first get_text_pe() call",),
)


def main() -> int:
    print("=" * 74)
    print("CASE 2  |  Tomato grading line - zero-shot counting")
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
    adopt_mobileclip(WEIGHTS_DIR, Path.cwd())
    print("-" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
