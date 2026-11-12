package id.ukurpaket.app

import id.ukurpaket.app.measure.Mask
import id.ukurpaket.app.photo.Calibration
import id.ukurpaket.app.photo.DepthMap
import id.ukurpaket.app.photo.DepthModel
import id.ukurpaket.app.photo.Intrinsics
import id.ukurpaket.app.photo.PhotoMeasure
import id.ukurpaket.app.photo.Sharpness
import id.ukurpaket.app.photo.ShotRecord
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * A tool, not a check: `./gradlew :app:testDebugUnitTest --tests '*RealPhotoExport*' -Pukur.real=<folder of photo
 * sessions from the phone's ZIP> -Pukur.trace=<out dir>` measures every shot exactly as the phone does today (the
 * phone's own depth map, its autofocus record, the outline's sharpness from the full-resolution photo, not calibrated)
 * and writes the result, with the 3D box's corners, to `<out dir>/<session>_<shot>.json`, for drawing it beside the
 * photo and the depth map. The photos are read from the ZIP folder and never copied into the repository.
 */
class RealPhotoExport {
    @Test fun export() {
        val root = System.getProperty("ukur.real"); val out = System.getProperty("ukur.trace")
        assumeTrue(root != null && out != null)
        val json = Json { ignoreUnknownKeys = true }
        File(out!!).mkdirs()
        for (rec in File(root!!).walk().filter { it.name.startsWith("shot_") && it.name.endsWith(".json") }.sorted()) {
            val dir = rec.parentFile; val i = rec.name.removePrefix("shot_").removeSuffix(".json")
            val r0 = json.decodeFromString(ShotRecord.serializer(), rec.readText())
            val m = TestImages.read(File(dir, "mask_$i.png").inputStream())
            val mask = Mask(m.w, m.h, BooleanArray(m.w * m.h) { (m.px[it] and 255) > 127 })
            val big = TestImages.read(File(dir, "photo_$i.jpg").inputStream())
            val luma = ByteArray(big.w * big.h) { q -> val c = big.px[q]; (((c shr 16) and 255) * 0.299 + ((c shr 8) and 255) * 0.587 + (c and 255) * 0.114).toInt().toByte() }
            val sharp = Sharpness.atOutline(luma, big.w, big.h, mask)
            val ds = r0.depthSize!!; val bs = File(dir, "depth_$i.u16").readBytes()
            val depth = DepthMap(ds[0], ds[1], FloatArray(ds[0] * ds[1]) { q -> ((bs[2 * q].toInt() and 255) or ((bs[2 * q + 1].toInt() and 255) shl 8)) / 1000f })
            val a = r0.accel
            val r = PhotoMeasure.measure(mask, r0.lensModel, Intrinsics.upFromAccel(a[0], a[1], a[2]), depth, DepthModel.DEFAULT_SCALE, false,
                null, r0.focus, Calibration.builtIn(r0.focus), sharp)
            val o = buildJsonObject {
                put("session", dir.name); put("shot", i.toInt()); put("app", r0.app ?: ""); put("pickMode", r0.pickMode ?: "")
                put("box", JsonArray((r0.box ?: emptyList()).map { JsonPrimitive(it) }))
                put("lengthCm", r.lengthCm); put("widthCm", r.widthCm); put("heightCm", r.heightCm)
                put("cameraHeightM", r.cameraHeightM); put("downDeg", r.downDeg); put("iou", r.iou); put("boxLike", r.boxLike)
                put("corners", JsonArray(r.corners.map { JsonPrimitive(it) })); put("confidence", r.confidence); put("ok", r.ok)
                put("notes", JsonArray(r.notes.map { JsonPrimitive(it) }))
                put("aiCameraM", r.aiCameraM); put("focusCameraM", r.focusCameraM); put("focusDistanceM", r.focusDistanceM)
                put("focusDiopters", r.focusDiopters); put("sharpness", r.sharpness); put("floorTiltDeg", r.floorTiltDeg)
                put("recordedCm", JsonArray(listOfNotNull(r0.result?.lengthCm, r0.result?.widthCm, r0.result?.heightCm).map { JsonPrimitive(it) }))
            }
            File(out, "${dir.name}_$i.json").writeText(o.toString())
            println("${dir.name}/$i: %.1f x %.1f x %.1f cm, camera %.3f m (focus %.3f, AI %.3f), sharp %.2f, conf %d, ok %b".format(
                r.lengthCm, r.widthCm, r.heightCm, r.cameraHeightM, r.focusCameraM, r.aiCameraM, r.sharpness, r.confidence, r.ok))
        }
    }
}
