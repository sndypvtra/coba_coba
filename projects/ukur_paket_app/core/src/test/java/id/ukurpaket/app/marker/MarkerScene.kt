package id.ukurpaket.app.marker

import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.photo.Intrinsics
import java.io.File
import java.util.Random
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * A synthetic photo of a printed marker sheet lying on a floor, through a pinhole camera held [heightM] above it, looking
 * [downDeg] below the horizon, rolled [rollDeg] about its axis. The sheet (white, [paperMarginCells] of white round the
 * black square) lies where the ray through picture point ([atX], [atY]) (fractions) meets the floor, turned [yawDeg].
 * Each pixel averages 4 x 4 rays (anti-aliased edges), then the picture is blurred (Gaussian [blurPx]), lit unevenly
 * ([shading]: darker towards one corner) and given sensor noise ([noise] grey levels).
 */
class MarkerScene(
    val k: Intrinsics,
    val heightM: Double,
    val downDeg: Double,
    val rollDeg: Double = 0.0,
    val id: Int = 1,
    val sideM: Double = 0.16,
    val atX: Double = 0.5,
    val atY: Double = 0.7,
    val yawDeg: Double = 20.0,
    val paperMarginCells: Double = 0.9,
    val blurPx: Double = 0.8,
    val noise: Double = 3.0,
    val shading: Double = 0.25,
    val floorGrey: Double = 105.0,
    val seed: Long = 1,
    /** Tilt of the sheet's plane against the floor (degrees, about its own first axis): a sheet propped up, or a slope. */
    val sheetTiltDeg: Double = 0.0,
    /** Extra dark rectangles (fractions of the picture: x0, y0, x1, y1) drawn over everything: clutter or a cover. */
    val covers: List<DoubleArray> = emptyList(),
) {
    val up: V3
    private val e1: DoubleArray
    private val e2: DoubleArray
    private val n: DoubleArray
    private val tl: DoubleArray

    init {
        val d = downDeg * PI / 180; val r = rollDeg * PI / 180
        // up in camera axes (x right, y down, z forward) for a camera looking d below the horizon, then rolled
        val ux = 0.0; val uy = -cos(d); val uz = -sin(d)
        val rx = ux * cos(r) - uy * sin(r); val ry = ux * sin(r) + uy * cos(r)
        up = V3(rx.toFloat(), ry.toFloat(), uz.toFloat())
        val u = doubleArrayOf(rx, ry, uz)
        // centre of the sheet: the floor under picture point (atX, atY)
        val ray = doubleArrayOf((atX * k.w - k.cx) / k.fx, (atY * k.h - k.cy) / k.fy, 1.0)
        val den = -dot(ray, u)
        require(den > 0.05) { "that picture point is above the horizon" }
        val c = ray.map { it * heightM / den }.toDoubleArray()
        // axes on the floor: a level direction, turned by the yaw; e2 = e1 x up, so the sheet reads upright (not mirrored)
        val a0 = cross(u, doubleArrayOf(1.0, 0.0, 0.0)).let { v -> val l = norm(v); v.map { it / l } }.toDoubleArray()
        val b0 = cross(u, a0)
        val y = yawDeg * PI / 180
        var a = DoubleArray(3) { a0[it] * cos(y) + b0[it] * sin(y) }
        var b = cross(a, u)
        // the sheet tilted about its first axis
        val t = sheetTiltDeg * PI / 180
        var nn = DoubleArray(3) { -u[it] }                                  // into the floor
        if (t != 0.0) {
            b = DoubleArray(3) { b[it] * cos(t) + u[it] * sin(t) }
            nn = cross(a, b)
        }
        e1 = a; e2 = b; n = nn
        tl = DoubleArray(3) { c[it] - (a[it] + b[it]) * sideM / 2 }
    }

    /** The printed corners TL, TR, BR, BL in the picture (continuous positions). */
    fun truth(): List<P2> = listOf(0.0 to 0.0, 1.0 to 0.0, 1.0 to 1.0, 0.0 to 1.0).map { (p, q) ->
        val x = DoubleArray(3) { tl[it] + (e1[it] * p + e2[it] * q) * sideM }
        P2((k.fx * x[0] / x[2] + k.cx).toFloat(), (k.fy * x[1] / x[2] + k.cy).toFloat())
    }

    fun render(): Luma {
        val code = Aruco.DICT_4X4_50[id]
        val ss = 4
        val img = DoubleArray(k.w * k.h)
        val cell = sideM / Aruco.GRID
        for (py in 0 until k.h) for (px in 0 until k.w) {
            var acc = 0.0
            for (sy in 0 until ss) for (sx in 0 until ss) {
                val x = px + (sx + 0.5) / ss; val y = py + (sy + 0.5) / ss
                val ray = doubleArrayOf((x - k.cx) / k.fx, (y - k.cy) / k.fy, 1.0)
                acc += shade(ray, code, cell)
            }
            img[py * k.w + px] = acc / (ss * ss)
        }
        val blurred = if (blurPx > 0) blur(img, k.w, k.h, blurPx) else img
        val rnd = Random(seed)
        val out = ByteArray(k.w * k.h)
        for (i in out.indices) {
            val x = (i % k.w).toDouble() / k.w; val y = (i / k.w).toDouble() / k.h
            val light = 1.0 - shading * (0.6 * x + 0.4 * y)
            out[i] = (blurred[i] * light + rnd.nextGaussian() * noise).roundToInt().coerceIn(0, 255).toByte()
        }
        return Luma(k.w, k.h, out)
    }

    private fun shade(ray: DoubleArray, code: Int, cell: Double): Double {
        val xf = ray[0] / ray[2]; val yf = ray[1] / ray[2]
        for (c in covers) if (xf * k.fx + k.cx in c[0] * k.w..c[2] * k.w && yf * k.fy + k.cy in c[1] * k.h..c[3] * k.h) return 40.0
        val u = doubleArrayOf(up.x.toDouble(), up.y.toDouble(), up.z.toDouble())
        // the sheet's plane first (it may be tilted), then the floor
        val den = dot(ray, n)
        if (den > 1e-6) {
            val t = dot(tl, n) / den
            val p = DoubleArray(3) { ray[it] * t - tl[it] }
            val su = dot(p, e1) / cell; val sv = dot(p, e2) / cell
            val m = paperMarginCells
            if (su >= -m && sv >= -m && su < Aruco.GRID + m && sv < Aruco.GRID + m) {
                if (su < 0 || sv < 0 || su >= Aruco.GRID || sv >= Aruco.GRID) return 235.0
                val i = sv.toInt(); val j = su.toInt()
                if (i == 0 || j == 0 || i == Aruco.GRID - 1 || j == Aruco.GRID - 1) return 22.0
                val bit = (code shr (15 - ((i - 1) * 4 + (j - 1)))) and 1
                return if (bit == 1) 235.0 else 22.0
            }
        }
        val fd = -dot(ray, u)
        if (fd <= 1e-6) return 170.0                                       // wall / sky
        val t = heightM / fd
        val fx = ray[0] * t; val fz = ray[2] * t
        // a floor with some texture: tiles and a soft pattern
        val tile = if (((fx / 0.3).let { kotlin.math.floor(it) } + (fz / 0.3).let { kotlin.math.floor(it) }).toInt() % 2 == 0) 0.0 else 14.0
        return floorGrey + tile + 10 * sin(fx * 23) * cos(fz * 17)
    }

    /** The picture as an 8-bit grey PNG (written by hand: the Android unit-test classpath has no ImageIO). */
    fun save(img: Luma, f: File) {
        val raw = java.io.ByteArrayOutputStream()
        for (y in 0 until img.h) { raw.write(0); raw.write(img.px, y * img.w, img.w) }
        fun chunk(o: java.io.DataOutputStream, type: String, data: ByteArray) {
            o.writeInt(data.size); val t = type.toByteArray(Charsets.US_ASCII); o.write(t); o.write(data)
            val crc = java.util.zip.CRC32(); crc.update(t); crc.update(data); o.writeInt(crc.value.toInt())
        }
        f.parentFile?.mkdirs()
        java.io.DataOutputStream(f.outputStream().buffered()).use { o ->
            o.write(byteArrayOf(0x89.toByte(), 'P'.code.toByte(), 'N'.code.toByte(), 'G'.code.toByte(), 13, 10, 26, 10))
            val ihdr = java.io.ByteArrayOutputStream().also { b -> java.io.DataOutputStream(b).apply { writeInt(img.w); writeInt(img.h); write(8); write(0); write(0); write(0); write(0) } }
            chunk(o, "IHDR", ihdr.toByteArray())
            val z = java.io.ByteArrayOutputStream(); java.util.zip.DeflaterOutputStream(z).use { it.write(raw.toByteArray()) }
            chunk(o, "IDAT", z.toByteArray())
            chunk(o, "IEND", ByteArray(0))
        }
    }

    companion object {
        /** A DT50-like lens for its 960 x 1280 upright picture: about 66 degrees across. */
        fun dt50(w: Int = 960, h: Int = 1280): Intrinsics {
            val f = (w / 2.0 / kotlin.math.tan(33.0 * PI / 180)).toFloat()
            return Intrinsics(f, f, w / 2f, h / 2f, w, h)
        }

        fun dot(a: DoubleArray, b: DoubleArray) = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
        fun cross(a: DoubleArray, b: DoubleArray) = doubleArrayOf(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        fun norm(a: DoubleArray) = sqrt(dot(a, a))

        fun blur(src: DoubleArray, w: Int, h: Int, sigma: Double): DoubleArray {
            val r = max(1, (3 * sigma).toInt())
            val kern = DoubleArray(2 * r + 1) { exp(-((it - r) * (it - r)) / (2 * sigma * sigma)) }.let { k -> val s = k.sum(); k.map { it / s } }
            val tmp = DoubleArray(w * h); val out = DoubleArray(w * h)
            for (y in 0 until h) for (x in 0 until w) { var s = 0.0; for (i in -r..r) s += src[y * w + min(w - 1, max(0, x + i))] * kern[i + r]; tmp[y * w + x] = s }
            for (y in 0 until h) for (x in 0 until w) { var s = 0.0; for (i in -r..r) s += tmp[min(h - 1, max(0, y + i)) * w + x] * kern[i + r]; out[y * w + x] = s }
            return out
        }
    }
}
