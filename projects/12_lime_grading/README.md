# Lemon Colour Grading on the OECD Chart — detect, follow, count, grade

Lemons ride two singulator chains away from the camera. Each lemon is found as
a box, followed from frame to frame, counted once at a horizontal gate across
both chains, and given a colour degree on the external colour chart of the OECD
standard for citrus fruit. Detection, tracking and counting only: no
segmentation anywhere. The output is a Factory Vision dashboard, 1920 × 1080:
**`output/lime_grading.mp4`**.

The Pexels clip is titled "lime sorting", but the fruit is pointed at both ends
and runs from green to yellow like the lemons on the chart, so it is graded on
the lemon chart. The folder keeps its first name.

## The standard

The chart is Figure 2, "Lemon grading according to external colour", in the
[CBI market-entry guide for lemons](https://www.cbi.eu/market-information/fresh-fruit-vegetables/lemons/market-entry),
which takes it from OECD, *Citrus Fruits*, International Standards for Fruit
and Vegetables (OECD Publishing, Paris, 2010).

- **Ten colour degrees**, from 1 (fully yellow) to 10 (dark green).
- **Degrees 1 to 9 are allowed** in Extra Class, Class I and Class II.
  **Degree 10 is out of grade.**
- **Uniformity:** only 3 adjacent colour degrees are allowed within the same
  consignment.

So colour does not separate Extra, Class I and Class II; defects and shape
decide that, and this system does not judge them. Colour decides two things: a
lemon at degree 10 is rejected, and the line must pack the fruit in lots of 3
adjacent degrees. The dashboard uses three such lots, 1–3 (yellow), 4–6
(yellow-green) and 7–9 (green), plus out of grade.

## Result

| | |
|---|---|
| Lemons counted | **87** in 8.2 s at one gate across both chains |
| Per line | line 1 (left chain): 35 · line 2 (right chain): 52 |
| Colour degrees | 1: 6 · 2: 1 · 3: 14 · 4: 21 · 5: 23 · 6: 16 · 7: 6 · 8–10: 0 |
| Within the standard (degrees 1–9) | 87 (100 %) · no lemon at degree 10 |
| Main lot, degrees 4–6 | 60 (69 %) |
| Lot 1–3 / lot 7–9 | 21 (24 %) / 6 (7 %) · packed apart, each one in the event log |
| Line rate | ≈ 640 a minute, extrapolated from 8.2 s of footage |
| Degree against matching to the chart by eye | **18 of 24 within 1 degree**, 11 exact; same lot **17 of 24** |

The rate is the 8.2 s clip scaled to a minute. It describes this clip, not a
shift.

## The dashboard

- **On the picture.** Every lemon has a box in its lot colour. Once a lemon is
  counted, its box fills and a label shows its line and degree, e.g.
  "Line 2 · Warna 5 ✓". No track numbers are shown. The count gate runs across
  both chains, and each line's running count sits at the gate.
- **KPIs.** Lemons counted and the rate, the share within the colour standard
  (degrees 1–9), the share in the main lot, and the number out of grade.
- **Komposisi Grade · OECD colour chart.** How many lemons at each of the ten
  degrees, each bar in the chart's own colour. The limit before degree 10 is
  marked, and the lots are shown underneath.
- **Event Log.** Every lemon outside the main lot as it passes the gate, with a
  snapshot, its line, its degree and the lot it goes to. A lemon at degree 10
  would show here as a rejection.
- **Lot trend.** The share of each lot among the lemons counted in the last 2 s,
  so a change in the incoming fruit is seen as it happens.
- **Degree spread** of the counted lemons on the chart scale.
- **Timeline** of the lemons outside the main lot.

## The clip

[Pexels 32953325](https://www.pexels.com/video/lime-sorting-on-conveyor-belt-in-factory-32953325/),
filmed on a phone held by hand (portrait, 1080 × 1920, 60 fps). `prepare.py`
makes it usable:

1. ffmpeg vidstab with a 3 s smoothing window and an automatic zoom takes out
   the shake of the hand and leaves no black edge. Tripod mode, which pins every
   frame to the first, was tried first. The person filming also walks a little,
   so tripod mode left jumps and black borders.
2. A 1080 × 608 window over both chains is cut out, scaled to 1920 × 1080 and
   resampled to 30 fps.

The picture still drifts slowly sideways, and it is softer than a fixed
camera's would be (the window is upscaled 1.78×). The gate is horizontal, so a
sideways drift does not change what is counted.

## Run it

```bash
pip install ultralytics opencv-python pillow imageio-ffmpeg numpy pyyaml lap
python prepare.py                    # the clip, into input/
python dashboard/detect.py           # detect, follow and read every lemon (~11 min on 4 cores)
python dashboard/dashboard.py        # the video
```

`yoloe-11l-seg.pt` (detector) and `yolo11n-cls.pt` (the tracker's
re-identification backbone) go in `weights/`. On the first run Ultralytics
fetches the MobileCLIP text encoder (~572 MB) into the working directory, so
run `detect.py` from `weights/` or link the file there.

## How it works

1. **Detect.** YOLOE, an open-vocabulary detector, is given the words "lime"
   and "lemon" and returns a box and a score per fruit; the two words together
   find both the green and the yellow fruit. Only boxes are used. The checkpoint
   also has a mask head, but its masks are never read.
2. **Follow.** TrackTrack keeps one identity per lemon, with its gates lowered
   for zero-shot scores and a small re-identification network for appearance.
   A track is held for 3 frames before it can count.
3. **Count.** The gate is a horizontal line at y = 600 px across both chains. A
   lemon counts once, when its box centre crosses it, and its line is the side
   of the picture it crosses on.
   - The lemons touch each other on the chain. At about 32 px a frame and about
     105 px tall, one passes the gate every 3.3 frames, and the measured gaps
     between counts cluster at 2–4 frames. Only two counts on one line under
     1.5 frames apart would be one lemon counted twice, and there were none.
   - The same tracks crossing lines 100 px above and below the gate give 93 and
     87, against 87 at the gate.
4. **Read the colour.** Inside an ellipse at the centre of the box, half its
   width and height, in CIELAB, with highlights and deep shadow left out. The
   hue angle h = atan2(b\*, a\*) is taken from the median a\* and b\*. A lemon's
   hue is the median over the half of its frames where its box is sharpest.
5. **Put it on the chart.** The ten lemons of the chart, read the same way,
   have hue angles of 86, 94, 100, 99, 103, 107, 113, 112, 116 and 124° for
   degrees 1 to 10. A straight line through them,
   hue = 85.29 + 3.63 × degree, turns a lemon's hue into its nearest degree.
   Degrees 3 and 4, and 7 and 8, differ on the chart mostly in lightness, not
   in hue; the line spreads them evenly.

## How far to trust the degree

24 lemons were picked at random across the degrees and cut out at their two
sharpest frames, with the counted box drawn. The crops were shuffled and
lettered under a copy of the chart (`output/lime_audit_blind.jpg`). Each was
matched to a chart degree by eye before the letters were matched
(`output/lime_audit.json`).

- **Within 1 degree: 18 of 24. Exact: 11 of 24.** On average the system reads
  0.1 degree lower than the eye, so there is no lean either way.
- **Same lot: 17 of 24.** The misses are lemons near the edge of a lot (degree
  3 against 4, 6 against 7) and a few read 2 degrees apart.
- **The chart is a studio photograph and the video a packhouse camera.** The
  scale is fitted to the chart, not to this hall's lamps, so a degree here is
  an estimate to about ±1. Before a lot rule is enforced on a real line, the
  scale should be set against a few lemons graded on the chart under that
  line's light.

An earlier version graded these fruits A/B/C by fixed hue bounds (deep green,
light green, yellowing). It was replaced by the chart, because the chart is the
standard buyers use; that earlier check is kept in the audit file.

## What this does not do

- **It does not decide Extra, Class I or Class II.** Those classes depend on
  defects, shape and skin blemishes as well, which this system does not see.
- **It does not size the fruit.** There is nothing of known size in view.

## Files

| File | Role |
|---|---|
| `prepare.py` | download, stabilise and cut the inspection clip |
| `dashboard/detect.py` | YOLOE boxes, TrackTrack, colour per box → `output/tracks.json` |
| `dashboard/tracktrack.yaml` | the tracker's settings |
| `dashboard/dashboard.py` | the gate, lines, OECD degrees and lots, trend, event log and the dashboard video |
| `dashboard/ui.py`, `dashboard/board.py` | the dashboard's look and layout (Inter, Material Symbols in `dashboard/assets/fonts`) |

## Credits

Footage: Pexels 32953325 (Pexels licence). Colour chart: OECD, *Citrus Fruits*
(2010), via CBI. Detection: YOLOE; tracking: TrackTrack, both via Ultralytics.
Type: Inter (SIL OFL 1.1). Icons: Material Symbols (Apache 2.0).
