package id.ukurpaket.app.dt

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import id.ukurpaket.app.vio.Bits
import id.ukurpaket.app.vio.Engine
import id.ukurpaket.app.vio.Gray
import id.ukurpaket.app.vio.RecordingIO
import id.ukurpaket.app.vio.RecordingTracker
import id.ukurpaket.app.vio.SweepResult
import java.io.File

/** The on-device engine on one recording folder: Android decoding in, result.json and the evidence photo out. */
object SweepRun {
    fun decoderFor(rotation: Int): (File) -> Gray = { f ->
        val o = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(f.path, o)
        val opts = BitmapFactory.Options().apply { inSampleSize = if (o.outWidth > 1000) 2 else 1 }
        val b = BitmapFactory.decodeFile(f.path, opts) ?: throw IllegalStateException("foto ${f.name} tidak terbaca")
        val px = IntArray(b.width * b.height); b.getPixels(px, 0, b.width, 0, 0, b.width, b.height)
        val y = ByteArray(px.size) { i -> val c = px[i]; (((c shr 16 and 255) * 299 + (c shr 8 and 255) * 587 + (c and 255) * 114) / 1000).toByte() }
        Gray.fromLuma(y, b.width, b.height, down = 1, rotation = rotation)
    }

    fun decodeMask(f: File): Bits? {
        val b = BitmapFactory.decodeFile(f.path) ?: return null
        val px = IntArray(b.width * b.height); b.getPixels(px, 0, b.width, 0, 0, b.width, b.height)
        return Bits(b.width, b.height, BooleanArray(px.size) { (px[it] and 255) > 127 })
    }

    /** [prepared]: the tracking done while recording, when this recording was just made (else it is redone here). */
    fun run(dir: File, prepared: RecordingTracker.Prepared? = null, progress: (String, Float) -> Unit): SweepResult {
        val rot = ObjectPick.rotation(dir)
        val loaded = RecordingIO.load(dir, decoderFor(rot), ::decodeMask, prepared = prepared)
        val r = Engine.run(loaded.input, progress = progress)
        File(dir, "result.json").writeText(Diagnostics.json.encodeToString(SweepResult.serializer(), r) + "\n")
        evidence(dir, loaded.frameIndex[loaded.input.pickFrame], loaded.input.pickFrame, rot, r)
        return r
    }

    fun load(dir: File): SweepResult? = File(dir, "result.json").takeIf { it.exists() }?.let {
        runCatching { Diagnostics.json.decodeFromString(SweepResult.serializer(), it.readText()) }.getOrNull()
    }

    fun evidenceFile(dir: File) = File(dir, "result_photo.jpg")

    /** The picked frame with the object's outline, the box and its size: the record's evidence photo. */
    private fun evidence(dir: File, frameIndex: Int, pos: Int, rot: Int, r: SweepResult) {
        val pic = ObjectPick.upright(dir, frameIndex, rot)?.copy(Bitmap.Config.ARGB_8888, true) ?: return
        val c = Canvas(pic); val w = pic.width.toFloat(); val h = pic.height.toFloat()
        val fill = Paint().apply { color = 0x55ED0677; style = Paint.Style.FILL; isAntiAlias = true }
        val line = Paint().apply { color = Color.rgb(60, 220, 60); style = Paint.Style.STROKE; strokeWidth = w / 220f; isAntiAlias = true }
        r.outlines.getOrNull(pos)?.takeIf { it.size >= 6 }?.let { o ->
            val p = Path(); p.moveTo(o[0] * w, o[1] * h)
            for (i in 2 until o.size step 2) p.lineTo(o[i] * w, o[i + 1] * h)
            p.close(); c.drawPath(p, fill)
        }
        r.boxes.getOrNull(pos)?.takeIf { it.size == 16 }?.let { b ->
            fun pt(i: Int) = b[2 * i] * w to b[2 * i + 1] * h
            for ((a, e) in listOf(0 to 1, 1 to 2, 2 to 3, 3 to 0, 4 to 5, 5 to 6, 6 to 7, 7 to 4, 0 to 4, 1 to 5, 2 to 6, 3 to 7)) {
                val (x0, y0) = pt(a); val (x1, y1) = pt(e); c.drawLine(x0, y0, x1, y1, line)
            }
        }
        val txt = "%.1f × %.1f × %.1f cm".format(r.lengthCm, r.widthCm, r.heightCm).replace('.', ',')
        val tp = Paint().apply { color = Color.WHITE; textSize = w / 16f; isAntiAlias = true; isFakeBoldText = true; setShadowLayer(6f, 0f, 0f, Color.BLACK) }
        c.drawText(txt, w / 30f, w / 12f, tp)
        evidenceFile(dir).outputStream().use { pic.compress(Bitmap.CompressFormat.JPEG, 88, it) }
    }
}
