package id.ukurpaket.app.measure

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * The printed sheet for phones without ARCore: a black square ring on A4 (outer 160 mm, inner 100 mm),
 * plus a 100 mm check bar to verify the print came out at 100 %. Laid on the floor next to the parcel,
 * it gives the floor plane, the scale and the camera pose from one photo.
 */
object MarkerSheet {
    const val OUTER = 0.160f
    const val INNER = 0.100f
    const val CHECK_BAR = 0.100f

    /** Ring corners in sheet metres, centred: outer 0-3 then inner 4-7, clockwise as seen from above. */
    val model: List<P2> = run {
        val o = OUTER / 2; val i = INNER / 2
        listOf(P2(-o, -o), P2(o, -o), P2(o, o), P2(-o, o), P2(-i, -i), P2(i, -i), P2(i, i), P2(-i, i))
    }
}

class MarkerHit(
    /** The 8 ring corners in image pixels, same order as [MarkerSheet.model]. */
    val corners: List<P2>,
    /** Sheet metres -> image pixels. */
    val h: DoubleArray,
    val contrast: Float,
)

/**
 * Finds the ring in a grey image: dark blobs from a local threshold, a quadrilateral around each, a check
 * that ring / hole / margin are dark / light / light where the sheet says, then each of the 8 edges
 * re-fitted on the image gradient for sub-pixel corners. Plain Kotlin, no OpenCV.
 */
object MarkerDetector {
    fun detect(gray: IntArray, w: Int, h: Int): MarkerHit? {
        val dark = threshold(gray, w, h)
        var best: MarkerHit? = null
        for (quad in candidates(dark, w, h)) {
            for (rot in 0 until 4) {
                val q = List(4) { quad[(it + rot) % 4] }
                val hm = homography(MarkerSheet.model.take(4), q) ?: continue
                val contrast = verify(gray, w, h, hm) ?: continue
                val refined = refine(gray, w, h, hm) ?: continue
                val hr = homography(MarkerSheet.model, refined) ?: continue
                val c2 = verify(gray, w, h, hr) ?: continue
                if (best == null || c2 > best.contrast) best = MarkerHit(refined, hr, c2)
                break                                      // the ring is symmetric: one orientation is enough
            }
        }
        return best
    }

    /** Dark = clearly darker than the local mean (window ~1/8 of the image), from an integral image. */
    private fun threshold(g: IntArray, w: Int, h: Int): BooleanArray {
        val ii = LongArray((w + 1) * (h + 1))
        for (y in 0 until h) {
            var row = 0L
            for (x in 0 until w) { row += g[y * w + x]; ii[(y + 1) * (w + 1) + x + 1] = ii[y * (w + 1) + x + 1] + row }
        }
        val r = max(8, min(w, h) / 8)
        return BooleanArray(w * h) { i ->
            val x = i % w; val y = i / w
            val xa = max(0, x - r); val xb = min(w, x + r + 1); val ya = max(0, y - r); val yb = min(h, y + r + 1)
            val s = ii[yb * (w + 1) + xb] - ii[ya * (w + 1) + xb] - ii[yb * (w + 1) + xa] + ii[ya * (w + 1) + xa]
            val mean = s.toFloat() / ((xb - xa) * (yb - ya))
            g[i] < mean - 18 && g[i] < 150
        }
    }

    /** Each sizeable dark blob's outer quadrilateral, clockwise in the image. */
    private fun candidates(dark: BooleanArray, w: Int, h: Int): List<List<P2>> {
        val label = IntArray(w * h)
        val queue = IntArray(w * h)
        val out = ArrayList<List<P2>>()
        var next = 0
        val minArea = w * h / 1500; val maxArea = w * h / 3
        for (i in dark.indices) {
            if (!dark[i] || label[i] != 0) continue
            next++
            var head = 0; var tail = 0
            queue[tail++] = i; label[i] = next
            while (head < tail) {
                val p = queue[head++]
                val x = p % w; val y = p / w
                if (x > 0 && dark[p - 1] && label[p - 1] == 0) { label[p - 1] = next; queue[tail++] = p - 1 }
                if (x < w - 1 && dark[p + 1] && label[p + 1] == 0) { label[p + 1] = next; queue[tail++] = p + 1 }
                if (y > 0 && dark[p - w] && label[p - w] == 0) { label[p - w] = next; queue[tail++] = p - w }
                if (y < h - 1 && dark[p + w] && label[p + w] == 0) { label[p + w] = next; queue[tail++] = p + w }
            }
            if (tail < minArea || tail > maxArea) continue
            // hull candidates: the leftmost and rightmost pixel of every row
            val lo = HashMap<Int, Int>(); val hi = HashMap<Int, Int>()
            for (k in 0 until tail) {
                val p = queue[k]; val x = p % w; val y = p / w
                if (x < (lo[y] ?: Int.MAX_VALUE)) lo[y] = x
                if (x > (hi[y] ?: Int.MIN_VALUE)) hi[y] = x
            }
            val edge = lo.map { P2(it.value.toFloat(), it.key.toFloat()) } + hi.map { P2(it.value + 1f, it.key.toFloat()) }
            val hull = convexHull(edge)
            if (hull.size < 4) continue
            val quad = quadOf(hull) ?: continue
            val area = polyArea(quad)
            // a ring fills 1 - (100/160)^2 = 61 % of its square (less or more in perspective)
            val fill = tail / area
            if (fill < 0.35f || fill > 0.85f) continue
            out.add(quad)
        }
        return out.sortedByDescending { polyArea(it) }.take(12)
    }

