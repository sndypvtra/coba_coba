package id.ukurpaket.app.vio

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.measure.dilate
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * 2D affine motion x' = a x + b y + tx, y' = c x + d y + ty. Fitted either as a similarity (shift, scale, turn: 2
 * points per sample) or as a full affine (also the squash of a face seen more and more from the side: 3 points).
 */
class Aff(val a: Double, val b: Double, val c: Double, val d: Double, val tx: Double, val ty: Double) {
    fun apply(x: Double, y: Double) = doubleArrayOf(a * x + b * y + tx, c * x + d * y + ty)
    /** this after [o]. */
    fun after(o: Aff) = Aff(a * o.a + b * o.c, a * o.b + b * o.d, c * o.a + d * o.c, c * o.b + d * o.d,
        a * o.tx + b * o.ty + tx, c * o.tx + d * o.ty + ty)
    fun inverse(): Aff {
        val det = a * d - b * c
        val ia = d / det; val ib = -b / det; val ic = -c / det; val id = a / det
        return Aff(ia, ib, ic, id, -(ia * tx + ib * ty), -(ic * tx + id * ty))
    }
    /** The two stretch factors (singular values of the linear part). */
    fun stretch(): Pair<Double, Double> {
        val e = a * a + c * c; val f = a * b + c * d; val g = b * b + d * d
        val m = (e + g) / 2; val r = sqrt(((e - g) / 2) * ((e - g) / 2) + f * f)
        return sqrt(max(0.0, m - r)) to sqrt(m + r)
    }

