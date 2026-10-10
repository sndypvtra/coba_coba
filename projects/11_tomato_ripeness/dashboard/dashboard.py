"""Tomato colour classes per line on the USDA scale, as a packhouse manager reads it, 1920 x 1080.

    python prepare.py                    # once: the clip
    python dashboard/detect.py           # once: detect, follow and read every tomato (~6 min)
    python dashboard/dashboard.py        # -> output/tomato_ripeness.mp4
    python dashboard/dashboard.py --still 60 133

Four lines carry tomatoes away from the camera. A tomato is counted once, when
its box centre crosses the count gate, a horizontal line across all four lines
at GATE_Y; the line it is on is where it crosses.

Each tomato gets a colour class of the USDA standards for fresh tomatoes
(7 CFR 51.1860): Green, Breakers, Turning, Pink, Light Red, Red. The class comes
from the hue angle of its skin (CIELAB), read on skin pixels inside its box on
the frames where it is sharpest. The class bounds are the midpoints between the
mean hue angles a colorimeter study measured on tomatoes classed on the USDA
scale (Lopez-Camelo and Gomez 2004, Table 1): 113.3, 109.1, 93.2, 78.1, 64.9 and
59.3 deg from Green to Red.

A lot labelled with a colour class may hold at most 10 % off-colour tomatoes,
of which at most 5 % green (7 CFR 51.1861); the UNECE standard for tomatoes
(FFV-36) also asks for practically uniform colouring in Extra Class and Class I.
So the dashboard checks the lot against its main class: off-colour share
against the 10 % limit, green share against the 5 % limit, and every
off-colour tomato goes in the event log.
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
from ui import AMBER, BG, CYAN, GREEN, RED, SURFACE_2, TEXT, TEXT_2, TEXT_3, YELLOW, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "tomato_lanes.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
GATE_Y = 600                          # count gate (source px): horizontal, across all four lines
LINE_BOUNDS = [700, 1200, 1700]       # x on the gate between lines 1|2|3|4, from where tracks cross it
N_LINES = 4
MIN_AGE = 3                           # frames a track must be held before it can be counted
MIN_CHROMA = 20                       # a tomato is coloured; the belt, gloves and steel are not (tomatoes >= 25, rest <= 16)
DRAW_Y = 330                          # boxes are drawn below the crossbar; beyond it the fruit is too small to read
CHIP_FRAMES = 20                      # a counted tomato keeps its label this long after the gate
DUP_FRAMES, DUP_PX = 4, 60            # two counts on one line this close are one tomato whose identity broke
OFF_COLOUR_LIMIT = 0.10               # 7 CFR 51.1861: at most 10 % of a lot may fail the colour specified...
GREEN_LIMIT = 0.05                    # ...of which at most 5 % green

# USDA colour classes, red first. Mean hue angle per class from Lopez-Camelo and Gomez (2004), Table 1;
# a class runs from the midpoint with the class before it to the midpoint with the class after it.
# (name, mean hue, colour on screen, what the USDA standard says of the surface)
USDA = [
    ("Red", 59.3, (220, 38, 38), "> 90% red"),
    ("Light Red", 64.9, (248, 113, 113), "> 60% pinkish-red or red, ≤ 90% red"),
    ("Pink", 78.1, (244, 114, 182), "30–60% pink or red"),
    ("Turning", 93.2, (251, 146, 60), "10–30% changed from green"),
    ("Breakers", 109.1, YELLOW, "≤ 10% changed from green"),
    ("Green", 113.3, GREEN, "fully green surface"),
]
BOUNDS = [(USDA[k][1] + USDA[k + 1][1]) / 2 for k in range(len(USDA) - 1)]   # 62.1, 71.5, 85.7, 101.2, 111.2


def usda_class(hue):
    return int(np.searchsorted(BOUNDS, hue))


class TomatoBoard:
    def __init__(self, tr, n_frames):
        self.tr = tr
        self.fps = tr["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.board = ui.board(B.CARDS)
        self.paths, reads, chroma = {}, {}, {}
        for fr in tr["frames"]:
            for o in fr["objects"]:
                chroma.setdefault(o["tid"], []).append(o["chroma"])
                b = o["box"]
                self.paths.setdefault(o["tid"], []).append((fr["frame"], (b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
                if o["hue"] is not None:
                    reads.setdefault(o["tid"], []).append((o["sharp"], o["hue"]))
        # each tomato's hue: the median over the half of its frames where it is sharpest
        self.hue = {}
        for t, rs in reads.items():
            rs.sort(reverse=True)
            self.hue[t] = float(np.median([h for _, h in rs[:max(3, len(rs) // 2)]]))
        for t in self.paths:
            self.hue.setdefault(t, USDA[0][1])
        self.grey = {t for t, v in chroma.items() if np.median(v) < MIN_CHROMA}
        self.count()
        # the lot's main class: the one most tomatoes in it meet; every other tomato is off-colour for that label
        cnt = [sum(1 for _, t, _ in self.counted if self.cls(t) == k) for k in range(len(USDA))]
        self.main = int(np.argmax(cnt))
        self.thumbs = {}
        self.events = []
        for f, t, ln in self.counted:
            k = self.cls(t)
            if k == self.main:
                continue
            green = k == len(USDA) - 1
            self.events.append(B.Event(
                f, (f - 1) / self.fps, "high" if green else "low", "eco" if green else "call_split",
                f"{USDA[k][0]} · Line {ln}", f"hue {num(self.hue[t], 1)}° · off-colour for lot {USDA[self.main][0]}",
                "off_colour", focus=self.box_at(t, f)))

    def box_at(self, t, f):
        """The tomato's box (picture coordinates) in the frame nearest to f where it was seen."""
        best = None
        for fr in self.tr["frames"]:
            for o in fr["objects"]:
                if o["tid"] == t and (best is None or abs(fr["frame"] - f) < abs(best[0] - f)):
                    best = (fr["frame"], o["box"])
        return [v * K for v in best[1]] if best else None

    def count(self):
        """One count per tomato, when its box centre crosses the gate going away from the camera."""
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
            hits[int(np.searchsorted(LINE_BOUNDS, xx)) + 1].append((ff, t, xx))
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
        self.gate_x = {ln: float(np.median([h[2] for h in v])) for ln, v in hits.items() if v}

    def cls(self, t):
        return usda_class(self.hue[t])

    def done(self, f):
        return [(cf, t, ln) for cf, t, ln in self.counted if cf <= f]

    def lot(self, done):
        """Off-colour and green shares of the tomatoes so far, against the lot's main class."""
        n = len(done)
        off = sum(1 for _, t, _ in done if self.cls(t) != self.main)
        green = sum(1 for _, t, _ in done if self.cls(t) == len(USDA) - 1)
        return n, off, green

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        img = frame.copy()
        fr = self.tr["frames"][i]
        f = i + 1
        gy = GATE_Y * K
        age = {o["tid"]: sum(1 for q in self.paths[o["tid"]] if q[0] <= f) for o in fr["objects"]}
        for o in fr["objects"]:
            if age[o["tid"]] < MIN_AGE or o["tid"] in self.grey or (o["box"][1] + o["box"][3]) / 2 < DRAW_Y:
                continue
            done = self.count_f.get(o["tid"], 10 ** 6) <= f
            ui.lock_box(img, [v * K for v in o["box"]], USDA[self.cls(o["tid"])][2], 2, fill=0.12 if done else 0.0)
        ui.dashed(img, np.array([[0, gy], [B.VW, gy]]), CYAN, 2, 12, 6)
        c = ui.Canvas(img)
        c.pill((16, gy - 6), "Count gate · all lines", 11, (255, 255, 255), alpha(CYAN, 0.85), "semibold",
               icon="counter_1", pad=(8, 2), anchor="lb")
        n_line = [sum(1 for cf, _, ln in self.counted if ln == k and cf <= f) for k in range(1, N_LINES + 1)]
        # off-colour on top: it is the one the line has to act on
        for o in sorted(fr["objects"], key=lambda o: self.cls(o["tid"]) != self.main):
            t = o["tid"]
            if not 0 <= f - self.count_f.get(t, 10 ** 6) <= CHIP_FRAMES or (o["box"][1] + o["box"][3]) / 2 < DRAW_Y:
                continue
            name, _, col, _ = USDA[self.cls(t)]
            x0, y0 = o["box"][0] * K, o["box"][1] * K
            B.chip(c, (max(6, x0), y0 - 4), f"Line {self.line[t]} · {name} ✓", col, None, anchor="lb", size=11)
        for k in range(1, N_LINES + 1):
            if k in self.gate_x:
                c.pill((self.gate_x[k] * K, gy + 8), f"LINE {k} · {n_line[k - 1]}", 11, (20, 24, 30),
                       alpha(TEXT, 0.92), "bold", pad=(6, 2), anchor="mt", tnum=True)
        B.corner_chips(c, "CAM 01 · Tomato packing line, 4 lines", [f"Counted: {sum(n_line)}", "Real footage"])
        c.rrect((8, B.VH - 38, 700, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", u[2], u[0]) for u in USDA] + [("dot", TEXT, "✓ counted")], 12)
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
        off_s = self.off_series(f)
        ymax = max(40.0, max(off_s) * 1.15 if off_s else 0)
        B.series_chart(img, tb, [(off_s, AMBER, True), ([100 * OFF_COLOUR_LIMIT] * len(off_s), RED, False)],
                       self.n, ymax)
        c = ui.Canvas(img)
        c.topbar("Produce Grading · tomato (USDA)", "Tomato packing line · Pexels footage", "Replay", t, self.total,
                 ["Real footage", "CAM 01"])
        self.kpis(c, done, t)
        self.mix(c, done)
        B.feed(c, self.events, t, self.thumbs, title="Event Log", unit="events", empty="No events yet")
        self.off_card(c, tb, off_s, ymax)
        self.hue_strip(c, done)
        c.timeline(B.TL, t, self.total, self.events, title="Off-colour")
        return c.bgr()

    def off_series(self, f):
        """Off-colour share of the lot so far, frame by frame, once a few tomatoes are in."""
        out = []
        for g in range(1, f + 1):
            n, off, _ = self.lot(self.done(g))
            out.append(100 * off / n if n >= 5 else (out[-1] if out else 0.0))
        return out

    def kpis(self, c, done, t):
        n, off, green = self.lot(done)
        rate = n / t * 60 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[0], "nutrition", "Tomatoes counted", str(n),
              f"4 lines · ≈ {num(rate, 0)}/min, estimate from {num(t, 1)} s" if rate else "4 lines · count gate", RED)
        main = USDA[self.main]
        share = (n - off) / n if n else 0
        c.kpi(B.KPI_BOXES[1], "verified", f"Main colour class · {main[0]}", f"{num(100 * share, 0)}%" if n else "–",
              f"{n - off} of {n} · {main[3]}" if n else "waiting for the first tomato", main[2])
        over = n >= 5 and off / n > OFF_COLOUR_LIMIT
        c.kpi(B.KPI_BOXES[2], "rule", "Off-colour", f"{num(100 * off / n, 0)}%" if n else "–",
              ("over the 10% limit · re-sort, or label Mixed Color" if over else "within the 10% limit (USDA)") if n
              else "10% limit per lot (USDA)", AMBER, value_fill=AMBER if over else TEXT)
        g_over = n >= 5 and green / n > GREEN_LIMIT
        c.kpi(B.KPI_BOXES[3], "eco", "Green in lot", str(green),
              f"{num(100 * green / n, 0)}% · limit 5% (USDA)" if n else "5% limit per lot (USDA)", GREEN,
              value_fill=RED if g_over else TEXT)

    def mix(self, c, done):
        """How many tomatoes in each USDA colour class, and whether the lot may carry its main class's label."""
        n, off, green = self.lot(done)
        y = c.card_title(B.MID, "Grade Composition · USDA colour classes", "category", f"{n} tomatoes")
        x0, _, x1, y1 = B.MID
        cnt = [sum(1 for _, t, _ in done if self.cls(t) == k) for k in range(len(USDA))]
        vmax = max(max(cnt), 1)
        gx0, gx1 = x0 + 20, x1 - 20
        bw = (gx1 - gx0) / len(USDA)
        base, top = y + 150, y + 24
        for k, (name, _, col, _) in enumerate(USDA):
            bx = gx0 + k * bw
            h = (base - top) * cnt[k] / vmax
            c.rrect((bx + 10, base - max(h, 3), bx + bw - 10, base), 4, fill=col if cnt[k] else SURFACE_2)
            c.text((bx + bw / 2, base - h - 12), str(cnt[k]), 13, "bold", TEXT, anchor="mm", tnum=True)
            c.text((bx + bw / 2, base + 14), name, 12, "semibold", TEXT_2, anchor="mm")
            c.text((bx + bw / 2, base + 30), f"{num(100 * cnt[k] / n, 0)}%" if n else "–", 11, "regular", TEXT_3,
                   anchor="mm", tnum=True)
        # the lot label check: may this lot be labelled with its main class?
        main = USDA[self.main][0]
        ok = n < 5 or off / n <= OFF_COLOUR_LIMIT
        ly = base + 58
        c.rrect((x0 + 16, ly, x1 - 16, ly + 40), 8, fill=alpha(GREEN if ok else AMBER, 0.12))
        c.icon("check_circle" if ok else "warning", (x0 + 36, ly + 20), 18, GREEN if ok else AMBER)
        msg = (f"Lot label: {main} · off-colour {num(100 * off / n, 0)}% ≤ 10%" if ok and n else
               f"Lot label: Mixed Color · off-colour {num(100 * off / n, 0)}% > 10%, re-sort to label {main}"
               if n else "Lot label: waiting for the first tomato")
        c.text((x0 + 54, ly + 20), c.fit(msg, 13, "semibold", x1 - x0 - 80), 13, "semibold", TEXT, anchor="lm")
        c.text((x0 + 16, y1 - 16), "Source: USDA 7 CFR 51.1860–51.1861 · UNECE FFV-36 (uniform colour for Extra/Class I)",
               11, "regular", TEXT_3, anchor="lm")

    def off_card(self, c, tb, off_s, ymax):
        c.card_title(B.BL, "Off-colour trend", "monitoring", "off-colour share of the lot · limit 10%")
        step = 10 if ymax <= 60 else 20
        B.chart_axes(c, tb, ymax, list(range(0, int(ymax) + 1, step)), self.total, xstep=1,
                     fmt=lambda v: f"{v}%", xfmt=lambda s: f"{int(s)} s")
        x0, _, x1, y1 = B.BL
        c.legend((x0 + 16, y1 - 14), [("bar", AMBER, f"Off-colour {num(off_s[-1], 0)}%"),
                                      ("bar", RED, "USDA limit 10%")], 12)

    def hue_strip(self, c, done):
        y = c.card_title(B.BR, "Colour spread · hue angle", "palette", "USDA class bounds dashed")
        x0, _, x1, y1 = B.BR
        lo, hi = 40.0, 120.0
        sx0, sx1, sy = x0 + 30, x1 - 30, y + 70

        def X(h):
            return sx0 + (sx1 - sx0) * (min(max(h, lo), hi) - lo) / (hi - lo)
        edges = [lo] + BOUNDS + [hi]
        for k, (name, mean, col, _) in enumerate(USDA):
            a, b = X(edges[k]), X(edges[k + 1])
            c.rrect((a + 1, sy - 26, b - 1, sy + 26), 6, fill=alpha(col, 0.14))
            label = {"Light Red": "L. Red", "Breakers": "Brk"}.get(name, name)
            c.text(((a + b) / 2, sy - 40), label, 11, "semibold", TEXT_2, anchor="mm")
        for bd in BOUNDS:
            c.d.line((X(bd), sy - 30, X(bd), sy + 30), fill=alpha(TEXT_3, 0.9), width=1)
            c.text((X(bd), sy + 42), f"{num(bd, 1)}°", 10, "regular", TEXT_3, anchor="mm")
        rng = np.random.default_rng(3)
        for _, t, _ in done:
            col = USDA[self.cls(t)][2]
            yy = sy + rng.uniform(-16, 16)
            xx = X(self.hue[t])
            c.dot((xx, yy), 6, col)
            c.d.ellipse((xx - 6, yy - 6, xx + 6, yy + 6), outline=ui.SURFACE + (255,), width=2)
        audit = OUT / "tomato_audit.json"
        if audit.exists():
            c.text((x1 - 16, y1 - 16), json.loads(audit.read_text())["caption"], 11, "regular", TEXT_3, anchor="rm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    tr = json.loads((OUT / "tracks.json").read_text())
    frames, fps = B.read_video(VIDEO)
    tb = TomatoBoard(tr, len(frames))
    n, off, green = tb.lot(tb.counted)
    cnt = [sum(1 for _, t, _ in tb.counted if tb.cls(t) == k) for k in range(len(USDA))]
    summary = {"seconds": round(len(frames) / fps, 2), "counted": n, "per_minute": round(n / (len(frames) / fps) * 60),
               "not_tomato_tracks": len(tb.grey), "duplicate_counts_dropped": tb.dropped, "gate_y": GATE_Y,
               "per_line": [sum(1 for _, _, ln in tb.counted if ln == k) for k in range(1, N_LINES + 1)],
               "usda_classes": [{"name": u[0], "mean_hue_reference": u[1], "count": cnt[k],
                                 "share": round(cnt[k] / max(n, 1), 3)} for k, u in enumerate(USDA)],
               "class_bounds_deg": [round(b, 2) for b in BOUNDS],
               "lot": {"main_class": USDA[tb.main][0], "off_colour": off, "off_colour_share": round(off / max(n, 1), 3),
                       "green": green, "label": USDA[tb.main][0] if off / max(n, 1) <= OFF_COLOUR_LIMIT else "Mixed Color"},
               "tomatoes": [{"tid": t, "line": ln, "frame": f, "hue": round(tb.hue[t], 1),
                             "usda_class": USDA[tb.cls(t)][0]} for f, t, ln in tb.counted]}
    (OUT / "tomato_ripeness_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "tomatoes"}, ensure_ascii=False))
    if a.still is not None:
        if a.still:
            B.stills(lambda i: tb.draw(i, frames[i]), len(frames), set(a.still),
                     lambda f: OUT / f"tomato_still_{f:04d}.jpg")
        return
    B.encode((tb.draw(i, f) for i, f in enumerate(frames)), OUT / "tomato_ripeness.mp4", fps)
    print("video:", OUT / "tomato_ripeness.mp4")


if __name__ == "__main__":
    main()
