package id.ukurpaket.app

import android.app.Activity
import android.app.Application
import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.github.takahirom.roborazzi.captureRoboImage
import id.ukurpaket.app.ar.ArState
import id.ukurpaket.app.ar.DeviceCaps
import id.ukurpaket.app.ar.EngineUi
import id.ukurpaket.app.ar.Hint
import id.ukurpaket.app.ar.MeasureEngine
import id.ukurpaket.app.ar.Overlay
import id.ukurpaket.app.ar.Phase
import id.ukurpaket.app.ar.ResultData
import id.ukurpaket.app.data.Measurement
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.measure.BoxResult
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.ui.App
import id.ukurpaket.app.ui.AppModel
import id.ukurpaket.app.ui.ArChrome
import id.ukurpaket.app.ui.Draft
import id.ukurpaket.app.ui.LocalStill
import id.ukurpaket.app.ui.SamState
import id.ukurpaket.app.ui.Screen
import id.ukurpaket.app.ui.UkurTheme
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import kotlin.math.hypot
import android.graphics.Bitmap
import android.graphics.Matrix
import id.ukurpaket.app.dt.ObjectPick
import id.ukurpaket.app.dt.Pick
import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.ui.C
import id.ukurpaket.app.ui.DtRecordPreview
import id.ukurpaket.app.ui.LocalStillValue

