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
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlin.math.hypot
import kotlin.math.sin

/**
 * Fundo HUD (v3.1.0): grade técnica que respira, circuitos com pulsos de dados
 * viajando pelas linhas, linha de varredura que varre a tela e brackets nos
 * cantos — o QG do senhor, direto de filme de ficção.
 */
@Composable
fun HudBackground(
    modifier: Modifier = Modifier,
    isThinking: Boolean = false,
    isListening: Boolean = false
) {
    val transition = rememberInfiniteTransition(label = "hud")
    val scan by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(9000, easing = LinearEasing)),
        label = "scan"
    )
    val flow by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(3600, easing = LinearEasing)),
        label = "flow"
    )
    val breathe by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2400, easing = LinearEasing)),
        label = "breathe"
    )

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height

        // ---- grade técnica que respira ----
        val cell = 52f
        val gridAlpha = 0.08f + 0.04f * sin(breathe * 2f * Math.PI.toFloat())
        var gx = 0f
        while (gx < w) {
            drawLine(HoloLine.copy(alpha = gridAlpha), Offset(gx, 0f), Offset(gx, h), 1f)
            gx += cell
        }
        var gy = 0f
        while (gy < h) {
            drawLine(HoloLine.copy(alpha = gridAlpha), Offset(0f, gy), Offset(w, gy), 1f)
            gy += cell
        }

        // ---- circuitos com pulsos de dados ----
        val circuits = listOf(
            listOf(Offset(0f, h * 0.14f), Offset(w * 0.22f, h * 0.14f), Offset(w * 0.26f, h * 0.08f), Offset(w * 0.55f, h * 0.08f)),
            listOf(Offset(w, h * 0.30f), Offset(w * 0.78f, h * 0.30f), Offset(w * 0.74f, h * 0.22f), Offset(w * 0.50f, h * 0.22f)),
            listOf(Offset(0f, h * 0.86f), Offset(w * 0.18f, h * 0.86f), Offset(w * 0.24f, h * 0.92f), Offset(w * 0.62f, h * 0.92f)),
            listOf(Offset(w, h * 0.72f), Offset(w * 0.82f, h * 0.72f), Offset(w * 0.76f, h * 0.80f), Offset(w * 0.40f, h * 0.80f)),
            listOf(Offset(w * 0.5f, 0f), Offset(w * 0.5f, h * 0.05f), Offset(w * 0.42f, h * 0.10f), Offset(w * 0.42f, h * 0.16f))
        )
        circuits.forEachIndexed { ci, pts ->
            val lineCol = HoloLine.copy(alpha = 0.55f)
            for (i in 0 until pts.size - 1) {
                drawLine(lineCol, pts[i], pts[i + 1], 1.5f)
            }
            // nós dos circuitos
            pts.forEach { drawCircle(HoloLine.copy(alpha = 0.8f), 2.5f, it) }
            // pulso de dados viajando pela linha
            var totalLen = 0f
            val segLens = mutableListOf<Float>()
            for (i in 0 until pts.size - 1) {
                val l = hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y)
                segLens.add(l)
                totalLen += l
            }
            var d = ((flow + ci * 0.23f) % 1f) * totalLen
            var pos = pts.first()
            for (i in segLens.indices) {
                if (d <= segLens[i]) {
                    val f = if (segLens[i] > 0f) d / segLens[i] else 0f
                    pos = Offset(
                        pts[i].x + (pts[i + 1].x - pts[i].x) * f,
                        pts[i].y + (pts[i + 1].y - pts[i].y) * f
                    )
                    break
                }
                d -= segLens[i]
                pos = pts[i + 1]
            }
            drawCircle(Cyan.copy(alpha = 0.18f), 9f, pos)
            drawCircle(Cyan.copy(alpha = 0.75f), 3.5f, pos)
        }

        // ---- linha de varredura ----
        val scanY = scan * h
        drawRect(
            brush = Brush.verticalGradient(
                colors = listOf(Cyan.copy(alpha = 0.02f), Cyan.copy(alpha = 0.06f)),
                startY = scanY - 130f,
                endY = scanY
            ),
            topLeft = Offset(0f, (scanY - 130f).coerceAtLeast(0f)),
            size = Size(w, 130f)
        )
        drawLine(Cyan.copy(alpha = 0.10f), Offset(0f, scanY), Offset(w, scanY), 2f)

        // ---- brackets dos cantos ----
        val inset = 12f
        val arm = 38f
        val bc = Cyan.copy(alpha = 0.30f)
        listOf(
            Offset(inset, inset) to Pair(Offset(inset + arm, inset), Offset(inset, inset + arm)),
            Offset(w - inset, inset) to Pair(Offset(w - inset - arm, inset), Offset(w - inset, inset + arm)),
            Offset(inset, h - inset) to Pair(Offset(inset + arm, h - inset), Offset(inset, h - inset - arm)),
            Offset(w - inset, h - inset) to Pair(Offset(w - inset - arm, h - inset), Offset(w - inset, h - inset - arm))
        ).forEach { (corner, ends) ->
            drawLine(bc, corner, ends.first, 2f)
            drawLine(bc, corner, ends.second, 2f)
        }

        // ---- reação ao estado ----
        if (isListening) {
            // aura pulsante embaixo (modo mãos-livres ligado)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Cyan.copy(alpha = 0.05f + 0.04f * sin(breathe * 2f * Math.PI.toFloat())), androidx.compose.ui.graphics.Color.Transparent),
                    center = Offset(w / 2f, h),
                    radius = h * 0.45f
                ),
                radius = h * 0.45f,
                center = Offset(w / 2f, h)
            )
        }
        if (isThinking) {
            // arcos concêntricos no canto inferior direito (processando)
            val rr = 70f
            drawArc(
                color = Cyan.copy(alpha = 0.20f),
                startAngle = breathe * 360f,
                sweepAngle = 90f,
                useCenter = false,
                topLeft = Offset(w - rr * 1.4f, h - rr * 1.4f),
                size = Size(rr, rr),
                style = Stroke(width = 3f)
            )
            drawArc(
                color = Cyan.copy(alpha = 0.12f),
                startAngle = -breathe * 270f,
                sweepAngle = 60f,
                useCenter = false,
                topLeft = Offset(w - rr * 1.2f, h - rr * 1.2f),
                size = Size(rr * 0.6f, rr * 0.6f),
                style = Stroke(width = 2f)
            )
        }
    }
}
