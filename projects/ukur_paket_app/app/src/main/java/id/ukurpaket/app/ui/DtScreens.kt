package id.ukurpaket.app.ui

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.SurfaceTexture
import android.os.Handler
import android.os.Looper
import android.view.TextureView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import id.ukurpaket.app.dt.Check
import id.ukurpaket.app.dt.Diagnostics
import id.ukurpaket.app.dt.Level
import id.ukurpaket.app.dt.ObjectPick
import id.ukurpaket.app.dt.Pick
import id.ukurpaket.app.dt.SweepAnalysis
import id.ukurpaket.app.dt.SweepQuality
import id.ukurpaket.app.dt.SweepRecorder
import id.ukurpaket.app.measure.Embedding
import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.dt.SweepRun
import id.ukurpaket.app.data.cm
import id.ukurpaket.app.data.id
import id.ukurpaket.app.vio.LiveSegmenter
import java.util.concurrent.atomic.AtomicInteger
import id.ukurpaket.app.vio.SweepResult
import androidx.compose.runtime.collectAsState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

private fun Double.f1() = "%.1f".format(this).replace('.', ',')

/** A smaller outlined button that keeps its label on narrow screens and large font settings. */
@Composable
private fun SmallButton(text: String, icon: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    androidx.compose.material3.OutlinedButton(onClick = onClick, modifier = modifier.height(46.dp), shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.5.dp, C.line), contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 6.dp),
        colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(containerColor = Color.White)) {
        Sym(icon, 18.dp, C.ink); Spacer(Modifier.width(4.dp))
        T(text, 13.sp, FontWeight.SemiBold, C.ink, maxLines = 1)
    }
}

@Composable
private fun LevelIcon(l: Level) = when (l) {
    Level.OK -> Sym("check_circle", 20.dp, C.green, filled = true)
    Level.WARN -> Sym("warning", 20.dp, C.amber, filled = true)
    Level.FAIL -> Sym("error", 20.dp, C.red, filled = true)
    Level.INFO -> Sym("info", 20.dp, C.t3, filled = true)
}

@Composable
private fun CheckLine(c: Check) {
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.Top) {
        Box(Modifier.padding(top = 1.dp)) { LevelIcon(c.level) }
        Column(Modifier.weight(1f).padding(start = 10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                T(c.label, 14.sp, color = C.t2, modifier = Modifier.weight(1f))
                T(c.value, 14.sp, FontWeight.SemiBold)
            }
            if (c.note.isNotEmpty()) T(c.note, 12.sp, color = C.t3)
        }
    }
}

@Composable
private fun VerdictCard(level: Level, title: String, text: String, onClick: (() -> Unit)? = null, open: Boolean? = null) {
    val (bg, fg, icon) = when (level) {
        Level.OK -> Triple(C.greenL, C.green, "check_circle")
        Level.WARN -> Triple(C.amberL, C.amber, "warning")
        Level.FAIL -> Triple(C.redL, C.red, "error")
        Level.INFO -> Triple(Color(0xFFEEF1F5), C.t2, "info")
    }
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(bg).let { if (onClick != null) it.clickable(onClick = onClick) else it }
        .padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
        Sym(icon, 28.dp, fg, filled = true)
        Column(Modifier.weight(1f).padding(start = 12.dp)) {
            T(title, 15.sp, FontWeight.SemiBold, fg)
            T(text, 13.sp, color = C.ink)
        }
        if (open != null) Sym(if (open) "expand_more" else "chevron_right", 24.dp, fg)
    }
}

@Composable
private fun Kv(k: String, v: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
        T(k, 13.sp, color = C.t2, modifier = Modifier.width(132.dp))
        T(v, 13.sp, FontWeight.Medium, modifier = Modifier.weight(1f))
    }
}

