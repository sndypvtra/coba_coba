"""The printable marker sheet (A4, 300 dpi) for marker mode, same geometry as the app (MarkerSheet / MarkerPdf):
black square ring, outer 160 mm, inner 100 mm, centre 110 mm from the top; a 100 mm check bar.

    python tools/marker_sheet.py      # -> docs/kertas_penanda_A4.pdf and .png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DPI = 300
MM = DPI / 25.4
OUT = Path(__file__).resolve().parents[1] / "docs"
FONT = Path(__file__).resolve().parents[1] / "app" / "src" / "main" / "res" / "font"


def mm(v):
    return round(v * MM)


def main():
    im = Image.new("L", (mm(210), mm(297)), 255)
    d = ImageDraw.Draw(im)
    bold = ImageFont.truetype(str(FONT / "inter_bold.ttf"), mm(5))
    small = ImageFont.truetype(str(FONT / "inter_regular.ttf"), mm(3.4))
    d.text((mm(15), mm(11)), "UkurPaket · kertas penanda ukur", font=bold, fill=0)
    d.text((mm(15), mm(19)), "Cetak di A4 dengan skala 100% (ukuran asli), jangan \"sesuaikan dengan halaman\".", font=small, fill=60)
    cx, cy, o, i = 105, 110, 80, 50
    d.rectangle([mm(cx - o), mm(cy - o), mm(cx + o) - 1, mm(cy + o) - 1], fill=0)
    d.rectangle([mm(cx - i), mm(cy - i), mm(cx + i) - 1, mm(cy + i) - 1], fill=255)
    by, bx = 214, 55
    d.rectangle([mm(bx), mm(by), mm(bx + 100), mm(by + 2)], fill=0)
    for k in range(11):
        t = 5 if k % 5 == 0 else 3
        d.rectangle([mm(bx + k * 10 - 0.3), mm(by - t), mm(bx + k * 10 + 0.3), mm(by)], fill=0)
    d.text((mm(bx - 1.2), mm(by + 3.5)), "0", font=small, fill=60)
    d.text((mm(bx + 96), mm(by + 3.5)), "10 cm", font=small, fill=60)
    d.text((mm(15), mm(by + 12)), "Cek dengan penggaris: garis ini harus tepat 10 cm. Kalau tidak, cetak ulang.", font=small, fill=60)
    tips = ["1. Taruh kertas rata di lantai, di samping paket (boleh menempel, jangan tertutup paket).",
            "2. Foto dari sekitar 1 langkah, HP miring ke bawah ±45°.",
            "3. Kotak hitam dan seluruh paket harus terlihat di foto.",
            "4. Ketuk paket di foto, atau gambar kotak di sekelilingnya."]
    for k, t in enumerate(tips):
        d.text((mm(15), mm(248 + k * 6)), t, font=small, fill=60)
    OUT.mkdir(exist_ok=True)
    im.save(OUT / "kertas_penanda_A4.pdf", resolution=DPI)
    im.resize((im.width // 4, im.height // 4)).save(OUT / "kertas_penanda_A4.png")
    print(OUT / "kertas_penanda_A4.pdf")


if __name__ == "__main__":
    main()
