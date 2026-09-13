"""Memória de longo prazo do JARVIS — mesmas regras da versão Android.

Fatos guardados a pedido do senhor + log de interações, em
~/.jarvis_pro_ultra/memory.json. Busca por palavras-chave, offline.
"""
import json
import re
from datetime import datetime
from pathlib import Path

from .config import CONFIG_DIR

MEMORY_FILE = CONFIG_DIR / "memory.json"

MAX_MEMORIAS = 200       # corta antigas além disso
MAX_LOG = 500


def _load() -> dict:
    try:
        if MEMORY_FILE.exists():
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"memorias": [], "interacoes": []}


def _save(data: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def ensure() -> None:
    _save(_load())


def lembrar(fato: str) -> str:
    data = _load()
    data["memorias"].append({"texto": fato.strip(), "data": datetime.now().strftime("%d/%m/%Y %H:%M")})
    if len(data["memorias"]) > MAX_MEMORIAS:
        data["memorias"] = data["memorias"][-MAX_MEMORIAS:]
    _save(data)
    return f"Memorizado, senhor: {fato.strip()}"


def listar() -> str:
    data = _load()
    mems = data.get("memorias", [])
    if not mems:
        return "Nenhuma memória de longo prazo guardada até agora, senhor."
    linhas = [f"- {m['texto']} (guardada em {m['data']})" for m in mems[-30:]]
    total = len(mems)
    return f"{total} memória(s) guardada(s). Últimas:\n" + "\n".join(linhas)


def buscar(query: str, limite: int = 5) -> list[str]:
    """Busca memórias relevantes por palavras-chave (sem acento/caixa alta)."""
    data = _load()
    palavras = [p for p in re.split(r"\W+", query.lower()) if len(p) >= 4]
    if not palavras:
        return []
    resultados = []
    for m in reversed(data.get("memorias", [])):
        texto = m["texto"].lower()
        pontos = sum(1 for p in palavras if p in texto)
        if pontos:
            resultados.append(f"{m['texto']} (guardada em {m['data']})")
        if len(resultados) >= limite:
            break
    return resultados


def log_interaction(tipo: str, texto: str) -> None:
    data = _load()
    data.setdefault("interacoes", []).append(
        {"tipo": tipo, "texto": texto, "data": datetime.now().isoformat(timespec="seconds")}
    )
    if len(data["interacoes"]) > MAX_LOG:
        data["interacoes"] = data["interacoes"][-MAX_LOG:]
    _save(data)
