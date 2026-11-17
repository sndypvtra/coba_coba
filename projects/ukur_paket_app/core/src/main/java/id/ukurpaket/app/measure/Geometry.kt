package id.ukurpaket.app.measure

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/*
 * The measuring core, free of Android so it runs in unit tests and, later, on a PC against
 * recorded scans. Input: 3D points in metres (world frame, from ARCore depth or feature points),
 * the floor plane, and the point the courier picked. Output: the smallest box that stands on the
 * floor and holds the parcel: length x width from its footprint, height from its top.
 */

data class V3(val x: Float, val y: Float, val z: Float) {
    operator fun plus(o: V3) = V3(x + o.x, y + o.y, z + o.z)
    operator fun minus(o: V3) = V3(x - o.x, y - o.y, z - o.z)
    operator fun times(s: Float) = V3(x * s, y * s, z * s)
    infix fun dot(o: V3) = x * o.x + y * o.y + z * o.z
    infix fun cross(o: V3) = V3(y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x)
    fun norm() = sqrt(this dot this)
    fun unit(): V3 { val n = norm(); return if (n < 1e-9f) this else this * (1f / n) }
}

data class P2(val a: Float, val b: Float)

/** The surface the parcel stands on: a point on it and its upward normal. */
class FloorPlane(val origin: V3, normal: V3) {
    val n: V3 = normal.unit()
    val u: V3
    val v: V3

    init {
        val helper = if (abs(n.x) < 0.9f) V3(1f, 0f, 0f) else V3(0f, 0f, 1f)
        u = (helper cross n).unit()
        v = (n cross u).unit()
    }

    fun height(p: V3) = (p - origin) dot n
    fun to2d(p: V3): P2 { val d = p - origin; return P2(d dot u, d dot v) }
    fun to3d(q: P2, h: Float = 0f): V3 = origin + u * q.a + v * q.b + n * h
}

/** Merges points from many frames into 1 cm voxels; a voxel seen in several frames is trusted more. */
class PointAccumulator(private val voxel: Float = 0.01f) {
    private class Cell(var sx: Float, var sy: Float, var sz: Float, var n: Int)
    private val cells = HashMap<Long, Cell>()
    var frames = 0
        private set

    fun add(x: Float, y: Float, z: Float) {
        val k = key(floor(x / voxel).toInt(), floor(y / voxel).toInt(), floor(z / voxel).toInt())
        val c = cells[k]
        if (c == null) cells[k] = Cell(x, y, z, 1) else { c.sx += x; c.sy += y; c.sz += z; c.n++ }
    }

    fun endFrame() { frames++ }
    fun clear() { cells.clear(); frames = 0 }
    val size get() = cells.size

    fun points(minCount: Int = 1): List<V3> =
        cells.values.filter { it.n >= minCount }.map { V3(it.sx / it.n, it.sy / it.n, it.sz / it.n) }

    private fun key(i: Int, j: Int, k: Int): Long =
        ((i.toLong() and 0x1FFFFF) shl 42) or ((j.toLong() and 0x1FFFFF) shl 21) or (k.toLong() and 0x1FFFFF)
}

/** The parcel's points, cut out of the scene. */
class Segment(
    val plane: FloorPlane,
    val pts2: List<P2>,
    val heights: FloatArray,
    val cells: Int,
    val cellSize: Float,
)

data class BoxResult(
    val lengthM: Float,
    val widthM: Float,
    val heightM: Float,
    /** Footprint corners on the floor, world frame, in order around the rectangle. */
    val floorCorners: List<V3>,
    /** The same corners lifted to the top of the parcel. */
    val topCorners: List<V3>,
    /** Outline of the parcel seen from above (convex hull), at its top height. */
    val outline: List<V3>,
    val points: Int,
    val fillRatio: Float,
    val topNoiseM: Float,
) {
    val volumeL get() = lengthM * widthM * heightM * 1000f
}

