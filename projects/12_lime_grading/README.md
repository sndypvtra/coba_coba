# Lime Grading — detect, follow, count and grade on two chains

Limes ride two singulator chains away from the camera. Each lime is found as a
box, followed from frame to frame, counted once at a horizontal gate across both
chains, and given a grade from the colour inside its box. The grade says where
it goes: Grade A, deep green, to export and supermarkets; Grade B, light green,
to the local market; Grade C, yellowing, off the line to processing (juice,
concentrate). Detection, tracking and counting only: no segmentation anywhere.
The output is a Factory Vision dashboard, 1920 × 1080:
**`output/lime_grading.mp4`**.

## Result

| | |
|---|---|
| Limes counted | **87** in 8.2 s at one gate across both chains |
| Per line | line 1 (left chain): 35 · line 2 (right chain): 52 |
| Grade A · deep green (hue ≥ 106°) | 18 (21 %) · export / supermarket |
| Grade B · light green (97–106°) | 54 (62 %) · local market |
| Grade C · yellowing (below 97°) | 15 (17 %) · processing, each one marked on the timeline |
| Line rate | ≈ 640 a minute, extrapolated from 8.2 s of footage |
| Grade against a blind check by eye | **15 of 23** the same; **yellowing 7 of 7**; every miss is A against B |

The rate is the 8.2 s clip scaled to a minute. It describes this clip, not a
shift.

## The dashboard

- **On the picture.** Every lime has a box in its grade colour. Once a lime is
  counted, its box fills and a label shows its line and grade, e.g.
  "Line 2 · Grade A ✓". No track numbers are shown. The count gate runs across
  both chains, and each line's running count sits at the gate.
- **KPIs.** Limes counted and the rate, Grade A share, Grade B share, and the
  number of yellowing limes diverted to processing.
- **Grade mix and destination.**
- **Grade per line.** Each chain's load and grade mix side by side. When the
  two chains are fed from different sources, a difference in quality shows here.
- **Quality trend.** The share of Grade A and Grade C among the limes counted
  in the last 2 s, so a change in the incoming fruit is seen as it happens.
- **Colour spread** of the counted limes against the grade bounds.
- **Timeline** of the yellowing limes diverted.

## The clip

[Pexels 32953325](https://www.pexels.com/video/lime-sorting-on-conveyor-belt-in-factory-32953325/),
"Lime sorting on conveyor belt in factory", filmed on a phone held by hand
(portrait, 1080 × 1920, 60 fps). `prepare.py` makes it usable:

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
python dashboard/detect.py           # detect, follow and read every lime (~11 min on 4 cores)
python dashboard/dashboard.py        # the video
```

`yoloe-11l-seg.pt` (detector) and `yolo11n-cls.pt` (the tracker's
re-identification backbone) go in `weights/`. On the first run Ultralytics
fetches the MobileCLIP text encoder (~572 MB) into the working directory, so
run `detect.py` from `weights/` or link the file there.

## How it works

1. **Detect.** YOLOE, an open-vocabulary detector, is given the words "lime"
   and "lemon" and returns a box and a score per fruit; the second word lifts
   the yellowing limes that "lime" alone scores low. Only boxes are used. The
   checkpoint also has a mask head, but its masks are never read.
2. **Follow.** TrackTrack keeps one identity per lime, with its gates lowered
   for zero-shot scores and a small re-identification network for appearance.
   A track is held for 3 frames before it can count.
3. **Count.** The gate is a horizontal line at y = 600 px across both chains. A
   lime counts once, when its box centre crosses it, and its line is the side
   of the picture it crosses on.
   - The limes touch each other on the chain. At about 32 px a frame and about
     105 px tall, one passes the gate every 3.3 frames, and the measured gaps
     between counts cluster at 2–4 frames. Only two counts on one line under
     1.5 frames apart would be one lime counted twice, and there were none.
   - The same tracks crossing lines 100 px above and below the gate give 93 and
     87, against 87 at the gate.
4. **Read the colour.** Inside an ellipse at the centre of the box, half its
   width and height, in CIELAB, with highlights and deep shadow left out. The
   hue angle h = atan2(b\*, a\*) is taken from the median a\* and b\*. A lime's
   hue is the median over the half of its frames where its box is sharpest.
5. **Grade.** The bounds (106° and 97°) were set on another clip from the same
   packhouse and series (Pexels 32953304), same lamps, and are used here
   unchanged.

## How far to trust the grade

Limes were picked at random per grade, cut out at their two sharpest frames
with the counted box drawn, shuffled and lettered
(`output/lime_audit_blind.jpg`), and graded by eye before the letters were
matched (`output/lime_audit.json`). The bounds were not changed afterwards.

- **15 of 23 agree, and none is two grades apart.**
- **Yellowing agrees 7 of 7, both ways.** Every lime the eye called yellowing
  the system graded C, and the system called nothing else C. This is the call
  that decides what leaves the packing line.
- **All 8 misses are deep green against light green** (Grade A against B), in
  both directions, at hues of 101–108°. Where light green ends and deep green
  begins is the least sure call, for the eye as much as for the system.
- **A first check scored 13 of 24.** Its crops had no box drawn. In a row of
  touching limes it was not clear which one was meant, so it was repeated on
  fresh limes with the box drawn. Both are in the audit file.

Colour depends on the light. Another hall, other lamps or a camera with its own
white balance needs the bounds checked again against a few graded limes.

## What this does not do

- **It does not find defects** such as scars, oil spots or rot; colour only.
- **It does not size the fruit.** There is nothing of known size in view.
- **The grade-to-destination mapping is one example.** It is one line in `GRADES`.

## Files

| File | Role |
|---|---|
| `prepare.py` | download, stabilise and cut the inspection clip |
| `dashboard/detect.py` | YOLOE boxes, TrackTrack, colour per box → `output/tracks.json` |
| `dashboard/tracktrack.yaml` | the tracker's settings |
| `dashboard/dashboard.py` | the gate, lines, grades, trend and the dashboard video |
| `dashboard/ui.py`, `dashboard/board.py` | the dashboard's look and layout (Inter, Material Symbols in `dashboard/assets/fonts`) |

## Credits

Footage: Pexels 32953325 (Pexels licence). Detection: YOLOE; tracking:
TrackTrack, both via Ultralytics. Type: Inter (SIL OFL 1.1). Icons: Material
Symbols (Apache 2.0).
