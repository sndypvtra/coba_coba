"""The look and the chart helpers of the Factory Vision mockups.

Taken unchanged from the warehouse mockup (projects/07_warehouse_live_ops/mockup/build.py) so the two decks
read as one product family; only the font path, the figure format and the status names differ.
"""

from __future__ import annotations

import math

# ------------------------------------------------------------------ the look
CSS = """
@font-face{font-family:Inter;src:url(../assets/fonts/Inter-Regular.ttf);font-weight:400}
@font-face{font-family:Inter;src:url(../assets/fonts/Inter-Medium.ttf);font-weight:500}
@font-face{font-family:Inter;src:url(../assets/fonts/Inter-SemiBold.ttf);font-weight:600}
@font-face{font-family:Inter;src:url(../assets/fonts/Inter-Bold.ttf);font-weight:700}
@font-face{font-family:MSL;src:url(../fonts/MaterialSymbolsRounded-Line.ttf)}
@font-face{font-family:MSF;src:url(../fonts/MaterialSymbolsRounded-Fill.ttf)}
:root{
 --bg:#f3f5f8;--surface:#fff;--surface-2:#f8fafc;--border:#e3e8ef;--border-2:#d3dae4;--hair:#eef1f5;
 --text:#0f172a;--text-2:#475569;--text-3:#8391a5;
 --brand:#2563eb;--brand-2:#1d4ed8;--brand-50:#eff5ff;
 --nav:#0b1220;--nav-text:#c5cfdd;--nav-muted:#5f6f86;--nav-on:rgba(59,130,246,.16);--nav-accent:#3b82f6;--nav-icon:#60a5fa;
 --gridc:#e9edf2;--axisc:#c9d1dc;
 --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#4a3aa7;--s8:#e34948;
 --crit:#d03b3b;--warn:#fab219;--good:#0ca30c;--neutral:#94a3b8;
 --up:#067647;--down:#b42318;
 --tile:#0b1220;
}
body.dk{
 --bg:#0a0e13;--surface:#111820;--surface-2:#18212c;--border:#232f3d;--border-2:#2c3a4b;--hair:#1a2430;
 --text:#e9eef4;--text-2:#9ba9b8;--text-3:#657485;
 --gridc:#1d2833;--axisc:#33414f;
 --s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;
 --up:#0ca30c;--down:#f87171;--neutral:#5b6b7d;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1920px;height:1080px;overflow:hidden}
body{font-family:Inter,sans-serif;font-size:14px;line-height:1.4;color:var(--text);background:var(--bg);-webkit-font-smoothing:antialiased;position:relative}
b{font-weight:600}
.i{font-family:MSL;font-weight:400;font-style:normal;font-size:20px;line-height:1;display:inline-block;white-space:nowrap;direction:ltr;font-feature-settings:'liga';-webkit-font-smoothing:antialiased;vertical-align:middle;flex:none}
.i.f{font-family:MSF}
.tn{font-variant-numeric:tabular-nums}
.mut{color:var(--text-3)} .sec{color:var(--text-2)}
.row{display:flex;align-items:center;gap:10px}
.col{display:flex;flex-direction:column}
.grow{flex:1;min-width:0}
.ell{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.wm{position:absolute;right:20px;bottom:7px;font-size:11px;color:var(--text-3);letter-spacing:.01em}

/* --- app shell --- */
.app{display:grid;grid-template-columns:248px 1fr;height:1080px}
.side{background:var(--nav);color:var(--nav-text);display:flex;flex-direction:column;padding:16px 12px 14px}
.brand{display:flex;align-items:center;gap:11px;padding:2px 8px 10px}
.logo{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);display:grid;place-items:center;color:#fff;flex:none}
.brand b{color:#fff;font-size:15px;display:block;line-height:1.2}
.brand small{color:var(--nav-muted);font-size:12px}
.ng{margin-top:16px}
.ng .t{font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--nav-muted);padding:0 10px 6px;font-weight:600}
.ni{display:flex;align-items:center;gap:11px;height:36px;padding:0 10px;border-radius:8px;font-size:13.5px;font-weight:500;position:relative;color:var(--nav-text)}
.ni .i{font-size:19px;color:#7d8da5}
.ni.on{background:var(--nav-on);color:#fff}
.ni.on .i{color:var(--nav-icon)}
.ni.on:before{content:"";position:absolute;left:-12px;top:8px;bottom:8px;width:3px;border-radius:0 3px 3px 0;background:var(--nav-accent)}
.ni .nb{margin-left:auto;background:#dc2626;color:#fff;font-size:11px;font-weight:600;border-radius:10px;padding:1px 7px;line-height:16px}
.ni .ext{margin-left:auto;font-size:16px}
.sfoot{margin-top:auto;border-top:1px solid #1b2537;padding:14px 6px 0;display:flex;gap:10px;align-items:center}
.sfoot b{color:#fff;font-size:13px;display:block}
.side.sa{background:#120c22}
.side.sa .logo{background:linear-gradient(135deg,#8b5cf6,#6d28d9)}
.side.sa{--nav-on:rgba(139,92,246,.2);--nav-accent:#8b5cf6;--nav-icon:#c4b5fd}
.main{display:flex;flex-direction:column;min-width:0;height:1080px}
.top{height:64px;background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:14px;padding:0 28px;flex:none}
.sel{display:flex;align-items:center;gap:10px;border:1px solid var(--border);border-radius:9px;height:42px;padding:0 10px 0 12px}
.sel b{display:block;font-size:13.5px;line-height:1.15}
.sel small{display:block;font-size:11.5px;color:var(--text-3);line-height:1.15}
.search{width:540px;display:flex;align-items:center;gap:10px;background:var(--surface-2);border:1px solid var(--border);border-radius:10px;height:42px;padding:0 12px;color:var(--text-3);font-size:13.5px}
.kbd{margin-left:auto;white-space:nowrap;font-size:11px;border:1px solid var(--border-2);border-radius:5px;padding:1px 6px;color:var(--text-3);background:var(--surface)}
.top .right{margin-left:auto;display:flex;align-items:center;gap:10px}
.chip{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 11px;border-radius:15px;background:var(--surface-2);border:1px solid var(--border);font-size:12.5px;font-weight:500;color:var(--text-2);white-space:nowrap}
.chip.ok{background:#ecfdf3;border-color:#c6f0d6;color:#067647}
.chip.sa{background:#f3efff;border-color:#e2d9ff;color:#5b21b6;font-weight:700;letter-spacing:.04em}
.dot{width:8px;height:8px;border-radius:50%;background:currentColor;display:inline-block;flex:none}
.iconbtn{width:38px;height:38px;border-radius:9px;display:grid;place-items:center;color:var(--text-2);position:relative}
.iconbtn .nd{position:absolute;top:8px;right:9px;width:9px;height:9px;border-radius:50%;background:#dc2626;border:2px solid var(--surface)}
.av{border-radius:50%;display:inline-grid;place-items:center;color:#fff;font-weight:600;flex:none;letter-spacing:.02em}
.content{padding:22px 28px 30px;flex:1;min-height:0;display:flex;flex-direction:column;gap:18px}
.ph{display:flex;align-items:flex-end;gap:16px;flex:none}
.ph h1{font-size:24px;font-weight:600;letter-spacing:-.015em;line-height:1.2}
.ph p{color:var(--text-2);margin-top:5px;font-size:14px}
.ph .acts{margin-left:auto;display:flex;gap:10px;align-items:center}
.crumb{font-size:13px;color:var(--text-3);margin-bottom:6px;display:flex;align-items:center;gap:4px}
.btn{height:38px;padding:0 14px;border-radius:9px;border:1px solid var(--border-2);background:var(--surface);display:inline-flex;align-items:center;gap:8px;font-weight:500;font-size:13.5px;color:var(--text);white-space:nowrap}
.btn .i{font-size:18px}
.btn.sm{height:30px;padding:0 10px;font-size:12.5px;border-radius:8px}
.btn.sm .i{font-size:16px}
.btn.pri{background:var(--brand);border-color:var(--brand);color:#fff}
.btn.vio{background:#6d28d9;border-color:#6d28d9;color:#fff}
.btn.red{background:#dc2626;border-color:#dc2626;color:#fff}
.btn.danger{color:#b42318;border-color:#fecdca;background:#fff5f4}
.btn.ghost{border-color:transparent;background:transparent;color:var(--text-2)}
.lnk{color:var(--brand);font-weight:500;font-size:13px;display:inline-flex;align-items:center;gap:2px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:0 1px 2px rgba(16,24,40,.04);min-width:0;min-height:0;display:flex;flex-direction:column}
.ch{display:flex;align-items:center;gap:10px;padding:15px 18px 0;flex:none}
.ch h3{font-size:15px;font-weight:600;white-space:nowrap}
.ch .sub{color:var(--text-3);font-size:12.5px}
.ch .r{margin-left:auto;color:var(--text-3);font-size:12.5px;display:flex;align-items:center;gap:10px}
.ch>.i{color:var(--text-3);font-size:19px}
.cb{padding:14px 18px 16px;min-height:0}
.it{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;flex:none}
.it.red{background:#fef2f2;color:#dc2626}.it.amber{background:#fffaeb;color:#d97706}.it.blue{background:#eff5ff;color:#2563eb}
.it.green{background:#ecfdf3;color:#079455}.it.violet{background:#f4f0ff;color:#6d28d9}.it.slate{background:#f1f5f9;color:#475569}
.it.cyan{background:#ecfeff;color:#0e7490}
.kpi{padding:14px 18px;gap:6px}
.kpi .kl{display:flex;align-items:center;gap:10px;color:var(--text-2);font-weight:500;font-size:13px}
.kpi .v{font-size:30px;font-weight:600;letter-spacing:-.02em;line-height:1.05;display:flex;align-items:baseline;gap:8px}
.kpi .v small{font-size:15px;color:var(--text-3);font-weight:500;letter-spacing:0}
.kpi .s{color:var(--text-3);font-size:12.5px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.up{color:var(--up);font-weight:600;display:inline-flex;align-items:center}
.down{color:var(--down);font-weight:600;display:inline-flex;align-items:center}
.up .i,.down .i{font-size:16px}
.bd{display:inline-flex;align-items:center;gap:4px;height:22px;padding:0 8px;border-radius:6px;font-size:12px;font-weight:600;white-space:nowrap;flex:none}
.bd .i{font-size:15px}
.bd.red{background:#fef2f2;color:#b42318}.bd.amber{background:#fffaeb;color:#b54708}.bd.blue{background:#eff5ff;color:#1d4ed8}
.bd.slate{background:#f1f5f9;color:#475569}.bd.green{background:#ecfdf3;color:#067647}.bd.violet{background:#f4f0ff;color:#5b21b6}
.bd.poc{background:#0f172a;color:#fff;height:20px;font-size:10.5px;letter-spacing:.04em;padding:0 7px}
.st{display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:500;white-space:nowrap}
.st .dot{width:7px;height:7px}
.cam{display:inline-flex;align-items:center;gap:4px;height:22px;padding:0 7px;border-radius:6px;background:#f1f5f9;color:#334155;font-size:11.5px;font-weight:600;white-space:nowrap;flex:none}
.cam .i{font-size:14px}
.tbl{width:100%;border-collapse:collapse}
.tbl th{text-align:left;font-size:12px;font-weight:600;color:var(--text-3);padding:9px 12px;border-bottom:1px solid var(--border);background:var(--surface-2);white-space:nowrap}
.tbl td{padding:9px 12px;border-bottom:1px solid var(--hair);vertical-align:middle;font-size:13.5px}
.tbl tr.on td{background:#f5f9ff}
.tbl.cp td{padding-top:6px;padding-bottom:6px}
.tbl.cp th{padding-top:7px;padding-bottom:7px}
.tbl tr:last-child td{border-bottom:none}
.thumb{border-radius:6px;object-fit:cover;display:block;background:#0b1220;flex:none}
.tg{width:36px;height:20px;border-radius:10px;background:#cbd5e1;position:relative;flex:none;display:inline-block}
.tg:after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.tg.on{background:var(--brand)}.tg.on:after{left:18px}
.tg.v.on{background:#6d28d9}
.seg{display:inline-flex;background:#e9edf2;border-radius:9px;padding:3px;gap:2px}
.seg>span{height:32px;padding:0 12px;border-radius:7px;font-size:13px;font-weight:500;color:var(--text-2);display:inline-flex;align-items:center;gap:6px}
.seg>span.on{background:var(--surface);color:var(--text);box-shadow:0 1px 2px rgba(16,24,40,.1)}
.seg .i{font-size:18px}
.tabs{display:flex;gap:24px;border-bottom:1px solid var(--border);padding:0 18px;flex:none}
.tabs>span{padding:12px 2px 11px;font-weight:500;color:var(--text-2);display:inline-flex;gap:7px;align-items:center;font-size:13.5px}
.tabs>span.on{color:var(--brand);box-shadow:inset 0 -2px 0 var(--brand)}
.tabs .n{background:#eef1f5;color:var(--text-2);border-radius:10px;padding:0 7px;font-size:12px;line-height:18px}
.tabs span.on .n{background:var(--brand-50);color:var(--brand)}
.flt{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 10px 0 12px;border:1px solid var(--border-2);border-radius:8px;font-size:13px;color:var(--text-2);background:var(--surface);white-space:nowrap}
.flt b{color:var(--text);font-weight:500}
.flt .i{font-size:17px;color:var(--text-3)}
.inp{display:flex;align-items:center;gap:8px;height:32px;padding:0 10px;border:1px solid var(--border-2);border-radius:8px;color:var(--text-3);font-size:13px;background:var(--surface)}
.kv{display:grid;grid-template-columns:150px 1fr;row-gap:11px;column-gap:12px;font-size:13.5px;align-items:center}
.kv>span:nth-child(odd){color:var(--text-3)}
.lg{display:flex;gap:16px;font-size:12px;color:var(--text-2);align-items:center;flex-wrap:wrap}
.lg span{display:inline-flex;align-items:center;gap:6px}
.sw{width:10px;height:10px;border-radius:3px;display:inline-block;flex:none}
.swl{width:16px;height:0;border-top:2px solid;display:inline-block;flex:none}
.swd{width:16px;height:0;border-top:2px dashed;display:inline-block;flex:none}
.hb{display:grid;grid-template-columns:var(--lw,170px) 1fr 64px;align-items:center;column-gap:12px;height:31px;font-size:13px}
.hb .hl{color:var(--text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hb .ht{height:100%;display:flex;align-items:center}
.hb .ht i{height:12px;border-radius:0 4px 4px 0;display:block}
.hb .hv{text-align:right;font-weight:600}
.chart{position:relative}
.chart svg{display:block;overflow:visible}
.chart text{font-family:Inter}
.ax{font-size:11px;fill:var(--text-3);font-variant-numeric:tabular-nums}
.gl{stroke:var(--gridc);stroke-width:1;shape-rendering:crispEdges}
.bl{stroke:var(--axisc);stroke-width:1;shape-rendering:crispEdges}
.tip{position:absolute;background:var(--surface);border:1px solid var(--border);border-radius:9px;box-shadow:0 8px 24px rgba(15,23,42,.16);padding:9px 11px;font-size:12px;min-width:150px;z-index:3;pointer-events:none}
.tip b{display:block;font-size:12.5px;margin-bottom:4px}
.tip div{display:flex;align-items:center;gap:7px;color:var(--text-2);line-height:1.6}
.tip div em{margin-left:auto;font-style:normal;color:var(--text);font-weight:600;padding-left:12px}
.tile{position:relative;border-radius:8px;overflow:hidden;background:#000}
.tile img{width:100%;height:100%;object-fit:cover;display:block}
.tl{position:absolute;left:8px;top:8px;display:flex;align-items:center;gap:6px;background:rgba(10,14,19,.8);color:#e9eef4;font-size:11.5px;font-weight:600;padding:3px 8px;border-radius:6px;white-space:nowrap;max-width:calc(100% - 96px);overflow:hidden}
.tr{position:absolute;right:8px;top:8px;display:flex;align-items:center;gap:5px;background:rgba(10,14,19,.8);color:#e9eef4;font-size:11.5px;font-weight:500;padding:3px 8px;border-radius:6px}
.tr .i,.tl .i{font-size:15px}
.ev{display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--hair)}
.ev:last-child{border-bottom:none}
.ev .t1{font-weight:600;font-size:13.5px;display:flex;align-items:center;gap:7px}
.ev .t2{color:var(--text-3);font-size:12.5px;margin-top:2px}
.prog{height:6px;border-radius:3px;background:#e9edf2;overflow:hidden}
.prog i{display:block;height:100%;border-radius:3px}
.chk{display:flex;align-items:flex-start;gap:10px;padding:8px 0;font-size:13.5px}
.chk .i{font-size:20px}
.sect{font-size:11.5px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-3);margin:4px 0 8px}

/* --- dark dashboard --- */
.dtop{height:56px;display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid var(--border);background:#0a0e13}
.dlogo{width:32px;height:32px;border-radius:9px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);display:grid;place-items:center}
.dname{font-size:17px;font-weight:600}
.dcr{color:var(--text-2);font-size:15px}
.dcr.on{color:var(--text);font-weight:600}
.dtop .right{margin-left:auto;display:flex;gap:8px;align-items:center}
.dchip{height:30px;padding:0 11px;border-radius:15px;background:var(--surface-2);color:var(--text-2);font-size:12.5px;display:inline-flex;align-items:center;gap:6px;font-weight:500}
.dchip.live{background:rgba(34,197,94,.14);color:#4ade80;font-weight:700;letter-spacing:.04em}
.dchip.clock{color:var(--text);font-size:15px;font-weight:600}
.dtabs{height:50px;display:flex;align-items:center;gap:6px;padding:0 16px;border-bottom:1px solid var(--border)}
.dtabs>span{height:34px;padding:0 13px;border-radius:8px;display:inline-flex;align-items:center;gap:7px;color:var(--text-2);font-weight:500;font-size:13.5px}
.dtabs>span.on{background:var(--surface-2);color:var(--text);box-shadow:inset 0 -2px 0 #3b82f6}
.dtabs>span .i{font-size:18px}
.dtabs .rot{margin-left:auto;color:var(--text-3);font-size:12.5px;gap:10px}
.dbody{padding:16px;display:flex;flex-direction:column;gap:12px;height:974px}
body.dk .card{box-shadow:none;border-radius:12px}
body.dk .it.red{background:rgba(239,68,68,.15);color:#f87171}body.dk .it.amber{background:rgba(245,158,11,.15);color:#fbbf24}
body.dk .it.blue{background:rgba(59,130,246,.16);color:#60a5fa}body.dk .it.green{background:rgba(34,197,94,.14);color:#4ade80}
body.dk .it.violet{background:rgba(139,92,246,.16);color:#a78bfa}body.dk .it.cyan{background:rgba(34,211,238,.13);color:#22d3ee}
body.dk .it.slate{background:rgba(148,163,184,.13);color:#94a3b8}
body.dk .bd.red{background:rgba(239,68,68,.16);color:#fca5a5}body.dk .bd.amber{background:rgba(245,158,11,.16);color:#fcd34d}
body.dk .bd.blue{background:rgba(59,130,246,.18);color:#93c5fd}body.dk .bd.green{background:rgba(34,197,94,.15);color:#86efac}
body.dk .bd.slate{background:rgba(148,163,184,.14);color:#cbd5e1}
body.dk .cam{background:#1d2733;color:#cbd5e1}
body.dk .tg{background:#334155}
body.dk .tip{box-shadow:0 8px 24px rgba(0,0,0,.5)}
body.dk .tbl th{background:transparent}
body.dk .prog{background:#1d2733}
.dk .kpi .v{font-size:30px}

/* --- slides --- */
.slide{padding:44px 64px 34px;height:1080px;display:flex;flex-direction:column;gap:20px;background:#fff}
.eyebrow{font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand)}
.slide h1{font-size:36px;font-weight:700;letter-spacing:-.02em;line-height:1.15;margin-top:8px}
.slide .lead{font-size:17px;color:var(--text-2);margin-top:8px;max-width:1500px}
.shead{display:flex;align-items:flex-start;gap:20px}
.shead .brandmini{margin-left:auto;display:flex;align-items:center;gap:10px;font-weight:600;color:var(--text-2)}

/* --- phones --- */
.phone{width:376px;height:792px;border-radius:56px;background:#0b0f17;padding:12px;box-shadow:0 40px 80px rgba(15,23,42,.28),0 0 0 2px #2b3445 inset;flex:none}
.screen{width:100%;height:100%;border-radius:45px;overflow:hidden;background:#f3f5f8;position:relative;display:flex;flex-direction:column}
.notch{position:absolute;top:11px;left:50%;transform:translateX(-50%);width:112px;height:32px;border-radius:17px;background:#0b0f17;z-index:5}
.sbar{height:52px;display:flex;align-items:flex-end;justify-content:space-between;padding:0 30px 8px;font-weight:600;font-size:14.5px;flex:none}
"""


