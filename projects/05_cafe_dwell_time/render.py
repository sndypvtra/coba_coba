"""Pass 2: replay the clip against the identities pass 1 settled on.

Separate from detection because the identity repair has to see the whole clip
before the first frame can be drawn - a track that is re-linked at frame 122
changes what should have been written at frame 1. Nothing is measured here; the
dwell counters are accumulated as the frames go by purely so the overlay can
show a running total, and they are the same counters the summary reports.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import cv2
import supervision as sv

import overlay


@dataclass
class Timeline:
    """Per-identity time on screen, and the room's occupancy frame by frame."""

    dwell: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    staff_dwell: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    series: list[int] = field(default_factory=list)


def render(src, out_path, obs, alias, merged, customers, staff_locked,
           cfg, info, merges_n) -> Timeline:
    """Write the annotated video and return the dwell timeline it accumulated."""
    w, h, fps = info.width, info.height, info.fps
    scale = w / 1920.0
    out_info = sv.VideoInfo(width=w + overlay.PANEL_W, height=h, fps=info.fps,
                            total_frames=info.total_frames)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    box_ann = overlay.box_annotator(scale)
    tl = Timeline()

    cap = cv2.VideoCapture(str(src))
    with sv.VideoSink(str(out_path), out_info, codec="mp4v") as sink:
        for i, row in enumerate(obs.frames):
            ok, frame = cap.read()
            if not ok:
                break
            live, stf = _split_by_role(row, alias, customers, staff_locked, tl)
            # Occupancy is how many people are in the room, so it counts staff
            # too - a server standing at the counter is a person present. The
            # visitor total is a different question and stays customers-only:
            # staff are not visits.
            tl.series.append(len(live) + len(stf))

            vis = overlay.draw_zones(frame.copy(), cfg.exclusion_zones, max(scale, 0.8))
            vis = overlay.draw_people(vis, live, stf, tl.dwell, tl.staff_dwell,
                                      fps, scale, box_ann)
            visitors_so_far = sum(1 for a in customers if merged[a]["first"] <= i + 1)
            sink.write_frame(overlay.compose(
                vis, len(live) + len(stf), visitors_so_far,
                i + 1, info.total_frames, fps, tl.dwell, {t for t, _ in live},
                tl.staff_dwell, {t for t, _ in stf},
                obs.zone_counts[i] if i < len(obs.zone_counts) else {},
                tl.series, cfg.exclusion_zones, obs.tracker_name, merges_n))
    cap.release()
    return tl


def _split_by_role(row, alias, customers, staff_locked, tl):
    """One frame's track list, divided by the role each identity was assigned.

    Re-linking can leave two boxes carrying one identity in the same frame - the
    dying track and the one that replaced it overlap for a frame or two - so the
    first box of an identity wins and the rest are dropped. Counting both would
    inflate occupancy and double that person's dwell.
    """
    seen_c, seen_s = set(), set()
    live, stf = [], []
    for t, b in row["people"]:
        root = alias.get(t, t)
        if root in staff_locked:
            if root in seen_s:
                continue
            seen_s.add(root)
            stf.append((root, b))
            tl.staff_dwell[root] += 1
        elif root in customers:
            if root in seen_c:
                continue
            seen_c.add(root)
            live.append((root, b))
            tl.dwell[root] += 1
    return live, stf
