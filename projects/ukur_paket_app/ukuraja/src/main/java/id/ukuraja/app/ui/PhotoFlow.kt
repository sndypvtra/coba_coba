package id.ukuraja.app.ui

import android.app.Application
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.viewModelScope
import id.ukuraja.app.Version
import id.ukuraja.app.data.Settings
import id.ukuraja.app.data.Status
import id.ukurpaket.app.marker.Aruco
import id.ukurpaket.app.marker.Luma
import id.ukurpaket.app.marker.MarkerDetection
import id.ukurpaket.app.marker.MarkerObservation
import id.ukurpaket.app.marker.MarkerScale
import id.ukurpaket.app.marker.MarkerSheet
import id.ukurpaket.app.measure.Embedding
import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.photo.CalSample
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.DepthModel
import id.ukurpaket.app.photo.FocusCal
import id.ukurpaket.app.photo.FocusInfo
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoCamera
import id.ukurpaket.app.photo.PhotoFailed
import id.ukurpaket.app.photo.PhotoFiles
import id.ukurpaket.app.photo.PhotoMeasure
import id.ukurpaket.app.photo.PhotoResult
import id.ukurpaket.app.photo.Sharpness
import id.ukurpaket.app.photo.ShotRecord
import id.ukurpaket.app.photo.Standing
import id.ukurpaket.app.photo.SweepData
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.roundToInt

/** One photo as the screen shows it. Pick positions are in [picture] pixels (the 480-wide picture the models see). */
data class PhotoShotUi(
    val index: Int,
    val picture: Bitmap,
    val k: Intrinsics,
    val up: V3,
    val downDeg: Float,
    val still: Boolean,
    /** What is running on this photo now ("Memotong paket…"), null when nothing is. */
    val stage: String? = null,
    /** MobileSAM has read the photo: a tap or a box is answered at once. */
    val ready: Boolean = false,
    val tap: List<Float>? = null,
    val box: List<Float>? = null,
    val mask: Mask? = null,
    val tint: Bitmap? = null,
    /** The parcel's outline as fractions of the picture (x, y, x, y…), for drawing. */
    val outline: List<Float>? = null,
    val result: PhotoResult? = null,
    val error: String? = null,
    val focus: FocusInfo? = null,
    /** The full-resolution upright luma ([lumaW] x [lumaH]): sharpness and markers are read on it. */
    val luma: ByteArray? = null,
    val lumaW: Int = 0,
    val lumaH: Int = 0,
    val sweep: SweepData? = null,
    /** Printed markers found in the full-resolution picture. */
    val markers: List<MarkerDetection> = emptyList(),
) {
    /** Each marker's corners as fractions of the picture (x, y × 4), for drawing. */
    val markerFractions: List<List<Float>>
        get() = if (lumaW == 0) emptyList() else markers.map { d -> d.flat().mapIndexed { i, v -> if (i % 2 == 0) v / lumaW else v / lumaH } }
}

/**
 * The photo mode's state and work: photos of one parcel, each cut out by MobileSAM-512 and measured by the engine
 * (PhotoMeasure) with the camera height from the printed marker when one lies next to the parcel, else from the depth
 * model with what earlier marker photos taught (factor, standing height, focus). Several photos are combined (median).
 */
class PhotoFlow(private val model: AppModel) {
    private val app get() = model.getApplication<Application>()
    var dir: File? = null; private set
    val shots = mutableStateListOf<PhotoShotUi>()
    /** The photo shown, or null for the camera. */
    var current by mutableStateOf<Int?>(null)
    var capturing by mutableStateOf(false)
    var depthState by mutableStateOf(ModelState.LOADING); private set

