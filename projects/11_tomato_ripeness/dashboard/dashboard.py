"""Tomato ripeness per line, as a packhouse manager reads it, 1920 x 1080.

    python prepare.py                    # once: the clip
    python dashboard/detect.py           # once: detect, follow and read every tomato (~6 min)
    python dashboard/dashboard.py        # -> output/tomato_ripeness.mp4
    python dashboard/dashboard.py --still 60 133

Four lines carry tomatoes away from the camera. A tomato is counted once, when
its box centre crosses the count gate, a horizontal line across all four lines
at GATE_Y; the line it is on is where it crosses. Its ripeness is the colour of
its skin as a CIELAB hue angle, read on skin pixels inside its box on the frames
where it is sharpest, and sorted into three classes: ripe (red to orange-red),
half-ripe (pale orange with yellow) and unripe (yellow to green). Every tomato
not yet ripe goes in the event log with a snapshot at the gate. The class
bounds are in RIPENESS; how well they agree with grading by eye is in
output/tomato_audit.json.
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
from ui import AMBER, BG, CYAN, GREEN, RED, SURFACE_2, TEXT, TEXT_2, TEXT_3, alpha, num  # noqa: E402

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

# Ripeness by the hue angle of the skin (degrees): red ripe fruit sits lowest. The
# bounds were chosen on half of the tomatoes graded by eye and checked on the other
# half (output/tomato_audit.json). (name, upper hue bound, colour, what it looks like)
RIPENESS = [
    ("Matang", 62.5, RED, "merah sampai oranye-merah"),
    ("Setengah matang", 73.0, AMBER, "oranye pucat, ada bagian kuning"),
    ("Mentah", 999.0, GREEN, "kuning sampai hijau"),
]


def ripeness(hue):
    for k, r in enumerate(RIPENESS):
        if hue < r[1]:
            return k
    return len(RIPENESS) - 1


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
            self.hue.setdefault(t, 40.0)
        self.grey = {t for t, v in chroma.items() if np.median(v) < MIN_CHROMA}
        self.count()
        self.thumbs = {}
        # the event log: every tomato not yet ripe, with a snapshot at the gate
        self.events = [B.Event(f, (f - 1) / self.fps, "medium" if self.cls(t) == 2 else "low",
                               "eco" if self.cls(t) == 2 else "schedule", f"{RIPENESS[self.cls(t)][0]} · Line {ln}",
                               f"hue {num(self.hue[t], 1)}° · {RIPENESS[self.cls(t)][3]}", "not_ripe",
                               focus=self.box_at(t, f))
                       for f, t, ln in self.counted if self.cls(t) > 0]

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
        return ripeness(self.hue[t])

    def done(self, f):
        return [(cf, t, ln) for cf, t, ln in self.counted if cf <= f]

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        img = frame.copy()
        fr = self.tr["frames"][i]
        f = i + 1
        gy = GATE_Y * K
        age = {}
        for o in fr["objects"]:
            age[o["tid"]] = sum(1 for q in self.paths[o["tid"]] if q[0] <= f)
        for o in fr["objects"]:
            if age[o["tid"]] < MIN_AGE or o["tid"] in self.grey or (o["box"][1] + o["box"][3]) / 2 < DRAW_Y:
                continue
            col = RIPENESS[self.cls(o["tid"])][2]
            done = self.count_f.get(o["tid"], 10 ** 6) <= f
            ui.lock_box(img, [v * K for v in o["box"]], col, 2, fill=0.12 if done else 0.0)
        ui.dashed(img, np.array([[0, gy], [B.VW, gy]]), CYAN, 2, 12, 6)
        c = ui.Canvas(img)
        c.pill((16, gy - 6), "Gerbang hitung · semua line", 11, (255, 255, 255), alpha(CYAN, 0.85), "semibold",
               icon="counter_1", pad=(8, 2), anchor="lb")
        n_line = [sum(1 for cf, _, ln in self.counted if ln == k and cf <= f) for k in range(1, N_LINES + 1)]
        # the less ripe on top: an unripe tomato is the one the line has to act on
        for o in sorted(fr["objects"], key=lambda o: self.cls(o["tid"])):
            t = o["tid"]
            if not 0 <= f - self.count_f.get(t, 10 ** 6) <= CHIP_FRAMES or (o["box"][1] + o["box"][3]) / 2 < DRAW_Y:
                continue
            name, _, col, _ = RIPENESS[self.cls(t)]
            x0, y0 = o["box"][0] * K, o["box"][1] * K
            B.chip(c, (max(6, x0), y0 - 4), f"Line {self.line[t]} · {name} ✓", col, None, anchor="lb", size=11)
        for k in range(1, N_LINES + 1):
            if k in self.gate_x:
                c.pill((self.gate_x[k] * K, gy + 8), f"LINE {k} · {n_line[k - 1]}", 11, (20, 24, 30),
                       alpha(TEXT, 0.92), "bold", pad=(6, 2), anchor="mt", tnum=True)
        B.corner_chips(c, "CAM 01 · Lini packing tomat, 4 line", [f"Terhitung: {sum(n_line)}", "Rekaman nyata"])
        c.rrect((8, B.VH - 38, 520, B.VH - 8), 8, fill=alpha(BG, 0.75))
        c.legend((18, B.VH - 23), [("bar", RIPENESS[0][2], "matang"), ("bar", RIPENESS[1][2], "setengah matang"),
                                   ("bar", RIPENESS[2][2], "mentah"), ("dot", TEXT, "✓ terhitung")], 12)
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
        c.topbar("Kematangan · tomat per line", "Lini packing tomat · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, done, t)
        self.mix(c, done)
        B.feed(c, self.events, t, self.thumbs, title="Event Log", unit="events", empty="No events yet")
        self.history(c, done)
        self.hue_strip(c, done)
        c.timeline(B.TL, t, self.total, self.events, title="Tomat belum matang")
        return c.bgr()

    def kpis(self, c, done, t):
        n = len(done)
        rate = n / t * 60 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[0], "nutrition", "Tomat terhitung", str(n),
              f"4 line · ≈ {num(rate, 0)}/menit, perkiraan dari {num(t, 1)} s" if rate else "4 line · gerbang hitung",
              RED)
        cnt = [sum(1 for _, x, _ in done if self.cls(x) == k) for k in range(3)]
        c.kpi(B.KPI_BOXES[1], "check_circle", "Matang", f"{num(100 * cnt[0] / n, 0)}%" if n else "–",
              f"{cnt[0]} dari {n} tomat · merah sampai oranye-merah" if n else "menunggu tomat pertama", RED)
        c.kpi(B.KPI_BOXES[2], "schedule", "Setengah matang", f"{num(100 * cnt[1] / n, 0)}%" if n else "–",
              f"{cnt[1]} tomat · oranye pucat" if n else "menunggu tomat pertama", AMBER)
        c.kpi(B.KPI_BOXES[3], "eco", "Mentah", str(cnt[2]),
              f"{num(100 * cnt[2] / n, 0)}% · kuning sampai hijau" if cnt[2] else "belum ada tomat mentah", GREEN,
              value_fill=GREEN if cnt[2] else TEXT)

    def mix(self, c, done):
        y = c.card_title(B.MID, "Komposisi Grade", "category", f"{len(done)} tomat")
        x0, _, x1, y1 = B.MID
        counts = [sum(1 for _, t, _ in done if self.cls(t) == k) for k in range(3)]
        n = max(1, len(done))
        bx0, bx1, by = x0 + 16, x1 - 16, y + 14
        x = bx0
        for k, v in enumerate(counts):
            if v:
                w = (bx1 - bx0) * v / n
                c.rrect((x, by, x + w - 2, by + 18), 4, fill=RIPENESS[k][2])
                x += w
        if not done:
            c.rrect((bx0, by, bx1, by + 18), 4, fill=SURFACE_2)
        ry = by + 52
        lo = 0.0
        for k, (name, ub, col, looks) in enumerate(RIPENESS):
            c.dot((x0 + 24, ry), 6, col)
            c.text((x0 + 38, ry), name, 14, "semibold", TEXT, anchor="lm")
            rng = f"hue < {num(ub, 1).replace(',0', '')}°" if k == 0 else (
                f"hue ≥ {num(lo, 1).replace(',0', '')}°" if ub > 360 else
                f"hue {num(lo, 1).replace(',0', '')}–{num(ub, 1).replace(',0', '')}°")
            c.text((x0 + 38, ry + 22), f"{looks} · {rng}", 12, "regular", TEXT_2, anchor="lm")
            c.text((x1 - 16, ry), f"{counts[k]}", 20, "bold", TEXT, anchor="rm", tnum=True)
            c.text((x1 - 60, ry), f"{num(100 * counts[k] / n, 0)}%" if done else "–", 13, "medium", TEXT_2,
                   anchor="rm", tnum=True)
            lo = ub
            ry += 64
        c.text((x0 + 16, y1 - 18), "Kelas dari sudut hue warna kulit (CIELAB), dibaca di dalam kotak deteksi", 11,
               "regular", TEXT_3, anchor="lm")

    def history(self, c, done):
        y = c.card_title(B.BL, "Tomat terakhir terhitung", "history", "terbaru di kiri")
        x0, _, x1, y1 = B.BL
        tw, gap = 78, 9
        x = x0 + 16
        for _, t, ln in list(reversed(done))[:7]:
            name, _, col, _ = RIPENESS[self.cls(t)]
            c.rrect((x, y + 2, x + tw, y1 - 14), 8, fill=SURFACE_2)
            c.rrect((x, y + 2, x + tw, y + 6), 2, fill=col)
            c.text((x + tw / 2, y + 24), f"Line {ln}", 12, "semibold", TEXT, anchor="mm")
            c.dot((x + tw / 2, y + 62), 20, col)
            c.text((x + tw / 2, y + 100), f"{num(self.hue[t], 0)}°", 13, "medium", TEXT_2, anchor="mm", tnum=True)
            c.pill((x + tw / 2, y + 124), name.split()[0].lower(), 10, (255, 255, 255), alpha(col, 0.9), "semibold",
                   pad=(6, 2), anchor="mm")
            x += tw + gap
        if not done:
            c.text(((x0 + x1) / 2, (y + y1) / 2), "Menunggu tomat pertama melewati gerbang", 13, "regular", TEXT_3,
                   anchor="mm")

    def hue_strip(self, c, done):
        y = c.card_title(B.BR, "Sebaran warna tomat terhitung", "palette", "batas kelas di garis putus")
        x0, _, x1, y1 = B.BR
        lo, hi = 25.0, 85.0
        sx0, sx1, sy = x0 + 30, x1 - 30, y + 70

        def X(h):
            return sx0 + (sx1 - sx0) * (min(max(h, lo), hi) - lo) / (hi - lo)
        prev = lo
        for name, ub, col, _ in RIPENESS:
            ub_ = min(ub, hi)
            c.rrect((X(prev), sy - 26, X(ub_), sy + 26), 6, fill=alpha(col, 0.12))
            c.text(((X(prev) + X(ub_)) / 2, sy - 40), name, 12, "semibold", TEXT_2, anchor="mm")
            prev = ub_
        for ub in (RIPENESS[0][1], RIPENESS[1][1]):
            c.d.line((X(ub), sy - 30, X(ub), sy + 30), fill=alpha(TEXT_3, 0.9), width=1)
            c.text((X(ub), sy + 42), f"{num(ub, 1).replace(',0', '')}°", 10, "regular", TEXT_3, anchor="mm")
        rng = np.random.default_rng(3)
        for _, t, _ in done:
            col = RIPENESS[self.cls(t)][2]
            yy = sy + rng.uniform(-16, 16)
            c.dot((X(self.hue[t]), yy), 6, col)
            c.d.ellipse((X(self.hue[t]) - 6, yy - 6, X(self.hue[t]) + 6, yy + 6), outline=ui.SURFACE + (255,), width=2)
        c.text((sx0, sy + 42), f"{int(lo)}° merah", 10, "regular", TEXT_3, anchor="lm")
        c.text((sx1, sy + 42), f"{int(hi)}° hijau", 10, "regular", TEXT_3, anchor="rm")
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
    n = len(tb.counted)
    cnt = [sum(1 for _, t, _ in tb.counted if tb.cls(t) == k) for k in range(3)]
    summary = {"seconds": round(len(frames) / fps, 2), "counted": n, "per_minute": round(n / (len(frames) / fps) * 60),
               "not_tomato_tracks": len(tb.grey),
               "duplicate_counts_dropped": tb.dropped, "gate_y": GATE_Y,
               "per_line": [sum(1 for _, _, ln in tb.counted if ln == k) for k in range(1, N_LINES + 1)],
               "ripeness": [{"name": r[0], "hue_below": r[1], "looks": r[3], "count": cnt[k],
                             "share": round(cnt[k] / max(n, 1), 3)} for k, r in enumerate(RIPENESS)],
               "tomatoes": [{"tid": t, "line": ln, "frame": f, "hue": round(tb.hue[t], 1),
                             "ripeness": RIPENESS[tb.cls(t)][0]} for f, t, ln in tb.counted]}
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
