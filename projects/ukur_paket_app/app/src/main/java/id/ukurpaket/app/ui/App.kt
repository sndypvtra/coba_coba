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
import id.ukurpaket.app.ar.ResultData
import id.ukurpaket.app.data.Measurement
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Order
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.data.Store
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
    object Manual : Screen()
    object Weight : Screen()
    data class Saved(val id: String) : Screen()
    data class Detail(val id: String) : Screen()
}

/** What is being measured right now. */
data class Draft(val resi: String, val orderId: String?, val result: ResultData? = null, val manual: Measurement? = null)

class AppModel @JvmOverloads constructor(app: Application, checkDevice: Boolean = true) : AndroidViewModel(app) {
    val store = Store(app)
    val stack = mutableStateListOf<Screen>(Screen.Start)
    var caps by mutableStateOf(DeviceCaps(ArState.CHECKING, depth = false))
        internal set
    var draft by mutableStateOf<Draft?>(null)
    var message by mutableStateOf<String?>(null)

    init { if (checkDevice) viewModelScope.launch { check() } }

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
    fun home() { stack.clear(); stack.add(Screen.Home) }
    fun tab(s: Screen) { stack.clear(); stack.add(Screen.Home); if (s != Screen.Home) stack.add(s) }

    fun toast(m: String) { message = m }

    // ---------------------------------------------------------- measuring
    fun startMeasure(resi: String, orderId: String?) {
        draft = Draft(resi, orderId)
        val s = store.settings.value
        when {
            caps.mode == Mode.MANUAL -> go(Screen.Manual)
            s.prepShown < 3 -> { store.update { it.copy(prepShown = it.prepShown + 1) }; go(Screen.Prep) }
            else -> go(Screen.Measure)
        }
    }

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

    fun onManual(m: Measurement) {
        draft = draft?.copy(manual = m)
        stack.removeAt(stack.size - 1)
        go(Screen.Weight)
    }

    fun save(scaleKg: Double?) {
        val d = draft ?: return
        val div = store.settings.value.divisor
        val m = d.manual?.copy(scaleKg = scaleKg, divisor = div) ?: d.result?.let { r ->
            Measurement(resi = d.resi, orderId = d.orderId, lengthCm = r.lengthCm, widthCm = r.widthCm, heightCm = r.heightCm,
                scaleKg = scaleKg, divisor = div, mode = r.mode, status = r.status, confidence = r.confidence,
                seconds = r.seconds, photo = r.photo, recording = r.recording)
        } ?: return
        store.save(m)
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

    fun manualMeasurement(l: Double, w: Double, h: Double, photo: String?, note: String): Measurement? {
        val d = draft ?: return null
        return Measurement(resi = d.resi, orderId = d.orderId, lengthCm = l, widthCm = w, heightCm = h,
            mode = Mode.MANUAL, status = Status.MANUAL, confidence = 0, seconds = 0.0, photo = photo, note = note)
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
                    Screen.Manual -> ManualScreen(model, activity)
                    Screen.Weight -> WeightScreen(model)
                    is Screen.Saved -> SavedScreen(model, s.id)
                    is Screen.Detail -> DetailScreen(model, activity, s.id)
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
