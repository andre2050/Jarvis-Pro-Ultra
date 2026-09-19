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
 * v4.9.5: agora a activity PARTICIPA da presença 24h:
 *  - aberta pelo serviço (wake=true) ou pelo widget → marca wakePendente,
 *    e o JarvisApp arma as mãos livres sozinho: o app abre JÁ ESCUTANDO
 *  - onStart: o microfone passa a ser do APP (serviço de presença pausa)
 *  - onStop: o microfone VOLTA pro serviço de presença (se estiver ligado)
 *    — antes ninguém devolvia, e a presença morria após a primeira chamada
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
        // app visível: microfone do app, presença em espera
        if (SettingsStore.getWake24h(this)) WakeCoord.avisarServico(this, JarvisWakeService.ACTION_PAUSE)
    }

    override fun onStop() {
        super.onStop()
        WakeCoord.appEmPrimeiroPlano = false
        // app saiu de cena: presença retoma a escuta de fundo
        if (SettingsStore.getWake24h(this)) WakeCoord.avisarServico(this, JarvisWakeService.ACTION_RESUME)
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
