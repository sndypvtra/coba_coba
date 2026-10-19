package id.ukurpaket.app.measure

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.FloatBuffer
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** A parcel cut out of an image, one flag per pixel. */
class Mask(val w: Int, val h: Int, val bits: BooleanArray, val score: Float = 1f) {
    operator fun get(x: Int, y: Int) = x in 0 until w && y in 0 until h && bits[y * w + x]
    operator fun get(x: Float, y: Float) = get(floor(x).toInt(), floor(y).toInt())
    val area: Int get() = bits.count { it }

    /** x0, y0, x1, y1 (inclusive), or null when empty. */
    fun bounds(): IntArray? {
        var x0 = w; var y0 = h; var x1 = -1; var y1 = -1
        for (y in 0 until h) for (x in 0 until w) if (bits[y * w + x]) {
            if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y
        }
        return if (x1 < 0) null else intArrayOf(x0, y0, x1, y1)
    }

    /** Only the largest connected part (a mask sometimes adds a few stray specks). */
    fun largestPart(): Mask {
        val label = IntArray(w * h)
        val queue = IntArray(w * h)
        var best = 0; var bestSize = 0; var next = 0
        for (i in bits.indices) {
            if (!bits[i] || label[i] != 0) continue
            next++
            var head = 0; var tail = 0
            queue[tail++] = i; label[i] = next
            while (head < tail) {
                val p = queue[head++]
                val x = p % w; val y = p / w
                if (x > 0 && bits[p - 1] && label[p - 1] == 0) { label[p - 1] = next; queue[tail++] = p - 1 }
                if (x < w - 1 && bits[p + 1] && label[p + 1] == 0) { label[p + 1] = next; queue[tail++] = p + 1 }
                if (y > 0 && bits[p - w] && label[p - w] == 0) { label[p - w] = next; queue[tail++] = p - w }
                if (y < h - 1 && bits[p + w] && label[p + w] == 0) { label[p + w] = next; queue[tail++] = p + w }
            }
            if (tail > bestSize) { bestSize = tail; best = next }
        }
        return Mask(w, h, BooleanArray(w * h) { label[it] == best && best != 0 }, score)
    }

    /** The outline of the largest part as a polygon in image pixels, simplified to a few dozen points. */
    fun outline(): List<P2> {
        val f = max(1, max(w, h) / 240)
        val gw = (w + f - 1) / f; val gh = (h + f - 1) / f
        val g = BooleanArray(gw * gh) { i -> get((i % gw) * f + f / 2, (i / gw) * f + f / 2) }
        val ring = traceBoundary(Mask(gw, gh, g).largestPart().bits, gw, gh)
        if (ring.size < 3) return emptyList()
        return simplifyClosed(ring.map { P2((it.a + 0.5f) * f, (it.b + 0.5f) * f) }, 1.2f * f)
    }

    fun iou(o: Mask): Float {
        var i = 0; var u = 0
        for (k in bits.indices) { if (bits[k] && o.bits[k]) i++; if (bits[k] || o.bits[k]) u++ }
        return if (u == 0) 0f else i.toFloat() / u
    }
}

/** Moore-neighbour boundary trace of the first blob in raster order, clockwise, in grid cells. */
internal fun traceBoundary(g: BooleanArray, gw: Int, gh: Int): List<P2> {
    val start = g.indexOfFirst { it }
    if (start < 0) return emptyList()
    val dx = intArrayOf(-1, -1, 0, 1, 1, 1, 0, -1)
    val dy = intArrayOf(0, -1, -1, -1, 0, 1, 1, 1)
    fun on(x: Int, y: Int) = x in 0 until gw && y in 0 until gh && g[y * gw + x]
    val sx = start % gw; val sy = start / gw
    val out = arrayListOf(P2(sx.toFloat(), sy.toFloat()))
    var x = sx; var y = sy; var b = 0                    // the cell we came from: west of the first cell is empty
    repeat(4 * gw * gh) {
        var moved = false
        for (k in 1..8) {
            val d = (b + k) % 8
            val nx = x + dx[d]; val ny = y + dy[d]
            if (on(nx, ny)) {
                val pd = (b + k - 1) % 8
                val bx = x + dx[pd] - nx; val by = y + dy[pd] - ny
                x = nx; y = ny
                b = (0 until 8).first { dx[it] == bx && dy[it] == by }
                moved = true
                break
            }
        }
        if (!moved || (x == sx && y == sy)) return out
        out.add(P2(x.toFloat(), y.toFloat()))
    }
    return out
}

