package id.ukuraja.app.data

import java.io.OutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * A small Office Open XML spreadsheet (.xlsx) writer, written by hand so the APK carries no spreadsheet library.
 * It covers what the report needs:
 * - text, numbers, dates and links in cells, with a fixed set of [Style]s;
 * - column widths, row heights and merged cells;
 * - frozen header rows and columns, and the header's filter;
 * - landscape printing at page width, with the header repeated on each page;
 * - JPEG pictures placed in cells.
 * Excel, LibreOffice, Google Sheets and WPS open it.
 */
object Xlsx {
    data class Font(val bold: Boolean = false, val color: String = "FF0F172A", val size: Int = 11, val underline: Boolean = false)

    /** Every cell look the report uses; the order is the index in styles.xml (NORMAL first: Excel's default). */
    enum class Style(val numFmt: Int = 0, val font: Font = Font(), val fill: String? = null, val border: Boolean = false,
                     val h: String? = null, val wrap: Boolean = false) {
        NORMAL,
        TITLE(font = Font(bold = true, size = 16, color = "FFB0005A")),
        SUBTITLE(font = Font(color = "FF475569")),
        SECTION(font = Font(bold = true, size = 12), fill = "FFF1F5F9"),
        LABEL(font = Font(color = "FF475569"), border = true),
        VALUE(font = Font(bold = true), border = true, h = "left"),
        VALUE_INT(1, Font(bold = true), border = true, h = "left"),
        VALUE_DEC2(2, Font(bold = true), border = true, h = "left"),
        VALUE_DATE(164, Font(bold = true), border = true, h = "left"),
        VALUE_DATETIME(168, Font(bold = true), border = true, h = "left"),
        BAND(font = Font(bold = true, color = "FF0F172A"), fill = "FFFDE8F2", border = true, h = "center"),
        HEADER(font = Font(bold = true, color = "FFFFFFFF"), fill = "FF1E293B", border = true, h = "center", wrap = true),
        TEXT(border = true),
        TEXT_WRAP(border = true, wrap = true),
        TEXT_CENTER(border = true, h = "center"),
        INT(1, border = true, h = "center"),
        DEC1(166, border = true),
        DEC2(2, border = true),
        DEC6(167, border = true),
        PCT(9, border = true, h = "center"),
        DATE(164, border = true, h = "center"),
        TIME(165, border = true, h = "center"),
        CHARGED(2, Font(bold = true), fill = "FFFFF6D6", border = true),
        OK(font = Font(bold = true, color = "FF166534"), fill = "FFDCFCE7", border = true, h = "center"),
        CHECK(font = Font(bold = true, color = "FF854D0E"), fill = "FFFEF9C3", border = true, h = "center"),
        HUB(font = Font(bold = true, color = "FF9A3412"), fill = "FFFFEDD5", border = true, h = "center"),
        LINK(font = Font(color = "FF1D4ED8", underline = true), border = true, h = "center"),
        TOTAL(font = Font(bold = true), fill = "FFF1F5F9", border = true),
        TOTAL_INT(1, Font(bold = true), fill = "FFF1F5F9", border = true, h = "center"),
        TOTAL_DEC2(2, Font(bold = true), fill = "FFF1F5F9", border = true),
    }

    sealed class Cell {
        abstract val style: Style
        data class Text(val text: String, override val style: Style = Style.TEXT) : Cell()
        data class Num(val value: Double, override val style: Style) : Cell()
        data class Link(val text: String, val url: String, override val style: Style = Style.LINK) : Cell()
        /** A styled cell with nothing in it (inside a merged range, or a bordered blank). */
        data class Blank(override val style: Style) : Cell()
    }

    /** A JPEG placed in a cell, [w] x [h] screen pixels, inset a few pixels from its top-left corner. */
    class Picture(val row: Int, val col: Int, val jpeg: ByteArray, val w: Int, val h: Int, val name: String)

    class Sheet(val name: String) {
        internal val cells = sortedMapOf<Int, java.util.SortedMap<Int, Cell>>()
        internal val widths = sortedMapOf<Int, Double>()
        internal val heights = HashMap<Int, Double>()
        internal val merges = ArrayList<String>()
        internal val pictures = ArrayList<Picture>()
        /** Frozen: this many columns at the left and rows at the top. */
        var freezeCols = 0
        var freezeRows = 0
        /** The filter on a header row (0-based) over these columns. */
        var filter: Triple<Int, Int, Int>? = null
        var landscape = false
        /** Printed as wide as one page (as many pages down as needed). */
        var fitWidth = false
        /** Rows (0-based, inclusive) repeated at the top of every printed page. */
        var printTitleRows: IntRange? = null

