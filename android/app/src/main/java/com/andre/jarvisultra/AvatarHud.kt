package com.andre.jarvisultra

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlinx.coroutines.delay
import kotlin.math.abs
import kotlin.math.min
import kotlin.math.sin
import kotlin.random.Random

/**
 * O AVATAR do J.A.R.V.I.S (v4.8.0) — cabeça humana holográfica com
 * dublagem real: a boca se articula em ~50 formas por segundo a partir
 * dos visemas do texto que ele está falando (não é um medidor de volume).
 *
 * Atuação: sobrancelhas acompanham a frase, olhar se move entre fixações,
 * piscadas naturais, leve aceno de cabeça nas sílabas tônicas.
 * Rosto como status: desvia o olhar pensando, encontra seu olhar ouvindo,
 * pálpebras caem dormindo.
 */
@Composable
fun AvatarHud(
    modifier: Modifier = Modifier,
    isSpeaking: Boolean = false,
    isThinking: Boolean = false,
    isListening: Boolean = false,
    speakText: String? = null
) {
    var blink by remember { mutableFloatStateOf(1f) }            // 1 aberto .. 0 fechado
    var lookX by remember { mutableFloatStateOf(0f) }
    var lookY by remember { mutableFloatStateOf(0f) }
    var browRaise by remember { mutableFloatStateOf(0f) }
    var nod by remember { mutableFloatStateOf(0f) }
    var lidDrop by remember { mutableFloatStateOf(0f) }         // pálpebra caída (dormindo)
    // boca atual (interpolada) e alvo
    var mW by remember { mutableFloatStateOf(0.30f) }
    var mOpen by remember { mutableFloatStateOf(0.01f) }
    var mRound by remember { mutableFloatStateOf(0f) }
    var mCorner by remember { mutableFloatStateOf(0f) }

    // agenda de visemas do texto em fala
    var agenda by remember { mutableStateOf<List<Pair<String, Long>>>(emptyList()) }
    var agendaT0 by remember { mutableStateOf(0L) }
    var agendaIdx by remember { mutableStateOf(0) }

    LaunchedEffect(speakText, isSpeaking) {
        if (isSpeaking && !speakText.isNullOrBlank()) {
            agenda = Visemas.fraseParaVisemas(speakText)
            agendaT0 = android.os.SystemClock.elapsedRealtime()
            agendaIdx = 0
        } else if (!isSpeaking) {
            agenda = emptyList(); agendaIdx = 0
        }
    }

    LaunchedEffect(isSpeaking, isThinking, isListening, agenda) {
        var t = 0f
        var alvoW = 0.30f; var alvoOpen = 0.01f; var alvoRound = 0f; var alvoCorner = 0f
        while (true) {
            t += 0.045f
            // ---- piscadas naturais (nunca enquanto dorme) ----
            val dormindo = !isSpeaking && !isThinking && !isListening
            if (!dormindo && Random.nextFloat() < 0.010f) { blink = 0f; delay(110); blink = 1f }
            lidDrop += ((if (dormindo) 0.72f else 0f) - lidDrop) * 0.06f

            // ---- olhar: fixações por estado ----
            if (Random.nextFloat() < 0.03f) {
                when {
                    isThinking -> { lookX = -0.55f + Random.nextFloat() * 0.35f; lookY = -0.45f + Random.nextFloat() * 0.5f }
                    isListening -> { lookX = Random.nextFloat() * 0.22f - 0.11f; lookY = Random.nextFloat() * 0.2f - 0.08f }
                    isSpeaking -> { lookX = Random.nextFloat() * 0.3f - 0.15f; lookY = Random.nextFloat() * 0.12f - 0.04f }
                    else -> { lookX = 0.1f; lookY = 0.12f }
                }
            }
            // ---- sobrancelhas acompanham ----
            val alvoBrow = when {
                isListening -> 0.6f
                isThinking -> 0.35f
                isSpeaking -> 0.45f
                else -> -0.25f
            }
            browRaise += (alvoBrow - browRaise) * 0.12f

            // ---- boca: consome a agenda de visemas ----
            if (isSpeaking && agenda.isNotEmpty()) {
                var elapsed = android.os.SystemClock.elapsedRealtime() - agendaT0
                while (agendaIdx < agenda.size && elapsed > agenda[agendaIdx].second) {
                    elapsed -= agenda[agendaIdx].second
                    agendaIdx++
                    agendaT0 = android.os.SystemClock.elapsedRealtime()
                }
                if (agendaIdx >= agenda.size) {
                    agendaIdx = agenda.size - 1        // segura o último até isSpeaking cair
                }
                val (v, _) = agenda[agendaIdx]
                val f = Visemas.FORMAS[v] ?: Visemas.FORMAS["MM"]!!
                alvoW = f.largura; alvoOpen = f.abertura; alvoRound = f.arredonda; alvoCorner = f.canto
                if (v == "AA" || v == "EH" || v == "OH") nod = 1f   // tônica: aceno
            } else if (isSpeaking) {
                alvoW = 0.32f; alvoOpen = 0.4f + 0.3f * abs(sin(t * 8f)); alvoRound = 0.2f; alvoCorner = 0.05f
            } else if (isThinking) {
                alvoW = 0.28f; alvoOpen = 0.05f + 0.03f * sin(t * 2.2f); alvoRound = 0.1f; alvoCorner = 0.1f
            } else {
                alvoW = 0.30f; alvoOpen = 0.012f; alvoRound = 0f; alvoCorner = 0f
            }
            mW += (alvoW - mW) * 0.45f
            mOpen += (alvoOpen - mOpen) * 0.45f
            mRound += (alvoRound - mRound) * 0.45f
            mCorner += (alvoCorner - mCorner) * 0.45f
            nod *= 0.86f
            delay(45)
        }
    }

    val Cyan = Color(0xFF00E5C7)
    val CyanDim = Cyan.copy(alpha = 0.5f)
    val glow = Cyan.copy(alpha = if (isSpeaking || isListening) 0.16f else if (isThinking) 0.12f else 0.07f)

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val cx = w / 2f
        val cy = h * 0.52f
        val rx = min(w, h) * 0.30f
        val ry = min(w, h) * 0.37f

        // aura
        drawCircle(
            brush = Brush.radialGradient(listOf(glow, Color.Transparent), Offset(cx, cy), ry * 1.6f),
            radius = ry * 1.6f, center = Offset(cx, cy)
        )

        val nodY = sin(System.nanoTime() / 90_000_000.0).toFloat() * 3.5f * nod
        val skullTop = Offset(cx - rx, cy - ry + nodY)
        val skullBot = Offset(cx + rx, cy + ry + nodY)

        // ---- crânio ----
        drawOval(
            color = Cyan.copy(alpha = 0.9f),
            topLeft = skullTop, size = Size(rx * 2, ry * 2),
            style = Stroke(width = 3f)
        )
        // halo do crânio
        drawOval(
            color = Cyan.copy(alpha = 0.15f),
            topLeft = Offset(skullTop.x - rx * 0.12f, skullTop.y - ry * 0.08f),
            size = Size(rx * 2.24f, ry * 2.14f),
            style = Stroke(width = 7f)
        )
        // linha de cabelo
        drawArc(
            color = CyanDim,
            startAngle = 200f, sweepAngle = 140f, useCenter = false,
            topLeft = Offset(cx - rx * 0.9f, cy - ry * 0.92f + nodY),
            size = Size(rx * 1.8f, ry * 1.2f),
            style = Stroke(width = 2f, cap = StrokeCap.Round)
        )
        // mandíbula
        drawArc(
            color = CyanDim,
            startAngle = 210f, sweepAngle = 120f, useCenter = false,
            topLeft = Offset(cx - rx * 0.78f, cy - ry * 0.05f + nodY),
            size = Size(rx * 1.56f, ry * 1.5f),
            style = Stroke(width = 2f, cap = StrokeCap.Round)
        )
        // linhas de holograma
        for (fy in listOf(-0.6f, -0.25f, 0.1f, 0.45f, 0.72f)) {
            val halfW = rx * (1f - abs(fy) * 0.32f)
            drawLine(
                color = Cyan.copy(alpha = 0.10f),
                start = Offset(cx - halfW, cy + ry * fy + nodY),
                end = Offset(cx + halfW, cy + ry * fy + nodY),
                strokeWidth = 1f
            )
        }
        // nariz
        drawPath(Path().apply {
            moveTo(cx - rx * 0.06f, cy - ry * 0.02f + nodY)
            lineTo(cx, cy + ry * 0.14f + nodY)
            lineTo(cx + rx * 0.06f, cy - ry * 0.02f + nodY)
        }, color = CyanDim, style = Stroke(width = 2f, cap = StrokeCap.Round))

        // ---- olhos ----
        val eyeY = cy - ry * 0.18f + nodY
        val openH = (1f - lidDrop) * blink
        for (lado in listOf(-1f, 1f)) {
            val ex = cx + lado * rx * 0.40f
            val eyeW = rx * 0.30f
            val eyeH = ry * 0.115f * (0.12f + 0.88f * openH)
            // contorno do olho (lente)
            drawOval(
                color = Cyan.copy(alpha = 0.85f),
                topLeft = Offset(ex - eyeW, eyeY - eyeH),
                size = Size(eyeW * 2, eyeH * 2),
                style = Stroke(width = 2f)
            )
            // pupila — olhar entre fixações
            if (openH > 0.25f) {
                drawCircle(
                    color = Cyan,
                    radius = min(eyeW, eyeH) * 0.55f,
                    center = Offset(ex + lookX * eyeW * 0.55f, eyeY + lookY * eyeH * 0.7f)
                )
            }
            // sobrancelha — acompanha a frase
            val by = eyeY - ry * 0.14f - browRaise * ry * 0.075f + nodY
            drawLine(
                color = Cyan,
                start = Offset(ex - eyeW * 1.05f, by + lado * browRaise * 2.5f),
                end = Offset(ex + eyeW * 1.05f, by - lado * browRaise * 2.5f),
                strokeWidth = 4f, cap = StrokeCap.Round
            )
        }

        // ---- boca articulada por visemas ----
        val my = cy + ry * 0.52f + nodY
        val halfW = rx * mW * 1.15f
        val open = ry * 0.24f * mOpen
        val corner = mCorner * ry * 0.05f
        val boca = Path()
        if (mRound > 0.5f) {
            // arredondada (OH/UH): quase um círculo
            val r = halfW * 0.8f
            boca.addOval(
                androidx.compose.ui.geometry.Rect(
                    Offset(cx - r, my - open * 0.5f), Size(r * 2, open + r * 0.6f)
                )
            )
            drawPath(boca, color = Cyan.copy(alpha = 0.85f), style = Stroke(width = 3f))
        } else {
            val topo = my - open * 0.55f
            val base = my + open
            boca.moveTo(cx - halfW, my - corner)
            boca.cubicTo(cx - halfW * 0.45f, topo, cx + halfW * 0.45f, topo, cx + halfW, my - corner)
            boca.cubicTo(cx + halfW * 0.4f, base, cx - halfW * 0.4f, base, cx - halfW, my - corner)
            // brilho interno quando aberta + contorno
            if (mOpen > 0.35f) drawPath(boca, color = Color(0x1400E5C7))
            drawPath(boca, color = Cyan.copy(alpha = 0.85f), style = Stroke(width = 3.5f, cap = StrokeCap.Round))
        }
    }
}
