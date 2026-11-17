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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukuraja.app.data.Export
import id.ukuraja.app.data.Status
import id.ukuraja.app.data.cm
import id.ukuraja.app.data.id
import id.ukuraja.app.data.parseDecimal
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// ------------------------------------------------------------------ weight
@Composable
fun WeightScreen(model: AppModel) {
    val d = model.draft
    if (d?.result == null) { LaunchedEffect(Unit) { model.back() }; return }
    val r = d.result
    val settings by model.store.settings.collectAsState()
    val div = settings.divisor
    val volKg = r.lengthCm * r.widthCm * r.heightCm / div
    var text by remember { mutableStateOf("") }
    val scale = parseDecimal(text)?.takeIf { it > 0 && it <= 500 }
    val invalid = text.isNotBlank() && scale == null
    val charged = kotlin.math.ceil(maxOf(volKg, scale ?: 0.0) * 100) / 100

    Column(Modifier.fillMaxSize()) {
        TopBar("Berat paket", d.resi, onBack = { model.back() })
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Card {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Photo(r.evidence, Modifier.size(58.dp, 80.dp).clip(RoundedCornerShape(10.dp)), sample = 4)
                    Column(Modifier.weight(1f).padding(start = 12.dp)) {
                        T("${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} cm", 18.sp, FontWeight.Bold)
                        T("Volume ${(r.lengthCm * r.widthCm * r.heightCm / 1000).id()} L · ${r.scaleSource}", 12.5.sp, color = C.t2)
                    }
                    if (r.status == Status.OK) Chip("Akurat", Tone.OK, "check_circle") else Chip("Perlu Dicek", Tone.WARN, "warning")
                }
            }
            T("Berat Aktual (kg)", 13.sp, FontWeight.SemiBold, C.t2)
            OutlinedTextField(text, { v -> text = v.filter { it.isDigit() || it == ',' || it == '.' }.take(7) }, singleLine = true,
                modifier = Modifier.fillMaxWidth(), placeholder = { T("contoh 1,25", color = C.t3) }, isError = invalid,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                textStyle = TextStyle(fontFamily = Inter, fontSize = 24.sp, fontWeight = FontWeight.Bold))
            if (invalid) T("Isi angka berat dalam kg, contoh 1,25 (maksimal 500).", 12.5.sp, color = C.red)
            else T("Boleh dikosongkan kalau tidak ada timbangan.", 12.5.sp, color = C.t3)
            Card {
                WRow("Berat Aktual", scale?.let { "${it.id(2)} kg" } ?: "–")
                WRow("Berat volumetrik", "${volKg.id(2)} kg", "${r.lengthCm.cm()} × ${r.widthCm.cm()} × ${r.heightCm.cm()} ÷ ${div.toDouble().id(0)}")
                Spacer(Modifier.height(6.dp))
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(C.greenL).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        T("Berat Tagih", 14.sp, FontWeight.SemiBold)
                        T(if (volKg >= (scale ?: 0.0)) "berat volumetrik lebih besar" else "berat aktual lebih besar", 12.sp, color = C.t2)
                    }
                    T("${charged.id(2)} kg", 22.sp, FontWeight.Bold, C.green)
                }
            }
            T("Faktor volumetrik ${div.toDouble().id(0)} bisa diubah di Pengaturan.", 12.sp, color = C.t3)
        }
        PrimaryButton("Simpan", "check", Modifier.fillMaxWidth().padding(16.dp), enabled = !invalid) { model.save(scale) }
    }
}

