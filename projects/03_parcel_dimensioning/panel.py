"""What the live dashboard shows on the parcel belt.

This is the one project of the three that may print a size, because it is the
one that measures. The rows below all trace back to `measurement.py`, and every
one of them would be a structural zero anywhere else - which is exactly why they
live here and not in the shared overlay.

What a depot runs on is not the count. It is rate, volume rate, headway and the
size mix it bills on; what is on the belt right now is what a supervisor uses to
decide whether to open another lane. The model name, the prompt list and the
tracker are true and none of them is a decision, so they sit in `summary.json`
and once, small, in the footer.
"""

from __future__ import annotations

from factory_vision.counting.overlay import INK, WARM, Panel

TITLE = "PARCEL UNLOADING - LIVE"
NOUN = "PARCELS COUNTED"


def build(stats: dict) -> Panel:
    """One frame's dashboard, from counting stats merged with measured ones."""
    big = stats.get("largest")
    mix = stats.get("mix", {})
    return Panel(
        title=TITLE,
        headline=NOUN,
        subtitle=f"{stats['elapsed_s']:.1f} s  ·  {stats.get('volume_l', 0):.0f} L handled",
        rows=[
            ("THROUGHPUT", f"{stats['per_hour']:,.0f} /h", WARM),
            ("SIZE MIX",
             f"S{mix.get('S', 0)}  M{mix.get('M', 0)}  L{mix.get('L', 0)}", INK),
            ("VOLUME RATE", f"{stats.get('m3_per_hour', 0):.1f} m3/h", WARM),
            ("MEAN PARCEL", f"{stats.get('mean_volume_l', 0):.0f} L", INK),
            ("HEADWAY", f"{stats['headway_s']:.1f} s" if stats["headway_s"] else "-", WARM),
            ("LARGEST",
             f"{big.length_m*100:.0f}x{big.width_m*100:.0f}x{big.height_m*100:.0f}"
             if big else "-", INK),
            ("ON BELT NOW",
             f"{stats.get('on_belt', 0)}  ·  {stats.get('on_belt_l', 0):.0f} L", INK),
            ("SIZES LOCKED", f"{stats.get('locked', 0)}", INK),
        ],
        footer=f"sizes frozen before the line  ·  rates extrapolated from "
               f"{stats['elapsed_s']:.0f} s  ·  DA3 metric depth",
    )
