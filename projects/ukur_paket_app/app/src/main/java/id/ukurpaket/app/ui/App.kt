package id.ukurpaket.app.ui

import android.app.Activity
import android.app.Application
import android.content.Intent
import android.os.Build
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
import androidx.compose.runtime.mutableStateMapOf
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
import id.ukurpaket.app.dt.Check
import id.ukurpaket.app.dt.Diagnosis
import id.ukurpaket.app.dt.Diagnostics
import id.ukurpaket.app.dt.ObjectPick
import id.ukurpaket.app.dt.Pick
import id.ukurpaket.app.dt.SweepRun
import id.ukurpaket.app.vio.EngineFailed
import id.ukurpaket.app.vio.SweepResult
import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.scan.HardwareScanner
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
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
    /** Test screens for phones without ARCore (Urovo DT20): what the phone offers, and sweep recordings for our own engine. */
    object Diag : Screen()
    object DtRecord : Screen()
    data class DtReview(val dir: String) : Screen()
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

    /** Only phones that can measure need the model up front: it takes ~100 MB of memory once loaded. */
    private fun loadSamIfNeeded() {
        if (caps.arcore != ArState.READY || segmenter != null) return
        viewModelScope.launch { samNow() }
    }
    private val samLock = Mutex()

    /** The model now, loading it if needed (the DT20 recorder picks objects with it although the phone has no ARCore). */
    suspend fun samNow(): Segmenter? = samLock.withLock {
        segmenter ?: run {
            samState = SamState.LOADING
            samState = withContext(Dispatchers.Default) { loadSam() }
            segmenter
        }
    }

    // ---------------------------------------------------------- DT20 test screens
    var diag by mutableStateOf<Diagnosis?>(null)
        internal set
    var diagRates by mutableStateOf<Map<String, Double>>(emptyMap())
        internal set
    var diagBusy by mutableStateOf<String?>(null)
        internal set

    fun diagChecks(): List<Check> = diag?.let { Diagnostics.checks(it, diagRates) }.orEmpty()

    /** Reads the phone (instant), then measures the real sensor rates for 3 s. */
    fun runDiagnosis() {
        if (diagBusy != null) return
        val ctx = getApplication<Application>()
        viewModelScope.launch {
            diagBusy = "Membaca HP…"
            diag = withContext(Dispatchers.Default) {
                Diagnosis(Diagnostics.device(ctx), caps.arcore.label, hardwareScanner, Diagnostics.sensors(ctx), Diagnostics.cameras(ctx),
                    samEncodeMs = diag?.samEncodeMs)
            }
            diagBusy = "Mengukur kecepatan sensor satu per satu…"
            diagRates = runCatching { Diagnostics.measureRates(ctx) { n -> diagBusy = "Mengukur sensor: ${n.replace('_', ' ')}…" } }.getOrDefault(emptyMap())
            diag = diag?.let { d -> d.copy(sensors = d.sensors.map { it.copy(measuredHz = diagRates[it.type]) }) }
            diagBusy = null
        }
    }

    /** Times one MobileSAM picture encoding: the slow half of picking an object (the prompt itself takes milliseconds). */
    fun timeSam() {
        if (diagBusy != null) return
        viewModelScope.launch {
            diagBusy = "Memuat MobileSAM…"
            val sam = samNow()
            if (sam == null) { diagBusy = null; toast("MobileSAM tidak bisa dimuat."); return@launch }
            diagBusy = "Menguji MobileSAM (bisa 10–30 detik di HP ini)…"
            val ms = withContext(Dispatchers.Default) {
                val w = 640; val h = 480
                val px = IntArray(w * h) { i -> val v = ((i % w) * 255 / w); (0xFF shl 24) or (v shl 16) or (((i / w) * 255 / h) shl 8) or 128 }
                val t0 = System.nanoTime(); sam.embed(px, w, h); (System.nanoTime() - t0) / 1_000_000
            }
            diag = diag?.copy(samEncodeMs = ms)
            diagBusy = null
        }
    }

    /** The diagnosis as a file, for sharing and for each recording. */
    fun diagFile(dir: File = getApplication<Application>().cacheDir): File? {
        val d = diag ?: return null
        val f = File(dir, if (dir == getApplication<Application>().cacheDir) "diagnostik_${d.device.model.replace(' ', '_')}.json" else "diagnosis.json")
        f.writeText(Diagnostics.json.encodeToString(Diagnosis.serializer(), d.copy(checks = diagChecks(), sensors = d.sensors)) + "\n")
        return f
    }

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

    /** The engine on a recording: where it is, and its answer. */
    data class SweepJob(val stage: String, val progress: Float, val result: SweepResult? = null, val error: String? = null) {
        val running get() = result == null && error == null
    }
    val sweepJobs = mutableStateMapOf<String, SweepJob>()

    /** Measures the picked object of a recording on the phone (camera + motion sensors, no ARCore). */
    fun runSweep(dir: File) {
        if (sweepJobs[dir.path]?.running == true) return
        sweepJobs[dir.path] = SweepJob("Menyiapkan", 0f)
        viewModelScope.launch {
            val r = runCatching {
                withContext(Dispatchers.Default) {
                    SweepRun.run(dir) { st, p -> viewModelScope.launch { if (sweepJobs[dir.path]?.running == true) sweepJobs[dir.path] = SweepJob(st, p) } }
                }
            }
            sweepJobs[dir.path] = r.fold({ SweepJob("Selesai", 1f, it) },
                { SweepJob("Gagal", 1f, error = (it as? EngineFailed)?.message ?: "Gagal menghitung: ${it.message ?: it.javaClass.simpleName}") })
        }
    }

    /** A sweep's size for the parcel being measured: on to its weight, as after the ARCore measuring screen. */
    fun useSweep(dir: File, r: SweepResult) {
        val d = draft ?: return
        draft = d.copy(result = ResultData(r.lengthCm, r.widthCm, r.heightCm, r.confidence, if (r.ok) Status.OK else Status.CHECK, r.seconds,
            SweepRun.evidenceFile(dir).takeIf { it.exists() }?.path, dir.path, Mode.SWEEP))
        leaveMeasuring()
        go(Screen.Weight)
    }

    /** Object picks waiting for or being cut out: recording folder -> "cutting" | "done" | "failed". */
    val pickJobs = mutableStateMapOf<String, String>()

    /**
     * The object touched on the recorder's live picture, cut out of the sweep's first frame (taken at that touch) once
     * recording has stopped: MobileSAM during the sweep would take the CPU the recording needs.
     * [nx], [ny] or [box] (x0, y0, x1, y1): fractions of the upright picture.
     */
    fun cutPick(dir: File, rotation: Int, nx: Float?, ny: Float?, box: FloatArray?) {
        pickJobs[dir.path] = "cutting"
        viewModelScope.launch {
            val ok = runCatching {
                val sam = samNow() ?: error("MobileSAM tidak bisa dimuat")
                withContext(Dispatchers.Default) {
                    val pic = ObjectPick.upright(dir, 0, rotation) ?: error("foto pertama tidak ada")
                    val t0 = System.nanoTime()
                    val e = sam.embed(ObjectPick.argb(pic), pic.width, pic.height)
                    val enc = (System.nanoTime() - t0) / 1_000_000
                    val t1 = System.nanoTime()
                    val b = box?.let { floatArrayOf(it[0] * pic.width, it[1] * pic.height, it[2] * pic.width, it[3] * pic.height) }
                    val tap = if (b == null && nx != null && ny != null) floatArrayOf(nx * pic.width, ny * pic.height) else null
                    val m = (if (b != null) sam.box(e, b[0], b[1], b[2], b[3]) else sam.tap(e, tap!![0], tap[1])).largestPart()
                    val dec = (System.nanoTime() - t1) / 1_000_000
                    ObjectPick.save(dir, Pick(0, ObjectPick.frameFile(dir, 0).relativeTo(dir).path, rotation, pic.width, pic.height,
                        if (b != null) "box" else "tap", tap?.toList(), b?.toList(), maskScore = m.score, maskAreaPx = m.area,
                        maskBox = m.bounds()?.toList(), samEncodeMs = enc, samDecodeMs = dec, name = "", tapeCm = listOf(null, null, null)), pic, m)
                }
            }
            pickJobs[dir.path] = if (ok.isSuccess) "done" else "failed"
            if (ok.isFailure) toast("Objek tidak bisa dipotong: pilih lagi di foto") else runSweep(dir)
        }
    }

    /** The recorder screen is done: its recording opens in its place. */
    fun openReview(dir: File) {
        if (screen == Screen.DtRecord) stack.removeAt(stack.size - 1)
        go(Screen.DtReview(dir.path))
    }

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

    /** A built-in scanner key (Urovo PDA): shown on the home screen; also switched on by the first hardware scan. */
    var hardwareScanner by mutableStateOf(HardwareScanner.builtIn(Build.MANUFACTURER, Build.BRAND))
        internal set

    /** Screens where a hardware scan opens a parcel; they have no text field, so keyboard-output scans can be read too. */
    val takesHardwareScan get() = screen.let { it == Screen.Home || it == Screen.History || it == Screen.Settings || it is Screen.Saved || it is Screen.Detail }

    /**
     * The scan key (Urovo broadcast or keyboard output). On the measuring screens a stray press must not drop the
     * parcel being measured, so it only says so.
     */
    fun onHardwareScan(raw: String) {
        hardwareScanner = true
        val code = raw.trim()
        when {
            code.isEmpty() -> Unit
            HardwareScanner.looksLikeQr(code) -> toast("Itu kode QR. Scan barcode garis (resi) di label.")
            takesHardwareScan -> openResi(code)
            screen == Screen.Start -> toast("Tunggu cek HP selesai, lalu scan lagi")
            screen == Screen.Diag || screen == Screen.DtRecord || screen is Screen.DtReview -> toast("Scanner tidak dipakai di layar uji")
            else -> toast("Selesaikan paket ${draft?.resi ?: "ini"} dulu, lalu scan berikutnya")
        }
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
        while (stack.size > 1 && stack.last().let { it == Screen.Measure || it == Screen.NoAr || it == Screen.Weight || it == Screen.Prep ||
                it == Screen.DtRecord || it is Screen.DtReview })
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
                    Screen.Diag -> DiagScreen(model, activity)
                    Screen.DtRecord -> DtRecordScreen(model, activity)
                    is Screen.DtReview -> DtReviewScreen(model, activity, s.dir)
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
