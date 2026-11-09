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
 * is still), the object's outline (MobileSAM, tap or box), and a depth map (YOLO26n-depth). The depth model is only
 * asked for ONE number: how high the camera is above the floor around the object (the median over thousands of floor
 * pixels). Everything else is plain geometry with that number (single-view metrology):
 *   - the floor is the plane `up . X = -h`; every floor pixel's ray meets it at a known point
 *   - the outline's lower edge stands on the floor: the near half of the footprint
 *   - its left and right sides are vertical edges: their bottoms are on the floor, their tops give the height H
 *   - its upper edge is the far edge of the top, at H: the far half of the footprint
 *   - footprint = smallest rectangle round both halves; the box drawn from it is checked against the outline (IoU)
 * Every size scales with h, so a wrong h scales the result and nothing else: that is what the per-phone calibration
 * corrects. A box-like object fits its outline almost exactly (IoU ~0,98); a sack or a bottle much less (~0,8) and is
 * flagged.
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
)

class PhotoFailed(message: String) : Exception(message)

object PhotoMeasure {
    /** The outline must fit a box this well to count as box-like. */
    const val BOX_IOU = 0.92

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
    class Metrology(val lengthM: Float, val widthM: Float, val heightM: Float, val corners: List<V3>, val iou: Float, val sideAlign: Float)