    companion object {
        val ID = Aff(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

        private fun fit(p: List<FloatArray>, q: List<FloatArray>, affine: Boolean): Aff? {
            if (affine) {
                if (p.size < 3) return null
                // two 3 x 3 least squares sharing [x y 1]
                val ata = DoubleArray(9); val bx = DoubleArray(3); val by = DoubleArray(3)
                for (i in p.indices) {
                    val r = doubleArrayOf(p[i][0].toDouble(), p[i][1].toDouble(), 1.0)
                    for (j in 0 until 3) { bx[j] += r[j] * q[i][0]; by[j] += r[j] * q[i][1]; for (k in 0 until 3) ata[3 * j + k] += r[j] * r[k] }
                }
                val u = runCatching { Dense.solve(ata.copyOf(), bx, 3) }.getOrNull() ?: return null
                val v = runCatching { Dense.solve(ata.copyOf(), by, 3) }.getOrNull() ?: return null
                if (u.any { it.isNaN() } || v.any { it.isNaN() }) return null
                return Aff(u[0], u[1], v[0], v[1], u[2], v[2])
            }
            if (p.size < 2) return null
            // least squares on [x -y 1 0; y x 0 1] [a b tx ty]^T = [x' y']
            val ata = DoubleArray(16); val atb = DoubleArray(4)
            for (i in p.indices) {
                val x = p[i][0].toDouble(); val y = p[i][1].toDouble()
                val r1 = doubleArrayOf(x, -y, 1.0, 0.0); val r2 = doubleArrayOf(y, x, 0.0, 1.0)
                for (j in 0 until 4) { atb[j] += r1[j] * q[i][0] + r2[j] * q[i][1]; for (k in 0 until 4) ata[4 * j + k] += r1[j] * r1[k] + r2[j] * r2[k] }
            }
            val x = runCatching { Dense.solve(ata, atb, 4) }.getOrNull() ?: return null
            if (x.any { it.isNaN() }) return null
            return Aff(x[0], -x[1], x[1], x[0], x[2], x[3])
        }

        /** RANSAC on point pairs, refitted on the inliers within [tol] px. */
        fun estimate(p: List<FloatArray>, q: List<FloatArray>, affine: Boolean, tol: Double = 3.0, iters: Int = 60, seed: Long = 1): Pair<Aff, BooleanArray>? {
            val k = if (affine) 3 else 2
            if (p.size < k + 1) return null
            val rnd = java.util.Random(seed)
            var best: Aff? = null; var bestN = -1
            repeat(iters) {
                val idx = HashSet<Int>(); while (idx.size < k) idx.add(rnd.nextInt(p.size))
                val s = fit(idx.map { p[it] }, idx.map { q[it] }, affine) ?: return@repeat
                var n = 0
                for (j in p.indices) { val r = s.apply(p[j][0].toDouble(), p[j][1].toDouble()); if (abs(r[0] - q[j][0]) + abs(r[1] - q[j][1]) < tol) n++ }
                if (n > bestN) { bestN = n; best = s }
            }
            val b = best ?: return null
            val inl = BooleanArray(p.size) { j -> val r = b.apply(p[j][0].toDouble(), p[j][1].toDouble()); abs(r[0] - q[j][0]) + abs(r[1] - q[j][1]) < tol }
            val ip = p.filterIndexed { j, _ -> inl[j] }; val iq = q.filterIndexed { j, _ -> inl[j] }
            return (fit(ip, iq, affine) ?: b) to inl
        }
    }
}

/**
 * The object followed live while recording, as a mask on every frame:
 *  - MobileSAM (the light 512 model on PDAs) cuts the object out of the touched frame: box or tap;
 *  - every frame, the object's tracked points carry the mask along (a similarity: shift, scale, turn; on the synthetic
 *    sweeps a full affine or a plain shift do no better, as the outline changes shape when the camera goes round),
 *    and the object's and background's colours, learnt from the last MobileSAM answer, set its edges within 3 cells
 *    of the carried mask, frame by frame (PER_FRAME). Carrying the refined edges on (RECURSIVE) adapts better on the
 *    synthetic sweeps but creeps into a real background of similar colour; on the test video PER_FRAME keeps IoU 0,89
 *    with MobileSAM every 30 frames, RECURSIVE 0,32, none 0,82;
 *  - MobileSAM runs again in the background as often as it can, prompted with the box of the mask and the tracked
 *    points; its answer is moved forward to the current frame and taken when it is the same object (most like the
 *    carried mask, covering most of the tracked points).
 * The mask is kept as it was on its last anchor frame plus the motion since, so small motions add up instead of
 * being rounded away frame by frame.
 * Coordinates: the upright tracking picture [w] x [h]; the mask is kept at a quarter of that.
 * [shared]: the recording's tracker (the engine's tracks, fed every frame by the recorder), whose tracks [step] is given;
 * without it the segmenter tracks on its own. [threads] = true runs MobileSAM on its own thread (the phone); false runs
 * it inside [step] (tests, deterministic), every [syncEvery] frames.
 */
class LiveSegmenter(
    /** The model, once loaded (it may still be loading when recording starts: then the first answer comes later). */
    private val samOf: () -> Segmenter?, val w: Int, val h: Int,
    private val onUpdate: (Update) -> Unit,
    private val onFirstMask: (frame: Int, mask: Mask, samMs: Long) -> Unit = { _, _, _ -> },
    private val threads: Boolean = true, private val syncEvery: Int = 12, private val motion: Motion = Motion.SIMILARITY,
    shared: Tracker? = null,
    /** At least this long between MobileSAM runs (phone: leaves the cores to the recording's tracking). */
    private val minSamGapMs: Long = 0,
    private val refine: Refine = Refine.PER_FRAME,
) {
    enum class Motion { SHIFT, SHIFT_SCALE, SIMILARITY, AFFINE }
    /** Debug lines (tests). */
    var trace: ((String) -> Unit)? = null
    /** Edge refinement by colour between MobileSAM answers: none, on the carried mask, or carried on (the mask adapts). */
    enum class Refine { NONE, PER_FRAME, RECURSIVE }
    /** [outline]: x, y pairs as fractions of the picture; [samMs]: the last MobileSAM run; [anchors]: its answers taken. */
    class Update(val outline: FloatArray, val tracked: Int, val anchors: Int, val samMs: Long?, val frame: Int, val segmented: Boolean)

    private val gw = max(1, w / 4); private val gh = max(1, h / 4)
    // 4 pyramid levels: a hand-held sweep at ~15 frames a second can move 40-60 px between frames
    private val tracker = shared ?: Tracker(maxTracks = 300, minDist = 10, levels = 4)
    private var prevTf = -1                                // the tracker's frame at the previous step
    private val member = HashSet<Int>()
    private var base = BooleanArray(gw * gh)               // the mask on its anchor frame
    private var cum = Aff.ID                               // anchor frame -> now
    private var mask = BooleanArray(gw * gh)               // base carried to now
    private val history = HashMap<Int, Aff>()              // frame -> motion from the previous frame
    private var frame = -1
    @Volatile var anchors = 0; private set
    @Volatile var lastSamMs: Long? = null; private set
    @Volatile private var samBusy = false
    @Volatile private var lastSamEnd = 0L
    private class Answer(val frame: Int, val cands: List<Mask>, val colour: IntArray)
    @Volatile private var pending: Answer? = null
    private var colours: ColourModel? = null
    @Volatile var segmented = false; private set          // MobileSAM has cut the object at least once
    private var firstTried = false
    @Volatile private var closed = false
    private val samExec = ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, ArrayBlockingQueue(1), ThreadPoolExecutor.DiscardPolicy())
    private var prompt: FloatArray? = null                  // the touch: box (4) or tap (2), fractions
    val maskNow: Mask get() = synchronized(this) { Mask(gw, gh, mask.copyOf()) }

