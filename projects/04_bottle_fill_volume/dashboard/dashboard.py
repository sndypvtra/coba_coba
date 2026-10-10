"""Fill-level inspection as a plant manager reads it, 1920 x 1080.

    python dashboard/dashboard.py              # -> output/fill_inspection.mp4
    python dashboard/dashboard.py --still 150 232

The measurement is the project's own (see measure.py): bore, surface, volume by
disc integration. This file adds the line's view of it: the target at the thread
line and its tolerance, where the bottle is in its cycle, the flow rate, when
the target will be reached, and the rule the bottle will be judged by when the
nozzle stops.

The fill fraction is measured. Millilitres need the SKU's capacity, which no
camera can see; SKU_ML is an example and is labelled as one on screen.
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
sys.path.insert(0, str(HERE.parent))
import board as B  # noqa: E402
import ui  # noqa: E402
from calibration import BOTTLE_OUTLINE, ROI  # noqa: E402
from measure import measure  # noqa: E402
from ui import (AMBER, BLUE, CYAN, GREEN, RED, SLATE, SURFACE_2, TEXT, TEXT_2, TEXT_3, alpha,  # noqa: E402
                num)

ROOT = HERE.parent
VIDEO = ROOT / "input" / "07_bottle_filling_line.mp4"
OUT = ROOT / "output"
SKU_ML = 500.0                  # example SKU, typed in by the operator; not measured
TOL = 0.02                      # +-2 % of target
K = 1280 / 1920                 # source pixels to picture pixels


class FillBoard:
    def __init__(self, m, n_frames):
        self.m = m
        self.rows = m["rows"]
        self.fps = m["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.board = ui.board(B.CARDS)
        self.thumbs = {}
        self.start = m["flow_start"]
        self.in_pos = m["in_position"]
        self.events = self.make_events()
        last = self.rows[-1]
        rate = self.avg_rate(len(self.rows) - 1)
        self.eta_end = last["t"] + (1 - last["frac"]) / rate if rate else None
        self.x_max = float(np.ceil(max(self.total, self.eta_end or 0) + 0.5))

    # ---- numbers ---------------------------------------------------------
    def avg_rate(self, i):
        """Fill fraction per second since product started to flow."""
        if self.start is None or i + 1 <= self.start:
            return None
        a = self.rows[self.start - 1]
        r = self.rows[i]
        dt = r["t"] - a["t"]
        return (r["frac"] - a["frac"]) / dt if dt > 0.2 else None

    def phase(self, i):
        f = i + 1
        if self.in_pos is None or f < self.in_pos:
            return "botol masuk", SLATE
        if self.start is None or f < self.start:
            return "siap isi", CYAN
        return "mengisi", BLUE

    def make_events(self):
        ev = []
        f = self.in_pos
        ev.append(B.Event(f, (f - 1) / self.fps, "info", "check_circle", "Botol masuk posisi",
                          "4 botol di bawah nozzle · botol depan diukur", "in_position", focus=self.bottle_box(f - 1)))
        f = self.start
        ev.append(B.Event(f, (f - 1) / self.fps, "low", "water_drop", "Pengisian dimulai · nozzle 1",
                          f"{num((f - self.in_pos) / self.fps, 1)} s setelah botol di posisi", "flow_start",
                          focus=self.bottle_box(f - 1)))
        half = next((r for r in self.rows if r["frac"] >= 0.5), None)
        if half:
            f = half["frame"]
            rate = self.avg_rate(f - 1)
            ev.append(B.Event(f, (f - 1) / self.fps, "info", "timelapse", "Setengah target tercapai",
                              f"{num((f - self.start) / self.fps, 1)} s sejak mulai · {num(rate * SKU_ML, 0)} mL/s",
                              "half", focus=self.bottle_box(f - 1)))
        last = self.rows[-1]
        f = last["frame"]
        rate = self.avg_rate(f - 1)
        eta = (1 - last["frac"]) / rate
        ev.append(B.Event(f, (f - 1) / self.fps, "info", "hourglass_bottom", "Rekaman berakhir, siklus belum selesai",
                          f"{num(100 * last['frac'], 0)}% · target diperkirakan {num(eta, 1)} s lagi · belum diputuskan",
                          "clip_end", focus=self.bottle_box(f - 1)))
        return ev

    def bottle_box(self, i):
        x0, y0, x1, y1 = self.rows[i]["roi"]
        return [x0 * K, (y0 - 20) * K, x1 * K, y1 * K]

    # ---- the camera picture ------------------------------------------------
    def outline(self, i):
        x0, y0, _, _ = self.rows[i]["roi"]
        ox, oy = x0 - ROI[0], y0 - ROI[1]
        left = [((xl + ox) * K, (y + oy) * K) for y, xl, _ in BOTTLE_OUTLINE]
        right = [((xr + ox) * K, (y + oy) * K) for y, _, xr in BOTTLE_OUTLINE][::-1]
        return np.array(left + right, np.float32), oy

    def width_at(self, y_src, oy):
        ys = [y + oy for y, _, _ in BOTTLE_OUTLINE]
        xl = np.interp(y_src, ys, [x for _, x, _ in BOTTLE_OUTLINE])
        xr = np.interp(y_src, ys, [x for _, _, x in BOTTLE_OUTLINE])
        return xl, xr

    def overlay(self, frame, i):
        r = self.rows[i]
        img = frame.copy()
        phase, pcol = self.phase(i)
        f = i + 1
        poly, oy = self.outline(i)
        ox = r["roi"][0] - ROI[0]
        if f >= (self.in_pos or 10 ** 9):
            ui.dashed(img, np.vstack([poly, poly[:1]]), CYAN if phase == "siap isi" else BLUE, 1)
        c = ui.Canvas(img)
        if f >= (self.in_pos or 10 ** 9):
            ty = self.m["datum"]["thread_y"] + oy
            xl, xr = self.width_at(ty, oy)
            c.d.line(((xl + ox) * K, ty * K, (xr + ox) * K, ty * K), fill=GREEN + (255,), width=2)
            B.chip(c, ((xr + ox) * K + 10, ty * K), "Target 100% · garis ulir", GREEN, "flag", anchor="lm")
            if r["surface_y"] is not None and r["frac"] > 0:
                sy = r["surface_y"]
                xl, xr = self.width_at(sy, oy)
                c.d.line(((xl + ox) * K, sy * K, (xr + ox) * K, sy * K), fill=AMBER + (255,), width=3)
                B.chip(c, ((xr + ox) * K + 10, sy * K), f"{num(100 * r['frac'], 0)}% · {num(r['frac'] * SKU_ML, 0)} mL",
                       AMBER, "water_drop", anchor="lm")
            bx = (BOTTLE_OUTLINE[0][1] + ox) * K
            B.chip(c, (bx, (BOTTLE_OUTLINE[0][0] + oy - 120) * K), f"Nozzle 1 · {phase}", pcol,
                   "local_drink", anchor="lb")
        else:
            c.pill((B.VW / 2, B.VH - 40), "Menunggu botol masuk posisi", 13, TEXT, alpha(ui.BG, 0.8), "semibold",
                   icon="hourglass_top", pad=(10, 5), anchor="mm")
        B.corner_chips(c, "CAM 01 · Mesin pengisi, nozzle 1", [f"Fase: {phase}", "Rekaman nyata"])
        return c.bgr()

    # ---- the page ------------------------------------------------------------
    def draw(self, i, frame):
        r = self.rows[i]
        t = r["t"]
        vid = self.overlay(frame, i)
        for ev in self.events:
            if ev.frame == i + 1 and id(ev) not in self.thumbs:
                self.thumbs[id(ev)] = B.crop_16x9(vid, ev.focus)
        img = self.board.copy()
        ui.paste_rounded(img, vid, (B.VX, B.VY), 10)
        cb = (B.MID[0] + 52, B.MID[1] + 56, B.MID[2] - 24, B.MID[3] - 58)
        self.curve_marks(img, cb, i)
        hb = (B.BR[0] + 52, B.BR[1] + 50, B.BR[0] + 330, B.BR[3] - 40)
        self.height_volume(img, hb, r)
        c = ui.Canvas(img)
        c.topbar("Fill Inspection · isi botol", "Lini pengisian · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        self.kpis(c, i)
        self.curve_text(c, cb, i)
        B.feed(c, self.events, t, self.thumbs)
        self.rules(c, r)
        self.height_text(c, hb, r)
        c.timeline(B.TL, t, self.total, self.events)
        return c.bgr()

    def kpis(self, c, i):
        r = self.rows[i]
        started = self.start is not None and i + 1 >= self.start
        c.kpi(B.KPI_BOXES[0], "local_drink", "Isi botol · nozzle 1", f"{num(100 * r['frac'], 0)}%",
              f"≈ {num(r['frac'] * SKU_ML, 0)} mL dari target {num(SKU_ML, 0)} mL (SKU contoh)", BLUE)
        rate = self.avg_rate(i)
        c.kpi(B.KPI_BOXES[1], "water_drop", "Laju alir", f"{num(rate * SKU_ML, 0)} mL/s" if rate else "–",
              f"{num(100 * rate, 1)}% per detik, rata-rata sejak mulai" if rate else "menunggu produk mengalir", CYAN)
        el = (i + 1 - self.start) / self.fps if started else None
        c.kpi(B.KPI_BOXES[2], "timer", "Waktu isi", f"{num(el, 1)} s" if el is not None else "–",
              f"mulai {ui.clock((self.start - 1) / self.fps)},{int(((self.start - 1) / self.fps % 1) * 10)}"
              if started else "nozzle belum membuka", AMBER)
        if rate:
            eta = (1 - r["frac"]) / rate
            c.kpi(B.KPI_BOXES[3], "hourglass_bottom", "Perkiraan capai target", f"{num(eta, 1)} s lagi",
                  "dari laju rata-rata sejak mulai", GREEN)
        else:
            c.kpi(B.KPI_BOXES[3], "hourglass_bottom", "Perkiraan capai target", "–", "dihitung setelah produk mengalir",
                  GREEN)

    def tx(self, cb, t):
        return cb[0] + (cb[2] - cb[0]) * t / self.x_max

    def ty(self, cb, v, vmax=1.1):
        return cb[3] - (cb[3] - cb[1]) * v / vmax

    def curve_marks(self, img, cb, i):
        # tolerance band and the measured curve, drawn on the BGR page
        layer = img.copy()
        cv2.rectangle(layer, (int(cb[0]), int(self.ty(cb, 1 + TOL))), (int(cb[2]), int(self.ty(cb, 1 - TOL))),
                      ui.bgr(GREEN), -1)
        cv2.addWeighted(layer, 0.14, img, 0.86, 0, img)
        pts = np.array([(self.tx(cb, r["t"]), self.ty(cb, r["frac"])) for r in self.rows[:i + 1]], np.float32)
        if len(pts) > 1:
            poly = np.vstack([pts, [[pts[-1, 0], cb[3]], [pts[0, 0], cb[3]]]]).astype(np.int32)
            layer = img.copy()
            cv2.fillPoly(layer, [poly], ui.bgr(BLUE), cv2.LINE_AA)
            cv2.addWeighted(layer, 0.12, img, 0.88, 0, img)
            cv2.polylines(img, [pts.astype(np.int32)], False, ui.bgr(BLUE), 2, cv2.LINE_AA)
        rate = self.avg_rate(i)
        if rate:
            r = self.rows[i]
            t_end = r["t"] + (1 - r["frac"]) / rate
            t_draw = min(t_end, self.x_max)
            v_draw = r["frac"] + rate * (t_draw - r["t"])
            ui.dashed(img, np.array([[self.tx(cb, r["t"]), self.ty(cb, r["frac"])],
                                     [self.tx(cb, t_draw), self.ty(cb, v_draw)]]), BLUE, 2, 6, 5)

    def curve_text(self, c, cb, i):
        r = self.rows[i]
        c.card_title(B.MID, "Kurva pengisian · nozzle 1", "monitoring", f"sekarang {num(100 * r['frac'], 0)}%")
        B.chart_axes(c, cb, 1.1, [0, 0.5, 1.0], self.x_max, xstep=2, fmt=lambda v: f"{int(v * 100)}%",
                     xfmt=lambda s: f"{int(s)} s")
        c.text((cb[0] + 6, self.ty(cb, 1 + TOL) - 8), "target 100% · toleransi 98–102%", 10, "medium", TEXT_2,
               anchor="ls")
        rate = self.avg_rate(i)
        if rate:
            t_end = r["t"] + (1 - r["frac"]) / rate
            if t_end <= self.x_max:
                x = self.tx(cb, t_end)
                c.dot((x, self.ty(cb, 1.0)), 4.5, BLUE)
            else:
                x = cb[2]
            c.text((x - 10, self.ty(cb, 1 + TOL) - 8), f"perkiraan {num(t_end, 1)} s", 10, "semibold", TEXT, anchor="rs")
        x0, _, x1, y1 = B.MID
        c.legend((x0 + 16, y1 - 18), [("bar", BLUE, "isi terukur"), ("ring", BLUE, "perkiraan"),
                                     ("bar", alpha(GREEN, 0.5), "target ± toleransi")], 11)

    def rules(self, c, r):
        y = c.card_title(B.BL, "Aturan lolos / reject", "rule", f"SKU contoh {num(SKU_ML, 0)} mL")
        x0, _, x1, y1 = B.BL
        rows = [("flag", GREEN, "Target", "100% isi sampai garis ulir"),
                ("tune", CYAN, "Toleransi", "98–102% saat nozzle berhenti"),
                ("trending_down", RED, "Di bawah 98%", "reject · kurang isi"),
                ("water_drop", AMBER, "Di atas 102%", "lolos, dicatat sebagai produk terbuang")]
        ry = y + 10
        for icon, col, a, b in rows:
            c.icon(icon, (x0 + 26, ry), 16, col)
            c.text((x0 + 44, ry), a, 12, "semibold", TEXT, anchor="lm")
            c.text((x0 + 150, ry), b, 12, "regular", TEXT_2, anchor="lm")
            ry += 26
        c.d.line((x0 + 16, ry - 6, x1 - 16, ry - 6), fill=ui.BORDER, width=1)
        c.text((x0 + 16, ry + 12), "Siklus ini", 12, "medium", TEXT_3, anchor="lm")
        state = "mengisi" if r["frac"] > 0 else "menunggu"
        c.pill((x0 + 110, ry + 12), f"{state} · {num(100 * r['frac'], 0)}%", 11, TEXT, alpha(BLUE, 0.25), "semibold",
               pad=(8, 2), anchor="lm")
        c.text((x1 - 16, ry + 12), "keputusan saat nozzle berhenti", 11, "regular", TEXT_3, anchor="rm")

    def height_volume(self, img, hb, r):
        curve = self.m["datum"]["height_volume_curve"]
        pts = np.array([(hb[0] + (hb[2] - hb[0]) * h, hb[3] - (hb[3] - hb[1]) * v) for h, v in curve], np.float32)
        ui.dashed(img, np.array([[hb[0], hb[3]], [hb[2], hb[1]]]), SLATE, 1)
        cv2.polylines(img, [pts.astype(np.int32)], False, ui.bgr(AMBER), 2, cv2.LINE_AA)

    def height_text(self, c, hb, r):
        c.card_title(B.BR, "Tinggi cairan bukan volume", "straighten", "dihitung dari bentuk botol")
        for v in (0, 0.5, 1.0):
            y = hb[3] - (hb[3] - hb[1]) * v
            c.text((hb[0] - 8, y), f"{int(v * 100)}%", 10, "regular", TEXT_3, anchor="rm")
            x = hb[0] + (hb[2] - hb[0]) * v
            c.text((x, hb[3] + 12), f"{int(v * 100)}%", 10, "regular", TEXT_3, anchor="mm")
        c.text(((hb[0] + hb[2]) / 2, hb[3] + 26), "tinggi", 10, "regular", TEXT_3, anchor="mm")
        if r["frac"] > 0:
            x = hb[0] + (hb[2] - hb[0]) * r["height_frac"]
            y = hb[3] - (hb[3] - hb[1]) * r["frac"]
            c.dot((x, y), 5, AMBER)
            c.d.ellipse((x - 5, y - 5, x + 5, y + 5), outline=ui.SURFACE + (255,), width=2)
        tx = hb[2] + 36
        x1 = B.BR[2]
        c.text((tx, hb[1] + 6), f"Tinggi {num(100 * r['height_frac'], 0)}%  =  volume {num(100 * r['frac'], 0)}%",
               15, "semibold", TEXT, anchor="lm")
        lines = ["Botol menyempit di dasar dan bahu: naik",
                 "tinggi yang sama tidak sama dengan isi.",
                 "Kamera mengukur lebar botol per baris",
                 "lalu menjumlahkan volumenya."]
        for k, s in enumerate(lines):
            c.text((tx, hb[1] + 36 + k * 18), s, 12, "regular", TEXT_2, anchor="lm")
        c.legend((tx, hb[3] + 12), [("bar", AMBER, "botol ini"), ("bar", SLATE, "jika lurus")], 11)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    m = measure(VIDEO)
    frames, fps = B.read_video(VIDEO)
    fb = FillBoard(m, len(frames))
    OUT.mkdir(exist_ok=True)
    summary = {"sku_ml_example": SKU_ML, "tolerance": TOL, "frames": len(frames), "fps": fps,
               "bottle_in_position_s": round((m["in_position"] - 1) / fps, 2),
               "flow_start_s": round((m["flow_start"] - 1) / fps, 2),
               "fill_at_clip_end": round(m["rows"][-1]["frac"], 4),
               "height_at_clip_end": round(m["rows"][-1]["height_frac"], 4),
               "mean_rate_frac_per_s": round(fb.avg_rate(len(frames) - 1), 4),
               "target_expected_at_s": round(fb.eta_end, 2),
               "verdict": None,
               "note": "the clip ends while the bottle is still filling, so no pass/reject is given; "
                       "millilitres use an example SKU capacity, the fraction is measured",
               "events": [{"t": round(e.t, 2), "title": e.title, "detail": e.detail} for e in fb.events]}
    (OUT / "fill_inspection_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "events"}, ensure_ascii=False))
    if a.still:
        B.stills(lambda i: fb.draw(i, frames[i]), len(frames), set(a.still),
                 lambda f: OUT / f"fill_still_{f:04d}.jpg")
        return
    B.encode((fb.draw(i, f) for i, f in enumerate(frames)), OUT / "fill_inspection.mp4", fps)
    print("video:", OUT / "fill_inspection.mp4")


if __name__ == "__main__":
    main()