    private val embeddings = java.util.concurrent.ConcurrentHashMap<Int, Embedding>()
    private val depths = java.util.concurrent.ConcurrentHashMap<Int, CompletableDeferred<Pair<DepthMap, Long>?>>()
    private val records = java.util.concurrent.ConcurrentHashMap<Int, ShotRecord>()
    private val pendingPick = java.util.concurrent.ConcurrentHashMap<Int, Pair<List<Float>?, List<Float>?>>()
    private val learned = java.util.Collections.synchronizedSet(HashSet<Int>())
    private var next = 0
    /** One model at a time: on a phone CPU two at once are each slower than both in turn. */
    private val inference = Mutex()

    @Volatile var depthModel: DepthModel? = null; private set
    private val depthLock = Mutex()

    suspend fun depthNow(): DepthModel? = depthLock.withLock {
        depthModel ?: withContext(Dispatchers.Default) {
            runCatching {
                val threads = Runtime.getRuntime().availableProcessors().coerceIn(2, 4)
                DepthModel(app.assets.open(DepthModel.ASSET).use { it.readBytes() }, threads)
            }.getOrNull()
        }.also { depthModel = it; depthState = if (it != null) ModelState.READY else ModelState.FAILED }
    }

    private val settings: Settings get() = model.store.settings.value
    /** What earlier marker photos taught this phone (with the depth model in use). */
    val samples: List<CalSample> get() = Calibration.current(settings.photoCal)
    val scale: Double get() = Calibration.factor(samples) ?: DepthModel.DEFAULT_SCALE.toDouble()
    val calibrated: Boolean get() = samples.isNotEmpty()
    fun focusCal(lens: FocusInfo?): FocusCal? = Calibration.focus(samples, lens)
    val standing: Standing? get() = Calibration.standing(samples)

    /** All photos with a size, combined. */
    val combined: PhotoResult? get() = shots.mapNotNull { it.result }.takeIf { it.isNotEmpty() }?.let { PhotoMeasure.combine(it) }

    fun start() {
        dir = PhotoFiles.newDir(model.store.photoSessionsDir)
        shots.clear(); embeddings.clear(); depths.clear(); records.clear(); pendingPick.clear(); learned.clear(); next = 0
        current = null; capturing = false; seen = null
        model.viewModelScope.launch { model.samNow(); depthNow() }
    }

    private fun rec(index: Int, f: (ShotRecord) -> ShotRecord) { records[index]?.let { records[index] = f(it) } }

    private fun update(index: Int, f: (PhotoShotUi) -> PhotoShotUi) {
        val i = shots.indexOfFirst { it.index == index }
        if (i >= 0) shots[i] = f(shots[i])
    }

    // ------------------------------------------------------------------ the photo and its markers
    /** What the camera thread found with the photo (it decides on the focus sweep): handed to [onShot]. */
    private class Seen(val timeMs: Long, val luma: ByteArray, val w: Int, val h: Int, val markers: List<MarkerDetection>)
    @Volatile private var seen: Seen? = null

    /**
     * Asked by the camera with the photo, before its focus sweep (on the camera's thread, ~0,1–0,2 s): the markers in
     * the full picture. A sheet big enough to give the distance makes the sweep (up to 6 s of holding still) unneeded.
     */
    fun wantsSweep(s: PhotoCamera.Shot): Boolean {
        val rot = ((s.rotation % 360) + 360) % 360
        val uw = if (rot == 90 || rot == 270) s.sh else s.sw; val uh = if (rot == 90 || rot == 270) s.sw else s.sh
        val luma = PhotoFiles.uprightLuma(s.nv21, s.sw, s.sh, s.rotation)
        val found = runCatching { Aruco.detect(Luma(uw, uh, luma), MarkerSheet.IDS) }.getOrDefault(emptyList())
        seen = Seen(s.timeMs, luma, uw, uh, found)
        val enough = MarkerScale.MIN_SIDE_PX * 1.3 * uw / 480.0
        return found.none { it.sidePx >= enough && settings.markerSideM(it.id) != null }
    }

