"""Configurações centrais do JARVIS.

Lê config/settings.json (cria com defaults na primeira execução).
Tudo que é ajustável sem tocar em código mora aqui:
modelo, voz, idioma, timeouts e a URL do manifesto de update.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "config" / "settings.json"

DEFAULTS = {
    "model": "models/gemini-2.5-flash-native-audio-preview-12-2025",
    "voice": "Charon",
    "language": "pt-BR",
    "tool_timeout_seconds": 90,
    "max_reconnect_delay_seconds": 30,
    "manifest_url": "",
    "hologram_face": True
}


def load_settings() -> dict:
    settings = dict(DEFAULTS)
    try:
        settings.update(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")))
    except FileNotFoundError:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(
            json.dumps(DEFAULTS, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[Settings] Não foi possível ler settings.json: {e} — usando defaults.")
    return settings


SETTINGS = load_settings()
