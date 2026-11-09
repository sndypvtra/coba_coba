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
import android.hardware.camera2.CaptureRequest
import android.media.ImageReader
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.util.Size
import android.view.Surface
import id.ukurpaket.app.dt.SweepRecorder
import kotlin.math.asin
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
               val accel: FloatArray, val accelSpread: Float, val still: Boolean, val timeMs: Long)

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
                    // the lens must not move against the sensor: the measurement uses the factory focal length
                    b.set(CaptureRequest.CONTROL_VIDEO_STABILIZATION_MODE, CameraMetadata.CONTROL_VIDEO_STABILIZATION_MODE_OFF)
                    s.setRepeatingRequest(b.build(), null, handler)
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
    fun capture(maxWaitMs: Long = 2000, onShot: (Shot) -> Unit) {
        handler.post { pending = onShot; pendingSince = SystemClock.elapsedRealtime() }
        this.maxWait = maxWaitMs
    }
    @Volatile private var maxWait = 2000L

    private fun onImage(r: ImageReader) {
        val img = try { r.acquireNextImage() } catch (e: Exception) { null } ?: return
        try {
            if (++frames % 8 == 1) brightness = SweepRecorder.meanLuma(img)
            val p = pending ?: return
            val (m, sp) = accelNow()
            val still = m != null && isStill(m, sp)
            if (!still && SystemClock.elapsedRealtime() - pendingSince < maxWait) return
            pending = null
            val nv = SweepRecorder.toNv21(img)
            val shot = Shot(nv, img.width, img.height, rotation, lens(img.width, img.height), m ?: floatArrayOf(0f, 9.81f, 0f), sp, still, System.currentTimeMillis())
            p(shot)
        } finally { img.close() }
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
