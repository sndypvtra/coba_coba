package id.ukurpaket.app.ui

import android.app.Activity
import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukurpaket.app.BuildConfigInfo
import id.ukurpaket.app.ar.ArState
import id.ukurpaket.app.data.Measurement
import id.ukurpaket.app.data.Mode
import id.ukurpaket.app.data.Status
import id.ukurpaket.app.data.cm
import id.ukurpaket.app.data.id
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val ID = Locale("id", "ID")
private fun Measurement.dims() = if (atHub) "Ukur di hub" else "${lengthCm.cm()} × ${widthCm.cm()} × ${heightCm.cm()} cm"
private fun Measurement.place() = if (lat != null && lon != null) "GPS tercatat" else "tanpa GPS"

@Composable
private fun StatusChip(m: Measurement) = when (m.status) {
    Status.OK -> Chip("Akurat", Tone.OK, "check_circle")
    Status.CHECK -> Chip("Cek ulang", Tone.WARN, "warning")
    Status.HUB -> Chip("Ukur di hub", Tone.WARN, "warehouse")
}

@Composable
private fun ModeChip(mode: Mode) = when (mode) {
    Mode.AR_FULL -> Chip("AR penuh", Tone.OK, "view_in_ar")
    Mode.AR_BASIC -> Chip("AR dasar", Tone.BLUE, "view_in_ar")
    Mode.MARKER -> Chip("Kertas penanda", Tone.BLUE, "grid_on")
}

@Composable
private fun Photo(path: String?, modifier: Modifier) {
    val bmp = remember(path) {
        path?.let { p -> runCatching { BitmapFactory.decodeFile(p, BitmapFactory.Options().apply { inSampleSize = 2 }) }.getOrNull() }
    }
    if (bmp != null) Image(bmp.asImageBitmap(), null, modifier, contentScale = ContentScale.Crop)
    else Box(modifier.background(Color(0xFFE5E9F0)), contentAlignment = Alignment.Center) { Sym("photo_camera", 28.dp, C.t3) }
}

// ------------------------------------------------------------------ start
@Composable
fun StartScreen(model: AppModel, activity: Activity) {
    val c = model.caps
    val st by model.store.settings.collectAsState()
    LaunchedEffect(c.arcore, c.depth) {
        if (c.arcore == ArState.READY && st.prepShown > 0) model.home()
    }
    Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Spacer(Modifier.height(24.dp))
        IconTile("deployed_code", Color.White, C.blue, 64.dp)
        T("UkurPaket", 28.sp, FontWeight.Bold)
        T("Ukur panjang × lebar × tinggi paket dengan kamera HP.", 15.sp, color = C.t2)
        Card {
            T("Pemeriksaan HP", 15.sp, FontWeight.SemiBold)
            Spacer(Modifier.height(10.dp))
            CheckRow("smartphone", "HP", c.model, true)
            CheckRow("view_in_ar", "ARCore", c.arcore.label, c.arcore == ArState.READY, c.arcore == ArState.CHECKING)
            CheckRow("deployed_code", "Depth API", if (c.arcore != ArState.READY) "–" else if (c.depth) "Didukung" else "Tidak didukung",
                c.depth, c.arcore == ArState.CHECKING)
        }
        if (c.arcore != ArState.CHECKING) Card(padding = 14.dp) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ModeChip(c.mode)
            }
            Spacer(Modifier.height(8.dp))
            T(when (c.mode) {
                Mode.AR_FULL -> "Mode terbaik: alas, paket, dan kedalaman dibaca langsung oleh HP."
                Mode.AR_BASIC -> "HP ini tidak punya Depth API. Pengukuran memakai titik fitur ARCore, hasilnya perlu dicek lebih sering."
                Mode.MARKER -> when (c.arcore) {
                    ArState.NEEDS_INSTALL -> "ARCore (Google Play Services for AR) belum terpasang. Pasang sekali dari Play Store, lalu kembali ke sini. " +
                        "Tanpa ARCore, paket diukur dari 1 foto dengan kertas penanda A4."
                    ArState.INSTALL_DECLINED -> "Pemasangan ARCore dibatalkan. Paket diukur dari 1 foto dengan kertas penanda A4 di sampingnya."
                    else -> "HP ini tidak didukung ARCore. Paket diukur dari 1 foto dengan kertas penanda A4 di sampingnya (cetak dari Pengaturan)."
                }
            }, 13.5.sp, color = C.t2)
        }
        Spacer(Modifier.weight(1f))
        if (c.arcore == ArState.NEEDS_INSTALL || c.arcore == ArState.INSTALL_DECLINED)
            PrimaryButton("Pasang ARCore", "download", Modifier.fillMaxWidth()) { model.install(activity) }
        if (c.arcore != ArState.CHECKING)
            SecondaryButton(if (c.arcore == ArState.READY) "Lanjut" else "Lanjut dengan kertas penanda", "arrow_forward", Modifier.fillMaxWidth()) { model.home() }
    }
}

