package id.ukurpaket.app

import id.ukurpaket.app.measure.FloorCamera
import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.MarkerDetector
import id.ukurpaket.app.measure.MarkerSheet
import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.measure.SingleView
import id.ukurpaket.app.measure.convexHull
import id.ukurpaket.app.measure.inside
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.Locale
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Marker mode on synthetic photos: a camera with known focal length and pose sees the printed sheet and a
 * box on the floor. The photo is rendered pixel by pixel (2 x 2 supersampled, with floor texture and noise),
 * the sheet is found by MarkerDetector, and the box is measured from its outline by SingleView.
 */
class SingleViewTest {
    private val w = 1600; private val h = 1200; private val f = 1350.0

    private class Scene(val cam: FloorCamera, val sheetX: Double, val sheetY: Double, val sheetRot: Double,
                        val bx: Double, val by: Double, val bl: Double, val bw: Double, val bh: Double, val byaw: Double)

    private fun camera(c: DoubleArray, target: DoubleArray): FloorCamera {
        fun unit(v: DoubleArray): DoubleArray { val n = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); return DoubleArray(3) { v[it] / n } }
        fun cross(a: DoubleArray, b: DoubleArray) = doubleArrayOf(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        val z = unit(DoubleArray(3) { target[it] - c[it] })
        val x = unit(cross(z, doubleArrayOf(0.0, 0.0, 1.0)))
        val y = cross(z, x)
        val r = doubleArrayOf(x[0], x[1], x[2], y[0], y[1], y[2], z[0], z[1], z[2])
        val t = DoubleArray(3) { -(r[it * 3] * c[0] + r[it * 3 + 1] * c[1] + r[it * 3 + 2] * c[2]) }
        return FloorCamera(f, w / 2.0, h / 2.0, r, t)
    }

    private fun boxCorners(s: Scene, z: Double): List<DoubleArray> {
        val c = cos(s.byaw); val sn = sin(s.byaw)
        return listOf(-1 to -1, 1 to -1, 1 to 1, -1 to 1).map { (a, b) ->
            val u = a * s.bl / 2; val v = b * s.bw / 2
            doubleArrayOf(s.bx + u * c - v * sn, s.by + u * sn + v * c, z)
        }
    }

    /** Grey photo of the scene, and the box's true outline as a mask. */
    private fun render(s: Scene): Pair<IntArray, Mask> {
        val img = IntArray(w * h)
        val poly = convexHull((boxCorners(s, 0.0) + boxCorners(s, s.bh)).map { s.cam.project(it[0], it[1], it[2])!! })
        val mask = BooleanArray(w * h) { inside(poly, it % w + 0.5f, it / w + 0.5f) }
        val cr = cos(-s.sheetRot); val sr = sin(-s.sheetRot)
        fun shade(u: Double, v: Double): Double {
            val p = s.cam.floorPoint(u, v) ?: return 200.0
            // sheet frame
            val dx = p[0] - s.sheetX; val dy = p[1] - s.sheetY
            val sx = dx * cr - dy * sr; val sy = dx * sr + dy * cr
            if (abs(sx) < 0.105 && sy > -0.110 && sy < 0.187) {
                val m = maxOf(abs(sx), abs(sy))
                return if (m <= MarkerSheet.OUTER / 2 && m >= MarkerSheet.INNER / 2) 28.0 else 226.0
            }
            // speckled floor tiles
            val k = ((p[0] * 37).toInt() * 73856093) xor ((p[1] * 37).toInt() * 19349663)
            return 105.0 + (k and 31) + 18 * sin(p[0] * 90) * cos(p[1] * 70)
        }
        val rnd = java.util.Random(3)
        for (y in 0 until h) for (x in 0 until w) {
            val i = y * w + x
            val v = if (mask[i]) 80.0 + 10 * sin(x * 0.05) else
                (shade(x + 0.25, y + 0.25) + shade(x + 0.75, y + 0.25) + shade(x + 0.25, y + 0.75) + shade(x + 0.75, y + 0.75)) / 4
            img[i] = (v + rnd.nextGaussian() * 3).toInt().coerceIn(0, 255)
        }
        return img to Mask(w, h, mask)
    }

    private fun run(name: String, s: Scene, rows: StringBuilder, tolExif: Double): Unit {
        val (img, mask) = render(s)
        val t0 = System.nanoTime()
        val hit = MarkerDetector.detect(img, w, h)
        val detMs = (System.nanoTime() - t0) / 1e6
        assertNotNull("$name: sheet not found", hit)
        // corner accuracy against the true projection (any of the 4 rotations, the ring is symmetric)
        val cr = cos(s.sheetRot); val sr = sin(s.sheetRot)
        val truth = MarkerSheet.model.map { m -> s.cam.project(s.sheetX + m.a * cr - m.b * sr, s.sheetY + m.a * sr + m.b * cr, 0.0)!! }
        val err = hit!!.corners.maxOf { c -> truth.minOf { hypot(c.a - it.a, c.b - it.b) } }

        val exif = FloorCamera.fromHomography(hit.h, w, h, f)!!
        val est = FloorCamera.fromHomography(hit.h, w, h, null)
        val t1 = System.nanoTime()
        val r1 = SingleView.measure(mask, exif)!!
        val mMs = (System.nanoTime() - t1) / 1e6
        val r2 = est?.let { SingleView.measure(mask, it) }
        rows.append(String.format(Locale.US,
            "%-28s corners max err %.2f px (detect %.0f ms) | focal known: %.1f x %.1f x %.1f cm  IoU %.3f  band %.1f cm  conf %d (%.0f ms) | focal from sheet %.0f (true %.0f): %s\n",
            name, err, detMs, r1.lengthM * 100, r1.widthM * 100, r1.heightM * 100, r1.iou, r1.heightBandM * 100, SingleView.confidence(r1), mMs,
            est?.f ?: 0.0, f, r2?.let { String.format(Locale.US, "%.1f x %.1f x %.1f cm", it.lengthM * 100, it.widthM * 100, it.heightM * 100) } ?: "-"))
        assertTrue("$name corners $err px", err < 1.0)
        val truthLW = listOf(s.bl, s.bw).sortedDescending()
        assertEquals("$name L", truthLW[0], r1.lengthM.toDouble(), tolExif)
        assertEquals("$name W", truthLW[1], r1.widthM.toDouble(), tolExif)
        assertEquals("$name H", s.bh, r1.heightM.toDouble(), tolExif)
    }

