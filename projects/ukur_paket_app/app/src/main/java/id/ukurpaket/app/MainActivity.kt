package id.ukurpaket.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import id.ukurpaket.app.ui.App
import id.ukurpaket.app.ui.AppModel
import id.ukurpaket.app.ui.UkurTheme

class MainActivity : ComponentActivity() {
    private val model: AppModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { UkurTheme { App(model, this) } }
    }

    override fun onResume() {
        super.onResume()
        model.onResume(this)     // ARCore may have just been installed from the Play Store
    }
}