@Composable
private fun CheckRow(icon: String, label: String, value: String, ok: Boolean, busy: Boolean = false) {
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Sym(icon, 20.dp, C.t2)
        T(label, 14.sp, modifier = Modifier.padding(start = 10.dp).width(90.dp), color = C.t2)
        T(value, 14.sp, FontWeight.SemiBold, modifier = Modifier.weight(1f))
        when {
            busy -> CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
            ok -> Sym("check_circle", 20.dp, C.green, filled = true)
            else -> Sym("error", 20.dp, C.amber, filled = true)
        }
    }
}

// ------------------------------------------------------------------ home
@Composable
fun HomeScreen(model: AppModel, activity: Activity) {
    val ms by model.store.measurements.collectAsState()
    val settings by model.store.settings.collectAsState()
    val orders = model.store.orders
    val all = orders.flatMap { it.resi }
    val done = all.count { r -> ms.any { it.resi == r } }
    var typing by remember { mutableStateOf(false) }
    val nextOrder = orders.firstOrNull { o -> o.resi.any { r -> ms.none { it.resi == r } } }

    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            IconTile("deployed_code", Color.White, C.blue, 38.dp)
            Column(Modifier.weight(1f).padding(start = 10.dp)) {
                T("UkurPaket", 16.sp, FontWeight.Bold)
                T("${settings.courier} · Kurir pickup", 12.sp, color = C.t2)
            }
            ModeChip(model.caps.mode)
        }
        LazyColumn(Modifier.weight(1f), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp, 4.dp, 16.dp, 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) {
            item {
                T("Pickup hari ini", 24.sp, FontWeight.Bold)
                T(SimpleDateFormat("EEEE, d MMM", ID).format(Date()) + " · ${orders.size} lokasi · ${all.size} paket", 13.sp, color = C.t2)
                Spacer(Modifier.height(10.dp))
                Row { T("Paket sudah diukur", 12.5.sp, color = C.t2, modifier = Modifier.weight(1f)); T("$done dari ${all.size}", 12.5.sp, FontWeight.SemiBold) }
                Spacer(Modifier.height(6.dp))
                ProgressLine(if (all.isEmpty()) 0f else done.toFloat() / all.size)
            }
            items(orders, key = { it.id }) { o ->
                val measured = o.resi.count { r -> ms.any { it.resi == r } }
                val active = o == nextOrder
                Card(highlight = active) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconTile(when (o.kind) { "home" -> "home"; "warehouse" -> "inventory_2"; else -> "storefront" },
                            if (measured == o.resi.size) C.green else if (active) C.blue else C.t2,
                            if (measured == o.resi.size) C.greenL else if (active) C.blueL else Color(0xFFEEF1F5))
                        Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                            T(o.name, 15.sp, FontWeight.SemiBold)
                            T("${o.address} · ${o.note}", 12.5.sp, color = C.t2, maxLines = 1)
                        }
                        when {
                            measured == o.resi.size -> Chip("Selesai", Tone.OK, "check_circle")
                            active -> Chip("Berikutnya", Tone.BLUE)
                            else -> Chip("$measured/${o.resi.size}", Tone.GREY)
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    o.resi.forEach { r ->
                        val m = ms.lastOrNull { it.resi == r }
                        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp))
                            .clickable { if (m != null) model.go(Screen.Detail(m.id)) else model.startMeasure(r, o.id) }
                            .padding(vertical = 10.dp, horizontal = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            Sym("qr_code_2", 18.dp, C.t3)
                            T(r, 13.5.sp, FontWeight.SemiBold, modifier = Modifier.padding(start = 8.dp).weight(1f))
                            if (m != null) T(m.dims(), 12.5.sp, color = if (m.atHub) C.amber else C.green) else T("Ukur", 12.5.sp, FontWeight.SemiBold, C.blue)
                            Sym("chevron_right", 18.dp, C.t3)
                        }
                    }
                }
            }
        }
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            PrimaryButton("Scan resi", "barcode_scanner", Modifier.weight(1f)) { model.scanResi(activity) }
            SecondaryButton("Ketik", "keyboard", Modifier.width(120.dp)) { typing = true }
        }
        BottomNav(model, Screen.Home)
    }
    if (typing) ResiDialog(onDismiss = { typing = false }) { typing = false; model.openResi(it) }
}

