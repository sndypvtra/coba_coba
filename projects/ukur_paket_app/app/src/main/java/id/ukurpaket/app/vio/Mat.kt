package id.ukurpaket.app.vio

import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin
import kotlin.math.sqrt

/** Small dense linear algebra for the sweep engine (row-major DoubleArrays; 3x3 = 9 values). Android-free. */
object M3 {
    fun eye() = doubleArrayOf(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    fun diag(a: Double, b: Double, c: Double) = doubleArrayOf(a, 0.0, 0.0, 0.0, b, 0.0, 0.0, 0.0, c)

    fun mul(a: DoubleArray, b: DoubleArray): DoubleArray {
        val r = DoubleArray(9)
        for (i in 0 until 3) for (j in 0 until 3) r[3 * i + j] = a[3 * i] * b[j] + a[3 * i + 1] * b[3 + j] + a[3 * i + 2] * b[6 + j]
        return r
    }

    fun t(a: DoubleArray) = doubleArrayOf(a[0], a[3], a[6], a[1], a[4], a[7], a[2], a[5], a[8])
    fun mv(a: DoubleArray, v: DoubleArray, o: Int = 0) = doubleArrayOf(
        a[0] * v[o] + a[1] * v[o + 1] + a[2] * v[o + 2], a[3] * v[o] + a[4] * v[o + 1] + a[5] * v[o + 2], a[6] * v[o] + a[7] * v[o + 1] + a[8] * v[o + 2])
    /** a^T v */
    fun mtv(a: DoubleArray, v: DoubleArray, o: Int = 0) = doubleArrayOf(
        a[0] * v[o] + a[3] * v[o + 1] + a[6] * v[o + 2], a[1] * v[o] + a[4] * v[o + 1] + a[7] * v[o + 2], a[2] * v[o] + a[5] * v[o + 1] + a[8] * v[o + 2])

    /** exp of the rotation vector w (Rodrigues). */
    fun exp(wx: Double, wy: Double, wz: Double): DoubleArray {
        val th = sqrt(wx * wx + wy * wy + wz * wz)
        if (th < 1e-12) return doubleArrayOf(1.0, -wz, wy, wz, 1.0, -wx, -wy, wx, 1.0)
        val kx = wx / th; val ky = wy / th; val kz = wz / th
        val c = cos(th); val s = sin(th); val v = 1 - c
        return doubleArrayOf(
            c + kx * kx * v, kx * ky * v - kz * s, kx * kz * v + ky * s,
            ky * kx * v + kz * s, c + ky * ky * v, ky * kz * v - kx * s,
            kz * kx * v - ky * s, kz * ky * v + kx * s, c + kz * kz * v)
    }

    /** Rotation angle (rad). */
    fun angle(r: DoubleArray) = acos(((r[0] + r[4] + r[8] - 1) / 2).coerceIn(-1.0, 1.0))

    /** log: rotation vector of r. */
    fun log(r: DoubleArray): DoubleArray {
        val th = angle(r)
        if (th < 1e-9) return doubleArrayOf((r[7] - r[5]) / 2, (r[2] - r[6]) / 2, (r[3] - r[1]) / 2)
        val k = th / (2 * sin(th))
        return doubleArrayOf(k * (r[7] - r[5]), k * (r[2] - r[6]), k * (r[3] - r[1]))
    }

    /** Quaternion (x, y, z, w) -> rotation. */
    fun quat(x: Double, y: Double, z: Double, w: Double) = doubleArrayOf(
        1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
        2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
        2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y))

    /** Rotation taking unit vector a onto unit vector b. */
    fun align(a: DoubleArray, b: DoubleArray): DoubleArray {
        val v = doubleArrayOf(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        val s = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); val c = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
        if (s < 1e-12) return eye()
        val th = kotlin.math.atan2(s, c)
        return exp(v[0] / s * th, v[1] / s * th, v[2] / s * th)
    }

