package id.ukurpaket.app.ui

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.media.ExifInterface
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas as ComposeCanvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
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
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import id.ukurpaket.app.ar.ResultData
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.data.cm
import id.ukurpaket.app.measure.Embedding
import id.ukurpaket.app.measure.FloorCamera
import id.ukurpaket.app.measure.MarkerDetector
import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.SingleView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

enum class MStep { TAKE, FINDING, NO_SHEET, PICK, SELECTING, RESULT }

/** What marker mode shows. Kept apart from the work so the screenshots can set it directly. */
data class MarkerUi(
    val step: MStep = MStep.TAKE,
    val photo: ImageBitmap? = null,
    val iw: Int = 1, val ih: Int = 1,
    /** The ring's 8 corners in photo pixels. */
    val sheet: List<P2>? = null,
    /** The picked parcel's outline in photo pixels. */
    val outline: List<P2>? = null,
    /** The 3D box: 8 corners in photo pixels, floor 0-3 then top 4-7. */
    val box: FloatArray? = null,
    val result: ResultData? = null,
    val attempts: Int = 0,
    val message: String? = null,
)

interface MarkerActions {
    fun back(); fun take(); fun sheet()
    fun tap(x: Float, y: Float); fun box(x0: Float, y0: Float, x1: Float, y1: Float)
    fun repeat(); fun retake(); fun save(r: ResultData); fun hub(reason: String)
}

/**
 * Marker mode, for phones without ARCore: one photo of the parcel next to the printed sheet. The sheet gives
 * floor, scale and camera; the courier taps the parcel (or draws a box) and MobileSAM cuts it out; SingleView
 * turns the outline into L x W x H.
 */
@Composable
fun MarkerScreen(model: AppModel, activity: Activity) {
    CameraPermission(model, activity) { MarkerFlow(model, activity) }
}

@Composable
private fun MarkerFlow(model: AppModel, activity: Activity) {
    val scope = rememberCoroutineScope()
    val flow = remember { MarkerWork(model, scope) }
    val target = remember { File(model.store.photosDir, "foto_${System.currentTimeMillis()}.jpg") }
    val uri = remember { FileProvider.getUriForFile(activity, "${activity.packageName}.files", target) }
    val take = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok -> if (ok) flow.process(target) }
    MarkerChrome(flow.ui, model, object : MarkerActions {
        override fun back() = model.back()
        override fun take() = take.launch(uri)
        override fun sheet() = model.markerSheet(activity)
        override fun tap(x: Float, y: Float) = flow.pick(floatArrayOf(x, y))
        override fun box(x0: Float, y0: Float, x1: Float, y1: Float) = flow.pick(floatArrayOf(x0, y0, x1, y1))
        override fun repeat() = flow.repeat()
        override fun retake() { flow.ui = MarkerUi(attempts = flow.ui.attempts + 1); take.launch(uri) }
        override fun save(r: ResultData) = model.onMeasured(r)
        override fun hub(reason: String) = model.markHub(reason, target.takeIf { it.exists() }?.path)
    })
}

/** The work behind the screen: decode, find the sheet, cut out the parcel, measure, draw the evidence photo. */
private class MarkerWork(private val model: AppModel, private val scope: CoroutineScope) {
    var ui by mutableStateOf(MarkerUi())
    private var bmp: Bitmap? = null
    private var cam: FloorCamera? = null
    private var emb: Deferred<Embedding?>? = null
    private var source: File? = null
    private val started = System.currentTimeMillis()

    fun process(file: File) {
        source = file
        ui = ui.copy(step = MStep.FINDING, message = null, outline = null, box = null, result = null)
        scope.launch {
            val r = withContext(Dispatchers.Default) { load(file) }
            if (r == null) { ui = ui.copy(step = MStep.NO_SHEET, message = "Foto tidak bisa dibuka. Foto ulang."); return@launch }
            val (b, argb) = r
            bmp = b
            ui = ui.copy(photo = b.asImageBitmap(), iw = b.width, ih = b.height)
            emb = scope.async(Dispatchers.Default) { model.segmenter?.embed(argb, b.width, b.height) }
            val found = withContext(Dispatchers.Default) {
                val gray = IntArray(argb.size) { i -> val p = argb[i]; (((p shr 16) and 255) * 299 + ((p shr 8) and 255) * 587 + (p and 255) * 114) / 1000 }
                MarkerDetector.detect(gray, b.width, b.height)
            }
            if (found == null) {
                ui = ui.copy(step = MStep.NO_SHEET, message = "Kertas penanda tidak terlihat utuh. Pastikan kotak hitam terlihat seluruhnya, tidak tertutup paket atau bayangan.")
                return@launch
            }
            val c = FloorCamera.fromHomography(found.h, b.width, b.height, exifFocal(file, b.width, b.height))
                ?: FloorCamera.fromHomography(found.h, b.width, b.height, null)
            val height = c?.centre?.get(2) ?: 0.0
            if (c == null || height < 0.25 || height > 2.5) {
                ui = ui.copy(step = MStep.NO_SHEET, sheet = found.corners, message = "Sudut foto terlalu datar. Foto dari lebih tinggi, HP miring ke bawah ±45°.")
                return@launch
            }
            cam = c
            ui = ui.copy(step = MStep.PICK, sheet = found.corners)
        }
    }