    /** The touch: [box] x0, y0, x1, y1 or [tap] x, y, as fractions of the picture. Until MobileSAM answers it is the mask. */
    fun begin(box: FloatArray?, tap: FloatArray?) {
        prompt = box ?: tap
        val m = BooleanArray(gw * gh)
        for (y in 0 until gh) for (x in 0 until gw) {
            val fx = (x + 0.5f) / gw; val fy = (y + 0.5f) / gh
            m[y * gw + x] = if (box != null) fx in box[0]..box[2] && fy in box[1]..box[3]
            else { val dx = fx - tap!![0]; val dy = (fy - tap[1]) * h / w; dx * dx + dy * dy < 0.06f * 0.06f }
        }
        synchronized(this) { base = m; cum = Aff.ID; mask = m.copyOf() }
    }

    /** Starts from a known mask (any size; tests, or a pick cut earlier). */
    fun begin(m: Mask, colour: IntArray? = null) {
        prompt = null
        val g = largest(down(m))
        synchronized(this) { base = g; cum = Aff.ID; mask = g.copyOf() }
        if (colour != null) colours = ColourModel.of(g, shrink(colour), gw, gh)
        segmented = true; firstTried = true
    }

    /** One frame: track, carry the mask, maybe start MobileSAM, report the outline. [argb] gives the frame in colour for MobileSAM. */
    fun step(frameNo: Int, g: Gray, argb: () -> IntArray, small: (() -> IntArray)? = null, tracks: List<Track>? = null) {
        if (closed) return
        val live = tracks ?: tracker.feed(g)
        val tf = tracker.frames - 1; val ptf = prevTf; prevTf = tf
        val prev = frame; frame = frameNo
        if (prev >= 0) {
            // the members' motion from the previous frame
            val p = ArrayList<FloatArray>(); val q = ArrayList<FloatArray>(); val ids = ArrayList<Int>()
            for (t in live) if (t.id in member) { val j = t.at(ptf); if (j >= 0) { p.add(floatArrayOf(t.x[j], t.y[j])); q.add(floatArrayOf(t.lastX(), t.lastY())); ids.add(t.id) } }
            // too few of the object's own points (blur, a thin object): the points round it, which move with the camera
            var own = true
            if (p.size < MIN_OWN) {
                val b = synchronized(this) { bbox(mask) }
                if (b != null) {
                    val mx = 0.5f * (b[2] - b[0]) + 24; val my = 0.5f * (b[3] - b[1]) + 24
                    p.clear(); q.clear(); ids.clear(); own = false
                    for (t in live) { val j = t.at(ptf); if (j < 0) continue
                        val x = t.x[j]; val y = t.y[j]
                        if (x in b[0] - mx..b[2] + mx && y in b[1] - my..b[3] + my) { p.add(floatArrayOf(x, y)); q.add(floatArrayOf(t.lastX(), t.lastY())); ids.add(-1) }
                    }
                }
            }
            val est = when {
                !own -> Aff.estimate(p, q, false, tol = 4.0)
                motion == Motion.SHIFT || motion == Motion.SHIFT_SCALE -> shiftScale(p, q, motion == Motion.SHIFT_SCALE)
                else -> Aff.estimate(p, q, motion == Motion.AFFINE && p.size >= 12)
            }
            val s = est?.first?.takeIf { plausible(it) } ?: Aff.ID
            trace?.invoke("f$frameNo ${if (own) "members" else "around"} ${p.size} inliers ${est?.second?.count { it }} motion ${"%.1f".format(s.tx)},${"%.1f".format(s.ty)} k ${"%.3f".format(s.stretch().second)}${if (est != null && !plausible(est.first)) " REJECTED" else ""}")
            if (own) est?.second?.let { inl -> for (k in ids.indices) if (!inl[k]) member.remove(ids[k]) }
            history[frameNo] = s
            history.keys.filter { it < frameNo - 150 }.forEach { history.remove(it) }
            synchronized(this) { cum = s.after(cum); mask = warp(base, cum) }
        }
        pending?.let { pending = null; mergeAnchor(it.frame, it.cands, it.colour) }
        // the edges moved to where the picture's colours say the object is
        val cm = colours
        if (prev >= 0 && cm != null && refine != Refine.NONE) {
            val col = small?.invoke() ?: shrink(argb())
            val r = cm.refine(mask, col)
            if (r != null) synchronized(this) { mask = r; if (refine == Refine.RECURSIVE) { base = r; cum = Aff.ID } }
        }
        // membership: points born inside the mask join; members that left it go
        synchronized(this) {
            for (t in live) {
                val inM = at(mask, t.lastX(), t.lastY())
                if (t.f[0] == tf && inM && atEroded(mask, t.lastX(), t.lastY())) member.add(t.id)
                if (t.id in member && !inM && !near(mask, t.lastX(), t.lastY())) member.remove(t.id)
            }
        }
        val liveIds = live.map { it.id }.toHashSet(); member.retainAll(liveIds)
        // the object running short of points: new corners inside it (eroded, so they are its own)
        if (member.size < 2 * MIN_OWN) {
            val m = synchronized(this) { mask.copyOf() }
            for (t in tracker.alive().takeLast(tracker.topUp(40) { x, y -> atEroded(m, x, y) })) member.add(t.id)
        }
        if (prev < 0) synchronized(this) { for (t in live) if (at(mask, t.lastX(), t.lastY())) member.add(t.id) }
        // MobileSAM: the touch first, then again whenever it is free
        if (samOf() != null) {
            val box = if (!firstTried) promptBox() else currentBox(live)
            if (box != null) {
                if (threads) {
                    if (!samBusy && (!firstTried || System.currentTimeMillis() - lastSamEnd >= minSamGapMs)) {
                        samBusy = true; firstTried = true
                        val img = argb(); val f = frameNo
                        samExec.execute { try { runCatching { anchor(f, img, box) } } finally { lastSamEnd = System.currentTimeMillis(); samBusy = false } }
                    }
                } else if (!firstTried || !segmented || frameNo % syncEvery == 0) { firstTried = true; anchor(frameNo, argb(), box) }
            }
        }
        report()
    }

