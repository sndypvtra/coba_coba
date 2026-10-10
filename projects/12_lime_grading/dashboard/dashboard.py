"""Lemon colour grading on two singulator chains, against the OECD colour chart, 1920 x 1080.

    python prepare.py                    # once: the clip
    python dashboard/detect.py           # once: detect, follow and read every lemon (~11 min)
    python dashboard/dashboard.py        # -> output/lime_grading.mp4
    python dashboard/dashboard.py --still 120 245

Two chains carry lemons away from the camera. A lemon is counted once, when its
box centre crosses the count gate, a horizontal line across both chains at
GATE_Y; the chain it is on (line 1 left, line 2 right) is where it crosses.

Its colour is graded on the external colour chart of the OECD standard for
citrus fruit (the one the CBI market-entry guide for lemons shows as Figure 2):
ten degrees, 1 fully yellow to 10 dark green. Degrees 1 to 9 are allowed in
Extra Class, Class I and Class II; degree 10 is out of grade. Within one
consignment only 3 adjacent degrees are allowed, so the line sorts the fruit
into colour lots of 3 degrees: 1-3, 4-6 and 7-9.

The degree comes from the skin's CIELAB hue angle, read inside the box on the
frames where it is sharpest, through a straight line fitted to the ten lemons of
the chart read the same way (SCALE). How well it agrees with matching the fruit
to the chart by eye is in output/lime_audit.json.
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
from ui import BG, CYAN, RED, SURFACE_2, TEXT, TEXT_2, TEXT_3, YELLOW, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "lime_chain.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
GATE_Y = 600              # count gate (source px): horizontal, across both chains
LINE_SPLIT = 800          # x on the gate between line 1 (left chain) and line 2 (right chain)
N_LINES = 2
MIN_AGE = 3               # frames a track must be held before it can be counted
MIN_CHROMA = 20           # a lemon is coloured; steel and rubber are not
DUP_FRAMES, DUP_PX = 1.5, 60  # two counts on one line this close are one lemon whose identity broke (touching lemons pass 3 frames apart)
CHIP_FRAMES = 10          # a counted lemon keeps its label this long after the gate (lemons move fast)
TREND_WIN = 2.0           # s: the trend is the lot mix of the lemons counted in the last 2 s
LIME = (132, 204, 22)
DEEP = (21, 128, 61)

# OECD external colour chart for lemons: the hue angle of the ten chart lemons, read like the video
# (skin pixels, CIELAB), is 86, 94, 100, 99, 103, 107, 113, 112, 116 and 124 deg for degrees 1 to 10.
# A straight line through them: hue = SCALE[0] + SCALE[1] * degree.
SCALE = (85.29, 3.630)
SWATCH = [(235, 187, 43), (216, 190, 64), (205, 191, 59), (194, 183, 59), (184, 180, 63), (169, 174, 66),
          (148, 164, 59), (135, 146, 60), (109, 124, 58), (79, 101, 50)]   # the chart's lemons, degree 1 to 10
# Colour lots of 3 adjacent degrees, as one consignment allows, and degree 10. (name, first, last, colour, looks)
LOTS = [
    ("Colour lot 1–3", 1, 3, YELLOW, "yellow"),
    ("Colour lot 4–6", 4, 6, LIME, "yellow-green"),
    ("Colour lot 7–9", 7, 9, DEEP, "green"),
    ("Out of Grade", 10, 10, RED, "degree 10 · too green"),
]


def degree_of(hue):
    return int(np.clip(round((hue - SCALE[0]) / SCALE[1]), 1, 10))


def lot_of(d):
    for k, lot in enumerate(LOTS):
        if lot[1] <= d <= lot[2]:
            return k
    return len(LOTS) - 1


class LemonBoard:
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
        # each lemon's hue: the median over the half of its frames where it is sharpest
        self.hue = {}
        for t, rs in reads.items():
            rs.sort(reverse=True)
            self.hue[t] = float(np.median([h for _, h in rs[:max(3, len(rs) // 2)]]))
        self.grey = {t for t, v in chroma.items() if np.median(v) < MIN_CHROMA}
        self.count()
        # the main lot: the colour lot most of the fruit belongs to; the rest is packed apart
        shares = [sum(1 for _, t, _ in self.counted if self.lot(t) == k) for k in range(3)]
        self.main = int(np.argmax(shares))
        self.thumbs = {}
        self.events = []
        for f, t, ln in self.counted:
            k = self.lot(t)
            if k == self.main:
                continue
            name = LOTS[k][0]
            detail = (f"colour {self.degree(t)} (OECD) · reject, out of grade" if k == 3 else
                      f"colour {self.degree(t)} (OECD) · pack apart from {LOTS[self.main][0].lower()}")
            self.events.append(B.Event(f, (f - 1) / self.fps, "high" if k == 3 else "low",
                                       "block" if k == 3 else "call_split", f"{name} · Line {ln}", detail, "lot",
                                       focus=self.box_at(t, f)))

    def box_at(self, t, f):
        """The lemon's box (picture coordinates) in the frame nearest to f where it was seen."""
        best = None
        for fr in self.tr["frames"]:
            for o in fr["objects"]:
                if o["tid"] == t and (best is None or abs(fr["frame"] - f) < abs(best[0] - f)):
                    best = (fr["frame"], o["box"])
        return [v * K for v in best[1]] if best else None

    def count(self):
        """One count per lemon, when its box centre crosses the gate going away from the camera."""
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

    def degree(self, t):
        return degree_of(self.hue[t])

    def lot(self, t):
        return lot_of(self.degree(t))

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
            ui.lock_box(img, [v * K for v in o["box"]], LOTS[self.lot(t)][3], 2, fill=0.12 if done else 0.0)
        ui.dashed(img, np.array([[0, gy], [B.VW, gy]]), CYAN, 2, 12, 6)
        c = ui.Canvas(img)
        c.pill((B.VW / 2, gy - 6), "Count gate · both lines", 11, (255, 255, 255), alpha(CYAN, 0.85), "semibold",
               icon="counter_1", pad=(8, 2), anchor="mb")
        # the ones outside the main lot on top: they are the ones the line has to act on
        for o in sorted(fr["objects"], key=lambda o: self.lot(o["tid"]) != self.main):
            t = o["tid"]
            if not 0 <= f - self.count_f.get(t, 10 ** 6) <= CHIP_FRAMES:
                continue
            col = LOTS[self.lot(t)][3]
            x0, y0 = o["box"][0] * K, o["box"][1] * K
            B.chip(c, (max(6, x0), y0 - 4), f"Line {self.line[t]} · Colour {self.degree(t)} ✓", col, None, anchor="lb",
                   size=11)
        n_line = [sum(1 for cf, _, ln in self.counted if ln == k and cf <= f) for k in range(1, N_LINES + 1)]
        c.pill((16, gy + 10), f"LINE 1 · {n_line[0]}", 12, (20, 24, 30), alpha(TEXT, 0.92), "bold", pad=(7, 3),
               anchor="lt", tnum=True)
        c.pill((B.VW - 16, gy + 10), f"LINE 2 · {n_line[1]}", 12, (20, 24, 30), alpha(TEXT, 0.92), "bold",
               pad=(7, 3), anchor="rt", tnum=True)
        B.corner_chips(c, "CAM 01 · Lemon sorting chains, 2 lines", [f"Counted: {sum(n_line)}", "Real footage"])
        c.rrect((8, B.VH - 38, 640, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", LOTS[0][3], "colour 1–3"), ("bar", LOTS[1][3], "colour 4–6"),
                                   ("bar", LOTS[2][3], "colour 7–9"), ("bar", LOTS[3][3], "10 · out of grade"),
                                   ("dot", TEXT, "✓ counted")], 12)
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
        tb = (B.BL[0] + 52, B.BL[1] + 56, B.BL[2] - 20, B.BL[3] - 44)
        series = self.trend(f)
        B.series_chart(img, tb, [(series[k], LOTS[k][3], k == self.main) for k in range(3)], self.n, 100)
        c = ui.Canvas(img)
        c.topbar("Produce Grading · lemon (OECD)", "Lemon sorting chains · Pexels footage", "Replay", t, self.total,
                 ["Real footage", "CAM 01"])
        self.kpis(c, done, t)
        self.mix(c, done)
        B.feed(c, self.events, t, self.thumbs, title="Event Log", unit="events", empty="No events yet")
        self.trend_card(c, tb, series)
        self.degree_strip(c, done)
        c.timeline(B.TL, t, self.total, self.events, title="Outside main lot")
        return c.bgr()

    def trend(self, f):
        """Share of each colour lot among the lemons counted in the last TREND_WIN s, frame by frame."""
        out = [[], [], []]
        w = TREND_WIN * self.fps
        for g in range(1, f + 1):
            win = [t for cf, t, _ in self.counted if g - w < cf <= g]
            for k in range(3):
                if len(win) < 2:
                    out[k].append(out[k][-1] if out[k] else 0.0)
                else:
                    out[k].append(100 * sum(1 for t in win if self.lot(t) == k) / len(win))
        return out

    def kpis(self, c, done, t):
        n = len(done)
        rate = n / t * 60 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[0], "nutrition", "Lemons counted", str(n),
              f"2 lines · ≈ {num(rate, 0)}/min, estimate from {num(t, 1)} s" if rate else "2 lines · count gate",
              LIME)
        ok = sum(1 for _, x, _ in done if self.degree(x) <= 9)
        c.kpi(B.KPI_BOXES[1], "verified", "Within colour standard", f"{num(100 * ok / n, 0)}%" if n else "–",
              "colour 1–9 · Extra, Class I, Class II" if n else "waiting for the first lemon", DEEP)
        m = sum(1 for _, x, _ in done if self.lot(x) == self.main)
        c.kpi(B.KPI_BOXES[2], "inventory_2", f"Main lot · colour {LOTS[self.main][1]}–{LOTS[self.main][2]}",
              f"{num(100 * m / n, 0)}%" if n else "–",
              f"{m} lemon{'' if m == 1 else 's'} · max 3 colour degrees per pack" if n else "waiting for the first lemon", LIME)
        bad = sum(1 for _, x, _ in done if self.degree(x) == 10)
        c.kpi(B.KPI_BOXES[3], "block", "Out of Grade", str(bad),
              f"{num(100 * bad / n, 0)}% · colour 10, reject" if bad else "none · no colour 10", RED,
              value_fill=RED if bad else TEXT)

    def mix(self, c, done):
        """How many lemons at each degree of the chart, the chart's own colours, the lots under them."""
        y = c.card_title(B.MID, "Grade Composition · OECD colour chart", "category", f"{len(done)} lemon{'' if len(done) == 1 else 's'}")
        x0, _, x1, y1 = B.MID
        cnt = [sum(1 for _, t, _ in done if self.degree(t) == d) for d in range(1, 11)]
        vmax = max(max(cnt), 1)
        gx0, gx1 = x0 + 24, x1 - 24
        bw = (gx1 - gx0) / 10
        base, top = y + 168, y + 26
        for d in range(10):
            bx = gx0 + d * bw
            h = (base - top) * cnt[d] / vmax
            c.rrect((bx + 6, base - max(h, 3), bx + bw - 6, base), 4, fill=SWATCH[d] if cnt[d] else SURFACE_2)
            c.text((bx + bw / 2, base - h - 12), str(cnt[d]), 13, "bold", TEXT, anchor="mm", tnum=True)
            c.text((bx + bw / 2, base + 14), str(d + 1), 12, "semibold", TEXT_2, anchor="mm")
        # the lots of 3 adjacent degrees, and degree 10 apart, past the limit the chart marks
        lx = gx0 + 9 * bw
        c.d.line((lx, top - 6, lx, base + 4), fill=alpha(RED, 0.9), width=1)
        c.text((lx - 4, top - 8), "limit", 10, "regular", RED, anchor="rb")
        for name, a, b, col, looks in LOTS:
            ax, bx_ = gx0 + (a - 1) * bw + 4, gx0 + b * bw - 4
            yy = base + 32
            c.rrect((ax, yy, bx_, yy + 4), 2, fill=col)
            share = sum(cnt[a - 1:b])
            label = name.replace("Colour lot ", "Lot ") if a < 10 else "Out of Grade"
            c.text(((ax + bx_) / 2, yy + 16), f"{label} · {share}", 11, "semibold", TEXT_2, anchor="mm", tnum=True)
        c.text((x0 + 16, y1 - 32), "Colour 1–9 allowed in Extra, Class I and Class II · colour 10 out of grade", 11,
               "regular", TEXT_3, anchor="lm")
        c.text((x0 + 16, y1 - 16), "One pack holds max 3 adjacent colour degrees · source: OECD Citrus Fruits", 11,
               "regular", TEXT_3, anchor="lm")

    def trend_card(self, c, tb, series):
        c.card_title(B.BL, "Colour lot trend", "monitoring", f"lot share, last {num(TREND_WIN, 0)} s")
        B.chart_axes(c, tb, 100, [0, 50, 100], self.total, xstep=1, fmt=lambda v: f"{v}%", xfmt=lambda s: f"{int(s)} s")
        x0, _, x1, y1 = B.BL
        c.legend((x0 + 16, y1 - 14), [("bar", LOTS[k][3], f"{LOTS[k][1]}–{LOTS[k][2]}  {num(series[k][-1], 0)}%")
                                      for k in range(3)], 12)

    def degree_strip(self, c, done):
        y = c.card_title(B.BR, "Colour degree spread", "palette", "OECD chart · 1 yellow, 10 dark green")
        x0, _, x1, y1 = B.BR
        sx0, sx1, sy = x0 + 30, x1 - 30, y + 66

        def X(d):
            return sx0 + (sx1 - sx0) * (min(max(d, 0.5), 10.5) - 0.5) / 10
        for d in range(1, 11):
            c.rrect((X(d - 0.5) + 1, sy - 24, X(d + 0.5) - 1, sy + 24), 4, fill=alpha(SWATCH[d - 1], 0.35))
            c.text((X(d), sy + 38), str(d), 10, "semibold", TEXT_3, anchor="mm")
        c.d.line((X(9.5), sy - 30, X(9.5), sy + 30), fill=alpha(RED, 0.9), width=2)
        rng = np.random.default_rng(3)
        for _, t, _ in done:
            col = LOTS[self.lot(t)][3]
            dd = (self.hue[t] - SCALE[0]) / SCALE[1]
            yy = sy + rng.uniform(-14, 14)
            xx = X(dd)
            c.dot((xx, yy), 6, col)
            c.d.ellipse((xx - 6, yy - 6, xx + 6, yy + 6), outline=ui.SURFACE + (255,), width=2)
        audit = OUT / "lime_audit.json"
        if audit.exists():
            c.text((x1 - 16, y1 - 16), json.loads(audit.read_text())["caption"], 11, "regular", TEXT_3, anchor="rm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    tr = json.loads((OUT / "tracks.json").read_text())
    frames, fps = B.read_video(VIDEO)
    lb = LemonBoard(tr, len(frames))
    n = len(lb.counted)
    deg = [sum(1 for _, t, _ in lb.counted if lb.degree(t) == d) for d in range(1, 11)]
    summary = {"seconds": round(len(frames) / fps, 2), "counted": n, "per_minute": round(n / (len(frames) / fps) * 60),
               "duplicate_counts_dropped": lb.dropped, "not_lemon_tracks": len(lb.grey), "gate_y": GATE_Y,
               "per_line": [sum(1 for _, _, ln in lb.counted if ln == k) for k in range(1, N_LINES + 1)],
               "scale": {"hue_at_degree": "hue = %.2f + %.3f * degree" % SCALE, "source": "OECD Citrus Fruits colour chart"},
               "degrees": {str(d): deg[d - 1] for d in range(1, 11)},
               "lots": [{"name": l[0], "degrees": [l[1], l[2]], "count": sum(deg[l[1] - 1:l[2]]),
                         "share": round(sum(deg[l[1] - 1:l[2]]) / max(n, 1), 3)} for l in LOTS],
               "main_lot": LOTS[lb.main][0],
               "lemons": [{"tid": t, "line": ln, "frame": f, "hue": round(lb.hue[t], 1), "degree": lb.degree(t),
                           "lot": LOTS[lb.lot(t)][0]} for f, t, ln in lb.counted]}
    (OUT / "lime_grading_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "lemons"}, ensure_ascii=False))
    if a.still is not None:
        if a.still:
            B.stills(lambda i: lb.draw(i, frames[i]), len(frames), set(a.still),
                     lambda f: OUT / f"lime_still_{f:04d}.jpg")
        return
    B.encode((lb.draw(i, f) for i, f in enumerate(frames)), OUT / "lime_grading.mp4", fps)
    print("video:", OUT / "lime_grading.mp4")


if __name__ == "__main__":
    main()
