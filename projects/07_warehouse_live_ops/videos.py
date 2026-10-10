"""The three videos, laid out as the operations dashboard an owner would use.

Every video shares one frame: a top bar (which site, which view, the replay
clock), cards with the figures an owner acts on, the camera pictures, a feed
of alerts each with a snapshot of the camera that saw it, and a timeline of
the window. The cards speak in the owner's terms - people at risk, forklifts,
PPE, flows - and agree with the feed and the timeline because all three are
counted from the same list of events (ops.events). How the pictures were
checked against the ground truth lives in the accuracy report and the README.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import config as C
import ops
import render as R
import ui
from config import output_dir
from scene import FloorPlan, building_mask

TOTAL_S = C.WINDOW_S


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


def _row(x0: int, x1: int, y: int, h: int, n: int) -> list[tuple]:
    """n cards side by side between x0 and x1."""
    w = (x1 - x0 - (n - 1) * ui.G) / n
    return [(int(round(x0 + i * (w + ui.G))), y, int(round(x0 + i * (w + ui.G) + w)), y + h) for i in range(n)]


def _snapshots(evs: list, ctx: dict, prefer: list[str]) -> list:
    return [ops.snapshot(e, ctx["result"], ctx["detections"], ctx["frames"], ctx["video_path"], prefer) for e in evs]


def _feed(cv: ui.Canvas, box, evs: list, snaps: list, t: float, row_h: int = 64, cols: int = 1) -> None:
    """The card of alerts reported so far, newest first."""
    past = [(e, s) for e, s in zip(evs, snaps) if e.t <= t][::-1]
    y = cv.card_title(box, "Kejadian terbaru", "notifications", f"{len(past)} kejadian" if past else "")
    x0, _, x1, y1 = box
    if not past:
        cv.icon("check_circle", ((x0 + x1) / 2, (y + y1) / 2 - 14), 26, ui.GREEN)
        cv.text(((x0 + x1) / 2, (y + y1) / 2 + 14), "Belum ada kejadian", 13, "medium", ui.TEXT_2, anchor="mm")
        return
    gap = 8
    cw = (x1 - x0 - 24 - (cols - 1) * gap) / cols
    rows = max(1, int((y1 - 12 - y + gap) // (row_h + gap)))
    for i, (e, s) in enumerate(past[:rows * cols]):
        c, r = i % cols, i // cols
        bx0 = x0 + 12 + c * (cw + gap)
        by0 = y + r * (row_h + gap)
        cv.event_row((int(bx0), int(by0), int(bx0 + cw), int(by0 + row_h)), e, s, now=t - e.t < 3.0)


def _count(evs: list, kind: str, t: float) -> int:
    return sum(1 for e in evs if e.kind == kind and e.t <= t)


def _alert_value(n: int, kind: str) -> tuple:
    """A KPI value is in its alert's colour once something has happened, quiet otherwise."""
    return ui.SEVERITY[ops.KIND[kind][0]] if n else ui.TEXT


def _ppe_accuracy(scene: str) -> str:
    """The blind check's result, for the line under the PPE figures."""
    p = output_dir(scene) / "ppe_audit_score.json"
    if not p.exists():
        return ""
    sc = json.loads(p.read_text()).get("check")
    if not sc:
        return ""
    h, v = sc["helmet_live"], sc["vest_live"]
    if h["worn_found"].endswith("/0"):        # nobody wears PPE there: only false alarms can be checked
        fa = h["false_alarm"] + v["false_alarm"]
        return f"Uji buta APD: {fa} alarm palsu dari {h['labelled']} potongan acak"
    return f"Uji buta APD: helm benar {h['correct']}/{h['labelled']}, rompi {v['correct']}/{v['labelled']}"


