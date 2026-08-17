# 02 — Tomato grading line

The same engine as project 01, pointed at a different belt. The only file that
differs is `config.py`.

```bash
python main.py
```

| | |
|---|---|
| **Counted** | **16** line crossings, 0 reverse |
| Tracks | 50 unique IDs |
| Clip | 212 frames, 1920×1080 |
| Speed | ~1.2 s/frame, CPU-only |

## Files

| | |
|---|---|
| `main.py` | entry point — identical to project 01's but for the case number |
| `config.py` | one prompt (`tomato`), a line 9.4° off vertical, and a y-ROI |
| `assets.py` | identical to project 01's but for the clip id |
| `panel.py` | the dashboard — same shape as 01's, different words |
| `report.py` | identical to project 01's, so the two outputs compare line by line |
| `baseline.py` | the last verified count, and the check every run prints |
| `input/`, `output/` | this project's own video in and results out |

## Why this project exists next to project 01

To make the zero-shot claim checkable rather than asserted. Same weights, same
tracker, same counting rule — one word changed and a line moved. If a new belt
needed new code, the claim would be empty.

It is also the one clip where threshold tuning genuinely paid: 0.13 → 0.059 with
opened tracker gates cut the median entry lag from 0.326 to 0.203 and more than
doubled the share of tomatoes acquired within 15% of the frame edge, 21% → 50%.
The same change did almost nothing on the citrus line. Tuning is per-installation,
and the only way to know is to measure it.

The near lane sits outside the depth of field, smears, and breaks identity, so
`roi_y` restricts counting to the in-focus lanes. That is a config decision, not
a code one — which is the point.
