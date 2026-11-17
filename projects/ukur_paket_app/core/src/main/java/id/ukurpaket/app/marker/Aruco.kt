package id.ukurpaket.app.marker

import id.ukurpaket.app.measure.P2
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * A grey picture (luma 0-255), row-major. Positions are continuous: pixel (i, j) covers [i, i+1) x [j, j+1), its centre
 * at (i + 0.5, j + 0.5), the same convention as the photo engine (Intrinsics.ray(x + 0.5, y + 0.5) for pixel x).
 */
class Luma(val w: Int, val h: Int, val px: ByteArray) {
    init { require(w > 1 && h > 1 && px.size >= w * h) { "luma $w x $h needs ${w * h} bytes" } }

    operator fun get(x: Int, y: Int) = px[y * w + x].toInt() and 255

    /** Bilinear value at continuous position ([x], [y]), clamped at the border. */
    fun at(x: Float, y: Float): Float {
        val fx = (x - 0.5f).coerceIn(0f, w - 1.0001f); val fy = (y - 0.5f).coerceIn(0f, h - 1.0001f)
        val x0 = fx.toInt(); val y0 = fy.toInt(); val ax = fx - x0; val ay = fy - y0
        val i = y0 * w + x0
        val a = px[i].toInt() and 255; val b = px[i + 1].toInt() and 255
        val c = px[i + w].toInt() and 255; val d = px[i + w + 1].toInt() and 255
        return (a * (1 - ax) + b * ax) * (1 - ay) + (c * (1 - ax) + d * ax) * ay
    }

    /** Half the size, each pixel the mean of a 2 x 2 block: a position p here is 2p in this picture. */
    fun half(): Luma {
        val nw = w / 2; val nh = h / 2
        val out = ByteArray(nw * nh)
        for (y in 0 until nh) {
            val r0 = 2 * y * w; val r1 = r0 + w
            for (x in 0 until nw) {
                val s = (px[r0 + 2 * x].toInt() and 255) + (px[r0 + 2 * x + 1].toInt() and 255) +
                    (px[r1 + 2 * x].toInt() and 255) + (px[r1 + 2 * x + 1].toInt() and 255)
                out[y * nw + x] = ((s + 2) / 4).toByte()
            }
        }
        return Luma(nw, nh, out)
    }
}

/**
 * One marker found in a picture. [corners]: the printed marker's own corners in the order top-left, top-right,
 * bottom-right, bottom-left (as the sheet reads upright), in picture positions, refined to a fraction of a pixel from
 * the four straight edges of its black border.
 */
data class MarkerDetection(
    val id: Int,
    val corners: List<P2>,
    /** Mean side length, pixels. */
    val sidePx: Float,
    /** Data bits that did not match the dictionary code (corrected), and border cells read white. */
    val bitErrors: Int,
    val borderErrors: Int,
    /** Grey levels between the white and the black cells. */
    val contrast: Float,
    /** RMS distance of the edge points from their fitted lines (pixels) and the corners' standard error from it. */
    val edgeRms: Float,
    val cornerSigmaPx: Float,
) {
    /** The same detection in a picture [s] times as large (corners scaled; positions are continuous, so no offset). */
    fun scaled(s: Float) = copy(corners = corners.map { P2(it.a * s, it.b * s) }, sidePx = sidePx * s, edgeRms = edgeRms * s, cornerSigmaPx = cornerSigmaPx * s)

    /** Corners as x, y, x, y… */
    fun flat(): List<Float> = corners.flatMap { listOf(it.a, it.b) }
}