// ------------------------------------------------------------------ saved
@Composable
fun SavedScreen(model: AppModel, activity: Activity, id: String) {
    val ms by model.store.measurements.collectAsState()
    val m = ms.firstOrNull { it.id == id }
    var typing by remember { mutableStateOf(false) }
    if (m == null) { LaunchedEffect(Unit) { model.home() }; return }
    val today = ms.count { SimpleDateFormat("yyyyMMdd", Locale.US).let { f -> f.format(Date(it.createdAt)) == f.format(Date()) } }
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Column(Modifier.fillMaxWidth().padding(top = 20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.size(64.dp).clip(CircleShape).background(C.green), contentAlignment = Alignment.Center) { Sym("check", 40.dp, Color.White, filled = true) }
                Spacer(Modifier.height(12.dp))
                T("Paket tersimpan", 21.sp, FontWeight.Bold)
                T("Paket ke-$today hari ini", 13.sp, color = C.t2)
            }
            MeasurementCard(m)
            T(if (m.atHub) "Foto, waktu, lokasi, dan alasan disimpan. Ukuran diisi oleh hub."
              else "Foto dengan kotak ukur, ukuran, berat, waktu, dan lokasi disimpan sebagai bukti. Angka ukur tidak bisa diedit.", 12.5.sp, color = C.t2)
        }
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (model.hardwareScanner) T("Atau tekan tombol scan di samping HP untuk paket berikutnya.", 12.5.sp, color = C.t3)
            PrimaryButton("Paket berikutnya", "barcode_scanner", Modifier.fillMaxWidth()) { model.scanResi(activity) }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryButton("Ketik Resi", "keyboard", Modifier.weight(1f)) { typing = true }
                SecondaryButton("Selesai", "check", Modifier.weight(1f)) { model.home() }
            }
        }
    }
    if (typing) ResiDialog(onDismiss = { typing = false }) { typing = false; model.openResi(it) }
}

@Composable
private fun MeasurementCard(m: id.ukuraja.app.data.Measurement) {
    Card {
        Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            Photo(m.photo, Modifier.size(110.dp, 170.dp).clip(RoundedCornerShape(12.dp)))
            Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                KV("Resi", m.resi)
                KV("Ukuran", m.dims())
                if (m.atHub) KV("Alasan", m.note ?: "-")
                else KV("Berat Tagih", "${m.chargedKg.id(2)} kg · ${if (m.volumetricWins) "volumetrik" else "aktual"}")
                if (!m.atHub) KV("Skala", (m.scaleSource ?: "-") + " · skor ${m.confidence}")
                KV("Waktu & lokasi", SimpleDateFormat("HH:mm", ID_LOCALE).format(Date(m.createdAt)) + " · " + if (m.lat != null) "GPS tercatat" else "tanpa GPS")
            }
        }
    }
}

// ------------------------------------------------------------------ history & detail
@Composable
fun HistoryScreen(model: AppModel, activity: Activity) {
    val ms by model.store.measurements.collectAsState()
    var q by remember { mutableStateOf("") }
    val shown = ms.filter { q.isBlank() || it.resi.contains(q.trim(), ignoreCase = true) }.sortedByDescending { it.createdAt }
    Column(Modifier.fillMaxSize()) {
        TopBar("Riwayat", "${ms.size} paket di HP ini") {
            Box(Modifier.size(44.dp).clip(CircleShape).clickable(enabled = ms.isNotEmpty()) {
                model.shareFile(activity, "application/zip", "Bagikan hasil ukur") { Export.writeZip(ms, model.cacheFile("ukuraja_${stamp()}.zip")) }
            }, contentAlignment = Alignment.Center) { Sym("share", 22.dp, if (ms.isNotEmpty()) C.ink else C.t3) }
        }
        if (ms.isNotEmpty()) OutlinedTextField(q, { q = it.take(40) }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            placeholder = { T("Cari nomor resi", color = C.t3) }, leadingIcon = { Sym("search", 20.dp, C.t3) })
        if (ms.isEmpty()) Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) { T("Belum ada paket yang diukur.", 14.sp, color = C.t2) }
        else LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(16.dp, 10.dp, 16.dp, 16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(shown, key = { it.id }) { m ->
                Card(onClick = { model.go(Screen.Detail(m.id)) }) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Photo(m.photo, Modifier.size(48.dp, 64.dp).clip(RoundedCornerShape(8.dp)), sample = 4)
                        Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                            T(m.resi, 14.sp, FontWeight.SemiBold)
                            T(if (m.atHub) m.dims() else m.dims() + " · ${m.chargedKg.id(2)} kg", 12.5.sp, color = C.t2)
                            T(SimpleDateFormat("d MMM, HH:mm", ID_LOCALE).format(Date(m.createdAt)) + (m.scaleSource?.let { " · $it" } ?: ""), 11.5.sp, color = C.t3, maxLines = 1)
                        }
                        StatusChip(m)
                    }
                }
            }
            if (shown.isEmpty()) item { T("Tidak ada resi yang cocok.", 13.sp, color = C.t2) }
        }
        BottomNav(model, Screen.History)
    }
}

