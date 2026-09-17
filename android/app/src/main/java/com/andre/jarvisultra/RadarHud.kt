package com.andre.jarvisultra

import android.content.Context
import android.os.BatteryManager
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * O RADAR holográfico do JARVIS (v4.7.0): portado da edição desktop v5.1.x —
 * holograma circular teal com varredura de agulha vermelha, anéis concêntricos,
 * retículo, blips cintilantes e o núcleo pulsando com as leituras do aparelho
 * (bateria, hora, data). A agulha acelera quando ele pensa, fala ou escuta.
 */
@Composable
fun RadarHud(
    modifier: Modifier = Modifier,
    ctx: Context,
    isSpeaking: Boolean = false,
    isThinking: Boolean = false,
    isListening: Boolean = false
) {
    // paleta do radar (a mesma do desktop: teal holográfico + agulha vermelha)
    val teal = RadarTeal
    val tealDim = RadarTealDim
    val needle = RadarNeedle

    val transition = rememberInfiniteTransition(label = "radar")
    val breathe by transition.animateFloat(
        0f, 1f, infiniteRepeatable(tween(2600, easing = LinearEasing)), label = "breathe"
    )
    // agulha acelera com a energia: pensando 1.1s, falando 1.7s, ouvindo 2.2s, parada 4s
    val sweepDur = if (isThinking) 1100 else if (isSpeaking) 1700 else if (isListening) 2200 else 4000
    val sweep by transition.animateFloat(
        0f, 360f, infiniteRepeatable(tween(sweepDur, easing = LinearEasing)), label = "sweep"
    )
    val slowSpin by transition.animateFloat(
        0f, 360f, infiniteRepeatable(tween(24000, easing = LinearEasing)), label = "slow"
    )

    // blips fixos do radar (ângulo, distância) — cintilam com a respiração
    val blips = remember {
        List(7) { Pair(Random.nextFloat() * 2f * PI.toFloat(), 0.34f + Random.nextFloat() * 0.52f) }
    }

    // leitura viva do aparelho: bateria + hora, atualizada a cada segundo
    var pct by remember { mutableIntStateOf(0) }
    var horaTxt by remember { mutableStateOf("--:--") }
    var dataTxt by remember { mutableStateOf("") }
    LaunchedEffect(Unit) {
        val fmtHora = java.text.SimpleDateFormat("HH:mm", java.util.Locale("pt", "BR"))
        val fmtData = java.text.SimpleDateFormat("d 'de' MMM", java.util.Locale("pt", "BR"))
        while (true) {
            try {
                val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
                pct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY).coerceIn(0, 100)
            } catch (_: Exception) { }
            val now = java.util.Date()
            horaTxt = fmtHora.format(now)
            dataTxt = fmtData.format(now).uppercase()
            delay(1000)
        }
    }

    // Paints criados UMA vez (sem GC churn por frame)
    val paintLbl = remember { android.graphics.Paint().apply {
        isAntiAlias = true; textAlign = android.graphics.Paint.Align.CENTER
        typeface = android.graphics.Typeface.MONOSPACE; letterSpacing = 0.14f
    } }
    val paintInfo = remember { android.graphics.Paint().apply {
        isAntiAlias = true; textAlign = android.graphics.Paint.Align.CENTER
        typeface = android.graphics.Typeface.MONOSPACE; letterSpacing = 0.08f
    } }

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val cx = w / 2f
        val cy = h / 2f
        val r = minOf(w, h) * 0.42f
        val ca = Offset(cx, cy)

        // ---- halo de fundo (respira junto com o app) ----
        drawCircle(
            brush = Brush.radialGradient(
                colors = listOf(teal.copy(alpha = 0.14f + 0.10f * breathe), Color.Transparent),
                center = ca, radius = r * 1.12f
            ),
            radius = r * 1.12f, center = ca
        )

        // ---- retículo (linha horizontal e vertical) ----
        drawLine(tealDim.copy(alpha = 0.45f), Offset(cx - r * 1.05f, cy), Offset(cx + r * 1.05f, cy), 1f)
        drawLine(tealDim.copy(alpha = 0.45f), Offset(cx, cy - r * 1.05f), Offset(cx, cy + r * 1.05f), 1f)

        // ---- anéis concêntricos ----
        for (f in floatArrayOf(1.0f, 0.74f, 0.47f, 0.24f)) {
            drawCircle(
                teal.copy(alpha = if (f == 1f) 0.9f else 0.42f),
                radius = r * f, center = ca,
                style = Stroke(if (f == 1f) 2f else 1f)
            )
        }

        // ---- trilha da varredura (12 fatias com alpha decrescente) ----
        val trail = 48f
        for (i in 0 until 12) {
            drawArc(
                color = teal.copy(alpha = 0.20f * (1f - i / 12f)),
                startAngle = sweep - trail - i * (trail / 12f),
                sweepAngle = trail / 12f + 1f,
                useCenter = true,
                topLeft = Offset(cx - r, cy - r),
                size = Size(r * 2f, r * 2f)
            )
        }

        // ---- blips cintilando (orbitam bem devagar) ----
        blips.forEachIndexed { i, (bang, bdist) ->
            val flick = 0.35f + 0.65f * ((sin(breathe * 2f * PI.toFloat() + i * 1.9f) + 1f) / 2f)
            if (flick > 0.38f) {
                val a = bang + slowSpin * (PI.toFloat() / 180f) * 0.35f
                val bx = cx + r * bdist * cos(a)
                val by = cy + r * bdist * sin(a)
                drawCircle(needle.copy(alpha = 0.3f + 0.7f * flick), radius = 2.2f, center = Offset(bx, by))
            }
        }

        // ---- agulha vermelha ----
        val na = sweep * (PI.toFloat() / 180f)
        drawLine(needle, Offset(cx, cy), Offset(cx + r * cos(na), cy + r * sin(na)), 2f)

        // ---- rótulos técnicos ao redor ----
        paintLbl.textSize = r * 0.072f
        paintLbl.color = teal.copy(alpha = 0.8f).toArgbInt()
        listOf(-135f to "ULTRA", -45f to "RADAR", 135f to "GEMINI", 45f to "VOZ").forEach { (deg, lbl) ->
            val a = deg * (PI.toFloat() / 180f)
            drawContext.canvas.nativeCanvas.drawText(
                lbl, cx + r * 1.13f * cos(a), cy + r * 1.13f * sin(a) + r * 0.025f, paintLbl
            )
        }

        // ---- núcleo pulsante ----
        val energia = if (isSpeaking || isThinking) 1.6f else 1f
        val core = r * 0.15f * (1f + 0.22f * breathe * energia)
        drawCircle(
            brush = Brush.radialGradient(
                colors = listOf(teal.copy(alpha = 0.75f), tealDim.copy(alpha = 0.18f)),
                center = ca, radius = core * 2.4f
            ),
            radius = core * 2.4f, center = ca
        )
        drawCircle(teal, radius = core, center = ca)

        // ---- leituras do aparelho sob o núcleo ----
        paintInfo.textSize = r * 0.082f
        paintInfo.color = teal.copy(alpha = 0.92f).toArgbInt()
        drawContext.canvas.nativeCanvas.drawText("$horaTxt · $dataTxt", cx, cy + r * 0.55f, paintInfo)
        paintInfo.textSize = r * 0.072f
        paintInfo.color = tealDim.copy(alpha = 0.95f).toArgbInt()
        drawContext.canvas.nativeCanvas.drawText(
            if (isThinking) "PROCESSANDO ···" else "BAT $pct%",
            cx, cy + r * 0.68f, paintInfo
        )

        // ---- aura extra quando falando/ouvindo ----
        if (isSpeaking || isListening) {
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(teal.copy(alpha = 0.12f * breathe), Color.Transparent),
                    center = ca, radius = r * 1.2f
                ),
                radius = r * 1.2f, center = ca
            )
        }
    }
}

/** Paleta do radar — idêntica à edição desktop v5.1.x. */
val RadarTeal = Color(0xFF00E5C7)
val RadarTealDim = Color(0xFF0B6E63)
val RadarNeedle = Color(0xFFFF5A4D)

/** Converte a Color do Compose pro Int ARGB que o android.graphics.Paint espera. */
private fun Color.toArgbInt(): Int {
    val a = (alpha * 255f).toInt().coerceIn(0, 255)
    val r = (red * 255f).toInt().coerceIn(0, 255)
    val g = (green * 255f).toInt().coerceIn(0, 255)
    val b = (blue * 255f).toInt().coerceIn(0, 255)
    return (a shl 24) or (r shl 16) or (g shl 8) or b
}
