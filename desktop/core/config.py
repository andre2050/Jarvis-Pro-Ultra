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
    "cerebro": "gemini",       # "gemini" (nuvem) | "ollama" (100% offline)
    "ollama_model": "",        # ex: "llama3.2" — escolhido em ⚙ CONFIG
    "tema": "radar",           # "radar" (circular, padrão) | "classico" | "vermelho" | "gold"
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


def sync_api_keys(cfg: dict) -> None:
    """Mantém config/api_keys.json (formato lido pelas ações do Mark LIII) em dia."""
    try:
        from pathlib import Path
        raiz = Path(__file__).resolve().parent.parent  # raiz do projeto
        arquivo = raiz / "config" / "api_keys.json"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        dados = {}
        if arquivo.exists():
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"))
            except Exception:
                dados = {}
        if not isinstance(dados, dict):
            dados = {}
        if cfg.get("gemini_api_key"):
            dados["gemini_api_key"] = cfg["gemini_api_key"].strip()
        arquivo.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    except Exception:
        pass
