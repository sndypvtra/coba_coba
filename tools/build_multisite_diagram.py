#!/usr/bin/env python3
"""Build architecture_multi_pabrik.drawio: two plants, each with its own edge
video analytics, one central server, and Tailscale between them.

WARNING: this OVERWRITES ../architecture_multi_pabrik.drawio. Once the file is
edited by hand in draw.io, change the layout there, not here.

Every icon is read from tools/multisite_icons/ and base64-embedded, so the
diagram opens with no network. Sources:

  logos/*, simple-icons/*, mdi/*, material-symbols/*  via api.iconify.design
      (Iconify logos MIT/CC0, Simple Icons CC0, MDI + Material Symbols Apache-2.0;
      brand marks belong to their owners)
  cam.png, switch.png, server.svg, laptop.svg   draw.io clip art (Apache-2.0)
  mediamtx.png                                  github.com/bluenviron/mediamtx
"""

import base64
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "architecture_multi_pabrik.drawio"
ICONS = Path(__file__).with_name("multisite_icons")

W, H = 2520, 1660
FONT = "fontFamily=Helvetica;"

INK = "#111827"
BODY = "#374151"
MUTE = "#6B7280"
LINE = "#CBD5E1"
EDGE_C = "#C2410C"     # edge node, the hero of each plant
EVENT = "#1D4ED8"      # event / metadata flow
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
    kind = "svg+xml" if p.suffix == ".svg" else "png"
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


def fy(y, top, h):
    """Relative 0..1 position of absolute y on a box edge."""
    return round((y - top) / h, 4)


# ================================================================ title =====
text("Arsitektur Video Analytics Multi-Pabrik", 0, 16, W, 40, size=30, color=INK,
     align="center", bold=True)
text("Edge AI di tiap pabrik &#183; server pusat untuk event semua pabrik &#183; "
     "Tailscale sebagai jaringan privat. <b>Yang mengalir terus hanya event/metadata; "
     "video live dibuka langsung dari edge saat ada yang menonton.</b>",
     0, 60, W, 22, size=14, color=MUTE, align="center")

# ================================================================ zones =====
ZT, ZB = 110, 1460
ZONES = [
    (20, 270, "1. AKUISISI VIDEO", "#F3F4F6", "#4B5563"),
    (305, 925, "2. EDGE NODE (PER PABRIK)", "#FDF3E7", EDGE_C),
    (1245, 255, "3. JARINGAN &#183; TAILSCALE", "#EAF0FA", NET),
    (1515, 640, "4. SERVER PUSAT / DC", "#E9EEF7", NET),
    (2170, 330, "5. PENGGUNA", "#F3F4F6", "#4B5563"),
]
for x, w, title, fill, col in ZONES:
    box(x, ZT, w, ZB - ZT, stroke="none", fill=fill, arc=10)
    text(title, x, ZT + 12, w, 24, size=17, color=col, align="center", bold=True)


