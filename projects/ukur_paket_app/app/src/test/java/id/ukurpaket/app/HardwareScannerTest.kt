package id.ukurpaket.app

import android.app.Application
import android.content.Intent
import android.view.KeyEvent
import id.ukurpaket.app.ar.ArState
import id.ukurpaket.app.ar.DeviceCaps
import id.ukurpaket.app.scan.HardwareScanner
import id.ukurpaket.app.scan.KeyWedge
import id.ukurpaket.app.ui.AppModel
import id.ukurpaket.app.ui.Screen
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import android.os.Looper
import java.io.File

/** The Urovo scan key: broadcast (Intent output) and keyboard output, and where a scan may open a parcel. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class HardwareScannerTest {
    private val app: Application = RuntimeEnvironment.getApplication()

    @Before fun clean() { File(app.filesDir, "ukurpaket.json").delete() }

    private fun model() = AppModel(app, checkDevice = false).apply {
        caps = DeviceCaps(ArState.READY, depth = true, model = "test")
        store.update { it.copy(prepShown = 99) }
        stack.clear(); stack.add(Screen.Home)
    }

    @Test fun urovoIsRecognised() {
        assertTrue(HardwareScanner.builtIn("UROVO", "UROVO"))
        assertTrue(HardwareScanner.builtIn("Urovo", null))
        assertFalse(HardwareScanner.builtIn("samsung", "samsung"))
    }

    @Test fun urovoBroadcastFormats() {
        val a = Intent("android.intent.ACTION_DECODE_DATA").putExtra("barcode_string", "TSA-80745081104")
        assertEquals("TSA-80745081104", HardwareScanner.parse(a))
        // only the bytes, with a length shorter than the buffer
        val bytes = "TSA-1234567890xxxx".toByteArray()
        val b = Intent("android.intent.ACTION_DECODE_DATA").putExtra("barcode", bytes).putExtra("length", 14)
        assertEquals("TSA-1234567890", HardwareScanner.parse(b))
        // older firmware
        val c = Intent("urovo.rcv.message").putExtra("barocode", "AJ-77".toByteArray()).putExtra("length", 5)
        assertEquals("AJ-77", HardwareScanner.parse(c))
        assertNull(HardwareScanner.parse(Intent("some.other.ACTION").putExtra("barcode_string", "X")))
        assertNull(HardwareScanner.parse(Intent("android.intent.ACTION_DECODE_DATA")))
    }

    @Test fun broadcastReachesTheReceiver() {
        val seen = mutableListOf<String>()
        val r = HardwareScanner.Receiver { seen += it }
        r.register(app)
        app.sendBroadcast(Intent("android.intent.ACTION_DECODE_DATA").putExtra("barcode_string", "TSA-1"))
        shadowOf(Looper.getMainLooper()).idle()
        assertEquals(listOf("TSA-1"), seen)
        r.unregister(app)
    }

    @Test fun scanKeyOpensTheParcelOnlyWhereSafe() {
        val m = model()
        assertTrue(m.takesHardwareScan)
        m.onHardwareScan("TSA-90100000104\n")
        assertTrue(m.hardwareScanner)
        assertEquals(Screen.Measure, m.screen)
        assertEquals("TSA-90100000104", m.draft!!.resi)
        // a stray press while measuring keeps the parcel being measured
        m.onHardwareScan("TSA-90100000105")
        assertEquals(Screen.Measure, m.screen)
        assertEquals("TSA-90100000104", m.draft!!.resi)
        assertEquals("Selesaikan paket TSA-90100000104 dulu, lalu scan berikutnya", m.message)
        // a QR code read by mistake is not a tracking number
        m.back()
        m.onHardwareScan("https://anteraja.id/track?x=1")
        assertEquals(Screen.Home, m.screen)
    }

    @Test fun keyboardOutputScan() {
        val got = mutableListOf<String>()
        val w = KeyWedge { got += it }
        var t = 1000L
        fun type(s: String, gap: Long) = s.forEach { ch ->
            assertTrue(w.onKey(true, KeyEvent.KEYCODE_A, ch.code, t)); assertTrue(w.onKey(false, KeyEvent.KEYCODE_A, 0, t)); t += gap
        }
        type("TSA-123", 5)
        assertTrue(w.onKey(true, KeyEvent.KEYCODE_ENTER, '\n'.code, t))
        assertTrue(w.onKey(false, KeyEvent.KEYCODE_ENTER, 0, t))
        assertEquals(listOf("TSA-123"), got)
        // a person pressing keys slowly is not a scan
        type("abc", 400)
        w.onKey(true, KeyEvent.KEYCODE_ENTER, '\n'.code, t + 400)
        assertEquals(1, got.size)
        // keys without a character (back, volume, the scan trigger itself) pass through
        assertFalse(w.onKey(true, KeyEvent.KEYCODE_BACK, 0, t))
        assertFalse(w.onKey(true, KeyEvent.KEYCODE_ENTER, '\n'.code, t + 1000))   // Enter alone
    }
}
