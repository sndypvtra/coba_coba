package id.ukurpaket.app

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import com.github.takahirom.roborazzi.captureRoboImage
import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.dt.ObjectPick
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoCamera
import id.ukurpaket.app.photo.ShotRecord
import id.ukurpaket.app.ui.C
import id.ukurpaket.app.ui.LocalStill
import id.ukurpaket.app.ui.PhotoCameraChrome
import id.ukurpaket.app.ui.PhotoPurpose
import id.ukurpaket.app.ui.PhotoShotUi
import id.ukurpaket.app.ui.PhotoShotView
import id.ukurpaket.app.ui.UkurTheme
import kotlinx.serialization.json.Json
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * A tool, not a check: the photo mode's own screens (the app's Compose code, as the APK draws them) filled with one
 * real shot from the phone's ZIP: the camera, the pick (the courier's tap or box, as recorded) and the result the phone
 * computed (the record's PhotoResult, unchanged). For slides that must show the app as it is.
 *
 *     ./gradlew :app:testDebugUnitTest --tests '*RealPhotoScreens*' -Pukur.real=<session folder> -Pukur.trace=<out dir>
 *
 * The photo is read from the ZIP folder and the pictures are written to <out dir>: neither enters the repository.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "w360dp-h720dp-xxxhdpi")
class RealPhotoScreens {
    private fun shot(path: File, content: @Composable () -> Unit) =
        captureRoboImage(path.path) { CompositionLocalProvider(LocalStill provides true) { UkurTheme { content() } } }

    @Test fun screens() {
        val dir = System.getProperty("ukur.real")?.let(::File); val out = System.getProperty("ukur.trace")?.let(::File)
        assumeTrue(dir != null && out != null)
        out!!.mkdirs()
        val rec = dir!!.listFiles()!!.filter { it.name.startsWith("shot_") && it.name.endsWith(".json") }.minBy { it.name }
        val i = rec.name.removePrefix("shot_").removeSuffix(".json")
        val r = Json { ignoreUnknownKeys = true }.decodeFromString(ShotRecord.serializer(), rec.readText())
        val pic = BitmapFactory.decodeFile(File(dir, "photo_$i.jpg").path)
        val mb = BitmapFactory.decodeFile(File(dir, "mask_$i.png").path)
        val mw = mb.width; val mh = mb.height
        val mpx = IntArray(mw * mh).also { mb.getPixels(it, 0, mw, 0, 0, mw, mh) }
        val mask = Mask(mw, mh, BooleanArray(mpx.size) { (mpx[it] and 255) > 127 })
        val tint = ObjectPick.tint(mask)
        val outline = mask.outline().flatMap { listOf(it.a / mw, it.b / mh) }
        val s = pic.width.toFloat() / r.lensModel.w                  // pick positions: model picture -> this picture
        val tap = r.tap?.map { it * s }; val box = r.box?.map { it * s }
        val up = Intrinsics.upFromAccel(r.accel[0], r.accel[1], r.accel[2])
        val base = PhotoShotUi(0, pic, r.lens, up, r.downDeg, r.still, ready = true)
        val purpose = PhotoPurpose.PARCEL
        // the record says ok, which the engine gives only on a calibrated phone: the screen is drawn calibrated (its factor is not in the ZIP)
        val calibrated = r.result?.ok == true
        shot(File(out, "app_1_kamera.png")) { Box(Modifier.fillMaxSize().background(C.bg)) {
            PhotoCameraChrome("Ukur dengan foto", "foto dari pojok paket", PhotoCamera.Live(r.downDeg, r.still, 120.0, "${r.stream[0]}×${r.stream[1]}"),
                false, null, emptyList(), {}, {}, {}) { Image(pic.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop) } } }
        val picked = base.copy(tap = tap, box = box, mask = mask, tint = tint, outline = outline, stage = "Mengukur…")
        shot(File(out, "app_2_marking.png")) { Box(Modifier.fillMaxSize().background(C.bg)) {
            PhotoShotView(purpose, picked, listOf(picked), null, "1 foto", 6000, calibrated, null, 0, listOf("", "", ""), isParcel = true,
                {}, { _, _ -> }, {}, {}, {}, {}, {}, {}, {}) } }
        val result = r.result!!
        val done = base.copy(tap = tap, box = box, mask = mask, tint = tint, outline = outline, result = result)
        shot(File(out, "app_3_hasil.png")) { Box(Modifier.fillMaxSize().background(C.bg)) {
            PhotoShotView(purpose, done, listOf(done), result, "1 foto", 6000, calibrated, null, 0, listOf("", "", ""), isParcel = true,
                {}, { _, _ -> }, {}, {}, {}, {}, {}, {}, {}) } }
        println("screens for ${dir.name}/$i: %.1f x %.1f x %.1f cm, score %d, ok %b".format(result.lengthCm, result.widthCm, result.heightCm, result.confidence, result.ok))
    }
}
