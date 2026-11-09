package id.ukurpaket.app.photo

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import ai.onnxruntime.TensorInfo
import java.nio.FloatBuffer
import kotlin.math.min

/**
 * YOLO26n-depth (Ultralytics, AGPL-3.0) through ONNX Runtime: a picture -> metres along the optical axis per pixel.
 * Preprocessing as Ultralytics' depth predictor: the picture stretched to the model's input (here 480 x 640, the
 * upright phone picture's own shape), RGB / 255, no mean or std. Android-free (the PC tests run it too).
 * Model: tools/export_depth.py.
 */
class DepthModel(model: ByteArray, threads: Int = 4) : AutoCloseable {
    private val env = OrtEnvironment.getEnvironment()
    private val opts = OrtSession.SessionOptions().apply { setIntraOpNumThreads(threads) }
    private val session = env.createSession(model, opts)
    private val inputName = session.inputNames.first()
    private val shape = (session.inputInfo[inputName]!!.info as TensorInfo).shape
    val inH = shape[2].toInt()
    val inW = shape[3].toInt()

    /** [argb] packed 0xAARRGGBB, [w] x [h], any size: resampled (bilinear) to the model's input. */
    fun run(argb: IntArray, w: Int, h: Int): DepthMap {
        val plane = inW * inH
        val buf = FloatArray(3 * plane)
        val sx = w.toFloat() / inW; val sy = h.toFloat() / inH
        for (y in 0 until inH) {
            val fy = ((y + 0.5f) * sy - 0.5f).coerceIn(0f, h - 1f)
            val y0 = fy.toInt(); val y1 = min(y0 + 1, h - 1); val ay = fy - y0
            for (x in 0 until inW) {
                val fx = ((x + 0.5f) * sx - 0.5f).coerceIn(0f, w - 1f)
                val x0 = fx.toInt(); val x1 = min(x0 + 1, w - 1); val ax = fx - x0
                val p00 = argb[y0 * w + x0]; val p01 = argb[y0 * w + x1]; val p10 = argb[y1 * w + x0]; val p11 = argb[y1 * w + x1]
                for (c in 0 until 3) {
                    val sh = 16 - 8 * c
                    val v = ((p00 shr sh) and 255) * (1 - ax) * (1 - ay) + ((p01 shr sh) and 255) * ax * (1 - ay) +
                        ((p10 shr sh) and 255) * (1 - ax) * ay + ((p11 shr sh) and 255) * ax * ay
                    buf[c * plane + y * inW + x] = v / 255f
                }
            }
        }
        OnnxTensor.createTensor(env, FloatBuffer.wrap(buf), longArrayOf(1, 3, inH.toLong(), inW.toLong())).use { t ->
            session.run(mapOf(inputName to t)).use { r ->
                val out = r[0] as OnnxTensor
                val s = out.info.shape
                val oh = s[s.size - 2].toInt(); val ow = s[s.size - 1].toInt()
                val fb = out.floatBuffer
                val z = FloatArray(fb.remaining()); fb.get(z)
                return DepthMap(ow, oh, z)
            }
        }
    }

    override fun close() { session.close(); opts.close() }

    companion object { const val ASSET = "depth/yolo26n-depth-640x480.onnx" }
}
