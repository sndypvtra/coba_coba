#!/usr/bin/env python3
"""Build architecture_multi_pabrik.drawio: two plants, each with its own server
(video analytics, recording, database and web app), no central server, and
Tailscale so a laptop on any network can open each plant's web app.

WARNING: this OVERWRITES ../architecture_multi_pabrik.drawio. Once the file is
edited by hand in draw.io, change the layout there, not here.

Every icon is read from tools/multisite_icons/ and base64-embedded, so the
diagram opens with no network. Sources:

  logos/*, simple-icons/*, mdi/*, material-symbols/*  via api.iconify.design
      (Iconify logos MIT/CC0, Simple Icons CC0, MDI + Material Symbols Apache-2.0;
      brand marks belong to their owners)
  cam.png, switch.png, server.svg, laptop.svg   draw.io clip art (Apache-2.0)
  mediamtx.png                                  github.com/bluenviron/mediamtx
  webapp_a.jpg, webapp_b.jpg   the Produce Grading Dashboard TV pages of
      projects/factory_mockup (tomato for plant A, lemon for plant B), cut down to
      one product per plant; re-shoot them with --shots

    python tools/build_multisite_diagram.py           # write the .drawio
    python tools/build_multisite_diagram.py --shots   # re-shoot the two web-app pictures first
"""

import base64
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "architecture_multi_pabrik.drawio"
ICONS = Path(__file__).with_name("multisite_icons")

W, H = 2560, 1660
FONT = "fontFamily=Helvetica;"

INK = "#111827"
BODY = "#374151"
MUTE = "#6B7280"
LINE = "#CBD5E1"
EDGE_C = "#C2410C"     # plant server, the hero of each plant
EVENT = "#1D4ED8"      # app data: events, web app, API
VIDEO = "#7C3AED"      # live video, on demand
RTSP = "#6B7280"
CABLE = "#9CA3AF"
RED = "#DC2626"        # site boundary
GPU = "#FDBA74"
NET = "#2B4C9B"

CELLS: list[str] = []
_n = [0]


def nid(prefix="c"):
    _n[0] += 1
    return f"{prefix}{_n[0]}"


def esc(v):
    return html.escape(v, quote=True)


def uri(name):
    p = ICONS / name
    kind = {".svg": "svg+xml", ".jpg": "jpeg"}.get(p.suffix, "png")
    # draw.io splits style on ';' so the data URI carries no ';base64'
    return f"data:image/{kind}," + base64.b64encode(p.read_bytes()).decode()


