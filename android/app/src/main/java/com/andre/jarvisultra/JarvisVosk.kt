package com.andre.jarvisultra

import android.content.Context
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import org.vosk.Model
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import java.io.File
import java.io.FileInputStream
import java.util.zip.ZipInputStream

/**
 * Voz hands-free + offline (v3.0.0): rede neural Vosk de reconhecimento de fala
 * rodando DENTRO do aparelho. O senhor fala "Jarvis" e depois o comando — sem
 * apertar botão e sem precisar de internet pra escutar. O pacote de voz (31MB)
 * baixa uma vez só, direto do release do projeto no GitHub.
 */
object JarvisVosk {
    const val MODEL_URL = "https://github.com/andre2050/Jarvis-Pro-Ultra/releases/download/v3.0.0/vosk-model-small-pt-0.3.zip"
    private const val ZIP_PREFIX = "vosk-model-small-pt-0.3/"
    private val http = OkHttpClient()

    fun modelDir(ctx: Context): File = File(ctx.filesDir, "vosk-model")

    fun hasModel(ctx: Context): Boolean = File(modelDir(ctx), "conf").exists()

    /** Baixa e instala o pacote de voz. Bloqueante — chamar fora da thread principal. */
    fun ensureModel(ctx: Context): Boolean {
        if (hasModel(ctx)) return true
        return try {
            val zip = File(ctx.cacheDir, "vosk-model.zip")
            http.newCall(Request.Builder().url(MODEL_URL).build()).execute().use { r ->
                if (!r.isSuccessful) return false
                zip.outputStream().use { r.body!!.byteStream().copyTo(it) }
            }
            val dir = modelDir(ctx)
            dir.deleteRecursively()
            ZipInputStream(FileInputStream(zip)).use { zis ->
                var e = zis.nextEntry
                while (e != null) {
                    val rel = e.name.removePrefix(ZIP_PREFIX)
                    if (rel.isNotBlank()) {
                        val f = File(dir, rel)
                        if (f.canonicalPath.startsWith(dir.canonicalPath)) {
                            if (e.isDirectory) f.mkdirs() else {
                                f.parentFile?.mkdirs()
                                f.outputStream().use { zis.copyTo(it) }
                            }
                        }
                    }
                    zis.closeEntry()
                    e = zis.nextEntry
                }
            }
            zip.delete()
            hasModel(ctx)
        } catch (e: Exception) { false }
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