/** Douglas-Peucker on a closed ring. */
internal fun simplifyClosed(pts: List<P2>, eps: Float): List<P2> {
    if (pts.size < 4) return pts
    val far = pts.indices.maxBy { (pts[it].a - pts[0].a).let { a -> a * a } + (pts[it].b - pts[0].b).let { b -> b * b } }
    fun dp(a: Int, b: Int, keep: BooleanArray) {
        if (b <= a + 1) return
        val p = pts[a]; val q = pts[b % pts.size]
        val ex = q.a - p.a; val ey = q.b - p.b
        val len = kotlin.math.sqrt(ex * ex + ey * ey).coerceAtLeast(1e-6f)
        var best = -1; var bestD = eps
        for (i in a + 1 until b) {
            val r = pts[i]
            val d = kotlin.math.abs(ex * (r.b - p.b) - ey * (r.a - p.a)) / len
            if (d > bestD) { bestD = d; best = i }
        }
        if (best >= 0) { keep[best] = true; dp(a, best, keep); dp(best, b, keep) }
    }
    val keep = BooleanArray(pts.size)
    keep[0] = true; keep[far] = true
    dp(0, far, keep); dp(far, pts.size, keep)
    return pts.filterIndexed { i, _ -> keep[i] }
}

/** The image encoder's output for one picture; prompts are decoded against it in a few milliseconds. */
class Embedding internal constructor(internal val data: FloatArray, val w: Int, val h: Int, internal val scale: Float)

/**
 * MobileSAM (Apache 2.0) through ONNX Runtime: the courier taps a parcel or draws a box around it, and
 * gets that parcel's mask. Encoder ~1 s per picture on a phone CPU, decoder a few ms per prompt.
 * Android-free, so the same code runs in the PC tests. Models: tools/export_sam.py.
 */
class Segmenter(encoder: ByteArray, decoder: ByteArray, threads: Int = 4) : AutoCloseable {
    private val env = OrtEnvironment.getEnvironment()
    private val opts = OrtSession.SessionOptions().apply { setIntraOpNumThreads(threads) }
    private val enc = env.createSession(encoder, opts)
    private val dec = env.createSession(decoder, opts)

    /** [argb] packed 0xAARRGGBB, row by row. */
    fun embed(argb: IntArray, w: Int, h: Int): Embedding {
        val s = SIZE.toFloat() / max(w, h)
        val nw = (w * s).roundToInt(); val nh = (h * s).roundToInt()
        val plane = SIZE * SIZE
        val buf = FloatArray(3 * plane)                  // padding stays 0 (after normalising), as in SAM
        for (y in 0 until nh) {
            val sy = ((y + 0.5f) / s - 0.5f).coerceIn(0f, h - 1f)
            val y0 = sy.toInt(); val y1 = min(y0 + 1, h - 1); val fy = sy - y0
            for (x in 0 until nw) {
                val sx = ((x + 0.5f) / s - 0.5f).coerceIn(0f, w - 1f)
                val x0 = sx.toInt(); val x1 = min(x0 + 1, w - 1); val fx = sx - x0
                val p00 = argb[y0 * w + x0]; val p01 = argb[y0 * w + x1]
                val p10 = argb[y1 * w + x0]; val p11 = argb[y1 * w + x1]
                for (c in 0 until 3) {
                    val sh = 16 - 8 * c
                    val v = ((p00 shr sh) and 255) * (1 - fx) * (1 - fy) + ((p01 shr sh) and 255) * fx * (1 - fy) +
                        ((p10 shr sh) and 255) * (1 - fx) * fy + ((p11 shr sh) and 255) * fx * fy
                    buf[c * plane + y * SIZE + x] = (v - MEAN[c]) / STD[c]
                }
            }
        }
        OnnxTensor.createTensor(env, FloatBuffer.wrap(buf), longArrayOf(1, 3, SIZE.toLong(), SIZE.toLong())).use { t ->
            enc.run(mapOf("image" to t)).use { r ->
                val fb = (r[0] as OnnxTensor).floatBuffer
                val out = FloatArray(fb.remaining()); fb.get(out)
                return Embedding(out, w, h, s)
            }
        }
    }

