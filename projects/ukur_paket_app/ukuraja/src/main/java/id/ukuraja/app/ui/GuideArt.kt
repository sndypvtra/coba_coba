package id.ukuraja.app.ui

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukurpaket.app.marker.Aruco
import id.ukurpaket.app.marker.MarkerSheet
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

// ------------------------------------------------------------------ animation helpers
/**
 * A clock running 0 → 1 every [periodMs], forever. In screenshot tests (LocalStill) it stands at [still]: the frame
 * that says the most, with nothing left moving for the renderer to wait on.
 */
@Composable
fun loopClock(periodMs: Int, still: Float = 1f): Float {
    if (LocalStill.current) return still
    val tr = rememberInfiniteTransition(label = "loop")
    val t by tr.animateFloat(0f, 1f, infiniteRepeatable(tween(periodMs, easing = LinearEasing), RepeatMode.Restart), label = "t")
    return t
}

/** 0 before [a], 1 after [b], eased in between: one movement inside a loop. */
fun phase(t: Float, a: Float, b: Float): Float = FastOutSlowInEasing.transform(((t - a) / (b - a)).coerceIn(0f, 1f))

// ------------------------------------------------------------------ colours of the drawings
object Art {
    val floor = Color(0xFFE6EAEF)
    val floorLine = Color(0xFFD6DCE3)
    val boxTop = Color(0xFFEACBA2)
    val boxLeft = Color(0xFFD8AF7E)
    val boxRight = Color(0xFFC59864)
    val tape = Color(0xFFF5E6CC)
    val edge = Color(0x33000000)
    val paper = Color.White
    val measured = Color(0xFF22C55E)
    val mask = Color(0x66ED0677)
    val wood = Color(0xFFB98A5E)
    val woodDark = Color(0xFF9C7048)
    val sky = Color(0xFFF4F6F9)
}

// ------------------------------------------------------------------ isometric scene
/** Floor x, y and height z (in units of 10 cm) to the picture: the classic 30° isometric view, scaled by [s]. */
class Iso(val cx: Float, val cy: Float, val s: Float) {
    fun p(x: Float, y: Float, z: Float = 0f) = Offset(cx + (x - y) * 0.866f * s, cy + (x + y) * 0.5f * s - z * s)

    companion object {
        /** The view that fits the world box [x0, x1] × [y0, y1] × [0, z1] into [size] with a margin. */
        fun fit(size: Size, x0: Float, x1: Float, y0: Float, y1: Float, z1: Float, margin: Float = 0.06f): Iso {
            val pts = listOf(x0 to y0, x1 to y0, x1 to y1, x0 to y1)
            val sx = pts.map { (x, y) -> (x - y) * 0.866f }
            val syLo = pts.map { (x, y) -> (x + y) * 0.5f }
            val w = sx.max() - sx.min(); val h = syLo.max() - (syLo.min() - z1)
            val s = min(size.width * (1 - 2 * margin) / w, size.height * (1 - 2 * margin) / h)
            val cx = size.width / 2 - (sx.max() + sx.min()) / 2 * s
            val cy = size.height / 2 - (syLo.max() + syLo.min() - z1) / 2 * s
            return Iso(cx, cy, s)
        }
    }
}

fun DrawScope.fillPoly(pts: List<Offset>, color: Color) {
    if (pts.size < 3) return
    drawPath(Path().apply { moveTo(pts[0].x, pts[0].y); for (i in 1 until pts.size) lineTo(pts[i].x, pts[i].y); close() }, color)
}

fun DrawScope.strokePoly(pts: List<Offset>, color: Color, width: Float, closed: Boolean = true) {
    if (pts.size < 2) return
    drawPath(Path().apply { moveTo(pts[0].x, pts[0].y); for (i in 1 until pts.size) lineTo(pts[i].x, pts[i].y); if (closed) close() },
        color, style = Stroke(width, join = StrokeJoin.Round, cap = StrokeCap.Round))
}

/** A tiled floor over [x0, x1] × [y0, y1]. */
fun DrawScope.isoFloor(iso: Iso, x0: Float, x1: Float, y0: Float, y1: Float) {
    fillPoly(listOf(iso.p(x0, y0), iso.p(x1, y0), iso.p(x1, y1), iso.p(x0, y1)), Art.floor)
    var x = x0; while (x <= x1 + 1e-3f) { drawLine(Art.floorLine, iso.p(x, y0), iso.p(x, y1), 1.dp.toPx()); x += 3f }
    var y = y0; while (y <= y1 + 1e-3f) { drawLine(Art.floorLine, iso.p(x0, y), iso.p(x1, y), 1.dp.toPx()); y += 3f }
}

