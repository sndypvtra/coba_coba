"""What the live dashboard shows on the citrus line.

This file exists because of a real defect. The panel used to be hardcoded in the
shared `factory_vision/counting/overlay.py`, written for the parcel belt, and
this project rendered its whole 286-frame video captioned **PARCEL UNLOADING -
LIVE**, counting **PARCELS**, with SIZE MIX `S0 M0 L0`, VOLUME RATE `0.0 m3/h`,
MEAN PARCEL `0 L`, LARGEST `-`, SIZES LOCKED `0` - and a footer reading
`yoloe-11l-seg + DA3 metric depth`, on a project that never loads DA3 at all.

Five structural zeros are bad. The footer was worse: nothing in the frame told
the viewer it was false.

So the rule this file enforces is simple - **a project prints only what it
measures**. There is no size, no volume and no depth model on a citrus line, so
there is no row for any of them here. Only rate, headway and what is in view.
"""

from __future__ import annotations

from factory_vision.counting.overlay import INK, WARM, Panel

TITLE = "CITRUS SORTING LINE - LIVE"
NOUN = "ORANGES COUNTED"


def build(stats: dict) -> Panel:
    """One frame's dashboard, from the counting stats the pipeline hands over."""
    return Panel(
        title=TITLE,
        headline=NOUN,
        subtitle=f"{stats['elapsed_s']:.1f} s elapsed  ·  roller conveyor",
        rows=[
            ("THROUGHPUT", f"{stats['per_hour']:,.0f} /h", WARM),
            ("IN VIEW NOW", f"{stats['active']}", INK),
            ("HEADWAY", f"{stats['headway_s']:.1f} s" if stats["headway_s"] else "-", WARM),
            ("TRACKS SEEN", f"{stats['tracks_seen']}", INK),
        ],
        # Rates come from a 9.5-second clip. Saying so on the frame is the
        # difference between a demonstration and a claim.
        footer="counted from words alone  ·  rate extrapolated from "
               f"{stats['elapsed_s']:.0f} s",
    )
