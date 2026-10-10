# Tomato Colour Grading on the USDA Scale — detect, follow, count, grade

Tomatoes run on four lines away from a camera at the head of a packing line.
Each tomato is found as a box, followed from frame to frame, counted once at a
horizontal gate across all four lines, and given a colour class of the USDA
standards for fresh tomatoes. The dashboard then checks whether the lot may
carry its colour label under the USDA off-colour tolerance. Detection, tracking
and counting only: no segmentation anywhere. The output is a Factory Vision
dashboard, 1920 × 1080: **`output/tomato_ripeness.mp4`**.

## The standards

- **USDA, United States Standards for Grades of Fresh Tomatoes,
  [7 CFR 51.1860](https://www.law.cornell.edu/cfr/text/7/51.1860).** It sets six
  colour classes by how much of the surface has turned from green:

  | Class | Surface |
  |---|---|
  | Green | completely green |
  | Breakers | definite break from green on ≤ 10 % |
  | Turning | > 10 % and ≤ 30 % changed from green |
  | Pink | > 30 % and ≤ 60 % pink or red |
  | Light Red | > 60 % pinkish-red or red, ≤ 90 % red |
  | Red | > 90 % red |

  A lot that fits none of them may be labelled "Mixed Color".
- **USDA tolerance, [7 CFR 51.1861](https://www.law.cornell.edu/cfr/text/7/51.1861).**
  When a lot is labelled with a colour class, at most 10 % of its tomatoes may
  fail that colour, of which at most 5 % green.
- **UNECE standard for tomatoes (FFV-36).** It asks for practically uniform
  ripeness and colouring in Extra Class and Class I.
- **From colour class to camera reading.** A colorimeter study measured the hue
  angle of tomatoes classed on the USDA scale: 113.3° Green, 109.1° Breakers,
  93.2° Turning, 78.1° Pink, 64.9° Light Red, 59.3° Red
  ([López-Camelo and Gómez 2004, *Horticultura Brasileira* 22(3):534-537, Table 1](https://scielo.br/j/hb/a/nKQ4gGWYRc9CV37YWSKCGZt/?lang=en)).
  The class bounds used here are the midpoints between those means: 62.1, 71.5,
  85.7, 101.2 and 111.2°.

## Result

| | |
|---|---|
| Tomatoes counted | **41** in 4.4 s at one gate across four lines |
| Per line | line 1: 8 · line 2: 9 · line 3: 13 · line 4: 11 |
| USDA colour classes | Red 34 (83 %) · Light Red 7 (17 %) · Pink, Turning, Breakers, Green 0 |
| Lot check | main class Red; off-colour 17 % > 10 % limit → label "Mixed Color", or sort out the Light Red fruit to label the lot Red |
| Green in lot | 0 (limit 5 %) |
| Line rate | ≈ 550 a minute, extrapolated from 4.4 s of footage |
| Class against a blind check by eye | **75 of 78** the same; the 3 others one class apart |

The rate is the 4.4 s clip scaled to a minute. It describes this clip, not a
shift.

## The dashboard

- **On the picture.** Every tomato has a box in its USDA class colour. Once a
  tomato is counted, its box fills and a label shows its line and class, e.g.
  "Line 3 · Red ✓". No track numbers are shown. The count gate runs across all
  four lines, and each line's name and running count sit on the gate.
- **KPIs.** Tomatoes counted and the rate, the share in the main colour class,
  the off-colour share against the 10 % limit, and green tomatoes against the
  5 % limit.
- **Grade Composition · USDA colour classes.** How many tomatoes in each of the
  six classes, and the lot label check: the main class if off-colour is within
  10 %, otherwise "Mixed Color" or sort.
- **Event Log.** Every off-colour tomato as it passes the gate, with a
  snapshot, its line and its hue. A green tomato is raised as high severity.
- **Off-colour trend.** The off-colour share of the lot as it builds up,
  against the 10 % limit.
- **Colour spread** of the counted tomatoes on the hue axis with the USDA class
  bounds.
- **Timeline** of the off-colour tomatoes.

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
   second word lifts the pale tomatoes that "tomato" alone scores low. Only
   boxes are used. The checkpoint also has a mask head, but its masks are never
   read. Boxes smaller than 0.08 % or larger than 6 % of the frame are dropped.
2. **Follow.** TrackTrack keeps one identity per tomato, with its gates lowered
   for zero-shot scores and a small re-identification network for appearance.
   A track is held for 3 frames before it can count.
3. **Count.** The gate is a horizontal line at y = 600 px across all four lines,
   in the sharpest part of the picture. A tomato counts once, when its box
   centre crosses the gate, and its line is where it crosses. Two counts on one
   line within 4 frames and 60 px are one tomato whose identity broke
   (2 dropped).
4. **Read the colour.** Inside an ellipse at the centre of the box, 80 % of its
   width and height, in CIELAB, on skin pixels only: saturated (chroma above
   20), and neither highlight nor deep shadow. The cream belt and the steel
   that show inside a box are left out. The reading is the median per-pixel hue
   angle h = atan2(b\*, a\*). A tomato's hue is the median over the half of its
   frames where its box is sharpest.
5. **Not a tomato.** A track whose colour is grey (median chroma below 20) is
   steel, belt or a glove, and is not counted or drawn (5 such tracks).
6. **Classify and check the lot.** The hue gives the USDA class through the
   bounds above. The lot's main class is the one most tomatoes meet; every
   other tomato is off-colour for that label.

## How far to trust the class

Every tomato that appears on screen (78) was cut out at its two sharpest frames
with its box drawn. The crops were shuffled and coded
(`output/tomato_audit_blind.jpg`), and each was classed by eye on the USDA
scale before any reading was matched (`output/tomato_audit.json`).

- **75 of 78 agree, and the 3 others are one class apart.** Of the 41 counted
  tomatoes, 40 agree.
- **The bounds were not fitted to this clip.** They come from the published
  colorimeter means, so the check is a fair test of them.
- **The eye labels were made on the same crops as an earlier version's check.**
  That version used three local classes (ripe, half-ripe, unripe) fitted to
  those labels. The USDA classes replace it.
- **A colorimeter is not a camera.** The study measured skin with a CR-300
  chroma meter under illuminant C; this reads skin through a camera under
  packhouse lamps. The agreement above says the bounds hold for this hall.
  Another hall, other lamps or another white balance needs a few tomatoes
  checked again.
- The eye check is one person's grading of crops blurred by motion. It is the
  reference used here, not a lab measurement.

## What this does not do

- **It does not decide Extra, Class I or Class II.** Those also depend on
  defects, firmness, cracks and shape, which this system does not see.
- **It sees one side of each tomato.** USDA classes count the whole surface in
  aggregate; a camera above the line sees the top.
- **It does not size the fruit.** There is nothing of known size in view.

## Files

| File | Role |
|---|---|
| `prepare.py` | download and stabilise the clip |
| `dashboard/detect.py` | YOLOE boxes, TrackTrack, skin colour per box → `output/tracks.json` |
| `dashboard/tracktrack.yaml` | the tracker's settings |
| `dashboard/dashboard.py` | the gate, lines, USDA classes, lot check and the dashboard video |
| `dashboard/ui.py`, `dashboard/board.py` | the dashboard's look and layout (Inter, Material Symbols in `dashboard/assets/fonts`) |

## Credits

Footage: Pexels 8675103 (Pexels licence). Colour classes: USDA 7 CFR 51.1860–51.1861;
hue per class: López-Camelo and Gómez (2004). Detection: YOLOE; tracking:
TrackTrack, both via Ultralytics. Type: Inter (SIL OFL 1.1). Icons: Material
Symbols (Apache 2.0).
