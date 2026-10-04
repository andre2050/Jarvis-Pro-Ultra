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
    "tema": "sentinela",      # "sentinela" (padrão v4.14.1) | "novoskin" | "busto" | "radar" | "classico" | "vermelho" | "gold"
    "voz_id": "",              # v5.1.8: voz escolhida em ⚙ CONFIG ("" = automática)
    "voz_natwin": True,        # v4.10.6: Windows prefere TTS nativo (mais confiável)
    # v4.14.2: gerenciador de plugins — tools desligadas à mão em ⚙ CONFIG
    "tools_desligadas": [],
    # v4.14.2: atalho do botão de voz (padrão F4) customizável em ⚙ CONFIG
    "atalho_voz": "<F4>",
    # v4.14.2: modo econômico automático quando a bateria cai do nível
    "economia_auto": False,
    "economia_bateria": 40,    # % de bateria pra ligar sozinho
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    existia = False
    try:
        if CONFIG_FILE.exists():
            existia = True
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    # v4.10.4: André pediu a skin "novoskin" (foto de referência) no lugar da
    # "busto" que virou padrão sozinha na v4.10.3 — quem só tinha esse valor
    # AUTOMÁTICO (nunca escolheu de propósito em ⚙ CONFIG) migra uma vez só.
    # Depois da migração, qualquer escolha feita em CONFIG (inclusive voltar
    # pra "busto") fica intocada pra sempre.
    if existia and not cfg.get("_skin_migrada_v4104") and cfg.get("tema") == "busto":
        cfg["tema"] = "novoskin"
    cfg["_skin_migrada_v4104"] = True
    # v4.14.1: André pediu a interface circular do robô com fones vermelhos
    # (foto de referência) — skin "sentinela" vira padrão. Mesma regra da
    # v4.10.5: só migra quem nunca escolheu tema de propósito (estava no
    # padrão automático "novoskin"); escolha manual fica intocada pra sempre.
    if existia and not cfg.get("_skin_migrada_v4141") and cfg.get("tema") == "novoskin":
        cfg["tema"] = "sentinela"
    cfg["_skin_migrada_v4141"] = True
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
