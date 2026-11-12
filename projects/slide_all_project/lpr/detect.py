"""Pass 1: vehicles (RF-DETR, COCO), tracks (ByteTrack), plates inside each vehicle (YOLOv9 plate detector) and
plate reads (fast-plate-ocr, global model) for every frame of the video. Writes detections.json."""
import json, sys, time
import cv2, numpy as np
from track import Tracker
from open_image_models import create_detector, LicensePlateDetector
from fast_plate_ocr import LicensePlateRecognizer

video, out = sys.argv[1], sys.argv[2]
VEH = {"car": "car", "motorcycle": "motorcycle", "bus": "bus", "truck": "truck"}
det = create_detector("rf-detr-medium-576-coco", conf_thresh=0.35)
pdet = LicensePlateDetector(detection_model="yolo-v9-s-608-license-plate-end2end", conf_thresh=0.3)
ocr = LicensePlateRecognizer("cct-s-v2-global-model")
cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS); W = int(cap.get(3)); H = int(cap.get(4)); N = int(cap.get(7))
tracker = Tracker(high=0.5, low=0.35, match=0.25, lost=45, start=3)
frames = []; t0 = time.time(); k = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    res = det.predict(fr)
    boxes, confs, cls = [], [], []
    for d in res:
        name = d.label if hasattr(d, "label") else str(d.class_id)
        if name not in VEH: continue
        b = d.bounding_box
        boxes.append([b.x1, b.y1, b.x2, b.y2]); confs.append(d.confidence); cls.append(list(VEH).index(name))
    tr = tracker.update(boxes, confs, cls)
    rec = []
    for tid, (x1, y1, x2, y2), c, ci in tr:
        v = {"id": int(tid), "cls": list(VEH)[int(ci)], "conf": round(float(c), 3), "box": [round(float(a), 1) for a in (x1, y1, x2, y2)]}
        bw, bh = x2 - x1, y2 - y1
        if bw >= 90 and bh >= 90:
            ex = 0.06
            cx1, cy1 = int(max(0, x1 - ex * bw)), int(max(0, y1 - ex * bh)); cx2, cy2 = int(min(W, x2 + ex * bw)), int(min(H, y2 + ex * bh))
            crop = fr[cy1:cy2, cx1:cx2]
            best = None
            for p in pdet.predict(crop):
                pb = p.bounding_box; px1, py1, px2, py2 = pb.x1 + cx1, pb.y1 + cy1, pb.x2 + cx1, pb.y2 + cy1
                pcx, pcy = (px1 + px2) / 2, (py1 + py2) / 2
                if not (x1 <= pcx <= x2 and y1 + 0.25 * bh <= pcy <= y2): continue
                if best is None or p.confidence > best[0]: best = (p.confidence, px1, py1, px2, py2)
            if best:
                pc, px1, py1, px2, py2 = best
                pcrop = fr[int(max(0, py1)):int(py2), int(max(0, px1)):int(px2)]
                if pcrop.size:
                    r = ocr.run(cv2.cvtColor(pcrop, cv2.COLOR_BGR2RGB), return_confidence=True)[0]
                    probs = [round(float(x), 3) for x in (r.char_probs if r.char_probs is not None else [])]
                    v["plate"] = {"box": [round(float(a), 1) for a in (px1, py1, px2, py2)], "conf": round(float(pc), 3),
                                  "text": r.plate, "probs": probs, "region": r.region,
                                  "region_prob": None if r.region_prob is None else round(float(r.region_prob), 3)}
        rec.append(v)
    frames.append(rec); k += 1
    if k % 30 == 0: print(f"{k}/{N} {time.time() - t0:.0f}s", flush=True)
json.dump({"video": video, "fps": fps, "w": W, "h": H, "frames": frames}, open(out, "w"))
print("done", k, f"{time.time() - t0:.0f}s")
