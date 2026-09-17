#!/usr/bin/env python3
"""Build architecture.drawio from flow_process.md, with the hardware icons
fetched from the internet and embedded in the file.

WARNING: this OVERWRITES ../architecture.drawio. That file is meant to be
edited in draw.io from here on; if it has been edited by hand, re-running this
script throws those edits away. Change the layout here, or there, not both.

Icons come from the Iconify API (api.iconify.design), which serves the
open-source icon sets:

  mdi              Material Design Icons    Apache-2.0
  material-symbols Google Material Symbols  Apache-2.0
  carbon           IBM Carbon               Apache-2.0
  logos            brand marks              owned by each vendor, used as marks

They are base64-embedded rather than hot-linked, so the diagram renders with no
outbound network - see the warning in flow_process.md section 3.
"""

import base64
import html
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "architecture.drawio"
CACHE = Path(__file__).with_name("iconcache")
CACHE.mkdir(exist_ok=True)

# ---------------------------------------------------------------- palette ---
INK      = "#1F2430"   # headings
BODY     = "#3A414B"   # node labels
MUTE     = "#8A8F96"   # notes
FAINT    = "#9AA3AC"   # optional nodes
LINE     = "#7A8590"   # cabling
RULE     = "#D5D5CE"
FIELD    = "#5A6570"   # capture tier
ACCENT   = "#C2410C"   # edge compute - the hero
ACCENT_L = "#FCF2E8"
LIVE     = "#2E7D5B"   # the live-view link
LIVE_L   = "#EFF7F2"
NET      = "#2D6DB4"   # network + data flow
DB       = "#2B5F8A"   # database - the second hero
DB_L     = "#EAF2F9"
RED      = "#C0392B"   # site boundary
BAND     = "#F1F1EC"
PAPER    = "#FFFFFF"


def icon(name: str, color: str | None = None) -> str:
    """Fetch one icon and return it as a draw.io-safe data URI.

    draw.io parses `style` on `;`, so the usual `data:image/svg+xml;base64,`
    form would split the style in two. draw.io's own embedded images use
    `data:image/svg+xml,<base64>` instead, and that is what is written here.
    """
    prefix, short = name.split(":")
    key = f"{prefix}__{short}" + (f"__{color[1:]}" if color else "") + ".svg"
    path = CACHE / key
    if not path.exists():
        url = f"https://api.iconify.design/{prefix}/{short}.svg"
        if color:
            url += "?color=" + urllib.parse.quote(color)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        blob = urllib.request.urlopen(req, timeout=40).read()
        if b"<svg" not in blob:
            raise SystemExit(f"{name}: not an svg ({blob[:80]!r})")
        path.write_bytes(blob)
    return "data:image/svg+xml," + base64.b64encode(path.read_bytes()).decode()


CELLS: list[str] = []


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def cell(cid, value, style, x, y, w, h, parent="1"):
    CELLS.append(
        f'        <mxCell id="{cid}" value="{esc(value)}" style="{style}" '
        f'vertex="1" parent="{parent}">\n'
        f'          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />\n'
        f"        </mxCell>"
    )


def text(cid, value, x, y, w, h, size=11, color=BODY, align="center",
         bold=False, italic=False, spacing=0):
    style = (f"text;html=1;align={align};verticalAlign=middle;fontSize={size};"
             f"fontColor={color};")
    if bold:
        style += "fontStyle=1;"
    if italic:
        style += "fontStyle=2;"
    if spacing:
        style += f"letterSpacing={spacing};"
    cell(cid, value, style, x, y, w, h)


def image(cid, label, name, x, y, w, h=None, color=None, font=12, bold=True,
          fontcolor=BODY):
    h = w if h is None else h
    style = (f"shape=image;html=1;imageAspect=1;aspect=fixed;"
             f"verticalLabelPosition=bottom;verticalAlign=top;labelPosition=center;"
             f"align=center;labelBackgroundColor=none;fontSize={font};"
             f"fontColor={fontcolor};"
             + ("fontStyle=1;" if bold else "")
             + f"image={icon(name, color)};")
    cell(cid, label, style, x, y, w, h)


