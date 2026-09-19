package com.andre.jarvisultra

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.imageResource
import androidx.compose.ui.unit.IntSize
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * BUSTO HOLOGRÁFICO "QUASE REAL" (v4.9.4): a skin única do JARVIS agora é uma
 * projeção de altíssima qualidade — busto translúcido com reator de arco azul
 * gerado em arte fotorrealista (res/drawable-nodpi/holo_busto.png), animado
 * por cima com os efeitos de holograma: flutuação sutil, varredura, pulso do
 * reator, anéis de energia quando fala/pensa e partículas.
 */
@Composable
fun HologramBustHud(
    modifier: Modifier = Modifier,
    isSpeaking: Boolean = false,
    isThinking: Boolean = false,
    isListening: Boolean = false
) {
    val busto: ImageBitmap = ImageBitmap.imageResource(R.drawable.holo_busto)

    val transition = rememberInfiniteTransition(label = "busto")
    val breathe by transition.animateFloat(
        0f, 1f, infiniteRepeatable(tween(2600, easing = LinearEasing)), label = "breathe"
    )
    val scan by transition.animateFloat(
        0f, 1f, infiniteRepeatable(tween(4200, easing = LinearEasing)), label = "scan"
    )
    val core by transition.animateFloat(
        0f, 1f, infiniteRepeatable(
            tween(if (isThinking) 500 else if (isSpeaking) 700 else 1500, easing = LinearEasing)
        ), label = "core"
    )

    val ice = Color(0xFFE0F7FA)
    val reactorBlue = if (isListening) Color(0xFF7FE0FF) else Color(0xFF64B5F6)

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val cx = w / 2f

        // ---- a projeção quase real, com flutuação sutil de holograma ----
        val flicker = 0.93f + 0.07f * sin(breathe * 2f * PI.toFloat())
        drawImage(
            image = busto,
            dstSize = IntSize(w.toInt(), h.toInt()),
            alpha = flicker
        )

        // ---- linha de varredura atravessando a projeção ----
        val scanY = h * (0.06f + 0.88f * (if (scan < 0.5f) scan * 2f else (1f - scan) * 2f))
        drawLine(
            Brush.horizontalGradient(
                listOf(Color.Transparent, ice.copy(alpha = 0.22f), Color.Transparent),
                startX = 0f, endX = w
            ),
            Offset(0f, scanY), Offset(w, scanY), 1.6f
        )

        // ---- pulso do reator (posição real do reator na arte: 49.9%, 59.1%) ----
        val corePos = Offset(w * 0.499f, h * 0.591f)
        val intensidade = 0.28f + 0.22f * core + (if (isSpeaking || isThinking) 0.18f else 0f)
        val raioGlow = w * 0.32f
        drawCircle(
            brush = Brush.radialGradient(
                listOf(reactorBlue.copy(alpha = intensidade), Color.Transparent),
                corePos, raioGlow
            ),
            radius = raioGlow, center = corePos
        )
        // mini núcleo branco pulsante bem no centro do reator
        val pulso = w * (0.012f + 0.004f * sin(core * 2f * PI.toFloat()))
        drawCircle(Color.White.copy(alpha = 0.75f), radius = pulso, center = corePos)

        // ---- anéis de energia expandindo do reator quando fala/pensa ----
        if (isSpeaking || isThinking) {
            val raioAnel = w * (0.10f + 0.26f * core)
            val alphaAnel = (1f - core) * 0.55f
            drawCircle(
                reactorBlue.copy(alpha = alphaAnel),
                radius = raioAnel, center = corePos,
                style = Stroke(width = w * 0.008f)
            )
        }

        // ---- escutando: retículo tracejado em volta da projeção ----
        if (isListening) {
            val tracejado = PathEffect.dashPathEffect(floatArrayOf(w * 0.03f, w * 0.02f))
            drawCircle(
                Color(0xFF7FE0FF).copy(alpha = 0.45f),
                radius = w * 0.52f, center = Offset(cx, h * 0.52f),
                style = Stroke(width = 1.6f, pathEffect = tracejado)
            )
        }

        // ---- partículas de poeira de energia flutuando ----
        val rnd = Random(42)
        repeat(14) {
            val a = rnd.nextFloat() * 2f * PI.toFloat()
            val d = w * (0.30f + rnd.nextFloat() * 0.24f)
            val fase = breathe * 2f * PI.toFloat() * 0.05f + rnd.nextFloat()
            val px = cx + d * cos(a + fase)
            val py = h * 0.5f + d * 0.55f * sin(a + fase)
            if (px in 0f..w && py in 0f..h) {
                drawCircle(
                    (if (rnd.nextInt(3) == 0) reactorBlue else ice).copy(alpha = 0.30f),
                    radius = 1.3f + rnd.nextFloat(), center = Offset(px, py)
                )
            }
        }
    }
}