# ------------------------------------------------------------------ small parts
USED: dict[bool, set] = {False: set(), True: set()}


def I(name: str, fill: bool = False, size: int | None = None, color: str | None = None) -> str:
    USED[fill].add(name)
    st = ";".join(s for s in (f"font-size:{size}px" if size else "", f"color:{color}" if color else "") if s)
    return f'<span class="i{" f" if fill else ""}"{f" style={chr(34)}{st}{chr(34)}" if st else ""}>{name}</span>'


def num(v: float, dec: int = 0) -> str:
    """Figures with a thousands comma and a decimal point: 1,284 and 0.19."""
    return f"{v:,.{dec}f}"


AV_COLOURS = ["#2563eb", "#0e7490", "#7c3aed", "#be185d", "#c2410c", "#15803d", "#475569", "#a16207"]


def avatar(name: str, size: int = 32) -> str:
    ini = "".join(w[0] for w in name.split()[:2]).upper()
    col = AV_COLOURS[sum(map(ord, name)) % len(AV_COLOURS)]
    return f'<span class="av" style="width:{size}px;height:{size}px;background:{col};font-size:{size * 0.38:.0f}px">{ini}</span>'


SEV = {"high": ("red", "High", "error"), "medium": ("amber", "Medium", "warning"),
       "low": ("blue", "Low", "info"), "info": ("slate", "Info", "info")}


