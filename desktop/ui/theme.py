"""Temas do HUD — o visual do JARVIS muda com um clique (⚙ CONFIG → TEMA).

Temas:
  - classico  · azul holográfico do JARVIS original (Homem de Ferro)
  - vermelho  · Reator de Arco Vermelho (o clássico das versões Android)
  - gold      · dourado Stark (MK III)
  - radar     · holograma circular teal com sweep de radar (v5.1.0)
  - busto     · Busto Holográfico wireframe gelo/azul (v4.9.3 Android)
  - novoskin  · Busto Holográfico cyan/teal com painel HUD lateral (02/10/2026) — PADRÃO
"""
TEMAS = {
    "classico": {
        "principal": "#22b7ff", "vivo": "#66d4ff", "dim": "#0f6da1",
        "escuro": "#072a3d", "fundo": "#030a12",
        "glows": ["#05121f", "#072a3d", "#0a3a56", "#0f6da1", "#1a8ad0"],
        "janela_bg": "#040810", "painel_bg": "#081018", "painel2": "#0e1a26",
        "entrada_bg": "#0c1826", "user_bg": "#0d2f47", "chat_bg": "#081018",
        "chat_fundo": "#050d16", "fg_dim": "#cdeeff", "txt_fraco": "#7f97a8",
        "txt_claro": "#e8f4fc", "erro_bg": "#2a1212", "erro_fg": "#ff9a8f",
    },
    "vermelho": {
        "principal": "#ff2d20", "vivo": "#ff5a4d", "dim": "#a1160f",
        "escuro": "#3d0a07", "fundo": "#0a0507",
        "glows": ["#2a0705", "#3d0a07", "#560d09", "#7a110b", "#a1160f"],
        "janela_bg": "#080506", "painel_bg": "#0d0708", "painel2": "#171012",
        "entrada_bg": "#1d1214", "user_bg": "#33100c", "chat_bg": "#0d0708",
        "chat_fundo": "#0a0507", "fg_dim": "#ffe4de", "txt_fraco": "#9c8a86",
        "txt_claro": "#f2e6e4", "erro_bg": "#2a0d0d", "erro_fg": "#ff9a8f",
    },
    "radar": {
        # cores amostradas da foto de referência: núcleo teal + anel azul + branco
        "principal": "#1baaad", "vivo": "#2cc5c8", "dim": "#0e5a5c",
        "escuro": "#0a3a3c", "fundo": "#0d111c",
        "glows": ["#0d2a2c", "#12494b", "#1baaad", "#2cc5c8", "#3fd8db"],
        "janela_bg": "#090d16", "painel_bg": "#0d121c", "painel2": "#131a26",
        "entrada_bg": "#101823", "user_bg": "#12324a", "chat_bg": "#0d121c",
        "chat_fundo": "#0a0e18", "fg_dim": "#cfe8ea", "txt_fraco": "#7e8f96",
        "txt_claro": "#e8f2f4", "erro_bg": "#2a1212", "erro_fg": "#ff9a8f",
    },
    "busto": {
        # portado da skin "busto" do Android v4.9.3/4.10.3: wireframe branco-gelo
        # sobre preto, reator azul com anéis (foto novaskins.jpg do André)
        "principal": "#64b5f6", "vivo": "#e0f7fa", "dim": "#2a5a88",
        "escuro": "#0a1a26", "fundo": "#05080c",
        "glows": ["#071018", "#0a1a26", "#123048", "#1d4d73", "#2a6ea8"],
        "janela_bg": "#04070a", "painel_bg": "#081018", "painel2": "#0e1a26",
        "entrada_bg": "#0c1826", "user_bg": "#12324a", "chat_bg": "#081018",
        "chat_fundo": "#050a12", "fg_dim": "#d8ecf7", "txt_fraco": "#7e93a8",
        "txt_claro": "#e8f4fc", "erro_bg": "#2a1212", "erro_fg": "#ff9a8f",
    },
    "novoskin": {
        # pedido do André (foto novoskin.jpg): capacete wireframe cyan/teal
        # vibrante sobre preto puro, reator com brilho branco-ciano no peito
        # e painel HUD de círculos na lateral direita
        "principal": "#19c7d6", "vivo": "#5fe8f0", "dim": "#0d6e78",
        "escuro": "#06292e", "fundo": "#010304",
        "glows": ["#031a1d", "#06292e", "#0d6e78", "#19c7d6", "#8df3f8"],
        "janela_bg": "#000202", "painel_bg": "#040c0d", "painel2": "#081618",
        "entrada_bg": "#061214", "user_bg": "#0d2e32", "chat_bg": "#040c0d",
        "chat_fundo": "#020607", "fg_dim": "#cdf6f8", "txt_fraco": "#6f9598",
        "txt_claro": "#e5fcfd", "erro_bg": "#2a1212", "erro_fg": "#ff9a8f",
    },
    "gold": {
        "principal": "#ffb830", "vivo": "#ffd35e", "dim": "#a1730f",
        "escuro": "#3d2c07", "fundo": "#0a0805",
        "glows": ["#2a1f05", "#3d2c07", "#564109", "#7a5c0b", "#a1730f"],
        "janela_bg": "#080604", "painel_bg": "#0d0a06", "painel2": "#171208",
        "entrada_bg": "#1d1610", "user_bg": "#33260c", "chat_bg": "#0d0a06",
        "chat_fundo": "#0a0805", "fg_dim": "#fff0d4", "txt_fraco": "#a39a86",
        "txt_claro": "#f5efe0", "erro_bg": "#2a0d0d", "erro_fg": "#ff9a8f",
    },
}

_ativo = "novoskin"  # 02/10/2026: skin cyan/teal pedida pelo André vira o padrão


def usar(nome: str) -> None:
    global _ativo
    if nome in TEMAS:
        _ativo = nome


def atual() -> str:
    return _ativo


def cor(chave: str) -> str:
    return TEMAS[_ativo][chave]


def cores() -> dict:
    return TEMAS[_ativo]

