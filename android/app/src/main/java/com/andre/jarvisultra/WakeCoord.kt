package com.andre.jarvisultra

import android.content.Context
import android.content.Intent

/**
 * v4.9.5: coordenação de presença — quem é dono do microfone em cada momento.
 *
 * Regra da casa: com o app ABERTO, o microfone é do app (o serviço de presença
 * pausa). Com o app em segundo plano, o microfone volta pro serviço, que fica
 * de prontidão ouvindo "Jarvis". Quando o serviço acorda, marca wakePendente
 * e a UI arma as mãos livres na hora — o app abre JÁ ESCUTANDO, não mudo.
 */
object WakeCoord {
    /** true quando a MainActivity está visível (entre onStart e onStop). */
    @Volatile var appEmPrimeiroPlano = false

    /** o serviço acordou com "Jarvis" — o JarvisScreen consome e arma a escuta. */
    @Volatile var wakePendente = false

    const val EXTRA_WAKE = "wake"

    fun avisarServico(ctx: Context, action: String) {
        try {
            ctx.startForegroundService(
                Intent(ctx, JarvisWakeService::class.java).setAction(action))
        } catch (_: Exception) { }
    }
}