def sev(s: str) -> str:
    tone, label, icon = SEV[s]
    return f'<span class="bd {tone}">{I(icon, True)}{label}</span>'


def bd(text: str, tone: str = "slate", icon: str | None = None) -> str:
    return f'<span class="bd {tone}">{I(icon, True) if icon else ""}{text}</span>'


STATUS = {"New": "#2563eb", "In progress": "#d97706", "Closed": "#079455", "False alarm": "#94a3b8",
          "Online": "#079455", "Offline": "#dc2626", "Updating": "#2563eb", "Active": "#079455",
          "Released": "#079455", "On hold": "#d97706", "Re-sort": "#dc2626", "Mixed Color": "#7c3aed", "Running": "#079455",
          "Check": "#d97706", "Draft": "#94a3b8", "Pass": "#079455", "Reject": "#dc2626", "Rework": "#d97706"}


def status(text: str, colour: str | None = None) -> str:
    return f'<span class="st"><span class="dot" style="color:{colour or STATUS.get(text, "#94a3b8")}"></span>{text}</span>'


def cam(label: str) -> str:
    return f'<span class="cam">{I("videocam", True)}{label}</span>'


def poc() -> str:
    return '<span class="bd poc">PoC</span>'


def tg(on: bool = True, v: bool = False) -> str:
    return f'<span class="tg{" on" if on else ""}{" v" if v else ""}"></span>'


