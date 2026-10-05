#!/usr/bin/env python3
"""Mockup pages for the investor deck: the web app, the realtime dashboard, the platform console, the phone app.

Each page is plain HTML and CSS (html/NN_name.html) and is rendered to a 1920x1080 picture
(pages/NN_name.png) by headless Chromium. The camera pictures, floor plans, snapshots and
camera verdicts on the pages are the PoC's own outputs (assets.py, output/); the counts a
deployment would produce (incidents today, compliance this month, tenants, revenue) are
illustrative, and every page says so in its corner.

    python mockup/assets.py         # once: the pictures from the PoC (~3 min)
    python mockup/build.py          # every page (~1 min)
    python mockup/build.py 05 09    # some pages
    python mockup/build.py --icons  # refetch the icon subset after using a new icon (network)
"""

from __future__ import annotations

import glob
import json
import math
import os
import random
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import ops  # noqa: E402

HTML, PAGES, IMG, FONTS = HERE / "html", HERE / "pages", HERE / "img", HERE / "fonts"
META = json.loads((IMG / "meta.json").read_text())
GEO = json.loads((ROOT / "output" / "warehouse_000" / "geometry.json").read_text())

WM_POC = "Mockup konsep · angka ilustrasi · gambar kamera & peta: keluaran PoC pada rekaman NVIDIA PhysicalAI-SmartSpaces (CC BY 4.0)"
WM = "Mockup konsep · angka ilustrasi"

