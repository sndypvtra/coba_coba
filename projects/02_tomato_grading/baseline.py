"""The numbers this project last produced, and a check against them.

Same purpose as `01_citrus_counting/baseline.py`: a refactor that quietly moves
a count is worse than one that crashes, because nothing tells you. Every run is
compared against the last verified one and the result is printed in the report.

These are *observations of this clip*, not targets. If a genuine improvement
moves one, change the number here in the same commit that changes the behaviour
and say why. What must never happen is the number moving and nobody noticing.
"""

from __future__ import annotations

from dataclasses import dataclass

# Counted across the line at x=1000, tilted 9.4 degrees off vertical to sit
# square across the lane. The blurred foreground lane is excluded by the y-ROI
# in config.py, so this is the count for the in-focus lanes - which is what the
# panel says on the frame, so the figure cannot be read as "every tomato on the
# machine".
COUNT = 16
REVERSE = 0


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


def check(summary: dict) -> list[Check]:
    """Compare a fresh run against the last verified one."""
    return [
        Check("counted", COUNT, summary["count_total"]),
        Check("reverse crossings", REVERSE, summary["count_reverse_crossings"]),
    ]
