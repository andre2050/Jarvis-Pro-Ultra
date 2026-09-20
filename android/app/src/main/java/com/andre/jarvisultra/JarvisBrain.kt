package com.andre.jarvisultra

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * O cérebro do JARVIS: persona + loop de function calling (mesma arquitetura do desktop).
 * Um turno pode gerar várias rodadas: Gemini pede tools -> executamos -> devolvemos -> resposta final.
 */
object JarvisBrain {

    const val APP_VERSION = "4.10.1"
    private const val MAX_TOOL_ROUNDS = 4

    fun systemPrompt(): String = """
        Você é J.A.R.V.I.S PRO ULTRA, o assistente pessoal do André, no Android.
        (Se ele configurou outro nome pra você ou pra ele no ⚙ CONFIG, trate-o pelo nome escolhido.)
        Personalidade: direto, levemente espirituoso, eficiente — um mordomo digital de língua afiada.
        Regras:
        - Responda sempre em português do Brasil, de forma curta e prática (no máximo 3 frases, salvo pedido explícito).
        - Quando precisar de cálculo, hora, status do dispositivo ou humor, use as tools disponíveis.
        - Chame o usuário de 'senhor' com bom humor, sem exagero — mas se ele tem um nome salvo no CONTEXTO VIVO (campo 'nome'), prefira o nome.
        - Se não tiver a tool certa, responda o melhor que puder e sugira o que pode fazer.
        - Você tem memória de longo prazo: quando o usuário pedir para lembrar ou guardar algo, chame a tool lembrar_fato.
        - Você controla o celular do senhor: ligações (ligar_para), WhatsApp (abre o chat com a mensagem pronta — o toque final de envio é dele, nunca prometa envio automático), SMS, leitura de notificações e SMS, alarmes, timers, lanterna, abrir apps, agenda (criar_lembrete — você calcula data/hora em ms), email (enviar_email) e o painel holográfico (abrir_modo_mesa). Prefira sempre as tools quando ele pedir ações do telefone.
        - Também tem: definir_timer, pesquisar_web e listar_memorias. E o modo mãos-livres: o senhor fala 'Jarvis' e depois o comando por voz, tudo offline.
        - VISÃO COMPUTACIONAL (v4.5): quando o senhor pedir para ver/olhar algo pela câmera, ler texto físico (etiqueta, conta, papel) ou identificar um objeto, chame ver_camera (pode escolher a câmera: 'frontal' para se olhar/olhar o senhor, 'traseira' para apontar pro mundo) — a foto chegará em seguida na conversa como imagem; analise-a com precisão: descreva objetos e contexto, transcreva textos por completo e responda o que foi pedido.
        - PERCEPÇÃO TOTAL (v4.0): clima (tempo real via GPS), onde_estou (bairro/cidade via GPS), navegar_para (abre o mapa com rota), tocar_musica (YouTube/Spotify) e controlar_volume.
        - No fim deste prompt vem o CONTEXTO VIVO do aparelho (hora, bateria, volume) — você já sabe isso sem precisar de tools; cite quando for útil (ex: 'bateria em 12%, senhor, sugiro o carregador').
        - Quando o senhor pedir um resumo/briefing do dia, componha com o contexto vivo, ler_notificacoes e listar_memorias — um resumo curto e espirituoso.
        - Versão atual do sistema: $APP_VERSION (compilado como APK Android).
    """.trimIndent()

    data class TurnResult(val reply: String, val updatedContents: JSONArray, val toolsUsed: List<String>)

