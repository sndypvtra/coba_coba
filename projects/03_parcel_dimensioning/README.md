# 03 — Parcel unloading belt: count, range and dimension

Counting a parcel is the easy half. The half a depot bills on is *how big it
was*, and a fixed camera cannot answer that from pixels — the same carton covers
four times the area at half the distance.

```bash
python main.py
```

First run downloads two Depth Anything 3 checkpoints (~2.9 GB) alongside the
detector. They are cached afterwards, and the pipeline additionally caches every
depth map it computes in `output/.depth_cache`, so a second run costs a fraction
of the first.

| | |
|---|---|
| **Counted** | **8** crossings, 0 reverse — matching the slit-scan ground truth exactly |
| Dimensioned | 21 parcels, 1,087 L |
| Rejected off the belt | 7,602 detections, on geometry |
| Belt-plane fit | 8.4 mm rms over 34,905 px |
| Speed | 1.25 s/frame detect, plus depth every 5th frame |

## Files

| | |
|---|---|
| `main.py` | entry point — assets, run, the per-parcel table |
| `config.py` | every constant, each with the measurement that set it |
| `input/`, `output/` | clip in, video + `summary.json` + depth cache out |

Shared engine in `factory_vision/counting/`: `pipeline.py` (detect → track →
count → measure → render), `depth.py` (Depth Anything 3 → metres), `sizing.py`
(belt plane, parcel dimensions, the on-belt test), `geometry.py` (the counting
line), `overlay.py` (the operations panel).

## Extra install

Depth Anything 3 must go in **without its dependency list** — its `pyproject`
pins `numpy<2` and pulls `opencv-python`, which would downgrade the stack out
from under every other project:

```bash
pip install --pre "omegaconf>=2.4.0.dev0"
pip install --no-deps addict einops plyfile trimesh
git clone --depth 1 https://github.com/ByteDance-Seed/depth-anything-3
pip install --no-deps -e depth-anything-3
```

Without it, set `measure_size=False` in `config.py` and the project still counts.

## What the size classes mean

- `[M]` — measured; the camera resolved this parcel's top face
- `[M*]` — the footprint came from a calibrated correction, good to about ±10%
- `[M?]` — the longest side sits within that uncertainty of a class boundary

That distinction is the honest core of this project. A parcel's extent *away*
from the camera lives on its top face, and this lens rides 488 mm above a belt
carrying 340 mm cartons — 125 mm above their lids. At 2.25 m a 500 mm top face
spans **17 pixels**, and no algorithm recovers a depth extent from 17 pixels.
The same camera sees a 110 mm bag's top over 38 px and measures it correctly.

Two cartons in the clip print `720x500x340 mm` on the side, which is what every
calibration here is set and checked against:

| | measured | true | class |
|---|:--:|:--:|:--:|
| brown carton | 689 × 465 × 366 | 720 × 500 × 340 | **L\*** |
| white carton | 754 × 543 × 341 | 720 × 500 × 340 | **L\*** |
| flat poly bag | 444 × 427 × 138 | ~420 long | **M** |

Height is the trustworthy dimension — base on a fitted plane, top against open
air. The footprint is not, and the remedy is a second view across the lane, not
a better monocular model.

Full method, every failure found and how: [`../../docs/conveyor-counting.md`](../../docs/conveyor-counting.md)
