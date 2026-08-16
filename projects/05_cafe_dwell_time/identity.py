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
                        max_move_frac=0.12, min_similarity=0.45):
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

    Returns an alias map (every track id -> the id it now belongs to) and the
    list of joins made, for the summary and the console.
    """
    ids = sorted(tracks)
    parent = {i: i for i in ids}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    max_gap = max_gap_s * fps
    merges = []
    for a in ids:
        for b in ids:
            if a == b:
                continue
            ta, tb = tracks[a], tracks[b]
            gap = tb["first"] - ta["last"]
            if not (0 < gap <= max_gap):
                continue
            ca = ta["last_centre"]
            cb = tb["first_centre"]
            move = float(np.hypot(ca[0] - cb[0], ca[1] - cb[1])) / diag
            if move > max_move_frac:
                continue
            sim = float(cv2.compareHist(ta["hist"], tb["hist"], cv2.HISTCMP_CORREL))
            if sim < min_similarity:
                continue
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
                merges.append((b, a, round(gap / fps, 2), round(move, 3), round(sim, 3)))
    return {i: find(i) for i in ids}, merges


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
