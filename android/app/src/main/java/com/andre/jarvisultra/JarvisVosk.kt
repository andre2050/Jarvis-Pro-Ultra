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
 * Voz hands-free + offline (v3.0.0): rede neural Vosk de reconhecimento de fala
 * rodando DENTRO do aparelho. O senhor fala "Jarvis" e depois o comando — sem
 * apertar botão e sem precisar de internet pra escutar. O pacote de voz (31MB)
 * baixa uma vez só; se uma fonte falhar, tenta a outra.
 */
object JarvisVosk {
    private val MODEL_URLS = listOf(
        "https://github.com/andre2050/Jarvis-Pro-Ultra/releases/download/v3.0.0/vosk-model-small-pt-0.3.zip",
        "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
    )
    private const val ZIP_PREFIX = "vosk-model-small-pt-0.3/"

    /** Mesma blindagem do chat: DNS de reserva + timeout generoso pra 31MB. */
    private val http = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .dns(FallbackDns)
        .build()

    fun modelDir(ctx: Context): File = File(ctx.filesDir, "vosk-model")

    fun hasModel(ctx: Context): Boolean = File(modelDir(ctx), "conf").exists()

    /** v3.1.1: o pacote de voz vem DENTRO do APK — copia dos assets pro armazenamento interno. */
    private fun installFromAssets(ctx: Context): Boolean {
        return try {
            val dir = modelDir(ctx)
            dir.deleteRecursively()
            fun copiar(path: String) {
                val itens = ctx.assets.list(path) ?: return
                if (itens.isEmpty()) {
                    val rel = path.removePrefix("vosk-model/")
                    if (rel.isBlank()) return
                    val f = File(dir, rel)
                    f.parentFile?.mkdirs()
                    ctx.assets.open(path).use { input -> f.outputStream().use { input.copyTo(it) } }
                } else {
                    itens.forEach { copiar(path + "/" + it) }
                }
            }
            val raiz = ctx.assets.list("vosk-model") ?: return false
            if (raiz.isEmpty()) return false
            raiz.forEach { copiar("vosk-model/" + it) }
            hasModel(ctx)
        } catch (e: Exception) { false }
    }

    /**
     * Baixa e instala o pacote de voz. Bloqueante — chamar fora da thread principal.
     * Retorna null se ficou pronto, ou a mensagem de erro do que deu errado.
     */
    fun ensureModel(ctx: Context, onProgress: (String) -> Unit = {}): String? {
        if (hasModel(ctx)) return null
        // v3.1.1: instala direto do APK — instantâneo, sem depender de rede.
        onProgress("instalando pacote de voz...")
        if (installFromAssets(ctx)) return null
        // Plano B (APK antigo / assets indisponíveis): download pela rede.
        val zip = File(ctx.cacheDir, "vosk-model.zip")
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
                    // Só considera OK se recebeu o total esperado (ou se o servidor não informou o tamanho).
                    contentOk = (total <= 0) || (done >= total)
                    if (!contentOk) ultimoErro = "conexão caiu no meio do download (recebido " + (done / 1024 / 1024) + "MB de " + (total / 1024 / 1024) + "MB)"
                }
                if (!contentOk || !zip.exists() || zip.length() < 1000000) {
                    zip.delete()
                    if (ultimoErro == null) ultimoErro = "download incompleto"
                    continue
                }
                onProgress("verificando pacote...")
                // ZipFile valida o índice central do arquivo — detecta corrupção antes de gastar tempo extraindo.
                val validZip = try { ZipFile(zip); true } catch (e: Exception) { ultimoErro = "arquivo baixado está corrompido"; false }
                if (!validZip) { zip.delete(); continue }
                onProgress("instalando pacote de voz...")
                val dir = modelDir(ctx)
                dir.deleteRecursively()
                var extraiu = false
                try {
                    ZipFile(zip).use { zf ->
                        val entries = zf.entries()
                        while (entries.hasMoreElements()) {
                            val e = entries.nextElement()
                            val rel = e.name.removePrefix(ZIP_PREFIX)
                            if (rel.isBlank()) continue
                            val f = File(dir, rel)
                            if (!f.canonicalPath.startsWith(dir.canonicalPath)) continue
                            if (e.isDirectory) { f.mkdirs(); continue }
                            f.parentFile?.mkdirs()
                            zf.getInputStream(e).use { input -> f.outputStream().use { input.copyTo(it) } }
                        }
                    }
                    extraiu = true
                } catch (e: Exception) {
                    ultimoErro = "falha ao extrair: " + (e.message ?: "erro desconhecido")
                }
                zip.delete()
                if (extraiu && hasModel(ctx)) return null
                if (ultimoErro == null) ultimoErro = "pacote instalado mas o modelo não ficou completo"
            } catch (e: Exception) {
                ultimoErro = (e.message ?: "erro de rede")
            }
        }
        return "não consegui baixar o pacote de voz (" + (ultimoErro ?: "rede") + "). Tente no Wi-Fi."
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
