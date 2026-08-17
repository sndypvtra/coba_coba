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

import numpy as np

import zones

# Share of a track's frames that must sit inside a service polygon before the
# person is called staff. A server working a station spends nearly all of theirs
# there; a customer who steps up to order spends only the ordering part of a
# longer track.
STAFF_ZONE_SHARE = 0.6

# How much taller than her established size a station worker's box may get
# before it has plainly annexed somebody standing in front of her.
#
# One-sided on purpose. A box that *shrinks* is a person partly hidden - the
# scene 5 server drops to 0.69 of her median height when a customer covers her
# shoulder, and that is still her. A box that grows has taken in something that
# is not her, because she stands at a fixed distance from a fixed camera and
# cannot become half again as tall.
#
# The value is insensitive, which is what makes it trustworthy rather than
# tuned: her legitimate in-zone heights top out at 1.04 of the median and the
# annexed ones start at 1.64, so every gate from 1.3 to 1.6 drops exactly the
# same six observations. 1.5 sits in the middle of that empty band.
STATION_MAX_GROWTH = 1.5


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


def confine_to_station(frames_data, alias, staff_locked, zone_list, masks,
                       w: int, h: int, max_growth: float = STATION_MAX_GROWTH) -> int:
    """Drop a staff identity's observations that have left the service polygon.

    This exists because of a failure that no step-wise test catches. A tracker
    box does not always jump from one person to another - sometimes it *slides*.
    Measured on scene 5, the server's box grew from 127x166 at f1 to 197x601 by
    f15 while its centre drifted 330 px right and down, swallowing the customer
    standing in front of her and finally settling on him alone. Every single
    step was innocent: displacement 0.03-0.26 body widths, colour correlation
    0.81-0.94, because she wears black and so does he. The identity was stolen
    a few pixels at a time.

    The repair is not another threshold on the pixels. It is the domain fact
    that a station worker is *at the station*: the polygon in `config.py` is
    where the work happens, and an observation outside it is not service,
    whatever the tracker believes. So a staff identity keeps only the frames
    whose centre is inside its zone.

    Two things fall out of this at once. The drifting box stops being drawn on
    the wrong person, and the service figure finally matches what the panel has
    always called it - "time inside the service ROI" - where before it counted
    every frame of the identity, off-station ones included.

    A server who steps out to clear a table is therefore not on service time
    while she is away, which is the right reading of the phrase and the one a
    manager would expect.

    TWO TESTS, BECAUSE THE POLYGON ALONE IS NOT ENOUGH
    --------------------------------------------------
    On scene 5 the sliding box kept its *centre* inside the polygon for six
    frames after it had already swallowed the customer - the service zone is a
    wide strip along the top of the frame, so a box can grow downwards into the
    room and still be centred in it. Those six frames still drew PELAYAN on the
    wrong man.

    So an observation is kept only if it is both at the station and still her
    size. Her in-zone box holds 163-172 px for the first seven frames and then
    jumps to 270-347 while the annexation happens; see `STATION_MAX_GROWTH`.

    Mutates `frames_data` in place; returns how many observations were dropped.
    """
    if not staff_locked:
        return 0

    # Her own size, from the frames where she was demonstrably at the station.
    # A median, so the drifted frames cannot define the reference they are
    # supposed to be measured against.
    at_station: dict[int, list[float]] = defaultdict(list)
    for row in frames_data:
        for tid, box in row["people"]:
            root = alias.get(tid, tid)
            if root not in staff_locked:
                continue
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            if zones.staff_zone_at(cx, cy, zone_list, masks, w, h):
                at_station[root].append(float(box[3] - box[1]))
    reference = {root: float(np.median(hs)) for root, hs in at_station.items() if hs}

    dropped = 0
    for row in frames_data:
        keep = []
        for tid, box in row["people"]:
            root = alias.get(tid, tid)
            if root in staff_locked:
                cx = int((box[0] + box[2]) / 2)
                cy = int((box[1] + box[3]) / 2)
                ref = reference.get(root)
                off_station = not zones.staff_zone_at(cx, cy, zone_list, masks, w, h)
                annexed = ref is not None and (box[3] - box[1]) > max_growth * ref
                if off_station or annexed:
                    dropped += 1
                    continue
            keep.append((tid, box))
        row["people"] = keep
    return dropped


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
