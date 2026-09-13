plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.andre.jarvisultra"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.andre.jarvisultra"
        minSdk = 26
        targetSdk = 34
        versionCode = 21
        versionName = "4.3.0"
    }

    signingConfigs {
        create("release") {
            // keystore gerado na máquina que compila; NUNCA commitar as senhas
            storeFile = file(System.getenv("JARVIS_KEYSTORE") ?: "jarvis-release.jks")
            storePassword = System.getenv("JARVIS_KEYSTORE_PASS") ?: ""
            keyAlias = System.getenv("JARVIS_KEY_ALIAS") ?: "jarvis"
            keyPassword = System.getenv("JARVIS_KEY_PASS") ?: ""
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (System.getenv("JARVIS_KEYSTORE") != null) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.11" }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    implementation("com.alphacephei:vosk-android:0.3.47")
    val composeBom = platform("androidx.compose:compose-bom:2024.05.00")
    implementation(composeBom)
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
