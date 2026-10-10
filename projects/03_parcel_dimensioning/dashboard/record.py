"""Run the project exactly as `main.py` does and record, per frame, what it saw.

Nothing in the counting or the measurement is changed. Four places in the shared
pipeline are wrapped so that their results are also written down: the label
annotator (which tracked parcels are drawn, and where), the size lookup (each
parcel's dimensions, and whether they are frozen yet), the counting line (who
crossed), and the HUD (the end of a frame). The dashboard draws from that record.

    python dashboard/record.py        # -> output/record.json
                                      #    first run ~2.5 h (depth), later ~20 min
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import supervision as sv  # noqa: E402

import assets  # noqa: E402
import panel  # noqa: E402
from config import CLIP, SIZING  # noqa: E402
from factory_vision.assets import adopt_mobileclip, place_mobileclip  # noqa: E402
from factory_vision.counting import pipeline as P  # noqa: E402
from factory_vision.counting import run_case  # noqa: E402
from factory_vision.counting.overlay import Hud  # noqa: E402
from factory_vision.paths import WEIGHTS_DIR, project_dirs  # noqa: E402
from measurement import ParcelMeasurement  # noqa: E402

VIDEO_DIR, OUTPUT_DIR = project_dirs(str(ROOT / "main.py"))
frames: list[dict] = []
cur = {"objects": [], "sizes": {}, "crossed": []}


def size_dict(s, locked):
    return {"l_mm": round(s.length_m * 1000), "w_mm": round(s.width_m * 1000), "h_mm": round(s.height_m * 1000),
            "volume_l": round(s.volume_l, 1), "cls": s.class_name, "mark": s.class_mark,
            "distance_m": round(s.distance_m, 2), "locked": locked}


_size_of = P._size_of


def size_of(tid, locked, running, backend):
    s = _size_of(tid, locked, running, backend)
    if s is not None:
        cur["sizes"][int(tid)] = size_dict(s, int(tid) in locked)
    return s


_label = sv.LabelAnnotator.annotate


def label(self, scene, detections, labels=None, **kw):
    cur["objects"] = [{"tid": int(t), "box": [round(float(v), 1) for v in b], "conf": round(float(c), 3)}
                      for t, b, c in zip(detections.tracker_id, detections.xyxy, detections.confidence)]
    return _label(self, scene, detections, labels, **kw)


_trigger = sv.LineZone.trigger


def trigger(self, detections):
    crossed_in, crossed_out = _trigger(self, detections)
    for j, flag in enumerate(crossed_in):
        if flag and detections.tracker_id is not None:
            cur["crossed"].append(int(detections.tracker_id[j]))
    return crossed_in, crossed_out


_draw = Hud.draw


def draw(self, frame, idx, *a, **kw):
    frames.append({"frame": int(idx), "objects": cur["objects"],
                   "sizes": {str(k): v for k, v in cur["sizes"].items()}, "crossed": cur["crossed"]})
    cur["objects"], cur["sizes"], cur["crossed"] = [], {}, []
    return _draw(self, frame, idx, *a, **kw)


def main():
    P._size_of = size_of
    sv.LabelAnnotator.annotate = label
    sv.LineZone.trigger = trigger
    Hud.draw = draw
    if not assets.depth_installed():
        print(assets.DA3_INSTALL)
        return 1
    if not assets.fetch(VIDEO_DIR, WEIGHTS_DIR, with_depth=True):
        return 1
    place_mobileclip(WEIGHTS_DIR, Path.cwd())
    summary = run_case(CLIP, VIDEO_DIR, OUTPUT_DIR, backend=ParcelMeasurement(SIZING, CLIP), panel=panel.build)
    adopt_mobileclip(WEIGHTS_DIR, Path.cwd())
    out = {"video": CLIP.filename, "fps": summary["fps"], "line": summary["line"], "count": summary["count_in"],
           "dimensioning": summary.get("dimensioning", {}), "frames": frames}
    (OUTPUT_DIR / "record.json").write_text(json.dumps(out))
    print("recorded", len(frames), "frames; counted", summary["count_in"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
