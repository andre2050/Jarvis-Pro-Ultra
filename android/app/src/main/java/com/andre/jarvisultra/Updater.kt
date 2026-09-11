package com.andre.jarvisultra

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Verificador de atualização do JARVIS Android.
 * Lê o MESMO manifesto assinado do projeto (update.json das Releases do GitHub)
 * e avisa quando há versão nova. No Android, a instalação do APK é manual
 * (padrão do sistema), então o app abre a página de releases pra você baixar.
 */
object Updater {
    const val MANIFEST_URL = "https://github.com/andre2050/Jarvis-Pro-Ultra/releases/latest/download/update.json"
    const val RELEASES_URL = "https://github.com/andre2050/Jarvis-Pro-Ultra/releases"

    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun check(): String = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(MANIFEST_URL).header("User-Agent", "JarvisProUltra-Android/${JarvisBrain.APP_VERSION}").build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return@withContext "Não consegui consultar o servidor de atualização (HTTP ${resp.code})."
            val man = JSONObject(resp.body?.string() ?: "{}")
            val latest = man.optString("latest_version", "")
            if (latest.isEmpty()) return@withContext "Servidor de atualização respondeu sem versão."

            val local = JarvisBrain.APP_VERSION
            when {
                isNewer(latest, local) -> "Nova versão disponível: $latest (instalada: $local).\n" +
                    "Baixe o APK da release no GitHub e instale por cima."
                else -> "Você está na versão mais recente, senhor. ($local)"
            }
        }
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
