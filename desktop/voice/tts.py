"""Voz do JARVIS (TTS) — pyttsx3 offline com fallback NATIVO do Windows.

Cadeia de motores (v5.1.9 — "o JARVIS nunca fica mudo"):
  1. pyttsx3 (vozes do sistema, config de velocidade/voz escolhida)
  2. PowerShell + System.Speech — TTS NATIVO do Windows, funciona sem
     instalar NADA (é a mesma engine do Windows, chamada direta)

Se o pyttsx3 não estiver instalado ou o driver engasgar (caso comum em
builds .exe ou Windows sem pywin32), cada fala cai pro fallback nativo
automaticamente. Em último caso, a UI avisa o motivo exato.
"""
import queue
import subprocess
import sys
import threading

try:
    import pyttsx3
    TEM_PYTTSX3 = True
except ImportError:
    TEM_PYTTSX3 = False


def _tts_powershell(texto: str, velocidade: float = 0.85, volume: float = 1.0) -> tuple:
    """Fala usando o TTS NATIVO do Windows (System.Speech via PowerShell).

    Zero dependências Python — funciona mesmo se pyttsx3/pywin32 estiverem
    quebrados. Devolve (ok, erro).
    """
    if not sys.platform.startswith("win"):
        return False, "voz nativa só existe no Windows"
    try:
        rate = max(-10, min(10, int(round((velocidade - 1.0) * 10))))
        vol = max(0, min(100, int(volume * 100)))
        esc = (texto.replace("'", "''")
                    .replace("\r", " ").replace("\n", " "))[:800]
        cmd = ("Add-Type -AssemblyName System.Speech;"
               "$j = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
               f"$j.Rate = {rate}; $j.Volume = {vol};"
               f"$j.Speak('{esc}')")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", cmd],
            timeout=60, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=flags, check=False)
        return True, ""
    except Exception as e:
        return False, str(e)


def _powershell_disponivel() -> bool:
    """Sonda rápida: System.Speech responde nesse Windows? (cacheado por quem chama)"""
    if not sys.platform.startswith("win"):
        return False
    try:
        cmd = ("Add-Type -AssemblyName System.Speech;"
               "$j = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
               "$j.GetInstalledVoices().Count | Out-Null")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", cmd],
            timeout=25, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=flags, check=False)
        return r.returncode == 0
    except Exception:
        return False


class Voz:
    def __init__(self, config: dict):
        self.config = config
        self.enabled = bool(config.get("voz_ativa", True))
        self._fila: queue.Queue = queue.Queue()
        # v5.1.7: fim do silêncio — a UI sempre sabe POR QUE não fala
        # status: "ok" | "sem_biblioteca" | "erro_engine" | "iniciando"
        self._status = "iniciando"
        self._erro = ""
        self._ps_ok = None       # cache da sonda do TTS nativo do Windows
        self.vozes = []          # v5.1.8: vozes do sistema (preenchido pelo engine)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def reconfigurar(self) -> None:
        """Reaplica a config no engine em uso (voz escolhida, velocidade) —
        atravessa a fila pra não mexer no engine fora da thread dele."""
        self._fila.put("__reconfigurar__")

    def estado(self) -> tuple:
        """(pode_falar, motivo) — diagnóstico honesto pra UI avisar o usuário.

        v5.1.9: com o fallback nativo do Windows, pyttsx3 quebrado NÃO significa
        mudo — o motivo diz por qual motor ele está falando.
        """
        if self._status == "ok":
            return True, "ok"
        if self._status == "iniciando" and not TEM_PYTTSX3:
            self._status = "sem_biblioteca"
        if self._status == "iniciando":
            return False, "motor de voz ainda inicializando…"
        motivo_py = ("pyttsx3 não instalado" if self._status == "sem_biblioteca"
                     else f"pyttsx3 falhou: {self._erro[:120]}")
        if self._ps_ok is None:
            self._ps_ok = _powershell_disponivel()
        if self._ps_ok:
            return True, (f"falando pela VOZ NATIVA DO WINDOWS "
                          f"({motivo_py} — dá pra melhorar com o botão de instalar)")
        return False, f"nenhum motor de voz funciona ({motivo_py} | voz nativa indisponível)"

    # ---------- API ----------

    def falar(self, texto: str) -> None:
        """Fala um texto (limpando markdown simples antes).

        v5.1.9: NÃO bloqueia mais quando o pyttsx3 falta — o texto entra na
        fila de qualquer jeito e o _loop decide qual motor usa (pyttsx3 ou
        voz nativa do Windows). A guarda antiga `not TEM_PYTTSX3: return`
        descartava a fala ANTES do fallback — era mudo garantido.
        """
        if not self.enabled:
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
        engine = None
        if TEM_PYTTSX3:
            try:
                engine = pyttsx3.init()
                self._configurar(engine)
                self._status, self._erro = "ok", ""
            except Exception as e:
                engine = None
                self._status, self._erro = "erro_engine", str(e)
        while True:
            texto = self._fila.get()
            if texto == "__reconfigurar__":
                if engine is not None:
                    self._configurar(engine)
                continue
            # ---- motor 1: pyttsx3 ----
            falou = False
            if engine is None and TEM_PYTTSX3:
                # v5.1.7: tenta reerguer o motor a cada fala perdida
                try:
                    engine = pyttsx3.init()
                    self._configurar(engine)
                    self._status, self._erro = "ok", ""
                except Exception as e:
                    engine = None
                    self._status, self._erro = "erro_engine", str(e)
            if engine is not None:
                try:
                    engine.say(texto)
                    engine.runAndWait()
                    falou = True
                except Exception as e:
                    self._status, self._erro = "erro_engine", str(e)
                    try:
                        engine = pyttsx3.init()
                        self._configurar(engine)
                    except Exception:
                        engine = None
            # ---- motor 2: TTS NATIVO do Windows (fallback) ----
            if not falou:
                ok_ps, err_ps = _tts_powershell(
                    texto,
                    float(self.config.get("voz_velocidade", 0.85)),
                    float(self.config.get("voz_volume", 1.0)))
                if ok_ps:
                    self._ps_ok = True
                    if self._status != "ok":
                        self._status = self._status or "sem_biblioteca"
                else:
                    self._ps_ok = False
                    self._status = "sem_voz"
                    self._erro = (f"pyttsx3: {self._erro[:80]} | "
                                  f"nativo: {err_ps[:80]}")

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
