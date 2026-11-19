package id.ukuraja.app.ui

import android.app.Activity
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Handler
import android.os.Looper
import android.view.HapticFeedbackConstants
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathFillType
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.LocalLifecycleOwner
import id.ukuraja.app.scan.Hint
import id.ukuraja.app.scan.ResiReader
import id.ukuraja.app.scan.ScanCamera
import id.ukuraja.app.scan.ScanStep
import id.ukuraja.app.scan.Seen
import id.ukuraja.app.scan.Window
import kotlinx.coroutines.delay
import kotlin.math.min

/** The label scanner: point the window at the resi's barcode; it is read, confirmed with a beep, and measuring starts. */
@Composable
fun ScanScreen(model: AppModel, activity: Activity) {
    CameraPermission(model, activity) { LiveScanner(model) }
}

@Composable
private fun LiveScanner(model: AppModel) {
    val ctx = LocalContext.current
    val owner = LocalLifecycleOwner.current
    val view = LocalView.current
    val stepState = remember { mutableStateOf(ScanStep(null, null, emptyList(), Hint.AIM)) }
    val step by stepState
    var ready by remember { mutableStateOf(false) }
    var torchAvailable by remember { mutableStateOf(false) }
    var torch by remember { mutableStateOf(false) }
    val darkState = remember { mutableStateOf(false) }
    val dark by darkState
    var error by remember { mutableStateOf<String?>(null) }
    var typing by remember { mutableStateOf(false) }
    val cam = remember {
        ScanCamera(ctx, ResiReader(), object : ScanCamera.Callback {
            override fun onReady(hasTorch: Boolean) { ready = true; torchAvailable = hasTorch }
            override fun onStep(step: ScanStep) { stepState.value = step }
            override fun onDark(dark: Boolean) { darkState.value = dark }
            override fun onError(msg: String) { error = msg }
        })
    }
    DisposableEffect(Unit) { onDispose { cam.close() } }
    val resi = step.resi
    // read: a beep and a buzz, the number shown for a moment, then the parcel opens
    LaunchedEffect(resi) {
        if (resi == null) return@LaunchedEffect
        view.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
        beep()
        if (torch) cam.torch(false)
        delay(450)
        cam.close()
        model.openResi(resi)
    }
    ScanChrome(step, ready, torchAvailable, torch, dark, error,
        onBack = { model.back() },
        onTorch = { torch = !torch; cam.torch(torch) },
        onType = { typing = true },
        onGuide = { model.go(Screen.Guide(GuidePages.SCAN)) }) {
        AndroidView(factory = { c ->
            PreviewView(c).apply {
                scaleType = PreviewView.ScaleType.FIT_CENTER
                implementationMode = PreviewView.ImplementationMode.COMPATIBLE
                cam.bind(owner, this)
            }
        }, modifier = Modifier.fillMaxSize())
    }
    if (typing) ResiDialog(onDismiss = { typing = false }) { typing = false; cam.close(); model.openResi(it) }
}

/** A short scanner beep; silent where the phone cannot make one. */
private fun beep() {
    runCatching {
        val tone = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80)
        tone.startTone(ToneGenerator.TONE_PROP_BEEP, 150)
        Handler(Looper.getMainLooper()).postDelayed({ tone.release() }, 400)
    }
}

/** The scanner screen around its preview (also drawn by the screenshot test with a still picture). */
@Composable
internal fun ScanChrome(step: ScanStep, ready: Boolean, hasTorch: Boolean, torch: Boolean, dark: Boolean, error: String?,
                        onBack: () -> Unit, onTorch: () -> Unit, onType: () -> Unit, onGuide: () -> Unit, preview: @Composable () -> Unit) {
    Column(Modifier.fillMaxSize()) {
        TopBar("Scan resi", "Barcode garis di label paket", onBack = onBack) {
            Box(Modifier.size(44.dp).clip(RoundedCornerShape(22.dp)).clickable(onClick = onGuide), contentAlignment = Alignment.Center) { Sym("help", 22.dp, C.ink) }
            if (hasTorch) Box(Modifier.size(44.dp).clip(RoundedCornerShape(22.dp)).background(if (torch) C.yellow else Color.Transparent)
                .clickable(onClick = onTorch), contentAlignment = Alignment.Center) {
                Sym(if (torch) "flashlight_on" else "flashlight_off", 22.dp, if (torch) C.onYellow else C.ink, filled = torch)
            }
        }
        BoxWithConstraints(Modifier.weight(1f).fillMaxWidth().background(Color.Black), contentAlignment = Alignment.Center) {
            val pw = min(maxWidth.value, maxHeight.value * 3f / 4f).dp
            Box(Modifier.size(pw, (pw.value * 4f / 3f).dp)) {
                preview()
                val t = loopClock(2000, still = 0.25f)
                Canvas(Modifier.fillMaxSize()) { scanOverlay(step, Window.DEFAULT, t) }
                if (dark && hasTorch && !torch) Box(Modifier.align(Alignment.TopStart).padding(8.dp)) {
                    Chip("Gelap: nyalakan senter", Tone.RED, "flashlight_on", onTorch)
                }
            }
        }
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (error != null) Banner(error, C.redL, C.red, "error") else ScanHint(step, ready)
            SecondaryButton("Ketik resi", "keyboard", Modifier.fillMaxWidth(), onClick = onType)
        }
    }
}

