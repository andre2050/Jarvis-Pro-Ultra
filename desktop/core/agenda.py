"""Agendador persistente (v4.12.0) — avisos com hora marcada que sobrevivem
a fechar o app.

agenda.json em ~/.jarvis_pro_ultra guarda {id, quando, motivo, criada}.
O main roda uma viga que confere a cada 20s: o que venceu dispara com
voz e mensagem. Se o app só abrir DEPOIS da hora, os avisos atrasados
disparam na hora do boot — nada se perde.

Horários aceitos (o modelo preenche; validação amigável devolve o erro
pra ele se corrigir):
  - "HH:MM"                        -> hoje (se já passou, amanhã)
  - "amanhã HH:MM" / "depois de amanhã HH:MM"
  - "dd/mm HH:MM" ou "dd/mm/aaaa HH:MM"
  - ISO "aaaa-mm-ddTHH:MM"
"""
import json
import re
from datetime import datetime, timedelta

from .config import CONFIG_DIR

AGENDA_FILE = CONFIG_DIR / "agenda.json"


# ---------- persistência ----------

def _load() -> dict:
    try:
        if AGENDA_FILE.exists():
            data = json.loads(AGENDA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"proximo_id": 1, "avisos": []}


def _save(data: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        AGENDA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass


# ---------- parse do horário ----------

def _parse_horario(txt: str):
    """datetime ou None se não entendeu."""
    t = (txt or "").strip().lower()
    agora = datetime.now()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
    if m:
        d = agora.replace(hour=int(m.group(1)) % 24, minute=int(m.group(2)) % 60,
                          second=0, microsecond=0)
        if d <= agora:
            d += timedelta(days=1)
        return d
    m = re.fullmatch(r"(amanh[ãa]|depois de amanh[ãa])\s+(\d{1,2}):(\d{2})", t)
    if m:
        dias = 2 if t.startswith("depois") else 1
        d = (agora + timedelta(days=dias)).replace(
            hour=int(m.group(2)) % 24, minute=int(m.group(3)) % 60,
            second=0, microsecond=0)
        return d
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+(\d{1,2}):(\d{2})", t)
    if m:
        ano = int(m.group(3)) if m.group(3) else agora.year
        try:
            return datetime(ano, int(m.group(2)), int(m.group(1)),
                            int(m.group(4)) % 24, int(m.group(5)) % 60)
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2})", t)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                            int(m.group(4)), int(m.group(5)))
        except ValueError:
            return None
    return None


# ---------- API ----------

def agendar(horario: str, motivo: str) -> str:
    motivo = (motivo or "").strip()
    quando = _parse_horario(horario)
    if quando is None:
        return (f"[ARGUMENTOS INVÁLIDOS] não entendi o horário '{horario}' — use "
                "'18:30', 'amanhã 08:00', '05/12 09:00' ou '2026-12-05T09:00'.")
    if not motivo:
        return "[ARGUMENTOS INVÁLIDOS] falta o motivo do aviso."
    data = _load()
    ident = data.get("proximo_id", 1)
    data["proximo_id"] = ident + 1
    data.setdefault("avisos", []).append({
        "id": ident,
        "quando": quando.isoformat(timespec="minutes"),
        "motivo": motivo[:200],
        "criada": datetime.now().strftime("%d/%m/%Y %H:%M"),
    })
    _save(data)
    return f"Agendado, senhor: {motivo} às {quando.strftime('%H:%M de %d/%m')}. Se o senhor fechar o app antes, o aviso dispara sozinho na próxima abertura."


def listar() -> str:
    data = _load()
    avisos = data.get("avisos", [])
    if not avisos:
        return "Nenhum aviso agendado, senhor."
    linhas = [f"- #{a['id']} · {a['motivo']} · às {a['quando'][:16].replace('T', ' ')}"
              for a in avisos]
    return f"{len(avisos)} aviso(s) agendado(s):\n" + "\n".join(linhas)


def cancelar(ident: int) -> str:
    data = _load()
    avisos = data.get("avisos", [])
    for i, a in enumerate(avisos):
        if a.get("id") == ident:
            avisos.pop(i)
            data["avisos"] = avisos
            _save(data)
            return f"Cancelado, senhor: {a['motivo']}."
    return f"não encontrei o aviso #{ident}, senhor — veja em listar_agenda."


def de_hoje() -> list:
    """[(hora "HH:MM", motivo)] dos avisos agendados pra hoje — pro briefing."""
    hoje = datetime.now().date().isoformat()
    achados = []
    for a in _load().get("avisos", []):
        try:
            quando = datetime.fromisoformat(a["quando"])
            if quando.date().isoformat() == hoje:
                achados.append((quando.strftime("%H:%M"), a["motivo"]))
        except Exception:
            pass
    return achados


def devidos() -> list:
    """Avisos cuja hora já chegou (inclusive os atrasados de quando o app
    estava fechado). Remove do disco e devolve [(motivo, quando_iso)]."""
    agora = datetime.now()
    data = _load()
    prontos, restantes = [], []
    for a in data.get("avisos", []):
        try:
            if datetime.fromisoformat(a["quando"]) <= agora:
                prontos.append((a["motivo"], a["quando"]))
                continue
        except Exception:
            pass
        restantes.append(a)
    if len(restantes) != len(data.get("avisos", [])):
        data["avisos"] = restantes
        _save(data)
    return prontos
