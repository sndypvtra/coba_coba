package id.ukurpaket.app.photo

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.hardware.camera2.TotalCaptureResult
import android.hardware.camera2.CaptureResult
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.params.MeteringRectangle
import android.media.ImageReader
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.util.Size
import android.view.Surface
import id.ukurpaket.app.dt.SweepRecorder
import kotlin.math.asin
import kotlin.math.min
import kotlin.math.sqrt

/**
 * The photo mode's camera: preview, and one still frame taken when the phone is held still, with what the measurement
 * needs from that moment: the lens (Camera2 facts) and which way is up (the accelerometer averaged over the last 0,4 s,
 * so the hand's shake averages out). No gyroscope is needed (the DT50's sends nothing).
 */
class PhotoCamera(private val ctx: Context, private val cb: Callback) {
    interface Callback {
        fun onLive(s: Live)
        fun onError(msg: String)
    }

    /** For the screen: how far down the camera looks, whether the phone is still, the picture's brightness. */
    data class Live(val downDeg: Float?, val still: Boolean, val brightness: Double, val size: String)

    /** One still: the NV21 frame (sensor orientation), the lens of the upright full picture, the mean acceleration. */
    class Shot(val nv21: ByteArray, val sw: Int, val sh: Int, val rotation: Int, val k: Intrinsics,
               val accel: FloatArray, val accelSpread: Float, val still: Boolean, val timeMs: Long,
               /** Where the autofocus stood (recorded for the PC: a second, physical clue to the distance). */
               val focus: FocusInfo? = null,
               /** Frames through a series of lens positions taken right after (FocusSweep), or null. */
               val sweep: SweepData? = null)

    private val thread = HandlerThread("photo-cam").apply { start() }
    private val handler = Handler(thread.looper)
    private val sm = ctx.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as CameraManager
    private var device: CameraDevice? = null
    private var session: CameraCaptureSession? = null
    private var reader: ImageReader? = null
    private var surface: Surface? = null
    private var chars: CameraCharacteristics? = null
    var size = Size(1280, 960); private set
    val rotation get() = chars?.get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 90
    @Volatile private var closed = false

    // accelerometer: the last 0,4 s
    private val acc = ArrayDeque<FloatArray>()
    private val accT = ArrayDeque<Long>()
    @Volatile private var brightness = 128.0
    private var frames = 0
    private var lastLive = 0L

    // the autofocus of the last preview frame
    @Volatile private var focusDiopters: Float? = null
    @Volatile private var afState: Int? = null