        fun set(r: Int, c: Int, cell: Cell) { cells.getOrPut(r) { sortedMapOf() }[c] = cell }
        fun text(r: Int, c: Int, s: String?, style: Style = Style.TEXT) = set(r, c, if (s.isNullOrEmpty()) Cell.Blank(style) else Cell.Text(s, style))
        fun num(r: Int, c: Int, v: Double?, style: Style) =
            set(r, c, if (v == null || v.isNaN() || v.isInfinite()) Cell.Blank(style) else Cell.Num(v, style))
        fun width(c: Int, chars: Double) { widths[c] = chars }
        fun height(r: Int, points: Double) { heights[r] = points }
        /** Merges [r]:[c0]..[c1]; the first cell holds the content, the others carry its style. */
        fun merge(r: Int, c0: Int, c1: Int, style: Style) {
            for (c in c0 + 1..c1) if (cells[r]?.get(c) == null) set(r, c, Cell.Blank(style))
            merges += "${ref(r, c0)}:${ref(r, c1)}"
        }
        fun picture(p: Picture) { pictures += p }
        val lastRow get() = cells.keys.lastOrNull() ?: 0
    }

    // ------------------------------------------------------------------ helpers
    /** "A", "B", ... "Z", "AA"... for a 0-based column. */
    fun col(c: Int): String {
        var n = c + 1; val sb = StringBuilder()
        while (n > 0) { val m = (n - 1) % 26; sb.append('A' + m); n = (n - 1) / 26 }
        return sb.reverse().toString()
    }

    fun ref(r: Int, c: Int) = col(c) + (r + 1)

    /** Excel's day number for a moment, in the phone's time zone (dates in a sheet have no zone). */
    fun serial(ms: Long, tz: TimeZone = TimeZone.getDefault()): Double = (ms + tz.getOffset(ms)) / 86_400_000.0 + 25569.0

    /** Text safe inside XML: the five entities escaped, characters XML forbids dropped. */
    fun esc(s: String): String {
        val sb = StringBuilder(s.length + 16)
        for (ch in s) when {
            ch == '&' -> sb.append("&amp;")
            ch == '<' -> sb.append("&lt;")
            ch == '>' -> sb.append("&gt;")
            ch == '"' -> sb.append("&quot;")
            ch == '\'' -> sb.append("&apos;")
            ch == '\t' || ch == '\n' || ch == '\r' -> sb.append(ch)
            ch < ' ' || ch == '￾' || ch == '￿' -> Unit
            else -> sb.append(ch)
        }
        return sb.toString()
    }

    /** Excel's column width (characters of the default font) as screen pixels: 7 px per character and 5 px padding. */
    fun widthPx(chars: Double) = (chars * 7 + 5).toInt()

    private const val EMU = 9525L   // per screen pixel at 96 dpi
    private const val NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    private const val NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    private const val NS_PR = "http://schemas.openxmlformats.org/package/2006/relationships"
    private const val HEAD = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"

