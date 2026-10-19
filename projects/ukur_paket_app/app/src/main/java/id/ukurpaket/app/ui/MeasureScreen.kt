package id.ukurpaket.app.ui

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.opengl.GLSurfaceView
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import id.ukurpaket.app.ar.EngineUi
import id.ukurpaket.app.ar.Hint
import id.ukurpaket.app.ar.MeasureEngine
import id.ukurpaket.app.ar.Phase
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.data.cm
import id.ukurpaket.app.data.id
import id.ukurpaket.app.measure.BoxResult
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File
import kotlin.math.abs
import kotlin.math.min
import kotlin.math.roundToInt

/** Camera and (optional) location permission, asked together when measuring starts. */
@Composable
fun CameraPermission(model: AppModel, activity: Activity, content: @Composable () -> Unit) {
    var granted by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(activity, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
    }
    val ask = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { r ->
        granted = r[Manifest.permission.CAMERA] == true || granted
        model.locator.refresh()
    }
    val perms = arrayOf(Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
    LaunchedEffect(Unit) { if (!granted || !model.locator.allowed()) ask.launch(perms) }
    if (!granted) {
        Column(Modifier.fillMaxSize().background(C.bg).windowInsetsPadding(WindowInsets.statusBars).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)) {
            TopBar("Izin kamera", onBack = { model.back() })
            T("UkurPaket memakai kamera untuk mengukur paket. Gambar diproses di HP ini dan tidak dikirim ke mana pun. " +
                "Lokasi (boleh ditolak) dicatat bersama hasil ukur sebagai bukti tempat pickup.", 15.sp, color = C.t2)
            PrimaryButton("Izinkan kamera", "photo_camera", Modifier.fillMaxWidth()) { ask.launch(perms) }
        }
        return
    }
    content()
}

@Composable
fun MeasureScreen(model: AppModel, activity: Activity) {
    CameraPermission(model, activity) { ArMeasure(model, activity) }
}

@Composable
private fun ArMeasure(model: AppModel, activity: Activity) {
    val settings by model.store.settings.collectAsState()
    val engine = remember { model.engineFor(activity, model.caps.depth, if (settings.record) model.store.recordingsDir else null) }
    var glView by remember { mutableStateOf<GLSurfaceView?>(null) }
    var openError by remember { mutableStateOf<String?>(null) }
    val owner = LocalLifecycleOwner.current
    DisposableEffect(owner, glView) {
        val v = glView
        val obs = LifecycleEventObserver { _, e ->
            when (e) {
                Lifecycle.Event.ON_RESUME -> { openError = engine.resume(); v?.onResume() }
                Lifecycle.Event.ON_PAUSE -> { v?.onPause(); engine.pause() }
                else -> Unit
            }
        }
        if (v != null) owner.lifecycle.addObserver(obs)
        onDispose { owner.lifecycle.removeObserver(obs) }
    }
    // the session is paused, not closed: the next parcel of this pickup reuses it (AppModel.releaseEngine closes it)
    DisposableEffect(Unit) { onDispose { glView?.onPause(); engine.pause() } }

    val ui by engine.ui.collectAsState()

    Box(Modifier.fillMaxSize().background(Color.Black)) {
        AndroidView(factory = { ctx ->
            GLSurfaceView(ctx).apply {
                preserveEGLContextOnPause = true
                setEGLContextClientVersion(2)
                setEGLConfigChooser(8, 8, 8, 8, 16, 0)
                setRenderer(engine)
                renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
                glView = this
            }
        }, modifier = Modifier.fillMaxSize())

        ArChrome(ui, engine, model, openError)
    }
}

/**
 * Everything drawn over the camera: overlay, labels, top bar, warnings and the bottom sheet.
 * [demoBox] / [showHub] only set a state for the screenshots.
 */
