package id.ukuraja.app.ui

import android.app.Activity
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukuraja.app.data.id
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

val ID_LOCALE = Locale("id", "ID")

private fun Long.isToday(): Boolean {
    val f = SimpleDateFormat("yyyyMMdd", Locale.US)
    return f.format(Date(this)) == f.format(Date())
}

/** Home: scan the label (or type the number); the marker tip; the parcels measured today. */
@Composable
fun HomeScreen(model: AppModel, activity: Activity) {
    val ms by model.store.measurements.collectAsState()
    val settings by model.store.settings.collectAsState()
    val today = ms.filter { it.createdAt.isToday() }.sortedByDescending { it.createdAt }
    var typing by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            IconTile("deployed_code", Color.White, C.brand, 38.dp)
            Column(Modifier.weight(1f).padding(start = 10.dp)) {
                T("UkurAja", 16.sp, FontWeight.Bold)
                T(settings.operator.ifBlank { "Ukur paket dengan foto" }, 12.sp, color = C.t2, maxLines = 1)
            }
            Chip("Panduan ukur", Tone.GREY, "menu_book") { model.go(Screen.Guide()) }
        }
        LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(16.dp, 4.dp, 16.dp, 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            item {
                Card(highlight = true) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconTile("barcode_scanner", Color.White, C.brand, 52.dp)
                        Column(Modifier.weight(1f).padding(start = 12.dp)) {
                            T("Scan Resi", 20.sp, FontWeight.Bold)
                            T(if (model.hardwareScanner) "Tekan tombol scan di samping HP, arahkan ke barcode resi"
                              else "Arahkan kamera ke barcode di label paket", 13.sp, color = C.t2)
                        }
                    }
                    Spacer(Modifier.height(14.dp))
                    if (model.hardwareScanner) {
                        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(C.brandL).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                            Sym("barcode_scanner", 22.dp, C.brand, filled = true)
                            T("Scanner HP siap · tekan tombol scan", 14.sp, FontWeight.SemiBold, C.brandD, modifier = Modifier.padding(start = 10.dp))
                        }
                        Spacer(Modifier.height(10.dp))
                    }
                    PrimaryButton(if (model.hardwareScanner) "Scan pakai kamera" else "Scan resi", if (model.hardwareScanner) "photo_camera" else "barcode_scanner",
                        Modifier.fillMaxWidth()) { model.scanResi(activity) }
                    Spacer(Modifier.height(10.dp))
                    SecondaryButton("Ketik Resi", "keyboard", Modifier.fillMaxWidth()) { typing = true }
                }
            }
            if (!settings.guideSeen) item { GuideTip { model.go(Screen.Guide()) } }
            item {
                Spacer(Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.Bottom) {
                    T("Hari ini", 18.sp, FontWeight.Bold, modifier = Modifier.weight(1f))
                    T(SimpleDateFormat("EEEE, d MMM", ID_LOCALE).format(Date()), 12.5.sp, color = C.t2)
                }
                T(if (today.isEmpty()) "Belum ada paket yang diukur" else "${today.size} paket diukur" +
                    today.count { it.atHub }.let { if (it > 0) " · $it Ukur di Hub" else "" } +
                    today.filter { !it.atHub }.sumOf { it.chargedKg }.let { if (it > 0) " · total berat tagih ${it.id(2)} kg" else "" }, 13.sp, color = C.t2)
            }
            if (today.isEmpty()) item {
                Card {
                    Column(Modifier.fillMaxWidth().padding(vertical = 18.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        IconTile("inventory_2", C.t3, Color(0xFFEEF1F5), 56.dp)
                        Spacer(Modifier.height(10.dp))
                        T("Scan resi paket pertama", 15.sp, FontWeight.SemiBold)
                        T("Hasil ukur hari ini muncul di sini", 12.5.sp, color = C.t2)
                    }
                }
            } else item {
                Card(padding = 6.dp) {
                    today.forEachIndexed { i, m ->
                        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).clickable { model.go(Screen.Detail(m.id)) }.padding(10.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            Photo(m.photo, Modifier.size(40.dp, 54.dp).clip(RoundedCornerShape(8.dp)), sample = 4)
                            Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                                T(m.resi, 14.sp, FontWeight.SemiBold, maxLines = 1)
                                T((if (m.atHub) m.note ?: m.dims() else m.dims() + " · ${m.chargedKg.id(2)} kg") + " · " +
                                    SimpleDateFormat("HH:mm", ID_LOCALE).format(Date(m.createdAt)), 12.5.sp, color = C.t2, maxLines = 1)
                            }
                            StatusChip(m)
                        }
                        if (i < today.size - 1) Box(Modifier.fillMaxWidth().padding(horizontal = 10.dp).height(1.dp).background(C.line))
                    }
                }
            }
        }
        BottomNav(model, Screen.Home)
    }
    if (typing) ResiDialog(onDismiss = { typing = false }) { typing = false; model.openResi(it) }
}

/** Until the guide has been gone through once: how to measure, step by illustrated step. */
@Composable
private fun GuideTip(onOpen: () -> Unit) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(C.yellowL).clickable(onClick = onOpen).padding(14.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(44.dp).clip(RoundedCornerShape(12.dp)).background(Color.White), contentAlignment = Alignment.Center) { MarkerGlyph(30.dp) }
        Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
            T("Baru pakai UkurAja?", 14.5.sp, FontWeight.SemiBold, C.onYellow)
            T("Lihat Panduan ukur: ${GuidePages.COUNT} langkah bergambar, dari scan resi sampai hasil. Pakai marker supaya ukuran langsung tepat.", 12.5.sp, color = C.onYellow)
        }
        Sym("chevron_right", 22.dp, C.onYellow)
    }
}

@Composable
fun ResiDialog(onDismiss: () -> Unit, onOk: (String) -> Unit) {
    var v by remember { mutableStateOf("") }
    val code = v.trim()
    AlertDialog(onDismissRequest = onDismiss,
        title = { T("Nomor resi", 18.sp, FontWeight.SemiBold) },
        text = { OutlinedTextField(v, { v = it.take(60) }, singleLine = true, supportingText = { T("Lihat nomor pengiriman di label paket", 12.sp, color = C.t3) }) },
        confirmButton = { TextButton(onClick = { onOk(code) }, enabled = code.isNotEmpty()) { T("Ukur", weight = FontWeight.SemiBold, color = if (code.isNotEmpty()) C.brand else C.t3) } },
        dismissButton = { TextButton(onClick = onDismiss) { T("Batal", color = C.t2) } })
}
