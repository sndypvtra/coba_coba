package id.ukurpaket.app.measure

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * A pinhole camera looking at the floor. World: the floor is z = 0, z points up (toward the camera),
 * metres. Camera: x right, y down, z forward (the image's own axes). [r] is world -> camera, row-major.
 */
class FloorCamera(val f: Double, val cx: Double, val cy: Double, val r: DoubleArray, val t: DoubleArray) {
    /** Camera centre in the world. */
    val centre: DoubleArray get() = doubleArrayOf(
        -(r[0] * t[0] + r[3] * t[1] + r[6] * t[2]),
        -(r[1] * t[0] + r[4] * t[1] + r[7] * t[2]),
        -(r[2] * t[0] + r[5] * t[1] + r[8] * t[2]))

    fun project(x: Double, y: Double, z: Double): P2? {
        val X = r[0] * x + r[1] * y + r[2] * z + t[0]
        val Y = r[3] * x + r[4] * y + r[5] * z + t[1]
        val Z = r[6] * x + r[7] * y + r[8] * z + t[2]
        if (Z < 1e-4) return null
        return P2((cx + f * X / Z).toFloat(), (cy + f * Y / Z).toFloat())
    }

    /** Where the ray through image pixel (u, v) meets the floor, or null when it points above the horizon. */
    fun floorPoint(u: Double, v: Double): DoubleArray? {
        val dx = (u - cx) / f; val dy = (v - cy) / f
        val wx = r[0] * dx + r[3] * dy + r[6]; val wy = r[1] * dx + r[4] * dy + r[7]; val wz = r[2] * dx + r[5] * dy + r[8]
        val c = centre
        if (wz >= -1e-6) return null
        val s = -c[2] / wz
        return doubleArrayOf(c[0] + s * wx, c[1] + s * wy)
    }

    fun scaled(k: Double) = FloorCamera(f * k, cx * k, cy * k, r, t)

    companion object {
        /**
         * Camera from a homography floor (metres) -> image, as given by the printed sheet. The principal point is
         * taken as the image centre; the focal length is [focal] (from the photo's EXIF) when known, or else
         * estimated from the homography itself (two orthogonality constraints, one unknown).
         */
        fun fromHomography(hm: DoubleArray, w: Int, h: Int, focal: Double?): FloorCamera? {
            val cx = w / 2.0; val cy = h / 2.0
            // move the principal point to the origin
            val a = DoubleArray(9) { i ->
                val row = i / 3
                when (row) { 0 -> hm[i] - cx * hm[6 + i % 3]; 1 -> hm[i] - cy * hm[6 + i % 3]; else -> hm[i] }
            }
            val f = focal ?: estimateFocal(a) ?: return null
            val b1 = doubleArrayOf(a[0] / f, a[3] / f, a[6])
            val b2 = doubleArrayOf(a[1] / f, a[4] / f, a[7])
            val b3 = doubleArrayOf(a[2] / f, a[5] / f, a[8])
            var lam = 2.0 / (norm(b1) + norm(b2))
            if (b3[2] * lam < 0) lam = -lam                 // the sheet is in front of the camera
            val r1 = unit(b1.map { it * lam }.toDoubleArray())
            var r2 = b2.map { it * lam }.toDoubleArray()
            val d = dot(r2, r1)
            r2 = unit(DoubleArray(3) { r2[it] - d * r1[it] })
            var r3 = cross(r1, r2)
            val t = b3.map { it * lam }.toDoubleArray()
            var rr2 = r2
            // world z must point toward the camera: if the camera is below the sheet, turn the world over (x stays)
            val cz = -(r3[0] * t[0] + r3[1] * t[1] + r3[2] * t[2])
            if (cz < 0) { rr2 = rr2.map { -it }.toDoubleArray(); r3 = r3.map { -it }.toDoubleArray() }
            val rot = doubleArrayOf(r1[0], rr2[0], r3[0], r1[1], rr2[1], r3[1], r1[2], rr2[2], r3[2])
            return FloorCamera(f, cx, cy, rot, t)
        }

        /** Zhang's constraints with square pixels and the principal point at the origin; null when ill-posed. */
        fun estimateFocal(a: DoubleArray): Double? {
            val h1 = doubleArrayOf(a[0], a[3], a[6]); val h2 = doubleArrayOf(a[1], a[4], a[7])
            // (h1x h2x + h1y h2y) x + h1z h2z = 0 ; (|h1xy|^2 - |h2xy|^2) x + (h1z^2 - h2z^2) = 0, x = 1 / f^2
            val a1 = h1[0] * h2[0] + h1[1] * h2[1]; val c1 = h1[2] * h2[2]
            val a2 = h1[0] * h1[0] + h1[1] * h1[1] - h2[0] * h2[0] - h2[1] * h2[1]; val c2 = h1[2] * h1[2] - h2[2] * h2[2]
            val den = a1 * a1 + a2 * a2
            if (den < 1e-18) return null
            val x = -(a1 * c1 + a2 * c2) / den
            if (x <= 0) return null
            return 1.0 / sqrt(x)
        }

        internal fun norm(v: DoubleArray) = sqrt(dot(v, v))
        internal fun dot(a: DoubleArray, b: DoubleArray) = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
        internal fun unit(v: DoubleArray): DoubleArray { val n = norm(v); return DoubleArray(3) { v[it] / n } }
        internal fun cross(a: DoubleArray, b: DoubleArray) =
            doubleArrayOf(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    }
}

/** Homography from >= 4 point pairs (normalised DLT, h33 = 1). Returns row-major 3x3, or null. */
fun homography(src: List<P2>, dst: List<P2>): DoubleArray? {
    if (src.size < 4 || src.size != dst.size) return null
    fun norm(p: List<P2>): DoubleArray {
        val mx = p.sumOf { it.a.toDouble() } / p.size; val my = p.sumOf { it.b.toDouble() } / p.size
        val d = p.sumOf { sqrt((it.a - mx) * (it.a - mx) + (it.b - my) * (it.b - my)) } / p.size
        val s = if (d < 1e-12) 1.0 else sqrt(2.0) / d
        return doubleArrayOf(s, 0.0, -s * mx, 0.0, s, -s * my, 0.0, 0.0, 1.0)
    }
    val ts = norm(src); val td = norm(dst)
    val ata = Array(8) { DoubleArray(8) }; val atb = DoubleArray(8)
    for (i in src.indices) {
        val x = ts[0] * src[i].a + ts[2]; val y = ts[4] * src[i].b + ts[5]
        val u = td[0] * dst[i].a + td[2]; val v = td[4] * dst[i].b + td[5]
        val rows = arrayOf(doubleArrayOf(x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y) to u,
            doubleArrayOf(0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y) to v)
        for ((row, rhs) in rows) for (j in 0 until 8) { atb[j] += row[j] * rhs; for (k in 0 until 8) ata[j][k] += row[j] * row[k] }
    }
    val h = solve(ata, atb) ?: return null
    val hn = doubleArrayOf(h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1.0)
    // undo the normalisation: H = Td^-1 * Hn * Ts
    val tdInv = doubleArrayOf(1 / td[0], 0.0, -td[2] / td[0], 0.0, 1 / td[4], -td[5] / td[4], 0.0, 0.0, 1.0)
    val out = mul3(mul3(tdInv, hn), ts)
    return out.map { it / out[8] }.toDoubleArray()
}

fun applyH(h: DoubleArray, x: Double, y: Double): P2 {
    val w = h[6] * x + h[7] * y + h[8]
    return P2(((h[0] * x + h[1] * y + h[2]) / w).toFloat(), ((h[3] * x + h[4] * y + h[5]) / w).toFloat())
}

internal fun mul3(a: DoubleArray, b: DoubleArray) = DoubleArray(9) { i ->
    val r = i / 3; val c = i % 3
    a[r * 3] * b[c] + a[r * 3 + 1] * b[3 + c] + a[r * 3 + 2] * b[6 + c]
}

/** Gaussian elimination with partial pivoting. */
internal fun solve(a: Array<DoubleArray>, b: DoubleArray): DoubleArray? {
    val n = b.size
    val m = Array(n) { i -> DoubleArray(n + 1) { j -> if (j < n) a[i][j] else b[i] } }
    for (c in 0 until n) {
        val p = (c until n).maxBy { abs(m[it][c]) }
        if (abs(m[p][c]) < 1e-14) return null
        val tmp = m[c]; m[c] = m[p]; m[p] = tmp
        for (r in 0 until n) if (r != c) {
            val k = m[r][c] / m[c][c]
            if (k != 0.0) for (j in c..n) m[r][j] -= k * m[c][j]
        }
    }
    return DoubleArray(n) { m[it][n] / m[it][it] }
}

/** One photo's measurement. Corners: world (z up, metres); [iou] = how well the box explains the parcel's outline. */
class SingleViewResult(
    val lengthM: Float, val widthM: Float, val heightM: Float,
    val floorCorners: List<V3>, val topCorners: List<V3>,
    val iou: Float,
    /** Heights (m) that explain the outline almost as well as the best one: a wide band means an ambiguous view. */
    val heightBandM: Float,
)

/**
 * Size of a parcel standing on the floor from ONE photo, its mask and a camera known from the printed sheet.
 *
 * For a guessed height H, the footprint is every floor point q whose column (q at 0, H/2 and H) projects
 * inside the mask (silhouette carving). The box on that footprint, H tall, is projected back; the H whose
 * box outline overlaps the mask best (IoU) is the answer. Works for boxes; for soft bags it gives the
 * box around them, with a lower IoU.
 */
object SingleView {
    fun measure(mask0: Mask, cam: FloorCamera, maxHeight: Double = 1.5): SingleViewResult? {
        val mask = mask0.largestPart()
        val b = mask.bounds() ?: return null
        // floor area the parcel can occupy: where the mask's pixels meet the floor (the top lands further away)
        var x0 = Double.MAX_VALUE; var y0 = Double.MAX_VALUE; var x1 = -Double.MAX_VALUE; var y1 = -Double.MAX_VALUE
        val step = max(1, max(b[2] - b[0], b[3] - b[1]) / 120)
        var y = b[1]
        while (y <= b[3]) {
            var x = b[0]
            while (x <= b[2]) {
                if (mask[x, y]) cam.floorPoint(x + 0.5, y + 0.5)?.let { p ->
                    x0 = min(x0, p[0]); x1 = max(x1, p[0]); y0 = min(y0, p[1]); y1 = max(y1, p[1])
                }
                x += step
            }
            y += step
        }
        if (x1 <= x0 || y1 <= y0) return null
        // keep the search area sane when the top's rays run far away
        val ext = min(3.0, max(x1 - x0, y1 - y0)) + 0.06
        val mx = (x0 + x1) / 2; val my = (y0 + y1) / 2
        val g = max(0.002, ext / 170)
        val n = (ext / g).toInt() + 1
        val gx = DoubleArray(n) { mx - ext / 2 + it * g }; val gy = DoubleArray(n) { my - ext / 2 + it * g }
        val base = BooleanArray(n * n) { i -> cam.project(gx[i % n], gy[i / n], 0.0)?.let { mask[it.a, it.b] } ?: false }
        val camZ = cam.centre[2]
        val hMax = min(maxHeight, 0.92 * camZ)

        // outline overlap is checked on a coarse copy of the mask around the parcel
        val pad = ((b[2] - b[0]) + (b[3] - b[1])) / 10
        val rx0 = b[0] - pad; val ry0 = b[1] - pad; val rx1 = b[2] + pad; val ry1 = b[3] + pad
        val rs = max(1, max(rx1 - rx0, ry1 - ry0) / 200)

        fun carve(hh: Double): List<P2> {
            val out = ArrayList<P2>()
            for (i in 0 until n * n) {
                if (!base[i]) continue
                val qx = gx[i % n]; val qy = gy[i / n]
                val top = cam.project(qx, qy, hh) ?: continue
                if (!mask[top.a, top.b]) continue
                val mid = cam.project(qx, qy, hh / 2) ?: continue
                if (!mask[mid.a, mid.b]) continue
                out.add(P2(qx.toFloat(), qy.toFloat()))
            }
            return out
        }

        class Cand(val h: Double, val rect: Rect2, val iou: Float)
        fun evaluate(hh: Double): Cand? {
            val pts = carve(hh)
            if (pts.size < 8) return null
            val hull = convexHull(pts)
            if (hull.size < 3) return null
            val r0 = minAreaRect(hull)
            val rect = grow(r0, (g / 2).toFloat())
            val img = (rect.corners.map { cam.project(it.a.toDouble(), it.b.toDouble(), 0.0) } +
                rect.corners.map { cam.project(it.a.toDouble(), it.b.toDouble(), hh) })
            if (img.any { it == null }) return null
            val poly = convexHull(img.filterNotNull())
            var inter = 0; var uni = 0
            var yy = ry0
            while (yy <= ry1) {
                var xx = rx0
                while (xx <= rx1) {
                    val a = mask[xx, yy]; val p = inside(poly, xx + 0.5f, yy + 0.5f)
                    if (a && p) inter++
                    if (a || p) uni++
                    xx += rs
                }
                yy += rs
            }
            return Cand(hh, rect, if (uni == 0) 0f else inter.toFloat() / uni)
        }

        val coarse = ArrayList<Cand>()
        var hh = 0.01
        while (hh <= hMax) { evaluate(hh)?.let { coarse.add(it) }; hh += 0.01 }
        val c0 = coarse.maxByOrNull { it.iou } ?: return null
        val fine = ArrayList<Cand>(coarse)
        hh = max(0.005, c0.h - 0.012)
        while (hh <= min(hMax, c0.h + 0.012)) { evaluate(hh)?.let { fine.add(it) }; hh += 0.002 }
        val best = fine.maxBy { it.iou }
        val band = fine.filter { it.iou >= best.iou - 0.01f }.let { s -> (s.maxOf { it.h } - s.minOf { it.h }).toFloat() }
        val r = best.rect
        val h = best.h.toFloat()
        return SingleViewResult(
            lengthM = max(r.l, r.w), widthM = min(r.l, r.w), heightM = h,
            floorCorners = r.corners.map { V3(it.a, it.b, 0f) }, topCorners = r.corners.map { V3(it.a, it.b, h) },
            iou = best.iou, heightBandM = band)
    }

    /** 0-100 from how well the box explains the outline and how well the height is pinned down. */
    fun confidence(r: SingleViewResult): Int {
        val fit = ((r.iou - 0.75f) / 0.2f).coerceIn(0f, 1f)
        val pin = (1f - (r.heightBandM - 0.01f) / 0.05f).coerceIn(0f, 1f)
        return (100f * (0.6f * fit + 0.4f * pin)).toInt().coerceIn(0, 100)
    }

    private fun grow(r: Rect2, d: Float): Rect2 {
        val cxm = r.corners.map { it.a }.average().toFloat(); val cym = r.corners.map { it.b }.average().toFloat()
        val e0 = P2(r.corners[1].a - r.corners[0].a, r.corners[1].b - r.corners[0].b)
        val e1 = P2(r.corners[3].a - r.corners[0].a, r.corners[3].b - r.corners[0].b)
        val l0 = sqrt(e0.a * e0.a + e0.b * e0.b).coerceAtLeast(1e-6f); val l1 = sqrt(e1.a * e1.a + e1.b * e1.b).coerceAtLeast(1e-6f)
        val u = P2(e0.a / l0, e0.b / l0); val v = P2(e1.a / l1, e1.b / l1)
        val hu = l0 / 2 + d; val hv = l1 / 2 + d
        fun at(su: Float, sv: Float) = P2(cxm + u.a * su * hu + v.a * sv * hv, cym + u.b * su * hu + v.b * sv * hv)
        return Rect2(2 * hu, 2 * hv, listOf(at(-1f, -1f), at(1f, -1f), at(1f, 1f), at(-1f, 1f)))
    }
}

/** Point in a convex polygon (either winding). */
fun inside(poly: List<P2>, x: Float, y: Float): Boolean {
    var pos = false; var neg = false
    for (i in poly.indices) {
        val a = poly[i]; val b = poly[(i + 1) % poly.size]
        val c = (b.a - a.a) * (y - a.b) - (b.b - a.b) * (x - a.a)
        if (c > 0) pos = true else if (c < 0) neg = true
        if (pos && neg) return false
    }
    return true
}