@Composable
internal fun ArChrome(ui: EngineUi, engine: MeasureEngine, model: AppModel, openError: String?,
                      demoBox: FloatArray? = null, showHub: Boolean = false) {
    var boxMode by remember { mutableStateOf(demoBox != null) }
    var drag by remember { mutableStateOf(demoBox) }
    var hub by remember { mutableStateOf(showHub) }
    val canPick = ui.phase == Phase.SELECT && model.samState == SamState.READY || demoBox != null
    LaunchedEffect(ui.phase) { if (ui.phase != Phase.SELECT && demoBox == null) { boxMode = false; drag = null } }
    val scope = rememberCoroutineScope()
    Box(Modifier.fillMaxSize()) {
        val gestures = if (boxMode && canPick) Modifier.pointerInput(boxMode) {
            detectDragGestures(
                onDragStart = { drag = floatArrayOf(it.x, it.y, it.x, it.y) },
                onDrag = { ch, _ -> drag = drag?.let { d -> floatArrayOf(d[0], d[1], ch.position.x, ch.position.y) } },
                onDragEnd = {
                    drag?.let { d -> if (abs(d[2] - d[0]) > 30 && abs(d[3] - d[1]) > 30) engine.box(d[0], d[1], d[2], d[3]) }
                    drag = null; boxMode = false
                },
            )
        } else Modifier.pointerInput(Unit) { detectTapGestures { engine.tap(it.x, it.y) } }
        Overlay(ui, drag, Modifier.fillMaxSize().then(gestures))
        if (ui.phase == Phase.SELECT) OverlayLabels(ui)
        if (ui.phase == Phase.RESULT) DimLabels(ui)
        if (ui.phase == Phase.SEARCH) SwipeHint()
        if (ui.phase == Phase.SCAN) ArcArrow()

        Box(Modifier.fillMaxWidth().height(120.dp).background(
            androidx.compose.ui.graphics.Brush.verticalGradient(listOf(Color(0x8C020617), Color.Transparent))))
        Column(Modifier.fillMaxWidth().windowInsetsPadding(WindowInsets.statusBars).padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                GlassButton("arrow_back") { model.back() }
                StepPill(ui.phase, Modifier.weight(1f))
                if (ui.torchSupported) GlassButton(if (ui.torch) "flashlight_on" else "flashlight_off", on = ui.torch) { engine.torch(!ui.torch) }
            }
            val warn = ui.hint in setOf(Hint.SLOW, Hint.DARK, Hint.TEXTURE, Hint.LOST, Hint.BACK, Hint.STACKED, Hint.FAILED, Hint.PICK_FAILED)
            val err = openError ?: ui.error
            if (err != null) Banner(err, C.red, Color.White)
            else if (warn) Banner(ui.hint.text, C.warn, Color(0xFF1F1300))
            else if (boxMode && drag == null) Banner("Geser jari untuk menandai area paket", C.brand, Color.White, "highlight_alt")
        }
        Sheet(Modifier.align(Alignment.BottomCenter), ui, engine, model, boxMode, canPick, { boxMode = !boxMode }, { hub = true })
    }
    if (hub) HubDialog(onDismiss = { hub = false }) { reason ->
        hub = false
        val f = File(model.store.photosDir, "hub_${System.currentTimeMillis()}.jpg")
        var sent = false
        engine.photo(f) { saved -> if (!sent) { sent = true; model.markHub(reason, saved?.path) } }
        // no camera frame within 3 s (tracking stopped, camera busy): save without the photo rather than hang
        scope.launch { delay(3000); if (!sent) { sent = true; model.markHub(reason, null) } }
    }
}

