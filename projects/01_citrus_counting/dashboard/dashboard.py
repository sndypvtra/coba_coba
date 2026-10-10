"""The citrus line as a packhouse manager reads it, 1920 x 1080.

    python dashboard/tracks.py               # once: detect, track, count (~8 min)
    python dashboard/dashboard.py            # -> output/citrus_flow.mp4
    python dashboard/dashboard.py --still 150 286

Counting is the project's own engine, unchanged (see tracks.py). A count alone
tells a manager little; what a sizer is run by is flow, lane by lane. So this
adds the lanes: every track's path is extended to the counting line, where it
lands says which lane carried it, and the lanes are found by where the paths
cluster. From that: fruit per lane, how evenly the lanes are fed, and how long
each lane has gone without fruit - an empty lane is a blocked singulator or a
feed that is not keeping up.
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
LANE_GAP = 0.06          # tracks landing this far apart on the line are on different lanes
EMPTY_WARN_S = 3.0       # a lane with no fruit for this long is flagged


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
        self.counted = {c["tid"]: c["frame"] for c in tr["crossings"]}
        self.order = [c["tid"] for c in tr["crossings"]]
        self.paths = {}
        for fr in tr["frames"]:
            for o in fr["objects"]:
                if o["age"] >= MIN_AGE:
                    x0, y0, x1, y1 = o["box"]
                    self.paths.setdefault(o["tid"], []).append((fr["frame"], (x0 + x1) / 2, (y0 + y1) / 2))
        self.s = {tid: self.landing(p) for tid, p in self.paths.items() if len(p) >= 6}
        self.s = {k: v for k, v in self.s.items() if v is not None}
        self.lanes = self.find_lanes()
        self.lane_of = {tid: self.lane_for(s) for tid, s in self.s.items()}
        self.events = self.make_events()

    # ---- lanes -------------------------------------------------------------
    def landing(self, path):
        """Where a track's straight-line path meets the counting line, 0..1 along it."""
        pts = np.array([(x, y) for _, x, y in path])
        c = pts.mean(0)
        u, s_, vt = np.linalg.svd(pts - c)
        d = vt[0]
        e = self.Bp - self.A
        m = np.array([[d[0], -e[0]], [d[1], -e[1]]])
        if abs(np.linalg.det(m)) < 1e-6:
            return None
        t, s = np.linalg.solve(m, self.A - c)
        return float(s) if -0.1 <= s <= 1.1 else None

    def find_lanes(self):
        vals = sorted(self.s.values())
        groups = [[vals[0]]] if vals else []
        for v in vals[1:]:
            if v - groups[-1][-1] > LANE_GAP:
                groups.append([v])
            else:
                groups[-1].append(v)
        return [float(np.median(g)) for g in groups if len(g) >= 2]

    def lane_for(self, s):
        if not self.lanes:
            return None
        k = int(np.argmin([abs(s - c) for c in self.lanes]))
        return k if abs(s - self.lanes[k]) <= LANE_GAP * 1.5 else None

    def lane_point(self, k):
        p = self.A + (self.Bp - self.A) * self.lanes[k]
        return p * K

    def lane_state(self, f):
        """Per lane: fruit seen so far, and seconds since fruit was last on it."""
        last = {k: None for k in range(len(self.lanes))}
        seen = {k: set() for k in range(len(self.lanes))}
        for tid, path in self.paths.items():
            k = self.lane_of.get(tid)
            if k is None:
                continue
            fr = [p[0] for p in path if p[0] <= f]
            if fr:
                seen[k].add(tid)
                last[k] = max(last[k] or 0, max(fr))
        idle = {k: ((f - last[k]) / self.fps if last[k] else f / self.fps) for k in last}
        return seen, idle

    # ---- events ------------------------------------------------------------
    def make_events(self):
        ev = []
        start = self.first_light()
        ev.append(B.Event(start, (start - 1) / self.fps, "info", "videocam", "Kamera aktif",
                          "rekaman dimulai dari layar gelap", "start", feed=False, focus=[0, 0, B.VW, B.VH]))
        warned = set()
        for f in range(start, self.n + 1):
            seen, idle = self.lane_state(f)
            for k, s in idle.items():
                if s >= EMPTY_WARN_S and k not in warned and (f - start) / self.fps >= EMPTY_WARN_S:
                    warned.add(k)
                    p = self.lane_point(k)
                    ev.append(B.Event(f, (f - 1) / self.fps, "medium", "warning", f"Lajur {k + 1} kosong",
                                      f"tidak ada buah {num(s, 0)} s · cek singulator / suplai", "lane_empty",
                                      focus=[p[0] - 160, p[1] - 90, p[0] + 160, p[1] + 90]))
                if k in warned and s < 0.5:
                    warned.discard(k)
        for tid in self.order:
            f = self.counted[tid]
            k = self.lane_of.get(tid)
            box = self.box_at(tid, f)
            ev.append(B.Event(f, (f - 1) / self.fps, "info", "nutrition", f"Jeruk #{tid} terhitung",
                              f"lajur {k + 1}" if k is not None else "lajur tak pasti", "counted", feed=False,
                              focus=box))
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
        seen, idle = self.lane_state(f)
        for o in self.tr["frames"][i]["objects"]:
            if o["age"] < MIN_AGE:
                continue
            done = o["tid"] in self.counted and self.counted[o["tid"]] <= f
            ui.lock_box(img, [v * K for v in o["box"]], GREEN if done else ORANGE, 2)
        c = ui.Canvas(img)
        for k in range(len(self.lanes)):
            x, y = self.lane_point(k)
            bad = idle[k] >= EMPTY_WARN_S
            c.pill((x + 10, y), f"L{k + 1}", 11, (255, 255, 255), alpha(AMBER if bad else CYAN, 0.9), "bold",
                   pad=(6, 2), anchor="lm")
        c.pill(((ax + bx) / 2 + 30, min(ay, by) - 6), "Garis hitung", 11, (255, 255, 255), alpha(CYAN, 0.85),
               "semibold", icon="filter_center_focus", pad=(7, 2), anchor="mb")
        for o in self.tr["frames"][i]["objects"]:
            if o["age"] < MIN_AGE:
                continue
            done = o["tid"] in self.counted and self.counted[o["tid"]] <= f
            k = self.lane_of.get(o["tid"])
            lab = f"#{o['tid']}" + (f" · L{k + 1}" if k is not None else "") + (" ✓" if done else "")
            B.chip(c, (max(6, o["box"][0] * K), o["box"][1] * K - 4), lab, GREEN if done else ORANGE, None,
                   anchor="lb", size=11)
        n = sum(1 for t, fr in self.counted.items() if fr <= f)
        B.corner_chips(c, "CAM 01 · Lini sortir jeruk", [f"Terhitung: {n}", "Rekaman nyata"])
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
        inview = [sum(1 for o in self.tr["frames"][j]["objects"] if o["age"] >= MIN_AGE) for j in range(i + 1)]
        ymax = max(4, max(max(cum), max(inview)) + 1)
        B.series_chart(img, cb, [(inview, ORANGE, True), (cum, GREEN, False)], self.n, ymax)
        c = ui.Canvas(img)
        c.topbar("Flow monitor · lini jeruk", "Lini sortir jeruk · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, f, t)
        self.lanes_card(c, f)
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
        c.kpi(B.KPI_BOXES[0], "nutrition", "Jeruk terhitung", str(n), "lewat garis hitung", ORANGE)
        t0 = (self.first_light() - 1) / self.fps
        el = max(0.0, t - t0)
        rate = n / el * 3600 if el > 1 and n else None
        c.kpi(B.KPI_BOXES[1], "speed", "Laju lini", f"{num(rate, 0)}/jam" if rate else "–",
              f"perkiraan dari {num(el, 1)} s rekaman" if rate else "menunggu buah pertama", CYAN)
        seen, idle = self.lane_state(f)
        active = sum(1 for k in idle if idle[k] < EMPTY_WARN_S)
        c.kpi(B.KPI_BOXES[2], "view_module", "Lajur terisi", f"{active}/{len(self.lanes)}",
              "ada buah dalam 3 s terakhir", GREEN, value_fill=TEXT if active == len(self.lanes) else AMBER)
        gaps = [(b - a) / self.fps for a, b in zip(sorted(self.counted.values()), sorted(self.counted.values())[1:])
                if b <= f]
        c.kpi(B.KPI_BOXES[3], "timer", "Jarak antar buah", f"{num(np.mean(gaps), 1)} s" if gaps else "–",
              "rata-rata di garis hitung" if gaps else "butuh 2 buah terhitung", AMBER)

    def lanes_card(self, c, f):
        seen, idle = self.lane_state(f)
        y = c.card_title(B.MID, "Pasokan per lajur", "view_module", f"{len(self.lanes)} lajur terbaca")
        x0, _, x1, y1 = B.MID
        n = max(1, max((len(v) for v in seen.values()), default=1))
        rh = min(44, (y1 - y - 60) // max(1, len(self.lanes)))
        ry = y + 14
        for k in range(len(self.lanes)):
            bad = idle[k] >= EMPTY_WARN_S
            c.text((x0 + 16, ry + rh / 2), f"Lajur {k + 1}", 13, "semibold", TEXT, anchor="lm")
            bx0, bx1 = x0 + 100, x1 - 190
            c.rrect((bx0, ry + rh / 2 - 7, bx1, ry + rh / 2 + 7), 4, fill=SURFACE_2)
            w = (bx1 - bx0) * len(seen[k]) / n
            if w > 2:
                c.rrect((bx0, ry + rh / 2 - 7, bx0 + w, ry + rh / 2 + 7), 4, fill=ORANGE)
            c.text((bx1 + 12, ry + rh / 2), f"{len(seen[k])} buah", 12, "medium", TEXT_2, anchor="lm", tnum=True)
            c.pill((x1 - 16, ry + rh / 2), f"kosong {num(idle[k], 0)} s" if bad else "mengalir", 10,
                   (255, 255, 255), alpha(AMBER if bad else GREEN, 0.9), "semibold", pad=(7, 2), anchor="rm")
            ry += rh
        c.text((x0 + 16, y1 - 18), f"Lajur dari lintasan tiap buah · kosong ≥ {num(EMPTY_WARN_S, 0)} s ditandai",
               11, "regular", TEXT_3, anchor="lm")

    def history(self, c, f):
        y = c.card_title(B.BL, "Jeruk terakhir terhitung", "history", "terbaru di kiri")
        x0, _, x1, y1 = B.BL
        done = [tid for tid in self.order if self.counted[tid] <= f]
        tw, gap = 78, 9
        x = x0 + 16
        for tid in list(reversed(done))[:7]:
            k = self.lane_of.get(tid)
            c.rrect((x, y + 2, x + tw, y1 - 14), 8, fill=SURFACE_2)
            c.rrect((x, y + 2, x + tw, y + 6), 2, fill=ORANGE)
            c.text((x + tw / 2, y + 24), f"#{tid}", 13, "semibold", TEXT, anchor="mm")
            c.dot((x + tw / 2, y + 62), 18, ORANGE)
            c.text((x + tw / 2, y + 100), f"L{k + 1}" if k is not None else "L?", 13, "medium", TEXT_2, anchor="mm")
            c.text((x + tw / 2, y + 124), ui.clock((self.counted[tid] - 1) / self.fps), 11, "regular", TEXT_3,
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
    summary = {"counted": len(cb.order), "lanes": [round(v, 3) for v in cb.lanes],
               "tracks_with_lane": sum(1 for v in cb.lane_of.values() if v is not None),
               "per_lane": {f"L{k + 1}": sum(1 for v in cb.lane_of.values() if v == k) for k in range(len(cb.lanes))},
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
