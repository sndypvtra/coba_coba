# UkurPaket: Android app (v0.1, test build)

Measures a parcel's length × width × height with the phone camera, the way the courier mockup
(`../ukur_paket_mockup`) describes: method A, ARCore depth + floor detection. Native Android, Kotlin +
Jetpack Compose. Measuring runs on the phone; measurements and photos stay on it until the courier shares them.
The app needs the internet only through Google Play: once to install ARCore, and for the label scanner module.

## What is in this build

| | |
|---|---|
| Device check | First screen: phone model, ARCore installed or not, Depth API or not, and the mode that follows (AR penuh / AR dasar / manual). Asks Google Play to install *Google Play Services for AR* when it is missing. |
| Pickup list | Example pickups (made-up names and tracking numbers), progress, scan the label (Google code scanner) or type the number. |
| Measuring | 1/3 find the floor (white dots on the floor), 2/3 pick the parcel (crosshair or tap, blue outline, live size estimate), 3/3 scan (move the phone toward the corner, depth dots, progress), result (3D box drawn on the parcel, size labels, confidence, Save locked 2 s when the result is doubtful). |
| Weight | Scale weight vs volumetric weight (divisor 4.000 / 5.000 / 6.000 in Settings); the larger is used. |
| Records | Saved on the phone with the evidence photo (camera frame with the 3D box). History, detail, delete, re-measure, share all as JSON. |
| Phones without ARCore | Manual entry: L, W, H from a tape measure plus a required photo; marked "Manual · audit". |
| Recording for the PC | Settings → "Rekam data scan": every scan also saves raw depth, confidence, camera pose, intrinsics and some camera frames, to be replayed on a PC with the same code (`measure/Geometry.kt`). Share as ZIP from the detail screen or Settings. |

## How it measures (method A)

1. ARCore finds horizontal planes (the floor or a table) and tracks the phone in metres.
2. The courier's pick (crosshair or tap) is hit-tested against depth; the surface under it is the highest plane below that point.
3. Every second frame, ARCore raw depth (with confidence ≥ 90/255) is turned into 3D points and merged into 1 cm voxels.
4. `BoxFitter` keeps the points that stand on the floor near the pick, grows a connected region on a 1,5 cm grid (parcels more than ~5 cm apart stay separate), and fits the smallest rectangle around its footprint (rotating calipers): that is L × W. H is the 95th percentile of the heights.
5. Confidence (0–100) from point count, frames, how well the footprint fills its rectangle, and how flat the top is. ≥ 75 is "Akurat", below is "Cek ulang". Phones without the Depth API use ARCore feature points and are never marked "Akurat" on their own.

There is no machine-learning model in this build yet: the parcel is cut out by geometry (what stands on the floor, connected to the pick). That is enough for boxes and bags standing apart on a flat surface. A segmentation model (MobileSAM-class, Apache 2.0) for parcels that touch is the next step, once recorded scans show where geometry alone fails.

## Build

```bash
./gradlew :app:assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:testDebugUnitTest    # geometry tests + screenshots of every screen into app/screenshots/
```

JDK 17+ and the Android SDK (platform 35). Versions: AGP 8.7.3, Kotlin 2.1.0, Compose BOM 2024.12.01,
ARCore 1.47.0, minSdk 26, targetSdk 35. The debug APK is signed with the debug key, so it installs directly
(allow "install unknown apps"). For the Play Store, build a release with your own key.

## What has and has not been tested

- **Tested here**: the measuring core (`GeometryTest`: a box turned 30°, 40 × 30 × 20 cm with 2 mm noise and a taller
  box 8 cm away, measured within 1,2 cm with the neighbour left out; a 30 × 20 × 10 cm box on a floor with 0,8 cm depth
  noise, within 2 cm), Android lint without errors, and every screen rendered on the JVM (`ScreenshotTest`, copies in
  `screenshots/`; the camera screens use the mockup photo with the overlay the engine draws). The test APK is
  `release/UkurPaket-0.1.0-uji.apk`.
- **Not tested yet**: anything that needs a real phone: ARCore tracking, depth quality, speed, heat, battery. The
  first test on an ARCore phone (for example a Galaxy A35 5G / A55 5G) is where the thresholds in `MeasureEngine`
  (depth confidence, scan length, cell size) get tuned, ideally from recorded scans of 50–100 parcels with tape-measure sizes.

## Code

| File | |
|---|---|
| `measure/Geometry.kt` | the measuring core, Android-free: voxel merge, segmentation, convex hull, minimum-area rectangle, confidence |
| `ar/MeasureEngine.kt` | ARCore session, per-frame steps (find floor → pick → scan → result), depth to 3D points, overlay projection |
| `ar/BackgroundRenderer.kt` | camera image on the GL surface |
| `ar/Snapshot.kt`, `ar/Recorder.kt` | evidence photo with the 3D box; raw scan recording |
| `ar/ArCheck.kt` | ARCore availability, install request, Depth API check |
| `data/Store.kt` | orders, measurements, settings in one JSON file; Indonesian number format |
| `ui/` | Compose screens: `Screens.kt` (start, pickup, prep, weight, saved, history, detail, settings, manual), `MeasureScreen.kt` (camera + overlay + sheets) |

Fonts: Inter (SIL OFL 1.1). Icons: Material Symbols Rounded (Apache 2.0), bundled subset.