def card(title: str, body: str, *, icon: str | None = None, sub: str = "", right: str = "", style: str = "",
         cb_style: str = "", cls: str = "") -> str:
    head = ""
    if title:
        head = (f'<div class="ch">{I(icon) if icon else ""}<h3>{title}</h3>'
                f'{f"<span class={chr(34)}sub{chr(34)}>{sub}</span>" if sub else ""}'
                f'{f"<div class={chr(34)}r{chr(34)}>{right}</div>" if right else ""}</div>')
    return f'<section class="card {cls}" style="{style}">{head}<div class="cb" style="{cb_style}">{body}</div></section>'


def kpi(icon: str, tone: str, label: str, value: str, sub: str = "", extra: str = "") -> str:
    return (f'<section class="card kpi"><div class="kl"><span class="it {tone}">{I(icon, True, 19)}</span>{label}</div>'
            f'<div class="v tn">{value}</div><div class="s">{sub}</div>{extra}</section>')


def up(text: str, good: bool = True, arrow: str = "up") -> str:
    icon = "arrow_upward" if arrow == "up" else "arrow_downward"
    return f'<span class="{"up" if good else "down"}">{I(icon, size=15)}{text}</span>'


def img(src: str, w: int | str, h: int | str, style: str = "", cls: str = "thumb") -> str:
    ws = f"{w}px" if isinstance(w, int) else w
    hs = f"{h}px" if isinstance(h, int) else h
    return f'<img class="{cls}" src="{src}" style="width:{ws};height:{hs};{style}">'


