package com.andre.jarvisultra

import android.content.Context
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import org.vosk.Model
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import java.io.File
import java.util.concurrent.TimeUnit
import java.util.zip.ZipFile

/**
 * Voz hands-free + offline: rede neural Vosk de reconhecimento de fala rodando
 * DENTRO do aparelho. O senhor fala "Jarvis" e depois o comando — sem apertar
 * botão e sem precisar de internet pra escutar.
 *
 * Desde a v3.1.2 o pacote de voz (32MB) vem EMBUTIDO no APK (assets/vosk-model.zip):
 * a instalação é local e instantânea. O download pela rede é só plano B.
 *
 * NOTA: este modelo (vosk-model-small-pt-0.3) é ACHATADO — os arquivos ficam na
 * raiz (final.mdl, HCLr.fst…), sem as pastas clássicas am/conf/graph. O marcador
 * de "instalado" é o final.mdl, não a pasta conf/.
 */
object JarvisVosk {
    private val MODEL_URLS = listOf(
        "https://github.com/andre2050/Jarvis-Pro-Ultra/releases/download/v3.0.0/vosk-model-small-pt-0.3.zip",
        "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
    )
    private const val ZIP_PREFIX = "vosk-model-small-pt-0.3/"
    /** Arquivo central do modelo — se existe, a instalação está completa. */
    private const val SENTINEL = "final.mdl"

    /** Mesma blindagem do chat: DNS de reserva + timeout generoso. */
    private val http = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .dns(FallbackDns)
        .build()

    fun modelDir(ctx: Context): File = File(ctx.filesDir, "vosk-model")

    fun hasModel(ctx: Context): Boolean = File(modelDir(ctx), SENTINEL).exists()

    /**
     * Garante que o pacote de voz está instalado. Bloqueante — chamar fora da
     * thread principal. Retorna null se pronto, ou mensagem do que deu errado.
     */
    fun ensureModel(ctx: Context, onProgress: (String) -> Unit = {}): String? {
        if (hasModel(ctx)) return null
        val zip = File(ctx.cacheDir, "vosk-model.zip")

        // 1) Instala direto do APK — sem rede, instantâneo.
        onProgress("instalando pacote de voz...")
        try {
            ctx.assets.open("vosk-model.zip").use { input ->
                zip.outputStream().use { input.copyTo(it) }
            }
            modelDir(ctx).deleteRecursively()
            if (extrairZip(ctx, zip)) {
                zip.delete()
                return null
            }
        } catch (e: Exception) {
            // assets indisponível — segue pro plano B
        }

        // 2) Plano B: download pela rede (APK antigo ou assets faltando).
        var ultimoErro: String? = null
        for (url in MODEL_URLS) {
            try {
                onProgress("baixando pacote de voz...")
                var contentOk = false
                http.newCall(Request.Builder().url(url).build()).execute().use { r ->
                    if (!r.isSuccessful) { ultimoErro = "servidor respondeu " + r.code; return@use }
                    val total = r.body!!.contentLength()
                    var done = 0L
                    zip.outputStream().use { out ->
                        val input = r.body!!.byteStream()
                        val buf = ByteArray(16384)
                        var read = input.read(buf)
                        var lastPct = -1
                        while (read >= 0) {
                            out.write(buf, 0, read)
                            done += read
                            if (total > 0) {
                                val pct = (done * 100 / total).toInt()
                                if (pct / 5 != lastPct) { lastPct = pct / 5; onProgress("baixando voz... " + pct + "%") }
                            }
                            read = input.read(buf)
                        }
                    }
                    contentOk = (total <= 0) || (done >= total)
                    if (!contentOk) ultimoErro = "conexão caiu no meio do download (recebido " + (done / 1024 / 1024) + "MB de " + (total / 1024 / 1024) + "MB)"
                }
                if (!contentOk || !zip.exists() || zip.length() < 1000000) {
                    zip.delete()
                    if (ultimoErro == null) ultimoErro = "download incompleto"
                    continue
                }
                modelDir(ctx).deleteRecursively()
                if (extrairZip(ctx, zip)) {
                    zip.delete()
                    return null
                }
                ultimoErro = "instalação não ficou completa"
            } catch (e: Exception) {
                ultimoErro = (e.message ?: "erro de rede")
            }
        }
        zip.delete()
        return "não consegui instalar o pacote de voz (" + (ultimoErro ?: "falha") + ")."
    }

    private fun extrairZip(ctx: Context, zip: File): Boolean {
        return try {
            ZipFile(zip).use { zf ->
                val entries = zf.entries()
                while (entries.hasMoreElements()) {
                    val e = entries.nextElement()
                    val rel = e.name.removePrefix(ZIP_PREFIX)
                    if (rel.isBlank()) continue
                    val f = File(modelDir(ctx), rel)
                    if (!f.canonicalPath.startsWith(modelDir(ctx).canonicalPath)) continue
                    if (e.isDirectory) { f.mkdirs(); continue }
                    f.parentFile?.mkdirs()
                    zf.getInputStream(e).use { input -> f.outputStream().use { input.copyTo(it) } }
                }
            }
            hasModel(ctx)
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Sessão de escuta contínua: espera o senhor dizer "jarvis" e captura a
     * frase seguinte como comando pro cérebro. Funciona 100% offline.
     */
    class Session(
        ctx: Context,
        private val onCommand: (String) -> Unit,
        private val onWake: () -> Unit,
        private val onState: (String) -> Unit
    ) : RecognitionListener {
        private val appCtx = ctx.applicationContext
        private var service: SpeechService? = null
        private var armed = false
        private var lastCmd = 0L

        fun start() {
            val model = Model(modelDir(appCtx).absolutePath)
            val recognizer = org.vosk.Recognizer(model, 16000.0f)
            service = SpeechService(recognizer, 16000.0f)
            service?.startListening(this)
            onState("on")
        }

        fun stop() {
            try { service?.stop() } catch (_: Exception) {}
            service = null
            onState("off")
        }

        /** v4.9.7: cancela um armamento (wake alucinado na carência inicial). */
        fun desarmar() { armed = false }

        override fun onPartialResult(partial: String) {
            val t = JSONObject(partial).optString("partial", "").lowercase()
            if (!armed && t.contains("jarvis")) {
                armed = true
                onWake()
            }
        }

        override fun onResult(result: String) {
            val t = JSONObject(result).optString("text", "").trim().lowercase()
            if (t.isBlank()) return
            if (armed) {
                if (System.currentTimeMillis() - lastCmd > 2000) {
                    lastCmd = System.currentTimeMillis()
                    armed = false
                    val cmd = t.replace(Regex("^[^a-z0-9]+"), "")
                    if (cmd.isNotBlank()) onCommand(cmd)
                }
            } else if (t.contains("jarvis")) {
                armed = true
                onWake()
                val resto = t.substringAfter("jarvis", "").replace(Regex("^[^a-z0-9]+"), "")
                if (resto.isNotBlank()) {
                    armed = false
                    lastCmd = System.currentTimeMillis()
                    onCommand(resto)
                }
            }
        }

        override fun onFinalResult(result: String) {}

        override fun onError(e: Exception) { onState("erro") }

        override fun onTimeout() {}
    }
}
