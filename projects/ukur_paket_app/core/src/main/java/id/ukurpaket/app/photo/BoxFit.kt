package id.ukurpaket.app.photo

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.measure.convexHull
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/*
 * Fitting a box to the object's silhouette (0.4.3): analysis by synthesis. A box standing on the floor has six unknowns
 * once the camera height, the lens and 'up' are known: where it stands (2), which way it is turned (1), and its length,
 * width and height (3). The box is drawn into the picture (the convex hull of its 8 projected corners is exactly its
 * silhouette) and the six numbers are moved until that silhouette matches the object's mask best (intersection over
 * union). Unlike reading the outline's corners one by one, every pixel of the outline votes: a strip of tape sticking
 * out, a shadow cut in with the box, a bulging side or a rounded corner moves the answer by its area, not by its reach.
 */

/** The mask, prepared so that the IoU of any convex polygon with it costs one pass over the polygon's rows. */
class Silhouette(private val mask: Mask) {
    private val w = mask.w
    private val h = mask.h
    /** Per row, the number of mask pixels left of each column (w + 1 entries per row). */
    private val prefix = IntArray(h * (w + 1)).also { p ->
        for (y in 0 until h) {
            var s = 0; val o = y * (w + 1)
            for (x in 0 until w) { p[o + x] = s; if (mask.bits[y * w + x]) s++ }
            p[o + w] = s
        }
    }
    val area = (0 until h).sumOf { prefix[it * (w + 1) + w] }

    /** Mask pixels in row [y] between x = [a] and [b] (continuous: a pixel partly covered counts partly). */
    private fun rowCount(y: Int, a: Float, b: Float): Float {
        fun at(x: Float): Float {
            if (x <= 0f) return 0f
            if (x >= w) return prefix[y * (w + 1) + w].toFloat()
            val i = x.toInt(); val f = x - i
            return prefix[y * (w + 1) + i] + if (mask.bits[y * w + i]) f else 0f
        }
        return at(b) - at(a)
    }

    /**
     * IoU of the convex polygon [poly] (picture pixels) with the mask. The polygon's area outside the picture counts
     * against it (nothing of the object is assumed beyond the picture's edge), so a box cannot grow there for free.
     */
    fun iou(poly: List<P2>): Float {
        val (inter, polyArea) = overlap(poly) ?: return 0f
        val union = polyArea + area - inter
        return if (union <= 0f) 0f else (inter / union).coerceIn(0f, 1f)
    }

    /** Share of the mask inside [poly] (1 = the polygon covers the whole object). */
    fun coverage(poly: List<P2>): Float = overlap(poly)?.let { it.first / area } ?: 0f

    /** Mask pixels inside [poly], and [poly]'s whole area (outside the picture too); null for no polygon. */
    fun overlap(poly: List<P2>): Pair<Float, Float>? {
        if (poly.size < 3 || area == 0) return null
        var a2 = 0f
        for (i in poly.indices) { val p = poly[i]; val q = poly[(i + 1) % poly.size]; a2 += p.a * q.b - q.a * p.b }
        val polyArea = abs(a2) / 2
        val y0 = max(0, floor(poly.minOf { it.b }).toInt()); val y1 = min(h - 1, ceil(poly.maxOf { it.b }).toInt())
        var inter = 0f
        for (y in y0..y1) {
            val cy = y + 0.5f
            var xa = Float.MAX_VALUE; var xb = -Float.MAX_VALUE
            for (i in poly.indices) {
                val p = poly[i]; val q = poly[(i + 1) % poly.size]
                if ((p.b <= cy && q.b > cy) || (q.b <= cy && p.b > cy)) {
                    val x = p.a + (cy - p.b) / (q.b - p.b) * (q.a - p.a)
                    if (x < xa) xa = x; if (x > xb) xb = x
                }
            }
            if (xa < xb) inter += rowCount(y, xa, xb)
        }
        return inter to polyArea
    }
}

