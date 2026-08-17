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
| Belt-plane fit | 8.4 mm rms over 34,903 px |
| Speed | 1.25 s/frame detect, plus depth every 5th frame |

## Files

Six models are in play, and each has a module that owns it.

| | |
|---|---|
| `main.py` | entry point — assets, run, report |
| `config.py` | `CLIP` (counting) and `SIZING` (metric), deliberately apart |
| `assets.py` | the clip, the detector, and the two depth checkpoints (~2.9 GB) |
| `intrinsics.py` | DA3-LARGE's camera decoder, and the square-pixel test |
| `depth.py` | DA3METRIC-LARGE — canonical depth × focal ÷ 300 = metres |
| `depth_cache.py` | float16 maps on disk; the second run is nearly free |
| `belt.py` | the plane heights are measured from, and the on-belt test |
| `sizing.py` | mask + depth + plane → millimetres, and how much to trust them |
| `measurement.py` | the order of operations, and the contract with the counter |
| `panel.py` | the live dashboard — the only project entitled to a size row |
| `report.py` | the read-out: measurement chain, per-parcel table, `*`/`?` |
| `input/`, `output/` | clip in, video + `summary.json` + depth cache out |

### Why the metric half lives here and not in the shared engine

`depth.py` and `sizing.py` used to sit in `factory_vision/counting/`, alongside
the counter shared with projects 01 and 02 — 619 lines that neither of those two
ever executes, in a package named for what the three have in common. `ClipConfig`
carried eleven metric fields for the same reason, so reading project 01 meant
stepping over belt patches and footprint scales that have nothing to do with
oranges.

The measurement now reaches the counter through
`factory_vision/counting/measuring.py`, a protocol the shared pipeline calls
when it is given a backend and skips entirely when it is not. So "project 01
does not measure" is a structural fact — no torch, no DA3, no checkpoints —
rather than a flag that happens to be `False`.

Still shared, because all three genuinely use it: `pipeline.py` (detect → track →
count → render), `geometry.py` (the counting line), and `overlay.py` — which now
knows how to *draw* a panel and nothing about what belongs on one. Each project
builds its own in `panel.py`, so this project's SIZE MIX and VOLUME RATE rows
cannot leak onto a citrus line again.

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

Without it, drop the `backend=` argument from the `run_case` call in `main.py`
and the project still counts — exactly the call projects 01 and 02 make.

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
