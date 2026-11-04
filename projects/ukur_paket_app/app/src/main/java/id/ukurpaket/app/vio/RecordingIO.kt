package id.ukurpaket.app.vio

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File

/**
 * Reads a sweep recording folder (recorder 0.2.x format) into the engine's input. Android-free: the picture decoding
 * is passed in, so the same code runs on the phone (BitmapFactory) and in the PC tests (ImageIO).
 * [decode]: frame file -> upright tracking grey (the caller shrinks 1280-wide frames by 2 and turns them upright).
 * [decodeMask]: mask file -> Bits at its own size (upright picture).
 */
object RecordingIO {
    private val json = Json { ignoreUnknownKeys = true }

    class Loaded(val input: SweepInput, val frameIndex: IntArray, val dir: File)

    fun load(dir: File, decode: (File) -> Gray, decodeMask: (File) -> Bits?, tracks: List<Track>? = null): Loaded {
        val ses = json.parseToJsonElement(File(dir, "session.json").readText()).jsonObject
        val realtime = ses["timestamp_source"]?.jsonPrimitive?.content == "REALTIME"
        val rows = File(dir, "frames.csv").readLines().drop(1).filter { it.isNotBlank() }.map { it.split(',') }
            .filter { File(dir, "frames/%05d.jpg".format(it[0].toInt())).exists() }.sortedBy { it[1].toLong() }
        val idx = IntArray(rows.size) { rows[it][0].toInt() }
        val tCam = DoubleArray(rows.size) { rows[it][1].toLong() / 1e9 }
        val arrival = if (rows.isNotEmpty() && rows.all { it.size > 6 && it[6].isNotBlank() }) DoubleArray(rows.size) { rows[it][6].toLong() / 1e9 } else null
        val acc = ArrayList<Sample>(); val gyr = ArrayList<Sample>(); val rv = ArrayList<Sample>(); val rvAbs = ArrayList<Sample>()
        File(dir, "imu.csv").forEachLine { line ->
            val p = line.split(',')
            if (p.size < 5 || p[0] == "sensor") return@forEachLine
            val t = p[1].toLongOrNull()?.div(1e9) ?: return@forEachLine
            val v = p.drop(2).mapNotNull { it.toDoubleOrNull() }.toDoubleArray()
            when (p[0]) {
                "accelerometer" -> acc.add(Sample(t, v)); "gyroscope" -> gyr.add(Sample(t, v))
                "game_rotation_vector" -> rv.add(Sample(t, v)); "rotation_vector" -> rvAbs.add(Sample(t, v))
            }
        }
        acc.sortBy { it.t }; gyr.sortBy { it.t }; rv.sortBy { it.t }; rvAbs.sortBy { it.t }
        val first = decode(File(dir, "frames/%05d.jpg".format(idx[0])))
        // focal prior from the Camera2 facts: focal (mm) / sensor width (mm) x sensor-side width, at the tracking width
        val size = ses["size"]?.jsonArray?.map { it.jsonPrimitive.int } ?: listOf(first.h, first.w)
        val side = size.max()
        val diag = File(dir, "diagnosis.json").takeIf { it.exists() }?.let { json.parseToJsonElement(it.readText()).jsonObject }
        val cam = diag?.get("cameras")?.jsonArray?.map { it.jsonObject }?.firstOrNull { (it["facing"]?.jsonPrimitive?.content ?: "back") == "back" }
        val fMm = cam?.get("focalLengthsMm")?.jsonArray?.firstOrNull()?.jsonPrimitive?.double
        val sMm = cam?.get("sensorSizeMm")?.jsonArray?.firstOrNull()?.jsonPrimitive?.double
        val fPrior = if (fMm != null && sMm != null && sMm > 0) fMm / sMm * side * (first.w.toDouble() / size.min()) else 0.85 * max(first.w, first.h)
        // the pick: its frame and mask, at the tracking size
        val pick = File(dir, "pick.json").takeIf { it.exists() }?.let { json.parseToJsonElement(it.readText()).jsonObject }
            ?: throw EngineFailed("Belum ada objek yang dipilih")
        val pf = pick.int("frame")
        val pos = idx.indexOf(pf).takeIf { it >= 0 } ?: throw EngineFailed("Foto pilihan tidak ada di rekaman")
        val raw = decodeMask(File(dir, pick["maskFile"]?.jsonPrimitive?.content ?: "mask.png")) ?: throw EngineFailed("Mask objek tidak terbaca")
        val m = Bits(first.w, first.h, BooleanArray(first.w * first.h) { i ->
            raw[(i % first.w) * raw.w / first.w, (i / first.w) * raw.h / first.h]
        })
        val cache = HashMap<Int, Gray>()
        val gray = { i: Int -> synchronized(cache) { cache.getOrPut(i) { decode(File(dir, "frames/%05d.jpg".format(idx[i]))).also { if (cache.size > 40) cache.clear() } } } }
        val inp = SweepInput(tCam, arrival, realtime, acc, gyr, rv.ifEmpty { rvAbs }, fPrior, first.w, first.h, gray, pos, m, tracks)
        return Loaded(inp, idx, dir)
    }

    private fun JsonObject.int(k: String) = this[k]!!.jsonPrimitive.int
    private fun max(a: Int, b: Int) = if (a > b) a else b
}
