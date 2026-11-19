package id.ukuraja.app.ui

import android.app.Activity
import android.app.Application
import android.content.Intent
import android.os.Build
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.FileProvider
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import id.ukuraja.app.data.Locator
import id.ukuraja.app.data.Measurement
import id.ukuraja.app.data.Status
import id.ukuraja.app.data.Store
import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.scan.HardwareScanner
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File

sealed class Screen {
    object Home : Screen()
    object History : Screen()
    object Settings : Screen()
    /** The label scanner: the camera reads the resi's barcode. */
    object Scan : Screen()
    /** How to measure: six illustrated steps; [page] is the one it opens on (0-based). */
    data class Guide(val page: Int = 0) : Screen()
    /** Photos of the parcel: taken, picked and measured on the phone. */
    object Photo : Screen()
    object Weight : Screen()
    data class Saved(val id: String) : Screen()
    data class Detail(val id: String) : Screen()
}

/** The size the photos gave, carried to the weight screen. */
data class PhotoOutcome(
    val lengthCm: Double, val widthCm: Double, val heightCm: Double,
    val confidence: Int, val status: Status,
    val evidence: String?, val session: String?,
    val scaleSource: String, val cameraM: Double, val photos: Int,
)

/** The parcel being measured. [replaces]: its earlier record when measured again ("Ukur ulang"), dropped once saved. */
data class Draft(val resi: String, val result: PhotoOutcome? = null, val replaces: String? = null)

enum class ModelState { LOADING, READY, FAILED }

class AppModel @JvmOverloads constructor(app: Application, preload: Boolean = true) : AndroidViewModel(app) {
    val store = Store(app)
    val stack = mutableStateListOf<Screen>(Screen.Home)
    var draft by mutableStateOf<Draft?>(null)
    var message by mutableStateOf<String?>(null)
    val locator = Locator(app)
    val photo = PhotoFlow(this)

    /** MobileSAM-512 (the parcel's outline from a tap or a box), loaded once. */
    @Volatile var sam: Segmenter? = null
        private set
    var samState by mutableStateOf(ModelState.LOADING)
        private set
    private val samLock = Mutex()

    suspend fun samNow(): Segmenter? = samLock.withLock {
        sam ?: withContext(Dispatchers.Default) {
            runCatching {
                val am = getApplication<Application>().assets
                val threads = (Runtime.getRuntime().availableProcessors() / 2).coerceIn(2, 4)
                Segmenter(am.open("sam/encoder512.onnx").use { it.readBytes() }, am.open("sam/decoder512.onnx").use { it.readBytes() }, threads = threads)
            }.getOrNull()
        }.also { sam = it; samState = if (it != null) ModelState.READY else ModelState.FAILED }
    }

    init {
        // both models load while the courier scans the first label: the first photo is answered sooner
        if (preload) viewModelScope.launch { samNow(); photo.depthNow() }
    }

    override fun onCleared() {
        sam?.let { s -> sam = null; Thread { Thread.sleep(3000); s.close() }.start() }
        photo.close()
    }

    // ---------------------------------------------------------- navigation
    val screen get() = stack.last()
    fun go(s: Screen) { stack.add(s) }
    fun back() { if (stack.size > 1) stack.removeAt(stack.size - 1) }
    fun home() { stack.clear(); stack.add(Screen.Home) }
    fun tab(s: Screen) { stack.clear(); stack.add(Screen.Home); if (s != Screen.Home) stack.add(s) }
    fun toast(m: String) { message = m }

    /** Drops the measuring screens (photo, weight) from the top of the stack. */
    internal fun leaveMeasuring() {
        while (stack.size > 1 && stack.last().let { it == Screen.Photo || it == Screen.Weight }) stack.removeAt(stack.size - 1)
    }

    // ---------------------------------------------------------- scanning
    /**
     * Opens the app's own label scanner ([ScanScreen]). It runs on the bundled ML Kit model and CameraX, so it works
     * without Google Play services and offline, as on a PDA. Linear codes only: the label's QR codes are never read.
     */
    @Suppress("UNUSED_PARAMETER")
    fun scanResi(activity: Activity) = go(Screen.Scan)

    /** A built-in scanner key (Urovo PDA): shown on home; also switched on by the first hardware scan. */
    var hardwareScanner by mutableStateOf(HardwareScanner.builtIn(Build.MANUFACTURER, Build.BRAND))
        internal set

