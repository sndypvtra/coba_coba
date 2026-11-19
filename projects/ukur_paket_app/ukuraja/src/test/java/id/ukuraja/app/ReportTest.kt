package id.ukuraja.app

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import id.ukuraja.app.data.Measurement
import id.ukuraja.app.data.Period
import id.ukuraja.app.data.Report
import id.ukuraja.app.data.ReportInfo
import id.ukuraja.app.data.Status
import id.ukuraja.app.data.Thumbs
import id.ukuraja.app.data.Xlsx
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import org.w3c.dom.Element
import java.io.File
import java.util.Calendar
import java.util.TimeZone
import java.util.zip.ZipFile
import javax.xml.parsers.DocumentBuilderFactory

/** The Excel report: which records, what is in each sheet, the photos, and a file Excel can read. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35])
class ReportTest {
    private val tz: TimeZone = TimeZone.getTimeZone("Asia/Jakarta")
    /** 19 Nov 2026, 15:30 in Jakarta. */
    private val now = Calendar.getInstance(tz).apply { clear(); set(2026, Calendar.NOVEMBER, 19, 15, 30, 0) }.timeInMillis
    private fun at(daysAgo: Int, hour: Int) = Calendar.getInstance(tz).apply {
        clear(); set(2026, Calendar.NOVEMBER, 19 - daysAgo, hour, 5, 0)
    }.timeInMillis

    private fun photo(dir: File, w: Int, h: Int): String {
        val b = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        Canvas(b).drawColor(Color.rgb(185, 139, 90))
        val f = File(dir, "p_${w}x$h.jpg")
        f.outputStream().use { b.compress(Bitmap.CompressFormat.JPEG, 90, it) }
        return f.path
    }

    private fun records(dir: File): List<Measurement> {
        val portrait = photo(dir, 960, 1280)
        return listOf(
            Measurement(resi = "TSA-1", lengthCm = 40.12, widthCm = 30.0, heightCm = 20.0, scaleKg = 2.5, status = Status.OK, confidence = 100,
                photo = portrait, scaleSource = "Marker A4", cameraM = 1.304, createdAt = at(0, 9), operator = "Andi & <Bekasi>",
                lat = -6.2384, lon = 106.9756, gpsM = 8f, note = "kata \"rapuh\"\u0007"),
            Measurement(resi = "807450811040012", lengthCm = 62.0, widthCm = 41.5, heightCm = 35.0, status = Status.CHECK, confidence = 60,
                photo = photo(dir, 1280, 960), scaleSource = "AI (tanpa marker)", cameraM = 1.24, createdAt = at(1, 14), operator = "Andi"),
            Measurement(resi = "TSA-3", lengthCm = 0.0, widthCm = 0.0, heightCm = 0.0, status = Status.HUB, confidence = 0, note = "Bentuk tidak beraturan / lunak",
                photo = portrait, createdAt = at(6, 8), operator = "Budi", lat = -6.24, lon = 106.98),
            // a week ago yesterday: outside the 7 days
            Measurement(resi = "TSA-OLD", lengthCm = 10.0, widthCm = 10.0, heightCm = 10.0, status = Status.OK, confidence = 90, createdAt = at(7, 23)),
        )
    }

    private fun xml(z: ZipFile, name: String): org.w3c.dom.Document {
        val f = DocumentBuilderFactory.newInstance().apply { isNamespaceAware = true }
        return z.getInputStream(z.getEntry(name) ?: error("missing $name")).use { f.newDocumentBuilder().parse(it) }
    }

    /** The cells of a sheet: reference -> text or number (as text). */
    private fun cells(z: ZipFile, sheet: Int): Map<String, String> {
        val d = xml(z, "xl/worksheets/sheet$sheet.xml")
        val out = HashMap<String, String>()
        val cs = d.getElementsByTagName("c")
        for (i in 0 until cs.length) {
            val c = cs.item(i) as Element
            val v = c.getElementsByTagName("t").item(0)?.textContent ?: c.getElementsByTagName("v").item(0)?.textContent ?: continue
            out[c.getAttribute("r")] = v
        }
        return out
    }

    @Test fun periodsAreWholeDaysUpToNow() {
        val ms = records(createTempDir("rep"))
        assertEquals(listOf("TSA-1"), Period.TODAY.of(ms, now, tz).map { it.resi })
        assertEquals(listOf("TSA-3", "807450811040012", "TSA-1"), Period.WEEK.of(ms, now, tz).map { it.resi })
        assertEquals(4, Period.MONTH.of(ms, now, tz).size)
        assertEquals(4, Period.ALL.of(ms, now, tz).size)
        // a record made after the report's moment is not in it
        assertTrue(Period.ALL.of(ms + ms[0].copy(resi = "LATER", createdAt = now + 60_000), now, tz).none { it.resi == "LATER" })
        assertNull(Period.ALL.start(now, tz))
    }

    @Test fun theWorkbookHasFourSheetsAndEveryRecordWithItsPhoto() {
        val dir = createTempDir("rep")
        val ms = records(dir)
        val info = ReportInfo(Period.WEEK, now, "UkurAja 1.0.0", "Urovo DT50", tz)
        assertEquals("UkurAja_7_hari_20261119_1530.xlsx", Report.fileName(info))
        val out = Report.write(ms, info, File(dir, Report.fileName(info))) { Thumbs.of(it.photo) }
        ZipFile(out).use { z ->
            val names = z.entries().toList().map { it.name }
            // every XML part parses (a broken one makes Excel offer to "repair" the file)
            names.filter { it.endsWith(".xml") || it.endsWith(".rels") }.forEach { xml(z, it) }
            val wb = xml(z, "xl/workbook.xml").getElementsByTagName("sheet")
            assertEquals(listOf("Ringkasan", "Data Ukur", "Ukur di Hub", "Keterangan"), (0 until wb.length).map { (wb.item(it) as Element).getAttribute("name") })
            // photos: 3 in Data Ukur (TSA-OLD is outside the period), 1 in Ukur di Hub
            assertEquals(4, names.count { it.startsWith("xl/media/") })
            assertTrue("xl/drawings/drawing2.xml" in names && "xl/drawings/drawing3.xml" in names)
            names.filter { it.startsWith("xl/media/") }.forEach { n ->
                val b = z.getInputStream(z.getEntry(n)).readBytes()
                assertTrue(b.size in 300..60_000 && b[0] == 0xFF.toByte() && b[1] == 0xD8.toByte())   // a small JPEG
            }

            val data = cells(z, 2)
            assertEquals("Identitas", data["A1"]); assertEquals("Resi", data["B2"]); assertEquals("Foto", data["Y2"])
            // oldest first; the long numeric resi stays text (no 8,07E+14)
            assertEquals("TSA-3", data["B3"]); assertEquals("807450811040012", data["B4"]); assertEquals("TSA-1", data["B5"])
            val resiCell = xml(z, "xl/worksheets/sheet2.xml").getElementsByTagName("c").let { cs ->
                (0 until cs.length).map { cs.item(it) as Element }.first { it.getAttribute("r") == "B4" }
            }
            assertEquals("inlineStr", resiCell.getAttribute("t"))
            // a measured parcel: numbers; the volumetric weight wins, so it is the charged one
            assertEquals("40.12", data["F5"]); assertEquals("24.072", data["I5"]); assertEquals("4.02", data["M5"])
            assertEquals("Volumetrik", data["N5"]); assertEquals("Akurat", data["O5"]); assertEquals("Marker A4", data["Q5"])
            assertEquals("Andi & <Bekasi>", data["E5"]); assertEquals("kata \"rapuh\"", data["T5"])   // escaped, the bell dropped
            assertEquals("Buka peta", data["X5"])
            // the hub parcel: no size, no score; its reason in the notes
            assertNull(data["F3"]); assertNull(data["M3"]); assertNull(data["P3"])
            assertEquals("Ukur di Hub", data["O3"]); assertEquals("Bentuk tidak beraturan / lunak", data["T3"])
            // time of day as a fraction: 14:05
            assertEquals(14 + 5 / 60.0, data["D4"]!!.toDouble() * 24, 1e-6)
            // links to the map for the two parcels with a location
            val rels = String(z.getInputStream(z.getEntry("xl/worksheets/_rels/sheet2.xml.rels")).readBytes())
            assertEquals(2, Regex("TargetMode=\"External\"").findAll(rels).count())
            assertTrue(rels.contains("https://www.google.com/maps/search/?api=1&amp;query=-6.238400,106.975600"))
            // the portrait photo fits the cell's height, the landscape one its width
            val drawing = String(z.getInputStream(z.getEntry("xl/drawings/drawing2.xml")).readBytes())
            assertTrue(drawing, drawing.contains("cx=\"${72 * 9525}\" cy=\"${96 * 9525}\""))
            assertTrue(drawing, drawing.contains("cx=\"${100 * 9525}\" cy=\"${75 * 9525}\""))

            val sum = cells(z, 1)
            assertEquals("Laporan Hasil Ukur Paket", sum["A1"])
            assertTrue(sum["A2"]!!, sum["A2"]!!.contains("7 hari terakhir · 13/11/2026 – 19/11/2026"))
            // the labels are in column A, their values beside them in B
            val label = sum.entries.filter { Regex("A\\d+").matches(it.key) }.associate { it.value to it.key }
            fun valueOf(l: String) = sum["B" + label[l]!!.drop(1)]
            assertEquals("Budi, Andi, Andi & <Bekasi>", valueOf("Petugas"))
            assertEquals("Urovo DT50", valueOf("HP")); assertEquals("UkurAja 1.0.0", valueOf("Aplikasi"))
            assertEquals("3", valueOf("Jumlah paket"))
            assertEquals("1", valueOf("Akurat")); assertEquals("1", valueOf("Perlu Dicek")); assertEquals("1", valueOf("Ukur di Hub"))
            assertEquals("1", valueOf("Diukur dengan marker")); assertEquals("1", valueOf("Tanpa marker (skala AI)"))
            assertEquals("2.5", valueOf("Total berat aktual (kg)"))
            // charged: TSA-1 4,02 + the second 15,01 (62 x 41,5 x 35 / 6000 = 15,0092 -> up to 15,01)
            assertEquals(4.02 + 15.01, valueOf("Total berat tagih (kg)")!!.toDouble(), 1e-9)
            assertEquals("Total", sum.entries.first { it.value == "Total" }.value)

            val hub = cells(z, 3)
            assertEquals("TSA-3", hub["B3"]); assertEquals("Bentuk tidak beraturan / lunak", hub["F3"]); assertEquals("Buka peta", hub["H3"])
            assertNull(hub["B4"])

            val legend = cells(z, 4)
            assertEquals(Report.LEGEND.size, legend.keys.count { it.startsWith("A") && it.drop(1).toInt() >= 4 })
            assertFalse(legend.values.any { it.contains("PPN", ignoreCase = true) })
        }
        dir.deleteRecursively()
    }

    @Test fun anEmptyPeriodStillMakesAReadableFile() {
        val dir = createTempDir("rep")
        val out = Report.write(emptyList(), ReportInfo(Period.TODAY, now, "UkurAja 1.0.0", "HP", tz), File(dir, "kosong.xlsx")) { null }
        ZipFile(out).use { z ->
            assertEquals("Tidak ada paket pada periode ini", cells(z, 2)["A3"])
            assertTrue(z.entries().toList().none { it.name.startsWith("xl/media/") })
        }
        dir.deleteRecursively()
    }

    @Test fun cellReferencesDatesAndText() {
        assertEquals(listOf("A", "Z", "AA", "AZ", "ZZ", "AAA"), listOf(0, 25, 26, 51, 701, 702).map(Xlsx::col))
        assertEquals("Y3", Xlsx.ref(2, 24))
        val utc = TimeZone.getTimeZone("UTC")
        assertEquals(25569.0, Xlsx.serial(0, utc), 0.0)                  // 1 Jan 1970
        assertEquals(25570.5, Xlsx.serial(36 * 3_600_000L, utc), 1e-9)
        assertEquals(25569.0 + 7 / 24.0, Xlsx.serial(0, TimeZone.getTimeZone("Asia/Jakarta")), 1e-9)   // the wall clock in Jakarta
        assertEquals("a &amp; b &lt;c&gt; &quot;d&quot; e", Xlsx.esc("a & b <c> \"d\" e\u0001"))
        assertNull(Thumbs.of(null)); assertNull(Thumbs.of("/nope.jpg"))
    }
}
