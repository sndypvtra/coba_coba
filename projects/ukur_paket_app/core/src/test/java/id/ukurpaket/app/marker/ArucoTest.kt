package id.ukurpaket.app.marker

import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.V3
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.Locale
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.max

/**
 * The marker detector and the camera height it gives, on synthetic photos of the printed sheet on a floor (MarkerScene:
 * DT50-like lens, 960 x 1280 upright picture, anti-aliased, blurred, unevenly lit, noisy). Set -Dukur.markerOut=<dir>
 * to keep the pictures and their true corners (tools/marker/check_opencv.py compares OpenCV's detector on them).
 */
class ArucoTest {
    private val out = System.getProperty("ukur.markerOut")?.let(::File)
    private val ids = setOf(1, 2)

    private fun cornerError(d: MarkerDetection, truth: List<P2>) = d.corners.indices.maxOf { hypot(d.corners[it].a - truth[it].a, d.corners[it].b - truth[it].b) }

    private fun keep(name: String, s: MarkerScene, img: Luma) {
        val o = out ?: return
        s.save(img, File(o, "$name.png"))
        File(o, "$name.json").writeText("{\"id\": ${s.id}, \"corners\": [" + s.truth().joinToString(", ") { "[%.4f, %.4f]".format(Locale.US, it.a, it.b) } + "]}\n")
    }

    /** The code turned as numpy's rot90 turns the 4 x 4 bit matrix (OpenCV matches markers in those four turns). */
    @Test fun turnIsNumpyRot90() {
        for (code in Aruco.DICT_4X4_50) {
            val m = Array(4) { i -> IntArray(4) { j -> (code shr (15 - (i * 4 + j))) and 1 } }
            val r = Array(4) { i -> IntArray(4) { j -> m[j][3 - i] } }
            var v = 0; for (i in 0 until 4) for (j in 0 until 4) v = (v shl 1) or r[i][j]
            assertEquals(v, Aruco.turn(code))
            assertEquals(code, Aruco.turn(Aruco.turn(Aruco.turn(Aruco.turn(code)))))
        }
    }

    /** The two sheet ids differ from each other and from their own turns in at least 8 bits: one wrong bit is never a swap. */
    @Test fun sheetIdsAreFarApart() {
        fun d(a: Int, b: Int) = (0 until 4).minOf { k -> var x = b; repeat(k) { x = Aruco.turn(x) }; Integer.bitCount(a xor x) }
        val a = Aruco.DICT_4X4_50[1]; val b = Aruco.DICT_4X4_50[2]
        assertTrue(d(a, b) >= 8)
        for (c in listOf(a, b)) assertTrue((1..3).minOf { k -> var x = c; repeat(k) { x = Aruco.turn(x) }; Integer.bitCount(c xor x) } >= 8)
    }

    @Test fun findsTheSheetAndItsCornersInManyPoses() {
        val k = MarkerScene.dt50()
        data class Pose(val h: Double, val down: Double, val roll: Double, val yaw: Double, val atX: Double, val atY: Double, val id: Int, val side: Double)
        val poses = listOf(
            Pose(1.30, 45.0, 0.0, 15.0, 0.50, 0.75, 1, 0.16),     // standing, A4 next to the parcel
            Pose(1.40, 35.0, 4.0, 70.0, 0.35, 0.80, 1, 0.16),     // shallower, sheet turned
            Pose(1.20, 60.0, -8.0, 160.0, 0.60, 0.65, 1, 0.16),   // steeper, upside down on the floor
            Pose(1.50, 40.0, 2.0, -35.0, 0.45, 0.70, 2, 0.24),    // A3 from further
            Pose(0.70, 55.0, 12.0, 100.0, 0.50, 0.70, 1, 0.16),   // crouching
            Pose(1.30, 30.0, 0.0, 5.0, 0.50, 0.62, 2, 0.24),      // far and flat: A3
        )
        for ((n, p) in poses.withIndex()) {
            val s = MarkerScene(k, p.h, p.down, p.roll, p.id, p.side, p.atX, p.atY, p.yaw, seed = n.toLong())
            val img = s.render()
            keep("pose_$n", s, img)
            val t0 = System.nanoTime()
            val found = Aruco.detect(img, ids)
            val ms = (System.nanoTime() - t0) / 1e6
            assertEquals("pose $n: one marker", 1, found.size)
            val d = found[0]
            assertEquals("pose $n id", p.id, d.id)
            val err = cornerError(d, s.truth())
            val fit = MarkerScale.fit(MarkerObservation.of(d, p.side), k, s.up)
            println(String.format(Locale.US, "pose %d: id %d, side %.0f px, corners within %.2f px (sigma %.2f), height %.3f m for %.2f (%.2f%%), residual %.4f, tilt %.1f deg, %.0f ms",
                n, d.id, d.sidePx, err, d.cornerSigmaPx, fit.heightM, p.h, (fit.heightM / p.h - 1) * 100, fit.residual, fit.tiltDeg, ms))
            assertTrue("pose $n corners off by $err px", err < 0.35f)
            assertTrue("pose $n usable: ${fit.reason}", fit.usable)
            assertEquals("pose $n height", p.h, fit.heightM, 0.01 * p.h)
        }
    }

