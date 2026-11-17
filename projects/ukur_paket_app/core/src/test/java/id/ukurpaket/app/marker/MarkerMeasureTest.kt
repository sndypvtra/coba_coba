package id.ukurpaket.app.marker

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.photo.CalSample
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoMeasure
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Locale
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.sin

/**
 * The whole photo measurement with a printed marker next to the parcel: a carton on the floor and the A4 sheet beside it,
 * seen as the phone sees them (the marker found by Aruco in the 960 x 1280 picture, the parcel measured in the 480 x 640
 * one), with a depth model that guesses the camera height badly. The marker must bring the size back.
 */
class MarkerMeasureTest {
    private val kFull = MarkerScene.dt50()
    private val k = kFull.scaled(480, 640)

    /** A carton [l] x [w] x [h] metres standing on the floor under picture point (0.55, 0.45), turned [yawDeg]: its mask. */
    private fun cartonMask(scene: MarkerScene, l: Double, w: Double, hgt: Double, yawDeg: Double, at: Pair<Double, Double> = 0.55 to 0.42): Mask {
        val u = doubleArrayOf(scene.up.x.toDouble(), scene.up.y.toDouble(), scene.up.z.toDouble())
        val ray = doubleArrayOf((at.first * k.w - k.cx) / k.fx, (at.second * k.h - k.cy) / k.fy, 1.0)
        val c = ray.map { it * scene.heightM / -MarkerScene.dot(ray, u) }.toDoubleArray()
        val a0 = MarkerScene.cross(u, doubleArrayOf(1.0, 0.0, 0.0)).let { v -> val n = MarkerScene.norm(v); v.map { it / n } }.toDoubleArray()
        val b0 = MarkerScene.cross(u, a0)
        val y = Math.toRadians(yawDeg)
        val ax = DoubleArray(3) { a0[it] * cos(y) + b0[it] * sin(y) }
        val ay = MarkerScene.cross(u, ax)
        val o = DoubleArray(3) { c[it] - ax[it] * l / 2 - ay[it] * w / 2 }
        val edges = listOf(ax.map { it * l }, ay.map { it * w }, u.map { it * hgt })
        val bits = BooleanArray(k.w * k.h)
        for (py in 0 until k.h) for (px in 0 until k.w) {
            val r = doubleArrayOf((px + 0.5 - k.cx) / k.fx, (py + 0.5 - k.cy) / k.fy, 1.0)
            var t0 = 0.0; var t1 = Double.MAX_VALUE; var hit = true
            for (e in edges) {
                val l2 = e.sumOf { it * it }
                val ro = -(o[0] * e[0] + o[1] * e[1] + o[2] * e[2]) / l2; val rd = (r[0] * e[0] + r[1] * e[1] + r[2] * e[2]) / l2
                if (abs(rd) < 1e-12) { if (ro < 0 || ro > 1) { hit = false; break }; continue }
                var ta = -ro / rd; var tb = (1 - ro) / rd
                if (ta > tb) { val t = ta; ta = tb; tb = t }
                t0 = maxOf(t0, ta); t1 = minOf(t1, tb)
                if (t0 > t1) { hit = false; break }
            }
            bits[py * k.w + px] = hit && t0 > 0
        }
        return Mask(k.w, k.h, bits)
    }

    /** A depth map of a level floor [floorM] below the camera (what a depth model gives, its own scale included). */
    private fun floorDepth(up: V3, floorM: Double, near: Double? = null, nearBox: IntArray? = null): DepthMap {
        val z = FloatArray(k.w * k.h) { i ->
            val x = i % k.w; val y = i / k.w
            val den = -(k.ray(x + 0.5f, y + 0.5f) dot up)
            val h = if (near != null && nearBox != null && x in nearBox[0]..nearBox[2] && y in nearBox[1]..nearBox[3]) near else floorM
            if (den > 1e-3f) (h / den).toFloat() else 40f
        }
        return DepthMap(k.w, k.h, z)
    }

    private fun observe(scene: MarkerScene): List<MarkerObservation> =
        Aruco.detect(scene.render(), MarkerSheet.IDS).map { MarkerObservation.of(it, MarkerSheet.of(it.id)!!.sideMm / 1000, 0.5f) }