# ================================================================ plants ====
def plant(L, y0):
    """One plant. L is the site letter ('A', 'B'); returns the Tailscale box id."""
    l = L.lower()

    # site boundary
    box(30, y0, 1192, 575, stroke=RED, fill="none", sw=2, dashed=True, arc=12)
    chip(f"LOKASI PABRIK {L} &#183; site_id = {l}", 48, y0 - 11, 250, 22, fill="#FFFFFF",
         color=RED, stroke=RED, size=11, bold=True)

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
    text("uplink 1 GbE ke edge node<br>1 koneksi RTSP per kamera", 42, y0 + 348, 226, 34,
         size=10, color=MUTE, align="center")
    edge(cam, sw, color=CABLE, exit_=(.5, 1), entry=(.5, 0), arrow=False)

    ups = box(42, y0 + 420, 226, 85, stroke=LINE, dashed=True)
    img("battery.svg", 54, y0 + 442, 40, 40)
    text("<b>UPS</b> <font color='#9CA3AF'>(opsional)</font><br>daya untuk switch<br>"
         "+ edge node", 102, y0 + 434, 160, 58, size=12)

    # 2. edge node
    ey, eh = y0 + 30, 515
    ec = box(320, ey, 895, eh, stroke=EDGE_C, sw=2, arc=8)
    img("server.svg", 334, y0 + 42, 24, 48)
    text(f"EDGE NODE PABRIK {L}", 368, y0 + 40, 600, 24, size=17, color=EDGE_C, bold=True)
    text("GPU server on-prem &#183; Ubuntu LTS &#183; Docker Compose &#183; "
         "NVIDIA GPU (CUDA / TensorRT)", 368, y0 + 66, 680, 18, size=11.5, color=MUTE)
    img("ubuntu.svg", 1098, y0 + 46, 26, 26)
    img("docker.svg", 1134, y0 + 46, 26, 26)
    img("nvidia.svg", 1170, y0 + 46, 30, 30)
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
    yolo = step("YOLO", "PPE &#183; person", 755, y0 + 168, 135, True)
    trk = step("ByteTrack", "track_id", 905, y0 + 168, 115, False)
    evt = step("EVENT LOGIC", "zona &#183; aturan PPE &#183; durasi", 885, y0 + 244, 135, False)
    meta = step("metadata JSON", "site &#183; cam &#183; ts &#183; bbox &#183; track_id "
                "&#183; class &#183; event", 615, y0 + 244, 255, False)
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
    text("<b>RabbitMQ lokal</b><br><b>event</b>: queue durable, buffer saat WAN putus<br>"
         "<b>track</b> (bbox live): TTL pendek<br>shovel &#8594; RabbitMQ pusat",
         612, y0 + 398, 260, 90, size=12)
    edge(meta, rmq, color=EVENT, exit_=(fy(745, 615, 255), 1), entry=(fy(745, 600, 300), 0),
         label="publish &#183; AMQP :5672")

    # Tailscale on the edge node
    ty, th = y0 + 110, 415
    ts = box(1060, ty, 140, th, stroke="#334155", fill="#F8FAFC", sw=1.5)
    img("tailscale.svg", 1110, y0 + 122, 40, 40)
    text(f"<b>Tailscale</b><br>tailscaled<br><br>MagicDNS<br>"
         f"<b><font color='{INK}'>edge-pabrik-{l}</font></b><br><br>tag:edge<br><br>"
         f"<font color='{MUTE}'>keluar ke internet:<br>UDP 41641 / TCP 443<br>"
         "(outbound saja)</font><br><br>IP tailnet<br>100.x.y.z", 1064, y0 + 172, 132, 330, size=12, align="center")
    edge(rmq, ts, color=EVENT, exit_=(1, .5), entry=(0, fy(ry + rh / 2, ty, th)),
         label="shovel")
    edge(whep, ts, color=VIDEO, exit_=(1, fy(y0 + 510, wy, wh)),
         entry=(0, fy(y0 + 510, ty, th)), dashed=True)
    return ts


TS_A = plant("A", 160)
TS_B = plant("B", 770)

# Pabrik C, D, ...
box(30, 1362, 1192, 78, stroke="#9CA3AF", fill="none", sw=1.5, dashed=True, arc=12)
text("<b>PABRIK C, D, &#8230;</b> &#8212; polanya sama: Kamera IP &#8594; Edge Node "
     "(MediaMTX &#183; CV Worker &#183; RabbitMQ lokal &#183; Tailscale) &#183; MagicDNS "
     "<b>edge-pabrik-c</b><br>Tambah pabrik = 1 edge node + kamera + join tailnet "
     "(tag:edge) + 1 shovel + 1 baris di tabel <i>site</i>. Server pusat tidak berubah.",
     50, 1372, 1160, 60, size=13, color=MUTE)

# ============================================================ tailnet =======
box(1280, 200, 175, 190,
    "<br><br><br><b>TAILNET</b><br>WireGuard, terenkripsi end-to-end<br>"
    "MagicDNS: edge-pabrik-a,<br>edge-pabrik-b, pusat<br>"
    f"<font color='{MUTE}'>login user: SSO + MFA</font>",
    stroke="#94A3B8", size=12)
img("tailscale.svg", 1292, 210, 36, 36)
box(1280, 410, 175, 170,
    f"<b><font color='{RED}'>Yang lewat WAN</font></b><br>"
    "&#8226; event/metadata: kecil, terus-menerus<br>"
    "&#8226; video: hanya saat ada viewer<br><br>"
    "Video tidak dikirim terus-menerus ke pusat.",
    stroke=RED, fill="#FEF2F2", size=12)
