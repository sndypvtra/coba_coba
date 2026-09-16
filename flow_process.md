# Flow Process — End-to-End Video Analytics Architecture

**A brief for one slide.** This describes the product as a general system: fixed
cameras in, a GPU doing the seeing, PostgreSQL holding the answers, and people
looking at both a live view and a dashboard. It is written to be handed to a
design tool — the nodes, the icons, the connections and the labels are specified
rather than described.

Nothing here is tied to one installation. The cafe occupancy case is named once,
at the end, as a worked example of the workload — not as the source of the
numbers.

---

## 1. The slide in one sentence

> Fixed cameras feed a GPU appliance over PoE; the model runs there under
> TensorRT, annotated video goes straight to a local monitor, and only the
> extracted events cross the network into PostgreSQL — **pixels stay on site,
> numbers travel.**

---

## 2. Nodes to draw

Core nodes carry the story. Optional nodes are real parts of most installations —
draw them lighter, or drop them first if the slide gets crowded.

| # | Node | Label | Weight |
|---|---|---|---|
| 1 | IP cameras (×N) | `IP Cameras`<br>PoE · H.264/H.265 · ONVIF | **core** |
| 2 | PoE switch | `PoE Switch`<br>1 GbE · 802.3af/at | **core** |
| 3 | NVR | `NVR`<br>existing recorder, untouched | optional |
| 4 | **GPU appliance** | `AI Inference Server`<br>GPU · TensorRT engine | **core — hero** |
| 5 | Local monitor | `Live View`<br>annotated video, on-site | **core** |
| 6 | UPS | `UPS` | optional |
| 7 | Router / firewall | `Router + Firewall`<br>outbound only | **core** |
| 8 | Internet | `Internet / VPN` | **core** |
| 9 | App server | `API Server`<br>ingest · auth | **core** |
| 10 | **PostgreSQL** | `PostgreSQL`<br>+ TimescaleDB | **core — hero** |
| 11 | Dashboard | `Dashboard`<br>BI / Grafana | **core** |
| 12 | Alerts | `Alerts`<br>email · webhook · chat | optional |
| 13 | Remote viewer | `Remote Access`<br>browser over VPN | optional |

**Two nodes are the point of the slide** — node 4 (where the seeing happens) and
node 10 (where the answers live). Draw them larger or in the accent colour.

### On the hardware label

Do **not** name a specific board on the slide. The appliance is sized to the
camera count, and that is a procurement decision, not an architecture one:

| Site size | Shape |
|---|---|
| 1–4 cameras | embedded GPU module, fanless, wall-mounted |
| 4–16 cameras | small-form-factor x86 + one workstation GPU |
| 16+ cameras | 1U/2U rack server, one or two datacentre GPUs |

Label the node `AI Inference Server (GPU)` and put the sizing in a footnote.

---

## 3. Icons — from the internet, one family only

The single rule that decides whether this looks professional: **pick one icon
family and use it for every device.** Mixing a flat outline switch with a
photoreal camera and an isometric server is what makes a diagram look assembled
rather than designed.

### Recommended sources

| Source | URL | Style | Licence |
|---|---|---|---|
| **Cisco Network Topology Icons** | cisco.com/c/en/us/about/brand-center/network-topology-icons.html | the industry standard for network diagrams | free for documentation, see their terms |
| **SVG Repo** | svgrepo.com | huge, many CC0 sets | much of it CC0 / public domain |
| **Iconduck** | iconduck.com | curated open sets | per-set, mostly MIT / CC0 |
| **Font Awesome 6 Free** | fontawesome.com/icons | flat outline, complete device set | CC BY 4.0 |
| **Material Symbols** | fonts.google.com/icons | flat outline, very consistent | Apache 2.0 |
| **Flaticon** | flaticon.com | isometric and 3D hardware | free tier needs attribution |

**For hardware that should feel physical** — cameras, switches, rack servers —
isometric or 3D-render sets read best on a slide. Search terms that land well:
`isometric network switch`, `isometric server rack`, `cctv camera 3d icon`,
`poe switch icon`, `monitor screen isometric`.

**For the abstract nodes** — internet, firewall, database, dashboard — a flat
outline set is clearer than a render. Mixing *these two* is acceptable and
common: physical things look physical, concepts look like symbols. What must not
vary is the style *within* each group.

### Per-node search terms

| Node | Search | Fallback (Lucide) |
|---|---|---|
| IP camera | `cctv camera`, `security camera isometric` | `cctv` |
| PoE switch | `network switch`, `ethernet switch isometric` | `network` |
| NVR | `nvr`, `video recorder rack` | `hard-drive` |
| GPU appliance | `gpu server`, `edge ai server`, `mini pc gpu` | `cpu` |
| Monitor | `monitor screen`, `display isometric` | `monitor` |
| UPS | `ups battery backup` | `battery-charging` |
| Router / firewall | `router firewall`, `firewall shield` | `shield` |
| Internet | `internet cloud`, `globe network` | `cloud` |
| App server | `server rack`, `api server` | `server` |
| PostgreSQL | use the **official elephant** — postgresql.org/media/img/about/press/elephant.png | `database` |
| Dashboard | `analytics dashboard`, `bi chart screen` | `layout-dashboard` |
| Alerts | `bell notification` | `bell` |