    fun pick(prompt: FloatArray) {
        val c = cam ?: return
        if (ui.step != MStep.PICK && ui.step != MStep.RESULT) return
        ui = ui.copy(step = MStep.SELECTING, box = null, result = null, outline = null, message = null)
        scope.launch {
            val out = withContext(Dispatchers.Default) {
                val e = emb?.await() ?: return@withContext null
                val sam = model.segmenter ?: return@withContext null
                val m = if (prompt.size == 2) sam.tap(e, prompt[0], prompt[1]) else sam.box(e, prompt[0], prompt[1], prompt[2], prompt[3])
                val r = SingleView.measure(m, c) ?: return@withContext Triple(m.outline(), null, null)
                val corners = (r.floorCorners + r.topCorners).map { c.project(it.x.toDouble(), it.y.toDouble(), it.z.toDouble()) }
                val box = FloatArray(16) { i -> corners[i / 2]?.let { if (i % 2 == 0) it.a else it.b } ?: Float.NaN }
                Triple(m.outline(), r, box)
            }
            if (out?.second == null) {
                ui = ui.copy(step = MStep.PICK, outline = out?.first, attempts = ui.attempts + 1,
                    message = "Paket belum terbaca. Ketuk tengah paket, atau gambar kotak di sekelilingnya.")
                return@launch
            }
            val (outline, r, box) = out
            val conf = SingleView.confidence(r!!)
            val photo = withContext(Dispatchers.Default) { evidence(box!!) }
            val res = ResultData(round1(r.lengthM * 100.0), round1(r.widthM * 100.0), round1(r.heightM * 100.0),
                conf, if (conf >= 75) Status.OK else Status.CHECK, (System.currentTimeMillis() - started) / 1000.0, photo, null, Mode.MARKER)
            ui = ui.copy(step = MStep.RESULT, outline = outline, box = box, result = res)
        }
    }

    fun repeat() { ui = ui.copy(step = MStep.PICK, box = null, result = null, outline = null, attempts = ui.attempts + 1) }

    private fun round1(x: Double) = Math.round(x * 10.0) / 10.0

    /** The photo, upright, at most 1600 px on its long side, plus its pixels. */
    private fun load(file: File): Pair<Bitmap, IntArray>? = runCatching {
        val o = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(file.path, o)
        var sample = 1
        while (max(o.outWidth, o.outHeight) / (sample * 2) >= 1600) sample *= 2
        var b = BitmapFactory.decodeFile(file.path, BitmapFactory.Options().apply { inSampleSize = sample }) ?: return null
        val rot = when (ExifInterface(file.path).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
            ExifInterface.ORIENTATION_ROTATE_90 -> 90f; ExifInterface.ORIENTATION_ROTATE_180 -> 180f
            ExifInterface.ORIENTATION_ROTATE_270 -> 270f; else -> 0f
        }
        val k = min(1f, 1600f / max(b.width, b.height))
        if (rot != 0f || k < 1f) {
            val m = android.graphics.Matrix().apply { postScale(k, k); postRotate(rot) }
            b = Bitmap.createBitmap(b, 0, 0, b.width, b.height, m, true)
        }
        b = b.copy(Bitmap.Config.ARGB_8888, true)
        val px = IntArray(b.width * b.height)
        b.getPixels(px, 0, b.width, 0, 0, b.width, b.height)
        b to px
    }.getOrNull()