@Composable
private fun ResiDialog(onDismiss: () -> Unit, onOk: (String) -> Unit) {
    var v by remember { mutableStateOf("") }
    AlertDialog(onDismissRequest = onDismiss,
        title = { T("Nomor resi", 18.sp, FontWeight.SemiBold) },
        text = { OutlinedTextField(v, { v = it.uppercase() }, singleLine = true, placeholder = { T("UKP-…", color = C.t3) }) },
        confirmButton = { TextButton(onClick = { if (v.isNotBlank()) onOk(v.trim()) }) { T("Ukur", weight = FontWeight.SemiBold, color = C.blue) } },
        dismissButton = { TextButton(onClick = onDismiss) { T("Batal", color = C.t2) } })
}

@Composable
fun BottomNav(model: AppModel, current: Screen) {
    Row(Modifier.fillMaxWidth().background(Color.White).padding(vertical = 8.dp), horizontalArrangement = Arrangement.SpaceAround) {
        listOf(Triple(Screen.Home, "local_shipping", "Pickup"), Triple(Screen.History, "history", "Riwayat"),
            Triple(Screen.Settings, "settings", "Pengaturan")).forEach { (s, icon, label) ->
            val on = s == current
            Column(Modifier.clip(RoundedCornerShape(12.dp)).clickable { model.tab(s) }.padding(horizontal = 18.dp, vertical = 4.dp),
                horizontalAlignment = Alignment.CenterHorizontally) {
                Sym(icon, 24.dp, if (on) C.blue else C.t3, filled = on)
                T(label, 11.5.sp, FontWeight.Medium, if (on) C.blue else C.t3)
            }
        }
    }
}