    private fun bbox(m: BooleanArray): FloatArray? {
        var x0 = Float.MAX_VALUE; var y0 = Float.MAX_VALUE; var x1 = -1f; var y1 = -1f
        for (y in 0 until gh) for (x in 0 until gw) if (m[y * gw + x]) { x0 = min(x0, x * 4f); y0 = min(y0, y * 4f); x1 = max(x1, x * 4f + 4); y1 = max(y1, y * 4f + 4) }
        return if (x1 < 0) null else floatArrayOf(x0, y0, x1, y1)
    }

    /** Median shift (and median ratio of distances to the centre, when [scale]): the robust low-order fit. */
    private fun shiftScale(p: List<FloatArray>, q: List<FloatArray>, scale: Boolean): Pair<Aff, BooleanArray>? {
        if (p.size < 3) return null
        val dx = p.indices.map { (q[it][0] - p[it][0]).toDouble() }.sorted()[p.size / 2]
        val dy = p.indices.map { (q[it][1] - p[it][1]).toDouble() }.sorted()[p.size / 2]
        val inl = BooleanArray(p.size) { abs(q[it][0] - p[it][0] - dx) + abs(q[it][1] - p[it][1] - dy) < 3.0 + 0.0 }
        var k = 1.0
        val cx = p.map { it[0].toDouble() }.average(); val cy = p.map { it[1].toDouble() }.average()
        if (scale) {
            val r = p.indices.mapNotNull { val d0 = hypot(p[it][0] - cx, p[it][1] - cy); if (d0 < 15) null else hypot(q[it][0] - cx - dx, q[it][1] - cy - dy) / d0 }.sorted()
            if (r.size >= 5) k = r[r.size / 2]
        }
        // x' = k (x - c) + c + d
        return Aff(k, 0.0, 0.0, k, (1 - k) * cx + dx, (1 - k) * cy + dy) to BooleanArray(p.size) { true }.also { inl.copyInto(it) }
    }