// ------------------------------------------------------------------ diagnostics
/** What this phone offers for our own engine (the stand-in for ARCore on the DT20), checked one by one. */
@Composable
fun DiagScreen(model: AppModel, activity: Activity) {
    LaunchedEffect(Unit) { if (model.diag == null) model.runDiagnosis() }
    val d = model.diag
    val checks = model.diagChecks()
    Column(Modifier.fillMaxSize()) {
        TopBar("Diagnostik HP", d?.device?.let { "${it.manufacturer} ${it.model} · Android ${it.android}" }, onBack = { model.back() })
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            model.diagBusy?.let { b ->
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(C.brandL).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = C.brand)
                    T(b, 13.5.sp, FontWeight.SemiBold, C.brandD, modifier = Modifier.padding(start = 10.dp))
                }
            }
            if (checks.isNotEmpty()) {
                val (lv, txt) = Diagnostics.verdict(checks)
                VerdictCard(lv, "Syarat engine tanpa ARCore", txt)
                Card(padding = 10.dp) { checks.forEach { CheckLine(it) } }
            }
            if (d != null) {
                Card {
                    T("Perangkat", 15.sp, FontWeight.SemiBold)
                    Spacer(Modifier.height(6.dp))
                    Kv("Model", "${d.device.manufacturer} ${d.device.model} (${d.device.device})")
                    Kv("Android", "${d.device.android} (API ${d.device.sdk})")
                    Kv("Chip", d.device.hardware)
                    Kv("CPU · RAM", "${d.device.cores} inti · ${(d.device.ramMb / 1024.0).f1()} GB")
                    Kv("ABI", d.device.abis.joinToString())
                    Kv("Kamera AR (ARCore)", d.arcore)
                    Kv("Scanner Urovo", if (d.urovoScanner) "Ada" else "Tidak terdeteksi")
                }
                Card {
                    T("Sensor gerak", 15.sp, FontWeight.SemiBold)
                    T("Kecepatan maks dari spesifikasi sensor · terukur di HP ini", 12.sp, color = C.t3)
                    Spacer(Modifier.height(6.dp))
                    if (d.sensors.isEmpty()) T("Tidak ada sensor gerak.", 13.sp, color = C.red)
                    d.sensors.forEach { s ->
                        Kv(s.type.replace('_', ' '), "${s.maxHz.toInt()} Hz" + (s.measuredHz?.let { " · terukur ${it.toInt()} Hz" } ?: "") + "\n${s.name}")
                    }
                }
                if (d.gyroProbes.isNotEmpty()) Card {
                    T("Semua gyroscope di HP ini", 15.sp, FontWeight.SemiBold)
                    T("Dicoba satu per satu: diterima Android? · data per detik di kecepatan tercepat / game / 5 ms", 12.sp, color = C.t3)
                    Spacer(Modifier.height(6.dp))
                    d.gyroProbes.forEach { g ->
                        Kv(g.type.replace('_', ' ') + if (g.wakeUp) " · wake-up" else "",
                            "${if (g.registered) "diterima" else "DITOLAK"} · ${g.hzFastest.toInt()} / ${g.hzGame.toInt()} / ${g.hz5ms.toInt()} Hz\n${g.name} (${g.vendor})")
                    }
                }
                Diagnostics.mainCamera(d.cameras)?.let { c ->
                    Card {
                        T("Kamera belakang (id ${c.id})", 15.sp, FontWeight.SemiBold)
                        Spacer(Modifier.height(6.dp))
                        Kv("Level", c.hardwareLevel)
                        Kv("Jam (timestamp)", c.timestampSource)
                        Kv("Fokus", "${c.focusCalibration} · min ${c.minFocusDiopters} dioptri · ${c.afModes.joinToString()}")
                        Kv("Lensa", c.focalLengthsMm.joinToString { "$it mm" } + " · sensor ${c.sensorSizeMm.joinToString(" × ") { "%.2f".format(it) }} mm")
                        Kv("Piksel", c.pixelArray.joinToString(" × "))
                        Kv("Orientasi sensor", "${c.sensorOrientation}°")
                        Kv("Kalibrasi pabrik", c.intrinsics?.joinToString { "%.1f".format(it) } ?: "tidak ada")
                        Kv("Kunci AE · AWB", "${if (c.aeLock) "ya" else "tidak"} · ${if (c.awbLock) "ya" else "tidak"}")
                        Kv("Stabilisasi", "OIS ${if (c.ois) "ada" else "tidak"} · video ${if (c.videoStabilization) "ada" else "tidak"}")
                        Kv("YUV", c.yuvSizes.take(6).joinToString())
                        Kv("FPS", c.fpsRanges.joinToString())
                        Kv("Kemampuan", c.capabilities.joinToString())
                    }
                }
            }
            Spacer(Modifier.height(4.dp))
        }
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SmallButton("Sensor", "refresh", Modifier.weight(1f)) { model.runDiagnosis() }
                SmallButton("Uji SAM", "speed", Modifier.weight(1f)) { model.timeSam() }
                SmallButton("JSON", "share", Modifier.weight(1f)) {
                    if (model.diag == null) model.toast("Tunggu diagnostik selesai")
                    else model.shareFile(activity, "application/json", "Bagikan diagnostik") { model.diagFile()!! }
                }
            }
            PrimaryButton("Buka perekam sapuan", "videocam", Modifier.fillMaxWidth()) { model.go(Screen.DtRecord) }
        }
    }
}

// ------------------------------------------------------------------ recorder
private enum class RecPhase { READY, RECORDING, SAVING }

/** Camera + motion sensors for one sweep around an object; then the review screen. */
@Composable
fun DtRecordScreen(model: AppModel, activity: Activity) {
    CameraPermission(model, activity) { DtRecorder(model) }
}

