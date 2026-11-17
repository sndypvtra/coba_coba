package id.ukuraja.app

import id.ukuraja.app.data.Export
import id.ukuraja.app.data.Measurement
import id.ukuraja.app.data.Status
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.zip.ZipFile

class ExportTest {
    private val ms = listOf(
        Measurement(resi = "TSA-1", lengthCm = 40.12, widthCm = 30.0, heightCm = 20.0, scaleKg = 2.5, status = Status.OK, confidence = 100,
            scaleSource = "Marker A4", cameraM = 1.304, createdAt = 1_700_000_000_000, operator = "Andi; Bekasi", note = "kata \"rapuh\""),
        Measurement(resi = "TSA-2", lengthCm = 0.0, widthCm = 0.0, heightCm = 0.0, status = Status.HUB, confidence = 0, note = "Lainnya",
            createdAt = 1_700_000_100_000),
    )

    @Test fun csvColumnsAndRows() {
        val lines = Export.csv(ms).removePrefix("﻿").split("\r\n").filter { it.isNotEmpty() }
        assertEquals(3, lines.size)
        assertEquals(Export.COLUMNS.joinToString(";"), lines[0])
        val row = lines[1]
        assertTrue(row, row.startsWith("TSA-1;"))
        assertTrue(row, row.contains(";40,1;30,0;20,0;24,07;6000;4,01;2,50;4,02;Akurat;100;Marker A4;1,30;1;"))
        // the separator and quotes inside a cell are quoted
        assertTrue(row, row.contains(";\"Andi; Bekasi\";"))
        assertTrue(row, row.contains(";\"kata \"\"rapuh\"\"\";"))
        // a hub parcel has no size
        assertTrue(lines[2], lines[2].startsWith("TSA-2;") && lines[2].contains(";;;;;6000;;;;Ukur di Hub;;"))
        assertEquals(Export.COLUMNS.size, lines[1].replace(Regex("\"[^\"]*(\"\"[^\"]*)*\""), "x").split(";").size)
    }

    @Test fun zipHoldsTheTableAndThePhotos() {
        val dir = createTempDir("ukuraja")
        val photo = File(dir, "evidence.jpg").apply { writeBytes(byteArrayOf(1, 2, 3)) }
        val out = Export.writeZip(listOf(ms[0].copy(photo = photo.path), ms[1]), File(dir, "out.zip"))
        ZipFile(out).use { z ->
            val names = z.entries().toList().map { it.name }.toSet()
            assertTrue(names.contains("ukuraja.csv"))
            assertTrue(names.any { it.startsWith("foto/TSA-1_") && it.endsWith(".jpg") })
            assertEquals(2, names.size)
        }
        dir.deleteRecursively()
    }
}
