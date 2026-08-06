# Case 6 — Multi-camera 3D localisation and the eagle view

Four fixed cameras look at one warehouse floor. The case answers three questions
that no single camera can:

- **Where is each person, in metres?** Not "in the top-left of camera 2".
- **How many people are there?** One number for the building, not four numbers
  that cannot be added up.
- **What did they do on the floor?** Distance walked, speed, which areas, how
  close they came to a moving robot.

The dataset ships the true 3D position of every object. The pipeline never reads
it; every figure below is the pipeline's own answer, and the error against the
truth is measured rather than asserted.

---

## Source

[NVIDIA PhysicalAI-SmartSpaces](https://huggingface.co/datasets/nvidia/PhysicalAI-SmartSpaces),
CC BY 4.0, ungated. `MTMC_Tracking_2025/train/Warehouse_014` — 12 fixed cameras
over one 19.3 × 19.3 m floor, 1920×1080 at 30 fps, 9,000 frames (5 minutes).
Synthetic, rendered in Omniverse; the calibration and the ground truth are exact
because the scene was rendered rather than surveyed.

### Which four cameras, and why

The dataset's own banner (`demo.gif` at the repository root) is a 12-tile montage
of this scene arranged around its top-down view. The four cameras used here are
the tiles requested for this case:

| Banner tile | Camera | Panel |
|---|---|---|
| left block, top-left | `Camera_02` | top-left |
| left block, bottom-left | `Camera` | bottom-left |
| right block, top-left | `Camera_06` | top-right |
| right block, bottom-right | `Camera_01` | bottom-right |

The banner carries no labels, so the mapping was measured rather than guessed.
The centre panel was matched against every scene's `map.png` — `Warehouse_014`
rotated 180° scores **0.945**, the next-best scene **0.60**. Each of the twelve
tiles was then matched against the first frame of all twelve videos: every tile
resolved at **0.86–0.96** against a next-best of **at most 0.44**.

### The clip

30 seconds from source frame 1950 (t = 65 s), subsampled 30 → 10 fps: 300 frames
per camera, 1,200 inferences. That window was chosen by measurement, not by eye —
it is the busiest 30 s of the recording by person travel distance (31.2 m) with
7,678 person-boxes visible across these four cameras.

---

## Method

### 1. Detection — still zero-shot

The prompt list is the class list. This warehouse contains people, two humanoid
robots and three wheeled transporters, and the prompt list decides which of those
the system can even represent.

Twelve prompt lists were measured against the ground truth over 60 camera-frames
(15 frames × 4 cameras), scoring a hit at IoU ≥ 0.3:

| Prompt list | Person found | …labelled person | AgilityDigit found | …separated | GR1T2 found | …separated | Transporter found | Boxes on nothing |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `person` | 128/128 | 128 | 14/45 | 0 | 42/46 | 0 | 0/143 | 26 |
| `person`, `humanoid robot` | 128/128 | 127 | 38/45 | **31** | 43/46 | 1 | 0/143 | **26** |
| `person`, `robot` | 128/128 | 128 | 37/45 | 29 | 44/46 | 2 | 0/143 | 26 |
| `person`, `humanoid robot`, `robot` | 128/128 | 127 | 40/45 | 33 | 44/46 | 2 | 0/143 | 26 |
| `person`, `android` | 128/128 | 128 | 14/45 | 0 | 42/46 | 0 | 0/143 | 26 |
| `person`, `humanoid` | 128/128 | 128 | 16/45 | 4 | 42/46 | 0 | 0/143 | 26 |
| `…`, `white humanoid robot` | 128/128 | 127 | 38/45 | 31 | 43/46 | 1 | 0/143 | 26 |
| `…`, `robot mannequin` | 128/128 | 124 | 39/45 | 33 | 45/46 | 5 | 0/143 | 35 |
| `…`, `transport robot` | 128/128 | 127 | 44/45 | 22 | 45/46 | 0 | 57/143 | 58 |
| `…`, `mobile robot` | 128/128 | 127 | 44/45 | 1 | 45/46 | 0 | 55/143 | 90 |
| `…`, `yellow robot cart` | 128/128 | 127 | 43/45 | 20 | 44/46 | 1 | **128/143** | **660** |
| `…`, `forklift` | 128/128 | 127 | 38/45 | 31 | 43/46 | 1 | 6/143 | 28 |

Three things fall out of that table, and only the first was expected.

**People are found perfectly and every list agrees.** 128 of 128, at
`conf = 0.15`, in every configuration. Person detection is not where the
difficulty is.

**An unnamed object is not invisible — it is absorbed.** This is the sharper
version of the lesson case 3 taught. There, a black holdall nobody named simply
went undetected. Here, the humanoid robots are detected *91 % of the time* under
a `person`-only list and every one of those detections is labelled **person**.
The failure mode is not a missing box; it is a **correct-looking box in the wrong
class**, which walks straight into the headcount with nothing flagging it.

**Naming has a limit, and the limit is shape.** `humanoid robot` separates the
AgilityDigit — a headless, bird-legged machine — in 31 of 38 detections. It
separates the Fourier GR1T2 in **1 of 43**. Nothing in the twelve lists does
better than 5 of 45, and the ones that try (`robot mannequin`) cost four real
people and nine extra spurious boxes. A human-shaped, human-sized robot is not
separable by a phrase.

Nor by geometry, which was the obvious next idea. This pipeline *measures*
height, so a stature gate looked promising until the true heights were checked:

| Class | True height |
|---|---|
| Person | 1.77 – 2.05 m (three individuals: 1.84, 2.03, 1.82) |
| AgilityDigit | 1.67 – 1.88 m |
| Fourier GR1T2 | 1.62 – 1.68 m |
| Transporter | 0.20 – 0.23 m |

The gap between the shortest person and the tallest GR1T2 is **0.09 m**, against
a single-view height error of ±0.27 m. AgilityDigit overlaps people outright. So
the transporters are trivially separable by height and the humanoids are not.

**The list used is `person`, `humanoid robot`** — the simplest list that achieves
the separation available, at no cost in false positives (26 boxes on nothing,
identical to the `person`-only baseline). The consequence is stated rather than
hidden: **the Fourier GR1T2 humanoid is counted as a person.**

### 2. Lifting a rectangle to a place in the building

A monocular detector cannot see depth. It does not have to: a person standing on
a **known floor** has one unknown left, and the calibration supplies it.

- **Position.** The bottom-centre of the box is where the person meets the floor.
  Back-projecting it through the ground-plane homography `H⁻¹` gives (x, y) in
  metres.
- **Height.** A person is a vertical segment: feet at (x, y, 0), head at
  (x, y, h). Projecting that through the camera matrix gives

  ```
  v(h) = (a₁ + h·b₁) / (a₂ + h·b₂),   a = P[:, :2]·(x, y) + P[:, 3],  b = P[:, 2]
  ```

  which is linear in `h` once cross-multiplied, so the height that puts the head
  at the box's top edge follows in closed form. No search, no assumed stature —
  and a height outside human range is then a *signal* that the box was not a
  whole standing person.
- **Footprint.** A constant (0.60 × 0.46 m, the dataset's own mean person
  footprint). A silhouette does not carry it, and the output says so.
- **Precision.** The world size of one image pixel at that floor point. Near the
  camera that is a couple of centimetres; near the horizon it is most of a metre.
  This is what makes a distant, grazing-angle observation count for less when
  cameras disagree.

Clipping is handled by *which* edge it happens at, and getting that wrong was a
visible defect in the first version of this case: boxes touching any edge were
dropped, so a person walking at the side of a view carried no box at all while
the panel still counted them. Only the **bottom** edge destroys the measurement —
there the feet are off-frame and the lowest pixel is not the floor contact, so
the observation goes. A **side** clip keeps the feet and only pulls the box's
horizontal centre inwards, so it is kept at a third of the weight. A **top** clip
costs only the height.

### 3. Fusion — one identity per person

Each camera runs its own tracker, so four cameras give four track IDs for one
person. Adding them up counts a warehouse of three as a warehouse of twelve.

Grouping happens on the floor, under two constraints:

- **Never two observations from one camera.** The per-camera tracker has already
  ruled they are different objects.
- **Never two different classes.** Over this window the three people never come
  within **8.07 m** of one another — position alone would separate them
  trivially. But a person passes a humanoid robot at **0.69 m**, *inside* the
  0.90 m fusion radius. Without the class constraint that pass merges a person
  into a robot and the headcount drops.

Across frames, identity is carried by the single-camera track keys first and by
distance second. A group containing `Camera_01#7` and a group that contained
`Camera_01#7` a moment ago are the same object almost regardless of where they
are, because the single-camera tracker is the one component with appearance to
work with.

### 4. The eagle view

The dataset ships a top-down render of the building and the two numbers that tie
it to world coordinates — a scale in pixels per metre and a translation in
metres. So the eagle view is the actual floor, and a marker on it is where the
person is standing. Camera coverage outlines are computed, not drawn by hand: a
grid of image points is back-projected onto the floor and hulled.

---

## Reading the output video

- **Same colour = same person.** A box in the top-left tile and a box in the
  bottom-right tile share a colour only if the pipeline decided they are one
  identity.
- **Solid box with a filled floor face** — this camera detected the object.
- **Faint outline** — the fused estimate rendered into a view that *missed* it.
  Kept deliberately: a box standing correctly on a person a camera did not detect
  is the clearest evidence the fusion is working, and labelling it differently
  means the picture never implies a detection that did not happen.
- **Rings on the plan** — one extra ring per additional camera that agreed the
  object is there.
- **Warm blobs on the plan** — cumulative traffic density, the heat map.
- **Green tint on the floor** — how many of the four cameras cover that spot.
  Overlap is what makes fusion possible, so where it is thin is worth seeing.

---

## The operational readout

The panel answers the three questions a shift supervisor asks, in that order.
Detector and tracker diagnostics are not on it — they live in the JSON summary,
because a number nobody can act on is clutter on a wall display.

### 1. Is the labour being spent well?

| | | Why it is the number |
|---|---:|---|
| Headcount, mean / peak | **3.87 / 4** | staffing actually present, not rostered |
| Time spent walking | **44.7 %** of person-time | travel is the classic non-value-adding activity; halving it is what a slotting review is for |
| Travel rate | **1,263 m** per person-hour | **≈ 10.1 km per person per 8 h shift** at this pace |
| Time by area | racking **52.1 %** · staging **37.7 %** · walkway **10.2 %** | where the shift actually went |

### 2. Is anyone where they should not be?

| | | |
|---|---:|---|
| Pallet-lane entries | **8** | crossings of a marked drop lane, not frames inside one |
| Time inside marked lanes | **13.3 s** (11.5 % of person-time) | lane 1 took 12.2 s of it, lane 2 none |
| Near misses under 1.5 m | **18 events**, 6.0 s total | a person inside 1.5 m of a moving machine |
| Closest approach | **0.40 m** | the worst single moment in the clip |

Entries and events rather than seconds is the whole point of this block. "13
seconds in a pallet lane" reads as nothing; "eight separate crossings in thirty
seconds, one of them within 40 cm of a moving machine" is a toolbox-talk.

### 3. Where is the floor being used?

The heat map on the plan is the answer, and it is cumulative person-seconds per
square metre rather than a count of visits. Two hot spots form inside the
staging block within 30 seconds — that is where a layout change would pay.

**Extrapolations are labelled as extrapolations.** A 30-second sample cannot
observe a shift. The per-hour and per-shift figures are stated as *rates implied
at this pace*, carry that caveat in the JSON, and are not presented as
measurements.

---

## What the analytics are, and what they rest on

| Figure | Rests on |
|---|---|
| Headcount | detection **and** cross-camera identity |
| Position, height | geometry alone — the calibration and "the box bottom is the feet" |
| Time by area, lane entries | position, plus zone outlines read off the floor paint |
| Distance walked, walking share | position **and** identity holding over time, **and** smoothing |
| Near misses | position and class |

Two of these deserve their measurement rule spelled out, because the answer
moves with it.

**Walking, live, is displacement over a 0.6 s window — not the sum of the steps
inside it.** Summing steps accumulates position noise and reports a stationary
person as walking; the first version of this panel did exactly that and drew a
"walking" line identical to the headcount line, which is how the bug was found.
Straight-line displacement of someone standing still stays near zero however
noisy each sample is.

**A lane entry is a boundary crossing, not a frame inside the lane.** One person
working in a lane for ten seconds is one event; ten people stepping through it
is ten. Only the second is a habit worth addressing, and only the event count
tells them apart.

Speed and distance need the smoothing, and the reason is arithmetic rather than
taste. A floor position carries roughly 0.3 m of error; differencing samples
0.1 s apart turns that into 3 m/s of pure noise — faster than walking — and
summing those differences inflates path length without bound. Both are computed
on a track smoothed over 0.5 s, and the window is reported with the result. Top
speed is a 95th percentile, not a maximum, so a single bad frame cannot become
the headline.

Zone outlines are measured, not sketched. The three pallet lanes are the blue
rectangles painted inside the staging block, isolated on `map.png` by taking
pixels where blue leads red by more than 25 levels and reading off each
contour's bounding box; the staging block and the racking bay come from the same
image with a one-metre grid drawn over it. They are stored in world metres, so
they survive a change of camera.

---

## Results

30 seconds, four cameras, 1,200 inferences on CPU at about 3.5 s per fused frame.

### Against the dataset's own 3D ground truth

| | |
|---|---|
| **Localisation error, median** | **0.311 m** |
| Localisation error, mean / p95 | 0.285 m / 0.449 m |
| Recall | **0.9833** (885 of 900 person-boxes matched inside a 1 m gate) |
| Precision | 0.7424 |
| Global IDs per real person | **1.0** — no identity switches in 30 s |
| Headcount error per frame | **+0.95 mean** |

The precision figure and the headcount error are the same fact seen twice: the
pipeline reports four people where there are three, every frame, because the
Fourier GR1T2 humanoid is one of them. Remove that known object and the count is
exact. Nothing else is invented — the recall says almost every real person is
found, and the identity figure says each of them was found *as one person* for
the whole clip.

For scale, 0.329 m is *better* than the same geometry applied to the dataset's
own 2D boxes: back-projecting the ground-truth box bottoms one camera at a time
gives a median of 0.311 m and a p95 of 0.661 m. Fusing four views cuts the tail
by a third. The remaining error is not detector noise — it is the gap between
"the lowest pixel of the box" and "the point between the feet", which no amount
of averaging removes.

### What the four cameras bought

| | |
|---|---|
| Views contributing per person, mean | **2.71** of 4 |
| Cross-camera agreement | **0.267 m** median spread within a fused group |
| Observations merged away | 2,240 |
| Identities dropped as single-view | 5 |

Without fusion these four cameras would report their own headcounts and there
would be no way to add them up. The agreement figure is the honest measure of
how well the geometry holds: two cameras looking at one person from different
sides put them 0.26 m apart.

### The floor

| | |
|---|---|
| On the floor, mean / max | 3.87 / 4 |
| Measured height, median | **1.86 m** |
| Floor walked | **42.0 m** in 30 s across four people |
| Walking speed, mean | 0.35 m/s |
| Person-seconds in marked pallet lanes | lane 1 **12.2** · lane 3 **1.1** · lane 2 0 |

### Height, measured per identity

The stature figures are worth a table of their own, because they are the part of
the 3D estimate a reader can check against their own intuition:

| Identity | Measured | True | Error |
|---|---:|---:|---:|
| P4 | 1.866 m | 1.84 m | +0.03 |
| P7 | 1.863 m | 1.82 m | +0.04 |
| P6 | 1.961 m | 2.03 m | -0.07 |
| P2 *(the GR1T2 humanoid)* | 1.728 m | 1.65 m | +0.08 |

A median over a whole track, across up to four views, lands within **0.03–0.10 m**
of the truth — against ±0.27 m for a single view in a single frame. That is the
clearest demonstration in the case of what fusion plus time actually buys.

It also means the humanoid *did* come out as the shortest identity, by 0.135 m.
That is not a rule and it is not used as one: the true gap is 0.09 m and this
estimator's own bias reaches 0.10 m, so a stature gate that works on this clip
would be reading its own noise. It is reported because it is interesting, not
because it is a method.

---

## Limits

**The humanoid robot is in the headcount.** Measured, unfixable by naming, and
stated on the console at the end of every run. See the prompt table above.

**The footprint is a constant.** Height is measured per detection; width and
length are not observable from a silhouette at this distance and are set to the
dataset's own mean person footprint. The eagle-view rectangles are therefore
correctly *placed* and correctly *oriented* but not individually sized.

**Orientation comes from motion, not from the body.** Yaw is the direction of
travel of the smoothed world track, held through moments of standing still. A
person standing still and turning on the spot will not turn on the plan.

**The floor plane is assumed flat and at Z = 0.** True for this warehouse. On a
site with a loading ramp or a mezzanine, the single homography per camera stops
being enough and each level needs its own.

**"The box bottom is the feet" is the load-bearing assumption.** Where it fails,
so does the position — which is why boxes clipped by the frame edge are dropped
rather than lifted. Occlusion by a pallet that hides the feet but not the head
is not detectable this way and will place the person too far from the camera.

**Synthetic footage flatters the calibration.** This scene was rendered, so the
camera matrices are exact and there is no lens distortion left over. On a real
install the same pipeline carries the calibration's own error on top of
everything measured here.
