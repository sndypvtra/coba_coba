"""UkurPaket mockup v2: the courier's flow step by step, in AnterAja colours (magenta #ED0677, yellow #FFCB08),
in the same layout as the first mockup (one 4K board per story, numbered phones, captions, notes).

The screens are the app's own renders (ukur_paket_app, ScreenshotTest), so mockup and APK match 1:1.
Captions use plain business words: no product or library names.

    cd ../../ukur_paket_app && ./gradlew :app:testDebugUnitTest --tests '*ScreenshotTest*'
    python build_v2.py     # -> alur_kurir.png, fitur_lapangan.png (3840 x 2160), screens/*.png (each phone, full size)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "ukur_paket_app" / "app" / "screenshots"
FONTS = HERE.parents[1] / "ukur_paket_app" / "app" / "src" / "main" / "res" / "font"
MAGENTA, MAGENTA_D, YELLOW = (237, 6, 119), (176, 0, 90), (255, 203, 8)
INK, T2, T3, BG, LINE = (15, 23, 42), (71, 85, 105), (148, 163, 184), (246, 247, 250), (226, 232, 240)
BEZEL = (17, 20, 28)

# (screen, title, caption)
MAIN = [
    ("02_scan_resi", "Scan Resi", "Scan barcode di label, atau ketik resi; ukuran langsung terikat ke resi"),
    ("03_persiapan", "Persiapan", "4 aturan foto bergambar, muncul di 3 kali pertama"),
    ("04_scan_lantai", "Scan Lantai", "Gerakkan HP pelan sampai titik putih muncul di lantai"),
    ("05_pilih_paket", "Pilih Paket", "Ketuk paket yang diukur; paket lain di sekitarnya diabaikan"),
    ("06_scan_paket", "Scan Paket", "Gerakkan HP pelan mengitari sudut paket sampai 100%"),
    ("07_hasil_ukur", "Hasil Ukur", "Kotak 3D menempel di paket, lengkap dengan P × L × T"),
    ("08_berat", "Berat", "Isi berat timbangan; Berat Tagih = yang lebih besar"),
    ("09_tersimpan", "Tersimpan", "Bukti tersimpan; Paket berikutnya langsung scan resi lagi"),
]
FIELD = [
    ("05b_pilih_area", "Pilih Area", "Kalau ketukan kurang pas, tandai area paket dengan jari"),
    ("14_paket_berikutnya", "Paket berikutnya", "Tanpa scan lantai ulang; paket yang sudah diukur diberi tanda ✓"),
    ("06b_peringatan", "Arahan langsung", "Paket terpotong, HP terlalu cepat, atau gelap: app memberi tahu"),
    ("07b_perlu_dicek", "Perlu Dicek", "Skor rendah: tombol Simpan dikunci 2 detik, kurir cek ulang"),
    ("07c_ukur_di_hub", "Ukur di Hub", "Setelah 2× gagal, paket tetap diambil dan diukur di hub"),
    ("15_detail_ukur_di_hub", "Data Ukur di Hub", "Foto, waktu, lokasi, dan alasan tersimpan untuk hub"),
    ("01_cek_hp", "Cek HP", "Saat pertama dibuka, app memastikan HP kurir siap mengukur"),
    ("16_hari_ini", "Hari ini", "Semua paket yang diukur hari ini, lengkap dengan statusnya"),
]
# exported to screens/ too, not on a board
EXTRA = [("10_riwayat", "Riwayat", "")]
BOARDS = [
    ("alur_kurir.png", MAIN, "UKURPAKET · ALUR KURIR", "Mengukur P × L × T paket dengan kamera HP",
     "8 langkah dari scan resi sampai data tersimpan. Ukuran, foto, waktu, dan lokasi langsung terikat ke nomor resi.",
     [("Kalau hasil meragukan", "Status Perlu Dicek, tombol Simpan dikunci 2 detik, kurir diminta cek kotak 3D atau ulangi dari sudut lain."),
      ("Kalau paket menempel paket lain", "Kurir cukup ketuk paketnya, atau tandai area paket. Paket di sebelahnya tidak ikut terukur."),
      ("Banyak paket sekaligus", "Tekan Paket berikutnya: scan resi, lalu ukur. Lantai sudah dikenali, paket yang selesai diberi tanda ✓.")]),
    ("fitur_lapangan.png", FIELD, "UKURPAKET · DI LAPANGAN", "Dibuat untuk kondisi nyata kurir",
     "Paket menempel, tempat gelap, hasil meragukan, sampai paket yang sulit diukur: semuanya ada jalan keluarnya.",
     [("Bukti untuk setiap resi", "Setiap hasil ukur menyimpan foto dengan kotak 3D, waktu, dan lokasi, terikat ke resi hasil scan barcode."),
      ("Tidak ada paket tertinggal", "Paket yang sulit diukur tetap diambil dan ditandai Ukur di Hub, lengkap dengan foto, lokasi, dan alasan."),
      ("Data tetap di HP", "Semua proses berjalan di HP, tanpa internet. Data siap dikirim ke sistem saat sudah terhubung.")]),
]
FOOT_L = "Tampilan asli dari aplikasi uji coba (APK v0.1). Foto paket asli, label resi disamarkan. Ukuran di layar adalah contoh untuk uji alur."
FOOT_R = "Mockup konsep · UkurPaket"


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"inter_{weight}.ttf"), size)


def status_bar(w, top_rgb):
    """A phone status bar (time, signal, wifi, battery) in the screen's own top colour."""
    h = round(w * 0.058)
    bar = Image.new("RGB", (w, h), top_rgb)
    d = ImageDraw.Draw(bar)
    dark = sum(top_rgb) < 384
    fg = (255, 255, 255) if dark else INK
    s = h / 72
    d.text((round(w * 0.11), round(16 * s)), "09:41", font=font("semibold", round(34 * s)), fill=fg)
    x = w - round(w * 0.11) - round(150 * s); base = round(52 * s)
    for i in range(4):                                       # signal
        bh = round((10 + 7 * i) * s)
        d.rounded_rectangle([x + i * round(9 * s), base - bh, x + i * round(9 * s) + round(6 * s), base], round(1.5 * s), fill=fg)
    cx, cy = w - round(w * 0.11) - round(88 * s), base       # wifi
    for k, r in enumerate((22, 15, 8)):
        rr = round(r * s)
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], 225, 315, fill=fg, width=max(2, round(4 * s)))
    bx = w - round(w * 0.11) - round(62 * s)                 # battery
    d.rounded_rectangle([bx, round(24 * s), bx + round(40 * s), round(48 * s)], round(5 * s), outline=fg, width=max(2, round(3 * s)))
    d.rounded_rectangle([bx + round(4 * s), round(28 * s), bx + round(34 * s), round(44 * s)], round(3 * s), fill=fg)
    d.rectangle([bx + round(41 * s), round(31 * s), bx + round(44 * s), round(41 * s)], fill=fg)
    return bar


