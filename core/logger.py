"""Logging central do JARVIS.

Saída dupla: console (para você acompanhar) + arquivo rotativo
logs/jarvis.log (essencial para diagnosticar problemas nas máquinas
de outros usuários depois que o JARVIS for distribuído).
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(base_dir) -> logging.Logger:
    logs_dir = Path(base_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger("jarvis")
    log.setLevel(logging.INFO)

    if not log.handlers:  # evita duplicar handlers em reinicializações
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        fh = RotatingFileHandler(
            logs_dir / "jarvis.log",
            maxBytes=1_000_000,  # 1 MB
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        log.addHandler(fh)

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        log.addHandler(sh)

    return log