/** A carton at floor position ([x], [y]), [w] × [d] × [h], standing on height [z0] (a table), with its tape and soft shadow. */
fun DrawScope.isoBox(iso: Iso, x: Float, y: Float, w: Float, d: Float, h: Float, z0: Float = 0f, alpha: Float = 1f) {
    // shadow on what it stands on, towards the viewer's right
    fillPoly(listOf(iso.p(x + 0.25f, y + 0.25f, z0), iso.p(x + w + 0.45f, y + 0.25f, z0), iso.p(x + w + 0.45f, y + d + 0.35f, z0), iso.p(x + 0.25f, y + d + 0.35f, z0)),
        Color.Black.copy(alpha = 0.10f * alpha))
    val top = z0 + h
    val left = listOf(iso.p(x, y + d, z0), iso.p(x + w, y + d, z0), iso.p(x + w, y + d, top), iso.p(x, y + d, top))
    val right = listOf(iso.p(x + w, y, z0), iso.p(x + w, y + d, z0), iso.p(x + w, y + d, top), iso.p(x + w, y, top))
    val topF = listOf(iso.p(x, y, top), iso.p(x + w, y, top), iso.p(x + w, y + d, top), iso.p(x, y + d, top))
    fillPoly(left, Art.boxLeft.copy(alpha = alpha)); fillPoly(right, Art.boxRight.copy(alpha = alpha)); fillPoly(topF, Art.boxTop.copy(alpha = alpha))
    // tape along the top and down the right side
    val m = d / 2; val tw = 0.22f
    fillPoly(listOf(iso.p(x, y + m - tw, top), iso.p(x + w, y + m - tw, top), iso.p(x + w, y + m + tw, top), iso.p(x, y + m + tw, top)), Art.tape.copy(alpha = alpha))
    fillPoly(listOf(iso.p(x + w, y + m - tw, top), iso.p(x + w, y + m + tw, top), iso.p(x + w, y + m + tw, top - h * 0.35f), iso.p(x + w, y + m - tw, top - h * 0.35f)),
        Art.tape.copy(alpha = alpha * 0.9f))
    for (f in listOf(left, right, topF)) strokePoly(f, Art.edge.copy(alpha = 0.2f * alpha), 1.dp.toPx())
}

/** The faces of the carton coloured as the app's cut-out (magenta), with opacity [a]. */
fun DrawScope.isoBoxMask(iso: Iso, x: Float, y: Float, w: Float, d: Float, h: Float, a: Float) {
    if (a <= 0f) return
    val c = Art.mask.copy(alpha = Art.mask.alpha * a)
    fillPoly(listOf(iso.p(x, y + d), iso.p(x + w, y + d), iso.p(x + w, y + d, h), iso.p(x, y + d, h)), c)
    fillPoly(listOf(iso.p(x + w, y), iso.p(x + w, y + d), iso.p(x + w, y + d, h), iso.p(x + w, y, h)), c)
    fillPoly(listOf(iso.p(x, y, h), iso.p(x + w, y, h), iso.p(x + w, y + d, h), iso.p(x, y + d, h)), c)
}

/** The measured box's 12 edges in green, drawn edge by edge up to [progress] (0..1), as the app draws its result. */
fun DrawScope.isoBoxEdges(iso: Iso, x: Float, y: Float, w: Float, d: Float, h: Float, progress: Float, width: Float) {
    if (progress <= 0f) return
    val c = listOf(iso.p(x, y), iso.p(x + w, y), iso.p(x + w, y + d), iso.p(x, y + d), iso.p(x, y, h), iso.p(x + w, y, h), iso.p(x + w, y + d, h), iso.p(x, y + d, h))
    val edges = listOf(3 to 2, 2 to 1, 2 to 6, 3 to 7, 1 to 5, 7 to 6, 6 to 5, 4 to 5, 4 to 7, 0 to 1, 0 to 3, 0 to 4)
    val n = progress * edges.size
    for ((i, e) in edges.withIndex()) {
        val f = (n - i).coerceIn(0f, 1f); if (f <= 0f) break
        val a = c[e.first]; val b = c[e.second]
        drawLine(Art.measured, a, Offset(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f), width, cap = StrokeCap.Round)
    }
}

/**
 * The printed sheet (A4: 21 × 29,7 cm, the black square 16 cm) lying at ([x], [y]); [fold] lifts its far half (a bent
 * sheet), [z] raises all of it (on top of a parcel). The square shows the real id-1 pattern. [glow]: the app's yellow
 * outline round the square once it has found it.
 */
fun DrawScope.isoSheet(iso: Iso, x: Float, y: Float, z: Float = 0f, fold: Float = 0f, glow: Float = 0f, alpha: Float = 1f) {
    val w = 2.1f; val d = 2.97f
    fun at(u: Float, v: Float): Offset { val lift = if (v > d / 2) fold * (v - d / 2) / (d / 2) else 0f; return iso.p(x + u, y + v, z + lift) }
    fun quad(u0: Float, v0: Float, u1: Float, v1: Float) = listOf(at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1))
    if (z == 0f && fold == 0f) fillPoly(quad(0.08f, 0.1f, w + 0.12f, d + 0.12f), Color.Black.copy(alpha = 0.06f * alpha))
    if (fold > 0f) { fillPoly(quad(0f, 0f, w, d / 2), Art.paper.copy(alpha = alpha)); fillPoly(quad(0f, d / 2, w, d), Color(0xFFF1F2F4).copy(alpha = alpha)) }
    else fillPoly(quad(0f, 0f, w, d), Art.paper.copy(alpha = alpha))
    strokePoly(quad(0f, 0f, w, d), Color(0x22000000).copy(alpha = 0.13f * alpha), 1.dp.toPx())
    val s = 1.6f; val u0 = (w - s) / 2; val v0 = 0.3f; val cell = s / Aruco.GRID
    fillPoly(quad(u0, v0, u0 + s, v0 + s), C.ink.copy(alpha = alpha))
    val code = Aruco.DICT_4X4_50[MarkerSheet.A4.id]
    for (i in 0 until 4) for (j in 0 until 4) if ((code shr (15 - (i * 4 + j))) and 1 == 1)
        fillPoly(quad(u0 + (j + 1) * cell, v0 + (i + 1) * cell, u0 + (j + 2) * cell + 0.01f, v0 + (i + 2) * cell + 0.01f), Art.paper.copy(alpha = alpha))
    // a few lines of text under the square, as on the printed sheet
    for (k in 0..2) fillPoly(quad(u0, v0 + s + 0.25f + k * 0.22f, u0 + s * (if (k == 2) 0.55f else 0.9f), v0 + s + 0.32f + k * 0.22f), Color(0xFFCBD2DA).copy(alpha = alpha))
    if (glow > 0f) strokePoly(quad(u0 - 0.04f, v0 - 0.04f, u0 + s + 0.04f, v0 + s + 0.04f), C.yellow.copy(alpha = glow * alpha), 3.dp.toPx())
}

