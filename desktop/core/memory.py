"""Memória de longo prazo do JARVIS — mesmas regras da versão Android.

Fatos guardados a pedido do senhor + log de interações, em
~/.jarvis_pro_ultra/memory.json. Busca por palavras-chave, offline.
"""
import json
import re
from datetime import datetime

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


def dados() -> list[dict]:
    """Lista crua de memórias (para o painel de memória do CONFIG)."""
    return _load().get("memorias", [])


def atualizar(texto_velho: str, texto_novo: str) -> str:
    """v4.14.0: editor de memórias do CONFIG — reescreve o texto mantendo a data."""
    data = _load()
    for m in data.get("memorias", []):
        if m.get("texto") == texto_velho:
            m["texto"] = texto_novo.strip()
            _save(data)
            return "Memória atualizada, senhor."
    return "não encontrei essa memória, senhor."


def esquecer(texto: str) -> str:
    """Apaga a memória cujo texto bate exatamente (para o painel)."""
    data = _load()
    mems = data.get("memorias", [])
    for i, m in enumerate(mems):
        if m.get("texto") == texto:
            mems.pop(i)
            data["memorias"] = mems
            _save(data)
            return f"Esquecida: {texto}"
    return "não encontrei essa memória, senhor."


def limpar() -> str:
    data = _load()
    n = len(data.get("memorias", []))
    data["memorias"] = []
    _save(data)
    return f"{n} memória(s) apagada(s)."


def _normalizar(t: str) -> str:
    """minúsculas e SEM ACENTO (evido/evito, vacina/vacinação)."""
    import unicodedata
    return unicodedata.normalize("NFD", (t or "").lower()).encode(
        "ascii", "ignore").decode()


_STOPWORDS = {"que", "para", "pra", "com", "sem", "senhor", "sobre", "isso",
              "uma", "um", "como", "quando", "onde", "meu", "minha", "seu",
              "sua", "ele", "ela", "não", "nao", "sim", "tem", "vou"}


def buscar(query: str, limite: int = 5) -> list[str]:
    """v4.12.0: busca por RELEVÂNCIA (o RAG leve do pacote) — cada memória
    ganha pontos por palavra casada (sem acento/caixa), bônus se a frase
    inteira aparece, e empata pela mais recente. Retorna as N melhores,
    em vez das N primeiras que casam qualquer palavra."""
    data = _load()
    q = _normalizar(query)
    palavras = [p for p in re.split(r"\W+", q)
                if len(p) >= 3 and p not in _STOPWORDS]
    if not palavras:
        return []
    frase = " ".join(palavras)
    pontuadas = []
    for m in data.get("memorias", []):
        texto = _normalizar(m["texto"])
        pontos = sum(2 for p in palavras if p in texto)
        if pontos == 0:
            continue
        if frase and frase in texto:
            pontos += 3  # a pergunta inteira aparece na memória: forte
        pontuadas.append((pontos, m["data"], f"{m['texto']} (guardada em {m['data']})"))
    # mais pontos primeiro; empate: mais recente
    pontuadas.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [t for _, _, t in pontuadas[:limite]]


def log_interaction(tipo: str, texto: str) -> None:
    data = _load()
    data.setdefault("interacoes", []).append(
        {"tipo": tipo, "texto": texto, "data": datetime.now().isoformat(timespec="seconds")}
    )
    if len(data["interacoes"]) > MAX_LOG:
        data["interacoes"] = data["interacoes"][-MAX_LOG:]
    _save(data)
