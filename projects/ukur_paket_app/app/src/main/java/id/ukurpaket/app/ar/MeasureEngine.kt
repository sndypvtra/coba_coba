package id.ukurpaket.app.ar

import android.app.Activity
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.WindowManager
import com.google.ar.core.Camera
import com.google.ar.core.Config
import com.google.ar.core.Coordinates2d
import com.google.ar.core.Frame
import com.google.ar.core.Plane
import com.google.ar.core.Pose
import com.google.ar.core.Session
import com.google.ar.core.TrackingFailureReason
import com.google.ar.core.TrackingState
import com.google.ar.core.exceptions.CameraNotAvailableException
import com.google.ar.core.exceptions.NotYetAvailableException
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.measure.BoxFitter
import id.ukurpaket.app.measure.BoxResult
import id.ukurpaket.app.measure.FloorPlane
import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.PointAccumulator
import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.measure.convexHull
import id.ukurpaket.app.measure.dilate
import id.ukurpaket.app.measure.inside
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.File
import java.nio.ByteOrder
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicReference
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

enum class Phase { SEARCH, SELECT, SCAN, RESULT }

enum class Hint(val text: String) {
    NONE(""),
    MOVE("Gerakkan HP pelan ke kiri dan kanan"),
    SLOW("Pelan-pelan"),
    DARK("Terlalu gelap · nyalakan senter atau cari tempat terang"),
    TEXTURE("Arahkan ke lantai yang bertekstur"),
    LOST("Pelacakan hilang · gerakkan HP pelan"),
    NO_PARCEL("Arahkan titik ke paket"),
    PICK_FAILED("Paket belum terbaca · ketuk lagi atau gambar kotak"),
    BACK("Mundur sedikit · paket terpotong layar"),
    STACKED("Taruh paket langsung di lantai atau meja"),
    SWEEP("Geser HP pelan memutar ke sudut paket"),
    FAILED("Paket belum terbaca · ulangi dari sudut lain"),
}

/** Screen-space drawing for the overlay, in surface pixels. */
class Overlay(
    val floorDots: FloatArray = FloatArray(0),
    val depthDots: FloatArray = FloatArray(0),
    val outline: FloatArray? = null,
    /** 8 corners x,y: floor 0-3 then top 4-7; NaN where a corner is behind the camera. */
    val box: FloatArray? = null,
    /** Other parcels in view, each a closed outline: drawn dashed, labelled "Paket lain", tap to pick. */
    val others: List<FloatArray> = emptyList(),
    /** Parcels already measured in this session (x, y per mark) with their labels. */
    val marks: FloatArray = FloatArray(0),
    val markLabels: List<String> = emptyList(),
)

data class ResultData(
    val lengthCm: Double, val widthCm: Double, val heightCm: Double,
    val confidence: Int, val status: Status, val seconds: Double,
    val photo: String?, val recording: String?, val mode: Mode,
)

data class EngineUi(
    val phase: Phase = Phase.SEARCH,
    val planeFound: Boolean = false,
    val targetFound: Boolean = false,
    val progress: Float = 0f,
    val hint: Hint = Hint.MOVE,
    val overlay: Overlay = Overlay(),
    val live: BoxResult? = null,
    val result: ResultData? = null,
    val error: String? = null,
    val reticle: Pair<Float, Float>? = null,
    /** The segmentation model is cutting the parcel out of the picture. */
    val selecting: Boolean = false,
    /** The parcel was picked by tap / box (segmentation), not by the crosshair alone. */
    val picked: Boolean = false,
    /** Failed scans and repeats for this parcel: after two, the courier may hand it to the hub. */
    val attempts: Int = 0,
    val torch: Boolean = false,
    val torchSupported: Boolean = true,
)

/**
 * The AR side of measuring: runs on the GL thread, owns the ARCore session, and turns frames into
 * an [EngineUi] the Compose screen draws. Method A: floor from ARCore plane finding, parcel points
 * from the Depth API (or feature points on phones without it), the parcel cut out by a tap or drawn box
 * (MobileSAM, [segmenter]) and the box from [BoxFitter].
 *
 * The engine outlives one parcel: "Paket berikutnya" calls [next], which keeps the session and the floor
 * and marks the parcels already measured.
 */
