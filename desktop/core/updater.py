"""Verificação de atualizações — consulta as releases do repo no GitHub."""
import requests

from version import __version__, GITHUB_REPO

API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
SUFIXO_EDICAO = "-desktop"   # v4.10.3-desktop: ignora releases Android/iOS do mesmo repo


def _parse(v: str) -> list[int]:
    nums = []
    for p in v.strip().lstrip("v").split("."):
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return nums


def check_latest() -> dict:
    """{'update': bool, 'latest': str, 'url': str, 'note': str}"""
    try:
        r = requests.get(API + "?per_page=30", timeout=10,
                         headers={"Accept": "application/vnd.github+json"})
        r.raise_for_status()
        releases = [d for d in r.json()
                    if str(d.get("tag_name", "")).endswith(SUFIXO_EDICAO)]
        if not releases:
            raise RuntimeError("nenhuma release desktop publicada ainda")
        data = releases[0]
        latest = data.get("tag_name", "").lstrip("v").replace(SUFIXO_EDICAO, "")
        tem_update = _parse(latest) > _parse(__version__)
        return {
            "update": tem_update,
            "latest": latest,
            "atual": __version__,
            "url": data.get("html_url", ""),
            "note": ("Nova versão disponível!" if tem_update else "Você já está na versão mais recente, senhor."),
        }
    except Exception as e:
        return {"update": False, "latest": "?", "atual": __version__,
                "url": "", "note": f"não consegui consultar o GitHub: {e}"}
