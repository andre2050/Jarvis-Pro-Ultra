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

// Paleta v4.3.0: reator de arco vermelho (os nomes "Cyan…" ficaram de herança do HUD ciano original)
val Cyan = Color(0xFFFF2A2A)
val CyanDim = Color(0xFF8A0F12)
val HoloBg = Color(0xFF0A0303)
val HoloCard = Color(0xFF170707)
val HoloLine = Color(0xFF3A1414)

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
