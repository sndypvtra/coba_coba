# Peach Colour Grading on the USDA Standard — six-line sizer, fruit by fruit

Peaches drop from a feed belt into six lines and roll along them. A fixed camera
over the lines outlines every peach, follows it while it turns on its line,
measures how much of its skin is red, and checks it against the colour rules of
the USDA grade standards for peaches. The dashboard then says which grade the
lot meets on colour. Every peach on screen carries its line, its colour class
and its red share. The output is a Factory Vision dashboard, 1920 × 1080:
**`output/peach_grading.mp4`**.

## The standards

- **USDA, United States Standards for Grades of Peaches (7 CFR 51.1210–51.1214,
  May 2004)** ([standard](https://www.ams.usda.gov/sites/default/files/media/Peach_Standard%5B1%5D.pdf),
  [USDA page](https://www.ams.usda.gov/node/787)):
  - **U.S. Fancy:** each peach shall have not less than **one-third of its
    surface** showing blushed, pink or red colour. For colour, at most **10 %**
    of the peaches in a lot may fail this.
  - **U.S. Extra No. 1:** U.S. No. 1, and **50 % of the peaches in the lot**, by
    count, with not less than **one-fourth of the surface** blushed, pink or red.
    Single packages may hold as few as 40 % if the lot averages 50 %.
  - **U.S. No. 1 and U.S. No. 2:** no colour requirement.
- **UNECE FFV-26 and the EU marketing standard for peaches and nectarines**
  ([UNECE](https://unece.org/sites/default/files/2024-03/FFV-26_Peaches_2023_e.pdf),
  [EU Reg. 543/2011](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/869236/marketing-standard-peaches-nectarines.pdf)).
  They class fruit as Extra, Class I and Class II by skin defects, bruises and
  shape, and by size codes D to AAAA (51 to over 90 mm). On colour they set no
  number: Class I allows "slight defects in colouring", and an Extra Class
  package must be uniform in colouring. That is why the colour rules here are
  the USDA ones, and why colour uniformity per line is shown as information.

The grades also ask for freedom from decay, bruises, cuts and other defects,
which the camera does not judge. What the dashboard checks is the **colour
requirement** of each grade, and nothing else.

## Result

| | |
|---|---|
| Peaches counted | **204** in 8.1 s at one count gate across all six lines |
| Per line | line 1: 36 · line 2: 41 · line 3: 41 · line 4: 50 · line 5: 26 · line 6: 10 |
| Fancy colour (≥ ⅓ red) | **204 (100 %)** · the least red peach shows 48 % |
| Extra No. 1 colour (¼–⅓ red) | 0 |
| Below colour requirement (< ¼ red) | 0 |
| Lot colour | **meets U.S. Fancy** (0 % fail, limit 10 %) |
| Line rate | ≈ 1,500 peaches a minute, extrapolated from 8.1 s of footage |
| The 12 least red peaches, by eye | **12 of 12** show ≥ ⅓ red, as the system reads |

The rate is the 8.1 s clip scaled to a minute. It describes this clip, not a
shift. The lot in this clip is a deeply red variety, so every peach meets the
U.S. Fancy colour rule and the event log stays empty. On a paler lot the same
dashboard would flag each peach under ⅓ red as it passes the gate.

## The dashboard

- **On the picture.** Each peach has a FastSAM outline and a chip with its line,
  colour class and red share, e.g. "Line 3 · Fancy · 97%". Grey means fewer
  than 3 reads so far. The name tag of each line sits where the line leaves the
  picture (line 1 at the bottom, lines 2–6 on the right) with its running count.
- **Two horizontal lines across all six lines.** The cyan line is where the
  colour zone starts, just below the feed belt. The white line is the count gate.
- **KPIs.** Peaches counted and the rate; *Meets U.S. Fancy colour* against the
  90 % the lot needs; *Extra No. 1 colour rule* against the 50 % it needs;
  *Below colour requirement*.
- **Grade Composition · USDA colour.** The three colour classes and the lot
  verdict: the highest grade whose colour rule the lot meets.
- **Colour uniformity per line.** For each line, the middle half of its
  peaches' red shares, the median and the least red peach, against the ¼ and
  ⅓ marks. It shows whether one line carries paler fruit, and how even the
  colour is for an Extra Class pack.
- **Last peaches graded.** Line, red share and colour class.
- **Red colour spread** of all graded peaches against the ¼ and ⅓ marks.
- **Timeline** of the peaches below U.S. Fancy colour.

## The clip

[Pexels 32642676](https://www.pexels.com/video/efficient-peach-sorting-in-food-processing-plant-32642676/),
"Efficient peach sorting in food processing plant", 1920 × 1080, 29.97 fps,
8.1 s, filmed from a fixed point over the infeed of the sizer. The camera does
not move, so the clip is used as it is (`prepare.py` only downloads it).

## Run it

```bash
pip install ultralytics opencv-python pillow imageio-ffmpeg numpy scipy
python prepare.py                    # the clip, into input/
python dashboard/segment.py          # find and follow every peach (~30 min on 4 cores)
python dashboard/colour.py           # red share of every peach on the lines (~1 min)
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
2. **Follow.** Each track predicts where its peach will be from its last two
   positions, and new outlines are matched to those predictions by distance
   (Hungarian), within 0.9 of a peach diameter. A track that ends and one that
   starts within 5 frames where it was heading are joined (80 joins).
3. **Which line.** Line 1 runs steeply down the left of the picture. Lines 2 to 6
   fan out to the right; each one's centreline is the median path of the
   peaches that ran along it, and a peach belongs to the line whose centreline
   it follows most closely.
4. **Count.** The six lines all run inside the picture only near the top: lower
   down, the far lines have already left it on the right. So the count gate is a
   horizontal line at y = 375 px (source frame), just past where the fruit drops
   into the lines. A peach counts when its track crosses it, or when it is first
   found within 120 px below it (the fruit is still crowded there and a track
   may start just after the gate). Two counts on one line within 6 frames and
   60 px are one peach (77 such doubles dropped); the dropped piece of track is
   joined to the peach that was counted.
   As a cross-check, the same tracks were counted again where the lines are
   furthest apart (lines 2–6 at the right edge of the picture, line 1 low in
   the picture): 213 peaches there against 204 at the gate (−4 %), per line
   within ±9.
5. **Read the colour.** For every frame a peach is on its line, inside its
   outline shrunk by 2 px, each pixel is put in CIELAB and given a hue angle
   h = atan2(b\*, a\*). Highlights, deep shadow and grey pixels are left out.
   A pixel is red when h < 38°: the blush of these peaches sits at 0–30°, red
   skin under the lamps at 30–37°, the yellow-orange ground colour at 44–60°.
   FastSAM now and then outlines a group of small far-away peaches as one
   segment; a segment more than 1.6 times wider than the usual peach at its
   height is not read (461 segments).
6. **Colour class.** The peach turns on the rollers, so frame by frame it shows
   other sides; the USDA rule is about the whole surface. Its red share is the
   median of all its reads, fixed when it leaves the picture: ≥ ⅓ is Fancy
   colour, ¼ to ⅓ Extra No. 1 colour, below ¼ below the colour requirement.
   While it is still in view its chip shows the class from the reads so far.

## How far to trust the colour class

The red share was checked by eye four times while it was built (every row is in
`output/peach_audit.json`):

| Check | Set-up | Same | Note |
|---|---|---|---|
| 1 | right-hand lines only, red pixel < 30° | 14/24 | 9 of the 10 misses had the system stricter than the eye: lit red skin (30–37°) counted as not red |
| 2 | right-hand lines only, red pixel < 36° | 18/24 | 5 of 6 misses still stricter |
| 3 | all six lines, < 36°, first 12 reads | 13/24 | the first reads are where the fruit is crowded at the line entry; used to develop the fix |
| 4 | all six lines, < 38°, all reads, oversize segments skipped | 19/24 | none more than one band apart |

Those checks used three bands of 90 % and 60 % red, an earlier buyer
specification that the USDA rules have replaced. The USDA rule turns on ⅓, so a
fifth check looked where it matters. The 12 peaches the system read as least
red (48 % and up) were cut out four times each over their path, shuffled and
lettered (`output/peach_audit_usda_lowest.jpg`), and judged by eye before the
letters were matched: **all 12 show at least ⅓ red**, as the system reads. No
peach in this lot comes near the ⅓ mark, so the lot verdict does not hang on a
borderline reading.

The eye is not a perfect reference. The crops are small and blurred by the
fruit's motion. Colour depends on the light: another hall, other lamps or a
camera with its own white balance needs the 38° red bound checked again.

## What this does not do

- **It does not decide U.S. Fancy, Extra No. 1 or No. 1 on its own.** Those
  grades also need freedom from decay, bruises, cuts and other defects, and
  maturity, which the camera does not judge. It checks the colour rule only.
- **It does not give UNECE / EU classes or size codes.** Those turn on defect
  sizes in cm and fruit diameter in mm, and there is nothing of known size in
  view to scale by.
- **A peach's track can still break or swap.** Some peaches on screen are
  pieces of track that could not be joined safely to a counted peach. They
  carry a chip from their own reads but add nothing to the counts. On line 1,
  where the fruit queues touching, a crop now and then shows a neighbour.
- **It sees the side of the peach that faces the camera.** The rollers turn
  each peach while it is in view, so most of the skin is seen, but not all.

## Files

| File | Role |
|---|---|
| `prepare.py` | download the clip |
| `dashboard/segment.py` | FastSAM, the fruit filter, tracking → `output/tracks.json` |
| `dashboard/colour.py` | red share per peach per frame on the lines → `output/colour.json` |
| `dashboard/dashboard.py` | stitching, lines, the count gate, USDA colour classes, lot verdict and the dashboard video |
| `dashboard/ui.py`, `dashboard/board.py` | the dashboard's look and layout (Inter, Material Symbols in `dashboard/assets/fonts`) |

## Credits

Footage: Pexels 32642676 (Pexels licence). Colour rules: USDA 7 CFR 51.1210–51.1214.
Segmentation: FastSAM via Ultralytics.
Type: Inter (SIL OFL 1.1). Icons: Material Symbols (Apache 2.0).
