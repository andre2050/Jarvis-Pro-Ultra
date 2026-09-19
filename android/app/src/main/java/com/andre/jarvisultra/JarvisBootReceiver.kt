package com.andre.jarvisultra

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * v4.9.0: o celular reiniciou? O JARVIS se rearma sozinho.
 * - Presença 24h volta a escutar se estava ligada
 * - O alarme do briefing matinal é reagendado
 * (damos 20s de fôlego pro sistema terminar de subir)
 */
class JarvisBootReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        android.os.Handler(ctx.mainLooper).postDelayed({
            try {
                if (SettingsStore.getWake24h(ctx)) JarvisWakeService.ligar(ctx)
                if (SettingsStore.getBriefingOn(ctx)) BriefingScheduler.agendar(ctx)
            } catch (e: Exception) { }
        }, 20_000)
    }
}
