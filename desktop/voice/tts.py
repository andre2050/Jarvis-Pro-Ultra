"""Voz do JARVIS (TTS) — cadeia de motores, "o JARVIS nunca fica mudo".

Cadeia de motores (v4.10.8):
  Windows:
    1. TTS NATIVO do Windows (System.Speech) num processo PowerShell
       PERSISTENTE pré-aquecido — fala sem a pausa de ~1s de carregar o
       powershell a cada frase. O texto vai por stdin em BASE64 (imune a
       problemas de acentuação/codificação) e o processo só responde 'ok'
       DEPOIS de terminar de falar (backpressure natural: a próxima fala
       espera a atual acabar).
       Se o processo cair ou engasgar, a fala cai na hora pro modo one-shot
       (powershell novo por fala — o motor que provou funcionar na máquina
       do André, linha 5.1.9) e o persistente renasce na próxima fala.
    2. pyttsx3 (reserva — desligue "voz nativa" no ⚙ CONFIG pra usá-lo)
  Linux/Mac:
    1. pyttsx3 (vozes do sistema, config de velocidade/voz escolhida)

v4.10.8 — correções da auditoria do código de áudio:
  - estado() NÃO sonda mais nada na thread da UI (podia congelar o app
    1-2s na 1ª chamada); toda sonda do nativo roda na thread da voz.
  - a voz escolhida no ⚙ CONFIG (seletor de vozes) agora vale TAMBÉM no
    motor nativo (SelectVoice pelo nome da voz).
  - textos longos: FATIADOS por frase (não truncados em 800 caracteres).
  - timeout da fala escala com o tamanho do texto (não é mais 60s fixo) e
    uma falha pontual NÃO desativa o nativo pela sessão inteira.
  - one-shot confere o returncode do PowerShell (erro não é mais
    reportado como sucesso).

Histórico: v4.10.4 corrigiu o bug "fala uma vez e para" do pyttsx3
(engine novo a cada fala); v4.10.6 promoveu a voz nativa a principal no
Windows e moveu TODOS os objetos COM pra uma thread só (a da fila de
fala) — sonda incluída.
"""
import base64
import queue
import re
import subprocess
import sys
import threading
import time

try:
    import pyttsx3
    TEM_PYTTSX3 = True
except ImportError:
    TEM_PYTTSX3 = False

# ---- processo PowerShell persistente -------------------------------------
# Protocolo por stdin (tudo em ASCII puro — o texto vem em base64):
#   "C <rate>,<vol>"      ajusta velocidade/volume
#   "V <b64 nome voz>"    seleciona a voz (SelectVoice)
#   "S <b64 texto>"       fala o texto (Speak — bloqueia até terminar)
#   "P"                  responde "ok" no stdout DEPOIS de tudo que veio antes
_PS_SCRIPT = (
    "Add-Type -AssemblyName System.Speech;"
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "while($true){"
    "$l = [Console]::In.ReadLine();"
    "if($l -eq $null){ break }"
    "if($l -eq 'P'){ [Console]::Out.WriteLine('ok'); [Console]::Out.Flush(); continue }"
    "if($l.StartsWith('V ')){ try{ $s.SelectVoice([System.Text.Encoding]::UTF8.GetString("
    "[System.Convert]::FromBase64String($l.Substring(2)))) }catch{}; continue }"
    "if($l.StartsWith('C ')){ $p = $l.Substring(2).Split(','); "
    "try{ $s.Rate = [int]$p[0]; $s.Volume = [int]$p[1] }catch{}; continue }"
    "if($l.StartsWith('S ')){ try{ $s.Speak([System.Text.Encoding]::UTF8.GetString("
    "[System.Convert]::FromBase64String($l.Substring(2)))) }catch{} }"
    "}"
)
_PS_CMD = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-Command", _PS_SCRIPT]
_PS_ESPERA_MIN = 10.0   # folga mínima (s) esperando o 'ok' — processo engasgado cai pro one-shot


def _duracao_estimada(texto: str, velocidade: float) -> float:
    """Segundos que o texto deve levar pra ser falado (pra dimensionar timeouts)."""
    palavras = max(1, len(texto.split()))
    return palavras * 0.42 / max(0.5, velocidade or 1.0)


