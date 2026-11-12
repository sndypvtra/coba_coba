"""Joins pieces of one camera's recording into one clip: the frames of each piece in order, their detections with the
track IDs of each piece kept apart (piece n adds n * 100000), and the frame where each new piece starts ("cuts"), so
that nothing is carried from one piece to the next. A piece is video:detections:first:end (frames first..end-1).

    python lpr/join.py <out.mp4> <out.json> <piece> [<piece> ...]
"""
import json
import subprocess
import sys

import cv2

out_mp4, out_json, pieces = sys.argv[1], sys.argv[2], sys.argv[3:]
frames, persons, cuts, meta, ff = [], [], [], None, None
for n, piece in enumerate(pieces):
    video, det, a, b = piece.rsplit(":", 3)
    a, b = int(a), int(b)
    D = json.load(open(det))
    if meta is None:
        meta = {"fps": D["fps"], "w": D["w"], "h": D["h"]}
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{D['w']}x{D['h']}",
                               "-r", str(D["fps"]), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "14",
                               "-pix_fmt", "yuv420p", out_mp4], stdin=subprocess.PIPE)
    assert (D["fps"], D["w"], D["h"]) == (meta["fps"], meta["w"], meta["h"]), "pieces differ in size or frame rate"
    if n:
        cuts.append(len(frames))
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    P = D.get("persons") or [None] * len(D["frames"])
    for k in range(a, b):
        ok, fr = cap.read()
        assert ok, f"{video}: no frame {k}"
        ff.stdin.write(fr.tobytes())
        frames.append([dict(v, id=v["id"] + n * 100000) for v in D["frames"][k]])
        persons.append(P[k])
ff.stdin.close(); ff.wait()
json.dump({"video": out_mp4, **meta, "frames": frames, "persons": persons, "cuts": cuts,
           "pieces": [p.rsplit(":", 3)[0].split("/")[-1] + ":" + ":".join(p.rsplit(":", 3)[2:]) for p in pieces]}, open(out_json, "w"))
print(len(frames), "frames, cuts at", cuts)
