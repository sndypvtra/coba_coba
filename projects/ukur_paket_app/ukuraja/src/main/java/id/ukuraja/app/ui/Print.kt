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
import java.io.File

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
