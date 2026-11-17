package id.ukuraja.app

import id.ukurpaket.app.marker.Aruco
import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.Intrinsics
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.math.tan

/**
 * A synthetic colour photo as the phone takes it (960 x 1280 upright, a DT50-like 66° lens): a carton [boxCm] on a tiled
 * floor, the printed A4 marker sheet beside it (or not), the camera [camH] m up looking [down]° down. Everything the
 * engine needs comes with it: the exact outline (as MobileSAM would cut it), a depth map with the depth model's scale
 * error [aiFactor], the lens and 'up'.
 */
class Scene(
    val camH: Double = 1.15,
    val down: Double = 50.0,
    val marker: Boolean = true,
    val boxCm: Triple<Double, Double, Double> = Triple(40.0, 30.0, 20.0),
    val boxYaw: Double = 28.0,
    val boxAt: Pair<Double, Double> = 0.56 to 0.44,
    val markerAt: Pair<Double, Double> = 0.26 to 0.80,
    val markerYaw: Double = 12.0,
    val markerSideM: Double = 0.16,
    val w: Int = 960,
    val h: Int = 1280,
) {
    val k: Intrinsics = (w / 2.0 / tan(33.0 * PI / 180)).toFloat().let { f -> Intrinsics(f, f, w / 2f, h / 2f, w, h) }
    private val u = doubleArrayOf(0.0, -cos(down * PI / 180), -sin(down * PI / 180))
    val up = V3(u[0].toFloat(), u[1].toFloat(), u[2].toFloat())

    private fun dot(a: DoubleArray, b: DoubleArray) = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    private fun cross(a: DoubleArray, b: DoubleArray) = doubleArrayOf(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    private fun unit(a: DoubleArray) = sqrt(dot(a, a)).let { n -> DoubleArray(3) { a[it] / n } }
    private fun floorAt(fx: Double, fy: Double): DoubleArray {
        val r = doubleArrayOf((fx * w - k.cx) / k.fx, (fy * h - k.cy) / k.fy, 1.0)
        return DoubleArray(3) { r[it] * camH / -dot(r, u) }
    }
    private fun axes(yawDeg: Double): Pair<DoubleArray, DoubleArray> {
        val a0 = unit(cross(u, doubleArrayOf(1.0, 0.0, 0.0))); val b0 = cross(u, a0)
        val y = yawDeg * PI / 180
        val a = DoubleArray(3) { a0[it] * cos(y) + b0[it] * sin(y) }
        return a to cross(a, u)
    }

    // the carton: corner o, edges ex (length), ey (width), ez (height, up)
    private val bl = boxCm.first / 100; private val bw = boxCm.second / 100; private val bh = boxCm.third / 100
    private val bAx = axes(boxYaw)
    private val bo = floorAt(boxAt.first, boxAt.second).let { c -> DoubleArray(3) { c[it] - bAx.first[it] * bl / 2 - bAx.second[it] * bw / 2 } }
    private val edges = listOf(bAx.first.map { it * bl }.toDoubleArray(), bAx.second.map { it * bw }.toDoubleArray(), u.map { it * bh }.toDoubleArray())

    // the sheet: top-left of the black square, its axes; white margin round it
    private val mAx = axes(markerYaw)
    private val mtl = floorAt(markerAt.first, markerAt.second).let { c -> DoubleArray(3) { c[it] - (mAx.first[it] + mAx.second[it]) * markerSideM / 2 } }

    /** Where the ray [r] meets the carton first: distance and which face (0-5), or null. */
    private fun hitBox(r: DoubleArray): Pair<Double, Int>? {
        var t0 = 0.0; var t1 = Double.MAX_VALUE; var face = -1
        for ((i, e) in edges.withIndex()) {
            val l2 = dot(e, e)
            val ro = -dot(bo, e) / l2; val rd = dot(r, e) / l2
            if (abs(rd) < 1e-12) { if (ro < 0 || ro > 1) return null; continue }
            var ta = -ro / rd; var tb = (1 - ro) / rd
            var fa = 2 * i; if (ta > tb) { val t = ta; ta = tb; tb = t; fa = 2 * i + 1 }
            if (ta > t0) { t0 = ta; face = fa }
            t1 = min(t1, tb)
            if (t0 > t1) return null
        }
        return if (t0 > 0 && face >= 0) t0 to face else null
    }

    private fun colour(r: DoubleArray): Int {
        val fl = -dot(r, u)
        val tf = if (fl > 1e-6) camH / fl else Double.MAX_VALUE
        hitBox(r)?.let { (t, face) ->
            if (t < tf) {
                // brown cardboard: top lightest, the two sides seen darker; a tape strip along the top
                val p = DoubleArray(3) { r[it] * t - bo[it] }
                val b = dot(p, bAx.second) / bw
                return when (face / 2) {
                    2 -> if (abs(b - 0.5) < 0.08) rgb(214, 190, 150) else rgb(205, 160, 110)
                    0 -> rgb(170, 125, 80)
                    else -> rgb(150, 108, 68)
                }
            }
        }
        if (tf == Double.MAX_VALUE) return rgb(225, 228, 232)
        val p = DoubleArray(3) { r[it] * tf }
        if (marker) {
            val q = DoubleArray(3) { p[it] - mtl[it] }
            val cell = markerSideM / Aruco.GRID
            val su = dot(q, mAx.first) / cell; val sv = dot(q, mAx.second) / cell
            if (su >= -0.95 && sv >= -0.9 && su < Aruco.GRID + 0.95 && sv < Aruco.GRID + 4.2) {
                if (su < 0 || sv < 0 || su >= Aruco.GRID || sv >= Aruco.GRID) return rgb(243, 243, 240)
                val i = sv.toInt(); val j = su.toInt()
                if (i == 0 || j == 0 || i == Aruco.GRID - 1 || j == Aruco.GRID - 1) return rgb(24, 24, 26)
                val bit = (Aruco.DICT_4X4_50[1] shr (15 - ((i - 1) * 4 + (j - 1)))) and 1
                return if (bit == 1) rgb(243, 243, 240) else rgb(24, 24, 26)
            }
        }
        // tiles 40 cm with grout; a soft shadow by the carton
        val fx = dot(p, axes(0.0).first); val fz = dot(p, axes(0.0).second)
        val gx = fx / 0.4 - floor(fx / 0.4); val gz = fz / 0.4 - floor(fz / 0.4)
        var c = if (gx < 0.012 || gz < 0.012) 176 else 206 + (if ((floor(fx / 0.4) + floor(fz / 0.4)).toInt() % 2 == 0) 4 else -3)
        val d = DoubleArray(3) { p[it] - bo[it] }
        val da = dot(d, bAx.first) / bl; val db = dot(d, bAx.second) / bw
        val out = max(max(-da, da - 1) * bl, max(-db, db - 1) * bw)
        if (out < 0.05) c -= ((0.05 - max(0.0, out)) / 0.05 * 38).toInt()
        return rgb(c, c + 2, c + 6)
    }

    private fun rgb(r: Int, g: Int, b: Int) = (0xFF shl 24) or (r.coerceIn(0, 255) shl 16) or (g.coerceIn(0, 255) shl 8) or b.coerceIn(0, 255)

    /** The photo, ARGB, 2 x 2 rays per pixel. */
    fun render(): IntArray {
        val out = IntArray(w * h)
        val rnd = java.util.Random(3)
        for (py in 0 until h) for (px in 0 until w) {
            var rr = 0; var gg = 0; var bb = 0
            for (sy in 0..1) for (sx in 0..1) {
                val r = doubleArrayOf((px + 0.25 + 0.5 * sx - k.cx) / k.fx, (py + 0.25 + 0.5 * sy - k.cy) / k.fy, 1.0)
                val c = colour(r); rr += (c shr 16) and 255; gg += (c shr 8) and 255; bb += c and 255
            }
            val n = (rnd.nextGaussian() * 2.5).roundToInt()
            out[py * w + px] = rgb(rr / 4 + n, gg / 4 + n, bb / 4 + n)
        }
        return out
    }

    fun luma(argb: IntArray) = ByteArray(argb.size) { i -> val c = argb[i]; ((((c shr 16) and 255) * 77 + ((c shr 8) and 255) * 150 + (c and 255) * 29) shr 8).toByte() }

    /** The photo at half size (the 480 x 640 picture the models see). */
    fun half(argb: IntArray): IntArray {
        val nw = w / 2; val nh = h / 2
        return IntArray(nw * nh) { i ->
            val x = (i % nw) * 2; val y = (i / nw) * 2
            var r = 0; var g = 0; var b = 0
            for (dy in 0..1) for (dx in 0..1) { val c = argb[(y + dy) * w + x + dx]; r += (c shr 16) and 255; g += (c shr 8) and 255; b += c and 255 }
            rgb(r / 4, g / 4, b / 4)
        }
    }

    /** The carton's exact outline in the 480 x 640 picture. */
    fun mask(): Mask {
        val k2 = k.scaled(w / 2, h / 2)
        val bits = BooleanArray(k2.w * k2.h) { i ->
            val r = doubleArrayOf((i % k2.w + 0.5 - k2.cx) / k2.fx, (i / k2.w + 0.5 - k2.cy) / k2.fy, 1.0)
            hitBox(r) != null
        }
        return Mask(k2.w, k2.h, bits)
    }

    /** The depth model's picture of a level floor, its camera height wrong by [aiFactor]. */
    fun depth(aiFactor: Double): DepthMap {
        val k2 = k.scaled(w / 2, h / 2)
        val z = FloatArray(k2.w * k2.h) { i ->
            val den = -(k2.ray(i % k2.w + 0.5f, i / k2.w + 0.5f) dot up)
            if (den > 1e-3f) (camH * aiFactor / den).toFloat() else 40f
        }
        return DepthMap(k2.w, k2.h, z)
    }
}
