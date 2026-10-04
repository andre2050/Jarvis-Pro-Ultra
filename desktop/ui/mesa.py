"""Modo Mesa (v4.11.0) — porte do DeskModeActivity do Android (v4.7.2).

Tela cheia SEMPRE LIGADA com o holograma gigante do tema atual, relógio
vivo, data em português, clima ao vivo (Open-Meteo, renova a cada 15 min)
e leitura de bateria/CPU. Sai com Esc ou clique em qualquer lugar.
Entrada: ⚙ CONFIG → MODO MESA, ou F11 na janela principal.
"""
import threading
import time
import tkinter as tk
from datetime import datetime

from ui import theme as _tema
from ui.reactor import ArcReactorHud

DIAS = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA",
        "SEXTA-FEIRA", "SÁBADO", "DOMINGO"]


class ModoMesa(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self._vivo = True
        self.configure(bg="#050507", cursor="none")
        self.attributes("-fullscreen", True)
        self.title("Modo Mesa — J.A.R.V.I.S")

        tela_w = self.winfo_screenwidth()
        self.hud = ArcReactorHud(self, size=int(min(tela_w * 0.42, 620)))
        self.hud.pack(pady=(int(tela_w * 0.02), 6))

        cor_viva = _tema.cor("vivo")
        cor_dim = _tema.cor("dim")
        self.lbl_hora = tk.Label(self, font=("Segoe UI", int(tela_w * 0.045), "bold"),
                                 fg=cor_viva, bg="#050507")
        self.lbl_hora.pack()
        self.lbl_data = tk.Label(self, font=("Segoe UI", int(tela_w * 0.016)),
                                 fg=cor_viva, bg="#050507")
        self.lbl_data.pack()
        self.lbl_clima = tk.Label(self, font=("Segoe UI", int(tela_w * 0.012)),
                                  fg=cor_viva, bg="#050507",
                                  wraplength=int(tela_w * 0.8), justify=tk.CENTER)
        self.lbl_clima.pack(pady=(18, 2))
        self.lbl_aviso = tk.Label(self, font=("Segoe UI", 9),
                                  fg=cor_dim, bg="#050507")
        self.lbl_aviso.pack(side=tk.BOTTOM, pady=8)

        self.bind("<Escape>", lambda e: self.fechar())
        self.bind("<Button-1>", lambda e: self.fechar())
        self.protocol("WM_DELETE_WINDOW", self.fechar)

        self._tic()
        self._carregar_clima()
        threading.Thread(target=self._manter_acorda, daemon=True).start()

    # ---------- relógio ----------

    def _tic(self):
        if not self._vivo:
            return
        try:
            agora = datetime.now()
            self.lbl_hora.config(text=agora.strftime("%H:%M"))
            self.lbl_data.config(text=f"{DIAS[agora.weekday()]} · "
                                      f"{agora.strftime('%d/%m/%Y')}")
            self.lbl_aviso.config(text="Esc ou clique para sair do Modo Mesa")
            self.after(1000, self._tic)
        except tk.TclError:
            self._vivo = False

    # ---------- clima (renova a cada 15 min) ----------

    def _carregar_clima(self):
        if not self._vivo:
            return

        def run():
            try:
                from core import tools
                texto = tools.execute("clima", {})
                if self._vivo:
                    self.after(0, lambda: self.lbl_clima.config(text=texto[:140]))
            except Exception as e:
                if self._vivo:
                    self.after(0, lambda e=e: self.lbl_clima.config(
                        text=f"clima indisponível ({str(e)[:40]})"))

        threading.Thread(target=run, daemon=True).start()
        if self._vivo:
            self.after(15 * 60 * 1000, self._carregar_clima)

    # ---------- tela sempre ligada (Windows) ----------

    def _manter_acorda(self):
        """No Windows, renova SetThreadExecutionState(ES_DISPLAY_REQUIRED)
        a cada 45s — a tela não apaga enquanto o Modo Mesa estiver aberto."""
        import sys
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            ES_CONTINUOUS, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000002
            while self._vivo:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_DISPLAY_REQUIRED)
                time.sleep(45)
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            pass

    def fechar(self):
        self._vivo = False
        try:
            self.destroy()
        except tk.TclError:
            pass
