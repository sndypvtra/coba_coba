package id.ukurpaket.app.photo

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.measure.convexHull
import id.ukurpaket.app.measure.dilate
import id.ukurpaket.app.measure.minAreaRect
import id.ukurpaket.app.measure.simplifyClosed
import kotlinx.serialization.Serializable
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.asin
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

/*
 * The photo mode (0.4.0): one still picture of an object on the floor -> its size, on a phone without ARCore and
 * without a working gyroscope (Urovo DT50). Android-free, so the PC tests run the same code.
 *
 * What is known for the picture: the lens (intrinsics, from Camera2), which way is up (the accelerometer while the phone
 * is still), the object's outline (MobileSAM, tap or box), and a depth map (Depth Anything V2). The depth model is only
 * asked for ONE number: how high the camera is above the floor around the object (the median over thousands of floor
 * pixels). Everything else is plain geometry with that number (single-view metrology), on the picture turned level
 * when the phone was held tilted sideways:
 *   - the floor is the plane `up . X = -h`; every floor pixel's ray meets it at a known point
 *   - the outline's lower edge stands on the floor: the near half of the footprint
 *   - its left and right sides are vertical edges: their bottoms are on the floor, their tops give the height H
 *   - its upper edge is the far edge of the top, at H: the far half of the footprint
 *   - footprint = smallest rectangle round both halves: the starting box
 *   - that box is then fitted to the whole silhouette (BoxFit, 0.4.3): position, turn, length, width and height moved
 *     until the box drawn into the picture covers the object's mask best (IoU)
 * Every size scales with h, so a wrong h scales the result and nothing else: that is what the per-phone calibration
 * corrects, with the courier's standing camera height learnt from the calibration photos. A carton fits its outline
 * almost exactly (IoU ~0,99, 6 outline corners); a gallon is fitted as a cylinder; a sack or a plant gets its outer box
 * and is flagged.
 */

/** Pinhole camera of an upright picture of [w] x [h] pixels. */
@Serializable
data class Intrinsics(val fx: Float, val fy: Float, val cx: Float, val cy: Float, val w: Int, val h: Int) {
    /** The same lens for the picture resized to [nw] x [nh]. */
    fun scaled(nw: Int, nh: Int) = Intrinsics(fx * nw / w, fy * nh / h, cx * nw / w, cy * nh / h, nw, nh)

    fun ray(x: Float, y: Float) = V3((x - cx) / fx, (y - cy) / fy, 1f)
    fun project(p: V3) = P2(fx * p.x / p.z + cx, fy * p.y / p.z + cy)

    companion object {
        /**
         * The lens of a camera stream of [sw] x [sh] (sensor orientation), turned upright by [rotation] (clockwise).
         * Camera2 scales the active array into the stream after a centred crop to the stream's shape. [intr]: the
         * factory calibration (fx, fy, cx, cy, s) in active-array pixels when the phone has one; otherwise the focal
         * length (mm) over the sensor's width (mm) gives fx, with the principal point in the middle.
         */
        fun fromCamera(focalMm: Float, sensorWmm: Float, pixelW: Int, activeW: Int, activeH: Int, intr: FloatArray?,
                       sw: Int, sh: Int, rotation: Int): Intrinsics {
            val cropW = min(activeW.toFloat(), activeH.toFloat() * sw / sh)
            val cropH = cropW * sh / sw
            val k = sw / cropW
            val fx: Float; val fy: Float; val cx: Float; val cy: Float
            if (intr != null && intr.size >= 4 && intr[0] > 0f && intr[1] > 0f) {
                fx = intr[0] * k; fy = intr[1] * k
                cx = (intr[2] - (activeW - cropW) / 2) * k; cy = (intr[3] - (activeH - cropH) / 2) * k
            } else {
                val f = focalMm / sensorWmm * pixelW * k
                fx = f; fy = f; cx = sw / 2f; cy = sh / 2f
            }
            return when (((rotation % 360) + 360) % 360) {
                90 -> Intrinsics(fy, fx, sh - cy, cx, sh, sw)
                180 -> Intrinsics(fx, fy, sw - cx, sh - cy, sw, sh)
                270 -> Intrinsics(fy, fx, cy, sw - cx, sh, sw)
                else -> Intrinsics(fx, fy, cx, cy, sw, sh)
            }
        }

        /**
         * 'Up' in the axes of the upright back-camera picture (x right, y down, z forward), from the accelerometer of a
         * still phone in its natural (portrait) orientation: it reads +g along the device's up. Device x is picture x,
         * device y is picture up, device z points out of the screen (the back camera looks the other way).
         */
        fun upFromAccel(ax: Float, ay: Float, az: Float): V3 = V3(ax, -ay, -az).unit()
    }
}

/** A depth map (metres along the optical axis) covering the whole picture, at the model's resolution. */
class DepthMap(val w: Int, val h: Int, val z: FloatArray) {
    /** Depth at a picture position given as fractions (0..1) of its width and height, bilinear. */
    fun at(fx: Float, fy: Float): Float {
        val x = (fx * w - 0.5f).coerceIn(0f, w - 1f); val y = (fy * h - 0.5f).coerceIn(0f, h - 1f)
        val x0 = x.toInt(); val y0 = y.toInt(); val x1 = min(x0 + 1, w - 1); val y1 = min(y0 + 1, h - 1)
        val ax = x - x0; val ay = y - y0
        return (z[y0 * w + x0] * (1 - ax) + z[y0 * w + x1] * ax) * (1 - ay) + (z[y1 * w + x0] * (1 - ax) + z[y1 * w + x1] * ax) * ay
    }
}

/** How high the camera is above the floor near the object, from the depth map. */
data class FloorEstimate(
    /** Camera height above the floor, metres, as the depth model's scale has it (before the phone's calibration). */
    val heightM: Float,
    /** Floor pixels that agree with the floor plane / pixels tried. */
    val inliers: Int, val tried: Int,
    /** Angle between the depth model's floor and the accelerometer's horizontal (degrees): large = inconsistent. */
    val tiltDeg: Float,
    /** Floor taken from the whole picture: too little floor round the object. */
    val wide: Boolean,
)