// ------------------------------------------------------------------ overlay
@Composable
private fun Overlay(ui: EngineUi, drag: FloatArray?, modifier: Modifier) {
    val ov = ui.overlay
    val scan = ui.phase == Phase.SCAN
    Canvas(modifier) {
        dots(ov.floorDots, Color.White.copy(alpha = 0.85f), 2.6.dp.toPx())
        dots(ov.depthDots, C.yellow, 2.2.dp.toPx())
        val dash = PathEffect.dashPathEffect(floatArrayOf(10.dp.toPx(), 7.dp.toPx()))
        for (o in ov.others) poly(o)?.let { drawPath(it, Color.White.copy(alpha = 0.9f), style = Stroke(2.dp.toPx(), pathEffect = dash)) }
        ov.outline?.let { pts ->
            val path = poly(pts) ?: return@let
            val col = if (scan) C.live else C.brand
            drawPath(path, col.copy(alpha = 0.16f))
            drawPath(path, col, style = Stroke(3.dp.toPx()))
        }
        ov.box?.let { b ->
            val col = if (ui.result?.status == Status.CHECK) C.warn else C.live
            fun p(i: Int) = Offset(b[2 * i], b[2 * i + 1])
            fun ok(i: Int) = !b[2 * i].isNaN()
            val dashed = PathEffect.dashPathEffect(floatArrayOf(14f, 10f))
            for (i in 0 until 4) {
                val j = (i + 1) % 4
                if (ok(i) && ok(j)) drawLine(col.copy(alpha = 0.9f), p(i), p(j), 2.5.dp.toPx(), pathEffect = dashed)
                if (ok(i) && ok(i + 4)) drawLine(col, p(i), p(i + 4), 2.5.dp.toPx())
            }
            val top = Path()
            var first = true
            for (i in 4 until 8) if (ok(i)) { if (first) top.moveTo(b[2 * i], b[2 * i + 1]) else top.lineTo(b[2 * i], b[2 * i + 1]); first = false }
            top.close()
            drawPath(top, col.copy(alpha = 0.10f))
            drawPath(top, col, style = Stroke(3.5.dp.toPx(), cap = StrokeCap.Round))
            for (i in 4 until 8) if (ok(i)) { drawCircle(Color.White, 5.dp.toPx(), p(i)); drawCircle(col, 5.dp.toPx(), p(i), style = Stroke(2.dp.toPx())) }
        }
        var k = 0
        while (k + 1 < ov.marks.size) {
            if (!ov.marks[k].isNaN()) {
                val c = Offset(ov.marks[k], ov.marks[k + 1])
                drawCircle(C.green, 15.dp.toPx(), c); drawCircle(Color.White, 15.dp.toPx(), c, style = Stroke(2.dp.toPx()))
                val s = 6.dp.toPx()
                drawLine(Color.White, Offset(c.x - s, c.y), Offset(c.x - s / 3, c.y + s * 0.65f), 3.dp.toPx(), StrokeCap.Round)
                drawLine(Color.White, Offset(c.x - s / 3, c.y + s * 0.65f), Offset(c.x + s, c.y - s * 0.6f), 3.dp.toPx(), StrokeCap.Round)
            }
            k += 2
        }
        ui.reticle?.let { (x, y) ->
            val c = Offset(x, y)
            drawCircle(Color.White, 20.dp.toPx(), c, style = Stroke(2.5.dp.toPx()))
            drawCircle(Color.White, 3.5.dp.toPx(), c)
            val a = 26.dp.toPx(); val b = 32.dp.toPx()
            drawLine(Color.White, Offset(x, y - b), Offset(x, y - a), 2.5.dp.toPx())
            drawLine(Color.White, Offset(x, y + a), Offset(x, y + b), 2.5.dp.toPx())
            drawLine(Color.White, Offset(x - b, y), Offset(x - a, y), 2.5.dp.toPx())
            drawLine(Color.White, Offset(x + a, y), Offset(x + b, y), 2.5.dp.toPx())
        }
        drag?.let { d ->
            val tl = Offset(min(d[0], d[2]), min(d[1], d[3]))
            val sz = Size(abs(d[2] - d[0]), abs(d[3] - d[1]))
            drawRect(Color.White.copy(alpha = 0.12f), tl, sz)
            drawRect(Color.White, tl, sz, style = Stroke(2.5.dp.toPx(), pathEffect = dash))
            for (c in listOf(tl, Offset(tl.x + sz.width, tl.y), Offset(tl.x, tl.y + sz.height), Offset(tl.x + sz.width, tl.y + sz.height)))
                drawCircle(Color.White, 6.dp.toPx(), c)
        }
    }
}

