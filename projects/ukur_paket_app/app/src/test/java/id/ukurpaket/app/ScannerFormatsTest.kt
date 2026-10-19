package id.ukurpaket.app

import com.google.mlkit.vision.barcode.common.Barcode
import id.ukurpaket.app.ui.AppModel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Scan resi reads linear barcodes only: the QR codes on a label are never read. */
class ScannerFormatsTest {
    @Test fun linearBarcodesOnly() {
        val f = AppModel.LINEAR_BARCODES
        for (twoD in listOf(Barcode.FORMAT_QR_CODE, Barcode.FORMAT_DATA_MATRIX, Barcode.FORMAT_PDF417, Barcode.FORMAT_AZTEC))
            assertFalse("2D format $twoD must not be read", twoD in f)
        assertFalse(Barcode.FORMAT_ALL_FORMATS in f)              // "all formats" would let QR back in
        assertTrue(Barcode.FORMAT_CODE_128 in f)                  // the type on the AnterAja label (BarcodeTest)
        assertEquals(9, f.toSet().size)
    }
}