/** One photo's answer. Sizes in cm, after the phone's calibration [scale]. */
@Serializable
data class PhotoResult(
    val lengthCm: Double, val widthCm: Double, val heightCm: Double,
    /** The same three before calibration (scale 1): what calibration samples are compared with. */
    val rawCm: List<Double>,
    val scale: Double,
    val cameraHeightM: Double,
    /** Camera looking down this many degrees below the horizon. */
    val downDeg: Double,
    /** Box drawn from the result vs the object's outline. */
    val iou: Double,
    /** The outline is a box's (IoU high): the result can be "Akurat"; otherwise a rough size of an irregular object. */
    val boxLike: Boolean,
    /** 8 corners (floor 0-3, top 4-7) as fractions of the picture, x then y: for drawing the box on the photo. */
    val corners: List<Float>,
    val confidence: Int,
    val ok: Boolean,
    val notes: List<String>,
    val floorInliers: Int = 0,
    val floorTiltDeg: Double = 0.0,
    /** The camera height the depth model gave (after the phone's factor), metres. */
    val aiCameraM: Double = 0.0,
    /** The courier's standing camera height it was combined with (0 = not used), metres. */
    val standingM: Double = 0.0,
    /** The camera height the autofocus gave (0 = not used), metres, and the distance it focused at. */
    val focusCameraM: Double = 0.0,
    val focusDistanceM: Double = 0.0,
    /** What calibration needs from the photo: the diopters the camera reported, and the depth of the autofocus point per
     *  metre of camera height (from the box's geometry); 0 = none. */
    val focusDiopters: Double = 0.0,
    val focusDepthUnit: Double = 0.0,
)

class PhotoFailed(message: String) : Exception(message)

object PhotoMeasure {
    /** The fitted box must cover the outline this well (IoU) to count as box-like... */
    const val BOX_IOU = 0.90

    /** ...and the outline have at most this many corners (a box seen from a corner has 6; a gallon's round ends 9+). */
    const val MAX_BOX_CORNERS = 8

    /** A cylinder must beat the best box by this much IoU to be taken as the shape. */
    const val ROUND_MARGIN = 0.01f

    /**
     * Camera height above the floor from the depth map: floor candidates are the pixels round the object (a window
     * 0,8 x its size on every side, outside the object grown by 3 % of the picture), below the horizon; a plane within
     * 20 deg of level is found among them (RANSAC); the height is the median, over its inliers, of how far below the
     * camera each one lies along 'up'.
     */
    fun floor(depth: DepthMap, mask: Mask, k: Intrinsics, up: V3, seed: Long = 7): FloorEstimate {
        val b = mask.bounds() ?: throw PhotoFailed("Objek belum dipilih")
        val bw = b[2] - b[0] + 1; val bh = b[3] - b[1] + 1
        val grow = max(2, (0.03f * mask.w).toInt())
        val grown = growMask(mask, grow)
        fun collect(x0: Int, y0: Int, x1: Int, y1: Int, step: Int): Pair<ArrayList<V3>, ArrayList<V3>> {
            val pts = ArrayList<V3>(); val rays = ArrayList<V3>()
            var y = y0
            while (y < y1) {
                var x = x0
                while (x < x1) {
                    if (!grown.bits[y * mask.w + x]) {
                        val r = k.ray(x + 0.5f, y + 0.5f)
                        if (-(r dot up) > 0.05f) {
                            val z = depth.at((x + 0.5f) / mask.w, (y + 0.5f) / mask.h)
                            if (z in 0.05f..30f) { pts.add(r * z); rays.add(r) }
                        }
                    }
                    x += step
                }
                y += step
            }
            return pts to rays
        }
        val step = max(1, mask.w / 240)
        var wide = false
        var (pts, rays) = collect(max(0, (b[0] - 0.8f * bw).toInt()), max(0, (b[1] - 0.8f * bh).toInt()),
            min(mask.w, (b[2] + 0.8f * bw).toInt() + 1), min(mask.h, (b[3] + 0.8f * bh).toInt() + 1), step)
        if (pts.size < 400) { wide = true; collect(0, 0, mask.w, mask.h, step).let { pts = it.first; rays = it.second } }
        if (pts.size < 50) throw PhotoFailed("Lantai tidak terlihat: foto dari atas agak miring, lantai kelihatan di sekeliling paket")

        // RANSAC on a sample of at most 6000 points, then inliers on all of them
        val rnd = java.util.Random(seed)
        val sample = if (pts.size <= 6000) pts.indices.toList() else List(6000) { rnd.nextInt(pts.size) }
        val cosMax = cos(20.0 * PI / 180).toFloat()
        var bestN = -1; var bestNormal = up; var bestD = 0f
        repeat(300) {
            val a = pts[sample[rnd.nextInt(sample.size)]]; val c = pts[sample[rnd.nextInt(sample.size)]]; val e = pts[sample[rnd.nextInt(sample.size)]]
            var n = (c - a) cross (e - a)
            val nn = n.norm(); if (nn < 1e-9f) return@repeat
            n = n * (1f / nn); if ((n dot up) < 0) n = n * -1f
            if ((n dot up) < cosMax) return@repeat
            val d = -(n dot a)
            var cnt = 0
            for (i in sample) { val p = pts[i]; if (abs((n dot p) + d) < 0.015f * max(1f, p.z)) cnt++ }
            if (cnt > bestN) { bestN = cnt; bestNormal = n; bestD = d }
        }
        val hs = ArrayList<Float>()
        if (bestN > 0) {
            for (i in pts.indices) { val p = pts[i]; if (abs((bestNormal dot p) + bestD) < 0.015f * max(1f, p.z)) hs.add(-(rays[i] dot up) * p.z) }
        }
        val tilt: Float
        if (hs.size < 30) {                      // no level plane: the median over every candidate
            hs.clear(); for (i in pts.indices) hs.add(-(rays[i] dot up) * pts[i].z)
            tilt = 90f
        } else tilt = Math.toDegrees(kotlin.math.acos((bestNormal dot up).toDouble().coerceIn(-1.0, 1.0))).toFloat()
        hs.sort()
        return FloorEstimate(hs[hs.size / 2], hs.size, pts.size, tilt, wide)
    }

    /**
     * The object's box from its outline, given the camera height [hM] above the floor. Returns the size (metres), the
     * box's 8 corners in camera axes, and the IoU of the box drawn with the outline.
     */
    class Metrology(val lengthM: Float, val widthM: Float, val heightM: Float, val corners: List<V3>, val iou: Float, val sideAlign: Float,
                    /** Read as an object lying flat (a phone, a mailer bag): its thickness is the uncertain part. */
                    val flat: Boolean = false,
                    /** A box explains the outline (fit IoU and straight sides): otherwise the size is the object's outer box. */
                    val boxLike: Boolean = true,
                    /** Corners of the simplified outline: 4-7 for a box, more for round or soft shapes. */
                    val outlineCorners: Int = 0,
                    /** A standing cylinder fits better than a box: the size is its outer box (diameter x diameter x height). */
                    val round: Boolean = false) {
        fun withCorners(c: List<V3>) = Metrology(lengthM, widthM, heightM, c, iou, sideAlign, flat, boxLike, outlineCorners, round)
    }

