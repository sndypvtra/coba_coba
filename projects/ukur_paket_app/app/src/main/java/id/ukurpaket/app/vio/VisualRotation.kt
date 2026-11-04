package id.ukurpaket.app.vio

import java.util.Random
import java.util.concurrent.Callable
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * The camera's rotation on every frame from the picture alone: the stand-in for the gyroscope and the rotation
 * vector when a phone sends neither (the Urovo DT50 lists a gyroscope but delivers no events from it).
 *
 *  1. relative rotation for many frame pairs (i, i+1), (i, i+2), (i, i+4), (i, i+8) from the tracked points:
 *     the essential matrix (normalised 8-point, RANSAC on the Sampson error, refitted on the inliers), its rotation
 *     chosen by points in front of both cameras; a pair whose points fit a pure turn as well uses that turn (Kabsch);
 *  2. rotation averaging: the frame rotations that agree best with all pairs (Gauss-Newton on the rotation tangent
 *     space, Huber-weighted, frame 0 fixed), so errors of single pairs do not add up along the sweep;
 *  3. the bundle adjustment then refines them with the points (a looser prior than for sensor rotations).
 *
 * Returns world <- camera rotations (world = the first frame's camera), or null when too few pairs were found.
 */
object VisualRotation {
    class Pair3(val i: Int, val j: Int, val r: DoubleArray, val w: Double)      // r: camera i -> camera j (x_j = r x_i + t)

    /** Rotations per frame; [measured]: false where a frame had no usable pair and its rotation is interpolated. */
    class Result(val rot: Array<DoubleArray>, val measured: BooleanArray) { val measuredCount get() = measured.count { it } }

    fun estimate(obs: List<PointObs>, n: Int, cam: Intrinsics, pool: Par = Par.default): Array<DoubleArray>? = solve(obs, n, cam, pool)?.rot

    /**
     * As [estimate], tolerant of bad frames (blur, a hand over the lens, a hole in the recording): a frame without a
     * pair is skipped and its rotation interpolated from its neighbours; it fails only when fewer than 60 % of the
     * frames are measured. Pairs that fail at 1,5 px are tried again at 3 px (blurred, dim frames).
     */
    fun solve(obs: List<PointObs>, n: Int, cam: Intrinsics, pool: Par = Par.default, trace: ((String) -> Unit)? = null): Result? {
        if (n < 2) return null
        // bearings per frame: point id -> normalised (x, y)
        val byFrame = Array(n) { HashMap<Int, DoubleArray>() }
        for (p in obs) for (j in p.k.indices) {
            val k = p.k[j]; if (k in 0 until n) byFrame[k][p.id] = doubleArrayOf((p.u[j] - cam.cx) / cam.f, (p.v[j] - cam.cy) / cam.f)
        }
        val jobs = ArrayList<IntArray>()
        for (i in 0 until n) for (d in intArrayOf(1, 2, 3, 4, 6, 8, 12)) if (i + d < n) jobs.add(intArrayOf(i, i + d))
        val tol = 1.5 / cam.f
        val pairs = pool.map(jobs) { (i, j) ->
            (relative(byFrame[i], byFrame[j], tol, 1000L * i + j) ?: relative(byFrame[i], byFrame[j], 2 * tol, 7000L * i + j, minIds = 12, minIn = 10))
                ?.let { Pair3(i, j, it.first, it.second.toDouble()) }
        }.filterNotNull()
        if (pairs.isEmpty()) return null
        // the reference: frame 0 when it has pairs, else the frame with the most
        val wByFrame = DoubleArray(n); for (p in pairs) { wByFrame[p.i] += p.w; wByFrame[p.j] += p.w }
        val ref = if (wByFrame[0] > 0) 0 else wByFrame.indices.maxBy { wByFrame[it] }
        // spread from the reference over the pairs, strongest first, both ways (x_j = r x_i: R_j = R_i r^T, R_i = R_j r)
        val rot = arrayOfNulls<DoubleArray>(n); rot[ref] = M3.eye()
        val ordered = pairs.sortedByDescending { it.w / (it.j - it.i) }
        var changed = true
        while (changed) {
            changed = false
            for (p in ordered) {
                val ri = rot[p.i]; val rj = rot[p.j]
                if (ri != null && rj == null) { rot[p.j] = M3.mul(ri, M3.t(p.r)); changed = true }
                else if (rj != null && ri == null) { rot[p.i] = M3.mul(rj, p.r); changed = true }
            }
        }
        val measured = BooleanArray(n) { rot[it] != null }
        trace?.invoke("visual: ${pairs.size} pairs of ${jobs.size}, reached ${measured.count { it }} of $n frames from $ref; " +
            "points per frame ${byFrame.map { it.size }}")
        if (measured.count { it } < 0.6 * n) return null
        // the rest from their neighbours: interpolated between the nearest measured frames (copied at the ends)
        for (k in 0 until n) if (rot[k] == null) {
            val a = (k - 1 downTo 0).firstOrNull { measured[it] }; val b = (k + 1 until n).firstOrNull { measured[it] }
            rot[k] = when {
                a != null && b != null -> {
                    val d = M3.log(M3.mul(M3.t(rot[a]!!), rot[b]!!)); val t = (k - a).toDouble() / (b - a)
                    M3.mul(rot[a]!!, M3.exp(d[0] * t, d[1] * t, d[2] * t))
                }
                a != null -> rot[a]!!.copyOf()
                else -> rot[b!!]!!.copyOf()
            }
        }
        val r = Array(n) { rot[it]!! }
        average(r, pairs.filter { measured[it.i] && measured[it.j] }, ref)
        // frame 0's camera as the world, as before
        val r0t = M3.t(r[0])
        return Result(Array(n) { M3.mul(r0t, r[it]) }, measured)
    }

    /** Gauss-Newton on R_k <- R_k exp(d_k): residual log(R_ij^T R_j^T R_i), d/dd_i = I, d/dd_j = -R_i^T R_j. */
    private fun average(r: Array<DoubleArray>, pairs: List<Pair3>, ref: Int = 0, iters: Int = 6) {
        val n = r.size; val m = 3 * (n - 1)
        if (m == 0) return
        fun ix(k: Int) = if (k == ref) -1 else if (k < ref) k else k - 1
        for (it in 0 until iters) {
            val h = DoubleArray(m * m); val g = DoubleArray(m)
            var moved = 0.0
            for (p in pairs) {
                val e = M3.log(M3.mul(M3.t(p.r), M3.mul(M3.t(r[p.j]), r[p.i])))
                val ang = sqrt(e[0] * e[0] + e[1] * e[1] + e[2] * e[2])
                val k = Math.toRadians(0.5)                                     // Huber at 0,5°
                val w = p.w * (if (ang < k) 1.0 else k / ang)
                val jj = M3.mul(M3.t(r[p.i]), r[p.j]).map { -it }.toDoubleArray()  // d/dd_j
                val ii = ix(p.i); val ij = ix(p.j)
                // blocks: J_i = I, J_j = jj
                fun addBlock(a: Int, ja: DoubleArray?, b: Int, jb: DoubleArray?) {
                    for (x in 0 until 3) for (y in 0 until 3) {
                        var s = 0.0
                        for (z in 0 until 3) s += (ja?.get(3 * z + x) ?: if (z == x) 1.0 else 0.0) * (jb?.get(3 * z + y) ?: if (z == y) 1.0 else 0.0)
                        h[(3 * a + x) * m + 3 * b + y] += w * s
                    }
                }
                if (ii >= 0) { addBlock(ii, null, ii, null); for (x in 0 until 3) g[3 * ii + x] += w * e[x] }
                if (ij >= 0) {
                    addBlock(ij, jj, ij, jj)
                    for (x in 0 until 3) { var s = 0.0; for (z in 0 until 3) s += jj[3 * z + x] * e[z]; g[3 * ij + x] += w * s }
                }
                if (ii >= 0 && ij >= 0) { addBlock(ii, null, ij, jj); addBlock(ij, jj, ii, null) }
            }
            for (a in 0 until m) h[a * m + a] += 1e-6
            val d = runCatching { Dense.solve(h, g.map { -it }.toDoubleArray(), m) }.getOrNull() ?: return
            for (k in 0 until n) {
                val q = ix(k); if (q < 0) continue
                val dk = doubleArrayOf(d[3 * q], d[3 * q + 1], d[3 * q + 2])
                moved = max(moved, sqrt(dk[0] * dk[0] + dk[1] * dk[1] + dk[2] * dk[2]))
                r[k] = M3.mul(r[k], M3.exp(dk[0], dk[1], dk[2]))
            }
            if (moved < 1e-6) break
        }
    }

    /** Rotation camera a -> camera b and its inlier count, from the points both see; null when too few. */
    fun relative(a: Map<Int, DoubleArray>, b: Map<Int, DoubleArray>, tol: Double, seed: Long, minIds: Int = 15, minIn: Int = 12): kotlin.Pair<DoubleArray, Int>? {
        val ids = a.keys.filter { it in b }
        if (ids.size < minIds) return null
        val x1 = ids.map { a[it]!! }; val x2 = ids.map { b[it]!! }
        // a pure turn first: when it explains the points, the baseline is too short for the essential matrix
        val pure = kabsch(x1, x2, ids.indices.toList())
        val pureIn = ids.indices.filter { angErr(pure, x1[it], x2[it]) < tol }
        val rnd = Random(seed)
        var best: DoubleArray? = null; var bestIn = -1
        repeat(120) {
            val s = HashSet<Int>(); while (s.size < 8) s.add(rnd.nextInt(ids.size))
            val e = eightPoint(x1, x2, s.toList()) ?: return@repeat
            var c = 0; for (k in ids.indices) if (sampson(e, x1[k], x2[k]) < tol * tol) c++
            if (c > bestIn) { bestIn = c; best = e }
        }
        val e0 = best
        if (e0 == null || bestIn < minIn || pureIn.size >= 0.9 * bestIn) {
            if (pureIn.size < minIn) return null
            return kabsch(x1, x2, pureIn) to pureIn.size
        }
        val inl = ids.indices.filter { sampson(e0, x1[it], x2[it]) < tol * tol }
        val e = eightPoint(x1, x2, inl) ?: e0
        val r = rotationOf(e, x1, x2, inl) ?: return null
        return r to inl.size
    }

    /** Normalised 8-point on bearings (z = 1): x2^T E x1 = 0, projected to rank 2 with equal singular values. */
    private fun eightPoint(x1: List<DoubleArray>, x2: List<DoubleArray>, idx: List<Int>): DoubleArray? {
        if (idx.size < 8) return null
        // Hartley normalisation of each set
        fun norm(x: List<DoubleArray>): DoubleArray {
            var mx = 0.0; var my = 0.0; for (i in idx) { mx += x[i][0]; my += x[i][1] }; mx /= idx.size; my /= idx.size
            var d = 0.0; for (i in idx) d += sqrt((x[i][0] - mx) * (x[i][0] - mx) + (x[i][1] - my) * (x[i][1] - my)); d /= idx.size
            val s = if (d > 1e-12) sqrt(2.0) / d else 1.0
            return doubleArrayOf(s, 0.0, -s * mx, 0.0, s, -s * my, 0.0, 0.0, 1.0)
        }
        val t1 = norm(x1); val t2 = norm(x2)
        val ata = DoubleArray(81)
        val row = DoubleArray(9)
        for (i in idx) {
            val a = M3.mv(t1, doubleArrayOf(x1[i][0], x1[i][1], 1.0)); val b = M3.mv(t2, doubleArrayOf(x2[i][0], x2[i][1], 1.0))
            for (p in 0 until 3) for (q in 0 until 3) row[3 * p + q] = b[p] * a[q]
            for (p in 0 until 9) for (q in 0 until 9) ata[9 * p + q] += row[p] * row[q]
        }
        val f = Dense.smallestEigvec(ata, 9)
        if (f.any { it.isNaN() }) return null
        val e = M3.mul(M3.t(t2), M3.mul(f, t1))
        return essentialProject(e)
    }

    /** E = U diag(s, s, 0) V^T with s the mean of the two largest singular values. */
    private fun essentialProject(e: DoubleArray): DoubleArray? {
        val (u, v) = svdRot(e) ?: return null
        val ev1 = M3.mv(e, doubleArrayOf(v[0], v[3], v[6])); val ev2 = M3.mv(e, doubleArrayOf(v[1], v[4], v[7]))
        val s = (len(ev1) + len(ev2)) / 2
        return M3.mul(u, M3.mul(M3.diag(s, s, 0.0), M3.t(v)))
    }

    /** U, V (rotations, columns) with E v_k = s_k u_k, for a 3 x 3 matrix whose third singular value is the smallest. */
    private fun svdRot(e: DoubleArray): kotlin.Pair<DoubleArray, DoubleArray>? {
        val ete = M3.mul(M3.t(e), e)
        val vals = M3.symEig(ete)                                   // ascending
        // v3 = eigenvector of the smallest eigenvalue, v1 of the largest
        val v3 = eigvec(ete, vals[0]) ?: return null
        // v1: any unit vector across v3 (the two large singular values are equal for an essential matrix)
        val ax = if (abs(v3[0]) < 0.6) doubleArrayOf(1.0, 0.0, 0.0) else doubleArrayOf(0.0, 1.0, 0.0)
        val v1 = unit(cross(v3, ax)) ?: return null
        val v2 = cross(v3, v1)
        val u1 = unit(M3.mv(e, v1)) ?: return null
        val u2raw = M3.mv(e, v2)
        val u2 = unit(DoubleArray(3) { u2raw[it] - dot(u2raw, u1) * u1[it] }) ?: return null
        val u3 = cross(u1, u2)
        val u = doubleArrayOf(u1[0], u2[0], u3[0], u1[1], u2[1], u3[1], u1[2], u2[2], u3[2])
        val v = doubleArrayOf(v1[0], v2[0], v3[0], v1[1], v2[1], v3[1], v1[2], v2[2], v3[2])
        return u to v
    }

    /** Of the four (R, t) in E, the rotation that puts most inliers in front of both cameras. */
    private fun rotationOf(e: DoubleArray, x1: List<DoubleArray>, x2: List<DoubleArray>, idx: List<Int>): DoubleArray? {
        val (u, v) = svdRot(e) ?: return null
        val w = doubleArrayOf(0.0, -1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)
        val ra = M3.mul(u, M3.mul(w, M3.t(v))); val rb = M3.mul(u, M3.mul(M3.t(w), M3.t(v)))
        val t = doubleArrayOf(u[2], u[5], u[8])
        var best: DoubleArray? = null; var bestN = -1
        for (r in listOf(ra, rb)) for (sg in doubleArrayOf(1.0, -1.0)) {
            val tt = DoubleArray(3) { t[it] * sg }
            var c = 0
            for (i in idx) {
                // depths z1, z2 with z2 x2 = z1 R x1 + t (least squares on the two rays)
                val a = M3.mv(r, doubleArrayOf(x1[i][0], x1[i][1], 1.0)); val b = doubleArrayOf(x2[i][0], x2[i][1], 1.0)
                // [a, -b] [z1 z2]^T = -t
                val aa = dot(a, a); val ab = dot(a, b); val bb = dot(b, b); val at = dot(a, tt); val bt = dot(b, tt)
                val det = aa * bb - ab * ab
                if (abs(det) < 1e-12) continue
                val z1 = (-at * bb + ab * bt) / det; val z2 = (aa * bt - ab * at) / det
                if (z1 > 0 && z2 > 0) c++
            }
            if (c > bestN) { bestN = c; best = r }
        }
        return best
    }

    /** The turn that best maps bearings x1 onto x2 (Kabsch on unit vectors). */
    private fun kabsch(x1: List<DoubleArray>, x2: List<DoubleArray>, idx: List<Int>): DoubleArray {
        val h = DoubleArray(9)
        for (i in idx) {
            val a = unit(doubleArrayOf(x1[i][0], x1[i][1], 1.0))!!; val b = unit(doubleArrayOf(x2[i][0], x2[i][1], 1.0))!!
            for (p in 0 until 3) for (q in 0 until 3) h[3 * p + q] += b[p] * a[q]
        }
        // nearest rotation to h (polar decomposition by a few Newton iterations: R <- (R + R^-T) / 2)
        var r = h.copyOf()
        repeat(30) {
            val inv = M3.inv(r) ?: return M3.eye()
            val it2 = M3.t(inv)
            r = DoubleArray(9) { (r[it] + it2[it]) / 2 }
        }
        val det = r[0] * (r[4] * r[8] - r[5] * r[7]) - r[1] * (r[3] * r[8] - r[5] * r[6]) + r[2] * (r[3] * r[7] - r[4] * r[6])
        return if (det > 0) r else M3.eye()
    }

    private fun angErr(r: DoubleArray, a: DoubleArray, b: DoubleArray): Double {
        val p = M3.mv(r, doubleArrayOf(a[0], a[1], 1.0))
        if (p[2] <= 1e-9) return 1e9
        return abs(p[0] / p[2] - b[0]) + abs(p[1] / p[2] - b[1])
    }

    private fun sampson(e: DoubleArray, a: DoubleArray, b: DoubleArray): Double {
        val x1 = doubleArrayOf(a[0], a[1], 1.0); val x2 = doubleArrayOf(b[0], b[1], 1.0)
        val ex1 = M3.mv(e, x1); val etx2 = M3.mtv(e, x2)
        val num = dot(x2, ex1)
        val den = ex1[0] * ex1[0] + ex1[1] * ex1[1] + etx2[0] * etx2[0] + etx2[1] * etx2[1]
        return if (den < 1e-18) 1e9 else num * num / den
    }

    /** Unit eigenvector of a symmetric 3 x 3 for eigenvalue [l]: the largest cross product of two rows of A - l I. */
    private fun eigvec(a: DoubleArray, l: Double): DoubleArray? {
        val r0 = doubleArrayOf(a[0] - l, a[1], a[2]); val r1 = doubleArrayOf(a[3], a[4] - l, a[5]); val r2 = doubleArrayOf(a[6], a[7], a[8] - l)
        val c = listOf(cross(r0, r1), cross(r0, r2), cross(r1, r2)).maxBy { dot(it, it) }
        return unit(c)
    }

    private fun dot(a: DoubleArray, b: DoubleArray) = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    private fun len(a: DoubleArray) = sqrt(dot(a, a))
    private fun cross(a: DoubleArray, b: DoubleArray) = doubleArrayOf(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    private fun unit(a: DoubleArray): DoubleArray? { val l = len(a); return if (l < 1e-12) null else DoubleArray(3) { a[it] / l } }
}

/** A fixed pool over the phone's cores for the engine's independent pieces of work (frames, pairs, views). */
class Par(val threads: Int) {
    private val exec = java.util.concurrent.Executors.newFixedThreadPool(threads) { r -> Thread(r, "engine").apply { isDaemon = true } }

    fun <T, R> map(items: List<T>, f: (T) -> R): List<R> {
        if (threads <= 1 || items.size <= 1) return items.map(f)
        return exec.invokeAll(items.map { Callable { f(it) } }).map { it.get() }
    }

    companion object {
        val default by lazy { Par(min(8, max(1, Runtime.getRuntime().availableProcessors()))) }
    }
}
