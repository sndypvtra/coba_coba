package id.ukurpaket.app

import id.ukurpaket.app.measure.FloorCamera
import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.MarkerSheet
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * A ray-traced phone photo for marker mode: tiled floor, the printed A4 sheet, a taped carton with a label.
 * Every pixel is a ray from a known camera, so the true size is known exactly. 2 x 2 supersampled, light noise.
 */
class SyntheticScene(
    val w: Int = 1200, val h: Int = 1600, val f: Double = 1250.0,
    camPos: DoubleArray = doubleArrayOf(-0.04, -0.52, 0.80), target: DoubleArray = doubleArrayOf(-0.02, 0.10, 0.0),
    val sheetX: Double = -0.24, val sheetY: Double = 0.02, val sheetRot: Double = 0.15,
    val bx: Double = 0.16, val by: Double = 0.14, val bl: Double = 0.38, val bw: Double = 0.28, val bh: Double = 0.18, val byaw: Double = 0.35,
) {
    val cam: FloorCamera = run {
        fun unit(v: DoubleArray): DoubleArray { val n = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); return DoubleArray(3) { v[it] / n } }
        fun cross(a: DoubleArray, b: DoubleArray) = doubleArrayOf(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        val z = unit(DoubleArray(3) { target[it] - camPos[it] })
        val x = unit(cross(z, doubleArrayOf(0.0, 0.0, 1.0)))
        val y = cross(z, x)
        val r = doubleArrayOf(x[0], x[1], x[2], y[0], y[1], y[2], z[0], z[1], z[2])
        val t = DoubleArray(3) { -(r[it * 3] * camPos[0] + r[it * 3 + 1] * camPos[1] + r[it * 3 + 2] * camPos[2]) }
        FloorCamera(f, w / 2.0, h / 2.0, r, t)
    }

    /** Ray through pixel (u, v) in world coordinates: origin, direction. */
    private fun ray(u: Double, v: Double): Pair<DoubleArray, DoubleArray> {
        val r = cam.r
        val dx = (u - cam.cx) / f; val dy = (v - cam.cy) / f
        return cam.centre to doubleArrayOf(r[0] * dx + r[3] * dy + r[6], r[1] * dx + r[4] * dy + r[7], r[2] * dx + r[5] * dy + r[8])
    }

    /** Distance along the ray to the carton and which face (0 top, 1..4 sides), or null. */
    private fun hitBox(o: DoubleArray, d: DoubleArray): Pair<Double, Int>? {
        val c = cos(-byaw); val s = sin(-byaw)
        val ox = (o[0] - bx) * c - (o[1] - by) * s; val oy = (o[0] - bx) * s + (o[1] - by) * c; val oz = o[2]
        val dx = d[0] * c - d[1] * s; val dy = d[0] * s + d[1] * c; val dz = d[2]
        var tn = -1e9; var tf = 1e9; var face = -1
        val lo = doubleArrayOf(-bl / 2, -bw / 2, 0.0); val hi = doubleArrayOf(bl / 2, bw / 2, bh)
        val oo = doubleArrayOf(ox, oy, oz); val dd = doubleArrayOf(dx, dy, dz)
        for (a in 0 until 3) {
            if (abs(dd[a]) < 1e-12) { if (oo[a] < lo[a] || oo[a] > hi[a]) return null; continue }
            var t1 = (lo[a] - oo[a]) / dd[a]; var t2 = (hi[a] - oo[a]) / dd[a]
            val f1 = if (a == 2) 5 else a * 2 + 1; val f2 = if (a == 2) 0 else a * 2 + 2
            var fa = f1
            if (t1 > t2) { val t = t1; t1 = t2; t2 = t; fa = f2 }
            if (t1 > tn) { tn = t1; face = fa }
            tf = min(tf, t2)
        }
        return if (tn <= tf && tn > 0) tn to face else null
    }

    private fun shade(u: Double, v: Double): IntArray {
        val (o, d) = ray(u, v)
        hitBox(o, d)?.let { (t, face) ->
            val p = DoubleArray(3) { o[it] + t * d[it] }
            val c = cos(-byaw); val s = sin(-byaw)
            val lx = (p[0] - bx) * c - (p[1] - by) * s; val ly = (p[0] - bx) * s + (p[1] - by) * c
            val k = when (face) { 0 -> 1.0; 1, 2 -> 0.78; else -> 0.66 }
            var col = doubleArrayOf(196.0, 152.0, 104.0)
            if (face == 0) {
                if (abs(ly) < 0.025) col = doubleArrayOf(214.0, 178.0, 128.0)                        // tape
                if (lx > 0.03 && lx < 0.14 && ly > -0.11 && ly < -0.035) col = doubleArrayOf(244.0, 244.0, 240.0)  // label
                if (lx > 0.045 && lx < 0.125 && ly > -0.10 && ly < -0.045 && ((lx * 900).toInt() % 3 == 0)) col = doubleArrayOf(70.0, 70.0, 70.0)
            } else if (abs(p[2] - bh / 2) < 0.012 && face != 0) col = doubleArrayOf(184.0, 140.0, 94.0)
            return IntArray(3) { (col[it] * k).toInt() }
        }
        if (d[2] >= 0) return intArrayOf(200, 200, 200)
        val s = -o[2] / d[2]
        val x = o[0] + s * d[0]; val y = o[1] + s * d[1]
        // the sheet
        val cr = cos(-sheetRot); val sr = sin(-sheetRot)
        val sx = (x - sheetX) * cr - (y - sheetY) * sr; val sy = (x - sheetX) * sr + (y - sheetY) * cr
        if (abs(sx) < 0.105 && sy > -0.110 && sy < 0.187) {
            val m = max(abs(sx), abs(sy))
            if (m <= MarkerSheet.OUTER / 2 && m >= MarkerSheet.INNER / 2) return intArrayOf(26, 26, 28)
            if (sy > 0.104 && sy < 0.106 && sx > -0.05 && sx < 0.05) return intArrayOf(30, 30, 30)              // check bar
            return intArrayOf(238, 238, 234)
        }
        // soft shadow by the carton, then floor tiles with grout and speckle
        val c = cos(-byaw); val sn = sin(-byaw)
        val lx = (x - bx) * c - (y - by) * sn; val ly = (x - bx) * sn + (y - by) * c
        val out = max(0.0, max(abs(lx) - bl / 2, abs(ly) - bw / 2))
        val shadow = if (out < 0.05) 0.72 + 0.28 * out / 0.05 else 1.0
        val gx = ((x + 10) / 0.3) % 1.0; val gy = ((y + 10) / 0.3) % 1.0
        val grout = gx < 0.012 || gy < 0.012
        val hsh = ((x * 400).toInt() * 73856093) xor ((y * 400).toInt() * 19349663)
        val sp = (hsh and 15) - 8
        val base = if (grout) doubleArrayOf(150.0, 146.0, 140.0) else doubleArrayOf(186.0 + sp, 180.0 + sp, 170.0 + sp)
        return IntArray(3) { (base[it] * shadow).toInt() }
    }

    /** The photo as ARGB, row by row. */
    fun argb(): IntArray {
        val rnd = java.util.Random(5)
        return IntArray(w * h) { i ->
            val x = i % w; val y = i / w
            val a = shade(x + 0.25, y + 0.25); val b = shade(x + 0.75, y + 0.25); val c = shade(x + 0.25, y + 0.75); val d = shade(x + 0.75, y + 0.75)
            val n = rnd.nextGaussian() * 2.5
            val ch = IntArray(3) { k -> ((a[k] + b[k] + c[k] + d[k]) / 4.0 + n).toInt().coerceIn(0, 255) }
            (0xFF shl 24) or (ch[0] shl 16) or (ch[1] shl 8) or ch[2]
        }
    }

    /** The carton's true outline. */
    fun mask() = Mask(w, h, BooleanArray(w * h) { i -> val (o, d) = ray(i % w + 0.5, i / w + 0.5); hitBox(o, d) != null })

    /** Where to tap: the carton's top centre. */
    fun tapPoint() = cam.project(bx, by, bh)!!
}
