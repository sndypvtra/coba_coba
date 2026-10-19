package id.ukurpaket.app.ar

import android.app.Activity
import android.content.Context
import com.google.ar.core.ArCoreApk
import com.google.ar.core.Config
import com.google.ar.core.Session
import id.ukurpaket.app.data.Mode
import kotlinx.coroutines.delay

/** What this phone can do, decided once at start-up. */
data class DeviceCaps(
    val arcore: ArState,
    val depth: Boolean,
    val model: String = "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}",
) {
    val mode: Mode get() = when {
        arcore != ArState.READY -> Mode.NONE
        depth -> Mode.AR_FULL
        else -> Mode.AR_BASIC
    }
}

enum class ArState(val label: String) {
    CHECKING("Memeriksa…"),
    READY("ARCore siap"),
    NEEDS_INSTALL("ARCore perlu dipasang"),
    INSTALL_DECLINED("Pemasangan ARCore dibatalkan"),
    UNSUPPORTED("HP ini tidak didukung ARCore"),
    ERROR("ARCore tidak bisa dibuka"),
}

object ArCheck {
    /** Availability without touching the network or prompting. Polls while ARCore is still checking. */
    suspend fun availability(ctx: Context): ArState {
        repeat(20) {
            val a = ArCoreApk.getInstance().checkAvailability(ctx)
            if (a.isTransient) { delay(200); return@repeat }
            return when (a) {
                ArCoreApk.Availability.SUPPORTED_INSTALLED -> ArState.READY
                ArCoreApk.Availability.SUPPORTED_APK_TOO_OLD,
                ArCoreApk.Availability.SUPPORTED_NOT_INSTALLED -> ArState.NEEDS_INSTALL
                else -> ArState.UNSUPPORTED
            }
        }
        return ArState.ERROR
    }

    /**
     * Asks Google Play to install or update "Google Play Services for AR". Returns READY when it is
     * installed, NEEDS_INSTALL when the Play Store screen was opened (call again on resume).
     */
    fun requestInstall(activity: Activity, userRequested: Boolean): ArState = try {
        when (ArCoreApk.getInstance().requestInstall(activity, userRequested)) {
            ArCoreApk.InstallStatus.INSTALLED -> ArState.READY
            else -> ArState.NEEDS_INSTALL
        }
    } catch (e: com.google.ar.core.exceptions.UnavailableUserDeclinedInstallationException) {
        ArState.INSTALL_DECLINED
    } catch (e: com.google.ar.core.exceptions.UnavailableDeviceNotCompatibleException) {
        ArState.UNSUPPORTED
    } catch (e: Exception) {
        ArState.ERROR
    }

    /** Opens a session briefly to ask whether the Depth API works on this phone. */
    fun depthSupported(ctx: Context): Boolean = try {
        val s = Session(ctx)
        val ok = s.isDepthModeSupported(Config.DepthMode.AUTOMATIC)
        s.close()
        ok
    } catch (e: Exception) {
        false
    }
}
