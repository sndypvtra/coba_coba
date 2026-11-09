package id.ukurpaket.app

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.photo.CalSample
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.DepthModel
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoMeasure
import id.ukurpaket.app.photo.PhotoResult
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.double
import kotlinx.serialization.json.float
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.Locale
import kotlin.math.abs

/**
 * The photo mode's engine on synthetic hand-held photos (tools/photo/synth_photo.py: 480 x 640, f 420 px, the camera
 * 0,75-1,15 m above the floor looking 38-62 deg down at a 40 x 30 x 20 cm carton, a gallon or a sack). The geometry is
 * checked with the true camera height; the depth model's own guess of that height is what the phone's calibration
 * corrects, and synthetic pictures say little about it (they look nothing like the photos it learnt from), so the
 * real-model test only checks that it runs and prints what it guessed.
 */
class PhotoMeasureTest {
    private class Shot(val name: String, val argb: TestImages.Argb, val mask: Mask, val up: V3, val camH: Float, val box: IntArray)
    private class Set(val kind: String, val truth: List<Double>, val k: Intrinsics, val shots: List<Shot>)

    private fun load(name: String): Set {
        val dir = File(javaClass.getResource("/photo/$name/truth.json")!!.toURI()).parentFile
        val t = Json.parseToJsonElement(File(dir, "truth.json").readText()).jsonObject
        val k = Intrinsics(t["fx"]!!.jsonPrimitive.float, t["fy"]!!.jsonPrimitive.float, t["cx"]!!.jsonPrimitive.float, t["cy"]!!.jsonPrimitive.float,
            t["width"]!!.jsonPrimitive.int, t["height"]!!.jsonPrimitive.int)
        val shots = t["photos"]!!.jsonArray.map { e ->
            val p = e.jsonObject
            val img = TestImages.read(File(dir, p["photo"]!!.jsonPrimitive.content).inputStream())
            val m = TestImages.read(File(dir, p["mask"]!!.jsonPrimitive.content).inputStream())
            val up = p["up"]!!.jsonArray.map { it.jsonPrimitive.float }
            Shot("$name/${p["photo"]!!.jsonPrimitive.content}", img, Mask(m.w, m.h, BooleanArray(m.w * m.h) { (m.px[it] and 255) > 127 }),
                V3(up[0], up[1], up[2]), p["camera_height_m"]!!.jsonPrimitive.float, p["box"]!!.jsonArray.map { it.jsonPrimitive.int }.toIntArray())
        }
        return Set(t["kind"]!!.jsonPrimitive.content, t["size_cm"]!!.jsonArray.map { it.jsonPrimitive.double }, k, shots)
    }

    private val sets = listOf("box_3", "box_7", "cylinder_3", "sack_3", "phone_3", "phone_7", "mailer_3")

    /** A depth map that is exactly the floor at [camH] below the camera (object pixels: anything, they are skipped). */
    private fun floorDepth(k: Intrinsics, up: V3, camH: Float, mask: Mask): DepthMap {
        val z = FloatArray(k.w * k.h) { i ->
            val x = i % k.w; val y = i / k.w
            val den = -(k.ray(x + 0.5f, y + 0.5f) dot up)
            if (mask.bits[i]) 0.5f else if (den > 1e-3f) camH / den else 40f
        }
        return DepthMap(k.w, k.h, z)
    }

