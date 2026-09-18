package com.andre.jarvisultra

import android.app.Activity
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * MODO MESA/CARRO (v4.7.2): o celular virado um painel do Homem de Ferro.
 * Tela cheia sempre ligada: radar holográfico grande, relógio vivo, clima
 * ao vivo (Open-Meteo, sem chave) e bateria. Toque em qualquer lugar pra sair.
 */
class DeskModeActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // painel de mesa: a tela não apaga enquanto o modo estiver aberto
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContent { DeskModeScreen() }
    }
}

@Composable
fun DeskModeScreen() {
    val ctx = LocalContext.current
    val teal = RadarTeal
    val tealDim = RadarTealDim

    // relógio vivo (atualiza a cada segundo)
    var agora by remember { mutableStateOf(Date()) }
    LaunchedEffect(Unit) {
        while (true) {
            agora = Date()
            delay(1000)
        }
    }

    // clima ao vivo: busca na abertura e renova a cada 15 min
    var clima by remember { mutableStateOf<String?>(null) }
    var climaStatus by remember { mutableStateOf<String>("sincronizando clima…") }
    LaunchedEffect(Unit) {
        while (true) {
            when (val r = buscarClima(ctx)) {
                null -> climaStatus = "clima indisponível (sem GPS/permissão de local)"
                else -> {
                    clima = r
                    climaStatus = ""
                }
            }
            delay(15 * 60 * 1000L)
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .clickable { (ctx as? Activity)?.finish() },
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth()
        ) {
            Spacer(Modifier.statusBarsPadding())

            // ---- relógio gigante ----
            val fmtHora = SimpleDateFormat("HH:mm", Locale.getDefault())
            Text(
                fmtHora.format(agora),
                fontSize = 64.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Light,
                color = teal
            )
            val fmtData = SimpleDateFormat("EEEE, d 'de' MMMM", Locale("pt", "BR"))
            Text(
                fmtData.format(agora).uppercase(),
                fontSize = 13.sp,
                fontFamily = FontFamily.Monospace,
                color = tealDim,
                letterSpacing = 3.sp
            )

            Spacer(Modifier.height(24.dp))

            // ---- o radar gigante (o mesmo do HUD, expandido) ----
            RadarHud(
                modifier = Modifier
                    .fillMaxWidth(0.94f)
                    .aspectRatio(1f),
                ctx = ctx,
                isThinking = false,
                isSpeaking = false,
                isListening = false
            )

            Spacer(Modifier.height(24.dp))

            // ---- clima ao vivo ----
            if (clima != null) {
                Text(clima!!, fontSize = 16.sp, fontFamily = FontFamily.Monospace, color = teal)
            } else if (climaStatus.isNotEmpty()) {
                Text(climaStatus, fontSize = 12.sp, fontFamily = FontFamily.Monospace, color = tealDim)
            }

            Spacer(Modifier.height(36.dp))
            Text(
                "JARVIS · MODO MESA — TOQUE PARA SAIR",
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                color = tealDim,
                letterSpacing = 2.sp
            )
        }
    }
}

/**
 * Busca o clima atual via Open-Meteo (grátis, sem chave). Devolve
 * "26°C · Céu limpo" ou null quando não dá (sem local, sem rede).
 */
private suspend fun buscarClima(ctx: Context): String? = withContext(Dispatchers.IO) {
    try {
        val fina = ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.ACCESS_FINE_LOCATION)
        val grossa = ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.ACCESS_COARSE_LOCATION)
        if (fina != PackageManager.PERMISSION_GRANTED && grossa != PackageManager.PERMISSION_GRANTED) {
            return@withContext null
        }
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val local = lm.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            ?: lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            ?: return@withContext null

        val url = "https://api.open-meteo.com/v1/forecast?latitude=${local.latitude}" +
            "&longitude=${local.longitude}&current=temperature_2m,weather_code"
        val http = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .build()
        val req = Request.Builder().url(url)
            .header("User-Agent", "JarvisProUltra-Android/${JarvisBrain.APP_VERSION}")
            .build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return@withContext null
            val json = JSONObject(resp.body?.string() ?: return@withContext null)
            val atual = json.getJSONObject("current")
            val temp = atual.optDouble("temperature_2m", 0.0).toInt()
            val codigo = atual.optInt("weather_code", -1)
            "${temp}°C · ${descricaoClima(codigo)}"
        }
    } catch (e: Exception) {
        null
    }
}

/** Códigos WMO do Open-Meteo em português. */
private fun descricaoClima(codigo: Int): String = when (codigo) {
    0 -> "Céu limpo"
    1, 2 -> "Parcialmente nublado"
    3 -> "Nublado"
    45, 48 -> "Nevoeiro"
    51, 53, 55 -> "Garoa"
    56, 57 -> "Garoa congelante"
    61, 63, 65 -> "Chuva"
    66, 67 -> "Chuva congelante"
    71, 73, 75, 77 -> "Neve"
    80, 81, 82 -> "Pancadas de chuva"
    85, 86 -> "Pancadas de neve"
    95, 96, 99 -> "Tempestade"
    else -> "—"
}