    /** A projected corner behind the camera (PhotoResult.corners): its edges are not drawn. */
    const val BEHIND = -100f

    /** Thicknesses tried for an object lying flat (metres, for a camera 0,6 m up; scaled with the camera's height). */
    private val FLAT_H = floatArrayOf(0.005f, 0.01f, 0.015f, 0.02f, 0.03f, 0.04f, 0.05f, 0.06f, 0.08f)

    /**
     * Thinner than this reads as lying flat (its thickness only roughly known): 4 cm, less close up, where one view
     * resolves thickness better (a cigarette pack 1,5 cm thick shot from 7 cm is a box, not a flat thing).
     */
    fun flatBelow(hM: Float) = min(0.04f, 0.05f * hM)

    /** Below this roll (degrees) the picture is measured as it is. */
    private const val ROLL_MIN_DEG = 1.5

    /**
     * The picture as a camera turned about its optical axis would have taken it, so that 'up' points straight up in it:
     * a phone held tilted sideways, even in landscape, then reads like an upright one (the outline's lower edge is
     * the one standing on the floor, its leftmost and rightmost points are on its sides). The mask is resampled
     * (nearest pixel) into a canvas holding the whole picture, at the same resolution; [toOriginal] turns a point of
     * the new camera back into the phone's.
     */
    class Levelled(val mask: Mask, val k: Intrinsics, val up: V3, val rollDeg: Float, private val c: Float, private val s: Float) {
        fun toOriginal(p: V3) = V3(c * p.x - s * p.y, s * p.x + c * p.y, p.z)
    }

    /** [mask] seen from the camera rolled level ('up' straight up in the picture); null when it already is. */
    fun level(mask: Mask, k: Intrinsics, up: V3): Levelled? {
        val roll = kotlin.math.atan2(up.x, -up.y)
        if (abs(Math.toDegrees(roll.toDouble())) < ROLL_MIN_DEG) return null
        val c = cos(roll); val s = kotlin.math.sin(roll)
        // new camera = old turned by -roll about z: x' = c x + s y, y' = -s x + c y (normalised coordinates)
        val f = (k.fx + k.fy) / 2
        var minX = Float.MAX_VALUE; var minY = Float.MAX_VALUE; var maxX = -Float.MAX_VALUE; var maxY = -Float.MAX_VALUE
        for ((px, py) in listOf(0f to 0f, k.w.toFloat() to 0f, 0f to k.h.toFloat(), k.w.toFloat() to k.h.toFloat())) {
            val nx = (px - k.cx) / k.fx; val ny = (py - k.cy) / k.fy
            val x = f * (c * nx + s * ny); val y = f * (-s * nx + c * ny)
            minX = min(minX, x); maxX = max(maxX, x); minY = min(minY, y); maxY = max(maxY, y)
        }
        val w = ceil(maxX - minX).toInt(); val h = ceil(maxY - minY).toInt()
        val nk = Intrinsics(f, f, -minX, -minY, w, h)
        val bits = BooleanArray(w * h)
        for (y in 0 until h) for (x in 0 until w) {
            val nx = (x + 0.5f - nk.cx) / f; val ny = (y + 0.5f - nk.cy) / f
            val ox = k.fx * (c * nx - s * ny) + k.cx; val oy = k.fy * (s * nx + c * ny) + k.cy
            bits[y * w + x] = mask[ox, oy]
        }
        val nu = V3(c * up.x + s * up.y, -s * up.x + c * up.y, up.z)
        return Levelled(Mask(w, h, bits), nk, nu, Math.toDegrees(roll.toDouble()).toFloat(), c, s)
    }

    fun metrology(mask: Mask, k: Intrinsics, up: V3, hM: Float, forceH: Float? = null, trace: ((String) -> Unit)? = null): Metrology {
        val lv = level(mask, k, up) ?: return metrologyLevel(mask, k, up, hM, forceH, trace)
        trace?.invoke("picture levelled: phone rolled %.0f deg".format(java.util.Locale.US, lv.rollDeg))
        val m = metrologyLevel(lv.mask, lv.k, lv.up, hM, forceH, trace)
        return m.withCorners(m.corners.map { lv.toOriginal(it) })
    }