/** A round badge: a green tick or a red cross. */
fun DrawScope.badge(c: Offset, r: Float, ok: Boolean, a: Float = 1f) {
    if (a <= 0f) return
    drawCircle(Color.White.copy(alpha = a), r * 1.12f, c)
    drawCircle((if (ok) C.green else C.red).copy(alpha = a), r, c)
    val w = r * 0.22f
    if (ok) {
        drawLine(Color.White.copy(alpha = a), Offset(c.x - r * 0.45f, c.y + r * 0.02f), Offset(c.x - r * 0.12f, c.y + r * 0.35f), w, cap = StrokeCap.Round)
        drawLine(Color.White.copy(alpha = a), Offset(c.x - r * 0.12f, c.y + r * 0.35f), Offset(c.x + r * 0.48f, c.y - r * 0.3f), w, cap = StrokeCap.Round)
    } else {
        drawLine(Color.White.copy(alpha = a), Offset(c.x - r * 0.38f, c.y - r * 0.38f), Offset(c.x + r * 0.38f, c.y + r * 0.38f), w, cap = StrokeCap.Round)
        drawLine(Color.White.copy(alpha = a), Offset(c.x + r * 0.38f, c.y - r * 0.38f), Offset(c.x - r * 0.38f, c.y + r * 0.38f), w, cap = StrokeCap.Round)
    }
}

/** A label in a rounded pill centred at [c]. */
fun DrawScope.pill(tm: TextMeasurer, text: String, c: Offset, bg: Color, fg: Color, a: Float = 1f, size: Float = 12f) {
    if (a <= 0f) return
    val layout = tm.measure(text, TextStyle(fontFamily = Inter, fontSize = size.sp, fontWeight = FontWeight.SemiBold, color = fg.copy(alpha = a)))
    val pw = layout.size.width + 14.dp.toPx(); val ph = layout.size.height + 6.dp.toPx()
    drawRoundRect(bg.copy(alpha = bg.alpha * a), Offset(c.x - pw / 2, c.y - ph / 2), Size(pw, ph), CornerRadius(ph / 2))
    drawText(layout, topLeft = Offset(c.x - layout.size.width / 2f, c.y - layout.size.height / 2f))
}

// ------------------------------------------------------------------ the scene of the guide: parcel and sheet
/** Where things stand in the guide's scene (units of 10 cm): a 40 × 30 × 20 cm parcel, the sheet 5 cm in front of it. */
object Spot {
    const val BX = 3.2f; const val BY = 1.0f; const val BW = 4f; const val BD = 3f; const val BH = 2f
    const val SX = 3.9f; const val SY = BY + BD + 0.5f
}