    // ------------------------------------------------------------------ writing
    fun write(sheets: List<Sheet>, out: OutputStream, title: String, creator: String, now: Long = System.currentTimeMillis()) {
        require(sheets.isNotEmpty())
        val withPics = sheets.withIndex().filter { it.value.pictures.isNotEmpty() }
        ZipOutputStream(out).use { z ->
            fun put(name: String, text: String) { z.putNextEntry(ZipEntry(name)); z.write(text.toByteArray(Charsets.UTF_8)); z.closeEntry() }

            put("[Content_Types].xml", HEAD + "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">" +
                "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>" +
                "<Default Extension=\"xml\" ContentType=\"application/xml\"/>" +
                "<Default Extension=\"jpeg\" ContentType=\"image/jpeg\"/>" +
                "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>" +
                "<Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>" +
                sheets.indices.joinToString("") { "<Override PartName=\"/xl/worksheets/sheet${it + 1}.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>" } +
                withPics.joinToString("") { "<Override PartName=\"/xl/drawings/drawing${it.index + 1}.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.drawing+xml\"/>" } +
                "<Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>" +
                "<Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>" +
                "</Types>")
            put("_rels/.rels", HEAD + "<Relationships xmlns=\"$NS_PR\">" +
                "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>" +
                "<Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\"/>" +
                "<Relationship Id=\"rId3\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties\" Target=\"docProps/app.xml\"/>" +
                "</Relationships>")
            val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply { timeZone = TimeZone.getTimeZone("UTC") }.format(Date(now))
            put("docProps/core.xml", HEAD + "<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" " +
                "xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:dcterms=\"http://purl.org/dc/terms/\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">" +
                "<dc:title>${esc(title)}</dc:title><dc:creator>${esc(creator)}</dc:creator>" +
                "<dcterms:created xsi:type=\"dcterms:W3CDTF\">$iso</dcterms:created><dcterms:modified xsi:type=\"dcterms:W3CDTF\">$iso</dcterms:modified>" +
                "</cp:coreProperties>")
            put("docProps/app.xml", HEAD + "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\"><Application>${esc(creator)}</Application></Properties>")

            // workbook: the sheets, the filter ranges and the printed header rows
            val names = StringBuilder()
            sheets.forEachIndexed { i, s ->
                val q = "'" + s.name.replace("'", "''") + "'"
                s.filter?.let { (r, c0, c1) ->
                    names.append("<definedName name=\"_xlnm._FilterDatabase\" localSheetId=\"$i\" hidden=\"1\">")
                        .append(esc("$q!\$${col(c0)}\$${r + 1}:\$${col(c1)}\$${maxOf(r + 1, s.lastRow + 1)}")).append("</definedName>")
                }
                s.printTitleRows?.let { rows ->
                    names.append("<definedName name=\"_xlnm.Print_Titles\" localSheetId=\"$i\">").append(esc("$q!\$${rows.first + 1}:\$${rows.last + 1}")).append("</definedName>")
                }
            }
            put("xl/workbook.xml", HEAD + "<workbook xmlns=\"$NS\" xmlns:r=\"$NS_R\"><bookViews><workbookView activeTab=\"0\"/></bookViews><sheets>" +
                sheets.withIndex().joinToString("") { (i, s) -> "<sheet name=\"${esc(s.name)}\" sheetId=\"${i + 1}\" r:id=\"rId${i + 1}\"/>" } +
                "</sheets>" + (if (names.isNotEmpty()) "<definedNames>$names</definedNames>" else "") + "<calcPr calcId=\"191029\"/></workbook>")
            put("xl/_rels/workbook.xml.rels", HEAD + "<Relationships xmlns=\"$NS_PR\">" +
                sheets.indices.joinToString("") { "<Relationship Id=\"rId${it + 1}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet${it + 1}.xml\"/>" } +
                "<Relationship Id=\"rId${sheets.size + 1}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/>" +
                "</Relationships>")
            put("xl/styles.xml", styles())

            var image = 0
            sheets.forEachIndexed { i, s ->
                val links = ArrayList<Pair<String, String>>()   // cell ref -> url
                put("xl/worksheets/sheet${i + 1}.xml", sheetXml(s, i == 0, links))
                val rels = StringBuilder()
                if (s.pictures.isNotEmpty()) rels.append("<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing\" Target=\"../drawings/drawing${i + 1}.xml\"/>")
                links.forEachIndexed { k, (_, url) ->
                    rels.append("<Relationship Id=\"rId${k + 2}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink\" Target=\"${esc(url)}\" TargetMode=\"External\"/>")
                }
                if (rels.isNotEmpty()) put("xl/worksheets/_rels/sheet${i + 1}.xml.rels", HEAD + "<Relationships xmlns=\"$NS_PR\">$rels</Relationships>")
                if (s.pictures.isNotEmpty()) {
                    val dr = StringBuilder(); val drRels = StringBuilder()
                    s.pictures.forEachIndexed { k, p ->
                        image++
                        z.putNextEntry(ZipEntry("xl/media/image$image.jpeg")); z.write(p.jpeg); z.closeEntry()
                        drRels.append("<Relationship Id=\"rId${k + 1}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image\" Target=\"../media/image$image.jpeg\"/>")
                        dr.append(anchor(p, k))
                    }
                    put("xl/drawings/drawing${i + 1}.xml", HEAD + "<xdr:wsDr xmlns:xdr=\"http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing\" " +
                        "xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"$NS_R\">$dr</xdr:wsDr>")
                    put("xl/drawings/_rels/drawing${i + 1}.xml.rels", HEAD + "<Relationships xmlns=\"$NS_PR\">$drRels</Relationships>")
                }
            }
        }
    }

