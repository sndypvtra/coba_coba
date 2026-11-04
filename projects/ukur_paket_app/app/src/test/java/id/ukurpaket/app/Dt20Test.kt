package id.ukurpaket.app

import android.app.Application
import id.ukurpaket.app.ar.ArState
import id.ukurpaket.app.ar.DeviceCaps
import id.ukurpaket.app.dt.CameraInfo
import id.ukurpaket.app.dt.DeviceInfo
import id.ukurpaket.app.dt.Diagnosis
import id.ukurpaket.app.dt.Diagnostics
import id.ukurpaket.app.dt.Level
import id.ukurpaket.app.dt.ObjectPick
import id.ukurpaket.app.dt.SensorInfo
import id.ukurpaket.app.dt.SweepAnalysis
import id.ukurpaket.app.dt.SweepAnalysis.Frame
import id.ukurpaket.app.dt.SweepAnalysis.Imu
import id.ukurpaket.app.dt.SweepRecorder
import id.ukurpaket.app.ui.AppModel
import id.ukurpaket.app.ui.Screen
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import java.io.File
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/** DT20 test tools: the diagnosis rules, the sweep quality check (on synthetic sweeps and on the files), picking, navigation. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class Dt20Test {
    private val app: Application = RuntimeEnvironment.getApplication()

    companion object {
        fun camera(ts: String = "REALTIME", level: String = "LIMITED", manual: Boolean = false, minFocus: Float = 10f) = CameraInfo(
            "0", "back", level, listOfNotNull("BACKWARD_COMPATIBLE", if (manual) "MANUAL_SENSOR" else null), ts, 90, "APPROXIMATE", minFocus,
            listOf(3.5f), listOf(4.7f, 3.5f), listOf(4208, 3120), null, null, null, null, listOf("AUTO", "CONTINUOUS_VIDEO"),
            aeLock = true, awbLock = true, ois = false, videoStabilization = false, yuvSizes = listOf("1280x960", "640x480"),
            fpsRanges = listOf("15-30", "30-30"), yuv640Fps = 30.0, yuv1280Fps = 30.0)

        fun diagnosis(gyro: Boolean = true, cam: CameraInfo = camera()) = Diagnosis(
            DeviceInfo("TestMaker", "Test Phone", "test", "test", "mt6762", "11", 30, listOf("arm64-v8a"), 8, 3800, 40_000),
            "Tidak Didukung", true,
            listOfNotNull(SensorInfo("accelerometer", "ACC", "v", 200.0, 39f, 0.001f),
                if (gyro) SensorInfo("gyroscope", "GYR", "v", 200.0, 35f, 0.001f) else null),
            listOf(cam))

        /** A sweep: [secs] long, frames at [fps], IMU at [imuHz], turning at [radPerS], moving with [accAmp] m/s². */
        fun sweep(secs: Double = 5.0, fps: Double = 15.0, imuHz: Double = 200.0, radPerS: Double = 0.35, accAmp: Double = 1.2): Pair<List<Frame>, List<Imu>> {
            val t0 = 1_000_000_000L
            val frames = (0 until (secs * fps).toInt()).map { i -> Frame(i, t0 + (i / fps * 1e9).toLong(), if (i % 7 == 0) 20.0 else 120.0 + i) }
            val imu = ArrayList<Imu>()
            val n = ((secs + 0.4) * imuHz).toInt()
            for (i in 0 until n) {
                val t = t0 - 200_000_000L + (i / imuHz * 1e9).toLong()
                val s = (t - t0) / 1e9
                imu += Imu("accelerometer", t, accAmp * sin(2 * PI * 0.8 * s), 9.81 + accAmp * cos(2 * PI * 0.8 * s), 0.3)
                imu += Imu("gyroscope", t + 1000, 0.0, radPerS, 0.0)
            }
            return frames to imu
        }
    }

    @Test fun diagnosisRules() {
        val good = Diagnostics.checks(diagnosis(), mapOf("accelerometer" to 198.0, "gyroscope" to 199.0))
        assertEquals(Level.OK, good.first { it.key == "gyro" }.level)
        assertEquals(Level.OK, good.first { it.key == "clock" }.level)
        assertEquals(Level.WARN, good.first { it.key == "focus" }.level)            // AF lock only, no manual focus
        assertEquals(Level.WARN, Diagnostics.verdict(good).first)
        // no gyroscope, or one listed but silent (the DT50, rotation vector silent too): usable with a warning, the
        // turn comes from the camera and the scale from the accelerometer; without an accelerometer: not usable
        val noGyro = Diagnostics.checks(diagnosis(gyro = false), mapOf("accelerometer" to 198.0))
        val silent = Diagnostics.checks(diagnosis(), mapOf("accelerometer" to 200.0, "gyroscope" to 0.0, "game_rotation_vector" to 200.0))
        assertEquals(Level.WARN, silent.first { it.key == "gyro" }.level)
        assertEquals(Level.WARN, Diagnostics.checks(diagnosis(), mapOf("accelerometer" to 200.0, "gyroscope" to 0.0)).first { it.key == "gyro" }.level)
        assertEquals(Level.FAIL, Diagnostics.checks(diagnosis(), mapOf("accelerometer" to 0.0, "gyroscope" to 0.0)).first { it.key == "gyro" }.level)
        assertEquals(Level.WARN, noGyro.first { it.key == "gyro" }.level)
        // separate clocks, slow sensors, a fixed-focus lens
        val other = Diagnostics.checks(diagnosis(cam = camera(ts = "UNKNOWN", minFocus = 0f)), mapOf("accelerometer" to 60.0, "gyroscope" to 100.0))
        assertEquals(Level.WARN, other.first { it.key == "clock" }.level)
        assertEquals(Level.FAIL, other.first { it.key == "accel_hz" }.level)
        assertEquals(Level.WARN, other.first { it.key == "gyro_hz" }.level)
        assertEquals(Level.OK, other.first { it.key == "focus" }.level)
        assertTrue(Diagnostics.json.encodeToString(Diagnosis.serializer(), diagnosis()).contains("\"timestampSource\": \"REALTIME\""))
    }

    @Test fun goodSweepPasses() {
        val (f, i) = sweep()
        val q = SweepAnalysis.analyse(f, i, sameClock = true)
        assertEquals(75, q.frames)
        assertEquals(15.0, q.savedFps, 0.3)
        assertEquals(200.0, q.gyroHz, 1.0)
        assertEquals(Math.toDegrees(0.35 * 5.4), q.turnDeg, 3.0)                // the IMU runs 0,2 s before and after the frames
        assertTrue(q.imuCoversFrames)
        assertTrue(q.accelStd > 0.5)
        assertEquals(11, q.blurry)                                             // every 7th frame is blurred
        assertTrue(q.bestFrame in 18..56)                                      // picked in the middle half
        assertTrue(q.checks.joinToString { "${it.key}=${it.level}" }, q.checks.none { it.level == Level.FAIL })
    }

    @Test fun stillOrTooShortSweepFails() {
        val (f, i) = sweep(radPerS = 0.0, accAmp = 0.0)
        val q = SweepAnalysis.analyse(f, i, sameClock = true)
        assertEquals(Level.FAIL, q.checks.first { it.key == "turn" }.level)
        assertEquals(Level.FAIL, q.checks.first { it.key == "acc" }.level)  // no acceleration: no metric scale
        val (f2, i2) = sweep(secs = 1.0)
        assertEquals(Level.FAIL, SweepAnalysis.analyse(f2, i2, true).checks.first { it.key == "dur" }.level)
        val (f3, _) = sweep()
        val noImu = SweepAnalysis.analyse(f3, emptyList(), true)
        assertEquals(Level.FAIL, noImu.checks.first { it.key == "gyro" }.level)
        // accelerometer only (the DT50 when neither gyroscope nor rotation vector send): usable, the turn from the camera
        val accOnly = SweepAnalysis.analyse(f3, i.filter { it.sensor == "accelerometer" }, true)
        assertEquals(Level.WARN, accOnly.checks.first { it.key == "gyro" }.level)
        assertEquals(Level.INFO, accOnly.checks.first { it.key == "turn" }.level)
    }

    /** A phone whose gyroscope is listed but silent (seen on a Urovo DT50), and whose camera clock is not the sensors'. */
    @Test fun silentGyroAndSeparateClock() {
        val (f, i) = sweep()
        // the same turn as a rotation vector: rotation about the device y axis at 0,35 rad/s, as unit quaternions
        val rv = i.filter { it.sensor == "gyroscope" }.map { g ->
            val ang = 0.35 * (g.t - 1_000_000_000L) / 1e9
            Imu("game_rotation_vector", g.t, 0.0, Math.sin(ang / 2), 0.0, Math.cos(ang / 2))
        }
        val noGyro = i.filter { it.sensor == "accelerometer" } + rv
        val q = SweepAnalysis.analyse(f, noGyro, sameClock = true)
        assertEquals(Math.toDegrees(0.35 * 5.4), q.turnDeg, 4.0)
        assertEquals(Level.WARN, q.checks.first { it.key == "imu" }.level)
        val rate = SweepAnalysis.gyroFromRotationVector(rv.take(3))
        assertEquals(0.35, rate.first().y, 1e-3)
        // camera clock 5 s behind the sensors, frames arriving 40 ms after their timestamps
        val shifted = f.map { it.copy(t = it.t - 5_000_000_000L, arrival = it.t + 40_000_000L) }
        val q2 = SweepAnalysis.analyse(shifted, i, sameClock = false)
        assertTrue(q2.imuCoversFrames)
        assertEquals("terpisah · dikoreksi", q2.checks.first { it.key == "sync" }.value)
        // and without arrival times there is nothing to map with
        val q3 = SweepAnalysis.analyse(f.map { it.copy(t = it.t - 5_000_000_000L) }, i, sameClock = false)
        assertEquals("terpisah", q3.checks.first { it.key == "sync" }.value)
    }

    @Test fun qualityReadsTheRecorderFiles() {
        val dir = File(app.filesDir, "dt_test").apply { deleteRecursively(); mkdirs() }
        val (f, i) = sweep()
        File(dir, "frames.csv").writeText("index,t_ns,sharpness,width,height,bytes\n" + f.joinToString("") { "${it.index},${it.t},${it.sharpness},1280,960,1000\n" })
        File(dir, "imu.csv").writeText("sensor,t_ns,v0,v1,v2,v3,v4,v5\n" + i.joinToString("") { "${it.sensor},${it.t},${it.x},${it.y},${it.z}\n" } +
            "magnetometer,1000,1,2,3\n")
        File(dir, "session.json").writeText("{\n  \"sensor_orientation\": 90,\n  \"timestamp_source\": \"REALTIME\"\n}\n")
        val q = SweepAnalysis.read(dir, ObjectPick.sameClock(dir))
        assertEquals(SweepAnalysis.analyse(f, i, true).copy(checks = emptyList()), q.copy(checks = emptyList()))
        assertEquals(90, ObjectPick.rotation(dir))
        assertTrue(ObjectPick.sameClock(dir))
    }

    @Test fun recorderHelpers() {
        assertEquals(1280 to 960, SweepRecorder.pickSize(listOf(4160 to 3120, 1920 to 1080, 1280 to 960, 1280 to 720, 640 to 480)))
        assertEquals(640 to 480, SweepRecorder.pickSize(listOf(1920 to 1080, 640 to 480, 320 to 240)))
        assertEquals(1440 to 1080, SweepRecorder.pickSize(listOf(1920 to 1080, 1440 to 1080, 320 to 240)))
        // a sharp edge pattern scores higher than the same pattern smeared sideways (motion blur)
        val w = 160; val h = 120
        val sharp = ByteArray(w * h) { i -> if (((i % w) / 8 + (i / w) / 8) % 2 == 0) 0 else 200.toByte() }
        val blur = ByteArray(w * h) { i -> val x = i % w; val y = i / w
            (((-6..6).sumOf { d -> (sharp[y * w + (x + d).coerceIn(0, w - 1)].toInt() and 255) }) / 13).toByte() }
        assertTrue(SweepRecorder.sharpness(sharp, w, h) > 3 * SweepRecorder.sharpness(blur, w, h))
        assertEquals(27.5, ObjectPick.cm("27,5")!!, 1e-9)
        assertEquals(30.0, ObjectPick.cm(" 30 ")!!, 1e-9)
        assertNull(ObjectPick.cm(""))
        assertNull(ObjectPick.cm("0"))
    }

    @Test fun testScreensNavigation() {
        File(app.filesDir, "ukurpaket.json").delete()
        val m = AppModel(app, checkDevice = false).apply {
            caps = DeviceCaps(ArState.UNSUPPORTED, depth = false, model = "test"); stack.clear(); stack.add(Screen.Home)
        }
        m.go(Screen.Diag); m.go(Screen.DtRecord)
        m.onHardwareScan("TSA-1")                                           // the scan key does not jump out of a recording
        assertEquals(Screen.DtRecord, m.screen)
        assertEquals("Scanner tidak dipakai di layar uji", m.message)
        m.openReview(File("/x/20261104_101010"))
        assertEquals(listOf(Screen.Home, Screen.Diag, Screen.DtReview("/x/20261104_101010")), m.stack.toList())
        assertTrue(m.store.dtDir.isDirectory)
    }
}
