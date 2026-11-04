package id.ukurpaket.app.vio

import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

/**
 * The engine's tracking done while recording, so that only the rest is left when recording stops: every saved frame,
 * in order, is turned into the upright tracking grey and fed to the engine's tracker on its own thread (KLT spread
 * over the cores). The same thread drives the live segmentation with these tracks, on the frames it is not behind on.
 * The greys are kept (one byte per pixel) so the engine reads no JPEG back.
 */
class RecordingTracker(pool: Par = Par.default) {
    class Prepared(val frameIndex: IntArray, val tracks: List<Track>, val grays: List<GrayBytes>)

    /** A grey picture at one byte per pixel (a fifth of the float one). */
    class GrayBytes(val w: Int, val h: Int, val p: ByteArray) {
        fun gray() = Gray(w, h, FloatArray(p.size) { (p[it].toInt() and 255).toFloat() })
        companion object { fun of(g: Gray) = GrayBytes(g.w, g.h, ByteArray(g.p.size) { g.p[it].toInt().coerceIn(0, 255).toByte() }) }
    }

    private class Item(val idx: Int, val g: GrayBytes, val nv21: ByteArray?, val sw: Int, val sh: Int, val rotation: Int)
    private object End

    val tracker = Tracker(levels = ENGINE_LEVELS, pool = pool)
    @Volatile var seg: LiveSegmenter? = null
    private val queue = LinkedBlockingQueue<Any>()
    private val idx = ArrayList<Int>()
    private val grays = ArrayList<GrayBytes>()
    @Volatile private var failed = false
    val backlog get() = queue.size
    private val thread = Thread({ loop() }, "sweep-track").apply { isDaemon = true; start() }

    /** A saved frame (NV21, sensor orientation), in saving order. Converted here; tracked on the tracking thread. */
    fun offer(index: Int, nv21: ByteArray, sw: Int, sh: Int, rotation: Int) {
        val g = GrayBytes.of(Gray.fromLuma(nv21, sw, sh, down = if (sw > 1000) 2 else 1, rotation = rotation))
        // colour for the live segmentation only while the tracker keeps up (a copy is 1,8 MB at 1280 x 960)
        val colour = if (seg != null && queue.size <= 2) nv21.copyOf(sw * sh * 3 / 2) else null
        queue.put(Item(index, g, colour, sw, sh, rotation))
    }

    private fun loop() {
        while (true) {
            val it = queue.take()
            if (it === End) return
            it as Item
            try {
                val g = it.g.gray()
                val live = tracker.feed(g)
                idx.add(it.idx); grays.add(it.g)
                val s = seg
                val c = it.nv21
                // the live view must never cost the measurement: its failures stay its own
                if (s != null && c != null) runCatching { s.step(it.idx, g, { Yuv.argb(c, it.sw, it.sh, it.rotation, s.w, s.h) },
                    { Yuv.argb(c, it.sw, it.sh, it.rotation, s.w / 4, s.h / 4) }, live) }
            } catch (e: Throwable) { failed = true }
        }
    }

    /** No more frames: the rest of the queue is tracked, then the tracks are handed over (null if tracking failed). */
    fun finish(timeoutS: Long = 120): Prepared? {
        queue.put(End)
        thread.join(TimeUnit.SECONDS.toMillis(timeoutS))
        if (thread.isAlive || failed) return null
        return Prepared(idx.toIntArray(), tracker.tracks, grays)
    }

    /** Recording abandoned. */
    fun cancel() { queue.clear(); queue.put(End) }

    companion object {
        /** Pyramid levels of the engine's tracker: 4, for the 40–60 px a hand-held sweep can move between frames. */
        const val ENGINE_LEVELS = 4
    }
}
