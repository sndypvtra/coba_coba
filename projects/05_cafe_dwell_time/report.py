"""The console read-out for one room.

Kept apart from `main.py` so the entry point is the sequence of steps and this
is the wording. The closing note is not filler: occupancy and dwell time come
out of the same run but do not deserve the same confidence, and a table that
prints them in the same typeface without saying so is misleading.
"""

from __future__ import annotations


def rooms(selected, others) -> None:
    """Say which room is being measured, and which ones are not.

    A default run measures one room. Without this line it looks like the whole
    project, and the second room stays invisible to anyone who does not read
    the argument parser.
    """
    which = ", ".join(f"scene {c.scene_id}" for c in selected)
    print(f"\n  measuring: {which}")
    if others:
        rest = ", ".join(f"--scene {c.scene_id}" for c in others)
        print(f"  not run  : {rest}   (or --all for every room)")


def banner(cfg) -> None:
    print("=" * 74)
    print(f"CASE 5  |  Cafe occupancy and dwell time - scene {cfg.scene_id}")
    print(f"  scene : {cfg.scene}")
    print(f"  source: {cfg.source}")
    print("=" * 74)
    print(f"  prompts: {cfg.prompts}")
    print(f"  conf={cfg.conf}  min_track_age={cfg.min_track_age}  "
          f"dedup={cfg.dedup_containment}")
    for z in cfg.exclusion_zones:
        print(f"  zone '{z.name}': {z.reason}")
    print()


def results(summary: dict) -> None:
    q, f = summary["quality"], summary["filtering"]
    print("-" * 74)
    for label, value in (
        ("Distinct visitors", summary["visitors_total"]),
        ("Occupancy, mean", summary["occupancy_mean"]),
        ("Occupancy, max", summary["occupancy_max"]),
        ("Dwell, mean", f"{summary['dwell_mean_seconds']} s"),
        ("Dwell, max", f"{summary['dwell_max_seconds']} s"),
        ("Clip duration", f"{summary['duration_seconds']} s"),
        ("Duplicate boxes removed", f["duplicate_boxes_removed"]),
        ("Broken tracks re-linked", f["tracks_relinked"]),
        ("Staff service time", f"{summary['staff_service_seconds']} s"
                               if summary["staff"] else "no service point"),
        ("Tracks with gaps", f"{q['tracks_with_gaps']} of {summary['visitors_total']}"),
        ("Speed", f"{summary['avg_ms_per_frame']:.0f} ms/frame"),
    ):
        print(f"  {label:<28} {value}")
    print(f"  {'video':<28} output/{summary['output']}")
    print("-" * 74)
    print("  Occupancy is a detection result and is the reliable number here.")
    print("  Dwell time and the visitor total depend on identity holding across")
    print("  occlusions; 'tracks with gaps' is how often it did not.\n")


def clips_not_found(missing: list[str]) -> None:
    """Both clips are committed, so this means the checkout is incomplete.

    Worth saying explicitly. Every other project would answer "it will download
    on the next run"; here it will not, because CAFE has no fetchable API, so
    the remedy is to restore the file rather than to re-run.
    """
    print(f"\n  input/ is missing {missing}.")
    print("  These clips are committed to the repository - they are not fetched -")
    print("  so a missing one means an incomplete checkout rather than a failed")
    print("  download. Restore it with:")
    print("      git checkout -- projects/05_cafe_dwell_time/input/")
    print("  README.md records where the footage comes from and how it was cut.")