private fun DrawScope.dots(a: FloatArray, color: Color, r: Float) {
    var i = 0
    while (i + 1 < a.size) {
        if (!a[i].isNaN()) drawCircle(color, r, Offset(a[i], a[i + 1]))
        i += 2
    }
}

private fun poly(a: FloatArray): Path? {
    val path = Path()
    var n = 0
    var i = 0
    while (i + 1 < a.size) {
        if (!a[i].isNaN()) { if (n == 0) path.moveTo(a[i], a[i + 1]) else path.lineTo(a[i], a[i + 1]); n++ }
        i += 2
    }
    if (n < 3) return null
    path.close()
    return path
}

/** Glass label at a surface-pixel position, centred above it. */
@Composable
private fun Tag(x: Float, y: Float, text: String, icon: String, bg: Color) {
    val density = LocalDensity.current
    val dx = with(density) { 58.dp.toPx() }; val dy = with(density) { 34.dp.toPx() }
    Row(Modifier.offset { IntOffset((x - dx).roundToInt(), (y - dy).roundToInt()) }.clip(RoundedCornerShape(14.dp)).background(bg)
        .padding(horizontal = 9.dp, vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
        Sym(icon, 15.dp, Color.White)
        T(" $text", 12.5.sp, FontWeight.SemiBold, Color.White, maxLines = 1)
    }
}

/** "Paket terpilih" over the picked parcel, "Paket lain" over the others, the label of each parcel already measured. */
@Composable
private fun OverlayLabels(ui: EngineUi) {
    val ov = ui.overlay
    // "Paket lain" sits inside the bottom edge of each other parcel (their tops are often cut off by the screen edge)
    for (o in ov.others) {
        val xs = o.filterIndexed { j, v -> j % 2 == 0 && !v.isNaN() }; val ys = o.filterIndexed { j, v -> j % 2 == 1 && !v.isNaN() }
        if (xs.isNotEmpty()) Tag(xs.average().toFloat(), ys.max() - 6f, "Paket lain", "inventory_2", C.glass)
    }
    // "Paket terpilih" at the picked outline's top-left corner, clear of the labels of its neighbours
    val density = LocalDensity.current
    if (ui.picked) ov.outline?.let { o ->
        val xs = o.filterIndexed { j, v -> j % 2 == 0 && !v.isNaN() }; val ys = o.filterIndexed { j, v -> j % 2 == 1 && !v.isNaN() }
        if (xs.isNotEmpty()) Tag(xs.min() + with(density) { 58.dp.toPx() }, ys.min(), "Paket dipilih", "check_circle", C.brand)
    }
    var k = 0
    while (k + 1 < ov.marks.size) {
        if (!ov.marks[k].isNaN()) Tag(ov.marks[k], ov.marks[k + 1] - 14f, "Selesai · " + ov.markLabels.getOrElse(k / 2) { "" }, "task_alt", C.green)
        k += 2
    }
}

/** Length, width and height written on the 3D box. */
@Composable
private fun DimLabels(ui: EngineUi) {
    val b = ui.overlay.box ?: return
    val r: BoxResult = ui.live ?: return
    val res = ui.result ?: return
    val e01 = (r.floorCorners[0] - r.floorCorners[1]).norm()
    val e12 = (r.floorCorners[1] - r.floorCorners[2]).norm()
    val first = if (e01 >= e12) res.lengthCm else res.widthCm
    val second = if (e01 >= e12) res.widthCm else res.lengthCm
    DimTags(b, first, second, res.heightCm, res.status == Status.CHECK)
}

/** Three size labels on a projected box (corners floor 0-3, top 4-7). */
@Composable
internal fun DimTags(b: FloatArray, first: Double, second: Double, height: Double, check: Boolean) {
    val density = LocalDensity.current
    fun mid(i: Int, j: Int) = Offset((b[2 * i] + b[2 * j]) / 2, (b[2 * i + 1] + b[2 * j + 1]) / 2)
    listOf(mid(4, 5) to first, mid(5, 6) to second, mid(2, 6) to height).forEach { (o, v) ->
        if (o.x.isNaN()) return@forEach
        val dx = with(density) { 32.dp.toPx() }; val dy = with(density) { 14.dp.toPx() }
        Box(Modifier.offset { IntOffset((o.x - dx).roundToInt(), (o.y - dy).roundToInt()) }
            .clip(RoundedCornerShape(8.dp)).background(Color.White).padding(horizontal = 8.dp, vertical = 4.dp)) {
            T("${v.cm()} cm", 14.sp, FontWeight.Bold, if (check) C.amber else Color(0xFF15803D))
        }
    }
}

@Composable
private fun BoxScope.SwipeHint() {
    val x = if (LocalStill.current) 0f else {
        val t = rememberInfiniteTransition(label = "swipe")
        t.animateFloat(-14f, 14f, infiniteRepeatable(tween(800), RepeatMode.Reverse), label = "x").value
    }
    Box(Modifier.align(Alignment.Center).offset(y = (-60).dp).size(84.dp).clip(CircleShape).background(C.glass),
        contentAlignment = Alignment.Center) {
        Sym("swipe", 44.dp, Color.White, modifier = Modifier.offset(x = x.dp))
    }
}

/** Dashed arc with an arrowhead around the parcel's lower right: "move round toward the corner". */
@Composable
private fun BoxScope.ArcArrow() {
    val phase = if (LocalStill.current) 0f else {
        val t = rememberInfiniteTransition(label = "arc")
        t.animateFloat(0f, 1f, infiniteRepeatable(tween(1400, easing = LinearEasing)), label = "p").value
    }
    Canvas(Modifier.align(Alignment.BottomEnd).padding(end = 18.dp, bottom = 250.dp).size(170.dp, 130.dp)) {
        val w = size.width; val h = size.height
        val path = Path().apply { moveTo(w * 0.05f, h * 0.92f); quadraticBezierTo(w * 0.95f, h * 0.98f, w * 0.88f, h * 0.10f) }
        val dl = 12.dp.toPx(); val gap = 8.dp.toPx()
        drawPath(path, Color.White, style = Stroke(3.dp.toPx(), cap = StrokeCap.Round,
            pathEffect = PathEffect.dashPathEffect(floatArrayOf(dl, gap), -phase * (dl + gap) * 3)))
        val tip = Offset(w * 0.88f, h * 0.10f)
        val a = 12.dp.toPx()
        drawLine(Color.White, tip, Offset(tip.x - a * 0.75f, tip.y + a * 0.75f), 3.dp.toPx(), StrokeCap.Round)
        drawLine(Color.White, tip, Offset(tip.x + a * 0.55f, tip.y + a * 0.9f), 3.dp.toPx(), StrokeCap.Round)
    }
}

// ------------------------------------------------------------------ chrome
@Composable
internal fun GlassButton(icon: String, on: Boolean = false, onClick: () -> Unit) {
    Box(Modifier.size(44.dp).clip(CircleShape).background(if (on) C.yellow else C.glass).clickable(onClick = onClick),
        contentAlignment = Alignment.Center) {
        Sym(icon, 22.dp, if (on) C.onYellow else Color.White, filled = on)
    }
}

@Composable
private fun StepPill(phase: Phase, modifier: Modifier) {
    val (n, label) = when (phase) {
        Phase.SEARCH -> 1 to "Scan Lantai"
        Phase.SELECT -> 2 to "Pilih Paket"
        Phase.SCAN -> 3 to "Scan Paket"
        Phase.RESULT -> 0 to "Hasil Ukur"
    }
    StepPillOf(n, label, modifier)
}

@Composable
internal fun StepPillOf(n: Int, label: String, modifier: Modifier) {
    Row(modifier.height(44.dp).clip(RoundedCornerShape(22.dp)).background(C.glass).padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically) {
        T(if (n > 0) "$n/3 · $label" else label, 14.sp, FontWeight.SemiBold, Color.White, modifier = Modifier.weight(1f))
        if (n > 0) Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            for (k in 1..3) Box(Modifier.size(18.dp, 5.dp).clip(RoundedCornerShape(3.dp))
                .background(if (k < n) C.live else if (k == n) Color.White else Color.White.copy(alpha = 0.3f)))
        }
    }
}

