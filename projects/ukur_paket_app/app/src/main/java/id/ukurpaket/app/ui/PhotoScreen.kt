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
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
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
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
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
import id.ukurpaket.app.data.cm
import id.ukurpaket.app.data.id
import id.ukurpaket.app.dt.ObjectPick
import id.ukurpaket.app.photo.CalSample
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.DepthModel
import id.ukurpaket.app.photo.PhotoCamera
import id.ukurpaket.app.photo.PhotoFiles
import id.ukurpaket.app.photo.PhotoResult
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/** The photo mode: camera -> photo -> tap the parcel -> size (and more photos, a test, or the calibration). */
@Composable
fun PhotoScreen(model: AppModel, activity: Activity) {
    CameraPermission(model, activity) { PhotoContent(model, activity) }
}

private fun PhotoPurpose.title() = when (this) {
    PhotoPurpose.PARCEL -> "Ukur dengan foto"
    PhotoPurpose.TEST -> "Uji mode foto"
    PhotoPurpose.CALIBRATE -> "Kalibrasi mode foto"
}

@Composable
private fun PhotoContent(model: AppModel, activity: Activity) {
    val f = model.photo
    val shot = f.shots.firstOrNull { it.index == f.current }
    val subtitle = (if (f.purpose == PhotoPurpose.PARCEL) model.draft?.resi?.let { "Resi $it · " } else null).orEmpty() +
        if (f.shots.isEmpty()) "foto dari pojok paket" else "${f.shots.size} foto"
    if (shot == null) LiveCamera(model, f, subtitle)
    else PhotoShotChrome(model, f, shot, subtitle, activity)
}