    private fun metrologyLevel(mask: Mask, k: Intrinsics, up: V3, hM: Float, forceH: Float?, trace: ((String) -> Unit)?): Metrology {
        // the outline: convex hull of the mask's pixel corners
        val pts = ArrayList<P2>()
        for (y in 0 until mask.h) {
            var x0 = -1; var x1 = -1
            for (x in 0 until mask.w) if (mask.bits[y * mask.w + x]) { if (x0 < 0) x0 = x; x1 = x }
            if (x0 >= 0) { pts += P2(x0.toFloat(), y.toFloat()); pts += P2(x0.toFloat(), y + 1f); pts += P2(x1 + 1f, y.toFloat()); pts += P2(x1 + 1f, y + 1f) }
        }
        if (pts.size < 8) throw PhotoFailed("Objek terlalu kecil di foto: dekati paketnya")
        val hull = convexHull(pts)
        if (hull.size < 3) throw PhotoFailed("Objek terlalu kecil di foto: dekati paketnya")
        val dense = densify(hull, 2f)
        var peri = 0f
        for (i in hull.indices) { val a = hull[i]; val c = hull[(i + 1) % hull.size]; peri += hypot(c.a - a.a, c.b - a.b) }
        val simp = simplifyClosed(hull, 0.012f * peri).let { if (it.size >= 3) it else hull }
        trace?.invoke("outline: ${hull.size} hull points, ${simp.size} corners")

        class Side(val align: Float, val hM: Float, val bot: P2, val top: P2)
        fun side(iExt: Int): Side? {
            var best: Side? = null
            val m = simp.size
            for (j in intArrayOf((iExt - 1 + m) % m, (iExt + 1) % m)) {
                val p = simp[iExt]; val q = simp[j]
                val (bot, top) = if (p.b >= q.b) p to q else q to p
                val bp = onPlane(k, up, bot.a, bot.b, hM) ?: continue
                val v0 = k.project(bp); val v1 = k.project(bp + up * 0.1f)
                val vl = hypot(v1.a - v0.a, v1.b - v0.b); if (vl < 1e-6f) continue
                val ex = top.a - bot.a; val ey = top.b - bot.b; val el = hypot(ex, ey)
                if (el < 3f) continue
                val al = ((v1.a - v0.a) * ex + (v1.b - v0.b) * ey) / (vl * el)
                val hh = heightOnVertical(k, up, bp, top)
                if (best == null || al > best.align) best = Side(al, hh, bot, top)
            }
            return best
        }
        val il = simp.indices.minBy { simp[it].a }; val ir = simp.indices.maxBy { simp[it].a }
        val sl = side(il); val sr = side(ir)
        fun nearest(p: P2) = dense.indices.minBy { (dense[it].a - p.a).let { d -> d * d } + (dense[it].b - p.b).let { d -> d * d } }
        fun path(i0: Int, j: Int): List<Int> { val out = ArrayList<Int>(); var i = i0; out += i; while (i != j) { i = (i + 1) % dense.size; out += i }; return out }
        val bl = nearest(sl?.bot ?: simp[il]); val tl = nearest(sl?.top ?: simp[il])
        val br = nearest(sr?.bot ?: simp[ir]); val tr = nearest(sr?.top ?: simp[ir])
        val p1 = path(bl, br); val p2 = path(br, bl)
        val sideLower = if (p1.map { dense[it].b }.average() > p2.map { dense[it].b }.average()) p1 else p2
        val q1 = path(tl, tr); val q2 = path(tr, tl)
        val sideUpper = if (q1.map { dense[it].b }.average() < q2.map { dense[it].b }.average()) q1 else q2

        // plane axes for the footprint
        val ax = (up cross (if (abs(up.x) < 0.9f) V3(1f, 0f, 0f) else V3(0f, 0f, 1f))).unit()
        val ay = (up cross ax).unit()
        val origin = up * -hM

        // an object lying flat has no tall sides: what looked like a side is an edge of its top. Its outline splits at its
        // leftmost and rightmost points instead, the lower part on the floor, the upper part at its (small) thickness
        val fl0 = dense.indices.minBy { dense[it].a }; val fr0 = dense.indices.maxBy { dense[it].a }
        val f1 = path(fl0, fr0); val f2 = path(fr0, fl0)
        val flatLower = if (f1.map { dense[it].b }.average() > f2.map { dense[it].b }.average()) f1 else f2
        val flatUpper = if (flatLower === f1) f2 else f1

        fun footprint(H: Float, lower: List<Int> = sideLower, upper: List<Int> = sideUpper): Pair<FloatArray, List<P2>>? {
            val q = ArrayList<P2>()
            for (i in lower) onPlane(k, up, dense[i].a, dense[i].b, hM)?.let { p -> val d = p - origin; q += P2(d dot ax, d dot ay) }
            if (hM - H > 0.03f * hM) for (i in upper) onPlane(k, up, dense[i].a, dense[i].b, hM - H)?.let { p ->
                val d = p - origin; q += P2(d dot ax, d dot ay) }
            if (q.size < 3) return null
            val hq = convexHull(q); if (hq.size < 3) return null
            val r = minAreaRect(hq)
            val o = r.corners[0]
            val ux = P2(r.corners[1].a - o.a, r.corners[1].b - o.b).let { val n = hypot(it.a, it.b); if (n < 1e-6f) P2(1f, 0f) else P2(it.a / n, it.b / n) }
            val uy = P2(-ux.b, ux.a)
            val us = FloatArray(q.size) { (q[it].a - o.a) * ux.a + (q[it].b - o.b) * ux.b }.apply { sort() }
            val vs = FloatArray(q.size) { (q[it].a - o.a) * uy.a + (q[it].b - o.b) * uy.b }.apply { sort() }
            val u0 = pct(us, 0.005f); val u1 = pct(us, 0.995f); val v0 = pct(vs, 0.005f); val v1 = pct(vs, 0.995f)
            fun at(u: Float, v: Float) = P2(o.a + ux.a * u + uy.a * v, o.b + ux.b * u + uy.b * v)
            return floatArrayOf(u1 - u0, v1 - v0) to listOf(at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1))
        }
        fun corners(rect: List<P2>, H: Float): List<V3> =
            rect.map { origin + ax * it.a + ay * it.b } + rect.map { origin + ax * it.a + ay * it.b + up * H }

        val cands = LinkedHashSet<Float>()
        for (s in listOf(sl, sr)) if (s != null && s.hM > 0.005f) cands += s.hM
        if (cands.size == 2) cands += cands.average().toFloat()
        if (forceH != null) { cands.clear(); cands += forceH }
        if (cands.isEmpty() && forceH != null) throw PhotoFailed("Tinggi objek tidak terbaca: foto dari pojok paket, agak dari atas")
        val align = listOfNotNull(sl?.align, sr?.align).minOrNull() ?: 0f
        var upright: Metrology? = null
        for (H in cands) {
            val f = footprint(H) ?: continue
            val cs = corners(f.second, H)
            val iou = silhouetteIou(cs, k, mask)
            trace?.invoke("upright H %.1f cm -> %.1f x %.1f, IoU %.3f".format(java.util.Locale.US, H * 100, f.first.max() * 100, f.first.min() * 100, iou))
            if (upright == null || iou > upright.iou) upright = Metrology(max(f.first[0], f.first[1]), min(f.first[0], f.first[1]), H, cs, iou, align)
        }
        // the same outline read as an object lying flat
        var flat: Metrology? = null
        if (forceH == null) for (H0 in FLAT_H) {
            val H = H0 * hM / 0.6f
            if (H > 0.8f * hM) break
            val f = footprint(H, flatLower, flatUpper) ?: continue
            val cs = corners(f.second, H)
            val iou = silhouetteIou(cs, k, mask)
            trace?.invoke("flat H %.1f cm -> %.1f x %.1f, IoU %.3f".format(java.util.Locale.US, H * 100, f.first.max() * 100, f.first.min() * 100, iou))
            if (flat == null || iou > flat.iou) flat = Metrology(max(f.first[0], f.first[1]), min(f.first[0], f.first[1]), H, cs, iou, align, flat = true)
        }
        if (upright == null && flat == null) throw PhotoFailed("Ukuran tidak terbaca dari foto ini: ulangi dari sudut lain")

