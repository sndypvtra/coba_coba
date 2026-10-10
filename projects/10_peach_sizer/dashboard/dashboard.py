"""Peach colour grading on the sizer, as a packhouse manager reads it, 1920 x 1080.

    python dashboard/segment.py          # once: find and follow every peach (~30 min on 4 cores)
    python dashboard/colour.py           # once: red share of every peach on the lines
    python dashboard/dashboard.py        # -> output/peach_grading.mp4
    python dashboard/dashboard.py --still 120 244

Buyers of red peaches and nectarines specify how much of the skin must be red:
the more red, the better the grade and the price. Each peach is read on its line
for as long as it is in view, turning on the rollers, and graded on the median
red share of those frames, once it has left the picture:

* Grade A: at least 90 % red, premium packs and export;
* Grade B: 60 to 90 % red, regular packs;
* Grade C: below 60 % red, diverted to processing.

The bounds are an example buyer specification, set before the blind check by
eye in output/peach_audit.json and not changed after it.

The camera looks along six lines that fan out from the feed belt: line 1 runs
down the left of the picture, lines 2 to 6 to the right, line 6 furthest away.
The count gate is one horizontal line across all six at GATE_Y, just past where
the fruit drops into the lines; it is the one height every line crosses inside
the picture (lower down, the far lines have already left it on the right).
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
from ui import AMBER, BG, CYAN, GREEN, SURFACE_2, TEXT, TEXT_2, TEXT_3, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "peach_sizer.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
GATE_Y = 375            # count gate, source px: a horizontal line across all six lines
BORN_BAND = 120         # a peach first found this close below the gate came through it unseen
MIN_BELOW = 4           # frames below the gate for a track to count as a peach on a line...
EXIT_X = 1850           # ...unless it left the picture on the right after crossing
DUP_FRAMES, DUP_PX = 6, 60   # two counts on one line this close in time and place are one peach
STITCH_GAP, STITCH_R = 5, 0.8   # a track that ends and one that starts this soon, this near, are one peach
RELINK_GAP, RELINK_R = 15, 1.0  # the same, looser, for a counted peach lost and found again on its own line
LANE_X = 1780                       # where lines 2-6 are told apart: their spread is widest here
LANE_BOUNDS = [391, 477, 567, 673]  # y on LANE_X between lines 6|5|4|3|2, from the crossing histogram
N_LINES = 6
MIN_READS = 3           # colour reads before a peach shows a grade
CRIMSON = (190, 18, 60)
ROSE = (251, 113, 133)

# (name, short, lowest red share, colour, where it goes). The reddest peaches are the best grade.
GRADES = [
    ("Grade A · merah ≥ 90%", "A", 0.90, CRIMSON, "kemasan premium / ekspor"),
    ("Grade B · merah 60–90%", "B", 0.60, ROSE, "kemasan reguler"),
    ("Grade C · merah < 60%", "C", -1.0, AMBER, "dialihkan ke olahan"),
]


def grade(s):
    for k, g in enumerate(GRADES):
        if s >= g[2]:
            return k
    return len(GRADES) - 1


def on_line1(x, y):
    """Line 1 runs down the left of the picture, steeper than the others."""
    return x < 0.9 * y - 100


class PeachBoard:
    def __init__(self, tr, colour, n_frames):
        self.tr = tr
        self.fps = tr["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.zone_y = colour["zone_y"]
        self.oversize = {tuple(v) for v in colour["oversize"]}
        self.board = ui.board(B.CARDS)
        self.thumbs = {}
        raw = {}
        for fr in tr["frames"]:
            for o in fr["objects"]:
                raw.setdefault(o["tid"], []).append((fr["frame"], o["cx"], o["cy"], 2 * np.sqrt(o["area"] / np.pi)))
        self.root, self.stitched = self.stitch(raw)
        self.paths = {}
        for t, p in raw.items():
            self.paths.setdefault(self.root[t], []).extend(p)
        for p in self.paths.values():
            p.sort()
        self.reads = {}
        for t, r in colour["reads"].items():
            self.reads.setdefault(self.root[int(t)], []).extend(r)
        for r in self.reads.values():
            r.sort()
        self.centrelines()
        self.count()
        self.grade_all()
        self.events = self.make_events()
        self._line_disp = {}

    # ---- following -----------------------------------------------------------
    @staticmethod
    def stitch(raw):
        """Join a track that ends to one that starts within STITCH_GAP frames where it was heading."""
        link, taken = {}, set()

        def find(t):
            while t in link:
                t = link[t]
            return t
        for b in sorted(raw, key=lambda t: raw[t][0][0]):
            fb, xb, yb, db = raw[b][0]
            best = None
            for a, p in raw.items():
                if a == b or a in taken:
                    continue
                fa, xa, ya, da = p[-1]
                g = fb - fa
                if not 1 <= g <= STITCH_GAP or find(a) == find(b):
                    continue
                if len(p) >= 2:
                    f0, x0, y0, _ = p[-2]
                    k = g / max(fa - f0, 1)
                    xa, ya = xa + (xa - x0) * k, ya + (ya - y0) * k
                d = np.hypot(xb - xa, yb - ya)
                if d <= STITCH_R * max(da, db) and (best is None or d < best[0]):
                    best = (d, a)
            if best:
                link[b] = best[1]
                taken.add(best[1])
        return {t: find(t) for t in raw}, len(link)

    def centrelines(self):
        """Lines 2-6: the median path of the peaches that reach LANE_X on each, in 60 px steps."""
        pts = {k: [] for k in range(2, N_LINES + 1)}
        for p in self.paths.values():
            x = np.array([q[1] for q in p])
            y = np.array([q[2] for q in p])
            if x.min() < LANE_X < x.max() and not on_line1(x.mean(), y.mean()):
                i = int(np.argmax(x >= LANE_X))
                yy = float(np.interp(LANE_X, x[[i - 1, i]], y[[i - 1, i]]))
                if yy >= 310:
                    pts[N_LINES - int(np.searchsorted(LANE_BOUNDS, yy))] += list(zip(x, y))
        self.centre = {}
        for k, v in pts.items():
            v = np.array(v)
            line = [(a + 30, float(np.median(v[(v[:, 0] >= a) & (v[:, 0] < a + 60), 1])))
                    for a in range(400, 1921, 60) if ((v[:, 0] >= a) & (v[:, 0] < a + 60)).sum() >= 4]
            self.centre[k] = np.array(line)

    def line_of(self, p):
        x = np.array([q[1] for q in p])
        y = np.array([q[2] for q in p])
        if np.mean(on_line1(x, y)) > 0.5:
            return 1
        sel = x >= 1100 if (x >= 1100).sum() >= 2 else np.ones(len(x), bool)
        best, bd = None, 1e9
        for k, c in self.centre.items():
            ok = sel & (x >= c[0, 0] - 30)
            if not ok.any():
                continue
            d = float(np.median(np.abs(y[ok] - np.interp(x[ok], c[:, 0], c[:, 1]))))
            if d < bd:
                best, bd = k, d
        return best

    # ---- counting and grading --------------------------------------------------
    def count(self):
        """One count per peach, when it crosses the gate (or is first found just below it)."""
        hits = {k: [] for k in range(1, N_LINES + 1)}
        for t, p in self.paths.items():
            f = np.array([q[0] for q in p], float)
            x = np.array([q[1] for q in p])
            y = np.array([q[2] for q in p])
            below = y >= GATE_Y
            # line 6 runs just under the gate and leaves the picture on the right soon after crossing it
            if below.sum() < MIN_BELOW and not (below.any() and x[-1] > EXIT_X):
                continue
            j = int(np.argmax(below))
            if j > 0:
                xx = float(np.interp(GATE_Y, y[[j - 1, j]], x[[j - 1, j]]))
                ff = float(np.interp(GATE_Y, y[[j - 1, j]], f[[j - 1, j]]))
            elif y[0] < GATE_Y + BORN_BAND:
                xx, ff = float(x[0]), float(f[0])
            else:
                continue
            ln = self.line_of(p)
            if ln is not None:
                hits[ln].append((ff, t, xx, float(y[j])))
        self.counted, self.dropped, self.owner = [], 0, {}
        for ln, v in hits.items():
            v.sort()
            keep = []
            for h in v:
                same = [q for q in keep if abs(h[0] - q[0]) <= DUP_FRAMES and np.hypot(h[2] - q[2], h[3] - q[3]) < DUP_PX]
                if same:
                    self.dropped += 1
                    self.owner[h[1]] = same[-1][1]       # the same peach: its frames and reads go to the one counted
                    continue
                keep.append(h)
            self.counted += [(int(np.ceil(h[0])), h[1], ln) for h in keep]
        self.counted.sort()
        self.line = {t: ln for _, t, ln in self.counted}
        self.relink()
        for a, b in self.owner.items():
            self.paths[b] = sorted(self.paths[b] + self.paths[a])
            self.reads[b] = sorted(self.reads.get(b, []) + self.reads.get(a, []))
        # where each line leaves the picture, for its name tag: line 1 at the bottom, lines 2-6 on the right
        p1 = np.array([(q[1], q[2]) for t, ln in self.line.items() if ln == 1 for q in self.paths[t]])
        self.tag = {1: (float(np.median(p1[p1[:, 1] > 960, 0])) + 90, 1000.0)}
        for k, cl in self.centre.items():
            self.tag[k] = (1905.0, float(np.interp(1880, cl[:, 0], cl[:, 1])))
        self.count_f = {t: f for f, t, _ in self.counted}

    def relink(self):
        """A piece of track that starts mid-line, where a counted peach on the same line was lost a moment
        before, is that peach found again: it gets no count of its own, its frames and reads join the peach."""
        last = {t: self.paths[t][-1] for t in self.line}
        for u in sorted(self.paths, key=lambda t: self.paths[t][0][0]):
            if u in self.line or u in self.owner:
                continue
            p = self.paths[u]
            if sum(1 for q in p if q[2] >= GATE_Y) < MIN_BELOW:
                continue
            ln = self.line_of(p)
            fu, xu, yu, du = p[0]
            best = None
            for t, (ft, xt, yt, dt) in last.items():
                g = fu - ft
                if self.line[t] != ln or not 1 <= g <= RELINK_GAP:
                    continue
                d = np.hypot(xu - xt, yu - yt)
                if d <= RELINK_R * max(du, dt) and (best is None or d < best[0]):
                    best = (d, t)
            if best:
                self.owner[u] = best[1]
                last[best[1]] = p[-1]

    def grade_all(self):
        """The grade is the median red share of all the peach's reads, final when it leaves the picture."""
        self.final_f, self.share = {}, {}
        for f, t, _ in self.counted:
            r = self.reads.get(t, [])
            if not r:
                continue
            self.final_f[t] = max(f, self.paths[t][-1][0])
            self.share[t] = float(np.median([s for _, s in r]))
        self.graded = sorted(self.final_f, key=self.final_f.get)

    def cls(self, t):
        return grade(self.share[t])

    def live(self, t, f):
        if t in self.final_f and self.final_f[t] <= f:
            return self.share[t]
        r = [s for fr, s in self.reads.get(t, []) if fr <= f]
        return float(np.median(r)) if len(r) >= MIN_READS else None

    def line_disp(self, t):
        """The line a peach on screen is on: its counted line, or read from its path if it was not counted
        (a piece of track that could not be joined safely to a counted peach)."""
        if t not in self._line_disp:
            p = self.paths[t]
            self._line_disp[t] = self.line[t] if t in self.line else (
                self.line_of(p) if sum(1 for q in p if q[2] >= GATE_Y) >= MIN_BELOW else None)
        return self._line_disp[t]

    def done(self, f):
        return [t for t in self.graded if self.final_f[t] <= f]

    def make_events(self):
        ev = []
        for t in self.graded:
            if self.cls(t) == 2:
                f = self.final_f[t]
                ev.append(B.Event(f, (f - 1) / self.fps, "medium", "call_split", f"Grade C · Line {self.line[t]}",
                                  f"{num(100 * self.share[t], 0)}% merah · dialihkan", "grade_c", feed=False))
        return ev

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        f = i + 1
        img = frame.copy()
        fr = self.tr["frames"][i]
        layer = img.copy()
        chips = []
        for o in fr["objects"]:
            r = self.root[o["tid"]]
            t = self.owner.get(r, r)
            if not o["poly"] or o["cy"] < self.zone_y or (o["tid"], f) in self.oversize or self.line_disp(t) is None:
                continue
            pts = (np.array(o["poly"], np.float32) * K).astype(np.int32)
            s = self.live(t, f)
            if s is None:
                cv2.polylines(img, [pts], True, ui.bgr(TEXT_3), 1, cv2.LINE_AA)
                continue
            col = GRADES[grade(s)][3]
            cv2.fillPoly(layer, [pts], ui.bgr(col))
            cv2.polylines(img, [pts], True, ui.bgr(col), 2, cv2.LINE_AA)
            chips.append((o, t, s))
        cv2.addWeighted(layer, 0.22, img, 0.78, 0, img)
        zy, gy = self.zone_y * K, GATE_Y * K
        ui.dashed(img, np.array([[0, zy], [B.VW, zy]]), CYAN, 1, 10, 8)
        ui.dashed(img, np.array([[0, gy], [B.VW, gy]]), TEXT, 2, 12, 6)
        c = ui.Canvas(img)
        c.pill((B.VW - 10, zy - 4), "Zona grading · warna dibaca selama buah di line", 11, (255, 255, 255),
               alpha(CYAN, 0.85), "semibold", icon="filter_center_focus", pad=(8, 2), anchor="rb")
        c.pill((300, gy - 4), "Gerbang hitung · semua line", 11, TEXT, alpha(BG, 0.85), "semibold", icon="counter_1",
               pad=(8, 2), anchor="mb")
        for o, t, s in sorted(chips, key=lambda v: -grade(v[2])):
            col = GRADES[grade(s)][3]
            x0, y0, x1, y1 = (v * K for v in o["box"])
            B.chip(c, ((x0 + x1) / 2, (y0 + y1) / 2), f"Line {self.line_disp(t)} · Grade {GRADES[grade(s)][1]}", col,
                   None, anchor="mm", size=11)
        n_line = [sum(1 for cf, _, ln in self.counted if ln == k and cf <= f) for k in range(1, N_LINES + 1)]
        for k in range(1, N_LINES + 1):
            tx, ty = self.tag[k]
            c.pill((tx * K, ty * K), f"LINE {k} · {n_line[k - 1]}", 12, (20, 24, 30), alpha(TEXT, 0.92), "bold",
                   pad=(7, 3), anchor="rm" if k > 1 else "lm", tnum=True)
        B.corner_chips(c, "CAM 01 · Sizer persik, 6 line", [f"Terhitung: {sum(n_line)}", "Rekaman nyata"])
        c.rrect((8, B.VH - 38, 600, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", GRADES[0][3], "Grade A ≥ 90%"), ("bar", GRADES[1][3], "Grade B 60–90%"),
                                   ("bar", GRADES[2][3], "Grade C < 60%"), ("bar", TEXT_3, "sedang dibaca")], 12)
        return c.bgr()

    # ---- the page ------------------------------------------------------------
    def draw(self, i, frame):
        f = i + 1
        t = i / self.fps
        vid = self.overlay(frame, i)
        img = self.board.copy()
        ui.paste_rounded(img, vid, (B.VX, B.VY), 10)
        done = self.done(f)
        c = ui.Canvas(img)
        c.topbar("Grading · warna persik", "Lini sortir persik · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, f, done, t)
        self.mix(c, done)
        self.per_line(c, f, done)
        self.history(c, done)
        self.red_strip(c, done)
        c.timeline(B.TL, t, self.total, self.events, title="Grade C dialihkan")
        return c.bgr()

    def kpis(self, c, f, done, t):
        n = sum(1 for cf, _, _ in self.counted if cf <= f)
        rate = n / t * 60 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[0], "nutrition", "Persik terhitung", str(n),
              f"6 line · ≈ {num(rate, 0)}/menit, perkiraan dari {num(t, 1)} s" if rate else "6 line · gerbang hitung",
              CRIMSON)
        g = len(done)
        a = sum(1 for x in done if self.cls(x) == 0)
        c.kpi(B.KPI_BOXES[1], "verified", "Grade A", f"{num(100 * a / g, 0)}%" if g else "–",
              f"{a} dari {g} tergrade · premium / ekspor" if g else "menunggu grade pertama", CRIMSON)
        b = sum(1 for x in done if self.cls(x) == 1)
        c.kpi(B.KPI_BOXES[2], "label", "Grade B", f"{num(100 * b / g, 0)}%" if g else "–",
              f"{b} persik · kemasan reguler" if g else "menunggu grade pertama", ROSE)
        y = sum(1 for x in done if self.cls(x) == 2)
        c.kpi(B.KPI_BOXES[3], "call_split", "Grade C, dialihkan", str(y),
              f"{num(100 * y / g, 0)}% · ke olahan, bukan kemasan" if y else "belum ada", AMBER,
              value_fill=AMBER if y else TEXT)

    def mix(self, c, done):
        y = c.card_title(B.MID, "Komposisi grade", "category", f"{len(done)} persik tergrade")
        x0, _, x1, y1 = B.MID
        counts = [sum(1 for t in done if self.cls(t) == k) for k in range(3)]
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
        c.text((x0 + 16, y1 - 18), "Grade = bagian kulit berwarna merah, median selama buah berputar di line", 11,
               "regular", TEXT_3, anchor="lm")

    def per_line(self, c, f, done):
        """Load and grade mix per line: where the fruit runs, and whether one line carries worse fruit."""
        y = c.card_title(B.FEED, "Kualitas per line", "stacked_bar_chart", "jumlah terhitung · grade")
        x0, _, x1, y1 = B.FEED
        cnt = [sum(1 for cf, _, ln in self.counted if ln == k and cf <= f) for k in range(1, N_LINES + 1)]
        mix = [[sum(1 for t in done if self.line[t] == k and self.cls(t) == g) for g in range(3)]
               for k in range(1, N_LINES + 1)]
        tot = max(1, sum(cnt))
        vmax = max(max(cnt), 1)
        bx0, bx1 = x0 + 92, x1 - 150
        ry = y + 20
        for k in range(N_LINES):
            c.text((x0 + 16, ry), f"Line {k + 1}", 13, "semibold", TEXT, anchor="lm")
            c.rrect((bx0, ry - 8, bx1, ry + 8), 4, fill=SURFACE_2)
            g = sum(mix[k])
            wtot = (bx1 - bx0) * cnt[k] / vmax
            x = bx0
            for gi in range(3):
                if g and mix[k][gi]:
                    w = wtot * mix[k][gi] / g
                    c.rrect((x, ry - 8, x + max(w - 2, 2), ry + 8), 4, fill=GRADES[gi][3])
                    x += w
            if cnt[k] and not g:
                c.rrect((bx0, ry - 8, bx0 + wtot, ry + 8), 4, fill=alpha(TEXT_3, 0.6))
            c.text((bx1 + 12, ry), f"{cnt[k]}", 14, "bold", TEXT, anchor="lm", tnum=True)
            c.text((bx1 + 44, ry), f"{num(100 * cnt[k] / tot, 0)}%" if sum(cnt) else "–", 11, "regular", TEXT_3,
                   anchor="lm", tnum=True)
            c.text((x1 - 16, ry), f"A {num(100 * mix[k][0] / g, 0)}%" if g else "–", 12, "semibold", TEXT_2,
                   anchor="rm", tnum=True)
            ry += 52
        c.text((x0 + 16, y1 - 18), "Panjang bar = persik terhitung per line · warna = grade · kanan = porsi Grade A",
               11, "regular", TEXT_3, anchor="lm")

    def history(self, c, done):
        y = c.card_title(B.BL, "Persik terakhir tergrade", "history", "terbaru di kiri")
        x0, _, x1, y1 = B.BL
        tw, gap = 78, 9
        x = x0 + 16
        for t in list(reversed(done))[:7]:
            name, short, _, col, _ = GRADES[self.cls(t)]
            c.rrect((x, y + 2, x + tw, y1 - 14), 8, fill=SURFACE_2)
            c.rrect((x, y + 2, x + tw, y + 6), 2, fill=col)
            c.text((x + tw / 2, y + 24), f"Line {self.line[t]}", 12, "semibold", TEXT, anchor="mm")
            # a ring filled red as far as the skin is red
            cx, cy, r = x + tw / 2, y + 62, 20
            c.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=SURFACE_2, outline=alpha(TEXT_3, 0.6), width=5)
            c.d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * self.share[t], fill=col, width=5)
            c.text((cx, cy), f"{num(100 * self.share[t], 0)}%", 11, "semibold", TEXT, anchor="mm", tnum=True)
            c.text((x + tw / 2, y + 100), "merah", 11, "regular", TEXT_2, anchor="mm")
            c.pill((x + tw / 2, y + 124), f"Grade {short}", 10, (255, 255, 255), alpha(col, 0.95), "semibold",
                   pad=(6, 2), anchor="mm")
            x += tw + gap
        if not done:
            c.text(((x0 + x1) / 2, (y + y1) / 2), "Menunggu persik pertama selesai dibaca", 13, "regular", TEXT_3,
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
            c.text(((a + b) / 2, sy - 40), f"Grade {GRADES[k][1]}", 12, "semibold", TEXT_2, anchor="mm")
        for b in (GRADES[0][2], GRADES[1][2]):
            c.d.line((X(b), sy - 30, X(b), sy + 30), fill=alpha(TEXT_3, 0.9), width=1)
            c.text((X(b), sy + 42), f"{int(round(100 * b))}%", 10, "regular", TEXT_3, anchor="mm")
        rng = np.random.default_rng(3)
        for t in done:
            col = GRADES[self.cls(t)][3]
            yy = sy + rng.uniform(-16, 16)
            xx = X(self.share[t]) + (rng.uniform(-14, 0) if self.share[t] > 0.985 else 0)
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
    n, g = len(pb.counted), len(pb.graded)
    counts = [sum(1 for t in pb.graded if pb.cls(t) == k) for k in range(3)]
    summary = {"seconds": round(len(frames) / fps, 2), "counted": n, "graded": g,
               "per_minute": round(n / (len(frames) / fps) * 60), "duplicate_counts_dropped": pb.dropped,
               "track_pieces_stitched": pb.stitched, "gate_y": GATE_Y,
               "per_line": [sum(1 for _, _, ln in pb.counted if ln == k) for k in range(1, N_LINES + 1)],
               "grades": [{"name": gr[0], "red_share_from": max(gr[2], 0.0), "destination": gr[4], "count": counts[k],
                           "share": round(counts[k] / max(g, 1), 3)} for k, gr in enumerate(GRADES)],
               "peaches": [{"tid": t, "line": pb.line[t], "counted_frame": pb.count_f[t], "graded_frame": pb.final_f[t],
                            "reads": sum(1 for fr, _ in pb.reads[t] if fr <= pb.final_f[t]),
                            "red_share": round(pb.share[t], 3), "grade": GRADES[pb.cls(t)][1]} for t in pb.graded]}
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
