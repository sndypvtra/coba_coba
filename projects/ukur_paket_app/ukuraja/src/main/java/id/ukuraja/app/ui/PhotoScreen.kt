package id.ukuraja.app.ui

import android.app.Activity
import android.graphics.SurfaceTexture
import android.os.Handler
import android.os.Looper
import android.view.TextureView
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.draw.scale
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import id.ukuraja.app.data.cm
import id.ukuraja.app.data.id
import id.ukurpaket.app.marker.MarkerSheet
import id.ukurpaket.app.photo.PhotoCamera
import id.ukurpaket.app.photo.PhotoFiles
import id.ukurpaket.app.photo.PhotoResult
import kotlinx.coroutines.delay
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/** The photo mode: camera -> photo -> tap the parcel -> size; more photos from other corners when wanted. */
@Composable
fun PhotoScreen(model: AppModel, activity: Activity) {
    CameraPermission(model, activity) {
        val f = model.photo
        val shot = f.shots.firstOrNull { it.index == f.current }
        val subtitle = (model.draft?.resi?.let { "Resi $it · " } ?: "") + if (f.shots.isEmpty()) "foto dari pojok paket" else "${f.shots.size} foto"
        if (shot == null) LiveCamera(model, f, subtitle) else ShotScreen(model, f, shot, subtitle)
    }
}

// ------------------------------------------------------------------ camera
@Composable
private fun LiveCamera(model: AppModel, f: PhotoFlow, subtitle: String) {
    val ctx = LocalContext.current
    val main = remember { Handler(Looper.getMainLooper()) }
    var live by remember { mutableStateOf<PhotoCamera.Live?>(null) }
    var marker by remember { mutableStateOf(LiveMarkerState.NONE) }
    var error by remember { mutableStateOf<String?>(null) }
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) { while (true) { delay(250); now = System.currentTimeMillis() } }
    val cam = remember {
        PhotoCamera(ctx, object : PhotoCamera.Callback {
            override fun onLive(s: PhotoCamera.Live) { main.post { live = s } }
            override fun onError(msg: String) { main.post { error = msg; f.capturing = false } }
        })
    }
    val liveMarker = remember { LiveMarker { s -> main.post { marker = s } } }
    DisposableEffect(Unit) {
        cam.preview = liveMarker
        onDispose { cam.preview = null; liveMarker.close(); cam.close() }
    }
    // a sheet seen in the last 0,8 s counts as in view
    val seen = marker.takeIf { it.id != null && now - it.atMs < 800 }
    PhotoCameraChrome("Ukur paket", subtitle, live, seen, f.capturing, error, f.shots,
        onBack = { model.back() },
        onGuide = { model.go(Screen.Guide(3)) },
        onShutter = {
            if (!f.capturing && error == null) {
                f.capturing = true
                cam.capture(sweepIf = { s -> f.wantsSweep(s) }) { s -> main.post { f.onShot(s) } }
            }
        },
        onOpen = { f.current = it }) {
        AndroidView(factory = { c ->
            TextureView(c).apply {
                surfaceTextureListener = object : TextureView.SurfaceTextureListener {
                    override fun onSurfaceTextureAvailable(st: SurfaceTexture, w: Int, h: Int) { cam.open(st) }
                    override fun onSurfaceTextureSizeChanged(st: SurfaceTexture, w: Int, h: Int) {}
                    override fun onSurfaceTextureDestroyed(st: SurfaceTexture) = true
                    override fun onSurfaceTextureUpdated(st: SurfaceTexture) {}
                }
            }
        }, modifier = Modifier.fillMaxSize())
    }
}

