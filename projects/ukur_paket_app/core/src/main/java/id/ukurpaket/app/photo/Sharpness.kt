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
 * or a rounded corner) is the photo's sharpness. On the first real DT50 photos: 1,1-2,1 for the in-focus ones (a carton,
 * two of a cigarette pack), 0,24-0,41 for the blurred ones (the iPhone twice, a book, a parcel, a bottle): a gap of 3x.
 *
 * The same profiles serve the focus sweep (FocusSweep): each outline point's sharpness through a series of lens
 * positions finds the distance of that point of the object's edge.
 */
object Sharpness {
    /** Below this the object is taken as out of focus: the autofocus distance is not used. */
    const val MIN = 0.6f

    /**
     * The object's outline in a picture of [w] x [h] (full resolution): points ([x], [y]) on it and the normal ([nx],
     * [ny]) pointing into the object, from [mask] at any lower resolution of the same picture; every [step]-th point.
     */
    class Outline(val x: FloatArray, val y: FloatArray, val nx: FloatArray, val ny: FloatArray, val w: Int, val h: Int) {
        val size get() = x.size

        companion object {
            fun of(mask: Mask, w: Int, h: Int, step: Int = 3, half: Float = HALF): Outline {
                val mw = mask.w; val mh = mask.h
                val r = 2
                val blur = FloatArray(mw * mh)
                run {
                    val tmp = FloatArray(mw * mh)
                    for (yy in 0 until mh) for (xx in 0 until mw) {
                        var s = 0; for (d in -r..r) if (mask[xx + d, yy]) s++
                        tmp[yy * mw + xx] = s.toFloat()
                    }
                    for (yy in 0 until mh) for (xx in 0 until mw) {
                        var s = 0f; for (d in -r..r) { val y2 = yy + d; if (y2 in 0 until mh) s += tmp[y2 * mw + xx] }
                        blur[yy * mw + xx] = s
                    }
                }
                val sx = w.toFloat() / mw; val sy = h.toFloat() / mh
                val xs = ArrayList<Float>(); val ys = ArrayList<Float>(); val nxs = ArrayList<Float>(); val nys = ArrayList<Float>()
                var count = 0
                for (yy in 1 until mh - 1) for (xx in 1 until mw - 1) {
                    if (!mask.bits[yy * mw + xx]) continue
                    if (mask[xx - 1, yy] && mask[xx + 1, yy] && mask[xx, yy - 1] && mask[xx, yy + 1]) continue
                    if (count++ % step != 0) continue
                    val gx = (blur[yy * mw + xx + 1] - blur[yy * mw + xx - 1]) * sx
                    val gy = (blur[(yy + 1) * mw + xx] - blur[(yy - 1) * mw + xx]) * sy
                    val gn = hypot(gx, gy); if (gn < 1e-3f) continue
                    val cx = (xx + 0.5f) * sx; val cy = (yy + 0.5f) * sy; val nx = gx / gn; val ny = gy / gn
                    if (min(cx - half * abs(nx), cx + half * abs(nx)) < 1 || min(cy - half * abs(ny), cy + half * abs(ny)) < 1 ||
                        cx + half * abs(nx) > w - 2 || cy + half * abs(ny) > h - 2) continue
                    xs += cx; ys += cy; nxs += nx; nys += ny
                }
                return Outline(xs.toFloatArray(), ys.toFloatArray(), nxs.toFloatArray(), nys.toFloatArray(), w, h)
            }
        }
    }

    /** Half length of a profile across the outline, pixels. */
    const val HALF = 12f

    /**
     * Sharpness of outline point [i] in [luma] (the outline's picture size, 0-255): steepest slope over step height
     * (about 1 / edge width in pixels); null where the step has too little contrast to judge. [buf]: scratch space.
     */
    fun at(o: Outline, i: Int, luma: ByteArray, buf: FloatArray = FloatArray(PROFILE)): Float? {
        val w = o.w
        fun lum(x: Float, y: Float): Float {
            val x0 = floor(x).toInt(); val y0 = floor(y).toInt(); val ax = x - x0; val ay = y - y0
            fun p(a: Int, b: Int) = (luma[b * w + a].toInt() and 255).toFloat()
            return (p(x0, y0) * (1 - ax) + p(x0 + 1, y0) * ax) * (1 - ay) + (p(x0, y0 + 1) * (1 - ax) + p(x0 + 1, y0 + 1) * ax) * ay
        }
        val cx = o.x[i]; val cy = o.y[i]; val nx = o.nx[i]; val ny = o.ny[i]
        for (k in 0 until PROFILE) { val t = -HALF + k * 0.25f; buf[k] = lum(cx + t * nx, cy + t * ny) }
        val m = 12                                                   // 12 samples (3 px) at each end
        val lo = buf.copyOfRange(0, m).sorted()[m / 2]; val hi = buf.copyOfRange(PROFILE - m, PROFILE).sorted()[m / 2]
        val stepH = hi - lo
        if (abs(stepH) < 15f) return null
        var g = 0f
        for (k in 1 until PROFILE - 1) g = max(g, abs(buf[k + 1] - buf[k - 1]) / 0.5f)
        return g / abs(stepH)
    }
    private const val PROFILE = (2 * HALF / 0.25f).toInt() + 1

    /**
     * Sharpness of the object's outline: [luma] is the full-resolution picture ([w] x [h], 0-255), [mask] the object at
     * any lower resolution of the same picture. Null when the outline has too few contrasted stretches to judge.
     */
    fun atOutline(luma: ByteArray, w: Int, h: Int, mask: Mask, step: Int = 3): Float? {
        val o = Outline.of(mask, w, h, step)
        val buf = FloatArray(PROFILE)
        val out = ArrayList<Float>()
        for (i in 0 until o.size) at(o, i, luma, buf)?.let { out += it }
        if (out.size < 20) return null
        out.sort()
        return out[(out.size * 3) / 4]
    }
}