    /** One picture, anchored to its cell and moving with it, [INSET] px from the cell's top-left corner. */
    private fun anchor(p: Picture, k: Int): String {
        val x0 = INSET * EMU; val y0 = INSET * EMU
        val x1 = (INSET + p.w) * EMU; val y1 = (INSET + p.h) * EMU
        return "<xdr:twoCellAnchor editAs=\"oneCell\">" +
            "<xdr:from><xdr:col>${p.col}</xdr:col><xdr:colOff>$x0</xdr:colOff><xdr:row>${p.row}</xdr:row><xdr:rowOff>$y0</xdr:rowOff></xdr:from>" +
            "<xdr:to><xdr:col>${p.col}</xdr:col><xdr:colOff>$x1</xdr:colOff><xdr:row>${p.row}</xdr:row><xdr:rowOff>$y1</xdr:rowOff></xdr:to>" +
            "<xdr:pic><xdr:nvPicPr><xdr:cNvPr id=\"${k + 2}\" name=\"${esc(p.name)}\" descr=\"${esc(p.name)}\"/>" +
            "<xdr:cNvPicPr><a:picLocks noChangeAspect=\"1\"/></xdr:cNvPicPr></xdr:nvPicPr>" +
            "<xdr:blipFill><a:blip r:embed=\"rId${k + 1}\"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>" +
            "<xdr:spPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"${p.w * EMU}\" cy=\"${p.h * EMU}\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom></xdr:spPr>" +
            "</xdr:pic><xdr:clientData/></xdr:twoCellAnchor>"
    }

    /** Pixels between a picture and its cell's top-left corner. */
    const val INSET = 4

    private fun sheetXml(s: Sheet, selected: Boolean, links: MutableList<Pair<String, String>>): String {
        val sb = StringBuilder(HEAD).append("<worksheet xmlns=\"$NS\" xmlns:r=\"$NS_R\">")
        if (s.fitWidth) sb.append("<sheetPr><pageSetUpPr fitToPage=\"1\"/></sheetPr>")
        val lastCol = s.cells.values.maxOfOrNull { it.keys.lastOrNull() ?: 0 } ?: 0
        sb.append("<dimension ref=\"A1:${ref(s.lastRow, lastCol)}\"/>")
        sb.append("<sheetViews><sheetView workbookViewId=\"0\"").append(if (selected) " tabSelected=\"1\"" else "").append(">")
        if (s.freezeRows > 0 || s.freezeCols > 0) {
            val tl = ref(s.freezeRows, s.freezeCols)
            val pane = when { s.freezeRows > 0 && s.freezeCols > 0 -> "bottomRight"; s.freezeRows > 0 -> "bottomLeft"; else -> "topRight" }
            sb.append("<pane").append(if (s.freezeCols > 0) " xSplit=\"${s.freezeCols}\"" else "").append(if (s.freezeRows > 0) " ySplit=\"${s.freezeRows}\"" else "")
                .append(" topLeftCell=\"$tl\" activePane=\"$pane\" state=\"frozen\"/><selection pane=\"$pane\" activeCell=\"$tl\" sqref=\"$tl\"/>")
        }
        sb.append("</sheetView></sheetViews><sheetFormatPr defaultRowHeight=\"15\"/>")
        if (s.widths.isNotEmpty()) {
            sb.append("<cols>")
            s.widths.forEach { (c, w) -> sb.append("<col min=\"${c + 1}\" max=\"${c + 1}\" width=\"").append(fmt(w)).append("\" customWidth=\"1\"/>") }
            sb.append("</cols>")
        }
        sb.append("<sheetData>")
        for ((r, row) in s.cells) {
            sb.append("<row r=\"${r + 1}\"")
            s.heights[r]?.let { sb.append(" ht=\"").append(fmt(it)).append("\" customHeight=\"1\"") }
            sb.append(">")
            for ((c, cell) in row) {
                val at = ref(r, c); val st = cell.style.ordinal
                when (cell) {
                    is Cell.Text -> sb.append("<c r=\"$at\" s=\"$st\" t=\"inlineStr\"><is><t xml:space=\"preserve\">").append(esc(cell.text)).append("</t></is></c>")
                    is Cell.Link -> {
                        links += at to cell.url
                        sb.append("<c r=\"$at\" s=\"$st\" t=\"inlineStr\"><is><t xml:space=\"preserve\">").append(esc(cell.text)).append("</t></is></c>")
                    }
                    is Cell.Num -> sb.append("<c r=\"$at\" s=\"$st\"><v>").append(fmt(cell.value)).append("</v></c>")
                    is Cell.Blank -> sb.append("<c r=\"$at\" s=\"$st\"/>")
                }
            }
            sb.append("</row>")
        }
        sb.append("</sheetData>")
        s.filter?.let { (r, c0, c1) -> sb.append("<autoFilter ref=\"${ref(r, c0)}:${ref(maxOf(r + 1, s.lastRow), c1)}\"/>") }
        if (s.merges.isNotEmpty()) sb.append("<mergeCells count=\"${s.merges.size}\">").append(s.merges.joinToString("") { "<mergeCell ref=\"$it\"/>" }).append("</mergeCells>")
        if (links.isNotEmpty()) sb.append("<hyperlinks>").append(links.withIndex().joinToString("") { (k, l) -> "<hyperlink ref=\"${l.first}\" r:id=\"rId${k + 2}\"/>" }).append("</hyperlinks>")
        sb.append("<pageMargins left=\"0.4\" right=\"0.4\" top=\"0.5\" bottom=\"0.5\" header=\"0.3\" footer=\"0.3\"/>")
        sb.append("<pageSetup paperSize=\"9\" orientation=\"${if (s.landscape) "landscape" else "portrait"}\"")
            .append(if (s.fitWidth) " fitToWidth=\"1\" fitToHeight=\"0\"" else "").append("/>")
        if (s.pictures.isNotEmpty()) sb.append("<drawing r:id=\"rId1\"/>")
        return sb.append("</worksheet>").toString()
    }

