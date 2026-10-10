# Lemon Grading — colour grade at the washer, fruit by fruit

Lemons tumble under the sprays of a brush washer. A camera over the front rows
outlines every lemon, follows it while it is in the sharp part of the picture,
reads its skin colour and gives it a grade, and the grade says where it goes:
green to the premium market, green-yellow to the local market, yellow to
processing. The output is a Factory Vision dashboard, 1920 × 1080:
**`output/lemon_grading.mp4`**.

## Result

| | |
|---|---|
| Lemons read | **70** in 10.2 s, in the front rows |
| Grade A · green (hue ≥ 106°) | 27 (39 %) · premium / export |
| Grade B · green-yellow (97–106°) | 27 (39 %) · local market |
| Grade C · yellow (below 97°) | 16 (23 %) · processing (juice, syrup), each one raised as an event |
| Lemons in the zone at once | 8.5 on average |
| Grade against a blind check by eye | **21 of 24** the same; the 3 others A against B, never green against yellow |

The **grade mix is the figure to use, not the count**. A lemon that turns or is
hidden for a moment by its neighbours can come back under a new number. Track
pieces that end and start again within half a second in the same place with the
same colour are joined (33 of 152), but some doubles may remain, so the count is
labelled "lemons read" and no hourly rate is extrapolated from it. A double read
of the same fruit carries the same colour, so it moves the percentages far less
than the count.

## The clip

[Pexels 32953304](https://www.pexels.com/video/fresh-citrus-fruits-on-washing-conveyor-32953304/),
"Fresh citrus fruits on washing conveyor", filmed on a phone held by hand
(portrait, 1080 × 1920, 60 fps). `prepare.py` turns it into what a camera bolted
over the washer would see:

1. ffmpeg vidstab in tripod mode aligns every frame to the first, so the machine
   stays put and only the fruit moves;
2. a 1080 × 608 window over the front rows is cut out, scaled to 1920 × 1080 and
   resampled to 30 fps.

The picture is softer than a real fixed camera's (the window is upscaled 1.78×),
and the stabilised clip is still phone footage. None of the eight lime and lemon
clips found in this series was filmed on a tripod.

## Run it

```bash
pip install ultralytics opencv-python pillow imageio-ffmpeg numpy
python prepare.py                    # the clip, into input/
python dashboard/segment.py          # find, follow and read every lemon (~12-15 min on 4 cores)
python dashboard/dashboard.py        # the video
```

`FastSAM-x.pt` (138 MB) downloads into `weights/` on the first run.

## How it works

1. **Find.** FastSAM segments everything in the frame without being told what
   it is. A segment is a lemon when at least 60 % of its pixels are
   fruit-coloured (hue 15–50, saturation > 80 in OpenCV HSV), it is at least
   18,000 px, and its centre is in the inspection zone below 40 % of the frame
   height, the front rows that are in focus. A zero-shot detector (YOLOE,
   "lime", "lemon", "citrus fruit") was tried first: on these wet, packed fruit
   its best box scored 0.64 and several boxes spanned two fruits.
2. **Follow.** Each lemon keeps its number by mask overlap with the frames
   before (IoU ≥ 0.3, up to 4 frames unseen), then broken tracks are stitched
   (see above).
3. **Read the colour.** Inside the mask, in CIELAB, as a hue angle
   h = atan2(b\*, a\*), with water highlights and deep shadow left out; the
   lemon's value is the median over the half of its frames where it was
   sharpest. Green sits around 110–117°, yellow around 75–90°.
4. **Grade** once a lemon has been followed for 8 frames (0.27 s).

## How far to trust the grade

24 lemons were picked at random, cropped at their sharpest frame, shuffled and
lettered (`output/lemon_audit_blind.jpg`) and graded by eye before the letters
were matched (`output/lemon_audit.json`). The bounds (106° and 97°) were set
before this check and not changed after it: 21 of 24 agree, and the three that
do not are green against green-yellow. Moving the bounds to fit this sample would
only reach 22 of 24.

Colour depends on the light. Another hall, other lamps or a camera with its own
white balance needs the bounds checked again against a few graded lemons.

## What this does not do

- **It does not count lemons exactly** (see Result).
- **It does not find defects** such as rot, scars or misshapes; colour only.
- **It does not size the fruit.** There is nothing of known size in view to scale by.
- **The grade-to-market mapping is one example.** Whether yellow is "processing"
  or "ripe" depends on the variety and the buyer; it is one line in `GRADES`.

## Files

| File | Role |
|---|---|
| `prepare.py` | download, stabilise and cut the inspection clip |
| `dashboard/segment.py` | FastSAM, the fruit filter, tracking, colour per lemon → `output/tracks.json` |
| `dashboard/dashboard.py` | stitching, grades, events and the dashboard video |
| `dashboard/ui.py`, `dashboard/board.py` | the dashboard's look and layout (Inter, Material Symbols in `dashboard/assets/fonts`) |

## Credits

Footage: Pexels 32953304 (Pexels licence). Segmentation: FastSAM via Ultralytics.
Type: Inter (SIL OFL 1.1). Icons: Material Symbols (Apache 2.0).
