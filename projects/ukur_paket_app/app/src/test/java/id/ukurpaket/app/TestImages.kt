package id.ukurpaket.app

import java.io.InputStream

/**
 * Reads a JPEG/PNG on the PC as ARGB pixels. Unit tests compile against android.jar, which has no
 * javax.imageio, but the JVM running them does: so ImageIO is reached by name.
 */
internal object TestImages {
    class Argb(val px: IntArray, val w: Int, val h: Int)

    fun read(stream: InputStream): Argb {
        val img = Class.forName("javax.imageio.ImageIO").getMethod("read", InputStream::class.java).invoke(null, stream)
        val c = img.javaClass
        val w = c.getMethod("getWidth").invoke(img) as Int
        val h = c.getMethod("getHeight").invoke(img) as Int
        val i = Int::class.javaPrimitiveType
        val px = c.getMethod("getRGB", i, i, i, i, IntArray::class.java, i, i).invoke(img, 0, 0, w, h, null, 0, w) as IntArray
        return Argb(px, w, h)
    }
}
