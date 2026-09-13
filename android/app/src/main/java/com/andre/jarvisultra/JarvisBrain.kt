package com.andre.jarvisultra

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * O cérebro do JARVIS: persona + loop de function calling (mesma arquitetura do desktop).
 * Um turno pode gerar várias rodadas: Gemini pede tools -> executamos -> devolvemos -> resposta final.
 */
object JarvisBrain {

    const val APP_VERSION = "3.0.1"
    private const val MAX_TOOL_ROUNDS = 4

    fun systemPrompt(): String = """
        Você é J.A.R.V.I.S PRO ULTRA, o assistente pessoal do André, no Android.
        Personalidade: direto, levemente espirituoso, eficiente — um mordomo digital de língua afiada.
        Regras:
        - Responda sempre em português do Brasil, de forma curta e prática (no máximo 3 frases, salvo pedido explícito).
        - Quando precisar de cálculo, hora, status do dispositivo ou humor, use as tools disponíveis.
        - Chame o usuário de 'senhor' com bom humor, sem exagero.
        - Se não tiver a tool certa, responda o melhor que puder e sugira o que pode fazer.
        - Você tem memória de longo prazo: quando o usuário pedir para lembrar ou guardar algo, chame a tool lembrar_fato.
        - Você controla o celular do senhor: ligações (ligar_para), WhatsApp (abre o chat com a mensagem pronta — o toque final de envio é dele, nunca prometa envio automático), SMS, leitura de notificações e SMS, alarmes, lanterna e abrir apps. Prefira sempre as tools quando ele pedir ações do telefone.
        - Também tem: definir_timer, pesquisar_web e listar_memorias. E o modo mãos-livres: o senhor fala 'Jarvis' e depois o comando por voz, tudo offline.
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

        JarvisMemory.ensure(ctx)
        JarvisMemory.logInteraction(ctx, "chat", userMessage.take(80))

        val mems = JarvisMemory.search(ctx, userMessage)
        val prompt = if (mems.isEmpty()) systemPrompt() else
            systemPrompt() + "\nMem\u00f3rias de longo prazo sobre o usu\u00e1rio (use quando relevante):\n- " + mems.joinToString("\n- ")

        val toolsUsed = mutableListOf<String>()

        for (round in 1..MAX_TOOL_ROUNDS) {
            val result = GeminiClient.turn(apiKey, prompt, contents, JarvisTools.declarations())

            if (result.functionCallParts.isEmpty()) {
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

            // modelo pediu tools -> devolve as PARTES INTEIRAS (com thoughtSignature se houver)
            val callParts = JSONArray()
            for (part in result.functionCallParts) callParts.put(part)
            contents.put(JSONObject().put("role", "model").put("parts", callParts))

            val responseParts = JSONArray()
            for (part in result.functionCallParts) {
                val c = part.getJSONObject("functionCall")
                val name = c.optString("name")
                val args = c.optJSONObject("args") ?: JSONObject()
                val output = JarvisTools.execute(ctx, name, args)
                JarvisMemory.logInteraction(ctx, name, output.take(80))
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
