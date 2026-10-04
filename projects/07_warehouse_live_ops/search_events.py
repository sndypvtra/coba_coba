#!/usr/bin/env python3
"""#19 - Ask the recording a question in plain Indonesian, get the moments back.

Every event the analytics found (near misses, speeding, people still for too
long, line crossings, people entering the forklift lane, going the wrong way,
crowds) is stored with its time, its place in metres and the cameras that saw
it. This reads a question, works out what kind of event, who, where and when
it asks about, and lists the matching moments with the video time to jump to.
With --clip it also cuts each moment out of the rendered video.

It runs offline and understands questions by their words, not with a language
model: event words (nyaris, ngebut, diam, melintas, jalur forklift, salah arah,
kerumunan), names (P12, F3, CCTV 0005, Garis A, a zone), time (setelah detik
10, sebelum 00:20, antara 5 dan 15 detik) and order (terdekat, terlama,
tercepat). What it did not understand it says, instead of guessing.

    python search_events.py "nyaris tertabrak forklift setelah detik 10"
    python search_events.py "siapa yang diam lama di area kerja timur"
    python search_events.py "orang masuk jalur forklift terlihat CCTV 0005" --clip
    python search_events.py "kerumunan" --video 2
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C  # noqa: E402
from analytics import inside  # noqa: E402
from config import output_dir  # noqa: E402

VIDEOS = {1: ("warehouse_000", "video1_live_ops"), 2: ("warehouse_000", "video2_one_camera"),
          3: ("warehouse_027", "video3_real")}

# multi-word phrases are tried first, so "jalur forklift" is not read as "forklift"
WORDS = [
    ("lane", ["jalur forklift", "jalur kendaraan", "masuk jalur", "di jalur", "lajur forklift"]),
    ("wrong_way", ["salah arah", "lawan arah", "berlawanan arah", "melawan arah", "wrong way"]),
    ("near_miss", ["nyaris", "hampir tertabrak", "hampir ditabrak", "tertabrak", "ditabrak", "tabrakan",
                   "near miss", "nearmiss", "berbahaya", "bahaya"]),
    ("speeding", ["ngebut", "kebut", "kencang", "terlalu cepat", "melebihi batas", "kecepatan", "speeding"]),
    ("idle", ["diam lama", "diam", "berhenti", "tidak bergerak", "menganggur", "idle", "berdiri lama"]),
    ("crossing", ["melintasi", "melintas", "lintasan", "menyeberang", "lewat garis", "garis", "crossing"]),
    ("crowd", ["kerumunan", "berkerumun", "ramai", "padat", "crowd", "menumpuk"]),
]
NAME = {"near_miss": "nyaris tertabrak", "speeding": "forklift ngebut", "idle": "diam lama",
        "crossing": "melintas garis", "lane": "masuk jalur forklift", "wrong_way": "salah arah",
        "crowd": "kerumunan"}
GENERIC = {"area", "zona", "jalur", "lorong", "contoh", "garis", "tengah", "forklift"}


# ------------------------------------------------------------------ events
def load_events(video: int) -> tuple[list[dict], dict]:
    scene, name = VIDEOS[video]
    data = json.loads((output_dir(scene) / f"{name}.json").read_text())
    a = data["analytics"]
    ev = []
    for e in a["#11_near_miss"]["events"]:
        ev.append({"type": "near_miss", "t": e.get("t", e["start_t"]), "start_t": e["start_t"],
                   "who": [f"P{e['person']}", f"F{e['forklift']}"], "x": e["x"], "y": e["y"],
                   "cams": e.get("cams", []), "value": e["min_m"],
                   "detail": f"jarak {e['min_m']:.1f} m dari badan forklift".replace(".", ",")
                   + (f", forklift {e['forklift_kmh']:.0f} km/j" if "forklift_kmh" in e else "")})
    for e in a["#10_speeding"]["events"]:
        ev.append({"type": "speeding", "t": e["start_t"], "who": [f"F{e['gid']}"], "x": e["x"], "y": e["y"],
                   "cams": e.get("cams", []), "value": e["max_kmh"],
                   "detail": f"puncak {e['max_kmh']:.1f} km/j (batas {a['#10_speeding']['limit_kmh']:.0f})"
                   .replace(".", ",")})
    for e in a["#8_idle"]["events"]:
        ev.append({"type": "idle", "t": e["start_t"], "who": [f"P{e['gid']}"], "x": e["x"], "y": e["y"],
                   "cams": e.get("cams", []), "value": e["seconds"],
                   "detail": f"diam {e['seconds']:.0f} s dalam radius {C.IDLE_RADIUS_M:g} m".replace(".", ",")})
    for e in a["#3_crossings"]:
        ev.append({"type": "crossing", "t": e["t"], "who": [f"P{e['gid']}"], "x": e.get("x"), "y": e.get("y"),
                   "cams": e.get("cams", []), "line": e["line"], "dir": e["dir"], "value": 0,
                   "detail": f"{e['line'].split(' ·')[0]}, {'masuk' if e['dir'] == 'in' else 'keluar'}"})
    for e in a["#12_vehicle_lane"].get("events", []):
        ev.append({"type": "lane", "t": e["t"], "who": [f"P{e['gid']}"], "x": e["x"], "y": e["y"],
                   "cams": e.get("cams", []), "value": 0, "detail": "orang masuk jalur forklift"})
    for e in a["#13_wrong_way"]["events"]:
        ev.append({"type": "wrong_way", "t": e["t"], "who": [f"P{e['gid']}"], "x": e["x"], "y": e["y"],
                   "cams": e.get("cams", []), "value": 0, "detail": e["zone"]})
    for e in a["#7_congestion"].get("events", []):
        ev.append({"type": "crowd", "t": e["start_t"], "who": [f"P{g}" for g in e["people"]],
                   "x": e["x"], "y": e["y"], "cams": e.get("cams", []), "value": e["people_max"],
                   "detail": f"{e['people_max']} orang dalam {C.CROWD_RADIUS_M:g} m, "
                             f"{e['end_t'] - e['start_t']:.0f} s".replace(".", ",")})
    return sorted(ev, key=lambda e: e["t"]), data


# ------------------------------------------------------------------ question
def _seconds(s: str) -> float:
    if ":" in s:
        m, sec = s.split(":")
        return int(m) * 60 + float(sec)
    return float(s.replace(",", "."))


def parse(q: str, scene: str) -> dict:
    """What a question asks for. Everything recognised is removed, the rest reported."""
    text = " " + q.lower().strip() + " "
    want: dict = {"types": [], "who": [], "cams": [], "zones": [], "lines": [], "dir": None,
                  "after": None, "before": None, "order": None, "unknown": []}

    def take(pattern: str):
        nonlocal text
        m = re.search(pattern, text)
        if m:
            text = text[:m.start()] + " " + text[m.end():]
        return m

    num = r"(\d+(?::\d+)?(?:[.,]\d+)?)"
    if m := take(rf"antara\s+(?:detik\s+|menit\s+)?{num}\s*(?:s|detik)?\s*(?:dan|-|sampai|hingga)\s*{num}\s*(?:s|detik)?"):
        want["after"], want["before"] = _seconds(m[1]), _seconds(m[2])
    if m := take(rf"(?:setelah|sesudah|lewat|mulai|dari)\s+(?:detik\s+|menit\s+)?(?:ke-?)?{num}\s*(?:s|detik)?"):
        want["after"] = _seconds(m[1])
    if m := take(rf"(?:sebelum|sampai|hingga)\s+(?:detik\s+|menit\s+)?(?:ke-?)?{num}\s*(?:s|detik)?"):
        want["before"] = _seconds(m[1])
    while m := take(r"\b(?:cctv|kamera|camera)[\s_]*(\d{1,4})\b"):
        want["cams"].append(f"Camera_{int(m[1]):04d}")
    site = C.SITE.get(scene, {"zones": [], "lines": []})
    while m := take(r"\bgaris\s+([a-z])\b"):
        want["lines"] += [ln.name for ln in site["lines"] if ln.name.lower().startswith(f"garis {m[1]}")]
    for z in site["zones"]:
        key = z.name.lower().split(" (")[0]
        if key in text:
            want["zones"].append(z)
            text = text.replace(key, " ")
            continue
        words = [w for w in re.findall(r"[a-z]+", key) if len(w) >= 5 and w not in GENERIC]
        if words and all(w in text for w in words):
            want["zones"].append(z)
            for w in words:
                text = text.replace(w, " ")
    while m := take(r"\b([pftr])\s*-?\s*(\d+)\b"):
        want["who"].append(f"{m[1].upper()}{int(m[2])}")
    while m := take(r"\b(?:orang|person)\s+(?:nomor\s+|no\.?\s*)?(\d+)\b"):
        want["who"].append(f"P{int(m[1])}")
    while m := take(r"\bforklift\s+(?:nomor\s+|no\.?\s*)?(\d+)\b"):
        want["who"].append(f"F{int(m[1])}")
    for t, phrases in WORDS:
        for p in phrases:
            if re.search(rf"\b{re.escape(p)}\b", text):
                if t not in want["types"]:
                    want["types"].append(t)
                text = re.sub(rf"\b{re.escape(p)}\b", " ", text)
    if take(r"\bmasuk\b"):
        want["dir"] = "in"
    if take(r"\bkeluar\b"):
        want["dir"] = "out"
    if want["dir"] and not want["types"]:
        want["types"].append("crossing")
    for order, pats in (("value_asc", [r"terdekat", r"paling dekat"]),
                        ("value_desc", [r"terlama", r"paling lama", r"tercepat", r"paling cepat", r"terbesar",
                                        r"terpadat", r"paling ramai"]),
                        ("time_desc", [r"terakhir", r"terbaru"]), ("time_asc", [r"pertama", r"paling awal"])):
        for p in pats:
            if take(rf"\b{p}\b"):
                want["order"] = order
    if want["order"] == "value_asc" and "near_miss" not in want["types"] and not want["types"]:
        want["types"].append("near_miss")
    filler = {"siapa", "yang", "ada", "apa", "apakah", "kapan", "di", "ke", "dan", "atau", "oleh", "dengan",
              "dalam", "pada", "saat", "ketika", "orang", "forklift", "terlihat", "tampilkan", "cari",
              "carikan", "semua", "kejadian", "momen", "detik", "s", "berapa", "tolong", "lihat", "dilihat",
              "the", "yg", "nya", "sekitar", "area", "zona", "dekat", "seseorang", "pekerja", "lama", "kali",
              "ini", "itu", "video", "rekaman", "cctv", "kamera", "lewat", "terjadi", "saja", "mana",
              "bagaimana", "tunjukkan", "list", "daftar", "waktu", "jam"}
    want["unknown"] = [w for w in re.findall(r"[a-z0-9:]+", text) if w not in filler]
    return want


def search(events: list[dict], want: dict) -> list[dict]:
    out = []
    for e in events:
        if want["types"] and e["type"] not in want["types"]:
            continue
        if want["who"] and not any(w in e["who"] for w in want["who"]):
            continue
        if want["cams"] and not any(c in e["cams"] for c in want["cams"]):
            continue
        if want["lines"] and e.get("line") not in want["lines"]:
            continue
        if want["dir"] and e["type"] == "crossing" and e["dir"] != want["dir"]:
            continue
        if want["zones"] and (e.get("x") is None or
                              not any(bool(inside(e["x"], e["y"], z.polygon)) for z in want["zones"])):
            continue
        if want["after"] is not None and e["t"] < want["after"]:
            continue
        if want["before"] is not None and e["t"] > want["before"]:
            continue
        out.append(e)
    if want["order"] == "value_asc":
        out.sort(key=lambda e: e["value"])
    elif want["order"] == "value_desc":
        out.sort(key=lambda e: -e["value"])
    elif want["order"] == "time_desc":
        out.sort(key=lambda e: -e["t"])
    return out


def _area(poly) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(poly, list(poly[1:]) + [poly[0]]))) / 2


def where(e: dict, scene: str) -> str:
    """The most specific zone the event is in (zones overlap), and the point in metres."""
    if e.get("x") is None:
        return "-"
    zones = [z for z in C.SITE.get(scene, {"zones": []})["zones"] if bool(inside(e["x"], e["y"], z.polygon))]
    zs = [z.name for z in sorted(zones, key=lambda z: _area(z.polygon))]
    xy = f"({e['x']:.1f}; {e['y']:.1f}) m".replace(".", ",")
    return f"{zs[0]} {xy}" if zs else xy


def clip(video: int, e: dict, n: int, folder: Path) -> Path:
    """Six seconds of the rendered video around the moment."""
    import imageio_ffmpeg
    scene, name = VIDEOS[video]
    src = output_dir(scene) / f"{name}.mp4"
    folder.mkdir(parents=True, exist_ok=True)
    dst = folder / f"{n:02d}_{e['type']}_{e['t']:.0f}s.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", f"{max(0.0, e['t'] - 3):.1f}",
                    "-i", str(src), "-t", "6", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-pix_fmt", "yuv420p", "-an", str(dst)], check=True)
    return dst


def describe(want: dict) -> str:
    parts = [", ".join(NAME[t] for t in want["types"]) or "semua jenis kejadian"]
    if want["who"]:
        parts.append("melibatkan " + ", ".join(want["who"]))
    if want["zones"]:
        parts.append("di " + ", ".join(z.name for z in want["zones"]))
    if want["lines"]:
        parts.append("di " + ", ".join(ln.split(" ·")[0] for ln in want["lines"]))
    if want["dir"] and "crossing" in want["types"]:
        parts.append("arah " + ("masuk" if want["dir"] == "in" else "keluar"))
    if want["cams"]:
        parts.append("terlihat " + ", ".join(c.replace("Camera_", "CCTV ") for c in want["cams"]))
    if want["after"] is not None:
        parts.append(f"setelah detik {want['after']:g}")
    if want["before"] is not None:
        parts.append(f"sebelum detik {want['before']:g}")
    return " · ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("question", nargs="+")
    ap.add_argument("--video", type=int, choices=[1, 2, 3], default=1)
    ap.add_argument("--clip", action="store_true", help="cut each moment (up to 10) from the rendered video")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()
    q = " ".join(args.question)
    scene = VIDEOS[args.video][0]
    events, data = load_events(args.video)
    want = parse(q, scene)
    hits = search(events, want)
    print(f"Pertanyaan : {q}")
    print(f"Dipahami   : {describe(want)}")
    if want["unknown"]:
        print(f"Tidak dipahami (diabaikan): {', '.join(want['unknown'])}")
    print(f"Ditemukan  : {len(hits)} dari {len(events)} kejadian dalam video {args.video}\n")
    if not hits:
        print("Contoh: 'nyaris tertabrak terdekat', 'forklift ngebut', 'diam lama di staging',\n"
              "        'P12', 'melintasi garis A masuk', 'jalur forklift CCTV 0005', 'kerumunan setelah detik 10'")
        return 0
    print(f"{'waktu':>6}  {'kejadian':20s} {'siapa':12s} {'tempat':38s} {'CCTV yang melihat':26s} keterangan")
    for n, e in enumerate(hits[:args.limit], 1):
        t = f"{int(e['t']) // 60:02d}:{int(e['t']) % 60:02d}"
        who = ", ".join(e["who"][:3]) + (" …" if len(e["who"]) > 3 else "")
        cams = ", ".join(c.replace("Camera_", "") for c in e["cams"]) or "-"
        print(f"{t:>6}  {NAME[e['type']]:20s} {who:12s} {where(e, scene):38s} {cams:26s} {e['detail']}")
    if len(hits) > args.limit:
        print(f"   … dan {len(hits) - args.limit} lagi (--limit)")
    if args.clip:
        folder = output_dir(scene) / "search_clips"
        for n, e in enumerate(hits[:10], 1):
            print("klip:", clip(args.video, e, n, folder))
    return 0


if __name__ == "__main__":
    sys.exit(main())
