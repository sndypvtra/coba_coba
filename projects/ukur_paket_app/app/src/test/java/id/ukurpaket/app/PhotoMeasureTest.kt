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
import id.ukurpaket.app.photo.Standing
import id.ukurpaket.app.photo.ShotRecord
import id.ukurpaket.app.photo.FocusInfo
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
                        assertTrue("${sh.name} box-like", m.boxLike)
                    }
                    "phone", "mailer" -> {
                        // lying flat: length and width as a box's; the thickness is read roughly (a few cm at most)
                        val tol = if (s.kind == "phone") 1.5 else 2.5
                        for (i in 0..1) assertEquals("${sh.name} side $i", s.truth[i], got[i], tol)
                        assertTrue("${sh.name} thickness ${got[2]}", got[2] <= s.truth[2] + 2.5)
                        assertTrue("${sh.name} read as flat", m.flat)
                    }
                    "cylinder" -> {
                        // a standing cylinder fits better than any box: its outer box, diameter x diameter x height
                        for (i in 0..2) assertEquals("${sh.name} side $i", s.truth[i], got[i], 1.0)
                        assertFalse("${sh.name} not box-like", m.boxLike)
                        assertTrue("${sh.name} round", m.round)
                    }
                    else -> {
                        // a sack: rough outer box (one view cannot see how far it bulges behind), flagged, never "Akurat"
                        for (i in 0..2) assertEquals("${sh.name} side $i", s.truth[i], got[i], (if (i == 2) 0.25 else 0.22) * s.truth[i])
                        assertFalse("${sh.name} not box-like", m.boxLike)
                        assertFalse("${sh.name} not round", m.round)
                    }
                }
            }
        }
    }

    /**
     * The phone held tilted sideways (up to landscape): the picture is turned level before the geometry, so the carton
     * reads the same. The rolled view is made from the upright one (mask turned about the lens centre, 'up' with it).
     */
    @Test fun aPhoneHeldTiltedSidewaysReadsTheSame() {
        val s = load("box_3"); val sh = s.shots[0]
        for (deg in listOf(12f, 35f, 79f, -60f)) {
            val a = Math.toRadians(-deg.toDouble())
            // a fake 'up' with roll -deg: level() then turns the picture by +deg, which is the phone rolled by deg
            val fake = V3((sh.up.x * Math.cos(a) - sh.up.y * Math.sin(a)).toFloat(), (sh.up.x * Math.sin(a) + sh.up.y * Math.cos(a)).toFloat(), sh.up.z)
            val lv = PhotoMeasure.level(sh.mask, s.k, fake)!!
            val r = kotlin.math.atan2(fake.x, -fake.y); val c = kotlin.math.cos(r); val sn = kotlin.math.sin(r)
            val up = V3(c * sh.up.x + sn * sh.up.y, -sn * sh.up.x + c * sh.up.y, sh.up.z)
            assertEquals(deg.toDouble(), Math.toDegrees(kotlin.math.atan2(up.x, -up.y).toDouble()), 0.5)
            val m = PhotoMeasure.metrology(lv.mask, lv.k, up, sh.camH)
            val got = listOf(m.lengthM * 100.0, m.widthM * 100.0, m.heightM * 100.0)
            println(String.format(Locale.US, "rolled %.0f deg: %.1f x %.1f x %.1f cm, IoU %.3f", deg, got[0], got[1], got[2], m.iou))
            for (i in 0..2) assertEquals("roll $deg side $i", s.truth[i], got[i], 1.2)
            assertTrue(m.boxLike)
        }
    }

    /**
     * What the first real carton photo had: a strip of tape sticking out of the top and the shadow under the box cut in
     * with it along the floor. The box fitted to the whole silhouette gives way to them only by the area they add.
     */
    @Test fun tapeStickingOutAndAShadowBarelyMoveTheFit() {
        val s = load("box_7"); val sh = s.shots[0]
        val bits = sh.mask.bits.copyOf(); val w = sh.mask.w
        val b = sh.mask.bounds()!!
        val top = (0 until sh.mask.h).first { y -> (0 until w).any { bits[y * w + it] } }
        val cx = (0 until w).filter { bits[top * w + it] }.average().toInt()
        for (y in top - 10 until top) for (x in cx - 12..cx + 12) bits[y * w + x] = true          // tape: 25 x 10 px
        for (x in b[0] until b[0] + (b[2] - b[0]) * 2 / 5) {                                       // shadow: 6 px under the left part
            val low = (sh.mask.h - 1 downTo 0).firstOrNull { bits[it * w + x] } ?: continue
            for (y in low + 1..low + 6) bits[y * w + x] = true
        }
        val tr = ArrayList<String>()
        val m = PhotoMeasure.metrology(Mask(w, sh.mask.h, bits), s.k, sh.up, sh.camH, trace = { tr += it })
        val got = listOf(m.lengthM * 100.0, m.widthM * 100.0, m.heightM * 100.0)
        println(String.format(Locale.US, "tape + shadow: %.1f x %.1f x %.1f cm, IoU %.3f", got[0], got[1], got[2], m.iou))
        tr.filter { it.startsWith("fit") }.forEach { println("      $it") }
        for (i in 0..2) assertEquals("side $i", s.truth[i], got[i], 2.0)
        assertTrue(m.boxLike)
    }

    /**
     * The first real DT50 photos (masks and records only, no picture is kept), at the camera height
     * Depth Anything gave. No tape size was typed for them, so this checks what can be checked without it: the carton
     * and the parcel fit a box closely (0.4.2 read the carton at IoU 0,86 with a box twice too long), the book shot in
     * landscape is levelled and reads as a book (about 1,4 : 1), the bottle is not taken for a box.
     */
    @Test fun firstRealPhotos() {
        fun run(name: String, hM: Float): PhotoMeasure.Metrology {
            val dir = File(javaClass.getResource("/photo_real/$name")!!.toURI())
            val rec = dir.listFiles()!!.first { it.name.startsWith("shot_") }
            val j = Json.parseToJsonElement(rec.readText()).jsonObject
            val lm = j["lensModel"]!!.jsonObject
            val k = Intrinsics(lm["fx"]!!.jsonPrimitive.float, lm["fy"]!!.jsonPrimitive.float, lm["cx"]!!.jsonPrimitive.float, lm["cy"]!!.jsonPrimitive.float,
                lm["w"]!!.jsonPrimitive.int, lm["h"]!!.jsonPrimitive.int)
            val a = j["accel"]!!.jsonArray.map { it.jsonPrimitive.float }
            val img = TestImages.read(File(dir, rec.name.replace("shot_", "mask_").replace(".json", ".png")).inputStream())
            val mask = Mask(img.w, img.h, BooleanArray(img.w * img.h) { (img.px[it] and 255) > 127 })
            val m = PhotoMeasure.metrology(mask, k, Intrinsics.upFromAccel(a[0], a[1], a[2]), hM)
            println(String.format(Locale.US, "%s: %.1f x %.1f x %.1f cm, IoU %.3f, box %b, round %b, %d corners", name,
                m.lengthM * 100, m.widthM * 100, m.heightM * 100, m.iou, m.boxLike, m.round, m.outlineCorners))
            return m
        }
        val carton = run("20261109_154822", 1.094f)
        assertTrue(carton.boxLike); assertTrue(carton.iou > 0.93f)
        assertEquals(0.63, (carton.widthM / carton.lengthM).toDouble(), 0.06)              // the hand-measured corners: 0,67
        val parcel = run("20261109_162517", 1.471f)
        assertTrue(parcel.boxLike); assertTrue(parcel.iou > 0.93f); assertFalse(parcel.flat)
        val book = run("20261109_154658", 0.376f)                                          // landscape: rolled 79 deg
        assertTrue(book.iou > 0.93f)
        assertEquals(1.4, (book.lengthM / book.widthM).toDouble(), 0.12)
        val bottle = run("20261109_162622", 1.121f)
        assertFalse(bottle.boxLike)
    }

    @Test fun theStandingCameraHeightSteadiesTheAi() {
        // three calibration photos taken standing: the courier's camera height is learnt from them
        val cal = listOf(CalSample(listOf(44.0, 33.0, 22.0), listOf(40.0, 30.0, 20.0), aiCameraM = 1.45),
            CalSample(listOf(50.0, 40.0, 25.0), listOf(46.0, 36.0, 23.0), aiCameraM = 1.40), CalSample(listOf(30.0, 20.0, 10.0), listOf(30.0, 20.0, 10.0)))
        val st = Calibration.standing(cal)!!
        assertEquals(2, st.samples)                                                       // the third has no height
        assertEquals((1.45 / 1.1 + 1.40 * 0.92) / 2, st.heightM, 0.01)
        // the AI 8 % high: pulled most of the way to the standing height; the AI far off (crouching, a table): left alone
        val p1 = PhotoMeasure.cameraHeight(1.40f, Standing(1.30, 0.04, 3))
        assertTrue(p1.standing); assertTrue(p1.heightM in 1.30f..1.33f)
        val p2 = PhotoMeasure.cameraHeight(0.70f, Standing(1.30, 0.04, 3))
        assertFalse(p2.standing); assertEquals(0.70f, p2.heightM, 1e-6f)
        assertEquals(1.10f, PhotoMeasure.cameraHeight(1.10f, null).heightM, 1e-6f)
        // close up, the autofocus (3 %) outweighs the depth model (50 %); far off from it, the model is dropped
        val p3 = PhotoMeasure.cameraHeight(0.54f, null, 0.07f, 0.03)
        assertTrue(p3.focus); assertFalse(p3.ai); assertEquals(0.07f, p3.heightM, 1e-4f)
        val p4 = PhotoMeasure.cameraHeight(1.30f, null, 1.20f, 0.20)                    // far: both kept, the model weighs more
        assertTrue(p4.ai && p4.focus); assertTrue(p4.heightM in 1.25f..1.30f)
    }

    /**
     * A cigarette pack shot close up on the DT50 (0.4.3, tape 8 x 4 x 1,5 cm, photos rolled 52 and 80 deg): the depth model
     * put the camera 0,64 and 0,74 m above the table, 9x and 14x too high and not by the same factor (the two photos read
     * 52 and 77 cm long). The autofocus said 3,97 and 5,84 "diopters" (uncalibrated: no physical unit), and against the
     * tape both are 3,1x too few, within 2 % of each other: one factor learnt from one photo puts the other within 3 %.
     */
    @Test fun theAutofocusGivesTheDistanceCloseUp() {
        class Shot(val mask: Mask, val k: Intrinsics, val up: V3, val focus: FocusInfo, val depth: DepthMap, val tape: List<Double>)
        val dir = File(javaClass.getResource("/photo_real/20261110_113804")!!.toURI())
        val json = Json { ignoreUnknownKeys = true }
        val shots = (0..1).map { i ->
            val rec = json.decodeFromString(ShotRecord.serializer(), File(dir, "shot_$i.json").readText())
            val img = TestImages.read(File(dir, "mask_$i.png").inputStream())
            val bs = File(dir, "depth_$i.u16").readBytes(); val ds = rec.depthSize!!
            Shot(Mask(img.w, img.h, BooleanArray(img.w * img.h) { (img.px[it] and 255) > 127 }), rec.lensModel,
                Intrinsics.upFromAccel(rec.accel[0], rec.accel[1], rec.accel[2]), rec.focus!!,
                DepthMap(ds[0], ds[1], FloatArray(ds[0] * ds[1]) { q -> ((bs[2 * q].toInt() and 255) or ((bs[2 * q + 1].toInt() and 255) shl 8)) / 1000f }), rec.tapeCm!!)
        }
        // the factor each photo gives (the real camera height from the tape, the focus point's depth from the box)
        val f = shots.map { s ->
            val m = PhotoMeasure.metrology(s.mask, s.k, s.up, 1f)
            val zUnit = PhotoMeasure.focusDepth(m.corners, s.up, 1f, s.k)!!
            val q = listOf(s.tape[0] / (m.lengthM * 100), s.tape[1] / (m.widthM * 100), s.tape[2] / (m.heightM * 100)).sorted()[1]
            1 / (zUnit * q) / s.focus.diopters
        }
        println(String.format(Locale.US, "real / reported diopters: %.3f, %.3f", f[0], f[1]))
        assertEquals(f[0], f[1], 0.03 * f[0])
        assertEquals(Calibration.DT50_FOCUS, f.average(), 0.1)
        // the lens is recognised as the DT50's; the whole measurement then takes its distance from the focus
        val cal = Calibration.builtIn(shots[0].focus)!!
        assertEquals(Calibration.DT50_FOCUS, cal.factor, 1e-9)
        val rs = shots.map { s -> PhotoMeasure.measure(s.mask, s.k, s.up, s.depth, DepthModel.DEFAULT_SCALE, false, null, s.focus, cal) }
        rs.forEachIndexed { i, r -> println(String.format(Locale.US, "photo %d: %.1f x %.1f x %.1f cm (0.4.3 read it %s), camera %.3f m, AI %.3f m, notes %s", i,
            r.lengthCm, r.widthCm, r.heightCm, listOf("51.7 x 31.1 x 13.9", "76.6 x 45.3 x 19.6")[i], r.cameraHeightM, r.aiCameraM, r.notes)) }
        for (r in rs) {
            assertTrue(r.focusCameraM > 0); assertEquals(r.focusCameraM, r.cameraHeightM, 1e-6)
            assertEquals(8.0, r.lengthCm, 2.0); assertEquals(4.0, r.widthCm, 1.0); assertEquals(1.5, r.heightCm, 0.6)
        }
        // the two photos now agree: within 3 % (0.4.3: 48 % apart)
        assertEquals(rs[0].lengthCm, rs[1].lengthCm, 0.03 * rs[0].lengthCm)
        // calibration learns it from its own photos: the factor of each shot
        assertEquals(f[0], Calibration.focusFactor(PhotoMeasure.measure(shots[0].mask, shots[0].k, shots[0].up, shots[0].depth, 1f, false, null, shots[0].focus, null), shots[0].tape)!!, 0.03 * f[0])
    }

    /**
     * Whether the object is in focus, from the photo: the synthetic carton as rendered (edges about a pixel wide) reads
     * sharp, the same photo blurred like the iPhone's (Gaussian, sigma 2 px) does not; the real photos measured 1,1-2,1
     * in focus and 0,24-0,41 blurred (RealPhotoBenchTest has them).
     */
    @Test fun anObjectOutOfFocusIsToldFromThePhoto() {
        val s = load("box_3"); val sh = s.shots[0]
        val w = sh.argb.w; val h = sh.argb.h
        val luma = ByteArray(w * h) { q -> val c = sh.argb.px[q]; (((c shr 16) and 255) * 0.299 + ((c shr 8) and 255) * 0.587 + (c and 255) * 0.114).toInt().toByte() }
        fun blurred(src: ByteArray, sigma: Double): ByteArray {
            val r = (3 * sigma).toInt(); val k = DoubleArray(2 * r + 1) { Math.exp(-((it - r) * (it - r)) / (2 * sigma * sigma)) }.let { kk -> val t = kk.sum(); DoubleArray(kk.size) { kk[it] / t } }
            val a = DoubleArray(w * h); val out = ByteArray(w * h)
            for (y in 0 until h) for (x in 0 until w) { var v = 0.0; for (i in -r..r) v += k[i + r] * (src[y * w + (x + i).coerceIn(0, w - 1)].toInt() and 255); a[y * w + x] = v }
            for (y in 0 until h) for (x in 0 until w) { var v = 0.0; for (i in -r..r) v += k[i + r] * a[(y + i).coerceIn(0, h - 1) * w + x]; out[y * w + x] = v.toInt().toByte() }
            return out
        }
        val sharp = id.ukurpaket.app.photo.Sharpness.atOutline(luma, w, h, sh.mask)!!
        val soft = id.ukurpaket.app.photo.Sharpness.atOutline(blurred(luma, 2.0), w, h, sh.mask)!!
        println(String.format(Locale.US, "sharpness: as rendered %.2f, blurred %.2f", sharp, soft))
        assertTrue(sharp > id.ukurpaket.app.photo.Sharpness.MIN); assertTrue(soft < id.ukurpaket.app.photo.Sharpness.MIN)
        // the measurement: a blurred photo does not take its distance from the focus, and says so first
        val k = s.k; val up = sh.up
        val depth = DepthMap(k.w, k.h, FloatArray(k.w * k.h) { i -> val den = -(k.ray(i % k.w + 0.5f, i / k.w + 0.5f) dot up); if (den > 1e-3f) sh.camH / den else 40f })
        val focus = FocusInfo(1 / (3.0f * 0.9f), "calibrated", 20f, 0.2f, 4)
        val r = PhotoMeasure.measure(sh.mask, k, up, depth, 1f, true, null, focus, Calibration.builtIn(focus), soft)
        assertEquals(0.0, r.focusCameraM, 0.0); assertTrue(r.notes.first().startsWith("Foto buram")); assertFalse(r.ok)
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
