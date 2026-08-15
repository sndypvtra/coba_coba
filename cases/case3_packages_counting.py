#!/usr/bin/env python3
"""Case 3 - Parcel unloading belt: count, range and dimension mixed packages.

Counting a parcel is the easy half. The half a depot actually bills on is *how
big it was*, and a single fixed camera has no way to answer that from pixels
alone - the same carton covers four times the area at half the distance. Depth
Anything 3 closes the gap: metric depth per pixel, and the camera intrinsics
that the metric model leaves out. From those, three numbers per parcel that no
2D pipeline can produce - distance, dimensions, volume.

Three things this case has to get right, and the evidence for each:

  every parcel detected   A slit-scan of the counting column - one pixel
                          column per frame, stacked - shows eight parcels
                          reaching the line, of which seven complete a
                          crossing: the eighth one's leading edge passes at
                          frame 480, its centre stalls 44 px short, and the
                          belt decelerates from -5.03 to -1.37 px/frame as the
                          unload ends. So the count to hit is seven. What the
                          0.15 confidence floor cost was not the count but the
                          *sight* of the faint parcels (0.098, 0.10, 0.12) -
                          and one of those cleared every filter and still had
                          no box, because a 0.098 detection cannot reach the
                          tracker's new_track_thresh of 0.20. The prompt fixed
                          it, not the gate.
  the line square and long
                          The counting line is a plane cut across the belt, and
                          that plane is vertical. The normal of the *image*
                          motion is not: the belt recedes as it crosses frame,
                          so its normal sits 3.2 deg off plumb. With no camera
                          roll to correct for (-0.4 deg on the trailer's door
                          post) the line is snapped upright and drawn the full
                          working height of the lane.
  size from pixels        pixels x distance / focal, measured against the belt
                          plane rather than the image axes, so a carton at an
                          angle is not read as wider than it is.

Run:  python cases/case3_packages_counting.py
"""

from _common import ROOT, banner, report  # noqa: F401

from factory_vision.counting import CLIPS, run_case

CLIP = "03_packages_conveyor.mp4"


def main() -> None:
    cfg = next(c for c in CLIPS if c.filename == CLIP)
    banner(3, "Parcel counting and dimensioning (zero-shot)", cfg.scene, cfg.source_url)
    print(f"  prompts: {cfg.prompts}")
    print(f"  conf={cfg.conf}  min_track_age={cfg.min_track_age}  "
          f"belt motion={cfg.motion} px/frame")
    print(f"  line   : plumb={cfg.line_plumb}  span y={cfg.line_span}")
    print(f"  depth  : every {cfg.depth_every} frames @ {cfg.depth_process_res}px, "
          f"corridor {cfg.depth_corridor} m")
    print(f"  note   : {cfg.extra_notes}\n")

    summary = run_case(CLIP)
    dim = summary.get("dimensioning", {})

    report(summary, [
        ("Counted (line crossings)", f"{summary['count_total']}  "
                                     f"(slit-scan truth: 7 centres cross, 8 reach the line)"),
        ("Unique track IDs", summary["unique_track_ids"]),
        ("Reverse crossings", summary["count_reverse_crossings"]),
        ("Detections / frame", summary["avg_detections_per_frame"]),
        ("Dropped outside corridor", dim.get("detections_outside_corridor", "-")),
        ("Parcels dimensioned", dim.get("parcels_measured", "-")),
        ("Total volume on belt", f"{dim.get('total_volume_l', 0):.0f} L"),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame detect"
                  f" + {dim.get('avg_depth_ms', 0):.0f} ms/frame depth"),
    ])

    if not dim:
        return

    K = dim["intrinsics"]
    print("\n  MEASUREMENT CHAIN")
    print(f"    {dim['method']}")
    print(f"    intrinsics    fx={K['fx']:.0f} fy={K['fy']:.0f}  hFOV {K['hfov_deg']:.1f} deg"
          f"   spread {K['frame_to_frame_spread_pct']:.1f}%"
          f"   square-pixel error {K['square_pixel_error_pct']:.1f}%")
    print(f"                  {K['note']}")
    b = dim["belt_plane"]
    print(f"    belt plane    residual {b['fit_rms_mm']:.1f} mm over {b['pixels']:,} px"
          f"   camera {b['camera_height_above_belt_mm']} mm above the belt")
    print(f"    size scale    x{dim['size_scale']:.4f}  - {dim['size_scale_note']}")

    print("\n  PER PARCEL  (L/W = footprint long/short side, H = above the belt)")
    print(f"    {'trk':>4} {'dist m':>7} {'L mm':>6} {'W mm':>6} {'H mm':>6} "
          f"{'vol L':>7} {'cls':>4} {'frames':>7} {'H IQR':>6}")
    for p in dim["parcels"]:
        print(f"    {p['track']:>4} {p['distance_m']:>7.2f} {p['length_mm']:>6} "
              f"{p['width_mm']:>6} {p['height_mm']:>6} {p['volume_l']:>7.1f} "
              f"{p['size_class']:>4} {p['frames_measured']:>7} {p['height_iqr_mm']:>6}")

    print("\n  WHAT THIS DOES NOT MEASURE")
    print("    A single camera sees the front of a parcel and not its back, so the")
    print("    footprint's short side is a lower bound whenever no side face is in view.")
    print("    Height does not have that problem - base on a fitted plane, top against")
    print("    open air - which is why the scale is calibrated on height alone.")


if __name__ == "__main__":
    main()
