# Flow Process — Case 05: Cafe Occupancy & Dwell Time

**A brief for one slide.** This document describes an end-to-end field
deployment of the cafe dwell-time system, from the cameras on the ceiling to
rows landing in PostgreSQL. It is written to be handed to a design tool: the
node list, the icons, the connections and the labels are all specified
explicitly so the diagram can be drawn without inventing anything.

Everything marked **measured** comes from a real run of this project and is
reproducible from its committed `output/*__dwell.json`. Everything marked
**budget** is a planning figure for hardware not yet benchmarked, and is labelled
as such rather than presented as a result.

---

## 1. The slide in one sentence

> Two ceiling cameras watch two rooms of one cafe over PoE; an edge box decodes
> their streams, runs a TensorRT-optimised open-vocabulary detector at 5 fps,
> repairs identities, and writes occupancy, per-visitor dwell and staff service
> time into PostgreSQL — **video never leaves the building; only numbers do.**

That last clause is the point of the architecture and should be visible on the
slide, not buried in a footnote.

---

## 2. Nodes to draw

Icon names are given for **Lucide** (primary), with a Font Awesome alternative
and an emoji fallback, so whichever set the renderer has will resolve.

| # | Node | Label on slide | Lucide | Font Awesome | Emoji | Tier |
|---|---|---|---|---|---|---|
| 1 | Camera A | `CAM-01 · Room 1`<br>2 MP, 25 fps, H.264 | `cctv` | `fa-video` | 📹 | Edge / Field |
| 2 | Camera B | `CAM-02 · Room 5`<br>2 MP, 25 fps, H.264 | `cctv` | `fa-video` | 📹 | Edge / Field |
| 3 | PoE switch | `PoE Switch`<br>8-port, 1 GbE, 802.3af | `network` | `fa-network-wired` | 🔀 | Edge / Field |
| 4 | Edge inference box | `AI Inference Server`<br>GPU · TensorRT | `cpu` | `fa-microchip` | 🧠 | Edge / Compute |
| 5 | Local store & forward | `Local Buffer`<br>SQLite queue, 7-day retention | `hard-drive` | `fa-hard-drive` | 💾 | Edge / Compute |
| 6 | Router / firewall | `Router + Firewall`<br>outbound TLS only | `shield` | `fa-shield-halved` | 🛡️ | Network |
| 7 | Internet | `Internet`<br>site uplink, VPN tunnel | `cloud` | `fa-cloud` | 🌐 | Network |
| 8 | Application server | `App Server`<br>ingest API, auth | `server` | `fa-server` | 🖥️ | Core / Backend |
| 9 | **PostgreSQL** | `PostgreSQL 16`<br>+ TimescaleDB | `database` | `fa-database` | 🗄️ | Core / Backend |
| 10 | Dashboard | `Dashboard`<br>Grafana / BI | `layout-dashboard` | `fa-chart-line` | 📊 | Consumers |

**Emphasis:** node 4 (Edge AI Box) and node 9 (PostgreSQL) are the two the slide
is about. Draw them larger or in the accent colour; keep the rest neutral.

---

## 3. Connections to draw

All physical links are **plain straight lines** — no arrowheads on cabling, and
no curves. Only the logical data flow gets arrowheads.

| From → To | Medium | Line style | Label on the line |
|---|---|---|---|
| 1 → 3 | Cat6 UTP, PoE | solid line | `LAN · PoE` |
| 2 → 3 | Cat6 UTP, PoE | solid line | `LAN · PoE` |
| 3 → 4 | Cat6 UTP | solid line | `RTSP / H.264 · 1 GbE` |
| 4 → 5 | internal | short solid line | `queue on failure` |
| 4 → 6 | Cat6 UTP | solid line | `JSON events · HTTPS` |
| 6 → 7 | WAN / fibre | solid line | `TLS 1.3 outbound` |
| 7 → 8 | — | **arrow →** | `~2 KB per event` |
| 8 → 9 | — | **arrow →** | `INSERT` |
| 9 → 10 | — | **arrow →** | `SQL query` |

**One annotation matters more than the others.** Put a small crossed-out video
icon (`video-off` / 🚫📹) on the link between node 4 and node 6, captioned:

> **No frames cross this line.** Video is decoded, inferred and discarded in RAM
> at the edge. What leaves the site is counts and durations.

---

## 4. Layout

Left to right, four tiers, with a light vertical divider and a header label per
tier:

```
  FIELD                 EDGE COMPUTE            NETWORK              CORE
┌───────────┐         ┌──────────────┐      ┌───────────┐     ┌──────────────┐
│  📹 CAM-01 │──┐      │              │      │           │     │  🖥️ App Srv   │
│  Room 1   │  │      │   🧠 Edge AI  │      │  🛡️ FW     │     │      ↓        │
└───────────┘  ├──🔀──│   TensorRT   │──────│     ↕     │─🌐──│  🗄️ Postgres  │
┌───────────┐  │ PoE  │              │      │           │     │      ↓        │
│  📹 CAM-02 │──┘      │   💾 buffer   │      │           │     │  📊 Dashboard │
│  Room 5   │         └──────────────┘      └───────────┘     └──────────────┘
└───────────┘
```