> **One practical warning.** Some renderers cannot fetch remote images at draw
> time — a sandboxed preview may have no outbound network. If icons come back
> blank, download the SVG/PNG files and embed them (as files or base64) rather
> than linking to a URL.

---

## 4. Connections

Physical cabling is **plain straight lines, no arrowheads**. Logical data flow
gets arrowheads. Keep the two visually distinct — that contrast is what makes the
diagram readable.

| From → To | Medium | Style | Label |
|---|---|---|---|
| Cameras → PoE switch | Cat6, PoE | solid line | `LAN · PoE` |
| PoE switch → NVR | Cat6 | thin solid | `existing recording path` |
| PoE switch → GPU appliance | Cat6 | solid line | `RTSP · 1 GbE` |
| GPU appliance → Monitor | HDMI / DisplayPort | **solid, different colour** | `HDMI · live annotated video` |
| UPS → switch, appliance | power | dotted | `power` |
| GPU appliance → Firewall | Cat6 | solid line | `events only · HTTPS` |
| Firewall → Internet | WAN | solid line | `TLS · outbound` |
| Internet → App server | — | **arrow →** | `JSON events` |
| App server → PostgreSQL | — | **arrow →** | `INSERT` |
| PostgreSQL → Dashboard | — | **arrow →** | `SQL` |
| PostgreSQL → Alerts | — | **arrow →** | `threshold triggers` |
| Internet → Remote viewer | — | **arrow ←→** | `VPN` |

### The one annotation that matters most

Draw a **vertical boundary line** through the diagram between the GPU appliance
and the firewall, labelled `SITE BOUNDARY`. Put a crossed-out video icon on it:

> **Video does not cross this line.** Frames are decoded, inferred and discarded
> in memory. What leaves the site is a few kilobytes of events per camera per
> hour — orders of magnitude less than the footage, and nothing that identifies
> anyone.

That single line answers the privacy question, the bandwidth question and the
storage-cost question at once, which is why it earns space on the slide.

---

## 5. Yes — you can watch it live on a monitor

This is worth drawing explicitly, because it is the first thing anyone asks and
most architecture diagrams leave it out. There are **three** ways to see the
system working, and they are not alternatives — most sites use two.

| | How | Latency | Where you can watch |
|---|---|---|---|
| **A. Direct display** | HDMI/DisplayPort straight out of the appliance to a monitor on the wall | lowest — tens of ms | that one room |
| **B. Re-stream** | the annotated video is re-encoded and served as RTSP / WebRTC / HLS | 0.2–2 s depending on protocol | any browser on the LAN, or remote over VPN |
| **C. Dashboard** | no video at all — the numbers, charted | seconds to minutes | anywhere |

**A is nearly free.** The annotated frames are already in GPU memory; rendering
them to a display surface costs almost nothing, and no encoder is involved. If
there is a back office with a screen, this is the obvious choice.

**B costs one more encode per stream.** That is real GPU budget — account for it
when sizing the appliance, not after. Use it when the appliance lives in a rack
or a locked cabinet where nobody can stand in front of it.

**C is what crosses the site boundary.** A and B stay inside.

On the slide: draw the monitor connected to the appliance with a distinctly
coloured line labelled `HDMI · live annotated video`, and keep it clearly on the
site side of the boundary. If you have room, put B as a thin dashed branch from
the same node to a browser icon.

---

## 6. Inside the appliance

Draw as a left-to-right chain beneath node 4:

```
RTSP ──▶ DECODE ──▶ SAMPLE ──▶ INFER ──▶ TRACK ──▶ LOGIC ──▶ EVENTS
         hardware   rate       TensorRT   identity  rules     JSON
                                                    ▼
                                              ANNOTATE ──▶ HDMI
```

| Stage | What it does | Runs on |
|---|---|---|
| **Decode** | H.264/H.265 → frames, hardware decoder, stays in GPU memory | video decoder |
| **Sample** | drop to the rate the task actually needs | CPU |
| **Infer** | the detector, as a TensorRT engine | **GPU** |
| **Track** | one identity per object across frames | CPU |
| **Logic** | zones, dwell, counting rules — the domain part | CPU |
| **Annotate** | boxes and overlays drawn for the live view | GPU |
| **Events** | structured records, queued for upload | CPU |

**Sample rate is a design lever, not a constant.** Counting objects on a belt
needs a high rate; measuring how long someone stood somewhere does not. Halving
the rate roughly doubles the cameras one GPU serves — and makes tracking harder,
because objects move further between frames. State the chosen rate on the slide;
it explains most of the sizing.

---

## 7. TensorRT — what is actually optimised

Two things belong on the slide, and they are both structural rather than
numerical.

### The engine is built offline, not at the edge

```
trained model ──▶ ONNX ──▶ trtexec (FP16 / INT8) ──▶ calibrate ──▶ .engine
     build machine                                                 deploy ──▶ appliance
```

