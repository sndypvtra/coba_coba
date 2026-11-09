# UkurPaket: Android app (v0.4.0, test build)

Measures a parcel's length × width × height with the phone camera, the way the courier mockup
(`../ukur_paket_mockup`) describes: method A, ARCore depth + floor detection, with the parcel picked by a tap or a
drawn box. Native Android, Kotlin + Jetpack Compose. Everything runs on the phone, including the segmentation model;
measurements and photos stay on it until the courier shares them. The app needs the internet only through Google
Play: once to install ARCore, and for the label scanner module.

Colours follow AnterAja: magenta **#ED0677** (the buttons on anteraja.id and the logo) and yellow **#FFCB08** (the
logo); green / orange / red are kept for status only. Screen text uses the common field terms (Scan Lantai, Pilih
Paket, Pilih Area, Mulai Scan, Scan Paket, Perlu Dicek, Berat Aktual, Berat Tagih, Ukur di Hub …). The step-by-step
mockup made from these very screens is `../ukur_paket_mockup/v2`.

## What is in this build

| | |
|---|---|
| Device check | First screen: phone model, ARCore installed or not, Depth API or not, and the state that follows (Siap Ukur / Mode Dasar / Tidak Didukung), in plain words. Asks Google Play to install *Google Play Services for AR* when it is missing. |
| Scan Resi (home) | The app opens on **Scan Resi**: scan the label's barcode (Google code scanner, linear barcodes only) or type the number, and nothing else; no store names, addresses or order lists. Below it, the parcels measured today with their status (empty on first open: "Scan resi paket pertama"). |
| Scan resi | Google's code scanner reads linear (1D) barcodes only, so the label's QR codes (and other 2D codes) are never picked up; the barcode's content is used as it is, with no rules on the number (on a real AnterAja label the long Code 128 barcode holds `TSA-80745081104`). **Ketik Resi** takes the number as typed. |
| Hardware scanner (Urovo PDA) | On a Urovo PDA (DT20 and others) the scan key reads the resi: home says **Scanner HP siap · tekan tombol scan**, the camera scanner stays as **Scan pakai kamera**. Read from Urovo's broadcast (`android.intent.ACTION_DECODE_DATA`, `barcode_string`, or the raw `barcode` bytes; older firmware `urovo.rcv.message`) and from keyboard output (fast keys ending with Enter, which also covers Bluetooth/USB ring scanners). A scan opens its parcel on home, history, settings, saved and detail; while a parcel is being measured a stray press only says "Selesaikan paket … dulu". A link or multi-line text (a QR code read by mistake) is not taken as a resi. Setup below. |
| Measuring (ARCore) | 1/3 find the floor (white dots), 2/3 pick the parcel, 3/3 scan (move the phone round toward the corner, animated arc arrow, depth dots, progress), result (3D box drawn on the parcel, size labels, confidence, Save locked 2 s when the result is doubtful). Flashlight button (ARCore torch). |
| Picking among many parcels | Tap the parcel, or **Pilih Area** and drag a box around it (the fix when a tap picks only part). MobileSAM cuts it out of the camera image; only depth points inside that cut-out and its footprint are measured. Other parcels in view get a dashed outline labelled **Paket lain**; tapping one picks it. **Mulai Scan** without a tap uses the crosshair as the tap. |
| Measuring session | **Paket berikutnya** on the saved screen opens the scanner again and keeps the AR session: no floor search again, the parcels already measured carry a ✓ with their tracking number. **Selesai** closes the session. |
| Phones without ARCore | Cannot measure: the app says so, offers the ARCore install when Google Play can install it, and lets the courier mark the parcel **ukur di hub**. |
| Cannot be measured | After two failed attempts: **Gagal ukur? Ukur di Hub** with a reason. The record keeps photo, time, place and reason, without a size; the hub measures it. |
| Weight | Scale weight vs volumetric weight (divisor 4.000 / 5.000 / 6.000 in Settings); the larger is used. |
| Records | Saved on the phone with the evidence photo (photo with the 3D box), time and GPS (when the courier allows location). History, detail, delete, re-measure, share all as JSON. |
| Recording for the PC | Settings → "Rekam data scan": every AR scan also saves raw depth, confidence, camera pose, intrinsics and some frames, to replay on a PC with the same code. |

There is no manual size entry: every size comes from the camera. When it cannot give one, the parcel is marked for
the hub instead of being typed in.

## Photo mode on phones without ARCore (v0.4.0)

The DT50 sweep (v0.3.x) took its metric scale from the accelerometer, and on the DT50 that failed in the field
("Skala tidak terbaca: HP kurang digeser"): without a gyroscope, gravity has to be removed with a rotation computed
from the camera, and a 1° error leaves 0,17 m/s² of gravity in a hand movement of about 0,5 m/s². The photo mode
needs no motion at all: **one still photo** (more if wanted), taken from near a corner of the parcel, looking down.

