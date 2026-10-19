plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

android {
    namespace = "id.ukurpaket.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "id.ukurpaket.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 7
        versionName = "0.1.0-uji"
        // 32-bit kept too, so the app still installs (and can mark parcels for the hub) on older phones.
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a") }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Signed with the debug key so a test build installs without a keystore; use a real key for Play.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
    packaging {
        resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" }
        jniLibs { useLegacyPackaging = true }          // compressed native libraries: a smaller APK to send
    }
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            all { it.systemProperty("roborazzi.test.record", "true"); it.maxHeapSize = "3g" }
        }
    }
}

dependencies {
    implementation("com.google.ar:core:1.47.0")
    implementation("com.google.android.gms:play-services-code-scanner:16.1.0")
    // MobileSAM (Apache 2.0) runs on the phone through ONNX Runtime (MIT): tap or box -> parcel mask
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")

    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    testImplementation("junit:junit:4.13.2")
    // the same segmentation code on the PC: the desktop ONNX Runtime instead of the Android one
    testImplementation("com.microsoft.onnxruntime:onnxruntime:1.20.0")
    // reads the barcode of a real AnterAja label in ResiTest (the phone uses Google's scanner)
    testImplementation("com.google.zxing:core:3.5.3")
    // Screenshots of every screen on the JVM (no phone or emulator needed): ./gradlew testDebugUnitTest
    testImplementation("org.robolectric:robolectric:4.14.1")
    testImplementation("io.github.takahirom.roborazzi:roborazzi:1.40.1")
    testImplementation("io.github.takahirom.roborazzi:roborazzi-compose:1.40.1")
    testImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

// Robolectric's own downloader does not use the build's proxy; let Gradle fetch the Android jar instead.
val robolectricJars: Configuration by configurations.creating
dependencies { robolectricJars("org.robolectric:android-all-instrumented:15-robolectric-12650502-i7") }
val copyRobolectricJars by tasks.registering(Copy::class) {
    from(robolectricJars)
    into(layout.buildDirectory.dir("robolectric-jars"))
}
tasks.withType<Test>().configureEach {
    dependsOn(copyRobolectricJars)
    systemProperty("robolectric.offline", "true")
    systemProperty("robolectric.dependency.dir", layout.buildDirectory.dir("robolectric-jars").get().asFile.absolutePath)
}

// Unit tests run on the PC: use the desktop ONNX Runtime there, not the Android one (same classes, Android binaries).
configurations.matching { it.name.endsWith("UnitTestRuntimeClasspath") || it.name.endsWith("UnitTestCompileClasspath") }.configureEach {
    exclude(group = "com.microsoft.onnxruntime", module = "onnxruntime-android")
}