    @Test fun boxesFromTheirOutlineGivenTheCameraHeight() {
        for (name in sets) {
            val s = load(name)
            for (sh in s.shots) {
                val trace = ArrayList<String>()
                val m = PhotoMeasure.metrology(sh.mask, s.k, sh.up, sh.camH, trace = { trace += it })
                val got = listOf(m.lengthM * 100.0, m.widthM * 100.0, m.heightM * 100.0)
                println(String.format(Locale.US, "%-26s truth %s -> %.1f x %.1f x %.1f cm, outline IoU %.3f%s", sh.name,
                    s.truth.joinToString(" x ") { "%.1f".format(Locale.US, it) }, got[0], got[1], got[2], m.iou, if (m.flat) " (flat)" else ""))
                if (System.getProperty("ukur.trace") != null || s.kind in setOf("phone", "mailer")) trace.forEach { println("      $it") }
                when (s.kind) {
                    "box" -> {
                        for (i in 0..2) assertEquals("${sh.name} side $i", s.truth[i], got[i], 1.0)
                        assertTrue("${sh.name} box-like", m.iou >= PhotoMeasure.BOX_IOU)
                    }
                    "phone", "mailer" -> {
                        // lying flat: length and width as a box's; the thickness is read roughly (a few cm at most)
                        val tol = if (s.kind == "phone") 1.5 else 2.5
                        for (i in 0..1) assertEquals("${sh.name} side $i", s.truth[i], got[i], tol)
                        assertTrue("${sh.name} thickness ${got[2]}", got[2] <= s.truth[2] + 2.5)
                        assertTrue("${sh.name} read as flat", m.flat)
                    }
                    "cylinder" -> {
                        // a round object: rough (its lid's curve hides where the side ends), and flagged as not a box
                        for (i in 0..2) assertEquals("${sh.name} side $i", s.truth[i], got[i], 0.35 * s.truth[i])
                        assertTrue("${sh.name} not box-like", m.iou < PhotoMeasure.BOX_IOU)
                    }
                    else -> {
                        // a sack: its footprint is fair, its height (bulging sides) is under: flagged, never "Akurat"
                        assertEquals("${sh.name} length", s.truth[0], got[0], 0.15 * s.truth[0])
                        assertTrue("${sh.name} not box-like", m.iou < PhotoMeasure.BOX_IOU)
                    }
                }
            }
        }
    }

    @Test fun everySizeScalesWithTheCameraHeight() {
        val s = load("box_3"); val sh = s.shots[0]
        val a = PhotoMeasure.metrology(sh.mask, s.k, sh.up, sh.camH)
        val b = PhotoMeasure.metrology(sh.mask, s.k, sh.up, sh.camH * 1.2f)
        assertEquals(a.lengthM * 1.2f, b.lengthM, 0.004f)
        assertEquals(a.widthM * 1.2f, b.widthM, 0.004f)
        assertEquals(a.heightM * 1.2f, b.heightM, 0.004f)
    }

    @Test fun cameraHeightFromTheFloorAroundTheObject() {
        for (name in listOf("box_3", "sack_3")) {
            val s = load(name)
            for (sh in s.shots) {
                val f = PhotoMeasure.floor(floorDepth(s.k, sh.up, sh.camH, sh.mask), sh.mask, s.k, sh.up)
                assertEquals(sh.name, sh.camH, f.heightM, sh.camH * 0.01f)
                assertTrue("${sh.name} level floor", f.tiltDeg < 2f)
                assertFalse(f.wide)
            }
        }
        // a depth model 20 % off in scale: the height (and so every size) is 20 % off, which calibration then removes
        val s = load("box_7"); val sh = s.shots[1]
        val d = floorDepth(s.k, sh.up, sh.camH, sh.mask).let { m -> DepthMap(m.w, m.h, FloatArray(m.z.size) { m.z[it] * 1.2f }) }
        val r = PhotoMeasure.measure(sh.mask, s.k, sh.up, d, scale = 1f, calibrated = false)
        assertEquals(s.truth[0] * 1.2, r.lengthCm, 1.5)
        assertEquals(s.truth[2] * 1.2, r.heightCm, 1.5)
        assertFalse("uncalibrated is never Akurat", r.ok)
        val cal = PhotoMeasure.measure(sh.mask, s.k, sh.up, d, scale = (1 / 1.2).toFloat(), calibrated = true)
        for (i in 0..2) assertEquals(s.truth[i], listOf(cal.lengthCm, cal.widthCm, cal.heightCm)[i], 1.0)
        assertEquals(r.rawCm[0], cal.rawCm[0], 0.01)                     // what calibration compares stays the same
        assertTrue("a calibrated carton is Akurat: ${cal.notes}", cal.ok)
        assertTrue(cal.boxLike)
        assertEquals(16, cal.corners.size)
    }

