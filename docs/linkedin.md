# Project title and LinkedIn copy

## Title

**Fixed-Camera Metrics** — repo slug `fixed-camera-metrics`

The five cases share one idea: an ordinary fixed camera, and a number an operator
can act on. Throughput on a belt, millilitres in a bottle, people in a room and
how long they stayed. `factory-vision-poc` no longer fits now that case 5 is a
cafe rather than a production line.

Alternatives, if a different emphasis is wanted:

| Slug | Emphasis |
|---|---|
| `camera-to-metric` | the transformation itself |
| `zero-shot-vision-ops` | that four of five cases need no training data |
| `operational-vision-poc` | the business framing |

---

## LinkedIn post

**Five computer-vision proofs of concept, all on CPU, four of them with no
training data at all.**

I built these to answer one question: how much operational insight can you get
out of a camera that is already installed?

**Conveyor counting (3 cases).** Objects are named in plain English and counted
as they cross a line — no labels, no fine-tuning, no fixed class list. YOLOE
open-vocabulary detection, TrackTrack (CVPR 2025), supervision for the counting
geometry. Results: 5 oranges, 16 tomatoes, 7 mixed parcels.

**Fill-volume inspection.** Product inside a bottle is segmented and the volume
below the liquid surface integrated over the bottle's bore as a stack of discs.
1,001 mL of a 1,500 mL nominal fill — 66.7%, monotonic, worst frame-to-frame
step 3.1%.

**Cafe occupancy and dwell time.** People detected zero-shot, tracked, and timed.
Two cafes: 12 visitors each, mean dwell 21.2 s and 24.6 s over 30-second clips.
Staff are measured separately as service time rather than counted as visits.

**Three findings I did not expect:**

*The prompt list defines what exists.* A black holdall sat on a parcel belt
undetected for several runs. Against `cardboard box`, `parcel` and `plastic bag`
its best overlap was IoU 0.01 — and it stayed invisible even at conf 0.04. What
fixed it was `sports bag` (IoU 0.81). `black object` — an accurate description —
finds nothing. What matters is how close the phrase sits to a concrete object
category, not how correctly it describes the thing.

*Duplicate boxes are separable by containment, not by IoU.* Two boxes on one
seated customer span IoU 0.076–0.485, while genuinely adjacent customers span
0.000–0.425 — the ranges overlap almost entirely, so no NMS threshold can split
them. Intersection over the *smaller* box separates them cleanly.

*A role belongs to a person, not to a frame.* Deciding staff-vs-customer from
per-frame geometry made a server flip identity the moment she leaned over the
counter. Deciding it once per track, from the share of frames spent inside the
service zone, separates 100% from 46%.

**And the limit, stated rather than hidden.** The fill-volume case is calibrated
to one camera position. Re-rendering the same scene with a 120 px shift gives
143 mL against a correct 1,001 mL — an 86% error, reported through the same
confident panel with no error flag. Translation breaks it; a 20% zoom costs only
7%. That silence is the real hazard in vision demos, so the repo measures it
instead of asserting robustness.

Stack: YOLOE-11L-seg (ultralytics 8.4.106) · TrackTrack · supervision 0.29.1 ·
OpenCV 5 · CPU only.

Code, method write-ups and every number above: <repo link>

---

## Short version (if the long post is too much)

Five computer-vision PoCs on CPU — conveyor counting, bottle fill-volume
inspection, and cafe occupancy with dwell time. Four of the five use zero-shot
detection: the model is given words, never labels, never training data.

The most useful thing I learned is uncomfortable. An object nobody names is not
missed — it is invisible, and nothing in the output flags it. A black holdall on
a parcel belt scored IoU 0.01 against `cardboard box`, `parcel` and `plastic
bag`, and stayed invisible even at conf 0.04. The prompt that found it was
`sports bag`, at IoU 0.81. Meanwhile `black object` — a perfectly accurate
description — finds nothing at all.

So the prompt list is not a detail. It is the class list, and building it from an
inventory of what can appear beats building it from what you happen to see in the
frames you calibrate on.

Code and the full write-up: <repo link>