// ------------------------------------------------------------------ camera
@Composable
private fun LiveCamera(model: AppModel, f: PhotoFlow, subtitle: String) {
    val ctx = LocalContext.current
    val main = remember { Handler(Looper.getMainLooper()) }
    var live by remember { mutableStateOf<PhotoCamera.Live?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    val cam = remember {
        PhotoCamera(ctx, object : PhotoCamera.Callback {
            override fun onLive(s: PhotoCamera.Live) { main.post { live = s } }
            override fun onError(msg: String) { main.post { error = msg; f.capturing = false } }
        })
    }
    DisposableEffect(Unit) { onDispose { cam.close() } }
    PhotoCameraChrome(f.purpose.title(), subtitle, live, f.capturing, error, f.shots,
        onBack = { model.back() },
        onShutter = {
            if (!f.capturing && error == null) {
                f.capturing = true
                cam.capture { s -> main.post { f.onShot(s) } }
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
internal fun PhotoCameraChrome(title: String, subtitle: String, live: PhotoCamera.Live?, capturing: Boolean, error: String?,
                               shots: List<PhotoShotUi>, onBack: () -> Unit, onShutter: () -> Unit, onOpen: (Int) -> Unit,
                               preview: @Composable () -> Unit) {
    Column(Modifier.fillMaxSize()) {
        TopBar(title, subtitle, onBack = onBack)
        BoxWithConstraints(Modifier.weight(1f).fillMaxWidth().background(Color.Black), contentAlignment = Alignment.Center) {
            val pw = min(maxWidth.value, maxHeight.value * 3f / 4f).dp
            Box(Modifier.size(pw, (pw.value * 4f / 3f).dp)) {
                preview()
                // a light guide: the parcel in the middle, whole, with floor round it; the centre mark is where the
                // autofocus measures the distance (best on the parcel)
                Canvas(Modifier.fillMaxSize()) {
                    val cx = size.width / 2; val cy = size.height / 2; val r = size.width * 0.035f
                    drawCircle(Color.White.copy(alpha = 0.8f), r, Offset(cx, cy), style = Stroke(2.dp.toPx()))
                    drawLine(Color.White.copy(alpha = 0.8f), Offset(cx - 2 * r, cy), Offset(cx - r, cy), 2.dp.toPx())
                    drawLine(Color.White.copy(alpha = 0.8f), Offset(cx + r, cy), Offset(cx + 2 * r, cy), 2.dp.toPx())
                    drawLine(Color.White.copy(alpha = 0.8f), Offset(cx, cy - 2 * r), Offset(cx, cy - r), 2.dp.toPx())
                    drawLine(Color.White.copy(alpha = 0.8f), Offset(cx, cy + r), Offset(cx, cy + 2 * r), 2.dp.toPx())
                    val m = size.width * 0.12f
                    val c = Color.White.copy(alpha = 0.55f); val l = size.width * 0.07f; val sw = 2.5.dp.toPx()
                    for ((x, y, dx, dy) in listOf(listOf(m, m * 1.4f, 1f, 1f), listOf(size.width - m, m * 1.4f, -1f, 1f),
                            listOf(m, size.height - m * 1.4f, 1f, -1f), listOf(size.width - m, size.height - m * 1.4f, -1f, -1f))) {
                        drawLine(c, Offset(x, y), Offset(x + dx * l, y), sw); drawLine(c, Offset(x, y), Offset(x, y + dy * l), sw)
                    }
                }
                Column(Modifier.align(Alignment.TopStart).padding(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        val d = live?.downDeg
                        when {
                            d == null -> Chip("Sudut …", Tone.GREY, "3d_rotation")
                            d < 25f -> Chip("Sudut ${d.toInt()}° · miringkan ke bawah", Tone.WARN, "3d_rotation")
                            d > 72f -> Chip("Sudut ${d.toInt()}° · sedikit dari samping", Tone.WARN, "3d_rotation")
                            else -> Chip("Sudut ${d.toInt()}° pas", Tone.OK, "3d_rotation")
                        }
                        if (live != null) Chip(if (live.still) "HP diam" else "Tahan diam", if (live.still) Tone.OK else Tone.GREY, if (live.still) "check" else "timer")
                    }
                    if ((live?.brightness ?: 128.0) < 55) Chip("Terlalu gelap: tambah cahaya", Tone.RED, "light_mode")
                }
                Box(Modifier.align(Alignment.BottomCenter).padding(10.dp).clip(RoundedCornerShape(12.dp)).background(C.glass).padding(horizontal = 12.dp, vertical = 8.dp)) {
                    T("Lingkaran tengah tepat di paket · berdiri di pojok paket, HP setinggi dada · miring 30–60° ke bawah · paket utuh, lantai kelihatan", 12.5.sp, color = Color.White)
                }
            }
        }
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (error != null) Banner(error, C.redL, C.red, "error")
            if (shots.isNotEmpty()) ShotStrip(shots, null, onOpen, onAdd = null)
            PrimaryButton(if (capturing) "Tahan diam, mengukur jarak…" else "Ambil foto", if (capturing) "timer" else "photo_camera", Modifier.fillMaxWidth(),
                enabled = !capturing && error == null) { onShutter() }
            if (shots.isNotEmpty()) SecondaryButton("Kembali ke hasil", "arrow_back", Modifier.fillMaxWidth()) { onOpen(shots.last().index) }
        }
    }
}

// ------------------------------------------------------------------ one photo: pick and result
@Composable
private fun PhotoShotChrome(model: AppModel, f: PhotoFlow, shot: PhotoShotUi, subtitle: String, activity: Activity) {
    val settings by model.store.settings.collectAsState()
    val samples = Calibration.current(settings.photoCal)
    var mismatch by remember { mutableStateOf<CalSample?>(null) }
    fun save(force: Boolean) = when (f.saveCalibration(force)) {
        PhotoFlow.CalSave.SAVED -> model.back()
        PhotoFlow.CalSave.MISMATCH -> mismatch = f.pendingSample()
        PhotoFlow.CalSave.INCOMPLETE -> model.toast("Isi P × L × T meteran dulu")
    }
    PhotoShotView(f.purpose, shot, f.shots, f.combined, subtitle, settings.divisor, f.calibrated,
        Calibration.factor(samples), samples.size, f.tape,
        isParcel = model.draft != null && f.purpose == PhotoPurpose.PARCEL,
        onBack = { model.back() },
        onPick = { t, b -> f.pick(shot.index, t, b) },
        onOpen = { f.current = it },
        onAdd = { f.current = null },
        onRetake = { f.remove(shot.index); f.current = null },
        onTape = { f.tape = it },
        onUse = { f.use() },
        onSaveCal = { save(force = false) },
        onShare = {
            f.saveTape()
            val d = f.dir
            if (d != null) model.shareFile(activity, "application/zip", "Bagikan data mode foto") { model.zip(listOf(d), "foto_${d.name}.zip") }
        })
    mismatch?.let { s ->
        val r = s.ratios()
        AlertDialog(onDismissRequest = { mismatch = null },
            title = { T("Bentuk terbaca beda dengan meteran", 18.sp, FontWeight.SemiBold) },
            text = { T("Meteran ÷ terbaca: " + listOf("P", "L", "T").zip(r).joinToString(" · ") { (l, v) -> "$l ×${v.id(2)}" } +
                ". Kalau fotonya benar, ketiganya hampir sama. Beda sejauh ini artinya foto ini salah membaca bentuk kardus, " +
                "jadi faktornya ikut salah. Lebih baik foto ulang: kardus utuh di foto, dari pojoknya, agak dari atas.", color = C.t2) },
            confirmButton = { TextButton(onClick = { mismatch = null; f.remove(shot.index); f.current = null }) { T("Foto ulang", weight = FontWeight.SemiBold, color = C.brandD) } },
            dismissButton = { TextButton(onClick = { mismatch = null; save(force = true) }) { T("Simpan tetap", color = C.t2) } })
    }
}

internal enum class PhotoPick { TAP, BOX }

@Composable
internal fun PhotoShotView(
    purpose: PhotoPurpose, shot: PhotoShotUi, shots: List<PhotoShotUi>, combined: PhotoResult?, subtitle: String, divisor: Int,
    calibrated: Boolean, factor: Double?, samples: Int, tape: List<String>, isParcel: Boolean,
    onBack: () -> Unit, onPick: (List<Float>?, List<Float>?) -> Unit, onOpen: (Int) -> Unit, onAdd: () -> Unit, onRetake: () -> Unit,
    onTape: (List<String>) -> Unit, onUse: () -> Unit, onSaveCal: () -> Unit, onShare: () -> Unit,
) {
    var mode by remember { mutableStateOf(if (shot.box != null) PhotoPick.BOX else PhotoPick.TAP) }
    var drag by remember(shot.index) { mutableStateOf<FloatArray?>(null) }
    val busy = shot.stage != null && shot.stage != "Membaca foto…"
    Column(Modifier.fillMaxSize()) {
        TopBar(purpose.title(), subtitle, onBack = onBack)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            // with a size, the size comes first (a small screen shows it without scrolling) and the photo below it
            if (combined != null) PhotoResultCard(purpose, combined, shots.mapNotNull { it.result }, divisor, calibrated, factor, samples)
            // the tape size right under it: the calibration's ratios and the test's error show without scrolling
            if (purpose != PhotoPurpose.PARCEL && combined != null) TapeCard(purpose, tape, combined, onTape)
            Box(Modifier.fillMaxWidth().heightIn(max = if (combined != null) 300.dp else 2000.dp), contentAlignment = Alignment.Center) {
                ShotImage(shot, mode, drag, enabled = !busy,
                    onTap = { x, y -> drag = null; onPick(listOf(x, y), null) },
                    onDrag = { drag = it },
                    onBox = { r -> drag = null; if (abs(r[2] - r[0]) > 12 && abs(r[3] - r[1]) > 12) onPick(null, r.toList()) })
            }
            // what happens now, or what to do
            when {
                shot.stage != null -> Row(verticalAlignment = Alignment.CenterVertically) {
                    if (LocalStill.current) Sym("sync", 18.dp, C.brand) else CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = C.brand)
                    T(shot.stage + if (shot.stage == "Membaca foto…" && shot.mask == null) " Sambil menunggu, ketuk paketnya." else "",
                        13.5.sp, FontWeight.SemiBold, C.brandD, modifier = Modifier.padding(start = 10.dp))
                }
                shot.error != null -> Banner(shot.error, C.redL, C.red, "error")
                shot.mask == null -> T(if (mode == PhotoPick.TAP) "Ketuk paketnya di foto." else "Tarik kotak di sekeliling paket.", 14.sp, FontWeight.SemiBold)
                shot.result != null -> T("Kotak hijau = ukuran terbaca. Salah pilih? Ketuk paketnya lagi.", 12.5.sp, color = C.t3)
            }
            if (shot.result == null || shot.error != null) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Chip("Klik paket", if (mode == PhotoPick.TAP) Tone.BRAND else Tone.GREY, "touch_app") { mode = PhotoPick.TAP }
                Chip("Tarik kotak", if (mode == PhotoPick.BOX) Tone.BRAND else Tone.GREY, "highlight_alt") { mode = PhotoPick.BOX }
            }
            if (shots.size > 1 || combined != null) ShotStrip(shots, shot.index, onOpen, onAdd)
            if (purpose != PhotoPurpose.PARCEL && combined == null) TapeCard(purpose, tape, null, onTape)
            Spacer(Modifier.height(2.dp))
        }
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            when {
                purpose == PhotoPurpose.CALIBRATE && combined != null -> {
                    val ok = tape.all { ObjectPick.cm(it) != null }
                    PrimaryButton("Simpan kalibrasi", "tune", Modifier.fillMaxWidth(), enabled = ok) { onSaveCal() }
                }
                // a size from blurred photos only is not used for a parcel: its distance is not known
                isParcel && combined != null -> PrimaryButton(if (combined.blurred()) "Foto buram: ulangi foto" else "Pakai ukuran ini",
                    if (combined.blurred()) "refresh" else "arrow_forward", Modifier.fillMaxWidth()) { if (combined.blurred()) onRetake() else onUse() }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                val three = purpose == PhotoPurpose.TEST
                SmallAction(if (three) "Ulangi" else "Ulangi foto", "refresh", Modifier.weight(1f)) { onRetake() }
                SmallAction(if (three) "Tambah" else "Tambah foto", "add", Modifier.weight(1f)) { onAdd() }
                if (three) SmallAction("ZIP", "folder_zip", Modifier.weight(0.8f)) { onShare() }
            }
        }
    }
}

