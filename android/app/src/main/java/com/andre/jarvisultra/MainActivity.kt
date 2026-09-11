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

val Cyan = Color(0xFF22D3EE)
val CyanDim = Color(0xFF0E7490)
val HoloBg = Color(0xFF070B14)
val HoloCard = Color(0xFF0D1526)
val HoloLine = Color(0xFF1B2B4A)

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
