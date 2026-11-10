package id.ukurpaket.app.photo

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import id.ukurpaket.app.measure.Mask
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.roundToInt

/**
 * The photo mode's files, one folder per object (filesDir/photo_sessions/yyyyMMdd_HHmmss): for each photo the upright
 * picture (photo_N.jpg), the object's mask (mask_N.png), the depth map (depth_N.u16: millimetres, little-endian,
 * width x height in shot_N.json) and shot_N.json (lens, acceleration, the pick, the result); evidence.jpg (the photo
 * with its box) once the size is used. Everything needed to run the measurement again on a PC.
 */
object PhotoFiles {
    val json = Json { prettyPrint = true; encodeDefaults = true; ignoreUnknownKeys = true }

    fun newDir(root: File): File = File(root, SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())).apply { mkdirs() }
    fun photo(dir: File, i: Int) = File(dir, "photo_$i.jpg")
    fun mask(dir: File, i: Int) = File(dir, "mask_$i.png")
    fun depth(dir: File, i: Int) = File(dir, "depth_$i.u16")
    fun record(dir: File, i: Int) = File(dir, "shot_$i.json")
    fun evidence(dir: File) = File(dir, "evidence.jpg")

    /**
     * NV21 (sensor orientation) -> upright ARGB of [ow] x [oh]: each output pixel is the mean of the block of camera
     * pixels it covers (a plain nearest pick would alias the fine print and edges the models look at).
     */
    fun uprightArgb(nv21: ByteArray, sw: Int, sh: Int, rotation: Int, ow: Int, oh: Int): IntArray {
        val rot = ((rotation % 360) + 360) % 360
        val uw = if (rot == 90 || rot == 270) sh else sw; val uh = if (rot == 90 || rot == 270) sw else sh
        val out = IntArray(ow * oh)
        for (oy in 0 until oh) {
            val uy0 = oy * uh / oh; val uy1 = maxOf(uy0 + 1, (oy + 1) * uh / oh)
            for (ox in 0 until ow) {
                val ux0 = ox * uw / ow; val ux1 = maxOf(ux0 + 1, (ox + 1) * uw / ow)
                var r = 0; var g = 0; var b = 0; var n = 0
                for (uy in uy0 until uy1) for (ux in ux0 until ux1) {
                    val x: Int; val y: Int
                    when (rot) { 90 -> { x = uy; y = sh - 1 - ux }; 180 -> { x = sw - 1 - ux; y = sh - 1 - uy }; 270 -> { x = sw - 1 - uy; y = ux }; else -> { x = ux; y = uy } }
                    val yy = (nv21[y * sw + x].toInt() and 255) - 16
                    val vi = sw * sh + (y / 2) * sw + (x / 2) * 2
                    val v = (nv21[vi].toInt() and 255) - 128; val u = (nv21[vi + 1].toInt() and 255) - 128
                    val c = 1.164f * yy
                    r += (c + 1.596f * v).toInt().coerceIn(0, 255); g += (c - 0.392f * u - 0.813f * v).toInt().coerceIn(0, 255)
                    b += (c + 2.017f * u).toInt().coerceIn(0, 255); n++
                }
                out[oy * ow + ox] = (0xFF shl 24) or ((r / n) shl 16) or ((g / n) shl 8) or (b / n)
            }
        }
        return out
    }

    fun bitmap(argb: IntArray, w: Int, h: Int): Bitmap = Bitmap.createBitmap(argb, w, h, Bitmap.Config.ARGB_8888)

    fun saveJpeg(b: Bitmap, f: File, quality: Int = 88) { f.outputStream().buffered().use { b.compress(Bitmap.CompressFormat.JPEG, quality, it) } }

    fun saveMask(m: Mask, f: File) {
        val px = IntArray(m.w * m.h) { if (m.bits[it]) Color.WHITE else Color.BLACK }
        f.outputStream().buffered().use { Bitmap.createBitmap(px, m.w, m.h, Bitmap.Config.ARGB_8888).compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    fun saveDepth(d: DepthMap, f: File) {
        val bytes = ByteArray(d.z.size * 2)
        for (i in d.z.indices) {
            val mm = (d.z[i] * 1000f).roundToInt().coerceIn(0, 65535)
            bytes[2 * i] = (mm and 255).toByte(); bytes[2 * i + 1] = (mm shr 8).toByte()
        }
        f.writeBytes(bytes)
    }

    /** The photo with the measured box drawn (the record's evidence), at the photo's own size. */
    fun evidence(photo: Bitmap, corners: List<Float>, outline: List<Float>?, out: File) {
        val b = photo.copy(Bitmap.Config.ARGB_8888, true)
        val c = Canvas(b)
        val w = b.width.toFloat(); val h = b.height.toFloat()
        val s = w / 480f
        if (outline != null && outline.size >= 6) {
            val p = android.graphics.Path().apply {
                moveTo(outline[0] * w, outline[1] * h); var i = 2
                while (i + 1 < outline.size) { lineTo(outline[i] * w, outline[i + 1] * h); i += 2 }
                close()
            }
            c.drawPath(p, Paint().apply { color = 0x55ED0677; style = Paint.Style.FILL; isAntiAlias = true })
        }
        if (corners.size == 16) {
            val paint = Paint().apply { color = 0xFF3CDC3C.toInt(); strokeWidth = 3.5f * s; isAntiAlias = true; strokeCap = Paint.Cap.ROUND }
            fun pt(i: Int) = floatArrayOf(corners[2 * i] * w, corners[2 * i + 1] * h)
            for ((a, e) in EDGES) { if (!drawable(corners, a) || !drawable(corners, e)) continue; val p = pt(a); val q = pt(e); c.drawLine(p[0], p[1], q[0], q[1], paint) }
        }
        saveJpeg(b, out, 85)
    }

    /** Corner [i] of PhotoResult.corners is in front of the camera (outside the picture is fine: the drawing clips). */
    fun drawable(corners: List<Float>, i: Int) = corners[2 * i] > PhotoMeasure.BEHIND / 2 && corners[2 * i + 1] > PhotoMeasure.BEHIND / 2

    /** The 12 edges of the box, as indices into its 8 corners (floor 0-3, top 4-7). */
    val EDGES = listOf(0 to 1, 1 to 2, 2 to 3, 3 to 0, 4 to 5, 5 to 6, 6 to 7, 7 to 4, 0 to 4, 1 to 5, 2 to 6, 3 to 7)
}

/**
 * The autofocus when the photo was taken: [diopters] = 1 / distance in metres (0 = infinity); [calibration] is how far
 * the camera says that can be trusted ("calibrated", "approximate", "uncalibrated"). Recorded to judge, on the PC,
 * whether the DT50's focus can serve as a physical check of the camera's distance.
 */
@Serializable
data class FocusInfo(val diopters: Float, val calibration: String, val minFocusDiopters: Float? = null, val hyperfocalDiopters: Float? = null,
                     val afState: Int? = null)

/** What shot_N.json holds. */
@Serializable
data class ShotRecord(
    val index: Int,
    val created: Long,
    val stream: List<Int>,
    val rotationDeg: Int,
    /** Lens of the upright full picture, and of the 480 x 640 picture the models saw. */
    val lens: Intrinsics,
    val lensModel: Intrinsics,
    /** Mean acceleration (device axes, m/s²) over the 0,4 s before the photo, how much it wandered, and 'still'. */
    val accel: List<Float>,
    val accelSpread: Float,
    val still: Boolean,
    val downDeg: Float,
    val pickMode: String? = null,
    val tap: List<Float>? = null,
    val box: List<Float>? = null,
    val maskScore: Float? = null,
    val samMs: Long? = null,
    val depthMs: Long? = null,
    val depthSize: List<Int>? = null,
    val result: PhotoResult? = null,
    val error: String? = null,
    /** Tape-measure size typed for testing or calibration (cm), when given. */
    val tapeCm: List<Double>? = null,
    val focus: FocusInfo? = null,
    /** App version that took the photo. */
    val app: String? = null,
)
