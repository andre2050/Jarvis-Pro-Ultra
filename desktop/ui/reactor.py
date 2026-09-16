"""O reator de arco do JARVIS (v4.3.0) — porte fiel do ArcReactorHud.kt.

Dial circular vermelho, estilo Homem de Ferro: marcações finas de
instrumento, blooms de luz pulsantes, anel de chevrons girando, grade
radial no núcleo e leitura viva do computador (bateria/CPU, hora, data).
Animações: respira (2,6s), gira devagar (22s — 6s no modo mãos-livres),
gira rápido (14s — 0,9s pensando), com aura extra falando/ouvindo.

v5.1.0: cores lidas AO VIVO do tema (trocar em ⚙ CONFIG recolore sem reiniciar)
e o tema "radar" desenha o HOLOGRAMA CIRCULAR — anéis concêntricos, sweep
giratório com rastros, blips que acendem quando o varredura passa e retículo
central. Mesmos estados (pensando/ouvindo/falando) do reator.
"""
import math
import time
import tkinter as tk

try:
    import psutil
    TEM_PSUTIL = True
except ImportError:
    TEM_PSUTIL = False

# v5.0.0: cores vêm do tema ativo (ui/theme.py) — azul clássico, vermelho ou gold
from ui import theme as _tema


def _T(chave):
    return _tema.cor(chave)


SEMANA = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


def _cor_letra(flick: float) -> str:
    """Interpola na paleta de glows DO TEMA ATIVO conforme intensidade 0..1."""
    glows = _tema.cores()["glows"]
    idx = min(len(glows) - 1, int(flick * len(glows)))
    return glows[idx]