/**
 * ArUco markers of OpenCV's DICT_4X4_50 (4 x 4 data bits inside a one-cell black border: 6 x 6 cells), found in a grey
 * picture with no library: the classic pipeline of OpenCV's detector, written out for the phone and the PC alike.
 *
 *  1. adaptive threshold (local mean minus [Params.offset]) at two window sizes, so small and large markers both give a
 *     closed dark ring along their black border;
 *  2. connected dark regions; the outer contour of each plausible one (Moore tracing), reduced to a polygon
 *     (Douglas-Peucker); convex quadrilaterals with sides of at least [Params.minSidePx] are candidates;
 *  3. each candidate's corners refined from its four edges: along each edge, the strongest white-to-black step across it
 *     (sub-pixel, parabola on the gradient), a straight line fitted to those points (total least squares, outliers out),
 *     corners where neighbouring lines meet; twice. A corner then sits to about 0.1 px on a sharp picture;
 *  4. the 6 x 6 cells read through the homography of the refined square (the middle of each cell), split into black and
 *     white by Otsu's threshold over the 36 cells; the border must be black, the contrast real; the 16 data bits are
 *     matched with the wanted codes in the four turns, at most [Params.maxBitErrors] bits apart.
 *
 * Only the ids asked for are accepted: the sheets printed for UkurAja use ids 1 (A4) and 2 (A3), whose codes differ from
 * each other in at least 8 bits in every turn, and from themselves turned in at least 8.
 */
object Aruco {
    /** OpenCV DICT_4X4_50, id -> 16 data bits row by row, first bit highest, 1 = white. */
    val DICT_4X4_50 = intArrayOf(
        0xB532, 0x0F9A, 0x332D, 0x9946, 0x549E, 0x79CD, 0x9E2E, 0xC4F2, 0xFEDA, 0xCF56, 0xF991, 0x11A7, 0x0EB7, 0x2A0F,
        0x24B1, 0x263E, 0x4665, 0x6600, 0x6C5E, 0x76AF, 0x868B, 0xB02B, 0xCCD5, 0xDD82, 0xFE47, 0x9471, 0xACE4, 0xA554,
        0x2123, 0x346F, 0x4415, 0x57B2, 0x9ECF, 0xF0CB, 0x08AE, 0x0929, 0x1875, 0x04FF, 0x0DF6, 0x1C5A, 0x1718, 0x2A28,
        0x328C, 0x38B2, 0x24E8, 0x2EEB, 0x2D3F, 0x4B64, 0x502E, 0x5013,
    )

    /** Cells across the marker: 4 data + 1 border each side. */
    const val GRID = 6

    data class Params(
        /** Shortest side accepted, pixels (shorter cannot be read nor give a usable scale). */
        val minSidePx: Float = 20f,
        /** Threshold below the local mean, grey levels. */
        val offset: Int = 7,
        /** Data bits corrected at most. */
        val maxBitErrors: Int = 1,
        /** Border cells allowed to read white (of 20). */
        val maxBorderErrors: Int = 2,
        /** Grey levels between white and black cells at least. */
        val minContrast: Float = 22f,
        /** Window sizes (pixels, odd) of the adaptive threshold; null = from the picture's size. */
        val windows: IntArray? = null,
    )

    /** The markers with ids in [ids] found in [img]; at most one per place (the best read when several windows found it). */
    fun detect(img: Luma, ids: Set<Int>, p: Params = Params()): List<MarkerDetection> {
        val codes = ids.filter { it in DICT_4X4_50.indices }.associateWith { DICT_4X4_50[it] }
        if (codes.isEmpty()) return emptyList()
        val m = min(img.w, img.h)
        val windows = p.windows ?: intArrayOf(odd(max(7, m / 64)), odd(max(15, m / 16)))
        val integral = integral(img)
        val cands = ArrayList<List<P2>>()
        for (win in windows) {
            val dark = threshold(img, integral, win, p.offset)
            for (q in quads(dark, img.w, img.h, p.minSidePx)) if (cands.none { same(it, q) }) cands += q
        }
        val found = ArrayList<MarkerDetection>()
        for (q in cands) {
            val det = read(img, q, codes, p) ?: continue
            val i = found.indexOfFirst { same(it.corners, det.corners) }
            if (i < 0) found += det
            else if (better(det, found[i])) found[i] = det
        }
        return found.sortedByDescending { it.sidePx }
    }

    private fun better(a: MarkerDetection, b: MarkerDetection) =
        a.bitErrors + a.borderErrors < b.bitErrors + b.borderErrors ||
            (a.bitErrors + a.borderErrors == b.bitErrors + b.borderErrors && a.cornerSigmaPx < b.cornerSigmaPx)

    private fun odd(v: Int) = if (v % 2 == 0) v + 1 else v