Draw this as a small **Build / Offline** box feeding the appliance once, with a
dashed line labelled `deploy engine`, visibly separate from the live data path.
Nothing in that chain runs on site.

The consequence is operational and worth one line: **an engine is built for a
specific GPU, precision and input size.** Change any of those and it is rebuilt
and re-benchmarked. Model updates are a release, not a config edit.

### What the optimisation buys

| Lever | Effect |
|---|---|
| FP16 | typically ~2× over FP32, with accuracy loss small enough to verify rather than assume |
| INT8 | faster again, needs a calibration set **and** a recall check before it ships |
| Layer fusion | fewer kernel launches; most of the win on small models |
| Batching | several camera streams inferred together, better GPU occupancy |
| Hardware decode | frames never leave the GPU — often the biggest single win |

**Do not put a milliseconds figure on the slide unless you measured it on the
hardware you are quoting.** Throughput depends on the GPU, the precision, the
input resolution and the batch. The defensible statement is the *shape*: an
unoptimised prototype runs at a fraction of real time; the engine is what closes
the gap; the exact factor is what `trtexec` tells you on the target board.

---

## 8. PostgreSQL — the sink

Draw four tables, or just name them. The shape generalises across every case in
this family:

| Table | One row per | Holds |
|---|---|---|
| `camera` | installed camera | site, room, position, stream settings |
| `observation` | processed frame | timestamp, counts — **TimescaleDB hypertable** |
| `subject` | tracked object's life | first seen, last seen, duration, a quality score |
| `event` | something that happened | crossing, entry, dwell threshold, alert |

Three properties of this schema are worth a line each on the slide:

- **Time-series and relational are separated.** Per-frame counts are an append
  stream and belong in a hypertable; a tracked object's life is a row that gets
  closed once.
- **Observed and inferred are separate columns**, never summed into one. A figure
  partly interpolated through an occlusion must not read as one fully observed.
- **A quality score rides with every subject.** Detection is reliable; tracking is
  the part that fails, and a broken identity silently becomes two short visits
  instead of one long one. Storing the score is what makes that visible instead
  of assumed.

Order-of-magnitude for sizing: a handful of rows per camera per second of
processing, which is **megabytes per camera per day** — against **gigabytes per
day** for the same period as video.

---

## 9. State these limits on the slide

Small type, bottom edge. A diagram showing only the happy path is a sales
diagram:

1. **Counting is a detection result; duration is a tracking result.** They are
   not equally reliable and the system reports which is which.
2. **Interpolated frames are stored apart from observed ones.**
3. **No faces, no re-identification across sites or sessions.** Identifiers are
   anonymous and scoped to one camera's session.
4. **Calibration is per installation.** Zones, thresholds and geometry belong to
   one camera position; moving it means re-measuring.

---

## 10. Layout

Left to right, five tiers, one horizontal axis:

```
   CAPTURE            EDGE / COMPUTE          │ NETWORK          CORE              PEOPLE
 ┌──────────┐      ┌─────────────────┐        │ ┌──────────┐   ┌────────────┐   ┌───────────┐
 │ 📷 CAM ×N │──┐   │  🖥️ AI SERVER    │        │ │ 🛡️ FW     │   │ 🗄️ Postgres │   │ 📊 Dashboard│
 └──────────┘  ├─🔀─│     TensorRT     │───────┼─│    ↕     │─🌐│      ↓      │──▶│           │
 ┌──────────┐  │    │        │         │        │ └──────────┘   │  ⚙️ API      │   │ 🔔 Alerts  │
 │ 📷 CAM    │──┘    │        ▼         │        │                └────────────┘   └───────────┘
 └──────────┘       │   🖵 LIVE VIEW    │        │
                    └─────────────────┘        │
                                      SITE BOUNDARY
```

Put the pipeline strip (section 6) as a horizontal band under the AI server, and
the Build/Offline box (section 7) above it. The live-view monitor hangs below the
server, clearly inside the boundary.

**If it does not fit**, drop in this order: the UPS and NVR, then the alerts and
remote-viewer nodes, then the build-offline box. Sections 2, 4 and 5 are the
slide.

---

## 11. Palette

| Role | Colour |
|---|---|
| Capture / field | neutral grey |
| Edge compute (emphasis) | warm accent |
| Live-view link | a second, distinct accent |
| Network | muted blue |
| Database (emphasis) | deep blue |
| Site-boundary marker | red |
| Background | white or a very light warm neutral |

---

## Appendix — a worked example

The cafe occupancy case in this repository is one instance of exactly this
architecture: two ceiling cameras, one appliance, zones drawn over each room, and
PostgreSQL holding per-frame occupancy, per-visitor duration and staff service
time. Its measured figures live in
`projects/05_cafe_dwell_time/output/*__dwell.json`, and its own deployment brief
is `projects/05_cafe_dwell_time/flow_process.md`.

Use it to make the slide concrete if you want a caption — but the diagram above
is the product, and the numbers belong to one installation.
