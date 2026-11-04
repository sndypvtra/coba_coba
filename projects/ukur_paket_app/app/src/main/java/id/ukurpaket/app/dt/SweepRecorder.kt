package id.ukurpaket.app.dt

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.SurfaceTexture
import android.graphics.YuvImage
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureResult
import android.hardware.camera2.TotalCaptureResult
import android.media.Image
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.util.Range
import android.util.Size
import android.view.Surface
import java.io.BufferedWriter
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.sqrt

/**
 * Records one sweep around an object for the DT20 engine: camera frames (JPEG, with the camera's own timestamps and
 * per-frame exposure, focus and rolling-shutter skew) and every motion-sensor event at the fastest rate, all on the
 * same clock when the camera says REALTIME. Nothing is computed here; the files are what the solver reads.
 *
 * Folder: frames/NNNNN.jpg, frames.csv, capture.csv, imu.csv, session.json (+ diagnosis.json written by the caller).
 */
class SweepRecorder(private val ctx: Context, val dir: File, private val cb: Callback) {
    interface Callback {
        fun onStatus(s: LiveStatus)
        fun onError(msg: String)
    }

    data class LiveStatus(val recording: Boolean, val seconds: Double, val savedFrames: Int, val dropped: Int, val cameraFps: Double,
                          val accelHz: Double, val gyroHz: Double, val turnDeg: Double, val size: String, val rotationHz: Double = 0.0,
                          val brightness: Double = 128.0, val exposureMs: Double? = null)

