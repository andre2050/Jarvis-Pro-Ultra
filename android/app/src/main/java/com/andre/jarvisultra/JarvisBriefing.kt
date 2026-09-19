package com.andre.jarvisultra

import android.app.AlarmManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.BatteryManager
import android.os.IBinder
import android.os.PowerManager
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

/**
 * BRIEFING MATINAL (v4.9.0): todo dia na hora marcada o JARVIS fala sozinho —
 * bom dia, hora, clima da região, bateria e o que ele lembra do senhor.
 * 100% local: AlarmManager + TTS, sem depender de servidor.
 *
 * AlarmScheduler.agendar() usa setExactAndAllowWhileIdle quando o Android
 * libera (tela do "Alarms & reminders") e cai pro inexact quando não —
 * o briefing chega alguns minutos depois, mas chega.
 */
object BriefingScheduler {

    fun agendar(ctx: Context) {
        val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val (h, m) = SettingsStore.getBriefingHora(ctx).split(":").map { it.toInt() }
        val cal = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, h); set(Calendar.MINUTE, m)
            set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) add(Calendar.DAY_OF_YEAR, 1)
        }
        val pi = PendingIntent.getBroadcast(
            ctx, 4243,
            Intent(ctx, JarvisBriefingReceiver::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val exato = if (android.os.Build.VERSION.SDK_INT >= 31)
            am.canScheduleExactAlarms() else true
        try {
            if (exato) {
                am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cal.timeInMillis, pi)
            } else {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cal.timeInMillis, pi)
            }
        } catch (e: SecurityException) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cal.timeInMillis, pi)
        }
    }

    fun cancelar(ctx: Context) {
        val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pi = PendingIntent.getBroadcast(
            ctx, 4243,
            Intent(ctx, JarvisBriefingReceiver::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        am.cancel(pi)
    }
}

class JarvisBriefingReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        BriefingScheduler.agendar(ctx)          // já marca o próximo dia
        try {
            ctx.startForegroundService(
                Intent(ctx, JarvisBriefingService::class.java))
        } catch (e: Exception) {
            // fabricantes agressivos bloqueiam FGS do nada — o próximo dia tenta de novo
        }
    }
}

class JarvisBriefingService : Service() {

    private var wakeLock: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(NotificationChannel(
            "jarvis_briefing", "Briefing matinal",
            NotificationManager.IMPORTANCE_DEFAULT).apply {
            description = "O bom dia falado do JARVIS."
        })
        startForeground(4244, Notification.Builder(this, "jarvis_briefing")
            .setContentTitle("Briefing matinal")
            .setContentText("O JARVIS está preparando o seu bom dia, senhor.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .build())

        wakeLock = (getSystemService(POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "jarvis:briefing").also {
                it.setReferenceCounted(false); it.acquire(3 * 60 * 1000L)
            }

        Thread {
            val texto = montarBriefing()
            val voz = JarvisVoice(this)
            voz.speakNow(texto)
            // o TTS fala na própria thread do serviço; esperamos terminar com teto de 2 min
            val t0 = System.currentTimeMillis()
            while (voz.isSpeaking && System.currentTimeMillis() - t0 < 120_000) {
                Thread.sleep(500)
            }
            voz.shutdown()
            stopSelf()
        }.start()
        return START_NOT_STICKY
    }

    private fun montarBriefing(): String {
        val nome = SettingsStore.getUserName(this).ifBlank { "senhor" }
        val agora = Calendar.getInstance()
        val dias = listOf("domingo", "segunda-feira", "terça-feira", "quarta-feira",
            "quinta-feira", "sexta-feira", "sábado")
        val hora = SimpleDateFormat("HH:mm", Locale("pt", "BR")).format(agora.time)
        val dia = dias[agora.get(Calendar.DAY_OF_WEEK) - 1]
        val data = SimpleDateFormat("d 'de' MMMM", Locale("pt", "BR")).format(agora.time)

        val bateria = try {
            val bm = getSystemService(BATTERY_SERVICE) as BatteryManager
            "${bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)}%"
        } catch (e: Exception) { "não sei" }

        val clima = try { JarvisPercepcao.clima(this) } catch (e: Exception) { "" }
        val fraseClima = if (clima.isNotBlank() && !clima.startsWith("sem permissão"))
            " Lá fora: $clima" else ""

        val mems = try { JarvisMemory.recent(this, 3) } catch (e: Exception) { emptyList() }
        val fraseMem = if (mems.isNotEmpty())
            " Aliás, das últimas coisas que o senhor me pediu pra lembrar: ${mems.joinToString("; ") { it.take(90) }}." else ""

        return "Bom dia, $nome. São $hora de $dia, $data.$fraseClima " +
                "Sua bateria está em $bateria.$fraseMem " +
                "Tenha um excelente dia — eu fico de prontidão."
    }
}