def tile(src: str, label: str, colour: str = "#3b82f6", right: str = "", style: str = "", extra: str = "") -> str:
    return (f'<div class="tile" style="{style}"><img src="{src}">'
            f'<span class="tl"><span class="dot" style="color:{colour}"></span>{label}</span>'
            f'{f"<span class={chr(34)}tr{chr(34)}>{right}</span>" if right else ""}{extra}</div>')


def legend(items: list[tuple]) -> str:
    out = []
    for it in items:
        name, colour = it[0], it[1]
        kind = it[2] if len(it) > 2 else "sw"
        if kind == "sw":
            out.append(f'<span><i class="sw" style="background:{colour}"></i>{name}</span>')
        else:
            out.append(f'<span><i class="{kind}" style="border-color:{colour}"></i>{name}</span>')
    return f'<div class="lg">{"".join(out)}</div>'


# ------------------------------------------------------------------ charts (SVG, after the dataviz rules)
def nice(v: float) -> float:
    if v <= 0:
        return 1
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * e + 1e-9:
            return m * e
    return 10 * e


def bar_d(x: float, base: float, w: float, h: float, r: float = 4) -> str:
    """A bar standing on the baseline, its data end rounded."""
    if h <= 0.5:
        return ""
    r = min(r, h, w / 2)
    t = base - h
    return (f"M{x:.1f},{base:.1f}V{t + r:.1f}Q{x:.1f},{t:.1f} {x + r:.1f},{t:.1f}H{x + w - r:.1f}"
            f"Q{x + w:.1f},{t:.1f} {x + w:.1f},{t + r:.1f}V{base:.1f}Z")


