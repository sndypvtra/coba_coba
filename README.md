# Conveyor Vision — Zero-Shot Counting + Fill-Level Measurement

Two pipelines share this repo:

- **Conveyor counting** (`src/conveyor_count.py`) — counts objects crossing a
  line, from text prompts only. Three clips, documented below.
- **LiquidLevel-Vision** (`src/liquid_level.py`) — segments product inside a
  bottle on a filling line and estimates how much went in. See the section at
  the end.

---

## Conveyor Counting — Zero-Shot Detection + Tracking + Supervision

Counting and classifying objects on conveyor belts **without training a single
class**. Objects are found from plain-English text prompts, given stable IDs by
a multi-object tracker, and counted as they cross a line drawn with
[supervision](https://github.com/roboflow/supervision).

Three Pexels clips are processed end to end: two fruit lines (oranges,
tomatoes) and one parcel belt.

## Stack

| Piece | Choice | Why |
|---|---|---|
| Detector | **YOLOE-11L-seg** (`ultralytics` 8.4.106) | Open-vocabulary. Prompts are embedded with `get_text_pe()` and installed with `set_classes()` — no training, no fixed class list. Returns masks as well as boxes. |
| Tracker | **TrackTrack** (CVPR 2025) + ReID + GMC | Newest tracker shipping in ultralytics. Multi-cue association (HMIoU + appearance + confidence + corner angle), iterative assignment, track-aware initialization. `--tracker botsort` is available as a baseline. |
| Drawing / counting | **supervision 0.29.1** | `LineZone` crossings, plus mask / round-box / label / trace annotators and `VideoSink`. |
| Video I/O + HUD | **OpenCV 5.0.0** | Decode, HUD panel, dashed ROI, encode. |

## Results

Produced by `python src/conveyor_count.py` (CPU-only, 4 cores). Full numbers in
[`output/summary.json`](output/summary.json).

| Output clip | Scene | Prompts | Frames |
|---|---|---|---|
| `01_oranges_production_line__counted.mp4` | Citrus sorting line | `orange`, `round orange fruit` | 286 |
| `02_tomatoes_conveyor__counted.mp4` | Tomato grading line | `tomato` | 212 |
| `03_packages_conveyor__counted.mp4` | Parcel unloading belt | `cardboard box`, `parcel`, `plastic bag`, `sports bag` | 511 |

Counts are in [`output/summary.json`](output/summary.json). "Counted" is line
crossings by locked tracks; "unique IDs" is every object the tracker ever held.
They differ a lot on purpose — clip 1's belt moves ~3 px/frame, so in 9.5 s most
detected oranges never reach the line. Crossings measure throughput past a
point, which is what a conveyor counter is for; unique IDs would measure
"how much fruit appeared on screen".

Sources (Pexels, free for commercial use):
[oranges](https://www.pexels.com/video/fruit-on-production-line-10576687/) ·
[tomatoes](https://www.pexels.com/video/tomatoes-on-a-moving-conveyor-belt-8675102/) ·
[parcels](https://www.pexels.com/video/unloading-packages-on-a-conveyor-belt-5370836/)

## Run it

```bash
pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
./scripts/fetch_assets.sh          # weights + the three source clips

python src/conveyor_count.py                       # all three clips
python src/conveyor_count.py --only 02_tomatoes_conveyor.mp4
python src/conveyor_count.py --max-frames 45       # quick smoke test
python src/conveyor_count.py --tracker botsort     # swap the tracker
```

`src/probe_prompts.py` sweeps candidate prompt sets against sampled frames and
reports detections-per-frame and confidence spread — that is how the prompts and
per-clip `conf` values below were chosen rather than guessed.

## How each clip is configured

Every clip is one `ClipConfig` in `src/conveyor_count.py`. Belt direction is
measured from tracked-object displacement, not eyeballed. All three belts run
left, so all three lines sit near-vertical — but each is tilted to be square to
its own belt rather than to the frame.

| Clip | conf | min_track_age | Motion (px/frame) | Line tilt off vertical | ROI |
|---|---|---|---|---|---|
| oranges | 0.095 | 4 | (−3.2, +0.9) | 16.4° | full frame |
| tomatoes | 0.059 | 3 | (−14.8, −2.5) | 9.4° | y < 0.70 |
| parcels | 0.15 | 4 | (−1.5, +0.1) | 3.0° | x > 0.34 |

### Threshold tuning is clip-specific, and often not the answer

`src/tune_thresholds.py` measures **entry lag**: how far into the frame an object
travels before the pipeline locks onto it. 0.00 means caught at the edge, 0.30
means it was already 30% across. Lowering `conf` and opening the tracker gates
helps one clip a lot and the other two barely at all:

| Clip | entry lag before → after | acquired within 15% of edge | verdict |
|---|---|---|---|
| tomatoes | 0.326 → **0.203** | 21% → **50%** | real win |
| oranges | 0.303 → 0.276 | 22% → 15% | mostly fragments |
| parcels | 0.559 → 0.546 | 20% → 17% | no effect |

On the oranges, dropping `conf` 2.2× nearly doubled the track count while the
share acquired early *fell* — the extra detections were fragments of objects
already tracked, not earlier pickups, so the settings were left moderate.

The parcels number is a measurement artefact worth knowing about: that clip's
entry lag is dominated by the **stationary pallet stack**, which is present from
frame 1 and never "enters" the frame at all. Belt items are in fact acquired
close to the right edge. A latency metric over all tracks quietly measures the
furniture unless static objects are excluded.

### Prompting: the prompt list defines what exists

The most useful thing measured here, and the easiest way to get a silently wrong
count. **An object type nobody named is not missed — it is invisible.** Nothing
in the output flags it.

The parcel belt is the live example. It ran for several passes with
`cardboard box`, `parcel`, `plastic bag`, and a black holdall sat on the belt
undetected the whole time: against those three prompts its best overlap with any
predicted box was **IoU 0.01**. It is fabric, so `plastic bag` never matched it.
It was not a threshold, ROI or size problem — the bag sits inside the ROI, fills
~1.5% of frame, and stayed invisible even at `conf=0.04`.

What fixed it is not what you would guess. Measured against the bag's true box:

| Prompt | IoU | conf |
|---|---|---|
| `sports bag` | 0.81 | 0.56 |
| `duffel bag` | 0.81 | 0.41 |
| `holdall` | 0.81 | 0.46 |
| `black object` | 0.00 | — |
| `luggage` | 0.00 | — |

`black object` is an accurate description and finds nothing; `holdall` is an
obscure word and works. What matters is how close the phrase sits to a concrete
object category, not how correctly it describes the thing.

The same effect showed up on two manufacturing clips that have since been
removed from this repo: `beer can`/`soda can`/`tin can` returned **0.0**
det/frame on a canning line where `shiny metal cylinder` returned 19.0 at
conf 0.66, and `chocolate`/`praline`/`chocolate bar` returned **0.0** on a
confectionery belt where `brown cube` returned 6.0 at conf 0.65.

Two rules that follow:

1. Build the prompt list from an inventory of what can travel the belt, not from
   whatever happens to be visible in the frames you calibrate on.
2. If a prompt returns nothing, try neighbouring nouns and a shape/colour/material
   description before concluding the model cannot see the object.

The limit is transparency. A PET bottle-preform clip was dropped after 15
prompts — `plastic bottle preform`, `test tube`, `transparent cylinder`,
`clear plastic cylinder` and others all peaked at **conf 0.13**, too low to
track. Clear objects on cluttered backgrounds are where this runs out.

### Counting rules

Two rules decide what becomes a count:

**The line is built from the belt, not from the frame axes.** Each clip stores
its measured `motion`, and `build_counting_line()` lays the line perpendicular
to it, then orders the endpoints so travel along `motion` registers as **IN**.
A line parallel to the travel direction would hardly be crossed at all, which is
why orientation follows the belt. The total is `in_count` alone;
`count_reverse_crossings` in `summary.json` records backward crossings, which on
a one-way conveyor should be near zero — a few mean box jitter or an ID switch
briefly threw a centroid back over the line, and they are excluded from the
total rather than netted against it.

**An object must be locked before it can count.** `min_track_age = 6`: the
tracker has to hold the same ID for six consecutive frames before that object is
eligible. Locked tracks are drawn with `[L]`. A box that flickers into existence
on top of the line cannot register a crossing — it has to be acquired early,
held, and only then counted as it passes.

The ROI is drawn on the output as a dashed box, so what was and was not counted
is visible rather than implied.

## Notes from getting this working

Four things that were not obvious and are worth keeping:

1. **TrackTrack's defaults reject zero-shot detections.** Stock thresholds are
   `track_high_thresh: 0.6` / `new_track_thresh: 0.7`, but open-vocabulary YOLOE
   scores on this footage run ~0.10–0.65. With defaults almost no track is ever
   created. `src/trackers/tracktrack_zeroshot.yaml` moves the gates down to
   0.22 / 0.28 and documents each change against its stock value.
2. **ReID `model: auto` crashes on YOLOE `*-seg` checkpoints.** The native path
   (`get_obj_feats`) permutes a 4-D feature map, but the segmentation head
   returns a 3-D one → `RuntimeError: permute(sparse_coo)`. Fixed by pointing
   ReID at an explicit backbone (`yolo11n-cls.pt`), which keeps appearance
   re-identification instead of silently dropping it.
3. **Prompt aliases double-count without class-agnostic NMS.** `orange` and
   `round orange fruit` fire on the same fruit with different class ids, so
   class-wise NMS keeps both. `agnostic_nms=True` collapses them, and all
   aliases are then relabelled to one counting class.
4. **Input resolution matters far more than model size here.** At `imgsz=640`
   the fruit is too small; going to `imgsz=1280` roughly doubled mean confidence
   (e.g. oranges 0.17 → 0.33) for ~4× the compute. Measured, not assumed.

## Layout

```
src/conveyor_count.py                  main pipeline
src/probe_prompts.py                   prompt/confidence calibration
src/trackers/tracktrack_zeroshot.yaml  TrackTrack retuned for zero-shot scores
src/trackers/botsort_zeroshot.yaml     BoT-SORT baseline
scripts/fetch_assets.sh                weights + source clips
output/                                rendered .mp4 results + summary.json
```

## Caveats

- Counts are line-crossing counts on short clips (7–17 s); they are not a
  validated ground truth, and no clip here ships with one.
- Encoding is `mp4v` — this sandbox has no ffmpeg/H.264 encoder, so the files
  are MPEG-4 Part 2. Plays in VLC/QuickTime; re-encode if you need H.264.
- CPU-only: ~1.3 s/frame at `imgsz=1280`. On a GPU this is real-time territory.


---

# LiquidLevel-Vision

Measures how much liquid a filling machine puts into a bottle, from video alone.

    python src/liquid_level.py --capacity-ml 500
    python src/liquid_level.py --detect        # overlay live YOLOE segmentation

Source: [Pexels 8720278](https://www.pexels.com/video/empty-bottles-in-a-filling-machine-8720278/),
inline filler, clear bottles, amber product. Output:
`output/07_bottle_filling__liquid.mp4`, series in `output/liquid_level_summary.json`.

## How it measures

**Segmentation is by saturation, not hue.** Calibrated from pixel statistics
rather than guessed: product sits at S~255, while the shiny conveyor (S~36-55)
and the empty glass (S~8-60) overlap the product's *hue* almost exactly. Hue
alone cannot separate them; `S>=150` can.

**The surface is found by width, not by the topmost lit pixel.** This was a real
bug, caught on review. The falling jet is connected to the pool, so "topmost lit
row" tracked the *nozzle stream*: on frame 229 it put the level line at y=597,
where the mask is 9 px wide — 3% of the bore — when the actual surface was at
y=660 at 146 px. Fill read 88.6% instead of the true level. Now the surface is
the highest row spanning >=45% of the bore, found by climbing from the base, and
the jet is drawn separately as excluded.

Two follow-on faults surfaced while fixing it:

- *Bistable readings.* A gap tolerance wide enough to bridge occlusions also
  bridged the turbulent splash sheet sitting 30-40 rows above the settled pool,
  so the fill flipped between ~30% and ~50% on alternate frames. The tolerance
  is now 10 rows. The static rod crossing the bottle needs no bridging — it
  occludes every frame, so the learned bore already accounts for it.
- *An inverted bore profile.* The unwetted neck was extrapolated to a hand-read
  mouth diameter of 185 px, but that came from the bottle's **outer rim** while
  the mask measures the inner bore, whose observed maximum is 159 px. The neck
  came out wider than the body, and 60% of the "capacity" was extrapolation
  rather than measurement. Nothing is extrapolated now: 100% is the fullest
  level actually reached in the clip, which is also the industrially meaningful
  datum since a filler targets a level at the shoulder, not the brim.
- *Splash written into the bore, which then invited the level to climb into it.*
  Reported as "at the end it jumps to the top and joins the pool at the base".
  Three separate faults fed it, each found by printing the learned bore rather
  than trusting it: the bore was learned from **any** wide row, so a turbulent
  sheet under the nozzle was recorded as bore — at the datum row the "bore" was
  **41 px against a real 282 px**, a tall thin column that both inflated the
  reference and gave the surface a low bar to clear. The bore is now learned
  only from the run of rows that reaches the base, so a sheet separated from the
  pool cannot enter it. Second, `pool_surface` compared against
  `max(bore, 1.0)`, so above the known bore it compared against **1 px** and
  passed on anything; rows with no measured bore are now rejected outright.
  Third, a wave crest can still connect to the pool through a thin neck, so any
  learned bore under 30% of the widest is discarded as implausible — no bottle
  bore narrows that far inside its fillable body.

**Volume is integrated over the bore, not the mask.** Below the surface the
bottle is full, so the true cross-section is the bore; a narrower mask is glare
or occlusion, not less liquid. The reading depends only on locating the surface.

**The surface trajectory is fitted, not read frame by frame.** Reported as "not
smooth, and the last frame is not at 500 mL yet". Both were real.

A per-frame threshold cannot place this surface stably. Seen at an angle the
liquid surface projects as an **ellipse ~50 rows tall**, and inside that band the
colour mask runs 95-133 px against a 282 px bore — ratios of 0.34-0.48, straddling
whatever cutoff you choose. On f215 those rows failed and on f216 they passed, so
the surface moved 56 rows and the reading jumped 27 points in 1/25 s. Sweeping
the cutoff (0.20-0.45) and the reference (learned bore vs observed pool width) did
not fix it: every one of the twelve variants still jumped 50-70 rows somewhere.

So the trajectory comes from physics rather than thresholds: a 7-frame median
kills splash spikes, then an **isotonic (non-increasing) fit** enforces that a
filling level only rises, then an 11-frame smooth and a second isotonic pass make
the rate physically plausible.

| | before | after |
|---|---|---|
| worst backward dip | 27.6% | **0.0%** |
| worst single-frame jump | 27.2% | **4.5%** |

This assumes **one monotonic fill of one bottle**. It will flatten a genuine drop
in level — a drained or swapped bottle — so it is the wrong tool for footage that
is not a single fill cycle.

**Neighbouring bottles were setting the level.** Reported as "the level is not at
the surface on the last frame, it is affected by the bottle next to it being
filled too". Correct, and there were two separate leaks:

- *Product seen through glass.* The front bottle's upper half is transparent and
  other filled bottles sit behind it, so their amber showed through and colour
  called it liquid **inside** this bottle. The extra glass layer desaturates it,
  which turns out to be cleanly separable: product in direct view sits at
  **S 251-255**, product seen through glass at **S 104-199**. The old cut of
  `S>=150` passed it, putting the surface at y=652 when the real meniscus was at
  y~690. The cut is now `S>=200`.
- *The neighbour in direct view.* Product in the bottle behind is exactly as
  saturated as product in this one, so no colour rule can separate them — only
  position can. The surface is now located in a column band `x=700-890`: inside
  the front bottle and right of where the neighbour's product reaches (x~690).

Datum row moved from y=651 to **y=699**, against a meniscus measured at y~690.
Together with the trajectory fit the series is smooth (worst frame-to-frame jump
4.8%, no backward dip) and ends exactly at 100%.

**The ROI is anchored, not detected per frame.** YOLOE does find the bottles
(`transparent bottle`, conf 0.78, masks included) but on clear plastic its boxes
wander 194-328 px and swap between neighbouring bottles — a fill series built on
them jumped 5% → 60% → 46% and was meaningless. Template matching showed the
bottle itself moves **7 px** across the whole fill cycle, so the ROI is measured
once and micro-aligned per frame. `--detect` overlays the live detector so you
can see it running and judge that call yourself.

**The denominator is fixed in a first pass.** Learning the bottle profile while
also reporting fractions against it makes the series non-monotonic — an early
version reported 72% fill on the frame where product first appeared, because the
capacity it was dividing by was only the sliver of bottle wetted so far.

## What the numbers mean

| Reported | Status |
|---|---|
| fill fraction by volume | **measured** |
| fill fraction by height | **measured** |
| millilitres | **assumed capacity x measured fraction** |

`--capacity-ml` is not observable from the video. The fill *fraction* is real;
millilitres are that fraction scaled by whatever capacity you supply. Pass the
real SKU capacity and the number means something; the 500 mL default is
illustrative. Disc integration also assumes a solid of revolution — true for
these round bottles, false for a flask or a rectangular jerrycan.

Residual limits worth knowing: the fill series still dips up to 5.3% frame to
frame while the surface is turbulent under the nozzle, and the ROI clips a
little of the bottle's base bulge, so the profile is slightly truncated. Both
affect the fraction only mildly because numerator and denominator are measured
the same way, but neither is zero.
