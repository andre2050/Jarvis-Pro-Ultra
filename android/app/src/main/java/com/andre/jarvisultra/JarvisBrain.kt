package com.andre.jarvisultra

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * O cérebro do JARVIS: persona + loop de function calling (mesma arquitetura do desktop).
 * Um turno pode gerar várias rodadas: Gemini pede tools -> executamos -> devolvemos -> resposta final.
 */
object JarvisBrain {

    const val APP_VERSION = "1.0.1"
    private const val MAX_TOOL_ROUNDS = 4

    fun systemPrompt(): String = """
        Você é J.A.R.V.I.S PRO ULTRA, o assistente pessoal do André, no Android.
        Personalidade: direto, levemente espirituoso, eficiente — um mordomo digital de língua afiada.
        Regras:
        - Responda sempre em português do Brasil, de forma curta e prática (no máximo 3 frases, salvo pedido explícito).
        - Quando precisar de cálculo, hora, status do dispositivo ou humor, use as tools disponíveis.
        - Chame o usuário de 'senhor' com bom humor, sem exagero.
        - Se não tiver a tool certa, responda o melhor que puder e sugira o que pode fazer.
        - Versão atual do sistema: $APP_VERSION (compilado como APK Android).
    """.trimIndent()

    data class TurnResult(val reply: String, val updatedContents: JSONArray, val toolsUsed: List<String>)

    /**
     * Processa uma mensagem do usuário: roda o loop de function calling e devolve
     * a resposta final + o histórico atualizado (incluindo as rodadas de tool).
     */
    suspend fun process(ctx: Context, apiKey: String, history: JSONArray, userMessage: String): TurnResult {
        val contents = history
        contents.put(JSONObject()
            .put("role", "user")
            .put("parts", JSONArray().put(JSONObject().put("text", userMessage))))

        val toolsUsed = mutableListOf<String>()

        for (round in 1..MAX_TOOL_ROUNDS) {
            val result = GeminiClient.turn(apiKey, systemPrompt(), contents, JarvisTools.declarations())

            if (result.functionCalls.isEmpty()) {
                if (result.text != null) {
                    contents.put(JSONObject()
                        .put("role", "model")
                        .put("parts", JSONArray().put(JSONObject().put("text", result.text))))
                } else {
                    contents.put(JSONObject()
                        .put("role", "model")
                        .put("parts", JSONArray().put(JSONObject().put("text", "(silêncio pensativo...)")))) // evita histórico inválido
                    return TurnResult("Desculpe, senhor — não consegui formular uma resposta. Tente de novo.", contents, toolsUsed)
                }
                return TurnResult(result.text ?: "", contents, toolsUsed)
            }

            // modelo pediu tools -> registra as chamadas e responde cada uma
            val callParts = JSONArray()
            for (c in result.functionCalls) callParts.put(JSONObject().put("functionCall", c))
            contents.put(JSONObject().put("role", "model").put("parts", callParts))

            val responseParts = JSONArray()
            for (c in result.functionCalls) {
                val name = c.optString("name")
                val args = c.optJSONObject("args") ?: JSONObject()
                val output = JarvisTools.execute(ctx, name, args)
                toolsUsed.add(name)
                responseParts.put(JSONObject()
                    .put("functionResponse", JSONObject()
                        .put("name", name)
                        .put("response", JSONObject().put("result", output))))
            }
            contents.put(JSONObject().put("role", "user").put("parts", responseParts))
        }
        return TurnResult("Cheguei ao limite de tools num único turno, senhor — que tal quebrar a pergunta?", contents, toolsUsed)
    }
}
