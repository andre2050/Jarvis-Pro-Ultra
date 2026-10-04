"""Backup e restauração (v4.14.0) — a vida do JARVIS em um arquivo.

Exporta/importa memórias, agenda, config e briefing num .zip — pra
trocar de PC ou guardar uma cópia sem perder nada.
"""
import zipfile
from pathlib import Path

from .config import CONFIG_DIR

ARQUIVOS = ["memory.json", "agenda.json", "config.json", "briefing.json"]


def exportar(caminho: str) -> str:
    """Cria um zip com tudo que importa em ~/.jarvis_pro_ultra."""
    alvo = Path(caminho)
    if alvo.suffix.lower() != ".zip":
        alvo = alvo.with_suffix(".zip")
    achados = [f for f in ARQUIVOS if (CONFIG_DIR / f).exists()]
    if not achados:
        return "nada pra exportar, senhor — o senhor ainda não tem memórias nem configurações."
    alvo.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in achados:
            z.write(CONFIG_DIR / nome, nome)
    return (f"Backup criado, senhor: {alvo} "
            f"({len(achados)} arquivo(s): {', '.join(achados)}).")


def importar(caminho: str) -> str:
    """Restaura um backup criado por exportar()."""
    origem = Path(caminho)
    if not origem.exists():
        return f"não achei o arquivo '{caminho}', senhor."
    try:
        with zipfile.ZipFile(origem) as z:
            nomes = [n for n in z.namelist() if n in ARQUIVOS]
            if not nomes:
                return "esse zip não é um backup do JARVIS, senhor."
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            for nome in nomes:
                z.extract(nome, CONFIG_DIR)
        return (f"Backup restaurado, senhor: {', '.join(nomes)}. "
                "Reabra o app pra tudo entrar em vigor.")
    except zipfile.BadZipFile:
        return "esse arquivo está corrompido ou não é um zip, senhor."