def cell(value, style, x, y, w, h, cid=None):
    cid = cid or nid()
    CELLS.append(
        f'<mxCell id="{cid}" value="{esc(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    return cid


def text(value, x, y, w, h, size=11, color=BODY, align="left", valign="top",
         bold=False, extra=""):
    st = (f"text;html=1;whiteSpace=wrap;{FONT}align={align};verticalAlign={valign};"
          f"fontSize={size};fontColor={color};spacing=0;" + ("fontStyle=1;" if bold else "")
          + extra)
    return cell(value, st, x, y, w, h)


def box(x, y, w, h, value="", stroke=LINE, fill="#FFFFFF", sw=1, dashed=False,
        arc=6, size=11, color=BODY, align="left", valign="top", pad=10, cid=None,
        extra=""):
    st = (f"rounded=1;arcSize={arc};absoluteArcSize=1;whiteSpace=wrap;html=1;{FONT}"
          f"fillColor={fill};strokeColor={stroke};strokeWidth={sw};fontSize={size};"
          f"fontColor={color};align={align};verticalAlign={valign};spacing={pad};"
          + ("dashed=1;dashPattern=6 4;" if dashed else "") + extra)
    return cell(value, st, x, y, w, h, cid)


def chip(value, x, y, w, h=20, fill="#F1F5F9", color="#475569", stroke="none",
         size=10, bold=False, cid=None):
    st = (f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;{FONT}fillColor={fill};"
          f"strokeColor={stroke};fontSize={size};fontColor={color};align=center;"
          f"verticalAlign=middle;spacing=0;" + ("fontStyle=1;" if bold else ""))
    return cell(value, st, x, y, w, h, cid)


def img(name, x, y, w, h):
    st = f"shape=image;html=1;imageAspect=1;aspect=fixed;image={uri(name)};"
    return cell("", st, x, y, w, h)


def edge(src, tgt, color=RTSP, width=2, exit_=(1, .5), entry=(0, .5), pts=(),
         dashed=False, arrow=True, start=False, dotted=False, label="", lsize=10):
    ex, ey = exit_
    nx, ny = entry
    st = ("html=1;rounded=1;arcSize=10;jumpStyle=arc;jumpSize=10;"
          + ("edgeStyle=none;" if pts else "edgeStyle=orthogonalEdgeStyle;")
          + f"strokeColor={color};strokeWidth={width};{FONT}fontSize={lsize};"
          f"fontColor={color};labelBackgroundColor=#FFFFFF;"
          f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0;"
          + ("endArrow=block;endFill=1;endSize=7;" if arrow else "endArrow=none;")
          + ("startArrow=block;startFill=1;startSize=7;" if start else "startArrow=none;")
          + ("dashed=1;dashPattern=8 5;" if dashed else "")
          + ("dashed=1;dashPattern=1 4;" if dotted else ""))
    pts_xml = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in pts)
    arr = f'<Array as="points">{pts_xml}</Array>' if pts else ""
    CELLS.append(
        f'<mxCell id="{nid("e")}" value="{esc(label)}" style="{st}" edge="1" parent="1" '
        f'source="{src}" target="{tgt}"><mxGeometry relative="1" as="geometry">{arr}'
        f"</mxGeometry></mxCell>")


