"""Voz do JARVIS (TTS) — pyttsx3 offline, com fila dedicada.

Se a biblioteca não estiver instalada, o JARVIS simplesmente fala por
escrito (degradação elegante, sem quebrar nada).
"""
import queue
import threading

try:
    import pyttsx3
    TEM_PYTTSX3 = True
except ImportError:
    TEM_PYTTSX3 = False


class Voz:
    def __init__(self, config: dict):
        self.config = config
        self.enabled = bool(config.get("voz_ativa", True))
        self._fila: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ---------- API ----------

    def falar(self, texto: str) -> None:
        """Fala um texto (limpando markdown simples antes)."""
        if not self.enabled or not TEM_PYTTSX3:
            return
        limpo = texto.replace("**", "").replace("##", "").replace("`", "").strip()
        if limpo:
            self._fila.put(limpo)

    def alternar(self) -> bool:
        self.enabled = not self.enabled
        self.config["voz_ativa"] = self.enabled
        return self.enabled

    @property
    def instalada(self) -> bool:
        return TEM_PYTTSX3

    # ---------- engine ----------

    def _loop(self) -> None:
        if not TEM_PYTTSX3:
            return
        engine = None
        try:
            engine = pyttsx3.init()
            self._configurar(engine)
        except Exception:
            engine = None
        while True:
            texto = self._fila.get()
            if engine is None:
                continue
            try:
                engine.say(texto)
                engine.runAndWait()
            except Exception:
                try:
                    engine = pyttsx3.init()
                    self._configurar(engine)
                except Exception:
                    engine = None

    def _configurar(self, engine) -> None:
        try:
            rate = int(engine.getProperty("rate"))
            fator = float(self.config.get("voz_velocidade", 0.85))
            engine.setProperty("rate", int(rate * fator))
            engine.setProperty("volume", float(self.config.get("voz_volume", 1.0)))
            # prefere voz masculina pt-BR/en-GB quando houver
            preferidas = []
            for v in engine.getProperty("voices"):
                nome = (v.name or "").lower()
                idioma = (getattr(v, "id", "") or "").lower() + " " + (v.name or "").lower()
                if "pt" in idioma and ("male" in nome or "daniel" in nome or "felipe" in nome or "ricardo" in nome):
                    preferidas.insert(0, v)
                elif "en-gb" in idioma or "daniel" in nome or "george" in nome:
                    preferidas.append(v)
            if preferidas:
                engine.setProperty("voice", preferidas[0].id)
        except Exception:
            pass