def _axes(w, h, L, R, T, B, lo, hi, ticks, fmt) -> list[str]:
    out = []
    ph = h - T - B
    for k in range(ticks + 1):
        y = T + ph - ph * k / ticks
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}" class="{"bl" if k == 0 else "gl"}"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" class="ax" text-anchor="end">{fmt(lo + (hi - lo) * k / ticks)}</text>')
    return out


def tooltip(x: float, y: float, title: str, rows: list[tuple]) -> str:
    body = "".join(f'<div><i class="sw" style="background:{c}"></i>{n}<em>{v}</em></div>' for n, c, v in rows)
    return f'<div class="tip" style="left:{x:.0f}px;top:{y:.0f}px"><b>{title}</b>{body}</div>'


def vbars(series: list[tuple], labels: list[str], w: int, h: int, *, ymax: float | None = None, ticks: int = 4,
          fmt=None, every: int = 1, stacked: bool = False, avg: tuple | None = None, tip: tuple | None = None,
          L: int = 36, B: int = 26, bw_max: float = 24) -> str:
    """Bars per label; several series side by side or stacked (2px surface gap), one axis.

    `avg` = (name, values): a dashed reference line on the same axis.
    `tip` = (index, x offset, y): a hover card shown for one label, as on screen.
    """
    fmt = fmt or (lambda v: num(v))
    R, T = 8, 10
    n = len(labels)
    tot = [sum(s[1][i] for s in series) if stacked else max(s[1][i] for s in series) for i in range(n)]
    ymax = ymax or nice(max(tot + (list(avg[1]) if avg else [])))
    pw, ph = w - L - R, h - T - B
    slot = pw / n
    groups = 1 if stacked else len(series)
    gap = 3 if groups > 1 else 0
    bw = min(bw_max, (slot * 0.66 - gap * (groups - 1)) / groups)
    base = T + ph
    out = _axes(w, h, L, R, T, B, 0, ymax, ticks, fmt)
    if tip is not None:
        cx = L + slot * (tip[0] + .5)
        out.append(f'<rect x="{cx - slot / 2:.1f}" y="{T}" width="{slot:.1f}" height="{ph}" style="fill:var(--text);opacity:.05"/>')
    for i in range(n):
        cx = L + slot * (i + .5)
        if stacked:
            y = base
            segs = [(s[2], s[1][i]) for s in series if s[1][i] > 0]
            for k, (col, v) in enumerate(segs):
                hh = ph * v / ymax
                last = k == len(segs) - 1
                if last:
                    d = bar_d(cx - bw / 2, y, bw, hh)
                else:
                    hseg = max(hh - 2, 0)
                    d = f"M{cx - bw / 2:.1f},{y:.1f}V{y - hseg:.1f}H{cx + bw / 2:.1f}V{y:.1f}Z" if hseg > 0 else ""
                if d:
                    out.append(f'<path d="{d}" style="fill:{col}"/>')
                y -= hh
        else:
            total = groups * bw + gap * (groups - 1)
            for g, s in enumerate(series):
                x = cx - total / 2 + g * (bw + gap)
                d = bar_d(x, base, bw, ph * s[1][i] / ymax)
                if d:
                    out.append(f'<path d="{d}" style="fill:{s[2]}"/>')
        if i % every == 0:
            out.append(f'<text x="{cx:.1f}" y="{h - 8}" class="ax" text-anchor="middle">{labels[i]}</text>')
    if avg:
        pts = " ".join(f"{L + slot * (i + .5):.1f},{base - ph * v / ymax:.1f}" for i, v in enumerate(avg[1]))
        out.append(f'<polyline points="{pts}" fill="none" style="stroke:var(--text-2)" stroke-width="2" '
                   f'stroke-dasharray="5 4" stroke-linejoin="round"/>')
    tip_html = ""
    if tip is not None:
        i, dx, ty = tip[:3]
        cx = L + slot * (i + .5)
        rows = [(s[0], s[2], fmt(s[1][i])) for s in series] + ([(avg[0], "var(--text-2)", fmt(avg[1][i]))] if avg else [])
        tip_html = tooltip(cx + dx, ty, tip[3] if len(tip) > 3 else labels[i], rows)
    return f'<div class="chart" style="width:{w}px;height:{h}px"><svg width="{w}" height="{h}">{"".join(out)}</svg>{tip_html}</div>'


