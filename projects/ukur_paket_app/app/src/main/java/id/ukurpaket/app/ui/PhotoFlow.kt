package id.ukurpaket.app.ui

import android.app.Application
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.viewModelScope
import id.ukurpaket.app.ar.ResultData
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.dt.ObjectPick
import id.ukurpaket.app.measure.Embedding
import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.photo.CalSample
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.DepthModel
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoCamera
import id.ukurpaket.app.photo.PhotoFailed
import id.ukurpaket.app.photo.PhotoFiles
import id.ukurpaket.app.photo.PhotoMeasure
import id.ukurpaket.app.photo.FocusCal
import id.ukurpaket.app.photo.FocusInfo
import id.ukurpaket.app.photo.Standing
import id.ukurpaket.app.photo.PhotoResult
import id.ukurpaket.app.photo.ShotRecord
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.roundToInt

/** Why the photo screen is open: a parcel's size, a test against a tape measure, or this phone's calibration. */
enum class PhotoPurpose { PARCEL, TEST, CALIBRATE }

/** One photo as the screen shows it. Pick positions are in [picture] pixels. */
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
    /** The object's outline as fractions of the picture (x, y, x, y…), for drawing. */
    val outline: List<Float>? = null,
    val result: PhotoResult? = null,
    val error: String? = null,
    /** The autofocus when the photo was taken: a physical clue to the distance. */
    val focus: FocusInfo? = null,
)

/**
 * The photo mode's state and work (0.4.0): photos of one object, each cut out by MobileSAM-512 and measured with the
 * camera height from Depth Anything V2, the autofocus and the standing height; several photos are combined (median). Lives in the [AppModel], so a turn of the
 * screen or a trip to the weight screen keeps it.
 */
class PhotoFlow(private val model: AppModel) {
    private val app get() = model.getApplication<Application>()
    var purpose by mutableStateOf(PhotoPurpose.TEST); private set
    var dir: File? = null; private set
    val shots = mutableStateListOf<PhotoShotUi>()
    /** The photo shown, or null for the camera. */
    var current by mutableStateOf<Int?>(null)
    var capturing by mutableStateOf(false)
    var depthState by mutableStateOf(SamState.LOADING); private set
    /** Tape-measure size typed on the screen (test or calibration), as typed. */
    var tape by mutableStateOf(listOf("", "", ""))