    /** Blur and noise worse than a still DT50 photo: the corners degrade gracefully; the height stays within 2 %. */
    @Test fun blurNoiseAndShade() {
        val k = MarkerScene.dt50()
        for ((n, c) in listOf(Triple(1.6, 6.0, 0.4), Triple(2.4, 8.0, 0.5), Triple(0.5, 12.0, 0.6)).withIndex()) {
            val s = MarkerScene(k, 1.3, 45.0, 3.0, 1, 0.16, yawDeg = 30.0, blurPx = c.first, noise = c.second, shading = c.third, seed = 10L + n)
            val img = s.render(); keep("blur_$n", s, img)
            val d = Aruco.detect(img, ids).firstOrNull()
            assertNotNull("blur ${c.first} noise ${c.second}: found", d)
            val fit = MarkerScale.fit(MarkerObservation.of(d!!, 0.16), k, s.up)
            println(String.format(Locale.US, "blur %.1f px, noise %.0f: corners within %.2f px, height %.2f%% off, sigma %.3f",
                c.first, c.second, cornerError(d, s.truth()), (fit.heightM / 1.3 - 1) * 100, fit.sigma))
            assertEquals(1.3, fit.heightM, 0.02 * 1.3)
        }
    }

    /** The scale of the camera height from the accelerometer's level: 1-2 degrees off cost about as many percent. */
    @Test fun aSlightlyWrongLevelCostsLittle() {
        val k = MarkerScene.dt50()
        val s = MarkerScene(k, 1.3, 45.0, 0.0, 1, 0.16, yawDeg = 25.0)
        val d = Aruco.detect(s.render(), ids).first()
        for (deg in listOf(0.5, 1.0, 2.0)) {
            for (axis in listOf("pitch", "roll")) {
                val a = Math.toRadians(deg)
                val u = s.up
                val v = if (axis == "pitch") V3(u.x, (u.y * kotlin.math.cos(a) - u.z * kotlin.math.sin(a)).toFloat(), (u.y * kotlin.math.sin(a) + u.z * kotlin.math.cos(a)).toFloat())
                        else V3((u.x * kotlin.math.cos(a) - u.y * kotlin.math.sin(a)).toFloat(), (u.x * kotlin.math.sin(a) + u.y * kotlin.math.cos(a)).toFloat(), u.z)
                val fit = MarkerScale.fit(MarkerObservation.of(d, 0.16), k, v)
                println(String.format(Locale.US, "level %s off by %.1f deg: height %.2f%% off, residual %.4f, tilt %.1f deg", axis, deg, (fit.heightM / 1.3 - 1) * 100, fit.residual, fit.tiltDeg))
                assertEquals(1.3, fit.heightM, 0.035 * 1.3)
            }
        }
    }

    @Test fun aSheetThatIsNotFlatOnTheFloorIsNotUsed() {
        val k = MarkerScene.dt50()
        val s = MarkerScene(k, 1.3, 45.0, 0.0, 1, 0.16, yawDeg = 25.0, sheetTiltDeg = 25.0)
        val d = Aruco.detect(s.render(), ids).firstOrNull()
        assertNotNull(d)
        val fit = MarkerScale.fit(MarkerObservation.of(d!!, 0.16), k, s.up)
        println("sheet tilted 25 deg: residual ${fit.residual}, tilt ${fit.tiltDeg}, ${fit.reason}")
        assertFalse(fit.usable)
    }

    @Test fun aCoveredCornerOrAMarkerOutsideThePictureGivesNothing() {
        val k = MarkerScene.dt50()
        val base = MarkerScene(k, 1.3, 45.0, 0.0, 1, 0.16, yawDeg = 0.0)
        val t = base.truth()
        val cx = t[2].a / k.w; val cy = t[2].b / k.h
        val covered = MarkerScene(k, 1.3, 45.0, 0.0, 1, 0.16, yawDeg = 0.0, covers = listOf(doubleArrayOf(cx - 0.05, cy - 0.03, cx + 0.05, cy + 0.03)))
        assertTrue(Aruco.detect(covered.render(), ids).isEmpty())
        val cut = MarkerScene(k, 1.3, 45.0, 0.0, 1, 0.16, atX = 0.03, atY = 0.7)
        assertTrue(Aruco.detect(cut.render(), ids).isEmpty())
    }

