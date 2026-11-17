package id.ukurpaket.app.marker

import id.ukurpaket.app.measure.V3
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.Intrinsics
import kotlinx.serialization.Serializable
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.sqrt

/**
 * A printed marker of known size seen in a photo, in the pixels of the picture it is measured on (the engine's
 * 480-wide picture: the detector's full-resolution corners scaled down, sub-pixel precision kept).
 */
@Serializable
data class MarkerObservation(
    val id: Int,
    /** x, y of the printed top-left, top-right, bottom-right, bottom-left corners. */
    val corners: List<Float>,
    /** The black square's side on the sheet, metres (as printed and checked with a ruler). */
    val sideM: Double,
    /** Standard error of a corner, pixels, from the edge fit. */
    val cornerSigmaPx: Double = 0.2,
) {
    fun x(i: Int) = corners[2 * i]
    fun y(i: Int) = corners[2 * i + 1]

    /** The same marker in a picture [s] times as large. */
    fun scaled(s: Float) = copy(corners = corners.map { it * s }, cornerSigmaPx = cornerSigmaPx * s)

    companion object {
        fun of(d: MarkerDetection, sideM: Double, scale: Float = 1f) =
            MarkerObservation(d.id, d.flat().map { it * scale }, sideM, (d.cornerSigmaPx * scale).toDouble())
    }
}

/** What one marker says about the camera's height above the floor it lies on. */
@Serializable
data class MarkerFit(
    val id: Int,
    /** Camera height above the marker's plane, metres. */
    val heightM: Double,
    /** Relative standard error of [heightM]. */
    val sigma: Double,
    /** RMS relative misfit of the marker's sides and diagonals on the floor at [heightM]: 0 for a flat, true square. */
    val residual: Double,
    /** Angle between the marker's plane (from its picture alone) and the accelerometer's level, degrees. */
    val tiltDeg: Double,
    /** Mean side in the picture, pixels. */
    val sidePx: Double,
    /** Usable for the measurement; otherwise [reason] says why not (in the courier's words). */
    val usable: Boolean,
    val reason: String? = null,
) {
    /** The same fit, set aside for [why]. */
    fun reject(why: String) = copy(usable = false, reason = why)
}

/**
 * The camera height from a printed marker lying on the floor (or table) next to the parcel.
 *
 * The photo engine models the floor as the level plane `up . X = -h` below the camera, `up` from the accelerometer;
 * every size it measures scales with h. A marker on that plane fixes h directly: each corner's ray meets the plane at a
 * point that, for h = 1, lies at distance d from the others; the true distances D are the side s (four sides) and s√2
 * (two diagonals), so h = Σ dD / Σ d² (least squares). The misfit of the six distances after scaling is the check that
 * the marker is flat and level and was found right; the plane given by the marker's picture alone (its homography
 * through the lens) must agree with the accelerometer's level as well. The same model as the box fit, so the scale it
 * gives is exactly the one the box needs.
 */
object MarkerScale {
    /** Shortest side in the measured picture (480 wide), pixels: below, a corner's half pixel is a large part of the side. */
    const val MIN_SIDE_PX = 11.0

    /** Largest misfit of the sides and diagonals accepted (bent sheet, tilted floor, a corner found wrong). */
    const val MAX_RESIDUAL = 0.05

    /** Largest angle between the marker's own plane and the level accepted, degrees. */
    const val MAX_TILT_DEG = 15.0

    /** Floor on the relative error: the lens's focal length and the accelerometer's level are not perfect either. */
    const val SIGMA_FLOOR = 0.012

    /** The marker's plane and the floor round the parcel, as the depth model sees both: further apart than this, not the same plane. */
    const val MAX_PLANE_RATIO = 1.22