# ================================================================ video 1
def video_live_ops(ctx: dict, out_path) -> None:
    """Video 1, the site overview: four cameras, the whole floor live, the alerts, the figures."""
    scene, cams, plan = ctx["scene"], ctx["cams"], ctx["plan"]
    shown, others = ctx["shown"], [c for c in ctx["used"] if c not in ctx["shown"]]
    res, frames, summary = ctx["result"], ctx["frames"], ctx["summary"]
    site = C.SITE[scene]
    zones, lines = site["zones"], site["lines"]

    kpis = _row(ui.M, ui.W - ui.M, 68, 88, 6)
    TW, TH = 562, 316
    tiles = [(16, 168), (590, 168), (16, 496), (590, 496)]
    feed_box = (16, 824, 1152, 1012)
    map_box = (1164, 168, 1904, 1012)
    map_xy, map_wh = (1176, 210), (716, 700)
    timeline_box = (16, 1024, 1904, 1064)
    bg = ui.board(kpis + [feed_box, map_box, timeline_box])

    inside = building_mask(plan)
    ys, xs = np.nonzero(inside)
    x0, y1 = plan.to_world(xs.min(), ys.min())
    x1, y0 = plan.to_world(xs.max(), ys.max())
    view = R.PlanView(plan, (x0 - 1, y0 - 1, x1 + 1, y1 + 1), *map_wh)
    floor = _view_mask(view, plan, inside)
    static = R.plan_static(view, cams, shown, others, zones, lines, floor)
    heat = R.Heat(view)
    overlays = {c: R.CameraOverlay(cams[c], (TW, TH), zones, lines) for c in shown}
    readers = {c: R.Reader(Path(ctx["video_path"](c)), frames[0].frame, ctx["stride"]) for c in shown}
    confirmed = res.confirmed_ids()
    evs = ops.events(scene, summary)
    snaps = _snapshots(evs, ctx, shown)
    # an alert seen only by a camera that is not on screen calls that camera up into the fourth tile
    spots = ops.spotlights(evs, shown)
    spot_cams = sorted({sp[2] for sp in spots})
    for c in spot_cams:
        overlays[c] = R.CameraOverlay(cams[c], (TW, TH), zones, lines)
        readers[c] = R.Reader(Path(ctx["video_path"](c)), frames[0].frame, ctx["stride"])
    spot_fov = {c: cv2.findContours(R.fov_mask(view, cams[c], floor), cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)[0] for c in spot_cams}
    memory = {c: {} for c in list(shown) + spot_cams}
    plan_memory: dict = {}
    tally = ops.Tally()
    trails: dict = {}
    out = R.VideoOut(out_path, 10.0)
    for fr in frames:
        canvas = bg.copy()
        k2g, seen = R.key_index(res.blobs.get(fr.frame, []), confirmed)
        tally.add(fr)
        spot = next((sp for sp in spots if sp[0] <= fr.t < sp[1]), None)
        on_screen = list(shown) if spot is None else list(shown[:3]) + [spot[2]]
        colours = list(ui.CAMERA[:4]) if spot is None else list(ui.CAMERA[:3]) + [ui.RED]
        marks = []
        for k, cid in enumerate(on_screen):
            rows, classes = ctx["detections"][cid]
            pic, mk = R.camera_view(readers[cid].get(fr.frame), overlays[cid], rows, classes, fr.frame, fr, k2g,
                                    confirmed, header=(colours[k], ops.cam_label(cid), ops.camera_name(scene, cid),
                                                       fr.camera_people.get(cid, 0)), memory=memory[cid])
            ui.paste_rounded(canvas, pic, tiles[k], 10)
            marks.append((mk, *tiles[k]))
        # the floor
        m = static.copy()
        for o in fr.objects:
            if o.cls == "person":
                heat.add(o.x, o.y)
        heat.blend(m)
        if spot is not None:                # the called-up camera and what it sees, in red
            c = spot[2]
            for cnt in spot_fov[c]:
                ui.dashed(m, np.vstack([cnt[:, 0], cnt[:1, 0]]), ui.RED, 2, 7, 5)
            u, v = view.pt(cams[c].centre[0], cams[c].centre[1])
            cv2.circle(m, (u, v), 6, ui.bgr(ui.RED), -1, cv2.LINE_AA)
            cv2.circle(m, (u, v), 10, ui.bgr(ui.RED), 1, cv2.LINE_AA)
        mk = R.plan_labels(view, cams, on_screen, zones, lines, fr, scene, plan_memory, colours)
        for e in evs:                       # #11's hot spots: every near miss so far stays where it happened
            if e.kind == "near_miss" and e.t <= fr.t:
                u, v = view.pt(e.x, e.y)
                cv2.circle(m, (u, v), 11, ui.bgr(ui.RED), 2, cv2.LINE_AA)
                mk.chip((u + 14, v), f"{ui.clock(e.t)} · {e.cams[0]}" if e.cams else ui.clock(e.t), 10, ui.RED,
                        (10, 14, 19, 220), icon="warning", anchor="lm")
        R.plan_objects(m, view, fr, seen, on_screen, trails, mk, colours=colours)
        ui.paste_rounded(canvas, m, map_xy, 8)
        marks.append((mk, *map_xy))
        # the headcount's curve, inside its card
        kb = kpis[0]
        ui.area_chart(canvas, (kb[2] - 120, kb[1] + 22, kb[2] - 16, kb[1] + 56), [(tally.heads, ui.CYAN)],
                      ymax=max(max(tally.heads), 1) * 1.25, n_total=len(frames))

        cv = ui.Canvas(canvas)
        for mk_, x, y in marks:
            mk_.draw(cv, x, y)
        if spot is not None:                # the call-up: framed in red, and why it is on screen
            x, y = tiles[3]
            cv.rrect((x - 1, y - 1, x + TW, y + TH), r=11, outline=ui.RED, width=3)
            e = spot[3]
            cv.pill((x + 10, y + TH - 10), f"SOROTAN · {e.title} · {e.detail.split(' · ')[0]}", 12, (255, 255, 255),
                    ui.RED, "semibold", icon=e.icon, pad=(9, 4), anchor="lb")
            cv.pill((x + TW - 10, y + TH - 10), f"kembali ke {ops.cam_label(shown[3])} pukul {ui.clock(spot[1])}", 10,
                    ui.TEXT, (10, 14, 19, 215), "medium", pad=(7, 3), anchor="rb")
        people = [o for o in fr.objects if o.cls == "person"]
        walking = sum(o.walking for o in people)
        lifts = [o for o in fr.objects if o.cls == "forklift"]
        moving = sum(o.speed > C.VEHICLE_MOVING_MS for o in lifts)
        in_lane = sum("lane" in o.alerts for o in people)
        n_near, n_lane = _count(evs, "near_miss", fr.t), _count(evs, "lane", fr.t)
        n_speed, n_crowd = _count(evs, "speeding", fr.t), _count(evs, "crowd", fr.t)
        util = tally.utilisation
        cv.kpi(kpis[0], "groups", "Orang terpantau", f"{len(people)}",
               f"{walking} bergerak · {len(people) - walking} diam · dari 15 kamera", ui.CYAN)
        cv.kpi(kpis[1], "forklift", "Forklift bergerak", f"{moving}/{len(lifts)}",
               f"utilisasi {util:.0%}: waktu bergerak dari waktu terlihat" if util is not None else "", ui.ORANGE)
        cv.kpi(kpis[2], "warning", "Nyaris tertabrak", f"{n_near}", "pejalan ≤ 1,5 m dari forklift bergerak",
               ui.RED, _alert_value(n_near, "near_miss"))
        cv.kpi(kpis[3], "do_not_step", "Masuk jalur forklift", f"{n_lane}",
               f"{in_lane} orang di jalur sekarang", ui.ORANGE, _alert_value(n_lane, "lane"))
        cv.kpi(kpis[4], "speed", "Forklift ngebut", f"{n_speed}",
               f"di atas {C.SPEED_LIMIT_KMH:.0f} km/j selama ≥ 1 detik", ui.RED, _alert_value(n_speed, "speeding"))
        cv.kpi(kpis[5], "groups", "Kerumunan", f"{n_crowd}",
               f"≥ {C.CROWD_MIN} orang dalam {C.CROWD_RADIUS_M:g} m", ui.BLUE, _alert_value(n_crowd, "crowd"))
        _feed(cv, feed_box, evs, snaps, fr.t, row_h=64, cols=2)
        cv.card_title(map_box, "Peta lantai · posisi langsung", "map", "dari 15 kamera, dalam meter")
        zx, zy = map_box[0] + 16, map_xy[1] + map_wh[1] + 20
        for k, z in enumerate(zones):        # each numbered zone: how many people are in it now
            b = cv.pill((zx, zy), f"{k + 1}", 10, ui.TEXT, ui.SURFACE_2, "semibold", pad=(6, 2), anchor="lm")
            b = cv.text((b[2] + 6, zy), ops.zone_label(z.name), 12, "regular", ui.TEXT_2, anchor="lm")
            b = cv.text((b[2] + 6, zy), f"{fr.zone_people.get(z.name, 0)}", 12, "bold", ui.TEXT, anchor="lm",
                        tnum=True)
            zx = b[2] + 18
            if zx > map_box[2] - 150 and k < len(zones) - 1:
                zx, zy = map_box[0] + 16, zy + 22
        cv.legend((map_box[0] + 16, map_box[3] - 22),
                  [("dot", ui.CYAN, "Orang bergerak"), ("dot", (186, 230, 253), "Diam"),
                   ("bar", ui.ORANGE, "Forklift"), ("bar", ui.YELLOW, "Pallet truck"),
                   ("bar", ui.alpha(ui.AMBER, 0.5), "Jalur forklift"),
                   ("icon:warning", ui.RED, "Titik nyaris tertabrak")], 11)
        cv.topbar("Denah gudang", "Gudang simulasi A", "Putar ulang", fr.t, TOTAL_S,
                  ["Data simulasi NVIDIA", f"{len(ctx['used'])} kamera aktif"])
        cv.timeline(timeline_box, fr.t, TOTAL_S, evs)
        out.write(cv.bgr())
    out.close()


