package id.ukurpaket.app

import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.vio.Gray
import id.ukurpaket.app.vio.LiveSegmenter
import id.ukurpaket.app.vio.Yuv
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.Locale

/**
 * The live segmentation the recorder shows (the code the phone runs, here in step-by-step mode): MobileSAM-512 on the
 * box drawn at the start, the mask carried by the tracked points and its edges set by the object's colours, MobileSAM
 * again every 12 frames (30 for a slow phone). Scored on the
 * synthetic DT50 sweeps against the object's true mask on every frame (tools/dt20/synth_sweep.py --masks).
 */
class LiveSegTest {
    private class Frame(val argb: IntArray, val gray: Gray, val truth: BooleanArray)

    private fun frames(name: String): Pair<List<Frame>, FloatArray> {
        val dir = File(javaClass.getResource("/sweep/$name/session.json")!!.toURI()).parentFile
        val out = ArrayList<Frame>()
        for (f in File(dir, "frames").listFiles()!!.sortedBy { it.name }) {
            val img = TestImages.read(f.inputStream())                    // as the sensor sees it: upright = 90° clockwise
            val w = img.h; val h = img.w
            val up = IntArray(w * h) { i -> val ux = i % w; val uy = i / w; img.px[(img.h - 1 - ux) * img.w + uy] }
            val luma = ByteArray(img.w * img.h) { i -> val c = img.px[i]; (((c shr 16 and 255) * 299 + (c shr 8 and 255) * 587 + (c and 255) * 114) / 1000).toByte() }
            val m = TestImages.read(File(dir, "masks/${f.nameWithoutExtension}.png").inputStream())
            out.add(Frame(up, Gray.fromLuma(luma, img.w, img.h, rotation = 90), BooleanArray(m.w * m.h) { (m.px[it] and 255) > 127 }))
        }
        val pick = Json.parseToJsonElement(File(dir, "pick.json").readText()).jsonObject
        val b = pick["box"]!!.jsonArray.map { it.jsonPrimitive.float }
        val w = pick["width"]!!.jsonPrimitive.float; val h = pick["height"]!!.jsonPrimitive.float
        return out to floatArrayOf(b[0] / w, b[1] / h, b[2] / w, b[3] / h)
    }

    /** IoU of the live mask (quarter grid) with the true mask sampled at the grid's cell centres. */
    private fun iou(live: id.ukurpaket.app.measure.Mask, truth: BooleanArray, w: Int, h: Int): Double {
        var i = 0; var u = 0
        for (y in 0 until live.h) for (x in 0 until live.w) {
            val t = truth[minOf(h - 1, y * 4 + 2) * w + minOf(w - 1, x * 4 + 2)]; val l = live.bits[y * live.w + x]
            if (t && l) i++; if (t || l) u++
        }
        return if (u == 0) 0.0 else i.toDouble() / u
    }

    private fun run(name: String, sam: Segmenter?, every: Int = 12, refine: LiveSegmenter.Refine = LiveSegmenter.Refine.PER_FRAME): List<Double> {
        val (fs, box) = frames(name)
        val w = fs[0].gray.w; val h = fs[0].gray.h
        var first = -1
        val seg = LiveSegmenter({ sam }, w, h, onUpdate = {}, onFirstMask = { f, _, _ -> first = f }, threads = false, syncEvery = every, refine = refine)
        seg.begin(box, null)
        val ious = fs.mapIndexed { k, f -> seg.step(k, f.gray, { f.argb }); iou(seg.maskNow, f.truth, w, h) }
        if (sam != null) assertEquals("MobileSAM cut the object on the touched frame", 0, first)
        println(String.format(Locale.US, "%s %s, SAM every %d frames, edges %s: IoU median %.3f, min %.3f, last %.3f, anchors %d, SAM %d ms  [%s]", name,
            if (sam == null) "tracking only" else "MobileSAM-512 + tracking", every, refine, ious.sorted()[ious.size / 2], ious.min(), ious.last(),
            seg.anchors, seg.lastSamMs ?: 0, ious.filterIndexed { i, _ -> i % 6 == 0 }.joinToString(" ") { "%.2f".format(Locale.US, it) }))
        seg.close()
        return ious
    }

    @Test fun followsTheBoxOnEveryFrame() {
        Segmenter(File("src/main/assets/sam/encoder512.onnx").readBytes(), File("src/main/assets/sam/decoder512.onnx").readBytes()).use { sam ->
            assertEquals(512, sam.size)
            for (name in listOf("box_dt50", "sack_dt50")) {
                val ious = run(name, sam)
                val med = ious.sorted()[ious.size / 2]
                assertTrue("$name median IoU $med", med >= 0.85)
                assertTrue("$name worst IoU ${ious.min()}", ious.min() >= 0.6)
                // a slow phone: MobileSAM answers only every ~2 s (30 frames); the tracked points carry the mask between
                val slow = run(name, sam, every = 30)
                assertTrue("$name slow median ${slow.sorted()[slow.size / 2]}", slow.sorted()[slow.size / 2] >= 0.85)
                assertTrue("$name slow worst ${slow.min()}", slow.min() >= 0.7)
                run(name, sam, every = 30, refine = LiveSegmenter.Refine.NONE)     // for comparison: without the colour edges
            }
        }
        run("box_dt50", null)
    }

    @Test fun nv21IsTurnedUprightLikeTheTracker() {
        // a 4 x 2 sensor picture with distinct luma; upright (90° clockwise) it is 2 x 4
        val sw = 4; val sh = 2
        val nv = ByteArray(sw * sh * 3 / 2) { if (it < sw * sh) (16 + it * 20).toByte() else 128.toByte() }
        val g = Gray.fromLuma(nv, sw, sh, rotation = 90)
        val c = Yuv.argb(nv, sw, sh, 90, g.w, g.h)
        assertEquals(2, g.w); assertEquals(4, g.h)
        for (i in c.indices) {
            val y = (((c[i] shr 16) and 255) / 1.164f + 16).toInt()
            assertTrue("pixel $i: grey ${g.p[i]} vs colour $y", kotlin.math.abs(g.p[i] - y) <= 2)
        }
    }
}
