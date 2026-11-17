package id.ukuraja.app

import android.app.Application
import android.graphics.Bitmap
import id.ukuraja.app.data.Settings
import id.ukuraja.app.data.Status
import id.ukuraja.app.ui.AppModel
import id.ukuraja.app.ui.PhotoShotUi
import id.ukuraja.app.ui.Screen
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import org.robolectric.shadows.ShadowLooper
import java.io.File

/** The courier's way through the screens, without the camera: what is saved, and where the app goes next. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class FlowTest {
    private val app: Application = RuntimeEnvironment.getApplication()

    @Before fun clean() { File(app.filesDir, "ukuraja.json").delete() }

    private fun model() = AppModel(app, preload = false)

    private fun result(marker: Boolean, ok: Boolean = true) = PhotoResult(40.1, 30.0, 20.0, listOf(52.0, 39.0, 26.0), 0.83, 1.30, 45.0, 0.97, true,
        List(16) { 0.5f }, if (ok) 100 else 60, ok, emptyList(), floorInliers = 5000, aiCameraM = 1.40,
        markerId = if (marker) 1 else -1, markerCameraM = if (marker) 1.30 else 0.0, markerSigma = if (marker) 0.013 else 0.0)

    private fun until(m: AppModel, s: Screen) {
        val t0 = System.currentTimeMillis()
        while (m.screen != s && System.currentTimeMillis() - t0 < 10_000) { ShadowLooper.idleMainLooper(); Thread.sleep(20) }
    }

    @Test fun scanMeasureWithTheMarkerWeighSave() {
        val m = model()
        m.openResi(" TSA-80745081104 ")
        assertEquals(Screen.Photo, m.screen)
        assertEquals("TSA-80745081104", m.draft!!.resi)
        val dir = m.photo.dir!!
        assertTrue(dir.isDirectory)
        // a measured photo, as PhotoFlow leaves it once the engine answered
        val pic = Bitmap.createBitmap(480, 640, Bitmap.Config.ARGB_8888)
        m.photo.shots.add(PhotoShotUi(0, pic, Intrinsics(420f, 420f, 240f, 320f, 480, 640), V3(0f, -0.7f, -0.7f), 45f, true, result = result(marker = true)))
        m.photo.current = 0
        m.photo.use()
        until(m, Screen.Weight)
        assertEquals(listOf(Screen.Home, Screen.Weight), m.stack.toList())
        val out = m.draft!!.result!!
        assertEquals(Status.OK, out.status)
        assertEquals("Marker A4", out.scaleSource)
        // a stray scan while weighing does not drop the parcel
        m.onHardwareScan("TSA-999")
        assertEquals(Screen.Weight, m.screen)
        m.save(2.35)
        val saved = m.store.measurements.value.single()
        assertEquals(Screen.Saved(saved.id), m.screen)
        assertEquals(2.35, saved.scaleKg!!, 1e-9)
        assertEquals("Marker A4", saved.scaleSource)
        assertEquals(40.1 * 30.0 * 20.0 / 6000, saved.volumetricKg, 1e-9)
        assertEquals(4.01, saved.chargedKg, 1e-9)                      // volumetric 4,01 kg beats the scale's 2,35
        assertNull(m.draft)
        // scanning it again opens its record, not a new measurement
        m.onHardwareScan("TSA-80745081104")
        assertEquals(Screen.Detail(saved.id), m.screen)
    }

    @Test fun aParcelThatCannotBeMeasuredGoesToTheHub() {
        val m = model()
        m.openResi("TSA-1")
        m.markHub("Bentuk tidak beraturan / lunak")
        val r = m.store.measurements.value.single()
        assertEquals(Status.HUB, r.status)
        assertEquals("Bentuk tidak beraturan / lunak", r.note)
        assertEquals(Screen.Saved(r.id), m.screen)
    }

    @Test fun measuringAgainReplacesTheRecord() {
        val m = model()
        m.openResi("TSA-2"); m.markHub("Lainnya")
        val first = m.store.measurements.value.single()
        m.startMeasure("TSA-2", replaces = first.id)
        m.photo.shots.add(PhotoShotUi(0, Bitmap.createBitmap(480, 640, Bitmap.Config.ARGB_8888), Intrinsics(420f, 420f, 240f, 320f, 480, 640),
            V3(0f, -0.7f, -0.7f), 45f, true, result = result(marker = false, ok = false)))
        m.photo.use(); until(m, Screen.Weight); m.save(null)
        val now = m.store.measurements.value.single()
        assertEquals(Status.CHECK, now.status)
        assertEquals("AI (tanpa marker)", now.scaleSource)
    }

    /** Marker photos teach the phone; the newest MAX_MARKER_SAMPLES are kept; photos without a marker teach nothing. */
    @Test fun markerPhotosTeachTheScale() {
        val m = model()
        m.startMeasure("TSA-3")
        m.photo.learn(0, result(marker = false))
        assertTrue(m.store.settings.value.photoCal.isEmpty())
        m.photo.learn(0, result(marker = true))
        m.photo.learn(0, result(marker = true))                                // the same photo once only
        assertEquals(1, m.store.settings.value.photoCal.size)
        val s = m.store.settings.value.photoCal.single()
        assertEquals("marker", s.source)
        // the depth model's own height was 1,40 / 0,83; the marker said 1,30
        assertEquals(1.30 / (1.40 / 0.83), Calibration.factor(listOf(s))!!, 1e-9)
        for (i in 1..30) m.photo.learn(i, result(marker = true))
        assertEquals(Settings.MAX_MARKER_SAMPLES, m.store.settings.value.photoCal.size)
        assertTrue(m.photo.calibrated)
        m.store.update { it.copy(learnFromMarker = false, photoCal = emptyList()) }
        m.photo.learn(99, result(marker = true))
        assertTrue(m.store.settings.value.photoCal.isEmpty())
    }

    @Test fun markerSidesFromSettings() {
        val s = Settings(markerA4Mm = 158.0)
        assertEquals(0.158, s.markerSideM(1)!!, 1e-12)
        assertEquals(0.24, s.markerSideM(2)!!, 1e-12)
        assertNull(s.markerSideM(7))
    }
}
