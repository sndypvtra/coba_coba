"""Lime grading on two singulator chains, as a packhouse manager reads it, 1920 x 1080.

    python prepare.py                    # once: the clip
    python dashboard/detect.py           # once: detect, follow and read every lime (~11 min)
    python dashboard/dashboard.py        # -> output/lime_grading.mp4
    python dashboard/dashboard.py --still 120 245

Two chains carry limes away from the camera. A lime is counted once, when its
box centre crosses the count gate, a horizontal line across both chains at
GATE_Y; the chain it is on (line 1 left, line 2 right) is where it crosses. Its
grade is the colour of its skin as a CIELAB hue angle, read inside its box on
the frames where it is sharpest: deep green limes are Grade A (export and
supermarkets), light green Grade B (local market), yellowing limes Grade C
(processing, juice). The bounds are in GRADES; how well they agree with grading
by eye is in output/lime_audit.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import board as B  # noqa: E402
import ui  # noqa: E402
from ui import AMBER, BG, CYAN, GREEN, SURFACE_2, TEXT, TEXT_2, TEXT_3, YELLOW, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "lime_chain.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
GATE_Y = 600              # count gate (source px): horizontal, across both chains
LINE_SPLIT = 800          # x on the gate between line 1 (left chain) and line 2 (right chain)
N_LINES = 2
MIN_AGE = 3               # frames a track must be held before it can be counted
MIN_CHROMA = 20           # a lime is coloured; steel and rubber are not
DUP_FRAMES, DUP_PX = 1.5, 60  # two counts on one line this close are one lime whose identity broke (touching limes pass 3 frames apart)
CHIP_FRAMES = 10          # a counted lime keeps its label this long after the gate (limes move fast)
TREND_WIN = 2.0           # s: the quality trend is the grade mix of the limes counted in the last 2 s
LIME = (132, 204, 22)
DEEP = (21, 128, 61)      # Grade A: a darker green than Grade B, so the two read apart

# Grade by hue angle (degrees): the greenest limes have the highest angle. The bounds
# were set on another clip of the same packhouse and series (Pexels 32953304), same
# light, and are used here unchanged. (name, short, lower hue bound, colour, destination)
GRADES = [
    ("Grade A · hijau tua", "A", 106.0, DEEP, "ekspor / supermarket"),
    ("Grade B · hijau muda", "B", 97.0, LIME, "pasar lokal"),
    ("Grade C · menguning", "C", -999.0, YELLOW, "olahan: jus, konsentrat"),
]


def grade(h):
    for k, g in enumerate(GRADES):
        if h >= g[2]:
            return k
    return len(GRADES) - 1


class LimeBoard:
    def __init__(self, tr, n_frames):
        self.tr = tr
        self.fps = tr["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.board = ui.board(B.CARDS)
        self.paths, reads, chroma = {}, {}, {}
        for fr in tr["frames"]:
            for o in fr["objects"]:
                b = o["box"]
                self.paths.setdefault(o["tid"], []).append((fr["frame"], (b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
                reads.setdefault(o["tid"], []).append((o["sharp"], o["hue"]))
                chroma.setdefault(o["tid"], []).append(o["chroma"])
        # each lime's hue: the median over the half of its frames where it is sharpest
        self.hue = {}
        for t, rs in reads.items():
            rs.sort(reverse=True)
            self.hue[t] = float(np.median([h for _, h in rs[:max(3, len(rs) // 2)]]))
        self.grey = {t for t, v in chroma.items() if np.median(v) < MIN_CHROMA}
        self.count()
        self.events = [B.Event(f, (f - 1) / self.fps, "medium", "call_split", f"Lime menguning · Line {ln}",
                               f"hue {num(self.hue[t], 0)}° · alihkan ke olahan", "grade_c", feed=False)
                       for f, t, ln in self.counted if self.cls(t) == 2]

    def count(self):
        """One count per lime, when its box centre crosses the gate going away from the camera."""
        hits = {k: [] for k in range(1, N_LINES + 1)}
        for t, p in self.paths.items():
            if t in self.grey:
                continue
            f = np.array([q[0] for q in p], float)
            x = np.array([q[1] for q in p])
            y = np.array([q[2] for q in p])
            i = np.nonzero((y[:-1] >= GATE_Y) & (y[1:] < GATE_Y))[0]
            if not len(i) or i[0] + 1 < MIN_AGE:
                continue
            j = i[0]
            xx = float(np.interp(GATE_Y, [y[j + 1], y[j]], [x[j + 1], x[j]]))
            ff = int(np.ceil(np.interp(GATE_Y, [y[j + 1], y[j]], [f[j + 1], f[j]])))
            hits[1 if xx < LINE_SPLIT else 2].append((ff, t, xx))
        self.counted, self.dropped = [], 0
        for ln, v in hits.items():
            v.sort()
            keep = []
            for h in v:
                if any(abs(h[0] - q[0]) <= DUP_FRAMES and abs(h[2] - q[2]) < DUP_PX for q in keep):
                    self.dropped += 1
                    continue
                keep.append(h)
            self.counted += [(h[0], h[1], ln) for h in keep]
        self.counted.sort()
        self.line = {t: ln for _, t, ln in self.counted}
        self.count_f = {t: f for f, t, _ in self.counted}

    def cls(self, t):
        return grade(self.hue[t])

    def done(self, f):
        return [(cf, t, ln) for cf, t, ln in self.counted if cf <= f]

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        img = frame.copy()
        fr = self.tr["frames"][i]
        f = i + 1
        gy = GATE_Y * K
        for o in fr["objects"]:
            t = o["tid"]
            if t in self.grey or sum(1 for q in self.paths[t] if q[0] <= f) < MIN_AGE:
                continue
            done = self.count_f.get(t, 10 ** 6) <= f
            ui.lock_box(img, [v * K for v in o["box"]], GRADES[self.cls(t)][3], 2, fill=0.12 if done else 0.0)
        ui.dashed(img, np.array([[0, gy], [B.VW, gy]]), CYAN, 2, 12, 6)
        c = ui.Canvas(img)
        c.pill((B.VW / 2, gy - 6), "Gerbang hitung · kedua line", 11, (255, 255, 255), alpha(CYAN, 0.85), "semibold",
               icon="counter_1", pad=(8, 2), anchor="mb")
        # the yellowing ones on top: they are the ones the line has to act on
        for o in sorted(fr["objects"], key=lambda o: -self.cls(o["tid"])):
            t = o["tid"]
            if not 0 <= f - self.count_f.get(t, 10 ** 6) <= CHIP_FRAMES:
                continue
            name, short, _, col, _ = GRADES[self.cls(t)]
            x0, y0 = o["box"][0] * K, o["box"][1] * K
            B.chip(c, (max(6, x0), y0 - 4), f"Line {self.line[t]} · Grade {short} ✓", col, None, anchor="lb", size=11)
        n_line = [sum(1 for cf, _, ln in self.counted if ln == k and cf <= f) for k in range(1, N_LINES + 1)]
        c.pill((16, gy + 10), f"LINE 1 · {n_line[0]}", 12, (20, 24, 30), alpha(TEXT, 0.92), "bold", pad=(7, 3),
               anchor="lt", tnum=True)
        c.pill((B.VW - 16, gy + 10), f"LINE 2 · {n_line[1]}", 12, (20, 24, 30), alpha(TEXT, 0.92), "bold",
               pad=(7, 3), anchor="rt", tnum=True)
        B.corner_chips(c, "CAM 01 · Rantai sortir lime, 2 line", [f"Terhitung: {sum(n_line)}", "Rekaman nyata"])
        c.rrect((8, B.VH - 38, 560, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", GRADES[0][3], "A · hijau tua"), ("bar", GRADES[1][3], "B · hijau muda"),
                                   ("bar", GRADES[2][3], "C · menguning"), ("dot", TEXT, "✓ terhitung")], 12)
        return c.bgr()

    # ---- the page ------------------------------------------------------------
    def draw(self, i, frame):
        f = i + 1
        t = i / self.fps
        vid = self.overlay(frame, i)
        img = self.board.copy()
        ui.paste_rounded(img, vid, (B.VX, B.VY), 10)
        done = self.done(f)
        tb = (B.BL[0] + 52, B.BL[1] + 56, B.BL[2] - 20, B.BL[3] - 44)
        a_s, c_s = self.trend(f)
        B.series_chart(img, tb, [(a_s, DEEP, True), (c_s, YELLOW, False)], self.n, 100)
        c = ui.Canvas(img)
        c.topbar("Grading · warna lime", "Rantai sortir lime · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, done, t)
        self.mix(c, done)
        self.per_line(c, done)
        self.trend_card(c, tb, a_s, c_s)
        self.hue_strip(c, done)
        c.timeline(B.TL, t, self.total, self.events, title="Lime menguning dialihkan")
        return c.bgr()

    def trend(self, f):
        """Share of Grade A and Grade C among the limes counted in the last TREND_WIN s, frame by frame."""
        a_s, c_s = [], []
        w = TREND_WIN * self.fps
        for g in range(1, f + 1):
            win = [t for cf, t, _ in self.counted if g - w < cf <= g]
            if len(win) < 2:
                a_s.append(a_s[-1] if a_s else 0.0)
                c_s.append(c_s[-1] if c_s else 0.0)
                continue
            a_s.append(100 * sum(1 for t in win if self.cls(t) == 0) / len(win))
            c_s.append(100 * sum(1 for t in win if self.cls(t) == 2) / len(win))
        return a_s, c_s

    def kpis(self, c, done, t):
        n = len(done)
        rate = n / t * 60 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[0], "nutrition", "Lime terhitung", str(n),
              f"2 line · ≈ {num(rate, 0)}/menit, perkiraan dari {num(t, 1)} s" if rate else "2 line · gerbang hitung",
              LIME)
        cnt = [sum(1 for _, x, _ in done if self.cls(x) == k) for k in range(3)]
        c.kpi(B.KPI_BOXES[1], "verified", "Grade A · ekspor", f"{num(100 * cnt[0] / n, 0)}%" if n else "–",
              f"{cnt[0]} lime hijau tua · supermarket / ekspor" if n else "menunggu lime pertama", DEEP)
        c.kpi(B.KPI_BOXES[2], "label", "Grade B · pasar lokal", f"{num(100 * cnt[1] / n, 0)}%" if n else "–",
              f"{cnt[1]} lime hijau muda" if n else "menunggu lime pertama", LIME)
        c.kpi(B.KPI_BOXES[3], "call_split", "Grade C · menguning", str(cnt[2]),
              f"{num(100 * cnt[2] / n, 0)}% · alihkan ke olahan" if cnt[2] else "belum ada lime menguning", AMBER,
              value_fill=AMBER if cnt[2] else TEXT)

    def mix(self, c, done):
        y = c.card_title(B.MID, "Komposisi grade & tujuan", "category", f"{len(done)} lime")
        x0, _, x1, y1 = B.MID
        counts = [sum(1 for _, t, _ in done if self.cls(t) == k) for k in range(3)]
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
        c.text((x0 + 16, y1 - 18), "Grade dari sudut hue warna kulit (CIELAB), dibaca di dalam kotak deteksi", 11,
               "regular", TEXT_3, anchor="lm")

    def per_line(self, c, done):
        """Each chain's load and grade mix, side by side."""
        y = c.card_title(B.FEED, "Grade per line", "stacked_bar_chart", "jumlah terhitung · grade")
        x0, _, x1, y1 = B.FEED
        cnt = [sum(1 for _, _, ln in done if ln == k) for k in range(1, N_LINES + 1)]
        mix = [[sum(1 for _, t, ln in done if ln == k and self.cls(t) == g) for g in range(3)]
               for k in range(1, N_LINES + 1)]
        tot = max(1, sum(cnt))
        ry = y + 20
        for k in range(N_LINES):
            c.text((x0 + 16, ry), f"Line {k + 1}", 16, "bold", TEXT, anchor="lm")
            c.text((x0 + 92, ry), "rantai kiri" if k == 0 else "rantai kanan", 12, "regular", TEXT_3, anchor="lm")
            c.text((x1 - 16, ry), f"{cnt[k]} lime · {num(100 * cnt[k] / tot, 0)}%" if sum(cnt) else "–", 13,
                   "semibold", TEXT_2, anchor="rm", tnum=True)
            bx0, bx1, by = x0 + 16, x1 - 16, ry + 22
            c.rrect((bx0, by, bx1, by + 18), 4, fill=SURFACE_2)
            x = bx0
            for g in range(3):
                if mix[k][g]:
                    w = (bx1 - bx0) * mix[k][g] / cnt[k]
                    c.rrect((x, by, x + w - 2, by + 18), 4, fill=GRADES[g][3])
                    x += w
            gx = x0 + 16
            for g in range(3):
                share = f"{num(100 * mix[k][g] / cnt[k], 0)}%" if cnt[k] else "–"
                c.dot((gx + 6, by + 44), 5, GRADES[g][3])
                c.text((gx + 16, by + 44), f"Grade {GRADES[g][1]}  {share}", 12, "medium", TEXT_2, anchor="lm",
                       tnum=True)
                gx += (x1 - x0 - 32) / 3
            ry += 150
        c.text((x0 + 16, y1 - 18), "Bandingkan mutu tiap line: pasokan dari sumber berbeda terlihat di sini", 11,
               "regular", TEXT_3, anchor="lm")

    def trend_card(self, c, tb, a_s, c_s):
        c.card_title(B.BL, "Tren mutu", "monitoring", f"porsi grade, {num(TREND_WIN, 0)} s terakhir")
        B.chart_axes(c, tb, 100, [0, 50, 100], self.total, xstep=1, fmt=lambda v: f"{v}%", xfmt=lambda s: f"{int(s)} s")
        x0, _, x1, y1 = B.BL
        c.legend((x0 + 16, y1 - 14), [("bar", DEEP, f"Grade A {num(a_s[-1], 0)}%"),
                                      ("bar", YELLOW, f"Grade C {num(c_s[-1], 0)}%")], 12)

    def hue_strip(self, c, done):
        y = c.card_title(B.BR, "Sebaran warna lime terhitung", "palette", "batas grade di garis putus")
        x0, _, x1, y1 = B.BR
        lo, hi = 80.0, 120.0
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
            c.text((X(b), sy + 42), f"{int(b)}°", 10, "regular", TEXT_3, anchor="mm")
        rng = np.random.default_rng(3)
        for _, t, _ in done:
            col = GRADES[self.cls(t)][3]
            yy = sy + rng.uniform(-16, 16)
            c.dot((X(self.hue[t]), yy), 6, col)
            c.d.ellipse((X(self.hue[t]) - 6, yy - 6, X(self.hue[t]) + 6, yy + 6), outline=ui.SURFACE + (255,), width=2)
        c.text((sx0, sy + 42), f"{int(lo)}° kuning", 10, "regular", TEXT_3, anchor="lm")
        c.text((sx1, sy + 42), f"{int(hi)}° hijau", 10, "regular", TEXT_3, anchor="rm")
        audit = OUT / "lime_audit.json"
        if audit.exists():
            c.text((x1 - 16, y1 - 16), json.loads(audit.read_text())["caption"], 11, "regular", TEXT_3, anchor="rm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    tr = json.loads((OUT / "tracks.json").read_text())
    frames, fps = B.read_video(VIDEO)
    lb = LimeBoard(tr, len(frames))
    n = len(lb.counted)
    cnt = [sum(1 for _, t, _ in lb.counted if lb.cls(t) == k) for k in range(3)]
    summary = {"seconds": round(len(frames) / fps, 2), "counted": n, "per_minute": round(n / (len(frames) / fps) * 60),
               "duplicate_counts_dropped": lb.dropped, "not_lime_tracks": len(lb.grey), "gate_y": GATE_Y,
               "per_line": [sum(1 for _, _, ln in lb.counted if ln == k) for k in range(1, N_LINES + 1)],
               "grades": [{"name": g[0], "hue_from": max(g[2], 0.0), "destination": g[4], "count": cnt[k],
                           "share": round(cnt[k] / max(n, 1), 3)} for k, g in enumerate(GRADES)],
               "limes": [{"tid": t, "line": ln, "frame": f, "hue": round(lb.hue[t], 1),
                          "grade": GRADES[lb.cls(t)][1]} for f, t, ln in lb.counted]}
    (OUT / "lime_grading_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "limes"}, ensure_ascii=False))
    if a.still is not None:
        if a.still:
            B.stills(lambda i: lb.draw(i, frames[i]), len(frames), set(a.still),
                     lambda f: OUT / f"lime_still_{f:04d}.jpg")
        return
    B.encode((lb.draw(i, f) for i, f in enumerate(frames)), OUT / "lime_grading.mp4", fps)
    print("video:", OUT / "lime_grading.mp4")


if __name__ == "__main__":
    main()
