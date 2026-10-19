package id.ukurpaket.app.ui

import android.app.Activity
import android.app.Application
import android.content.Intent
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.Snackbar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import id.ukurpaket.app.ar.ArCheck
import id.ukurpaket.app.ar.ArState
import id.ukurpaket.app.ar.DeviceCaps
import id.ukurpaket.app.ar.MeasureEngine
import id.ukurpaket.app.ar.ResultData
import id.ukurpaket.app.data.Locator
import id.ukurpaket.app.data.Measurement
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.data.Store
import id.ukurpaket.app.measure.Segmenter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

sealed class Screen {
    object Start : Screen()
    object Home : Screen()
    object History : Screen()
    object Settings : Screen()
    object Prep : Screen()
    object Measure : Screen()
    /** This phone cannot measure (no ARCore): explain, offer ARCore install, or hand the parcel to the hub. */
    object NoAr : Screen()
    object Weight : Screen()
    data class Saved(val id: String) : Screen()
    data class Detail(val id: String) : Screen()
}

/** What is being measured right now. */
/** [replaces]: the earlier record of this parcel when it is measured again ("Ukur ulang"); dropped once the new one is saved. */
data class Draft(val resi: String, val result: ResultData? = null, val replaces: String? = null)

enum class SamState { LOADING, READY, FAILED }

class AppModel @JvmOverloads constructor(app: Application, checkDevice: Boolean = true) : AndroidViewModel(app) {
    val store = Store(app)
    val stack = mutableStateListOf<Screen>(Screen.Start)
    var caps by mutableStateOf(DeviceCaps(ArState.CHECKING, depth = false))
        internal set
    var draft by mutableStateOf<Draft?>(null)
    var message by mutableStateOf<String?>(null)
    val locator = Locator(app)

    /** MobileSAM, loaded once in the background (about 30 MB of model). Null until ready. */
    @Volatile var segmenter: Segmenter? = null
        private set
    var samState by mutableStateOf(SamState.LOADING)
        internal set

    /**
     * One measuring session: scan, measure, "Paket berikutnya"… until "Selesai". The AR session lives across its
     * parcels (floor kept, measured parcels marked), and the saved screen counts them.
     */
    var session by mutableStateOf<String?>(null)
        private set
    private var engine: MeasureEngine? = null
    private var engineSession: String? = null

    init { if (checkDevice) viewModelScope.launch { check() } }

    /** Only phones that can measure need the model: it takes ~100 MB of memory once loaded. */
    private fun loadSamIfNeeded() {
        if (caps.arcore != ArState.READY || segmenter != null || samLoading) return
        samLoading = true
        viewModelScope.launch {
            samState = withContext(Dispatchers.Default) { loadSam() }
            samLoading = false
        }
    }
    private var samLoading = false

    private fun loadSam(): SamState =
        try {
            val am = getApplication<Application>().assets
            segmenter = Segmenter(am.open("sam/encoder.onnx").use { it.readBytes() }, am.open("sam/decoder.onnx").use { it.readBytes() })
            SamState.READY
        } catch (e: Throwable) { SamState.FAILED }

    fun engineFor(activity: Activity, depth: Boolean, recordDir: File?): MeasureEngine {
        val e = engine
        if (e != null && e.activity === activity && engineSession == session) return e
        releaseEngine()
        return MeasureEngine(activity, depth, store.photosDir, recordDir) { segmenter }.also { engine = it; engineSession = session }
    }

    fun releaseEngine() { engine?.let { it.pause(); it.close() }; engine = null; engineSession = null }

    override fun onCleared() {
        val e = engine
        releaseEngine()
        // the model is freed only once the engine's worker has finished any cut-out still running
        val sam = segmenter
        segmenter = null
        if (sam != null) Thread { e?.awaitWorker(); sam.close() }.start()
    }

    private suspend fun check() {
        val ctx = getApplication<Application>()
        caps = try {
            val st = ArCheck.availability(ctx)
            val depth = if (st == ArState.READY) withContext(Dispatchers.Default) { ArCheck.depthSupported(ctx) } else false
            DeviceCaps(st, depth)
        } catch (e: Exception) {
            DeviceCaps(ArState.ERROR, depth = false)
        }
        loadSamIfNeeded()
    }

    fun recheck() { caps = caps.copy(arcore = ArState.CHECKING); viewModelScope.launch { check() } }

