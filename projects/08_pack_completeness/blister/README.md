# Blister strips with one capsule missing (real footage, edited)

The source is a real factory clip: [Mixkit #4750, "Capsule packing machine in a
factory"](https://mixkit.co/free-stock-video/capsule-packing-machine-in-a-factory-4750/),
1920 × 1080, 25 fps, 6.2 s. Blister strips of ten capsules (2 × 5) index across
a fixed camera. Every pocket in it is full, so the defect is put in afterwards:
one capsule is taken out of three different strips, and each of those strips
then holds 9 of 10.

The clip itself is not in the repository (Mixkit's licence allows use in a
project, not redistribution of the clip); the scripts below rebuild it, and the
truth for the edited clip is `../output/blister_truth.json`.

## How it is done

| Stage | Script | What it does |
|---|---|---|
| 0 | `prepare.py` | One reference frame per still segment (17, 85, 145) and the homographies between them, fitted on many patches with RANSAC because the pocket pattern repeats |
| 1 | `edit_refs.py` | Empties the target pockets on each reference with LaMa inpainting |
| 2 | `propagate.py` | Carries the edit through all 154 frames and writes the truth |

Two details made the edit hold up:

- **LaMa redraws the capsule if it can see one.** The pattern is so regular that
  inpainting a single capsule brings a new capsule back. Every capsule in the
  crop is therefore masked as context, so the model only has foil and pocket
  rims to copy from; only the target pocket is kept from its output.
- **The indexing moves.** On the still frames the edit is added as a delta, so
  the clip's own grain stays on top. During the two moves the edited reference
  is warped along the sheet's path, given the same motion blur, re-aligned to the
  real frame by template matching (the interpolated path lags by up to 23 px),
  and composited. Adding a colour delta there left pink fringes wherever the
  alignment was a few pixels off.

## Targets

One per strip, picked on frame 85 by their green cap:

| Name | Cap at (frame 85) | Visible |
|---|---|---|
| `strip_upper` | (894, 155) | frames 0-126: sharp on 0-34, at the blurred top edge on 44-126, out of frame after the second index |
| `strip_middle` | (809, 612) | whole clip; sharp on frames 44-126 |
| `strip_lower` | (1110, 706) | whole clip; cut by the bottom edge on frames 0-34 |

`targets_reference.json` keeps the pocket geometry found on each reference.

## Run

```bash
pip install torch opencv-python imageio-ffmpeg
curl -L -o mixkit_4750.mp4 https://assets.mixkit.co/videos/4750/4750-1080.mp4
curl -L -o big-lama.pt https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt
python prepare.py   work mixkit_4750.mp4
python edit_refs.py work big-lama.pt
python propagate.py work mixkit_4750.mp4 work/blister_kurang1.mp4
```

## What it is not

The empty pockets are made, not filmed. Seen at full size on a still frame they
pass for an empty pocket, foil and rim included; on the out-of-focus edges of
the frame they are soft grey patches, which is what an empty pocket would be
there too. A detector trained only on this clip learns this one edit, so it is
for showing the counting logic, not for training a model for a real line.