        // both readings are only starting points: the box is then fitted to the whole silhouette (BoxFit), and the
        // better fit wins. A few centimetres high, whichever won: a thickness the outline only hints at (flat)
        val sil = Silhouette(mask)
        var best: Pair<FloorBox, Float>? = null
        var bestAlign = align
        for ((name, m0) in listOf("upright" to upright, "flat" to flat)) {
            if (m0 == null) continue
            val b0 = FloorBox.of(m0.corners.take(4), m0.heightM, ax, ay, up, hM)
            val iou0 = sil.iou(BoxFit.silhouette(m0.corners, k))
            val (b, iou) = BoxFit.refine(b0, sil, k, up, hM, ax, ay, fixH = forceH)
            trace?.invoke("fit from %s: %.1f x %.1f x %.1f cm, IoU %.3f -> %.3f".format(java.util.Locale.US, name, max(b.l, b.w) * 100,
                min(b.l, b.w) * 100, b.hgt * 100, iou0, iou))
            val pick = if (iou > iou0) b to iou else b0 to iou0
            if (best == null || pick.second > best.second) { best = pick; bestAlign = m0.sideAlign }
        }
        var (box, iou) = best!!
        // a standing cylinder instead (gallon, bottle, bucket): kept when it fits clearly better than any box
        var round = false
        if (forceH == null) {
            val (c, ci) = BoxFit.cylinder(box, sil, k, up, hM, ax, ay)
            trace?.invoke("cylinder: %.1f cm across, %.1f cm tall, IoU %.3f (box %.3f)".format(java.util.Locale.US, c.l * 100, c.hgt * 100, ci, iou))
            if (ci > iou + ROUND_MARGIN) { box = c; iou = ci; round = true }
        }
        // a box explains the outline when it fits it closely and the outline has a box's few straight sides; a soft or
        // irregular object (sack, plant) is measured by its outer box instead, the size its volumetric weight uses
        val boxLike = !round && iou >= BOX_IOU && simp.size <= MAX_BOX_CORNERS
        if (!boxLike && !round && forceH == null) {
            // one view cannot tell how far a soft shape bulges where it is not seen: the smallest box whose silhouette
            // covers it is a lower bound, and so is the box read from the outline's edges (its lower edge projected on
            // the floor reaches out under the bulge). Each side is the larger of the two: the outer box, rough
            var (o, oi) = BoxFit.cover(box, sil, k, up, hM, ax, ay)
            val first = listOfNotNull(upright, flat).maxBy { it.iou }
            val longAxis = o.l >= o.w
            // the outline's edges can also be read badly (a cap, a handle): never more than 30 % beyond the covering box
            fun outer(a: Float, b: Float) = max(a, min(b, 1.3f * a))
            val l = outer(max(o.l, o.w), first.lengthM); val w = outer(min(o.l, o.w), first.widthM); val hh = outer(o.hgt, first.heightM)
            o = FloorBox(o.u, o.v, o.yaw, if (longAxis) l else w, if (longAxis) w else l, hh)
            oi = sil.iou(BoxFit.silhouette(o.corners(ax, ay, up, hM), k))
            trace?.invoke("outer box (%d corners, IoU %.3f): %.1f x %.1f x %.1f cm, IoU %.3f".format(java.util.Locale.US, simp.size, iou,
                max(o.l, o.w) * 100, min(o.l, o.w) * 100, o.hgt * 100, oi))
            box = o; iou = oi
        }
        return Metrology(max(box.l, box.w), min(box.l, box.w), box.hgt, box.corners(ax, ay, up, hM), iou, bestAlign,
            flat = box.hgt < flatBelow(hM), boxLike = boxLike, outlineCorners = simp.size, round = round)
    }

    /**
     * One photo: floor -> camera height -> metrology -> checks. [scale]: this phone's calibration (1 = none yet).
     * [mask] and [k] at the same resolution.
     */
    /** How much the depth model's camera height is trusted after calibration (relative standard deviation)... */
    const val SIGMA_AI = 0.12

    /** ...and close up (camera under 0,6 m), where the depth models read far too much (4-14x on the first close-ups). */
    const val SIGMA_AI_CLOSE = 0.5

    /** How precisely the autofocus finds a distance, in real diopters (1 / metres): 0,15 D is 1,5 % at 10 cm, 15 % at 1 m. */
    const val FOCUS_SIGMA_D = 0.15

    /** Which clues the camera height came from. */
    data class HeightPick(val heightM: Float, val ai: Boolean, val standing: Boolean, val focus: Boolean)

    /**
     * The camera height for the measurement from up to three clues, each a scale error of its own, combined in log space
     * weighted by how much each is trusted: the depth model's [hAi]; the autofocus's [hFocus] (relative error
     * [sigmaFocus]: small close up, large far away); the courier's standing camera height [standing] learnt from the
     * calibration photos. The lens is a physical measurement and the depth model a guess: when the two disagree beyond
     * what both allow, the guess is dropped. The standing height joins only within a factor 1,43 of the others (not when
     * crouching or with the parcel on a table).
     */
    fun cameraHeight(hAi: Float, standing: Standing?, hFocus: Float? = null, sigmaFocus: Double = 0.0): HeightPick {
        val sAi = if (hAi < 0.6f) SIGMA_AI_CLOSE else SIGMA_AI
        val clues = ArrayList<Pair<Double, Double>>()                // ln height, sigma
        var useAi = true
        if (hFocus != null && hFocus > 0f) {
            val sf = max(0.01, sigmaFocus)
            if (abs(kotlin.math.ln(hAi.toDouble() / hFocus)) > 3 * kotlin.math.sqrt(sAi * sAi + sf * sf)) useAi = false
            clues += kotlin.math.ln(hFocus.toDouble()) to sf
        }
        if (useAi) clues += kotlin.math.ln(hAi.toDouble()) to sAi
        fun mean() = clues.sumOf { it.first / (it.second * it.second) } / clues.sumOf { 1 / (it.second * it.second) }
        var m = mean()
        var useSt = false
        if (standing != null && abs(kotlin.math.ln(standing.heightM) - m) < kotlin.math.ln(1.43)) {
            clues += kotlin.math.ln(standing.heightM) to max(0.05, standing.spread / 2); useSt = true; m = mean()
        }
        return HeightPick(kotlin.math.exp(m).toFloat(), useAi, useSt, hFocus != null && hFocus > 0f)
    }

    /**
     * One photo: floor -> camera height (depth model, autofocus, standing height) -> metrology -> checks.
     * [focus]: the autofocus when the photo was taken; [focusCal]: how its diopters turn into real ones (null: not used).
     */
    fun measure(mask: Mask, k: Intrinsics, up: V3, depth: DepthMap, scale: Float, calibrated: Boolean, standing: Standing? = null,
                focus: FocusInfo? = null, focusCal: FocusCal? = null): PhotoResult {
        require(mask.w == k.w && mask.h == k.h) { "mask and intrinsics differ in size" }
        val b = mask.bounds() ?: throw PhotoFailed("Objek belum dipilih")
        val area = mask.bits.count { it }
        if (area < mask.w * mask.h * 0.004f) throw PhotoFailed("Objek terlalu kecil di foto: dekati paketnya")
        val downDeg = Math.toDegrees(asin((-up.z).toDouble().coerceIn(-1.0, 1.0)))
        if (downDeg < 8) throw PhotoFailed("HP terlalu tegak: arahkan kamera miring ke bawah (30–60°)")
        val fl = floor(depth, mask, k, up)
        val hAi = fl.heightM * scale
        var met = metrology(mask, k, up, hAi)
        // the autofocus: how far the lens says the middle of the picture is; the box's geometry says how far that is
        // per metre of camera height, so the two give the camera height. The shape does not depend on the height.
        val zUnit = focusDepth(met.corners, up, hAi, k)?.div(hAi)
        val focusOk = focus != null && focus.usable()
        var hFocus: Float? = null; var sFocus = 0.0; var dTrue = 0.0
        if (zUnit != null && focusOk && focusCal != null) {
            dTrue = focusCal.factor * focus!!.diopters
            hFocus = (1.0 / dTrue / zUnit).toFloat(); sFocus = kotlin.math.sqrt((FOCUS_SIGMA_D / dTrue).let { it * it } + focusCal.sigma * focusCal.sigma)
        }
        val pick = cameraHeight(hAi, standing, hFocus, sFocus)
        val h = pick.heightM
        if (abs(kotlin.math.ln(h / hAi)) > 0.03f) met = metrology(mask, k, up, h)
        val notes = ArrayList<String>()
        var conf = 100.0
        if (pick.focus && !pick.ai) notes += "Jarak dari fokus kamera (${"%.2f".format(1 / dTrue)} m); tebakan AI (kamera ${"%.2f".format(hAi)} m) beda jauh, tidak dipakai"
        if (standing != null && !pick.standing) {
            notes += "Tinggi kamera tidak seperti saat kalibrasi (${"%.2f".format(h)} m, biasanya ${"%.2f".format(standing.heightM)} m): foto sambil berdiri, HP setinggi dada"
            conf -= 15
        }
        if (!pick.focus && hAi < 0.6f) { notes += "Foto terlalu dekat: AI kurang akurat dari dekat. Mundur, foto sambil berdiri"; conf -= 15 }
        // touching (or nearly touching) the picture's edge: part of the parcel may be outside it
        val margin = max(2, (0.012f * max(mask.w, mask.h)).toInt())
        val touches = b[0] < margin || b[1] < margin || b[2] >= mask.w - margin || b[3] >= mask.h - margin
        if (touches) { notes += "Paket terpotong atau terlalu mepet tepi foto: mundur sedikit supaya paket utuh dengan lantai di sekelilingnya"; conf -= 35 }
        if (met.flat) { notes += "Benda pipih: panjang × lebar terbaca, tebalnya hanya perkiraan (bisa meleset 1–3 cm)"; conf -= 15 }
        val boxLike = met.boxLike
        if (met.round) { notes += "Bentuk bulat (seperti galon): ukuran kotak terluarnya, diameter × diameter × tinggi"; conf -= 25 }
        else if (!boxLike) { notes += "Bentuk tidak seperti kotak: ukuran kotak terluarnya (dipakai untuk berat volumetrik)"; conf -= 25 }
        else conf -= (0.97 - met.iou).coerceAtLeast(0.0) * 150
        if (downDeg < 25 || downDeg > 72) { notes += "Sudut foto ${downDeg.toInt()}°: paling pas 30–60° ke bawah"; conf -= 10 }
        // a camera a few centimetres up is real close up when the focus says so; from the depth model alone it is not
        if (h < (if (pick.focus) 0.03f else 0.25f) || h > 2.2f) { notes += "Jarak kamera ke lantai tidak wajar (${"%.2f".format(h)} m): ulangi foto"; conf -= 30 }
        if (met.heightM > h - max(0.01f, 0.06f * h)) { notes += "Kamera kurang tinggi dari paket: foto dari lebih atas"; conf -= 20 }
        if (fl.wide || fl.inliers < 300) { notes += "Lantai di sekitar paket kurang terlihat"; conf -= 15 }
        if (fl.tiltDeg > 15) { notes += "Lantai tidak terbaca rata"; conf -= 15 }
        if (!calibrated) { notes += "Mode foto belum dikalibrasi di HP ini: angka bisa meleset jauh"; conf = min(conf, 60.0) }
        val c = conf.toInt().coerceIn(0, 100)
        // the same sizes at the depth model's own height (no factor, no other clue): what calibration compares with
        val raw = listOf(met.lengthM, met.widthM, met.heightM).map { it * 100.0 * fl.heightM / h }
        // fractions of the picture, kept even far outside it (the drawing clips); a corner behind the camera is BEHIND
        val proj = met.corners.flatMap { p ->
            if (p.z > 0.01f) k.project(p).let { listOf((it.a / k.w).coerceIn(-20f, 20f), (it.b / k.h).coerceIn(-20f, 20f)) } else listOf(BEHIND, BEHIND)
        }
        return PhotoResult(met.lengthM * 100.0, met.widthM * 100.0, met.heightM * 100.0, raw, scale.toDouble(), h.toDouble(), downDeg,
            met.iou.toDouble(), boxLike, proj, c, ok = calibrated && boxLike && !touches && !met.flat && c >= 75, notes = notes,
            floorInliers = fl.inliers, floorTiltDeg = fl.tiltDeg.toDouble(), aiCameraM = hAi.toDouble(),
            standingM = if (pick.standing) standing!!.heightM else 0.0,
            focusCameraM = if (pick.focus) hFocus!!.toDouble() else 0.0, focusDistanceM = if (pick.focus) 1 / dTrue else 0.0,
            focusDiopters = if (focusOk) focus!!.diopters.toDouble() else 0.0, focusDepthUnit = zUnit?.toDouble() ?: 0.0)
    }

    /** Several photos of one object: the median of each side; a spread over 10 % is flagged. */
    fun combine(rs: List<PhotoResult>): PhotoResult {
        require(rs.isNotEmpty())
        if (rs.size == 1) return rs[0]
        fun med(v: List<Double>) = v.sorted().let { if (it.size % 2 == 1) it[it.size / 2] else (it[it.size / 2 - 1] + it[it.size / 2]) / 2 }
        val l = med(rs.map { it.lengthCm }); val w = med(rs.map { it.widthCm }); val h = med(rs.map { it.heightCm })
        val spread = rs.maxOf { r -> maxOf(abs(r.lengthCm - l) / l, abs(r.widthCm - w) / w, abs(r.heightCm - h) / h) }
        val notes = LinkedHashSet<String>()
        rs.forEach { notes.addAll(it.notes) }
        if (spread > 0.10) notes += "Hasil antar foto beda ${(spread * 100).toInt()}%: tambah foto dari pojok lain"
        val boxLike = rs.count { it.boxLike } * 2 > rs.size
        val conf = (rs.map { it.confidence }.average() - max(0.0, spread - 0.05) * 200).toInt().coerceIn(0, 100)
        val best = rs.maxBy { it.confidence }
        return best.copy(lengthCm = l, widthCm = w, heightCm = h, cameraHeightM = med(rs.map { it.cameraHeightM }), aiCameraM = med(rs.map { it.aiCameraM }),
            rawCm = listOf(med(rs.map { it.rawCm[0] }), med(rs.map { it.rawCm[1] }), med(rs.map { it.rawCm[2] })),
            boxLike = boxLike, confidence = conf, ok = rs.all { it.ok } && spread <= 0.10 && conf >= 75, notes = notes.toList())
    }

    // ----------------------------------------------------------------------------------------------- geometry
    /** Where the ray through pixel (x, y) meets the level plane [below] metres under the camera. */
    fun onPlane(k: Intrinsics, up: V3, x: Float, y: Float, below: Float): V3? {
        val r = k.ray(x, y); val den = -(r dot up)
        if (den <= 1e-3f || below <= 0f) return null
        return r * (below / den)
    }

    /** H such that [b] + H·up lies on the ray through pixel [t] (least squares on s·r - H·up = b). */
    fun heightOnVertical(k: Intrinsics, up: V3, b: V3, t: P2): Float {
        val r = k.ray(t.a, t.b)
        val rr = r dot r; val ru = r dot up; val uu = up dot up
        val rb = r dot b; val ub = up dot b
        // [rr  -ru][s]   [rb]
        // [-ru  uu][H] = [-ub]
        val det = rr * uu - ru * ru
        if (abs(det) < 1e-9f) return 0f
        return (rr * -ub + ru * rb) / det
    }

    /**
     * Depth (metres along the optical axis) of what the picture shows at pixel ([x], [y]): the box [corners] (camera
     * axes, floor 0-3 and top 4-7) where the ray meets it, else the floor `up . X = -hM`; null if it meets neither.
     */
    fun depthAt(corners: List<V3>, up: V3, hM: Float, k: Intrinsics, x: Float, y: Float): Float? {
        val r = k.ray(x, y)
        var best = Float.MAX_VALUE
        // the box by slabs along its three edges from corner 0 (the ray starts at the camera, the origin)
        val o = corners[0]
        var t0 = 0f; var t1 = Float.MAX_VALUE; var hit = true
        for (e in listOf(corners[1] - o, corners[3] - o, corners[4] - o)) {
            val l2 = e dot e
            if (l2 < 1e-12f) { hit = false; break }
            val ro = -(o dot e) / l2; val rd = (r dot e) / l2
            if (abs(rd) < 1e-12f) { if (ro < 0f || ro > 1f) { hit = false; break }; continue }
            var ta = -ro / rd; var tb = (1f - ro) / rd
            if (ta > tb) { val t = ta; ta = tb; tb = t }
            t0 = max(t0, ta); t1 = min(t1, tb)
            if (t0 > t1) { hit = false; break }
        }
        if (hit && t0 > 0f) best = t0
        val den = -(r dot up)
        if (den > 1e-4f) { val tf = hM / den; if (tf < best) best = tf }
        return if (best == Float.MAX_VALUE) null else best * r.z
    }

    /**
     * Depth of what the autofocus looks at: the median over the middle of the picture (±6 % of its width round the
     * centre, where continuous autofocus measures), of the box or the floor there.
     */
    fun focusDepth(corners: List<V3>, up: V3, hM: Float, k: Intrinsics): Float? {
        val d = ArrayList<Float>()
        val half = 0.06f * k.w
        for (i in -2..2) for (j in -2..2) depthAt(corners, up, hM, k, k.w / 2f + i * half / 2, k.h / 2f + j * half / 2)?.let { d += it }
        if (d.size < 5) return null
        d.sort(); return d[d.size / 2]
    }

    /** IoU of the convex hull of the projected corners with the mask. */
    fun silhouetteIou(corners: List<V3>, k: Intrinsics, mask: Mask): Float {
        if (corners.any { it.z < 0.03f }) return 0f
        val poly = convexHull(corners.map { k.project(it) })
        if (poly.size < 3) return 0f
        var inter = 0; var uni = 0
        val minY = max(0, floor(poly.minOf { it.b }).toInt()); val maxY = min(mask.h - 1, ceil(poly.maxOf { it.b }).toInt())
        var inPoly = 0
        for (y in minY..maxY) {
            val cy = y + 0.5f
            var x0 = Float.MAX_VALUE; var x1 = -Float.MAX_VALUE
            for (i in poly.indices) {
                val a = poly[i]; val c = poly[(i + 1) % poly.size]
                if ((a.b <= cy && c.b > cy) || (c.b <= cy && a.b > cy)) {
                    val x = a.a + (cy - a.b) / (c.b - a.b) * (c.a - a.a)
                    x0 = min(x0, x); x1 = max(x1, x)
                }
            }
            if (x0 > x1) continue
            val xs = max(0, ceil(x0 - 0.5f).toInt()); val xe = min(mask.w - 1, floor(x1 - 0.5f).toInt())
            for (x in xs..xe) { inPoly++; if (mask.bits[y * mask.w + x]) inter++ }
        }
        val m = mask.bits.count { it }
        uni = inPoly + m - inter
        return if (uni == 0) 0f else inter.toFloat() / uni
    }

    private fun densify(poly: List<P2>, step: Float): List<P2> {
        val out = ArrayList<P2>()
        for (i in poly.indices) {
            val a = poly[i]; val b = poly[(i + 1) % poly.size]
            val n = max(1, (hypot(b.a - a.a, b.b - a.b) / step).toInt())
            for (s in 0 until n) { val t = s.toFloat() / n; out += P2(a.a + (b.a - a.a) * t, a.b + (b.b - a.b) * t) }
        }
        return out
    }

    private fun pct(sorted: FloatArray, q: Float) = sorted[((sorted.size - 1) * q).toInt().coerceIn(0, sorted.size - 1)]

    private fun growMask(m: Mask, r: Int): Mask = m.dilate(r)
}