    /** The marker sheets of [found] as the engine reads them, in the 480-wide picture (sides as set in Settings). */
    private fun observations(found: List<MarkerDetection>, s: Float): List<MarkerObservation> =
        found.mapNotNull { d -> settings.markerSideM(d.id)?.let { MarkerObservation.of(d, it, s) } }

    /** A still from the camera: kept, shown, and read by both models in the background. */
    fun onShot(s: PhotoCamera.Shot) {
        val d = dir ?: return
        val index = next++
        val pre = seen?.takeIf { it.timeMs == s.timeMs }
        seen = null
        model.viewModelScope.launch {
            val rot = ((s.rotation % 360) + 360) % 360
            val uw = if (rot == 90 || rot == 270) s.sh else s.sw; val uh = if (rot == 90 || rot == 270) s.sw else s.sh
            val ow = 480; val oh = (480f * uh / uw).roundToInt()
            val (small, pic) = withContext(Dispatchers.Default) {
                val a = PhotoFiles.uprightArgb(s.nv21, s.sw, s.sh, s.rotation, ow, oh)
                a to PhotoFiles.bitmap(a, ow, oh)
            }
            val luma = pre?.luma ?: withContext(Dispatchers.Default) { PhotoFiles.uprightLuma(s.nv21, s.sw, s.sh, s.rotation) }
            val markers = pre?.markers ?: withContext(Dispatchers.Default) {
                runCatching { Aruco.detect(Luma(uw, uh, luma), MarkerSheet.IDS) }.getOrDefault(emptyList())
            }
            val kSmall = s.k.scaled(ow, oh)
            val up = Intrinsics.upFromAccel(s.accel[0], s.accel[1], s.accel[2])
            val down = PhotoCamera.downDeg(s.accel)
            shots.add(PhotoShotUi(index, pic, kSmall, up, down, s.still, stage = "Membaca foto…", focus = s.focus, luma = luma, lumaW = uw, lumaH = uh,
                sweep = s.sweep, markers = markers))
            current = index; capturing = false
            records[index] = ShotRecord(index, s.timeMs, listOf(s.sw, s.sh), s.rotation, s.k, kSmall, s.accel.toList(), s.accelSpread, s.still, down,
                focus = s.focus, app = "UkurAja ${Version.NAME}",
                sweepDiopters = s.sweep?.frames?.map { it.diopters }, sweepSize = s.sweep?.let { listOf(it.w / 2, it.h / 2) },
                markers = observations(markers, 1f))
            s.sweep?.let { sw -> launch(Dispatchers.IO) { runCatching { PhotoFiles.saveSweep(sw, PhotoFiles.sweep(d, index)) } } }
            val depthDone = CompletableDeferred<Pair<DepthMap, Long>?>()
            depths[index] = depthDone
            // the full photo is the record's evidence; written while the models work
            launch(Dispatchers.IO) {
                runCatching { PhotoFiles.saveJpeg(PhotoFiles.bitmap(PhotoFiles.uprightArgb(s.nv21, s.sw, s.sh, s.rotation, uw, uh), uw, uh), PhotoFiles.photo(d, index)) }
                writeRecord(index)
            }
            val sam = model.samNow()
            if (sam == null) { update(index) { it.copy(stage = null, error = "Model pemotong paket tidak bisa dimuat") }; depthDone.complete(null); return@launch }
            val t0 = System.nanoTime()
            val e = runCatching { inference.withLock { withContext(Dispatchers.Default) { sam.embed(small, ow, oh) } } }.getOrNull()
            if (e == null) { update(index) { it.copy(stage = null, error = "Foto tidak bisa dibaca: ulangi foto") }; depthDone.complete(null); return@launch }
            embeddings[index] = e
            rec(index) { it.copy(samMs = (System.nanoTime() - t0) / 1_000_000) }
            update(index) { it.copy(ready = true, stage = if (it.tap == null && it.box == null) null else it.stage) }
            pendingPick.remove(index)?.let { (t, b) -> pick(index, t, b) }
            val dm = depthNow()
            val t1 = System.nanoTime()
            val depth = dm?.let { m -> runCatching { inference.withLock { withContext(Dispatchers.Default) { m.run(small, ow, oh) } } }.getOrNull() }
            depthDone.complete(depth?.let { it to (System.nanoTime() - t1) / 1_000_000 })
            if (depth != null) launch(Dispatchers.IO) { runCatching { PhotoFiles.saveDepth(depth, PhotoFiles.depth(d, index)) } }
            else update(index) { it.copy(error = it.error ?: "Model jarak tidak bisa dijalankan di HP ini") }
        }
    }

