package com.andre.jarvisultra

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/**
 * v4.9.7: com a presença ligada, o SERVIÇO é o único dono do microfone.
 * A activity agora só: (1) marca se está visível (o serviço usa isso pra
 * decidir se precisa abrir o app ao ouvir "Jarvis"), (2) repassa o extra
 * wake (presença/widget) pro JarvisApp saudar e mostrar a conversa.
 * Nada de PAUSE/RESUME de microfone aqui — essa disputa derrubava o app.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tratarWake(intent)
        setContent {
            JarvisTheme {
                JarvisApp()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        tratarWake(intent)
    }

    private fun tratarWake(i: Intent?) {
        if (i?.getBooleanExtra(WakeCoord.EXTRA_WAKE, false) == true) {
            WakeCoord.wakePendente = true
        }
    }

    override fun onStart() {
        super.onStart()
        WakeCoord.appEmPrimeiroPlano = true
    }

    override fun onStop() {
        super.onStop()
        WakeCoord.appEmPrimeiroPlano = false
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