// ------------------------------------------------------------------ prep
@Composable
fun PrepScreen(model: AppModel) {
    var dontShow by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        TopBar("Ukur paket", model.draft?.resi, onBack = { model.back() })
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            T("Sebelum mulai", 20.sp, FontWeight.Bold)
            Card(padding = 6.dp) {
                listOf(
                    Triple("inventory_2", "Taruh paket di lantai atau meja", "Bidang datar, jangan di atas paket lain"),
                    Triple("crop_free", "Satu paket, beri jarak ±5 cm", "Paket yang menempel bisa ikut terukur"),
                    Triple("directions_walk", "Mundur sekitar 1 langkah", "Seluruh paket terlihat di layar"),
                    Triple("light_mode", "Tempat cukup terang", "Hindari lantai basah atau sangat mengkilap"),
                ).forEachIndexed { i, (icon, t, s) ->
                    Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                        IconTile(icon)
                        Column(Modifier.padding(start = 12.dp)) { T(t, 14.5.sp, FontWeight.SemiBold); T(s, 12.5.sp, color = C.t2) }
                    }
                    if (i < 3) Box(Modifier.fillMaxWidth().height(1.dp).background(C.line))
                }
            }
            Row(Modifier.clip(RoundedCornerShape(14.dp)).background(C.blueL).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Sym("front_hand", 22.dp, C.blue, filled = true)
                T("Plastik hitam mengkilap atau paket sangat tipis (< 2 cm) lebih sulit dibaca. Kalau hasil kuning, ulangi dari sudut lain.",
                    13.sp, color = Color(0xFF1E3A8A), modifier = Modifier.padding(start = 10.dp))
            }
            Row(Modifier.clickable { dontShow = !dontShow }.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Sym(if (dontShow) "check_circle" else "radio_button_checked", 22.dp, if (dontShow) C.blue else C.t3, filled = dontShow)
                T("Jangan tampilkan lagi", 13.5.sp, color = C.t2, modifier = Modifier.padding(start = 8.dp))
            }
        }
        PrimaryButton("Mulai ukur", "photo_camera", Modifier.fillMaxWidth().padding(16.dp)) {
            if (dontShow) model.store.update { it.copy(prepShown = 99) }
            model.back(); model.go(model.measureScreen())
        }
    }
}

// ------------------------------------------------------------------ weight
@Composable
fun WeightScreen(model: AppModel) {
    val d = model.draft ?: run { model.back(); return }
    val l = d.result?.lengthCm ?: 0.0
    val w = d.result?.widthCm ?: 0.0
    val h = d.result?.heightCm ?: 0.0
    val settingsW by model.store.settings.collectAsState()
    val div = settingsW.divisor
    val volKg = l * w * h / div
    var text by remember { mutableStateOf("") }
    val scale = text.replace(',', '.').toDoubleOrNull()
    val charged = maxOf(volKg, scale ?: 0.0)

    Column(Modifier.fillMaxSize()) {
        TopBar("Berat paket", d.resi, onBack = { model.back() })
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Card {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Photo(d.result?.photo, Modifier.size(58.dp, 80.dp).clip(RoundedCornerShape(10.dp)))
                    Column(Modifier.weight(1f).padding(start = 12.dp)) {
                        T("${l.cm()} × ${w.cm()} × ${h.cm()} cm", 18.sp, FontWeight.Bold)
                        T("Volume ${(l * w * h / 1000).id()} L", 12.5.sp, color = C.t2)
                    }
                    when (d.result?.status) {
                        Status.OK -> Chip("Akurat", Tone.OK, "check_circle")
                        else -> Chip("Cek ulang", Tone.WARN, "warning")
                    }
                }
            }
            T("Berat timbangan (kg)", 13.sp, FontWeight.SemiBold, C.t2)
            OutlinedTextField(text, { v -> text = v.filter { it.isDigit() || it == ',' || it == '.' }.take(7) }, singleLine = true,
                modifier = Modifier.fillMaxWidth(), placeholder = { T("contoh 1,25", color = C.t3) },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                textStyle = androidx.compose.ui.text.TextStyle(fontFamily = Inter, fontSize = 24.sp, fontWeight = FontWeight.Bold))
            T("Boleh dikosongkan kalau tidak ada timbangan.", 12.5.sp, color = C.t3)
            Card {
                WRow("Berat timbangan", scale?.let { "${it.id(2)} kg" } ?: "–")
                WRow("Berat volumetrik", "${volKg.id(2)} kg", "${l.cm()} × ${w.cm()} × ${h.cm()} ÷ ${div.toDouble().id(0)}")
                Spacer(Modifier.height(6.dp))
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(C.greenL).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        T("Berat dipakai", 14.sp, FontWeight.SemiBold)
                        T(if (volKg >= (scale ?: 0.0)) "volumetrik lebih besar" else "timbangan lebih besar", 12.sp, color = C.t2)
                    }
                    T("${charged.id(2)} kg", 22.sp, FontWeight.Bold, C.green)
                }
            }
            T("Pembagi ${div.toDouble().id(0)} bisa diubah di Pengaturan.", 12.sp, color = C.t3)
        }
        PrimaryButton("Simpan", "check", Modifier.fillMaxWidth().padding(16.dp)) { model.save(scale) }
    }
}

