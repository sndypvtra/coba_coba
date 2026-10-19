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

    @Test fun measureWeighSaveThenNextParcel() {
        val m = model()
        m.startMeasure("TSA-90100000107", "o1")
        assertEquals(Screen.Measure, m.screen)
        m.onMeasured(result)
        assertEquals(Screen.Weight, m.screen)
        m.onMeasured(result)                                    // a second tap on "Simpan" does nothing
        assertEquals(listOf(Screen.Home, Screen.Weight), m.stack.toList())
        m.save(1.2)
        val saved = m.store.measurements.value.single()
        assertEquals(Screen.Saved(saved.id), m.screen)
        assertEquals(listOf(Screen.Home, Screen.Saved(saved.id)), m.stack.toList())
        assertEquals(1.2, saved.scaleKg!!, 1e-9)
        assertNull(m.draft)
        assertEquals("TSA-90100000108", m.nextInOrder("o1"))
        m.nextParcel("TSA-90100000108", "o1")
        assertEquals(listOf(Screen.Home, Screen.Measure), m.stack.toList())
    }

    @Test fun remeasureReplacesTheOldRecord() {
        val m = model()
        m.startMeasure("TSA-90100000110", "o2"); m.onMeasured(result); m.save(null)
        val first = m.store.measurements.value.single()
        m.startMeasure("TSA-90100000110", "o2", replaces = first.id)
        m.onMeasured(result.copy(lengthCm = 30.0)); m.save(null)
        val all = m.store.measurements.value
        assertEquals(1, all.size)
        assertEquals(30.0, all.single().lengthCm, 1e-9)
    }

    @Test fun hubFlagFromThePhoneWithoutArcore() {
        val m = model(ArState.UNSUPPORTED)
        m.startMeasure("TSA-90100000111", "o3")
        assertEquals(Screen.NoAr, m.screen)
        m.markHub("HP kurir tanpa ARCore", null)
        val r = m.store.measurements.value.single()
        assertEquals(Status.HUB, r.status)
        assertTrue(r.atHub)
        assertEquals(listOf(Screen.Home, Screen.Saved(r.id)), m.stack.toList())
    }

    @Test fun scannedQrThatIsNotAResiIsRejected() {
        val m = model()
        m.openResi("OJKX1234567AB68")                           // e.g. the order code in one of the label's QR codes
        assertEquals("OJKX1234567AB68", m.scanRejected)
        assertEquals(listOf(Screen.Home), m.stack.toList())     // nothing opened, nothing recorded
        assertTrue(m.store.measurements.value.isEmpty())
        assertNull(m.draft)
    }

    @Test fun scannedResiOpensItsParcel() {
        val m = model()
        m.openResi(" tsa-90100000109 ")                         // spaces and case from the scanner are cleaned up
        assertNull(m.scanRejected)
        assertEquals(Screen.Measure, m.screen)
        assertEquals("TSA-90100000109", m.draft!!.resi)
        assertEquals("o1", m.draft!!.orderId)
        // a real label not in today's list is still taken, as a pickup of its own
        m.back(); m.openResi("TSA-80745081104")
        assertEquals("TSA-80745081104", m.draft!!.resi)
        assertTrue(m.store.orders.any { "TSA-80745081104" in it.resi })
    }

    @Test fun formatCheckCanBeSwitchedOff() {
        val m = model()
        m.store.update { it.copy(resiCheck = false) }
        m.openResi("AJ1234567890")
        assertNull(m.scanRejected)
        assertEquals(Screen.Measure, m.screen)
    }

    @Test fun lateHubPhotoAfterLeavingDoesNothing() {
        val m = model()
        m.startMeasure("TSA-90100000112", "o3")
        m.back()                                                // the courier left before the photo arrived
        m.markHub("Paket terlalu besar", "/x.jpg")
        assertTrue(m.store.measurements.value.isEmpty())
        assertEquals(listOf(Screen.Home), m.stack.toList())
    }
}