def box(cid, x, y, w, h, stroke=RULE, fill=PAPER, width=1, dashed=False):
    style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};"
             f"strokeColor={stroke};strokeWidth={width};arcSize=6;")
    if dashed:
        style += "dashed=1;dashPattern=6 4;"
    cell(cid, "", style, x, y, w, h)


def chip(cid, value, x, y, w, h, fill, stroke, color, size=10, bold=True):
    style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};"
             f"strokeColor={stroke};fontSize={size};fontColor={color};arcSize=40;")
    if bold:
        style += "fontStyle=1;"
    cell(cid, value, style, x, y, w, h)


def edge(cid, source, target, *, color=LINE, width=2, arrow=False, dashed=False,
         exit_xy=(1, 0.5), entry_xy=(0, 0.5), style_extra=""):
    ex, ey = exit_xy
    nx, ny = entry_xy
    style = ("edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=8;html=1;jettySize=auto;"
             f"strokeColor={color};strokeWidth={width};"
             f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;"
             f"entryX={nx};entryY={ny};entryDx=0;entryDy=0;"
             + ("endArrow=block;endFill=1;" if arrow else "endArrow=none;startArrow=none;")
             + ("dashed=1;dashPattern=6 4;" if dashed else "")
             + style_extra)
    CELLS.append(
        f'        <mxCell id="{cid}" style="{style}" edge="1" parent="1" '
        f'source="{source}" target="{target}">\n'
        f'          <mxGeometry relative="1" as="geometry" />\n'
        f"        </mxCell>"
    )


def free_edge(cid, x1, y1, x2, y2, *, color=LINE, width=2, arrow=False,
              dashed=False):
    style = (f"html=1;strokeColor={color};strokeWidth={width};"
             + ("endArrow=block;endFill=1;endSize=6;" if arrow
                else "endArrow=none;startArrow=none;")
             + ("dashed=1;dashPattern=6 4;" if dashed else ""))
    CELLS.append(
        f'        <mxCell id="{cid}" style="{style}" edge="1" parent="1">\n'
        f'          <mxGeometry relative="1" as="geometry">\n'
        f'            <mxPoint x="{x1}" y="{y1}" as="sourcePoint" />\n'
        f'            <mxPoint x="{x2}" y="{y2}" as="targetPoint" />\n'
        f"          </mxGeometry>\n"
        f"        </mxCell>"
    )


def edge_label(cid, parent, value, color=BODY, bg=BAND, dy=0, pos=0.0, bold=False):
    style = (f"edgeLabel;html=1;align=center;verticalAlign=middle;fontSize=10;"
             f"fontColor={color};labelBackgroundColor={bg};")
    if bold:
        style += "fontStyle=1;"
    CELLS.append(
        f'        <mxCell id="{cid}" value="{esc(value)}" style="{style}" '
        f'vertex="1" connectable="0" parent="{parent}">\n'
        f'          <mxGeometry x="{pos}" y="{dy}" relative="1" as="geometry">\n'
        f'            <mxPoint as="offset" />\n'
        f"          </mxGeometry>\n"
        f"        </mxCell>"
    )


# =============================================================== title =====
text("title", "Video Analytics Platform &#8212; End-to-End Architecture",
     36, 22, 900, 34, size=25, color=INK, align="left", bold=True)
text("subtitle",
     "Fixed cameras in &#183; a GPU does the seeing &#183; PostgreSQL holds the answers "
     "&#183; <b>pixels stay on site, numbers travel</b>",
     36, 56, 1000, 20, size=13, color="#5A6570", align="left")
cell("titlerule", "", f"line;strokeWidth=1;html=1;strokeColor={RULE};",
     36, 80, 1528, 8)

