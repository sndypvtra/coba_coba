# 04 — Bottling line: fill-volume inspection

Not counting, and not zero-shot. Product inside the bottle is segmented on
saturation, the liquid surface is located, and the volume beneath it is
integrated over the bottle's bore as a stack of discs.

```bash
python main.py
python main.py --capacity-ml 1000     # a different SKU
python main.py --detect               # overlay YOLOE bottle segmentation
```

| | |
|---|---|
| **Dispensed volume** | **1,001 mL** |
| **Fill, by volume** | **66.7 %** |
| Fill, by height | 74.4 % |
| Nominal capacity | 1,500 mL — configured per SKU, not measured |
| Trajectory | monotonic, worst frame-to-frame step 3.1 %, no backward dip |
| Clip | 232 frames @ 25 fps |

This is the only project that runs **no network at all** by default, and it is
the quickest.

## Files

| | |
|---|---|
| `main.py` | entry point |
| `calibration.py` | every constant tied to this one station — eleven of them |
| `segmentation.py` | product mask and bottle silhouette |
| `profile.py` | bore, surface, isotonic fit, volume integration |
| `panel.py` | the readout panel |
| `pipeline.py` | three passes over the clip |

## What is measured and what is configured

The fill **fraction** is measured. The millilitre figure is that fraction against
a capacity you type in — no video can observe how big a bottle is. Getting this
backwards is the easiest way to report a confident wrong number.

Four decisions worth knowing:

1. **Segment on saturation, not hue.** Product in direct view sits at `S 251–255`;
   the same product seen *through* the glass sits at `S 104–199`. Their hues are
   nearly identical, so hue cannot separate them and saturation can.
2. **Find the surface by width.** The falling stream is a thin column ~3 % of the
   bore; standing liquid spans it. Taking the topmost lit pixel instead tracked
   the nozzle and over-read the fill.
3. **Integrate the bore, not the mask.** Below the surface the bottle is full, so
   glare and machine rods cannot shrink the reading — only the surface position
   matters.
4. **Reference to the thread line.** Capacity runs base → threads, which is what
   a stated fill volume means, not "the fullest this clip happened to get".

## What breaks it

Everything here is calibrated to one camera, one bottle and one product.
`factory_vision/tools/perturbation_test.py` measures the cost of a moved camera,
and the size of the error is not the point — the point is that every reading is
still reported through the same confident panel with no flag saying the
calibration no longer holds. Full table and all eleven constants:
[`../../docs/liquid-level.md`](../../docs/liquid-level.md)
