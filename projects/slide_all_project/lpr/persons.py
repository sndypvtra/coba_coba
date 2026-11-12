"""Pass 1b: people where a motorcycle was detected. RF-DETR can call a pedestrian carrying goods a motorcycle; the same
model also reports the person in that box, which render2.py uses to drop such tracks. Runs the detector again on every
STEP-th frame that has a motorcycle (pass 1 kept vehicles only) and adds "persons" to the detections file:
persons[k] is a list of [x1, y1, x2, y2, conf] for a frame that was checked, None for one that was not.

    python lpr/persons.py <video> <detections.json> [step]
"""
import json
import sys
import time

import cv2
from open_image_models import create_detector

video, path = sys.argv[1], sys.argv[2]
STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 5
D = json.load(open(path))
want = [k for k, fr in enumerate(D["frames"]) if any(v["cls"] == "motorcycle" for v in fr)][::STEP]
det = create_detector("rf-detr-medium-576-coco", conf_thresh=0.35)
persons = [None] * len(D["frames"])
cap = cv2.VideoCapture(video); t0 = time.time(); k = 0; todo = set(want)
while todo:
    ok, fr = cap.read()
    if not ok:
        break
    if k in todo:
        persons[k] = [[round(float(a), 1) for a in (d.bounding_box.x1, d.bounding_box.y1, d.bounding_box.x2, d.bounding_box.y2)]
                      + [round(float(d.confidence), 3)] for d in det.predict(fr) if d.label == "person"]
        todo.discard(k)
        if len(want) - len(todo) == 1 or (len(want) - len(todo)) % 20 == 0:
            print(f"{len(want) - len(todo)}/{len(want)} {time.time() - t0:.0f}s", flush=True)
    k += 1
D["persons"] = persons
json.dump(D, open(path, "w"))
print("done", len(want), "frames checked")