    fun install(activity: Activity) {
        val st = ArCheck.requestInstall(activity, userRequested = true)
        if (st == ArState.READY) recheck() else caps = caps.copy(arcore = st)
    }

    fun onResume(activity: Activity) {
        if (caps.arcore == ArState.NEEDS_INSTALL) {
            val st = ArCheck.requestInstall(activity, userRequested = false)
            if (st == ArState.READY) recheck()
        }
    }

    // ---------------------------------------------------------- navigation
    val screen get() = stack.last()
    fun go(s: Screen) { stack.add(s) }
    fun back() { if (stack.size > 1) stack.removeAt(stack.size - 1) }
    fun home() { endSession(); stack.clear(); stack.add(Screen.Home) }
    fun tab(s: Screen) { endSession(); stack.clear(); stack.add(Screen.Home); if (s != Screen.Home) stack.add(s) }

    /** "Selesai": the AR session is closed; the next scan starts a new measuring session. */
    private fun endSession() { releaseEngine(); session = null }

    fun toast(m: String) { message = m }

    // ---------------------------------------------------------- measuring
    fun startMeasure(resi: String, replaces: String? = null) {
        if (session == null) session = UUID.randomUUID().toString()
        draft = Draft(resi, replaces = replaces)
        locator.refresh()
        val s = store.settings.value
        when {
            caps.mode == Mode.NONE -> go(Screen.NoAr)
            s.prepShown < 3 -> { store.update { it.copy(prepShown = it.prepShown + 1) }; go(Screen.Prep) }
            else -> go(Screen.Measure)
        }
    }

    /**
     * Reads the label's barcode and uses its content as it is: no rules on the tracking number itself.
     * Only linear (1D) barcodes are read, so the label's QR codes are never picked up by mistake.
     */
    fun scanResi(activity: Activity) {
        val options = GmsBarcodeScannerOptions.Builder()
            .setBarcodeFormats(LINEAR_BARCODES.first(), *LINEAR_BARCODES.drop(1).toIntArray())
            .enableAutoZoom()
            .build()
        GmsBarcodeScanning.getClient(activity, options).startScan()
            .addOnSuccessListener { b -> b.rawValue?.let { openResi(it) } }
            .addOnFailureListener { toast("Scan tidak bisa dibuka. Ketik nomor resi.") }
    }

    /**
     * The scanned or typed number opens its parcel: measured already -> its record, otherwise measuring starts.
     * From the saved screen ("Paket berikutnya") the parcel opens on top of the home screen, the session goes on.
     */
    fun openResi(raw: String) {
        val code = raw.trim()
        if (code.isEmpty()) return
        stack.clear(); stack.add(Screen.Home)
        val done = store.measurementFor(code)
        if (done != null) { go(Screen.Detail(done.id)); toast("Resi $code sudah diukur") } else startMeasure(code)
    }

    fun onMeasured(r: ResultData) {
        if (screen != Screen.Measure) return
        draft = draft?.copy(result = r)
        stack.removeAt(stack.size - 1)          // the camera screen is done; back from weight goes to the list
        go(Screen.Weight)
    }

    /**
     * "Tandai ukur di hub": after repeated failures the parcel is not measured here; the record keeps the
     * photo, place and reason, and the hub's measuring station measures it.
     */
    fun markHub(reason: String, photo: String?) {
        val d = draft ?: return
        // the hub photo arrives a moment later: only act if the courier is still on this parcel's screen
        if (screen != Screen.Measure && screen != Screen.NoAr) return
        val loc = locator.fresh()
        val m = Measurement(resi = d.resi, session = session, lengthCm = 0.0, widthCm = 0.0, heightCm = 0.0,
            divisor = store.settings.value.divisor, mode = caps.mode, status = Status.HUB, confidence = 0, seconds = 0.0,
            photo = photo, note = reason, lat = loc?.latitude, lon = loc?.longitude, gpsM = loc?.accuracy)
        store.save(m)
        d.replaces?.let { store.delete(it) }
        draft = null
        leaveMeasuring()
        go(Screen.Saved(m.id))
    }

    /** Drops the measuring screens (camera / no-AR / weight, and the prep page under them) from the stack. */
    private fun leaveMeasuring() {
        while (stack.size > 1 && stack.last().let { it == Screen.Measure || it == Screen.NoAr || it == Screen.Weight || it == Screen.Prep })
            stack.removeAt(stack.size - 1)
    }