**What the courier does.** Scan resi → **Ukur dengan foto** → stand near a corner, phone tilted 30–60° down (a chip
shows the angle; "HP diam" when still) → **Ambil foto** (taken when the phone is still) → tap the parcel or drag a box
→ size, volumetric weight and volume. **Tambah foto** from another corner: the result becomes the median of the photos,
and a spread above 10 % is flagged. **Pakai ukuran ini** → weight → saved with the photo and its box as evidence.

**How it measures** (`photo/PhotoMeasure.kt`, Android-free; models through ONNX Runtime on the phone's CPU):

| Step | |
|---|---|
| Lens | Camera2: factory calibration when it agrees with the focal length, else focal (mm) / sensor width (mm); turned upright with the sensor orientation |
| Up | the accelerometer averaged over the 0,4 s before the photo (a still phone reads gravity only: reliable, unlike integrating it) |
| Outline | MobileSAM-512 on a 480 × 640 picture, tap or box (2,2 s on the DT50) |
| Camera height | **YOLO26n-depth** (Ultralytics, ONNX 640 × 480, 20 MB; ~1,3 s on the DT50, estimated from the PC/DT50 ratio): a level plane (within 20° of the accelerometer's) is found among the floor pixels round the object; the camera height is the median, over thousands of them, of how far below the camera each lies. This is the **only** number taken from the AI |
| Geometry | single-view metrology with that height: the outline's lower edge on the floor (near half of the footprint), its left and right sides as vertical edges (bottom on the floor, top at H), its upper edge on the plane at H (far half); footprint = smallest rectangle round both halves; the box drawn from it is compared with the outline (IoU) |
| Score | box-like when IoU ≥ 0,92 (a carton ~0,98, a gallon or sack ~0,8); notes for an object cut by the picture's edge, a bad angle, an implausible camera height, little floor, an uncalibrated phone. "Akurat" needs a calibrated phone, a box-like object, a whole object and a score ≥ 75 |

Every size scales with the camera height, so the AI's scale error scales the whole result and nothing else. That is
what **Kalibrasi mode foto** (Settings) removes: photos of cartons whose size is typed from a tape measure; the
phone's factor is the median of tape / measured over every side of every carton (3 cartons recommended; the card shows
the spread). Without calibration the result is never "Akurat" and says so.

**Tested on the PC** (`PhotoMeasureTest`, synthetic photos from `tools/photo/synth_photo.py`: 480 × 640, f 420 px,
camera 0,75–1,15 m above the floor, 38–62° down):

| | Truth (cm) | Photo mode with the true camera height | Notes |
|---|---|---|---|
| Carton, true outline, 4 photos | 40 × 30 × 20 | 39,9–40,1 × 29,9–30,2 × 20,4–20,6 | IoU 0,97–0,98 |
| Carton, MobileSAM-512's outline from a box, 4 photos | 40 × 30 × 20 | 40,0–40,5 × 29,7–31,8 × 19,8–21,1 | SAM vs true mask IoU 0,95–0,98 |
| Gallon (cylinder) | 27 × 27 × 40 | 20–25 × 19–23 × 43–48 | rough, flagged "bukan kotak" |
| Sack | 45,4 × 30,2 × 19 | 47–50 × 29–32 × 8–10 | footprint fair, height under (bulging sides): flagged |

Also: a depth map 20 % off in scale gives sizes 20 % off, and the calibration factor brings them back to ±1 cm; an
object cut by the edge is never "Akurat"; a phone held upright is refused with advice. **What the synthetic photos
cannot test is the depth model's scale on real photos** (on these artificial pictures it is off by a factor 0,3–1,3,
which says more about the pictures than about the model): that is the phone test, with calibration. Ultralytics'
own figures for the released model: NYU AbsRel 0,109; with its built-in scale, 4–46 % off on other cameras, which is
why the per-phone calibration exists.

**Limits.** Estimation class, not a certified (legal-for-trade) dimensioner. Built for cartons; round, soft and
bulging parcels get a rough outer box and "Perlu Dicek". The camera must be above the parcel's top (standing), the
parcel whole in the picture with some floor round it, on the floor or a table (not on another parcel).

**Files** (`files/photo_sessions/<time>/`, shared as ZIP from the screen or Settings): `photo_N.jpg` (upright, full
size), `mask_N.png`, `depth_N.u16` (mm, little-endian, size in the record), `shot_N.json` (lenses, acceleration, the
pick, timings, the result, the tape size when typed), `evidence.jpg` once used. Everything needed to rerun on a PC.

## How it measures (method A)

1. ARCore finds horizontal planes and tracks the phone in metres.
2. The courier taps or draws a box; MobileSAM (Apache 2.0, ONNX Runtime) cuts the parcel out of that camera image.
   A 3D point belongs to the parcel when it projects inside the (slightly grown) cut-out as seen from that frame
   and lies within 4 cm of the footprint of the depth points inside it. So the hidden back of the parcel still counts
   and a neighbour standing behind it does not.
3. Every second frame, raw depth (confidence ≥ 90/255) becomes 3D points, merged into 1 cm voxels.
4. `BoxFitter` keeps the points standing on the floor, grows a connected region on a 1,5 cm grid and fits the
   smallest rectangle around its footprint (rotating calipers, 0,5/99,5 % extents): L × W. H is the 95th percentile height.