    /** Four hull points spanning the largest quadrilateral (two diagonal ends, then the farthest on each side). */
    private fun quadOf(hull: List<P2>): List<P2>? {
        val c = P2(hull.map { it.a }.average().toFloat(), hull.map { it.b }.average().toFloat())
        val a = hull.maxBy { d2(it, c) }
        val b = hull.maxBy { d2(it, a) }
        fun side(p: P2) = (b.a - a.a) * (p.b - a.b) - (b.b - a.b) * (p.a - a.a)
        val p1 = hull.maxBy { side(it) }; val p2 = hull.minBy { side(it) }
        if (side(p1) <= 0f || side(p2) >= 0f) return null
        val q = listOf(a, p1, b, p2)
        // clockwise in image coordinates (y down) = positive signed area
        val ordered = if (signedArea(q) > 0) q else q.reversed()
        // start at the corner nearest the top-left, for a stable order
        val s = ordered.indices.minBy { ordered[it].a + ordered[it].b }
        return List(4) { ordered[(s + it) % 4] }
    }

    /** Ring dark, hole and margin light; returns the contrast (light - dark), or null when it is not the sheet. */
    private fun verify(g: IntArray, w: Int, h: Int, hm: DoubleArray): Float? {
        val ringR = (MarkerSheet.OUTER + MarkerSheet.INNER) / 4      // middle of the ring
        val holeR = MarkerSheet.INNER / 2 * 0.6f
        val outR = MarkerSheet.OUTER / 2 + 0.012f
        val ring = squareSamples(ringR, 32).mapNotNull { sample(g, w, h, hm, it) }
        val light = (squareSamples(holeR, 16) + squareSamples(outR, 32)).mapNotNull { sample(g, w, h, hm, it) }
        if (ring.size < 28 || light.size < 40) return null
        val dm = ring.sorted()[ring.size / 2]; val lm = light.sorted()[light.size / 2]
        if (lm - dm < 35f) return null
        val cut = (dm + lm) / 2
        val ok = ring.count { it < cut } + light.count { it > cut }
        return if (ok >= 0.9f * (ring.size + light.size)) lm - dm else null
    }

    private fun squareSamples(r: Float, n: Int): List<P2> = List(n) { k ->
        val t = k * 4f / n; val side = t.toInt(); val f = t - side
        val s = -r + 2 * r * f
        when (side) { 0 -> P2(s, -r); 1 -> P2(r, s); 2 -> P2(-s, r); else -> P2(-r, -s) }
    }

    private fun sample(g: IntArray, w: Int, h: Int, hm: DoubleArray, p: P2): Float? {
        val q = applyH(hm, p.a.toDouble(), p.b.toDouble())
        return bilinear(g, w, h, q.a, q.b)
    }

    private fun bilinear(g: IntArray, w: Int, h: Int, x: Float, y: Float): Float? {
        if (x < 0 || y < 0 || x > w - 1.001f || y > h - 1.001f) return null
        val x0 = x.toInt(); val y0 = y.toInt(); val fx = x - x0; val fy = y - y0
        val i = y0 * w + x0
        return g[i] * (1 - fx) * (1 - fy) + g[i + 1] * fx * (1 - fy) + g[i + w] * (1 - fx) * fy + g[i + w + 1] * fx * fy
    }

