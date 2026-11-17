plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
}

// The measuring engine both apps share (UkurPaket and UkurAja): photo mode (MobileSAM-512, Depth Anything V2, box fit,
// focus sweep), the ArUco marker scale, the geometry, and the Urovo hardware scanner. Android-light: everything but the
// camera and the scanner runs on the PC in the unit tests.
android {
    namespace = "id.ukurpaket.core"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
        consumerProguardFiles("consumer-rules.pro")
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    testOptions {
        unitTests.all { t ->
            t.maxHeapSize = "3g"
            // -Pukur.markerOut=<dir>: keep the synthetic marker photos (tools/marker/check_opencv.py reads them)
            for (k in listOf("ukur.markerOut", "ukur.trace")) project.findProperty(k)?.let { t.systemProperty(k, it.toString()) }
        }
    }
}

dependencies {
    // MobileSAM (Apache 2.0) and Depth Anything V2 (Apache 2.0) run on the phone through ONNX Runtime (MIT)
    api("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")
    api("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    implementation("androidx.core:core-ktx:1.15.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("com.microsoft.onnxruntime:onnxruntime:1.20.0")
}

// Unit tests run on the PC: the desktop ONNX Runtime there, not the Android one (same classes, Android binaries).
configurations.matching { it.name.endsWith("UnitTestRuntimeClasspath") || it.name.endsWith("UnitTestCompileClasspath") }.configureEach {
    exclude(group = "com.microsoft.onnxruntime", module = "onnxruntime-android")
}