/**
 * A box on the floor in the floor's own axes: centre ([u], [v]) metres along [ax], [ay] from the point under the
 * camera, turned [yaw] radians, [l] x [w] footprint, [hgt] tall.
 */
class FloorBox(val u: Float, val v: Float, val yaw: Float, val l: Float, val w: Float, val hgt: Float) {
    /** The 8 corners in camera axes (floor 0-3, top 4-7), the floor being `up . X = -hM`. */
    fun corners(ax: V3, ay: V3, up: V3, hM: Float): List<V3> {
        val c = cos(yaw); val s = sin(yaw)
        val origin = up * -hM
        val foot = listOf(-1f to -1f, 1f to -1f, 1f to 1f, -1f to 1f).map { (i, j) ->
            val a = u + c * i * l / 2 - s * j * w / 2; val b = v + s * i * l / 2 + c * j * w / 2
            origin + ax * a + ay * b
        }
        return foot + foot.map { it + up * hgt }
    }

    companion object {
        /** The box whose floor rectangle has the corners [foot] (in order round it, camera axes) and height [hgt]. */
        fun of(foot: List<V3>, hgt: Float, ax: V3, ay: V3, up: V3, hM: Float): FloorBox {
            val origin = up * -hM
            val q = foot.map { val d = it - origin; P2(d dot ax, d dot ay) }
            val e1 = P2(q[1].a - q[0].a, q[1].b - q[0].b); val e2 = P2(q[2].a - q[1].a, q[2].b - q[1].b)
            return FloorBox(q.map { it.a }.average().toFloat(), q.map { it.b }.average().toFloat(), atan2(e1.b, e1.a),
                hypot(e1.a, e1.b), hypot(e2.a, e2.b), hgt)
        }
    }
}

object BoxFit {
    /** Silhouette (picture pixels) of the box: hull of its projected corners; empty when a corner is behind the camera. */
    fun silhouette(corners: List<V3>, k: Intrinsics): List<P2> =
        if (corners.any { it.z < 0.03f }) emptyList() else convexHull(corners.map { k.project(it) })

    /**
     * The box nearest [start] whose silhouette fits [sil] best. [fixH]: the height is known (kept). Returns the box
     * and its IoU.
     */
    fun refine(start: FloorBox, sil: Silhouette, k: Intrinsics, up: V3, hM: Float, ax: V3, ay: V3, fixH: Float? = null): Pair<FloorBox, Float> {
        val size = max(max(start.l, start.w), start.hgt).coerceAtLeast(0.02f)
        fun box(p: DoubleArray) = FloorBox(p[0].toFloat(), p[1].toFloat(), p[2].toFloat(), p[3].toFloat(), p[4].toFloat(), fixH ?: p[5].toFloat())
        fun cost(p: DoubleArray): Double {
            val b = box(p)
            if (b.l < 0.005f || b.w < 0.005f || b.hgt < 0.003f || b.hgt > 3 * hM) return 2.0
            val poly = silhouette(b.corners(ax, ay, up, hM), k)
            if (poly.size < 3) return 2.0
            return 1.0 - sil.iou(poly)
        }
        // several starts (the height halved and doubled, the box turned a quarter): one view leaves shallow valleys
        // between a taller box and a deeper one, and a single descent can settle in the wrong one
        val seeds = ArrayList<FloorBox>()
        seeds += start
        if (fixH == null) { seeds += FloorBox(start.u, start.v, start.yaw, start.l, start.w, start.hgt * 0.5f); seeds += FloorBox(start.u, start.v, start.yaw, start.l, start.w, start.hgt * 2f) }
        seeds += FloorBox(start.u, start.v, start.yaw + (Math.PI / 2).toFloat(), start.w, start.l, start.hgt)
        fun steps(sd: DoubleArray) = doubleArrayOf(0.06 * size, 0.06 * size, 0.08, 0.06 * sd[3], 0.06 * sd[4], 0.12 * sd[5] + 0.01 * size)
            .also { if (fixH != null) it[5] = 0.0 }
        // one descent from each start, then two restarts with a smaller simplex from the best (Nelder-Mead stalls on a
        // flat stretch otherwise)
        var bestX: DoubleArray? = null; var bestC = Double.MAX_VALUE
        for (sd in seeds) {
            val x0 = doubleArrayOf(sd.u.toDouble(), sd.v.toDouble(), sd.yaw.toDouble(), sd.l.toDouble(), sd.w.toDouble(), sd.hgt.toDouble())
            val x = nelderMead(::cost, x0, steps(x0), 240)
            val c = cost(x)
            if (c < bestC) { bestC = c; bestX = x }
        }
        var x = bestX!!
        val st = steps(x)
        for (round in 1 until 3) x = nelderMead(::cost, x, DoubleArray(6) { st[it] / (1 shl round) }, 240)
        return box(x) to (1.0 - cost(x)).toFloat().coerceAtLeast(0f)
    }

