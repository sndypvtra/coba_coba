"""The printable marker sheets for UkurAja's photo mode: one ArUco marker (OpenCV DICT_4X4_50) per sheet, vector, exact
millimetres, with a ruler to check the print scale and the how-to in Indonesian.

    python tools/marker/make_marker_pdf.py marker/      # -> UkurAja_marker_A4.pdf, UkurAja_marker_A3.pdf

A4: id 1, black square 160 mm. A3: id 2, black square 240 mm (MarkerSheet.kt). The codes are the app's own table
(Aruco.kt), taken from OpenCV; tools/marker/check_opencv.py and the app read them alike.
"""
import sys
from pathlib import Path

from reportlab.lib.colors import Color, black, white
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parents[2]
FONTS = HERE / "app" / "src" / "main" / "res" / "font"
for name, f in (("Inter", "inter_regular.ttf"), ("Inter-SemiBold", "inter_semibold.ttf"), ("Inter-Bold", "inter_bold.ttf")):
    pdfmetrics.registerFont(TTFont(name, str(FONTS / f)))

DICT_4X4_50 = [0xB532, 0x0F9A, 0x332D, 0x9946, 0x549E, 0x79CD, 0x9E2E, 0xC4F2, 0xFEDA, 0xCF56, 0xF991, 0x11A7, 0x0EB7,
               0x2A0F, 0x24B1, 0x263E, 0x4665, 0x6600, 0x6C5E, 0x76AF, 0x868B, 0xB02B, 0xCCD5, 0xDD82, 0xFE47, 0x9471,
               0xACE4, 0xA554, 0x2123, 0x346F, 0x4415, 0x57B2, 0x9ECF, 0xF0CB, 0x08AE, 0x0929, 0x1875, 0x04FF, 0x0DF6,
               0x1C5A, 0x1718, 0x2A28, 0x328C, 0x38B2, 0x24E8, 0x2EEB, 0x2D3F, 0x4B64, 0x502E, 0x5013]

# the app reads exactly these codes: the table in Aruco.kt must be the same
_KT = (HERE / "core/src/main/java/id/ukurpaket/app/marker/Aruco.kt").read_text()
_APP = [int(v, 16) for v in _KT.split("DICT_4X4_50 = intArrayOf(")[1].split(")")[0].replace("\n", " ").split(",") if v.strip()]
assert _APP == DICT_4X4_50, "marker codes differ from the app's (Aruco.kt)"

INK = Color(0.06, 0.09, 0.16)
GREY = Color(0.40, 0.45, 0.53)
LINE = Color(0.80, 0.83, 0.87)
BRAND = Color(0xED / 255, 0x06 / 255, 0x77 / 255)

SHEETS = {
    #       page (mm)    id  side  top   scale of the text
    "A4": ((210, 297), 1, 160, 27, 1.0),
    "A3": ((297, 420), 2, 240, 38, 1.35),
}


def marker(c: canvas.Canvas, x: float, y_top: float, side: float, mid: int) -> None:
    """The marker with its top-left corner at (x, y_top) (mm from the page's top-left), [side] mm across."""
    ph = c._pagesize[1] / mm
    cell = side / 6
    code = DICT_4X4_50[mid]
    c.setFillColor(black)
    c.rect(x * mm, (ph - y_top - side) * mm, side * mm, side * mm, stroke=0, fill=1)
    # all white cells in one path: one fill, so neighbouring cells show no seam on screen
    p = c.beginPath()
    for i in range(4):
        for j in range(4):
            if (code >> (15 - (i * 4 + j))) & 1:
                cx = x + (j + 1) * cell
                cy = ph - y_top - (i + 2) * cell
                p.rect(cx * mm, cy * mm, cell * mm, cell * mm)
    c.setFillColor(white)
    c.drawPath(p, stroke=0, fill=1)


def ruler(c: canvas.Canvas, x: float, y: float, length_mm: int, s: float) -> None:
    """A ruler [length_mm] long starting at (x, y) (mm from the top-left): mm ticks, numbers every cm."""
    ph = c._pagesize[1] / mm
    base = (ph - y) * mm
    c.setStrokeColor(INK); c.setLineWidth(0.25 * mm)
    c.line(x * mm, base, (x + length_mm) * mm, base)
    c.setFont("Inter", 6.5 * s); c.setFillColor(INK)
    for t in range(length_mm + 1):
        h = 4.5 if t % 10 == 0 else (3.0 if t % 5 == 0 else 1.8)
        c.setLineWidth((0.25 if t % 10 == 0 else 0.15) * mm)
        c.line((x + t) * mm, base, (x + t) * mm, base + h * mm)
        if t % 10 == 0:
            c.drawCentredString((x + t) * mm, base + 6.2 * mm, f"{t // 10}")
    c.setFont("Inter", 6.5 * s)
    c.drawString((x + length_mm + 2) * mm, base + 0.5 * mm, "cm")


def text_block(c, x, y, lines, size, lead, font="Inter", color=INK, width=None):
    """Lines of text from (x, y) mm (top-left), wrapped to [width] mm; returns the y below it."""
    ph = c._pagesize[1] / mm
    c.setFont(font, size); c.setFillColor(color)
    for line in lines:
        words = line.split(" ")
        cur = ""
        for w in words:
            t = (cur + " " + w).strip()
            if width and pdfmetrics.stringWidth(t, font, size) > width * mm and cur:
                c.drawString(x * mm, (ph - y) * mm, cur); y += lead; cur = w
            else:
                cur = t
        c.drawString(x * mm, (ph - y) * mm, cur); y += lead
    return y


