package com.andre.jarvisultra

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.os.PowerManager

/**
 * PRESENÇA 24H (v4.9.0): o JARVIS escuta "Jarvis" com o celular na mesa,
 * no bolso, tela apagada. Um Foreground Service com o microfone aberto
 * e o Vosk rodando 100% offline.
 *
 * Quando o senhor chama:
 *  1. o serviço pausa a própria escuta (libera o microfone pro app)
 *  2. abre o MainActivity já em modo "armado, fale o comando"
 *  3. o app cuida do resto (saudação, cérebro, fala)
 * Ao voltar pro fundo, o app devolve o microfone pro serviço (ACTION_RESUME).
 */
class JarvisWakeService : Service() {

    companion object {
        const val CHANNEL = "jarvis_presenca"
        const val NOTIF_ID = 4242
        const val ACTION_START = "com.andre.jarvisultra.wake.START"
        const val ACTION_STOP = "com.andre.jarvisultra.wake.STOP"
        const val ACTION_PAUSE = "com.andre.jarvisultra.wake.PAUSE"
        const val ACTION_RESUME = "com.andre.jarvisultra.wake.RESUME"

        fun ligar(ctx: Context) {
            ctx.startForegroundService(
                Intent(ctx, JarvisWakeService::class.java).setAction(ACTION_START))
        }

        fun desligar(ctx: Context) {
            ctx.stopService(Intent(ctx, JarvisWakeService::class.java))
        }
    }

    private var session: JarvisVosk.Session? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private val mainHandler by lazy { android.os.Handler(mainLooper) }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                SettingsStore.setWake24h(this, false)
                parar()
                return START_NOT_STICKY
            }
            ACTION_PAUSE -> { pausar(); return START_STICKY }
            ACTION_RESUME -> { retomar(); return START_STICKY }
        }

        startForeground(NOTIF_ID, notificacao())
        if (wakeLock?.isHeld != true) {
            wakeLock = (getSystemService(POWER_SERVICE) as PowerManager)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "jarvis:wake24h").also {
                    it.setReferenceCounted(false); it.acquire(10 * 60 * 60 * 1000L)
                }
        }
        retomar()
        return START_STICKY   // se o sistema matar, ele volta
    }

    private fun retomar() {
        if (session != null) return
        if (!JarvisVosk.hasModel(this)) return   // o app instala o modelo antes de ligar
        try {
            session = JarvisVosk.Session(this,
                onCommand = { },
                onWake = {
                    // chamou! libera o microfone e abre o app já armado
                    mainHandler.post {
                        pausar()
                        val i = Intent(this, MainActivity::class.java)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                            .putExtra("wake", true)
                        startActivity(i)
                    }
                },
                onState = { })
            session?.start()
        } catch (e: Exception) {
            // microfone ocupado pelo app em primeiro plano — o RESUME resolve depois
        }
    }

    private fun pausar() {
        try { session?.stop() } catch (_: Exception) {}
        session = null
    }

    private fun parar() {
        pausar()
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun notificacao(): Notification {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL, "Presença 24h do JARVIS",
                NotificationManager.IMPORTANCE_LOW).apply {
                description = "Ele fica de prontidão ouvindo o senhor chamar \"Jarvis\"."
                setShowBadge(false)
            })
        val abrir = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val parar = PendingIntent.getService(
            this, 1,
            Intent(this, JarvisWakeService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, CHANNEL)
            .setContentTitle("JARVIS de prontidão")
            .setContentText("Diga \"Jarvis\" pra chamar — escuta local, offline.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .setContentIntent(abrir)
            .addAction(android.R.drawable.ic_delete, "Parar escuta", parar)
            .build()
    }
}
