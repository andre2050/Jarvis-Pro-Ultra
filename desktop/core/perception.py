"""Percepção Total (v4.0) adaptada ao desktop: contexto vivo do computador.

Lê hora, CPU, memória RAM e bateria e injeta no prompt do cérebro a cada
turno — o JARVIS SABE sem precisar de tools ("CPU em 87%, senhor, sugiro
fechar umas abas").
"""
import platform
from datetime import datetime

try:
    import psutil
    TEM_PSUTIL = True
except ImportError:
    TEM_PSUTIL = False


def _bateria():
    if not TEM_PSUTIL:
        return None
    try:
        bat = psutil.sensors_battery()
        if bat:
            return round(bat.percent), bool(bat.power_plugged)
    except Exception:
        pass
    return None


def contexto_do_computador() -> str:
    """Contexto vivo injetado no prompt do cérebro a cada turno."""
    try:
        agora = datetime.now()
        hora = agora.strftime("%H:%M")
        dia = agora.strftime("%d/%m/%Y")
        partes = [f"Contexto do computador AGORA: são {hora} de {dia}"]

        if TEM_PSUTIL:
            cpu = psutil.cpu_percent(interval=0.3)
            mem = psutil.virtual_memory()
            total_gb = round(mem.total / (1024 ** 3))
            partes.append(f"CPU em {cpu:.0f}%")
            partes.append(f"memória RAM em {mem.percent:.0f}% de {total_gb} GB")
            bat = _bateria()
            if bat:
                pct, plug = bat
                energia = "carregando" if plug else "na bateria"
                partes.append(f"bateria em {pct}% ({energia})")

        partes.append(f"sistema operacional {platform.system()}")
        return ", ".join(partes) + "."
    except Exception:
        return ""


def leitura_viva() -> dict:
    """Leitura rápida para o HUD (sem bloquear): CPU %, RAM %, bateria %."""
    cpu = ram = bat = None
    if TEM_PSUTIL:
        try:
            cpu = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory().percent
        except Exception:
            pass
        b = _bateria()
        if b:
            bat = b[0]
    return {"cpu": cpu, "ram": ram, "bat": bat}