def lines(series: list[tuple], labels: list[str], w: int, h: int, *, lo: float = 0, hi: float | None = None,
          ticks: int = 4, fmt=None, every: int = 1, ref: tuple | None = None, area: bool = False,
          tip: tuple | None = None, L: int = 36, B: int = 26, R: int = 10, end_labels: bool = False) -> str:
    """Lines (2px) on one axis; `ref` = (label, value) a dashed target; `tip` = (index, x offset, y, title)."""
    fmt = fmt or (lambda v: num(v))
    T = 10
    n = len(labels)
    hi = hi or nice(max(max(s[1]) for s in series))
    pw, ph = w - L - R, h - T - B
    X = lambda i: L + pw * i / (n - 1)  # noqa: E731
    Y = lambda v: T + ph - ph * (v - lo) / (hi - lo)  # noqa: E731
    out = _axes(w, h, L, R, T, B, lo, hi, ticks, fmt)
    for i in range(0, n, every):
        out.append(f'<text x="{X(i):.1f}" y="{h - 8}" class="ax" text-anchor="middle">{labels[i]}</text>')
    if ref:
        y = Y(ref[1])
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}" style="stroke:var(--text-2)" stroke-width="1.5" stroke-dasharray="5 4"/>')
        out.append(f'<text x="{w - R}" y="{y - 6:.1f}" class="ax" text-anchor="end" style="fill:var(--text-2)">{ref[0]}</text>')
    if tip is not None:
        x = X(tip[0])
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{T + ph}" style="stroke:var(--text-3)" stroke-width="1"/>')
    for s in series:
        name, vals, col = s[0], s[1], s[2]
        dashed = len(s) > 3 and s[3]
        pts = [(X(i), Y(v)) for i, v in enumerate(vals) if v is not None]
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        if area and not dashed:
            out.append(f'<polygon points="{pts[0][0]:.1f},{T + ph} {p} {pts[-1][0]:.1f},{T + ph}" style="fill:{col};opacity:.10"/>')
        out.append(f'<polyline points="{p}" fill="none" style="stroke:{col}" stroke-width="2" stroke-linejoin="round" '
                   f'stroke-linecap="round"{" stroke-dasharray=" + chr(34) + "5 4" + chr(34) if dashed else ""}/>')
        if tip is not None and tip[0] < len(vals) and vals[tip[0]] is not None:
            out.append(f'<circle cx="{X(tip[0]):.1f}" cy="{Y(vals[tip[0]]):.1f}" r="4.5" style="fill:{col};stroke:var(--surface)" stroke-width="2"/>')
        if end_labels:
            x, y = pts[-1]
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" style="fill:{col};stroke:var(--surface)" stroke-width="2"/>')
            out.append(f'<text x="{x + 9:.1f}" y="{y + 4:.1f}" style="fill:var(--text-2);font-size:11.5px;font-weight:500">{name}</text>')
    tip_html = ""
    if tip is not None:
        i, dx, ty, title = tip
        rows = [(s[0], s[2], fmt(s[1][i])) for s in series if s[1][i] is not None]
        tip_html = tooltip(X(i) + dx, ty, title, rows)
    return f'<div class="chart" style="width:{w}px;height:{h}px"><svg width="{w}" height="{h}">{"".join(out)}</svg>{tip_html}</div>'


