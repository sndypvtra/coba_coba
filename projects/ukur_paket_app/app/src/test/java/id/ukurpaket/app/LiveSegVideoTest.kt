package id.ukurpaket.app

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.Segmenter
import id.ukurpaket.app.vio.Gray
import id.ukurpaket.app.vio.LiveSegmenter
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.util.Locale

/**
 * The live segmentation on a real hand-held video (frames upright, as JPEG), when one is given: not committed, as such
 * videos show people.
 *     ./gradlew :app:testDebugUnitTest --tests '*LiveSegVideoTest*' -Pukur.video=<frames dir> -Pukur.videoRef=<ref dir> -Pukur.videoOut=<out dir>
 * <ref dir>: reference masks (NNNNN.png, white = object) for some frames; <out dir> gets every frame's mask (PNG).
 * The box is the one drawn on the first frame, in its pixels (-Pukur.videoBox=x0,y0,x1,y1).
 */
class LiveSegVideoTest {
    @Test fun followsTheObjectInAVideo() {
        val dir = System.getProperty("ukur.video")?.let(::File)
        assumeTrue("no video given", dir != null && dir.isDirectory)
        val refDir = System.getProperty("ukur.videoRef")?.let(::File)
        val out = System.getProperty("ukur.videoOut")?.let(::File)?.also { it.mkdirs() }
        val box = (System.getProperty("ukur.videoBox") ?: "185,255,360,685").split(',').map { it.toFloat() }
        val files = dir!!.listFiles { f -> f.name.endsWith(".jpg") }!!.sortedBy { it.name }
        val sam = Segmenter(File("src/main/assets/sam/encoder512.onnx").readBytes(), File("src/main/assets/sam/decoder512.onnx").readBytes())
        val refines = (System.getProperty("ukur.videoRefine") ?: "RECURSIVE").split(',').map { LiveSegmenter.Refine.valueOf(it) }
        for (rf in refines) for (every in listOf(12, 30)) {
            val first = TestImages.read(files[0].inputStream())
            val w = first.w; val h = first.h
            val seg = LiveSegmenter({ sam }, w, h, onUpdate = {}, threads = false, syncEvery = every, refine = rf)
            if (System.getProperty("ukur.videoTrace") != null) seg.trace = { println("  $it") }
            seg.begin(floatArrayOf(box[0] / w, box[1] / h, box[2] / w, box[3] / h), null)
            val ious = ArrayList<String>(); val vals = ArrayList<Double>(); var ms = 0L
            for ((k, f) in files.withIndex()) {
                val img = TestImages.read(f.inputStream())
                val luma = ByteArray(img.w * img.h) { i -> val c = img.px[i]; (((c shr 16 and 255) * 299 + (c shr 8 and 255) * 587 + (c and 255) * 114) / 1000).toByte() }
                val t0 = System.nanoTime()
                seg.step(k, Gray.fromLuma(luma, img.w, img.h, rotation = 0), { img.px })
                ms += (System.nanoTime() - t0) / 1_000_000
                val m = seg.maskNow
                val ref = refDir?.let { File(it, "%05d.png".format(k)) }?.takeIf { it.exists() }?.let { r ->
                    val t = TestImages.read(r.inputStream()); Mask(t.w, t.h, BooleanArray(t.w * t.h) { (t.px[it] and 255) > 127 })
                }
                if (ref != null) {
                    var i = 0; var u = 0
                    for (y in 0 until m.h) for (x in 0 until m.w) { val a = ref[x * 4 + 2, y * 4 + 2]; val b = m.bits[y * m.w + x]; if (a && b) i++; if (a || b) u++ }
                    val v = i.toDouble() / maxOf(1, u); vals.add(v); ious.add("$k:" + "%.2f".format(Locale.US, v))
                }
                if (out != null && every == 12 && rf == refines.first()) {
                    val sb = StringBuilder("P1\n${m.w} ${m.h}\n")
                    for (y in 0 until m.h) { for (x in 0 until m.w) sb.append(if (m.bits[y * m.w + x]) "1 " else "0 "); sb.append('\n') }
                    File(out, "%05d.pbm".format(k)).writeText(sb.toString())
                }
            }
            println(String.format(Locale.US, "video, %s, SAM every %d frames: IoU vs MobileSAM-1024 median %.3f, min %.3f, anchors %d, %d ms per frame with SAM on PC [%s]",
                rf, every, vals.sorted()[vals.size / 2], vals.min(), seg.anchors, ms / files.size, ious.joinToString(" ")))
            seg.close()
        }
        sam.close()
    }

