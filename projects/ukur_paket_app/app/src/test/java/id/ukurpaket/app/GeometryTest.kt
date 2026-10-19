package id.ukurpaket.app

import id.ukurpaket.app.measure.BoxFitter
import id.ukurpaket.app.measure.FloorPlane
import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.PointAccumulator
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.measure.convexHull
import id.ukurpaket.app.measure.minAreaRect
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

class GeometryTest {
    private val rnd = Random(7)

    /** Points on the visible faces (top + two sides) of a box standing on y = floorY, in ARCore's y-up world. */
    private fun box(cx: Float, cz: Float, l: Float, w: Float, h: Float, yaw: Float, floorY: Float, noise: Float): List<V3> {
        val out = ArrayList<V3>()
        val c = cos(yaw); val s = sin(yaw)
        fun put(a: Float, b: Float, y: Float) {
            val x = cx + a * c - b * s; val z = cz + a * s + b * c
            out.add(V3(x + gauss(noise), floorY + y + gauss(noise), z + gauss(noise)))
        }
        var a = -l / 2
        while (a <= l / 2) { var b = -w / 2; while (b <= w / 2) { put(a, b, h); b += 0.008f }; a += 0.008f }
        var y = 0.004f
        while (y <= h) {
            a = -l / 2; while (a <= l / 2) { put(a, -w / 2, y); a += 0.01f }
            var b = -w / 2; while (b <= w / 2) { put(-l / 2, b, y); b += 0.01f }
            y += 0.01f
        }
        return out
    }

    private fun floor(y: Float, half: Float): List<V3> {
        val out = ArrayList<V3>()
        var x = -half; while (x <= half) { var z = -half; while (z <= half) { out.add(V3(x, y + gauss(0.003f), z)); z += 0.02f }; x += 0.02f }
        return out
    }

    private fun gauss(sd: Float) = (rnd.nextFloat() + rnd.nextFloat() + rnd.nextFloat() - 1.5f) * 2f * sd

    @Test fun measuresARotatedBoxAndIgnoresItsNeighbour() {
        val fy = -0.8f
        val pts = floor(fy, 1.2f) + box(0f, 0f, 0.40f, 0.30f, 0.20f, 0.5f, fy, 0.002f) +
            box(0.45f, 0.05f, 0.25f, 0.25f, 0.30f, 0f, fy, 0.002f)          // 10+ cm away, taller
        val plane = FloorPlane(V3(0f, fy, 0f), V3(0f, 1f, 0f))
        val seg = BoxFitter.segment(pts, plane, seed = V3(0f, fy + 0.2f, 0f))
        assertNotNull(seg)
        val r = BoxFitter.fit(seg!!)!!
        assertEquals(0.40f, r.lengthM, 0.012f)
        assertEquals(0.30f, r.widthM, 0.012f)
        assertEquals(0.20f, r.heightM, 0.008f)
        assertEquals(4, r.topCorners.size)
    }

    @Test fun accumulatorAveragesRepeatedPoints() {
        val acc = PointAccumulator(0.01f)
        repeat(5) { acc.add(0.1031f, 0.2f, -0.3f); acc.endFrame() }
        acc.add(0.5f, 0.5f, 0.5f)
        assertEquals(1, acc.points(minCount = 2).size)
        assertEquals(5, acc.frames)
    }

    @Test fun minAreaRectOfARotatedSquare() {
        val pts = listOf(P2(0f, 1f), P2(1f, 0f), P2(2f, 1f), P2(1f, 2f), P2(1f, 1f))
        val r = minAreaRect(convexHull(pts))
        assertEquals(1.4142f, r.l, 0.001f)
        assertEquals(1.4142f, r.w, 0.001f)
    }

    @Test fun confidenceIsHighForADenseFlatScan() {
        val fy = 0f
        val pts = box(0f, 0f, 0.3f, 0.2f, 0.1f, 0f, fy, 0.001f)
        val r = BoxFitter.fit(BoxFitter.segment(pts, FloorPlane(V3(0f, 0f, 0f), V3(0f, 1f, 0f)), V3(0f, 0.1f, 0f))!!)!!
        assertTrue(BoxFitter.confidence(r, frames = 20, depth = true) >= 75)
        assertTrue(BoxFitter.confidence(r, frames = 20, depth = false) < 75)
    }

    @Test fun floorNoiseDoesNotGrowTheFootprint() {
        val fy = 0f
        // floor with 1,5 cm depth noise around a 30 x 20 x 10 cm box: some floor points rise above 1,2 cm
        val noisy = ArrayList<V3>()
        var x = -0.6f
        while (x <= 0.6f) { var z = -0.6f; while (z <= 0.6f) { noisy.add(V3(x, fy + gauss(0.008f), z)); z += 0.012f }; x += 0.012f }
        val pts = noisy + box(0f, 0f, 0.30f, 0.20f, 0.10f, 0f, fy, 0.004f)
        val plane = FloorPlane(V3(0f, fy, 0f), V3(0f, 1f, 0f))
        val r = BoxFitter.fit(BoxFitter.segment(pts, plane, V3(0f, 0.1f, 0f), minH = 0.02f, minPerCell = 2)!!)!!
        assertEquals(0.30f, r.lengthM, 0.02f)
        assertEquals(0.20f, r.widthM, 0.02f)
        assertEquals(0.10f, r.heightM, 0.01f)
    }
}