    fun save(scaleKg: Double?) {
        val d = draft ?: return
        val div = store.settings.value.divisor
        val r = d.result ?: return
        val loc = locator.fresh()
        val m = Measurement(resi = d.resi, session = session, lengthCm = r.lengthCm, widthCm = r.widthCm, heightCm = r.heightCm,
            scaleKg = scaleKg, divisor = div, mode = r.mode, status = r.status, confidence = r.confidence,
            seconds = r.seconds, photo = r.photo, recording = r.recording,
            lat = loc?.latitude, lon = loc?.longitude, gpsM = loc?.accuracy)
        store.save(m)
        d.replaces?.let { store.delete(it) }
        // next parcel of this session: the AR session keeps the floor and marks this one as done
        engine?.next("…" + d.resi.takeLast(4))
        draft = null
        leaveMeasuring()
        go(Screen.Saved(m.id))
    }

    /** How many parcels the session of [m] holds so far (1 for a record from no session). */
    fun sessionCount(m: Measurement, all: List<Measurement>): Int =
        if (m.session == null) 1 else all.count { it.session == m.session }

    // ---------------------------------------------------------- sharing
    /** Builds the file off the main thread (a ZIP of recordings can be large), then opens the share sheet. */
    fun shareFile(activity: Activity, mime: String, title: String, build: () -> File) {
        toast("Menyiapkan file…")
        viewModelScope.launch {
            val f = runCatching { withContext(Dispatchers.IO) { build() } }.getOrNull()
            if (f == null) toast("File tidak bisa dibuat. Coba lagi.") else { message = null; share(activity, f, mime, title) }
        }
    }

    fun share(activity: Activity, file: File, mime: String, title: String) {
        val uri = FileProvider.getUriForFile(activity, "${activity.packageName}.files", file)
        val i = Intent(Intent.ACTION_SEND).setType(mime).putExtra(Intent.EXTRA_STREAM, uri)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        activity.startActivity(Intent.createChooser(i, title))
    }

    fun zip(dirs: List<File>, name: String): File {
        val out = File(getApplication<Application>().cacheDir, name)
        ZipOutputStream(out.outputStream().buffered()).use { z ->
            for (d in dirs) d.walkTopDown().filter { it.isFile }.forEach { f ->
                z.putNextEntry(ZipEntry("${d.name}/${f.relativeTo(d).path}"))
                f.inputStream().use { it.copyTo(z) }
                z.closeEntry()
            }
        }
        return out
    }

    companion object {
        /** Every linear (1D) barcode type; QR, Data Matrix, PDF417 and Aztec (2D codes) are left out. */
        val LINEAR_BARCODES = listOf(
            Barcode.FORMAT_CODE_128, Barcode.FORMAT_CODE_39, Barcode.FORMAT_CODE_93, Barcode.FORMAT_CODABAR,
            Barcode.FORMAT_EAN_13, Barcode.FORMAT_EAN_8, Barcode.FORMAT_ITF, Barcode.FORMAT_UPC_A, Barcode.FORMAT_UPC_E,
        )
    }
}

@Composable
fun App(model: AppModel, activity: Activity) {
    BackHandler(enabled = model.stack.size > 1) { model.back() }
    Box(Modifier.fillMaxSize().background(C.bg)) {
        when (val s = model.screen) {
            Screen.Measure -> MeasureScreen(model, activity)
            else -> Box(Modifier.fillMaxSize().safeDrawingPadding()) {
                when (s) {
                    Screen.Start -> StartScreen(model, activity)
                    Screen.Home -> HomeScreen(model, activity)
                    Screen.History -> HistoryScreen(model, activity)
                    Screen.Settings -> SettingsScreen(model, activity)
                    Screen.Prep -> PrepScreen(model)
                    Screen.Weight -> WeightScreen(model)
                    is Screen.Saved -> SavedScreen(model, activity, s.id)
                    is Screen.Detail -> DetailScreen(model, activity, s.id)
                    Screen.NoAr -> NoArScreen(model, activity)
                    Screen.Measure -> Unit
                }
            }
        }
        val msg = model.message
        if (msg != null) {
            LaunchedEffect(msg) { delay(2600); model.message = null }
            Snackbar(Modifier.align(Alignment.BottomCenter).safeDrawingPadding().padding(16.dp)) { T(msg, color = androidx.compose.ui.graphics.Color.White) }
        }
    }
}