    /** Screens where a hardware scan opens a parcel; they have no text field, so keyboard-output scans are read too. */
    val takesHardwareScan get() = screen.let {
        it == Screen.Home || it == Screen.Scan || it == Screen.History || it is Screen.Guide || it is Screen.Saved || it is Screen.Detail
    }

    fun onHardwareScan(raw: String) {
        hardwareScanner = true
        val code = raw.trim()
        when {
            code.isEmpty() -> Unit
            HardwareScanner.looksLikeQr(code) -> toast("Itu kode QR. Scan barcode garis (resi) di label.")
            takesHardwareScan -> openResi(code)
            screen == Screen.Settings -> toast("Kembali ke Ukur untuk scan resi")
            else -> toast("Selesaikan paket ${draft?.resi ?: "ini"} dulu, lalu scan berikutnya")
        }
    }

    /** The scanned or typed number: measured already -> its record, otherwise measuring starts. */
    fun openResi(raw: String) {
        val code = raw.trim()
        if (code.isEmpty()) return
        home()
        val done = store.measurementFor(code)
        if (done != null) { go(Screen.Detail(done.id)); toast("Resi $code sudah diukur") } else startMeasure(code)
    }

    fun startMeasure(resi: String, replaces: String? = null) {
        draft = Draft(resi, replaces = replaces)
        locator.refresh()
        photo.start()
        go(Screen.Photo)
    }

    // ---------------------------------------------------------- saving
    fun onMeasured(r: PhotoOutcome) {
        draft = draft?.copy(result = r) ?: return
        leaveMeasuring()
        go(Screen.Weight)
    }

    fun save(scaleKg: Double?) {
        val d = draft ?: return
        val r = d.result ?: return
        val s = store.settings.value
        val loc = locator.fresh()
        val m = Measurement(resi = d.resi, lengthCm = r.lengthCm, widthCm = r.widthCm, heightCm = r.heightCm, scaleKg = scaleKg,
            divisor = s.divisor, status = r.status, confidence = r.confidence, photo = r.evidence, session = r.session,
            scaleSource = r.scaleSource, cameraM = r.cameraM, photos = r.photos,
            lat = loc?.latitude, lon = loc?.longitude, gpsM = loc?.accuracy, operator = s.operator.ifBlank { null })
        store.save(m)
        d.replaces?.let { if (it != m.id) store.delete(it) }
        draft = null
        leaveMeasuring()
        go(Screen.Saved(m.id))
    }

    /**
     * Not measured here (a parcel the photo cannot read: very soft, glossy, too big for the picture): the record keeps
     * the photo, place and reason without a size; the hub's station measures it.
     */
    fun markHub(reason: String) {
        val d = draft ?: return
        val loc = locator.fresh()
        val s = store.settings.value
        val m = Measurement(resi = d.resi, lengthCm = 0.0, widthCm = 0.0, heightCm = 0.0, divisor = s.divisor, status = Status.HUB,
            confidence = 0, photo = photo.anyPhoto(), session = photo.dir?.path, note = reason,
            lat = loc?.latitude, lon = loc?.longitude, gpsM = loc?.accuracy, operator = s.operator.ifBlank { null })
        store.save(m)
        d.replaces?.let { store.delete(it) }
        draft = null
        leaveMeasuring()
        go(Screen.Saved(m.id))
    }

    // ---------------------------------------------------------- sharing
    /** Builds the file off the main thread (a ZIP can be large), then opens the share sheet. */
    fun shareFile(activity: Activity, mime: String, title: String, build: () -> File) {
        toast("Menyiapkan file…")
        viewModelScope.launch {
            val f = runCatching { withContext(Dispatchers.IO) { build() } }.getOrNull()
            if (f == null) toast("File tidak bisa dibuat. Coba lagi.") else { message = null; share(activity, f, mime, title) }
        }
    }

    fun share(activity: Activity, file: File, mime: String, title: String) {
        val uri = FileProvider.getUriForFile(activity, "${activity.packageName}.files", file)
        val i = Intent(Intent.ACTION_SEND).setType(mime).putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        activity.startActivity(Intent.createChooser(i, title))
    }

    /** A file for sharing in the cache folder (the FileProvider serves it). */
    fun cacheFile(name: String) = File(getApplication<Application>().cacheDir, name)

    /** The marker sheet PDF bundled with the app, copied where it can be shared or printed. */
    fun markerPdf(sheet: String): File {
        val f = cacheFile("UkurAja_marker_$sheet.pdf")
        getApplication<Application>().assets.open("marker/UkurAja_marker_$sheet.pdf").use { i -> f.outputStream().use { i.copyTo(it) } }
        return f
    }
}
