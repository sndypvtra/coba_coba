package id.ukuraja.app.ui

import android.app.Activity
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukuraja.app.data.Settings
import id.ukuraja.app.data.id
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** One step of the guide: its short title (the step bar), title, what to do, and a few points to remember. */
private class GuideStep(val short: String, val title: String, val text: String, val points: List<String>)

private val STEPS = listOf(
    GuideStep("Siapkan", "Siapkan marker",
        "Cetak marker di kertas A4 atau A3. Ukur kotak hitamnya dengan penggaris: harus sama dengan angka di kertas.",
        listOf("Cetak skala 100% (Actual size), jangan Fit to page", "Laminasi atau tempel di karton supaya tetap rata", "Paket besar atau difoto dari jauh: pakai A3")),
    GuideStep("Taruh", "Taruh di sebelah paket",
        "Letakkan marker rata di lantai atau meja yang sama dengan paket, di sisi yang menghadap Anda, berjarak ±5 cm.",
        listOf("Seluruh kotak hitam terlihat, tidak tertutup apa pun", "Jangan di atas paket, jangan dilipat")),
    GuideStep("Posisi", "Berdiri di pojok paket",
        "Pegang HP setinggi dada dan miringkan ke bawah 30–60°. Dari pojok, dua sisi dan bagian atas paket terlihat.",
        listOf("Jangan memotret dari samping dengan HP tegak", "Jangan terlalu dekat: paket dan marker harus muat di layar")),
    GuideStep("Foto", "Tunggu tiga tanda hijau",
        "Di layar kamera ada tiga tanda: Sudut, HP diam, dan Marker. Setelah ketiganya hijau, tekan Ambil foto lalu tahan HP sebentar.",
        listOf("Lingkaran di tengah layar diarahkan ke paket", "Tempat terang, hindari silau di kertas marker")),
    GuideStep("Ketuk", "Ketuk paketnya",
        "Di foto, ketuk paket yang mau diukur. Paket ditandai warna merah muda, lalu kotak hijau dan ukurannya muncul.",
        listOf("Kalau yang terpilih salah, pakai Tarik kotak di sekeliling paket", "Paket lain di dekatnya beri jarak supaya tidak ikut terpilih")),
    GuideStep("Hasil", "Cek hasilnya",
        "Lihat status di atas ukuran. Baris Skala: Marker A4 berarti ukuran dihitung dari marker, paling tepat.",
        listOf("Akurat: lanjut isi berat dan simpan", "Perlu Dicek: tambah 1–2 foto dari pojok lain", "Tidak bisa diukur: tandai Ukur di Hub")),
)

private val WRONG = listOf("Marker di atas paket", "Marker terlipat atau melengkung", "Paket di meja, marker di lantai", "Marker tertutup paket")

/** The measuring guide: six steps, each with a moving picture; swipe or use the buttons. [startPage]: 0-based. */
@Composable
fun GuideScreen(model: AppModel, activity: Activity, startPage: Int = 0, showWrong: Boolean = false) {
    val s by model.store.settings.collectAsState()
    val pager = rememberPagerState(initialPage = startPage.coerceIn(0, STEPS.lastIndex)) { STEPS.size }
    val scope = rememberCoroutineScope()
    fun done() { if (!s.guideSeen) model.store.update { it.copy(guideSeen = true) }; model.back() }
    Column(Modifier.fillMaxSize()) {
        TopBar("Panduan ukur", "${STEPS.size} langkah · sekitar 1 menit", onBack = { model.back() }) {
            Box(Modifier.clip(RoundedCornerShape(50)).clickable { done() }.padding(horizontal = 12.dp, vertical = 8.dp)) { T("Lewati", 14.sp, FontWeight.SemiBold, C.t2) }
        }
        StepBar(pager.currentPage) { i -> scope.launch { pager.animateScrollToPage(i) } }
        HorizontalPager(pager, Modifier.weight(1f).fillMaxWidth(), beyondViewportPageCount = 0) { page ->
            GuidePage(page, s, model, activity, showWrong)
        }
        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            if (pager.currentPage > 0) SecondaryButton("Kembali", "chevron_left", Modifier.weight(1f)) { scope.launch { pager.animateScrollToPage(pager.currentPage - 1) } }
            val last = pager.currentPage == STEPS.lastIndex
            PrimaryButton(if (last) "Mulai ukur" else "Lanjut", if (last) "check" else "arrow_forward", Modifier.weight(1.4f)) {
                if (last) done() else scope.launch { pager.animateScrollToPage(pager.currentPage + 1) }
            }
        }
    }
}

/** The steps as numbered circles joined by a line: done ones ticked, the current one in brand colour; tap to jump. */
@Composable
private fun StepBar(current: Int, onPick: (Int) -> Unit) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            STEPS.indices.forEach { i ->
                val done = i < current; val on = i == current
                Box(Modifier.size(30.dp).clip(CircleShape).background(if (done || on) C.brand else Color.White)
                    .border(1.5.dp, if (done || on) C.brand else C.line, CircleShape).clickable { onPick(i) }, contentAlignment = Alignment.Center) {
                    if (done) Sym("check", 18.dp, Color.White) else T("${i + 1}", 13.sp, FontWeight.Bold, if (on) Color.White else C.t3)
                }
                if (i < STEPS.lastIndex) Box(Modifier.weight(1f).height(2.dp).background(if (i < current) C.brand else C.line))
            }
        }
        Spacer(Modifier.height(4.dp))
        Row(Modifier.fillMaxWidth()) {
            STEPS.forEachIndexed { i, st ->
                T(st.short, 10.5.sp, if (i == current) FontWeight.SemiBold else FontWeight.Normal, if (i == current) C.brandD else C.t3,
                    modifier = Modifier.weight(1f), maxLines = 1)
            }
        }
    }
}

