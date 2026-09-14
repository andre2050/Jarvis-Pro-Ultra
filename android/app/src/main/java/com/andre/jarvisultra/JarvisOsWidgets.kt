package com.andre.jarvisultra

import android.app.ActivityManager
import android.content.Context
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat

/**
 * Painelzinhos de dado ao estilo "JARVIS OS" (v4.4.0): pequenas cápsulas com
 * rótulo + valor real do aparelho, flanqueando o reator — igual aos widgets
 * de CPU/rede da tela do Stark Industries, só que lendo dados de verdade.
 */
@Composable
fun StatChip(label: String, value: String) {
    androidx.compose.foundation.layout.Column(
        modifier = Modifier
            .background(HoloCard.copy(alpha = 0.7f), RoundedCornerShape(6.dp))
            .border(1.dp, HoloLine, RoundedCornerShape(6.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally
    ) {
        Text(label, fontSize = 8.sp, fontFamily = FontFamily.Monospace, color = CyanDim, letterSpacing = 1.sp)
        Text(value, fontSize = 11.sp, fontFamily = FontFamily.Monospace, color = Cyan)
    }
}

/** % de memória RAM em uso — leitura real via ActivityManager. */
fun memPct(ctx: Context): String {
    return try {
        val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val info = ActivityManager.MemoryInfo()
        am.getMemoryInfo(info)
        if (info.totalMem <= 0L) "--"
        else (((info.totalMem - info.availMem).toDouble() / info.totalMem) * 100).toInt().toString()
    } catch (e: Exception) { "--" }
}

/** Status real da conexão: WIFI, DADOS ou OFF — via ConnectivityManager. */
fun netStatus(ctx: Context): String {
    return try {
        val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return "OFF"
        when {
            caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "WIFI"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "DADOS"
            else -> "OFF"
        }
    } catch (e: Exception) { "OFF" }
}

/** Permissão de localização concedida? — checagem real via ContextCompat. */
fun hasLocationPermission(ctx: Context): Boolean {
    return ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
        ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
}
