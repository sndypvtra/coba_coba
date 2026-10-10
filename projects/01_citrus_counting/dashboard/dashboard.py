"""The citrus line as a packhouse manager reads it, 1920 x 1080.

    python dashboard/tracks.py               # once: detect, track, count (~8 min)
    python dashboard/dashboard.py            # -> output/citrus_flow.mp4
    python dashboard/dashboard.py --still 150 286

Counting is the project's own engine, unchanged (see tracks.py), with one rule
added: a fruit is counted once, even if the engine fires twice for an identity
that jitters on the line. A count alone tells a manager little; what a sizer is
run by is flow. So this adds how evenly the fruit arrives: the gap between
fruits at the counting line, the longest gap, and a warning while no fruit has
crossed for FEED_GAP_S seconds - a feed that is not keeping up, or a blocked
singulator. How many fruits are in view shows how full the belt is.

Lanes were tried and left out: with this camera's perspective and the short
paths fruit take through the frame, fruit from different channels extend to
the same point on the line, so a per-lane figure would have been wrong.
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
from ui import AMBER, BG, BLUE, CYAN, GREEN, ORANGE, RED, SLATE, SURFACE_2, TEXT, TEXT_2, TEXT_3, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "01_oranges_production_line.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
MIN_AGE = 4
FEED_GAP_S = 3.0         # no fruit across the line for this long is a feed gap


class CitrusBoard:
    def __init__(self, tr, n_frames):
        self.tr = tr
        self.fps = tr["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.board = ui.board(B.CARDS)
        self.thumbs = {}
        (ax, ay), (bx, by) = tr["line"]
        self.A, self.Bp = np.array([ax, ay], float), np.array([bx, by], float)
        self.line = [[ax * K, ay * K], [bx * K, by * K]]
        # one count per fruit: the engine can fire twice for an identity that jitters on the line
        self.counted, self.order = {}, []
        for c in tr["crossings"]:
            if c["tid"] not in self.counted:
                self.counted[c["tid"]] = c["frame"]
                self.order.append(c["tid"])
        self.double_fired = len(tr["crossings"]) - len(self.order)
        self.start = self.first_light()
        self.inview = [sum(1 for o in fr["objects"] if o["age"] >= MIN_AGE) for fr in tr["frames"]]
        self.events = self.make_events()

    # ---- flow --------------------------------------------------------------
    def crossings_until(self, f):
        return sorted(fr for fr in self.counted.values() if fr <= f)

    def gaps(self, f):
        cs = self.crossings_until(f)
        return [(b - a) / self.fps for a, b in zip(cs, cs[1:])]

    def since_last(self, f):
        cs = self.crossings_until(f)
        ref = cs[-1] if cs else self.start
        return (f - ref) / self.fps

    # ---- events ------------------------------------------------------------
    def make_events(self):
        ev = [B.Event(self.start, (self.start - 1) / self.fps, "info", "videocam", "Kamera aktif",
                      "rekaman dimulai dari layar gelap", "start", feed=False, focus=[0, 0, B.VW, B.VH])]
        in_gap = False
        for f in range(self.start, self.n + 1):
            gap = self.since_last(f)
            if gap >= FEED_GAP_S and not in_gap:
                in_gap = True
                ev.append(B.Event(f, (f - 1) / self.fps, "medium", "warning", "Celah pasokan buah",
                                  f"tidak ada jeruk lewat garis {num(FEED_GAP_S, 0)} s · cek pemasukan / singulator",
                                  "feed_gap", focus=[300, 200, 1000, 600]))
            if gap < 0.1:
                in_gap = False
        for tid in self.order:
            f = self.counted[tid]
            ev.append(B.Event(f, (f - 1) / self.fps, "info", "nutrition", f"Jeruk #{tid} terhitung",
                              ui.clock((f - 1) / self.fps), "counted", feed=False, focus=self.box_at(tid, f)))
        ev.sort(key=lambda e: e.frame)
        return ev

    def first_light(self):
        cap = cv2.VideoCapture(str(VIDEO))
        f = 0
        while True:
            ok, im = cap.read()
            if not ok:
                return 1
            f += 1
            if im.mean() > 25:
                return f

    def box_at(self, tid, frame):
        for o in self.tr["frames"][frame - 1]["objects"]:
            if o["tid"] == tid:
                return [v * K for v in o["box"]]
        return None

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        f = i + 1
        img = frame.copy()
        (ax, ay), (bx, by) = self.line
        cv2.line(img, (int(ax), int(ay)), (int(bx), int(by)), ui.bgr(CYAN), 2, cv2.LINE_AA)
        for o in self.tr["frames"][i]["objects"]:
            if o["age"] < MIN_AGE:
                continue
            done = o["tid"] in self.counted and self.counted[o["tid"]] <= f
            ui.lock_box(img, [v * K for v in o["box"]], GREEN if done else ORANGE, 2)
        c = ui.Canvas(img)
        c.pill(((ax + bx) / 2 + 30, min(ay, by) - 6), "Garis hitung", 11, (255, 255, 255), alpha(CYAN, 0.85),
               "semibold", icon="filter_center_focus", pad=(7, 2), anchor="mb")
        for o in self.tr["frames"][i]["objects"]:
            if o["age"] < MIN_AGE:
                continue
            done = o["tid"] in self.counted and self.counted[o["tid"]] <= f
            lab = f"#{o['tid']}" + (" ✓" if done else "")
            B.chip(c, (max(6, o["box"][0] * K), o["box"][1] * K - 4), lab, GREEN if done else ORANGE, None,
                   anchor="lb", size=11)
        n = sum(1 for t, fr in self.counted.items() if fr <= f)
        right = [f"Terhitung: {n}", "Rekaman nyata"]
        if f >= self.start and self.since_last(f) >= FEED_GAP_S:
            right.insert(0, f"Celah pasokan {num(self.since_last(f), 1)} s")
        B.corner_chips(c, "CAM 01 · Lini sortir jeruk", right)
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
        cb = (B.BR[0] + 44, B.BR[1] + 52, B.BR[2] - 20, B.BR[3] - 52)
        cum = [sum(1 for fr in self.counted.values() if fr <= j + 1) for j in range(i + 1)]
        inview = self.inview[:i + 1]
        ymax = max(4, max(max(cum), max(inview)) + 1)
        B.series_chart(img, cb, [(inview, ORANGE, True), (cum, GREEN, False)], self.n, ymax)
        c = ui.Canvas(img)
        c.topbar("Flow monitor · lini jeruk", "Lini sortir jeruk · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, f, t)
        self.flow_card(c, f)
        B.feed(c, self.events, t, self.thumbs)
        self.history(c, f)
        y = c.card_title(B.BR, "Buah di kamera dan terhitung", "monitoring", f"{cum[-1]} terhitung")
        B.chart_axes(c, cb, ymax, list(range(0, ymax + 1, 2 if ymax <= 10 else 5)), self.total)
        x0, _, x1, y1 = B.BR
        c.legend((x0 + 16, y1 - 16), [("bar", ORANGE, "buah di kamera"), ("bar", GREEN, "terhitung (kumulatif)")], 11)
        c.timeline(B.TL, t, self.total, self.events)
        return c.bgr()

    def kpis(self, c, f, t):
        done = [tid for tid in self.order if self.counted[tid] <= f]
        n = len(done)
        c.kpi(B.KPI_BOXES[0], "nutrition", "Jeruk terhitung", str(n), "lewat garis hitung · satu buah dihitung sekali",
              ORANGE)
        el = max(0.0, t - (self.start - 1) / self.fps)
        rate = n / el * 3600 if el > 1 and n else None
        c.kpi(B.KPI_BOXES[1], "speed", "Laju lini", f"{num(rate, 0)}/jam" if rate else "–",
              f"perkiraan dari {num(el, 1)} s rekaman" if rate else "menunggu buah pertama", CYAN)
        now = self.inview[f - 1]
        avg = float(np.mean(self.inview[self.start - 1:f])) if f >= self.start else 0
        c.kpi(B.KPI_BOXES[2], "view_module", "Buah di kamera", str(now), f"rata-rata {num(avg, 1)} · kepadatan belt",
              GREEN)
        g = self.gaps(f)
        gap_now = self.since_last(f) if f >= self.start else 0
        longest = max(g + [gap_now]) if f >= self.start else 0
        c.kpi(B.KPI_BOXES[3], "timer", "Celah terpanjang", f"{num(longest, 1)} s",
              f"jarak rata-rata {num(np.mean(g), 1)} s" if g else "jarak antar buah di garis hitung", AMBER,
              value_fill=AMBER if longest >= FEED_GAP_S else TEXT)

    def flow_card(self, c, f):
        g = self.gaps(f)
        y = c.card_title(B.MID, "Jarak antar jeruk di garis hitung", "timer", f"{len(g)} jarak terukur")
        x0, _, x1, y1 = B.MID
        top, bot = y + 30, y1 - 70
        lx0, lx1 = x0 + 50, x1 - 20
        vmax = max(5.0, max(g + [0]) + 0.5)
        for v in (0, FEED_GAP_S):
            yy = bot - (bot - top) * v / vmax
            c.d.line((lx0, yy, lx1, yy), fill=alpha(ui.BORDER, 0.9) if v == 0 else alpha(AMBER, 0.8), width=1)
            c.text((lx0 - 8, yy), f"{num(v, 0)} s", 11, "regular", TEXT_3, anchor="rm")
        c.text((lx1, bot - (bot - top) * FEED_GAP_S / vmax - 8), f"celah ≥ {num(FEED_GAP_S, 0)} s", 10, "medium",
               TEXT_2, anchor="rs")
        n = max(len(g), 6)
        bw = min(24, (lx1 - lx0) / n * 0.6)
        for k, v in enumerate(g):
            cx = lx0 + (lx1 - lx0) * (k + 0.5) / n
            h = (bot - top) * v / vmax
            col = AMBER if v >= FEED_GAP_S else ORANGE
            c.rrect((cx - bw / 2, bot - max(h, 3), cx + bw / 2, bot), 4, fill=col)
            c.text((cx, bot - h - 10), f"{num(v, 1)}", 11, "medium", TEXT, anchor="mm", tnum=True)
            c.text((cx, bot + 14), f"{k + 1}–{k + 2}", 10, "regular", TEXT_3, anchor="mm")
        if not g:
            c.text(((x0 + x1) / 2, (top + bot) / 2), "Butuh 2 jeruk terhitung", 13, "regular", TEXT_3, anchor="mm")
        msg = ""
        if len(g) >= 3:
            spread = max(g) / max(min(g), 0.05)
            msg = ("Pasokan tidak rata: buah datang berdempet lalu kosong lama." if spread > 5
                   else "Pasokan cukup rata.")
        c.text((x0 + 16, y1 - 38), msg, 13, "semibold", TEXT, anchor="lm")
        c.text((x0 + 16, y1 - 18), "Rata-ratakan pemasukan buah agar sizer terisi penuh tanpa berdempet", 11,
               "regular", TEXT_3, anchor="lm")

    def history(self, c, f):
        y = c.card_title(B.BL, "Jeruk terakhir terhitung", "history", "terbaru di kiri")
        x0, _, x1, y1 = B.BL
        done = [tid for tid in self.order if self.counted[tid] <= f]
        tw, gap = 78, 9
        x = x0 + 16
        for tid in list(reversed(done))[:7]:
            c.rrect((x, y + 2, x + tw, y1 - 14), 8, fill=SURFACE_2)
            c.rrect((x, y + 2, x + tw, y + 6), 2, fill=ORANGE)
            c.text((x + tw / 2, y + 24), f"#{tid}", 13, "semibold", TEXT, anchor="mm")
            c.dot((x + tw / 2, y + 62), 18, ORANGE)
            c.text((x + tw / 2, y + 108), ui.clock((self.counted[tid] - 1) / self.fps), 13, "medium", TEXT_2,
                   anchor="mm", tnum=True)
            x += tw + gap
        if not done:
            c.text(((x0 + x1) / 2, (y + y1) / 2), "Menunggu jeruk pertama melewati garis", 13, "regular", TEXT_3,
                   anchor="mm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    tr = json.loads((OUT / "tracks.json").read_text())
    frames, fps = B.read_video(VIDEO)
    cb = CitrusBoard(tr, len(frames))
    summary = {"counted": len(cb.order), "engine_crossings": len(tr["crossings"]),
               "repeat_crossings_dropped": cb.double_fired,
               "crossing_times_s": [round((cb.counted[t] - 1) / cb.fps, 2) for t in cb.order],
               "gaps_s": [round(g, 2) for g in cb.gaps(cb.n)], "mean_in_view": round(float(np.mean(cb.inview)), 2),
               "events": [{"t": round(e.t, 2), "title": e.title, "detail": e.detail} for e in cb.events]}
    (OUT / "citrus_flow_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps(summary, ensure_ascii=False)[:1500])
    if a.still is not None:
        if a.still:
            B.stills(lambda i: cb.draw(i, frames[i]), len(frames), set(a.still),
                     lambda f: OUT / f"citrus_still_{f:04d}.jpg")
        return
    B.encode((cb.draw(i, f) for i, f in enumerate(frames)), OUT / "citrus_flow.mp4", fps)
    print("video:", OUT / "citrus_flow.mp4")


if __name__ == "__main__":
    main()
