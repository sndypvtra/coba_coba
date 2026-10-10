"""Tomato sorting as a packhouse manager reads it, 1920 x 1080.

    python dashboard/tracks.py               # once: detect, track, count, read colour (~6 min)
    python dashboard/dashboard.py            # -> output/tomato_grading.mp4
    python dashboard/dashboard.py --still 120 212

Counting is the project's own engine, unchanged (see tracks.py). What this adds
is the grade: each tomato's colour as a CIELAB hue angle, read inside its mask
on the frames where it is in focus, and sorted into three ripeness classes by
where it should go next. The thresholds are in GRADES; how well they agree with
a person grading the same fruit by eye is in output/tomato_audit.json.
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
from ui import AMBER, BG, CYAN, GREEN, RED, SLATE, SURFACE_2, TEXT, TEXT_2, TEXT_3, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "02_tomatoes_conveyor.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
MIN_AGE = 3

# Ripeness by hue angle (degrees): ripe red fruit sits lowest. The class decides
# where the fruit goes next, which is what the line is sorting for. The ripe /
# half-ripe boundary was 47 deg before a blind check by eye (13 of 16 agreed);
# 42.5 deg is where that sample splits (see output/tomato_audit.json).
GRADES = [  # (name, upper hue bound, colour, destination)
    ("Matang", 42.5, RED, "pasar lokal · kirim hari ini"),
    ("Setengah matang", 62.0, AMBER, "distributor · perjalanan jauh"),
    ("Mentah", 999.0, GREEN, "ruang pemeraman"),
]


def grade(hue):
    for k, (name, hi, col, dest) in enumerate(GRADES):
        if hue < hi:
            return k
    return len(GRADES) - 1


class TomatoBoard:
    def __init__(self, tr, n_frames):
        self.tr = tr
        self.fps = tr["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.board = ui.board(B.CARDS)
        self.thumbs = {}
        self.line = [[v * K for v in p] for p in tr["line"]]
        self.roi_y = tr["roi_y"][1] * 1080 * K
        # each track's hue: the median over the frames where it is sharpest
        reads = {}
        for fr in tr["frames"]:
            for o in fr["objects"]:
                reads.setdefault(o["tid"], []).append((o["sharp"], o["hue"]))
        self.hue = {}
        for tid, rs in reads.items():
            rs.sort(reverse=True)
            top = rs[:max(3, len(rs) // 2)]
            self.hue[tid] = float(np.median([h for _, h in top]))
        self.counted = {c["tid"]: c["frame"] for c in tr["crossings"]}
        self.order = [c["tid"] for c in tr["crossings"]]
        self.events = self.make_events()

    def cls(self, tid):
        return grade(self.hue.get(tid, 40.0))

    def make_events(self):
        ev = [B.Event(1, 0.0, "info", "visibility", "Lajur depan di luar fokus",
                      "tidak dihitung · hanya lajur yang tajam", "scope", feed=True,
                      focus=[0, self.roi_y, B.VW, B.VH])]
        seen = {0: 0, 1: 0, 2: 0}
        for c in self.tr["crossings"]:
            k = self.cls(c["tid"])
            seen[k] += 1
            box = self.box_at(c["tid"], c["frame"])
            name, _, col, dest = GRADES[k]
            if k == 2:
                ev.append(B.Event(c["frame"], (c["frame"] - 1) / self.fps, "medium", "eco",
                                  f"Tomat mentah · #{c['tid']}", f"hue {num(self.hue[c['tid']], 0)}° · arahkan ke {dest}",
                                  "green", focus=box))
            else:
                ev.append(B.Event(c["frame"], (c["frame"] - 1) / self.fps, "info", "nutrition",
                                  f"{name} · #{c['tid']}", f"hue {num(self.hue[c['tid']], 0)}° · {dest}",
                                  "graded", feed=False, focus=box))
        return ev

    def box_at(self, tid, frame):
        fr = self.tr["frames"][frame - 1]
        for o in fr["objects"]:
            if o["tid"] == tid:
                return [v * K for v in o["box"]]
        return None

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        img = frame.copy()
        fr = self.tr["frames"][i]
        f = i + 1
        (ax, ay), (bx, by) = self.line
        ui.dashed(img, np.array([[0, self.roi_y], [B.VW, self.roi_y]]), SLATE, 1, 10, 8)
        cv2.line(img, (int(ax), int(ay)), (int(bx), int(by)), ui.bgr(CYAN), 2, cv2.LINE_AA)
        for o in fr["objects"]:
            if o["age"] < MIN_AGE:
                continue
            k = self.cls(o["tid"])
            col = GRADES[k][2]
            done = o["tid"] in self.counted and self.counted[o["tid"]] <= f
            ui.lock_box(img, [v * K for v in o["box"]], col, 2, fill=0.10 if done else 0.0)
        c = ui.Canvas(img)
        top = min(ay, by)
        c.pill(((ax + bx) / 2, top - 6), "Garis hitung", 11, (255, 255, 255), alpha(CYAN, 0.85), "semibold",
               icon="filter_center_focus", pad=(7, 2), anchor="mb")
        c.pill((12, self.roi_y + 8), "Lajur depan di luar fokus · tidak dihitung", 11, TEXT, alpha(BG, 0.75), "medium",
               icon="visibility", pad=(8, 3), anchor="la")
        # the less ripe on top: a green tomato is the one the line has to act on
        for o in sorted(fr["objects"], key=lambda o: self.cls(o["tid"])):
            if o["age"] < MIN_AGE:
                continue
            k = self.cls(o["tid"])
            name, _, col, _ = GRADES[k]
            x0, y0 = o["box"][0] * K, o["box"][1] * K
            done = o["tid"] in self.counted and self.counted[o["tid"]] <= f
            if done:                        # graded boxes say it in colour; the counted ones also in words
                B.chip(c, (max(6, x0), y0 - 4), f"#{o['tid']} · {name} ✓", col, None, anchor="lb", size=11)
        n = sum(1 for t, fr_ in self.counted.items() if fr_ <= f)
        B.corner_chips(c, "CAM 01 · Lini sortir tomat", [f"Terhitung: {n}", "Rekaman nyata"])
        c.rrect((8, B.VH - 38, 470, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", GRADES[0][2], "matang"), ("bar", GRADES[1][2], "setengah matang"),
                                   ("bar", GRADES[2][2], "mentah"), ("dot", TEXT, "✓ terhitung")], 12)
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
        done = [tid for tid in self.order if self.counted[tid] <= f]
        c = ui.Canvas(img)
        c.topbar("Grading · kematangan tomat", "Lini sortir tomat · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, done, t)
        self.mix(c, done)
        B.feed(c, self.events, t, self.thumbs)
        self.history(c, done)
        self.hue_strip(c, done)
        c.timeline(B.TL, t, self.total, [e for e in self.events if e.t <= self.total])
        return c.bgr()

    def kpis(self, c, done, t):
        n = len(done)
        c.kpi(B.KPI_BOXES[0], "nutrition", "Tomat terhitung", str(n), "lewat garis hitung · lajur yang tajam", RED)
        rate = n / t * 3600 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[1], "speed", "Laju lini", f"{num(rate, 0)}/jam" if rate else "–",
              f"perkiraan dari {num(t, 1)} s rekaman" if rate else "menunggu tomat pertama", CYAN)
        ripe = sum(1 for tid in done if self.cls(tid) == 0)
        c.kpi(B.KPI_BOXES[2], "check_circle", "Siap jual (matang)", f"{num(100 * ripe / n, 0)}%" if n else "–",
              f"{ripe} dari {n} tomat" if n else "belum ada yang terhitung", GREEN)
        green = sum(1 for tid in done if self.cls(tid) == 2)
        c.kpi(B.KPI_BOXES[3], "eco", "Perlu pemeraman", str(green),
              "tomat mentah · pisahkan dari lini kirim" if green else "belum ada tomat mentah", AMBER,
              value_fill=AMBER if green else TEXT)

    def mix(self, c, done):
        y = c.card_title(B.MID, "Komposisi kematangan", "category", f"{len(done)} tomat")
        x0, _, x1, y1 = B.MID
        counts = [sum(1 for tid in done if self.cls(tid) == k) for k in range(3)]
        n = max(1, len(done))
        # one stacked bar, then a row per class with where it goes
        bx0, bx1, by = x0 + 16, x1 - 16, y + 14
        x = bx0
        for k, v in enumerate(counts):
            if not v:
                continue
            w = (bx1 - bx0) * v / n
            c.rrect((x, by, x + w - 2, by + 18), 4, fill=GRADES[k][2])
            x += w
        if not done:
            c.rrect((bx0, by, bx1, by + 18), 4, fill=SURFACE_2)
        ry = by + 52
        for k, (name, hi, col, dest) in enumerate(GRADES):
            c.dot((x0 + 24, ry), 6, col)
            c.text((x0 + 38, ry), name, 14, "semibold", TEXT, anchor="lm")
            c.text((x0 + 38, ry + 22), f"→ {dest}", 12, "regular", TEXT_2, anchor="lm")
            c.text((x1 - 16, ry), f"{counts[k]}", 20, "bold", TEXT, anchor="rm", tnum=True)
            c.text((x1 - 60, ry), f"{num(100 * counts[k] / n, 0)}%" if done else "–", 13, "medium", TEXT_2,
                   anchor="rm", tnum=True)
            ry += 64
        c.text((x0 + 16, y1 - 18), "Kelas dari sudut hue warna kulit (CIELAB), dibaca saat buah tajam di kamera",
               11, "regular", TEXT_3, anchor="lm")

    def history(self, c, done):
        y = c.card_title(B.BL, "Tomat terakhir terhitung", "history", "terbaru di kiri")
        x0, _, x1, y1 = B.BL
        tw, gap = 78, 9
        x = x0 + 16
        for tid in list(reversed(done))[:7]:
            k = self.cls(tid)
            name, _, col, _ = GRADES[k]
            c.rrect((x, y + 2, x + tw, y1 - 14), 8, fill=SURFACE_2)
            c.rrect((x, y + 2, x + tw, y + 6), 2, fill=col)
            c.text((x + tw / 2, y + 24), f"#{tid}", 13, "semibold", TEXT, anchor="mm")
            c.dot((x + tw / 2, y + 62), 20, col)
            c.text((x + tw / 2, y + 100), f"{num(self.hue[tid], 0)}°", 13, "medium", TEXT_2, anchor="mm", tnum=True)
            c.pill((x + tw / 2, y + 124), name.split()[0].lower(), 10, (255, 255, 255), alpha(col, 0.9), "semibold",
                   pad=(6, 2), anchor="mm")
            x += tw + gap
        if not done:
            c.text(((x0 + x1) / 2, (y + y1) / 2), "Menunggu tomat pertama melewati garis", 13, "regular", TEXT_3,
                   anchor="mm")

    def hue_strip(self, c, done):
        y = c.card_title(B.BR, "Sebaran warna tomat terhitung", "palette", "ambang kelas di garis putus")
        x0, _, x1, y1 = B.BR
        lo, hi = 25.0, 85.0
        sx0, sx1, sy = x0 + 30, x1 - 30, y + 70

        def X(h):
            return sx0 + (sx1 - sx0) * (min(max(h, lo), hi) - lo) / (hi - lo)
        prev = lo
        for k, (name, ub, col, _) in enumerate(GRADES):
            ub_ = min(ub, hi)
            c.rrect((X(prev), sy - 26, X(ub_), sy + 26), 6, fill=alpha(col, 0.12))
            c.text(((X(prev) + X(ub_)) / 2, sy - 40), name, 12, "semibold", TEXT_2, anchor="mm")
            prev = ub_
        for ub in (GRADES[0][1], GRADES[1][1]):
            c.d.line((X(ub), sy - 30, X(ub), sy + 30), fill=alpha(TEXT_3, 0.9), width=1)
            c.text((X(ub), sy + 42), f"{num(ub, 1).replace(',0', '')}°", 10, "regular", TEXT_3, anchor="mm")
        rng = np.random.default_rng(3)
        for tid in done:
            col = GRADES[self.cls(tid)][2]
            yy = sy + rng.uniform(-16, 16)
            c.dot((X(self.hue[tid]), yy), 6, col)
            c.d.ellipse((X(self.hue[tid]) - 6, yy - 6, X(self.hue[tid]) + 6, yy + 6), outline=ui.SURFACE + (255,),
                        width=2)
        c.text((sx0, sy + 42), f"{int(lo)}° merah", 10, "regular", TEXT_3, anchor="lm")
        c.text((sx1, sy + 42), f"{int(hi)}° hijau", 10, "regular", TEXT_3, anchor="rm")
        audit = OUT / "tomato_audit.json"
        if audit.exists():
            a = json.loads(audit.read_text())
            c.text((x1 - 16, y1 - 16), f"Uji buta vs mata: {a['agree_preset']}/{a['n']} sebelum kalibrasi · "
                   f"{a['agree']}/{a['n']} sesudah (sampel sama)", 11, "regular", TEXT_3, anchor="rm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    tr = json.loads((OUT / "tracks.json").read_text())
    frames, fps = B.read_video(VIDEO)
    tb = TomatoBoard(tr, len(frames))
    summary = {"counted": len(tb.order), "frames": len(frames), "fps": fps,
               "grades": [{"name": g[0], "hue_below": g[1], "destination": g[3]} for g in GRADES],
               "tomatoes": [{"tid": tid, "frame": tb.counted[tid], "hue": round(tb.hue[tid], 1),
                             "grade": GRADES[tb.cls(tid)][0]} for tid in tb.order]}
    (OUT / "tomato_grading_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "tomatoes"}, ensure_ascii=False))
    for t in summary["tomatoes"]:
        print(t)
    if a.still is not None:
        if a.still:
            B.stills(lambda i: tb.draw(i, frames[i]), len(frames), set(a.still),
                     lambda f: OUT / f"tomato_still_{f:04d}.jpg")
        return
    B.encode((tb.draw(i, f) for i, f in enumerate(frames)), OUT / "tomato_grading.mp4", fps)
    print("video:", OUT / "tomato_grading.mp4")


if __name__ == "__main__":
    main()
