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
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import id.ukurpaket.app.ar.ArCheck
import id.ukurpaket.app.ar.ArState
import id.ukurpaket.app.ar.DeviceCaps
import id.ukurpaket.app.ar.MeasureEngine
import id.ukurpaket.app.ar.ResultData
import id.ukurpaket.app.data.Locator
import id.ukurpaket.app.data.MarkerPdf
import id.ukurpaket.app.data.Measurement
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Order
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.data.Store
import id.ukurpaket.app.measure.Segmenter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

sealed class Screen {
    object Start : Screen()
    object Home : Screen()
    object History : Screen()
    object Settings : Screen()
    object Prep : Screen()
    object Measure : Screen()
    object Marker : Screen()
    object Weight : Screen()
    data class Saved(val id: String) : Screen()
    data class Detail(val id: String) : Screen()
}

/** What is being measured right now. */
data class Draft(val resi: String, val orderId: String?, val result: ResultData? = null)

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

    /** The AR session lives across parcels of one pickup ("mode beruntun"): floor kept, measured parcels marked. */
    private var engine: MeasureEngine? = null
    private var engineOrder: String? = null

    init {
        if (checkDevice) {
            viewModelScope.launch { check() }
            viewModelScope.launch(Dispatchers.Default) { loadSam() }
        }
    }

    private fun loadSam() {
        samState = try {
            val am = getApplication<Application>().assets
            segmenter = Segmenter(am.open("sam/encoder.onnx").use { it.readBytes() }, am.open("sam/decoder.onnx").use { it.readBytes() })
            SamState.READY
        } catch (e: Throwable) { SamState.FAILED }
    }

    fun engineFor(activity: Activity, depth: Boolean, recordDir: File?): MeasureEngine {
        val e = engine
        if (e != null && e.activity === activity && engineOrder == draft?.orderId) return e
        releaseEngine()
        return MeasureEngine(activity, depth, store.photosDir, recordDir) { segmenter }.also { engine = it; engineOrder = draft?.orderId }
    }

    fun releaseEngine() { engine?.let { it.pause(); it.close() }; engine = null; engineOrder = null }

    override fun onCleared() { releaseEngine(); segmenter?.close() }

    private suspend fun check() {
        val ctx = getApplication<Application>()
        caps = try {
            val st = ArCheck.availability(ctx)
            val depth = if (st == ArState.READY) withContext(Dispatchers.Default) { ArCheck.depthSupported(ctx) } else false
            DeviceCaps(st, depth)
        } catch (e: Exception) {
            DeviceCaps(ArState.ERROR, depth = false)
        }
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
    fun home() { releaseEngine(); stack.clear(); stack.add(Screen.Home) }
    fun tab(s: Screen) { releaseEngine(); stack.clear(); stack.add(Screen.Home); if (s != Screen.Home) stack.add(s) }

    fun toast(m: String) { message = m }

    // ---------------------------------------------------------- measuring
    fun startMeasure(resi: String, orderId: String?) {
        draft = Draft(resi, orderId)
        locator.refresh()
        val s = store.settings.value
        when {
            caps.mode == Mode.MARKER -> go(Screen.Marker)          // its first step shows the rules itself
            s.prepShown < 3 -> { store.update { it.copy(prepShown = it.prepShown + 1) }; go(Screen.Prep) }
            else -> go(measureScreen())
        }
    }

    fun measureScreen(): Screen = if (caps.mode == Mode.MARKER) Screen.Marker else Screen.Measure

    /** "Paket berikutnya": back to the list underneath, keeping the AR session for this pickup. */
    fun nextParcel(resi: String, orderId: String?) { stack.clear(); stack.add(Screen.Home); startMeasure(resi, orderId) }

    fun scanResi(activity: Activity) {
        GmsBarcodeScanning.getClient(activity).startScan()
            .addOnSuccessListener { b ->
                val code = b.rawValue?.trim().orEmpty()
                if (code.isNotEmpty()) openResi(code)
            }
            .addOnFailureListener { toast("Scan tidak bisa dibuka. Ketik nomor resi.") }
    }

    fun openResi(code: String) {
        val order = store.orders.firstOrNull { code in it.resi } ?: store.addAdHocOrder(code)
        val done = store.measurementFor(code)
        if (done != null) { go(Screen.Detail(done.id)); toast("Resi $code sudah diukur") } else startMeasure(code, order.id)
    }

    fun onMeasured(r: ResultData) {
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
        val loc = locator.fresh()
        val m = Measurement(resi = d.resi, orderId = d.orderId, lengthCm = 0.0, widthCm = 0.0, heightCm = 0.0,
            divisor = store.settings.value.divisor, mode = caps.mode, status = Status.HUB, confidence = 0, seconds = 0.0,
            photo = photo, note = reason, lat = loc?.latitude, lon = loc?.longitude, gpsM = loc?.accuracy)
        store.save(m)
        draft = null
        stack.removeAt(stack.size - 1)
        if (stack.lastOrNull() == Screen.Prep) stack.removeAt(stack.size - 1)
        go(Screen.Saved(m.id))
    }

    fun markerSheet(activity: Activity) {
        val f = MarkerPdf.write(File(getApplication<Application>().cacheDir, "kertas_penanda_A4.pdf"))
        share(activity, f, "application/pdf", "Cetak kertas penanda (A4, skala 100%)")
    }

    fun save(scaleKg: Double?) {
        val d = draft ?: return
        val div = store.settings.value.divisor
        val r = d.result ?: return
        val loc = locator.fresh()
        val m = Measurement(resi = d.resi, orderId = d.orderId, lengthCm = r.lengthCm, widthCm = r.widthCm, heightCm = r.heightCm,
            scaleKg = scaleKg, divisor = div, mode = r.mode, status = r.status, confidence = r.confidence,
            seconds = r.seconds, photo = r.photo, recording = r.recording,
            lat = loc?.latitude, lon = loc?.longitude, gpsM = loc?.accuracy)
        store.save(m)
        // next parcel of this pickup: the AR session keeps the floor and marks this one as done
        engine?.next("…" + d.resi.takeLast(4))
        draft = null
        stack.removeAt(stack.size - 1)
        if (stack.lastOrNull() == Screen.Prep) stack.removeAt(stack.size - 1)
        go(Screen.Saved(m.id))
    }

    fun nextInOrder(orderId: String?): String? {
        val o = store.orders.firstOrNull { it.id == orderId } ?: return null
        return o.resi.firstOrNull { store.measurementFor(it) == null }
    }

    fun order(id: String?): Order? = store.orders.firstOrNull { it.id == id }

    // ---------------------------------------------------------- sharing
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
}

@Composable
fun App(model: AppModel, activity: Activity) {
    BackHandler(enabled = model.stack.size > 1) { model.back() }
    Box(Modifier.fillMaxSize().background(C.bg)) {
        when (val s = model.screen) {
            Screen.Measure -> MeasureScreen(model, activity)
            Screen.Marker -> MarkerScreen(model, activity)
            else -> Box(Modifier.fillMaxSize().safeDrawingPadding()) {
                when (s) {
                    Screen.Start -> StartScreen(model, activity)
                    Screen.Home -> HomeScreen(model, activity)
                    Screen.History -> HistoryScreen(model, activity)
                    Screen.Settings -> SettingsScreen(model, activity)
                    Screen.Prep -> PrepScreen(model)
                    Screen.Weight -> WeightScreen(model)
                    is Screen.Saved -> SavedScreen(model, s.id)
                    is Screen.Detail -> DetailScreen(model, activity, s.id)
                    Screen.Measure, Screen.Marker -> Unit
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