/** One calibration photo: what the photo mode measured (before calibration) and what the tape says, cm. */
@Serializable
data class CalSample(val rawCm: List<Double>, val tapeCm: List<Double>, val at: Long = System.currentTimeMillis(),
                     /** The depth model the sample was measured with: a new model needs a new calibration. */
                     val model: String = "",
                     /** The camera height the depth model gave for the photo (no factor), metres; 0 = not recorded. */
                     val aiCameraM: Double = 0.0,
                     /** Real / reported autofocus diopters from this carton's photos taken close (see Calibration.focusFactor). */
                     val focusFactors: List<Double> = emptyList()) {
    /** How high the camera really was: the model's height times this carton's tape / measured; null if unknown. */
    fun cameraM(): Double? {
        val r = ratios().sorted(); if (aiCameraM <= 0 || r.isEmpty()) return null
        return aiCameraM * (if (r.size % 2 == 1) r[r.size / 2] else (r[r.size / 2 - 1] + r[r.size / 2]) / 2)
    }

    /** tape / measured for each side: length with length, width with width (both sorted long-short), height with height. */
    fun ratios(): List<Double> {
        val r = rawCm.take(2).sortedDescending() + rawCm[2]
        val t = tapeCm.take(2).sortedDescending() + tapeCm[2]
        return r.indices.mapNotNull { i -> if (r[i] > 0.5 && t[i] > 0.5) t[i] / r[i] else null }
    }
}

