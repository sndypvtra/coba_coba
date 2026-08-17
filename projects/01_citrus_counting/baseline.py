"""The numbers this project last produced, and a check against them.

A refactor that quietly moves a count is worse than one that crashes, because
nothing tells you. So the last verified run is written down here and every run
is compared against it - printed as a line in the report, not buried in a test
nobody runs.

These are *observations of this clip*, not targets. If a genuine improvement
moves one, the right response is to change the number here in the same commit
that changes the behaviour, and to say why in the commit message. What must
never happen is the number moving and nobody noticing.
"""

from __future__ import annotations

from dataclasses import dataclass

# Verified against the counting line at x=900, by hand, from the rendered video:
# five oranges complete a crossing in the 286 frames of this clip. The tracker
# holds far more identities than that - fruit enters and leaves at the frame
# edges without ever reaching the line - which is why tracks and counts are
# reported as separate figures and only the first is the answer.
COUNT = 5
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