def sketch(c, x, y, w, s):
    """Top view (60 x 58 units across [w] mm): the parcel, the sheet beside it on the camera's side, the courier at a corner."""
    ph = c._pagesize[1] / mm
    u = w / 60

    def P(px, py):
        return (x + px * u) * mm, (ph - y - py * u) * mm

    def R(x0, y0, ww, hh, fill=None, stroke=INK, lw=0.3):
        c.setLineWidth(lw * mm); c.setStrokeColor(stroke)
        if fill is not None: c.setFillColor(fill)
        c.rect(P(x0, y0 + hh)[0], P(x0, y0 + hh)[1], ww * u * mm, hh * u * mm, stroke=1, fill=1 if fill is not None else 0)
    R(24, 2, 34, 20, fill=Color(0.99, 0.91, 0.95), stroke=BRAND, lw=0.35)
    c.setFillColor(BRAND); c.setFont("Inter-SemiBold", 6.8 * s)
    c.drawCentredString(*P(41, 13.5), "PAKET")
    R(33, 27, 13, 17, fill=white, stroke=GREY, lw=0.25)
    R(35, 30, 9, 9, fill=INK, stroke=INK, lw=0.1)
    R(37.5, 32.5, 4, 4, fill=white, stroke=white, lw=0.1)
    c.setFillColor(GREY); c.setFont("Inter", 6.2 * s)
    c.drawCentredString(*P(39.5, 48.5), "marker")
    c.setFillColor(INK); c.circle(*P(6, 52), 2.2 * u * mm, stroke=0, fill=1)
    c.setStrokeColor(INK); c.setLineWidth(0.35 * mm)
    c.line(*P(8.5, 49), *P(22, 24.5))
    # arrowhead at the parcel's corner
    import math
    ax, ay = P(22, 24.5); bx, by = P(8.5, 49)
    ang = math.atan2(ay - by, ax - bx); L = 2.2 * u * mm
    p = c.beginPath(); p.moveTo(ax, ay)
    p.lineTo(ax - L * math.cos(ang - 0.45), ay - L * math.sin(ang - 0.45)); p.lineTo(ax - L * math.cos(ang + 0.45), ay - L * math.sin(ang + 0.45)); p.close()
    c.setFillColor(INK); c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(GREY); c.setFont("Inter", 6.2 * s)
    c.drawString(*P(11, 56.5), "foto dari pojok paket")


def make(name: str, out: Path) -> Path:
    (pw, ph), mid, side, top, s = SHEETS[name]
    f = out / f"UkurAja_marker_{name}.pdf"
    c = canvas.Canvas(str(f), pagesize=(pw * mm, ph * mm), invariant=1)   # reproducible bytes
    c.setTitle(f"Marker UkurAja {name}")
    c.setAuthor("UkurAja")
    c.setSubject(f"ArUco DICT_4X4_50 id {mid}, black square {side} mm")
    m = (pw - side) / 2
    # header (kept well clear of the marker: the white round it must stay plain)
    c.setFillColor(INK); c.setFont("Inter-Bold", 11 * s)
    c.drawString(m * mm, (ph - 14 * s) * mm, f"Marker UkurAja · {name}")
    c.setFont("Inter", 8 * s); c.setFillColor(GREY)
    c.drawRightString((pw - m) * mm, (ph - 14 * s) * mm, f"ID {mid} · kotak hitam {side} mm")
    marker(c, m, top, side, mid)
    y = top + side + 12 * s
    # print check
    c.setFillColor(INK); c.setFont("Inter-SemiBold", 10 * s)
    c.drawString(m * mm, (ph - y) * mm, f"Cek hasil cetak: sisi kotak hitam harus {side // 10} cm ({side} mm)")
    y += 6 * s
    y = text_block(c, m, y, [
        "Ukur dengan penggaris setelah dicetak. Kalau beda, isi angka hasil ukur di UkurAja → Pengaturan → Marker. "
        "Penggaris di bawah ini juga harus pas 10 cm.",
    ], 8 * s, 4.4 * s, color=GREY, width=pw - 2 * m)
    ruler(c, m, y + 9 * s, 100, s)
    y += 16 * s
    # how to use, left; sketch, right
    col = (pw - 2 * m) * 0.73
    c.setFillColor(INK); c.setFont("Inter-SemiBold", 10 * s)
    c.drawString(m * mm, (ph - y) * mm, "Cara pakai")
    y0 = y + 6 * s
    steps = [
        "1. Cetak skala 100% (Actual size), jangan Fit to page. Pakai kertas doff.",
        "2. Jaga tetap rata: jangan dilipat; tempel di karton tebal atau laminasi doff.",
        "3. Taruh rata di lantai/meja yang sama dengan paket, di sisi yang menghadap kamera, ±5\u00a0cm dari paket.",
        "4. Foto dari pojok paket: paket dan seluruh kotak hitam masuk foto, tidak tertutup, tidak silau.",
        "5. Jangan taruh marker di atas paket.",
    ]
    yy = y0
    for st in steps:
        yy = text_block(c, m, yy, [st], 8.3 * s, 4.5 * s, width=col - 4) + 1.4 * s
    sketch(c, m + col + 2, y0 - 5 * s, (pw - 2 * m) - col - 2, s)
    # footer
    c.setFont("Inter", 6.5 * s); c.setFillColor(GREY)
    c.drawString(m * mm, 9 * s * mm, f"UkurAja · ArUco DICT_4X4_50 · ID {mid} · {side} mm · cetak di kertas {name} portrait")
    c.showPage(); c.save()
    return f


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "marker"); out.mkdir(parents=True, exist_ok=True)
    assets = HERE / "ukuraja" / "src" / "main" / "assets" / "marker"
    for n in SHEETS:
        f = make(n, out)
        print(f)
        # the app carries the same sheets (Panduan marker: print or share them from the phone)
        if assets.is_dir():
            (assets / f.name).write_bytes(f.read_bytes())
