# LiquidLevel-Vision — method and limits

Overview and results in the [repository README](../README.md).

Measures how much liquid a filling machine puts into a bottle, from video alone.

    python src/liquid_level.py --capacity-ml 1500
    python src/liquid_level.py --video clip.mp4 --out-name result.mp4
    python src/liquid_level.py --detect          # overlay live YOLOE segmentation

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

**Capacity is measured to the thread line, so the clip does not end full.**
Reported as "if 1500 mL means filled to below the threads, then from the video it
should not be full". Right — and the old datum ("the fullest level this clip
reached") guaranteed 100% on the last frame by construction. The threads sit at
**y=585** and the liquid stops at **y~700**, so ~115 px of bottle is still empty.
Capacity now runs base → thread line, and the clip ends at **64.7% by volume /
74.4% by height**. After the silhouette ROI landed (below) the figure
settled at **67.1% / ~1,006 mL of 1,500 mL**.

Two geometry errors surfaced with it. The ROI's right edge was at x=900 while the
body reaches **x~1010**, clipping ~110 px of bore. And the unfilled neck was
extrapolated from the *topmost measured* bore — but right at the surface the mask
is only partial, so that value was **89 px against an upper-body bore of ~280**.
Since volume goes as bore squared, that shrank the empty neck about tenfold and
put the final reading at 94% of capacity. The neck is now carried up from a
robust upper-body median (272 px).

Volume % now sits *below* height % (64.7 vs 74.4), which is the right way round
for this jar: the empty neck is wide while the filled base tapers in.

**Closing the mask for demo use.** The bottom-left corner of the liquid was left
unshaded, and for a demo the overlay has to look complete. Two causes, both real:

- *The blob was being thrown away.* The rods and probe cut the liquid's image into
  separate components, and the mask kept only the **largest** base-anchored one.
  On the last frame the bottom-left corner was its own 5040 px component,
  discarded purely for being smaller. Now every component that reaches the base is
  kept; a splash clinging high on the shoulder is still dropped, since it never
  reaches the base.
- *Rod shadows desaturate the product.* In that corner saturation falls to
  **S 120-185**, under the strict `S>=200` cut. A relaxed cut (`S>=95`) now closes
  the mask, but **display only** and fenced in twice: confined to rows below the
  already-measured surface, and only for blobs that touch the strict mask, so
  conveyor spill is never painted into the bottle.

The measurement is provably untouched by this — it reads identically before and
after (67.4% volume / 74.4% height / ~1011 mL, no dip, worst jump 2.3%), because
the level comes from the strict mask and the volume integrates the bore.

**The ROI is a silhouette, not a rectangle.** A rectangle cannot express a
bottle: it necessarily takes in conveyor at the base corners, where product
spilled on the belt was both shading the overlay outside the bottle and inflating
the learned bore at the lowest rows. `BOTTLE_OUTLINE` is eight hand-measured
`(y, x_left, x_right)` points, interpolated between — the camera is fixed, so a
measured outline is exact and costs nothing. Final reading moved 1011 → 1006 mL
once the spill stopped counting.

**Residual:** the rods and probe stay unshaded, which is correct — they sit in
front of the bottle and are not liquid.

## Readout panel

Built for a portfolio proof-of-concept, so the panel states results rather than
narrating the implementation: a headline volume and fill percentage, then a short
spec table (nominal capacity, level height, reference datum, frame) and a two-item
colour legend. The earlier version printed internal notes on the frame —
thresholds, occlusion caveats, ROI behaviour — which belong in this README, not on
a demo reel.

Nominal capacity is a parameter (`--capacity-ml`, default 1500). What the vision
measures is the **fill fraction**; the millilitre figure is that fraction against
the capacity you configure for the SKU.

## Scope: this is a calibrated station, not a general model

It will **not** transfer to another clip unchanged, even at the same angle on the
same bottle. Tested rather than assumed — the same scene re-rendered with an 8%
zoom and a 60/30 px shift, the sort of difference a re-mounted camera produces:

| | Volume | Fill |
|---|---|---|
| Calibrated clip | 1,006 mL | 67.1% |
| Same scene, framing shifted | **239 mL** | **15.9%** |

Four times out, and reported through the same confident panel with no error flag.
That silence is the real hazard: nothing in the output says the calibration no
longer matches the scene.

Eleven constants are tied to this installation:

- **Absolute pixel geometry** — `ROI`, `THREAD_DATUM_Y`, `TEMPLATE_BOX`,
  `SURFACE_BAND`, and the eight-point `BOTTLE_OUTLINE`.
- **Colour tuned to this product and lighting** — `LIQUID_LO` (the `S>=200` cut
  that separates product from product-seen-through-glass) and `LIQUID_LO_SHADOW`.
- **Scale-dependent thresholds** — `JET_MAX_WIDTH_PX` is in pixels, so it moves
  with zoom; `POOL_MIN_RATIO`, `POOL_GAP_TOLERANCE`, `BORE_MIN_FRACTION` are
  tuned to this bore in this framing.

Plus the isotonic fit, which assumes a single monotonic fill of one bottle.

**Where it does run unchanged:** the same physical station — camera bolted, same
lens and working distance, same SKU, same lighting. That is the normal case for
filling-line vision, which is camera-fixed with a recipe per SKU, so the
constraint is ordinary rather than a flaw. `--video` points it at new footage from
that station.

**To widen it**, in increasing order of work: express the pixel thresholds as
fractions of the measured bore, which removes most of the zoom sensitivity;
recalibrate per station (~15 minutes — outline, thread line, band, one colour
sample); or derive the outline and colour automatically from a bottle
segmentation. The last is why `--detect` exists, and why it is not the default:
YOLOE finds these bottles at conf 0.78 but its boxes wander 194-328 px on clear
plastic, which is not stable enough to measure against.

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
real SKU capacity and the number means something; the 1,500 mL default is
illustrative. Disc integration also assumes a solid of revolution — true for
these round bottles, false for a flask or a rectangular jerrycan.

Residual limits worth knowing: the fill series still dips up to 5.3% frame to
frame while the surface is turbulent under the nozzle, and the ROI clips a
little of the bottle's base bulge, so the profile is slightly truncated. Both
affect the fraction only mildly because numerator and denominator are measured
the same way, but neither is zero.