object Calibration {
    /** The samples made with the depth model in use (one made with another model does not apply to this one). */
    fun current(all: List<CalSample>): List<CalSample> = all.filter { it.model == DepthModel.ID }

    /** Above this [mismatch] the photo read the box's shape wrong: saving it asks first. */
    const val MISMATCH = 1.35

    /** How far apart the three sides' ratios are (largest / smallest): over 1,35 the photo's shape does not match the tape. */
    fun mismatch(s: CalSample): Double { val r = s.ratios(); return if (r.size < 2) 1.0 else r.max() / r.min() }

    /** This phone's scale: the median of every side's tape / measured ratio over the samples; null without samples. */
    fun factor(samples: List<CalSample>): Double? {
        val r = samples.flatMap { it.ratios() }.sorted()
        if (r.isEmpty()) return null
        return if (r.size % 2 == 1) r[r.size / 2] else (r[r.size / 2 - 1] + r[r.size / 2]) / 2
    }

    /**
     * The height the courier photographs from when standing, learnt from the calibration photos (each one's real camera
     * height); null with fewer than two. [Standing.spread]: (highest - lowest) / median.
     */
    fun standing(samples: List<CalSample>): Standing? {
        val hs = samples.mapNotNull { it.cameraM() }.sorted()
        if (hs.size < 2) return null
        val m = if (hs.size % 2 == 1) hs[hs.size / 2] else (hs[hs.size / 2 - 1] + hs[hs.size / 2]) / 2
        return Standing(m, (hs.last() - hs.first()) / m, hs.size)
    }

