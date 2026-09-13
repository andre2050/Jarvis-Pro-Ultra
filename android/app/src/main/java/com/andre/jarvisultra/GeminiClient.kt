package com.andre.jarvisultra

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Dns
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.UnknownHostException
import java.util.concurrent.TimeUnit
import kotlin.random.Random

/**
 * Cliente do Gemini com function calling real (o mesmo protocolo do JARVIS desktop).
 * Tenta os modelos em ordem — se um foi aposentado (404), cai pro próximo.
 * Se o DNS do sistema falhar ("Unable to resolve host"), consulta os servidores
 * públicos diretamente por UDP (FallbackDns).
 */
object GeminiClient {
    private val MODELS = listOf("gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite")
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .dns(FallbackDns)
        .build()

    /**
     * [functionCallParts] são as partes CRUAS da resposta do modelo que contêm functionCall —
     * preservam o campo thoughtSignature (exigido pelos modelos novos, ex: gemini-3.6-flash,
     * ao devolver a chamada de função no histórico). Sempre reenvie a parte inteira como veio.
     */
    data class GeminiResult(val text: String?, val functionCallParts: List<JSONObject>, val model: String)

    suspend fun turn(apiKey: String, systemPrompt: String, contents: JSONArray, tools: JSONArray?): GeminiResult {
        var lastError: IllegalStateException? = null
        for (m in MODELS) {
            for (attempt in 1..2) {
                try {
                    return callModel(m, apiKey, systemPrompt, contents, tools)
                } catch (e: UnknownHostException) {
                    if (attempt == 2) {
                        throw IllegalStateException("⚠️ Sem conexão com a internet, senhor. Verifique o Wi-Fi/dados móveis e tente de novo.")
                    }
                    kotlinx.coroutines.delay(800)
                } catch (e: IllegalStateException) {
                    val msg = e.message ?: ""
                    if (msg.contains("404") || msg.contains("not found", ignoreCase = true) || msg.contains("not supported", ignoreCase = true)) {
                        lastError = e
                        break
                    }
                    if (msg.contains("503") || msg.contains("429") || msg.contains("high demand", ignoreCase = true) || msg.contains("overloaded", ignoreCase = true)) {
                        lastError = e
                        if (attempt < 2) { kotlinx.coroutines.delay(1000); continue }
                        break
                    }
                    throw e
                }
            }
        }
        val base = lastError?.message ?: ""
        if (base.contains("503") || base.contains("429") || base.contains("high demand", ignoreCase = true) || base.contains("overloaded", ignoreCase = true)) {
            throw IllegalStateException("⚠️ Os servidores do Gemini estão sobrecarregados agora, senhor. Aguarde um minuto e mande de novo.")
        }
        throw lastError ?: IllegalStateException("nenhum modelo disponível")
    }

    private suspend fun callModel(model: String, apiKey: String, systemPrompt: String, contents: JSONArray, tools: JSONArray?): GeminiResult =
        withContext(Dispatchers.IO) {
            val url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + apiKey
            val body = JSONObject().apply {
                put("system_instruction", JSONObject().put("parts", JSONArray().put(JSONObject().put("text", systemPrompt))))
                put("contents", contents)
                if (tools != null && tools.length() > 0) {
                    put("tools", JSONArray().put(JSONObject().put("function_declarations", tools)))
                }
                put("generationConfig", JSONObject().put("temperature", 0.7).put("maxOutputTokens", 2048))
            }

            val req = Request.Builder().url(url).post(body.toString().toRequestBody(JSON)).build()
            http.newCall(req).execute().use { resp ->
                val txt = resp.body?.string() ?: "{}"
                if (!resp.isSuccessful) {
                    val msg = try {
                        val err = JSONObject(txt).getJSONObject("error").getString("message")
                        "⚠️ Gemini respondeu " + resp.code + ": " + err
                    } catch (_: Exception) { "⚠️ Gemini respondeu " + resp.code }
                    throw IllegalStateException(msg)
                }
                val candidates = JSONObject(txt).optJSONArray("candidates")
                if (candidates == null || candidates.length() == 0) {
                    val block = JSONObject(txt).optJSONObject("promptFeedback")?.optString("blockReason")
                    if (block != null) throw IllegalStateException("resposta bloqueada: " + block)
                    return@withContext GeminiResult(null, emptyList(), model)
                }
                val parts = candidates.getJSONObject(0).optJSONObject("content")?.optJSONArray("parts") ?: JSONArray()
                val sb = StringBuilder()
                val callParts = mutableListOf<JSONObject>()
                for (i in 0 until parts.length()) {
                    val p = parts.getJSONObject(i)
                    if (p.has("text")) sb.append(p.getString("text"))
                    if (p.has("functionCall")) callParts.add(p)
                }
                GeminiResult(sb.toString().trim().ifEmpty { null }, callParts, model)
            }
        }
}