@Composable
private fun DtRecorder(model: AppModel) {
    val ctx = LocalContext.current
    var status by remember { mutableStateOf<SweepRecorder.LiveStatus?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var phase by remember { mutableStateOf(RecPhase.READY) }
    val keep = remember { booleanArrayOf(false) }
    val main = remember { Handler(Looper.getMainLooper()) }
    val dir = remember { SweepRecorder.newDir(model.store.dtDir) }
    val rec = remember {
        SweepRecorder(ctx, dir, object : SweepRecorder.Callback {
            override fun onStatus(s: SweepRecorder.LiveStatus) { main.post { status = s } }
            override fun onError(msg: String) { main.post { error = msg } }
        })
    }
    var pick by remember { mutableStateOf(LivePick()) }
    var live by remember { mutableStateOf<LiveSegmenter.Update?>(null) }
    // the live pick: 0 none yet, 1 being saved, 2 saved (then measured at Stop), 3 left to the cut after recording
    val pickState = remember { AtomicInteger(0) }
    LaunchedEffect(Unit) { if (model.diag == null) model.runDiagnosis() }
    LaunchedEffect(Unit) { model.samLightNow() }
    DisposableEffect(Unit) { onDispose { rec.close(); if (!keep[0]) dir.deleteRecursively() } }
    fun stop() {
        if (phase != RecPhase.RECORDING) return
        phase = RecPhase.SAVING
        val p = pick
        rec.stop { d ->
            // the live segmentation stops; a pick it is still writing is waited for (a few ms)
            rec.live?.close()
            val t0 = System.currentTimeMillis()
            while (pickState.get() == 1 && System.currentTimeMillis() - t0 < 3000) Thread.sleep(10)
            val cutLater = pickState.compareAndSet(0, 3)
            main.post {
                keep[0] = true; runCatching { model.diagFile(d) }
                if (p.tap != null || p.box != null) { if (cutLater) model.cutPick(d, rec.sensorOrientation, p.tap?.x, p.tap?.y, p.box) else model.runSweep(d) }
                model.openReview(d)
            }
        }
    }
    fun begin(p: LivePick? = null) {
        if (phase != RecPhase.READY || status == null || error != null) return
        if (p != null && (p.tap != null || p.box != null)) {
            // the tracking picture, upright: frames over 1000 px wide are halved, as in the engine
            val sz = rec.size; val down = if (sz.width > 1000) 2 else 1
            val turned = rec.sensorOrientation % 180 != 0
            val w = (if (turned) sz.height else sz.width) / down; val h = (if (turned) sz.width else sz.height) / down
            val rot = rec.sensorOrientation
            val mode = if (p.box != null) "box" else "tap"
            rec.live = LiveSegmenter({ model.samLight }, w, h,
                onUpdate = { u -> main.post { live = u } },
                onFirstMask = { f, m, ms ->
                    if (pickState.compareAndSet(0, 1)) {
                        runCatching {
                            val b = p.box?.let { listOf(it[0] * m.w, it[1] * m.h, it[2] * m.w, it[3] * m.h) }
                            val t = p.tap?.let { listOf(it.x * m.w, it.y * m.h) }
                            ObjectPick.saveMask(dir, Pick(f, ObjectPick.frameFile(dir, f).relativeTo(dir).path, rot, m.w, m.h, mode, t, b,
                                maskScore = m.score, maskAreaPx = m.area, maskBox = m.bounds()?.toList(), samEncodeMs = ms, samDecodeMs = 0,
                                name = "", tapeCm = listOf(null, null, null)), m)
                        }.onFailure { pickState.set(0) }.onSuccess { pickState.set(2) }
                    }
                }).also { it.begin(p.box, p.tap?.let { o -> floatArrayOf(o.x, o.y) }) }
        }
        phase = RecPhase.RECORDING; rec.start()
    }
    LaunchedEffect(status?.seconds) { if ((status?.seconds ?: 0.0) > 20) stop() }
    DtRecordChrome(status, phase, error, onBack = { model.back() }, onStart = { begin() }, onStop = { stop() }, pick = pick,
        onMode = { pick = pick.copy(mode = it) },
        outline = live?.outline, followed = live?.tracked ?: 0, segmented = live?.segmented == true, samMs = live?.samMs, anchors = live?.anchors ?: 0,
        onTap = { o -> if (status != null && error == null) { pick = pick.copy(tap = o, box = null, drag = null); begin(pick) } },
        onDrag = { r -> pick = pick.copy(drag = r) },
        onBox = { r -> if (status != null && error == null && abs(r[2] - r[0]) > 0.04f && abs(r[3] - r[1]) > 0.04f) {
            pick = pick.copy(box = r, tap = null, drag = null); begin(pick) } else pick = pick.copy(drag = null) }) {
        AndroidView(factory = { c ->
            TextureView(c).apply {
                surfaceTextureListener = object : TextureView.SurfaceTextureListener {
                    override fun onSurfaceTextureAvailable(st: SurfaceTexture, w: Int, h: Int) { rec.open(st) }
                    override fun onSurfaceTextureSizeChanged(st: SurfaceTexture, w: Int, h: Int) {}
                    override fun onSurfaceTextureDestroyed(st: SurfaceTexture) = true
                    override fun onSurfaceTextureUpdated(st: SurfaceTexture) {}
                }
            }
        }, modifier = Modifier.fillMaxSize())
    }
}

@Composable
private fun DtRecordChrome(status: SweepRecorder.LiveStatus?, phase: RecPhase, error: String?, onBack: () -> Unit,
                           onStart: () -> Unit, onStop: () -> Unit, pick: LivePick = LivePick(), onMode: (PickMode) -> Unit = {},
                           onTap: (Offset) -> Unit = {}, onDrag: (FloatArray?) -> Unit = {}, onBox: (FloatArray) -> Unit = {},
                           outline: FloatArray? = null, followed: Int = 0, segmented: Boolean = false, samMs: Long? = null, anchors: Int = 0,
                           preview: @Composable () -> Unit) {
    val turn = status?.turnDeg ?: 0.0
    val gyroDead = status != null && status.gyroHz < 1 && status.accelHz > 1
    Column(Modifier.fillMaxSize()) {
        TopBar("Perekam sapuan", "Kamera + sensor gerak", onBack = if (phase == RecPhase.READY) onBack else null)
        // the preview takes what is left: the controls below always stay on screen, whatever the screen's height
        androidx.compose.foundation.layout.BoxWithConstraints(Modifier.weight(1f).fillMaxWidth().background(Color.Black), contentAlignment = Alignment.Center) {
            val pw = min(maxWidth.value, maxHeight.value * 3f / 4f).dp          // 3:4, as large as fits both ways
            Box(Modifier.size(pw, (pw.value * 4f / 3f).dp)) {
                preview()
                // touch the object (or drag a box round it) on the live picture: it is picked, and recording starts
                Box(Modifier.fillMaxSize().pointerInput(phase, pick.mode) {
                    if (phase != RecPhase.READY) return@pointerInput
                    val wpx = size.width.toFloat(); val hpx = size.height.toFloat()
                    if (pick.mode == PickMode.TAP) detectTapGestures { o -> onTap(Offset(o.x / wpx, o.y / hpx)) }
                    else {
                        var a = Offset.Zero; var b = Offset.Zero
                        fun r() = floatArrayOf(min(a.x, b.x) / wpx, min(a.y, b.y) / hpx, max(a.x, b.x) / wpx, max(a.y, b.y) / hpx)
                        detectDragGestures(onDragStart = { a = it; b = it }, onDrag = { ch, _ -> b = ch.position; onDrag(r()) }, onDragEnd = { onBox(r()) })
                    }
                })
                Canvas(Modifier.fillMaxSize()) {
                    // the object as followed by the tracker, every frame
                    outline?.takeIf { it.size >= 6 }?.let { o -> drawOutline(o, size.width, size.height) }
                    if (outline == null || phase == RecPhase.READY) (pick.box ?: pick.drag)?.let { r -> drawRect(Color.White, Offset(r[0] * size.width, r[1] * size.height),
                        Size((r[2] - r[0]) * size.width, (r[3] - r[1]) * size.height), style = Stroke(3.dp.toPx())) }
                    pick.tap?.let { p -> val c = Offset(p.x * size.width, p.y * size.height)
                        drawCircle(Color.White, 12.dp.toPx(), c); drawCircle(C.brand, 8.dp.toPx(), c) }
                }
                Row(Modifier.align(Alignment.TopStart).padding(8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (phase == RecPhase.RECORDING) Chip("REC ${(status?.seconds ?: 0.0).f1()} s", Tone.RED, "fiber_manual_record")
                    if (phase != RecPhase.READY && (pick.tap != null || pick.box != null))
                        Chip(if (segmented) "Tersegmentasi · $followed titik" else "Memotong objek…", if (segmented) Tone.OK else Tone.GREY,
                            if (segmented) "check" else "sync")
                    if (phase == RecPhase.READY) Chip(status?.size ?: "kamera…", Tone.GREY, "photo_camera")
                }
                Column(Modifier.align(Alignment.BottomStart).padding(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        Chip("kamera ${status?.cameraFps?.toInt() ?: 0} fps", Tone.GREY)
                        Chip("acc ${status?.accelHz?.toInt() ?: 0} Hz", Tone.GREY)
                        Chip(if (gyroDead) "gyro diam" else "gyro ${status?.gyroHz?.toInt() ?: 0} Hz", if (gyroDead) Tone.WARN else Tone.GREY)
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        if (gyroDead) Chip("rotasi ${status!!.rotationHz.toInt()} Hz", Tone.WARN)
                        if (phase != RecPhase.READY) Chip("${status?.savedFrames ?: 0} foto · ${status?.dropped ?: 0} terlewat", Tone.GREY)
                    }
                    // MobileSAM: how long one cut takes on this phone, and how many times it has re-cut the object
                    if (phase != RecPhase.READY && segmented && samMs != null)
                        Chip("MobileSAM ${(samMs / 1000.0).f1()} s · dipotong ulang ${anchors}×", Tone.GREY, "memory")
                }
            }
        }
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (error != null) Banner(error, C.redL, C.red, "error")
            when (phase) {
                RecPhase.READY -> {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Chip("Klik objek", if (pick.mode == PickMode.TAP) Tone.BRAND else Tone.GREY, "touch_app") { onMode(PickMode.TAP) }
                        Chip("Tarik kotak", if (pick.mode == PickMode.BOX) Tone.BRAND else Tone.GREY, "highlight_alt") { onMode(PickMode.BOX) }
                    }
                    T((if (pick.mode == PickMode.TAP) "Sentuh objeknya" else "Tarik kotak di sekeliling objek") +
                        " untuk memilih dan mulai rekam: objek langsung tersegmentasi. Kelilingi objek pelan ±90° (5–10 detik); " +
                        "ukuran dan berat volumetrik keluar otomatis setelah Selesai.", 13.sp, color = C.t2)
                }
                RecPhase.RECORDING -> {
                    T("Kelilingi objek pelan… putaran ${turn.toInt()}° dari target 60°", 14.sp, FontWeight.SemiBold)
                    T("Area magenta = objek tersegmentasi, tiap frame. Jaga objek tetap di layar.", 12.sp, color = C.t3)
                    LinearProgressIndicator(progress = { min(1f, (turn / 60.0).toFloat()) }, modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
                        color = if (turn >= 60) C.green else C.brand, trackColor = C.line)
                }
                RecPhase.SAVING -> Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = C.brand)
                    T("Menyimpan rekaman, lalu langsung dihitung…", 14.sp, modifier = Modifier.padding(start = 10.dp))
                }
            }
            when (phase) {
                RecPhase.READY -> SecondaryButton("Mulai tanpa pilih (pilih nanti)", "fiber_manual_record", Modifier.fillMaxWidth()) { onStart() }
                RecPhase.RECORDING -> PrimaryButton("Selesai", "stop_circle", Modifier.fillMaxWidth(), color = C.green, enabled = (status?.seconds ?: 0.0) >= 1.5) { onStop() }
                RecPhase.SAVING -> Unit
            }
        }
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawOutline(o: FloatArray, w: Float, h: Float) {
    val path = androidx.compose.ui.graphics.Path().apply {
        moveTo(o[0] * w, o[1] * h); var i = 2
        while (i + 1 < o.size) { lineTo(o[i] * w, o[i + 1] * h); i += 2 }
        close()
    }
    drawPath(path, C.brand.copy(alpha = 0.35f))
    drawPath(path, C.brand, style = Stroke(2.5f * density))
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawBox(b: List<Float>, w: Float, h: Float) {
    if (b.size != 16) return
    fun p(i: Int) = Offset(b[2 * i] * w, b[2 * i + 1] * h)
    for ((a, e) in listOf(0 to 1, 1 to 2, 2 to 3, 3 to 0, 4 to 5, 5 to 6, 6 to 7, 7 to 4, 0 to 4, 1 to 5, 2 to 6, 3 to 7))
        drawLine(Color(0xFF3CDC3C), p(a), p(e), strokeWidth = 2.5f * density)
}

/** For the screenshot test: the recorder's screen around a still picture. */
@Composable
internal fun DtRecordPreview(picture: Bitmap?, recording: Boolean, gyroSilent: Boolean = false, tap: Offset? = null, outline: FloatArray? = null) {
    val st = SweepRecorder.LiveStatus(recording, if (recording) 3.4 else 0.0, if (recording) 48 else 0, 0, 29.8, 198.0,
        if (gyroSilent) 0.0 else 199.0, if (recording) 38.0 else 0.0, "1280×960", rotationHz = 200.0)
    DtRecordChrome(st, if (recording) RecPhase.RECORDING else RecPhase.READY, null, {}, {}, {}, pick = LivePick(tap = tap),
        outline = outline, followed = if (outline != null) 42 else 0, segmented = outline != null, samMs = if (outline != null) 1800L else null,
        anchors = if (outline != null) 3 else 0) {
        if (picture != null) Image(picture.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
    }
}

// ------------------------------------------------------------------ review + pick the object
internal enum class PickMode { TAP, BOX }

/** The pick made on the live picture, as fractions of it. */
internal data class LivePick(val mode: PickMode = PickMode.TAP, val tap: Offset? = null, val box: FloatArray? = null, val drag: FloatArray? = null)

private fun Double.cmText() = (if (this % 1.0 == 0.0) "%.0f" else "%.1f").format(this).replace('.', ',')

/** Everything the review screen shows on opening a recording, read in one go. */
private class ReviewLoad(val quality: SweepQuality, val frames: List<Int>, val frame: Int, val picture: Bitmap?, val pick: Pick?, val mask: Mask?) {
    companion object {
        fun load(dir: File, rotation: Int): ReviewLoad {
            val q = SweepAnalysis.read(dir, ObjectPick.sameClock(dir))
            val frames = ObjectPick.frames(dir)
            val pick = ObjectPick.load(dir)?.takeIf { it.frame in frames }
            val frame = pick?.frame ?: q.bestFrame.takeIf { it in frames } ?: frames.getOrElse(frames.size / 2) { -1 }
            val pic = if (frame >= 0) ObjectPick.upright(dir, frame, rotation) else null
            return ReviewLoad(q, frames, frame, pic, pick, pick?.let { ObjectPick.loadMask(dir, it) })
        }
    }
}

/** Set by the screenshot test (as LocalStill is): load at once instead of in the background. */
internal object LocalStillValue {
    @Volatile private var v = false
    fun get() = v
    fun set(b: Boolean) { v = b }
}

/** After a sweep: is it good enough, which object (tap it or drag a box), and the tape-measure size for the test. */
@Composable
fun DtReviewScreen(model: AppModel, activity: Activity, dirPath: String) {
    val dir = remember(dirPath) { File(dirPath) }
    val scope = rememberCoroutineScope()
    val rotation = remember(dirPath) { ObjectPick.rotation(dir) }
    // a reopened recording shows its saved pick; the screenshot test loads everything at once
    val first = remember(dirPath) { if (LocalStillValue.get()) ReviewLoad.load(dir, rotation) else null }
    var quality by remember { mutableStateOf(first?.quality) }
    var frames by remember { mutableStateOf(first?.frames.orEmpty()) }
    var frame by remember { mutableStateOf(first?.frame ?: -1) }
    var picture by remember { mutableStateOf(first?.picture) }
    var mode by remember { mutableStateOf(if (first?.pick?.mode == "box") PickMode.BOX else PickMode.TAP) }
    var tap by remember { mutableStateOf(first?.pick?.tap?.let { Offset(it[0], it[1]) }) }
    var box by remember { mutableStateOf(first?.pick?.box?.toFloatArray()) }
    var drag by remember { mutableStateOf<FloatArray?>(null) }
    var mask by remember { mutableStateOf(first?.mask) }
    var tint by remember { mutableStateOf(first?.mask?.let { ObjectPick.tint(it) }) }
    var busy by remember { mutableStateOf<String?>(null) }
    var encMs by remember { mutableStateOf(first?.pick?.samEncodeMs) }
    var decMs by remember { mutableStateOf(first?.pick?.samDecodeMs ?: 0L) }
    var name by remember { mutableStateOf(first?.pick?.name.orEmpty()) }
    var tape by remember { mutableStateOf(first?.pick?.tapeCm?.map { it?.cmText() ?: "" } ?: listOf("", "", "")) }
    var saved by remember { mutableStateOf(first?.pick != null) }
    val cache = remember { HashMap<Int, Embedding>() }
    var loadedFrame by remember { mutableStateOf(first?.frame ?: -1) }
    var detail by remember { mutableStateOf(false) }

    LaunchedEffect(dirPath) {
        if (first != null) return@LaunchedEffect
        val l = withContext(Dispatchers.IO) { ReviewLoad.load(dir, rotation) }
        quality = l.quality; frames = l.frames; picture = l.picture; loadedFrame = l.frame; frame = l.frame
        l.pick?.let { p ->
            name = p.name; tape = p.tapeCm.map { it?.cmText() ?: "" }; saved = true
            mode = if (p.mode == "box") PickMode.BOX else PickMode.TAP
            tap = p.tap?.let { Offset(it[0], it[1]) }; box = p.box?.toFloatArray(); encMs = p.samEncodeMs; decMs = p.samDecodeMs
            mask = l.mask; tint = l.mask?.let { withContext(Dispatchers.Default) { ObjectPick.tint(it) } }
        }
    }
    val job = model.pickJobs[dirPath]
    val sj = model.sweepJobs[dirPath]
    var result by remember(dirPath) { mutableStateOf(if (LocalStillValue.get()) SweepRun.load(dir) else null) }
    LaunchedEffect(dirPath, sj?.result) {
        result = sj?.result ?: withContext(Dispatchers.IO) { SweepRun.load(dir) }
    }
    LaunchedEffect(job) {
        if (job != "done") return@LaunchedEffect
        val l = withContext(Dispatchers.IO) { ReviewLoad.load(dir, rotation) }
        val p = l.pick ?: return@LaunchedEffect
        loadedFrame = l.frame; frame = l.frame; picture = l.picture; mask = l.mask
        tint = l.mask?.let { withContext(Dispatchers.Default) { ObjectPick.tint(it) } }
        mode = if (p.mode == "box") PickMode.BOX else PickMode.TAP
        tap = p.tap?.let { Offset(it[0], it[1]) }; box = p.box?.toFloatArray(); encMs = p.samEncodeMs; decMs = p.samDecodeMs; saved = true
    }
    LaunchedEffect(frame) {
        if (frame < 0 || frame == loadedFrame) return@LaunchedEffect
        loadedFrame = frame
        picture = withContext(Dispatchers.IO) { ObjectPick.upright(dir, frame, rotation) }
        mask = null; tint = null; tap = null; box = null
    }

    fun cut(point: Offset?, rect: FloatArray?) {
        val pic = picture ?: return
        if (busy != null) return
        scope.launch {
            busy = "Memuat MobileSAM…"
            val sam = model.samLightNow()
            if (sam == null) { busy = null; model.toast("MobileSAM tidak bisa dimuat."); return@launch }
            val e = cache[frame] ?: run {
                busy = "Memotong objek… sekali per foto, beberapa detik"
                val t0 = System.nanoTime()
                withContext(Dispatchers.Default) { sam.embed(ObjectPick.argb(pic), pic.width, pic.height) }.also {
                    cache[frame] = it; encMs = (System.nanoTime() - t0) / 1_000_000
                }
            }
            val t1 = System.nanoTime()
            val m = withContext(Dispatchers.Default) {
                (if (point != null) sam.tapRefined(e, point.x, point.y).maxBy { it.score } else sam.box(e, rect!![0], rect[1], rect[2], rect[3])).largestPart()
            }
            decMs = (System.nanoTime() - t1) / 1_000_000
            mask = m; tint = withContext(Dispatchers.Default) { ObjectPick.tint(m) }; saved = false
            busy = null
        }
    }

    fun save(): Boolean {
        val pic = picture ?: return false; val m = mask ?: return false
        val b = m.bounds()
        val p = Pick(frame, ObjectPick.frameFile(dir, frame).relativeTo(dir).path, rotation, pic.width, pic.height,
            if (tap != null) "tap" else "box", tap?.let { listOf(it.x, it.y) }, box?.toList(), maskScore = m.score, maskAreaPx = m.area,
            maskBox = b?.toList(), samEncodeMs = encMs, samDecodeMs = decMs, name = name.trim(), tapeCm = tape.map { ObjectPick.cm(it) })
        ObjectPick.save(dir, p, pic, m)
        saved = true
        return true
    }

    Column(Modifier.fillMaxSize()) {
        TopBar("Rekaman sapuan", dir.name, onBack = { model.back() })
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            when {
                sj?.running == true -> Card {
                    T("Menghitung ukuran di HP", 15.sp, FontWeight.SemiBold)
                    T(sj.stage + "…", 13.sp, color = C.t2)
                    Spacer(Modifier.height(8.dp))
                    LinearProgressIndicator(progress = { sj.progress }, modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
                        color = C.brand, trackColor = C.line)
                }
                job == "cutting" -> Card {
                    T("Memotong objek pilihan (MobileSAM)", 15.sp, FontWeight.SemiBold)
                    T("Lalu ukurannya dihitung otomatis.", 13.sp, color = C.t2)
                    Spacer(Modifier.height(8.dp))
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)), color = C.brand, trackColor = C.line)
                }
                sj?.error != null -> Card {
                    Banner(sj.error, C.redL, C.red, "error")
                    Spacer(Modifier.height(8.dp))
                    SecondaryButton("Coba hitung lagi", "refresh", Modifier.fillMaxWidth()) { model.runSweep(dir) }
                }
                result != null -> ResultCard(result!!, model, tape) { model.useSweep(dir, result!!) }
            }
            quality?.let { q ->
                VerdictCard(q.level, "Kualitas rekaman", SweepAnalysis.verdict(q) + if (detail) "" else " Ketuk untuk detail.",
                    onClick = { detail = !detail }, open = detail)
                if (detail) Card(padding = 10.dp) { q.checks.forEach { CheckLine(it) } }
            } ?: Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = C.brand)
                T("Memeriksa rekaman…", 14.sp, modifier = Modifier.padding(start = 10.dp))
            }
            Card {
                T("Pilih objek", 15.sp, FontWeight.SemiBold)
                T("Klik objeknya, atau tarik kotak di sekelilingnya. Objek apa saja.", 12.5.sp, color = C.t2)
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Chip("Klik objek", if (mode == PickMode.TAP) Tone.BRAND else Tone.GREY, "touch_app") { mode = PickMode.TAP }
                    Chip("Tarik kotak", if (mode == PickMode.BOX) Tone.BRAND else Tone.GREY, "highlight_alt") { mode = PickMode.BOX }
                }
                Spacer(Modifier.height(10.dp))
                val pic = picture
                val pos = frames.indexOf(frame)
                val res = result
                if (pic != null) PickImage(pic, tint, mode, tap, box ?: drag,
                    outline = res?.outlines?.getOrNull(pos)?.takeIf { tint == null }, boxLines = res?.boxes?.getOrNull(pos),
                    onTap = { p -> tap = p; box = null; cut(p, null) },
                    onDrag = { r -> drag = r },
                    onBox = { r -> drag = null; if (abs(r[2] - r[0]) > 12 && abs(r[3] - r[1]) > 12) { box = r; tap = null; cut(null, r) } })
                else Box(Modifier.fillMaxWidth().aspectRatio(3f / 4f).background(Color(0xFFE5E9F0)), contentAlignment = Alignment.Center) {
                    T(if (frames.isEmpty() && quality != null) "Tidak ada foto di rekaman ini" else "Memuat foto…", 13.sp, color = C.t2)
                }
                if (frames.size > 1) {
                    val i = frames.indexOf(frame).coerceAtLeast(0)
                    Slider(value = i.toFloat(), onValueChange = { v -> frames.getOrNull(v.toInt())?.let { if (it != frame && busy == null) frame = it } },
                        valueRange = 0f..(frames.size - 1).toFloat())
                    T("Foto ${i + 1} dari ${frames.size}" + if (frame == quality?.bestFrame) " · paling tajam" else "", 12.sp, color = C.t3)
                }
                if (job == "cutting") Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 6.dp)) {
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp, color = C.brand)
                    T("Memotong objek yang disentuh di perekam… bisa 10–30 detik", 13.sp, FontWeight.SemiBold, C.brandD, modifier = Modifier.padding(start = 8.dp))
                }
                busy?.let { b ->
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 6.dp)) {
                        CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp, color = C.brand)
                        T(b, 13.sp, FontWeight.SemiBold, C.brandD, modifier = Modifier.padding(start = 8.dp))
                    }
                }
                mask?.let { m ->
                    T("Objek terpilih · skor ${"%.2f".format(m.score)} · potong ${encMs?.let { (it / 1000.0).f1() + " s" } ?: "–"} + ${decMs} ms",
                        12.5.sp, FontWeight.SemiBold, C.green, modifier = Modifier.padding(top = 6.dp))
                }
            }
            Card {
                T("Data uji", 15.sp, FontWeight.SemiBold)
                T("Ukuran dihitung otomatis. Isi ukuran meteran (boleh kosong) untuk membandingkan akurasinya.", 12.5.sp, color = C.t2)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(name, { name = it.take(40); saved = false }, singleLine = true, modifier = Modifier.fillMaxWidth(),
                    label = { T("Nama objek (mis. kardus, galon)", 13.sp) })
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("P", "L", "T").forEachIndexed { i, l ->
                        OutlinedTextField(tape[i], { v -> tape = tape.toMutableList().also { it[i] = v.filter { c -> c.isDigit() || c == ',' || c == '.' }.take(6) }; saved = false },
                            singleLine = true, modifier = Modifier.weight(1f), label = { T("$l (cm)", 13.sp) },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal))
                    }
                }
                T("Ukuran meteran, boleh dikosongkan", 12.sp, color = C.t3)
            }
            Spacer(Modifier.height(2.dp))
        }
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (!saved || result == null && sj?.running != true && job != "cutting")
                PrimaryButton(if (saved) "Hitung ukuran" else "Simpan pilihan & hitung ukuran", "straighten", Modifier.fillMaxWidth(),
                    enabled = mask != null && busy == null && sj?.running != true) {
                    if (saved || save()) model.runSweep(dir)
                }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryButton("Bagikan ZIP", "folder_zip", Modifier.weight(1f)) {
                    if (mask != null && !saved) save()
                    val label = name.trim().ifEmpty { "objek" }.replace(Regex("[^A-Za-z0-9_-]+"), "_")
                    model.shareFile(activity, "application/zip", "Bagikan rekaman sapuan") { model.zip(listOf(dir), "dt20_${dir.name}_$label.zip") }
                }
                SecondaryButton("Rekam lagi", "videocam", Modifier.weight(1f)) { model.back(); model.go(Screen.DtRecord) }
            }
        }
    }
}