    /** Focal length in pixels from the 35 mm-equivalent focal in EXIF (on the frame diagonal), when present. */
    private fun exifFocal(file: File, w: Int, h: Int): Double? = runCatching {
        val f35 = ExifInterface(file.path).getAttributeInt(ExifInterface.TAG_FOCAL_LENGTH_IN_35MM_FILM, 0)
        if (f35 in 10..200) f35 * hypot(w.toDouble(), h.toDouble()) / 43.27 else null
    }.getOrNull()

    /** Evidence photo: the picture with the 3D box drawn on it. */
    private fun evidence(box: FloatArray): String? = runCatching {
        val b = bmp!!.copy(Bitmap.Config.ARGB_8888, true)
        val c = Canvas(b)
        val k = max(b.width, b.height) / 1000f
        val green = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0xFF22C55E.toInt(); strokeWidth = 5f * k; style = Paint.Style.STROKE }
        val dashed = Paint(green).apply { strokeWidth = 3f * k; pathEffect = DashPathEffect(floatArrayOf(10f * k, 7f * k), 0f) }
        fun line(i: Int, j: Int, p: Paint) { if (!box[2 * i].isNaN() && !box[2 * j].isNaN()) c.drawLine(box[2 * i], box[2 * i + 1], box[2 * j], box[2 * j + 1], p) }
        for (i in 0 until 4) { val j = (i + 1) % 4; line(i, j, dashed); line(i + 4, j + 4, green); line(i, i + 4, green) }
        val out = File(model.store.photosDir, "m${System.currentTimeMillis()}.jpg")
        out.outputStream().use { b.compress(Bitmap.CompressFormat.JPEG, 85, it) }
        out.path
    }.getOrNull()
}

