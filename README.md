# Conveyor Counting — Zero-Shot Detection + Tracking + Supervision

Counting and classifying objects on conveyor belts **without training a single
class**. Objects are found from plain-English text prompts, given stable IDs by
a multi-object tracker, and counted as they cross a line drawn with
[supervision](https://github.com/roboflow/supervision).

Three Pexels clips are processed end to end: two fruit lines (oranges,
tomatoes) and one parcel belt.

## Stack

| Piece | Choice | Why |
|---|---|---|
| Detector | **YOLOE-11L-seg** (`ultralytics` 8.4.106) | Open-vocabulary. Prompts are embedded with `get_text_pe()` and installed with `set_classes()` — no training, no fixed class list. Returns masks as well as boxes. |
| Tracker | **TrackTrack** (CVPR 2025) + ReID + GMC | Newest tracker shipping in ultralytics. Multi-cue association (HMIoU + appearance + confidence + corner angle), iterative assignment, track-aware initialization. `--tracker botsort` is available as a baseline. |
| Drawing / counting | **supervision 0.29.1** | `LineZone` crossings, plus mask / round-box / label / trace annotators and `VideoSink`. |
| Video I/O + HUD | **OpenCV 5.0.0** | Decode, HUD panel, dashed ROI, encode. |

## Results

Produced by `python src/conveyor_count.py` (CPU-only, 4 cores). Full numbers in
[`output/summary.json`](output/summary.json).

| Output clip | Scene | Prompts | Frames |
|---|---|---|---|
| `01_oranges_production_line__counted.mp4` | Citrus sorting line | `orange`, `round orange fruit` | 286 |
| `02_tomatoes_conveyor__counted.mp4` | Tomato grading line | `tomato` | 212 |
| `03_packages_conveyor__counted.mp4` | Parcel unloading belt | `cardboard box`, `parcel`, `plastic bag` | 511 |

Counts are in [`output/summary.json`](output/summary.json). "Counted" is line
crossings by locked tracks; "unique IDs" is every object the tracker ever held.
They differ a lot on purpose — clip 1's belt moves ~3 px/frame, so in 9.5 s most
detected oranges never reach the line. Crossings measure throughput past a
point, which is what a conveyor counter is for; unique IDs would measure
"how much fruit appeared on screen".

Sources (Pexels, free for commercial use):
[oranges](https://www.pexels.com/video/fruit-on-production-line-10576687/) ·
[tomatoes](https://www.pexels.com/video/tomatoes-on-a-moving-conveyor-belt-8675102/) ·
[parcels](https://www.pexels.com/video/unloading-packages-on-a-conveyor-belt-5370836/)

## Run it

```bash
pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
./scripts/fetch_assets.sh          # weights + the three source clips

python src/conveyor_count.py                       # all three clips
python src/conveyor_count.py --only 02_tomatoes_conveyor.mp4
python src/conveyor_count.py --max-frames 45       # quick smoke test
python src/conveyor_count.py --tracker botsort     # swap the tracker
```

`src/probe_prompts.py` sweeps candidate prompt sets against sampled frames and
reports detections-per-frame and confidence spread — that is how the prompts and
per-clip `conf` values below were chosen rather than guessed.

## How each clip is configured

Every clip is one `ClipConfig` in `src/conveyor_count.py`. Belt direction was
measured with Farneback optical flow rather than eyeballed — all three belts run
**left**, so all three counting lines are vertical.

| Clip | conf | Motion (px/frame) | Line tilt off vertical | ROI |
|---|---|---|---|---|
| oranges | 0.14 | (−3.2, +0.9) | 16.4° | full frame |
| tomatoes | 0.13 | (−14.8, −2.5) | 9.4° | y < 0.70 |
| parcels | 0.22 | (−1.5, +0.1) | 3.0° | x > 0.34 |

### Counting rules

Two rules decide what becomes a count:

**The line is built from the belt, not from the frame axes.** Each clip stores
its measured `motion`, and `build_counting_line()` lays the line perpendicular
to it, then orders the endpoints so travel along `motion` registers as **IN**.
Every clip therefore reports IN only, and `OUT` is asserted to stay 0 — a
non-zero OUT in `summary.json` means that clip's motion vector is wrong. A line
parallel to the travel direction would hardly be crossed at all, which is why
orientation follows the belt.

**An object must be locked before it can count.** `min_track_age = 6`: the
tracker has to hold the same ID for six consecutive frames before that object is
eligible. Locked tracks are drawn with `[L]`. A box that flickers into existence
on top of the line cannot register a crossing — it has to be acquired early,
held, and only then counted as it passes.

The ROI is drawn on the output as a dashed box, so what was and was not counted
is visible rather than implied.

## Notes from getting this working

Four things that were not obvious and are worth keeping:

1. **TrackTrack's defaults reject zero-shot detections.** Stock thresholds are
   `track_high_thresh: 0.6` / `new_track_thresh: 0.7`, but open-vocabulary YOLOE
   scores on this footage run ~0.10–0.65. With defaults almost no track is ever
   created. `src/trackers/tracktrack_zeroshot.yaml` moves the gates down to
   0.22 / 0.28 and documents each change against its stock value.
2. **ReID `model: auto` crashes on YOLOE `*-seg` checkpoints.** The native path
   (`get_obj_feats`) permutes a 4-D feature map, but the segmentation head
   returns a 3-D one → `RuntimeError: permute(sparse_coo)`. Fixed by pointing
   ReID at an explicit backbone (`yolo11n-cls.pt`), which keeps appearance
   re-identification instead of silently dropping it.
3. **Prompt aliases double-count without class-agnostic NMS.** `orange` and
   `round orange fruit` fire on the same fruit with different class ids, so
   class-wise NMS keeps both. `agnostic_nms=True` collapses them, and all
   aliases are then relabelled to one counting class.
4. **Input resolution matters far more than model size here.** At `imgsz=640`
   the fruit is too small; going to `imgsz=1280` roughly doubled mean confidence
   (e.g. oranges 0.17 → 0.33) for ~4× the compute. Measured, not assumed.

## Layout

```
src/conveyor_count.py                  main pipeline
src/probe_prompts.py                   prompt/confidence calibration
src/trackers/tracktrack_zeroshot.yaml  TrackTrack retuned for zero-shot scores
src/trackers/botsort_zeroshot.yaml     BoT-SORT baseline
scripts/fetch_assets.sh                weights + source clips
output/                                rendered .mp4 results + summary.json
```

## Caveats

- Counts are line-crossing counts on short clips (7–17 s); they are not a
  validated ground truth, and no clip here ships with one.
- Encoding is `mp4v` — this sandbox has no ffmpeg/H.264 encoder, so the files
  are MPEG-4 Part 2. Plays in VLC/QuickTime; re-encode if you need H.264.
- CPU-only: ~1.3 s/frame at `imgsz=1280`. On a GPU this is real-time territory.
