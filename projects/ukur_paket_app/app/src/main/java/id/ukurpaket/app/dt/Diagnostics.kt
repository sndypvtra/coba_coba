package id.ukurpaket.app.dt

import android.app.ActivityManager
import android.content.Context
import android.graphics.ImageFormat
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraCharacteristics.LENS_FACING
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.StatFs
import kotlinx.coroutines.delay
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * What a phone without ARCore (Urovo DT20) offers for our own visual-inertial engine: the motion sensors, their real
 * rate, the camera's controls and clock. Everything is read from the Android APIs; nothing is assumed per model.
 */
@Serializable
data class SensorInfo(val type: String, val name: String, val vendor: String, val maxHz: Double, val rangeMax: Float,
                      val resolution: Float, val measuredHz: Double? = null)

@Serializable
data class CameraInfo(
    val id: String, val facing: String, val hardwareLevel: String, val capabilities: List<String>,
    val timestampSource: String, val sensorOrientation: Int, val focusCalibration: String, val minFocusDiopters: Float,
    val focalLengthsMm: List<Float>, val sensorSizeMm: List<Float>, val pixelArray: List<Int>,
    val intrinsics: List<Float>?, val distortion: List<Float>?, val poseRotation: List<Float>?, val poseTranslation: List<Float>?,
    val afModes: List<String>, val aeLock: Boolean, val awbLock: Boolean, val ois: Boolean, val videoStabilization: Boolean,
    val yuvSizes: List<String>, val fpsRanges: List<String>, val yuv640Fps: Double?, val yuv1280Fps: Double?,
)

@Serializable
data class DeviceInfo(val manufacturer: String, val model: String, val brand: String, val device: String, val hardware: String,
                      val android: String, val sdk: Int, val abis: List<String>, val cores: Int, val ramMb: Long, val freeMb: Long)

@Serializable
data class Diagnosis(val device: DeviceInfo, val arcore: String, val urovoScanner: Boolean, val sensors: List<SensorInfo>,
                     val cameras: List<CameraInfo>, val samEncodeMs: Long? = null, val checks: List<Check> = emptyList())

enum class Level { OK, WARN, FAIL, INFO }

@Serializable
data class Check(val key: String, val label: String, val value: String, val level: Level, val note: String)

object Diagnostics {
    val json = Json { prettyPrint = true; encodeDefaults = true }

    /** The sensors the solver can use; the first two are required. */
    val SENSORS = linkedMapOf(
        Sensor.TYPE_ACCELEROMETER to "accelerometer", Sensor.TYPE_GYROSCOPE to "gyroscope",
        Sensor.TYPE_ACCELEROMETER_UNCALIBRATED to "accelerometer_uncalibrated", Sensor.TYPE_GYROSCOPE_UNCALIBRATED to "gyroscope_uncalibrated",
        Sensor.TYPE_MAGNETIC_FIELD to "magnetometer", Sensor.TYPE_GRAVITY to "gravity", Sensor.TYPE_ROTATION_VECTOR to "rotation_vector",
        Sensor.TYPE_GAME_ROTATION_VECTOR to "game_rotation_vector",
    )

    fun device(ctx: Context): DeviceInfo {
        val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val mi = ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
        val free = runCatching { StatFs(ctx.filesDir.path).availableBytes / (1 shl 20) }.getOrDefault(-1)
        return DeviceInfo(Build.MANUFACTURER, Build.MODEL, Build.BRAND, Build.DEVICE, Build.HARDWARE, Build.VERSION.RELEASE,
            Build.VERSION.SDK_INT, Build.SUPPORTED_ABIS.toList(), Runtime.getRuntime().availableProcessors(), mi.totalMem / (1 shl 20), free)
    }

    fun sensors(ctx: Context): List<SensorInfo> {
        val sm = ctx.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        return SENSORS.mapNotNull { (t, name) ->
            sm.getDefaultSensor(t)?.let { s ->
                SensorInfo(name, s.name, s.vendor, if (s.minDelay > 0) 1e6 / s.minDelay else 0.0, s.maximumRange, s.resolution)
            }
        }
    }