    private fun fmt(v: Double): String =
        if (v == Math.rint(v) && kotlin.math.abs(v) < 1e15) v.toLong().toString() else java.math.BigDecimal(v).round(java.math.MathContext(15)).stripTrailingZeros().toPlainString()

    private fun styles(): String {
        val styles = Style.entries
        val fonts = styles.map { it.font }.distinct()
        val fills = styles.mapNotNull { it.fill }.distinct()
        val sb = StringBuilder(HEAD).append("<styleSheet xmlns=\"$NS\">")
        sb.append("<numFmts count=\"5\">" +
            "<numFmt numFmtId=\"164\" formatCode=\"dd/mm/yyyy\"/><numFmt numFmtId=\"165\" formatCode=\"hh:mm\"/>" +
            "<numFmt numFmtId=\"166\" formatCode=\"0.0\"/><numFmt numFmtId=\"167\" formatCode=\"0.000000\"/>" +
            "<numFmt numFmtId=\"168\" formatCode=\"dd/mm/yyyy hh:mm\"/></numFmts>")
        sb.append("<fonts count=\"${fonts.size}\">")
        fonts.forEach { f ->
            sb.append("<font>").append(if (f.bold) "<b/>" else "").append(if (f.underline) "<u/>" else "")
                .append("<sz val=\"${f.size}\"/><color rgb=\"${f.color}\"/><name val=\"Calibri\"/><family val=\"2\"/></font>")
        }
        sb.append("</fonts><fills count=\"${fills.size + 2}\"><fill><patternFill patternType=\"none\"/></fill><fill><patternFill patternType=\"gray125\"/></fill>")
        fills.forEach { sb.append("<fill><patternFill patternType=\"solid\"><fgColor rgb=\"$it\"/><bgColor indexed=\"64\"/></patternFill></fill>") }
        sb.append("</fills><borders count=\"2\"><border><left/><right/><top/><bottom/><diagonal/></border>")
        val line = "style=\"thin\"><color rgb=\"FFCBD5E1\"/>"
        sb.append("<border><left $line</left><right $line</right><top $line</top><bottom $line</bottom><diagonal/></border></borders>")
        sb.append("<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>")
        sb.append("<cellXfs count=\"${styles.size}\">")
        styles.forEach { s ->
            val font = fonts.indexOf(s.font); val fill = s.fill?.let { fills.indexOf(it) + 2 } ?: 0; val border = if (s.border) 1 else 0
            sb.append("<xf numFmtId=\"${s.numFmt}\" fontId=\"$font\" fillId=\"$fill\" borderId=\"$border\" xfId=\"0\"")
            if (s.numFmt != 0) sb.append(" applyNumberFormat=\"1\"")
            if (font != 0) sb.append(" applyFont=\"1\"")
            if (fill != 0) sb.append(" applyFill=\"1\"")
            if (border != 0) sb.append(" applyBorder=\"1\"")
            sb.append(" applyAlignment=\"1\"><alignment vertical=\"center\"")
            s.h?.let { sb.append(" horizontal=\"$it\"") }
            if (s.wrap) sb.append(" wrapText=\"1\"")
            sb.append("/></xf>")
        }
        sb.append("</cellXfs><cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles>")
        return sb.append("<dxfs count=\"0\"/><tableStyles count=\"0\"/></styleSheet>").toString()
    }
}
