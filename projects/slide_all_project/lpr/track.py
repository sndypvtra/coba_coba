"""A small two-stage IoU tracker in the spirit of ByteTrack: boxes move at their last velocity, confident
detections are matched first, weak ones then keep existing tracks alive; a track ends after `lost` frames unseen."""
import numpy as np
from scipy.optimize import linear_sum_assignment


def iou(a, b):
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (aa[:, None] + bb[None, :] - inter + 1e-9)


class Tracker:
    def __init__(self, high=0.5, low=0.25, match=0.25, lost=45, start=3):
        self.high, self.low, self.match, self.lost, self.start = high, low, match, lost, start
        self.tracks = []; self.next = 1

    def _assign(self, tracks, boxes):
        if not tracks or not len(boxes): return [], list(range(len(tracks))), list(range(len(boxes)))
        pred = np.array([t["box"] + t["vel"] for t in tracks])
        m = iou(pred, boxes); r, c = linear_sum_assignment(-m)
        pairs = [(i, j) for i, j in zip(r, c) if m[i, j] >= self.match]
        ti = {i for i, _ in pairs}; dj = {j for _, j in pairs}
        return pairs, [i for i in range(len(tracks)) if i not in ti], [j for j in range(len(boxes)) if j not in dj]

    def update(self, boxes, confs, classes):
        boxes = np.asarray(boxes, float).reshape(-1, 4); confs = np.asarray(confs, float); classes = list(classes)
        hi = [k for k in range(len(boxes)) if confs[k] >= self.high]; lo = [k for k in range(len(boxes)) if self.low <= confs[k] < self.high]
        for t in self.tracks: t["seen"] = False
        pairs, left, unhi = self._assign(self.tracks, boxes[hi])
        for i, j in pairs: self._hit(self.tracks[i], boxes[hi[j]], confs[hi[j]], classes[hi[j]])
        rest = [self.tracks[i] for i in left]
        pairs2, _, _ = self._assign(rest, boxes[lo])
        for i, j in pairs2: self._hit(rest[i], boxes[lo[j]], confs[lo[j]], classes[lo[j]])
        for j in unhi:
            k = hi[j]
            self.tracks.append({"id": None, "box": boxes[k].copy(), "vel": np.zeros(4), "hits": 1, "miss": 0, "seen": True,
                                "conf": confs[k], "votes": {classes[k]: confs[k]}})
        out = []
        for t in self.tracks:
            if not t["seen"]:
                t["miss"] += 1; t["box"] = t["box"] + t["vel"]; t["vel"] *= 0.9
        self.tracks = [t for t in self.tracks if t["miss"] <= self.lost and (t["id"] is not None or t["miss"] == 0)]
        for t in self.tracks:
            if t["id"] is None and t["hits"] >= self.start: t["id"] = self.next; self.next += 1
            if t["seen"] and t["id"] is not None:
                out.append((t["id"], t["box"].copy(), t["conf"], max(t["votes"], key=t["votes"].get)))
        return out

    def _hit(self, t, box, conf, cls):
        v = box - t["box"]; t["vel"] = 0.6 * t["vel"] + 0.4 * v if t["hits"] > 1 else v
        t["box"] = box.copy(); t["hits"] += 1; t["miss"] = 0; t["seen"] = True; t["conf"] = conf
        t["votes"][cls] = t["votes"].get(cls, 0) + conf
