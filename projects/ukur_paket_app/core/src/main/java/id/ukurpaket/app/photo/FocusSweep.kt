package id.ukurpaket.app.photo

import id.ukurpaket.app.measure.Mask

/*
 * The distance from a focus sweep (0.4.6). The camera's autofocus measures the middle of the picture, and it needs
 * texture there: on a cigarette pack (print) it found the distance within 2 %; on an iPhone (a black glossy screen, a
 * plain dark case) it locked somewhere else and the photo came out blurred, twice. What every object does have is its
 * outline: SAM could only cut it out because it differs from what is behind it.
 *
 * So after the photo the lens is stepped through a series of positions (16, from far to near, about 2 s with the phone
 * held still) and a frame kept at each. Once the object is picked, each point of its outline is looked at through the
 * series: its edge is sharpest where the lens focused at that point's distance. A defocused edge's width grows with the
 * focus error and adds to the lens's own sharpness in quadrature, so 1 / sharpness² is a parabola in dioptres and its
 * vertex is the point's focus. The box's geometry gives that point's depth per metre of camera height, so each point
 * gives the camera height; the median over the outline is the sweep's answer, the spread its own check.
 */
class SweepFrame(
    /** The lens position the camera reported for the frame (its own units; real dioptres = factor x this). */
    val diopters: Float,
    /** The upright luma of the frame, [SweepData.w] x [SweepData.h]. */
    val luma: ByteArray,
)

class SweepData(val frames: List<SweepFrame>, val w: Int, val h: Int)

object FocusSweep {
    /** The answer: the camera height (metres), the spread of the points' answers ((p75 - p25) / median), how many points. */
    class Result(val heightM: Float, val spread: Float, val points: Int, val outline: Int, val medianDiopters: Float)

    /** Least share of the outline with a clear focus peak for the sweep to count. */
    const val MIN_SHARE = 0.25f

    /**
     * The camera height from [sweep] for the object [mask] (any resolution of the same picture): for each outline point
     * the reported dioptres of its sharpest focus, turned real by [factor], and [depthUnitAt] (the box's depth per metre
     * of camera height at a picture position given as fractions of its width and height). Null when too few points
     * show a clear peak (the phone moved, the camera did not move its lens, the object is beyond the focus range).
     */
    fun estimate(sweep: SweepData, mask: Mask, factor: Double, depthUnitAt: (fx: Float, fy: Float) -> Float?, trace: ((String) -> Unit)? = null): Result? {
        val frames = sweep.frames.sortedBy { it.diopters }
        if (frames.size < 5) return null
        // the lens must really have moved: at least a factor of 4 between the nearest and the farthest kept frame
        if (frames.last().diopters < 4 * frames.first().diopters.coerceAtLeast(0.05f)) return null
        val o = Sharpness.Outline.of(mask, sweep.w, sweep.h, step = 2)
        if (o.size < 30) return null
        val buf = FloatArray(200)
        val hs = ArrayList<Float>(); val ds = ArrayList<Float>()
        val s = FloatArray(frames.size)
        for (i in 0 until o.size) {
            var ok = true
            for (k in frames.indices) { val v = Sharpness.at(o, i, frames[k].luma, buf); if (v == null) { ok = false; break }; s[k] = v }
            if (!ok) continue
            var kb = 0; for (k in frames.indices) if (s[k] > s[kb]) kb = k
            val smin = s.minOrNull() ?: continue
            // a clear peak, inside the series: sharp enough there, and well above its blurred ends
            if (kb == 0 || kb == frames.lastIndex || s[kb] < 0.5f || s[kb] < 1.6f * smin) continue
            // 1 / s² against dioptres round the peak: a parabola whose vertex is the focus
            val k0 = (kb - 2).coerceAtLeast(0); val k1 = (kb + 2).coerceAtMost(frames.lastIndex)
            val d = DoubleArray(k1 - k0 + 1) { frames[k0 + it].diopters.toDouble() }
            val y = DoubleArray(k1 - k0 + 1) { 1.0 / (s[k0 + it] * s[k0 + it]) }
            val p = parabola(d, y)
            var dStar = frames[kb].diopters.toDouble()
            if (p != null && p[2] > 0) {
                val v = -p[1] / (2 * p[2])
                if (v > frames[kb - 1].diopters && v < frames[kb + 1].diopters) dStar = v
            }
            // the point's depth per metre of camera height: just inside the outline, on the box
            val zu = depthUnitAt((o.x[i] + 2 * o.nx[i]) / sweep.w, (o.y[i] + 2 * o.ny[i]) / sweep.h) ?: continue
            if (zu <= 0f) continue
            val h = (1.0 / (factor * dStar * zu)).toFloat()
            if (h.isFinite() && h > 0f) { hs += h; ds += dStar.toFloat() }
        }
        trace?.invoke("focus sweep: ${hs.size} of ${o.size} outline points with a clear peak")
        if (hs.size < 15 || hs.size < MIN_SHARE * o.size) return null
        hs.sort(); ds.sort()
        val med = hs[hs.size / 2]
        val spread = (hs[(hs.size * 3) / 4] - hs[hs.size / 4]) / med
        return Result(med, spread, hs.size, o.size, ds[ds.size / 2])
    }

    /** Least-squares parabola y = a + b x + c x²: [a, b, c], or null if degenerate. */
    private fun parabola(x: DoubleArray, y: DoubleArray): DoubleArray? {
        if (x.size < 3) return null
        var s0 = 0.0; var s1 = 0.0; var s2 = 0.0; var s3 = 0.0; var s4 = 0.0; var t0 = 0.0; var t1 = 0.0; var t2 = 0.0
        for (i in x.indices) { val a = x[i]; val a2 = a * a; s0 += 1; s1 += a; s2 += a2; s3 += a2 * a; s4 += a2 * a2; t0 += y[i]; t1 += y[i] * a; t2 += y[i] * a2 }
        val m = arrayOf(doubleArrayOf(s0, s1, s2, t0), doubleArrayOf(s1, s2, s3, t1), doubleArrayOf(s2, s3, s4, t2))
        for (c in 0..2) {
            var p = c; for (r in c + 1..2) if (kotlin.math.abs(m[r][c]) > kotlin.math.abs(m[p][c])) p = r
            if (kotlin.math.abs(m[p][c]) < 1e-12) return null
            val t = m[c]; m[c] = m[p]; m[p] = t
            for (r in 0..2) if (r != c) { val f = m[r][c] / m[c][c]; for (k in c..3) m[r][k] -= f * m[c][k] }
        }
        return DoubleArray(3) { m[it][3] / m[it][it] }
    }
}