/** Step 3: the sheet slides in beside the parcel, the 5 cm gap shows, a tick. Or one of the [wrong] ways (0-3), with a cross. */
@Composable
fun ArtPlace(modifier: Modifier, wrong: Int?) {
    val t = loopClock(3600, still = 0.95f)
    val tm = rememberTextMeasurer()
    Canvas(modifier.background(Art.sky)) {
        val iso = if (wrong == 2) Iso.fit(size, 1.5f, 9f, 0f, 9f, 5.5f) else Iso.fit(size, 2.6f, 8.2f, 0.6f, 8f, 2.4f)
        isoFloor(iso, 0f, 10.5f, -1f, 9.5f)
        when (wrong) {
            null -> {
                isoBox(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH)
                val k = phase(t, 0.05f, 0.4f)
                isoSheet(iso, Spot.SX - (1 - k) * 0f, Spot.SY + (1 - k) * 3.5f, alpha = 0.3f + 0.7f * k)
                // the gap
                val g = phase(t, 0.45f, 0.6f)
                if (g > 0f) {
                    val gx = Spot.SX + 2.1f + 0.35f
                    val a = iso.p(gx, Spot.BY + Spot.BD); val b = iso.p(gx, Spot.SY)
                    drawLine(C.brand.copy(alpha = g), a, b, 2.5.dp.toPx())
                    drawLine(C.brand.copy(alpha = g), iso.p(gx - 0.2f, Spot.BY + Spot.BD), iso.p(gx + 0.2f, Spot.BY + Spot.BD), 2.5.dp.toPx())
                    drawLine(C.brand.copy(alpha = g), iso.p(gx - 0.2f, Spot.SY), iso.p(gx + 0.2f, Spot.SY), 2.5.dp.toPx())
                    val m = Offset((a.x + b.x) / 2, (a.y + b.y) / 2)
                    drawLine(C.brand.copy(alpha = g), m, Offset(m.x + 34.dp.toPx(), m.y + 14.dp.toPx()), 1.5.dp.toPx())
                    pill(tm, "jarak ±5 cm", Offset(m.x + 66.dp.toPx(), m.y + 16.dp.toPx()), C.brand, Color.White, g, 11f)
                }
                badge(Offset(size.width - 26.dp.toPx(), 26.dp.toPx()), 15.dp.toPx(), true, phase(t, 0.62f, 0.72f))
            }
            0 -> { isoBox(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH); isoSheet(iso, Spot.BX + 0.95f, Spot.BY + 0.02f, z = Spot.BH) }
            1 -> { isoBox(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH); isoSheet(iso, Spot.SX, Spot.SY, fold = 1.1f) }
            2 -> {
                // a table: top at 50 cm, four legs; the parcel on it, the sheet on the floor
                val tz = 3.2f; val x0 = 2.4f; val x1 = 8.2f; val y0 = 0.2f; val y1 = 4.8f
                for ((lx, ly) in listOf(x0 + 0.2f to y1 - 0.2f, x1 - 0.2f to y1 - 0.2f, x1 - 0.2f to y0 + 0.2f)) drawLine(Art.woodDark, iso.p(lx, ly), iso.p(lx, ly, tz), 4.dp.toPx())
                fillPoly(listOf(iso.p(x0, y1, tz - 0.25f), iso.p(x1, y1, tz - 0.25f), iso.p(x1, y1, tz), iso.p(x0, y1, tz)), Art.woodDark)
                fillPoly(listOf(iso.p(x1, y0, tz - 0.25f), iso.p(x1, y1, tz - 0.25f), iso.p(x1, y1, tz), iso.p(x1, y0, tz)), Art.woodDark)
                fillPoly(listOf(iso.p(x0, y0, tz), iso.p(x1, y0, tz), iso.p(x1, y1, tz), iso.p(x0, y1, tz)), Art.wood)
                isoBox(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH, z0 = tz)
                isoSheet(iso, Spot.SX, 5.6f)
            }
            else -> { isoSheet(iso, Spot.SX, Spot.BY + Spot.BD - 1.6f); isoBox(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH) }
        }
        if (wrong != null) badge(Offset(size.width - 26.dp.toPx(), 26.dp.toPx()), 15.dp.toPx(), false)
    }
}

/** Step 1: the sheet as printed; a ruler slides under the black square and reads its side. */
@Composable
fun ArtPrint(modifier: Modifier, a3: Boolean) {
    val t = loopClock(3400, still = 1f)
    val tm = rememberTextMeasurer()
    Canvas(modifier.background(Art.sky)) {
        val sh = size.height * 0.86f; val sw = sh / 1.414f
        val ox = size.width * 0.36f - sw / 2; val oy = (size.height - sh) / 2
        drawRoundRect(Color.Black.copy(alpha = 0.08f), Offset(ox + 4.dp.toPx(), oy + 5.dp.toPx()), Size(sw, sh), CornerRadius(4.dp.toPx()))
        drawRoundRect(Color.White, Offset(ox, oy), Size(sw, sh), CornerRadius(4.dp.toPx()))
        val side = sw * (if (a3) 240f / 297f else 160f / 210f)
        val mx = ox + (sw - side) / 2; val my = oy + sh * 0.1f
        drawRect(C.ink, Offset(mx, my), Size(side, side))
        val cell = side / Aruco.GRID
        val code = Aruco.DICT_4X4_50[if (a3) MarkerSheet.A3.id else MarkerSheet.A4.id]
        for (i in 0 until 4) for (j in 0 until 4) if ((code shr (15 - (i * 4 + j))) and 1 == 1)
            drawRect(Color.White, Offset(mx + (j + 1) * cell, my + (i + 1) * cell), Size(cell + 0.6f, cell + 0.6f))
        for (k in 0..3) drawRoundRect(Color(0xFFD5DBE2), Offset(mx, my + side + sh * 0.06f + k * sh * 0.045f), Size(side * (if (k == 3) 0.5f else 0.92f), sh * 0.016f), CornerRadius(3f))
        // the ruler: slides in from the left, its zero on the square's left edge
        val k = phase(t, 0.08f, 0.45f)
        val rh = sw * 0.07f; val ry = my + side + 2.dp.toPx(); val rl = side * 1.18f
        val rx = mx - (1 - k) * (mx + rl)
        drawRoundRect(Color(0xFFFFD84D), Offset(rx, ry), Size(rl, rh), CornerRadius(2.dp.toPx()))
        val n = 40
        for (i in 0..n) {
            val x = rx + i * side / (if (a3) 24f else 16f) / 2.5f
            if (x > rx + rl - 2) break
            drawLine(C.onYellow, Offset(x, ry), Offset(x, ry + rh * (if (i % 5 == 0) 0.6f else 0.32f)), 1.dp.toPx())
        }
        val a = phase(t, 0.5f, 0.62f)
        if (a > 0f) {
            drawLine(C.green.copy(alpha = a), Offset(mx, my - 9.dp.toPx()), Offset(mx + side, my - 9.dp.toPx()), 2.dp.toPx())
            drawLine(C.green.copy(alpha = a), Offset(mx, my - 14.dp.toPx()), Offset(mx, my - 4.dp.toPx()), 2.dp.toPx())
            drawLine(C.green.copy(alpha = a), Offset(mx + side, my - 14.dp.toPx()), Offset(mx + side, my - 4.dp.toPx()), 2.dp.toPx())
        }
        // what it must read, beside the sheet
        val lx = ox + sw + (size.width - ox - sw) / 2
        pill(tm, if (a3) "A3 · 24 cm" else "A4 · 16 cm", Offset(lx, size.height * 0.36f), C.ink, Color.White, 1f, 13f)
        pill(tm, "skala 100%", Offset(lx, size.height * 0.52f), C.brandL, C.brandD, 1f, 12f)
        badge(Offset(lx, size.height * 0.7f), 15.dp.toPx(), true, a)
    }
}