@Composable
internal fun Banner(text: String, bg: Color, fg: Color, icon: String = "warning") {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(bg).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Sym(icon, 24.dp, fg, filled = true)
        T(text, 14.sp, FontWeight.SemiBold, fg, modifier = Modifier.padding(start = 10.dp))
    }
}

/** Reasons a courier hands a parcel to the hub instead of measuring it. */
val HUB_REASONS = listOf("Bentuk tidak beraturan", "Paket terlalu besar", "Tempat gelap / sempit", "Hasil ukur berubah-ubah")

@Composable
internal fun HubDialog(onDismiss: () -> Unit, onPick: (String) -> Unit) {
    AlertDialog(onDismissRequest = onDismiss,
        title = { T("Ukur di Hub?", 18.sp, FontWeight.SemiBold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                T("Paket tetap diambil. Foto dan lokasi disimpan; ukurannya diukur di hub. Pilih alasannya:", 13.5.sp, color = C.t2)
                HUB_REASONS.forEach { r ->
                    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(C.bg).clickable { onPick(r) }.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically) {
                        Sym("warehouse", 20.dp, C.amber)
                        T(r, 14.sp, FontWeight.Medium, modifier = Modifier.padding(start = 10.dp))
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = { TextButton(onClick = onDismiss) { T("Batal", color = C.t2) } })
}

/** The quiet way out after repeated failures. */
@Composable
internal fun HubLink(onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).clickable(onClick = onClick).padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
        Sym("warehouse", 18.dp, C.amber)
        T(" Gagal ukur? Ukur di Hub", 13.5.sp, FontWeight.SemiBold, C.amber)
    }
}

@Composable
private fun Sheet(modifier: Modifier, ui: EngineUi, engine: MeasureEngine, model: AppModel, boxMode: Boolean, canPick: Boolean,
                  toggleBox: () -> Unit, openHub: () -> Unit) {
    val sheetSettings by model.store.settings.collectAsState()
    Column(modifier.fillMaxWidth().clip(RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp)).background(Color.White)
        .windowInsetsPadding(WindowInsets.navigationBars).padding(start = 18.dp, end = 18.dp, top = 10.dp, bottom = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(Modifier.align(Alignment.CenterHorizontally).size(40.dp, 4.dp).clip(RoundedCornerShape(2.dp)).background(C.line))
        when (ui.phase) {
            Phase.SEARCH -> {
                if (ui.planeFound) Chip("Lantai terdeteksi", Tone.OK, "check_circle") else Chip("Mencari lantai…", Tone.WARN, "sync")
                T("Gerakkan HP pelan ke kiri dan kanan", 18.sp, FontWeight.Bold)
                T("Titik putih muncul di lantai berarti lantai sudah dikenali. Paket harus berdiri di lantai itu.", 13.5.sp, color = C.t2)
            }
            Phase.SELECT -> {
                val lv = ui.live
                if (ui.selecting) Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.5.dp, color = C.brand)
                    T("  Memilih paket…", 18.sp, FontWeight.Bold)
                } else T(if (ui.picked) "Paket dipilih" else if (ui.targetFound) "Paket terdeteksi" else "Arahkan bidikan ke paket", 18.sp, FontWeight.Bold)
                T(when {
                    lv != null -> "Perkiraan ${(lv.lengthM * 100.0).cm()} × ${(lv.widthM * 100.0).cm()} × ${(lv.heightM * 100.0).cm()} cm. " +
                        if (ui.picked) "Bukan paket ini? Ketuk paket yang benar." else "Tekan Mulai Scan untuk mengukur teliti."
                    else -> "Garis magenta = paket yang akan diukur. Bukan paket ini? Ketuk paket yang benar."
                }, 13.5.sp, color = C.t2)
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    if (model.samState == SamState.READY || canPick)
                        SecondaryButton(if (boxMode) "Batal" else "Pilih Area", if (boxMode) "close" else "crop", Modifier.weight(1f)) { toggleBox() }
                    PrimaryButton("Mulai Scan", "view_in_ar", Modifier.weight(1f), enabled = (ui.targetFound || model.samState == SamState.READY) && !ui.selecting) { engine.lock() }
                }
                if (ui.attempts >= 2) HubLink(openHub)
            }
            Phase.SCAN -> {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(58.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(progress = { ui.progress }, modifier = Modifier.size(58.dp), color = C.brand,
                            trackColor = C.line, strokeWidth = 6.dp)
                        T("${(ui.progress * 100).roundToInt()}%", 13.sp, FontWeight.Bold)
                    }
                    T(if (ui.hint == Hint.SLOW || ui.hint == Hint.BACK) ui.hint.text else Hint.SWEEP.text, 17.sp, FontWeight.Bold,
                        modifier = Modifier.padding(start = 14.dp))
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Check("Lantai"); Check("Paket dipilih")
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Sym("deployed_code", 16.dp, C.brand, filled = true)
                        T(" Data 3D ${(ui.progress * 100).roundToInt()}%", 12.5.sp, color = C.brand)
                    }
                }
                SecondaryButton("Scan Ulang", "refresh", Modifier.fillMaxWidth()) { engine.rescan() }
            }
            Phase.RESULT -> {
                val r = ui.result ?: return@Column
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (r.status == Status.OK) Chip("Akurat · Skor ${r.confidence}%", Tone.OK, "check_circle")
                    else Chip("Perlu Dicek · Skor ${r.confidence}%", Tone.WARN, "warning")
                    Spacer(Modifier.weight(1f))
                    T("…" + (model.draft?.resi?.takeLast(4) ?: ""), 12.sp, color = C.t3)
                }
                T("${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm", 30.sp, FontWeight.Bold)
                if (r.status == Status.CHECK) T("Pastikan garis kotak 3D pas dengan paket, atau ulangi dari sudut lain.", 13.sp, color = C.t2)
                ResultStats(r.lengthCm, r.widthCm, r.heightCm, sheetSettings.divisor, r.seconds)
                SaveRow(r.status == Status.CHECK, r, { engine.rescan() }) { model.onMeasured(r) }
                if (ui.attempts >= 2 && r.status == Status.CHECK) HubLink(openHub)
            }
        }
    }
}

