"""Render the pack-completeness clip and its per-frame ground truth.

    pip install bpy==4.2.0          # Blender as a Python module, CPU rendering
    python render.py --test         # one frame, to check the look
    python render.py                # all frames, then output/pack_line.mp4

Frames go to output/frames/ and are kept, so an interrupted run resumes where it
stopped. The ground truth lands next to the video as pack_line_truth.json: for
every frame, every tray in view with its image box, how many cans it holds and
which slots are empty.
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
import scene  # noqa: E402

OUT = HERE / "output"
W, H = 1280, 720


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


def tray_box(sc, cam, ob):
    """Image-space box of the tray including the can tops, in pixels."""
    hl, hw = scene.TRAY_L / 2, scene.TRAY_W / 2
    pts = []
    for z in (0.0, max(scene.TRAY_H, scene.CAN_H + 0.004)):
        for x in (-hl, hl):
            for y in (-hw, hw):
                p = world_to_camera_view(sc, cam, ob.matrix_world @ Vector((x, y, z)))
                pts.append((p.x * W, (1 - p.y) * H))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]


def write_truth(trays, cam):
    sc = bpy.context.scene
    frames = []
    for f in range(sc.frame_start, sc.frame_end + 1):
        sc.frame_set(f)
        seen = []
        for t in trays:
            x0, y0, x1, y1 = tray_box(sc, cam, t.obj)
            if x1 < 0 or x0 > W or y1 < 0 or y0 > H:
                continue
            seen.append({"tray": t.idx, "box": [x0, y0, x1, y1],
                         "fully_visible": x0 >= 0 and x1 <= W and y0 >= 0 and y1 <= H,
                         "expected": scene.EXPECTED, "packed": t.packed,
                         "missing_slots": t.missing})
        frames.append({"frame": f, "trays": seen})
    meta = {"fps": scene.FPS, "size": [W, H], "expected_per_tray": scene.EXPECTED,
            "slot_numbering": "slot 0 = leading edge, left row; then across, then back",
            "trays": [{"tray": t.idx, "packed": t.packed, "missing_slots": t.missing}
                      for t in trays],
            "frames": frames}
    (OUT / "pack_line_truth.json").write_text(json.dumps(meta, indent=1))


def encode():
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-v", "error", "-y", "-framerate", str(scene.FPS),
                    "-i", str(OUT / "frames" / "%04d.jpg"), "-c:v", "libx264",
                    "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
                    str(OUT / "pack_line.mp4")], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="render one frame only")
    ap.add_argument("--frame", type=int, default=150)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--no-encode", action="store_true")
    ap.add_argument("--truth-only", action="store_true")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    trays, cam = scene.build()
    setup_render(a.samples)
    sc = bpy.context.scene
    if a.test:
        sc.frame_set(a.frame)
        sc.render.filepath = str(OUT / f"test_{a.frame:04d}.jpg")
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"test frame {a.frame}: {time.time() - t:.1f}s -> {sc.render.filepath}")
        return

    write_truth(trays, cam)
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
        print("video:", OUT / "pack_line.mp4")


if __name__ == "__main__":
    main()