    /**
     * Counts the events each sensor really delivers, one sensor at a time (so one silent sensor cannot hide behind
     * another): at the fastest rate, and for a silent one once more at a fixed 5 ms period, as some drivers ignore
     * "fastest". 0 means the sensor is listed but sends nothing.
     */
    suspend fun measureRates(ctx: Context, msEach: Long = 1500, onStep: (String) -> Unit = {}): Map<String, Double> {
        val sm = ctx.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val thread = HandlerThread("diag-imu").apply { start() }
        val out = LinkedHashMap<String, Double>()
        try {
            for ((type, name) in SENSORS) {
                val s = sm.getDefaultSensor(type) ?: continue
                onStep(name)
                var hz = count(sm, s, SensorManager.SENSOR_DELAY_FASTEST, Handler(thread.looper), msEach)
                if (hz == 0.0) hz = count(sm, s, 5000, Handler(thread.looper), msEach)
                out[name] = hz
            }
        } finally { thread.quitSafely() }
        return out
    }

    private suspend fun count(sm: SensorManager, s: Sensor, period: Int, h: Handler, ms: Long): Double {
        val n = IntArray(1); val first = LongArray(1); val last = LongArray(1)
        val l = object : SensorEventListener {
            override fun onSensorChanged(e: SensorEvent) {
                synchronized(n) { if (n[0] == 0) first[0] = e.timestamp; last[0] = e.timestamp; n[0]++ }
            }
            override fun onAccuracyChanged(s: Sensor?, a: Int) {}
        }
        sm.registerListener(l, s, period, h)
        try { delay(ms) } finally { sm.unregisterListener(l) }
        return synchronized(n) { val span = (last[0] - first[0]) / 1e9; if (n[0] > 1 && span > 0) (n[0] - 1) / span else 0.0 }
    }

    fun cameras(ctx: Context): List<CameraInfo> {
        val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        return cm.cameraIdList.mapNotNull { id -> runCatching { camera(cm.getCameraCharacteristics(id), id) }.getOrNull() }
    }