@Composable
private fun GuidePage(page: Int, s: Settings, model: AppModel, activity: Activity, showWrong: Boolean) {
    val st = STEPS[page]
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        var a3 by remember { mutableStateOf(false) }
        var wrong by remember { mutableStateOf(showWrong) }
        var which by remember { mutableIntStateOf(0) }
        if (page == 1 && wrong && !LocalStill.current) LaunchedEffect(Unit) { while (true) { delay(2600); which = (which + 1) % WRONG.size } }
        Card(padding = 0.dp) {
            val art = Modifier.fillMaxWidth().height(230.dp)
            Box(art.clickable(enabled = page == 1 && wrong) { which = (which + 1) % WRONG.size }) {
                when (page) {
                    0 -> ArtPrint(art, a3)
                    1 -> ArtPlace(art, if (wrong) which else null)
                    2 -> ArtAngle(art)
                    3 -> ArtReady(art)
                    4 -> ArtTap(art)
                    else -> ArtResult(art)
                }
                if (page == 1 && wrong) Row(Modifier.align(Alignment.BottomCenter).padding(10.dp).clip(RoundedCornerShape(50)).background(C.red).padding(horizontal = 12.dp, vertical = 5.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Sym("cancel", 16.dp, Color.White, filled = true)
                    T("${WRONG[which]} · ${which + 1}/${WRONG.size}", 12.5.sp, FontWeight.SemiBold, Color.White, modifier = Modifier.padding(start = 6.dp))
                }
            }
        }
        // a segmented switch under the pictures that have a choice
        if (page == 0) Segmented(listOf("A4 · 16 cm", "A3 · 24 cm"), if (a3) 1 else 0) { a3 = it == 1 }
        if (page == 1) Segmented(listOf("Benar", "Salah"), if (wrong) 1 else 0, listOf(C.green, C.red)) { wrong = it == 1; which = 0 }
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            T("Langkah ${page + 1} dari ${STEPS.size}", 12.5.sp, FontWeight.SemiBold, C.brand)
            T(st.title, 21.sp, FontWeight.Bold)
            T(st.text, 14.5.sp, color = C.t2, lineHeight = 21.sp)
        }
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            st.points.forEach { p ->
                Row(verticalAlignment = Alignment.Top) {
                    Box(Modifier.padding(top = 7.dp).size(6.dp).clip(CircleShape).background(C.brand))
                    T(p, 13.5.sp, color = C.ink, modifier = Modifier.padding(start = 10.dp))
                }
            }
        }
        if (page == 0) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Chip("Cetak A4", Tone.BRAND, "print") { printMarker(activity, model, "A4") }
                Chip("Cetak A3", Tone.BRAND, "print") { printMarker(activity, model, "A3") }
                Chip("Bagikan PDF", Tone.GREY, "share") { model.share(activity, model.markerPdf(if (a3) "A3" else "A4"), "application/pdf", "Marker ${if (a3) "A3" else "A4"}") }
            }
            val a4 = s.markerA4Mm != 160.0; val a3m = s.markerA3Mm != 240.0
            if (a4 || a3m) T("Ukuran tersimpan di Pengaturan: A4 ${(s.markerA4Mm / 10).id(1)} cm · A3 ${(s.markerA3Mm / 10).id(1)} cm.", 12.sp, color = C.t3)
        }
        if (page == 4) Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(C.brandL).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Sym("touch_app", 22.dp, C.brand, filled = true)
            T("Sambil foto diproses, paket sudah bisa diketuk. Hasil keluar begitu proses selesai.", 13.sp, color = C.brandD, modifier = Modifier.padding(start = 10.dp))
        }
        if (page == STEPS.lastIndex) Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(C.yellowL).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            MarkerGlyph(26.dp)
            T("Tanpa marker, UkurAja tetap mengukur dengan AI, tapi hasilnya lebih sering Perlu Dicek.", 13.sp, color = C.onYellow, modifier = Modifier.padding(start = 10.dp))
        }
        Spacer(Modifier.height(4.dp))
    }
}

/** Two or three options as one rounded switch; [colors]: the chosen option's colour per option (brand by default). */
@Composable
private fun Segmented(options: List<String>, selected: Int, colors: List<Color>? = null, onPick: (Int) -> Unit) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Color(0xFFE9EDF2)).padding(3.dp)) {
        options.forEachIndexed { i, o ->
            val on = i == selected; val c = colors?.getOrNull(i) ?: C.brand
            Box(Modifier.weight(1f).clip(RoundedCornerShape(10.dp)).background(if (on) Color.White else Color.Transparent).clickable { onPick(i) }.padding(vertical = 9.dp),
                contentAlignment = Alignment.Center) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (colors != null) { Sym(if (i == 0) "check_circle" else "cancel", 16.dp, if (on) c else C.t3, filled = on); Spacer(Modifier.width(5.dp)) }
                    T(o, 13.5.sp, FontWeight.SemiBold, if (on) (if (colors != null) c else C.ink) else C.t3)
                }
            }
        }
    }
}
