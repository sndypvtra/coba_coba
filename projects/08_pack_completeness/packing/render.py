"""Render the packing-station clip and its per-frame ground truth.

    pip install bpy==4.2.0          # Blender as a Python module, CPU rendering
    python render.py --test         # one frame, to check the look
    python render.py                # all frames, then output/packing_station.mp4

Frames go to output/frames/ and are kept, so an interrupted run resumes where it
stopped. The ground truth lands next to the video as packing_station_truth.json:
for every frame, every box in view with its image box, how many products are in
it by then, which slots are filled, and where each slot is in the image.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import station  # noqa: E402

OUT = HERE / "output"
W, H = 1280, 720
NAME = "packing_station"


def setup_render(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 4
    sc.cycles.adaptive_threshold = 0.04
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 95
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -1.4


def to_px(sc, cam, p):
    q = world_to_camera_view(sc, cam, p)
    return round(q.x * W, 1), round((1 - q.y) * H, 1)


def box_px(sc, cam, ob):
    """Image-space box of the carton opening and walls (flaps left out), in pixels."""
    hx = station.BOX_IN[0] / 2 + station.WALL
    hy = station.BOX_IN[1] / 2 + station.WALL
    pts = [to_px(sc, cam, ob.matrix_world @ Vector((x, y, z)))
           for z in (0.0, station.BOX_H) for x in (-hx, hx) for y in (-hy, hy)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def write_truth(boxes, cycles, cam):
    sc = bpy.context.scene
    frames = []
    for f in range(sc.frame_start, sc.frame_end + 1):
        sc.frame_set(f)
        seen = []
        for b in boxes:
            x0, y0, x1, y1 = box_px(sc, cam, b.obj)
            if x1 < 0 or x0 > W or y1 < 0 or y0 > H:
                continue
            filled = sorted(slot for t, slot in b.placed if t <= f)
            missed = sorted(c["slot"] for c in cycles
                            if c["box"] == b.idx and c["empty"] and c["release"] <= f)
            slots = [to_px(sc, cam, b.obj.matrix_world @ Vector((*station.slot_xy(s), station.ITEM[2])))
                     for s in range(station.EXPECTED)]
            seen.append({"box": b.idx, "bbox": [x0, y0, x1, y1],
                         "fully_visible": x0 >= 0 and x1 <= W and y0 >= 0 and y1 <= H,
                         "count": len(filled), "expected": station.EXPECTED,
                         "filled_slots": filled, "missed_slots": missed,
                         "slot_centres_px": slots})
        frames.append({"frame": f, "boxes": seen})
    events = []
    for c in cycles:
        events.append({"frame": c["release"], "box": c["box"], "slot": c["slot"],
                       "event": "missed" if c["empty"] else "placed"})
    meta = {"fps": station.FPS, "size": [W, H], "expected_per_box": station.EXPECTED,
            "slot_numbering": "slot 0 = back-left (far from camera); left to right, then towards the camera",
            "boxes": [{"box": b.idx, "already_in_at_start": station.PLAN[b.idx]["start"],
                       "final_count": len(b.placed), "empty_slots": b.empty_slots}
                      for b in boxes],
            "events": events, "frames": frames}
    (OUT / f"{NAME}_truth.json").write_text(json.dumps(meta, indent=1))


def encode():
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-v", "error", "-y", "-framerate", str(station.FPS),
                    "-i", str(OUT / "frames" / "%04d.jpg"), "-c:v", "libx264",
                    "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p",
                    str(OUT / f"{NAME}.mp4")], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="render one frame only")
    ap.add_argument("--frame", type=int, default=60)
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--no-encode", action="store_true")
    ap.add_argument("--truth-only", action="store_true")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    boxes, cycles, stations, cam = station.build()
    setup_render(a.samples)
    sc = bpy.context.scene
    if a.test:
        sc.frame_set(a.frame)
        sc.render.filepath = str(OUT / f"test_{a.frame:04d}.jpg")
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"test frame {a.frame}: {time.time() - t:.1f}s -> {sc.render.filepath}")
        return

    write_truth(boxes, cycles, cam)
    if a.truth_only:
        return
    frames = OUT / "frames"
    frames.mkdir(exist_ok=True)
    lo = a.start or sc.frame_start
    hi = a.end or sc.frame_end
    t0 = time.time()
    done = 0
    for f in range(lo, hi + 1):
        path = frames / f"{f:04d}.jpg"
        if path.exists():
            continue
        sc.frame_set(f)
        sc.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        done += 1
        per = (time.time() - t0) / done
        print(f"frame {f}/{hi}  {per:.1f}s/frame", flush=True)
    if not a.no_encode and all((frames / f"{f:04d}.jpg").exists()
                               for f in range(sc.frame_start, sc.frame_end + 1)):
        encode()
        print("video:", OUT / f"{NAME}.mp4")


if __name__ == "__main__":
    main()