    /** A frame-to-frame motion a hand-held sweep can make (a wrong fit on a few points can jump or zoom). */
    private fun plausible(s: Aff): Boolean {
        val (lo, hi) = s.stretch()
        return lo > 0.85 && hi < 1.18 && hi / lo < 1.15 && abs(s.tx) < w * 0.25 && abs(s.ty) < h * 0.25
    }

    private fun report() {
        val m = synchronized(this) { Mask(gw, gh, mask.copyOf()) }
        val poly = if (m.area > 4) m.outline() else emptyList()
        val out = FloatArray(poly.size * 2) { if (it % 2 == 0) poly[it / 2].a / gw else poly[it / 2].b / gh }
        onUpdate(Update(out, member.size, anchors, lastSamMs, frame, segmented))
    }

    private fun promptBox(): FloatArray? {
        val p = prompt ?: return null
        return if (p.size == 4) floatArrayOf(p[0] * w, p[1] * h, p[2] * w, p[3] * h) else floatArrayOf(p[0] * w, p[1] * h)
    }

    /** Box of the carried mask and the tracked members together, grown by 10 %. */
    private fun currentBox(live: List<Track>): FloatArray? {
        var x0 = Float.MAX_VALUE; var y0 = Float.MAX_VALUE; var x1 = -1f; var y1 = -1f
        synchronized(this) {
            for (y in 0 until gh) for (x in 0 until gw) if (mask[y * gw + x]) {
                x0 = min(x0, x * 4f); y0 = min(y0, y * 4f); x1 = max(x1, x * 4f + 4); y1 = max(y1, y * 4f + 4)
            }
        }
        for (t in live) if (t.id in member) { x0 = min(x0, t.lastX()); y0 = min(y0, t.lastY()); x1 = max(x1, t.lastX()); y1 = max(y1, t.lastY()) }
        if (x1 < 0) return null
        val mx = 0.1f * (x1 - x0) + 6; val my = 0.1f * (y1 - y0) + 6
        return floatArrayOf(max(0f, x0 - mx), max(0f, y0 - my), min(w - 1f, x1 + mx), min(h - 1f, y1 + my))
    }

    private fun anchor(f: Int, img: IntArray, box: FloatArray) {
        val sam = samOf() ?: return
        val t0 = System.nanoTime()
        val e = sam.embed(img, w, h)
        val cands = if (box.size == 4) sam.boxAll(e, box[0], box[1], box[2], box[3]) else sam.tapRefined(e, box[0], box[1])
        lastSamMs = (System.nanoTime() - t0) / 1_000_000
        // the answer is for frame f: the tracking thread carries it to its frame with the motion since
        if (threads) pending = Answer(f, cands, shrink(img)) else mergeAnchor(f, cands, shrink(img))
    }

    /** The picture at the mask grid's cells. */
    private fun shrink(img: IntArray) = IntArray(gw * gh) { i -> img[min(h - 1, (i / gw) * 4 + 2) * w + min(w - 1, (i % gw) * 4 + 2)] }

    private fun mergeAnchor(f: Int, cands: List<Mask>, colour: IntArray) {
        if (closed) return
        var s = Aff.ID
        for (k in (f + 1)..frame) history[k]?.let { s = it.after(s) }
        val raw = cands.map { down(it) }
        val grids = raw.map { warp(it, s) }
        val cur = synchronized(this) { mask.copyOf() }
        val i: Int
        if (!segmented) {
            // the touch: the whole object; of SAM's answers the best-scoring that is not a speck nor most of the picture
            val ok = cands.indices.filter { grids[it].count { b -> b } in 6 until gw * gh / 2 }
            i = ok.maxByOrNull { cands[it].score } ?: return
        } else {
            val ious = grids.map { iou(it, cur) }
            i = ious.indices.maxBy { ious[it] }
            val g = grids[i]
            val mem = tracker.alive().filter { it.id in member }
            val cover = if (mem.isEmpty()) 1.0 else mem.count { at(g, it.lastX(), it.lastY()) }.toDouble() / mem.size
            trace?.invoke("anchor from f$f at f$frame: ious ${ious.joinToString { "%.2f".format(it) }} cover ${"%.2f".format(cover)} area ${g.count { it }} vs ${cur.count { it }}")
            if (ious[i] < 0.3 || cover < 0.6 || g.count { it } >= gw * gh / 2) return
        }
        synchronized(this) { base = largest(raw[i]); cum = s; mask = warp(base, cum) }
        colours = ColourModel.of(base, colour, gw, gh)
        anchors++
        val first = !segmented
        segmented = true
        if (first) member.clear()
        for (t in tracker.alive()) { if (atEroded(mask, t.lastX(), t.lastY())) member.add(t.id) else if (!at(mask, t.lastX(), t.lastY())) member.remove(t.id) }
        if (first) onFirstMask(f, cands[i].largestPart(), lastSamMs ?: 0)
    }