def _fatiar(texto: str, tamanho: int = 750) -> list:
    """Corta o texto em pedaços no máximo `tamanho` chars, preferindo
    fronteiras de frase — v4.10.8: texto longo é FATIADO, não truncado."""
    partes, atual = [], ""
    for frase in re.split(r"(?<=[.!?])\s+", texto.strip()):
        while len(frase) > tamanho:
            if atual:
                partes.append(atual)
                atual = ""
            partes.append(frase[:tamanho])
            frase = frase[tamanho:]
        if not atual:
            atual = frase
        elif len(atual) + len(frase) + 1 <= tamanho:
            atual = atual + " " + frase
        else:
            partes.append(atual)
            atual = frase
    if atual:
        partes.append(atual)
    return partes or [texto.strip()]


def _tts_powershell(texto: str, velocidade: float = 0.85,
                   volume: float = 1.0, voz_nome: str = "") -> tuple:
    """Fala usando o TTS NATIVO do Windows (System.Speech via PowerShell),
    num processo descartável (one-shot) — o caminho comprovado, usado como
    reserva se o processo persistente cair. Devolve (ok, erro)."""
    if not sys.platform.startswith("win"):
        return False, "voz nativa só existe no Windows"
    try:
        rate = max(-10, min(10, int(round((velocidade - 1.0) * 10))))
        vol = max(0, min(100, int(volume * 100)))
        esc = (texto.replace("'", "''")
                    .replace("\r", " ").replace("\n", " "))[:800]
        cmd = ("Add-Type -AssemblyName System.Speech;"
               "$j = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
               f"$j.Rate = {rate}; $j.Volume = {vol};")
        if voz_nome:
            b64 = base64.b64encode(voz_nome.encode("utf-8")).decode("ascii")
            cmd += (f"try{{ $j.SelectVoice([System.Text.Encoding]::UTF8.GetString("
                    f"[System.Convert]::FromBase64String('{b64}'))) }}catch{{}};")
        cmd += f"$j.Speak('{esc}')"
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        timeout = max(30.0, _duracao_estimada(esc, velocidade) + 15.0)
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", cmd],
            timeout=timeout, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            creationflags=flags, check=False)
        if r.returncode != 0:  # v4.10.8: erro de verdade não é mais "sucesso"
            detalhe = (r.stderr or b"").decode("utf-8", "replace")[:80]
            return False, f"powershell terminou com código {r.returncode} {detalhe}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "timeout da fala nativa"
    except Exception as e:
        return False, str(e)


