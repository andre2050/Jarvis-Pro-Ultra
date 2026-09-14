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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Paint
import androidx.compose.ui.graphics.PaintingStyle
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.text.font.FontWeight
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * O reator de arco do JARVIS (v4.3.0): dial circular vermelho, estilo Homem de Ferro —
 * anéis com marcações, blooms de luz pulsantes, anel de chevrons rotativo, grade radial
 * e o núcleo com a leitura viva do aparelho (bateria, hora, data).
 */
@Composable
fun ArcReactorHud(
    modifier: Modifier = Modifier,
    ctx: Context,
    isSpeaking: Boolean = false,
    isThinking: Boolean = false,
    isListening: Boolean = false
) {
    val transition = rememberInfiniteTransition(label = "reactor")
    val breathe by transition.animateFloat(
        0f, 1f, infiniteRepeatable(tween(2600, easing = LinearEasing)), label = "breathe"
    )
    val slowSpin by transition.animateFloat(
        0f, 360f, infiniteRepeatable(tween(if (isListening) 6000 else 22000, easing = LinearEasing)), label = "spin"
    )
    val fastSpin by transition.animateFloat(
        0f, 360f, infiniteRepeatable(tween(if (isThinking) 900 else 14000, easing = LinearEasing)), label = "spin2"
    )

    // leitura viva do aparelho: bateria + hora, atualizada a cada segundo
    var pct by remember { mutableIntStateOf(0) }
    var horaTxt by remember { mutableStateOf("--:--") }
    var dataTxt by remember { mutableStateOf("") }
    androidx.compose.runtime.LaunchedEffect(Unit) {
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

    val red = Cyan               // paleta já convertida pra vermelho em MainActivity.kt
    val redDim = CyanDim
    val glow = red.copy(alpha = 0.55f + 0.35f * breathe)

    // Paints criados UMA vez e reciclados por frame (sem GC churn)
    val paintLbl = remember { android.graphics.Paint().apply {
        isAntiAlias = true; textAlign = android.graphics.Paint.Align.CENTER
        typeface = android.graphics.Typeface.MONOSPACE; letterSpacing = 0.12f
    } }
    val paintBig = remember { android.graphics.Paint().apply {
        isAntiAlias = true; textAlign = android.graphics.Paint.Align.CENTER
        typeface = android.graphics.Typeface.create(android.graphics.Typeface.MONOSPACE, android.graphics.Typeface.BOLD)
    } }
    val paintSmall = remember { android.graphics.Paint().apply {
        isAntiAlias = true; textAlign = android.graphics.Paint.Align.CENTER
        typeface = android.graphics.Typeface.MONOSPACE; letterSpacing = 0.15f
    } }
    val paintPct = remember { android.graphics.Paint().apply {
        isAntiAlias = true; textAlign = android.graphics.Paint.Align.CENTER
        typeface = android.graphics.Typeface.MONOSPACE
    } }

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val cx = w / 2f
        val cy = h / 2f
        val r = minOf(w, h) * 0.46f

        // ---- núcleo: disco com grade radial e brilho por trás do número ----
        drawCircle(
            brush = Brush.radialGradient(
                colors = listOf(red.copy(alpha = 0.28f + 0.10f * breathe), Color.Transparent),
                center = Offset(cx, cy), radius = r * 0.62f
            ),
            radius = r * 0.62f, center = Offset(cx, cy)
        )
        rotate(degrees = slowSpin * 0.3f, pivot = Offset(cx, cy)) {
            for (i in 0 until 16) {
                val a = i * (360f / 16) * (PI.toFloat() / 180f)
                val inner = r * 0.20f
                val outer = r * 0.40f
                drawLine(
                    redDim.copy(alpha = 0.35f),
                    Offset(cx + inner * cos(a), cy + inner * sin(a)),
                    Offset(cx + outer * cos(a), cy + outer * sin(a)),
                    1.2f
                )
            }
        }
        drawCircle(redDim.copy(alpha = 0.5f), radius = r * 0.40f, center = Offset(cx, cy), style = Stroke(1.2f))

        // ---- anel de chevrons (dashes triangulares) girando ----
        rotate(degrees = slowSpin, pivot = Offset(cx, cy)) {
            val nChev = 40
            val rr = r * 0.52f
            for (i in 0 until nChev) {
                val a0 = i * (360f / nChev) * (PI.toFloat() / 180f)
                val a1 = (i * (360f / nChev) + (360f / nChev) * 0.55f) * (PI.toFloat() / 180f)
                drawLine(
                    red.copy(alpha = if (i % 5 == 0) 0.85f else 0.35f),
                    Offset(cx + rr * cos(a0), cy + rr * sin(a0)),
                    Offset(cx + rr * cos(a1), cy + rr * sin(a1)),
                    if (i % 5 == 0) 3.5f else 2f
                )
            }
        }

        // ---- ticks do dial (marcações finas, como um instrumento) ----
        val nTicks = 72
        val rTickOuter = r * 0.82f
        for (i in 0 until nTicks) {
            val big = i % 6 == 0
            val a = i * (360f / nTicks) * (PI.toFloat() / 180f) + fastSpin * 0.02f
            val len = if (big) 14f else 6f
            val inner = rTickOuter - len
            drawLine(
                red.copy(alpha = if (big) 0.7f else 0.30f),
                Offset(cx + inner * cos(a), cy + inner * sin(a)),
                Offset(cx + rTickOuter * cos(a), cy + rTickOuter * sin(a)),
                if (big) 2f else 1f
            )
        }

        // ---- bezel externo (anel duplo) ----
        drawCircle(redDim.copy(alpha = 0.55f), radius = r * 0.86f, center = Offset(cx, cy), style = Stroke(1.5f))
        drawCircle(redDim.copy(alpha = 0.35f), radius = r * 0.995f, center = Offset(cx, cy), style = Stroke(1.5f))

        // ---- blooms de luz pulsantes distribuídos no anel externo ----
        val nBlooms = 7
        for (i in 0 until nBlooms) {
            val a = (i * (360f / nBlooms) + slowSpin * 0.15f) * (PI.toFloat() / 180f)
            val bx = cx + r * 0.92f * cos(a)
            val by = cy + r * 0.92f * sin(a)
            val flick = 0.4f + 0.6f * ((sin(breathe * 2f * PI.toFloat() + i * 1.7f) + 1f) / 2f)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(glow.copy(alpha = 0.55f * flick), Color.Transparent),
                    center = Offset(bx, by), radius = r * 0.22f
                ),
                radius = r * 0.22f, center = Offset(bx, by)
            )
        }

        // ---- setas/triângulos no topo e nos cardeais ----
        listOf(-90f, 0f, 90f, 180f).forEach { deg ->
            val a = deg * (PI.toFloat() / 180f)
            val bx = cx + r * 1.02f * cos(a)
            val by = cy + r * 1.02f * sin(a)
            val ang = a + PI.toFloat() / 2f
            val p1 = Offset(bx + 9f * cos(ang), by + 9f * sin(ang))
            val p2 = Offset(bx - 9f * cos(ang), by - 9f * sin(ang))
            val tipA = a
            val tip = Offset(bx + 11f * cos(tipA), by + 11f * sin(tipA))
            val path = androidx.compose.ui.graphics.Path().apply {
                moveTo(p1.x, p1.y); lineTo(tip.x, tip.y); lineTo(p2.x, p2.y); close()
            }
            drawPath(path, red.copy(alpha = 0.6f))
        }

        // ---- rótulos curtos ao redor (capsule labels) ----
        val labels = listOf("VOZ", "GPS", "MEM", "REDE")
        paintLbl.textSize = r * 0.075f
        paintLbl.color = red.copy(alpha = 0.85f).toArgbInt()
        labels.forEachIndexed { i, lbl ->
            val a = (45f + i * 90f) * (PI.toFloat() / 180f)
            val lx = cx + r * 0.68f * cos(a)
            val ly = cy + r * 0.68f * sin(a)
            drawContext.canvas.nativeCanvas.drawText(lbl, lx, ly, paintLbl)
        }

        // ---- núcleo: glifo triangular estilo Stark (pulsa com o breathe) ----
        val s = r * 0.40f * (0.97f + 0.03f * breathe)
        fun vert(angDeg: Float): Offset {
            val a = angDeg * (PI.toFloat() / 180f)
            return Offset(cx + s * cos(a), cy + s * sin(a))
        }
        val v0 = vert(-90f); val v1 = vert(30f); val v2 = vert(150f)
        val triPath = androidx.compose.ui.graphics.Path().apply {
            moveTo(v0.x, v0.y); lineTo(v1.x, v1.y); lineTo(v2.x, v2.y); close()
        }
        drawPath(
            triPath,
            brush = Brush.radialGradient(
                colors = listOf(red.copy(alpha = 0.30f + 0.12f * breathe), red.copy(alpha = 0.06f)),
                center = Offset(cx, cy), radius = s
            )
        )
        drawPath(triPath, red.copy(alpha = 0.9f), style = Stroke(width = 2.4f))
        // triângulo interno, levemente menor, girando bem devagar
        rotate(degrees = slowSpin * 0.08f, pivot = Offset(cx, cy)) {
            fun vertIn(angDeg: Float): Offset {
                val a = angDeg * (PI.toFloat() / 180f)
                return Offset(cx + s * 0.58f * cos(a), cy + s * 0.58f * sin(a))
            }
            val i0 = vertIn(-90f); val i1 = vertIn(30f); val i2 = vertIn(150f)
            val innerPath = androidx.compose.ui.graphics.Path().apply {
                moveTo(i0.x, i0.y); lineTo(i1.x, i1.y); lineTo(i2.x, i2.y); close()
            }
            drawPath(innerPath, redDim.copy(alpha = 0.7f), style = Stroke(width = 1.4f))
        }
        drawCircle(red.copy(alpha = 0.85f + 0.15f * breathe), radius = 3.5f, center = Offset(cx, cy))

        if (isThinking) {
            paintBig.textSize = r * 0.13f
            paintBig.color = red.copy(alpha = 0.95f).toArgbInt()
            drawContext.canvas.nativeCanvas.drawText("···", cx, cy + s * 0.9f, paintBig)
        } else {
            paintPct.textSize = r * 0.085f
            paintPct.color = redDim.copy(alpha = 0.85f).toArgbInt()
            drawContext.canvas.nativeCanvas.drawText("BAT $pct%", cx, cy + s + r * 0.16f, paintPct)
        }
        paintSmall.textSize = r * 0.095f
        paintSmall.color = red.copy(alpha = 0.9f).toArgbInt()
        drawContext.canvas.nativeCanvas.drawText(
            "$horaTxt · $dataTxt", cx, cy + s + r * 0.30f, paintSmall
        )

        // ---- aura extra quando falando/escutando ----
        if (isSpeaking || isListening) {
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(red.copy(alpha = 0.10f * breathe), Color.Transparent),
                    center = Offset(cx, cy), radius = r * 1.15f
                ),
                radius = r * 1.15f, center = Offset(cx, cy)
            )
        }
    }
}

/** Converte a Color do Compose pro Int ARGB que o android.graphics.Paint espera. */
private fun Color.toArgbInt(): Int {
    val a = (alpha * 255f).toInt().coerceIn(0, 255)
    val r = (red * 255f).toInt().coerceIn(0, 255)
    val g = (green * 255f).toInt().coerceIn(0, 255)
    val b = (blue * 255f).toInt().coerceIn(0, 255)
    return (a shl 24) or (r shl 16) or (g shl 8) or b
}
