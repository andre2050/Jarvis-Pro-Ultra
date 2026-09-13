"""Escuta contínua do "Hey Jarvis" — a rede neural local (openwakeword/ONNX).

Fluxo: microfone em stream contínuo (sounddevice, 16 kHz) -> frames alimentam o
detector local (NADA sai da máquina) -> ao detectar "Hey Jarvis", o app pausa o
stream, escuta o comando pelo STT e retoma. Se openwakeword/sounddevice não
estiverem instalados, o recurso simplesmente fica desligado — nada quebra.
"""
import threading

from core import wake_word

try:
    import sounddevice as sd
    TEM_SOUNDDEVICE = True
except ImportError:
    TEM_SOUNDDEVICE = False


class WakeListener:
    def __init__(self, on_wake, logger=print):
        self.on_wake = on_wake
        self.logger = logger
        self.detector = None
        self.stream = None
        self.ativo = False
        self._trava = threading.Lock()

    # ---------- estado ----------

    @property
    def disponivel(self) -> bool:
        """Instalado e pronto pra ligar (pacotes + modelo baixado)."""
        return TEM_SOUNDDEVICE and wake_word.is_ready()

    @property
    def ligado(self) -> bool:
        return self.ativo

    # ---------- ciclo de vida ----------

    def iniciar(self) -> bool:
        """Liga o stream de microfone e a detecção. Retorna True se ligou."""
        with self._trava:
            if self.ativo or not self.disponivel:
                return False
            self.detector = wake_word.WakeWordDetector(on_detect=self._detectou, logger=self.logger)
            if not self.detector.start():
                self.detector = None
                return False
            try:
                self.stream = sd.InputStream(
                    samplerate=wake_word.SAMPLE_RATE, channels=1,
                    dtype="int16", blocksize=1280, callback=self._callback,
                )
                self.stream.start()
            except Exception as e:
                self.logger(f"Wake: não abriu o microfone — {e}")
                self.detector.stop()
                self.detector = None
                return False
            self.ativo = True
            self.logger("Wake: 'Hey Jarvis' em escuta local (offline).")
            return True

    def parar(self) -> None:
        with self._trava:
            self.ativo = False
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            if self.detector:
                try:
                    self.detector.stop()
                except Exception:
                    pass
                self.detector = None
            self.logger("Wake: desligado.")

    def pausar(self) -> None:
        """Solta o microfone (o STT vai usar) sem desligar o detector."""
        if self.stream and self.ativo:
            try:
                self.stream.stop()
            except Exception:
                pass

    def retomar(self) -> None:
        if self.stream and self.ativo:
            try:
                self.stream.start()
            except Exception:
                pass

    # ---------- internals ----------

    def _callback(self, indata, frames, time_info, status):
        """Roda na thread de áudio — só empurra o frame pro detector (nunca bloqueia)."""
        if self.detector:
            self.detector.feed(indata)

    def _detectou(self) -> None:
        """Chamado pela thread do detector quando ouve 'Hey Jarvis'."""
        try:
            self.on_wake()
        except Exception as e:
            self.logger(f"Wake: erro no callback — {e}")
