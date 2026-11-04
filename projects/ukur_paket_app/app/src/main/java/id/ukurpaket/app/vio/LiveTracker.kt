package id.ukurpaket.app.vio

import id.ukurpaket.app.measure.P2
import id.ukurpaket.app.measure.convexHull
import id.ukurpaket.app.measure.inside
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit

/**
 * Follows the picked object during recording, for the live outline: a light KLT tracker on the newest frame only
 * (frames are dropped while it is busy). Tracks inside the pick (box, or a disc round the tap) at the start are the
 * object's; a track born later inside the object's current outline joins it. [onOutline] gets the outline as x, y
 * pairs in fractions of the upright picture. The measurement itself is computed afterwards from the saved frames.
 */
class LiveTracker(private val rotation: Int, private val region: (Float, Float) -> Boolean, private val onOutline: (FloatArray, Int) -> Unit) {
    private val tracker = Tracker(maxTracks = 260, minDist = 12)
    private val member = HashSet<Int>()
    private val exec = ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, ArrayBlockingQueue(1), ThreadPoolExecutor.DiscardPolicy())
    @Volatile private var first = true

    /** Luma of one frame (sensor orientation); copied before returning. */
    fun offer(luma: ByteArray, w: Int, h: Int) {
        if (exec.queue.isNotEmpty() || exec.activeCount > 0) return
        val copy = luma.copyOf(w * h)
        exec.execute { step(Gray.fromLuma(copy, w, h, down = if (w > 1000) 2 else 1, rotation = rotation)) }
    }

    private fun step(g: Gray) {
        val live = tracker.feed(g)
        val w = g.w.toFloat(); val h = g.h.toFloat()
        if (first) {
            for (t in live) if (region(t.lastX() / w, t.lastY() / h)) member.add(t.id)
            first = false
        } else {
            val mem = live.filter { it.id in member }
            if (mem.size >= 3) {
                val hull = shrunk(convexHull(mem.map { P2(it.lastX(), it.lastY()) }), 0.92f)
                for (t in live) if (t.id !in member && t.n == 1 && inside(hull, t.lastX(), t.lastY())) member.add(t.id)
            }
        }
        val mem = live.filter { it.id in member }
        val hull = if (mem.size >= 3) convexHull(mem.map { P2(it.lastX() / w, it.lastY() / h) }) else emptyList()
        onOutline(FloatArray(hull.size * 2) { if (it % 2 == 0) hull[it / 2].a else hull[it / 2].b }, mem.size)
    }

    private fun shrunk(p: List<P2>, k: Float): List<P2> {
        if (p.isEmpty()) return p
        val cx = p.map { it.a }.average().toFloat(); val cy = p.map { it.b }.average().toFloat()
        return p.map { P2(cx + (it.a - cx) * k, cy + (it.b - cy) * k) }
    }

    fun close() = exec.shutdownNow()
}