    fun fit(o: MarkerObservation, k: Intrinsics, up: V3): MarkerFit {
        val sidePx = (0 until 4).map { i -> val j = (i + 1) % 4; kotlin.math.hypot(o.x(j) - o.x(i), o.y(j) - o.y(i)).toDouble() }.average()
        val bad = MarkerFit(o.id, 0.0, 1.0, 1.0, 90.0, sidePx, false)
        // each corner on the level plane one metre below the camera
        val p = (0 until 4).map { i ->
            val r = k.ray(o.x(i), o.y(i)); val den = -(r dot up)
            if (den < 0.02f) return bad.reject("Marker terlalu jauh atau di atas garis cakrawala: foto lebih dari atas")
            r * (1f / den)
        }
        val pairs = listOf(0 to 1, 1 to 2, 2 to 3, 3 to 0, 0 to 2, 1 to 3)
        val s = o.sideM
        val dTrue = pairs.map { (a, b) -> if (abs(a - b) == 2) s * sqrt(2.0) else s }
        val dUnit = pairs.map { (a, b) -> (p[a] - p[b]).norm().toDouble() }
        val h = dUnit.indices.sumOf { dUnit[it] * dTrue[it] } / dUnit.sumOf { it * it }
        val residual = sqrt(dUnit.indices.sumOf { val e = (h * dUnit[it] - dTrue[it]) / dTrue[it]; e * e } / dUnit.size)
        val tilt = tiltDeg(o, k, up)
        val sigma = sqrt(2 * (o.cornerSigmaPx / sidePx).let { it * it } + residual * residual + SIGMA_FLOOR * SIGMA_FLOOR)
        val fit = MarkerFit(o.id, h, sigma, residual, tilt, sidePx, true)
        return when {
            sidePx < MIN_SIDE_PX -> fit.reject("Marker terlalu kecil di foto: dekatkan HP atau pakai marker A3")
            residual > MAX_RESIDUAL -> fit.reject("Marker tidak terbaca rata (terlipat, melengkung, atau tertutup sebagian)")
            tilt > MAX_TILT_DEG -> fit.reject("Marker miring terhadap lantai: taruh rata di lantai atau meja")
            else -> fit
        }
    }

    /**
     * Angle between the marker's plane as its own picture gives it (the homography from the square to the normalised
     * picture: its first two columns are the plane's axes) and the level from the accelerometer.
     */
    fun tiltDeg(o: MarkerObservation, k: Intrinsics, up: V3): Double {
        val s = o.sideM
        val src = listOf(0.0 to 0.0, s to 0.0, s to s, 0.0 to s)
        val dst = (0 until 4).map { i -> ((o.x(i) - k.cx) / k.fx).toDouble() to ((o.y(i) - k.cy) / k.fy).toDouble() }
        val hm = Homography.from(src, dst) ?: return 90.0
        val m = hm.m
        val h1 = doubleArrayOf(m[0], m[3], m[6]); val h2 = doubleArrayOf(m[1], m[4], m[7])
        val n1 = sqrt(h1.sumOf { it * it }); val n2 = sqrt(h2.sumOf { it * it })
        if (n1 < 1e-12 || n2 < 1e-12) return 90.0
        val r1 = h1.map { it / n1 }; val r2 = h2.map { it / n2 }
        val n = doubleArrayOf(r1[1] * r2[2] - r1[2] * r2[1], r1[2] * r2[0] - r1[0] * r2[2], r1[0] * r2[1] - r1[1] * r2[0])
        val nn = sqrt(n.sumOf { it * it }); if (nn < 1e-12) return 90.0
        val c = abs((n[0] * up.x + n[1] * up.y + n[2] * up.z) / nn / up.norm())
        return Math.toDegrees(acos(c.coerceIn(0.0, 1.0)))
    }

    /**
     * How high the camera stands above the marker's plane compared with the floor round the parcel, both read from the
     * same depth map (a ratio, so the depth model's scale cancels): about 1 when the marker lies on the parcel's floor;
     * well above 1 for a marker on the floor under a parcel on a table, below 1 for one on top of the parcel. Null when
     * the depth map says nothing there.
     */
    fun planeRatio(o: MarkerObservation, depth: DepthMap, k: Intrinsics, up: V3, floorM: Float): Double? {
        if (floorM <= 0f) return null
        val hm = Homography.fromSquare((0 until 4).map { id.ukurpaket.app.measure.P2(o.x(it), o.y(it)) }, 1.0) ?: return null
        val hs = ArrayList<Double>()
        for (i in 1..5) for (j in 1..5) {
            val pt = hm.map(i / 6.0, j / 6.0)
            if (pt.a < 0 || pt.b < 0 || pt.a >= k.w || pt.b >= k.h) continue
            val r = k.ray(pt.a, pt.b); val den = -(r dot up)
            if (den <= 0.02f) continue
            val z = depth.at(pt.a / k.w, pt.b / k.h)
            if (z in 0.05f..30f) hs += (den * z).toDouble()
        }
        if (hs.size < 5) return null
        hs.sort()
        return hs[hs.size / 2] / floorM
    }

    /** Several usable markers in one photo: their heights combined in log space by their errors (they are scale errors). */
    fun combine(fits: List<MarkerFit>): MarkerFit? {
        val ok = fits.filter { it.usable }
        if (ok.isEmpty()) return null
        if (ok.size == 1) return ok[0]
        val wsum = ok.sumOf { 1 / (it.sigma * it.sigma) }
        val m = ok.sumOf { ln(it.heightM) / (it.sigma * it.sigma) } / wsum
        val best = ok.maxBy { it.sidePx }
        return best.copy(heightM = exp(m), sigma = max(SIGMA_FLOOR, sqrt(1 / wsum)))
    }
}