    /** Other markers, squares, tiles and noise: never taken for a sheet. */
    @Test fun noFalseMarkers() {
        val k = MarkerScene.dt50(640, 853)
        for (other in listOf(0, 3, 7, 17, 33, 49)) {
            val s = MarkerScene(k, 1.0, 50.0, 0.0, other, 0.16, seed = other.toLong())
            assertTrue("id $other is not a sheet", Aruco.detect(s.render(), ids).isEmpty())
        }
        val rnd = java.util.Random(5)
        repeat(10) { n ->
            val covers = List(30) { val x = rnd.nextDouble(); val y = rnd.nextDouble(); val w = 0.02 + rnd.nextDouble() * 0.15; doubleArrayOf(x, y, x + w, y + w * (0.5 + rnd.nextDouble())) }
            // the scene's marker hidden far away under a cover, so only clutter is left
            val s = MarkerScene(k, 1.0, 50.0, 0.0, 1, 0.16, covers = covers + listOf(doubleArrayOf(0.0, 0.4, 1.0, 1.0)), seed = 100L + n)
            assertTrue("clutter $n", Aruco.detect(s.render(), ids).isEmpty())
        }
    }

    /** Small in the picture: found up to a point, and below MarkerScale.MIN_SIDE_PX (in the 480 picture) set aside. */
    @Test fun tooSmallForAScale() {
        val k = MarkerScene.dt50()
        val s = MarkerScene(k, 2.6, 22.0, 0.0, 1, 0.16, atY = 0.6)
        val d = Aruco.detect(s.render(), ids).firstOrNull()
        if (d != null) {
            val fit = MarkerScale.fit(MarkerObservation.of(d, 0.16, 0.5f), k.scaled(480, 640), s.up)
            println("small: side ${d.sidePx} px at full size -> usable ${fit.usable} (${fit.reason})")
            assertTrue(fit.sidePx >= MarkerScale.MIN_SIDE_PX || !fit.usable)
        }
    }

    /** Both sheets in one photo: both found, each with its own id, and their heights agree. */
    @Test fun twoSheets() {
        val k = MarkerScene.dt50()
        val a = MarkerScene(k, 1.3, 45.0, 0.0, 1, 0.16, atX = 0.3, atY = 0.75, yawDeg = 10.0)
        val b = MarkerScene(k, 1.3, 45.0, 0.0, 2, 0.24, atX = 0.72, atY = 0.62, yawDeg = -20.0)
        val ia = a.render(); val ib = b.render()
        // the left half from one, the right half from the other (the sheets do not overlap)
        val px = ByteArray(k.w * k.h) { i -> if (i % k.w < k.w / 2) ia.px[i] else ib.px[i] }
        val found = Aruco.detect(Luma(k.w, k.h, px), ids)
        assertEquals(setOf(1, 2), found.map { it.id }.toSet())
        val fits = found.map { MarkerScale.fit(MarkerObservation.of(it, if (it.id == 1) 0.16 else 0.24), k, a.up) }
        val c = MarkerScale.combine(fits)!!
        println("two sheets: " + fits.joinToString { "id ${it.id} %.3f m".format(Locale.US, it.heightM) } + " -> %.3f m".format(Locale.US, c.heightM))
        assertEquals(1.3, c.heightM, 0.01 * 1.3)
    }

    /** The live preview runs on a half-size grey picture: still found there, a few frames a second. */
    @Test fun halfSizePreview() {
        val k = MarkerScene.dt50()
        val s = MarkerScene(k, 1.3, 45.0, 0.0, 1, 0.16)
        val half = s.render().half()
        var found: List<MarkerDetection> = emptyList()
        val t0 = System.nanoTime()
        repeat(5) { found = Aruco.detect(half, ids) }
        val ms = (System.nanoTime() - t0) / 5e6
        println("preview 480 x 640: ${found.size} found, %.1f ms each on this PC".format(Locale.US, ms))
        assertEquals(1, found.size)
        assertTrue(cornerError(found[0].scaled(2f), s.truth()) < 1.0f)
        assertTrue(max(0.0, ms) < 400)
        assertTrue(abs(found[0].sidePx * 2 - s.truth().let { t -> (0 until 4).map { i -> hypot(t[(i + 1) % 4].a - t[i].a, t[(i + 1) % 4].b - t[i].b) }.average() }.toFloat()) < 2f)
    }
}