@Composable
private fun SmallAction(text: String, icon: String, modifier: Modifier, onClick: () -> Unit) {
    androidx.compose.material3.OutlinedButton(onClick = onClick, modifier = modifier.height(48.dp), shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.5.dp, C.line), contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 6.dp),
        colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(containerColor = Color.White)) {
        Sym(icon, 20.dp, C.ink); Spacer(Modifier.width(4.dp))
        T(text, 14.sp, FontWeight.SemiBold, C.ink, maxLines = 1)
    }
}

/** The photo with the cut-out, the measured box and the pick; taps and drags come back in picture pixels. */
@Composable
private fun ShotImage(shot: PhotoShotUi, mode: PhotoPick, drag: FloatArray?, enabled: Boolean,
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
            if (mode == PhotoPick.TAP) detectTapGestures { o -> onTap(o.x * k, o.y * k) }
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
            shot.outline?.takeIf { it.size >= 6 }?.let { drawOutlineFr(it, size.width, size.height) }
            shot.result?.corners?.let { drawBoxFr(it, size.width, size.height) }
            (drag ?: shot.box?.toFloatArray())?.takeIf { shot.mask == null || drag != null }?.let { r ->
                drawRect(Color.White, Offset(r[0] * s, r[1] * s), Size((r[2] - r[0]) * s, (r[3] - r[1]) * s), style = Stroke(3.dp.toPx()))
            }
            shot.tap?.takeIf { shot.result == null }?.let { p ->
                drawCircle(Color.White, 9.dp.toPx(), Offset(p[0] * s, p[1] * s)); drawCircle(C.brand, 6.dp.toPx(), Offset(p[0] * s, p[1] * s))
            }
        }
        Row(Modifier.align(Alignment.TopStart).padding(8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Chip("Foto ${shot.index + 1} · ${shot.downDeg.toInt()}°", Tone.GREY, "photo_camera")
            if (!shot.still) Chip("HP bergoyang", Tone.WARN, "warning")
        }
    }
    }
}

