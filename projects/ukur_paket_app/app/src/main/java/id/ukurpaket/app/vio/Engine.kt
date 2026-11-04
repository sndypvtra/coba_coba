package id.ukurpaket.app.vio

import kotlinx.serialization.Serializable
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Everything the engine needs from one sweep. Frame positions 0 until n; [gray] gives frame i as the upright tracking
 * picture ([w] x [h]); [pickMask] is the object's mask on frame [pickFrame], same size.
 */
class SweepInput(
    val tCam: DoubleArray, val arrival: DoubleArray?, val realtimeClock: Boolean,
    val acc: List<Sample>, val gyro: List<Sample>, val rv: List<Sample>,
    val focalPrior: Double, val w: Int, val h: Int,
    val gray: (Int) -> Gray,
    val pickFrame: Int, val pickMask: Bits,
    val tracks: List<Track>? = null,
)

@Serializable
data class SweepResult(
    val lengthCm: Double, val widthCm: Double, val heightCm: Double,
    val confidence: Int, val ok: Boolean, val method: String,
    val frames: Int, val points: Int, val objectPoints: Int, val densePoints: Int,
    val rotationSource: String, val timeOffsetMs: Double, val focalPx: Double, val reprojPx: Double,
    val scaleSdPct: Double, val accMotion: Double, val floorTiltDeg: Double, val seconds: Double,
    val notes: List<String>,
    /** Per frame: the object's outline (convex hull of its points), x, y pairs as fractions of the picture. */
    val outlines: List<List<Float>>,
    /** Per frame: the 8 box corners (bottom 4, top 4), x, y pairs as fractions of the picture; empty when behind. */
    val boxes: List<List<Float>>,
)

class EngineFailed(msg: String) : Exception(msg)

object Engine {
    private val RDC = M3.diag(1.0, -1.0, -1.0)      // upright camera -> device (portrait phone, back camera)

    /** Optional trace of the intermediate numbers (tests, and the recording's result.json). */
    var trace: ((String) -> Unit)? = null

