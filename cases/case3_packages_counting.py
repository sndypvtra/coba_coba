#!/usr/bin/env python3
"""Case 3 - Parcel unloading belt: count, range and dimension mixed packages.

Counting a parcel is the easy half. The half a depot actually bills on is *how
big it was*, and a single fixed camera has no way to answer that from pixels
alone - the same carton covers four times the area at half the distance. Depth
Anything 3 closes the gap: metric depth per pixel, and the camera intrinsics
that the metric model leaves out. From those, three numbers per parcel that no
2D pipeline can produce - distance, dimensions, volume.

Three things this case has to get right, and the evidence for each:

  every parcel detected   Background is rejected on *geometry* - a depth
                          corridor plus a test that the parcel's base sits on
                          the fitted belt plane - before the tracker is ever
                          asked to hold an identity. That is what lets the
                          confidence floor sit at 0.05 and the tracker's spawn
                          gate at 0.07, which is what it takes to see every
                          parcel: several at the tail of the clip score 0.05 to
                          0.10 and one, at 0.65, carried no box at all purely
                          because the old spawn gate was 0.20.
  the line at the exit    Placed where the belt is nearest the camera (2.20 m,
                          against 2.90 m at the entry), because that is where
                          one image pixel is smallest on the belt and every
                          measurement is best conditioned. It is snapped plumb:
                          the line is a vertical plane cut across the belt, and
                          the normal of the *image* motion is 3.3 deg off that,
                          which is perspective in the flow rather than a
                          property of the cut.
  size locked before it   Frozen 170 px before the line, so a parcel is not
                          still revising its own dimensions at the moment it is
                          clipped by the frame edge and counted. What is
                          counted and what is measured are the same number.
  a panel of rates        Throughput, volume rate, headway and size mix - the
                          numbers a shift is staffed and a chute is sized
                          against. The model and tracker names moved to
                          summary.json, where a decision never needed them.

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
    print(f"  line   : x={cfg.line_center[0]} plumb={cfg.line_plumb} span y={cfg.line_span}")
    print(f"  size   : locked once the centre passes x={cfg.size_lock_x}")
    print(f"  depth  : every {cfg.depth_every} frames @ {cfg.depth_process_res}px, "
          f"corridor {cfg.depth_corridor} m, base band {cfg.belt_base_band} m")
    print(f"  note   : {cfg.extra_notes}\n")

    summary = run_case(CLIP)
    dim = summary.get("dimensioning", {})

    report(summary, [
        ("Counted (line crossings)", f"{summary['count_total']}  "
                                     f"(slit-scan truth at x={cfg.line_center[0]}: 8)"),
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
