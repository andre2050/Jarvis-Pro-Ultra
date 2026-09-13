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
