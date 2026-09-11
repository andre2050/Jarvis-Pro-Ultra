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
 * Tenta os modelos em ordem — se um foi aposentado (404), cai pro próximo.
 */
object GeminiClient {
    private val MODELS = listOf("gemini-3.6-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash")
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    data class GeminiResult(val text: String?, val functionCalls: List<JSONObject>, val model: String)

    suspend fun turn(apiKey: String, systemPrompt: String, contents: JSONArray, tools: JSONArray?): GeminiResult {
        var lastError: IllegalStateException? = null
        for (m in MODELS) {
            try {
                return callModel(m, apiKey, systemPrompt, contents, tools)
            } catch (e: IllegalStateException) {
                val msg = e.message ?: ""
                if (msg.contains("404") || msg.contains("not found", ignoreCase = true) || msg.contains("not supported", ignoreCase = true)) {
                    lastError = e
                    continue
                }
                throw e
            }
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
                put("generationConfig", JSONObject().put("temperature", 0.7).put("maxOutputTokens", 1024))
            }

            val req = Request.Builder().url(url).post(body.toString().toRequestBody(JSON)).build()
            http.newCall(req).execute().use { resp ->
                val txt = resp.body?.string() ?: "{}"
                if (!resp.isSuccessful) {
                    val msg = try {
                        val err = JSONObject(txt).getJSONObject("error").getString("message")
                        "\u26a0\ufe0f Gemini respondeu " + resp.code + ": " + err
                    } catch (_: Exception) { "\u26a0\ufe0f Gemini respondeu " + resp.code }
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
                val calls = mutableListOf<JSONObject>()
                for (i in 0 until parts.length()) {
                    val p = parts.getJSONObject(i)
                    if (p.has("text")) sb.append(p.getString("text"))
                    if (p.has("functionCall")) calls.add(p.getJSONObject("functionCall"))
                }
                GeminiResult(sb.toString().trim().ifEmpty { null }, calls, model)
            }
        }
}
