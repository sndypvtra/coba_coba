package id.ukurpaket.app.vio

import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/** Grey image (0..255 floats), row-major. */
class Gray(val w: Int, val h: Int, val p: FloatArray) {
    fun at(x: Float, y: Float): Float {
        val xc = x.coerceIn(0f, w - 1.001f); val yc = y.coerceIn(0f, h - 1.001f)
        val x0 = xc.toInt(); val y0 = yc.toInt(); val fx = xc - x0; val fy = yc - y0
        val i = y0 * w + x0
        val a = p[i] + (p[i + 1] - p[i]) * fx
        val b = p[i + w] + (p[i + w + 1] - p[i + w]) * fx
        return a + (b - a) * fy
    }

    fun half(): Gray {
        val nw = w / 2; val nh = h / 2
        val o = FloatArray(nw * nh)
        for (y in 0 until nh) {
            val r0 = 2 * y * w; val r1 = r0 + w
            for (x in 0 until nw) { val c = 2 * x; o[y * nw + x] = (p[r0 + c] + p[r0 + c + 1] + p[r1 + c] + p[r1 + c + 1]) * 0.25f }
        }
        return Gray(nw, nh, o)
    }

    companion object {
        /**
         * Luma bytes (sensor orientation) -> upright grey, shrunk by [down] (1 or 2) and turned clockwise by [rotation]
         * (0/90/180/270), as the recorder's frames stand upright on the phone.
         */
        fun fromLuma(y: ByteArray, w: Int, h: Int, rowStride: Int = w, down: Int = 1, rotation: Int = 90): Gray {
            val sw = w / down; val sh = h / down
            val s = FloatArray(sw * sh)
            for (yy in 0 until sh) for (xx in 0 until sw) {
                if (down == 1) s[yy * sw + xx] = (y[yy * rowStride + xx].toInt() and 255).toFloat()
                else {
                    val r0 = 2 * yy * rowStride + 2 * xx
                    s[yy * sw + xx] = ((y[r0].toInt() and 255) + (y[r0 + 1].toInt() and 255) + (y[r0 + rowStride].toInt() and 255) +
                        (y[r0 + rowStride + 1].toInt() and 255)) * 0.25f
                }
            }
            return rotate(Gray(sw, sh, s), rotation)
        }

        fun rotate(g: Gray, rotation: Int): Gray = when (((rotation % 360) + 360) % 360) {
            90 -> Gray(g.h, g.w, FloatArray(g.w * g.h).also { o -> for (y in 0 until g.h) for (x in 0 until g.w) o[x * g.h + (g.h - 1 - y)] = g.p[y * g.w + x] })
            180 -> Gray(g.w, g.h, FloatArray(g.w * g.h) { g.p[g.w * g.h - 1 - it] })
            270 -> Gray(g.h, g.w, FloatArray(g.w * g.h).also { o -> for (y in 0 until g.h) for (x in 0 until g.w) o[(g.w - 1 - x) * g.h + y] = g.p[y * g.w + x] })
            else -> g
        }
    }
}

/** Image pyramid with horizontal / vertical gradients per level. */
class Pyramid(base: Gray, levels: Int = 3) {
    val img = ArrayList<Gray>()
    val gx = ArrayList<FloatArray>()
    val gy = ArrayList<FloatArray>()

    init {
        var g = base
        for (l in 0 until levels) {
            img.add(g)
            val x = FloatArray(g.w * g.h); val y = FloatArray(g.w * g.h)
            for (r in 1 until g.h - 1) for (c in 1 until g.w - 1) {
                val i = r * g.w + c
                x[i] = (g.p[i + 1] - g.p[i - 1]) * 0.5f; y[i] = (g.p[i + g.w] - g.p[i - g.w]) * 0.5f
            }
            gx.add(x); gy.add(y)
            if (l < levels - 1) g = g.half()
        }
    }

    fun grad(l: Int, x: Float, y: Float, which: FloatArray): Float {
        val g = img[l]
        val xc = x.coerceIn(0f, g.w - 1.001f); val yc = y.coerceIn(0f, g.h - 1.001f)
        val x0 = xc.toInt(); val y0 = yc.toInt(); val fx = xc - x0; val fy = yc - y0; val i = y0 * g.w + x0
        val a = which[i] + (which[i + 1] - which[i]) * fx
        val b = which[i + g.w] + (which[i + g.w + 1] - which[i + g.w]) * fx
        return a + (b - a) * fy
    }
}

object Klt {
    const val HALF = 5           // 11 x 11 window