    /** Two quadrilaterals around the same place (centres within a fifth of the side, sizes alike). */
    private fun same(a: List<P2>, b: List<P2>): Boolean {
        val ca = centre(a); val cb = centre(b)
        val sa = perimeter(a) / 4; val sb = perimeter(b) / 4
        return hypot(ca.a - cb.a, ca.b - cb.b) < 0.2f * min(sa, sb) && max(sa, sb) < 1.3f * min(sa, sb)
    }

    private fun centre(q: List<P2>) = P2(q.sumOf { it.a.toDouble() }.toFloat() / q.size, q.sumOf { it.b.toDouble() }.toFloat() / q.size)
    private fun perimeter(q: List<P2>): Float { var s = 0f; for (i in q.indices) { val a = q[i]; val b = q[(i + 1) % q.size]; s += hypot(b.a - a.a, b.b - a.b) }; return s }

    // ------------------------------------------------------------------------------------------------ 1. threshold
    private fun integral(img: Luma): LongArray {
        val w = img.w; val h = img.h
        val s = LongArray((w + 1) * (h + 1))
        for (y in 0 until h) {
            var row = 0L
            for (x in 0 until w) { row += img.px[y * w + x].toInt() and 255; s[(y + 1) * (w + 1) + x + 1] = s[y * (w + 1) + x + 1] + row }
        }
        return s
    }

    /** Dark pixels: below the mean of the [win] x [win] window round them (clipped at the border) minus [offset]. */
    private fun threshold(img: Luma, s: LongArray, win: Int, offset: Int): BooleanArray {
        val w = img.w; val h = img.h; val r = win / 2; val sw = w + 1
        val out = BooleanArray(w * h)
        for (y in 0 until h) {
            val y0 = max(0, y - r); val y1 = min(h, y + r + 1)
            for (x in 0 until w) {
                val x0 = max(0, x - r); val x1 = min(w, x + r + 1)
                val sum = s[y1 * sw + x1] - s[y0 * sw + x1] - s[y1 * sw + x0] + s[y0 * sw + x0]
                val n = (y1 - y0) * (x1 - x0)
                out[y * w + x] = (img.px[y * w + x].toInt() and 255) * n < sum - offset.toLong() * n
            }
        }
        return out
    }