def phone(name, w):
    """The app screen at width [w] inside a dark phone body with a status bar; RGBA, transparent around."""
    src = Image.open(SRC / f"{name}.png").convert("RGB")
    scr = src.resize((w, round(src.height * w / src.width)), Image.LANCZOS)
    top = scr.getpixel((w // 2, 2))
    bar = status_bar(w, top if sum(top) > 120 else (12, 12, 14))
    screen = Image.new("RGB", (w, bar.height + scr.height))
    screen.paste(bar, (0, 0)); screen.paste(scr, (0, bar.height))
    b = round(w * 0.045); r = round(w * 0.12)
    out = Image.new("RGBA", (w + 2 * b, screen.height + 2 * b), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle([0, 0, out.width - 1, out.height - 1], r + b, fill=BEZEL + (255,))
    mask = Image.new("L", screen.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, screen.width - 1, screen.height - 1], r, fill=255)
    out.paste(screen, (b, b), mask)
    return out


def shadowed(img, blur, dy, alpha):
    pad = blur * 3
    canvas = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: alpha if v > 0 else 0)
    sh.paste((15, 23, 42, 255), (pad, pad + dy), a)
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    canvas.alpha_composite(img, (pad, pad))
    return canvas, pad


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) <= width: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines


def board(out, items, eyebrow, title, subtitle, cards):
    W, H, M = 3840, 2160, 104
    b = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(b)
    d.text((M, 84), eyebrow, font=font("bold", 30), fill=MAGENTA)
    d.text((M, 132), title, font=font("bold", 82), fill=INK)
    d.text((M, 248), subtitle, font=font("regular", 36), fill=T2)
    n = len(items); gap = 40
    pw = (W - 2 * M - (n - 1) * gap)
    sw = round(pw / n / 1.09)                               # screen width inside the bezel
    y0 = 500
    for i, (name, t, cap) in enumerate(items):
        ph = phone(name, sw)
        x = M + i * (W - 2 * M + gap) // n
        cx = x + ph.width // 2
        d.ellipse([cx - 34, y0 - 112, cx + 34, y0 - 44], fill=MAGENTA)
        num = str(i + 1)
        d.text((cx - d.textlength(num, font=font("bold", 36)) / 2, y0 - 100), num, font=font("bold", 36), fill="white")
        sp, pad = shadowed(ph, 18, 10, 90)
        b.alpha_composite(sp, (x - pad, y0 - pad))
        ty = y0 + ph.height + 34
        d.text((cx - d.textlength(t, font=font("bold", 38)) / 2, ty), t, font=font("bold", 38), fill=INK)
        for k, line in enumerate(wrap(d, cap, font("regular", 27), ph.width + 20)):
            d.text((cx - d.textlength(line, font=font("regular", 27)) / 2, ty + 58 + k * 38), line, font=font("regular", 27), fill=T2)
    cy = 1720
    cw = (W - 2 * M - 2 * 36) // 3
    for i, (ct, cb) in enumerate(cards):
        x = M + i * (cw + 36)
        d.rounded_rectangle([x, cy, x + cw, cy + 190], 22, fill="white", outline=LINE, width=2)
        d.rounded_rectangle([x, cy, x + 12, cy + 190], 6, fill=YELLOW)
        d.text((x + 44, cy + 30), ct, font=font("bold", 36), fill=INK)
        for k, line in enumerate(wrap(d, cb, font("regular", 28), cw - 80)[:3]):
            d.text((x + 44, cy + 84 + k * 38), line, font=font("regular", 28), fill=T2)
    d.text((M, H - 74), FOOT_L, font=font("regular", 26), fill=T3)
    d.text((W - M - d.textlength(FOOT_R, font=font("regular", 26)), H - 74), FOOT_R, font=font("regular", 26), fill=T3)
    b.convert("RGB").save(HERE / out, optimize=True)
    print(out, b.size)


def main():
    scr = HERE / "screens"
    scr.mkdir(exist_ok=True)
    for f in scr.glob("*"):
        f.unlink()
    for i, (name, _, _) in enumerate(MAIN + FIELD + EXTRA, 1):
        ph = phone(name, 1236)
        ph.save(scr / f"{i:02d}_{name.split('_', 1)[1]}.png", optimize=True)
    for out, items, eyebrow, title, subtitle, cards in BOARDS:
        board(out, items, eyebrow, title, subtitle, cards)


if __name__ == "__main__":
    main()
