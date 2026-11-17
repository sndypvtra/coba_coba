package id.ukuraja.app.ui

import android.app.Activity
import android.os.Bundle
import android.os.CancellationSignal
import android.os.ParcelFileDescriptor
import android.print.PageRange
import android.print.PrintAttributes
import android.print.PrintDocumentAdapter
import android.print.PrintDocumentInfo
import android.print.PrintManager
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukuraja.app.data.id
import id.ukurpaket.app.marker.Aruco
import id.ukurpaket.app.marker.MarkerSheet
import java.io.File

/** A small drawing of the A4 sheet's marker (its real pattern), as an icon. */
@Composable
fun MarkerGlyph(size: Dp, id: Int = MarkerSheet.A4.id) {
    Canvas(Modifier.size(size).clip(RoundedCornerShape(size / 8)).background(Color.White).padding(size / 10)) {
        val c = this.size.width / Aruco.GRID
        drawRect(C.ink)
        val code = Aruco.DICT_4X4_50[id]
        for (i in 0 until 4) for (j in 0 until 4) if ((code shr (15 - (i * 4 + j))) and 1 == 1)
            drawRect(Color.White, Offset((j + 1) * c, (i + 1) * c), androidx.compose.ui.geometry.Size(c + 0.5f, c + 0.5f))
    }
}

/** How to print the sheet, check it and lay it next to the parcel; printing straight from the phone. */
@Composable
fun GuideScreen(model: AppModel, activity: Activity) {
    val s by model.store.settings.collectAsState()
    Column(Modifier.fillMaxSize()) {
        TopBar("Panduan marker", "ukuran tepat tanpa kalibrasi", onBack = { model.back() })
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Card(padding = 0.dp) { Scene(Modifier.fillMaxWidth().height(190.dp)) }
            T("Marker adalah kertas bergambar kotak hitam yang ukurannya pasti. Dari kotak itu UkurAja tahu jarak kamera ke lantai dengan tepat, " +
                "jadi panjang, lebar, dan tinggi paket ikut tepat. Tanpa marker, jarak itu ditebak AI dan bisa meleset.", 13.5.sp, color = C.t2)
            Step(1, "print", "Cetak marker", "A4: kotak hitam ${(s.markerA4Mm / 10).id(1).removeSuffix(",0")} cm · A3: ${(s.markerA3Mm / 10).id(1).removeSuffix(",0")} cm. " +
                "Cetak skala 100% (Actual size), jangan Fit to page; kertas doff.") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Chip("Cetak A4", Tone.BRAND, "print") { printMarker(activity, model, "A4") }
                    Chip("Cetak A3", Tone.BRAND, "print") { printMarker(activity, model, "A3") }
                    Chip("Bagikan PDF", Tone.GREY, "share") { model.share(activity, model.markerPdf("A4"), "application/pdf", "Marker A4") }
                }
            }
            Step(2, "straighten", "Cek dengan penggaris", "Ukur sisi kotak hitam. Kalau hasil cetak beda (printer mengecilkan), isi angka hasil ukur di Pengaturan → Marker.") {}
            Step(3, "layers", "Jaga tetap rata", "Jangan dilipat. Tempel di karton tebal atau laminasi doff supaya tidak melengkung dan tidak silau.") {}
            Step(4, "crop_free", "Taruh di sebelah paket", "Rata di lantai atau meja yang sama dengan paket, di sisi yang menghadap kamera, ±5 cm dari paket. Jangan di atas paket.") {}
            Step(5, "photo_camera", "Foto dari pojok paket", "Paket dan seluruh kotak hitam masuk foto. Tunggu chip \"Marker terbaca\" hijau, lalu Ambil foto. " +
                "Dengan marker, foto juga lebih cepat: sapuan fokus tidak perlu.") {}
            Card {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Sym("info", 20.dp, C.t2)
                    T("Tidak bawa marker?", 14.sp, FontWeight.SemiBold, modifier = Modifier.padding(start = 8.dp))
                }
                Spacer(Modifier.height(4.dp))
                T("UkurAja tetap mengukur dengan AI. Setiap foto yang memakai marker juga melatih HP ini, jadi foto tanpa marker ikut makin tepat. " +
                    "Tanpa marker hasilnya lebih sering Perlu Dicek.", 12.5.sp, color = C.t2)
            }
            Spacer(Modifier.height(4.dp))
        }
        PrimaryButton("Mengerti", "check", Modifier.fillMaxWidth().padding(16.dp)) {
            if (!s.guideSeen) model.store.update { it.copy(guideSeen = true) }
            model.back()
        }
    }
}

@Composable
private fun Step(n: Int, icon: String, title: String, text: String, extra: @Composable () -> Unit) {
    Card {
        Row {
            IconTile(icon, size = 36.dp)
            Column(Modifier.padding(start = 12.dp).weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                T("$n. $title", 14.5.sp, FontWeight.SemiBold)
                T(text, 12.5.sp, color = C.t2)
                extra()
            }
        }
    }
}

