# 06 — Warehouse: four cameras, one floor plan, people in 3D

Four fixed cameras watching one warehouse floor. Each sees 2D boxes; the output
is one eagle-eye plan with one identity per person, positioned in metres.

```bash
python fetch_scene.py     # once: the scene, calibration, ground truth (~520 MB)
python main.py
python main.py --max-frames 60      # a quick look
```

| | |
|---|---|
| **Localisation error** | median **0.181 m**, p95 0.519 m |
| **Recall / precision** | 0.9822 / 0.7367 |
| **Identity** | **1.0 global IDs per real person** — no fragmentation |
| On the floor | 4 people, 3 machine identities, 7 pallet loads |
| Floor use | staging aisle 75.0 %, staging area 25.0 % |
| Proximity | 12 near-miss events, 2.1 s total, closest 0.44 m |

The only project whose accuracy is stated against a **ground truth** rather than
argued for: NVIDIA's PhysicalAI-SmartSpaces ships calibration and 3D truth with
the video. The pipeline never reads the truth — it is used at the end, to score.

## Files

| | |
|---|---|
| `main.py` | entry point |
| `fetch_scene.py` | downloads the scene and cuts four 30-second clips |
| `config.py` | the scene: cameras, floor zones, per-class dimensions, clip window |
| `calibration.py` | camera matrix, ground homography, closed-form height solve |
| `bev.py` | the eagle view's world ↔ map transform |
| `lift.py` | a 2D box → a place and a height in metres |
| `fuse.py` | one global identity per person, across cameras |
| `analytics.py` | zones, speed, proximity, ground-truth validation |
| `render.py` | 3D wireframes, eagle view, operations panel |
| `pipeline.py` | four views per frame, fused and drawn |

## How a box becomes a position

One assumption does the work: **the bottom edge of a box is where the object
meets the floor.** Back-project that point through the ground-plane homography
and you have a position in metres. Height then follows in closed form, because a
standing person is a vertical segment and the camera matrix makes `v(h)` a
Möbius function of height — invertible exactly, no search.

The assumption fails in three different ways and each is handled on its own
terms rather than lumped together: a box clipped by the **bottom** of frame has
no visible feet, so the floor point is wrong and the observation goes; a **side**
clip keeps the feet and only shifts the horizontal centre, so it is kept at
reduced weight; a **top** clip loses only the height.

## The bug worth reading about

Every marker sat in the wrong half of the building for several iterations, and
the positions were never wrong — 0.18 m against ground truth throughout. Only
the *picture* was, because the map ↔ world transform had its y axis mirrored.
Mirrored points still land inside the building, so nothing looked broken. It was
caught by projecting the floor plan's own painted bay outlines back into a camera
and watching them miss by half a warehouse.

Full geometry, fusion and cost: [`../../docs/warehouse-spatial.md`](../../docs/warehouse-spatial.md)
