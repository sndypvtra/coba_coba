#!/usr/bin/env python3
"""The accuracy report: one picture of every number the videos rest on.

Reads what main.py measured (output/<scene>/video*.json and the geometry check)
and draws docs/accuracy_report.jpg. Nothing here measures anything itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import draw as dr  # noqa: E402
from config import DOCS, output_dir  # noqa: E402

W, H = 1920, 1330
NAME = {"zero_shot": "zero-shot", "site": "dilatih", "hybrid": "hybrid"}


def pct(x) -> str:
    return "-" if x is None else f"{100 * x:.0f}%"


def m(x) -> str:
    return "-" if x is None else f"{x:.2f} m".replace(".", ",")


def num(x, d: int = 1) -> str:
    if x is None:
        return "-"
    if isinstance(x, int):
        return str(x)
    return f"{x:.{d}f}".replace(".", ",")


class Sheet:
    def __init__(self):
        self.img = np.full((H, W, 3), dr.BG, np.uint8)
        self.T = dr.Texts()

    def head(self, n: int, title: str, x: int, y: int) -> None:
        self.T.add(f"{n}", (x, y), 18, dr.WARN, True)
        self.T.add(title, (x + self.T.width(str(n), 18, True) + 12, y), 18, dr.INK, True)

    def table(self, x: int, y: int, cols: list[int], rows: list[list[str]], header: list[str] | None = None,
              size: int = 14, step: int = 23, colours: list | None = None) -> int:
        """cols: right edge of every column after the first (left-aligned) one."""
        if header:
            self.T.add(header[0], (x, y), 12, dr.MUTED, True)
            for c, h in zip(cols, header[1:]):
                self.T.add(h, (c, y), 12, dr.MUTED, True, anchor="ra")
            y += 20
        for i, r in enumerate(rows):
            col = colours[i] if colours else dr.INK
            self.T.add(r[0], (x, y), size, col)
            for c, v in zip(cols, r[1:]):
                self.T.add(v, (c, y), size, col, True, anchor="ra")
            y += step
        return y

    def save(self, path: Path) -> None:
        self.T.flush(self.img)
        cv2.imwrite(str(path), self.img, [cv2.IMWRITE_JPEG_QUALITY, 90])


def build() -> Path:
    v1 = json.loads((output_dir("warehouse_000") / "video1_live_ops.json").read_text())
    geo = json.loads((output_dir("warehouse_000") / "geometry.json").read_text())
    p2 = output_dir("warehouse_000") / "video2_one_camera.json"
    v2 = json.loads(p2.read_text()) if p2.exists() else None
    p3 = output_dir("warehouse_027") / "video3_real.json"
    v3 = json.loads(p3.read_text()) if p3.exists() else None
    acc = v1["accuracy"]
    det = acc["detector"]
    other = acc.get("other_detector", {})
    order = ["zero_shot", "site", "hybrid"]
    both = sorted([det] + list(other), key=order.index)
    by = {det: acc, **other}
    S = Sheet()
    T = S.T
    w = v1["window"]
    T.add("SEBERAPA AKURAT?", (40, 26), 30, dr.INK, True)
    T.add(f"Diukur terhadap label dataset NVIDIA (posisi 3D dan kotak 2D setiap orang dan kendaraan) · "
          f"Warehouse_000, detik {w['start_s']:.0f}-{w['end_s']:.0f} · {len(v1['analytics']['#1_people_per_camera'])} "
          f"CCTV · video memakai detektor {NAME[det]}", (40, 68), 16, dr.MUTED)

    # ------------------------------------------------------------ column 1
    x, y = 40, 116
    S.head(1, "CCTV vs PETA", x, y)
    passed = [c for c, v in geo["cameras"].items() if v["passed"]]
    T.add(f"{len(passed)} dari {len(geo['cameras'])} CCTV lolos uji kalibrasi", (x, y + 30), 24, dr.GOOD, True)
    T.add("lolos = kaki orang (label) jatuh di titik yang dihitung: bias ≤ 6 px, meleset ≤ 0,30 m", (x, y + 62),
          13, dr.MUTED)
    fails = sorted((c, v["verdict"]) for c, v in geo["cameras"].items() if not v["passed"])
    for i, (c, why) in enumerate(fails):
        T.add(f"{c.replace('Camera_', 'CCTV ')}  {why}".replace(".", ","), (x, y + 86 + i * 20), 13, dr.BAD)
    meds = [v["labels"]["floor_m_median"] for v in geo["cameras"].values() if v["passed"]]
    T.add(f"CCTV yang lolos: meleset median {min(meds):.2f}-{max(meds):.2f} m".replace(".", ","),
          (x, y + 90 + len(fails) * 20), 13, dr.INK)

    y = 330
    S.head(2, "DETEKTOR: KOTAK DI GAMBAR CCTV", x, y)
    cols = [x + 560 - 95 * (len(both) - 1 - i) for i in range(len(both))]
    rows = []
    for cls, name in (("person", "Orang"), ("forklift", "Forklift"), ("pallet_truck", "Pallet truck")):
        rows.append([f"{name}: recall"] + [pct(by[d]["boxes_in_the_pictures"][cls]["recall"]) for d in both])
        rows.append([f"{name}: presisi"] + [pct(by[d]["boxes_in_the_pictures"][cls]["precision"]) for d in both])
    y = S.table(x, y + 32, cols, rows, ["IoU ≥ 0,4 · label ≥ 20 px"] + [NAME[d] for d in both])
    T.add("dilatih = YOLO11n, 6 epoch di CPU, frame di luar jendela uji (#18)", (x, y + 2), 12, dr.MUTED)
    T.add("hybrid = orang dari zero-shot, kendaraan dari dilatih (dipakai video)", (x, y + 18), 12, dr.MUTED)

    y = 568
    S.head(3, "ORANG DI PETA", x, y)
    rows = []
    for key, name in (("precision", "Presisi (titik = orang sungguhan, ≤ 1 m)"),
                      ("recall_seeable", "Recall: yang terlihat CCTV (≥ 40 px)"),
                      ("recall_all_on_floor", "Recall: semua orang di gedung")):
        rows.append([name] + [pct(by[d]["people_on_plan"][key]) for d in both])
    rows.append(["Posisi meleset, median"] + [m(by[d]["people_on_plan"]["position_error_m_median"]) for d in both])
    rows.append(["Posisi meleset, 90% di bawah"] + [m(by[d]["people_on_plan"]["position_error_m_p90"])
                                                    for d in both])
    rows.append(["ID per orang (1,0 = tak pernah ganti)"] + [num(by[d]["people_on_plan"]["plan_ids_per_label_mean"],
                                                                  2) for d in both])
    y = S.table(x, y + 32, cols, rows, [""] + [NAME[d] for d in both])
    T.add(f"Tinggi orang terukur dari kotak + kalibrasi: median {m(acc['person_height']['median_m'])}",
          (x, y + 2), 13, dr.MUTED)

    y = 810
    S.head(4, "KENDARAAN DI PETA", x, y)
    rows = []
    for k, name in (("forklifts_on_plan", "Forklift"), ("pallet_trucks_on_plan", "Pallet truck")):
        rows.append([f"{name}: presisi (≤ 2 m)"] + [pct(by[d][k]["precision"]) for d in both])
        rows.append([f"{name}: recall"] + [pct(by[d][k]["recall_all_on_floor"]) for d in both])
        rows.append([f"{name}: meleset median"] + [m(by[d][k]["position_error_m_median"]) for d in both])
    y = S.table(x, y + 32, cols, rows, [""] + [NAME[d] for d in both])

    # ------------------------------------------------------------ column 2
    x, y = 650, 116
    S.head(5, "ANALYTICS vs KEBENARAN (video 1)", x, y)
    T.add("Label dataset dijalankan lewat kode analytics yang sama persis.", (x, y + 30), 13, dr.MUTED)
    avt = acc["analytics_vs_truth"]
    cols2 = [x + 430, x + 520, x + 610]
    rows = []
    for r in avt["rows"]:
        name = r["analytic"].replace(": okupansi rata-rata", ": okupansi").replace(", rata-rata", "")
        rows.append([name, num(r["ai"]), num(r["truth_seen_by_cameras"]), num(r["truth_whole_floor"])])
    y = S.table(x, y + 56, cols2, rows, ["", "AI", "terlihat", "semua"], size=13, step=21)
    T.add("terlihat = kebenaran yang tampak ≥ 40 px di salah satu CCTV · semua = seluruh gedung", (x, y + 2),
          12, dr.MUTED)

    y += 40
    S.head(6, "KEJADIAN: COCOK DENGAN KEBENARAN?", x, y)
    T.add("cocok = waktu bertumpang (±1 s) dan tempat ≤ 3 m; garis: garis dan arah sama, ±0,5 s", (x, y + 30),
          13, dr.MUTED)
    rows, colours = [], []
    for key, name in (("crossing", "Melintasi garis"), ("near_miss", "Nyaris tertabrak"),
                      ("speeding", "Forklift ngebut"), ("idle", "Diam lama"), ("lane", "Masuk jalur forklift")):
        e = avt["events"][key]["vs_truth_seen"]
        rows.append([name, f"{e['ai']}", f"{e['matched']}", f"{e['truth']}",
                     pct(e["precision"]), pct(e["recall"])])
        good = (e["ai"] == 0 and e["truth"] == 0) or \
            ((e["precision"] or 0) >= 0.7 and (e["recall"] is None or e["recall"] >= 0.5))
        colours.append(dr.INK if good else dr.WARN)
    y = S.table(x, y + 56, [x + 290, x + 360, x + 440, x + 520, x + 610], rows,
                ["", "AI", "cocok", "nyata", "presisi", "recall"], size=13, step=21, colours=colours)
    if other:
        o = list(other)[0]
        e = other[o]["analytics_vs_truth"]["events"]
        T.add("Dengan detektor " + NAME[o] + ": " + " · ".join(
            f"{n} {e[k]['vs_truth_seen']['matched']}/{e[k]['vs_truth_seen']['ai']} benar"
            for k, n in (("near_miss", "nyaris"), ("speeding", "ngebut"), ("lane", "jalur"))), (x, y + 4), 12,
            dr.MUTED)

    # ------------------------------------------------------------ column 3
    x, y = 1310, 116
    S.head(7, "HITUNG ORANG PER CCTV (#1)", x, y)
    cc = acc["#1_people_per_camera_vs_labels"]
    rows = [[c.replace("Camera_", "CCTV "), num(v["ai_mean"]), num(v["label_mean"]), num(v["abs_error_mean"]),
             f"{v['within_1_pct']:.0f}%"] for c, v in sorted(cc.items())]
    y = S.table(x, y + 32, [x + 210, x + 290, x + 380, x + 480], rows, ["", "AI", "label", "selisih", "±1 orang"],
                size=13, step=19)
    T.add("rata-rata per frame, orang ≥ 40 px di gambar CCTV itu sendiri", (x, y + 2), 12, dr.MUTED)

    y += 34
    S.head(8, "PER SUDUT KAMERA (#17)", x, y)
    y += 30
    for g, v in acc["#17_detection_per_camera"]["groups"].items():
        T.add(g, (x, y), 13, dr.INK)
        T.add(f"{v['cameras']} CCTV · recall {pct(v['recall_mean'])} · presisi {pct(v['precision_mean'])}",
              (x + 12, y + 17), 12, dr.MUTED)
        y += 40

    y += 6
    S.head(9, "CAKUPAN LANTAI (#15)", x, y)
    cov = acc["#15_floor_coverage"]
    for i, (name, v, col) in enumerate((("tidak terlihat", cov["seen_by_0_pct"], dr.BAD),
                                         ("1 CCTV", cov["seen_by_1_pct"], dr.WARN),
                                         ("2+ CCTV", cov["seen_by_2plus_pct"], dr.GOOD))):
        yy = y + 32 + i * 24
        T.add(name, (x, yy), 13, dr.INK)
        cv2.rectangle(S.img, (x + 120, yy + 2), (x + 120 + int(v * 3.6), yy + 16), col, -1)
        T.add(f"{v:.0f}%", (x + 128 + int(v * 3.6), yy), 13, dr.INK, True)
    T.add("lantai gedung yang bisa ditempati titik orang (≤ 0,25 m/px); rak tidak dimodelkan",
          (x, y + 108), 12, dr.MUTED)

    y += 140
    S.head(10, "BERAPA CCTV MINIMAL? (#16)", x, y)
    curve = acc["#16_fewest_cameras"]
    cx0, cy0, cw, ch = x + 10, y + 34, 560, 130
    cv2.rectangle(S.img, (cx0, cy0), (cx0 + cw, cy0 + ch), dr.FAINT, 1)
    n0 = curve[0]["cameras"]
    top = max(c["recall_all_on_floor"] for c in curve) * 1.15 or 1
    pts = [(cx0 + int((n0 - c["cameras"]) / max(n0 - 1, 1) * cw), cy0 + ch - int(c["recall_all_on_floor"] / top * ch))
           for c in curve]
    cv2.polylines(S.img, [np.array(pts, np.int32)], False, dr.PERSON, 2, cv2.LINE_AA)
    for p in pts:
        cv2.circle(S.img, p, 3, dr.PERSON, -1, cv2.LINE_AA)
    T.add(f"{n0} CCTV · recall {pct(curve[0]['recall_all_on_floor'])}", (cx0, cy0 + ch + 6), 12, dr.MUTED)
    T.add(f"1 CCTV · {pct(curve[-1]['recall_all_on_floor'])}", (cx0 + cw, cy0 + ch + 6), 12, dr.MUTED, anchor="ra")
    drop = next((c for c in curve if c["recall_all_on_floor"] < 0.9 * curve[0]["recall_all_on_floor"]), None)
    if drop:
        T.add(f"recall turun > 10% baru setelah tersisa {drop['cameras']} CCTV", (x, cy0 + ch + 28), 13, dr.INK, True)
    first = [c["removed"].replace("Camera_", "") for c in curve[1:5] if c["removed"]]
    T.add("paling sedikit menambah: " + ", ".join(first), (x, cy0 + ch + 48), 12, dr.MUTED)

    # ------------------------------------------------------------ the two other videos
    y = 840
    x = 650
    if v2:
        a = v2["accuracy"]["#1_count_vs_labels"]
        S.head(11, "VIDEO 2: SATU CCTV", x, y)
        T.add(f"{v2['window']['camera'].replace('Camera_', 'CCTV ')}: AI {num(a['ai_mean'])} orang per frame, "
              f"label {num(a['label_mean'])}, selisih {num(a['abs_error_mean'])} · ±1 orang di "
              f"{a['within_1_pct']:.0f}% frame", (x, y + 32), 14, dr.INK)
    if v3:
        ag = v3["checks"]["camera_agreement"]["all_pairs"]
        ref = acc.get("camera_agreement", {}).get("all_pairs", {})
        S.head(12, "VIDEO 3: GUDANG ASLI, TANPA LABEL", x, y + 80)
        if ag.get("median_m") is not None:
            T.add(f"Orang yang sama menurut dua CCTV: selisih median {m(ag['median_m'])}, "
                  f"{ag['within_0_5_m_pct']:.0f}% ≤ 0,5 m ({ag['samples']} pasang)", (x, y + 112), 14, dr.INK)
        if ref.get("median_m") is not None:
            T.add(f"pembanding, gudang simulasi dengan kebenaran: {m(ref['median_m'])}, "
                  f"{ref['within_0_5_m_pct']:.0f}% ≤ 0,5 m", (x, y + 136), 13, dr.MUTED)
        h = v3["checks"]["person_height"]["median_m"]
        if h:
            T.add(f"Tinggi orang terukur (median) {m(h)}: skala meter kalibrasi masuk akal", (x, y + 160), 14, dr.INK)
    _ppe_band(S, v2, v3)
    DOCS.mkdir(exist_ok=True)
    out = DOCS / "accuracy_report.jpg"
    S.save(out)
    return out


def _ppe_band(S: Sheet, v2: dict | None, v3: dict | None) -> None:
    """#21 across the bottom: the PPE detector's test split, the blind check by eye, false alarms, violations."""
    from config import OUTPUT
    T = S.T
    info_p = OUTPUT / "ppe_detector.json"
    if not info_p.exists():
        return
    info = json.loads(info_p.read_text())
    scores = {v: json.loads(p.read_text()) for v, p in ((2, output_dir("warehouse_000") / "ppe_audit_score.json"),
                                                         (3, output_dir("warehouse_027") / "ppe_audit_score.json"))
              if p.exists()}
    y0 = 1066
    cv2.line(S.img, (40, y0 - 12), (W - 40, y0 - 12), dr.FAINT, 1)
    x = 40
    S.head(13, "APD: HELM & ROMPI (#21)", x, y0)
    T.add(f"YOLO11n dilatih {info['minutes_on_cpu']:.0f} menit di CPU pada Construction-PPE (Ultralytics);",
          (x, y0 + 30), 13, dr.MUTED)
    T.add("split test-nya sendiri, tidak dipakai melatih:", (x, y0 + 48), 13, dr.MUTED)
    pc = info["test_split"]["per_class"]
    rows = [[name, pct(pc[k]["precision"]), pct(pc[k]["recall"]), pct(pc[k]["mAP50"])]
            for k, name in (("helmet", "Helm"), ("vest", "Rompi")) if k in pc]
    y = S.table(x, y0 + 74, [x + 330, x + 430, x + 530], rows, ["", "presisi", "recall", "mAP50"])
    T.add("Di CCTV: tiap orang ≥ 100 px dipotong dan dibaca sendiri; rompi harus disetujui CLIP", (x, y + 4), 12,
          dr.MUTED)
    T.add("(ViT-B/32) yang memilih di antara 9 jenis pakaian.", (x, y + 20), 12, dr.MUTED)

    x = 650
    S.head(14, "DICEK MATA: SAMPEL UJI BUTA", x, y0)
    T.add("diambil dan dilabel setelah aturan tetap, sebelum putusan AI dilihat; status live (mayoritas 2 s)",
          (x, y0 + 30), 12, dr.MUTED)
    rows = []
    for v in (2, 3):
        sc = scores.get(v, {}).get("check")
        if not sc:
            continue
        for item, name in (("helmet", "helm"), ("vest", "rompi")):
            a = sc[f"{item}_live"]
            rows.append([f"Video {v}, {name}", f"{a['correct']}/{a['labelled']}", a["worn_found"],
                         a["not_worn_found"]])
    S.table(x, y0 + 56, [x + 300, x + 440, x + 600], rows, ["", "benar", "dipakai: ketemu", "tidak: benar"],
            size=13, step=21)

    x = 1310
    S.head(15, "ALARM PALSU & PELANGGARAN", x, y0)
    y = y0 + 34
    a3 = scores.get(3, {}).get("all_crops_called_worn")
    if a3:
        n = f"{a3['judged_crops']:,}".replace(",", ".")
        T.add(f"Gudang asli, tak ada yang memakai APD: dari {n} potongan", (x, y), 13, dr.INK)
        T.add(f"AI bilang helm {100 * a3['helmet']:.1f}% · rompi {100 * a3['vest']:.1f}% "
              f"(detektor saja: {100 * a3['vest_detector_alone']:.0f}%)".replace(".", ","), (x, y + 19), 14, dr.INK,
              True)
        y += 52
    for v, scene in ((2, "warehouse_000"), (3, "warehouse_027")):
        cp = output_dir(scene) / "ppe_violation_check.json"
        if not cp.exists():
            continue
        vs = [e["verdict"] for e in json.loads(cp.read_text())["events"]]
        T.add(f"Video {v}: {len(vs)} pelanggaran (≥ 2 s tanpa helm / rompi), dicek mata:", (x, y), 13, dr.INK)
        T.add(f"{vs.count('real')} nyata · {vs.count('false')} salah · {vs.count('cannot tell')} tak bisa dipastikan",
              (x + 12, y + 19), 13, dr.GOOD if vs.count("false") == 0 else dr.WARN, True)
        y += 46
    T.add("salah di video 2: rompi pucat, hijau muda dan putih yang tak terdeteksi, 2 helm", (x, y + 2), 12,
          dr.MUTED)


if __name__ == "__main__":
    print(build())
