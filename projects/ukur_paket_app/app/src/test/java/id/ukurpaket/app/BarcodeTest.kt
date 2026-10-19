package id.ukurpaket.app

import com.google.zxing.BarcodeFormat
import com.google.zxing.BinaryBitmap
import com.google.zxing.DecodeHintType
import com.google.zxing.MultiFormatReader
import com.google.zxing.RGBLuminanceSource
import com.google.zxing.common.HybridBinarizer
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Scan resi reads the label's barcode as it is. The barcode image is cut from a photo of a real AnterAja label (bars only: no name,
 * address or phone number), straightened; on the label it sits next to "Nomor Pengiriman TSA-80745081104".
 * The phone reads it with Google's code scanner; this test uses ZXing, the open-source reader, on the same bars.
 */
class BarcodeTest {
    @Test fun theLabelBarcodeHoldsTheTrackingNumber() {
        val img = TestImages.read(javaClass.getResourceAsStream("/label/anteraja_barcode.png")!!)
        val bitmap = BinaryBitmap(HybridBinarizer(RGBLuminanceSource(img.w, img.h, sharpened(img))))
        val r = MultiFormatReader().decode(bitmap, mapOf(DecodeHintType.TRY_HARDER to true,
            DecodeHintType.POSSIBLE_FORMATS to listOf(BarcodeFormat.CODE_128)))
        assertEquals(BarcodeFormat.CODE_128, r.barcodeFormat)
        assertEquals("TSA-80745081104", r.text)
    }

    /** The photo is soft (a screenshot of a phone photo): a light unsharp mask across the bars, as scanners do. */
    private fun sharpened(img: TestImages.Argb): IntArray {
        val g = IntArray(img.px.size) { (img.px[it] shr 8) and 255 }
        return IntArray(g.size) { i ->
            val x = i % img.w; var sum = 0
            for (d in -4..4) sum += g[i - x + (x + d).coerceIn(0, img.w - 1)]
            val v = (g[i] + 1.5 * (g[i] - sum / 9.0)).toInt().coerceIn(0, 255)
            (0xFF shl 24) or (v shl 16) or (v shl 8) or v
        }
    }
}