@Composable
internal fun MarkerChrome(ui: MarkerUi, model: AppModel, act: MarkerActions, demoBox: FloatArray? = null, showHub: Boolean = false) {
    var boxMode by remember { mutableStateOf(demoBox != null) }
    var drag by remember { mutableStateOf<FloatArray?>(null) }
    var hub by remember { mutableStateOf(showHub) }
    var area by remember { mutableStateOf(IntSize(1, 1)) }
    // photo pixels <-> screen pixels (photo fitted into the area, centred)
    val s = min(area.width.toFloat() / ui.iw, area.height.toFloat() / ui.ih)
    val ox = (area.width - ui.iw * s) / 2; val oy = (area.height - ui.ih * s) / 2
    fun toScreen(p: P2) = Offset(ox + p.a * s, oy + p.b * s)
    val shownDrag = drag ?: demoBox?.let { d -> floatArrayOf(ox + d[0] * s, oy + d[1] * s, ox + d[2] * s, oy + d[3] * s) }

    Box(Modifier.fillMaxSize().background(Color(0xFF0B1220))) {
        if (ui.step == MStep.TAKE) { TakeStep(model, act); return@Box }
        Box(Modifier.fillMaxSize().padding(bottom = 210.dp).onSizeChanged { area = it }) {
            ui.photo?.let { Image(it, null, Modifier.fillMaxSize(), contentScale = ContentScale.Fit) }
            val gestures = if (boxMode) Modifier.pointerInput(boxMode, s) {
                detectDragGestures(
                    onDragStart = { drag = floatArrayOf(it.x, it.y, it.x, it.y) },
                    onDrag = { ch, _ -> drag = drag?.let { d -> floatArrayOf(d[0], d[1], ch.position.x, ch.position.y) } },
                    onDragEnd = {
                        drag?.let { d -> if (abs(d[2] - d[0]) > 30 && abs(d[3] - d[1]) > 30)
                            act.box((d[0] - ox) / s, (d[1] - oy) / s, (d[2] - ox) / s, (d[3] - oy) / s) }
                        drag = null; boxMode = false
                    })
            } else Modifier.pointerInput(s, ox, oy) { detectTapGestures { act.tap((it.x - ox) / s, (it.y - oy) / s) } }
            ComposeCanvas(Modifier.fillMaxSize().then(gestures)) {
                ui.sheet?.let { c ->
                    for (ring in 0..1) {
                        val p = Path()
                        for (k in 0 until 4) { val q = toScreen(c[ring * 4 + k]); if (k == 0) p.moveTo(q.x, q.y) else p.lineTo(q.x, q.y) }
                        p.close()
                        drawPath(p, C.live, style = Stroke(2.5.dp.toPx()))
                    }
                }
                if (ui.box == null) ui.outline?.takeIf { it.size >= 3 }?.let { o ->
                    val p = Path()
                    o.forEachIndexed { k, q -> val v = toScreen(q); if (k == 0) p.moveTo(v.x, v.y) else p.lineTo(v.x, v.y) }
                    p.close()
                    drawPath(p, Color(0xFF3B82F6).copy(alpha = 0.18f)); drawPath(p, Color(0xFF3B82F6), style = Stroke(3.dp.toPx()))
                }
                ui.box?.let { b ->
                    val col = if (ui.result?.status == Status.CHECK) Color(0xFFF59E0B) else C.live
                    fun p(i: Int) = Offset(ox + b[2 * i] * s, oy + b[2 * i + 1] * s)
                    fun ok(i: Int) = !b[2 * i].isNaN()
                    val dashed = PathEffect.dashPathEffect(floatArrayOf(14f, 10f))
                    for (i in 0 until 4) {
                        val j = (i + 1) % 4
                        if (ok(i) && ok(j)) drawLine(col.copy(alpha = 0.9f), p(i), p(j), 2.5.dp.toPx(), pathEffect = dashed)
                        if (ok(i) && ok(i + 4)) drawLine(col, p(i), p(i + 4), 2.5.dp.toPx())
                        if (ok(i + 4) && ok(j + 4)) drawLine(col, p(i + 4), p(j + 4), 3.5.dp.toPx(), cap = StrokeCap.Round)
                    }
                    for (i in 4 until 8) if (ok(i)) { drawCircle(Color.White, 5.dp.toPx(), p(i)); drawCircle(col, 5.dp.toPx(), p(i), style = Stroke(2.dp.toPx())) }
                }
                shownDrag?.let { d ->
                    val tl = Offset(min(d[0], d[2]), min(d[1], d[3])); val sz = Size(abs(d[2] - d[0]), abs(d[3] - d[1]))
                    drawRect(Color.White.copy(alpha = 0.12f), tl, sz)
                    drawRect(Color.White, tl, sz, style = Stroke(2.5.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(24f, 16f))))
                }
            }
            val r = ui.result
            val b = ui.box
            if (r != null && b != null) {
                val sb = FloatArray(16) { i -> if (i % 2 == 0) ox + b[i] * s else oy + b[i] * s }
                val e01 = hypot(b[0] - b[2], b[1] - b[3]); val e12 = hypot(b[2] - b[4], b[3] - b[5])
                DimTags(sb, if (e01 >= e12) r.lengthCm else r.widthCm, if (e01 >= e12) r.widthCm else r.lengthCm, r.heightCm, r.status == Status.CHECK)
            }
        }

        Column(Modifier.fillMaxWidth().windowInsetsPadding(WindowInsets.statusBars).padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                GlassButton("arrow_back") { act.back() }
                StepPillOf(if (ui.step == MStep.RESULT) 0 else 2, if (ui.step == MStep.RESULT) "Hasil ukur" else "Pilih paket", Modifier.weight(1f))
            }
            if (ui.message != null && ui.step != MStep.NO_SHEET) Banner(ui.message, Color(0xFFF59E0B), Color(0xFF1F1300))
            else if (ui.sheet != null && ui.step == MStep.PICK && !boxMode) Banner("Kertas penanda terbaca", C.green, Color.White, "check_circle")
            else if (boxMode) Banner("Tarik jari dari satu sudut paket ke sudut seberangnya", C.blue, Color.White, "highlight_alt")
        }

        MarkerSheetPanel(Modifier.align(Alignment.BottomCenter), ui, model, act, boxMode, { boxMode = !boxMode }, { hub = true })
    }
    if (hub) HubDialog(onDismiss = { hub = false }) { reason -> hub = false; act.hub(reason) }
}