/** Step 4, seen from the side: the courier at the corner, the phone at chest height tilting down to 45°. */
@Composable
fun ArtAngle(modifier: Modifier) {
    val t = loopClock(3800, still = 1f)
    val tm = rememberTextMeasurer()
    Canvas(modifier.background(Art.sky)) {
        val w = size.width; val h = size.height
        val ground = h * 0.86f
        drawRect(Art.floor, Offset(0f, ground), Size(w, h - ground))
        drawLine(Art.floorLine, Offset(0f, ground), Offset(w, ground), 2.dp.toPx())
        // parcel and sheet
        val bx = w * 0.62f; val bw = w * 0.24f; val bh = h * 0.2f
        drawRect(Art.boxLeft, Offset(bx, ground - bh), Size(bw, bh)); drawRect(Art.tape, Offset(bx, ground - bh), Size(bw, bh * 0.12f))
        drawRect(C.ink, Offset(w * 0.4f, ground - 3.dp.toPx()), Size(w * 0.16f, 3.dp.toPx()))
        drawRect(Color.White, Offset(w * 0.37f, ground - 1.dp.toPx()), Size(w * 0.22f, 1.dp.toPx()))
        // the courier: head, body, arm
        val px = w * 0.13f
        val headR = h * 0.055f
        drawCircle(Color(0xFF64748B), headR, Offset(px, ground - h * 0.64f))
        drawRoundRect(C.brand, Offset(px - headR * 1.1f, ground - h * 0.56f), Size(headR * 2.2f, h * 0.3f), CornerRadius(headR))
        drawLine(Color(0xFF475569), Offset(px - headR * 0.5f, ground - h * 0.26f), Offset(px - headR * 0.5f, ground), headR * 0.7f, cap = StrokeCap.Round)
        drawLine(Color(0xFF475569), Offset(px + headR * 0.5f, ground - h * 0.26f), Offset(px + headR * 0.5f, ground), headR * 0.7f, cap = StrokeCap.Round)
        // the phone at chest height, tilting from level to 45° down
        val ph = Offset(w * 0.25f, ground - h * 0.47f)
        drawLine(Color(0xFF64748B), Offset(px + headR * 0.6f, ground - h * 0.45f), Offset(ph.x - 4.dp.toPx(), ph.y), headR * 0.45f, cap = StrokeCap.Round)
        val k = phase(t, 0.12f, 0.55f)
        val deg = 45f * k
        val good = deg >= 30f
        val col = lerp(C.warn, C.green, phase(t, 0.45f, 0.55f))
        // the view: the optical axis and the edges of the picture
        val rad = Math.toRadians(deg.toDouble())
        val axisLen = w * 0.75f
        for ((off, a) in listOf(0f to 0.9f, -18f to 0.35f, 18f to 0.35f)) {
            val r = Math.toRadians((deg + off).toDouble())
            val end = Offset((ph.x + cos(r) * axisLen).toFloat(), (ph.y + sin(r) * axisLen).toFloat())
            val clipT = if (end.y > ground) (ground - ph.y) / (end.y - ph.y) else 1f
            drawLine(col.copy(alpha = a), ph, Offset(ph.x + (end.x - ph.x) * clipT, ph.y + (end.y - ph.y) * clipT), 2.dp.toPx(),
                pathEffect = if (off == 0f) null else PathEffect.dashPathEffect(floatArrayOf(10f, 8f)))
        }
        rotate(deg, ph) {
            drawRoundRect(C.ink, Offset(ph.x - 4.dp.toPx(), ph.y - 13.dp.toPx()), Size(8.dp.toPx(), 26.dp.toPx()), CornerRadius(2.dp.toPx()))
        }
        // the angle against the level
        val arc = w * 0.16f
        drawLine(Color(0xFF94A3B8), ph, Offset(ph.x + arc * 1.25f, ph.y), 1.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f)))
        drawArc(col, 0f, deg, false, Offset(ph.x - arc, ph.y - arc), Size(arc * 2, arc * 2), style = Stroke(2.5.dp.toPx()))
        val mid = Math.toRadians(deg / 2.0)
        pill(tm, "${deg.toInt()}°", Offset((ph.x + cos(mid) * arc * 1.45f).toFloat(), (ph.y + sin(mid) * arc * 1.45f).toFloat()), col, Color.White, 1f, 12f)
        pill(tm, "HP setinggi dada", Offset(ph.x + w * 0.12f, ph.y - h * 0.2f), C.ink, Color.White, 1f, 11f)
        pill(tm, if (good) "Sudut pas: 30–60°" else "Miringkan ke bawah", Offset(w * 0.76f, h * 0.14f), if (good) C.greenL else C.amberL, if (good) C.green else C.amber, 1f, 12f)
        badge(Offset(w * 0.76f + 0f, h * 0.3f), 13.dp.toPx(), true, phase(t, 0.55f, 0.65f))
    }
}