@Composable
private fun WRow(label: String, value: String, sub: String? = null) {
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) { T(label, 14.sp); if (sub != null) T(sub, 12.sp, color = C.t3) }
        T(value, 15.sp, FontWeight.SemiBold)
    }
}

// ------------------------------------------------------------------ saved
@Composable
fun SavedScreen(model: AppModel, id: String) {
    val ms by model.store.measurements.collectAsState()
    val m = ms.firstOrNull { it.id == id } ?: run { model.home(); return }
    val order = model.order(m.orderId)
    val next = model.nextInOrder(m.orderId)
    val doneInOrder = order?.resi?.count { r -> ms.any { it.resi == r } } ?: 1
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Column(Modifier.fillMaxWidth().padding(top = 20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(Modifier.size(64.dp).clip(CircleShape).background(C.green), contentAlignment = Alignment.Center) { Sym("check", 40.dp, Color.White, filled = true) }
            Spacer(Modifier.height(12.dp))
            T("Paket tersimpan", 21.sp, FontWeight.Bold)
            T(order?.let { "Paket $doneInOrder dari ${it.resi.size} · ${it.name}" } ?: m.resi, 13.sp, color = C.t2)
        }
        MeasurementCard(m)
        Chip("Tersimpan di HP · siap dikirim saat server diatur", Tone.BLUE, "cloud_upload")
        T(if (m.atHub) "Foto, waktu, lokasi, dan alasan disimpan. Ukuran diisi oleh hub."
          else "Foto, kotak 3D, ukuran, waktu, dan lokasi disimpan sebagai bukti. Angka ukur tidak bisa diedit.", 12.5.sp, color = C.t2)
        if (order != null && order.resi.size > 1) {
            Row { T(order.name, 13.sp, color = C.t2, modifier = Modifier.weight(1f)); T("$doneInOrder dari ${order.resi.size} paket", 13.sp, FontWeight.SemiBold) }
            ProgressLine(doneInOrder.toFloat() / order.resi.size)
        }
        Spacer(Modifier.weight(1f))
        if (next != null) PrimaryButton("Paket berikutnya", "arrow_forward", Modifier.fillMaxWidth()) { model.nextParcel(next, m.orderId) }
        SecondaryButton(if (next != null) "Selesai pickup" else "Kembali ke daftar", null, Modifier.fillMaxWidth()) { model.home() }
    }
}

@Composable
private fun MeasurementCard(m: Measurement) {
    Card {
        Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            Photo(m.photo, Modifier.size(110.dp, 170.dp).clip(RoundedCornerShape(12.dp)))
            Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                KV("Resi", m.resi)
                KV("Ukuran", m.dims())
                if (m.atHub) KV("Alasan", m.note ?: "-")
                else KV("Berat dipakai", "${m.chargedKg.id(2)} kg · ${if (m.volumetricWins) "volumetrik" else "timbangan"}")
                KV("Cara ukur", if (m.atHub) "Diukur di hub" else m.mode.label + " · ${m.confidence}%")
                KV("Waktu & lokasi", SimpleDateFormat("HH:mm", ID).format(Date(m.createdAt)) + " · " + m.place())
            }
        }
    }
}

@Composable
private fun KV(k: String, v: String) {
    Column { T(k, 11.5.sp, color = C.t3); T(v, 14.sp, FontWeight.SemiBold) }
}