/** The camera screen around its preview (also drawn by the screenshot test with a still picture). */
@Composable
internal fun PhotoCameraChrome(title: String, subtitle: String, live: PhotoCamera.Live?, marker: LiveMarkerState?, capturing: Boolean, error: String?,
                               shots: List<PhotoShotUi>, onBack: () -> Unit, onGuide: () -> Unit, onShutter: () -> Unit, onOpen: (Int) -> Unit,
                               preview: @Composable () -> Unit) {
    Column(Modifier.fillMaxSize()) {
        TopBar(title, subtitle, onBack = onBack) {
            Box(Modifier.size(44.dp).clip(RoundedCornerShape(22.dp)).clickable(onClick = onGuide), contentAlignment = Alignment.Center) { Sym("help", 22.dp, C.ink) }
        }
        BoxWithConstraints(Modifier.weight(1f).fillMaxWidth().background(Color.Black), contentAlignment = Alignment.Center) {
            val pw = min(maxWidth.value, maxHeight.value * 3f / 4f).dp
            Box(Modifier.size(pw, (pw.value * 4f / 3f).dp)) {
                preview()
                Canvas(Modifier.fillMaxSize()) {
                    // where the autofocus measures (best on the parcel), and the frame's corners
                    val cx = size.width / 2; val cy = size.height / 2; val r = size.width * 0.035f
                    val wc = Color.White.copy(alpha = 0.8f)
                    drawCircle(wc, r, Offset(cx, cy), style = Stroke(2.dp.toPx()))
                    drawLine(wc, Offset(cx - 2 * r, cy), Offset(cx - r, cy), 2.dp.toPx()); drawLine(wc, Offset(cx + r, cy), Offset(cx + 2 * r, cy), 2.dp.toPx())
                    drawLine(wc, Offset(cx, cy - 2 * r), Offset(cx, cy - r), 2.dp.toPx()); drawLine(wc, Offset(cx, cy + r), Offset(cx, cy + 2 * r), 2.dp.toPx())
                    val m = size.width * 0.12f; val c = Color.White.copy(alpha = 0.55f); val l = size.width * 0.07f; val sw = 2.5.dp.toPx()
                    for ((x, y, dx, dy) in listOf(listOf(m, m * 1.4f, 1f, 1f), listOf(size.width - m, m * 1.4f, -1f, 1f),
                            listOf(m, size.height - m * 1.4f, 1f, -1f), listOf(size.width - m, size.height - m * 1.4f, -1f, -1f))) {
                        drawLine(c, Offset(x, y), Offset(x + dx * l, y), sw); drawLine(c, Offset(x, y), Offset(x, y + dy * l), sw)
                    }
                    // the sheet as the live check sees it
                    marker?.corners?.let { q -> drawQuad(q, size.width, size.height, if (marker.big) C.yellow else C.warn, 3.dp.toPx()) }
                }
                if ((live?.brightness ?: 128.0) < 55) Box(Modifier.align(Alignment.TopStart).padding(8.dp)) { Chip("Terlalu gelap: tambah cahaya", Tone.RED, "light_mode") }
            }
        }
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (error != null) Banner(error, C.redL, C.red, "error")
            // below the picture, so it never hides the parcel or the sheet
            if (error == null) Readiness(live, marker, Modifier)
            if (shots.isNotEmpty()) ShotStrip(shots, null, onOpen, onAdd = null)
            // all three checks green: the button breathes, the courier knows it is the moment
            val ready = !capturing && error == null && ready(live) && marker?.big == true
            val t = loopClock(1400, still = 0f)
            val pulse = if (ready) 1f + 0.025f * kotlin.math.sin(t * 2 * Math.PI.toFloat()) else 1f
            PrimaryButton(when {
                    capturing && marker?.big == true -> "Tahan diam…"
                    capturing -> "Tahan diam, mengukur jarak…"
                    marker?.big != true -> "Ambil foto tanpa marker"
                    else -> "Ambil foto"
                }, if (capturing) "timer" else "photo_camera", Modifier.fillMaxWidth().scale(pulse), enabled = !capturing && error == null) { onShutter() }
            if (shots.isNotEmpty()) SecondaryButton("Kembali ke hasil", "arrow_back", Modifier.fillMaxWidth()) { onOpen(shots.last().index) }
        }
    }
}

