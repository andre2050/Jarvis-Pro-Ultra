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
