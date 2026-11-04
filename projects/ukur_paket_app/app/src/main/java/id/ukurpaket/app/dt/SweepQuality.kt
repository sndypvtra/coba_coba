package id.ukurpaket.app.dt

import java.io.File
import kotlin.math.sqrt

/**
 * Is a recorded sweep good enough for the solver? Read back from the files the recorder wrote, so the numbers are what
 * the PC will see. Scale comes from the accelerometer only when the phone really accelerates, and the shape only
 * when the view turns, so both are checked, not just the file counts.
 */
data class SweepQuality(
    val seconds: Double, val frames: Int, val savedFps: Double, val maxGapMs: Double, val blurry: Int,
    val accelHz: Double, val gyroHz: Double, val turnDeg: Double, val accelStd: Double, val imuCoversFrames: Boolean,
    val bestFrame: Int, val checks: List<Check>,
) {
    val level get() = when { checks.any { it.level == Level.FAIL } -> Level.FAIL; checks.any { it.level == Level.WARN } -> Level.WARN; else -> Level.OK }
}

object SweepAnalysis {
    data class Frame(val index: Int, val t: Long, val sharpness: Double, val arrival: Long? = null)
    data class Imu(val sensor: String, val t: Long, val x: Double, val y: Double, val z: Double, val w: Double? = null)

    private val KEEP = setOf("accelerometer", "gyroscope", "game_rotation_vector", "rotation_vector")

    /** Angular rate from the fused orientation (rotation vector), for phones whose gyroscope sends nothing. */
    fun gyroFromRotationVector(rv: List<Imu>): List<Imu> {
        fun q(i: Imu): DoubleArray { val w = i.w ?: sqrt(maxOf(0.0, 1 - i.x * i.x - i.y * i.y - i.z * i.z)); return doubleArrayOf(w, i.x, i.y, i.z) }
        return rv.zipWithNext().mapNotNull { (a, b) ->
            val dt = (b.t - a.t) / 1e9
            if (dt <= 0 || dt > 0.1) return@mapNotNull null
            val qa = q(a); val qb = q(b)
            // rate in the device frame: 2 * vec(conj(qa) * qb) / dt
            val w = qa[0] * qb[0] + qa[1] * qb[1] + qa[2] * qb[2] + qa[3] * qb[3]
            val sgn = if (w < 0) -1.0 else 1.0
            val x = qa[0] * qb[1] - qa[1] * qb[0] - qa[2] * qb[3] + qa[3] * qb[2]
            val y = qa[0] * qb[2] + qa[1] * qb[3] - qa[2] * qb[0] - qa[3] * qb[1]
            val z = qa[0] * qb[3] - qa[1] * qb[2] + qa[2] * qb[1] - qa[3] * qb[0]
            Imu("gyroscope", (a.t + b.t) / 2, 2 * sgn * x / dt, 2 * sgn * y / dt, 2 * sgn * z / dt)
        }
    }

    fun read(dir: File, sameClock: Boolean): SweepQuality {
        val frames = File(dir, "frames.csv").takeIf { it.exists() }?.readLines()?.drop(1)?.mapNotNull { l ->
            l.split(',').takeIf { it.size >= 3 }?.let { Frame(it[0].toInt(), it[1].toLong(), it[2].toDouble(), it.getOrNull(6)?.toLongOrNull()) }
        }.orEmpty().sortedBy { it.t }
        val imu = File(dir, "imu.csv").takeIf { it.exists() }?.useLines { ls ->
            ls.drop(1).mapNotNull { l ->
                val p = l.split(',')
                if (p.size < 5 || p[0] !in KEEP) null
                else Imu(p[0], p[1].toLong(), p[2].toDouble(), p[3].toDouble(), p[4].toDouble(), p.getOrNull(5)?.toDoubleOrNull())
            }.toList()
        }.orEmpty()
        return analyse(frames, imu, sameClock)
    }

