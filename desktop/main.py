"""J.A.R.V.I.S — Pro Ultra Desktop v4.4.0 · Reator de Arco Vermelho × Mark LIII

Fusão: interface reator de arco + persona em português (v4.3.0) com o cérebro
do Mark LIII — rede neural de wake word local ("Hey Jarvis"), 17 ações
auto-descritivas, undo real e confirmação com botão humano.

Executa com:  python main.py
Requer:       pip install -r requirements.txt
"""
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from core import brain, config, tools, confirm
from core.action_loader import discover_actions
from core.adapters import PlayerAdapter, SessionMemoryAdapter
from core.config import sync_api_keys
from ui import theme
from ui.reactor import ArcReactorHud
from ui.chat import ChatPanel
from ui.settings import PainelConfig
from voice.tts import Voz
from voice import stt
from voice.wakelistener import WakeListener
from version import APP_NAME, __version__

# raiz do projeto no path — dentro do .exe vira a pasta temporária do PyInstaller
RAIZ = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

class JarvisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{__version__}")
        self.geometry("1120x760")
        self.minsize(960, 660)

        self.cfg = config.load()
        theme.usar(self.cfg.get("tema", "radar"))
        self.cor = theme.cor            # paleta do tema ativo (muda em ⚙ CONFIG)
        self.configure(bg=self.cor("janela_bg"))  # só agora, com o tema já certo
        sync_api_keys(self.cfg)          # ações do Mark LIII leem config/api_keys.json
        self.voz = Voz(self.cfg)
        self.historico: list = []
        self.fila_eventos: queue.Queue = queue.Queue()
        self._ocupado = False

        # o timer das tools avisa por aqui
        tools.on_timer_fire = self._timer_disparou

        # ---------- FUSÃO MARK LIII: registro de ações auto-descritivas ----------
        self.registro = discover_actions(
            RAIZ / "actions",
            reserved_names=tools.nomes(),   # tools nativas têm prioridade de nome
            logger=lambda msg: print(f"[MARK] {msg}"),
        )
        ctx = {
            "player": PlayerAdapter(lambda msg: print(f"[AÇÃO] {msg}")),
            "speak": self._falar_acao,
            "response": None,
            "session_memory": SessionMemoryAdapter(),
        }
        brain.attach_actions(self.registro, ctx)

        # confirmação que o modelo não forja (shutdown, restart, wifi, arquivos)
        confirm.bind(show=self._pedir_confirmacao, hide=lambda: None, log=print)

        # wake word neural ("Hey Jarvis", local e offline)
        self.wake = WakeListener(on_wake=self._wake_acordou, logger=print)

        self._montar_layout()
        self._boas_vindas()

        # liga o modo mãos-livres se estava habilitado e está instalado
        if self.cfg.get("wake_ativo") and self.wake.disponivel:
            self.wake.iniciar()

        self.protocol("WM_DELETE_WINDOW", self._sair)
        self.bind("<F4>", lambda e: self._alternar_voz())
        self.after(80, self._consumir_eventos)

    # ==================== LAYOUT ====================

    def _montar_layout(self):
        # ---- barra superior ----
        topo = tk.Frame(self, bg=self.cor("painel_bg"), height=54)
        topo.pack(fill=tk.X)
        topo.pack_propagate(False)
        tk.Label(topo, text="J.A.R.V.I.S — PRO ULTRA", font=("Consolas", 14, "bold"),
                 fg=self.cor("vivo"), bg=self.cor("painel_bg")).pack(side=tk.LEFT, padx=(18, 4))
        tk.Label(topo, text=f"DESKTOP v{__version__}", font=("Consolas", 9),
                 fg=self.cor("txt_fraco"), bg=self.cor("painel_bg")).pack(side=tk.LEFT, pady=(6, 0))

        # relógio vivo
        self.lbl_relogio = tk.Label(topo, text="", font=("Consolas", 9),
                                     bg=self.cor("painel_bg"), fg=self.cor("txt_fraco"))
        self.lbl_relogio.pack(side=tk.RIGHT, padx=(0, 14))
        self._tick_relogio()

        # chip de status pulsante
        self.chip = tk.Canvas(topo, width=120, height=26, bg=self.cor("painel_bg"), highlightthickness=0)
        self.chip.pack(side=tk.RIGHT, padx=(4, 0))
        self._chip_texto = "PRONTO"

        tk.Button(topo, text="💾", command=self._exportar_conversa,
                  bg=self.cor("painel_bg"), fg=self.cor("vivo"), bd=0,
                  font=("Segoe UI", 12), cursor="hand2").pack(side=tk.RIGHT, padx=6)
        self.btn_wake = tk.Button(topo, text="🧠 WAKE ?", command=self._alternar_wake,
                                  bg=self.cor("painel_bg"), fg=self.cor("vivo"), bd=0,
                                  font=("Consolas", 9, "bold"), cursor="hand2")
        self.btn_wake.pack(side=tk.RIGHT, padx=6)
        self.btn_voz = tk.Button(topo, text="🎙 VOZ ON", command=self._alternar_voz,
                                 bg=self.cor("painel_bg"), fg=self.cor("vivo"), bd=0,
                                 font=("Consolas", 9, "bold"), cursor="hand2")
        self.btn_voz.pack(side=tk.RIGHT, padx=6)
        tk.Button(topo, text="⚙ CONFIG", command=self._abrir_config,
                  bg=self.cor("painel_bg"), fg=self.cor("vivo"), bd=0,
                  font=("Consolas", 9, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=6)
        self._pulsar_chip()

        # ---- corpo: reator (esq) + chat (dir) ----
        corpo = tk.Frame(self, bg=self.cor("janela_bg"))
        corpo.pack(fill=tk.BOTH, expand=True)

        # v5.1.5: sem painel visível à esquerda — o holograma flutua direto
        # no fundo da janela (igual à foto de referência), sem "quadrado" atrás
        esquerda = tk.Frame(corpo, bg=self.cor("janela_bg"), width=460)
        esquerda.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 6), pady=10)
        esquerda.pack_propagate(False)
        self.reator = ArcReactorHud(esquerda, size=430)
        self.reator.pack(pady=(26, 6))

        # leituras vivas embaixo do reator
        self.lbl_leituras = tk.Label(esquerda, text="inicializando sensores…",
                                     font=("Consolas", 9), fg=self.cor("dim"), bg=self.cor("janela_bg"))
        self.lbl_leituras.pack(pady=(4, 12))
        tk.Label(esquerda, text="F4 alterna a voz  ·  senhor",
                 font=("Consolas", 8), fg=self.cor("txt_fraco"), bg=self.cor("janela_bg")).pack(pady=(0, 14))
        self.after(2000, self._atualizar_leituras)

        direita = tk.Frame(corpo, bg=self.cor("painel_bg"))
        direita.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        self.chat = ChatPanel(direita)
        self.chat.pack(fill=tk.BOTH, expand=True)

        # ---- chips de atalho ----
        chips = tk.Frame(direita, bg=self.cor("chat_bg"))
        chips.pack(fill=tk.X, padx=10, pady=(0, 4))
        for rotulo in ("Clima", "Status", "Memórias", "Resumir arquivo"):
            tk.Button(chips, text=rotulo, command=lambda r=rotulo: self._chip(r),
                      bg=self.cor("painel2"), fg=self.cor("vivo"), bd=0,
                      font=("Segoe UI", 8, "bold"), cursor="hand2",
                      padx=8, pady=2).pack(side=tk.LEFT, padx=(0, 6))

        # ---- barra de entrada ----
        barra = tk.Frame(direita, bg=self.cor("painel2"))
        barra.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.entrada = tk.Entry(barra, bg=self.cor("entrada_bg"), fg=self.cor("txt_claro"), bd=0,
                                insertbackground=self.cor("vivo"), font=("Segoe UI", 12))
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 8), pady=10, ipady=8)
        self.entrada.bind("<Return>", lambda e: self._enviar())

        if stt.DISPONIVEL:
            self.btn_mic = tk.Button(barra, text="🎙", command=lambda: self._ouvir(pausar_wake=True),
                                     bg=self.cor("painel2"), fg=self.cor("vivo"), bd=0,
                                     font=("Segoe UI", 13), cursor="hand2")
            self.btn_mic.pack(side=tk.LEFT, padx=(0, 6), pady=6)
        tk.Button(barra, text="ENVIAR ➤", command=self._enviar, bg=self.cor("dim"),
                  fg=self.cor("fg_dim"), bd=0, font=("Consolas", 10, "bold"),
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 10), pady=8)

        self._atualiza_botao_wake()

    # ==================== STATUS / HUD ====================

    def _pulsar_chip(self):
        import time
        cores = [self.cor("dim"), "#c4231a", self.cor("principal"), "#c4231a"]
        estagio = int(time.time() * 2) % len(cores)
        self.chip.delete("all")
        self.chip.create_oval(8, 9, 20, 21, fill=cores[estagio], outline="")
        self.chip.create_text(62, 15, text=self._chip_texto, fill=self.cor("txt_fraco"),
                              font=("Consolas", 9, "bold"))
        self.after(500, self._pulsar_chip)

    def _tick_relogio(self):
        from datetime import datetime
        dias = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
        d = datetime.now()
        self.lbl_relogio.config(text=f"{dias[d.weekday()]} {d.strftime('%d/%m')} · {d.strftime('%H:%M:%S')}")
        self.after(1000, self._tick_relogio)

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

    def _atualiza_botao_wake(self):
        if self.wake.ligado:
            self.btn_wake.config(text="🧠 HEY JARVIS ON", fg=self.cor("vivo"))
        elif self.wake.disponivel:
            self.btn_wake.config(text="🧠 HEY JARVIS OFF", fg=self.cor("txt_fraco"))
        else:
            self.btn_wake.config(text="🧠 WAKE ? (CONFIG)", fg=self.cor("txt_fraco"))

    # ==================== CHAT ====================

    def _boas_vindas(self):
        from datetime import datetime
        n_acoes = len(self.registro.names())

        h = datetime.now().hour
        if 5 <= h < 12:
            saudacao = "Bom dia, senhor André"
        elif 12 <= h < 18:
            saudacao = "Boa tarde, senhor André"
        else:
            saudacao = "Boa noite, senhor André"

        self.chat.add("jarvis",
                      f"{saudacao}. Sistemas online — reator de arco a plena capacidade.")
        if n_acoes:
            self.chat.add("sistema", f"{n_acoes} ações do Mark LIII fundidas ao meu arsenal.")
        if self.cfg.get("cerebro") == "ollama":
            self.chat.add("sistema", f"🧠 Cérebro OFFLINE: {self.cfg.get('ollama_model')} via Ollama — "
                                     "nada sai deste computador.")
        if self.cfg.get("hermes_ativo"):
            self.chat.add("sistema", "🛰 HERMES em posição — pedidos complexos serão "
                                    "orquestrados em planos de até 8 passos.")

        # ---- briefing do dia (primeira inicialização de hoje) ----
        hoje = datetime.now().strftime("%Y-%m-%d")
        primeiro_boot_do_dia = self.cfg.get("ultimo_boot") != hoje
        self.cfg["ultimo_boot"] = hoje
        config.save(self.cfg)
        if primeiro_boot_do_dia:
            threading.Thread(target=self._briefing_do_dia, daemon=True).start()

        if not config.api_key_ok(self.cfg):
            self.chat.add("sistema", "Cole sua chave do Gemini em ⚙ CONFIG para me dar um cérebro — "
                                     "é grátis em aistudio.google.com")

    def _briefing_do_dia(self):
        """Resumo local do dia (sem gastar API): data, clima e memórias recentes."""
        try:
            from datetime import datetime
            from core import memory as mem
            agora = datetime.now()
            dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                    "sexta-feira", "sábado", "domingo"]
            data_txt = f"{dias[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}"
            partes = [f"Hoje é {data_txt}, {agora.strftime('%H:%M')}."]

            clima = tools.execute("clima", {})
            if "falha" not in clima and "não consegui" not in clima:
                partes.append(clima)

            mems = mem.dados()[-3:]
            if mems:
                partes.append("Lembrando o que importa: " + "; ".join(m["texto"] for m in mems))

            briefing = " ".join(partes)
            self.fila_eventos.put(("fala", briefing))
        except Exception as e:
            print(f"[briefing] {e}")

    def _chip(self, rotulo: str):
        pedido = {"Clima": "qual o clima agora?",
                 "Status": "me dá o status do computador",
                 "Memórias": "liste minhas memórias",
                 "Resumir arquivo": "resuma o arquivo "}.get(rotulo, rotulo.lower())
        if rotulo == "Resumir arquivo":
            self.entrada.delete(0, tk.END)
            self.entrada.insert(0, pedido)
            self.entrada.focus_set()
        else:
            self._enviar(pedido)

    def _enviar(self, texto: str | None = None):
        msg = (texto or self.entrada.get()).strip()
        if not msg or self._ocupado:
            return
        if self.cfg.get("cerebro") == "ollama":
            if not self.cfg.get("ollama_model"):
                self._abrir_config()
                return
        elif not config.api_key_ok(self.cfg):
            self._abrir_config()
            return
        self.entrada.delete(0, tk.END)
        self.chat.add("user", msg)
        self._ocupado = True
        self._status("pensando", pensando=True)
        self.chat.mostrar_digitando()

        def retorno(resultado):
            self.fila_eventos.put(resultado)

        brain.process_async(self.cfg, self.historico, msg, retorno)

    def _ouvir(self, pausar_wake: bool = False):
        if self._ocupado:
            return
        self._status("ouvindo", ouvindo=True)
        if pausar_wake and self.wake.ligado:
            self.wake.pausar()   # solta o microfone pro STT

        def run():
            texto = stt.ouvir()
            if pausar_wake and self.wake.ligado:
                self.after(200, self.wake.retomar)  # devolve o microfone ao detector
            self.fila_eventos.put(("voz", texto))
        import threading
        threading.Thread(target=run, daemon=True).start()

    # ---- wake word neural ----

    def _wake_acordou(self):
        """A rede neural local ouviu 'Hey Jarvis' — acorda o modo mãos-livres."""
        if self._ocupado:
            return
        self.chat.add("sistema", "🧠 'Hey Jarvis' detectado — estou ouvindo, senhor.")
        self._ouvir(pausar_wake=True)

    def _alternar_wake(self):
        if self.wake.ligado:
            self.wake.parar()
            self.cfg["wake_ativo"] = False
            config.save(self.cfg)
            self.chat.add("sistema", "Wake word desligado.")
        elif self.wake.disponivel:
            if self.wake.iniciar():
                self.cfg["wake_ativo"] = True
                config.save(self.cfg)
                self.chat.add("sistema", "Modo mãos-livres ligado: fale 'Hey Jarvis' e eu escuto (detecção 100% local).")
            else:
                self.chat.add("sistema", "não consegui abrir o microfone pra o wake word.")
        else:
            self.chat.add("sistema", "Wake word não instalado — instale em ⚙ CONFIG → WAKE WORD (um clique).")
            self._abrir_config()
        self._atualiza_botao_wake()

    # ---- fala intermediária das ações (instant acknowledgment) ----

    def _falar_acao(self, msg: str):
        """speak() das ações — atravessa a fila pra chegar à UI com segurança."""
        if msg:
            self.fila_eventos.put(("fala", str(msg)))

    # ---- confirmação com botão humano (core/confirm.py) ----

    def _pedir_confirmacao(self, titulo: str, detalhe: str):
        """show do confirm.bind — chamado da thread do cérebro; só empurra pra fila."""
        self.fila_eventos.put(("confirm", (titulo, detalhe)))

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
                elif isinstance(item, tuple) and item[0] == "fala":
                    _, frase = item
                    self.chat.add("sistema", f"« {frase} »")
                    self.voz.falar(frase)
                elif isinstance(item, tuple) and item[0] == "confirm":
                    titulo, detalhe = item[1]
                    aceito = messagebox.askyesno(
                        "J.A.R.V.I.S — confirmação necessária",
                        f"{titulo}\n\n{detalhe}\n\nConfirmar?",
                        icon="warning", parent=self)
                    confirm.resolve(aceito)   # só o humano desbloqueia
                elif isinstance(item, tuple) and item[0] == "voz":
                    _, texto = item
                    self._status("pronto")
                    if texto:
                        self.chat.add("sistema", f"🎙 ouvi: \"{texto}\"")
                        self._enviar(texto)
                    elif not self.wake.ligado:
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
                            fg=self.cor("vivo") if ligado else self.cor("txt_fraco"))
        if not ligado:
            self.voz.falar("Voz desativada, senhor.")

    def _exportar_conversa(self):
        caminho = self.chat.exportar()
        if caminho:
            self.chat.add("sistema", f"💾 conversa salva em {caminho}")
        else:
            self.chat.add("sistema", "conversa vazia ou cancelada, senhor.")

    def _abrir_config(self):
        PainelConfig(self, self)

    def recarregar_config(self):
        self.cfg = config.load()
        sync_api_keys(self.cfg)
        self.voz.config = self.cfg
        self.voz.enabled = bool(self.cfg.get("voz_ativa", True))
        self.btn_voz.config(text=f"🎙 VOZ {'ON' if self.voz.enabled else 'OFF'}",
                            fg=self.cor("vivo") if self.voz.enabled else self.cor("txt_fraco"))
        self._atualiza_botao_wake()

    def _sair(self):
        try:
            self.wake.parar()
            from core.undo import clear as undo_clear
            undo_clear()
        except Exception:
            pass
        config.save(self.cfg)
        self.destroy()


if __name__ == "__main__":
    try:
        app = JarvisApp()
        app.mainloop()
    except Exception as e:
        # nunca mais fecha em silêncio: loga o erro e mostra na tela
        import traceback
        from datetime import datetime as _dt
        log = config.CONFIG_DIR / "erro.log"
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(f"J.A.R.V.I.S v{__version__} caiu em {_dt.now()}\n\n"
                           + traceback.format_exc(), encoding="utf-8")
        except Exception:
            log = None
        try:
            messagebox.showerror("J.A.R.V.I.S — erro",
                                 f"O sistema caiu, senhor.\n\n{e}\n\n"
                                 + (f"Log salvo em:\n{log}" if log else "Nao consegui salvar o log."))
        except Exception:
            pass