// ------------------------------------------------------------------ one photo: pick and result
@Composable
private fun ShotScreen(model: AppModel, f: PhotoFlow, shot: PhotoShotUi, subtitle: String) {
    val settings by model.store.settings.collectAsState()
    var hub by remember { mutableStateOf(false) }
    PhotoShotView(shot, f.shots, f.combined, subtitle, settings.divisor, f.combined?.let { f.scaleSource(it) },
        onBack = { model.back() },
        onPick = { t, b -> f.pick(shot.index, t, b) },
        onOpen = { f.current = it },
        onAdd = { f.current = null },
        onRetake = { f.remove(shot.index); f.current = null },
        onUse = { f.use() },
        onHub = { hub = true })
    if (hub) HubDialog(onDismiss = { hub = false }) { reason -> hub = false; model.markHub(reason) }
}

internal enum class PickMode { TAP, BOX }

@Composable
internal fun PhotoShotView(
    shot: PhotoShotUi, shots: List<PhotoShotUi>, combined: PhotoResult?, subtitle: String, divisor: Int, scaleSource: String?,
    onBack: () -> Unit, onPick: (List<Float>?, List<Float>?) -> Unit, onOpen: (Int) -> Unit, onAdd: () -> Unit, onRetake: () -> Unit,
    onUse: () -> Unit, onHub: () -> Unit,
) {
    var mode by remember { mutableStateOf(if (shot.box != null) PickMode.BOX else PickMode.TAP) }
    var drag by remember(shot.index) { mutableStateOf<FloatArray?>(null) }
    val busy = shot.stage != null && shot.stage != "Membaca foto…"
    Column(Modifier.fillMaxSize()) {
        TopBar("Ukur paket", subtitle, onBack = onBack)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (combined != null) ResultCard(combined, shots.mapNotNull { it.result }, divisor, scaleSource)
            Box(Modifier.fillMaxWidth().heightIn(max = if (combined != null) 300.dp else 2000.dp), contentAlignment = Alignment.Center) {
                ShotImage(shot, mode, drag, enabled = !busy,
                    onTap = { x, y -> drag = null; onPick(listOf(x, y), null) },
                    onDrag = { drag = it },
                    onBox = { r -> drag = null; if (abs(r[2] - r[0]) > 12 && abs(r[3] - r[1]) > 12) onPick(null, r.toList()) })
            }
            when {
                shot.stage != null -> ProcessSteps(shot.stage, picked = shot.tap != null || shot.box != null)
                shot.error != null -> Banner(shot.error, C.redL, C.red, "error")
                shot.mask == null -> T(if (mode == PickMode.TAP) "Ketuk paketnya di foto." else "Tarik kotak di sekeliling paket.", 14.sp, FontWeight.SemiBold)
                shot.result != null -> T("Kotak hijau = ukuran terbaca · garis kuning = marker. Salah pilih? Ketuk paketnya lagi.", 12.5.sp, color = C.t3)
            }
            if (shot.result == null || shot.error != null) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Chip("Klik paket", if (mode == PickMode.TAP) Tone.BRAND else Tone.GREY, "touch_app") { mode = PickMode.TAP }
                Chip("Tarik kotak", if (mode == PickMode.BOX) Tone.BRAND else Tone.GREY, "highlight_alt") { mode = PickMode.BOX }
            }
            if (shots.size > 1 || combined != null) ShotStrip(shots, shot.index, onOpen, onAdd)
            TextButton(onClick = onHub) { T("Paket tidak bisa diukur? Tandai Ukur di Hub", 13.sp, color = C.t2) }
        }
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            // a size from blurred photos only is not used: its distance is not known
            if (combined != null) PrimaryButton(if (combined.blurred()) "Foto buram: ulangi foto" else "Pakai ukuran ini",
                if (combined.blurred()) "refresh" else "arrow_forward", Modifier.fillMaxWidth()) { if (combined.blurred()) onRetake() else onUse() }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SmallAction("Ulangi foto", "refresh", Modifier.weight(1f)) { onRetake() }
                SmallAction("Tambah foto", "add", Modifier.weight(1f)) { onAdd() }
            }
        }
    }
}