box(1280, 700, 175, 490,
    "<b>ACL (policy file)</b><br><br>"
    "<font face='Courier New'>tag:edge<br>&#8594; tag:pusat :5672</font><br><br>"
    "<font face='Courier New'>group:viewer<br>&#8594; tag:pusat :443</font><br><br>"
    "<font face='Courier New'>group:viewer<br>&#8594; tag:edge :8889,<br>&#160;&#160;UDP :8189</font><br><br>"
    "<font face='Courier New'>tag:edge &#8596; tag:edge<br>&#8594; ditolak</font><br><br>"
    f"<font color='{MUTE}'>Akses SSH ke edge hanya untuk group:ops (opsional).</font>",
    stroke="#94A3B8", size=13)
box(1280, 1300, 175, 112,
    "Tanpa port forwarding dan tanpa IP publik di pabrik. Jalur langsung (P2P); "
    "relay DERP hanya jika NAT tidak tembus.", stroke="#94A3B8", size=11.5)

# ============================================================ central =======
box(1530, 300, 610, 900, stroke=NET, sw=2, arc=8)
img("server.svg", 1546, 312, 24, 48)
text("SERVER PUSAT / DC", 1580, 312, 400, 24, size=17, color=NET, bold=True)
text("VM atau bare-metal &#183; Docker Compose &#183; Tailscale: MagicDNS <b>pusat</b> "
     "(tag:pusat)", 1580, 338, 540, 18, size=11.5, color=MUTE)
img("docker.svg", 2100, 314, 26, 26)

rc = box(1550, 400, 270, 130,
         "<b>RabbitMQ pusat</b><br>exchange <i>events</i> (topic)<br>"
         "routing: &lt;site&gt;.&lt;cam&gt;.event<br>"
         "&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;| &lt;site&gt;.&lt;cam&gt;.track"
         "<br>shovel masuk dari tiap pabrik", stroke="#94A3B8", size=12.5)
img("rabbitmq.svg", 1788, 408, 24, 24)
api = box(1860, 400, 260, 130,
          "<b>FastAPI</b> (uvicorn)<br>consumer &#8594; simpan &#8594; broadcast<br>"
          "event &#8594; PostgreSQL<br>track &#8594; WebSocket (overlay live)<br>"
          "REST /api &#183; WS /ws &#183; auth JWT", stroke="#94A3B8", size=12.5)
img("fastapi.svg", 2088, 408, 24, 24)
pg = box(1550, 580, 270, 140,
         "<b>PostgreSQL</b> + TimescaleDB<br>event semua pabrik<br>"
         "kolom site_id &#183; hypertable per waktu<br>retensi + compression",
         stroke="#94A3B8", size=12.5)
img("timescale.svg", 1758, 590, 22, 22)
img("postgresql.svg", 1786, 588, 26, 26)
web = box(1860, 580, 260, 140,
          "<b>Nginx :443</b> + Frontend (React)<br>dashboard multi-pabrik<br>"
          "proxy /api &amp; /ws &#8594; FastAPI<br>TLS: <i>tailscale cert</i>",
          stroke="#94A3B8", size=12.5)
img("react.svg", 2058, 590, 24, 24)
img("nginx.svg", 2088, 590, 24, 24)
edge(rc, api, color=EVENT, exit_=(1, .3), entry=(0, .3), label="consume")
edge(api, pg, color=EVENT, exit_=(0, .85), entry=(1, .5), pts=[(1840, 510.5), (1840, 650)],
     start=True)
text("INSERT /<br>SELECT", 1822, 560, 60, 30, size=9.5, color=EVENT, align="center",
     extra="labelBackgroundColor=#FFFFFF;")
edge(api, web, color=EVENT, exit_=(.5, 1), entry=(.5, 0), label="/api &#183; /ws")

# schema
sch = box(1550, 750, 570, 300, stroke="#94A3B8", fill="#F8FAFC")
text("Skema data &#183; PostgreSQL", 1562, 758, 400, 20, size=13, color=INK, bold=True)
TABLES = [
    ("site", "id<br>nama<br>lokasi<br>edge_host"),
    ("camera", "id<br>site_id<br>rtsp_path<br>zona<br>status"),
    ("event", "ts<br>site_id<br>cam_id<br>track_id<br>class, conf<br>bbox<br>event_type"),
    ("alert", "event_id<br>status<br>user<br>catatan<br>ack_at"),
]
for i, (name, cols) in enumerate(TABLES):
    x = 1562 + i * 140
    chip(f"<b>{name}</b>", x, 788, 128, 26, fill="#DBE4F3", color=NET, size=12)
    box(x, 818, 128, 150, cols, stroke="#CBD5E1", size=12, pad=8,
        extra="fontFamily=Courier New;")