def free(x1, y1, x2, y2, color, width=2, dashed=False, dotted=False, arrow=True):
    st = (f"html=1;endArrow={'block;endFill=1;endSize=7' if arrow else 'none'};"
          f"strokeColor={color};strokeWidth={width};"
          + ("dashed=1;dashPattern=8 5;" if dashed else "")
          + ("dashed=1;dashPattern=1 4;" if dotted else ""))
    CELLS.append(
        f'<mxCell id="{nid("e")}" style="{st}" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>'
        f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/></mxGeometry></mxCell>')


def shots():
    """Shoot the plant A and plant B web-app pictures from the factory mockup pages.

    Plant A runs tomato only and plant B lemon only, so each page loses the other
    product's tab, and the lemon page is moved to Pabrik B.
    """
    import cv2
    sys.path.insert(0, str(ROOT / "projects" / "factory_mockup"))
    from build import shoot
    pages = ROOT / "projects" / "factory_mockup" / "html"
    tomato = ('<span class=""><span class="i">nutrition</span>Tomat · USDA</span>')
    lemon_on = ('<span class=""><span class="i">nutrition</span>Lemon · OECD</span>')
    for out, page, cuts in [
            ("webapp_a.jpg", "produce_grading__03_dashboard_tv_tomat.html", [(lemon_on, "")]),
            ("webapp_b.jpg", "produce_grading__04_dashboard_tv_lemon.html",
             [(tomato, ""), ("Pabrik A · Cikarang", "Pabrik B · Karawang")])]:
        src = (pages / page).read_text()
        for old, new in cuts:
            assert old in src, (page, old)
            src = src.replace(old, new)
        tmp = pages / f"_diagram_{out[:-4]}.html"
        tmp.write_text(src)
        png = tmp.with_suffix(".png")
        try:
            shoot(tmp, png, 1.0)
            pic = cv2.resize(cv2.imread(str(png)), (1280, 720), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(ICONS / out), pic, [cv2.IMWRITE_JPEG_QUALITY, 88])
        finally:
            tmp.unlink(missing_ok=True)
            png.unlink(missing_ok=True)
        print("shot", out)


if "--shots" in sys.argv:
    shots()


def fy(y, top, h):
    """Relative 0..1 position of absolute y on a box edge."""
    return round((y - top) / h, 4)


# ================================================================ title =====
text("Arsitektur Video Analytics 2 Pabrik &#8212; Server per Pabrik + Tailscale", 0, 16, W,
     40, size=30, color=INK, align="center", bold=True)
text("Tiap pabrik punya server sendiri: AI, rekaman, database dan webapp. <b>Tidak ada server "
     "pusat:</b> laptop di jaringan mana pun membuka webapp tiap pabrik langsung lewat "
     "Tailscale.", 0, 60, W, 22, size=14, color=MUTE, align="center")

# ================================================================ zones =====
ZT, ZB = 110, 1460
ZONES = [
    (20, 270, "1. AKUISISI VIDEO", "#F3F4F6", "#4B5563"),
    (305, 1485, "2. SERVER PABRIK (SEMUA DI LOKASI MASING-MASING)", "#FDF3E7", EDGE_C),
    (1805, 300, "3. JARINGAN &#183; TAILSCALE", "#EAF0FA", NET),
    (2120, 420, "4. PENGGUNA (BEDA JARINGAN)", "#F3F4F6", "#4B5563"),
]
for x, w, title, fill, col in ZONES:
    box(x, ZT, w, ZB - ZT, stroke="none", fill=fill, arc=10)
    text(title, x, ZT + 12, w, 24, size=17, color=col, align="center", bold=True)

TS_X, TS_W = 1610, 145      # Tailscale box on each server
WEB_DY, VID_DY = 445, 510   # where the webapp and the video leave the server


# ================================================================ plants ====
def plant(L, y0):
    """One plant. L is the site letter ('A', 'B'); returns the Tailscale box id."""
    l = L.lower()

    # site boundary
    box(30, y0, 1752, 575, stroke=RED, fill="none", sw=2, dashed=True, arc=12)
    chip(f"LOKASI PABRIK {L} &#183; jaringan lokal pabrik {L}", 48, y0 - 11, 300, 22,
         fill="#FFFFFF", color=RED, stroke=RED, size=11, bold=True)

    # 1. cameras, switch, UPS
    cam = box(42, y0 + 30, 226, 220)
    text("Kamera IP (&#215;N)", 42, y0 + 40, 226, 20, size=14, color=INK, align="center",
         bold=True)
    img("cam.png", 78, y0 + 66, 60, 65)
    img("cam.png", 172, y0 + 66, 60, 65)
    text(f"{l}_cam01 &#8230; {l}_camNN", 42, y0 + 136, 226, 16, size=11, color=MUTE,
         align="center", extra="fontFamily=Courier New;")
    for i, c in enumerate(["RTSP", "ONVIF", "H.264 / H.265", "main + sub"]):
        chip(c, 58 + (i % 2) * 104, y0 + 160 + (i // 2) * 26, 94)
    text("Cat6 &#183; PoE 802.3af/at", 42, y0 + 216, 226, 16, size=10, color=MUTE,
         align="center")

    sw = box(42, y0 + 275, 226, 120)
    img("switch.png", 54, y0 + 290, 84, 45)
    text("<b>PoE Switch</b><br>VLAN kamera<br>LAN lokal", 146, y0 + 284, 118, 58,
         size=12, color=BODY)
    text("uplink 1 GbE ke server pabrik<br>1 koneksi RTSP per kamera", 42, y0 + 348, 226,
         34, size=10, color=MUTE, align="center")
    edge(cam, sw, color=CABLE, exit_=(.5, 1), entry=(.5, 0), arrow=False)

    ups = box(42, y0 + 420, 226, 85, stroke=LINE, dashed=True)
    img("battery.svg", 54, y0 + 442, 40, 40)
    text("<b>UPS</b> <font color='#9CA3AF'>(opsional)</font><br>daya untuk switch<br>"
         "+ server pabrik", 102, y0 + 434, 160, 58, size=12)

    # 2. the plant server
    ey, eh = y0 + 30, 515
    ec = box(320, ey, 1455, eh, stroke=EDGE_C, sw=2, arc=8)
    img("server.svg", 334, y0 + 42, 24, 48)
    text(f"SERVER PABRIK {L}", 368, y0 + 40, 600, 24, size=17, color=EDGE_C, bold=True)
    text("1 GPU server on-prem &#183; Ubuntu LTS &#183; Docker Compose &#183; NVIDIA GPU "
         "(CUDA / TensorRT) &#183; AI, rekaman, database dan webapp di satu mesin",
         368, y0 + 66, 1000, 18, size=11.5, color=MUTE)
    img("ubuntu.svg", 1658, y0 + 46, 26, 26)
    img("docker.svg", 1694, y0 + 46, 26, 26)
    img("nvidia.svg", 1730, y0 + 46, 30, 30)
    edge(ups, ec, color=CABLE, exit_=(1, .5), entry=(0, fy(y0 + 462.5, ey, eh)),
         arrow=False, dotted=True)

    # MediaMTX
    my, mh = y0 + 130, 230
    mtx = box(340, my, 230, mh, stroke="#94A3B8")
    img("mediamtx.png", 352, y0 + 142, 150, 32)
    text("<b>MediaMTX</b><br>ingest + relay + recording lokal<br>"
         f"<font color='{MUTE}'>path <b>{l}_cam01</b> (main)<br>"
         f"path <b>{l}_cam01_sub</b> (sub)</font>", 352, y0 + 182, 210, 76, size=12)
    chip("RTSP :8554", 352, y0 + 268, 100)
    chip("playback :9996", 460, y0 + 268, 100)
    chip("rekaman main stream &#8594; disk lokal", 352, y0 + 294, 208)
    chip("1 koneksi ke kamera, banyak pembaca", 352, y0 + 320, 208)
    edge(sw, mtx, color=RTSP, exit_=(1, .5), entry=(0, fy(y0 + 335, my, mh)), label="RTSP")

    # WebRTC / WHEP
    wy, wh = y0 + 400, 125
    whep = box(340, wy, 230, wh, stroke=VIDEO, fill="#F5F3FF", sw=1.5)
    img("webrtc.svg", 536, y0 + 408, 24, 24)
    text(f"<b><font color='{VIDEO}'>WebRTC / WHEP :8889</font></b><br>"
         "hanya dibuka saat ada viewer<br>ICE: UDP :8189<br>"
         "HTTPS: sertifikat <i>tailscale cert</i>", 352, y0 + 410, 200, 100, size=12)
    edge(mtx, whep, color=VIDEO, exit_=(.5, 1), entry=(.5, 0), dashed=True,
         label="on-demand")

    # CV worker
    box(600, y0 + 110, 430, 260, stroke="#F59E0B", fill="#FFFBF5", dashed=True)
    text("<b>CV Worker</b> <font color='#9A3412'>(container &#183; Python)</font>",
         612, y0 + 118, 300, 20, size=13, color="#9A3412")
    for i, ic in enumerate(["python.svg", "opencv.svg", "pytorch.svg", "ultralytics.svg"]):
        img(ic, 906 + i * 29, y0 + 117, 22, 22)
    text(f"pull rtsp://localhost:8554/{l}_cam01_sub &#8230; {l}_camNN_sub", 612,
         y0 + 143, 410, 16, size=10.5, extra="fontFamily=Courier New;")

    def step(t, s, x, y, w, gpu):
        return box(x, y, w, 54, f"<b>{t}</b><br><font style='font-size:10px'>{s}</font>",
                   stroke="#E07B1A" if gpu else "#94A3B8", fill=GPU if gpu else "#FFFFFF",
                   size=11.5, color=INK, align="center", valign="middle", pad=2)

    dec = step("DECODE", "NVDEC / FFmpeg", 615, y0 + 168, 125, True)
    yolo = step("YOLO", ("tomat" if L == "A" else "lemon") + " &#183; PPE/person", 755,
                y0 + 168, 135, True)
    trk = step("ByteTrack", "track_id", 905, y0 + 168, 115, False)
    evt = step("EVENT LOGIC", "grade &#183; lot &#183; aturan PPE", 885, y0 + 244, 135, False)
    meta = step("metadata JSON", "cam &#183; ts &#183; bbox &#183; track_id &#183; class "
                "&#183; event", 615, y0 + 244, 255, False)
    for a, b, ex_, en_ in [(dec, yolo, (1, .5), (0, .5)), (yolo, trk, (1, .5), (0, .5)),
                           (trk, evt, (.5, 1), (.5, 0)), (evt, meta, (0, .5), (1, .5))]:
        edge(a, b, color=RTSP, width=1.5, exit_=ex_, entry=en_)
    edge(mtx, dec, color=RTSP, exit_=(1, fy(y0 + 195, my, mh)), entry=(0, .5))
    box(615, y0 + 312, 12, 12, stroke="#E07B1A", fill=GPU, arc=2)
    text("GPU", 632, y0 + 310, 30, 16, size=10, color=MUTE)
    box(666, y0 + 312, 12, 12, stroke="#94A3B8", arc=2)
    text("CPU", 683, y0 + 310, 30, 16, size=10, color=MUTE)
    text("Model: YOLO &#8594; ONNX &#8594; TensorRT <b>.engine</b>,<br>"
         "dibangun per tipe GPU (FP16)", 762, y0 + 306, 262, 34, size=10, color=MUTE)

    # local RabbitMQ
    ry, rh = y0 + 390, 105
    rmq = box(600, ry, 300, rh, stroke="#94A3B8")
    img("rabbitmq.svg", 866, y0 + 398, 24, 24)
    text("<b>RabbitMQ lokal</b><br>antrean CV Worker &#8594; FastAPI<br>"
         "<b>event</b>: durable &#183; <b>track</b>: TTL pendek<br>"
         "AI tetap jalan walau API restart", 612, y0 + 398, 260, 90, size=12)
    edge(meta, rmq, color=EVENT, exit_=(fy(745, 615, 255), 1), entry=(fy(745, 600, 300), 0),
         label="publish &#183; AMQP :5672")

    # schema (top of the app column)
    box(1060, y0 + 110, 525, 118, stroke="#94A3B8", fill="#F8FAFC")
    text(f"<b>Skema data</b> &#183; database lokal pabrik {L}", 1072, y0 + 116, 400, 18,
         size=12, color=INK)
    for i, (name, cols) in enumerate([
            ("camera", "id &#183; rtsp_path<br>zona &#183; status"),
            ("event", "ts &#183; cam_id &#183; track_id<br>class &#183; bbox &#183; event_type"),
            ("alert", "event_id &#183; status<br>user &#183; ack_at")]):
        x = 1072 + i * 170
        chip(f"<b>{name}</b>" + (" &#183; hypertable" if name == "event" else ""), x,
             y0 + 140, 160, 20, fill="#DBE4F3", color=NET, size=10.5)
        text(cols, x + 4, y0 + 166, 158, 40, size=10.5, extra="fontFamily=Courier New;")

    # PostgreSQL, FastAPI, Nginx + webapp, notifications
    pg = box(1060, y0 + 250, 260, 115,
             "<b>PostgreSQL</b> + TimescaleDB<br>event pabrik ini saja<br>"
             "retensi + compression<br>backup harian (NAS lokal)", stroke="#94A3B8", size=12)
    img("timescale.svg", 1258, y0 + 260, 22, 22)
    img("postgresql.svg", 1286, y0 + 258, 26, 26)
    api = box(1060, y0 + 390, 260, 110,
              "<b>FastAPI</b> (uvicorn)<br>event &#8594; PostgreSQL<br>"
              "track &#8594; WebSocket (overlay live)<br>REST /api &#183; WS /ws &#183; JWT",
              stroke="#94A3B8", size=12)
    img("fastapi.svg", 1288, y0 + 398, 24, 24)
    web = box(1345, y0 + 390, 240, 110,
              "<b>Nginx :443</b> + Webapp<br>Produce Grading, " + ("tomat" if L == "A" else "lemon") + "<br>"
              "proxy /api &amp; /ws &#8594; FastAPI<br>TLS: <i>tailscale cert</i>",
              stroke="#94A3B8", size=12)
    img("react.svg", 1524, y0 + 398, 24, 24)
    img("nginx.svg", 1552, y0 + 398, 24, 24)
    box(1345, y0 + 250, 240, 115, "<b>Notifikasi</b> <font color='#9CA3AF'>(opsional)</font>"
        "<br>WhatsApp / email / webhook<br>dipicu event kritis", stroke="#9CA3AF",
        dashed=True, size=12)
    img("whatsapp.svg", 1552, y0 + 258, 24, 24)
    edge(rmq, api, color=EVENT, exit_=(1, .5), entry=(0, fy(ry + rh / 2, y0 + 390, 110)),
         label="consume")
    edge(api, pg, color=EVENT, exit_=(.5, 0), entry=(.5, 1), start=True,
         label="INSERT / SELECT")
    edge(api, web, color=EVENT, exit_=(1, .5), entry=(0, .5))

    # Tailscale on the server
    ty, th = y0 + 110, 415
    ts = box(TS_X, ty, TS_W, th, stroke="#334155", fill="#F8FAFC", sw=1.5)
    img("tailscale.svg", TS_X + 52, y0 + 122, 40, 40)
    text(f"<b>Tailscale</b><br>tailscaled<br><br>MagicDNS<br>"
         f"<b><font color='{INK}'>server-pabrik-{l}</font></b><br><br>tag:pabrik<br><br>"
         f"<font color='{MUTE}'>keluar ke internet:<br>UDP 41641 / TCP 443<br>"
         "(outbound saja)</font><br><br>IP tailnet<br>100.x.y.z", TS_X + 4, y0 + 172,
         TS_W - 8, 330, size=12, align="center")
    edge(web, ts, color=EVENT, exit_=(1, fy(y0 + WEB_DY, y0 + 390, 110)),
         entry=(0, fy(y0 + WEB_DY, ty, th)))
    edge(whep, ts, color=VIDEO, exit_=(1, fy(y0 + VID_DY, wy, wh)),
         entry=(0, fy(y0 + VID_DY, ty, th)), dashed=True)
    return ts


A0, B0 = 160, 770
TS_A = plant("A", A0)
TS_B = plant("B", B0)

# Pabrik C, D, ...
box(30, 1362, 1752, 78, stroke="#9CA3AF", fill="none", sw=1.5, dashed=True, arc=12)
text("<b>PABRIK C, D, &#8230;</b> &#8212; polanya sama: Kamera IP &#8594; Server Pabrik "
     "(MediaMTX &#183; CV Worker &#183; RabbitMQ &#183; FastAPI &#183; PostgreSQL &#183; "
     "Webapp &#183; Tailscale) &#183; MagicDNS <b>server-pabrik-c</b><br>"
     "Tambah pabrik = 1 server + kamera + join tailnet (tag:pabrik) + 1 bookmark baru di "
     "laptop. Server pabrik lain tidak berubah.", 50, 1372, 1720, 60, size=13, color=MUTE)

# ============================================================ tailnet =======
box(1820, 200, 270, 190,
    "<br><br><br><b>TAILNET</b> (WireGuard, terenkripsi end-to-end)<br>"
    "MagicDNS: server-pabrik-a, server-pabrik-b<br>"
    f"<font color='{MUTE}'>login user: SSO + MFA<br>device harus di-approve admin</font>",
    stroke="#94A3B8", size=12)
img("tailscale.svg", 1832, 210, 36, 36)
box(1820, 410, 270, 172,
    f"<b><font color='{RED}'>Tanpa server pusat</font></b><br>"
    "Laptop tersambung langsung ke server tiap pabrik (P2P lewat Tailscale). "
    "Data tiap pabrik tetap di server pabriknya.<br><br>"
    "Video hanya mengalir saat ada yang menonton.",
    stroke=RED, fill="#FEF2F2", size=12)
box(1820, 700, 270, 490,
    "<b>ACL (policy file)</b><br><br>"
    "<font face='Courier New'>group:viewer<br>&#8594; tag:pabrik :443</font><br>"
    f"<font color='{MUTE}'>webapp, API, WebSocket</font><br><br>"
    "<font face='Courier New'>group:viewer<br>&#8594; tag:pabrik :8889, UDP :8189</font><br>"
    f"<font color='{MUTE}'>video live</font><br><br>"
    "<font face='Courier New'>tag:pabrik &#8596; tag:pabrik<br>&#8594; ditolak</font><br>"
    f"<font color='{MUTE}'>server A dan B tidak saling akses</font><br><br>"
    "<font face='Courier New'>group:ops &#8594; tag:pabrik :22</font><br>"
    f"<font color='{MUTE}'>maintenance (opsional)</font><br><br>"
    f"<font color='{MUTE}'>Bisa dibatasi per pabrik: group:viewer-a hanya ke "
    "server-pabrik-a.</font>",
    stroke="#94A3B8", size=12)
box(1820, 1310, 270, 112,
    "Tanpa port forwarding dan tanpa IP publik di pabrik. Jalur langsung (P2P); "
    "relay DERP hanya jika NAT tidak tembus.", stroke="#94A3B8", size=12)

# ============================================================== user =======
UY, UH = 560, 780
usr = box(2140, UY, 380, UH, stroke="#94A3B8", sw=1.5)


def mock(y, L):
    l = L.lower()
    fruit = "tomat" if L == "A" else "lemon"
    box(2160, y, 340, 240, stroke="#94A3B8", arc=6)
    box(2160, y, 340, 22, f"&#9679; &#9679; &#9679;&#160;&#160; https://server-pabrik-{l}"
        ".&lt;tailnet&gt;.ts.net", stroke="#94A3B8", fill="#E5E7EB", size=10, color=BODY,
        valign="middle", pad=6, arc=6)
    img(f"webapp_{l}.jpg", 2162, y + 23, 336, 189)
    text(f"<b>Webapp Pabrik {L}</b> &#183; Produce Grading, {fruit}", 2170, y + 216, 324, 18,
         size=11, color=INK)


mock(UY + 12, "A")
mock(UY + UH - 250, "B")
img("laptop.svg", 2205, 818, 104, 66)
img("smartphone.svg", 2340, 822, 54, 54)
text("Laptop / HP user", 2140, 888, 380, 22, size=15, color=INK, align="center", bold=True)
text("di jaringan mana pun (kantor, rumah, 4G)<br>Tailscale client &#183; login SSO &#183; "
     "group:viewer", 2140, 910, 380, 36, size=11.5, color=MUTE, align="center")
text("Buka 2 alamat (bookmark), satu per pabrik.<br>"
     f"<b><font color='{EVENT}'>Webapp, event, kotak &amp; label</font></b> &#8592; HTTPS + "
     "WSS dari server pabrik<br>"
     f"<b><font color='{VIDEO}'>Video live</font></b> &#8592; WebRTC/WHEP dari server pabrik "
     "yang sama, hanya saat dibuka", 2156, 952, 350, 84, size=12)
text("<i>Gambar: mockup Produce Grading (Dashboard TV); angka di layar = ilustrasi.</i>",
     2156, 1040, 350, 32, size=10, color="#9CA3AF")

# ======================================================== WAN flows =========
for ts, y0, L in [(TS_A, A0, "A"), (TS_B, B0, "B")]:
    l = L.lower()
    edge(ts, usr, color=EVENT, width=2.5, exit_=(1, fy(y0 + WEB_DY, y0 + 110, 415)),
         entry=(0, fy(y0 + WEB_DY, UY, UH)))
    edge(ts, usr, color=VIDEO, width=2.5, dashed=True,
         exit_=(1, fy(y0 + VID_DY, y0 + 110, 415)), entry=(0, fy(y0 + VID_DY, UY, UH)))
    chip(f"webapp {L} &#183; HTTPS + WSS :443", 1838, y0 + WEB_DY - 10, 234, 20,
         fill="#FFFFFF", color=EVENT, stroke=EVENT, size=10.5, bold=True)
    chip(f"video {L} &#183; WHEP :8889 &#183; saat ditonton", 1838, y0 + VID_DY - 10, 234,
         20, fill="#FFFFFF", color=VIDEO, stroke=VIDEO, size=10.5, bold=True)

# ============================================================== footer =====
FY = 1478
box(20, FY, 740, 166, stroke=LINE)
text("Keterangan", 34, FY + 10, 200, 20, size=13, color=INK, bold=True)
LEG = [
    (dict(color=CABLE, arrow=False), "kabel fisik (LAN / PoE)"),
    (dict(color=RTSP), "RTSP / proses lokal di server"),
    (dict(color=EVENT, width=2.5), "data aplikasi: event, webapp, API"),
    (dict(color=VIDEO, width=2.5, dashed=True), "video live (hanya saat ditonton)"),
    (dict(color=CABLE, dotted=True, arrow=False), "daya listrik"),
    (dict(color=RED, dashed=True, arrow=False), "batas lokasi pabrik"),
]
for i, (kw, label) in enumerate(LEG):
    cx, cy = 34 + (i // 3) * 360, FY + 50 + (i % 3) * 32
    free(cx, cy, cx + 56, cy, **kw)
    text(label, cx + 68, cy - 9, 280, 18, size=11.5)
box(34, FY + 140, 14, 14, stroke="#E07B1A", fill=GPU, arc=2)
text("langkah di GPU", 54, FY + 139, 120, 18, size=11.5)
box(190, FY + 140, 14, 14, stroke="#9CA3AF", dashed=True, arc=2)
text("garis putus abu = opsional", 210, FY + 139, 220, 18, size=11.5)

box(780, FY, 1760, 166, stroke=LINE)
text("<b>Jika internet pabrik putus:</b> server pabrik tetap jalan (deteksi, rekaman, "
     "database). User di LAN pabrik tetap bisa membuka webapp lewat alamat lokal; dari luar "
     "baru bisa lagi setelah tersambung. Data tidak hilang.<br>"
     "<b>Port:</b> lewat Tailscale hanya 443 (webapp, API, WebSocket) dan 8889 + UDP 8189 "
     "(video). RTSP 8554, AMQP 5672 dan PostgreSQL 5432 hanya lokal di server. Tidak ada port "
     "yang dibuka ke internet.<br>"
     "<b>Bandwidth internet pabrik:</b> hampir nol saat tidak ada yang membuka webapp. Saat "
     "ditonton: &#177; 0,5&#8211;2 Mbps per sub-stream per viewer + overlay puluhan kbps. "
     "Perkiraan, ukur di lokasi.<br>"
     "<b>Konsekuensi tanpa server pusat:</b> tidak ada dashboard atau laporan gabungan "
     "otomatis; akun, backup dan update dikelola per server. Jika nanti perlu gabungan, "
     "tambahkan server pusat atau webapp yang membaca API kedua pabrik, tanpa mengubah "
     "server pabrik.<br>"
     "<b>Keamanan:</b> kamera di VLAN sendiri dan hanya bisa dibaca server pabrik; user hanya "
     "melihat pabrik sesuai haknya (ACL Tailscale + role di webapp).",
     796, FY + 12, 1730, 124, size=12.5)
text("Logo &amp; ikon: Iconify (logos, Simple Icons CC0, MDI, Material Symbols), draw.io "
     "clip art (Apache 2.0), MediaMTX (bluenviron). Logo adalah merek dagang pemiliknya.",
     796, FY + 144, 1730, 16, size=10.5, color="#9CA3AF")

# ================================================================ write ====
xml = (
    '<mxfile host="app.diagrams.net" agent="tools/build_multisite_diagram.py" '
    'version="24.7.17" type="device">\n'
    '  <diagram id="multi-pabrik" name="2 Pabrik + Tailscale">\n'
    f'    <mxGraphModel dx="{W}" dy="{H}" grid="0" gridSize="10" guides="1" tooltips="1" '
    f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" '
    f'pageHeight="{H}" math="0" shadow="0" background="#FFFFFF">\n'
    '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
    + "\n".join("        " + c for c in CELLS)
    + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"
)
OUT.write_text(xml)
print(f"wrote {OUT} ({len(xml) // 1024} KB, {len(CELLS)} cells)")