@Composable
private fun SmallAction(text: String, icon: String, modifier: Modifier, onClick: () -> Unit) {
    OutlinedButton(onClick = onClick, modifier = modifier.height(48.dp), shape = RoundedCornerShape(12.dp), border = BorderStroke(1.5.dp, C.line),
        contentPadding = PaddingValues(horizontal = 6.dp), colors = ButtonDefaults.outlinedButtonColors(containerColor = Color.White)) {
        Sym(icon, 20.dp, C.ink); Spacer(Modifier.width(4.dp))
        T(text, 14.sp, FontWeight.SemiBold, C.ink, maxLines = 1)
    }
}

/** The photo with the cut-out, the measured box, the marker and the pick; taps and drags come back in picture pixels. */
@Composable
private fun ShotImage(shot: PhotoShotUi, mode: PickMode, drag: FloatArray?, enabled: Boolean,
                      onTap: (Float, Float) -> Unit, onDrag: (FloatArray) -> Unit, onBox: (FloatArray) -> Unit) {
    val pic = shot.picture
    var view by remember { mutableStateOf(IntSize(1, 1)) }
    val k = pic.width.toFloat() / max(1, view.width)
    val aspect = pic.width.toFloat() / pic.height
    BoxWithConstraints(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        val w = min(maxWidth.value, maxHeight.value * aspect).dp
        Box(Modifier.size(w, (w.value / aspect).dp).clip(RoundedCornerShape(12.dp)).onSizeChanged { view = it }
            .pointerInput(mode, k, enabled) {
                if (!enabled) return@pointerInput
                if (mode == PickMode.TAP) detectTapGestures { o -> onTap(o.x * k, o.y * k) }
                else {
                    var a = Offset.Zero; var b = Offset.Zero
                    fun r() = floatArrayOf(min(a.x, b.x) * k, min(a.y, b.y) * k, max(a.x, b.x) * k, max(a.y, b.y) * k)
                    detectDragGestures(onDragStart = { o -> a = o; b = o }, onDrag = { ch, _ -> b = ch.position; onDrag(r()) }, onDragEnd = { onBox(r()) })
                }
            }) {
            Image(pic.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.FillBounds)
            shot.tint?.let { Image(it.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.FillBounds) }
            Canvas(Modifier.fillMaxSize()) {
                val s = size.width / pic.width
                shot.markerFractions.forEach { drawQuad(it, size.width, size.height, C.yellow, 2.5.dp.toPx()) }
                shot.outline?.takeIf { it.size >= 6 }?.let { o ->
                    val path = Path().apply { moveTo(o[0] * size.width, o[1] * size.height); var i = 2; while (i + 1 < o.size) { lineTo(o[i] * size.width, o[i + 1] * size.height); i += 2 }; close() }
                    drawPath(path, C.brand, style = Stroke(2.5f * density))
                }
                shot.result?.corners?.let { drawBox(it, size.width, size.height) }
                (drag ?: shot.box?.toFloatArray())?.takeIf { shot.mask == null || drag != null }?.let { r ->
                    drawRect(Color.White, Offset(r[0] * s, r[1] * s), Size((r[2] - r[0]) * s, (r[3] - r[1]) * s), style = Stroke(3.dp.toPx()))
                }
                shot.tap?.takeIf { shot.result == null }?.let { p ->
                    drawCircle(Color.White, 9.dp.toPx(), Offset(p[0] * s, p[1] * s)); drawCircle(C.brand, 6.dp.toPx(), Offset(p[0] * s, p[1] * s))
                }
            }
            Row(Modifier.align(Alignment.TopStart).padding(8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Chip("Foto ${shot.index + 1} · ${shot.downDeg.toInt()}°", Tone.GREY, "photo_camera")
                if (shot.markers.isNotEmpty()) Chip("Marker ${shot.markers.joinToString("+") { MarkerSheet.of(it.id)?.label ?: "?" }}", Tone.ACCENT, "qr_code_2")
                if (!shot.still) Chip("HP bergoyang", Tone.WARN, "warning")
            }
        }
    }
}

/** The angle is right (30–60° is best; 25–72° is accepted) and the phone is held still. */
private fun ready(live: PhotoCamera.Live?) = live?.downDeg?.let { it in 25f..72f } == true && live.still

/**
 * The three things a good photo needs, as checks that turn green, and the one thing to do next: the angle, a still phone,
 * the marker in view and big enough. The marker is not required (the photo works without it) but is asked for.
 */
@Composable
private fun Readiness(live: PhotoCamera.Live?, marker: LiveMarkerState?, modifier: Modifier) {
    val d = live?.downDeg
    val angleOk = d != null && d in 25f..72f
    val still = live?.still == true
    val mk = marker != null && marker.big
    val msg = when {
        d == null -> "Arahkan kamera ke paket"
        d < 25f -> "Miringkan HP ke bawah: sekarang ${d.toInt()}°, pas 30–60°"
        d > 72f -> "Terlalu tegak dari atas: mundur sedikit, miring 30–60°"
        marker == null -> "Marker belum terlihat: taruh rata di sebelah paket"
        !marker.big -> "Marker terlalu kecil: dekatkan HP atau pakai A3"
        !still -> "Tahan HP diam sebentar"
        else -> "Siap · lingkaran tengah di paket, tekan Ambil foto"
    }
    val all = angleOk && still && mk
    Column(modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(if (all) C.greenL else Color.White)
        .border(1.dp, if (all) C.green.copy(alpha = 0.5f) else C.line, RoundedCornerShape(14.dp)).padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(7.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            ReadyCheck(if (d != null) "Sudut ${d.toInt()}°" else "Sudut", angleOk)
            ReadyCheck("HP diam", still)
            ReadyCheck(if (marker?.id != null) "Marker ${MarkerSheet.of(marker.id)?.label ?: ""}" else "Marker", mk)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Sym(if (all) "check_circle" else "info", 18.dp, if (all) C.green else C.brand, filled = true)
            T(msg, 13.sp, FontWeight.SemiBold, if (all) C.green else C.ink, modifier = Modifier.padding(start = 6.dp))
        }
    }
}

@Composable
private fun ReadyCheck(text: String, ok: Boolean) {
    Row(Modifier.clip(RoundedCornerShape(50)).background(if (ok) Color.White else Color(0xFFEEF1F5)).border(1.dp, if (ok) C.green else Color.Transparent, RoundedCornerShape(50))
        .padding(horizontal = 8.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Sym(if (ok) "check_circle" else "radio_button_unchecked", 15.dp, if (ok) C.green else C.t3, filled = ok)
        T(text, 12.sp, FontWeight.SemiBold, if (ok) C.green else C.t2, maxLines = 1)
    }
}

/** What the phone is doing with the photo: read it, cut the parcel out, compute the size; done steps ticked. */
@Composable
private fun ProcessSteps(stage: String, picked: Boolean) {
    val idx = when (stage) { "Membaca foto…" -> 0; "Memotong paket…" -> 1; else -> 2 }
    val t = loopClock(1000, still = 1f)
    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(Color.White).border(1.dp, C.line, RoundedCornerShape(14.dp)).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            listOf("Baca foto", "Potong paket", "Hitung ukuran").forEachIndexed { i, label ->
                val done = i < idx; val on = i == idx
                Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(22.dp).clip(CircleShape).background(when { done -> C.green; on -> C.brand.copy(alpha = 0.55f + 0.45f * t); else -> C.line }),
                        contentAlignment = Alignment.Center) {
                        if (done) Sym("check", 15.dp, Color.White) else T("${i + 1}", 11.sp, FontWeight.Bold, if (on) Color.White else C.t3)
                    }
                    T(label, 12.sp, if (on) FontWeight.SemiBold else FontWeight.Normal, if (on) C.brandD else if (done) C.ink else C.t3,
                        modifier = Modifier.padding(start = 5.dp), maxLines = 1)
                }
            }
        }
        if (LocalStill.current) LinearProgressIndicator(progress = { (idx + 0.5f) / 3f }, modifier = Modifier.fillMaxWidth(), color = C.brand, trackColor = C.brandL,
            gapSize = 0.dp, drawStopIndicator = {})
        else LinearProgressIndicator(modifier = Modifier.fillMaxWidth(), color = C.brand, trackColor = C.brandL)
        if (idx == 0 && !picked) Row(verticalAlignment = Alignment.CenterVertically) {
            Sym("touch_app", 18.dp, C.brand, filled = true)
            T("Sambil menunggu, ketuk paketnya di foto.", 13.sp, FontWeight.SemiBold, C.brandD, modifier = Modifier.padding(start = 6.dp))
        }
    }
}