5. Confidence (0–100) from point count, frames, footprint fill and top flatness. ≥ 75 is "Akurat", below is "Perlu Dicek" (shown as "Skor").
   Phones without the Depth API use ARCore feature points and are never "Akurat" on their own.

## Build

```bash
./gradlew :app:assembleRelease      # app/build/outputs/apk/release/app-release.apk (signed with the debug key)
./gradlew :app:testDebugUnitTest    # all tests below + screenshots of every screen into app/screenshots/
```

JDK 17+ and the Android SDK (platform 35). AGP 8.7.3, Kotlin 2.1.0, Compose BOM 2024.12.01, ARCore 1.47.0,
ONNX Runtime 1.20.0, minSdk 26, targetSdk 35, arm64-v8a + armeabi-v7a. The test APK is
`release/UkurPaket-0.4.0-uji.apk` (about 75 MB; the photo mode's depth model is 20 MB of it; MobileSAM is two models: the 1024 one for ARCore phones, encoder float16
13,8 MB + decoder with int8 weights 4,6 MB, made by `tools/export_sam.py`, the int8 decoder's masks within IoU 0,989 of
float32; and the 512 one for PDAs, encoder float32 28 MB + decoder 4,7 MB, made by `tools/export_sam512.py`). It installs directly (allow "install unknown apps"); for the Play Store use your own key.

## Urovo DT20 (and other Urovo PDAs)

The DT20 (Android 11, MediaTek Helio P22) is **not on Google's ARCore device list**, so on it the app can scan,
type and mark parcels **Ukur di Hub**, but it cannot measure. The device check shows *Tidak Didukung*. The setup
used in the field: the DT20 scans, an ARCore phone (for example a Galaxy A35 5G / A55 5G) measures.

Scanner settings on the DT20 (Settings → Scanner, the names vary a little by firmware):

1. **Output mode: Intent output** (recommended). Keep the default action `android.intent.ACTION_DECODE_DATA` and
   the string label `barcode_string`. Keyboard output also works, but only on screens without a text field.
2. **Symbologies**: switch off QR Code, Data Matrix, PDF417 and Aztec, so the QR codes on the label are never read
   (the app also ignores links, but a QR holding plain text would pass).
3. Leave "Add Enter/suffix" as it is: the app trims spaces and line ends.

`scan/HardwareScanner.kt` holds the receiver and the keyboard reader. The receiver is registered only while the app
is in front.

### DT20 test tools (v0.2.0): diagnosis and sweep recorder

The groundwork for our own engine in place of ARCore on the DT20: camera + motion sensors (visual-inertial), solved
after the sweep, then the same pick → points → `BoxFitter` → result as method A. This build records and checks; it
does **not** compute a size yet. The recordings are what the solver is built and tested on, on a PC first.
Entry: home card **Uji DT20** (phones without ARCore), the start screen, Settings, and the no-ARCore screen.

