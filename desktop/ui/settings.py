"""Painel de Configurações (v4.2.0) — MICROFONE, ATUALIZAÇÃO, CHAVE GEMINI, SOBRE."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core import config, gemini_client, updater, wake_word
from core.config import sync_api_keys
from version import __version__, GITHUB_REPO


class PainelConfig(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(bg="#0d0708")
        self.title("Configurações — J.A.R.V.I.S")
        self.geometry("580x760")
        self.resizable(True, True)
        self.transient(master)

        self._montar()

    # ==================== UI ====================

    def _montar(self):
        fundo = {"bg": "#0d0708"}
        cfg = config.load()

        titulo = tk.Label(self, text="⚙ CONFIGURAÇÕES", font=("Consolas", 15, "bold"),
                         fg="#ff5a4d", **fundo)
        titulo.pack(pady=(18, 14))

        # ---------- CÉREBRO (nuvem ou offline) ----------
        self._secao("🧠 CÉREBRO — GEMINI (nuvem) ou OLLAMA (100% offline)")
        zona_c = tk.Frame(self, bg="#171012")
        zona_c.pack(fill=tk.X, padx=24)
        self.var_cerebro = tk.StringVar(value=cfg.get("cerebro", "gemini"))
        tk.Radiobutton(zona_c, text="Gemini (nuvem — precisa de chave)", variable=self.var_cerebro,
                       value="gemini", bg="#171012", fg="#f2e6e4", selectcolor="#0d0708",
                       activebackground="#171012", font=("Segoe UI", 9),
                       anchor="w").pack(fill=tk.X, padx=10, anchor="w")
        tk.Radiobutton(zona_c, text="Ollama (offline — roda no seu PC, sem internet)",
                       variable=self.var_cerebro, value="ollama", command=self._atualiza_ollama,
                       bg="#171012", fg="#f2e6e4", selectcolor="#0d0708",
                       activebackground="#171012", font=("Segoe UI", 9),
                       anchor="w").pack(fill=tk.X, padx=10, anchor="w")
        self.lbl_ollama = tk.Label(zona_c, text="verificando…", fg="#9c8a86", bg="#171012",
                                   font=("Segoe UI", 9), anchor="w", justify=tk.LEFT)
        self.lbl_ollama.pack(fill=tk.X, padx=10, pady=(4, 2))
        linha_o = tk.Frame(zona_c, bg="#171012")
        linha_o.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.cmb_modelo = ttk.Combobox(linha_o, width=28, state="readonly",
                                       font=("Segoe UI", 9))
        self.cmb_modelo.pack(side=tk.LEFT)
        tk.Button(linha_o, text="Verificar", command=self._verificar_ollama,
                  bg="#a1160f", fg="#ffe4de", bd=0, font=("Segoe UI", 9, "bold"),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT, padx=8)
        self._verificar_ollama()

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

        # ---------- PAINEL DE MEMÓRIA ----------
        self._secao("🧠 MEMÓRIAS DO J.A.R.V.I.S")
        zona_m = tk.Frame(self, bg="#171012")
        zona_m.pack(fill=tk.X, padx=24)
        self.lista_mem = tk.Listbox(zona_m, bg="#0d0708", fg="#f2e6e4", bd=0,
                                     highlightthickness=0, font=("Segoe UI", 9),
                                     selectbackground="#a1160f", height=5, activestyle="none")
        self.lista_mem.pack(fill=tk.X, padx=10, pady=(8, 4), side=tk.TOP)
        barra_m = tk.Frame(zona_m, bg="#171012")
        barra_m.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Button(barra_m, text="Apagar selecionada", command=self._apagar_memoria,
                  bg="#33100c", fg="#ffe4de", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT)
        tk.Button(barra_m, text="Apagar tudo", command=self._apagar_todas_memorias,
                  bg="#33100c", fg="#ff9a8f", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT, padx=6)
        self.lbl_mem_status = tk.Label(barra_m, text="", fg="#9c8a86", bg="#171012",
                                       font=("Segoe UI", 9))
        self.lbl_mem_status.pack(side=tk.LEFT, padx=8)
        self._carregar_memorias()

        # ---------- WAKE WORD (rede neural local) ----------
        self._secao("🧠 WAKE WORD — 'HEY JARVIS'")
        zona_w = tk.Frame(self, bg="#171012")
        zona_w.pack(fill=tk.X, padx=24)
        self.lbl_wake = tk.Label(zona_w, text="", fg="#9c8a86", bg="#171012",
                                 font=("Segoe UI", 9), anchor="w", justify=tk.LEFT)
        self.lbl_wake.pack(fill=tk.X, padx=10, pady=(8, 2))
        linha_w = tk.Frame(zona_w, bg="#171012")
        linha_w.pack(fill=tk.X, padx=10, pady=(2, 10))
        tk.Button(linha_w, text="Instalar agora (1 clique)",
                  command=self._instalar_wake, bg="#a1160f", fg="#ffe4de", bd=0,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  padx=12, pady=4).pack(side=tk.LEFT)
        self.lbl_wake_instala = tk.Label(linha_w, text="", fg="#9c8a86", bg="#171012",
                                         font=("Segoe UI", 9))
        self.lbl_wake_instala.pack(side=tk.LEFT, padx=10)
        self._atualiza_status_wake()

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

        # ---------- TEMA ----------
        self._secao("🎨 TEMA DO HUD (aplica ao reiniciar)")
        zona_t = tk.Frame(self, bg="#171012")
        zona_t.pack(fill=tk.X, padx=24)
        self.var_tema = tk.StringVar(value=cfg.get("tema", "classico"))
        for rot, desc in (("classico", "Azul holográfico (J.A.R.V.I.S original)"),
                          ("vermelho", "Reator de Arco Vermelho (v4.x)"),
                          ("gold", "Dourado Stark MK III")):
            tk.Radiobutton(zona_t, text=desc, variable=self.var_tema, value=rot,
                           bg="#171012", fg="#f2e6e4", selectcolor="#0d0708",
                           activebackground="#171012", font=("Segoe UI", 9),
                           anchor="w").pack(fill=tk.X, padx=10, anchor="w")

        # ---------- SOBRE ----------
        self._secao("ℹ SOBRE")
        zona4 = tk.Frame(self, bg="#171012")
        zona4.pack(fill=tk.X, padx=24)
        sobre = (f"J.A.R.V.I.S — Pro Ultra Desktop v{__version__}\n"
                 "Cérebro Gemini · interface Reator de Arco Vermelho\n"
                 "Porte da v4.3.0 Android para Python desktop\n"
                 "Fusão Mark LIII: wake word neural + 16 ações\n"
                 f"Repo: github.com/{GITHUB_REPO}\n"
                 "Desenvolvedor: André Luiz Lima Menezes")
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
        cfg["cerebro"] = self.var_cerebro.get()
        cfg["ollama_model"] = self.cmb_modelo.get()
        cfg["tema"] = self.var_tema.get()
        config.save(cfg)
        self.lbl_teste.config(text="testando…", fg="#9c8a86")
        threading.Thread(target=self._testar_chave, args=(chave,), daemon=True).start()

    def _avalia(self, texto: str, cor: str):
        """Atualiza o resultado na thread principal do tkinter (seguro)."""
        self.after(0, lambda: self.lbl_teste.config(text=texto, fg=cor))

    def _testar_chave(self, chave: str):
        try:
            if not chave:
                self._avalia("cole a chave primeiro, senhor.", "#ff9a8f")
                return
            teste = [{"role": "user", "parts": [{"text": "Diga apenas: ok."}]}]
            r = gemini_client.turn(chave, "Você é um teste de conexão. Responda de forma curtíssima.", teste, None)
            self._avalia(f"✓ chave válida — modelo {r.model}", "#7dc98f")
            self.after(0, self.app.recarregar_config)
        except Exception as e:
            msg = str(e)
            if "API key not valid" in msg or "api key" in msg.lower():
                self._avalia("✗ chave inválida — confira se copiou inteira (aistudio.google.com)", "#ff9a8f")
            elif "Failed to establish" in msg or "Connection" in msg:
                self._avalia("✗ sem internet — confira a conexão", "#ff9a8f")
            else:
                self._avalia(f"✗ {msg[:70]}", "#ff9a8f")

    def _testar_voz(self):
        self.app.voz.falar("Good evening. All systems are online and operating at full capacity.")

    # ==================== CÉREBRO / OLLAMA ====================

    def _verificar_ollama(self):
        def run():
            from core import ollama_client
            try:
                if ollama_client.disponivel():
                    modelos = ollama_client.modelos()
                    self.after(0, lambda: self._mostra_ollama(modelos))
                else:
                    self.after(0, lambda: self.lbl_ollama.config(
                        text="Ollama não encontrado. Instale em ollama.com, depois `ollama pull llama3.2`"))
            except Exception as e:
                erro_txt = str(e)
                self.after(0, lambda: self.lbl_ollama.config(text=f"erro: {erro_txt}"))
        threading.Thread(target=run, daemon=True).start()

    def _mostra_ollama(self, modelos: list):
        if not modelos:
            self.lbl_ollama.config(text="Ollama online, mas sem modelos. Rode `ollama pull llama3.2`")
            self.cmb_modelo["values"] = []
            return
        self.cmb_modelo["values"] = modelos
        atual = config.load().get("ollama_model", "")
        self.cmb_modelo.set(atual if atual in modelos else modelos[0])
        self.lbl_ollama.config(text=f"✓ Ollama online — {len(modelos)} modelo(s) disponível(is)")

    def _atualiza_ollama(self):
        self._verificar_ollama()

    # ==================== MEMÓRIA ====================

    def _carregar_memorias(self):
        from core import memory as mem
        self.lista_mem.delete(0, tk.END)
        self._memorias = mem.dados()
        if not self._memorias:
            self.lista_mem.insert(tk.END, "(nenhuma memória guardada ainda, senhor)")
            self.lista_mem.config(fg="#9c8a86")
        else:
            self.lista_mem.config(fg="#f2e6e4")
            for m in self._memorias[-30:]:
                texto = f"{m.get('data', '')} — {m.get('texto', '')[:60]}"
                self.lista_mem.insert(tk.END, texto)

    def _apagar_memoria(self):
        from core import memory as mem
        sel = self.lista_mem.curselection()
        if not sel:
            self.lbl_mem_status.config(text="selecione uma memória na lista")
            return
        idx_lista = sel[0]
        # mapeia a linha visível pra memória real (lista mostra as últimas 30)
        m = self._memorias[-(self.lista_mem.size() - idx_lista)]
        mem.esquecer(m.get("texto", ""))
        self.lbl_mem_status.config(text="memória apagada")
        self._carregar_memorias()

    def _apagar_todas_memorias(self):
        from core import memory as mem
        if messagebox.askyesno("J.A.R.V.I.S", "Apagar TODAS as memórias de longo prazo?",
                               parent=self, icon="warning"):
            mem.limpar()
            self.lbl_mem_status.config(text="todas apagadas")
            self._carregar_memorias()

    # ==================== WAKE WORD ====================

    def _atualiza_status_wake(self):
        try:
            from voice.wakelistener import WakeListener, TEM_SOUNDDEVICE
            dummy = WakeListener(lambda: None)
            if dummy.disponivel:
                texto = "✓ Rede neural pronta — fale 'Hey Jarvis' com o app aberto (100% local e offline)"
            elif wake_word.is_installed() and not TEM_SOUNDDEVICE:
                texto = "✓ openwakeword instalado, falta 'sounddevice' (pip install sounddevice)"
            else:
                texto = "Não instalado — a detecção ouve 'Hey Jarvis' localmente; nada sai do seu microfone"
            self.lbl_wake.config(text=texto)
        except Exception as e:
            self.lbl_wake.config(text=f"status indisponível: {e}")

    def _instalar_wake(self):
        self.lbl_wake_instala.config(text="instalando (baixa um modelo de ~5 MB, única vez)…")
        def run():
            ok, msg = wake_word.install_and_download(
                logger=lambda m: self.after(0, lambda mm=m: self.lbl_wake_instala.config(text=mm[:70]))
            )
            self.after(0, lambda: self.lbl_wake_instala.config(
                text=("✓ instalado!" if ok else f"✗ {msg[:60]}"),
                fg=("#7dc98f" if ok else "#ff9a8f")))
            self.after(0, self._atualiza_status_wake)
        threading.Thread(target=run, daemon=True).start()

    def _checar_update(self):
        self.lbl_versao.config(text="consultando o GitHub…")
        def run():
            info = updater.check_latest()
            texto = (f"Nova versão v{info['latest']} disponível! (instalada v{info['atual']})"
                     if info["update"] else f"{info['note']} (v{info['atual']})")
            self.after(0, lambda: self.lbl_versao.config(text=texto))
            if info["update"] and info["url"]:
                self.after(0, lambda: __import__("webbrowser").open(info["url"]))
        threading.Thread(target=run, daemon=True).start()

    def _concluir(self):
        cfg = config.load()
        cfg["gemini_api_key"] = self.var_chave.get().strip()
        cfg["voz_ativa"] = self.var_voz.get()
        cfg["voz_velocidade"] = float(self.vel.get())
        cfg["cerebro"] = self.var_cerebro.get()
        cfg["ollama_model"] = self.cmb_modelo.get()
        cfg["tema"] = self.var_tema.get()
        config.save(cfg)
        sync_api_keys(cfg)
        self.app.recarregar_config()
        self.destroy()