# ================================================================ video 2
def video_one_camera(ctx: dict, out_path) -> None:
    """Video 2, one camera: the east work area large, its people and PPE, its flows and zones."""
    scene, cams, plan = ctx["scene"], ctx["cams"], ctx["plan"]
    cid = ctx["camera"]
    cam = cams[cid]
    res, frames, summary = ctx["result"], ctx["frames"], ctx["summary"]
    site = C.SITE[scene]
    zones, lines = site["zones"], site["lines"]
    rows, classes = ctx["detections"][cid]
    live = ctx.get("ppe_live") or {}

    cam_xy, cam_wh = (16, 68), (1280, 720)
    kpis = [b for y in (68, 168, 268) for b in _row(1308, 1904, y, 88, 2)]
    map_box = (1308, 368, 1904, 700)
    feed_box = (1308, 712, 1904, 1012)
    zone_box = (16, 800, 650, 1012)
    trend_box = (662, 800, 1296, 1012)
    timeline_box = (16, 1024, 1904, 1064)
    bg = ui.board(kpis + [map_box, feed_box, zone_box, trend_box, timeline_box])

    fp = cam.footprint(0.10)
    bx0, by0 = fp.min(0) - 3
    bx1, by1 = fp.max(0) + 3
    map_xy, map_wh = (1320, 408), (572, 282)
    view = R.PlanView(plan, (min(bx0, cam.centre[0] - 3), min(by0, cam.centre[1] - 3),
                             max(bx1, cam.centre[0] + 3), max(by1, cam.centre[1] + 3)), *map_wh)
    static = R.plan_static(view, cams, [cid], [], zones, lines)
    overlay = R.CameraOverlay(cam, cam_wh, zones, lines)
    reader = R.Reader(Path(ctx["video_path"](cid)), frames[0].frame, ctx["stride"])
    confirmed = res.confirmed_ids()
    evs = ops.events(scene, summary, ctx.get("ppe_events"))
    snaps = _snapshots(evs, ctx, [cid])
    # the zones this camera watches, in the order an owner would read them
    covered = [z for z in zones if R.zone_share(cam, z) >= 0.25]
    cam_memory: dict = {}
    plan_memory: dict = {}
    watched_lines = [ln for ln, segs in overlay.lines if segs]
    dwell: dict = {}
    trails: dict = {}
    counts: list[int] = []
    accuracy = _ppe_accuracy(scene)
    out = R.VideoOut(out_path, 10.0)
    for i, fr in enumerate(frames):
        canvas = bg.copy()
        k2g, seen = R.key_index(res.blobs.get(fr.frame, []), confirmed)
        now = live.get(fr.frame, {})
        ai = ctx["count_series"][i][0]
        counts.append(ai)
        pic, mk = R.camera_view(reader.get(fr.frame), overlay, rows, classes, fr.frame, fr, k2g, confirmed,
                                big=True, ppe=now if live else None,
                                header=(ui.CAMERA[0], ops.cam_label(cid), ops.camera_name(scene, cid), ai),
                                memory=cam_memory)
        ui.paste_rounded(canvas, pic, cam_xy, 12)
        marks = [(mk, *cam_xy)]
        for o in fr.objects:                 # seconds each person has spent in each zone so far
            if o.cls == "person" and o.gid in seen:
                for zn in o.zones:
                    dwell[(o.gid, zn)] = dwell.get((o.gid, zn), 0.0) + 0.1
        m = static.copy()
        mk2 = R.Marks(view.w, view.h, view.taken, plan_memory)
        R.plan_objects(m, view, fr, seen, [cid], trails, mk2, ppe=now if live else None, label_all=True)
        ui.paste_rounded(canvas, m, map_xy, 8)
        marks.append((mk2, *map_xy))
        tb = trend_box
        ui.area_chart(canvas, (tb[0] + 56, tb[1] + 52, tb[2] - 18, tb[3] - 46), [(counts, ui.CYAN)],
                      ymax=max(20, max(counts) * 1.2), n_total=len(frames))

        cv = ui.Canvas(canvas)
        for mk_, x, y in marks:
            mk_.draw(cv, x, y)
        here = [g for g in seen if any(o.gid == g and o.cls == "person" for o in fr.objects)]
        n, helm, vest, both = ops.ppe_now(now, here)
        n_ppe = _count(evs, "ppe", fr.t)
        ins = sum(fr.line_totals.get(ln.name, (0, 0))[0] for ln in watched_lines)
        outs = sum(fr.line_totals.get(ln.name, (0, 0))[1] for ln in watched_lines)
        n_wrong, n_lane = _count(evs, "wrong_way", fr.t), _count(evs, "lane", fr.t)
        cv.kpi(kpis[0], "groups", "Orang di kamera", f"{ai}",
               f"rata-rata {ui.num(float(np.mean(counts)))} · puncak {max(counts)}", ui.CYAN)
        cv.kpi(kpis[1], "engineering", "APD lengkap", f"{both}/{n}" if n else "–",
               f"helm {helm} · rompi {vest} · dinilai {n} dari {ai} orang" if n
               else "belum ada yang cukup dekat untuk dinilai", ui.GREEN, ui.TEXT)
        cv.kpi(kpis[2], "gpp_bad", "Peringatan APD", f"{n_ppe}", "≥ 2 detik tanpa helm / rompi",
               ui.AMBER, _alert_value(n_ppe, "ppe"))
        cv.kpi(kpis[3], "swap_horiz", "Melintasi garis hitung", f"{ins + outs}", f"{ins} masuk · {outs} keluar",
               ui.BLUE)
        cv.kpi(kpis[4], "route", "Melawan arah", f"{n_wrong}", "di lorong satu arah", ui.PINK,
               _alert_value(n_wrong, "wrong_way"))
        cv.kpi(kpis[5], "do_not_step", "Masuk jalur forklift", f"{n_lane}", "pejalan kaki", ui.ORANGE,
               _alert_value(n_lane, "lane"))
        cv.card_title(map_box, "Posisi di denah", "map", ops.camera_name(scene, cid))
        _feed(cv, feed_box, evs, snaps, fr.t, row_h=70)
        # zones: how many now, and how long people stay
        y = cv.card_title(zone_box, "Zona yang diawasi", "location_on", "sekarang · rata-rata lama tinggal")
        for k, z in enumerate(covered[:4]):
            yy = y + 4 + k * 40
            occ = fr.zone_people.get(z.name, 0)
            stays = [v for (g, zn), v in dwell.items() if zn == z.name]
            rgb = R.ZONE_RGB.get(z.kind, ui.SLATE)
            cv.dot((zone_box[0] + 22, yy + 12), 4.5, rgb if z.kind != "area" else ui.TEXT_2)
            cv.text((zone_box[0] + 34, yy + 12), ops.zone_label(z.name), 13, "medium", ui.TEXT, anchor="lm")
            if z.kind == "vehicle_lane":
                note = f"{n_lane} kali dimasuki"
            elif z.kind == "one_way":
                note = f"{n_wrong} melawan arah · aturan PoC"
            else:
                note = f"rata-rata {np.mean(stays):.0f} s per orang" if stays else "belum ada"
            cv.text((zone_box[2] - 16, yy + 12), note, 12, "regular", ui.TEXT_3, anchor="rm")
            bx0, bx1 = zone_box[0] + 250, zone_box[2] - 190
            cv.rrect((bx0, yy + 8, bx1, yy + 16), r=4, fill=ui.SURFACE_2)
            if occ:
                cv.rrect((bx0, yy + 8, bx0 + (bx1 - bx0) * min(1.0, occ / 6), yy + 16), r=4, fill=rgb)
            cv.text((bx0 - 12, yy + 12), f"{occ}", 14, "bold", ui.TEXT, anchor="rm", tnum=True)
        # trend
        y = cv.card_title(trend_box, "Orang di kamera, 30 detik", "monitoring",
                          f"rata-rata {ui.num(float(np.mean(counts)))} · puncak {max(counts)}")
        top = max(20, max(counts) * 1.2)
        for v in (0, 10, 20):
            if v <= top:
                yy = tb[3] - 46 - (tb[3] - 46 - tb[1] - 52) * v / top
                cv.text((tb[0] + 44, yy), f"{v}", 10, "regular", ui.TEXT_3, anchor="rm", tnum=True)
        if accuracy:
            cv.text((tb[0] + 16, tb[3] - 18), accuracy, 11, "regular", ui.TEXT_3, anchor="lm")
        cv.legend((tb[2] - 16 - 300, tb[3] - 18), [("bar", ui.CYAN, "orang terhitung di gambar")], 11)
        cv.topbar(ops.camera_name(scene, cid), "Gudang simulasi A", "Putar ulang", fr.t, TOTAL_S,
                  ["Data simulasi NVIDIA", ops.cam_label(cid)])
        cv.timeline(timeline_box, fr.t, TOTAL_S, evs)
        out.write(cv.bgr())
    out.close()


