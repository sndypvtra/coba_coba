#!/usr/bin/env python3
"""Case 6 - Warehouse: 3D localisation of people across four cameras, on one map.

The other five cases each answer a question inside a single frame. This one
answers a question about a *building*: where is everyone, how many are there
really, and what have they been doing on the floor.

That needs three things a single camera cannot give:

  a position in metres     - from the ground-plane homography, not from depth
                             regression. A person standing on a known floor has
                             one unknown left, and calibration supplies it.
  one identity per person  - four cameras produce four track IDs for the same
                             person, and adding them up counts a warehouse of
                             three as a warehouse of twelve.
  a shared frame           - the dataset's own top-down render of the building,
                             tied to world coordinates by a scale and an offset,
                             so a marker on it is where the person is standing.

Detection is still zero-shot: the prompt list is `person` and `humanoid robot`.
The second entry is not decoration. This warehouse contains two humanoid robots,
and a prompt list without a name for them does not leave them undetected - it
puts them in the headcount.

Everything is validated. The dataset ships the true 3D position of every object;
the pipeline never reads it, and the summary reports how far off it was.

Run:  python scripts/fetch_warehouse_scene.py      # once, ~520 MB
      python cases/case6_warehouse_spatial.py
"""

import argparse

from _common import ROOT, banner, report  # noqa: F401  (sets sys.path)

from factory_vision.spatial import SCENES, run_case


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default=SCENES[0].name,
                    choices=[s.name for s in SCENES])
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args()

    cfg = next(s for s in SCENES if s.name == args.scene)
    banner(6, "Warehouse 3D localisation and eagle view", cfg.scene, cfg.source)
    print(f"  prompts: {cfg.prompts}   conf={cfg.conf}")
    for v in cfg.views:
        print(f"  view {v.slot:<13} {v.sensor_id:<10} {v.provenance}")
    print(f"  fuse radius {cfg.fuse_radius_m} m   footprint {cfg.footprint_m} m   "
          f"height gate {cfg.height_bounds_m} m")
    print()

    summary = run_case(cfg.name, max_frames=args.max_frames, progress=args.progress)
    f, fu = summary["filtering"], summary["fusion"]
    val = summary.get("validation")

    lines = [
        ("Distinct people", summary["distinct_people"]),
        ("Distinct humanoid robots", summary["distinct_robots"]),
        ("On the floor, mean / max", f"{summary['occupancy_mean']} / {summary['occupancy_max']}"),
        ("Measured height, median", f"{summary['person_height_median_m']} m"),
        ("Floor walked", f"{summary['floor_walked_m']} m"),
        ("Walking speed, mean", f"{summary['walking_speed_mean_ms']} m/s"),
        ("Views per person, mean", fu["mean_views_per_person"]),
        ("Cross-camera agreement", f"{fu['cross_camera_agreement_m']} m"),
        ("Observations fused away", fu["observations_merged"]),
        ("Single-view identities dropped", fu["identities_dropped_as_single_view"]),
        ("Duplicate boxes removed", f["duplicate_boxes_removed"]),
        ("Clip duration", f"{summary['clip']['duration_seconds']} s"),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame (4 views)"),
    ]
    if val:
        lines += [
            ("-- against ground truth --", ""),
            ("Localisation error, median", f"{val['localisation_error_m']['median']} m"),
            ("Localisation error, p95", f"{val['localisation_error_m']['p95']} m"),
            ("Recall / precision", f"{val['recall']} / {val['precision']}"),
            ("Headcount exact", f"{val['count_error_per_frame']['frames_exact']}"
                                f" of {val['count_error_per_frame']['frames']} frames"),
            ("Global IDs per real person", val["id_fragmentation"]),
        ]
    report(summary, lines)

    print("  Position is a geometry result and is the reliable number here: it")
    print("  depends on the calibration and on the box bottom being the feet.")
    print("  The headcount and the dwell figures depend on identity surviving")
    print("  across cameras - 'global IDs per real person' is how often it did.")
    print()
    print("  Known limit, measured rather than hidden: this warehouse contains a")
    print("  human-shaped humanoid robot that no prompt separates from a person")
    print("  (1 of 43 detections across twelve prompt lists) and no height gate")
    print("  separates either - it stands 1.62-1.68 m against people at")
    print("  1.77-2.05 m, a 0.09 m margin under a +-0.27 m height error. It is")
    print("  therefore in the headcount. See docs/warehouse-spatial.md.\n")


if __name__ == "__main__":
    main()
