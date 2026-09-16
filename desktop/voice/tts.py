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
        # v5.1.7: fim do silêncio — a UI sempre sabe POR QUE não fala
        # status: "ok" | "sem_biblioteca" | "erro_engine" | "iniciando"
        self._status = "iniciando"
        self._erro = ""
        self.vozes = []          # v5.1.8: vozes do sistema (preenchido pelo engine)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def reconfigurar(self) -> None:
        """Reaplica a config no engine em uso (voz escolhida, velocidade) —
        atravessa a fila pra não mexer no engine fora da thread dele."""
        self._fila.put("__reconfigurar__")

    def estado(self) -> tuple:
        """(pode_falar, motivo) — diagnóstico honesto pra UI avisar o usuário."""
        if not TEM_PYTTSX3:
            return False, ("pyttsx3 não está instalado (pip install pyttsx3) "
                           "— dá pra instalar em 1 clique aqui nas configurações")
        if self._status == "erro_engine":
            return False, f"motor de voz falhou ao iniciar: {self._erro[:140]}"
        if self._status == "iniciando":
            return False, "motor de voz ainda inicializando…"
        return True, "ok"

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
            self._status = "sem_biblioteca"
            return
        engine = None
        try:
            engine = pyttsx3.init()
            self._configurar(engine)
            self._status, self._erro = "ok", ""
        except Exception as e:
            engine = None
            self._status, self._erro = "erro_engine", str(e)
        while True:
            texto = self._fila.get()
            if engine is None:
                # v5.1.7: tenta reerguer o motor a cada fala perdida (antes:
                # descartava em silêncio pra sempre depois da 1ª falha)
                try:
                    engine = pyttsx3.init()
                    self._configurar(engine)
                    self._status, self._erro = "ok", ""
                except Exception as e:
                    self._status, self._erro = "erro_engine", str(e)
                    continue
            if texto == "__reconfigurar__":
                self._configurar(engine)
                continue
            try:
                engine.say(texto)
                engine.runAndWait()
            except Exception as e:
                self._status, self._erro = "erro_engine", str(e)
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
            # v5.1.8: catálogo de vozes do sistema pra UI deixar o usuário escolher
            try:
                disponiveis = list(engine.getProperty("voices") or [])
                self.vozes = [{"id": getattr(v, "id", str(i)),
                               "nome": (v.name or f"voz {i+1}")}
                              for i, v in enumerate(disponiveis)]
            except Exception:
                disponiveis = []
                self.vozes = []
            # v5.1.8: voz escolhida pelo usuário tem prioridade total
            escolhida = (self.config.get("voz_id") or "").strip()
            if escolhida:
                for v in disponiveis:
                    if getattr(v, "id", "") == escolhida:
                        engine.setProperty("voice", escolhida)
                        return
            # sem escolha: prefere voz masculina pt-BR/en-GB quando houver
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