@Composable
internal fun ResultStats(l: Double, w: Double, h: Double, div: Int, seconds: Double) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Stat("Volume", "${(l * w * h / 1000).id()} L", Modifier.weight(1f))
        Stat("Berat volumetrik", "${(l * w * h / div).id(2)} kg", Modifier.weight(1.3f))
        Stat("Durasi", "${seconds.id(0)} dtk", Modifier.weight(1f))
    }
}

/** Repeat / Save; Save waits 2 s on a doubtful result so it is not saved by reflex. */
@Composable
internal fun SaveRow(check: Boolean, key: Any, onRepeat: () -> Unit, onSave: () -> Unit) {
    var wait by remember(key) { mutableIntStateOf(if (check) 2 else 0) }
    LaunchedEffect(key) { while (wait > 0) { delay(1000); wait-- } }
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        SecondaryButton("Ulangi", "refresh", Modifier.width(130.dp)) { onRepeat() }
        PrimaryButton(if (wait > 0) "Simpan ($wait)" else "Simpan", "check", Modifier.weight(1f), color = C.green, enabled = wait == 0) { onSave() }
    }
}

@Composable
private fun Check(label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Sym("check_circle", 16.dp, C.green, filled = true)
        T(" $label", 12.5.sp, color = C.green)
    }
}

@Composable
private fun Stat(label: String, value: String, modifier: Modifier) {
    Column(modifier.clip(RoundedCornerShape(12.dp)).background(C.bg).padding(horizontal = 10.dp, vertical = 8.dp)) {
        T(label, 11.5.sp, color = C.t2, maxLines = 1)
        T(value, 16.sp, FontWeight.Bold, maxLines = 1)
    }
}