    @Test fun measuresABoxNextToTheSheet() {
        val rows = StringBuilder("truth 40 x 30 x 20 cm unless noted\n")
        // a courier standing, phone at chest height, ~45 degrees down, parcel and sheet side by side
        run("oblique 45, box turned 30", Scene(camera(doubleArrayOf(-0.25, -0.75, 1.0), doubleArrayOf(0.0, 0.25, 0.0)),
            -0.30, 0.20, 0.3, 0.22, 0.30, 0.40, 0.30, 0.20, 0.52), rows, 0.012)
        run("steeper, box turned 10", Scene(camera(doubleArrayOf(0.1, -0.45, 1.15), doubleArrayOf(0.0, 0.2, 0.0)),
            -0.28, 0.25, -0.2, 0.20, 0.25, 0.40, 0.30, 0.20, 0.17), rows, 0.012)
        run("small parcel 25x18x8", Scene(camera(doubleArrayOf(0.3, -0.5, 0.9), doubleArrayOf(0.0, 0.2, 0.0)),
            -0.22, 0.25, 0.8, 0.12, 0.25, 0.25, 0.18, 0.08, 1.1), rows, 0.012)
        // the hard case: looking straight along the box, only its top and front visible
        run("square-on (hard)", Scene(camera(doubleArrayOf(0.2, -0.7, 0.95), doubleArrayOf(0.2, 0.3, 0.0)),
            -0.12, 0.20, 0.0, 0.25, 0.30, 0.40, 0.30, 0.20, 0.0), rows, 0.03)
        println(rows)
        File("build/conveyor").mkdirs()
        File("build/conveyor/single_view.txt").writeText(rows.toString())
    }

    @Test fun focalFromTheSheetAlone() {
        val s = Scene(camera(doubleArrayOf(-0.25, -0.75, 1.0), doubleArrayOf(0.0, 0.25, 0.0)), -0.30, 0.20, 0.3, 0.22, 0.30, 0.40, 0.30, 0.20, 0.52)
        val hit = MarkerDetector.detect(render(s).first, w, h)!!
        val est = FloorCamera.fromHomography(hit.h, w, h, null)!!
        assertEquals(f, est.f, f * 0.05)
        // and the sheet maps back onto itself
        val p = est.project(MarkerSheet.model[0].a.toDouble(), MarkerSheet.model[0].b.toDouble(), 0.0)
        assertNotNull(p)
    }

    /** The whole marker-mode chain on a ray-traced photo: sheet detection, MobileSAM tap, single-view size. */
    @Test fun photoTapMeasure() {
        val sc = SyntheticScene()
        val argb = sc.argb()
        val gray = IntArray(argb.size) { i -> val p = argb[i]; (((p shr 16) and 255) * 299 + ((p shr 8) and 255) * 587 + (p and 255) * 114) / 1000 }
        val hit = MarkerDetector.detect(gray, sc.w, sc.h)
        assertNotNull("sheet not found", hit)
        val cam = FloorCamera.fromHomography(hit!!.h, sc.w, sc.h, sc.f)!!
        val tap = sc.tapPoint()
        Segmenter(File("src/main/assets/sam/encoder.onnx").readBytes(), File("src/main/assets/sam/decoder.onnx").readBytes()).use { sam ->
            val m = sam.tap(sam.embed(argb, sc.w, sc.h), tap.a, tap.b)
            val iou = m.iou(sc.mask())
            val r = SingleView.measure(m, cam)!!
            val line = String.format(Locale.US, "synthetic photo, truth 38 x 28 x 18 cm: SAM mask IoU vs truth %.3f -> %.1f x %.1f x %.1f cm, box IoU %.3f, conf %d\n",
                iou, r.lengthM * 100, r.widthM * 100, r.heightM * 100, r.iou, SingleView.confidence(r))
            println(line)
            File("build/conveyor").mkdirs()
            File("build/conveyor/single_view_photo.txt").writeText(line)
            assertTrue("mask $iou", iou > 0.93f)
            assertEquals(0.38, r.lengthM.toDouble(), 0.015)
            assertEquals(0.28, r.widthM.toDouble(), 0.015)
            assertEquals(0.18, r.heightM.toDouble(), 0.015)
        }
    }
}
