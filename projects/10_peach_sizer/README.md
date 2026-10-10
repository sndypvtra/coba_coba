# Peach Grading — red colour class on the sizer, fruit by fruit

Peaches roll single file along the five roller lanes of a sizer. A fixed camera
over the lanes outlines every peach, follows it while it turns on the rollers,
measures how much of its skin is red, and gives it a class. The class says where
it goes: Extra to premium and export packs, Class I to regular packs, Class II
off the premium line to the local market or processing. The output is a
Factory Vision dashboard, 1920 × 1080: **`output/peach_grading.mp4`**.

## Result

| | |
|---|---|
| Peaches graded | **172** in 8.1 s, counted once each at the gate at the end of the lanes |
| Extra · red ≥ 90 % | 142 (83 %) · premium packs / export |
| Class I · red 60–90 % | 24 (14 %) · regular packs |
| Class II · red < 60 % | 6 (3 %) · local market / processing, each one raised as an event |
| Line rate | ≈ 1,270 peaches a minute, extrapolated from 8.1 s of footage |
| Class against a blind check by eye | **18 of 24** the same; the 6 others one class apart, never Extra against Class II |

The rate is the 8.1 s clip scaled to a minute. It describes this clip, not a
shift. Three crossings were dropped as the same peach counted twice on one lane.

## The clip

[Pexels 32642676](https://www.pexels.com/video/efficient-peach-sorting-in-food-processing-plant-32642676/),
"Efficient peach sorting in food processing plant", 1920 × 1080, 29.97 fps,
8.1 s, filmed from a fixed point over the infeed of a roller sizer. The camera
does not move, so the clip is used as it is (`prepare.py` only downloads it).

## Run it

```bash
pip install ultralytics opencv-python pillow imageio-ffmpeg numpy scipy
python prepare.py                    # the clip, into input/
python dashboard/segment.py          # find and follow every peach (~30 min on 4 cores)
python dashboard/colour.py           # red share of every peach in the grading zone (~1 min)
python dashboard/dashboard.py        # the video
```

`FastSAM-x.pt` (138 MB) downloads into `weights/` on the first run.

## How it works

1. **Find.** FastSAM segments everything in the frame without being told what
   it is. A segment is a peach when at least half of its pixels are
   peach-coloured (OpenCV HSV hue ≤ 25 or ≥ 165, saturation > 90, value > 45),
   it is 1,200 to 90,000 px, and it lies below the feed belt and the people at
   the back of the machine. A zero-shot detector (YOLOE) was tried first:
   prompted "peach" it found nothing, prompted "apple" it boxed touching
   peaches in pairs.
2. **Follow.** Peaches move fast along the lanes, so each track predicts where
   its peach will be from its last two positions, and new outlines are matched
   to those predictions by distance (Hungarian), within 0.9 of a peach diameter.
3. **Read the colour.** Only in the grading zone, right of x = 1250 px in the
   source frame, where the peaches run one by one, in focus and in full view.
   Inside the outline, shrunk by 2 px to stay off the roller, each pixel is put
   in CIELAB and given a hue angle h = atan2(b\*, a\*). Highlights, deep shadow
   and grey pixels are left out. A pixel is red when h < 36°: the blush of
   these peaches sits at 0–30°, red skin under the lamps at 30–37°, the
   yellow-orange ground colour at 44–60°. A frame's read is the red share of
   the peach's pixels.
4. **Grade.** The peach turns on the rollers, so frame by frame it shows
   different sides; its red share is the median of all its reads (11 frames
   for a typical peach). It is counted, and its class fixed, when it crosses
   the count gate at x = 1780 px. While it is still in the zone its label shows
   the class from the reads so far, once it has at least 3.

## How far to trust the grade

The class bounds (90 % and 60 % red) are an example buyer specification and were
set before any check. Each check took 24 graded peaches, cut three crops of each
(start, middle and end of the grading zone), shuffled and lettered them, and
graded them by eye against the same bounds before the letters were matched.

* **First check, red pixel bound at 30°: 14 of 24.** Nine of the ten
  disagreements had the system one class lower than the eye. Painting the
  pixels showed why: the lit side of a red peach turns red-orange (30–37°), and
  the 30° bound counted it as not red. True yellow ground colour sits at
  44–60°, so the pixel bound moved to 36°. The class bounds did not change.
* **Second check, on 24 peaches not in the first: 18 of 24**
  (`output/peach_audit_blind.jpg`, `output/peach_audit.json`). This sample is
  deliberately weighted to the borders (10 Extra, 10 Class I, 4 Class II, as
  the system graded them), so it is harder than a random draw, where most
  peaches are clearly Extra. All six disagreements are one class apart, and
  five of them still have the system stricter than the eye.

The bounds were not moved again to fit this sample. The eye is not a perfect
reference either: the crops are small and blurred by the fruit's motion, and
where 60 % or 90 % of a turning peach lies is hard to judge by eye.

Colour depends on the light. Another hall, other lamps or a camera with its own
white balance needs the 36° bound checked again against a few graded peaches.

## What this does not do

- **It does not size the fruit.** There is nothing of known size in view to
  scale by; the sizer does that mechanically.
- **It does not find defects** such as bruises, splits or rot; colour only.
- **It does not read the peaches in the left chute** or the ones still bunched
  in the drop zone at the start of the lanes; only the lanes' grading zone.
- **The class-to-destination mapping is one example.** Buyer specifications
  for red colour differ by variety and market; it is one line in `GRADES`.

## Files

| File | Role |
|---|---|
| `prepare.py` | download the clip |
| `dashboard/segment.py` | FastSAM, the fruit filter, tracking → `output/tracks.json` |
| `dashboard/colour.py` | red share per peach per frame in the grading zone → `output/colour.json` |
| `dashboard/dashboard.py` | gate count, classes, events and the dashboard video |
| `dashboard/ui.py`, `dashboard/board.py` | the dashboard's look and layout (Inter, Material Symbols in `dashboard/assets/fonts`) |

## Credits

Footage: Pexels 32642676 (Pexels licence). Segmentation: FastSAM via Ultralytics.
Type: Inter (SIL OFL 1.1). Icons: Material Symbols (Apache 2.0).
