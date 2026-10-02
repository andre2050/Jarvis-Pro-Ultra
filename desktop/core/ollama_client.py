"""Cliente Ollama — o cérebro 100% offline do JARVIS.

Fala com o servidor local (http://localhost:11434), sem internet, sem chave,
sem custo. Suporta function calling nativo pros modelos que têm tools
(llama3.1+, qwen2.5, mistral-nemo...). Se o Ollama não estiver rodando,
tudo degrada com elegância — o Gemini segue disponível em ⚙ CONFIG.
"""
import json

import requests

BASE = "http://localhost:11434"
TIMEOUT_CHAT = 300  # modelos grandes podem demorar na primeira resposta


def disponivel() -> bool:
    """True se o servidor Ollama responde na porta padrão."""
    try:
        return requests.get(f"{BASE}/api/tags", timeout=2).status_code == 200
    except Exception:
        return False


def modelos() -> list:
    """Nomes dos modelos já baixados (ex: 'llama3.2:latest')."""
    try:
        r = requests.get(f"{BASE}/api/tags", timeout=3)
        return [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        return []


def chat(modelo: str, messages: list, tools: list | None = None,
         system: str | None = None) -> dict:
    """Um turno de /api/chat. Devolve {"texto": str, "tool_calls": [{name, args}]}.

    Formato das tools: [{"type":"function","function":{"name", "description",
    "parameters"}}] — schema OpenAI, aceito nativamente pelo Ollama.
    """
    msgs = list(messages)
    if system:
        msgs = [{"role": "system", "content": system}] + msgs
    body = {"model": modelo, "messages": msgs, "stream": False}
    if tools:
        body["tools"] = [{"type": "function", "function": t} for t in tools]
    r = requests.post(f"{BASE}/api/chat", json=body, timeout=TIMEOUT_CHAT)
    r.raise_for_status()
    msg = r.json().get("message", {}) or {}
    calls = []
    for c in msg.get("tool_calls") or []:
        fn = c.get("function", {}) or {}
        args = fn.get("arguments", {})
        if isinstance(args, str):  # alguns modelos mandam JSON em string
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        if fn.get("name"):
            calls.append({"name": fn["name"], "args": args or {}})
    return {"texto": (msg.get("content") or "").strip(), "tool_calls": calls}


def _objetos_json(texto: str):
    """Gera cada substring {...} delimitada por chaves BALANCEADAS,
    respeitando aspas e escapes (port do LocalCommandParser Android v4.10.3)."""
    inicio = -1
    profundidade = 0
    em_aspas = False
    escapado = False
    for i, ch in enumerate(texto):
        if profundidade == 0:
            if ch == "{":
                inicio, profundidade = i, 1
                em_aspas = escapado = False
            continue
        if em_aspas:
            if escapado:
                escapado = False
            elif ch == "\\":
                escapado = True
            elif ch == '"':
                em_aspas = False
            continue
        if ch == '"':
            em_aspas = True
        elif ch == "{":
            profundidade += 1
        elif ch == "}":
            profundidade -= 1
            if profundidade == 0:
                yield texto[inicio:i + 1]


def extrair_tool_json(texto: str, nomes_validos: set) -> dict | None:
    """Fallback pro Ollama sem function calling nativo (ex.: gemma3, llama2):
    procura {"tool": "...", "args": {...}} no texto e valida nome e args.
    Retorna {"name": str, "args": dict} ou None."""
    for bruto in _objetos_json(texto or ""):
        try:
            obj = json.loads(bruto)
        except Exception:
            continue
        if not isinstance(obj, dict) or "tool" not in obj:
            continue
        nome = obj.get("tool")
        if not isinstance(nome, str) or nome.strip() not in nomes_validos:
            continue
        args = obj.get("args", {})
        if not isinstance(args, dict):   # null/lista/número: recusa, nunca silencioso
            continue
        return {"name": nome.strip(), "args": args}
    return None
