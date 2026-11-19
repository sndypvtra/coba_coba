package id.ukuraja.app.scan

import com.google.mlkit.vision.barcode.common.Barcode
import id.ukurpaket.app.scan.HardwareScanner
import kotlin.math.hypot

/**
 * One barcode found in a camera frame: its text, its ML Kit format and its box, all as fractions (0..1) of the upright
 * frame, which is also the preview on screen.
 */
data class Seen(val raw: String, val format: Int, val left: Float, val top: Float, val right: Float, val bottom: Float) {
    val cx get() = (left + right) / 2
    val cy get() = (top + bottom) / 2
}

/** The scan window, as fractions of the upright frame. */
data class Window(val left: Float, val top: Float, val right: Float, val bottom: Float) {
    val cx get() = (left + right) / 2
    val cy get() = (top + bottom) / 2
    operator fun contains(s: Seen) = s.cx in left..right && s.cy in top..bottom

    companion object {
        /** A wide band across the middle of the 3:4 preview: a label's barcode is wider than tall. */
        val DEFAULT = Window(0.08f, 0.35f, 0.92f, 0.65f)
    }
}

/** What one frame told the scanner. */
data class ScanStep(
    /** The label's number, once it is read for certain: the scan is done. */
    val resi: String?,
    /** The barcode the scanner is reading (inside the window, nearest its middle), to outline on the preview. */
    val target: Seen?,
    /** The other barcodes in view, outlined thinner. */
    val others: List<Seen>,
    val hint: Hint,
)

enum class Hint { AIM, MOVE_INTO_WINDOW, HOLD, DONE }

/**
 * Turns the barcodes found frame by frame into one tracking number, the way a courier expects a scanner to behave:
 * - only the barcode inside the window counts (a label carries several), the one nearest its middle;
 * - codes with a check character (Code 128, Code 93, EAN, UPC) are taken on the first read;
 * - codes without one (Code 39, Codabar, ITF), whose partial reads look valid, must read the same twice;
 * - QR content and text too short for a number are never taken.
 */
class ResiReader(private val window: Window = Window.DEFAULT, private val confirmMs: Long = 1500) {
    private var last: String? = null
    private var lastAt = 0L

    fun offer(seen: List<Seen>, nowMs: Long): ScanStep {
        val usable = seen.mapNotNull { s -> clean(s.raw)?.let { s.copy(raw = it) } }
        val target = usable.filter { it in window }.minByOrNull { hypot(it.cx - window.cx, (it.cy - window.cy) * 2) }
        val others = usable.filter { it !== target }
        if (target == null) {
            return ScanStep(null, null, others, if (others.isEmpty()) Hint.AIM else Hint.MOVE_INTO_WINDOW)
        }
        val sure = target.format in CHECKED || (target.raw == last && nowMs - lastAt <= confirmMs)
        last = target.raw; lastAt = nowMs
        return if (sure) ScanStep(target.raw, target, others, Hint.DONE) else ScanStep(null, target, others, Hint.HOLD)
    }

    fun reset() { last = null; lastAt = 0L }

    companion object {
        /** Linear formats only: the label's QR codes are never picked up. */
        val FORMATS = listOf(
            Barcode.FORMAT_CODE_128, Barcode.FORMAT_CODE_39, Barcode.FORMAT_CODE_93, Barcode.FORMAT_CODABAR,
            Barcode.FORMAT_EAN_13, Barcode.FORMAT_EAN_8, Barcode.FORMAT_ITF, Barcode.FORMAT_UPC_A, Barcode.FORMAT_UPC_E,
        )

        /** Formats whose check character makes a misread or a partial read fail to decode at all. */
        val CHECKED = setOf(Barcode.FORMAT_CODE_128, Barcode.FORMAT_CODE_93, Barcode.FORMAT_EAN_13, Barcode.FORMAT_EAN_8,
            Barcode.FORMAT_UPC_A, Barcode.FORMAT_UPC_E)

        /**
         * The text as a tracking number: control characters (Code 128's FNC1 arrives as a group separator) and spaces
         * at the ends removed; null for QR-like content or fewer than 4 characters.
         */
        fun clean(raw: String?): String? {
            if (raw == null || HardwareScanner.looksLikeQr(raw)) return null
            val s = raw.filter { it >= ' ' && it != '\u007F' }.trim()
            return s.takeIf { it.length >= 4 }
        }
    }
}