    fun analyse(framesIn: List<Frame>, imu: List<Imu>, sameClock: Boolean): SweepQuality {
        // a camera clock that is not the sensors' one: moved onto it by the frames' arrival times (median offset)
        val offsets = framesIn.mapNotNull { f -> f.arrival?.let { it - f.t } }.sorted()
        val mapped = !sameClock && offsets.isNotEmpty()
        val frames = if (mapped) framesIn.map { it.copy(t = it.t + offsets[offsets.size / 2]) } else framesIn
        val acc = imu.filter { it.sensor == "accelerometer" }.sortedBy { it.t }
        val realGyro = imu.filter { it.sensor == "gyroscope" }.sortedBy { it.t }
        val rv = imu.filter { it.sensor == "game_rotation_vector" }.ifEmpty { imu.filter { it.sensor == "rotation_vector" } }.sortedBy { it.t }
        val fromRv = realGyro.isEmpty() && rv.size > 2
        val gyr = if (fromRv) gyroFromRotationVector(rv) else realGyro
        fun hz(l: List<Imu>) = if (l.size > 2) (l.size - 1) / ((l.last().t - l.first().t) / 1e9) else 0.0
        val secs = if (frames.size > 1) (frames.last().t - frames.first().t) / 1e9 else 0.0
        val gaps = frames.zipWithNext { a, b -> (b.t - a.t) / 1e6 }
        var turn = 0.0
        for ((a, b) in gyr.zipWithNext()) {
            val dt = (b.t - a.t) / 1e9
            if (dt in 0.0..0.1) turn += sqrt(a.x * a.x + a.y * a.y + a.z * a.z) * dt
        }
        val mags = acc.map { sqrt(it.x * it.x + it.y * it.y + it.z * it.z) }
        val mean = mags.average().takeIf { !it.isNaN() } ?: 0.0
        val std = if (mags.size > 1) sqrt(mags.sumOf { (it - mean) * (it - mean) } / (mags.size - 1)) else 0.0
        val med = frames.map { it.sharpness }.sorted().let { if (it.isEmpty()) 0.0 else it[it.size / 2] }
        val blurry = frames.count { it.sharpness < 0.4 * med }
        val covers = (sameClock || mapped) && acc.isNotEmpty() && gyr.isNotEmpty() && frames.isNotEmpty() &&
            acc.first().t <= frames.first().t && acc.last().t >= frames.last().t && gyr.first().t <= frames.first().t && gyr.last().t >= frames.last().t
        // the sharpest frame in the middle half: the view the object is picked in
        val mid = frames.drop(frames.size / 4).dropLast(frames.size / 4).ifEmpty { frames }
        val best = mid.maxByOrNull { it.sharpness }?.index ?: 0
        val q = SweepQuality(secs, frames.size, if (secs > 0) (frames.size - 1) / secs else 0.0, gaps.maxOrNull() ?: 0.0, blurry,
            hz(acc), hz(gyr), Math.toDegrees(turn), std, covers, best, emptyList())
        return q.copy(checks = checks(q, sameClock, mapped, fromRv))
    }

