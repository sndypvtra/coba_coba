package id.ukuraja.app

import android.app.Activity
import android.app.Application
import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import com.github.takahirom.roborazzi.captureRoboImage
import id.ukuraja.app.data.Measurement
import id.ukuraja.app.data.Status
import id.ukuraja.app.ui.App
import id.ukuraja.app.ui.AppModel
import id.ukuraja.app.ui.C
import id.ukuraja.app.ui.Draft
import id.ukuraja.app.ui.GuideScreen
import id.ukuraja.app.ui.GuidePages
import id.ukuraja.app.ui.LiveMarkerState
import id.ukuraja.app.ui.LocalStill
import id.ukuraja.app.ui.PhotoCameraChrome
import id.ukuraja.app.ui.PhotoFlow
import id.ukuraja.app.ui.PhotoOutcome
import id.ukuraja.app.ui.PhotoShotUi
import id.ukuraja.app.ui.PhotoShotView
import id.ukuraja.app.ui.ScanChrome
import id.ukuraja.app.ui.ExcelChoices
import id.ukuraja.app.ui.T
import id.ukuraja.app.data.Period
import id.ukuraja.app.data.Report
import id.ukuraja.app.data.ReportInfo
import id.ukuraja.app.data.Thumbs
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.ukuraja.app.scan.Hint
import id.ukuraja.app.scan.ResiReader
import id.ukuraja.app.scan.ScanStep
import id.ukuraja.app.scan.Seen
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.zxing.BarcodeFormat
import com.google.zxing.MultiFormatWriter
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import id.ukuraja.app.ui.Screen
import id.ukuraja.app.ui.UkurAjaTheme
import id.ukurpaket.app.marker.Aruco
import id.ukurpaket.app.marker.Luma
import id.ukurpaket.app.marker.MarkerObservation
import id.ukurpaket.app.marker.MarkerSheet
import id.ukurpaket.app.photo.DepthModel
import id.ukurpaket.app.photo.PhotoCamera
import id.ukurpaket.app.photo.PhotoFiles
import id.ukurpaket.app.photo.PhotoMeasure
import id.ukurpaket.app.photo.PhotoResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.util.Locale

