# 01 — Citrus sorting line

Count oranges crossing a line, with a detector that was never trained on
oranges. Prompts go in, a number comes out.

```bash
python main.py
```

Everything missing is fetched on first run, with a progress bar: the clip into
`input/`, the weights into the shared `weights/` at the repository root.

| | |
|---|---|
| **Counted** | **5** line crossings, 0 reverse |
| Tracks | 32 unique IDs |
| Detections | 7.7 per frame |
| Clip | 286 frames, 1920×1080 @ 30 fps |
| Speed | ~1.2 s/frame, CPU-only |

## Files

| | |
|---|---|
| `main.py` | entry point — four calls, no logic of its own |
| `config.py` | the prompts, the confidence floor, the counting line, the belt's measured travel |
| `assets.py` | what has to be downloaded before a run |
| `report.py` | the console read-out |
| `input/` | source clip |
| `output/` | rendered video and `summary.json` |

The pipeline itself lives in `factory_vision/counting/`, shared with projects 02
and 03. That is deliberate: those three differ **only** in `config.py`, and
copying the engine into each would be three versions of one tracker drifting
apart on the next fix.

## What this case is really for

`config.py` is the whole project, and the interesting line in it is the
confidence floor. Dropping it from 0.14 to 0.095 lifts detections from 5.9 to
7.0 per frame and pulls the median entry lag from 0.303 to 0.276 — but going
further, to 0.063, nearly doubled the track count while the share of objects
acquired *early* fell. Those extra detections were fragments of fruit already
being tracked, not earlier pickups. The measurement is in
`factory_vision/tools/tune_thresholds.py`; the conclusion is that a lower
threshold is not the same thing as better recall.