    /**
     * Each frame's own lens and autofocus, by its sensor timestamp: an image is judged by what the lens did for it, not by
     * the latest result (images come a few frames behind their results: 0.4.5 could take a frame the lens was still
     * moving in). Results and images both arrive on [handler].
     */
    private class FrameMeta(val focus: Float?, val af: Int?, val lens: Int?)
    private val meta = object : LinkedHashMap<Long, FrameMeta>() {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Long, FrameMeta>?) = size > 40
    }
    private val frameCb = object : CameraCaptureSession.CaptureCallback() {
        override fun onCaptureCompleted(s: CameraCaptureSession, r: CaptureRequest, res: TotalCaptureResult) {
            val fm = FrameMeta(res.get(CaptureResult.LENS_FOCUS_DISTANCE), res.get(CaptureResult.CONTROL_AF_STATE), res.get(CaptureResult.LENS_STATE))
            res.get(CaptureResult.SENSOR_TIMESTAMP)?.let { meta[it] = fm }
            focusDiopters = fm.focus; afState = fm.af
            if (pending != null) process()
        }
    }

    // the capture: the photo first, then (when the lens can be moved by hand) the focus sweep
    private enum class Phase { IDLE, SHOT, SWEEP }
    private var phase = Phase.IDLE
    private var base: Shot? = null
    private val swept = ArrayList<SweepFrame>()
    private var targets = FloatArray(0)
    private var target = 0
    private var stepSince = 0L
    private var sweepSince = 0L

    // the preview request, kept to send the autofocus trigger; whether a lock was asked for this photo
    private var request: CaptureRequest.Builder? = null
    @Volatile private var locking = false

    @Volatile private var pending: ((Shot) -> Unit)? = null
    @Volatile private var pendingSince = 0L

    @SuppressLint("MissingPermission")
    fun open(texture: SurfaceTexture) {
        try {
            val id = cm.cameraIdList.firstOrNull { cm.getCameraCharacteristics(it).get(CameraCharacteristics.LENS_FACING) == CameraMetadata.LENS_FACING_BACK }
                ?: cm.cameraIdList.first()
            val c = cm.getCameraCharacteristics(id).also { chars = it }
            val sizes = c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)!!.getOutputSizes(ImageFormat.YUV_420_888)
            size = SweepRecorder.pickSize(sizes.map { it.width to it.height })?.let { Size(it.first, it.second) } ?: sizes.first()
            texture.setDefaultBufferSize(size.width, size.height)
            surface = Surface(texture)
            reader = ImageReader.newInstance(size.width, size.height, ImageFormat.YUV_420_888, 3).apply {
                setOnImageAvailableListener({ r -> onImage(r) }, handler)
            }
            cm.openCamera(id, object : CameraDevice.StateCallback() {
                override fun onOpened(d: CameraDevice) { if (closed) { d.close(); return }; device = d; startSession() }
                override fun onDisconnected(d: CameraDevice) { d.close(); device = null }
                override fun onError(d: CameraDevice, e: Int) { d.close(); device = null; cb.onError("Kamera tidak bisa dibuka (kode $e).") }
            }, handler)
        } catch (e: Exception) { cb.onError("Kamera tidak bisa dibuka: ${e.message}") }
        sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)?.let { sm.registerListener(accListener, it, SensorManager.SENSOR_DELAY_GAME, handler) }
            ?: cb.onError("HP ini tidak punya accelerometer: mode foto tidak bisa dipakai.")
    }

    @Suppress("DEPRECATION")
    private fun startSession() {
        val d = device ?: return
        d.createCaptureSession(listOf(surface!!, reader!!.surface), object : CameraCaptureSession.StateCallback() {
            override fun onConfigured(s: CameraCaptureSession) {
                session = s
                try {
                    val b = d.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW)
                    b.addTarget(surface!!); b.addTarget(reader!!.surface)
                    val af = chars?.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES)?.toList().orEmpty()
                    if (CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_PICTURE in af) b.set(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_PICTURE)
                    // the autofocus measures the middle of the picture (its distance is a clue to the scale: PhotoMeasure)
                    // a wide middle (half the picture each way): it then holds the object's outline too, whose contrast a plain
                    // or glossy object's surface lacks
                    val act = chars?.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)
                    if (act != null && (chars?.get(CameraCharacteristics.CONTROL_MAX_REGIONS_AF) ?: 0) > 0) {
                        val w = act.width() / 4; val h = act.height() / 4
                        b.set(CaptureRequest.CONTROL_AF_REGIONS, arrayOf(MeteringRectangle(act.centerX() - w, act.centerY() - h, 2 * w, 2 * h, MeteringRectangle.METERING_WEIGHT_MAX)))
                    }
                    // the lens must not move against the sensor: the measurement uses the factory focal length
                    b.set(CaptureRequest.CONTROL_VIDEO_STABILIZATION_MODE, CameraMetadata.CONTROL_VIDEO_STABILIZATION_MODE_OFF)
                    request = b
                    s.setRepeatingRequest(b.build(), frameCb, handler)
                } catch (e: Exception) { cb.onError("Kamera berhenti: ${e.message}") }
            }
            override fun onConfigureFailed(s: CameraCaptureSession) {
                if (size.width > 640) {                       // some cameras cannot stream preview + 1280x960 YUV
                    size = Size(640, 480)
                    reader?.close()
                    reader = ImageReader.newInstance(size.width, size.height, ImageFormat.YUV_420_888, 3).apply { setOnImageAvailableListener({ r -> onImage(r) }, handler) }
                    startSession()
                } else cb.onError("Sesi kamera gagal dibuat.")
            }
        }, handler)
    }

    private val accListener = object : SensorEventListener {
        override fun onSensorChanged(e: SensorEvent) {
            acc.addLast(floatArrayOf(e.values[0], e.values[1], e.values[2])); accT.addLast(e.timestamp)
            while (accT.isNotEmpty() && e.timestamp - accT.first() > 400_000_000L) { acc.removeFirst(); accT.removeFirst() }
            val now = SystemClock.elapsedRealtime()
            if (now - lastLive > 100) {
                lastLive = now
                val (m, sp) = accelNow()
                cb.onLive(Live(m?.let { downDeg(it) }, m != null && isStill(m, sp), brightness, "${size.width}×${size.height}"))
            }
        }
        override fun onAccuracyChanged(s: Sensor?, a: Int) {}
    }

    /** Mean acceleration over the last 0,4 s and how much it wandered (rms, m/s²). */
    private fun accelNow(): Pair<FloatArray?, Float> {
        if (acc.size < 5) return null to 99f
        val m = FloatArray(3)
        for (a in acc) for (i in 0..2) m[i] += a[i] / acc.size
        var s = 0f
        for (a in acc) for (i in 0..2) s += (a[i] - m[i]) * (a[i] - m[i])
        return m to sqrt(s / acc.size)
    }

    /** Takes the next frame once the phone is still (at most [maxWaitMs] of waiting; then as it is). */
    fun capture(maxWaitMs: Long = 2500, onShot: (Shot) -> Unit) {
        handler.post {
            pending = onShot; pendingSince = SystemClock.elapsedRealtime(); phase = Phase.SHOT
            locking = afTrigger(CameraMetadata.CONTROL_AF_TRIGGER_START)
        }
        this.maxWait = maxWaitMs
    }

    /** The lens can be set by hand: autofocus off is offered and the camera has a focus range. */
    private fun canSweep(): Boolean {
        val c = chars ?: return false
        val af = c.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES)?.toList().orEmpty()
        return CameraMetadata.CONTROL_AF_MODE_OFF in af && (c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE) ?: 0f) > 0f
    }

    /**
     * Starts the focus sweep: the lens set by hand to 16 positions from far to near (spaced evenly in the log of the
     * camera's dioptres, up to 70 % of its closest focus), a frame kept at each once the lens has settled there.
     */
    private fun startSweep(): Boolean {
        if (!canSweep()) return false
        val b = request ?: return false; val s = session ?: return false
        val near = min(14f, 0.7f * (chars?.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE) ?: 14f)); val far = 0.3f
        targets = FloatArray(SWEEP_STEPS) { far * Math.pow((near / far).toDouble(), it / (SWEEP_STEPS - 1.0)).toFloat() }
        target = 0; swept.clear()
        return try {
            b.set(CaptureRequest.CONTROL_AF_TRIGGER, CameraMetadata.CONTROL_AF_TRIGGER_IDLE)
            b.set(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_OFF)
            b.set(CaptureRequest.LENS_FOCUS_DISTANCE, targets[0])
            s.setRepeatingRequest(b.build(), frameCb, handler)
            stepSince = SystemClock.elapsedRealtime(); sweepSince = stepSince; true
        } catch (e: Exception) { restoreAf(); false }
    }

    private fun nextTarget() {
        target++
        stepSince = SystemClock.elapsedRealtime()
        if (target >= targets.size) return
        try { request?.let { b -> b.set(CaptureRequest.LENS_FOCUS_DISTANCE, targets[target]); session?.setRepeatingRequest(b.build(), frameCb, handler) } }
        catch (e: Exception) { target = targets.size }
    }

    /** The continuous autofocus back on. */
    private fun restoreAf() {
        val b = request ?: return
        try {
            val af = chars?.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES)?.toList().orEmpty()
            if (CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_PICTURE in af) b.set(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_PICTURE)
            b.set(CaptureRequest.CONTROL_AF_TRIGGER, CameraMetadata.CONTROL_AF_TRIGGER_IDLE)
            session?.setRepeatingRequest(b.build(), frameCb, handler)
        } catch (e: Exception) { }
    }

    /** The luma plane of a YUV image, tightly packed (width x height). */
    private fun yPlane(img: android.media.Image): ByteArray {
        val pl = img.planes[0]; val buf = pl.buffer; val w = img.width; val h = img.height
        val out = ByteArray(w * h)
        if (pl.pixelStride == 1 && pl.rowStride == w) { buf.rewind(); buf.get(out, 0, w * h); return out }
        for (y in 0 until h) for (x in 0 until w) out[y * w + x] = buf.get(y * pl.rowStride + x * pl.pixelStride)
        return out
    }

    /**
     * Sends an autofocus trigger: START makes the continuous autofocus finish its search and lock (focused or not: the
     * camera says which), CANCEL lets it run again. False when the camera has no autofocus or no session.
     */
    private fun afTrigger(t: Int): Boolean {
        val b = request ?: return false; val s = session ?: return false
        val af = chars?.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES)?.toList().orEmpty()
        if (CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_PICTURE !in af) return false
        return try {
            b.set(CaptureRequest.CONTROL_AF_TRIGGER, t); s.capture(b.build(), frameCb, handler)
            b.set(CaptureRequest.CONTROL_AF_TRIGGER, CameraMetadata.CONTROL_AF_TRIGGER_IDLE); true
        } catch (e: Exception) { false }
    }
    @Volatile private var maxWait = 2000L

    /**
     * Frames waiting for their capture result (by sensor timestamp; the result may come before or after the image):
     * while taking the photo the whole NV21 frame, during the sweep its luma. At most a few, the oldest dropped.
     */
    private class Held(val data: ByteArray, val w: Int, val h: Int)
    private val held = object : LinkedHashMap<Long, Held>() {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Long, Held>?) = size > 4
    }

    private fun onImage(r: ImageReader) {
        val img = try { r.acquireNextImage() } catch (e: Exception) { null } ?: return
        try {
            if (++frames % 8 == 1) brightness = SweepRecorder.meanLuma(img)
            if (pending == null) return
            when (phase) {
                Phase.SHOT -> held[img.timestamp] = Held(SweepRecorder.toNv21(img), img.width, img.height)
                Phase.SWEEP -> held[img.timestamp] = Held(yPlane(img), img.width, img.height)
                Phase.IDLE -> return
            }
        } finally { img.close() }
        process()
    }

    /** Matches held frames with their results and moves the capture on; called on every image and every result. */
    private fun process() {
        val p = pending ?: return
        val now = SystemClock.elapsedRealtime()
        when (phase) {
            Phase.SHOT -> {
                val (m, sp) = accelNow()
                val still = m != null && isStill(m, sp)
                // a frame whose own autofocus is locked after the trigger (focused, or the camera saying it could not),
                // else settled, with its lens not moving; a lens still searching says nothing about the distance
                var pick: Long? = null
                for ((ts, _) in held) {
                    val fm = meta[ts] ?: continue
                    val lensStill = fm.lens == null || fm.lens == CaptureResult.LENS_STATE_STATIONARY
                    val focused = fm.af.let {
                        if (locking) it == CaptureResult.CONTROL_AF_STATE_FOCUSED_LOCKED || it == CaptureResult.CONTROL_AF_STATE_NOT_FOCUSED_LOCKED
                        else it == null || it == CaptureResult.CONTROL_AF_STATE_PASSIVE_FOCUSED || it == CaptureResult.CONTROL_AF_STATE_FOCUSED_LOCKED ||
                            it == CaptureResult.CONTROL_AF_STATE_INACTIVE
                    }
                    if (still && focused && lensStill) pick = ts
                }
                if (pick == null && now - pendingSince >= maxWait) pick = held.keys.lastOrNull()      // waited enough: as it is
                val ts = pick ?: return
                val f = held[ts]!!
                held.clear()
                val shot = Shot(f.data, f.w, f.h, rotation, lens(f.w, f.h), m ?: floatArrayOf(0f, 9.81f, 0f), sp, still, System.currentTimeMillis(), focus(meta[ts]))
                locking = false
                if (startSweep()) { base = shot; phase = Phase.SWEEP }
                else { afTrigger(CameraMetadata.CONTROL_AF_TRIGGER_CANCEL); pending = null; phase = Phase.IDLE; p(shot) }
            }
            Phase.SWEEP -> {
                val t = targets.getOrNull(target)
                if (t != null) {
                    // the first held frame at this position with the lens settled there
                    val ts = held.keys.firstOrNull { k ->
                        val fm = meta[k]
                        fm?.focus != null && (fm.lens == null || fm.lens == CaptureResult.LENS_STATE_STATIONARY) && kotlin.math.abs(fm.focus - t) <= 0.05f * t + 0.03f
                    }
                    if (ts != null) {
                        val f = held[ts]!!
                        swept += SweepFrame(meta[ts]!!.focus!!, PhotoFiles.uprightLuma(f.data, f.w, f.h, rotation))
                        held.clear(); nextTarget()
                    } else if (now - stepSince > 600) { held.clear(); nextTarget() }     // this position never settled: skip it
                }
                if (target >= targets.size || now - sweepSince > 6000) {
                    restoreAf()
                    val b = base ?: return
                    val (m, sp) = accelNow()
                    // the phone moved during the sweep: its frames no longer line up with the photo
                    val steady = m != null && sp < 0.35f
                    val rot = ((rotation % 360) + 360) % 360
                    val uw = if (rot == 90 || rot == 270) b.sh else b.sw; val uh = if (rot == 90 || rot == 270) b.sw else b.sh
                    val shot = Shot(b.nv21, b.sw, b.sh, b.rotation, b.k, b.accel, b.accelSpread, b.still, b.timeMs, b.focus,
                        if (steady && swept.size >= 5) SweepData(swept.toList(), uw, uh) else null)
                    base = null; swept.clear(); held.clear(); pending = null; phase = Phase.IDLE
                    p(shot)
                }
            }
            Phase.IDLE -> {}
        }
    }

    /** The autofocus of frame [fm] (or the latest), with how far the camera says its focus distances can be trusted. */
    private fun focus(fm: FrameMeta? = null): FocusInfo? {
        val d = fm?.focus ?: focusDiopters ?: return null
        val af = if (fm != null) fm.af else afState
        val c = chars ?: return null
        val cal = when (c.get(CameraCharacteristics.LENS_INFO_FOCUS_DISTANCE_CALIBRATION)) {
            CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_CALIBRATED -> "calibrated"
            CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_APPROXIMATE -> "approximate"
            else -> "uncalibrated"
        }
        return FocusInfo(d, cal, c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE), c.get(CameraCharacteristics.LENS_INFO_HYPERFOCAL_DISTANCE), af)
    }

    /** The lens of the upright full picture for a [sw] x [sh] stream. */
    private fun lens(sw: Int, sh: Int): Intrinsics {
        val c = chars!!
        val f = c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)?.firstOrNull() ?: 0f
        val phys = c.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)
        val pix = c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE)
        val act = c.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE)
        // the factory calibration is in active-array pixels from Android 9; earlier it may be in pixel-array ones
        val intr = if (Build.VERSION.SDK_INT >= 28) c.get(CameraCharacteristics.LENS_INTRINSIC_CALIBRATION)?.takeIf { a -> a.size >= 4 && a[0] > 0f } else null
        val aw = act?.width() ?: pix?.width ?: sw; val ah = act?.height() ?: pix?.height ?: sh
        val fromLens = if (f > 0f && phys != null && pix != null) Intrinsics.fromCamera(f, phys.width, pix.width, aw, ah, null, sw, sh, rotation) else null
        // a factory calibration far from what the lens's focal length says is not trusted (some phones fill it badly)
        val fromCal = intr?.let { Intrinsics.fromCamera(f, phys?.width ?: 1f, pix?.width ?: aw, aw, ah, it, sw, sh, rotation) }
            ?.takeIf { c -> fromLens == null || kotlin.math.abs(c.fx / fromLens.fx - 1f) < 0.25f }
        // nothing known: a 66 deg wide view, typical of these phones (the calibration then absorbs the rest)
        return fromCal ?: fromLens ?: Intrinsics.fromCamera(1f, 2f * 0.6494f, sw, sw, sh, null, sw, sh, rotation)
    }

    fun close() {
        closed = true
        pending = null
        sm.unregisterListener(accListener)
        runCatching { session?.close() }; runCatching { device?.close() }; runCatching { reader?.close() }; runCatching { surface?.release() }
        session = null; device = null; reader = null
        thread.quitSafely()
    }

    companion object {
        /** Lens positions in the focus sweep. */
        const val SWEEP_STEPS = 16

        /** Still: the acceleration wandered less than 0,25 m/s² rms over 0,4 s and is close to g (no swing). */
        fun isStill(m: FloatArray, spread: Float): Boolean {
            val g = sqrt(m[0] * m[0] + m[1] * m[1] + m[2] * m[2])
            return spread < 0.25f && g in 9.0f..10.6f
        }

        /** How far below the horizon the back camera looks, from the mean acceleration. */
        fun downDeg(m: FloatArray): Float {
            val up = Intrinsics.upFromAccel(m[0], m[1], m[2])
            return Math.toDegrees(asin((-up.z).toDouble().coerceIn(-1.0, 1.0))).toFloat()
        }
    }
}
