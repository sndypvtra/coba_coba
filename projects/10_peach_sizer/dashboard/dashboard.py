"""Peach colour grading on the sizer, as a packhouse manager reads it, 1920 x 1080.

    python dashboard/segment.py          # once: find and follow every peach (~30 min on 4 cores)
    python dashboard/colour.py           # once: red share of every peach in the grading zone
    python dashboard/dashboard.py        # -> output/peach_grading.mp4
    python dashboard/dashboard.py --still 120 244

Buyers of red peaches and nectarines specify how much of the skin must be red
(the blush): the more red, the better the class and the price. Here each peach
is read while it rolls through the grading zone (right of ZONE_X), so it shows
most of its skin, and graded on the median red share of those frames:

* Extra: at least 90 % red, premium packs;
* Class I: 60 to 90 % red, regular packs;
* Class II: below 60 % red, diverted to the local market or processing.

The bounds are an example buyer specification, set before the blind check by
eye in output/peach_audit.json and not changed after it. A peach counts once,
when it crosses the count gate at GATE_X at the end of its lane, with the grade
it has at that moment.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import board as B  # noqa: E402
import ui  # noqa: E402
from ui import AMBER, BG, CYAN, RED, SURFACE_2, TEXT, TEXT_2, TEXT_3, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "peach_sizer.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
GATE_X = 1780                       # count gate across the roller lanes (source px)
LANE_BOUNDS = [391, 477, 567, 673]  # where the five lanes divide on the gate, from the crossing histogram
DUP_FRAMES = 1.5                    # two crossings this close on one lane are one peach seen twice
MIN_READS = 3                       # colour reads before a peach shows a grade
CRIMSON = (190, 18, 60)
ROSE = (251, 113, 133)

# (name, short, lowest red share, colour, where it goes). The reddest peaches are the best class.
GRADES = [
    ("Extra · merah ≥ 90%", "Extra", 0.90, CRIMSON, "kemasan premium / ekspor"),
    ("Kelas I · merah 60–90%", "Kelas I", 0.60, ROSE, "kemasan reguler"),
    ("Kelas II · merah < 60%", "Kelas II", -1.0, AMBER, "pasar lokal / olahan"),
]


def grade(s):
    for k, g in enumerate(GRADES):
        if s >= g[2]:
            return k
    return len(GRADES) - 1


def in_chute(x, y):
    return x < 700 or (y > 600 and x < 1000)


class PeachBoard:
    def __init__(self, tr, colour, n_frames):
        self.tr = tr
        self.fps = tr["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.zone_x = colour["zone_x"]
        self.board = ui.board(B.CARDS)
        self.thumbs = {}
        self.reads = {int(t): r for t, r in colour["reads"].items()}
        self.paths = {}
        for fr in tr["frames"]:
            for o in fr["objects"]:
                self.paths.setdefault(o["tid"], []).append((fr["frame"], o["cx"], o["cy"]))
        self.crossings()
        self.share = {}                         # tid -> red share at the gate
        for f, tid, lane in self.passed:
            r = [s for fr, s in self.reads.get(tid, []) if fr <= f + 1]
            self.share[tid] = float(np.median(r)) if r else None
        self.passed = [p for p in self.passed if self.share[p[1]] is not None]
        self.events = self.make_events()

    def crossings(self):
        """Peaches crossing the count gate at the end of the roller lanes, one count each."""
        lanes = {k: [] for k in range(5)}
        for tid, p in self.paths.items():
            p = sorted(p)
            f = np.array([q[0] for q in p], float)
            x = np.array([q[1] for q in p])
            y = np.array([q[2] for q in p])
            if x.min() < GATE_X < x.max() and not in_chute(x.mean(), y.mean()):
                i = int(np.argmax(x >= GATE_X))
                yy = float(np.interp(GATE_X, x[[i - 1, i]], y[[i - 1, i]]))
                ff = float(np.interp(GATE_X, x[[i - 1, i]], f[[i - 1, i]]))
                if yy >= 310:
                    lanes[int(np.searchsorted(LANE_BOUNDS, yy))].append((ff, tid))
        self.passed, self.dropped = [], 0
        for k, v in lanes.items():
            v.sort()
            last = None
            for ff, tid in v:
                if last is not None and ff - last < DUP_FRAMES:
                    self.dropped += 1
                    continue
                last = ff
                self.passed.append((int(np.ceil(ff)), tid, k))
        self.passed.sort()

    # ---- numbers at a frame ------------------------------------------------
    def cls(self, tid):
        return grade(self.share[tid])

    def done(self, f):
        return [p for p in self.passed if p[0] <= f]

    def live_share(self, tid, f):
        r = [s for fr, s in self.reads.get(tid, []) if fr <= f]
        return float(np.median(r)) if len(r) >= MIN_READS else None

    def obj(self, tid, f):
        for o in self.tr["frames"][f - 1]["objects"]:
            if o["tid"] == tid:
                return o
        return None

    def make_events(self):
        ev = []
        for f, tid, lane in self.passed:
            k = self.cls(tid)
            name, short, _, col, dest = GRADES[k]
            o = self.obj(tid, min(f, self.n)) or self.obj(tid, max(1, f - 1))
            box = [v * K for v in o["box"]] if o else None
            red = f"{num(100 * self.share[tid], 0)}% merah"
            if k == 2:
                ev.append(B.Event(f, (f - 1) / self.fps, "medium", "call_split", f"Persik Kelas II · lajur {lane + 1}",
                                  f"{red} · alihkan ke {dest}", "class2", focus=box))
            else:
                ev.append(B.Event(f, (f - 1) / self.fps, "info", "nutrition", f"Persik {short} · lajur {lane + 1}",
                                  f"{red} · {dest}", "graded", feed=False, focus=box))
        return ev

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        f = i + 1
        img = frame.copy()
        fr = self.tr["frames"][i]
        counted = {tid for pf, tid, _ in self.passed if pf <= f}
        layer = img.copy()
        chips = []
        for o in fr["objects"]:
            if not o["poly"] or o["cx"] < self.zone_x or in_chute(o["cx"], o["cy"]):
                continue
            s = self.share[o["tid"]] if o["tid"] in counted else self.live_share(o["tid"], f)
            pts = (np.array(o["poly"], np.float32) * K).astype(np.int32)
            if s is None:
                cv2.polylines(img, [pts], True, ui.bgr(TEXT_3), 1, cv2.LINE_AA)
                continue
            col = GRADES[grade(s)][3]
            cv2.fillPoly(layer, [pts], ui.bgr(col))
            cv2.polylines(img, [pts], True, ui.bgr(col), 2, cv2.LINE_AA)
            chips.append((o, s))
        cv2.addWeighted(layer, 0.22, img, 0.78, 0, img)
        zx, gx = self.zone_x * K, GATE_X * K
        ui.dashed(img, np.array([[zx, 250 * K], [zx, 1060 * K]]), CYAN, 1, 10, 8)
        ui.dashed(img, np.array([[gx, 300 * K], [gx, 860 * K]]), TEXT, 2, 10, 6)
        c = ui.Canvas(img)
        c.pill((zx + 6, 250 * K), "Zona grading · buah berputar di roller", 11, (255, 255, 255), alpha(CYAN, 0.85),
               "semibold", icon="filter_center_focus", pad=(8, 2), anchor="lb")
        c.pill((gx, 300 * K - 6), "Gerbang hitung", 11, TEXT, alpha(BG, 0.75), "semibold", pad=(7, 2), anchor="mb")
        for o, s in sorted(chips, key=lambda v: -grade(v[1])):
            short = GRADES[grade(s)][1]
            col = GRADES[grade(s)][3]
            x0, y0, x1, y1 = (v * K for v in o["box"])
            B.chip(c, ((x0 + x1) / 2, (y0 + y1) / 2), f"{short} · {num(100 * s, 0)}%", col, None, anchor="mm", size=11)
        B.corner_chips(c, "CAM 01 · Sizer persik, 5 lajur", [f"Tergrade: {len(counted)}", "Rekaman nyata"])
        c.rrect((8, B.VH - 38, 560, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", GRADES[0][3], "Extra ≥ 90%"), ("bar", GRADES[1][3], "Kelas I 60–90%"),
                                   ("bar", GRADES[2][3], "Kelas II < 60%"), ("bar", TEXT_3, "sedang dibaca")], 12)
        return c.bgr()

    # ---- the page ------------------------------------------------------------
    def draw(self, i, frame):
        f = i + 1
        t = i / self.fps
        vid = self.overlay(frame, i)
        for ev in self.events:
            if ev.frame == f and id(ev) not in self.thumbs and ev.focus:
                self.thumbs[id(ev)] = B.crop_16x9(vid, ev.focus)
        img = self.board.copy()
        ui.paste_rounded(img, vid, (B.VX, B.VY), 10)
        done = self.done(f)
        c = ui.Canvas(img)
        c.topbar("Grading · warna persik", "Lini sortir persik · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, done, t)
        self.mix(c, done)
        B.feed(c, self.events, t, self.thumbs)
        self.history(c, done)
        self.red_strip(c, done)
        c.timeline(B.TL, t, self.total, self.events)
        return c.bgr()

    def kpis(self, c, done, t):
        n = len(done)
        rate = n / t * 60 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[0], "nutrition", "Persik tergrade", str(n), "5 lajur roller · di gerbang hitung", RED)
        c.kpi(B.KPI_BOXES[1], "speed", "Laju lini", f"≈ {num(rate, 0)}/menit" if rate else "–",
              f"perkiraan dari {num(t, 1)} s rekaman" if rate else "menunggu buah pertama", CYAN)
        a = sum(1 for _, tid, _ in done if self.cls(tid) == 0)
        c.kpi(B.KPI_BOXES[2], "verified", "Kelas Extra", f"{num(100 * a / n, 0)}%" if n else "–",
              f"{a} dari {n} persik · kemasan premium" if n else "belum ada", CRIMSON)
        y = sum(1 for _, tid, _ in done if self.cls(tid) == 2)
        c.kpi(B.KPI_BOXES[3], "call_split", "Kelas II, dialihkan", str(y),
              f"{num(100 * y / n, 0)}% · jangan masuk kemasan premium" if y else "belum ada", AMBER,
              value_fill=AMBER if y else TEXT)

    def mix(self, c, done):
        y = c.card_title(B.MID, "Komposisi grade", "category", f"{len(done)} persik")
        x0, _, x1, y1 = B.MID
        counts = [sum(1 for _, tid, _ in done if self.cls(tid) == k) for k in range(3)]
        n = max(1, len(done))
        bx0, bx1, by = x0 + 16, x1 - 16, y + 14
        x = bx0
        for k, v in enumerate(counts):
            if v:
                w = (bx1 - bx0) * v / n
                c.rrect((x, by, x + w - 2, by + 18), 4, fill=GRADES[k][3])
                x += w
        if not done:
            c.rrect((bx0, by, bx1, by + 18), 4, fill=SURFACE_2)
        ry = by + 52
        for k, (name, short, lo, col, dest) in enumerate(GRADES):
            c.dot((x0 + 24, ry), 6, col)
            c.text((x0 + 38, ry), name, 14, "semibold", TEXT, anchor="lm")
            c.text((x0 + 38, ry + 22), f"→ {dest}", 12, "regular", TEXT_2, anchor="lm")
            c.text((x1 - 16, ry), f"{counts[k]}", 20, "bold", TEXT, anchor="rm", tnum=True)
            c.text((x1 - 60, ry), f"{num(100 * counts[k] / n, 0)}%" if done else "–", 13, "medium", TEXT_2,
                   anchor="rm", tnum=True)
            ry += 64
        c.text((x0 + 16, y1 - 18), "Grade = bagian kulit berwarna merah, median selama buah berputar di zona grading",
               11, "regular", TEXT_3, anchor="lm")

    def history(self, c, done):
        y = c.card_title(B.BL, "Persik terakhir tergrade", "history", "terbaru di kiri")
        x0, _, x1, y1 = B.BL
        tw, gap = 78, 9
        x = x0 + 16
        for _, tid, lane in list(reversed(done))[:7]:
            name, short, _, col, _ = GRADES[self.cls(tid)]
            c.rrect((x, y + 2, x + tw, y1 - 14), 8, fill=SURFACE_2)
            c.rrect((x, y + 2, x + tw, y + 6), 2, fill=col)
            c.text((x + tw / 2, y + 24), f"Lajur {lane + 1}", 12, "semibold", TEXT, anchor="mm")
            # a ring filled red as far as the skin is red
            cx, cy, r = x + tw / 2, y + 62, 20
            c.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=SURFACE_2, outline=alpha(TEXT_3, 0.6), width=5)
            c.d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * self.share[tid], fill=col, width=5)
            c.text((cx, cy), f"{num(100 * self.share[tid], 0)}%", 11, "semibold", TEXT, anchor="mm", tnum=True)
            c.text((x + tw / 2, y + 100), "merah", 11, "regular", TEXT_2, anchor="mm")
            c.pill((x + tw / 2, y + 124), short, 10, (255, 255, 255), alpha(col, 0.95), "semibold",
                   pad=(6, 2), anchor="mm")
            x += tw + gap
        if not done:
            c.text(((x0 + x1) / 2, (y + y1) / 2), "Menunggu persik pertama di gerbang hitung", 13, "regular", TEXT_3,
                   anchor="mm")

    def red_strip(self, c, done):
        y = c.card_title(B.BR, "Sebaran warna merah persik", "palette", "batas grade di garis putus")
        x0, _, x1, y1 = B.BR
        lo, hi = 0.0, 1.0
        sx0, sx1, sy = x0 + 30, x1 - 30, y + 70

        def X(s):
            return sx0 + (sx1 - sx0) * (min(max(s, lo), hi) - lo) / (hi - lo)
        bounds = [hi, GRADES[0][2], GRADES[1][2], lo]
        for k in range(3):
            a, b = X(bounds[k + 1]), X(bounds[k])
            c.rrect((a, sy - 26, b, sy + 26), 6, fill=alpha(GRADES[k][3], 0.14))
            c.text(((a + b) / 2, sy - 40), GRADES[k][1], 12, "semibold", TEXT_2, anchor="mm")
        for b in (GRADES[0][2], GRADES[1][2]):
            c.d.line((X(b), sy - 30, X(b), sy + 30), fill=alpha(TEXT_3, 0.9), width=1)
            c.text((X(b), sy + 42), f"{int(round(100 * b))}%", 10, "regular", TEXT_3, anchor="mm")
        rng = np.random.default_rng(3)
        for _, tid, _ in done:
            col = GRADES[self.cls(tid)][3]
            yy = sy + rng.uniform(-16, 16)
            xx = X(self.share[tid]) + (rng.uniform(-14, 0) if self.share[tid] > 0.985 else 0)
            c.dot((xx, yy), 5, col)
            c.d.ellipse((xx - 5, yy - 5, xx + 5, yy + 5), outline=ui.SURFACE + (255,), width=2)
        c.text((sx0, sy + 42), "0% merah", 10, "regular", TEXT_3, anchor="lm")
        c.text((sx1, sy + 42), "100%", 10, "regular", TEXT_3, anchor="rm")
        audit = OUT / "peach_audit.json"
        if audit.exists():
            a = json.loads(audit.read_text())
            c.text((x1 - 16, y1 - 16), a["caption"], 11, "regular", TEXT_3, anchor="rm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    tr = json.loads((OUT / "tracks.json").read_text())
    colour = json.loads((OUT / "colour.json").read_text())
    frames, fps = B.read_video(VIDEO)
    pb = PeachBoard(tr, colour, len(frames))
    n = len(pb.passed)
    counts = [sum(1 for _, tid, _ in pb.passed if pb.cls(tid) == k) for k in range(3)]
    summary = {"seconds": round(len(frames) / fps, 2), "graded": n,
               "per_minute": round(n / (len(frames) / fps) * 60), "duplicate_crossings_dropped": pb.dropped,
               "grades": [{"name": g[0], "red_share_from": max(g[2], 0.0), "destination": g[4], "count": counts[k],
                           "share": round(counts[k] / n, 3)} for k, g in enumerate(GRADES)],
               "peaches": [{"tid": tid, "lane": lane + 1, "frame": f, "red_share": round(pb.share[tid], 3),
                            "grade": GRADES[pb.cls(tid)][1]} for f, tid, lane in pb.passed]}
    (OUT / "peach_grading_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "peaches"}, ensure_ascii=False))
    if a.still is not None:
        if a.still:
            B.stills(lambda i: pb.draw(i, frames[i]), len(frames), set(a.still),
                     lambda f: OUT / f"peach_still_{f:04d}.jpg")
        return
    B.encode((pb.draw(i, f) for i, f in enumerate(frames)), OUT / "peach_grading.mp4", fps)
    print("video:", OUT / "peach_grading.mp4")


if __name__ == "__main__":
    main()