/** The picture with the pick drawn on it; taps and drags come back in picture pixels. */
@Composable
private fun PickImage(pic: Bitmap, tint: Bitmap?, mode: PickMode, tap: Offset?, rect: FloatArray?,
                      outline: List<Float>? = null, boxLines: List<Float>? = null,
                      onTap: (Offset) -> Unit, onDrag: (FloatArray) -> Unit, onBox: (FloatArray) -> Unit) {
    var view by remember { mutableStateOf(IntSize(1, 1)) }
    val k = pic.width.toFloat() / max(1, view.width)          // view px -> picture px
    Box(Modifier.fillMaxWidth().aspectRatio(pic.width.toFloat() / pic.height).clip(RoundedCornerShape(12.dp)).onSizeChanged { view = it }
        .pointerInput(mode, k) {
            if (mode == PickMode.TAP) detectTapGestures { o -> onTap(Offset(o.x * k, o.y * k)) }
            else {
                var a = Offset.Zero; var b = Offset.Zero
                detectDragGestures(
                    onDragStart = { o -> a = o; b = o },
                    onDrag = { ch, _ -> b = ch.position; onDrag(floatArrayOf(min(a.x, b.x) * k, min(a.y, b.y) * k, max(a.x, b.x) * k, max(a.y, b.y) * k)) },
                    onDragEnd = { onBox(floatArrayOf(min(a.x, b.x) * k, min(a.y, b.y) * k, max(a.x, b.x) * k, max(a.y, b.y) * k)) },
                )
            }
        }) {
        Image(pic.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.FillBounds)
        if (tint != null) Image(tint.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.FillBounds)
        Canvas(Modifier.fillMaxSize()) {
            val s = size.width / pic.width
            // this frame's segmentation and box, from the measurement
            outline?.takeIf { it.size >= 6 }?.let { drawOutline(it.toFloatArray(), size.width, size.height) }
            boxLines?.let { drawBox(it, size.width, size.height) }
            rect?.let { r -> drawRect(Color.White, Offset(r[0] * s, r[1] * s), Size((r[2] - r[0]) * s, (r[3] - r[1]) * s), style = Stroke(3.dp.toPx())) }
            tap?.let { p -> drawCircle(Color.White, 9.dp.toPx(), Offset(p.x * s, p.y * s)); drawCircle(C.brand, 6.dp.toPx(), Offset(p.x * s, p.y * s)) }
        }
    }
}