# ====================================================== build / offline ====
box("buildbox", 346, 96, 328, 86, stroke="#B9B9AF", fill="#FAFAF7", dashed=True)
text("buildlbl", "BUILD &#183; OFFLINE &#183; NOT ON SITE", 358, 100, 200, 14,
     size=9, color=MUTE, align="left", bold=True, spacing=1)
image("nvlogo", "", "logos:nvidia", 596, 99, 68, 17, font=1, bold=False)
text("buildchain",
     "model &#8594; ONNX &#8594; <b>trtexec</b> FP16/INT8 &#8594; calibrate &#8594; <b>.engine</b>",
     354, 120, 312, 18, size=10, color=BODY)
text("buildnote",
     "one GPU, one precision, one input size &#8212;<br>a model update is a release, not a config edit",
     354, 140, 312, 30, size=9, color=MUTE)

# ============================================================== bands ======
BAND_Y, BAND_H = 214, 380
bands = [
    ("b1", 36, 164, "CAPTURE", MUTE),
    ("b2", 214, 452, "EDGE &#183; COMPUTE", ACCENT),
    ("b3", 712, 300, "NETWORK", MUTE),
    ("b4", 1028, 310, "CORE &#183; BACKEND", MUTE),
    ("b5", 1354, 210, "PEOPLE", MUTE),
]
for bid, bx, bw, label, color in bands:
    fill = ACCENT_L if bid == "b2" else BAND
    cell(bid, "", f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};"
                  f"strokeColor=none;arcSize=4;", bx, BAND_Y, bw, BAND_H)
    text(bid + "t", label, bx, BAND_Y - 20, bw, 16,
         size=10, color=color, align="left", bold=True, spacing=2)

# ============================================================ capture ======
image("cam1", "IP Camera 01", "mdi:cctv", 84, 250, 68, color=FIELD, font=11)
image("cam2", "IP Camera 02 &#8230; N", "mdi:cctv", 84, 392, 68, color=FIELD, font=11)
text("camnote",
     "PoE &#183; H.264/H.265 &#183; ONVIF<br>fixed position, calibrated once",
     44, 492, 148, 32, size=9, color=MUTE)

# =============================================================== edge ======
cell("sw", "PoE Switch<br><font style='font-size:9px' color='#8A8F96'>"
           "1 GbE &#183; 802.3af/at</font>",
     "shape=image;html=1;imageAspect=1;aspect=fixed;verticalLabelPosition=top;"
     "verticalAlign=bottom;labelPosition=center;align=center;"
     "labelBackgroundColor=none;fontSize=11;fontStyle=1;fontColor=" + BODY + ";"
     "image=" + icon("mdi:switch", FIELD) + ";", 250, 300, 64, 64)

box("nvr", 222, 410, 120, 112, stroke="#C9CDD2", fill=PAPER, dashed=True)
image("nvricon", "", "mdi:nas", 256, 420, 52, color=FAINT, font=1, bold=False)
text("nvrlbl", "NVR", 226, 476, 112, 16, size=11, color=FAINT, bold=True)
text("nvrnote", "existing recorder,<br>left untouched", 226, 492, 112, 24,
     size=9, color=FAINT)

box("gpu", 384, 248, 252, 168, stroke=ACCENT, fill=PAPER, width=2)
image("gpuicon", "", "mdi:server", 478, 256, 60, color=ACCENT, font=1, bold=False)
text("gpulbl", "AI Inference Server", 392, 320, 236, 20, size=15, color=INK, bold=True)
text("gpusub", "GPU &#183; sized to the camera count", 392, 340, 236, 14,
     size=9, color=MUTE)
chip("trtchip", "TensorRT &#183; FP16 / INT8", 434, 358, 152, 24,
     ACCENT_L, "#E8C9AE", ACCENT, size=11)
text("gpunote", "decode &#183; infer &#183; track &#183; logic, in one box",
     392, 386, 236, 14, size=9, color=MUTE)