/** A quadrilateral given as fractions (x, y × 4). */
fun DrawScope.drawQuad(q: List<Float>, w: Float, h: Float, color: Color, width: Float) {
    if (q.size < 8) return
    val p = Path().apply { moveTo(q[0] * w, q[1] * h); for (i in 1 until 4) lineTo(q[2 * i] * w, q[2 * i + 1] * h); close() }
    drawPath(p, color, style = Stroke(width, join = StrokeJoin.Round))
}

private fun DrawScope.drawBox(c: List<Float>, w: Float, h: Float) {
    if (c.size != 16) return
    fun p(i: Int) = Offset(c[2 * i] * w, c[2 * i + 1] * h)
    for ((a, e) in PhotoFiles.EDGES) if (PhotoFiles.drawable(c, a) && PhotoFiles.drawable(c, e)) drawLine(Color(0xFF3CDC3C), p(a), p(e), strokeWidth = 2.5f * density)
}

/** The photos taken so far, the one shown outlined; the last tile takes another. */
@Composable
private fun ShotStrip(shots: List<PhotoShotUi>, current: Int?, onOpen: (Int) -> Unit, onAdd: (() -> Unit)?) {
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        shots.forEach { s ->
            Column(Modifier.width(66.dp).clip(RoundedCornerShape(10.dp)).border(if (s.index == current) 2.dp else 1.dp, if (s.index == current) C.brand else C.line, RoundedCornerShape(10.dp))
                .background(Color.White).clickable { onOpen(s.index) }.padding(3.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Image(s.picture.asImageBitmap(), null, Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(7.dp)), contentScale = ContentScale.Crop)
                T(s.result?.let { "${it.lengthCm.cm()}×${it.widthCm.cm()}×${it.heightCm.cm()}" } ?: if (s.error != null) "gagal" else "…",
                    10.sp, FontWeight.SemiBold, if (s.error != null) C.red else C.t2, maxLines = 1)
            }
        }
        if (onAdd != null) Column(Modifier.width(66.dp).aspectRatio(0.62f).clip(RoundedCornerShape(10.dp)).border(1.dp, C.line, RoundedCornerShape(10.dp))
            .background(C.brandL).clickable { onAdd() }, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
            Sym("add", 26.dp, C.brand); T("Foto lagi", 11.sp, FontWeight.SemiBold, C.brandD)
        }
    }
}