    /** The parcel picked on photo [index]: [tap] (x, y) or [box] (x0, y0, x1, y1) in picture pixels. */
    fun pick(index: Int, tap: List<Float>?, box: List<Float>?) {
        val shot = shots.firstOrNull { it.index == index } ?: return
        val e = embeddings[index]
        update(index) { it.copy(tap = tap, box = box, mask = null, tint = null, outline = null, result = null, error = null, stage = "Memotong paket…") }
        if (e == null) { pendingPick[index] = tap to box; return }
        model.viewModelScope.launch {
            val sam = model.samNow() ?: return@launch
            val m = withContext(Dispatchers.Default) {
                runCatching {
                    (if (box != null) sam.box(e, box[0], box[1], box[2], box[3]) else sam.tapRefined(e, tap!![0], tap[1]).maxBy { it.score }).largestPart()
                }.getOrNull()
            }
            if (m == null || m.area < 30) { update(index) { it.copy(stage = null, error = "Paket tidak terpotong: ketuk tepat di paketnya, atau tarik kotak") }; return@launch }
            val tint = withContext(Dispatchers.Default) { tint(m) }
            val outline = m.outline().flatMap { listOf(it.a / m.w, it.b / m.h) }
            update(index) { it.copy(mask = m, tint = tint, outline = outline, stage = "Mengukur…") }
            rec(index) { it.copy(pickMode = if (box != null) "box" else "tap", tap = tap, box = box, maskScore = m.score) }
            dir?.let { d -> launch(Dispatchers.IO) { runCatching { PhotoFiles.saveMask(m, PhotoFiles.mask(d, index)) } } }
            val dep = depths[index]?.await()
            if (dep == null) { update(index) { it.copy(stage = null, error = "Jarak tidak terbaca: ulangi foto") }; return@launch }
            rec(index) { it.copy(depthMs = dep.second, depthSize = listOf(dep.first.w, dep.first.h)) }
            val obs = if (shot.lumaW > 0) observations(shot.markers, shot.k.w.toFloat() / shot.lumaW) else emptyList()
            val r = withContext(Dispatchers.Default) {
                val sharp = shot.luma?.let { Sharpness.atOutline(it, shot.lumaW, shot.lumaH, m) }
                rec(index) { it.copy(sharpness = sharp) }
                runCatching { PhotoMeasure.measure(m, shot.k, shot.up, dep.first, scale.toFloat(), calibrated, standing, shot.focus, focusCal(shot.focus), sharp, shot.sweep, obs) }
            }
            r.onSuccess { res -> update(index) { it.copy(stage = null, result = res) }; rec(index) { it.copy(result = res, error = null) }; learn(index, res) }
                .onFailure { t ->
                    val msg = (t as? PhotoFailed)?.message ?: "Gagal mengukur: ${t.message ?: t.javaClass.simpleName}"
                    update(index) { it.copy(stage = null, error = msg) }; rec(index) { it.copy(result = null, error = msg) }
                }
            writeRecord(index)
        }
    }

