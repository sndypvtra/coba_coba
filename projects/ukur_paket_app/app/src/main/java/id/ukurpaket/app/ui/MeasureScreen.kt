package id.ukurpaket.app.ui

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.opengl.GLSurfaceView
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
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
import kotlin.math.roundToInt

@Composable
fun MeasureScreen(model: AppModel, activity: Activity) {
    var granted by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(activity, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
    }
    val ask = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted = it }
    LaunchedEffect(Unit) { if (!granted) ask.launch(Manifest.permission.CAMERA) }
    if (!granted) {
        Column(Modifier.fillMaxSize().background(C.bg).windowInsetsPadding(WindowInsets.statusBars).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)) {
            TopBar("Izin kamera", onBack = { model.back() })
            T("UkurPaket memakai kamera untuk mengukur paket. Gambar diproses di HP ini dan tidak dikirim ke mana pun.", 15.sp, color = C.t2)
            PrimaryButton("Izinkan kamera", "photo_camera", Modifier.fillMaxWidth()) { ask.launch(Manifest.permission.CAMERA) }
        }
        return
    }
    ArMeasure(model, activity)
}

@Composable
private fun ArMeasure(model: AppModel, activity: Activity) {
    val settings by model.store.settings.collectAsState()
    val engine = remember {
        MeasureEngine(activity, useDepth = model.caps.depth, photosDir = model.store.photosDir,
            recordDir = if (settings.record) model.store.recordingsDir else null)
    }
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
    DisposableEffect(Unit) { onDispose { glView?.onPause(); engine.pause(); engine.close() } }

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

/** Everything drawn over the camera: overlay, labels, top bar, warnings and the bottom sheet. */
@Composable
internal fun ArChrome(ui: EngineUi, engine: MeasureEngine, model: AppModel, openError: String?) {
    Box(Modifier.fillMaxSize()) {
        Overlay(ui, Modifier.fillMaxSize().pointerInput(Unit) { detectTapGestures { engine.tap(it.x, it.y) } })
        if (ui.phase == Phase.RESULT) DimLabels(ui)
        if (ui.phase == Phase.SEARCH) SwipeHint()

        Box(Modifier.fillMaxWidth().height(120.dp).background(
            androidx.compose.ui.graphics.Brush.verticalGradient(listOf(Color(0x8C020617), Color.Transparent))))
        Column(Modifier.fillMaxWidth().windowInsetsPadding(WindowInsets.statusBars).padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                GlassButton("arrow_back") { model.back() }
                StepPill(ui.phase)
            }
            val warn = ui.hint in setOf(Hint.SLOW, Hint.DARK, Hint.TEXTURE, Hint.LOST, Hint.BACK, Hint.STACKED, Hint.FAILED)
            val err = openError ?: ui.error
            if (err != null) Banner(err, C.red, Color.White)
            else if (warn) Banner(ui.hint.text, Color(0xFFF59E0B), Color(0xFF1F1300))
        }
        Sheet(Modifier.align(Alignment.BottomCenter), ui, engine, model)
    }
}