/** A phone frame round a camera picture of the scene. */
@Composable
fun PhoneFrame(modifier: Modifier, content: @Composable androidx.compose.foundation.layout.BoxScope.() -> Unit) {
    Box(modifier.fillMaxHeight().aspectRatio(0.6f).clip(RoundedCornerShape(20.dp)).background(C.ink).padding(5.dp)) {
        Box(Modifier.fillMaxSize().clip(RoundedCornerShape(15.dp)).background(Art.floor)) { content() }
    }
}

/** A small status pill inside the phone picture, turning from grey to green as [on] goes 0 → 1. */
@Composable
private fun MiniCheck(text: String, on: Float) {
    Row(Modifier.clip(RoundedCornerShape(50)).background(lerp(Color(0xE6FFFFFF), C.greenL, on)).padding(horizontal = 6.dp, vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(3.dp)) {
        Sym(if (on > 0.5f) "check_circle" else "radio_button_unchecked", 11.dp, lerp(C.t3, C.green, on), filled = on > 0.5f)
        T(text, 9.sp, FontWeight.SemiBold, lerp(C.t2, C.green, on), maxLines = 1)
    }
}

/** Step 5: the camera screen; the three checks turn green one by one, the sheet is outlined, the shutter pulses. */
@Composable
fun ArtReady(modifier: Modifier) {
    val t = loopClock(4200, still = 0.95f)
    Row(modifier.background(Art.sky).padding(vertical = 10.dp), horizontalArrangement = Arrangement.Center) {
        PhoneFrame(Modifier) {
            val glow = phase(t, 0.55f, 0.65f)
            Canvas(Modifier.fillMaxSize()) {
                val iso = Iso.fit(size, 1.5f, 9.5f, 0f, 8.5f, 2.6f, 0.04f)
                isoFloor(iso, -2f, 12f, -2f, 12f)
                isoBox(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH)
                isoSheet(iso, Spot.SX, Spot.SY, glow = glow)
                val c = Offset(size.width / 2, size.height * 0.45f); val r = size.width * 0.05f
                drawCircle(Color.White.copy(alpha = 0.85f), r, c, style = Stroke(1.5.dp.toPx()))
            }
            Column(Modifier.padding(5.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                MiniCheck("Sudut 45°", phase(t, 0.15f, 0.25f))
                MiniCheck("HP diam", phase(t, 0.35f, 0.45f))
                MiniCheck("Marker A4", glow)
            }
            val ready = phase(t, 0.72f, 0.8f)
            val pulse = 1f + 0.12f * ready * sin((t * 6 * PI).toFloat()).coerceAtLeast(0f)
            Box(Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp).size(30.dp).scale(pulse).clip(CircleShape).background(Color.White).padding(3.dp)
                .clip(CircleShape).background(lerp(Color(0xFFCBD5E1), C.brand, ready)))
        }
        Column(Modifier.padding(start = 14.dp).align(Alignment.CenterVertically), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((i, s) in listOf("Sudut pas", "HP diam", "Marker terbaca").withIndex()) {
                val on = when (i) { 0 -> phase(t, 0.15f, 0.25f); 1 -> phase(t, 0.35f, 0.45f); else -> phase(t, 0.55f, 0.65f) }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Sym(if (on > 0.5f) "check_circle" else "radio_button_unchecked", 18.dp, lerp(C.t3, C.green, on), filled = on > 0.5f)
                    T(s, 13.sp, FontWeight.SemiBold, lerp(C.t3, C.ink, on), modifier = Modifier.padding(start = 6.dp))
                }
            }
            Row(Modifier.alpha(phase(t, 0.72f, 0.8f)).clip(RoundedCornerShape(50)).background(C.brand).padding(horizontal = 10.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Sym("photo_camera", 14.dp, Color.White); T("Ambil foto", 12.sp, FontWeight.SemiBold, Color.White, modifier = Modifier.padding(start = 4.dp))
            }
        }
    }
}

/**
 * Step 2: the scanner screen over a parcel label. The label has the order number's barcode and a QR code at the top
 * and the resi's barcode in the window; the scan line sweeps, the window turns green round the resi, a beep, Terbaca.
 */
@Composable
fun ArtScan(modifier: Modifier) {
    val t = loopClock(4200, still = 0.95f)
    val read = phase(t, 0.5f, 0.58f)
    Row(modifier.background(Art.sky).padding(vertical = 10.dp), horizontalArrangement = Arrangement.Center) {
        PhoneFrame(Modifier) {
            Canvas(Modifier.fillMaxSize()) {
                val w = size.width; val h = size.height
                drawRect(Art.boxTop)                                                     // the carton
                drawRoundRect(Art.paper, Offset(w * 0.07f, h * 0.08f), Size(w * 0.86f, h * 0.84f), CornerRadius(3.dp.toPx()))
                bars(Offset(w * 0.14f, h * 0.15f), Size(w * 0.42f, h * 0.07f), 7)       // the order number's barcode
                qr(Offset(w * 0.66f, h * 0.13f), w * 0.2f)
                val resi = Rect(w * 0.15f, h * 0.43f, w * 0.85f, h * 0.55f)
                bars(resi.topLeft, resi.size, 3)                                          // the resi's barcode
                drawRoundRect(C.t2, Offset(w * 0.3f, h * 0.585f), Size(w * 0.4f, h * 0.022f), CornerRadius(2.dp.toPx()))
                for (i in 0 until 3) drawRoundRect(Color(0xFFCBD5E1), Offset(w * 0.15f, h * (0.68f + i * 0.055f)), Size(w * (0.6f - i * 0.12f), h * 0.02f), CornerRadius(2.dp.toPx()))
                // the window: the rest dimmed, its corners white, then green once read
                val win = Rect(w * 0.1f, h * 0.38f, w * 0.9f, h * 0.62f)
                drawPath(Path().apply { fillType = androidx.compose.ui.graphics.PathFillType.EvenOdd; addRect(Rect(Offset.Zero, size)); addRect(win) }, Color.Black.copy(alpha = 0.32f))
                val corner = lerp(Color.White, C.live, read); val l = w * 0.09f; val sw = 2.5.dp.toPx()
                for ((x, y, dx, dy) in listOf(listOf(win.left, win.top, 1f, 1f), listOf(win.right, win.top, -1f, 1f),
                        listOf(win.left, win.bottom, 1f, -1f), listOf(win.right, win.bottom, -1f, -1f))) {
                    drawLine(corner, Offset(x, y), Offset(x + dx * l, y), sw); drawLine(corner, Offset(x, y), Offset(x, y + dy * l), sw)
                }
                if (read < 1f) {                                                          // the scan line sweeps until the read
                    val p = (t / 0.5f).coerceIn(0f, 1f).let { if (it < 0.5f) it * 2 else 2 - it * 2 }
                    val y = win.top + 4.dp.toPx() + p * (win.height - 8.dp.toPx())
                    drawLine(C.brand.copy(alpha = 1f - read), Offset(win.left + 4.dp.toPx(), y), Offset(win.right - 4.dp.toPx(), y), 1.5.dp.toPx())
                }
                if (read > 0f) {
                    drawRect(C.live.copy(alpha = read), Offset(resi.left - 3.dp.toPx(), resi.top - 3.dp.toPx()),
                        Size(resi.width + 6.dp.toPx(), resi.height + 6.dp.toPx()), style = Stroke(2.dp.toPx()))
                    val beep = phase(t, 0.5f, 0.75f)                                       // the beep, as a ripple
                    if (beep in 0.01f..0.99f) drawCircle(C.live.copy(alpha = (1 - beep) * 0.6f), w * (0.1f + 0.45f * beep), resi.center, style = Stroke(2.dp.toPx()))
                }
            }
            Row(Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp).alpha(phase(t, 0.58f, 0.68f)).clip(RoundedCornerShape(50))
                .background(C.greenL).padding(horizontal = 7.dp, vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                Sym("check_circle", 12.dp, C.green, filled = true)
                T("Terbaca", 9.5.sp, FontWeight.Bold, C.green, modifier = Modifier.padding(start = 3.dp))
            }
        }
        Column(Modifier.padding(start = 14.dp).align(Alignment.CenterVertically), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((i, s) in listOf("Kotak di barcode resi", "Jarak 10–25 cm", "Bip: resi terbaca").withIndex()) {
                val on = when (i) { 0 -> phase(t, 0.08f, 0.18f); 1 -> phase(t, 0.26f, 0.36f); else -> read }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Sym(if (on > 0.5f) "check_circle" else "radio_button_unchecked", 18.dp, lerp(C.t3, C.green, on), filled = on > 0.5f)
                    T(s, 13.sp, FontWeight.SemiBold, lerp(C.t3, C.ink, on), modifier = Modifier.padding(start = 6.dp))
                }
            }
            Row(Modifier.alpha(phase(t, 0.72f, 0.8f)).clip(RoundedCornerShape(50)).background(C.brand).padding(horizontal = 10.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Sym("photo_camera", 14.dp, Color.White); T("Lanjut foto paket", 12.sp, FontWeight.SemiBold, Color.White, modifier = Modifier.padding(start = 4.dp))
            }
        }
    }
}

/** A linear barcode's bars filling [at] + [size]; [seed] picks the pattern (the same every frame). */
private fun DrawScope.bars(at: Offset, size: Size, seed: Int) {
    var r = seed * 7919 + 17
    val widths = ArrayList<Int>()
    while (widths.sum() < 90) { r = (r * 1103515245 + 12345) and 0x7fffffff; widths += 1 + (r shr 16) % 3 }
    val unit = size.width / widths.sum()
    var x = at.x
    widths.forEachIndexed { i, wd -> if (i % 2 == 0) drawRect(C.ink, Offset(x, at.y), Size(unit * wd, size.height)); x += unit * wd }
}

/** A small QR-like square: three finder corners and a fixed scatter of modules. */
private fun DrawScope.qr(at: Offset, side: Float) {
    val n = 9; val c = side / n
    fun mod(i: Int, j: Int) = drawRect(C.ink, Offset(at.x + i * c, at.y + j * c), Size(c, c))
    for ((fi, fj) in listOf(0 to 0, n - 3 to 0, 0 to n - 3)) for (i in 0 until 3) for (j in 0 until 3) if (i != 1 || j != 1) mod(fi + i, fj + j)
    var r = 41
    for (i in 0 until n) for (j in 0 until n) {
        val finder = (i < 3 && j < 3) || (i >= n - 3 && j < 3) || (i < 3 && j >= n - 3)
        r = (r * 1103515245 + 12345) and 0x7fffffff
        if (!finder && (r shr 16) % 2 == 0) mod(i, j)
    }
}

/** Step 6: a tap on the parcel, the cut-out appears, the green box draws itself, the size shows. */
@Composable
fun ArtTap(modifier: Modifier) {
    val t = loopClock(4200, still = 1f)
    val tm = rememberTextMeasurer()
    Canvas(modifier.background(Art.sky)) {
        val iso = Iso.fit(size, 1.5f, 9.5f, 0f, 8.5f, 2.6f, 0.08f)
        isoFloor(iso, -2f, 12f, -2f, 12f)
        isoBox(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH)
        isoSheet(iso, Spot.SX, Spot.SY, glow = 1f)
        val c = iso.p(Spot.BX + Spot.BW * 0.55f, Spot.BY + Spot.BD * 0.5f, Spot.BH)
        // the tap: a ripple and the finger's point
        val tap = ((t - 0.05f) / 0.3f).coerceIn(0f, 1f)
        if (tap > 0f && tap < 1f) {
            drawCircle(C.brand.copy(alpha = (1 - tap) * 0.5f), 10.dp.toPx() + tap * 34.dp.toPx(), c, style = Stroke(3.dp.toPx()))
            drawCircle(Color.White, 9.dp.toPx(), c); drawCircle(C.brand, 6.dp.toPx(), c)
        }
        isoBoxMask(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH, 0.6f * phase(t, 0.3f, 0.45f))
        isoBoxEdges(iso, Spot.BX, Spot.BY, Spot.BW, Spot.BD, Spot.BH, phase(t, 0.45f, 0.78f), 2.5.dp.toPx())
        val a = phase(t, 0.78f, 0.88f)
        pill(tm, "40 × 30 × 20 cm", Offset(size.width / 2, size.height * 0.1f), C.ink, Color.White, a, 14f)
        pill(tm, "Ketuk paket", Offset(c.x, c.y - 30.dp.toPx()), C.brand, Color.White, 1f - phase(t, 0.3f, 0.4f), 11f)
    }
}

/** Step 7: what each status means and what to do, appearing one after another. */
@Composable
fun ArtResult(modifier: Modifier) {
    val t = loopClock(4000, still = 1f)
    Column(modifier.background(Art.sky).padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterVertically)) {
        val rows = listOf(
            Triple(Tone.OK to "check_circle", "Akurat", "Lanjut isi berat, simpan"),
            Triple(Tone.WARN to "warning", "Perlu Dicek", "Tambah foto dari pojok lain"),
            Triple(Tone.WARN to "warehouse", "Tidak bisa diukur", "Tandai Ukur di Hub"),
        )
        rows.forEachIndexed { i, (tone, title, todo) ->
            val a = phase(t, 0.08f + i * 0.16f, 0.24f + i * 0.16f)
            Row(Modifier.fillMaxWidth().offset(x = ((1 - a) * 40).dp).alpha(a).clip(RoundedCornerShape(12.dp)).background(Color.White).padding(10.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Chip(title, tone.first, tone.second)
                Sym("arrow_forward", 18.dp, C.t3, modifier = Modifier.padding(horizontal = 8.dp))
                T(todo, 13.sp, FontWeight.SemiBold, maxLines = 2)
            }
        }
    }
}

/** A small drawing of the A4 sheet's marker (its real pattern), as an icon. */
@Composable
fun MarkerGlyph(size: Dp, id: Int = MarkerSheet.A4.id) {
    Canvas(Modifier.size(size).clip(RoundedCornerShape(size / 8)).background(Color.White).padding(size / 10)) {
        val c = this.size.width / Aruco.GRID
        drawRect(C.ink)
        val code = Aruco.DICT_4X4_50[id]
        for (i in 0 until 4) for (j in 0 until 4) if ((code shr (15 - (i * 4 + j))) and 1 == 1)
            drawRect(Color.White, Offset((j + 1) * c, (i + 1) * c), Size(c + 0.5f, c + 0.5f))
    }
}
