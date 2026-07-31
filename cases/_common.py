"""Shared bootstrap for the per-case scripts.

Puts the repository root on sys.path so each case can be run directly from
anywhere, e.g. `python cases/case1_oranges_counting.py`.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def banner(number: int, title: str, scene: str, source: str) -> None:
    print("=" * 74)
    print(f"CASE {number}  |  {title}")
    print(f"  scene : {scene}")
    print(f"  source: {source}")
    print("=" * 74)


def report(summary: dict, lines: list[tuple[str, str]]) -> None:
    print("-" * 74)
    for label, value in lines:
        print(f"  {label:<28} {value}")
    print(f"  {'output':<28} output/{summary['output']}")
    print("-" * 74)
