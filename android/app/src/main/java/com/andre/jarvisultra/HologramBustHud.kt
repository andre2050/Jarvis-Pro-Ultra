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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * BUSTO HOLOGRÁFICO (v4.9.0): tema novo inspirado direto na referência do senhor —
 * o capacete e os ombros do Homem de Ferro em wireframe azul-gélido, flutuando sobre
 * uma grade técnica, com o reator de arco pulsando no peito. Mais "projeção de
 * engenharia" do que rosto animado — o visual de holograma de sala de comando.
 *
 * Como não há um modelo 3D real embutido, o busto é composto por curvas/linhas
 * paramétricas (capacete, viseira, mandíbula, colar, ombros) desenhadas com Stroke —
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

    val ice = Color(0xFFBFE8FF)
    val iceDim = Color(0x33BFE8FF)
    val coreColor = if (isListening) Color(0xFF6CFFD8) else Color(0xFF7FD6FF)

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val cx = w / 2f
        val topoCapacete = h * 0.10f
        val alturaCapacete = h * 0.40f
        val larguraOmbros = w * 0.92f
        val yOmbros = h * 0.62f

        // ---- grade técnica de fundo, tipo blueprint ----
        var gx = 0f
        val gridAlpha = 0.10f + 0.05f * sin(breathe * 2f * PI.toFloat())
        while (gx < w) {
            drawLine(iceDim.copy(alpha = gridAlpha), Offset(gx, 0f), Offset(gx, h), 1f)
            gx += w / 14f
        }
        var gy = 0f
        while (gy < h) {
            drawLine(iceDim.copy(alpha = gridAlpha), Offset(0f, gy), Offset(w, gy), 1f)
            gy += h / 14f
        }

        // ---- linha de scan horizontal subindo e descendo ----
        val scanY = h * (0.08f + 0.84f * (if (scan < 0.5f) scan * 2f else (1f - scan) * 2f))
        drawLine(ice.copy(alpha = 0.18f), Offset(0f, scanY), Offset(w, scanY), 1.4f)

        val linhaFina = Stroke(width = w * 0.006f, cap = StrokeCap.Round)

        // ---- capacete: contorno tipo "elmo" facetado, igual à referência ----
        val topo = Offset(cx, topoCapacete)
        val larguraTesta = w * 0.30f
        val yTesta = topoCapacete + alturaCapacete * 0.28f
        val yQueixo = topoCapacete + alturaCapacete

        // contorno esquerdo/direito do capacete (facetado, não curva suave)
        val pontosEsq = listOf(
            topo,
            Offset(cx - larguraTesta * 0.55f, topoCapacete + alturaCapacete * 0.08f),
            Offset(cx - larguraTesta, yTesta),
            Offset(cx - larguraTesta * 0.92f, topoCapacete + alturaCapacete * 0.55f),
            Offset(cx - larguraTesta * 0.62f, topoCapacete + alturaCapacete * 0.80f),
            Offset(cx - larguraTesta * 0.30f, yQueixo)
        )
        val pontosDir = pontosEsq.map { Offset(cx + (cx - it.x), it.y) }

        for (pontos in listOf(pontosEsq, pontosDir)) {
            for (i in 0 until pontos.size - 1) {
                drawLine(ice.copy(alpha = 0.85f), pontos[i], pontos[i + 1], w * 0.012f, StrokeCap.Round)
            }
        }
        // mandíbula fechando o queixo
        drawLine(ice.copy(alpha = 0.85f), pontosEsq.last(), pontosDir.last(), w * 0.012f, StrokeCap.Round)

        // viseira/olhos: duas fendas horizontais luminosas
        val yOlhos = topoCapacete + alturaCapacete * 0.42f
        for (sinal in listOf(-1f, 1f)) {
            val ex = cx + sinal * larguraTesta * 0.42f
            drawLine(coreColor.copy(alpha = 0.9f), Offset(ex - w * 0.05f, yOlhos), Offset(ex + w * 0.05f, yOlhos), w * 0.02f, StrokeCap.Round)
        }
        // brilho pulsante nos olhos (mais forte falando/pensando)
        val brilhoOlhos = 0.4f + 0.6f * core
        for (sinal in listOf(-1f, 1f)) {
            val ex = cx + sinal * larguraTesta * 0.42f
            drawCircle(coreColor.copy(alpha = brilhoOlhos * 0.5f), radius = w * 0.05f, center = Offset(ex, yOlhos))
        }

        // linhas técnicas faciais (grade de painel, como no wireframe da foto)
        for (f in listOf(0.15f, 0.30f, 0.65f)) {
            val y = topoCapacete + alturaCapacete * f
            val larguraNesseY = larguraTesta * (1f - f * 0.35f)
            drawLine(iceDim.copy(alpha = 0.5f), Offset(cx - larguraNesseY, y), Offset(cx + larguraNesseY, y), 1f)
        }

        // ---- colar/pescoço ----
        drawLine(ice.copy(alpha = 0.7f), Offset(cx - larguraTesta * 0.3f, yQueixo), Offset(cx - larguraOmbros * 0.22f, yOmbros * 0.86f), w * 0.01f, StrokeCap.Round)
        drawLine(ice.copy(alpha = 0.7f), Offset(cx + larguraTesta * 0.3f, yQueixo), Offset(cx + larguraOmbros * 0.22f, yOmbros * 0.86f), w * 0.01f, StrokeCap.Round)

        // ---- ombros/peitoral facetados ----
        val yPeito = yOmbros * 0.9f
        val ombroEsq = listOf(
            Offset(cx - larguraOmbros * 0.22f, yOmbros * 0.86f),
            Offset(cx - larguraOmbros * 0.50f, yOmbros * 0.95f),
            Offset(cx - larguraOmbros * 0.50f, h * 0.96f)
        )
        val ombroDir = ombroEsq.map { Offset(cx + (cx - it.x), it.y) }
        for (lado in listOf(ombroEsq, ombroDir)) {
            for (i in 0 until lado.size - 1) {
                drawLine(ice.copy(alpha = 0.8f), lado[i], lado[i + 1], w * 0.012f, StrokeCap.Round)
            }
        }
        // linha do peitoral unindo os dois ombros por baixo do colar
        drawLine(ice.copy(alpha = 0.55f), ombroEsq[0], ombroDir[0], w * 0.008f, StrokeCap.Round)

        // ---- reator de arco no peito ----
        val corePos = Offset(cx, yPeito + h * 0.03f)
        val coreRaio = w * (0.06f + 0.015f * sin(core * 2f * PI.toFloat()))
        drawCircle(coreColor.copy(alpha = 0.25f), radius = coreRaio * 2.2f, center = corePos)
        drawCircle(coreColor.copy(alpha = 0.55f), radius = coreRaio * 1.4f, center = corePos, style = linhaFina)
        drawCircle(coreColor.copy(alpha = 0.95f), radius = coreRaio * 0.7f, center = corePos)
        drawCircle(Color.White.copy(alpha = 0.9f), radius = coreRaio * 0.3f, center = corePos)

        // ---- pontinhos de dados flutuando (partículas de HUD) ----
        val rnd = Random(42)
        repeat(10) {
            val a = rnd.nextFloat() * 2f * PI.toFloat()
            val d = w * (0.35f + rnd.nextFloat() * 0.25f)
            val px = cx + d * cos(a + breathe * 2f * PI.toFloat() * 0.05f)
            val py = h * 0.4f + d * 0.5f * sin(a + breathe * 2f * PI.toFloat() * 0.05f)
            if (py in 0f..h) drawCircle(ice.copy(alpha = 0.25f), radius = 1.6f, center = Offset(px, py))
        }
    }
}
