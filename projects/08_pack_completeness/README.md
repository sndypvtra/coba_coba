# Project 08 · Pack completeness (synthetic line)

A box is meant to hold ten cans; now and then one leaves the line holding nine.
No public video shows that event: inspection datasets such as MVTec LOCO AD
and VisA are single still photographs, each one a separate sample, and stock
footage has no short packs in it. So this project builds the line itself, in
Blender, and renders it as a continuous clip from a fixed inspection camera.

Because the scene is built rather than filmed, every frame comes with its
answer: which tray is in view, where it is in the image, how many cans it
holds and which slot is empty. Whatever counting model is later run on the
clip can be scored against that, not against someone's eye.

## What is in the clip

| | |
|---|---|
| Line | belt conveyor, 0.30 m/s, side guide rails |
| Product | open cardboard tray, 2 × 5 beverage cans |
| Camera | fixed, 1.1 m above the belt and slightly in front of it, 30 mm lens |
| Clip | 15 s, 1280 × 720, 30 fps (450 frames) |
| Short trays | 3 of the trays that cross the frame hold 9 cans, the slot chosen at random |
| Render | Cycles on CPU, 12 samples + OpenImageDenoise, motion blur |

The tray order is `LINE` in `scene.py`; the empty slot of a short tray comes from
the seeded RNG (`SEED`), so the same command gives the same clip.

## Run

```bash
pip install bpy==4.2.0 imageio-ffmpeg     # Blender as a Python module; no GPU needed
python render.py --test                   # one frame to output/test_0150.jpg
python render.py                          # all frames, then output/pack_line.mp4
```

Frames are written to `output/frames/` and skipped if already there, so an
interrupted render picks up where it stopped. On a 4-core CPU a frame takes
about 15 s, so the full clip is roughly two hours.

## Ground truth

`output/pack_line_truth.json`, one entry per frame:

```json
{"frame": 120, "trays": [
  {"tray": 4, "box": [262.1, 254.3, 627.9, 433.0], "fully_visible": true,
   "expected": 10, "packed": 10, "missing_slots": []}]}
```

`box` is the tray in pixels, including the can tops. Slot 0 is the leading
edge, left row; numbering runs across the tray, then back.

## How real does it look

It is a clean product render, not camera footage. The geometry, materials and
light are physically based, so cans, cardboard and steel read as what they
are, with shadows and motion blur; but there is no dust, no label print, no
dents, no sensor noise and no flicker from factory lights. That is enough to
build and demonstrate the counting logic. A model meant for a real line still
needs footage from that line before anyone trusts its numbers.

## Second clip: real blister footage, edited

`blister/` takes a real capsule-packing clip (Mixkit #4750) and empties one
pocket in three different strips, so each of those strips holds 9 of 10; the
truth per frame is `output/blister_truth.json`. See `blister/README.md`.

## Third clip: packing station, boxes of 20

`packing/` renders a robot placing products one by one into boxes of 20 from a
fixed camera; the second box leaves with 18 because of two feeder gaps. Truth per
frame (count, filled and missed slots, slot positions) is in
`packing/output/packing_station_truth.json`. See `packing/README.md`.