    private fun camera(c: CameraCharacteristics, id: String): CameraInfo {
        val map = c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
        val yuv = map?.getOutputSizes(ImageFormat.YUV_420_888).orEmpty().sortedByDescending { it.width * it.height }
        fun fps(w: Int, h: Int): Double? = yuv.firstOrNull { it.width == w && it.height == h }?.let { s ->
            val d = map!!.getOutputMinFrameDuration(ImageFormat.YUV_420_888, s); if (d > 0) 1e9 / d else null
        }
        val caps = c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)?.toList().orEmpty()
        return CameraInfo(
            id = id,
            facing = when (c.get(LENS_FACING)) { CameraMetadata.LENS_FACING_BACK -> "back"; CameraMetadata.LENS_FACING_FRONT -> "front"; else -> "external" },
            hardwareLevel = when (c.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)) {
                CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY -> "LEGACY"; CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_LIMITED -> "LIMITED"
                CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_FULL -> "FULL"; CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_3 -> "LEVEL_3"
                CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_EXTERNAL -> "EXTERNAL"; else -> "?"
            },
            capabilities = caps.map { CAPS[it] ?: "cap$it" },
            timestampSource = if (c.get(CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE) == CameraMetadata.SENSOR_INFO_TIMESTAMP_SOURCE_REALTIME) "REALTIME" else "UNKNOWN",
            sensorOrientation = c.get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 0,
            focusCalibration = when (c.get(CameraCharacteristics.LENS_INFO_FOCUS_DISTANCE_CALIBRATION)) {
                CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_CALIBRATED -> "CALIBRATED"
                CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_APPROXIMATE -> "APPROXIMATE"; else -> "UNCALIBRATED"
            },
            minFocusDiopters = c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE) ?: 0f,
            focalLengthsMm = c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)?.toList().orEmpty(),
            sensorSizeMm = c.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)?.let { listOf(it.width, it.height) }.orEmpty(),
            pixelArray = c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE)?.let { listOf(it.width, it.height) }.orEmpty(),
            intrinsics = c.get(CameraCharacteristics.LENS_INTRINSIC_CALIBRATION)?.toList()?.takeIf { l -> l.any { it != 0f } },
            distortion = if (Build.VERSION.SDK_INT >= 28) c.get(CameraCharacteristics.LENS_DISTORTION)?.toList()?.takeIf { l -> l.any { it != 0f } } else null,
            poseRotation = c.get(CameraCharacteristics.LENS_POSE_ROTATION)?.toList(),
            poseTranslation = c.get(CameraCharacteristics.LENS_POSE_TRANSLATION)?.toList(),
            afModes = c.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES)?.map { AF[it] ?: "af$it" }.orEmpty(),
            aeLock = c.get(CameraCharacteristics.CONTROL_AE_LOCK_AVAILABLE) == true,
            awbLock = c.get(CameraCharacteristics.CONTROL_AWB_LOCK_AVAILABLE) == true,
            ois = c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)?.any { it == CameraMetadata.LENS_OPTICAL_STABILIZATION_MODE_ON } == true,
            videoStabilization = c.get(CameraCharacteristics.CONTROL_AVAILABLE_VIDEO_STABILIZATION_MODES)?.any { it == CameraMetadata.CONTROL_VIDEO_STABILIZATION_MODE_ON } == true,
            yuvSizes = yuv.take(12).map { "${it.width}x${it.height}" },
            fpsRanges = c.get(CameraCharacteristics.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES)?.map { "${it.lower}-${it.upper}" }.orEmpty(),
            yuv640Fps = fps(640, 480), yuv1280Fps = fps(1280, 960) ?: fps(1280, 720),
        )
    }

    private val CAPS = mapOf(
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE to "BACKWARD_COMPATIBLE",
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR to "MANUAL_SENSOR",
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_POST_PROCESSING to "MANUAL_POST_PROCESSING",
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_RAW to "RAW", CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_READ_SENSOR_SETTINGS to "READ_SENSOR_SETTINGS",
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_BURST_CAPTURE to "BURST_CAPTURE", CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT to "DEPTH_OUTPUT",
        CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MOTION_TRACKING to "MOTION_TRACKING", CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA to "LOGICAL_MULTI_CAMERA",
    )
    private val AF = mapOf(
        CameraMetadata.CONTROL_AF_MODE_OFF to "OFF", CameraMetadata.CONTROL_AF_MODE_AUTO to "AUTO", CameraMetadata.CONTROL_AF_MODE_MACRO to "MACRO",
        CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_VIDEO to "CONTINUOUS_VIDEO", CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_PICTURE to "CONTINUOUS_PICTURE",
        CameraMetadata.CONTROL_AF_MODE_EDOF to "EDOF",
    )

    /** The back camera the recorder uses: the first one facing back. */
    fun mainCamera(cams: List<CameraInfo>) = cams.firstOrNull { it.facing == "back" }

    /**
     * Whether this phone can feed our own visual-inertial engine (the stand-in for ARCore), in plain words.
     * [rates]: measured Hz per sensor name.
     */
    fun checks(d: Diagnosis, rates: Map<String, Double>): List<Check> {
        val out = ArrayList<Check>()
        val has = d.sensors.associateBy { it.type }
        fun rate(name: String) = rates[name] ?: rates["${name}_uncalibrated"]
        val gyroHz = rates["gyroscope"]
        val rvHz = listOfNotNull(rates["game_rotation_vector"], rates["rotation_vector"]).maxOrNull()
        out += when {
            has["gyroscope"] == null -> Check("gyro", "Gyroscope", "Tidak ada", Level.FAIL, "Tanpa gyroscope, skala dari sensor gerak tidak bisa. Sisa cara: label resi sebagai penggaris.")
            gyroHz == 0.0 && (rvHz ?: 0.0) > 0 -> Check("gyro", "Gyroscope", "terdaftar, tapi diam", Level.WARN,
                "Gyroscope tidak mengirim data. Putaran HP diambil dari rotation vector (${rvHz!!.toInt()} Hz): bisa, kurang teliti.")
            gyroHz == 0.0 -> Check("gyro", "Gyroscope", "terdaftar, tapi diam", Level.FAIL, "Gyroscope dan rotation vector tidak mengirim data.")
            else -> Check("gyro", "Gyroscope", has["gyroscope"]!!.name, Level.OK, "Ada: putaran HP terbaca langsung.")
        }
        out += if (has["accelerometer"] != null) Check("accel", "Accelerometer", has["accelerometer"]!!.name, Level.OK, "Ada: sumber skala meter dan arah gravitasi.")
        else Check("accel", "Accelerometer", "Tidak ada", Level.FAIL, "Tanpa accelerometer tidak ada skala dan arah lantai.")
        for ((key, name, label) in listOf(Triple("accel_hz", "accelerometer", "Kecepatan accelerometer"), Triple("gyro_hz", "gyroscope", "Kecepatan gyroscope"))) {
            val r = rate(name)
            out += when {
                r == null -> Check(key, label, "belum diukur", Level.INFO, "Tekan Sensor.")
                r == 0.0 -> Check(key, label, "0 Hz", if (name == "gyroscope") Level.WARN else Level.FAIL, "Sensor terdaftar tetapi tidak mengirim data.")
                r >= 150 -> Check(key, label, "${r.toInt()} Hz", Level.OK, "Cukup (≥ 150 Hz).")
                r >= 90 -> Check(key, label, "${r.toInt()} Hz", Level.WARN, "Bisa dipakai, ideal ≥ 150 Hz.")
                else -> Check(key, label, "${r.toInt()} Hz", Level.FAIL, "Terlalu pelan untuk mengikuti gerakan HP (perlu ≥ 90 Hz).")
            }
        }
        val cam = mainCamera(d.cameras)
        if (cam == null) { out += Check("camera", "Kamera belakang", "Tidak ditemukan", Level.FAIL, ""); return out }
        out += if (cam.timestampSource == "REALTIME") Check("clock", "Jam kamera = jam sensor", "REALTIME", Level.OK, "Waktu tiap foto dan data sensor bisa langsung dicocokkan.")
        else Check("clock", "Jam kamera = jam sensor", "UNKNOWN", Level.WARN, "Jam kamera dan sensor terpisah: selisihnya harus diperkirakan dari rekaman (bisa, tapi kurang teliti).")
        out += when (cam.hardwareLevel) {
            "LEGACY" -> Check("level", "Level kamera", "LEGACY", Level.WARN, "Kontrol kamera terbatas (fokus/exposure tidak selalu bisa dikunci).")
            else -> Check("level", "Level kamera", cam.hardwareLevel, Level.OK, "Kontrol kamera tersedia.")
        }
        val manual = "MANUAL_SENSOR" in cam.capabilities
        out += when {
            cam.minFocusDiopters == 0f -> Check("focus", "Fokus", "Fokus tetap", Level.OK, "Fokus tidak berubah: kalibrasi kamera tetap berlaku.")
            manual -> Check("focus", "Fokus", "Bisa dikunci (manual)", Level.OK, "Fokus dikunci selama rekam.")
            "AUTO" in cam.afModes -> Check("focus", "Fokus", "Kunci lewat AF lock", Level.WARN, "Fokus dikunci setelah AF; jarak fokus dicatat tiap foto.")
            else -> Check("focus", "Fokus", cam.afModes.joinToString(), Level.WARN, "Fokus tidak bisa dikunci; jarak fokus dicatat tiap foto.")
        }
        out += if (cam.aeLock) Check("ae", "Kunci exposure", "Bisa", Level.OK, "Terang foto tetap selama rekam.")
        else Check("ae", "Kunci exposure", "Tidak bisa", Level.WARN, "Terang foto bisa berubah selama rekam.")
        val f640 = cam.yuv640Fps
        out += when {
            f640 == null -> Check("fps", "Video 640×480", "tidak ada", Level.WARN, "Ukuran lain dipakai.")
            f640 >= 29 -> Check("fps", "Video 640×480", "${f640.toInt()} fps", Level.OK, "Cukup untuk rekaman sapuan.")
            else -> Check("fps", "Video 640×480", "${f640.toInt()} fps", Level.WARN, "Di bawah 30 fps.")
        }
        out += if (cam.intrinsics != null) Check("intr", "Kalibrasi lensa dari pabrik", "Ada", Level.INFO, "Dipakai sebagai titik awal; tetap dicek dengan kalibrasi sendiri.")
        else Check("intr", "Kalibrasi lensa dari pabrik", "Tidak ada", Level.INFO, "Normal untuk HP ini: kamera dikalibrasi sekali per model di kantor.")
        val free = if (d.device.freeMb >= 1024) "${d.device.freeMb / 1024} GB" else "${d.device.freeMb} MB"
        out += if (d.device.freeMb in 0 until 1024) Check("disk", "Ruang kosong", free, Level.WARN, "Satu rekaman ±10–40 MB.")
        else Check("disk", "Ruang kosong", free, Level.OK, "Cukup untuk puluhan rekaman.")
        d.samEncodeMs?.let { ms ->
            out += Check("sam", "MobileSAM (pilih objek)", "${"%.1f".format(ms / 1000.0).replace('.', ',')} s per foto",
                if (ms <= 8000) Level.OK else if (ms <= 25000) Level.WARN else Level.FAIL,
                if (ms <= 8000) "Cukup cepat." else "Lambat: dipakai sekali per objek saja.")
        }
        return out
    }

    /** One line for the screen: can our own engine run here? */
    fun verdict(checks: List<Check>): Pair<Level, String> = when {
        checks.any { it.level == Level.FAIL } -> Level.FAIL to "Belum memenuhi syarat: lihat tanda merah."
        checks.any { it.level == Level.WARN } -> Level.WARN to "Bisa dipakai, dengan catatan (kuning)."
        else -> Level.OK to "Memenuhi syarat engine tanpa ARCore."
    }
}
