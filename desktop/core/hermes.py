"""HERMES — o agente orquestrador do J.A.R.V.I.S (v5.1.0).

Camada separada do cérebro conversacional: enquanto o cérebro responde
turnos, o HERMES PLANEJA. Para pedidos complexos ele pede à rede neural
(Gemini ou Ollama) um plano de execução em JSON, executa os passos um a
um através das tools (nativas + ações Mark LIII), verifica os resultados
e sintetiza a resposta final — como um maestro regendo o arsenal.

Fluxo de um turno em modo HERMES:

    pedido ─► [1] PLANEJAR (LLM sem tools → plano JSON, máx. 8 passos)
              [2] EXECUTAR  (cada passo = 1 chamada de tool, log completo)
              [3] SINTETIZAR (LLM compõe a resposta com os resultados)

Se qualquer etapa falhar, o cérebro normal assume sem falhar na frente do
senhor — o HERMES nunca deixa o JARVIS mudo.

Estado exposto pra interface: hermes.ultimo_plano() / hermes.ultimo_relatorio().
"""
import json
import time

from . import gemini_client, memory, ollama_client

MAX_PASSOS = 8

# ---- estado visível pra interface (⚙ CONFIG → HERMES) ----
_STATUS = {
    "ultimo_pedido": "",
    "plano": [],           # [{passo, tool, args, objetivo}]
    "execucao": [],        # [{passo, tool, ok, resultado}]
    "quando": None,
}


# ==================== chamadas à rede neural ====================

def _chamar_llm(cfg: dict, system: str, mensagem: str) -> str:
    """Uma chamada pura (sem tools) ao cérebro ativo — Gemini ou Ollama."""
    if cfg.get("cerebro") == "ollama":
        modelo = cfg.get("ollama_model") or "llama3.2"
        res = ollama_client.chat(modelo, [{"role": "user", "content": mensagem}],
                                 tools=None, system=system)
        return (res or {}).get("texto", "") or ""
    api_key = cfg.get("gemini_api_key", "")
    result = gemini_client.turn(api_key, system,
                                [{"role": "user", "parts": [{"text": mensagem}]}], None)
    return (getattr(result, "text", "") or "")


def _extrair_json(texto: str) -> dict | None:
    """Pega o primeiro objeto JSON válido do texto (tolera cercas ``` e enrolação)."""
    if not texto:
        return None
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fim <= inicio:
        return None
    try:
        dados = json.loads(texto[inicio:fim + 1])
        return dados if isinstance(dados, dict) else None
    except (ValueError, TypeError):
        return None


# ==================== [1] PLANEJAR ====================

def planejar(cfg: dict, pedido: str, contexto: str) -> list | None:
    """Pede à rede neural um plano de execução. None = desiste (cérebro assume)."""
    from . import brain  # import tardio: evita circularidade

    decls = brain.todas_declaracoes()
    catalogo = "\n".join(f"- {d['name']}: {d['description']}" for d in decls)

    system = (
        "Você é o HERMES, módulo orquestrador do J.A.R.V.I.S. "
        "Sua única função é gerar PLANOS de execução. "
        "Responda SEMPRE e APENAS com um objeto JSON válido, sem texto extra."
    )
    mensagem = f"""Catalogo de tools disponiveis:
{catalogo}

Contexto do computador: {contexto}

Pedido do usuario: "{pedido}"

Gere o plano neste formato exato:
{{"plano": [
  {{"passo": 1, "tool": "nome_da_tool", "args": {{...}}, "objetivo": "resumo curto"}},
  {{"passo": 2, "tool": "nome_da_tool", "args": {{...}}, "objetivo": "resumo curto"}}
]}}

Regras:
- Maximo {MAX_PASSOS} passos; cada passo executa UMA chamada de tool.
- So use tools do catalogo — ou a pseudo-tool "responder_direto".
- Se nenhuma tool for necessaria (conversa simples), retorne um unico passo:
  {{"passo": 1, "tool": "responder_direto", "args": {{"texto": "resposta completa em portugues"}}, "objetivo": "responder"}}
- Os "args" devem respeitar os parametros de cada tool; se a tool nao recebe argumentos, use {{}}.
- Ordene os passos logicamente (ex: buscar informacao antes de agir com ela)."""

    try:
        dados = _extrair_json(_chamar_llm(cfg, system, mensagem))
    except Exception:
        return None
    if not dados or not isinstance(dados.get("plano"), list):
        return None
    plano = [p for p in dados["plano"] if isinstance(p, dict) and p.get("tool")]
    return plano[:MAX_PASSOS] or None