chip("hypertable", 1856, 942, 100, 20, fill="#FEF3C7", color="#92400E")
text("Satu baris event &#177; ratusan byte. <b>track</b> (bbox per frame) tidak disimpan, "
     "hanya diteruskan ke WebSocket. Video tidak masuk database.",
     1562, 980, 548, 50, size=12, color=MUTE)
edge(pg, sch, color="#94A3B8", width=1.5, exit_=(.5, 1), entry=(fy(1685, 1550, 570), 0),
     dashed=True, arrow=False)

box(1550, 1080, 275, 100, "<b>Notifikasi</b> <font color='#9CA3AF'>(opsional)</font><br>"
    "WhatsApp / email / webhook<br>dipicu event kritis", stroke="#9CA3AF", dashed=True,
    size=12.5)
img("whatsapp.svg", 1790, 1090, 24, 24)
box(1845, 1080, 275, 100, "<b>Monitoring</b> <font color='#9CA3AF'>(opsional)</font><br>"
    "Prometheus + Grafana<br>health edge &#183; antrean RabbitMQ", stroke="#9CA3AF",
    dashed=True, size=12.5)
img("prometheus.svg", 2056, 1090, 24, 24)
img("grafana.svg", 2086, 1090, 24, 24)

# ============================================================== user =======
usr = box(2190, 420, 290, 470, stroke="#94A3B8", sw=1.5)
img("laptop.svg", 2232, 438, 96, 61)
img("smartphone.svg", 2342, 444, 46, 46)
text("Laptop / HP user", 2190, 506, 290, 20, size=14, color=INK, align="center", bold=True)
text("Tailscale client &#183; login SSO &#183; group:viewer", 2190, 528, 290, 18, size=11.5,
     color=MUTE, align="center")
# browser mock
box(2205, 558, 260, 222, stroke="#CBD5E1", arc=6)
box(2205, 558, 260, 20, "&#9679; &#9679; &#9679;&#160;&#160; dashboard multi-pabrik",
    stroke="#CBD5E1", fill="#E5E7EB", size=9, color=MUTE, valign="middle", pad=6, arc=6)
chip("Pabrik A", 2213, 586, 62, 18, fill=EVENT, color="#FFFFFF", size=9.5, bold=True)
chip("Pabrik B", 2281, 586, 62, 18, size=9.5)
box(2213, 610, 244, 162, stroke="none", fill="#1F2937", arc=4)
chip("LIVE &#183; a_cam01", 2219, 616, 84, 16, fill=RED, color="#FFFFFF", size=8.5, bold=True)
box(2262, 662, 50, 98, stroke="#22C55E", fill="none", sw=2, arc=2)
chip("id 17 &#183; helm &#10003;", 2252, 644, 72, 15, fill="#22C55E", color="#FFFFFF", size=8)
box(2362, 672, 46, 88, stroke="#EF4444", fill="none", sw=2, arc=2)
chip("id 23 &#183; tanpa helm", 2340, 654, 90, 15, fill="#EF4444", color="#FFFFFF", size=8)
text(f"<b><font color='{VIDEO}'>Video</font></b> &#8592; langsung dari edge "
     "(WebRTC/WHEP)<br>"
     f"<b><font color='{EVENT}'>Kotak &amp; label</font></b> &#8592; track/event via WSS dari "
     "pusat, digambar di atas video (canvas)<br>"
     "Dashboard tetap jalan walau video tidak dibuka.", 2204, 788, 266, 96, size=12)
edge(web, usr, color=EVENT, exit_=(1, .5), entry=(0, fy(650, 420, 470)))
text("HTTPS<br>+ WSS", 2142, 618, 46, 28, size=9.5, color=EVENT, align="center",
     bold=True)

# ======================================================== WAN flows =========
# event / metadata (blue, continuous) into central RabbitMQ
edge(TS_A, rc, color=EVENT, width=2.5, exit_=(1, fy(602.5, 270, 415)),
     entry=(0, fy(430, 400, 130)), pts=[(1470, 602.5), (1470, 430)])
edge(TS_B, rc, color=EVENT, width=2.5, exit_=(1, fy(1212.5, 880, 415)),
     entry=(0, fy(490, 400, 130)), pts=[(1486, 1212.5), (1486, 490)])
chip("event A &#183; AMQP :5672 &#183; terus", 1286, 593, 164, 20, fill="#FFFFFF",
     color=EVENT, stroke=EVENT, size=10, bold=True)
