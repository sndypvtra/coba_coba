# Conveyor Counting — method and limits

Zero-shot object counting on conveyor footage. Overview and results in the
[repository README](../README.md).

---

Counting and classifying objects on conveyor belts **without training a single
class**. Objects are found from plain-English text prompts, given stable IDs by
a multi-object tracker, and counted as they cross a line drawn with
[supervision](https://github.com/roboflow/supervision).

Three Pexels clips are processed end to end: two fruit lines (oranges,
tomatoes) and one parcel belt.

## How each clip is configured

Every clip is one `ClipConfig` in `../factory_vision/counting/clips.py`. Belt direction is
measured from tracked-object displacement, not eyeballed. All three belts run
left, so all three lines sit near-vertical — but each is tilted to be square to
its own belt rather than to the frame.

| Clip | conf | min_track_age | Motion (px/frame) | Line tilt off vertical | Gate on background |
|---|---|---|---|---|---|
| oranges | 0.095 | 4 | (−3.2, +0.9) | 16.4° | full frame |
| tomatoes | 0.059 | 3 | (−14.8, −2.5) | 9.4° | y < 0.70 |
| parcels | 0.08 | 4 | (−4.7, +0.3) | 0.0° (plumb) | depth 1.45–2.95 m |

The parcel row is the one that changed, in all four columns, and the reasons are
in [Dimensioning the parcel belt](#dimensioning-the-parcel-belt) below.

### Threshold tuning is clip-specific, and often not the answer

`../factory_vision/tools/tune_thresholds.py` measures **entry lag**: how far into the frame an object
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
why orientation follows the belt. Where the camera has no roll, `line_plumb`
snaps the result upright — see
[the counting line](#the-counting-line-plumb-not-normal-to-motion) for why the
motion normal is not the same as the cut plane. The total is `in_count` alone;
`count_reverse_crossings` in `summary.json` records backward crossings, which on
a one-way conveyor should be near zero — a few mean box jitter or an ID switch
briefly threw a centroid back over the line, and they are excluded from the
total rather than netted against it.

**An object must be locked before it can count.** `min_track_age` is 3–4 frames
depending on the clip: the tracker has to hold the same ID for that many
consecutive frames before the object is eligible. Locked tracks are drawn with
`[L]`. A box that flickers into existence on top of the line cannot register a
crossing — it has to be acquired early, held, and only then counted as it passes.

Where a clip uses an image ROI it is drawn on the output as a dashed box, so
what was and was not counted is visible rather than implied. The parcel belt no
longer needs one; its background is excluded in depth instead.

## Dimensioning the parcel belt

Counting a parcel is the easy half. The half a depot bills on is *how big it
was* — and a fixed camera cannot answer that from pixels, because the same
carton covers four times the area at half the distance. Case 3 closes the gap
with [Depth Anything 3](https://depth-anything-3.github.io) (ByteDance, Nov
2025) and reports distance, dimensions and volume per parcel.

### Two models, because DA3 splits the problem

| Model | Gives | Missing |
|---|---|---|
| `DA3METRIC-LARGE` | *canonical* metric depth — metres ÷ focal length | the focal length |
| `DA3-LARGE` | camera intrinsics from its camera decoder | metric scale |

Multiplying one by the other is DA3's own recipe, taken from the nested model's
forward pass (`DepthAnything3Net._apply_metric_scaling`):

```
metres = canonical × (fx + fy) / 2 / 300
```

Two consequences, pulling opposite ways, and they decide the whole design:

- **Distance inherits the focal's error.** The predicted focal is the weak link
  — it moves 3% between processing resolutions — and it multiplies depth
  directly.
- **Size does not.** A length off the image is `pixels × Z / f`, and `Z` already
  carries a factor of `f`, so it cancels: `size = pixels_proc × canonical / 300`.
  The sizes below survive an intrinsics estimate that is merely approximate.

Picking the processing resolution has an objective test rather than a taste:
`fx/W` and `fy/H` must agree once the aspect ratio is divided out, because real
sensors have square pixels. At 392 px and 700 px the camera decoder returns a
camera no sensor could be (8% off); at 518 px and 896 px it returns 0.2–0.4%.
896 px is used, and the check is reported in `summary.json` as
`square_pixel_error_pct`.

### Measuring against the belt, not against the image

Silhouette width and height answer the wrong question — a carton at an angle
has a silhouette wider than any of its sides. So the measurement happens in the
world:

1. **Fit the belt once.** The camera never moves, so neither does the belt.
2. **Remove the traffic first.** No frame in this clip has every patch of belt
   clear, so a plane fitted from any single frame is fitted partly to whatever
   parcel was sitting on it — and that tilt is then subtracted from every height
   measured afterwards. A parcel sits *on* the belt, so it is always nearer than
   the belt it hides: a high percentile of depth per pixel across frames returns
   the bare belt. Fit residual **8.4 mm** over ~35,000 px.
3. **Unproject the mask, drop what it leaked.** Behind a parcel here is a wall
   1.5 m further back, so a plain mean over the mask is dragged a long way by a
   minority of pixels. An object occupies one depth band; anything outside a
   robust band around the median is not part of it.
4. **Height along the belt normal, footprint as a minimum-area rectangle in the
   belt plane**, turned to run along the belt rather than along the image axes.

### One number of calibration, and what validates it

Monocular metric depth is scale-accurate to roughly 20%, and no amount of
geometry fixes that — the error is in the depth itself. One reference object
fixes it for the whole install, which is how a dimensioning station is
commissioned on site with a test carton.

This clip supplies its own. Two cartons print `Ebat/Dimensions 720x500x340 mm`
on the side, legible in frame. Both ride flat on the 720×500 face, so their
height above the belt is 340 mm — and height is the one dimension a single
camera sees whole, base on the fitted plane and top against open air.

| | Frames | Height measured | After ×1.226 | True |
|---|:--:|:--:|:--:|:--:|
| White carton — **calibration** | 19 | 277.4 mm | — | 340 mm |
| Brown carton — **validation**, never used to fit the scale | 11 | 277.8 mm | **340.5 mm** | 340 mm |

That agreement says the scale *transfers* between objects. It does **not** say
the depth is unbiased: both cartons are the same model at similar range, so any
systematic error hits them equally. The honest per-frame error bar is the spread
within one pass — the height wobbles by an IQR of **31 mm (11%)** frame to
frame, which is why every size is reported as a median over the pass.

### What depth fixed that had nothing to do with size

The static stack of cartons at the back of this shot is the same colour, the
same shape and the same size in pixels as the parcels riding past it. No
threshold on the image separates them, which is why the old configuration
fenced them off with a hand-drawn `x > 0.34` band — a band that also clipped
real belt traffic at the same x, and which forced the confidence floor up to
0.15 to stop the remaining stack detections from counting.

In depth they are 1.4 m apart and the separation is trivial. With a depth
corridor of 1.45–2.95 m doing that job, the floor drops to **0.08**, which is
what it takes to see the faint ones: the last cream container scores 0.098 as
`parcel`, the dark parcel behind it 0.12, the far-right carton 0.10.

Dropping the floor does not change the count — the objects it recovers are at
the tail of the clip and none of them completes a crossing before the belt
stops. It changes whether the belt is *fully seen*, which is the different
question, and it exposed the next one.

### A detection that clears every filter and still does not exist

The cream container at the end of the clip clears the confidence floor (0.098 >
0.08), clears the depth corridor (2.41 m), and clears the size gate. It still
carried no box, no identity and no measurement, because this clip's
`tracker_overrides` set `new_track_thresh: 0.20` — TrackTrack will not *start* a
track from a 0.098 detection. Lowering the confidence floor without lowering the
tracker's spawn gate buys nothing at all for anything under 0.20.

The fix is the prompt, not the gate, and it is the holdall lesson a second time:

| Prompts | conf on that container | cost |
|---|:--:|:--:|
| base four | 0.098 | — |
| **+ `styrofoam box`** | **0.580** | **+0.67 det/frame** |
| + `cool box` | 0.759 | +3.44 det/frame |
| + `plastic crate` | 0.098 | no effect |
| + `foam container` | 0.098 | no effect |

`cool box` scores highest and was rejected: five times the extra detections for
a box that is already well clear of every gate at 0.580. Note also that two
plausible synonyms move the score not at all — the useful phrase is not
predictable from the description being accurate.

### Ground truth for "every parcel detected"

Not an estimate. A **slit-scan** of the counting column — one pixel column per
frame, stacked into an image — shows every object that passed the line, as a
distinct blob, with no detector involved:

```
python - <<'PY'
import cv2, numpy as np
cap = cv2.VideoCapture('videos/03_packages_conveyor.mp4'); cols = []
while True:
    ok, f = cap.read()
    if not ok: break
    cols.append(f[430:780, 1179:1182].mean(axis=1))
cv2.imwrite('slitscan.jpg', np.stack(cols, axis=1).astype(np.uint8))
PY
```

It shows **8 parcels reaching the line**. Only **7 complete a crossing**, and
the difference is the whole point of reading it carefully: the slit-scan records
a parcel's *leading edge* arriving at the column, while the counting rule fires
on the box *centre*. The eighth parcel's leading edge passes at frame 480, its
centre stalls **44 px short**, and the belt decelerates from −5.03 px/frame
(frames 420–480) to **−1.37 px/frame** (frames 480–509) as the unload ends. It
never crosses.

So the count to hit is **7**, and the pipeline reports 7 with zero reverse
crossings. An earlier version of this document read the slit-scan as eight
crossings and treated the correct answer as a miss; that was wrong, and the fix
it prompted was still worth keeping — see below.

### The counting line: plumb, not normal-to-motion

What the line is supposed to be is a *plane cut across the belt*, and that plane
is vertical. Taking the normal of the **image** motion is not the same thing:
this belt travels (−4.69, +0.27) px/frame because the lane recedes as it crosses
frame, and the normal of that comes out **3.3° off plumb** — a tilt that is
perspective in the flow, not a property of the cut.

A vertical image line is the correct projection of that vertical plane whenever
the camera has no roll, and this one has none. Measured on the longest plumb
structure in view, the trailer's door post: **−0.4° to 0.0°**. So `line_plumb`
snaps it upright; clips whose camera *is* rolled leave the flag off and keep the
motion normal.

The line is also drawn the full working height of the lane (`line_span`,
y 330–940) rather than a 520 px segment in the middle of it. Length does not
change what a centre-anchored crossing test decides, but a line that stops short
of the belt reads as though anything passing above or below it is outside the
count, and it leaves no margin for a parcel riding higher than the ones the
half-length was set from.

### What this does not measure

A single camera sees the front of a parcel and not its back, so the footprint's
**short side is a lower bound** whenever no side face is in view. Height does
not have that problem, which is why the scale is calibrated on height alone and
why `length`, `width` and `height` are reported separately rather than rolled
into a single "size".

The footprint is reported **long side first**, as the parcel's own dimensions —
not as extents along the belt axes. Those are different questions once a parcel
sits at an angle, and only the first has an answer a depot can use: a carton is
720 × 500 whichever way round it was set down. Resolving it the other way needs
the rectangle's rotation, and reading that out of OpenCV is a trap worth
recording: `minAreaRect` returns its angle in (−90, 0] with the `w` side along
it, so the obvious cos-vs-sin test silently swaps the two sides for every parcel
rotated past 45°.

Volume is therefore a lower bound too. For a depot that bills on volumetric
weight, this is the wrong side to err on, and the fix is a second camera across
the lane rather than a better monocular model.

## Notes from getting this working

Four things that were not obvious and are worth keeping:

1. **TrackTrack's defaults reject zero-shot detections.** Stock thresholds are
   `track_high_thresh: 0.6` / `new_track_thresh: 0.7`, but open-vocabulary YOLOE
   scores on this footage run ~0.10–0.65. With defaults almost no track is ever
   created. `../factory_vision/counting/trackers/tracktrack_zeroshot.yaml` moves the gates down to
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

## Caveats

- Counts are line-crossing counts on short clips (7–17 s). The parcel belt now
  has a slit-scan ground truth (8 crossings); the two fruit lines do not, and
  their counts are unvalidated.
- The parcel clip's dimensioning depends on one calibration constant derived
  from a carton in that same clip. Moving the camera, or changing the lens,
  invalidates it — the belt plane and the scale both have to be re-measured.
- Depth costs ~7 s/frame on this 4-core CPU, so it runs every 5th frame and each
  parcel's measurement is carried between runs. On a GPU there is no reason not
  to run it every frame.
- Encoding is `mp4v` — this sandbox has no ffmpeg/H.264 encoder, so the files
  are MPEG-4 Part 2. Plays in VLC/QuickTime; re-encode if you need H.264.
- CPU-only: ~1.3 s/frame at `imgsz=1280`. On a GPU this is real-time territory.


---

