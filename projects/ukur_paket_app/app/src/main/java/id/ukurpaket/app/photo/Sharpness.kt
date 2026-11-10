package id.ukurpaket.app.photo

import id.ukurpaket.app.measure.Mask
import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

/*
 * Is the object in focus? (0.4.5) The autofocus distance is the photo mode's scale close up, and the camera's own word
 * ("focused") is not enough: on an iPhone's black glossy screen the DT50 reported a sharp focus at about 32 cm while the
 * phone was 13 cm away and the photo was plainly blurred (the lens had settled on a reflection). So the photo itself is
 * asked: across the object's outline, how steep is the step from the background to the object?
 *
 * For each outline point a profile is sampled along the outline's normal in the full-resolution picture; its steepest
 * slope divided by the height of its step is about 1 / (width of the edge in pixels): a step blurred over w pixels
 * peaks near 1/w. The 75th percentile over the outline (the outline's sharpest stretches: a part may be soft, a shadow
 * or a rounded corner) is the photo's sharpness. On the first real DT50 photos: 1,2-2,2 for the in-focus ones (a carton,
 * two of a cigarette pack), 0,23-0,39 for the blurred ones (the iPhone, a book, a parcel, a bottle): a gap of 3x.
 */
object Sharpness {
    /** Below this the object is taken as out of focus: the autofocus distance is not used. */
    const val MIN = 0.6f

    /**
     * Sharpness of the object's outline: [luma] is the full-resolution picture ([w] x [h], 0-255), [mask] the object at
     * any lower resolution of the same picture. Null when the outline has too few contrasted stretches to judge.
     */
    fun atOutline(luma: ByteArray, w: Int, h: Int, mask: Mask, step: Int = 3, half: Float = 12f): Float? {
        // the outline's normals from a lightly blurred mask (box filter, radius 2 at the mask's resolution)
        val mw = mask.w; val mh = mask.h
        val r = 2
        val blur = FloatArray(mw * mh)
        run {
            val tmp = FloatArray(mw * mh)
            for (y in 0 until mh) for (x in 0 until mw) {
                var s = 0; for (d in -r..r) if (mask[x + d, y]) s++
                tmp[y * mw + x] = s.toFloat()
            }
            for (y in 0 until mh) for (x in 0 until mw) {
                var s = 0f; for (d in -r..r) { val yy = y + d; if (yy in 0 until mh) s += tmp[yy * mw + x] }
                blur[y * mw + x] = s
            }
        }
        val sx = w.toFloat() / mw; val sy = h.toFloat() / mh
        fun lum(x: Float, y: Float): Float {
            val x0 = floor(x).toInt(); val y0 = floor(y).toInt(); val ax = x - x0; val ay = y - y0
            fun p(i: Int, j: Int) = (luma[j * w + i].toInt() and 255).toFloat()
            return (p(x0, y0) * (1 - ax) + p(x0 + 1, y0) * ax) * (1 - ay) + (p(x0, y0 + 1) * (1 - ax) + p(x0 + 1, y0 + 1) * ax) * ay
        }
        val n = (2 * half / 0.25f).toInt() + 1
        val v = FloatArray(n)
        val out = ArrayList<Float>()
        var count = 0
        for (y in 1 until mh - 1) for (x in 1 until mw - 1) {
            if (!mask.bits[y * mw + x]) continue
            if (mask[x - 1, y] && mask[x + 1, y] && mask[x, y - 1] && mask[x, y + 1]) continue
            if (count++ % step != 0) continue
            // the normal, pointing into the object, in full-resolution pixels
            val gx = (blur[y * mw + x + 1] - blur[y * mw + x - 1]) * sx
            val gy = (blur[(y + 1) * mw + x] - blur[(y - 1) * mw + x]) * sy
            val gn = hypot(gx, gy); if (gn < 1e-3f) continue
            val nx = gx / gn; val ny = gy / gn
            val cx = (x + 0.5f) * sx; val cy = (y + 0.5f) * sy
            val x0 = cx - half * nx; val y0 = cy - half * ny; val x1 = cx + half * nx; val y1 = cy + half * ny
            if (min(x0, x1) < 1 || min(y0, y1) < 1 || max(x0, x1) > w - 2 || max(y0, y1) > h - 2) continue
            for (i in 0 until n) { val t = -half + i * 0.25f; v[i] = lum(cx + t * nx, cy + t * ny) }
            val m = 12 * 4 / 4                                           // 12 samples (3 px) at each end
            val lo = v.copyOfRange(0, m).sorted()[m / 2]; val hi = v.copyOfRange(n - m, n).sorted()[m / 2]
            val stepH = hi - lo
            if (abs(stepH) < 15f) continue                               // too little contrast to judge
            var g = 0f
            for (i in 1 until n - 1) g = max(g, abs(v[i + 1] - v[i - 1]) / 0.5f)
            out += g / abs(stepH)
        }
        if (out.size < 20) return null
        out.sort()
        return out[(out.size * 3) / 4]
    }
}