    @Test fun badPhotosAreSaidPlainly() {
        val s = load("box_3"); val sh = s.shots[0]
        // the object cut by the picture's edge: said so (or refused with a reason), never "Akurat"
        val w = sh.mask.w; val shift = sh.box[0] + (sh.box[2] - sh.box[0]) / 2
        val cut = Mask(w, sh.mask.h, BooleanArray(sh.mask.bits.size) { i -> val sx = i % w + shift; sx < w && sh.mask.bits[(i / w) * w + sx] })
        val rc = runCatching { PhotoMeasure.measure(cut, s.k, sh.up, floorDepth(s.k, sh.up, sh.camH, cut), 1f, calibrated = true) }
        rc.onSuccess { r -> assertFalse(r.ok); assertTrue(r.notes.toString(), r.notes.any { it.startsWith("Paket terpotong") }) }
            .onFailure { assertTrue(it.message.orEmpty().isNotBlank()) }
        // a phone lying flat (the case seen on the DT50: read 12 cm thick before 0.4.1): flat, and never "Akurat"
        val p = load("phone_7"); val ps = p.shots[0]
        val flat = PhotoMeasure.measure(ps.mask, p.k, ps.up, floorDepth(p.k, ps.up, ps.camH, ps.mask), 1f, calibrated = true)
        assertTrue("${flat.heightCm}", flat.heightCm < 3.0)
        assertFalse(flat.ok)
        assertTrue(flat.notes.toString(), flat.notes.any { it.startsWith("Benda pipih") })
        // a phone held upright (no floor below the horizon in view): refused with advice
        val level = V3(0f, -1f, 0f)
        val e = runCatching { PhotoMeasure.measure(sh.mask, s.k, level, floorDepth(s.k, sh.up, sh.camH, sh.mask), 1f, true) }.exceptionOrNull()
        assertNotNull(e); assertTrue(e!!.message!!, e.message!!.contains("tegak"))
    }

    @Test fun lensFromCamera2FactsTurnedUpright() {
        // a 1280 x 960 stream of a 4000 x 3000 sensor 5,6 mm wide with a 4,0 mm lens; sensor orientation 90
        val k = Intrinsics.fromCamera(4.0f, 5.6f, 4000, 4000, 3000, null, 1280, 960, 90)
        assertEquals(960, k.w); assertEquals(1280, k.h)
        assertEquals(4.0f / 5.6f * 4000 * (1280f / 4000), k.fx, 0.01f)
        assertEquals(480f, k.cx, 0.01f); assertEquals(640f, k.cy, 0.01f)
        // the factory calibration, with an off-centre principal point, follows the turn as Yuv.argb does
        val c = Intrinsics.fromCamera(0f, 0f, 4000, 4000, 3000, floatArrayOf(3000f, 3000f, 2100f, 1400f, 0f), 1280, 960, 90)
        val kk = 1280f / 4000
        assertEquals(960 - 1400f * kk, c.cx, 0.01f)        // upright x = sh - sensor y
        assertEquals(2100f * kk, c.cy, 0.01f)              // upright y = sensor x
        // a 16:9 stream is a centred crop of the 4:3 array
        val w = Intrinsics.fromCamera(4.0f, 5.6f, 4000, 4000, 3000, null, 1280, 720, 0)
        assertEquals(4.0f / 5.6f * 4000 * (1280f / 4000), w.fx, 0.01f)
        // a still portrait phone: up is picture-up; looking 45 deg down at the floor
        val up = Intrinsics.upFromAccel(0f, 9.81f, 0f)
        assertEquals(-1f, up.y, 1e-6f)
        val down45 = Intrinsics.upFromAccel(0f, 6.94f, 6.94f)        // top tilted away, screen facing up at the user
        assertEquals(-0.707f, down45.z, 0.01f)
    }

