package com.andre.jarvisultra

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Cliente do Gemini com function calling real (o mesmo protocolo do JARVIS desktop).
 * Contém: contents (histórico), system_instruction (persona) e tools (manifesto de tools).
 */
object GeminiClient {
    private const val MODEL = "gemini-2.0-flash"
    private const val BASE = "https://generativelanguage.googleapis.com/v1beta/models/$MODEL:generateContent"
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    data class GeminiResult(val text: String?, val functionCalls: List<JSONObject>)

    /**
     * Envia o turno pro Gemini. [contents] carrega o histórico completo do chat,
     * incluindo parts de functionCall/functionResponse das rodadas anteriores.
     */
    suspend fun turn(apiKey: String, systemPrompt: String, contents: JSONArray, tools: JSONArray?): GeminiResult =
        withContext(Dispatchers.IO) {
            val body = JSONObject().apply {
                put("system_instruction", JSONObject().put("parts", JSONArray().put(JSONObject().put("text", systemPrompt))))
                put("contents", contents)
                if (tools != null && tools.length() > 0) put("tools", JSONArray().put(JSONObject().put("function_declarations", tools)))
                put("generationConfig", JSONObject()
                    .put("temperature", 0.7)
                    .put("maxOutputTokens", 1024))
            }

            val req = Request.Builder()
                .url("$BASE?key=$apiKey")
                .post(body.toString().toRequestBody(JSON))
                .build()

            http.newCall(req).execute().use { resp ->
                val txt = resp.body?.string() ?: "{}"
                if (!resp.isSuccessful) {
                    val msg = try {
                        val err = JSONObject(txt).getJSONObject("error").getString("message")
                        "⚠️ Gemini respondeu ${resp.code}: $err"
                    } catch (_: Exception) { "⚠️ Gemini respondeu ${resp.code}" }
                    throw IllegalStateException(msg)
                }
                val candidates = JSONObject(txt).optJSONArray("candidates") ?: JSONArray()
                if (candidates.length() == 0) return@withContext GeminiResult(null, emptyList())

                val parts = candidates.getJSONObject(0).getJSONObject("content").optJSONArray("parts") ?: JSONArray()
                val sb = StringBuilder()
                val calls = mutableListOf<JSONObject>()
                for (i in 0 until parts.length()) {
                    val p = parts.getJSONObject(i)
                    if (p.has("text")) sb.append(p.getString("text"))
                    if (p.has("functionCall")) calls.add(p.getJSONObject("functionCall"))
                }
                GeminiResult(sb.toString().trim().ifEmpty { null }, calls)
            }
        }
}
