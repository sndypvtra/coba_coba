plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

// UkurAja: the parcel app with only what the field needs (scan the label, measure by photo with the printed marker,
// weight, history, export), on the same measuring engine as UkurPaket (:core).
android {
    namespace = "id.ukuraja.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "id.ukuraja.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
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
        jniLibs { useLegacyPackaging = true }
    }
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            all { t -> t.systemProperty("roborazzi.test.record", "true"); t.maxHeapSize = "3g" }
        }
    }
}

dependencies {
    implementation(project(":core"))
    implementation("com.google.android.gms:play-services-code-scanner:16.1.0")

    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("com.microsoft.onnxruntime:onnxruntime:1.20.0")
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

// Unit tests run on the PC: the desktop ONNX Runtime there, not the Android one (same classes, Android binaries).
configurations.matching { it.name.endsWith("UnitTestRuntimeClasspath") || it.name.endsWith("UnitTestCompileClasspath") }.configureEach {
    exclude(group = "com.microsoft.onnxruntime", module = "onnxruntime-android")
}
