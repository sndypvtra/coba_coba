# Tomato Ripeness per Line — detect, follow, count, grade

Tomatoes run on four lines away from a camera at the head of a packing line.
Each tomato is found as a box, followed from frame to frame, counted once at a
horizontal gate across all four lines, and given a ripeness class from the
colour of the skin inside its box: ripe (red to orange-red), half-ripe (pale
orange with yellow) or unripe (yellow to green). Detection, tracking and
counting only: no segmentation anywhere.
The output is a Factory Vision dashboard, 1920 × 1080:
**`output/tomato_ripeness.mp4`**.

## Result

| | |
|---|---|
| Tomatoes counted | **41** in 4.4 s at one gate across four lines |
| Per line | line 1: 8 · line 2: 9 · line 3: 13 · line 4: 11 |
| Matang (ripe, skin hue < 62.5°) | 34 (83 %) · red to orange-red |
| Setengah matang (half-ripe, 62.5–73°) | 7 (17 %) · pale orange with yellow, each one in the event log |
| Mentah (unripe, ≥ 73°) | 0 · yellow to green |
| Line rate | ≈ 550 a minute, extrapolated from 4.4 s of footage |
| Class against a blind check by eye | **38 of 39** the same on the test half; the one miss is one class apart |

The rate is the 4.4 s clip scaled to a minute. It describes this clip, not a
shift.

## The dashboard

- **On the picture.** Every tomato has a box in its class colour. Once a tomato
  is counted, its box fills and a label shows its line and class, e.g.
  "Line 3 · Matang ✓", for 0.7 s. No track numbers are shown. The
  count gate runs across all four lines, and each line's name and running
  count sit on the gate.
- **KPIs.** Tomatoes counted and the rate, share ripe, share half-ripe, and the
  number of unripe tomatoes.
- **Komposisi Grade.** One row per class with what it looks like and its hue
  range.
- **Event Log.** Every tomato not yet ripe as it passes the gate, newest first,
  with a snapshot, its line and its hue.
- **Last tomatoes counted.** Line, hue and class of each.
- **Colour spread** of the counted tomatoes against the class bounds.
- **Timeline** of the tomatoes not yet ripe.

## The clip

[Pexels 8675103](https://www.pexels.com/video/tomatoes-on-a-moving-conveyor-belt-8675103/),
"Tomatoes on a moving conveyor belt", 1920 × 1080, 29.97 fps, 4.4 s. The
camera drifts slowly (about 30 px over the clip). `prepare.py` downloads the
clip and holds it still with ffmpeg vidstab in tripod mode and a 3 % zoom.

## Run it

```bash
pip install ultralytics opencv-python pillow imageio-ffmpeg numpy pyyaml lap
python prepare.py                    # the clip, into input/
python dashboard/detect.py           # detect, follow and read every tomato (~6 min on 4 cores)
python dashboard/dashboard.py        # the video
```

`yoloe-11l-seg.pt` (detector) and `yolo11n-cls.pt` (the tracker's
re-identification backbone) go in `weights/`. On the first run Ultralytics
fetches the MobileCLIP text encoder (~572 MB) into the working directory, so
run `detect.py` from `weights/` or link the file there.

## How it works

1. **Detect.** YOLOE, an open-vocabulary detector, is given the words
   "tomato" and "orange fruit" and returns a box and a score per fruit; the
   second word lifts the pale orange tomatoes that "tomato" alone scores low.
   Only boxes are used. The checkpoint also has a mask head, but its masks are
   never read. Boxes smaller than 0.08 % or larger than 6 % of the frame are
   dropped.
2. **Follow.** TrackTrack keeps one identity per tomato, with its gates lowered
   for zero-shot scores and a small re-identification network for appearance.
   A track is held for 3 frames before it can count.
3. **Count.** The tomatoes run away from the camera. The gate is a horizontal
   line at y = 600 px across all four lines, in the sharpest part of the
   picture. A tomato counts once, when its box centre crosses the gate, and its
   line is where it crosses. Two counts on one line within 4 frames and 60 px
   are one tomato whose identity broke (2 dropped).
4. **Read the colour.** Inside an ellipse at the centre of the box, 80 % of its
   width and height, in CIELAB, on skin pixels only: saturated (chroma above
   20), and neither highlight nor deep shadow. The cream belt and the steel that
   show inside a box are grey or pale, so they are left out. The reading is the
   median per-pixel hue angle h = atan2(b\*, a\*). A tomato's hue is the median
   over the half of its frames where its box is sharpest.
5. **Not a tomato.** A track whose colour is grey (median chroma below 20) is
   steel, belt or a glove, and is not counted or drawn (5 such tracks). Tomato
   tracks have chroma of 25 and more; those tracks have 16 or less.
6. **Classify.** Ripe below 62.5°, half-ripe from 62.5° to 73°, unripe from 73°.
   The bounds come from a blind check (below).

## How far to trust the class

Every tomato that appears on screen (78) was cut out at its two sharpest frames
with its box drawn. The crops were shuffled and coded
(`output/tomato_audit_blind.jpg`), and each was classed by eye before any reading
was matched: ripe is red to orange-red, half-ripe is pale orange with yellow,
unripe is yellow to green. The bounds were chosen on half of the tomatoes (dev)
and checked on the other half (test); every row is in `output/tomato_audit.json`.

- **Test half: 38 of 39 agree.** The one miss is a yellow-green tomato read as
  half-ripe (64°), one class apart. Dev half: 38 of 39.
- **A model instead of the colour reading was tried.** CLIP (ViT-B/32), asked
  "ripe red", "half-ripe orange and yellow" or "unripe green" tomato for each
  crop, agreed on 29 of the 39 test tomatoes, so the colour reading is kept.
- **An earlier version read every tomato too pale.** It took the colour of the
  whole centre of the box, belt and steel included, and used bounds from another
  clip (42.5° and 62°), so orange-red tomatoes came out half-ripe or unripe.

The eye check is one person's grading of crops blurred by motion; it is the
reference used here, not a lab measurement. Colour depends on the light: another
hall, other lamps or a camera with its own white balance needs the bounds
checked again against a few classed tomatoes.

## What this does not do

- **It does not find defects** such as cracks, blotches or rot; colour only.
- **It does not size the fruit.** There is nothing of known size in view.
- **The count covers the part of the lines in view.** The narrow channel on the
  far left carried no tomatoes in this clip.
- **The class bounds are for this light.** They are one line in `RIPENESS`.

## Files

| File | Role |
|---|---|
| `prepare.py` | download and stabilise the clip |
| `dashboard/detect.py` | YOLOE boxes, TrackTrack, colour per box → `output/tracks.json` |
| `dashboard/tracktrack.yaml` | the tracker's settings |
| `dashboard/dashboard.py` | the gate, lines, classes and the dashboard video |
| `dashboard/ui.py`, `dashboard/board.py` | the dashboard's look and layout (Inter, Material Symbols in `dashboard/assets/fonts`) |

## Credits

Footage: Pexels 8675103 (Pexels licence). Detection: YOLOE; tracking:
TrackTrack, both via Ultralytics. Type: Inter (SIL OFL 1.1). Icons: Material
Symbols (Apache 2.0).
