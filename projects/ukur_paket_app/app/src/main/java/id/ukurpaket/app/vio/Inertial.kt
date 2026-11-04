package id.ukurpaket.app.vio

import kotlin.math.sqrt

/** One motion-sensor sample: time (s, sensor clock) and values. */
class Sample(val t: Double, val v: DoubleArray)

/**
 * World <- device rotation at any time. With the game rotation vector the world is gravity-aligned (z up), so gravity
 * is known; with only the gyroscope it is integrated from the first sample and gravity has to be solved for.
 */
class RotationSource(gyro: List<Sample>, rv: List<Sample>) {
    val fromRv = rv.size > 10
    private val t: DoubleArray
    private val q: Array<DoubleArray>          // quaternions (x, y, z, w), sign-continuous
    private val r: Array<DoubleArray>          // integrated gyro rotations

    init {
        if (fromRv) {
            t = DoubleArray(rv.size) { rv[it].t }
            q = Array(rv.size) { i ->
                val v = rv[i].v
                val w = if (v.size > 3) v[3] else sqrt(maxOf(0.0, 1 - v[0] * v[0] - v[1] * v[1] - v[2] * v[2]))
                doubleArrayOf(v[0], v[1], v[2], w)
            }
            for (i in 1 until q.size) {
                val d = q[i][0] * q[i - 1][0] + q[i][1] * q[i - 1][1] + q[i][2] * q[i - 1][2] + q[i][3] * q[i - 1][3]
                if (d < 0) for (j in 0 until 4) q[i][j] = -q[i][j]
            }
            r = emptyArray()
        } else {
            t = DoubleArray(gyro.size) { gyro[it].t }
            q = emptyArray()
            r = Array(gyro.size) { M3.eye() }
            for (i in 1 until gyro.size) {
                val h = t[i] - t[i - 1]; val w = gyro[i - 1].v
                r[i] = M3.mul(r[i - 1], M3.exp(w[0] * h, w[1] * h, w[2] * h))
            }
        }
    }

    val available get() = t.size > 2

    fun at(time: Double): DoubleArray {
        var lo = 0; var hi = t.size - 1
        if (time <= t[0]) hi = 1 else if (time >= t[hi]) lo = hi - 1 else {
            while (hi - lo > 1) { val m = (lo + hi) / 2; if (t[m] <= time) lo = m else hi = m }
        }
        val a = ((time - t[lo]) / (t[hi] - t[lo])).coerceIn(0.0, 1.0)
        return if (fromRv) {
            val x = DoubleArray(4) { q[lo][it] * (1 - a) + q[hi][it] * a }
            val n = sqrt(x[0] * x[0] + x[1] * x[1] + x[2] * x[2] + x[3] * x[3])
            M3.quat(x[0] / n, x[1] / n, x[2] / n, x[3] / n)
        } else {
            val d = M3.log(M3.mul(M3.t(r[lo]), r[hi]))
            M3.mul(r[lo], M3.exp(d[0] * a, d[1] * a, d[2] * a))
        }
    }
}

/** Accelerometer integrated between two frames, in the world frame, with its derivative by the accelerometer bias. */
class Preint(val dt: Double, val alpha: DoubleArray, val beta: DoubleArray, val ja: DoubleArray, val jb: DoubleArray)

object Inertial {
    const val G = 9.81
    const val SIG_POS = 0.01        // m/s on the position rows (divided by dt)
    const val SIG_VEL = 0.01        // m/s on the velocity rows
    const val SIG_BA = 0.3          // m/s^2 prior on the accelerometer bias

    fun preintegrate(times: DoubleArray, rot: RotationSource, acc: List<Sample>): List<Preint> {
        val out = ArrayList<Preint>()
        var j = 0
        for (a in 0 until times.size - 1) {
            val ta = times[a]; val tb = times[a + 1]
            while (j < acc.size && acc[j].t < ta) j++
            val al = DoubleArray(3); val be = DoubleArray(3); val ja = DoubleArray(9); val jb = DoubleArray(9)
            var tp = ta; var k = j
            while (k < acc.size && acc[k].t < tb) {
                val tn = acc[k].t; val h = tn - tp
                if (h > 0) step(rot.at(tp + h / 2), acc[maxOf(k - 1, 0)].v, h, al, be, ja, jb)
                tp = tn; k++
            }
            val h = tb - tp
            if (h > 0 && k > 0) step(rot.at(tp + h / 2), acc[k - 1].v, h, al, be, ja, jb)
            out.add(Preint(tb - ta, al, be, ja, jb))
        }
        return out
    }

