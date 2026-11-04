package id.ukurpaket.app.dt

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import id.ukurpaket.app.measure.Mask
import kotlinx.serialization.Serializable
import java.io.File

/**
 * The object picked in one frame of a sweep, any object (parcel, gallon, chair…): by a tap on it or a box dragged
 * around it, cut out by MobileSAM. Saved next to the recording so the PC solver knows what to measure, with the
 * tape-measure size when the tester typed one (the reference the engine is judged against).
 */
@Serializable
data class Pick(
    val frame: Int, val file: String, val rotationDeg: Int, val width: Int, val height: Int,
    val mode: String, val tap: List<Float>? = null, val box: List<Float>? = null,
    val maskFile: String = "mask.png", val maskScore: Float, val maskAreaPx: Int, val maskBox: List<Int>?,
    val samEncodeMs: Long?, val samDecodeMs: Long, val name: String, val tapeCm: List<Double?>,
    val note: String = "coordinates in the upright picture: the frame rotated clockwise by rotationDeg",
)

object ObjectPick {
    fun frameFile(dir: File, index: Int) = File(dir, "frames/%05d.jpg".format(index))

    /** The saved frame numbers, in order. */
    fun frames(dir: File): List<Int> =
        File(dir, "frames").listFiles { f -> f.name.endsWith(".jpg") }?.mapNotNull { it.nameWithoutExtension.toIntOrNull() }?.sorted().orEmpty()

    /** From session.json; how far the frames must turn to stand upright on the DT20 held in portrait. */
    fun rotation(dir: File): Int =
        Regex("\"sensor_orientation\":\\s*(\\d+)").find(File(dir, "session.json").takeIf { it.exists() }?.readText().orEmpty())
            ?.groupValues?.get(1)?.toInt() ?: 90

    fun sameClock(dir: File) = File(dir, "session.json").takeIf { it.exists() }?.readText()?.contains("\"REALTIME\"") == true

    fun upright(dir: File, index: Int, rotation: Int): Bitmap? {
        val b = BitmapFactory.decodeFile(frameFile(dir, index).path) ?: return null
        if (rotation % 360 == 0) return b
        return Bitmap.createBitmap(b, 0, 0, b.width, b.height, Matrix().apply { postRotate(rotation.toFloat()) }, true)
    }

    fun argb(b: Bitmap) = IntArray(b.width * b.height).also { b.getPixels(it, 0, b.width, 0, 0, b.width, b.height) }

    /** The mask as a see-through tint, for drawing over the picture. */
    fun tint(m: Mask, color: Int = 0x99ED0677.toInt()): Bitmap {
        val px = IntArray(m.w * m.h) { if (m.bits[it]) color else 0 }
        return Bitmap.createBitmap(px, m.w, m.h, Bitmap.Config.ARGB_8888)
    }

    fun save(dir: File, pick: Pick, picture: Bitmap, m: Mask) {
        val bw = IntArray(m.w * m.h) { if (m.bits[it]) -1 else 0xFF000000.toInt() }
        File(dir, pick.maskFile).outputStream().use { Bitmap.createBitmap(bw, m.w, m.h, Bitmap.Config.ARGB_8888).compress(Bitmap.CompressFormat.PNG, 100, it) }
        val over = picture.copy(Bitmap.Config.ARGB_8888, true)
        val px = argb(over)
        for (i in px.indices) if (m.bits[i]) {
            val c = px[i]
            val r = (((c shr 16) and 255) * 0.5 + 0xED * 0.5).toInt(); val g = (((c shr 8) and 255) * 0.5 + 0x06 * 0.5).toInt()
            val b = ((c and 255) * 0.5 + 0x77 * 0.5).toInt()
            px[i] = (0xFF shl 24) or (r shl 16) or (g shl 8) or b
        }
        over.setPixels(px, 0, over.width, 0, 0, over.width, over.height)
        File(dir, "pick_overlay.jpg").outputStream().use { over.compress(Bitmap.CompressFormat.JPEG, 88, it) }
        File(dir, "pick.json").writeText(Diagnostics.json.encodeToString(Pick.serializer(), pick) + "\n")
    }

    /** The pick made live while recording: the mask and pick.json only (the review draws the mask over the frame). */
    fun saveMask(dir: File, pick: Pick, m: Mask) {
        val bw = IntArray(m.w * m.h) { if (m.bits[it]) -1 else 0xFF000000.toInt() }
        File(dir, pick.maskFile).outputStream().use { Bitmap.createBitmap(bw, m.w, m.h, Bitmap.Config.ARGB_8888).compress(Bitmap.CompressFormat.PNG, 100, it) }
        File(dir, "pick.json").writeText(Diagnostics.json.encodeToString(Pick.serializer(), pick) + "\n")
    }

    /** The saved mask (white = object), or null. */
    fun loadMask(dir: File, pick: Pick): Mask? {
        val b = BitmapFactory.decodeFile(File(dir, pick.maskFile).path) ?: return null
        if (b.width != pick.width || b.height != pick.height) return null
        val px = argb(b)
        return Mask(b.width, b.height, BooleanArray(px.size) { (px[it] and 0xFF) > 127 }, pick.maskScore)
    }

    fun load(dir: File): Pick? = File(dir, "pick.json").takeIf { it.exists() }?.let {
        runCatching { Diagnostics.json.decodeFromString(Pick.serializer(), it.readText()) }.getOrNull()
    }

    /** Parses "27,5" or "27.5"; blank -> null. */
    fun cm(s: String): Double? = s.trim().replace(',', '.').toDoubleOrNull()?.takeIf { it > 0 && it < 1000 }
}
