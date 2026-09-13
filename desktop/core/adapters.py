"""Adaptadores de contexto — ligam as ações do Mark LIII ao nosso app.

As ações auto-descritivas esperam ctx com `player`, `speak`, `response` e
`session_memory`. Aqui:
  - player          -> PlayerAdapter (write_log vira log do app)
  - speak           -> função que fala com o TTS e mostra no chat (via fila, thread-safe)
  - response        -> None (arquitetura REST não usa; nenhuma ação chama métodos dele)
  - session_memory  -> SessionMemoryAdapter (set_last_search vira log de busca)

Também normaliza os schemas das declarações (OBJECT -> object) pro protocolo
v1beta que usamos.
"""

REGRA_TIPO = {
    "OBJECT": "object", "STRING": "string", "NUMBER": "number",
    "BOOLEAN": "boolean", "ARRAY": "array", "INTEGER": "integer",
}


def normaliza_schema(decl: dict) -> dict:
    """Converte o schema Gemini (OBJECT/STRING...) para minúsculo, recursivamente."""
    import copy
    d = copy.deepcopy(decl)
    params = d.get("parameters")
    if isinstance(params, dict):
        _caminha(params)
    return d


def _caminha(no: dict) -> None:
    if not isinstance(no, dict):
        return
    if "type" in no and isinstance(no["type"], str):
        no["type"] = REGRA_TIPO.get(no["type"], no["type"].lower())
    props = no.get("properties")
    if isinstance(props, dict):
        for v in props.values():
            _caminha(v)
    itens = no.get("items")
    if isinstance(itens, dict):
        _caminha(itens)


class PlayerAdapter:
    """O que as ações do Mark chamam de `player` — aqui é só log."""

    def __init__(self, log_fn=None):
        self._log = log_fn or (lambda msg: print(f"[AÇÃO] {msg}"))

    def write_log(self, msg) -> None:
        try:
            self._log(str(msg))
        except Exception:
            pass


class SessionMemoryAdapter:
    """`session_memory` das ações — guarda a última busca no log de interações."""

    def __init__(self, log_busca=None):
        self._log_busca = log_busca

    def set_last_search(self, **kw) -> None:
        try:
            from . import memory
            memory.log_interaction("busca", str(kw.get("query", ""))[:80])
            if self._log_busca:
                self._log_busca(str(kw.get("query", "")))
        except Exception:
            pass
