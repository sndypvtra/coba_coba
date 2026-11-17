package id.ukuraja.app.ui

import id.ukurpaket.app.marker.Aruco
import id.ukurpaket.app.marker.Luma
import id.ukurpaket.app.marker.MarkerScale
import id.ukurpaket.app.marker.MarkerSheet
import id.ukurpaket.app.photo.PhotoCamera
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** What the live check sees in the preview: the sheet (id), how big it is, and its corners as fractions of the upright picture. */
data class LiveMarkerState(val id: Int?, val sidePx: Float, val corners: List<Float>?, val atMs: Long, val big: Boolean) {
    companion object { val NONE = LiveMarkerState(null, 0f, null, 0L, false) }
}

/**
 * Finds the marker sheet in the camera preview a few times a second (half-size grey picture, its own thread, the newest
 * frame only), so the courier sees before pressing the button that the sheet is in view and big enough.
 */
class LiveMarker(private val onState: (LiveMarkerState) -> Unit) : PhotoCamera.PreviewListener {
    private val busy = AtomicBoolean(false)
    private val worker = Executors.newSingleThreadExecutor { r -> Thread(r, "live-marker").apply { priority = Thread.NORM_PRIORITY - 1 } }
    @Volatile private var closed = false

    override fun wants() = !closed && !busy.get()

    override fun onFrame(luma: ByteArray, w: Int, h: Int, rotation: Int) {
        if (!busy.compareAndSet(false, true)) return
        worker.execute {
            try {
                val half = Luma(w, h, luma).half()
                val found = runCatching { Aruco.detect(half, MarkerSheet.IDS, Aruco.Params(minSidePx = 12f)) }.getOrDefault(emptyList())
                val best = found.maxByOrNull { it.sidePx }
                val rot = ((rotation % 360) + 360) % 360
                val uw = if (rot == 90 || rot == 270) h else w; val uh = if (rot == 90 || rot == 270) w else h
                val corners = best?.corners?.flatMap { p ->
                    val (x, y) = upright(p.a * 2, p.b * 2, w, h, rot)
                    listOf(x / uw, y / uh)
                }
                // big enough for a scale in the photo: the engine's minimum, at the full picture's size, with a margin
                val full = (best?.sidePx ?: 0f) * 2
                val big = full >= MarkerScale.MIN_SIDE_PX * 1.3 * uw / 480.0
                if (!closed) onState(LiveMarkerState(best?.id, full, corners, System.currentTimeMillis(), big))
            } finally { busy.set(false) }
        }
    }

    fun close() { closed = true; worker.shutdownNow() }

    companion object {
        /** A continuous position in the sensor's picture ([w] x [h]) turned upright by [rot] (as PhotoFiles.uprightLuma). */
        fun upright(x: Float, y: Float, w: Int, h: Int, rot: Int): Pair<Float, Float> = when (rot) {
            90 -> (h - y) to x
            180 -> (w - x) to (h - y)
            270 -> y to (w - x)
            else -> x to y
        }
    }
}
