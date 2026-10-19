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
            Mode.NONE -> DeviceCaps(ArState.UNSUPPORTED, false, "samsung SM-A055F")
        }
        m.samState = SamState.READY
        return m
    }

    private val thumb by lazy { resource("thumb.jpg") }

    private fun measured(resi: String, order: String, l: Double, w: Double, h: Double, kg: Double?, status: Status = Status.OK) =
        Measurement(resi = resi, orderId = order, lengthCm = l, widthCm = w, heightCm = h, scaleKg = kg, mode = Mode.AR_FULL,
            status = status, confidence = if (status == Status.OK) 92 else 61, seconds = 8.0, photo = thumb,
            lat = -6.30421, lon = 107.15232, gpsM = 6f)

    private fun hubRecord(resi: String, order: String) =
        Measurement(resi = resi, orderId = order, lengthCm = 0.0, widthCm = 0.0, heightCm = 0.0, mode = Mode.AR_FULL,
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
        m.store.save(measured("TSA-90100000110", "o2", 30.0, 20.0, 12.0, 1.2))
        screen("02_pickup", m, Screen.Home)
        m.scanRejected = "OJKX1234567AB68"                 // a QR from the label that is not the tracking number
        screen("02b_bukan_resi", m, Screen.Home)
        m.scanRejected = null

        m.draft = Draft("TSA-90100000107", "o1")
        screen("03_persiapan", m, Screen.Prep)

        m.draft = Draft("TSA-90100000107", "o1", ResultData(27.0, 15.0, 6.0, 92, Status.OK, 8.0, thumb, null, Mode.AR_FULL))
        screen("08_berat", m, Screen.Weight)

        val saved = measured("TSA-90100000107", "o1", 27.0, 15.0, 6.0, 0.10)
        m.store.save(saved)
        screen("09_tersimpan", m, Screen.Saved(saved.id))
        m.store.save(measured("TSA-90100000111", "o3", 41.5, 33.0, 24.5, 3.4, Status.CHECK))
        val hub = hubRecord("TSA-90100000112", "o3")
        m.store.save(hub)
        screen("10_riwayat", m, Screen.History)
        screen("11_pengaturan", m, Screen.Settings)
        screen("15_detail_ukur_di_hub", m, Screen.Detail(hub.id))

        m = model(Mode.NONE)
        screen("12_cek_hp_tanpa_arcore", m, Screen.Start)
        m.draft = Draft("TSA-90100000108", "o1")
        screen("13_hp_tanpa_arcore_ukur", m, Screen.NoAr)
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
        // the third parcel of a pickup: the floor is kept, the two cartons already measured carry a check mark
        val marks = othersAt.map { o -> floatArrayOf((o[0] + o[2]) / 2, o[5] - 30f * d) }
        cam("14_paket_berikutnya", oy, EngineUi(Phase.SELECT, planeFound = true, targetFound = true, hint = Hint.NONE, live = box,
            overlay = Overlay(floorDots = px(grid, oy), outline = px(outline, oy), marks = marks[0] + marks[1],
                markLabels = listOf("…0007", "…0008")), reticle = 206f * d to (400f + oy) * d), resi = "TSA-90100000109")
    }

    private fun cam(name: String, oyDp: Float, ui: EngineUi, demoBox: FloatArray? = null, showHub: Boolean = false, resi: String = "TSA-90100000107") {
        val m = model()
        m.draft = Draft(resi, "o1")
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