    @Test fun theMarkerFixesAWrongDepthGuess() {
        for ((n, c) in listOf(Triple(1.30, 45.0, 1.35), Triple(1.15, 52.0, 0.70), Triple(1.45, 38.0, 1.6)).withIndex()) {
            val (camH, down, aiFactor) = c
            val scene = MarkerScene(kFull, camH, down, 0.0, 1, 0.16, atX = 0.22, atY = 0.82, yawDeg = 18.0 + 30 * n, seed = n.toLong())
            val mask = cartonMask(scene, 0.40, 0.30, 0.20, 25.0 + 20 * n)
            val obs = observe(scene)
            assertEquals("marker found", 1, obs.size)
            val depth = floorDepth(scene.up, camH * aiFactor)
            val plain = PhotoMeasure.measure(mask, k, scene.up, depth, 1f, calibrated = false)
            val r = PhotoMeasure.measure(mask, k, scene.up, depth, 1f, calibrated = false, markers = obs)
            println(String.format(Locale.US, "camera %.2f m, AI x%.2f: without marker %.1f x %.1f x %.1f cm; with marker %.1f x %.1f x %.1f cm, camera %.3f m (marker %.3f m, sigma %.3f), score %d, ok %b, notes %s",
                camH, aiFactor, plain.lengthCm, plain.widthCm, plain.heightCm, r.lengthCm, r.widthCm, r.heightCm, r.cameraHeightM, r.markerCameraM, r.markerSigma, r.confidence, r.ok, r.notes))
            assertTrue(r.markerUsed())
            assertEquals(40.0, r.lengthCm, 1.2); assertEquals(30.0, r.widthCm, 1.2); assertEquals(20.0, r.heightCm, 1.2)
            assertEquals(camH, r.cameraHeightM, 0.015 * camH)
            // the plain measurement is off by the depth model's factor; the marker removes it
            assertEquals(40.0 * aiFactor, plain.lengthCm, 2.5 * aiFactor)
            assertTrue("box-like carton with a marker is 'Akurat' without calibration: ${r.notes}", r.ok)
            assertFalse(r.notes.any { it.startsWith("Mode foto belum dikalibrasi") })
        }
    }

    /** The marker on the floor while the parcel stands on a table: the depth map shows two planes; the marker is not used. */
    @Test fun aMarkerOnAnotherPlaneIsNotUsed() {
        val scene = MarkerScene(kFull, 1.30, 45.0, 0.0, 1, 0.16, atX = 0.22, atY = 0.86, yawDeg = 10.0)
        val mask = cartonMask(scene, 0.40, 0.30, 0.20, 30.0)
        val obs = observe(scene)
        val b = mask.bounds()!!
        val bw = b[2] - b[0]; val bh = b[3] - b[1]
        // round the parcel (the depth engine's window, 0,8 x its size each side) a table 0,55 m under the camera
        val around = intArrayOf((b[0] - 0.9 * bw).toInt(), (b[1] - 0.9 * bh).toInt(), (b[2] + 0.9 * bw).toInt(), (b[3] + 0.9 * bh).toInt())
        val depth = floorDepth(scene.up, 1.30, near = 0.55, nearBox = around)
        val r = PhotoMeasure.measure(mask, k, scene.up, depth, 1f, calibrated = false, markers = obs)
        println("marker on the floor, parcel on a table: used ${r.markerUsed()}, note ${r.markerNote}")
        assertFalse(r.markerUsed())
        assertNotNull(r.markerNote)
        assertTrue(r.notes.any { it.startsWith("Marker tidak dipakai") })
    }

    /** The combination: the marker leads; a depth guess far off is dropped, a focus distance that agrees joins. */
    @Test fun theMarkerLeadsTheOtherClues() {
        val p = PhotoMeasure.cameraHeight(hAi = 2.1f, standing = null, hMarker = 1.30f, sigmaMarker = 0.015)
        assertTrue(p.marker); assertFalse(p.ai)
        assertEquals(1.30f, p.heightM, 0.001f)
        val q = PhotoMeasure.cameraHeight(hAi = 1.33f, standing = null, hFocus = 1.31f, sigmaFocus = 0.05, hMarker = 1.30f, sigmaMarker = 0.015)
        assertTrue(q.marker && q.ai && q.focus)
        assertEquals(1.30f, q.heightM, 0.01f)
        val f = PhotoMeasure.cameraHeight(hAi = 1.3f, standing = null, hFocus = 0.5f, sigmaFocus = 0.05, hMarker = 1.30f, sigmaMarker = 0.015)
        assertFalse("a focus far off the marker is dropped", f.focus)
        // without a marker: exactly as before
        val old = PhotoMeasure.cameraHeight(hAi = 1.2f, standing = null, hFocus = 1.0f, sigmaFocus = 0.05)
        assertTrue(old.focus && !old.marker)
    }

    /** A marker photo teaches the phone's factor exactly as a carton measured with a tape would. */
    @Test fun aMarkerPhotoIsACalibrationSample() {
        val s = CalSample.fromMarker(aiRawCameraM = 1.60, markerCameraM = 1.30)
        assertEquals(1.30 / 1.60, Calibration.factor(listOf(s))!!, 1e-9)
        assertEquals(1.30, s.cameraM()!!, 1e-9)
        assertEquals(1.0, Calibration.mismatch(s), 1e-9)
        val st = Calibration.standing(listOf(s, CalSample.fromMarker(1.5, 1.34)))!!
        assertEquals(1.32, st.heightM, 1e-9)
    }
}
