# 05 — Cafe: occupancy and per-person dwell time

Two rooms of the same cafe. How many people are here, and how long did each of
them stay.

```bash
python main.py              # scene 5, the default room
python main.py --scene 1    # the other room
python main.py --all        # both, one after another
```

| | scene 1 | scene 5 |
|---|:--:|:--:|
| **Distinct visitors** | 12 | 12 |
| Occupancy, mean / max | 10.32 / 12 | 9.04 / 10 |
| **Dwell, mean / max** | **24.64 s** / 30.03 s | **20.97 s** / 30.03 s |
| Staff service time | 14.21 s | 19.82 s |
| — of which observed | 38 frames | 93 frames |
| — of which held | **33 frames** | 6 frames |
| Server's share of the service zone | 100 % | 94 % |
| Duplicate boxes removed | 80 | 76 |
| Broken tracks re-linked | 0 | 4 |
| Tracks with gaps | **3 of 12** | 2 of 12 |

Both rooms are measured by the same twelve modules; only `config.py` differs,
and only in the zones. Every figure above comes from `output/*__dwell.json`.

### Scene 1 is the harder room, and its numbers say so

Read the two rows in bold before quoting scene 1's dwell time.

**Its service figure is nearly half interpolated.** The counter sits deep in the
room, backlit by the menu boards, with equipment on the counter top cutting the
server in half. She is detected in 38 frames and held across 33 more, so 14.21 s
of service is 8.0 s observed and 6.2 s inferred. Scene 5's server is detected in
93 of 99. The held frames are reported separately in the JSON precisely so this
cannot be passed off as observation.

**Its identity assignment is much weaker.** Worst continuity 0.152 means one
customer was seen in 15 % of the frames between their first and last sighting —
the tracker lost them repeatedly and re-linking joined none of it, because the
gaps exceed what `identity.py` will bridge on appearance alone. Three of twelve
tracks are fragmented against two of twelve in scene 5.

Occupancy is unaffected by any of this — it is a per-frame detection count, and
10.32 / 12 is as sound here as 9.04 / 10 is next door.

### What the server cost to get right

Scene 5's server stands at the till for the whole clip, and customers lean on
the counter in front of her. She is tracked for 19 frames, hidden for the next
51, and picked up again for the last 80. Two defects followed, and both are
fixed in [`identity.py`](identity.py):

**One person was put in two places.** The pairwise re-link rule refuses to join
tracks that coexist, but union-find joined them transitively anyway — two weak
matches (similarity 0.50 and 0.53) chained the server's track to three people
elsewhere in the room. The identity that came out was 15 % inside the service
polygon instead of her 68 %, so she was reported as a *customer* and the room
looked unattended for the first 70 frames. A union is now refused when any
member of one group shares a frame with any member of the other.

**A counter is not a room.** Her 10.4 s occlusion is far outside the 3 s gap
that suits a customer walking behind someone. A service polygon is a fixed
workplace, so two tracks that both sit predominantly inside one now get a longer
gap and a looser displacement. She is one identity again, 94 % inside the zone,
labelled from frame 1.

The similarity floor moved 0.45 → 0.65 at the same time, and the value is not a
taste: of the five candidate pairs in this clip, three score 0.82–0.98 and two
score 0.50–0.53. The empty band between them is 0.286 wide, five times the next
largest gap, and 0.65 sits in the middle of it.

What is *not* fixed: for the ~50 frames she is hidden, her occasional visible
detections are absorbed by the customer tracks around her, so she carries no
PELAYAN box there. Four alternative tracker settings were measured — heavier
ReID, a longer track buffer, a looser match threshold — and each traded that for
a worse defect, either splitting her in two again or losing a visitor.

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
| `baseline.py` | each room's last verified figures, checked on every run |
| `report.py` | the console read-out, including the regression line |
| `input/`, `output/` | the two pre-cut clips, and results |

Four of those six steps are about *identity* rather than pixels, which is the
shape of the problem: occupancy falls out of detection alone, and everything
else depends on one person keeping one ID.

## The two numbers are not equally good

**Occupancy is a detection result.** Count the people visible in a frame; no
identity required. It is the number to trust.

**Dwell time is a tracking result.** It needs one person to keep one ID while
someone walks in front of them. `tracks_with_gaps` reports how often that failed
— 2 of 12 in scene 5, 3 of 12 in scene 1 — and the visitor total inherits the
same risk: a broken identity becomes two visitors who each stayed half as long.
`baseline.py` pins both, so a change that moves them says so on the next run.

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