    fun inv(a: DoubleArray): DoubleArray? {
        val c00 = a[4] * a[8] - a[5] * a[7]; val c01 = a[5] * a[6] - a[3] * a[8]; val c02 = a[3] * a[7] - a[4] * a[6]
        val det = a[0] * c00 + a[1] * c01 + a[2] * c02
        if (abs(det) < 1e-300) return null
        val id = 1 / det
        return doubleArrayOf(
            c00 * id, (a[2] * a[7] - a[1] * a[8]) * id, (a[1] * a[5] - a[2] * a[4]) * id,
            c01 * id, (a[0] * a[8] - a[2] * a[6]) * id, (a[2] * a[3] - a[0] * a[5]) * id,
            c02 * id, (a[1] * a[6] - a[0] * a[7]) * id, (a[0] * a[4] - a[1] * a[3]) * id)
    }

    /** Eigenvalues of a symmetric 3x3, ascending (closed form). */
    fun symEig(a: DoubleArray): DoubleArray {
        val p1 = a[1] * a[1] + a[2] * a[2] + a[5] * a[5]
        if (p1 < 1e-30) return doubleArrayOf(a[0], a[4], a[8]).sortedArray()
        val q = (a[0] + a[4] + a[8]) / 3
        val p2 = (a[0] - q) * (a[0] - q) + (a[4] - q) * (a[4] - q) + (a[8] - q) * (a[8] - q) + 2 * p1
        val p = sqrt(p2 / 6)
        val b = DoubleArray(9) { (a[it] - if (it % 4 == 0) q else 0.0) / p }
        val r = (b[0] * (b[4] * b[8] - b[5] * b[7]) - b[1] * (b[3] * b[8] - b[5] * b[6]) + b[2] * (b[3] * b[7] - b[4] * b[6])) / 2
        val phi = acos(r.coerceIn(-1.0, 1.0)) / 3
        val e1 = q + 2 * p * cos(phi); val e3 = q + 2 * p * cos(phi + 2 * Math.PI / 3)
        return doubleArrayOf(e3, 3 * q - e1 - e3, e1)
    }
}

/** Dense symmetric positive (semi)definite systems. */
object Dense {
    /** Solves A x = b in place by Cholesky with a small diagonal shift; A (n x n, row-major) is overwritten. */
    fun solve(a: DoubleArray, b: DoubleArray, n: Int, shift: Double = 1e-9): DoubleArray {
        var md = 0.0
        for (i in 0 until n) md = max(md, abs(a[i * n + i]))
        val eps = shift * max(md, 1e-12)
        for (i in 0 until n) a[i * n + i] += eps
        cholesky(a, n)
        return cholSolve(a, b, n)
    }

    fun cholesky(a: DoubleArray, n: Int) {
        for (j in 0 until n) {
            var s = a[j * n + j]
            for (k in 0 until j) s -= a[j * n + k] * a[j * n + k]
            val d = sqrt(max(s, 1e-300))
            a[j * n + j] = d
            val inv = 1 / d
            for (i in j + 1 until n) {
                var t = a[i * n + j]
                val ri = i * n; val rj = j * n
                for (k in 0 until j) t -= a[ri + k] * a[rj + k]
                a[ri + j] = t * inv
            }
        }
    }

    fun cholSolve(l: DoubleArray, b: DoubleArray, n: Int): DoubleArray {
        val y = b.copyOf()
        for (i in 0 until n) { var s = y[i]; for (k in 0 until i) s -= l[i * n + k] * y[k]; y[i] = s / l[i * n + i] }
        for (i in n - 1 downTo 0) { var s = y[i]; for (k in i + 1 until n) s -= l[k * n + i] * y[k]; y[i] = s / l[i * n + i] }
        return y
    }

    /** Eigenvector of the smallest eigenvalue of a symmetric PSD matrix (inverse iteration), unit length. */
    fun smallestEigvec(a: DoubleArray, n: Int, iters: Int = 30): DoubleArray {
        val l = a.copyOf()
        var md = 0.0
        for (i in 0 until n) md = max(md, abs(l[i * n + i]))
        for (i in 0 until n) l[i * n + i] += 1e-10 * md
        cholesky(l, n)
        var x = DoubleArray(n) { 1.0 / sqrt(n.toDouble()) + 0.01 * ((it * 7919) % 13) }
        for (it in 0 until iters) {
            val y = cholSolve(l, x, n)
            var nn = 0.0; for (v in y) nn += v * v
            nn = sqrt(nn)
            x = DoubleArray(n) { y[it] / nn }
        }
        return x
    }
}
