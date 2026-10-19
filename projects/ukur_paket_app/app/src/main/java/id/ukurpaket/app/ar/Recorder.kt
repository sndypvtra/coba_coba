package id.ukurpaket.app.ar

import android.media.Image
import com.google.ar.core.Camera
import com.google.ar.core.Frame
import id.ukurpaket.app.measure.BoxResult
import id.ukurpaket.app.measure.FloorPlane
import id.ukurpaket.app.measure.V3
import java.io.DataOutputStream
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import java.util.concurrent.Executors

/**
 * Developer recording ("Rekam data scan"): writes what the measuring core saw during a scan, so the
 * same scan can be replayed on a PC with the same code.
 *
 *   meta.json          seed point, floor plane
 *   frames.jsonl       per frame: time, camera pose, depth intrinsics, files
 *   f0003_depth.u16    raw depth, little-endian uint16 millimetres (header: "UKD1", width, height)
 *   f0003_conf.u8      raw depth confidence 0-255 (header: "UKC1", width, height)
 *   f0003.jpg          camera image (every 4th recorded frame)
 *   result.json        the box and confidence
 */
class Recorder(private val root: File) {
    private val exec = Executors.newSingleThreadExecutor()
    private var dir: File? = null
    private var n = 0

    fun begin(seed: V3, plane: FloorPlane) {
        val d = File(root, "scan_${System.currentTimeMillis()}").apply { mkdirs() }
        dir = d; n = 0
        val txt = String.format(Locale.US,
            "{\"seed\":[%.4f,%.4f,%.4f],\"plane_origin\":[%.4f,%.4f,%.4f],\"plane_normal\":[%.5f,%.5f,%.5f]," +
                "\"device\":\"%s %s\"}\n",
            seed.x, seed.y, seed.z, plane.origin.x, plane.origin.y, plane.origin.z, plane.n.x, plane.n.y, plane.n.z,
            android.os.Build.MANUFACTURER, android.os.Build.MODEL)
        exec.execute { File(d, "meta.json").writeText(txt) }
    }

    fun frame(frame: Frame, cam: Camera, depth: Image, conf: Image, fx: Float, fy: Float, cx: Float, cy: Float) {
        val d = dir ?: return
        val i = n++
        if (i % 2 != 0) return
        val name = String.format(Locale.US, "f%04d", i)
        val dw = depth.width; val dh = depth.height
        val dBytes = copy(depth, 2); val cBytes = copy(conf, 1)
        val p = cam.pose
        val line = String.format(Locale.US,
            "{\"i\":%d,\"t\":%d,\"pose\":[%.5f,%.5f,%.5f,%.6f,%.6f,%.6f,%.6f],\"depth_wh\":[%d,%d]," +
                "\"fx\":%.3f,\"fy\":%.3f,\"cx\":%.3f,\"cy\":%.3f,\"name\":\"%s\"}\n",
            i, frame.timestamp, p.tx(), p.ty(), p.tz(), p.qx(), p.qy(), p.qz(), p.qw(), dw, dh, fx, fy, cx, cy, name)
        var nv21: ByteArray? = null; var iw = 0; var ih = 0
        if (i % 8 == 0) runCatching {
            val img = frame.acquireCameraImage()
            try { nv21 = Yuv.toNv21(img); iw = img.width; ih = img.height } finally { img.close() }
        }
        exec.execute {
            writeRaw(File(d, "${name}_depth.u16"), "UKD1", dw, dh, dBytes)
            writeRaw(File(d, "${name}_conf.u8"), "UKC1", dw, dh, cBytes)
            nv21?.let { File(d, "$name.jpg").writeBytes(Yuv.nv21ToJpeg(it, iw, ih, 85)) }
            File(d, "frames.jsonl").appendText(line)
        }
    }

    fun finish(r: BoxResult, confidence: Int): File? {
        val d = dir ?: return null
        val txt = String.format(Locale.US,
            "{\"length_cm\":%.1f,\"width_cm\":%.1f,\"height_cm\":%.1f,\"points\":%d,\"fill\":%.3f,\"top_noise_m\":%.4f,\"confidence\":%d}\n",
            r.lengthM * 100, r.widthM * 100, r.heightM * 100, r.points, r.fillRatio, r.topNoiseM, confidence)
        exec.execute { File(d, "result.json").writeText(txt) }
        dir = null
        return d
    }

    fun close() = exec.shutdown()

    /** Tightly packed copy of a single-plane image (row stride removed). */
    private fun copy(img: Image, bpp: Int): ByteArray {
        val pl = img.planes[0]
        val buf: ByteBuffer = pl.buffer
        val w = img.width; val h = img.height
        val out = ByteArray(w * h * bpp)
        for (row in 0 until h) for (col in 0 until w) for (b in 0 until bpp)
            out[(row * w + col) * bpp + b] = buf.get(row * pl.rowStride + col * pl.pixelStride + b)
        return out
    }

    private fun writeRaw(f: File, magic: String, w: Int, h: Int, data: ByteArray) {
        DataOutputStream(f.outputStream().buffered()).use { o ->
            o.writeBytes(magic)
            o.write(ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN).putInt(w).putInt(h).array())
            o.write(data)
        }
    }
}
