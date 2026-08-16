#!/usr/bin/env python3
"""Case 3 - Parcel belt: count, range and dimension mixed packages.

    python main.py

The heaviest of the six to set up, and all of it automatic: two Depth Anything 3
checkpoints (~2.9 GB) arrive alongside the detector on first run. They are the
reason this project can answer *how big was it* from a single fixed camera, and
they are cached afterwards - both by Hugging Face, and per-frame by the pipeline
itself in `output/.depth_cache`, so a second run costs a fraction of the first.
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
    clips=(Clip("03_packages_conveyor.mp4", 5370836),),
    weights=("yoloe-11l-seg.pt", "yolo11n-cls.pt"),
    # DA3 splits metric depth across two checkpoints: the metric head returns
    # depth divided by focal length, and the geometry model supplies the focal.
    hub_models=("depth-anything/DA3METRIC-LARGE", "depth-anything/DA3-LARGE"),
    notes=("Depth Anything 3 must be installed separately - see this project's "
           "README; without it, set measure_size=False in config.py to count only",),
)


def main() -> int:
    print("=" * 74)
    print("CASE 3  |  Parcel counting and dimensioning - zero-shot")
    print(f"  scene : {CLIP.scene}")
    print(f"  source: {CLIP.source_url}")
    print("=" * 74)

    if not ensure(NEEDS, VIDEO_DIR, WEIGHTS_DIR):
        print("\nSome assets could not be fetched; see above.")
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())

    print(f"\n  prompts: {CLIP.prompts}")
    print(f"  conf={CLIP.conf}  min_track_age={CLIP.min_track_age}  "
          f"belt motion={CLIP.motion} px/frame")
    print(f"  line   : x={CLIP.line_center[0]} plumb={CLIP.line_plumb} "
          f"span y={CLIP.line_span}")
    print(f"  size   : locked once the centre passes x={CLIP.size_lock_x}")
    print(f"  depth  : every {CLIP.depth_every} frames @ {CLIP.depth_process_res}px, "
          f"corridor {CLIP.depth_corridor} m, base band {CLIP.belt_base_band} m\n")

    summary = run_case(CLIP, VIDEO_DIR, OUTPUT_DIR)
    dim = summary.get("dimensioning", {})

    print("-" * 74)
    for label, value in (
        ("Counted (line crossings)", f"{summary['count_total']}  "
                                     f"(slit-scan truth at x={CLIP.line_center[0]}: 8)"),
        ("Unique track IDs", summary["unique_track_ids"]),
        ("Reverse crossings", summary["count_reverse_crossings"]),
        ("Detections / frame", summary["avg_detections_per_frame"]),
        ("Rejected off the belt", dim.get("detections_outside_corridor", "-")),
        ("Parcels dimensioned", dim.get("parcels_measured", "-")),
        ("Total volume", f"{dim.get('total_volume_l', 0):.0f} L"),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame detect"
                  f" + {dim.get('avg_depth_ms') or 0:.0f} ms/frame depth"),
    ):
        print(f"  {label:<28} {value}")
    print(f"  {'video':<28} output/{summary['output']}")
    print("-" * 74)

    if not dim:
        return 0

    K = dim["intrinsics"]
    print("\n  MEASUREMENT CHAIN")
    print(f"    {dim['method']}")
    print(f"    intrinsics    fx={K['fx']:.0f} fy={K['fy']:.0f}  "
          f"hFOV {K['hfov_deg']:.1f} deg   spread {K['frame_to_frame_spread_pct']:.1f}%"
          f"   square-pixel error {K['square_pixel_error_pct']:.1f}%")
    b = dim["belt_plane"]
    print(f"    belt plane    residual {b['fit_rms_mm']:.1f} mm over {b['pixels']:,} px"
          f"   camera {b['camera_height_above_belt_mm']} mm above the belt")
    print(f"    size scale    x{dim['size_scale']:.4f} - {dim['size_scale_note']}")
    print(f"    footprint     x{tuple(dim['footprint_scale'])} - {dim['footprint_scale_note']}")

    print("\n  PER PARCEL  (L/W = footprint long/short side, H = above the belt)")
    print(f"    {'trk':>4} {'dist m':>7} {'L mm':>6} {'W mm':>6} {'H mm':>6} "
          f"{'vol L':>7} {'cls':>5} {'top px':>7} {'frames':>7}")
    for p in dim["parcels"]:
        print(f"    {p['track']:>4} {p['distance_m']:>7.2f} {p['length_mm']:>6} "
              f"{p['width_mm']:>6} {p['height_mm']:>6} {p['volume_l']:>7.1f} "
              f"{p['size_class'] + p.get('size_class_mark', ''):>5} "
              f"{p['top_face_px']:>7.1f} {p['frames_measured']:>7}")

    print("\n  READING THE SIZE CLASS")
    print("    *  the camera could not resolve this parcel's top face, so its")
    print("       footprint came from the calibrated correction: good to ~10%.")
    print("    ?  the longest side sits within that uncertainty of a class boundary.")
    print("    A lens 488 mm above a belt of 340 mm cartons sees 10-17 px of their")
    print("    tops. The remedy is a second view across the lane, not an algorithm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
