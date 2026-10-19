# UkurPaket: Android app (v0.1, test build)

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
| Pickup list | Example pickups (made-up names and tracking numbers in the AnterAja format `TSA-` + digits), progress, scan the label (Google code scanner) or type the number. |
| Scan resi | Google's code scanner reads linear (1D) barcodes only, so the label's QR codes (and other 2D codes) are never picked up; the barcode's content is used as it is, with no rules on the number (on a real AnterAja label the long Code 128 barcode holds `TSA-80745081104`). **Ketik Resi** takes the number as typed. |
| Measuring (ARCore) | 1/3 find the floor (white dots), 2/3 pick the parcel, 3/3 scan (move the phone round toward the corner, animated arc arrow, depth dots, progress), result (3D box drawn on the parcel, size labels, confidence, Save locked 2 s when the result is doubtful). Flashlight button (ARCore torch). |
| Picking among many parcels | Tap the parcel, or **Pilih Area** and drag a box around it (the fix when a tap picks only part). MobileSAM cuts it out of the camera image; only depth points inside that cut-out and its footprint are measured. Other parcels in view get a dashed outline labelled **Paket lain**; tapping one picks it. **Mulai Scan** without a tap uses the crosshair as the tap. |
| Next parcel of a pickup | **Paket berikutnya** keeps the AR session: no floor search again, and the parcels already measured carry a ✓ with their tracking number. |
| Phones without ARCore | Cannot measure: the app says so, offers the ARCore install when Google Play can install it, and lets the courier mark the parcel **ukur di hub**. |
| Cannot be measured | After two failed attempts: **Gagal ukur? Ukur di Hub** with a reason. The record keeps photo, time, place and reason, without a size; the hub measures it. |
| Weight | Scale weight vs volumetric weight (divisor 4.000 / 5.000 / 6.000 in Settings); the larger is used. |
| Records | Saved on the phone with the evidence photo (photo with the 3D box), time and GPS (when the courier allows location). History, detail, delete, re-measure, share all as JSON. |
| Recording for the PC | Settings → "Rekam data scan": every AR scan also saves raw depth, confidence, camera pose, intrinsics and some frames, to replay on a PC with the same code. |

There is no manual size entry: every size comes from the camera. When it cannot give one, the parcel is marked for
the hub instead of being typed in.

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
`release/UkurPaket-0.1.0-uji.apk` (29 MB; MobileSAM is 18,8 MB of it: encoder float16 13,8 MB + decoder with int8
weights 4,6 MB, made by `tools/export_sam.py`; the int8 decoder's masks are within IoU 0,989 of float32). It installs directly (allow "install unknown apps"); for the Play Store use your own key.

## What has and has not been tested

Tested here, on the PC:

| Test | What | Result |
|---|---|---|
| `GeometryTest` | box turned 30°, 40 × 30 × 20 cm, 2 mm noise, a taller box 8 cm away; 30 × 20 × 10 cm on a floor with 0,8 cm depth noise | within 1,2 cm, neighbour left out; within 2 cm |
| `SegmenterTest` | the app's own MobileSAM code on the conveyor frame (7 parcels, some touching), one tap and one box each, vs the Python reference from the same ONNX files | mask IoU ≥ 0,985 for every tap and box (references made with the float32 decoder) |
| `ConveyorReplayTest` | the conveyor scene in 3D, each parcel measured from geometry alone and from the tap/box cut-out | geometry alone merges touching parcels; with the cut-out every parcel stays separate (README section below) |
| `FlowTest` | the courier's path through the screens: measure → weight → save → next parcel; a second tap on Simpan; re-measuring replaces the old record; Ukur di Hub on a phone without ARCore; a late hub photo after the courier left; a scanned number opens its parcel, any content is taken as it is | 5 flows, records and screen stack as expected |
| `BarcodeTest` | the barcode cut from a photo of a real AnterAja label (bars only, no personal data) read with ZXing | Code 128, `TSA-80745081104` |
| `ScannerFormatsTest` | the scanner's barcode types | the 9 linear types; QR, Data Matrix, PDF417 and Aztec left out |
| `ScreenshotTest` | every screen rendered on the JVM (`screenshots/`); camera screens on the mockup photo with the overlay the engine draws | 19 screens |
| Android lint | | no errors |

**Not tested yet**: anything that needs a real phone: ARCore tracking, depth quality, how the cut-out lines up with
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
| `data/Store.kt`, `data/Locator.kt` | records and settings in one JSON file; GPS |
| `ui/` | Compose: `Screens.kt` (start, pickup, prep, weight, saved, history, detail, settings, phone without ARCore), `MeasureScreen.kt` (camera) |
| `tools/` | `export_sam.py`, `check_sam_onnx.py` (model export and check), `fetch_icons.py`, conveyor replay scripts |

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
