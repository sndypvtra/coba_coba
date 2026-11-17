package id.ukuraja.app.data

import android.content.Context
import id.ukurpaket.app.marker.MarkerSheet
import id.ukurpaket.app.photo.CalSample
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.File
import java.util.UUID
import kotlin.math.ceil

enum class Status(val label: String) { OK("Akurat"), CHECK("Perlu Dicek"), HUB("Ukur di Hub") }

/** One parcel: its size from the photo mode (or none: measured at the hub), weight and evidence. */
@Serializable
data class Measurement(
    val id: String = UUID.randomUUID().toString(),
    val resi: String,
    val lengthCm: Double,
    val widthCm: Double,
    val heightCm: Double,
    /** Weight on a scale, kg (typed; null when there is no scale). */
    val scaleKg: Double? = null,
    val divisor: Int = 6000,
    val status: Status,
    val confidence: Int,
    val createdAt: Long = System.currentTimeMillis(),
    /** The evidence photo: the parcel with its measured box (and the marker outlined). */
    val photo: String? = null,
    /** The photo-mode folder (photos, masks, depth maps, records) behind the size. */
    val session: String? = null,
    val note: String? = null,
    /** Where the scale came from, in plain words ("Marker A4", "AI + kalibrasi"…). */
    val scaleSource: String? = null,
    /** Camera height above the floor the size was computed with, metres. */
    val cameraM: Double? = null,
    val photos: Int = 1,
    val lat: Double? = null,
    val lon: Double? = null,
    /** GPS accuracy, metres. */
    val gpsM: Float? = null,
    /** The courier or counter staff who measured it (Settings). */
    val operator: String? = null,
) {
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
    /** Name on the records and the export ("" = not set). */
    val operator: String = "",
    /** The black square's side of each printed sheet, measured with a ruler (mm): a printer may shrink the page. */
    val markerA4Mm: Double = MarkerSheet.A4.sideMm,
    val markerA3Mm: Double = MarkerSheet.A3.sideMm,
    /** Every photo with a usable marker also teaches the scale used when no marker is in the picture. */
    val learnFromMarker: Boolean = true,
    /** What it has learnt (CalSample.fromMarker): the depth model's factor, the standing height, the focus factor. */
    val photoCal: List<CalSample> = emptyList(),
    /** The marker guide was opened once (home then shows it as a small link only). */
    val guideSeen: Boolean = false,
) {
    /** The printed side of sheet [id], metres (null: not a sheet of this app). */
    fun markerSideM(id: Int): Double? = when (id) {
        MarkerSheet.A4.id -> markerA4Mm / 1000
        MarkerSheet.A3.id -> markerA3Mm / 1000
        else -> null
    }

    companion object {
        /** Marker samples kept: the latest ones, so a new phone holder or a new habit takes over within a day. */
        const val MAX_MARKER_SAMPLES = 20
        /** A side typed outside this range (mm) is a typo, not a printer's shrink. */
        val SIDE_RANGE = 100.0..400.0
    }
}

@Serializable
private data class Db(val measurements: List<Measurement> = emptyList(), val settings: Settings = Settings())

/** Everything the app keeps, in one JSON file in app storage: small, offline, easy to export. */
class Store(private val ctx: Context) {
    private val json = Json { ignoreUnknownKeys = true; prettyPrint = true; encodeDefaults = true }
    private val file = File(ctx.filesDir, "ukuraja.json")
    private val lock = Any()
    private var db = load()

    private val measurementsFlow = MutableStateFlow(db.measurements)
    val measurements: StateFlow<List<Measurement>> get() = measurementsFlow
    val settings = MutableStateFlow(db.settings)

    /** Photo-mode measurements (photos, masks, depth maps, records), one folder per parcel. */
    val photoSessionsDir get() = File(ctx.filesDir, "photo_sessions").apply { mkdirs() }

    fun measurementFor(resi: String) = measurementsFlow.value.lastOrNull { it.resi.equals(resi, ignoreCase = true) }

    fun save(m: Measurement) = synchronized(lock) {
        val list = measurementsFlow.value.filterNot { it.id == m.id } + m
        measurementsFlow.value = list
        write(db.copy(measurements = list))
    }

    /** Removes the record with its evidence photo and photo folder. */
    fun delete(id: String) = synchronized(lock) {
        val m = measurementsFlow.value.firstOrNull { it.id == id } ?: return
        m.photo?.let { File(it).delete() }
        m.session?.let { File(it).deleteRecursively() }
        val list = measurementsFlow.value.filterNot { it.id == id }
        measurementsFlow.value = list
        write(db.copy(measurements = list))
    }

    fun update(f: (Settings) -> Settings) = synchronized(lock) {
        val s = f(settings.value)
        settings.value = s
        write(db.copy(settings = s))
    }

    private fun write(d: Db) {
        db = d
        val tmp = File(file.path + ".tmp")
        tmp.writeText(json.encodeToString(d))
        if (!tmp.renameTo(file)) { file.delete(); tmp.renameTo(file) }
    }

    private fun load(): Db {
        if (file.exists()) {
            runCatching { return json.decodeFromString<Db>(file.readText()) }
            // unreadable: keep a copy instead of silently losing it
            file.copyTo(File(ctx.filesDir, "ukuraja_${System.currentTimeMillis()}.bak.json"), overwrite = true)
        }
        return Db()
    }
}

/** Indonesian figures: 2,4 and 6.000. */
fun Double.id(d: Int = 1): String {
    val s = String.format(java.util.Locale.US, "%,.${d}f", this)
    return s.replace(",", "§").replace(".", ",").replace("§", ".")
}

/** A size in cm as the label shows it: whole above 1 m, one decimal below, no trailing ",0". */
fun Double.cm(): String = if (this >= 100) this.id(0) else this.id(1).removeSuffix(",0")

/** A number typed with a comma or a point, or null. */
fun parseDecimal(s: String): Double? = s.trim().replace(',', '.').toDoubleOrNull()