    private fun step(r: DoubleArray, f: DoubleArray, h: Double, al: DoubleArray, be: DoubleArray, ja: DoubleArray, jb: DoubleArray) {
        val rf = M3.mv(r, f)
        for (i in 0 until 3) { al[i] += be[i] * h + 0.5 * rf[i] * h * h; be[i] += rf[i] * h }
        for (i in 0 until 9) { ja[i] += jb[i] * h + 0.5 * r[i] * h * h; jb[i] += r[i] * h }
    }

    class Alignment(val scale: Double, val accBias: DoubleArray, val gravity: DoubleArray, val scaleSd: Double, val rms: Double)

    /**
     * Metric scale, velocities, accelerometer bias (and gravity without the rotation vector) from the unit-scale camera
     * path [cs] (k x 3): s(c_b - c_a) - v_a dt - g dt^2/2 + Ja b = alpha ; v_b - v_a - g dt + Jb b = beta.
     */
    fun align(cs: Array<DoubleArray>, pre: List<Preint>, gravityKnown: DoubleArray?): Alignment {
        val k = cs.size; val ng = if (gravityKnown == null) 3 else 0
        val n = 1 + 3 * k + 3 + ng
        val vi = { i: Int -> 1 + 3 * i }; val bi = 1 + 3 * k; val gi = bi + 3
        val ata = DoubleArray(n * n); val aty = DoubleArray(n)
        var rows = 0; var ss = 0.0
        val rowsList = ArrayList<Pair<DoubleArray, Double>>()
        fun add(row: DoubleArray, y: Double) {
            val nz = row.indices.filter { row[it] != 0.0 }
            for (i in nz) { aty[i] += row[i] * y; for (j in nz) ata[i * n + j] += row[i] * row[j] }
            rows++; rowsList.add(row to y)
        }
        for (a in pre.indices) {
            val p = pre[a]; val b = a + 1; val dt = p.dt
            if (dt <= 0) continue
            for (j in 0 until 3) {
                val r = DoubleArray(n); r[0] = cs[b][j] - cs[a][j]; r[vi(a) + j] = -dt
                for (c in 0 until 3) r[bi + c] = p.ja[3 * j + c]
                var y = p.alpha[j]
                if (ng > 0) r[gi + j] = -0.5 * dt * dt else y += 0.5 * dt * dt * gravityKnown!![j]
                val w = 1 / (dt * SIG_POS)
                for (i in r.indices) r[i] *= w
                add(r, y * w)
                val r2 = DoubleArray(n); r2[vi(b) + j] = 1.0; r2[vi(a) + j] = -1.0
                for (c in 0 until 3) r2[bi + c] = p.jb[3 * j + c]
                var y2 = p.beta[j]
                if (ng > 0) r2[gi + j] = -dt else y2 += dt * gravityKnown!![j]
                for (i in r2.indices) r2[i] /= SIG_VEL
                add(r2, y2 / SIG_VEL)
            }
        }
        for (j in 0 until 3) { val r = DoubleArray(n); r[bi + j] = 1 / SIG_BA; add(r, 0.0) }
        val m = ata.copyOf()
        val x = Dense.solve(m, aty, n)
        for ((r, y) in rowsList) { var e = -y; for (i in r.indices) e += r[i] * x[i]; ss += e * e }
        // variance of the scale: (A^T A)^-1 [0,0] x residual variance
        val l = ata.copyOf(); Dense.cholesky(l, n)
        val e0 = DoubleArray(n).also { it[0] = 1.0 }
        val c0 = Dense.cholSolve(l, e0, n)[0]
        val dof = maxOf(1, rows - n)
        val g = gravityKnown ?: doubleArrayOf(x[gi], x[gi + 1], x[gi + 2])
        return Alignment(x[0], doubleArrayOf(x[bi], x[bi + 1], x[bi + 2]), g, sqrt(maxOf(0.0, c0 * ss / dof)), sqrt(ss / rows))
    }
}
