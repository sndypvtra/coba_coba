"""Peach colour on the sizer against the USDA grade standards, as a packhouse manager reads it, 1920 x 1080.

    python dashboard/segment.py          # once: find and follow every peach (~30 min on 4 cores)
    python dashboard/colour.py           # once: red share of every peach on the lines
    python dashboard/dashboard.py        # -> output/peach_grading.mp4
    python dashboard/dashboard.py --still 120 244

The colour rules are those of the United States Standards for Grades of Peaches
(7 CFR 51.1210-51.1214, 2004):

* U.S. Fancy: each peach shall have not less than one-third of its surface
  showing blushed, pink or red colour; at most 10 % of a lot may fail it;
* U.S. Extra No. 1: 50 % of the peaches in a lot, by count, shall have not less
  than one-fourth of the surface showing blushed, pink or red colour;
* U.S. No. 1 and No. 2 carry no colour requirement.

Each peach is read on its line for as long as it is in view, turning on the
rollers, and its red share is the median of those frames. The grades also ask
for freedom from defects, decay and bruises, which the camera does not judge:
what this checks is the colour requirement of each grade, nothing else.

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

FANCY = 1 / 3            # USDA U.S. Fancy: each peach >= 1/3 of the surface blushed, pink or red
FANCY_TOL = 0.10         # ...at most 10 % of a lot may fail it
EXTRA1 = 1 / 4           # USDA U.S. Extra No. 1: >= 50 % of the lot with >= 1/4 of the surface red
EXTRA1_SHARE = 0.50

# Colour class of one peach under the USDA rules. (name, short, lowest red share, colour, what it means)
GRADES = [
    ("Fancy colour", "Fancy", FANCY, CRIMSON, "≥ ⅓ permukaan merah · syarat warna U.S. Fancy"),
    ("Extra No. 1 colour", "Extra 1", EXTRA1, ROSE, "¼–⅓ permukaan merah · dihitung untuk U.S. Extra No. 1"),
    ("Below colour requirement", "Below", -1.0, AMBER, "< ¼ permukaan merah · hanya U.S. No. 1 / No. 2"),
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
            if self.cls(t) > 0:
                f = self.final_f[t]
                ev.append(B.Event(f, (f - 1) / self.fps, "medium", "call_split",
                                  f"{GRADES[self.cls(t)][0]} · Line {self.line[t]}",
                                  f"{num(100 * self.share[t], 0)}% merah · gagal syarat warna U.S. Fancy", "off_colour",
                                  feed=False))
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
        c.pill((B.VW - 10, zy - 4), "Colour zone · read while the fruit turns on its line", 11, (255, 255, 255),
               alpha(CYAN, 0.85), "semibold", icon="filter_center_focus", pad=(8, 2), anchor="rb")
        c.pill((300, gy - 4), "Count gate · all lines", 11, TEXT, alpha(BG, 0.85), "semibold", icon="counter_1",
               pad=(8, 2), anchor="mb")
        for o, t, s in sorted(chips, key=lambda v: -grade(v[2])):
            col = GRADES[grade(s)][3]
            x0, y0, x1, y1 = (v * K for v in o["box"])
            B.chip(c, ((x0 + x1) / 2, (y0 + y1) / 2), f"Line {self.line_disp(t)} · {GRADES[grade(s)][1]} · {num(100 * s, 0)}%", col,
                   None, anchor="mm", size=11)
        n_line = [sum(1 for cf, _, ln in self.counted if ln == k and cf <= f) for k in range(1, N_LINES + 1)]
        for k in range(1, N_LINES + 1):
            tx, ty = self.tag[k]
            c.pill((tx * K, ty * K), f"LINE {k} · {n_line[k - 1]}", 12, (20, 24, 30), alpha(TEXT, 0.92), "bold",
                   pad=(7, 3), anchor="rm" if k > 1 else "lm", tnum=True)
        B.corner_chips(c, "CAM 01 · Peach sizer, 6 lines", [f"Counted: {sum(n_line)}", "Rekaman nyata"])
        c.rrect((8, B.VH - 38, 700, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", GRADES[0][3], "Fancy ≥ ⅓ red"), ("bar", GRADES[1][3], "Extra No. 1 ≥ ¼"),
                                   ("bar", GRADES[2][3], "Below < ¼"), ("bar", TEXT_3, "reading")], 12)
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
        c.topbar("Colour grading · persik (USDA)", "Peach sizer line · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, f, done, t)
        self.mix(c, done)
        self.per_line(c, f, done)
        self.history(c, done)
        self.red_strip(c, done)
        c.timeline(B.TL, t, self.total, self.events, title="Below U.S. Fancy colour")
        return c.bgr()

    def lot(self, done):
        """Colour shares of the peaches graded so far, against the USDA lot rules."""
        g = len(done)
        fancy = sum(1 for x in done if self.share[x] >= FANCY)
        quarter = sum(1 for x in done if self.share[x] >= EXTRA1)
        return g, fancy, quarter

    def verdict(self, done):
        g, fancy, quarter = self.lot(done)
        if not g:
            return None, "menunggu persik pertama", TEXT_3
        if fancy / g >= 1 - FANCY_TOL:
            return "U.S. Fancy", f"{num(100 * fancy / g, 0)}% ≥ ⅓ merah · gagal {num(100 * (g - fancy) / g, 0)}% ≤ 10%", GREEN
        if quarter / g >= EXTRA1_SHARE:
            return "U.S. Extra No. 1", f"{num(100 * quarter / g, 0)}% ≥ ¼ merah · syarat ≥ 50%", AMBER
        return "U.S. No. 1", "tidak memenuhi syarat warna Fancy / Extra No. 1", AMBER

    def kpis(self, c, f, done, t):
        n = sum(1 for cf, _, _ in self.counted if cf <= f)
        rate = n / t * 60 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[0], "nutrition", "Peaches counted", str(n),
              f"6 lines · ≈ {num(rate, 0)}/min, perkiraan dari {num(t, 1)} s" if rate else "6 lines · count gate",
              CRIMSON)
        g, fancy, quarter = self.lot(done)
        ok = g and fancy / g >= 1 - FANCY_TOL
        c.kpi(B.KPI_BOXES[1], "verified", "Meets U.S. Fancy colour", f"{num(100 * fancy / g, 0)}%" if g else "–",
              f"{fancy} dari {g} · syarat lot ≥ 90% (toleransi 10%)" if g else "≥ ⅓ permukaan merah per buah",
              CRIMSON, value_fill=TEXT if (ok or not g) else AMBER)
        c.kpi(B.KPI_BOXES[2], "rule", "Extra No. 1 colour rule", f"{num(100 * quarter / g, 0)}%" if g else "–",
              f"{quarter} buah ≥ ¼ merah · syarat lot ≥ 50%" if g else "≥ 50% lot dengan ≥ ¼ merah", ROSE)
        below = g - quarter
        c.kpi(B.KPI_BOXES[3], "call_split", "Below colour requirement", str(below),
              f"{num(100 * below / g, 0)}% · < ¼ permukaan merah" if below else "belum ada · semua ≥ ¼ merah", AMBER,
              value_fill=AMBER if below else TEXT)

    def mix(self, c, done):
        y = c.card_title(B.MID, "Grade Composition · USDA colour", "category", f"{len(done)} persik graded")
        x0, _, x1, y1 = B.MID
        counts = [sum(1 for t in done if self.cls(t) == k) for k in range(3)]
        n = max(1, len(done))
        bx0, bx1, by = x0 + 16, x1 - 16, y + 12
        x = bx0
        for k, v in enumerate(counts):
            if v:
                w = (bx1 - bx0) * v / n
                c.rrect((x, by, x + w - 2, by + 18), 4, fill=GRADES[k][3])
                x += w
        if not done:
            c.rrect((bx0, by, bx1, by + 18), 4, fill=SURFACE_2)
        ry = by + 46
        for k, (name, short, lo, col, means) in enumerate(GRADES):
            c.dot((x0 + 24, ry), 6, col)
            c.text((x0 + 38, ry), name, 14, "semibold", TEXT, anchor="lm")
            c.text((x0 + 38, ry + 20), means, 12, "regular", TEXT_2, anchor="lm")
            c.text((x1 - 16, ry), f"{counts[k]}", 20, "bold", TEXT, anchor="rm", tnum=True)
            c.text((x1 - 60, ry), f"{num(100 * counts[k] / n, 0)}%" if done else "–", 13, "medium", TEXT_2,
                   anchor="rm", tnum=True)
            ry += 54
        grade_name, detail, col = self.verdict(done)
        ly = ry - 18
        c.rrect((x0 + 16, ly, x1 - 16, ly + 44), 8, fill=alpha(col, 0.12))
        c.icon("check_circle" if col == GREEN else "inventory_2", (x0 + 36, ly + 22), 18, col)
        c.text((x0 + 54, ly + 13), f"Lot colour: {grade_name}" if grade_name else "Lot colour: –", 13, "semibold",
               TEXT, anchor="lm")
        c.text((x0 + 54, ly + 31), detail, 11, "regular", TEXT_2, anchor="lm")
        c.text((x0 + 16, y1 - 16), "USDA 7 CFR 51.1210–51.1214 · hanya syarat warna; cacat, busuk, memar tidak dinilai", 11,
               "regular", TEXT_3, anchor="lm")

    def per_line(self, c, f, done):
        """Colour uniformity per line: the middle half of the red shares on each line, and its median."""
        y = c.card_title(B.FEED, "Colour uniformity per line", "stacked_bar_chart", "sebaran % merah · garis = ⅓, ¼")
        x0, _, x1, y1 = B.FEED
        cnt = [sum(1 for cf, _, ln in self.counted if ln == k and cf <= f) for k in range(1, N_LINES + 1)]
        bx0, bx1 = x0 + 92, x1 - 140

        def X(v):
            return bx0 + (bx1 - bx0) * v
        ry = y + 22
        for k in range(1, N_LINES + 1):
            sh = np.array([self.share[t] for t in done if self.line[t] == k])
            c.text((x0 + 16, ry), f"Line {k}", 13, "semibold", TEXT, anchor="lm")
            c.rrect((bx0, ry - 8, bx1, ry + 8), 4, fill=SURFACE_2)
            for b, colb in ((EXTRA1, ROSE), (FANCY, CRIMSON)):
                c.d.line((X(b), ry - 10, X(b), ry + 10), fill=alpha(colb, 0.9), width=1)
            if len(sh):
                q1, med, q3 = np.percentile(sh, [25, 50, 75])
                c.rrect((X(q1), ry - 6, max(X(q3), X(q1) + 4), ry + 6), 3, fill=alpha(GRADES[grade(med)][3], 0.55))
                c.dot((X(med), ry), 5, GRADES[grade(med)][3])
                c.text((bx1 + 12, ry), f"{num(100 * med, 0)}%", 13, "bold", TEXT, anchor="lm", tnum=True)
            c.text((x1 - 16, ry), f"min {num(100 * sh.min(), 0)}%" if len(sh) else "–", 11, "regular", TEXT_3,
                   anchor="rm", tnum=True)
            ry += 52
        c.text((x0 + 16, y1 - 18), "Bar = 50% tengah persik di line itu · titik = median · kanan = persik paling sedikit merah", 11,
               "regular", TEXT_3, anchor="lm")

    def history(self, c, done):
        y = c.card_title(B.BL, "Last peaches graded", "history", "terbaru di kiri")
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
            c.pill((x + tw / 2, y + 124), short, 10, (255, 255, 255), alpha(col, 0.95), "semibold",
                   pad=(6, 2), anchor="mm")
            x += tw + gap
        if not done:
            c.text(((x0 + x1) / 2, (y + y1) / 2), "Menunggu persik pertama selesai dibaca", 13, "regular", TEXT_3,
                   anchor="mm")

    def red_strip(self, c, done):
        y = c.card_title(B.BR, "Red colour spread", "palette", "batas USDA ¼ dan ⅓ di garis putus")
        x0, _, x1, y1 = B.BR
        sx0, sx1, sy = x0 + 30, x1 - 30, y + 70

        def X(s):
            return sx0 + (sx1 - sx0) * min(max(s, 0.0), 1.0)
        bounds = [1.0, FANCY, EXTRA1, 0.0]
        for k in range(3):
            a, b = X(bounds[k + 1]), X(bounds[k])
            c.rrect((a, sy - 26, b, sy + 26), 6, fill=alpha(GRADES[k][3], 0.14))
            c.text(((a + b) / 2, sy - 40), GRADES[k][1], 12, "semibold", TEXT_2, anchor="mm")
        for b, lab in ((FANCY, "⅓"), (EXTRA1, "¼")):
            c.d.line((X(b), sy - 30, X(b), sy + 30), fill=alpha(TEXT_3, 0.9), width=1)
            c.text((X(b), sy + 42), lab, 11, "semibold", TEXT_3, anchor="mm")
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
    lot_name, lot_detail, _ = pb.verdict(pb.graded)
    summary = {"seconds": round(len(frames) / fps, 2), "counted": n, "graded": g,
               "per_minute": round(n / (len(frames) / fps) * 60), "duplicate_counts_dropped": pb.dropped,
               "track_pieces_stitched": pb.stitched, "gate_y": GATE_Y,
               "per_line": [sum(1 for _, _, ln in pb.counted if ln == k) for k in range(1, N_LINES + 1)],
               "standard": "USDA United States Standards for Grades of Peaches, 7 CFR 51.1210-51.1214 (2004), colour only",
               "colour_classes": [{"name": gr[0], "red_share_from": round(max(gr[2], 0.0), 3), "count": counts[k],
                                   "share": round(counts[k] / max(g, 1), 3)} for k, gr in enumerate(GRADES)],
               "lot_colour": {"meets": lot_name, "detail": lot_detail, "min_red_share": round(min(pb.share.values()), 3)},
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