    // ------------------------------------------------------------------------------------------------ 2. quadrilaterals
    /** Connected dark regions (8-neighbours): label per pixel and each label's bounding box. */
    private fun quads(dark: BooleanArray, w: Int, h: Int, minSide: Float): List<List<P2>> {
        val label = IntArray(w * h)
        val parent = IntArray(w * h / 2 + 2)
        var next = 1
        fun find(a: Int): Int { var x = a; while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x] }; return x }
        fun union(a: Int, b: Int) { val ra = find(a); val rb = find(b); if (ra != rb) { if (ra < rb) parent[rb] = ra else parent[ra] = rb } }
        for (y in 0 until h) for (x in 0 until w) {
            val i = y * w + x
            if (!dark[i]) continue
            var l = 0
            // already labelled neighbours: W, NW, N, NE
            if (x > 0 && label[i - 1] != 0) l = label[i - 1]
            if (y > 0) {
                for (dx in -1..1) {
                    val xx = x + dx; if (xx < 0 || xx >= w) continue
                    val n = label[i - w + dx]
                    if (n != 0) { if (l == 0) l = n else if (n != l) union(l, n) }
                }
            }
            if (l == 0) {
                if (next >= parent.size) return emptyList()          // pathological noise: nothing sensible to find
                parent[next] = next; l = next++
            }
            label[i] = l
        }
        // bounding boxes and first pixel (raster order) per root
        val x0 = IntArray(next) { Int.MAX_VALUE }; val y0 = IntArray(next) { Int.MAX_VALUE }
        val x1 = IntArray(next) { -1 }; val y1 = IntArray(next) { -1 }; val first = IntArray(next) { -1 }
        for (i in 0 until w * h) {
            val l0 = label[i]; if (l0 == 0) continue
            val l = find(l0); label[i] = l
            val x = i % w; val y = i / w
            if (first[l] < 0) first[l] = i
            if (x < x0[l]) x0[l] = x; if (x > x1[l]) x1[l] = x
            if (y < y0[l]) y0[l] = y; if (y > y1[l]) y1[l] = y
        }
        val out = ArrayList<List<P2>>()
        for (l in 1 until next) {
            if (first[l] < 0) continue
            val bw = x1[l] - x0[l] + 1; val bh = y1[l] - y0[l] + 1
            if (max(bw, bh) < minSide || min(bw, bh) < 0.25f * minSide) continue
            if (bw > 0.97f * w && bh > 0.97f * h) continue
            if (x0[l] <= 1 || y0[l] <= 1 || x1[l] >= w - 2 || y1[l] >= h - 2) continue      // cut by the picture's edge
            val contour = trace(label, w, h, first[l], l, 8 * (bw + bh) + 64) ?: continue
            if (contour.size < 4 * minSide * 0.9f) continue
            quad(contour, minSide)?.let { out += it }
        }
        return out
    }

    private val DX = intArrayOf(1, 1, 0, -1, -1, -1, 0, 1)      // E SE S SW W NW N NE: clockwise on the screen
    private val DY = intArrayOf(0, 1, 1, 1, 0, -1, -1, -1)

    /** Outer boundary of region [l] from its first pixel [start] (Moore neighbour tracing, Jacob's stop), pixel centres. */
    private fun trace(label: IntArray, w: Int, h: Int, start: Int, l: Int, maxSteps: Int): List<P2>? {
        fun fg(x: Int, y: Int) = x in 0 until w && y in 0 until h && label[y * w + x] == l
        val sx = start % w; val sy = start / w
        val pts = ArrayList<P2>()
        var bx = sx; var by = sy
        var back = 4                                        // came from the west: the pixel to the left is background
        var secondX = -1; var secondY = -1
        var steps = 0
        pts += P2(sx + 0.5f, sy + 0.5f)
        while (steps++ < maxSteps) {
            var found = -1
            for (k in 1..8) {
                val d = (back + k) % 8
                if (fg(bx + DX[d], by + DY[d])) { found = d; break }
            }
            if (found < 0) return if (pts.size == 1) null else pts        // a lone pixel
            val nx = bx + DX[found]; val ny = by + DY[found]
            // the background pixel checked just before, seen from the new pixel, is where the next search starts
            val pd = (found + 7) % 8
            val cx = bx + DX[pd]; val cy = by + DY[pd]
            back = dirOf(cx - nx, cy - ny)
            if (bx == sx && by == sy && nx == secondX && ny == secondY && pts.size > 2) { pts.removeAt(pts.size - 1); return pts }
            if (secondX < 0) { secondX = nx; secondY = ny }
            bx = nx; by = ny
            pts += P2(bx + 0.5f, by + 0.5f)
        }
        return null
    }

    private fun dirOf(dx: Int, dy: Int): Int {
        for (d in 0 until 8) if (DX[d] == dx && DY[d] == dy) return d
        return 4
    }

    /** The contour as a convex quadrilateral in clockwise order (on the screen), or null. */
    private fun quad(c: List<P2>, minSide: Float): List<P2>? {
        val per = perimeter(c)
        for (rate in floatArrayOf(0.03f, 0.05f)) {
            val poly = simplifyClosed(c, rate * per)
            if (poly.size != 4) continue
            var q = poly
            // clockwise on the screen (y down): positive shoelace sum
            var s = 0f
            for (i in 0 until 4) { val a = q[i]; val b = q[(i + 1) % 4]; s += a.a * b.b - b.a * a.b }
            if (s < 0) q = q.reversed()
            // convex, sides long enough, corners apart
            var convex = true
            for (i in 0 until 4) {
                val a = q[i]; val b = q[(i + 1) % 4]; val e = q[(i + 2) % 4]
                val cr = (b.a - a.a) * (e.b - b.b) - (b.b - a.b) * (e.a - b.a)
                if (cr <= 0) { convex = false; break }
                if (hypot(b.a - a.a, b.b - a.b) < minSide * 0.8f) { convex = false; break }
            }
            if (!convex) continue
            // the region must fill its quadrilateral (an L shape or a ragged blob does not)
            if (abs(area(c)) < 0.8f * abs(area(q))) continue
            return q
        }
        return null
    }

    private fun area(q: List<P2>): Float { var s = 0f; for (i in q.indices) { val a = q[i]; val b = q[(i + 1) % q.size]; s += a.a * b.b - b.a * a.b }; return s / 2 }

    /** Douglas-Peucker on a closed curve: split at the two points farthest apart, simplify both halves. */
    private fun simplifyClosed(c: List<P2>, eps: Float): List<P2> {
        if (c.size < 4) return c
        var ia = 0; var best = -1f
        for (i in c.indices) { val d = d2(c[i], c[0]); if (d > best) { best = d; ia = i } }
        var ib = 0; best = -1f
        for (i in c.indices) { val d = d2(c[i], c[ia]); if (d > best) { best = d; ib = i } }
        val (i0, i1) = if (ia < ib) ia to ib else ib to ia
        val a = c.subList(i0, i1 + 1)
        val b = c.subList(i1, c.size) + c.subList(0, i0 + 1)
        val ra = dp(a, eps); val rb = dp(b, eps)
        return ra.dropLast(1) + rb.dropLast(1)
    }

    private fun d2(a: P2, b: P2) = (a.a - b.a) * (a.a - b.a) + (a.b - b.b) * (a.b - b.b)

    private fun dp(pts: List<P2>, eps: Float): List<P2> {
        if (pts.size < 3) return pts
        val a = pts.first(); val b = pts.last()
        val dx = b.a - a.a; val dy = b.b - a.b; val len = hypot(dx, dy)
        var idx = -1; var dmax = -1f
        for (i in 1 until pts.size - 1) {
            val p = pts[i]
            val d = if (len < 1e-6f) hypot(p.a - a.a, p.b - a.b) else abs(dy * (p.a - a.a) - dx * (p.b - a.b)) / len
            if (d > dmax) { dmax = d; idx = i }
        }
        if (dmax <= eps) return listOf(a, b)
        val l = dp(pts.subList(0, idx + 1), eps); val r = dp(pts.subList(idx, pts.size), eps)
        return l.dropLast(1) + r
    }

    // ------------------------------------------------------------------------------------------------ 3. corners
    private class Line(val mx: Float, val my: Float, val dx: Float, val dy: Float, val rms: Float, val n: Int)

    class Refined(val corners: List<P2>, val rms: Float, val sigma: Float)

    /**
     * Corners of the black square [q] (clockwise on the screen) moved onto its edges: per edge, the steepest dark-going
     * step across it at points along its middle 76 %, a line through them, corners where lines meet. Null when an edge
     * shows no step (not a printed square) or the corners jump.
     */
    fun refine(img: Luma, q: List<P2>, iterations: Int = 2): Refined? {
        var c = q
        var lines: List<Line>? = null
        repeat(iterations) {
            val side = perimeter(c) / 4
            val ls = (0 until 4).map { i -> fitEdge(img, c[i], c[(i + 1) % 4], side / GRID) ?: return null }
            val nc = (0 until 4).map { i -> meet(ls[(i + 3) % 4], ls[i]) ?: return null }
            for (i in 0 until 4) if (hypot(nc[i].a - c[i].a, nc[i].b - c[i].b) > 0.35f * side / GRID * GRID / 4) return null
            c = nc; lines = ls
        }
        val ls = lines ?: return null
        val rms = ls.map { it.rms }.average().toFloat()
        // a corner is a line's end: its error is about 2 rms / sqrt(n) of the worse of its two lines
        val sigma = (0 until 4).maxOf { i -> max(2 * ls[i].rms / sqrt(ls[i].n.toFloat()), 2 * ls[(i + 3) % 4].rms / sqrt(ls[(i + 3) % 4].n.toFloat())) }
        return Refined(c, rms, max(0.03f, sigma))
    }

    private fun fitEdge(img: Luma, a: P2, b: P2, cell: Float): Line? {
        val ex = b.a - a.a; val ey = b.b - a.b; val len = hypot(ex, ey)
        if (len < 4f) return null
        val dx = ex / len; val dy = ey / len
        val nx = -dy; val ny = dx                           // into the square for a clockwise (screen) order
        val reach = (0.3f * cell).coerceIn(1.5f, 10f)
        val step = 0.5f
        val ns = (2 * reach / step).toInt() + 1
        val prof = FloatArray(ns + 2)
        val count = (len * 0.76f).toInt().coerceIn(8, 120)
        val xs = ArrayList<Float>(count); val ys = ArrayList<Float>(count)
        for (k in 0 until count) {
            val t = len * (0.12f + 0.76f * k / (count - 1))
            val px = a.a + dx * t; val py = a.b + dy * t
            for (j in 0 until ns + 2) {
                val s = -reach - step + j * step
                prof[j] = img.at(px + nx * s, py + ny * s)
            }
            // gradient between neighbours; the steepest drop (white outside to black inside)
            var bi = -1; var bg = 0f
            for (j in 1..ns) { val g = prof[j + 1] - prof[j - 1]; if (g < bg) { bg = g; bi = j } }
            if (bi < 2 || bi > ns - 1 || -bg < 8f) continue
            val gm = prof[bi] - prof[bi - 2]; val gp = prof[bi + 2] - prof[bi]
            val den = gm - 2 * bg + gp
            val off = if (abs(den) > 1e-6f) (0.5f * (gm - gp) / den).coerceIn(-0.5f, 0.5f) else 0f
            val s = -reach - step + (bi + off) * step
            xs += px + nx * s; ys += py + ny * s
        }
        if (xs.size < 6) return null
        var line = fitLine(xs, ys) ?: return null
        // once more without the points far from the line (a dent, a speck, a corner of the data cells)
        val keepX = ArrayList<Float>(); val keepY = ArrayList<Float>()
        val tol = max(0.75f, 2.5f * line.rms)
        for (i in xs.indices) if (abs((xs[i] - line.mx) * -line.dy + (ys[i] - line.my) * line.dx) <= tol) { keepX += xs[i]; keepY += ys[i] }
        if (keepX.size >= 6 && keepX.size < xs.size) line = fitLine(keepX, keepY) ?: line
        return line
    }

    private fun fitLine(xs: List<Float>, ys: List<Float>): Line? {
        val n = xs.size; if (n < 2) return null
        var mx = 0.0; var my = 0.0
        for (i in 0 until n) { mx += xs[i]; my += ys[i] }
        mx /= n; my /= n
        var sxx = 0.0; var sxy = 0.0; var syy = 0.0
        for (i in 0 until n) { val x = xs[i] - mx; val y = ys[i] - my; sxx += x * x; sxy += x * y; syy += y * y }
        val th = 0.5 * atan2(2 * sxy, sxx - syy)
        val dx = cos(th); val dy = sin(th)
        var r2 = 0.0
        for (i in 0 until n) { val r = (xs[i] - mx) * -dy + (ys[i] - my) * dx; r2 += r * r }
        return Line(mx.toFloat(), my.toFloat(), dx.toFloat(), dy.toFloat(), sqrt(r2 / n).toFloat(), n)
    }

    private fun meet(a: Line, b: Line): P2? {
        val den = a.dx * b.dy - a.dy * b.dx
        if (abs(den) < 1e-4f) return null
        val t = ((b.mx - a.mx) * b.dy - (b.my - a.my) * b.dx) / den
        return P2(a.mx + a.dx * t, a.my + a.dy * t)
    }

    // ------------------------------------------------------------------------------------------------ 4. bits
    private fun read(img: Luma, q: List<P2>, codes: Map<Int, Int>, p: Params): MarkerDetection? {
        val r = refine(img, q) ?: return null
        val c = r.corners
        val hm = Homography.fromSquare(c, GRID.toDouble()) ?: return null
        val cells = FloatArray(GRID * GRID)
        for (i in 0 until GRID) for (j in 0 until GRID) {
            var s = 0f
            for (du in -1..1) for (dv in -1..1) {
                val pt = hm.map(j + 0.5 + du * 0.2, i + 0.5 + dv * 0.2)
                s += img.at(pt.a, pt.b)
            }
            cells[i * GRID + j] = s / 9
        }
        val t = otsu(cells)
        var black = 0.0; var nb = 0; var white = 0.0; var nw = 0
        for (v in cells) if (v > t) { white += v; nw++ } else { black += v; nb++ }
        if (nb == 0 || nw == 0) return null
        val contrast = (white / nw - black / nb).toFloat()
        if (contrast < p.minContrast) return null
        var border = 0
        for (i in 0 until GRID) for (j in 0 until GRID) {
            if (i == 0 || j == 0 || i == GRID - 1 || j == GRID - 1) if (cells[i * GRID + j] > t) border++
        }
        if (border > p.maxBorderErrors) return null
        var bits = 0
        for (i in 1..4) for (j in 1..4) bits = (bits shl 1) or (if (cells[i * GRID + j] > t) 1 else 0)
        var bestId = -1; var bestTurn = 0; var bestD = 99
        for ((id, code) in codes) {
            var rc = code
            for (k in 0 until 4) {
                val d = Integer.bitCount(bits xor rc)
                if (d < bestD) { bestD = d; bestId = id; bestTurn = k }
                rc = turn(rc)
            }
        }
        if (bestId < 0 || bestD > p.maxBitErrors) return null
        // the code turned k quarter-turns (counter-clockwise) is what the picture shows: the printed top-left corner
        // is the picture's corner (0 - k) mod 4 of the clockwise order
        val ordered = (0 until 4).map { m -> c[(m - bestTurn + 4) % 4] }
        val side = perimeter(ordered) / 4
        return MarkerDetection(bestId, ordered, side, bestD, border, contrast, r.rms, r.sigma)
    }

    /** A 4 x 4 code turned a quarter counter-clockwise (numpy's rot90): out[i][j] = in[j][3 - i]. */
    fun turn(code: Int): Int {
        var out = 0
        for (i in 0 until 4) for (j in 0 until 4) {
            val bit = (code shr (15 - (j * 4 + (3 - i)))) and 1
            out = out or (bit shl (15 - (i * 4 + j)))
        }
        return out
    }

    /** Otsu's threshold over a few values: the split with the largest between-class variance. */
    private fun otsu(v: FloatArray): Float {
        val s = v.sortedArray()
        var bestT = (s.first() + s.last()) / 2; var best = -1.0
        val total = s.sumOf { it.toDouble() }
        var left = 0.0
        for (i in 0 until s.size - 1) {
            left += s[i]
            val n0 = i + 1; val n1 = s.size - n0
            val m0 = left / n0; val m1 = (total - left) / n1
            val between = n0.toDouble() * n1 * (m0 - m1) * (m0 - m1)
            if (between > best) { best = between; bestT = (s[i] + s[i + 1]) / 2 }
        }
        return bestT
    }
}