def hbars(items: list[tuple], *, colour: str = "var(--s1)", vmax: float | None = None, fmt=None,
          label_w: int = 170) -> str:
    """Horizontal bars, one hue (magnitude), values written at the end in text ink."""
    fmt = fmt or (lambda v: num(v))
    vmax = vmax or max(v for _, v, *_ in items)
    rows = []
    for label, v, *rest in items:
        col = rest[0] if rest else colour
        rows.append(f'<div class="hb" style="--lw:{label_w}px"><span class="hl">{label}</span>'
                    f'<span class="ht"><i style="width:{100 * v / vmax:.1f}%;background:{col}"></i></span>'
                    f'<span class="hv tn">{fmt(v)}</span></div>')
    return "".join(rows)


RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf",
        "#1c5cab", "#184f95", "#104281", "#0d366b"]


def heatgrid(m: list[list[float]], xl: list[str], yl: list[str], w: int, h: int, *, every: int = 1,
             empty: str = "var(--hair)") -> str:
    """Rows x columns of cells, one hue light to dark; zero is the empty surface."""
    L, B = 40, 22
    rows, cols = len(m), len(m[0])
    cw, chh = (w - L) / cols, (h - B) / rows
    vmax = max(max(r) for r in m)
    out = []
    for r in range(rows):
        out.append(f'<text x="{L - 8}" y="{r * chh + chh / 2 + 4:.1f}" class="ax" text-anchor="end">{yl[r]}</text>')
        for c in range(cols):
            v = m[r][c]
            col = empty if v <= 0 else RAMP[min(len(RAMP) - 1, int(round(v / vmax * (len(RAMP) - 1))))]
            out.append(f'<rect x="{L + c * cw + 1:.1f}" y="{r * chh + 1:.1f}" width="{cw - 2:.1f}" height="{chh - 2:.1f}" rx="3" style="fill:{col}"/>')
    for c in range(0, cols, every):
        out.append(f'<text x="{L + c * cw + cw / 2:.1f}" y="{h - 6}" class="ax" text-anchor="middle">{xl[c]}</text>')
    return f'<div class="chart" style="width:{w}px;height:{h}px"><svg width="{w}" height="{h}">{"".join(out)}</svg></div>'


def ramp_legend(lo: str, hi: str) -> str:
    sw = "".join(f'<i style="display:inline-block;width:14px;height:10px;background:{c}"></i>' for c in RAMP[::2])
    return f'<div class="lg"><span>{lo}</span><span style="gap:0">{sw}</span><span>{hi}</span></div>'


def spark(vals: list[float], w: int = 120, h: int = 34, colour: str = "var(--s1)") -> str:
    lo, hi = min(vals), max(vals)
    pts = " ".join(f"{w * i / (len(vals) - 1):.1f},{h - 3 - (h - 6) * (v - lo) / max(hi - lo, 1e-9):.1f}"
                   for i, v in enumerate(vals))
    return (f'<svg width="{w}" height="{h}" style="display:block;overflow:visible"><polyline points="{pts}" fill="none" '
            f'style="stroke:{colour}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>')


