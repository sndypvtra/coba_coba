package id.ukuraja.app.data

import id.ukuraja.app.data.Xlsx.Cell
import id.ukuraja.app.data.Xlsx.Style
import java.io.File
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** Which records a report covers: whole days in the phone's time zone, today included. */
enum class Period(val label: String, val days: Int?, val tag: String) {
    TODAY("Hari ini", 1, "hari_ini"),
    WEEK("7 hari terakhir", 7, "7_hari"),
    MONTH("30 hari terakhir", 30, "30_hari"),
    ALL("Semua data", null, "semua");

    /** The first moment counted (midnight [days] - 1 days ago), or null for all. */
    fun start(now: Long, tz: TimeZone = TimeZone.getDefault()): Long? {
        val d = days ?: return null
        return Calendar.getInstance(tz).apply {
            timeInMillis = now
            set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
            add(Calendar.DAY_OF_MONTH, -(d - 1))
        }.timeInMillis
    }

    fun of(ms: List<Measurement>, now: Long, tz: TimeZone = TimeZone.getDefault()): List<Measurement> {
        val from = start(now, tz)
        return ms.filter { (from == null || it.createdAt >= from) && it.createdAt <= now }.sortedBy { it.createdAt }
    }
}

/** A small JPEG of the evidence photo for the sheet, and its size in pixels. */
class Thumb(val jpeg: ByteArray, val w: Int, val h: Int)

/** About the report itself: what the summary sheet says besides the records. */
data class ReportInfo(val period: Period, val now: Long, val app: String, val device: String, val tz: TimeZone = TimeZone.getDefault())

/**
 * The Excel report (.xlsx): four sheets.
 * - **Ringkasan**: the period, who and what, the counts per status, marker use, the weights, and a table per day.
 * - **Data Ukur**: one row per parcel, every field the app keeps, a link to the place on a map and the evidence photo
 *   in the row.
 * - **Ukur di Hub**: the parcels the hub still has to measure, with the reason.
 * - **Keterangan**: what each column and status means.
 */
object Report {
    const val MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    /** The photo in a row: at most this many screen pixels (the cell is sized to it). */
    const val PHOTO_W = 100
    const val PHOTO_H = 96

    fun fileName(info: ReportInfo) =
        "UkurAja_${info.period.tag}_" + java.text.SimpleDateFormat("yyyyMMdd_HHmm", Locale.US).apply { timeZone = info.tz }.format(java.util.Date(info.now)) + ".xlsx"

    fun write(all: List<Measurement>, info: ReportInfo, out: File, thumb: (Measurement) -> Thumb?): File {
        val ms = info.period.of(all, info.now, info.tz)
        val sheets = listOf(summary(ms, info), data(ms, info, thumb), hub(ms, info, thumb), legend())
        out.outputStream().buffered().use { Xlsx.write(sheets, it, "Laporan Hasil Ukur UkurAja", "UkurAja", info.now) }
        return out
    }

