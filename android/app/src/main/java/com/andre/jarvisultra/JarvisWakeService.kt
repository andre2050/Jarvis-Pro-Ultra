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
 * PRESENÇA 24H — v4.9.7: ARQUITETURA DE DONO ÚNICO.
 *
 * Histórico: o app "abria e fechava" quando a presença chamava, mesmo
 * depois de duas rodadas de correção — porque a disputa de microfone
 * (serviço pausando, app armando outra sessão Vosk em cima) derruba o
 * processo em código NATIVO: sem exceção Java, sem caixa-preta, sem pistas.
 *
 * Agora, com a presença LIGADA, ESTE serviço é o único dono do microfone,
 * com o app aberto ou fechado — o app nunca abre uma escuta Vosk própria
 * enquanto a presença estiver ativa. O comando dito pelo senhor chega ao
 * app via WakeCoord. Sem PAUSE/RESUME, sem corrida, sem double Model.
 */
class JarvisWakeService : Service() {

    companion object {
        const val CHANNEL = "jarvis_presenca"
        const val NOTIF_ID = 4242
        const val ACTION_START = "com.andre.jarvisultra.wake.START"
        const val ACTION_STOP = "com.andre.jarvisultra.wake.STOP"

        /** ignora "jarvis" ouvido nos primeiros ms de escuta (alucinação do Vosk) */
        private const val CARENCIA_MS = 2500L
        /** tempo mínimo entre dois disparos de wake */
        private const val DEBOUNCE_MS = 10000L

        /** v4.9.9: retorna true se conseguiu pedir a partida (não garante que
         * o startForeground() interno vá ter sucesso — isso é validado dentro
         * do onStartCommand, que tem sua própria blindagem). */
        fun ligar(ctx: Context): Boolean {
            return try {
                ctx.startForegroundService(
                    Intent(ctx, JarvisWakeService::class.java).setAction(ACTION_START))
                true
            } catch (e: Exception) {
                // Android 14: SecurityException/IllegalStateException podem nascer
                // aqui mesmo se o app não estiver em estado elegível pra FGS de mic
                SettingsStore.setAvisoPresenca(ctx,
                    "Não consegui ligar a presença agora, senhor — o Android exige o app " +
                    "aberto e na tela pra isso. Deixe o JARVIS aberto por alguns segundos e " +
                    "tente de novo em ⚙ CONFIG.")
                false
            }
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

        // v4.9.9: aqui é onde o crash de verdade nascia — Android 14 valida
        // NA HORA se o app está em estado elegível pra abrir um serviço de
        // microfone em primeiro plano (app visível há pouco tempo). Sem o
        // app na tela (ex.: boot, ou o app saiu de vista enquanto baixava o
        // modelo), o sistema lança SecurityException AQUI DENTRO — e sem
        // captura isso derruba o processo sem deixar rastro de exceção Java
        // "normal" (mata a UncaughtExceptionHandler antes de qualquer log).
        try {
            startForeground(NOTIF_ID, notificacao())
        } catch (e: Exception) {
            SettingsStore.setAvisoPresenca(this,
                "A presença não ligou, senhor — o Android bloqueou por eu não estar " +
                "com o app visível na hora. Abra o JARVIS, deixe a tela acesa por uns " +
                "segundos e ative de novo em ⚙ CONFIG.")
            SettingsStore.setWake24h(this, false)
            stopSelf()
            return START_NOT_STICKY
        }
        if (wakeLock?.isHeld != true) {
            wakeLock = (getSystemService(POWER_SERVICE) as PowerManager)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "jarvis:wake24h").also {
                    it.setReferenceCounted(false); it.acquire(10 * 60 * 60 * 1000L)
                }
        }
        retomar()
        return START_STICKY   // se o sistema matar, ele volta
    }

    /** Escuta única: só o serviço toca no microfone enquanto a presença viver. */
    private fun retomar() {
        if (session != null) return
        if (!JarvisVosk.hasModel(this)) return   // o app instala o modelo antes de ligar
        Thread {
            if (session != null) return@Thread
            try {
                val nova = JarvisVosk.Session(this,
                    onCommand = { cmd -> WakeCoord.comandoPendente = cmd },
                    onWake = { acordou() },
                    onState = { })
                synchronized(this) {
                    if (session != null) return@Thread
                    nova.start()
                    session = nova
                    inicioEscuta = System.currentTimeMillis()
                }
            } catch (e: Exception) {
                // microfone indisponível — tenta de novo no próximo reinício do serviço
            }
        }.start()
    }

    /** O senhor chamou "Jarvis" — mas só se for de verdade. */
    private fun acordou() {
        val agora = System.currentTimeMillis()
        val falouDeVerdade = (agora - inicioEscuta >= CARENCIA_MS) &&
                            (agora - ultimoWake >= DEBOUNCE_MS)
        if (!falouDeVerdade) {
            session?.desarmar()   // alucinação na carência: não captura nada
            return
        }
        ultimoWake = agora

        mainHandler.post {
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