@Composable
private fun MarkerSheetPanel(modifier: Modifier, ui: MarkerUi, model: AppModel, act: MarkerActions, boxMode: Boolean,
                             toggleBox: () -> Unit, openHub: () -> Unit) {
    val settings by model.store.settings.collectAsState()
    Column(modifier.fillMaxWidth().clip(RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp)).background(Color.White)
        .windowInsetsPadding(WindowInsets.navigationBars).padding(start = 18.dp, end = 18.dp, top = 10.dp, bottom = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(Modifier.align(Alignment.CenterHorizontally).size(40.dp, 4.dp).clip(RoundedCornerShape(2.dp)).background(C.line))
        when (ui.step) {
            MStep.TAKE -> Unit
            MStep.FINDING, MStep.SELECTING -> {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.5.dp, color = C.blue)
                    T(if (ui.step == MStep.FINDING) "  Membaca kertas penanda…" else "  Memilih dan mengukur paket…", 18.sp, FontWeight.Bold)
                }
                T("Pengukuran berjalan di HP ini, beberapa detik.", 13.5.sp, color = C.t2)
            }
            MStep.NO_SHEET -> {
                Chip("Kertas penanda belum terbaca", Tone.WARN, "warning")
                T(ui.message ?: "", 13.5.sp, color = C.t2)
                PrimaryButton("Foto ulang", "photo_camera", Modifier.fillMaxWidth()) { act.retake() }
                if (ui.attempts >= 2) HubLink(openHub)
            }
            MStep.PICK -> {
                T("Ketuk paket yang diukur", 18.sp, FontWeight.Bold)
                T("Atau gambar kotak di sekeliling paket kalau ketukan hanya memilih sebagian.", 13.5.sp, color = C.t2)
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    SecondaryButton(if (boxMode) "Batal kotak" else "Gambar kotak", if (boxMode) "close" else "crop", Modifier.weight(1f)) { toggleBox() }
                    SecondaryButton("Foto ulang", "photo_camera", Modifier.weight(1f)) { act.retake() }
                }
                if (ui.attempts >= 2) HubLink(openHub)
            }
            MStep.RESULT -> {
                val r = ui.result ?: return@Column
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (r.status == Status.OK) Chip("Akurat · keyakinan ${r.confidence}%", Tone.OK, "check_circle")
                    else Chip("Cek ulang · keyakinan ${r.confidence}%", Tone.WARN, "warning")
                    Spacer(Modifier.weight(1f))
                    T("…" + (model.draft?.resi?.takeLast(4) ?: ""), 12.sp, color = C.t3)
                }
                T("${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm", 30.sp, FontWeight.Bold)
                if (r.status == Status.CHECK) T("Pastikan kotak pas membungkus paket, atau foto ulang dari sudut lebih tinggi.", 13.sp, color = C.t2)
                ResultStats(r.lengthCm, r.widthCm, r.heightCm, settings.divisor, r.seconds)
                SaveRow(r.status == Status.CHECK, r, { act.repeat() }) { act.save(r) }
                if (ui.attempts >= 2 && r.status == Status.CHECK) HubLink(openHub)
            }
        }
    }
}

/** Step 1 in marker mode: how to lay the sheet and take the photo. */
@Composable
private fun TakeStep(model: AppModel, act: MarkerActions) {
    Column(Modifier.fillMaxSize().background(C.bg)) {
        TopBar("Ukur dengan kertas penanda", model.draft?.resi, onBack = { act.back() })
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.clip(RoundedCornerShape(14.dp)).background(C.blueL).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Sym("info", 22.dp, C.blue, filled = true)
                T("HP ini belum bisa AR. Ukuran dihitung dari 1 foto: paket berdiri di samping kertas penanda A4.",
                    13.sp, color = Color(0xFF1E3A8A), modifier = Modifier.padding(start = 10.dp))
            }
            Card(padding = 6.dp) {
                listOf(
                    Triple("grid_on", "Taruh kertas penanda di lantai", "Rata, di samping paket, kotak hitam tidak tertutup"),
                    Triple("inventory_2", "Paket berdiri di lantai yang sama", "Jangan di atas paket lain atau di atas kertas"),
                    Triple("directions_walk", "Mundur sekitar 1 langkah", "HP miring ke bawah ±45°, bukan dari samping"),
                    Triple("crop_free", "Paket dan kertas masuk foto", "Seluruhnya terlihat, cukup terang"),
                ).forEachIndexed { i, (icon, t, sub) ->
                    Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                        IconTile(icon)
                        Column(Modifier.padding(start = 12.dp)) { T(t, 14.5.sp, FontWeight.SemiBold); T(sub, 12.5.sp, color = C.t2) }
                    }
                    if (i < 3) Box(Modifier.fillMaxWidth().height(1.dp).background(C.line))
                }
            }
            SecondaryButton("Belum punya kertasnya? Cetak (PDF A4)", "print", Modifier.fillMaxWidth()) { act.sheet() }
            if (model.samState != SamState.READY)
                T(if (model.samState == SamState.LOADING) "Menyiapkan model pemilih paket…" else "Model pemilih paket tidak bisa dimuat.", 12.5.sp, color = C.t3)
        }
        PrimaryButton("Ambil foto", "photo_camera", Modifier.fillMaxWidth().padding(16.dp)) { act.take() }
    }
}