class MeasureEngine(
    val activity: Activity,
    private val useDepth: Boolean,
    private val photosDir: File,
    private val recordDir: File?,
    private val segmenter: () -> Segmenter? = { null },
) : GLSurfaceView.Renderer {

    private val _ui = MutableStateFlow(EngineUi())
    val ui: StateFlow<EngineUi> = _ui

    private var session: Session? = null
    private val bg = BackgroundRenderer()
    private var w = 1
    private var h = 1
    private var geometryChanged = true

    private val view = FloatArray(16)
    private val proj = FloatArray(16)
    private val vp = FloatArray(16)

    private val commands = ConcurrentLinkedQueue<Cmd>()
    private sealed class Cmd {
        data class Tap(val x: Float, val y: Float) : Cmd()
        data class Box(val x0: Float, val y0: Float, val x1: Float, val y1: Float) : Cmd()
        object Lock : Cmd()
        object Rescan : Cmd()
        data class Next(val label: String) : Cmd()
        data class Torch(val on: Boolean) : Cmd()
        data class Photo(val file: File, val done: (File?) -> Unit) : Cmd()
    }

    private var phase = Phase.SEARCH
    private var frameNo = 0L
    private var planeFrames = 0
    private var tap: Pair<Float, Float>? = null
    private var seed: V3? = null
    private var plane: FloorPlane? = null
    private var live: BoxResult? = null
    private val liveAcc = PointAccumulator(0.01f)
    private val scanAcc = PointAccumulator(0.01f)
    private val sceneAcc = PointAccumulator(0.02f)
    private var others: List<BoxResult> = emptyList()
    private var travel = 0f
    private var lastPos: V3? = null
    private var lastPosTime = 0L
    private var speed = 0f
    private var result: BoxResult? = null
    private var resultData: ResultData? = null
    private var floorWorld: List<V3> = emptyList()
    private var depthWorld: List<V3> = emptyList()
    private var startMs = SystemClock.elapsedRealtime()
    private val recorder = recordDir?.let { Recorder(it) }
    private var attempts = 0
    private var torch = false
    private var torchSupported = true
    private var pickHint = false
    private val done = ArrayList<Pair<V3, String>>()

    // segmentation: one job at a time on a worker thread; the GL thread picks up the finished mask
    private val worker = Executors.newSingleThreadExecutor()
    private var prompt: FloatArray? = null
    private var lockAfterPick = false
    @Volatile private var busy = false
    private val finished = AtomicReference<Pick?>(null)
    private var pick: Pick? = null

    /**
     * A parcel cut out in one camera image. A 3D point belongs to it when it projects inside the (slightly
     * grown) mask as seen from that frame, and lies near the footprint of the depth points inside the mask:
     * the back of the parcel, unseen in that frame, still projects inside; a neighbour standing behind it
     * is outside the footprint.
     */
    private class Pick(
        val mask: Mask, val inv: Pose, val fx: Float, val fy: Float, val cx: Float, val cy: Float,
        val framePoints: List<V3>,
    ) {
        var footprint: List<P2>? = null
        var plane: FloorPlane? = null

        fun projects(p: V3): Boolean {
            val l = inv.transformPoint(floatArrayOf(p.x, p.y, p.z))
            if (l[2] > -0.05f) return false
            return mask[cx + fx * l[0] / -l[2], cy - fy * l[1] / -l[2]]
        }

        fun contains(p: V3): Boolean {
            if (!projects(p)) return false
            val fp = footprint ?: return true
            val q = plane!!.to2d(p)
            return inside(fp, q.a, q.b) || nearEdge(fp, q, 0.04f)
        }
    }

    fun tap(x: Float, y: Float) = commands.add(Cmd.Tap(x, y))
    fun box(x0: Float, y0: Float, x1: Float, y1: Float) = commands.add(Cmd.Box(x0, y0, x1, y1))
    fun lock() = commands.add(Cmd.Lock)
    fun rescan() = commands.add(Cmd.Rescan)
    /** Next parcel in the same session: keep the floor, mark the one just measured with [label]. */
    fun next(label: String) = commands.add(Cmd.Next(label))
    fun torch(on: Boolean) = commands.add(Cmd.Torch(on))
    /** A plain camera photo (for "ukur di hub"), delivered on the main thread. */
    fun photo(file: File, done: (File?) -> Unit) = commands.add(Cmd.Photo(file, done))

    // ------------------------------------------------------------ lifecycle
    fun resume(): String? {
        try {
            if (session == null) {
                val s = Session(activity)
                val c = Config(s)
                c.planeFindingMode = Config.PlaneFindingMode.HORIZONTAL
                c.focusMode = Config.FocusMode.AUTO
                c.updateMode = Config.UpdateMode.LATEST_CAMERA_IMAGE
                c.depthMode = if (useDepth && s.isDepthModeSupported(Config.DepthMode.AUTOMATIC))
                    Config.DepthMode.AUTOMATIC else Config.DepthMode.DISABLED
                s.configure(c)
                session = s
            }
            session?.resume()
            return null
        } catch (e: CameraNotAvailableException) {
            return "Kamera sedang dipakai aplikasi lain. Tutup aplikasi itu lalu coba lagi."
        } catch (e: Exception) {
            return "ARCore tidak bisa dibuka: ${e.javaClass.simpleName}"
        }
    }

    fun pause() { session?.pause() }

    fun close() {
        session?.close(); session = null
        recorder?.close()
        worker.shutdown()
    }

    // ------------------------------------------------------------ GL
    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(0.04f, 0.07f, 0.13f, 1f)
        bg.create()
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        GLES20.glViewport(0, 0, width, height)
        w = width; h = height; geometryChanged = true
    }

    override fun onDrawFrame(gl: GL10?) {
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
        val s = session ?: return
        if (geometryChanged) { s.setDisplayGeometry(rotation(), w, h); geometryChanged = false }
        s.setCameraTextureName(bg.textureId)
        val frame = try { s.update() } catch (e: Exception) { return }
        bg.draw(frame)
        try { step(s, frame) } catch (e: Exception) {
            _ui.value = _ui.value.copy(error = "Galat ukur: ${e.javaClass.simpleName}")
        }
    }

    private fun rotation(): Int =
        if (Build.VERSION.SDK_INT >= 30) activity.display?.rotation ?: 0
        else @Suppress("DEPRECATION") (activity.getSystemService(WindowManager::class.java)).defaultDisplay.rotation

    // ------------------------------------------------------------ per frame
    private fun step(s: Session, frame: Frame) {
        frameNo++
        val cam = frame.camera
        handleCommands(s, frame)

        if (cam.trackingState != TrackingState.TRACKING) {
            val hint = when (cam.trackingFailureReason) {
                TrackingFailureReason.INSUFFICIENT_LIGHT -> Hint.DARK
                TrackingFailureReason.EXCESSIVE_MOTION -> Hint.SLOW
                TrackingFailureReason.INSUFFICIENT_FEATURES -> Hint.TEXTURE
                else -> if (phase == Phase.SEARCH) Hint.MOVE else Hint.LOST
            }
            publish(hint, Overlay())
            return
        }
        cam.getViewMatrix(view, 0)
        cam.getProjectionMatrix(proj, 0, 0.05f, 30f)
        Matrix.multiplyMM(vp, 0, proj, 0, view, 0)
        trackSpeed(cam)

        val planes = s.getAllTrackables(Plane::class.java).filter {
            it.trackingState == TrackingState.TRACKING && it.subsumedBy == null &&
                it.type == Plane.Type.HORIZONTAL_UPWARD_FACING
        }
        val bigPlane = planes.any { it.extentX * it.extentZ > 0.06f }
        if (frameNo % 10 == 0L || floorWorld.isEmpty()) floorWorld = floorDots(planes)

        when (phase) {
            Phase.SEARCH -> {
                planeFrames = if (bigPlane) planeFrames + 1 else 0
                if (planeFrames > 25) phase = Phase.SELECT
                publish(if (bigPlane) Hint.NONE else Hint.MOVE, Overlay(floorDots = project(floorWorld), marks = marks(), markLabels = done.map { it.second }))
            }
            Phase.SELECT -> select(frame, cam, planes)
            Phase.SCAN -> scan(frame, cam)
            Phase.RESULT -> publish(Hint.NONE, Overlay(box = projectBox(result)))
        }
    }

    private fun handleCommands(s: Session, frame: Frame) {
        while (true) {
            when (val c = commands.poll() ?: return) {
                is Cmd.Tap -> if (phase == Phase.SELECT || phase == Phase.SEARCH) {
                    tap = c.x to c.y
                    if (phase == Phase.SELECT && segmenter() != null) prompt = floatArrayOf(c.x, c.y)
                }
                is Cmd.Box -> if (phase == Phase.SELECT && segmenter() != null) {
                    tap = (c.x0 + c.x1) / 2 to (c.y0 + c.y1) / 2
                    prompt = floatArrayOf(c.x0, c.y0, c.x1, c.y1)
                }
                Cmd.Lock -> if (phase == Phase.SELECT) {
                    when {
                        pick == null && segmenter() != null -> { val r = reticle(); prompt = floatArrayOf(r.first, r.second); lockAfterPick = true }
                        busy -> lockAfterPick = true
                        live != null && seed != null && plane != null -> startScan(frame)
                    }
                }
                Cmd.Rescan -> {
                    if (phase == Phase.RESULT || phase == Phase.SCAN) attempts++
                    resetPick()
                    phase = Phase.SELECT
                    _ui.value = EngineUi(phase = Phase.SELECT, planeFound = true, attempts = attempts, torch = torch, torchSupported = torchSupported)
                }
                is Cmd.Next -> {
                    result?.let { r -> done.add(centre(r.topCorners) to c.label) }
                    attempts = 0
                    resetPick()
                    startMs = SystemClock.elapsedRealtime()
                    phase = if (planeFrames > 25) Phase.SELECT else Phase.SEARCH
                    _ui.value = EngineUi(phase = phase, planeFound = phase == Phase.SELECT, torch = torch, torchSupported = torchSupported)
                }
                is Cmd.Torch -> {
                    val cfg = s.config
                    cfg.flashMode = if (c.on) Config.FlashMode.TORCH else Config.FlashMode.OFF
                    try {
                        if (!s.isSupported(cfg)) throw IllegalStateException()
                        s.configure(cfg); torch = c.on
                    } catch (e: Exception) { torchSupported = false; torch = false }
                    _ui.value = _ui.value.copy(torch = torch, torchSupported = torchSupported)
                }
                is Cmd.Photo -> {
                    val f = Snapshot.save(frame, frame.camera, null, c.file)
                    Handler(Looper.getMainLooper()).post { c.done(f) }
                }
            }
        }
    }

    private fun resetPick() {
        result = null; resultData = null; live = null; pick = null; prompt = null; lockAfterPick = false
        finished.set(null); seed = null; pickHint = false
        scanAcc.clear(); liveAcc.clear(); tap = null
    }

    private fun reticle() = tap ?: (w / 2f to h * 0.40f)

    private fun select(frame: Frame, cam: Camera, planes: List<Plane>) {
        val (px, py) = reticle()
        val pts = if (useDepth && frameNo % 2 == 0L) framePoints(frame, cam) else null

        // a finished cut-out replaces the crosshair pick
        finished.getAndSet(null)?.let { p -> adopt(p, planes) }
        prompt?.let { pr -> if (!busy) { prompt = null; startPick(frame, cam, pr, pts) } }

        val pk = pick
        if (pk == null && frameNo % 3 == 0L) {
            val hit = frame.hitTest(px, py).firstOrNull { it.trackable !is Plane }
                ?: frame.hitTest(px, py).firstOrNull()
            val p = hit?.hitPose
            val sd = p?.let { V3(it.tx(), it.ty(), it.tz()) }
            val fl = sd?.let { choosePlane(planes, it) }
            if (sd != null && fl != null && fl.height(sd) > 0.012f) {
                if (seed == null || hypot(sd.x - seed!!.x, sd.z - seed!!.z) > 0.08f) liveAcc.clear()
                seed = sd; plane = fl
            } else { seed = null; live = null }
        }
        val sd = seed; val fl = plane
        if (sd != null && fl != null) {
            if (liveAcc.frames > 12) liveAcc.clear()
            addPoints(frame, cam, liveAcc, fl, sd, pts = pts)
            if (frameNo % 3 == 0L) {
                val seg = BoxFitter.segment(liveAcc.points(), fl, sd, cell = if (useDepth) 0.015f else 0.03f,
                    minH = 0.02f, minPerCell = if (useDepth) 2 else 1)
                live = seg?.let { BoxFitter.fit(it) }?.takeIf { plausible(it) } ?: if (pk != null) live else null
            }
        }
        if (lockAfterPick && pk != null && live != null && !busy) { lockAfterPick = false; startScan(frame); return }

        // the other parcels around: coarse clusters from a rolling cloud of the scene
        if (useDepth && pts != null) {
            val floor = fl ?: lowestPlane(planes)
            if (floor != null) {
                if (sceneAcc.frames > 40) sceneAcc.clear()
                val c2 = cam.pose
                val near = V3(c2.tx(), c2.ty(), c2.tz())
                for (p in pts) if (floor.height(p) > 0.03f && (p - near).norm() < 2.5f) sceneAcc.add(p.x, p.y, p.z)
                sceneAcc.endFrame()
                if (frameNo % 16 == 0L) {
                    val centre = sd ?: floor.to3d(floor.to2d(near))
                    others = BoxFitter.clusters(sceneAcc.points(2), floor, centre)
                }
            }
        }
        val lv = live
        val otherOutlines = others.filter { o -> sd == null || !containsSeed(o, sd, fl) }.map { project(it.topCorners) }

        val hint = when {
            pickHint -> Hint.PICK_FAILED
            lv == null -> Hint.NO_PARCEL
            stacked(fl, planes) -> Hint.STACKED
            else -> Hint.NONE
        }
        publish(hint, Overlay(floorDots = project(floorWorld), outline = lv?.let { projectPoly(it.outline) },
            others = otherOutlines, marks = marks(), markLabels = done.map { it.second }),
            targetFound = lv != null, reticle = if (pk == null) px to py else null)
    }

    /** Hands the current camera image and a tap or box (view pixels) to the segmentation model. */
    private fun startPick(frame: Frame, cam: Camera, pr: FloatArray, pts: List<V3>?) {
        val sam = segmenter() ?: return
        val img = try { frame.acquireCameraImage() } catch (e: NotYetAvailableException) { prompt = pr; return }
        val argb: IntArray; val iw: Int; val ih: Int
        try { argb = Yuv.toArgb(img); iw = img.width; ih = img.height } finally { img.close() }
        val ip = FloatArray(pr.size)
        frame.transformCoordinates2d(Coordinates2d.VIEW, pr, Coordinates2d.IMAGE_PIXELS, ip)
        val intr = cam.imageIntrinsics
        val f = intr.focalLength; val pp = intr.principalPoint; val dims = intr.imageDimensions
        val sx = iw.toFloat() / dims[0]; val sy = ih.toFloat() / dims[1]
        val inv = cam.pose.inverse()
        val framePts = pts ?: if (useDepth) framePoints(frame, cam) else featurePoints(frame)
        busy = true
        worker.execute {
            try {
                val e = sam.embed(argb, iw, ih)
                val m = if (ip.size == 2) sam.tap(e, ip[0], ip[1]) else sam.box(e, ip[0], ip[1], ip[2], ip[3])
                val grown = m.largestPart().dilate(max(2, iw / 200))
                finished.set(Pick(grown, inv, f[0] * sx, f[1] * sy, pp[0] * sx, pp[1] * sy, framePts))
            } catch (e: Throwable) {
                pickHint = true
            } finally { busy = false }
        }
        publish(Hint.NONE, _ui.value.overlay, selecting = true)
    }

    /** A finished cut-out becomes the parcel: seed, surface, footprint fence. */
    private fun adopt(p: Pick, planes: List<Plane>) {
        val inMask = p.framePoints.filter { p.projects(it) }
        if (inMask.size < (if (useDepth) 40 else 4)) { pickHint = true; lockAfterPick = false; return }
        val ys = inMask.map { it.y }.sorted()
        val top = ys[(ys.size * 0.9f).toInt().coerceAtMost(ys.size - 1)]
        val sd = V3(inMask.map { it.x }.average().toFloat(), top, inMask.map { it.z }.average().toFloat())
        val fl = choosePlane(planes, sd) ?: run { pickHint = true; lockAfterPick = false; return }
        val above = inMask.filter { fl.height(it) > 0.02f }
        if (above.size >= (if (useDepth) 30 else 4)) p.footprint = convexHull(above.map { fl.to2d(it) })
        p.plane = fl
        pick = p; seed = sd; plane = fl; pickHint = false
        liveAcc.clear(); live = null
        // reuse this frame's points straight away so the outline appears without waiting
        for (q in inMask) if (p.contains(q)) liveAcc.add(q.x, q.y, q.z)
        liveAcc.endFrame()
        BoxFitter.segment(liveAcc.points(), fl, sd, cell = if (useDepth) 0.015f else 0.03f, minH = 0.02f, minPerCell = 1)
            ?.let { BoxFitter.fit(it) }?.takeIf { plausible(it) }?.let { live = it }
    }

    private fun startScan(frame: Frame) {
        phase = Phase.SCAN
        scanAcc.clear(); travel = 0f
        val pose = frame.camera.pose
        lastPos = V3(pose.tx(), pose.ty(), pose.tz())
        recorder?.begin(seed!!, plane!!)
    }

    private fun scan(frame: Frame, cam: Camera) {
        val sd = seed ?: return
        val fl = plane ?: return
        val pose = cam.pose
        val pos = V3(pose.tx(), pose.ty(), pose.tz())
        lastPos?.let { travel += (pos - it).norm() }
        lastPos = pos
        val added = addPoints(frame, cam, scanAcc, fl, sd, record = true)
        if (added > (if (useDepth) 60 else 4)) scanAcc.endFrame()

        if (frameNo % 4 == 0L) {
            val seg = BoxFitter.segment(scanAcc.points(if (useDepth) 2 else 1), fl, sd, cell = if (useDepth) 0.015f else 0.03f,
                minH = 0.02f, minPerCell = if (useDepth) 2 else 1)
            live = seg?.let { BoxFitter.fit(it) }?.takeIf { plausible(it) } ?: live
            depthWorld = seg?.let { sg -> sg.pts2.indices.filter { it % max(1, sg.pts2.size / 450) == 0 }
                .map { sg.plane.to3d(sg.pts2[it], sg.heights[it]) } } ?: emptyList()
        }
        val progress = min(1f, min(scanAcc.frames / 18f, travel / 0.18f))
        val outline = live?.let { projectPoly(it.outline) }
        val cut = outline != null && edgeCut(outline)
        val hint = when { speed > 0.7f -> Hint.SLOW; cut -> Hint.BACK; else -> Hint.SWEEP }

        if (progress >= 1f) {
            val seg = BoxFitter.segment(scanAcc.points(if (useDepth) 2 else 1), fl, sd, cell = if (useDepth) 0.015f else 0.03f,
                minH = 0.02f, minPerCell = if (useDepth) 2 else 1)
            val r = seg?.let { BoxFitter.fit(it) }?.takeIf { plausible(it) }
            if (r == null) {
                attempts++
                phase = Phase.SELECT; scanAcc.clear()
                publish(Hint.FAILED, Overlay())
                return
            }
            finish(frame, cam, r, cut)
            return
        }
        publish(hint, Overlay(depthDots = project(depthWorld), outline = outline), progress = progress)
    }

    private fun finish(frame: Frame, cam: Camera, r: BoxResult, cut: Boolean) {
        result = r
        live = r
        var conf = BoxFitter.confidence(r, scanAcc.frames, useDepth)
        if (cut) conf = min(conf, 60)
        val status = if (conf >= 75) Status.OK else Status.CHECK
        val id = "m${System.currentTimeMillis()}"
        val photo = Snapshot.save(frame, cam, r, File(photosDir, "$id.jpg"))
        val rec = recorder?.finish(r, conf)
        resultData = ResultData(
            lengthCm = round1(r.lengthM * 100), widthCm = round1(r.widthM * 100), heightCm = round1(r.heightM * 100),
            confidence = conf, status = status,
            seconds = (SystemClock.elapsedRealtime() - startMs) / 1000.0,
            photo = photo?.path, recording = rec?.path, mode = if (useDepth) Mode.AR_FULL else Mode.AR_BASIC)
        phase = Phase.RESULT
        publish(Hint.NONE, Overlay(box = projectBox(r)))
    }

    private fun round1(x: Float) = Math.round(x * 10.0) / 10.0

    // ------------------------------------------------------------ points
    /** Adds this frame's points near the parcel (and inside the picked cut-out) to [acc]; returns how many. */
    private fun addPoints(frame: Frame, cam: Camera, acc: PointAccumulator, fl: FloorPlane, sd: V3,
                          record: Boolean = false, pts: List<V3>? = null): Int {
        val s2 = fl.to2d(sd)
        val pk = pick
        var n = 0
        val sink = { x: Float, y: Float, z: Float ->
            val p = V3(x, y, z)
            val hh = fl.height(p)
            if (hh > -0.02f && hh < 1.6f) {
                val q = fl.to2d(p)
                if (hypot(q.a - s2.a, q.b - s2.b) < 1.2f && (pk == null || hh < 0.02f || pk.contains(p))) { acc.add(x, y, z); n++ }
            }
        }
        if (useDepth) {
            if (pts != null) { for (p in pts) sink(p.x, p.y, p.z); return n }
            if (frameNo % 2 != 0L) return 0
            depthPoints(frame, cam, sink, if (record) recorder else null)
        } else {
            for (p in featurePoints(frame)) sink(p.x, p.y, p.z)
        }
        return n
    }

    private fun framePoints(frame: Frame, cam: Camera): List<V3> {
        val out = ArrayList<V3>(3000)
        depthPoints(frame, cam, { x, y, z -> out.add(V3(x, y, z)) }, null)
        return out
    }

    private fun featurePoints(frame: Frame): List<V3> {
        val out = ArrayList<V3>()
        val pc = frame.acquirePointCloud()
        try {
            val b = pc.points
            while (b.remaining() >= 4) {
                val x = b.get(); val y = b.get(); val z = b.get(); val c = b.get()
                if (c >= 0.2f) out.add(V3(x, y, z))
            }
        } finally { pc.close() }
        return out
    }

    private fun depthPoints(frame: Frame, cam: Camera, sink: (Float, Float, Float) -> Unit, rec: Recorder?) {
        val depth = try { frame.acquireRawDepthImage16Bits() } catch (e: NotYetAvailableException) { return }
        val conf = try { frame.acquireRawDepthConfidenceImage() } catch (e: NotYetAvailableException) { depth.close(); return }
        try {
            val dw = depth.width; val dh = depth.height
            val dp = depth.planes[0]; val db = dp.buffer.order(ByteOrder.LITTLE_ENDIAN)
            val cp = conf.planes[0]; val cb = cp.buffer
            val intr = cam.textureIntrinsics
            val f = intr.focalLength; val pp = intr.principalPoint; val dims = intr.imageDimensions
            val fx = f[0] * dw / dims[0]; val fy = f[1] * dh / dims[1]
            val cx = pp[0] * dw / dims[0]; val cy = pp[1] * dh / dims[1]
            val pose = cam.pose
            val local = FloatArray(3)
            val world = FloatArray(3)
            for (v in 0 until dh step 2) for (u in 0 until dw step 2) {
                val d = db.getShort(v * dp.rowStride + u * dp.pixelStride).toInt() and 0xFFFF
                if (d == 0) continue
                val c = cb.get(v * cp.rowStride + u * cp.pixelStride).toInt() and 0xFF
                if (c < 90) continue
                val z = d / 1000f
                if (z < 0.15f || z > 3f) continue
                local[0] = (u - cx) * z / fx; local[1] = -(v - cy) * z / fy; local[2] = -z
                pose.transformPoint(local, 0, world, 0)
                sink(world[0], world[1], world[2])
            }
            rec?.frame(frame, cam, depth, conf, fx, fy, cx, cy)
        } finally {
            depth.close(); conf.close()
        }
    }

    // ------------------------------------------------------------ helpers
    /** The surface under the parcel: the highest horizontal plane below the picked point. */
    private fun choosePlane(planes: List<Plane>, sd: V3): FloorPlane? =
        planes.filter { it.centerPose.ty() < sd.y - 0.012f && it.centerPose.ty() > sd.y - 1.6f }
            .maxByOrNull { it.centerPose.ty() }
            ?.let { toFloor(it) }

    private fun lowestPlane(planes: List<Plane>): FloorPlane? =
        planes.filter { it.extentX * it.extentZ > 0.06f }.minByOrNull { it.centerPose.ty() }?.let { toFloor(it) }

    private fun toFloor(p: Plane): FloorPlane {
        val c = p.centerPose; val yA = c.yAxis
        return FloorPlane(V3(c.tx(), c.ty(), c.tz()), V3(yA[0], yA[1], yA[2]))
    }

    private fun containsSeed(o: BoxResult, sd: V3, fl: FloorPlane?): Boolean {
        val p = fl ?: return false
        val q = p.to2d(sd)
        return inside(o.floorCorners.map { p.to2d(it) }, q.a, q.b)
    }

    private fun centre(c: List<V3>) = V3(c.map { it.x }.average().toFloat(), c.map { it.y }.average().toFloat(), c.map { it.z }.average().toFloat())

    private fun marks(): FloatArray = project(done.map { it.first })

    /** A plane right under the parcel that is not the floor the courier set it on: probably another parcel. */
    private fun stacked(fl: FloorPlane?, planes: List<Plane>): Boolean {
        if (fl == null) return false
        val lowest = planes.minOfOrNull { it.centerPose.ty() } ?: return false
        return fl.origin.y - lowest > 0.15f && planes.size > 1 &&
            planes.first { it.centerPose.ty() == lowest }.let { it.extentX * it.extentZ > 0.4f }
    }

    private fun plausible(r: BoxResult) =
        r.lengthM in 0.03f..1.6f && r.widthM >= 0.02f && r.heightM in 0.012f..1.6f

    private fun trackSpeed(cam: Camera) {
        val t = SystemClock.elapsedRealtime()
        val p = cam.pose
        val pos = V3(p.tx(), p.ty(), p.tz())
        val last = lastSpeedPos
        if (last != null && t > lastPosTime) speed = 0.8f * speed + 0.2f * ((pos - last).norm() * 1000f / (t - lastPosTime))
        lastSpeedPos = pos; lastPosTime = t
    }
    private var lastSpeedPos: V3? = null

    private fun floorDots(planes: List<Plane>): List<V3> {
        val out = ArrayList<V3>()
        for (p in planes) {
            val poly = p.polygon
            val xs = FloatArray(poly.limit() / 2); val zs = FloatArray(poly.limit() / 2)
            for (i in xs.indices) { xs[i] = poly.get(2 * i); zs[i] = poly.get(2 * i + 1) }
            if (xs.size < 3) continue
            var x = xs.min()
            val local = FloatArray(3); val world = FloatArray(3)
            while (x <= xs.max()) {
                var z = zs.min()
                while (z <= zs.max()) {
                    if (insideAny(xs, zs, x, z)) {
                        local[0] = x; local[1] = 0f; local[2] = z
                        p.centerPose.transformPoint(local, 0, world, 0)
                        out.add(V3(world[0], world[1], world[2]))
                    }
                    z += 0.09f
                }
                x += 0.09f
            }
            if (out.size > 700) break
        }
        return out
    }

    private fun insideAny(xs: FloatArray, zs: FloatArray, x: Float, z: Float): Boolean {
        var c = false; var j = xs.size - 1
        for (i in xs.indices) {
            if ((zs[i] > z) != (zs[j] > z) && x < (xs[j] - xs[i]) * (z - zs[i]) / (zs[j] - zs[i]) + xs[i]) c = !c
            j = i
        }
        return c
    }

    private val tmp4 = FloatArray(4)
    private val out4 = FloatArray(4)
    private fun projectOne(p: V3, dst: FloatArray, at: Int): Boolean {
        tmp4[0] = p.x; tmp4[1] = p.y; tmp4[2] = p.z; tmp4[3] = 1f
        Matrix.multiplyMV(out4, 0, vp, 0, tmp4, 0)
        if (out4[3] <= 0.01f) { dst[at] = Float.NaN; dst[at + 1] = Float.NaN; return false }
        dst[at] = (out4[0] / out4[3] + 1f) * 0.5f * w
        dst[at + 1] = (1f - out4[1] / out4[3]) * 0.5f * h
        return true
    }

    private fun project(pts: List<V3>): FloatArray {
        val a = FloatArray(pts.size * 2)
        pts.forEachIndexed { i, p -> projectOne(p, a, 2 * i) }
        return a
    }

    private fun projectPoly(pts: List<V3>) = project(pts)

    private fun projectBox(r: BoxResult?): FloatArray? = r?.let { project(it.floorCorners + it.topCorners) }

    private fun edgeCut(poly: FloatArray): Boolean {
        var i = 0
        while (i < poly.size) {
            val x = poly[i]; val y = poly[i + 1]
            if (x.isNaN() || x < w * 0.02f || x > w * 0.98f || y < h * 0.06f || y > h * 0.80f) return true
            i += 2
        }
        return false
    }

    private fun publish(hint: Hint, overlay: Overlay, progress: Float = _ui.value.progress,
                        targetFound: Boolean = _ui.value.targetFound, reticle: Pair<Float, Float>? = null,
                        selecting: Boolean = busy) {
        _ui.value = EngineUi(
            phase = phase,
            planeFound = phase != Phase.SEARCH || planeFrames > 0,
            targetFound = targetFound,
            progress = if (phase == Phase.SCAN) progress else if (phase == Phase.RESULT) 1f else 0f,
            hint = hint, overlay = overlay, live = live, result = resultData, reticle = reticle,
            selecting = selecting || prompt != null, picked = pick != null, attempts = attempts,
            torch = torch, torchSupported = torchSupported,
        )
    }

    companion object {
        /** Within [d] of a polygon's edge. */
        internal fun nearEdge(poly: List<P2>, q: P2, d: Float): Boolean {
            for (i in poly.indices) {
                val a = poly[i]; val b = poly[(i + 1) % poly.size]
                val ex = b.a - a.a; val ey = b.b - a.b
                val l2 = ex * ex + ey * ey
                val t = if (l2 < 1e-9f) 0f else (((q.a - a.a) * ex + (q.b - a.b) * ey) / l2).coerceIn(0f, 1f)
                if (hypot(q.a - (a.a + t * ex), q.b - (a.b + t * ey)) <= d) return true
            }
            return false
        }
    }
}
