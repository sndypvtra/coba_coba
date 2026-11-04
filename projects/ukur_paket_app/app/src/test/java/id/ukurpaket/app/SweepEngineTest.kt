package id.ukurpaket.app

import id.ukurpaket.app.vio.Bits
import id.ukurpaket.app.vio.Engine
import id.ukurpaket.app.vio.Gray
import id.ukurpaket.app.vio.RecordingIO
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import kotlin.math.abs

/**
 * The on-device engine (pure Kotlin, the code the phone runs) on synthetic sweeps in the recorder's own format, made
 * by tools/dt20/synth_sweep.py --dt50 --pick-first: what a Urovo DT50 delivers (gyroscope silent, game rotation vector
 * only, camera clock not the sensors'), the object picked on the first frame. Truth from the simulation.
 */
class SweepEngineTest {
    private fun gray(f: File): Gray {
        val img = TestImages.read(f.inputStream())
        val luma = ByteArray(img.w * img.h) { i -> val c = img.px[i]; (((c shr 16 and 255) * 299 + (c shr 8 and 255) * 587 + (c and 255) * 114) / 1000).toByte() }
        return Gray.fromLuma(luma, img.w, img.h, down = if (img.w > 1000) 2 else 1, rotation = 90)
    }

    private fun mask(f: File): Bits? {
        if (!f.exists()) return null
        val img = TestImages.read(f.inputStream())
        return Bits(img.w, img.h, BooleanArray(img.w * img.h) { (img.px[it] and 255) > 127 })
    }

    private fun run(name: String): Pair<DoubleArray, DoubleArray> {
        val dir = File(javaClass.getResource("/sweep/$name/session.json")!!.toURI()).parentFile
        val l = RecordingIO.load(dir, ::gray, ::mask)
        Engine.trace = { println("  [$name] $it") }
        val r = Engine.run(l.input) { stage, p -> if (p == 0f) println(stage) }
        val truth = Json.parseToJsonElement(File(dir, "truth.json").readText()).jsonObject["size_cm"]!!.jsonArray.map { it.jsonPrimitive.double }
        println("$name: ${"%.1f x %.1f x %.1f".format(r.lengthCm, r.widthCm, r.heightCm)} cm (truth ${truth.joinToString(" x ") { "%.1f".format(it) }}), " +
            "${r.method}, conf ${r.confidence}, dense ${r.densePoints}, points ${r.points}, td ${r.timeOffsetMs} ms, f ${"%.1f".format(r.focalPx)}, " +
            "reproj ${"%.2f".format(r.reprojPx)} px, scale sd ${"%.2f".format(r.scaleSdPct)} %, ${"%.1f".format(r.seconds)} s, notes ${r.notes}")
        assertEquals(l.input.tCam.size, r.outlines.size)
        assertTrue("an outline on the picked frame", r.outlines[l.input.pickFrame].size >= 6)
        return doubleArrayOf(r.lengthCm, r.widthCm, r.heightCm) to truth.toDoubleArray()
    }

    @Test fun boxOnTheDt50() {
        val (got, truth) = run("box_dt50")
        for (i in 0 until 3) assertTrue("dimension $i: ${got[i]} vs ${truth[i]}", abs(got[i] - truth[i]) <= 3.0)
    }

    @Test fun irregularSackOnTheDt50() {
        val (got, truth) = run("sack_dt50")
        for (i in 0 until 3) assertTrue("dimension $i: ${got[i]} vs ${truth[i]}", abs(got[i] - truth[i]) <= 6.0)
    }
}
