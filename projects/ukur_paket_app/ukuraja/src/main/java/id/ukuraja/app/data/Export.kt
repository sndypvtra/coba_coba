package id.ukuraja.app.data

import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * The records as a spreadsheet (CSV, semicolon-separated with decimal commas: what Excel and Google Sheets open as
 * columns on an Indonesian-locale computer) and as a ZIP with the evidence photos next to it.
 */
object Export {
    val COLUMNS = listOf(
        "resi", "waktu", "panjang_cm", "lebar_cm", "tinggi_cm", "volume_l", "pembagi", "berat_volumetrik_kg", "berat_aktual_kg",
        "berat_tagih_kg", "status", "skor", "skala", "tinggi_kamera_m", "jumlah_foto", "petugas", "lat", "lon", "akurasi_gps_m",
        "catatan", "foto",
    )

    private val time = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)

    fun csv(ms: List<Measurement>): String {
        val sb = StringBuilder()
        sb.append('﻿')                                   // UTF-8 mark: Excel reads the accents and the dash right
        sb.append(COLUMNS.joinToString(";")).append("\r\n")
        for (m in ms.sortedBy { it.createdAt }) {
            fun d(v: Double?, n: Int) = v?.let { String.format(Locale.US, "%.${n}f", it).replace('.', ',') } ?: ""
            val hub = m.atHub
            val row = listOf(
                m.resi, time.format(Date(m.createdAt)),
                if (hub) "" else d(m.lengthCm, 1), if (hub) "" else d(m.widthCm, 1), if (hub) "" else d(m.heightCm, 1),
                if (hub) "" else d(m.volumeL, 2), m.divisor.toString(), if (hub) "" else d(m.volumetricKg, 2), d(m.scaleKg, 2),
                if (hub) "" else d(m.chargedKg, 2), m.status.label, if (hub) "" else m.confidence.toString(), m.scaleSource ?: "",
                d(m.cameraM, 2), m.photos.toString(), m.operator ?: "", m.lat?.let { String.format(Locale.US, "%.6f", it) } ?: "",
                m.lon?.let { String.format(Locale.US, "%.6f", it) } ?: "", d(m.gpsM?.toDouble(), 0), m.note ?: "",
                m.photo?.let { photoName(m) } ?: "",
            )
            sb.append(row.joinToString(";") { cell(it) }).append("\r\n")
        }
        return sb.toString()
    }

    /** A cell quoted when it holds the separator, a quote or a line break (RFC 4180). */
    fun cell(v: String): String = if (v.any { it == ';' || it == '"' || it == '\n' || it == '\r' }) "\"" + v.replace("\"", "\"\"") + "\"" else v

    /** The evidence photo's name inside the ZIP: resi and time, safe for any file system. */
    fun photoName(m: Measurement): String =
        "foto/" + m.resi.replace(Regex("[^A-Za-z0-9._-]"), "_") + "_" + SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date(m.createdAt)) + ".jpg"

    fun writeCsv(ms: List<Measurement>, out: File): File { out.writeText(csv(ms), Charsets.UTF_8); return out }

    /** CSV + every evidence photo (foto/<resi>_<time>.jpg, the name in the CSV's last column). */
    fun writeZip(ms: List<Measurement>, out: File): File {
        ZipOutputStream(out.outputStream().buffered()).use { z ->
            z.putNextEntry(ZipEntry("ukuraja.csv")); z.write(csv(ms).toByteArray(Charsets.UTF_8)); z.closeEntry()
            val seen = HashSet<String>()
            for (m in ms) {
                val f = m.photo?.let(::File)?.takeIf { it.isFile } ?: continue
                val name = photoName(m); if (!seen.add(name)) continue
                z.putNextEntry(ZipEntry(name)); f.inputStream().use { it.copyTo(z) }; z.closeEntry()
            }
        }
        return out
    }

    /** Folders (photo sessions) into one ZIP, each under its own name: the raw data to analyse on a PC. */
    fun zipDirs(dirs: List<File>, out: File): File {
        ZipOutputStream(out.outputStream().buffered()).use { z ->
            for (d in dirs) d.walkTopDown().filter { it.isFile }.forEach { f ->
                z.putNextEntry(ZipEntry("${d.name}/${f.relativeTo(d).path}"))
                f.inputStream().use { it.copyTo(z) }
                z.closeEntry()
            }
        }
        return out
    }
}