    private fun down(m: Mask): BooleanArray {
        val o = BooleanArray(gw * gh)
        for (y in 0 until gh) for (x in 0 until gw) o[y * gw + x] = m[(x * 4 + 2) * m.w / w, (y * 4 + 2) * m.h / h]
        return o
    }

    /** mask in -> mask out under the motion s (picture pixels); nearest, on the quarter grid. */
    private fun warp(m: BooleanArray, s: Aff): BooleanArray {
        val inv = s.inverse(); val o = BooleanArray(gw * gh)
        for (y in 0 until gh) for (x in 0 until gw) {
            val r = inv.apply(x * 4.0 + 2, y * 4.0 + 2)
            val sx = floor(r[0] / 4).toInt(); val sy = floor(r[1] / 4).toInt()
            if (sx in 0 until gw && sy in 0 until gh) o[y * gw + x] = m[sy * gw + sx]
        }
        return o
    }

    private fun largest(m: BooleanArray) = Mask(gw, gh, m).largestPart().bits
    private fun at(m: BooleanArray, x: Float, y: Float): Boolean { val gx = floor(x / 4).toInt(); val gy = floor(y / 4).toInt(); return gx in 0 until gw && gy in 0 until gh && m[gy * gw + gx] }
    private fun atEroded(m: BooleanArray, x: Float, y: Float) = at(m, x, y) && at(m, x - 6, y) && at(m, x + 6, y) && at(m, x, y - 6) && at(m, x, y + 6)
    private fun near(m: BooleanArray, x: Float, y: Float) = at(m, x - 8, y) || at(m, x + 8, y) || at(m, x, y - 8) || at(m, x, y + 8)
    private fun iou(a: BooleanArray, b: BooleanArray): Double { var i = 0; var u = 0; for (k in a.indices) { if (a[k] && b[k]) i++; if (a[k] || b[k]) u++ }; return if (u == 0) 0.0 else i.toDouble() / u }

    companion object {
        /** Fewer of the object's points than this: its motion is taken from the points round it. */
        const val MIN_OWN = 8
    }

    /** Stops both threads; a MobileSAM run in progress finishes but its answer is dropped. */
    fun close() { closed = true; samExec.shutdownNow() }
}

/**
 * Object and background colours (8 levels per channel) learnt from a MobileSAM answer; between answers they move the
 * carried mask's edges, within 3 cells of where they were, to where the picture says the object is.
 */
class ColourModel private constructor(private val obj: FloatArray, private val bg: FloatArray, private val gw: Int, private val gh: Int) {
    private fun bin(c: Int) = ((c shr 21) and 7) * 64 + ((c shr 13) and 7) * 8 + ((c shr 5) and 7)

    fun refine(m: BooleanArray, col: IntArray, band: Int = 3, prior: Float = 0.6f): BooleanArray? {
        val n = m.count { it }
        if (n < 12) return null
        val inner = erode(m, band); val outer = dilate(m, band)
        val o = m.copyOf()
        for (i in m.indices) if (outer[i] && !inner[i]) {
            val b = bin(col[i])
            o[i] = obj[b] - bg[b] + (if (m[i]) prior else -prior) > 0f
        }
        // 3 x 3 majority in the band, then the largest part with its holes filled
        val sm = o.copyOf()
        for (y in 0 until gh) for (x in 0 until gw) {
            val i = y * gw + x
            if (!outer[i] || inner[i]) continue
            var c = 0; var t = 0
            for (dy in -1..1) for (dx in -1..1) { val xx = x + dx; val yy = y + dy; if (xx in 0 until gw && yy in 0 until gh) { t++; if (o[yy * gw + xx]) c++ } }
            sm[i] = 2 * c > t
        }
        val big = Mask(gw, gh, sm).largestPart().bits
        val r = fillHoles(big)
        val a = r.count { it }
        return if (a in n / 2..n * 2) r else null
    }

