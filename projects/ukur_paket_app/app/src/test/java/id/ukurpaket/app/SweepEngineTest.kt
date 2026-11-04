package id.ukurpaket.app

import id.ukurpaket.app.vio.Bits
import id.ukurpaket.app.vio.Engine
import id.ukurpaket.app.vio.Gray
import id.ukurpaket.app.vio.RecordingIO
import id.ukurpaket.app.vio.RecordingTracker
import id.ukurpaket.app.vio.SweepInput
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

    private fun run(name: String, noRotation: Boolean = false): Pair<DoubleArray, DoubleArray> {
        val dir = File(javaClass.getResource("/sweep/$name/session.json")!!.toURI()).parentFile
        val l0 = RecordingIO.load(dir, ::gray, ::mask)
        // as the DT50 that sends neither gyroscope nor rotation vector: the accelerometer only
        val inp = if (!noRotation) l0.input else l0.input.let { i -> SweepInput(i.tCam, i.arrival, i.realtimeClock, i.acc, emptyList(), emptyList(),
            i.focalPrior, i.w, i.h, i.gray, i.pickFrame, i.pickMask, i.tracks) }
        val l = RecordingIO.Loaded(inp, l0.frameIndex, l0.dir)
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

    /** No rotation from any sensor (what the DT50 recording showed): the camera's own rotation, accelerometer for scale. */
    @Test fun boxWithoutAnyRotationSensor() {
        val (got, truth) = run("box_dt50", noRotation = true)
        for (i in 0 until 3) assertTrue("dimension $i: ${got[i]} vs ${truth[i]}", abs(got[i] - truth[i]) <= 3.0)
    }

    @Test fun sackWithoutAnyRotationSensor() {
        val (got, truth) = run("sack_dt50", noRotation = true)
        for (i in 0 until 3) assertTrue("dimension $i: ${got[i]} vs ${truth[i]}", abs(got[i] - truth[i]) <= 6.0)
    }

    /**
     * The phone's whole path: frames tracked one by one while "recording" (RecordingTracker, as the recorder feeds it),
     * then the engine at "Selesai" with those tracks and greys, no rotation sensor. Times both halves.
     */
    @Test fun phonePathTracksWhileRecording() {
        for (name in listOf("box_dt50", "sack_dt50")) {
            val dir = File(javaClass.getResource("/sweep/$name/session.json")!!.toURI()).parentFile
            val tr = RecordingTracker()
            val frames = File(dir, "frames").listFiles()!!.sortedBy { it.name }
            val nv = frames.map { f ->
                val img = TestImages.read(f.inputStream())
                ByteArray(img.w * img.h * 3 / 2) { i -> if (i < img.w * img.h) { val c = img.px[i]
                    (((c shr 16 and 255) * 299 + (c shr 8 and 255) * 587 + (c and 255) * 114) / 1000).toByte() } else 128.toByte() } to img
            }
            val t0 = System.nanoTime()
            for ((k, p) in nv.withIndex()) tr.offer(k, p.first, p.second.w, p.second.h, 90)
            val prep = tr.finish()!!
            val tRec = (System.nanoTime() - t0) / 1e9
            val l0 = RecordingIO.load(dir, ::gray, ::mask, prepared = prep)
            val inp = l0.input.let { i -> SweepInput(i.tCam, i.arrival, i.realtimeClock, i.acc, emptyList(), emptyList(),
                i.focalPrior, i.w, i.h, i.gray, i.pickFrame, i.pickMask, i.tracks) }
            assertTrue("the recording's tracks are used", inp.tracks != null)
            val t1 = System.nanoTime()
            val r = Engine.run(inp)
            val tStop = (System.nanoTime() - t1) / 1e9
            val truth = Json.parseToJsonElement(File(dir, "truth.json").readText()).jsonObject["size_cm"]!!.jsonArray.map { it.jsonPrimitive.double }
            println("$name phone path: ${"%.1f x %.1f x %.1f".format(r.lengthCm, r.widthCm, r.heightCm)} cm (truth ${truth.joinToString(" x ") { "%.1f".format(it) }}), " +
                "tracking during recording ${"%.1f".format(tRec)} s for ${frames.size} frames, after Selesai ${"%.2f".format(tStop)} s, ${r.method}")
            val tol = if (name.startsWith("box")) 3.0 else 6.0
            val got = doubleArrayOf(r.lengthCm, r.widthCm, r.heightCm)
            for (i in 0 until 3) assertTrue("$name dimension $i: ${got[i]} vs ${truth[i]}", abs(got[i] - truth[i]) <= tol)
        }
    }

    /**
     * As the first real DT50 recording (20261104_171719): no rotation sensor, about 8 saved frames a second, one
     * 0,3–0,4 s hole, some frames blurred, a dim room (dark, noisy). Here every second frame of the synthetic sweep,
     * two of those dropped in the middle, every 4th blurred, two flat (nothing to track), all darkened with noise.
     */
    internal fun degraded(i: SweepInput, step: Int = 2, hole: Boolean = true, blur: Boolean = true, dark: Boolean = true, blank: Boolean = true): SweepInput {
        val keep = (0 until i.tCam.size step step).toMutableList()
        val mid = keep.size / 2; if (hole) { keep.removeAt(mid); keep.removeAt(mid) }
        val rnd = java.util.Random(5)
        val cache = HashMap<Int, Gray>()
        fun dim(k: Int): Gray = synchronized(cache) { cache.getOrPut(k) {
            val g = i.gray(keep[k])
            var p = g.p
            // two frames with nothing to track (a hand over the lens, a whip of the phone): flat grey
            if (blank && (k == keep.size / 3 || k == keep.size / 3 + 1)) p = FloatArray(p.size) { 120f }
            if (blur && k % 4 == 1) {                                     // motion blur: 9 px along x
                p = FloatArray(p.size) { idx -> val x = idx % g.w; var s = 0f; var c = 0
                    for (d in -4..4) { val xx = x + d; if (xx in 0 until g.w) { s += g.p[idx + d]; c++ } }; s / c }
            }
            if (!dark) Gray(g.w, g.h, p) else Gray(g.w, g.h, FloatArray(p.size) { (p[it] * 0.35f + rnd.nextGaussian().toFloat() * 4f).coerceIn(0f, 255f) })
        } }
        return SweepInput(DoubleArray(keep.size) { i.tCam[keep[it]] }, i.arrival?.let { a -> DoubleArray(keep.size) { a[keep[it]] } }, i.realtimeClock,
            i.acc, emptyList(), emptyList(), i.focalPrior, i.w, i.h, { dim(it) }, 0, i.pickMask, null)
    }

    @Test fun dt50LikeRecordingSlowBlurredDim() {
        for (name in listOf("box_dt50", "sack_dt50")) {
            val dir = File(javaClass.getResource("/sweep/$name/session.json")!!.toURI()).parentFile
            val inp = degraded(RecordingIO.load(dir, ::gray, ::mask).input)
            Engine.trace = { println("  [$name degraded] $it") }
            val r = Engine.run(inp)
            val truth = Json.parseToJsonElement(File(dir, "truth.json").readText()).jsonObject["size_cm"]!!.jsonArray.map { it.jsonPrimitive.double }
            println("$name degraded (${inp.tCam.size} frames): ${"%.1f x %.1f x %.1f".format(r.lengthCm, r.widthCm, r.heightCm)} cm (truth ${truth.joinToString(" x ") { "%.1f".format(it) }}), " +
                "${r.method}, conf ${r.confidence}, ${"%.1f".format(r.seconds)} s, notes ${r.notes}")
            val tol = if (name.startsWith("box")) 4.0 else 7.0
            val got = doubleArrayOf(r.lengthCm, r.widthCm, r.heightCm)
            for (k in 0 until 3) assertTrue("$name dimension $k: ${got[k]} vs ${truth[k]}", abs(got[k] - truth[k]) <= tol)
        }
    }

    @Test fun irregularSackOnTheDt50() {
        val (got, truth) = run("sack_dt50")
        for (i in 0 until 3) assertTrue("dimension $i: ${got[i]} vs ${truth[i]}", abs(got[i] - truth[i]) <= 6.0)
    }
}
