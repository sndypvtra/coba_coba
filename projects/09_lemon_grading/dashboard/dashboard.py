"""Lemon colour grading at the washer, as a packhouse manager reads it, 1920 x 1080.

    python prepare.py                    # once: the inspection clip
    python dashboard/segment.py          # once: find, follow and read every lemon (~15 min)
    python dashboard/dashboard.py        # -> output/lemon_grading.mp4
    python dashboard/dashboard.py --still 150 306

A lemon counts as inspected once it has been followed for MIN_FRAMES frames in
the inspection zone; its grade is the median hue angle over the frames where it
was sharpest. The grade decides where it goes, which is what a packhouse sorts
for: green fruit to the premium market, green-yellow to the local market,
yellow to processing. The bounds are in GRADES; how well they agree with grading
by eye is in output/lemon_audit.json.
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
from ui import AMBER, BG, CYAN, GREEN, SLATE, SURFACE_2, TEXT, TEXT_2, TEXT_3, YELLOW, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "lemon_wash.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
MIN_FRAMES = 8
LIME = (132, 204, 22)

# (name, short, lower hue bound in degrees, colour, where it goes). Green fruit has the highest hue angle.
GRADES = [
    ("Grade A · hijau", "A", 106.0, GREEN, "ekspor / supermarket"),
    ("Grade B · hijau kekuningan", "B", 97.0, LIME, "pasar lokal"),
    ("Grade C · kuning", "C", -999.0, YELLOW, "olahan: jus, sirup"),
]


def grade(h):
    for k, g in enumerate(GRADES):
        if h >= g[2]:
            return k
    return len(GRADES) - 1


class LemonBoard:
    def __init__(self, tr, n_frames):
        self.tr = tr
        self.fps = tr["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.board = ui.board(B.CARDS)
        self.thumbs = {}
        self.zone_y = tr["zone_y"] * 1080 * K
        seen, reads = {}, {}
        self.inspected = {}                     # tid -> frame it reached MIN_FRAMES
        for fr in tr["frames"]:
            for o in fr["objects"]:
                seen[o["tid"]] = seen.get(o["tid"], 0) + 1
                reads.setdefault(o["tid"], []).append((o["sharp"], o["hue"]))
                if seen[o["tid"]] == MIN_FRAMES:
                    self.inspected[o["tid"]] = fr["frame"]
        self.hue = {}
        for tid, rs in reads.items():
            rs.sort(reverse=True)
            top = rs[:max(3, len(rs) // 2)]
            self.hue[tid] = float(np.median([h for _, h in top]))
        self.order = sorted(self.inspected, key=self.inspected.get)
        self.events = self.make_events()

    def cls(self, tid):
        return grade(self.hue.get(tid, 110.0))

    def obj(self, tid, f):
        for o in self.tr["frames"][f - 1]["objects"]:
            if o["tid"] == tid:
                return o
        return None

    def make_events(self):
        ev = []
        for tid in self.order:
            f = self.inspected[tid]
            k = self.cls(tid)
            name, short, _, col, dest = GRADES[k]
            o = self.obj(tid, f)
            box = [v * K for v in o["box"]] if o else None
            if k == 2:
                ev.append(B.Event(f, (f - 1) / self.fps, "medium", "label", f"Lemon kuning · #{tid}",
                                  f"hue {num(self.hue[tid], 0)}° · alihkan ke {dest}", "yellow", focus=box))
            else:
                ev.append(B.Event(f, (f - 1) / self.fps, "info", "nutrition", f"Lemon #{tid} · grade {short}",
                                  f"hue {num(self.hue[tid], 0)}° · {dest}", "graded", feed=False, focus=box))
        return ev

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        f = i + 1
        img = frame.copy()
        fr = self.tr["frames"][i]
        ui.dashed(img, np.array([[0, self.zone_y], [B.VW, self.zone_y]]), CYAN, 1, 10, 8)
        layer = img.copy()
        for o in fr["objects"]:
            if not o["poly"]:
                continue
            col = GRADES[self.cls(o["tid"])][3]
            done = o["tid"] in self.inspected and self.inspected[o["tid"]] <= f
            pts = (np.array(o["poly"], np.float32) * K).astype(np.int32)
            if done:
                cv2.fillPoly(layer, [pts], ui.bgr(col))
            cv2.polylines(img, [pts], True, ui.bgr(col), 2 if done else 1, cv2.LINE_AA)
        cv2.addWeighted(layer, 0.18, img, 0.82, 0, img)
        c = ui.Canvas(img)
        c.pill((B.VW / 2, self.zone_y - 6), "Zona inspeksi · baris depan yang tajam", 11, (255, 255, 255),
               alpha(CYAN, 0.85), "semibold", icon="filter_center_focus", pad=(8, 2), anchor="mb")
        for o in sorted(fr["objects"], key=lambda o: -self.cls(o["tid"])):
            done = o["tid"] in self.inspected and self.inspected[o["tid"]] <= f
            if not done:
                continue
            name, short, _, col, _ = GRADES[self.cls(o["tid"])]
            x0, y0, x1, y1 = (v * K for v in o["box"])
            B.chip(c, ((x0 + x1) / 2, (y0 + y1) / 2), f"#{o['tid']} · {short}", col, None, anchor="mm", size=12)
        n = sum(1 for fr_ in self.inspected.values() if fr_ <= f)
        B.corner_chips(c, "CAM 01 · Mesin cuci lemon", [f"Terinspeksi: {n}", "Rekaman nyata · distabilkan"])
        c.rrect((8, B.VH - 38, 520, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", GRADES[0][3], "A · hijau"), ("bar", GRADES[1][3], "B · hijau kekuningan"),
                                   ("bar", GRADES[2][3], "C · kuning")], 12)
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
        done = [tid for tid in self.order if self.inspected[tid] <= f]
        c = ui.Canvas(img)
        c.topbar("Grading · warna lemon", "Mesin cuci lemon · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, done, t)
        self.mix(c, done)
        B.feed(c, self.events, t, self.thumbs)
        self.history(c, done)
        self.hue_strip(c, done)
        c.timeline(B.TL, t, self.total, self.events)
        return c.bgr()

    def kpis(self, c, done, t):
        n = len(done)
        c.kpi(B.KPI_BOXES[0], "nutrition", "Lemon terinspeksi", str(n), "baris depan, tiap buah sekali", LIME)
        rate = n / t * 3600 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[1], "speed", "Laju inspeksi", f"{num(rate, 0)}/jam" if rate else "–",
              f"perkiraan dari {num(t, 1)} s rekaman" if rate else "menunggu lemon pertama", CYAN)
        a = sum(1 for tid in done if self.cls(tid) == 0)
        c.kpi(B.KPI_BOXES[2], "check_circle", "Grade A (hijau)", f"{num(100 * a / n, 0)}%" if n else "–",
              f"{a} dari {n} lemon · ekspor / supermarket" if n else "belum ada", GREEN)
        y = sum(1 for tid in done if self.cls(tid) == 2)
        c.kpi(B.KPI_BOXES[3], "label", "Kuning, dialihkan", str(y),
              "ke olahan · jangan masuk kemasan premium" if y else "belum ada lemon kuning", AMBER,
              value_fill=AMBER if y else TEXT)

    def mix(self, c, done):
        y = c.card_title(B.MID, "Komposisi grade", "category", f"{len(done)} lemon")
        x0, _, x1, y1 = B.MID
        counts = [sum(1 for tid in done if self.cls(tid) == k) for k in range(3)]
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
        c.text((x0 + 16, y1 - 18), "Grade dari sudut hue warna kulit (CIELAB), dibaca saat buah paling tajam", 11,
               "regular", TEXT_3, anchor="lm")

    def history(self, c, done):
        y = c.card_title(B.BL, "Lemon terakhir terinspeksi", "history", "terbaru di kiri")
        x0, _, x1, y1 = B.BL
        tw, gap = 78, 9
        x = x0 + 16
        for tid in list(reversed(done))[:7]:
            name, short, _, col, _ = GRADES[self.cls(tid)]
            c.rrect((x, y + 2, x + tw, y1 - 14), 8, fill=SURFACE_2)
            c.rrect((x, y + 2, x + tw, y + 6), 2, fill=col)
            c.text((x + tw / 2, y + 24), f"#{tid}", 13, "semibold", TEXT, anchor="mm")
            c.dot((x + tw / 2, y + 62), 20, col)
            c.text((x + tw / 2, y + 100), f"{num(self.hue[tid], 0)}°", 13, "medium", TEXT_2, anchor="mm", tnum=True)
            c.pill((x + tw / 2, y + 124), f"grade {short}", 10, (20, 24, 30), alpha(col, 0.95), "semibold",
                   pad=(6, 2), anchor="mm")
            x += tw + gap
        if not done:
            c.text(((x0 + x1) / 2, (y + y1) / 2), "Menunggu lemon pertama di zona inspeksi", 13, "regular", TEXT_3,
                   anchor="mm")

    def hue_strip(self, c, done):
        y = c.card_title(B.BR, "Sebaran warna lemon terinspeksi", "palette", "batas grade di garis putus")
        x0, _, x1, y1 = B.BR
        lo, hi = 80.0, 125.0
        sx0, sx1, sy = x0 + 30, x1 - 30, y + 70

        def X(h):
            return sx0 + (sx1 - sx0) * (min(max(h, lo), hi) - lo) / (hi - lo)
        bounds = [hi, GRADES[0][2], GRADES[1][2], lo]
        for k in range(3):
            a, b = X(bounds[k + 1]), X(bounds[k])
            c.rrect((a, sy - 26, b, sy + 26), 6, fill=alpha(GRADES[k][3], 0.12))
            c.text(((a + b) / 2, sy - 40), f"Grade {GRADES[k][1]}", 12, "semibold", TEXT_2, anchor="mm")
        for b in (GRADES[0][2], GRADES[1][2]):
            c.d.line((X(b), sy - 30, X(b), sy + 30), fill=alpha(TEXT_3, 0.9), width=1)
            c.text((X(b), sy + 42), f"{num(b, 1).replace(',0', '')}°", 10, "regular", TEXT_3, anchor="mm")
        rng = np.random.default_rng(3)
        for tid in done:
            col = GRADES[self.cls(tid)][3]
            yy = sy + rng.uniform(-16, 16)
            xx = X(self.hue[tid])
            c.dot((xx, yy), 6, col)
            c.d.ellipse((xx - 6, yy - 6, xx + 6, yy + 6), outline=ui.SURFACE + (255,), width=2)
        c.text((sx0, sy + 42), f"{int(lo)}° kuning", 10, "regular", TEXT_3, anchor="lm")
        c.text((sx1, sy + 42), f"{int(hi)}° hijau", 10, "regular", TEXT_3, anchor="rm")
        audit = OUT / "lemon_audit.json"
        if audit.exists():
            a = json.loads(audit.read_text())
            c.text((x1 - 16, y1 - 16), a["caption"], 11, "regular", TEXT_3, anchor="rm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    tr = json.loads((OUT / "tracks.json").read_text())
    frames, fps = B.read_video(VIDEO)
    lb = LemonBoard(tr, len(frames))
    summary = {"inspected": len(lb.order), "frames": len(frames), "fps": fps, "min_frames": MIN_FRAMES,
               "grades": [{"name": g[0], "hue_from": g[2], "destination": g[4]} for g in GRADES],
               "lemons": [{"tid": tid, "frame": lb.inspected[tid], "hue": round(lb.hue[tid], 1),
                           "grade": GRADES[lb.cls(tid)][1]} for tid in lb.order]}
    (OUT / "lemon_grading_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "lemons"}, ensure_ascii=False))
    for t in summary["lemons"]:
        print(t)
    if a.still is not None:
        if a.still:
            B.stills(lambda i: lb.draw(i, frames[i]), len(frames), set(a.still),
                     lambda f: OUT / f"lemon_still_{f:04d}.jpg")
        return
    B.encode((lb.draw(i, f) for i, f in enumerate(frames)), OUT / "lemon_grading.mp4", fps)
    print("video:", OUT / "lemon_grading.mp4")


if __name__ == "__main__":
    main()