    /**
     * The smallest box (by its area in the picture) round [start] that still covers 98,5 % of the object: the outer
     * box of something that is not a box (a gallon, a sack, a plant), which is what its volumetric weight is charged
     * on. The box fitted by IoU sits inside such an object's bulges; this one encloses them. Returns the box and its IoU.
     */
    fun cover(start: FloorBox, sil: Silhouette, k: Intrinsics, up: V3, hM: Float, ax: V3, ay: V3): Pair<FloorBox, Float> {
        val size = max(max(start.l, start.w), start.hgt).coerceAtLeast(0.02f)
        fun box(p: DoubleArray) = FloorBox(p[0].toFloat(), p[1].toFloat(), p[2].toFloat(), p[3].toFloat(), p[4].toFloat(), p[5].toFloat())
        fun cost(p: DoubleArray): Double {
            val b = box(p)
            if (b.l < 0.005f || b.w < 0.005f || b.hgt < 0.003f || b.hgt > 3 * hM) return 1e3
            val (inter, polyArea) = sil.overlap(silhouette(b.corners(ax, ay, up, hM), k)) ?: return 1e3
            return (polyArea / sil.area).toDouble() + 40.0 * max(0.0, COVER - inter.toDouble() / sil.area)
        }
        // start a little larger than the IoU box, so that the search begins covering
        var x = doubleArrayOf(start.u.toDouble(), start.v.toDouble(), start.yaw.toDouble(), start.l * 1.1, start.w * 1.1, start.hgt * 1.1)
        val step = doubleArrayOf(0.04 * size, 0.04 * size, 0.05, 0.05 * start.l, 0.05 * start.w, 0.08 * start.hgt + 0.01 * size)
        for (round in 0 until 3) x = nelderMead(::cost, x, DoubleArray(6) { step[it] / (1 shl round) }, 260)
        val b = box(x)
        return b to sil.iou(silhouette(b.corners(ax, ay, up, hM), k))
    }

    /** Share of the object the outer box must cover. */
    const val COVER = 0.985

    /** Silhouette of a standing cylinder (centre [u], [v] on the floor, radius [r], [hgt] tall): hull of its two rims. */
    fun cylinderSilhouette(u: Float, v: Float, r: Float, hgt: Float, ax: V3, ay: V3, up: V3, hM: Float, k: Intrinsics): List<P2> {
        val origin = up * -hM
        val rim = ArrayList<V3>(2 * RIM)
        for (i in 0 until RIM) {
            val t = 2 * Math.PI * i / RIM
            val p = origin + ax * (u + r * cos(t).toFloat()) + ay * (v + r * sin(t).toFloat())
            rim += p; rim += p + up * hgt
        }
        return silhouette(rim, k)
    }
    private const val RIM = 32

