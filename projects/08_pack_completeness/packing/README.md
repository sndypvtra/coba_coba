# Packing station: boxes of 20, one leaves with 18

A robot puts products into a shipping box one at a time, and the camera above
the station has to say how many are in. Standard is 20 per box (5 × 4). The
scene is built in Blender and rendered from one fixed camera, like the can-tray
line in the parent folder, so every frame comes with its true count.

## What happens in the clip

| Box | When it is at the station | Ends with |
|---|---|---|
| 1 | already holds 14 when the clip opens; the robot adds the last 6 | 20 |
| 2 | arrives empty; the feeder has two gaps (cycles 7 and 15), the robot still makes both trips, and slots 6 and 14 stay empty | **18** |
| 3 | arrives empty, filled to 20 | 20 |

A full box leaves to the right and stays in view at the edge while the next box
is filled, so box 2 with its two holes is still on screen while box 3 fills.

| | |
|---|---|
| Line | main belt carrying boxes, which stops while a box is filled; feeder belt with a stop for the products |
| Robot | Cartesian (x rail behind the line, y arm reaching over the box, z slide with a 4-cup vacuum head), 16 frames = 0.64 s per pick |
| Product | carton 88 × 88 × 70 mm, white with a blue top panel, sits below the box rim |
| Camera | fixed, 1.95 m up and 1.05 m in front of the line, 30 mm lens |
| Clip | 34 s, 1280 × 720, 25 fps (857 frames) |
| Render | Cycles on CPU, 12 samples + OpenImageDenoise, motion blur |

The plan is `PLAN` in `station.py`; nothing in it is random except a few
millimetres of jitter in where each product lands.

## Run

```bash
pip install bpy==4.2.0 imageio-ffmpeg
python render.py --test --frame 300     # one frame to output/test_0300.jpg
python render.py                        # all frames, then output/packing_station.mp4
python render.py --truth-only           # only the truth file
```

Frames go to `output/frames/` and are skipped if already there, so an
interrupted render resumes (`--start` picks the first frame). About 14 s a frame
on a 4-core CPU, so 3+ hours. The rendered clip is kept in the repository as
`output/packing_station.mp4` (2,9 MB).

The analytics run on it is in `../analytics/`: `../output/analytics/packing_qc.mp4`.

## Ground truth

`output/packing_station_truth.json`:

- `boxes`: per box, how many were in at the start, the final count, the empty slots
- `events`: every pick, with the frame the product is released (`placed`) or the
  frame an empty trip ends (`missed`)
- `frames`: for every frame, every box in view

```json
{"frame": 300, "boxes": [
  {"box": 1, "bbox": [499.0, 349.0, 781.0, 563.0], "fully_visible": true,
   "count": 9, "expected": 20, "filled_slots": [0, 1, 2, 3, 4, 5, 7, 8, 9],
   "missed_slots": [6], "slot_centres_px": [[540.7, 381.2], ...]}]}
```

`count` changes on the frame the head lets go of the product. `bbox` is the
box opening and walls in pixels (flaps left out). `slot_centres_px` is the top
centre of each of the 20 slots, so a counter can be checked slot by slot. Slot 0
is back-left, far from the camera; numbering runs left to right, then towards
the camera.

## What to expect from it

It is a clean render, not camera footage: physically based light, materials,
shadows and motion blur, but no dust, print, dents, sensor noise or flicker.
The robot arm passes over the box on every placement and hides one column for
a few frames, as a real one would; a counter has to cope with that, for
instance by counting while the head is back at the feeder. Good for building
and showing the counting logic; a model for a real line still needs footage
from that line.