    fun metrology(mask: Mask, k: Intrinsics, up: V3, hM: Float, forceH: Float? = null): Metrology {
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
        val lower = if (p1.map { dense[it].b }.average() > p2.map { dense[it].b }.average()) p1 else p2
        val q1 = path(tl, tr); val q2 = path(tr, tl)
        val upper = if (q1.map { dense[it].b }.average() < q2.map { dense[it].b }.average()) q1 else q2

        // plane axes for the footprint
        val ax = (up cross (if (abs(up.x) < 0.9f) V3(1f, 0f, 0f) else V3(0f, 0f, 1f))).unit()
        val ay = (up cross ax).unit()
        val origin = up * -hM

        fun footprint(H: Float): Pair<FloatArray, List<P2>>? {
            val q = ArrayList<P2>()
            for (i in lower) onPlane(k, up, dense[i].a, dense[i].b, hM)?.let { p -> val d = p - origin; q += P2(d dot ax, d dot ay) }
            if (hM - H > 0.02f) for (i in upper) onPlane(k, up, dense[i].a, dense[i].b, hM - H)?.let { p ->
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
        if (cands.isEmpty()) throw PhotoFailed("Tinggi objek tidak terbaca: foto dari pojok paket, agak dari atas")
        var best: Metrology? = null
        for (H in cands) {
            val f = footprint(H) ?: continue
            val cs = corners(f.second, H)
            val iou = silhouetteIou(cs, k, mask)
            if (best == null || iou > best.iou) best = Metrology(max(f.first[0], f.first[1]), min(f.first[0], f.first[1]), H, cs, iou,
                listOfNotNull(sl?.align, sr?.align).minOrNull() ?: 0f)
        }
        return best ?: throw PhotoFailed("Ukuran tidak terbaca dari foto ini: ulangi dari sudut lain")
    }

    /**
     * One photo: floor -> camera height -> metrology -> checks. [scale]: this phone's calibration (1 = none yet).
     * [mask] and [k] at the same resolution.
     */
    fun measure(mask: Mask, k: Intrinsics, up: V3, depth: DepthMap, scale: Float, calibrated: Boolean): PhotoResult {
        require(mask.w == k.w && mask.h == k.h) { "mask and intrinsics differ in size" }
        val b = mask.bounds() ?: throw PhotoFailed("Objek belum dipilih")
        val area = mask.bits.count { it }
        if (area < mask.w * mask.h * 0.004f) throw PhotoFailed("Objek terlalu kecil di foto: dekati paketnya")
        val downDeg = Math.toDegrees(asin((-up.z).toDouble().coerceIn(-1.0, 1.0)))
        if (downDeg < 8) throw PhotoFailed("HP terlalu tegak: arahkan kamera miring ke bawah (30–60°)")
        val fl = floor(depth, mask, k, up)
        val h = fl.heightM * scale
        val met = metrology(mask, k, up, h)
        val notes = ArrayList<String>()
        var conf = 100.0
        val touches = b[0] <= 1 || b[1] <= 1 || b[2] >= mask.w - 2 || b[3] >= mask.h - 2
        if (touches) { notes += "Paket terpotong di tepi foto: mundur sedikit supaya paket utuh"; conf -= 35 }
        val boxLike = met.iou >= BOX_IOU
        if (!boxLike) { notes += "Bentuk tidak seperti kotak: ukuran perkiraan kasar (kotak terluar)"; conf -= 25 }
        conf -= (0.99 - met.iou).coerceAtLeast(0.0) * 150
        if (downDeg < 25 || downDeg > 72) { notes += "Sudut foto ${downDeg.toInt()}°: paling pas 30–60° ke bawah"; conf -= 10 }
        if (h < 0.25f || h > 2.2f) { notes += "Jarak kamera ke lantai tidak wajar (${"%.2f".format(h)} m): ulangi foto"; conf -= 30 }
        if (met.heightM > h - 0.08f) { notes += "Kamera kurang tinggi dari paket: foto dari lebih atas"; conf -= 20 }
        if (fl.wide || fl.inliers < 300) { notes += "Lantai di sekitar paket kurang terlihat"; conf -= 15 }
        if (fl.tiltDeg > 15) { notes += "Lantai tidak terbaca rata"; conf -= 15 }
        if (!calibrated) { notes += "Mode foto belum dikalibrasi di HP ini: angka bisa meleset jauh"; conf = min(conf, 60.0) }
        val c = conf.toInt().coerceIn(0, 100)
        val raw = listOf(met.lengthM / scale, met.widthM / scale, met.heightM / scale).map { it * 100.0 }
        val proj = met.corners.flatMap { p -> if (p.z > 0.01f) k.project(p).let { listOf(it.a / k.w, it.b / k.h) } else listOf(-1f, -1f) }
        return PhotoResult(met.lengthM * 100.0, met.widthM * 100.0, met.heightM * 100.0, raw, scale.toDouble(), h.toDouble(), downDeg,
            met.iou.toDouble(), boxLike, proj, c, ok = calibrated && boxLike && !touches && c >= 75, notes = notes,
            floorInliers = fl.inliers, floorTiltDeg = fl.tiltDeg.toDouble())
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
        return best.copy(lengthCm = l, widthCm = w, heightCm = h,
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
data class CalSample(val rawCm: List<Double>, val tapeCm: List<Double>, val at: Long = System.currentTimeMillis()) {
    /** tape / measured for each side: length with length, width with width (both sorted long-short), height with height. */
    fun ratios(): List<Double> {
        val r = rawCm.take(2).sortedDescending() + rawCm[2]
        val t = tapeCm.take(2).sortedDescending() + tapeCm[2]
        return r.indices.mapNotNull { i -> if (r[i] > 0.5 && t[i] > 0.5) t[i] / r[i] else null }
    }
}

object Calibration {
    /** This phone's scale: the median of every side's tape / measured ratio over the samples; null without samples. */
    fun factor(samples: List<CalSample>): Double? {
        val r = samples.flatMap { it.ratios() }.sorted()
        if (r.isEmpty()) return null
        return if (r.size % 2 == 1) r[r.size / 2] else (r[r.size / 2 - 1] + r[r.size / 2]) / 2
    }

    /** How much the samples disagree: (largest - smallest ratio) / factor, 0 for one sample. */
    fun spread(samples: List<CalSample>): Double {
        val r = samples.flatMap { it.ratios() }
        val f = factor(samples) ?: return 0.0
        return if (r.size < 2) 0.0 else (r.max() - r.min()) / f
    }
}