    /**
     * The standing cylinder (gallon, bottle, bucket, roll) whose silhouette fits [sil] best, started from the box
     * [start]. Returns its outer box (2r x 2r x height, turned as [start]) and its IoU. A box's straight sides and
     * corners never fit a cylinder's round ends and the other way round, so the better fit tells the shape; and a
     * round object's outer box is not the box fitted to it (that one sits inside its bulges, turned 45 deg).
     */
    fun cylinder(start: FloorBox, sil: Silhouette, k: Intrinsics, up: V3, hM: Float, ax: V3, ay: V3): Pair<FloorBox, Float> {
        val size = max(max(start.l, start.w), start.hgt).coerceAtLeast(0.02f)
        fun cost(p: DoubleArray): Double {
            val r = p[2].toFloat(); val hh = p[3].toFloat()
            if (r < 0.004f || hh < 0.003f || hh > 3 * hM) return 2.0
            val poly = cylinderSilhouette(p[0].toFloat(), p[1].toFloat(), r, hh, ax, ay, up, hM, k)
            if (poly.size < 3) return 2.0
            return 1.0 - sil.iou(poly)
        }
        var x = doubleArrayOf(start.u.toDouble(), start.v.toDouble(), (start.l + start.w) / 4.0 * 1.15, start.hgt.toDouble())
        val step = doubleArrayOf(0.06 * size, 0.06 * size, 0.08 * x[2], 0.1 * start.hgt + 0.01 * size)
        for (round in 0 until 3) x = nelderMead(::cost, x, DoubleArray(4) { step[it] / (1 shl round) }, 200)
        val d = 2 * x[2].toFloat()
        return FloorBox(x[0].toFloat(), x[1].toFloat(), start.yaw, d, d, x[3].toFloat()) to (1.0 - cost(x)).toFloat().coerceAtLeast(0f)
    }

    /** Minimises [f] from [x0]; [step] sets the starting simplex (a zero step leaves that coordinate fixed). */
    fun nelderMead(f: (DoubleArray) -> Double, x0: DoubleArray, step: DoubleArray, iterations: Int): DoubleArray {
        val free = x0.indices.filter { step[it] != 0.0 }
        val n = free.size
        if (n == 0) return x0
        val pts = Array(n + 1) { x0.copyOf() }
        for ((j, i) in free.withIndex()) pts[j + 1][i] += step[i]
        val v = DoubleArray(n + 1) { f(pts[it]) }
        fun combine(a: DoubleArray, b: DoubleArray, t: Double) = DoubleArray(a.size) { a[it] + t * (b[it] - a[it]) }
        repeat(iterations) {
            val order = (0..n).sortedBy { v[it] }
            val best = order[0]; val worst = order[n]; val second = order[n - 1]
            if (abs(v[worst] - v[best]) < 1e-7) return pts[best]
            val centroid = DoubleArray(x0.size)
            for (i in 0..n) if (i != worst) for (d in centroid.indices) centroid[d] += pts[i][d] / n
            val r = combine(centroid, pts[worst], -1.0); val fr = f(r)
            when {
                fr < v[best] -> {
                    val e = combine(centroid, pts[worst], -2.0); val fe = f(e)
                    if (fe < fr) { pts[worst] = e; v[worst] = fe } else { pts[worst] = r; v[worst] = fr }
                }
                fr < v[second] -> { pts[worst] = r; v[worst] = fr }
                else -> {
                    val c = if (fr < v[worst]) combine(centroid, r, 0.5) else combine(centroid, pts[worst], 0.5)
                    val fc = f(c)
                    if (fc < min(fr, v[worst])) { pts[worst] = c; v[worst] = fc }
                    else for (i in 0..n) if (i != best) { pts[i] = combine(pts[best], pts[i], 0.5); v[i] = f(pts[i]) }
                }
            }
        }
        return pts[(0..n).minBy { v[it] }]
    }
}