/** The measured size, as the ARCore result shows it, with the tape size beside it when one was typed. */
@Composable
private fun ResultCard(r: SweepResult, model: AppModel, tape: List<String>, onUse: () -> Unit) {
    val settings by model.store.settings.collectAsState()
    val volL = r.lengthCm * r.widthCm * r.heightCm / 1000
    val volKg = r.lengthCm * r.widthCm * r.heightCm / settings.divisor
    Card(highlight = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            T("Ukuran", 15.sp, FontWeight.SemiBold, modifier = Modifier.weight(1f))
            if (r.ok) Chip("Akurat · skor ${r.confidence}", Tone.OK, "check_circle") else Chip("Perlu Dicek · skor ${r.confidence}", Tone.WARN, "warning")
        }
        T("${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm", 28.sp, FontWeight.Bold)
        T("Volume ${volL.id()} L · berat volumetrik ${volKg.id(2)} kg (÷ ${settings.divisor.toDouble().id(0)})", 13.sp, color = C.t2)
        val t = tape.map { ObjectPick.cm(it) }
        if (t.all { it != null }) {
            val e = listOf(r.lengthCm - t[0]!!, r.widthCm - t[1]!!, r.heightCm - t[2]!!)
            T("Meteran ${t[0]!!.cm()} × ${t[1]!!.cm()} × ${t[2]!!.cm()} cm · selisih " + e.joinToString(" / ") { (if (it >= 0) "+" else "") + it.id() }, 12.5.sp, FontWeight.SemiBold, C.brandD)
        }
        T("${r.method} · ${r.frames} foto · ${r.densePoints} titik depth · ${r.seconds.id(0)} s di HP", 12.sp, color = C.t3)
        r.notes.forEach { T("• $it", 12.sp, color = C.amber) }
        Spacer(Modifier.height(4.dp))
        T("Geser slider foto: area magenta dan kotak hijau = hasil segmentasi tiap frame.", 12.sp, color = C.t3)
        if (model.draft != null) {
            Spacer(Modifier.height(8.dp))
            T("Resi ${model.draft!!.resi}", 12.5.sp, FontWeight.SemiBold, color = C.t2)
            PrimaryButton("Pakai ukuran ini", "arrow_forward", Modifier.fillMaxWidth()) { onUse() }
        }
    }
}

