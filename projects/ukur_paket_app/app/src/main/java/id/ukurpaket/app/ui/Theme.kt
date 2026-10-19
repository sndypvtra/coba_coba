package id.ukurpaket.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukurpaket.app.R

/** True in screenshot tests: endless animations are drawn still so the renderer can settle. */
val LocalStill = staticCompositionLocalOf { false }

object C {
    val ink = Color(0xFF0F172A)
    val t2 = Color(0xFF475569)
    val t3 = Color(0xFF94A3B8)
    val line = Color(0xFFE2E8F0)
    val bg = Color(0xFFF3F5F8)
    val card = Color.White
    val blue = Color(0xFF2563EB)
    val blueL = Color(0xFFEFF4FF)
    val green = Color(0xFF16A34A)
    val greenL = Color(0xFFECFDF3)
    val live = Color(0xFF22C55E)
    val amber = Color(0xFFD97706)
    val amberL = Color(0xFFFFF7E6)
    val red = Color(0xFFDC2626)
    val redL = Color(0xFFFEF2F2)
    val glass = Color(0xA80F172A)
    val cyan = Color(0xFF22D3EE)
}

val Inter = FontFamily(
    Font(R.font.inter_regular, FontWeight.Normal),
    Font(R.font.inter_medium, FontWeight.Medium),
    Font(R.font.inter_semibold, FontWeight.SemiBold),
    Font(R.font.inter_bold, FontWeight.Bold),
)
private val SymLine = FontFamily(Font(R.font.msym_line))
private val SymFill = FontFamily(Font(R.font.msym_fill))

@Composable
fun UkurTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(primary = C.blue, background = C.bg, surface = C.card, onSurface = C.ink),
        typography = MaterialTheme.typography.let { t ->
            t.copy(
                bodyLarge = t.bodyLarge.copy(fontFamily = Inter),
                bodyMedium = t.bodyMedium.copy(fontFamily = Inter),
                labelLarge = t.labelLarge.copy(fontFamily = Inter),
                titleLarge = t.titleLarge.copy(fontFamily = Inter),
            )
        },
        content = content,
    )
}

/** Material Symbols icon by name (ligature), from the bundled subset. */
@Composable
fun Sym(name: String, size: Dp = 20.dp, color: Color = Color.Unspecified, filled: Boolean = false, modifier: Modifier = Modifier) {
    Text(name, modifier = modifier, color = color,
        style = TextStyle(fontFamily = if (filled) SymFill else SymLine, fontSize = (size.value).sp, lineHeight = (size.value).sp,
            fontFeatureSettings = "liga"))
}

@Composable
fun T(text: String, size: TextUnit = 14.sp, weight: FontWeight = FontWeight.Normal, color: Color = C.ink, modifier: Modifier = Modifier,
      lineHeight: TextUnit = TextUnit.Unspecified, maxLines: Int = Int.MAX_VALUE) {
    Text(text, modifier = modifier, color = color, maxLines = maxLines,
        style = TextStyle(fontFamily = Inter, fontSize = size, fontWeight = weight, lineHeight = lineHeight))
}

@Composable
fun Card(modifier: Modifier = Modifier, highlight: Boolean = false, padding: Dp = 14.dp, onClick: (() -> Unit)? = null,
         content: @Composable ColumnScope.() -> Unit) {
    val shape = RoundedCornerShape(16.dp)
    Column(
        modifier
            .fillMaxWidth()
            .clip(shape)
            .background(C.card)
            .border(if (highlight) 1.5.dp else 1.dp, if (highlight) C.blue else C.line, shape)
            .let { if (onClick != null) it.clickable(onClick = onClick) else it }
            .padding(padding),
        content = content,
    )
}

enum class Tone { OK, WARN, BLUE, GREY, RED }

@Composable
fun Chip(text: String, tone: Tone, icon: String? = null, onClick: (() -> Unit)? = null) {
    val (bg, fg) = when (tone) {
        Tone.OK -> C.greenL to C.green
        Tone.WARN -> C.amberL to C.amber
        Tone.BLUE -> C.blueL to C.blue
        Tone.GREY -> Color(0xFFEEF1F5) to C.t2
        Tone.RED -> C.redL to C.red
    }
    Row(
        Modifier.clip(RoundedCornerShape(50)).background(bg)
            .let { if (onClick != null) it.clickable(onClick = onClick) else it }
            .padding(horizontal = 10.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        if (icon != null) Sym(icon, 16.dp, fg, filled = true)
        T(text, 12.sp, FontWeight.SemiBold, fg, maxLines = 1)
    }
}

@Composable
fun IconTile(icon: String, tint: Color = C.blue, bg: Color = C.blueL, size: Dp = 40.dp) {
    Box(Modifier.size(size).clip(RoundedCornerShape(12.dp)).background(bg), contentAlignment = Alignment.Center) {
        Sym(icon, (size.value * 0.55f).dp, tint, filled = true)
    }
}

@Composable
fun PrimaryButton(text: String, icon: String? = null, modifier: Modifier = Modifier, color: Color = C.blue,
                  enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick, enabled = enabled, modifier = modifier.height(54.dp),
        shape = RoundedCornerShape(14.dp), contentPadding = PaddingValues(horizontal = 16.dp),
        colors = ButtonDefaults.buttonColors(containerColor = color, disabledContainerColor = Color(0xFFCBD5E1), disabledContentColor = Color.White),
    ) {
        if (icon != null) { Sym(icon, 22.dp, Color.White); Box(Modifier.size(8.dp)) }
        T(text, 16.sp, FontWeight.SemiBold, Color.White, maxLines = 1)
    }
}

@Composable
fun SecondaryButton(text: String, icon: String? = null, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick, modifier = modifier.height(54.dp), shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.5.dp, C.line), contentPadding = PaddingValues(horizontal = 14.dp),
        colors = ButtonDefaults.outlinedButtonColors(containerColor = Color.White),
    ) {
        if (icon != null) { Sym(icon, 22.dp, C.ink); Box(Modifier.size(8.dp)) }
        T(text, 16.sp, FontWeight.SemiBold, C.ink, maxLines = 1)
    }
}

@Composable
fun TopBar(title: String, subtitle: String? = null, onBack: (() -> Unit)? = null, action: @Composable RowScope.() -> Unit = {}) {
    Row(Modifier.fillMaxWidth().height(64.dp).padding(horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        if (onBack != null) {
            Box(Modifier.size(44.dp).clip(CircleShape).clickable(onClick = onBack), contentAlignment = Alignment.Center) {
                Sym("arrow_back", 24.dp, C.ink)
            }
        } else Box(Modifier.size(8.dp))
        Column(Modifier.weight(1f).padding(start = 6.dp)) {
            T(title, 18.sp, FontWeight.SemiBold)
            if (subtitle != null) T(subtitle, 12.5.sp, color = C.t2, maxLines = 1)
        }
        action()
    }
}

@Composable
fun ProgressLine(fraction: Float, color: Color = C.blue) {
    Box(Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)).background(Color(0xFFE5E9F0))) {
        Box(Modifier.fillMaxWidth(fraction.coerceIn(0f, 1f)).height(6.dp).clip(RoundedCornerShape(3.dp)).background(color))
    }
}
