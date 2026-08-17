"""The console read-out, and the caveats that belong beside each number.

This is the only case that reports a *measurement* rather than a count, so it is
the only one whose read-out has to carry its own error budget. Three sections do
that work:

  the measurement chain   every constant the millimetres rest on - intrinsics,
                          the belt plane fit, the two calibration scales - so a
                          wrong dimension can be traced to the step that made it
  the per-parcel table    `top px` is the diagnostic column: how many pixels of
                          the parcel's top face the camera actually resolved
  the legend              what `*` and `?` mean, and why the fix is a second
                          camera rather than a better algorithm

A table of millimetres with none of that would read as more certain than it is.
"""

from __future__ import annotations


def banner(cfg) -> None:
    print("=" * 74)
    print("CASE 3  |  Parcel counting and dimensioning - zero-shot")
    print(f"  scene : {cfg.scene}")
    print(f"  source: {cfg.source_url}")
    print("=" * 74)


def settings(clip, sizing) -> None:
    """Two blocks, because they are two configs - see config.py."""
    print(f"\n  prompts: {clip.prompts}")
    print(f"  conf={clip.conf}  min_track_age={clip.min_track_age}  "
          f"belt motion={clip.motion} px/frame")
    print(f"  line   : x={clip.line_center[0]} plumb={clip.line_plumb} "
          f"span y={clip.line_span}")
    print(f"  size   : locked once the centre passes x={sizing.size_lock_x}")
    print(f"  depth  : every {sizing.depth_every} frames @ "
          f"{sizing.depth_process_res}px, corridor {sizing.depth_corridor} m, "
          f"base band {sizing.belt_base_band} m\n")


def headline(summary: dict, cfg, slit_scan_truth: int) -> None:
    """The counting result, against the frame-by-frame truth it was checked on."""
    dim = summary.get("dimensioning", {})
    print("-" * 74)
    for label, value in (
        ("Counted (line crossings)", f"{summary['count_total']}  "
                                     f"(slit-scan truth at x={cfg.line_center[0]}: "
                                     f"{slit_scan_truth})"),
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


def measurement_chain(dim: dict) -> None:
    """Every constant the millimetres rest on, with its measured residual."""
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
    print(f"    footprint     x{tuple(dim['footprint_scale'])} - "
          f"{dim['footprint_scale_note']}")


def parcel_table(dim: dict) -> None:
    print("\n  PER PARCEL  (L/W = footprint long/short side, H = above the belt)")
    print(f"    {'trk':>4} {'dist m':>7} {'L mm':>6} {'W mm':>6} {'H mm':>6} "
          f"{'vol L':>7} {'cls':>5} {'top px':>7} {'frames':>7}")
    for p in dim["parcels"]:
        print(f"    {p['track']:>4} {p['distance_m']:>7.2f} {p['length_mm']:>6} "
              f"{p['width_mm']:>6} {p['height_mm']:>6} {p['volume_l']:>7.1f} "
              f"{p['size_class'] + p.get('size_class_mark', ''):>5} "
              f"{p['top_face_px']:>7.1f} {p['frames_measured']:>7}")


def legend() -> None:
    """What the marks in the class column mean, and why they are there."""
    print("\n  READING THE SIZE CLASS")
    print("    *  the camera could not resolve this parcel's top face, so its")
    print("       footprint came from the calibrated correction: good to ~10%.")
    print("    ?  the longest side sits within that uncertainty of a class boundary.")
    print("    A lens 488 mm above a belt of 340 mm cartons sees 10-17 px of their")
    print("    tops. The remedy is a second view across the lane, not an algorithm.")
