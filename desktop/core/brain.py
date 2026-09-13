"""O cérebro do JARVIS: persona + loop de function calling.

Um turno pode gerar várias rodadas: Gemini pede tools -> executamos ->
devolvemos -> resposta final. Mesma arquitetura do Android v4.3.0.
"""
import threading
import time

from . import gemini_client, memory, perception, tools
from version import __version__

MAX_TOOL_ROUNDS = 4
RETRY_503 = 2  # retentativas enxutas (v4.0.1)


def system_prompt() -> str:
    return f"""
Você é J.A.R.V.I.S PRO ULTRA, o assistente pessoal do André, no computador desktop.
Personalidade: direto, levemente espirituoso, eficiente — um mordomo digital de língua afiada.
Regras:
- Responda sempre em português do Brasil, de forma curta e prática (no máximo 3 frases, salvo pedido explícito).
- Chame o usuário de 'senhor' com bom humor, sem exagero.
- Quando precisar de hora, status do computador ou humor, use as tools disponíveis.
- Você controla o computador do senhor: abrir apps (abrir_app), sites (abrir_site), música no YouTube (tocar_musica), volume (controlar_volume) e timers (definir_timer). Prefira sempre as tools quando ele pedir ações do computador.
- PERCEPÇÃO TOTAL (v4.0): clima (tempo real via Open-Meteo), onde_estou (cidade via IP), navegar_para (abre o mapa com a rota) e pesquisar_web.
- Você tem memória de longo prazo: quando o usuário pedir para lembrar ou guardar algo, chame a tool lembrar_fato. Para listar, listar_memorias.
- No fim deste prompt vem o CONTEXTO VIVO do computador (hora, CPU, RAM, bateria) — você já sabe isso sem precisar de tools; cite quando for útil (ex: 'CPU em 87%, senhor, sugiro fechar umas abas').
- Quando o senhor pedir um resumo/briefing do dia, componha com o contexto vivo e listar_memorias — um resumo curto e espirituoso.
- Se não tiver a tool certa, responda o melhor que puder e sugira o que pode fazer.
- Versão atual do sistema: {__version__} (edição desktop em Python).
""".strip()


class TurnResult:
    def __init__(self, reply: str, history: list, tools_used: list):
        self.reply = reply
        self.history = history
        self.tools_used = tools_used


def process(api_key: str, history: list, user_message: str) -> TurnResult:
    """Processa uma mensagem: roda o loop de function calling e devolve a
    resposta final + histórico atualizado (incluindo as rodadas de tool)."""
    history.append({"role": "user", "parts": [{"text": user_message}]})

    memory.ensure()
    memory.log_interaction("chat", user_message[:80])

    mems = memory.buscar(user_message)
    prompt = system_prompt() + "\n" + perception.contexto_do_computador()
    if mems:
        prompt += "\nMemórias de longo prazo sobre o senhor (use quando relevante):\n- " + "\n- ".join(mems)

    tools_used = []

    for _round in range(1, MAX_TOOL_ROUNDS + 1):
        result = gemini_client.turn(api_key, prompt, history, tools.declarations())

        if not result.function_call_parts:
            if result.text:
                history.append({"role": "model", "parts": [{"text": result.text}]})
                return TurnResult(result.text, history, tools_used)
            # evita histórico inválido (silêncio pensativo)
            history.append({"role": "model", "parts": [{"text": "(silêncio pensativo...)"}]})
            return TurnResult("Desculpe, senhor — não consegui formular uma resposta. Tente de novo.",
                              history, tools_used)

        # modelo pediu tools -> devolve as PARTES INTEIRAS (com thoughtSignature se houver)
        history.append({"role": "model", "parts": result.function_call_parts})

        response_parts = []
        for part in result.function_call_parts:
            call = part.get("functionCall", {})
            name = call.get("name", "")
            args = call.get("args") or {}
            try:
                output = tools.execute(name, args)
            except Exception as e:
                output = f"erro ao executar '{name}': {e}"
            memory.log_interaction(name, str(output)[:80])
            tools_used.append(name)
            response_parts.append({
                "functionResponse": {"name": name, "response": {"result": output}}
            })
        history.append({"role": "user", "parts": response_parts})

    return TurnResult("Cheguei ao limite de tools num único turno, senhor — que tal quebrar a pergunta?",
                      history, tools_used)


def process_async(api_key: str, history: list, user_message: str, callback):
    """Roda o turno numa thread; callback(TurnResult ou RuntimeError) no fim."""
    def run():
        try:
            callback(process(api_key, history, user_message))
        except Exception as e:
            callback(e)
    threading.Thread(target=run, daemon=True).start()
