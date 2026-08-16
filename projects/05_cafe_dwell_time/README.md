# 05 — Cafe: occupancy and per-person dwell time

Two rooms of the same cafe. How many people are here, and how long did each of
them stay.

```bash
python main.py                              # scene 5
python main.py --clip cafe_scene1_30s.mp4   # scene 1
python main.py --all
```

| | scene 1 | scene 5 |
|---|:--:|:--:|
| **Distinct visitors** | 12 | 12 |
| Occupancy, mean / max | — | 9.0 / 10 |
| **Dwell, mean** | 24.6 s | **21.19 s** |
| Staff service time | — | 16.02 s |
| Duplicate boxes removed | — | 76 |
| Tracks with gaps | — | 1 of 12 |

## Files

| | |
|---|---|
| `main.py` | entry point |
| `config.py` | per-room zones: mirrors to exclude, the service point |
| `pipeline.py` | detect → track → role → dwell → render |
| `input/`, `output/` | the two pre-cut clips, and results |

## The two numbers are not equally good

**Occupancy is a detection result.** Count the people visible in a frame; no
identity required. It is the number to trust.

**Dwell time is a tracking result.** It needs one person to keep one ID while
someone walks in front of them. `tracks_with_gaps` reports how often that failed
— 1 of 12 here — and the visitor total inherits the same risk: a broken identity
becomes two visitors who each stayed half as long.

Reporting them as though they were equally reliable is the failure this project
is built to avoid.

## Why the mirror is excluded

A cafe mirror produces people who are genuinely there, in the image, and
genuinely not in the room. No confidence threshold separates a reflection from a
customer, because the reflection *is* a customer — just counted twice. The
exclusion zone is in `config.py` with the reason written next to it.

## Source clips

Cut from a long stock video rather than downloaded whole, so `input/` ships with
them rather than fetching by id.