    fun run(inp: SweepInput, pool: Par = Par.default, progress: (String, Float) -> Unit = { _, _ -> }): SweepResult {
        val t0 = System.nanoTime()
        val n = inp.tCam.size
        if (n < 15) throw EngineFailed("Rekaman terlalu pendek ($n foto)")
        val notes = ArrayList<String>()
        // 1. tracks
        val tracks = inp.tracks ?: run {
            val tr = Tracker(levels = RecordingTracker.ENGINE_LEVELS, pool = pool)
            for (i in 0 until n) { tr.feed(inp.gray(i)); if (i % 5 == 0) progress("Melacak titik", 0.25f * i / n) }
            trace?.invoke("tracker: ${tr.tracks.size} tracks, bridged ${tr.bridged} bad frames")
            tr.tracks
        }
        val obs = tracks.filter { it.n >= 3 }.map { t -> PointObs(t.id, t.f.copyOf(t.n), DoubleArray(t.n) { t.x[it].toDouble() }, DoubleArray(t.n) { t.y[it].toDouble() }) }
        if (obs.size < 50) throw EngineFailed("Terlalu sedikit titik yang bisa dilacak (${obs.size}). Butuh permukaan bertekstur dan cahaya cukup.")
        // 2. clocks and rotations
        var times = inp.tCam.copyOf()
        if (!inp.realtimeClock && inp.arrival != null) {
            val off = inp.tCam.indices.map { inp.arrival[it] - inp.tCam[it] }.sorted()[n / 2]
            times = DoubleArray(n) { inp.tCam[it] + off }
        }
        val sensorRot = RotationSource(inp.gyro, inp.rv)
        val cx = inp.w / 2.0; val cy = inp.h / 2.0
        var rot: RotationSource
        var gKnown: DoubleArray?
        var bestTd = 0.0; var f = inp.focalPrior
        val ba: Structure
        val pre: List<Preint>
        val al: Inertial.Alignment
        if (sensorRot.available) {
            rot = sensorRot
            if (!rot.fromRv) notes += "Putaran dari gyroscope (tanpa koreksi bias)."
            gKnown = if (rot.fromRv) doubleArrayOf(0.0, 0.0, -Inertial.G) else null
            fun rwc(td: Double) = Array(n) { M3.mul(rot.at(times[it] + td), RDC) }
            // 3. time offset and focal length: least reprojection error of the linear stage (independent tries, in parallel)
            val sub = obs.filterIndexed { i, _ -> i % 3 == 0 }
            fun err(td: Double, ff: Double) = Vision.linear(rwc(td), sub, Intrinsics(ff, cx, cy), iters = 1).medianErr
            progress("Mencocokkan jam kamera dan sensor", 0.3f)
            val coarse = (0..12).map { -0.08 + 0.01 * it }
            val ce = pool.map(coarse) { err(it, inp.focalPrior) }
            var bestE = ce.min(); bestTd = coarse[ce.indexOf(bestE)]
            val fine = (0..8).map { bestTd - 0.008 + 0.002 * it }
            val fe = pool.map(fine) { err(it, inp.focalPrior) }
            if (fe.min() < bestE) { bestE = fe.min(); bestTd = fine[fe.indexOf(bestE)] }
            progress("Mengkalibrasi lensa", 0.4f)
            val fs = listOf(0.9, 0.95, 1.05, 1.1).map { inp.focalPrior * it }
            val fsE = pool.map(fs) { err(bestTd, it) }
            if (fsE.min() < bestE) { bestE = fsE.min(); f = fs[fsE.indexOf(bestE)] }
            trace?.invoke("tracks ${tracks.size}, used ${obs.size}, td ${bestTd}, f ${f}, search err ${bestE}")
            // 4. structure, bundle adjustment, metric scale
            progress("Menghitung posisi kamera", 0.45f)
            val lin = Vision.linear(rwc(bestTd), obs, Intrinsics(f, cx, cy))
            progress("Bundle adjustment", 0.55f)
            trace?.invoke("linear: points ${lin.points.size}, median err ${lin.medianErr}")
            ba = Vision.bundleAdjust(lin, obs, Intrinsics(f, cx, cy))
            pre = Inertial.preintegrate(DoubleArray(n) { times[it] + bestTd }, rot, inp.acc)
            al = Inertial.align(Array(n) { ba.cams[it].c }, pre, gKnown)
        } else {
            // no gyroscope and no rotation vector (the DT50's sensor hub sends neither): the camera's own rotation
            progress("Menghitung putaran HP dari kamera", 0.3f)
            val cam0 = Intrinsics(f, cx, cy)
            val vr = VisualRotation.solve(obs, n, cam0, pool, trace)
                ?: throw EngineFailed("Putaran HP tidak terbaca dari kamera: terlalu banyak foto blur/gelap. Tambah cahaya, sapukan lebih pelan.")
            val rwcV = vr.rot
            notes += "Gyroscope dan rotation vector tidak mengirim data: putaran HP dihitung dari kamera."
            if (vr.measuredCount < n) notes += "${n - vr.measuredCount} dari $n foto blur/kosong: putarannya diisi dari foto sebelah."
            trace?.invoke("visual: measured ${vr.measuredCount} of $n frames")
            progress("Menghitung posisi kamera", 0.45f)
            val lin = Vision.linear(rwcV, obs, cam0)
            trace?.invoke("visual: linear points ${lin.points.size}, median err ${lin.medianErr}")
            progress("Bundle adjustment", 0.55f)
            ba = Vision.bundleAdjust(lin, obs, cam0, sigRotDeg = 1.0, iters = 8)
            val rwd = Array(n) { M3.mul(ba.cams[it].r, RDC) }        // RDC is its own inverse
            // the scale only from frames whose position was measured: a blank or blurred frame's centre is a guess
            // (the middle of its neighbours) and would spoil the inertial fit; the accelerometer is integrated past it
            val seenBy = IntArray(n); for (p in obs) if ((ba.err[p.id] ?: 99.0) < 2.0) for (kk in p.k) if (kk in 0 until n) seenBy[kk]++
            // and only frames inside the accelerometer's recording (its first and last sample)
            val aT0 = inp.acc.firstOrNull()?.t ?: Double.NEGATIVE_INFINITY; val aT1 = inp.acc.lastOrNull()?.t ?: Double.POSITIVE_INFINITY
            val gi = (0 until n).filter { vr.measured[it] && seenBy[it] >= 10 && times[it] in aT0 - 0.02..aT1 + 0.02 }.ifEmpty { (0 until n).toList() }
            if (gi.size < n) trace?.invoke("visual: scale from ${gi.size} of $n frames")
            // accelerometer clock against the frames: the offset that makes the inertial alignment fit best
            fun aligned(td: Double): Triple<RotationSource, List<Preint>, Inertial.Alignment> {
                val tt = DoubleArray(n) { times[it] + td }
                val rs = RotationSource.fromFrames(tt, rwd)
                // gravity in this world, as a fallback: the accelerometer's mean over the sweep, turned into the world
                val g = DoubleArray(3); var c = 0
                for (a in inp.acc) if (a.t in tt.first()..tt.last()) { val v = M3.mv(rs.at(a.t), a.v); for (k in 0 until 3) g[k] -= v[k]; c++ }
                val gl = sqrt(g[0] * g[0] + g[1] * g[1] + g[2] * g[2])
                val gk = if (c > 10 && gl > 0) DoubleArray(3) { g[it] / gl * Inertial.G } else null
                val pr = Inertial.preintegrate(DoubleArray(gi.size) { tt[gi[it]] }, rs, inp.acc)
                val cs = Array(gi.size) { ba.cams[gi[it]].c }
                // gravity solved with the rest (better on the synthetic sweeps); the mean only if that one is implausible
                val free = Inertial.align(cs, pr, null)
                val gl2 = sqrt(free.gravity.sumOf { it * it })
                return Triple(rs, pr, if (gl2 in 9.3..10.3 || gk == null) free else Inertial.align(cs, pr, gk))
            }
            val tds = (0..24).map { -0.08 + 0.005 * it }
            val tries = pool.map(tds) { td -> runCatching { aligned(td) }.getOrNull()?.takeIf { it.third.scale > 0 } }
            val k = tries.indices.filter { tries[it] != null }.minByOrNull { tries[it]!!.third.rms } ?: throw EngineFailed("Skala tidak terbaca: HP kurang digeser")
            bestTd = tds[k]
            rot = tries[k]!!.first; pre = tries[k]!!.second; al = tries[k]!!.third; gKnown = al.gravity
            trace?.invoke("visual: td ${bestTd}, BA err ${ba.medianErr}")
        }
        val cam = Intrinsics(f, cx, cy)
        trace?.invoke("BA: points ${ba.points.size}, median worst-err ${ba.medianErr}, good ${ba.err.count { it.value < 1.5 }}")
        if (al.scale <= 0) throw EngineFailed("Skala tidak terbaca: HP kurang digeser")
        val s = al.scale
        trace?.invoke("scale ${al.scale} sd ${al.scaleSd} bias ${al.accBias.toList()} rms ${al.rms}")
        // gravity-aligned metric world (z up)
        val gdir = al.gravity.let { g -> val l = sqrt(g[0] * g[0] + g[1] * g[1] + g[2] * g[2]); DoubleArray(3) { g[it] / l } }
        val ga = M3.align(gdir, doubleArrayOf(0.0, 0.0, -1.0))
        val cams = Array(n) { Cam(M3.mul(ga, ba.cams[it].r), M3.mv(ga, DoubleArray(3) { a -> ba.cams[it].c[a] * s })) }
        val good = ba.err.filter { it.value < 1.5 }.keys
        val pts = HashMap<Int, DoubleArray>()
        for (id in good) pts[id] = M3.mv(ga, ba.points[id]!!.let { p -> DoubleArray(3) { p[it] * s } })
        // acceleration actually present (no metric scale without it)
        val am = inp.acc.map { sqrt(it.v[0] * it.v[0] + it.v[1] * it.v[1] + it.v[2] * it.v[2]) }
        val amMean = am.average(); val accMotion = sqrt(am.sumOf { (it - amMean) * (it - amMean) } / max(1, am.size - 1))
        // 5. seeds: points seen in the picked frame inside its mask
        progress("Memisahkan objek", 0.65f)
        val mask = inp.pickMask.erode()
        val seen = tracks.filter { t -> t.id in pts && t.at(inp.pickFrame).let { j -> j >= 0 && mask[t.x[j].toInt(), t.y[j].toInt()] } }.map { it.id }.toSet()
        // few points seen on the picked frame itself (blurred just after the touch): the 3D points that fall inside its
        // mask; those of the floor behind the object drop out below, as they stand at height 0
        val seedIds = if (seen.size >= 12) seen else {
            val pc = cams[inp.pickFrame]; val ic = Intrinsics(f, cx, cy)
            val cand = pts.filter { (_, p) -> project(p, pc, ic)?.let { uv -> mask[uv[0].toInt(), uv[1].toInt()] } == true }
            // the object's front is what is nearest inside the mask; the floor and anything behind it are further
            val z = cand.mapValues { (_, p) -> M3.mtv(pc.r, DoubleArray(3) { p[it] - pc.c[it] })[2] }
            val zs = z.values.sorted()
            val zRef = if (zs.isEmpty()) 0.0 else zs[(zs.size * 0.3).toInt().coerceAtMost(zs.size - 1)]
            seen + z.filter { it.value <= 1.3 * zRef }.keys
        }
        if (seedIds.size > seen.size) trace?.invoke("seeds: seen ${seen.size}, projected ${seedIds.size - seen.size}")
        if (seedIds.size < 8) throw EngineFailed("Objek pilihan hampir tidak punya titik terlacak (${seedIds.size}). Pilih objek yang lebih besar di layar atau lebih bertekstur.")
        val seedPts = seedIds.map { pts[it]!! }
        val sc = DoubleArray(2); for (p in seedPts) { sc[0] += p[0] / seedPts.size; sc[1] += p[1] / seedPts.size }
        val bg = pts.filter { it.key !in seedIds && hyp(it.value[0] - sc[0], it.value[1] - sc[1]) < 0.6 }.values.toList()
        val plane = Measure.supportPlane(bg.ifEmpty { pts.values.toList() }) ?: throw EngineFailed("Bidang tumpu (lantai / meja) tidak ditemukan")
        val tilt = Math.toDegrees(kotlin.math.acos(abs(plane.n[2]).coerceAtMost(1.0)))
        val toPlane = M3.align(plane.n, doubleArrayOf(0.0, 0.0, 1.0))
        fun pf(p: DoubleArray): DoubleArray { val q = M3.mv(toPlane, p); return doubleArrayOf(q[0], q[1], plane.height(p)) }
        // sparse object points: standing on the plane, joined to the seeds
        val sparseAll = pts.values.map { pf(it) }.filter { it[2] > 0.008 }
        val seedsP = seedPts.map { pf(it) }.filter { it[2] > 0.008 }
        val sparseObj = Measure.grow(sparseAll, seedsP, 0.03).map { sparseAll[it] }
        // 6. dense depth: picked frame (its mask) first, then three more views round where it found the object
        progress("Menghitung depth padat", 0.7f)
        val half = Intrinsics(f / 2, cx / 2, cy / 2)
        fun halfGray(i: Int) = inp.gray(i).half()
        fun neighbours(r: Int) = listOf(r - 8, r - 4, r + 4, r + 8).filter { it in 0 until n }.map { halfGray(it) to cams[it] }
        fun depthRange(r: Int, ref: List<DoubleArray>): Pair<Double, Double>? {
            val z = ref.map { p -> val d = DoubleArray(3) { p[it] - cams[r].c[it] }; M3.mtv(cams[r].r, d)[2] }.filter { it > 0.05 }
            if (z.size < 5) return null
            return Measure.pct(z.toDoubleArray(), 1.0) * 0.8 to Measure.pct(z.toDoubleArray(), 99.0) * 1.25
        }
        val worldSeeds = seedPts
        val dense = ArrayList<DoubleArray>()
        val pk = inp.pickFrame
        val r0 = depthRange(pk, worldSeeds)
        var seedDense: List<DoubleArray> = emptyList()
        if (r0 != null) {
            val d0 = Measure.planeSweep(halfGray(pk), cams[pk], neighbours(pk), half, inp.pickMask.half().erode(), r0.first, r0.second)
            seedDense = d0.filter { plane.height(it) > 0.008 }
            dense.addAll(seedDense)
        }
        val src = if (seedDense.size > 200) seedDense else worldSeeds
        val others = listOf(0.1, 0.3, 0.5, 0.7, 0.9).map { (it * (n - 1)).toInt() }.filter { abs(it - pk) > 6 }.distinct()
        for ((oi, r) in others.withIndex()) {
            progress("Menghitung depth padat", 0.72f + 0.2f * oi / max(1, others.size))
            val roi = roiFrom(src, cams[r], half, inp.w / 2, inp.h / 2) ?: continue
            val rng = depthRange(r, src) ?: continue
            dense.addAll(Measure.planeSweep(halfGray(r), cams[r], neighbours(r), half, roi, rng.first, rng.second).filter { plane.height(it) > 0.008 })
        }
        // 7. object: dense points standing on the plane, joined to the picked frame's object points
        progress("Menghitung ukuran", 0.95f)
        val denseP = dense.map { pf(it) }
        val seedsDP = (if (seedDense.size > 200) seedDense else worldSeeds).map { pf(it) }.filter { it[2] > 0.008 }
        var obj = Measure.grow(denseP, seedsDP, 0.022).map { denseP[it] }
        var method = "depth padat"
        if (obj.size < 300) { obj = sparseObj; method = "titik jarang"; notes += "Depth padat kurang (permukaan polos/gelap): ukuran dari titik jarang, cenderung kecil." }
        if (obj.size < 20) throw EngineFailed("Objek tidak terbaca dalam 3D")
        val stride = max(1, obj.size / 3000)
        val clean = Measure.removeOutliers(obj.filterIndexed { i, _ -> i % stride == 0 })
        val bx = Measure.box(clean)
        // 8. quality
        val sdPct = 100 * al.scaleSd / s
        var conf = 100
        if (sdPct > 1.5) conf -= ((sdPct - 1.5) * 10).toInt()
        if (ba.medianErr > 0.8) conf -= ((ba.medianErr - 0.8) * 30).toInt()
        if (accMotion < 0.3) { conf -= 25; notes += "HP kurang digeser: skala meter kurang teliti." }
        if (method != "depth padat") conf -= 20
        if (tilt > 3) { conf -= 10; notes += "Bidang tumpu miring ${"%.1f".format(tilt)}° terhadap gravitasi." }
        if (!rot.fromRv) conf -= 10
        if (rot.visual) conf -= 5
        conf = conf.coerceIn(0, 100)
        // 9. per frame: object outline and box, for the review screen
        // the outline from the points inside the measured box (+1 cm): the same object the size is of
        val foot = bx.corners.map { id.ukurpaket.app.measure.P2(it[0].toFloat(), it[1].toFloat()) }
        val cxF = foot.map { it.a }.average().toFloat(); val cyF = foot.map { it.b }.average().toFloat()
        val footG = foot.map { c -> val dx = c.a - cxF; val dy = c.b - cyF; val l = sqrt((dx * dx + dy * dy).toDouble()).toFloat(); id.ukurpaket.app.measure.P2(c.a + dx / l * 0.01f, c.b + dy / l * 0.01f) }
        val inBox = clean.filter { q -> q[2] <= bx.h + 0.01 && Measure.inPoly(footG, q[0].toFloat(), q[1].toFloat()) }
        val objW = inBox.filterIndexed { i, _ -> i % max(1, inBox.size / 600) == 0 }.map { q -> fromPlane(q, toPlane, plane) }
        val outlines = ArrayList<List<Float>>(); val boxes = ArrayList<List<Float>>()
        val corners = bx.corners.map { c -> doubleArrayOf(c[0], c[1], 0.0) } + bx.corners.map { c -> doubleArrayOf(c[0], c[1], bx.h) }
        val cornersW = corners.map { fromPlane(it, toPlane, plane) }
        for (k in 0 until n) {
            val pp = objW.mapNotNull { project(it, cams[k], cam) }.map { floatArrayOf((it[0] / inp.w).toFloat(), (it[1] / inp.h).toFloat()) }
            outlines.add(Measure.hull2(pp).flatMap { listOf(it.a, it.b) })
            val bc = cornersW.map { project(it, cams[k], cam) }
            boxes.add(if (bc.any { it == null }) emptyList() else bc.flatMap { listOf((it!![0] / inp.w).toFloat(), (it[1] / inp.h).toFloat()) })
        }
        return SweepResult(bx.l * 100, bx.w * 100, bx.h * 100, conf, conf >= 75, method, n, pts.size, sparseObj.size, dense.size,
            if (rot.visual) "kamera (visual)" else if (rot.fromRv) "rotation vector" else "gyroscope", bestTd * 1000, f, ba.medianErr, sdPct, accMotion, tilt,
            (System.nanoTime() - t0) / 1e9, notes, outlines, boxes)
    }

