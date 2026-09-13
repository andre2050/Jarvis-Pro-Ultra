"""O cérebro do JARVIS: persona + loop de function calling.

Um turno pode gerar várias rodadas: Gemini pede tools -> executamos ->
devolvemos -> resposta final. Mesma arquitetura do Android v4.3.0.
"""
import threading
import time

from . import gemini_client, memory, ollama_client, perception, tools
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


def process(cfg: dict, history: list, user_message: str) -> TurnResult:
    """Processa uma mensagem com o cérebro ativo — Gemini (nuvem) ou Ollama
    (100% offline). Mesmo histórico canônico; mesmo loop de function calling."""
    history.append({"role": "user", "parts": [{"text": user_message}]})

    memory.ensure()
    memory.log_interaction("chat", user_message[:80])

    mems = memory.buscar(user_message)
    prompt = system_prompt() + "\n" + perception.contexto_do_computador()
    if mems:
        prompt += "\nMemórias de longo prazo sobre o senhor (use quando relevante):\n- " + "\n- ".join(mems)

    if cfg.get("cerebro") == "ollama":
        return _process_ollama(cfg, history, prompt)

    tools_used = []
    api_key = cfg.get("gemini_api_key", "")

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


# ==================== OLLAMA (offline) ====================

def _para_ollama(history: list) -> list:
    """Converte o histórico canônico (formato Gemini) pro formato Ollama."""
    out = []
    for h in history:
        role = "assistant" if h.get("role") == "model" else h.get("role", "user")
        for p in h.get("parts", []):
            if "text" in p:
                out.append({"role": role, "content": p["text"]})
            elif "functionCall" in p:
                fc = p["functionCall"]
                out.append({"role": "assistant", "content": "",
                            "tool_calls": [{"function": {
                                "name": fc.get("name", ""),
                                "arguments": fc.get("args") or {}}}]})
            elif "functionResponse" in p:
                fr = p["functionResponse"]
                out.append({"role": "tool", "tool_name": fr.get("name", ""),
                            "content": str(fr.get("response", {}).get("result", ""))})
    return out


def _process_ollama(cfg: dict, history: list, prompt: str) -> TurnResult:
    """Loop de function calling rodando em modelo local — sem internet."""
    modelo = cfg.get("ollama_model") or "llama3.2"
    tools_used = []
    decls = [{"name": d["name"], "description": d["description"],
              "parameters": d["parameters"]} for d in todas_declaracoes()]

    if not ollama_client.disponivel():
        history.append({"role": "model", "parts": [{"text": "(offline)"}]})
        return TurnResult("O Ollama não está respondindo, senhor. Rode `ollama serve` "
                          "(ou abra o app do Ollama) e tente de novo — ou volte ao "
                          "Gemini em ⚙ CONFIG.", history, tools_used)

    for _round in range(1, MAX_TOOL_ROUNDS + 1):
        try:
            res = ollama_client.chat(modelo, _para_ollama(history), tools=decls, system=prompt)
        except Exception as e:
            history.append({"role": "model", "parts": [{"text": "(erro)"}]})
            return TurnResult(f"Falha ao falar com o Ollama: {e}", history, tools_used)

        if not res["tool_calls"]:
            texto = res["texto"] or "(silêncio pensativo...)"
            history.append({"role": "model", "parts": [{"text": texto}]})
            return TurnResult(texto, history, tools_used)

        # registra as chamadas no histórico canônico (mesmo formato do Gemini)
        history.append({"role": "model", "parts": [
            {"functionCall": {"name": c["name"], "args": c["args"]}} for c in res["tool_calls"]]})
        resp_parts = []
        for c in res["tool_calls"]:
            try:
                output = _executa_tool(c["name"], c["args"])
            except Exception as e:
                output = f"erro ao executar '{c['name']}': {e}"
            memory.log_interaction(c["name"], str(output)[:80])
            tools_used.append(c["name"])
            resp_parts.append({"functionResponse": {"name": c["name"],
                                                    "response": {"result": output}}})
        history.append({"role": "user", "parts": resp_parts})

    return TurnResult("Cheguei ao limite de tools num único turno, senhor — que tal quebrar a pergunta?",
                      history, tools_used)


def process_async(cfg: dict, history: list, user_message: str, callback):
    """Roda o turno numa thread; callback(TurnResult ou RuntimeError) no fim."""
    def run():
        try:
            callback(process(cfg, history, user_message))
        except Exception as e:
            callback(e)
    threading.Thread(target=run, daemon=True).start()