@Composable
private fun ScanHint(step: ScanStep, ready: Boolean) {
    val done = step.resi != null
    val (icon, text) = when {
        done -> "check_circle" to "Terbaca: ${step.resi}"
        !ready -> "photo_camera" to "Menyalakan kamera…"
        step.hint == Hint.HOLD -> "timer" to "Tahan sebentar, membaca ulang…"
        step.hint == Hint.MOVE_INTO_WINDOW -> "open_with" to "Geser HP: barcode resi harus di dalam kotak"
        else -> "barcode_scanner" to "Arahkan kotak ke barcode resi"
    }
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(if (done) C.greenL else Color.White).padding(14.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Sym(icon, 22.dp, if (done) C.green else C.brand, filled = done)
        Column(Modifier.weight(1f).padding(start = 10.dp)) {
            T(text, 14.5.sp, FontWeight.SemiBold, if (done) C.green else C.ink, maxLines = 2)
            if (!done) T("Jarak 10–25 cm. Kode QR tidak dibaca. Tidak terbaca? Nyalakan senter atau ketik resi.", 12.5.sp, color = C.t2)
        }
    }
}

/** The window (the rest dimmed), its corners, the moving scan line, and the barcodes found: the one being read in green. */
private fun DrawScope.scanOverlay(step: ScanStep, w: Window, t: Float) {
    val win = Rect(w.left * size.width, w.top * size.height, w.right * size.width, w.bottom * size.height)
    val dim = Path().apply {
        fillType = PathFillType.EvenOdd
        addRect(Rect(Offset.Zero, size))
        addRect(win)
    }
    drawPath(dim, Color.Black.copy(alpha = 0.45f))
    val found = step.target != null
    val corner = if (found) C.live else Color.White
    // the corners just outside the window's edge, so nothing of the dimmed area shows between them
    val l = 26.dp.toPx(); val sw = 4.dp.toPx(); val o = sw / 2
    for ((x, y, dx, dy) in listOf(listOf(win.left - o, win.top - o, 1f, 1f), listOf(win.right + o, win.top - o, -1f, 1f),
            listOf(win.left - o, win.bottom + o, 1f, -1f), listOf(win.right + o, win.bottom + o, -1f, -1f))) {
        drawLine(corner, Offset(x - dx * o, y), Offset(x + dx * l, y), sw); drawLine(corner, Offset(x, y - dy * o), Offset(x, y + dy * l), sw)
    }
    // the scan line sweeps the window while nothing is being read
    if (!found) {
        val p = if (t < 0.5f) t * 2 else 2 - t * 2
        val y = win.top + 10.dp.toPx() + p * (win.height - 20.dp.toPx())
        drawLine(C.brand.copy(alpha = 0.25f), Offset(win.left + 12.dp.toPx(), y), Offset(win.right - 12.dp.toPx(), y), 8.dp.toPx())
        drawLine(C.brand, Offset(win.left + 12.dp.toPx(), y), Offset(win.right - 12.dp.toPx(), y), 2.dp.toPx())
    }
    step.others.forEach { box(it, Color.White.copy(alpha = 0.7f), 2.dp.toPx()) }
    step.target?.let { box(it, C.live, 3.dp.toPx()) }
}

private fun DrawScope.box(s: Seen, color: Color, width: Float) {
    drawRect(color, Offset(s.left * size.width, s.top * size.height),
        Size((s.right - s.left) * size.width, (s.bottom - s.top) * size.height), style = Stroke(width))
}
