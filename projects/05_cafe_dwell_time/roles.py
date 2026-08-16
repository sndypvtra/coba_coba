"""Staff or customer - decided once per person, not once per frame.

A role is a property of a person. Deciding it per frame, from how much of a box
fell inside the service polygon, is what let a server acquire a visitor
identity: measured on scene 1, she registered as staff in only 71 of 150 frames
and her leftovers surfaced as customer tracks #49 and #52. So the vote is taken
here, after tracking, over a whole track's history.

Both numbers a room is judged on depend on this split:

  visitors   customers only - a shift is not a visit
  service    staff only, reported separately, because how long a server spent
             attending the counter is the one measurement a manager wants from
             them and dropping staff outright throws it away
"""

from __future__ import annotations

from collections import defaultdict

# Share of a track's frames that must sit inside a service polygon before the
# person is called staff. A server working a station spends nearly all of theirs
# there; a customer who steps up to order spends only the ordering part of a
# longer track.
STAFF_ZONE_SHARE = 0.6


def classify(merged, cfg, min_fraction: float = STAFF_ZONE_SHARE):
    """Split identities into customers and staff.

    Pairing the zone share with a minimum duration keeps a brief visit to the
    counter from reading as staff. Measured on scene 5: the real server holds
    107 frames, while two customers who happened to stand at the counter early
    in the clip produced 9- and 5-frame tracks and were reported as staff. A
    server attends a station; a customer passes one.
    """
    staff, customers = set(), set()
    for root, t in merged.items():
        if t["frames"] < cfg.min_track_age:
            continue
        share = t["in_zone"] / max(t["frames"], 1)
        if share >= min_fraction and t["frames"] >= cfg.min_staff_frames:
            staff.add(root)
        else:
            customers.add(root)
    return customers, staff


def zone_shares(merged) -> list[tuple[float, int, dict]]:
    """Every identity that touched a service zone, most-of-the-time first."""
    return sorted(((t["in_zone"] / max(t["frames"], 1), r, t)
                   for r, t in merged.items() if t["in_zone"]), reverse=True)


def hold_across_gaps(frames_data, alias, staff_locked, hold: int) -> int:
    """Carry a confirmed staff track over short gaps of missed detection.

    The counter in scene 1 is deep in the room and backlit by the menu boards,
    and equipment on the counter top keeps cutting the server in half - she
    appears in roughly half the sampled frames at the room threshold. Holding
    her box across a gap she was demonstrably present through is the honest
    reading; the held frames are counted separately from detected ones in the
    summary so the interpolation is never passed off as observation.

    Mutates `frames_data` in place and returns how many frames were filled.
    """
    if not hold or not staff_locked:
        return 0
    seen_at: dict[int, dict[int, list]] = defaultdict(dict)
    for i, row in enumerate(frames_data):
        for tid, box in row["people"]:
            seen_at[alias[tid]][i] = box
    held_total = 0
    for tid in staff_locked:
        fr = sorted(seen_at[tid])
        for a, b in zip(fr, fr[1:]):
            gap = b - a - 1
            if 0 < gap <= hold:
                for k in range(a + 1, b):
                    frames_data[k]["people"].append((tid, seen_at[tid][a]))
                    frames_data[k].setdefault("held", set()).add(tid)
                    held_total += 1
    return held_total


def held_frames_per_track(frames_data) -> dict[int, int]:
    """How many of each staff track's frames were interpolated rather than seen."""
    per_track: dict[int, int] = defaultdict(int)
    for row in frames_data:
        for tid in row.get("held", ()):
            per_track[tid] += 1
    return per_track
