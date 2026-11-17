package id.ukuraja.app.ui

import android.app.Activity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukuraja.app.Version
import id.ukuraja.app.data.Export
import id.ukuraja.app.data.Settings
import id.ukuraja.app.data.id
import id.ukuraja.app.data.parseDecimal
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.DepthModel

@Composable
fun SettingsScreen(model: AppModel, activity: Activity) {
    val s by model.store.settings.collectAsState()
    val ms by model.store.measurements.collectAsState()
    Column(Modifier.fillMaxSize()) {
        TopBar("Pengaturan")
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Card {
                T("Petugas", 15.sp, FontWeight.SemiBold)
                T("Nama yang tercatat di setiap hasil ukur dan di file ekspor.", 12.5.sp, color = C.t2)
                Spacer(Modifier.height(8.dp))
                var name by remember { mutableStateOf(s.operator) }
                OutlinedTextField(name, { v -> name = v.take(40); model.store.update { it.copy(operator = name.trim()) } }, singleLine = true,
                    modifier = Modifier.fillMaxWidth(), placeholder = { T("contoh: Andi · Counter Bekasi", color = C.t3) })
            }
            Card {
                T("Faktor Volumetrik", 15.sp, FontWeight.SemiBold)
                T("P × L × T (cm) ÷ faktor = berat volumetrik (kg)", 12.5.sp, color = C.t2)
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(4000, 5000, 6000).forEach { v ->
                        Chip(v.toDouble().id(0), if (s.divisor == v) Tone.BRAND else Tone.GREY, if (s.divisor == v) "check" else null) { model.store.update { it.copy(divisor = v) } }
                    }
                }
            }
            MarkerCard(model, activity, s)
            ScaleCard(model, s)
            Card {
                T("Data", 15.sp, FontWeight.SemiBold)
                T("${ms.size} paket tersimpan di HP ini. Hasil hanya keluar dari HP kalau dibagikan.", 12.5.sp, color = C.t2)
                Spacer(Modifier.height(8.dp))
                SecondaryButton("Ekspor tabel (CSV)", "table_view", Modifier.fillMaxWidth()) {
                    if (ms.isEmpty()) model.toast("Belum ada paket yang diukur.")
                    else model.shareFile(activity, "text/csv", "Ekspor hasil ukur") { Export.writeCsv(ms, model.cacheFile("ukuraja_${stamp()}.csv")) }
                }
                Spacer(Modifier.height(8.dp))
                SecondaryButton("Ekspor tabel + foto (ZIP)", "folder_zip", Modifier.fillMaxWidth()) {
                    if (ms.isEmpty()) model.toast("Belum ada paket yang diukur.")
                    else model.shareFile(activity, "application/zip", "Ekspor hasil ukur") { Export.writeZip(ms, model.cacheFile("ukuraja_${stamp()}.zip")) }
                }
                Spacer(Modifier.height(8.dp))
                SecondaryButton("Data foto untuk analisis (ZIP)", "biotech", Modifier.fillMaxWidth()) {
                    val dirs = model.store.photoSessionsDir.listFiles()?.filter { it.isDirectory && !it.list().isNullOrEmpty() }.orEmpty()
                    if (dirs.isEmpty()) model.toast("Belum ada data foto.")
                    else model.shareFile(activity, "application/zip", "Data foto UkurAja") { Export.zipDirs(dirs, model.cacheFile("ukuraja_foto_${stamp()}.zip")) }
                }
            }
            T("UkurAja ${Version.NAME}. Pengukuran berjalan di HP ini: MobileSAM memotong paket, Depth Anything V2 membaca lantai, " +
                "marker ArUco memberi skala. Foto dan hasil disimpan di HP ini.", 12.sp, color = C.t3)
            Spacer(Modifier.height(4.dp))
        }
        BottomNav(model, Screen.Settings)
    }
}

