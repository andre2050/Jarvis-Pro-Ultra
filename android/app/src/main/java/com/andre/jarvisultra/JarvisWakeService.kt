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
 * PRESENÇA 24H (v4.9.0, consertada v4.9.5, blindada v4.9.6): o JARVIS escuta
 * "Jarvis" com o celular na mesa, no bolso, tela apagada. Foreground Service
 * com o microfone aberto e o Vosk rodando 100% offline.
 *
 * v4.9.6 — blindagem total contra o "abre e fecha":
 *  - REGRA ÚNICA de dono do microfone: app aberto → escuta do app (serviço
 *    pausa); app no fundo → escuta do serviço. Qualquer intent (START,
 *    PAUSE, RESUME, recriação do sistema) cai na MESMA lógica — sem estado
 *    inconsistente, sem zumbi, sem presença morta.
 *  - SEMPRE startForeground() no início de qualquer onStartCommand: quem
 *    chega via startForegroundService (obrigatório a partir do onStop do
 *    app) NUNCA derruba o app por não chamar startForeground em 5s
 *    (ForegroundServiceDidNotStartInTimeException — crash real).
 *  - carência 2,5s + debounce 10s contra alucinação do Vosk (v4.9.5).
 *  - modelo carrega em thread própria, nunca na main (v4.9.5).
 *  - qualquer crash do processo é gravado pela caixa-preta (JarvisUltraApp).
 */
class JarvisWakeService : Service() {

    companion object {
        const val CHANNEL = "jarvis_presenca"
        const val NOTIF_ID = 4242
        const val ACTION_START = "com.andre.jarvisultra.wake.START"
        const val ACTION_STOP = "com.andre.jarvisultra.wake.STOP"
        const val ACTION_PAUSE = "com.andre.jarvisultra.wake.PAUSE"
        const val ACTION_RESUME = "com.andre.jarvisultra.wake.RESUME"

        /** ignora "jarvis" ouvido nos primeiros ms de escuta (alucinação do Vosk) */
        private const val CARENCIA_MS = 2500L
        /** tempo mínimo entre dois disparos de wake */
        private const val DEBOUNCE_MS = 10000L

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
    private var inicioEscuta = 0L
    private var ultimoWake = 0L
    private val mainHandler by lazy { android.os.Handler(mainLooper) }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            SettingsStore.setWake24h(this, false)
            parar()
            return START_NOT_STICKY
        }

        // START, PAUSE, RESUME ou recriação do sistema: primeiro deixa o
        // estado de foreground garantido (exigência do startForegroundService)
        startForeground(NOTIF_ID, notificacao())
        if (wakeLock?.isHeld != true) {
            wakeLock = (getSystemService(POWER_SERVICE) as PowerManager)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "jarvis:wake24h").also {
                    it.setReferenceCounted(false); it.acquire(10 * 60 * 60 * 1000L)
                }
        }

        // REGRA ÚNICA: microfone do app se o app está aberto, meu se não está
        if (WakeCoord.appEmPrimeiroPlano) pausar() else retomar()
        return START_STICKY   // se o sistema matar, ele volta
    }

    private fun retomar() {
        if (session != null) return
        if (!JarvisVosk.hasModel(this)) return   // o app instala o modelo antes de ligar
        // o modelo é pesado: carregar fora da main thread (evita travar o app)
        Thread {
            if (session != null) return@Thread
            try {
                val nova = JarvisVosk.Session(this,
                    onCommand = { },
                    onWake = { acordou() },
                    onState = { })
                synchronized(this) {
                    if (session != null) return@Thread  // outro RESUME ganhou a corrida
                    nova.start()
                    session = nova
                    inicioEscuta = System.currentTimeMillis()
                }
            } catch (e: Exception) {
                // microfone ocupado pelo app em primeiro plano — o RESUME resolve depois
            }
        }.start()
    }

    /** O senhor chamou "Jarvis" — mas só se for de verdade. */
    private fun acordou() {
        val agora = System.currentTimeMillis()
        // carência: nos primeiros instantes o Vosk alucina "jarvis" no ruído
        if (agora - inicioEscuta < CARENCIA_MS) return
        // debounce: dois disparos seguidos (parcial + final) só abrem o app uma vez
        if (agora - ultimoWake < DEBOUNCE_MS) return
        ultimoWake = agora

        mainHandler.post {
            pausar()   // libera o microfone pro app
            // app já aberto? ele está com as mãos livres — só avisa que chegou ordem por voz
            WakeCoord.wakePendente = true
            if (!WakeCoord.appEmPrimeiroPlano) {
                try {
                    startActivity(Intent(this, MainActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                        .putExtra(WakeCoord.EXTRA_WAKE, true))
                } catch (_: Exception) { }
            }
        }
    }

    override fun onDestroy() {
        // presença encerrada (app fechou de vez / desligaram): devolve o microfone
        pausar()
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        super.onDestroy()
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
