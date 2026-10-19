package id.ukurpaket.app.data

import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import id.ukurpaket.app.measure.MarkerSheet
import java.io.File

/**
 * The printable A4 sheet for marker mode, drawn in millimetres: the ring (centre 110 mm from the top) and a
 * 100 mm check bar. Same geometry as tools/marker_sheet.py, which makes docs/kertas_penanda_A4.pdf.
 */
object MarkerPdf {
    const val RING_CENTRE_FROM_TOP_MM = 110f

    fun write(file: File): File {
        val pt = 72f / 25.4f                                  // points per millimetre
        val doc = PdfDocument()
        val page = doc.startPage(PdfDocument.PageInfo.Builder(595, 842, 1).create())
        val c = page.canvas
        c.scale(pt, pt)                                       // draw in millimetres from here on
        val black = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.BLACK; style = Paint.Style.FILL }
        val text = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.BLACK; textSize = 5f; typeface = Typeface.DEFAULT_BOLD }
        val small = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(60, 60, 60); textSize = 3.4f }

        c.drawText("UkurPaket · kertas penanda ukur", 15f, 16f, text)
        c.drawText("Cetak di A4 dengan skala 100% (ukuran asli), jangan \"sesuaikan dengan halaman\".", 15f, 22f, small)

        val cx = 105f; val cy = RING_CENTRE_FROM_TOP_MM
        val o = MarkerSheet.OUTER * 1000 / 2; val i = MarkerSheet.INNER * 1000 / 2
        c.drawRect(cx - o, cy - o, cx + o, cy - i, black)
        c.drawRect(cx - o, cy + i, cx + o, cy + o, black)
        c.drawRect(cx - o, cy - i, cx - i, cy + i, black)
        c.drawRect(cx + i, cy - i, cx + o, cy + i, black)

        // check bar: 100 mm with 10 mm ticks
        val by = 214f; val bx = 55f; val bar = MarkerSheet.CHECK_BAR * 1000
        c.drawRect(bx, by, bx + bar, by + 2f, black)
        for (k in 0..10) c.drawRect(bx + k * 10f - 0.3f, by - (if (k % 5 == 0) 5f else 3f), bx + k * 10f + 0.3f, by, black)
        c.drawText("0", bx - 1.2f, by + 7f, small); c.drawText("10 cm", bx + bar - 4f, by + 7f, small)
        c.drawText("Cek dengan penggaris: garis ini harus tepat 10 cm. Kalau tidak, cetak ulang.", 15f, by + 16f, small)

        val tips = listOf(
            "1. Taruh kertas rata di lantai, di samping paket (boleh menempel, jangan tertutup paket).",
            "2. Foto dari sekitar 1 langkah, HP miring ke bawah ±45°.",
            "3. Kotak hitam dan seluruh paket harus terlihat di foto.",
            "4. Ketuk paket di foto, atau gambar kotak di sekelilingnya.",
        )
        tips.forEachIndexed { k, t -> c.drawText(t, 15f, 252f + k * 6f, small) }
        doc.finishPage(page)
        file.parentFile?.mkdirs()
        file.outputStream().use { doc.writeTo(it) }
        doc.close()
        return file
    }
}
