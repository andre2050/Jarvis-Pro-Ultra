"""v4.14.2 — Central de dependências do ⚙ CONFIG.

Lista o que está instalado/faltando (imports reais, não chute) e instala
os faltantes com pip na hora, mostrando o progresso na própria janela.
Regra de projeto: dependência essencial nunca é opcional silenciosa —
aqui o senhor VÊ o que falta e instala com um clique.
"""
import subprocess
import sys

# (chave, rótulo no painel, módulo importado, pacote pip, pra quê serve)
DEPS = [
    ("psutil", "Status do sistema (CPU/bateria)", "psutil", "psutil",
     "leituras vivas no holograma e modo econômico automático"),
    ("pillow", "Imagens (Pillow)", "PIL", "Pillow",
     "skins com arte, anexos de foto, captura de tela"),
    ("mss", "Captura de tela rápida", "mss", "mss",
     "ferramenta ver_tela"),
    ("requests", "Internet", "requests", "requests",
     "clima, busca web, atualizações"),
    ("whisper", "Ditado offline (Whisper)", "faster_whisper", "faster-whisper",
     "transcrição de voz 100% offline no 🎙"),
    ("vosk", "Wake word offline", "vosk", "vosk",
     "'Hey Jarvis' sem internet"),
    ("sounddevice", "Microfone bruto", "sounddevice", "sounddevice",
     "escuta do microfone para a wake word"),
    ("ddgs", "Busca no DuckDuckGo", "ddgs", "ddgs",
     "pesquisar na web e resumir"),
    ("send2trash", "Lixeira segura", "send2trash", "send2trash",
     "apagar arquivos sem risco permanente"),
    ("pyautogui", "Controle do PC", "pyautogui", "pyautogui",
     "mover mouse/digitar por comando"),
    ("playwright", "Navegador automático", "playwright", "playwright",
     "agente navegador_pro"),
    ("pypdf", "Ler PDFs", "pypdf", "pypdf",
     "ler_em_voz_alta de arquivos pdf"),
]


def _importavel(modulo: str) -> tuple[bool, str]:
    """Tenta importar de verdade — devolve (ok, motivo)."""
    try:
        __import__(modulo)
        return True, ""
    except ImportError as e:
        return False, f"não instalado ({e})"
    except Exception as e:  # DLL quebrada, versão errada etc
        return False, f"instalado mas quebrado ({e})"


def status() -> list[dict]:
    """[{chave, rotulo, pip, para, ok, motivo}] — na ordem de DEPS."""
    saida = []
    for chave, rotulo, modulo, pacote, para in DEPS:
        ok, motivo = _importavel(modulo)
        saida.append({"chave": chave, "rotulo": rotulo, "pip": pacote,
                      "para": para, "ok": ok, "motivo": motivo})
    return saida


def instalar(pacotes: list[str], log=print) -> bool:
    """pip install dos pacotes pedidos, linha a linha no log.
    Devolve True se TODOS instalaram."""
    if not pacotes:
        return True
    cmd = [sys.executable, "-m", "pip", "install", "--user", *pacotes]
    log(f"$ {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for linha in proc.stdout:          # mostra o pip ao vivo no painel
            log(linha.rstrip())
        proc.wait()
        if proc.returncode != 0:
            log(f"pip terminou com erro ({proc.returncode}) — tentando sem --user…")
            cmd = [sys.executable, "-m", "pip", "install", *pacotes]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            for linha in proc.stdout:
                log(linha.rstrip())
            proc.wait()
            if proc.returncode != 0:
                log("instalação falhou — veja as linhas acima, senhor.")
                return False
    except Exception as e:
        log(f"falhou ao rodar o pip: {e}")
        return False
    log("instalado, senhor — se não pegar de primeira, reinicie o app.")
    return True