class ArcReactorHud(tk.Canvas):
    def __init__(self, master, size: int = 430, **kw):
        super().__init__(master, width=size, height=size, bg=_T("fundo"),
                         highlightthickness=0, **kw)
        self.size = size
        self.thinking = False
        self.listening = False
        self.speaking = False

        self._t0 = time.time()
        self._bat = None
        self._cpu = 0
        self._atualiza_leituras()
        self._frame()

    # ---------- leitura viva do computador (a cada 2s) ----------

    def _atualiza_leituras(self):
        if TEM_PSUTIL:
            try:
                self._cpu = psutil.cpu_percent(interval=0)
                bat = psutil.sensors_battery()
                self._bat = round(bat.percent) if bat else None
            except Exception:
                pass
        self.after(2000, self._atualiza_leituras)

    # ---------- loop de animação ----------

    def _frame(self):
        self.delete("all")
        w = h = self.size
        cx = cy = w / 2
        r = min(w, h) * 0.46
        el = time.time() - self._t0

        # v5.1.0: tema "radar" desenha o holograma circular da foto;
        # qualquer outro tema usa o reator de arco clássico.
        # BUG CORRIGIDO (v5.1.2): faltava o "else" aqui — em qualquer tema
        # que não fosse "radar" a tela ficava em branco pra sempre e o loop
        # de animação morria (o after() de reagendamento só existia dentro
        # do if, então nunca era chamado no caso padrão).
        if _tema.atual() == "radar":
            self._frame_radar(cx, cy, r, el)
        else:
            self._frame_arc(cx, cy, r, el)

        self.after(40, self._frame)  # ~25 fps — reagenda sempre, uma única vez

    def _frame_radar(self, cx, cy, r, el):
        """HOLOGRAMA CIRCULAR da foto: núcleo teal, anel azul, branco nos
        detalhes e agulha vermelha varrendo. Estados: pensando 0,9s/volta,
        ouvindo 6s, ocioso 14s."""
        teal = _T("principal")          # núcleo (#1baaad)
        teal_vivo = _T("vivo")
        teal_dim = _T("dim")
        glows = _tema.cores()["glows"]
        AZUL = "#4a8fb5"                # anel externo azul da foto
        AZUL_DIM = "#2a4a60"
        BRANCO = "#dfe9ec"              # marcações em branco
        VERMELHO = "#ff4238"            # agulha vermelha

        periodo = 0.9 if self.thinking else (6 if self.listening else 14)
        sweep = (el / periodo) * 360
        ang = math.radians(sweep)

        # ---- cross-hair discreto (cinza-azulado) ----
        for (x1, y1, x2, y2) in ((cx - r * 0.94, cy, cx + r * 0.94, cy),
                                 (cx, cy - r * 0.94, cx, cy + r * 0.94)):
            self.create_line(x1, y1, x2, y2, fill=AZUL_DIM, width=1)

        # ---- fundo do disco (levemente mais claro que a janela) ----
        self.create_oval(cx - r * 0.90, cy - r * 0.90, cx + r * 0.90, cy + r * 0.90,
                         fill=_T("escuro"), outline="")

        # ---- ANEL AZUL EXTERNO grosso (marca da foto: 0.6-0.85 do raio) ----
        self.create_oval(cx - r * 0.78, cy - r * 0.78, cx + r * 0.78, cy + r * 0.78,
                         outline=AZUL, width=int(r * 0.16))
        self.create_oval(cx - r * 0.94, cy - r * 0.94, cx + r * 0.94, cy + r * 0.94,
                         outline=AZUL_DIM, width=int(r * 0.05), stipple="gray25")
        self.create_oval(cx - r * 0.65, cy - r * 0.65, cx + r * 0.65, cy + r * 0.65,
                         outline=AZUL_DIM, width=1.5)

        # ---- trilha do sweep (fatias teal com alpha decrescente) ----
        bbox = (cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62)
        for larg, stipp in ((90, "gray12"), (55, "gray25"), (30, "gray50")):
            self.create_arc(bbox, start=sweep - larg, extent=larg,
                            style=tk.CHORD, fill=teal, outline="", stipple=stipp)

        # ---- ANEL DE TRILHA teal-escuro onde os blips vivem ----
        self.create_oval(cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62,
                         outline=teal_dim, width=1.4)
        self.create_oval(cx - r * 0.44, cy - r * 0.44, cx + r * 0.44, cy + r * 0.44,
                         outline=teal_dim, width=1)

        # ---- AGULHA VERMELHA do radar ----
        self.create_line(cx, cy, cx + r * 0.62 * math.cos(ang),
                         cy + r * 0.62 * math.sin(ang), fill=VERMELHO, width=2)

        # ---- blips: acendem quando a agulha passa ----
        for i in range(8):
            b_ang = (i * 47 + 13) % 360
            b_dist = 0.50 + (i % 2) * 0.09
            a = math.radians(b_ang)
            bx = cx + r * b_dist * math.cos(a)
            by = cy + r * b_dist * math.sin(a)
            atraso = (sweep - b_ang) % 360
            brilho = max(0.0, 1.0 - atraso / 360)
            if brilho <= 0.02:
                continue
            raio = 2.5 + 3.5 * brilho
            idx = min(len(glows) - 1, int(brilho * len(glows)))
            self.create_oval(bx - raio, by - raio, bx + raio, by + raio,
                             fill=BRANCO if brilho > 0.65 else glows[idx],
                             outline="")
            if brilho > 0.30:
                self.create_oval(bx - raio - 5, by - raio - 5, bx + raio + 5, by + raio + 5,
                                 outline=glows[-2], width=1, stipple="gray25")

        # ---- ticks BRANCOS no anel azul (72, grandes a cada 6) ----
        n_ticks = 72
        r_out = r * 0.86
        for i in range(n_ticks):
            grande = i % 6 == 0
            a = i * (360 / n_ticks) * math.pi / 180
            tamanho = 13 if grande else 5
            x1 = cx + (r_out - tamanho) * math.cos(a)
            y1 = cy + (r_out - tamanho) * math.sin(a)
            x2 = cx + r_out * math.cos(a)
            y2 = cy + r_out * math.sin(a)
            self.create_line(x1, y1, x2, y2, fill=BRANCO if grande else AZUL_DIM,
                             width=2 if grande else 1)

        # ---- NÚCLEO TEAL brilhante (o coração da foto) ----
        self.create_oval(cx - r * 0.34, cy - r * 0.34, cx + r * 0.34, cy + r * 0.34,
                         fill=teal, outline="")
        self.create_oval(cx - r * 0.40, cy - r * 0.40, cx + r * 0.40, cy + r * 0.40,
                         outline=teal_dim, width=1.2)
        # brilho extra pulsando devagar
        pulso = 0.5 + 0.5 * math.sin(el * 2.4)
        self.create_oval(cx - r * (0.36 + 0.02 * pulso), cy - r * (0.36 + 0.02 * pulso),
                         cx + r * (0.36 + 0.02 * pulso), cy + r * (0.36 + 0.02 * pulso),
                         outline=teal_vivo, width=2, stipple="gray50")

        # ---- rótulos BRANCOS orbitais ----
        labels = ["H E R M E S", "R E D E", "M E M", "V O Z"]
        for i, lbl in enumerate(labels):
            a = (-90 + i * 90) * math.pi / 180
            lx, ly = cx + r * 0.78 * math.cos(a), cy + r * 0.78 * math.sin(a)
            self.create_text(lx, ly, text=lbl, fill=BRANCO,
                             font=("Consolas", max(8, int(r * 0.045))))

        # ---- leitura no núcleo (bateria/CPU), texto branco ----
        if self.thinking:
            centro = "···"
        elif self._bat is not None:
            centro = str(self._bat)
        else:
            centro = f"{self._cpu:.0f}"
        self.create_text(cx, cy, text=centro, fill=BRANCO,
                         font=("Consolas", int(r * 0.16), "bold"))
        rotulo = "BAT%" if self._bat is not None else "CPU%"
        if not self.thinking:
            self.create_text(cx, cy - r * 0.22, text=rotulo, fill=BRANCO,
                             font=("Consolas", max(8, int(r * 0.045))))

        # ---- hora · data embaixo, azul ----
        import datetime as _dt
        agora = _dt.datetime.now()
        self.create_text(cx, cy + r * 0.24,
                         text=agora.strftime("%H:%M") + f" · {agora.day} DE {SEMANA[agora.weekday()]}",
                         fill=BRANCO, font=("Consolas", max(8, int(r * 0.045))))

        # ---- bezel externo ----
        self.create_oval(cx - r * 0.995, cy - r * 0.995, cx + r * 0.995, cy + r * 0.995,
                         outline=AZUL_DIM, width=1.5)

        # ---- aura quando falando ou ouvindo ----
        if self.speaking or self.listening:
            raio = r * (0.92 + 0.02 * math.sin(el * 6))
            self.create_oval(cx - raio, cy - raio, cx + raio, cy + raio,
                             outline=teal, width=2, stipple="gray50")

    def _frame_arc(self, cx, cy, r, el):
        """Reator de arco clássico — o dial circular das versões anteriores."""
        principal = _T("principal")
        vivo = _T("vivo")
        dim = _T("dim")
        escuro = _T("escuro")
        breathe = (el % 2.6) / 2.6
        slow_spin = (el / (6 if self.listening else 22)) * 360
        fast_spin = (el / (0.9 if self.thinking else 14)) * 360
        # ---- núcleo: disco com brilho por trás do número ----
        self.create_oval(cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62,
                         fill=_cor_letra(0.28 + 0.10 * breathe), outline="")

        # ---- grade radial girando devagar (16 raios, r*0.20 -> r*0.40) ----
        rot = math.radians(slow_spin * 0.3)
        for i in range(16):
            a = i * (360 / 16) * math.pi / 180 + rot
            x1, y1 = cx + r * 0.20 * math.cos(a), cy + r * 0.20 * math.sin(a)
            x2, y2 = cx + r * 0.40 * math.cos(a), cy + r * 0.40 * math.sin(a)
            self.create_line(x1, y1, x2, y2, fill=dim, width=1.2)
        self.create_oval(cx - r * 0.40, cy - r * 0.40, cx + r * 0.40, cy + r * 0.40,
                         outline=dim, width=1.2)

        # ---- anel de chevrons (40 dashes triangulares) girando ----
        rot = math.radians(slow_spin)
        rr = r * 0.52
        n_chev = 40
        for i in range(n_chev):
            a0 = i * (360 / n_chev) * math.pi / 180 + rot
            a1 = (i * (360 / n_chev) + (360 / n_chev) * 0.55) * math.pi / 180 + rot
            grande = i % 5 == 0
            cor = principal if grande else dim
            self.create_line(cx + rr * math.cos(a0), cy + rr * math.sin(a0),
                             cx + rr * math.cos(a1), cy + rr * math.sin(a1),
                             fill=cor, width=3.5 if grande else 2)

        # ---- ticks do dial (72 marcações finas, grandes a cada 6) ----
        n_ticks = 72
        r_out = r * 0.82
        drift = math.radians(fast_spin * 0.02)
        for i in range(n_ticks):
            grande = i % 6 == 0
            a = i * (360 / n_ticks) * math.pi / 180 + drift
            tamanho = 14 if grande else 6
            x1, y1 = cx + (r_out - tamanho) * math.cos(a), cy + (r_out - tamanho) * math.sin(a)
            x2, y2 = cx + r_out * math.cos(a), cy + r_out * math.sin(a)
            self.create_line(x1, y1, x2, y2,
                             fill=principal if grande else dim,
                             width=2 if grande else 1)

        # ---- bezel externo (anel duplo) ----
        self.create_oval(cx - r * 0.86, cy - r * 0.86, cx + r * 0.86, cy + r * 0.86,
                         outline=dim, width=1.5)
        self.create_oval(cx - r * 0.995, cy - r * 0.995, cx + r * 0.995, cy + r * 0.995,
                         outline=escuro, width=1.5)

        # ---- blooms de luz pulsantes (7, ritmos diferentes) ----
        n_blooms = 7
        for i in range(n_blooms):
            a = (i * (360 / n_blooms) + slow_spin * 0.15) * math.pi / 180
            bx, by = cx + r * 0.92 * math.cos(a), cy + r * 0.92 * math.sin(a)
            flick = 0.4 + 0.6 * ((math.sin(breathe * 2 * math.pi + i * 1.7) + 1) / 2)
            raio = r * 0.22
            self.create_oval(bx - raio, by - raio, bx + raio, by + raio,
                             fill=_cor_letra(0.55 * flick), outline="", stipple="gray50")

        # ---- setas nos cardeais ----
        for deg in (-90, 0, 90, 180):
            a = deg * math.pi / 180
            bx, by = cx + r * 1.02 * math.cos(a), cy + r * 1.02 * math.sin(a)
            ang = a + math.pi / 2
            p1 = (bx + 9 * math.cos(ang), by + 9 * math.sin(ang))
            p2 = (bx - 9 * math.cos(ang), by - 9 * math.sin(ang))
            tip = (bx + 11 * math.cos(a), by + 11 * math.sin(a))
            self.create_polygon(p1, tip, p2, fill=dim, outline="")

        # ---- rótulos do dial: VOZ, GPS, MEM, REDE ----
        labels = ["V O Z", "G P S", "M E M", "R E D E"]
        for i, lbl in enumerate(labels):
            a = (45 + i * 90) * math.pi / 180
            lx, ly = cx + r * 0.68 * math.cos(a), cy + r * 0.68 * math.sin(a)
            self.create_text(lx, ly, text=lbl, fill=vivo,
                             font=("Consolas", max(9, int(r * 0.055))))

        # ---- número central (bateria; CPU em desktops sem bateria) ----
        if self.thinking:
            centro = "···"
        elif self._bat is not None:
            centro = str(self._bat)
        else:
            centro = f"{self._cpu:.0f}"
        self.create_text(cx, cy + r * 0.17, text=centro, fill=vivo,
                         font=("Consolas", int(r * 0.42), "bold"))

        # ---- BAT% / CPU% e hora · data ----
        rotulo = "BAT%" if self._bat is not None else "CPU%"
        if not self.thinking:
            self.create_text(cx, cy - r * 0.08, text=rotulo, fill=dim,
                             font=("Consolas", max(9, int(r * 0.085))))
        import datetime as _dt
        agora = _dt.datetime.now()
        hora_txt = agora.strftime("%H:%M")
        data_txt = f"{agora.day} DE {SEMANA[agora.weekday()]}"
        self.create_text(cx, cy + r * 0.34, text=f"{hora_txt} · {data_txt}",
                         fill=dim, font=("Consolas", max(9, int(r * 0.085))))

        # ---- aura extra quando falando ou ouvindo ----
        if self.speaking or self.listening:
            raio = r * (0.46 + 0.03 * breathe)
            self.create_oval(cx - raio, cy - raio, cx + raio, cy + raio,
                             outline=principal, width=2, stipple="gray50")
