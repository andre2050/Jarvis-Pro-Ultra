"""Voz do JARVIS (TTS) — pyttsx3 offline com fallback NATIVO do Windows.

Cadeia de motores (v4.10.6 — "o JARVIS nunca fica mudo"):
  Windows:
    1. PowerShell + System.Speech — TTS NATIVO do Windows (PRINCIPAL; é o
       motor que provou funcionar na máquina do André, linha 5.1.9)
    2. pyttsx3 (reserva — desligue "voz nativa" no CONFIG pra usá-lo)
  Linux/Mac:
    1. pyttsx3 (vozes do sistema, config de velocidade/voz escolhida)

Se o pyttsx3 não estiver instalado ou o driver engasgar (caso comum em
builds .exe ou Windows sem pywin32), cada fala cai pro fallback nativo
automaticamente. Em último caso, a UI avisa o motivo exato.

v4.10.4: CORRIGIDO o bug "fala uma vez e para" — pyttsx3 reutilizando o
MESMO objeto engine pra várias falas é um bug conhecido do driver SAPI5 no
Windows (e do espeak no Linux): depois do primeiro runAndWait() o laço
interno do driver não reinicia e as falas seguintes saem mudas, sem
exceção nenhuma (então o código antigo nunca caía no fallback). Fix: cria
um engine NOVO pra cada fala e descarta no fim (engine.stop() + del) —
é o workaround oficial do próprio mantenedor do pyttsx3 pra esse bug.
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
        self.on_palavra = None   # v4.10.3-desktop: visemas — pulso a cada palavra falada
        self.config = config
        self.enabled = bool(config.get("voz_ativa", True))
        self._fila: queue.Queue = queue.Queue()
        # v5.1.7: fim do silêncio — a UI sempre sabe POR QUE não fala
        # status: "ok" | "sem_biblioteca" | "erro_engine" | "iniciando"
        self._status = "iniciando"
        self._erro = ""
        self._ps_ok = None       # cache da sonda do TTS nativo do Windows
        self.vozes = []          # v5.1.8: vozes do sistema (preenchido pelo engine)
        self._motor = ""         # "" | "nativo" | "pyttsx3" — quem falou por último
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._fila.put("__sondar__")  # v4.10.6: sonda roda NA THREAD da voz

    def reconfigurar(self) -> None:
        """Reaplica a config no engine em uso (voz escolhida, velocidade) —
        atravessa a fila pra não mexer no engine fora da thread dele."""
        self._fila.put("__reconfigurar__")

    def estado(self) -> tuple:
        """(pode_falar, motivo) — diagnóstico honesto pra UI avisar o usuário."""
        if self._motor == "nativo" and self._ps_ok:
            return True, "voz nativa do Windows"
        if self._motor == "pyttsx3" and self._status == "ok":
            return True, "ok"
        # nada falou ainda nesta sessão: vê o que estaria disponível agora
        if sys.platform.startswith("win"):
            if self._ps_ok is None:
                self._ps_ok = _powershell_disponivel()
            if self._ps_ok:
                return True, "voz nativa do Windows"
        if self._status == "ok":
            return True, "ok"
        if self._status == "iniciando" and not TEM_PYTTSX3 and not self._ps_ok:
            self._status = "sem_biblioteca"
        if self._status == "iniciando":
            return False, "motor de voz ainda inicializando…"
        motivo_py = ("pyttsx3 não instalado" if self._status == "sem_biblioteca"
                     else f"pyttsx3 falhou: {self._erro[:120]}")
        if self._ps_ok is None:
            self._ps_ok = _powershell_disponivel()
        if self._ps_ok:
            return True, f"voz nativa do Windows ({motivo_py})"
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

    def _sondar_vozes(self) -> None:
        """Pega o catálogo de vozes do sistema UMA vez pra UI (⚙ CONFIG),
        num engine descartável — não é o engine usado pra falar depois."""
        if not TEM_PYTTSX3:
            self._status = "sem_biblioteca"
            return
        try:
            sonda = pyttsx3.init()
            self._configurar(sonda)
            self._status, self._erro = "ok", ""
            try:
                sonda.stop()
            except Exception:
                pass
            del sonda
        except Exception as e:
            self._status, self._erro = "erro_engine", str(e)

    # ---------- motores ----------

    def _nativo_preferido(self) -> bool:
        """No Windows, a VOZ NATIVA (System.Speech) é o motor principal."""
        return (sys.platform.startswith("win")
                and bool(self.config.get("voz_natwin", True)))

    def _falar_nativo(self, texto: str) -> bool:
        """TTS nativo do Windows (System.Speech via PowerShell) — o motor que
        já provou funcionar na máquina do André (linha 5.1.9)."""
        if not sys.platform.startswith("win"):
            return False
        if self._ps_ok is None:
            self._ps_ok = _powershell_disponivel()
        if not self._ps_ok:
            return False
        self._visemas_estimadas(texto)  # nativo não tem eventos: pulsa por duração
        ok_ps, err_ps = _tts_powershell(
            texto,
            float(self.config.get("voz_velocidade", 0.85)),
            float(self.config.get("voz_volume", 1.0)))
        if getattr(self, "_fim_visemas", None):
            self._fim_visemas.set()
        if ok_ps:
            self._motor, self._ps_ok = "nativo", True
            return True
        self._ps_ok = False
        self._erro = err_ps[:120]
        return False

    def _falar_pyttsx3(self, texto: str) -> bool:
        """pyttsx3 com engine NOVO a cada fala (workaround da v4.10.4)."""
        if not TEM_PYTTSX3:
            self._status = "sem_biblioteca"
            return False
        engine = None
        try:
            engine = pyttsx3.init()
            self._configurar(engine)
            self._ligar_visemas(engine)
            engine.say(texto)
            engine.runAndWait()
            self._motor, self._status, self._erro = "pyttsx3", "ok", ""
            return True
        except Exception as e:
            self._status, self._erro = "erro_engine", str(e)
            return False
        finally:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass
                del engine

    def _loop(self) -> None:
        while True:
            texto = self._fila.get()
            if texto in ("__reconfigurar__", "__sondar__"):
                self._sondar_vozes()  # atualiza status/vozes; nada fica retido
                continue
            # v4.10.6: no Windows o pyttsx3 continuou mudo após a 1a fala mesmo com
            # engine novo por fala (v4.10.4) — a voz nativa assume o posto de
            # principal lá; pyttsx3 segue principal no Linux/Mac e reserva no Windows.
            falou = self._falar_nativo(texto) if self._nativo_preferido() else False
            if not falou:
                falou = self._falar_pyttsx3(texto)
            if not falou and not self._nativo_preferido():
                falou = self._falar_nativo(texto)  # última chance (Windows)

    def _ligar_visemas(self, engine) -> None:
        """pyttsx3 dispara 'word' a cada palavra — vira pulso na boca.
        v4.10.4: engine é novo a cada fala, então conecta sempre (sem guard)."""
        try:
            engine.connect("word", lambda nome, loc, tam: self._pulsa())
        except Exception:
            pass

    def _pulsa(self) -> None:
        try:
            if self.on_palavra:
                self.on_palavra()
        except Exception:
            pass

    def _visemas_estimadas(self, texto: str) -> None:
        """Motor nativo do Windows não tem eventos de palavra: pulsa a boca
        por uma thread de fundo pela duração estimada da fala."""
        import threading as _th
        fim = _th.Event()

        def pulsa():
            while not fim.wait(0.13):
                self._pulsa()
        _th.Thread(target=pulsa, daemon=True).start()
        self._fim_visemas = fim

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
