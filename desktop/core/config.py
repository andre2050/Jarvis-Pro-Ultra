"""Configurações persistidas — ~/.jarvis_pro_ultra/config.json"""
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".jarvis_pro_ultra"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "gemini_api_key": "",
    "voz_ativa": True,
    "voz_velocidade": 0.85,      # mais lenta = mais mordomo
    "voz_volume": 1.0,
    "usuario": "senhor",
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        if CONFIG_FILE.exists():
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return cfg


def save(cfg: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def api_key_ok(cfg: dict) -> bool:
    return bool(cfg.get("gemini_api_key", "").strip())
