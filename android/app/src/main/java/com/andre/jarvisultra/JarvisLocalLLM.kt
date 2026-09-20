package com.andre.jarvisultra

import android.content.Context
import android.os.StatFs
import com.google.mediapipe.tasks.genai.llminference.LlmInference
import okhttp3.OkHttpClient
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * v4.10.0 — CÉREBRO LOCAL: o J.A.R.V.I.S pensa 100% DENTRO do celular.
 *
 * Motor: MediaPipe LLM Inference API do Google (tasks-genai), rodando o modelo
 * Gemma 3 1B IT quantizado em 4 bits (529MB). Sem internet, sem chave de API,
 * sem dado saindo do aparelho — conversa privada por definição.
 *
 * O modelo é baixado UMA vez (do HuggingFace, link público, no ⚙ CONFIG).
 * Depois disso o cérebro funciona em avião.
 */
object JarvisLocalLLM {

    private const val MODEL_URL =
        "https://huggingface.co/litert-community/Gemma3-1B-IT/resolve/main/gemma3-1b-it-int4.task"
    private const val MODEL_MIN_BYTES = 100_000_000L // 100MB — menor que isso = download quebrado

    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()

    @Volatile
    private var llm: LlmInference? = null
    private var llmPath: String? = null // caminho do modelo carregado

    fun modelFile(ctx: Context): File =
        File(File(ctx.filesDir, "models"), "gemma3-1b-int4.task")

    fun hasModel(ctx: Context): Boolean {
        val f = modelFile(ctx)
        return f.exists() && f.length() >= MODEL_MIN_BYTES
    }

    /** Espaço livre no armazenamento interno, em MB. */
    fun espacoLivreMb(ctx: Context): Long {
        val stat = StatFs(ctx.filesDir.absolutePath)
        return stat.availableBytes / (1024 * 1024)
    }

    fun removerModelo(ctx: Context) {
        liberarMemoria()
        modelFile(ctx).delete()
    }

    /** Libera a RAM ocupada pelo modelo (~700MB). Chamado ao sair do modo local. */
    fun liberarMemoria() {
        try { llm?.close() } catch (_: Exception) { }
        llm = null
        llmPath = null
    }

    /**
     * Carrega o modelo (uma vez só; fica em RAM enquanto o app vive).
     * Retorna null se não conseguiu — o cérebro cai pro plano B (nuvem).
     */
    @Synchronized
    fun obter(ctx: Context): LlmInference? {
        val path = modelFile(ctx).absolutePath
        if (llm != null && llmPath == path) return llm
        if (!hasModel(ctx)) return null
        try {
            llm = LlmInference.createFromOptions(
                ctx,
                LlmInference.LlmInferenceOptions.builder()
                    .setModelPath(path)
                    .setMaxTokens(3072)
                    .build()
            )
            llmPath = path
        } catch (e: Exception) {
            // RAM insuficiente, aparelho sem suporte etc — nunca derruba o app
            llm = null
            llmPath = null
        }
        return llm
    }

    /**
     * Baixa o modelo com progresso. Rodar em THREAD PRÓPRIA.
     * onProgress: 0..100. Retorna null se ok, senão o motivo do erro.
     */
    fun downloadModel(ctx: Context, onProgress: (Int) -> Unit): String? {
        if (hasModel(ctx)) return null
        val dest = modelFile(ctx)
        dest.parentFile?.mkdirs()

        val livreMb = espacoLivreMb(ctx)
        if (livreMb < 900) {
            return "Pouco espaço no aparelho, senhor: faltam ${900 - livreMb}MB. Libere espaço e tente de novo."
        }

        val part = File(dest.absolutePath + ".part")
        try {
            http.newCall(okhttp3.Request.Builder().url(MODEL_URL).build()).execute().use { r ->
                if (!r.isSuccessful) return "Servidor respondeu ${r.code}"
                val total = r.body!!.contentLength()
                var done = 0L
                var lastPct = -1
                part.outputStream().use { out ->
                    val input = r.body!!.byteStream()
                    val buf = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        done += n
                        if (total > 0) {
                            val pct = (done * 100 / total).toInt()
                            if (pct != lastPct) { lastPct = pct; onProgress(pct) }
                        }
                    }
                }
                if (done < MODEL_MIN_BYTES) {
                    part.delete()
                    return "Download incompleto ($done bytes) — verifique sua internet e tente de novo."
                }
            }
            if (part.length() < MODEL_MIN_BYTES) { part.delete(); return "Arquivo baixado veio quebrado." }
            part.renameTo(dest)
            return null
        } catch (e: Exception) {
            part.delete()
            return "Falha no download: ${e.message ?: "sem detalhes"}"
        }
    }
}
