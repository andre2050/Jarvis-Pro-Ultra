package com.andre.jarvisultra

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlinx.coroutines.delay
import kotlin.math.abs
import kotlin.math.sin
import kotlin.random.Random

/**
 * O rosto holográfico do JARVIS PRO ULTRA em Compose:
 * olhos que piscam em intervalos naturais, pupilas que vagam,
 * e boca que se anima em sincronia com a fala (isSpeaking) ou pulsa
 * devagar quando está pensando (isThinking).
 */
@Composable
fun HologramFace(
    modifier: Modifier = Modifier,
    isSpeaking: Boolean = false,
    isThinking: Boolean = false
) {
    var blink by remember { mutableFloatStateOf(1f) }        // 1 = aberto, 0 = fechado
    var lookX by remember { mutableFloatStateOf(0f) }
    var lookY by remember { mutableFloatStateOf(0f) }
    var mouthOpen by remember { mutableFloatStateOf(0f) }
    var pulse by remember { mutableFloatStateOf(0f) }

    val blinkAnim by animateFloatAsState(blink, tween(90), label = "blink")

    LaunchedEffect(isSpeaking, isThinking) {
        var t = 0f
        while (true) {
            t += 0.05f
            // piscada aleatória a cada 2–6s
            if (Random.nextFloat() < 0.012f) { blink = 0f; delay(120); blink = 1f }
            // pupilas vagam suavemente
            if (Random.nextFloat() < 0.02f) {
                lookX = Random.nextFloat() * 8f - 4f
                lookY = Random.nextFloat() * 5f - 2.5f
            }
            // boca: oscila rápido falando, pulsa devagar pensando
            mouthOpen = when {
                isSpeaking -> 0.35f + 0.35f * abs(sin(t * 9f))
                isThinking -> 0.12f + 0.08f * sin(t * 2.5f)
                else -> 0.06f + 0.04f * sin(t * 1.8f)
            }
            pulse = 0.5f + 0.5f * sin(t * 1.2f)
            delay(50)
        }
    }

    val glow = Cyan.copy(alpha = 0.10f + 0.06f * pulse)
    val core = Cyan
    val coreDim = Cyan.copy(alpha = 0.55f)

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val cx = w / 2f
        val cy = h / 2f
        val r = minOf(w, h) * 0.42f

        // aura de fundo
        drawCircle(
            brush = Brush.radialGradient(
                colors = listOf(glow, Color.Transparent),
                center = Offset(cx, cy),
                radius = r * 1.35f
            ),
            radius = r * 1.35f,
            center = Offset(cx, cy)
        )

        // anel reator (gira com o pulso)
        val arcSweep = 70f + 40f * pulse
        drawArc(
            color = coreDim,
            startAngle = -60f + pulse * 360f,
            sweepAngle = arcSweep,
            useCenter = false,
            topLeft = Offset(cx - r, cy - r),
            size = Size(r * 2, r * 2),
            style = Stroke(width = 4f, cap = StrokeCap.Round)
        )
        drawArc(
            color = core.copy(alpha = 0.25f),
            startAngle = 150f - pulse * 300f,
            sweepAngle = 40f,
            useCenter = false,
            topLeft = Offset(cx - r, cy - r),
            size = Size(r * 2, r * 2),
            style = Stroke(width = 2f, cap = StrokeCap.Round)
        )

        // olhos
        val eyeW = r * 0.16f
        val eyeH = r * 0.26f
        val eyeY = cy - r * 0.18f
        val gap = r * 0.30f
        val openH = eyeH * blinkAnim
        listOf(cx - gap, cx + gap).forEach { ex ->
            drawRoundRect(
                color = core,
                topLeft = Offset(ex - eyeW / 2 + lookX * 0.4f, eyeY - openH / 2 + lookY * 0.3f),
                size = Size(eyeW, openH.coerceAtLeast(2.5f)),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(eyeW / 2, eyeW / 2)
            )
        }

        // boca: curva que abre/fecha com a fala
        val mouthW = r * 0.5f
        val mouthY = cy + r * 0.30f
        val openAmount = mouthOpen
        val path = Path().apply {
            moveTo(cx - mouthW / 2, mouthY)
            val midY = mouthY - openAmount * r * 0.14f + r * 0.04f
            quadraticBezierTo(cx, mouthY + (1f - openAmount * 2f) * r * 0.06f, cx + mouthW / 2, mouthY)
            lineTo(cx + mouthW / 2, mouthY)
            quadraticBezierTo(cx, mouthY + (1f - openAmount * 2f) * r * 0.10f, cx - mouthW / 2, mouthY)
            close()
        }
        // preenchimento suave da boca quando aberta
        if (openAmount > 0.15f) {
            drawPath(path, core.copy(alpha = 0.20f + openAmount * 0.25f))
        }
        drawPath(path, core, style = Stroke(width = 2.5f, cap = StrokeCap.Round))
    }
}