    private fun hyp(a: Double, b: Double) = sqrt(a * a + b * b)

    /** (u, v, height) in the plane frame -> world: the inverse of pf (height = n.p + d, (toPlane p)_z = n.p). */
    private fun fromPlane(q: DoubleArray, toPlane: DoubleArray, plane: Plane): DoubleArray =
        M3.mtv(toPlane, doubleArrayOf(q[0], q[1], q[2] - plane.d))

    fun project(p: DoubleArray, c: Cam, cam: Intrinsics): DoubleArray? {
        val xc = M3.mtv(c.r, DoubleArray(3) { p[it] - c.c[it] })
        if (xc[2] < 0.02) return null
        return doubleArrayOf(cam.f * xc[0] / xc[2] + cam.cx, cam.f * xc[1] / xc[2] + cam.cy)
    }

    /** Where [pts] fall in a view, as a mask: their hull, grown by 15 % of its size. */
    private fun roiFrom(pts: List<DoubleArray>, c: Cam, cam: Intrinsics, w: Int, h: Int): Bits? {
        val uv = pts.mapNotNull { project(it, c, cam) }.map { floatArrayOf(it[0].toFloat(), it[1].toFloat()) }
        if (uv.size < 5) return null
        val hull = Measure.hull2(uv)
        if (hull.size < 3) return null
        val xs = uv.map { it[0] }; val ys = uv.map { it[1] }
        val grow = (0.15f * max(xs.max() - xs.min(), ys.max() - ys.min())).toInt() + 3
        val b = BooleanArray(w * h)
        val x0 = max(0, xs.min().toInt() - grow); val x1 = min(w - 1, xs.max().toInt() + grow)
        val y0 = max(0, ys.min().toInt() - grow); val y1 = min(h - 1, ys.max().toInt() + grow)
        // inside the hull, or within `grow` of it (checked on a coarse step)
        for (y in y0..y1) for (x in x0..x1) {
            if (Measure.inPoly(hull, x.toFloat(), y.toFloat())) { b[y * w + x] = true; continue }
            var near = false
            for (pt in hull) { val dx = pt.a - x; val dy = pt.b - y; if (dx * dx + dy * dy < grow * grow) { near = true; break } }
            if (!near) for (i in hull.indices) {
                val a = hull[i]; val bb = hull[(i + 1) % hull.size]
                val ex = bb.a - a.a; val ey = bb.b - a.b; val l2 = ex * ex + ey * ey
                val t = (((x - a.a) * ex + (y - a.b) * ey) / max(l2, 1e-6f)).coerceIn(0f, 1f)
                val px = a.a + t * ex - x; val py = a.b + t * ey - y
                if (px * px + py * py < grow * grow) { near = true; break }
            }
            b[y * w + x] = near
        }
        return Bits(w, h, b)
    }
}
