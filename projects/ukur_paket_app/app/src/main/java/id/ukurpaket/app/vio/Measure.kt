package id.ukurpaket.app.vio

import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.convexHull
import id.ukurpaket.app.measure.inside
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/** A picture-sized yes/no mask. */
class Bits(val w: Int, val h: Int, val b: BooleanArray) {
    operator fun get(x: Int, y: Int) = x in 0 until w && y in 0 until h && b[y * w + x]
    fun erode(): Bits = Bits(w, h, BooleanArray(w * h) { i -> val x = i % w; val y = i / w; get(x, y) && get(x - 1, y) && get(x + 1, y) && get(x, y - 1) && get(x, y + 1) })
    fun half(): Bits = Bits(w / 2, h / 2, BooleanArray((w / 2) * (h / 2)) { i -> val x = 2 * (i % (w / 2)); val y = 2 * (i / (w / 2)); get(x, y) && get(x + 1, y + 1) })
}

/** Support plane n.x + d = 0 (n up). */
class Plane(val n: DoubleArray, val d: Double) {
    fun height(p: DoubleArray) = n[0] * p[0] + n[1] * p[1] + n[2] * p[2] + d
}

object Measure {
    /** RANSAC: the plane with most points within 6 mm, normal within 12 deg of up. */
    fun supportPlane(p: List<DoubleArray>, seed: Long = 7): Plane? {
        if (p.size < 20) return null
        val rnd = java.util.Random(seed)
        var best = 0; var bp: Plane? = null
        val cosMax = cos(Math.toRadians(12.0))
        repeat(600) {
            val a = p[rnd.nextInt(p.size)]; val b = p[rnd.nextInt(p.size)]; val c = p[rnd.nextInt(p.size)]
            val u = DoubleArray(3) { b[it] - a[it] }; val v = DoubleArray(3) { c[it] - a[it] }
            var n = doubleArrayOf(u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            val nn = sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]); if (nn < 1e-12) return@repeat
            n = DoubleArray(3) { n[it] / nn }
            if (abs(n[2]) < cosMax) return@repeat
            if (n[2] < 0) n = DoubleArray(3) { -n[it] }
            val d = -(n[0] * a[0] + n[1] * a[1] + n[2] * a[2])
            var cnt = 0
            for (q in p) if (abs(n[0] * q[0] + n[1] * q[1] + n[2] * q[2] + d) < 0.006) cnt++
            if (cnt > best) { best = cnt; bp = Plane(n, d) }
        }
        // refine on its inliers (least squares normal through the centroid)
        val pl = bp ?: return null
        val inl = p.filter { abs(pl.height(it)) < 0.006 }
        if (inl.size < 10) return pl
        val c = DoubleArray(3); for (q in inl) for (i in 0 until 3) c[i] += q[i] / inl.size
        val cov = DoubleArray(9)
        for (q in inl) for (i in 0 until 3) for (j in 0 until 3) cov[3 * i + j] += (q[i] - c[i]) * (q[j] - c[j])
        val n = smallestVec3(cov).let { if (it[2] < 0) DoubleArray(3) { i -> -it[i] } else it }
        return Plane(n, -(n[0] * c[0] + n[1] * c[1] + n[2] * c[2]))
    }

    private fun smallestVec3(a: DoubleArray): DoubleArray {
        val l = M3.symEig(a)[0]
        val m = DoubleArray(9) { a[it] - if (it % 4 == 0) l else 0.0 }
        // the null vector of (A - l I): largest cross product of two rows
        val r0 = doubleArrayOf(m[0], m[1], m[2]); val r1 = doubleArrayOf(m[3], m[4], m[5]); val r2 = doubleArrayOf(m[6], m[7], m[8])
        val cands = listOf(cross(r0, r1), cross(r0, r2), cross(r1, r2))
        val v = cands.maxByOrNull { it[0] * it[0] + it[1] * it[1] + it[2] * it[2] }!!
        val n = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
        return DoubleArray(3) { v[it] / n }
    }

    fun cross(a: DoubleArray, b: DoubleArray) = doubleArrayOf(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

    /** Points joined (3D grid of [cell]) to any of [seeds]; returns the indices kept. */
    fun grow(p: List<DoubleArray>, seeds: List<DoubleArray>, cell: Double): List<Int> {
        fun key(q: DoubleArray) = Triple(floor(q[0] / cell).toInt(), floor(q[1] / cell).toInt(), floor(q[2] / cell).toInt())
        val cells = HashMap<Triple<Int, Int, Int>, MutableList<Int>>()
        for ((i, q) in p.withIndex()) cells.getOrPut(key(q)) { ArrayList() }.add(i)
        val seen = HashSet<Triple<Int, Int, Int>>(); val stack = ArrayList<Triple<Int, Int, Int>>()
        for (s in seeds) { val k = key(s); if (cells.containsKey(k) && seen.add(k)) stack.add(k) }
        val out = ArrayList<Int>()
        while (stack.isNotEmpty()) {
            val k = stack.removeAt(stack.size - 1); out.addAll(cells[k]!!)
            for (dx in -1..1) for (dy in -1..1) for (dz in -1..1) {
                val nb = Triple(k.first + dx, k.second + dy, k.third + dz)
                if (cells.containsKey(nb) && seen.add(nb)) stack.add(nb)
            }
        }
        return out
    }

    /** Statistical outlier removal: drop points whose mean distance to their k nearest neighbours is unusual. */
    fun removeOutliers(p: List<DoubleArray>, k: Int = 6, z: Double = 2.5): List<DoubleArray> {
        if (p.size <= k + 2) return p
        val m = DoubleArray(p.size)
        val best = DoubleArray(k)
        for (i in p.indices) {
            java.util.Arrays.fill(best, Double.MAX_VALUE)
            val a = p[i]
            for (j in p.indices) {
                if (i == j) continue
                val b = p[j]; val d = (a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]) + (a[2] - b[2]) * (a[2] - b[2])
                if (d < best[k - 1]) { var t = k - 1; while (t > 0 && best[t - 1] > d) { best[t] = best[t - 1]; t-- }; best[t] = d }
            }
            var s = 0.0; for (v in best) s += sqrt(v); m[i] = s / k
        }
        val sorted = m.sorted(); val med = sorted[m.size / 2]
        val mad = m.map { abs(it - med) }.sorted()[m.size / 2] + 1e-9
        return p.filterIndexed { i, _ -> m[i] < med + z * 1.4826 * mad }
    }

    class Box(val l: Double, val w: Double, val h: Double, val corners: List<DoubleArray>)

    /**
     * Smallest box round points given in the plane's frame (z = height): the angle (0,5 deg steps) whose trimmed
     * ([trim] % off each side) footprint extents have the least area; height the (100 - trim)th percentile.
     */
    fun box(p: List<DoubleArray>, trim: Double = 1.5): Box {
        var best = Double.MAX_VALUE; var ba = 0.0; var bl = DoubleArray(2); var bh = DoubleArray(2)
        val u = DoubleArray(p.size); val v = DoubleArray(p.size)
        var ang = 0.0
        while (ang < 90.0) {
            val a = Math.toRadians(ang); val c = cos(a); val s = sin(a)
            for (i in p.indices) { u[i] = p[i][0] * c + p[i][1] * s; v[i] = -p[i][0] * s + p[i][1] * c }
            val lo0 = pct(u, trim); val hi0 = pct(u, 100 - trim); val lo1 = pct(v, trim); val hi1 = pct(v, 100 - trim)
            val area = (hi0 - lo0) * (hi1 - lo1)
            if (area < best) { best = area; ba = a; bl = doubleArrayOf(lo0, lo1); bh = doubleArrayOf(hi0, hi1) }
            ang += 0.5
        }
        val hz = pct(DoubleArray(p.size) { p[it][2] }, 100 - trim)
        val c = cos(ba); val s = sin(ba)
        fun back(a: Double, b: Double) = doubleArrayOf(a * c - b * s, a * s + b * c, 0.0)
        val corners = listOf(back(bl[0], bl[1]), back(bh[0], bl[1]), back(bh[0], bh[1]), back(bl[0], bh[1]))
        val e0 = bh[0] - bl[0]; val e1 = bh[1] - bl[1]
        return Box(max(e0, e1), min(e0, e1), hz, corners)
    }

    fun pct(a: DoubleArray, q: Double): Double {
        val s = a.sortedArray(); if (s.isEmpty()) return 0.0
        val pos = (q / 100.0) * (s.size - 1); val i = pos.toInt(); val f = pos - i
        return if (i + 1 < s.size) s[i] * (1 - f) + s[i + 1] * f else s[i]
    }

    /**
     * Plane-sweep depth on the reference frame [ref] (grey, picture coordinates), from its [nbs] neighbours, inside
     * [roi]: fronto-parallel planes between [zMin] and [zMax] (inverse-depth steps), ZNCC over 7 x 7 averaged over the
     * neighbours; a pixel counts when the best score is over [minScore] with at least two neighbours seeing it.
     * Returns world points.
     */
    fun planeSweep(ref: Gray, refCam: Cam, nbs: List<Pair<Gray, Cam>>, cam: Intrinsics, roi: Bits, zMin: Double, zMax: Double,
                   planes: Int = 64, minScore: Float = 0.7f, pool: Par = Par.default): List<DoubleArray> {
        val w = ref.w; val h = ref.h
        var x0 = w; var y0 = h; var x1 = -1; var y1 = -1
        for (y in 0 until h) for (x in 0 until w) if (roi[x, y]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y }
        if (x1 < 0) return emptyList()
        val r = 3
        x0 = max(r + 1, x0 - r); y0 = max(r + 1, y0 - r); x1 = min(w - r - 2, x1 + r); y1 = min(h - r - 2, y1 + r)
        val bw = x1 - x0 + 1; val bh = y1 - y0 + 1
        if (bw < 8 || bh < 8) return emptyList()
        val refP = FloatArray(bw * bh) { ref.p[(y0 + it / bw) * w + x0 + it % bw] }
        val iw = bw + 1
        val sr = integral(refP, bw, bh); val srr = integral(FloatArray(bw * bh) { refP[it] * refP[it] }, bw, bh)
        val rcwRef = refCam.r
        // the planes in groups, one group per core; each keeps its own best depth, merged at the end
        val groups = (0 until planes).toList().let { all -> all.chunked(max(1, (all.size + pool.threads - 1) / pool.threads)) }
        val parts = pool.map(groups) { group ->
            val best = FloatArray(bw * bh) { -2f }; val bestZ = FloatArray(bw * bh)
            val warped = FloatArray(bw * bh); val valid = BooleanArray(bw * bh)
            val accS = FloatArray(bw * bh); val accN = IntArray(bw * bh)
            for (pi in group) {
                val inv = 1 / zMax + (1 / zMin - 1 / zMax) * pi / (planes - 1)
                val z = 1 / inv
                java.util.Arrays.fill(accS, 0f); java.util.Arrays.fill(accN, 0)
                for ((img, nc) in nbs) {
                    // homography of the plane z_ref = z: x_n ~ K (R_nr + t_nr n^T / z) K^-1 x_r
                    val rnr = M3.mul(M3.t(nc.r), rcwRef)
                    val tnr = M3.mtv(nc.r, doubleArrayOf(refCam.c[0] - nc.c[0], refCam.c[1] - nc.c[1], refCam.c[2] - nc.c[2]))
                    val hm = DoubleArray(9)
                    for (i in 0 until 3) for (j in 0 until 3) hm[3 * i + j] = rnr[3 * i + j] + if (j == 2) tnr[i] / z else 0.0
                    // in pixels: K H K^-1
                    val k = doubleArrayOf(cam.f, 0.0, cam.cx, 0.0, cam.f, cam.cy, 0.0, 0.0, 1.0)
                    val ki = doubleArrayOf(1 / cam.f, 0.0, -cam.cx / cam.f, 0.0, 1 / cam.f, -cam.cy / cam.f, 0.0, 0.0, 1.0)
                    val hp = M3.mul(k, M3.mul(hm, ki))
                    for (yy in 0 until bh) for (xx in 0 until bw) {
                        val px = (x0 + xx).toDouble(); val py = (y0 + yy).toDouble()
                        val q = hp[6] * px + hp[7] * py + hp[8]
                        val u = (hp[0] * px + hp[1] * py + hp[2]) / q; val v = (hp[3] * px + hp[4] * py + hp[5]) / q
                        val i = yy * bw + xx
                        if (q > 0 && u >= 0 && v >= 0 && u < img.w - 1 && v < img.h - 1) { warped[i] = img.at(u.toFloat(), v.toFloat()); valid[i] = true }
                        else { warped[i] = 0f; valid[i] = false }
                    }
                    val sw = integral(warped, bw, bh); val sww = integral(FloatArray(bw * bh) { warped[it] * warped[it] }, bw, bh)
                    val srw = integral(FloatArray(bw * bh) { refP[it] * warped[it] }, bw, bh)
                    val n = ((2 * r + 1) * (2 * r + 1)).toFloat()
                    for (yy in r until bh - r) for (xx in r until bw - r) {
                        val i = yy * bw + xx
                        if (!valid[i] || !roi[x0 + xx, y0 + yy]) continue
                        val a = boxSum(sr, iw, xx, yy, r) / n; val b = boxSum(sw, iw, xx, yy, r) / n
                        val vr = boxSum(srr, iw, xx, yy, r) / n - a * a; val vw = boxSum(sww, iw, xx, yy, r) / n - b * b
                        if (vr < 1f || vw < 1f) continue
                        val cv = boxSum(srw, iw, xx, yy, r) / n - a * b
                        accS[i] += (cv / sqrt(vr * vw)); accN[i]++
                    }
                }
                for (i in 0 until bw * bh) if (accN[i] >= 2) { val sc = accS[i] / accN[i]; if (sc > best[i]) { best[i] = sc; bestZ[i] = z.toFloat() } }
            }
            best to bestZ
        }
        val best = FloatArray(bw * bh) { -2f }; val bestZ = FloatArray(bw * bh)
        // ties go to the earlier plane group, as in one pass over the planes in order
        for ((b, z) in parts) for (i in best.indices) if (b[i] > best[i]) { best[i] = b[i]; bestZ[i] = z[i] }
        val out = ArrayList<DoubleArray>()
        for (yy in r until bh - r) for (xx in r until bw - r) {
            val i = yy * bw + xx
            if (best[i] < minScore || !roi[x0 + xx, y0 + yy]) continue
            val z = bestZ[i].toDouble()
            val xc = doubleArrayOf(((x0 + xx) - cam.cx) / cam.f * z, ((y0 + yy) - cam.cy) / cam.f * z, z)
            val wv = M3.mv(rcwRef, xc)
            out.add(doubleArrayOf(wv[0] + refCam.c[0], wv[1] + refCam.c[1], wv[2] + refCam.c[2]))
        }
        return out
    }

    private fun integral(a: FloatArray, w: Int, h: Int): FloatArray {
        val iw = w + 1; val s = FloatArray(iw * (h + 1))
        for (y in 0 until h) { var row = 0f; for (x in 0 until w) { row += a[y * w + x]; s[(y + 1) * iw + x + 1] = s[y * iw + x + 1] + row } }
        return s
    }

    private fun boxSum(s: FloatArray, iw: Int, x: Int, y: Int, r: Int) =
        s[(y + r + 1) * iw + x + r + 1] - s[(y - r) * iw + x + r + 1] - s[(y + r + 1) * iw + x - r] + s[(y - r) * iw + x - r]

    /** Convex hull of 2D points (picture coordinates) as polygon; empty under 3 points. */
    fun hull2(pts: List<FloatArray>): List<P2> = if (pts.size < 3) emptyList() else convexHull(pts.map { P2(it[0], it[1]) })

    fun inPoly(poly: List<P2>, x: Float, y: Float) = poly.size >= 3 && inside(poly, x, y)
}
