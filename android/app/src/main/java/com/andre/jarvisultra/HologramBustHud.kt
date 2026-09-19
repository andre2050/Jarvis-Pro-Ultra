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
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * BUSTO HOLOGRÁFICO — A ÚNICA SKIN do JARVIS (v4.9.3), fiel à referência do senhor:
 * torso e capacete em wireframe branco-gelo flutuando no vazio preto, reator de
 * arco azul no peito com anéis concêntricos, fiação mecânica visível pelo casco
 * translúcido e brilho etéreo emanando do reator. "Projeção de sala de comando".
 *
 * Sem modelo 3D embutido: o busto é composto por linhas paramétricas com Stroke —
 * leve o bastante pra rodar liso em qualquer aparelho.
 */
@Composable
fun HologramBustHud(
    modifier: Modifier = Modifier,
    isSpeaking: Boolean = false,
    isThinking: Boolean = false,
    isListening: Boolean = false
) {
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

    // paleta da referência: wireframe gelo-branco, reator azul neon
    val ice = Color(0xFFE0F7FA)
    val iceDim = ice.copy(alpha = 0.30f)
    val reactorBlue = if (isListening) Color(0xFF7FE0FF) else Color(0xFF64B5F6)
    val reactorLight = Color(0xFFB3E5FC)

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val cx = w / 2f

        // ---- vazio preto com grade técnica muito sutil (blueprint) ----
        var gx = 0f
        val gridAlpha = 0.06f + 0.03f * sin(breathe * 2f * PI.toFloat())
        while (gx < w) {
            drawLine(iceDim.copy(alpha = gridAlpha), Offset(gx, 0f), Offset(gx, h), 1f)
            gx += w / 14f
        }
        var gy = 0f
        while (gy < h) {
            drawLine(iceDim.copy(alpha = gridAlpha), Offset(0f, gy), Offset(w, gy), 1f)
            gy += h / 14f
        }

        // ---- linha de varredura subindo e descendo ----
        val scanY = h * (0.08f + 0.84f * (if (scan < 0.5f) scan * 2f else (1f - scan) * 2f))
        drawLine(ice.copy(alpha = 0.15f), Offset(0f, scanY), Offset(w, scanY), 1.2f)

        val espGrosso = w * 0.012f
        val espMedio = w * 0.008f
        val tracejado = PathEffect.dashPathEffect(floatArrayOf(w * 0.02f, w * 0.015f))

        // ---- CAPACETE: silhueta facetada (referência: elmo com faceplate) ----
        val topo = h * 0.05f
        val yQueixo = h * 0.40f
        val silhuetaEsq = listOf(
            Offset(cx, topo),
            Offset(cx - w * 0.14f, topo + h * 0.02f),
            Offset(cx - w * 0.19f, topo + h * 0.11f),
            Offset(cx - w * 0.20f, topo + h * 0.22f),
            Offset(cx - w * 0.15f, topo + h * 0.30f),
            Offset(cx - w * 0.07f, yQueixo)
        )
        val silhuetaDir = silhuetaEsq.map { Offset(cx + (cx - it.x), it.y) }
        for (pontos in listOf(silhuetaEsq, silhuetaDir)) {
            for (i in 0 until pontos.size - 1) {
                drawLine(ice.copy(alpha = 0.9f), pontos[i], pontos[i + 1], espGrosso, StrokeCap.Round)
            }
        }
        // mandíbula
        drawLine(ice.copy(alpha = 0.9f), silhuetaEsq.last(), silhuetaDir.last(), espGrosso, StrokeCap.Round)

        // faceplate segmentado: costura central + laterais (como no wireframe da foto)
        drawLine(iceDim, Offset(cx, topo + h * 0.05f), Offset(cx, yQueixo - h * 0.01f), espMedio)
        for (sinal in listOf(-1f, 1f)) {
            drawLine(
                iceDim,
                Offset(cx + sinal * w * 0.19f, topo + h * 0.11f),
                Offset(cx + sinal * w * 0.13f, topo + h * 0.30f),
                espMedio
            )
        }
        // linhas de painel na testa
        drawLine(iceDim, Offset(cx - w * 0.10f, topo + h * 0.08f), Offset(cx + w * 0.10f, topo + h * 0.08f), 1f)
        drawLine(iceDim, Offset(cx - w * 0.13f, topo + h * 0.16f), Offset(cx + w * 0.13f, topo + h * 0.16f), 1f)

        // ---- olhos: fendas luminosas (alongam quando escutando) ----
        val yOlhos = topo + h * 0.16f
        val meiaFenda = w * (if (isListening) 0.065f else 0.05f)
        val brilhoOlhos = 0.55f + 0.45f * core
        for (sinal in listOf(-1f, 1f)) {
            val ex = cx + sinal * w * 0.105f
            drawLine(
                reactorLight.copy(alpha = 0.95f),
                Offset(ex - meiaFenda, yOlhos), Offset(ex + meiaFenda, yOlhos),
                w * 0.020f, StrokeCap.Round
            )
            drawCircle(reactorLight.copy(alpha = brilhoOlhos * 0.35f), radius = w * 0.045f, center = Offset(ex, yOlhos))
        }

        // ---- pescoço (só sugerido, deixa a cabeça "flutuar") ----
        drawLine(iceDim, Offset(cx - w * 0.05f, yQueixo), Offset(cx - w * 0.10f, h * 0.47f), espMedio)
        drawLine(iceDim, Offset(cx + w * 0.05f, yQueixo), Offset(cx + w * 0.10f, h * 0.47f), espMedio)

        // ---- OMBROS / TÓRAX: contorno do busto saindo do vazio ----
        val contorno = listOf(
            Offset(cx - w * 0.17f, h * 0.47f),
            Offset(cx - w * 0.40f, h * 0.56f),
            Offset(cx - w * 0.44f, h * 0.78f),
            Offset(cx - w * 0.44f, h)
        )
        val contornoDir = contorno.map { Offset(cx + (cx - it.x), it.y) }
        for (lado in listOf(contorno, contornoDir)) {
            for (i in 0 until lado.size - 1) {
                drawLine(ice.copy(alpha = 0.85f), lado[i], lado[i + 1], espGrosso, StrokeCap.Round)
            }
        }
        // trapézio dos ombros até o colar
        drawLine(ice.copy(alpha = 0.6f), Offset(cx - w * 0.17f, h * 0.47f), Offset(cx - w * 0.015f, h * 0.54f), espMedio)
        drawLine(ice.copy(alpha = 0.6f), Offset(cx + w * 0.17f, h * 0.47f), Offset(cx + w * 0.015f, h * 0.54f), espMedio)
        drawLine(ice.copy(alpha = 0.6f), Offset(cx - w * 0.17f, h * 0.47f), Offset(cx + w * 0.17f, h * 0.47f), espMedio)

        // fiação mecânica interna do tórax (vazada pelo casco translúcido)
        val wiring = listOf(
            Offset(cx - w * 0.24f, h * 0.62f) to Offset(cx - w * 0.13f, h * 0.62f),
            Offset(cx - w * 0.24f, h * 0.66f) to Offset(cx - w * 0.15f, h * 0.66f),
            Offset(cx + w * 0.13f, h * 0.62f) to Offset(cx + w * 0.24f, h * 0.62f),
            Offset(cx + w * 0.15f, h * 0.66f) to Offset(cx + w * 0.24f, h * 0.66f),
            Offset(cx - w * 0.34f, h * 0.70f) to Offset(cx - w * 0.28f, h * 0.70f),
            Offset(cx + w * 0.28f, h * 0.70f) to Offset(cx + w * 0.34f, h * 0.70f),
            Offset(cx - w * 0.36f, h * 0.82f) to Offset(cx - w * 0.30f, h * 0.82f),
            Offset(cx + w * 0.30f, h * 0.82f) to Offset(cx + w * 0.36f, h * 0.82f)
        )
        for ((a, b) in wiring) {
            drawLine(iceDim, a, b, espMedio, pathEffect = tracejado)
        }

        // ---- REATOR DE ARCO no peito: anéis concêntricos + cruz + núcleo ----
        val corePos = Offset(cx, h * 0.70f)
        val coreRaio = w * 0.085f
        // brilho etéreo emanando do reator (a luz da cena vem daqui, como na foto)
        val intensidade = 0.30f + 0.25f * core + (if (isSpeaking || isThinking) 0.15f else 0f)
        val glow = Brush.radialGradient(
            listOf(reactorBlue.copy(alpha = intensidade), Color.Transparent),
            corePos, coreRaio * 3.4f
        )
        drawCircle(brush = glow, radius = coreRaio * 3.4f, center = corePos)
        // anéis concêntricos
        drawCircle(reactorBlue.copy(alpha = 0.35f), radius = coreRaio * 2.05f, center = corePos, style = androidx.compose.ui.graphics.drawscope.Stroke(width = 1f))
        drawCircle(reactorBlue.copy(alpha = 0.55f), radius = coreRaio * 1.45f, center = corePos, style = androidx.compose.ui.graphics.drawscope.Stroke(width = espMedio))
        // marcas da cruz no anel externo
        for (angulo in listOf(0f, PI.toFloat() / 2f, PI.toFloat(), 3f * PI.toFloat() / 2f)) {
            val r1 = coreRaio * 2.05f
            val r2 = coreRaio * 2.35f
            drawLine(
                reactorBlue.copy(alpha = 0.6f),
                Offset(corePos.x + r1 * cos(angulo), corePos.y + r1 * sin(angulo)),
                Offset(corePos.x + r2 * cos(angulo), corePos.y + r2 * sin(angulo)),
                espMedio, StrokeCap.Round
            )
        }
        // núcleo pulsante
        val pulso = coreRaio * (1f + 0.08f * sin(core * 2f * PI.toFloat()))
        drawCircle(reactorBlue.copy(alpha = 0.85f), radius = pulso * 0.85f, center = corePos)
        drawCircle(reactorLight.copy(alpha = 0.95f), radius = pulso * 0.45f, center = corePos)
        drawCircle(Color.White.copy(alpha = 0.9f), radius = pulso * 0.16f, center = corePos)

        // ---- overlays de dados técnicos (canto do ombro direito + sob o reator) ----
        // retângulo tracejado atrás do ombro direito, como na foto
        val ombroDirRect = androidx.compose.ui.geometry.Rect(
            left = cx + w * 0.20f, top = h * 0.50f,
            right = cx + w * 0.38f, bottom = h * 0.72f
        )
        drawRect(
            iceDim.copy(alpha = 0.5f), topLeft = ombroDirRect.topLeft,
            size = ombroDirRect.size, style = androidx.compose.ui.graphics.drawscope.Stroke(width = 1f, pathEffect = tracejado)
        )
        // barrinhas de "leitura de dados" sob o reator
        var bx = cx - w * 0.30f
        val rnd = Random(7)
        while (bx < cx + w * 0.30f) {
            val larg = w * (0.015f + rnd.nextFloat() * 0.03f)
            val y = h * (0.88f + rnd.nextFloat() * 0.06f)
            drawLine(iceDim.copy(alpha = 0.6f), Offset(bx, y), Offset(bx + larg, y), 1.4f)
            bx += larg + w * 0.012f
        }

        // ---- partículas de HUD flutuando ao redor do busto ----
        val rnd2 = Random(42)
        repeat(12) {
            val a = rnd2.nextFloat() * 2f * PI.toFloat()
            val d = w * (0.34f + rnd2.nextFloat() * 0.26f)
            val px = cx + d * cos(a + breathe * 2f * PI.toFloat() * 0.04f)
            val py = h * 0.45f + d * 0.5f * sin(a + breathe * 2f * PI.toFloat() * 0.04f)
            if (py in 0f..h && px in 0f..w) {
                drawCircle(ice.copy(alpha = 0.22f), radius = 1.4f, center = Offset(px, py))
            }
        }
    }
}