    /**
     * Pyramidal Lucas-Kanade (Bouguet) from [a] at (x, y) into [b]; returns (x', y') or null when it does not converge
     * or leaves the picture.
     */
    fun track(a: Pyramid, b: Pyramid, x: Float, y: Float): FloatArray? {
        var gxs = 0f; var gys = 0f
        val n = (2 * HALF + 1) * (2 * HALF + 1)
        val ti = FloatArray(n); val tx = FloatArray(n); val ty = FloatArray(n)
        for (l in a.img.size - 1 downTo 0) {
            val s = 1f / (1 shl l)
            val px = x * s; val py = y * s
            val ia = a.img[l]; val ib = b.img[l]
            if (px < HALF + 1 || py < HALF + 1 || px > ia.w - HALF - 2 || py > ia.h - HALF - 2) {
                if (l == 0) return null
                gxs *= 2f; gys *= 2f; continue
            }
            var g11 = 0f; var g12 = 0f; var g22 = 0f; var k = 0
            for (dy in -HALF..HALF) for (dx in -HALF..HALF) {
                val sx = px + dx; val sy = py + dy
                ti[k] = ia.at(sx, sy); tx[k] = a.grad(l, sx, sy, a.gx[l]); ty[k] = a.grad(l, sx, sy, a.gy[l])
                g11 += tx[k] * tx[k]; g12 += tx[k] * ty[k]; g22 += ty[k] * ty[k]; k++
            }
            val det = g11 * g22 - g12 * g12
            if (det < 1e-3f) return null
            var vx = 0f; var vy = 0f
            for (it in 0 until 10) {
                var b1 = 0f; var b2 = 0f; k = 0
                val qx = px + gxs + vx; val qy = py + gys + vy
                if (qx < 1 || qy < 1 || qx > ib.w - 2 || qy > ib.h - 2) return null
                for (dy in -HALF..HALF) for (dx in -HALF..HALF) {
                    val d = ib.at(qx + dx, qy + dy) - ti[k]
                    b1 += d * tx[k]; b2 += d * ty[k]; k++
                }
                val ex = -(g22 * b1 - g12 * b2) / det; val ey = -(-g12 * b1 + g11 * b2) / det
                vx += ex; vy += ey
                if (ex * ex + ey * ey < 0.0009f) break
            }
            if (l > 0) { gxs = 2f * (gxs + vx); gys = 2f * (gys + vy) } else { gxs += vx; gys += vy }
        }
        val nx = x + gxs; val ny = y + gys
        val g0 = b.img[0]
        if (nx < 2 || ny < 2 || nx > g0.w - 3 || ny > g0.h - 3) return null
        return floatArrayOf(nx, ny)
    }

    /**
     * Shi-Tomasi corners (minimum eigenvalue of the 5 x 5 structure tensor), one per [cell] x [cell] block, at least
     * [minDist] from [taken] points and above [quality] x the best response.
     */
    fun corners(p: Pyramid, want: Int, minDist: Int, taken: List<FloatArray>, quality: Float = 0.01f, cell: Int = 12): List<FloatArray> {
        val g = p.img[0]; val w = g.w; val h = g.h; val gx = p.gx[0]; val gy = p.gy[0]
        val iw = w + 1
        val sxx = DoubleArray(iw * (h + 1)); val syy = DoubleArray(iw * (h + 1)); val sxy = DoubleArray(iw * (h + 1))
        for (y in 0 until h) {
            var rx = 0.0; var ry = 0.0; var rxy = 0.0
            for (x in 0 until w) {
                val i = y * w + x
                rx += gx[i] * gx[i]; ry += gy[i] * gy[i]; rxy += gx[i] * gy[i]
                val o = (y + 1) * iw + x + 1
                sxx[o] = sxx[o - iw] + rx; syy[o] = syy[o - iw] + ry; sxy[o] = sxy[o - iw] + rxy
            }
        }
        fun box(s: DoubleArray, x: Int, y: Int) = s[(y + 3) * iw + x + 3] - s[(y - 2) * iw + x + 3] - s[(y + 3) * iw + x - 2] + s[(y - 2) * iw + x - 2]
        val cw = (w + cell - 1) / cell; val ch = (h + cell - 1) / cell
        val best = FloatArray(cw * ch); val bx = IntArray(cw * ch); val by = IntArray(cw * ch)
        var top = 0f
        val m = HALF + 3
        var y = m
        while (y < h - m) {
            var x = m
            while (x < w - m) {
                val a = box(sxx, x, y); val c = box(syy, x, y); val b = box(sxy, x, y)
                val l = ((a + c) / 2 - sqrt(((a - c) / 2) * ((a - c) / 2) + b * b)).toFloat()
                val ci = (y / cell) * cw + x / cell
                if (l > best[ci]) { best[ci] = l; bx[ci] = x; by[ci] = y }
                if (l > top) top = l
                x += 2
            }
            y += 2
        }
        // occupancy of the live tracks
        val oc = max(1, minDist)
        val ow = w / oc + 1; val oh = h / oc + 1
        val occ = BooleanArray(ow * oh)
        for (t in taken) {
            val cx = (t[0] / oc).toInt(); val cy = (t[1] / oc).toInt()
            for (dy in -1..1) for (dx in -1..1) { val xx = cx + dx; val yy = cy + dy; if (xx in 0 until ow && yy in 0 until oh) occ[yy * ow + xx] = true }
        }
        val cand = (0 until cw * ch).filter { best[it] > quality * top && best[it] > 0f }.sortedByDescending { best[it] }
        val out = ArrayList<FloatArray>()
        for (ci in cand) {
            if (out.size >= want) break
            val cx = bx[ci] / oc; val cy = by[ci] / oc
            if (occ[cy * ow + cx]) continue
            for (dy in -1..1) for (dx in -1..1) { val xx = cx + dx; val yy = cy + dy; if (xx in 0 until ow && yy in 0 until oh) occ[yy * ow + xx] = true }
            out.add(floatArrayOf(bx[ci].toFloat(), by[ci].toFloat()))
        }
        return out
    }
}

