"""Parcel dimensioning as a depot or dispatch manager reads it, 1920 x 1080.

    python dashboard/record.py               # once: the project's own run, recorded per frame
    python dashboard/dashboard.py            # -> output/parcel_dimensioning.mp4
    python dashboard/dashboard.py --still 300 511

Everything measured is the project's own (count, depth, belt plane, sizes; see
record.py). This file lays it out for the people who bill and load by it: each
parcel's dimensions and size class as it passes, volume handled, the size mix,
and the parcels whose class is not certain and so should be checked by hand
before they are charged.
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
from ui import AMBER, BG, BLUE, CYAN, GREEN, RED, SLATE, SURFACE_2, TEXT, TEXT_2, TEXT_3, VIOLET, alpha, num  # noqa: E402

ROOT = HERE.parent
VIDEO = ROOT / "input" / "03_packages_conveyor.mp4"
OUT = ROOT / "output"
K = 1280 / 1920
CLS_COL = {"S": CYAN, "M": BLUE, "L": VIOLET}
CLS_NAME = {"S": "kecil", "M": "sedang", "L": "besar"}
SLIT_SCAN_TRUTH = 8


def dims(s):
    return f"{s['l_mm'] / 10:.0f}×{s['w_mm'] / 10:.0f}×{s['h_mm'] / 10:.0f} cm"


class ParcelBoard:
    def __init__(self, rec, n_frames):
        self.rec = rec
        self.fps = rec["fps"]
        self.n = n_frames
        self.total = n_frames / self.fps
        self.board = ui.board(B.CARDS)
        self.thumbs = {}
        self.frames = rec["frames"]
        (ax, ay), (bx, by) = rec["line"]
        self.line = [[ax * K, ay * K], [bx * K, by * K]]
        # a parcel's size as the dashboard carries it: the last reading it had, frozen once locked
        self.size_at = []
        last = {}
        for fr in self.frames:
            for tid, s in fr["sizes"].items():
                if not last.get(int(tid), {}).get("locked"):
                    last[int(tid)] = s
            self.size_at.append(dict(last))
        self.counted = {}
        for fr in self.frames:
            for tid in fr["crossed"]:
                self.counted.setdefault(tid, fr["frame"])
        self.order = sorted(self.counted, key=self.counted.get)
        self.events = self.make_events()

    def size(self, tid, f):
        return self.size_at[min(f, len(self.size_at)) - 1].get(tid)

    def box_at(self, tid, f):
        for o in self.frames[f - 1]["objects"]:
            if o["tid"] == tid:
                return [v * K for v in o["box"]]
        return None

    def make_events(self):
        ev = []
        for tid in self.order:
            f = self.counted[tid]
            s = self.size(tid, f)
            box = self.box_at(tid, f) or [0, 300, 400, 600]
            if s is None:
                ev.append(B.Event(f, (f - 1) / self.fps, "low", "package_2", f"Paket #{tid} terhitung",
                                  "ukuran belum terbaca", "counted", focus=box))
                continue
            cls = f"{s['cls']}{s['mark']}"
            if s["mark"] == "?":
                ev.append(B.Event(f, (f - 1) / self.fps, "medium", "straighten", f"Paket #{tid} · cek ukuran manual",
                                  f"{dims(s)} · {num(s['volume_l'], 0)} L · kelas {cls} dekat batas", "check", focus=box))
            else:
                ev.append(B.Event(f, (f - 1) / self.fps, "info", "package_2",
                                  f"Paket #{tid} · {CLS_NAME[s['cls']]} ({s['cls']})",
                                  f"{dims(s)} · {num(s['volume_l'], 0)} L", "counted", focus=box))
        return ev

    # ---- the camera picture ------------------------------------------------
    def overlay(self, frame, i):
        f = i + 1
        img = frame.copy()
        (ax, ay), (bx, by) = self.line
        cv2.line(img, (int(ax), int(ay)), (int(bx), int(by)), ui.bgr(CYAN), 2, cv2.LINE_AA)
        objs = self.frames[i]["objects"]
        for o in objs:
            s = self.size(o["tid"], f)
            col = CLS_COL.get(s["cls"], SLATE) if s and s["locked"] else SLATE
            done = o["tid"] in self.counted and self.counted[o["tid"]] <= f
            ui.lock_box(img, [v * K for v in o["box"]], col, 2, fill=0.10 if done else 0.0)
        c = ui.Canvas(img)
        c.pill((ax + 6, min(ay, by) + 6), "Garis hitung", 11, (255, 255, 255), alpha(CYAN, 0.85), "semibold",
               icon="filter_center_focus", pad=(7, 2), anchor="la")
        for o in sorted(objs, key=lambda o: o["box"][1]):
            s = self.size(o["tid"], f)
            done = o["tid"] in self.counted and self.counted[o["tid"]] <= f
            x0, y0 = o["box"][0] * K, o["box"][1] * K
            if s and s["locked"]:
                lab = f"#{o['tid']} · {dims(s)} · {num(s['volume_l'], 0)} L · {s['cls']}{s['mark']}" + (" ✓" if done else "")
                B.chip(c, (max(6, x0), y0 - 4), lab, CLS_COL[s["cls"]], None, anchor="lb", size=11)
            else:
                c.pill((max(6, x0), y0 - 4), f"#{o['tid']} · mengukur…", 10, TEXT, alpha(BG, 0.75), "medium",
                       pad=(6, 2), anchor="lb")
        n = sum(1 for fr in self.counted.values() if fr <= f)
        B.corner_chips(c, "CAM 01 · Ban bongkar paket", [f"Terhitung: {n}", "Rekaman nyata"])
        c.pill((B.VW - 10, B.VH - 12), "Tumpukan di belakang tidak dihitung · bukan di atas ban", 11, TEXT,
               alpha(BG, 0.75), "medium", icon="visibility_off", pad=(8, 3), anchor="rb")
        return c.bgr()

    # ---- the page ------------------------------------------------------------
    def counted_sizes(self, f):
        out = []
        for tid in self.order:
            if self.counted[tid] <= f:
                out.append((tid, self.size(tid, self.counted[tid])))
        return out

    def draw(self, i, frame):
        f = i + 1
        t = i / self.fps
        vid = self.overlay(frame, i)
        for ev in self.events:
            if ev.frame == f and id(ev) not in self.thumbs and ev.focus:
                self.thumbs[id(ev)] = B.crop_16x9(vid, ev.focus)
        img = self.board.copy()
        ui.paste_rounded(img, vid, (B.VX, B.VY), 10)
        cb = (B.BR[0] + 52, B.BR[1] + 52, B.BR[2] - 20, B.BR[3] - 52)
        vol = []
        for j in range(i + 1):
            vol.append(sum(s["volume_l"] for tid, s in self.counted_sizes(j + 1) if s))
        vmax = max(200.0, float(self.total_volume()) * 1.15)
        B.series_chart(img, cb, [(vol, VIOLET, True)], self.n, vmax)
        c = ui.Canvas(img)
        c.topbar("Dimensioning · paket", "Ban bongkar paket · rekaman Pexels", "Putar ulang", t, self.total,
                 ["Rekaman nyata", "CAM 01"])
        cs = self.counted_sizes(f)
        self.kpis(c, cs, t)
        self.table(c, f)
        B.feed(c, self.events, t, self.thumbs)
        self.mix(c, cs)
        c.card_title(B.BR, "Volume tertangani, kumulatif", "monitoring", f"{num(vol[-1], 0)} L")
        step = 100 if vmax <= 600 else 200
        B.chart_axes(c, cb, vmax, list(range(0, int(vmax) + 1, step)), self.total, fmt=lambda v: f"{v} L")
        x0, _, x1, y1 = B.BR
        c.text((x1 - 16, y1 - 16), f"Hitungan {len(self.order)} = hitungan manual {SLIT_SCAN_TRUTH} · karton uji "
               "terbaca 340,5 mm, aslinya 340 mm", 11, "regular", TEXT_3, anchor="rm")
        c.timeline(B.TL, t, self.total, self.events)
        return c.bgr()

    def total_volume(self):
        return sum(s["volume_l"] for tid, s in self.counted_sizes(self.n) if s)

    def kpis(self, c, cs, t):
        n = len(cs)
        c.kpi(B.KPI_BOXES[0], "package_2", "Paket terhitung", str(n), "lewat garis hitung · diukur 3D", BLUE)
        v = sum(s["volume_l"] for _, s in cs if s)
        c.kpi(B.KPI_BOXES[1], "view_in_ar", "Volume tertangani", f"{num(v / 1000, 2)} m³",
              f"{num(v, 0)} L · rata-rata {num(v / n, 0)} L/paket" if n else "menunggu paket pertama", VIOLET)
        rate = n / t * 3600 if t > 1 and n else None
        c.kpi(B.KPI_BOXES[2], "speed", "Laju bongkar", f"{num(rate, 0)}/jam" if rate else "–",
              f"≈ {num(v / t * 3600 / 1000, 1)} m³/jam · perkiraan dari {num(t, 0)} s" if rate else "menunggu paket pertama",
              CYAN)
        unsure = sum(1 for _, s in cs if s and s["mark"] == "?")
        c.kpi(B.KPI_BOXES[3], "straighten", "Perlu cek manual", str(unsure),
              "ukuran dekat batas kelas" if unsure else "semua kelas pasti", AMBER,
              value_fill=AMBER if unsure else TEXT)

    def table(self, c, f):
        y = c.card_title(B.MID, "Paket terukur", "straighten", "ukuran final sebelum garis hitung")
        x0, _, x1, y1 = B.MID
        cols = [("Paket", 16), ("P × L × T", 92), ("Volume", 270), ("Kelas", 350), ("Status", 440)]
        for name, dx in cols:
            c.text((x0 + dx, y + 6), name, 11, "medium", TEXT_3, anchor="lm")
        c.d.line((x0 + 14, y + 19, x1 - 14, y + 19), fill=ui.BORDER, width=1)
        sizes = self.size_at[f - 1]
        locked = [(tid, s) for tid, s in sizes.items() if s["locked"]]
        seen_now = {o["tid"] for o in self.frames[f - 1]["objects"]}
        locked.sort(key=lambda p: (p[0] not in self.counted or self.counted[p[0]] > f, -p[0]))
        rows = [p for p in locked if p[0] in seen_now or (p[0] in self.counted and self.counted[p[0]] <= f)]
        rows = sorted(rows, key=lambda p: -(self.counted.get(p[0], 10 ** 6) if self.counted.get(p[0], 10 ** 6) <= f
                                             else 10 ** 5 + p[0]))[:7]
        ry = y + 38
        for tid, s in rows:
            done = tid in self.counted and self.counted[tid] <= f
            c.text((x0 + 16, ry), f"#{tid}", 13, "semibold", TEXT, anchor="lm")
            c.text((x0 + 92, ry), dims(s), 12, "regular", TEXT, anchor="lm", tnum=True)
            c.text((x0 + 270, ry), f"{num(s['volume_l'], 0)} L", 12, "regular", TEXT_2, anchor="lm", tnum=True)
            c.pill((x0 + 350, ry), f"{s['cls']}{s['mark']}", 10, (255, 255, 255), alpha(CLS_COL[s['cls']], 0.9), "bold",
                   pad=(7, 2), anchor="lm")
            if done:
                c.pill((x0 + 440, ry), "terhitung", 10, (255, 255, 255), alpha(GREEN, 0.85), "semibold", pad=(7, 2),
                       anchor="lm")
            else:
                c.pill((x0 + 440, ry), "di ban", 10, TEXT, alpha(CYAN, 0.25), "semibold", pad=(7, 2), anchor="lm")
            ry += 34
        c.text((x0 + 16, y1 - 18), "* ukuran ±10% (bagian atas karton kurang terlihat) · ? dekat batas kelas", 10, "regular", TEXT_3, anchor="lm")

    def mix(self, c, cs):
        y = c.card_title(B.BL, "Campuran ukuran", "category", "batas 30 cm dan 60 cm, sisi terpanjang")
        x0, _, x1, y1 = B.BL
        n = max(1, len(cs))
        ry = y + 20
        for k in ("S", "M", "L"):
            cnt = sum(1 for _, s in cs if s and s["cls"] == k)
            vol = sum(s["volume_l"] for _, s in cs if s and s["cls"] == k)
            c.dot((x0 + 24, ry), 6, CLS_COL[k])
            c.text((x0 + 38, ry), f"{k} · {CLS_NAME[k]}", 13, "semibold", TEXT, anchor="lm")
            bx0, bx1 = x0 + 160, x1 - 170
            c.rrect((bx0, ry - 7, bx1, ry + 7), 4, fill=SURFACE_2)
            w = (bx1 - bx0) * cnt / n
            if w > 2:
                c.rrect((bx0, ry - 7, bx0 + w, ry + 7), 4, fill=CLS_COL[k])
            c.text((bx1 + 12, ry), f"{cnt} paket", 12, "medium", TEXT, anchor="lm", tnum=True)
            c.text((x1 - 16, ry), f"{num(vol, 0)} L", 12, "regular", TEXT_2, anchor="rm", tnum=True)
            ry += 40
        c.text((x0 + 16, y1 - 18), "Kelas ukuran menentukan tarif dan cara muat", 11, "regular", TEXT_3, anchor="lm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    rec = json.loads((OUT / "record.json").read_text())
    frames, fps = B.read_video(VIDEO)
    pb = ParcelBoard(rec, len(frames))
    cs = pb.counted_sizes(len(frames))
    summary = {"counted": len(pb.order), "slit_scan_truth": SLIT_SCAN_TRUTH,
               "volume_counted_l": round(sum(s["volume_l"] for _, s in cs if s), 1),
               "parcels": [{"tid": tid, "frame": pb.counted[tid], **(s or {})} for tid, s in cs],
               "events": [{"t": round(e.t, 2), "severity": e.severity, "title": e.title, "detail": e.detail}
                          for e in pb.events]}
    (OUT / "parcel_dimensioning_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summary.items() if k != "events"}, ensure_ascii=False)[:2000])
    if a.still is not None:
        if a.still:
            B.stills(lambda i: pb.draw(i, frames[i]), len(frames), set(a.still),
                     lambda f: OUT / f"parcel_still_{f:04d}.jpg")
        return
    B.encode((pb.draw(i, f) for i, f in enumerate(frames)), OUT / "parcel_dimensioning.mp4", fps)
    print("video:", OUT / "parcel_dimensioning.mp4")


if __name__ == "__main__":
    main()