/** The scene drawn: floor, the parcel, the sheet beside it, the phone at the corner looking down. */
@Composable
private fun Scene(modifier: Modifier) {
    Canvas(modifier.background(Color(0xFFEDF0F4))) {
        val w = size.width; val h = size.height
        // floor in perspective
        val floor = Path().apply { moveTo(w * 0.05f, h * 0.95f); lineTo(w * 0.95f, h * 0.95f); lineTo(w * 0.80f, h * 0.30f); lineTo(w * 0.20f, h * 0.30f); close() }
        drawPath(floor, Color(0xFFD9DEE5))
        // the parcel: an isometric box
        fun p(x: Float, y: Float) = Offset(w * x, h * y)
        val top = Path().apply { moveTo(p(0.52f, 0.30f).x, p(0.52f, 0.30f).y); lineTo(p(0.70f, 0.38f).x, p(0.70f, 0.38f).y); lineTo(p(0.56f, 0.47f).x, p(0.56f, 0.47f).y); lineTo(p(0.38f, 0.39f).x, p(0.38f, 0.39f).y); close() }
        val left = Path().apply { moveTo(p(0.38f, 0.39f).x, p(0.38f, 0.39f).y); lineTo(p(0.56f, 0.47f).x, p(0.56f, 0.47f).y); lineTo(p(0.56f, 0.72f).x, p(0.56f, 0.72f).y); lineTo(p(0.38f, 0.64f).x, p(0.38f, 0.64f).y); close() }
        val right = Path().apply { moveTo(p(0.56f, 0.47f).x, p(0.56f, 0.47f).y); lineTo(p(0.70f, 0.38f).x, p(0.70f, 0.38f).y); lineTo(p(0.70f, 0.63f).x, p(0.70f, 0.63f).y); lineTo(p(0.56f, 0.72f).x, p(0.56f, 0.72f).y); close() }
        drawPath(top, Color(0xFFE9C9A0)); drawPath(left, Color(0xFFD6AD7C)); drawPath(right, Color(0xFFC49663))
        // the green measured box
        for (path in listOf(top, left, right)) drawPath(path, Color(0xFF3CDC3C), style = Stroke(2.dp.toPx()))
        // the sheet on the floor, in front of the parcel, a little apart
        val sheet = Path().apply { moveTo(p(0.17f, 0.70f).x, p(0.17f, 0.70f).y); lineTo(p(0.33f, 0.66f).x, p(0.33f, 0.66f).y); lineTo(p(0.38f, 0.85f).x, p(0.38f, 0.85f).y); lineTo(p(0.20f, 0.90f).x, p(0.20f, 0.90f).y); close() }
        drawPath(sheet, Color.White)
        val sq = Path().apply { moveTo(p(0.200f, 0.715f).x, p(0.200f, 0.715f).y); lineTo(p(0.315f, 0.687f).x, p(0.315f, 0.687f).y); lineTo(p(0.345f, 0.815f).x, p(0.345f, 0.815f).y); lineTo(p(0.222f, 0.848f).x, p(0.222f, 0.848f).y); close() }
        drawPath(sq, C.ink)
        drawPath(sq, C.yellow, style = Stroke(2.5.dp.toPx()))
        val inner = Path().apply { moveTo(p(0.240f, 0.740f).x, p(0.240f, 0.740f).y); lineTo(p(0.278f, 0.731f).x, p(0.278f, 0.731f).y); lineTo(p(0.291f, 0.785f).x, p(0.291f, 0.785f).y); lineTo(p(0.251f, 0.795f).x, p(0.251f, 0.795f).y); close() }
        drawPath(inner, Color.White)
        // the phone above the near corner, its view lines down to the parcel and the sheet
        val phone = p(0.86f, 0.12f)
        drawRoundRect(C.ink, Offset(phone.x - 14.dp.toPx(), phone.y - 22.dp.toPx()), androidx.compose.ui.geometry.Size(28.dp.toPx(), 44.dp.toPx()),
            androidx.compose.ui.geometry.CornerRadius(5.dp.toPx()))
        val dash = PathEffect.dashPathEffect(floatArrayOf(8f, 8f))
        drawLine(C.brand, phone, p(0.56f, 0.60f), 2.dp.toPx(), pathEffect = dash)
        drawLine(C.brand, phone, p(0.27f, 0.78f), 2.dp.toPx(), pathEffect = dash)
    }
}

// ------------------------------------------------------------------ printing
/** The bundled marker PDF to Android's print dialog, at its own size (A4 or A3 page, no scaling). */
fun printMarker(activity: Activity, model: AppModel, sheet: String) {
    val pm = activity.getSystemService(PrintManager::class.java) ?: run { model.toast("HP ini tidak punya layanan cetak. Bagikan PDF-nya."); return }
    val f = runCatching { model.markerPdf(sheet) }.getOrNull() ?: run { model.toast("PDF marker tidak ditemukan"); return }
    val attrs = PrintAttributes.Builder()
        .setMediaSize(if (sheet == "A3") PrintAttributes.MediaSize.ISO_A3 else PrintAttributes.MediaSize.ISO_A4)
        .setColorMode(PrintAttributes.COLOR_MODE_MONOCHROME)
        .setMinMargins(PrintAttributes.Margins.NO_MARGINS)
        .build()
    pm.print("Marker UkurAja $sheet", PdfAdapter(f), attrs)
}

private class PdfAdapter(private val file: File) : PrintDocumentAdapter() {
    override fun onLayout(old: PrintAttributes?, new: PrintAttributes, cancel: CancellationSignal?, cb: LayoutResultCallback, extras: Bundle?) {
        if (cancel?.isCanceled == true) { cb.onLayoutCancelled(); return }
        cb.onLayoutFinished(PrintDocumentInfo.Builder(file.name).setContentType(PrintDocumentInfo.CONTENT_TYPE_DOCUMENT).setPageCount(1).build(), old != new)
    }

    override fun onWrite(pages: Array<out PageRange>, dest: ParcelFileDescriptor, cancel: CancellationSignal?, cb: WriteResultCallback) {
        runCatching { file.inputStream().use { i -> java.io.FileOutputStream(dest.fileDescriptor).use { o -> i.copyTo(o) } } }
            .onSuccess { cb.onWriteFinished(arrayOf(PageRange.ALL_PAGES)) }
            .onFailure { cb.onWriteFailed(it.message) }
    }
}