def _powershell_disponivel() -> bool:
    """Sonda rápida: System.Speech responde nesse Windows?
    (Só chamada pela THREAD DA VOZ — nunca pela UI.)"""
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
        self.vozes = []           # v5.1.8: vozes do sistema (preenchido pelo engine)
        self._motor = ""          # "" | "nativo" | "pyttsx3" — quem falou por último
        # v4.10.8: processo PowerShell persistente (pré-aquecido)
        self._ps_p = None
        self._ps_q = None
        self._ps_cfg_sent = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._fila.put("__sondar__")  # v4.10.6: sonda roda NA THREAD da voz

    def reconfigurar(self) -> None:
        """Reaplica a config no engine em uso (voz escolhida, velocidade) —
        atravessa a fila pra não mexer no engine fora da thread dele."""
        self._fila.put("__reconfigurar__")

    def estado(self) -> tuple:
        """(pode_falar, motivo) — diagnóstico honesto pra UI avisar o usuário.

        v4.10.8: NÃO sonda mais nada aqui (a sonda podia congelar a thread da
        UI por 1-2s). Só lê o que a thread da voz já descobriu; enquanto a
        sonda do boot não termina, devolve motivo "verificando" e a UI
        re-checa em vez de acusar problema falso."""
        if self._motor == "nativo" and self._ps_ok:
            return True, "voz nativa do Windows"
        if self._motor == "pyttsx3" and self._status == "ok":
            return True, "ok"
        if sys.platform.startswith("win"):
            if self._ps_ok is None:
                return True, "verificando"      # sonda do boot ainda correndo
            if self._ps_ok:
                return True, "voz nativa do Windows"
        if self._status == "ok":
            return True, "ok"
        if self._status == "iniciando":
            return False, "motor de voz ainda inicializando…"
        motivo_py = ("pyttsx3 não instalado" if self._status == "sem_biblioteca"
                     else f"pyttsx3 falhou: {self._erro[:120]}")
        return False, f"nenhum motor de voz funciona ({motivo_py} | voz nativa indisponível)"

    # ---------- API ----------

    def falar(self, texto: str) -> None:
        """Fala um texto (limpando markdown simples antes). Não bloqueia:
        o texto entra na fila e o _loop decide qual motor usa."""
        if not self.enabled:
            return
        limpo = texto.replace("**", "").replace("##", "").replace("`", "").strip()
        if limpo:
            self._fila.put(limpo)

    def alternar(self) -> bool:
        self.enabled = not self.enabled
        self.config["voz_ativa"] = self.enabled
        if not self.enabled:
            self._matar_ps()   # v4.10.8: voz OFF não deixa powershell parado
        return self.enabled

    @property
    def instalada(self) -> bool:
        return TEM_PYTTSX3

    # ---------- sondas ----------

    def _sondar_vozes(self) -> None:
        """Catálogo de vozes do sistema pra UI (⚙ CONFIG) + sonda do TTS
        nativo + pré-aquecimento do processo persistente. Roda sempre NA
        THREAD DA VOZ (v4.10.6: COM numa thread só; v4.10.8: UI nunca sonda)."""
        if TEM_PYTTSX3:
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
        else:
            self._status = "sem_biblioteca"
        if sys.platform.startswith("win"):
            self._ps_ok = _powershell_disponivel()
            if self._ps_ok and self.enabled:
                self._ps_proc()   # pré-aquece: a 1ª fala sai sem pausa de carga

    def _nome_voz_escolhida(self) -> str:
        """v4.10.8: voz escolhida no ⚙ CONFIG, traduzida pro NOME que o
        System.Speech entende (o seletor guarda o id do pyttsx3)."""
        escolhida = (self.config.get("voz_id") or "").strip()
        if not escolhida:
            return ""
        for v in (self.vozes or []):
            if v.get("id") == escolhida:
                return v.get("nome") or ""
        return ""

    # ---------- motor nativo (Windows) ----------

    def _ps_proc(self):
        """O processo PowerShell PERSISTENTE (nasce 1x, fala muitas vezes).
        Caiu? _matar_ps + a próxima fala renasce ele."""
        if self._ps_p is not None and self._ps_p.poll() is None:
            return self._ps_p
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self._ps_p = subprocess.Popen(
                _PS_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, creationflags=flags)
            self._ps_q = queue.Queue()

            def _le(out, destino):
                try:
                    for linha in iter(out.readline, b""):
                        destino.put(linha)
                except Exception:
                    pass
                destino.put(None)   # EOF — o processo morreu

            threading.Thread(target=_le, args=(self._ps_p.stdout, self._ps_q),
                             daemon=True).start()
            return self._ps_p
        except Exception:
            self._ps_p = None
            return None

    def _matar_ps(self) -> None:
        p, self._ps_p = self._ps_p, None
        self._ps_q = None
        self._ps_cfg_sent = None
        if p is not None:
            try:
                p.kill()
            except Exception:
                pass
            for canal in (p.stdin, p.stdout):
                try:
                    if canal:
                        canal.close()
                except Exception:
                    pass

    def _nativo_persistente(self, texto: str) -> bool:
        """Fala pelo processo persistente. Devolve False (e derruba o
        processo) se ele morrer ou engolir o 'ok' — quem chama cai pro
        one-shot na hora."""
        p = self._ps_proc()
        if p is None:
            return False
        vel = float(self.config.get("voz_velocidade", 0.85))
        vol = float(self.config.get("voz_volume", 1.0))
        rate = max(-10, min(10, int(round((vel - 1.0) * 10))))
        vpc = max(0, min(100, int(vol * 100)))
        nome = self._nome_voz_escolhida()
        cfg = (rate, vpc, nome)
        try:
            if cfg != self._ps_cfg_sent:   # config mudou? reaplica no processo
                p.stdin.write(("C %d,%d\n" % (rate, vpc)).encode("ascii"))
                p.stdin.write(("V %s\n" % base64.b64encode(
                    nome.encode("utf-8")).decode("ascii")).encode("ascii"))
                p.stdin.flush()
                self._ps_cfg_sent = cfg
            for pedaco in _fatiar(texto):  # sem limite de tamanho (vai por stdin)
                p.stdin.write(("S %s\n" % base64.b64encode(
                    pedaco.encode("utf-8")).decode("ascii")).encode("ascii"))
            p.stdin.write(b"P\n")
            p.stdin.flush()
            # espera o 'ok' — o PS só responde DEPOIS de terminar de falar
            limite = max(_PS_ESPERA_MIN, _duracao_estimada(texto, vel) * 1.5 + 6.0)
            t0 = time.monotonic()
            while time.monotonic() - t0 < limite:
                try:
                    item = self._ps_q.get(timeout=1.0)
                except queue.Empty:
                    continue
                if item is None:            # EOF: processo morreu
                    break
                if item.strip() == b"ok":
                    return True
            self._matar_ps()                # watchdog: o 'ok' sumiu
            return False
        except Exception:
            self._matar_ps()
            return False

    def _nativo_one_shot(self, texto: str) -> bool:
        """Reserva comprovada: powershell novo por fala, com a voz escolhida
        e texto fatiado (v4.10.8)."""
        vel = float(self.config.get("voz_velocidade", 0.85))
        vol = float(self.config.get("voz_volume", 1.0))
        nome = self._nome_voz_escolhida()
        for pedaco in _fatiar(texto, 800):
            ok, err = _tts_powershell(pedaco, vel, vol, nome)
            if not ok:
                self._erro = err[:120]
                return False
        return True

    def _falar_nativo(self, texto: str) -> bool:
        """TTS nativo do Windows — principal no Windows (voz_natwin)."""
        if not sys.platform.startswith("win"):
            return False
        if self._ps_ok is None:
            self._ps_ok = _powershell_disponivel()
            if self._ps_ok and self.enabled:
                self._ps_proc()
        if not self._ps_ok:
            return False
        self._visemas_estimadas(texto)  # nativo não tem eventos: pulsa por duração
        falou = self._nativo_persistente(texto)
        if not falou:
            falou = self._nativo_one_shot(texto)
        if getattr(self, "_fim_visemas", None):
            self._fim_visemas.set()
        if falou:
            self._motor, self._ps_ok = "nativo", True
            return True
        # v4.10.8: UMA fala que falhou não desliga o nativo da sessão —
        # re-sonda: se o TTS nativo responde, a próxima fala volta pra ele.
        self._ps_ok = _powershell_disponivel()
        return False

    # ---------- motor pyttsx3 ----------

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
                self._sondar_vozes()  # atualiza status/vozes/sonda nativa
                continue
            # v4.10.6: no Windows o pyttsx3 continuava mudo após a 1a fala mesmo com
            # engine novo por fala (v4.10.4) — a voz nativa assume o posto de
            # principal lá; pyttsx3 segue principal no Linux/Mac e reserva no Windows.
            falou = self._falar_nativo(texto) if self._nativo_preferido() else False
            if not falou:
                falou = self._falar_pyttsx3(texto)
            if not falou and not self._nativo_preferido():
                falou = self._falar_nativo(texto)  # última chance (Windows)

    def _nativo_preferido(self) -> bool:
        """No Windows, a VOZ NATIVA (System.Speech) é o motor principal."""
        return (sys.platform.startswith("win")
                and bool(self.config.get("voz_natwin", True)))

    # ---------- visemas ----------

    def _ligar_visemas(self, engine) -> None:
        """pyttsx3 dispara 'word' a cada palavra — vira pulso na boca."""
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
        por uma thread de fundo enquanto a fala dura."""
        import threading as _th
        fim = _th.Event()

        def pulsa():
            while not fim.wait(0.13):
                self._pulsa()
        _th.Thread(target=pulsa, daemon=True).start()
        self._fim_visemas = fim

    # ---------- config do engine pyttsx3 ----------

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
