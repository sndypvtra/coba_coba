# Analytics: what the camera tells the plant manager

Two dashboards, one per case, each as a 1920 × 1080 video: the camera picture
with what the system sees drawn on it, and beside it the numbers the line is run
by. Everything on screen comes from the pixels of the clip. The scene's ground
truth is used only afterwards, to score the result, and that score is printed
on the dashboard.

| Video | Clip | What it decides |
|---|---|---|
| `../output/analytics/line_qc.mp4` | `../output/pack_line.mp4`, 15 s | every tray of 10 cans: complete, or short and which slot is empty |
| `../output/analytics/packing_qc.mp4` | `../packing/output/packing_station.mp4`, 34 s | the box at the station: how many are in it now, which slot is next, empty picks, and every box that leaves |

```bash
pip install opencv-python pillow imageio-ffmpeg numpy
python dashboard.py line
python dashboard.py pack
python dashboard.py pack --still 300 470      # a few frames as JPEG instead of the video
```

Besides the video, each run writes `<name>_events.json` (every event with its
frame, severity and text) and `<name>_score.json` (the check against the truth).

## What a plant manager needs from it, and where it is on screen

The question behind both cases is the same: *does every pack that leaves hold
what the customer pays for, and if not, why not?* That turns into five needs.

| Need | Can line | Packing station |
|---|---|---|
| **Catch the short pack before it ships**, with the evidence | tray box turns red at the inspection zone, chip "9/10 · KURANG", the empty slot ringed; event with snapshot; "tandai reject" | X on the empty slot the moment the miss is certain; box leaves red "18/20 · KURANG"; history row says *"Tahan, tambah 2 unit"* |
| **Know exactly what to fix on the pack** | slot name (A2, B5 ...) on the video, in the event and in the tray tile | slot map of the box at the station; empty slots listed per box |
| **Find the root cause, not only the symptom** | "Posisi kaleng yang hilang": a tray-shaped heat map of where cans go missing; the same slot twice points at one filler lane | each empty pick is tied to the feeder: "Celah suplai di feeder" is raised as the robot leaves for a product that is not there, before the slot is lost |
| **Quality and output in one look** | trays inspected, short trays (% of inspected), cans missing, line rate in trays/min | count of the box now, boxes done (complete / short), empty picks, robot rate in picks/min and cycle time |
| **Trust the numbers** | "Uji vs ground truth" line under the chart | the same, plus how late the count follows the robot |

Severity follows what it costs: a short pack that left is **Tinggi** (red), an
empty pick is **Sedang** (amber), a feeder gap is an early warning, **Rendah**
(blue), and a complete pack is **Info** (grey, on the timeline).

## How the vision works

**Can line** (`vision_line.py`). Trays are the cardboard-coloured regions on the
belt. A tray is read only inside a fixed inspection zone in the middle of the
picture, where the camera looks straight down at it; there each of the ten slots
is checked for a lid (a bright, colourless disc; an empty slot shows the brown
tray floor). The slot positions inside the tray box were measured from this clip
(trays whose ten lids are all found by Hough circles). The verdict is the most
common reading over the ~27 frames a tray spends in the zone, given as it leaves.

**Packing station** (`vision_pack.py`). Boxes are the cardboard regions on the
main belt, products are the blue top panels. Calibrated from the clip: where a
box stands while it is filled, the 5 × 4 slot grid inside it (from a box seen
full), and where products stop on the feeder. The robot arm hides part of the
box on every trip, so a slot counts as filled once a product is seen in it on 3
frames running, and stays filled until the box leaves. The robot fills slots in
order: a slot still empty 20 frames after the next one was filled is an empty
pick. A normal cycle leaves the feeder stop empty for about 9 frames; 14 frames
with nothing there while the box still needs products is a feeder gap.

## Results against the ground truth

| | Can line | Packing station |
|---|---|---|
| Packs judged | 7 trays, 7 correct (count and empty slot) | 3 boxes, 3 correct (count and empty slots) |
| Short packs | 3 of 3 found | 1 of 1 found (18/20, slots B2 and C5) |
| Per frame | 181 of 181 in-zone readings right | count follows the truth 4 frames (0,16 s) late, by design (the head must lift first) |
| Root cause | – | 2 of 2 empty picks found; feeder gap raised 12 frames (0,5 s) before each empty pick was released |

The packing column is filled in from `packing_qc_score.json` after the full run.

## Limits

This is a rendered scene, clean and evenly lit, and the colour rules (cardboard,
blue top panel, bright lid) are tuned to it. On a real line the same logic holds
(zone, slot template, latch, order of filling, feeder watch) but the "is there a
product in this slot" test should be a small classifier trained on that line's
own footage. The defect rates are far above any real line (3 short trays in 7)
because the clips have to show the event several times.
