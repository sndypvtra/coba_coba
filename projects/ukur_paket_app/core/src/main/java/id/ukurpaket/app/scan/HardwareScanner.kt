package id.ukurpaket.app.scan

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.view.KeyEvent
import androidx.core.content.ContextCompat

/**
 * The built-in laser/imager scanner of a rugged PDA (Urovo DT20 and the other Urovo models), next to Google's
 * camera scanner. The scan key reads the label and the result reaches the app in one of two ways, chosen on the
 * device in Settings → Scanner → Output mode:
 *
 *  - **Intent output** (recommended): the scanner service sends a broadcast. Urovo's default is
 *    `android.intent.ACTION_DECODE_DATA` with the text in `barcode_string` (and the raw bytes in `barcode` + `length`);
 *    older Urovo firmware sends `urovo.rcv.message` with the bytes in `barocode` (sic).
 *  - **Keyboard output**: the scanner types the code as fast key presses ending with Enter; [KeyWedge] reads them.
 *    This also works for Bluetooth / USB ring scanners on any phone.
 */
object HardwareScanner {
    val ACTIONS = listOf("android.intent.ACTION_DECODE_DATA", "urovo.rcv.message")

    /** Phones whose maker ships a built-in scanner key. Others can still use it (a broadcast or wedge scan switches it on). */
    fun builtIn(manufacturer: String?, brand: String?): Boolean =
        listOf(manufacturer, brand).any { it != null && it.trim().equals("urovo", ignoreCase = true) }

    /** The scanned text from one of the broadcasts above, or null when the intent holds none. */
    fun parse(intent: Intent): String? {
        if (intent.action !in ACTIONS) return null
        intent.getStringExtra("barcode_string")?.let { if (it.isNotBlank()) return it }
        for (key in listOf("barcode", "barocode")) {
            val bytes = intent.getByteArrayExtra(key) ?: continue
            val n = intent.getIntExtra("length", bytes.size).coerceIn(0, bytes.size)
            val s = String(bytes, 0, n, Charsets.UTF_8)
            if (s.isNotBlank()) return s
        }
        return null
    }

    /**
     * A label's QR code read by mistake (the hardware scanner reads 2D codes unless they are switched off in its
     * settings): links and multi-line text are not tracking numbers. Anything else is used as it is.
     */
    fun looksLikeQr(code: String): Boolean = "://" in code || code.trim().contains('\n')

    /** Listens while the app is in front (registered in onResume, removed in onPause). */
    class Receiver(private val onCode: (String) -> Unit) : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) { parse(intent)?.let(onCode) }

        fun register(context: Context) {
            val filter = IntentFilter().apply { ACTIONS.forEach { addAction(it) } }
            // the scanner service is another app: the receiver has to be exported
            ContextCompat.registerReceiver(context, this, filter, ContextCompat.RECEIVER_EXPORTED)
        }

        fun unregister(context: Context) { runCatching { context.unregisterReceiver(this) } }
    }
}

/**
 * Keyboard-output scanners type the code much faster than a person can (a few ms per key) and end it with Enter.
 * Keys closer together than [maxGapMs] are collected; Enter after at least [minLength] of them gives the code.
 * Only used on screens without a text field, so no typing is taken away from the courier.
 */
class KeyWedge(private val maxGapMs: Long = 120, private val minLength: Int = 3, private val onCode: (String) -> Unit) {
    private val buf = StringBuilder()
    private var last = 0L
    private val held = HashSet<Int>()

    /** @return true when the key belongs to a scan and must not reach the screen. */
    fun onKey(down: Boolean, keyCode: Int, char: Int, time: Long): Boolean {
        if (!down) return held.remove(keyCode)
        val end = keyCode == KeyEvent.KEYCODE_ENTER || keyCode == KeyEvent.KEYCODE_NUMPAD_ENTER || keyCode == KeyEvent.KEYCODE_TAB
        if (end) {
            if (buf.isEmpty()) return false
            val code = buf.toString()
            val fast = time - last <= maxGapMs
            buf.clear()
            held.add(keyCode)
            if (fast && code.length >= minLength) onCode(code)
            return true
        }
        if (char == 0 || Character.isISOControl(char)) return false
        if (buf.isNotEmpty() && time - last > maxGapMs) buf.clear()      // a slow key: a person, not the scanner
        buf.appendCodePoint(char)
        last = time
        held.add(keyCode)
        return true
    }
}