image("mon", "", "mdi:monitor", 472, 452, 72, color=LIVE, font=1, bold=False)
text("monlbl", "Live View", 400, 528, 216, 18, size=12, color=INK, bold=True)
text("monnote",
     "annotated video on a monitor in the room<br>"
     "<b>lowest latency &#183; no encoder in the path</b>",
     344, 550, 332, 28, size=9, color=LIVE)

# ====================================================== site boundary ======
free_edge("boundary", 688, 192, 688, 606, color=RED, width=2, dashed=True)
text("boundarylbl", "SITE BOUNDARY", 698, 170, 150, 16,
     size=10, color=RED, align="left", bold=True, spacing=1)
box("noframes", 634, 452, 108, 78, stroke=RED, width=2)
image("noframesicon", "", "mdi:cctv-off", 668, 460, 40, color=RED, font=1, bold=False)
text("noframeslbl", "NO FRAMES<br>CROSS HERE", 638, 500, 100, 26,
     size=10, color=RED, bold=True)

# ============================================================ network ======
image("fw", "Router + Firewall", "material-symbols:router", 754, 300, 64,
      color=NET, font=11)
image("fwbadge", "", "carbon:firewall", 812, 296, 26, color=RED, font=1, bold=False)
text("fwnote", "outbound TLS only<br>no inbound port opened", 724, 388, 124, 26,
     size=9, color=MUTE)
image("net", "Internet / VPN", "mdi:cloud", 902, 298, 68, color=NET, font=11)
text("netnote", "a few kB of events<br>per camera per hour", 876, 390, 120, 26,
     size=9, color=MUTE)

# ============================================================= legend ======
box("legend", 752, 428, 248, 156, stroke="#E0E0DA", fill=PAPER)
text("legendlbl", "HOW TO READ THIS DIAGRAM", 764, 436, 224, 14,
     size=9, color=MUTE, align="left", bold=True, spacing=1)
legend_rows = [
    ("lg1", 464, LINE,     2, False, False, "physical cabling &#183; no arrowhead", BODY),
    ("lg2", 488, LIVE,     3, False, False, "HDMI / DP &#183; live annotated video", LIVE),
    ("lg3", 512, NET,      2, True,  False, "data flow &#183; events and queries", NET),
    ("lg4", 536, "#B9B9AF", 2, True, True,  "built offline, deployed once", MUTE),
    ("lg5", 560, RED,      2, False, True,  "site boundary &#183; frames stop here", RED),
]
for lid, ly, lcolor, lw, larrow, ldash, ltext, tcolor in legend_rows:
    free_edge(lid, 766, ly, 810, ly, color=lcolor, width=lw, arrow=larrow,
              dashed=ldash)
    text(lid + "t", ltext, 818, ly - 8, 176, 16, size=9, color=tcolor,
         align="left")

# =============================================================== core ======
image("api", "API Server", "mdi:server-network", 1052, 301, 62, color=NET, font=11)
text("apinote", "ingest &#183; auth &#183; retention", 1024, 387, 118, 14,
     size=9, color=MUTE)

box("pgbox", 1156, 248, 160, 168, stroke=DB, fill=PAPER, width=2)
image("pgicon", "", "logos:postgresql", 1208, 258, 56, font=1, bold=False)
text("pglbl", "PostgreSQL", 1162, 320, 148, 18, size=14, color=INK, bold=True)
text("pgsub", "+ TimescaleDB hypertable", 1162, 338, 148, 14, size=9, color=MUTE)
chip("pgchip", "camera &#183; observation<br>subject &#183; event",
     1174, 356, 124, 28, DB_L, "#BBD3E6", DB, size=9)
text("pgnote", "megabytes per camera per day,<br>against gigabytes as video",
     1162, 386, 148, 24, size=9, color=MUTE)

# ============================================================= people ======
image("dash", "Dashboard", "logos:grafana", 1398, 301, 62, font=11)
text("dashnote", "BI / Grafana &#183; the numbers, charted", 1362, 387, 194, 14,
     size=9, color=MUTE)
