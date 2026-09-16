"""Temas do HUD — o visual do JARVIS muda com um clique (⚙ CONFIG → TEMA).

Temas:
  - classico  · azul holográfico do JARVIS original (Homem de Ferro)
  - vermelho  · Reator de Arco Vermelho (o clássico das versões Android)
  - gold      · dourado Stark (MK III)
  - radar     · holograma circular teal com sweep de radar (v5.1.0)
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

_ativo = "classico"


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

