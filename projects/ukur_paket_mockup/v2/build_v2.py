"""UkurPaket mockup v2: the courier's flow step by step, in AnterAja colours (magenta #ED0677, yellow #FFCB08).

The screens are the app's own renders (ukur_paket_app, ScreenshotTest), so the mockup and the APK match 1:1.

    cd ../../ukur_paket_app && ./gradlew :app:testDebugUnitTest --tests '*ScreenshotTest*'
    python build_v2.py        # -> screens/*.jpg, alur_kurir.jpg, kondisi_khusus.jpg
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "ukur_paket_app" / "app" / "screenshots"
FONTS = HERE.parents[1] / "ukur_paket_app" / "app" / "src" / "main" / "res" / "font"
MAGENTA, YELLOW, INK, T2, BG = (237, 6, 119), (255, 203, 8), (15, 23, 42), (71, 85, 105), (246, 247, 250)

# (screen file, step title, what the courier does)
FLOW = [
    ("01_cek_hp", "Cek Perangkat", "App mengecek ARCore & Depth di HP"),
    ("02_pickup", "Pickup", "Pilih resi di daftar, atau Scan resi"),
    ("03_persiapan", "Persiapan", "4 aturan foto, muncul di 3 kali pertama"),
    ("04_scan_lantai", "Scan Lantai", "Gerakkan HP sampai titik putih muncul"),
    ("05_pilih_paket", "Pilih Paket", "Ketuk paket. Paket lain diabaikan"),
    ("05b_pilih_area", "Pilih Area", "Ketukan kurang pas? Tandai area paket"),
    ("06_scan_paket", "Scan Paket", "Gerakkan HP mengitari sudut paket"),
    ("07_hasil_ukur", "Hasil Ukur", "Cek kotak 3D & ukuran, lalu Simpan"),
    ("08_berat", "Berat", "Isi Berat Aktual, Berat Tagih otomatis"),
    ("09_tersimpan", "Tersimpan", "Foto, ukuran, waktu & GPS tersimpan"),
    ("14_paket_berikutnya", "Paket Berikutnya", "Tanpa Scan Lantai ulang, ✓ = selesai"),
    ("10_riwayat", "Riwayat", "Semua hasil di HP, bisa dibagikan"),
]
SPECIAL = [
    ("06b_peringatan", "Peringatan", "Paket terpotong layar: mundur sedikit"),
    ("07b_perlu_dicek", "Perlu Dicek", "Skor rendah: Simpan terkunci 2 detik"),
    ("07c_ukur_di_hub", "Ukur di Hub", "Setelah 2× gagal, pilih alasan"),
    ("15_detail_ukur_di_hub", "Data Ukur di Hub", "Foto, waktu, lokasi & alasan tersimpan"),
    ("12_cek_hp_tanpa_arcore", "HP Tidak Didukung", "HP tanpa ARCore terdeteksi di awal"),
    ("13_hp_tanpa_arcore_ukur", "Tanpa ARCore", "Paket tetap diambil, Ukur di Hub"),
]


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"inter_{weight}.ttf"), size)


def phone(img, w):
    """Screen with rounded corners, a thin frame and a soft shadow."""
    h = round(img.height * w / img.width)
    s = img.convert("RGB").resize((w, h), Image.LANCZOS)
    r = round(w * 0.075)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    pad = 28
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 10, pad + w, pad + h + 10], r, fill=(15, 23, 42, 70))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    frame = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rounded_rectangle([0, 0, w + 7, h + 7], r + 4, fill=(30, 30, 36, 255))
    out.alpha_composite(frame, (pad - 4, pad - 4))
    out.paste(s, (pad, pad), mask)
    return out


def board(items, title, subtitle, cols, out, first=1, letters=False):
    W = 3840
    sw = 520
    gap = (W - 2 * 120 - cols * sw) // (cols - 1)
    sample = Image.open(SRC / f"{items[0][0]}.png")
    sh = round(sample.height * sw / sample.width)
    rows = (len(items) + cols - 1) // cols
    H = 300 + rows * (sh + 260) + 60
    b = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(b)
    d.rectangle([0, 0, W, 210], fill=MAGENTA)
    d.rectangle([0, 210, W, 222], fill=YELLOW)
    d.text((120, 52), title, font=font("bold", 76), fill="white")
    d.text((120, 146), subtitle, font=font("medium", 38), fill=(255, 225, 240))
    for i, (name, step, what) in enumerate(items):
        r, c = divmod(i, cols)
        x = 120 + c * (sw + gap)
        y = 300 + r * (sh + 260)
        label = chr(ord("A") + i) if letters else str(first + i)
        d.ellipse([x, y, x + 74, y + 74], fill=YELLOW)
        tw = d.textlength(label, font=font("bold", 40))
        d.text((x + 37 - tw / 2, y + 12), label, font=font("bold", 40), fill=INK)
        d.text((x + 92, y + 2), step, font=font("bold", 40), fill=INK)
        d.text((x + 92, y + 52), what, font=font("regular", 25), fill=T2)
        p = phone(Image.open(SRC / f"{name}.png"), sw)
        b.paste(p, (x - 28, y + 100), p)
        if not letters and c < cols - 1 and i < len(items) - 1:
            ax = x + sw + gap // 2; ay = y + 100 + sh // 2
            d.polygon([(ax - 14, ay - 22), (ax + 16, ay), (ax - 14, ay + 22)], fill=MAGENTA)
    b.save(out, quality=90, optimize=True)
    print(out.name, b.size)


def main():
    scr = HERE / "screens"
    scr.mkdir(exist_ok=True)
    for i, (name, _, _) in enumerate(FLOW, 1):
        Image.open(SRC / f"{name}.png").convert("RGB").save(scr / f"{i:02d}_{name.split('_', 1)[1]}.jpg", quality=90, optimize=True)
    for i, (name, _, _) in enumerate(SPECIAL):
        Image.open(SRC / f"{name}.png").convert("RGB").save(scr / f"{chr(ord('A') + i)}_{name.split('_', 1)[1]}.jpg", quality=90, optimize=True)
    board(FLOW, "UkurPaket · Alur Kurir Step by Step",
          "Ukur P × L × T paket dengan kamera HP (ARCore + Depth) · tampilan asli dari APK v0.1", 6, HERE / "alur_kurir.jpg")
    board(SPECIAL, "UkurPaket · Kondisi Khusus",
          "Peringatan, hasil yang perlu dicek, paket yang diukur di hub, dan HP tanpa ARCore", 6, HERE / "kondisi_khusus.jpg",
          letters=True)


if __name__ == "__main__":
    main()
