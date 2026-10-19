package id.ukurpaket.app.ar

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.DashPathEffect
import android.graphics.ImageFormat
import android.graphics.Paint
import android.graphics.PointF
import android.graphics.Rect
import android.graphics.YuvImage
import android.media.Image
import com.google.ar.core.Camera
import com.google.ar.core.Frame
import id.ukurpaket.app.measure.BoxResult
import id.ukurpaket.app.measure.V3
import java.io.ByteArrayOutputStream
import java.io.File
import kotlin.math.max

object Yuv {
    /** YUV_420_888 camera image to NV21, honouring row and pixel strides. */
    fun toNv21(image: Image): ByteArray {
        val w = image.width; val h = image.height
        val yP = image.planes[0]; val uP = image.planes[1]; val vP = image.planes[2]
        val out = ByteArray(w * h * 3 / 2)
        var pos = 0
        val yb = yP.buffer
        for (row in 0 until h) {
            val base = row * yP.rowStride
            if (yP.pixelStride == 1) { yb.position(base); yb.get(out, pos, w); pos += w }
            else for (col in 0 until w) out[pos++] = yb.get(base + col * yP.pixelStride)
        }
        val ub = uP.buffer; val vb = vP.buffer
        for (row in 0 until h / 2) for (col in 0 until w / 2) {
            out[pos++] = vb.get(row * vP.rowStride + col * vP.pixelStride)
            out[pos++] = ub.get(row * uP.rowStride + col * uP.pixelStride)
        }
        return out
    }

    /** YUV_420_888 camera image to packed ARGB pixels (BT.601), for the segmentation model. */
    fun toArgb(image: Image): IntArray {
        val w = image.width; val h = image.height
        val yP = image.planes[0]; val uP = image.planes[1]; val vP = image.planes[2]
        val yb = yP.buffer; val ub = uP.buffer; val vb = vP.buffer
        val out = IntArray(w * h)
        for (row in 0 until h) {
            val yr = row * yP.rowStride; val cr = (row / 2)
            for (col in 0 until w) {
                val y = (yb.get(yr + col * yP.pixelStride).toInt() and 255) - 16
                val u = (ub.get(cr * uP.rowStride + (col / 2) * uP.pixelStride).toInt() and 255) - 128
                val v = (vb.get(cr * vP.rowStride + (col / 2) * vP.pixelStride).toInt() and 255) - 128
                val yy = 1.164f * y
                val r = (yy + 1.596f * v).toInt().coerceIn(0, 255)
                val g = (yy - 0.392f * u - 0.813f * v).toInt().coerceIn(0, 255)
                val b = (yy + 2.017f * u).toInt().coerceIn(0, 255)
                out[row * w + col] = (0xFF shl 24) or (r shl 16) or (g shl 8) or b
            }
        }
        return out
    }

    fun nv21ToJpeg(nv21: ByteArray, w: Int, h: Int, quality: Int): ByteArray {
        val bos = ByteArrayOutputStream()
        YuvImage(nv21, ImageFormat.NV21, w, h, null).compressToJpeg(Rect(0, 0, w, h), quality, bos)
        return bos.toByteArray()
    }
}

/** The evidence photo: the camera frame at the moment of measuring, with the 3D box drawn on it (when there is one). */
object Snapshot {
    fun save(frame: Frame, cam: Camera, r: BoxResult?, file: File): File? = try {
        val img = frame.acquireCameraImage()
        val jpeg = try { Yuv.nv21ToJpeg(Yuv.toNv21(img), img.width, img.height, 90) } finally { img.close() }
        val bmp = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.size).copy(Bitmap.Config.ARGB_8888, true)
        if (r != null) draw(bmp, cam, r)
        val rot = android.graphics.Matrix().apply { postRotate(90f) }     // sensor is landscape, the app is portrait
        var out = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, rot, true)
        val scale = 1280f / max(out.width, out.height)
        if (scale < 1f) out = Bitmap.createScaledBitmap(out, (out.width * scale).toInt(), (out.height * scale).toInt(), true)
        file.parentFile?.mkdirs()
        file.outputStream().use { out.compress(Bitmap.CompressFormat.JPEG, 85, it) }
        file
    } catch (e: Exception) {
        null
    }

    private fun draw(bmp: Bitmap, cam: Camera, r: BoxResult) {
        val intr = cam.imageIntrinsics
        val f = intr.focalLength; val pp = intr.principalPoint; val dims = intr.imageDimensions
        val sx = bmp.width.toFloat() / dims[0]; val sy = bmp.height.toFloat() / dims[1]
        val inv = cam.pose.inverse()
        fun px(p: V3): PointF? {
            val l = inv.transformPoint(floatArrayOf(p.x, p.y, p.z))
            if (l[2] > -0.02f) return null
            return PointF((pp[0] + f[0] * l[0] / -l[2]) * sx, (pp[1] - f[1] * l[1] / -l[2]) * sy)
        }
        val c = Canvas(bmp)
        val k = bmp.width / 640f
        val green = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0xFF22C55E.toInt(); strokeWidth = 5f * k; style = Paint.Style.STROKE }
        val dashed = Paint(green).apply { strokeWidth = 3f * k; pathEffect = DashPathEffect(floatArrayOf(10f * k, 7f * k), 0f) }
        val fl = r.floorCorners.map { px(it) }
        val tp = r.topCorners.map { px(it) }
        for (i in 0 until 4) {
            val j = (i + 1) % 4
            line(c, fl[i], fl[j], dashed); line(c, tp[i], tp[j], green); line(c, fl[i], tp[i], green)
        }
    }

    private fun line(c: Canvas, a: PointF?, b: PointF?, p: Paint) {
        if (a != null && b != null) c.drawLine(a.x, a.y, b.x, b.y, p)
    }
}