image("alert", "Alerts", "mdi:bell-ring", 1408, 452, 48, color=FIELD, font=11)
text("alertnote", "email &#183; webhook &#183; chat", 1362, 524, 194, 14,
     size=9, color=MUTE)

# ============================================== cabling - no arrowheads ====
edge("e1", "cam1", "sw")
edge_label("e1l", "e1", "LAN &#183; PoE", color="#5A6570", bg=BAND, pos=-0.35)
edge("e2", "cam2", "sw")
edge("e3", "sw", "gpu")
edge_label("e3l", "e3", "RTSP &#183; 1 GbE", color="#5A6570", bg=ACCENT_L, dy=-12)
edge("e12", "sw", "nvr", color="#C9CDD2", width=1,
     exit_xy=(0.5, 1), entry_xy=(0.5, 0))

edge("e4", "gpu", "mon", color=LIVE, width=3,
     exit_xy=(0.5, 1), entry_xy=(0.5, 0))
edge_label("e4l", "e4", "HDMI / DP &#183; live annotated video",
           color=LIVE, bg=ACCENT_L, bold=True)

edge("e5", "gpu", "fw")
edge_label("e5l", "e5", "events only", color="#5A6570", bg=ACCENT_L,
           dy=-12, pos=-0.5)
edge("e6", "fw", "net")

# ============================================ data flow - with arrowheads ==
edge("e7", "net", "api", color=NET, arrow=True)
edge_label("e7l", "e7", "JSON events", color=NET, bg=BAND, dy=11)
edge("e8", "api", "pgbox", color=NET, arrow=True)
edge_label("e8l", "e8", "INSERT", color=NET, bg=BAND, dy=11)
edge("e9", "pgbox", "dash", color=NET, arrow=True)
edge_label("e9l", "e9", "SQL", color=NET, bg=BAND, dy=11)
edge("e10", "pgbox", "alert", color=NET, arrow=True,
     exit_xy=(0.5, 1), entry_xy=(0, 0.5))
edge_label("e10l", "e10", "threshold", color=NET, bg=BAND)

edge("e11", "buildbox", "gpu", color="#B9B9AF", arrow=True, dashed=True,
     exit_xy=(0.5, 1), entry_xy=(0.5, 0))
edge_label("e11l", "e11", "deploy engine", color=MUTE, bg=PAPER)

# ====================================================== pipeline strip =====
text("striplbl", "INSIDE THE INFERENCE SERVER", 36, 616, 400, 16,
     size=10, color=MUTE, align="left", bold=True, spacing=2)
text("stripnote",
     "sample rate is a design lever, not a constant &#8212; halving it roughly doubles "
     "the cameras one GPU serves, and makes tracking harder",
     460, 616, 1104, 16, size=10, color=MUTE, align="right", italic=True)

stages = [
    ("p1", "DECODE",   "H.264/H.265 &#8594; frames,<br>hardware decoder", "video decoder", False),
    ("p2", "SAMPLE",   "drop to the rate the<br>task actually needs",     "CPU",           False),
    ("p3", "INFER",    "the detector, as a<br>TensorRT engine",           "GPU",           "accent"),
    ("p4", "TRACK",    "one identity per object<br>across frames",        "CPU",           False),
    ("p5", "LOGIC",    "zones, dwell, counting<br>&#8212; the domain part", "CPU",         False),
    ("p6", "ANNOTATE", "boxes drawn for<br>the live view",                "GPU &#8594; HDMI", "live"),
    ("p7", "EVENTS",   "structured records,<br>queued for upload",        "CPU",           False),
]
SX, SW, SGAP = 36, 202, 18
for i, (pid, head, mid, foot, flavour) in enumerate(stages):
    if flavour == "accent":
        fill, stroke, head_c, mid_c, foot_c, sw_ = ACCENT_L, ACCENT, ACCENT, "#B07A55", ACCENT, 2
    elif flavour == "live":
        fill, stroke, head_c, mid_c, foot_c, sw_ = LIVE_L, LIVE, LIVE, "#5D8F76", LIVE, 2
    else:
        fill, stroke, head_c, mid_c, foot_c, sw_ = PAPER, RULE, INK, MUTE, "#5A6570", 1
    value = (f'<b><font color="{head_c}">{head}</font></b><br>'
             f'<font color="{mid_c}">{mid}</font><br>'
             f'<b><font color="{foot_c}">{foot}</font></b>')
    cell(pid, value,
         f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
         f"strokeWidth={sw_};fontSize=10;align=center;spacing=4;arcSize=8;",
         SX + i * (SW + SGAP), 638, SW, 76)
    if i:
        edge(f"pa{i}", stages[i - 1][0], pid, color="#B9B9AF", arrow=True)

