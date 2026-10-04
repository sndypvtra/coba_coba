"""Compose the three videos from the cached detections, the floor and the analytics."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

import config as C
import draw as dr
import render as R
from scene import FloorPlan, building_mask


def _view_mask(view, plan: FloorPlan, inside: np.ndarray) -> np.ndarray:
    """The building mask, resampled into a PlanView's pixels."""
    uu, vv = np.meshgrid(np.arange(view.w) + 0.5, np.arange(view.h) + 0.5)
    Ainv = np.linalg.inv(view.A)
    wx = Ainv[0, 0] * uu + Ainv[0, 1] * vv + Ainv[0, 2]
    wy = Ainv[1, 0] * uu + Ainv[1, 1] * vv + Ainv[1, 2]
    pu, pv = plan.to_px(wx, wy)
    pu = np.clip(pu.astype(int), 0, inside.shape[1] - 1)
    pv = np.clip(pv.astype(int), 0, inside.shape[0] - 1)
    return inside[pv, pu]


def _events_timeline(summary: dict) -> list[tuple[float, str]]:
    """Every reported event as (seconds into the window, one line of text)."""
    ev = []
    for e in summary["#11_near_miss"]["events"]:
        ev.append((e.get("t", e["start_t"]), f"nyaris tertabrak · P{e['person']} & F{e['forklift']} · "
                                            f"{e['min_m']:.1f} m".replace(".", ",")))
    for e in summary["#10_speeding"]["events"]:
        ev.append((e["start_t"], f"forklift F{e['gid']} ngebut · {e['max_kmh']:.1f} km/j".replace(".", ",")))
    for e in summary["#8_idle"]["events"]:
        ev.append((e["start_t"] + C.IDLE_S, f"P{e['gid']} diam {C.IDLE_S:.0f} detik di satu titik"))
    for e in summary["#13_wrong_way"]["events"]:
        ev.append((e["t"], f"P{e['gid']} salah arah di lorong satu arah"))
    for e in summary["#3_crossings"]:
        ev.append((e["t"], f"P{e['gid']} melintasi {e['line'].split(' ·')[0]} ({'masuk' if e['dir'] == 'in' else 'keluar'})"))
    return sorted(ev)


def _ticker_lines(timeline, t_now: float) -> list[str]:
    return [f"{R.fmt_t(t)}  {s}" for t, s in timeline if t <= t_now]


