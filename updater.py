"""Verificação de atualização do JARVIS (leitura apenas).

Consulta o manifesto online (settings.json -> manifest_url) e compara
com a versão local (version.py). O manifesto DEVE ter assinatura Ed25519
válida (verificada com keys/ed25519_public.pem) — manifestos adulterados
são recusados. Se houver versão nova, o JARVIS avisa o usuário por voz;
a instalação em si é feita pelo launcher na próxima inicialização.

Quando manifest_url estiver vazio, a checagem é desativada.
"""
import base64
import json
import urllib.request
from pathlib import Path

from core.settings import SETTINGS
from version import __version__

PUBLIC_KEY_PATH = Path(__file__).parent / "keys" / "ed25519_public.pem"


def _version_tuple(v: str):
    return tuple(int(x) for x in v.split("."))


def _canonical_payload(manifest: dict) -> bytes:
    payload = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def verify_signature(manifest: dict) -> bool:
    """Exige assinatura Ed25519 válida — sem ela, o aviso não acontece."""
    sig_b64 = manifest.get("signature")
    if not sig_b64:
        print("[Updater] Manifesto sem assinatura — RECUSADO.")
        return False
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PATH.read_bytes())
        if not isinstance(public_key, Ed25519PublicKey):
            print("[Updater] Chave pública inválida — RECUSADO.")
            return False
        public_key.verify(base64.b64decode(sig_b64), _canonical_payload(manifest))
        return True
    except FileNotFoundError:
        print("[Updater] keys/ed25519_public.pem não encontrado — RECUSADO.")
        return False
    except Exception as e:
        print(f"[Updater] Assinatura inválida — RECUSADO ({e})")
        return False


def check_update():
    """Retorna o manifesto assinado se houver versão nova, senão None."""
    url = SETTINGS.get("manifest_url")
    if not url:
        return None

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            manifest = json.loads(resp.read().decode())

        if not verify_signature(manifest):
            return None

        if _version_tuple(manifest["latest_version"]) > _version_tuple(__version__):
            return manifest
    except Exception as e:
        print(f"[Updater] Checagem falhou (app continua normal): {e}")

    return None