/**
 * Rede de segurança de DNS: usa o resolvedor do sistema; se ele falhar
 * (UnknownHostException / "Unable to resolve host"), monta um pacote de
 * consulta DNS na mão e pergunta direto pros servidores públicos.
 */
object FallbackDns : Dns {
    override fun lookup(hostname: String): List<InetAddress> = try {
        Dns.SYSTEM.lookup(hostname)
    } catch (e: UnknownHostException) {
        udpLookup(hostname)
    }

    private fun udpLookup(hostname: String): List<InetAddress> {
        val name = hostname.trimEnd('.')
        for (srv in listOf("8.8.8.8", "8.8.4.4", "1.1.1.1")) {
            try {
                val id = Random.nextInt(65536)
                val q = ByteArrayOutputStream()
                q.write(byteArrayOf(((id shr 8) and 0xFF).toByte(), (id and 0xFF).toByte(),
                    0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00))
                for (label in name.split('.')) {
                    val bs = label.toByteArray(Charsets.US_ASCII)
                    if (bs.isEmpty() || bs.size > 63) throw UnknownHostException(hostname)
                    q.write(bs.size)
                    q.write(bs)
                }
                q.write(0)
                q.write(byteArrayOf(0x00, 0x01, 0x00, 0x01))
                val pkt = q.toByteArray()
                DatagramSocket().use { s ->
                    s.soTimeout = 3000
                    s.send(DatagramPacket(pkt, pkt.size, InetAddress.getByName(srv), 53))
                    val buf = ByteArray(2048)
                    val rp = DatagramPacket(buf, buf.size)
                    s.receive(rp)
                    val ips = parseA(buf)
                    if (ips.isNotEmpty()) return ips.map { InetAddress.getByAddress(it) }
                }
            } catch (_: Exception) { /* tenta o próximo servidor */ }
        }
        throw UnknownHostException(hostname)
    }

    private fun parseA(b: ByteArray): List<ByteArray> {
        if (b.size < 12) return emptyList()
        val anCount = ((b[6].toInt() and 0xFF) shl 8) or (b[7].toInt() and 0xFF)
        var i = 12
        while (i < b.size && b[i] != 0.toByte()) i += (b[i].toInt() and 0xFF) + 1
        i += 5
        val ips = mutableListOf<ByteArray>()
        repeat(anCount) {
            if (i >= b.size) return@repeat
            if (i < b.size && (b[i].toInt() and 0xC0) == 0xC0) {
                i += 2
            } else {
                while (i < b.size && b[i] != 0.toByte()) i += (b[i].toInt() and 0xFF) + 1
                i++
            }
            if (i + 10 > b.size) return@repeat
            val type = ((b[i].toInt() and 0xFF) shl 8) or (b[i + 1].toInt() and 0xFF)
            val rdlen = ((b[i + 8].toInt() and 0xFF) shl 8) or (b[i + 9].toInt() and 0xFF)
            i += 10
            if (type == 1 && rdlen == 4 && i + 4 <= b.size) ips.add(b.copyOfRange(i, i + 4))
            i += rdlen
        }
        return ips
    }
}