    /**
     * How the autofocus's diopters turn into real ones on this phone: from the calibration photos taken close
     * (median of their factors), else what the camera itself says about its focus, else the DT50's (see [DT50_FOCUS]).
     */
    fun focus(samples: List<CalSample>, lens: FocusInfo?): FocusCal? {
        val fs = samples.flatMap { it.focusFactors }.sorted()
        if (fs.isNotEmpty()) {
            val m = if (fs.size % 2 == 1) fs[fs.size / 2] else (fs[fs.size / 2 - 1] + fs[fs.size / 2]) / 2
            return FocusCal(m, if (fs.size == 1) 0.05 else max(0.02, (fs.last() - fs.first()) / m / 2), fs.size)
        }
        return builtIn(lens)
    }

    /**
     * Real / reported autofocus diopters for one calibration photo [r] of a carton of tape size [tapeCm]: its real camera
     * height is the depth model's times tape / read, the autofocus point's real distance its depth per metre of camera
     * height times that. Only within 0,8 m, where the lens moves enough to tell; null otherwise or without a focus.
     */
    fun focusFactor(r: PhotoResult, tapeCm: List<Double>): Double? {
        if (r.focusDiopters <= 0 || r.focusDepthUnit <= 0 || r.aiCameraM <= 0) return null
        val q = CalSample(r.rawCm, tapeCm).ratios().sorted(); if (q.isEmpty()) return null
        val z = r.focusDepthUnit * r.aiCameraM * q[q.size / 2]
        if (z > 0.8) return null
        return 1 / z / r.focusDiopters
    }

    /**
     * Real / reported diopters of the Urovo DT50's camera, whose focus Android calls "uncalibrated": 3,13 and 3,08 on the
     * first two photos measured with a tape (a cigarette pack 8 x 4 x 1,5 cm at 6-8 cm, 0.4.3), while the depth model
     * was 9x and 14x off on them. Recognised by its lens facts (closest focus 20, hyperfocal 1/3 in its own units).
     */
    const val DT50_FOCUS = 3.1

    /** The focus factor before the phone has its own: the camera's word for a calibrated focus, the DT50's, or none. */
    fun builtIn(lens: FocusInfo?): FocusCal? = when {
        lens == null -> null
        lens.calibration == "calibrated" -> FocusCal(1.0, 0.04, 0, builtIn = true)
        lens.calibration == "approximate" -> FocusCal(1.0, 0.15, 0, builtIn = true)
        lens.minFocusDiopters == 20f && abs((lens.hyperfocalDiopters ?: 0f) - 1f / 3) < 0.01f -> FocusCal(DT50_FOCUS, 0.06, 0, builtIn = true)
        else -> null
    }

    /** How much the samples disagree: (largest - smallest ratio) / factor, 0 for one sample. */
    fun spread(samples: List<CalSample>): Double {
        val r = samples.flatMap { it.ratios() }
        val f = factor(samples) ?: return 0.0
        return if (r.size < 2) 0.0 else (r.max() - r.min()) / f
    }
}

/** The courier's camera height when standing, metres, from [samples] calibration photos. */
data class Standing(val heightM: Double, val spread: Double, val samples: Int)

/**
 * How the autofocus's reported diopters turn into real ones ([factor]), how far that is trusted ([sigma], relative), from
 * how many calibration photos ([samples]; 0 with [builtIn] = the camera's own word or the DT50's known factor).
 */
data class FocusCal(val factor: Double, val sigma: Double, val samples: Int, val builtIn: Boolean = false)