/** The size from every photo so far: P × L × T, volumetric weight, volume, where the scale came from, and the notes. */
@Composable
internal fun ResultCard(r: PhotoResult, each: List<PhotoResult>, divisor: Int, scaleSource: String?) {
    val volL = r.lengthCm * r.widthCm * r.heightCm / 1000
    val volKg = r.lengthCm * r.widthCm * r.heightCm / divisor
    Card(highlight = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            T("Ukuran", 15.sp, FontWeight.SemiBold, modifier = Modifier.weight(1f))
            when {
                r.blurred() -> Chip("Foto buram · ulangi", Tone.RED, "error")
                r.ok -> Chip("Akurat · skor ${r.confidence}", Tone.OK, "check_circle")
                else -> Chip("Perlu Dicek · skor ${r.confidence}", Tone.WARN, "warning")
            }
        }
        if (r.blurred()) {
            T("Jarak belum terbaca", 26.sp, FontWeight.Bold, C.red)
            T("Perkiraan AI saja: ${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm (tidak dipakai)", 13.sp, color = C.t2)
        } else T("${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm", 28.sp, FontWeight.Bold)
        if (!r.blurred()) Row(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Column(Modifier.weight(1f).clip(RoundedCornerShape(10.dp)).background(C.brandL).padding(10.dp)) {
                T("Berat volumetrik", 12.sp, color = C.brandD)
                T("${volKg.id(2)} kg", 22.sp, FontWeight.Bold, C.brandD)
                T("P × L × T ÷ ${divisor.toDouble().id(0)}", 11.sp, color = C.brandD)
            }
            Column(Modifier.weight(1f).clip(RoundedCornerShape(10.dp)).background(C.line).padding(10.dp)) {
                T("Volume", 12.sp, color = C.t2)
                T("${volL.id()} L", 22.sp, FontWeight.Bold)
                T("${(volL / 1000).id(3)} m³", 11.sp, color = C.t2)
            }
        }
        Spacer(Modifier.height(8.dp))
        // where the scale came from: the marker (a measurement) or the AI (an estimate)
        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(if (r.markerUsed()) C.yellowL else Color(0xFFEEF1F5)).padding(10.dp),
            verticalAlignment = Alignment.CenterVertically) {
            if (r.markerUsed()) MarkerGlyph(22.dp) else Sym("info", 20.dp, C.t2)
            Column(Modifier.padding(start = 10.dp)) {
                T("Skala: ${scaleSource ?: "-"}", 13.sp, FontWeight.SemiBold, if (r.markerUsed()) C.onYellow else C.ink)
                T("kamera ${r.cameraHeightM.id(2)} m di atas lantai" + (if (r.markerUsed()) " · ketelitian ±${(r.markerSigma * 100).id(1)}%" else "") +
                    " · sudut ${r.downDeg.toInt()}° · cocok siluet ${(r.iou * 100).toInt()}%", 12.sp, color = if (r.markerUsed()) C.onYellow else C.t2)
            }
        }
        if (each.size > 1) {
            Spacer(Modifier.height(6.dp))
            each.forEachIndexed { i, e -> T("Foto ${i + 1}: ${e.lengthCm.cm()} × ${e.widthCm.cm()} × ${e.heightCm.cm()} cm" + (if (e.markerUsed()) " · marker" else "") +
                if (!e.boxLike) " · bukan kotak" else "", 12.5.sp, color = C.t2) }
        }
        if (r.notes.isNotEmpty()) Spacer(Modifier.height(6.dp))
        r.notes.forEach { T("• " + courierNote(it), 12.sp, color = C.amber) }
        if (!r.markerUsed()) T("Untuk hasil paling tepat, taruh marker A4/A3 di sebelah paket lalu foto ulang.", 12.sp, FontWeight.SemiBold, C.brandD,
            modifier = Modifier.padding(top = 4.dp))
    }
}

