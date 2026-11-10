package id.ukurpaket.app

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.DepthModel
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoMeasure
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.util.Locale
import kotlin.math.atan2

/**
 * A tool, not a check: `./gradlew :app:testDebugUnitTest --tests '*RealPhotoProbe*' -Pukur.real=<folder of photo sessions
 * from the phone's ZIP>` runs the photo engine on real phone photos (the phone's depth and Depth Anything run here), with
 * its traces; `-Pukur.h=0.9,1.2` adds camera heights to try, `-Pukur.trace=<dir>` writes each fitted box's corners. The
 * photos themselves are never committed (they show the courier's surroundings and parcel labels).
 */
class RealPhotoProbe {
    @Test fun probe() {
        val root = System.getProperty("ukur.real")
        assumeTrue(root != null)
        val dm = DepthModel(File("src/main/assets/${DepthModel.ASSET}").readBytes())
        for (rec in File(root!!).walk().filter { it.name.startsWith("shot_") && it.name.endsWith(".json") }.sorted()) {
            val dir = rec.parentFile; val i = rec.name.removePrefix("shot_").removeSuffix(".json")
            val j = Json.parseToJsonElement(rec.readText()).jsonObject
            val lm = j["lensModel"]!!.jsonObject
            val k = Intrinsics(lm["fx"]!!.jsonPrimitive.float, lm["fy"]!!.jsonPrimitive.float, lm["cx"]!!.jsonPrimitive.float, lm["cy"]!!.jsonPrimitive.float,
                lm["w"]!!.jsonPrimitive.int, lm["h"]!!.jsonPrimitive.int)
            val a = j["accel"]!!.jsonArray.map { it.jsonPrimitive.float }
            val up = Intrinsics.upFromAccel(a[0], a[1], a[2])
            val m = TestImages.read(File(dir, "mask_$i.png").inputStream())
            val mask = Mask(m.w, m.h, BooleanArray(m.w * m.h) { (m.px[it] and 255) > 127 })
            val big = TestImages.read(File(dir, "photo_$i.jpg").inputStream())
            val f = big.w / k.w
            val small = IntArray(k.w * k.h) { p ->
                val x = p % k.w; val y = p / k.w; var r = 0; var g = 0; var b = 0
                for (dy in 0 until f) for (dx in 0 until f) { val c = big.px[(y * f + dy) * big.w + x * f + dx]; r += (c shr 16) and 255; g += (c shr 8) and 255; b += c and 255 }
                val n = f * f; (0xFF shl 24) or ((r / n) shl 16) or ((g / n) shl 8) or (b / n)
            }
            val ds = j["depthSize"]!!.jsonArray.map { it.jsonPrimitive.int }
            val old = File(dir, "depth_$i.u16").readBytes().let { bs -> DepthMap(ds[0], ds[1], FloatArray(ds[0] * ds[1]) { q -> ((bs[2 * q].toInt() and 255) or ((bs[2 * q + 1].toInt() and 255) shl 8)) / 1000f }) }
            val new = dm.run(small, k.w, k.h)
            val roll = Math.toDegrees(atan2(up.x.toDouble(), -up.y.toDouble()))
            println(String.format(Locale.US, "\n=== %s  up (%.2f %.2f %.2f) roll %.0f deg, down %.0f deg, mask area %d",
                dir.name, up.x, up.y, up.z, roll, Math.toDegrees(kotlin.math.asin(-up.z.toDouble())), mask.area))
            for ((name, d) in listOf("phone (YOLO26n)" to old, "DAv2" to new)) {
                val fl = PhotoMeasure.floor(d, mask, k, up)
                println(String.format(Locale.US, "  %-16s camera %.3f m (inliers %d/%d, tilt %.1f, wide %b)", name, fl.heightM, fl.inliers, fl.tried, fl.tiltDeg, fl.wide))
            }
            // the distance the autofocus reports, against the one the tape size implies (geometry at h = 1, then scaled)
            val unit = PhotoMeasure.metrology(mask, k, up, 1f)
            val zUnit = PhotoMeasure.focusDepth(unit.corners, up, 1f, k)
            val fd = j["focus"]?.let { runCatching { it.jsonObject["diopters"]!!.jsonPrimitive.float }.getOrNull() }
            val tape = j["tapeCm"]?.let { runCatching { it.jsonArray.map { v -> v.jsonPrimitive.float } }.getOrNull() }
            println(String.format(Locale.US, "  at h = 1 m: %.1f x %.1f x %.1f cm; autofocus point %.3f m away; focus %s D (%s m)",
                unit.lengthM * 100, unit.widthM * 100, unit.heightM * 100, zUnit ?: -1f, fd?.toString() ?: "-", fd?.let { "%.3f".format(Locale.US, 1 / it) } ?: "-"))
            if (tape != null && zUnit != null) {
                val t = tape.take(2).sortedDescending() + tape[2]
                val rs = listOf(t[0] / (unit.lengthM * 100), t[1] / (unit.widthM * 100), t[2] / (unit.heightM * 100))
                val hTrue = rs.sorted()[1]
                println(String.format(Locale.US, "  tape %s: ratios %s -> camera %.3f m, focus point %.3f m (%.1f D)%s", tape, rs.map { "%.3f".format(Locale.US, it) },
                    hTrue, hTrue * zUnit, 1 / (hTrue * zUnit), fd?.let { "; true / reported diopters %.2f".format(Locale.US, (1 / (hTrue * zUnit)) / it) } ?: ""))
            }
            val hs = (System.getProperty("ukur.h") ?: "").split(',').mapNotNull { it.toFloatOrNull() }
            val fl = PhotoMeasure.floor(new, mask, k, up)
            for (h in listOf(fl.heightM / 1.21f) + hs) {
                val tr = ArrayList<String>()
                val r = runCatching { PhotoMeasure.metrology(mask, k, up, h, trace = { tr += it }) }
                r.onSuccess { g -> println(String.format(Locale.US, "  h %.3f -> %.1f x %.1f x %.1f cm, IoU %.3f, align %.2f, flat %b", h, g.lengthM * 100, g.widthM * 100, g.heightM * 100, g.iou, g.sideAlign, g.flat))
                    System.getProperty("ukur.trace")?.let { out -> File(out).apply { mkdirs() }.resolve("${dir.name}.corners").writeText(
                        g.corners.joinToString(" ") { p -> k.project(p).let { q -> "%.4f %.4f".format(Locale.US, q.a / k.w, q.b / k.h) } }) } }
                    .onFailure { println("  h $h -> failed: ${it.message}") }
                tr.forEach { println("      $it") }
            }
        }
    }
}