    /** The parcel under one tap. */
    fun tap(e: Embedding, x: Float, y: Float): Mask = decode(e, floatArrayOf(x, y, 0f, 0f), floatArrayOf(1f, -1f))

    /** The parcel inside a drawn box (the fix when a tap only picks part of it). */
    fun box(e: Embedding, x0: Float, y0: Float, x1: Float, y1: Float): Mask =
        decode(e, floatArrayOf(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), floatArrayOf(2f, 3f))

    private fun decode(e: Embedding, pts: FloatArray, labels: FloatArray): Mask {
        val n = labels.size.toLong()
        val coords = FloatArray(pts.size) { i -> if (labels[i / 2] < 0) 0f else pts[i] * e.scale }
        val emb = OnnxTensor.createTensor(env, FloatBuffer.wrap(e.data), longArrayOf(1, 256, 64, 64))
        val c = OnnxTensor.createTensor(env, FloatBuffer.wrap(coords), longArrayOf(1, n, 2))
        val l = OnnxTensor.createTensor(env, FloatBuffer.wrap(labels), longArrayOf(1, n))
        try {
            dec.run(mapOf("embeddings" to emb, "coords" to c, "labels" to l)).use { r ->
                val mb = (r[0] as OnnxTensor).floatBuffer
                val sb = (r[1] as OnnxTensor).floatBuffer
                val scores = FloatArray(sb.remaining()); sb.get(scores)
                val best = scores.indices.maxBy { scores[it] }          // best-scoring of the three masks
                val grid = FloatArray(LOW * LOW)
                mb.position(best * LOW * LOW); mb.get(grid)
                return Mask(e.w, e.h, upsample(grid, e), scores[best])
            }
        } finally { emb.close(); c.close(); l.close() }
    }

    /** 256 x 256 logits over the padded 1024 frame -> one flag per original pixel (bilinear, > 0). */
    private fun upsample(g: FloatArray, e: Embedding): BooleanArray {
        val out = BooleanArray(e.w * e.h)
        val k = e.scale * LOW / SIZE
        for (y in 0 until e.h) {
            val v = ((y + 0.5f) * k - 0.5f).coerceIn(0f, LOW - 1f)
            val v0 = v.toInt(); val v1 = min(v0 + 1, LOW - 1); val fv = v - v0
            for (x in 0 until e.w) {
                val u = ((x + 0.5f) * k - 0.5f).coerceIn(0f, LOW - 1f)
                val u0 = u.toInt(); val u1 = min(u0 + 1, LOW - 1); val fu = u - u0
                val a = g[v0 * LOW + u0] * (1 - fu) + g[v0 * LOW + u1] * fu
                val b = g[v1 * LOW + u0] * (1 - fu) + g[v1 * LOW + u1] * fu
                out[y * e.w + x] = a * (1 - fv) + b * fv > 0f
            }
        }
        return out
    }

    override fun close() { enc.close(); dec.close(); opts.close() }

    companion object {
        const val SIZE = 1024
        private const val LOW = 256
        private val MEAN = floatArrayOf(123.675f, 116.28f, 103.53f)
        private val STD = floatArrayOf(58.395f, 57.12f, 57.375f)
    }
}

/** The mask grown by [r] pixels (square), so depth points that land a little off the edge still count. */
fun Mask.dilate(r: Int): Mask {
    if (r <= 0) return this
    val tmp = BooleanArray(w * h)
    for (y in 0 until h) {
        var last = -r - 1
        for (x in 0 until w) if (bits[y * w + x]) last = x else if (x - last <= r) tmp[y * w + x] = true
        last = w + r + 1
        for (x in w - 1 downTo 0) if (bits[y * w + x]) { last = x; tmp[y * w + x] = true } else if (last - x <= r) tmp[y * w + x] = true
    }
    val out = BooleanArray(w * h)
    for (x in 0 until w) {
        var last = -r - 1
        for (y in 0 until h) if (tmp[y * w + x]) last = y else if (y - last <= r) out[y * w + x] = true
        last = h + r + 1
        for (y in h - 1 downTo 0) if (tmp[y * w + x]) { last = y; out[y * w + x] = true } else if (last - y <= r) out[y * w + x] = true
    }
    return Mask(w, h, out, score)
}
