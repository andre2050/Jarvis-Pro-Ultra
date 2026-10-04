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
        # botão só aparece quando o Ollama não é encontrado — 1 clique pro download oficial
        self.btn_ollama_baixar = tk.Button(
            zona_c, text="⬇ Baixar Ollama (ollama.com)",
            command=lambda: __import__("webbrowser").open("https://ollama.com/download"),
            bg="#33100c", fg="#ff9a8f", bd=0, font=("Segoe UI", 9, "bold"),
            cursor="hand2", padx=10, pady=4)
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
        # v4.10.6: no Windows, voz nativa (System.Speech) é mais confiável que o
        # pyttsx3 — é o motor principal por padrão lá; desmarque p/ testar pyttsx3
        import sys as _sys
        self.var_natwin = tk.BooleanVar(value=bool(cfg.get("voz_natwin", True)))
        tk.Checkbutton(zona, text="Usar voz NATIVA do Windows (recomendado — mais confiável)",
                       variable=self.var_natwin,
                       bg="#171012", fg="#9c8a86", activebackground="#171012",
                       selectcolor="#1d1214", font=("Segoe UI", 9), bd=0, anchor="w"
                       ).pack(fill=tk.X, padx=10, pady=(0, 2)) if _sys.platform.startswith("win") else None
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
                  padx=12, pady=4).pack(padx=10, pady=(2, 4), anchor="w")
        # v5.1.7: status honesto da voz + instalação em 1 clique
        self.lbl_voz_detalhe = tk.Label(zona, text="", fg="#9c8a86", bg="#171012",
                                        font=("Segoe UI", 9), anchor="w",
                                        justify=tk.LEFT, wraplength=460)
        self.lbl_voz_detalhe.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.btn_voz_instalar = tk.Button(
            zona, text="⬇ Instalar voz (1 clique — pyttsx3)",
            command=self._instalar_voz, bg="#33100c", fg="#ff9a8f", bd=0,
            font=("Segoe UI", 9, "bold"), cursor="hand2", padx=12, pady=4)
        # v5.1.8: SELETOR DE VOZ — escolha qualquer voz instalada no Windows
        linha_vozes = tk.Frame(zona, bg="#171012")
        linha_vozes.pack(fill=tk.X, padx=10, pady=(2, 2))
        self.cmb_voz = ttk.Combobox(linha_vozes, state="readonly", width=34,
                                    font=("Segoe UI", 9))
        self.cmb_voz.pack(side=tk.LEFT)
        tk.Label(linha_vozes, text="← escolha a voz e ouça o teste",
                 fg="#9c8a86", bg="#171012", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=8)
        self._vozes = [{"id": "", "nome": "Automática (padrão do JARVIS)"}]
        self.cmb_voz["values"] = [self._vozes[0]["nome"]]
        self.cmb_voz.set(self._vozes[0]["nome"])
        self.after(700, self._carregar_vozes)   # engine carrega as vozes em background
        self._atualiza_status_voz()

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
        tk.Button(barra_m, text="Editar selecionada", command=self._editar_memoria,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT)
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
        self.btn_wake_vcredist = tk.Button(
            zona_w, text="⬇ Baixar componente que falta (Visual C++)",
            command=lambda: __import__("webbrowser").open(wake_word.VCREDIST_URL),
            bg="#33100c", fg="#ff9a8f", bd=0, font=("Segoe UI", 9, "bold"),
            cursor="hand2", padx=12, pady=4)
        # fica escondido até o instalador detectar essa falta específica
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
        self.var_tema = tk.StringVar(value=cfg.get("tema", "novoskin"))
        for rot, desc in (("sentinela", "Sentinela: robô de fones vermelhos em HUD circular (padrão v4.14.1)"),
                          ("novoskin", "Busto cyan/teal com painel HUD lateral"),
                          ("busto", "Busto Holográfico wireframe gelo/azul (v4.9.3)"),
                          ("classico", "Azul holográfico (J.A.R.V.I.S original)"),
                          ("vermelho", "Reator de Arco Vermelho (v4.x)"),
                          ("gold", "Dourado Stark MK III"),
                          ("radar", "Holograma circular teal com sweep de radar (v5.1.0)")):
            tk.Radiobutton(zona_t, text=desc, variable=self.var_tema, value=rot,
                           bg="#171012", fg="#f2e6e4", selectcolor="#0d0708",
                           activebackground="#171012", font=("Segoe UI", 9),
                           anchor="w").pack(fill=tk.X, padx=10, anchor="w")

        # ---------- HERMES (agente orquestrador) ----------
        self._secao("🛰 HERMES — AGENTE ORQUESTRADOR (v5.1.0)")
        zona_h = tk.Frame(self, bg="#171012")
        zona_h.pack(fill=tk.X, padx=24)
        tk.Label(zona_h, text=(
            "Ligado, o HERMES planeja antes de responder: pede à rede neural um plano\n"
            "de até 8 passos, executa as tools um a um e sintetiza a resposta final.\n"
            "Ideal para pedidos complexos; para conversa simples ele responde direto."),
            fg="#f2e6e4", bg="#171012", font=("Segoe UI", 9),
            justify=tk.LEFT).pack(anchor="w", padx=10, pady=(6, 4))
        self.var_hermes = tk.BooleanVar(value=bool(cfg.get("hermes_ativo")))
        tk.Checkbutton(zona_h, text="Ativar modo orquestrador (aplica na hora)",
                       variable=self.var_hermes, bg="#171012", fg="#f2e6e4",
                       selectcolor="#0d0708", activebackground="#171012",
                       font=("Segoe UI", 9, "bold"), anchor="w",
                       command=self._alterna_hermes).pack(fill=tk.X, padx=10, anchor="w")
        self.lbl_hermes = tk.Label(zona_h, text="HERMES em espera.",
                                   fg="#9c8a86", bg="#171012", font=("Consolas", 8),
                                   justify=tk.LEFT, wraplength=470)
        self.lbl_hermes.pack(anchor="w", padx=10, pady=(4, 8))
        tk.Button(zona_h, text="Ver último plano executado", bg="#0d0708",
                  fg="#ff5a4d", bd=0, font=("Consolas", 8, "bold"), cursor="hand2",
                  command=self._mostra_plano_hermes).pack(anchor="w", padx=10, pady=(0, 8))

        # ---------- MODO MESA (v4.11.0) ----------
        self._secao("🖥 MODO MESA / CARRO (v4.11.0)")
        zona_m = tk.Frame(self, bg="#171012")
        zona_m.pack(fill=tk.X, padx=24)
        tk.Label(zona_m, text=(
            "Tela cheia SEMPRE LIGADA com o holograma, relógio, data e clima\n"
            "ao vivo. Sai com Esc ou clique. Atalho: F11."),
            fg="#f2e6e4", bg="#171012", font=("Segoe UI", 9),
            justify=tk.LEFT).pack(anchor="w", padx=10, pady=(6, 4))
        tk.Button(zona_m, text="▶ Abrir Modo Mesa", bg="#0d0708",
                  fg="#ff5a4d", bd=0, font=("Consolas", 9, "bold"), cursor="hand2",
                  command=self._abrir_mesa).pack(anchor="w", padx=10, pady=(0, 8))

        # ---------- PERSONALIZAÇÃO (v4.14.0) ----------
        self._secao("👤 PERSONALIZAÇÃO — como o JARVIS fala com o senhor")
        zona_p = tk.Frame(self, bg="#171012")
        zona_p.pack(fill=tk.X, padx=24)
        cfg_atual = config.load()
        self.var_nome_usuario = tk.StringVar(value=cfg_atual.get("nome_usuario", "André"))
        self.var_nome_assistente = tk.StringVar(value=cfg_atual.get("nome_assistente", "J.A.R.V.I.S"))
        self.var_estilo = tk.StringVar(value=cfg_atual.get("estilo", "formal"))
        self.var_economica = tk.BooleanVar(value=bool(cfg_atual.get("modo_economico", False)))
        self.var_whisper = tk.StringVar(value=cfg_atual.get("whisper_tamanho", "base"))
        # v4.14.2
        self.var_economia_auto = tk.BooleanVar(value=bool(cfg_atual.get("economia_auto", False)))
        self.var_economia_bateria = tk.StringVar(value=str(cfg_atual.get("economia_bateria", 40)))
        self.var_atalho_voz = tk.StringVar(value=cfg_atual.get("atalho_voz", "<F4>"))
        tk.Label(zona_p, text="Seu nome:", fg="#f2e6e4", bg="#171012",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=10, pady=4)
        tk.Entry(zona_p, textvariable=self.var_nome_usuario, bg="#0d0708",
                 fg="#f2e6e4", bd=0, width=22, insertbackground="#ff5a4d").grid(
            row=0, column=1, sticky="w", pady=4)
        tk.Label(zona_p, text="Nome do assistente:", fg="#f2e6e4", bg="#171012",
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=(16, 0), pady=4)
        tk.Entry(zona_p, textvariable=self.var_nome_assistente, bg="#0d0708",
                 fg="#f2e6e4", bd=0, width=18, insertbackground="#ff5a4d").grid(
            row=0, column=3, sticky="w", pady=4)
        tk.Label(zona_p, text="Estilo:", fg="#f2e6e4", bg="#171012",
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=10, pady=4)
        tk.Radiobutton(zona_p, text="Formal (senhor)", variable=self.var_estilo,
                       value="formal", bg="#171012", fg="#f2e6e4",
                       selectcolor="#0d0708", activebackground="#171012",
                       font=("Segoe UI", 9)).grid(row=1, column=1, sticky="w")
        tk.Radiobutton(zona_p, text="Descontraído (pelo seu nome)", variable=self.var_estilo,
                       value="descontraido", bg="#171012", fg="#f2e6e4",
                       selectcolor="#0d0708", activebackground="#171012",
                       font=("Segoe UI", 9)).grid(row=1, column=2, columnspan=2, sticky="w")
        tk.Label(zona_p, text="Ditado offline (Whisper):", fg="#f2e6e4", bg="#171012",
                 font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", padx=10, pady=4)
        cmb_w = ttk.Combobox(zona_p, textvariable=self.var_whisper, width=10,
                             state="readonly", values=["tiny", "base", "small"])
        cmb_w.grid(row=2, column=1, sticky="w", pady=4)
        tk.Label(zona_p, text="menor = mais rápido · maior = entende melhor",
                 fg="#9c8a86", bg="#171012", font=("Segoe UI", 8)).grid(
            row=2, column=2, columnspan=2, sticky="w", padx=(16, 0))

        # ---------- MODO ECONÔMICO (v4.14.0) ----------
        self._secao("⚡ MODO ECONÔMICO — pra PC mais fraco")
        zona_e = tk.Frame(self, bg="#171012")
        zona_e.pack(fill=tk.X, padx=24)
        tk.Label(zona_e, text=("Reduz o holograma pra ~12 fps e as leituras de CPU/RAM\n"
                               "de 2s pra 8s. A voz e as respostas continuam iguais."),
                  fg="#9c8a86", bg="#171012", font=("Segoe UI", 8),
                  justify=tk.LEFT).pack(anchor="w", padx=10, pady=(6, 2))
        tk.Checkbutton(zona_e, text="Ativar modo econômico (aplica na hora)",
                       variable=self.var_economica, bg="#171012", fg="#f2e6e4",
                       selectcolor="#0d0708", activebackground="#171012",
                       font=("Segoe UI", 9),
                       command=self._aplicar_economia).pack(anchor="w", padx=10, pady=(0, 8))

        # ---------- MODO ECONÔMICO AUTOMÁTICO (v4.14.2) ----------
        tk.Checkbutton(zona_e, text="Ligar sozinho quando a bateria cair abaixo de",
                       variable=self.var_economia_auto, bg="#171012", fg="#f2e6e4",
                       selectcolor="#0d0708", activebackground="#171012",
                       font=("Segoe UI", 9)).pack(anchor="w", padx=10)
        linha_bat = tk.Frame(zona_e, bg="#171012")
        linha_bat.pack(anchor="w", padx=10, pady=(0, 8))
        tk.Entry(linha_bat, textvariable=self.var_economia_bateria, width=4,
                 bg="#1d1214", fg="#f2e6e4", insertbackground="#f2e6e4",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        tk.Label(linha_bat, text="% de bateria (só em notebook, com bateria)",
                 fg="#9c8a86", bg="#171012", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=6)

        # ---------- GERENCIADOR DE PLUGINS (v4.14.2) ----------
        self._secao("🔌 GERENCIADOR DE PLUGINS — ligue/desligue funções")
        zona_pl = tk.Frame(self, bg="#171012")
        zona_pl.pack(fill=tk.X, padx=24)
        tk.Label(zona_pl, text=("Desligada, a função nem aparece pro cérebro — ele não tenta\n"
                                "chamar. Ligar de volta aplica na hora, sem reiniciar."),
                 fg="#9c8a86", bg="#171012", font=("Segoe UI", 8),
                 justify=tk.LEFT).pack(anchor="w", padx=10, pady=(6, 2))
        grade = tk.Frame(zona_pl, bg="#171012")
        grade.pack(fill=tk.X, padx=10, pady=(0, 8))
        self._plugin_vars: dict[str, tk.BooleanVar] = {}
        desligadas = set(cfg_atual.get("tools_desligadas") or [])
        de_todos = self._todas_tools_declaradas()
        for idx, decl in enumerate(de_todos):
            nome = decl["name"]
            var = tk.BooleanVar(value=nome not in desligadas)
            self._plugin_vars[nome] = var
            desc = (decl.get("description") or "").strip()
            rot = nome.replace("_", " ")
            celula = tk.Frame(grade, bg="#171012")
            celula.grid(row=idx // 2, column=idx % 2, sticky="w",
                        padx=(0, 10), pady=1)
            tk.Checkbutton(celula, text=rot, variable=var, bg="#171012",
                           fg="#f2e6e4", selectcolor="#0d0708",
                           activebackground="#171012", font=("Segoe UI", 8),
                           onvalue=True, offvalue=False).pack(anchor="w")
            tk.Label(celula, text=desc[:70] + ("…" if len(desc) > 70 else ""),
                     fg="#6a5750", bg="#171012", font=("Segoe UI", 7),
                     wraplength=200, justify=tk.LEFT).pack(anchor="w")

        # ---------- AGENDA (v4.14.2) ----------
        self._secao("📅 AGENDA — avisos agendados")
        zona_ag = tk.Frame(self, bg="#171012")
        zona_ag.pack(fill=tk.X, padx=24)
        self.zona_agenda = tk.Frame(zona_ag, bg="#171012")
        self.zona_agenda.pack(fill=tk.X, padx=10, pady=(6, 4))
        self.lbl_agenda = tk.Label(zona_ag, text="", fg="#9c8a86", bg="#171012",
                                   font=("Segoe UI", 8))
        self.lbl_agenda.pack(anchor="w", padx=10, pady=(0, 4))
        tk.Button(zona_ag, text="Atualizar lista", command=self._atualizar_agenda,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(anchor="w", padx=10, pady=(0, 8))
        self._atualizar_agenda()

        # ---------- LOG DE ERROS (v4.14.2) ----------
        self._secao("🧯 LOG DE ERROS — veja e exporte quando algo bugar")
        zona_log = tk.Frame(self, bg="#171012")
        zona_log.pack(fill=tk.X, padx=24)
        barra_log = tk.Frame(zona_log, bg="#171012")
        barra_log.pack(anchor="w", padx=10, pady=(6, 4))
        tk.Button(barra_log, text="Ver log de erros", command=self._ver_log_erros,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT)
        tk.Button(barra_log, text="Exportar cópia", command=self._exportar_log,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT, padx=6)
        self.lbl_log = tk.Label(zona_log, text="", fg="#9c8a86", bg="#171012",
                               font=("Segoe UI", 8), wraplength=380)
        self.lbl_log.pack(anchor="w", padx=10, pady=(0, 4))

        # ---------- ATALHO DA VOZ (v4.14.2) ----------
        self._secao("⌨️ ATALHO DA VOZ — liga/desliga a escuta")
        zona_at = tk.Frame(self, bg="#171012")
        zona_at.pack(fill=tk.X, padx=24)
        self.lbl_atalho = tk.Label(zona_at, textvariable=self.var_atalho_voz,
                                   fg="#ffd9a0", bg="#171012", font=("Consolas", 10, "bold"))
        self.lbl_atalho.pack(anchor="w", padx=10, pady=(6, 2))
        tk.Button(zona_at, text="Gravar novo atalho", command=self._gravar_atalho,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(anchor="w", padx=10, pady=(0, 8))

        # ---------- DEPENDÊNCIAS (v4.14.2) ----------
        self._secao("📦 DEPENDÊNCIAS — o que está instalado e o que falta")
        zona_dp = tk.Frame(self, bg="#171012")
        zona_dp.pack(fill=tk.BOTH, padx=24)
        barra_dp = tk.Frame(zona_dp, bg="#171012")
        barra_dp.pack(fill=tk.X, pady=(6, 4))
        tk.Button(barra_dp, text="Verificar agora", command=self._verificar_deps,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT)
        tk.Button(barra_dp, text="Instalar faltantes", command=self._instalar_deps,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT, padx=6)
        self.lbl_deps = tk.Label(barra_dp, text="", fg="#9c8a86", bg="#171012",
                                font=("Segoe UI", 8))
        self.lbl_deps.pack(side=tk.LEFT, padx=8)
        self.txt_deps = tk.Text(zona_dp, height=6, bg="#0d0708", fg="#f2e6e4",
                                font=("Consolas", 8), bd=0, wrap="word")
        self.txt_deps.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.txt_deps.insert("1.0", "Toque em \"Verificar agora\" pra checar o que está instalado.")
        self.txt_deps.configure(state=tk.DISABLED)

        # ---------- BACKUP (v4.14.0) ----------
        self._secao("💾 BACKUP — a vida do JARVIS em um arquivo")
        zona_b = tk.Frame(self, bg="#171012")
        zona_b.pack(fill=tk.X, padx=24)
        tk.Label(zona_b, text=("Exporta memórias, agenda e configurações num .zip —\n"
                               "troque de PC sem perder nada. Importar restaura tudo."),
                  fg="#9c8a86", bg="#171012", font=("Segoe UI", 8),
                  justify=tk.LEFT).pack(anchor="w", padx=10, pady=(6, 2))
        barra_b = tk.Frame(zona_b, bg="#171012")
        barra_b.pack(fill=tk.X, padx=10, pady=(0, 4))
        tk.Button(barra_b, text="Exportar backup", command=self._exportar_backup,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT)
        tk.Button(barra_b, text="Importar backup", command=self._importar_backup,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT, padx=6)
        self.lbl_backup = tk.Label(barra_b, text="", fg="#9c8a86", bg="#171012",
                                   font=("Segoe UI", 8), wraplength=360)
        self.lbl_backup.pack(side=tk.LEFT, padx=8)

        # ---------- DIAGNÓSTICO (v4.14.0) ----------
        self._secao("🩺 DIAGNÓSTICO — teste de todas as ferramentas")
        zona_d = tk.Frame(self, bg="#171012")
        zona_d.pack(fill=tk.BOTH, padx=24)
        barra_d = tk.Frame(zona_d, bg="#171012")
        barra_d.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Button(barra_d, text="▶ Rodar diagnóstico", command=self._rodar_diagnostico,
                  bg="#241408", fg="#ffd9a0", bd=0, font=("Segoe UI", 9),
                  cursor="hand2", padx=10, pady=3).pack(side=tk.LEFT)
        self.lbl_diag = tk.Label(barra_d, text="", fg="#9c8a86", bg="#171012",
                                 font=("Segoe UI", 8))
        self.lbl_diag.pack(side=tk.LEFT, padx=8)
        self.txt_diag = tk.Text(zona_d, bg="#0d0708", fg="#f2e6e4", bd=0,
                                highlightthickness=0, font=("Consolas", 8),
                                height=8, wrap="word", state=tk.DISABLED)
        self.txt_diag.pack(fill=tk.X, padx=10, pady=(2, 8))

        # ---------- CATÁLOGO DE COMANDOS (v4.11.0) ----------
        self._secao("📖 CATÁLOGO DE COMANDOS — tudo que o J.A.R.V.I.S sabe fazer")
        zona_c = tk.Frame(self, bg="#171012")
        zona_c.pack(fill=tk.BOTH, padx=24, expand=True)
        try:
            from core import brain
            decls = brain.todas_declaracoes()
        except Exception:
            decls = []
        linhas = []
        for d in decls:
            linhas.append(f"▸ {d.get('name', '?')} — {d.get('description', '')[:110]}")
        txt_cat = tk.Text(zona_c, bg="#0d0708", fg="#f2e6e4", bd=0,
                          highlightthickness=0, font=("Consolas", 8),
                          wrap="word", height=min(14, max(6, len(decls) // 3)),
                          state=tk.DISABLED)
        txt_cat.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 8))
        txt_cat.configure(state=tk.NORMAL)
        txt_cat.insert("1.0",
            "Comandos rápidos (respondem na hora, até offline):\n"
            "  'que horas são' · 'que dia é hoje' · 'status do pc' · 'abre o bloco de notas'\n"
            "  'toca música de rock' · 'aumenta o volume' · 'me avisa em 10 minutos pra sair'\n"
            "  'às 18:30 me avisa do boleto' · 'quanto é 15*3' · 'briefing' · 'pausa a música'\n\n"
            "Tools do cérebro (nuvem ou offline):\n" + "\n".join(linhas))
        txt_cat.configure(state=tk.DISABLED)

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

    def _alterna_hermes(self):
        self.app.cfg["hermes_ativo"] = bool(self.var_hermes.get())
        config.save(self.app.cfg)
        self._avalia("✓ HERMES " + ("ativado, senhor." if self.var_hermes.get()
                                    else "desativado."), "#a9ff9c" if self.var_hermes.get() else "#ff9a8f")

    def _mostra_plano_hermes(self):
        from core import hermes
        self.lbl_hermes.config(text=hermes.ultimo_relatorio())

    def _abrir_mesa(self):
        """v4.11.0: abre o Modo Mesa (mesma janela do F11 do app)."""
        try:
            from ui.mesa import ModoMesa
            ModoMesa(self)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Modo Mesa", f"Não consegui abrir: {e}", parent=self)

    def _aplicar_economia(self):
        """v4.14.0: aplica o modo econômico NA HORA no holograma."""
        try:
            app = getattr(self, "app", None)
            if app is not None and hasattr(app, "hud"):
                app.hud.economia = bool(self.var_economia.get())
        except Exception:
            pass

    def _exportar_backup(self):
        from tkinter import filedialog
        from core import backup
        alvo = filedialog.asksaveasfilename(
            parent=self, defaultextension=".zip",
            initialfile="jarvis-backup.zip",
            filetypes=[("Backup do JARVIS", "*.zip")])
        if alvo:
            self.lbl_backup.config(text=backup.exportar(alvo), fg="#ffd9a0")

    def _importar_backup(self):
        from tkinter import filedialog, messagebox
        from core import backup
        origem = filedialog.askopenfilename(
            parent=self, filetypes=[("Backup do JARVIS", "*.zip")])
        if not origem:
            return
        if not messagebox.askyesno(
                "J.A.R.V.I.S",
                "Importar substitui memórias, agenda e configurações atuais. Continuar?",
                parent=self, icon="warning"):
            return
        msg = backup.importar(origem)
        self.lbl_backup.config(text=msg, fg="#ffd9a0")

    def _rodar_diagnostico(self):
        from core import diagnostico
        self.lbl_diag.config(text="testando…")
        self.txt_diag.configure(state=tk.NORMAL)
        self.txt_diag.delete("1.0", tk.END)
        self.txt_diag.configure(state=tk.DISABLED)

        def run():
            try:
                resultados = diagnostico.rodar()
            except Exception as e:
                resultados = [("diagnóstico", False, f"falhou: {e}")]
            self.after(0, lambda: self._mostrar_diagnostico(resultados))

        import threading
        threading.Thread(target=run, daemon=True).start()

    def _mostrar_diagnostico(self, resultados):
        linhas = []
        ok_total = 0
        for nome, ok, detalhe in resultados:
            marca = "✓" if ok else "✗"
            ok_total += 1 if ok else 0
            linhas.append(f"{marca} {nome} — {detalhe}")
        self.txt_diag.configure(state=tk.NORMAL)
        self.txt_diag.delete("1.0", tk.END)
        self.txt_diag.insert("1.0", f"{ok_total}/{len(resultados)} prontas\n" +
                             "\n".join(linhas))
        self.txt_diag.configure(state=tk.DISABLED)
        self.lbl_diag.config(text=f"{ok_total}/{len(resultados)} ferramentas prontas")

    # ==================== v4.14.2: GERENCIADOR DE PLUGINS ====================

    def _todas_tools_declaradas(self) -> list[dict]:
        """Declarações completas: tools nativas + ações do registro
        (plugins .py da pasta actions), sem filtrar as desligadas."""
        from core import tools
        de_todos = list(tools.declarations())
        registro = getattr(getattr(self, "app", None), "registro", None)
        if registro is not None:
            try:
                de_todos += list(registro.get_tool_declarations())
            except Exception:
                pass
        return de_todos

    def _plugins_escolhidos_desligados(self) -> list[str]:
        return [n for n, v in getattr(self, "_plugin_vars", {}).items()
                if not v.get()]

    # ==================== v4.14.2: AGENDA ====================

    def _atualizar_agenda(self):
        from core import agenda
        for filho in self.zona_agenda.winfo_children():
            filho.destroy()
        avisos = agenda.itens()
        if not avisos:
            self.lbl_agenda.config(text="Nenhum aviso agendado, senhor.")
            return
        self.lbl_agenda.config(text=f"{len(avisos)} aviso(s) agendado(s):")
        for a in avisos:
            linha = tk.Frame(self.zona_agenda, bg="#171012")
            linha.pack(fill=tk.X, pady=1)
            quando = (a.get("quando") or "")[:16].replace("T", " ")
            tk.Label(linha, text=f"#{a.get('id')} · {a.get('motivo')} · {quando}",
                     fg="#f2e6e4", bg="#171012", font=("Segoe UI", 8),
                     wraplength=330, justify=tk.LEFT).pack(side=tk.LEFT)
            tk.Button(linha, text="Editar", command=lambda av=a: self._editar_aviso(av),
                      bg="#1d1610", fg="#ffd9a0", bd=0, font=("Segoe UI", 7),
                      cursor="hand2", padx=6).pack(side=tk.LEFT, padx=3)
            tk.Button(linha, text="Cancelar", command=lambda av=a: self._cancelar_aviso(av),
                      bg="#2a0d0d", fg="#ff9a8f", bd=0, font=("Segoe UI", 7),
                      cursor="hand2", padx=6).pack(side=tk.LEFT)

    def _editar_aviso(self, aviso):
        from tkinter import simpledialog
        ident = aviso.get("id")
        novo_h = simpledialog.askstring(
            "J.A.R.V.I.S", "Novo horário (vazio mantém o atual)\n\n"
            "Formatos: 18:30 · amanhã 9:00 · 25/12 08:00",
            parent=self, initialvalue=aviso.get("quando", "")[:16].replace("T", " "))
        if novo_h is None:
            return
        novo_m = simpledialog.askstring(
            "J.A.R.V.I.S", "Novo motivo (vazio mantém o atual):",
            parent=self, initialvalue=aviso.get("motivo", ""))
        if novo_m is None:
            return
        from core import agenda
        msg = agenda.editar(ident, novo_h, novo_m)
        self._atualizar_agenda()
        if "não encontrei" in msg or "não entendi" in msg:
            from tkinter import messagebox
            messagebox.showwarning("J.A.R.V.I.S", msg, parent=self)

    def _cancelar_aviso(self, aviso):
        from tkinter import messagebox
        from core import agenda
        if not messagebox.askyesno("J.A.R.V.I.S",
                                   f"Cancelar o aviso \"{aviso.get('motivo')}\"?",
                                   parent=self):
            return
        agenda.cancelar(aviso.get("id"))
        self._atualizar_agenda()

    # ==================== v4.14.2: LOG DE ERROS ====================

    def _caminho_log(self):
        from core.config import CONFIG_DIR
        return CONFIG_DIR / "erro.log"

    def _ver_log_erros(self):
        import tkinter.scrolledtext as st
        log = self._caminho_log()
        win = tk.Toplevel(self)
        win.title("J.A.R.V.I.S — log de erros")
        win.configure(bg="#171012")
        win.geometry("640x420")
        txt = st.ScrolledText(win, bg="#0d0708", fg="#f2e6e4",
                              font=("Consolas", 9), bd=0)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        if log.exists():
            try:
                conteudo = log.read_text(encoding="utf-8", errors="replace")[-20000:]
            except Exception as e:
                conteudo = f"não consegui ler o log: {e}"
            txt.insert("1.0", conteudo)
            self.lbl_log.config(text=f"log: {log}")
        else:
            txt.insert("1.0", "Nenhum erro registrado até agora, senhor — o log "
                              "só nasce quando algo falha.")
            self.lbl_log.config(text="sem log (nada quebrou ainda)")
        txt.configure(state=tk.DISABLED)

    def _exportar_log(self):
        from tkinter import filedialog
        log = self._caminho_log()
        if not log.exists():
            self.lbl_log.config(text="nada pra exportar — o log ainda não existe")
            return
        alvo = filedialog.asksaveasfilename(
            parent=self, defaultextension=".log",
            initialfile="jarvis-erro.log", filetypes=[("Log", "*.log"), ("Tudo", "*.*")])
        if not alvo:
            return
        try:
            import shutil
            shutil.copy(log, alvo)
            self.lbl_log.config(text=f"cópia salva em {alvo}")
        except Exception as e:
            self.lbl_log.config(text=f"falhou ao exportar: {e}")

    # ==================== v4.14.2: ATALHO DA VOZ ====================

    def _gravar_atalho(self):
        """Captura a PRÓXIMA combinação de teclas e vira o atalho da voz."""
        self._capturando = True
        self.lbl_atalho.config(text="aperte a combinação agora…")
        self.focus_force()
        self.bind("<KeyPress>", self._captura_atalho, add=True)

    def _captura_atalho(self, ev):
        if not getattr(self, "_capturando", False):
            return
        # ignora modificadores puros (Ctrl, Shift, Alt sozinhos)
        if ev.keysym == "Escape":        # desiste: mantém o atalho anterior
            self._fim_captura()
            return
        if ev.keysym in ("Control_L", "Control_R", "Shift_L", "Shift_R",
                         "Alt_L", "Alt_R", "AltGr", "Caps_Lock"):
            return
        partes = []
        if ev.state & 0x0004:
            partes.append("Control")
        if ev.state & 0x0008 or ev.state & 0x0080:
            partes.append("Alt")
        if ev.state & 0x0001:
            partes.append("Shift")
        tecla = ev.keysym
        if len(tecla) == 1:
            tecla = tecla.lower()
        partes.append(tecla)
        novo = "<" + "-".join(partes) + ">"
        self.var_atalho_voz.set(novo)
        self._fim_captura()

    def _fim_captura(self):
        self._capturando = False
        try:
            self.unbind("<KeyPress>", self._captura_atalho)
        except Exception:
            pass
        self.lbl_atalho.config(textvariable=self.var_atalho_voz)

    # ==================== v4.14.2: DEPENDÊNCIAS ====================

    def _verificar_deps(self):
        from core import deps as dep_mod
        res = dep_mod.status()
        linhas, faltando = [], []
        for r in res:
            marca = "✓" if r["ok"] else "✗"
            linhas.append(f"{marca} {r['rotulo']} — {'' if r['ok'] else r['motivo']}"
                          + ("" if r["ok"] else f"  (pra: {r['para']})"))
            if not r["ok"]:
                faltando.append(r["pip"])
        self.txt_deps.configure(state=tk.NORMAL)
        self.txt_deps.delete("1.0", tk.END)
        self.txt_deps.insert("1.0", "\n".join(linhas))
        self.txt_deps.configure(state=tk.DISABLED)
        ok_n = sum(1 for r in res if r["ok"])
        self.lbl_deps.config(text=f"{ok_n}/{len(res)} instaladas"
                             + (f" · {len(faltando)} faltando" if faltando else " · tudo em ordem"))
        self._deps_faltantes = faltando

    def _instalar_deps(self):
        from core import deps as dep_mod
        faltando = getattr(self, "_deps_faltantes", None)
        if not faltando:
            self._verificar_deps()
            faltando = getattr(self, "_deps_faltantes", [])
        if not faltando:
            self.lbl_deps.config(text="nada pra instalar, senhor — tudo aí.")
            return
        self.lbl_deps.config(text=f"instalando {len(faltando)} pacote(s)…")
        self.txt_deps.configure(state=tk.NORMAL)
        self.txt_deps.delete("1.0", tk.END)
        self.txt_deps.configure(state=tk.DISABLED)

        def escrever(linha):
            def _poe():
                self.txt_deps.configure(state=tk.NORMAL)
                self.txt_deps.insert(tk.END, linha + "\n")
                self.txt_deps.see(tk.END)
                self.txt_deps.configure(state=tk.DISABLED)
            self.after(0, _poe)

        def run():
            dep_mod.instalar(list(faltando), log=escrever)
            self.after(0, self._verificar_deps)

        import threading
        threading.Thread(target=run, daemon=True).start()

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
        if hasattr(self, "var_natwin"):
            cfg["voz_natwin"] = bool(self.var_natwin.get())
        cfg["voz_velocidade"] = float(self.vel.get())
        cfg["cerebro"] = self.var_cerebro.get()
        cfg["ollama_model"] = self.cmb_modelo.get()
        cfg["tema"] = self.var_tema.get()
        cfg["nome_usuario"] = self.var_nome_usuario.get().strip() or "André"   # v4.14.0
        cfg["nome_assistente"] = self.var_nome_assistente.get().strip() or "J.A.R.V.I.S"
        cfg["estilo"] = self.var_estilo.get()
        cfg["modo_economico"] = bool(self.var_economica.get())
        cfg["whisper_tamanho"] = self.var_whisper.get()
        # v4.14.2
        cfg["tools_desligadas"] = self._plugins_escolhidos_desligados()
        cfg["atalho_voz"] = self.var_atalho_voz.get() or "<F4>"
        cfg["economia_auto"] = bool(self.var_economia_auto.get())
        try:
            cfg["economia_bateria"] = max(5, min(95, int(self.var_economia_bateria.get())))
        except ValueError:
            cfg["economia_bateria"] = 40
        config.save(cfg)
        try:
            from core import tools as _tools
            _tools.set_cfg(cfg)
        except Exception:
            pass
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
        self._aplicar_voz_escolhida()   # ouve o teste NA voz selecionada
        self.app.voz.falar("Good evening. All systems are online and operating at full capacity.")
        self.after(300, self._atualiza_status_voz)

    def _carregar_vozes(self):
        """preenche o combobox com as vozes que o Windows tem instaladas"""
        try:
            do_sistema = self.app.voz.vozes or []
        except Exception:
            do_sistema = []
        self._vozes = [{"id": "", "nome": "Automática (padrão do JARVIS)"}] + list(do_sistema)
        self.cmb_voz["values"] = [v["nome"] for v in self._vozes]
        atual = (self.app.voz.config.get("voz_id") or "").strip()
        sel = self._vozes[0]["nome"]
        for v in self._vozes:
            if v["id"] == atual:
                sel = v["nome"]
        self.cmb_voz.set(sel)

    def _aplicar_voz_escolhida(self):
        """salva a escolha no config em memória e reaplica no engine na hora"""
        escolhida = ""
        for v in getattr(self, "_vozes", []):
            if v["nome"] == self.cmb_voz.get():
                escolhida = v["id"]
        self.app.voz.config["voz_id"] = escolhida
        self.app.voz.reconfigurar()

    def _atualiza_status_voz(self):
        ok, motivo = self.app.voz.estado()
        if ok and motivo == "ok":
            self.lbl_voz_detalhe.config(text="✓ Voz do JARVIS funcionando (pyttsx3)",
                                        fg="#7dc98f")
            self.btn_voz_instalar.pack_forget()
        elif ok:
            # v5.1.9: falando pela voz nativa do Windows — funciona, mas dá pra melhorar
            self.lbl_voz_detalhe.config(
                text=f"✓ Voz funcionando — {motivo}",
                fg="#e0c48f")
            self.btn_voz_instalar.pack(fill=tk.X, padx=10, pady=(0, 10), anchor="w")
        else:
            self.lbl_voz_detalhe.config(text=f"✗ O JARVIS NÃO ESTÁ CONSEGUINDO FALAR — {motivo}",
                                        fg="#ff9a8f")
            self.btn_voz_instalar.pack(fill=tk.X, padx=10, pady=(0, 10), anchor="w")

    def _instalar_voz(self):
        self.btn_voz_instalar.config(text="instalando pyttsx3…")
        def run():
            import subprocess, sys
            r = subprocess.run([sys.executable, "-m", "pip", "install", "pyttsx3"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                self.after(0, lambda: self.lbl_voz_detalhe.config(
                    text="✓ pyttsx3 instalado! FECHE E ABRA O JARVIS de novo pra voz ativar.",
                    fg="#7dc98f"))
                self.after(0, self.btn_voz_instalar.pack_forget)
            else:
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
                self.after(0, lambda: self.lbl_voz_detalhe.config(
                    text=f"✗ falha na instalação: {tail[0][:110]}", fg="#ff9a8f"))
        threading.Thread(target=run, daemon=True).start()

    # ==================== CÉREBRO / OLLAMA ====================

    def _verificar_ollama(self):
        self.btn_ollama_baixar.pack_forget()
        self.lbl_ollama.config(text="verificando…")
        def run():
            from core import ollama_client
            try:
                if ollama_client.disponivel():
                    modelos = ollama_client.modelos()
                    self.after(0, lambda: self._mostra_ollama(modelos))
                else:
                    self.after(0, self._ollama_nao_encontrado)
            except Exception as e:
                erro_txt = str(e)
                self.after(0, lambda: self.lbl_ollama.config(text=f"erro: {erro_txt}"))
        threading.Thread(target=run, daemon=True).start()

    def _ollama_nao_encontrado(self):
        # Não é bug do JARVIS: o Ollama é um programa separado (como o Docker),
        # precisa ser instalado no Windows/Mac/Linux antes de aparecer aqui.
        self.lbl_ollama.config(
            text=("Ollama não encontrado no seu PC. É um programa separado — instale, "
                  "depois abra um terminal e rode `ollama pull llama3.2`, então clique "
                  "'Verificar' de novo. Enquanto isso, o Gemini (nuvem) continua funcionando "
                  "normalmente se você marcar essa opção."),
            wraplength=460, justify=tk.LEFT)
        self.btn_ollama_baixar.pack(fill=tk.X, padx=10, pady=(0, 8), anchor="w")

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

    def _editar_memoria(self):
        """v4.14.0: editor de memórias — reescreve o texto mantendo a data."""
        from core import memory as mem
        from tkinter import simpledialog
        sel = self.lista_mem.curselection()
        if not sel:
            self.lbl_mem_status.config(text="selecione uma memória na lista")
            return
        m = self._memorias[-(self.lista_mem.size() - sel[0])]
        novo = simpledialog.askstring("Editar memória", "Novo texto:",
                                      initialvalue=m.get("texto", ""),
                                      parent=self)
        if novo and novo.strip() and novo.strip() != m.get("texto"):
            mem.atualizar(m.get("texto", ""), novo.strip())
            self.lbl_mem_status.config(text="memória atualizada")
            self._carregar_memorias()

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
        self.btn_wake_vcredist.pack_forget()
        def run():
            ok, msg = wake_word.install_and_download(
                logger=lambda m: self.after(0, lambda mm=m: self.lbl_wake_instala.config(text=mm[:70]))
            )
            self.after(0, lambda: self._finaliza_instala_wake(ok, msg))
        threading.Thread(target=run, daemon=True).start()

    def _finaliza_instala_wake(self, ok: bool, msg: str):
        if ok:
            self.lbl_wake_instala.config(text="✓ instalado!", fg="#7dc98f")
            self.btn_wake_vcredist.pack_forget()
        elif wake_word.VCREDIST_MARCADOR in msg:
            # causa raiz conhecida: falta o Visual C++ Redistributable no Windows.
            # mostra a instrução completa (sem truncar) e o botão de download direto.
            explicacao = msg.split("::", 1)[1]
            self.lbl_wake_instala.config(text=explicacao, fg="#ff9a8f",
                                        wraplength=460, justify=tk.LEFT)
            self.btn_wake_vcredist.pack(padx=10, pady=(0, 10), anchor="w")
        else:
            self.lbl_wake_instala.config(text=f"✗ {msg[:120]}", fg="#ff9a8f",
                                        wraplength=460, justify=tk.LEFT)
            self.btn_wake_vcredist.pack_forget()
        self._atualiza_status_wake()

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
        if hasattr(self, "var_natwin"):
            cfg["voz_natwin"] = bool(self.var_natwin.get())
        cfg["voz_velocidade"] = float(self.vel.get())
        cfg["cerebro"] = self.var_cerebro.get()
        cfg["ollama_model"] = self.cmb_modelo.get()
        cfg["tema"] = self.var_tema.get()
        cfg["voz_id"] = self._id_voz_escolhida()
        # v4.14.2
        cfg["tools_desligadas"] = self._plugins_escolhidos_desligados()
        cfg["atalho_voz"] = self.var_atalho_voz.get() or "<F4>"
        cfg["economia_auto"] = bool(self.var_economia_auto.get())
        try:
            cfg["economia_bateria"] = max(5, min(95, int(self.var_economia_bateria.get())))
        except ValueError:
            cfg["economia_bateria"] = 40
        config.save(cfg)
        sync_api_keys(cfg)
        self.app.recarregar_config()
        self.destroy()

    def _id_voz_escolhida(self) -> str:
        for v in getattr(self, "_vozes", []):
            if v["nome"] == self.cmb_voz.get():
                return v["id"]
        return ""
