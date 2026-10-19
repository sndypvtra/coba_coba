package id.ukurpaket.app

import android.app.Application
import id.ukurpaket.app.ar.ArState
import id.ukurpaket.app.ar.DeviceCaps
import id.ukurpaket.app.ar.ResultData
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.ui.AppModel
import id.ukurpaket.app.ui.Screen
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import java.io.File

/** The courier's flow through the screens, without the camera: what is saved, and where the app goes next. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class FlowTest {
    private val app: Application = RuntimeEnvironment.getApplication()

    @Before fun clean() { File(app.filesDir, "ukurpaket.json").delete() }

    private fun model(arcore: ArState = ArState.READY) = AppModel(app, checkDevice = false).apply {
        caps = DeviceCaps(arcore, depth = arcore == ArState.READY, model = "test")
        store.update { it.copy(prepShown = 99) }
        stack.clear(); stack.add(Screen.Home)
    }

    private val result = ResultData(27.0, 15.0, 6.0, 92, Status.OK, 8.0, null, null, Mode.AR_FULL)

    @Test fun firstOpenHasNothingButTheScanner() {
        val m = model()
        assertTrue(m.store.measurements.value.isEmpty())
        assertNull(m.session)
    }

    @Test fun measureWeighSaveThenNextParcel() {
        val m = model()
        m.openResi("TSA-90100000104")
        assertEquals(Screen.Measure, m.screen)
        val session = m.session!!
        m.onMeasured(result)
        assertEquals(Screen.Weight, m.screen)
        m.onMeasured(result)                                    // a second tap on "Simpan" does nothing
        assertEquals(listOf(Screen.Home, Screen.Weight), m.stack.toList())
        m.save(1.2)
        val saved = m.store.measurements.value.single()
        assertEquals(Screen.Saved(saved.id), m.screen)
        assertEquals(listOf(Screen.Home, Screen.Saved(saved.id)), m.stack.toList())
        assertEquals(1.2, saved.scaleKg!!, 1e-9)
        assertEquals(session, saved.session)
        assertNull(m.draft)
        // "Paket berikutnya": the next scanned label opens on top of home, in the same session
        m.openResi("TSA-90100000105")
        assertEquals(listOf(Screen.Home, Screen.Measure), m.stack.toList())
        m.onMeasured(result); m.save(null)
        val all = m.store.measurements.value
        assertEquals(listOf(session, session), all.map { it.session })
        assertEquals(2, m.sessionCount(all.last(), all))
        // "Selesai": the next parcel starts a new session
        m.home()
        assertNull(m.session)
        m.openResi("TSA-90100000106")
        assertTrue(m.session != session)
    }

    @Test fun remeasureReplacesTheOldRecord() {
        val m = model()
        m.startMeasure("TSA-90100000104"); m.onMeasured(result); m.save(null)
        val first = m.store.measurements.value.single()
        m.startMeasure("TSA-90100000104", replaces = first.id)
        m.onMeasured(result.copy(lengthCm = 30.0)); m.save(null)
        val all = m.store.measurements.value
        assertEquals(1, all.size)
        assertEquals(30.0, all.single().lengthCm, 1e-9)
    }

    @Test fun hubFlagFromThePhoneWithoutArcore() {
        val m = model(ArState.UNSUPPORTED)
        m.openResi("TSA-90100000104")
        assertEquals(Screen.NoAr, m.screen)
        m.markHub("HP kurir tanpa ARCore", null)
        val r = m.store.measurements.value.single()
        assertEquals(Status.HUB, r.status)
        assertTrue(r.atHub)
        assertEquals(listOf(Screen.Home, Screen.Saved(r.id)), m.stack.toList())
    }

    @Test fun scannedResiOpensItsParcel() {
        val m = model()
        m.openResi(" TSA-90100000104 ")                         // the scanned text is used as it is, minus outer spaces
        assertEquals(Screen.Measure, m.screen)
        assertEquals("TSA-90100000104", m.draft!!.resi)
        // no format rules: whatever the barcode holds becomes the parcel's number
        m.back(); m.openResi("AJ-0001/xyz")
        assertEquals("AJ-0001/xyz", m.draft!!.resi)
        // a number measured already opens its record instead of measuring it twice
        m.onMeasured(result); m.save(null)
        m.openResi("AJ-0001/xyz")
        assertEquals(Screen.Detail(m.store.measurements.value.single().id), m.screen)
        m.openResi("   ")                                       // nothing scanned: nothing happens
        assertEquals(Screen.Detail(m.store.measurements.value.single().id), m.screen)
    }

    @Test fun lateHubPhotoAfterLeavingDoesNothing() {
        val m = model()
        m.openResi("TSA-90100000104")
        m.back()                                                // the courier left before the photo arrived
        m.markHub("Paket terlalu besar", "/x.jpg")
        assertTrue(m.store.measurements.value.isEmpty())
        assertEquals(listOf(Screen.Home), m.stack.toList())
    }

    @Test fun oldDataFileWithExamplePickupsStillLoads() {
        File(app.filesDir, "ukurpaket.json").writeText("""{"orders":[{"id":"o1","name":"Toko","address":"Jl.","note":"","resi":["X"]}],
            "measurements":[{"id":"a","resi":"X","orderId":"o1","lengthCm":1.0,"widthCm":2.0,"heightCm":3.0,"mode":"AR_FULL",
            "status":"OK","confidence":90,"seconds":5.0}],"settings":{"divisor":5000}}""")
        val m = AppModel(app, checkDevice = false)
        assertEquals("X", m.store.measurements.value.single().resi)
        assertEquals(5000, m.store.settings.value.divisor)
    }
}