// ------------------------------------------------------------------ history & detail
@Composable
fun HistoryScreen(model: AppModel, activity: Activity) {
    val ms by model.store.measurements.collectAsState()
    Column(Modifier.fillMaxSize()) {
        TopBar("Riwayat ukur", "${ms.size} paket di HP ini") {
            Box(Modifier.size(44.dp).clip(CircleShape).clickable {
                model.share(activity, model.store.exportJson(), "application/json", "Bagikan hasil ukur")
            }, contentAlignment = Alignment.Center) { Sym("share", 22.dp, C.ink) }
        }
        if (ms.isEmpty()) Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
            T("Belum ada paket yang diukur.", 14.sp, color = C.t2)
        } else LazyColumn(Modifier.weight(1f), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp, 0.dp, 16.dp, 16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(ms.sortedByDescending { it.createdAt }, key = { it.id }) { m ->
                Card(onClick = { model.go(Screen.Detail(m.id)) }) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Photo(m.photo, Modifier.size(48.dp, 64.dp).clip(RoundedCornerShape(8.dp)))
                        Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                            T(m.resi, 14.sp, FontWeight.SemiBold)
                            T(if (m.atHub) m.dims() else m.dims() + " · ${m.chargedKg.id(2)} kg", 12.5.sp, color = C.t2)
                            T(SimpleDateFormat("d MMM, HH:mm", ID).format(Date(m.createdAt)), 11.5.sp, color = C.t3)
                        }
                        StatusChip(m)
                    }
                }
            }
        }
        BottomNav(model, Screen.History)
    }
}

@Composable
fun DetailScreen(model: AppModel, activity: Activity, id: String) {
    val ms by model.store.measurements.collectAsState()
    val m = ms.firstOrNull { it.id == id } ?: run { model.back(); return }
    var confirm by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        TopBar(m.resi, m.mode.label, onBack = { model.back() })
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Photo(m.photo, Modifier.fillMaxWidth().height(360.dp).clip(RoundedCornerShape(16.dp)))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { StatusChip(m); if (!m.atHub) Chip("Keyakinan ${m.confidence}%", Tone.GREY) }
            T(m.dims(), 28.sp, FontWeight.Bold)
            Card {
                if (!m.atHub) {
                    WRow("Volume", "${m.volumeL.id()} L")
                    WRow("Berat volumetrik", "${m.volumetricKg.id(2)} kg", "÷ ${m.divisor.toDouble().id(0)}")
                    WRow("Berat timbangan", m.scaleKg?.let { "${it.id(2)} kg" } ?: "–")
                    WRow("Berat dipakai", "${m.chargedKg.id(2)} kg")
                    WRow("Waktu ukur", if (m.seconds > 0) "${m.seconds.id(0)} detik" else "–")
                }
                WRow("Waktu", SimpleDateFormat("d MMM yyyy, HH:mm", ID).format(Date(m.createdAt)))
                WRow("Lokasi", if (m.lat != null && m.lon != null) String.format(Locale.US, "%.5f, %.5f", m.lat, m.lon) else "–",
                    m.gpsM?.let { "± ${it.toDouble().id(0)} m" })
                if (m.note != null) WRow(if (m.atHub) "Alasan" else "Catatan", m.note)
            }
            if (m.recording != null) SecondaryButton("Bagikan rekaman scan", "folder_zip", Modifier.fillMaxWidth()) {
                model.share(activity, model.zip(listOf(File(m.recording)), "scan_${m.resi}.zip"), "application/zip", "Bagikan rekaman scan")
            }
        }
        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryButton("Hapus", "delete", Modifier.weight(1f)) { confirm = true }
            PrimaryButton("Ukur ulang", "refresh", Modifier.weight(1.4f)) { model.back(); model.startMeasure(m.resi, m.orderId) }
        }
    }
    if (confirm) AlertDialog(onDismissRequest = { confirm = false },
        title = { T("Hapus hasil ukur?", 18.sp, FontWeight.SemiBold) },
        text = { T("Foto dan rekaman ${m.resi} ikut terhapus dari HP ini.", color = C.t2) },
        confirmButton = { TextButton(onClick = { confirm = false; model.back(); model.store.delete(m.id) }) { T("Hapus", weight = FontWeight.SemiBold, color = C.red) } },
        dismissButton = { TextButton(onClick = { confirm = false }) { T("Batal", color = C.t2) } })
}

