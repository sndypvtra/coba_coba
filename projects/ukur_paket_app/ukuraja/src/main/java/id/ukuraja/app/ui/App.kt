package id.ukuraja.app.ui

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Snackbar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import id.ukuraja.app.data.Measurement
import id.ukuraja.app.data.Status
import id.ukuraja.app.data.cm
import kotlinx.coroutines.delay

@Composable
fun App(model: AppModel, activity: Activity) {
    BackHandler(enabled = model.stack.size > 1) { model.back() }
    Box(Modifier.fillMaxSize().background(C.bg)) {
        Box(Modifier.fillMaxSize().safeDrawingPadding()) {
            when (val s = model.screen) {
                Screen.Home -> HomeScreen(model, activity)
                Screen.History -> HistoryScreen(model, activity)
                Screen.Settings -> SettingsScreen(model, activity)
                is Screen.Guide -> GuideScreen(model, activity, s.page)
                Screen.Photo -> PhotoScreen(model, activity)
                Screen.Weight -> WeightScreen(model)
                is Screen.Saved -> SavedScreen(model, activity, s.id)
                is Screen.Detail -> DetailScreen(model, activity, s.id)
            }
        }
        val msg = model.message
        if (msg != null) {
            LaunchedEffect(msg) { delay(2600); if (model.message == msg) model.message = null }
            Snackbar(Modifier.align(Alignment.BottomCenter).safeDrawingPadding().padding(16.dp)) { T(msg, color = Color.White) }
        }
    }
}

/** The camera (and, optionally, location) permission first; the screen itself once the camera is allowed. */
@Composable
fun CameraPermission(model: AppModel, activity: Activity, content: @Composable () -> Unit) {
    var granted by remember { mutableStateOf(ContextCompat.checkSelfPermission(activity, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) }
    val ask = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { r ->
        granted = r[Manifest.permission.CAMERA] == true || granted
        model.locator.refresh()
    }
    val perms = arrayOf(Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
    LaunchedEffect(Unit) { if (!granted || !model.locator.allowed()) ask.launch(perms) }
    if (!granted) {
        Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            TopBar("Izin kamera", onBack = { model.back() })
            T("UkurAja memakai kamera untuk mengukur paket. Foto diproses di HP ini dan tidak dikirim ke mana pun. " +
                "Lokasi (boleh ditolak) dicatat bersama hasil ukur sebagai bukti tempat pengukuran.", 15.sp, color = C.t2)
            PrimaryButton("Izinkan kamera", "photo_camera", Modifier.fillMaxWidth()) { ask.launch(perms) }
        }
        return
    }
    content()
}

// ------------------------------------------------------------------ pieces used on several screens
@Composable
fun BottomNav(model: AppModel, current: Screen) {
    Row(Modifier.fillMaxWidth().background(Color.White).padding(vertical = 8.dp), horizontalArrangement = Arrangement.SpaceAround) {
        listOf(Triple(Screen.Home, "barcode_scanner", "Ukur"), Triple(Screen.History, "history", "Riwayat"),
            Triple(Screen.Settings, "settings", "Pengaturan")).forEach { (s, icon, label) ->
            val on = s == current
            Column(Modifier.clip(RoundedCornerShape(12.dp)).clickable { model.tab(s) }.padding(horizontal = 18.dp, vertical = 4.dp),
                horizontalAlignment = Alignment.CenterHorizontally) {
                Sym(icon, 24.dp, if (on) C.brand else C.t3, filled = on)
                T(label, 11.5.sp, FontWeight.Medium, if (on) C.brand else C.t3)
            }
        }
    }
}

@Composable
fun StatusChip(m: Measurement) = when (m.status) {
    Status.OK -> Chip("Akurat", Tone.OK, "check_circle")
    Status.CHECK -> Chip("Perlu Dicek", Tone.WARN, "warning")
    Status.HUB -> Chip("Ukur di Hub", Tone.WARN, "warehouse")
}

fun Measurement.dims() = if (atHub) "Ukur di Hub" else "${lengthCm.cm()} × ${widthCm.cm()} × ${heightCm.cm()} cm"

/** An evidence photo from a file (decoded at 1/[sample]), or a placeholder. */
@Composable
fun Photo(path: String?, modifier: Modifier, sample: Int = 2) {
    val bmp = remember(path, sample) {
        path?.let { p -> runCatching { BitmapFactory.decodeFile(p, BitmapFactory.Options().apply { inSampleSize = sample }) }.getOrNull() }
    }
    if (bmp != null) Image(bmp.asImageBitmap(), null, modifier, contentScale = ContentScale.Crop)
    else Box(modifier.background(Color(0xFFE5E9F0)), contentAlignment = Alignment.Center) { Sym("photo_camera", 28.dp, C.t3) }
}

@Composable
fun KV(k: String, v: String) { Column { T(k, 11.5.sp, color = C.t3); T(v, 14.sp, FontWeight.SemiBold) } }

@Composable
fun WRow(label: String, value: String, sub: String? = null) {
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) { T(label, 14.sp); if (sub != null) T(sub, 12.sp, color = C.t3) }
        T(value, 15.sp, FontWeight.SemiBold)
    }
}
