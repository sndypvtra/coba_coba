package id.ukurpaket.app.photo

import android.media.Image

/**
 * Camera2 frame helpers shared by the photo camera and the DT20 sweep recorder (moved here from SweepRecorder when the
 * engine became its own module, so both apps use the same code).
 */
object CameraFrames {
    /** 4:3, about 1280 wide (label still readable, small files); else the nearest 4:3 at least 640 wide. */
    fun pickSize(sizes: List<Pair<Int, Int>>): Pair<Int, Int>? {
        val four3 = sizes.filter { (w, h) -> w * 3 == h * 4 && w >= 640 }
        return four3.filter { it.first <= 1280 }.maxByOrNull { it.first } ?: four3.minByOrNull { it.first }
            ?: sizes.filter { it.first >= 640 }.minByOrNull { it.first * it.second }
    }

    /** YUV_420_888 (any strides) to NV21. */
    fun toNv21(img: Image): ByteArray {
        val w = img.width; val h = img.height
        val out = ByteArray(w * h * 3 / 2)
        val y = img.planes[0]; val u = img.planes[1]; val v = img.planes[2]
        val yb = y.buffer; var o = 0
        for (row in 0 until h) {
            yb.position(row * y.rowStride)
            if (y.pixelStride == 1) { yb.get(out, o, w); o += w }
            else for (x in 0 until w) out[o++] = yb.get(row * y.rowStride + x * y.pixelStride)
        }
        val ub = u.buffer; val vb = v.buffer
        for (row in 0 until h / 2) for (x in 0 until w / 2) {
            out[o++] = vb.get(row * v.rowStride + x * v.pixelStride)
            out[o++] = ub.get(row * u.rowStride + x * u.pixelStride)
        }
        return out
    }

    /** The luma plane of a YUV image, tightly packed (width x height). */
    fun luma(img: Image): ByteArray {
        val pl = img.planes[0]; val buf = pl.buffer; val w = img.width; val h = img.height
        val out = ByteArray(w * h)
        if (pl.pixelStride == 1 && pl.rowStride == w) { buf.rewind(); buf.get(out, 0, w * h); return out }
        if (pl.pixelStride == 1) {
            for (y in 0 until h) { buf.position(y * pl.rowStride); buf.get(out, y * w, w) }
            buf.rewind(); return out
        }
        for (y in 0 until h) for (x in 0 until w) out[y * w + x] = buf.get(y * pl.rowStride + x * pl.pixelStride)
        return out
    }

    /** Mean luma of a camera image, every 16th pixel. */
    fun meanLuma(img: Image): Double {
        val pl = img.planes[0]; val buf = pl.buffer; val rs = pl.rowStride; val ps = pl.pixelStride
        var sum = 0L; var n = 0
        var y = 0
        while (y < img.height) { var x = 0; while (x < img.width) { sum += buf.get(y * rs + x * ps).toInt() and 255; n++; x += 16 }; y += 16 }
        return if (n == 0) 128.0 else sum.toDouble() / n
    }
}