    private val camThread = HandlerThread("sweep-cam").apply { start() }
    private val camHandler = Handler(camThread.looper)
    private val imuThread = HandlerThread("sweep-imu", android.os.Process.THREAD_PRIORITY_URGENT_DISPLAY).apply { start() }
    private val imuHandler = Handler(imuThread.looper)
    private val encoder = ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, ArrayBlockingQueue(6), ThreadPoolExecutor.DiscardPolicy())
    private val sm = ctx.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as CameraManager

    private var device: CameraDevice? = null
    private var session: CameraCaptureSession? = null
    private var reader: ImageReader? = null
    private var previewSurface: Surface? = null
    private var chars: CameraCharacteristics? = null
    private var texture: SurfaceTexture? = null
    var size: Size = Size(640, 480); private set
    /** How far the frames turn to stand upright (the camera's sensor orientation). */
    val sensorOrientation get() = chars?.get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 90
    var cameraId: String = ""; private set

    @Volatile private var recording = false
    private var startNs = 0L
    private var recWallNs = 0L
    private var lastSavedNs = 0L
    private val saved = AtomicInteger(0)
    private val dropped = AtomicInteger(0)
    // arrival_ns: when the frame reached the app, on the motion sensors' clock; it maps a camera clock that is not
    // REALTIME onto the sensors' one (to within the delivery delay, which the solver then estimates)
    private val frameRows = StringBuilder("index,t_ns,sharpness,width,height,bytes,arrival_ns\n")
    private val clockOffsets = ArrayList<Long>()
    private val captureRows = StringBuilder("t_ns,exposure_ns,frame_duration_ns,rolling_shutter_skew_ns,focus_diopters,af_state,ae_state,iso\n")
    private var imuOut: BufferedWriter? = null
    private var lastFocus: Float? = null
    // the auto exposure's choice while previewing: recording keeps the same brightness with a shorter exposure
    @Volatile private var lastExposureNs: Long? = null
    @Volatile private var lastIso: Int? = null
    @Volatile private var brightness = 128.0

    // live counters for the screen
    private var camFrames = 0; private var camT0 = 0L
    private val imuCount = IntArray(3); private var imuT0 = 0L
    private var lastRv: FloatArray? = null; private var lastRvNs = 0L
    @Volatile private var gyroTotal = 0
    private var lastGyroNs = 0L
    @Volatile private var turnRad = 0.0
    private var lastStatus = 0L

    /** The engine's tracking, done while recording on every saved frame; it also drives the live segmentation. */
    val tracking = id.ukurpaket.app.vio.RecordingTracker()
    /** What [tracking] handed over once recording stopped (null before, or if it failed). */
    @Volatile var prepared: id.ukurpaket.app.vio.RecordingTracker.Prepared? = null; private set

    /** Segments the picked object live (set when recording starts with a pick), on the tracking thread's tracks. */
    var live: id.ukurpaket.app.vio.LiveSegmenter?
        get() = tracking.seg
        set(v) { tracking.seg = v }

    /** Target rate of saved frames: the solver needs ~10–15 per second; the motion sensors carry the fast motion. */
    var minFrameGapNs = 60_000_000L

    // ---------------------------------------------------------------- camera
    @SuppressLint("MissingPermission")
    fun open(texture: SurfaceTexture) {
        try {
            cameraId = cm.cameraIdList.firstOrNull { cm.getCameraCharacteristics(it).get(CameraCharacteristics.LENS_FACING) == CameraMetadata.LENS_FACING_BACK }
                ?: cm.cameraIdList.first()
            val c = cm.getCameraCharacteristics(cameraId).also { chars = it }
            val sizes = c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)!!.getOutputSizes(ImageFormat.YUV_420_888)
            size = pickSize(sizes.map { it.width to it.height })?.let { Size(it.first, it.second) } ?: sizes.first()
            this.texture = texture
            makeSurfaces()
            cm.openCamera(cameraId, object : CameraDevice.StateCallback() {
                override fun onOpened(d: CameraDevice) { device = d; startSession() }
                override fun onDisconnected(d: CameraDevice) { d.close(); device = null }
                override fun onError(d: CameraDevice, e: Int) { d.close(); device = null; cb.onError("Kamera tidak bisa dibuka (kode $e).") }
            }, camHandler)
        } catch (e: Exception) { cb.onError("Kamera tidak bisa dibuka: ${e.message}") }
        startImu()
    }

    private fun makeSurfaces() {
        texture!!.setDefaultBufferSize(size.width, size.height)
        previewSurface?.release()
        previewSurface = Surface(texture)
        reader?.close()
        reader = ImageReader.newInstance(size.width, size.height, ImageFormat.YUV_420_888, 4).apply {
            setOnImageAvailableListener({ r -> onImage(r) }, camHandler)
        }
    }

    @Suppress("DEPRECATION")
    private fun startSession() {
        val d = device ?: return
        val targets = listOf(previewSurface!!, reader!!.surface)
        d.createCaptureSession(targets, object : CameraCaptureSession.StateCallback() {
            override fun onConfigured(s: CameraCaptureSession) { session = s; repeat(locked = false) }
            override fun onConfigureFailed(s: CameraCaptureSession) {
                // some cameras cannot stream preview + 1280×960 YUV together: retry at 640×480 once
                if (size.width > 640) { size = Size(640, 480); makeSurfaces(); startSession() }
                else cb.onError("Sesi kamera gagal dibuat.")
            }
        }, camHandler)
    }

    /** Preview: auto focus and exposure. Recording: focus, exposure and white balance locked, no stabilisation. */
    private fun repeat(locked: Boolean) {
        val s = session ?: return; val d = device ?: return; val c = chars ?: return
        try {
            val b = d.createCaptureRequest(CameraDevice.TEMPLATE_RECORD)
            b.addTarget(previewSurface!!); b.addTarget(reader!!.surface)
            fixedFps(c)?.let { b.set(CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE, it) }
            // stabilisation moves the image against the lens: it would break the camera model
            b.set(CaptureRequest.CONTROL_VIDEO_STABILIZATION_MODE, CameraMetadata.CONTROL_VIDEO_STABILIZATION_MODE_OFF)
            if (c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)?.contains(CameraMetadata.LENS_OPTICAL_STABILIZATION_MODE_OFF) == true)
                b.set(CaptureRequest.LENS_OPTICAL_STABILIZATION_MODE, CameraMetadata.LENS_OPTICAL_STABILIZATION_MODE_OFF)
            val afModes = c.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES)?.toList().orEmpty()
            val manual = c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)?.contains(CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR) == true
            val focus = lastFocus
            if (locked && manual && focus != null && (c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE) ?: 0f) > 0f) {
                b.set(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_OFF)
                b.set(CaptureRequest.LENS_FOCUS_DISTANCE, focus)
            } else if (CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_VIDEO in afModes) {
                b.set(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_VIDEO)
            }
            val exp = lastExposureNs; val iso = lastIso
            val isoRange = c.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE)
            val expRange = c.get(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE)
            if (locked && manual && exp != null && iso != null && isoRange != null && expRange != null && exp > MAX_EXPOSURE_NS) {
                // a dim room: auto exposure picks long exposures, and a moving phone then blurs every frame (tracks are
                // lost). Same brightness with at most 1/80 s: the gain makes up the rest (noise hurts tracking far less)
                val target = maxOf(MAX_EXPOSURE_NS, expRange.lower)
                var newIso = (iso.toDouble() * exp / target).toInt()
                var newExp = target
                if (newIso > isoRange.upper) { newIso = isoRange.upper; newExp = minOf(exp, (exp.toDouble() * iso / newIso).toLong()) }
                b.set(CaptureRequest.CONTROL_AE_MODE, CameraMetadata.CONTROL_AE_MODE_OFF)
                b.set(CaptureRequest.SENSOR_EXPOSURE_TIME, newExp)
                b.set(CaptureRequest.SENSOR_SENSITIVITY, newIso.coerceIn(isoRange.lower, isoRange.upper))
                b.set(CaptureRequest.SENSOR_FRAME_DURATION, 33_333_333L)
                if (c.get(CameraCharacteristics.CONTROL_AWB_LOCK_AVAILABLE) == true) b.set(CaptureRequest.CONTROL_AWB_LOCK, true)
            } else if (locked) {
                if (c.get(CameraCharacteristics.CONTROL_AE_LOCK_AVAILABLE) == true) b.set(CaptureRequest.CONTROL_AE_LOCK, true)
                if (c.get(CameraCharacteristics.CONTROL_AWB_LOCK_AVAILABLE) == true) b.set(CaptureRequest.CONTROL_AWB_LOCK, true)
            }
            s.setRepeatingRequest(b.build(), object : CameraCaptureSession.CaptureCallback() {
                override fun onCaptureCompleted(s: CameraCaptureSession, r: CaptureRequest, res: TotalCaptureResult) { onResult(res) }
            }, camHandler)
        } catch (e: Exception) { cb.onError("Kamera berhenti: ${e.message}") }
    }

    private fun fixedFps(c: CameraCharacteristics): Range<Int>? {
        val r = c.get(CameraCharacteristics.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES)?.toList().orEmpty()
        return r.filter { it.upper == 30 }.maxByOrNull { it.lower } ?: r.maxByOrNull { it.upper }
    }

    private fun onResult(r: TotalCaptureResult) {
        r.get(CaptureResult.LENS_FOCUS_DISTANCE)?.let { lastFocus = it }
        if (!recording) { r.get(CaptureResult.SENSOR_EXPOSURE_TIME)?.let { lastExposureNs = it }; r.get(CaptureResult.SENSOR_SENSITIVITY)?.let { lastIso = it } }
        if (!recording) return
        val t = r.get(CaptureResult.SENSOR_TIMESTAMP) ?: return
        synchronized(captureRows) {
            captureRows.append(t).append(',').append(r.get(CaptureResult.SENSOR_EXPOSURE_TIME) ?: "").append(',')
                .append(r.get(CaptureResult.SENSOR_FRAME_DURATION) ?: "").append(',').append(r.get(CaptureResult.SENSOR_ROLLING_SHUTTER_SKEW) ?: "").append(',')
                .append(r.get(CaptureResult.LENS_FOCUS_DISTANCE) ?: "").append(',').append(r.get(CaptureResult.CONTROL_AF_STATE) ?: "").append(',')
                .append(r.get(CaptureResult.CONTROL_AE_STATE) ?: "").append(',').append(r.get(CaptureResult.SENSOR_SENSITIVITY) ?: "").append('\n')
        }
    }

    private fun onImage(r: ImageReader) {
        val img = try { r.acquireNextImage() } catch (e: Exception) { null } ?: return
        try {
            val now = img.timestamp
            val arrival = SystemClock.elapsedRealtimeNanos()
            if (camT0 == 0L) camT0 = arrival           // rate on the wall clock: the camera's own clock may be another one
            camFrames++
            if (camFrames % 8 == 1) brightness = meanLuma(img)
            if (recording) synchronized(clockOffsets) { clockOffsets.add(arrival - now) }
            if (!recording || now < startNs || now - lastSavedNs < minFrameGapNs) return
            lastSavedNs = now
            val nv21 = toNv21(img)
            val w = img.width; val h = img.height
            val idx = saved.getAndIncrement()
            if (encoder.queue.remainingCapacity() == 0) { dropped.incrementAndGet(); saved.decrementAndGet(); return }
            encoder.execute {
                val f = File(dir, "frames/%05d.jpg".format(idx))
                // 85: the engine works on the greys kept in memory; the JPEG is for the review and re-runs
                f.outputStream().buffered().use { YuvImage(nv21, ImageFormat.NV21, w, h, null).compressToJpeg(Rect(0, 0, w, h), 85, it) }
                val sharp = sharpness(nv21, w, h)
                tracking.offer(idx, nv21, w, h, sensorOrientation)
                synchronized(frameRows) { frameRows.append(idx).append(',').append(now).append(',').append("%.2f".format(Locale.US, sharp)).append(',')
                    .append(w).append(',').append(h).append(',').append(f.length()).append(',').append(arrival).append('\n') }
            }
        } finally { img.close(); status() }
    }

    // ---------------------------------------------------------------- motion sensors
    private val imu = object : SensorEventListener {
        override fun onSensorChanged(e: SensorEvent) {
            val name = Diagnostics.SENSORS[e.sensor.type] ?: return
            if (imuT0 == 0L) imuT0 = e.timestamp
            when (e.sensor.type) {
                Sensor.TYPE_ACCELEROMETER -> imuCount[0]++
                Sensor.TYPE_ROTATION_VECTOR, Sensor.TYPE_GAME_ROTATION_VECTOR -> {
                    imuCount[2]++
                    // turn angle from the fused orientation when the gyroscope itself sends nothing
                    val q = rvQuat(e.values)
                    val prev = lastRv
                    if (recording && gyroTotal == 0 && prev != null && e.timestamp - lastRvNs < 100_000_000L) turnRad += quatAngle(prev, q)
                    lastRv = q; lastRvNs = e.timestamp
                }
                Sensor.TYPE_GYROSCOPE, Sensor.TYPE_GYROSCOPE_UNCALIBRATED -> {
                    synchronized(gyroSeen) { val k = key(e.sensor); gyroSeen[k] = (gyroSeen[k] ?: 0).coerceAtLeast(0) + 1 }
                    // one gyroscope only: the calibrated one when it delivers, else the first that does
                    val used = gyroUsed
                    if (used == null || (used.type == Sensor.TYPE_GYROSCOPE_UNCALIBRATED && e.sensor.type == Sensor.TYPE_GYROSCOPE)) gyroUsed = e.sensor
                    else if (used !== e.sensor) return
                    imuCount[1]++; gyroTotal++
                    if (recording && lastGyroNs > 0) {
                        val dt = (e.timestamp - lastGyroNs) / 1e9
                        if (dt in 0.0..0.1) turnRad += sqrt((e.values[0] * e.values[0] + e.values[1] * e.values[1] + e.values[2] * e.values[2]).toDouble()) * dt
                    }
                    lastGyroNs = e.timestamp
                }
            }
            val out = imuOut ?: return
            if (!recording) return
            if ((e.sensor.type == Sensor.TYPE_GYROSCOPE || e.sensor.type == Sensor.TYPE_GYROSCOPE_UNCALIBRATED) && e.sensor !== gyroUsed) return
            out.append(name).append(',').append(e.timestamp.toString())
            for (i in 0 until minOf(e.values.size, 6)) out.append(',').append(e.values[i].toString())
            out.append('\n')
        }
        override fun onAccuracyChanged(s: Sensor?, a: Int) {}
    }

    /**
     * Every motion sensor the engine can use. For the gyroscope, every one the phone lists (calibrated, uncalibrated,
     * wake-up or not): on the DT50 the default one is listed at 200 Hz but sends nothing, so whichever really delivers
     * is recorded; session.json says which.
     */
    private fun startImu() {
        val gyroTypes = setOf(Sensor.TYPE_GYROSCOPE, Sensor.TYPE_GYROSCOPE_UNCALIBRATED)
        Diagnostics.SENSORS.keys.filter { it !in gyroTypes }.forEach { t -> sm.getDefaultSensor(t)?.let { sm.registerListener(imu, it, SensorManager.SENSOR_DELAY_FASTEST, imuHandler) } }
        for (t in gyroTypes) {
            val all = (sm.getSensorList(t) + listOfNotNull(sm.getDefaultSensor(t, false), sm.getDefaultSensor(t, true))).distinct()
            for (g in all) {
                val ok = sm.registerListener(imu, g, SensorManager.SENSOR_DELAY_FASTEST, imuHandler)
                synchronized(gyroSeen) { gyroSeen[key(g)] = if (ok) 0 else -1 }
            }
        }
    }

    // gyroscope sensor -> events (-1: Android refused the listener)
    private val gyroSeen = LinkedHashMap<String, Int>()
    private fun key(s: Sensor) = "${Diagnostics.SENSORS[s.type]}|${s.name}|${if (s.isWakeUpSensor) "wakeup" else "non-wakeup"}"
    // the gyroscope sensor whose events are recorded: the first one that sends any
    @Volatile private var gyroUsed: Sensor? = null

    // ---------------------------------------------------------------- recording
    fun start() {
        File(dir, "frames").mkdirs()
        imuHandler.post {
            imuOut = File(dir, "imu.csv").bufferedWriter().also { it.append("sensor,t_ns,v0,v1,v2,v3,v4,v5\n") }
            turnRad = 0.0; lastGyroNs = 0L
        }
        camHandler.post {
            startNs = SystemClock.elapsedRealtimeNanos().let { now -> if (chars.isRealtime()) now else 0L }
            lastSavedNs = 0L
            recWallNs = SystemClock.elapsedRealtimeNanos()
            recording = true
            repeat(locked = true)
        }
    }

    /** Stops and writes the files; [onDone] runs on the camera thread once everything is on disk. */
    fun stop(onDone: (File) -> Unit) {
        camHandler.post {
            recording = false
            repeat(locked = false)
            // one recorder records one sweep: wait for the frames still being encoded, then write the tables
            Thread {
                encoder.shutdown()
                encoder.awaitTermination(15, TimeUnit.SECONDS)
                // the live segmentation stops; the frames still queued are tracked for the engine
                live?.close()
                prepared = tracking.finish()
                File(dir, "frames.csv").writeText(synchronized(frameRows) { frameRows.toString() })
                File(dir, "capture.csv").writeText(synchronized(captureRows) { captureRows.toString() })
                imuHandler.post {
                    runCatching { imuOut?.close() }; imuOut = null
                    writeSession()
                    onDone(dir)
                }
            }.start()
        }
    }

    private fun writeSession() {
        val c = chars
        val txt = """{
  "created": "${SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.US).format(Date())}",
  "camera_id": "$cameraId",
  "size": [${size.width}, ${size.height}],
  "sensor_orientation": ${c?.get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 0},
  "timestamp_source": "${if (c.isRealtime()) "REALTIME" else "UNKNOWN"}",
  "frames_saved": ${saved.get()},
  "frames_dropped": ${dropped.get()},
  "camera_to_sensor_clock_ns": ${synchronized(clockOffsets) { clockOffsets.sorted().let { if (it.isEmpty()) 0 else it[it.size / 2] } }},
  "gyroscope_events": $gyroTotal,
  "preview_exposure_ns": ${lastExposureNs ?: 0},
  "preview_iso": ${lastIso ?: 0},
  "exposure_capped_ns": $MAX_EXPOSURE_NS,
  "gyroscope_used": "${gyroUsed?.let { key(it) } ?: ""}",
  "gyroscopes": {${synchronized(gyroSeen) { gyroSeen.entries.joinToString(", ") { "\"${it.key}\": ${it.value}" } }}},
  "min_frame_gap_ms": ${minFrameGapNs / 1_000_000},
  "turn_deg": ${"%.1f".format(Locale.US, Math.toDegrees(turnRad))},
  "imu_axes": "Android sensor axes of the device's natural orientation (portrait on the DT20); m/s^2 and rad/s",
  "frame_axes": "camera sensor orientation (rotate by sensor_orientation for an upright picture)"
}
"""
        File(dir, "session.json").writeText(txt)
    }

    fun close() {
        recording = false
        live?.close(); live = null
        if (prepared == null) tracking.cancel()
        sm.unregisterListener(imu)
        runCatching { session?.close() }; runCatching { device?.close() }; runCatching { reader?.close() }; runCatching { previewSurface?.release() }
        session = null; device = null; reader = null
        encoder.shutdown()
        imuHandler.post { runCatching { imuOut?.close() }; imuOut = null }
        camThread.quitSafely(); imuThread.quitSafely()
    }

    private fun status() {
        val now = SystemClock.elapsedRealtime()
        if (now - lastStatus < 250) return
        lastStatus = now
        val camSpan = (SystemClock.elapsedRealtimeNanos() - camT0) / 1e9
        val imuSpan = (SystemClock.elapsedRealtimeNanos() - imuT0) / 1e9
        cb.onStatus(LiveStatus(recording, if (recording) (SystemClock.elapsedRealtimeNanos() - recWallNs) / 1e9 else 0.0,
            saved.get(), dropped.get(), if (camSpan > 0.5) camFrames / camSpan else 0.0,
            if (imuSpan > 0.5) imuCount[0] / imuSpan else 0.0, if (imuSpan > 0.5) imuCount[1] / imuSpan else 0.0,
            Math.toDegrees(turnRad), "${size.width}×${size.height}", if (imuSpan > 0.5) imuCount[2] / imuSpan else 0.0,
            brightness, lastExposureNs?.let { it / 1e6 }))
        if (camSpan > 4) { camFrames = 0; camT0 = SystemClock.elapsedRealtimeNanos() }
        if (imuSpan > 4) { imuCount[0] = 0; imuCount[1] = 0; imuCount[2] = 0; imuT0 = SystemClock.elapsedRealtimeNanos() }
    }

    private fun CameraCharacteristics?.isRealtime() =
        this?.get(CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE) == CameraMetadata.SENSOR_INFO_TIMESTAMP_SOURCE_REALTIME

    companion object {
        /** Rotation vector event -> unit quaternion (x, y, z, w); w is optional in the event. */
        fun rvQuat(v: FloatArray): FloatArray {
            val x = v[0]; val y = v[1]; val z = v[2]
            val w = if (v.size > 3) v[3] else sqrt(maxOf(0f, 1 - x * x - y * y - z * z))
            return floatArrayOf(x, y, z, w)
        }

        /** Angle (rad) between two orientations. */
        fun quatAngle(a: FloatArray, b: FloatArray): Double {
            val d = kotlin.math.abs((a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]).toDouble()).coerceAtMost(1.0)
            return 2 * kotlin.math.acos(d)
        }

        /** 4:3, about 1280 wide (label still readable, small files); else the nearest 4:3 at least 640 wide. */
        fun pickSize(sizes: List<Pair<Int, Int>>): Pair<Int, Int>? {
            val four3 = sizes.filter { (w, h) -> w * 3 == h * 4 && w >= 640 }
            return four3.filter { it.first <= 1280 }.maxByOrNull { it.first } ?: four3.minByOrNull { it.first }
                ?: sizes.filter { it.first >= 640 }.minByOrNull { it.first * it.second }
        }

        fun newDir(root: File): File =
            File(root, SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())).apply { mkdirs() }

        /** YUV_420_888 (any strides) to NV21. */
        fun toNv21(img: Image): ByteArray {
            val w = img.width; val h = img.height
            val out = ByteArray(w * h * 3 / 2)
            val y = img.planes[0]; val u = img.planes[1]; val v = img.planes[2]
            val yb = y.buffer; var o = 0
            for (row in 0 until h) {
                yb.position(row * y.rowStride)
                if (y.pixelStride == 1) { yb.get(out, o, w); o += w }
                else for (x in 0 until w) out[o++] = yb.get(row * y.rowStride + x * y.pixelStride)
            }
            val ub = u.buffer; val vb = v.buffer
            for (row in 0 until h / 2) for (x in 0 until w / 2) {
                out[o++] = vb.get(row * v.rowStride + x * v.pixelStride)
                out[o++] = ub.get(row * u.rowStride + x * u.pixelStride)
            }
            return out
        }

        /** Variance of the Laplacian on the luma, every 4th pixel: higher is sharper (motion blur lowers it). */
        /** Above this the recording takes over the exposure (1/80 s). */
        const val MAX_EXPOSURE_NS = 12_500_000L

        /** Mean luma of a camera image, every 16th pixel. */
        fun meanLuma(img: Image): Double {
            val pl = img.planes[0]; val buf = pl.buffer; val rs = pl.rowStride; val ps = pl.pixelStride
            var sum = 0L; var n = 0
            var y = 0
            while (y < img.height) { var x = 0; while (x < img.width) { sum += buf.get(y * rs + x * ps).toInt() and 255; n++; x += 16 }; y += 16 }
            return if (n == 0) 128.0 else sum.toDouble() / n
        }

        fun sharpness(luma: ByteArray, w: Int, h: Int): Double {
            var sum = 0.0; var sq = 0.0; var n = 0
            var yy = 4
            while (yy < h - 4) {
                var x = 4
                while (x < w - 4) {
                    val c = luma[yy * w + x].toInt() and 255
                    val l = (luma[yy * w + x - 4].toInt() and 255) + (luma[yy * w + x + 4].toInt() and 255) +
                        (luma[(yy - 4) * w + x].toInt() and 255) + (luma[(yy + 4) * w + x].toInt() and 255) - 4 * c
                    sum += l; sq += l.toDouble() * l; n++
                    x += 4
                }
                yy += 4
            }
            if (n == 0) return 0.0
            val m = sum / n
            return sq / n - m * m
        }
    }
}
