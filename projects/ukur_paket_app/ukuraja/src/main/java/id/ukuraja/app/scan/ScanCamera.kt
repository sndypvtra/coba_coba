package id.ukuraja.app.scan

import android.annotation.SuppressLint
import android.content.Context
import android.util.Size
import android.view.MotionEvent
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ExperimentalGetImage
import androidx.camera.core.FocusMeteringAction
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.AspectRatioStrategy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.ZoomSuggestionOptions
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * The label scanner's camera: CameraX preview and analysis (4:3, about 1280 x 960), each frame read by ML Kit's
 * barcode model, which is bundled in the APK. Nothing here needs Google Play services or a network, unlike the Play
 * services code scanner it replaces, which fails on a PDA without them (or before its module has been downloaded).
 *
 * The callbacks come on the main thread.
 */
class ScanCamera(private val ctx: Context, private val reader: ResiReader, private val cb: Callback) {
    interface Callback {
        fun onReady(hasTorch: Boolean)
        fun onStep(step: ScanStep)
        fun onDark(dark: Boolean)
        fun onError(msg: String)
    }

    private val main = ContextCompat.getMainExecutor(ctx)
    private val worker: ExecutorService = Executors.newSingleThreadExecutor { r -> Thread(r, "resi-scan") }
    private var provider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var scanner: BarcodeScanner? = null
    @Volatile private var closed = false
    @Volatile private var done = false
    private var frames = 0
    private var failures = 0

    /** Starts the camera into [view], tied to [owner]'s lifecycle (it stops in the background and comes back). */
    @SuppressLint("ClickableViewAccessibility")
    fun bind(owner: LifecycleOwner, view: PreviewView) {
        val future = ProcessCameraProvider.getInstance(ctx)
        future.addListener({
            if (closed) return@addListener
            try {
                val p = future.get().also { provider = it }
                val ratio = AspectRatioStrategy.RATIO_4_3_FALLBACK_AUTO_STRATEGY
                val preview = Preview.Builder()
                    .setResolutionSelector(ResolutionSelector.Builder().setAspectRatioStrategy(ratio).build())
                    .build()
                preview.setSurfaceProvider(view.surfaceProvider)
                // 1280 x 960: Code 128 on a label gets 3-4 px per bar at 15 cm, and ML Kit reads a frame in tens of ms
                val analysis = ImageAnalysis.Builder()
                    .setResolutionSelector(ResolutionSelector.Builder().setAspectRatioStrategy(ratio)
                        .setResolutionStrategy(ResolutionStrategy(Size(1280, 960), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER))
                        .build())
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                p.unbindAll()
                val cam = p.bindToLifecycle(owner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis).also { camera = it }
                // a small barcode far away: ML Kit asks for zoom (as the Play services scanner's auto zoom), up to 3x
                val maxZoom = minOf(3f, cam.cameraInfo.zoomState.value?.maxZoomRatio ?: 1f)
                val options = BarcodeScannerOptions.Builder()
                    .setBarcodeFormats(ResiReader.FORMATS.first(), *ResiReader.FORMATS.drop(1).toIntArray())
                    .apply {
                        if (maxZoom > 1.05f) setZoomSuggestionOptions(
                            ZoomSuggestionOptions.Builder { r -> if (!closed && !done) cam.cameraControl.setZoomRatio(r); true }
                                .setMaxSupportedZoomRatio(maxZoom).build())
                    }
                    .build()
                scanner = BarcodeScanning.getClient(options)
                analysis.setAnalyzer(worker) { img -> analyze(img) }
                // a tap focuses there (a label close up, or a glossy one)
                view.setOnTouchListener { v, e ->
                    if (e.action == MotionEvent.ACTION_UP) {
                        val pt = view.meteringPointFactory.createPoint(e.x, e.y)
                        runCatching {
                            cam.cameraControl.startFocusAndMetering(FocusMeteringAction.Builder(pt, FocusMeteringAction.FLAG_AF or FocusMeteringAction.FLAG_AE)
                                .setAutoCancelDuration(3, TimeUnit.SECONDS).build())
                        }
                        v.performClick()
                    }
                    true
                }
                cb.onReady(cam.cameraInfo.hasFlashUnit())
            } catch (e: Exception) {
                cb.onError("Kamera tidak bisa dibuka (${e.message ?: e.javaClass.simpleName}). Tutup aplikasi kamera lain, lalu coba lagi.")
            }
        }, main)
    }

    fun torch(on: Boolean) { runCatching { camera?.cameraControl?.enableTorch(on) } }

    /** Stops reading frames (the number is taken); the preview stays until [close]. */
    fun stop() { done = true }

    fun close() {
        closed = true
        runCatching { provider?.unbindAll() }
        worker.shutdown()
        runCatching { scanner?.close() }
    }

    @androidx.annotation.OptIn(ExperimentalGetImage::class)
    private fun analyze(proxy: ImageProxy) {
        val media = proxy.image
        val sc = scanner
        if (closed || done || media == null || sc == null) { proxy.close(); return }
        if (frames++ % 10 == 0) {
            val dark = meanLuma(proxy) < DARK_LUMA
            main.execute { if (!closed) cb.onDark(dark) }
        }
        val rot = proxy.imageInfo.rotationDegrees
        // ML Kit gives the boxes in the upright picture, which is the preview on screen
        val uw = (if (rot % 180 == 0) proxy.width else proxy.height).toFloat()
        val uh = (if (rot % 180 == 0) proxy.height else proxy.width).toFloat()
        val task = try { sc.process(InputImage.fromMediaImage(media, rot)) } catch (e: Exception) { proxy.close(); return }
        task.addOnSuccessListener(main) { codes ->
            failures = 0
            if (closed || done) return@addOnSuccessListener
            val seen = codes.mapNotNull { b ->
                val r = b.boundingBox ?: return@mapNotNull null
                Seen(b.rawValue ?: b.displayValue ?: return@mapNotNull null, b.format, r.left / uw, r.top / uh, r.right / uw, r.bottom / uh)
            }
            val step = reader.offer(seen, System.currentTimeMillis())
            if (step.resi != null) done = true
            cb.onStep(step)
        }.addOnFailureListener(main) { e ->
            // a frame now and then may fail; every frame failing means the reader itself cannot run
            if (++failures == 30 && !closed) cb.onError("Pembaca barcode tidak jalan (${e.message ?: e.javaClass.simpleName}). Ketik nomor resi.")
        }.addOnCompleteListener(main) { proxy.close() }
    }

    private fun meanLuma(proxy: ImageProxy): Double {
        val pl = proxy.planes[0]; val buf = pl.buffer; val rs = pl.rowStride; val ps = pl.pixelStride
        var sum = 0L; var n = 0
        var y = 0
        while (y < proxy.height) {
            var x = 0
            while (x < proxy.width) { sum += buf.get(y * rs + x * ps).toInt() and 255; n++; x += 24 }
            y += 24
        }
        return if (n == 0) 128.0 else sum.toDouble() / n
    }

    companion object {
        /** Mean brightness below which the screen suggests the torch. */
        const val DARK_LUMA = 45.0
    }
}
