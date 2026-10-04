"""Briefing matinal (v4.13.0) — porte do briefing falado do Android (v4.9.0).

Ao abrir o app (a partir das 5h da manhã, uma vez por dia), o JARVIS dá
bom-dia com dia/data, clima e o que está na agenda de hoje — tudo
composto offline, sem gastar cérebro. O senhor também pode pedir
'briefing' a qualquer hora (intent rápido).
"""
import json
from datetime import datetime

from .config import CONFIG_DIR

ESTADO_FILE = CONFIG_DIR / "briefing.json"

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]


def _estado() -> dict:
    try:
        if ESTADO_FILE.exists():
            data = json.loads(ESTADO_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _marcar_dia() -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ESTADO_FILE.write_text(json.dumps(
            {"ultimo": datetime.now().strftime("%d/%m/%Y")}), encoding="utf-8")
    except Exception:
        pass


def gerar() -> str:
    """Compõe o briefing com o que se sabe SEM cérebro (hora, agenda,
    clima via Open-Meteo, última memória). Nunca lança exceção."""
    agora = datetime.now()
    saudacao = ("Bom dia" if 5 <= agora.hour < 12
                else "Boa tarde" if 12 <= agora.hour < 18 else "Boa noite")
    partes = [f"{saudacao}, senhor. Hoje é {DIAS[agora.weekday()]}, "
              f"{agora.strftime('%d/%m/%Y')} às {agora.strftime('%H:%M')}."]

    try:
        from . import agenda
        avisos = agenda.de_hoje()
        if avisos:
            itens = "; ".join(f"{h} {m}" for h, m in avisos)
            partes.append(f"Na agenda de hoje: {itens}.")
        else:
            partes.append("Nada na agenda de hoje.")
    except Exception:
        pass

    try:
        from . import tools
        clima = tools.execute("clima", {})
        if clima and "indispon" not in clima.lower():
            partes.append(f"No tempo: {clima[:130]}")
    except Exception:
        pass

    try:
        from . import memory
        mems = memory.dados()
        if mems:
            partes.append(f"Última coisa que me pediu pra lembrar: "
                          f"{mems[-1]['texto'][:90]}.")
    except Exception:
        pass

    return " ".join(partes)


def do_boot(hora_minima: int = 5) -> str | None:
    """Briefing do boot: só na primeira abertura do dia (a partir das 5h).
    Devolve o texto pra falar, ou None se já deu hoje / ainda é madrugada."""
    agora = datetime.now()
    if agora.hour < hora_minima:
        return None
    if _estado().get("ultimo") == agora.strftime("%d/%m/%Y"):
        return None
    _marcar_dia()
    return gerar()
