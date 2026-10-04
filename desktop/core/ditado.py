"""Ditado por voz (v4.14.0) — Whisper local, transcreve a fala do senhor.

Regra de projeto: dependência essencial de UX NUNCA é opcional silenciosa.
Na primeira vez que o 🎙 for usado, o faster-whisper é AUTO-INSTALADO e o
modelo pequeno baixado; se algo falhar, o motivo exato aparece na cara
(messagebox), nunca só um status discreto no rodapé.
"""
import subprocess
import sys
import wave
from pathlib import Path

from .config import CONFIG_DIR

MODELO_DIR = CONFIG_DIR / "whisper"
TAMANHOS_VALIDOS = ("tiny", "base", "small", "medium")
TAMANHO_PADRAO = "base"   # bom equilíbrio pt-BR x velocidade em CPU


# ---------- dependência (auto-instala com aviso honesto) ----------

def _lib_ok() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("faster_whisper") is not None
    except Exception:
        return False


def instalar() -> tuple[bool, str]:
    """pip install faster-whisper — chamado na 1ª tentativa de ditado."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "faster_whisper"],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return False, f"pip falhou: {(r.stderr or r.stdout).strip()[:180]}"
        return True, "faster-whisper instalado"
    except Exception as e:
        return False, f"não consegui rodar o pip: {e}"


def garantir() -> tuple[bool, str]:
    """Garante a lib; devolve (ok, motivo) pro chamador mostrar na cara."""
    if _lib_ok():
        return True, "ok"
    ok, msg = instalar()
    return ok, msg


# ---------- modelo ----------

def modelo_instalado(tamanho: str = TAMANHO_PADRAO) -> bool:
    """O faster-whisper baixa o modelo na 1ª transcrição; ele baixa pro
    MODELO_DIR e guardamos essa marca pra avisar no botão."""
    try:
        if not MODELO_DIR.exists():
            return False
        return any(MODELO_DIR.rglob("model.bin"))
    except Exception:
        return False


def _abrir_modelo(tamanho: str):
    from faster_whisper import WhisperModel
    MODELO_DIR.mkdir(parents=True, exist_ok=True)
    return WhisperModel(tamanho, device="cpu", compute_type="int8",
                        download_root=str(MODELO_DIR))


# ---------- gravação ----------

class Gravador:
    """Grava o microfone até parar() — 16 kHz mono int16 (formato do Whisper)."""

    def __init__(self):
        import sounddevice as sd
        self._sd = sd
        self._frames: list[bytes] = []
        self._stream = None

    def iniciar(self) -> None:
        self._frames = []

        def callback(indata, frames, tempo, status):
            self._frames.append(bytes(indata))

        self._stream = self._sd.RawInputStream(
            samplerate=16000, channels=1, dtype="int16", callback=callback)
        self._stream.start()

    def parar(self, destino: Path) -> Path:
        """Fecha a stream e salva o WAV no destino."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        destino.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(destino), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"".join(self._frames))
        return destino

    def duracao(self) -> float:
        return len(b"".join(self._frames)) / (2 * 16000)


def transcrever(arquivo_wav: str, tamanho: str = TAMANHO_PADRAO) -> str:
    """Roda o Whisper local no WAV e devolve o texto minúsculo."""
    ok, msg = garantir()
    if not ok:
        raise RuntimeError(msg)
    if tamanho not in TAMANHOS_VALIDOS:
        tamanho = TAMANHO_PADRAO
    modelo = _abrir_modelo(tamanho)
    segmentos, _info = modelo.transcribe(arquivo_wav, language="pt", beam_size=1)
    texto = " ".join(s.text.strip() for s in segmentos).strip()
    return texto


def ditado_rapido(tamanho: str = TAMANHO_PADRAO, segundos: float = 8.0) -> str:
    """Grava `segundos` de fala e transcreve (bloqueante) — usado em
    testes e chamadas pontuais; a interface usa o Gravador com toggle."""
    import time as _t
    g = Gravador()
    g.iniciar()
    _t.sleep(segundos)
    destino = CONFIG_DIR / "ditado.wav"
    g.parar(destino)
    if g.duracao() < 0.3:
        return ""
    return transcrever(str(destino), tamanho)
