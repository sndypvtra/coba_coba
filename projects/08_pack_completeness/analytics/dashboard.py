"""The two analytics videos: the camera picture with what the system sees on it, and the
numbers a plant manager runs the line by, side by side, 1920 x 1080.

    python dashboard.py line      # the can line   -> output/analytics/line_qc.mp4
    python dashboard.py pack      # packing station -> output/analytics/packing_qc.mp4

Each run first analyses the whole clip (vision only, see analyse.py), scores it
against the scene's ground truth, then draws every frame.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyse as A  # noqa: E402
import ui  # noqa: E402
import vision_line as VL  # noqa: E402
import vision_pack as VP  # noqa: E402
from ui import (AMBER, BG, BLUE, BORDER, CYAN, GREEN, RED, SLATE, SURFACE, SURFACE_2, TEXT,  # noqa: E402
                TEXT_2, TEXT_3, G, M, TOP, W, alpha, num)

ROOT = HERE.parent
OUT = ROOT / "output" / "analytics"
VX, VY, VW, VH = M, TOP + 12, 1280, 720
RX = VX + VW + G
RX1 = W - M
KW = (RX1 - RX - G) // 2
KPI_BOXES = [(RX, 68, RX + KW, 156), (RX + KW + G, 68, RX1, 156),
             (RX, 168, RX + KW, 256), (RX + KW + G, 168, RX1, 256)]
MID = (RX, 268, RX1, 588)
FEED = (RX, 600, RX1, 1012)
BL = (VX, 800, 650, 1012)
BR = (662, 800, VX + VW, 1012)
TL = (VX, 1024, RX1, 1064)
CARDS = KPI_BOXES + [MID, FEED, BL, BR]


# ---------------------------------------------------------------- shared parts
def read_video(path):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return out, fps
        out.append(f)


def crop_16x9(img, box, min_w=300):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w = max(min_w, (x1 - x0) * 1.35)
    h = w * 9 / 16
    if h < (y1 - y0) * 1.25:
        h = (y1 - y0) * 1.25
        w = h * 16 / 9
    H_, W_ = img.shape[:2]
    w, h = min(w, W_), min(h, H_)
    ax = int(np.clip(cx - w / 2, 0, W_ - w))
    ay = int(np.clip(cy - h / 2, 0, H_ - h))
    return img[ay:ay + int(h), ax:ax + int(w)].copy()


def chip(c, xy, label, colour, icon=None, anchor="lb", size=12):
    """A label tied to a detection: solid colour, white text."""
    return c.pill(xy, label, size, (255, 255, 255), alpha(colour, 0.92), "semibold", icon=icon,
                  pad=(7, 3), anchor=anchor, tnum=True)


def corner_chips(c, left, right):
    c.pill((10, 10), left, 12, TEXT, alpha(BG, 0.78), "semibold", dot=BLUE, pad=(9, 4))
    x = VW - 10
    for label in right:
        b = c.pill((x, 10), label, 12, TEXT, alpha(BG, 0.78), "semibold", pad=(9, 4), anchor="ra")
        x = b[0] - 6


def feed(c, events, t, thumbs, title="Event Log"):
    shown = [e for e in events if e.feed and e.t <= t]
    x0, y0, x1, y1 = FEED
    y = c.card_title(FEED, title, "notifications", f"{len(shown)} events")
    if not shown:
        c.text(((x0 + x1) / 2, (y + y1) / 2), "No events yet", 13, "regular", TEXT_3, anchor="mm")
        return
    rows = 4
    rh = (y1 - y - 12 - (rows - 1) * 8) // rows
    for k, ev in enumerate(reversed(shown[-rows:])):
        ry = y + 4 + k * (rh + 8)
        c.event_row((x0 + 12, ry, x1 - 12, ry + rh), ev, thumbs.get(id(ev)), now=t - ev.t < 2.0)


def chart_axes(c, box, ymax, ticks, total, unit_note=None):
    x0, y0, x1, y1 = box
    for v in ticks:
        y = y1 - (y1 - y0) * v / ymax
        c.d.line((x0, y, x1, y), fill=alpha(BORDER, 0.9), width=1)
        c.text((x0 - 8, y), str(v), 11, "regular", TEXT_3, anchor="rm", tnum=True)
    for s in range(0, int(total) + 1, 5):
        x = x0 + (x1 - x0) * s / total
        c.text((x, y1 + 12), ui.clock(s), 10, "regular", TEXT_3, anchor="mm", tnum=True)


def series_chart(img, box, series, total_n, ymax):
    """Thin lines over the box, growing left to right; series is [(values, rgb, fill)]."""
    x0, y0, x1, y1 = box
    for vals, rgb, fill in series:
        if len(vals) < 2:
            continue
        pts = np.array([(x0 + (x1 - x0) * i / max(total_n - 1, 1), y1 - (y1 - y0) * min(v, ymax) / ymax)
                        for i, v in enumerate(vals)], np.float32)
        if fill:
            poly = np.vstack([pts, [[pts[-1, 0], y1], [pts[0, 0], y1]]]).astype(np.int32)
            layer = img.copy()
            cv2.fillPoly(layer, [poly], ui.bgr(rgb), cv2.LINE_AA)
            cv2.addWeighted(layer, 0.12, img, 0.88, 0, img)
        cv2.polylines(img, [pts.astype(np.int32)], False, ui.bgr(rgb), 2, cv2.LINE_AA)


def encode(frames_iter, path, fps):
    import imageio_ffmpeg
    path.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-s", f"{W}x{ui.H}", "-r", str(fps), "-i", "-",
                          "-c:v", "libx264", "-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p",
                          "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)
    for f in frames_iter:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()


# ---------------------------------------------------------------- can line
class LineBoard:
    TITLE = "Pack Count QC · can trays"

    def __init__(self, run, score, total_s):
        self.run, self.score, self.total = run, score, total_s
        self.tpl = run.calibration["template"]
        self.board = ui.board(CARDS)
        self.thumbs = {}
        n = len(run.snaps)
        self.n = n
        self.cum_all = [len(s["judged"]) for s in run.snaps]
        self.cum_short = [sum(1 for j in s["judged"] if not j["ok"]) for s in run.snaps]
        self.reads = int(np.median([j["reads"] for j in run.snaps[-1]["judged"]]))

    # the camera picture ------------------------------------------------
    def overlay(self, frame, s):
        img = frame.copy()
        zx0 = VL.ZONE_X - VL.ZONE_HALF - 185
        zx1 = VL.ZONE_X + VL.ZONE_HALF + 185
        for x in (zx0, zx1):
            ui.dashed(img, np.array([[x, 214], [x, 448]]), CYAN, 1)
        for t in s["trays"]:
            b = t["box"]
            v = t["verdict"]
            if v is not None:
                ui.lock_box(img, b, GREEN if v["ok"] else RED, 2, fill=0.0 if v["ok"] else 0.10)
            elif t["live"] is not None:
                ui.lock_box(img, b, CYAN, 2, fill=0.04)
            else:
                ui.lock_box(img, b, SLATE, 1, outline=0.35)
        c = ui.Canvas(img)
        c.pill((VL.ZONE_X, 200), "Zona inspeksi", 12, (255, 255, 255), alpha(CYAN, 0.30), "semibold",
               icon="filter_center_focus", pad=(9, 3), anchor="mb")
        for t in s["trays"]:
            b, v = t["box"], t["verdict"]
            full = b[0] > 4 and b[2] < VW - 4
            lx = max(8, b[0])
            if v is not None:
                if v["ok"]:
                    chip(c, (lx, b[1] - 8), f"#{t['tid']} · 10/10 · lolos", GREEN, "check_circle")
                else:
                    chip(c, (lx, b[1] - 8), f"#{t['tid']} · {v['count']}/10 · KURANG", RED, "production_quantity_limits")
                    pts = VL.slot_points(self.tpl, VL.anchored(b, v["box"]))
                    for k in v["empty"]:
                        x, y = pts[k]
                        if 0 < x < VW:
                            c.d.ellipse((x - 22, y - 22, x + 22, y + 22), outline=RED + (255,), width=3)
                            c.pill((x, y), VL.slot_label(k), 11, (255, 255, 255), alpha(RED, 0.95), "bold",
                                   pad=(5, 1), anchor="mm")
            elif t["live"] is not None:
                n = sum(t["live"])
                chip(c, (lx, b[1] - 8), f"#{t['tid']} · memeriksa · {n}/10", CYAN, "fact_check")
                for k, (x, y) in enumerate(VL.slot_points(self.tpl, b)):
                    if t["live"][k]:
                        c.dot((x, y), 5, GREEN + (255,))
                        c.d.ellipse((x - 5, y - 5, x + 5, y + 5), outline=(255, 255, 255, 200), width=1)
                    else:
                        c.d.ellipse((x - 22, y - 22, x + 22, y + 22), outline=RED + (255,), width=3)
            elif full and b[2] < zx0 + 40:
                c.pill((lx, b[1] - 8), "to zone", 11, TEXT, alpha(BG, 0.7), "medium", pad=(7, 2), anchor="lb")
        in_zone = sum(1 for t in s["trays"] if t["live"] is not None)
        corner_chips(c, f"{A.CAM} · End of can filling line",
                     ["Belt →", f"In zone: {in_zone} tray"])
        return c.bgr()

    # the page ------------------------------------------------------------
    def draw(self, i, frame):
        s = self.run.snaps[i]
        t = i / self.run.fps
        vid = self.overlay(frame, s)
        for ev in self.run.events:
            if ev.frame == s["frame"] and id(ev) not in self.thumbs:
                self.thumbs[id(ev)] = crop_16x9(vid, ev.focus)
        img = self.board.copy()
        ui.paste_rounded(img, vid, (VX, VY), 10)
        cb = (BR[0] + 44, BR[1] + 52, BR[2] - 20, BR[3] - 52)
        ymax = max(4, max(self.cum_all) + 1)
        series_chart(img, cb, [(self.cum_all[:i + 1], BLUE, True), (self.cum_short[:i + 1], RED, False)], self.n, ymax)
        c = ui.Canvas(img)
        c.topbar(self.TITLE, "Simulated plant · can line", "Replay", t, self.total,
                 ["3D simulation", A.CAM])
        judged = s["judged"]
        n = len(judged)
        short = [j for j in judged if not j["ok"]]
        missing = sum(VL.EXPECTED - j["count"] for j in short)
        c.kpi(KPI_BOXES[0], "fact_check", "Trays inspected", str(n), f"{n - len(short)} pass · {len(short)} short", BLUE)
        pct = f"{num(100 * len(short) / n, 0)}% of trays inspected · flagged reject" if n else "no tray inspected yet"
        c.kpi(KPI_BOXES[1], "production_quantity_limits", "Short trays", str(len(short)), pct, RED,
              value_fill=RED if short else TEXT)
        c.kpi(KPI_BOXES[2], "remove_circle", "Missing cans", str(missing),
              f"of {n * VL.EXPECTED} cans expected", AMBER, value_fill=AMBER if missing else TEXT)
        r = s["rate_per_min"]
        c.kpi(KPI_BOXES[3], "speed", "Line speed", f"{num(r, 1)} trays/min" if r else "–",
              f"≈ {num(r * VL.EXPECTED, 0)} cans/min, from the tray spacing" if r else "needs 2 trays to measure",
              CYAN)
        self.mid(c, s)
        feed(c, self.run.events, t, self.thumbs)
        self.history(c, judged)
        self.chart_text(c, cb, ymax, n, len(short))
        c.timeline(TL, t, self.total, [e for e in self.run.events])
        return c.bgr()

    def mid(self, c, s):
        heat = s["heat"]
        total = sum(heat)
        y = c.card_title(MID, "Missing can positions", "grid_view", f"{total} events")
        x0, _, x1, y1 = MID
        cw, chh, gap = 88, 58, 8
        gw = 5 * cw + 4 * gap
        gx = x0 + (x1 - x0 - gw) // 2
        gy = y + 30
        c.text((gx, y + 12), "Baris A · belakang", 11, "regular", TEXT_3, anchor="lm")
        c.text((gx + gw, y + 12), "arah jalan →", 11, "medium", TEXT_2, anchor="rm")
        top = max(heat) if heat else 0
        for k in range(VL.EXPECTED):
            col, row = divmod(k, 2)
            cx = gx + (4 - col) * (cw + gap)          # column 1 is the leading edge, on the right
            cy = gy + row * (chh + gap)
            v = heat[k]
            fill = alpha(RED, 0.25 + 0.6 * v / max(top, 1)) if v else SURFACE_2
            c.rrect((cx, cy, cx + cw, cy + chh), 8, fill=fill)
            c.text((cx + 8, cy + 7), VL.slot_label(k), 11, "semibold", TEXT_2 if not v else TEXT)
            c.text((cx + cw - 8, cy + chh - 8), f"{v}×" if v else "–", 16 if v else 13, "bold" if v else "regular",
                   TEXT if v else TEXT_3, anchor="rs", tnum=True)
        c.text((gx, gy + 2 * chh + gap + 14), "Row B · front (near camera)", 11, "regular", TEXT_3, anchor="lm")
        # what it means
        ty = gy + 2 * chh + gap + 44
        if total == 0:
            msg, sub = "No short tray yet.", "Every tray is checked for 10 slots in the inspection zone."
        elif top >= 2:
            k = heat.index(top)
            msg = f"Slot {VL.slot_label(k)} empty {top}× — repeating pattern."
            sub = f"Check filler lane {k // 2 + 1} on the filling machine."
        elif total == 1:
            msg = f"1 event, at slot {VL.slot_label(heat.index(1))}."
            sub = "One event is not a pattern yet; keep watching."
        else:
            msg = f"{total} events at {total} different positions."
            sub = "No single filler lane pattern yet; keep watching."
        c.icon("insights", (x0 + 28, ty + 1), 18, BLUE)
        c.text((x0 + 44, ty), msg, 13, "semibold", TEXT, anchor="lm")
        c.text((x0 + 44, ty + 22), sub, 12, "regular", TEXT_2, anchor="lm")
        c.icon("rule", (x0 + 28, ty + 55), 18, TEXT_3)
        c.text((x0 + 44, ty + 54), f"Standard 10 cans/tray · verdict from ±{self.reads} readings in the zone", 12, "regular",
               TEXT_2, anchor="lm")

    def history(self, c, judged):
        y = c.card_title(BL, "Last trays", "history", "newest on the left")
        x0, _, x1, y1 = BL
        tw, gap = 78, 9
        x = x0 + 16
        for j in list(reversed(judged))[:7]:
            col = GREEN if j["ok"] else RED
            c.rrect((x, y + 2, x + tw, y1 - 14), 8, fill=alpha(col, 0.10) if not j["ok"] else SURFACE_2)
            c.rrect((x, y + 2, x + tw, y + 6), 2, fill=col)
            c.text((x + tw / 2, y + 22), f"#{j['tid']}", 13, "semibold", TEXT, anchor="mm")
            for k in range(VL.EXPECTED):
                cc, rr = divmod(k, 2)
                dx = x + tw / 2 + (2 - cc) * 12
                dy = y + 48 + rr * 14
                c.dot((dx, dy), 4.5, GREEN if k not in j["empty"] else RED)
            c.text((x + tw / 2, y + 90), f"{j['count']}/10", 15, "bold", TEXT, anchor="mm", tnum=True)
            c.pill((x + tw / 2, y + 116), "lolos" if j["ok"] else "reject", 10, (255, 255, 255), alpha(col, 0.9),
                   "semibold", pad=(7, 2), anchor="mm")
            x += tw + gap
        if not judged:
            c.text(((x0 + x1) / 2, (y + y1) / 2), "Waiting for the first tray to pass the zone", 13, "regular", TEXT_3,
                   anchor="mm")

    def chart_text(self, c, cb, ymax, n, short):
        y = c.card_title(BR, "Trays inspected, cumulative", "monitoring", f"{n} inspected · {short} short")
        step = 2 if ymax <= 10 else 5
        chart_axes(c, cb, ymax, list(range(0, ymax + 1, step)), self.total)
        sc = self.score
        x0, _, x1, y1 = BR
        lx = c.legend((x0 + 16, y1 - 16), [("bar", BLUE, "inspected"), ("bar", RED, "short")], 11)
        c.text((x1 - 16, y1 - 16), f"Uji vs ground truth: {sc['trays_correct']}/{sc['trays_judged']} tray benar · "
               f"{sc['readings_in_zone'] - sc['readings_wrong']}/{sc['readings_in_zone']} pembacaan",
               11, "regular", TEXT_3, anchor="rm")


# ---------------------------------------------------------------- packing station
class PackBoard:
    TITLE = "Pack Count QC · robot packing station"

    def __init__(self, run, score, total_s):
        self.run, self.score, self.total = run, score, total_s
        cal = run.calibration
        self.cal = VP.Calibration(cal["station_cx"], cal["template"], cal["pitch_px"], cal["feeder_stop"])
        self.board = ui.board(CARDS)
        self.thumbs = {}
        self.n = len(run.snaps)
        self.series = [s["series"] or 0 for s in run.snaps]

    def overlay(self, frame, s):
        img = frame.copy()
        fx0, fy0, fx1, fy1 = (int(v) for v in self.cal.feeder_stop)
        for b in s["boxes"]:
            col = {"filling": CYAN, "waiting": SLATE}.get(b["state"])
            if b["state"] == "done":
                col = GREEN if b["verdict"]["ok"] else RED
            ui.lock_box(img, b["box"], col, 2 if b["state"] != "waiting" else 1,
                        fill=0.08 if col == RED else 0.0, outline=0.65 if b["state"] != "waiting" else 0.35)
        c = ui.Canvas(img)
        alert = s["feeder_alert"]
        c.rrect((fx0, fy0, fx1, fy1), 6, fill=alpha(AMBER, 0.25) if alert else None,
                outline=AMBER + (255,) if alert else alpha(SLATE, 0.8), width=2)
        if alert:
            chip(c, (fx1 + 6, fy0 - 4), "Feeder stopper empty", AMBER, "warning", anchor="lb")
        else:
            c.pill((fx1 + 6, fy0 - 4), "Stopper feeder", 11, TEXT, alpha(BG, 0.7), "medium", pad=(7, 2), anchor="lb")
        for b in s["boxes"]:
            bx = b["box"]
            full = bx[0] > 4 and bx[2] < VW - 4
            lx = max(8, bx[0])
            slots = self.cal.slots(bx)
            if b["state"] == "filling":
                chip(c, (lx, bx[1] - 8), f"Box #{b['bid']} · {b['count']}/20 · filling", CYAN, "inventory_2")
                st = s["station"]
                for k, (x, y) in enumerate(slots):
                    if k in b["filled"]:
                        c.dot((x, y), 4.5, GREEN + (255,))
                        c.d.ellipse((x - 5, y - 5, x + 5, y + 5), outline=(255, 255, 255, 200), width=1)
                    elif k in b["missed"]:
                        self.cross(c, x, y)
                    elif st and k == st["next"]:
                        c.d.ellipse((x - 15, y - 15, x + 15, y + 15), outline=BLUE + (255,), width=2)
            elif b["state"] == "done":
                v = b["verdict"]
                if v["ok"]:
                    chip(c, (lx, bx[1] - 8), f"#{b['bid']} · 20/20 · complete", GREEN, "check_circle")
                else:
                    chip(c, (lx, bx[1] - 8), f"#{b['bid']} · {v['count']}/20 · SHORT", RED,
                         "production_quantity_limits")
                pts = self.cal.slots(VL.anchored(bx, v["box"]))
                for k in v["empty"]:
                    if 0 < pts[k][0] < VW:
                        self.cross(c, *pts[k])
            else:
                c.pill((lx, bx[1] - 8), "Next box", 11, TEXT, alpha(BG, 0.7), "medium", pad=(7, 2), anchor="lb")
        st = s["station"]
        robot = "Robot: filling" if st and st["filling"] else "Robot: box change"
        right = [robot]
        if s["cycle_s"]:
            right.append(f"Cycle {num(s['cycle_s'], 2)} s")
        corner_chips(c, f"{A.CAM} · Robot packing station", right)
        return c.bgr()

    @staticmethod
    def cross(c, x, y, r=9):
        c.dot((x, y), 13, alpha(RED, 0.9))
        c.d.line((x - r / 1.6, y - r / 1.6, x + r / 1.6, y + r / 1.6), fill=(255, 255, 255, 255), width=3)
        c.d.line((x - r / 1.6, y + r / 1.6, x + r / 1.6, y - r / 1.6), fill=(255, 255, 255, 255), width=3)

    def draw(self, i, frame):
        s = self.run.snaps[i]
        t = i / self.run.fps
        vid = self.overlay(frame, s)
        for ev in self.run.events:
            if ev.frame == s["frame"] and id(ev) not in self.thumbs and ev.focus:
                self.thumbs[id(ev)] = crop_16x9(vid, ev.focus)
        img = self.board.copy()
        ui.paste_rounded(img, vid, (VX, VY), 10)
        cb = (BR[0] + 44, BR[1] + 52, BR[2] - 20, BR[3] - 52)
        tgt = cb[3] - (cb[3] - cb[1]) * 20 / 22
        ui.dashed(img, np.array([[cb[0], tgt], [cb[2], tgt]]), SLATE, 1)
        series_chart(img, cb, [(self.series[:i + 1], BLUE, True)], self.n, 22)
        c = ui.Canvas(img)
        c.topbar(self.TITLE, "Simulated plant · packing line", "Replay", t, self.total,
                 ["3D simulation", A.CAM])
        st = s["station"]
        done = s["done"]
        short = [d for d in done if not d["ok"]]
        if st:
            state = "filling" if st["filling"] else "done, box change"
            c.kpi(KPI_BOXES[0], "inventory_2", "Box at station", f"{st['count']}/20", f"Box #{st['bid']} · {state}",
                  BLUE)
        else:
            c.kpi(KPI_BOXES[0], "inventory_2", "Box at station", "–", "waiting for a box", BLUE)
        c.kpi(KPI_BOXES[1], "local_shipping", "Boxes done", str(len(done)),
              f"{len(done) - len(short)} complete · {len(short)} short", GREEN)
        m = s["missed_total"]
        c.kpi(KPI_BOXES[2], "report", "Empty picks", str(m),
              f"{s['feeder_gaps']}× feeder supply gap detected" if s["feeder_gaps"] else "robot always carried a product",
              AMBER, value_fill=AMBER if m else TEXT)
        cy = s["cycle_s"]
        c.kpi(KPI_BOXES[3], "speed", "Robot speed", f"{num(60 / cy, 0)} picks/min" if cy else "–",
              f"cycle time {num(cy, 2)} s (median)" if cy else "needs 2 picks to measure", CYAN)
        self.mid(c, st)
        feed(c, self.run.events, t, self.thumbs)
        self.history(c, done, st, s["frame"])
        self.chart_text(c, cb, st)
        c.timeline(TL, t, self.total, self.run.events)
        return c.bgr()

    def mid(self, c, st):
        if not st:
            c.card_title(MID, "Box slot map", "grid_view")
            return
        rest = VP.EXPECTED - st["count"] - len(st["missed"])
        y = c.card_title(MID, f"Slot map · Box #{st['bid']}", "grid_view",
                         f"filled {st['count']} · empty {len(st['missed'])} · to go {rest}")
        x0, _, x1, y1 = MID
        cw, chh, gap = 92, 44, 7
        gw = 5 * cw + 4 * gap
        gx = x0 + (x1 - x0 - gw) // 2
        gy = y + 22
        c.text((gx, y + 6), "Back", 11, "regular", TEXT_3, anchor="lm")
        for k in range(VP.EXPECTED):
            r, col = divmod(k, VP.COLS)
            cx, cy = gx + col * (cw + gap), gy + r * (chh + gap)
            if k in st["filled"]:
                c.rrect((cx, cy, cx + cw, cy + chh), 8, fill=alpha(GREEN, 0.80))
                c.icon("check_circle", (cx + cw - 16, cy + chh / 2), 18, (255, 255, 255))
                lab = (255, 255, 255)
            elif k in st["missed"]:
                c.rrect((cx, cy, cx + cw, cy + chh), 8, fill=alpha(RED, 0.85))
                c.icon("cancel", (cx + cw - 16, cy + chh / 2), 18, (255, 255, 255))
                lab = (255, 255, 255)
            elif st["filling"] and k == st["next"]:
                c.rrect((cx, cy, cx + cw, cy + chh), 8, fill=alpha(BLUE, 0.16), outline=BLUE + (255,), width=2)
                c.text((cx + cw - 10, cy + chh / 2), "next", 10, "medium", TEXT_2, anchor="rm")
                lab = TEXT
            else:
                c.rrect((cx, cy, cx + cw, cy + chh), 8, fill=SURFACE_2)
                lab = TEXT_3
            c.text((cx + 10, cy + chh / 2), VP.slot_label(k), 12, "semibold", lab, anchor="lm")
        ly = gy + 4 * chh + 3 * gap + 14
        c.text((gx, ly), "Front (near camera)", 11, "regular", TEXT_3, anchor="lm")
        c.legend((x0 + 16, y1 - 18), [("bar", GREEN, "filled"), ("bar", RED, "empty pick"),
                                     ("ring", BLUE, "next slot"), ("bar", SURFACE_2, "to go")], 11)

    def history(self, c, done, st, frame):
        y = c.card_title(BL, "Box history", "list_alt", "per box released")
        x0, _, x1, y1 = BL
        cols = [("Box", 16), ("Released", 96), ("Count", 172), ("Status", 236), ("Empty slots", 336), ("Action", 452)]
        hy = y + 6
        for name, dx in cols:
            c.text((x0 + dx, hy), name, 11, "medium", TEXT_3, anchor="lm")
        c.d.line((x0 + 14, hy + 13, x1 - 14, hy + 13), fill=BORDER, width=1)
        rows = [(d, False) for d in done[-3:]]
        if st and st["filling"]:
            rows.append(({"bid": st["bid"], "count": st["count"], "ok": None, "empty": st["missed"], "frame": None}, True))
        ry = hy + 32
        for d, live in rows:
            c.text((x0 + 16, ry), f"#{d['bid']}", 13, "semibold", TEXT, anchor="lm")
            c.text((x0 + 96, ry), ui.clock((d["frame"] - 1) / self.run.fps) if d["frame"] else "–", 12, "regular",
                   TEXT_2, anchor="lm", tnum=True)
            c.text((x0 + 172, ry), f"{d['count']}/20", 13, "semibold", TEXT, anchor="lm", tnum=True)
            if live:
                c.pill((x0 + 236, ry), "filling", 10, TEXT, alpha(CYAN, 0.25), "semibold", pad=(7, 2), anchor="lm")
                act = "–"
            elif d["ok"]:
                c.pill((x0 + 236, ry), "complete", 10, (255, 255, 255), alpha(GREEN, 0.9), "semibold", pad=(7, 2),
                       anchor="lm")
                act = "Seal & ship"
            else:
                c.pill((x0 + 236, ry), "short", 10, (255, 255, 255), alpha(RED, 0.9), "semibold", pad=(7, 2),
                       anchor="lm")
                act = f"Hold, add {20 - d['count']} units"
            c.text((x0 + 336, ry), ", ".join(VP.slot_label(k) for k in d["empty"]) or "–", 12, "regular",
                   TEXT if d["empty"] else TEXT_3, anchor="lm")
            c.text((x0 + 452, ry), act, 12, "medium" if not live and not d["ok"] else "regular",
                   TEXT if not live and not d["ok"] else TEXT_2, anchor="lm")
            ry += 34

    def chart_text(self, c, cb, st):
        right = f"Box #{st['bid']}: {st['count']}/20" if st else ""
        c.card_title(BR, "Box count at station", "monitoring", right)
        chart_axes(c, cb, 22, [0, 10, 20], self.total)
        x0, _, x1, y1 = BR
        c.legend((x0 + 16, y1 - 16), [("bar", BLUE, "box count"), ("bar", SLATE, "standard 20")], 11)
        sc = self.score
        c.text((x1 - 16, y1 - 16), f"Test vs ground truth: {sc['boxes_correct']}/{sc['boxes_judged']} boxes correct · "
               f"empty picks {sc['empty_picks_found']}/{sc['empty_picks_in_truth']} · count lag {num(sc['count_lag_s'], 2)} s",
               11, "regular", TEXT_3, anchor="rm")


# ---------------------------------------------------------------- main
def run_line(src=None):
    frames, fps = read_video(ROOT / "output" / "pack_line.mp4")
    truth = json.loads((ROOT / "output" / "pack_line_truth.json").read_text())
    run = A.analyse_line(frames, fps)
    score = A.score_line(run, truth)
    return frames, fps, run, score, LineBoard(run, score, len(frames) / fps), "line_qc"


def run_pack(src=None):
    src = src or ROOT / "packing" / "output" / "packing_station.mp4"
    frames, fps = read_video(src)
    truth = json.loads((ROOT / "packing" / "output" / "packing_station_truth.json").read_text())
    hsv = [cv2.cvtColor(f, cv2.COLOR_BGR2HSV) for f in frames[:200]]
    run = A.analyse_pack(hsv, frames, fps)
    score = A.score_pack(run, truth)
    return frames, fps, run, score, PackBoard(run, score, len(frames) / fps), "packing_qc"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=["line", "pack"])
    ap.add_argument("--still", type=int, nargs="*", help="only write these frames as JPEG")
    ap.add_argument("--src", type=Path, help="another copy of the clip (e.g. a partial render)")
    a = ap.parse_args()
    frames, fps, run, score, board, name = (run_line if a.case == "line" else run_pack)(a.src)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}_score.json").write_text(json.dumps(score, indent=1))
    (OUT / f"{name}_events.json").write_text(json.dumps(
        [{"frame": e.frame, "t": round(e.t, 2), "severity": e.severity, "kind": e.kind, "ref": e.ref,
          "title": e.title, "detail": e.detail} for e in run.events], indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in score.items() if k != "verdicts"}))
    if a.still:
        want = set(a.still)
        for i, f in enumerate(frames):
            img = board.draw(i, f)          # every frame, so snapshots and charts build up as in the video
            if i + 1 in want:
                cv2.imwrite(str(OUT / f"{name}_still_{i + 1:04d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if i + 1 >= max(want):
                break
        return
    encode((board.draw(i, f) for i, f in enumerate(frames)), OUT / f"{name}.mp4", fps)
    print("video:", OUT / f"{name}.mp4")


if __name__ == "__main__":
    main()