# ------------------------------------------------------------------ the look
CSS = """
@font-face{font-family:Inter;src:url(../../assets/fonts/Inter-Regular.ttf);font-weight:400}
@font-face{font-family:Inter;src:url(../../assets/fonts/Inter-Medium.ttf);font-weight:500}
@font-face{font-family:Inter;src:url(../../assets/fonts/Inter-SemiBold.ttf);font-weight:600}
@font-face{font-family:Inter;src:url(../../assets/fonts/Inter-Bold.ttf);font-weight:700}
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
    """Indonesian figures: 1.284 and 0,19."""
    return f"{v:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")


AV_COLOURS = ["#2563eb", "#0e7490", "#7c3aed", "#be185d", "#c2410c", "#15803d", "#475569", "#a16207"]


def avatar(name: str, size: int = 32) -> str:
    ini = "".join(w[0] for w in name.split()[:2]).upper()
    col = AV_COLOURS[sum(map(ord, name)) % len(AV_COLOURS)]
    return f'<span class="av" style="width:{size}px;height:{size}px;background:{col};font-size:{size * 0.38:.0f}px">{ini}</span>'


SEV = {"high": ("red", "Tinggi", "error"), "medium": ("amber", "Sedang", "warning"),
       "low": ("blue", "Rendah", "info"), "info": ("slate", "Info", "info")}
KIND_ICON = {k: v[1] for k, v in ops.KIND.items()}


def sev(s: str) -> str:
    tone, label, icon = SEV[s]
    return f'<span class="bd {tone}">{I(icon, True)}{label}</span>'


def bd(text: str, tone: str = "slate", icon: str | None = None) -> str:
    return f'<span class="bd {tone}">{I(icon, True) if icon else ""}{text}</span>'


STATUS = {"Baru": "#2563eb", "Ditangani": "#d97706", "Selesai": "#079455", "Alarm palsu": "#94a3b8",
          "Online": "#079455", "Offline": "#dc2626", "Memperbarui": "#2563eb", "Aktif": "#079455"}


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


# ------------------------------------------------------------------ shells
NAV_APP = [
    ("Pantau", [("dashboard", "Beranda", "beranda"), ("videocam", "Live Monitoring", "live"),
                ("map", "Peta Lantai", "peta"), ("space_dashboard", "Dashboard Realtime", "dash")]),
    ("Kejadian", [("notification_important", "Pusat Insiden", "insiden"), ("search", "Pencarian", "cari"),
                  ("description", "Laporan & Kepatuhan", "laporan")]),
    ("Konfigurasi", [("polyline", "Zona & Aturan", "zona"), ("photo_camera", "Kamera & Kalibrasi", "kamera"),
                     ("campaign", "Notifikasi & Eskalasi", "notif")]),
    ("Administrasi", [("group", "Pengguna & Peran", "pengguna"), ("hub", "Integrasi & API", "api"),
                      ("receipt_long", "Langganan & Tagihan", "tagihan")]),
]
NAV_SA = [
    ("Platform", [("insights", "Ringkasan", "ringkasan"), ("domain", "Tenant & Langganan", "tenant"),
                  ("toggle_on", "Paket & Fitur", "fitur"), ("payments", "Penagihan", "tagihan")]),
    ("Operasi", [("memory", "Edge & Model AI", "edge"), ("monitor_heart", "Kesehatan Platform", "sehat"),
                 ("crisis_alert", "Insiden Platform", "insplat")]),
    ("Dukungan", [("support_agent", "Tiket Dukungan", "tiket"), ("key", "Akses Darurat", "akses"),
                  ("history", "Log Audit Platform", "audit")]),
]


def sidebar(nav, active: str, user: tuple, sub: str, sa: bool = False) -> str:
    groups = []
    for title, items in nav:
        rows = []
        for icon, label, key in items:
            extra = ""
            if key == "insiden" and not sa:
                extra = '<span class="nb">7</span>'
            if key == "dash":
                extra = I("open_in_new", size=16).replace('class="i"', 'class="i ext"')
            if key == "tiket" and sa:
                extra = '<span class="nb" style="background:#7c3aed">4</span>'
            rows.append(f'<div class="ni{" on" if key == active else ""}">{I(icon, key == active)}{label}{extra}</div>')
        groups.append(f'<div class="ng"><div class="t">{title}</div>{"".join(rows)}</div>')
    name, role, tone = user
    return (f'<aside class="side{" sa" if sa else ""}"><div class="brand"><span class="logo">{I("warehouse", True, 21)}</span>'
            f'<div><b>Warehouse Live Ops</b><small>{sub}</small></div></div>{"".join(groups)}'
            f'<div class="sfoot">{avatar(name, 34)}<div class="grow"><b>{name}</b>{bd(role, tone)}</div>'
            f'{I("unfold_more", size=18, color="#5f6f86")}</div></aside>')


def topbar(search: str = "Cari kejadian, kamera, zona…  mis. “tanpa helm di area kerja timur kemarin”",
           site: tuple = ("Gudang Simulasi A", "PT Contoh Logistik"), sa: bool = False, clock: str = "10:43") -> str:
    left = (f'<span class="chip sa">{I("shield_person", True, 16)}SUPER ADMIN</span>' if sa else "")
    status = ('<span class="chip ok"><span class="dot"></span>61 edge online · 2 perlu dicek</span>' if sa else
              '<span class="chip ok"><span class="dot"></span>15 kamera aktif</span>'
              f'<span class="chip">{I("schedule", size=16)}Shift Pagi · 07–15 · {clock}</span>')
    who = "Tim Platform" if sa else "Rina Hartono"
    return (f'<header class="top">{left}<div class="sel">{I("domain" if sa else "warehouse", size=20, color="var(--text-2)")}'
            f'<div><b>{site[0]}</b><small>{site[1]}</small></div>{I("expand_more", size=18, color="var(--text-3)")}</div>'
            f'<div class="search">{I("search", size=19)}<span class="ell">{search}</span><span class="kbd">Ctrl K</span></div>'
            f'<div class="right">{status}<span class="iconbtn">{I("notifications")}<span class="nd"></span></span>'
            f'<span class="iconbtn">{I("help")}</span>{avatar(who, 34)}</div></header>')


def doc(body: str, cls: str = "", extra_css: str = "") -> str:
    return (f'<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Warehouse Live Ops · mockup</title>'
            f'<style>{CSS}{extra_css}</style></head><body class="{cls}">{body}</body></html>')


def app(active: str, body: str, *, wm: str = WM_POC, clock: str = "10:43", search: str | None = None) -> str:
    top = topbar(clock=clock) if search is None else topbar(search=search, clock=clock)
    return doc(f'<div class="app">{sidebar(NAV_APP, active, ("Rina Hartono", "Admin", "blue"), "Web App · Admin")}'
               f'<div class="main">{top}<main class="content">{body}</main></div></div><div class="wm">{wm}</div>')


def superadmin(active: str, body: str, *, wm: str = WM) -> str:
    return doc(f'<div class="app">{sidebar(NAV_SA, active, ("Tim Platform", "Super Admin", "violet"), "Konsol Platform", sa=True)}'
               f'<div class="main">{topbar("Cari tenant, lokasi, perangkat, invoice…", ("Semua tenant", "24 tenant · 61 lokasi"), sa=True)}'
               f'<main class="content">{body}</main></div></div><div class="wm">{wm}</div>')


DASH_TABS = [("space_dashboard", "Command Center"), ("center_focus_strong", "Fokus Kamera"),
             ("engineering", "Kepatuhan APD"), ("health_and_safety", "Analitik Keselamatan"),
             ("monitoring", "Analitik Operasional"), ("apartment", "Multi-lokasi")]


def dash(active: int, crumbs: tuple, body: str, *, wm: str = WM_POC) -> str:
    tabs = "".join(f'<span class="{"on" if k == active else ""}">{I(icon, k == active)}{name}</span>'
                   for k, (icon, name) in enumerate(DASH_TABS))
    top = (f'<header class="dtop"><span class="dlogo">{I("warehouse", True, 20, "#fff")}</span><b class="dname">Warehouse Live Ops</b>'
           f'<span class="dcr">/ {crumbs[0]}</span><span class="dcr on">/ {crumbs[1]}</span>'
           f'<div class="right"><span class="dchip live"><span class="dot"></span>LANGSUNG</span>'
           f'<span class="dchip">{I("schedule", size=16)}Shift Pagi · 07–15</span>'
           f'<span class="dchip clock tn">10:42:07</span></div></header>')
    nav = (f'<nav class="dtabs">{tabs}<span class="rot">{I("autorenew", size=17)}Rotasi otomatis tiap 30 dtk {tg(True)}</span></nav>')
    return doc(f'{top}{nav}<main class="dbody">{body}</main><div class="wm">{wm}</div>', cls="dk")


def slide(eyebrow: str, title: str, lead: str, body: str, *, wm: str = WM) -> str:
    head = (f'<div class="shead"><div><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p class="lead">{lead}</p></div>'
            f'<div class="brandmini"><span class="logo" style="width:32px;height:32px">{I("warehouse", True, 19)}</span>'
            f'Warehouse Live Ops</div></div>')
    return doc(f'<div class="slide">{head}{body}</div><div class="wm">{wm}</div>')


# ------------------------------------------------------------------ shared story
CAMNAME = dict(ops.CAMERA_NAME["warehouse_000"])
CAMNAME.update({"Camera_0002": "Rak barat", "Camera_0004": "Dok muat selatan", "Camera_0006": "Sudut barat daya, rak",
                "Camera_0009": "Lorong rak tengah", "Camera_0012": "Sudut barat daya, pintu",
                "Camera_0013": "Area barat laut", "Camera_0014": "Area tengah timur",
                "Camera_0016": "Lorong rak selatan", "Camera_0017": "Area barat laut, rak",
                "Camera_0019": "Area tengah selatan"})
CAM_RGB = {"Camera_0001": "#ef4444", "Camera_0003": "#3b82f6", "Camera_0005": "#fb923c", "Camera_0011": "#22c55e",
           "Camera_0007": "#a78bfa", "Camera_0015": "#22d3ee", "Camera_0010": "#facc15", "Camera_0008": "#f472b6",
           "Camera_0000": "#94a3b8"}


def ev1(k: int) -> dict:
    return META["events_v1"][k]


def ev2(k: int) -> dict:
    return META["events_v2"][k]


def snap(e: dict) -> str:
    return f"../img/{e['img']}"


# the incidents of the morning at Gudang Simulasi A, with the PoC's own snapshots
INCIDENTS = [
    # id, event, severity, title, detail, place, cams, time, ago, status, owner, sla
    ("0142", ev1(0), "high", "Nyaris tertabrak forklift", "P14 & forklift F12", "Lintasan forklift", ["CAM 0001"],
     "10:41:58", "1 mnt lalu", "Ditangani", "Budi Santoso", ("sisa 13 mnt", 0.13, "#dc2626")),
    ("0141", ev2(14), "medium", "Melawan arah di lorong satu arah", "P72", "Lorong satu arah", ["CAM 0003"],
     "10:38:20", "5 mnt lalu", "Baru", None, ("sisa 25 mnt", 0.17, "#d97706")),
    ("0140", ev2(12), "medium", "Tanpa helm & rompi", "P67", "Area kerja timur", ["CAM 0003"],
     "10:37:41", "5 mnt lalu", "Ditangani", "Agus Prasetyo", ("ditanggapi 2 mnt", 1, "#079455")),
    ("0139", ev1(1), "medium", "Pejalan kaki di jalur forklift", "P18", "Jalur forklift tengah", ["CAM 0005"],
     "10:31:05", "12 mnt lalu", "Ditangani", "Siti Rahma", ("ditanggapi 4 mnt", 1, "#079455")),
    ("0138", ev2(13), "medium", "Tanpa rompi", "P66", "Area kerja timur", ["CAM 0003"],
     "10:24:12", "19 mnt lalu", "Baru", "Agus Prasetyo", ("sisa 11 mnt", 0.63, "#d97706")),
    ("0137", ev2(7), "medium", "Tanpa helm", "P20", "Area kerja timur", ["CAM 0003"],
     "10:15:37", "27 mnt lalu", "Ditangani", "Agus Prasetyo", ("ditanggapi 6 mnt", 1, "#079455")),
    ("0136", ev1(4), "medium", "Pejalan kaki di jalur forklift", "P91", "Jalur forklift tengah", ["CAM 0005"],
     "10:02:51", "40 mnt lalu", "Ditangani", "Siti Rahma", ("ditanggapi 3 mnt", 1, "#079455")),
    ("0135", ev1(3), "info", "Diam lama di satu titik", "P22 · 24 dtk", "Sudut barat daya", ["CAM 0000"],
     "09:48:10", "55 mnt lalu", "Selesai", "Dimas Saputra", ("selesai", 1, "#079455")),
    ("0134", ev2(2), "medium", "Tanpa helm", "P2", "Area kerja timur", ["CAM 0003"],
     "09:47:30", "56 mnt lalu", "Alarm palsu", "Agus Prasetyo", ("ditinjau", 1, "#94a3b8")),
]


# ------------------------------------------------------------------ the product, module by module
WEB_APP = [
    ("dashboard", "Beranda", False, ["Ringkasan KPI per shift", "Insiden yang perlu tindakan", "Cuplikan kamera langsung", "Tren & titik rawan"]),
    ("videocam", "Live Monitoring", True, ["Video wall 1 / 4 / 9 / 1+5", "Overlay AI: kotak, ID, zona", "Sorotan kamera otomatis", "Peringatan langsung"]),
    ("map", "Peta Lantai Digital", True, ["Posisi orang & forklift (meter)", "Heatmap kepadatan", "Zona & garis hitung", "Putar ulang 3D"]),
    ("notification_important", "Pusat Insiden", False, ["Triase & penugasan", "Status & SLA", "Tandai alarm palsu", "Aksi massal"]),
    ("fact_check", "Detail Insiden & Bukti", False, ["Klip sebelum–sesudah", "Posisi di peta", "Tindakan korektif (CAPA)", "Ekspor bukti PDF"]),
    ("search", "Pencarian Kejadian", True, ["Tanya bahasa sehari-hari", "Filter otomatis", "Lompat ke rekaman", "Simpan jadi aturan"]),
    ("description", "Laporan & Kepatuhan K3", False, ["Laporan shift / minggu / bulan", "Kepatuhan APD", "Format SMK3 & ISO 45001", "Kirim terjadwal"]),
    ("polyline", "Zona & Aturan", False, ["Gambar zona & garis", "Aturan siap pakai", "Jadwal per shift", "Uji aturan di rekaman"]),
    ("photo_camera", "Kamera & Kalibrasi", True, ["Tambah RTSP / ONVIF", "Verifikasi posisi otomatis", "Kesehatan kamera", "Kalibrasi 4 titik"]),
    ("campaign", "Notifikasi & Eskalasi", False, ["WhatsApp, email, push", "Matriks eskalasi", "Webhook / sirene", "Ringkasan shift"]),
    ("group", "Pengguna & Peran", False, ["Undang & atur peran", "Akses per lokasi", "SSO & 2FA", "Log audit"]),
    ("hub", "Integrasi & Langganan", False, ["API & webhook", "Integrasi WMS / HRIS", "Langganan & tagihan", "Ekspor data"]),
]
DASHBOARD = [
    ("space_dashboard", "Command Center", True, ["KPI langsung", "Video wall + sorotan", "Peta lantai langsung", "Feed & lini masa"]),
    ("center_focus_strong", "Fokus Kamera / Zona", True, ["Satu kamera besar", "APD per orang", "Zona & garis hitung", "Posisi di denah"]),
    ("engineering", "Kepatuhan APD", True, ["Helm & rompi per orang", "Satu orang lintas kamera", "Status sistem", "Feed pelanggaran"]),
    ("health_and_safety", "Analitik Keselamatan", False, ["Near miss per jam", "Titik rawan", "Pelanggaran per jenis", "Waktu tanggap"]),
    ("monitoring", "Analitik Operasional", False, ["Utilisasi forklift", "Arus garis hitung", "Kepadatan zona", "Orang di lantai"]),
    ("apartment", "Multi-lokasi (HQ)", False, ["Skor per lokasi", "Peringkat & tren", "Insiden lintas lokasi", "Rotasi layar otomatis"]),
]
SUPER = [
    ("domain", "Tenant & Langganan", ["Klien, paket & kuota", "Status pilot", "Perpanjangan", "Kesehatan akun"]),
    ("toggle_on", "Paket & Fitur", ["Feature flag per tenant", "Add-on", "Batas pemakaian", "Uji beta terbatas"]),
    ("memory", "Edge & Model AI", ["Status edge box", "Rilis model bertahap", "Rollback", "Akurasi per lokasi"]),
    ("monitor_heart", "Kesehatan & Penagihan", ["Uptime & latensi", "Invoice & MRR", "Tunggakan", "Kuota penyimpanan"]),
    ("support_agent", "Dukungan & Audit", ["Tiket dukungan", "Masuk sebagai tenant (izin)", "Log audit platform", "Pengumuman"]),
]
MOBILE = ["Push alert dengan foto", "Tangani insiden di lantai", "Live kamera", "Ringkasan & serah terima shift"]
ROLES = [
    ("shield_person", "Super Admin", "violet", "Tim kita (vendor)", "Semua tenant · platform"),
    ("admin_panel_settings", "Admin", "blue", "Pemilik / manajer gudang, IT", "Semua lokasi milik tenant"),
    ("health_and_safety", "Supervisor K3", "green", "HSE / kepala shift", "Lokasi yang ditugaskan"),
    ("videocam", "Operator CCTV", "amber", "Ruang kontrol", "Lokasi yang ditugaskan"),
    ("visibility", "Viewer / Manajemen", "slate", "Direksi, auditor", "Hanya lihat"),
]


def counts() -> dict:
    return {"web_modules": len(WEB_APP), "web_features": sum(len(m[3]) for m in WEB_APP),
            "dash_views": len(DASHBOARD), "dash_widgets": sum(len(m[3]) for m in DASHBOARD),
            "super_modules": len(SUPER), "super_features": sum(len(m[2]) for m in SUPER),
            "mobile_features": len(MOBILE), "roles": len(ROLES)}


# ================================================================== pages
def p00_peta_produk() -> str:
    n = counts()
    total = n["web_features"] + n["dash_widgets"] + n["super_features"] + n["mobile_features"]

    def mod_list(mods, cols=1):
        rows = []
        for m in mods:
            icon, name, proven, feats = (m[0], m[1], m[2], m[3]) if len(m) == 4 else (m[0], m[1], False, m[2])
            rows.append(f'<div style="display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--hair)">'
                        f'{I(icon, False, 19, "var(--text-2)")}<div class="grow"><div class="row" style="gap:7px">'
                        f'<b style="font-size:13.5px">{name}</b>{poc() if proven else ""}</div>'
                        f'<div class="mut" style="font-size:12px;margin-top:2px;line-height:1.45">{" · ".join(feats)}</div></div></div>')
        return f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);column-gap:28px">{"".join(rows)}</div>'

    def surface(icon, tone, title, who, count, body, style=""):
        return (f'<section class="card" style="padding:16px 20px;{style}"><div class="row" style="gap:12px">'
                f'<span class="it {tone}" style="width:42px;height:42px">{I(icon, True, 23)}</span>'
                f'<div class="grow"><b style="font-size:17px;display:block">{title}</b><span class="mut" style="font-size:12.5px">{who}</span></div>'
                f'<div style="text-align:right"><b style="font-size:22px" class="tn">{count[0]}</b>'
                f'<div class="mut" style="font-size:11.5px">{count[1]}</div></div></div>'
                f'<div style="margin-top:6px">{body}</div></section>')

    web = surface("web", "blue", "Web App", "Admin klien, Supervisor K3, Operator CCTV · di browser",
                  (f'{n["web_modules"]} modul', f'{n["web_features"]} fitur'), mod_list(WEB_APP, 2))
    dashb = surface("live_tv", "cyan", "Realtime Dashboard", "Layar ruang kontrol / TV · aplikasi terpisah",
                    (f'{n["dash_views"]} tampilan', f'{n["dash_widgets"]} widget'), mod_list(DASHBOARD))
    sa = surface("shield_person", "violet", "Konsol Super Admin", "Tim kita: semua tenant & platform",
                 (f'{n["super_modules"]} modul', f'{n["super_features"]} fitur'), mod_list(SUPER, 2))
    mob = surface("smartphone", "green", "Aplikasi Supervisor", "iOS & Android · di lantai gudang",
                  (f'{n["mobile_features"]} fitur', "+ WhatsApp"),
                  "".join(f'<div class="row" style="padding:5px 0;font-size:13px">{I("check", size=17, color="var(--text-3)")}{f}</div>' for f in MOBILE))
    roles = "".join(f'<div class="row" style="padding:4px 0;font-size:13px">{bd(r[1], r[2], r[0])}<span class="mut">{r[3]}</span></div>' for r in ROLES)
    rolec = (f'<section class="card" style="padding:16px 20px"><div class="row" style="gap:12px"><span class="it slate" style="width:42px;height:42px">{I("badge", True, 23)}</span>'
             f'<div class="grow"><b style="font-size:17px;display:block">{n["roles"]} peran</b><span class="mut" style="font-size:12.5px">hak akses berlapis, per lokasi</span></div></div>'
             f'<div style="margin-top:6px">{roles}</div></section>')
    flow_steps = [("videocam", "CCTV yang ada", "RTSP / ONVIF, diverifikasi dulu"), ("memory", "Edge AI box di gudang", "deteksi + peta lantai, ±1 dtk"),
                  ("cloud", "Platform cloud", "multi-tenant, aturan, bukti"),
                  ("devices", "Web · TV · HP · WhatsApp", "orang yang tepat, saat itu juga")]
    flow = "".join(
        f'<div class="row" style="gap:10px;flex:1"><span class="it blue">{I(ic, True, 19)}</span><div><b style="font-size:13.5px;display:block">{a}</b>'
        f'<span class="mut" style="font-size:12px">{b}</span></div></div>' + (I("arrow_forward", size=20, color="var(--text-3)") if k < 3 else "")
        for k, (ic, a, b) in enumerate(flow_steps))
    body = (f'<div style="display:grid;grid-template-columns:1fr 600px;gap:20px">{web}{dashb}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 360px 600px;gap:20px">{sa}{mob}{rolec}</div>'
            f'<section class="card" style="padding:14px 22px;flex-direction:row;align-items:center;gap:16px">'
            f'<b style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);white-space:nowrap">Alur data</b>{flow}</section>')
    return slide("Peta produk", f"Satu platform, empat tampilan, {n['roles']} peran",
                 f"{n['web_modules']} modul web app · {n['dash_views']} tampilan dashboard realtime · {n['super_modules']} modul super admin · "
                 f"aplikasi supervisor = {total} fitur. {poc()} = sudah berjalan di proof of concept.", body)


def p01_peran() -> str:
    roles = ROLES
    cards = "".join(
        f'<section class="card" style="padding:16px 18px;gap:8px"><div class="row"><span class="it {r[2]}">{I(r[0], True, 19)}</span>'
        f'<b style="font-size:16px">{r[1]}</b></div><div class="sec" style="font-size:13px">{r[3]}</div>'
        f'<div class="row mut" style="font-size:12.5px;gap:6px">{I("location_on", size=16)}{r[4]}</div></section>' for r in roles)
    F, E, V, N = "full", "edit", "view", "none"
    cap = [
        ("Live monitoring & peta lantai", [V + "*", F, F, F, V]),
        ("Tangani insiden: tugaskan, ubah status, tutup", [N, F, F, E, N]),
        ("Konfirmasi / tandai alarm palsu", [N, F, F, F, N]),
        ("Ekspor bukti video & PDF", [N, F, F, N, N]),
        ("Laporan & kepatuhan K3", [N, F, F, V, V]),
        ("Zona & aturan", [N, F, E, N, N]),
        ("Kamera & kalibrasi", [E + "*", F, V, V, N]),
        ("Notifikasi & eskalasi", [N, F, E, N, N]),
        ("Pengguna, peran & SSO", [E, F, N, N, N]),
        ("Integrasi & API", [N, F, N, N, N]),
        ("Langganan & tagihan tenant", [F, V, N, N, N]),
        ("Tenant, paket & feature flag", [F, N, N, N, N]),
        ("Edge box & rilis model AI", [F, V, N, N, N]),
        ("Log audit", [F, V, N, N, N]),
        ("Masuk sebagai tenant (dukungan)", [E + "*", N, N, N, N]),
    ]
    mark = {F: (I("check_circle", True, 20, "#0f172a"), "Kelola"), E: (I("edit_square", False, 19, "#0f172a"), "Terbatas"),
            V: (I("visibility", False, 19, "#64748b"), "Lihat"), N: ('<span style="color:#cbd5e1;font-size:18px">—</span>', "")}
    head = "".join(f'<th style="text-align:center;width:170px">{bd(r[1], r[2], r[0])}</th>' for r in roles)
    rows = []
    for name, cells in cap:
        tds = []
        for c in cells:
            star = c.endswith("*")
            m, label = mark[c.rstrip("*")]
            tds.append(f'<td style="text-align:center"><span class="row" style="justify-content:center;gap:6px">{m}'
                       f'<span class="mut" style="font-size:12px">{label}{"*" if star else ""}</span></span></td>')
        rows.append(f'<tr><td style="font-weight:500">{name}</td>{"".join(tds)}</tr>')
    table = (f'<section class="card" style="flex:1;min-height:0"><table class="tbl"><thead><tr><th>Kemampuan</th>{head}</tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></section>')
    notes = (f'<div class="row" style="gap:28px;font-size:13px;color:var(--text-2)">'
             f'<span class="row" style="gap:6px">{mark[F][0]} Kelola = buat, ubah, hapus</span>'
             f'<span class="row" style="gap:6px">{mark[E][0]} Terbatas = untuk timnya / perlu persetujuan Admin</span>'
             f'<span class="row" style="gap:6px">{mark[V][0]} Lihat saja</span>'
             f'<span class="row" style="gap:6px">{I("lock", True, 18, "#6d28d9")}* Super Admin hanya dengan izin Admin tenant, berbatas waktu, dan tercatat di log audit</span></div>')
    body = f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px">{cards}</div>{table}{notes}'
    return slide("Peran & hak akses", "Super Admin mengelola platform, Admin mengelola gudangnya",
                 "Peran berbasis RBAC dengan akses per lokasi. Data tiap klien terpisah (multi-tenant); "
                 "tim kita tidak bisa melihat kamera klien tanpa izin yang tercatat.", body)


def p02_beranda() -> str:
    kpis = (
        kpi("notification_important", "red", "Insiden terbuka", "7",
            f'{bd("1 tinggi", "red")}{bd("6 sedang", "amber")}<span>3 belum ditanggapi</span>') +
        kpi("warning", "red", "Nyaris tertabrak forklift", '3<small>hari ini</small>',
            f'{up("40%", True, "down")} dari rata-rata 7 hari (5)') +
        kpi("engineering", "amber", "Kepatuhan APD", "86%",
            f'{up("4 poin")} dari minggu lalu · target 95%',
            '<div class="prog" style="margin-top:2px"><i style="width:86%;background:var(--s1)"></i></div>') +
        kpi("forklift", "blue", "Utilisasi forklift", "62%", "waktu bergerak dari waktu terlihat · 5 unit") +
        kpi("videocam", "green", "Kamera siap pakai", '15<small>/ 19</small>',
            f'<span>4 gagal uji posisi</span><span class="lnk">Perbaiki {I("chevron_right", size=16)}</span>')
    )
    big = tile("../img/cam_0003.jpg", "CAM 0003 · Area kerja timur", CAM_RGB["Camera_0003"],
               f'{I("groups", True)}5 orang', "width:640px;height:360px")
    small = "".join(tile(f"../img/cam_{c[-4:]}.jpg", f"{ops.cam_label(c)} · {CAMNAME[c]}", CAM_RGB[c],
                         f'{I("groups", True)}{n} orang', "width:320px;height:174px")
                    for c, n in (("Camera_0005", 6), ("Camera_0001", 6)))
    live = card("Live sekarang", f'<div class="row" style="gap:12px;align-items:stretch">{big}<div class="col" style="gap:12px">{small}</div></div>',
                icon="videocam", sub="3 dari 15 kamera · dipilih otomatis: yang paling ramai",
                right=f'<span class="lnk">Buka Live Monitoring {I("arrow_forward", size=16)}</span>')
    items = []
    for inc in INCIDENTS[:4]:
        iid, e, s, title, detail, place, cams, t, ago, st, owner, sla = inc
        who = (f'{avatar(owner, 24)}<span class="sec" style="font-size:12.5px">{owner.split()[0]}</span>' if owner else
               '<span class="bd slate">Belum ditugaskan</span>')
        items.append(
            f'<div class="ev">{img(snap(e), 96, 54)}<div class="grow"><div class="t1">{I(KIND_ICON.get(e["kind"], "warning"), True, 17, "var(--text-2)")}'
            f'<span class="ell">{title}</span></div><div class="t2 ell">INS-{iid} · {detail} · {place} · {t}</div>'
            f'<div class="row" style="gap:8px;margin-top:5px">{sev(s)}{status(st)}{who}</div></div>'
            f'<div style="width:118px;text-align:right"><div class="tn" style="font-size:12px;font-weight:600;white-space:nowrap;color:{sla[2]}">{sla[0]}</div>'
            f'<div class="prog" style="margin-top:6px"><i style="width:{sla[1] * 100:.0f}%;background:{sla[2]}"></i></div></div></div>')
    todo = card("Perlu tindakan", "".join(items), icon="pending_actions", sub="diurutkan menurut tingkat & SLA",
                right=f'<span class="lnk">Pusat Insiden {I("arrow_forward", size=16)}</span>', cb_style="padding-top:4px;padding-bottom:4px")
    days = ["Sel", "Rab", "Kam", "Jum", "Sab", "Min", "Sen"]
    trend = card("Insiden 7 hari", vbars([("Tinggi", [1, 0, 2, 1, 0, 0, 1], "var(--crit)"),
                                          ("Sedang", [9, 12, 8, 11, 6, 3, 8], "var(--warn)"),
                                          ("Rendah & info", [4, 6, 3, 5, 2, 1, 3], "var(--neutral)")],
                                         days, 470, 196, stacked=True, ticks=4),
                 icon="bar_chart", right=legend([("Tinggi", "var(--crit)"), ("Sedang", "var(--warn)"), ("Rendah & info", "var(--neutral)")]))
    heat = card("Titik rawan minggu ini",
                f'<div class="row" style="gap:14px;align-items:stretch">'
                f'<div style="width:260px;height:200px;border-radius:10px;overflow:hidden;border:1px solid var(--border)">'
                f'<img src="../img/plan_heat_light.png" style="width:578px;margin:-220px 0 0 -260px;display:block"></div>'
                f'<div class="grow col" style="gap:10px;font-size:13px">'
                + "".join(f'<div class="row" style="gap:10px"><b class="tn" style="width:18px;color:var(--text-3)">{k}</b><div class="grow"><b>{a}</b>'
                          f'<div class="mut" style="font-size:12px">{b}</div></div></div>'
                          for k, (a, b) in enumerate([("Persimpangan jalur forklift", "3 near miss · 18 masuk jalur"),
                                                      ("Area kerja timur", "padat 09:00–10:00"),
                                                      ("Lorong satu arah", "11 melawan arah")], 1))
                + '</div></div>', icon="local_fire_department")
    apd = card("Kepatuhan APD per area", hbars([("Area kerja timur", 78), ("Jalur forklift tengah", 84), ("Area utara", 91),
                                                ("Area selatan", 93), ("Staging A", 95)], vmax=100,
                                               fmt=lambda v: f"{v}%", label_w=150),
               icon="engineering", sub="helm & rompi, shift ini", cb_style="padding-top:10px")
    body = (f'<div class="ph"><div><h1>Selamat pagi, Rina</h1><p>Senin, 5 Oktober 2026 · Shift Pagi 07:00–15:00 · Gudang Simulasi A</p></div>'
            f'<div class="acts"><span class="btn">{I("download")}Unduh ringkasan shift</span>'
            f'<span class="btn pri">{I("open_in_new")}Buka Dashboard Realtime</span></div></div>'
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px">{kpis}</div>'
            f'<div style="display:grid;grid-template-columns:1012px 1fr;gap:16px">{live}{todo}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;flex:1;min-height:0">{trend}{heat}{apd}</div>')
    return app("beranda", body)


def p03_live() -> str:
    big = ('<div class="tile" style="grid-column:1/3;grid-row:1/3;box-shadow:0 0 0 3px #ef4444">'
           '<img src="../img/evidence_0001.jpg">'
           f'<span class="tl"><span class="dot" style="color:#ef4444"></span>CAM 0001 · Area konveyor barat</span>'
           f'<span class="tr">{I("groups", True)}6 orang · 5 di peta</span>'
           f'<div style="position:absolute;left:0;right:0;bottom:0;padding:10px 12px;display:flex;align-items:center;gap:10px;'
           f'background:linear-gradient(transparent,rgba(10,14,19,.92) 40%)">'
           f'<span class="bd" style="background:#ef4444;color:#fff;height:26px;font-size:12.5px">{I("warning", True)}SOROTAN OTOMATIS</span>'
           f'<b style="color:#fff;font-size:14px;white-space:nowrap">Nyaris tertabrak forklift · P14 & forklift F12</b>'
           f'<span style="margin-left:auto;color:#cbd5e1;font-size:12px;white-space:nowrap">menggantikan CAM 0008 · kembali otomatis</span></div></div>')
    smalls = "".join(tile(f"../img/cam_{c[-4:]}.jpg", f"{ops.cam_label(c)} · {CAMNAME[c]}", CAM_RGB[c], f'{I("groups", True)}{n}')
                     for c, n in (("Camera_0003", 5), ("Camera_0005", 6), ("Camera_0011", 2), ("Camera_0007", 1), ("Camera_0015", 4)))
    wall = (f'<section class="card" style="background:#0b1220;border-color:#0b1220;padding:12px">'
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,240px);gap:10px">{big}{smalls}</div></section>')
    marks = [(4, "medium"), (9, "medium"), (17, "medium"), (22, "info"), (31, "medium"), (38, "medium"), (52, "medium"),
             (61, "medium"), (66, "medium"), (78, "medium"), (84, "medium"), (97, "high")]
    col = {"high": "#dc2626", "medium": "#f59e0b", "info": "#94a3b8"}
    ticks = "".join(f'<span style="position:absolute;left:{p}%;top:-5px;width:12px;height:12px;border-radius:50%;margin-left:-6px;'
                    f'background:{col[s]};border:2px solid #fff;box-shadow:0 0 0 1px {col[s]}"></span>' for p, s in marks)
    labels = "".join(f'<span style="position:absolute;left:{p}%;transform:translateX(-50%)">{t}</span>'
                     for p, t in ((0, "10:12"), (25, "10:20"), (50, "10:27"), (75, "10:35"), (100, "10:42")))
    timeline = (f'<section class="card" style="padding:16px 20px;flex-direction:row;align-items:center;gap:18px">'
                f'<div class="row" style="gap:6px">{I("skip_previous", True, 22, "var(--text-2)")}{I("pause_circle", True, 34, "var(--brand)")}'
                f'{I("skip_next", True, 22, "var(--text-2)")}</div>'
                f'<span class="bd red" style="height:26px">{I("radio_button_checked", True)}LANGSUNG</span>'
                f'<div class="grow" style="position:relative;padding:0 6px"><div style="height:6px;border-radius:3px;background:linear-gradient(90deg,#bfdbfe,#2563eb)"></div>'
                f'{ticks}<div style="position:relative;height:16px;margin-top:10px;font-size:11.5px;color:var(--text-3)" class="tn">{labels}</div></div>'
                f'{legend([("Tinggi", "#dc2626"), ("Sedang", "#f59e0b"), ("Info", "#94a3b8")])}</section>')
    feed = []
    for inc in INCIDENTS[:4]:
        iid, e, s, title, detail, place, cams, t, *_ = inc
        acts = (f'<div class="row" style="gap:6px;margin-top:8px"><span class="btn sm pri">{I("check")}Konfirmasi</span>'
                f'<span class="btn sm">{I("block")}Alarm palsu</span></div>') if s == "high" else ""
        feed.append(f'<div class="ev" style="align-items:flex-start">{img(snap(e), 92, 52)}<div class="grow">'
                    f'<div class="t1" style="font-size:13px"><span class="ell">{title}</span></div>'
                    f'<div class="t2 ell">{detail} · {t}</div><div class="row" style="gap:6px;margin-top:5px">{sev(s)}{"".join(cam(c) for c in cams)}</div>{acts}</div></div>')
    mini = card("Peta lantai", f'<div style="border-radius:10px;overflow:hidden;background:#0a0e13;height:330px">'
                               f'<img src="../img/plan_live.png" style="width:627px;margin:-174px 0 0 -125px;display:block"></div>',
                icon="map", right='<span class="mut">posisi langsung · meter</span>', cb_style="padding-top:12px")
    alerts = card("Peringatan langsung", "".join(feed), icon="notifications_active", right='<span class="bd red">1 baru</span>',
                  cb_style="padding-top:2px;padding-bottom:6px", style="flex:1")
    body = (f'<div class="ph"><div><h1>Live Monitoring</h1><p>15 kamera aktif · AI menandai orang, forklift, APD dan zona di setiap gambar</p></div>'
            f'<div class="acts"><div class="seg"><span>{I("crop_square")}1</span><span>{I("grid_view")}4</span><span>{I("apps")}9</span>'
            f'<span class="on">{I("view_quilt", True)}1+5</span></div>'
            f'<span class="flt">{I("video_library")}<b>Grup: Semua kamera</b>{I("expand_more")}</span>'
            f'<span class="flt" style="gap:10px">Overlay AI {tg(True)}</span><span class="flt" style="gap:10px">Sorotan otomatis {tg(True)}</span></div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 440px;gap:16px;flex:1;min-height:0">'
            f'<div class="col" style="gap:16px">{wall}{timeline}</div><div class="col" style="gap:16px">{mini}{alerts}</div></div>')
    return app("live", body, clock="10:42")


def p04_peta() -> str:
    chips = "".join(f'<span class="row" style="gap:6px;background:rgba(10,14,19,.85);color:#e9eef4;padding:4px 9px;border-radius:8px;font-size:11.5px;font-weight:500">'
                    f'{tg(on)}{n}</span>' for n, on in (("Orang", True), ("Forklift & pallet truck", True), ("Zona", True),
                                                       ("Garis hitung", True), ("Jangkauan kamera", True), ("Jejak 3 dtk", False)))
    mapc = (f'<section class="card" style="background:#0a0e13;border-color:#0a0e13;padding:10px;position:relative;width:860px">'
            f'<img src="../img/plan_live.png" style="width:840px;height:821px;display:block;border-radius:8px">'
            f'<div style="position:absolute;left:22px;top:22px;display:flex;flex-direction:column;gap:6px">{chips}</div>'
            f'<div style="position:absolute;right:22px;bottom:22px;display:flex;flex-direction:column;gap:6px">'
            + "".join(f'<span style="width:36px;height:36px;border-radius:8px;background:rgba(10,14,19,.85);display:grid;place-items:center;color:#e9eef4">{I(x)}</span>'
                      for x in ("add", "remove", "my_location")) +
            '</div></section>')
    stats = "".join(
        f'<div class="col" style="gap:4px;padding:2px 0"><div class="row" style="gap:8px;color:var(--text-2);font-size:13px;font-weight:500">'
        f'<span class="it {t}" style="width:28px;height:28px">{I(ic, True, 17)}</span>{a}</div><b class="tn" style="font-size:26px">{b}</b>'
        f'<span class="mut" style="font-size:12px">{c}</span></div>'
        for ic, t, a, b, c in (("groups", "cyan", "Orang", "31", "22 bergerak · 9 diam"), ("forklift", "amber", "Forklift", "3 / 5", "bergerak / terlihat"),
                               ("pallet", "amber", "Pallet truck", "2", "1 bergerak"), ("warning", "red", "Near miss", "1", "10:41:58 · CAM 0001")))
    now = card("Di lantai sekarang", f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">{stats}</div>',
               icon="sensors", right='<span class="mut">dari 15 kamera · diperbarui 10× per detik</span>')
    zrows = [("1", "Staging A", "area", "0", "1 dtk / orang", "—"), ("2", "Area kerja timur", "area", "2", "5 dtk / orang", "APD wajib"),
             ("3", "Area utara", "area", "1", "8 dtk / orang", "—"), ("4", "Area selatan", "area", "0", "—", "—"),
             ("5", "Jalur forklift tengah", "vehicle_lane", "0", "1 kali dimasuki", "Jalur forklift · near miss · kecepatan"),
             ("6", "Lorong satu arah", "one_way", "0", "11 melawan arah hari ini", "Satu arah")]
    zc = {"area": "#94a3b8", "vehicle_lane": "#f59e0b", "one_way": "#f472b6"}
    zt = "".join(f'<tr><td><span class="row" style="gap:8px"><b class="tn" style="width:22px;height:22px;border-radius:6px;background:#0f172a;color:#fff;display:grid;place-items:center;font-size:11.5px">{k}</b>'
                 f'<i class="sw" style="background:{zc[kind]}"></i>{n}</span></td><td class="tn" style="font-weight:600">{a}</td><td class="sec">{b}</td><td class="sec" style="font-size:12.5px">{c}</td></tr>'
                 for k, n, kind, a, b, c in zrows)
    lt = "".join(f'<tr><td><span class="row" style="gap:8px"><b class="tn" style="width:22px;height:22px;border-radius:6px;background:#e2e8f0;display:grid;place-items:center;font-size:11.5px">{k}</b>{n}</span></td>'
                 f'<td class="tn"><span class="up" style="color:var(--text)">{I("north", size=15)}{a}</span></td><td class="tn"><span class="up" style="color:var(--text)">{I("south", size=15)}{b}</span></td><td class="sec" style="font-size:12.5px">{c}</td></tr>'
                 for k, n, a, b, c in (("A", "Lintasan timur", "412", "405", "puncak 09:00–09:15"),
                                       ("B", "Lintasan area kerja", "233", "229", "puncak 13:30"),
                                       ("C", "Penyeberangan jalur forklift", "96", "101", "aturan: hanya di garis ini")))
    zones = card("Zona & garis hitung",
                 f'<table class="tbl cp"><thead><tr><th>Zona</th><th>Orang sekarang</th><th>Lama tinggal</th><th>Aturan aktif</th></tr></thead><tbody>{zt}</tbody></table>'
                 f'<table class="tbl cp" style="margin-top:8px"><thead><tr><th>Garis hitung</th><th>Masuk hari ini</th><th>Keluar</th><th>Catatan</th></tr></thead><tbody>{lt}</tbody></table>',
                 icon="polyline", right=f'<span class="lnk">Ubah di Zona & Aturan {I("arrow_forward", size=16)}</span>', cb_style="padding:12px 0 8px")
    replay = card("Putar ulang 3D", f'<div class="row" style="gap:16px;align-items:stretch">'
                                    f'<div class="tile" style="width:256px;height:144px;flex:none"><img src="../img/replay_3d.jpg" style="object-position:50% 40%">'
                                    f'<span style="position:absolute;inset:0;display:grid;place-items:center">{I("play_circle", True, 54, "#fff")}</span></div>'
                                    f'<div class="col" style="gap:10px;font-size:13.5px"><b style="font-size:14px">Lihat ulang dari sudut mana pun</b>'
                                    f'<span class="sec">Semua kamera disinkronkan ke satu ruang 3D: berguna untuk investigasi insiden dan pelatihan.</span>'
                                    f'<span class="sec">Pilih rentang waktu atau langsung dari detail insiden.</span>'
                                    f'<span class="btn sm" style="align-self:flex-start;margin-top:auto">{I("view_in_ar")}Buka replay 3D</span></div></div>',
                  icon="view_in_ar", right=poc())
    body = (f'<div class="ph"><div><h1>Peta Lantai Digital</h1><p>Satu peta dari 15 kamera · setiap orang dan forklift dalam meter · satu ID yang sama di semua kamera</p></div>'
            f'<div class="acts"><div class="seg"><span class="on">{I("radio_button_checked", True)}Langsung</span><span>{I("local_fire_department")}Heatmap</span>'
            f'<span>{I("history")}Putar ulang</span></div><span class="btn">{I("fullscreen")}Layar penuh</span></div></div>'
            f'<div style="display:grid;grid-template-columns:860px 1fr;gap:16px;flex:1;min-height:0;align-items:start">{mapc}'
            f'<div class="col" style="gap:16px;min-width:0">{now}{zones}{replay}</div></div>')
    return app("peta", body, clock="10:42")


def p05_insiden() -> str:
    stats = "".join(
        f'<section class="card" style="padding:14px 18px;flex-direction:row;align-items:center;gap:14px"><span class="it {t}">{I(ic, True, 19)}</span>'
        f'<div><div class="sec" style="font-size:12.5px;font-weight:500">{a}</div><div class="row" style="gap:8px"><b class="tn" style="font-size:22px">{b}</b>'
        f'<span class="mut" style="font-size:12.5px">{c}</span></div></div></section>'
        for ic, t, a, b, c in (("pending_actions", "red", "Terbuka", "7", "1 tinggi · 2 belum ditanggapi"),
                               ("timer", "blue", "Waktu tanggap median", "3 mnt 40 dtk", "target ≤ 15 mnt (tinggi)"),
                               ("verified", "green", "Selesai sesuai SLA", "94%", "30 hari terakhir"),
                               ("block", "slate", "Ditandai alarm palsu", "6%", "dipakai untuk melatih ulang AI")))
    rows = []
    for k, inc in enumerate([i for i in INCIDENTS if i[0] != "0137"]):
        iid, e, s, title, detail, place, cams, t, ago, st, owner, sla = inc
        who = (f'<span class="row" style="gap:8px">{avatar(owner, 26)}<span>{owner}</span></span>' if owner
               else f'<span class="btn sm">{I("person_add")}Tugaskan</span>')
        rows.append(
            f'<tr class="{"on" if k in (1, 4) else ""}"><td style="width:34px">{I("check_box" if k in (1, 4) else "check_box_outline_blank", k in (1, 4), 20, "var(--brand)" if k in (1, 4) else "var(--text-3)")}</td>'
            f'<td style="width:108px;padding-top:7px;padding-bottom:7px">{img(snap(e), 90, 50)}</td>'
            f'<td><div class="t1 row" style="gap:7px;font-weight:600">{I(KIND_ICON.get(e["kind"], "warning"), True, 17, "var(--text-2)")}{title}</div>'
            f'<div class="mut" style="font-size:12.5px;margin-top:2px">INS-{iid} · {detail}</div></td>'
            f'<td>{sev(s)}</td><td><div>{place}</div><div class="row" style="gap:5px;margin-top:4px">{"".join(cam(c) for c in cams)}</div></td>'
            f'<td class="tn"><div>{t}</div><div class="mut" style="font-size:12px">{ago}</div></td><td>{status(st)}</td><td>{who}</td>'
            f'<td style="width:130px"><div class="tn" style="font-size:12px;font-weight:600;color:{sla[2]}">{sla[0]}</div>'
            f'<div class="prog" style="margin-top:6px"><i style="width:{sla[1] * 100:.0f}%;background:{sla[2]}"></i></div></td>'
            f'<td style="width:40px">{I("more_vert", size=20, color="var(--text-3)")}</td></tr>')
    tabs = ('<div class="tabs"><span class="on">Semua <span class="n">42</span></span><span>Baru <span class="n">2</span></span>'
            '<span>Ditangani <span class="n">5</span></span><span>Selesai <span class="n">33</span></span><span>Alarm palsu <span class="n">2</span></span></div>')
    filters = (f'<div class="row" style="padding:12px 18px;gap:8px"><span class="inp" style="width:300px">{I("search", size=18)}Cari ID, orang, kamera…</span>'
               + "".join(f'<span class="flt">{a}: <b>{b}</b>{I("expand_more")}</span>' for a, b in
                         (("Tingkat", "Semua"), ("Jenis", "Semua"), ("Zona", "Semua"), ("Kamera", "Semua"), ("PJ", "Semua"), ("Waktu", "Hari ini")))
               + f'<span class="btn sm ghost" style="margin-left:auto">{I("tune")}Simpan tampilan</span></div>')
    bulk = (f'<div class="row" style="margin:auto 18px 14px;padding:10px 14px;border-radius:10px;background:#0f172a;color:#fff;gap:14px;font-size:13px">'
            f'<b>2 dipilih</b><span class="row" style="gap:6px;color:#cbd5e1">{I("person_add", size=18)}Tugaskan ke…</span>'
            f'<span class="row" style="gap:6px;color:#cbd5e1">{I("swap_horiz", size=18)}Ubah status</span>'
            f'<span class="row" style="gap:6px;color:#cbd5e1">{I("block", size=18)}Tandai alarm palsu</span>'
            f'<span class="row" style="gap:6px;color:#cbd5e1">{I("picture_as_pdf", size=18)}Ekspor bukti</span>'
            f'<span style="margin-left:auto;color:#94a3b8">{I("close", size=18)}</span></div>')
    table = (f'<section class="card" style="flex:1">{tabs}{filters}<table class="tbl"><thead><tr><th></th><th>Bukti</th><th>Kejadian</th><th>Tingkat</th>'
             f'<th>Lokasi & kamera</th><th>Waktu</th><th>Status</th><th>Penanggung jawab</th><th>SLA tanggap</th><th></th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table>{bulk}</section>')
    body = (f'<div class="ph"><div><h1>Pusat Insiden</h1><p>Setiap peringatan AI menjadi insiden: ditugaskan, ditangani, ditutup dengan bukti</p></div>'
            f'<div class="acts"><span class="btn">{I("download")}Ekspor CSV</span><span class="btn pri">{I("add")}Insiden manual</span></div></div>'
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">{stats}</div>{table}')
    return app("insiden", body)


def p06_detail() -> str:
    player = (f'<section class="card" style="padding:0;overflow:hidden;background:#000;border-color:#000">'
              f'<div class="tile" style="width:100%;height:580px;border-radius:0"><img src="../img/evidence_0001_before.jpg">'
              f'<span class="tl" style="font-size:12.5px;padding:5px 10px"><span class="dot" style="color:#ef4444"></span>CAM 0001 · Area konveyor barat · 10:41:58</span>'
              f'<span class="tr" style="font-size:12.5px;padding:5px 10px">{I("auto_awesome", True)}Ditandai AI · aturan jarak 1,5 m</span>'
              f'<div style="position:absolute;left:0;right:0;bottom:0;padding:34px 18px 14px;background:linear-gradient(transparent,rgba(0,0,0,.85));color:#fff">'
              f'<div style="position:relative;height:6px;border-radius:3px;background:rgba(255,255,255,.25)">'
              f'<i style="position:absolute;left:0;top:0;bottom:0;width:48%;background:#fff;border-radius:3px"></i>'
              f'<i style="position:absolute;left:50%;top:-4px;width:4px;height:14px;background:#ef4444;border-radius:2px"></i>'
              f'<i style="position:absolute;left:62%;top:-4px;width:4px;height:14px;background:#ef4444;opacity:.6;border-radius:2px"></i></div>'
              f'<div class="row" style="margin-top:10px;gap:14px;font-size:13px">{I("replay_10", False, 22)}{I("play_arrow", True, 30)}{I("forward_10", False, 22)}'
              f'<span class="tn">−00:01 / klip 00:20 (10 dtk sebelum – 10 dtk sesudah)</span>'
              f'<span style="margin-left:auto" class="row">{I("speed", size=18)}1×</span><span class="row">{I("view_in_ar", size=18)}Replay 3D</span>'
              f'<span class="row">{I("fullscreen", size=20)}</span></div></div></div></section>')
    shots = "".join(f'<div class="col" style="gap:6px">{img(src, 214, 120)}<span class="sec tn" style="font-size:12px">{t}</span></div>'
                    for src, t in (("../img/evidence_0001_before.jpg", "10:41:58 · terdeteksi"), ("../img/cam_0001.jpg", "10:41:59"),
                                   ("../img/evidence_0001.jpg", "10:42:00 · forklift melintas")))
    shots_card = card("Cuplikan bukti", f'<div class="row" style="gap:12px;align-items:flex-start">{shots}</div>', icon="photo_library",
                      right=f'<span class="lnk">{I("add_photo_alternate", size=16)} Tambah foto lapangan</span>')
    mapcrop = card("Posisi di peta", f'<div style="border-radius:10px;overflow:hidden;background:#0a0e13;height:150px;position:relative">'
                                     f'<img src="../img/plan_live.png" style="width:900px;margin:-431px 0 0 -236px;display:block"></div>'
                                     f'<div class="mut" style="font-size:12px;margin-top:8px">Lintasan forklift · ±0,2 m</div>', icon="map")
    kv = (f'<div class="kv"><span>Aturan</span><span>Pejalan kaki ≤ 1,5 m dari forklift bergerak</span>'
          f'<span>Pihak terlibat</span><span class="row" style="gap:6px">{bd("P14 · pejalan kaki", "slate", "directions_walk")}{bd("F12 · forklift 4 km/j", "amber", "forklift")}</span>'
          f'<span>Lokasi</span><span>Lintasan forklift, dekat Area konveyor barat</span>'
          f'<span>Kamera</span><span class="row" style="gap:6px">{cam("CAM 0001")}<span class="mut" style="font-size:12.5px">hanya kamera ini yang melihat</span></span>'
          f'<span>Terdeteksi</span><span class="tn">Senin, 5 Okt 2026 · 10:41:58 WIB</span>'
          f'<span>Penanggung jawab</span><span class="row" style="gap:8px">{avatar("Budi Santoso", 24)}Budi Santoso · Supervisor K3</span>'
          f'<span>SLA</span><span class="row" style="gap:8px"><span class="tn" style="font-weight:600;color:#079455">ditanggapi dalam 33 dtk</span>'
          f'<span class="mut">· selesai ≤ 24 jam</span></span></div>')
    summary = card("Ringkasan", kv, icon="info")
    capa = card("Tindakan korektif (CAPA)", "".join(
        f'<div class="chk">{I("check_circle" if done else "radio_button_unchecked", done, 20, "#079455" if done else "var(--text-3)")}'
        f'<div class="grow"><div style="{"text-decoration:line-through;color:var(--text-3)" if done else ""}">{a}</div>'
        f'<div class="mut" style="font-size:12px">{b}</div></div>{avatar(c, 24)}</div>'
        for a, b, c, done in (("Briefing ulang operator forklift F12", "selesai 10:58", "Budi Santoso", True),
                              ("Pasang cermin cembung di persimpangan", "jatuh tempo 12 Okt", "Fajar Nugroho", False),
                              ("Tinjau marka penyeberangan pejalan kaki", "jatuh tempo 9 Okt", "Siti Rahma", False))),
        icon="task_alt", right=f'<span class="lnk">{I("add", size=16)} Tambah</span>', cb_style="padding-top:6px")
    tl = [("auto_awesome", "#2563eb", "10:41:58", "AI mendeteksi near miss, CAM 0001 disorot otomatis di Live Monitoring"),
          ("chat", "#079455", "10:41:59", "WhatsApp & push terkirim ke Budi Santoso (Supervisor K3 shift)"),
          ("visibility", "#64748b", "10:42:20", "Dibaca Budi Santoso"),
          ("assignment_ind", "#d97706", "10:42:31", "Status → Ditangani oleh Budi Santoso"),
          ("description", "#64748b", "10:58:04", "Catatan: operator F12 tidak membunyikan klakson di persimpangan")]
    tlh = "".join(f'<div class="row" style="gap:12px;align-items:flex-start;padding:6px 0"><span class="it" style="width:28px;height:28px;background:{c}1a;color:{c}">{I(ic, True, 16)}</span>'
                  f'<div class="grow" style="font-size:13px"><b class="tn" style="font-size:12.5px">{t}</b><div class="sec">{x}</div></div></div>' for ic, c, t, x in tl)
    timeline = card("Linimasa", tlh, icon="history", cb_style="padding-top:4px", style="flex:1")
    body = (f'<div class="ph"><div><div class="crumb">Pusat Insiden {I("chevron_right", size=16)} INS-0142</div>'
            f'<div class="row" style="gap:12px"><h1>Nyaris tertabrak forklift</h1>{sev("high")}{bd("Ditangani", "amber", "assignment_ind")}</div>'
            f'<p>Senin, 5 Oktober 2026 · 10:41:58 WIB · Lintasan forklift · CAM 0001</p></div>'
            f'<div class="acts"><span class="btn">{I("block")}Alarm palsu</span><span class="btn">{I("share")}Bagikan</span>'
            f'<span class="btn">{I("picture_as_pdf")}Ekspor bukti (PDF)</span><span class="btn pri">{I("check")}Selesaikan</span></div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 560px;gap:16px;flex:1;min-height:0">'
            f'<div class="col" style="gap:16px">{player}<div style="display:grid;grid-template-columns:1fr 330px;gap:16px">{shots_card}{mapcrop}</div></div>'
            f'<div class="col" style="gap:16px">{summary}{capa}{timeline}</div></div>')
    return app("insiden", body, clock="10:58")


def p07_cari() -> str:
    q = "orang tanpa rompi di area kerja timur pagi ini"
    chips = "".join(f'<span class="bd blue" style="height:28px;font-size:12.5px;padding:0 10px">{a}: {b} {I("close", size=15)}</span>'
                    for a, b in (("Jenis", "Tanpa rompi"), ("Zona", "Area kerja timur"), ("Waktu", "hari ini 07:00–10:43"),
                                 ("Kamera", "semua yang melihat zona (3)")))
    hero = (f'<section class="card" style="padding:20px 22px;gap:14px"><div class="row" style="gap:12px">'
            f'<div class="row grow" style="height:58px;border:2px solid var(--brand);border-radius:12px;padding:0 16px;gap:12px;box-shadow:0 0 0 4px #dbe8fe">'
            f'{I("auto_awesome", True, 24, "var(--brand)")}<span style="font-size:18px;font-weight:500">{q}</span>'
            f'<span class="i" style="margin-left:auto;color:var(--text-3)">mic</span></div>'
            f'<span class="btn pri" style="height:58px;padding:0 26px;font-size:15px">{I("search")}Cari</span></div>'
            f'<div class="row" style="gap:8px;flex-wrap:wrap"><span class="mut" style="font-size:13px">Dipahami sebagai</span>{chips}'
            f'<span class="mut" style="margin-left:auto;font-size:13px">6 hasil · 0,4 dtk · dicari di 3 kamera</span></div></section>')
    picks = [(ev2(13), "P66", "Tanpa rompi", "10:24:12"), (ev2(11), "P60", "Tanpa rompi", "10:21:40"),
             (ev2(12), "P67", "Tanpa helm & rompi", "10:37:41"), (ev2(9), "P30", "Tanpa rompi", "09:58:03"),
             (ev2(3), "P4", "Tanpa rompi", "09:12:26"), (ev2(1), "P3", "Tanpa rompi", "08:47:15")]
    res = "".join(
        f'<section class="card" style="overflow:hidden">{img(snap(e), "100%", 214, "border-radius:0")}'
        f'<div style="padding:12px 14px 14px"><div class="row" style="gap:8px"><b style="font-size:14px">{t}</b>{bd(p, "slate", "person")}'
        f'<span class="mut tn" style="margin-left:auto;font-size:12.5px">{tm}</span></div>'
        f'<div class="row" style="gap:6px;margin-top:6px">{cam("CAM 0003")}<span class="mut" style="font-size:12.5px">Area kerja timur</span></div>'
        f'<div class="row" style="gap:8px;margin-top:12px"><span class="btn sm">{I("play_arrow", True)}Putar klip</span>'
        f'<span class="btn sm">{I("add")}Jadikan insiden</span></div></div></section>' for e, p, t, tm in picks)
    grid = f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">{res}</div>'
    examples = "".join(f'<div class="row" style="gap:10px;padding:9px 0;border-bottom:1px solid var(--hair);font-size:13.5px">{I(ic, False, 19, "var(--text-3)")}<span>“{x}”</span></div>'
                       for ic, x in (("forklift", "forklift lewat 5 km/j minggu ini"), ("do_not_step", "pejalan kaki masuk jalur forklift di dok selatan"),
                                     ("groups", "kerumunan lebih dari 4 orang setelah jam 14"), ("route", "melawan arah di lorong satu arah kemarin"),
                                     ("hourglass_bottom", "orang diam lebih dari 10 menit di staging")))
    saved = "".join(f'<div class="row" style="gap:10px;padding:9px 0;border-bottom:1px solid var(--hair);font-size:13.5px">{I("bookmark", True, 19, "var(--brand)")}'
                    f'<span class="grow">{x}</span>{I("notifications_active" if on else "notifications_off", on, 18, "var(--brand)" if on else "var(--text-3)")}</div>'
                    for x, on in (("APD tidak lengkap · Area kerja timur", True), ("Near miss · semua zona", True), ("Forklift ngebut · dok", False)))
    side = (card("Contoh pertanyaan", examples, icon="lightbulb", cb_style="padding-top:4px") +
            card("Pencarian tersimpan", saved, icon="bookmarks", cb_style="padding-top:4px") +
            f'<section class="card" style="padding:18px;background:linear-gradient(135deg,#eff5ff,#fff);gap:10px">'
            f'<div class="row">{I("bolt", True, 22, "var(--brand)")}<b>Jadikan aturan</b></div>'
            f'<span class="sec" style="font-size:13.5px">Beri tahu Supervisor K3 lewat WhatsApp setiap kali “tanpa rompi di Area kerja timur” terjadi lagi.</span>'
            f'<span class="btn pri" style="align-self:flex-start">{I("add_alert")}Buat aturan dari pencarian ini</span></section>')
    body = (f'<div class="ph"><div><div class="row" style="gap:10px"><h1>Pencarian Kejadian</h1>{poc()}</div>'
            f'<p>Tanya dengan bahasa sehari-hari · AI mencari di semua kamera, kejadian dan rekaman 30 hari</p></div></div>{hero}'
            f'<div style="display:grid;grid-template-columns:1fr 420px;gap:16px;flex:1;min-height:0">{grid}<div class="col" style="gap:16px">{side}</div></div>')
    return app("cari", body, search="")


def p08_laporan() -> str:
    kpis = (kpi("verified_user", "blue", "Skor keselamatan", '82<small>/ 100</small>', f'{up("5 poin")} dari Agustus') +
            kpi("warning", "red", "Nyaris tertabrak", "23", f'{up("31%", True, "down")} dari Agustus (33)') +
            kpi("engineering", "amber", "Kepatuhan APD", "86%", f'{up("4 poin")} · target 95%') +
            kpi("task_alt", "green", "Insiden selesai sesuai SLA", "94%", f'{up("2 poin")} · 241 insiden'))
    rnd = random.Random(7)
    days = [str(d) for d in range(1, 31)]
    helm = [round(min(99, 86 + d * 0.22 + rnd.uniform(-2.2, 2.2)), 1) for d in range(30)]
    rompi = [round(min(98, 78 + d * 0.3 + rnd.uniform(-2.8, 2.8)), 1) for d in range(30)]
    apd = card("Kepatuhan APD harian", lines([("Helm", helm, "var(--s1)"), ("Rompi", rompi, "var(--s2)")], days, 960, 262,
                                              lo=70, hi=100, ticks=3, every=3, ref=("target 95%", 95), fmt=lambda v: f"{v:.0f}%",
                                              tip=(17, 14, 64, "Jumat, 18 Sep")),
               icon="show_chart", right=legend([("Helm", "var(--s1)", "swl"), ("Rompi", "var(--s2)", "swl"), ("Target", "var(--text-2)", "swd")]))
    kinds = card("Pelanggaran per jenis", hbars([("Tanpa rompi", 212), ("Tanpa helm", 164), ("Masuk jalur forklift", 97),
                                                 ("Melawan arah", 61), ("Nyaris tertabrak", 23), ("Forklift ngebut", 9)], label_w=160),
                 icon="format_list_numbered", sub="September", cb_style="padding-top:8px")
    weeks = card("Nyaris tertabrak per minggu", vbars([("Near miss", [8, 6, 5, 3, 1], "var(--s1)")], ["1–7", "8–14", "15–21", "22–28", "29–30"],
                                                       470, 300, ticks=4, ymax=8),
                 icon="bar_chart", sub="cermin dipasang 14 Sep")
    hours = [f"{h:02d}" for h in range(7, 23)]
    dn = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
    rnd = random.Random(3)
    peak = {2: 1.0, 3: 0.8, 7: 0.9, 8: 1.0, 9: 0.6}
    m = [[max(0, round((peak.get(h, 0.25) + rnd.uniform(-0.15, 0.2)) * (0.45 if d >= 5 else 1) * 10)) for h in range(16)] for d in range(7)]
    heat = card("Jam rawan pelanggaran", heatgrid(m, hours, dn, 470, 262, every=3) + f'<div style="margin-top:8px">{ramp_legend("sedikit", "banyak")}</div>',
                icon="calendar_view_week", sub="hari × jam")
    sched = "".join(f'<div class="row" style="gap:12px;padding:9px 0;border-bottom:1px solid var(--hair)"><span class="it {t}" style="width:30px;height:30px">{I(ic, True, 17)}</span>'
                    f'<div class="grow"><b style="font-size:13.5px">{a}</b><div class="mut" style="font-size:12px">{b}</div></div>{bd(f, "slate")}</div>'
                    for ic, t, a, b, f in (("today", "blue", "Laporan akhir shift", "otomatis 15:05 · 23:05 · 07:05 → Manajer Gudang", "PDF"),
                                           ("date_range", "blue", "Ringkasan mingguan manajemen", "Senin 08:00 → Direksi", "PDF"),
                                           ("gavel", "violet", "Laporan bulanan SMK3 (PP 50/2012)", "tanggal 1 → Tim K3", "PDF · XLSX"),
                                           ("workspace_premium", "violet", "Paket bukti audit ISO 45001", "sesuai permintaan auditor", "ZIP")))
    reports = card("Laporan terjadwal", sched, icon="schedule_send", right=f'<span class="lnk">{I("add", size=16)} Jadwal baru</span>', cb_style="padding-top:2px")
    body = (f'<div class="ph"><div><h1>Laporan & Kepatuhan K3</h1><p>Gudang Simulasi A · September 2026 · dibandingkan dengan Agustus</p></div>'
            f'<div class="acts"><span class="flt">{I("calendar_month")}<b>1–30 Sep 2026</b>{I("expand_more")}</span>'
            f'<span class="flt">{I("warehouse")}<b>Gudang Simulasi A</b>{I("expand_more")}</span>'
            f'<span class="btn">{I("schedule_send")}Jadwalkan</span><span class="btn pri">{I("picture_as_pdf")}Unduh PDF</span></div></div>'
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">{kpis}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 560px;gap:16px">{apd}{kinds}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;flex:1;min-height:0">{weeks}{heat}{reports}</div>')
    return app("laporan", body, wm=WM)


def p09_zona() -> str:
    geo = META["plan_raw"]
    zc = {"area": ("#64748b", .10), "vehicle_lane": ("#d97706", .28), "one_way": ("#db2777", .22)}
    shapes = []
    sel_name = "Jalur forklift tengah"
    vb = (296, 250, 600, 641)          # the part of the plan around the lane, its lines and cameras: shown at 1.34x
    k = vb[2] / 804                    # plan pixels per screen pixel: marks keep their screen size
    num_bg = {"area": "#475569", "vehicle_lane": "#b45309", "one_way": "#be185d"}
    for n, z in enumerate(geo["zones"], 1):
        col, a = zc[z["kind"]]
        pts = " ".join(f"{x},{y}" for x, y in z["points"])
        on = z["name"] == sel_name
        dash = f' stroke-dasharray="{7 * k:.1f} {5 * k:.1f}"' if z["kind"] == "area" and not on else ""
        shapes.append(f'<polygon points="{pts}" fill="{col}" fill-opacity="{a + (.14 if on else 0)}" stroke="{"#2563eb" if on else col}" '
                      f'stroke-width="{(3 if on else 2) * k:.2f}"{dash}/>')
        x0, y0 = min(p[0] for p in z["points"]), min(p[1] for p in z["points"])
        x1, y1 = max(p[0] for p in z["points"]), max(p[1] for p in z["points"])
        if on:
            for x, y in z["points"]:
                shapes.append(f'<rect x="{x - 6 * k:.1f}" y="{y - 6 * k:.1f}" width="{12 * k:.1f}" height="{12 * k:.1f}" rx="{2 * k:.1f}" '
                              f'fill="#fff" stroke="#2563eb" stroke-width="{2.5 * k:.2f}"/>')
            shapes.append(f'<g transform="translate({x0},{y1 + 10 * k:.1f}) scale({k:.3f})"><rect width="262" height="32" rx="8" fill="#1d4ed8"/>'
                          f'<text x="12" y="21" style="font-size:14px;font-weight:600;fill:#fff">{sel_name} · 43 × 3 m</text></g>')
        else:
            shapes.append(f'<g transform="translate({x0 + 3 * k:.1f},{y0 + 3 * k:.1f}) scale({k:.3f})"><rect width="22" height="22" rx="6" fill="{num_bg[z["kind"]]}"/>'
                          f'<text x="11" y="15.5" text-anchor="middle" style="font-size:12.5px;font-weight:700;fill:#fff">{n}</text></g>')
    for ln in geo["lines"]:
        (ax, ay), (bx, by) = ln["a"], ln["b"]
        shapes.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="#0f172a" stroke-width="{3 * k:.2f}" stroke-linecap="round"/>')
        shapes.append(f'<circle cx="{ax}" cy="{ay}" r="{4.5 * k:.1f}" fill="#0f172a"/><circle cx="{bx}" cy="{by}" r="{4.5 * k:.1f}" fill="#0f172a"/>')
        letter = ln["name"].split(" ·")[0]
        vert = abs(ax - bx) < abs(ay - by)
        tx, ty = ((ax + 8 * k, (ay + by) / 2 - 11 * k) if vert else ((ax + bx) / 2 - 11 * k, ay - 30 * k))
        shapes.append(f'<g transform="translate({tx:.1f},{ty:.1f}) scale({k:.3f})"><rect width="22" height="22" rx="11" fill="#fff" stroke="#0f172a" stroke-width="2"/>'
                      f'<text x="11" y="15.5" text-anchor="middle" style="font-size:12.5px;font-weight:700;fill:#0f172a">{letter}</text></g>')
    for cid in ("Camera_0001", "Camera_0005", "Camera_0010"):
        x, y = geo["cameras"][cid]
        shapes.append(f'<circle cx="{x}" cy="{y}" r="{8 * k:.1f}" fill="#2563eb" stroke="#fff" stroke-width="{3 * k:.1f}"/>'
                      f'<g transform="translate({x + 12 * k:.1f},{y - 11 * k:.1f}) scale({k:.3f})"><rect width="78" height="22" rx="6" fill="#fff" stroke="#bfdbfe"/>'
                      f'<text x="39" y="15.5" text-anchor="middle" style="font-size:12px;font-weight:600;fill:#1d4ed8">{ops.cam_label(cid)}</text></g>')
    tools = "".join(f'<span style="width:40px;height:40px;border-radius:9px;display:grid;place-items:center;{"background:#eff5ff;color:#2563eb" if on else "color:#475569"}">{I(ic, on)}</span>'
                    for ic, on in (("near_me", False), ("pentagon", True), ("horizontal_rule", False), ("straighten", False), ("delete", False)))
    canvas = (f'<div style="position:relative;width:804px;height:859px;border-radius:10px;overflow:hidden;border:1px solid var(--border);background:#f6f3f0">'
              f'<svg viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" width="804" height="859" style="position:absolute;left:0;top:0">'
              f'<image href="../img/plan_raw.jpg" x="0" y="0" width="1000" height="980"/>{"".join(shapes)}</svg>'
              f'<div style="position:absolute;left:12px;top:12px;background:#fff;border-radius:12px;box-shadow:0 4px 16px rgba(15,23,42,.14);padding:5px;display:flex;flex-direction:column;gap:2px">{tools}</div>'
              f'<div style="position:absolute;right:12px;bottom:12px" class="row"><span class="chip" style="background:#fff">{I("grid_4x4", size=16)}Grid 1 m</span>'
              f'<span class="chip" style="background:#fff">{I("zoom_in", size=16)}{100 * 804 / vb[2]:.0f}%</span></div>'
              f'<div style="position:absolute;right:12px;top:12px;width:150px;height:147px;border-radius:8px;overflow:hidden;border:2px solid #fff;box-shadow:0 4px 16px rgba(15,23,42,.18)">'
              f'<img src="../img/plan_raw.jpg" style="width:150px;height:147px;display:block">'
              f'<span style="position:absolute;left:{150 * vb[0] / 1000:.0f}px;top:{147 * vb[1] / 980:.0f}px;width:{150 * vb[2] / 1000:.0f}px;height:{147 * vb[3] / 980:.0f}px;border:2px solid #2563eb;background:rgba(37,99,235,.08)"></span></div></div>')
    zl = "".join(f'<div class="row" style="gap:9px;padding:7px 8px;border-radius:8px;font-size:13px;{"background:#eff5ff;color:#1d4ed8;font-weight:600" if z["name"] == sel_name else ""}">'
                 f'<b class="tn" style="width:20px;height:20px;border-radius:6px;background:{num_bg[z["kind"]]};color:#fff;display:grid;place-items:center;font-size:11px;flex:none">{n}</b>'
                 f'<span class="ell">{z["name"]}</span></div>' for n, z in enumerate(geo["zones"], 1))
    ll = "".join(f'<div class="row" style="gap:9px;padding:7px 8px;font-size:13px"><b style="width:20px;height:20px;border-radius:50%;border:2px solid #0f172a;display:grid;place-items:center;font-size:11px;flex:none">{ln["name"][0]}</b>'
                 f'<span class="ell">{ln["name"].split(" · ")[1]}</span></div>' for ln in geo["lines"])
    left = (f'<section class="card" style="padding:14px;flex-direction:row;gap:14px">'
            f'<div style="width:186px;flex:none"><div class="sect">Zona (6)</div>{zl}<div class="sect" style="margin-top:14px">Garis hitung (3)</div>{ll}'
            f'<span class="btn sm" style="margin-top:12px">{I("add")}Zona baru</span></div>{canvas}</section>')
    rules = [("do_not_step", "Pejalan kaki masuk jalur", "medium", "orang di dalam zona ≥ 1 dtk", True),
             ("warning", "Nyaris tertabrak", "high", "pejalan ≤ 1,5 m dari forklift bergerak", True),
             ("speed", "Forklift ngebut", "high", "> 5 km/j selama ≥ 1 dtk", True),
             ("engineering", "APD wajib", "medium", "tanpa helm / rompi ≥ 2 dtk", False)]
    rh = "".join(f'<div class="row" style="gap:12px;padding:11px 0;border-bottom:1px solid var(--hair)"><span class="it slate" style="width:32px;height:32px">{I(ic, True, 18)}</span>'
                 f'<div class="grow"><div class="row" style="gap:8px"><b style="font-size:13.5px">{a}</b>{sev(s)}</div><div class="mut" style="font-size:12.5px;margin-top:2px">{c}</div></div>{tg(on)}</div>'
                 for ic, a, s, c, on in rules)
    acts = "".join(f'<div class="row" style="gap:10px;padding:7px 0;font-size:13.5px">{I("check_box" if on else "check_box_outline_blank", on, 20, "var(--brand)" if on else "var(--text-3)")}{a}</div>'
                   for a, on in (("Sorot kamera otomatis di Live Monitoring & Dashboard", True),
                                 ("WhatsApp + push ke Supervisor K3 yang sedang shift", True),
                                 ("Bunyikan sirene lokal lewat webhook", False),
                                 ("Eskalasi ke Manajer Gudang bila belum ditanggapi 5 mnt", True)))
    props = (f'<div class="kv" style="grid-template-columns:120px 1fr"><span>Jenis</span><span><span class="flt" style="height:30px">{I("forklift")}<b>Jalur forklift</b>{I("expand_more")}</span></span>'
             f'<span>Ukuran</span><span>43 × 3 m · 129 m²</span>'
             f'<span>Dilihat oleh</span><span class="row" style="gap:6px">{cam("CAM 0001")}{cam("CAM 0005")}{cam("CAM 0010")}</span>'
             f'<span>Berlaku</span><span><div class="seg"><span class="on">Setiap saat</span><span>Per shift</span><span>Jadwal khusus</span></div></span></div>')
    sim = (f'<div style="margin-top:14px;padding:14px;border-radius:12px;background:var(--surface-2);border:1px solid var(--border)">'
           f'<div class="row" style="gap:10px">{I("science", True, 20, "var(--brand)")}<b style="font-size:13.5px">Uji pada rekaman 7 hari terakhir</b>'
           f'<span class="lnk" style="margin-left:auto">Lihat hasil {I("chevron_right", size=16)}</span></div>'
           f'<div class="row" style="gap:18px;margin-top:10px;font-size:13px"><span><b class="tn" style="font-size:18px">41</b> <span class="mut">peringatan</span></span>'
           f'<span><b class="tn" style="font-size:18px">≈ 6</b> <span class="mut">per hari</span></span>'
           f'<span><b class="tn" style="font-size:18px">3</b> <span class="mut">perlu ditinjau</span></span>'
           f'<span style="margin-left:auto">{spark([5, 7, 6, 9, 4, 3, 7], 120, 30)}</span></div></div>')
    right = card("Jalur forklift tengah", props + f'<div class="sect" style="margin-top:18px">Aturan di zona ini</div>{rh}'
                 f'<div class="sect" style="margin-top:16px">Saat aturan terpicu</div>{acts}{sim}',
                 icon="pentagon", right=f'<span class="bd amber">{I("forklift", True)}zona kendaraan</span>', style="flex:1")
    body = (f'<div class="ph"><div><h1>Zona & Aturan</h1><p>Gambar zona di peta sekali saja · aturan berlaku di semua kamera yang melihat zona itu</p></div>'
            f'<div class="acts"><span class="btn">{I("history")}Riwayat versi</span><span class="btn">{I("science")}Uji pada rekaman</span>'
            f'<span class="btn pri">{I("check")}Simpan & terapkan</span></div></div>'
            f'<div style="display:grid;grid-template-columns:1032px 1fr;gap:16px;flex:1;min-height:0">{left}{right}</div>')
    return app("zona", body)


def p10_kamera() -> str:
    cams = GEO["cameras"]
    crit = GEO["criteria"]
    passed = [c for c, v in cams.items() if v["passed"]]
    med = sorted(cams[c]["labels"]["floor_m_median"] for c in passed)
    median = med[len(med) // 2]
    kpis = (kpi("wifi", "green", "Online", '19<small>/ 19</small>', "semua kamera mengirim gambar") +
            kpi("verified", "blue", "Lolos verifikasi posisi", f'{len(passed)}<small>/ 19</small>', "dipakai di peta & analitik") +
            kpi("error", "red", "Perlu tindakan", f"{19 - len(passed)}", "posisi meleset dari peta") +
            kpi("straighten", "violet", "Selisih posisi median", f'{num(median, 2)} m', f"kamera yang lolos · batas {num(crit['floor_m'], 2)} m"))
    order = sorted(cams, key=lambda c: (cams[c]["passed"], c))
    uses = {"Camera_0003": ["Peta", "APD", "Garis"], "Camera_0001": ["Peta", "Near miss"], "Camera_0005": ["Peta", "Jalur"],
            "Camera_0015": ["Peta", "Garis"], "Camera_0010": ["Peta", "Jalur"]}
    rows = []
    for cid in order[:11]:
        v = cams[cid]
        lab = v["labels"]
        ok = v["passed"]
        verdict = (bd("Lolos", "green", "check_circle") if ok else bd("Gagal", "red", "cancel"))
        why = (f'<span class="mut tn" style="font-size:12.5px">meleset {num(lab["floor_m_median"], 2)} m</span>' if ok else
               f'<span class="tn" style="font-size:12.5px;color:#b42318">{num(lab["floor_m_median"], 2)} m · bias {num(lab["bias_px"], 1)} px</span>')
        use = "".join(f'<span class="cam" style="background:#eff5ff;color:#1d4ed8">{u}</span>' for u in uses.get(cid, ["Peta"] if ok else []))
        if not ok:
            use = '<span class="mut" style="font-size:12.5px">tidak dipakai di peta</span>'
        rows.append(f'<tr class="{"on" if cid == "Camera_0004" else ""}"><td><span class="row" style="gap:10px">{img(f"../img/thumb_{cid[-4:]}.jpg", 64, 36)}'
                    f'<span><b style="font-size:13px">{ops.cam_label(cid)}</b><div class="mut" style="font-size:12px">{CAMNAME[cid]}</div></span></span></td>'
                    f'<td>{status("Online")}</td><td class="tn sec" style="font-size:12.5px">{num(v["mount_height_m"], 1)} m · {num(v["tilt_deg"], 0)}°</td>'
                    f'<td><span class="row" style="gap:8px">{verdict}{why}</span></td><td><span class="row" style="gap:4px">{use}</span></td>'
                    f'<td>{I("more_vert", size=20, color="var(--text-3)")}</td></tr>')
    table = (f'<section class="card" style="flex:1;min-height:0;overflow:hidden"><div class="row" style="padding:12px 16px;gap:8px">'
             f'<span class="inp" style="width:240px">{I("search", size=18)}Cari kamera…</span>'
             f'<span class="flt">Status: <b>Semua</b>{I("expand_more")}</span><span class="flt">Verifikasi: <b>Semua</b>{I("expand_more")}</span>'
             f'<span class="mut" style="margin-left:auto;font-size:12.5px">1920×1080 · 30 fps · RTSP</span></div>'
             f'<table class="tbl"><thead><tr><th>Kamera</th><th>Status</th><th>Tinggi · sudut</th><th>Verifikasi posisi</th><th>Dipakai untuk</th><th></th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table>'
             f'<div class="row mut" style="padding:12px 16px;font-size:12.5px;margin-top:auto;border-top:1px solid var(--hair)">Menampilkan 11 dari 19 kamera'
             f'<span style="margin-left:auto" class="row">{I("chevron_left", size=18)}1 / 2{I("chevron_right", size=18)}</span></div></section>')
    c4 = cams["Camera_0004"]
    c3 = cams["Camera_0003"]
    detail = card("Verifikasi posisi · CAM 0004",
                  f'{img("../img/calib_0004.jpg", "100%", 262)}'
                  f'<div class="mut" style="font-size:12px;margin-top:8px" class="row">Silang = kaki orang di gambar · lingkaran = posisi menurut kalibrasi · garis = selisihnya</div>'
                  f'<div class="row" style="gap:10px;margin-top:14px">{bd("Gagal", "red", "cancel")}<b style="font-size:14px">Meleset {num(c4["labels"]["floor_m_median"], 2)} m di lantai</b>'
                  f'<span class="mut" style="font-size:12.5px">batas {num(crit["floor_m"], 2)} m</span></div>'
                  f'<div class="sec" style="font-size:13px;margin-top:6px">Semua titik bergeser ke arah yang sama (bias {num(c4["labels"]["bias_px"], 1)} px): '
                  f'tinggi atau sudut kamera yang tercatat ({num(c4["mount_height_m"], 2)} m · {num(c4["tilt_deg"], 0)}°) kemungkinan tidak sesuai pemasangan.</div>'
                  f'<div class="row" style="gap:12px;margin-top:14px;padding:10px;border-radius:10px;background:var(--surface-2);border:1px solid var(--border)">'
                  f'{img("../img/calib_0003.jpg", 128, 72)}<div style="font-size:12.5px"><div class="row" style="gap:6px">{bd("Lolos", "green", "check_circle")}<b>CAM 0003 sebagai pembanding</b></div>'
                  f'<div class="mut" style="margin-top:4px">meleset {num(c3["labels"]["floor_m_median"], 2)} m · bias {num(c3["labels"]["bias_px"], 1)} px: kaki dan lingkaran bertemu</div></div></div>'
                  f'<div class="sect" style="margin-top:12px">Langkah perbaikan</div>'
                  + "".join(f'<div class="row" style="gap:10px;padding:5px 0;font-size:13px"><b class="tn" style="width:22px;height:22px;border-radius:50%;background:#eff5ff;color:#1d4ed8;display:grid;place-items:center;font-size:12px">{k}</b>{x}</div>'
                            for k, x in enumerate(("Ukur ulang tinggi & sudut pemasangan", "Tandai 4 titik lantai yang jaraknya diketahui",
                                                   "Jalankan verifikasi ulang (± 2 menit, otomatis)"), 1))
                  + f'<div class="row" style="gap:8px;margin-top:14px"><span class="btn pri">{I("ads_click")}Mulai kalibrasi 4 titik</span>'
                    f'<span class="btn">{I("visibility_off")}Keluarkan dari peta</span></div>',
                  icon="straighten", right=poc(), style="flex:1")
    body = (f'<div class="ph"><div><div class="row" style="gap:10px"><h1>Kamera & Kalibrasi</h1>{poc()}</div>'
            f'<p>19 kamera · setiap kamera diuji otomatis: apakah posisi orang di gambar jatuh di tempat yang benar di peta</p></div>'
            f'<div class="acts"><span class="btn">{I("refresh")}Verifikasi ulang semua</span><span class="btn pri">{I("add")}Tambah kamera (RTSP / ONVIF)</span></div></div>'
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">{kpis}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 600px;gap:16px;flex:1;min-height:0">{table}{detail}</div>')
    return app("kamera", body)


def p11_notif() -> str:
    chans = [("chat", "green", "WhatsApp Business", "Terhubung · nomor resmi perusahaan", True),
             ("mail", "blue", "Email", "Terhubung · 12 penerima", True),
             ("notifications_active", "violet", "Push aplikasi", "28 perangkat terdaftar", True),
             ("send", "cyan", "Telegram", "Belum diatur", False),
             ("webhook", "slate", "Webhook / sirene", "2 endpoint · sirene dok", True),
             ("sms", "amber", "SMS", "Add-on · cadangan bila internet putus", False)]
    ch = "".join(f'<div class="row" style="gap:12px;padding:14px;border:1px solid var(--border);border-radius:12px">'
                 f'<span class="it {t}">{I(ic, True, 19)}</span><div class="grow"><b style="font-size:13.5px">{a}</b>'
                 f'<div class="mut" style="font-size:12px">{b}</div></div>{tg(on)}</div>' for ic, t, a, b, on in chans)
    channels = card("Saluran", f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">{ch}</div>', icon="hub")

    def who(roles):
        return "".join(f'<span class="row" style="gap:6px;padding:3px 0;font-size:13px">{bd(r, tone)}{"".join(I(x, False, 17, "var(--text-3)") for x in via)}</span>'
                       for r, tone, via in roles)
    mtx = [("high", who([("Operator CCTV", "amber", ["desktop_windows"]), ("Supervisor K3 shift", "green", ["chat", "notifications_active"])]),
            who([("Manajer Gudang", "blue", ["chat", "call"])]), who([("Kepala HSE", "violet", ["mail", "chat"])]), "Laporan harian"),
           ("medium", who([("Supervisor K3 shift", "green", ["notifications_active"])]), who([("Supervisor K3 shift", "green", ["chat"])]),
            who([("Manajer Gudang", "blue", ["chat"])]), "Laporan harian"),
           ("low", who([("Operator CCTV", "amber", ["desktop_windows"])]), '<span class="mut">—</span>', '<span class="mut">—</span>', "Ringkasan per jam"),
           ("info", '<span class="mut">tidak dikirim</span>', '<span class="mut">—</span>', '<span class="mut">—</span>', "Ringkasan shift")]
    rows = "".join(f'<tr><td>{sev(s)}</td><td>{a}</td><td>{b}</td><td>{c}</td><td class="sec">{d}</td></tr>' for s, a, b, c, d in mtx)
    matrix = card("Matriks eskalasi", f'<table class="tbl"><thead><tr><th>Tingkat</th><th>Langsung</th><th>Belum ditanggapi 5 mnt</th>'
                                      f'<th>Belum ditanggapi 15 mnt</th><th>Ringkasan</th></tr></thead><tbody>{rows}</tbody></table>',
                  icon="trending_up", right='<span class="mut">berlaku untuk semua zona · bisa diatur per aturan</span>', cb_style="padding:10px 0 4px")
    quiet = card("Ringkasan & jam tenang", "".join(
        f'<div class="row" style="gap:12px;padding:10px 0;border-bottom:1px solid var(--hair)">{I(ic, False, 20, "var(--text-3)")}<div class="grow"><b style="font-size:13.5px">{a}</b>'
        f'<div class="mut" style="font-size:12.5px">{b}</div></div>{tg(on)}</div>'
        for ic, a, b, on in (("summarize", "Ringkasan akhir shift", "15:05 · 23:05 · 07:05 → Manajer Gudang (WhatsApp + PDF)", True),
                             ("event_note", "Ringkasan mingguan", "Senin 08:00 → Direksi (email)", True),
                             ("bedtime", "Jam tenang untuk Rendah & Info", "22:00–06:00 · Tinggi & Sedang tetap dikirim", True),
                             ("group_off", "Jangan kirim ke pengguna yang sedang cuti", "mengikuti jadwal shift dari HRIS", False))),
        icon="tune", cb_style="padding-top:2px")
    bubble = (f'<div style="background:#eef2f6;border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:10px">'
              f'<div class="row" style="gap:10px;padding-bottom:10px;border-bottom:1px solid var(--border)"><span class="logo" style="width:36px;height:36px">{I("warehouse", True, 20)}</span>'
              f'<div><b style="font-size:14px">Live Ops · Notifikasi</b><div class="mut" style="font-size:12px">akun bisnis terverifikasi</div></div></div>'
              f'<div style="background:#fff;border-radius:12px;padding:8px;box-shadow:0 1px 1px rgba(0,0,0,.06);max-width:330px">'
              f'{img(snap(ev1(0)), "100%", 176)}<div style="padding:8px 4px 2px;font-size:13.5px;line-height:1.5">'
              f'<b style="color:#b42318">⚠ TINGGI · Nyaris tertabrak forklift</b><br>Gudang Simulasi A · CAM 0001 Area konveyor barat<br>'
              f'P14 & forklift F12 · 10:41:58<br><span class="mut">Balas 1 = saya tangani · 2 = alarm palsu</span>'
              f'<div class="mut tn" style="text-align:right;font-size:11px">10:41 ✓✓</div></div></div>'
              f'<div class="row" style="gap:8px">' + "".join(f'<span style="flex:1;text-align:center;background:#fff;border-radius:10px;padding:9px 0;color:var(--brand);font-weight:600;font-size:13px">{x}</span>'
                                                         for x in ("Saya tangani", "Alarm palsu", "Lihat bukti")) + '</div>'
              f'<div style="align-self:flex-end;background:#dbe8fe;border-radius:12px;padding:8px 12px;font-size:13.5px">1<div class="mut tn" style="font-size:11px;text-align:right">10:42 ✓✓</div></div>'
              f'<div style="background:#fff;border-radius:12px;padding:8px 12px;font-size:13.5px;max-width:300px">Tercatat: INS-0142 ditangani Budi Santoso. SLA tanggap terpenuhi (33 dtk).'
              f'<div class="mut tn" style="font-size:11px;text-align:right">10:42</div></div></div>')
    preview = card("Pratinjau pesan", bubble, icon="preview", sub="WhatsApp · tingkat Tinggi")
    log = card("Riwayat pengiriman", "".join(
        f'<div class="row" style="gap:10px;padding:7px 0;font-size:13px;border-bottom:1px solid var(--hair)"><span class="tn mut" style="width:62px">{t}</span>'
        f'{I(ic, False, 18, "var(--text-3)")}<span class="grow ell">{a}</span>{bd(b, tone)}</div>'
        for t, ic, a, b, tone in (("10:41:59", "chat", "WhatsApp → Budi Santoso", "dibaca", "green"),
                                  ("10:41:59", "notifications_active", "Push → 3 perangkat", "terkirim", "green"),
                                  ("10:41:59", "desktop_windows", "Sorotan → ruang kontrol", "tampil", "green"),
                                  ("10:38:21", "notifications_active", "Push → Agus Prasetyo", "terkirim", "green"))),
        icon="receipt_long", cb_style="padding-top:2px", style="flex:1")
    body = (f'<div class="ph"><div><h1>Notifikasi & Eskalasi</h1><p>Siapa diberi tahu, lewat saluran apa, dan kapan dinaikkan bila belum ditanggapi</p></div>'
            f'<div class="acts"><span class="btn">{I("send")}Kirim pesan uji</span><span class="btn pri">{I("check")}Simpan</span></div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 450px;gap:16px;flex:1;min-height:0">'
            f'<div class="col" style="gap:16px">{channels}{matrix}{quiet}</div><div class="col" style="gap:16px">{preview}{log}</div></div>')
    return app("notif", body, wm=WM_POC)


def p12_pengguna() -> str:
    users = [("Rina Hartono", "Admin", "blue", "Semua lokasi", True, "aktif sekarang"),
             ("Hendra Wijaya", "Admin", "blue", "Semua lokasi", True, "kemarin"),
             ("Budi Santoso", "Supervisor K3", "green", "Gudang Simulasi A", True, "2 mnt lalu"),
             ("Agus Prasetyo", "Supervisor K3", "green", "Gudang Simulasi A", True, "5 mnt lalu"),
             ("Fajar Nugroho", "Supervisor K3", "green", "DC Surabaya", True, "1 jam lalu"),
             ("Siti Rahma", "Operator CCTV", "amber", "Gudang Simulasi A", True, "aktif sekarang"),
             ("Dimas Saputra", "Operator CCTV", "amber", "Gudang Simulasi A", True, "1 jam lalu"),
             ("Yuni Kartika", "Operator CCTV", "amber", "DC Cikarang", None, "undangan terkirim"),
             ("Maya Putri", "Viewer / Manajemen", "slate", "Semua lokasi", True, "3 hari lalu"),
             ("Andi Kurniawan", "Viewer / Manajemen", "slate", "DC Cikarang", True, "1 minggu lalu")]
    rows = "".join(
        f'<tr><td><span class="row" style="gap:10px">{avatar(n, 32)}<span><b style="font-size:13.5px">{n}</b>'
        f'<div class="mut" style="font-size:12px">{n.split()[0].lower()}.{n.split()[1][0].lower()}@contohlogistik.id</div></span></span></td>'
        f'<td>{bd(r, t)}</td><td class="sec">{loc}</td>'
        f'<td>{bd("2FA aktif", "green", "verified_user") if fa else bd("menunggu", "slate", "schedule")}</td>'
        f'<td class="sec">{last}</td><td>{I("more_vert", size=20, color="var(--text-3)")}</td></tr>'
        for n, r, t, loc, fa, last in users)
    tabs = ('<div class="tabs"><span class="on">Pengguna <span class="n">28</span></span><span>Peran & izin <span class="n">4</span></span>'
            '<span>Undangan <span class="n">2</span></span><span>Log audit</span></div>')
    table = (f'<section class="card" style="flex:1">{tabs}<div class="row" style="padding:12px 18px;gap:8px">'
             f'<span class="inp" style="width:280px">{I("search", size=18)}Cari nama atau email…</span>'
             f'<span class="flt">Peran: <b>Semua</b>{I("expand_more")}</span><span class="flt">Lokasi: <b>Semua</b>{I("expand_more")}</span></div>'
             f'<table class="tbl"><thead><tr><th>Pengguna</th><th>Peran</th><th>Akses lokasi</th><th>Keamanan</th><th>Terakhir aktif</th><th></th></tr></thead>'
             f'<tbody>{rows}</tbody></table></section>')
    roles = "".join(f'<div class="row" style="gap:12px;padding:10px 0;border-bottom:1px solid var(--hair)"><span class="it {r[2]}" style="width:32px;height:32px">{I(r[0], True, 18)}</span>'
                    f'<div class="grow"><b style="font-size:13.5px">{r[1]}</b><div class="mut" style="font-size:12px">{d}</div></div><b class="tn">{c}</b></div>'
                    for r, d, c in ((ROLES[1], "semua menu, pengguna, kamera, aturan, tagihan", 2),
                                    (ROLES[2], "insiden, laporan, usul aturan · per lokasi", 6),
                                    (ROLES[3], "live, konfirmasi & buat insiden · per lokasi", 14),
                                    (ROLES[4], "dashboard & laporan, hanya lihat", 6)))
    rolec = card("Peran di organisasi ini", roles + f'<div class="mut" style="font-size:12px;margin-top:10px">{I("lock", True, 15)} Super Admin ada di sisi vendor dan tidak termasuk pengguna Anda.</div>',
                 icon="badge", right=f'<span class="lnk">Kelola {I("chevron_right", size=16)}</span>', cb_style="padding-top:4px")
    sec = card("Keamanan", "".join(f'<div class="row" style="gap:12px;padding:9px 0;border-bottom:1px solid var(--hair)">{I(ic, False, 20, "var(--text-3)")}'
                                   f'<div class="grow"><b style="font-size:13.5px">{a}</b><div class="mut" style="font-size:12px">{b}</div></div>{tg(on)}</div>'
                                   for ic, a, b, on in (("key", "Masuk dengan SSO", "Google Workspace · Microsoft Entra ID", True),
                                                        ("verified_user", "Wajib 2FA", "untuk Admin & Supervisor", True),
                                                        ("timer", "Keluar otomatis", "setelah 30 menit tidak aktif", True))),
               icon="security", cb_style="padding-top:2px")
    audit = card("Log audit terbaru", "".join(
        f'<div class="row" style="gap:10px;padding:8px 0;border-bottom:1px solid var(--hair);align-items:flex-start;font-size:13px">'
        f'<span class="tn mut" style="width:58px;flex:none">{t}</span><span class="grow">{x}</span></div>'
        for t, x in (("10:42", "<b>Budi Santoso</b> mengubah INS-0142 → Ditangani"),
                     ("09:12", "<b>Rina Hartono</b> mengubah aturan “Forklift ngebut” 6 → 5 km/j"),
                     ("07:02", "<b>Sistem</b>: CAM 0004 gagal verifikasi posisi"),
                     ("Kemarin", f'<span style="color:#5b21b6">{I("lock", True, 15)} <b>Dukungan platform</b> masuk sebagai tenant selama 30 mnt, atas izin Rina Hartono</span>'))),
        icon="history", cb_style="padding-top:2px", style="flex:1")
    body = (f'<div class="ph"><div><h1>Pengguna & Peran</h1><p>28 pengguna · 4 peran di organisasi · SSO & 2FA aktif</p></div>'
            f'<div class="acts"><span class="btn">{I("badge")}Kelola peran</span><span class="btn pri">{I("person_add")}Undang pengguna</span></div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 520px;gap:16px;flex:1;min-height:0">{table}'
            f'<div class="col" style="gap:16px">{rolec}{sec}{audit}</div></div>')
    return app("pengguna", body, wm=WM)


def annotated(src: str, title: str, sub: str, view: int, notes: list[tuple]) -> str:
    """A frame of the dashboard video, numbered, with what each part is for."""
    s = 1584 / 1920
    marks = "".join(f'<span class="mk" style="left:{24 + x * s - 15:.0f}px;top:{96 + y * s - 15:.0f}px">{k}</span>'
                    for k, (x, y, _, _) in enumerate(notes, 1))
    items = "".join(f'<div style="display:flex;gap:12px"><span class="mk" style="position:static;flex:none">{k}</span><div><b style="font-size:15px;color:#e9eef4">{a}</b>'
                    f'<div style="color:#9ba9b8;font-size:13px;margin-top:3px;line-height:1.45">{b}</div></div></div>'
                    for k, (_, _, a, b) in enumerate(notes, 1))
    tabs = "".join(f'<span style="color:{"#e9eef4" if k == view else "#657485"};font-weight:{600 if k == view else 500}">{name}</span>'
                   for k, (_, name) in enumerate(DASH_TABS))
    css = (".mk{position:absolute;width:30px;height:30px;border-radius:50%;background:#3b82f6;color:#fff;font-weight:700;font-size:15px;"
           "display:grid;place-items:center;box-shadow:0 0 0 3px #05080c,0 4px 12px rgba(0,0,0,.5);z-index:3}")
    body = (f'<div style="position:absolute;left:24px;top:22px;right:24px;display:flex;align-items:center;gap:14px">'
            f'<span class="bd" style="background:#1e3a8a;color:#bfdbfe;height:26px">{I("tv", True)}REALTIME DASHBOARD · TAMPILAN {view + 1}/6</span>'
            f'<b style="font-size:22px;color:#e9eef4">{title}</b><span style="color:#9ba9b8;font-size:15px">{sub}</span>'
            f'<span style="margin-left:auto;display:flex;gap:18px;font-size:13px">{tabs}</span></div>'
            f'<img src="{src}" style="position:absolute;left:24px;top:96px;width:1584px;height:891px;border-radius:10px;box-shadow:0 0 0 1px #232f3d">'
            f'{marks}<div style="position:absolute;left:1640px;top:96px;width:256px;display:flex;flex-direction:column;gap:20px">{items}</div>'
            f'<div style="position:absolute;left:24px;top:1003px;color:#9ba9b8;font-size:13px">Cuplikan langsung dari video PoC (rekaman diputar ulang). '
            f'Pada produk: layar ruang kontrol / TV, berganti tampilan otomatis, data langsung dari edge box.</div>')
    return doc(body + f'<div class="wm" style="color:#657485">{WM_POC}</div>', cls="dk", extra_css=css + "body{background:#05080c}")


def p13_command() -> str:
    return annotated("../../docs/video1_spotlight.jpg", "Command Center", "semua kamera, satu peta, satu feed", 0, [
        (16, 68, "KPI langsung", "Orang, forklift bergerak & utilisasi, near miss, masuk jalur, ngebut, kerumunan."),
        (16, 168, "Video wall dengan AI", "Kotak terkunci pada orang & forklift, ID sama di semua kamera."),
        (590, 496, "Sorotan otomatis", "Kamera yang melihat bahaya dipanggil ke layar saat alert, lalu kembali sendiri."),
        (1164, 168, "Peta lantai langsung", "Posisi semua orang & forklift dalam meter dari 15 kamera; titik near miss dan kameranya."),
        (16, 824, "Feed kejadian", "Foto bukti, siapa, di mana, kamera mana."),
        (16, 1024, "Lini masa", "Setiap kejadian di garis waktu; klik untuk lompat ke detiknya.")])


def p14_fokus() -> str:
    return annotated("../../docs/video2_one_camera.jpg", "Fokus Kamera / Zona", "satu area yang paling ramai, detail per orang", 1, [
        (16, 68, "Kamera besar + APD", "Helm & rompi tiap orang, zona dan garis hitung digambar di lantai."),
        (1308, 68, "KPI area", "Orang di kamera, APD lengkap, peringatan APD, melintasi garis, melawan arah."),
        (1308, 368, "Posisi di denah", "Orang di kamera ini, di peta lantai."),
        (16, 800, "Zona yang diawasi", "Jumlah orang dan lama tinggal per zona."),
        (662, 800, "Tren 30 detik", "Orang di kamera dari waktu ke waktu."),
        (1308, 712, "Feed kejadian", "Pelanggaran terbaru dengan foto.")])


def p15_apd() -> str:
    return annotated("../../docs/video3_real.jpg", "Kepatuhan APD", "gudang nyata, 3 kamera terverifikasi", 2, [
        (16, 68, "KPI APD", "Orang di area, APD lengkap, peringatan, robot AMR, diam lama, kamera dipakai."),
        (16, 168, "Kamera dengan status APD", "Dua lencana per orang: helm dan rompi."),
        (666, 540, "Satu orang = satu baris", "Orang yang sama dari 3 kamera digabung; status APD & aktivitasnya."),
        (16, 910, "Status sistem", "Kamera yang dipakai, yang ditolak, dan alasannya."),
        (1316, 168, "Feed kejadian", "Tanpa helm / rompi, kerumunan, diam lama.")])


def p16_keselamatan() -> str:
    kp = "".join(kpi(*k) for k in (
        ("warning", "red", "Near miss hari ini", "3", "rata-rata 7 hari: 5"),
        ("engineering", "amber", "Pelanggaran APD", "41", "shift ini · 86% patuh"),
        ("do_not_step", "amber", "Masuk jalur forklift", "12", "8 di persimpangan C"),
        ("speed", "red", "Forklift ngebut", "2", "> 5 km/j ≥ 1 dtk"),
        ("timer", "blue", "Waktu tanggap median", "3:40", "menit · target 15"),
        ("verified_user", "green", "Skor keselamatan", "82", f'{up("5")} dari minggu lalu')))
    hrs = [f"{h:02d}" for h in range(7, 15)]
    nm = card("Near miss per jam", vbars([("Hari ini", [0, 1, 0, 1, 1, 0, 0, 0], "var(--s1)")], hrs, 900, 318,
                                         avg=("Rata-rata 7 hari", [0.4, 0.9, 1.1, 0.7, 0.6, 0.5, 0.8, 0.6]), ymax=2, ticks=2,
                                         fmt=lambda v: num(v, 0) if v == int(v) else num(v, 1), tip=(3, 18, 30, "10:00–11:00")),
              icon="bar_chart", right=legend([("Hari ini", "var(--s1)"), ("Rata-rata 7 hari", "var(--text-2)", "swd")]))
    hot = card("Titik rawan", f'<div class="row" style="gap:16px;align-items:stretch"><div style="width:540px;height:318px;border-radius:10px;overflow:hidden;background:#0a0e13;flex:none">'
                              f'<img src="../img/plan_heat.png" style="width:900px;margin:-330px 0 0 -330px;display:block"></div><div class="grow col" style="gap:12px">'
                              + "".join(f'<div class="row" style="gap:10px;align-items:flex-start"><b class="tn" style="width:24px;height:24px;border-radius:7px;background:var(--surface-2);display:grid;place-items:center;font-size:12px">{k}</b>'
                                        f'<div><b style="font-size:14px">{a}</b><div class="mut" style="font-size:12.5px">{b}</div></div></div>'
                                        for k, (a, b) in enumerate([("Persimpangan jalur forklift", "3 near miss · 18 masuk jalur"), ("Area kerja timur", "padat 09:00–10:00 · APD 78%"),
                                                                    ("Lorong satu arah", "11 melawan arah")], 1))
                              + f'<div class="mut" style="font-size:12px;margin-top:auto">Heatmap = kepadatan orang; lingkaran merah = near miss; jingga = masuk jalur.</div></div></div>',
               icon="local_fire_department")
    kinds = card("Pelanggaran per jenis · shift ini", hbars([("Tanpa rompi", 22), ("Tanpa helm", 19), ("Masuk jalur forklift", 12),
                                                             ("Melawan arah", 7), ("Nyaris tertabrak", 3), ("Forklift ngebut", 2)], label_w=160)
                 + '<div class="mut" style="font-size:12px;margin-top:12px;line-height:1.5">Shift pagi sejak 07:00. Klik baris untuk melihat semua kejadian jenis itu dengan foto bukti.</div>',
                 icon="format_list_numbered", cb_style="padding-top:8px")
    shifts = card("Kepatuhan APD per shift", vbars([("Helm", [91, 88, 84], "var(--s1)"), ("Rompi", [83, 80, 76], "var(--s2)")],
                                                   ["Pagi", "Siang", "Malam"], 560, 290, ymax=100, ticks=4, fmt=lambda v: f"{v:.0f}%"),
                  icon="groups", right=legend([("Helm", "var(--s1)"), ("Rompi", "var(--s2)")]))
    inc = card("Insiden terbuka", "".join(
        f'<div class="ev">{img(snap(e), 84, 47)}<div class="grow"><div class="t1" style="font-size:13px">{t}</div>'
        f'<div class="t2">{d}</div></div>{sev(s)}<span class="tn mut" style="font-size:12px;width:44px;text-align:right">{tm}</span></div>'
        for e, t, d, s, tm in ((ev1(0), "Nyaris tertabrak forklift", "P14 & F12 · Budi S.", "high", "10:41"),
                               (ev2(14), "Melawan arah", "P72 · belum ditugaskan", "medium", "10:38"),
                               (ev2(12), "Tanpa helm & rompi", "P67 · Agus P.", "medium", "10:37"),
                               (ev1(1), "Pejalan kaki di jalur forklift", "P18 · Siti R.", "medium", "10:31"),
                               (ev2(13), "Tanpa rompi", "P66 · Agus P.", "medium", "10:24"))),
              icon="notification_important", right='<span class="bd red">7 terbuka</span>', cb_style="padding-top:2px")
    body = (f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px">{kp}</div>'
            f'<div style="display:grid;grid-template-columns:950px 1fr;gap:12px">{nm}{hot}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 600px 1fr;gap:12px;flex:1;min-height:0">{kinds}{shifts}{inc}</div>')
    return dash(3, ("Gudang Simulasi A", "Analitik keselamatan"), body)


def p17_operasional() -> str:
    kp = "".join(kpi(*k) for k in (
        ("groups", "cyan", "Orang di lantai", "31", "puncak 52 · 09:15"),
        ("forklift", "amber", "Forklift bergerak", '3<small>/ 5</small>', "utilisasi 62%"),
        ("route", "blue", "Jarak tempuh forklift", '18,4<small>km</small>', "shift ini"),
        ("swap_horiz", "violet", "Melintasi garis", "1.476", "A 817 · B 462 · C 197"),
        ("hourglass_bottom", "slate", "Diam di staging", '4<small>mnt</small>', "rata-rata per orang"),
        ("pallet", "amber", "Pallet truck aktif", '2<small>/ 3</small>', "1 parkir 40 mnt")))
    t = [f"{h:02d}:00" for h in range(7, 15)]
    lbl = [f"{7 + i // 4:02d}:{(i % 4) * 15:02d}" for i in range(29)]
    today = [24, 28, 31, 33, 36, 39, 41, 44, 47, 52, 49, 46, 41, 37, 31] + [None] * 14
    yday = [22, 25, 29, 31, 34, 37, 40, 42, 45, 47, 46, 44, 41, 39, 37, 36, 38, 40, 42, 43, 41, 39, 37, 35, 33, 31, 29, 27, 25]
    ppl = card("Orang di lantai", lines([("Hari ini", today, "var(--s1)"), ("Kemarin", yday, "var(--text-3)", True)], lbl, 900, 318,
                                        hi=60, ticks=3, every=4, area=True, tip=(9, 14, 22, "09:15")),
               icon="show_chart", right=legend([("Hari ini", "var(--s1)", "swl"), ("Kemarin", "var(--text-3)", "swd")]))
    util = card("Utilisasi per forklift · shift ini", hbars([("F12", 74), ("F13", 69), ("F10", 61), ("F23", 58), ("F54", 47), ("F56", 33)],
                                                          vmax=100, fmt=lambda v: f"{v}%", label_w=60)
                + '<div class="mut" style="font-size:12px;margin-top:8px">Utilisasi = waktu bergerak ÷ waktu terlihat kamera. F56 lebih banyak diam: kandidat dipindah ke shift siang.</div>',
                icon="forklift", cb_style="padding-top:10px")
    flow = card("Arus melewati garis hitung", vbars([("Masuk", [412, 233, 96], "var(--s1)"), ("Keluar", [405, 229, 101], "var(--s2)")],
                                                    ["A · Lintasan timur", "B · Area kerja", "C · Penyeberangan"], 600, 290, ticks=4),
                icon="swap_horiz", right=legend([("Masuk", "var(--s1)"), ("Keluar", "var(--s2)")]))
    dens = card("Kepadatan per zona", hbars([("Area kerja timur", 7.4), ("Area utara", 4.1), ("Staging A", 2.6), ("Area selatan", 1.9),
                                            ("Jalur forklift tengah", 0.4)], fmt=lambda v: num(v, 1), label_w=150)
                + '<div class="mut" style="font-size:12px;margin-top:8px">rata-rata orang di zona selama shift</div>',
                icon="dashboard_customize", cb_style="padding-top:10px")
    mp = card("Posisi langsung", f'<div style="border-radius:10px;overflow:hidden;height:290px;background:#0a0e13">'
                                 f'<img src="../img/plan_live_24.png" style="width:900px;margin:-320px 0 0 -330px;display:block"></div>',
              icon="map", right='<span class="mut">15 kamera</span>')
    body = (f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px">{kp}</div>'
            f'<div style="display:grid;grid-template-columns:950px 1fr;gap:12px">{ppl}{util}</div>'
            f'<div style="display:grid;grid-template-columns:640px 1fr 1fr;gap:12px;flex:1;min-height:0">{flow}{dens}{mp}</div>')
    return dash(4, ("Gudang Simulasi A", "Analitik operasional"), body)


def p18_multi() -> str:
    sites = [("Gudang Simulasi A", "Simulasi · PoC", 19, 82, 3, 86, 7, "1 tinggi", "amber"),
             ("DC Cikarang", "Jawa Barat", 24, 88, 1, 92, 3, None, "green"),
             ("DC Surabaya", "Jawa Timur", 18, 71, 2, 79, 9, "1 tinggi", "red"),
             ("Cold Storage Bekasi", "Jawa Barat", 12, 90, 0, 95, 1, None, "green"),
             ("DC Medan", "Sumatera Utara", 13, 84, 1, 88, 4, None, "green")]
    cards_ = "".join(
        f'<section class="card" style="padding:16px 18px;gap:10px;{"box-shadow:inset 0 0 0 1px #ef4444" if tone == "red" else ""}">'
        f'<div class="row"><span class="it {"red" if tone == "red" else "blue"}">{I("warehouse", True, 19)}</span><div class="grow"><b style="font-size:15px">{n}</b>'
        f'<div class="mut" style="font-size:12px">{reg} · {c} kamera</div></div></div>'
        f'<div class="row" style="align-items:baseline;gap:8px"><b class="tn" style="font-size:34px">{s}</b><span class="mut">skor keselamatan</span></div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:12px" class="sec">'
        f'<div><b class="tn" style="font-size:16px;color:var(--text);display:block">{nm}</b>near miss</div>'
        f'<div><b class="tn" style="font-size:16px;color:var(--text);display:block">{apd}%</b>APD</div>'
        f'<div><b class="tn" style="font-size:16px;color:var(--text);display:block">{op}</b>terbuka</div></div>'
        f'<div>{bd(hi, "red", "error") if hi else bd("tidak ada insiden tinggi", "green", "check_circle")}</div></section>'
        for n, reg, c, s, nm, apd, op, hi, tone in sites)
    kp = "".join(kpi(*k) for k in (
        ("apartment", "blue", "Lokasi", "5", "86 kamera · 79 dipakai di peta"),
        ("warning", "red", "Near miss hari ini", "7", f'{up("22%", True, "down")} dari rata-rata'),
        ("engineering", "amber", "Kepatuhan APD", "88%", "rata-rata 5 lokasi"),
        ("error", "red", "Insiden tinggi terbuka", "2", "Gudang Simulasi A · DC Surabaya"),
        ("timer", "green", "Waktu tanggap median", "4:10", "menit · semua lokasi")))
    wk = [f"M{w}" for w in range(29, 41)]
    rnd = random.Random(5)
    base = {"Gudang Simulasi A": 72, "DC Cikarang": 80, "DC Surabaya": 74, "Cold Storage Bekasi": 85, "DC Medan": 77}
    end = {n: s for n, _, _, s, *_ in sites}
    cols = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)", "var(--s5)"]
    series = []
    for k, (n, *_) in enumerate(sites):
        vals = [round(base[n] + (end[n] - base[n]) * i / 11 + rnd.uniform(-2.5, 2.5)) for i in range(11)] + [end[n]]
        series.append((n, vals, cols[k]))
    trend = card("Skor keselamatan 12 minggu", lines(series, wk, 1060, 462, lo=60, hi=100, ticks=4, every=1),
                 icon="show_chart", right=legend([(n, c, "swl") for n, _, c in series]))
    rank = sorted(sites, key=lambda s: -s[3])
    rt = "".join(f'<tr><td class="tn mut">{k}</td><td><b>{s[0]}</b></td><td class="tn" style="font-weight:600">{s[3]}</td>'
                 f'<td class="tn">{s[4]}</td><td class="tn">{s[5]}%</td><td class="tn">{s[6]}</td></tr>' for k, s in enumerate(rank, 1))
    ranking = card("Peringkat lokasi", f'<table class="tbl"><thead><tr><th>#</th><th>Lokasi</th><th>Skor</th><th>Near miss</th><th>APD</th><th>Terbuka</th></tr></thead>'
                                       f'<tbody>{rt}</tbody></table>', icon="leaderboard", cb_style="padding:10px 0 4px")
    watch = card("Perlu perhatian HQ", "".join(
        f'<div class="ev"><span class="it {t}" style="width:30px;height:30px">{I(ic, True, 17)}</span><div class="grow"><div class="t1" style="font-size:13px">{a}</div>'
        f'<div class="t2">{b}</div></div><span class="tn mut" style="font-size:12px">{c}</span></div>'
        for ic, t, a, b, c in (("warning", "red", "Gudang Simulasi A · nyaris tertabrak forklift", "INS-0142 · ditangani Budi S. · CAPA 1/3", "10:41"),
                               ("speed", "red", "DC Surabaya · forklift ngebut di dok", "belum ditanggapi 6 mnt · eskalasi ke Manajer", "10:36"),
                               ("memory", "amber", "DC Surabaya · edge box offline 14 mnt", "16 kamera tanpa analitik · tiket dukungan dibuat", "10:28"))),
        icon="priority_high", cb_style="padding-top:2px", style="flex:1")
    body = (f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px">{kp}</div>'
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px">{cards_}</div>'
            f'<div style="display:grid;grid-template-columns:1110px 1fr;gap:12px;flex:1;min-height:0">{trend}<div class="col" style="gap:12px">{ranking}{watch}</div></div>')
    return dash(5, ("PT Contoh Logistik", "Semua lokasi"), body, wm=WM)


def p19_tenant() -> str:
    kp = (kpi("payments", "violet", "MRR", 'Rp 412<small>jt</small>', f'{up("6,1%")} dari bulan lalu') +
          kpi("domain", "blue", "Tenant aktif", "24", "3 sedang pilot · 0 churn 90 hari") +
          kpi("videocam", "cyan", "Kamera tertagih", "1.284", "di 61 lokasi") +
          kpi("memory", "green", "Edge box online", '59<small>/ 61</small>', "2 offline > 10 mnt") +
          kpi("receipt_long", "amber", "Tagihan jatuh tempo", 'Rp 38<small>jt</small>', "2 tenant · 14 & 21 hari"))
    tenants = [("PT Contoh Logistik", "Keselamatan", 5, 86, 96, ("Aktif", "#079455"), "47,7", 92),
               ("PT Contoh Manufaktur", "Enterprise", 9, 214, 240, ("Aktif", "#079455"), "96,5", 88),
               ("PT Contoh Rantai Dingin", "Keselamatan", 3, 40, 48, ("Aktif", "#079455"), "19,8", 95),
               ("PT Contoh Fulfilment", "Operasional", 4, 72, 80, ("Aktif", "#079455"), "20,1", 81),
               ("PT Contoh Distribusi", "Keselamatan", 2, 31, 32, ("Kuota hampir habis", "#d97706"), "15,4", 90),
               ("PT Contoh Farmasi", "Pilot", 1, 8, 8, ("Pilot hari 18 / 30", "#2563eb"), None, 76),
               ("PT Contoh Ritel", "Operasional", 6, 94, 120, ("Tunggakan 14 hari", "#dc2626"), "26,3", 64),
               ("PT Contoh Otomotif", "Enterprise", 7, 160, 160, ("Aktif", "#079455"), "71,9", 89)]
    plan_tone = {"Keselamatan": "blue", "Enterprise": "violet", "Operasional": "slate", "Pilot": "amber"}
    rows = "".join(
        f'<tr class="{"on" if k == 0 else ""}"><td><span class="row" style="gap:10px"><span class="it slate" style="width:32px;height:32px">{I("domain", True, 18)}</span><b>{n}</b></span></td>'
        f'<td>{bd(p, plan_tone[p])}</td><td class="tn">{l}</td>'
        f'<td style="width:150px"><div class="tn" style="font-size:12.5px">{u} / {q}</div><div class="prog" style="margin-top:5px"><i style="width:{100 * u / q:.0f}%;background:{"#d97706" if u / q > .95 else "var(--s1)"}"></i></div></td>'
        f'<td>{status(st[0], st[1])}</td><td class="tn">{f"Rp {m} jt" if m else "pilot berbayar"}</td>'
        f'<td><span class="tn" style="font-weight:600;color:{"#079455" if h >= 85 else "#d97706" if h >= 70 else "#dc2626"}">{h}</span></td>'
        f'<td>{I("more_vert", size=20, color="var(--text-3)")}</td></tr>'
        for k, (n, p, l, u, q, st, m, h) in enumerate(tenants))
    table = (f'<section class="card" style="flex:1"><div class="row" style="padding:12px 16px;gap:8px">'
             f'<span class="inp" style="width:260px">{I("search", size=18)}Cari tenant…</span>'
             f'<span class="flt">Paket: <b>Semua</b>{I("expand_more")}</span><span class="flt">Status: <b>Semua</b>{I("expand_more")}</span></div>'
             f'<table class="tbl"><thead><tr><th>Tenant</th><th>Paket</th><th>Lokasi</th><th>Kamera</th><th>Status</th><th>MRR</th><th>Kesehatan</th><th></th></tr></thead>'
             f'<tbody>{rows}</tbody></table></section>')
    flags = "".join(f'<div class="row" style="gap:10px;padding:8px 0;border-bottom:1px solid var(--hair);font-size:13.5px"><span class="grow">{a}</span>'
                    f'{f"<span class={chr(34)}bd slate{chr(34)}>{b}</span>" if b else ""}{tg(on, True)}</div>'
                    for a, b, on in (("Sorotan kamera otomatis", "", True), ("Pencarian bahasa sehari-hari", "beta", True),
                                     ("Model APD v1.4 (helm & rompi)", "", True), ("Aplikasi Supervisor", "", True),
                                     ("Integrasi WMS", "add-on", False), ("SSO & API publik", "Enterprise", False)))
    use = "".join(f'<div style="margin-bottom:10px"><div class="row" style="font-size:13px"><span class="sec">{a}</span><b class="tn" style="margin-left:auto">{b}</b></div>'
                  f'<div class="prog" style="margin-top:5px"><i style="width:{p}%;background:#7c3aed"></i></div></div>'
                  for a, b, p in (("Kamera", "86 / 96", 90), ("Penyimpanan bukti", "412 / 1.000 GB", 41), ("Pengguna", "28 · tanpa batas", 100)))
    drawer = card("PT Contoh Logistik",
                  f'<div class="kv" style="grid-template-columns:120px 1fr"><span>Paket</span><span class="row" style="gap:8px">{bd("Keselamatan", "blue")}<span class="sec">96 kamera · tahunan</span></span>'
                  f'<span>Perpanjangan</span><span>1 Jan 2027</span><span>Lokasi</span><span>5 · 86 kamera · 6 edge box</span>'
                  f'<span>Region data</span><span>Jakarta (ID)</span><span>Retensi bukti</span><span>90 hari (add-on)</span></div>'
                  f'<div class="sect" style="margin-top:16px">Pemakaian</div>{use}'
                  f'<div class="sect" style="margin-top:8px">Fitur & add-on</div>{flags}'
                  f'<div class="row" style="gap:8px;margin-top:14px;flex-wrap:wrap"><span class="btn vio">{I("upgrade")}Ubah paket</span>'
                  f'<span class="btn">{I("login")}Masuk sebagai tenant</span><span class="btn danger">{I("pause_circle")}Tangguhkan</span></div>'
                  f'<div class="mut" style="font-size:12px;margin-top:8px">{I("lock", True, 15, "#6d28d9")} Masuk sebagai tenant butuh izin Admin tenant, maks. 60 menit, tercatat di log audit kedua pihak.</div>',
                  icon="domain", right=bd("Aktif", "green"), style="flex:1")
    body = (f'<div class="ph"><div><h1>Tenant & Langganan</h1><p>24 tenant · 61 lokasi · 1.284 kamera · semua angka bisnis di satu tempat</p></div>'
            f'<div class="acts"><span class="btn">{I("download")}Ekspor</span><span class="btn vio">{I("add")}Tenant baru</span></div></div>'
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px">{kp}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 540px;gap:16px;flex:1;min-height:0">{table}{drawer}</div>')
    return superadmin("tenant", body)


def p20_edge() -> str:
    kp = (kpi("memory", "green", "Edge box online", '59<small>/ 61</small>', "2 offline · tiket otomatis dibuat") +
          kpi("bolt", "blue", "Latensi alert p95", '1,8<small>dtk</small>', "kejadian → notifikasi") +
          kpi("monitor_heart", "green", "Uptime platform", "99,95%", "30 hari terakhir") +
          kpi("model_training", "violet", "Model terbaru", "v2.3", "rilis bertahap · 40% lokasi"))
    edges = [("EDGE-SIMA-01", "PT Contoh Logistik", "Gudang Simulasi A", 16, 72, 61, "v2.3", "3 dtk", ("Online", "#079455")),
             ("EDGE-CKR-01", "PT Contoh Logistik", "DC Cikarang", 16, 64, 58, "v2.2", "4 dtk", ("Online", "#079455")),
             ("EDGE-SBY-01", "PT Contoh Logistik", "DC Surabaya", 16, 0, 0, "v2.2", "14 mnt", ("Offline", "#dc2626")),
             ("EDGE-MFG-03", "PT Contoh Manufaktur", "Plant Karawang", 16, 55, 57, "v2.2 → v2.3", "1 dtk", ("Memperbarui 62%", "#2563eb")),
             ("EDGE-RDG-01", "PT Contoh Rantai Dingin", "Cold Storage Bekasi", 12, 47, 41, "v2.3", "3 dtk", ("Online", "#079455")),
             ("EDGE-RTL-04", "PT Contoh Ritel", "DC Semarang", 16, 81, 69, "v2.2", "5 dtk", ("Online", "#079455"))]
    rows = "".join(
        f'<tr class="{"on" if st[0] == "Offline" else ""}"><td><b class="tn" style="font-size:13px">{e}</b></td><td><div>{t}</div><div class="mut" style="font-size:12px">{loc}</div></td>'
        f'<td class="tn">{c}</td><td style="width:130px"><div class="tn" style="font-size:12.5px">{g}%</div><div class="prog" style="margin-top:5px"><i style="width:{g}%;background:{"#d97706" if g > 80 else "var(--s1)"}"></i></div></td>'
        f'<td class="tn sec">{f"{tmp}°C" if tmp else "—"}</td><td>{bd(v, "violet" if "v2.3" in v else "slate")}</td><td class="tn sec">{hb}</td><td>{status(st[0], st[1])}</td></tr>'
        for e, t, loc, c, g, tmp, v, hb, st in edges)
    table = card("Perangkat edge", f'<table class="tbl"><thead><tr><th>Perangkat</th><th>Tenant · lokasi</th><th>Kamera</th><th>Beban GPU</th><th>Suhu</th>'
                                   f'<th>Model</th><th>Detak terakhir</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>',
                 icon="memory", right=f'<span class="flt">Status: <b>Semua</b>{I("expand_more")}</span>', cb_style="padding:10px 0 4px")
    lat = [1.2, 1.3, 1.2, 1.1, 1.2, 1.4, 1.6, 1.9, 1.7, 1.5, 1.6, 1.8, 1.7, 1.5, 1.4, 1.6, 1.7, 1.5, 1.3, 1.2, 1.2, 1.1, 1.2, 1.3]
    health = card("Latensi alert p95 · 24 jam", lines([("p95", lat, "var(--s7)")], [f"{h:02d}" for h in range(24)], 900, 170, lo=0, hi=3, ticks=3,
                                                       every=3, ref=("batas 3 dtk", 3), fmt=lambda v: f"{num(v, 0)} dtk"),
                  icon="bolt", sub="dari kejadian di kamera sampai notifikasi terkirim")
    models = (f'<div style="padding:14px;border:1px solid var(--border);border-radius:12px">'
              f'<div class="row" style="gap:10px"><span class="it violet">{I("person_search", True, 19)}</span><div class="grow"><b>Deteksi orang & kendaraan</b>'
              f'<div class="mut" style="font-size:12px">detektor orang umum + detektor kendaraan dilatih per lokasi</div></div>{bd("v2.3", "violet")}</div>'
              f'<div class="sect" style="margin-top:12px">Akurasi terukur di PoC · Gudang Simulasi A</div>'
              f'<table class="tbl" style="font-size:13px"><thead><tr><th></th><th>v2.2 umum</th><th>v2.3 dilatih lokasi</th></tr></thead><tbody>'
              f'<tr><td>Forklift ditemukan</td><td class="tn">16%</td><td class="tn"><b>46%</b> {up("30 poin")}</td></tr>'
              f'<tr><td>Presisi forklift</td><td class="tn">55%</td><td class="tn"><b>77%</b> {up("22 poin")}</td></tr>'
              f'<tr><td>Orang: titik yang benar</td><td class="tn">79%</td><td class="tn"><b>79%</b> · posisi 0,19 m</td></tr>'
              f'<tr><td>Orang ditemukan (≥ 40 px)</td><td class="tn">46%</td><td class="tn"><b>46%</b> · detektor jadi batas</td></tr></tbody></table></div>'
              f'<div style="padding:14px;border:1px solid var(--border);border-radius:12px;margin-top:12px">'
              f'<div class="row" style="gap:10px"><span class="it amber">{I("engineering", True, 19)}</span><div class="grow"><b>APD helm & rompi</b>'
              f'<div class="mut" style="font-size:12px">uji buta pada potongan gambar orang</div></div>{bd("v1.4", "violet")}</div>'
              f'<div class="row" style="gap:24px;margin-top:10px;font-size:13px"><span>Helm <b class="tn">24 / 26</b> benar</span><span>Rompi <b class="tn">22 / 28</b> benar</span></div></div>'
              f'<div class="sect" style="margin-top:16px">Rilis v2.3 bertahap</div>'
              f'<div class="row" style="gap:0;margin-top:4px">'
              + "".join(f'<div class="grow col" style="gap:6px;align-items:center;font-size:12.5px"><span class="it {t}" style="width:30px;height:30px;border-radius:50%">{I(ic, True, 17)}</span>'
                        f'<b>{a}</b><span class="mut">{b}</span></div>' + ("" if k == 3 else '<div style="flex:0 0 40px;height:2px;background:var(--border);margin-bottom:34px"></div>')
                        for k, (ic, t, a, b) in enumerate((("check", "green", "10%", "selesai"), ("sync", "blue", "40%", "berjalan · 24 lokasi"),
                                                           ("schedule", "slate", "100%", "12 Okt"), ("undo", "slate", "Rollback", "otomatis bila akurasi turun")))) +
              '</div>'
              f'<div class="sect" style="margin-top:14px">Gerbang rilis</div>'
              + "".join(f'<div class="row" style="gap:10px;padding:5px 0;font-size:13px">{I("check_circle", True, 18, "#079455")}{x}</div>'
                        for x in ("Akurasi tidak turun di 5 lokasi acuan (rekaman berlabel)", "Latensi alert p95 ≤ 2 dtk di edge box terlemah",
                                  "Alarm palsu tidak naik pada pilot 10%")))
    mc = card("Model AI", models, icon="model_training", right=f'<span class="lnk">Registri model {I("chevron_right", size=16)}</span>', style="flex:1")
    body = (f'<div class="ph"><div><h1>Perangkat Edge & Model AI</h1><p>61 edge box di 61 lokasi · rilis model bertahap dengan rollback · akurasi dilaporkan per lokasi</p></div>'
            f'<div class="acts"><span class="btn">{I("download")}Unduh image edge</span><span class="btn vio">{I("rocket_launch")}Rilis model baru</span></div></div>'
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">{kp}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 600px;gap:16px;flex:1;min-height:0"><div class="col" style="gap:16px">{table}{health}</div>{mc}</div>')
    return superadmin("edge", body, wm="Mockup konsep · armada, latensi & tenant ilustrasi · akurasi model: hasil PoC")


def p21_mobile() -> str:
    def phone(screen: str, dark: bool = False) -> str:
        bg = "background:#0b1220;color:#fff" if dark else ""
        return (f'<div class="phone"><div class="screen" style="{bg}"><span class="notch"></span>'
                f'<div class="sbar"><span class="tn">10:42</span><span class="row" style="gap:5px">{I("signal_cellular_alt", True, 17)}{I("wifi", True, 17)}{I("battery_5_bar", True, 17)}</span></div>{screen}</div></div>')
    lock = (f'<div style="text-align:center;margin-top:30px"><div style="font-size:16px;opacity:.8">Senin, 5 Oktober</div>'
            f'<div class="tn" style="font-size:84px;font-weight:600;line-height:1.05;letter-spacing:-.02em">10:42</div></div>'
            f'<div style="margin:30px 14px 0;background:rgba(255,255,255,.14);border-radius:22px;padding:14px;backdrop-filter:blur(8px)">'
            f'<div class="row" style="gap:8px;font-size:12.5px;opacity:.85"><span class="logo" style="width:22px;height:22px;border-radius:6px">{I("warehouse", True, 14)}</span>'
            f'LIVE OPS<span style="margin-left:auto">sekarang</span></div>'
            f'<b style="display:block;margin-top:8px;font-size:15px">⚠ Tinggi · Nyaris tertabrak forklift</b>'
            f'<div style="font-size:14px;opacity:.9;margin-top:2px">CAM 0001 · Area konveyor barat · P14 & forklift F12</div>'
            f'{img(snap(ev1(0)), "100%", 170, "border-radius:12px;margin-top:10px")}</div>'
            f'<div style="margin:10px 14px 0;background:rgba(255,255,255,.1);border-radius:22px;padding:12px 14px;font-size:13.5px">'
            f'<div class="row" style="opacity:.8;font-size:12px">LIVE OPS<span style="margin-left:auto">4 mnt lalu</span></div>'
            f'<b style="display:block;margin-top:4px">Sedang · Melawan arah di lorong satu arah</b><span style="opacity:.85">CAM 0003 · P72</span></div>')
    inc = (f'<div class="row" style="padding:6px 18px 10px;gap:10px">{I("arrow_back_ios_new", False, 20)}<b style="font-size:16px">INS-0142</b>'
           f'<span style="margin-left:auto">{sev("high")}</span></div>'
           f'<div class="tile" style="height:196px;border-radius:0"><img src="../img/evidence_0001_before.jpg">'
           f'<span style="position:absolute;inset:0;display:grid;place-items:center">{I("play_circle", True, 52, "#fff")}</span></div>'
           f'<div style="padding:14px 18px;display:flex;flex-direction:column;gap:10px;flex:1">'
           f'<b style="font-size:18px">Nyaris tertabrak forklift</b>'
           f'<div class="sec" style="font-size:13.5px">10:41:58 · Lintasan forklift<br>CAM 0001 · P14 & forklift F12 (4 km/j)</div>'
           f'<div class="row" style="gap:8px">{cam("CAM 0001")}{status("Ditangani")}</div>'
           f'<div style="background:#fff;border-radius:14px;padding:12px;font-size:13px;border:1px solid var(--border)"><div class="row" style="gap:8px">{avatar("Budi Santoso", 26)}'
           f'<b>Budi Santoso</b><span class="mut" style="margin-left:auto">10:44</span></div><div class="sec" style="margin-top:6px">Operator F12 sudah diingatkan, klakson di persimpangan.</div>'
           f'{img("../img/cam_0001.jpg", "100%", 110, "margin-top:8px;border-radius:10px")}</div>'
           f'<div class="row" style="gap:8px;margin-top:auto"><span class="btn" style="flex:1;justify-content:center">{I("photo_camera")}Foto</span>'
           f'<span class="btn" style="flex:1;justify-content:center">{I("mic")}Catatan</span></div>'
           f'<span class="btn pri" style="justify-content:center;height:46px;font-size:15px">{I("check")}Selesaikan insiden</span></div>')
    hrs = ["07", "08", "09", "10", "11", "12", "13", "14"]
    summ = (f'<div style="padding:4px 18px 10px"><div class="mut" style="font-size:13px">Shift Pagi · 07:00–15:00</div><b style="font-size:21px">Ringkasan shift</b></div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:0 18px">'
            + "".join(f'<div style="background:#fff;border:1px solid var(--border);border-radius:14px;padding:12px"><div class="mut" style="font-size:12px">{a}</div>'
                      f'<b class="tn" style="font-size:24px">{b}</b><div class="mut" style="font-size:11.5px">{c}</div></div>'
                      for a, b, c in (("Insiden", "12", "3 masih terbuka"), ("Near miss", "3", "rata-rata 5"), ("Kepatuhan APD", "86%", "target 95%"),
                                      ("Waktu tanggap", "3:40", "menit, median"))) + '</div>'
            f'<div style="margin:12px 18px 0;background:#fff;border:1px solid var(--border);border-radius:14px;padding:12px 12px 4px">'
            f'<div class="mut" style="font-size:12px;margin-bottom:4px">Insiden per jam</div>'
            + vbars([("Insiden", [1, 2, 3, 3, 1, 1, 1, 0], "var(--s1)")], hrs, 316, 120, ymax=4, ticks=2, L=24, B=22) + '</div>'
            f'<div style="padding:12px 18px 0;font-size:13px"><b>Belum selesai (3)</b>'
            + "".join(f'<div class="row" style="gap:8px;padding:7px 0;border-bottom:1px solid var(--border)">{sev(s)}<span class="ell grow">{t}</span><span class="mut tn">{tm}</span></div>'
                      for s, t, tm in (("high", "Nyaris tertabrak · CAPA", "10:41"), ("medium", "Melawan arah · P72", "10:38"), ("medium", "Tanpa rompi · P66", "10:24")))
            + f'</div><span class="btn pri" style="margin:auto 18px 22px;justify-content:center;height:46px;font-size:15px">{I("draw")}Serah terima ke Shift Siang</span>')
    nav = (f'<div class="row" style="justify-content:space-around;padding:10px 0 22px;border-top:1px solid var(--border);background:#fff;font-size:11px;color:var(--text-3)">'
           + "".join(f'<span class="col" style="align-items:center;gap:2px;{"color:var(--brand)" if on else ""}">{I(ic, on, 22)}{t}</span>'
                     for ic, t, on in (("notifications", "Alert", False), ("videocam", "Live", False), ("summarize", "Shift", True), ("person", "Akun", False))) + '</div>')
    phones = [("1", "Alert masuk walau HP terkunci", "Foto bukti, kamera, siapa, di mana: supervisor tahu dalam hitungan detik.", phone(lock, True)),
              ("2", "Tangani di lantai gudang", "Lihat klip, ambil alih insiden, tambah foto & catatan, selesaikan.", phone(inc)),
              ("3", "Ringkasan & serah terima shift", "Angka shift, insiden yang belum selesai, tanda tangan serah terima.", phone(summ.replace("</span>\n", "</span>") + nav))]
    cols = "".join(f'<div class="col" style="gap:18px;align-items:center;width:420px"><div style="text-align:center"><div class="row" style="gap:10px;justify-content:center">'
                   f'<span class="mk2">{k}</span><b style="font-size:19px">{a}</b></div><div class="sec" style="font-size:14px;margin-top:6px;max-width:400px">{b}</div></div>{p}</div>'
                   for k, a, b, p in phones)
    css = (".mk2{width:28px;height:28px;border-radius:50%;background:#2563eb;color:#fff;font-weight:700;display:grid;place-items:center;font-size:14px}"
           "body{background:linear-gradient(160deg,#eef4ff 0%,#f6f8fb 55%,#eef2f7 100%)}")
    body = (f'<div style="padding:44px 72px 0;display:flex;align-items:flex-end;gap:20px"><div><div class="eyebrow">Aplikasi Supervisor · iOS & Android</div>'
            f'<h1 style="font-size:36px;font-weight:700;letter-spacing:-.02em;margin-top:6px">Insiden ditangani dari lantai gudang, bukan dari meja</h1></div>'
            f'<div class="sec" style="margin-left:auto;max-width:520px;font-size:15px;text-align:right">Untuk Supervisor K3 & kepala shift. Notifikasi juga lewat WhatsApp bagi yang belum memasang aplikasi.</div></div>'
            f'<div style="display:flex;justify-content:center;gap:56px;margin-top:30px">{cols}</div>')
    return doc(body + f'<div class="wm">{WM_POC}</div>', extra_css=css)


def p22_bisnis() -> str:
    tiers = [
        ("Operasional", "Rp 250 rb", "/ kamera / bulan", "Untuk efisiensi gudang", False, "slate",
         ["Peta lantai digital & heatmap", "Hitung orang & garis", "Utilisasi forklift", "Kepadatan & lama tinggal per zona",
          "Laporan harian & mingguan", "Bukti kejadian 30 hari", "Hingga 10 pengguna"],
         "Gudang 40 kamera ≈ Rp 10 jt / bulan", "Mulai dari sini"),
        ("Keselamatan", "Rp 450 rb", "/ kamera / bulan", "Paling sesuai untuk K3", True, "blue",
         ["Semua di Operasional", "Near miss orang–forklift", "Jalur & zona terlarang, kecepatan forklift", "APD helm & rompi",
          "Sorotan kamera otomatis", "WhatsApp, push & eskalasi", "Pencarian bahasa sehari-hari", "Laporan SMK3 & ISO 45001",
          "Aplikasi Supervisor · pengguna tanpa batas"],
         "Gudang 40 kamera ≈ Rp 18 jt / bulan", "Mulai pilot 30 hari"),
        ("Enterprise", "Hubungi kami", "harga per kontrak", "Untuk grup multi-lokasi", False, "violet",
         ["Semua di Keselamatan", "Dashboard HQ multi-lokasi", "SSO, audit lanjutan, region data", "Integrasi WMS / HRIS & API",
          "Opsi on-premise", "SLA 99,9% & dukungan 24/7", "Model AI khusus lokasi"],
         "Untuk 5+ lokasi; harga per kontrak tahunan", "Jadwalkan demo"),
    ]
    tc = "".join(
        f'<section class="card" style="padding:24px 26px;gap:14px;{"border:2px solid var(--brand);box-shadow:0 12px 32px rgba(37,99,235,.15)" if hot else ""}">'
        f'<div class="row"><b style="font-size:20px">{n}</b>{bd("Direkomendasikan", "blue", "star") if hot else ""}</div>'
        f'<div class="sec" style="font-size:13.5px;margin-top:-8px">{who}</div>'
        f'<div class="row" style="align-items:baseline;gap:8px"><b class="tn" style="font-size:34px;letter-spacing:-.02em">{p}</b><span class="mut">{u}</span></div>'
        + "".join(f'<div class="row" style="gap:10px;font-size:14px">{I("check_circle", True, 19, "var(--brand)" if hot else "#64748b")}{f}</div>' for f in feats)
        + f'<div style="margin-top:auto;padding-top:14px;border-top:1px solid var(--hair)"><div class="mut" style="font-size:12.5px">{ex}</div>'
        + f'<span class="btn {"pri" if hot else ""}" style="margin-top:12px;width:100%;justify-content:center;height:42px">{cta}</span></div>'
        + '</section>' for n, p, u, who, hot, tone, feats, ex, cta in tiers)
    once = "".join(f'<div class="row" style="gap:14px;padding:12px 0;border-bottom:1px solid var(--hair)"><span class="it {t}">{I(ic, True, 19)}</span>'
                   f'<div class="grow"><b style="font-size:14.5px">{a}</b><div class="mut" style="font-size:12.5px">{c}</div></div><b class="tn" style="font-size:15px;white-space:nowrap">{b}</b></div>'
                   for ic, t, a, b, c in (("memory", "green", "Edge AI box", "Rp 1,5 jt / bln", "sewa per 16 kamera · atau beli putus"),
                                          ("engineering", "amber", "Onboarding & kalibrasi", "Rp 15 jt / lokasi", "audit kamera, verifikasi posisi, gambar zona, pelatihan"),
                                          ("science", "blue", "Pilot 30 hari · 1 lokasi, ≤ 8 kamera", "Rp 25 jt", "baseline keselamatan & laporan akurasi · dikreditkan ke kontrak bila lanjut"),
                                          ("add_circle", "violet", "Add-on", "Replay 3D · retensi 90 hari · SMS", "dibeli per lokasi")))
    ex = (f'<section class="card" style="padding:22px 24px;gap:10px;background:#0f172a;border-color:#0f172a;color:#e9eef4">'
          f'<div class="eyebrow" style="color:#93c5fd">Contoh 1 gudang · 40 kamera</div>'
          + "".join(f'<div class="row" style="font-size:14px;color:#cbd5e1"><span>{a}</span><b class="tn" style="margin-left:auto;color:#fff">{b}</b></div>'
                    for a, b in (("Keselamatan 40 × Rp 450 rb", "Rp 18,0 jt"), ("Edge box 3 unit", "Rp 4,5 jt"))) +
          f'<div style="height:1px;background:#334155;margin:4px 0"></div>'
          f'<div class="row"><span>Pendapatan berulang / bulan</span><b class="tn" style="margin-left:auto;font-size:22px">Rp 22,5 jt</b></div>'
          f'<div class="row" style="color:#93c5fd"><span>per tahun (ARR)</span><b class="tn" style="margin-left:auto;font-size:22px">Rp 270 jt</b></div>'
          f'<div style="font-size:12.5px;color:#94a3b8;margin-top:4px">+ onboarding Rp 15 jt sekali bayar</div></section>')
    market = (f'<section class="card" style="padding:22px 24px;gap:12px"><div class="eyebrow">Siapa yang membeli</div>'
              + "".join(f'<div class="row" style="gap:12px;font-size:14px">{I(ic, False, 21, "var(--text-2)")}<span>{a}</span></div>'
                        for ic, a in (("local_shipping", "3PL & distribusi"), ("factory", "Pabrik & gudang bahan baku"), ("ac_unit", "Cold storage"),
                                      ("inventory_2", "E-commerce fulfilment & DC ritel")))
              + f'<div class="mut" style="font-size:12.5px;line-height:1.5">Pemicu: kewajiban SMK3 (PP 50/2012), audit ISO 45001, klaim kecelakaan & asuransi, '
                f'dan biaya forklift yang menganggur.</div></section>')
    body = (f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 520px;gap:20px;flex:1;min-height:0">{tc}'
            f'<div class="col" style="gap:20px">{ex}{market}</div></div>'
            f'<section class="card" style="padding:6px 24px 4px"><div style="display:grid;grid-template-columns:1fr 1fr;column-gap:40px">{once}</div></section>')
    return slide("Model bisnis", "Langganan per kamera + edge box + onboarding",
                 "Pendapatan berulang yang tumbuh mengikuti jumlah kamera dan lokasi; pilot 30 hari membuktikan nilai sebelum kontrak. "
                 "Harga di halaman ini adalah ilustrasi untuk divalidasi saat pilot.", body, wm="Mockup konsep · harga ilustrasi, belum final")


PAGE_FUNCS = [
    ("00_peta_produk", p00_peta_produk), ("01_peran_hak_akses", p01_peran), ("02_beranda", p02_beranda),
    ("03_live_monitoring", p03_live), ("04_peta_lantai", p04_peta), ("05_pusat_insiden", p05_insiden),
    ("06_detail_insiden", p06_detail), ("07_pencarian", p07_cari), ("08_laporan_k3", p08_laporan),
    ("09_zona_aturan", p09_zona), ("10_kamera_kalibrasi", p10_kamera), ("11_notifikasi_eskalasi", p11_notif),
    ("12_pengguna_peran", p12_pengguna), ("13_dashboard_command_center", p13_command), ("14_dashboard_fokus_kamera", p14_fokus),
    ("15_dashboard_kepatuhan_apd", p15_apd), ("16_dashboard_analitik_keselamatan", p16_keselamatan),
    ("17_dashboard_analitik_operasional", p17_operasional), ("18_dashboard_multi_lokasi", p18_multi),
    ("19_superadmin_tenant", p19_tenant), ("20_superadmin_edge_ai", p20_edge), ("21_aplikasi_supervisor", p21_mobile),
    ("22_model_bisnis", p22_bisnis),
]


# ------------------------------------------------------------------ rendering
def chrome() -> tuple[str, bool]:
    """(binary, is_headless_shell). The headless shell's page is exactly the window; full Chrome's
    new headless mode keeps 87 px of the window for a browser frame it does not draw."""
    shells = sorted(glob.glob("/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell"))
    for c in [os.environ.get("CHROME", "")] + shells + sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")) + \
             [shutil.which(n) or "" for n in ("chromium", "chromium-browser", "google-chrome")]:
        if c and Path(c).exists():
            return c, c.endswith("headless_shell")
    sys.exit("headless Chromium not found: set CHROME=/path/to/chrome")


def shoot(html: Path, png: Path, scale: float = 1.0) -> None:
    exe, shell = chrome()
    frame = 0 if shell else 87
    subprocess.run([exe] + ([] if shell else ["--headless=new"]) +
                   ["--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
                    f"--force-device-scale-factor={scale}", f"--window-size=1920,{1080 + frame}",
                    "--allow-file-access-from-files", "--virtual-time-budget=4000", f"--screenshot={png}", html.as_uri()],
                   check=True, capture_output=True, timeout=120)
    if frame:
        import cv2
        pic = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
        cv2.imwrite(str(png), pic[:int(1080 * scale)])


def fetch_icons() -> None:
    """Material Symbols Rounded, only the glyphs the pages use (Apache 2.0), from Google Fonts."""
    for fill, name in ((False, "Line"), (True, "Fill")):
        names = ",".join(sorted(USED[fill]))
        url = ("https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,"
               f"{int(fill)},0&icon_names={names}&display=block")
        req = urllib.request.Request(url, headers={"User-Agent": "Wget/1.21"})
        css = urllib.request.urlopen(req, timeout=60).read().decode()
        font_url = css.split("url(")[1].split(")")[0]
        data = urllib.request.urlopen(urllib.request.Request(font_url, headers={"User-Agent": "Wget/1.21"}), timeout=60).read()
        (FONTS / f"MaterialSymbolsRounded-{name}.ttf").write_bytes(data)
        print(f"icons {name}: {len(USED[fill])} glyphs, {len(data) // 1024} KB")


def main(argv: list[str]) -> int:
    HTML.mkdir(exist_ok=True)
    PAGES.mkdir(exist_ok=True)
    want = [a for a in argv if not a.startswith("--")]
    scale = 2.0 if "--2x" in argv else 1.0
    built = []
    for slug, fn in PAGE_FUNCS:
        page = fn()
        if want and not any(slug.startswith(w) for w in want):
            continue
        path = HTML / f"{slug}.html"
        path.write_text(page)
        built.append((slug, path))
    if "--icons" in argv:
        fetch_icons()
    if "--no-shot" not in argv:
        for slug, path in built:
            shoot(path, PAGES / f"{slug}.png", scale)
            print("page", slug)
    print(json.dumps(counts()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