/**
 * Every UkurAja screen rendered on the JVM (phone 412 x 892 dp at 3x) into ukuraja/screenshots/. The photo screens show
 * what the real engine makes of a synthetic photo (Scene: a 40 x 30 x 20 cm carton and the A4 marker, the depth model's
 * height 30 % off): the marker found by Aruco, the size by PhotoMeasure, as on the phone.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "w412dp-h892dp-xxhdpi")
class ScreenshotTest {
    private val app: Application = RuntimeEnvironment.getApplication()

    private fun shot(name: String, content: @Composable () -> Unit) =
        captureRoboImage("screenshots/$name.png") {
            CompositionLocalProvider(LocalStill provides true) { UkurAjaTheme { Box(Modifier.fillMaxSize().background(C.bg)) { content() } } }
        }

    private fun model(): AppModel {
        File(app.filesDir, "ukuraja.json").delete()
        return AppModel(app, preload = false)
    }

    private fun screen(name: String, m: AppModel, s: Screen) {
        m.stack.clear(); m.stack.add(Screen.Home); if (s != Screen.Home) m.stack.add(s)
        shot(name) { App(m, LocalContext.current as Activity) }
    }

    private class Measured(val pic: Bitmap, val full: Bitmap, val shot: PhotoShotUi, val result: PhotoResult)

    /** The scene through the engine, as PhotoFlow does it: markers on the full picture, the size on the 480 one. */
    private fun measure(scene: Scene): Measured {
        val argb = scene.render()
        val dets = Aruco.detect(Luma(scene.w, scene.h, scene.luma(argb)), MarkerSheet.IDS)
        val half = scene.half(argb)
        val pic = Bitmap.createBitmap(half, scene.w / 2, scene.h / 2, Bitmap.Config.ARGB_8888)
        val full = Bitmap.createBitmap(argb, scene.w, scene.h, Bitmap.Config.ARGB_8888)
        val mask = scene.mask()
        val k = scene.k.scaled(scene.w / 2, scene.h / 2)
        val obs = dets.map { MarkerObservation.of(it, 0.16, 0.5f) }
        val r = PhotoMeasure.measure(mask, k, scene.up, scene.depth(1.3), DepthModel.DEFAULT_SCALE, calibrated = false, markers = obs)
        val outline = mask.outline().flatMap { listOf(it.a / mask.w, it.b / mask.h) }
        val shot = PhotoShotUi(0, pic, k, scene.up, scene.down.toFloat(), true, ready = true, tap = listOf(270f, 300f), mask = mask,
            tint = PhotoFlow.tint(mask), outline = outline, result = r, lumaW = scene.w, lumaH = scene.h, markers = dets)
        return Measured(pic, full, shot, r)
    }

    /**
     * A parcel label held up to the scanner (the preview, 3:4): the resi's Code 128 in the window, the order number's
     * barcode above it and a QR code beside. Returns the picture and the two barcodes' boxes as fractions.
     */
    private fun labelPhoto(): Triple<Bitmap, Seen, Seen> {
        val w = 960; val h = 1280
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp)
        c.drawColor(0xFFB98B5A.toInt())                                   // carton
        val p = Paint(Paint.ANTI_ALIAS_FLAG)
        p.color = 0xFFFCFCF8.toInt(); c.drawRect(40f, 150f, 920f, 1180f, p)  // the label
        fun bars(text: String, x: Float, y: Float, bw: Float, bh: Float): Seen {
            val m = MultiFormatWriter().encode(text, BarcodeFormat.CODE_128, 0, 1)
            val unit = bw / m.width
            p.color = 0xFF111111.toInt()
            for (i in 0 until m.width) if (m.get(i, 0)) c.drawRect(x + i * unit, y, x + (i + 1) * unit, y + bh, p)
            return Seen(text, Barcode.FORMAT_CODE_128, x / w, y / h, (x + bw) / w, (y + bh) / h)
        }
        val order = bars("ORD99120034", 90f, 205f, 420f, 90f)
        p.typeface = Typeface.DEFAULT_BOLD; p.textSize = 30f; c.drawText("No. Order ORD99120034", 90f, 335f, p)
        val qr = MultiFormatWriter().encode("https://anteraja.id", BarcodeFormat.QR_CODE, 0, 0)
        val qs = 200f / qr.width
        for (y in 0 until qr.height) for (x in 0 until qr.width) if (qr.get(x, y)) c.drawRect(680 + x * qs, 170 + y * qs, 680 + (x + 1) * qs, 170 + (y + 1) * qs, p)
        val resi = bars("TSA-80745081104", 110f, 520f, 740f, 190f)
        p.textSize = 44f; c.drawText("TSA-80745081104", 300f, 770f, p)
        p.typeface = Typeface.DEFAULT; p.textSize = 30f; p.color = 0xFF333333.toInt()
        listOf("Penerima: Budi S.", "Jl. Melati No. 12, Bekasi Timur", "Berat: 2,4 kg · REG").forEachIndexed { i, t -> c.drawText(t, 90f, 880f + i * 50, p) }
        return Triple(bmp, order, resi)
    }

    private fun records(dir: File, evidence: File?): List<Measurement> {
        val now = System.currentTimeMillis()
        return listOf(
            Measurement(resi = "TSA-80745081104", lengthCm = 40.1, widthCm = 30.0, heightCm = 20.0, scaleKg = 2.35, status = Status.OK, confidence = 100,
                photo = evidence?.path, scaleSource = "Marker A4", cameraM = 1.30, createdAt = now - 60_000, lat = -6.2384, lon = 106.9756, gpsM = 8f, operator = "Andi"),
            Measurement(resi = "TSA-80745081187", lengthCm = 62.0, widthCm = 41.5, heightCm = 35.0, scaleKg = 8.4, status = Status.OK, confidence = 94,
                photo = evidence?.path, scaleSource = "Marker A3", cameraM = 1.42, createdAt = now - 25 * 60_000, operator = "Andi"),
            Measurement(resi = "TSA-80745081190", lengthCm = 0.0, widthCm = 0.0, heightCm = 0.0, status = Status.HUB, confidence = 0,
                note = "Bentuk tidak beraturan / lunak", createdAt = now - 50 * 60_000, operator = "Andi"),
            Measurement(resi = "TSA-80745081201", lengthCm = 25.4, widthCm = 18.2, heightCm = 9.6, scaleKg = 0.8, status = Status.CHECK, confidence = 60,
                photo = evidence?.path, scaleSource = "AI + skala dari 6 foto marker", cameraM = 1.24, createdAt = now - 80 * 60_000, operator = "Andi"),
        ).also { dir.mkdirs() }
    }

    @Test fun everyScreen() {
        val withMarker = measure(Scene())
        val r = withMarker.result
        println(String.format(Locale.US, "engine on the synthetic photo: %.1f x %.1f x %.1f cm (truth 40 x 30 x 20), marker %b (%.3f m, sigma %.3f), score %d, ok %b, notes %s",
            r.lengthCm, r.widthCm, r.heightCm, r.markerUsed(), r.markerCameraM, r.markerSigma, r.confidence, r.ok, r.notes))
        assertTrue(r.markerUsed())
        assertEquals(40.0, r.lengthCm, 1.5); assertEquals(30.0, r.widthCm, 1.5); assertEquals(20.0, r.heightCm, 1.5)

        // the evidence photo as the app writes it: box, outline, marker labelled
        val dir = File(app.filesDir, "photo_sessions/demo").apply { mkdirs() }
        val ev = File(dir, "evidence.jpg")
        val q = withMarker.shot.markerFractions.first()
        PhotoFiles.evidence(withMarker.full, r.corners, withMarker.shot.outline, ev, q, "Marker A4 · 16 cm")
        File("screenshots").mkdirs(); ev.copyTo(File("screenshots/bukti_foto.jpg"), overwrite = true)

        val m = model()
        records(dir, ev).forEach { m.store.save(it) }
        m.store.update { it.copy(operator = "Andi · Counter Bekasi") }
        screen("01_beranda", m, Screen.Home)
        // the label scanner: aiming (the order number's barcode is outside the window, so it is not taken), then read
        val (label, order, resiBox) = labelPhoto()
        val aiming = ResiReader().offer(listOf(order), 0)
        assertEquals(Hint.MOVE_INTO_WINDOW, aiming.hint)
        shot("01b_scan_resi") {
            ScanChrome(ScanStep(null, null, emptyList(), Hint.AIM), true, true, false, false, null, {}, {}, {}, {}) {
                Image(label.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
            }
        }
        val read = ResiReader().offer(listOf(order, resiBox), 0)
        assertEquals("TSA-80745081104", read.resi)
        shot("01c_scan_resi_terbaca") {
            ScanChrome(read, true, true, false, false, null, {}, {}, {}, {}) {
                Image(label.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
            }
        }
        listOf("siapkan", "scan", "taruh", "posisi", "foto", "ketuk", "hasil").forEachIndexed { i, n -> screen("02_panduan_ukur_${i + 1}_$n", m, Screen.Guide(i)) }
        shot("02_panduan_ukur_3_contoh_salah") { GuideScreen(m, LocalContext.current as Activity, GuidePages.PLACE, showWrong = true) }

        // the camera: marker in view and big enough / not in view
        val live = PhotoCamera.Live(45f, true, 120.0, "1280×960")
        val det = withMarker.shot.markers.first()
        val lm = LiveMarkerState(det.id, det.sidePx, q, 0L, big = true)
        shot("03_kamera_marker_terbaca") {
            PhotoCameraChrome("Ukur paket", "Resi TSA-80745081104 · foto dari pojok paket", live, lm, false, null, emptyList(), {}, {}, {}, {}) {
                Image(withMarker.pic.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
            }
        }
        val noMarker = measure(Scene(marker = false))
        shot("04_kamera_belum_siap") {
            PhotoCameraChrome("Ukur paket", "Resi TSA-80745081104 · foto dari pojok paket", PhotoCamera.Live(18f, false, 120.0, "1280×960"), null, false, null, emptyList(), {}, {}, {}, {}) {
                Image(noMarker.pic.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
            }
        }
        shot("05a_proses") {
            PhotoShotView(withMarker.shot.copy(result = null, mask = null, tint = null, outline = null, stage = "Memotong paket…"), listOf(withMarker.shot), null,
                "Resi TSA-80745081104 · 1 foto", 6000, null, {}, { _, _ -> }, {}, {}, {}, {}, {})
        }
        shot("05_hasil_dengan_marker") {
            PhotoShotView(withMarker.shot, listOf(withMarker.shot), r, "Resi TSA-80745081104 · 1 foto", 6000, "Marker A4", {}, { _, _ -> }, {}, {}, {}, {}, {})
        }
        val r0 = noMarker.result
        println(String.format(Locale.US, "without the marker: %.1f x %.1f x %.1f cm, score %d, ok %b", r0.lengthCm, r0.widthCm, r0.heightCm, r0.confidence, r0.ok))
        assertFalse(r0.markerUsed()); assertFalse(r0.ok)
        shot("06_hasil_tanpa_marker") {
            PhotoShotView(noMarker.shot, listOf(noMarker.shot), r0, "Resi TSA-80745081187 · 1 foto", 6000, "AI (tanpa marker)", {}, { _, _ -> }, {}, {}, {}, {}, {})
        }
        m.draft = Draft("TSA-80745081104", PhotoOutcome(r.lengthCm, r.widthCm, r.heightCm, r.confidence, Status.OK, ev.path, dir.path, "Marker A4", r.cameraHeightM, 1))
        screen("07_berat", m, Screen.Weight)
        screen("08_tersimpan", m, Screen.Saved(m.store.measurements.value.first().id))
        screen("09_riwayat", m, Screen.History)
        screen("10_detail", m, Screen.Detail(m.store.measurements.value.first().id))
        screen("11_pengaturan", m, Screen.Settings)
        // Pengaturan -> Ekspor Excel: the period dialog, and the file it makes from these records
        shot("12_ekspor_excel") {
            Column(Modifier.padding(24.dp).fillMaxWidth().clip(RoundedCornerShape(28.dp)).background(androidx.compose.ui.graphics.Color.White).padding(24.dp)) {
                T("Ekspor Excel", 18.sp, FontWeight.SemiBold); androidx.compose.foundation.layout.Spacer(Modifier.padding(6.dp))
                ExcelChoices(m.store.measurements.value, System.currentTimeMillis()) {}
            }
        }
        val info = ReportInfo(Period.ALL, System.currentTimeMillis(), "UkurAja 1.0.0", "Urovo DT50")
        Report.write(m.store.measurements.value, info, File("screenshots/contoh_laporan.xlsx")) { Thumbs.of(it.photo) }
    }
}