/** The printed sheets: their measured sides, printing, and the guide. */
@Composable
private fun MarkerCard(model: AppModel, activity: Activity, s: Settings) {
    Card {
        Row(verticalAlignment = Alignment.CenterVertically) {
            MarkerGlyph(30.dp)
            Column(Modifier.weight(1f).padding(start = 10.dp)) {
                T("Marker", 15.sp, FontWeight.SemiBold)
                T("Sisi kotak hitam hasil cetak, diukur dengan penggaris.", 12.5.sp, color = C.t2)
            }
            Chip("Panduan ukur", Tone.GREY, "menu_book") { model.go(Screen.Guide()) }
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SideField("A4 (mm)", s.markerA4Mm, Modifier.weight(1f)) { v -> model.store.update { it.copy(markerA4Mm = v) } }
            SideField("A3 (mm)", s.markerA3Mm, Modifier.weight(1f)) { v -> model.store.update { it.copy(markerA3Mm = v) } }
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Chip("Cetak A4", Tone.BRAND, "print") { printMarker(activity, model, "A4") }
            Chip("Cetak A3", Tone.BRAND, "print") { printMarker(activity, model, "A3") }
            Chip("PDF", Tone.GREY, "share") { model.share(activity, model.markerPdf("A4"), "application/pdf", "Marker A4") }
        }
    }
}

/** A side in mm: saved as soon as it reads as a plausible side (100–400 mm); anything else shows an error and is not saved. */
@Composable
private fun SideField(label: String, value: Double, modifier: Modifier, onValid: (Double) -> Unit) {
    var text by remember { mutableStateOf(value.id(1).removeSuffix(",0")) }
    val v = parseDecimal(text)
    val bad = v == null || v !in Settings.SIDE_RANGE
    OutlinedTextField(text, { t -> text = t.filter { it.isDigit() || it == ',' || it == '.' }.take(6); parseDecimal(text)?.takeIf { it in Settings.SIDE_RANGE }?.let(onValid) },
        singleLine = true, modifier = modifier, label = { T(label, 13.sp) }, isError = bad,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        supportingText = { if (bad) T("100–400 mm", 11.sp, color = C.red) })
}

/** What marker photos have taught for photos without one. */
@Composable
private fun ScaleCard(model: AppModel, s: Settings) {
    val cal = Calibration.current(s.photoCal)
    var confirm by remember { mutableStateOf(false) }
    Card {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                T("Belajar dari foto marker", 15.sp, FontWeight.SemiBold)
                T("Setiap foto dengan marker melatih skala HP ini, untuk foto paket tanpa marker.", 12.5.sp, color = C.t2)
            }
            Switch(s.learnFromMarker, { v -> model.store.update { it.copy(learnFromMarker = v) } })
        }
        Spacer(Modifier.height(8.dp))
        val f = Calibration.factor(cal)
        if (f == null) Chip("Belum ada foto marker · skala bawaan AI ×${DepthModel.DEFAULT_SCALE.toDouble().id(2)}", Tone.WARN, "warning")
        else {
            Chip("${cal.size} foto marker · faktor AI ×${f.id(2)}", if (cal.size >= 3) Tone.OK else Tone.WARN, "tune")
            Calibration.standing(cal)?.let { st -> T("Tinggi kamera saat berdiri: ${st.heightM.id(2)} m (sebaran ${(st.spread * 100).toInt()}%).", 12.sp, color = C.t2, modifier = Modifier.padding(top = 6.dp)) }
            Calibration.focus(cal, null)?.takeIf { !it.builtIn }?.let { fc -> T("Fokus kamera: faktor ×${fc.factor.id(2)} dari ${fc.samples} foto dekat.", 12.sp, color = C.t2) }
            if (cal.size < 3) T("Ukur 3 paket atau lebih dengan marker supaya skalanya stabil.", 12.sp, color = C.t3)
        }
        if (s.photoCal.isNotEmpty()) TextButton(onClick = { confirm = true }) { T("Hapus yang sudah dipelajari", 13.sp, color = C.red) }
    }
    if (confirm) AlertDialog(onDismissRequest = { confirm = false },
        title = { T("Hapus skala yang dipelajari?", 18.sp, FontWeight.SemiBold) },
        text = { T("Foto tanpa marker kembali memakai skala bawaan AI sampai ada foto marker baru. Hasil ukur yang tersimpan tidak berubah.", color = C.t2) },
        confirmButton = { TextButton(onClick = { confirm = false; model.store.update { it.copy(photoCal = emptyList()) } }) { T("Hapus", weight = FontWeight.SemiBold, color = C.red) } },
        dismissButton = { TextButton(onClick = { confirm = false }) { T("Batal", color = C.t2) } })
}