    /**
     * A photo whose scale a marker gave also teaches the phone (Settings → learnFromMarker): the depth model's factor,
     * the courier's standing height and the focus factor, so photos without a marker get better too. Once per photo,
     * and only when the depth model saw enough floor to have said something.
     */
    internal fun learn(index: Int, r: PhotoResult) {
        if (!settings.learnFromMarker || !r.markerUsed() || r.floorInliers < 300 || r.aiCameraM <= 0 || r.scale <= 0) return
        if (!learned.add(index)) return
        val sample = CalSample.fromMarker(r.aiCameraM / r.scale, r.markerCameraM, listOfNotNull(Calibration.focusFactorAt(r, r.markerCameraM)))
        model.store.update { st ->
            val (mk, other) = st.photoCal.partition { it.source == "marker" }
            st.copy(photoCal = other + (mk + sample).takeLast(Settings.MAX_MARKER_SAMPLES))
        }
    }

    /** Drops photo [index] (a bad one); the others stay. */
    fun remove(index: Int) {
        shots.removeAll { it.index == index }
        embeddings.remove(index); depths.remove(index); records.remove(index); pendingPick.remove(index)
        dir?.let { d -> listOf(PhotoFiles.photo(d, index), PhotoFiles.mask(d, index), PhotoFiles.depth(d, index), PhotoFiles.record(d, index), PhotoFiles.sweep(d, index)).forEach { it.delete() } }
        current = shots.lastOrNull()?.index
    }

    private fun writeRecord(index: Int) {
        val d = dir ?: return
        val r = records[index] ?: return
        runCatching { PhotoFiles.record(d, index).writeText(PhotoFiles.json.encodeToString(ShotRecord.serializer(), r)) }
    }

    /** The first photo of this parcel (for a record without a size). */
    fun anyPhoto(): String? = dir?.let { d -> shots.firstOrNull()?.let { PhotoFiles.photo(d, it.index).takeIf { f -> f.exists() }?.path } }

    /** In plain words, where a result's scale came from. */
    fun scaleSource(r: PhotoResult): String = when {
        r.markerUsed() -> "Marker " + (MarkerSheet.of(r.markerId)?.label ?: "")
        calibrated -> "AI + skala dari ${samples.size} foto marker"
        else -> "AI (tanpa marker)"
    }.trim()

    /** The combined size for the parcel being measured, with the evidence photo; on to the weight screen. */
    fun use() {
        val r = combined ?: return
        val d = dir ?: return
        val best = shots.filter { it.result != null }.maxByOrNull { it.result!!.confidence } ?: return
        val res = best.result!!
        model.viewModelScope.launch {
            val ev = withContext(Dispatchers.IO) {
                runCatching {
                    val full = BitmapFactory.decodeFile(PhotoFiles.photo(d, best.index).path) ?: best.picture
                    val mk = if (res.markerUsed()) best.markers.indices.maxByOrNull { best.markers[it].sidePx } else null
                    val label = mk?.let { i -> val id = best.markers[i].id; "Marker ${MarkerSheet.of(id)?.label} · ${((settings.markerSideM(id) ?: 0.0) * 100).let { v -> if (v % 1.0 == 0.0) v.toInt().toString() else "%.1f".format(v) }} cm" }
                    PhotoFiles.evidence(full, res.corners, best.outline, PhotoFiles.evidence(d), mk?.let { best.markerFractions[it] }, label)
                    PhotoFiles.evidence(d).path
                }.getOrNull()
            }
            model.onMeasured(PhotoOutcome(r.lengthCm, r.widthCm, r.heightCm, r.confidence, if (r.ok) Status.OK else Status.CHECK, ev, d.path,
                scaleSource(r), r.cameraHeightM, shots.count { it.result != null }))
        }
    }

    fun close() { depthModel?.let { m -> depthModel = null; Thread { Thread.sleep(3000); m.close() }.start() } }

    companion object {
        /** The cut-out as a translucent magenta layer over the photo. */
        fun tint(m: Mask): Bitmap {
            val px = IntArray(m.w * m.h) { if (m.bits[it]) 0x66ED0677 else 0 }
            return Bitmap.createBitmap(px, m.w, m.h, Bitmap.Config.ARGB_8888)
        }
    }
}