/** Settings card: the DT20 test tools and their recordings. */
@Composable
fun DtSettingsCard(model: AppModel, activity: Activity) {
    var ask by remember { mutableStateOf(false) }
    var tick by remember { mutableStateOf(0) }
    val dirs = remember(tick) { model.store.dtDir.listFiles()?.filter { it.isDirectory }.orEmpty() }
    val mb = remember(tick) { dirs.sumOf { d -> d.walkTopDown().filter { it.isFile }.sumOf { it.length() } } / (1 shl 20) }
    Card {
        T("Uji HP tanpa ARCore (Urovo DT20/DT50)", 15.sp, FontWeight.SemiBold)
        T("Diagnostik sensor dan kamera, dan rekaman sapuan objek untuk membangun engine pengganti ARCore.", 12.5.sp, color = C.t2)
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton("Diagnostik", "monitor_heart", Modifier.weight(1f)) { model.go(Screen.Diag) }
            SecondaryButton("Perekam", "videocam", Modifier.weight(1f)) { model.go(Screen.DtRecord) }
        }
        Spacer(Modifier.height(8.dp))
        T("${dirs.size} rekaman tersimpan · $mb MB", 12.5.sp, color = C.t3)
        if (dirs.isNotEmpty()) {
            Spacer(Modifier.height(6.dp))
            SecondaryButton("Bagikan semua rekaman sapuan (ZIP)", "folder_zip", Modifier.fillMaxWidth()) {
                model.shareFile(activity, "application/zip", "Bagikan rekaman sapuan") { model.zip(dirs, "dt20_semua_rekaman.zip") }
            }
            TextButton(onClick = { ask = true }) { T("Hapus semua rekaman sapuan", 13.sp, color = C.red) }
        }
    }
    if (ask) AlertDialog(onDismissRequest = { ask = false },
        title = { T("Hapus ${dirs.size} rekaman?", 18.sp, FontWeight.SemiBold) },
        text = { T("Foto dan data sensor rekaman sapuan terhapus dari HP ini. Hasil ukur paket tidak ikut terhapus.", color = C.t2) },
        confirmButton = { TextButton(onClick = { dirs.forEach { it.deleteRecursively() }; ask = false; tick++ }) { T("Hapus", weight = FontWeight.SemiBold, color = C.red) } },
        dismissButton = { TextButton(onClick = { ask = false }) { T("Batal", color = C.t2) } })
}

/** Home card on a phone without ARCore: the way into the DT20 tests. */
@Composable
fun DtHomeCard(model: AppModel) {
    Card {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconTile("biotech", C.brand, C.brandL)
            Column(Modifier.weight(1f).padding(start = 12.dp)) {
                T("Uji tanpa ARCore", 15.sp, FontWeight.SemiBold)
                T("Diagnostik HP dan perekam sapuan objek (klik atau tarik kotak)", 12.5.sp, color = C.t2)
            }
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton("Diagnostik", "monitor_heart", Modifier.weight(1f)) { model.go(Screen.Diag) }
            SecondaryButton("Perekam", "videocam", Modifier.weight(1f)) { model.go(Screen.DtRecord) }
        }
    }
}