object BoxFitter {
    /**
     * Cuts the parcel out of [points]: everything standing on [plane] (between [minH] and [maxH]
     * above it) that is connected, on a grid of [cell] metres, to the courier's pick [seed].
     * Parcels further apart than about two cells end up in separate pieces.
     */
    fun segment(
        points: List<V3>, plane: FloorPlane, seed: V3,
        cell: Float = 0.015f, minH: Float = 0.012f, maxH: Float = 1.6f, radius: Float = 1.2f, bridge: Int = 1,
        minPerCell: Int = 1,
    ): Segment? {
        val s2 = plane.to2d(seed)
        val grid = HashMap<Long, MutableList<Int>>()
        val p2 = ArrayList<P2>(points.size)
        val hs = ArrayList<Float>(points.size)
        for (p in points) {
            val h = plane.height(p)
            if (h < minH || h > maxH) continue
            val q = plane.to2d(p)
            if (hypot(q.a - s2.a, q.b - s2.b) > radius) continue
            val idx = p2.size
            p2.add(q); hs.add(h)
            grid.getOrPut(ck(cellOf(q.a, cell), cellOf(q.b, cell))) { ArrayList() }.add(idx)
        }
        // a cell needs [minPerCell] points to count: lone noisy points around the parcel do not grow its footprint
        if (minPerCell > 1) grid.entries.removeIf { it.value.size < minPerCell }
        if (grid.isEmpty()) return null

        // start from the occupied cell nearest the pick (it may land in a hole of the depth map)
        val si = cellOf(s2.a, cell); val sj = cellOf(s2.b, cell)
        var start: Long? = null
        var best = Int.MAX_VALUE
        val reach = max(2, (0.12f / cell).toInt())
        for (di in -reach..reach) for (dj in -reach..reach) {
            val k = ck(si + di, sj + dj)
            if (grid.containsKey(k) && di * di + dj * dj < best) { best = di * di + dj * dj; start = k }
        }
        val s = start ?: return null

        val seen = HashSet<Long>()
        val queue = ArrayDeque<Long>()
        seen.add(s); queue.add(s)
        while (queue.isNotEmpty()) {
            val k = queue.removeFirst()
            val i = (k shr 32).toInt(); val j = k.toInt()
            for (di in -1 - bridge..1 + bridge) for (dj in -1 - bridge..1 + bridge) {
                val n = ck(i + di, j + dj)
                if (n !in seen && grid.containsKey(n)) { seen.add(n); queue.add(n) }
            }
        }
        // drop speckles: a cell with fewer than 3 occupied neighbours is noise, or a one-cell sliver at the edge
        val kept = seen.filter { k ->
            val i = (k shr 32).toInt(); val j = k.toInt()
            var n = 0
            for (di in -1..1) for (dj in -1..1) if ((di != 0 || dj != 0) && ck(i + di, j + dj) in seen) n++
            n >= 3
        }.ifEmpty { seen.toList() }
        val idx = kept.flatMap { grid[it]!! }
        return Segment(plane, idx.map { p2[it] }, FloatArray(idx.size) { hs[idx[it]] }, kept.size, cell)
    }

    /**
     * Every separate thing standing on [plane] within [radius] of [centre]: the "other parcels" drawn around
     * the one being picked. Coarser than [segment]; for display and tap targets only, never for the size.
     */
    fun clusters(
        points: List<V3>, plane: FloorPlane, centre: V3,
        cell: Float = 0.03f, minH: Float = 0.03f, maxH: Float = 1.6f, radius: Float = 1.8f, minCells: Int = 6,
    ): List<BoxResult> {
        val c2 = plane.to2d(centre)
        val grid = HashMap<Long, MutableList<Int>>()
        val p2 = ArrayList<P2>(); val hs = ArrayList<Float>()
        for (p in points) {
            val h = plane.height(p)
            if (h < minH || h > maxH) continue
            val q = plane.to2d(p)
            if (hypot(q.a - c2.a, q.b - c2.b) > radius) continue
            grid.getOrPut(ck(cellOf(q.a, cell), cellOf(q.b, cell))) { ArrayList() }.add(p2.size)
            p2.add(q); hs.add(h)
        }
        grid.entries.removeIf { it.value.size < 2 }
        val seen = HashSet<Long>()
        val out = ArrayList<BoxResult>()
        for (start in grid.keys) {
            if (start in seen) continue
            val comp = ArrayList<Long>()
            val queue = ArrayDeque<Long>()
            seen.add(start); queue.add(start)
            while (queue.isNotEmpty()) {
                val k = queue.removeFirst(); comp.add(k)
                val i = (k shr 32).toInt(); val j = k.toInt()
                for (di in -1..1) for (dj in -1..1) {
                    val n = ck(i + di, j + dj)
                    if (n !in seen && grid.containsKey(n)) { seen.add(n); queue.add(n) }
                }
            }
            if (comp.size < minCells) continue
            val idx = comp.flatMap { grid[it]!! }
            fit(Segment(plane, idx.map { p2[it] }, FloatArray(idx.size) { hs[idx[it]] }, comp.size, cell))
                ?.takeIf { it.lengthM in 0.08f..1.6f && it.widthM >= 0.05f }
                ?.let { out.add(it) }
        }
        return out
    }

    fun fit(seg: Segment): BoxResult? {
        if (seg.pts2.size < 12) return null
        val hull = convexHull(seg.pts2)
        if (hull.size < 3) return null
        val rect = trimmed(minAreaRect(hull), seg.pts2)
        val sorted = seg.heights.sortedArray()
        val h = percentile(sorted, 0.95f)
        val top = sorted.filter { it >= percentile(sorted, 0.80f) }
        val mean = top.average().toFloat()
        val noise = sqrt(top.map { (it - mean) * (it - mean) }.average().toFloat())
        val area = rect.l * rect.w
        val fill = if (area > 0f) min(1f, seg.cells * seg.cellSize * seg.cellSize / area) else 0f
        val floor = rect.corners.map { seg.plane.to3d(it, 0f) }
        val topC = rect.corners.map { seg.plane.to3d(it, h) }
        return BoxResult(
            lengthM = max(rect.l, rect.w), widthM = min(rect.l, rect.w), heightM = h,
            floorCorners = floor, topCorners = topC, outline = hull.map { seg.plane.to3d(it, h) },
            points = seg.pts2.size, fillRatio = fill, topNoiseM = noise,
        )
    }