/**
 * Renders every screen on the JVM, phone size 412 x 892 dp at 3x, into app/screenshots/.
 * The AR camera screens use the parcel photo from the mockup with the overlay the engine would draw;
 * the camera picture itself only exists on a real phone.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "w412dp-h892dp-xxhdpi")
class ScreenshotTest {
    private val app: Application = RuntimeEnvironment.getApplication()
    private val d = 3f
    private val k = 412f / 899f
    private val geom = Json.parseToJsonElement(javaClass.getResource("/geom.json")!!.readText()).jsonObject
    private fun pts(key: String) = geom[key]!!.jsonArray.map { p -> p.jsonArray.let { it[0].jsonPrimitive.float to it[1].jsonPrimitive.float } }

    private fun px(list: List<Pair<Float, Float>>, oy: Float) = FloatArray(list.size * 2).also { a ->
        list.forEachIndexed { i, (x, y) -> a[2 * i] = x * k * d; a[2 * i + 1] = (y * k + oy) * d }
    }

    private fun resource(name: String): String {
        val f = File(app.filesDir, name)
        f.outputStream().use { o -> javaClass.getResourceAsStream("/$name")!!.copyTo(o) }
        return f.path
    }

    private fun model(mode: Mode = Mode.AR_FULL): AppModel {
        File(app.filesDir, "ukurpaket.json").delete()
        val m = AppModel(app, checkDevice = false)
        m.caps = when (mode) {
            Mode.AR_FULL -> DeviceCaps(ArState.READY, true, "samsung SM-A356E")
            Mode.AR_BASIC -> DeviceCaps(ArState.READY, false, "samsung SM-A245F")
            Mode.NONE, Mode.SWEEP, Mode.PHOTO -> DeviceCaps(ArState.UNSUPPORTED, false, "samsung SM-A055F")
        }
        m.samState = SamState.READY
        return m
    }

    private val thumb by lazy { resource("thumb.jpg") }

    private fun measured(resi: String, l: Double, w: Double, h: Double, kg: Double?, status: Status = Status.OK) =
        Measurement(resi = resi, session = "s1", lengthCm = l, widthCm = w, heightCm = h, scaleKg = kg, mode = Mode.AR_FULL,
            status = status, confidence = if (status == Status.OK) 92 else 61, seconds = 8.0, photo = thumb,
            lat = -6.30421, lon = 107.15232, gpsM = 6f)

    private fun hubRecord(resi: String) =
        Measurement(resi = resi, session = "s1", lengthCm = 0.0, widthCm = 0.0, heightCm = 0.0, mode = Mode.AR_FULL,
            status = Status.HUB, confidence = 0, seconds = 0.0, photo = thumb, note = "Bentuk tidak beraturan",
            lat = -6.30421, lon = 107.15232, gpsM = 6f)

    private fun shot(name: String, content: @Composable () -> Unit) =
        captureRoboImage("screenshots/$name.png") { CompositionLocalProvider(LocalStill provides true) { UkurTheme { content() } } }

    private fun screen(name: String, m: AppModel, s: Screen) {
        m.stack.clear(); m.stack.add(s)
        shot(name) { App(m, LocalContext.current as Activity) }
    }

    @Test fun nonCameraScreens() {
        var m = model()
        screen("01_cek_hp", m, Screen.Start)

        m = model()
        screen("02_scan_resi", m, Screen.Home)                  // first open: nothing measured yet

        m.draft = Draft("TSA-90100000104")
        screen("03_persiapan", m, Screen.Prep)

        m.draft = Draft("TSA-90100000104", ResultData(27.0, 15.0, 6.0, 92, Status.OK, 8.0, thumb, null, Mode.AR_FULL))
        screen("08_berat", m, Screen.Weight)

        // the parcels measured so far today, a minute apart
        val t0 = System.currentTimeMillis() - 30 * 60_000L
        m.store.save(measured("TSA-90100000101", 30.0, 20.0, 12.0, 1.2).copy(createdAt = t0))
        m.store.save(measured("TSA-90100000102", 41.5, 33.0, 24.5, 3.4, Status.CHECK).copy(createdAt = t0 + 6 * 60_000L))
        val saved = measured("TSA-90100000104", 27.0, 15.0, 6.0, 0.10).copy(createdAt = t0 + 12 * 60_000L)
        m.store.save(saved)
        screen("09_tersimpan", m, Screen.Saved(saved.id))
        val hub = hubRecord("TSA-90100000103").copy(createdAt = t0 + 9 * 60_000L)
        m.store.save(hub)
        screen("16_hari_ini", m, Screen.Home)
        screen("10_riwayat", m, Screen.History)
        screen("11_pengaturan", m, Screen.Settings)
        screen("15_detail_ukur_di_hub", m, Screen.Detail(hub.id))

        m = model(Mode.NONE)
        screen("12_cek_hp_tanpa_arcore", m, Screen.Start)
        m.draft = Draft("TSA-90100000104")
        screen("13_hp_tanpa_arcore_ukur", m, Screen.NoAr)

        // Urovo PDA (built-in scan key), here the DT20 without ARCore
        m = model(Mode.NONE)
        m.hardwareScanner = true
        screen("17_scan_resi_urovo", m, Screen.Home)
    }

    /** The recorder on the Urovo DT50's screen (720 x 1440 px): the start button must stay on screen. */
    @Test @Config(sdk = [35], qualifiers = "w360dp-h720dp-xhdpi") fun recorderOnSmallScreen() {
        val photo = BitmapFactory.decodeFile(resource("paket.jpg"))
        shot("21_perekam_layar_dt50") { Box(Modifier.fillMaxSize().background(C.bg)) { DtRecordPreview(photo, recording = false, gyroSilent = true) } }
        // the live outline as the tracker would follow the parcel (the mockup photo's parcel outline, in fractions)
        val outline = floatArrayOf(0.21f, 0.24f, 0.83f, 0.23f, 0.87f, 0.40f, 0.86f, 0.80f, 0.73f, 0.92f, 0.19f, 0.93f, 0.17f, 0.50f)
        shot("23_perekam_objek_disentuh") { Box(Modifier.fillMaxSize().background(C.bg)) {
            DtRecordPreview(photo, recording = true, gyroSilent = true, tap = androidx.compose.ui.geometry.Offset(0.5f, 0.55f), outline = outline) } }
        val m = model(Mode.NONE)
        // every gyroscope tried (example names): accepted by Android, but none sends events, as on the DT50
        m.diag = Dt20Test.diagnosis().copy(sam512EncodeMs = 1800, sam512Kernels = "CPU (CPU 1800 ms · XNNPACK 2100 ms)", gyroProbes = listOf(
            id.ukurpaket.app.dt.GyroProbe("gyroscope", "gyroscope (contoh)", "vendor", false, true, 0.0, 0.0, 0.0),
            id.ukurpaket.app.dt.GyroProbe("gyroscope", "gyroscope (contoh)", "vendor", true, true, 0.0, 0.0, 0.0),
            id.ukurpaket.app.dt.GyroProbe("gyroscope_uncalibrated", "gyroscope uncalibrated (contoh)", "vendor", false, true, 0.0, 0.0, 0.0)))
        m.diagRates = mapOf("accelerometer" to 200.0, "gyroscope" to 0.0, "game_rotation_vector" to 200.0)
        screen("22_diagnostik_gyro_diam_dt50", m, Screen.Diag)
        // the screens whose bottom buttons were cut off on this screen size
        screen("24_awal_layar_dt50", m, Screen.Start)
        m.draft = Draft("TSA-90100000104")
        screen("25_tanpa_arcore_layar_dt50", m, Screen.NoAr)
        val saved = measured("TSA-90100000104", 27.0, 15.0, 6.0, 0.10)
        m.store.save(saved)
        screen("26_tersimpan_layar_dt50", m, Screen.Saved(saved.id))
    }

    /**
     * The photo mode (0.4.0) on the DT50's screen: the camera with its angle and stillness chips, a photo waiting for the
     * tap, and the result of the real engine on a synthetic photo (true mask, the floor at the true camera height, a
     * calibrated phone): as a parcel, as a test with the tape size, and as a calibration photo; then the settings card.
     */
    @Test @Config(sdk = [35], qualifiers = "w360dp-h720dp-xhdpi") fun photoModeOnSmallScreen() {
        val dir = File("src/test/resources/photo/box_3")
        val pic = BitmapFactory.decodeFile(File(dir, "photo_00.jpg").path)
        val t = Json.parseToJsonElement(File(dir, "truth.json").readText()).jsonObject
        val p0 = t["photos"]!!.jsonArray[0].jsonObject
        val upL = p0["up"]!!.jsonArray.map { it.jsonPrimitive.float }; val up = V3(upL[0], upL[1], upL[2])
        val camH = p0["camera_height_m"]!!.jsonPrimitive.float
        val k = id.ukurpaket.app.photo.Intrinsics(420f, 420f, 240f, 320f, 480, 640)
        val mb = BitmapFactory.decodeFile(File(dir, "mask_00.png").path)
        val mpx = IntArray(480 * 640).also { mb.getPixels(it, 0, 480, 0, 0, 480, 640) }
        val mask = id.ukurpaket.app.measure.Mask(480, 640, BooleanArray(mpx.size) { (mpx[it] and 255) > 127 })
        val depth = id.ukurpaket.app.photo.DepthMap(480, 640, FloatArray(480 * 640) { i ->
            val den = -(k.ray(i % 480 + 0.5f, i / 480 + 0.5f) dot up); if (den > 1e-3f) camH / den else 40f })
        val r = id.ukurpaket.app.photo.PhotoMeasure.measure(mask, k, up, depth, 1f, calibrated = true)
        println("photo mode screenshot: ${r.lengthCm} x ${r.widthCm} x ${r.heightCm}, ok ${r.ok}, ${r.notes}")
        val tint = ObjectPick.tint(mask)
        val outline = mask.outline().flatMap { listOf(it.a / 480f, it.b / 640f) }
        val live = id.ukurpaket.app.photo.PhotoCamera.Live(46f, true, 120.0, "1280×960")
        shot("40_foto_kamera_dt50") { Box(Modifier.fillMaxSize().background(C.bg)) {
            id.ukurpaket.app.ui.PhotoCameraChrome("Ukur dengan foto", "Resi TSA-90100000104 · foto dari pojok paket", live, false, null, emptyList(), {}, {}, {}) {
                Image(pic.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop) } } }
        shot("41_foto_kamera_miring_dt50") { Box(Modifier.fillMaxSize().background(C.bg)) {
            id.ukurpaket.app.ui.PhotoCameraChrome("Ukur dengan foto", "Resi TSA-90100000104 · 1 foto", live.copy(downDeg = 14f, still = false), true, null,
                listOf(id.ukurpaket.app.ui.previewShot(pic, r, tint = tint, outline = outline)), {}, {}, {}) {
                Image(pic.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop) } } }
        fun view(name: String, purpose: id.ukurpaket.app.ui.PhotoPurpose, shotUi: id.ukurpaket.app.ui.PhotoShotUi, combined: id.ukurpaket.app.photo.PhotoResult?,
                 tape: List<String> = listOf("", "", ""), calibrated: Boolean = true) =
            shot(name) { Box(Modifier.fillMaxSize().background(C.bg)) {
                id.ukurpaket.app.ui.PhotoShotView(purpose, shotUi, listOf(shotUi), combined, "Resi TSA-90100000104 · 1 foto", 6000, calibrated,
                    if (calibrated) 0.87 else null, if (calibrated) 3 else 0, tape, isParcel = purpose == id.ukurpaket.app.ui.PhotoPurpose.PARCEL,
                    {}, { _, _ -> }, {}, {}, {}, {}, {}, {}, {}) } }
        view("42_foto_pilih_paket_dt50", id.ukurpaket.app.ui.PhotoPurpose.PARCEL, id.ukurpaket.app.ui.previewShot(pic, stage = "Membaca foto…"), null)
        view("43_foto_hasil_dt50", id.ukurpaket.app.ui.PhotoPurpose.PARCEL, id.ukurpaket.app.ui.previewShot(pic, r, tint = tint, outline = outline), r)
        val raw = r.copy(lengthCm = r.rawCm[0], widthCm = r.rawCm[1], heightCm = r.rawCm[2], ok = false, notes = listOf("Mode foto belum dikalibrasi di HP ini: angka bisa meleset jauh"))
        view("44_foto_uji_meteran_dt50", id.ukurpaket.app.ui.PhotoPurpose.TEST, id.ukurpaket.app.ui.previewShot(pic, raw, tint = tint, outline = outline), raw,
            listOf("40", "30", "20"), calibrated = false)
        view("45_foto_kalibrasi_dt50", id.ukurpaket.app.ui.PhotoPurpose.CALIBRATE, id.ukurpaket.app.ui.previewShot(pic, raw, tint = tint, outline = outline), raw,
            listOf("40", "30", ""), calibrated = false)
        val m = model(Mode.NONE)
        m.store.update { it.copy(photoCal = listOf(id.ukurpaket.app.photo.CalSample(listOf(46.0, 34.5, 23.0), listOf(40.0, 30.0, 20.0)),
            id.ukurpaket.app.photo.CalSample(listOf(36.0, 28.0, 17.0), listOf(31.0, 24.5, 15.0)))) }
        screen("46_pengaturan_kalibrasi_foto_dt50", m, Screen.Settings)
        m.draft = Draft("TSA-90100000104", ResultData(r.lengthCm, r.widthCm, r.heightCm, r.confidence, Status.OK, 0.0, null, null, Mode.PHOTO))
        screen("47_berat_dari_foto_dt50", m, Screen.Weight)
    }

    /** The sweep measured on the phone path (Android decoding, the Kotlin engine), the result screen, then weight and save. */
    @Test @Config(sdk = [35], qualifiers = "w360dp-h720dp-xhdpi") fun sweepMeasuredOnThePhone() {
        val m = model(Mode.NONE)
        val src = File("src/test/resources/sweep/box_dt50")
        val dir = File(m.store.dtDir, "20261104_120000").apply { deleteRecursively() }
        src.copyRecursively(dir)
        val r = id.ukurpaket.app.dt.SweepRun.run(dir) { _, _ -> }
        println("phone path: ${r.lengthCm} x ${r.widthCm} x ${r.heightCm}, conf ${r.confidence}")
        org.junit.Assert.assertEquals(40.0, r.lengthCm, 3.0); org.junit.Assert.assertEquals(30.0, r.widthCm, 3.0); org.junit.Assert.assertEquals(20.0, r.heightCm, 3.0)
        org.junit.Assert.assertTrue(id.ukurpaket.app.dt.SweepRun.evidenceFile(dir).exists())
        // every frame has its own segmentation: a contact sheet of six of them, outline and box as the review draws them
        val frames = ObjectPick.frames(dir)
        val sheet = Bitmap.createBitmap(3 * 240, 2 * 320, Bitmap.Config.ARGB_8888); val cv = android.graphics.Canvas(sheet)
        val fill = android.graphics.Paint().apply { color = 0x66ED0677; style = android.graphics.Paint.Style.FILL; isAntiAlias = true }
        val line = android.graphics.Paint().apply { color = android.graphics.Color.rgb(60, 220, 60); strokeWidth = 2.5f; isAntiAlias = true }
        for ((j, pos) in listOf(0, 15, 30, 45, 60, frames.size - 1).withIndex()) {
            val pic = Bitmap.createScaledBitmap(ObjectPick.upright(dir, frames[pos], 90)!!, 240, 320, true).copy(Bitmap.Config.ARGB_8888, true)
            val c = android.graphics.Canvas(pic)
            val o = r.outlines[pos]
            if (o.size >= 6) { val p = android.graphics.Path(); p.moveTo(o[0] * 240, o[1] * 320); for (i in 2 until o.size step 2) p.lineTo(o[i] * 240, o[i + 1] * 320); p.close(); c.drawPath(p, fill) }
            val b = r.boxes[pos]
            if (b.size == 16) for ((a, e) in listOf(0 to 1, 1 to 2, 2 to 3, 3 to 0, 4 to 5, 5 to 6, 6 to 7, 7 to 4, 0 to 4, 1 to 5, 2 to 6, 3 to 7))
                c.drawLine(b[2 * a] * 240, b[2 * a + 1] * 320, b[2 * e] * 240, b[2 * e + 1] * 320, line)
            cv.drawBitmap(pic, (j % 3) * 240f, (j / 3) * 320f, null)
        }
        File("screenshots").mkdirs()
        File("screenshots/31_segmentasi_tiap_frame.png").outputStream().use { sheet.compress(Bitmap.CompressFormat.PNG, 100, it) }
        m.stack.clear(); m.stack.add(Screen.Home)
        m.draft = Draft("TSA-90100000104")
        m.go(Screen.NoAr)
        screen("28_tanpa_arcore_ukur_sapuan", m, Screen.NoAr)
        m.stack.clear(); m.stack.addAll(listOf(Screen.Home, Screen.NoAr, Screen.DtReview(dir.path)))
        LocalStillValue.set(true)
        try { shot("29_hasil_ukur_sapuan") { App(m, LocalContext.current as Activity) } } finally { LocalStillValue.set(false) }
        // on to the weight, and saved as a sweep measurement with its evidence photo
        m.useSweep(dir, r)
        org.junit.Assert.assertEquals(Screen.Weight, m.screen)
        org.junit.Assert.assertEquals(listOf(Screen.Home, Screen.Weight), m.stack.toList())
        m.save(1.1)
        val saved = m.store.measurements.value.last()
        org.junit.Assert.assertEquals(Mode.SWEEP, saved.mode)
        org.junit.Assert.assertEquals(r.lengthCm, saved.lengthCm, 1e-9)
        org.junit.Assert.assertTrue(File(saved.photo!!).exists())
        screen("30_tersimpan_sapuan", m, Screen.Saved(saved.id))
    }

    /** Touching the object on the recorder's live picture: the first frame of the sweep is cut out once it stops. */
    @Test @Config(sdk = [35], qualifiers = "w360dp-h720dp-xhdpi") fun livePickIsCutAfterRecording() {
        val m = model(Mode.NONE)
        val photo = BitmapFactory.decodeFile(resource("paket.jpg"))
        val dir = File(m.store.dtDir, "20261104_111111").apply { deleteRecursively(); mkdirs() }
        File(dir, "frames").mkdirs()
        val sideways = Bitmap.createBitmap(photo, 0, 0, photo.width, photo.height, Matrix().apply { postRotate(-90f) }, true)
        File(dir, "frames/00000.jpg").outputStream().use { sideways.compress(Bitmap.CompressFormat.JPEG, 90, it) }
        // a box dragged round the parcel on the live picture, as fractions of it
        m.cutPick(dir, 90, null, null, floatArrayOf(185f / 899, 345f / 1599, 815f / 899, 1560f / 1599))
        val t0 = System.currentTimeMillis()
        while (m.pickJobs[dir.path] == "cutting" && System.currentTimeMillis() - t0 < 120_000) {
            org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle(); Thread.sleep(50)
        }
        org.junit.Assert.assertEquals("done", m.pickJobs[dir.path])
        val p = ObjectPick.load(dir)!!
        org.junit.Assert.assertEquals(0, p.frame)
        org.junit.Assert.assertEquals("box", p.mode)
        val frac = p.maskAreaPx.toDouble() / (p.width * p.height)
        org.junit.Assert.assertTrue("mask covers $frac of the picture", frac in 0.3..0.6)     // the parcel fills about 45 % of the frame
        LocalStillValue.set(true)
        try { screen("27_rekaman_objek_dari_perekam", m, Screen.DtReview(dir.path)) } finally { LocalStillValue.set(false) }
    }

    /** The DT20 test screens. Device values are test data (TestMaker Test Phone), not a real DT20 reading. */
    @Test fun dt20Screens() {
        val m = model(Mode.NONE)
        m.hardwareScanner = true
        m.diag = Dt20Test.diagnosis().let { d -> d.copy(samEncodeMs = 21_400, sensors = d.sensors.map { it.copy(measuredHz = 198.0) }) }
        m.diagRates = mapOf("accelerometer" to 198.0, "gyroscope" to 198.0)
        screen("18_diagnostik_hp", m, Screen.Diag)

        val photo = BitmapFactory.decodeFile(resource("paket.jpg"))
        shot("19_perekam_dt20") { Box(Modifier.fillMaxSize().background(C.bg)) { DtRecordPreview(photo, recording = true) } }

        // a recording as the recorder leaves it: frames stored sideways (sensor orientation 90), CSV tables, session.json
        val dir = File(m.store.dtDir, "20261104_101010").apply { deleteRecursively(); mkdirs() }
        File(dir, "frames").mkdirs()
        val sideways = Bitmap.createBitmap(photo, 0, 0, photo.width, photo.height, Matrix().apply { postRotate(-90f) }, true)
        for (i in 0 until 5) File(dir, "frames/%05d.jpg".format(i)).outputStream().use { sideways.compress(Bitmap.CompressFormat.JPEG, 90, it) }
        val (f, imu) = Dt20Test.sweep()
        File(dir, "frames.csv").writeText("index,t_ns,sharpness,width,height,bytes\n" + f.joinToString("") { "${it.index},${it.t},${it.sharpness},1599,899,1000\n" })
        File(dir, "imu.csv").writeText("sensor,t_ns,v0,v1,v2\n" + imu.joinToString("") { "${it.sensor},${it.t},${it.x},${it.y},${it.z}\n" })
        File(dir, "session.json").writeText("{\n  \"sensor_orientation\": 90,\n  \"timestamp_source\": \"REALTIME\"\n}\n")
        // the object picked with a box, cut out by the app's own MobileSAM
        val up = ObjectPick.upright(dir, 2, 90)!!
        val mask = Segmenter(File("src/main/assets/sam/encoder.onnx").readBytes(), File("src/main/assets/sam/decoder.onnx").readBytes()).use { sam ->
            sam.box(sam.embed(ObjectPick.argb(up), up.width, up.height), 185f, 345f, 815f, 1560f).largestPart()
        }
        ObjectPick.save(dir, Pick(2, "frames/00002.jpg", 90, up.width, up.height, "box", box = listOf(185f, 345f, 815f, 1560f),
            maskScore = mask.score, maskAreaPx = mask.area, maskBox = mask.bounds()?.toList(), samEncodeMs = 21_400, samDecodeMs = 45,
            name = "paket plastik", tapeCm = listOf(null, null, null)), up, mask)
        LocalStillValue.set(true)
        try { screen("20_rekaman_dt20_pilih_objek", m, Screen.DtReview(dir.path)) } finally { LocalStillValue.set(false) }
    }

    @Test fun cameraScreens() {
        val outline = pts("outline"); val grid = pts("grid"); val top = pts("top"); val base = pts("base")
        val cx = outline.map { it.first }.average().toFloat(); val cy = outline.map { it.second }.average().toFloat()
        val dots = pts("dots").sortedBy { hypot(it.first - cx, it.second - cy) }
        val oy = 50f          // the photo a little lower, so the cartons behind the bag clear the top bar
        val otherRects = geom["others"]!!.jsonArray.map { r -> r.jsonArray.map { it.jsonPrimitive.float } }
            .map { (x0, y0, x1, y1) -> listOf(x0 to y0 - oy / k, x1 - 4 to y0 - oy / k, x1 - 4 to y1, x0 to y1) }
        val othersAt = otherRects.map { px(it, oy) }
        val box = BoxResult(0.27f, 0.15f, 0.06f,
            floorCorners = base.map { V3(it.first / 1000f, 0f, it.second / 1000f) },
            topCorners = top.map { V3(it.first / 1000f, 0.06f, it.second / 1000f) },
            outline = emptyList(), points = 2400, fillRatio = 0.8f, topNoiseM = 0.004f)
        val ok = ResultData(27.0, 15.0, 6.0, 92, Status.OK, 8.0, null, null, Mode.AR_FULL)
        val xs = outline.map { it.first }; val ys = outline.map { it.second }

        cam("04_scan_lantai", 0f, EngineUi(Phase.SEARCH, planeFound = true, hint = Hint.NONE, overlay = Overlay(floorDots = px(grid, 0f))))
        cam("05_pilih_paket", oy, EngineUi(Phase.SELECT, planeFound = true, targetFound = true, hint = Hint.NONE, live = box, picked = true,
            overlay = Overlay(floorDots = px(grid, oy), outline = px(outline, oy), others = othersAt)))
        cam("05b_pilih_area", oy, EngineUi(Phase.SELECT, planeFound = true, targetFound = false, hint = Hint.NONE,
            overlay = Overlay(floorDots = px(grid, oy), others = othersAt)),
            demoBox = px(listOf(xs.min() - 12 to ys.min() - 12, xs.max() + 12 to ys.max() + 12), oy))
        cam("06_scan_paket", -59f, EngineUi(Phase.SCAN, planeFound = true, targetFound = true, progress = 0.64f, hint = Hint.SWEEP,
            overlay = Overlay(depthDots = px(dots.take((dots.size * 0.64f).toInt()), -59f), outline = px(outline, -59f))))
        cam("06b_peringatan", 30f, EngineUi(Phase.SCAN, planeFound = true, targetFound = true, progress = 0.38f, hint = Hint.BACK,
            overlay = Overlay(depthDots = px(dots.take((dots.size * 0.38f).toInt()), 30f), outline = px(outline, 30f))))
        cam("07_hasil_ukur", -59f, EngineUi(Phase.RESULT, planeFound = true, targetFound = true, progress = 1f, hint = Hint.NONE, live = box,
            overlay = Overlay(box = px(base + top, -59f)), result = ok))
        val doubtful = EngineUi(Phase.RESULT, planeFound = true, targetFound = true, progress = 1f, hint = Hint.NONE, live = box,
            overlay = Overlay(box = px(base + top, -59f)), result = ok.copy(confidence = 61, status = Status.CHECK), attempts = 2)
        cam("07b_perlu_dicek", -59f, doubtful)
        cam("07c_ukur_di_hub", -59f, doubtful, showHub = true)
        // the third parcel of a session: the floor is kept, the two cartons already measured carry a check mark
        val marks = othersAt.map { o -> floatArrayOf((o[0] + o[2]) / 2, o[5] - 30f * d) }
        cam("14_paket_berikutnya", oy, EngineUi(Phase.SELECT, planeFound = true, targetFound = true, hint = Hint.NONE, live = box,
            overlay = Overlay(floorDots = px(grid, oy), outline = px(outline, oy), marks = marks[0] + marks[1],
                markLabels = listOf("…0101", "…0102")), reticle = 206f * d to (400f + oy) * d), resi = "TSA-90100000104")
    }

    private fun cam(name: String, oyDp: Float, ui: EngineUi, demoBox: FloatArray? = null, showHub: Boolean = false, resi: String = "TSA-90100000104") {
        val m = model()
        m.draft = Draft(resi)
        val photo = BitmapFactory.decodeStream(javaClass.getResourceAsStream("/paket.jpg")).asImageBitmap()
        shot(name) {
            val act = LocalContext.current as Activity
            val engine = remember { MeasureEngine(act, true, app.filesDir, null) }
            Box(Modifier.fillMaxSize().background(Color.Black)) {
                Image(photo, null, Modifier.fillMaxWidth().offset(y = oyDp.dp), contentScale = ContentScale.FillWidth, alignment = Alignment.TopCenter)
                ArChrome(ui, engine, m, null, demoBox, showHub)
            }
        }
    }
}