/** The engine's notes in UkurAja's words: here the scale is learnt from marker photos, not a tape calibration. */
fun courierNote(n: String): String =
    if (n.startsWith("Mode foto belum dikalibrasi")) "Belum ada foto marker di HP ini: skala hanya dari tebakan AI, angka bisa meleset jauh" else n

@Composable
fun Banner(text: String, bg: Color, fg: Color, icon: String) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(bg).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Sym(icon, 20.dp, fg, filled = true)
        T(text, 13.5.sp, FontWeight.Medium, fg, modifier = Modifier.padding(start = 10.dp))
    }
}

/** Why the parcel goes to the hub instead: the common reasons, one tap. */
@Composable
private fun HubDialog(onDismiss: () -> Unit, onPick: (String) -> Unit) {
    val reasons = listOf("Paket terlalu besar untuk difoto", "Bentuk tidak beraturan / lunak", "Plastik mengkilap, tidak terbaca", "Tempat terlalu gelap atau sempit", "Lainnya")
    AlertDialog(onDismissRequest = onDismiss,
        title = { T("Tandai Ukur di Hub", 18.sp, FontWeight.SemiBold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                T("Paket disimpan tanpa ukuran, dengan foto, waktu, dan lokasi. Hub yang mengukur.", 13.sp, color = C.t2)
                reasons.forEach { r ->
                    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).border(1.dp, C.line, RoundedCornerShape(10.dp)).clickable { onPick(r) }.padding(12.dp)) {
                        T(r, 14.sp, FontWeight.Medium)
                    }
                }
            }
        },
        confirmButton = {}, dismissButton = { TextButton(onClick = onDismiss) { T("Batal", color = C.t2) } })
}
