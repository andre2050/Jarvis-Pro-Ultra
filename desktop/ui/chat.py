"""Painel de chat — bolhas refinadas estilo v4.1.0 'Elegância' em vermelho."""
import tkinter as tk
from tkinter import font as tkfont

COR_FUNDO = "#0a0507"
COR_CHAT = "#0d0708"
COR_USER = "#33100c"
COR_JARVIS = "#171012"
TXT_USER = "#ffe4de"
TXT_JARVIS = "#f2e6e4"
TXT_FRACO = "#9c8a86"
VERMELHO = "#ff2d20"


class ChatPanel(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=COR_CHAT, **kw)
        self.texto = tk.Text(self, bg=COR_CHAT, bd=0, highlightthickness=0,
                             wrap="word", padx=16, pady=12, cursor="arrow",
                             font=("Segoe UI", 11), state=tk.DISABLED)
        barra = tk.Scrollbar(self, command=self.texto.yview, bg="#1a1012",
                             troughcolor=COR_CHAT, width=10, bd=0,
                             activebackground="#2a1417", relief=tk.FLAT)
        self.texto.configure(yscrollcommand=barra.set)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        self.texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        f_user = tkfont.Font(font=("Segoe UI", 10))
        f_hora = tkfont.Font(font=("Segoe UI", 8))

        self.texto.tag_configure("user", background=COR_USER, foreground=TXT_USER,
                                 lmargin1=140, lmargin2=140, rmargin=16,
                                 spacing1=6, spacing3=6, borderwidth=8,
                                 relief=tk.SOLID)
        self.texto.tag_configure("jarvis", background=COR_JARVIS, foreground=TXT_JARVIS,
                                 lmargin1=16, lmargin2=16, rmargin=140,
                                 spacing1=6, spacing3=6, borderwidth=8,
                                 relief=tk.SOLID)
        self.texto.tag_configure("user_hora", foreground=TXT_FRACO, justify=tk.RIGHT,
                                  rmargin=16, font=f_hora)
        self.texto.tag_configure("jarvis_hora", foreground=TXT_FRACO,
                                 lmargin1=16, font=f_hora)
        self.texto.tag_configure("erro", background="#2a0d0d", foreground="#ff9a8f",
                                 lmargin1=16, lmargin2=16, rmargin=140,
                                 spacing1=6, spacing3=6, borderwidth=8,
                                 relief=tk.SOLID)
        self.texto.tag_configure("sep", foreground=COR_CHAT, spacing1=2)
        self._marcador_digitando = None
        self.transcricao: list[tuple[str, str, str]] = []  # (papel, hora, msg)

    # ---------- API ----------

    def add(self, papel: str, msg: str) -> None:
        """papel: 'user' | 'jarvis' | 'erro' | 'sistema'."""
        from datetime import datetime
        hora = datetime.now().strftime("%H:%M")
        self.esconder_digitando()
        if papel in ("user", "jarvis", "erro"):
            self.transcricao.append((papel, hora, msg))
        self.texto.configure(state=tk.NORMAL)
        self.texto.insert(tk.END, "\n", "sep")
        if papel == "sistema":
            self.texto.insert(tk.END, f"  {msg}", "jarvis_hora")
        else:
            tag = "erro" if papel == "erro" else papel
            self.texto.insert(tk.END, f"{msg}\n", tag)
            self.texto.insert(tk.END, f"{'você' if papel == 'user' else 'J.A.R.V.I.S'} · {hora}\n",
                             "user_hora" if papel == "user" else "jarvis_hora")
        self.texto.insert(tk.END, "\n", "sep")
        self.texto.see(tk.END)
        self.texto.configure(state=tk.DISABLED)

    def exportar(self) -> str | None:
        """Salva a conversa num .txt e devolve o caminho (ou None se vazia)."""
        if not self.transcricao:
            return None
        from datetime import datetime
        from tkinter import filedialog
        nome_padrao = f"jarvis-conversa-{datetime.now().strftime('%Y%m%d-%H%M')}.txt"
        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile=nome_padrao,
            filetypes=[("Texto", "*.txt")], title="Salvar conversa")
        if not caminho:
            return None
        quem = {"user": "VOCÊ", "jarvis": "J.A.R.V.I.S", "erro": "ERRO"}
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("Conversa com J.A.R.V.I.S — Pro Ultra Desktop\n"
                    f"Exportada em {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                    + "=" * 50 + "\n\n")
            for papel, hora, msg in self.transcricao:
                f.write(f"[{hora}] {quem.get(papel, papel)}:\n{msg}\n\n")
        return caminho

    def mostrar_digitando(self) -> None:
        self.esconder_digitando()
        self.texto.configure(state=tk.NORMAL)
        self._marcador_digitando = self.texto.index(tk.END + "-1c")
        self.texto.insert(tk.END, f"J.A.R.V.I.S está pensando ···\n", "jarvis_hora")
        self.texto.see(tk.END)
        self.texto.configure(state=tk.DISABLED)

    def esconder_digitando(self) -> None:
        if self._marcador_digitando:
            self.texto.configure(state=tk.NORMAL)
            self.texto.delete(self._marcador_digitando, tk.END)
            self.texto.configure(state=tk.DISABLED)
            self._marcador_digitando = None

    def limpar(self) -> None:
        self.texto.configure(state=tk.NORMAL)
        self.texto.delete("1.0", tk.END)
        self.texto.configure(state=tk.DISABLED)