def video_live_ops(ctx: dict, out_path) -> None:
    """Video 1: four cameras, the whole floor, and the live operations panel."""
    cams, plan = ctx["cams"], ctx["plan"]
    shown, others = ctx["shown"], [c for c in ctx["used"] if c not in ctx["shown"]]
    res, frames, summary = ctx["result"], ctx["frames"], ctx["summary"]
    site = C.SITE[ctx["scene"]]
    inside = building_mask(plan)
    ys, xs = np.nonzero(inside)
    x0, y1 = plan.to_world(xs.min(), ys.min())
    x1, y0 = plan.to_world(xs.max(), ys.max())
    view = R.PlanView(plan, (x0 - 1, y0 - 1, x1 + 1, y1 + 1), 768, 768)
    static = R.draw_static(view, cams, shown, others, site["zones"], site["lines"], _view_mask(view, plan, inside))
    heat = R.Heat(view)
    readers = {c: R.Reader(Path(ctx["video_path"](c)), frames[0].frame, ctx["stride"]) for c in shown}
    confirmed = res.confirmed_ids()
    timeline = _events_timeline(summary)
    near = summary["#11_near_miss"]["events"]
    trails: dict = {}
    head_series, walk_series = [], []
    out = R.VideoOut(out_path, 10.0)
    for fr in frames:
        canvas = np.full((R.H, R.W, 3), dr.BG, np.uint8)
        k2g, seen = R.key_index(res.blobs.get(fr.frame, []), confirmed)
        for k, cid in enumerate(shown):
            img = readers[cid].get(fr.frame)
            rows, classes = ctx["detections"][cid]
            cam = cams[cid]
            title = (f"{cid.replace('Camera_', 'CCTV ')} · {fr.camera_people.get(cid, 0)} orang · "
                     f"{R.num(cam.mount_height_m)} m · {cam.tilt_deg:.0f}°")
            t = R.tile(img, cam, rows, classes, fr.frame, fr, k2g, confirmed, dr.CAMERA_COLOURS[k],
                       (576, 324), site["zones"], site["lines"], title)
            x, y = (k % 2) * 576, R.HEADER + (k // 2) * 324
            canvas[y:y + 324, x:x + 576] = t
        # the plan
        m = static.copy()
        for o in fr.objects:
            if o.cls == "person":
                heat.add(o.x, o.y)
        heat.blend(m)
        # #11's hot-spot map: every near miss so far stays marked where it happened
        for e in near:
            if e.get("t", e["start_t"]) <= fr.t:
                u, v = view.pt(e["x"], e["y"])
                cv2.drawMarker(m, (u, v), dr.BAD, cv2.MARKER_TILTED_CROSS, 13, 2, cv2.LINE_AA)
        T = dr.Texts()
        R.draw_objects(m, view, fr, seen, shown, trails, T)
        T.flush(m)
        canvas[R.HEADER:R.HEADER + 768, 1152:1920] = m
        cv2.rectangle(canvas, (1152, R.HEADER), (1919, R.HEADER + 767), dr.FAINT, 1)

        # the panel under the tiles
        people = [o for o in fr.objects if o.cls == "person"]
        walking = sum(o.walking for o in people)
        lifts = [o for o in fr.objects if o.cls == "forklift"]
        moving = sum(o.speed > C.VEHICLE_MOVING_MS for o in lifts)
        in_lane = sum("lane" in o.alerts for o in people)
        head_series.append(len(people))
        walk_series.append(walking)
        T = dr.Texts()
        py = R.HEADER + 648 + 14
        R.kpi(T, 18, py, "Orang terpantau", f"{len(people)}", f"{walking} jalan · {len(people) - walking} diam")
        R.kpi(T, 300, py, "Forklift bergerak", f"{moving}/{len(lifts)}", "", dr.FORKLIFT)
        R.kpi(T, 470, py, "Nyaris tertabrak", f"{fr.events_so_far['near_miss']}", "kejadian", dr.BAD)
        R.kpi(T, 680, py, "Di jalur forklift", f"{in_lane}", f"orang · {fr.events_so_far['lane_entries']} masuk",
              dr.bgr("#fb923c"))
        R.kpi(T, 930, py, "Ngebut", f"{fr.events_so_far['speeding']}", f"> {C.SPEED_LIMIT_KMH:.0f} km/j", dr.BAD)
        py2 = py + 74
        R.kpi(T, 18, py2, "Diam lama", f"{fr.events_so_far['idle']}", f"≥ {C.IDLE_S:.0f} s", dr.WARN, 26)
        R.kpi(T, 200, py2, "Kerumunan", f"{len(fr.crowd_spots)}", f"{C.CROWD_MIN}+ dlm {C.CROWD_RADIUS_M:.0f} m",
              dr.bgr("#f87171"), 26)
        R.kpi(T, 420, py2, "Salah arah", f"{fr.events_so_far['wrong_way']}", "lorong contoh",
              dr.bgr("#f472b6"), 26)
        ln = "  ·  ".join(f"{name.split(' ·')[0].replace('Garis ', '')}: {a} masuk {b} keluar"
                          for name, (a, b) in fr.line_totals.items())
        T.add("GARIS HITUNG", (650, py2), 12, dr.MUTED, True)
        T.add(ln, (650, py2 + 18), 14, dr.INK)
        R.ticker(T, 18, py2 + 64, 620, _ticker_lines(timeline, fr.t), rows=4)
        T.add("ORANG TERPANTAU · BERJALAN", (650, py2 + 64), 12, dr.MUTED, True)
        T.flush(canvas)
        R.sparkline(canvas, 650, py2 + 84, 480, 92, [head_series, walk_series], [dr.INK, dr.PERSON],
                    ymax=max(max(head_series), 1) * 1.2)

        # under the plan: zones and legend
        T = dr.Texts()
        lx, ly = 1168, R.HEADER + 768 + 12
        T.add("ZONA · ORANG SEKARANG", (lx, ly), 12, dr.MUTED, True)
        for i, (name, n) in enumerate(fr.zone_people.items()):
            T.add(f"{name}", (lx, ly + 20 + i * 19), 13, dr.INK)
            T.add(f"{n}", (lx + 250, ly + 20 + i * 19), 13, dr.INK, True)
        lx2 = 1460
        T.add("LEGENDA", (lx2, ly), 12, dr.MUTED, True)
        items = [(dr.PERSON, "orang berjalan"), (dr.PERSON_IDLE, "orang diam"), (dr.FORKLIFT, "forklift"),
                 (dr.PALLET, "pallet truck"), (dr.BAD, "nyaris tertabrak / ngebut"),
                 (dr.bgr("#fb923c"), "orang di jalur forklift"), (dr.WARN, "diam lama")]
        for i, (col, name) in enumerate(items):
            cv2.circle(canvas, (lx2 + 6, ly + 28 + i * 19), 5, col, -1, cv2.LINE_AA)
            T.add(name, (lx2 + 18, ly + 20 + i * 19), 13, dr.INK)
        i = len(items)
        cv2.drawMarker(canvas, (lx2 + 6, ly + 28 + i * 19), dr.BAD, cv2.MARKER_TILTED_CROSS, 11, 2, cv2.LINE_AA)
        T.add("titik nyaris tertabrak (sejak awal)", (lx2 + 18, ly + 20 + i * 19), 13, dr.INK)
        T.add("Cincin berwarna = terlihat oleh CCTV dengan warna itu", (lx, R.H - 26), 12, dr.MUTED)
        T.flush(canvas)
        R.header(canvas, "WAREHOUSE LIVE OPS",
                 f"PoC · {ctx['source_note']} · {len(ctx['used'])} CCTV lolos uji kalibrasi, 4 ditampilkan · "
                 f"{ctx['detector_note']}",
                 f"{R.fmt_t(fr.t)} / {R.fmt_t(len(frames) / 10)}")
        out.write(canvas)
    out.close()


def video_one_camera(ctx: dict, out_path) -> None:
    """Video 2: one camera, large, with its own counting and a plan of what it sees."""
    cams, plan = ctx["cams"], ctx["plan"]
    cid = ctx["camera"]
    cam = cams[cid]
    res, frames, summary = ctx["result"], ctx["frames"], ctx["summary"]
    site = C.SITE[ctx["scene"]]
    rows, classes = ctx["detections"][cid]
    fp = cam.footprint(0.10)
    bx0, by0 = fp.min(0) - 3
    bx1, by1 = fp.max(0) + 3
    view = R.PlanView(plan, (min(bx0, cam.centre[0] - 3), min(by0, cam.centre[1] - 3),
                             max(bx1, cam.centre[0] + 3), max(by1, cam.centre[1] + 3)), 640, 480)
    static = R.draw_static(view, cams, [cid], [], site["zones"], site["lines"])
    reader = R.Reader(Path(ctx["video_path"](cid)), frames[0].frame, ctx["stride"])
    confirmed = res.confirmed_ids()
    timeline = _events_timeline(summary)
    ai_series, gt_series = [], []
    trails: dict = {}
    zones_area = [z for z in site["zones"] if z.kind == "area"]
    dwell: dict = {}
    out = R.VideoOut(out_path, 10.0)
    for i, fr in enumerate(frames):
        canvas = np.full((R.H, R.W, 3), dr.BG, np.uint8)
        k2g, seen = R.key_index(res.blobs.get(fr.frame, []), confirmed)
        img = reader.get(fr.frame)
        ai, gt = ctx["count_series"][i]
        ai_series.append(ai)
        gt_series.append(gt)
        title = f"{cid.replace('Camera_', 'CCTV ')} · {ai} orang terhitung AI · label: {gt}"
        t = R.tile(img, cam, rows, classes, fr.frame, fr, k2g, confirmed, dr.CAMERA_COLOURS[0], (1280, 720),
                   site["zones"], site["lines"], title, big=True)
        # time each person has spent in each zone so far, for the zone panels
        for o in fr.objects:
            if o.cls != "person" or o.gid not in seen:
                continue
            zs = [z for z in o.zones if any(z == a.name for a in zones_area)]
            if zs:
                dwell[(o.gid, zs[0])] = dwell.get((o.gid, zs[0]), 0.0) + 0.1
        canvas[R.HEADER:R.HEADER + 720, :1280] = t
        m = static.copy()
        T = dr.Texts()
        R.draw_objects(m, view, fr, seen, [cid], trails, T, label_all=True)
        T.flush(m)
        canvas[R.HEADER:R.HEADER + 480, 1280:1920] = m
        cv2.rectangle(canvas, (1280, R.HEADER), (1919, R.HEADER + 479), dr.CAMERA_COLOURS[0], 2)
        # AI count against the labels, over time
        T = dr.Texts()
        cy = R.HEADER + 480 + 12
        T.add("ORANG DI GAMBAR CCTV INI: AI vs LABEL", (1296, cy), 12, dr.MUTED, True)
        T.flush(canvas)
        R.sparkline(canvas, 1296, cy + 22, 608, 180, [gt_series, ai_series], [dr.MUTED, dr.PERSON],
                    ymax=max(max(gt_series), max(ai_series), 1) * 1.15)
        T = dr.Texts()
        T.add("— label (kebenaran)", (1300, cy + 206), 12, dr.MUTED)
        T.add("— hitungan AI", (1460, cy + 206), 12, dr.PERSON, True)
        err = np.abs(np.array(ai_series) - np.array(gt_series))
        T.add(f"rata-rata selisih {err.mean():.1f} orang".replace(".", ","), (1600, cy + 206), 12, dr.INK)
        # bottom panel
        py = R.HEADER + 720 + 16
        R.kpi(T, 18, py, "Orang di gambar", f"{ai}", f"label {gt}")
        x = 260
        for name, (a, b) in fr.line_totals.items():
            if name.startswith("Garis C"):
                continue
            R.kpi(T, x, py, name, f"{a}↗ {b}↘", "masuk · keluar", dr.INK, 30)
            x += 260
        for z in zones_area[:2]:
            occ = fr.zone_people.get(z.name, 0)
            d = [v for (g, zn), v in dwell.items() if zn == z.name]
            R.kpi(T, x, py, z.name, f"{occ}", f"orang · rata-rata {np.mean(d) if d else 0:.0f} s di zona", dr.INK, 30)
            x += 330
        R.kpi(T, 18, py + 84, "Diam lama", f"{fr.events_so_far['idle']}", f"≥ {C.IDLE_S:.0f} s", dr.WARN, 26)
        R.ticker(T, 260, py + 84, 1300, _ticker_lines(timeline, fr.t), rows=5)
        T.add("Lingkaran kosong = posisi orang menurut CCTV lain, digambar di lantai CCTV ini",
              (1296, R.H - 26), 12, dr.MUTED)
        T.flush(canvas)
        R.header(canvas, "HITUNG ORANG · SATU CCTV",
                 f"PoC · {ctx['source_note']} · {cid.replace('Camera_', 'CCTV ')} (lolos uji kalibrasi, "
                 f"meleset {ctx['geometry']['labels']['floor_m_median']:.2f} m) · ".replace(".", ",")
                 + ctx["detector_note"],
                 f"{R.fmt_t(fr.t)} / {R.fmt_t(len(frames) / 10)}")
        out.write(canvas)
    out.close()


def _alignment_panel(w: int, h: int, a: dict) -> np.ndarray:
    """The real recording's camera check, for a tile slot no verified camera fills."""
    img = np.full((h, w, 3), dr.PANEL, np.uint8)
    T = dr.Texts()
    T.add("UJI KALIBRASI ANTAR-CCTV", (14, 12), 15, dr.INK, True)
    T.add("orang yang sama, dilihat dua CCTV pada detik yang sama", (14, 34), 12, dr.MUTED)
    before = a["check_on_video_window"]["all_cameras_as_shipped"]
    after = a["check_on_video_window"]["verified_cameras_shifted"]
    n_all, n_used = len(a["cameras"]), len(a["verified"])
    for i, (name, r, col) in enumerate(((f"kalibrasi bawaan, {n_all} CCTV", before, dr.BAD),
                                        (f"setelah uji + koreksi, {n_used} CCTV", after, dr.GOOD))):
        y = 62 + i * 52
        T.add(name, (14, y), 13, dr.INK)
        T.add(f"selisih median {R.num(r['median_m'], 2)} m", (w - 14, y), 13, col, True, anchor="ra")
        cv2.rectangle(img, (14, y + 22), (14 + int((w - 28) * r["within_0_5_m_pct"] / 100), y + 36), col, -1)
        T.add(f"{r['within_0_5_m_pct']:.0f}% ≤ 0,5 m", (18, y + 21), 11, dr.BG, True)
    y = 172
    for c in a["verified"]:
        dx, dy = a["cameras"][c]["shift_m"]
        T.add(f"{c.replace('Camera_', 'CCTV ')} dipakai · digeser {R.num(dx, 2)}; {R.num(dy, 2)} m", (14, y), 12,
              dr.GOOD)
        y += 17
    for c in sorted(a["rejected"]):
        v = a["cameras"][c]
        why = (f"tetap meleset {R.num(v['disagreement_after_shift_m'], 2)} m: salah sudut, bukan geseran"
               if v.get("disagreement_after_shift_m") is not None else "tak bisa diuji: tak terlihat bersama CCTV lain")
        T.add(f"{c.replace('Camera_', 'CCTV ')} tidak dipakai · {why}", (14, y), 12, dr.WARN)
        y += 17
    T.add("koreksi diukur di luar 30 detik ini, diuji pada 30 detik ini", (14, h - 22), 11, dr.MUTED)
    return T.flush(img)


def video_real(ctx: dict, out_path) -> None:
    """Video 3: the real warehouse, its own cameras painting the floor."""
    cams, plan = ctx["cams"], ctx["plan"]
    shown, others = ctx["shown"], [c for c in ctx["used"] if c not in ctx["shown"]]
    res, frames = ctx["result"], ctx["frames"]
    site = C.SITE.get(ctx["scene"], {"zones": [], "lines": []})
    view = R.PlanView(plan, ctx["plan_bounds"], 768, 768, dim=0.85)
    static = R.draw_static(view, cams, shown, others, site["zones"], site["lines"])
    heat = R.Heat(view, radius_m=0.8)
    readers = {c: R.Reader(Path(ctx["video_path"](c)), frames[0].frame, ctx["stride"]) for c in shown}
    confirmed = res.confirmed_ids()
    trails: dict = {}
    panel = _alignment_panel(576, 324, ctx["alignment"]) if ctx.get("alignment") and len(shown) < 4 else None
    out = R.VideoOut(out_path, 10.0)
    for fr in frames:
        canvas = np.full((R.H, R.W, 3), dr.BG, np.uint8)
        k2g, seen = R.key_index(res.blobs.get(fr.frame, []), confirmed)
        for k, cid in enumerate(shown):
            img = readers[cid].get(fr.frame)
            rows, classes = ctx["detections"][cid]
            cam = cams[cid]
            title = (f"{cid.replace('Camera_', 'CCTV ')} · {fr.camera_people.get(cid, 0)} orang · "
                     f"{R.num(cam.mount_height_m)} m · {cam.tilt_deg:.0f}°")
            t = R.tile(img, cam, rows, classes, fr.frame, fr, k2g, confirmed, dr.CAMERA_COLOURS[k],
                       (576, 324), site["zones"], site["lines"], title)
            x, y = (k % 2) * 576, R.HEADER + (k // 2) * 324
            canvas[y:y + 324, x:x + 576] = t
        for k in range(len(shown), 4 if panel is not None else 0):
            x, y = (k % 2) * 576, R.HEADER + (k // 2) * 324
            canvas[y:y + 324, x:x + 576] = panel
        m = static.copy()
        for o in fr.objects:
            if o.cls == "person":
                heat.add(o.x, o.y)
        heat.blend(m)
        T = dr.Texts()
        R.draw_objects(m, view, fr, seen, shown, trails, T, label_all=True)
        T.flush(m)
        canvas[R.HEADER:R.HEADER + 768, 1152:1920] = m
        cv2.rectangle(canvas, (1152, R.HEADER), (1919, R.HEADER + 767), dr.FAINT, 1)
        people = [o for o in fr.objects if o.cls == "person"]
        walking = sum(o.walking for o in people)
        robots = [o for o in fr.objects if o.cls == "robot"]
        T = dr.Texts()
        py = R.HEADER + 648 + 14
        R.kpi(T, 18, py, "Orang di area", f"{len(people)}", f"{walking} jalan · {len(people) - walking} diam")
        R.kpi(T, 300, py, "Robot", f"{len(robots)}", "", dr.ROBOT)
        ag, within = ctx["agreement"], ctx["agreement_within"]
        R.kpi(T, 450, py, "Kesepakatan antar-CCTV", f"{ag:.2f} m".replace(".", ",") if ag is not None else "-",
              f"selisih median orang yang sama · {within:.0f}% ≤ 0,5 m" if within is not None else "", dr.GOOD, 30)
        cams_line = "  ·  ".join(f"{c.replace('Camera_', '')}: {n}" for c, n in fr.camera_people.items())
        T.add("ORANG PER CCTV", (18, py + 76), 12, dr.MUTED, True)
        T.add(cams_line, (18, py + 94), 14, dr.INK)
        T.add("Rekaman gudang asli: tidak ada label, jadi akurasi dinilai dari kesepakatan antar-CCTV, "
              "bukan dari kebenaran.", (18, py + 130), 13, dr.MUTED)
        T.add(f"Denah dilukis dari {len(ctx['used'])} CCTV terverifikasi itu sendiri: hanya lantai yang "
              "disepakati dua kamera, atau terlihat sangat dekat.", (18, py + 150), 13, dr.MUTED)
        T.add("Cincin berwarna = terlihat oleh CCTV dengan warna itu", (1168, R.H - 26), 12, dr.MUTED)
        T.flush(canvas)
        R.header(canvas, "WAREHOUSE LIVE OPS · REKAMAN ASLI",
                 f"PoC · {ctx['source_note']} · {len(ctx['used'])} dari {ctx['cameras_total']} CCTV terverifikasi, "
                 f"{len(shown)} ditampilkan",
                 f"{R.fmt_t(fr.t)} / {R.fmt_t(len(frames) / 10)}")
        out.write(canvas)
    out.close()