    /**
     * Processa uma mensagem do usuário: roda o loop de function calling e devolve
     * a resposta final + o histórico atualizado (incluindo as rodadas de tool).
     */
    suspend fun process(ctx: Context, apiKey: String, history: JSONArray, userMessage: String,
                           imageB64: String? = null, imageMime: String = "image/jpeg"): TurnResult {
        val contents = history
        val userParts = JSONArray()
        if (imageB64 != null) {
            userParts.put(JSONObject().put("inline_data", JSONObject()
                .put("mime_type", imageMime).put("data", imageB64)))
        }
        userParts.put(JSONObject().put("text", userMessage))
        contents.put(JSONObject()
            .put("role", "user")
            .put("parts", userParts))

        JarvisMemory.ensure(ctx)
        JarvisMemory.logInteraction(ctx, "chat", userMessage.take(80))

        val mems = JarvisMemory.search(ctx, userMessage)
        val basePrompt = systemPrompt() + "\n" + JarvisPercepcao.contextoDoAparelho(ctx)
        val visaoNota = if (imageB64 != null) "\nVISÃO: o senhor acaba de enviar uma FOTO pela câmera — analise a imagem recebida (descreva, transcreva textos, responda a pergunta) antes de qualquer outra coisa." else ""
        val prompt = (if (mems.isEmpty()) basePrompt + visaoNota else
            basePrompt + visaoNota + "\nMem\u00f3rias de longo prazo sobre o usu\u00e1rio (use quando relevante):\n- " + mems.joinToString("\n- ")
        )

        // ---- v4.10.0: CÉREBRO LOCAL (offline) ----
        // v4.10.1: no modo LOCAL o app NUNCA cai pra nuvem em silêncio —
        // se o senhor escolheu local, ele diz exatamente o que falta.
        val modoLocal = SettingsStore.getBrainMode(ctx) == "local" && imageB64 == null
        if (modoLocal) {
            if (!JarvisLocalLLM.hasModel(ctx)) {
                return TurnResult(
                    "O modo LOCAL está ligado, mas o modelo offline ainda não foi baixado, senhor. Toque em ⚙ CONFIG → CÉREBRO LOCAL → Baixar cérebro offline (529MB, uma vez só, com internet). Depois de baixado, eu penso 100% sem internet — até em modo avião.",
                    contents, emptyList())
            }
            val local = turnoLocal(ctx, contents, userMessage, mems)
            if (local != null) return local
            return TurnResult(
                "O modelo local não conseguiu carregar agora, senhor — provavelmente memória do aparelho apertada. Feche outros apps e tente de novo, ou volte pro modo ☁️ NUVEM em ⚙ CONFIG.",
                contents, emptyList())
        }

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

    // ================= CÉREBRO LOCAL (v4.10.0) =================

    /** Um turno 100% offline com o Gemma 3 1B do aparelho. Null = não conseguiu (cae pro Gemini). */
    private suspend fun turnoLocal(ctx: Context, contents: JSONArray, userMessage: String,
                                      mems: List<String>): TurnResult? {
        val llm = JarvisLocalLLM.obter(ctx) ?: return null
        JarvisMemory.ensure(ctx)

        // ferramentas em formato compacto pro modelo pequeno
        val decls = JarvisTools.declarations()
        val nomes = mutableSetOf<String>()
        val lista = StringBuilder()
        for (i in 0 until decls.length()) {
            val d = decls.optJSONObject(i) ?: continue
            val nome = d.optString("name")
            nomes.add(nome)
            val desc = d.optString("description").replace("\n", " ").take(110)
            lista.append("- ").append(nome).append(": ").append(desc).append('\n')
        }

        val sys = """
            Você é J.A.R.V.I.S PRO ULTRA, o assistente pessoal do André, rodando 100% OFFLINE dentro do celular dele.
            Personalidade: direto, levemente espirituoso, eficiente — um mordomo digital de língua afiada.
            Regras:
            - Responda sempre em português do Brasil, curto e prático (máximo 3 frases).
            - Chame o usuário de 'senhor'.
            - Você tem FERRAMENTAS do telefone. Para usar uma, responda APENAS um JSON: {"tool": "nome_da_ferramenta", "args": {}}
            - Para responder sem ferramenta, responda APENAS um JSON: {"resposta": "seu texto aqui"}
            - NÃO use ferramenta se a resposta for conversa, opinião ou conhecimento geral.
            FERRAMENTAS DISPONÍVEIS:
            ${lista.toString().trim()}
        """.trimIndent()

        val memoria = if (mems.isEmpty()) "" else
            "\nMemórias de longo prazo sobre o usuário (use quando relevante):\n- " + mems.take(5).joinToString("\n- ")

        val conversa = StringBuilder()
        val ultimos = mutableListOf<String>()
        for (i in 0 until contents.length()) {
            val turn = contents.optJSONObject(i) ?: continue
            val quem = if (turn.optString("role") == "user") "Usuário: " else "JARVIS: "
            val parts = turn.optJSONArray("parts") ?: continue
            for (j in 0 until parts.length()) {
                val part = parts.optJSONObject(j) ?: continue
                val txt = part.opt("text") as? String ?: continue
                ultimos.add(quem + txt.trim())
            }
        }
        for (linha in ultimos.takeLast(8).dropLast(1)) conversa.append(linha).append('\n')

        var prompt = sys + "\n" + JarvisPercepcao.contextoDoAparelho(ctx) + memoria +
            "\nCONVERSA ATÉ AGORA:\n" + conversa.toString().trim() +
            "\nUsuário: " + userMessage.trim() + "\nJARVIS:"

        val toolsUsed = mutableListOf<String>()
        var resposta = ""

        for (round in 1..2) {
            val saida = try {
                kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { llm.generateResponse(prompt) }
            } catch (e: Exception) { return null }

            val (toolNome, toolArgs) = parseTool(saida)
            if (toolNome == null || toolNome !in nomes) {
                resposta = parseResposta(saida)
                break
            }

            // modelo pediu ferramenta -> executa e faz a 2ª rodada com o resultado
            val output = try {
                JarvisTools.execute(ctx, toolNome, toolArgs)
            } catch (e: Exception) { "erro na ferramenta: ${e.message}" }
            JarvisMemory.logInteraction(ctx, toolNome, output.take(80))
            toolsUsed.add(toolNome)

            prompt = prompt + "\nJARVIS (pediu ferramenta {\"tool\": \"$toolNome\"})\n" +
                "RESULTADO DA FERRAMENTA $toolNome: $output\n" +
                "Agora responda ao usuário com o resultado em APENAS um JSON: {\"resposta\": \"texto curto em português\"}.\nJARVIS:"
        }

        if (resposta.isBlank()) resposta = "Desculpe, senhor — o processador local travou no raciocínio. Pergunte de novo."
        contents.put(JSONObject()
            .put("role", "model")
            .put("parts", JSONArray().put(JSONObject().put("text", resposta))))
        return TurnResult(resposta, contents, toolsUsed)
    }

    /** Procura {"tool": ..., "args": {...}} na saída do modelo pequeno. */
    private fun parseTool(saida: String): Pair<String?, JSONObject> {
        val regex = Regex("""\{[^{}]*"tool"[^{}]*\}""")
        val m = regex.find(saida) ?: return Pair(null, JSONObject())
        return try {
            val o = JSONObject(m.value)
            val args = try { o.optJSONObject("args") ?: JSONObject() } catch (_: Exception) { JSONObject() }
            Pair(o.optString("tool"), args)
        } catch (_: Exception) { Pair(null, JSONObject()) }
    }

    /** Extrai {"resposta": ...} ou limpa o texto cru do modelo. */
    private fun parseResposta(saida: String): String {
        val regex = Regex("""\{\s*"resposta"\s*:\s*"(.*?)"\s*\}""", RegexOption.DOT_MATCHES_ALL)
        val m = regex.find(saida)
        if (m != null) {
            return m.groupValues[1]
                .replace("\\n", "\n")
                .replace("\\'", "'")
        }
        // sem JSON: devolve o texto sem a persona vazando
        var t = saida.trim()
        if (t.startsWith("{") && t.endsWith("}")) {
            try { t = JSONObject(t).optString("resposta", t) } catch (_: Exception) { }
        }
        return t.take(600)
    }
}