Put the **pipeline strip** (section 5) as a horizontal band *underneath* the
Edge AI Box, visually attached to it — that is where the computer-vision work
happens and it deserves the centre of the slide.

---

## 5. What happens inside the Edge AI Box

Draw as a left-to-right chain of small blocks under node 4. Six stages:

```
RTSP ──▶ DECODE ──▶ DECIMATE ──▶ DETECT ──▶ TRACK ──▶ IDENTITY ──▶ EVENTS
         NVDEC      25→5 fps     TensorRT   TrackTrack  repair      JSON
```

| Stage | What it does | Runs on |
|---|---|---|
| **Decode** | H.264 → frames, hardware decoder, zero-copy to GPU | NVDEC |
| **Decimate** | keep every 5th frame → **5 fps** | CPU |
| **Detect** | YOLOE-11L-seg, prompt `"person"`, conf 0.25, 1280 px | **GPU / TensorRT** |
| **Track** | TrackTrack (CVPR 2025) + ReID + GMC | CPU |
| **Identity** | split → merge → classify → confine → hold | CPU |
| **Events** | occupancy per frame, visits, service sessions | CPU |

### Why 5 fps, and why that makes the tracker the hard part

The pipeline runs at **4.995 fps** — the rate the project is tuned and validated
at. That is a deliberate compute trade, not a limitation: at 5 fps one GPU serves
many more cameras than at 25.

The cost lands on identity. At ~5 fps a walking person crosses far more pixels
between frames than a tracker's motion model expects, so identity breaks in ways
that never appear at 25 fps. **That is why five of the six pipeline stages after
detection are about identity rather than pixels**, and it is worth one line on
the slide:

> Occupancy is a detection result. Dwell time is a tracking result. They are not
> equally reliable, and the system reports which is which.

---

## 6. TensorRT optimisation — what actually gets optimised

This is the part most diagrams get wrong, so it is worth drawing correctly.

### The text encoder does not ship to the edge

YOLOE is open-vocabulary: it takes words, not a fixed class list. But the words
are embedded **once, offline**:

```
"person" ──▶ MobileCLIP-BLT text encoder ──▶ class embedding ──▶ baked into head
            (572 MB, build machine only)                          (ships to edge)
```

At inference the text encoder never runs. The edge box carries a **single-class
detector engine**, not a vision-language model. Draw this as a separate small
"Build / Offline" box feeding the edge box once, with a dashed line labelled
`deploy engine`, clearly distinct from the live data path.

**The operational consequence belongs on the slide:** changing the prompt means
re-exporting and re-benchmarking the engine. Prompts are a build-time decision in
production, even though they are a runtime decision in the prototype.

### The export chain

```
yoloe-11l-seg.pt ──▶ set_classes(["person"]) ──▶ ONNX (opset 17)
                 ──▶ trtexec --fp16 ──▶ calibration ──▶ .engine
```

| Setting | Value | Why |
|---|---|---|
| Precision | **FP16** | ~2× over FP32 with no measurable mAP loss on this task |
| INT8 | optional, needs calibration set | only if the camera count demands it; re-validate recall first |
| Input | `1×3×1280×1280`, static | the resolution the project's thresholds were set at |
| Batch | 1 per stream, or 2 for two cameras | two rooms fit one batch |
| Workspace | 4 GB | |
| DLA | not used | segmentation head falls back to GPU anyway |

### Performance: what is measured, and what is budget

| | Value | Status |
|---|---|---|
| CPU baseline, 4 cores, PyTorch, 1280 px | **1,215 ms/frame** | **measured** — from `cafe_scene5_30s__dwell.json` |
| Required per camera at 5 fps | 200 ms/frame | requirement |
| TensorRT FP16 on an embedded GPU, 1280 px | not measured | **benchmark on the board you actually buy** |
| Cameras per box at 5 fps | `1000 ÷ ms_per_frame ÷ 5` | arithmetic, fill in after benchmarking |

The honest framing for the slide: **the CPU prototype runs at 0.8 fps and the
requirement is 5 fps per camera — a 6× gap that TensorRT exists to close.** The
exact multiple is a hardware question that gets answered by `trtexec`, not by a
slide.

---

## 7. PostgreSQL — the output

Four tables. Occupancy is time-series and belongs in a TimescaleDB hypertable;
the rest are ordinary relational rows.

