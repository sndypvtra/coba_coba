"""From pixels to what a plant manager reads: run the vision, keep a snapshot per frame, raise events.

    analyse_line(frames)  -> Run   the can line (trays of 10)
    analyse_pack(frames)  -> Run   the packing station (boxes of 20)

A Run holds one snapshot per frame (what is on screen and the running totals
at that moment), the events with their severity, and the calibration found.
`score_*` then checks the run against the scene's ground truth; the truth is
used for nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import vision_line as VL
import vision_pack as VP

CAM = "CAM 01"


@dataclass
class Event:
    frame: int
    t: float
    severity: str              # high / medium / low / info
    icon: str
    title: str
    detail: str
    kind: str
    ref: int                   # tray or box number
    feed: bool = True          # shown in the feed (info events only go on the timeline)
    cams: list = field(default_factory=lambda: [CAM])
    focus: list | None = None  # image box to cut the snapshot from


@dataclass
class Run:
    fps: float
    snaps: list
    events: list
    calibration: dict


def _names(slots, label):
    return ", ".join(label(k) for k in slots)


# ---------------------------------------------------------------- can line
def analyse_line(frames, fps):
    template, n_cal = VL.calibrate(frames)
    ins = VL.LineInspector(template)
    snaps, events = [], []
    judged = []
    for i, fr in enumerate(frames):
        f = i + 1
        live = ins.step(f, fr)
        for t in ins.done[len(judged):]:
            judged.append(t)
            v = t.verdict
            box = list(t.box)
            if v["ok"]:
                events.append(Event(f, i / fps, "info", "check_circle", f"Tray #{t.tid} lengkap",
                                    f"{v['count']}/10 kaleng · lolos", "tray_ok", t.tid, feed=False, focus=box))
            else:
                short = VL.EXPECTED - v["count"]
                events.append(Event(f, i / fps, "high", "production_quantity_limits",
                                    f"Tray #{t.tid} kurang {short} kaleng",
                                    f"{v['count']}/10 · slot {_names(v['empty'], VL.slot_label)} kosong · tandai reject",
                                    "tray_short", t.tid, focus=box))
        rate = None
        if len(judged) >= 2:
            span = (judged[-1].verdict["frame"] - judged[0].verdict["frame"]) / fps
            rate = (len(judged) - 1) / span * 60 if span > 0 else None
        heat = [0] * VL.EXPECTED
        for t in judged:
            for k in t.verdict["empty"]:
                heat[k] += 1
        snaps.append({
            "frame": f,
            "trays": [{"key": t.key, "tid": t.tid, "box": list(t.box),
                       "live": list(t.live) if t.readings and t.readings[-1][0] == f and t.verdict is None else None,
                       "verdict": t.verdict} for t in live],
            "judged": [{"tid": t.tid, "frame": t.verdict["frame"], "count": t.verdict["count"],
                        "ok": t.verdict["ok"], "empty": t.verdict["empty"],
                        "reads": t.verdict["frames_read"]} for t in judged],
            "rate_per_min": rate,
            "heat": heat,
        })
    return Run(fps, snaps, events, {"template": template, "calibrated_on": n_cal,
                                    "zone_x": VL.ZONE_X, "zone_half": VL.ZONE_HALF})


def score_line(run, truth):
    """Every in-zone reading and every verdict against the truth (matched by tray centre)."""
    def nearest(frame, box):
        cx = (box[0] + box[2]) / 2
        trays = truth["frames"][frame - 1]["trays"]
        return min(trays, key=lambda t: abs((t["box"][0] + t["box"][2]) / 2 - cx))

    readings = wrong = 0
    first_seen = {}
    for s in run.snaps:
        for t in s["trays"]:
            if t["live"] is None:
                continue
            tt = nearest(s["frame"], t["box"])
            first_seen.setdefault(t["tid"], tt["tray"])
            readings += 1
            if sum(t["live"]) != tt["packed"]:
                wrong += 1
    verdicts = []
    last = run.snaps[-1]["judged"]
    for v in last:
        tt = truth["trays"][first_seen[v["tid"]]]
        got_slots = sorted(VL.truth_slot(k) for k in v["empty"])
        verdicts.append({"tray": v["tid"], "truth_tray": tt["tray"], "count": v["count"], "truth_count": tt["packed"],
                         "empty_slots": got_slots, "truth_empty_slots": tt["missing_slots"],
                         "correct": v["count"] == tt["packed"] and got_slots == tt["missing_slots"]})
    return {"readings_in_zone": readings, "readings_wrong": wrong,
            "trays_judged": len(verdicts), "trays_correct": sum(v["correct"] for v in verdicts),
            "short_trays_found": sum(1 for v in verdicts if v["count"] < 10),
            "short_trays_in_truth_judged": sum(1 for v in verdicts if v["truth_count"] < 10),
            "verdicts": verdicts}


# ---------------------------------------------------------------- packing station
def analyse_pack(frames_hsv_for_cal, frame_iter, fps):
    cal, n_cal = VP.calibrate(frames_hsv_for_cal)
    ins = VP.PackInspector(cal)
    snaps, events = [], []
    n_ev = 0
    last_station = None                       # the box most recently at the station
    series = []
    for i, fr in enumerate(frame_iter):
        f = i + 1
        live = ins.step(f, fr)
        for e in ins.events[n_ev:]:
            box = next((b for b in live if b.bid == e.get("box")), None)
            focus = list(box.box) if box else None
            lab = VP.slot_label
            if e["kind"] == "feeder_gap":
                events.append(Event(f, i / fps, "low", "conveyor_belt", "Celah suplai di feeder",
                                    f"Stopper kosong · slot {lab(e['slot'])} kardus #{e['box']} berisiko",
                                    "feeder_gap", e["box"], focus=list(cal.feeder_stop)))
            elif e["kind"] == "missed":
                events.append(Event(f, i / fps, "medium", "report", f"Pick kosong · slot {lab(e['slot'])}",
                                    f"Kardus #{e['box']} · robot jalan tanpa produk"
                                    + (" · sebab: celah feeder" if e.get("feeder_gap", 0) >= VP.FEED_WARN else ""),
                                    "missed", e["box"], focus=focus))
            elif e["kind"] == "released":
                short = VP.EXPECTED - e["count"]
                if short:
                    events.append(Event(f, i / fps, "high", "production_quantity_limits",
                                        f"Kardus #{e['box']} keluar kurang {short}",
                                        f"{e['count']}/20 · slot {_names(e['empty'], lab)} kosong · tahan & lengkapi",
                                        "box_short", e["box"], focus=focus))
                else:
                    events.append(Event(f, i / fps, "info", "check_circle", f"Kardus #{e['box']} lengkap",
                                        "20/20 · lanjut ke penutupan", "box_ok", e["box"], feed=True, focus=focus))
        n_ev = len(ins.events)
        station = next((b for b in live if b.arrived is not None and b.left is None), None)
        if station is not None:
            last_station = station
        placed = [e for e in ins.events if e["kind"] == "placed"]
        gaps = [b["frame"] - a["frame"] for a, b in zip(placed, placed[1:]) if a["box"] == b["box"]]
        cycle = float(np.median(gaps)) / fps if gaps else None
        series.append(last_station.count if last_station is not None else None)
        nxt = None
        if station is not None:
            todo = [k for k in range(VP.EXPECTED) if k not in station.filled and k not in station.missed]
            nxt = todo[0] if todo else None
        snaps.append({
            "frame": f,
            "boxes": [{"key": b.key, "bid": b.bid, "box": list(b.box), "count": b.count,
                       "filled": sorted(b.filled), "missed": sorted(b.missed),
                       "state": ("filling" if b is station else "done" if b.verdict else "waiting"),
                       "verdict": b.verdict} for b in live],
            "station": None if last_station is None else {
                "bid": last_station.bid, "count": last_station.count, "filled": sorted(last_station.filled),
                "missed": sorted(last_station.missed), "filling": station is not None, "next": nxt,
                "start_count": last_station.start_count},
            "done": [{"bid": b.bid, "frame": b.verdict["frame"], "count": b.verdict["count"],
                      "ok": b.verdict["ok"], "empty": b.verdict["empty"]} for b in ins.done],
            "missed_total": sum(1 for e in ins.events if e["kind"] == "missed"),
            "feeder_gaps": sum(1 for e in ins.events if e["kind"] == "feeder_gap"),
            "placed_total": len(placed),
            "cycle_s": cycle,
            "feeder_run": ins.feeder_run,
            "feeder_alert": ins.feeder_run >= VP.FEED_WARN and station is not None
                            and station.count + len(station.missed) < VP.EXPECTED,
            "series": series[-1],
        })
    return Run(fps, snaps, events, {"station_cx": cal.station_cx, "template": cal.template,
                                    "pitch_px": cal.pitch_px, "feeder_stop": cal.feeder_stop,
                                    "calibrated_on": n_cal})


def score_pack(run, truth):
    """Count while at the station, the final verdicts and the empty picks, against the truth."""
    cx = run.calibration["station_cx"]
    frames = wrong = 0
    lags = []
    for s in run.snaps:
        st = s["station"]
        if not st or not st["filling"]:
            continue
        tb = [b for b in truth["frames"][s["frame"] - 1]["boxes"] if abs((b["bbox"][0] + b["bbox"][2]) / 2 - cx) < 12]
        if not tb:
            continue
        frames += 1
        if st["count"] != tb[0]["count"]:
            wrong += 1
    placed_truth = [e for e in truth["events"] if e["event"] == "placed"]
    # lag: the frame our count reaches n against the frame the truth reaches n, per box
    by_box = {}
    for s in run.snaps:
        st = s["station"]
        if st and st["filling"]:
            by_box.setdefault(st["bid"], {}).setdefault(st["count"], s["frame"])
    for b, seen in by_box.items():
        tbox = b - 1
        reach = {}
        cnt = truth["boxes"][tbox]["already_in_at_start"]
        for e in placed_truth:
            if e["box"] == tbox:
                cnt += 1
                reach[cnt] = e["frame"]
        for n, fr in seen.items():
            if n in reach:
                lags.append(fr - reach[n])
    done = run.snaps[-1]["done"]
    verdicts = []
    for d in done:
        tb = truth["boxes"][d["bid"] - 1]
        verdicts.append({"box": d["bid"], "count": d["count"], "truth_count": tb["final_count"],
                         "empty": d["empty"], "truth_empty": tb["empty_slots"],
                         "correct": d["count"] == tb["final_count"] and d["empty"] == tb["empty_slots"]})
    missed_found = sorted((e.ref, e.title) for e in run.events if e.kind == "missed")
    last_frame = run.snaps[-1]["frame"]
    missed_truth = [e for e in truth["events"] if e["event"] == "missed" and e["frame"] <= last_frame]
    warn = [e for e in run.events if e.kind == "feeder_gap"]
    lead = []
    for m in missed_truth:
        w = [e for e in warn if e.frame <= m["frame"]]
        if w:
            lead.append(m["frame"] - w[-1].frame)
    return {"station_frames": frames, "station_frames_count_differs": wrong,
            "count_lag_frames": sorted(set(lags)), "count_lag_s": round(float(np.median(lags)) / run.fps, 2) if lags else None,
            "boxes_judged": len(verdicts), "boxes_correct": sum(v["correct"] for v in verdicts), "verdicts": verdicts,
            "empty_picks_found": len(missed_found), "empty_picks_in_truth": len(missed_truth),
            "feeder_warning_before_release_frames": lead}
