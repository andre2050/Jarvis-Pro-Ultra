package com.andre.jarvisultra

import java.text.Normalizer

/**
 * Visemas — dublagem real, boca sem idioma (v4.8.0).
 *
 * A articulação vem da REDUÇÃO UNICODE do texto: todo caractere é
 * reduzido (NFD, sem acentos, transliterado quando cirílico/grego) e
 * mapeado pra uma forma de boca. Um único conjunto de regras serve
 * latino, cirílico e grego.
 *
 * Formas: fechamentos (MM), aberturas (AA) e arredondamentos (OH/UH) —
 * não um medidor de volume.
 */
object Visemas {

    /** Parâmetros de cada forma: (largura, abertura, arredondamento, canto) */
    data class Forma(val largura: Float, val abertura: Float, val arredonda: Float, val canto: Float)

    val FORMAS = mapOf(
        "MM" to Forma(0.30f, 0.01f, 0.00f, 0.30f),   // descanso: sorriso leve
        "AA" to Forma(0.28f, 1.00f, 0.15f, 0.15f),   // vogal aberta sorrindo (não triste)
        "EH" to Forma(0.32f, 0.55f, 0.05f, 0.25f),
        "IH" to Forma(0.34f, 0.26f, 0.00f, 0.35f),
        "OH" to Forma(0.18f, 0.80f, 0.85f, 0.12f),
        "UH" to Forma(0.15f, 0.40f, 0.90f, 0.10f),
        "FF" to Forma(0.29f, 0.16f, 0.10f, 0.30f),
        "SS" to Forma(0.22f, 0.08f, 0.00f, 0.35f)
    )

    private val TRANSLIT = mapOf(
        'а' to "a", 'б' to "b", 'в' to "v", 'г' to "g", 'д' to "d", 'е' to "e", 'ё' to "e",
        'ж' to "zh", 'з' to "z", 'и' to "i", 'й' to "i", 'к' to "k", 'л' to "l", 'м' to "m",
        'н' to "n", 'о' to "o", 'п' to "p", 'р' to "r", 'с' to "s", 'т' to "t", 'у' to "u",
        'ф' to "f", 'х' to "kh", 'ц' to "ts", 'ч' to "ch", 'ш' to "sh", 'щ' to "sh",
        'ы' to "i", 'э' to "e", 'ю' to "iu", 'я' to "ia",
        'α' to "a", 'β' to "v", 'γ' to "g", 'δ' to "d", 'ε' to "e", 'ζ' to "z", 'η' to "i",
        'θ' to "th", 'ι' to "i", 'κ' to "k", 'λ' to "l", 'μ' to "m", 'ν' to "n", 'ξ' to "ks",
        'ο' to "o", 'π' to "p", 'ρ' to "r", 'σ' to "s", 'ς' to "s", 'τ' to "t", 'υ' to "u",
        'φ' to "f", 'χ' to "kh", 'ψ' to "ps", 'ω' to "o"
    )

    private val VOGAIS = mapOf('a' to "AA", 'e' to "EH", 'i' to "IH", 'o' to "OH", 'u' to "UH", 'y' to "IH", 'w' to "UH")
    private val BILABIAIS = setOf('m', 'b', 'p')
    private val LABIODENTAIS = setOf('f', 'v')
    private val FRESTA = setOf('s', 'z', 'c', 'x', 'j', 't', 'd', 'k', 'g', 'r', 'l', 'n', 'h', 'q')

    /** Reduz qualquer alfabeto suportado a uma sequência base latinizada. */
    fun reduzir(texto: String): String {
        val t = Normalizer.normalize(texto.lowercase(), Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
        return buildString { for (c in t) append(TRANSLIT[c] ?: c.toString()) }
    }

    private fun visema(c: Char): String? = when {
        VOGAIS.containsKey(c) -> VOGAIS[c]
        c in BILABIAIS -> "MM"
        c in LABIODENTAIS -> "FF"
        c in FRESTA -> "SS"
        else -> null
    }

    /**
     * Agenda de formas de boca: [(visema, duração_ms)] — ~50 formas/s
     * interpoladas no desenho. Pausas naturais em vírgulas e pontos.
     */
    fun fraseParaVisemas(texto: String, velocidade: Float = 0.85f): List<Pair<String, Long>> {
        val base = (62f / velocidade.coerceAtLeast(0.5f)).toLong()
        val agenda = mutableListOf<Pair<String, Long>>()
        var buf: String? = null
        var dur = 0L
        for (ch in reduzir(texto)) {
            when {
                ch in " ,;" -> {
                    buf?.let { agenda.add(it to dur) }
                    buf = null; dur = 0
                    agenda.add("MM" to (base * 3 / 2))
                }
                ch in ".!?:…" -> {
                    buf?.let { agenda.add(it to dur) }
                    buf = null; dur = 0
                    agenda.add("MM" to base * 4)
                }
                else -> {
                    val v = visema(ch) ?: continue
                    if (v == buf) dur += base * 3 / 5
                    else {
                        buf?.let { agenda.add(it to dur) }
                        buf = v; dur = base
                    }
                }
            }
        }
        buf?.let { agenda.add(it to dur) }
        if (agenda.isEmpty()) agenda.add("MM" to 200)
        return agenda
    }

    // ---------- anti-eco ----------

    /** Minúsculas e sem acento — comparação robusta pro anti-eco. */
    fun normalizar(t: String): String = reduzir(t).filter { it.isLetterOrDigit() || it == ' ' }.trim()

    /**
     * O ouvido pegou a cauda da própria fala do JARVIS? Descarta —
     * ele nunca responde à própria última frase.
     */
    fun ehEco(ouvido: String, ultimaFalada: String): Boolean {
        val o = normalizar(ouvido)
        val f = normalizar(ultimaFalada)
        if (o.length < 8 || f.length < 8) return false
        if (o in f || f.takeLast(24) in o) return true
        val to = o.split(' ').filter { it.length > 2 }
        if (to.isEmpty()) return false
        val tf = f.split(' ').toSet()
        val iguais = to.count { it in tf }
        return iguais.toFloat() / to.size > 0.7f
    }
}
