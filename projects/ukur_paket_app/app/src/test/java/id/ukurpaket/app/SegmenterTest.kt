package id.ukurpaket.app

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.measure.Segmenter
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.Locale

/**
 * The app's own MobileSAM code (the one the phone runs) on the conveyor frame with seven parcels, one tap
 * and one drawn box per parcel, compared with the masks the Python reference makes from the same ONNX files
 * (tools/check_sam_onnx.py). Desktop ONNX Runtime here, Android ONNX Runtime on the phone: same model, same code.
 */
class SegmenterTest {
    private val scene = Json.parseToJsonElement(javaClass.getResource("/conveyor/scene.json")!!.readText()).jsonObject

    private fun ref(name: String): Mask {
        val img = TestImages.read(javaClass.getResourceAsStream("/conveyor/$name.png")!!)
        return Mask(img.w, img.h, BooleanArray(img.w * img.h) { (img.px[it] and 0xFF) > 127 })
    }

    @Test fun tapAndBoxMatchTheReference() {
        val img = TestImages.read(javaClass.getResourceAsStream("/conveyor/frame.jpg")!!)
        Segmenter(File("src/main/assets/sam/encoder.onnx").readBytes(), File("src/main/assets/sam/decoder.onnx").readBytes()).use { sam ->
            val t0 = System.nanoTime()
            val e = sam.embed(img.px, img.w, img.h)
            val encMs = (System.nanoTime() - t0) / 1e6
            val rows = StringBuilder(String.format(Locale.US, "encoder %.0f ms (PC CPU)\n", encMs))
            for (t in scene["taps"]!!.jsonArray) {
                val o = t.jsonObject
                val tid = o["tid"]!!.jsonPrimitive.int
                val tap = o["tap_px"]!!.jsonArray.map { it.jsonPrimitive.float }
                val box = o["box_px"]!!.jsonArray.map { it.jsonPrimitive.float }
                val t1 = System.nanoTime()
                val mt = sam.tap(e, tap[0], tap[1])
                val decMs = (System.nanoTime() - t1) / 1e6
                val mb = sam.box(e, box[0], box[1], box[2], box[3])
                val it = mt.iou(ref("sam_tap_$tid")); val ib = mb.iou(ref("sam_box_$tid"))
                rows.append(String.format(Locale.US, "#%-3d tap IoU vs reference %.3f  box %.3f  tap vs box %.3f  decoder %.0f ms  outline %d pts\n",
                    tid, it, ib, mt.iou(mb), decMs, mb.outline().size))
                assertTrue("#$tid tap $it", it > 0.97f)
                assertTrue("#$tid box $ib", ib > 0.97f)
                assertTrue("#$tid outline", mb.outline().size in 4..200)
            }
            println(rows)
            File("build/conveyor").mkdirs()
            File("build/conveyor/segmenter.txt").writeText(rows.toString())
        }
    }
}
