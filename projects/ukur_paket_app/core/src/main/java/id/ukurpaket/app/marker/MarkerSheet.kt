package id.ukurpaket.app.marker

/**
 * The printed marker sheets (tools/marker/make_marker_pdf.py): one ArUco DICT_4X4_50 marker per sheet, its black square
 * [sideMm] across as printed at 100 %. The app lets the courier type the side measured with a ruler instead (a printer
 * that shrinks the page), so [sideMm] is only the default.
 */
enum class MarkerSheet(val id: Int, val label: String, val sideMm: Double) {
    A4(1, "A4", 160.0),
    A3(2, "A3", 240.0);

    companion object {
        val IDS = entries.map { it.id }.toSet()
        fun of(id: Int) = entries.firstOrNull { it.id == id }
    }
}
