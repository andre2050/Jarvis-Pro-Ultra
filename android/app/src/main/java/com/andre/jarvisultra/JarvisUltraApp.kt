package com.andre.jarvisultra

import android.app.Application
import android.content.Context
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * v4.9.6 — CAIXA-PRETA: o app estava "abrindo e fechando" no aparelho do
 * senhor sem deixar pistas. Agora, qualquer crash (na activity OU no serviço
 * de presença, que roda no mesmo processo) é gravado em crash.log ANTES de
 * o processo morrer. Na próxima abertura o app mostra o motivo exato —
 * chega de adivinhar.
 */
class JarvisUltraApp : Application() {

    companion object {
        fun crashFile(ctx: Context): File = File(ctx.filesDir, "crash.log")

        /** Último crash gravado (ou null). Limitado a 4000 caracteres. */
        fun lerUltimoCrash(ctx: Context): String? = try {
            val f = crashFile(ctx)
            if (!f.exists()) null else f.readText().take(4000)
        } catch (_: Exception) { null }

        fun apagarCrash(ctx: Context) { try { crashFile(ctx).delete() } catch (_: Exception) {} }
    }

    override fun onCreate() {
        super.onCreate()
        val anterior = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try {
                crashFile(this).writeText(
                    SimpleDateFormat("dd/MM/yyyy HH:mm:ss", Locale("pt", "BR")).format(Date()) +
                    " — JARVIS v" + JarvisBrain.APP_VERSION + " (thread: " + t.name + ")\n\n" +
                    "MOTIVO DO FECHAMENTO:\n" +
                    e.javaClass.name + ": " + (e.message ?: "(sem mensagem)") + "\n\n" +
                    e.stackTrace.take(30).joinToString("\n") { "  em " + it.toString() } + "\n")
            } catch (_: Exception) { }
            // segue o curso normal: o app fecha, mas deixa o relatório pra trás
            anterior?.uncaughtException(t, e)
        }
    }
}
