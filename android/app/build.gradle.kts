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
        versionCode = 37
        versionName = "4.9.0"
    }

    // Assinatura FIXA (v4.7.1): toda build — sandbox, Actions ou PC — usa a mesma
    // chave (android/keys/jarvis-update.jks), então toda atualização instala por cima
    // sem o erro "app não foi instalado" de assinatura diferente.
    // Chave pessoal do projeto: apps avulsos, sem loja. Variáveis de ambiente ainda
    // têm prioridade caso você um dia queira assinar com outra chave.
    val ksJarvis = rootProject.file("keys/jarvis-update.jks")
    signingConfigs {
        getByName("debug") {
            storeFile = ksJarvis
            storePassword = System.getenv("JARVIS_KEYSTORE_PASS") ?: "jarvis2026"
            keyAlias = System.getenv("JARVIS_KEY_ALIAS") ?: "jarvis"
            keyPassword = System.getenv("JARVIS_KEY_PASS") ?: "jarvis2026"
        }
        create("release") {
            storeFile = System.getenv("JARVIS_KEYSTORE")?.let { file(it) } ?: ksJarvis
            storePassword = System.getenv("JARVIS_KEYSTORE_PASS") ?: "jarvis2026"
            keyAlias = System.getenv("JARVIS_KEY_ALIAS") ?: "jarvis"
            keyPassword = System.getenv("JARVIS_KEY_PASS") ?: "jarvis2026"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("release")
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
    // Câmera nativa v4.6.0 (frontal + traseira)
    implementation("androidx.camera:camera-core:1.3.3")
    implementation("androidx.camera:camera-camera2:1.3.3")
    implementation("androidx.camera:camera-lifecycle:1.3.3")
    implementation("androidx.camera:camera-view:1.3.3")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
