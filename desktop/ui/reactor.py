"""O reator de arco do JARVIS (v4.3.0) — porte fiel do ArcReactorHud.kt.

Dial circular vermelho, estilo Homem de Ferro: marcações finas de
instrumento, blooms de luz pulsantes, anel de chevrons girando, grade
radial no núcleo e leitura viva do computador (bateria/CPU, hora, data).
Animações: respira (2,6s), gira devagar (22s — 6s no modo mãos-livres),
gira rápido (14s — 0,9s pensando), com aura extra falando/ouvindo.
"""
import math
import time
import tkinter as tk

try:
    import psutil
    TEM_PSUTIL = True
except ImportError:
    TEM_PSUTIL = False

# paleta Reator de Arco Vermelho (paleta global convertida de ciano pra vermelho)
RED = "#ff2d20"
RED_VIVO = "#ff5a4d"
RED_DIM = "#a1160f"
RED_ESCURO = "#3d0a07"
FUNDO = "#0a0507"
# tons de glow: do mais fraco ao mais forte
GLOWS = ["#2a0705", "#3d0a07", "#560d09", "#7a110b", "#a1160f"]

SEMANA = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


def _cor_letra(flick: float) -> str:
    """Interpola na paleta GLOWS conforme intensidade 0..1."""
    idx = min(len(GLOWS) - 1, int(flick * len(GLOWS)))
    return GLOWS[idx]


class ArcReactorHud(tk.Canvas):
    def __init__(self, master, size: int = 430, **kw):
        super().__init__(master, width=size, height=size, bg=FUNDO,
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

        # ciclos (idênticos ao Kotlin: 2600ms respirando, 22s/6s spin, 14s/0.9s spin2)
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
            self.create_line(x1, y1, x2, y2, fill=RED_DIM, width=1.2)
        self.create_oval(cx - r * 0.40, cy - r * 0.40, cx + r * 0.40, cy + r * 0.40,
                         outline=RED_DIM, width=1.2)

        # ---- anel de chevrons (40 dashes triangulares) girando ----
        rot = math.radians(slow_spin)
        rr = r * 0.52
        n_chev = 40
        for i in range(n_chev):
            a0 = i * (360 / n_chev) * math.pi / 180 + rot
            a1 = (i * (360 / n_chev) + (360 / n_chev) * 0.55) * math.pi / 180 + rot
            grande = i % 5 == 0
            cor = RED if grande else RED_DIM
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
                             fill=RED if grande else RED_DIM,
                             width=2 if grande else 1)

        # ---- bezel externo (anel duplo) ----
        self.create_oval(cx - r * 0.86, cy - r * 0.86, cx + r * 0.86, cy + r * 0.86,
                         outline=RED_DIM, width=1.5)
        self.create_oval(cx - r * 0.995, cy - r * 0.995, cx + r * 0.995, cy + r * 0.995,
                         outline=RED_ESCURO, width=1.5)

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
            self.create_polygon(p1, tip, p2, fill=RED_DIM, outline="")

        # ---- rótulos do dial: VOZ, GPS, MEM, REDE ----
        labels = ["V O Z", "G P S", "M E M", "R E D E"]
        for i, lbl in enumerate(labels):
            a = (45 + i * 90) * math.pi / 180
            lx, ly = cx + r * 0.68 * math.cos(a), cy + r * 0.68 * math.sin(a)
            self.create_text(lx, ly, text=lbl, fill=RED_VIVO,
                             font=("Consolas", max(9, int(r * 0.055))))

        # ---- número central (bateria; CPU em desktops sem bateria) ----
        if self.thinking:
            centro = "···"
        elif self._bat is not None:
            centro = str(self._bat)
        else:
            centro = f"{self._cpu:.0f}"
        self.create_text(cx, cy + r * 0.17, text=centro, fill=RED_VIVO,
                         font=("Consolas", int(r * 0.42), "bold"))

        # ---- BAT% / CPU% e hora · data ----
        rotulo = "BAT%" if self._bat is not None else "CPU%"
        if not self.thinking:
            self.create_text(cx, cy - r * 0.08, text=rotulo, fill=RED_DIM,
                             font=("Consolas", max(9, int(r * 0.085))))
        import datetime as _dt
        agora = _dt.datetime.now()
        hora_txt = agora.strftime("%H:%M")
        data_txt = f"{agora.day} DE {SEMANA[agora.weekday()]}"
        self.create_text(cx, cy + r * 0.34, text=f"{hora_txt} · {data_txt}",
                         fill=RED_DIM, font=("Consolas", max(9, int(r * 0.085))))

        # ---- aura extra quando falando ou ouvindo ----
        if self.speaking or self.listening:
            pulso = 0.55 + 0.35 * math.sin(el * 6)
            raio = r * (0.46 + 0.03 * breathe)
            self.create_oval(cx - raio, cy - raio, cx + raio, cy + raio,
                             outline=RED, width=2, stipple="gray50")

        self.after(40, self._frame)  # ~25 fps
