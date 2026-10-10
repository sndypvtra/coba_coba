"""Pages added when each factory product became its own web app (see build.py for the shell and APPS).

Live Monitoring for fill, pack and parcel; Reject & Giveaway (fill); Spesifikasi Kemasan (pack);
Kelas Ukuran & Tagihan (parcel); and one "Kamera, Alert & Integrasi" page per product.
"""
from __future__ import annotations

import json

import build as B
from look import I, bd, card, kpi, legend, num, sev, status, tg, tile, vbars

app, btn, grid, history, im, ph, poc = B.app, B.btn, B.grid, B.history, B.im, B.ph, B.poc


def idle(label: str, icon: str, text: str, style: str = "aspect-ratio:16/9") -> str:
    return (f'<div class="tile" style="{style};background:#111821;display:grid;place-items:center">'
            f'<span class="tl"><span class="dot" style="color:#94a3b8"></span>{label}</span>'
            f'<div style="text-align:center;color:#8b99ad;font-size:12.5px">{I(icon, size=30, color="#8b99ad")}'
            f'<div style="margin-top:6px">{text}</div></div></div>')


def live_wall(big: str, small: list[str]) -> str:
    return (f'<div style="display:flex;flex-direction:column;gap:10px">{big}'
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">{"".join(small)}</div></div>')


def live_page(product: str, sub: str, wall: str, side: str, user=("Andi Wijaya", "Line Supervisor", "amber")) -> str:
    body = (ph("Live Monitoring", sub,
               '<span class="seg"><span>' + I("crop_square") + '1</span><span>' + I("grid_view") + '4</span><span class="on">'
               + I("view_quilt") + '1+3</span></span>' + btn("Layar penuh", "fullscreen"))
            + f'<div style="display:grid;grid-template-columns:1fr 420px;gap:18px;flex:1;min-height:0">'
              f'<div style="min-height:0">{wall}</div><div class="col" style="gap:14px">{side}</div></div>')
    return app(product, "live", body, user=user)


# ------------------------------------------------------------------ Live Monitoring
def live_fill() -> str:
    big = tile(im("fill"), "LIVE · F1 · Mesin pengisi, nozzle 1 · CAM 06", "#ef4444", "67% · 334 mL", style="aspect-ratio:16/9")
    small = [idle("F1 · nozzle 5–8 · CAM 07", "warning", "Cek kamera: silau di lensa"),
             idle("F2 · Mesin pengisi · CAM 08", "sync", "Line berhenti · ganti SKU"),
             idle("F3 · Mesin pengisi · CAM 09", "schedule", "Line hanya jalan di shift 2")]
    noz = [("N1", 67, "mengisi", "#2563eb"), ("N2", 100.4, "pass", "#079455"), ("N3", 101.8, "pass · giveaway", "#d97706"),
           ("N4", 100.2, "pass", "#079455"), ("N5", 97.4, "reject · underfill", "#dc2626"), ("N6", 100.7, "pass", "#079455"),
           ("N7", 100.5, "pass", "#079455"), ("N8", 100.3, "pass", "#079455")]
    rows = "".join(f'<div class="row" style="gap:10px;padding:6px 0;border-bottom:1px solid var(--hair);font-size:13px">'
                   f'<b style="width:30px">{n}</b><div class="prog grow" style="height:8px"><i style="width:{min(v, 100)}%;background:{c}"></i></div>'
                   f'<span class="tn" style="width:56px;text-align:right">{num(v, 1)}%</span><span class="mut" style="width:118px">{t}</span></div>'
                   for n, v, t, c in noz)
    side = (card("Siklus berjalan · nozzle 1", f'<div class="kv"><span>Level isi</span><b>67% · 334 mL {poc()}</b>'
                 f'<span>Flow rate</span><span>88 mL/detik</span><span>Sisa ke target</span><span>± 1,9 detik</span>'
                 f'<span>Target</span><span>500 mL · toleransi 98–102%</span></div>', icon="water_drop", right=status("Berjalan"))
            + card("Hasil terakhir per nozzle · Line F1", rows, icon="bar_chart", right="% dari target")
            + card("", f'<div class="col" style="gap:8px">{btn("Hentikan nozzle 5 untuk dicek", "pause_circle", "pri")}'
                       f'{btn("Tandai reject manual", "block")}</div>'))
    return live_page("fill", "Overlay AI di setiap kamera: outline botol, garis target, level isi", live_wall(big, small), side)


def live_pack() -> str:
    big = tile(im("tray"), "LIVE · C1 · Ujung line kaleng · CAM 03", "#ef4444", "simulasi 3D", style="aspect-ratio:16/9")
    small = [tile(im("packing", 1), "LIVE · P1 · Robot packing · CAM 04", "#ef4444", style="aspect-ratio:16/9"),
             idle("C2 · Line kaleng 2 · CAM 05", "sync", "Line berhenti · ganti SKU"),
             idle("P2 · Packing station 2 · CAM 06", "schedule", "Hanya jalan di shift 2")]
    trays = "".join(f'<div style="flex:1;text-align:center;padding:8px 4px;border-radius:8px;'
                    f'background:{"#fef2f2" if n < 10 else "#f0fdf4"}"><b style="font-size:12px">#{t}</b>'
                    f'<div class="tn" style="font-size:15px;font-weight:600;margin-top:2px">{n}/10</div></div>'
                    for t, n in [(7, 9), (6, 10), (5, 10), (4, 9), (3, 10)])
    side = (card("Tray terakhir · line C1", f'<div style="display:flex;gap:6px">{trays}</div>'
                 f'<div class="mut" style="font-size:12px;margin-top:8px">{poc()} 7 tray, 3 kurang isi · 7/7 benar vs data kebenaran</div>',
                 icon="history", right="terbaru di kiri")
            + card("Alert terbaru", f'<div class="ev"><img class="thumb" src="../img/snap_tray_413.jpg" style="width:112px;height:63px">'
                   f'<div class="grow"><div class="t1">Tray #7 kurang 1 kaleng</div><div class="t2">slot B5 kosong · C1 · 10:41</div></div></div>'
                   f'<div class="row" style="gap:8px;margin-top:10px">{btn("Konfirmasi & reject", "check", "pri sm")}{btn("Alarm palsu", "block", "sm")}</div>'
                   f'<div class="ev" style="margin-top:6px"><img class="thumb" src="../img/snap_box_461.jpg" style="width:112px;height:63px">'
                   f'<div class="grow"><div class="t1">Kardus #2 keluar kurang 2</div><div class="t2">slot B2, C5 · P1 · 10:38 · di-hold</div></div></div>',
                   icon="notifications", right=bd("2 baru", "red"))
            + card("Kardus di station P1", f'<div class="kv"><span>Isi sekarang</span><b>0/20 · kardus #3 baru masuk</b>'
                   f'<span>Kecepatan robot</span><span>94 pick/menit {poc()}</span><span>Feeder</span><span>{status("Online")} stopper terisi</span></div>',
                   icon="precision_manufacturing"))
    return live_page("pack", "Overlay AI di setiap kamera: jumlah isi, slot kosong, kardus di station", live_wall(big, small), side)


def live_parcel() -> str:
    big = tile(im("parcel"), "LIVE · OB1 · Belt bongkar truk · CAM 05", "#ef4444", "8 terhitung", style="aspect-ratio:16/9")
    small = [idle("OB2 · Belt outbound 2 · CAM 06", "schedule", "Belt hanya jalan di shift 2"),
             idle("Dock 3 · Muat truk · CAM 07", "local_shipping", "Belum ada truk di dock"),
             idle("OB3 · Belt retur · CAM 08", "sync", "Belt berhenti · perawatan")]
    ps = sorted(json.loads((B.P / "03_parcel_dimensioning/output/parcel_dimensioning_summary.json").read_text())["parcels"],
                key=lambda p: -p["frame"])
    rows = "".join(f'<div class="ev"><img class="thumb" src="../img/snap_parcel_{p["tid"]}.jpg" style="width:96px;height:54px">'
                   f'<div class="grow"><div class="t1">Paket #{p["tid"]} · {p["cls"]}</div>'
                   f'<div class="t2">{p["l_mm"] / 10:.0f} × {p["w_mm"] / 10:.0f} × {p["h_mm"] / 10:.0f} cm · {num(p["volume_l"])} L</div></div></div>'
                   for p in ps[:4])
    side = (card("Paket terakhir", rows, icon="list_alt", right=poc())
            + card("Perlu manual check", '<div class="ev"><img class="thumb" src="../img/snap_parcel_20.jpg" style="width:96px;height:54px">'
                   '<div class="grow"><div class="t1">Paket #20 · S atau M?</div><div class="t2">28 × 23 × 10 cm · dekat batas 30 cm</div></div></div>'
                   f'<div class="row" style="gap:8px;margin-top:10px">{btn("Konfirmasi S", "check", "pri sm")}{btn("Ubah ke M", "edit", "sm")}</div>',
                   icon="straighten", right=bd("1 terbuka", "amber")))
    return live_page("parcel", "Overlay AI di setiap kamera: kotak paket, P × L × T, kelas ukuran, count line", live_wall(big, small), side,
                     user=("Dewi Lestari", "QC Manager", "green"))


# ------------------------------------------------------------------ Fill Level · Reject & Giveaway
def fill_events() -> str:
    k = grid("repeat(4,1fr)", [
        kpi("trending_down", "red", "Reject underfill shift ini", "37", "0,08% dari 48.320 botol"),
        kpi("water_drop", "amber", "Giveaway shift ini", "≈ 150 L", "rata-rata +3,1 mL per botol"),
        kpi("rule", "blue", "Nozzle perlu dicek", "2", "N3 overfill · N5 underfill berulang"),
        kpi("verified", "green", "Reject dikonfirmasi QC", "35/37", "2 dibatalkan · busa tinggi")])
    rej = [("10:41:12", "F1", "N5", "486 mL", "97,2%", "Reject"), ("10:36:48", "F1", "N5", "488 mL", "97,6%", "Reject"),
           ("10:12:05", "F2", "N2", "323 mL", "97,9%", "Reject"), ("10:04:31", "F1", "N1–N8", "9 botol", "tangki rendah", "Reject"),
           ("09:47:10", "F1", "N3", "489 mL", "97,8%", "Alarm palsu")]
    rows = "".join(f'<tr><td class="tn">{a}</td><td>{b}</td><td><b>{c}</b></td><td class="tn">{d}</td><td class="tn">{e}</td>'
                   f'<td>{status(f)}</td></tr>' for a, b, c, d, e, f in rej)
    tbl = card("Reject underfill terbaru", f'<table class="tbl cp"><thead><tr><th>Jam</th><th>Line</th><th>Nozzle</th><th>Isi</th>'
               f'<th>% target</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>', icon="report",
               right=btn("Ekspor CSV", "download", "sm"), cb_style="padding:10px 6px 6px")
    gv = card("Giveaway per nozzle · Line F1", B.dev_bars([3.0, 2.0, 9.0, 1.0, -3.0, 3.5, 2.5, 1.5], [f"N{i}" for i in range(1, 9)],
                                                         760, 230, -12, 12, (-10, 10), 4, flag=2)
              + f'<div class="row" style="gap:12px;margin-top:6px">{bd("N3 selalu +9 mL: cek timing valve", "amber", "warning")}'
                f'{bd("N5 sering di bawah target: cek nozzle", "red", "error")}</div>', icon="bar_chart", right="mL vs target")
    ev = card("Bukti reject · 10:41:12 · nozzle 5",
              f'<div style="display:grid;grid-template-columns:480px 1fr;gap:20px"><img class="thumb" src="{im("fill", 2)}" style="width:480px;height:270px;object-fit:cover">'
              '<div><div class="kv"><span>Level saat nozzle berhenti</span><b>97,2% · 486 mL</b>'
              f'<span>Batas bawah</span><span>98% · 490 mL</span><span>Tindakan</span><span>sinyal reject ke PLC dalam 0,4 detik</span>'
              f'<span>Status</span><span>{status("Reject")}</span></div>'
              '<div class="mut" style="font-size:12px;margin-top:12px">Gambar kamera dari PoC (level isi terukur tiap frame); '
              'kejadian reject ini ilustrasi, karena klip PoC berakhir sebelum siklus selesai.</div></div></div>',
              icon="photo_library", right=btn("Putar klip −10 / +10 detik", "play_circle", "sm"))
    trend = card("Reject underfill per jam", vbars([("Line F1", [2, 3, 1, 9, 4, 2, 3, 1], "#2563eb"), ("Line F2", [1, 2, 1, 2, 1, 3, 1, 1], "#93c5fd")],
                                                  ["07", "08", "09", "10", "11", "12", "13", "14"], 520, 230, bw_max=16)
                 + legend([("Line F1", "#2563eb"), ("Line F2", "#93c5fd")]), icon="monitoring", right="lonjakan 10:00: tangki rendah")
    body = (ph("Reject & Giveaway", "Setiap botol di bawah toleransi di-reject; setiap mL di atas target dihitung sebagai produk terbuang",
               btn("Laporan shift (PDF)", "picture_as_pdf") + btn("Buka Dashboard TV", "live_tv", "pri"))
            + k + grid("1fr 1fr", [tbl, gv]) + grid("1fr 560px", [ev, trend]))
    return app("fill", "events", body)


# ------------------------------------------------------------------ Pack Count QC · Spesifikasi Kemasan
def pack_spec() -> str:
    skus = [("Kaleng 330 mL · tray 10", "Line C1 · 2 × 5 slot", "Aktif"), ("Snack Box 20", "Station P1 · 4 × 5 slot", "Aktif"),
            ("Kaleng 500 mL · tray 6", "Line C2 · 2 × 3 slot", "Aktif"), ("Gift Box 12", "Station P2 · 3 × 4 slot", "Draft")]
    rows = "".join(f'<tr class="{"on" if k == 1 else ""}"><td><b>{a}</b><div class="mut" style="font-size:12px">{b}</div></td><td>{status(c)}</td></tr>'
                   for k, (a, b, c) in enumerate(skus))
    left = card("Kemasan", f'<table class="tbl"><thead><tr><th>SKU · layout slot</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>',
                icon="inventory", right=btn("Kemasan baru", "add", "sm"), cb_style="padding:10px 6px 6px")
    slots = "".join(f'<div style="height:42px;border-radius:8px;display:grid;place-items:center;font-size:12.5px;font-weight:600;'
                    f'background:#eff6ff;color:#1d4ed8;border:1px dashed #93c5fd">{r}{c}</div>' for r in "ABCD" for c in range(1, 6))
    rules = [("check_circle", "#079455", "20/20", "Lengkap · lanjut ke seal"),
             ("production_quantity_limits", "#dc2626", "Kurang 1 atau lebih", "Hold di outfeed · alert Line Supervisor · slot kosong disebut"),
             ("conveyor_belt", "#2563eb", "Feeder gap", "Alert ke Maintenance jika 2 kali dalam 5 menit"),
             ("report", "#d97706", "Empty pick", "Dicatat sebagai penyebab; kardus dipantau sampai keluar")]
    rr = "".join(f'<div class="row" style="gap:12px;padding:9px 0;border-bottom:1px solid var(--hair)">{I(ic, True, 20, c)}'
                 f'<b style="width:170px">{a}</b><span class="sec">{b}</span></div>' for ic, c, a, b in rules)
    spec = card("Snack Box 20 · aturan hitung",
                '<div style="display:grid;grid-template-columns:400px 1fr;gap:28px">'
                f'<div><div class="sect">Layout slot (dilihat dari kamera atas)</div>'
                f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:7px">{slots}</div>'
                '<div class="row mut" style="justify-content:space-between;font-size:12px;margin-top:8px"><span>Baris A · belakang</span>'
                '<span>Baris D · depan</span></div></div>'
                f'<div><div class="sect">Jika jumlah isi…</div>{rr}'
                '<div class="kv" style="margin-top:14px"><span>Standar isi</span><span><span class="inp" style="width:90px">20</span></span>'
                '<span>Kapan dinilai</span><span>saat kardus keluar dari station</span>'
                '<span>Kamera</span><span>CAM 04 · tampak atas, di atas station</span></div></div></div>',
                icon="rule", right=f'{btn("Uji di rekaman", "play_circle", "sm")}{btn("Simpan", "check", "sm pri")}')
    test = card("Uji di rekaman sebelum go-live", grid("1fr 1fr 1fr 1fr", [
        kpi("inventory_2", "green", "Kardus benar", "3/3", "vs data kebenaran simulasi"),
        kpi("report", "amber", "Empty pick ditemukan", "2/2", "feeder gap terdeteksi lebih dulu"),
        kpi("fact_check", "green", "Tray benar · line C1", "7/7", "181/181 pembacaan benar"),
        kpi("timer", "blue", "Jeda hitung", "0,16 detik", "dari kejadian ke angka di layar")], 14), icon="science", right=poc())
    chg = card("Riwayat perubahan", history([
        ("8 Okt", "Layout Snack Box 20 dicek ulang", "Dewi Lestari · QC Manager", "#2563eb"),
        ("6 Okt", "Alert feeder gap ke Maintenance", "Rina Hartono · Plant Admin", "#16a34a"),
        ("2 Okt", "Kaleng 500 mL · tray 6 ditambahkan", "Rina Hartono · Plant Admin", "#2563eb")]), icon="history")
    wk = [("Kaleng 330 mL · tray 10", "3.410", "14", "0,41%", "A2 (6×), A3 (4×)"), ("Snack Box 20", "1.280", "6", "0,47%", "B2, C5 · penyebab feeder gap"),
          ("Kaleng 500 mL · tray 6", "2.150", "3", "0,14%", "—")]
    wr = "".join(f'<tr><td><b>{a}</b></td><td class="tn">{b}</td><td class="tn">{c}</td><td class="tn">{d}</td><td class="sec">{e}</td></tr>' for a, b, c, d, e in wk)
    week = card("Hasil per kemasan · minggu ini", f'<table class="tbl cp"><thead><tr><th>Kemasan</th><th>Diinspeksi</th><th>Kurang isi</th>'
                f'<th>Rate</th><th>Slot / penyebab tersering</th></tr></thead><tbody>{wr}</tbody></table>', icon="table_chart",
                cb_style="padding:10px 6px 6px")
    body = (ph("Spesifikasi Kemasan", "Layout slot, standar isi, dan tindakan per SKU; diuji dulu di rekaman sebelum dipakai",
               btn("Impor daftar SKU", "upload")) + grid("440px 1fr", [left, spec]) + grid("1fr 560px", [test, chg]) + week)
    return app("pack", "specs", body)


# ------------------------------------------------------------------ Parcel Dimensioning · Kelas Ukuran & Tagihan
def parcel_spec() -> str:
    cls = [("S", "kecil", "< 30 cm", "#22d3ee", "812"), ("M", "sedang", "30–60 cm", "#3b82f6", "1.904"), ("L", "besar", "> 60 cm", "#7c3aed", "524")]
    cr = "".join(f'<div class="row" style="gap:12px;padding:10px 0;border-bottom:1px solid var(--hair)">'
                 f'<span class="bd" style="background:{c}22;color:{c};width:34px;justify-content:center">{a}</span><b style="width:90px">{b}</b>'
                 f'<span class="sec" style="width:170px">sisi terpanjang {r}</span><span class="mut">{n} paket hari ini</span></div>'
                 for a, b, r, c, n in cls)
    left = card("Kelas ukuran", cr + '<div class="kv" style="margin-top:14px"><span>Manual check jika</span><span>dalam ±1 cm dari batas kelas</span>'
                '<span>Sisi yang dipakai</span><span>sisi terpanjang (P)</span></div>', icon="category", right=btn("Kelas baru", "add", "sm"))
    bill = card("Berat volumetrik & tagihan", '<div class="kv"><span>Rumus</span><b>P × L × T (cm) ÷ 6000 = kg</b>'
                '<span>Pembagi</span><span><span class="inp" style="width:90px">6000</span> <span class="mut">bisa diubah per pelanggan</span></span>'
                '<span>Ditagih per</span><span>yang lebih besar: berat aktual atau berat volumetrik</span>'
                '<span>Kirim ke</span><span>TMS / WMS / sistem invoice, per paket</span></div>', icon="scale")
    cal = card("Kalibrasi kamera · belt OB1",
               f'<div style="display:grid;grid-template-columns:420px 1fr;gap:20px"><img class="thumb" src="{im("parcel", 1)}" style="width:420px;height:236px;object-fit:cover">'
               '<div class="kv"><span>Referensi</span><span>karton bertuliskan 720 × 500 × 340 mm</span>'
               f'<span>Uji karton lain</span><span><b>340,5 mm</b> vs 340 mm sebenarnya {poc()}</span>'
               '<span>Jarak kamera</span><span>± 2,0–2,4 m ke paket</span>'
               f'<span>Cek ulang</span><span>setiap minggu, dengan 1 karton referensi {tg(True)}</span></div></div>',
               icon="straighten", right=status("Pass"))
    test = card("Uji di rekaman sebelum go-live", grid("1fr 1fr 1fr", [
        kpi("package_2", "violet", "Paket terhitung", "8/8", "sama dengan hitungan manual"),
        kpi("straighten", "green", "Karton uji", "340,5 mm", "aslinya 340 mm"),
        kpi("flag", "amber", "Target pilot", "±1 cm", "pada 100 paket vs meteran")], 14), icon="science", right=poc())
    body = (ph("Kelas Ukuran & Tagihan", "Batas kelas S/M/L, rumus berat volumetrik, dan kalibrasi kamera per belt",
               btn("Simpan", "check", "pri")) + grid("1fr 1fr", [left, bill]) + cal + test)
    return app("parcel", "specs", body)


# ------------------------------------------------------------------ Kamera, Alert & Integrasi, per product
SETTINGS = {
    "grading": dict(
        cams=[("CAM 01", "T1–T4 · Packing tomat", "Online", "30 fps", "Pass"), ("CAM 02", "L1–L2 · Chain lemon", "Online", "30 fps", "Pass"),
              ("CAM 03", "T5–T8 · Packing tomat 2", "Jeda", "—", "Line berhenti")],
        rules=[("Off-colour lot di atas limit 10%", "Hold lot · WhatsApp QC Manager", "high"),
               ("Hijau di lot di atas 5%", "Hold lot · alert QC Manager", "high"),
               ("Lemon derajat 10 (out of grade)", "Reject di line · dicatat", "medium"),
               ("Lemon di luar lot utama", "Pack terpisah · dicatat", "low"),
               ("Kartu referensi warna gagal", "Alert Line Supervisor · cek lampu", "medium")],
        ints=[("PLC sortir / reject", "sinyal ke flap atau pusher di line", "Terhubung"),
              ("ERP / sistem lot", "lot, label kelas, sertifikat lot", "Tersedia"),
              ("WhatsApp Business", "alert berfoto ke QC Manager", "Terhubung"), ("Webhook & REST API", "setiap buah dan setiap lot", "Terhubung")],
        wa=("tomato_cam_133.jpg", "Lot T-1012-07 off-colour 17%", "Line T1–T4 · 10:38", "di atas limit 10% · lot di-hold")),
    "fill": dict(
        cams=[("CAM 06", "F1 · nozzle 1–4", "Online", "25 fps", "Pass"), ("CAM 07", "F1 · nozzle 5–8", "Cek", "25 fps", "Silau di lensa"),
              ("CAM 08", "F2 · mesin pengisi", "Jeda", "—", "Line berhenti")],
        rules=[("Botol di bawah 98% target", "Sinyal reject ke PLC · dicatat", "high"),
               ("3 reject di satu nozzle dalam 10 menit", "WhatsApp Line Supervisor", "medium"),
               ("Overfill di atas 102%, 5 kali berturut-turut", "Alert QC · giveaway naik", "medium"),
               ("Kamera silau / buram", "Alert Maintenance · cek manual", "low")],
        ints=[("PLC / rejector", "Modbus TCP · output digital ke rejector", "Terhubung"),
              ("Check weigher", "bandingkan level isi vs berat", "Tersedia"),
              ("MES", "SKU, shift, jumlah reject", "Terhubung"), ("WhatsApp Business", "alert berfoto", "Terhubung")],
        wa=("fill_cam_230.jpg", "3 reject di nozzle 5", "Line F1 · 10:41", "cek nozzle 5 sebelum shift lanjut")),
    "pack": dict(
        cams=[("CAM 03", "C1 · Ujung line kaleng", "Online", "30 fps", "Pass"), ("CAM 04", "P1 · Robot packing", "Online", "25 fps", "Pass"),
              ("CAM 05", "C2 · Line kaleng 2", "Jeda", "—", "Line berhenti")],
        rules=[("Tray / kardus kurang isi", "Hold di outfeed · alert Line Supervisor", "high"),
               ("2 feeder gap dalam 5 menit", "Alert Maintenance", "medium"),
               ("Slot yang sama kosong 3 kali dalam 1 shift", "Alert QC · cek lane filler", "medium"),
               ("Empty pick robot", "Dicatat · penyebab ditautkan", "low")],
        ints=[("PLC / diverter", "alihkan ke lane rework", "Terhubung"), ("MES", "SKU, jumlah pack, short pack", "Terhubung"),
              ("Robot controller", "status pick dan siklus", "Tersedia"), ("WhatsApp Business", "alert berfoto", "Terhubung")],
        wa=("snap_box_461.jpg", "Kardus #2 keluar kurang 2", "Packing station P1 · 10:41", "slot B2, C5 kosong · di-hold di outfeed")),
    "parcel": dict(
        cams=[("CAM 05", "OB1 · Belt bongkar truk", "Online", "30 fps", "Pass"), ("CAM 06", "OB2 · Belt outbound 2", "Jeda", "—", "Shift 2 saja"),
              ("CAM 07", "Dock 3 · Muat truk", "Online", "15 fps", "Pass")],
        rules=[("Ukuran dekat batas kelas", "Masuk antrean manual check", "low"),
               ("Paket tidak terukur (tertutup)", "Ditandai · foto disimpan", "medium"),
               ("Truk hampir penuh (> 90% volume)", "Alert supervisor dock", "medium"),
               ("Belt berhenti > 5 menit", "Alert supervisor shift", "low")],
        ints=[("WMS", "dimensi & volume per paket", "Terhubung"), ("TMS", "rencana muat truk", "Tersedia"),
              ("Sistem invoice", "berat volumetrik per pelanggan", "Tersedia"), ("Webhook & REST API", "setiap paket", "Terhubung")],
        wa=("snap_parcel_20.jpg", "Paket #20 perlu manual check", "Belt OB1 · 10:42", "28 × 23 × 10 cm · S atau M?")),
}


def settings(product: str) -> str:
    d = SETTINGS[product]
    name = B.PRODUCTS[product][1]
    crow = "".join(f'<tr><td><span class="cam">{I("videocam", True)}{a}</span></td><td><b>{b}</b></td>'
                   f'<td>{status(c, {"Online": "#079455", "Cek": "#d97706", "Jeda": "#94a3b8"}[c])}</td><td class="tn">{e}</td>'
                   f'<td>{bd(f, "green" if f == "Pass" else "amber" if c == "Cek" else "slate")}</td></tr>' for a, b, c, e, f in d["cams"])
    cams = card("Kamera", f'<table class="tbl cp"><thead><tr><th>Kamera</th><th>Line</th><th>Status</th><th>Frame rate</th><th>Cek gambar</th></tr></thead>'
                f'<tbody>{crow}</tbody></table>', icon="photo_camera", right=btn("Tambah kamera (RTSP / ONVIF)", "add", "sm"),
                cb_style="padding:10px 6px 6px")
    rrow = "".join(f'<tr><td><b>{a}</b></td><td class="sec">{b}</td><td>{sev(s)}</td><td>{tg(True)}</td></tr>' for a, b, s in d["rules"])
    rules = card("Aturan alert", f'<table class="tbl cp"><thead><tr><th>Kapan</th><th>Lalu</th><th>Tingkat</th><th>Aktif</th></tr></thead>'
                 f'<tbody>{rrow}</tbody></table>', icon="rule", right=btn("Aturan baru", "add", "sm"), cb_style="padding:10px 6px 6px")
    esc = card("Eskalasi", '<div class="col" style="gap:10px;font-size:13.5px">'
               f'<div class="row" style="gap:10px">{bd("Tinggi", "red", "error")}<span>Line Supervisor langsung → QC Manager setelah 5 menit → Plant Admin setelah 15 menit</span></div>'
               f'<div class="row" style="gap:10px">{bd("Sedang", "amber", "warning")}<span>Line Supervisor · ringkasan shift ke QC Manager</span></div>'
               f'<div class="row" style="gap:10px">{bd("Rendah", "blue", "info")}<span>Hanya di laporan shift</span></div></div>', icon="campaign")
    ir = "".join(f'<div class="ev"><span class="it slate">{I("hub", True, 19)}</span><div class="grow"><div class="t1">{a}</div>'
                 f'<div class="t2">{b}</div></div>{status("Online" if c == "Terhubung" else "Tersedia", "#079455" if c == "Terhubung" else "#94a3b8")}</div>'
                 for a, b, c in d["ints"])
    ints = card("Integrasi", ir, icon="hub")
    img, t1, t2, t3 = d["wa"]
    wa = card("Contoh pesan WhatsApp", '<div style="background:#e7f6e7;border-radius:12px;padding:12px;font-size:13px;line-height:1.45">'
              f'<b>{name} · Pabrik A</b><br>{I("error", True, 16, "#dc2626")} <b>{t1}</b> · {t2}<br>{t3}'
              f'<img class="thumb" src="../img/{img}" style="width:100%;height:190px;object-fit:cover;margin-top:8px">'
              '<div class="mut" style="margin-top:6px">Balas 1 = saya tangani · 2 = alarm palsu</div></div>', icon="chat")
    body = (ph("Kamera, Alert & Integrasi", f"Kamera yang dipakai {name}, siapa diberi tahu, dan sistem mana yang menerima datanya",
               btn("Jalankan cek kamera", "fact_check"))
            + grid("1fr 520px", [f'<div class="col" style="gap:18px">{cams}{rules}{esc}</div>', f'<div class="col" style="gap:18px">{ints}{wa}</div>'],
                   18, "flex:1;min-height:0"))
    return app(product, "settings", body, user=("Rina Hartono", "Plant Admin", "blue"))
