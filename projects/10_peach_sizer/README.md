# Peach Grading — red colour grade on a six-line sizer, fruit by fruit

Peaches drop from a feed belt into six lines and roll along them. A fixed camera
over the lines outlines every peach, follows it while it turns on its line,
measures how much of its skin is red, and gives it a grade. The grade says where
it goes: Grade A to premium and export packs, Grade B to regular packs, Grade C
off the line to processing. Every peach on screen carries its line and its
grade. The output is a Factory Vision dashboard, 1920 × 1080:
**`output/peach_grading.mp4`**.

## Result

| | |
|---|---|
| Peaches counted | **204** in 8.1 s at one count gate across all six lines |
| Per line | line 1: 36 · line 2: 41 · line 3: 41 · line 4: 50 · line 5: 26 · line 6: 10 |
| Grade A · red ≥ 90 % | 177 (87 %) · premium packs / export |
| Grade B · red 60–90 % | 24 (12 %) · regular packs |
| Grade C · red < 60 % | 3 (1 %) · diverted to processing, each one marked on the timeline |
| Line rate | ≈ 1,500 peaches a minute, extrapolated from 8.1 s of footage |
| Grade against a blind check by eye | **19 of 24** the same on peaches not seen before; the 5 others one grade apart, 3 stricter and 2 softer than the eye |

The rate is the 8.1 s clip scaled to a minute. It describes this clip, not a
shift. The lot in this clip is a deeply red variety, so most fruit is Grade A.

## The dashboard

- **On the picture.** Each peach has a FastSAM outline and a chip with its line
  and grade, e.g. "Line 3 · Grade A". The colour of the outline and chip is
  the grade; grey means fewer than 3 reads so far. The name tag of each line
  sits where the line leaves the picture (line 1 at the bottom, lines 2–6 on
  the right) with its running count.
- **Two horizontal lines across all six lines.** The cyan line is where the
  grading zone starts, just below the feed belt, where the fruit drops into the
  lines. The white line is the count gate.
- **KPIs.** Peaches counted and the rate, Grade A share, Grade B share, Grade C
  diverted.
- **Grade composition** with the destination of each grade.
- **Quality per line.** One bar per line: its length is how many peaches the
  line carried, its colours are the grade mix, and the share of Grade A is on
  the right. It shows whether the feed is spread evenly over the lines and
  whether one line carries worse fruit.
- **Last peaches graded.** The latest peaches graded, with line, red share and grade.
- **Red-share spread** of all graded peaches against the grade bounds.
- **Timeline** of the Grade C diversions.

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
6. **Grade.** The peach turns on the rollers, so frame by frame it shows other
   sides. Its red share is the median of all its reads, and its grade is fixed
   when it leaves the picture. While it is still in view its chip shows the
   grade from the reads so far.

## How far to trust the grade

The grade bounds (90 % and 60 % red) are an example buyer specification and were
set before any check. Each check took 24 graded peaches, cut three crops of each
from the frames the system read, shuffled and lettered them, and graded them by
eye against the same bounds before the letters were matched. Every check used
peaches no earlier check had used.

| Check | Set-up | Same | Note |
|---|---|---|---|
| 1 | right-hand lines only, red pixel < 30° | 14/24 | 9 of the 10 misses had the system stricter than the eye: lit red skin (30–37°) counted as not red |
| 2 | right-hand lines only, red pixel < 36° | 18/24 | 5 of 6 misses still stricter |
| 3 | all six lines, < 36°, grade on the first 12 reads | 13/24 | the first reads are where the fruit is crowded at the line entry; used to develop the fix |
| **4** | **all six lines, < 38°, all reads, oversize segments skipped** | **19/24** | **3 stricter, 2 softer; none two grades apart** |

Check 3 was used as a development set: grading on all reads and the 38° bound
brought it from 13 to 17 of 24, with the misses no longer one-sided. Check 4,
on fresh peaches, is the figure to quote. It holds 13 Grade A and 11 Grade B
peaches as the system graded them. All three Grade C peaches had already been
used in earlier checks, so Grade C has no fresh check. The crops are
`output/peach_audit_blind.jpg`, and every check's rows are in
`output/peach_audit.json`.

The eye is not a perfect reference either. The crops are small and blurred by
the fruit's motion, and it is hard to judge by eye where 60 % or 90 % of a
turning peach lies.

Colour depends on the light. Another hall, other lamps or a camera with its own
white balance needs the 38° bound checked again against a few graded peaches.

## What this does not do

- **It does not size the fruit.** There is nothing of known size in view to
  scale by; the sizer does that mechanically.
- **It does not find defects** such as bruises, splits or rot; colour only.
- **A peach's track can still break or swap.** Some peaches on screen are
  pieces of track that could not be joined safely to a counted peach. They
  carry a chip from their own reads but add nothing to the counts. On line 1,
  where the fruit queues touching, a crop now and then shows a neighbour.
- **The grade-to-destination mapping is one example.** Buyer specifications
  for red colour differ by variety and market; it is one line in `GRADES`.

## Files

| File | Role |
|---|---|
| `prepare.py` | download the clip |
| `dashboard/segment.py` | FastSAM, the fruit filter, tracking → `output/tracks.json` |
| `dashboard/colour.py` | red share per peach per frame on the lines → `output/colour.json` |
| `dashboard/dashboard.py` | stitching, lines, the count gate, grades and the dashboard video |
| `dashboard/ui.py`, `dashboard/board.py` | the dashboard's look and layout (Inter, Material Symbols in `dashboard/assets/fonts`) |

## Credits

Footage: Pexels 32642676 (Pexels licence). Segmentation: FastSAM via Ultralytics.
Type: Inter (SIL OFL 1.1). Icons: Material Symbols (Apache 2.0).