# ================================================================ video 3
def video_real(ctx: dict, out_path) -> None:
    """Video 3, the real warehouse: three verified cameras, everyone in them and their PPE, the alerts.

    No floor plan: the recording ships none, and one painted from three
    cameras looking along the floor cannot be trusted (README).
    """
    scene, cams = ctx["scene"], ctx["cams"]
    shown = ctx["shown"]
    res, frames, summary = ctx["result"], ctx["frames"], ctx["summary"]
    site = C.SITE.get(scene, {"zones": [], "lines": []})
    live = ctx.get("ppe_live") or {}
    a = ctx.get("alignment") or {}

    kpis = _row(ui.M, ui.W - ui.M, 68, 88, 6)
    TW, TH = 638, 359
    tiles = [(16, 168), (666, 168), (16, 539)]
    roster_box = (666, 539, 1304, 898)
    system_box = (16, 910, 1304, 1012)
    feed_box = (1316, 168, 1904, 1012)
    timeline_box = (16, 1024, 1904, 1064)
    bg = ui.board(kpis + [roster_box, system_box, feed_box, timeline_box])
    overlays = {c: R.CameraOverlay(cams[c], (TW, TH), site["zones"], site["lines"]) for c in shown}
    readers = {c: R.Reader(Path(ctx["video_path"](c)), frames[0].frame, ctx["stride"]) for c in shown}
    confirmed = res.confirmed_ids()
    evs = ops.events(scene, summary, ctx.get("ppe_events"))
    snaps = _snapshots(evs, ctx, shown)
    memory = {c: {} for c in shown}
    robot_moving = 0
    robot_seen = 0
    since: dict[int, float] = {}            # when each person's current missing PPE began
    accuracy = _ppe_accuracy(scene)
    rejected = sorted(a.get("rejected", []))
    miscal = [c for c in rejected if (a.get("cameras", {}).get(c, {}).get("matches_with_others") or 0) > 0]
    untestable = [c for c in rejected if c not in miscal]
    out = R.VideoOut(out_path, 10.0)
    for fr in frames:
        canvas = bg.copy()
        k2g, seen = R.key_index(res.blobs.get(fr.frame, []), confirmed)
        now = live.get(fr.frame, {})
        imgs = {c: readers[c].get(fr.frame) for c in shown}
        marks = []
        for k, cid in enumerate(shown):
            rows, classes = ctx["detections"][cid]
            pic, mk = R.camera_view(imgs[cid], overlays[cid], rows, classes, fr.frame, fr, k2g, confirmed,
                                    big=True, ppe=now if live else None,
                                    header=(ui.CAMERA[k], ops.cam_label(cid), ops.camera_name(scene, cid),
                                            fr.camera_people.get(cid, 0)), memory=memory[cid])
            ui.paste_rounded(canvas, pic, tiles[k], 10)
            marks.append((mk, *tiles[k]))
        people = sorted((o for o in fr.objects if o.cls == "person"), key=lambda o: o.gid)
        for o in people:
            st = now.get(o.gid)
            if st is not None and not all(st):
                since.setdefault(o.gid, fr.t)
            elif st is not None:
                since.pop(o.gid, None)
        robots = [o for o in fr.objects if o.cls == "robot"]
        robot_seen += sum(o.reliable for o in robots)
        robot_moving += sum(o.reliable and o.speed > C.VEHICLE_MOVING_MS for o in robots)
        # the roster's thumbnails: each person as the camera on screen that shows them largest
        thumbs = {}
        for b in res.blobs.get(fr.frame, []):
            if b.cls != "person":
                continue
            best = None
            for m in b.members:
                if m.cam not in shown or m.track < 0:
                    continue
                rws = ctx["detections"][m.cam][0]
                r = rws[(rws[:, 0] == fr.frame) & (rws[:, 1] == m.track)]
                if len(r) and (best is None or r[0, 5] - r[0, 3] > best[1][3] - best[1][1]):
                    best = (m.cam, r[0, 2:6])
            if best:
                c, (x1, y1, x2, y2) = best
                img = imgs[c]
                x1, y1, x2, y2 = int(max(0, x1)), int(max(0, y1)), int(min(img.shape[1], x2)), int(min(img.shape[0], y2))
                if x2 - x1 > 4 and y2 - y1 > 8:
                    thumbs[b.gid] = img[y1:y2, x1:x2]

        cv = ui.Canvas(canvas)
        for mk_, x, y in marks:
            mk_.draw(cv, x, y)
        walking = sum(o.walking for o in people)
        n, helm, vest, both = ops.ppe_now(now, [o.gid for o in people])
        n_ppe = _count(evs, "ppe", fr.t)
        n_idle = _count(evs, "idle", fr.t)
        cv.kpi(kpis[0], "groups", "Orang di area", f"{len(people)}",
               f"{walking} bergerak · {len(people) - walking} diam · unik di 3 kamera", ui.CYAN)
        cv.kpi(kpis[1], "engineering", "APD lengkap", f"{both}/{n}" if n else "–",
               f"helm {helm} · rompi {vest} · dinilai {n} dari {len(people)} orang" if n
               else "belum ada yang bisa dinilai", ui.GREEN, ui.RED if n and both == 0 else ui.TEXT)
        cv.kpi(kpis[2], "gpp_bad", "Peringatan APD", f"{n_ppe}", "≥ 2 detik tanpa helm / rompi",
               ui.AMBER, _alert_value(n_ppe, "ppe"))
        rstate = "bergerak" if any(o.reliable and o.speed > C.VEHICLE_MOVING_MS for o in robots) else "diam"
        cv.kpi(kpis[3], "smart_toy", "Robot AMR", f"{len(robots)}",
               (f"R{robots[0].gid} {rstate} · bergerak {robot_moving / max(robot_seen, 1):.0%} dari waktunya"
                if robots else "tidak terlihat"), ui.VIOLET)
        cv.kpi(kpis[4], "hourglass_bottom", "Diam ≥ 15 detik", f"{n_idle}", "orang berdiri di satu titik", ui.SLATE)
        cv.kpi(kpis[5], "videocam", "Kamera dipakai", f"{len(ctx['used'])}/{ctx['cameras_total']}",
               f"{len(rejected)} tidak lolos uji posisi", ui.BLUE)
        # the roster: everyone in the area now, PPE first
        y = cv.card_title(roster_box, "Orang di area & APD", "badge")
        lx = roster_box[2] - 16                  # what the dots at the end of each row mean
        for kk in reversed(range(len(shown))):
            b = cv.text((lx, roster_box[1] + 20), ops.cam_label(shown[kk]), 11, "regular", ui.TEXT_3, anchor="rm")
            cv.dot((b[0] - 8, roster_box[1] + 20), 4, ui.CAMERA[kk])
            lx = b[0] - 20
        cv.text((lx, roster_box[1] + 20), "terlihat di", 11, "regular", ui.TEXT_3, anchor="rm")
        order = sorted(people, key=lambda o: (now.get(o.gid) is None, all(now.get(o.gid) or (False,)), o.gid))
        rh = 38
        for k, o in enumerate(order[:int((roster_box[3] - 10 - y) // rh)]):
            yy = y + k * rh
            x0 = roster_box[0] + 14
            if k % 2 == 0:
                cv.rrect((roster_box[0] + 8, yy, roster_box[2] - 8, yy + rh - 4), r=6, fill=ui.SURFACE_2)
            th = thumbs.get(o.gid)
            if th is not None:
                t = cv2.resize(th, (24, 32), interpolation=cv2.INTER_AREA)
                cv.im.paste(Image.fromarray(cv2.cvtColor(t, cv2.COLOR_BGR2RGB)), (x0, yy + 1),
                            ui.rounded_mask(24, 32, 4))
            cv.text((x0 + 34, yy + 17), f"P{o.gid}", 13, "semibold", ui.TEXT, anchor="lm")
            st = now.get(o.gid) if live else None
            h_, v_ = st if st else (None, None)
            bx = x0 + 84
            for name, state in (("helmet", h_), ("vest", v_)):
                cv.dot((bx + 11, yy + 17), 11, ui.STATE[state])
                cv.pictogram(name, (bx + 11, yy + 17), 15)
                bx += 26
            if st is None:
                status, rgb = "belum bisa dinilai", ui.TEXT_3
            elif all(st):
                status, rgb = "APD lengkap", ui.GREEN
            else:
                miss = " & ".join(w for w, ok in (("helm", h_), ("rompi", v_)) if not ok)
                status, rgb = f"tanpa {miss} · {fr.t - since.get(o.gid, fr.t):.0f} s", ui.AMBER
            cv.text((bx + 8, yy + 17), status, 12, "medium", rgb, anchor="lm")
            cv.icon("directions_walk" if o.walking else "accessibility_new", (roster_box[2] - 140, yy + 17), 16,
                    ui.TEXT_2)
            cv.text((roster_box[2] - 128, yy + 17), "bergerak" if o.walking else "diam", 12, "regular", ui.TEXT_2,
                    anchor="lm")
            dx = roster_box[2] - 22
            for kk, c in reversed(list(enumerate(shown))):     # which cameras on screen see them
                cv.dot((dx, yy + 17), 4, ui.CAMERA[kk] if c in seen.get(o.gid, ()) else ui.BORDER)
                dx -= 11
        # the system's own health
        y = system_box[1]
        cv.icon("health_and_safety", (system_box[0] + 26, y + 26), 20, ui.GREEN)
        cv.text((system_box[0] + 44, y + 26), "Status sistem", 14, "semibold", ui.TEXT, anchor="lm")
        col = [system_box[0] + 16, system_box[0] + 440, system_box[0] + 860]
        ag = ctx.get("agreement")
        cv.text((col[0], y + 56), f"{len(ctx['used'])} dari {ctx['cameras_total']} kamera dipakai", 13, "medium",
                ui.TEXT, anchor="lm")
        why = []
        for group, reason in ((miscal, "posisi meleset"), (untestable, "tak bisa diuji")):
            if group:
                why.append("CAM " + ", ".join(c.replace("Camera_", "") for c in group) + f": {reason}")
        cv.text((col[0], y + 78), cv.fit("; ".join(why), 12, "regular", 410), 12, "regular", ui.TEXT_3, anchor="lm")
        cv.text((col[1], y + 56), f"Posisi antar-kamera sepakat {ui.num(ag, 2)} m" if ag is not None else "", 13,
                "medium", ui.TEXT, anchor="lm")
        cv.text((col[1], y + 78), "selisih median orang yang sama di dua kamera", 12, "regular", ui.TEXT_3,
                anchor="lm")
        cv.text((col[2], y + 56), "Aturan APD (PoC): helm & rompi wajib di seluruh area", 13, "medium", ui.TEXT,
                anchor="lm")
        cv.text((col[2], y + 78), cv.fit(accuracy or "", 12, "regular", system_box[2] - col[2] - 16), 12, "regular",
                ui.TEXT_3, anchor="lm")
        _feed(cv, feed_box, evs, snaps, fr.t, row_h=78)
        cv.topbar("3 kamera terverifikasi", "Gudang nyata", "Putar ulang", fr.t, TOTAL_S,
                  ["Data nyata NVIDIA", "tanpa denah lantai"])
        cv.timeline(timeline_box, fr.t, TOTAL_S, evs)
        out.write(cv.bgr())
    out.close()