    private fun erode(m: BooleanArray, r: Int): BooleanArray = dilate(BooleanArray(m.size) { !m[it] }, r).let { d -> BooleanArray(m.size) { !d[it] } }
    private fun dilate(m: BooleanArray, r: Int): BooleanArray = Mask(gw, gh, m).dilate(r).bits

    private fun fillHoles(m: BooleanArray): BooleanArray {
        val seen = BooleanArray(m.size); val q = IntArray(m.size); var t = 0
        for (x in 0 until gw) { for (y in intArrayOf(0, gh - 1)) { val i = y * gw + x; if (!m[i] && !seen[i]) { seen[i] = true; q[t++] = i } } }
        for (y in 0 until gh) { for (x in intArrayOf(0, gw - 1)) { val i = y * gw + x; if (!m[i] && !seen[i]) { seen[i] = true; q[t++] = i } } }
        var hd = 0
        while (hd < t) {
            val i = q[hd++]; val x = i % gw; val y = i / gw
            for ((nx, ny) in arrayOf(x - 1 to y, x + 1 to y, x to y - 1, x to y + 1)) if (nx in 0 until gw && ny in 0 until gh) {
                val j = ny * gw + nx; if (!m[j] && !seen[j]) { seen[j] = true; q[t++] = j }
            }
        }
        return BooleanArray(m.size) { !seen[it] }
    }

    companion object {
        /** From the mask [m] on its frame's colours [col]: inside it, and a ring up to 8 cells round it. */
        fun of(m: BooleanArray, col: IntArray, gw: Int, gh: Int): ColourModel {
            val ho = FloatArray(512); val hb = FloatArray(512)
            val ring = Mask(gw, gh, m).dilate(8).bits
            val tmp = ColourModel(ho, hb, gw, gh)
            var no = 0; var nb = 0
            for (i in m.indices) { val b = tmp.bin(col[i]); if (m[i]) { ho[b]++; no++ } else if (ring[i]) { hb[b]++; nb++ } }
            val a = 0.5f
            for (b in 0 until 512) { ho[b] = kotlin.math.ln((ho[b] + a) / (no + a * 512)); hb[b] = kotlin.math.ln((hb[b] + a) / (nb + a * 512)) }
            return tmp
        }
    }
}

/** NV21 -> ARGB, shrunk and turned upright to [ow] x [oh] (nearest). */
object Yuv {
    fun argb(nv21: ByteArray, sw: Int, sh: Int, rotation: Int, ow: Int, oh: Int): IntArray {
        val out = IntArray(ow * oh)
        val rot = ((rotation % 360) + 360) % 360
        val uw = if (rot == 90 || rot == 270) sh else sw; val uh = if (rot == 90 || rot == 270) sw else sh
        for (oy in 0 until oh) for (ox in 0 until ow) {
            val ux = ox * uw / ow; val uy = oy * uh / oh
            // upright (ux, uy) -> sensor (x, y)
            val x: Int; val y: Int
            when (rot) { 90 -> { x = uy; y = sh - 1 - ux }; 180 -> { x = sw - 1 - ux; y = sh - 1 - uy }; 270 -> { x = sw - 1 - uy; y = ux }; else -> { x = ux; y = uy } }
            val yy = (nv21[y * sw + x].toInt() and 255) - 16
            val vi = sw * sh + (y / 2) * sw + (x / 2) * 2
            val v = (nv21[vi].toInt() and 255) - 128; val u = (nv21[vi + 1].toInt() and 255) - 128
            val c = 1.164f * yy
            val r = (c + 1.596f * v).toInt().coerceIn(0, 255); val gg = (c - 0.392f * u - 0.813f * v).toInt().coerceIn(0, 255); val b = (c + 2.017f * u).toInt().coerceIn(0, 255)
            out[oy * ow + ox] = (0xFF shl 24) or (r shl 16) or (gg shl 8) or b
        }
        return out
    }
}
