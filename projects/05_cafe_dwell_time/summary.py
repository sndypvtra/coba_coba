"""The result record: what was measured, and how much of it to believe.

`quality` and `filtering` are not decoration. Occupancy is a detection result
and holds up on its own; dwell time and the visitor total additionally need an
identity to survive people walking behind each other, and this file is where
that dependency is written down instead of being left for the reader to guess.

The one number to check before quoting a dwell time is `continuity`: frames
actually seen divided by the first-to-last span. Below 1.0 the track was lost
and re-acquired, and re-linking joins the obvious cases but cannot join every
one.
"""

from __future__ import annotations

import json

import numpy as np

import roles


def build(cfg, args, obs, merged, customers, staff_locked, timeline, merges,
          out_path, info) -> dict:
    fps = info.fps
    people = _people(customers, merged, timeline.dwell, fps)
    staff = _staff(staff_locked, merged, timeline.staff_dwell, obs.frames, fps)
    dwells = [p["dwell_seconds"] for p in people]
    series = timeline.series

    return {
        "video": cfg.filename, "scene": cfg.scene, "source": cfg.source,
        "output": out_path.name, "resolution": f"{info.width}x{info.height}",
        "fps": round(fps, 3), "frames": len(obs.frames),
        "duration_seconds": round(len(obs.frames) / fps, 1),
        "model": args.weights.replace(".pt", ""), "prompts": cfg.prompts,
        "conf": cfg.conf, "tracker": "TrackTrack (CVPR 2025) + ReID + GMC",
        "visitors_total": len(customers),
        "occupancy_includes_staff": True,
        "occupancy_mean": round(float(np.mean(series)), 2) if series else 0,
        "occupancy_max": int(np.max(series)) if series else 0,
        "dwell_mean_seconds": round(float(np.mean(dwells)), 2) if dwells else 0,
        "dwell_max_seconds": round(float(np.max(dwells)), 2) if dwells else 0,
        "staff": staff,
        "staff_service_seconds": round(sum(s["service_seconds"] for s in staff), 2),
        "filtering": {
            "detections_before_filters": obs.raw_detections,
            "duplicate_boxes_removed": obs.duplicates_dropped,
            "zones": [{"name": z.name, "mode": z.mode, "reason": z.reason,
                       "min_overlap": z.min_overlap} for z in cfg.exclusion_zones],
            "tracks_relinked": len(merges),
            "relink_detail": [{"from": b, "into": a, "gap_seconds": g,
                               "moved_frac": mv, "appearance": s}
                              for b, a, g, mv, s in merges],
        },
        "quality": {
            "tracks_with_gaps": sum(1 for p in people if p["continuity"] < 0.8),
            "worst_continuity": round(min((p["continuity"] for p in people),
                                          default=1.0), 3),
            "note": ("continuity = frames actually seen / first-to-last span. "
                     "Below 1.0 the track was lost and re-acquired; re-linking "
                     "joins the obvious cases but cannot join every one."),
        },
        "avg_ms_per_frame": obs.avg_ms,
        "occupancy_series": series, "people": people, "notes": cfg.notes,
    }


def _people(customers, merged, dwell, fps) -> list[dict]:
    return [{"track_id": r, "first_frame": merged[r]["first"],
             "last_frame": merged[r]["last"], "frames_seen": dwell[r],
             "dwell_seconds": round(dwell[r] / fps, 2),
             "span_seconds": round((merged[r]["last"] - merged[r]["first"] + 1) / fps, 2),
             "continuity": round(dwell[r] / max(merged[r]["last"]
                                                - merged[r]["first"] + 1, 1), 3)}
            for r in sorted(customers)]


def _staff(staff_locked, merged, staff_dwell, frames_data, fps) -> list[dict]:
    """Held frames are reported apart from detected ones, never folded in."""
    held = roles.held_frames_per_track(frames_data)
    return [{"track_id": t,
             "service_seconds": round(staff_dwell[t] / fps, 2),
             "frames_total": staff_dwell[t],
             "frames_detected": staff_dwell[t] - held[t],
             "frames_held": held[t],
             "zone_share": round(merged[t]["in_zone"] / max(merged[t]["frames"], 1), 3)}
            for t in sorted(staff_locked)]


def write(summary: dict, output_dir, filename: str) -> None:
    name = filename.replace(".mp4", "__dwell.json")
    (output_dir / name).write_text(json.dumps(summary, indent=2))