chip("event B &#183; AMQP :5672 &#183; terus", 1286, 1203, 164, 20, fill="#FFFFFF",
     color=EVENT, stroke=EVENT, size=10, bold=True)

# live video (purple dashed, on demand) straight from each edge to the user
edge(TS_A, usr, color=VIDEO, width=2.5, dashed=True, exit_=(1, fy(670, 270, 415)),
     entry=(fy(2300, 2190, 290), 0), pts=[(1262, 670), (1262, 180), (2300, 180)])
edge(TS_B, usr, color=VIDEO, width=2.5, dashed=True, exit_=(1, fy(1280, 880, 415)),
     entry=(fy(2300, 2190, 290), 1), pts=[(1262, 1280), (1262, 1432), (2300, 1432)])
chip("video live A &#183; WebRTC/WHEP &#8594; edge-pabrik-a:8889 &#183; hanya saat ditonton",
     1560, 170, 420, 20, fill="#FFFFFF", color=VIDEO, stroke=VIDEO, size=10.5, bold=True)
chip("video live B &#183; WebRTC/WHEP &#8594; edge-pabrik-b:8889 &#183; hanya saat ditonton",
     1560, 1422, 420, 20, fill="#FFFFFF", color=VIDEO, stroke=VIDEO, size=10.5, bold=True)

# ============================================================== footer =====
FY = 1478
box(20, FY, 740, 166, stroke=LINE)
text("Keterangan", 34, FY + 10, 200, 20, size=13, color=INK, bold=True)
LEG = [
    (dict(color=CABLE, arrow=False), "kabel fisik (LAN / PoE)"),
    (dict(color=RTSP), "RTSP / proses lokal di edge"),
    (dict(color=EVENT, width=2.5), "event / metadata (terus-menerus)"),
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

box(780, FY, 1720, 166, stroke=LINE)
text("<b>Jika WAN putus:</b> CV Worker tetap jalan dan rekaman tetap di disk edge; "
     "<i>event</i> ditahan di RabbitMQ lokal (queue durable, dibatasi ukuran disk) lalu "
     "dikirim ulang otomatis oleh shovel saat tersambung. <i>track</i> lama dibuang (TTL), "
     "karena hanya berguna untuk overlay live.<br>"
     "<b>Port:</b> RTSP 8554 dan AMQP 5672 hanya lokal di edge; WHEP 8889 + UDP 8189 hanya "
     "untuk group:viewer; 443 di pusat. Tidak ada port yang dibuka ke internet, semua lewat "
     "Tailscale.<br>"
     "<b>Bandwidth WAN:</b> metadata &#177; puluhan kbps per kamera (tergantung fps dan "
     "jumlah objek); video hanya saat ditonton, &#177; 0,5&#8211;2 Mbps per sub-stream per "
     "viewer. Angka ini perkiraan, ukur di lokasi.<br>"
     "<b>Overlay:</b> track membawa ts + bbox; browser menggambar kotak di atas video WebRTC "
     "dan menyelaraskan lewat ts. Penamaan stream: &lt;site&gt;_camNN (main) dan "
     "&lt;site&gt;_camNN_sub (untuk AI dan viewer).<br>"
     "<b>Keamanan:</b> kamera di VLAN sendiri dan hanya bisa dibaca edge node; user hanya "
     "melihat pabrik sesuai haknya (ACL Tailscale + role di FastAPI).",
     796, FY + 12, 1690, 124, size=13)
text("Logo &amp; ikon: Iconify (logos, Simple Icons CC0, MDI, Material Symbols), draw.io "
     "clip art (Apache 2.0), MediaMTX (bluenviron). Logo adalah merek dagang pemiliknya.",
     796, FY + 144, 1690, 16, size=10.5, color="#9CA3AF")

# ================================================================ write ====
xml = (
    '<mxfile host="app.diagrams.net" agent="tools/build_multisite_diagram.py" '
    'version="24.7.17" type="device">\n'
    '  <diagram id="multi-pabrik" name="Multi-Pabrik + Tailscale">\n'
    f'    <mxGraphModel dx="{W}" dy="{H}" grid="0" gridSize="10" guides="1" tooltips="1" '
    f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" '
    f'pageHeight="{H}" math="0" shadow="0" background="#FFFFFF">\n'
    '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
    + "\n".join("        " + c for c in CELLS)
    + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"
)
OUT.write_text(xml)
print(f"wrote {OUT} ({len(xml) // 1024} KB, {len(CELLS)} cells)")