| Screen | What it does |
|---|---|
| **Diagnostik HP** (`dt/Diagnostics.kt`) | Device, chip, RAM; each motion sensor with its rated and **measured** rate (3 s at the fastest rate); the back camera's Camera2 facts (hardware level, timestamp source, focus calibration and control, AE/AWB lock, OIS, YUV sizes and fps, factory intrinsics if any); MobileSAM speed test. Each requirement of the engine gets ✅ / ⚠️ / ❌ with the reason (no gyroscope = ❌; camera and sensor clocks not shared = ⚠️). Shared as JSON. |
| **Perekam DT20** (`dt/SweepRecorder.kt`) | Camera2 preview + YUV frames (4:3 near 1280 × 960, falls back to 640 × 480) saved as JPEG at ~15/s, every accelerometer / gyroscope (+ uncalibrated, magnetometer, gravity, rotation vector) event at the fastest rate. Focus, exposure and white balance locked while recording; OIS and video stabilisation off (they move the image against the lens). Live: fps, sensor Hz, turn angle against a 60° target. **Klik objek / Tarik kotak on the live picture** picks the object and starts recording at once (frame 0 is the picked view); MobileSAM cuts it out when recording stops, not during it (on the PDA's CPU it would cost frames). **Mulai tanpa pilih** records first and picks later. |
| **Rekaman DT20** (`dt/SweepQuality.kt`, `dt/ObjectPick.kt`) | Checks the files just written: length, frames/s and gaps, sensor rates, same clock and coverage, turn angle, **acceleration** (no acceleration = no metric scale), blurred frames. Then **any object** is picked in the sharpest frame (or another, slider): **Klik objek** or **Tarik kotak**, cut out by MobileSAM. Name and the tape-measure size (optional) are saved with it. Share the recording as ZIP. |

One recording folder (`files/dt_sessions/<time>/`): `frames/NNNNN.jpg`, `frames.csv` (index, camera timestamp, sharpness),
`capture.csv` (per-frame exposure, frame duration, rolling-shutter skew, focus distance, AF/AE state, ISO), `imu.csv`
(sensor, timestamp, values), `session.json` (size, sensor orientation, clock), `diagnosis.json`, and after the pick
`pick.json` + `mask.png` + `pick_overlay.jpg`. Frames are stored as the sensor sees them; `pick.json` coordinates are
in the upright picture (rotated by the sensor orientation).

Not tested on a DT20 yet: everything with the real camera and sensors (Camera2 session, locks, rates, files on
the device). Tested here: the diagnosis rules, the quality check on synthetic sweeps and on the file format, the
recorder's size choice and sharpness score, the navigation, and the screens (`18`–`20`; the diagnosis screenshot uses
test values, not a DT20 reading; the pick screenshot runs the app's MobileSAM on the parcel photo with a box).

### The first real DT50 recordings (v0.3.3)

Recording 20261104_171719 (a plush toy on a dark blanket, dim room) failed with "Putaran HP tidak terbaca dari
kamera". What it showed: 7,9 saved frames/s (the CPU shared by JPEG, tracking and MobileSAM), a 304 ms hole, a dim
picture, no rotation sensor. MobileSAM-512 measured on the DT50 itself: **2,2 s** per picture (1024 float16: 13,7 s).
The same conditions are now a test (`SweepEngineTest.dt50LikeRecordingSlowBlurredDim`: every 2nd frame, two frames
dropped, every 4th blurred, two flat frames, everything darkened with noise), which failed with the same message.
Fixed, in the order the test showed them:

| Weakness | Fix |
|---|---|
| a bad frame kills every track, so the sweep falls apart in two | `Tracker`: when most tracks are lost, the last good frame's tracks (up to 5 frames back) are followed straight from it |
| one frame without a pair stopped the camera-rotation chain | `VisualRotation.solve`: spread from a reference both ways; frames without pairs interpolated; pairs up to 12 frames apart; a 3 px retry for blurred pairs; fails only below 60 % of frames |
| a frame that sees nothing left the linear system singular | `Vision.linear`: such a frame's centre tied to the middle of its neighbours |
| that guessed centre spoilt the scale | the inertial fit uses only frames whose position was measured (and inside the accelerometer's recording); the accelerometer is integrated past the others |
| the picked frame blurred just after the touch: no seed points | seeds also from the 3D points that project into the pick mask, the nearest ones (the object's front) |
| long exposures in a dim room blur every frame | recording keeps the preview's brightness at ≤ 1/80 s (manual exposure, the gain makes up), a "Terlalu gelap" chip below a mean luma of 55 |
| the CPU too busy for ≥ 10 frames/s | JPEG quality 85, the tracking thread above MobileSAM, MobileSAM re-cuts at most every 3 s |
| "Data sensor tidak menutupi semua foto" on every DT50 recording | the check asked for a gyroscope; now the sensors there are, to 0,15 s |

Degraded synthetic sweeps (36 frames, accelerometer only): box 40 × 30 × 20 → 40,3 × 30,9 × 21,2 cm; sack
45,4 × 30,1 × 19 → 43,4 × 27,9 × 20,1 cm. The result card shows the size, the **volumetric weight** (P × L × T ÷ the
divisor in Settings) and the volume without any input; a recording whose object is picked is measured on opening,
and a new pick on the review screen is measured at once. Only the actual weight (a scale) is still typed in, on the
weight screen, for the charged weight. The diagnosis no longer marks a silent gyroscope red: the engine runs on the
camera and the accelerometer.

### No rotation sensor, and the size within seconds of Selesai (v0.3.2)

**The DT50 recording that failed** ("Tidak ada data putaran"): its imu.csv had neither gyroscope nor rotation-vector
events. On that phone the rotation vector is fused from the gyroscope, so when the gyroscope's driver sends nothing,
both are silent; only the accelerometer works. No app setting can make the driver send, so the engine no longer needs
it: **the camera's own rotation** (`vio/VisualRotation.kt`):

1. relative rotations for frame pairs (i, i+1 / +2 / +4 / +8) from the tracked points: essential matrix (normalised
   8-point, RANSAC on the Sampson error, refitted on the inliers, the rotation chosen by points in front of both
   cameras); a pair that fits a pure turn as well (short baseline) uses that turn (Kabsch);
2. rotation averaging over all pairs (Gauss-Newton on the tangent space, Huber), so single-pair errors do not add up;
3. bundle adjustment with a looser rotation prior; gravity and the accelerometer's clock offset solved with the scale
   (offset: the best inertial fit over −80…+40 ms).

The recorder still tries every gyroscope the phone lists; a rotation sensor, when one sends, is used as before.

| Synthetic DT50 sweep, accelerometer only | Truth (cm) | Camera rotation (cm) | With the rotation vector (cm) |
|---|---|---|---|
| box | 40 × 30 × 20 | 39,2 × 29,4 × 20,9 | 39,6 × 29,5 × 21,0 |
| sack | 45,4 × 30,1 × 19 | 43,2 × 25,8 × 19,0 | 42,9 × 25,0 × 19,0 |

**Speed.** The engine's tracking (the largest part, 3,2 s of 5 s on this PC) now runs **while recording**
(`vio/RecordingTracker.kt`): every saved frame, in order, goes to the engine's tracker on its own thread, its KLT spread
over the cores, and the same tracks drive the live segmentation (one tracker, not two). The greys stay in memory, so
no JPEG is read back. The independent parts left (clock and focal search, frame pairs, the 64 depth planes) run on all
cores. On this PC (4 cores): tracking 1,4–1,6 s for 75 frames, i.e. faster than the recording itself; after
**Selesai** 1,3–2,6 s to the size. On the DT50 expect several times that (not measured yet: `result.json` and the
result card show the seconds).

Phone path on the test video (the recording tracker driving the live segmentation): IoU 0,93 median against
MobileSAM-1024 on frames 0–54, the lighter followed until it leaves the picture.

### Live segmentation while recording (v0.3.1, `vio/LiveSeg.kt`)

The object is cut out the moment it is touched (tap, or a box dragged round it like a snipping tool), and its mask is
drawn over the preview on every frame while recording. When **Selesai** is pressed the cut from the touch is already
saved, so the size, volume and volumetric weight are computed straight away, with no second pick.

**Why MobileSAM was not live before.** The shipped 1024 encoder is float16. ARM cores without native float16 (the
DT50/DT20 class) run it emulated: the DT50 took 13,7 s per picture. Two changes:

| | 1024, float16 (ARCore phones) | 512, float32 (PDAs) |
|---|---|---|
| Model | MobileSAM as published | the same weights; TinyViT rebuilt at img_size 512 (window attention biases depend on the window, not the picture), 32 × 32 embedding, decoder with the 32 × 32 positional grid |
| Encoder, this PC (4 threads) | 1,57 s | **0,15–0,20 s** (7,7× less) |
| Box prompt vs the 1024 masks (7 parcels on the conveyor frame) | reference | IoU 0,83–0,96, median 0,91 |
| Tap prompt | reference | lone tap 0,57–0,94; **tap → its box → box + tap again** (`Segmenter.tapRefined`): 0,77–0,97 |
| On the DT50 | 13,7 s (measured) | not measured yet: Diagnostik → **Uji SAM** times it, and keeps XNNPACK or the default CPU kernels, whichever is faster |

**Live loop** (`LiveSegmenter`, on its own thread, newest frame only):
1. touch → MobileSAM-512 on that frame (box, or refined tap); until it answers the box/disc is shown;
2. every frame: KLT on the object's points (4 pyramid levels, for 40–60 px jumps), a similarity carries the mask; with
   fewer than 8 object points (blur, thin objects) the points round the object give the motion, and new corners are
   added inside it;
3. the edges, within 3 cells of the carried mask, follow the object's and background's colours learnt from the last
   MobileSAM answer;
4. MobileSAM runs again whenever it is free, prompted with the box of the mask and the tracked points; of its three
   answers the one most like the carried mask is taken if it covers ≥ 60 % of the object's points.

`LiveSegTest` (synthetic DT50 sweeps, true mask on every frame, `synth_sweep.py --masks`), IoU per frame:

| Sweep | MobileSAM every 12 frames | every 30 frames (slow phone) | every 30, without the colour edges |
|---|---|---|---|
| box | median 0,96, min 0,88 | 0,90, min 0,73 | 0,86, min 0,62 |
| sack | median 0,98, min 0,95 | 0,96, min 0,76 | 0,75, min 0,57 |

On the hand-held test video (lighter on a glass table, 15 fps, fast pans; not committed, it shows people;
`LiveSegVideoTest -Pukur.video=…`), against MobileSAM-1024 on frames 0–54 where that reference is right: median 0,92
with MobileSAM every 12 frames. The live mask stays on the lighter until it leaves the picture at ~8 s, through blur and
the lighter turning to its other side. Carrying the refined edges on from frame to frame (instead of from the carried
mask) did better on the synthetic sweeps but crept into the glass table here (0,32), so it is off.

**Gyroscope on the DT50.** The default gyroscope is listed at 200 Hz but sends nothing. The game rotation vector
(200 Hz, smooth) is computed from the gyroscope, so the hardware works; only the raw events are not passed on. The
recorder now registers every gyroscope listed (calibrated and uncalibrated, wake-up or not) and records the first
that sends (`session.json`: `gyroscope_used`, events per sensor); the engine also reads the uncalibrated one (rate
minus drift). Diagnostik tries each at three rates and shows whether Android accepted it. If none sends, the rotation
vector is used, as in 0.3.0.

### Measuring without ARCore on the phone (v0.3.0, `vio/`)

Phones without ARCore (Urovo DT50/DT20) now measure: scan resi → **Ukur dengan sapuan** → touch the parcel or drag a
box round it on the live picture (recording starts) → walk round it → **Selesai** → the size comes out on the phone →
**Pakai ukuran ini** → weight → saved (method "Sapuan", with the evidence photo). Same steps and output as method A.

| Step | On the phone (pure Kotlin, no new libraries) |
|---|---|
| Live segmentation | `LiveSegmenter` (0.3.1, above): MobileSAM-512 + tracking + colour edges, the mask on every frame |
| Tracks | `Klt.kt`: pyramidal Lucas-Kanade, forward-backward checked, Shi-Tomasi corners (up to 700 over 480 × 640) |
| Rotations | game rotation vector (or integrated gyroscope); camera clock mapped by arrival times; time offset and focal length searched on the reprojection error |
| Structure | `Vision.linear`: points on their viewing rays, a homogeneous system (points eliminated by Schur) solved as its smallest eigenvector, reweighted to pixels; then `Vision.bundleAdjust` (Gauss-Newton/LM with Schur, Huber, sensor rotations as prior) |
| Metric scale | `Inertial.align`: accelerometer between frames vs the camera path: scale, velocities, bias (gravity known from the rotation vector) |
| Object | seeds = tracks in the pick mask (MobileSAM); support plane by RANSAC; **plane-sweep depth** (ZNCC, 64 planes) on the picked frame inside its mask and on 5 more views; dense points standing on the plane, grown in 3D from the picked frame's; box rule as method A |
| Every frame | the object's outline and the box projected into each frame (review slider; evidence photo) |

`SweepEngineTest` runs this code on synthetic DT50-like sweeps (gyroscope silent, rotation vector only, camera clock
apart, pick on frame 0; `tools/dt20/synth_sweep.py --dt50 --pick-first`): box 40 × 30 × 20 → **39,7 × 29,5 × 21,0 cm**;
irregular sack 45,4 × 30,1 × 19 → 41,8 × 24,5 × 19,1 cm (round, dark, low-texture surfaces come out small: no depth
where there is no texture, and the far side is not seen). ~8 s on this PC's JVM; on the phone CPU expect several
times that (not measured yet). `tools/dt20/vio_proto.py` is the Python prototype it was ported from.
Not tested on a real DT50 yet: its rotation vector quality (its gyroscope reported nothing), rolling shutter, motion
blur, plain cardboard, glass tables (reflections).

### Engine without ARCore: PC reference (`tools/dt20/`)

What the recordings are for. `solve.py` turns one recording into L × W × H; it runs on a PC for now, so that the
method can be measured on real DT20/DT50 sweeps before it is ported to the phone. Licences are not a constraint here
(open source, GPL allowed); the parts used are COLMAP (BSD), SciPy and the app's MobileSAM.

1. **Structure from motion** (COLMAP via pycolmap): camera poses and sparse 3D points, scale unknown.
2. **Clock and axes**: IMU ↔ camera time offset (gyro vs visual turn rate), camera ← device rotation (Kabsch), gyro bias.
3. **Visual-inertial alignment** (as in the VINS-Mono initialisation): with the rotations from vision, the accelerometer
   integrated between frames must match the camera path. One linear system in scale, gravity, accelerometer bias and
   velocities, each row weighted by its noise, then |g| = 9,81 m/s². Scale exists only when the phone accelerates.
4. **Floor**: plane of sparse points perpendicular to gravity; the angle between them is reported.
5. **Object**: masks in 9 keyframes (MobileSAM prompted from the pick, two rounds), points voted inside ≥ 80 % of the
   masks that see them, mask outlines lifted to 3D; least-area rectangle + 97th-percentile height, as method A.

`synth_sweep.py` makes test sweeps in the recorder's own format with a known object: textured floor and object, a
walk of ~80° round it, accelerometer/gyroscope at 200 Hz with phone-grade noise and bias and a 12 ms clock offset; the
`--dt50` variant has what the DT50 reported (gyroscope silent, only the game rotation vector; camera clock 3,2 s off,
frames arriving 35 ± 5 ms late). `run_synth.py` runs the cases below (`docs/dt_engine_synthetic.jpg`, `…_summary.json`):

| Case | Truth (cm) | Engine (cm) | Error (cm) | Scale error | Time offset (truth 12 ms) |
|---|---|---|---|---|---|
| box, seed 0 | 40 × 30 × 20 | 41,6 × 32,9 × 21,2 | +1,6 / +2,9 / +1,2 | +0,99 % | 11 ms |
| cylinder (gallon) | 27 × 27 × 40 | 24,5 × 24,1 × 40,2 | −2,5 / −2,9 / +0,2 | −0,69 % | 13 ms |
| sack (irregular) | 45,4 × 30,1 × 19 | 41,8 × 32,5 × 19,1 | −3,6 / +2,4 / +0,1 | −0,68 % | 13 ms |
| box, seed 1 | 40 × 30 × 20 | 41,6 × 30,2 × 21,1 | +1,6 / +0,2 / +1,1 | +0,91 % | 10 ms |
| cylinder, seed 1 | 27 × 27 × 40 | 25,4 × 24,8 × 40,4 | −1,6 / −2,2 / +0,4 | −0,38 % | 11 ms |
| sack, seed 1 | 45,4 × 30,1 × 19 | 42,8 × 29,2 × 18,9 | −2,6 / −0,9 / −0,1 | −0,34 % | 11 ms |
| box, DT50 mode | 40 × 30 × 20 | 41,3 × 32,5 × 21,1 | +1,3 / +2,5 / +1,1 | +0,18 % | (after arrival mapping) |
| sack, DT50 mode | 45,4 × 30,1 × 19 | 42,9 × 29,3 × 18,9 | −2,5 / −0,8 / −0,1 | −0,16 % | (after arrival mapping) |
| phone only turned, not moved | | refused: "HP harus digeser mengitari objek" | | | |

Mean size error 1,5 cm, largest 3,6 cm; scale within ±1 % in every case, the DT50 variant included; ~80 s per sweep on
this PC (4 cores). Pattern: boxes come out 1–3 cm large, round and soft objects 2–4 cm small (sparse points thin out at
their edges). What the simulation leaves out: rolling shutter, motion blur, autofocus, lens distortion, the
camera–IMU lever arm, plain untextured cardboard, real sensor quirks. So these numbers are an upper bound on what to
expect; the real answer comes from DT20/DT50 recordings with tape-measured sizes. Next: run it on those, then choose
how to put it on the phone (SfM on the device's CPU is the expensive part).

### Smoke test: the resi label as the ruler (no ARCore, no extra items)

`tools/smoke_label_ruler.py` (opencv-python-headless, onnxruntime, zxing-cpp, python-barcode) runs on the two photos
already in the test resources. Result image: `docs/smoke_label_ruler.jpg`.

| Step | Result |
|---|---|
| Courier's box → MobileSAM (the app's own ONNX files) on `paket.jpg` (black poly mailer) | mask score 0,994, clean outline |
| Label patch → 4 corners (Otsu inside the parcel mask) | found; width/height recovered from perspective 1,06–1,07, so the patch is about square |
| Parcel outline in cm through the label homography | 28,3 × 15,0 cm if the label is 10 × 10 cm; 31,0 × 22,0 cm if 10 × 15 cm |
| Sensitivity to the label edge | a fixed threshold instead of Otsu (corners ±15–30 px) gives 30,8 × 16,4 cm: **about 8 %** |
| Height | not measurable from one top-down photo (needs gravity from the phone and a second view) |
| Barcode crop as ruler | decodes `TSA-80745081104`; the best Code 128 encoding (B + C, 156 modules) fits the bars only weakly (0,42), so this soft crop gives no reliable module width |

What it shows: the steps run, and with this photo the size depends on facts it does not have. The label here is
blurred for privacy, so its edges are soft, and its real size and the parcel's real size are unknown. The outline is
measured on the label's plane, while the parcel's widest part lies lower, so a parcel 8 cm thick seen from about
25 cm reads roughly 10–15 % small. Next: sharp DT20 photos (label readable, 2–3 views) of parcels measured with a tape.

## What has and has not been tested

Tested here, on the PC:

| Test | What | Result |
|---|---|---|
| `GeometryTest` | box turned 30°, 40 × 30 × 20 cm, 2 mm noise, a taller box 8 cm away; 30 × 20 × 10 cm on a floor with 0,8 cm depth noise | within 1,2 cm, neighbour left out; within 2 cm |
| `SegmenterTest` | the app's own MobileSAM code on the conveyor frame (7 parcels, some touching), one tap and one box each, vs the Python reference from the same ONNX files | mask IoU ≥ 0,985 for every tap and box (references made with the float32 decoder) |
| `ConveyorReplayTest` | the conveyor scene in 3D, each parcel measured from geometry alone and from the tap/box cut-out | geometry alone merges touching parcels; with the cut-out every parcel stays separate (README section below) |
| `PhotoMeasureTest` | the photo mode's engine on synthetic photos (carton, gallon, sack; 2 photos each, two cartons): sizes from the outline with the true camera height; every size scales with the camera height; the camera height from a floor depth map; a 20 % depth-scale error and the calibration that removes it; an object cut by the edge, a phone held upright; Camera2 lens facts turned upright; combining photos; the calibration factor; then the real MobileSAM-512 and YOLO26n-depth on the photos | cartons within 1 cm (true outline) / 1,8 cm (MobileSAM's); 7 tests pass |
| `FlowTest` | the courier's path through the screens: first open with nothing but the scanner; measure → weight → save → next parcel in the same session → Selesai starts a new one; a second tap on Simpan; re-measuring replaces the old record; Ukur di Hub on a phone without ARCore; a late hub photo after the courier left; a scanned number opens its parcel (or its record if measured already), any content is taken as it is; a data file of an earlier test build still loads; the photo mode: no-AR screen → photo → weight → saved as "Foto", then a calibration sample | 8 flows, records and screen stack as expected |
| `HardwareScannerTest` | Urovo detection; the three broadcast formats (string, bytes + length, older `urovo.rcv.message`); a broadcast reaching the registered receiver; a scan key press on home opens the parcel, while measuring it does not, a QR link is ignored; keyboard output: fast keys + Enter is a scan, slow keys are not, Back/volume pass through | 5 tests pass |
| `Dt20Test` | DT20 tools: diagnosis rules (no gyroscope, separate clocks, slow sensors, fixed focus), sweep quality on synthetic sweeps (good, still phone, too short, no motion sensors) and read back from the recorder's file format, size choice, sharpness, cm parsing, the scan key on the test screens, review navigation | 6 tests pass |
| `BarcodeTest` | the barcode cut from a photo of a real AnterAja label (bars only, no personal data) read with ZXing | Code 128, `TSA-80745081104` |
| `ScannerFormatsTest` | the scanner's barcode types | the 9 linear types; QR, Data Matrix, PDF417 and Aztec left out |
| `ScreenshotTest` | every screen rendered on the JVM (`screenshots/`); camera screens on the mockup photo with the overlay the engine draws | 24 screens (`17` home on a Urovo PDA without ARCore, `18`–`20` DT20 diagnosis, recorder, pick); the photo mode on the DT50's screen size `40`–`47` (camera, angle warning, pick, result, test, calibration, settings, weight) |
| Android lint | | no errors |

**Photo mode, not tested yet** (needs a DT50): the Camera2 still and the accelerometer's axes on the phone (the
mapping follows Android's documented axes and is unit-tested, not seen on the device), the lens facts the DT50 reports,
the depth model's speed there (~1,3 s estimated) and, above all, its camera-height scale on real photos, i.e. how much
the calibration has to correct and how much it varies from photo to photo. The first test: calibrate with 3 cartons,
then measure 5–10 others against a tape measure (the result screen shows the difference when the tape size is typed).

**Not tested yet**: anything that needs a real phone, including the scan key on a real DT20: ARCore tracking, depth quality, how the cut-out lines up with
depth on a moving phone, MobileSAM speed on a phone CPU (about 3–5 s per tap on this PC's CPU in the tests; a phone
may be similar or slower), heat, battery. The first test on an ARCore phone (for example a Galaxy A35 5G / A55 5G) is where the
thresholds get tuned, ideally from recorded scans of 50–100 parcels with tape-measure sizes.

## Code

| File | |
|---|---|
| `measure/Geometry.kt` | Android-free measuring core: voxel merge, segmentation, clusters ("Paket lain"), convex hull, minimum-area rectangle, confidence |
| `measure/Segmenter.kt` | MobileSAM through ONNX Runtime: tap / box → mask; mask outline, largest part, dilation |
| `ar/MeasureEngine.kt` | ARCore session, per-frame steps, tap/box pick, depth to 3D points, fence, other parcels, done marks, torch |
| `ar/BackgroundRenderer.kt`, `ar/Snapshot.kt`, `ar/Recorder.kt` | camera image; evidence photo; raw scan recording |
| `ar/ArCheck.kt` | ARCore availability, install request, Depth API check |
| `dt/` | DT20 tools: `Diagnostics.kt`, `SweepRecorder.kt` (Camera2 + motion sensors), `SweepQuality.kt`, `ObjectPick.kt`; screens in `ui/DtScreens.kt` |
| `photo/` | the photo mode (0.4.0): `PhotoMeasure.kt` (camera height, single-view metrology, combining photos, calibration; Android-free), `DepthModel.kt` (YOLO26n-depth through ONNX Runtime), `PhotoCamera.kt` (Camera2 still + accelerometer + lens), `PhotoFiles.kt`; state in `ui/PhotoFlow.kt`, screens in `ui/PhotoScreen.kt` |
| `scan/HardwareScanner.kt` | Urovo scan key: broadcast receiver and keyboard-output reader |
| `data/Store.kt`, `data/Locator.kt` | records and settings in one JSON file; GPS |
| `ui/` | Compose: `Screens.kt` (start, scan resi, prep, weight, saved, history, detail, settings, phone without ARCore), `MeasureScreen.kt` (camera) |
| `tools/` | `export_sam.py`, `check_sam_onnx.py` (model export and check), `export_depth.py` (YOLO26n-depth), `photo/synth_photo.py` (synthetic photos with truth), `fetch_icons.py`, conveyor replay scripts |

Fonts: Inter (SIL OFL 1.1). Icons: Material Symbols Rounded (Apache 2.0), bundled subset. Model: MobileSAM (Apache 2.0).
Runtime: ONNX Runtime (MIT).

## Many parcels in one view: replay on the conveyor PoC

`tools/conveyor_scene.py` turns frame 471 of the parcel-belt PoC (`../03_parcel_dimensioning`, 7 parcels, some
touching, its calibrated Depth Anything 3 depth) into 3D points plus one "tap" per parcel; `ConveyorReplayTest`
measures each tap with this app's core. `tools/conveyor_masks.py` adds MobileSAM masks (prompted by the tap point,
and by a box) and the test measures only the depth points inside each mask. `tools/conveyor_draw.py` draws both:
`docs/conveyor_test.jpg`.

| | Result |
|---|---|
| Geometry only | parcels that touch are merged: #28, the printed 720 × 500 × 340 mm carton, comes out 140 × 42 × 70 cm |
| Tap or box → MobileSAM mask → depth inside the mask (what the app now does) | every parcel is cut out on its own; #28 stays one carton |
| Tap point vs box | with the app's rule (best of the three masks the model returns) the tap and the box agree on all 7 (IoU 0,93–0,99), the sports bag (#41) included |
| Absolute size from this view | off (#28 reads 84 × 40 × 28 cm): the camera is low, 2–3 m away and very oblique, so the back and top of each parcel are barely seen. The app's own view (0,5–1,5 m, from above at 30–45°, moving the phone) is different; its accuracy is a phone test, not this replay. |
