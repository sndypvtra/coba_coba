# factory-vision-poc

Two computer-vision proofs of concept on factory line footage, both built on
[YOLOE](https://docs.ultralytics.com/models/yoloe/) (open-vocabulary, YOLO11
backbone), [supervision](https://github.com/roboflow/supervision) and OpenCV 5.

**Four cases, one repository.** A fill-volume inspection on a bottling line, and
zero-shot object counting on three different conveyors. Both are proofs of
concept: they run end to end on real footage and every figure below is measured,
but each is calibrated to its own clip rather than trained to generalise. The
scope and limits of each are stated in `docs/`.

---

## LiquidLevel-Vision — fill-volume inspection

Measures how much product a filling machine dispenses into a bottle, from video
alone. Liquid inside the bottle is segmented, the surface is located, and the
volume below it is integrated over the bottle's bore.

![LiquidLevel-Vision result](output/preview_liquid_level.jpg)

**Result — final frame of the reference clip:**

| | |
|---|---|
| Dispensed volume | **1,006 mL** |
| Fill, by volume | **67.1 %** |
| Level height | 74.4 % |
| Nominal capacity | 1,500 mL (configured per SKU) |
| Reference datum | bottle base to thread line |
| Clip | 232 frames @ 25 fps, 1920x1080 |
| Trajectory quality | monotonic; worst frame-to-frame step 2.4 % |

Result video: **[`output/07_bottle_filling__liquid.mp4`](output/07_bottle_filling__liquid.mp4)**
· per-frame series in [`output/liquid_level_summary.json`](output/liquid_level_summary.json)
· method and limits in **[`docs/liquid-level.md`](docs/liquid-level.md)**

```bash
python cases/case4_bottle_fill_volume.py                    # this case, end to end
python cases/case4_bottle_fill_volume.py --capacity-ml 1000 # another SKU
python src/liquid_level.py --video clip.mp4 --out-name result.mp4
```

What is **measured** is the fill fraction. The millilitre figure is that fraction
against the nominal capacity configured for the SKU — a video cannot observe a
bottle's size. This is a **calibrated single-station inspection**, not a general
model: it is tied to one camera position, one bottle and one product colour,
which is the normal arrangement for filling-line vision. `docs/liquid-level.md`
shows, with a measured test, what happens when the framing shifts, and lists
every constant that would need recalibrating.

---

## Conveyor Counting — zero-shot object counting

Counts objects crossing a line on a conveyor **without training a single class**.
Objects are found from plain-English text prompts, tracked with TrackTrack
(CVPR 2025), and counted with supervision's `LineZone`.

![Conveyor counting result](output/preview_counting.jpg)

| Output clip | Scene | Prompts | Counted | Frames |
|---|---|---|---|---|
| `01_oranges_production_line__counted.mp4` | Citrus sorting line | `orange`, `round orange fruit` | 5 | 286 |
| `02_tomatoes_conveyor__counted.mp4` | Tomato grading line | `tomato` | 16 | 212 |
| `03_packages_conveyor__counted.mp4` | Parcel unloading belt | `cardboard box`, `parcel`, `plastic bag`, `sports bag` | 7 | 511 |

Full numbers in [`output/summary.json`](output/summary.json) · method, tuning
results and failure modes in **[`docs/conveyor-counting.md`](docs/conveyor-counting.md)**

```bash
python cases/case1_oranges_counting.py     # citrus line
python cases/case2_tomatoes_counting.py    # tomato line
python cases/case3_packages_counting.py    # parcel belt
python src/conveyor_count.py               # all three in one pass
```

---

## Stack

| Piece | Choice |
|---|---|
| Detector | **YOLOE-11L-seg** (`ultralytics` 8.4.106) — open-vocabulary, YOLO11 backbone, text-prompted via `get_text_pe()` / `set_classes()` |
| Tracker | **TrackTrack** (CVPR 2025) + ReID + GMC, with BoT-SORT as a baseline |
| Annotation & counting | **supervision 0.29.1** — `LineZone`, mask/box/label/trace annotators, `VideoSink` |
| Segmentation & I/O | **OpenCV 5.0.0** — HSV segmentation, disc integration, HUD, encode |

## Setup

```bash
pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
./scripts/fetch_assets.sh      # model weights + source clips (both gitignored)
```

Runs CPU-only; the reference machine was 4 cores, about 1.3 s/frame for the
counting pipeline at `imgsz=1280`.

## Running the four cases

Each case has its own entry-point script in `cases/`, runnable on its own:

```bash
python cases/case1_oranges_counting.py       # zero-shot counting, citrus line
python cases/case2_tomatoes_counting.py      # zero-shot counting, tomato line
python cases/case3_packages_counting.py      # zero-shot counting, parcel belt
python cases/case4_bottle_fill_volume.py     # fill-volume inspection
```

Each prints the case's scene, source and configuration, runs it end to end, and
reports its own result. They are thin by design — the three counting cases differ
only in their `ClipConfig`, so the tracking, counting and rendering code lives
once in `src/` rather than being copied into each script and drifting apart on
the next fix.

## Layout

```
cases/case1_oranges_counting.py        case 1 entry point
cases/case2_tomatoes_counting.py       case 2 entry point
cases/case3_packages_counting.py       case 3 entry point
cases/case4_bottle_fill_volume.py      case 4 entry point
src/liquid_level.py                    fill-volume inspection
src/conveyor_count.py                  zero-shot line counting
src/probe_prompts.py                   prompt/confidence calibration sweep
src/tune_thresholds.py                 detection-latency measurement
src/trackers/*.yaml                    trackers retuned for zero-shot scores
scripts/fetch_assets.sh                weights + source clips
docs/liquid-level.md                   fill-volume: method, tuning, limits
docs/conveyor-counting.md              counting: method, tuning, limits
output/                                rendered results, previews, JSON series
```

## Sources

Footage from [Pexels](https://www.pexels.com), free for commercial use:
[bottle filling](https://www.pexels.com/video/empty-bottles-in-a-filling-machine-8720278/) ·
[oranges](https://www.pexels.com/video/fruit-on-production-line-10576687/) ·
[tomatoes](https://www.pexels.com/video/tomatoes-on-a-moving-conveyor-belt-8675102/) ·
[parcels](https://www.pexels.com/video/unloading-packages-on-a-conveyor-belt-5370836/)