    /**
     * The rectangle's orientation comes from the hull; its extents are re-measured along those axes
     * at the 0,5 / 99,5 percentiles, so a few stray points cannot widen the box.
     */
    private fun trimmed(r: Rect2, pts: List<P2>): Rect2 {
        val o = r.corners[0]
        val ax = P2(r.corners[1].a - o.a, r.corners[1].b - o.b).let { val n = hypot(it.a, it.b); if (n < 1e-6f) return r; P2(it.a / n, it.b / n) }
        val ay = P2(-ax.b, ax.a)
        val us = FloatArray(pts.size) { (pts[it].a - o.a) * ax.a + (pts[it].b - o.b) * ax.b }.apply { sort() }
        val vs = FloatArray(pts.size) { (pts[it].a - o.a) * ay.a + (pts[it].b - o.b) * ay.b }.apply { sort() }
        val u0 = percentile(us, 0.005f); val u1 = percentile(us, 0.995f)
        val v0 = percentile(vs, 0.005f); val v1 = percentile(vs, 0.995f)
        fun at(u: Float, v: Float) = P2(o.a + ax.a * u + ay.a * v, o.b + ax.b * u + ay.b * v)
        return Rect2(u1 - u0, v1 - v0, listOf(at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1)))
    }

    /** 0-100. Many points, many frames, a footprint that fills its box and a flat top score high. */
    fun confidence(r: BoxResult, frames: Int, depth: Boolean): Int {
        val pts = min(1f, r.points / (if (depth) 900f else 120f))
        val frm = min(1f, frames / 16f)
        val fill = min(1f, r.fillRatio / 0.55f)
        val flat = (1f - min(1f, max(0f, r.topNoiseM - 0.006f) / 0.03f))
        var s = 100f * (0.30f * pts + 0.25f * frm + 0.20f * fill + 0.25f * flat)
        if (!depth) s = min(s, 74f)          // feature points only: never "accurate" on their own
        return s.toInt().coerceIn(0, 100)
    }

    private fun cellOf(x: Float, c: Float) = floor(x / c).toInt()
    private fun ck(i: Int, j: Int): Long = (i.toLong() shl 32) or (j.toLong() and 0xFFFFFFFFL)
    private fun percentile(sorted: FloatArray, q: Float): Float =
        sorted[((sorted.size - 1) * q).toInt().coerceIn(0, sorted.size - 1)]
}

/** Andrew's monotone chain. */
fun convexHull(points: List<P2>): List<P2> {
    val p = points.distinct().sortedWith(compareBy({ it.a }, { it.b }))
    if (p.size < 3) return p
    fun cross(o: P2, a: P2, b: P2) = (a.a - o.a) * (b.b - o.b) - (a.b - o.b) * (b.a - o.a)
    val lower = ArrayList<P2>()
    for (q in p) { while (lower.size >= 2 && cross(lower[lower.size - 2], lower.last(), q) <= 0) lower.removeAt(lower.size - 1); lower.add(q) }
    val upper = ArrayList<P2>()
    for (q in p.asReversed()) { while (upper.size >= 2 && cross(upper[upper.size - 2], upper.last(), q) <= 0) upper.removeAt(upper.size - 1); upper.add(q) }
    lower.removeAt(lower.size - 1); upper.removeAt(upper.size - 1)
    return lower + upper
}

class Rect2(val l: Float, val w: Float, val corners: List<P2>)

/** Smallest rectangle around a convex polygon: one side always lies on a hull edge. */
fun minAreaRect(hull: List<P2>): Rect2 {
    var best: Rect2? = null
    var bestArea = Float.MAX_VALUE
    for (i in hull.indices) {
        val a = hull[i]; val b = hull[(i + 1) % hull.size]
        val ang = atan2(b.b - a.b, b.a - a.a)
        val c = cos(ang); val s = sin(ang)
        var minX = Float.MAX_VALUE; var maxX = -Float.MAX_VALUE; var minY = Float.MAX_VALUE; var maxY = -Float.MAX_VALUE
        for (q in hull) {
            val x = q.a * c + q.b * s; val y = -q.a * s + q.b * c
            minX = min(minX, x); maxX = max(maxX, x); minY = min(minY, y); maxY = max(maxY, y)
        }
        val area = (maxX - minX) * (maxY - minY)
        if (area < bestArea) {
            bestArea = area
            fun back(x: Float, y: Float) = P2(x * c - y * s, x * s + y * c)
            best = Rect2(maxX - minX, maxY - minY,
                listOf(back(minX, minY), back(maxX, minY), back(maxX, maxY), back(minX, maxY)))
        }
    }
    return best!!
}

/** Point in a convex polygon (either winding). */
fun inside(poly: List<P2>, x: Float, y: Float): Boolean {
    var pos = false; var neg = false
    for (i in poly.indices) {
        val a = poly[i]; val b = poly[(i + 1) % poly.size]
        val c = (b.a - a.a) * (y - a.b) - (b.b - a.b) * (x - a.a)
        if (c > 0) pos = true else if (c < 0) neg = true
        if (pos && neg) return false
    }
    return true
}
