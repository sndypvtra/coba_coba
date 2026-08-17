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
| `assets.py` | what has to be present before a run |
| `zones.py` | frame regions that are not ordinary customers — geometry only |
| `detection.py` | pass 1 — detect, filter by zone, track, describe |
| `identity.py` | re-linking tracks the tracker broke on occlusion |
| `roles.py` | staff or customer, decided once per person |
| `render.py` | pass 2 — the annotated video |
| `overlay.py` | the readout strip and the box tags |
| `summary.py` | the result record and its quality signals |
| `pipeline.py` | the six-step sequence, and nothing else |
| `report.py` | the console read-out |
| `input/`, `output/` | the two pre-cut clips, and results |

Four of those six steps are about *identity* rather than pixels, which is the
shape of the problem: occupancy falls out of detection alone, and everything
else depends on one person keeping one ID.

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

The two clips in `input/` are **committed**, and this is the only project of the
six whose source is. The others fetch on first run — five by Pexels id, case 6
from HuggingFace — so keeping their inputs out of git costs nothing.

This one cannot. The source is the [CAFE dataset](https://dk-kim.github.io/CAFE/),
distributed as a single ~150 GB Google Drive archive with no API, which no
`main.py` can reasonably pull. So the two 30-second cuts live in the repository
instead, 47 MB, and `python main.py` works on a clean clone.

Each is 150 consecutive frames of a 29.97 fps recording, every 6th frame kept —
4.995 fps, 30.0 s. That frame rate is not incidental: at ~5 fps a walking person
crosses far more pixels between frames than a tracker's motion model expects,
which is the whole reason [`identity.py`](identity.py) exists.

> CAFE is credited to its authors at the link above. If you redistribute this
> repository, check the dataset's own licence terms rather than relying on this
> note — the project page states CC BY-SA 4.0 for the site, and is less explicit
> about the data itself.
