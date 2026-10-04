"""Comandos críticos reconhecidos OFFLINE (v4.11.0).

Hora, data, status do PC, abrir app, música, volume e timer respondem NA
HORA — sem esperar o cérebro, sem internet e sem chave do Gemini. Os
padrões são ESTRITOS de propósito: só roteiam o que têm certeza; qualquer
outra coisa segue pro cérebro normalmente (conversa nunca é sequestrada).
"""
import re
from datetime import datetime

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]


def _exec_padrao():
    from . import tools
    return tools.execute


def reconhecer(texto: str, _exec=None):
    """Reconhece um comando crítico. Devolve (resposta_do_jarvis, acao) ou
    None pra deixar o cérebro lidar. Nunca lança exceção pro chamador."""
    try:
        return _reconhecer(texto, _exec or _exec_padrao())
    except Exception:
        return None


def _reconhecer(texto: str, executa) -> tuple | None:
    t = (texto or "").strip()
    tl = re.sub(r"\s+", " ", t.lower())
    if not t or len(t) > 90:
        return None

    # ---------- respostas diretas (zero tools, zero rede) ----------
    m = re.fullmatch(r"(?:(?:me\s+)?(?:d[áa]|dê)\s+(?:o\s+)?(?:meu\s+)?briefing|briefing"
                     r"|resumo\s+do\s+dia|not[íi]cias\s+do\s+dia)\??", tl)
    if m:
        from . import briefing
        return briefing.gerar(), None

    # calculadora: "quanto é 25*48+12" / "calcula 2 mais 2"
    m = re.fullmatch(r"(?:quanto\s+(?:é|e|dá|da)\s+|calcula(?:r)?\s+)(.{1,60})", tl)
    if m:
        r = _calcular(m.group(1))
        if r is not None:
            return r, None

    # mídia: pausa/toca/próxima/anterior (qualquer player que esteja tocando)
    if re.fullmatch(r"(?:pausa|pausar|despausa|despausar|toca|tocar|play|d[áa] play)\s*"
                    r"(?:a\s+|o\s+)?(?:m[úu]sica|musica|som|player|v[íi]deo)?\??", tl):
        return executa("controlar_midia", {"acao": "play_pause"}), "midia"
    if re.fullmatch(r"(?:pr[óo]xima|passa|pula|avan[çc]a)\s+(?:a\s+|o\s+)?"
                    r"(?:m[úu]sica|musica|faixa|v[íi]deo)\??", tl):
        return executa("controlar_midia", {"acao": "proxima"}), "midia"
    if re.fullmatch(r"(?:volta|anterior|retorna)\s+(?:a\s+|o\s+)?"
                    r"(?:m[úu]sica|musica|faixa)\??", tl):
        return executa("controlar_midia", {"acao": "anterior"}), "midia"
    if re.fullmatch(r"(que horas?( são?)?|horas?)\??", tl):
        return f"São {datetime.now().strftime('%H:%M')}, senhor.", None
    if re.fullmatch(r"(que dia (é|e) hoje|data( de hoje)?)\??", tl):
        agora = datetime.now()
        return (f"Hoje é {DIAS[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}, senhor.",
                None)
    if re.fullmatch(r"(status( do (pc|computador))?|como (está|esta) o (pc|computador|sistema)"
                    r"|bateria( do (pc|notebook))?)\??", tl):
        return executa("status_do_sistema", {}), None

    # ---------- ações diretas (tool executada sem rodada de LLM) ----------
    m = re.fullmatch(r"(?:abre|abra|abrir|abrir|executa|executar|roda|rodar)\s+"
                     r"(?:o |a |os |as )?(.{2,60})", tl)
    if m and not re.search(r"(site|link|navegador|pesqui|arquivo|pasta|janela)", m.group(1)):
        return executa("abrir_app", {"app": m.group(1).strip()}), "abrir_app"

    m = re.fullmatch(r"(?:toca|tocar|p[õo]e|p[ôo]r|coloca|colocar)\s+"
                     r"(?:um |uma )?(?:a |o )?(?:m[úu]sica|som)(?:\s+(?:de|do|da)\s+(.+))?",
                     tl)
    if m:
        busca = (m.group(1) or "").strip() or "música"
        return executa("tocar_musica", {"busca": busca}), "tocar_musica"

    if re.fullmatch(r"(?:aumenta|aumentar|ab[úu]a|ab[úu]a o volume|mais)\s+(?:o\s+)?volume\??", tl) \
            or re.fullmatch(r"mais\s+volume\??", tl):
        return executa("controlar_volume", {"acao": "aumentar"}), "volume"
    if re.fullmatch(r"(?:diminui|diminuir|abaixa|abaixar|menos)\s+(?:o\s+)?volume\??", tl):
        return executa("controlar_volume", {"acao": "diminuir"}), "volume"
    if re.fullmatch(r"(silencia|silenciar|mute|mudo|muta|no mudo|sem som)\??", tl):
        return executa("controlar_volume", {"acao": "silenciar"}), "volume"

    # aviso com HORA MARCADA: "às 18:30 me avisa do boleto" (agenda persistente)
    m = re.search(r"(?:às|as)\s*(\d{1,2})(?:h|:|h)(\d{2})?\b", tl)
    if m and re.search(r"\b(avisa|avise|lembra|lembrete|agend\w+)\b", tl):
        hora = int(m.group(1)) % 24
        minuto = int(m.group(2) or 0) % 60
        horario = f"{hora:02d}:{minuto:02d}"
        if "amanh" in tl:
            horario = "amanhã " + horario
        motivo = re.sub(r"[àa]s\s*\d{1,2}(?:h|:)?\d{0,2}", " ", t, flags=re.I)
        motivo = re.sub(r"\b(me\s+)?(avisa[rl]?|avise|lembra[rl]?|lembrete|"
                        r"agend\w+|que|às|as|no|na)\b", " ",
                        motivo, flags=re.I)
        motivo = re.sub(r"\s+", " ", motivo).strip(" .,!?;:")
        motivo = re.sub(r"^(de|do|da|pra|para)\s+", "", motivo, flags=re.I).strip(" .,!?;:")
        return executa("agendar_aviso",
                       {"horario": horario, "motivo": (motivo or "aviso")[:60]}), "agenda"

    # timer/lembrete: "me avisa em 10 minutos (pra X)" / "timer de 30 segundos"
    m = re.search(r"(?:avisa|avise|lembra|lembrete|timer)"
                  r"[^.?!]{0,24}?(?:em|de)\s+(\d{1,3})\s*"
                  r"(segundos?|minutos?|horas?)"
                  r"(?:\s+(?:para|pra|de|do)\s+(.+))?", tl)
    if m:
        n = int(m.group(1))
        unidade = m.group(2)
        mult = 3600 if unidade.startswith("hora") else (60 if unidade.startswith("min") else 1)
        motivo = (m.group(3) or "timer").strip()[:60]
        return executa("definir_timer", {"segundos": n * mult, "motivo": motivo}), "timer"

    return None


def _calcular(expressao: str):
    """Calculadora offline com lista-branca: só passa pra eval o que é
    número e operador depois de traduzir por extenso. Qualquer letra ou
    coisa esquisita devolve None (a pergunta segue pro cérebro)."""
    e = (expressao or "").strip().lower()
    e = (e.replace("vezes", "*").replace(" x ", "*").replace("x", "*")
          .replace("×", "*").replace("÷", "/")
          .replace("dividido por", "/").replace("dividido", "/")
          .replace("mais", "+").replace("menos", "-")
          .replace("elevado a", "**").replace("^", "**")
          .replace(",", "."))
    e = re.sub(r"[^0-9+\-*/().%\s*]", "", e)
    e = re.sub(r"\*{3,}", "**", e)
    e = e.strip()
    digitos = re.sub(r"\D", "", e)
    if not e or not digitos or not re.search(r"[+\-*/]", e):
        return None
    if len(digitos) > 24:  # bomba de potência gigante: fora
        return None
    try:
        resultado = eval(e, {"__builtins__": None}, {})  # noqa: S307 — whitelist
    except Exception:
        return None
    if isinstance(resultado, float) and resultado.is_integer():
        resultado = int(resultado)
    return f"O resultado é {resultado}, senhor."
