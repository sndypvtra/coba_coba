"""What the live dashboard shows on the tomato line.

Same shape as `01_citrus_counting/panel.py`, and that is the point: the two
projects differ in their words and their geometry, not in what they are able to
report. Both count, neither measures, so neither prints a size, a volume or a
depth model.

Before this file existed both inherited the parcel belt's dashboard from the
shared overlay - PARCEL UNLOADING, SIZE MIX `S0 M0 L0`, and a footer crediting
DA3 metric depth on a project that never loads it. A project now prints only
what it measures.
"""

from __future__ import annotations

from factory_vision.counting.overlay import INK, WARM, Panel

TITLE = "TOMATO GRADING LINE - LIVE"
NOUN = "TOMATOES COUNTED"


def build(stats: dict) -> Panel:
    """One frame's dashboard, from the counting stats the pipeline hands over."""
    return Panel(
        title=TITLE,
        headline=NOUN,
        subtitle=f"{stats['elapsed_s']:.1f} s elapsed  ·  in-focus lanes only",
        rows=[
            ("THROUGHPUT", f"{stats['per_hour']:,.0f} /h", WARM),
            ("IN VIEW NOW", f"{stats['active']}", INK),
            ("HEADWAY", f"{stats['headway_s']:.1f} s" if stats["headway_s"] else "-", WARM),
            ("TRACKS SEEN", f"{stats['tracks_seen']}", INK),
        ],
        # The blurred foreground lane is excluded by the y-ROI in config.py, so
        # the count is of the lanes in focus. Printing that on the frame stops
        # the number being read as "every tomato on the machine".
        footer="in-focus lanes only  ·  rate extrapolated from "
               f"{stats['elapsed_s']:.0f} s",
    )