    // read from the IO and Default threads too (files, records): concurrent maps
    private val embeddings = java.util.concurrent.ConcurrentHashMap<Int, Embedding>()
    private val depths = java.util.concurrent.ConcurrentHashMap<Int, CompletableDeferred<Pair<DepthMap, Long>?>>()
    private val records = java.util.concurrent.ConcurrentHashMap<Int, ShotRecord>()
    private val pendingPick = java.util.concurrent.ConcurrentHashMap<Int, Pair<List<Float>?, List<Float>?>>()
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
        }.also { depthModel = it; depthState = if (it != null) SamState.READY else SamState.FAILED }
    }

    /** This phone's calibration samples made with the current depth model. */
    val samples: List<CalSample> get() = Calibration.current(model.store.settings.value.photoCal)
    val scale: Double get() = if (purpose == PhotoPurpose.CALIBRATE) 1.0 else Calibration.factor(samples) ?: DepthModel.DEFAULT_SCALE.toDouble()
    val calibrated: Boolean get() = purpose != PhotoPurpose.CALIBRATE && samples.isNotEmpty()
    /** How the autofocus turns into a distance on this phone (not used while calibrating: the photos teach it then). */
    fun focusCal(lens: FocusInfo?): FocusCal? = if (purpose == PhotoPurpose.CALIBRATE) null else Calibration.focus(samples, lens)

    /** The courier's standing camera height from the calibration photos (not used while calibrating). */
    val standing: Standing? get() = if (purpose == PhotoPurpose.CALIBRATE) null else Calibration.standing(samples)

    /** All photos with a size, combined. */
    val combined: PhotoResult? get() = shots.mapNotNull { it.result }.takeIf { it.isNotEmpty() }?.let { PhotoMeasure.combine(it) }

    fun start(p: PhotoPurpose) {
        purpose = p
        dir = PhotoFiles.newDir(model.store.photoSessionsDir)
        shots.clear(); embeddings.clear(); depths.clear(); records.clear(); pendingPick.clear(); next = 0
        current = null; capturing = false; tape = listOf("", "", "")
        model.viewModelScope.launch { model.samLightNow(); depthNow() }
    }

    private fun rec(index: Int, f: (ShotRecord) -> ShotRecord) { records[index]?.let { records[index] = f(it) } }

    private fun update(index: Int, f: (PhotoShotUi) -> PhotoShotUi) {
        val i = shots.indexOfFirst { it.index == index }
        if (i >= 0) shots[i] = f(shots[i])
    }

    /** A still from the camera: kept, shown, and read by both models in the background. */
    fun onShot(s: PhotoCamera.Shot) {
        val d = dir ?: return
        val index = next++
        model.viewModelScope.launch {
            val rot = ((s.rotation % 360) + 360) % 360
            val uw = if (rot == 90 || rot == 270) s.sh else s.sw; val uh = if (rot == 90 || rot == 270) s.sw else s.sh
            val ow = 480; val oh = (480f * uh / uw).roundToInt()
            val (small, pic) = withContext(Dispatchers.Default) {
                val a = PhotoFiles.uprightArgb(s.nv21, s.sw, s.sh, s.rotation, ow, oh)
                a to PhotoFiles.bitmap(a, ow, oh)
            }
            val kSmall = s.k.scaled(ow, oh)
            val up = Intrinsics.upFromAccel(s.accel[0], s.accel[1], s.accel[2])
            val down = PhotoCamera.downDeg(s.accel)
            shots.add(PhotoShotUi(index, pic, kSmall, up, down, s.still, stage = "Membaca foto…", focus = s.focus))
            current = index; capturing = false
            records[index] = ShotRecord(index, s.timeMs, listOf(s.sw, s.sh), s.rotation, s.k, kSmall, s.accel.toList(), s.accelSpread, s.still, down,
                focus = s.focus, app = id.ukurpaket.app.BuildConfigInfo.VERSION)
            val depthDone = CompletableDeferred<Pair<DepthMap, Long>?>()
            depths[index] = depthDone
            // the full photo is the record's evidence; written while the models work
            launch(Dispatchers.IO) {
                runCatching { PhotoFiles.saveJpeg(PhotoFiles.bitmap(PhotoFiles.uprightArgb(s.nv21, s.sw, s.sh, s.rotation, uw, uh), uw, uh), PhotoFiles.photo(d, index)) }
                writeRecord(index)
            }
            val sam = model.samLightNow()
            if (sam == null) { update(index) { it.copy(stage = null, error = "MobileSAM tidak bisa dimuat") }; depthDone.complete(null); return@launch }
            val t0 = System.nanoTime()
            val e = runCatching { inference.withLock { withContext(Dispatchers.Default) { sam.embed(small, ow, oh) } } }.getOrNull()
            if (e == null) { update(index) { it.copy(stage = null, error = "Foto tidak bisa dibaca MobileSAM") }; depthDone.complete(null); return@launch }
            embeddings[index] = e
            rec(index) { it.copy(samMs = (System.nanoTime() - t0) / 1_000_000) }
            update(index) { it.copy(ready = true, stage = if (it.tap == null && it.box == null) null else it.stage) }
            pendingPick.remove(index)?.let { (t, b) -> pick(index, t, b) }
            val dm = depthNow()
            val t1 = System.nanoTime()
            val depth = dm?.let { m -> runCatching { inference.withLock { withContext(Dispatchers.Default) { m.run(small, ow, oh) } } }.getOrNull() }
            val ms = (System.nanoTime() - t1) / 1_000_000
            depthDone.complete(depth?.let { it to ms })
            if (depth != null) launch(Dispatchers.IO) { runCatching { PhotoFiles.saveDepth(depth, PhotoFiles.depth(d, index)) } }
            else update(index) { it.copy(error = it.error ?: "Model depth tidak bisa dijalankan di HP ini") }
        }
    }

    /** The object picked on photo [index]: [tap] (x, y) or [box] (x0, y0, x1, y1) in picture pixels. */
    fun pick(index: Int, tap: List<Float>?, box: List<Float>?) {
        val shot = shots.firstOrNull { it.index == index } ?: return
        val e = embeddings[index]
        update(index) { it.copy(tap = tap, box = box, mask = null, tint = null, outline = null, result = null, error = null, stage = "Memotong paket…") }
        if (e == null) { pendingPick[index] = tap to box; return }
        model.viewModelScope.launch {
            val sam = model.samLightNow() ?: return@launch
            val m = withContext(Dispatchers.Default) {
                runCatching {
                    (if (box != null) sam.box(e, box[0], box[1], box[2], box[3]) else sam.tapRefined(e, tap!![0], tap[1]).maxBy { it.score }).largestPart()
                }.getOrNull()
            }
            if (m == null || m.area < 30) { update(index) { it.copy(stage = null, error = "Paket tidak terpotong: ketuk tepat di paketnya, atau tarik kotak") }; return@launch }
            val tint = withContext(Dispatchers.Default) { ObjectPick.tint(m) }
            val outline = m.outline().flatMap { listOf(it.a / m.w, it.b / m.h) }
            update(index) { it.copy(mask = m, tint = tint, outline = outline, stage = "Mengukur…") }
            rec(index) { it.copy(pickMode = if (box != null) "box" else "tap", tap = tap, box = box, maskScore = m.score) }
            dir?.let { d -> launch(Dispatchers.IO) { runCatching { PhotoFiles.saveMask(m, PhotoFiles.mask(d, index)) } } }
            val dep = depths[index]?.await()
            if (dep == null) { update(index) { it.copy(stage = null, error = "Kedalaman tidak terbaca: ulangi foto") }; return@launch }
            rec(index) { it.copy(depthMs = dep.second, depthSize = listOf(dep.first.w, dep.first.h)) }
            val r = withContext(Dispatchers.Default) {
                runCatching { PhotoMeasure.measure(m, shot.k, shot.up, dep.first, scale.toFloat(), calibrated, standing, shot.focus, focusCal(shot.focus)) }
            }
            r.onSuccess { res -> update(index) { it.copy(stage = null, result = res) }; rec(index) { it.copy(result = res, error = null) } }
                .onFailure { t ->
                    val msg = (t as? PhotoFailed)?.message ?: "Gagal mengukur: ${t.message ?: t.javaClass.simpleName}"
                    update(index) { it.copy(stage = null, error = msg) }; rec(index) { it.copy(result = null, error = msg) }
                }
            writeRecord(index)
        }
    }

    /** Drops photo [index] (a bad one); the others stay. */
    fun remove(index: Int) {
        shots.removeAll { it.index == index }
        embeddings.remove(index); depths.remove(index); records.remove(index); pendingPick.remove(index)
        dir?.let { d -> listOf(PhotoFiles.photo(d, index), PhotoFiles.mask(d, index), PhotoFiles.depth(d, index), PhotoFiles.record(d, index)).forEach { it.delete() } }
        current = shots.lastOrNull()?.index
    }

    private fun writeRecord(index: Int) {
        val d = dir ?: return
        val r = records[index] ?: return
        val t = tapeCm()
        runCatching { PhotoFiles.record(d, index).writeText(PhotoFiles.json.encodeToString(ShotRecord.serializer(), if (t != null) r.copy(tapeCm = t) else r)) }
    }

    /** The typed tape size (L, W, H in cm), or null when not all three are given. */
    fun tapeCm(): List<Double>? = tape.map { ObjectPick.cm(it) }.takeIf { l -> l.all { it != null } }?.map { it!! }

    /** The tape size is written into every photo's record (for the PC), e.g. when the test data is shared. */
    fun saveTape() { model.viewModelScope.launch(Dispatchers.IO) { records.keys.forEach { writeRecord(it) } } }

    /** The combined size for the parcel being measured, with the evidence photo; on to the weight screen. */
    fun use() {
        val r = combined ?: return
        val d = dir ?: return
        val draft = model.draft ?: return
        val best = shots.filter { it.result != null }.maxByOrNull { it.result!!.confidence } ?: return
        model.viewModelScope.launch {
            val ev = withContext(Dispatchers.IO) {
                runCatching {
                    val full = BitmapFactory.decodeFile(PhotoFiles.photo(d, best.index).path) ?: best.picture
                    PhotoFiles.evidence(full, best.result!!.corners, best.outline, PhotoFiles.evidence(d))
                    PhotoFiles.evidence(d).path
                }.getOrNull()
            }
            model.draft = draft.copy(result = ResultData(r.lengthCm, r.widthCm, r.heightCm, r.confidence, if (r.ok) Status.OK else Status.CHECK,
                0.0, ev, d.path, Mode.PHOTO))
            model.leaveMeasuring()
            model.go(Screen.Weight)
        }
    }

    enum class CalSave { SAVED, MISMATCH, INCOMPLETE }

    /** The sample the typed tape size would make with the photos so far (null without a size or a full tape size). */
    fun pendingSample(): CalSample? {
        val r = combined ?: return null
        val t = tapeCm() ?: return null
        return CalSample(r.rawCm, t, model = DepthModel.ID, aiCameraM = r.aiCameraM,
            focusFactors = shots.mapNotNull { it.result }.mapNotNull { Calibration.focusFactor(it, t) })
    }

    /**
     * This photo's size against the typed tape size becomes one calibration sample of the phone. A photo whose shape does
     * not match the tape (the sides' ratios over 1,35 apart) is saved only when [force]: the screen asks first.
     */
    fun saveCalibration(force: Boolean = false): CalSave {
        val s = pendingSample() ?: return CalSave.INCOMPLETE
        if (!force && Calibration.mismatch(s) > Calibration.MISMATCH) return CalSave.MISMATCH
        model.store.update { it.copy(photoCal = it.photoCal + s) }
        saveTape()
        val f = Calibration.factor(samples) ?: 1.0
        model.toast("Kalibrasi tersimpan · faktor ×${"%.2f".format(f).replace('.', ',')} · ${samples.size} kardus")
        return CalSave.SAVED
    }

    fun close() { depthModel?.let { m -> depthModel = null; Thread { Thread.sleep(3000); m.close() }.start() } }
}
