package com.andre.jarvisultra

/**
 * v4.9.7: coordenação da presença — UMA DONA DO MICROFONE.
 *
 * Mudança de arquitetura que mata o "abre e fecha" de vez: quando a
 * presença 24h está LIGADA, o SERVIÇO é o único dono do microfone, com o
 * app aberto ou fechado. O app NUNCA abre uma segunda escuta Vosk (era
 * essa disputa de microfone que derrubava o processo — crash nativo,
 * sem exceção Java, invisível pra qualquer caixa-preta).
 *
 * Fluxo: o serviço escuta "Jarvis" → marca wakePendente (o app sauda e
 * mostra a conversa) → o comando dito em seguida chega em comandoPendente
 * → o JarvisScreen processa e responde. Sem PAUSE, sem RESUME, sem
 * corrida, sem double Model do Vosk.
 */
object WakeCoord {
    /** true quando a MainActivity está visível (entre onStart e onStop). */
    @Volatile var appEmPrimeiroPlano = false

    /** o serviço acordou com "Jarvis" — o JarvisApp consome e saúda. */
    @Volatile var wakePendente = false

    /** comando capturado pelo serviço após o wake — o JarvisApp consome e responde. */
    @Volatile var comandoPendente: String? = null

    const val EXTRA_WAKE = "wake"
}