private fun DrawScope.drawOutlineFr(o: List<Float>, w: Float, h: Float) {
    val path = Path().apply { moveTo(o[0] * w, o[1] * h); var i = 2; while (i + 1 < o.size) { lineTo(o[i] * w, o[i + 1] * h); i += 2 }; close() }
    drawPath(path, C.brand, style = Stroke(2.5f * density))
}

private fun DrawScope.drawBoxFr(c: List<Float>, w: Float, h: Float) {
    if (c.size != 16) return
    fun p(i: Int) = Offset(c[2 * i] * w, c[2 * i + 1] * h)
    // corners outside the photo still draw (the photo clips the lines); only a corner behind the camera is left out
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

/** The size from every photo so far, as the other methods show it. */
@Composable
internal fun PhotoResultCard(purpose: PhotoPurpose, r: PhotoResult, each: List<PhotoResult>, divisor: Int, calibrated: Boolean, factor: Double?, samples: Int) {
    val volL = r.lengthCm * r.widthCm * r.heightCm / 1000
    val volKg = r.lengthCm * r.widthCm * r.heightCm / divisor
    Card(highlight = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            T(if (purpose == PhotoPurpose.CALIBRATE) "Ukuran terbaca (sebelum kalibrasi)" else "Ukuran", 15.sp, FontWeight.SemiBold, modifier = Modifier.weight(1f))
            when {
                purpose == PhotoPurpose.CALIBRATE -> Chip("Kalibrasi", Tone.BRAND, "tune")
                r.blurred() -> Chip("Foto buram · ulangi", Tone.RED, "error")
                !calibrated -> Chip("Belum dikalibrasi", Tone.WARN, "warning")
                r.ok -> Chip("Akurat · skor ${r.confidence}", Tone.OK, "check_circle")
                else -> Chip("Perlu Dicek · skor ${r.confidence}", Tone.WARN, "warning")
            }
        }
        // without a distance it can stand on (blurred, no focus clue: the depth model alone close up) the size is not
        // headlined: it would read as a measurement
        if (r.blurred()) {
            T("Jarak belum terbaca", 26.sp, FontWeight.Bold, C.red)
            T("Perkiraan AI saja: ${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm (tidak dipakai)", 13.sp, color = C.t2)
        } else T("${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm", 28.sp, FontWeight.Bold)
        if (purpose != PhotoPurpose.CALIBRATE && !r.blurred()) Row(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
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
        Spacer(Modifier.height(6.dp))
        T("${each.size} foto · kamera ${r.cameraHeightM.id(2)} m di atas lantai" +
            listOfNotNull(
                if (r.focusCameraM > 0) (if (r.sweepPoints > 0) "sapuan fokus ${r.focusDistanceM.id(2)} m, ${r.sweepPoints} titik tepi" else "fokus ${r.focusDistanceM.id(2)} m ke paket") else null,
                "AI ${r.aiCameraM.id(2)} m",
                if (r.standingM > 0) "tinggi berdiri ${r.standingM.id(2)} m" else null,
            ).takeIf { it.size > 1 }?.joinToString(", ", " (", ")").orEmpty() +
            " · sudut ${r.downDeg.toInt()}° · cocok siluet ${(r.iou * 100).toInt()}%" +
            if (purpose != PhotoPurpose.CALIBRATE && factor != null) " · kalibrasi ×${factor.id(2)} ($samples sampel)" else "", 12.sp, color = C.t3)
        if (each.size > 1) each.forEachIndexed { i, e ->
            T("Foto ${i + 1}: ${e.lengthCm.cm()} × ${e.widthCm.cm()} × ${e.heightCm.cm()} cm" + if (!e.boxLike) " · bukan kotak" else "", 12.5.sp, color = C.t2)
        }
        // a calibration photo is read before calibration on purpose: its "not calibrated" note says nothing there
        r.notes.filter { purpose != PhotoPurpose.CALIBRATE || !it.startsWith("Mode foto belum dikalibrasi") }.forEach { T("• $it", 12.sp, color = C.amber) }
        if (!calibrated && purpose != PhotoPurpose.CALIBRATE)
            T("Kalibrasi sekali di Pengaturan → Kalibrasi mode foto, dengan kardus yang sudah diukur meteran.", 12.sp, FontWeight.SemiBold, C.brandD)
    }
}

/** The tape-measure size: compared with the result in a test, or the truth of a calibration photo. */
@Composable
private fun TapeCard(purpose: PhotoPurpose, tape: List<String>, r: PhotoResult?, onTape: (List<String>) -> Unit) {
    Card {
        T(if (purpose == PhotoPurpose.CALIBRATE) "Ukuran meteran kardus ini" else "Data uji", 15.sp, FontWeight.SemiBold)
        T(if (purpose == PhotoPurpose.CALIBRATE) "Ukur kardus dengan meteran, isi P × L × T, lalu Simpan kalibrasi. Ulangi dengan 3 kardus berbeda ukuran supaya angkanya stabil; " +
            "satu di antaranya kardus kecil difoto dekat (30–60 cm) untuk melatih fokus kamera."
          else "Isi ukuran meteran (boleh kosong) untuk melihat selisihnya. ZIP berisi foto, mask, dan depth untuk dianalisis di PC.", 12.5.sp, color = C.t2)
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("P", "L", "T").forEachIndexed { i, l ->
                OutlinedTextField(tape[i], { v -> onTape(tape.toMutableList().also { it[i] = v.filter { c -> c.isDigit() || c == ',' || c == '.' }.take(6) }) },
                    singleLine = true, modifier = Modifier.weight(1f), label = { T("$l (cm)", 13.sp) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal))
            }
        }
        val t = tape.map { ObjectPick.cm(it) }
        if (r != null && t.all { it != null } && purpose == PhotoPurpose.TEST) {
            val tt = t.map { it!! }.let { listOf(maxOf(it[0], it[1]), minOf(it[0], it[1]), it[2]) }
            val e = listOf(r.lengthCm - tt[0], r.widthCm - tt[1], r.heightCm - tt[2])
            Spacer(Modifier.height(6.dp))
            T("Selisih " + e.joinToString(" / ") { (if (it >= 0) "+" else "") + it.id() } + " cm · " +
                e.indices.joinToString(" / ") { i -> (if (e[i] >= 0) "+" else "") + (e[i] / tt[i] * 100).id(0) + "%" }, 12.5.sp, FontWeight.SemiBold, C.brandD)
        }
        if (purpose == PhotoPurpose.CALIBRATE && r != null && t.all { it != null }) {
            // what this box's calibration would be: the three sides' tape / measured ratios, alike when the photo read it right
            val sample = CalSample(r.rawCm, t.map { it!! }, model = DepthModel.ID)
            val ratios = sample.ratios()
            val bad = Calibration.mismatch(sample) > Calibration.MISMATCH
            Spacer(Modifier.height(6.dp))
            T("Meteran ÷ terbaca: " + listOf("P", "L", "T").zip(ratios).joinToString(" · ") { (l, v) -> "$l ×${v.id(2)}" } +
                (Calibration.factor(listOf(sample))?.let { " → faktor ×${it.id(2)}" } ?: ""), 12.5.sp, FontWeight.SemiBold, if (bad) C.amber else C.brandD)
            // a figure the courier can check by eye: about chest height when standing
            CalSample(r.rawCm, t.map { it!! }, aiCameraM = r.aiCameraM).cameraM()?.let {
                T("Berarti kamera ${it.id(2)} m di atas lantai saat foto (AI menebak ${r.aiCameraM.id(2)} m).", 12.5.sp, color = C.t2)
            }
            Calibration.focusFactor(r, t.map { it!! })?.let { T("Fokus kamera: faktor ×${it.id(2)} dari foto ini.", 12.5.sp, color = C.t2) }
            if (bad) T("Ketiga angka beda jauh: foto ini salah membaca bentuk kardus. Foto ulang dari pojok kardus (kardus utuh, agak dari atas) " +
                "supaya faktornya benar. Tetap bisa disimpan.", 12.5.sp, color = C.amber)
        }
    }
}