    private fun isMarker(m: Measurement) = m.scaleSource?.startsWith("Marker") == true
    private fun statusStyle(s: Status) = when (s) { Status.OK -> Style.OK; Status.CHECK -> Style.CHECK; Status.HUB -> Style.HUB }
    private fun day(ms: Long, tz: TimeZone) = Calendar.getInstance(tz).run {
        timeInMillis = ms; set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0); timeInMillis
    }
    private fun mapsUrl(m: Measurement): String? {
        val la = m.lat ?: return null; val lo = m.lon ?: return null
        return String.format(Locale.US, "https://www.google.com/maps/search/?api=1&query=%.6f,%.6f", la, lo)
    }

    // ------------------------------------------------------------------ Ringkasan
    private fun summary(ms: List<Measurement>, info: ReportInfo): Xlsx.Sheet {
        val s = Xlsx.Sheet("Ringkasan").apply { fitWidth = true }
        listOf(30.0, 16.0, 12.0, 14.0, 14.0, 18.0).forEachIndexed { c, w -> s.width(c, w) }
        val from = info.period.start(info.now, info.tz) ?: day(ms.firstOrNull()?.createdAt ?: info.now, info.tz)
        val d = java.text.SimpleDateFormat("dd/MM/yyyy", Locale.US).apply { timeZone = info.tz }
        s.text(0, 0, "Laporan Hasil Ukur Paket", Style.TITLE); s.height(0, 26.0)
        s.text(1, 0, "UkurAja · ${info.period.label} · ${d.format(java.util.Date(from))} – ${d.format(java.util.Date(info.now))}", Style.SUBTITLE)
        s.merge(0, 0, 5, Style.TITLE); s.merge(1, 0, 5, Style.SUBTITLE)

        var r = 3
        fun section(t: String) { s.text(r, 0, t, Style.SECTION); s.merge(r, 0, 5, Style.SECTION); s.height(r, 20.0); r++ }
        fun pair(label: String, value: Cell, pct: Double? = null) {
            s.text(r, 0, label, Style.LABEL); s.set(r, 1, value)
            if (pct != null) s.num(r, 2, pct, Style.PCT)
            r++
        }
        section("Info laporan")
        pair("Periode", Cell.Text(info.period.label, Style.VALUE))
        pair("Dari tanggal", Cell.Num(Xlsx.serial(from, info.tz), Style.VALUE_DATE))
        pair("Sampai tanggal", Cell.Num(Xlsx.serial(info.now, info.tz), Style.VALUE_DATE))
        pair("Petugas", Cell.Text(ms.mapNotNull { it.operator?.takeIf(String::isNotBlank) }.distinct().joinToString(", ").ifEmpty { "-" }, Style.VALUE))
        pair("Diekspor", Cell.Num(Xlsx.serial(info.now, info.tz), Style.VALUE_DATETIME))
        pair("Aplikasi", Cell.Text(info.app, Style.VALUE))
        pair("HP", Cell.Text(info.device, Style.VALUE))
        pair("Faktor volumetrik (pembagi)", Cell.Text(ms.map { it.divisor }.distinct().sorted().joinToString(", ") { it.toDouble().id(0) }.ifEmpty { "-" }, Style.VALUE))
        r++

        val n = ms.size
        val measured = ms.filter { !it.atHub }
        fun pct(k: Int) = if (n == 0) null else k.toDouble() / n
        section("Ringkasan paket")
        pair("Jumlah paket", Cell.Num(n.toDouble(), Style.VALUE_INT))
        Status.entries.forEach { st ->
            val k = ms.count { it.status == st }
            s.text(r, 0, st.label, Style.LABEL); s.num(r, 1, k.toDouble(), statusStyle(st)); pct(k)?.let { s.num(r, 2, it, Style.PCT) }; r++
        }
        // marker use: a share of the parcels measured from photos (the hub's are not)
        val withMarker = measured.count(::isMarker)
        fun ofMeasured(k: Int) = if (measured.isEmpty()) null else k.toDouble() / measured.size
        pair("Diukur dengan marker", Cell.Num(withMarker.toDouble(), Style.VALUE_INT), ofMeasured(withMarker))
        pair("Tanpa marker (skala AI)", Cell.Num((measured.size - withMarker).toDouble(), Style.VALUE_INT), ofMeasured(measured.size - withMarker))
        pair("Total berat aktual (kg)", Cell.Num(ms.sumOf { it.scaleKg ?: 0.0 }, Style.VALUE_DEC2))
        pair("Total berat volumetrik (kg)", Cell.Num(measured.sumOf { it.volumetricKg }, Style.VALUE_DEC2))
        pair("Total berat tagih (kg)", Cell.Num(measured.sumOf { it.chargedKg }, Style.CHARGED))
        r++

        section("Per hari")
        listOf("Tanggal", "Paket", "Akurat", "Perlu Dicek", "Ukur di Hub", "Berat tagih (kg)").forEachIndexed { c, h -> s.text(r, c, h, Style.HEADER) }
        s.height(r, 20.0); r++
        val days = ms.groupBy { day(it.createdAt, info.tz) }.toSortedMap()
        if (days.isEmpty()) { s.text(r, 0, "Tidak ada paket pada periode ini", Style.TEXT); s.merge(r, 0, 5, Style.TEXT); r++ }
        for ((dayMs, list) in days) {
            s.num(r, 0, Xlsx.serial(dayMs, info.tz), Style.DATE)
            s.num(r, 1, list.size.toDouble(), Style.INT)
            s.num(r, 2, list.count { it.status == Status.OK }.toDouble(), Style.INT)
            s.num(r, 3, list.count { it.status == Status.CHECK }.toDouble(), Style.INT)
            s.num(r, 4, list.count { it.status == Status.HUB }.toDouble(), Style.INT)
            s.num(r, 5, list.filter { !it.atHub }.sumOf { it.chargedKg }, Style.DEC2)
            r++
        }
        if (days.size > 1) {
            s.text(r, 0, "Total", Style.TOTAL)
            s.num(r, 1, n.toDouble(), Style.TOTAL_INT)
            listOf(Status.OK, Status.CHECK, Status.HUB).forEachIndexed { i, st -> s.num(r, 2 + i, ms.count { it.status == st }.toDouble(), Style.TOTAL_INT) }
            s.num(r, 5, measured.sumOf { it.chargedKg }, Style.TOTAL_DEC2)
        }
        return s
    }

    // ------------------------------------------------------------------ Data Ukur
    /** The columns of Data Ukur: group, header, width (characters). */
    val DATA_COLUMNS = listOf(
        Triple("Identitas", "No", 5.0), Triple("Identitas", "Resi", 22.0), Triple("Identitas", "Tanggal", 11.0),
        Triple("Identitas", "Jam", 7.0), Triple("Identitas", "Petugas", 18.0),
        Triple("Ukuran", "Panjang (cm)", 9.0), Triple("Ukuran", "Lebar (cm)", 9.0), Triple("Ukuran", "Tinggi (cm)", 9.0),
        Triple("Ukuran", "Volume (L)", 10.0),
        Triple("Berat", "Berat aktual (kg)", 11.0), Triple("Berat", "Pembagi", 9.0), Triple("Berat", "Berat volumetrik (kg)", 12.0),
        Triple("Berat", "Berat tagih (kg)", 11.0), Triple("Berat", "Dasar tagih", 12.0),
        Triple("Kualitas", "Status", 13.0), Triple("Kualitas", "Skor", 7.0), Triple("Kualitas", "Sumber skala", 24.0),
        Triple("Kualitas", "Tinggi kamera (m)", 10.0), Triple("Kualitas", "Jumlah foto", 8.0), Triple("Kualitas", "Catatan", 30.0),
        Triple("Lokasi", "Lat", 11.0), Triple("Lokasi", "Lon", 11.0), Triple("Lokasi", "Akurasi GPS (m)", 9.0), Triple("Lokasi", "Peta", 12.0),
        Triple("Bukti", "Foto", 15.0),
    )

    /** The group band (row 0), the headers (row 1), widths, frozen panes, the filter and printing, for a record table. */
    private fun table(s: Xlsx.Sheet, cols: List<Triple<String, String, Double>>, freezeCols: Int) {
        cols.forEachIndexed { c, (_, h, w) -> s.width(c, w); s.text(1, c, h, Style.HEADER) }
        var c0 = 0
        while (c0 < cols.size) {
            var c1 = c0; while (c1 + 1 < cols.size && cols[c1 + 1].first == cols[c0].first) c1++
            s.text(0, c0, cols[c0].first, Style.BAND); if (c1 > c0) s.merge(0, c0, c1, Style.BAND)
            c0 = c1 + 1
        }
        s.height(0, 18.0); s.height(1, 46.0)          // three lines of a wrapped header
        s.freezeRows = 2; s.freezeCols = freezeCols
        s.filter = Triple(1, 0, cols.size - 1)
        s.landscape = true; s.fitWidth = true; s.printTitleRows = 0..1
    }

    /** The evidence photo placed in [r]:[c], fitted inside the cell; the row is made tall enough. */
    private fun photo(s: Xlsx.Sheet, r: Int, c: Int, m: Measurement, thumb: (Measurement) -> Thumb?): Boolean {
        val t = runCatching { thumb(m) }.getOrNull() ?: return false
        if (t.w <= 0 || t.h <= 0) return false
        val k = min(PHOTO_W.toDouble() / t.w, PHOTO_H.toDouble() / t.h)
        val w = max(1, (t.w * k).roundToInt()); val h = max(1, (t.h * k).roundToInt())
        s.picture(Xlsx.Picture(r, c, t.jpeg, w, h, "Foto ${m.resi}"))
        s.height(r, (PHOTO_H + 2 * Xlsx.INSET + 2) * 0.75)    // pixels to points
        return true
    }

    private fun data(ms: List<Measurement>, info: ReportInfo, thumb: (Measurement) -> Thumb?): Xlsx.Sheet {
        val s = Xlsx.Sheet("Data Ukur")
        table(s, DATA_COLUMNS, freezeCols = 2)
        val photoCol = DATA_COLUMNS.size - 1
        ms.forEachIndexed { i, m ->
            val r = i + 2
            val hub = m.atHub
            s.num(r, 0, (i + 1).toDouble(), Style.INT)
            s.text(r, 1, m.resi)
            s.num(r, 2, Xlsx.serial(day(m.createdAt, info.tz), info.tz), Style.DATE)
            s.num(r, 3, Xlsx.serial(m.createdAt, info.tz) % 1.0, Style.TIME)
            s.text(r, 4, m.operator)
            s.num(r, 5, if (hub) null else m.lengthCm, Style.DEC1)
            s.num(r, 6, if (hub) null else m.widthCm, Style.DEC1)
            s.num(r, 7, if (hub) null else m.heightCm, Style.DEC1)
            s.num(r, 8, if (hub) null else m.volumeL, Style.DEC2)
            s.num(r, 9, m.scaleKg, Style.DEC2)
            s.num(r, 10, m.divisor.toDouble(), Style.INT)
            s.num(r, 11, if (hub) null else m.volumetricKg, Style.DEC2)
            s.num(r, 12, if (hub) null else m.chargedKg, Style.CHARGED)
            s.text(r, 13, if (hub) null else if (m.volumetricWins) "Volumetrik" else "Aktual", Style.TEXT_CENTER)
            s.text(r, 14, m.status.label, statusStyle(m.status))
            s.num(r, 15, if (hub) null else m.confidence.toDouble(), Style.INT)
            s.text(r, 16, m.scaleSource, Style.TEXT_WRAP)
            s.num(r, 17, m.cameraM, Style.DEC2)
            s.num(r, 18, if (hub) null else m.photos.toDouble(), Style.INT)
            s.text(r, 19, m.note, Style.TEXT_WRAP)
            s.num(r, 20, m.lat, Style.DEC6)
            s.num(r, 21, m.lon, Style.DEC6)
            s.num(r, 22, m.gpsM?.toDouble(), Style.INT)
            mapsUrl(m)?.let { s.set(r, 23, Cell.Link("Buka peta", it)) } ?: s.text(r, 23, null, Style.TEXT_CENTER)
            s.text(r, photoCol, null, Style.TEXT_CENTER)
            if (!photo(s, r, photoCol, m, thumb)) s.text(r, photoCol, "Tidak ada foto", Style.TEXT_CENTER)
        }
        if (ms.isEmpty()) { s.text(2, 0, "Tidak ada paket pada periode ini", Style.TEXT); s.merge(2, 0, 6, Style.TEXT) }
        return s
    }

    // ------------------------------------------------------------------ Ukur di Hub
    val HUB_COLUMNS = listOf(
        Triple("Paket", "No", 5.0), Triple("Paket", "Resi", 22.0), Triple("Paket", "Tanggal", 11.0), Triple("Paket", "Jam", 7.0),
        Triple("Paket", "Petugas", 18.0), Triple("Paket", "Alasan", 34.0), Triple("Paket", "Berat aktual (kg)", 11.0),
        Triple("Lokasi", "Peta", 12.0), Triple("Bukti", "Foto", 15.0),
    )

    private fun hub(ms: List<Measurement>, info: ReportInfo, thumb: (Measurement) -> Thumb?): Xlsx.Sheet {
        val s = Xlsx.Sheet("Ukur di Hub")
        table(s, HUB_COLUMNS, freezeCols = 2)
        val list = ms.filter { it.atHub }
        list.forEachIndexed { i, m ->
            val r = i + 2
            s.num(r, 0, (i + 1).toDouble(), Style.INT)
            s.text(r, 1, m.resi)
            s.num(r, 2, Xlsx.serial(day(m.createdAt, info.tz), info.tz), Style.DATE)
            s.num(r, 3, Xlsx.serial(m.createdAt, info.tz) % 1.0, Style.TIME)
            s.text(r, 4, m.operator)
            s.text(r, 5, m.note, Style.TEXT_WRAP)
            s.num(r, 6, m.scaleKg, Style.DEC2)
            mapsUrl(m)?.let { s.set(r, 7, Cell.Link("Buka peta", it)) } ?: s.text(r, 7, null, Style.TEXT_CENTER)
            s.text(r, 8, null, Style.TEXT_CENTER)
            if (!photo(s, r, 8, m, thumb)) s.text(r, 8, "Tidak ada foto", Style.TEXT_CENTER)
        }
        if (list.isEmpty()) { s.text(2, 0, "Tidak ada paket untuk diukur di hub pada periode ini", Style.TEXT); s.merge(2, 0, 5, Style.TEXT) }
        return s
    }

    // ------------------------------------------------------------------ Keterangan
    val LEGEND = listOf(
        "No" to "Nomor urut paket dalam laporan, dari yang paling awal diukur.",
        "Resi" to "Nomor resi dari barcode label, atau yang diketik petugas.",
        "Tanggal, Jam" to "Waktu paket diukur, menurut jam HP.",
        "Petugas" to "Nama petugas di Pengaturan saat paket diukur.",
        "Panjang, Lebar, Tinggi (cm)" to "Ukuran kotak paket dari foto. Kosong untuk paket Ukur di Hub.",
        "Volume (L)" to "Panjang × Lebar × Tinggi ÷ 1.000.",
        "Berat aktual (kg)" to "Berat dari timbangan, kalau diisi petugas.",
        "Pembagi" to "Faktor volumetrik yang dipakai: 4.000, 5.000 atau 6.000.",
        "Berat volumetrik (kg)" to "Panjang × Lebar × Tinggi (cm) ÷ pembagi.",
        "Berat tagih (kg)" to "Yang lebih besar antara berat aktual dan berat volumetrik, dibulatkan ke atas per 0,01 kg.",
        "Dasar tagih" to "Berat mana yang dipakai untuk berat tagih: Aktual atau Volumetrik.",
        "Status: Akurat" to "Ukuran dari foto bisa langsung dipakai.",
        "Status: Perlu Dicek" to "Ukuran perlu diperiksa ulang sebelum dipakai (lihat Catatan).",
        "Status: Ukur di Hub" to "Paket tidak diukur di lapangan; hub yang mengukur. Daftarnya ada di sheet Ukur di Hub.",
        "Skor" to "Keyakinan aplikasi pada ukuran ini, 0–100.",
        "Sumber skala" to "Marker A4 / Marker A3: skala dari kertas marker di foto (paling tepat). " +
            "AI + skala dari foto marker: tanpa marker, skala dari AI yang sudah belajar dari foto marker sebelumnya. " +
            "AI (tanpa marker): skala hanya dari perkiraan AI.",
        "Tinggi kamera (m)" to "Tinggi HP dari lantai saat memotret, yang dipakai untuk menghitung ukuran.",
        "Jumlah foto" to "Banyaknya foto (dari pojok berbeda) yang digabung untuk ukuran ini.",
        "Catatan" to "Catatan dari aplikasi tentang hasil ukur, atau alasan paket diukur di hub.",
        "Lat, Lon" to "Lokasi saat paket diukur, kalau izin lokasi diberikan.",
        "Akurasi GPS (m)" to "Ketelitian lokasi dalam meter: makin kecil makin tepat.",
        "Peta" to "Klik untuk membuka lokasi di Google Maps.",
        "Foto" to "Foto bukti: paket dengan kotak ukur hijau, dan marker bergaris kuning kalau ada.",
    )

    private fun legend(): Xlsx.Sheet {
        val s = Xlsx.Sheet("Keterangan").apply { fitWidth = true }
        s.width(0, 28.0); s.width(1, 90.0)
        s.text(0, 0, "Keterangan kolom", Style.TITLE); s.merge(0, 0, 1, Style.TITLE); s.height(0, 26.0)
        s.text(2, 0, "Kolom", Style.HEADER); s.text(2, 1, "Arti", Style.HEADER); s.height(2, 20.0)
        LEGEND.forEachIndexed { i, (k, v) -> s.text(3 + i, 0, k, Style.VALUE); s.text(3 + i, 1, v, Style.TEXT_WRAP) }
        s.freezeRows = 3
        return s
    }
}