fun stamp(): String = SimpleDateFormat("yyyyMMdd_HHmm", Locale.US).format(Date())

@Composable
fun DetailScreen(model: AppModel, activity: Activity, id: String) {
    val ms by model.store.measurements.collectAsState()
    val m = ms.firstOrNull { it.id == id }
    var confirm by remember { mutableStateOf(false) }
    if (m == null) { LaunchedEffect(Unit) { model.back() }; return }
    Column(Modifier.fillMaxSize()) {
        TopBar(m.resi, if (m.atHub) m.status.label else (m.scaleSource ?: "Foto"), onBack = { model.back() }) {
            Box(Modifier.size(44.dp).clip(CircleShape).clickable {
                model.shareFile(activity, "application/zip", "Bagikan ${m.resi}") { Export.writeZip(listOf(m), model.cacheFile("ukuraja_${m.resi.replace(Regex("[^A-Za-z0-9_-]"), "_")}.zip")) }
            }, contentAlignment = Alignment.Center) { Sym("share", 22.dp, C.ink) }
        }
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Photo(m.photo, Modifier.fillMaxWidth().height(360.dp).clip(RoundedCornerShape(16.dp)), sample = 1)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { StatusChip(m); if (!m.atHub) Chip("Skor ${m.confidence}", Tone.GREY) }
            T(m.dims(), 28.sp, FontWeight.Bold)
            Card {
                if (!m.atHub) {
                    WRow("Volume", "${m.volumeL.id()} L")
                    WRow("Berat volumetrik", "${m.volumetricKg.id(2)} kg", "÷ ${m.divisor.toDouble().id(0)}")
                    WRow("Berat Aktual", m.scaleKg?.let { "${it.id(2)} kg" } ?: "–")
                    WRow("Berat Tagih", "${m.chargedKg.id(2)} kg")
                    WRow("Skala", m.scaleSource ?: "–", m.cameraM?.let { "kamera ${it.id(2)} m di atas lantai · ${m.photos} foto" })
                }
                WRow("Waktu", SimpleDateFormat("d MMM yyyy, HH:mm", ID_LOCALE).format(Date(m.createdAt)))
                WRow("Lokasi", if (m.lat != null && m.lon != null) String.format(Locale.US, "%.5f, %.5f", m.lat, m.lon) else "–", m.gpsM?.let { "± ${it.toDouble().id(0)} m" })
                m.operator?.let { WRow("Petugas", it) }
                if (m.note != null) WRow(if (m.atHub) "Alasan" else "Catatan", m.note)
            }
            if (m.session != null && File(m.session).isDirectory) SecondaryButton("Bagikan data foto (ZIP)", "folder_zip", Modifier.fillMaxWidth()) {
                model.shareFile(activity, "application/zip", "Bagikan data foto") { Export.zipDirs(listOf(File(m.session)), model.cacheFile("foto_${File(m.session).name}.zip")) }
            }
        }
        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton("Hapus", "delete", Modifier.weight(1f)) { confirm = true }
            PrimaryButton("Ukur ulang", "refresh", Modifier.weight(1.4f)) { model.back(); model.startMeasure(m.resi, replaces = m.id) }
        }
    }
    if (confirm) AlertDialog(onDismissRequest = { confirm = false },
        title = { T("Hapus hasil ukur?", 18.sp, FontWeight.SemiBold) },
        text = { T("Foto dan data ${m.resi} ikut terhapus dari HP ini.", color = C.t2) },
        confirmButton = { TextButton(onClick = { confirm = false; model.back(); model.store.delete(m.id) }) { T("Hapus", weight = FontWeight.SemiBold, color = C.red) } },
        dismissButton = { TextButton(onClick = { confirm = false }) { T("Batal", color = C.t2) } })
}
