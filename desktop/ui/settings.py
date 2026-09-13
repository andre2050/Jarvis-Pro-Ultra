"""Painel de Configurações (v4.2.0) — MICROFONE, ATUALIZAÇÃO, CHAVE GEMINI, SOBRE."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core import config, gemini_client, updater
from version import __version__, GITHUB_REPO


class PainelConfig(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(bg="#0d0708")
        self.title("Configurações — J.A.R.V.I.S")
        self.geometry("560x600")
        self.resizable(False, False)
        self.transient(master)

        self._montar()

    # ==================== UI ====================

    def _montar(self):
        fundo = {"bg": "#0d0708"}
        cfg = config.load()

        titulo = tk.Label(self, text="⚙ CONFIGURAÇÕES", font=("Consolas", 15, "bold"),
                         fg="#ff5a4d", **fundo)
        titulo.pack(pady=(18, 14))

        # ---------- CHAVE DO GEMINI ----------
        self._secao("🧠 CHAVE DO GEMINI")
        moldura = tk.Frame(self, bg="#171012")
        moldura.pack(fill=tk.X, padx=24)
        self.var_chave = tk.StringVar(value=cfg.get("gemini_api_key", ""))
        self.ent_chave = tk.Entry(moldura, textvariable=self.var_chave, show="•",
                                  bg="#1d1214", fg="#ffe4de", insertbackground="#ff5a4d",
                                  relief=tk.FLAT, font=("Consolas", 11))
        self.ent_chave.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10, ipady=6)
        tk.Button(moldura, text="👁", command=self._alternar_mostrar, bg="#171012",
                  fg="#ff5a4d", bd=0, font=("Segoe UI", 11), cursor="hand2"
                  ).pack(side=tk.LEFT, padx=(0, 10))
        linha = tk.Frame(self, bg="#0d0708")
        linha.pack(fill=tk.X, padx=24, pady=(8, 0))
        tk.Button(linha, text="Salvar e Testar", command=self._salvar_testar,
                  bg="#a1160f", fg="#ffe4de", bd=0, font=("Segoe UI", 10, "bold"),
                  cursor="hand2", padx=14, pady=6).pack(side=tk.LEFT)
        self.lbl_teste = tk.Label(linha, text="", fg="#9c8a86", font=("Segoe UI", 9), **fundo)
        self.lbl_teste.pack(side=tk.LEFT, padx=10)

        # ---------- VOZ ----------
        self._secao("🎙️ VOZ E MICROFONE")
        zona = tk.Frame(self, bg="#171012")
        zona.pack(fill=tk.X, padx=24)
        self.var_voz = tk.BooleanVar(value=bool(cfg.get("voz_ativa", True)))
        tk.Checkbutton(zona, text="JARVIS fala em voz alta", variable=self.var_voz,
                      bg="#171012", fg="#f2e6e4", activebackground="#171012",
                      activeforeground="#ff5a4d", selectcolor="#1d1214",
                      font=("Segoe UI", 10), bd=0, anchor="w"
                      ).pack(fill=tk.X, padx=10, pady=(10, 2))
        linha2 = tk.Frame(zona, bg="#171012")
        linha2.pack(fill=tk.X, padx=10, pady=(2, 6))
        tk.Label(linha2, text="Velocidade da fala", fg="#9c8a86",
                 bg="#171012", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.vel = tk.DoubleVar(value=float(cfg.get("voz_velocidade", 0.85)))
        tk.Scale(linha2, from_=0.5, to=1.5, resolution=0.05, variable=self.vel,
                 orient=tk.HORIZONTAL, bg="#171012", fg="#f2e6e4",
                 troughcolor="#1d1214", highlightthickness=0, bd=0, length=220
                 ).pack(side=tk.LEFT, padx=10)
        from voice import stt, tts
        self.lbl_mic = tk.Label(zona, text="", fg="#9c8a86", bg="#171012",
                                font=("Segoe UI", 9), anchor="w")
        self.lbl_mic.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.lbl_mic.config(text=("✓ Reconhecimento de voz disponível" if stt.DISPONIVEL
                             else "Reconhecimento de voz indisponível (pip install SpeechRecognition pyaudio)")
                            + (" · TTS ✓" if tts.TEM_PYTTSX3 else " · TTS indisponível (pip install pyttsx3)"))
        tk.Button(zona, text="Testar voz", command=self._testar_voz, bg="#a1160f",
                  fg="#ffe4de", bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2",
                  padx=12, pady=4).pack(padx=10, pady=(2, 10), anchor="w")

        # ---------- ATUALIZAÇÃO ----------
        self._secao("⟳ ATUALIZAÇÃO")
        zona3 = tk.Frame(self, bg="#171012")
        zona3.pack(fill=tk.X, padx=24)
        self.lbl_versao = tk.Label(zona3, text=f"Versão instalada: v{__version__}",
                                   fg="#9c8a86", bg="#171012", font=("Segoe UI", 9))
        self.lbl_versao.pack(anchor="w", padx=10, pady=(8, 2))
        tk.Button(zona3, text="Verificar nova versão agora", command=self._checar_update,
                  bg="#a1160f", fg="#ffe4de", bd=0, font=("Segoe UI", 9, "bold"),
                  cursor="hand2", padx=12, pady=4).pack(padx=10, pady=(2, 8), anchor="w")
        tk.Button(zona3, text="Abrir página de releases", command=lambda:
                  __import__("webbrowser").open(f"https://github.com/{GITHUB_REPO}/releases"),
                  bg="#171012", fg="#ff5a4d", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=12, pady=4).pack(padx=10, pady=(0, 10), anchor="w")

        # ---------- SOBRE ----------
        self._secao("ℹ SOBRE")
        zona4 = tk.Frame(self, bg="#171012")
        zona4.pack(fill=tk.X, padx=24)
        sobre = (f"J.A.R.V.I.S — Pro Ultra Desktop v{__version__}\n"
                 "Cérebro Gemini · interface Reator de Arco Vermelho\n"
                 "Porte da v4.3.0 Android para Python desktop\n"
                 f"Repo: github.com/{GITHUB_REPO}\n"
                 "Desenvolvedor: Andre Luiz Lima Menezes")
        tk.Label(zona4, text=sobre, fg="#9c8a86", bg="#171012",
                 font=("Consolas", 9), justify=tk.LEFT).pack(anchor="w", padx=10, pady=8)

        tk.Button(self, text="Concluir", command=self._concluir, bg="#a1160f",
                  fg="#ffe4de", bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2",
                  padx=18, pady=6).pack(pady=16)

    def _secao(self, txt: str):
        tk.Label(self, text=txt, bg="#0d0708", fg="#ff5a4d",
                 font=("Consolas", 10, "bold")).pack(fill=tk.X, padx=24, pady=(12, 4))

    # ==================== AÇÕES ====================

    def _alternar_mostrar(self):
        self.ent_chave.config(show="" if self.ent_chave.cget("show") == "•" else "•")

    def _salvar_testar(self):
        chave = self.var_chave.get().strip()
        cfg = config.load()
        cfg["gemini_api_key"] = chave
        cfg["voz_ativa"] = self.var_voz.get()
        cfg["voz_velocidade"] = float(self.vel.get())
        config.save(cfg)
        self.lbl_teste.config(text="testando…", fg="#9c8a86")
        threading.Thread(target=self._testar_chave, args=(chave,), daemon=True).start()

    def _testar_chave(self, chave: str):
        try:
            if not chave:
                self.lbl_teste.config(text="cole a chave primeiro, senhor.", fg="#ff9a8f")
                return
            r = gemini_client.turn(chave, "Responda apenas: ok.", [], None)
            self.lbl_teste.config(text=f"✓ chave válida — modelo {r.model}", fg="#7dc98f")
            self.app.recarregar_config()
        except Exception as e:
            self.lbl_teste.config(text=f"✗ {str(e)[:70]}", fg="#ff9a8f")

    def _testar_voz(self):
        self.app.voz.falar("Good evening. All systems are online and operating at full capacity.")

    def _checar_update(self):
        self.lbl_versao.config(text="consultando o GitHub…")
        def run():
            info = updater.check_latest()
            texto = (f"Nova versão v{info['latest']} disponível! (instalada v{info['atual']})"
                     if info["update"] else f"{info['note']} (v{info['atual']})")
            self.lbl_versao.config(text=texto)
            if info["update"] and info["url"]:
                __import__("webbrowser").open(info["url"])
        threading.Thread(target=run, daemon=True).start()

    def _concluir(self):
        cfg = config.load()
        cfg["gemini_api_key"] = self.var_chave.get().strip()
        cfg["voz_ativa"] = self.var_voz.get()
        cfg["voz_velocidade"] = float(self.vel.get())
        config.save(cfg)
        self.app.recarregar_config()
        self.destroy()