/** Growable track storage: per track the frames it was seen in and where. */
class Track(val id: Int) {
    var f = IntArray(16); var x = FloatArray(16); var y = FloatArray(16); var n = 0
    fun add(frame: Int, px: Float, py: Float) {
        if (n == f.size) { f = f.copyOf(n * 2); x = x.copyOf(n * 2); y = y.copyOf(n * 2) }
        f[n] = frame; x[n] = px; y[n] = py; n++
    }
    fun lastX() = x[n - 1]
    fun lastY() = y[n - 1]
    fun at(frame: Int): Int { for (i in n - 1 downTo 0) { if (f[i] == frame) return i; if (f[i] < frame) return -1 }; return -1 }
}

/**
 * KLT tracker over a sweep: frames in order (upright grey), tracks kept while forward-backward consistent, new
 * corners topped up in empty places. Every observation is kept for the solver.
 */
class Tracker(val maxTracks: Int = 700, val minDist: Int = 9, val fbMax: Float = 0.7f, val levels: Int = 3) {
    val tracks = ArrayList<Track>()
    private val live = ArrayList<Track>()
    private var prev: Pyramid? = null
    var frames = 0; private set
    var width = 0; private set
    var height = 0; private set

    /** Adds one frame; returns the tracks alive in it. */
    fun feed(g: Gray): List<Track> {
        val pyr = Pyramid(g, levels)
        width = g.w; height = g.h
        val k = frames
        val pp = prev
        if (pp != null) {
            val keep = ArrayList<Track>()
            for (t in live) {
                val fw = Klt.track(pp, pyr, t.lastX(), t.lastY()) ?: continue
                val bw = Klt.track(pyr, pp, fw[0], fw[1]) ?: continue
                if (abs(bw[0] - t.lastX()) + abs(bw[1] - t.lastY()) > fbMax) continue
                t.add(k, fw[0], fw[1]); keep.add(t)
            }
            live.clear(); live.addAll(keep)
        }
        if (live.size < maxTracks * 0.8) {
            val taken = live.map { floatArrayOf(it.lastX(), it.lastY()) }
            for (c in Klt.corners(pyr, maxTracks - live.size, minDist, taken)) {
                val t = Track(tracks.size); t.add(k, c[0], c[1]); tracks.add(t); live.add(t)
            }
        }
        prev = pyr
        frames++
        return live
    }

    fun alive(): List<Track> = live

    /** Up to [n] new corners on the last frame where [inside] says, beyond the usual top-up (an object losing its points). */
    fun topUp(n: Int, inside: (Float, Float) -> Boolean): Int {
        val pyr = prev ?: return 0
        val taken = live.map { floatArrayOf(it.lastX(), it.lastY()) }
        var added = 0
        for (c in Klt.corners(pyr, 4 * maxTracks, minDist, taken)) {
            if (added >= n) break
            if (!inside(c[0], c[1])) continue
            val t = Track(tracks.size); t.add(frames - 1, c[0], c[1]); tracks.add(t); live.add(t); added++
        }
        return added
    }

    companion object {
        fun floorI(v: Float) = floor(v).toInt()
        fun clampI(v: Int, lo: Int, hi: Int) = min(max(v, lo), hi)
    }
}
