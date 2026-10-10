# Tomato Ripeness per Line — detect, follow, count, grade

Tomatoes run on four lines away from a camera at the head of a packing line.
Each tomato is found as a box, followed from frame to frame, counted once at a
horizontal gate across all four lines, and given a ripeness class from the
colour inside its box. The class says where it goes: ripe fruit to the local
market today, half-ripe to distributors for a 3–5 day trip, unripe to the
ripening room. Detection, tracking and counting only: no segmentation anywhere.
The output is a Factory Vision dashboard, 1920 × 1080:
**`output/tomato_ripeness.mp4`**.

## Result

| | |
|---|---|
| Tomatoes counted | **41** in 4.4 s at one gate across four lines |
| Per line | line 1: 8 · line 2: 9 · line 3: 13 · line 4: 11 |
| Matang (ripe, hue < 42.5°) | 0 · local market, ship today |
| Setengah matang (half-ripe, 42.5–62°) | 35 (85 %) · distributor / supermarket, 3–5 days |
| Mentah (unripe, ≥ 62°) | 6 (15 %) · ripening room, each one marked on the timeline |
| Line rate | ≈ 550 a minute, extrapolated from 4.4 s of footage |
| Class against a blind check by eye | **34 of 41** the same; the 7 others one class apart |

The rate is the 4.4 s clip scaled to a minute. It describes this clip, not a
shift. The fruit in this clip is pale orange, so no tomato reaches the ripe
class. The two the eye called ripe sit at 42.6° and 43.2°, right on the bound.

## The dashboard

- **On the picture.** Every tomato has a box in its class colour. Once a tomato
  is counted, its box fills and a label shows its line and class, e.g.
  "Line 3 · Setengah matang ✓", for 0.7 s. No track numbers are shown. The
  count gate runs across all four lines, and each line's name and running
  count sit on the gate.
- **KPIs.** Tomatoes counted and the rate, share ripe (ship today), share
  half-ripe, and the number of unripe tomatoes to the ripening room.
- **Shipping plan by ripeness.** One row per class with its destination and
  time to sale.
- **Ripeness per line.** One bar per line: its length is how many tomatoes the
  line carried, its colours are the ripeness mix, and the unripe share is on
  the right.
- **Last tomatoes counted.** Line, hue and class of each.
- **Colour spread** of the counted tomatoes against the class bounds.
- **Timeline** of the unripe tomatoes.

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
4. **Read the colour.** Inside an ellipse at the centre of the box, half its
   width and height, which keeps the reading on the fruit and off the belt and
   the neighbours. The pixels are put in CIELAB, highlights and deep shadow are
   left out, and the hue angle h = atan2(b\*, a\*) is taken from the median a\*
   and b\*. A tomato's hue is the median over the half of its frames where its
   box is sharpest.
5. **Not a tomato.** A track whose colour is grey (median chroma below 25) is
   steel, belt or a glove, and is not counted or drawn (6 such tracks). Counted
   tomatoes have chroma of 37 and more; those tracks have 15 or less.
6. **Classify.** The bounds (42.5° and 62°) were set on another clip from the
   same packhouse and series (Pexels 8675102), same lamps, and are used here
   unchanged.

## How far to trust the class

Every counted tomato was cut out at its two sharpest frames, the crops were
shuffled and coded (`output/tomato_audit_blind.jpg`), and each was classed by
eye before the codes were matched (`output/tomato_audit.json`). The bounds were
not changed afterwards.

- **34 of 41 agree.** All 6 tomatoes the system called unripe the eye called
  unripe too.
- Of the 7 that disagree, 5 are pale tomatoes the eye called unripe and the
  system half-ripe (hue 56–60°). The other 2 are the redder pair at 42.6° and
  43.2° that the eye called ripe.
- None is two classes apart.

Colour depends on the light. Another hall, other lamps or a camera with its own
white balance needs the bounds checked again against a few classed tomatoes.

## What this does not do

- **It does not find defects** such as cracks, blotches or rot; colour only.
- **It does not size the fruit.** There is nothing of known size in view.
- **The count covers the part of the lines in view.** The narrow channel on the
  far left carried no tomatoes in this clip.
- **The class-to-destination mapping is one example.** It is one line in
  `RIPENESS`.

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
