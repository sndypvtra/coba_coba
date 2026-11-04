package id.ukurpaket.app

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.KeyEvent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import id.ukurpaket.app.scan.HardwareScanner
import id.ukurpaket.app.scan.KeyWedge
import id.ukurpaket.app.ui.App
import id.ukurpaket.app.ui.AppModel
import id.ukurpaket.app.ui.UkurTheme

class MainActivity : ComponentActivity() {
    private val model: AppModel by viewModels()
    private val scanner = HardwareScanner.Receiver { model.onHardwareScan(it) }
    private val wedge = KeyWedge { model.onHardwareScan(it) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { UkurTheme { App(model, this) } }
    }

    override fun onResume() {
        super.onResume()
        model.onResume(this)     // ARCore may have just been installed from the Play Store
        scanner.register(this)   // Urovo scan key, Intent output
    }

    override fun onPause() {
        scanner.unregister(this)
        super.onPause()
    }

    /**
     * Urovo scan key in keyboard output, or a Bluetooth/USB scanner: read only where no text field is on screen.
     * Overriding (not calling) this androidx-restricted method is the way to see the keys before any view does.
     */
    @SuppressLint("RestrictedApi")
    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (model.takesHardwareScan &&
            wedge.onKey(event.action == KeyEvent.ACTION_DOWN, event.keyCode, event.unicodeChar, event.eventTime)) return true
        return super.dispatchKeyEvent(event)
    }
}
