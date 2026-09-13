"""O cérebro do JARVIS: persona + loop de function calling.

Um turno pode gerar várias rodadas: Gemini pede tools -> executamos ->
devolvemos -> resposta final. Mesma arquitetura do Android v4.3.0.
"""
import threading
import time

from . import gemini_client, memory, perception, tools
from .adapters import normaliza_schema
from version import __version__

MAX_TOOL_ROUNDS = 6  # v4.4.0: toolkit maior (ações do Mark LIII) pede mais rodadas
RETRY_503 = 2  # retentativas enxutas (v4.0.1)

# Registro das ações auto-descritivas (Mark LIII) — anexado pelo main.py
_registro = None
_ctx = None


def attach_actions(registro, ctx: dict) -> None:
    """Funde as ações descobertas (actions/*.py com TOOL) ao cérebro."""
    global _registro, _ctx
    _registro = registro
    _ctx = ctx


def todas_declaracoes() -> list:
    """Tools nativas + ações do Mark LIII, com schema normalizado."""
    decls = list(tools.declarations())
    if _registro is not None:
        for d in _registro.get_tool_declarations():
            decls.append(normaliza_schema(d))
    return decls


def _executa_tool(name: str, args: dict) -> str:
    """Despacha: primeiro as tools nativas, depois o registro de ações."""
    if name in tools.nomes():
        return tools.execute(name, args)
    if _registro is not None and _registro.has(name):
        return _registro.run(name, args, _ctx or {})
    return f"tool desconhecida: {name}"


def system_prompt() -> str:
    return f"""
Você é J.A.R.V.I.S PRO ULTRA, o assistente pessoal de André Luiz Lima Menezes, no computador desktop dele.
Personalidade: direto, levemente espirituoso, eficiente — um mordomo digital de língua afiada.
Regras:
- Responda sempre em português do Brasil, de forma curta e prática (no máximo 3 frases, salvo pedido explícito).
- Chame o usuário de 'senhor' com bom humor, sem exagero.
- Quando precisar de hora, status do computador ou humor, use as tools disponíveis.
- Você controla o computador do senhor: abrir apps (abrir_app), sites (abrir_site), música no YouTube (tocar_musica), volume (controlar_volume) e timers (definir_timer). Prefira sempre as tools quando ele pedir ações do computador.
- PERCEPÇÃO TOTAL (v4.0): clima (tempo real via Open-Meteo), onde_estou (cidade via IP), navegar_para (abre o mapa com a rota) e pesquisar_web.
- Você tem memória de longo prazo: quando o usuário pedir para lembrar ou guardar algo, chame a tool lembrar_fato. Para listar, listar_memorias.
- Ações do Mark LIII também estão disponíveis (open_app, web_search, browser_control, file_processor, file_controller, code_helper, dev_agent, computer_control, computer_settings, desktop, send_message, youtube_video, reminder, flight_finder, game_updater, weather_report) — use-as quando pedirem arquivos, navegador, código, mensagens ou controle fino do computador. Prefira desfazer_ultima_acao quando o senhor pedir para desfazer algo que você fez.
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
        result = gemini_client.turn(api_key, prompt, history, todas_declaracoes())

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
                output = _executa_tool(name, args)
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
