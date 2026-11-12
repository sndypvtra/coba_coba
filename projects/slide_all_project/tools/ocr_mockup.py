#!/usr/bin/env python3
"""The OCR use case as it is: the ticket extractor's own result pages (results/single0, multiple0, multiple1), unchanged,
with bounding boxes drawn on them: one box per ticket and one per field the model returned, in the colour of the same
column in the result table, so the eye can follow each value from the ticket to the table.

The boxes come from a text detector (RapidOCR) run on the same pictures, matched to the values the model returned
(mockup/data/ocr_tickets.json); the model itself (Qwen2.5-VL) returns text only, no positions.

    python tools/ocr_mockup.py <results dir> <out dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from rapidocr_onnxruntime import RapidOCR

HERE = Path(__file__).resolve().parent.parent
FONT = HERE / "mockup" / "assets" / "fonts"
FIELDS = [("Tanggal", (37, 99, 235)), ("Stasiun asal", (22, 163, 74)), ("Stasiun tujuan", (13, 148, 136)),
          ("Jam berangkat", (217, 119, 6)), ("Jam tiba", (234, 88, 12)), ("Harga", (124, 58, 237))]
DATE = re.compile(r"\d{4}[./]\d{2}[./]\d{2}")


def font(w: str, s: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT / f"Inter-{w}.ttf"), s)


def union(bs):
    return [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]


def analyse(img: Path, tickets: list[dict], ocr: RapidOCR) -> dict:
    res, _ = ocr(str(img))
    boxes = [([min(p[0] for p in b), min(p[1] for p in b), max(p[0] for p in b), max(p[1] for p in b)], t) for b, t, _ in res]
    head_y = min(b[1] for b, t in boxes if t.strip().upper() in ("DATE", "PRICE", "MILEAGE"))
    top = [(b, t) for b, t in boxes if b[3] < head_y - 20 and t != "OCR Output"]
    rows_txt = [(b, t) for b, t in boxes if b[1] > head_y + 30 and t not in ("Go Back",)]
    dates = sorted([(b, t) for b, t in top if DATE.search(t)], key=lambda x: x[0][0])
    # tickets side by side: each starts where its date starts (the date is printed at its left edge)
    cuts = [-1e9] + [b[0] - 20 for b, _ in dates[1:]] + [1e9]
    out = []
    for k, tk in enumerate(tickets):
        mine = [(b, t) for b, t in top if cuts[k] <= (b[0] + b[2]) / 2 < cuts[k + 1]]
        read = tk["read"]
        f = {}
        f[0] = [b for b, t in mine if DATE.search(t)][:1]
        for j, name in ((1, read[1]), (2, read[2])):
            latin = [b for b, t in mine if t.strip().lower() == name.lower()]
            if not latin:
                latin = [b for b, t in mine if name.lower() in t.lower()]
            # one box round the station's text line: its Latin name and, when printed on the same line just left of it,
            # its Chinese name (a Chinese name on the line above is a different line, left out on every ticket alike)
            if latin:
                lb = latin[0]

                def near(b, lb=lb):
                    ov = min(b[3], lb[3]) - max(b[1], lb[1])
                    return ov > 0.5 * (lb[3] - lb[1]) and -40 <= lb[0] - b[2] < 60
                zh = [b for b, t in mine if re.search(r"[一-鿿]{2}", t) and near(b)
                      and not re.search(r"\d", t) and "鐵" not in t and "局" not in t]
                f[j] = [union([lb] + zh[:1])]
        for j, val in ((3, read[3]), (4, read[4])):
            hit = [b for b, t in mine if val and val in t.replace("：", ":")]
            if not hit and val:
                # the detector joined the time with its neighbour ("30011:19到"): keep the part from the hour on,
                # cut in proportion to the characters
                other = f.get(3) or []
                for b, t in mine:
                    i = t.replace("：", ":").find(val[-3:])
                    if i >= 2:
                        # character width from the other time's box when there is one (noise widens this one)
                        if other:
                            ob = other[0]; ot = next(t2 for b2, t2 in mine if b2 == ob)
                            cw = (ob[2] - ob[0]) / len(ot)
                        else:
                            cw = (b[2] - b[0]) / len(t)
                        hit = [[max(b[0], b[2] - (len(t) - i + 2) * cw), b[1], b[2], b[3]]]
                        break
            f[j] = hit[:1]
        pr = [b for b, t in mine if re.search(r"NT\s*[$S]?\s*\d+", t.replace(" ", ""))]
        f[5] = pr[:1]
        out.append({"ticket": union([b for b, _ in mine]), "fields": f})
    # the result table: rows by height, cells left to right
    rows = []
    for b, t in sorted(rows_txt, key=lambda x: x[0][1]):
        if rows and abs(rows[-1][0][1] - b[1]) < 18:
            rows[-1][1].append((b, t))
        else:
            rows.append((b, [(b, t)]))
    table = [sorted(cells, key=lambda c: c[0][0]) for _, cells in rows]
    return {"tickets": out, "table": table, "head_y": head_y}


def draw(img: Path, a: dict, scale: float, multi: bool) -> Image.Image:
    im = Image.open(img).convert("RGB")
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    S = lambda b, p=0: [b[0] * scale - p, b[1] * scale - p, b[2] * scale + p, b[3] * scale + p]  # noqa: E731
    lw = max(3, round(2.2 * scale))
    fl = font("Bold", round(15 * scale))
    for k, tk in enumerate(a["tickets"]):
        if multi:
            box = S(tk["ticket"], 10 * scale)
            d.rounded_rectangle(box, round(8 * scale), outline=(15, 23, 42), width=lw)
            lab = f"Tiket {k + 1}"
            tw = d.textlength(lab, font=fl)
            d.rounded_rectangle([box[0], box[1] - 30 * scale, box[0] + tw + 18 * scale, box[1] - 4 * scale], round(6 * scale), fill=(15, 23, 42))
            d.text((box[0] + 9 * scale, box[1] - 17 * scale), lab, font=fl, fill="white", anchor="lm")
        for j, bs in tk["fields"].items():
            for b in bs:
                d.rounded_rectangle(S(b, 4 * scale), round(5 * scale), outline=FIELDS[j][1], width=lw)
    for k, cells in enumerate(a["table"]):
        for j, (b, t) in enumerate(cells[:6]):
            d.rounded_rectangle(S(b, 5 * scale), round(4 * scale), outline=FIELDS[j][1], width=max(2, lw - 1))
        if multi:
            b = cells[0][0]
            c = ((b[0] - 26) * scale, (b[1] + b[3]) / 2 * scale)
            r = 11 * scale
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(15, 23, 42))
            d.text(c, str(k + 1), font=font("Bold", round(13 * scale)), fill="white", anchor="mm")
    return im


def legend(w: int, h: int, note: str) -> Image.Image:
    im = Image.new("RGB", (w, h), (241, 245, 249)); d = ImageDraw.Draw(im)
    f = font("SemiBold", 40); x = 0
    for name, col in FIELDS:
        d.rounded_rectangle([x, h / 2 - 20, x + 40, h / 2 + 20], 8, outline=col, width=6)
        d.text((x + 58, h / 2), name, font=f, fill=(15, 23, 42), anchor="lm"); x += 58 + d.textlength(name, font=f) + 64
    d.text((w, h / 2), note, font=font("Medium", 34), fill=(100, 116, 139), anchor="rm")
    return im


def main(src: str, out: str) -> None:
    src, out = Path(src), Path(out); out.mkdir(parents=True, exist_ok=True)
    data = json.loads((HERE / "mockup" / "data" / "ocr_tickets.json").read_text())
    by = {}
    for t in data["tickets"]:
        by.setdefault(t["img"], []).append(t)
    ocr = RapidOCR()
    W, H, M = 3840, 2160, 90
    # 1 ticket
    a = analyse(src / "single0.jpeg", by["single0"], ocr)
    im0 = Image.open(src / "single0.jpeg")
    s = (H - 2 * M - 150) / im0.height
    pic = draw(src / "single0.jpeg", a, s, multi=False)
    cv = Image.new("RGB", (W, H), (241, 245, 249))
    cv.paste(legend(W - 2 * M, 110, "Hasil apa adanya dari repo · kotak = posisi field di tiket dan di tabel"), (M, M - 10))
    cv.paste(pic, ((W - pic.width) // 2, M + 140))
    cv.save(out / "UC8_document_ocr_1.png")
    json.dump(a, open(HERE / "mockup" / "data" / "ocr_boxes_single0.json", "w"))
    # 2 and 3 tickets, side by side
    pics = []
    for n in ("multiple0", "multiple1"):
        a = analyse(src / f"{n}.jpeg", by[n], ocr)
        im = Image.open(src / f"{n}.jpeg")
        pics.append(draw(src / f"{n}.jpeg", a, (H - 2 * M - 150) / im.height, multi=True))
        json.dump(a, open(HERE / "mockup" / "data" / f"ocr_boxes_{n}.json", "w"))
    cv = Image.new("RGB", (W, H), (241, 245, 249))
    cv.paste(legend(W - 2 * M, 110, "Hasil apa adanya dari repo · 2 tiket dan 3 tiket dalam satu foto"), (M, M - 10))
    gap = (W - sum(p.width for p in pics)) // 3
    x = gap
    for p in pics:
        cv.paste(p, (x, M + 140)); x += p.width + gap
    cv.save(out / "UC8_document_ocr_2.png")
    print("ok", [p.size for p in pics])


if __name__ == "__main__":
    main(*sys.argv[1:3])