# ============================================================= footer ======
cell("footrule", "", f"line;strokeWidth=1;html=1;strokeColor={RULE};",
     36, 730, 1528, 8)
text("foot1",
     "<b>Sizing</b>&#160;&#160;1&#8211;4 cameras: embedded GPU module, fanless &#183; "
     "4&#8211;16: small-form-factor x86 + one workstation GPU &#183; 16+: 1U/2U rack server. "
     "The board is a procurement decision, not an architecture one.",
     36, 744, 1528, 16, size=10, color="#5A6570", align="left")
text("foot2",
     "<b>Watching it live</b>&#160;&#160;three ways, not alternatives &#8212; "
     f'<font color="{LIVE}"><b>A</b> direct HDMI, tens of ms, nearly free</font> &#183; '
     "<b>B</b> re-stream RTSP/WebRTC, 0.2&#8211;2 s, costs one encode per stream &#8212; budget for it &#183; "
     "<b>C</b> dashboard, numbers only. A and B stay inside the boundary; only C crosses it.",
     36, 762, 1528, 16, size=10, color="#5A6570", align="left")
text("foot3",
     "<b>Read the limits</b>&#160;&#160;counting is a detection result and duration is a tracking result &#8212; "
     "they are not equally reliable, and a quality score rides with every subject. "
     "Interpolated frames are stored apart from observed ones. No faces, no re-identification across sites. "
     "Calibration belongs to one camera position.",
     36, 780, 1528, 16, size=10, color=MUTE, align="left")
text("foot4",
     "Throughput figures belong on a benchmark, not on an architecture diagram: an engine is built for one GPU, "
     "one precision and one input size, and <i>trtexec</i> on the target board is what gives the number.",
     36, 798, 1528, 14, size=9, color="#A0A5AC", align="left", italic=True)
text("credit",
     "Icons: Material Design Icons &#183; Google Material Symbols &#183; IBM Carbon (all Apache-2.0), "
     "served by api.iconify.design and embedded in this file. "
     "PostgreSQL, Grafana and NVIDIA marks belong to their owners.",
     36, 816, 1528, 14, size=9, color="#B4B8BE", align="left")

# =============================================================== write =====
XML = (
    '<mxfile host="app.diagrams.net" agent="built from flow_process.md" '
    'version="24.7.17" type="device">\n'
    '  <diagram id="cv-architecture" name="End-to-End Architecture">\n'
    '    <mxGraphModel dx="1600" dy="900" grid="0" gridSize="10" guides="1" '
    'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
    'pageWidth="1600" pageHeight="900" math="0" shadow="0">\n'
    "      <root>\n"
    '        <mxCell id="0" />\n'
    '        <mxCell id="1" parent="0" />\n'
    + "\n".join(CELLS)
    + "\n      </root>\n"
    "    </mxGraphModel>\n"
    "  </diagram>\n"
    "</mxfile>\n"
)
OUT.write_text(XML, encoding="utf-8")
print(f"wrote {OUT}  {len(XML)/1024:.0f} KB  cells={len(CELLS)}")
