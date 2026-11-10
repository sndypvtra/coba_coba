package id.ukurpaket.app

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.DepthModel
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoMeasure
import id.ukurpaket.app.photo.PhotoResult
import id.ukurpaket.app.photo.Sharpness
import id.ukurpaket.app.photo.ShotRecord
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.double
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.Locale
import kotlin.math.abs

/**
 * The real DT50 photos with a known size (`src/test/resources/photo_real/<session>/truth.json`: masks, records and the
 * phone's depth maps; never the photos), measured exactly as the phone does, with the parameters every photo shares.
 * This is the yardstick for every change to the photo mode: a change that helps one photo and hurts another shows here,
 * and nothing is tuned for one parcel. Each shared ZIP with a tape size adds a session.
 */
class RealPhotoBenchTest {
    private class Case(val name: String, val rec: ShotRecord, val mask: Mask, val depth: DepthMap, val truth: List<Double>, val sharpness: Float?)

    private fun cases(): List<Case> {
        val root = File(javaClass.getResource("/photo_real")!!.toURI())
        val json = Json { ignoreUnknownKeys = true }
        return root.listFiles()!!.filter { File(it, "truth.json").exists() }.sortedBy { it.name }.flatMap { dir ->
            val t = Json.parseToJsonElement(File(dir, "truth.json").readText()).jsonObject
            val truth = t["size_cm"]!!.jsonArray.map { it.jsonPrimitive.double }
            val sharp = t["sharpness"]?.jsonArray?.map { it.jsonPrimitive.float }
            dir.listFiles()!!.filter { it.name.startsWith("shot_") }.sortedBy { it.name }.mapIndexed { n, f ->
                val i = f.name.removePrefix("shot_").removeSuffix(".json")
                val rec = json.decodeFromString(ShotRecord.serializer(), f.readText())
                val img = TestImages.read(File(dir, "mask_$i.png").inputStream())
                val ds = rec.depthSize!!; val bs = File(dir, "depth_$i.u16").readBytes()
                Case("${dir.name}/$i", rec, Mask(img.w, img.h, BooleanArray(img.w * img.h) { (img.px[it] and 255) > 127 }),
                    DepthMap(ds[0], ds[1], FloatArray(ds[0] * ds[1]) { q -> ((bs[2 * q].toInt() and 255) or ((bs[2 * q + 1].toInt() and 255) shl 8)) / 1000f }),
                    truth, sharp?.getOrNull(n))
            }
        }
    }

    /** As the phone measures: Depth Anything's map, the DT50's focus factor, the outline's sharpness; not calibrated. */
    private fun measure(c: Case): PhotoResult {
        val a = c.rec.accel
        return PhotoMeasure.measure(c.mask, c.rec.lensModel, Intrinsics.upFromAccel(a[0], a[1], a[2]), c.depth, DepthModel.DEFAULT_SCALE, false,
            null, c.rec.focus, Calibration.builtIn(c.rec.focus), c.sharpness)
    }

    @Test fun everyRealPhotoWithAKnownSize() {
        val cs = cases()
        assertTrue(cs.size >= 3)
        println(String.format(Locale.US, "%-20s %-18s %-20s %-22s %-9s %s", "photo", "truth (cm)", "measured (cm)", "error", "sharp", "distance from"))
        val rs = cs.map { c ->
            val r = measure(c)
            val got = listOf(r.lengthCm, r.widthCm, r.heightCm)
            val err = got.indices.map { (got[it] - c.truth[it]) / c.truth[it] * 100 }
            println(String.format(Locale.US, "%-20s %-18s %-20s %-22s %-9s %s", c.name, c.truth.joinToString(" x ") { "%.1f".format(Locale.US, it) },
                got.joinToString(" x ") { "%.1f".format(Locale.US, it) }, err.joinToString(" / ") { "%+.0f%%".format(Locale.US, it) },
                c.sharpness?.let { "%.2f".format(Locale.US, it) } ?: "-",
                if (r.focusCameraM > 0) "focus (%.2f m)".format(Locale.US, r.focusDistanceM) else "AI (camera %.2f m)".format(Locale.US, r.cameraHeightM)))
            r.notes.forEach { println("      • $it") }
            // what the geometry alone gives at the true distance (scaled by the tape length): the shape's own error
            val s = c.truth[0] / r.lengthCm
            println(String.format(Locale.US, "      at the true distance: %.1f x %.1f x %.1f cm", r.lengthCm * s, r.widthCm * s, r.heightCm * s))
            c to r
        }
        for ((c, r) in rs) {
            val sharp = c.sharpness == null || c.sharpness >= Sharpness.MIN
            if (sharp && r.focusCameraM > 0) {
                // in focus, the distance from the lens: every side within 25 % (the cigarette pack's tape is in doubt)
                for ((i, v) in listOf(r.lengthCm, r.widthCm, r.heightCm).withIndex()) assertTrue("${c.name} side $i: $v vs ${c.truth[i]}", abs(v - c.truth[i]) <= 0.25 * c.truth[i])
            }
            if (!sharp) {
                // out of focus: the lens's distance is not the object's; said first, never "Akurat", score at most 30
                assertEquals("${c.name} focus not used", 0.0, r.focusCameraM, 0.0)
                assertTrue(r.notes.first().startsWith("Foto buram")); assertFalse(r.ok); assertTrue(r.confidence <= 30)
                // the shape itself holds: at the true distance its length and width are right
                val s = c.truth[0] / r.lengthCm
                assertEquals("${c.name} width at the true distance", c.truth[1], r.widthCm * s, 0.1 * c.truth[1])
            }
        }
    }
}
