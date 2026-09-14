package com.andre.jarvisultra

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            JarvisTheme {
                JarvisApp()
            }
        }
    }
}

// Paleta v4.4.0: JARVIS OS - azul-ciano estilo Stark Industries
val Cyan = Color(0xFF2FD8FF)
val CyanDim = Color(0xFF0E5A78)
val HoloBg = Color(0xFF040B14)
val HoloCard = Color(0xFF071522)
val HoloLine = Color(0xFF163247)

@Composable
fun JarvisTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Cyan,
            onPrimary = HoloBg,
            background = HoloBg,
            surface = HoloCard,
            onSurface = Color(0xFFD7E5F4),
            outline = HoloLine,
        ),
        content = content
    )
}