    private fun checks(q: SweepQuality, sameClock: Boolean, mapped: Boolean = false, fromRv: Boolean = false): List<Check> {
        val c = ArrayList<Check>()
        fun f1(d: Double) = "%.1f".format(d).replace('.', ',')
        c += when {
            q.seconds < 2 -> Check("dur", "Lama rekam", "${f1(q.seconds)} s", Level.FAIL, "Terlalu singkat: rekam 3–8 detik.")
            q.seconds > 20 -> Check("dur", "Lama rekam", "${f1(q.seconds)} s", Level.WARN, "Panjang: 3–8 detik sudah cukup.")
            else -> Check("dur", "Lama rekam", "${f1(q.seconds)} s", Level.OK, "")
        }
        c += when {
            q.savedFps < 6 -> Check("fps", "Foto tersimpan", "${q.frames} (${f1(q.savedFps)}/s)", Level.FAIL, "Terlalu jarang; HP mungkin sibuk.")
            q.savedFps < 10 -> Check("fps", "Foto tersimpan", "${q.frames} (${f1(q.savedFps)}/s)", Level.WARN, "Ideal ≥ 10 per detik.")
            else -> Check("fps", "Foto tersimpan", "${q.frames} (${f1(q.savedFps)}/s)", Level.OK, "")
        }
        c += if (q.maxGapMs > 250) Check("gap", "Jeda foto terlama", "${q.maxGapMs.toInt()} ms", Level.WARN, "Ada foto yang terlewat.")
        else Check("gap", "Jeda foto terlama", "${q.maxGapMs.toInt()} ms", Level.OK, "")
        c += when {
            q.gyroHz == 0.0 && q.accelHz == 0.0 -> Check("gyro", "Sensor gerak", "tidak ada data", Level.FAIL,
                "Tidak ada data sensor gerak sama sekali: tanpa accelerometer ukuran meter tidak bisa dihitung.")
            q.gyroHz == 0.0 -> Check("gyro", "Gyroscope", "tidak ada data", Level.WARN,
                "Gyroscope dan rotation vector diam (firmware HP tidak meneruskan datanya): putaran HP dihitung dari kamera.")
            fromRv -> Check("imu", "Sensor gerak", "acc ${q.accelHz.toInt()} Hz · rotasi ${q.gyroHz.toInt()} Hz", Level.WARN,
                "Gyroscope diam: putaran dari rotation vector (lebih halus, sedikit terlambat).")
            q.gyroHz < 90 || q.accelHz < 90 -> Check("imu", "Sensor gerak", "acc ${q.accelHz.toInt()} Hz · gyro ${q.gyroHz.toInt()} Hz", Level.WARN, "Ideal ≥ 150 Hz.")
            else -> Check("imu", "Sensor gerak", "acc ${q.accelHz.toInt()} Hz · gyro ${q.gyroHz.toInt()} Hz", Level.OK, "")
        }
        c += when {
            !sameClock && !mapped -> Check("sync", "Jam kamera & sensor", "terpisah", Level.WARN, "Selisih jam diperkirakan di PC.")
            mapped && !q.imuCoversFrames -> Check("sync", "Jam kamera & sensor", "terpisah · tidak lengkap", Level.WARN, "Data sensor tidak menutupi semua foto.")
            mapped -> Check("sync", "Jam kamera & sensor", "terpisah · dikoreksi", Level.WARN, "Dicocokkan dari waktu tiba foto; sisa selisihnya dihitung di PC.")
            !q.imuCoversFrames -> Check("sync", "Jam kamera & sensor", "tidak lengkap", Level.WARN, "Data sensor tidak menutupi semua foto.")
            else -> Check("sync", "Jam kamera & sensor", "cocok", Level.OK, "")
        }
        c += when {
            q.gyroHz == 0.0 -> Check("turn", "Putaran HP", "dihitung dari kamera", Level.INFO, "Tanpa data sensor putaran, sudutnya dihitung saat mengukur.")
            q.turnDeg < 25 -> Check("turn", "Putaran HP", "${q.turnDeg.toInt()}°", Level.FAIL, "Kurang berputar: kelilingi objek ±45–90°.")
            q.turnDeg < 40 -> Check("turn", "Putaran HP", "${q.turnDeg.toInt()}°", Level.WARN, "Lebih baik ≥ 45°.")
            else -> Check("turn", "Putaran HP", "${q.turnDeg.toInt()}°", Level.OK, "")
        }
        // scale is only observable when the phone accelerates: a still or purely rotating phone gives no metres
        c += when {
            q.accelStd < 0.15 -> Check("acc", "Gerak geser HP", "${f1(q.accelStd)} m/s²", Level.FAIL, "HP hampir diam: geser HP sambil mengelilingi objek.")
            q.accelStd < 0.35 -> Check("acc", "Gerak geser HP", "${f1(q.accelStd)} m/s²", Level.WARN, "Gerakan kecil: skala kurang teliti.")
            q.accelStd > 6 -> Check("acc", "Gerak geser HP", "${f1(q.accelStd)} m/s²", Level.WARN, "Terlalu kasar/berguncang.")
            else -> Check("acc", "Gerak geser HP", "${f1(q.accelStd)} m/s²", Level.OK, "")
        }
        c += if (q.frames > 0 && q.blurry > q.frames / 3) Check("blur", "Foto blur", "${q.blurry} dari ${q.frames}", Level.WARN, "Gerak lebih pelan atau tambah cahaya.")
        else Check("blur", "Foto blur", "${q.blurry} dari ${q.frames}", Level.OK, "")
        return c
    }

    /** The plain-words verdict for the review screen. */
    fun verdict(q: SweepQuality) = when (q.level) {
        Level.FAIL -> "Rekaman belum layak: ulangi (lihat tanda merah)."
        Level.WARN -> "Rekaman bisa dipakai, dengan catatan."
        else -> "Rekaman layak untuk engine tanpa ARCore."
    }

}