    /** Re-fits each of the 8 ring edges on the image gradient and intersects them: sub-pixel corners. */
    private fun refine(g: IntArray, w: Int, h: Int, hm: DoubleArray): List<P2>? {
        val m = MarkerSheet.model
        fun line(a: P2, b: P2): DoubleArray? {
            val pa = applyH(hm, a.a.toDouble(), a.b.toDouble()); val pb = applyH(hm, b.a.toDouble(), b.b.toDouble())
            val len = hypot(pb.a - pa.a, pb.b - pa.b)
            if (len < 12f) return null
            val nx = -(pb.b - pa.b) / len; val ny = (pb.a - pa.a) / len
            val reach = max(3f, min(10f, len / 12f))
            val pts = ArrayList<P2>()
            for (k in 1..23) {
                val t = 0.1f + 0.8f * k / 24f
                val cx = pa.a + (pb.a - pa.a) * t; val cy = pa.b + (pb.b - pa.b) * t
                // strongest step along the normal, with a parabola through the peak for sub-pixel
                var bestS = 0f; var bestG = 0f; var gm = 0f; var gp = 0f
                var s = -reach
                var prevG = 0f
                val gs = ArrayList<Pair<Float, Float>>()
                while (s <= reach) {
                    val v1 = bilinear(g, w, h, cx + nx * (s + 0.5f), cy + ny * (s + 0.5f))
                    val v0 = bilinear(g, w, h, cx + nx * (s - 0.5f), cy + ny * (s - 0.5f))
                    if (v0 != null && v1 != null) gs.add(s to abs(v1 - v0))
                    s += 0.5f
                }
                for (j in 1 until gs.size - 1) if (gs[j].second > bestG) {
                    bestG = gs[j].second; bestS = gs[j].first; gm = gs[j - 1].second; gp = gs[j + 1].second
                }
                prevG = bestG
                if (prevG < 12f) continue
                val den = gm - 2 * bestG + gp
                val off = if (abs(den) > 1e-6f) (0.5f * (gm - gp) / den * 0.5f).coerceIn(-0.5f, 0.5f) else 0f
                pts.add(P2(cx + nx * (bestS + off), cy + ny * (bestS + off)))
            }
            if (pts.size < 8) return null
            return fitLine(pts)
        }
        val lines = ArrayList<DoubleArray>()
        for (ring in 0..1) for (k in 0 until 4) {
            val a = m[ring * 4 + k]; val b = m[ring * 4 + (k + 1) % 4]
            lines.add(line(a, b) ?: return null)
        }
        val out = ArrayList<P2>()
        for (ring in 0..1) for (k in 0 until 4) {
            // corner k sits between edge k-1 (ending at k) and edge k (starting at k)
            val l1 = lines[ring * 4 + (k + 3) % 4]; val l2 = lines[ring * 4 + k]
            out.add(intersect(l1, l2) ?: return null)
        }
        return out
    }

    /** Total least squares line a x + b y = c with a^2 + b^2 = 1. */
    private fun fitLine(p: List<P2>): DoubleArray {
        val mx = p.sumOf { it.a.toDouble() } / p.size; val my = p.sumOf { it.b.toDouble() } / p.size
        var sxx = 0.0; var sxy = 0.0; var syy = 0.0
        for (q in p) { val dx = q.a - mx; val dy = q.b - my; sxx += dx * dx; sxy += dx * dy; syy += dy * dy }
        val ang = 0.5 * atan2(2 * sxy, sxx - syy)            // direction of the line
        val a = -kotlin.math.sin(ang); val b = kotlin.math.cos(ang)
        return doubleArrayOf(a, b, a * mx + b * my)
    }

    private fun intersect(l1: DoubleArray, l2: DoubleArray): P2? {
        val det = l1[0] * l2[1] - l1[1] * l2[0]
        if (abs(det) < 1e-9) return null
        return P2(((l1[2] * l2[1] - l1[1] * l2[2]) / det).toFloat(), ((l1[0] * l2[2] - l1[2] * l2[0]) / det).toFloat())
    }

    private fun d2(a: P2, b: P2) = (a.a - b.a) * (a.a - b.a) + (a.b - b.b) * (a.b - b.b)
    private fun signedArea(q: List<P2>): Float {
        var s = 0f
        for (i in q.indices) { val a = q[i]; val b = q[(i + 1) % q.size]; s += a.a * b.b - b.a * a.b }
        return s / 2
    }
    private fun polyArea(q: List<P2>) = abs(signedArea(q))

    @Suppress("unused")
    private fun len(a: P2, b: P2) = sqrt(d2(a, b))
}
