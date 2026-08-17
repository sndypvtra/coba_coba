"""Repairing identities the tracker dropped.

Dwell time and the visitor total are only as good as identity assignment: if a
seated customer is occluded by someone walking past and comes back with a new
track ID, one 8-minute visit is reported as two 4-minute visits and the visitor
count goes up by one. Occupancy does not care - it is a per-frame detection
count - which is why occupancy is the number to trust and these two are the
numbers that need this module.

Nothing here invents an identity. It only joins two tracks the tracker already
produced, and every join is reported so the repair can be audited rather than
taken on faith.

TWO GATES, BECAUSE A COUNTER IS NOT A ROOM
------------------------------------------
Customers circulate; staff stand at a station. Measured on scene 5, the server
is tracked for the first 19 frames, hidden behind customers leaning on the
counter for the next 51, and picked up again for the last 80 - a 10.4 s gap, at
the same till, with a colour similarity of 0.84. The customer gates (3 s, 12 %
of the frame diagonal) reject that, so the room was reported as unattended for
the first half of the clip and the same server was counted as two people.

A service polygon is a fixed workplace, which is exactly the reasoning that put
the zones in `config.py` to begin with: nothing in a person's pixels says
"employee", and where they stand does. So two tracks that both sit
predominantly inside one service polygon get a longer gap and a looser
displacement - `station_*` below - while everyone else keeps the customer gates.

The limit of this is worth stating: two *different* people working the same
station in one clip would be joined into one. On a 30-second clip that is a
better bet than the alternative, and on a shift-length recording it would not
be - at which point the station gates need a face or a uniform, not a wider
tolerance.
"""

from __future__ import annotations

import cv2
import numpy as np

# How many frames of a track contribute to its colour signature. The first
# dozen is enough for a stable histogram and keeps the cost off the hot loop.
HIST_FRAMES = 12
HIST_BINS = (16, 16)


def appearance(frame, box) -> np.ndarray:
    """Hue/saturation histogram of a box interior, used to re-link broken tracks.

    Hue and saturation only: value is left out because it tracks the lighting a
    person walked through rather than the person.
    """
    x1, y1, x2, y2 = [int(v) for v in box]
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, frame.shape[1]), min(y2, frame.shape[0])
    if x2 - x1 < 4 or y2 - y1 < 4:
        return np.zeros(HIST_BINS, np.float32)
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, list(HIST_BINS), [0, 180, 0, 256])
    return cv2.normalize(hist, hist).astype(np.float32)


def merge_broken_tracks(tracks, fps, diag, max_gap_s=3.0,
                        max_move_frac=0.12, min_similarity=0.65,
                        station_share=0.6, station_max_gap_s=15.0,
                        station_max_move_frac=0.25):
    """Re-link a track that died to the one that replaced it.

    At 4.995 fps - the CAFE frames are every 6th of a 29.97 fps recording - a
    walking person crosses far more pixels between frames than a tracker's motion
    model expects, so a customer who is briefly occluded comes back as a new ID.
    Measured on scene 17 before this ran: seven tracks were born after frame 10,
    and the pattern was unmistakable (#2 died f116 / #27 born f122, #6 died f126 /
    #28 born f128).

    Two tracks are joined when the later one starts within `max_gap_s` of the
    earlier one ending, begins near where the earlier one stopped, and carries a
    similar colour histogram. All three must hold: time alone would merge
    strangers who swapped seats, and appearance alone would merge two customers
    in the same colour shirt.

    ONE PERSON CANNOT BE IN TWO PLACES
    ----------------------------------
    The pairwise rule above already refuses to join tracks that coexist - it
    needs ``gap > 0``, so the later track must begin after the earlier one ends.
    Union-find then broke that guarantee transitively, and on scene 5 it did:

        #15 -> #4   sim 0.53        both pass the pairwise test
        #15 -> #7   sim 0.82        and neither is compared to the other

    which quietly put #4 and #7 into one identity even though they overlap for
    22 frames - two boxes, in the same frames, in different places. That merged
    identity had 15 % of its frames inside the service polygon instead of #4's
    68 %, so the server it was built from was reported as a customer, and the
    room went unattended on screen for the first 70 frames.

    So a union is now refused when *any* member of one group shares a frame with
    *any* member of the other. It is the same physical claim the pairwise gap
    test makes, enforced over the whole group rather than over one pair, and it
    is the only one of these rules that is not a threshold: two boxes in one
    frame are two people, at any confidence, in any lighting.

    Returns an alias map (every track id -> the id it now belongs to), the list
    of joins made, and the list of joins refused for overlapping - the last so
    the console can say what it declined to do rather than silently not doing it.
    """
    ids = sorted(tracks)
    parent = {i: i for i in ids}
    members = {i: [i] for i in ids}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def coexist(x, y) -> bool:
        tx, ty = tracks[x], tracks[y]
        return not (tx["last"] < ty["first"] or ty["last"] < tx["first"])

    def at_station(t) -> bool:
        return t["in_zone"] / max(t["frames"], 1) >= station_share

    merges, refused = [], []
    for a in ids:
        for b in ids:
            if a == b:
                continue
            ta, tb = tracks[a], tracks[b]
            # A service station is a fixed workplace, so the gates for two
            # tracks that both live inside one are not the gates for two
            # customers. See the module docstring.
            station = at_station(ta) and at_station(tb)
            gap_limit = (station_max_gap_s if station else max_gap_s) * fps
            move_limit = station_max_move_frac if station else max_move_frac

            gap = tb["first"] - ta["last"]
            if not (0 < gap <= gap_limit):
                continue
            ca = ta["last_centre"]
            cb = tb["first_centre"]
            move = float(np.hypot(ca[0] - cb[0], ca[1] - cb[1])) / diag
            if move > move_limit:
                continue
            sim = float(cv2.compareHist(ta["hist"], tb["hist"], cv2.HISTCMP_CORREL))
            if sim < min_similarity:
                continue
            ra, rb = find(a), find(b)
            if ra == rb:
                continue
            clash = [(x, y) for x in members[ra] for y in members[rb] if coexist(x, y)]
            if clash:
                refused.append((b, a, clash[0]))
                continue
            parent[rb] = ra
            members[ra].extend(members[rb])
            members[rb] = []
            merges.append((b, a, round(gap / fps, 2), round(move, 3), round(sim, 3)))
    return {i: find(i) for i in ids}, merges, refused


def collapse(tracks: dict[int, dict], alias: dict[int, int]) -> dict[int, dict]:
    """Fold every track onto the identity it was aliased to.

    The result is one entry per *person*: when they were first and last seen,
    how many frames they were seen in, and how many of those sat inside a
    service polygon - which is all the role vote needs.
    """
    merged: dict[int, dict] = {}
    for tid, t in tracks.items():
        root = alias[tid]
        m = merged.setdefault(root, {"first": t["first"], "last": t["last"],
                                     "frames": 0, "in_zone": 0})
        m["first"] = min(m["first"], t["first"])
        m["last"] = max(m["last"], t["last"])
        m["frames"] += t["frames"]
        m["in_zone"] += t["in_zone"]
    return merged
