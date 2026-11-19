package id.ukuraja.app

import com.google.mlkit.vision.barcode.common.Barcode
import id.ukuraja.app.scan.Hint
import id.ukuraja.app.scan.ResiReader
import id.ukuraja.app.scan.Seen
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** How the scanner turns barcodes seen frame by frame into one tracking number. */
class ResiReaderTest {
    /** A barcode centred at ([cx], [cy]) of the frame, 0.5 wide and 0.08 tall. */
    private fun code(raw: String, cx: Float = 0.5f, cy: Float = 0.5f, format: Int = Barcode.FORMAT_CODE_128) =
        Seen(raw, format, cx - 0.25f, cy - 0.04f, cx + 0.25f, cy + 0.04f)

    @Test fun code128InTheWindowIsTakenAtOnce() {
        val s = ResiReader().offer(listOf(code("TSA-80745081104")), 0)
        assertEquals("TSA-80745081104", s.resi)
        assertEquals(Hint.DONE, s.hint)
    }

    @Test fun onlyTheBarcodeInTheWindowCountsTheNearestItsMiddle() {
        // a label with the order number above the window and a sorting code low in it
        val order = code("ORD-99120034", cy = 0.2f)
        val sort = code("JKT-BKS-07", cy = 0.62f)
        val resi = code("TSA-80745081104", cy = 0.47f)
        val s = ResiReader().offer(listOf(order, sort, resi), 0)
        assertEquals("TSA-80745081104", s.resi)
        assertEquals(2, s.others.size)
    }

    @Test fun aBarcodeOutsideTheWindowIsNotTaken() {
        val s = ResiReader().offer(listOf(code("TSA-80745081104", cy = 0.15f)), 0)
        assertNull(s.resi)
        assertEquals(Hint.MOVE_INTO_WINDOW, s.hint)
        assertEquals(Hint.AIM, ResiReader().offer(emptyList(), 0).hint)
    }

    @Test fun codesWithoutACheckCharacterMustReadTheSameTwice() {
        val r = ResiReader()
        // ITF: a partial read decodes as a shorter valid code; Codabar and Code 39 likewise have no check digit
        val first = r.offer(listOf(code("80745081", format = Barcode.FORMAT_ITF)), 0)
        assertNull(first.resi); assertEquals(Hint.HOLD, first.hint)
        // a different value next frame starts over
        assertNull(r.offer(listOf(code("8074508110", format = Barcode.FORMAT_ITF)), 100).resi)
        assertEquals("8074508110", r.offer(listOf(code("8074508110", format = Barcode.FORMAT_ITF)), 200).resi)
        // the same value too far apart in time is not a confirmation
        val slow = ResiReader(confirmMs = 1500)
        assertNull(slow.offer(listOf(code("A1234567B", format = Barcode.FORMAT_CODABAR)), 0).resi)
        assertNull(slow.offer(listOf(code("A1234567B", format = Barcode.FORMAT_CODABAR)), 2000).resi)
        assertEquals("A1234567B", slow.offer(listOf(code("A1234567B", format = Barcode.FORMAT_CODABAR)), 2600).resi)
    }

    @Test fun theTextIsCleaned() {
        // Code 128 FNC1 arrives as a group separator; spaces at the ends
        assertEquals("TSA80745081104", ResiReader.clean("\u001DTSA80745081104 "))
        assertNull(ResiReader.clean("https://anteraja.id/track/TSA80745081104"))
        assertNull(ResiReader.clean("12\n34567"))
        assertNull(ResiReader.clean("123"))
        assertNull(ResiReader.clean(null))
        val s = ResiReader().offer(listOf(code("  \u001DTSA-80745081104")), 0)
        assertEquals("TSA-80745081104", s.resi)
    }

    @Test fun onlyLinearFormatsAreAsked() {
        val f = ResiReader.FORMATS.toSet()
        assertTrue(Barcode.FORMAT_CODE_128 in f && Barcode.FORMAT_EAN_13 in f && Barcode.FORMAT_ITF in f)
        listOf(Barcode.FORMAT_QR_CODE, Barcode.FORMAT_DATA_MATRIX, Barcode.FORMAT_PDF417, Barcode.FORMAT_AZTEC).forEach { assertFalse(it in f) }
        assertTrue(ResiReader.CHECKED.all { it in f })
    }
}