// ------------------------------------------------------------------ settings
@Composable
fun SettingsScreen(model: AppModel, activity: Activity) {
    val s by model.store.settings.collectAsState()
    val c = model.caps
    Column(Modifier.fillMaxSize()) {
        TopBar("Pengaturan")
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Card {
                T("HP ini", 15.sp, FontWeight.SemiBold)
                Spacer(Modifier.height(6.dp))
                CheckRow("smartphone", "Model", c.model, true)
                CheckRow("view_in_ar", "ARCore", c.arcore.label, c.arcore == ArState.READY, c.arcore == ArState.CHECKING)
                CheckRow("deployed_code", "Depth API", if (c.depth) "Didukung" else "Tidak didukung", c.depth, c.arcore == ArState.CHECKING)
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    ModeChip(c.mode)
                    Spacer(Modifier.weight(1f))
                    if (c.arcore == ArState.NEEDS_INSTALL || c.arcore == ArState.INSTALL_DECLINED)
                        Chip("Pasang ARCore", Tone.BLUE, "download") { model.install(activity) }
                    else Chip("Periksa ulang", Tone.GREY, "refresh") { model.recheck() }
                }
            }
            Card {
                T("Pembagi berat volumetrik", 15.sp, FontWeight.SemiBold)
                T("P × L × T (cm) ÷ pembagi = berat volumetrik (kg)", 12.5.sp, color = C.t2)
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(4000, 5000, 6000).forEach { v ->
                        Chip(v.toDouble().id(0), if (s.divisor == v) Tone.BLUE else Tone.GREY, if (s.divisor == v) "check" else null) {
                            model.store.update { it.copy(divisor = v) }
                        }
                    }
                }
            }
            Card {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        T("Rekam data scan", 15.sp, FontWeight.SemiBold)
                        T("Untuk uji coba: menyimpan depth, posisi HP, dan foto setiap scan supaya bisa dianalisis di PC. Memakai ±5–20 MB per paket.",
                            12.5.sp, color = C.t2)
                    }
                    Switch(s.record, { v -> model.store.update { it.copy(record = v) } })
                }
            }
            Card {
                T("Kertas penanda (A4)", 15.sp, FontWeight.SemiBold)
                T("Untuk HP tanpa ARCore: paket diukur dari 1 foto dengan kertas ini di sampingnya. Cetak dengan skala 100%, lalu cek garis 10 cm dengan penggaris.",
                    12.5.sp, color = C.t2)
                Spacer(Modifier.height(8.dp))
                SecondaryButton("Bagikan / cetak PDF", "print", Modifier.fillMaxWidth()) { model.markerSheet(activity) }
            }
            Card {
                T("Data", 15.sp, FontWeight.SemiBold)
                Spacer(Modifier.height(8.dp))
                SecondaryButton("Bagikan semua hasil (JSON)", "share", Modifier.fillMaxWidth()) {
                    model.share(activity, model.store.exportJson(), "application/json", "Bagikan hasil ukur")
                }
                Spacer(Modifier.height(8.dp))
                SecondaryButton("Bagikan semua rekaman (ZIP)", "folder_zip", Modifier.fillMaxWidth()) {
                    val dirs = model.store.recordingsDir.listFiles()?.filter { it.isDirectory }.orEmpty()
                    if (dirs.isEmpty()) model.toast("Belum ada rekaman. Aktifkan 'Rekam data scan' lalu ukur paket.")
                    else model.share(activity, model.zip(dirs, "ukurpaket_rekaman.zip"), "application/zip", "Bagikan rekaman")
                }
            }
            T("UkurPaket ${BuildConfigInfo.VERSION} · versi uji coba. Pengukuran berjalan di HP. Hasil ukur dan foto disimpan di HP ini dan hanya keluar kalau Anda membagikannya.",
                12.sp, color = C.t3)
        }
        BottomNav(model, Screen.Settings)
    }
}
