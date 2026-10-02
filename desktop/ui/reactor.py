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
from pathlib import Path

try:
    import psutil
    TEM_PSUTIL = True
except ImportError:
    TEM_PSUTIL = False

try:
    from PIL import Image, ImageTk
    TEM_PIL = True
except ImportError:
    TEM_PIL = False

# v4.10.9: arte gerada por IA pra skin "novoskin" (fiel à foto de referência
# do André) — ver assets/README.md. Caminho relativo ao projeto desktop/.
_ASSET_NOVOSKIN = Path(__file__).resolve().parent.parent / "assets" / "novoskin_bust.png"
# posições relativas (0..1 da imagem) calibradas por análise de pixel da arte:
# olho esquerdo, olho direito, reator do peito. Boca é estimativa (a arte não
# tem boca visível — visor fechado — mas o HUD precisa animar fala).
_NOVOSKIN_OLHO_E = (0.400, 0.309)
_NOVOSKIN_OLHO_D = (0.605, 0.309)
_NOVOSKIN_REATOR = (0.499, 0.812)
_NOVOSKIN_BOCA = (0.502, 0.400)

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
        # v5.1.5: o canvas herda a cor de fundo do container — as bordas do
        # canvas ficam INVISÍVEIS e o holograma parece flutuar na tela,
        # sem o "quadrado" atrás do círculo (era bg=_T("fundo"), que tinha
        # um tom levemente diferente do painel e aparecia como uma caixa).
        try:
            bg_canvas = master.cget("bg")
        except Exception:
            bg_canvas = _T("fundo")
        super().__init__(master, width=size, height=size, bg=bg_canvas,
                         highlightthickness=0, **kw)
        self.size = size
        self.thinking = False
        self.listening = False
        self.speaking = False
        self._visema = 0.0   # v4.10.3-desktop: boca do busto anima por palavras faladas
        self._img_novoskin = None    # v4.10.9: cache do PhotoImage (lazy, 1x por tamanho)
        self._img_novoskin_erro = False

        self._t0 = time.time()
        self._bat = None
        self._cpu = 0
        self._atualiza_leituras()
        self._frame()

    def visema_pulso(self, forca: float = 1.0) -> None:
        """Um evento de fala chegou — abre a boca do busto (decai sozinha)."""
        self._visema = min(1.0, self._visema + forca)

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
        self._visema = max(0.0, self._visema - 0.22)   # boca fecha em ~90ms
        if _tema.atual() == "radar":
            self._frame_radar(cx, cy, r, el)
        elif _tema.atual() == "busto":
            self._frame_busto(cx, cy, r, el)
        elif _tema.atual() == "novoskin":
            self._frame_novoskin(cx, cy, r, el)
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

        # ---- BRILHO RADIAL atrás do círculo: luz emanando, não uma caixa ----
        # (3 halos concêntricos com alpha caindo — o canvas é invisível, então
        #  o que se vê em volta do holograma é esse glow, igual à foto)
        halo = _T("principal")
        for dist, stipp, wdt in ((1.06, "gray12", 10), (1.03, "gray25", 7), (1.005, "gray37", 4)):
            self.create_oval(cx - r * dist, cy - r * dist, cx + r * dist, cy + r * dist,
                             outline=halo, width=wdt, stipple=stipp)

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


    def _carregar_novoskin(self):
        """Carrega a arte da novoskin UMA vez por tamanho de canvas (lazy).
        Se Pillow ou o arquivo faltarem, cai pro desenho vetorial antigo —
        nunca quebra a tela."""
        if self._img_novoskin is not None or self._img_novoskin_erro:
            return self._img_novoskin
        if not TEM_PIL or not _ASSET_NOVOSKIN.exists():
            self._img_novoskin_erro = True
            return None
        try:
            im = Image.open(_ASSET_NOVOSKIN).convert("RGB")
            im = im.resize((int(self.size), int(self.size)), Image.LANCZOS)
            self._img_novoskin = ImageTk.PhotoImage(im)
        except Exception:
            self._img_novoskin_erro = True
            self._img_novoskin = None
        return self._img_novoskin

    def _frame_novoskin(self, cx, cy, r, el):
        """NOVOSKIN (v4.10.9): arte gerada por IA a partir da foto de
        referência do André (busto wireframe teal/cyan, reator triangular,
        painel HUD lateral) como imagem de fundo, com os overlays
        animados do JARVIS (olhos, boca por visema, reator pulsante,
        varredura pensando/ouvindo) desenhados por cima nas posições
        calibradas por análise de pixel da própria arte. Sem Pillow ou
        sem o arquivo, degrada pro busto vetorial clássico."""
        img = self._carregar_novoskin()
        if img is None:
            self._frame_busto(cx, cy, r, el, painel_lateral=True)
            return

        gelo = _T("vivo")
        azul = _T("principal")
        glows = _tema.cores()["glows"]
        tam = self.size

        self.create_image(cx, cy, image=img)  # arte de base (anchor=center)

        if self.speaking or self.listening:
            raio = r * (0.94 + 0.02 * math.sin(el * 6))
            self.create_oval(cx - raio, cy - raio, cx + raio, cy + raio,
                             outline=azul, width=2, stipple="gray50")

        # ---- olhos: brilho pulsante nas posições calibradas da arte ----
        pulso_olho = 0.5 + 0.5 * math.sin(el * 2.2)
        if self.thinking or self.listening:
            pulso_olho = 0.7 + 0.3 * math.sin(el * 5)
        rr_olho = tam * (0.028 + 0.006 * pulso_olho)
        for (nx, ny) in (_NOVOSKIN_OLHO_E, _NOVOSKIN_OLHO_D):
            ox, oy = nx * tam, ny * tam
            self.create_oval(ox - rr_olho, oy - rr_olho, ox + rr_olho, oy + rr_olho,
                             fill=glows[4], outline="", stipple="gray50")
            self.create_oval(ox - rr_olho * 0.45, oy - rr_olho * 0.45,
                             ox + rr_olho * 0.45, oy + rr_olho * 0.45,
                             fill=gelo, outline="")

        # ---- boca: grade visor fina que se abre com o visema ----
        boca = 2 + self._visema * r * 0.10
        if self.speaking and self._visema < 0.15:
            boca = 2 + r * 0.012 * (1 + math.sin(el * 18))
        bmx, bmy = _NOVOSKIN_BOCA[0] * tam, _NOVOSKIN_BOCA[1] * tam
        bx1, bx2 = bmx - r * 0.14, bmx + r * 0.14
        for i in range(3):
            yy = bmy - boca + i * boca
            self.create_line(bx1, yy, bx2, yy, fill=glows[3], width=2)

        if self.thinking:
            ys = (_NOVOSKIN_OLHO_E[1] * tam) + ((_NOVOSKIN_REATOR[1] - _NOVOSKIN_OLHO_E[1]) * tam) * ((el * 0.4) % 1.0)
            self.create_line(cx - r * 0.45, ys, cx + r * 0.45, ys,
                             fill=azul, width=2, stipple="gray50")
        if self.listening:
            self.create_oval(cx - r * 0.70, cy - r * 0.70, cx + r * 0.70, cy + r * 0.70,
                             outline=azul, width=1.5, stipple="gray25")

        # ---- reator: pulso + anel de energia na posição calibrada ----
        rcx, rcy = _NOVOSKIN_REATOR[0] * tam, _NOVOSKIN_REATOR[1] * tam
        rr = r * 0.10
        brilho = 0.55 + 0.25 * math.sin(el * 2.4) + (0.12 if self.speaking else 0)
        self.create_oval(rcx - rr * 1.6, rcy - rr * 1.6, rcx + rr * 1.6, rcy + rr * 1.6,
                         fill=glows[1], outline="", stipple="gray50")
        self.create_oval(rcx - rr * 0.4, rcy - rr * 0.4, rcx + rr * 0.4, rcy + rr * 0.4,
                         fill=_cor_letra(min(1.0, brilho)), outline="")
        if self.speaking:
            pulse = (el % 1.2) / 1.2
            ra = rr * (1.3 + pulse * 1.4)
            self.create_oval(rcx - ra, rcy - ra, rcx + ra, rcy + ra,
                             outline=azul, width=2, stipple="gray50")
        for i in range(5):
            a = el * 1.3 + i * (360 / 5) * math.pi / 180
            pr = rr * (1.8 + 0.15 * math.sin(el * 3 + i))
            px, py = rcx + pr * math.cos(a), rcy + pr * math.sin(a)
            self.create_oval(px - 1.3, py - 1.3, px + 1.3, py + 1.3, fill=glows[3], outline="")

        # ---- partículas subindo ----
        for i in range(7):
            pr = r * (0.5 + 0.45 * ((i * 0.137 + el * 0.05) % 1.0))
            pa = el * 0.4 + i * 2.3
            px, py = cx + pr * math.cos(pa), cy + pr * math.sin(pa) * 0.9
            self.create_oval(px - 1.5, py - 1.5, px + 1.5, py + 1.5,
                             fill=glows[2], outline="")

        # ---- painel HUD lateral: coluna de círculos (igual à foto) ----
        px = tam * 0.94
        py0 = cy - r * 0.55
        for i in range(4):
            py = py0 + i * r * 0.26
            aceso = (int(el * 1.3) + i) % 4 == 0
            self.create_oval(px - 7, py - 7, px + 7, py + 7,
                             outline=azul, width=1.5,
                             fill=(glows[3] if aceso else ""))
        self.create_line(px, py0 - r * 0.12, px, py0 + 3 * r * 0.26 + r * 0.12,
                         fill=_T("dim"), width=1)

        txt = time.strftime("%H:%M")
        if self._bat is not None:
            txt += f"  ·  {self._bat}%"
        else:
            txt += f"  ·  CPU {self._cpu:.0f}%"
        self.create_text(cx, cy + r * 0.97, text=txt, font=("Consolas", 9),
                         fill=_T("dim"))

    def _frame_busto(self, cx, cy, r, el, painel_lateral=False):
        """BUSTO HOLOGRÁFICO (paridade Android v4.9.3→4.10.3): capacete
        wireframe branco-gelo, fendas de olhos luminosas, boca animada por
        visemas, ombros com fiação tracejada e reator azul no peito."""
        gelo = _T("vivo")        # #e0f7fa — traço principal do wireframe
        gelo_dim = _T("dim")
        azul = _T("principal")   # #64b5f6 — reator
        glows = _tema.cores()["glows"]

        # ---- aura quando falando ou ouvindo ----
        if self.speaking or self.listening:
            raio = r * (0.94 + 0.02 * math.sin(el * 6))
            self.create_oval(cx - raio, cy - raio, cx + raio, cy + raio,
                             outline=azul, width=2, stipple="gray50")

        # ---- crânio: casquete superior do capacete ----
        top = cy - r * 0.92
        self.create_arc(cx - r * 0.58, top, cx + r * 0.58, cy + r * 0.10,
                         start=0, extent=180, style=tk.ARC, outline=gelo, width=2)
        # linha da têmpora até a mandíbula (dos dois lados)
        for lado in (-1, 1):
            x_t = cx + lado * r * 0.58
            self.create_line(x_t, cy - r * 0.42, x_t * 1 + lado * r * 0.02, cy + r * 0.18,
                             fill=gelo_dim, width=1.4)

        # ---- faceplate segmentado (a máscara central) ----
        fx1, fx2 = cx - r * 0.42, cx + r * 0.42
        fy1, fy2 = cy - r * 0.56, cy + r * 0.30
        self.create_rectangle(fx1, fy1, fx2, fy2, outline=gelo, width=2)
        for i in range(1, 4):  # facetas verticais suaves
            x = fx1 + (fx2 - fx1) * i / 4
            self.create_line(x, fy1 + r * 0.06, x, fy2 - r * 0.06,
                            fill=gelo_dim, width=1, stipple="gray50")

        # ---- olhos: fendas luminosas ----
        for lado in (-1, 1):
            ox = cx + lado * r * 0.20
            self.create_polygon(ox - r * 0.13, cy - r * 0.20,
                                ox + r * 0.10, cy - r * 0.26,
                                ox + r * 0.13, cy - r * 0.14,
                                ox - r * 0.10, cy - r * 0.10,
                                fill=glows[4], outline=gelo, width=1)

        # ---- boca animada por visema (o pulso vem do TTS, palavra a palavra) ----
        boca = 4 + self._visema * r * 0.11
        if self.speaking and self._visema < 0.15:
            boca = 4 + r * 0.015 * (1 + math.sin(el * 18))  # micro-vibração entre palavras
        self.create_oval(cx - r * 0.16, cy + r * 0.10 - boca / 2,
                         cx + r * 0.16, cy + r * 0.10 + boca / 2,
                         fill=glows[3], outline=gelo, width=1.2)

        # ---- varredura quando pensando (scan subindo pelo rosto) ----
        if self.thinking:
            ys = fy1 + (fy2 - fy1) * ((el * 0.55) % 1.0)
            self.create_line(fx1 - 6, ys, fx2 + 6, ys, fill=azul, width=2, stipple="gray50")

        # ---- retículo tracejado quando ouvindo ----
        if self.listening:
            self.create_oval(cx - r * 0.70, cy - r * 0.70, cx + r * 0.70, cy + r * 0.70,
                             outline=azul, width=1.5, stipple="gray25")

        # ---- ombros e tórax com fiação tracejada ----
        sh_y = cy + r * 0.52
        self.create_line(cx - r * 0.95, sh_y + r * 0.38, cx - r * 0.55, sh_y,
                         fill=gelo_dim, width=2)
        self.create_line(cx + r * 0.95, sh_y + r * 0.38, cx + r * 0.55, sh_y,
                         fill=gelo_dim, width=2)
        self.create_line(cx - r * 0.55, sh_y, cx - r * 0.30, sh_y - r * 0.10,
                         fill=gelo_dim, width=1.4)
        self.create_line(cx + r * 0.55, sh_y, cx + r * 0.30, sh_y - r * 0.10,
                         fill=gelo_dim, width=1.4)
        for i in range(3):  # fiação interna do tórax (como na foto de referência)
            y = sh_y + r * 0.08 + i * r * 0.09
            self.create_line(cx - r * 0.40 + i * r * 0.04, y,
                             cx - r * 0.12 - i * r * 0.03, y + r * 0.02,
                             fill=gelo_dim, width=1, stipple="gray50")
            self.create_line(cx + r * 0.40 - i * r * 0.04, y,
                             cx + r * 0.12 + i * r * 0.03, y + r * 0.02,
                             fill=gelo_dim, width=1, stipple="gray50")

        # ---- reator de arco no peito: anéis concêntricos + cruz + brilho ----
        rcx, rcy = cx, cy + r * 0.60
        rr = r * 0.13
        brilho = 0.55 + 0.25 * math.sin(el * 2.4) + (0.12 if self.speaking else 0)
        self.create_oval(rcx - rr * 1.9, rcy - rr * 1.9, rcx + rr * 1.9, rcy + rr * 1.9,
                         fill=glows[1], outline="")
        self.create_oval(rcx - rr * 1.3, rcy - rr * 1.3, rcx + rr * 1.3, rcy + rr * 1.3,
                         outline=azul, width=2)
        self.create_oval(rcx - rr * 0.8, rcy - rr * 0.8, rcx + rr * 0.8, rcy + rr * 0.8,
                         fill=glows[4], outline=gelo, width=1.5)
        self.create_oval(rcx - rr * 0.35, rcy - rr * 0.35, rcx + rr * 0.35, rcy + rr * 0.35,
                         fill=_cor_letra(min(1.0, brilho)), outline="")
        for a in (0, 90, 180, 270):  # pás da cruz
            rad = math.radians(a)
            self.create_line(rcx + rr * 0.8 * math.cos(rad), rcy + rr * 0.8 * math.sin(rad),
                             rcx + rr * 1.3 * math.cos(rad), rcy + rr * 1.3 * math.sin(rad),
                             fill=gelo, width=2)
        if self.speaking:  # anéis de energia expandindo enquanto fala
            pulse = (el % 1.2) / 1.2
            ra = rr * (1.3 + pulse * 1.2)
            self.create_oval(rcx - ra, rcy - ra, rcx + ra, rcy + ra,
                             outline=azul, width=2, stipple="gray50")

        # ---- partículas subindo (mesma linguagem do modo mesa Android) ----
        for i in range(7):
            pr = r * (0.5 + 0.45 * ((i * 0.137 + el * 0.05) % 1.0))
            pa = el * 0.4 + i * 2.3
            px, py = cx + pr * math.cos(pa), cy + pr * math.sin(pa) * 0.9
            self.create_oval(px - 1.5, py - 1.5, px + 1.5, py + 1.5,
                             fill=gelo_dim, outline="")

        # ---- bateria/hora discretos (leitura viva do PC) ----
        txt = time.strftime("%H:%M")
        if self._bat is not None:
            txt += f"  ·  {self._bat}%"
        if TEM_PSUTIL:
            txt += f"  ·  CPU {self._cpu:.0f}%"
        self.create_text(cx, cy + r * 0.97, text=txt, font=("Consolas", 9),
                         fill=gelo_dim)

        # ---- painel HUD lateral (skin "novoskin": coluna de círculos à direita,
        # como na foto de referência do André) ----
        if painel_lateral:
            px = self.size * 0.94
            py0 = cy - r * 0.55
            for i in range(4):
                py = py0 + i * r * 0.26
                aceso = (int(el * 1.3) + i) % 4 == 0  # um círculo "pisca" por vez
                self.create_oval(px - 7, py - 7, px + 7, py + 7,
                                 outline=azul, width=1.5,
                                 fill=(glows[3] if aceso else ""))
            self.create_line(px, py0 - r * 0.12, px, py0 + 3 * r * 0.26 + r * 0.12,
                             fill=gelo_dim, width=1)