/** A plane-to-picture homography (row-major 3 x 3). */
class Homography(val m: DoubleArray) {
    fun map(u: Double, v: Double): P2 {
        val w = m[6] * u + m[7] * v + m[8]
        return P2(((m[0] * u + m[1] * v + m[2]) / w).toFloat(), ((m[3] * u + m[4] * v + m[5]) / w).toFloat())
    }

    companion object {
        /** The homography taking the square (0,0) (s,0) (s,s) (0,s) to the four picture points [c]. */
        fun fromSquare(c: List<P2>, s: Double): Homography? =
            from(listOf(0.0 to 0.0, s to 0.0, s to s, 0.0 to s), c.map { it.a.toDouble() to it.b.toDouble() })

        /** From four point pairs (exact, 8 x 8 linear system), or null when degenerate. */
        fun from(src: List<Pair<Double, Double>>, dst: List<Pair<Double, Double>>): Homography? {
            val a = Array(8) { DoubleArray(9) }
            for (k in 0 until 4) {
                val (x, y) = src[k]; val (u, v) = dst[k]
                a[2 * k] = doubleArrayOf(x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y, u)
                a[2 * k + 1] = doubleArrayOf(0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y, v)
            }
            val h = solve(a) ?: return null
            return Homography(doubleArrayOf(h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1.0))
        }

        /** Gaussian elimination with partial pivoting on an n x (n+1) augmented matrix. */
        fun solve(a: Array<DoubleArray>): DoubleArray? {
            val n = a.size
            for (col in 0 until n) {
                var piv = col
                for (r in col + 1 until n) if (abs(a[r][col]) > abs(a[piv][col])) piv = r
                if (abs(a[piv][col]) < 1e-12) return null
                val t = a[col]; a[col] = a[piv]; a[piv] = t
                for (r in 0 until n) {
                    if (r == col) continue
                    val f = a[r][col] / a[col][col]
                    if (f == 0.0) continue
                    for (k in col..n) a[r][k] -= f * a[col][k]
                }
            }
            return DoubleArray(n) { a[it][n] / a[it][it] }
        }
    }
}
