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
 * PRESENÇA 24H (v4.9.0, consertada na v4.9.5): o JARVIS escuta "Jarvis" com
 * o celular na mesa, no bolso, tela apagada. Foreground Service com o
 * microfone aberto e o Vosk rodando 100% offline.
 *
 * v4.9.5 — o que estava quebrando e como ficou:
 *  1. FALSO-POSITIVO no ato de ligar (Vosk alucina "jarvis" nos primeiros
 *     áudios e o app abria sozinho em seguida): agora há CARÊNCIA de 2,5s
 *     após ligar a escuta + DEBOUNCE de 10s entre chamadas.
 *  2. O serviço PAUSAVA na primeira chamada e NINGUÉM retomava (presença
 *     morria logo em seguida): agora o MainActivity devolve o microfone com
 *     ACTION_RESUME sempre que o app vai pro fundo (e devolve também se o
 *     app fechar).
 *  3. O modelo carregava na MAIN THREAD (travasso/ANR): agora a escuta
 *     sobe numa thread própria.
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
    private var iniciado = false
    private var inicioEscuta = 0L
    private var ultimoWake = 0L
    private val mainHandler by lazy { android.os.Handler(mainLooper) }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                SettingsStore.setWake24h(this, false)
                parar()
                return START_NOT_STICKY
            }
            ACTION_PAUSE -> {
                if (iniciado) pausar()
                else stopSelf()          // chegou PAUSE sem estar ligado: não vira zumbi
                return START_STICKY
            }
            ACTION_RESUME -> {
                if (iniciado) retomar()
                else stopSelf()
                return START_STICKY
            }
        }

        // ACTION_START (ou recriação pelo sistema): sobe de fato
        startForeground(NOTIF_ID, notificacao())
        iniciado = true
        if (wakeLock?.isHeld != true) {
            wakeLock = (getSystemService(POWER_SERVICE) as PowerManager)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "jarvis:wake24h").also {
                    it.setReferenceCounted(false); it.acquire(10 * 60 * 60 * 1000L)
                }
        }
        // com o app aberto o microfone é do app; escutar só quando ele sair de cena
        if (!WakeCoord.appEmPrimeiroPlano) retomar()
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
        iniciado = false
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