```sql
CREATE TABLE camera (
    camera_id     TEXT PRIMARY KEY,          -- 'CAM-02'
    site_id       TEXT NOT NULL,
    room_label    TEXT NOT NULL,             -- 'Room 5'
    fps_inference REAL NOT NULL DEFAULT 4.995
);

-- one row per processed frame, per camera
CREATE TABLE occupancy_sample (
    ts            TIMESTAMPTZ NOT NULL,
    camera_id     TEXT REFERENCES camera,
    people_in_room SMALLINT NOT NULL,        -- customers + staff
    staff_in_zone SMALLINT NOT NULL
);
SELECT create_hypertable('occupancy_sample', 'ts');

-- one row per distinct visitor
CREATE TABLE visit (
    visit_id      BIGSERIAL PRIMARY KEY,
    camera_id     TEXT REFERENCES camera,
    track_id      INT NOT NULL,              -- anonymous, clip-scoped
    first_seen    TIMESTAMPTZ NOT NULL,
    last_seen     TIMESTAMPTZ NOT NULL,
    dwell_seconds REAL NOT NULL,
    continuity    REAL NOT NULL,             -- frames seen ÷ first-to-last span
    is_fragmented BOOLEAN GENERATED ALWAYS AS (continuity < 0.9) STORED
);

-- one row per staff service session
CREATE TABLE service_session (
    session_id      BIGSERIAL PRIMARY KEY,
    camera_id       TEXT REFERENCES camera,
    track_id        INT NOT NULL,
    service_seconds REAL NOT NULL,
    frames_detected INT NOT NULL,            -- observed
    frames_held     INT NOT NULL,            -- interpolated through occlusion
    zone_share      REAL NOT NULL            -- share of frames inside the service polygon
);
```

**`frames_detected` and `frames_held` are separate columns on purpose.** A
service figure that is partly interpolated must never be indistinguishable from
one that was fully observed. In the validated run for Room 5 the split is 88
observed and 6 held; in Room 1 it is 38 observed and 33 held — the same column
pair turns "14.2 seconds of service" into "7.6 seconds observed, 6.6 inferred".

### What the rows look like — measured, Room 5, 30 s

| Table | Value |
|---|---|
| `occupancy_sample` | 150 rows, mean **8.96** people, peak **10** |
| `visit` | **14** rows, mean dwell **17.88 s**, max 30.03 s |
| `service_session` | 1 row, **18.82 s**, 88 detected / 6 held, zone share 0.94 |
| Write volume | ~165 rows per camera per 30 s ≈ **0.5 MB per camera per day** |

Half a megabyte a day per camera is the number that justifies the architecture:
the same footage as video is ~15 GB/day. That contrast is worth putting on the
slide next to the database icon.

---

## 8. Numbers to annotate on the diagram

All measured, all from the committed run of Room 5:

| Annotate near | Value |
|---|---|
| Camera | 1920×1080, decimated to **4.995 fps** |
| Detector | YOLOE-11L-seg · prompt `"person"` · conf 0.25 · 1280 px |
| Detections | **2,016** raw in 150 frames, **76** duplicate boxes removed |
| Zones | 2 — `mirror` (exclude), `area pelayan` (staff) |
| Identity repair | **10** tracks split · **12** re-linked · **12** off-station frames dropped |
| Result | **14** visitors · occupancy 8.96 / 10 · dwell 17.88 s · service 18.82 s |
| Quality | **0** identity switches · 1 of 14 tracks with gaps |

---

## 9. The two zones, and why they are in the architecture rather than the code

Both are configuration, drawn as polygons over the frame, and both exist because
a detector alone gets the answer wrong:

- **Mirror — excluded.** A cafe mirror produces people who are genuinely in the
  image and genuinely not in the room. No confidence threshold separates a
  reflection from a customer, because the reflection *is* a customer — counted
  twice.
- **Service area — staff, not visitor.** A person behind the counter is not a
  visit. Dropping them loses the one measurement a manager wants from them, so
  they are tracked and timed, and reported as service.

On the slide this can be one small inset of the camera view with two shaded
polygons labelled `EXCLUDE` and `STAFF`.

---

## 10. State these limits on the slide

A diagram that shows only the happy path is a sales diagram. Three lines, small
type, bottom of the slide:

1. **Occupancy is a detection result; dwell is a tracking result.** A broken
   identity becomes two visitors who each stayed half as long. The system reports
   `continuity` per visit so this is visible rather than assumed.
2. **Held frames are interpolation, not observation**, and are stored in their
   own column.
3. **No faces, no re-identification across sessions, no demographics.** Track IDs
   are anonymous and scoped to one clip; a person leaving Room 5 and entering
   Room 1 is two visitors, and nothing claims otherwise.

---

## 11. Bill of materials

| Item | Spec | Qty |
|---|---|---|
| IP camera | 2 MP, H.264, PoE, fixed lens, ceiling mount | 2 |
| PoE switch | 8-port 1 GbE, 802.3af, 60 W budget | 1 |
| AI inference server | embedded GPU module or SFF x86 + GPU, fanless, sized to 2 cameras | 1 |
| Cabling | Cat6 UTP, per run | 2 |
| Router / firewall | outbound TLS only, VPN capable | 1 (existing) |
| Database | PostgreSQL 16 + TimescaleDB | 1 instance |
| Dashboard | Grafana or equivalent | 1 |

---

## 12. Palette suggestion

| Role | Colour |
|---|---|
| Field / cameras | slate grey |
| Edge compute (emphasis) | amber / accent |
| Network | muted blue |
| PostgreSQL (emphasis) | deep blue |
| The "no video crosses" marker | red |
| Background | white or very light neutral |

Keep the whole diagram on one horizontal axis. If it does not fit, drop section 9
(the zone inset) first and section 11 (BOM) second — sections 2, 3 and 5 are the
slide.