    @Test fun severalPhotosAndTheCalibration() {
        fun r(l: Double, w: Double, h: Double, ok: Boolean = true) = PhotoResult(l, w, h, listOf(l, w, h), 1.0, 1.0, 45.0, 0.97, true,
            List(16) { 0.5f }, 90, ok, emptyList())
        val c = PhotoMeasure.combine(listOf(r(40.0, 30.0, 20.0), r(42.0, 31.0, 21.0), r(41.0, 29.0, 19.0)))
        assertEquals(41.0, c.lengthCm, 1e-9); assertEquals(30.0, c.widthCm, 1e-9); assertEquals(20.0, c.heightCm, 1e-9)
        assertTrue(c.ok)
        val far = PhotoMeasure.combine(listOf(r(40.0, 30.0, 20.0), r(52.0, 30.0, 20.0)))
        assertFalse(far.ok); assertTrue(far.notes.any { it.startsWith("Hasil antar foto beda") })

        // the phone measured 10 % large: the factor is 1 / 1,1; long and short sides are matched whatever their order
        val s = listOf(CalSample(listOf(44.0, 33.0, 22.0), listOf(30.0, 40.0, 20.0)), CalSample(listOf(55.0, 22.0, 11.0), listOf(50.0, 20.0, 10.0)))
        assertEquals(1 / 1.1, Calibration.factor(s)!!, 1e-9)
        assertEquals(0.0, Calibration.spread(s), 1e-9)
        assertEquals(null, Calibration.factor(emptyList()))
        assertEquals(1.0, Calibration.mismatch(s[0]), 1e-9)

        // the 90 x 30 x 16 box read 263 x 130 x 5: the three ratios disagree, so the photo read the shape wrong
        val wrong = CalSample(listOf(263.0, 130.0, 5.0), listOf(90.0, 30.0, 16.0), model = DepthModel.ID)
        assertTrue(Calibration.mismatch(wrong) > Calibration.MISMATCH)
        // a sample made with another depth model is not used with this one
        assertEquals(listOf(wrong), Calibration.current(s + wrong))
    }

    /** The real models on the synthetic photos: MobileSAM-512 cuts the object from its box, Depth Anything V2 gives the height. */
    @Test fun withTheRealModels() {
        val sam = Segmenter(File("src/main/assets/sam/encoder512.onnx").readBytes(), File("src/main/assets/sam/decoder512.onnx").readBytes())
        val depth = DepthModel(File("src/main/assets/${DepthModel.ASSET}").readBytes())
        assertEquals(280, depth.inW); assertEquals(378, depth.inH)
        sam.use { depth.use {
            for (name in sets) {
                val s = load(name)
                for (sh in s.shots) {
                    val img = sh.argb
                    val t0 = System.nanoTime(); val d = depth.run(img.px, img.w, img.h); val ms = (System.nanoTime() - t0) / 1_000_000
                    assertEquals(280, d.w); assertEquals(378, d.h)
                    assertTrue(d.z.all { it.isFinite() && it > 0f })
                    val b = sh.box
                    val pad = 6f
                    val m = sam.box(sam.embed(img.px, img.w, img.h), b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad).largestPart()
                    val iou = m.iou(sh.mask)
                    val f = PhotoMeasure.floor(d, m, s.k, sh.up)
                    val geo = PhotoMeasure.metrology(m, s.k, sh.up, sh.camH)
                    println(String.format(Locale.US, "%-26s depth %d ms; SAM vs true mask IoU %.3f; camera %.2f m, model says %.2f m (x%.2f); " +
                        "with the true height and SAM's mask: %.1f x %.1f x %.1f cm (truth %s)", sh.name, ms, iou, sh.camH, f.heightM, sh.camH / f.heightM,
                        geo.lengthM * 100, geo.widthM * 100, geo.heightM * 100, s.truth.joinToString(" x ") { "%.1f".format(Locale.US, it) }))
                    assertTrue("${sh.name} SAM cut", iou > 0.85)
                    if (s.kind == "box") {
                        val got = listOf(geo.lengthM * 100.0, geo.widthM * 100.0, geo.heightM * 100.0)
                        for (i in 0..2) assertTrue("${sh.name} side $i: ${got[i]} vs ${s.truth[i]}", abs(got[i] - s.truth[i]) <= 2.5)
                    }
                }
            }
        } }
    }
}
