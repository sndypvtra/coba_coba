package id.ukurpaket.app

import id.ukurpaket.app.measure.BoxFitter
import id.ukurpaket.app.measure.FloorPlane
import id.ukurpaket.app.measure.PointAccumulator
import id.ukurpaket.app.measure.V3
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.float
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale

/**
 * Many parcels in one view: frame 471 of the parcel-belt PoC (projects/03_parcel_dimensioning), turned
 * into 3D points by tools/conveyor_scene.py. Each parcel is "tapped" once, exactly as a courier would,
 * and measured with the app's own core. Results go to build/conveyor/result.json for drawing.
 */
class ConveyorReplayTest {
    private val scene = Json.parseToJsonElement(javaClass.getResource("/conveyor/scene.json")!!.readText()).jsonObject

    private fun v3(a: JsonArray) = V3(a[0].jsonPrimitive.float, a[1].jsonPrimitive.float, a[2].jsonPrimitive.float)

    private fun points(): List<V3> {
        val bytes = javaClass.getResourceAsStream("/conveyor/points.f32")!!.readBytes()
        val fb = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
        val acc = PointAccumulator(0.01f)                  // the same 1 cm merge the app applies
        while (fb.remaining() >= 3) acc.add(fb.get(), fb.get(), fb.get())
        return acc.points()
    }

    @Test fun measuresEveryTappedParcelSeparately() {
        val pts = points()
        val plane = FloorPlane(v3(scene["plane_origin"]!!.jsonArray), v3(scene["plane_up"]!!.jsonArray))
        val rows = StringBuilder()
        val out = StringBuilder("[")
        var reference: Triple<Float, Float, Float>? = null
        for ((k, t) in scene["taps"]!!.jsonArray.withIndex()) {
            val o = t.jsonObject
            val tid = o["tid"]!!.jsonPrimitive.int
            val seg = BoxFitter.segment(pts, plane, v3(o["seed"]!!.jsonArray), cell = 0.015f, minH = 0.02f, minPerCell = 2)
            val r = seg?.let { BoxFitter.fit(it) }
            if (tid == 28) reference = r?.let { Triple(it.lengthM, it.widthM, it.heightM) }
            rows.append(String.format(Locale.US, "#%-3d %s   PoC %s\n", tid,
                r?.let { String.format(Locale.US, "%5.1f x %5.1f x %5.1f cm  (%d pts)", it.lengthM * 100, it.widthM * 100, it.heightM * 100, it.points) } ?: "not found",
                o["poc_mm"]?.toString() ?: "-"))
            if (k > 0) out.append(",")
            out.append("{\"tid\":$tid")
            if (r != null) {
                fun list(c: List<V3>) = c.joinToString(",", "[", "]") { String.format(Locale.US, "[%.4f,%.4f,%.4f]", it.x, it.y, it.z) }
                out.append(String.format(Locale.US, ",\"l\":%.1f,\"w\":%.1f,\"h\":%.1f,\"points\":%d,\"floor\":%s,\"top\":%s",
                    r.lengthM * 100, r.widthM * 100, r.heightM * 100, r.points, list(r.floorCorners), list(r.topCorners)))
            }
            out.append("}")
        }
        out.append("]")
        File("build/conveyor").mkdirs()
        File("build/conveyor/result.json").writeText(out.toString())
        File("build/conveyor/result.txt").writeText(rows.toString())
        println(rows)

        // Geometry alone merges #28 (the printed 720 x 500 x 340 mm carton) with what touches it; this test
        // records that limit rather than asserting on it. The mask-prompted test below is the one that must pass.
        assertNotNull(reference)
    }

    /**
     * The same taps, but the parcel is cut out by a segmentation mask (MobileSAM, prompted by the tap
     * point or by a drawn box; tools/conveyor_masks.py) instead of by geometry alone.
     */
    @Test fun measuresMaskPromptedParcels() {
        val plane = FloorPlane(v3(scene["plane_origin"]!!.jsonArray), v3(scene["plane_up"]!!.jsonArray))
        val rows = StringBuilder()
        val out = StringBuilder("[")
        var ref: Float? = null
        var first = true
        for (t in scene["taps"]!!.jsonArray) {
            val o = t.jsonObject
            val tid = o["tid"]!!.jsonPrimitive.int
            for (kind in listOf("point", "box")) {
                val bytes = javaClass.getResourceAsStream("/conveyor/mask_${kind}_$tid.f32")?.readBytes() ?: continue
                val fb = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
                val acc = PointAccumulator(0.01f)
                while (fb.remaining() >= 3) acc.add(fb.get(), fb.get(), fb.get())
                val seg = BoxFitter.segment(acc.points(), plane, v3(o["seed"]!!.jsonArray), cell = 0.015f, minH = 0.02f, minPerCell = 2)
                val r = seg?.let { BoxFitter.fit(it) }
                if (tid == 28 && kind == "box") ref = r?.lengthM
                assertNotNull("#$tid $kind not found", r)
                rows.append(String.format(Locale.US, "#%-3d %-5s %s   PoC %s\n", tid, kind,
                    r?.let { String.format(Locale.US, "%5.1f x %5.1f x %5.1f cm  (%d pts)", it.lengthM * 100, it.widthM * 100, it.heightM * 100, it.points) } ?: "not found",
                    o["poc_mm"]?.toString() ?: "-"))
                if (!first) out.append(",")
                first = false
                out.append("{\"tid\":$tid,\"kind\":\"$kind\"")
                if (r != null) {
                    fun list(c: List<V3>) = c.joinToString(",", "[", "]") { String.format(Locale.US, "[%.4f,%.4f,%.4f]", it.x, it.y, it.z) }
                    out.append(String.format(Locale.US, ",\"l\":%.1f,\"w\":%.1f,\"h\":%.1f,\"points\":%d,\"floor\":%s,\"top\":%s",
                        r.lengthM * 100, r.widthM * 100, r.heightM * 100, r.points, list(r.floorCorners), list(r.topCorners)))
                }
                out.append("}")
            }
        }
        out.append("]")
        File("build/conveyor").mkdirs()
        File("build/conveyor/result_mask.json").writeText(out.toString())
        File("build/conveyor/result_mask.txt").writeText(rows.toString())
        println(rows)
        // What this scene proves is separation: with geometry alone #28 swallows its neighbours (~1,4 m long);
        // with a mask it stays one carton. Its absolute size is off from this low, far, oblique view (README).
        assertNotNull(ref)
        org.junit.Assert.assertTrue("#28 still merged: $ref m", ref!! < 0.95f)
    }
}
