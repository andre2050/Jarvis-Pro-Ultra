"""J.A.R.V.I.S — Pro Ultra Desktop (v4.3.0, Reator de Arco Vermelho)

Executa com:  python main.py
Requer:       pip install -r requirements.txt
"""
import queue
import tkinter as tk
from tkinter import font as tkfont

from core import brain, config, tools
from ui.reactor import ArcReactorHud, RED, RED_VIVO, RED_DIM, FUNDO
from ui.chat import ChatPanel
from ui.settings import PainelConfig
from voice.tts import Voz
from voice import stt
from version import APP_NAME, __version__

FUNDO_JANELA = "#080506"
FUNDO_PAINEL = "#0d0708"
TXT_FRACO = "#9c8a86"
TXT_CLARO = "#f2e6e4"


class JarvisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{__version__}")
        self.configure(bg=FUNDO_JANELA)
        self.geometry("1080x740")
        self.minsize(940, 640)

        self.cfg = config.load()
        self.voz = Voz(self.cfg)
        self.historico: list = []
        self.fila_eventos: queue.Queue = queue.Queue()
        self._ocupado = False

        # o timer das tools avisa por aqui
        tools.on_timer_fire = self._timer_disparou

        self._montar_layout()
        self._boas_vindas()
        self.protocol("WM_DELETE_WINDOW", self._sair)
        self.bind("<F4>", lambda e: self._alternar_voz())
        self.after(80, self._consumir_eventos)

    # ==================== LAYOUT ====================

    def _montar_layout(self):
        # ---- barra superior ----
        topo = tk.Frame(self, bg=FUNDO_PAINEL, height=54)
        topo.pack(fill=tk.X)
        topo.pack_propagate(False)
        tk.Label(topo, text="J.A.R.V.I.S — PRO ULTRA", font=("Consolas", 14, "bold"),
                 fg=RED_VIVO, bg=FUNDO_PAINEL).pack(side=tk.LEFT, padx=(18, 4))
        tk.Label(topo, text=f"DESKTOP v{__version__}", font=("Consolas", 9),
                 fg=TXT_FRACO, bg=FUNDO_PAINEL).pack(side=tk.LEFT, pady=(6, 0))

        # chip de status pulsante
        self.chip = tk.Canvas(topo, width=120, height=26, bg=FUNDO_PAINEL, highlightthickness=0)
        self.chip.pack(side=tk.RIGHT, padx=(4, 0))
        self._chip_texto = "PRONTO"

        self.btn_voz = tk.Button(topo, text="🎙 VOZ ON", command=self._alternar_voz,
                                 bg=FUNDO_PAINEL, fg=RED_VIVO, bd=0,
                                 font=("Consolas", 9, "bold"), cursor="hand2")
        self.btn_voz.pack(side=tk.RIGHT, padx=6)
        tk.Button(topo, text="⚙ CONFIG", command=self._abrir_config,
                  bg=FUNDO_PAINEL, fg=RED_VIVO, bd=0,
                  font=("Consolas", 9, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=6)
        self._pulsar_chip()

        # ---- corpo: reator (esq) + chat (dir) ----
        corpo = tk.Frame(self, bg=FUNDO_JANELA)
        corpo.pack(fill=tk.BOTH, expand=True)

        esquerda = tk.Frame(corpo, bg=FUNDO_PAINEL, width=460)
        esquerda.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 6), pady=10)
        esquerda.pack_propagate(False)
        self.reator = ArcReactorHud(esquerda, size=430)
        self.reator.pack(pady=(26, 6))

        # leituras vivas embaixo do reator
        self.lbl_leituras = tk.Label(esquerda, text="inicializando sensores…",
                                     font=("Consolas", 9), fg=RED_DIM, bg=FUNDO_PAINEL)
        self.lbl_leituras.pack(pady=(4, 12))
        tk.Label(esquerda, text="F4 alterna a voz  ·  senhor",
                 font=("Consolas", 8), fg=TXT_FRACO, bg=FUNDO_PAINEL).pack(pady=(0, 14))
        self.after(2000, self._atualizar_leituras)

        direita = tk.Frame(corpo, bg=FUNDO_PAINEL)
        direita.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        self.chat = ChatPanel(direita)
        self.chat.pack(fill=tk.BOTH, expand=True)

        # ---- barra de entrada em vidro translúcido ----
        barra = tk.Frame(direita, bg="#171012")
        barra.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.entrada = tk.Entry(barra, bg="#1d1214", fg=TXT_CLARO, bd=0,
                                insertbackground=RED_VIVO, font=("Segoe UI", 12))
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 8), pady=10, ipady=8)
        self.entrada.bind("<Return>", lambda e: self._enviar())

        if stt.DISPONIVEL:
            self.btn_mic = tk.Button(barra, text="🎙", command=self._ouvir,
                                     bg="#171012", fg=RED_VIVO, bd=0,
                                     font=("Segoe UI", 13), cursor="hand2")
            self.btn_mic.pack(side=tk.LEFT, padx=(0, 6), pady=6)
        tk.Button(barra, text="ENVIAR ➤", command=self._enviar, bg="#a1160f",
                  fg="#ffe4de", bd=0, font=("Consolas", 10, "bold"),
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 10), pady=8)

    # ==================== STATUS / HUD ====================

    def _pulsar_chip(self):
        import time
        cores = [RED_DIM, "#c4231a", RED, "#c4231a"]
        estagio = int(time.time() * 2) % len(cores)
        self.chip.delete("all")
        self.chip.create_oval(8, 9, 20, 21, fill=cores[estagio], outline="")
        self.chip.create_text(62, 15, text=self._chip_texto, fill=TXT_FRACO,
                              font=("Consolas", 9, "bold"))
        self.after(500, self._pulsar_chip)

    def _status(self, texto: str, pensando=False, ouvindo=False, falando=False):
        self._chip_texto = texto.upper()
        self.reator.thinking = pensando
        self.reator.listening = ouvindo
        self.reator.speaking = falando

    def _atualizar_leituras(self):
        from core import perception
        d = perception.leitura_viva()
        partes = []
        if d.get("cpu") is not None:
            partes.append(f"CPU {d['cpu']:.0f}%")
        if d.get("ram") is not None:
            partes.append(f"RAM {d['ram']:.0f}%")
        if d.get("bat") is not None:
            partes.append(f"BAT {d['bat']}%")
        self.lbl_leituras.config(text="  ·  ".join(partes) or "sensores indisponíveis (pip install psutil)")
        self.after(2000, self._atualizar_leituras)

    # ==================== CHAT ====================

    def _boas_vindas(self):
        self.chat.add("jarvis", "Sistemas online, senhor. Reator de arco operando a plena capacidade.")
        if not config.api_key_ok(self.cfg):
            self.chat.add("sistema", "Cole sua chave do Gemini em ⚙ CONFIG para me dar um cérebro — "
                                     "é grátis em aistudio.google.com")

    def _enviar(self, texto: str | None = None):
        msg = (texto or self.entrada.get()).strip()
        if not msg or self._ocupado:
            return
        if not config.api_key_ok(self.cfg):
            self._abrir_config()
            return
        self.entrada.delete(0, tk.END)
        self.chat.add("user", msg)
        self._ocupado = True
        self._status("pensando", pensando=True)
        self.chat.mostrar_digitando()

        def retorno(resultado):
            self.fila_eventos.put(resultado)

        brain.process_async(self.cfg["gemini_api_key"], self.historico, msg, retorno)

    def _ouvir(self):
        if self._ocupado:
            return
        self._status("ouvindo", ouvindo=True)

        def run():
            texto = stt.ouvir()
            self.fila_eventos.put(("voz", texto))
        import threading
        threading.Thread(target=run, daemon=True).start()

    # ==================== EVENTOS DA FILA ====================

    def _consumir_eventos(self):
        try:
            while True:
                item = self.fila_eventos.get_nowait()
                if isinstance(item, tuple) and item[0] == "timer":
                    motivo = item[1]
                    msg = (f"⏰ Timer finalizado, senhor — {motivo}." if motivo != "timer"
                           else "⏰ Timer finalizado, senhor.")
                    self.chat.add("jarvis", msg)
                    self.voz.falar(msg)
                elif isinstance(item, tuple) and item[0] == "voz":
                    _, texto = item
                    self._status("pronto")
                    if texto:
                        self.chat.add("sistema", f"🎙 ouvi: \"{texto}\"")
                        self._enviar(texto)
                    else:
                        self.chat.add("sistema", "não captei nada, senhor.")
                elif isinstance(item, Exception):
                    self._finalizar_turno(str(item), erro=True)
                else:  # TurnResult
                    self._finalizar_turno(item.reply)
        except queue.Empty:
            pass
        self.after(80, self._consumir_eventos)

    def _finalizar_turno(self, resposta: str, erro: bool = False):
        self.chat.esconder_digitando()
        if erro:
            self.chat.add("erro", resposta)
        else:
            self.chat.add("jarvis", resposta)
            self.voz.falar(resposta)
        self._ocupado = False
        self._status("pronto")

    def _timer_disparou(self, motivo: str):
        # chamado pela thread do timer -> atravessa a fila pra chegar na UI com segurança
        self.fila_eventos.put(("timer", motivo))

    # ==================== VOZ / CONFIG ====================

    def _alternar_voz(self):
        ligado = self.voz.alternar()
        config.save(self.cfg)
        self.btn_voz.config(text=f"🎙 VOZ {'ON' if ligado else 'OFF'}",
                            fg=RED_VIVO if ligado else TXT_FRACO)
        if not ligado:
            self.voz.falar("Voz desativada, senhor.")

    def _abrir_config(self):
        PainelConfig(self, self)

    def recarregar_config(self):
        self.cfg = config.load()
        self.voz.config = self.cfg
        self.voz.enabled = bool(self.cfg.get("voz_ativa", True))
        self.btn_voz.config(text=f"🎙 VOZ {'ON' if self.voz.enabled else 'OFF'}",
                            fg=RED_VIVO if self.voz.enabled else TXT_FRACO)

    def _sair(self):
        config.save(self.cfg)
        self.destroy()


if __name__ == "__main__":
    app = JarvisApp()
    app.mainloop()