    /** As on the phone: the recording's tracker (RecordingTracker, every frame) drives the live segmentation. */
    @Test fun phonePathOnAVideo() {
        val dir = System.getProperty("ukur.video")?.let(::File)
        assumeTrue("no video given", dir != null && dir.isDirectory)
        val refDir = System.getProperty("ukur.videoRef")?.let(::File)
        val box = (System.getProperty("ukur.videoBox") ?: "185,255,360,685").split(',').map { it.toFloat() }
        val files = dir!!.listFiles { f -> f.name.endsWith(".jpg") }!!.sortedBy { it.name }
        val sam = Segmenter(File("src/main/assets/sam/encoder512.onnx").readBytes(), File("src/main/assets/sam/decoder512.onnx").readBytes())
        val first = TestImages.read(files[0].inputStream()); val w = first.w; val h = first.h
        val rt = id.ukurpaket.app.vio.RecordingTracker()
        val masks = java.util.concurrent.ConcurrentHashMap<Int, Mask>()
        lateinit var seg: LiveSegmenter
        seg = LiveSegmenter({ sam }, w, h, onUpdate = { u -> masks[u.frame] = seg.maskNow }, threads = false, syncEvery = 12, shared = rt.tracker)
        seg.begin(floatArrayOf(box[0] / w, box[1] / h, box[2] / w, box[3] / h), null)
        rt.seg = seg
        for ((k, f) in files.withIndex()) {
            val img = TestImages.read(f.inputStream())
            // NV21 of the upright frame: luma, then interleaved V/U at half resolution
            val nv = ByteArray(img.w * img.h * 3 / 2)
            for (i in 0 until img.w * img.h) { val c = img.px[i]; nv[i] = (16 + (((c shr 16 and 255) * 66 + (c shr 8 and 255) * 129 + (c and 255) * 25 + 128) shr 8)).toByte() }
            for (y in 0 until img.h / 2) for (x in 0 until img.w / 2) {
                val c = img.px[(2 * y) * img.w + 2 * x]; val r = c shr 16 and 255; val g = c shr 8 and 255; val b = c and 255
                val o = img.w * img.h + y * img.w + 2 * x
                nv[o] = (128 + ((112 * r - 94 * g - 18 * b + 128) shr 8)).toByte(); nv[o + 1] = (128 + ((-38 * r - 74 * g + 112 * b + 128) shr 8)).toByte()
            }
            rt.offer(k, nv, img.w, img.h, 0)
            while (rt.backlog > 0) Thread.sleep(2)          // as if the phone kept up: colour for every frame
        }
        val prep = rt.finish()!!
        val vals = ArrayList<Double>(); val txt = ArrayList<String>()
        for (k in files.indices) {
            val ref = refDir?.let { File(it, "%05d.png".format(k)) }?.takeIf { it.exists() } ?: continue
            if (k > 54) continue                                // the reference is wrong after this (it loses the lighter)
            val t = TestImages.read(ref.inputStream()); val rm = Mask(t.w, t.h, BooleanArray(t.w * t.h) { (t.px[it] and 255) > 127 })
            val m = masks[k] ?: continue
            var i = 0; var u = 0
            for (y in 0 until m.h) for (x in 0 until m.w) { val a = rm[x * 4 + 2, y * 4 + 2]; val b = m.bits[y * m.w + x]; if (a && b) i++; if (a || b) u++ }
            vals.add(i.toDouble() / maxOf(1, u)); txt.add("$k:" + "%.2f".format(Locale.US, vals.last()))
        }
        println(String.format(Locale.US, "phone path on the video: IoU vs MobileSAM-1024 (frames 0-54) median %.3f, min %.3f, anchors %d, tracks %d [%s]",
            vals.sorted()[vals.size / 2], vals.min(), seg.anchors, prep.tracks.size, txt.joinToString(" ")))
        System.getProperty("ukur.videoOut")?.let(::File)?.let { out ->
            out.mkdirs()
            for ((k, m) in masks) {
                val sb = StringBuilder("P1\n${m.w} ${m.h}\n")
                for (y in 0 until m.h) { for (x in 0 until m.w) sb.append(if (m.bits[y * m.w + x]) "1 " else "0 "); sb.append('\n') }
                File(out, "%05d.pbm".format(k)).writeText(sb.toString())
            }
        }
        seg.close(); sam.close()
    }
}