/** Settings card: the photo mode's calibration on this phone, and its saved photos. */
@Composable
fun PhotoSettingsCard(model: AppModel, activity: Activity) {
    val s by model.store.settings.collectAsState()
    var tick by remember { mutableStateOf(0) }
    val dirs = remember(tick) { model.store.photoSessionsDir.listFiles()?.filter { it.isDirectory }.orEmpty() }
    val cal = Calibration.current(s.photoCal)
    val f = Calibration.factor(cal)
    Card {
        T("Kalibrasi mode foto", 15.sp, FontWeight.SemiBold)
        T("Mode foto menebak tinggi kamera dari lantai dengan AI; kalibrasi sekali per HP memperbaiki skalanya dan mencatat tinggi kamera Anda saat berdiri. Foto 3 kardus yang sudah diukur meteran, sambil berdiri, HP setinggi dada.",
            12.5.sp, color = C.t2)
        Spacer(Modifier.height(8.dp))
        if (f == null) {
            Chip("Belum dikalibrasi · faktor bawaan ×${DepthModel.DEFAULT_SCALE.toDouble().id(2)}", Tone.WARN, "warning")
            if (s.photoCal.isNotEmpty()) T("${s.photoCal.size} sampel lama dibuat dengan model AI sebelumnya dan tidak dipakai lagi: kalibrasi ulang.", 12.sp, color = C.amber)
        } else {
            val sp = Calibration.spread(cal)
            Chip("Faktor ×${f.id(2)} · ${cal.size} kardus · sebaran ${(sp * 100).toInt()}%", if (sp > 0.15 || cal.size < 3) Tone.WARN else Tone.OK, "tune")
            if (cal.size < 3) T("Tambah sampai 3 kardus supaya faktornya stabil.", 12.sp, color = C.t3)
            Calibration.focus(cal, null)?.let { fc ->
                T("Fokus kamera: faktor ×${fc.factor.id(2)} (${fc.samples} foto dekat). Benda yang difoto dekat diukur dari jarak fokus.", 12.sp, color = C.t2)
            }
            Calibration.standing(cal)?.let { st ->
                T("Tinggi kamera saat berdiri: ${st.heightM.id(2)} m (${st.samples} foto, sebaran ${(st.spread * 100).toInt()}%). Dipakai bersama AI: foto paket sambil berdiri seperti saat kalibrasi.",
                    12.sp, color = C.t2)
            }
            if (sp > 0.15) T("Sampel tidak konsisten: hapus kalibrasi dan ulangi dengan foto dari pojok kardus.", 12.sp, color = C.amber)
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton("Kalibrasi", "tune", Modifier.weight(1f)) { model.startPhoto(PhotoPurpose.CALIBRATE) }
            SecondaryButton("Uji foto", "photo_camera", Modifier.weight(1f)) { model.startPhoto(PhotoPurpose.TEST) }
        }
        if (s.photoCal.isNotEmpty()) androidx.compose.material3.TextButton(onClick = { model.store.update { it.copy(photoCal = emptyList()) } }) {
            T("Hapus kalibrasi", 13.sp, color = C.red)
        }
        T("${dirs.size} pengukuran foto tersimpan", 12.5.sp, color = C.t3)
        if (dirs.isNotEmpty()) {
            Spacer(Modifier.height(6.dp))
            SecondaryButton("Bagikan data mode foto (ZIP)", "folder_zip", Modifier.fillMaxWidth()) {
                model.shareFile(activity, "application/zip", "Bagikan data mode foto") { model.zip(dirs, "foto_semua.zip") }
            }
            androidx.compose.material3.TextButton(onClick = { dirs.forEach { it.deleteRecursively() }; tick++ }) { T("Hapus data mode foto", 13.sp, color = C.red) }
        }
    }
}

/** For the screenshot test: a picture as a photo, with an optional mask and result. */
internal fun previewShot(picture: Bitmap, result: PhotoResult? = null, stage: String? = null, tint: Bitmap? = null, outline: List<Float>? = null) =
    PhotoShotUi(0, picture, id.ukurpaket.app.photo.Intrinsics(420f, 420f, 240f, 320f, 480, 640), id.ukurpaket.app.measure.V3(0f, -0.7f, -0.7f), 46f, true,
        stage = stage, ready = stage == null, tint = tint, outline = outline, result = result, mask = if (result != null || tint != null) id.ukurpaket.app.measure.Mask(1, 1, BooleanArray(1) { true }) else null)