# ==================== [2] + [3] EXECUTAR E SINTETIZAR ====================

def executar(cfg: dict, history: list, prompt_sistema: str, pedido: str):
    """Turno completo em modo orquestrado. Retorna TurnResult ou None (fallback)."""
    from . import brain

    plano = planejar(cfg, pedido, prompt_sistema)
    if plano is None:
        return None

    _STATUS.update({"ultimo_pedido": pedido, "plano": plano,
                    "execucao": [], "quando": time.strftime("%d/%m %H:%M")})

    # plano de passo único que já é a resposta
    if len(plano) == 1 and plano[0]["tool"] == "responder_direto":
        reply = str(plano[0].get("args", {}).get("texto", "")).strip()
        if reply:
            history.append({"role": "model", "parts": [{"text": reply}]})
            memory.log_interaction("hermes", f"resposta direta: {reply[:80]}")
            return brain.TurnResult(reply, history, [])

        return None  # resposta vazia — cérebro assume

    # executa os passos
    resultados = []
    tools_used = []
    for i, passo in enumerate(plano, start=1):
        tool = str(passo.get("tool", ""))
        args = passo.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        try:
            saida = brain._executa_tool(tool, args)
            ok = True
        except Exception as e:
            saida = f"erro ao executar '{tool}': {e}"
            ok = False
        tools_used.append(tool)
        memory.log_interaction(tool, str(saida)[:80])
        resultados.append(f"Passo {i} — {tool} ({passo.get('objetivo', '')}): {str(saida)[:400]}")
        _STATUS["execucao"].append({"passo": i, "tool": tool, "ok": ok,
                                    "resultado": str(saida)[:200]})

    # sintetiza a resposta final
    system = brain.system_prompt()
    mensagem = (f"O orquestrador HERMES executou um plano para o pedido do senhor.\n"
                f"Pedido: \"{pedido}\"\n\n"
                f"Resultado de cada passo:\n" + "\n".join(resultados) +
                "\n\nComponha a resposta final ao senhor, curta e prática (máx. 3 frases), "
                "usando o essencial dos resultados. Em português do Brasil.")
    try:
        reply = _chamar_llm(cfg, system, mensagem).strip()
    except Exception as e:
        # sintetizador caiu — devolve os resultados crus em vez de mudo
        reply = ("Plano executado, senhor, mas o redator final falhou "
                 f"(<{e}>). Resultados:\n" + "\n".join(resultados))
    if not reply:
        return None
    history.append({"role": "model", "parts": [{"text": reply}]})
    return brain.TurnResult(reply, history, tools_used)


# ==================== estado pra interface ====================

def ultimo_plano() -> list:
    return _STATUS["plano"]


def ultimo_relatorio() -> str:
    """Texto pronto pro painel ⚙ CONFIG → HERMES."""
    if not _STATUS["quando"]:
        return "HERMES ainda não orquestrou nada, senhor.\nAtive o modo e faça um pedido complexo."
    linhas = [f"Último turno: {_STATUS['quando']} — \"{_STATUS['ultimo_pedido'][:60]}\"", ""]
    for p in _STATUS["plano"]:
        linha = f"{p.get('passo', '?')}. {p.get('tool', '?')} — {p.get('objetivo', '')}"
        for e in _STATUS["execucao"]:
            if e["passo"] == p.get("passo"):
                linha += "" if e["ok"] else "  ✗ ERRO"
        linhas.append(linha)
    return "\n".join(linhas)