// ------------------------------------------------------------------ overlay
@Composable
private fun Overlay(ui: EngineUi, modifier: Modifier) {
    val ov = ui.overlay
    val scan = ui.phase == Phase.SCAN
    Canvas(modifier) {
        dots(ov.floorDots, Color.White.copy(alpha = 0.85f), 2.6.dp.toPx())
        dots(ov.depthDots, C.cyan, 2.2.dp.toPx())
        ov.outline?.let { pts ->
            val path = poly(pts) ?: return@let
            val col = if (scan) C.live else Color(0xFF3B82F6)
            drawPath(path, col.copy(alpha = 0.16f))
            drawPath(path, col, style = Stroke(3.dp.toPx()))
        }
        ov.box?.let { b ->
            val col = if (ui.result?.status == Status.CHECK) Color(0xFFF59E0B) else C.live
            fun p(i: Int) = Offset(b[2 * i], b[2 * i + 1])
            fun ok(i: Int) = !b[2 * i].isNaN()
            val dash = PathEffect.dashPathEffect(floatArrayOf(14f, 10f))
            for (i in 0 until 4) {
                val j = (i + 1) % 4
                if (ok(i) && ok(j)) drawLine(col.copy(alpha = 0.9f), p(i), p(j), 2.5.dp.toPx(), pathEffect = dash)
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
    val density = LocalDensity.current
    fun mid(i: Int, j: Int) = Offset((b[2 * i] + b[2 * j]) / 2, (b[2 * i + 1] + b[2 * j + 1]) / 2)
    listOf(mid(4, 5) to first, mid(5, 6) to second, mid(2, 6) to res.heightCm).forEach { (o, v) ->
        if (o.x.isNaN()) return@forEach
        val dx = with(density) { 32.dp.toPx() }; val dy = with(density) { 14.dp.toPx() }
        Box(Modifier.offset { IntOffset((o.x - dx).roundToInt(), (o.y - dy).roundToInt()) }
            .clip(RoundedCornerShape(8.dp)).background(Color.White).padding(horizontal = 8.dp, vertical = 4.dp)) {
            T("${v.cm()} cm", 14.sp, FontWeight.Bold, if (res.status == Status.CHECK) Color(0xFFB45309) else Color(0xFF15803D))
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

// ------------------------------------------------------------------ chrome
@Composable
private fun GlassButton(icon: String, onClick: () -> Unit) {
    Box(Modifier.size(44.dp).clip(CircleShape).background(C.glass).clickable(onClick = onClick), contentAlignment = Alignment.Center) {
        Sym(icon, 22.dp, Color.White)
    }
}

@Composable
private fun StepPill(phase: Phase) {
    val (n, label) = when (phase) {
        Phase.SEARCH -> 1 to "Cari alas"
        Phase.SELECT -> 2 to "Pilih paket"
        Phase.SCAN -> 3 to "Pindai"
        Phase.RESULT -> 0 to "Hasil ukur"
    }
    Row(Modifier.height(44.dp).fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(C.glass).padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically) {
        T(if (n > 0) "$n/3 · $label" else label, 14.sp, FontWeight.SemiBold, Color.White, modifier = Modifier.weight(1f))
        if (n > 0) Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            for (k in 1..3) Box(Modifier.size(18.dp, 5.dp).clip(RoundedCornerShape(3.dp))
                .background(if (k < n) C.live else if (k == n) Color.White else Color.White.copy(alpha = 0.3f)))
        }
    }
}

@Composable
private fun Banner(text: String, bg: Color, fg: Color) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(bg).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Sym("warning", 24.dp, fg, filled = true)
        T(text, 14.sp, FontWeight.SemiBold, fg, modifier = Modifier.padding(start = 10.dp))
    }
}

@Composable
private fun Sheet(modifier: Modifier, ui: EngineUi, engine: MeasureEngine, model: AppModel) {
    val sheetSettings by model.store.settings.collectAsState()
    Column(modifier.fillMaxWidth().clip(RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp)).background(Color.White)
        .windowInsetsPadding(WindowInsets.navigationBars).padding(start = 18.dp, end = 18.dp, top = 10.dp, bottom = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(Modifier.align(Alignment.CenterHorizontally).size(40.dp, 4.dp).clip(RoundedCornerShape(2.dp)).background(C.line))
        when (ui.phase) {
            Phase.SEARCH -> {
                if (ui.planeFound) Chip("Alas terdeteksi", Tone.OK, "check_circle") else Chip("Mencari alas…", Tone.WARN, "sync")
                T("Gerakkan HP pelan ke kiri dan kanan", 18.sp, FontWeight.Bold)
                T("Titik putih muncul di lantai berarti alas sudah dikenali. Paket harus berdiri di alas itu.", 13.5.sp, color = C.t2)
            }
            Phase.SELECT -> {
                val lv = ui.live
                T(if (ui.targetFound) "Paket terdeteksi" else "Arahkan titik ke paket", 18.sp, FontWeight.Bold)
                T(if (lv != null) "Perkiraan ${(lv.lengthM * 100.0).cm()} × ${(lv.widthM * 100.0).cm()} × ${(lv.heightM * 100.0).cm()} cm. Kunci untuk mengukur teliti."
                  else "Garis biru = paket yang akan diukur. Ketuk paket lain di layar untuk memilihnya.", 13.5.sp, color = C.t2)
                PrimaryButton("Kunci paket", "lock", Modifier.fillMaxWidth(), enabled = ui.targetFound) { engine.lock() }
            }
            Phase.SCAN -> {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(58.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(progress = { ui.progress }, modifier = Modifier.size(58.dp), color = C.blue,
                            trackColor = C.line, strokeWidth = 6.dp)
                        T("${(ui.progress * 100).roundToInt()}%", 13.sp, FontWeight.Bold)
                    }
                    T(if (ui.hint == Hint.SLOW || ui.hint == Hint.BACK) ui.hint.text else Hint.SWEEP.text, 17.sp, FontWeight.Bold,
                        modifier = Modifier.padding(start = 14.dp))
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Check("Alas"); Check("Paket terkunci")
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Sym("deployed_code", 16.dp, C.blue, filled = true)
                        T(" ${if (model.caps.depth) "Kedalaman" else "Titik fitur"} ${(ui.progress * 100).roundToInt()}%", 12.5.sp, color = C.blue)
                    }
                }
                SecondaryButton("Ulangi pindai", "refresh", Modifier.fillMaxWidth()) { engine.rescan() }
            }
            Phase.RESULT -> {
                val r = ui.result ?: return@Column
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (r.status == Status.OK) Chip("Akurat · keyakinan ${r.confidence}%", Tone.OK, "check_circle")
                    else Chip("Cek ulang · keyakinan ${r.confidence}%", Tone.WARN, "warning")
                    Spacer(Modifier.weight(1f))
                    T("…" + (model.draft?.resi?.takeLast(4) ?: ""), 12.sp, color = C.t3)
                }
                T("${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm", 30.sp, FontWeight.Bold)
                if (r.status == Status.CHECK) T("Pastikan kotak pas membungkus paket, atau ulangi dari sudut lain.", 13.sp, color = C.t2)
                val div = sheetSettings.divisor
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Stat("Volume", "${(r.lengthCm * r.widthCm * r.heightCm / 1000).id()} L", Modifier.weight(1f))
                    Stat("Berat volumetrik", "${(r.lengthCm * r.widthCm * r.heightCm / div).id(2)} kg", Modifier.weight(1.3f))
                    Stat("Waktu ukur", "${r.seconds.id(0)} dtk", Modifier.weight(1f))
                }
                var wait by remember(r) { mutableIntStateOf(if (r.status == Status.CHECK) 2 else 0) }
                LaunchedEffect(r) { while (wait > 0) { delay(1000); wait-- } }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    SecondaryButton("Ulangi", "refresh", Modifier.width(130.dp)) { engine.rescan() }
                    PrimaryButton(if (wait > 0) "Simpan ($wait)" else "Simpan", "check", Modifier.weight(1f), color = C.green, enabled = wait == 0) {
                        model.onMeasured(r)
                    }
                }
            }
        }
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
