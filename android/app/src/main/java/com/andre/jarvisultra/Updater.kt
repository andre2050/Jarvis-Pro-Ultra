package com.andre.jarvisultra

import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * Atualizador COMPLETO do JARVIS Android (v4.7.1): consulta a última release no
 * GitHub, BAIXA o APK sozinho (com progresso) e abre o instalador do sistema —
 * você só confirma na tela. Na v4.6/4.7.0 ele só avisava que havia versão nova
 * e mandava você baixar na mão pela página de releases.
 *
 * A partir desta versão todos os APKs saem assinados com a MESMA chave
 * (keys/jarvis-update.jks), então toda atualização instala por cima sem o erro
 * "app não foi instalado" de assinatura diferente.
 */
object Updater {
    const val RELEASES_URL = "https://github.com/andre2050/Jarvis-Pro-Ultra/releases"
    private const val LATEST_API = "https://api.github.com/repos/andre2050/Jarvis-Pro-Ultra/releases/latest"

    /** Consulta rápida (mantida pra compatibilidade com o botão do HUD). */
    suspend fun check(): String = checar().msg

    /** Resultado da verificação: mensagem pro usuário + APK quando há novidade. */
    data class Resultado(
        val msg: String,
        val apkUrl: String? = null,
        val apkName: String? = null
    )

    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .callTimeout(25, TimeUnit.SECONDS)   // nunca trava: no máximo 25s e devolve erro
        .dns(FallbackDns)                    // mesmo DNS resiliente do GeminiClient
        .build()

    /** Cliente de download: sem callTimeout (APK é grande), leitura paciente. */
    private val httpDownload = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .dns(FallbackDns)
        .build()

    /** Verifica a última release e devolve o que mostrar pro usuário. */
    suspend fun checar(): Resultado = withContext(Dispatchers.IO) {
        try {
            val req = Request.Builder().url(LATEST_API)
                .header("User-Agent", "JarvisProUltra-Android/${JarvisBrain.APP_VERSION}")
                .build()
            http.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) return@withContext Resultado(
                    "Não consegui consultar o servidor de atualização (HTTP ${resp.code}), senhor.")
                val rel = JSONObject(resp.body?.string() ?: "{}")
                val tag = rel.optString("tag_name", "")
                // v4.7.1-android → 4.7.1
                val versao = tag.removePrefix("v").substringBefore("-")
                if (versao.isEmpty()) return@withContext Resultado(
                    "Servidor de atualização respondeu sem versão.")

                var apkUrl: String? = null
                var apkName: String? = null
                val assets: JSONArray = rel.optJSONArray("assets") ?: JSONArray()
                for (i in 0 until assets.length()) {
                    val a = assets.getJSONObject(i)
                    if (a.optString("name").endsWith(".apk")) {
                        apkUrl = a.optString("browser_download_url")
                        apkName = a.optString("name")
                        break
                    }
                }

                val local = JarvisBrain.APP_VERSION
                when {
                    isNewer(versao, local) -> {
                        if (apkUrl == null) Resultado(
                            "Nova versão $versao disponível, mas sem APK anexado à release — " +
                            "baixe pela página de releases, senhor.")
                        else Resultado(
                            "Nova versão disponível: $versao (instalada: $local), senhor.",
                            apkUrl, apkName)
                    }
                    else -> Resultado("Você está na versão mais recente, senhor. ($local)")
                }
            }
        } catch (e: Exception) {
            Resultado("Falha na verificação: ${e.message ?: "sem detalhes"}")
        }
    }

    /**
     * Baixa o APK da atualização pra cache/updates/ com progresso em texto.
     * Devolve o arquivo pronto pra instalar. Limpo e simples: sem download
     * em segundo plano invisível — quem chama é que decide o que mostrar.
     */
    suspend fun baixar(ctx: Context, apkUrl: String, onProgress: (String) -> Unit): File =
        withContext(Dispatchers.IO) {
            val dir = File(ctx.cacheDir, "updates").apply { mkdirs() }
            val alvo = File(dir, "jarvis-update.apk")
            if (alvo.exists()) alvo.delete()

            val req = Request.Builder().url(apkUrl)
                .header("User-Agent", "JarvisProUltra-Android/${JarvisBrain.APP_VERSION}")
                .build()
            httpDownload.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) throw IllegalStateException("download falhou (HTTP ${resp.code})")
                val body = resp.body ?: throw IllegalStateException("resposta vazia do servidor")
                val total = body.contentLength()
                var lido = 0L
                var ultimoPct = -1
                body.byteStream().use { entrada ->
                    alvo.outputStream().use { saida ->
                        val buf = ByteArray(32 * 1024)
                        while (true) {
                            val n = entrada.read(buf)
                            if (n == -1) break
                            saida.write(buf, 0, n)
                            lido += n
                            if (total > 0) {
                                val pct = (lido * 100 / total).toInt()
                                if (pct / 5 != ultimoPct / 5) {
                                    ultimoPct = pct
                                    onProgress("Baixando atualização… $pct% (${lido / 1048576} MB)")
                                }
                            }
                        }
                    }
                }
            }
            alvo
        }

    /** Abre o instalador nativo do Android pro APK baixado. */
    fun instalar(ctx: Context, apk: File) {
        val uri = FileProvider.getUriForFile(
            ctx, "com.andre.jarvisultra.fileprovider", apk)
        val i = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        ctx.startActivity(i)
    }

    /** comparação de versões simples: 1.2.0 > 1.1.9 */
    private fun isNewer(remote: String, local: String): Boolean {
        val r = remote.split('.').map { it.toIntOrNull() ?: 0 }
        val l = local.split('.').map { it.toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(r.size, l.size)) {
            val rv = r.getOrElse(i) { 0 }
            val lv = l.getOrElse(i) { 0 }
            if (rv != lv) return rv > lv
        }
        return false
    }
}
