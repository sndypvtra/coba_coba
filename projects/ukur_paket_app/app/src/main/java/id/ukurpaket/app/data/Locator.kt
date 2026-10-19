package id.ukurpaket.app.data

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.Looper
import androidx.core.content.ContextCompat

/**
 * Where the parcel was measured, from the phone's own location service (no Google Play location, no
 * internet needed for GPS). Asked for when measuring starts; attached to the record when it is saved.
 */
class Locator(private val ctx: Context) {
    @Volatile var last: Location? = null
        private set

    fun allowed() = ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    @SuppressLint("MissingPermission")
    fun refresh() {
        if (!allowed()) return
        val lm = ctx.getSystemService(LocationManager::class.java) ?: return
        val providers = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER).filter {
            runCatching { lm.isProviderEnabled(it) }.getOrDefault(false)
        }
        for (p in providers) runCatching { lm.getLastKnownLocation(p) }.getOrNull()?.let { keep(it) }
        for (p in providers) runCatching {
            if (Build.VERSION.SDK_INT >= 30) lm.getCurrentLocation(p, null, ctx.mainExecutor) { it?.let(::keep) }
            else @Suppress("DEPRECATION") lm.requestSingleUpdate(p, { keep(it) }, Looper.getMainLooper())
        }
    }

    /** A fix from the last 15 minutes, or null. */
    fun fresh(): Location? = last?.takeIf { System.currentTimeMillis() - it.time < 15 * 60_000 }

    private fun keep(l: Location) {
        val cur = last
        if (cur == null || l.time > cur.time + 30_000 || (l.time >= cur.time - 30_000 && l.accuracy < cur.accuracy)) last = l
    }
}
