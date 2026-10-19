package id.ukurpaket.app.data

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.File
import java.util.UUID
import kotlin.math.ceil

/** [label]: the phone's state on the start screen; [method]: how a record was measured. Plain words, no product names. */
enum class Mode(val label: String, val method: String) {
    AR_FULL("Siap Ukur", "Kamera AR + sensor jarak"),
    AR_BASIC("Mode Dasar", "Kamera AR"),
    NONE("Tidak Didukung", "Tidak diukur"),
}
enum class Status(val label: String) { OK("Akurat"), CHECK("Perlu Dicek"), HUB("Ukur di Hub") }

@Serializable
data class Measurement(
    val id: String = UUID.randomUUID().toString(),
    val resi: String,
    /** The measuring session (scan, measure, next parcel… until "Selesai") this parcel was measured in. */
    val session: String? = null,
    val lengthCm: Double,
    val widthCm: Double,
    val heightCm: Double,
    val scaleKg: Double? = null,
    val divisor: Int = 6000,
    val mode: Mode,
    val status: Status,
    val confidence: Int,
    val seconds: Double,
    val createdAt: Long = System.currentTimeMillis(),
    val photo: String? = null,
    val recording: String? = null,
    val note: String? = null,
    val synced: Boolean = false,
    val lat: Double? = null,
    val lon: Double? = null,
    /** GPS accuracy, metres. */
    val gpsM: Float? = null,
) {
    /** Not measured here: the parcel goes to the hub's measuring station. */
    val atHub get() = status == Status.HUB
    val volumeL get() = lengthCm * widthCm * heightCm / 1000.0
    val volumetricKg get() = lengthCm * widthCm * heightCm / divisor
    /** The weight the tariff uses: the larger of scale and volumetric, rounded up to 0,01 kg. */
    val chargedKg get() = ceil(maxOf(volumetricKg, scaleKg ?: 0.0) * 100.0) / 100.0
    val volumetricWins get() = volumetricKg >= (scaleKg ?: 0.0)
}

@Serializable
data class Settings(
    val divisor: Int = 6000,
    val record: Boolean = false,
    val prepShown: Int = 0,
    val courier: String = "Andi",
)

@Serializable
private data class Db(
    val measurements: List<Measurement> = emptyList(),
    val settings: Settings = Settings(),
)

/** Everything the app keeps, in one JSON file in app storage. Small, offline, easy to export. */
class Store(private val ctx: Context) {
    private val json = Json { ignoreUnknownKeys = true; prettyPrint = true; encodeDefaults = true }
    private val file = File(ctx.filesDir, "ukurpaket.json")
    private val db = MutableStateFlow(load())

    val measurements: StateFlow<List<Measurement>> get() = measurementsFlow
    private val measurementsFlow = MutableStateFlow(db.value.measurements)
    val settings = MutableStateFlow(db.value.settings)

    val photosDir get() = File(ctx.filesDir, "photos").apply { mkdirs() }
    val recordingsDir get() = File(ctx.filesDir, "recordings").apply { mkdirs() }

    fun measurementFor(resi: String) = measurementsFlow.value.lastOrNull { it.resi == resi }

    fun save(m: Measurement) {
        val list = measurementsFlow.value.filterNot { it.id == m.id } + m
        measurementsFlow.value = list
        write(db.value.copy(measurements = list))
    }

    fun delete(id: String) {
        val m = measurementsFlow.value.firstOrNull { it.id == id } ?: return
        m.photo?.let { File(it).delete() }
        m.recording?.let { File(it).deleteRecursively() }
        val list = measurementsFlow.value.filterNot { it.id == id }
        measurementsFlow.value = list
        write(db.value.copy(measurements = list))
    }

    fun update(f: (Settings) -> Settings) {
        val s = f(settings.value)
        settings.value = s
        write(db.value.copy(settings = s))
    }

    fun exportJson(): File {
        val out = File(ctx.cacheDir, "ukurpaket_export.json")
        out.writeText(json.encodeToString(measurementsFlow.value))
        return out
    }

    private fun write(d: Db) {
        db.value = d
        val tmp = File(file.path + ".tmp")
        tmp.writeText(json.encodeToString(d))
        tmp.renameTo(file)
    }

    private fun load(): Db {
        if (file.exists()) {
            // files of earlier test builds also hold a list of example pickups: that key is simply skipped
            runCatching { return json.decodeFromString<Db>(file.readText()) }
            // unreadable (e.g. written by an older test build): keep a copy instead of silently losing it
            file.copyTo(File(ctx.filesDir, "ukurpaket_${System.currentTimeMillis()}.bak.json"), overwrite = true)
        }
        return Db()
    }
}

/** Indonesian figures: 2,4 and 6.000. */
fun Double.id(d: Int = 1): String {
    val s = String.format(java.util.Locale.US, "%,.${d}f", this)
    return s.replace(",", "§").replace(".", ",").replace("§", ".")
}

fun Double.cm(): String = if (this >= 100) this.id(0) else this.id(if (this % 1.0 == 0.0) 0 else 1).removeSuffix(",0")
