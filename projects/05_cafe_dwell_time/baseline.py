"""The numbers each room last produced, and a check against them.

This project needs the check more than the counting ones do, and the reason is
structural. Occupancy is a per-frame detection count and barely moves. Visitors
and dwell time are *identity* results, and identity here rests on constants that
look harmless in isolation - `min_similarity`, `max_gap_s`, `station_share` in
`identity.py`, `STAFF_ZONE_SHARE` in `roles.py`. Nudge any one of them and a
server becomes two people, or a customer becomes a server, with no error raised
and nothing in the console to notice.

That is not hypothetical. Before the station gates existed, a union-find chain
merged a track that was 68 % inside the service polygon with three tracks that
were 0 % inside it, and the server was reported as a customer for the first half
of the clip. Nothing failed. The video simply showed the room unattended.

So the figures below are pinned per room, and every run prints how it compares.

WHAT IS PINNED, AND WHAT IS NOT
-------------------------------
Pinned: the answers, and the diagnostics that reveal a behaviour change -
visitors, occupancy, dwell, service time, how much of that service was observed
rather than held, duplicates removed, re-links, fragmented tracks.

Not pinned: `avg_ms_per_frame`. That is the host's CPU load, not this code's
behaviour, and pinning it would cry wolf on every busy machine.

These are observations of two specific clips, not targets. If a genuine
improvement moves one, change it here in the same commit that changes the
behaviour and say why in the message. What must never happen is a figure moving
and nobody noticing.
"""

from __future__ import annotations

from dataclasses import dataclass

# Measured after the identity fixes: the overlap guard that stops one person
# being in two places, and the station gates that keep a server behind a counter
# from being split in half by the customers leaning on it.
ROOMS: dict[int, dict] = {
    5: {
        "visitors_total": 12,
        "occupancy_mean": 9.04,
        "occupancy_max": 10,
        "dwell_mean_seconds": 20.97,
        "staff_count": 1,
        "staff_service_seconds": 19.82,
        "duplicate_boxes_removed": 76,
        "tracks_relinked": 4,
        "tracks_with_gaps": 2,
    },
    1: {
        "visitors_total": 12,
        "occupancy_mean": 10.32,
        "occupancy_max": 12,
        "dwell_mean_seconds": 24.64,
        "staff_count": 1,
        "staff_service_seconds": 14.21,
        "duplicate_boxes_removed": 80,
        "tracks_relinked": 0,
        "tracks_with_gaps": 3,
    },
}


@dataclass
class Check:
    label: str
    expected: object
    actual: object

    @property
    def ok(self) -> bool:
        return self.expected == self.actual

    def __str__(self) -> str:
        mark = "OK  " if self.ok else "MOVED"
        tail = "" if self.ok else f"   (was {self.expected})"
        return f"{mark}  {self.label:<26} {self.actual}{tail}"


def check(scene_id: int, summary: dict) -> list[Check]:
    """Compare one room's fresh run against the last verified one."""
    want = ROOMS.get(scene_id)
    if want is None:
        return []
    got = {
        "visitors_total": summary["visitors_total"],
        "occupancy_mean": summary["occupancy_mean"],
        "occupancy_max": summary["occupancy_max"],
        "dwell_mean_seconds": summary["dwell_mean_seconds"],
        "staff_count": len(summary["staff"]),
        "staff_service_seconds": summary["staff_service_seconds"],
        "duplicate_boxes_removed": summary["filtering"]["duplicate_boxes_removed"],
        "tracks_relinked": summary["filtering"]["tracks_relinked"],
        "tracks_with_gaps": summary["quality"]["tracks_with_gaps"],
    }
    return [Check(k, want[k], got[k]) for k in want]
