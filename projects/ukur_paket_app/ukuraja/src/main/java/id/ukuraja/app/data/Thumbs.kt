package id.ukuraja.app.data

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.ByteArrayOutputStream
import java.io.File
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** The evidence photos made small for the Excel report. */
object Thumbs {
    /**
     * The photo at [path] at most [maxW] x [maxH] pixels (twice the cell, so it stays sharp when zoomed in), as JPEG.
     * It is decoded at a power-of-two reduction first, so a large photo never fills the memory. Null without a photo.
     */
    fun of(path: String?, maxW: Int = Report.PHOTO_W * 2, maxH: Int = Report.PHOTO_H * 2, quality: Int = 80): Thumb? {
        val f = path?.let(::File)?.takeIf { it.isFile } ?: return null
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(f.path, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
        var sample = 1
        while (bounds.outWidth / (sample * 2) >= maxW && bounds.outHeight / (sample * 2) >= maxH) sample *= 2
        val b = BitmapFactory.decodeFile(f.path, BitmapFactory.Options().apply { inSampleSize = sample }) ?: return null
        val k = min(maxW.toFloat() / b.width, maxH.toFloat() / b.height).coerceAtMost(1f)
        val s = if (k < 1f) Bitmap.createScaledBitmap(b, max(1, (b.width * k).roundToInt()), max(1, (b.height * k).roundToInt()), true) else b
        val out = ByteArrayOutputStream()
        s.compress(Bitmap.CompressFormat.JPEG, quality, out)
        val t = Thumb(out.toByteArray(), s.width, s.height)
        if (s !== b) s.recycle()
        b.recycle()
        return t
    }
}
