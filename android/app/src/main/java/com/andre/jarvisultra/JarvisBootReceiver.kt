package com.andre.jarvisultra

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * v4.9.0: o celular reiniciou? O JARVIS se rearma sozinho.
 * - O alarme do briefing matinal é reagendado (sem restrição de app visível)
 * - v4.9.9: a presença 24h NÃO tenta ligar o microfone sozinha aqui — o
 *   Android 14 exige o app visível na tela pra abrir um serviço de
 *   microfone em primeiro plano, e não existe exceção pra BOOT_COMPLETED
 *   nessa regra (tentar = crash garantido, sem captura possível). Em vez
 *   disso, uma notificação convida o senhor a reabrir o app — aí sim, com
 *   o app visível, a presença religa sem erro.
 * (damos 20s de fôlego pro sistema terminar de subir)
 */
class JarvisBootReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val appCtx = ctx.applicationContext
        android.os.Handler(appCtx.mainLooper).postDelayed({
            try {
                if (SettingsStore.getBriefingOn(appCtx)) BriefingScheduler.agendar(appCtx)
                if (SettingsStore.getWake24h(appCtx)) avisarPresenca(appCtx)
            } catch (e: Exception) { }
        }, 20_000)
    }

    private fun avisarPresenca(ctx: Context) {
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(
            NotificationChannel("jarvis_boot", "Rearme após reiniciar",
                NotificationManager.IMPORTANCE_DEFAULT))
        val abrir = PendingIntent.getActivity(
            ctx, 2,
            Intent(ctx, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val n = Notification.Builder(ctx, "jarvis_boot")
            .setContentTitle("Toque para reativar a presença do JARVIS")
            .setContentText("O celular reiniciou — abra o app pra eu voltar a ouvir \"Jarvis\".")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setAutoCancel(true)
            .setContentIntent(abrir)
            .build()
        nm.notify(4243, n)
    }
}
